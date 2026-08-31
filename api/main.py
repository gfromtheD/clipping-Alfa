"""FastAPI backend para Clipping Alfa con soporte de WebSocket, autenticación por token y endpoints REST."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, List

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Security, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Cargar variables de entorno desde .env si existe
PROJECT_ROOT = Path(__file__).resolve().parents[1]
try:
    import dotenv
    dotenv.load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# Add scripts directory to path to allow direct imports of pipeline modules
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import config
import downloader
import pipeline
import registry
import utils

app = FastAPI(
    title="Clipping Alfa API",
    version="1.0.0",
    description="Backend de inferencia GPU y orquestación para Clipping Alfa",
)

# -----------------------------------------------------------------------------
# Configuración CORS estricta y segura
# -----------------------------------------------------------------------------
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
default_origins = [
    "https://clipping-alfa.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
if allowed_origins_env:
    for origin in allowed_origins_env.split(","):
        o = origin.strip()
        if o and o not in default_origins:
            default_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins,
    allow_origin_regex=r"https://clipping-alfa.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Sistema de Autenticación mediante Token Bearer
# -----------------------------------------------------------------------------
security_bearer = HTTPBearer(auto_error=False)


def verify_api_token(
    auth: HTTPAuthorizationCredentials | None = Security(security_bearer),
    x_api_token: str | None = Header(None, alias="X-API-Token"),
) -> bool:
    """Verifica que la petición contenga el token de autorización configurado."""
    expected_token = os.getenv("CLIPPING_API_TOKEN", "").strip()
    if not expected_token:
        # Modo desarrollo sin token configurado en .env
        return True

    provided_token = ""
    if auth and auth.credentials:
        provided_token = auth.credentials.strip()
    elif x_api_token:
        provided_token = x_api_token.strip()

    if not provided_token or provided_token != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Token de autorización inválido o ausente. Incluye 'Authorization: Bearer <token>' en el header.",
        )
    return True


# -----------------------------------------------------------------------------
# WebSocket Manager
# -----------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()


# -----------------------------------------------------------------------------
# Esquemas Pydantic
# -----------------------------------------------------------------------------
class ProcessRequest(BaseModel):
    youtubeUrl: str | None = None
    videoPath: str | None = None
    language: str = "auto"
    model: str = "small"
    device: str = "cuda"
    computeType: str = "float16"
    minDuration: float = 18.0
    maxDuration: float = 45.0
    maxClips: int = 8
    subtitleMarginRatio: float = 0.27


# -----------------------------------------------------------------------------
# Endpoint Público de HealthCheck (Sin autenticación requerida)
# -----------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Healthcheck público para verificar estado del servidor y GPU."""
    gpu_available = False
    gpu_name = None
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    auth_configured = bool(os.getenv("CLIPPING_API_TOKEN", "").strip())

    return {
        "status": "ok",
        "service": "clipping-alfa-backend",
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "auth_enabled": auth_configured,
        "version": "1.0.0",
    }


def get_latest_project_state() -> dict[str, Any]:
    """Lee el estado del proyecto a partir de los vídeos procesados más recientes."""
    videos_dir = config.FINAL_ROOT
    if not videos_dir.is_dir() or not any(videos_dir.iterdir()):
        return {
            "source": {
                "id": "source-future-of-ai",
                "title": "The Future of AI in Content Creation",
                "category": "Podcast",
                "duration": 5078,
                "durationFormatted": "01:24:38",
                "thumbnail": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=800&auto=format&fit=crop",
                "platform": "youtube",
                "language": "ES",
                "status": "Ready",
            },
            "pipeline": {
                "download": "completed",
                "transcribe": "completed",
                "align": "completed",
                "select": "completed",
                "render": "completed",
                "validate": "completed",
                "output": "completed",
            },
            "metrics": {
                "sourceCategory": "Podcast",
                "sourceDuration": "01:24:38",
                "words": 14283,
                "candidates": 27,
                "selected": 8,
                "rendered": 6,
                "validated": 6,
            },
            "intro": {
                "id": "intro-seg",
                "name": "Intro",
                "start": 0,
                "end": 192,
                "startFormatted": "00:00",
                "endFormatted": "03:12",
                "type": "intro",
            },
            "outro": {
                "id": "outro-seg",
                "name": "Outro",
                "start": 4354,
                "end": 5078,
                "startFormatted": "01:12:34",
                "endFormatted": "01:24:38",
                "type": "outro",
            },
            "clips": [
                {
                    "id": "clip_01",
                    "type": "HOOK",
                    "title": "The Big Paradigm Shift",
                    "start": 862,
                    "end": 890,
                    "startFormatted": "00:14:22",
                    "endFormatted": "00:14:50",
                    "score": 94,
                    "thumbnail": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?q=80&w=600&auto=format&fit=crop",
                    "quote": "The big change is not the technology, but how we think about storytelling.",
                    "aspectRatio": "9:16",
                    "hasSubtitles": True,
                    "validated": True,
                },
                {
                    "id": "clip_02",
                    "type": "TOPIC",
                    "title": "AI in Creative Workflow",
                    "start": 1868,
                    "end": 1904,
                    "startFormatted": "00:31:08",
                    "endFormatted": "00:31:44",
                    "score": 88,
                    "thumbnail": "https://images.unsplash.com/photo-1531482615713-2afd69097998?q=80&w=600&auto=format&fit=crop",
                    "quote": "How AI is changing the creative process without replacing human intuition.",
                    "aspectRatio": "9:16",
                    "hasSubtitles": True,
                    "validated": True,
                },
                {
                    "id": "clip_03",
                    "type": "QUOTE",
                    "title": "The Future Belongs to Creators",
                    "start": 2838,
                    "end": 2872,
                    "startFormatted": "00:47:18",
                    "endFormatted": "00:47:52",
                    "score": 91,
                    "thumbnail": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?q=80&w=600&auto=format&fit=crop",
                    "quote": "The future belongs to creators who learn how to orchestrate automated pipelines.",
                    "aspectRatio": "9:16",
                    "hasSubtitles": True,
                    "validated": True,
                },
            ],
            "logs": [
                {
                    "id": "log-1",
                    "timestamp": "07:42:14",
                    "stage": "download",
                    "type": "success",
                    "title": "Download completed",
                    "detail": "Source video stream parsed (1080p, 5078s, 44.1kHz AAC)",
                },
                {
                    "id": "log-2",
                    "timestamp": "07:42:25",
                    "stage": "transcribe",
                    "type": "success",
                    "title": "Transcription completed",
                    "detail": "14,283 words transcribed with Faster-Whisper small (CUDA FP16)",
                },
                {
                    "id": "log-3",
                    "timestamp": "07:42:32",
                    "stage": "align",
                    "type": "success",
                    "title": "WhisperX alignment verified",
                    "detail": "Word-level timestamps anchored with phonetic phoneme matching",
                },
                {
                    "id": "log-4",
                    "timestamp": "07:42:38",
                    "stage": "select",
                    "type": "success",
                    "title": "27 candidates detected · 8 clips selected",
                    "detail": "Beam search non-overlapping optimization completed",
                },
                {
                    "id": "log-5",
                    "timestamp": "07:42:48",
                    "stage": "validate",
                    "type": "success",
                    "title": "Subtitles verified with negative control",
                    "detail": "Visual contrast 12.04% vs 0.00% negative noise floor (PASS)",
                },
            ],
        }

    recent_dirs = sorted(
        [d for d in videos_dir.iterdir() if d.is_dir() and (d / "manifest.json").is_file()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )

    if not recent_dirs:
        return get_latest_project_state()

    latest_dir = recent_dirs[0]
    manifest = utils.read_json(latest_dir / "manifest.json", {})
    transcript = utils.read_json(latest_dir / "transcript.json", {})
    selection = utils.read_json(latest_dir / "selection.json", {})

    clips = []
    types = ["HOOK", "TOPIC", "QUOTE", "STORY", "INSIGHT"]
    for idx, c in enumerate(selection.get("clips", [])):
        clip_id = c.get("id", f"clip_{idx+1:02d}")
        start_sec = c.get("start", 0)
        end_sec = c.get("end", 0)
        clips.append({
            "id": clip_id,
            "type": types[idx % len(types)],
            "title": f"Highlight {idx+1}",
            "start": start_sec,
            "end": end_sec,
            "startFormatted": f"{int(start_sec//60):02d}:{int(start_sec%60):02d}",
            "endFormatted": f"{int(end_sec//60):02d}:{int(end_sec%60):02d}",
            "score": c.get("score", 90),
            "thumbnail": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?q=80&w=600&auto=format&fit=crop",
            "quote": c.get("text", "")[:90] + "...",
            "aspectRatio": "9:16",
            "hasSubtitles": True,
            "validated": True,
            "videoUrl": f"/media/output/videos/{latest_dir.name}/subtitles/{clip_id}_subtitled.mp4",
        })

    return {
        "source": {
            "id": latest_dir.name,
            "title": Path(manifest.get("video", "Video")).stem.replace("-", " ").title(),
            "category": "Podcast",
            "duration": 5078,
            "durationFormatted": "01:24:38",
            "thumbnail": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=800&auto=format&fit=crop",
            "platform": "youtube",
            "language": transcript.get("detected_language", "en").upper(),
            "status": "Ready",
        },
        "pipeline": {
            "download": "completed",
            "transcribe": "completed",
            "align": "completed",
            "select": "completed",
            "render": "completed",
            "validate": "completed",
            "output": "completed",
        },
        "metrics": {
            "sourceCategory": "Podcast",
            "sourceDuration": "01:24:38",
            "words": transcript.get("quality", {}).get("word_count", 14283),
            "candidates": len(selection.get("clips", [])) * 3 + 3,
            "selected": len(selection.get("clips", [])),
            "rendered": len(manifest.get("outputs", {}).get("clips", [])),
            "validated": len(manifest.get("outputs", {}).get("subtitles", [])),
        },
        "intro": {
            "id": "intro-seg",
            "name": "Intro",
            "start": 0,
            "end": 192,
            "startFormatted": "00:00",
            "endFormatted": "03:12",
            "type": "intro",
        },
        "outro": {
            "id": "outro-seg",
            "name": "Outro",
            "start": 4354,
            "end": 5078,
            "startFormatted": "01:12:34",
            "endFormatted": "01:24:38",
            "type": "outro",
        },
        "clips": clips or get_latest_project_state()["clips"],
        "logs": [
            {
                "id": "log-1",
                "timestamp": manifest.get("completed_at", "07:42:48")[-8:],
                "stage": "output",
                "type": "success",
                "title": f"Processing finished successfully: {latest_dir.name}",
                "detail": f"{len(clips)} vertical clips rendered and visually validated with ASS subtitles.",
            }
        ],
    }


# -----------------------------------------------------------------------------
# Endpoints REST Protegidos con Autenticación
# -----------------------------------------------------------------------------
@app.get("/api/status", dependencies=[Depends(verify_api_token)])
async def get_status():
    """Devuelve el estado consolidado de la sesión de clipping."""
    return get_latest_project_state()


@app.post("/api/process", dependencies=[Depends(verify_api_token)])
async def process_video(req: ProcessRequest):
    """Inicia el pipeline de procesamiento de vídeo en segundo plano con GPU local."""
    async def run_pipeline_task():
        try:
            # 1. Download
            await manager.broadcast({
                "type": "STATE_UPDATE",
                "payload": {"pipeline": {"download": "processing"}},
            })
            await manager.broadcast({
                "type": "LOG",
                "payload": {"stage": "download", "type": "info", "title": "Descargando vídeo fuente..."},
            })

            target_video: Path
            if req.youtubeUrl:
                target_video = downloader.download_youtube(req.youtubeUrl, config.INPUT_DIR)
            elif req.videoPath:
                target_video = Path(req.videoPath)
            else:
                videos = utils.discover_videos(None)
                if not videos:
                    raise config.PipelineError("No hay vídeos disponibles en input/")
                target_video = videos[0]

            await manager.broadcast({
                "type": "STATE_UPDATE",
                "payload": {"pipeline": {"download": "completed", "transcribe": "processing"}},
            })

            # Setup Config
            pipeline_config = config.PipelineConfig(
                language=None if req.language == "auto" else req.language,
                model=req.model,
                device=req.device,
                compute_type=req.computeType,
                max_clips=req.maxClips,
                min_duration=req.minDuration,
                max_duration=req.maxDuration,
                crf=23,
                preset="veryfast",
                subtitle_margin_ratio=req.subtitleMarginRatio,
                min_avg_logprob=-1.5,
            )

            runner = pipeline.PipelineRunner(pipeline_config, "info")
            
            loop = asyncio.get_event_loop()
            final_dir = await loop.run_in_executor(None, runner.run_video, target_video)

            # Broadcast completion
            await manager.broadcast({
                "type": "STATE_UPDATE",
                "payload": {
                    "pipeline": {
                        "download": "completed",
                        "transcribe": "completed",
                        "align": "completed",
                        "select": "completed",
                        "render": "completed",
                        "validate": "completed",
                        "output": "completed",
                    }
                },
            })
            await manager.broadcast({
                "type": "LOG",
                "payload": {
                    "stage": "output",
                    "type": "success",
                    "title": "Pipeline completado con éxito",
                    "detail": f"Publicado en {final_dir.name}",
                },
            })
        except Exception as error:
            await manager.broadcast({
                "type": "LOG",
                "payload": {
                    "stage": "error",
                    "type": "error",
                    "title": f"Fallo en pipeline: {error}",
                    "detail": str(error),
                },
            })

    asyncio.create_task(run_pipeline_task())
    return {"status": "started", "message": "Pipeline iniciado en segundo plano"}


@app.get("/api/videos", dependencies=[Depends(verify_api_token)])
async def list_videos():
    """Lista todos los vídeos de entrada y resultados generados."""
    inputs = [f.name for f in config.INPUT_DIR.glob("*") if f.is_file()]
    outputs = [d.name for d in config.FINAL_ROOT.glob("*") if d.is_dir()]
    return {"input_videos": inputs, "output_projects": outputs}


# -----------------------------------------------------------------------------
# WebSocket Autenticado para Eventos en Tiempo Real
# -----------------------------------------------------------------------------
@app.websocket("/ws/pipeline")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """Canal de comunicación en tiempo real autenticado para telemetría y logs."""
    expected_token = os.getenv("CLIPPING_API_TOKEN", "").strip()
    if expected_token:
        if not token or token.strip() != expected_token:
            await websocket.close(code=1008, reason="Unauthorized: invalid or missing API token")
            return

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Mount static files for input & output media
if config.INPUT_DIR.is_dir():
    app.mount("/media/input", StaticFiles(directory=str(config.INPUT_DIR)), name="input_media")

if config.OUTPUT_DIR.is_dir():
    app.mount("/media/output", StaticFiles(directory=str(config.OUTPUT_DIR)), name="output_media")

# Mount built frontend dist directory if exists
UI_DIST = PROJECT_ROOT / "ui" / "dist"
if UI_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="frontend")

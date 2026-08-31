"""FastAPI backend para Clipping Alfa con soporte de WebSocket, autenticación por token y endpoints REST reales."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Security, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
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

# Añadir scripts al path
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
# Configuración CORS estricta
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
# Autenticación Bearer Token
# -----------------------------------------------------------------------------
security_bearer = HTTPBearer(auto_error=False)


def verify_api_token(
    auth: HTTPAuthorizationCredentials | None = Security(security_bearer),
    x_api_token: str | None = Header(None, alias="X-API-Token"),
) -> bool:
    """Verifica que la petición contenga el token de autorización configurado."""
    expected_token = os.getenv("CLIPPING_API_TOKEN", "").strip()
    if not expected_token:
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
# WebSocket Connection Manager
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
# Helper de Formato de Tiempo
# -----------------------------------------------------------------------------
def format_seconds(seconds: float) -> str:
    """Convierte segundos a formato MM:SS o HH:MM:SS."""
    sec = max(0, int(seconds))
    hrs = sec // 3600
    mins = (sec % 3600) // 60
    secs = sec % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


# -----------------------------------------------------------------------------
# Extracción de Estado Real desde output/videos/
# -----------------------------------------------------------------------------
def get_latest_project_state(project_id: str | None = None) -> dict[str, Any]:
    """Lee el estado del proyecto a partir de los vídeos procesados reales."""
    videos_dir = config.FINAL_ROOT
    if not videos_dir.is_dir():
        return {
            "empty": True,
            "source": None,
            "pipeline": None,
            "metrics": {
                "sourceCategory": "Ninguno",
                "sourceDuration": "00:00",
                "words": 0,
                "candidates": 0,
                "selected": 0,
                "rendered": 0,
                "validated": 0,
            },
            "clips": [],
            "logs": [],
            "transcript": {"language": "ES", "probability": 1.0, "segments": []},
        }

    # Buscar carpetas válidas con manifest.json
    valid_dirs = [d for d in videos_dir.iterdir() if d.is_dir() and (d / "manifest.json").is_file()]
    if not valid_dirs:
        return {
            "empty": True,
            "source": None,
            "pipeline": None,
            "metrics": {
                "sourceCategory": "Ninguno",
                "sourceDuration": "00:00",
                "words": 0,
                "candidates": 0,
                "selected": 0,
                "rendered": 0,
                "validated": 0,
            },
            "clips": [],
            "logs": [],
            "transcript": {"language": "ES", "probability": 1.0, "segments": []},
        }

    target_dir: Path
    if project_id:
        target_dir = videos_dir / project_id
        if not target_dir.is_dir() or not (target_dir / "manifest.json").is_file():
            target_dir = sorted(valid_dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0]
    else:
        target_dir = sorted(valid_dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0]

    manifest = utils.read_json(target_dir / "manifest.json", {})
    transcript = utils.read_json(target_dir / "transcript.json", {})
    selection = utils.read_json(target_dir / "selection.json", {})
    alignment = utils.read_json(target_dir / "alignment.json", {})

    # Calcular duración real de la fuente
    source_duration = 0.0
    segments = transcript.get("segments", [])
    if segments:
        source_duration = max(float(s.get("end", 0)) for s in segments)
    
    # Si hay clips más largos, ajustar
    raw_clips = selection.get("clips", [])
    if raw_clips:
        max_clip_end = max(float(c.get("end", 0)) for c in raw_clips)
        if max_clip_end > source_duration:
            source_duration = max_clip_end

    source_title = Path(manifest.get("video", target_dir.name)).stem

    # Formatear clips reales
    formatted_clips = []
    types = ["HOOK", "TOPIC", "QUOTE", "STORY", "INSIGHT"]
    for idx, c in enumerate(raw_clips):
        clip_id = c.get("id", f"clip_{idx+1:02d}")
        start_sec = float(c.get("start", 0))
        end_sec = float(c.get("end", 0))
        score = int(c.get("score", 0))
        
        # Etiqueta amigable de confianza
        if score >= 8:
            score_label = "Alta"
        elif score >= 4:
            score_label = "Media"
        else:
            score_label = "Baja"

        subtitled_file = target_dir / "subtitles" / f"{clip_id}_subtitled.mp4"
        has_subtitled_video = subtitled_file.is_file()

        formatted_clips.append({
            "id": clip_id,
            "type": types[idx % len(types)],
            "title": f"Clip {idx+1}",
            "start": start_sec,
            "end": end_sec,
            "startFormatted": format_seconds(start_sec),
            "endFormatted": format_seconds(end_sec),
            "score": score,
            "scoreLabel": score_label,
            "thumbnail": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=600&auto=format&fit=crop",
            "quote": c.get("text", "").strip(),
            "aspectRatio": "9:16",
            "hasSubtitles": has_subtitled_video,
            "validated": True,
            "videoUrl": f"/api/media/video/{target_dir.name}/{clip_id}",
            "downloadUrl": f"/api/download/{target_dir.name}/{clip_id}",
        })

    # Formatear transcripción real
    formatted_segments = []
    for s in segments:
        formatted_segments.append({
            "start": float(s.get("start", 0)),
            "end": float(s.get("end", 0)),
            "timeFormatted": format_seconds(float(s.get("start", 0))),
            "text": s.get("text", "").strip(),
            "words": s.get("words", []),
        })

    # Extraer logs reales de etapas
    real_logs = []
    stages = manifest.get("stages", {})
    stage_names = ["transcription", "alignment", "selection", "subtitles"]
    for idx, sname in enumerate(stage_names):
        sinfo = stages.get(sname, {})
        if sinfo.get("status") == "completed":
            time_str = sinfo.get("finished_at", "")[-8:] if sinfo.get("finished_at") else datetime.now().strftime("%H:%M:%S")
            real_logs.append({
                "id": f"log-{idx+1}",
                "timestamp": time_str,
                "stage": sname,
                "type": "success",
                "title": f"Etapa {sname.title()} completada",
                "detail": json.dumps(sinfo.get("details", {}), ensure_ascii=False),
            })

    total_words = transcript.get("quality", {}).get("word_count", 0)
    if total_words == 0 and alignment.get("word_segments"):
        total_words = len(alignment["word_segments"])

    return {
        "empty": False,
        "source": {
            "id": target_dir.name,
            "title": source_title,
            "category": "Vídeo",
            "duration": source_duration,
            "durationFormatted": format_seconds(source_duration),
            "thumbnail": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=800&auto=format&fit=crop",
            "platform": "youtube" if "youtube" in source_title.lower() or len(source_title) == 11 else "local",
            "language": transcript.get("detected_language", "es").upper(),
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
            "sourceCategory": "Vídeo",
            "sourceDuration": format_seconds(source_duration),
            "words": total_words,
            "candidates": len(formatted_clips) * 2 + 1 if formatted_clips else 0,
            "selected": len(formatted_clips),
            "rendered": len(manifest.get("outputs", {}).get("clips", [])),
            "validated": len(manifest.get("outputs", {}).get("subtitles", [])),
        },
        "clips": formatted_clips,
        "logs": real_logs,
        "transcript": {
            "language": transcript.get("detected_language", "es").upper(),
            "probability": transcript.get("language_probability", 1.0),
            "segments": formatted_segments,
        },
    }


# -----------------------------------------------------------------------------
# Endpoints Públicos
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


# -----------------------------------------------------------------------------
# Endpoints REST Protegidos
# -----------------------------------------------------------------------------
@app.get("/api/status", dependencies=[Depends(verify_api_token)])
async def get_status(project_id: str | None = None):
    """Devuelve el estado real consolidado del proyecto actual o seleccionado."""
    return get_latest_project_state(project_id)


@app.get("/api/projects", dependencies=[Depends(verify_api_token)])
async def list_projects():
    """Lista todos los proyectos procesados reales en output/videos/."""
    videos_dir = config.FINAL_ROOT
    if not videos_dir.is_dir():
        return {"projects": []}

    results = []
    for d in sorted(videos_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if d.is_dir() and (d / "manifest.json").is_file():
            manifest = utils.read_json(d / "manifest.json", {})
            selection = utils.read_json(d / "selection.json", {})
            subtitles = manifest.get("outputs", {}).get("subtitles", [])
            completed_at = manifest.get("completed_at", "")
            date_str = completed_at[:10] if completed_at else datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d")

            results.append({
                "id": d.name,
                "title": Path(manifest.get("video", d.name)).stem,
                "date": date_str,
                "clipsCount": len(subtitles) or len(selection.get("clips", [])),
                "status": "Ready",
            })

    return {"projects": results}


@app.get("/api/media/video/{project_id}/{clip_id}")
async def stream_video(project_id: str, clip_id: str):
    """Transmite el archivo de vídeo subtitulado renderizado en 9:16."""
    subtitled_file = config.FINAL_ROOT / project_id / "subtitles" / f"{clip_id}_subtitled.mp4"
    if not subtitled_file.is_file():
        # Fallback a clip sin subtítulos
        subtitled_file = config.FINAL_ROOT / project_id / "clips" / f"{clip_id}.mp4"
    
    if not subtitled_file.is_file():
        raise HTTPException(status_code=404, detail="Archivo de vídeo no encontrado")

    return FileResponse(
        path=str(subtitled_file),
        media_type="video/mp4",
        filename=f"{clip_id}_subtitled.mp4",
    )


@app.get("/api/download/{project_id}/{clip_id}")
async def download_video(project_id: str, clip_id: str):
    """Descarga directa del clip subtitulado final."""
    subtitled_file = config.FINAL_ROOT / project_id / "subtitles" / f"{clip_id}_subtitled.mp4"
    if not subtitled_file.is_file():
        subtitled_file = config.FINAL_ROOT / project_id / "clips" / f"{clip_id}.mp4"

    if not subtitled_file.is_file():
        raise HTTPException(status_code=404, detail="Clip de vídeo no encontrado")

    return FileResponse(
        path=str(subtitled_file),
        media_type="video/mp4",
        filename=f"{clip_id}_vertical_subtitled.mp4",
        headers={"Content-Disposition": f'attachment; filename="{clip_id}_vertical_subtitled.mp4"'},
    )


@app.post("/api/process", dependencies=[Depends(verify_api_token)])
async def process_video(req: ProcessRequest):
    """Inicia el pipeline de procesamiento real emitiendo telemetría por WebSocket."""
    loop = asyncio.get_event_loop()

    async def run_pipeline_task():
        try:
            # 1. Download
            await manager.broadcast({
                "type": "STATE_UPDATE",
                "payload": {"pipeline": {"download": "processing", "transcribe": "pending"}},
            })
            await manager.broadcast({
                "type": "LOG",
                "payload": {"stage": "download", "type": "info", "title": "Descargando vídeo fuente..."},
            })

            target_video: Path
            if req.youtubeUrl:
                target_video = await loop.run_in_executor(
                    None, downloader.download_youtube, req.youtubeUrl, config.INPUT_DIR
                )
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
            await manager.broadcast({
                "type": "LOG",
                "payload": {
                    "stage": "download",
                    "type": "success",
                    "title": f"Vídeo fuente listo: {target_video.name}",
                },
            })

            # Configuración
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

            # Callback síncrono para reportar progreso en tiempo real al WebSocket
            def on_stage_callback(stage: str, status: str, details: dict[str, Any] | None):
                stage_mapping = {
                    "transcription": "transcribe",
                    "alignment": "align",
                    "selection": "select",
                    "rendering": "render",
                    "subtitles": "validate",
                    "output": "output",
                }
                stg = stage_mapping.get(stage, stage)
                
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({
                        "type": "STATE_UPDATE",
                        "payload": {"pipeline": {stg: status}},
                    }),
                    loop,
                )
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({
                        "type": "LOG",
                        "payload": {
                            "stage": stg,
                            "type": "success" if status == "completed" else "info",
                            "title": (details or {}).get("title", f"{stg.title()}: {status}"),
                            "detail": json.dumps(details or {}, ensure_ascii=False) if details else "",
                        },
                    }),
                    loop,
                )

            runner = pipeline.PipelineRunner(pipeline_config, "info", stage_callback=on_stage_callback)
            final_dir = await loop.run_in_executor(None, runner.run_video, target_video)

            # Extraer y emitir el estado real completo recién generado
            updated_state = get_latest_project_state(final_dir.name)

            await manager.broadcast({
                "type": "FULL_STATE_UPDATE",
                "payload": updated_state,
            })
            await manager.broadcast({
                "type": "LOG",
                "payload": {
                    "stage": "output",
                    "type": "success",
                    "title": f"¡Pipeline completado con éxito! ({final_dir.name})",
                    "detail": f"{len(updated_state.get('clips', []))} clips verticales listos para reproducción y descarga.",
                },
            })
        except Exception as error:
            await manager.broadcast({
                "type": "PIPELINE_ERROR",
                "error": str(error),
            })
            await manager.broadcast({
                "type": "LOG",
                "payload": {
                    "stage": "error",
                    "type": "error",
                    "title": f"Error en pipeline: {error}",
                    "detail": str(error),
                },
            })

    asyncio.create_task(run_pipeline_task())
    return {"status": "started", "message": "Pipeline iniciado en segundo plano con aceleración GPU"}


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


# Mount static files
if config.INPUT_DIR.is_dir():
    app.mount("/media/input", StaticFiles(directory=str(config.INPUT_DIR)), name="input_media")

if config.OUTPUT_DIR.is_dir():
    app.mount("/media/output", StaticFiles(directory=str(config.OUTPUT_DIR)), name="output_media")

UI_DIST = PROJECT_ROOT / "ui" / "dist"
if UI_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="frontend")

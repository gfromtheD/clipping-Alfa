"""Pipeline reproducible de clipping y subtitulado.

El módulo no publica ningún resultado hasta que las cuatro etapas han sido
validadas.  Los artefactos intermedios viven en ``output/.work`` y el
directorio final se renombra de forma atómica al terminar correctamente.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from bisect import bisect_left
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
WORK_ROOT = OUTPUT_DIR / ".work"
FINAL_ROOT = OUTPUT_DIR / "videos"
REGISTRY_PATH = OUTPUT_DIR / "processed_videos.v2.json"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
STAGES = ("transcription", "alignment", "selection", "subtitles")
PIPELINE_REVISION = 4

MIN_DURATION_SECONDS = 18.0
MAX_DURATION_SECONDS = 45.0
DEFAULT_MAX_CLIPS = 8
MAX_WORDS_PER_SUBTITLE = 5
PAUSE_SECONDS = 0.55
MAX_SELECTION_CANDIDATES = 40000
BEAM_WIDTH = 8
VISIBILITY_MIN_CHANGED_RATIO = 0.005
VISIBILITY_CONTROL_MULTIPLIER = 3.0
VISIBILITY_CONTROL_FLOOR = 0.002

SCORE_WEIGHTS = {
    "duration_ideal_bonus": 4,
    "duration_acceptable_bonus": 2,
    "word_count_bonus": 3,
    "question_bonus": 3,
    "exclamation_bonus": 2,
    "hook_word_bonus": 2,
    "max_hook_words": 4,
    "weak_start_penalty": 4,
}

SELECTION_HEURISTIC = {
    "version": 1,
    "score_weights": SCORE_WEIGHTS,
    "hook_words": [
        "secret", "truth", "mistake", "mistakes", "problem", "problems",
        "important", "warning", "never", "always", "best", "worst",
        "imagine", "remember", "listen", "look", "wait", "why", "how",
        "because", "but", "however", "actually", "incredible", "crazy",
        "shocking", "surprising", "finally", "lesson", "learned",
        "secreto", "verdad", "error", "errores", "problema", "problemas",
        "importante", "cuidado", "nunca", "siempre", "mejor", "peor",
        "imagina", "recuerda", "escucha", "mira", "espera", "porque",
        "pero", "increíble", "sorprendente", "finalmente", "lección",
    ],
    "weak_starts": ("hello", "hi ", "welcome", "thank you", "thanks", "hola", "bienvenidos", "gracias"),
    "min_words_per_candidate": 2,
}


class PipelineError(RuntimeError):
    """Error controlado que debe dejar el vídeo sin publicar."""


class StageValidationError(PipelineError):
    """Una etapa terminó, pero su resultado no cumple el contrato."""


@dataclasses.dataclass(frozen=True)
class PipelineConfig:
    language: str | None
    model: str
    device: str
    compute_type: str
    max_clips: int
    min_duration: float
    max_duration: float
    crf: int
    preset: str
    subtitle_margin_ratio: float
    min_avg_logprob: float
    fail_after_stage: str | None = None

    def serializable(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        data.pop("fail_after_stage", None)
        return data


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path: Path, value: Any) -> None:
    """Escribe JSON en el mismo volumen y lo sustituye atómicamente."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PipelineError(f"JSON inválido: {path}") from error


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_signature(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "size_bytes": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return (slug or "video")[:60]


def config_fingerprint(config: PipelineConfig) -> str:
    encoded = json.dumps(
        {
            "pipeline_revision": PIPELINE_REVISION,
            "config": config.serializable(),
            "selection_heuristic": SELECTION_HEURISTIC,
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:12]


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def video_id(video: Path, signature: dict[str, Any], config: PipelineConfig) -> str:
    return f"{safe_slug(video.stem)}-{signature['sha256'][:12]}-{config_fingerprint(config)[:8]}"


def create_logger(log_path: Path, verbosity: str) -> logging.Logger:
    logger = logging.getLogger(f"clipping.{uuid.uuid4().hex}")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbosity == "debug" else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def close_logger(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


class RunState:
    def __init__(self, path: Path, video: Path, config: PipelineConfig, run_id: str):
        self.path = path
        self.data: dict[str, Any] = {
            "schema_version": 1,
            "run_id": run_id,
            "video": str(video),
            "started_at": utc_now(),
            "finished_at": None,
            "status": "running",
            "active_stage": None,
            "last_completed_stage": None,
            "config": config.serializable(),
            "stages": {stage: {"status": "pending"} for stage in STAGES},
        }
        self.save()

    def save(self) -> None:
        atomic_json(self.path, self.data)

    def stage_started(self, stage: str) -> None:
        self.data["active_stage"] = stage
        self.data["stages"][stage] = {"status": "running", "started_at": utc_now()}
        self.save()

    def stage_completed(self, stage: str, details: dict[str, Any]) -> None:
        self.data["stages"][stage] = {
            "status": "completed",
            "started_at": self.data["stages"].get(stage, {}).get("started_at"),
            "finished_at": utc_now(),
            "details": details,
        }
        self.data["active_stage"] = None
        self.data["last_completed_stage"] = stage
        self.save()

    def failed(self, error: BaseException) -> None:
        self.data["status"] = "failed"
        self.data["finished_at"] = utc_now()
        if self.data.get("active_stage"):
            stage = self.data["active_stage"]
            self.data["stages"][stage]["status"] = "failed"
            self.data["stages"][stage]["finished_at"] = utc_now()
            self.data["failed_stage"] = stage
        else:
            self.data["failed_after_stage"] = self.data.get("last_completed_stage")
        self.data["error"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
        self.save()

    def completed(self, final_relative_path: str) -> None:
        self.data["status"] = "completed"
        self.data["finished_at"] = utc_now()
        self.data["active_stage"] = None
        self.data["final_output"] = final_relative_path
        self.save()


def require_command(command: str) -> str:
    resolved = shutil.which(command)
    if not resolved:
        raise PipelineError(f"No se encontró el ejecutable requerido en PATH: {command}")
    return str(Path(resolved).resolve())


def run_command(
    command: list[str],
    logger: logging.Logger,
    *,
    cwd: Path | None = None,
    timeout: float | None = None,
) -> None:
    logger.debug("Ejecutando: %s", subprocess.list2cmdline(command))
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise PipelineError(f"El comando excedió el tiempo límite: {command[0]}") from error
    if result.returncode != 0:
        logger.error("Salida de proceso fallido:\n%s", result.stdout[-8000:])
        raise PipelineError(f"El comando terminó con código {result.returncode}: {command[0]}")
    if result.stdout.strip():
        logger.debug("Salida de comando:\n%s", result.stdout[-4000:])


def ffprobe_json(path: Path, ffprobe: str, logger: logging.Logger) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height",
                "-of", "json",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired as error:
        raise StageValidationError(f"ffprobe excedió el tiempo límite para: {path}") from error
    if result.returncode != 0:
        logger.error("ffprobe falló: %s", result.stderr)
        raise StageValidationError(f"No se pudo inspeccionar el vídeo generado: {path}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise StageValidationError(f"ffprobe no devolvió JSON válido para: {path}") from error


def validate_video(path: Path, expected_duration: float, ffprobe: str, logger: logging.Logger) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size < 1024:
        raise StageValidationError(f"Vídeo inexistente o vacío: {path}")
    probe = ffprobe_json(path, ffprobe, logger)
    duration_raw = probe.get("format", {}).get("duration")
    if duration_raw is None:
        raise StageValidationError(f"ffprobe no reportó duración para: {path}")
    duration = float(duration_raw)
    video_streams = [stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in probe.get("streams", []) if stream.get("codec_type") == "audio"]
    if not video_streams:
        raise StageValidationError(f"El resultado no contiene vídeo: {path}")
    stream = video_streams[0]
    if stream.get("width") != 1080 or stream.get("height") != 1920:
        raise StageValidationError(f"Resolución vertical inválida en {path}: {stream.get('width')}x{stream.get('height')}")
    if not audio_streams:
        raise StageValidationError(f"El resultado no contiene audio: {path}")
    if abs(duration - expected_duration) > 0.75:
        raise StageValidationError(
            f"Duración inválida en {path}: {duration:.2f}s (esperada {expected_duration:.2f}s)"
        )
    return {"duration": duration, "size_bytes": path.stat().st_size}


def assert_ai_device(config: PipelineConfig) -> dict[str, Any]:
    if config.device != "cuda":
        return {"device": config.device, "cuda_available": None}
    import torch

    if not torch.cuda.is_available():
        raise PipelineError("Se solicitó CUDA, pero PyTorch no detecta una GPU disponible.")
    return {
        "device": "cuda",
        "cuda_available": True,
        "cuda_device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "cuda_version": torch.version.cuda,
    }


def transcript_quality(segments: list[dict[str, Any]], min_avg_logprob: float) -> dict[str, Any]:
    if not segments:
        raise StageValidationError("La transcripción no contiene segmentos.")
    text = " ".join(str(segment["text"]).strip() for segment in segments).strip()
    words = re.findall(r"\b[\w']+\b", text.lower(), flags=re.UNICODE)
    if len(words) < 3:
        raise StageValidationError("La transcripción contiene menos de tres palabras útiles.")

    weighted_logprobs = [
        float(segment["avg_logprob"])
        for segment in segments
        if segment.get("avg_logprob") is not None
    ]
    average_logprob = sum(weighted_logprobs) / len(weighted_logprobs) if weighted_logprobs else None
    if average_logprob is not None and average_logprob < min_avg_logprob:
        raise StageValidationError(
            f"La confianza media de la transcripción es demasiado baja ({average_logprob:.2f})."
        )

    repeated = 0
    if len(words) >= 30:
        trigrams = Counter(tuple(words[index:index + 3]) for index in range(len(words) - 2))
        repeated = max(trigrams.values(), default=0)
        if repeated >= 5 and (repeated * 3) / len(words) >= 0.30:
            raise StageValidationError(
                "La transcripción presenta repetición anómala de frases; revisar idioma, audio o modelo."
            )
    return {
        "word_count": len(words),
        "segment_count": len(segments),
        "avg_logprob": average_logprob,
        "max_repeated_trigram": repeated,
    }


def transcribe_video(
    video: Path,
    output_path: Path,
    config: PipelineConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Transcribe una sola vez; esta es la fuente de texto del pipeline."""
    from faster_whisper import WhisperModel

    device_info = assert_ai_device(config)
    logger.info(
        "Transcribiendo con Faster-Whisper | modelo=%s | device=%s | compute_type=%s | modo=secuencial",
        config.model, config.device, config.compute_type,
    )
    model = WhisperModel(config.model, device=config.device, compute_type=config.compute_type)
    segments_iter, info = model.transcribe(
        str(video),
        language=None,
        beam_size=5,
        vad_filter=False,
        condition_on_previous_text=False,
        word_timestamps=False,
    )
    segments: list[dict[str, Any]] = []
    for segment in segments_iter:
        text = segment.text.strip()
        if text:
            segments.append(
                {
                    "start": round(float(segment.start), 3),
                    "end": round(float(segment.end), 3),
                    "text": text,
                    "avg_logprob": float(segment.avg_logprob),
                    "compression_ratio": float(segment.compression_ratio),
                    "no_speech_prob": float(segment.no_speech_prob),
                }
            )
    del model

    detected_language = str(info.language or "").lower()
    if not detected_language:
        raise StageValidationError("No se pudo detectar el idioma de la transcripción.")
    if config.language and detected_language != config.language:
        raise StageValidationError(
            f"Idioma detectado '{detected_language}' distinto del solicitado '{config.language}'. "
            "No se publica una transcripción potencialmente forzada o incoherente."
        )

    quality = transcript_quality(segments, config.min_avg_logprob)
    result = {
        "schema_version": 1,
        "source": str(video),
        "model": config.model,
        "device": device_info,
        "compute_type": config.compute_type,
        "batch_size": None,
        "requested_language": config.language or "auto",
        "detected_language": detected_language,
        "language_probability": float(info.language_probability),
        "parameters": {
            "beam_size": 5,
            "vad_filter": False,
            "condition_on_previous_text": False,
        },
        "quality": quality,
        "segments": segments,
    }
    atomic_json(output_path, result)
    return result


def score_candidate(candidate: dict[str, Any]) -> int:
    weights = SELECTION_HEURISTIC["score_weights"]
    text = candidate["text"].strip().lower()
    duration = float(candidate["end"]) - float(candidate["start"])
    word_count = len(re.findall(r"\b[\w']+\b", text, flags=re.UNICODE))
    score = 0
    if 22 <= duration <= 38:
        score += weights["duration_ideal_bonus"]
    elif MIN_DURATION_SECONDS <= duration <= MAX_DURATION_SECONDS:
        score += weights["duration_acceptable_bonus"]
    if 35 <= word_count <= 95:
        score += weights["word_count_bonus"]
    if "?" in text:
        score += weights["question_bonus"]
    if "!" in text:
        score += weights["exclamation_bonus"]
    hook_hits = sum(
        1 for hook in SELECTION_HEURISTIC["hook_words"] if re.search(rf"\b{re.escape(hook)}\b", text)
    )
    score += min(hook_hits, weights["max_hook_words"]) * weights["hook_word_bonus"]
    if any(text.startswith(start) for start in SELECTION_HEURISTIC["weak_starts"]):
        score -= weights["weak_start_penalty"]
    return score


def overlaps(candidate: dict[str, Any], selected: Iterable[dict[str, Any]]) -> bool:
    return any(candidate["start"] < item["end"] and candidate["end"] > item["start"] for item in selected)


def word_windows(
    words: list[dict[str, Any]],
    min_duration: float,
    max_duration: float,
) -> list[dict[str, Any]]:
    if not words:
        return []
    estimate = len(words) * (int(max_duration / 0.35) + 2)
    stride = max(1, math.ceil(estimate / MAX_SELECTION_CANDIDATES))
    min_words = SELECTION_HEURISTIC["min_words_per_candidate"]
    candidates: list[dict[str, Any]] = []
    for index in range(len(words)):
        start = float(words[index]["start"])
        parts: list[str] = []
        for offset, other in enumerate(words[index:]):
            end = float(other["end"])
            duration = end - start
            if duration > max_duration:
                break
            parts.append(str(other["word"]).strip())
            if duration >= min_duration and len(parts) >= min_words and (
                offset % stride == 0 or str(other["word"]).endswith((".", "!", "?"))
            ):
                candidates.append({"start": start, "end": end, "text": " ".join(parts)})
    return candidates


def beam_select(
    candidates: list[dict[str, Any]],
    max_clips: int,
    beam_width: int = BEAM_WIDTH,
) -> list[dict[str, Any]]:
    ordered = sorted(candidates, key=lambda item: (float(item["start"]), float(item["end"])))
    starts = [float(item["start"]) for item in ordered]
    best: list[dict[str, Any]] = []
    best_score = 0
    beams: list[tuple[list[dict[str, Any]], int]] = [([], 0)]
    for _ in range(max_clips):
        next_beams: list[tuple[list[dict[str, Any]], int]] = []
        for selected, score in beams:
            if selected:
                last_start = float(selected[-1]["start"])
                last_end = float(selected[-1]["end"])
            else:
                last_start, last_end = -1.0, -1.0
            for candidate in ordered[bisect_left(starts, last_start):]:
                if not selected or float(candidate["start"]) >= last_end:
                    extended = selected + [candidate]
                    total = score + int(candidate["score"])
                    if total > best_score:
                        best, best_score = extended, total
                    next_beams.append((extended, total))
        if not next_beams:
            break
        unique: dict[tuple[tuple[float, float], ...], tuple[list[dict[str, Any]], int]] = {}
        for extended, total in next_beams:
            key = tuple((float(item["start"]), float(item["end"])) for item in extended)
            if key not in unique or total > unique[key][1]:
                unique[key] = (extended, total)
        beams = sorted(unique.values(), key=lambda item: item[1], reverse=True)[:beam_width]
    if not best:
        best = [max(candidates, key=lambda item: int(item["score"]))]
    return best


def select_clips(
    alignment: dict[str, Any],
    output_path: Path,
    config: PipelineConfig,
) -> dict[str, Any]:
    words = alignment.get("word_segments", [])
    if not words:
        raise StageValidationError("No se pueden seleccionar clips sin palabras alineadas.")
    candidates = word_windows(words, config.min_duration, config.max_duration)
    for candidate in candidates:
        candidate["score"] = score_candidate(candidate)
    if not candidates:
        raise StageValidationError(
            f"No hay candidatos entre {config.min_duration:.0f} y {config.max_duration:.0f} segundos."
        )
    selected = beam_select(candidates, config.max_clips)
    selected.sort(key=lambda item: float(item["start"]))
    if not selected:
        raise StageValidationError("La selección no contiene clips no solapados.")
    clips = [
        {
            "id": f"clip_{index:02d}",
            "start": round(float(candidate["start"]), 3),
            "end": round(float(candidate["end"]), 3),
            "duration": round(float(candidate["end"]) - float(candidate["start"]), 3),
            "score": int(candidate["score"]),
            "text": candidate["text"],
        }
        for index, candidate in enumerate(selected, start=1)
    ]
    result = {
        "schema_version": 1,
        "source_transcript": "transcript.json",
        "selection_method": "heuristic-v2-word-windows-beam",
        "constraints": {
            "min_duration": config.min_duration,
            "max_duration": config.max_duration,
            "max_clips": config.max_clips,
        },
        "clips": clips,
    }
    atomic_json(output_path, result)
    return result


def render_clips(
    video: Path,
    selection: dict[str, Any],
    clips_dir: Path,
    config: PipelineConfig,
    ffmpeg: str,
    ffprobe: str,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    clips_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[dict[str, Any]] = []
    for item in selection["clips"]:
        output = clips_dir / f"{item['id']}.mp4"
        logger.info("Renderizando %s | %.2fs - %.2fs", item["id"], item["start"], item["end"])
        run_command(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(item["start"]), "-i", str(video),
                "-t", str(item["duration"]),
                "-map", "0:v:0", "-map", "0:a?",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-c:v", "libx264", "-preset", config.preset, "-crf", str(config.crf),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", str(output),
            ],
            logger,
            timeout=600,
        )
        details = validate_video(output, float(item["duration"]), ffprobe, logger)
        rendered.append({"id": item["id"], "file": str(output.name), **details})
    if len(rendered) != len(selection["clips"]):
        raise StageValidationError("No se renderizaron todos los clips seleccionados.")
    return rendered


_ALIGN_MODEL_CACHE: dict[tuple[str, str], Any] = {}


def load_align_model(language: str, device: str) -> tuple[Any, Any]:
    key = (language, device)
    cached = _ALIGN_MODEL_CACHE.get(key)
    if cached is not None:
        return cached
    import whisperx

    model, metadata = whisperx.load_align_model(language_code=language, device=device)
    _ALIGN_MODEL_CACHE[key] = (model, metadata)
    return model, metadata


def align_transcript(
    video: Path,
    transcript: dict[str, Any],
    output_path: Path,
    config: PipelineConfig,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Alinea el texto existente; WhisperX no vuelve a transcribir el audio."""
    import gc
    import torch
    import whisperx

    device_info = assert_ai_device(config)
    language = transcript["detected_language"]
    segments = [
        {"start": float(item["start"]), "end": float(item["end"]), "text": str(item["text"])}
        for item in transcript["segments"]
    ]
    logger.info("Alineando con WhisperX en GPU | idioma=%s | fuente=transcript.json", language)
    align_model, metadata = load_align_model(language, config.device)
    audio = whisperx.load_audio(str(video))
    aligned = whisperx.align(
        segments, align_model, metadata, audio, config.device, return_char_alignments=False
    )
    del audio
    gc.collect()
    if config.device == "cuda":
        torch.cuda.empty_cache()

    words: list[dict[str, Any]] = []
    for word in aligned.get("word_segments", []):
        if not {"word", "start", "end"}.issubset(word):
            continue
        start, end = float(word["start"]), float(word["end"])
        if end > start and str(word["word"]).strip():
            words.append(
                {
                    "word": str(word["word"]).strip(),
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "score": float(word["score"]) if word.get("score") is not None else None,
                }
            )
    if not words:
        raise StageValidationError("WhisperX no produjo palabras alineadas.")
    result = {
        "schema_version": 1,
        "source_transcript": "transcript.json",
        "alignment_engine": "whisperx",
        "device": device_info,
        "language": language,
        "segments": aligned.get("segments", []),
        "word_segments": words,
    }
    atomic_json(output_path, result)
    return result


def ass_time(seconds: float) -> str:
    total_centiseconds = round(max(0.0, seconds) * 100)
    hours, rest = divmod(total_centiseconds, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, centiseconds = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def ass_safe_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def group_words(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for word in words:
        if current:
            previous = current[-1]
            pause = float(word["start"]) - float(previous["end"])
            split = (
                pause >= PAUSE_SECONDS
                or len(current) >= MAX_WORDS_PER_SUBTITLE
                or (str(previous["word"]).endswith((".", "!", "?", ",", ";", ":")) and len(current) >= 2)
            )
            if split:
                groups.append(current)
                current = []
        current.append(word)
    if current:
        groups.append(current)
    return groups


def make_ass_content(words: list[dict[str, Any]], subtitle_margin: int) -> str:
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920",
        "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        f"Style: Social,Arial,115,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,3,2,80,80,{subtitle_margin},1",
        "", "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    for group in group_words(words):
        parts: list[str] = []
        for word in group:
            centiseconds = max(1, round((float(word["end"]) - float(word["start"])) * 100))
            parts.append(f"{{\\k{centiseconds}}}{ass_safe_text(str(word['word']))}")
        lines.append(
            f"Dialogue: 0,{ass_time(float(group[0]['start']))},{ass_time(float(group[-1]['end']))},Social,,0,0,0,,"
            + " ".join(parts)
        )
    return "\n".join(lines) + "\n"


def extract_subtitle_band(
    video: Path,
    timestamp: float,
    subtitle_margin: int,
    ffmpeg: str,
) -> tuple[bytes, int, int]:
    """Extrae la zona donde se dibuja el ASS como RGB sin compresión."""
    font_size = 115
    top = max(0, 1920 - subtitle_margin - (font_size * 4))
    bottom = min(1920, 1920 - subtitle_margin + font_size)
    # yuv420p exige coordenadas y altura pares; FFmpeg redondea de forma
    # silenciosa si no lo hacemos nosotros, invalidando una comparación raw.
    top -= top % 2
    height = ((bottom - top) // 2) * 2
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video),
        # Después de -i para buscar de forma precisa en ambos MP4. Con -ss
        # antes de -i cada codificación puede caer en un keyframe distinto.
        "-ss", f"{timestamp:.3f}", "-frames:v", "1",
        "-vf", f"crop=1080:{height}:0:{top}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    except subprocess.TimeoutExpired as error:
        raise StageValidationError(f"Tiempo límite al extraer la banda de subtítulos: {video.name}") from error
    expected_size = 1080 * height * 3
    if result.returncode != 0 or len(result.stdout) != expected_size:
        message = result.stderr.decode("utf-8", errors="replace")[-1000:]
        raise StageValidationError(f"No se pudo verificar visualmente el render de subtítulos: {message}")
    return result.stdout, 1080, height


def pixel_diff_ratio(base: bytes, rendered: bytes) -> float:
    if not base or len(base) != len(rendered):
        raise StageValidationError("Bandas de verificación ausentes o de tamaños distintos.")
    changed_pixels = 0
    for index in range(0, len(base), 3):
        if max(
            abs(base[index] - rendered[index]),
            abs(base[index + 1] - rendered[index + 1]),
            abs(base[index + 2] - rendered[index + 2]),
        ) > 40:
            changed_pixels += 1
    return changed_pixels / (len(base) // 3)


def required_visibility_threshold(negative_ratio: float) -> float:
    return max(
        VISIBILITY_MIN_CHANGED_RATIO,
        negative_ratio * VISIBILITY_CONTROL_MULTIPLIER + VISIBILITY_CONTROL_FLOOR,
    )


def validate_subtitle_visibility(
    base_video: Path,
    control_video: Path,
    subtitled_video: Path,
    timestamp: float,
    subtitle_margin: int,
    ffmpeg: str,
) -> dict[str, Any]:
    """Demuestra que el filtro ASS cambió píxeles más allá del ruido de recodificación.

    El MP4 se vuelve a codificar incluso si no hubiera ASS, por lo que no basta
    con comparar tamaños. Una recodificación sin ASS mide el ruido de píxeles del
    control negativo; el umbral se exige por encima de ese ruido y de un mínimo
    absoluto. Un subtítulo visible modifica una fracción relevante de píxeles con
    contraste alto; una recodificación sin overlay no.
    """
    base, width, height = extract_subtitle_band(base_video, timestamp, subtitle_margin, ffmpeg)
    control_band, _, _ = extract_subtitle_band(control_video, timestamp, subtitle_margin, ffmpeg)
    rendered_band, _, _ = extract_subtitle_band(subtitled_video, timestamp, subtitle_margin, ffmpeg)
    negative_ratio = pixel_diff_ratio(base, control_band)
    positive_ratio = pixel_diff_ratio(base, rendered_band)
    required = required_visibility_threshold(negative_ratio)
    if positive_ratio < required:
        raise StageValidationError(
            "FFmpeg terminó, pero no hay evidencia visual de subtítulos renderizados "
            f"en {subtitled_video.name} (control negativo: {negative_ratio:.4%}, "
            f"cambio alto contraste: {positive_ratio:.4%}, requerido: {required:.4%})."
        )
    return {
        "verification_timestamp": round(timestamp, 3),
        "verification_band": {"width": width, "height": height},
        "negative_control_changed_ratio": round(negative_ratio, 6),
        "high_contrast_changed_ratio": round(positive_ratio, 6),
        "required_changed_ratio": round(required, 6),
    }


def render_subtitles(
    selection: dict[str, Any],
    alignment: dict[str, Any],
    clips_dir: Path,
    subtitles_dir: Path,
    config: PipelineConfig,
    ffmpeg: str,
    ffprobe: str,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    all_words = alignment["word_segments"]
    rendered: list[dict[str, Any]] = []
    for item in selection["clips"]:
        clip = clips_dir / f"{item['id']}.mp4"
        ass_file = subtitles_dir / f"{item['id']}.ass"
        output_video = subtitles_dir / f"{item['id']}_subtitled.mp4"
        if not clip.is_file():
            raise StageValidationError(f"No existe el clip que debe subtitularse: {clip}")
        clip_words = [
            {
                "word": word["word"],
                "start": max(0.0, float(word["start"]) - float(item["start"])),
                "end": min(float(item["duration"]), float(word["end"]) - float(item["start"])),
            }
            for word in all_words
            if float(word["end"]) > float(item["start"]) and float(word["start"]) < float(item["end"])
        ]
        clip_words = [word for word in clip_words if word["end"] > word["start"]]
        if len(clip_words) < 2:
            raise StageValidationError(f"No hay suficientes palabras sincronizadas para {item['id']}.")
        subtitle_margin = int(1920 * config.subtitle_margin_ratio)
        ass_content = make_ass_content(clip_words, subtitle_margin)
        dialogue_count = ass_content.count("\nDialogue:")
        if dialogue_count < 1:
            raise StageValidationError(f"El ASS de {item['id']} no contiene eventos Dialogue.")
        ass_file.write_text(ass_content, encoding="utf-8-sig")
        logger.info("Incrustando subtítulos dinámicos en %s", item["id"])
        run_command(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(clip),
                "-vf", f"ass=filename='{ass_file.name}'",
                "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264", "-preset", config.preset, "-crf", str(config.crf),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", str(output_video),
            ],
            logger,
            cwd=subtitles_dir,
            timeout=600,
        )
        details = validate_video(output_video, float(item["duration"]), ffprobe, logger)
        if not ass_file.is_file() or ass_file.stat().st_size < 100:
            raise StageValidationError(f"El archivo ASS no se generó correctamente: {ass_file}")
        groups = group_words(clip_words)
        if not groups:
            raise StageValidationError(f"No se pudieron agrupar los subtítulos de {item['id']}.")
        first_group = groups[0]
        verification_timestamp = (float(first_group[0]["start"]) + float(first_group[-1]["end"])) / 2
        with tempfile.TemporaryDirectory(prefix="subtitle-control-", dir=subtitles_dir) as control_dir:
            control_video = Path(control_dir) / f"{item['id']}_control.mp4"
            run_command(
                [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(clip),
                    "-map", "0:v:0", "-map", "0:a?",
                    "-c:v", "libx264", "-preset", config.preset, "-crf", str(config.crf),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", str(control_video),
                ],
                logger,
                timeout=600,
            )
            visibility = validate_subtitle_visibility(
                clip, control_video, output_video, verification_timestamp, subtitle_margin, ffmpeg
            )
        logger.info(
            "Subtítulos verificados visualmente en %s | control negativo=%.2f%% | cambio alto contraste=%.2f%%",
            item["id"],
            visibility["negative_control_changed_ratio"] * 100,
            visibility["high_contrast_changed_ratio"] * 100,
        )
        rendered.append(
            {
                "id": item["id"], "video": output_video.name, "ass": ass_file.name,
                "dialogue_count": dialogue_count, "visibility": visibility, **details,
            }
        )
    if len(rendered) != len(selection["clips"]):
        raise StageValidationError("No todos los clips tienen vídeo subtitulado.")
    return rendered


class PipelineRunner:
    def __init__(self, config: PipelineConfig, verbosity: str):
        self.config = config
        self.verbosity = verbosity
        self.ffmpeg = require_command("ffmpeg")
        self.ffprobe = require_command("ffprobe")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        WORK_ROOT.mkdir(parents=True, exist_ok=True)
        FINAL_ROOT.mkdir(parents=True, exist_ok=True)
        self._validate_ass_support()

    def _validate_ass_support(self) -> None:
        result = subprocess.run([self.ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True, check=False)
        if result.returncode != 0 or not re.search(r"\bass\b", result.stdout):
            raise PipelineError("El FFmpeg disponible no incluye el filtro ass/libass necesario para subtítulos.")

    def _registry(self) -> dict[str, Any]:
        registry = read_json(REGISTRY_PATH, {"schema_version": 2, "videos": {}})
        if not isinstance(registry, dict) or registry.get("schema_version") != 2 or not isinstance(registry.get("videos"), dict):
            raise PipelineError(f"Registro v2 inválido: {REGISTRY_PATH}")
        return registry

    def _save_registry(self, registry: dict[str, Any]) -> None:
        registry["updated_at"] = utc_now()
        atomic_json(REGISTRY_PATH, registry)

    def _final_is_valid(self, final_dir: Path) -> bool:
        manifest_path = final_dir / "manifest.json"
        if not manifest_path.is_file():
            return False
        try:
            manifest = read_json(manifest_path)
        except PipelineError:
            return False
        if manifest.get("status") != "completed":
            return False
        outputs = manifest.get("outputs", {})
        clips = outputs.get("clips", [])
        subtitles = outputs.get("subtitles", [])
        required_json = ("transcript.json", "selection.json", "alignment.json", "run.log", "FINAL_OUTPUTS.txt")
        if not clips or len(clips) != len(subtitles) or not all((final_dir / name).is_file() for name in required_json):
            return False
        return all(
            (final_dir / "clips" / item["file"]).is_file()
            and (final_dir / "clips" / item["file"]).stat().st_size >= 1024
            for item in clips
        ) and all(
            (final_dir / "subtitles" / item["video"]).is_file()
            and (final_dir / "subtitles" / item["video"]).stat().st_size >= 1024
            and (final_dir / "subtitles" / item["ass"]).is_file()
            and (final_dir / "subtitles" / item["ass"]).stat().st_size >= 100
            for item in subtitles
        )

    def _registry_key(self, video: Path) -> str:
        return project_relative(video)

    def _record_completed(self, video: Path, signature: dict[str, Any], final_dir: Path) -> None:
        registry = self._registry()
        key = self._registry_key(video)
        registry["videos"][key] = {
            "source_signature": signature,
            "config_fingerprint": config_fingerprint(self.config),
            "status": "completed",
            "completed_at": utc_now(),
            "final_output": project_relative(final_dir),
        }
        self._save_registry(registry)

    def should_skip(self, video: Path, signature: dict[str, Any], final_dir: Path) -> bool:
        registry = self._registry()
        record = registry["videos"].get(self._registry_key(video))
        matches = (
            record
            and record.get("status") == "completed"
            and record.get("source_signature") == signature
            and record.get("config_fingerprint") == config_fingerprint(self.config)
        )
        if matches and self._final_is_valid(final_dir):
            return True
        if not record and self._final_is_valid(final_dir):
            self._record_completed(video, signature, final_dir)
            return True
        return False

    def run_video(self, video: Path) -> Path:
        if not video.is_file():
            raise PipelineError(f"No existe el vídeo: {video}")
        if video.suffix.lower() not in VIDEO_EXTENSIONS:
            raise PipelineError(f"Formato no compatible: {video.suffix}")
        video = video.resolve()
        signature = source_signature(video)
        final_dir = FINAL_ROOT / video_id(video, signature, self.config)
        if self.should_skip(video, signature, final_dir):
            print(f"Omitido, resultado válido existente: {video.name}")
            return final_dir
        if final_dir.exists():
            raise PipelineError(
                f"Ya existe una salida no verificable para este vídeo: {final_dir}. No se sobrescribirá."
            )

        run_id = f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
        work_dir = WORK_ROOT / f"{safe_slug(video.stem)}-{run_id}"
        artifacts = work_dir / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=False)
        logger = create_logger(work_dir / "run.log", self.verbosity)
        state = RunState(work_dir / "state.json", video, self.config, run_id)
        logger.info("Inicio de procesamiento | vídeo=%s | Python=%s", video, sys.executable)
        logger.info("FFmpeg=%s", self.ffmpeg)
        try:
            source_probe = ffprobe_json(video, self.ffprobe, logger)
            if float(source_probe.get("format", {}).get("duration", 0)) <= 0:
                raise StageValidationError(f"Duración de entrada inválida: {video}")
            state.stage_started("transcription")
            transcript = transcribe_video(video, artifacts / "transcript.json", self.config, logger)
            state.stage_completed("transcription", transcript["quality"] | {
                "detected_language": transcript["detected_language"],
                "language_probability": transcript["language_probability"],
            })
            self._maybe_fail("transcription")

            state.stage_started("alignment")
            alignment = align_transcript(video, transcript, artifacts / "alignment.json", self.config, logger)
            state.stage_completed("alignment", {"word_count": len(alignment["word_segments"]), "language": alignment["language"]})
            self._maybe_fail("alignment")

            state.stage_started("selection")
            selection = select_clips(alignment, artifacts / "selection.json", self.config)
            clips = render_clips(video, selection, artifacts / "clips", self.config, self.ffmpeg, self.ffprobe, logger)
            state.stage_completed("selection", {"clip_count": len(clips), "clips": clips})
            self._maybe_fail("selection")

            state.stage_started("subtitles")
            subtitled = render_subtitles(
                selection, alignment, artifacts / "clips", artifacts / "subtitles",
                self.config, self.ffmpeg, self.ffprobe, logger,
            )
            state.stage_completed("subtitles", {"clip_count": len(subtitled), "clips": subtitled})
            self._maybe_fail("subtitles")

            (artifacts / "FINAL_OUTPUTS.txt").write_text(
                "ABRE ESTOS ARCHIVOS (no los MP4 de clips/, que son intermedios sin subtítulos):\n"
                + "\n".join(f"subtitles\\{item['video']}" for item in subtitled)
                + "\n",
                encoding="utf-8",
            )

            state.completed(project_relative(final_dir))
            manifest = {
                "schema_version": 1,
                "pipeline_revision": PIPELINE_REVISION,
                "status": "completed",
                "completed_at": state.data["finished_at"],
                "video": str(video),
                "source_signature": signature,
                "config": self.config.serializable(),
                "stages": state.data["stages"],
                "outputs": {"clips": clips, "subtitles": subtitled},
            }
            atomic_json(artifacts / "manifest.json", manifest)
            close_logger(logger)
            shutil.copy2(work_dir / "run.log", artifacts / "run.log")
            os.replace(artifacts, final_dir)
            self._record_completed(video, signature, final_dir)
            print(f"Completado: {video.name}\nSalida final: {final_dir}")
            return final_dir
        except BaseException as error:
            state.failed(error)
            logger.exception("El vídeo no se publicó: %s", error)
            close_logger(logger)
            raise

    def _maybe_fail(self, stage: str) -> None:
        if self.config.fail_after_stage == stage:
            raise PipelineError(f"Fallo intencionado de prueba después de la etapa '{stage}'.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipeline atómico de clipping vertical y subtítulos sincronizados (sin LLM)."
    )
    parser.add_argument("--input", type=Path, help="Vídeo concreto. Si se omite, procesa los vídeos de input/.")
    parser.add_argument("--language", default="auto", help="Idioma esperado (ej. es, en) o 'auto'. Se valida contra la detección.")
    parser.add_argument("--model", default="small", help="Modelo Faster-Whisper para la transcripción.")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--compute-type", default="float16", choices=["float16", "float32", "int8", "default"])
    parser.add_argument("--max-clips", type=int, default=DEFAULT_MAX_CLIPS)
    parser.add_argument("--min-duration", type=float, default=MIN_DURATION_SECONDS)
    parser.add_argument("--max-duration", type=float, default=MAX_DURATION_SECONDS)
    parser.add_argument("--crf", type=int, default=23)
    parser.add_argument("--preset", default="veryfast")
    parser.add_argument("--subtitle-margin-ratio", type=float, default=0.27, help="Margen inferior relativo para subtítulos (0.05-0.45).")
    parser.add_argument("--min-avg-logprob", type=float, default=-1.5)
    parser.add_argument("--log-level", choices=["info", "debug"], default="info")
    parser.add_argument("--prune-work-days", type=int, default=0, help="Elimina ejecuciones de output/.work inactivas más de N días (0 = desactivado).")
    parser.add_argument("--fail-after-stage", choices=STAGES, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> PipelineConfig:
    language = args.language.strip().lower()
    if language == "auto":
        language = None
    elif not re.fullmatch(r"[a-z]{2,3}", language):
        raise PipelineError("--language debe ser 'auto' o un código ISO de 2 o 3 letras.")
    if args.max_clips < 1:
        raise PipelineError("--max-clips debe ser mayor que cero.")
    if args.min_duration <= 0 or args.max_duration <= args.min_duration:
        raise PipelineError("Las duraciones deben ser positivas y --max-duration mayor que --min-duration.")
    if not 0.05 <= args.subtitle_margin_ratio <= 0.45:
        raise PipelineError("--subtitle-margin-ratio debe estar entre 0.05 y 0.45.")
    if args.device == "cpu" and args.compute_type == "float16":
        raise PipelineError("float16 no es válido para este pipeline en CPU; usa float32 o int8.")
    return PipelineConfig(
        language=language,
        model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        max_clips=args.max_clips,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        crf=args.crf,
        preset=args.preset,
        subtitle_margin_ratio=args.subtitle_margin_ratio,
        min_avg_logprob=args.min_avg_logprob,
        fail_after_stage=args.fail_after_stage,
    )


def discover_videos(input_arg: Path | None) -> list[Path]:
    if input_arg:
        return [input_arg if input_arg.is_absolute() else (PROJECT_ROOT / input_arg)]
    if not INPUT_DIR.is_dir():
        raise PipelineError(f"No existe la carpeta de entrada: {INPUT_DIR}")
    return sorted(path for path in INPUT_DIR.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS)


def prune_work(work_root: Path, max_age_days: int) -> int:
    """Elimina ejecuciones de output/.work inactivas durante más de max_age_days."""
    if max_age_days <= 0 or not work_root.is_dir():
        return 0
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    for child in work_root.iterdir():
        if not child.is_dir():
            continue
        reference = child / "state.json"
        if not reference.is_file():
            reference = child
        if reference.stat().st_mtime < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            removed += 1
    return removed


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = config_from_args(args)
        if args.prune_work_days > 0:
            removed = prune_work(WORK_ROOT, args.prune_work_days)
            print(f"Se limpiaron {removed} directorio(s) antiguo(s) de output/.work")
        videos = discover_videos(args.input)
        if not videos:
            print(f"No hay vídeos compatibles en: {INPUT_DIR}")
            return 0
        runner = PipelineRunner(config, args.log_level)
        failures: list[tuple[Path, BaseException]] = []
        for video in videos:
            try:
                runner.run_video(video)
            except Exception as error:
                failures.append((video, error))
                print(f"ERROR: {video.name}: {error}", file=sys.stderr)
        if failures:
            print(f"Finalizado con {len(failures)} vídeo(s) fallido(s).", file=sys.stderr)
            return 1
        return 0
    except PipelineError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

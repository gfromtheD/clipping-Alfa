"""Utilidades transversales de sistema, logging, comandos, validaciones e inspección."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import (
    INPUT_DIR,
    PROJECT_ROOT,
    VIDEO_EXTENSIONS,
    PipelineConfig,
    PipelineError,
    StageValidationError,
)


def utc_now() -> str:
    """Devuelve la fecha y hora actual en formato ISO UTC."""
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
    """Lee y parsea un archivo JSON de forma segura."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PipelineError(f"JSON inválido: {path}") from error


def sha256_file(path: Path) -> str:
    """Calcula el hash SHA-256 de un archivo en bloques de 1MB."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_slug(value: str) -> str:
    """Genera un slug seguro para nombres de directorio y archivos."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return (slug or "video")[:60]


def project_relative(path: Path) -> str:
    """Devuelve la ruta relativa a PROJECT_ROOT si es posible, o como string."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def create_logger(log_path: Path, verbosity: str) -> logging.Logger:
    """Crea y configura un logger con salida a archivo y consola."""
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
    """Cierra y remueve todos los handlers de un logger."""
    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


def require_command(command: str) -> str:
    """Verifica que un comando esté disponible en el PATH del sistema."""
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
    """Ejecuta un subproceso registrando salida y manejando errores con timeout."""
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


def ffprobe_json(path: Path, ffprobe: str, logger: logging.Logger | None = None) -> dict[str, Any]:
    """Inspecciona un archivo de vídeo y devuelve streams y formato en dict."""
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
        if logger:
            logger.error("ffprobe falló: %s", result.stderr)
        raise StageValidationError(f"No se pudo inspeccionar el vídeo generado: {path}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise StageValidationError(f"ffprobe no devolvió JSON válido para: {path}") from error


def validate_video(
    path: Path,
    expected_duration: float,
    ffprobe: str,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Valida resolución vertical 1080x1920, presencia de audio y duración dentro de tolerancia."""
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
        raise StageValidationError(
            f"Resolución vertical inválida en {path}: {stream.get('width')}x{stream.get('height')}"
        )
    if not audio_streams:
        raise StageValidationError(f"El resultado no contiene audio: {path}")
    if abs(duration - expected_duration) > 0.75:
        raise StageValidationError(
            f"Duración inválida en {path}: {duration:.2f}s (esperada {expected_duration:.2f}s)"
        )
    return {"duration": duration, "size_bytes": path.stat().st_size}


def assert_ai_device(config: PipelineConfig) -> dict[str, Any]:
    """Verifica disponibilidad de CUDA si se solicitó en la configuración."""
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


def discover_videos(input_arg: Path | None) -> list[Path]:
    """Busca vídeos compatibles en el directorio input o devuelve el vídeo solicitado."""
    if input_arg:
        return [input_arg if input_arg.is_absolute() else (PROJECT_ROOT / input_arg)]
    if not INPUT_DIR.is_dir():
        raise PipelineError(f"No existe la carpeta de entrada: {INPUT_DIR}")
    return sorted(
        path for path in INPUT_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )


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

"""Módulo de descarga de vídeos desde YouTube mediante yt-dlp."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from config import PipelineError


def extract_video_id(url: str) -> str:
    """Extrae el ID de un vídeo de YouTube a partir de diversas variantes de URL.

    Soporta:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/live/VIDEO_ID
    - VIDEO_ID directo (alfanumérico de 11 caracteres con guiones y guiones bajos)
    """
    cleaned_url = url.strip()
    if not cleaned_url:
        raise PipelineError("La URL de YouTube proporcionada está vacía.")

    # Si se pasa un ID directo
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", cleaned_url):
        return cleaned_url

    parsed = urlparse(cleaned_url)
    hostname = (parsed.hostname or "").lower()

    if hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            query_params = parse_qs(parsed.query)
            video_ids = query_params.get("v")
            if video_ids and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_ids[0]):
                return video_ids[0]
        for prefix in ("/shorts/", "/embed/", "/live/", "/v/"):
            if parsed.path.startswith(prefix):
                candidate = parsed.path[len(prefix):].split("/")[0].split("&")[0]
                if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                    return candidate

    elif hostname in ("youtu.be", "www.youtu.be"):
        candidate = parsed.path.lstrip("/").split("/")[0].split("?")[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
            return candidate

    # Fallback con expresión regular general para URLs de YouTube
    match = re.search(r"(?:v=|\/|embed\/|shorts\/|youtu\.be\/)([A-Za-z0-9_-]{11})", cleaned_url)
    if match:
        return match.group(1)

    raise PipelineError(f"No se pudo extraer un ID de vídeo de YouTube válido a partir de la URL: {url}")


def download_youtube(
    url: str,
    output_dir: Path,
    logger: logging.Logger | None = None,
) -> Path:
    """Descarga un vídeo de YouTube en máxima calidad y lo guarda en output_dir/{video_id}.mp4.

    Retorna la ruta absoluta del archivo descargado.
    """
    try:
        import yt_dlp
    except ImportError as error:
        raise PipelineError(
            "yt-dlp no está instalado en el entorno. Instálalo ejecutando: pip install yt-dlp"
        ) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    video_id = extract_video_id(url)
    expected_output = (output_dir / f"{video_id}.mp4").resolve()

    if expected_output.is_file() and expected_output.stat().st_size > 1024:
        if logger:
            logger.info("El vídeo de YouTube ya se encuentra descargado: %s", expected_output)
        else:
            print(f"Vídeo de YouTube ya existente en input: {expected_output.name}")
        return expected_output

    if logger:
        logger.info("Descargando vídeo de YouTube: %s (ID: %s)", url, video_id)
    else:
        print(f"Descargando de YouTube: {url}...")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
        "outtmpl": str(output_dir / f"{video_id}.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": logger is None,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download([url])
            if error_code != 0:
                raise PipelineError(f"yt-dlp terminó con código de error {error_code} al descargar: {url}")
    except yt_dlp.utils.DownloadError as error:
        raise PipelineError(f"Error al descargar de YouTube ({url}): {error}") from error
    except Exception as error:
        raise PipelineError(f"Fallo inesperado durante la descarga de YouTube ({url}): {error}") from error

    if not expected_output.is_file() or expected_output.stat().st_size < 1024:
        # Buscar si yt-dlp guardó con otra extensión compatible
        candidates = list(output_dir.glob(f"{video_id}.*"))
        if candidates:
            return candidates[0].resolve()
        raise PipelineError(f"La descarga finalizó pero no se encontró el archivo esperado: {expected_output}")

    if logger:
        logger.info("Descarga completada con éxito: %s (%.2f MB)", expected_output, expected_output.stat().st_size / (1024 * 1024))
    else:
        print(f"Descarga completada: {expected_output.name} ({expected_output.stat().st_size / (1024 * 1024):.2f} MB)")

    return expected_output

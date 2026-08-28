"""Módulo de renderizado vertical, generación de subtítulos ASS y validación visual con control negativo."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from config import (
    PAUSE_SECONDS,
    MAX_WORDS_PER_SUBTITLE,
    VISIBILITY_CONTROL_FLOOR,
    VISIBILITY_CONTROL_MULTIPLIER,
    VISIBILITY_MIN_CHANGED_RATIO,
    PipelineConfig,
    StageValidationError,
)
from utils import run_command, validate_video


def render_clips(
    video: Path,
    selection: dict[str, Any],
    clips_dir: Path,
    config: PipelineConfig,
    ffmpeg: str,
    ffprobe: str,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    """Renderiza los fragmentos seleccionados a formato vertical 1080x1920."""
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


def ass_time(seconds: float) -> str:
    """Convierte segundos a formato de tiempo ASS (H:MM:SS.cs)."""
    total_centiseconds = round(max(0.0, seconds) * 100)
    hours, rest = divmod(total_centiseconds, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, centiseconds = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def ass_safe_text(text: str) -> str:
    """Escapa caracteres especiales para el formato ASS."""
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def group_words(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Agrupa palabras en bloques de subtítulos según pausas, longitud y signos de puntuación."""
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
    """Genera el contenido completo de un archivo .ass con efectos karaoke \\k."""
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
    top -= top % 2
    height = ((bottom - top) // 2) * 2
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video),
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
    """Calcula la fracción de píxeles con cambio de alto contraste."""
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
    """Calcula el umbral de cambio exigido por encima del ruido del control negativo."""
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
    """Demuestra que el filtro ASS cambió píxeles más allá del ruido de recodificación."""
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
    """Genera archivos ASS e incrusta subtítulos con validación visual por fotograma."""
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

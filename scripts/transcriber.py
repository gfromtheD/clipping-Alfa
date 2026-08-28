"""Módulo de transcripción (Faster-Whisper) y alineación fonética por palabra (WhisperX)."""

from __future__ import annotations

import gc
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

from config import PipelineConfig, StageValidationError
from utils import assert_ai_device, atomic_json


def transcript_quality(segments: list[dict[str, Any]], min_avg_logprob: float) -> dict[str, Any]:
    """Valida la calidad de la transcripción (longitud, confianza y repetición anómala)."""
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
    """Transcribe una sola vez usando Faster-Whisper; esta es la fuente de texto del pipeline."""
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


_ALIGN_MODEL_CACHE: dict[tuple[str, str], Any] = {}


def load_align_model(language: str, device: str) -> tuple[Any, Any]:
    """Carga y cachea en memoria el modelo de alineación de WhisperX."""
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
    """Alinea el texto existente con WhisperX sin volver a transcribir el audio."""
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

"""Módulo de selección de clips basado en palabras alineadas, heurísticas y beam search."""

from __future__ import annotations

import math
import re
from bisect import bisect_left
from pathlib import Path
from typing import Any, Iterable

from config import (
    BEAM_WIDTH,
    MAX_DURATION_SECONDS,
    MAX_SELECTION_CANDIDATES,
    MIN_DURATION_SECONDS,
    SELECTION_HEURISTIC,
    PipelineConfig,
    StageValidationError,
)
from utils import atomic_json


def score_candidate(candidate: dict[str, Any]) -> int:
    """Calcula la puntuación de un clip según duración, palabras, ganchos y signos de puntuación."""
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
    """Determina si un candidato se solapa temporalmente con algún clip ya seleccionado."""
    return any(candidate["start"] < item["end"] and candidate["end"] > item["start"] for item in selected)


def word_windows(
    words: list[dict[str, Any]],
    min_duration: float,
    max_duration: float,
) -> list[dict[str, Any]]:
    """Construye ventanas temporales candidatas sobre las palabras alineadas."""
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
    """Selecciona los N mejores clips no solapados mediante beam search."""
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
    """Genera candidatos a partir de las palabras alineadas y guarda selection.json."""
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

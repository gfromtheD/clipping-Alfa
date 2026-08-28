"""Configuración, constantes, rutas y excepciones del pipeline de clipping."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any


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

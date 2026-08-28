"""Módulo de firmas de archivos, huellas de configuración, estado transaccional y registro v2."""

from __future__ import annotations

import hashlib
import json
import traceback
from pathlib import Path
from typing import Any

from config import (
    PIPELINE_REVISION,
    REGISTRY_PATH,
    SELECTION_HEURISTIC,
    STAGES,
    PipelineConfig,
    PipelineError,
)
from utils import atomic_json, project_relative, read_json, safe_slug, sha256_file, utc_now


def source_signature(path: Path) -> dict[str, Any]:
    """Genera la firma única de un archivo fuente basada en tamaño, mtime_ns y SHA-256."""
    stat = path.stat()
    return {
        "size_bytes": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def config_fingerprint(config: PipelineConfig) -> str:
    """Genera un hash determinista que identifica la configuración, heurística y revisión del pipeline."""
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


def video_id(video: Path, signature: dict[str, Any], config: PipelineConfig) -> str:
    """Calcula el identificador único del directorio final para un vídeo y su configuración."""
    return f"{safe_slug(video.stem)}-{signature['sha256'][:12]}-{config_fingerprint(config)[:8]}"


class RunState:
    """Maneja el estado transaccional de una ejecución en output/.work/<run_id>/state.json."""

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
        """Guarda el estado actual en disco de forma atómica."""
        atomic_json(self.path, self.data)

    def stage_started(self, stage: str) -> None:
        """Registra el inicio de una etapa."""
        self.data["active_stage"] = stage
        self.data["stages"][stage] = {"status": "running", "started_at": utc_now()}
        self.save()

    def stage_completed(self, stage: str, details: dict[str, Any]) -> None:
        """Registra la finalización exitosa de una etapa."""
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
        """Registra el fallo de una etapa o del pipeline general."""
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
        """Marca la ejecución como completada con la ruta final publicada."""
        self.data["status"] = "completed"
        self.data["finished_at"] = utc_now()
        self.data["active_stage"] = None
        self.data["final_output"] = final_relative_path
        self.save()


class RegistryManager:
    """Gestiona la lectura, validación y persistencia de processed_videos.v2.json."""

    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self.registry_path = registry_path

    def read(self) -> dict[str, Any]:
        """Lee el registro v2 verificando el esquema."""
        registry = read_json(self.registry_path, {"schema_version": 2, "videos": {}})
        if (
            not isinstance(registry, dict)
            or registry.get("schema_version") != 2
            or not isinstance(registry.get("videos"), dict)
        ):
            raise PipelineError(f"Registro v2 inválido: {self.registry_path}")
        return registry

    def save(self, registry: dict[str, Any]) -> None:
        """Guarda el registro con marca de tiempo UTC de actualización."""
        registry["updated_at"] = utc_now()
        atomic_json(self.registry_path, registry)

    def is_final_valid(self, final_dir: Path) -> bool:
        """Valida que un directorio final contenga todos sus artefactos y manifiesto."""
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

    def should_skip(
        self,
        video: Path,
        signature: dict[str, Any],
        final_dir: Path,
        config: PipelineConfig,
    ) -> bool:
        """Determina si un vídeo puede omitirse por existir un resultado idéntico y válido."""
        registry = self.read()
        key = project_relative(video)
        record = registry["videos"].get(key)
        matches = (
            record
            and record.get("status") == "completed"
            and record.get("source_signature") == signature
            and record.get("config_fingerprint") == config_fingerprint(config)
        )
        if matches and self.is_final_valid(final_dir):
            return True
        if not record and self.is_final_valid(final_dir):
            self.record_completed(video, signature, final_dir, config)
            return True
        return False

    def record_completed(
        self,
        video: Path,
        signature: dict[str, Any],
        final_dir: Path,
        config: PipelineConfig,
    ) -> None:
        """Registra una ejecución como completada en processed_videos.v2.json."""
        registry = self.read()
        key = project_relative(video)
        registry["videos"][key] = {
            "source_signature": signature,
            "config_fingerprint": config_fingerprint(config),
            "status": "completed",
            "completed_at": utc_now(),
            "final_output": project_relative(final_dir),
        }
        self.save(registry)

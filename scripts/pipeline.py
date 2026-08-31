"""Orquestador central del pipeline de clipping y subtitulado."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

from clipper import render_clips, render_subtitles
from config import (
    DEFAULT_MAX_CLIPS,
    FINAL_ROOT,
    INPUT_DIR,
    MAX_DURATION_SECONDS,
    MIN_DURATION_SECONDS,
    OUTPUT_DIR,
    PIPELINE_REVISION,
    STAGES,
    VIDEO_EXTENSIONS,
    WORK_ROOT,
    PipelineConfig,
    PipelineError,
    StageValidationError,
)
from downloader import download_youtube
from highlights import select_clips
from registry import RegistryManager, RunState, source_signature, video_id
from transcriber import align_transcript, transcribe_video
from utils import (
    atomic_json,
    close_logger,
    create_logger,
    discover_videos,
    ffprobe_json,
    project_relative,
    prune_work,
    require_command,
    safe_slug,
)


class PipelineRunner:
    """Coordina las etapas de IA, corte, subtitulado, validación y publicación atómica."""

    def __init__(
        self,
        config: PipelineConfig,
        verbosity: str,
        stage_callback: Callable[[str, str, dict[str, Any] | None], None] | None = None,
    ):
        self.config = config
        self.verbosity = verbosity
        self.stage_callback = stage_callback
        self.ffmpeg = require_command("ffmpeg")
        self.ffprobe = require_command("ffprobe")
        self.registry = RegistryManager()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        WORK_ROOT.mkdir(parents=True, exist_ok=True)
        FINAL_ROOT.mkdir(parents=True, exist_ok=True)
        self._validate_ass_support()

    def _report_stage(self, stage: str, status: str, details: dict[str, Any] | None = None) -> None:
        """Emite una notificación de progreso si hay un callback registrado."""
        if self.stage_callback:
            try:
                self.stage_callback(stage, status, details or {})
            except Exception:
                pass

    def _validate_ass_support(self) -> None:
        """Verifica que el binario de FFmpeg contenga soporte para el filtro ass/libass."""
        result = subprocess.run([self.ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True, check=False)
        if result.returncode != 0 or not re.search(r"\bass\b", result.stdout):
            raise PipelineError("El FFmpeg disponible no incluye el filtro ass/libass necesario para subtítulos.")

    def run_video(self, video: Path) -> Path:
        """Ejecuta el pipeline completo para un vídeo con aislamiento en .work y commit atómico."""
        if not video.is_file():
            raise PipelineError(f"No existe el vídeo: {video}")
        if video.suffix.lower() not in VIDEO_EXTENSIONS:
            raise PipelineError(f"Formato no compatible: {video.suffix}")
        video = video.resolve()
        signature = source_signature(video)
        final_dir = FINAL_ROOT / video_id(video, signature, self.config)

        if self.registry.should_skip(video, signature, final_dir, self.config):
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
            source_duration = float(source_probe.get("format", {}).get("duration", 0))
            if source_duration <= 0:
                raise StageValidationError(f"Duración de entrada inválida: {video}")

            # Etapa 1: Transcripción
            self._report_stage("transcribe", "processing", {"title": "Transcribiendo audio con Faster-Whisper (CUDA FP16)..."})
            state.stage_started("transcription")
            transcript = transcribe_video(video, artifacts / "transcript.json", self.config, logger)
            state.stage_completed("transcription", transcript["quality"] | {
                "detected_language": transcript["detected_language"],
                "language_probability": transcript["language_probability"],
            })
            self._maybe_fail("transcription")
            self._report_stage("transcribe", "completed", {
                "title": "Transcripción completada",
                "word_count": transcript["quality"]["word_count"],
                "language": transcript["detected_language"],
            })

            # Etapa 2: Alineación fonética
            self._report_stage("align", "processing", {"title": "Alineando timestamps a nivel de palabra con WhisperX..."})
            state.stage_started("alignment")
            alignment = align_transcript(video, transcript, artifacts / "alignment.json", self.config, logger)
            state.stage_completed("alignment", {"word_count": len(alignment["word_segments"]), "language": alignment["language"]})
            self._maybe_fail("alignment")
            self._report_stage("align", "completed", {
                "title": "Alineación WhisperX completada",
                "word_count": len(alignment["word_segments"]),
            })

            # Etapa 3: Selección y corte
            self._report_stage("select", "processing", {"title": "Seleccionando clips de alto impacto mediante búsqueda en haz..."})
            state.stage_started("selection")
            selection = select_clips(alignment, artifacts / "selection.json", self.config)
            self._report_stage("render", "processing", {"title": f"Renderizando {len(selection.get('clips', []))} clips verticales 9:16 (1080x1920)..."})
            clips = render_clips(video, selection, artifacts / "clips", self.config, self.ffmpeg, self.ffprobe, logger)
            state.stage_completed("selection", {"clip_count": len(clips), "clips": clips})
            self._maybe_fail("selection")
            self._report_stage("select", "completed", {"title": f"{len(clips)} clips seleccionados"})
            self._report_stage("render", "completed", {"title": f"{len(clips)} clips renderizados en 9:16"})

            # Etapa 4: Subtítulos dinámicos con validación visual negativa
            self._report_stage("validate", "processing", {"title": "Incrustando subtítulos dinámicos ASS y validando contraste visual..."})
            state.stage_started("subtitles")
            subtitled = render_subtitles(
                selection, alignment, artifacts / "clips", artifacts / "subtitles",
                self.config, self.ffmpeg, self.ffprobe, logger,
            )
            state.stage_completed("subtitles", {"clip_count": len(subtitled), "clips": subtitled})
            self._maybe_fail("subtitles")
            self._report_stage("validate", "completed", {"title": "Subtítulos dinámicos verificados (PASS)"})

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
            self.registry.record_completed(video, signature, final_dir, self.config)
            print(f"Completado: {video.name}\nSalida final: {final_dir}")
            self._report_stage("output", "completed", {
                "title": f"Pipeline completado: {final_dir.name}",
                "final_dir": str(final_dir),
            })
            return final_dir
        except BaseException as error:
            state.failed(error)
            logger.exception("El vídeo no se publicó: %s", error)
            close_logger(logger)
            raise

    def _maybe_fail(self, stage: str) -> None:
        """Inyecta un fallo simulado tras una etapa si está configurado en los tests."""
        if self.config.fail_after_stage == stage:
            raise PipelineError(f"Fallo intencionado de prueba después de la etapa '{stage}'.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Configura y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Pipeline atómico de clipping vertical y subtítulos sincronizados (sin LLM)."
    )
    parser.add_argument("--input", type=Path, help="Vídeo concreto. Si se omite, procesa los vídeos de input/.")
    parser.add_argument("--youtube-url", type=str, help="URL de YouTube para descargar y procesar")
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
    """Construye e hipervalida la configuración tipada a partir de los argumentos parseados."""
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


def main(argv: list[str] | None = None) -> int:
    """Punto de ejecución principal del CLI.

    Ejemplos de uso:
    - Procesar vídeos locales:
        python scripts/process_video.py --input input/prueba.mp4 --language en
    - Descargar y procesar desde YouTube:
        python scripts/process_video.py --youtube-url "https://youtube.com/watch?v=XXXXX" --language en
    - Procesar toda la carpeta input/ en modo automático:
        python scripts/process_video.py --language auto
    """
    args = parse_args(argv)
    try:
        config = config_from_args(args)
        if args.prune_work_days > 0:
            removed = prune_work(WORK_ROOT, args.prune_work_days)
            print(f"Se limpiaron {removed} directorio(s) antiguo(s) de output/.work")

        if args.youtube_url:
            downloaded = download_youtube(args.youtube_url, INPUT_DIR)
            videos = [downloaded]
        else:
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

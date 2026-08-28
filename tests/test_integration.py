"""Test de integración sin GPU: dobles de IA + MP4 sintético generado con FFmpeg.

Verifica la publicación atómica, el registro v2, el control negativo de
subtítulos y el salto de resultados ya válidos sobre la arquitectura modular.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import config
import pipeline
import registry
import transcriber
import utils
from config import PIPELINE_REVISION, PipelineConfig, PipelineError
from pipeline import PipelineRunner
from transcriber import transcript_quality
from utils import atomic_json, read_json

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def make_synthetic_video(path: Path, duration: float = 40.0) -> None:
    duration_text = f"{duration:.0f}"
    subprocess.run(
        [
            FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c=gray:s=640x360:d={duration_text}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration_text}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def fake_transcribe(video, output_path, config_obj, logger):
    segments = []
    cursor = 0.0
    for index in range(8):
        segments.append(
            {
                "start": round(cursor, 3),
                "end": round(cursor + 5.0, 3),
                "text": f"This is segment {index} with a secret truth and an important lesson.",
                "avg_logprob": -0.3,
                "compression_ratio": 1.0,
                "no_speech_prob": 0.01,
            }
        )
        cursor += 5.0
    result = {
        "schema_version": 1,
        "source": str(video),
        "model": config_obj.model,
        "device": {"device": config_obj.device},
        "compute_type": config_obj.compute_type,
        "batch_size": None,
        "requested_language": config_obj.language or "auto",
        "detected_language": "en",
        "language_probability": 0.95,
        "parameters": {},
        "quality": transcript_quality(segments, config_obj.min_avg_logprob),
        "segments": segments,
    }
    atomic_json(output_path, result)
    return result


def fake_align(video, transcript_data, output_path, config_obj, logger):
    words = []
    for segment in transcript_data["segments"]:
        cursor = float(segment["start"])
        for raw in str(segment["text"]).split():
            words.append(
                {
                    "word": raw.strip(",.!?"),
                    "start": round(cursor, 3),
                    "end": round(cursor + 0.3, 3),
                    "score": 0.9,
                }
            )
            cursor += 0.35
    result = {
        "schema_version": 1,
        "source_transcript": "transcript.json",
        "alignment_engine": "fake",
        "device": {"device": config_obj.device},
        "language": transcript_data["detected_language"],
        "segments": [],
        "word_segments": words,
    }
    atomic_json(output_path, result)
    return result


def make_config():
    return PipelineConfig(
        language=None, model="small", device="cpu", compute_type="float32",
        max_clips=4, min_duration=18.0, max_duration=45.0, crf=23,
        preset="veryfast", subtitle_margin_ratio=0.27, min_avg_logprob=-1.5,
    )


def patched_workspace(root: Path):
    return mock.patch.multiple(
        pipeline,
        OUTPUT_DIR=root / "output",
        WORK_ROOT=root / "output" / ".work",
        FINAL_ROOT=root / "output" / "videos",
    )


@unittest.skipUnless(FFMPEG and FFPROBE, "Se requiere ffmpeg/ffprobe para el test de integración")
class IntegrationTest(unittest.TestCase):
    def test_full_pipeline_publishes_and_skips_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video_dir = root / "input"
            video_dir.mkdir()
            video = video_dir / "synthetic.mp4"
            make_synthetic_video(video)
            with patched_workspace(root), mock.patch.object(registry, "REGISTRY_PATH", root / "output" / "processed_videos.v2.json"):
                runner = PipelineRunner(make_config(), "info")
                runner.registry.registry_path = root / "output" / "processed_videos.v2.json"
                with mock.patch.object(pipeline, "transcribe_video", side_effect=fake_transcribe) as fake_t:
                    with mock.patch.object(pipeline, "align_transcript", side_effect=fake_align):
                        final = runner.run_video(video)
                        again = runner.run_video(video)
            self.assertEqual(again, final)
            self.assertEqual(fake_t.call_count, 1)

            manifest = read_json(final / "manifest.json")
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["pipeline_revision"], PIPELINE_REVISION)
            self.assertTrue((final / "FINAL_OUTPUTS.txt").is_file())

            subtitled = manifest["outputs"]["subtitles"]
            self.assertGreaterEqual(len(subtitled), 1)
            for item in subtitled:
                self.assertTrue((final / "subtitles" / item["video"]).is_file())
                self.assertTrue((final / "subtitles" / item["ass"]).is_file())
                self.assertIn("negative_control_changed_ratio", item["visibility"])
                self.assertGreaterEqual(
                    item["visibility"]["high_contrast_changed_ratio"],
                    item["visibility"]["required_changed_ratio"],
                )

            reg_data = read_json(root / "output" / "processed_videos.v2.json")
            self.assertEqual(reg_data["videos"][str(video.resolve())]["status"], "completed")

    def test_failure_never_publishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video_dir = root / "input"
            video_dir.mkdir()
            video = video_dir / "synthetic.mp4"
            make_synthetic_video(video)
            with patched_workspace(root), mock.patch.object(registry, "REGISTRY_PATH", root / "output" / "processed_videos.v2.json"):
                runner = PipelineRunner(make_config(), "info")
                runner.registry.registry_path = root / "output" / "processed_videos.v2.json"
                with mock.patch.object(pipeline, "transcribe_video", side_effect=PipelineError("boom")):
                    with self.assertRaises(PipelineError):
                        runner.run_video(video)
                final_root = root / "output" / "videos"
                self.assertTrue(final_root.is_dir())
                self.assertEqual(list(final_root.iterdir()), [])
                reg_data = read_json(
                    root / "output" / "processed_videos.v2.json", {"schema_version": 2, "videos": {}}
                )
                self.assertEqual(reg_data["videos"], {})
                states = list((root / "output" / ".work").glob("*/state.json"))
                self.assertEqual(len(states), 1)
                state = read_json(states[0])
                self.assertEqual(state["status"], "failed")
                self.assertEqual(state["error"]["type"], "PipelineError")


if __name__ == "__main__":
    unittest.main()

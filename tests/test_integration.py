"""Test de integración sin GPU: dobles de IA + MP4 sintético generado con FFmpeg.

Verifica la publicación atómica, el registro v2, el control negativo de
subtítulos y el salto de resultados ya válidos.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pipeline_core as pc

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


def fake_transcribe(video, output_path, config, logger):
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
        "model": config.model,
        "device": {"device": config.device},
        "compute_type": config.compute_type,
        "batch_size": None,
        "requested_language": config.language or "auto",
        "detected_language": "en",
        "language_probability": 0.95,
        "parameters": {},
        "quality": pc.transcript_quality(segments, config.min_avg_logprob),
        "segments": segments,
    }
    pc.atomic_json(output_path, result)
    return result


def fake_align(video, transcript, output_path, config, logger):
    words = []
    for segment in transcript["segments"]:
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
        "device": {"device": config.device},
        "language": transcript["detected_language"],
        "segments": [],
        "word_segments": words,
    }
    pc.atomic_json(output_path, result)
    return result


def make_config():
    return pc.PipelineConfig(
        language=None, model="small", device="cpu", compute_type="float32",
        max_clips=4, min_duration=18.0, max_duration=45.0, crf=23,
        preset="veryfast", subtitle_margin_ratio=0.27, min_avg_logprob=-1.5,
    )


def patched_workspace(root: Path):
    return mock.patch.multiple(
        pc,
        OUTPUT_DIR=root / "output",
        WORK_ROOT=root / "output" / ".work",
        FINAL_ROOT=root / "output" / "videos",
        REGISTRY_PATH=root / "output" / "processed_videos.v2.json",
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
            with patched_workspace(root):
                runner = pc.PipelineRunner(make_config(), "info")
                with mock.patch.object(pc, "transcribe_video", side_effect=fake_transcribe) as fake_t:
                    with mock.patch.object(pc, "align_transcript", side_effect=fake_align):
                        final = runner.run_video(video)
                        again = runner.run_video(video)
            self.assertEqual(again, final)
            self.assertEqual(fake_t.call_count, 1)

            manifest = pc.read_json(final / "manifest.json")
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["pipeline_revision"], pc.PIPELINE_REVISION)
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

            registry = pc.read_json(root / "output" / "processed_videos.v2.json")
            self.assertEqual(registry["videos"][str(video.resolve())]["status"], "completed")

    def test_failure_never_publishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video_dir = root / "input"
            video_dir.mkdir()
            video = video_dir / "synthetic.mp4"
            make_synthetic_video(video)
            with patched_workspace(root):
                runner = pc.PipelineRunner(make_config(), "info")
                with mock.patch.object(pc, "transcribe_video", side_effect=pc.PipelineError("boom")):
                    with self.assertRaises(pc.PipelineError):
                        runner.run_video(video)
                final_root = root / "output" / "videos"
                self.assertTrue(final_root.is_dir())
                self.assertEqual(list(final_root.iterdir()), [])
                registry = pc.read_json(
                    root / "output" / "processed_videos.v2.json", {"schema_version": 2, "videos": {}}
                )
                self.assertEqual(registry["videos"], {})
                states = list((root / "output" / ".work").glob("*/state.json"))
                self.assertEqual(len(states), 1)
                state = pc.read_json(states[0])
                self.assertEqual(state["status"], "failed")
                self.assertEqual(state["error"]["type"], "PipelineError")


if __name__ == "__main__":
    unittest.main()

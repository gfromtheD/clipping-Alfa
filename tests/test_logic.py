"""Tests de la lógica pura del pipeline modular. No requieren GPU ni FFmpeg."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from clipper import (
    ass_safe_text,
    ass_time,
    group_words,
    make_ass_content,
    pixel_diff_ratio,
    required_visibility_threshold,
)
from config import (
    SELECTION_HEURISTIC,
    PipelineConfig,
    StageValidationError,
)
from highlights import (
    beam_select,
    overlaps,
    score_candidate,
    select_clips,
    word_windows,
)
from registry import config_fingerprint
from transcriber import transcript_quality
from utils import prune_work, validate_video


def make_config(max_clips: int = 4, min_duration: float = 18.0, max_duration: float = 45.0):
    return PipelineConfig(
        language=None, model="small", device="cpu", compute_type="float32",
        max_clips=max_clips, min_duration=min_duration, max_duration=max_duration,
        crf=23, preset="veryfast", subtitle_margin_ratio=0.27, min_avg_logprob=-1.5,
    )


class FingerprintTest(unittest.TestCase):
    def test_fingerprint_changes_with_heuristics(self):
        first = config_fingerprint(make_config())
        original = dict(SELECTION_HEURISTIC)
        try:
            SELECTION_HEURISTIC["hook_words"] = list(original["hook_words"]) + ["newhook"]
            second = config_fingerprint(make_config())
        finally:
            SELECTION_HEURISTIC.clear()
            SELECTION_HEURISTIC.update(original)
        self.assertNotEqual(first, second)

    def test_fingerprint_changes_with_config(self):
        config = make_config()
        other = PipelineConfig(**{**config.serializable(), "max_clips": 6})
        self.assertNotEqual(config_fingerprint(config), config_fingerprint(other))


class ScoringTest(unittest.TestCase):
    def test_hook_words_question_and_ideal_duration(self):
        candidate = {"start": 0.0, "end": 30.0, "text": "Imagine a secret truth, why? because it matters."}
        self.assertEqual(score_candidate(candidate), 4 + 3 + 8)

    def test_weak_start_penalty(self):
        candidate = {"start": 0.0, "end": 25.0, "text": "Hello everyone, this is important"}
        self.assertEqual(score_candidate(candidate), 4 + 2 - 4)

    def test_hook_bonus_capped(self):
        candidate = {"start": 0.0, "end": 20.0, "text": "secret truth mistake problem important warning never always best"}
        self.assertEqual(score_candidate(candidate), 2 + min(8, 4) * 2)

    def test_overlaps(self):
        first = {"start": 10.0, "end": 20.0}
        second = {"start": 15.0, "end": 25.0}
        disjoint = {"start": 20.0, "end": 30.0}
        self.assertTrue(overlaps(second, [first]))
        self.assertFalse(overlaps(disjoint, [first]))


class WordWindowsTest(unittest.TestCase):
    def words(self, count: int, gap: float = 1.0):
        return [
            {"word": f"w{index}", "start": round(index * gap, 3), "end": round(index * gap + 0.9, 3)}
            for index in range(count)
        ]

    def test_windows_respect_duration_limits(self):
        windows = word_windows(self.words(10, gap=2.0), min_duration=3.0, max_duration=5.0)
        self.assertTrue(windows)
        for window in windows:
            duration = window["end"] - window["start"]
            self.assertGreaterEqual(duration, 3.0)
            self.assertLessEqual(duration, 5.0)
            self.assertGreaterEqual(len(window["text"].split()), 2)

    def test_windows_can_start_inside_sequence(self):
        windows = word_windows(self.words(6, gap=2.0), min_duration=3.0, max_duration=5.0)
        starts = {window["start"] for window in windows}
        self.assertIn(2.0, starts)
        self.assertIn(4.0, starts)

    def test_empty_words(self):
        self.assertEqual(word_windows([], 18.0, 45.0), [])


class BeamSelectTest(unittest.TestCase):
    def test_finds_better_global_than_greedy(self):
        candidates = [
            {"start": 0.0, "end": 30.0, "score": 15},
            {"start": 0.0, "end": 20.0, "score": 10},
            {"start": 21.0, "end": 40.0, "score": 9},
        ]
        selected = beam_select(candidates, max_clips=4, beam_width=2)
        pairs = [(item["start"], item["end"]) for item in selected]
        self.assertEqual(pairs, [(0.0, 20.0), (21.0, 40.0)])
        self.assertEqual(sum(item["score"] for item in selected), 19)

    def test_respects_max_clips(self):
        candidates = [
            {"start": float(index * 10), "end": float(index * 10 + 9), "score": 5}
            for index in range(6)
        ]
        selected = beam_select(candidates, max_clips=3, beam_width=4)
        self.assertEqual(len(selected), 3)

    def test_no_overlap_in_result(self):
        candidates = [
            {"start": 0.0, "end": 25.0, "score": 12},
            {"start": 10.0, "end": 35.0, "score": 11},
            {"start": 26.0, "end": 50.0, "score": 10},
        ]
        selected = beam_select(candidates, max_clips=2, beam_width=4)
        self.assertFalse(overlaps(selected[0], selected[1:]))

    def test_negative_scores_fallback_to_best_single(self):
        candidates = [
            {"start": 0.0, "end": 20.0, "score": -3},
            {"start": 0.0, "end": 25.0, "score": -1},
        ]
        selected = beam_select(candidates, max_clips=2, beam_width=2)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["score"], -1)


class SelectClipsTest(unittest.TestCase):
    def test_select_clips_writes_contract(self):
        alignment = {
            "word_segments": [
                {"word": f"w{index}", "start": index * 2.0, "end": index * 2.0 + 1.0}
                for index in range(30)
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "selection.json"
            result = select_clips(alignment, output, make_config(min_duration=8.0, max_duration=20.0))
            self.assertEqual(result["selection_method"], "heuristic-v2-word-windows-beam")
            self.assertTrue(result["clips"])
            self.assertTrue(output.is_file())

    def test_select_clips_requires_words(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(StageValidationError):
                select_clips({"word_segments": []}, Path(tmp) / "selection.json", make_config())


class TranscriptQualityTest(unittest.TestCase):
    def segment(self, start, end, text, logprob=-0.5):
        return {"start": start, "end": end, "text": text, "avg_logprob": logprob}

    def test_empty_segments_fail(self):
        with self.assertRaises(StageValidationError):
            transcript_quality([], -1.5)

    def test_too_few_words_fail(self):
        with self.assertRaises(StageValidationError):
            transcript_quality([self.segment(0, 2, "a b")], -1.5)

    def test_low_logprob_fail(self):
        segments = [self.segment(0, 5, "one two three four five", logprob=-2.5)]
        with self.assertRaises(StageValidationError):
            transcript_quality(segments, -1.5)

    def test_repeated_trigrams_fail(self):
        text = " ".join(["la la la"] * 12)
        segments = [self.segment(0, 30, text, logprob=-0.5)]
        with self.assertRaises(StageValidationError):
            transcript_quality(segments, -1.5)

    def test_ok_quality_metrics(self):
        segments = [self.segment(0, 5, "one two three four five", logprob=-0.4)]
        quality = transcript_quality(segments, -1.5)
        self.assertEqual(quality["word_count"], 5)
        self.assertEqual(quality["segment_count"], 1)


class SubtitleGroupingTest(unittest.TestCase):
    def word(self, start, end, text="word"):
        return {"start": start, "end": end, "word": text}

    def test_pause_splits_groups(self):
        groups = group_words([self.word(0, 1), self.word(2, 3)])
        self.assertEqual(len(groups), 2)

    def test_max_words_per_group(self):
        words = [self.word(index * 0.2, index * 0.2 + 0.1) for index in range(6)]
        groups = group_words(words)
        self.assertEqual([len(group) for group in groups], [5, 1])

    def test_punctuation_splits_groups(self):
        groups = group_words([
            self.word(0, 0.3, "alpha"),
            self.word(0.4, 0.7, "beta."),
            self.word(0.8, 1.1, "gamma"),
        ])
        self.assertEqual([len(group) for group in groups], [2, 1])

    def test_ass_time(self):
        self.assertEqual(ass_time(0.0), "0:00:00.00")
        self.assertEqual(ass_time(3661.25), "1:01:01.25")

    def test_ass_safe_text(self):
        self.assertEqual(ass_safe_text(r"a\b{c}d"), r"a\\b\{c\}d")

    def test_make_ass_content(self):
        words = [self.word(0, 0.5, "hello"), self.word(0.6, 1.0, "world.")]
        content = make_ass_content(words, 518)
        self.assertIn("[Script Info]", content)
        self.assertIn("Dialogue: 0,0:00:00.00,0:00:01.00,Social,,0,0,0,,", content)
        self.assertIn(r"{\k50}hello", content)
        self.assertIn(r"{\k40}world.", content)


class VisibilityTest(unittest.TestCase):
    def test_pixel_diff_ratio(self):
        base = b"\x00\x00\x00" * 4
        self.assertEqual(pixel_diff_ratio(base, base), 0.0)
        altered = bytearray(base)
        altered[9] = 255
        self.assertEqual(pixel_diff_ratio(base, bytes(altered)), 0.25)

    def test_pixel_diff_ratio_mismatched_sizes(self):
        with self.assertRaises(StageValidationError):
            pixel_diff_ratio(b"\x00" * 6, b"\x00" * 9)

    def test_required_threshold(self):
        self.assertEqual(required_visibility_threshold(0.0), 0.005)
        self.assertEqual(required_visibility_threshold(0.01), 0.032)


class PruneWorkTest(unittest.TestCase):
    def test_prunes_only_stale_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_dir = root / "old"
            new_dir = root / "new"
            old_dir.mkdir()
            new_dir.mkdir()
            for directory in (old_dir, new_dir):
                (directory / "state.json").write_text("{}", encoding="utf-8")
            now = time.time()
            os.utime(old_dir / "state.json", (now - 20 * 86400, now - 20 * 86400))
            os.utime(new_dir / "state.json", (now, now))
            removed = prune_work(root, max_age_days=10)
            self.assertEqual(removed, 1)
            self.assertFalse(old_dir.exists())
            self.assertTrue(new_dir.exists())

    def test_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(prune_work(Path(tmp), max_age_days=0), 0)


class ValidateVideoTest(unittest.TestCase):
    def test_missing_duration_is_controlled_error(self):
        from unittest import mock
        import utils

        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "fake.mp4"
            video.write_bytes(b"\x00" * 2048)
            probe = {
                "format": {},
                "streams": [
                    {"codec_type": "video", "width": 1080, "height": 1920},
                    {"codec_type": "audio"},
                ],
            }
            with mock.patch.object(utils, "ffprobe_json", return_value=probe):
                with self.assertRaises(StageValidationError):
                    validate_video(video, expected_duration=10.0, ffprobe="ffprobe", logger=None)


if __name__ == "__main__":
    unittest.main()

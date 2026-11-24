import unittest

from gameplay_editor.planner import (
    best_moments, full_gameplay, make_timeline, merge_intervals, validate_timeline,
)


class TestPlanner(unittest.TestCase):
    def test_merge(self):
        self.assertEqual(merge_intervals([(10, 20), (0, 4), (3, 7), (23, 30)], gap=3), [(0, 30)])

    def test_full_discards_long_still_silent_segments(self):
        audio = [.08] * 10 + [0.0] * 30 + [.08] * 20
        motion = [.6] * 10 + [0.0] * 30 + [.6] * 20
        self.assertEqual(full_gameplay(audio, motion, 60, min_idle=20, context=4), [(0, 14), (36, 60)])

    def test_full_preserves_speech_even_when_picture_still(self):
        self.assertEqual(full_gameplay([.04] * 60, [0.0] * 60, 60), [(0, 60)])

    def test_full_does_not_empty_silent_source(self):
        self.assertEqual(full_gameplay([0.0] * 50, [0.0] * 50, 50), [(0, 50)])

    def test_highlights_preserve_separate_chronological_moments(self):
        activity = [0.0] * 20 + [.9] * 4 + [0.0] * 30 + [.8] * 5 + [0.0] * 30
        selected = best_moments(activity, len(activity))
        self.assertEqual(selected, [(15, 32), (49, 67)])

    def test_highlights_no_activity(self):
        self.assertEqual(best_moments([0.0] * 90, 90), [])

    def test_highlights_no_fixed_total_duration(self):
        activity = ([0.0] * 30 + [.9] * 20 + [0.0] * 35) * 15
        selected = best_moments(activity, len(activity))
        self.assertGreater(len(selected), 8)
        self.assertGreater(sum(b - a for a, b in selected), 300)

    def test_timeline_validation(self):
        source = {"path": "/videos/original.mp4", "duration": 100, "size": 1, "mtime_ns": 1}
        timeline = make_timeline(
            source=source, mode="full", audio=[1] * 100,
            motion=[1] * 100, activity=[.5] * 100,
        )
        validate_timeline(timeline)
        timeline["clips"][0]["end"] = 200
        with self.assertRaises(ValueError):
            validate_timeline(timeline)


if __name__ == "__main__":
    unittest.main()

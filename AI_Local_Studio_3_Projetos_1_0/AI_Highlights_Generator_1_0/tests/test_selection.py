import copy
import random
import unittest
from highlights.selection import select, validate


def blocks(minutes):
    return [dict(start=i*60., end=(i+1)*60., motion=.03, audio=.1,
                 score=random.Random(i).random()) for i in range(minutes)]


class SelectionTests(unittest.TestCase):
    def test_ten_unique_chronological_episodes(self):
        p = select(blocks(240), 14400, 10, 12, .6)
        self.assertEqual(len(p['episodes']), 10)
        self.assertEqual(sum(e['duration'] for e in p['episodes']), 7200)
        validate(p, 14400)
        seconds = []
        for e in p['episodes']:
            for s in e['segments']:
                seconds.extend(range(int(s['start']), int(s['end'])))
        self.assertEqual(len(seconds), len(set(seconds)))
        self.assertEqual(seconds, sorted(seconds))

    def test_short_source_rejected(self):
        with self.assertRaises(ValueError):
            select(blocks(9), 599)

    def test_exact_ten_minutes(self):
        p = select(blocks(10), 600)
        self.assertEqual(len(p['episodes']), 1)
        self.assertEqual(p['episodes'][0]['duration'], 600)

    def test_less_than_ten_episodes_is_valid(self):
        p = select(blocks(45), 2700)
        self.assertEqual(len(p['episodes']), 2)

    def test_silent_static_does_not_get_selected(self):
        b = blocks(30)
        for x in b:
            x.update(motion=0, audio=0)
        with self.assertRaises(ValueError):
            select(b, 1800)

    def test_edits_reject_duplicate_reversed_nan_and_outside(self):
        for segment in [dict(start=0,end=720),dict(start=800,end=700),
                        dict(start=float('nan'),end=900),dict(start=1500,end=2300)]:
            plan = dict(episodes=[dict(segments=[dict(start=0,end=720)]),dict(segments=[segment])])
            with self.assertRaises(ValueError):
                validate(plan, 2000)

    def test_durations_and_maximum(self):
        for count in (0,11):
            with self.assertRaises(ValueError):
                validate(dict(episodes=[dict(segments=[dict(start=i*720,end=(i+1)*720)]) for i in range(count)]),10000)
        for length in (599,901):
            with self.assertRaises(ValueError):
                validate(dict(episodes=[dict(segments=[dict(start=0,end=length)])]),1000)

    def test_fuzz_plans(self):
        for minutes in (10,11,12,23,24,35,60,120,240,500):
            for cap in (1,3,10):
                for target in (11,12,13,14):
                    plan = select(blocks(minutes), minutes*60, cap, target, .6)
                    self.assertLessEqual(len(plan['episodes']), cap)
                    validate(plan, minutes*60)


if __name__ == '__main__':
    unittest.main()

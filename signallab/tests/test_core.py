import math
import random
import unittest

from core import analyze, demo, episodes, parse_csv, rolling, score, to_csv, validate


class WindowTests(unittest.TestCase):
    def test_weighting_is_by_requests(self):
        rows = [{"total": 1, "bad": 1}, {"total": 999, "bad": 0}]
        self.assertAlmostEqual(rolling(rows, 2, .99)[-1], .1)

    def test_full_window_and_empty_traffic(self):
        self.assertEqual(rolling([{"total": 0, "bad": 0}] * 3, 2, .99), [None, None, None])
        self.assertEqual(rolling([{"total": 100, "bad": 1}] * 2, 3, .99), [None, None])

    def test_minimum_request_gate(self):
        self.assertEqual(rolling([{"total": 99, "bad": 9}], 1, .99, 100), [None])

    def test_matches_independent_brute_force(self):
        rng = random.Random(18)
        rows = [{"total": 1000 + rng.randrange(100), "bad": rng.randrange(30)} for _ in range(80)]
        for window in [1, 5, 30, 60]:
            fast = rolling(rows, window, .999)
            for i in range(window - 1, len(rows)):
                segment = rows[i + 1 - window:i + 1]
                expected = sum(r["bad"] for r in segment) / sum(r["total"] for r in segment) / .001
                self.assertAlmostEqual(fast[i], expected)

    def test_episode_end_is_exclusive(self):
        alerts = episodes([False, True, True, False, True], "api", "x")
        self.assertEqual([(a["start"], a["end"]) for a in alerts], [(1, 3), (4, 5)])

    def test_unlabeled_metrics_are_unknown(self):
        self.assertIsNone(score([], None)["recall"])

    def test_score_detection_and_false_episode(self):
        alerts = [{"service": "api", "start": 12, "end": 20}, {"service": "api", "start": 25, "end": 28}]
        metrics = score(alerts, [{"service": "api", "start": 10, "end": 20}])
        self.assertEqual(metrics["precision"], .5)
        self.assertEqual(metrics["recall"], 1)
        self.assertEqual(metrics["median_detection_minutes"], 2)


class ContractTests(unittest.TestCase):
    def test_bad_options(self):
        for options in [{"slo": math.nan}, {"slo": 1}, {"seed": True}, {"min_requests": -1}, {"extra": 0}]:
            with self.subTest(options=options), self.assertRaises(ValueError): validate(options)

    def test_csv_rejects_duplicates_gaps_and_bad_counts(self):
        for body in ["0,api,10,11", "0,api,10,-1", "1,api,10,0", "0,api,10,0\n0,api,10,0"]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse_csv("minute,service,total,bad\n" + body)

    def test_demo_round_trip(self):
        rows, _ = demo(12)
        parsed = parse_csv(to_csv(rows))
        self.assertEqual(parsed, sorted(rows, key=lambda r: (r["service"], r["minute"])))

    def test_import_does_not_invent_labels(self):
        r = analyze({"csv": "minute,service,total,bad\n0,api,100,0\n"})
        self.assertFalse(r["synthetic"])
        self.assertIsNone(r["comparison"][0]["recall"])

    def test_incomplete_history_cannot_page(self):
        rows = [{"minute": i, "service": "api", "total": 1000, "bad": 1000} for i in range(59)]
        r = analyze({"csv": to_csv(rows)})
        self.assertEqual(r["alerts"], [])
        rows.append({"minute": 59, "service": "api", "total": 1000, "bad": 1000})
        self.assertEqual(analyze({"csv": to_csv(rows)})["alerts"][0]["start"], 59)

    def test_replay_is_deterministic(self):
        body = "minute,service,total,bad\n0,api,100,0\n"
        self.assertEqual(analyze({"csv": body}), analyze({"csv": body}))


if __name__ == "__main__": unittest.main()

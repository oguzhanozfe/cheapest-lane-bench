import json
import unittest

from bench import judge, report, scoring
from bench.scoring import values_equal as eq


def J(**kw):
    return json.dumps(kw)


EXTRACT = {"reference": {"key": ["owner"], "fuzzy": ["task"],
                         "records": [{"owner": "Priya", "task": "send revised budget", "due": "2026-03-13"},
                                     {"owner": "Tom", "task": "fix staging script", "due": None}]}}
EX_GOOD = [{"owner": "Priya", "task": "send the revised budget", "due": "2026-03-13"},
           {"owner": "Tom", "task": "fix staging script", "due": None}]

LOG = "FAILED tests/a.py::test_alpha - boom\nFAILED tests/b.py::test_beta - bang\n"
TRIAGE = {"input": LOG, "reference": {"failures": ["test_alpha", "test_beta"]}}
DIFF_IN = "--- a/x.py\n+++ b/x.py\n-old = 1\n+TOKEN = 'abc123'\n"
DIFF = {"input": DIFF_IN, "reference": {"issues": [{"key": "abc123"}]}}
CLEAN = {"input": DIFF_IN, "reference": {"issues": []}}


def fail(name, quote):
    return {"name": name, "message": "m", "likely_cause": "c", "quote": quote}


def finding(note, quote):
    return {"file": "x.py", "severity": "high", "note": note, "quote": quote}


class Values(unittest.TestCase):
    def test_values_equal(self):
        for ref, pred, fuzzy, want in [
            (1249.9, "$1,249.90", False, True), (1249.9, 1250, False, False), (3, "three", False, False),
            (None, None, False, True), (None, "N/A", False, True), (None, "x", False, False),
            ("a", None, False, False),
            ("+1 (555) 123-4567", "555.123.4567", False, False),  # country code digit differs
            ("555-123-4567", "(555) 123 4567", False, True),
            ("send the revised budget to finance", "revised budget sent to finance team", True, True),
            ("send the revised budget to finance", "water the plants", True, False),
            ("Hello World.", "  hello   world ", False, True),
        ]:
            with self.subTest(ref=ref, pred=pred):
                self.assertIs(eq(ref, pred, fuzzy), want)


class Json(unittest.TestCase):
    def test_extract(self):
        s = scoring.score_extract
        self.assertEqual(s(EXTRACT, J(records=EX_GOOD))["score"], 1.0)
        bad = s(EXTRACT, "not json")
        self.assertEqual((bad["score"], bad["valid_json"]), (0.0, False))
        extra = s(EXTRACT, J(records=EX_GOOD + [{"owner": "Zed", "task": "x", "due": None}]))
        self.assertLess(extra["score"], 1.0)
        empty = {"reference": {"key": ["owner"], "records": []}}
        self.assertEqual(s(empty, J(records=[]))["score"], 1.0)
        self.assertEqual(s(empty, J(records=[{"owner": "A"}]))["score"], 0.0)

    def test_triage(self):
        good = J(failures=[fail("test_alpha", "FAILED tests/a.py::test_alpha - boom"),
                           fail("test_beta", "FAILED tests/b.py::test_beta - bang")], summary="s")
        self.assertEqual(scoring.score_triage(TRIAGE, good)["score"], 1.0)
        para = J(failures=[fail("test_alpha", "FAILED tests/a.py::test_alpha - boom"),
                           fail("test_beta", "beta test blew up")], summary="s")
        r = scoring.score_triage(TRIAGE, para)
        self.assertEqual(r["quote_rate"], 0.5)
        self.assertEqual(r["score"], 0.5)

    def test_diff(self):
        ok = J(findings=[finding("secret", "+TOKEN = 'abc123'")], summary="s")
        self.assertEqual(scoring.score_diff(DIFF, ok)["score"], 1.0)
        para = J(findings=[finding("secret", "TOKEN is hardcoded abc123")], summary="s")
        r = scoring.score_diff(DIFF, para)
        self.assertEqual((r["quote_rate"], r["score"]), (0.0, 0.0))
        self.assertEqual(scoring.score_diff(CLEAN, J(findings=[], summary="s"))["score"], 1.0)
        self.assertEqual(scoring.score_diff(CLEAN, ok)["score"], 0.0)
        note_only = J(findings=[finding("hardcoded abc123 secret", "")], summary="s")
        self.assertEqual(scoring.score_diff(DIFF, note_only)["score"], 1.0)


class Text(unittest.TestCase):
    ITEM = {"reference": {"types": ["fix"], "keywords": [["discount"], ["zero", "clamp"]]}}

    def test_commit(self):
        s = scoring.score_commit
        r = s(self.ITEM, "fix(billing): clamp discount at zero\n\n- body line")
        self.assertEqual(r["score"], 1.0)
        long = s(self.ITEM, "fix(billing): " + "discount zero " * 6)
        self.assertFalse(long["format_ok"])
        self.assertFalse(s(self.ITEM, "feat(billing): clamp discount at zero")["type_ok"])
        self.assertFalse(s(self.ITEM, "fix: discount zero\n\n```\ncode\n```")["format_ok"])

    def test_summarize(self):
        item = {"arguments": {"bullets": "2"}, "reference": {"facts": [["43 minutes"], ["pgbouncer"]]}}
        r = scoring.score_summarize(item, "- 43 minutes down\n- other")
        self.assertEqual((r["bullets_ok"], r["fact_coverage"], r["score"]), (True, 0.5, 0.6))
        r = scoring.score_summarize(item, "- 43 minutes\n- pgbouncer\n- three")
        self.assertEqual((r["bullets_ok"], r["fact_coverage"], r["score"]), (False, 1.0, 0.8))

    def test_chrf_translate(self):
        self.assertEqual(scoring.chrf("hello world", "hello world"), 1.0)
        self.assertEqual(scoring.chrf("aaaa", "bbbb"), 0.0)
        self.assertTrue(0 < scoring.chrf("hello there", "hello world") < 1)
        item = {"reference": {"translation": "run `make` now", "preserve": ["`make`", "v1.2"]}}
        r = scoring.score_translate(item, "run `make` now")
        self.assertEqual(r["preserved"], 0.5)
        self.assertEqual(r["score"], 0.75)

    def test_none_scores_zero(self):
        for task in scoring.ALL_TASKS:
            self.assertEqual(scoring.score(task, {}, None)["score"], 0)


class Judge(unittest.TestCase):
    def test_parse_score(self):
        for text, want in [('{"score": 4, "reason": "ok"}', 4), ('{"score":"2"}', 2), ("Score: 5", 5),
                           ("no idea", None)]:
            self.assertEqual(judge.parse_score(text), want)


def cell(lane, q, usd, p50=1.0, ok=3):
    return {"lane": lane, "quality": q, "usd_per_1k_items": usd, "ok": ok, "p50_seconds": p50}


class Report(unittest.TestCase):
    def test_frontier(self):
        cells = [cell("cheap", 0.8, 0.1), cell("best", 0.9, 1.0), cell("dominated", 0.7, 2.0)]
        self.assertEqual(report.frontier(cells), ["cheap", "best"])

    def test_recommend(self):
        cells = [cell("best", 0.90, 5.0), cell("near", 0.86, 1.0, p50=9), cell("nearfast", 0.86, 1.0, p50=2),
                 cell("far", 0.80, 0.01)]
        self.assertEqual(report.recommend(cells)["lane"], "nearfast")
        self.assertIsNone(report.recommend([cell("x", 0.5, 1, ok=0)])["lane"])


if __name__ == "__main__":
    unittest.main()

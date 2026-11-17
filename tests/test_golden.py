import json
import unittest
from pathlib import Path

from bench import scoring
from bench.offload import tasks

GOLDEN = Path(__file__).resolve().parent.parent / "golden"
DATA = {p.stem: [json.loads(l) for l in p.read_text("utf-8").splitlines() if l.strip()]
        for p in sorted(GOLDEN.glob("*.jsonl"))}


def lines(text, prefix):
    return [l for l in text.splitlines() if l.startswith(prefix)]


class Golden(unittest.TestCase):
    def test_files(self):
        self.assertEqual(set(DATA), set(scoring.ALL_TASKS))

    def test_ids_and_counts(self):
        for name, items in DATA.items():
            with self.subTest(name):
                ids = [i["id"] for i in items]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(10 <= len(ids) <= 20)
                self.assertTrue(all(i.startswith((name, name.split("-")[0])) for i in ids))

    def test_references(self):
        for name, items in DATA.items():
            for it in items:
                ref, text = it["reference"], it["input"]
                with self.subTest(it["id"]):
                    if name == "extract":
                        self.assertTrue(ref["key"])
                        self.assertIsInstance(ref["records"], list)  # may be empty (no-record case)
                        for rec in ref["records"]:
                            self.assertTrue(all(k in rec for k in ref["key"]))
                    elif name == "triage-log":
                        for f in ref["failures"]:
                            self.assertIn(f, text)
                    elif name == "diff-review":
                        for issue in ref["issues"]:
                            k = issue["key"]
                            self.assertTrue(any(k in l for l in lines(text, "+")))
                            self.assertFalse(any(k in l for l in lines(text, "-")))
                    elif name == "summarize":
                        for group in ref["facts"]:
                            self.assertTrue(any(a.casefold() in text.casefold() for a in group), group)
                    elif name == "translate":
                        for s in ref["preserve"]:
                            self.assertIn(s, text)
                            self.assertIn(s, ref["translation"])
                    elif name == "commit-message":
                        self.assertTrue(set(ref["types"]) <= set(scoring.CONVENTIONAL_TYPES))

    def test_render(self):
        for name, items in DATA.items():
            for it in items:
                with self.subTest(it["id"]):
                    tasks.render(tasks.get(name), it["input"], it.get("arguments") or {})


if __name__ == "__main__":
    unittest.main()

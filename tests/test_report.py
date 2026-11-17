import unittest

from bench import report


class Reproducible(unittest.TestCase):
    def test_results_match(self):
        if not (report.RESULTS / "summary.json").exists():
            self.skipTest("no committed results")
        for name, text in report.outputs().items():
            with self.subTest(name):
                self.assertEqual((report.ROOT / name).read_bytes(), text.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()

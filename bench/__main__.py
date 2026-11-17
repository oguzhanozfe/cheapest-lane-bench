"""Demo: needs no key and no model.

    python -m bench demo          # rescore the committed runs, rebuild the report and docs/index.html
    python -m bench demo --live   # also run one golden item on the first available lane:
                                  # GEMINI_API_KEY -> Gemini Flash-Lite, else local Ollama, else replay
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request

from . import report
from .lanes import LANES
from .run import load_golden, load_jsonl, run_one, run_path
from .scoring import score

LIVE_TASK, LIVE_ITEM = "extract", "extract-01"


def pick_lane() -> str | None:
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini-3.5-flash-lite"
    try:
        with urllib.request.urlopen(os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/tags",
                                    timeout=3) as response:
            installed = {m["name"] for m in json.load(response).get("models", [])}
    except (OSError, ValueError):
        return None
    for name in ("qwen3.5-4b-local", "qwen3.5-9b-local"):
        if LANES[name].model in installed:
            return name
    return None


def live() -> None:
    item = next(i for i in load_golden(LIVE_TASK) if i["id"] == LIVE_ITEM)
    lane = pick_lane()
    if lane is None:
        recorded = next(r for r in load_jsonl(run_path("qwen3.5-4b-local", LIVE_TASK)) if r["id"] == LIVE_ITEM)
        print(f"mode: replay (recorded {recorded['model']}, {recorded['at'][:10]}); "
              "no GEMINI_API_KEY and no local Ollama model found")
        result = recorded
    else:
        print(f"mode: live ({lane}, model {LANES[lane].model})")
        started = time.monotonic()
        result = run_one(LANES[lane], LIVE_TASK, item, attempts=1, timeout=120)
        if result is None:  # run_one maps timeouts and quota errors to None
            print("the lane did not answer (timeout or quota); nothing to score")
            return
        print(f"answered in {time.monotonic() - started:.1f}s")
    detail = score(LIVE_TASK, item, result.get("content"))
    print(f"{LIVE_TASK}/{LIVE_ITEM}: score {detail['score']:.2f} "
          f"({detail.get('matched_records', 0)}/{detail.get('expected_records', 0)} records matched)")
    print((result.get("content") or "")[:400])


def demo(args: argparse.Namespace) -> None:
    started = time.monotonic()
    summary = report.build()
    lanes = ", ".join(summary["lanes"])
    print(f"mode: replay (recorded runs of {lanes}; 2026-11-17)")
    report.write(report.outputs())
    print(f"rescored {sum(len(v) for v in summary['items'].values())} recorded outputs in "
          f"{time.monotonic() - started:.1f}s; wrote results/ and docs/index.html\n")
    print(f"{'chore':15} {'cheapest lane that holds quality':32} {'quality':>7}  {'best lane':24} {'best':>5}")
    for task, data in summary["tasks"].items():
        rec = data["recommendation"]
        print(f"{task:15} {rec['lane']:32} {rec['quality']:7.2f}  {rec['best_lane']:24} {rec['best_quality']:5.2f}")
    print("\nopen docs/index.html for the tables and frontier chart")
    if args.live:
        print()
        live()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m bench", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    demo_parser = sub.add_parser("demo", help="rescore recorded runs offline and rebuild the report")
    demo_parser.add_argument("--live", action="store_true", help="also run one item on an available lane")
    args = parser.parse_args()
    demo(args)


if __name__ == "__main__":
    main()

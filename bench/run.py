"""Run golden items through lanes and record raw outputs. Resumable: finished items are skipped.

    python -m bench.run --lanes qwen3.5-4b-local,gemini-3.5-flash-lite --tasks extract --limit 3
"""
from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .lanes import LANES, Lane, LaneError, generate
from .offload import PINNED_COMMIT, tasks
from .scoring import ALL_TASKS

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "golden"
RUNS = ROOT / "results" / "runs"
_write_lock = threading.Lock()
NUM_CTX = 8192
# Lane errors that mean the model itself failed the item (scored 0). Everything else is
# treated as a capacity failure and the item stays unattempted.
MODEL_FAILURES = ("output budget", "empty answer", "empty message")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def load_golden(task: str) -> list[dict]:
    return load_jsonl(GOLDEN / f"{task}.jsonl")


def run_path(lane: str, task: str) -> Path:
    return RUNS / lane / f"{task}.jsonl"


def run_one(lane: Lane, task_name: str, item: dict, attempts: int, timeout: float = 300.0) -> dict:
    task = tasks.get(task_name)
    messages = tasks.render(task, item["input"], item.get("arguments") or {})
    record = {"id": item["id"], "task": task_name, "lane": lane.name, "model": lane.model,
              "offload_commit": PINNED_COMMIT,
              "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    for attempt in range(attempts):
        try:
            # Golden inputs are under ~2k tokens; an 8k window avoids reloading the shared
            # Ollama model at llm-offload's 32k default and does not change what the model sees.
            out = generate(lane, messages, schema=task.schema, num_ctx=min(task.num_ctx, NUM_CTX),
                           num_predict=task.num_predict, timeout=timeout)
            cost = lane.cost(out["prompt_tokens"], out["output_tokens"], out["seconds"])
            return {**record, "status": "ok", **out, "cost_usd": round(cost, 8)}
        except LaneError as error:
            message = str(error)
            if any(marker in message for marker in MODEL_FAILURES):
                # The model answered but the answer is unusable: that is a quality result.
                return {**record, "status": "error", "error": message[:300], "content": None}
            if attempt == attempts - 1:
                # Timeouts, 429/503, dropped connections: capacity, not quality. Leave the
                # item unattempted so it is neither scored nor counted.
                print(f"{lane.name:30} {task_name:15} {item['id']:20} skip  {message[:80]}", flush=True)
                return None
            time.sleep(15 * (attempt + 1))  # shared Ollama / rate limits: back off and retry
    raise AssertionError("unreachable")


def run_lane(lane: Lane, task_names: list[str], limit: int | None, attempts: int, timeout: float = 300.0,
             pace: float = 0.0) -> None:
    for task_name in task_names:
        path = run_path(lane.name, task_name)
        done = {r["id"] for r in load_jsonl(path) if r.get("status") == "ok"}
        for item in load_golden(task_name)[:limit]:
            if item["id"] in done:
                continue
            result = run_one(lane, task_name, item, attempts, timeout)
            time.sleep(pace)  # stay under per-minute token limits on free tiers
            if result is None:
                continue
            with _write_lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                kept = [r for r in load_jsonl(path) if r["id"] != item["id"]]
                kept.append(result)
                kept.sort(key=lambda r: r["id"])
                path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in kept), "utf-8")
            print(f"{lane.name:30} {task_name:15} {item['id']:20} {result['status']:5} "
                  f"{result.get('seconds', '')}", flush=True)


def ollama_digests(url: str = "http://127.0.0.1:11434") -> dict:
    with urllib.request.urlopen(url + "/api/tags", timeout=10) as response:
        tags = json.load(response)
    return {m["name"]: m.get("digest", "") for m in tags.get("models", [])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lanes", default=",".join(LANES))
    parser.add_argument("--tasks", default=",".join(ALL_TASKS))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=300.0, help="seconds per model call")
    parser.add_argument("--pace", type=float, default=0.0, help="seconds to wait between calls on a lane")
    args = parser.parse_args()
    lanes = [LANES[name] for name in args.lanes.split(",")]
    task_names = args.tasks.split(",")
    if any(lane.kind == "ollama" for lane in lanes):
        meta = ROOT / "results" / "ollama-models.json"
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(json.dumps(ollama_digests(), indent=2, sort_keys=True) + "\n", "utf-8")
    # One worker per lane, except that all Ollama lanes share a single worker: the
    # Ollama server is shared with other users of this machine.
    groups: dict[str, list[Lane]] = {}
    for lane in lanes:
        groups.setdefault("ollama" if lane.kind == "ollama" else lane.name, []).append(lane)
    with ThreadPoolExecutor(max_workers=len(groups)) as pool:
        futures = [pool.submit(lambda group=group: [run_lane(lane, task_names, args.limit, args.attempts, args.timeout, args.pace)
                                                    for lane in group]) for group in groups.values()]
        for future in futures:
            future.result()


if __name__ == "__main__":
    main()

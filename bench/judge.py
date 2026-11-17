"""Rubric LLM judge for the free-text tasks. Weaker evidence than the deterministic checks.

Each recorded output is graded 1-5 against the hand-written reference by a primary
judge; a second judge from a different vendor grades the same items so report.py can
state how often the two agree. Resumable like run.py.

    python -m bench.judge --judges primary,second
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from .lanes import Lane, LaneError, generate
from .offload import tasks
from .run import ROOT, load_golden, load_jsonl
from .scoring import TEXT_TASKS

JUDGE_DIR = ROOT / "results" / "judge"

JUDGES: dict[str, Lane] = {
    # Neither judge is one of the benchmarked lanes. Both are Google models (the only
    # judges with free quota on the run date), so shared-vendor bias is not ruled out.
    # Primary grades every free-text output; Gemma has the larger free daily quota.
    # The second judge only spot-checks a fixed sample (Gemini Flash quota is ~20/day).
    "primary": Lane("judge-primary", "gemini-openai", "gemma-4-31b-it"),
    "second": Lane("judge-second", "gemini", "gemini-3-flash-preview", thinking="low"),
}

RUBRICS = {
    "summarize": (
        "5: every key fact of the reference is present, nothing is invented or distorted, bullet limit respected.\n"
        "4: one minor key fact missing or slightly imprecise; nothing invented.\n"
        "3: several key facts missing, or one imprecise number/name.\n"
        "2: mostly vague or misses most key facts, or contains one invented/wrong fact.\n"
        "1: wrong, off-topic, or several invented facts."),
    "commit-message": (
        "5: accurately says what the diff does, in the right direction (added vs removed), right "
        "Conventional Commits type, concise, no invented details.\n"
        "4: accurate with a small omission or a slightly off type/scope.\n"
        "3: partly accurate or too vague to be useful as is.\n"
        "2: misleading about the main change, or describes it in the wrong direction.\n"
        "1: wrong, hallucinated, or not a commit message."),
    "translate": (
        "5: faithful and fluent in the target language; Markdown, code, links, paths and numbers intact.\n"
        "4: faithful with minor awkwardness or one small slip.\n"
        "3: meaning mostly preserved but with clear errors, omissions, or a damaged code/link.\n"
        "2: major omissions or mistranslations, or large parts left untranslated.\n"
        "1: wrong language, unusable, or content invented."),
}

REFERENCE_FIELD = {"summarize": "summary", "commit-message": "message", "translate": "translation"}

SYSTEM = ("You grade one output of a bounded text chore against a hand-written reference answer. "
          "The reference shows what a good answer contains; a candidate may word things differently. "
          "Return only a JSON object: {\"score\": <integer 1-5>, \"reason\": \"<at most 25 words>\"}.")


def judge_messages(task_name: str, item: dict, candidate: str) -> list[dict]:
    task = tasks.get(task_name)
    instruction = task.template.split("\n")[0].format(
        **{k: v for k, v in {"bullets": "8", "focus": "the whole content", "target": "",
                             **(item.get("arguments") or {})}.items()})
    user = (f"TASK: {instruction}\nTASK RULES: {task.system}\n\n"
            f"RUBRIC:\n{RUBRICS[task_name]}\n\n"
            f"--- INPUT ---\n{item['input']}\n--- END INPUT ---\n\n"
            f"--- REFERENCE ANSWER ---\n{item['reference'][REFERENCE_FIELD[task_name]]}\n--- END REFERENCE ---\n\n"
            f"--- CANDIDATE ANSWER ---\n{candidate}\n--- END CANDIDATE ---\n\nGrade the candidate.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def parse_score(content: str) -> int | None:
    match = re.search(r'"score"\s*:\s*"?([1-5])', content) or re.search(r"\b([1-5])\b", content)
    return int(match.group(1)) if match else None


def judge_path(judge: str, lane: str, task: str) -> Path:
    return JUDGE_DIR / judge / lane / f"{task}.jsonl"


def run_judge(judge_name: str, lanes: list[str] | None, limit: int | None) -> None:
    judge = JUDGES[judge_name]
    for task_name in TEXT_TASKS:
        golden = {item["id"]: item for item in load_golden(task_name)}
        for run_file in sorted((ROOT / "results" / "runs").glob(f"*/{task_name}.jsonl")):
            lane = run_file.parent.name
            if lanes and lane not in lanes:
                continue
            path = judge_path(judge_name, lane, task_name)
            done = {r["id"] for r in load_jsonl(path) if r.get("score") is not None}
            todo = [r for r in load_jsonl(run_file) if r.get("status") == "ok" and r["id"] not in done]
            for record in todo[:limit]:
                messages = judge_messages(task_name, golden[record["id"]], record["content"])
                result = {"id": record["id"], "lane": lane, "task": task_name, "judge": judge.model}
                try:
                    out = generate(judge, messages, schema=None, num_ctx=0, num_predict=1024, timeout=300)
                    result.update(score=parse_score(out["content"]), raw=out["content"].strip()[:400])
                except LaneError as error:
                    result.update(score=None, error=str(error)[:200])
                kept = [r for r in load_jsonl(path) if r["id"] != record["id"]] + [result]
                kept.sort(key=lambda r: r["id"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in kept), "utf-8")
                print(f"{judge_name:8} {lane:30} {record['id']:20} {result.get('score')}", flush=True)
                time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judges", default="primary,second")
    parser.add_argument("--lanes")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    lanes = args.lanes.split(",") if args.lanes else None
    for name in args.judges.split(","):
        run_judge(name, lanes, args.limit)


if __name__ == "__main__":
    main()

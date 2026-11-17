"""Score recorded outputs and write the cost/quality frontier. Needs no model or network.

    python -m bench.report            # writes results/{summary.json,report.md,frontier.svg,frontier.html} and the README block
    python -m bench.report --check    # exit 1 if the committed files differ from a fresh rebuild
"""
from __future__ import annotations

import argparse
import html
import json
import math
import random
import statistics
import sys

from .judge import JUDGES, judge_path
from .lanes import LANES
from .run import ROOT, load_golden, load_jsonl, run_path
from .scoring import ALL_TASKS, TEXT_TASKS, score

RESULTS = ROOT / "results"
TOLERANCE = 0.05  # a lane "holds quality" within 5 points of the best lane on that task

# Lanes this machine has but that could not be measured on the run date (2026-11-17).
UNAVAILABLE = {
    "deepseek-flash": "API key present but the account has no balance (HTTP 402); not topped up for this run.",
    "codex-luna (gpt-5.6-luna)": "Codex CLI present but the ChatGPT account was over its usage pressure line.",
    "rtx-3090 qwen3.8:27b": "Remote GPU box was unreachable on the run date.",
}


def bootstrap_ci(values: list[float], seed: int = 7, rounds: int = 2000) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(rounds))
    return (round(means[int(0.025 * rounds)], 4), round(means[int(0.975 * rounds) - 1], 4))


def item_rows(task: str, lane: str) -> list[dict]:
    runs = {r["id"]: r for r in load_jsonl(run_path(lane, task))}
    judged = {name: {r["id"]: r.get("score") for r in load_jsonl(judge_path(name, lane, task))} for name in JUDGES}
    rows = []
    for item in load_golden(task):
        record = runs.get(item["id"])
        if record is None:
            continue  # not attempted (lane quota ran out): missing coverage, not a quality failure
        ok = record.get("status") == "ok"
        detail = score(task, item, record.get("content") if ok else None)
        row = {"id": item["id"], "ok": ok, "det": detail["score"], "detail": detail,
               "seconds": record.get("seconds"), "prompt_tokens": record.get("prompt_tokens", 0),
               "output_tokens": record.get("output_tokens", 0), "cost_usd": record.get("cost_usd", 0.0),
               "judges": {name: judged[name].get(item["id"]) for name in JUDGES}}
        quality = row["det"]
        if task in TEXT_TASKS:
            primary = row["judges"]["primary"]
            if not ok:
                quality = 0.0
            elif primary is not None:
                quality = 0.5 * row["det"] + 0.5 * (primary - 1) / 4
            else:
                row["judge_missing"] = True
        row["quality"] = round(quality, 4)
        rows.append(row)
    return rows


def same_basis(rows_by_lane: list[list[dict]]) -> None:
    """If any output of a chore lacks a primary grade, score every lane on that chore
    deterministically, so judged and unjudged numbers are never compared."""
    if any(r.get("judge_missing") for rows in rows_by_lane for r in rows):
        for rows in rows_by_lane:
            for r in rows:
                r["quality"] = r["det"] if r["ok"] else 0.0
                r["judge_missing"] = True


def aggregate(task: str, lane: str, rows: list[dict], total: int) -> dict:
    ok = [r for r in rows if r["ok"]]
    qualities = [r["quality"] for r in rows]
    cost = statistics.fmean([r["cost_usd"] for r in ok]) if ok else 0.0
    return {
        "task": task, "lane": lane, "items": total, "attempted": len(rows), "ok": len(ok),
        "complete": len(rows) == total,
        "quality": round(statistics.fmean(qualities), 4) if rows else 0.0,
        "quality_ci95": bootstrap_ci(qualities),
        "deterministic": round(statistics.fmean([r["det"] for r in rows]), 4) if rows else 0.0,
        "judge_mean": (round(statistics.fmean(j), 3) if (j := [r["judges"]["primary"] for r in rows
                                                              if r["judges"]["primary"] is not None]) else None),
        "judged": not any(r.get("judge_missing") for r in rows),
        "p50_seconds": round(statistics.median([r["seconds"] for r in ok]), 2) if ok else None,
        "mean_prompt_tokens": round(statistics.fmean([r["prompt_tokens"] for r in ok])) if ok else 0,
        "mean_output_tokens": round(statistics.fmean([r["output_tokens"] for r in ok])) if ok else 0,
        "usd_per_1k_items": round(cost * 1000, 4),
    }


def frontier(cells: list[dict]) -> list[str]:
    """Lanes not dominated: no other lane is at most as costly and strictly better, or cheaper and as good."""
    keep = []
    for a in cells:
        dominated = any(
            b is not a and b["usd_per_1k_items"] <= a["usd_per_1k_items"] and b["quality"] >= a["quality"]
            and (b["usd_per_1k_items"] < a["usd_per_1k_items"] or b["quality"] > a["quality"])
            for b in cells)
        if not dominated:
            keep.append(a["lane"])
    return keep


def recommend(cells: list[dict]) -> dict:
    measured = [c for c in cells if c["ok"] and c.get("complete", True)]
    if not measured:
        return {"lane": None, "reason": "no lane produced output"}
    best = max(measured, key=lambda c: c["quality"])
    bar = best["quality"] - TOLERANCE
    holding = [c for c in measured if c["quality"] >= bar]
    pick = min(holding, key=lambda c: (c["usd_per_1k_items"], c["p50_seconds"] or 1e9))
    return {"lane": pick["lane"], "quality": pick["quality"], "best_lane": best["lane"],
            "best_quality": best["quality"], "bar": round(bar, 4), "usd_per_1k_items": pick["usd_per_1k_items"]}


def judge_agreement(all_rows: dict) -> dict:
    pairs = [(r["judges"]["primary"], r["judges"]["second"])
             for (task, _lane), rows in all_rows.items() if task in TEXT_TASKS
             for r in rows if r["judges"]["primary"] is not None and r["judges"]["second"] is not None]
    if not pairs:
        return {"pairs": 0}
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    try:
        correlation = round(statistics.correlation(xs, ys), 3)
    except (statistics.StatisticsError, AttributeError):
        correlation = None
    return {"pairs": len(pairs), "exact": round(sum(x == y for x, y in pairs) / len(pairs), 3),
            "within_1": round(sum(abs(x - y) <= 1 for x, y in pairs) / len(pairs), 3),
            "mean_primary": round(statistics.fmean(xs), 3), "mean_second": round(statistics.fmean(ys), 3),
            "pearson": correlation}


def build() -> dict:
    lanes = [name for name in LANES if any((ROOT / "results" / "runs" / name).glob("*.jsonl"))]
    all_rows = {(t, l): item_rows(t, l) for t in ALL_TASKS for l in lanes}
    for t in TEXT_TASKS:
        same_basis([all_rows[(t, l)] for l in lanes])
    tasks_out = {}
    for task in ALL_TASKS:
        total = len(load_golden(task))
        cells = [aggregate(task, lane, all_rows[(task, lane)], total) for lane in lanes
                 if all_rows[(task, lane)]]
        tasks_out[task] = {"cells": cells, "frontier": frontier([c for c in cells if c["ok"] and c["complete"]]),
                           "recommendation": recommend(cells)}
    return {
        "tolerance": TOLERANCE,
        "lanes": {name: {"model": LANES[name].model, "kind": LANES[name].kind,
                         "usd_in_per_m": LANES[name].usd_in_per_m, "usd_out_per_m": LANES[name].usd_out_per_m,
                         "price_note": LANES[name].price_note} for name in lanes},
        "unavailable": UNAVAILABLE,
        "judges": {name: lane.model for name, lane in JUDGES.items()},
        "judge_agreement": judge_agreement(all_rows),
        "tasks": tasks_out,
        "items": {f"{t}|{l}": [{k: r[k] for k in ("id", "ok", "det", "quality", "judges")} for r in rows]
                  for (t, l), rows in all_rows.items()},
    }


def fmt_usd(value: float) -> str:
    return "$0" if value == 0 else (f"${value:.4f}" if value < 1 else f"${value:.2f}")


def markdown(summary: dict) -> str:
    out = ["# Results", "", f"Quality is the mean per-item score in [0, 1]; a lane holds quality when it is within "
           f"{summary['tolerance']:.2f} of the best lane on that task. Cost is per 1,000 items. Lanes marked "
           "partial ran out of quota before every item was attempted; they are shown but not ranked.", ""]
    out += ["## Recommendation", "", "| Task | Cheapest lane that holds quality | Quality | Best lane | Best quality | Cost / 1k |",
            "| --- | --- | --- | --- | --- | --- |"]
    for task, data in summary["tasks"].items():
        rec = data["recommendation"]
        if rec.get("lane"):
            out.append(f"| {task} | **{rec['lane']}** | {rec['quality']:.2f} | {rec['best_lane']} | "
                       f"{rec['best_quality']:.2f} | {fmt_usd(rec['usd_per_1k_items'])} |")
    for task, data in summary["tasks"].items():
        out += ["", f"## {task}", "", "| Lane | Attempted / OK | Quality (95% CI) | Deterministic | Judge 1-5 | p50 s | "
                "Tokens in/out | Cost / 1k | Frontier |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for c in sorted(data["cells"], key=lambda c: -c["quality"]):
            lo, hi = c["quality_ci95"]
            judge = "" if c["judge_mean"] is None else f"{c['judge_mean']:.2f}"
            if task in TEXT_TASKS and not c["judged"]:
                judge = (judge + " " if judge else "") + "(pending; quality = deterministic only)"
            out.append(f"| {c['lane']} | {c['attempted']}/{c['items']} ({c['ok']} ok){'' if c['complete'] else ' partial'} | {c['quality']:.2f} ({lo:.2f}-{hi:.2f}) | "
                       f"{c['deterministic']:.2f} | {judge} | {c['p50_seconds'] if c['p50_seconds'] is not None else '-'} | "
                       f"{c['mean_prompt_tokens']}/{c['mean_output_tokens']} | {fmt_usd(c['usd_per_1k_items'])} | "
                       f"{'yes' if c['lane'] in data['frontier'] else ''} |")
    agreement = summary["judge_agreement"]
    out += ["", "## Judge agreement", ""]
    if agreement.get("pairs"):
        out.append(f"{agreement['pairs']} outputs graded by both judges ({summary['judges']['primary']} and "
                   f"{summary['judges']['second']}): exact agreement {agreement['exact']:.0%}, within one point "
                   f"{agreement['within_1']:.0%}, Pearson r = {agreement['pearson']}, mean score "
                   f"{agreement['mean_primary']} vs {agreement['mean_second']}.")
    else:
        out.append("No outputs were graded by both judges.")
    out += ["", "## Lanes not measured", ""] + [f"- **{k}**: {v}" for k, v in summary["unavailable"].items()]
    return "\n".join(out) + "\n"


COLORS = ["#2a6fdb", "#d9480f", "#2b8a3e", "#ae3ec9", "#e8590c", "#0b7285", "#5c940d"]


def svg(summary: dict) -> str:
    lanes = list(summary["lanes"])
    color = {lane: COLORS[i % len(COLORS)] for i, lane in enumerate(lanes)}
    w, h, pad = 300, 220, 42
    cols, tasks = 3, list(summary["tasks"])
    rows = math.ceil(len(tasks) / cols)
    width, height = cols * (w + 20) + 20, rows * (h + 40) + 40 + 22 * math.ceil(len(lanes) / 3)
    costs = [c["usd_per_1k_items"] for t in tasks for c in summary["tasks"][t]["cells"]]
    top = math.log10(max(costs + [0.01]) * 2 + 0.001)
    bottom = math.log10(0.0001)

    def x_of(cost: float) -> float:
        return pad + (math.log10(max(cost, 0.0001)) - bottom) / (top - bottom) * (w - pad - 10)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="system-ui, sans-serif" font-size="11">',
             f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    for index, task in enumerate(tasks):
        ox, oy = 20 + (index % cols) * (w + 20), 20 + (index // cols) * (h + 40)
        data = summary["tasks"][task]
        parts.append(f'<g transform="translate({ox},{oy})">')
        parts.append(f'<text x="{pad}" y="12" font-weight="600" font-size="13">{html.escape(task)}</text>')
        parts.append(f'<line x1="{pad}" y1="{h - 20}" x2="{w - 10}" y2="{h - 20}" stroke="#888"/>'
                     f'<line x1="{pad}" y1="20" x2="{pad}" y2="{h - 20}" stroke="#888"/>')
        for q in (0, 0.5, 1):
            y = h - 20 - q * (h - 40)
            parts.append(f'<text x="{pad - 6}" y="{y + 4}" text-anchor="end" fill="#555">{q:.1f}</text>'
                         f'<line x1="{pad}" y1="{y}" x2="{w - 10}" y2="{y}" stroke="#eee"/>')
        for tick in (0.0001, 0.01, 1):
            if math.log10(tick) <= top:
                parts.append(f'<text x="{x_of(tick)}" y="{h - 6}" text-anchor="middle" fill="#555">'
                             f'{"≤$0.0001" if tick == 0.0001 else fmt_usd(tick)}</text>')
        points = sorted((c for c in data["cells"] if c["lane"] in data["frontier"]), key=lambda c: c["usd_per_1k_items"])
        if len(points) > 1:
            path = " ".join(f"{x_of(c['usd_per_1k_items']):.1f},{h - 20 - c['quality'] * (h - 40):.1f}" for c in points)
            parts.append(f'<polyline points="{path}" fill="none" stroke="#bbb" stroke-dasharray="4 3"/>')
        for c in data["cells"]:
            cx, cy = x_of(c["usd_per_1k_items"]), h - 20 - c["quality"] * (h - 40)
            ring = ' stroke="#000" stroke-width="2"' if c["lane"] == data["recommendation"].get("lane") else ""
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{color[c["lane"]]}"{ring}>'
                         f'<title>{html.escape(c["lane"])}: quality {c["quality"]:.2f}, '
                         f'{fmt_usd(c["usd_per_1k_items"])} per 1k</title></circle>')
        parts.append("</g>")
    ly = rows * (h + 40) + 20
    parts.append(f'<text x="20" y="{ly}" fill="#333">x: est. USD per 1,000 items (log; local = electricity, free tiers at paid list price). '
                 'y: quality 0-1. Black ring: recommended lane. Dashed: frontier.</text>')
    for i, lane in enumerate(lanes):
        lx, lyy = 20 + (i % 3) * 320, ly + 20 + (i // 3) * 20
        parts.append(f'<circle cx="{lx + 5}" cy="{lyy - 4}" r="5" fill="{color[lane]}"/>'
                     f'<text x="{lx + 15}" y="{lyy}">{html.escape(lane)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def page(summary: dict, report_md: str, chart: str) -> str:
    body = html.escape(report_md)
    return ("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
            "<title>Cheapest lane frontier</title><style>body{font-family:system-ui,sans-serif;max-width:1000px;"
            "margin:24px auto;padding:0 16px;background:#fff;color:#111}svg{max-width:100%;height:auto}"
            "pre{white-space:pre-wrap;font-size:13px}</style></head><body><h1>Cheapest lane that holds quality</h1>"
            f"{chart}<pre>{body}</pre></body></html>\n")


START, END = "<!-- results:start -->", "<!-- results:end -->"


def readme_with(report_md: str) -> str | None:
    """README with its generated results block replaced, so README numbers come from results/."""
    path = ROOT / "README.md"
    if not path.exists():
        return None
    text = path.read_text("utf-8")
    if START not in text or END not in text:
        return text
    body = report_md.split("\n", 2)[2].replace("\n## ", "\n### ")  # drop "# Results", demote headings
    head, rest = text.split(START, 1)
    return head + START + "\n" + body + END + rest.split(END, 1)[1]


def outputs() -> dict[str, str]:
    summary = build()
    report_md = markdown(summary)
    chart = svg(summary)
    files = {"results/summary.json": json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
             "results/report.md": report_md, "results/frontier.svg": chart,
             "results/frontier.html": page(summary, report_md, chart)}
    readme = readme_with(report_md)
    if readme is not None:
        files["README.md"] = readme
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = outputs()
    if args.check:
        stale = [name for name, text in files.items()
                 if not (ROOT / name).exists() or (ROOT / name).read_text("utf-8") != text]
        if stale:
            print("stale or missing:", ", ".join(stale))
            sys.exit(1)
        print("results are reproducible from the recorded outputs")
        return
    for name, text in files.items():
        (ROOT / name).write_text(text, "utf-8")
    print(files["results/report.md"])


if __name__ == "__main__":
    main()

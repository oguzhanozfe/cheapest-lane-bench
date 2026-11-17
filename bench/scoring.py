"""Deterministic per-item scores in [0, 1]. Parsing and quote checks are llm-offload's own.

JSON tasks (extract, triage-log, diff-review) are scored entirely here. Free-text tasks
(summarize, commit-message, translate) get a deterministic part here and a rubric
judge part in judge.py; report.py blends them 50/50.
"""
from __future__ import annotations

import re
from collections import Counter

from .offload import tasks

JSON_TASKS = ("extract", "triage-log", "diff-review")
TEXT_TASKS = ("summarize", "commit-message", "translate")
ALL_TASKS = JSON_TASKS + TEXT_TASKS
CONVENTIONAL_TYPES = ("feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert")


def norm(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().strip(".,;:").casefold()


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^\d.\-]", "", str(value).replace(",", ""))
    try:
        return float(text) if text not in ("", "-", ".") else None
    except ValueError:
        return None


def _words(value) -> set[str]:
    return {w for w in re.findall(r"\w+", str(value).casefold()) if len(w) > 1}


def values_equal(ref, pred, fuzzy: bool = False) -> bool:
    if ref is None:
        return pred is None or norm(pred) in ("", "null", "none", "n/a")
    if pred is None:
        return False
    if fuzzy:
        ref_words = _words(ref)
        return bool(ref_words) and len(ref_words & _words(pred)) / len(ref_words) >= 0.5
    if isinstance(ref, (int, float)) and not isinstance(ref, bool):
        number = _number(pred)
        return number is not None and abs(number - float(ref)) < 0.01
    ref_digits = re.sub(r"\D", "", str(ref))
    if len(ref_digits) >= 7 and ref_digits == re.sub(r"\D", "", str(pred)):
        return True  # phone numbers written with different separators
    return norm(ref) == norm(pred)


def _f1(tp_p: float, n_pred: int, tp_r: float, n_ref: int) -> float:
    if n_pred == 0 and n_ref == 0:
        return 1.0
    precision = tp_p / n_pred if n_pred else 0.0
    recall = tp_r / n_ref if n_ref else 0.0
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def _parse(task_name: str, content: str):
    try:
        return tasks.parse_result(tasks.get(task_name), content), None
    except tasks.TaskError as error:
        return None, str(error)


def _items(parsed, key: str) -> list[dict]:
    value = parsed.get(key) if isinstance(parsed, dict) else None
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _quote_rate(task_name: str, parsed, source: str) -> tuple[float, int, int]:
    quoted = [x for k in ("findings", "failures") for x in _items(parsed, k)
              if isinstance(x.get("quote"), str) and x["quote"].strip()]
    bad = len(tasks.check_quotes(tasks.get(task_name), parsed, source))
    return (1.0 if not quoted else 1 - bad / len(quoted)), len(quoted), bad


def score_extract(item: dict, content: str) -> dict:
    parsed, error = _parse("extract", content)
    if error:
        return {"score": 0.0, "valid_json": False, "error": error}
    ref = item["reference"]
    keys, fuzzy = ref["key"], set(ref.get("fuzzy", []))
    ref_records = ref["records"]
    fields = sorted({f for r in ref_records for f in r} | set(keys))
    preds = _items(parsed, "records")
    used, tp = set(), 0
    for record in ref_records:
        for index, pred in enumerate(preds):
            if index in used:
                continue
            if all(values_equal(record.get(k), pred.get(k), k in fuzzy) for k in keys):
                used.add(index)
                tp += sum(values_equal(record.get(f), pred.get(f), f in fuzzy) for f in fields)
                break
    score = _f1(tp, len(preds) * len(fields), tp, len(ref_records) * len(fields))
    return {"score": round(score, 4), "valid_json": True, "records": len(preds),
            "matched_records": len(used), "expected_records": len(ref_records)}


def _matched(items: list[dict], ids: list[str], fields: tuple[str, ...]):
    blobs = [" ".join(str(x.get(f, "")) for f in fields).casefold() for x in items]
    hit_ids = [i for i in ids if any(i.casefold() in b for b in blobs)]
    hit_items = [b for b in blobs if any(i.casefold() in b for i in ids)]
    return len(hit_items), len(hit_ids)


def score_triage(item: dict, content: str) -> dict:
    parsed, error = _parse("triage-log", content)
    if error:
        return {"score": 0.0, "valid_json": False, "error": error}
    ids = item["reference"]["failures"]
    failures = _items(parsed, "failures")
    good_items, good_ids = _matched(failures, ids, ("name", "message", "quote"))
    f1 = _f1(good_items, len(failures), good_ids, len(ids))
    rate, quotes, bad = _quote_rate("triage-log", parsed, item["input"])
    return {"score": round(f1 * rate, 4), "valid_json": True, "f1": round(f1, 4), "quote_rate": round(rate, 4),
            "quotes": quotes, "unverified_quotes": bad, "reported": len(failures), "expected": len(ids)}


def score_diff(item: dict, content: str) -> dict:
    parsed, error = _parse("diff-review", content)
    if error:
        return {"score": 0.0, "valid_json": False, "error": error}
    keys = [issue["key"] for issue in item["reference"]["issues"]]
    findings = _items(parsed, "findings")
    good_items, good_ids = _matched(findings, keys, ("quote", "note"))
    f1 = _f1(good_items, len(findings), good_ids, len(keys))
    rate, quotes, bad = _quote_rate("diff-review", parsed, item["input"])
    return {"score": round(f1 * rate, 4), "valid_json": True, "f1": round(f1, 4), "quote_rate": round(rate, 4),
            "quotes": quotes, "unverified_quotes": bad, "reported": len(findings), "expected": len(keys)}


def _coverage(text: str, groups: list[list[str]]) -> float:
    low = text.casefold()
    return sum(any(alt.casefold() in low for alt in group) for group in groups) / len(groups) if groups else 1.0


HEADER = re.compile(r"^(?P<type>[a-z]+)(\([^)\n]+\))?!?: \S.*$")


def score_commit(item: dict, content: str) -> dict:
    text = tasks.parse_result(tasks.get("commit-message"), content)
    lines = text.splitlines()
    header = lines[0].strip() if lines else ""
    match = HEADER.match(header)
    body = [line for line in lines[2:] if line.strip()]
    format_ok = bool(match) and len(header) <= 72 and "```" not in text and \
        (len(lines) == 1 or lines[1].strip() == "") and len(body) <= 4
    type_ok = bool(match) and match.group("type") in item["reference"]["types"]
    coverage = _coverage(text, item["reference"]["keywords"])
    return {"score": round((format_ok + type_ok + coverage) / 3, 4), "format_ok": format_ok,
            "type_ok": type_ok, "keyword_coverage": round(coverage, 4)}


def score_summarize(item: dict, content: str) -> dict:
    text = tasks.parse_result(tasks.get("summarize"), content)
    limit = int(item.get("arguments", {}).get("bullets", 8))
    bullets = [line for line in text.splitlines() if re.match(r"^\s*([-*•]|\d+[.)])\s+", line)]
    bullets_ok = 1 <= len(bullets) <= limit
    coverage = _coverage(text, item["reference"]["facts"])
    return {"score": round(0.8 * coverage + 0.2 * bullets_ok, 4), "fact_coverage": round(coverage, 4),
            "bullets": len(bullets), "bullets_ok": bullets_ok}


def chrf(hypothesis: str, reference: str, max_n: int = 6, beta: float = 2.0) -> float:
    """Character n-gram F-score (Popovic 2015), whitespace removed, averaged over n=1..6."""
    hyp, ref = re.sub(r"\s+", "", hypothesis), re.sub(r"\s+", "", reference)
    precisions, recalls = [], []
    for n in range(1, max_n + 1):
        h = Counter(hyp[i:i + n] for i in range(len(hyp) - n + 1))
        r = Counter(ref[i:i + n] for i in range(len(ref) - n + 1))
        if not h or not r:
            continue
        overlap = sum((h & r).values())
        precisions.append(overlap / sum(h.values()))
        recalls.append(overlap / sum(r.values()))
    if not precisions:
        return 0.0
    p, r = sum(precisions) / len(precisions), sum(recalls) / len(recalls)
    return 0.0 if p + r == 0 else (1 + beta ** 2) * p * r / (beta ** 2 * p + r)


def score_translate(item: dict, content: str) -> dict:
    text = tasks.parse_result(tasks.get("translate"), content)
    preserve = item["reference"]["preserve"]
    kept = sum(s in text for s in preserve) / len(preserve) if preserve else 1.0
    similarity = chrf(text, item["reference"]["translation"])
    return {"score": round(0.5 * kept + 0.5 * similarity, 4), "preserved": round(kept, 4), "chrf": round(similarity, 4)}


SCORERS = {"extract": score_extract, "triage-log": score_triage, "diff-review": score_diff,
           "commit-message": score_commit, "summarize": score_summarize, "translate": score_translate}


def score(task: str, item: dict, content: str | None) -> dict:
    """Score one output; a lane error or missing output scores 0."""
    if content is None:
        return {"score": 0.0, "error": "no output"}
    return SCORERS[task](item, content)

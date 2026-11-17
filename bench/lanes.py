"""Model lanes: where a task can run, what it costs, and one generate() per kind.

Ollama lanes go through llm-offload's own backends.generate. Cloud lanes are thin
HTTP/CLI adapters that receive llm-offload's rendered messages unchanged; JSON tasks
get the same "respond with a JSON object matching this schema" suffix that
llm-offload's Codex lane uses, because only Ollama enforces a schema grammar.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .offload import backends

# Local electricity: an assumption, not a measurement. Apple-silicon package power
# under sustained generation sits roughly in this range; change it for your box.
LOCAL_WATTS = 40.0
USD_PER_KWH = 0.30


@dataclass(frozen=True)
class Lane:
    name: str
    kind: str  # ollama | gemini | gemini-openai | opencode | deepseek
    model: str
    usd_in_per_m: float = 0.0
    usd_out_per_m: float = 0.0
    price_note: str = ""
    thinking: str = "minimal"  # Gemini thinkingLevel: the cheapest the model accepts

    def cost(self, prompt_tokens: int, output_tokens: int, seconds: float) -> float:
        usd = prompt_tokens * self.usd_in_per_m / 1e6 + output_tokens * self.usd_out_per_m / 1e6
        if self.kind == "ollama":
            usd += seconds * LOCAL_WATTS / 3.6e6 * USD_PER_KWH
        return usd


# Prices are list prices per million tokens, read from the vendors' pricing pages on
# 2026-11-17 (Gemini paid tier; DeepSeek peak). The Gemini runs used the free tier,
# so the dollar column is what the same traffic would cost on the paid tier.
LANES: dict[str, Lane] = {lane.name: lane for lane in (
    Lane("qwen3.5-4b-local", "ollama", "qwen3.5:4b",
         price_note=f"local; electricity only at {LOCAL_WATTS:.0f} W x ${USD_PER_KWH}/kWh (assumed)"),
    Lane("qwen3.5-9b-local", "ollama", "qwen3.5:9b",
         price_note=f"local; electricity only at {LOCAL_WATTS:.0f} W x ${USD_PER_KWH}/kWh (assumed)"),
    Lane("nemotron-3.5-lightning-free", "opencode", "opencode/nemotron-3.5-lightning-free",
         price_note="OpenCode free model; $0, rate-limited, prompts may be retained by the provider"),
    Lane("gemini-3.5-flash-lite", "gemini", "gemini-3.5-flash-lite", 0.30, 2.50,
         "Gemini paid-tier list price; run on the free tier"),
    Lane("gemini-3.8-flash", "gemini", "gemini-3.8-flash", 0.75, 3.75,
         "Gemini paid-tier list price through 2026-12-31; run on the free tier", "low"),
    Lane("deepseek-flash", "deepseek", "deepseek-flash", 0.30, 1.20, "DeepSeek peak list price"),
)}


class LaneError(RuntimeError):
    pass


def _post(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    delay = 10.0
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read()[:300].decode("utf-8", "replace")
            if error.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            raise LaneError(f"HTTP {error.code}: {body}") from error
        except (urllib.error.URLError, OSError) as error:
            if attempt < 3:
                time.sleep(delay)
                continue
            raise LaneError(f"unreachable: {type(error).__name__}") from error
    raise LaneError("retries exhausted")


def _json_suffix(schema: dict | None) -> str:
    if not schema:
        return ""
    return "\n\nRespond with a single JSON object matching this schema and nothing else:\n" + json.dumps(schema)


def generate(lane: Lane, messages: list[dict], *, schema: dict | None, num_ctx: int,
             num_predict: int, timeout: float = 600.0) -> dict:
    """Return {content, prompt_tokens, output_tokens, seconds}."""
    started = time.monotonic()
    if lane.kind == "ollama":
        backend = backends.Backend(key="mac", label=f"Ollama {lane.model}",
                                   url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"),
                                   model=lane.model, max_ctx=32768, max_output=4096)
        try:
            out = backends.generate(backend, messages, num_ctx=num_ctx, num_predict=num_predict,
                                    temperature=0.0, thinking=False, fmt=schema, timeout=timeout,
                                    keep_alive="10m")
        except backends.BackendError as error:
            raise LaneError(str(error)) from error
        return {"content": out["content"], "prompt_tokens": out["prompt_tokens"],
                "output_tokens": out["output_tokens"], "seconds": out["seconds"]}

    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    user = "\n".join(m["content"] for m in messages if m["role"] != "system") + _json_suffix(schema)

    if lane.kind == "gemini":
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise LaneError("GEMINI_API_KEY is not set")
        config = {"temperature": 0, "maxOutputTokens": num_predict * 2}
        if lane.thinking:  # open-weight Gemma models reject thinkingConfig
            config["thinkingConfig"] = {"thinkingLevel": lane.thinking}
        if schema:
            config["responseMimeType"] = "application/json"
        data = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{lane.model}:generateContent",
                     {"systemInstruction": {"parts": [{"text": system}]},
                      "contents": [{"role": "user", "parts": [{"text": user}]}],
                      "generationConfig": config},
                     {"x-goog-api-key": key}, timeout)
        candidate = (data.get("candidates") or [{}])[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        content = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        usage = data.get("usageMetadata") or {}
        if not content.strip():
            raise LaneError(f"empty answer, finishReason={candidate.get('finishReason')}")
        return {"content": content, "prompt_tokens": usage.get("promptTokenCount", 0),
                "output_tokens": usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0),
                "seconds": round(time.monotonic() - started, 3)}

    if lane.kind == "gemini-openai":  # Gemini API's OpenAI-compatible endpoint; Gemma works here
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise LaneError("GEMINI_API_KEY is not set")
        data = _post("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                     {"model": lane.model, "temperature": 0, "max_tokens": num_predict * 2,
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                     {"Authorization": f"Bearer {key}"}, timeout)
        usage = data.get("usage") or {}
        content = re.sub(r"<thought>.*?</thought>", "", data["choices"][0]["message"].get("content") or "",
                         flags=re.S).strip()
        if not content:
            raise LaneError("empty answer")
        return {"content": content, "prompt_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "seconds": round(time.monotonic() - started, 3)}

    if lane.kind == "deepseek":
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise LaneError("DEEPSEEK_API_KEY is not set")
        payload = {"model": lane.model, "temperature": 0, "max_tokens": num_predict,
                   "thinking": {"type": "disabled"},
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if schema:
            payload["response_format"] = {"type": "json_object"}
        data = _post("https://api.deepseek.com/chat/completions", payload,
                     {"Authorization": f"Bearer {key}"}, timeout)
        usage = data.get("usage") or {}
        return {"content": data["choices"][0]["message"]["content"],
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "seconds": round(time.monotonic() - started, 3)}

    if lane.kind == "opencode":
        prompt = f"[SYSTEM]\n{system}\n\n[USER]\n{user}\n\n[INSTRUCTIONS]\nAnswer as the assistant. " \
                 "Do not run commands, read files or edit anything."
        with tempfile.TemporaryDirectory() as empty:  # nothing for the agent harness to read
            try:
                # Own process group: on timeout the whole tree is killed, otherwise a child
                # holding the stdout pipe keeps communicate() waiting forever.
                proc = subprocess.Popen(["opencode", "run", "--pure", "--format", "json", "-m", lane.model, prompt],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=empty,
                                        stdin=subprocess.DEVNULL, start_new_session=True)
            except OSError as error:
                raise LaneError(f"opencode failed: {type(error).__name__}") from error
            try:
                stdout, stderr = proc.communicate(timeout=min(timeout, 240))
            except subprocess.TimeoutExpired as error:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                raise LaneError("opencode timed out") from error
            done = subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)
        texts, prompt_tokens, output_tokens = [], 0, 0
        for line in done.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            part = event.get("part") or {}
            if event.get("type") == "text":
                texts.append(part.get("text", ""))
            elif event.get("type") == "step_finish":
                tokens = part.get("tokens") or {}
                prompt_tokens += tokens.get("input", 0)
                output_tokens += tokens.get("output", 0) + tokens.get("reasoning", 0)
        content = "".join(texts)
        if not content.strip():
            raise LaneError(f"opencode returned no text (exit {done.returncode}): {done.stderr[-200:]}")
        return {"content": content, "prompt_tokens": prompt_tokens, "output_tokens": output_tokens,
                "seconds": round(time.monotonic() - started, 3)}

    raise LaneError(f"unknown lane kind {lane.kind}")

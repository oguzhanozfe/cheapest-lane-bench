"""Import the task registry and runner pieces from llm-offload instead of copying them.

The benchmark measures llm-offload's own prompts and parsers, so it loads them from
a pinned checkout (scripts/fetch-llm-offload.sh) or from LLM_OFFLOAD_SRC.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PINNED_COMMIT = "c0eb687a7bf89e896c53ce0de2a35eb4652390c2"
SRC = Path(os.environ.get("LLM_OFFLOAD_SRC") or ROOT / ".deps" / "llm-offload")

if not (SRC / "offload" / "tasks.py").exists():
    raise SystemExit(f"llm-offload not found at {SRC}. Run scripts/fetch-llm-offload.sh first.")
# Keep llm-offload's state out of the user's home directory during a benchmark.
os.environ.setdefault("OFFLOAD_HOME", str(ROOT / ".deps" / "offload-home"))
sys.path.insert(0, str(SRC))

from offload import backends, tasks  # noqa: E402

__all__ = ["backends", "tasks", "PINNED_COMMIT"]

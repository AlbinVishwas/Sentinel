"""Shared helpers for the Phase 5 verification suite.

Every phase5 script imports from here for consistent output and config. Scripts
add the backend root to sys.path themselves so they run from any cwd:

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # backend/
    sys.path.insert(0, str(Path(__file__).resolve().parent))       # phase5/
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Project the live tests operate on (the seeded sandbox). Override per-script if needed.
PROJECT_PATH = os.environ.get("GITLAB_DEFAULT_PROJECT", "albinvishwas7/sentinel-test-sandbox")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

_GREEN, _RED, _DIM, _BOLD, _RESET = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


def section(title: str) -> None:
    print(f"\n{_BOLD}== {title} =={_RESET}")


def info(msg: str) -> None:
    print(f"   {_DIM}{msg}{_RESET}")


def check(label: str, ok: bool, detail: str = "") -> bool:
    mark = f"{_GREEN}PASS{_RESET}" if ok else f"{_RED}FAIL{_RESET}"
    tail = f"  {_DIM}{detail}{_RESET}" if detail else ""
    print(f"   [{mark}] {label}{tail}")
    return ok


def verdict(name: str, ok: bool) -> bool:
    mark = f"{_GREEN}PASS{_RESET}" if ok else f"{_RED}FAIL{_RESET}"
    print(f"\n{_BOLD}{name}: [{mark}]{_RESET}")
    return ok


async def run_capture(prompt: str, *, session_id: str, max_iterations: int | None = None) -> dict:
    """Drive one live agent run and capture everything the live tests assert on.

    Returns: {
      "status": "ok"|"aborted"|"error",
      "final":  <final answer text>,
      "tool_calls": [{"name": str, "args": dict}, ...],   # in call order, with args
      "error":  <error message if any>,
    }
    Uses stream_agent so tool-call *arguments* are visible (run_agent only keeps names).
    """
    from sentinel_agent.runner import stream_agent  # local import: avoids ADK load at import time

    kwargs = {"session_id": session_id}
    if max_iterations is not None:
        kwargs["max_iterations"] = max_iterations

    status, final, error = "ok", "", ""
    tool_calls: list[dict] = []
    async for ev in stream_agent(prompt, **kwargs):
        kind = ev.get("type")
        if kind == "tool_call":
            tool_calls.append({"name": str(ev.get("name", "")), "args": dict(ev.get("args") or {})})
        elif kind == "final":
            final = str(ev.get("text", ""))
        elif kind == "aborted":
            status, error = "aborted", str(ev.get("message", ""))
        elif kind == "error":
            status, error = "error", str(ev.get("message", ""))
    return {"status": status, "final": final, "tool_calls": tool_calls, "error": error}


def tool_names(capture: dict) -> list[str]:
    return [c["name"] for c in capture.get("tool_calls", [])]


def mentions_any(text: str, phrases: list[str]) -> bool:
    low = (text or "").lower()
    return any(p.lower() in low for p in phrases)

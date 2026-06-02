"""Deterministic Test 3 — Next.js streaming contract (no AI).

Drives the backend's canned multi-step stream (POST /agent/stream/mock) and validates
the exact SSE contract the Next.js frontend depends on, using the *same* frame-parsing
the browser uses (split on a blank line, take the `data:` line). This proves the
frontend can render intermediate "thought process" steps incrementally — events must
arrive spread out over time (true streaming), not in one burst, which is what avoids
UI flicker / timeouts.

  # start the backend first:  .venv/bin/uvicorn app.main:app --port 8000
  .venv/bin/python scripts/phase5/det_3_streaming.py

No Gemini, no GitLab — the mock endpoint replays a fixed sequence.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import BACKEND_URL, check, info, section, verdict  # noqa: E402

import httpx  # noqa: E402

MOCK_URL = f"{BACKEND_URL}/agent/stream/mock"
EXPECTED_TYPES = {"reasoning", "tool_call", "tool_result", "final", "done"}


async def collect_frames() -> list[tuple[float, dict]]:
    """Read the SSE stream, returning (arrival_time, event) for each parsed event.

    Mirrors the frontend's parsing in chat.tsx: buffer bytes, split on "\\n\\n",
    take the line starting with "data:".
    """
    events: list[tuple[float, dict]] = []
    buffer = ""
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", MOCK_URL, json={"prompt": "test", "session_id": "det3"}) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_text():
                buffer += chunk
                frames = buffer.split("\n\n")
                buffer = frames.pop()
                for frame in frames:
                    line = next((l for l in frame.split("\n") if l.startswith("data:")), None)
                    if line:
                        events.append((time.monotonic(), json.loads(line[5:].strip())))
    return events


async def main() -> int:
    section("Deterministic 3 — Next.js streaming contract (mock SSE)")
    info(f"GET {MOCK_URL}")

    try:
        events = await collect_frames()
    except (httpx.ConnectError, httpx.ReadError):
        check("backend reachable", False, f"start uvicorn on {BACKEND_URL} first")
        print("   [SKIP] backend not running — start it and re-run")
        return verdict("det_3_streaming", False) and 1
    except Exception as exc:  # noqa: BLE001
        check("stream consumed", False, f"{type(exc).__name__}: {exc}")
        return verdict("det_3_streaming", False) and 1

    times = [t for t, _ in events]
    evs = [e for _, e in events]
    types = [e.get("type") for e in evs]

    ok = True
    ok &= check("every frame parsed as JSON", len(evs) > 0, f"{len(evs)} events")
    ok &= check("all event types are known", set(types) <= EXPECTED_TYPES, str(sorted(set(types))))
    ok &= check("emits reasoning + tool_call + tool_result steps",
                all(t in types for t in ("reasoning", "tool_call", "tool_result")))
    ok &= check("exactly one 'final' event", types.count("final") == 1)
    ok &= check("'final' precedes terminal 'done'",
                "final" in types and types.index("final") < types.index("done") if "done" in types else False)
    ok &= check("tool_call/tool_result are paired", types.count("tool_call") == types.count("tool_result"))

    # True streaming: arrivals must be spread over time, not one burst (anti-flicker proof).
    span = (times[-1] - times[0]) if len(times) > 1 else 0.0
    ok &= check("events arrive incrementally (not one burst)", span > 0.5, f"span={span:.2f}s over {len(evs)} events")

    return 0 if verdict("det_3_streaming", ok) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

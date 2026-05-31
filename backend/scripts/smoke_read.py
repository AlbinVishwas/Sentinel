"""Phase 2 smoke test — one read-only round trip through the agent.

Sends a single prompt asking Sentinel to read issue #1 of the seeded test project
and name the file it mentions. Prints every tool call so the prompt -> tool call ->
response loop is visible. Pass = a GitLab read tool is invoked AND the answer names
the buggy file, with no write tool used.

Run from the backend/ dir:  .venv/bin/python scripts/smoke_read.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from sentinel_agent.agent import READ_TOOLS, gitlab_toolset, root_agent  # noqa: E402

PROJECT_PATH = "albinvishwas7/sentinel-test-sandbox"
PROMPT = (
    f"Read issue #1 in the GitLab project '{PROJECT_PATH}' and tell me which file it "
    "mentions. Do not modify anything."
)
APP = "sentinel"


async def main() -> None:
    session_service = InMemorySessionService()
    runner = Runner(app_name=APP, agent=root_agent, session_service=session_service)
    await session_service.create_session(app_name=APP, user_id="smoke", session_id="s1")

    msg = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    tool_calls: list[str] = []
    final_text = ""

    try:
        async for event in runner.run_async(
            user_id="smoke", session_id="s1", new_message=msg
        ):
            if event.content and event.content.parts:
                for p in event.content.parts:
                    fc = getattr(p, "function_call", None)
                    fr = getattr(p, "function_response", None)
                    if fc:
                        tool_calls.append(fc.name)
                        print(f"[tool call]   {fc.name}  args={dict(fc.args or {})}")
                    if fr:
                        print(f"[tool result] {fr.name} -> received")
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(p.text or "" for p in event.content.parts)
    finally:
        await gitlab_toolset.close()

    print("\n=== FINAL ANSWER ===")
    print(final_text.strip())

    read_used = [t for t in tool_calls if t in READ_TOOLS]
    write_used = [t for t in tool_calls if t not in READ_TOOLS]
    file_named = "parser.py" in final_text

    print("\n=== RESULT ===")
    print("tool calls      :", tool_calls)
    print("read tool used  :", bool(read_used), read_used)
    print("write tool used :", bool(write_used), write_used or "(none — good)")
    print("named the file  :", file_named)
    print("PASS            :", bool(read_used) and file_named and not write_used)


if __name__ == "__main__":
    asyncio.run(main())

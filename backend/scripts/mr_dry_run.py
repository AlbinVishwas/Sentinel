"""Phase 3 live dry-run — confirm the write path end-to-end on real GitLab.

Drives the agent to fix issue #1 by opening a Merge Request, then INDEPENDENTLY
verifies via the GitLab REST API (using the PAT directly, NOT the agent's claims)
that:
  * a new branch was created (not main),
  * a Merge Request is open from that branch -> main,
  * main's utils/parser.py is UNCHANGED (guardrail held — no direct write to main),
  * the MR branch's utils/parser.py IS fixed (has the missing colon).

Run from the backend/ dir:  .venv/bin/python scripts/mr_dry_run.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from google.adk.agents.invocation_context import LlmCallsLimitExceededError  # noqa: E402
from google.adk.agents.run_config import RunConfig  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from sentinel_agent.agent import gitlab_toolset, root_agent  # noqa: E402

PROJECT_ID = 82727935
PROJECT_PATH = "albinvishwas7/sentinel-test-sandbox"
API = os.environ.get("GITLAB_INSTANCE_URL", "https://gitlab.com").rstrip("/") + "/api/v4"
HEADERS = {"PRIVATE-TOKEN": os.environ["GITLAB_PERSONAL_ACCESS_TOKEN"]}

PROMPT = (
    f"Investigate issue #1 in the GitLab project '{PROJECT_PATH}'. Read the issue and "
    "the source file it references, then FIX the bug. Per your safety rules, create a "
    "NEW branch (e.g. 'sentinel/fix-issue-1'), commit the corrected file to that branch, "
    "and open a Merge Request from that branch into 'main'. Finally, report the Merge "
    "Request URL."
)


def gl_get(path: str, **params):
    r = httpx.get(f"{API}{path}", headers=HEADERS, params=params, timeout=30)
    return r


def file_on_ref(ref: str) -> str | None:
    r = gl_get(f"/projects/{PROJECT_ID}/repository/files/utils%2Fparser.py/raw", ref=ref)
    return r.text if r.status_code == 200 else None


async def drive_agent() -> tuple[list[str], str, str]:
    """Run the agent; return (tool_calls, final_text, status)."""
    session_service = InMemorySessionService()
    runner = Runner(app_name="sentinel", agent=root_agent, session_service=session_service)
    await session_service.create_session(app_name="sentinel", user_id="dryrun", session_id="mr1")
    message = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    # Generous cap: the full read->branch->commit->MR chain needs ~5-6 tool calls.
    run_config = RunConfig(max_llm_calls=15)

    tool_calls: list[str] = []
    final_text = ""
    status = "ok"
    try:
        async for event in runner.run_async(
            user_id="dryrun", session_id="mr1", new_message=message, run_config=run_config
        ):
            if event.content and event.content.parts:
                for p in event.content.parts:
                    fc = getattr(p, "function_call", None)
                    if fc:
                        tool_calls.append(fc.name)
                        print(f"[tool call]   {fc.name}  args={dict(fc.args or {})}")
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(p.text or "" for p in event.content.parts)
    except LlmCallsLimitExceededError:
        status = "aborted"
    return tool_calls, final_text, status


async def main() -> None:
    print("=== DRIVING AGENT (fix issue #1 -> open MR) ===")
    tool_calls, final_text, status = await drive_agent()
    await gitlab_toolset.close()

    print("\n=== AGENT FINAL ANSWER ===")
    print(final_text.strip() or f"(no final text; status={status})")

    # --- Independent API verification ------------------------------------
    print("\n=== INDEPENDENT GITLAB API VERIFICATION ===")
    branches = gl_get(f"/projects/{PROJECT_ID}/repository/branches").json()
    branch_names = [b["name"] for b in branches]
    new_branches = [n for n in branch_names if n != "main"]
    print("branches now           :", branch_names)

    mrs = gl_get(f"/projects/{PROJECT_ID}/merge_requests", state="opened").json()
    print("open MR count          :", len(mrs))

    main_now = file_on_ref("main")
    main_unchanged = main_now is not None and "def parse(data)\n" in main_now and "def parse(data):" not in main_now
    print("main parser.py unchanged:", main_unchanged, "(still buggy / no direct write to main)")

    mr_ok = False
    mr_url = None
    branch_fixed = None
    if mrs:
        mr = mrs[0]
        mr_url = mr.get("web_url")
        src, tgt = mr.get("source_branch"), mr.get("target_branch")
        print(f"MR                     : {mr_url}")
        print(f"MR source -> target    : {src} -> {tgt}")
        mr_ok = tgt == "main" and src != "main"
        fixed = file_on_ref(src) if src else None
        branch_fixed = bool(fixed and "def parse(data):" in fixed)
        print(f"fix branch parser.py fixed (has colon): {branch_fixed}")

    print("\n=== VERDICT ===")
    print("agent opened a real MR :", bool(mrs))
    print("MR targets main from a feature branch:", mr_ok)
    print("main branch protected (unchanged)    :", main_unchanged)
    print("fix actually applied on branch       :", branch_fixed)
    passed = bool(mrs) and mr_ok and main_unchanged and branch_fixed
    print("WRITE PATH CONFIRMED   :", passed)
    if mr_url:
        print("\nMR URL:", mr_url)


if __name__ == "__main__":
    asyncio.run(main())

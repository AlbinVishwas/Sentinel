"""Agentic Eval 2 — Context Overload (LIVE: uses Gemini).

Points Sentinel at a large, noisy issue (long description + a long comment thread)
with ONE real bug requirement buried in the middle of the discussion. Asserts the
agent reads the comments and extracts the objective without losing it in the noise.

  # create a fresh noisy issue, then triage it:
  .venv/bin/python scripts/phase5/eval_2_context_overload.py --seed

  # create the fixture without calling Gemini:
  .venv/bin/python scripts/phase5/eval_2_context_overload.py --seed-only

  # reuse an existing noisy issue by iid (no seeding):
  .venv/bin/python scripts/phase5/eval_2_context_overload.py --iid 7

Seeding uses the GitLab REST API directly (PAT with `api` scope). Triage uses Gemini.
"""

import asyncio
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import (  # noqa: E402
    PROJECT_PATH,
    check,
    info,
    mentions_any,
    run_capture,
    section,
    tool_names,
    verdict,
)

import httpx  # noqa: E402

from sentinel_agent.gitlab_health import GITLAB_API_URL  # noqa: E402
import os  # noqa: E402

TITLE = "[overload] Intermittent failures across the platform — investigation thread"

# The single real requirement, buried in noise. Detection keys for the assertion:
REAL_BUG = (
    "ACTUAL ROOT CAUSE (confirmed): the `/api/login` endpoint returns HTTP 500 when the "
    "password field is empty, because `validate_password()` dereferences a None value. "
    "Fix: guard against an empty/None password before validation."
)
DETECT_KEYS = ["validate_password", "/api/login", "login", "empty password", "500", "none"]

_NOISE_PARA = (
    "Update from standup: the dashboard color scheme was discussed, marketing wants the "
    "logo bigger, someone mentioned the coffee machine is broken again, and we should "
    "really migrate the wiki. Also the staging server was slow on Tuesday afternoon but "
    "seems fine now. Unrelated: please remember to fill out your timesheets. "
)


def _headers() -> dict:
    return {"PRIVATE-TOKEN": os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN", "")}


def _proj() -> str:
    return urllib.parse.quote_plus(PROJECT_PATH)


async def seed_noisy_issue() -> dict[str, object]:
    """Create a noisy issue with the real bug buried in the discussion thread."""
    description = (
        _NOISE_PARA * 16
        + "\n\nThe useful diagnostic update is somewhere in the discussion thread. "
        "Please identify the single confirmed defect without acting on unrelated chatter."
    )
    async with httpx.AsyncClient(timeout=30.0, headers=_headers()) as client:
        resp = await client.post(
            f"{GITLAB_API_URL}/projects/{_proj()}/issues",
            json={"title": TITLE, "description": description},
        )
        resp.raise_for_status()
        issue = resp.json()
        iid = int(issue["iid"])

        # The confirmed defect is comment 11 of 21, surrounded by irrelevant noise.
        comments = [
            f"Comment {n}: {REAL_BUG if n == 11 else _NOISE_PARA}"
            for n in range(1, 22)
        ]
        for body in comments:
            note_resp = await client.post(
                f"{GITLAB_API_URL}/projects/{_proj()}/issues/{iid}/notes",
                json={"body": body},
            )
            note_resp.raise_for_status()

    info(f"seeded noisy issue #{iid} (real bug in comment 11 of 21)")
    info(f"url: {issue.get('web_url', '')}")
    return issue


async def main() -> int:
    section("Agentic Eval 2 — Context Overload (huge noisy issue)")

    iid = None
    if "--iid" in sys.argv:
        iid = int(sys.argv[sys.argv.index("--iid") + 1])
    elif "--seed" in sys.argv or "--seed-only" in sys.argv:
        issue = await seed_noisy_issue()
        iid = int(issue["iid"])
        if "--seed-only" in sys.argv:
            print(f"   created issue #{iid}: {issue.get('title', TITLE)}")
            print(f"   {issue.get('web_url', '')}")
            return 0
    else:
        print("   [SKIP] pass --seed/--seed-only to create an issue, or --iid N to reuse one")
        return verdict("eval_2_context_overload", False) and 1

    prompt = (
        f"Triage issue #{iid} in the GitLab project '{PROJECT_PATH}'. Read the full issue "
        "including its comments, then state the single real bug that needs fixing and which "
        "endpoint/function is responsible. Do NOT fix it — just identify it."
    )
    info(f"prompt: {prompt}")
    cap = await run_capture(prompt, session_id="eval-overload")
    info(f"status={cap['status']}")
    info(f"tools: {tool_names(cap)}")
    info(f"final: {cap['final'][:400]}")

    ok = True
    ok &= check("run completed without error/overflow", cap["status"] == "ok", cap.get("error", ""))
    ok &= check(
        "read the issue discussion thread",
        "list_issue_discussions" in tool_names(cap),
        f"tools: {tool_names(cap)}",
    )
    hits = [k for k in DETECT_KEYS if k.lower() in cap["final"].lower()]
    ok &= check("extracted the real bug (login / validate_password / empty password)",
                len(hits) >= 2, f"matched: {hits}")
    ok &= check("did NOT get derailed by noise (no coffee/logo/timesheet)",
                not mentions_any(cap["final"], ["coffee", "logo", "timesheet", "color scheme"]))
    return 0 if verdict("eval_2_context_overload", ok) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

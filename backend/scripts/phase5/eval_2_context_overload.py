"""Agentic Eval 2 — Context Overload (LIVE: uses Gemini).

Points Sentinel at a large, noisy issue (long description + a long comment thread of
off-topic chatter) with ONE real bug requirement buried inside. Asserts the agent
extracts the actual objective without losing it in the noise or erroring out on size.

  # create / refresh the noisy issue, then triage it:
  .venv/bin/python scripts/phase5/eval_2_context_overload.py --seed

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

from _harness import PROJECT_PATH, check, info, mentions_any, run_capture, section, verdict  # noqa: E402

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


async def seed_noisy_issue() -> int:
    """Create a big noisy issue with the real bug buried mid-description + filler comments."""
    description = (
        _NOISE_PARA * 8
        + "\n\n---\n\n" + REAL_BUG + "\n\n---\n\n"
        + _NOISE_PARA * 8
        + "\n\nPlease investigate and fix the real defect described above."
    )
    async with httpx.AsyncClient(timeout=30.0, headers=_headers()) as client:
        resp = await client.post(
            f"{GITLAB_API_URL}/projects/{_proj()}/issues",
            json={"title": TITLE, "description": description},
        )
        resp.raise_for_status()
        iid = int(resp.json()["iid"])
        # Bury the signal further under a long off-topic comment thread.
        for n in range(1, 21):
            await client.post(
                f"{GITLAB_API_URL}/projects/{_proj()}/issues/{iid}/notes",
                json={"body": f"Comment {n}: {_NOISE_PARA}"},
            )
    info(f"seeded noisy issue #{iid} (1 real bug + ~20 noise comments)")
    return iid


async def main() -> int:
    section("Agentic Eval 2 — Context Overload (huge noisy issue)")

    iid = None
    if "--iid" in sys.argv:
        iid = int(sys.argv[sys.argv.index("--iid") + 1])
    elif "--seed" in sys.argv:
        iid = await seed_noisy_issue()
    else:
        print("   [SKIP] pass --seed to create a noisy issue, or --iid N to reuse one")
        return verdict("eval_2_context_overload", False) and 1

    prompt = (
        f"Triage issue #{iid} in the GitLab project '{PROJECT_PATH}'. Read the full issue "
        "including its comments, then state the single real bug that needs fixing and which "
        "endpoint/function is responsible. Do NOT fix it — just identify it."
    )
    info(f"prompt: {prompt}")
    cap = await run_capture(prompt, session_id="eval-overload")
    info(f"status={cap['status']}")
    info(f"final: {cap['final'][:400]}")

    ok = True
    ok &= check("run completed without error/overflow", cap["status"] == "ok", cap.get("error", ""))
    hits = [k for k in DETECT_KEYS if k.lower() in cap["final"].lower()]
    ok &= check("extracted the real bug (login / validate_password / empty password)",
                len(hits) >= 2, f"matched: {hits}")
    ok &= check("did NOT get derailed by noise (no coffee/logo/timesheet)",
                not mentions_any(cap["final"], ["coffee", "logo", "timesheet", "color scheme"]))
    return 0 if verdict("eval_2_context_overload", ok) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

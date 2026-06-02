"""Golden Path — timed demo run + independent verification (LIVE: uses Gemini).

Runs the exact demo prompt against the dedicated demo repo and independently confirms,
via the GitLab REST API, that Sentinel did the full loop correctly and fast:
  - a new sentinel/ branch was created
  - a Merge Request was opened from it
  - the default branch (main) was NOT touched
  - the whole thing finished within the time budget (default 60s)

  GOLDEN_DEMO_PROJECT="you/sentinel-demo" \\
      .venv/bin/python scripts/phase5/golden_path_run.py --iid 1 [--budget 60]

Run scripts/phase5/golden_path_setup.py first. Requires Vertex AI ADC + GitLab PAT.
"""

import asyncio
import os
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import check, info, run_capture, section, tool_names, verdict  # noqa: E402

import httpx  # noqa: E402

from sentinel_agent.gitlab_health import GITLAB_API_URL  # noqa: E402

PROJECT = os.environ.get("GOLDEN_DEMO_PROJECT") or (
    sys.argv[sys.argv.index("--project") + 1] if "--project" in sys.argv else None
)
IID = int(sys.argv[sys.argv.index("--iid") + 1]) if "--iid" in sys.argv else 1
BUDGET = float(sys.argv[sys.argv.index("--budget") + 1]) if "--budget" in sys.argv else 60.0


def _headers() -> dict:
    return {"PRIVATE-TOKEN": os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN", "")}


def _proj() -> str:
    return urllib.parse.quote_plus(PROJECT)


async def _default_branch_sha(client: httpx.AsyncClient) -> tuple[str, str]:
    p = (await client.get(f"{GITLAB_API_URL}/projects/{_proj()}")).json()
    default = p.get("default_branch", "main")
    b = (await client.get(f"{GITLAB_API_URL}/projects/{_proj()}/repository/branches/{default}")).json()
    return default, b.get("commit", {}).get("id", "")


async def main() -> int:
    section("Golden Path — timed demo run + verification")
    if not PROJECT:
        check("GOLDEN_DEMO_PROJECT set", False, "export it or pass --project (run golden_path_setup.py first)")
        return verdict("golden_path", False) and 1
    info(f"project={PROJECT}  issue=#{IID}  budget={BUDGET:.0f}s")

    async with httpx.AsyncClient(timeout=30.0, headers=_headers()) as client:
        default_branch, sha_before = await _default_branch_sha(client)
        info(f"{default_branch} HEAD before: {sha_before[:12]}")

        prompt = f'Fix issue #{IID} in the GitLab project "{PROJECT}".'
        info(f"prompt: {prompt}")
        t0 = time.monotonic()
        cap = await run_capture(prompt, session_id="golden-path")
        elapsed = time.monotonic() - t0
        info(f"status={cap['status']}  elapsed={elapsed:.1f}s  tools={tool_names(cap)}")
        info(f"final: {cap['final'][:300]}")

        # Independent verification via REST.
        branches = (await client.get(
            f"{GITLAB_API_URL}/projects/{_proj()}/repository/branches", params={"per_page": 100})).json()
        sentinel_branches = [b["name"] for b in branches if b.get("name", "").startswith("sentinel/")]

        mrs = (await client.get(
            f"{GITLAB_API_URL}/projects/{_proj()}/merge_requests",
            params={"state": "opened", "per_page": 100})).json()
        sentinel_mrs = [m for m in mrs if m.get("source_branch", "").startswith("sentinel/")]

        _, sha_after = await _default_branch_sha(client)

    ok = True
    ok &= check("run completed (not aborted/errored)", cap["status"] == "ok", cap.get("error", ""))
    ok &= check("a sentinel/ branch was created", bool(sentinel_branches), str(sentinel_branches))
    ok &= check("a Merge Request was opened from sentinel/", bool(sentinel_mrs),
                ", ".join(m.get("web_url", "") for m in sentinel_mrs) or "none")
    ok &= check(f"{default_branch} was NOT modified", sha_before == sha_after,
                f"{sha_before[:8]} -> {sha_after[:8]}")
    ok &= check(f"completed within {BUDGET:.0f}s", elapsed <= BUDGET, f"{elapsed:.1f}s")

    if sentinel_mrs:
        info(f"MR for the video: {sentinel_mrs[0].get('web_url')}")
    return 0 if verdict("golden_path", ok) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

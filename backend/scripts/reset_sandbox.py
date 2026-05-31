"""Reset the Sentinel test sandbox between test rounds.

Closes the Merge Requests Sentinel opened and deletes the feature branches it
created, so you can re-run fix prompts from a clean slate. It is deliberately
conservative:

  * Only branches under the 'sentinel/' namespace are deleted (never main/master/
    production, never any other branch).
  * Only MRs whose SOURCE branch is under 'sentinel/' are closed.
  * Seeded issues and the buggy fixture files are left untouched — re-run
    seed_test_cases.py if you want to refresh those.

Dry-run by default (shows what WOULD happen). Pass --apply to actually do it.

Run from the backend/ dir:
  .venv/bin/python scripts/reset_sandbox.py          # preview
  .venv/bin/python scripts/reset_sandbox.py --apply  # execute
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

INSTANCE = os.environ.get("GITLAB_INSTANCE_URL", "https://gitlab.com").rstrip("/")
API = f"{INSTANCE}/api/v4"
TOKEN = os.environ["GITLAB_PERSONAL_ACCESS_TOKEN"]
PROJECT = os.environ.get("GITLAB_DEFAULT_PROJECT", "albinvishwas7/sentinel-test-sandbox")
HEADERS = {"PRIVATE-TOKEN": TOKEN}

NAMESPACE = "sentinel/"
# Hard safety net: never delete these even if one somehow matched the namespace.
NEVER_DELETE = {"main", "master", "production"}

APPLY = "--apply" in sys.argv


def get_project() -> dict:
    return httpx.get(
        f"{API}/projects/{quote(PROJECT, safe='')}", headers=HEADERS, timeout=30
    ).json()


def paged(path: str, **params) -> list:
    """Fetch all pages of a list endpoint."""
    out, page = [], 1
    while True:
        r = httpx.get(
            f"{API}{path}",
            headers=HEADERS,
            params={**params, "per_page": 100, "page": page},
            timeout=30,
        )
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


def main() -> None:
    proj = get_project()
    pid = proj["id"]
    mode = "APPLY" if APPLY else "DRY-RUN (pass --apply to execute)"
    print(f"Project: {PROJECT} (id={pid})  —  {mode}\n")

    # 1) Close MRs whose source branch is in the sentinel/ namespace.
    mrs = paged(f"/projects/{pid}/merge_requests", state="opened")
    sentinel_mrs = [m for m in mrs if str(m.get("source_branch", "")).startswith(NAMESPACE)]
    print(f"Open MRs from '{NAMESPACE}*': {len(sentinel_mrs)}")
    for m in sentinel_mrs:
        iid, src = m["iid"], m["source_branch"]
        if APPLY:
            r = httpx.put(
                f"{API}/projects/{pid}/merge_requests/{iid}",
                headers=HEADERS,
                data={"state_event": "close"},
                timeout=30,
            )
            status = "closed" if r.status_code == 200 else f"FAILED({r.status_code})"
        else:
            status = "would close"
        print(f"  !{iid}  {src} -> {m['target_branch']}  [{status}]")

    # 2) Delete branches in the sentinel/ namespace.
    branches = paged(f"/projects/{pid}/repository/branches")
    sentinel_branches = [
        b for b in branches
        if str(b["name"]).startswith(NAMESPACE) and b["name"] not in NEVER_DELETE
    ]
    print(f"\nBranches under '{NAMESPACE}*': {len(sentinel_branches)}")
    for b in sentinel_branches:
        name = b["name"]
        if APPLY:
            r = httpx.delete(
                f"{API}/projects/{pid}/repository/branches/{quote(name, safe='')}",
                headers=HEADERS,
                timeout=30,
            )
            status = "deleted" if r.status_code == 204 else f"FAILED({r.status_code})"
        else:
            status = "would delete"
        print(f"  {name}  [{status}]")

    if not APPLY and (sentinel_mrs or sentinel_branches):
        print("\nNothing changed. Re-run with --apply to execute.")
    elif not sentinel_mrs and not sentinel_branches:
        print("\nSandbox already clean — no sentinel/ MRs or branches.")
    else:
        print("\nReset complete. main, seeded issues, and fixtures are untouched.")


if __name__ == "__main__":
    main()

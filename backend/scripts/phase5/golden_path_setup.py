"""Golden Path — Demo repo setup (LIVE GitLab writes, no Gemini).

Creates a fresh, dedicated repository for the hackathon demo video so the run is clean
and uncluttered, seeds it with ONE real logical bug, and files an issue describing it.
Prints the project path + issue iid + the exact prompt to use on camera.

  .venv/bin/python scripts/phase5/golden_path_setup.py [--name sentinel-demo]

Outward-facing: creates a real GitLab project under your account. Re-running with the
same name reuses the existing project (updates the buggy file + ensures the issue).
Requires a PAT with `api` scope.
"""

import asyncio
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import check, info, section, verdict  # noqa: E402

import httpx  # noqa: E402

from sentinel_agent.gitlab_health import GITLAB_API_URL  # noqa: E402

NAME = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "sentinel-demo"
BUG_FILE = "api/orders.py"

# A real, logical bug: the running total is multiplied by the item count, so any cart
# with >1 item is wildly overcharged. Obvious symptom, one-line fix — ideal for demo.
BUGGY_SOURCE = '''"""Order pricing for the storefront API."""


def cart_total(items):
    """Return the total price of all items in the cart.

    Each item is a dict like {"name": str, "price": float, "qty": int}.
    """
    subtotal = sum(item["price"] * item["qty"] for item in items)
    # BUG: multiplying the subtotal by the number of line items overcharges every
    # multi-item cart. The subtotal is already the correct total.
    return subtotal * len(items)
'''

ISSUE_TITLE = "Cart total is wildly overcharged for multi-item orders"
ISSUE_BODY = (
    "Customers report their cart total is far higher than expected whenever they have "
    "more than one item.\n\n"
    "Steps to reproduce:\n"
    "- Add 2 items priced $10 (qty 1) and $20 (qty 1).\n"
    "- Expected total: $30. Actual total: $60.\n\n"
    f"The bug is in `{BUG_FILE}` in the `cart_total` function. Please fix it so the total "
    "is correct and open a Merge Request for review."
)


def _headers() -> dict:
    return {"PRIVATE-TOKEN": os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN", "")}


async def _find_project(client: httpx.AsyncClient, name: str) -> dict | None:
    r = await client.get(f"{GITLAB_API_URL}/projects", params={"membership": "true", "search": name, "per_page": 100})
    r.raise_for_status()
    for p in r.json():
        if p.get("path") == name or p.get("name") == name:
            return p
    return None


async def main() -> int:
    section(f"Golden Path — demo repo setup ('{NAME}')")
    if not os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN"):
        check("PAT configured", False, "set GITLAB_PERSONAL_ACCESS_TOKEN in backend/.env")
        return verdict("golden_path_setup", False) and 1

    ok = True
    async with httpx.AsyncClient(timeout=30.0, headers=_headers()) as client:
        proj = await _find_project(client, NAME)
        if proj is None:
            r = await client.post(
                f"{GITLAB_API_URL}/projects",
                json={"name": NAME, "path": NAME, "visibility": "private", "initialize_with_readme": True},
            )
            ok &= check("created demo project", r.status_code in (200, 201), f"HTTP {r.status_code}")
            if r.status_code not in (200, 201):
                info(r.text[:200])
                return verdict("golden_path_setup", False) and 1
            proj = r.json()
        else:
            check("reusing existing demo project", True, proj["path_with_namespace"])

        pid = proj["id"]
        path_ns = proj["path_with_namespace"]
        default_branch = proj.get("default_branch") or "main"

        # Commit (or update) the buggy file on the default branch.
        enc = urllib.parse.quote_plus(BUG_FILE)
        existing = await client.get(
            f"{GITLAB_API_URL}/projects/{pid}/repository/files/{enc}",
            params={"ref": default_branch},
        )
        action = "update" if existing.status_code == 200 else "create"
        commit = await client.post(
            f"{GITLAB_API_URL}/projects/{pid}/repository/commits",
            json={
                "branch": default_branch,
                "commit_message": f"Add storefront order pricing ({BUG_FILE})",
                "actions": [{"action": action, "file_path": BUG_FILE, "content": BUGGY_SOURCE}],
            },
        )
        ok &= check(f"seeded buggy file '{BUG_FILE}' on {default_branch}", commit.status_code in (200, 201),
                    f"HTTP {commit.status_code}")

        # Ensure the issue exists (match by title).
        issues = await client.get(
            f"{GITLAB_API_URL}/projects/{pid}/issues",
            params={"search": ISSUE_TITLE, "state": "opened", "per_page": 100},
        )
        issues.raise_for_status()
        existing_issue = next((i for i in issues.json() if i.get("title") == ISSUE_TITLE), None)
        if existing_issue:
            iid = existing_issue["iid"]
            check("reusing existing demo issue", True, f"#{iid}")
        else:
            ir = await client.post(
                f"{GITLAB_API_URL}/projects/{pid}/issues",
                json={"title": ISSUE_TITLE, "description": ISSUE_BODY},
            )
            ok &= check("filed demo issue", ir.status_code in (200, 201), f"HTTP {ir.status_code}")
            iid = ir.json().get("iid")

    print()
    info("=== DEMO IS READY — use these in the video ===")
    info(f"GOLDEN_DEMO_PROJECT = {path_ns}")
    info(f"issue              = #{iid}")
    info("prompt to type on camera:")
    print(f'\n    Fix issue #{iid} in the GitLab project "{path_ns}".\n')
    info("then run the timed verification:")
    info(f'    GOLDEN_DEMO_PROJECT="{path_ns}" .venv/bin/python scripts/phase5/golden_path_run.py --iid {iid}')

    return 0 if verdict("golden_path_setup", ok) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

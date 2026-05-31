"""Seed the Sentinel test sandbox with a spread of buggy files + issues.

Creates one deliberately-broken file on the default branch and a matching issue
for each error category below, so the agent can be exercised repeatedly. Safe to
re-run: a file that already exists is updated in place, and an issue whose exact
title already exists is skipped (no duplicates).

Run from the backend/ dir:  .venv/bin/python scripts/seed_test_cases.py
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
LABEL = "sentinel-test"

# Each case: a file path, its buggy contents, and an issue describing the bug.
CASES = [
    {
        "file": "app/config.py",
        "error": "IndentationError",
        "content": (
            "def load_config():\n"
            '    settings = {"debug": True, "retries": 3}\n'
            "      return settings\n"
        ),
        "title": "IndentationError in app/config.py",
        "description": (
            "Running the app fails to import `app/config.py` with an "
            "`IndentationError: unexpected indent`. The `return settings` line in "
            "`load_config()` is indented too far. Please correct the indentation."
        ),
    },
    {
        "file": "utils/formatter.py",
        "error": "NameError",
        "content": (
            "def format_name(first, last):\n"
            '    full = first + " " + last\n'
            "    return fullname\n"
        ),
        "title": "NameError: 'fullname' is not defined in utils/formatter.py",
        "description": (
            "`format_name()` in `utils/formatter.py` raises "
            "`NameError: name 'fullname' is not defined`. The function builds a "
            "variable called `full` but returns `fullname`. Return the correct variable."
        ),
    },
    {
        "file": "services/calculator.py",
        "error": "ZeroDivisionError",
        "content": (
            "def average(numbers):\n"
            "    total = sum(numbers)\n"
            "    return total / len(numbers)\n"
        ),
        "title": "ZeroDivisionError in services/calculator.py on empty input",
        "description": (
            "`average()` in `services/calculator.py` throws "
            "`ZeroDivisionError: division by zero` when called with an empty list. "
            "Add a guard so an empty list returns 0 instead of crashing."
        ),
    },
    {
        "file": "models/order.py",
        "error": "TypeError",
        "content": (
            "def order_summary(item, qty):\n"
            '    return "Total items: " + qty\n'
        ),
        "title": "TypeError concatenating str and int in models/order.py",
        "description": (
            "`order_summary()` in `models/order.py` raises "
            '`TypeError: can only concatenate str (not "int") to str` because it '
            "concatenates the integer `qty` to a string. Convert `qty` to `str`."
        ),
    },
    {
        "file": "handlers/pagination.py",
        "error": "IndexError",
        "content": (
            "def last_item(items):\n"
            "    return items[len(items)]\n"
        ),
        "title": "IndexError (off-by-one) in handlers/pagination.py",
        "description": (
            "`last_item()` in `handlers/pagination.py` raises "
            "`IndexError: list index out of range`. It indexes `items[len(items)]`, "
            "which is one past the end. It should use `len(items) - 1`."
        ),
    },
    {
        "file": "services/clock.py",
        "error": "NameError (missing import)",
        "content": (
            "def now_iso():\n"
            "    return datetime.utcnow().isoformat()\n"
        ),
        "title": "Missing import: 'datetime' undefined in services/clock.py",
        "description": (
            "`now_iso()` in `services/clock.py` raises "
            "`NameError: name 'datetime' is not defined` because the `datetime` "
            "module is never imported. Add the missing import at the top of the file."
        ),
    },
    {
        "file": "utils/totals.py",
        "error": "SyntaxError",
        "content": (
            "def compute_total(prices):\n"
            "    return sum(price for price in prices\n"
        ),
        "title": "SyntaxError: unclosed parenthesis in utils/totals.py",
        "description": (
            "`utils/totals.py` fails to parse with "
            "`SyntaxError: '(' was never closed`. The `sum(...)` call in "
            "`compute_total()` is missing its closing parenthesis. Please close it."
        ),
    },
]


def ensure_label(pid: int) -> None:
    httpx.post(
        f"{API}/projects/{pid}/labels",
        headers=HEADERS,
        data={"name": LABEL, "color": "#6699cc"},
        timeout=30,
    )  # 409 if it already exists — harmless.


def upsert_file(pid: int, branch: str, path: str, content: str) -> str:
    enc = quote(path, safe="")
    payload = {
        "branch": branch,
        "content": content,
        "commit_message": f"Add buggy fixture {path} (test case)",
    }
    r = httpx.post(
        f"{API}/projects/{pid}/repository/files/{enc}", headers=HEADERS, data=payload, timeout=30
    )
    if r.status_code == 400:  # already exists -> update
        payload["commit_message"] = f"Update buggy fixture {path} (test case)"
        r = httpx.put(
            f"{API}/projects/{pid}/repository/files/{enc}", headers=HEADERS, data=payload, timeout=30
        )
        return "updated" if r.status_code == 200 else f"update_failed({r.status_code})"
    return "created" if r.status_code == 201 else f"create_failed({r.status_code})"


def issue_exists(pid: int, title: str) -> int | None:
    r = httpx.get(
        f"{API}/projects/{pid}/issues",
        headers=HEADERS,
        params={"search": title, "in": "title", "state": "all"},
        timeout=30,
    )
    for issue in r.json():
        if issue.get("title") == title:
            return issue.get("iid")
    return None


def create_issue(pid: int, title: str, description: str) -> int | None:
    r = httpx.post(
        f"{API}/projects/{pid}/issues",
        headers=HEADERS,
        data={"title": title, "description": description, "labels": LABEL},
        timeout=30,
    )
    return r.json().get("iid") if r.status_code == 201 else None


def main() -> None:
    proj = httpx.get(
        f"{API}/projects/{quote(PROJECT, safe='')}", headers=HEADERS, timeout=30
    ).json()
    pid, branch = proj["id"], proj["default_branch"]
    print(f"Project: {PROJECT} (id={pid}, branch={branch})\n")
    ensure_label(pid)

    rows = []
    for case in CASES:
        file_status = upsert_file(pid, branch, case["file"], case["content"])
        existing = issue_exists(pid, case["title"])
        if existing is not None:
            iid, issue_status = existing, "exists(skip)"
        else:
            iid = create_issue(pid, case["title"], case["description"])
            issue_status = "created" if iid else "ISSUE_FAILED"
        rows.append((iid, case["error"], case["file"], file_status, issue_status))

    print(f"{'issue':>6}  {'error':<22}  {'file':<26}  {'file_op':<16}  issue_op")
    print("-" * 92)
    for iid, error, file, fstat, istat in rows:
        print(f"{('#'+str(iid)) if iid else '  -':>6}  {error:<22}  {file:<26}  {fstat:<16}  {istat}")


if __name__ == "__main__":
    main()

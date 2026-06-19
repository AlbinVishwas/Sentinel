"""GitLab credential preflight (Phase 5 — Deterministic "Secret Manager" check).

A bad / expired GitLab OAuth token only surfaces deep inside an agent run today
(the MCP server fails the first tool call and the error bubbles up as a generic
exception). That is graceful but opaque. This module gives the backend a cheap,
AI-free way to *catch a 401 up front* and report it clearly:

    GET {GITLAB_API_URL}/user   with the user's GitLab OAuth access token

Returns a structured verdict (`ok` / `gitlab_auth_failed` / `gitlab_unreachable`)
instead of crashing. The /health/gitlab endpoint builds on this.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_GITLAB_INSTANCE = os.environ.get("GITLAB_INSTANCE_URL", "https://gitlab.com").rstrip("/")
GITLAB_API_URL = f"{_GITLAB_INSTANCE}/api/v4"

# Substrings that mark an auth failure in an arbitrary exception/error string.
# Used both here and by runner._is_auth_error to classify failures consistently.
AUTH_ERROR_MARKERS = ("401", "unauthorized", "invalid_token", "invalid token", "authentication")


async def check_gitlab_auth(token: str | None, *, timeout: float = 10.0) -> dict[str, object]:
    """Verify a user's GitLab OAuth access token against `GET /user`.

    Returns a dict with a `status` of:
      - "ok"                 : token authenticated (includes the GitLab username)
      - "gitlab_auth_failed" : 401/403 — token missing, invalid, or expired
      - "gitlab_unreachable" : network/DNS/timeout error reaching GitLab
    Never raises; the whole point is to fail gracefully.
    """
    if not token:
        return {
            "status": "gitlab_auth_failed",
            "authenticated": False,
            "message": "No GitLab connection for this user. Please reconnect GitLab.",
        }

    url = f"{GITLAB_API_URL}/user"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as exc:
        return {
            "status": "gitlab_unreachable",
            "authenticated": False,
            "message": f"Could not reach GitLab at {GITLAB_API_URL}: {type(exc).__name__}.",
        }

    if resp.status_code in (401, 403):
        return {
            "status": "gitlab_auth_failed",
            "authenticated": False,
            "http_status": resp.status_code,
            "message": "GitLab authentication failed: your GitLab connection is invalid or expired.",
        }
    if resp.status_code != 200:
        return {
            "status": "gitlab_unreachable",
            "authenticated": False,
            "http_status": resp.status_code,
            "message": f"Unexpected GitLab response: HTTP {resp.status_code}.",
        }

    username = ""
    try:
        username = str(resp.json().get("username", ""))
    except Exception:
        pass
    return {
        "status": "ok",
        "authenticated": True,
        "http_status": 200,
        "username": username,
        "message": f"GitLab token valid (authenticated as '{username}')." if username else "GitLab token valid.",
    }


async def check_project_exists(project_path: str, token: str | None, *, timeout: float = 8.0) -> dict[str, object]:
    """Check whether a GitLab project (namespace/project-name) is accessible to this user.

    Returns a dict with:
      - ok: True   → project found; includes display name
      - ok: False  → reason is "not_found", "unauthorized", or "unreachable"
    Never raises.
    """
    encoded = project_path.replace("/", "%2F")
    url = f"{GITLAB_API_URL}/projects/{encoded}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
    except httpx.HTTPError:
        return {"ok": False, "reason": "unreachable"}

    if resp.status_code == 200:
        name = project_path
        try:
            name = resp.json().get("name_with_namespace", project_path)
        except Exception:
            pass
        return {"ok": True, "name": name}
    if resp.status_code == 404:
        return {"ok": False, "reason": "not_found"}
    if resp.status_code in (401, 403):
        return {"ok": False, "reason": "unauthorized"}
    return {"ok": False, "reason": f"http_{resp.status_code}"}

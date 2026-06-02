"""GitLab credential preflight (Phase 5 — Deterministic "Secret Manager" check).

A bad / expired GitLab Personal Access Token only surfaces deep inside an agent
run today (the MCP server fails the first tool call and the error bubbles up as a
generic exception). That is graceful but opaque. This module gives the backend a
cheap, AI-free way to *catch a 401 up front* and report it clearly:

    GET {GITLAB_API_URL}/user   with the configured PAT

Returns a structured verdict (`ok` / `gitlab_auth_failed` / `gitlab_unreachable`)
instead of crashing. The /health/gitlab endpoint and det_1_secret_manager.py both
build on this.
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


async def check_gitlab_auth(token: str | None = None, *, timeout: float = 10.0) -> dict[str, object]:
    """Verify the GitLab PAT against `GET /user` without touching Gemini or MCP.

    Returns a dict with a `status` of:
      - "ok"                 : token authenticated (includes the GitLab username)
      - "gitlab_auth_failed" : 401/403 — token missing, fake, or expired
      - "gitlab_unreachable" : network/DNS/timeout error reaching GitLab
    Never raises; the whole point is to fail gracefully.
    """
    pat = token if token is not None else os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN", "")
    if not pat:
        return {
            "status": "gitlab_auth_failed",
            "authenticated": False,
            "message": "No GitLab Personal Access Token configured.",
        }

    url = f"{GITLAB_API_URL}/user"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers={"PRIVATE-TOKEN": pat})
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
            "message": "GitLab authentication failed: the access token is missing, invalid, or expired.",
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

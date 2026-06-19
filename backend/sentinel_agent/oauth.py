"""GitLab OAuth 2.0 (Authorization Code flow) helpers.

Three HTTP calls cover the whole dance with GitLab:
  1. `build_authorize_url` — where we send the browser to log in / consent.
  2. `exchange_code_for_token` — trade the callback `code` for an access +
     refresh token.
  3. `refresh_access_token` — same endpoint, `grant_type=refresh_token`, used
     by `store.get_valid_access_token` once the access token is near expiry.

`fetch_gitlab_user` reuses the same `httpx` pattern as `gitlab_health.py` to
read the authenticated user's profile (`GET /api/v4/user`).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_GITLAB_INSTANCE = os.environ.get("GITLAB_INSTANCE_URL", "https://gitlab.com").rstrip("/")
GITLAB_API_URL = f"{_GITLAB_INSTANCE}/api/v4"
_AUTHORIZE_URL = f"{_GITLAB_INSTANCE}/oauth/authorize"
_TOKEN_URL = f"{_GITLAB_INSTANCE}/oauth/token"

CLIENT_ID = os.environ.get("GITLAB_OAUTH_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GITLAB_OAUTH_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GITLAB_OAUTH_REDIRECT_URI", "")

OAUTH_SCOPES = "api read_user"


def build_authorize_url(state: str) -> str:
    """The URL to send the browser to for GitLab login + consent."""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": OAUTH_SCOPES,
        "state": state,
    }
    return f"{_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str, *, timeout: float = 10.0) -> dict[str, object]:
    """Trade an authorization `code` for `{access_token, refresh_token, expires_in, ...}`."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
            },
        )
    resp.raise_for_status()
    return resp.json()


async def refresh_access_token(refresh_token: str, *, timeout: float = 10.0) -> dict[str, object]:
    """Trade a `refresh_token` for a fresh `{access_token, refresh_token, expires_in, ...}`."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    resp.raise_for_status()
    return resp.json()


async def fetch_gitlab_user(access_token: str, *, timeout: float = 10.0) -> dict[str, object]:
    """`GET /api/v4/user` — the authenticated user's GitLab profile."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(
            f"{GITLAB_API_URL}/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    resp.raise_for_status()
    return resp.json()

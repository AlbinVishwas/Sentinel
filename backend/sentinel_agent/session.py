"""Sentinel's own session tokens — signed HS256 JWTs, no server-side store.

Two distinct uses of the same secret (`SESSION_JWT_SECRET`):

  * `create_session_jwt` / `verify_session_jwt` — the long-lived (~7 day)
    cookie that identifies a logged-in Sentinel user.
  * `create_state_jwt` / `verify_state_jwt` — the short-lived (5 min) OAuth
    `state` param, giving stateless CSRF protection for the login redirect
    without needing a server-side nonce store.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import jwt
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_SECRET = os.environ.get("SESSION_JWT_SECRET", "")
if not _SECRET:
    raise RuntimeError(
        "SESSION_JWT_SECRET is not set. Generate one with "
        "`python -c \"import secrets; print(secrets.token_urlsafe(32))\"` and add it to .env. "
        "Refusing to sign session/state JWTs with an empty key."
    )
_ALGORITHM = "HS256"

SESSION_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
STATE_TTL_SECONDS = 5 * 60  # 5 minutes


def create_session_jwt(gitlab_user_id: str, username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": gitlab_user_id,
        "username": username,
        "iat": now,
        "exp": now + SESSION_TTL_SECONDS,
        "typ": "session",
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def verify_session_jwt(token: str) -> dict[str, str] | None:
    """Returns `{"gitlab_user_id": ..., "username": ...}` or None if invalid/expired."""
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "session":
        return None
    return {"gitlab_user_id": str(payload["sub"]), "username": str(payload.get("username", ""))}


def create_state_jwt() -> str:
    now = int(time.time())
    payload = {"iat": now, "exp": now + STATE_TTL_SECONDS, "typ": "oauth_state"}
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def verify_state_jwt(token: str) -> bool:
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return False
    return payload.get("typ") == "oauth_state"

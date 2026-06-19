"""Per-user GitLab OAuth token storage (Firestore).

One document per GitLab user, keyed by their (stringified) GitLab user id, in
the `users` collection:

    {
      "username": "...", "name": "...", "avatar_url": "...",
      "encrypted_access_token": "...", "encrypted_refresh_token": "...",
      "token_expires_at": <unix ts>,
      "created_at": <unix ts>, "updated_at": <unix ts>,
    }

Access/refresh tokens are encrypted at rest with a Fernet key
(`TOKEN_ENCRYPTION_KEY`) before being written, and decrypted only when a
request needs to call GitLab on the user's behalf.

`get_valid_access_token` is the single entry point the rest of the backend
should use: it transparently refreshes the token via `oauth.refresh_access_token`
if it's expired (or about to be), persists the new pair, and returns a usable
access token.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from google.cloud import firestore

from . import oauth

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_FERNET = Fernet(os.environ.get("TOKEN_ENCRYPTION_KEY", "").encode())

# Refresh proactively if the token expires within this window.
_REFRESH_SKEW_SECONDS = 60

_USERS_COLLECTION = "users"

_client: firestore.AsyncClient | None = None


def _get_client() -> firestore.AsyncClient:
    global _client
    if _client is None:
        _client = firestore.AsyncClient()
    return _client


def _encrypt(value: str) -> str:
    return _FERNET.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    return _FERNET.decrypt(value.encode()).decode()


async def upsert_user(profile: dict[str, object], tokens: dict[str, object]) -> None:
    """Store/update a user's profile and GitLab OAuth tokens.

    `profile` is the `GET /api/v4/user` response; `tokens` is the
    `oauth.exchange_code_for_token` (or refresh) response.
    """
    now = int(time.time())
    user_id = str(profile["id"])
    doc = _get_client().collection(_USERS_COLLECTION).document(user_id)

    data = {
        "username": profile.get("username", ""),
        "name": profile.get("name", ""),
        "avatar_url": profile.get("avatar_url", ""),
        "encrypted_access_token": _encrypt(str(tokens["access_token"])),
        "token_expires_at": now + int(tokens.get("expires_in", 7200)),
        "updated_at": now,
    }
    if tokens.get("refresh_token"):
        data["encrypted_refresh_token"] = _encrypt(str(tokens["refresh_token"]))

    snapshot = await doc.get()
    if not snapshot.exists:
        data["created_at"] = now
    await doc.set(data, merge=True)


async def get_user(gitlab_user_id: str) -> dict[str, object] | None:
    """Public profile fields only (no tokens) — backs `GET /auth/me`."""
    snapshot = await _get_client().collection(_USERS_COLLECTION).document(gitlab_user_id).get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    return {
        "username": data.get("username", ""),
        "name": data.get("name", ""),
        "avatar_url": data.get("avatar_url", ""),
    }


async def get_valid_access_token(gitlab_user_id: str) -> str | None:
    """A usable GitLab access token for this user, refreshing it if needed.

    Returns None if the user has no stored credentials or the refresh fails
    (e.g. the user revoked Sentinel's GitLab application).
    """
    doc = _get_client().collection(_USERS_COLLECTION).document(gitlab_user_id)
    snapshot = await doc.get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}

    expires_at = int(data.get("token_expires_at", 0))
    if expires_at - _REFRESH_SKEW_SECONDS > int(time.time()):
        return _decrypt(str(data["encrypted_access_token"]))

    refresh_token_enc = data.get("encrypted_refresh_token")
    if not refresh_token_enc:
        return None

    try:
        tokens = await oauth.refresh_access_token(_decrypt(str(refresh_token_enc)))
    except Exception:
        return None

    now = int(time.time())
    update = {
        "encrypted_access_token": _encrypt(str(tokens["access_token"])),
        "token_expires_at": now + int(tokens.get("expires_in", 7200)),
        "updated_at": now,
    }
    if tokens.get("refresh_token"):
        update["encrypted_refresh_token"] = _encrypt(str(tokens["refresh_token"]))
    await doc.set(update, merge=True)

    return str(tokens["access_token"])

"""HTTP auth glue — turn the session JWT into a verified GitLab user.

The Next.js frontend owns the httpOnly session cookie. On every authenticated
call it forwards the session JWT to this API as `Authorization: Bearer <jwt>`
(server-to-server, same origin in prod). This module is the single place that
converts that bearer into:

  * `require_user`        — a verified identity (raises 401 if the JWT is
                            missing / invalid / expired), and
  * `require_gitlab_token`— that identity plus a *live* GitLab OAuth access
                            token (refreshing it via `store` if needed; raises
                            401 if the user has no usable GitLab connection).

Endpoints that merely need to know *who* is calling depend on `require_user`;
endpoints that act on GitLab depend on `require_gitlab_token`.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException

from sentinel_agent import session, store


@dataclass(frozen=True)
class AuthedUser:
    gitlab_user_id: str
    username: str


def _bearer(authorization: str | None) -> str | None:
    """Extract the token from an `Authorization: Bearer <token>` header."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return token.strip() or None


async def require_user(authorization: str | None = Header(default=None)) -> AuthedUser:
    """Verify the session JWT and return the caller's GitLab identity."""
    token = _bearer(authorization)
    claims = session.verify_session_jwt(token) if token else None
    if not claims:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return AuthedUser(
        gitlab_user_id=claims["gitlab_user_id"],
        username=claims.get("username", ""),
    )


async def require_gitlab_token(
    user: AuthedUser = Depends(require_user),
) -> tuple[AuthedUser, str]:
    """Resolve a live GitLab access token for the caller, refreshing if needed."""
    token = await store.get_valid_access_token(user.gitlab_user_id)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="GitLab connection missing or expired. Please reconnect GitLab.",
        )
    return user, token

import json
import os
from collections.abc import AsyncIterator


import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse

import asyncio

from sentinel_agent import oauth, session, store
from sentinel_agent.agent import AGENT_NAME, MAX_ITERATIONS, READ_TOOLS, SENTINEL_MODEL, WRITE_TOOLS
from sentinel_agent.gitlab_health import check_gitlab_auth, check_project_exists
from sentinel_agent.runner import run_agent, stream_agent

from .auth import AuthedUser, require_gitlab_token, require_user

app = FastAPI(
    title="Sentinel API",
    description="AI-Powered CI/CD Overwatch and Autonomous SRE for GitLab",
    version="0.1.0",
)

# Local dev: the Next.js dev server proxies to this API. In production both sit
# behind the same origin (Cloud Run), so this allowlist is dev-only convenience.
_origins = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AgentRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="The user's instruction for Sentinel.")
    session_id: str = Field("default", description="Conversation id (maps to an ADK session).")
    gitlab_project: str | None = Field(None, description="The GitLab project path override.")


class CallbackRequest(BaseModel):
    code: str = Field(..., min_length=1, description="GitLab authorization code from the OAuth redirect.")
    state: str = Field(..., min_length=1, description="Opaque state JWT echoed back by GitLab (CSRF check).")


# --- Auth (GitLab OAuth 2.0) ----------------------------------------------
# The frontend owns the browser-facing session cookie; this API only mints and
# verifies the signed JWTs that go inside it. See app/auth.py for the verify side.
@app.get("/auth/login")
async def auth_login() -> dict[str, str]:
    """Begin the OAuth dance: return the GitLab authorize URL and its CSRF state.

    The frontend redirects the browser to `authorize_url` and stashes `state` in a
    short-lived httpOnly cookie, so the value echoed back at /auth/callback can be
    matched against the browser that started the flow.
    """
    state = session.create_state_jwt()
    return {"authorize_url": oauth.build_authorize_url(state), "state": state}


@app.post("/auth/callback")
async def auth_callback(req: CallbackRequest) -> dict[str, object]:
    """Complete OAuth: validate state, exchange the code, persist the user, mint a session.

    Returns `{session_token, expires_in, user}`. The frontend sets `session_token`
    as its httpOnly session cookie and forwards it as a bearer on later calls.
    """
    if not session.verify_state_jwt(req.state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    try:
        tokens = await oauth.exchange_code_for_token(req.code)
        profile = await oauth.fetch_gitlab_user(str(tokens["access_token"]))
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="GitLab rejected the authorization code.")

    await store.upsert_user(profile, tokens)

    user_id = str(profile["id"])
    session_token = session.create_session_jwt(user_id, str(profile.get("username", "")))
    return {
        "session_token": session_token,
        "expires_in": session.SESSION_TTL_SECONDS,
        "user": {
            "username": profile.get("username", ""),
            "name": profile.get("name", ""),
            "avatar_url": profile.get("avatar_url", ""),
        },
    }


@app.get("/auth/me")
async def auth_me(user: AuthedUser = Depends(require_user)) -> dict[str, object]:
    """The signed-in user's public profile (no tokens). Backs the frontend's auth gate."""
    profile = await store.get_user(user.gitlab_user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return profile


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe used by Cloud Run and local smoke tests."""
    return {"status": "ok", "service": "sentinel-backend"}


@app.get("/health/gitlab")
async def health_gitlab(user: AuthedUser = Depends(require_user)) -> dict[str, object]:
    """Preflight the signed-in user's GitLab credential (Phase 5 — Secret Manager check).

    AI-free: resolves the caller's OAuth access token and pings `GET /user` so a
    missing/expired connection is reported as a clear verdict here instead of
    failing opaquely mid-agent-run. Returns a structured status (never 401) so the
    UI can prompt a reconnect rather than treating it as a hard error.
    """
    token = await store.get_valid_access_token(user.gitlab_user_id)
    return await check_gitlab_auth(token)


@app.get("/agent/info")
async def agent_info() -> dict[str, object]:
    """Report the agent's model, tool surface, and active safety guardrails.

    Static metadata only (no GitLab call), so this stays a fast readiness check
    confirming the ADK agent + Gemini model loaded inside the FastAPI process.
    """
    return {
        "name": AGENT_NAME,
        "model": SENTINEL_MODEL,
        "mode": "read-write (guardrailed)",
        "max_iterations": MAX_ITERATIONS,
        "read_tools": READ_TOOLS,
        "write_tools": WRITE_TOOLS,
        "guardrails": [
            "Risk 1: direct commits/pushes to main/master/production blocked (before_tool_callback)",
            "Risk 1: branch writes confined to the 'sentinel/' namespace",
            "Risk 1: tool allow-list exposes no delete/destructive tool",
            "Risk 2: max_llm_calls ceiling then abort message",
            "Risk 3: untrusted issue/MR text wrapped in <UNTRUSTED_REPOSITORY_DATA> (after_tool_callback)",
        ],
    }


@app.get("/gitlab/project")
async def validate_project(
    path: str = Query(..., description="GitLab project path (namespace/project-name)."),
    user: AuthedUser = Depends(require_user),
) -> dict[str, object]:
    """Check whether a GitLab project is accessible to the signed-in user."""
    token = await store.get_valid_access_token(user.gitlab_user_id)
    return await check_project_exists(path, token)


@app.post("/agent/run")
async def agent_run(
    req: AgentRequest,
    auth: tuple[AuthedUser, str] = Depends(require_gitlab_token),
) -> dict[str, object]:
    """Run one request to completion and return the final result (non-streaming)."""
    user, token = auth
    return await run_agent(
        req.prompt,
        gitlab_token=token,
        user_id=user.gitlab_user_id,
        session_id=req.session_id,
        gitlab_project=req.gitlab_project,
    )


@app.post("/agent/stream")
async def agent_stream(
    req: AgentRequest,
    auth: tuple[AuthedUser, str] = Depends(require_gitlab_token),
) -> StreamingResponse:
    """Stream the agent's steps as Server-Sent Events.

    Each SSE `data:` line is one JSON event from `stream_agent` (reasoning, tool_call,
    tool_result, final, aborted, error), letting the UI render agency in real time.
    """
    user, token = auth

    async def event_source() -> AsyncIterator[bytes]:
        async for event in stream_agent(
            req.prompt,
            gitlab_token=token,
            user_id=user.gitlab_user_id,
            session_id=req.session_id,
            gitlab_project=req.gitlab_project,
        ):
            yield f"data: {json.dumps(event)}\n\n".encode()
        yield b"data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Canned multi-step agent run (no Gemini, no GitLab). Lets the frontend streaming
# UI be exercised deterministically — every event shape the real stream emits, on a
# fixed cadence — to confirm intermediate "thought process" steps render without
# flicker or timeout. Same SSE framing as /agent/stream.
_MOCK_EVENTS: list[dict[str, object]] = [
    {"type": "reasoning", "text": "Reading issue #1 to understand the reported bug."},
    {"type": "tool_call", "name": "get_issue", "args": {"project_id": "demo/repo", "issue_iid": 1}},
    {"type": "tool_result", "name": "get_issue"},
    {"type": "reasoning", "text": "Issue points at utils/parser.py. Fetching the file."},
    {"type": "tool_call", "name": "get_file_contents", "args": {"file_path": "utils/parser.py"}},
    {"type": "tool_result", "name": "get_file_contents"},
    {"type": "reasoning", "text": "Found the off-by-one. Creating a fix branch."},
    {"type": "tool_call", "name": "create_branch", "args": {"branch": "sentinel/fix-issue-1"}},
    {"type": "tool_result", "name": "create_branch"},
    {"type": "tool_call", "name": "create_or_update_file", "args": {"branch": "sentinel/fix-issue-1"}},
    {"type": "tool_result", "name": "create_or_update_file"},
    {"type": "tool_call", "name": "create_merge_request", "args": {"source_branch": "sentinel/fix-issue-1"}},
    {"type": "tool_result", "name": "create_merge_request"},
    {"type": "final", "text": "Fixed the off-by-one in `utils/parser.py` and opened MR !42 for review."},
]


@app.post("/agent/stream/mock")
async def agent_stream_mock(req: AgentRequest) -> StreamingResponse:
    """Replay a fixed multi-step SSE sequence (no model/network) for UI testing."""

    async def event_source() -> AsyncIterator[bytes]:
        for event in _MOCK_EVENTS:
            yield f"data: {json.dumps(event)}\n\n".encode()
            await asyncio.sleep(0.4)  # realistic streaming cadence
        yield b"data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

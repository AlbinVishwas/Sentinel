import json
import os
from collections.abc import AsyncIterator


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse

import asyncio

from sentinel_agent.agent import MAX_ITERATIONS, READ_TOOLS, WRITE_TOOLS, root_agent
from sentinel_agent.gitlab_health import check_gitlab_auth
from sentinel_agent.runner import run_agent, stream_agent

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


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe used by Cloud Run and local smoke tests."""
    return {"status": "ok", "service": "sentinel-backend"}


@app.get("/health/gitlab")
async def health_gitlab() -> dict[str, object]:
    """Preflight the GitLab credential (Phase 5 — Secret Manager check).

    AI-free: pings `GET /user` with the configured PAT so a missing/expired token
    is caught as a clear 401 here instead of failing opaquely mid-agent-run.
    """
    return await check_gitlab_auth()


@app.get("/agent/info")
async def agent_info() -> dict[str, object]:
    """Report the agent's model, tool surface, and active safety guardrails.

    Static metadata only (no GitLab call), so this stays a fast readiness check
    confirming the ADK agent + Gemini model loaded inside the FastAPI process.
    """
    return {
        "name": root_agent.name,
        "model": root_agent.model,
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


@app.post("/agent/run")
async def agent_run(req: AgentRequest) -> dict[str, object]:
    """Run one request to completion and return the final result (non-streaming)."""
    return await run_agent(
        req.prompt,
        session_id=req.session_id,
        gitlab_project=req.gitlab_project,
    )


@app.post("/agent/stream")
async def agent_stream(req: AgentRequest) -> StreamingResponse:
    """Stream the agent's steps as Server-Sent Events.

    Each SSE `data:` line is one JSON event from `stream_agent` (reasoning, tool_call,
    tool_result, final, aborted, error), letting the UI render agency in real time.
    """

    async def event_source() -> AsyncIterator[bytes]:
        async for event in stream_agent(
            req.prompt,
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

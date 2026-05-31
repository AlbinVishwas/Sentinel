import json
import os
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from sentinel_agent.agent import MAX_ITERATIONS, READ_TOOLS, WRITE_TOOLS, root_agent
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


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe used by Cloud Run and local smoke tests."""
    return {"status": "ok", "service": "sentinel-backend"}


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
    return await run_agent(req.prompt, session_id=req.session_id)


@app.post("/agent/stream")
async def agent_stream(req: AgentRequest) -> StreamingResponse:
    """Stream the agent's steps as Server-Sent Events.

    Each SSE `data:` line is one JSON event from `stream_agent` (reasoning, tool_call,
    tool_result, final, aborted, error), letting the UI render agency in real time.
    """

    async def event_source() -> AsyncIterator[bytes]:
        async for event in stream_agent(req.prompt, session_id=req.session_id):
            yield f"data: {json.dumps(event)}\n\n".encode()
        yield b"data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

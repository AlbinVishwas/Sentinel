from fastapi import FastAPI

from sentinel_agent.agent import MAX_ITERATIONS, READ_TOOLS, WRITE_TOOLS, root_agent

app = FastAPI(
    title="Sentinel API",
    description="AI-Powered CI/CD Overwatch and Autonomous SRE for GitLab",
    version="0.1.0",
)


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
            "Risk 1: direct commits/pushes to main/master blocked (before_tool_callback)",
            "Risk 1: tool allow-list exposes no delete/destructive tool",
            "Risk 2: max_llm_calls ceiling then abort message",
            "Risk 3: untrusted issue/MR text wrapped in <UNTRUSTED_ISSUE_DATA> (after_tool_callback)",
        ],
    }

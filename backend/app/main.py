from fastapi import FastAPI

from sentinel_agent.agent import READ_TOOLS, root_agent

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
    """Report the initialized agent's model and read-only tool surface.

    Static metadata only (no GitLab call), so this stays a fast readiness check
    confirming the ADK agent + Gemini model loaded inside the FastAPI process.
    """
    return {
        "name": root_agent.name,
        "model": root_agent.model,
        "mode": "read-only",
        "read_tools": READ_TOOLS,
    }

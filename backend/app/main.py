from fastapi import FastAPI

app = FastAPI(
    title="Sentinel API",
    description="AI-Powered CI/CD Overwatch and Autonomous SRE for GitLab",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe used by Cloud Run and local smoke tests."""
    return {"status": "ok", "service": "sentinel-backend"}

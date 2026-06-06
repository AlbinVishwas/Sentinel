# ---------- Single-stage: Python 3.12 + Node.js 22 ----------
FROM python:3.12-slim

# Install Node.js 22 from the official NodeSource distribution.
# This gives us a fully working node/npm/npx — unlike copying binaries
# from a node image, which breaks npx's require('../lib/cli.js').
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Pre-install the MCP server globally so npx doesn't download it on cold start
RUN npx -y @zereight/mcp-gitlab --version 2>/dev/null || true

WORKDIR /app

# Python dependencies (install first for Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code only — no .env, no scripts, no .venv
COPY app/ app/
COPY sentinel_agent/ sentinel_agent/

# Cloud Run injects $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Single-worker uvicorn — the agent is async and holds state per request.
# Cloud Run scales horizontally via instances, not workers.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

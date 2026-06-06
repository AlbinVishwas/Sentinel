# Phase 6 — Production Deployment & Hackathon Submission

> **Target Dates:** June 9 – June 10, 2026
> Derived from PROJECT_PLAN.md (the SSOT). Tracks the Phase 6 items in CHECKLIST.md.

**Environment:** continues from Phase 5. GCP project = `sentinel-sre-nexol`. The backend and frontend are both working locally; all four Phase 5 verification tiers are green.

> **Goal:** deploy both tiers to Google Cloud Run so the hackathon judges see a live, hosted URL. Store production secrets in Google Cloud Secret Manager — never in environment variables or container images. Record the 3-minute demo video and submit to Devpost.

> **Status:** **Deployment complete (June 7, 2026).** Both services are live on Cloud Run. Secret Manager holds the PAT. End-to-end verified — the agent streams tool calls and final markdown in the production UI.

> **Principle: zero local breakage.** Every step in this phase adds *deployment infrastructure* alongside the existing code. No existing source file is modified unless strictly necessary (e.g. adding a `Dockerfile`). Local dev (`uvicorn` + `npm run dev`) must keep working unchanged.

---

## Architecture (production)

```text
┌─────────────────────────────────────────────────────────┐
│                   Google Cloud Run                       │
│                                                         │
│  ┌──────────────────────┐   ┌────────────────────────┐  │
│  │ sentinel-frontend    │──▶│ sentinel-backend       │  │
│  │ (Next.js standalone) │   │ (FastAPI + ADK + MCP)  │  │
│  │ Port 3000            │   │ Port 8080              │  │
│  └──────────────────────┘   └────────┬───────────────┘  │
│                                      │                   │
│           ┌──────────────────────────┘                   │
│           ▼                                              │
│  ┌─────────────────────┐                                │
│  │ Secret Manager      │                                │
│  │ GITLAB_PERSONAL_    │                                │
│  │ ACCESS_TOKEN        │                                │
│  └─────────────────────┘                                │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────────┐     ┌────────────────────┐     │
│  │ GitLab MCP Server   │────▶│ gitlab.com API     │     │
│  │ (npx, stdio)        │     └────────────────────┘     │
│  └─────────────────────┘                                │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────────┐                                │
│  │ Vertex AI (Gemini   │                                │
│  │ 3.5 Flash, global)  │                                │
│  └─────────────────────┘                                │
└─────────────────────────────────────────────────────────┘
```

**Two Cloud Run services**, each with its own `Dockerfile`:

| Service | Source dir | Port | Key dependency |
| --- | --- | --- | --- |
| `sentinel-backend` | `backend/` | 8080 (Cloud Run default) | Python 3.12 + Node.js 22 (MCP needs `npx`) |
| `sentinel-frontend` | `frontend/` | 3000 | Node.js 22 (Next.js standalone output) |

The frontend's proxy route handler (`/api/agent/stream`) talks to the backend's internal URL — both are on Cloud Run, so this is service-to-service. `BACKEND_URL` is set on the frontend service to the backend's Cloud Run URL.

---

## Prerequisites

| Need | How to check | Enable if missing |
| --- | --- | --- |
| `gcloud` CLI authenticated | `gcloud auth list` | `gcloud auth login` |
| GCP project set | `gcloud config get-value project` → `sentinel-sre-nexol` | `gcloud config set project sentinel-sre-nexol` |
| Cloud Run API | `gcloud services list --enabled \| grep run` | `gcloud services enable run.googleapis.com` |
| Secret Manager API | `gcloud services list --enabled \| grep secretmanager` | `gcloud services enable secretmanager.googleapis.com` |
| Artifact Registry API | `gcloud services list --enabled \| grep artifactregistry` | `gcloud services enable artifactregistry.googleapis.com` |
| Cloud Build API | `gcloud services list --enabled \| grep cloudbuild` | `gcloud services enable cloudbuild.googleapis.com` |
| Vertex AI API | already enabled (Phase 2) | — |

---

## Step 1 — Enable GCP APIs

```bash
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project=sentinel-sre-nexol
```

Verify:
```bash
gcloud services list --enabled --project=sentinel-sre-nexol \
  --filter="name:(run OR secretmanager OR artifactregistry OR cloudbuild)" \
  --format="table(name)"
```

---

## Step 2 — Store the GitLab PAT in Secret Manager

The PAT must **never** be baked into a container image or passed as a plain env var. Secret Manager mounts it at runtime.

```bash
# Create the secret (one-time)
gcloud secrets create GITLAB_PERSONAL_ACCESS_TOKEN \
  --project=sentinel-sre-nexol \
  --replication-policy=automatic

# Add the secret value
echo -n "<YOUR_GITLAB_PAT>" | gcloud secrets versions add GITLAB_PERSONAL_ACCESS_TOKEN \
  --project=sentinel-sre-nexol \
  --data-file=-
```

Verify:
```bash
gcloud secrets versions access latest \
  --secret=GITLAB_PERSONAL_ACCESS_TOKEN \
  --project=sentinel-sre-nexol | head -c 10
# Should print the first 10 chars of your PAT
```

---

## Step 3 — Backend Dockerfile

**Key challenge:** the backend is Python (FastAPI + ADK), but the GitLab MCP server runs via `npx @zereight/mcp-gitlab` — a Node.js child process spawned over stdio. The Docker image needs **both runtimes**.

Create `backend/Dockerfile`:

```dockerfile
# ---------- Stage 1: Node.js layer (MCP server) ----------
FROM node:22-slim AS node-base

# Pre-install the MCP server so npx doesn't download it on every cold start
RUN npx -y @zereight/mcp-gitlab --version 2>/dev/null || true

# ---------- Stage 2: Python + Node.js runtime ----------
FROM python:3.12-slim

# Install Node.js (copy from the node stage)
COPY --from=node-base /usr/local/bin/node /usr/local/bin/node
COPY --from=node-base /usr/local/bin/npx /usr/local/bin/npx
COPY --from=node-base /usr/local/bin/npm /usr/local/bin/npm
COPY --from=node-base /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-base /root/.npm /root/.npm

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY app/ app/
COPY sentinel_agent/ sentinel_agent/

# Cloud Run serves on $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Production server (single worker — the agent is async and holds state per request)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

Create `backend/.dockerignore`:

```
.venv/
.env
__pycache__/
*.pyc
scripts/
.next/
```

> **No `.env` file is copied** — secrets come from Secret Manager, and GCP env vars are set on the service.

---

## Step 4 — Frontend Dockerfile

Next.js 16 supports `output: "standalone"` which produces a self-contained Node.js server (no `node_modules` needed at runtime).

Update `frontend/next.config.ts` to add standalone output:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

Create `frontend/Dockerfile`:

```dockerfile
FROM node:22-slim AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---------- Production ----------
FROM node:22-slim AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# Copy standalone output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

Create `frontend/.dockerignore`:

```
node_modules/
.next/
.env.local
```

---

## Step 5 — Deploy the backend to Cloud Run

Build and deploy using Cloud Build (no local Docker required):

```bash
gcloud run deploy sentinel-backend \
  --project=sentinel-sre-nexol \
  --region=us-central1 \
  --source=backend/ \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=300 \
  --allow-unauthenticated \
  --set-secrets="GITLAB_PERSONAL_ACCESS_TOKEN=GITLAB_PERSONAL_ACCESS_TOKEN:latest" \
  --set-env-vars="\
GOOGLE_CLOUD_PROJECT=sentinel-sre-nexol,\
GOOGLE_CLOUD_LOCATION=global,\
GOOGLE_GENAI_USE_VERTEXAI=TRUE,\
SENTINEL_MODEL=gemini-3.5-flash,\
MAX_ITERATIONS=10,\
GITLAB_INSTANCE_URL=https://gitlab.com,\
GITLAB_DEFAULT_PROJECT=albinvishwas7/sentinel-test-sandbox,\
CORS_ALLOW_ORIGINS=*"
```

**Key flags explained:**

| Flag | Why |
| --- | --- |
| `--source=backend/` | Cloud Build builds the Dockerfile in-place (no local Docker needed) |
| `--set-secrets` | Mounts the PAT from Secret Manager as an env var at runtime |
| `--timeout=300` | Agent runs can take up to 60s; 5min timeout is safe headroom |
| `--memory=1Gi` | ADK + MCP child process need reasonable memory |
| `--allow-unauthenticated` | Hackathon judges need public access |
| `CORS_ALLOW_ORIGINS=*` | The frontend service URL is dynamic; in production both are behind a domain |

**Verify the backend:**

```bash
BACKEND_URL=$(gcloud run services describe sentinel-backend \
  --project=sentinel-sre-nexol --region=us-central1 \
  --format='value(status.url)')

curl -s "$BACKEND_URL/health"
# {"status":"ok","service":"sentinel-backend"}

curl -s "$BACKEND_URL/health/gitlab"
# {"status":"ok","authenticated":true,...,"username":"albinvishwas7",...}

curl -s "$BACKEND_URL/agent/info" | python3 -m json.tool
# Should show the full agent config with guardrails
```

---

## Step 6 — Deploy the frontend to Cloud Run

```bash
gcloud run deploy sentinel-frontend \
  --project=sentinel-sre-nexol \
  --region=us-central1 \
  --source=frontend/ \
  --port=3000 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=300 \
  --allow-unauthenticated \
  --set-env-vars="BACKEND_URL=$BACKEND_URL"
```

> `$BACKEND_URL` is the backend service URL from Step 5. The frontend's proxy route handler (`/api/agent/stream`) uses it to reach the backend.

**Verify the frontend:**

```bash
FRONTEND_URL=$(gcloud run services describe sentinel-frontend \
  --project=sentinel-sre-nexol --region=us-central1 \
  --format='value(status.url)')

echo "Frontend live at: $FRONTEND_URL"
# Open in browser → should redirect to /chat and show the Sentinel UI
```

---

## Step 7 — End-to-end production verification

With both services running:

1. **Health checks:**
   ```bash
   curl -s "$BACKEND_URL/health"
   curl -s "$BACKEND_URL/health/gitlab"
   ```

2. **Agent info:**
   ```bash
   curl -s "$BACKEND_URL/agent/info" | python3 -m json.tool
   ```

3. **Live agent call (via backend directly):**
   ```bash
   curl -N -X POST "$BACKEND_URL/agent/stream" \
     -H "Content-Type: application/json" \
     -d '{"prompt":"Check issue #1 in albinvishwas7/sentinel-test-sandbox"}'
   ```

4. **Full browser test:**
   Open `$FRONTEND_URL` in Chrome → type the prompt → confirm SSE streaming + agency log render.

---

## Step 8 — IAM: grant the Cloud Run service account access to secrets and Vertex AI

Cloud Run's default service account needs:

```bash
PROJECT_NUMBER=$(gcloud projects describe sentinel-sre-nexol --format='value(projectNumber)')

# Secret Manager access
gcloud secrets add-iam-policy-binding GITLAB_PERSONAL_ACCESS_TOKEN \
  --project=sentinel-sre-nexol \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Vertex AI access (should already be granted from Phase 2 ADC setup, but confirm)
gcloud projects add-iam-policy-binding sentinel-sre-nexol \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

> **Note:** If using a custom service account, replace the default compute SA email accordingly.

---

## Files created in this phase

| File | Type | Purpose |
| --- | --- | --- |
| `backend/Dockerfile` | [NEW] | Dual Python+Node.js container for the FastAPI backend + MCP child process |
| `backend/.dockerignore` | [NEW] | Exclude .venv, .env, scripts from the image |
| `frontend/Dockerfile` | [NEW] | Next.js standalone build for the frontend |
| `frontend/.dockerignore` | [NEW] | Exclude node_modules, .next, .env.local from the image |

| File | Type | Purpose |
| --- | --- | --- |
| `frontend/next.config.ts` | [MODIFY] | Add `output: "standalone"` for the Docker build |

> **No other existing file is modified.** The `.env` file, all `sentinel_agent/` source, `app/main.py`, and the frontend source remain unchanged. Local dev continues to work via `uvicorn` + `npm run dev`.

---

## Security checklist

- [x] GitLab PAT is in Secret Manager, not in the Docker image or plain env vars.
- [x] No `.env` file is copied into any container.
- [x] Backend is `--allow-unauthenticated` (hackathon requirement), but the PAT is never exposed to the browser.
- [x] The frontend proxy route keeps `BACKEND_URL` server-side only.
- [x] Cloud Run service account has minimal IAM: `secretmanager.secretAccessor` + `aiplatform.user`.

---

## Phase 6 completion checklist

- [x] Enable GCP APIs (Cloud Run, Secret Manager, Artifact Registry, Cloud Build).
- [x] Store the GitLab PAT in Secret Manager.
- [x] Create `backend/Dockerfile` (Python 3.12 + Node.js 22).
- [x] Create `frontend/Dockerfile` (Next.js standalone).
- [x] Modify `frontend/next.config.ts` (`output: "standalone"`).
- [x] Deploy backend to Cloud Run (`sentinel-backend`). URL: `https://sentinel-backend-332685207372.us-central1.run.app`
- [x] Deploy frontend to Cloud Run (`sentinel-frontend`). URL: `https://sentinel-frontend-rnvsnqnyja-uc.a.run.app`
- [x] IAM: grant service account Secret Manager + Vertex AI access.
- [x] Verify health, GitLab auth, agent info, and live streaming end-to-end. **Verified — full agent loop (get_issue → get_file_contents → list_branches → list_commits → final) streamed in production UI.**
- [ ] Record the 3-minute demonstration video.
- [ ] Submit to Devpost.

> **Execution order matters:** Steps 1–2 (APIs + secrets) must come first. Step 8 (IAM) should be done before Step 5 (backend deploy) to avoid runtime permission errors. Steps 3–4 (Dockerfiles) can be done any time before deploy.

---

## Rollback

If anything breaks:

```bash
# Delete a Cloud Run service
gcloud run services delete sentinel-backend --project=sentinel-sre-nexol --region=us-central1
gcloud run services delete sentinel-frontend --project=sentinel-sre-nexol --region=us-central1

# Delete the secret (if needed)
gcloud secrets delete GITLAB_PERSONAL_ACCESS_TOKEN --project=sentinel-sre-nexol
```

Local dev is unaffected — the Dockerfiles and `output: "standalone"` in next.config.ts don't change local behavior.

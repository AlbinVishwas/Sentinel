# Phase 1 — Foundations, Scaffolding, and Auth

> **Target Dates:** May 31 – June 1, 2026
> Derived from [PROJECT_PLAN.md](../PROJECT_PLAN.md) (the SSOT). Tracks the 8 Phase 1 items in [CHECKLIST.md](../CHECKLIST.md).

**Environment confirmed on this machine:** git 2.53 · Node v24.14 / npm 11.11 · Python 3.12 (use `python3.12` — the default `python3` is an old 3.9.6) · gh 2.91. `gcloud` is not installed, but it is only needed in Phase 6.

> **Note:** Source code lives on **GitHub** (per Risk 4 — "the public GitHub repository"), while the *agent* operates on GitLab. The git remote points at GitHub.

---

## Step 1 — Open a terminal at the project root

Everything happens inside your existing folder:

```bash
cd /Users/albinvishwas/Developer/Projects/Active/Sentinel
```

---

## Step 2 — Initialize the Git repository

```bash
git init
git branch -M main
```

This creates the repo and names the default branch `main`.

---

## Step 3 — Create the `.gitignore`

Create a file named `.gitignore` at the root and paste this in. It covers Python, Node/Next.js, secrets, and OS cruft — exactly what the checklist asks for:

```gitignore
# === Secrets (NEVER COMMIT) ===
.env
.env.*
!.env.example
*.pem
*.key
gcloud-key.json
service-account*.json

# === Python / backend ===
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/

# === Node / frontend ===
node_modules/
.next/
out/
npm-debug.log*
yarn-error.log*
.pnpm-debug.log*

# === Build artifacts ===
dist/
build/
*.log

# === OS / editor ===
.DS_Store
.idea/
.vscode/*
!.vscode/extensions.json
```

---

## Step 4 — Add the MIT `LICENSE`

The plan marks MIT as **mandatory**. Create a file named `LICENSE` (no extension) at the root and paste this, replacing the holder name if you want something other than your org:

```text
MIT License

Copyright (c) 2026 Nexol Media

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Step 5 — Initialize `README.md`

Create `README.md` at the root with the project overview pulled straight from the SSOT:

````markdown
# Sentinel

> **AI-Powered CI/CD Overwatch and Autonomous SRE for GitLab**

Sentinel is an autonomous AI agent that monitors GitLab repositories, triages
open issues, investigates broken CI/CD pipelines, and programmatically generates
secure, verified code patches via Merge Requests — keeping the human engineer
safely in the loop.

Built for the **GitLab Track** of the Google Cloud Rapid Agent Hackathon.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Orchestration | Google Cloud Vertex AI Agent Development Kit (ADK) |
| Core Model | Gemini 3.5 Flash |
| Backend | FastAPI (async Python) |
| Integration | GitLab Model Context Protocol (MCP) Server |
| Frontend | Next.js (App Router) + Tailwind CSS + TypeScript |
| Deployment | Google Cloud Run |
| Secrets | Google Cloud Secret Manager |

## Repository Layout

```
/backend    FastAPI service + ADK agent orchestration
/frontend   Next.js chat interface
```

## License

[MIT](LICENSE)
````

---

## Step 6 — Scaffold the `/backend` (FastAPI skeleton)

Run these commands to create the backend folder, a Python 3.12 virtual environment, and the dependency files:

```bash
mkdir -p backend/app
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Create `backend/requirements.txt`:

```text
fastapi
uvicorn[standard]
python-dotenv
pydantic
pydantic-settings
httpx
```

> We deliberately hold off on `google-adk` and the MCP libraries — those belong to Phase 2. Phase 1 is just a runnable skeleton.

Install them:

```bash
pip install -r requirements.txt
```

Create `backend/app/__init__.py` (empty file):

```python
```

Create `backend/app/main.py` — a minimal but real FastAPI app:

```python
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
```

Verify it runs (from inside `backend/`, venv active):

```bash
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/health — you should see `{"status":"ok","service":"sentinel-backend"}`. Then `Ctrl+C` to stop, and `deactivate` to leave the venv. Go back to root:

```bash
cd /Users/albinvishwas/Developer/Projects/Active/Sentinel
```

---

## Step 7 — Scaffold the `/frontend` (Next.js + Tailwind + TS)

From the project root, run the official scaffolder. The flags pre-answer every prompt so it matches the stack in the plan:

```bash
npx create-next-app@latest frontend \
  --ts \
  --tailwind \
  --app \
  --eslint \
  --src-dir \
  --import-alias "@/*" \
  --no-turbopack \
  --use-npm
```

If `npx` asks to install `create-next-app`, type **`y`**. This produces `frontend/` with the App Router, Tailwind, and TypeScript already wired. Quick check:

```bash
cd frontend
npm run dev
```

Open http://localhost:3000 to see the starter page, then `Ctrl+C` and return to root.

---

## Step 8 — Create the local `.env` (DO NOT COMMIT)

Two files: a committed **template** and the real **secret** file.

Create `backend/.env.example` (this one *is* committed — it documents required keys without values):

```text
# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=

# GitLab
GITLAB_PERSONAL_ACCESS_TOKEN=
GITLAB_INSTANCE_URL=https://gitlab.com

# App
MAX_ITERATIONS=5
```

Create `backend/.env` (the **real** one — fill values later, never commit):

```text
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

GITLAB_PERSONAL_ACCESS_TOKEN=glpat-REPLACE_ME
GITLAB_INSTANCE_URL=https://gitlab.com

MAX_ITERATIONS=5
```

---

## Step 9 — Confirm `.env` is ignored by Git

This is the safety check from the checklist. Run:

```bash
git add -A
git status
```

In the output, **confirm you do NOT see `backend/.env`** anywhere. You *should* see `backend/.env.example`, `.gitignore`, `LICENSE`, `README.md`, `backend/`, and `frontend/`. Double-check explicitly:

```bash
git check-ignore backend/.env
```

If that prints `backend/.env`, it's correctly ignored. ✅ If it prints nothing, **stop** — the gitignore isn't catching it.

---

## Step 10 — First commit

```bash
git commit -m "Phase 1: foundations, scaffolding, and auth setup"
```

Optional — create the GitHub repo and push, since you have `gh`:

```bash
gh repo create Sentinel --public --source=. --remote=origin --push
```

---

## Phase 1 completion checklist

- [ ] Git repository initialized
- [ ] `.gitignore` added (covers `.env`, `node_modules/`, `__pycache__/`, build artifacts)
- [ ] MIT `LICENSE` added
- [ ] `README.md` initialized with project overview
- [ ] `/backend` scaffolded (FastAPI skeleton runs, `/health` returns ok)
- [ ] `/frontend` scaffolded (Next.js App Router + Tailwind + TypeScript runs)
- [ ] `backend/.env` created (and `.env.example` committed)
- [ ] `.env` confirmed ignored by Git

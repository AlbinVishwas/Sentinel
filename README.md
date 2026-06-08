# Sentinel

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **MIT Open Source License Notice:** This project is licensed under the MIT License. See the [LICENSE](LICENSE) file at the root of this repository for the full text of the license.

---

**AI-Powered CI/CD Overwatch and Autonomous SRE for GitLab**  
*Remedial automation at scale, keeping the developer safely in the loop.*

> **Live demo:** [sentinel-frontend-rnvsnqnyja-uc.a.run.app](https://sentinel-frontend-rnvsnqnyja-uc.a.run.app)  
> **Backend API:** [sentinel-backend-332685207372.us-central1.run.app](https://sentinel-backend-332685207372.us-central1.run.app/health)  
> Built for the **Google Cloud Rapid Agent Hackathon — GitLab Track**

---

## Overview

Sentinel is an autonomous Site Reliability Engineering (SRE) agent that monitors GitLab repositories, triages open issues, investigates broken CI/CD pipelines, and programmatically generates secure, verified code patches via Merge Requests. 

Sentinel is built for the **GitLab Track** of the Google Cloud Rapid Agent Hackathon.

### Vertex AI ADK & GitLab MCP Integration

- **Vertex AI Agent Development Kit (ADK)**: Powering the cognitive engine with **Gemini 3.5 Flash**, the ADK driving Sentinel runs a multi-step reasoning (ReAct) loop that analyzes issues and plans remediation steps.
- **GitLab Model Context Protocol (MCP) Server**: Acting as the secure API bridge, the MCP server provides the agent with structured, permissioned access to codebase files, branches, issues, and merge requests.

For detailed architecture diagrams, multi-step ReAct loops, and enterprise AI safety guardrails (infinite loop defuse, branch protection, context sanitization), please see our **[PROJECT_PILLAR.md](PROJECT_PILLAR.md)** documentation.

---

## Repository Layout

```
├── backend/      # FastAPI service + Vertex AI ADK agent orchestration
└── frontend/     # Next.js App Router chat interface
```

---

## Setup & Installation

Follow these steps to run Sentinel locally:

### 1. Prerequisites
- **Node.js**: v18.0.0 or higher
- **Python**: 3.12.x or higher
- **GitLab PAT**: A GitLab Personal Access Token with `api` scope.
- **Google Cloud ADC**: Authenticated gcloud environment with Vertex AI APIs enabled.

---

### 2. Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Configure environment variables. Copy the example file and populate it with your credentials:
   ```bash
   cp .env.example .env
   ```
   *Note: Set your `GOOGLE_CLOUD_PROJECT` and your `GITLAB_PERSONAL_ACCESS_TOKEN` in `.env`.*
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Verify the API is live by visiting [http://localhost:8000/health](http://localhost:8000/health).

---

### 3. Frontend Setup (Next.js)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install the Node modules:
   ```bash
   npm install
   ```
3. Set up the local environment variables:
   ```bash
   cp .env.local.example .env.local
   ```
   *Note: Ensure `BACKEND_URL` is pointed to the backend API (`http://localhost:8000`). This variable is server-side only and is never exposed to the browser.*
4. Run the Next.js development server:
   ```bash
   npm run dev
   ```
5. Open [http://localhost:3000](http://localhost:3000) in your browser to interact with the Sentinel dashboard.

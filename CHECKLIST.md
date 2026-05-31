# Project Sentinel — Execution Checklist

> Living task tracker derived from [PROJECT_PLAN.md](PROJECT_PLAN.md) (the SSOT).
> Check items off as they are completed. Last updated: May 31, 2026 (Phases 1–3 complete; guardrailed read-write GitLab agent working).

**Legend:** `[ ]` Not started · `[~]` In progress · `[x]` Done

---

## Progress Overview

| Phase | Title | Target Dates | Progress |
| --- | --- | --- | --- |
| 1 | Foundations, Scaffolding, and Auth | May 31 – June 1, 2026 | 8 / 8 ✅ |
| 2 | Agent Architecture & MCP Bridge | June 2 – June 4, 2026 | 7 / 7 ✅ |
| 3 | Writing Capabilities & Safety Guardrails | June 5 – June 6, 2026 | 7 / 7 ✅ |
| 4 | UI Development & Thought Process Streaming | June 7, 2026 | 0 / 2 |
| 5 | Verification & Automated Validation | June 8, 2026 | 0 / 4 |
| 6 | Production Deployment & Hackathon Submission | June 9 – June 10, 2026 | 0 / 5 |

---

## Phase 1 — Foundations, Scaffolding, and Auth

**Target Dates:** May 31 – June 1, 2026

- [x] Initialize the root Git repository.
- [x] Add a standard `.gitignore` (include `.env`, `node_modules/`, `__pycache__/`, build artifacts).
- [x] Add the `LICENSE` file (MIT).
- [x] Initialize `README.md` with the project overview.
- [x] Scaffold the `/backend` directory (FastAPI project skeleton).
- [x] Scaffold the `/frontend` directory (Next.js App Router + Tailwind + TypeScript).
- [x] Create the local `.env` file (**DO NOT COMMIT**).
- [x] Confirm `.env` is ignored by Git.

## Phase 2 — Agent Architecture & MCP Bridge

**Target Dates:** June 2 – June 4, 2026

- [x] Install the `google-adk` package in the backend. *(google-adk 2.1.0 + `mcp` — the latter is not bundled by ADK)*
- [x] Configure Vertex AI / Google Cloud credentials for local development. *(project `sentinel-sre-nexol`, `aiplatform.googleapis.com` enabled, ADC via `gcloud auth application-default login` — no key file)*
- [x] Initialize the Gemini 3.5 Flash model within the FastAPI app. *(`gemini-3.5-flash` on the `global` endpoint — 404s in us-central1; exposed at `GET /agent/info`)*
- [x] Stand up the GitLab MCP server locally. *(`@zereight/mcp-gitlab` via `npx` over stdio, `GITLAB_READ_ONLY_MODE=true` — no Docker)*
- [x] Connect the ADK orchestrator to the GitLab MCP server. *(`MCPToolset` → `root_agent` in `backend/sentinel_agent/agent.py`)*
- [x] Map the GitLab MCP "Read" tools. *(15-tool allow-list incl. `get_issue`, `get_file_contents`, `search_repositories`; confirmed against the live 58-tool read-only list)*
- [x] Smoke-test a read-only round trip (prompt → tool call → response). *(`scripts/smoke_read.py`: agent called `get_issue`, named `utils/parser.py`, no write tool)*

## Phase 3 — Writing Capabilities & Safety Guardrails

**Target Dates:** June 5 – June 6, 2026

- [ ] Map the GitLab MCP "Write" tools (branch create, commit, open Merge Request).
- [x] ~~Scope the GitLab PAT to `read_api` + `write_repository` only.~~ **Revised:** PAT scoped to `api` (token `sentinel-mcp`, expires 2026-09-30). `write_repository` is Git-over-HTTPS only and cannot authenticate API calls / open MRs; `api` is required for MR creation. Risk 1 is instead enforced via the project **Developer** role + Phase 3 system-prompt guardrails.
- [ ] Add the system prompt prohibiting pushes to `main` / `master`.
- [ ] Implement XML delimiter wrapping (`<UNTRUSTED_ISSUE_DATA>`) for untrusted issue text.
- [ ] Add the prompt-injection defense system instruction.
- [ ] Set `max_iterations = 5` on the ADK ReAct loop.
- [ ] Implement the abort + error message on reaching max iterations.

## Phase 4 — UI Development & Thought Process Streaming

**Target Dates:** June 7, 2026

- [ ] Build the Next.js chat interface.
- [ ] Wire the frontend to the FastAPI backend (HTTP POST).
- [ ] Implement streaming status updates from backend to UI.
- [ ] Render intermediate agent actions / thoughts in real time.

## Phase 5 — Verification & Automated Validation

**Target Dates:** June 8, 2026

- [ ] Execute Test Case 1 — Context Gathering ("Read" loop): parses issue, finds file, no mutation.
- [ ] Execute Test Case 2 — Code Modification ("Write" loop): live MR URL returned, `main` untouched.
- [ ] Execute Test Case 3 — Boundary Protection ("Guardrail" check): declines push to `main`, refuses deletion.
- [ ] Execute Test Case 4 — Infinite Loop Timeout: halts after 5 attempts, returns error to UI.

## Phase 6 — Production Deployment & Hackathon Submission

**Target Dates:** June 9 – June 10, 2026

- [ ] Deploy the backend to Google Cloud Run.
- [ ] Store production keys in Google Cloud Secret Manager.
- [ ] Configure Cloud Run to mount secrets at runtime.
- [ ] Deploy the frontend.
- [ ] Record the 3-minute demonstration video.
- [ ] Submit to Devpost.

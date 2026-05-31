# Phase 4 — UI Development & Thought-Process Streaming

> **Target Dates:** June 7, 2026
> Derived from [PROJECT_PLAN.md](../PROJECT_PLAN.md) (the SSOT). Tracks the Phase 4 items in [CHECKLIST.md](../CHECKLIST.md).

**Environment:** continues from Phase 3. Frontend = Next.js **16.2.6** (App Router, Turbopack) + React 19 + Tailwind v4 + TypeScript, in `frontend/`. Backend = the FastAPI app from Phase 3.

> **Goal:** a clean operator console that streams Sentinel's intermediate steps in real time (Quadrant D). The design is deliberately **dark-only, monochrome, and motion-free** — no transitions, no animations, no spinners. Color appears only to signal state.

> **Note on Next.js 16:** this is a newer major than most references assume (`frontend/AGENTS.md` flags it). Everything here was validated against the **installed** version via `npm run build` + `npm run lint`, not from memory — both pass clean.

---

## Design system (locked)

- **Theme:** dark-only. One crafted theme; no light toggle.
- **Palette:** neutral zinc scale (`oklch`), near-black bg, softened off-white text — never pure `#000`/`#fff`. **No bright colors.**
- **Color = meaning only:** one low-chroma accent for *working/focus*, desaturated *success* (MR opened) and *danger* (blocked/error). Chrome is colorless.
- **Motion: none.** Streaming tokens append; state is instant; loading is the literal word `Working…`.
- **Type:** Geist (UI) + Geist Mono (the agency log, tool args, code).
- **Surfaces:** flat, hairline borders, no shadows; one calm conversation column.

All tokens live in [frontend/src/app/globals.css](../frontend/src/app/globals.css) under Tailwind v4's `@theme`.

---

## Step 1 — Backend: stream the agent's steps (SSE)

Phase 3's `run_agent` only returned the final result. Phase 4 adds `stream_agent`, an
async generator yielding one structured event per step, and `run_agent` is refactored to
consume it (single code path). See [backend/sentinel_agent/runner.py](../backend/sentinel_agent/runner.py).

Event shapes (each JSON-encodable for SSE):

```
{"type":"reasoning","text":...}            the model's intermediate prose
{"type":"tool_call","name":...,"args":...} an MCP tool invocation
{"type":"tool_result","name":...}          a tool returned (payload omitted — may be large/untrusted)
{"type":"final","text":...}                the final answer
{"type":"aborted","message":...}           hit the iteration ceiling (Risk 2)
{"type":"error","message":...}             safe failure (never crashes the stream)
```

> The `tool_result` event intentionally omits the payload: it can be large and, for
> issue/MR reads, is wrapped untrusted data. The UI only needs to show *that* a tool ran.

## Step 2 — Backend: endpoints + CORS

[backend/app/main.py](../backend/app/main.py) gains:
- `POST /agent/run` — run to completion, return JSON (non-streaming clients/tests).
- `POST /agent/stream` — `StreamingResponse` of `text/event-stream`; each `data:` line is one event, terminated by `{"type":"done"}`.
- `CORSMiddleware` allowing `http://localhost:3000` in dev (configurable via `CORS_ALLOW_ORIGINS`). In production both tiers are same-origin, so this is dev-only convenience.

Request body: `{ "prompt": str, "session_id": str }` (validated by a Pydantic model).

**Verified (direct):** `POST /agent/stream` for issue #1 produced the event sequence
`tool_call(get_issue) → tool_result → final → done` and named `utils/parser.py`.

## Step 3 — Frontend: routing

App Router structure (`frontend/src/app/`):

```
layout.tsx              root: Geist fonts, dark <html>, metadata
page.tsx                redirect("/chat")
globals.css             @theme design tokens
chat/page.tsx           renders <Chat /> (client component)
api/agent/stream/route.ts   POST proxy -> FastAPI /agent/stream
```

**Why a proxy route handler** ([api/agent/stream/route.ts](../frontend/src/app/api/agent/stream/route.ts)):
the browser talks only to same-origin `/api/agent/stream`; the handler pipes
`upstream.body` straight through. The backend URL (`BACKEND_URL`) and any token never
reach the browser, and there's no production CORS. It's marked `dynamic = "force-dynamic"`
so it's never statically cached.

## Step 4 — Frontend: the chat UI

Three pieces, all motion-free:
- [components/chat.tsx](../frontend/src/components/chat.tsx) — client component. Holds turns,
  POSTs to the proxy, parses the SSE byte stream (`split("\n\n")` framing), and appends each
  event. `Enter` sends, `Shift+Enter` newlines. The send button reads `Working…` while busy.
- [components/agency-log.tsx](../frontend/src/components/agency-log.tsx) — the visible record of
  agency (Quadrant D): plain monospace lines like `[MCP call] get_issue issue_iid=1`, appended
  statically as events arrive.
- [lib/types.ts](../frontend/src/lib/types.ts) — shared `AgentEvent` / `AgencyEntry` types mirroring
  the backend events.

A persistent footer note states the active guardrails ("pushes to main/master/production are
blocked · branches confined to sentinel/*") — making safety legible in the UI itself.

## Step 5 — Run it locally

Two terminals:

```bash
# backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000

# frontend (BACKEND_URL points the proxy at the backend; in frontend/.env.local)
cd frontend && npm run dev    # http://localhost:3000  -> redirects to /chat
```

`frontend/.env.local` holds `BACKEND_URL=http://127.0.0.1:8000` (git-ignored).

---

## Verification status

| Check | Status |
| --- | --- |
| Backend `stream_agent` events + `/agent/stream` SSE (direct curl) | ✅ verified — `get_issue → result → final → done`, named `parser.py` |
| Guardrail suite after runner refactor | ✅ ALL PASS |
| Frontend `npm run build` (all routes compile, TypeScript clean) | ✅ pass |
| Frontend `npm run lint` | ✅ clean |
| `/` → `/chat` redirect (`307`), `/chat` renders the Sentinel UI | ✅ verified at runtime |
| **Full browser → proxy → backend chain at runtime** | ✅ verified — `POST :3000/api/agent/stream` streamed `tool_call → tool_result → final → done` and named `utils/parser.py` |

> **Verified end-to-end.** Backend stream, frontend build/lint/type-check, and the live
> three-hop request (browser → Next proxy → FastAPI → agent) all pass. Note: an earlier
> attempt 404'd because port 3000 was occupied by an unrelated local app — run Sentinel's
> frontend on a free port if 3000 is taken.

---

## Phase 4 completion checklist

- [x] Build the Next.js chat interface (dark, monochrome, motion-free).
- [x] Wire the frontend to the FastAPI backend (same-origin proxy route handler → HTTP POST).
- [x] Implement streaming status updates from backend to UI (SSE; `stream_agent` + `/agent/stream`).
- [x] Render intermediate agent actions / thoughts in real time (the agency log).

> **Up next (Phase 5):** execute the four mandatory test cases end-to-end through the UI
> (read loop, write/MR loop, guardrail refusal, infinite-loop timeout).

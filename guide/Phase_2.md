# Phase 2 — Agent Architecture & MCP Bridge

> **Target Dates:** June 2 – June 4, 2026
> Derived from PROJECT_PLAN.md (the SSOT). Tracks the Phase 2 items in CHECKLIST.md.

**Environment confirmed on this machine:** Python 3.12 venv at `backend/.venv` · Node v24.14 / npx 11.11 (≥18, required by the MCP server) · `gcloud` configured with project `sentinel-sre-nexol`, Vertex AI enabled, and Application Default Credentials (ADC) working · `google-adk` 2.1.0. **Docker is not needed** — the GitLab MCP server runs through `npx` over stdio.

> **Goal of this phase:** stand up the agent brain. Install Google's Agent Development Kit (ADK), point it at **Gemini 3.5 Flash** on Vertex AI, bridge it to GitLab through the **Model Context Protocol (MCP)**, expose only the **read** tools, and prove a single `prompt → tool call → response` round trip. Writing code / opening Merge Requests is **Phase 3** — this phase is strictly read-only.

> **Two gotchas this guide bakes in (discovered during execution):**
> 1. `google-adk` 2.1.0 does **not** bundle the `mcp` client package — install it explicitly.
> 2. `gemini-3.5-flash` returns **404 in `us-central1`** on a fresh project but works on the **`global`** endpoint — so we set `GOOGLE_CLOUD_LOCATION=global`.

---

## Step 1 — Add the ADK dependencies and install

Append to `backend/requirements.txt`:

```text
# Phase 2 — Agent orchestration
google-adk
mcp          # MCP client (StdioServerParameters etc.); not bundled by google-adk 2.1.0
```

Install and verify (from inside `backend/`, venv active):

```bash
cd /Users/albinvishwas/Developer/Projects/Active/Sentinel/backend
source .venv/bin/activate
pip install -r requirements.txt
python -c "from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset; from mcp import StdioServerParameters; print('ADK + mcp OK')"
adk --version
```

You should see `ADK + mcp OK` and the `adk` CLI version (`2.1.0` or newer).

---

## Step 2 — Switch to the `global` endpoint and verify the model

`gemini-3.5-flash` is served on the **global** Vertex endpoint, not the regional one. Update `backend/.env`:

```text
GOOGLE_CLOUD_PROJECT=sentinel-sre-nexol
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=TRUE
SENTINEL_MODEL=gemini-3.5-flash
GOOGLE_APPLICATION_CREDENTIALS=
```

Create `backend/scripts/verify_model.py`:

```python
"""Verify the configured Gemini model resolves on Vertex AI with the current ADC."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
MODEL = os.environ.get("SENTINEL_MODEL", "gemini-3.5-flash")


def main() -> None:
    client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
    resp = client.models.generate_content(model=MODEL, contents="Reply with the single word: pong")
    print(f"{MODEL} @ {PROJECT}/{LOCATION} -> {resp.text.strip()!r}")


if __name__ == "__main__":
    main()
```

Run it:

```bash
python scripts/verify_model.py
```

Expected (observed on this machine): `gemini-3.5-flash @ sentinel-sre-nexol/global -> 'pong'`. If 3.5 is ever unavailable, set `SENTINEL_MODEL=gemini-2.5-flash` (the stable fallback) in `.env`.

---

## Step 3 — Create the ADK agent package

ADK discovers an agent from a package exposing `root_agent`. Create `backend/sentinel_agent/`.

`backend/sentinel_agent/__init__.py`:

```python
from . import agent

__all__ = ["agent"]
```

`backend/sentinel_agent/agent.py`:

```python
"""Sentinel ADK agent — Phase 2 (read-only GitLab bridge)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from mcp import StdioServerParameters

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SENTINEL_MODEL = os.environ.get("SENTINEL_MODEL", "gemini-3.5-flash")

_GITLAB_INSTANCE = os.environ.get("GITLAB_INSTANCE_URL", "https://gitlab.com").rstrip("/")
GITLAB_API_URL = f"{_GITLAB_INSTANCE}/api/v4"

# Curated allow-list of GitLab read tools. With GITLAB_READ_ONLY_MODE=true the server
# exposes only read tools (verified: zero create/update/delete/cancel/retry tools appear),
# and this tool_filter narrows that ~58-tool surface to the handful Sentinel needs.
# Every name is confirmed against the server's live tool list (scripts/list_tools.py).
READ_TOOLS = [
    # issues
    "get_issue", "list_issues", "my_issues",
    # merge requests
    "get_merge_request", "list_merge_requests", "get_merge_request_diffs",
    # code / repository
    "get_file_contents", "get_repository_tree", "list_commits",
    "get_commit", "list_branches", "get_branch",
    # project / search
    "get_project", "list_projects", "search_repositories",
]

_NPX = shutil.which("npx") or "npx"  # absolute path so the subprocess launch is PATH-independent


def make_gitlab_toolset(tool_filter: list[str] | None = READ_TOOLS) -> MCPToolset:
    """Build a GitLab MCP toolset over stdio. tool_filter=None exposes every server tool."""
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_NPX,
                args=["-y", "@zereight/mcp-gitlab"],
                env={
                    **os.environ,  # keep PATH so `npx` resolves in the child
                    "GITLAB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN", ""),
                    "GITLAB_API_URL": GITLAB_API_URL,
                    "GITLAB_READ_ONLY_MODE": "true",
                },
            ),
            timeout=60,
        ),
        tool_filter=tool_filter,
    )


gitlab_toolset = make_gitlab_toolset()

SYSTEM_INSTRUCTION = (
    "You are Sentinel, an autonomous Site Reliability Engineering agent for GitLab. "
    "You investigate issues and read repository code using the provided GitLab tools. "
    "In this phase you operate STRICTLY READ-ONLY: you may read issues, files, and "
    "project metadata, but you must never create, modify, or delete anything. When "
    "asked about an issue, identify the relevant file(s) and explain the problem; do "
    "not attempt to fix it yet."
)

root_agent = LlmAgent(
    model=SENTINEL_MODEL,
    name="sentinel",
    description="AI-powered CI/CD overwatch and SRE agent for GitLab (read-only phase).",
    instruction=SYSTEM_INSTRUCTION,
    tools=[gitlab_toolset],
)
```

> **Imports for `google-adk` 2.1.0:** the class is `MCPToolset` (from `google.adk.tools.mcp_tool.mcp_toolset`), wrapping `StdioConnectionParams` (from `…mcp_session_manager`) holding a `StdioServerParameters` (from the `mcp` package). `tool_filter` accepts a `list[str]` allow-list (a name passes if `tool.name in tool_filter`). Constructing `MCPToolset` is lazy — the `npx` server only spawns when tools are first requested.

---

## Step 4 — Stand up the MCP server and map the Read tools

The toolset launches `npx -y @zereight/mcp-gitlab` for you (first run downloads the package; later runs are cached). Create `backend/scripts/list_tools.py` to confirm the live names:

```python
"""Connect to the GitLab MCP server and print every tool it exposes (read-only mode)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel_agent.agent import READ_TOOLS, make_gitlab_toolset  # noqa: E402


async def main() -> None:
    toolset = make_gitlab_toolset(tool_filter=None)  # unfiltered = everything the server offers
    try:
        tools = await toolset.get_tools()
        names = sorted({t.name for t in tools})
        print(f"Server exposed {len(names)} tools (GITLAB_READ_ONLY_MODE=true):")
        for n in names:
            print("  -", n)
        missing = [t for t in READ_TOOLS if t not in names]
        print("\nREAD_TOOLS missing from server:", missing or "(none — all present)")
    finally:
        await toolset.close()


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python scripts/list_tools.py
```

On this machine the server exposed **58 tools** in read-only mode — and a scan confirmed **none** of them are write/state-changing (`GITLAB_READ_ONLY_MODE=true` filters all the `create_*`/`update_*`/`delete_*`/`*_pipeline` mutators out server-side). Our `tool_filter` then narrows that to the **15 tools** Sentinel actually needs. The line `READ_TOOLS missing from server: (none — all present)` confirms every name in the allow-list is real.

> **Why both layers:** `GITLAB_READ_ONLY_MODE=true` is the safety guard (no write tools exist at all); the `tool_filter` is a focus/clarity guard (the agent sees 15 relevant tools, not 58). In Phase 3 we lift read-only mode and add the specific write tools behind the guardrails.

---

## Step 5 — Initialize the model within the FastAPI app

Update `backend/app/main.py` so the model loads inside the FastAPI process:

```python
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
    """Report the initialized agent's model and read-only tool surface (static metadata)."""
    return {
        "name": root_agent.name,
        "model": root_agent.model,
        "mode": "read-only",
        "read_tools": READ_TOOLS,
    }
```

Verify:

```bash
uvicorn app.main:app --port 8000 &
sleep 2
curl -s localhost:8000/agent/info
kill %1
```

Observed: `{"name":"sentinel","model":"gemini-3.5-flash","mode":"read-only","read_tools":[…15 tools…]}`.

> The full chat/ReAct request endpoint and streaming come in **Phase 4**. `/agent/info` is intentionally static (no GitLab call) so it stays a fast readiness check.

---

## Step 6 — Seed a GitLab test project (read target)

Using the **`api`-scoped PAT** (not the agent), create a private sandbox, commit a deliberately buggy file, and open an issue. From `backend/` with `.env` loaded:

```bash
set -a; . ./.env; set +a
API="$GITLAB_INSTANCE_URL/api/v4"; H="PRIVATE-TOKEN: $GITLAB_PERSONAL_ACCESS_TOKEN"

# 1) project (note the "id" it returns)
curl -s --header "$H" -X POST "$API/projects" \
  --data-urlencode "name=sentinel-test-sandbox" \
  --data "visibility=private&initialize_with_readme=true"

# 2) buggy file (missing colon on the def line) — replace <ID>
printf 'def parse(data)\n    return data.split(",")\n' > /tmp/parser.py
curl -s --header "$H" -X POST "$API/projects/<ID>/repository/files/utils%2Fparser.py" \
  --data-urlencode "branch=main" \
  --data-urlencode "content=$(cat /tmp/parser.py)" \
  --data-urlencode "commit_message=Add parser with syntax error (test fixture)"

# 3) issue #1
curl -s --header "$H" -X POST "$API/projects/<ID>/issues" \
  --data-urlencode "title=Fix syntax error in utils/parser.py" \
  --data-urlencode "description=The function in utils/parser.py is missing a colon on the def line, causing a SyntaxError."
```

On this machine that produced project **`albinvishwas7/sentinel-test-sandbox`** (id `82727935`) with issue **#1**. Note your `path_with_namespace` for the next step.

---

## Step 7 — Smoke-test the read-only round trip

Create `backend/scripts/smoke_read.py`:

```python
"""Phase 2 smoke test — one read-only round trip through the agent."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from sentinel_agent.agent import READ_TOOLS, gitlab_toolset, root_agent  # noqa: E402

PROJECT_PATH = "albinvishwas7/sentinel-test-sandbox"
PROMPT = (
    f"Read issue #1 in the GitLab project '{PROJECT_PATH}' and tell me which file it "
    "mentions. Do not modify anything."
)
APP = "sentinel"


async def main() -> None:
    session_service = InMemorySessionService()
    runner = Runner(app_name=APP, agent=root_agent, session_service=session_service)
    await session_service.create_session(app_name=APP, user_id="smoke", session_id="s1")

    msg = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    tool_calls: list[str] = []
    final_text = ""

    try:
        async for event in runner.run_async(user_id="smoke", session_id="s1", new_message=msg):
            if event.content and event.content.parts:
                for p in event.content.parts:
                    fc = getattr(p, "function_call", None)
                    if fc:
                        tool_calls.append(fc.name)
                        print(f"[tool call]   {fc.name}  args={dict(fc.args or {})}")
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(p.text or "" for p in event.content.parts)
    finally:
        await gitlab_toolset.close()

    print("\n=== FINAL ANSWER ===")
    print(final_text.strip())

    read_used = [t for t in tool_calls if t in READ_TOOLS]
    write_used = [t for t in tool_calls if t not in READ_TOOLS]
    print("\n=== RESULT ===")
    print("read tool used  :", bool(read_used), read_used)
    print("write tool used :", bool(write_used), write_used or "(none — good)")
    print("named the file  :", "parser.py" in final_text)
    print("PASS            :", bool(read_used) and "parser.py" in final_text and not write_used)


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python scripts/smoke_read.py
```

**Observed result on this machine (PASS):**

```
[tool call]   get_project  args={'project_id': 'albinvishwas7/sentinel-test-sandbox'}
[tool call]   get_issue     args={'project_id': '82727935', 'issue_iid': '1'}
=== FINAL ANSWER ===
Issue #1 … mentions the file **`utils/parser.py`** … missing a colon on the def line, causing a SyntaxError.
=== RESULT ===
read tool used  : True ['get_project', 'get_issue']
write tool used : False (none — good)
named the file  : True
PASS            : True
```

The agent took the prompt, resolved the project, called the **`get_issue`** read tool, and returned the correct file — a complete `prompt → tool call → response` loop with **no write tool invoked**. ✅

---

## Phase 2 completion checklist

- [x] `google-adk` (and `mcp`) installed in the backend
- [x] Vertex AI / Google Cloud credentials configured for local development (done during auth setup)
- [x] Gemini 3.5 Flash model initialized within the FastAPI app (`/agent/info`, `global` endpoint)
- [x] GitLab MCP server stood up locally (`@zereight/mcp-gitlab` via `npx`, read-only)
- [x] ADK orchestrator connected to the GitLab MCP server (`MCPToolset` → `root_agent`)
- [x] GitLab MCP "Read" tools mapped (15-tool allow-list; confirmed against the live 58-tool list)
- [x] Read-only round trip smoke-tested (prompt → `get_issue` → response; no writes)

> **Up next (Phase 3):** map the GitLab **Write** tools (branch / commit / open MR), then add the guardrails — no pushes to `main`/`master`, `<UNTRUSTED_ISSUE_DATA>` prompt-injection defense, and `max_iterations = 5`. That's when `GITLAB_READ_ONLY_MODE` is lifted and the specific write tools are added — strictly behind the guardrails.

"""Deterministic Test 2 — MCP Tool Isolation (no AI).

Bypasses Gemini and ADK entirely: connects straight to the @zereight/mcp-gitlab
server over stdio and hand-invokes a mapped read tool (get_issue, issue_iid=1).
Proves the MCP bridge fetches real data from GitLab and returns it to the backend.

  .venv/bin/python scripts/phase5/det_2_mcp_isolation.py [issue_iid]

Requires a valid GITLAB_PERSONAL_ACCESS_TOKEN and the seeded sandbox (run
scripts/seed_test_cases.py first). Read-only — makes no changes.
"""

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import PROJECT_PATH, check, info, section, verdict  # noqa: E402

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from sentinel_agent.gitlab_health import GITLAB_API_URL  # noqa: E402

ISSUE_IID = int(sys.argv[1]) if len(sys.argv) > 1 else 1


def _server_params() -> StdioServerParameters:
    npx = shutil.which("npx") or "npx"
    return StdioServerParameters(
        command=npx,
        args=["-y", "@zereight/mcp-gitlab"],
        env={
            **os.environ,
            "GITLAB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN", ""),
            "GITLAB_API_URL": GITLAB_API_URL,
            "GITLAB_READ_ONLY_MODE": "true",  # isolation test only reads
        },
    )


def _extract_text(result) -> str:
    """Flatten an MCP CallToolResult's content blocks into a single string."""
    parts = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


async def main() -> int:
    section("Deterministic 2 — MCP Tool Isolation (manual get_issue, no AI)")
    info(f"project={PROJECT_PATH}  issue_iid={ISSUE_IID}  api={GITLAB_API_URL}")

    if not os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN"):
        check("GITLAB_PERSONAL_ACCESS_TOKEN configured", False, "set it in backend/.env")
        return verdict("det_2_mcp_isolation", False) and 1

    ok = True
    try:
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = (await session.list_tools()).tools
                names = {t.name for t in tools}
                ok &= check("MCP server handshake + tool listing", bool(names), f"{len(names)} tools")
                ok &= check("read tool 'get_issue' exposed", "get_issue" in names)

                # Hand-invoke the tool — no model in the loop.
                result = await session.call_tool(
                    "get_issue", {"project_id": PROJECT_PATH, "issue_iid": ISSUE_IID}
                )
                is_error = bool(getattr(result, "isError", False))
                text = _extract_text(result)
                ok &= check("get_issue call returned without error", not is_error, text[:120] if is_error else "")

                # Confirm the payload is real GitLab issue data.
                parsed = None
                try:
                    parsed = json.loads(text)
                except Exception:
                    pass
                has_fields = isinstance(parsed, dict) and any(
                    k in parsed for k in ("title", "iid", "description", "web_url")
                )
                ok &= check("payload looks like a GitLab issue", has_fields)
                if has_fields:
                    info(f"title : {parsed.get('title')!r}")
                    info(f"iid   : {parsed.get('iid')}   state: {parsed.get('state')}")
                    info(f"url   : {parsed.get('web_url')}")
    except Exception as exc:  # noqa: BLE001
        check("MCP round trip completed", False, f"{type(exc).__name__}: {exc}")
        ok = False

    return 0 if verdict("det_2_mcp_isolation", ok) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

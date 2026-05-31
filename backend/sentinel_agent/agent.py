"""Sentinel ADK agent — Phase 2 (read-only GitLab bridge).

Defines the root LlmAgent (Gemini 3.5 Flash on Vertex AI) and connects it to the
GitLab MCP server (`@zereight/mcp-gitlab`) over stdio. This phase is strictly
read-only: the server runs with GITLAB_READ_ONLY_MODE=true and the agent only
sees the read tools in READ_TOOLS. Write tools / MR creation arrive in Phase 3.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from mcp import StdioServerParameters

# Load backend/.env (this module lives in backend/sentinel_agent/).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Model verified live against Vertex AI on the 'global' endpoint (see scripts/verify_model.py).
# Override via SENTINEL_MODEL in .env if the ID ever changes.
SENTINEL_MODEL = os.environ.get("SENTINEL_MODEL", "gemini-3.5-flash")

_GITLAB_INSTANCE = os.environ.get("GITLAB_INSTANCE_URL", "https://gitlab.com").rstrip("/")
GITLAB_API_URL = f"{_GITLAB_INSTANCE}/api/v4"

# Curated allow-list of GitLab read tools the agent may see this phase. With
# GITLAB_READ_ONLY_MODE=true the server exposes only read tools (verified: no
# create/update/delete/cancel/retry tools appear), so this tool_filter is a second
# layer that also narrows the surface to the handful Sentinel actually needs.
# Every name below is confirmed against the server's live tool list (scripts/list_tools.py).
READ_TOOLS = [
    # issues
    "get_issue",
    "list_issues",
    "my_issues",
    # merge requests
    "get_merge_request",
    "list_merge_requests",
    "get_merge_request_diffs",
    # code / repository
    "get_file_contents",
    "get_repository_tree",
    "list_commits",
    "get_commit",
    "list_branches",
    "get_branch",
    # project / search
    "get_project",
    "list_projects",
    "search_repositories",
]

# Resolve npx to an absolute path so the subprocess launch never depends on the
# child's PATH being set up correctly.
_NPX = shutil.which("npx") or "npx"


def make_gitlab_toolset(tool_filter: list[str] | None = READ_TOOLS) -> MCPToolset:
    """Build a GitLab MCP toolset over stdio. Pass tool_filter=None to expose every
    tool the server offers (used by scripts/list_tools.py for discovery)."""
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_NPX,
                args=["-y", "@zereight/mcp-gitlab"],
                env={
                    **os.environ,  # keep PATH etc. so `npx` resolves inside the child
                    "GITLAB_PERSONAL_ACCESS_TOKEN": os.environ.get(
                        "GITLAB_PERSONAL_ACCESS_TOKEN", ""
                    ),
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

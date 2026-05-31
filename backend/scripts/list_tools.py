"""Discovery helper: connect to the GitLab MCP server and print every tool it
exposes (in read-only mode), then report which READ_TOOLS are missing.

Run from the backend/ dir:  .venv/bin/python scripts/list_tools.py
"""

import asyncio
import sys
from pathlib import Path

# Make `sentinel_agent` importable no matter the working directory (running a script
# puts scripts/ on sys.path, not backend/).
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

"""Capped agent runner with abort handling (Risk 2 — infinite reasoning loops).

`run_agent` drives the ADK ReAct loop under a hard `max_llm_calls` ceiling. When
the agent exceeds it, ADK raises LlmCallsLimitExceededError; we catch it and
return the mandated abort message instead of looping forever / burning quota.
"""

from __future__ import annotations

from google.adk.agents.invocation_context import LlmCallsLimitExceededError
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import MAX_ITERATIONS, root_agent

APP_NAME = "sentinel"
ABORT_MESSAGE = "Task aborted: Maximum reasoning steps reached."


async def run_agent(
    prompt: str,
    *,
    user_id: str = "api",
    session_id: str = "default",
    max_iterations: int = MAX_ITERATIONS,
) -> dict[str, object]:
    """Run one request through Sentinel under the iteration cap.

    Returns {"status": "ok", "message": <final answer>, "tool_calls": [...]} or
    {"status": "aborted", "message": ABORT_MESSAGE, "tool_calls": [...]} if the
    max_llm_calls ceiling is hit.
    """
    session_service = InMemorySessionService()
    runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    run_config = RunConfig(max_llm_calls=max_iterations)

    tool_calls: list[str] = []
    final_text = ""
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
            run_config=run_config,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc:
                        tool_calls.append(fc.name)
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(p.text or "" for p in event.content.parts)
    except LlmCallsLimitExceededError:
        return {"status": "aborted", "message": ABORT_MESSAGE, "tool_calls": tool_calls}

    return {"status": "ok", "message": final_text.strip(), "tool_calls": tool_calls}

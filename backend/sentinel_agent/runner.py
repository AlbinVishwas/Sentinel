"""Capped agent runner with abort handling (Risk 2 — infinite reasoning loops).

`run_agent` drives the ADK ReAct loop under a hard `max_llm_calls` ceiling and
returns the final result. `stream_agent` drives the same loop but yields structured
events as they happen (reasoning, tool calls, tool results, final answer), so the
frontend can visualize the agent's intermediate steps in real time (Quadrant D).

When the agent exceeds the ceiling ADK raises LlmCallsLimitExceededError; we catch
it and surface the mandated abort message instead of looping forever / burning quota.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from google.adk.agents.invocation_context import LlmCallsLimitExceededError
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import MAX_ITERATIONS, make_agent
from .gitlab_health import AUTH_ERROR_MARKERS

APP_NAME = "sentinel"
ABORT_MESSAGE = "Task aborted: Maximum reasoning steps reached."
AUTH_ERROR_MESSAGE = (
    "GitLab authentication failed: your GitLab connection is missing, invalid, or "
    "expired. Please sign out and reconnect GitLab."
)


def _is_auth_error(exc: BaseException) -> bool:
    """True if an exception looks like a GitLab 401/auth failure.

    MCP tool failures bubble up as opaque exceptions; we classify them by string so
    a bad token surfaces as a clear auth error instead of a generic 'Agent error'.
    """
    text = f"{type(exc).__name__} {exc}".lower()
    return any(marker in text for marker in AUTH_ERROR_MARKERS)


async def stream_agent(
    prompt: str,
    *,
    gitlab_token: str,
    user_id: str,
    session_id: str = "default",
    max_iterations: int = MAX_ITERATIONS,
    gitlab_project: str | None = None,
) -> AsyncIterator[dict[str, object]]:
    """Drive one request through Sentinel, yielding events as they occur.

    `gitlab_token` is the requesting user's GitLab OAuth access token (from
    `store.get_valid_access_token`); `user_id` is their GitLab user id, used to
    scope the ADK session. Event shapes (each a plain dict, ready to JSON-encode
    for SSE):
      {"type": "reasoning", "text": str}      - the model's intermediate prose
      {"type": "tool_call",  "name": str, "args": dict}
      {"type": "tool_result","name": str}     - a tool returned (result omitted; may be large/untrusted)
      {"type": "final",      "text": str}     - the final answer
      {"type": "aborted",    "message": str}  - hit the iteration ceiling (Risk 2)
      {"type": "error",      "message": str}  - unexpected failure
    """
    agent = make_agent(gitlab_token, gitlab_project)
    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=InMemorySessionService(),
    )
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    run_config = RunConfig(max_llm_calls=max_iterations)

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
            run_config=run_config,
        ):
            final = event.is_final_response()
            if not (event.content and event.content.parts):
                continue
            for part in event.content.parts:
                fc = getattr(part, "function_call", None)
                fr = getattr(part, "function_response", None)
                text = getattr(part, "text", None)
                if fc:
                    yield {"type": "tool_call", "name": fc.name, "args": dict(fc.args or {})}
                elif fr:
                    yield {"type": "tool_result", "name": fr.name}
                elif text:
                    yield {"type": "final" if final else "reasoning", "text": text}
    except LlmCallsLimitExceededError:
        yield {"type": "aborted", "message": ABORT_MESSAGE}
    except Exception as exc:  # noqa: BLE001 - surface a safe message, never crash the stream
        if _is_auth_error(exc):
            yield {"type": "error", "code": "gitlab_auth_failed", "message": AUTH_ERROR_MESSAGE}
        else:
            yield {"type": "error", "message": f"Agent error: {type(exc).__name__}"}


async def run_agent(
    prompt: str,
    *,
    gitlab_token: str,
    user_id: str,
    session_id: str = "default",
    max_iterations: int = MAX_ITERATIONS,
    gitlab_project: str | None = None,
) -> dict[str, object]:
    """Run one request through Sentinel under the iteration cap (non-streaming).

    Returns {"status": "ok", "message": <final answer>, "tool_calls": [...]} or
    {"status": "aborted", "message": ABORT_MESSAGE, "tool_calls": [...]} if the
    max_llm_calls ceiling is hit. Implemented on top of stream_agent so both paths
    share one code path.
    """
    tool_calls: list[str] = []
    final_text = ""
    async for ev in stream_agent(
        prompt,
        gitlab_token=gitlab_token,
        user_id=user_id,
        session_id=session_id,
        max_iterations=max_iterations,
        gitlab_project=gitlab_project,
    ):
        kind = ev.get("type")
        if kind == "tool_call":
            tool_calls.append(str(ev.get("name", "")))
        elif kind == "final":
            final_text = str(ev.get("text", ""))
        elif kind == "aborted":
            return {"status": "aborted", "message": ABORT_MESSAGE, "tool_calls": tool_calls}
        elif kind == "error":
            return {"status": "error", "message": str(ev.get("message", "")), "tool_calls": tool_calls}
    return {"status": "ok", "message": final_text.strip(), "tool_calls": tool_calls}

"""Deterministic Test 1 — Secret Manager / 401 graceful failure (AI-free).

Forces an auth failure with a fake PAT and proves the backend catches the 401 and
fails *gracefully* (a clear, structured verdict) rather than crashing. Also confirms
the runner classifies auth-shaped exceptions as gitlab_auth_failed.

  .venv/bin/python scripts/phase5/det_1_secret_manager.py

No Gemini and no agent run required. The one live call is a single GET /user against
GitLab with a bogus token — cheap and safe. If GitLab is unreachable the test still
passes its core assertion (the call returns a verdict, never an exception).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import check, section, verdict  # noqa: E402

from sentinel_agent.gitlab_health import check_gitlab_auth  # noqa: E402
from sentinel_agent.runner import AUTH_ERROR_MESSAGE, _is_auth_error  # noqa: E402


async def test_fake_token_caught() -> bool:
    """A fake token must produce a graceful gitlab_auth_failed verdict, not an exception."""
    ok = True
    try:
        result = await check_gitlab_auth("glpat-THIS-IS-A-FAKE-TOKEN-0000000000")
    except Exception as exc:  # noqa: BLE001
        return check("fake token handled without crashing", False, f"raised {type(exc).__name__}")

    ok &= check("call returned a verdict (no crash)", isinstance(result, dict))
    # Either the token is rejected (401/403) or GitLab is unreachable — both are graceful.
    graceful = result.get("status") in {"gitlab_auth_failed", "gitlab_unreachable"}
    ok &= check("fake token NOT authenticated", result.get("authenticated") is False, str(result.get("status")))
    ok &= check("verdict is a graceful failure status", graceful, str(result.get("status")))
    ok &= check("human-readable message present", bool(result.get("message")), str(result.get("message", "")))
    return ok


async def test_empty_token_caught() -> bool:
    result = await check_gitlab_auth("")
    return check(
        "empty token -> gitlab_auth_failed",
        result.get("status") == "gitlab_auth_failed" and result.get("authenticated") is False,
        str(result.get("message", "")),
    )


def test_runner_classifies_auth_errors() -> bool:
    """The runner's mid-run classifier flags 401-shaped exceptions as auth failures."""
    ok = True
    ok &= check("'401 Unauthorized' classified as auth", _is_auth_error(Exception("401 Unauthorized")))
    ok &= check("'invalid_token' classified as auth", _is_auth_error(RuntimeError("invalid_token")))
    ok &= check("unrelated error NOT misclassified", not _is_auth_error(ValueError("file not found")))
    ok &= check("auth message is clear", "authentication failed" in AUTH_ERROR_MESSAGE.lower())
    return ok


async def test_real_token_if_present() -> bool:
    """Sanity: the *configured* token (if real) should authenticate. Skipped if absent."""
    import os

    if not os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN"):
        print("   [SKIP] no GITLAB_PERSONAL_ACCESS_TOKEN configured")
        return True
    result = await check_gitlab_auth()
    if result.get("status") == "gitlab_unreachable":
        print(f"   [SKIP] GitLab unreachable: {result.get('message')}")
        return True
    return check(
        "configured token authenticates",
        result.get("authenticated") is True,
        f"user={result.get('username', '?')}",
    )


async def main() -> int:
    section("Deterministic 1 — Secret Manager / 401 graceful failure")
    results = [
        await test_fake_token_caught(),
        await test_empty_token_caught(),
        test_runner_classifies_auth_errors(),
        await test_real_token_if_present(),
    ]
    ok = all(results)
    verdict("det_1_secret_manager", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

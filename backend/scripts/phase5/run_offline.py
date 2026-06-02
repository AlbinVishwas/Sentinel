"""Run the deterministic (no-Gemini) Phase 5 suite end to end.

These are the tests that don't burn Vertex AI quota — the rock-solid foundation:
  det_1_secret_manager  (single bogus-token GET)
  det_2_mcp_isolation   (read-only MCP round trip)
  det_3_streaming       (mock SSE; needs the backend running)

  .venv/bin/python scripts/phase5/run_offline.py

The agentic evals, red-team, and golden-path tests cost Gemini calls and are run
individually — see scripts/phase5/README.md.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = ["det_1_secret_manager.py", "det_2_mcp_isolation.py", "det_3_streaming.py"]


def main() -> int:
    results: dict[str, int] = {}
    for name in SCRIPTS:
        print(f"\n{'─' * 70}\n▶ {name}\n{'─' * 70}")
        proc = subprocess.run([sys.executable, str(HERE / name)])
        results[name] = proc.returncode

    print(f"\n{'═' * 70}\nPHASE 5 — DETERMINISTIC SUITE SUMMARY\n{'═' * 70}")
    for name, code in results.items():
        print(f"   {'PASS' if code == 0 else 'FAIL'}  {name}")
    failed = [n for n, c in results.items() if c != 0]
    print(f"\n{'ALL DETERMINISTIC TESTS PASS' if not failed else 'FAILURES: ' + ', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

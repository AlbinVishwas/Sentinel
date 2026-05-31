"""Verify the configured Gemini model resolves on Vertex AI with the current ADC.

Run from the backend/ dir:  .venv/bin/python scripts/verify_model.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from google import genai  # noqa: E402

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

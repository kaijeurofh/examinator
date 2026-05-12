"""Command-line entry point.

Usage:
    uv run examinator-serve [--host 0.0.0.0] [--port 8000]

Starts the FastAPI web server that backs the Examinator web UI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv


def _load_project_dotenv() -> None:
    """Load `.env` from the current working directory only.

    Anchored to ``Path.cwd()`` so running the CLI from a child directory of
    an unrelated project cannot pull that project's secrets into our process.
    """
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


def main() -> int:
    _load_project_dotenv()

    parser = argparse.ArgumentParser(prog="examinator-serve")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "examinator.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        # Single worker is intentional — JobStore is in-memory per process.
        workers=1,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Command-line entry point.

Usage:
    uv run llm-uv-template "the windy city in the US of A"

Reads the prompt from argv (joined) and prints the agent's structured
response as JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from llm_uv_template.agent import build_agent


def _load_project_dotenv() -> None:
    """Load `.env` from the current working directory only.

    Plain ``dotenv.load_dotenv()`` walks up parent directories looking for a
    `.env`, which means running the CLI from a child directory of an
    unrelated project can pull that project's secrets into our process.
    Anchoring to ``Path.cwd()`` closes that footgun and behaves identically
    whether the package is installed editably (``uv sync``) or as a wheel
    from PyPI — a previous ``Path(__file__).parent.parent.parent`` resolved
    to ``site-packages/..`` in the wheel case and silently loaded nothing.
    """
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


def main() -> int:
    _load_project_dotenv()

    args = sys.argv[1:]
    if not args:
        print('Usage: llm-uv-template "your prompt"', file=sys.stderr)
        return 2

    prompt = " ".join(args)
    agent = build_agent()
    result = agent.run_sync(prompt)
    print(json.dumps(result.output.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

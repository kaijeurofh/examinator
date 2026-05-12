"""Tests for the Cursor hook scripts in `.cursor/hooks/`.

The hooks are guardrails that run *before* shell commands and prompt
submissions. They must keep behaving correctly across refactors of the
regex tables — exactly the kind of code where a silent regression is
expensive (false negative = secret leaks; false positive = workflow
breaks).

We invoke each hook as a subprocess with stdin JSON and parse its
stdout JSON, mirroring how Cursor itself calls them. This avoids any
coupling to the script's internal helpers.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GUARD_ENV = _REPO_ROOT / ".cursor" / "hooks" / "guard-env.py"
_SCAN_PROMPT = _REPO_ROOT / ".cursor" / "hooks" / "scan-prompt.py"


def _run_hook(script: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute `script` with `payload` on stdin, return its decoded JSON.

    Use the running interpreter explicitly so the test does not depend on
    the script's executable bit or on `#!/usr/bin/env python3` resolving
    correctly on the runner.
    """
    completed = subprocess.run(  # noqa: S603 - hardcoded path under repo root
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    assert completed.stdout, f"{script.name} produced no stdout"
    decoded: dict[str, Any] = json.loads(completed.stdout)
    return decoded


@pytest.mark.parametrize(
    ("command", "expected_permission"),
    [
        # Benign commands: always allow.
        ("echo hello", "allow"),
        ("uv run pytest -q", "allow"),
        ("cat README.md", "allow"),
        ("git status", "allow"),
        # Schema file is explicitly allowed.
        ("cat .env.example", "allow"),
        ("git diff .env.example", "allow"),
        ("cp .env.example /tmp/", "allow"),
        # Real .env access via any verb must be denied.
        ("cat .env", "deny"),
        ("echo OPENAI_API_KEY=stolen > .env", "deny"),
        ("tee .env", "deny"),
        ("grep KEY .env", "deny"),
        ("vim .env", "deny"),
        ("cp .env /tmp/leak", "deny"),
        # Variant .env files.
        ("echo X >> .env.local", "deny"),
        ("rm .env.production", "deny"),
        ("cat ./.env", "deny"),
        ("cat sub/.env.staging", "deny"),
        # Edge: empty / whitespace command.
        ("", "allow"),
        ("   ", "allow"),
        # Edge: lookalike that is NOT .env (must not false-positive).
        ("cat notes-about-the.environment", "allow"),
        ("echo dotenv-loader.py", "allow"),
    ],
)
def test_guard_env_decisions(command: str, expected_permission: str) -> None:
    result = _run_hook(_GUARD_ENV, {"command": command})
    assert result["permission"] == expected_permission, (
        f"command={command!r} expected {expected_permission}, got {result}"
    )


def test_guard_env_handles_malformed_shell_quoting() -> None:
    # shlex raises ValueError on unbalanced quotes; the hook must fall back
    # to whitespace splitting rather than crashing under failClosed=true.
    result = _run_hook(_GUARD_ENV, {"command": "echo 'unterminated > .env"})
    assert result["permission"] == "deny"


def test_guard_env_handles_garbage_stdin() -> None:
    # Bypass json.dumps by writing raw bytes; the script must not crash.
    completed = subprocess.run(  # noqa: S603 - hardcoded path under repo root
        [sys.executable, str(_GUARD_ENV)],
        input="this is not json",
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    payload = json.loads(completed.stdout)
    # On unparseable input we bias to allow (the comment in guard-env.py
    # explains why this is safer than wedging the agent under failClosed).
    assert payload["permission"] == "allow"


@pytest.mark.parametrize(
    ("prompt", "expected_permission"),
    [
        # Benign: no secret-shaped strings.
        ("How do I rename a function?", "allow"),
        ("Explain `uv lock --check`.", "allow"),
        # Known placeholders must be ignored.
        ("We use sk-replace-me as a placeholder.", "allow"),
        ("sk-ant-replace-me", "allow"),
        ("test-key-not-real", "allow"),
        # High-confidence secret patterns must ask for confirmation.
        ("Here is my key: sk-proj-abcdefghij1234567890ZZZZ", "ask"),
        ("AKIAIOSFODNN7EXAMPLE", "ask"),
        ("ghp_abcdefghijklmnopqrstuvwxyz0123456789", "ask"),
        ("Token: xoxb-1234567890-abcdefghijklmn", "ask"),
        ("-----BEGIN RSA PRIVATE KEY-----", "ask"),
    ],
)
def test_scan_prompt_decisions(prompt: str, expected_permission: str) -> None:
    result = _run_hook(_SCAN_PROMPT, {"prompt": prompt})
    assert result["permission"] == expected_permission, (
        f"prompt={prompt!r} expected {expected_permission}, got {result}"
    )


def test_scan_prompt_reports_what_it_matched() -> None:
    result = _run_hook(_SCAN_PROMPT, {"prompt": "deploy with AKIAIOSFODNN7EXAMPLE please"})
    assert result["permission"] == "ask"
    assert "AWS access key id" in result["user_message"]


def test_scan_prompt_handles_garbage_stdin() -> None:
    completed = subprocess.run(  # noqa: S603 - hardcoded path under repo root
        [sys.executable, str(_SCAN_PROMPT)],
        input="not json at all",
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["permission"] == "allow"

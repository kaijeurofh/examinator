#!/usr/bin/env python3
"""beforeSubmitPrompt hook: warn when a prompt looks like it contains a secret.

Why this exists
---------------
The most common way real API keys end up at a model provider is *not* via
a committed file — it is via a developer pasting `export OPENAI_API_KEY=...`
straight into the chat to "give the agent context". Once that lands in the
provider's logs, you have to rotate the key.

This hook scans the prompt for a handful of high-confidence secret
patterns (OpenAI/Anthropic-style, generic SK, AWS, GitHub PATs, Slack
tokens, JWTs, PEM headers) and asks the user to confirm before sending.

It deliberately does NOT block (``failClosed: false`` in ``hooks.json``)
because false positives on prompts would be infuriating; the goal is a
human-in-the-loop checkpoint, not a tripwire.

Stdlib-only on purpose; see guard-env.py.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

# Patterns are intentionally narrower than gitleaks' full ruleset — we want
# very few false positives at the prompt-submit interaction point.
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Anthropic-style API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub personal access token", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    (
        "JWT",
        re.compile(r"\beyJ[A-Za-z0-9_=-]{8,}\.[A-Za-z0-9_=-]{8,}\.[A-Za-z0-9_.+/=-]+\b"),
    ),
    ("PEM private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

# Obvious placeholder values used in this repo's docs/examples — never warn
# on these even though they share the `sk-` prefix.
_PLACEHOLDERS: frozenset[str] = frozenset(
    {
        "sk-replace-me",
        "sk-ant-replace-me",
        "test-key-not-real",
    }
)


def _findings(text: str) -> list[str]:
    hits: list[str] = []
    for label, pattern in _SECRET_PATTERNS:
        for match in pattern.findall(text):
            token = match if isinstance(match, str) else match[0]
            if token in _PLACEHOLDERS:
                continue
            hits.append(label)
            break
    return hits


def _decide(prompt: str) -> dict[str, Any]:
    hits = _findings(prompt)
    if not hits:
        return {"permission": "allow"}

    joined = ", ".join(sorted(set(hits)))
    return {
        "permission": "ask",
        "user_message": (
            "Possible secret detected in this prompt "
            f"({joined}). Confirm you want to send it to the model — if "
            "this is a real key, cancel, rotate it, and reference it by "
            "name only."
        ),
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        json.dump({"permission": "allow"}, sys.stdout)
        return 0

    prompt = str(payload.get("prompt") or payload.get("user_prompt") or "")
    json.dump(_decide(prompt), sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

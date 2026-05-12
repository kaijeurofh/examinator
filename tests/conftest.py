"""Shared pytest fixtures.

Anything that touches the LLM provider must be mocked here — unit tests
must never make real network calls. See `tests/test_agent.py` for the
canonical mocking pattern.
"""

from __future__ import annotations

import pytest

# Every env var pydantic-ai (and its underlying provider SDKs) might read to
# instantiate a real client. We overwrite each one with an obvious fake before
# every test so a misconfigured test cannot reach a live provider with a real
# key sitting in the developer's environment.
_PROVIDER_ENV_VARS: tuple[str, ...] = (
    # OpenAI + Azure
    "OPENAI_API_KEY",
    "OPENAI_ORG_ID",
    "OPENAI_PROJECT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    # Anthropic
    "ANTHROPIC_API_KEY",
    # Google / Gemini
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_GENAI_API_KEY",
    # Mistral
    "MISTRAL_API_KEY",
    # Cohere
    "COHERE_API_KEY",
    "CO_API_KEY",
    # Groq
    "GROQ_API_KEY",
    # DeepSeek
    "DEEPSEEK_API_KEY",
    # Together / Fireworks / Perplexity / OpenRouter
    "TOGETHER_API_KEY",
    "FIREWORKS_API_KEY",
    "PERPLEXITY_API_KEY",
    "OPENROUTER_API_KEY",
    # AWS (Bedrock providers may pick these up)
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
)


@pytest.fixture(autouse=True)
def _fake_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace any real provider keys with obvious fakes.

    pydantic-ai validates that *some* key is present when it instantiates a
    provider client, even if the test will swap the model with
    :class:`pydantic_ai.models.test.TestModel` before any real call. Setting
    placeholders here guarantees no real key can ever leak from the developer
    environment into a test run.
    """
    for var in _PROVIDER_ENV_VARS:
        monkeypatch.setenv(var, "test-key-not-real")

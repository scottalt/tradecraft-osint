"""Tests for tradecraft.providers.openai_compat."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tradecraft.providers.openai_compat import OpenAICompatProvider


def test_metadata() -> None:
    assert OpenAICompatProvider.name == "openai-compat"
    assert OpenAICompatProvider.requires_api_key is True
    # No default model — user must supply.
    assert OpenAICompatProvider.default_model == ""


def test_from_env_requires_base_url_and_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_COMPAT_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_COMPAT_KEY", raising=False)
    monkeypatch.delenv("TRADECRAFT_AI_OPENAI_COMPAT_MODEL", raising=False)
    assert OpenAICompatProvider.from_env() is None


def test_from_env_returns_when_all_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_KEY", "sk-test")
    monkeypatch.setenv("TRADECRAFT_AI_OPENAI_COMPAT_MODEL", "test-model")
    p = OpenAICompatProvider.from_env()
    assert p is not None
    assert p.model == "test-model"


async def test_generate_calls_chat_completions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_KEY", "sk-test")
    monkeypatch.setenv("TRADECRAFT_AI_OPENAI_COMPAT_MODEL", "test-model")
    p = OpenAICompatProvider.from_env()
    assert p is not None

    fake_choice = MagicMock()
    fake_choice.message.content = "compat answer"
    fake_response = MagicMock(choices=[fake_choice])
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)
    p._client = fake_client

    result = await p.generate("s", "u", 100)
    assert result == "compat answer"

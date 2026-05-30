"""Tests for tradecraft.providers.openai."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tradecraft.providers.openai import OpenAIProvider


def test_metadata() -> None:
    assert OpenAIProvider.name == "openai"
    assert OpenAIProvider.default_model == "gpt-4o"
    assert OpenAIProvider.requires_api_key is True


def test_from_env_returns_none_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert OpenAIProvider.from_env() is None


def test_from_env_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    p = OpenAIProvider.from_env()
    assert p is not None
    assert p.model == OpenAIProvider.default_model


async def test_generate_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    p = OpenAIProvider.from_env()
    assert p is not None

    fake_choice = MagicMock()
    fake_choice.message.content = "ai answer"
    fake_response = MagicMock(choices=[fake_choice])
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)
    p._client = fake_client

    result = await p.generate("sys", "user", 500)
    assert result == "ai answer"

    call = fake_client.chat.completions.create.call_args
    assert call.kwargs["model"] == p.model
    assert call.kwargs["max_tokens"] == 500
    msgs = call.kwargs["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "sys"
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "user"

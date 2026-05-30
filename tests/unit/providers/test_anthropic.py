"""Tests for tradecraft.providers.anthropic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tradecraft.providers.anthropic import AnthropicProvider


def test_metadata() -> None:
    assert AnthropicProvider.name == "anthropic"
    assert AnthropicProvider.default_model == "claude-sonnet-4-6"
    assert AnthropicProvider.requires_api_key is True


def test_from_env_returns_none_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert AnthropicProvider.from_env() is None


def test_from_env_returns_provider_when_key_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    p = AnthropicProvider.from_env()
    assert p is not None
    assert p.model == AnthropicProvider.default_model


def test_from_env_honors_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    p = AnthropicProvider.from_env(model="claude-opus-4-7")
    assert p is not None
    assert p.model == "claude-opus-4-7"


async def test_generate_calls_sdk_with_cache_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    p = AnthropicProvider.from_env()
    assert p is not None

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="generated answer")]
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_response)
    p._client = fake_client  # test override

    result = await p.generate("sys-prompt", "user-prompt", 500)
    assert result == "generated answer"

    call = fake_client.messages.create.call_args
    assert call.kwargs["model"] == p.model
    assert call.kwargs["max_tokens"] == 500
    assert call.kwargs["system"] == "sys-prompt"
    # cache_control should be on the user message
    user_msg = call.kwargs["messages"][0]
    assert user_msg["role"] == "user"
    assert isinstance(user_msg["content"], list)
    assert user_msg["content"][0]["cache_control"] == {"type": "ephemeral"}

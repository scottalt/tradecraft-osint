"""Tests for tradecraft.providers.ollama."""

from __future__ import annotations

import httpx
import pytest
import respx

from tradecraft.providers.ollama import OllamaProvider


def test_metadata() -> None:
    assert OllamaProvider.name == "ollama"
    assert OllamaProvider.default_model == "llama3.1:8b"
    assert OllamaProvider.requires_api_key is False


def test_from_env_uses_default_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    p = OllamaProvider.from_env()
    assert p is not None
    assert p.host == "http://localhost:11434"


def test_from_env_honors_host_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://gpu.lan:11434")
    p = OllamaProvider.from_env()
    assert p is not None
    assert p.host == "http://gpu.lan:11434"


@respx.mock
async def test_generate_uses_chat_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    route = respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "ai answer"}},
        )
    )
    p = OllamaProvider.from_env()
    assert p is not None
    result = await p.generate("sys", "user", 500)
    assert result == "ai answer"
    body = route.calls[0].request.read().decode()
    assert "llama3.1:8b" in body
    assert "sys" in body
    assert "user" in body

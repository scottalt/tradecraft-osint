"""Ollama adapter (raw httpx, no SDK)."""

from __future__ import annotations

import os
from typing import ClassVar

import httpx

from tradecraft.providers.base import _register

_DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider:
    name: ClassVar[str] = "ollama"
    default_model: ClassVar[str] = "llama3.1:8b"
    requires_api_key: ClassVar[bool] = False

    def __init__(self, host: str, model: str | None = None) -> None:
        self.host = host.rstrip("/")
        self.model = model or self.default_model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        response = await self._client.post(f"{self.host}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        message = data.get("message") or {}
        content = message.get("content")
        return str(content) if content else ""

    @classmethod
    def from_env(cls, model: str | None = None) -> OllamaProvider | None:
        host = os.environ.get("OLLAMA_HOST", _DEFAULT_HOST)
        return cls(host=host, model=model)


_register(OllamaProvider.name, OllamaProvider)

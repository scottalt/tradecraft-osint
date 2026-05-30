"""OpenAI-compatible adapter (OpenRouter, Groq, LM Studio, vLLM, ...)."""

from __future__ import annotations

import os
from typing import ClassVar

from tradecraft.providers.base import _register


class OpenAICompatProvider:
    name: ClassVar[str] = "openai-compat"
    default_model: ClassVar[str] = ""
    requires_api_key: ClassVar[bool] = True

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        import openai  # noqa: PLC0415 — lazy SDK import

        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str:
        response = await self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        choice = response.choices[0] if response.choices else None
        if choice is None or choice.message.content is None:
            return ""
        return str(choice.message.content)

    @classmethod
    def from_env(cls, model: str | None = None) -> OpenAICompatProvider | None:
        base_url = os.environ.get("OPENAI_COMPAT_BASE_URL")
        api_key = os.environ.get("OPENAI_COMPAT_KEY")
        resolved_model = model or os.environ.get("TRADECRAFT_AI_OPENAI_COMPAT_MODEL")
        if not (base_url and api_key and resolved_model):
            return None
        return cls(base_url=base_url, api_key=api_key, model=resolved_model)


_register(OpenAICompatProvider.name, OpenAICompatProvider)

"""OpenAI adapter."""

from __future__ import annotations

import os
from typing import ClassVar

from tradecraft.providers.base import _register


class OpenAIProvider:
    name: ClassVar[str] = "openai"
    default_model: ClassVar[str] = "gpt-4o"
    requires_api_key: ClassVar[bool] = True

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
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
    def from_env(cls, model: str | None = None) -> OpenAIProvider | None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        return cls(api_key=api_key, model=model)


_register(OpenAIProvider.name, OpenAIProvider)

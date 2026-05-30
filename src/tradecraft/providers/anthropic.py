"""Anthropic adapter."""

from __future__ import annotations

import os
from typing import ClassVar

from tradecraft.providers.base import _register


class AnthropicProvider:
    name: ClassVar[str] = "anthropic"
    default_model: ClassVar[str] = "claude-sonnet-4-6"
    requires_api_key: ClassVar[bool] = True

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        # Lazy: only import the SDK when an instance is built.
        import anthropic  # noqa: PLC0415

        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str:
        # The user prompt block is large (Findings + heuristic questions).
        # Mark it as ephemeral-cacheable so re-runs within the 5-minute
        # window hit cache for the bulk content.
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                }
            ],
        )
        # response.content is a list of content blocks; take the first text block.
        for block in response.content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                return text
        return ""

    @classmethod
    def from_env(cls, model: str | None = None) -> AnthropicProvider | None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        return cls(api_key=api_key, model=model)


_register(AnthropicProvider.name, AnthropicProvider)

"""Provider protocol + factory.

Adapters are registered lazily so importing tradecraft.providers does NOT
import anthropic / openai SDKs — those imports happen inside the adapter
module's `from_env` classmethod, which is only called when the user
actually requests that provider via --ai.
"""

from __future__ import annotations

import importlib
from typing import ClassVar, Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    name: ClassVar[str]
    default_model: ClassVar[str]
    requires_api_key: ClassVar[bool]

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str: ...

    @classmethod
    def from_env(cls, model: str | None = None) -> Provider | None: ...


# Adapter registry. Populated lazily by build_provider so optional SDK
# packages don't have to be importable at module-load time.
_REGISTRY: dict[str, type[Provider]] = {}


def build_provider(name: str, model: str | None = None) -> Provider | None:
    """Return a configured Provider instance, or None if required env vars missing.

    Raises ValueError if `name` is not a known provider key.
    """
    if name not in _REGISTRY:
        # Import the adapter module lazily; it self-registers via _register.
        _import_adapter(name)
    if name not in _REGISTRY:
        raise ValueError(f"unknown provider: {name!r}")
    return _REGISTRY[name].from_env(model)


def _register(name: str, cls: type[Provider]) -> None:
    """Adapter modules call this at import time to register themselves."""
    _REGISTRY[name] = cls


def _import_adapter(name: str) -> None:
    """Import the adapter module so it can self-register."""
    mapping = {
        "anthropic": "tradecraft.providers.anthropic",
        "openai": "tradecraft.providers.openai",
        "ollama": "tradecraft.providers.ollama",
        "openai-compat": "tradecraft.providers.openai_compat",
    }
    if name in mapping:
        try:
            importlib.import_module(mapping[name])
        except ImportError:
            # Adapter's SDK is missing; leave registry empty. build_provider
            # will treat this as "unknown".
            return

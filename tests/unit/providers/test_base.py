"""Tests for tradecraft.providers.base."""

from __future__ import annotations

import pytest

from tradecraft.providers.base import Provider, build_provider


class FakeProvider:
    name = "fake"
    default_model = "fake-1"
    requires_api_key = False

    def __init__(self, model: str | None = None) -> None:
        self.model = model or self.default_model

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str:  # noqa: ARG002
        return f"system={system!r} prompt={prompt!r}"

    @classmethod
    def from_env(cls, model: str | None = None) -> FakeProvider | None:
        return cls(model)


async def test_protocol_runtime_check() -> None:
    p = FakeProvider()
    assert isinstance(p, Provider)
    out = await p.generate("sys", "user", 100)
    assert "user" in out


def test_build_provider_dispatches_to_known_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        __import__("tradecraft.providers.base", fromlist=["_REGISTRY"]).__dict__["_REGISTRY"],
        "fake",
        FakeProvider,
    )
    p = build_provider("fake")
    assert p is not None
    assert p.name == "fake"


def test_build_provider_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown provider"):
        build_provider("does-not-exist")

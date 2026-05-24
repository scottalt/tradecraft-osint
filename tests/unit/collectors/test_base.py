"""Tests for tradecraft.collectors.base."""

from __future__ import annotations

from typing import ClassVar

from tradecraft.collectors.base import (
    Collector,
    CollectorContext,
    timed_run,
)
from tradecraft.models import (
    CollectorResult,
    Role,
    Signal,
    Target,
)


class FakeCollector(Collector):
    name: ClassVar[str] = "fake"
    requires_network: ClassVar[bool] = False
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.GENERIC}

    async def run(self, ctx: CollectorContext) -> CollectorResult:  # noqa: ARG002
        return CollectorResult(
            name=self.name,
            data={"ok": True},
            signals=[Signal.MISSING_CSP],
            errors=[],
            duration_ms=0,
        )


async def test_collector_runs() -> None:
    c = FakeCollector()
    ctx = CollectorContext(
        target=Target(company_name="Acme", root_url="https://acme.com"),
        http=None,  # type: ignore[arg-type]
        cache=None,  # type: ignore[arg-type]
    )
    result = await c.run(ctx)
    assert result.name == "fake"
    assert Signal.MISSING_CSP in result.signals


async def test_timed_run_records_duration_and_catches_errors() -> None:
    class Broken(Collector):
        name: ClassVar[str] = "broken"
        requires_network: ClassVar[bool] = False
        safe_for_hosted: ClassVar[bool] = True
        role_relevance: ClassVar[set[Role]] = {Role.GENERIC}

        async def run(self, ctx: CollectorContext) -> CollectorResult:  # noqa: ARG002
            raise RuntimeError("boom")

    ctx = CollectorContext(
        target=Target(company_name="Acme", root_url="https://acme.com"),
        http=None,  # type: ignore[arg-type]
        cache=None,  # type: ignore[arg-type]
    )
    result = await timed_run(Broken(), ctx)
    assert result.name == "broken"
    assert result.errors
    assert result.errors[0].message == "boom"
    assert result.duration_ms >= 0


async def test_timed_run_overrides_returned_duration() -> None:
    class Liar(Collector):
        name: ClassVar[str] = "liar"
        requires_network: ClassVar[bool] = False
        safe_for_hosted: ClassVar[bool] = True
        role_relevance: ClassVar[set[Role]] = {Role.GENERIC}

        async def run(self, ctx: CollectorContext) -> CollectorResult:  # noqa: ARG002
            return CollectorResult(
                name=self.name, data={}, signals=[], errors=[], duration_ms=99999
            )

    ctx = CollectorContext(
        target=Target(company_name="Acme", root_url="https://acme.com"),
        http=None,  # type: ignore[arg-type]
        cache=None,  # type: ignore[arg-type]
    )
    result = await timed_run(Liar(), ctx)
    assert result.duration_ms < 99999

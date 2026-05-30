"""Collector protocol + helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

from tradecraft.cache import Cache
from tradecraft.http import HttpClient
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Target,
)


@dataclass(frozen=True)
class CollectorContext:
    target: Target
    http: HttpClient
    cache: Cache


@runtime_checkable
class Collector(Protocol):
    """The plugin protocol every OSINT module implements."""

    name: ClassVar[str]
    requires_network: ClassVar[bool]
    safe_for_hosted: ClassVar[bool]
    role_relevance: ClassVar[set[Role]]

    async def run(self, ctx: CollectorContext) -> CollectorResult: ...


async def timed_run(collector: Collector, ctx: CollectorContext) -> CollectorResult:
    """Run a collector with timing + exception containment.

    Always returns a CollectorResult; never raises. If the collector raises,
    its name is preserved and the error is recorded in `errors`.
    """
    start = time.perf_counter()
    try:
        result = await collector.run(ctx)
    except Exception as exc:  # intentional containment
        duration_ms = int((time.perf_counter() - start) * 1000)
        return CollectorResult(
            name=collector.name,
            data={},
            signals=[],
            errors=[
                CollectorError(
                    stage="run",
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            ],
            duration_ms=duration_ms,
        )
    duration_ms = int((time.perf_counter() - start) * 1000)
    return result.model_copy(update={"duration_ms": duration_ms})

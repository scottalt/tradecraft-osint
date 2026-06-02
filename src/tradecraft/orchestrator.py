"""Orchestrator: run collectors concurrently and aggregate findings."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from tradecraft.cache import Cache
from tradecraft.collectors.base import Collector, CollectorContext, timed_run
from tradecraft.http import HttpClient
from tradecraft.models import CollectorError, CollectorResult, Findings, Target


class Orchestrator:
    def __init__(
        self,
        collectors: Iterable[Collector],
        http: HttpClient,
        cache: Cache,
    ) -> None:
        self.collectors: list[Collector] = list(collectors)
        self.http = http
        self.cache = cache

    async def run(
        self,
        target: Target,
        *,
        hosted: bool = False,
        only: set[str] | None = None,
        skip: set[str] | None = None,
        collector_timeout: float | None = None,
    ) -> Findings:
        active = self._select(hosted=hosted, only=only, skip=skip)
        ctx = CollectorContext(target=target, http=self.http, cache=self.cache)
        results = await asyncio.gather(*(self._bounded(c, ctx, collector_timeout) for c in active))
        return Findings(target=target, results=list(results))

    @staticmethod
    async def _bounded(
        collector: Collector,
        ctx: CollectorContext,
        timeout: float | None,
    ) -> CollectorResult:
        """Run a collector, capping its wall-clock time so one slow collector
        (e.g. crt.sh enumeration) cannot stall the whole run. A timeout yields a
        partial-failure result instead of hanging — important on hosted, where the
        serverless function has a hard request deadline."""
        if timeout is None:
            return await timed_run(collector, ctx)
        try:
            return await asyncio.wait_for(timed_run(collector, ctx), timeout)
        except TimeoutError:
            return CollectorResult(
                name=collector.name,
                data={},
                signals=[],
                errors=[
                    CollectorError(
                        stage="run",
                        message=f"timed out after {timeout:.0f}s (hosted budget)",
                        exception_type="TimeoutError",
                    )
                ],
                duration_ms=int(timeout * 1000),
            )

    def _select(
        self,
        *,
        hosted: bool,
        only: set[str] | None,
        skip: set[str] | None,
    ) -> list[Collector]:
        result: list[Collector] = []
        for c in self.collectors:
            if hosted and not c.safe_for_hosted:
                continue
            if only is not None and c.name not in only:
                continue
            if skip is not None and c.name in skip:
                continue
            result.append(c)
        return result

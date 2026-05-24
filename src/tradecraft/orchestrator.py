"""Orchestrator: run collectors concurrently and aggregate findings."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from tradecraft.cache import Cache
from tradecraft.collectors.base import Collector, CollectorContext, timed_run
from tradecraft.http import HttpClient
from tradecraft.models import Findings, Target


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
    ) -> Findings:
        active = self._select(hosted=hosted, only=only, skip=skip)
        ctx = CollectorContext(target=target, http=self.http, cache=self.cache)
        results = await asyncio.gather(*(timed_run(c, ctx) for c in active))
        return Findings(target=target, results=list(results))

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

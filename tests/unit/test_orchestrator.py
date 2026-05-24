"""Tests for tradecraft.orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from tradecraft.cache import Cache
from tradecraft.collectors.base import Collector, CollectorContext
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import (
    CollectorResult,
    Findings,
    Role,
    Signal,
    Target,
)
from tradecraft.orchestrator import Orchestrator


class Footprint(Collector):
    name: ClassVar[str] = "footprint"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY, Role.SWE}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        return CollectorResult(
            name=self.name,
            data={"host": ctx.target.root_url.host},
            signals=[Signal.MISSING_CSP],
            errors=[],
            duration_ms=0,
        )


class News(Collector):
    name: ClassVar[str] = "news"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {Role.GENERIC}

    async def run(self, _ctx: CollectorContext) -> CollectorResult:
        return CollectorResult(
            name=self.name, data={"items": []}, signals=[], errors=[], duration_ms=0
        )


class Broken(Collector):
    name: ClassVar[str] = "broken"
    requires_network: ClassVar[bool] = False
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.GENERIC}

    async def run(self, _ctx: CollectorContext) -> CollectorResult:
        raise RuntimeError("boom")


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache) as c:
        yield c, cache


async def test_runs_all_collectors_concurrently(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), News()], http=client, cache=cache)
    findings = await orch.run(target)
    assert isinstance(findings, Findings)
    names = {r.name for r in findings.results}
    assert names == {"footprint", "news"}


async def test_hosted_mode_skips_unsafe_collectors(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), News()], http=client, cache=cache)
    findings = await orch.run(target, hosted=True)
    assert {r.name for r in findings.results} == {"footprint"}


async def test_only_filter_runs_just_those(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), News()], http=client, cache=cache)
    findings = await orch.run(target, only={"news"})
    assert {r.name for r in findings.results} == {"news"}


async def test_skip_filter_excludes_those(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), News()], http=client, cache=cache)
    findings = await orch.run(target, skip={"footprint"})
    assert {r.name for r in findings.results} == {"news"}


async def test_one_broken_collector_does_not_kill_run(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), Broken()], http=client, cache=cache)
    findings = await orch.run(target)
    assert {r.name for r in findings.results} == {"footprint", "broken"}
    broken_result = findings.collector("broken")
    assert broken_result is not None
    assert broken_result.errors

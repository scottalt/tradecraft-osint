"""Tests for tradecraft.collectors.job."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.job import JobCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, str]:
    return {
        "gh": (fixtures_dir / "job" / "greenhouse_acme.html").read_text(),
        "lever": (fixtures_dir / "job" / "lever_acme.html").read_text(),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="boards.greenhouse.io") as c:
        yield c, cache


def test_metadata() -> None:
    c = JobCollector()
    assert c.name == "job"
    assert c.safe_for_hosted is True
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_greenhouse_extraction(http, fixtures) -> None:
    client, cache = http
    # robots required by target-scoped enforcement
    respx.get("https://boards.greenhouse.io/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://boards.greenhouse.io/acme/jobs/123").mock(
        return_value=httpx.Response(200, text=fixtures["gh"])
    )
    target = Target(
        company_name="Acme",
        root_url="https://acme.com",
        job_url="https://boards.greenhouse.io/acme/jobs/123",
    )
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await JobCollector().run(ctx)

    assert result.data["title"] == "Senior Security Engineer"
    stack = set(result.data["stack"])
    assert {"Go", "Kubernetes", "AWS", "Rust"} <= stack


async def test_no_job_url_no_op() -> None:
    cache = Cache(directory=Path(), default_ttl=60, enabled=False)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as client:
        target = Target(company_name="Acme", root_url="https://acme.com")
        ctx = CollectorContext(target=target, http=client, cache=cache)
        result = await JobCollector().run(ctx)
    assert result.data == {} or result.data.get("title") is None
    assert result.errors == []


@respx.mock
async def test_job_stack_listed_evidence(http, fixtures) -> None:
    """JD with known stack keywords fires JOB_STACK_LISTED and attaches Evidence."""
    client, cache = http
    respx.get("https://boards.greenhouse.io/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://boards.greenhouse.io/acme/jobs/123").mock(
        return_value=httpx.Response(200, text=fixtures["gh"])
    )
    target = Target(
        company_name="Acme",
        root_url="https://acme.com",
        job_url="https://boards.greenhouse.io/acme/jobs/123",
    )
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await JobCollector().run(ctx)

    assert Signal.JOB_STACK_LISTED in result.signals
    assert len(result.evidence) == 1
    ev = result.evidence[0]
    assert ev.signal == Signal.JOB_STACK_LISTED
    assert ev.source == "job"
    assert ev.url == "https://boards.greenhouse.io/acme/jobs/123"
    assert ev.date is None
    # summary is first ≤5 stack items joined by ", "
    stack = result.data["stack"]
    expected_summary = ", ".join(stack[:5])
    assert ev.summary == expected_summary


@respx.mock
async def test_empty_stack_no_evidence(http) -> None:
    """JD with no recognised stack keywords: no JOB_STACK_LISTED signal and evidence == []."""
    client, cache = http
    plain_html = (
        "<html><body><h1>Some Job</h1><p>Good communication skills required.</p></body></html>"
    )
    respx.get("https://boards.greenhouse.io/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://boards.greenhouse.io/acme/jobs/999").mock(
        return_value=httpx.Response(200, text=plain_html)
    )
    target = Target(
        company_name="Acme",
        root_url="https://acme.com",
        job_url="https://boards.greenhouse.io/acme/jobs/999",
    )
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await JobCollector().run(ctx)

    assert Signal.JOB_STACK_LISTED not in result.signals
    assert result.evidence == []


async def test_no_job_url_evidence_empty() -> None:
    """No job_url path returns evidence == []."""
    cache = Cache(directory=Path(), default_ttl=60, enabled=False)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as client:
        target = Target(company_name="Acme", root_url="https://acme.com")
        ctx = CollectorContext(target=target, http=client, cache=cache)
        result = await JobCollector().run(ctx)
    assert result.evidence == []

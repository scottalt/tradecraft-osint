"""Tests for tradecraft.collectors.company."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.company import CompanyCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, str]:
    return {
        "about": (fixtures_dir / "company" / "acme_about.html").read_text(),
        "team": (fixtures_dir / "company" / "acme_team.html").read_text(),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = CompanyCollector()
    assert c.name == "company"
    assert c.safe_for_hosted is True


@respx.mock
async def test_extracts_signals(http, fixtures) -> None:
    client, cache = http
    # robots.txt is required by target-scoped enforcement
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/about").mock(
        return_value=httpx.Response(200, text=fixtures["about"])
    )
    respx.get("https://acme.com/team").mock(return_value=httpx.Response(200, text=fixtures["team"]))
    # Default 404 for other paths
    respx.get("").mock(return_value=httpx.Response(404))

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await CompanyCollector().run(ctx)

    assert Signal.FOUNDER_TECHNICAL in result.signals  # "CTO, ... Stanford"
    assert "about" in {p["path"] for p in result.data["pages"]}
    assert any("Acme Cloud" in str(p) for p in result.data["pages"])


@respx.mock
async def test_no_pages_emits_product_empty(http) -> None:
    client, cache = http
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("").mock(return_value=httpx.Response(404))

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await CompanyCollector().run(ctx)

    assert Signal.PRODUCT_LIST_EMPTY in result.signals

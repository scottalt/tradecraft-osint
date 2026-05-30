"""Tests for tradecraft.collectors.people."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.people import PeopleCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Signal, Target


@pytest.fixture
def blog_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "people" / "acme_blog.html").read_text()


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = PeopleCollector()
    assert c.name == "people"
    assert c.safe_for_hosted is False


@respx.mock
async def test_strong_brand_signal(http, blog_html) -> None:
    client, cache = http
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/blog").mock(
        return_value=httpx.Response(200, text=blog_html)
    )
    respx.get("").mock(return_value=httpx.Response(404))  # default 404

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await PeopleCollector().run(ctx)

    assert Signal.STRONG_ENG_BRAND in result.signals
    assert "Sam Lee" in result.data["authors"]


@respx.mock
async def test_quiet_brand_when_no_blog(http) -> None:
    client, cache = http
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("").mock(return_value=httpx.Response(404))

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await PeopleCollector().run(ctx)

    assert Signal.QUIET_ENG_BRAND in result.signals

"""Tests for tradecraft.collectors.news."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.news import NewsCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, object]:
    return {
        "rss": (fixtures_dir / "news" / "google_news_acme.xml").read_text(),
        "hn": json.loads((fixtures_dir / "news" / "hn_algolia_acme.json").read_text()),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = NewsCollector()
    assert c.name == "news"
    assert c.safe_for_hosted is False
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_signal_extraction_from_headlines(http, fixtures) -> None:
    client, cache = http
    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text=str(fixtures["rss"]))
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json=fixtures["hn"])
    )
    target = Target(company_name="Acme Corp", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_FUNDING in result.signals  # "raises $200M Series D"
    assert Signal.RECENT_LEADERSHIP_CHANGE in result.signals  # "CEO ... steps down"
    assert Signal.RECENT_SECURITY_INCIDENT in result.signals  # "data breach"
    assert Signal.RECENT_LAYOFFS in result.signals  # "workforce reduction"
    assert len(result.data["items"]) >= 4


@respx.mock
async def test_empty_feeds_no_signals(http) -> None:
    client, cache = http
    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json={"hits": []})
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    for s in (
        Signal.RECENT_FUNDING,
        Signal.RECENT_LAYOFFS,
        Signal.RECENT_SECURITY_INCIDENT,
        Signal.RECENT_LEADERSHIP_CHANGE,
    ):
        assert s not in result.signals

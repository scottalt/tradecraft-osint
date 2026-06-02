"""Tests for tradecraft.collectors.ma."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.ma import MaCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Signal, Target


@pytest.fixture
def fixture(fixtures_dir: Path) -> str:
    return (fixtures_dir / "ma" / "wikipedia_infobox_acme.html").read_text()


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = MaCollector()
    assert c.name == "ma"
    assert c.safe_for_hosted is True


@respx.mock
async def test_subsidiary_and_frequent_acquirer(http, fixture) -> None:
    client, cache = http
    respx.get("https://en.wikipedia.org/wiki/Acme").mock(
        return_value=httpx.Response(200, text=fixture)
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await MaCollector().run(ctx)

    assert Signal.SUBSIDIARY_OF in result.signals
    assert Signal.M_A_FREQUENT_ACQUIRER in result.signals
    assert result.data["parent"] == "Globex Industries"
    assert len(result.data["subsidiaries"]) == 5


@respx.mock
async def test_subsidiary_of_evidence(http, fixture) -> None:
    """Parent row in infobox produces SUBSIDIARY_OF Evidence with correct fields."""
    client, cache = http
    respx.get("https://en.wikipedia.org/wiki/Acme").mock(
        return_value=httpx.Response(200, text=fixture)
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await MaCollector().run(ctx)

    subsidiary_ev = next((e for e in result.evidence if e.signal == Signal.SUBSIDIARY_OF), None)
    assert subsidiary_ev is not None
    assert subsidiary_ev.summary == "Subsidiary of Globex Industries"
    assert subsidiary_ev.source == "wikipedia"
    assert subsidiary_ev.url == "https://en.wikipedia.org/wiki/Acme"
    assert subsidiary_ev.date is None


@respx.mock
async def test_frequent_acquirer_evidence(http, fixture) -> None:
    """Many subsidiaries in infobox produces M_A_FREQUENT_ACQUIRER Evidence."""
    client, cache = http
    respx.get("https://en.wikipedia.org/wiki/Acme").mock(
        return_value=httpx.Response(200, text=fixture)
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await MaCollector().run(ctx)

    acquirer_ev = next(
        (e for e in result.evidence if e.signal == Signal.M_A_FREQUENT_ACQUIRER), None
    )
    assert acquirer_ev is not None
    assert acquirer_ev.summary == "Frequent acquirer (5 subsidiaries)"
    assert acquirer_ev.source == "wikipedia"
    assert acquirer_ev.url == "https://en.wikipedia.org/wiki/Acme"
    assert acquirer_ev.date is None


@respx.mock
async def test_no_infobox_evidence_empty(http) -> None:
    """Page with no infobox returns evidence == []."""
    client, cache = http
    html_no_infobox = "<html><body><p>No infobox here.</p></body></html>"
    respx.get("https://en.wikipedia.org/wiki/Acme").mock(
        return_value=httpx.Response(200, text=html_no_infobox)
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await MaCollector().run(ctx)

    assert result.evidence == []
    assert result.signals == []

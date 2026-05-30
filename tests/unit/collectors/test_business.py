"""Tests for tradecraft.collectors.business."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.business import BusinessCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, object]:
    return {
        "sec": json.loads((fixtures_dir / "business" / "sec_edgar_acme.json").read_text()),
        "wiki": (fixtures_dir / "business" / "wikipedia_acme.html").read_text(),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = BusinessCollector()
    assert c.name == "business"
    assert c.safe_for_hosted is False


@respx.mock
async def test_public_company_and_wikipedia(http, fixtures) -> None:
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json=fixtures["sec"])
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(200, text=str(fixtures["wiki"]))
    )
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    assert Signal.PUBLIC_COMPANY in result.signals
    assert Signal.WIKIPEDIA_INFOBOX_PRESENT in result.signals
    assert result.data["ticker"] == "ACME"


@respx.mock
async def test_no_match(http) -> None:
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(
            200, json={"0": {"cik_str": 1, "ticker": "XYZ", "title": "Unrelated"}}
        )
    )
    respx.get("").mock(return_value=httpx.Response(404))
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    assert Signal.PUBLIC_COMPANY not in result.signals
    assert Signal.WIKIPEDIA_INFOBOX_PRESENT not in result.signals

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
    assert c.safe_for_hosted is False


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

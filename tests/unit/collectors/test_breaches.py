"""Tests for tradecraft.collectors.breaches."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.breaches import BreachesCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixture(fixtures_dir: Path) -> list[dict]:
    return json.loads((fixtures_dir / "breaches" / "hibp_acme.json").read_text())


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = BreachesCollector()
    assert c.name == "breaches"
    assert c.safe_for_hosted is False
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_emits_history_and_recent_signals(http, fixture) -> None:
    client, cache = http
    respx.get("https://haveibeenpwned.com/api/v3/breaches").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BreachesCollector().run(ctx)

    assert Signal.BREACH_HISTORY in result.signals
    assert Signal.BREACH_RECENT in result.signals
    assert len(result.data["breaches"]) == 2
    # most recent first
    assert result.data["breaches"][0]["name"] == "AcmeRecent"


@respx.mock
async def test_no_breach_no_signals(http) -> None:
    client, cache = http
    respx.get("https://haveibeenpwned.com/api/v3/breaches").mock(
        return_value=httpx.Response(200, json=[])
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BreachesCollector().run(ctx)

    assert Signal.BREACH_HISTORY not in result.signals
    assert Signal.BREACH_RECENT not in result.signals


@respx.mock
async def test_404_recorded_as_error_not_crash(http) -> None:
    client, cache = http
    respx.get("https://haveibeenpwned.com/api/v3/breaches").mock(
        return_value=httpx.Response(404)
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BreachesCollector().run(ctx)

    assert result.signals == []
    # No error if 404 just means "no breaches recorded for this domain"
    assert result.data["breaches"] == []

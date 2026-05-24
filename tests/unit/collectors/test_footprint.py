"""Tests for tradecraft.collectors.footprint."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.footprint import FootprintCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, object]:
    crtsh = json.loads((fixtures_dir / "footprint" / "crtsh_acme.json").read_text())
    headers = json.loads((fixtures_dir / "footprint" / "acme_root_headers.json").read_text())
    return {"crtsh": crtsh, "headers": headers}


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache) as c:
        yield c, cache


def test_collector_metadata_is_correct() -> None:
    c = FootprintCollector()
    assert c.name == "footprint"
    assert c.safe_for_hosted is True
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_runs_and_emits_signals(http, fixtures) -> None:
    client, cache = http
    respx.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=fixtures["crtsh"])
    )
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=fixtures["headers"])
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    # Replace the DNS lookup with a noop for the test.
    monkey_dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    assert result.name == "footprint"
    assert Signal.MISSING_CSP in result.signals
    assert Signal.OPEN_STAGING_SUBDOMAIN in result.signals
    subdomains = result.data["subdomains"]
    assert "staging.acme.com" in subdomains  # type: ignore[operator]
    assert "*.acme.com" not in subdomains  # type: ignore[operator]


@respx.mock
async def test_no_staging_subdomain_no_signal(http, fixtures) -> None:
    client, cache = http
    crtsh_clean = [{"name_value": "acme.com"}, {"name_value": "www.acme.com"}]
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=crtsh_clean))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=fixtures["headers"])
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkey_dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    assert Signal.OPEN_STAGING_SUBDOMAIN not in result.signals


@respx.mock
async def test_csp_present_no_signal(http, fixtures) -> None:
    client, cache = http
    headers_with_csp = {**fixtures["headers"], "content-security-policy": "default-src 'self'"}
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=headers_with_csp)
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkey_dns = AsyncMock(return_value={"A": [], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    assert Signal.MISSING_CSP not in result.signals

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
        "home": (fixtures_dir / "company" / "acme_home.html").read_text(),
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
    respx.get("https://acme.com/").mock(return_value=httpx.Response(200, text=fixtures["home"]))
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
    assert "home" in {p["path"] for p in result.data["pages"]}
    assert any("Acme Cloud" in str(p) for p in result.data["pages"])

    # Homepage meta description -> BUSINESS_DESCRIPTION evidence, source/url set.
    assert Signal.BUSINESS_DESCRIPTION in result.signals
    desc_ev = next(e for e in result.evidence if e.signal == Signal.BUSINESS_DESCRIPTION)
    assert "cloud security platform" in desc_ev.summary
    assert desc_ev.source == "company"
    assert desc_ev.url == "https://acme.com/"


@respx.mock
async def test_about_page_fallback_cites_about_url(http) -> None:
    """Homepage has no meta description; about-page does -> evidence cites about URL."""
    client, cache = http
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    home_no_desc = "<html><head><title>Acme</title></head><body><h1>Acme</h1></body></html>"
    about_with_desc = (
        "<html><head><title>About</title>"
        '<meta name="description" content="Acme is a cloud security platform for teams.">'
        "</head><body><h1>About Acme</h1></body></html>"
    )
    respx.get("https://acme.com/").mock(return_value=httpx.Response(200, text=home_no_desc))
    respx.get("https://acme.com/about").mock(return_value=httpx.Response(200, text=about_with_desc))
    respx.get("").mock(return_value=httpx.Response(404))

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await CompanyCollector().run(ctx)

    assert Signal.BUSINESS_DESCRIPTION in result.signals
    desc_ev = next(e for e in result.evidence if e.signal == Signal.BUSINESS_DESCRIPTION)
    assert "cloud security platform" in desc_ev.summary
    assert desc_ev.url == "https://acme.com/about"


@respx.mock
async def test_no_pages_emits_product_empty(http) -> None:
    client, cache = http
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("").mock(return_value=httpx.Response(404))

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await CompanyCollector().run(ctx)

    assert Signal.PRODUCT_LIST_EMPTY in result.signals
    assert Signal.BUSINESS_DESCRIPTION not in result.signals
    assert not result.evidence


@respx.mock
async def test_security_page_with_soc2_emits_compliance_noted(http) -> None:
    """A /security page mentioning 'SOC 2' emits COMPLIANCE_NOTED evidence citing
    the site root — a GRC interview hook. Also confirms /security is fetched."""
    client, cache = http
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    home = "<html><head><title>Acme</title></head><body><h1>Acme</h1></body></html>"
    security_page = (
        "<html><head><title>Security - Acme</title></head><body>"
        "<h1>Trust & Security</h1>"
        "<p>Acme maintains SOC 2 Type II and ISO 27001 certifications.</p>"
        "</body></html>"
    )
    respx.get("https://acme.com/").mock(return_value=httpx.Response(200, text=home))
    respx.get("https://acme.com/security").mock(
        return_value=httpx.Response(200, text=security_page)
    )
    respx.get("").mock(return_value=httpx.Response(404))

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await CompanyCollector().run(ctx)

    # /security was fetched and parsed.
    assert "security" in {p["path"] for p in result.data["pages"]}

    assert Signal.COMPLIANCE_NOTED in result.signals
    ev = next(e for e in result.evidence if e.signal == Signal.COMPLIANCE_NOTED)
    assert ev.summary == "references SOC 2"
    assert ev.url == "https://acme.com/"
    assert ev.source == "company"
    assert ev.date is None

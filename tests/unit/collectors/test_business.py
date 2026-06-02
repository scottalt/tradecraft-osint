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
    assert c.safe_for_hosted is True


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
async def test_industry_and_description_evidence(http, fixtures) -> None:
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

    assert Signal.INDUSTRY_IDENTIFIED in result.signals
    assert result.data["industry"] == "Security software"
    industry_ev = next(e for e in result.evidence if e.signal == Signal.INDUSTRY_IDENTIFIED)
    assert industry_ev.summary == "Security software"
    assert industry_ev.source == "wikipedia"
    assert industry_ev.url == "https://en.wikipedia.org/wiki/Acme_Corporation"

    assert Signal.BUSINESS_DESCRIPTION in result.signals
    desc_ev = next(e for e in result.evidence if e.signal == Signal.BUSINESS_DESCRIPTION)
    assert "security software company" in desc_ev.summary
    assert desc_ev.source == "wikipedia"


@respx.mock
async def test_no_industry_or_description_when_missing(http) -> None:
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json={})
    )
    bare_wiki = (
        "<!doctype html><html><body>"
        "<table class='infobox'><tr><th>Founded</th><td>2018</td></tr></table>"
        "<p>Short.</p>"
        "</body></html>"
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(200, text=bare_wiki)
    )
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    assert Signal.WIKIPEDIA_INFOBOX_PRESENT in result.signals
    assert Signal.INDUSTRY_IDENTIFIED not in result.signals
    assert Signal.BUSINESS_DESCRIPTION not in result.signals
    assert not result.evidence


@respx.mock
async def test_description_without_infobox(http) -> None:
    """No table.infobox, but a qualifying lead <p> -> BUSINESS_DESCRIPTION only."""
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json={})
    )
    no_infobox_wiki = (
        "<!doctype html><html><body><div class='mw-parser-output'>"
        "<p>Acme Corporation is a privately held security software company "
        "headquartered in San Francisco building cloud tooling for enterprises.</p>"
        "</div></body></html>"
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(200, text=no_infobox_wiki)
    )
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    assert Signal.WIKIPEDIA_INFOBOX_PRESENT not in result.signals
    assert Signal.INDUSTRY_IDENTIFIED not in result.signals
    assert Signal.BUSINESS_DESCRIPTION in result.signals
    desc_ev = next(e for e in result.evidence if e.signal == Signal.BUSINESS_DESCRIPTION)
    assert "security software company" in desc_ev.summary
    assert desc_ev.source == "wikipedia"
    assert desc_ev.url == "https://en.wikipedia.org/wiki/Acme_Corporation"


@respx.mock
async def test_lead_paragraph_skips_infobox_p(http) -> None:
    """A long <p> nested in an infobox cell must not be picked as the lead."""
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json={})
    )
    wiki = (
        "<!doctype html><html><body>"
        "<table class='infobox'><tr><th>Products</th><td>"
        "<p>This is infobox junk listing many product names that exceeds sixty "
        "characters and should never be chosen as the company lead description.</p>"
        "</td></tr></table>"
        "<div class='mw-parser-output'>"
        "<p>Acme Corporation is a real security software company headquartered in "
        "San Francisco that builds modern cloud security tooling.</p>"
        "</div></body></html>"
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(200, text=wiki)
    )
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    desc_ev = next(e for e in result.evidence if e.signal == Signal.BUSINESS_DESCRIPTION)
    assert "real security software company" in desc_ev.summary
    assert "infobox junk" not in desc_ev.summary


@respx.mock
async def test_lead_paragraph_preserves_spaces_between_inline_elements(http) -> None:
    """Inline links must not be glued: 'cloud <a>cybersecurity</a>' -> standalone
    'cybersecurity', not 'cloudcybersecurity' (which would break \\bword\\b matching)."""
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json={})
    )
    wiki = (
        "<!doctype html><html><body><div class='mw-parser-output'>"
        "<p>Acme Corporation provides <a>content delivery network</a> and "
        "<a>cloud cybersecurity</a> services headquartered "
        "in <a>San Francisco</a>.</p>"
        "</div></body></html>"
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(200, text=wiki)
    )
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    desc_ev = next(e for e in result.evidence if e.signal == Signal.BUSINESS_DESCRIPTION)
    words = desc_ev.summary.split()
    assert "cybersecurity" in words, f"expected standalone 'cybersecurity' in {desc_ev.summary!r}"
    assert "cloudcybersecurity" not in desc_ev.summary
    assert "inSan" not in desc_ev.summary


@respx.mock
async def test_style_blocks_stripped_from_infobox_industry(http) -> None:
    """Infobox <td> with an embedded <style> block must not leak CSS into industry."""
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json={})
    )
    wiki = (
        "<!doctype html><html><body>"
        "<table class='infobox'><tr>"
        "<th>Industry</th>"
        "<td>"
        "<style>.mw-parser-output .plainlist ol,.mw-parser-output .plainlist ul"
        "{line-height:inherit;margin:0;padding:0}"
        ".mw-parser-output .plainlist ol li,.mw-parser-output .plainlist ul li"
        "{margin-bottom:0}</style>"
        "Financial services Payment processor"
        "</td>"
        "</tr></table>"
        "<p>Acme Corporation is a financial services and payment processing company "
        "headquartered in San Francisco that serves millions of businesses worldwide.</p>"
        "</body></html>"
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(200, text=wiki)
    )
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    assert Signal.INDUSTRY_IDENTIFIED in result.signals
    industry = result.data["industry"]
    assert "Financial services" in industry
    assert "mw-parser-output" not in industry
    assert "line-height" not in industry
    assert "{" not in industry

    industry_ev = next(e for e in result.evidence if e.signal == Signal.INDUSTRY_IDENTIFIED)
    assert "Financial services" in industry_ev.summary
    assert "mw-parser-output" not in industry_ev.summary
    assert "line-height" not in industry_ev.summary
    assert "{" not in industry_ev.summary


@respx.mock
async def test_style_blocks_stripped_from_lead_paragraph(http) -> None:
    """Lead <p> with an embedded <style> block must not leak CSS into description."""
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json={})
    )
    wiki = (
        "<!doctype html><html><body><div class='mw-parser-output'>"
        "<p>"
        "<style>.mw-parser-output .hatnote{font-style:italic;line-height:1.5em}</style>"
        "Acme Corporation is a privately held security software company "
        "headquartered in San Francisco building cloud tooling for enterprises."
        "</p>"
        "</div></body></html>"
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(200, text=wiki)
    )
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    assert Signal.BUSINESS_DESCRIPTION in result.signals
    desc_ev = next(e for e in result.evidence if e.signal == Signal.BUSINESS_DESCRIPTION)
    assert "security software company" in desc_ev.summary
    assert "mw-parser-output" not in desc_ev.summary
    assert "line-height" not in desc_ev.summary
    assert "{" not in desc_ev.summary


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

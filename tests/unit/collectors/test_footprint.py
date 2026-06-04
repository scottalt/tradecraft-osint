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
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=fixtures["crtsh"]))
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


@pytest.mark.parametrize(
    "subdomain,should_fire",
    [
        # Real-world patterns observed against hig.com (the test that motivated this regex):
        ("staging-br.acme.com", True),
        ("esubscribe-qa.acme.com", True),
        ("subscribe-uat.acme.com", True),
        ("dev-portal.acme.com", True),
        # Classic dotted form must still match:
        ("staging.acme.com", True),
        ("dev.acme.com", True),
        ("qa.acme.com", True),
        ("uat.acme.com", True),
        # Words that include staging keywords as substrings are NOT pre-prod:
        ("developer.acme.com", False),  # "dev" inside "developer"
        ("testimonials.acme.com", False),  # "test" inside "testimonials"
        ("devops.acme.com", False),  # "dev" inside "devops" — production tool
        # Unrelated production subdomains:
        ("events.acme.com", False),
        ("api.acme.com", False),
        ("prompts.acme.com", False),
    ],
)
@respx.mock
async def test_staging_signal_detection(
    http,
    fixtures,
    subdomain: str,
    should_fire: bool,
) -> None:
    client, cache = http
    crtsh_payload = [{"name_value": f"acme.com\n{subdomain}"}]
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=crtsh_payload))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=fixtures["headers"])
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkey_dns = AsyncMock(return_value={"A": [], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    fired = Signal.OPEN_STAGING_SUBDOMAIN in result.signals
    assert fired is should_fire, (
        f"{subdomain}: expected fire={should_fire}, got fire={fired}, "
        f"subdomains={result.data['subdomains']}"
    )


@respx.mock
async def test_fingerprints_cloudflare_from_cf_ray_header(http, fixtures) -> None:
    client, cache = http
    headers = {**fixtures["headers"], "cf-ray": "abc123-LHR", "server": "cloudflare"}
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=headers)
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkey_dns = AsyncMock(return_value={"A": [], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await FootprintCollector(_dns_lookup=monkey_dns).run(ctx)

    observed = result.data["observed_tech"]
    assert "Cloudflare" in observed["cdn_waf"]  # type: ignore[index]
    assert Signal.TECH_OBSERVED in result.signals
    ev = next(e for e in result.evidence if e.signal == Signal.TECH_OBSERVED)
    assert "cloudflare" in ev.summary.lower()
    assert ev.source == "footprint"
    assert ev.url == "https://acme.com/"


@respx.mock
async def test_fingerprints_wordpress_from_body(http) -> None:
    client, cache = http
    body = "<html><head></head><body><img src='/wp-content/uploads/x.png'></body></html>"
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text=body, headers={"server": "Apache"})
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkey_dns = AsyncMock(return_value={"A": [], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await FootprintCollector(_dns_lookup=monkey_dns).run(ctx)

    observed = result.data["observed_tech"]
    assert "WordPress" in observed["cms"]  # type: ignore[index]
    assert Signal.TECH_OBSERVED in result.signals


@respx.mock
async def test_no_security_tech_match_no_signal(http) -> None:
    # A bare server header is informational only — no CDN/WAF or CMS detected,
    # so no TECH_OBSERVED signal/evidence fires.
    client, cache = http
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>plain</html>", headers={"server": "Apache"})
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkey_dns = AsyncMock(return_value={"A": [], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await FootprintCollector(_dns_lookup=monkey_dns).run(ctx)

    observed = result.data["observed_tech"]
    assert "cdn_waf" not in observed  # type: ignore[operator]
    assert "cms" not in observed  # type: ignore[operator]
    assert Signal.TECH_OBSERVED not in result.signals
    assert not any(e.signal == Signal.TECH_OBSERVED for e in result.evidence)


@respx.mock
async def test_no_tech_at_all_observed_tech_empty(http) -> None:
    # No server header and no body signatures -> observed_tech is empty.
    client, cache = http
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>plain</html>", headers={})
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkey_dns = AsyncMock(return_value={"A": [], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await FootprintCollector(_dns_lookup=monkey_dns).run(ctx)

    assert not result.data["observed_tech"]
    assert Signal.TECH_OBSERVED not in result.signals


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


@respx.mock
async def test_vendor_fingerprint_from_dns(http, fixtures) -> None:
    """TXT (Google/MS/Atlassian) + MX (Mimecast) -> vendors + VENDOR_STACK."""
    client, cache = http
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=fixtures["headers"])
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    dns_records = {
        "A": ["1.2.3.4"],
        "MX": ["10 acme-com.mail.protection.mimecast.com."],
        "TXT": [
            '"google-site-verification=abc123"',
            '"MS=ms12345678"',
            '"atlassian-domain-verification=xyz"',
            '"v=spf1 include:_spf.google.com ~all"',
        ],
    }
    monkey_dns = AsyncMock(return_value=dns_records)
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    vendors = result.data["vendors"]
    assert "Google Workspace" in vendors
    assert "Microsoft 365" in vendors
    assert "Atlassian" in vendors
    assert "Mimecast (email security)" in vendors
    assert Signal.VENDOR_STACK in result.signals

    ev = next(e for e in result.evidence if e.signal == Signal.VENDOR_STACK)
    assert "DNS reveals:" in ev.summary
    assert "Atlassian" in ev.summary
    assert ev.source == "footprint"


@respx.mock
async def test_single_email_security_vendor_fires_signal(http, fixtures) -> None:
    """A single email-security vendor (no other markers) is enough to fire VENDOR_STACK."""
    client, cache = http
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=fixtures["headers"])
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    dns_records = {
        "A": ["1.2.3.4"],
        "MX": ["10 acme.mail.pphosted.com."],
        "TXT": [],
    }
    monkey_dns = AsyncMock(return_value=dns_records)
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    assert "Proofpoint (email security)" in result.data["vendors"]
    assert Signal.VENDOR_STACK in result.signals


@respx.mock
async def test_no_vendor_stack_under_threshold(http, fixtures) -> None:
    """A single non-email-security vendor -> no VENDOR_STACK signal."""
    client, cache = http
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=fixtures["headers"])
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    dns_records = {
        "A": ["1.2.3.4"],
        "MX": [],
        "TXT": ['"docusign=abc"'],
    }
    monkey_dns = AsyncMock(return_value=dns_records)
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    assert result.data["vendors"] == ["DocuSign"]
    assert Signal.VENDOR_STACK not in result.signals

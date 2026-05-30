"""Web/infra footprint collector: DNS + CT subdomains + headers + robots/sitemap."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar
from urllib.parse import urlparse

import dns.asyncresolver

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

# Pre-prod indicators matched as whole words within the leftmost subdomain
# label. `\b` (word boundary) prevents false positives like "developer"
# (contains "dev"), "testimonials" ("test"), "devops" ("dev"). It DOES match
# dashed forms (`staging-br`, `subscribe-qa`, `dev-portal`) because `-` is a
# non-word char so `\bstaging\b` finds a boundary at the dash.
_STAGING_WORDS_RE = re.compile(
    r"\b(staging|dev|test|qa|uat|sandbox|preview)\b",
    re.IGNORECASE,
)
_DNS_RECORD_TYPES = ("A", "AAAA", "MX", "NS", "TXT", "CAA")
_DnsLookup = Callable[[str], Awaitable[dict[str, list[str]]]]


async def _default_dns_lookup(host: str) -> dict[str, list[str]]:
    resolver = dns.asyncresolver.Resolver()
    out: dict[str, list[str]] = {}
    for rtype in _DNS_RECORD_TYPES:
        try:
            answer = await resolver.resolve(host, rtype, lifetime=5.0)
        except Exception:  # DNS lookups frequently NXDOMAIN; treat as empty
            out[rtype] = []
            continue
        out[rtype] = [r.to_text() for r in answer]
    return out


class FootprintCollector:
    name: ClassVar[str] = "footprint"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY, Role.SWE, Role.DEVOPS}

    def __init__(self, _dns_lookup: _DnsLookup | None = None) -> None:
        self._dns_lookup = _dns_lookup or _default_dns_lookup

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        host = urlparse(str(ctx.target.root_url)).hostname or ""
        errors: list[CollectorError] = []
        signals: list[Signal] = []

        dns_records, subdomains, root_response, robots_text, sitemap_text = await asyncio.gather(
            self._safe(self._dns_lookup(host), errors, "dns"),
            self._safe(self._crtsh(ctx, host), errors, "crtsh"),
            self._safe(ctx.http.get(str(ctx.target.root_url)), errors, "root_get"),
            self._safe(ctx.http.get(f"https://{host}/robots.txt"), errors, "robots"),
            self._safe(ctx.http.get(f"https://{host}/sitemap.xml"), errors, "sitemap"),
        )

        sec_headers: dict[str, str] = {}
        server_header = None
        powered_by = None
        if root_response is not None:
            sec_headers = {
                k.lower(): v
                for k, v in root_response.headers.items()
                if k.lower()
                in {
                    "content-security-policy",
                    "strict-transport-security",
                    "x-frame-options",
                    "x-content-type-options",
                    "referrer-policy",
                    "permissions-policy",
                }
            }
            server_header = root_response.headers.get("server")
            powered_by = root_response.headers.get("x-powered-by")

        if root_response is not None:
            if "content-security-policy" not in sec_headers:
                signals.append(Signal.MISSING_CSP)
            if "strict-transport-security" not in sec_headers:
                signals.append(Signal.MISSING_HSTS)

        cleaned_subs: list[str] = []
        if subdomains is not None:
            cleaned_subs = sorted(
                {
                    s
                    for s in subdomains
                    if not s.startswith("*") and (s == host or s.endswith("." + host))
                }
            )
            if any(_STAGING_WORDS_RE.search(s.split(".", 1)[0]) for s in cleaned_subs):
                signals.append(Signal.OPEN_STAGING_SUBDOMAIN)

        return CollectorResult(
            name=self.name,
            data={
                "host": host,
                "dns": dns_records or {},
                "subdomains": cleaned_subs,
                "security_headers": sec_headers,
                "server": server_header,
                "x_powered_by": powered_by,
                "has_robots_txt": robots_text is not None
                and getattr(robots_text, "status_code", 0) == 200,
                "has_sitemap_xml": sitemap_text is not None
                and getattr(sitemap_text, "status_code", 0) == 200,
            },
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

    async def _crtsh(self, ctx: CollectorContext, host: str) -> list[str]:
        response = await ctx.http.get(f"https://crt.sh/?q={host}&output=json")
        if response.status_code != 200:
            return []
        try:
            data = response.json()
        except Exception:  # malformed JSON from crt.sh
            return []
        names: set[str] = set()
        for entry in data:
            raw = entry.get("name_value", "")
            for name in str(raw).splitlines():
                cleaned = name.strip().lower()
                if cleaned:
                    names.add(cleaned)
        return sorted(names)

    @staticmethod
    async def _safe(
        awaitable: Awaitable[Any],
        errors: list[CollectorError],
        stage: str,
    ) -> Any | None:
        try:
            return await awaitable
        except Exception as exc:
            errors.append(
                CollectorError(
                    stage=stage,
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )
            return None

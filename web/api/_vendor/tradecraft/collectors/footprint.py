"""Web/infra footprint collector: DNS + CT subdomains + headers + robots/sitemap."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, ClassVar
from urllib.parse import urlparse

import dns.asyncresolver

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Evidence,
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


@dataclass(frozen=True)
class _TechSig:
    """One tech signature. Matches if ANY of:
    - a response header whose name is in ``header_keys`` is present, OR
    - a header value contains one of ``value_contains`` (checked against the
      named header), OR
    - the body (or extracted <meta generator>) contains one of ``body_contains``.
    """

    name: str
    header_keys: tuple[str, ...] = ()
    value_contains: tuple[tuple[str, str], ...] = ()  # (header_name, substring)
    body_contains: tuple[str, ...] = ()
    generator_contains: tuple[str, ...] = ()


# CDN / WAF signatures (header-driven; most reliable external signal).
_CDN_WAF_SIGS: tuple[_TechSig, ...] = (
    _TechSig("Cloudflare", header_keys=("cf-ray",), value_contains=(("server", "cloudflare"),)),
    _TechSig(
        "Akamai",
        header_keys=("x-akamai-transformed", "x-akamai-request-id"),
        value_contains=(("server", "akamai"), ("server", "akamaighost")),
    ),
    _TechSig(
        "Fastly",
        value_contains=(("server", "fastly"), ("x-served-by", "fastly"), ("x-served-by", "cache-")),
    ),
    _TechSig(
        "AWS CloudFront",
        header_keys=("x-amz-cf-id",),
        value_contains=(("via", "cloudfront"), ("x-cache", "cloudfront")),
    ),
    _TechSig("Sucuri", header_keys=("x-sucuri-id",), value_contains=(("server", "sucuri"),)),
    _TechSig(
        "Imperva/Incapsula",
        header_keys=("x-iinfo",),
        value_contains=(("set-cookie", "incap_ses"), ("x-cdn", "incapsula")),
    ),
    _TechSig("Vercel", header_keys=("x-vercel-id",), value_contains=(("server", "vercel"),)),
    _TechSig("Netlify", header_keys=("x-nf-request-id",), value_contains=(("server", "netlify"),)),
)

# CMS / platform signatures (body + a few platform headers).
_CMS_SIGS: tuple[_TechSig, ...] = (
    _TechSig(
        "WordPress", body_contains=("/wp-content", "/wp-json"), generator_contains=("wordpress",)
    ),
    _TechSig(
        "Shopify", header_keys=("x-shopify-stage", "x-shopid"), body_contains=("cdn.shopify.com",)
    ),
    _TechSig("Drupal", value_contains=(("x-generator", "drupal"),), generator_contains=("drupal",)),
    _TechSig("Webflow", body_contains=("webflow",), value_contains=(("server", "webflow"),)),
    _TechSig("Squarespace", body_contains=("squarespace",), generator_contains=("squarespace",)),
    _TechSig(
        "Wix",
        header_keys=("x-wix-request-id",),
        body_contains=("wix.com",),
        generator_contains=("wix",),
    ),
    _TechSig("Ghost", body_contains=('content="ghost',), generator_contains=("ghost",)),
    _TechSig(
        "Next.js", body_contains=("__next_data__",), value_contains=(("x-powered-by", "next.js"),)
    ),
    _TechSig("Gatsby", body_contains=("___gatsby",), generator_contains=("gatsby",)),
)

_SERVER_SIGS: tuple[tuple[str, str], ...] = (
    ("nginx", "nginx"),
    ("apache", "Apache"),
    ("microsoft-iis", "IIS"),
)


def _sig_matches(sig: _TechSig, h: dict[str, str], body_l: str, generator: str) -> bool:
    if any(k in h for k in sig.header_keys):
        return True
    if any(sub in h.get(name, "") for name, sub in sig.value_contains):
        return True
    if any(sub in body_l for sub in sig.body_contains):
        return True
    return any(sub in generator for sub in sig.generator_contains)


def _fingerprint_tech(headers: dict[str, str], body: str) -> dict[str, list[str]]:
    """Positively fingerprint observed CDN/WAF, CMS/platform, and server tech.

    Conservative — only emits on clear, well-known signatures. Works from the
    (already-fetched) root response headers plus the root HTML body. Returns a
    dict with only the non-empty categories among ``cdn_waf`` / ``cms`` /
    ``server``; each value is a de-duplicated, order-preserving list of names.
    """
    h = {k.lower(): str(v).lower() for k, v in headers.items()}
    body_l = body.lower()
    m = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', body_l)
    generator = m.group(1) if m else ""

    cdn_waf = [s.name for s in _CDN_WAF_SIGS if _sig_matches(s, h, body_l, generator)]
    cms = [s.name for s in _CMS_SIGS if _sig_matches(s, h, body_l, generator)]
    server = [label for needle, label in _SERVER_SIGS if needle in h.get("server", "")]

    out: dict[str, list[str]] = {}
    if cdn_waf:
        out["cdn_waf"] = list(dict.fromkeys(cdn_waf))
    if cms:
        out["cms"] = list(dict.fromkeys(cms))
    if server:
        out["server"] = list(dict.fromkeys(server))
    return out


def _tech_summary(observed: dict[str, list[str]]) -> str:
    """Human phrase naming the notable (security-relevant) tech, e.g.
    'behind Cloudflare (CDN/WAF); built on WordPress'."""
    parts: list[str] = []
    cdn_waf = observed.get("cdn_waf") or []
    cms = observed.get("cms") or []
    if cdn_waf:
        parts.append(f"behind {', '.join(cdn_waf)} (CDN/WAF)")
    if cms:
        parts.append(f"built on {', '.join(cms)}")
    return "; ".join(parts)


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
        evidence: list[Evidence] = []

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
        observed_tech: dict[str, list[str]] = {}
        if root_response is not None:
            observed_tech = _fingerprint_tech(
                dict(root_response.headers),
                getattr(root_response, "text", "") or "",
            )
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

        # Positive tech fingerprint: emit a TECH_OBSERVED signal + cited evidence
        # only when security-relevant tech (CDN/WAF or CMS) is detected.
        if observed_tech.get("cdn_waf") or observed_tech.get("cms"):
            summary = _tech_summary(observed_tech)
            if summary:
                signals.append(Signal.TECH_OBSERVED)
                evidence.append(
                    Evidence(
                        signal=Signal.TECH_OBSERVED,
                        summary=summary,
                        url=str(ctx.target.root_url),
                        date=None,
                        source="footprint",
                    )
                )

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
                "observed_tech": observed_tech,
                "has_robots_txt": robots_text is not None
                and getattr(robots_text, "status_code", 0) == 200,
                "has_sitemap_xml": sitemap_text is not None
                and getattr(sitemap_text, "status_code", 0) == 200,
            },
            signals=signals,
            errors=errors,
            evidence=evidence,
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

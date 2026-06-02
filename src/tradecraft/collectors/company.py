"""Company collector: parse standard pages on the target's own site."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Any, ClassVar

from selectolax.parser import HTMLParser

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Evidence,
    Role,
    Signal,
)

_PATHS = ("/about", "/about-us", "/team", "/leadership", "/careers", "/press", "/blog")
_TECH_HINTS = re.compile(
    r"\b(engineer|cto|cs|computer\s+science|stanford|mit|principal|staff\s+engineer)\b",
    re.IGNORECASE,
)
_FOUNDER_HINTS = re.compile(r"\b(co.?founder|founder|founding)\b", re.IGNORECASE)


class CompanyCollector:
    name: ClassVar[str] = "company"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.SWE,
        Role.DEVOPS,
        Role.DATA,
        Role.ENG_LEADERSHIP,
        Role.GENERIC,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        evidence: list[Evidence] = []
        base = str(ctx.target.root_url).rstrip("/")
        root_url = f"{base}/"

        # Fetch the root homepage first (its meta description is usually the
        # canonical "what we do" statement), then the standard sub-pages.
        fetch_paths = ("", *_PATHS)
        results = await asyncio.gather(
            *(
                self._safe(ctx.http.get(f"{base}{p}" if p else root_url), errors, p or "home")
                for p in fetch_paths
            )
        )

        pages: list[dict[str, Any]] = []
        for path, resp in zip(fetch_paths, results, strict=True):
            if resp is None or resp.status_code != 200:
                continue
            tree = HTMLParser(resp.text)
            title_el = tree.css_first("title")
            description_el = tree.css_first('meta[name="description"]')
            headings = [h.text(strip=True) for h in tree.css("h1, h2, h3") if h.text(strip=True)]
            body_text = tree.body.text(strip=True) if tree.body else ""
            pages.append(
                {
                    "path": path.strip("/") or "home",
                    "url": root_url if path == "" else f"{base}{path}",
                    "title": title_el.text(strip=True) if title_el else "",
                    "description": str(description_el.attributes.get("content", ""))
                    if description_el
                    else "",
                    "headings": headings,
                    "body_excerpt": body_text[:1000],
                }
            )

        # BUSINESS_DESCRIPTION: prefer the homepage meta description, falling
        # back to the first about-page description. Emit at most once, and cite
        # the page the description actually came from.
        home_page = next(
            (p for p in pages if p["path"] == "home" and p["description"].strip()),
            None,
        )
        about_page = next(
            (p for p in pages if p["path"].startswith("about") and p["description"].strip()),
            None,
        )
        source_page = home_page or about_page
        if source_page is not None:
            signals.append(Signal.BUSINESS_DESCRIPTION)
            evidence.append(
                Evidence(
                    signal=Signal.BUSINESS_DESCRIPTION,
                    summary=source_page["description"][:400],
                    url=source_page["url"],
                    date=None,
                    source="company",
                )
            )

        combined_text = " ".join(p["body_excerpt"] for p in pages)
        if _FOUNDER_HINTS.search(combined_text) and _TECH_HINTS.search(combined_text):
            signals.append(Signal.FOUNDER_TECHNICAL)

        # PRODUCT_LIST_EMPTY: zero pages with headings indicates a sparse site.
        if not any(p["headings"] for p in pages):
            signals.append(Signal.PRODUCT_LIST_EMPTY)

        # RECENT_PRESS_RELEASE: current year present in any heading.
        current_year = datetime.now(tz=UTC).year
        prev_year = current_year - 1
        year_re = re.compile(rf"\b({current_year}|{prev_year})\b")
        if any(year_re.search(h) for p in pages for h in p["headings"]):
            signals.append(Signal.RECENT_PRESS_RELEASE)

        return CollectorResult(
            name=self.name,
            data={"pages": pages, "page_count": len(pages)},
            signals=signals,
            errors=errors,
            duration_ms=0,
            evidence=evidence,
        )

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

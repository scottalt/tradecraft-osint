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
        base = str(ctx.target.root_url).rstrip("/")

        results = await asyncio.gather(
            *(self._safe(ctx.http.get(f"{base}{p}"), errors, p) for p in _PATHS)
        )

        pages: list[dict[str, Any]] = []
        for path, resp in zip(_PATHS, results, strict=True):
            if resp is None or resp.status_code != 200:
                continue
            tree = HTMLParser(resp.text)
            title_el = tree.css_first("title")
            description_el = tree.css_first('meta[name="description"]')
            headings = [h.text(strip=True) for h in tree.css("h1, h2, h3") if h.text(strip=True)]
            body_text = tree.body.text(strip=True) if tree.body else ""
            pages.append(
                {
                    "path": path.strip("/"),
                    "title": title_el.text(strip=True) if title_el else "",
                    "description": description_el.attributes.get("content", "")
                    if description_el
                    else "",
                    "headings": headings,
                    "body_excerpt": body_text[:1000],
                }
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

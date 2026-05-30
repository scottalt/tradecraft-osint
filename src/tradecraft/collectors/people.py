"""People collector: blog authors only."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable
from typing import Any, ClassVar

from selectolax.parser import HTMLParser

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_BLOG_PATHS = ("/blog", "/engineering", "/engineering-blog", "/eng-blog")
_BYLINE_RE = re.compile(r"by\s+([A-Z][A-Za-z\.\-']+(?:\s+[A-Z][A-Za-z\.\-']+){0,3})", re.IGNORECASE)
_STRONG_BRAND_AUTHOR_THRESHOLD = 3


class PeopleCollector:
    name: ClassVar[str] = "people"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.SWE,
        Role.DEVOPS,
        Role.DATA,
        Role.ENG_LEADERSHIP,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        base = str(ctx.target.root_url).rstrip("/")

        results = await asyncio.gather(
            *(self._safe(ctx.http.get(f"{base}{p}"), errors, p) for p in _BLOG_PATHS)
        )
        authors: list[str] = []
        seen: set[str] = set()
        for resp in results:
            if resp is None or resp.status_code != 200:
                continue
            authors.extend(self._extract_authors(resp.text, seen))

        if len(authors) >= _STRONG_BRAND_AUTHOR_THRESHOLD:
            signals.append(Signal.STRONG_ENG_BRAND)
        else:
            signals.append(Signal.QUIET_ENG_BRAND)

        return CollectorResult(
            name=self.name,
            data={"authors": authors, "author_count": len(authors)},
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

    @staticmethod
    def _extract_authors(html: str, seen: set[str]) -> list[str]:
        tree = HTMLParser(html)
        out: list[str] = []
        # 1. <meta name="author">
        meta = tree.css_first('meta[name="author"]')
        if meta:
            v = meta.attributes.get("content")
            if v and v not in seen:
                seen.add(v)
                out.append(v)
        # 2. byline elements (common class names)
        for sel in (".byline", ".author", ".post-author", "[rel=author]"):
            for el in tree.css(sel):
                t = el.text(strip=True)
                m = _BYLINE_RE.search(t)
                name = m.group(1) if m else t
                if name and name not in seen:
                    seen.add(name)
                    out.append(name)
        return out

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

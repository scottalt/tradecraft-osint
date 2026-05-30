"""News collector: Google News RSS + HN Algolia API."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable
from typing import Any, ClassVar
from urllib.parse import quote_plus

import feedparser  # type: ignore[import-untyped]

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}"
_HN_ALGOLIA = "https://hn.algolia.com/api/v1/search?query={q}&tags=story"

_SIGNAL_PATTERNS: tuple[tuple[Signal, re.Pattern[str]], ...] = (
    (
        Signal.RECENT_SECURITY_INCIDENT,
        re.compile(
            r"\b(breach|incident|hacked|ransomware|leak|cyber.{0,8}attack|data\s+exposure)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Signal.RECENT_LAYOFFS,
        re.compile(
            r"\b(layoffs?|workforce\s+reduction|headcount\s+cut|staff\s+cuts?)\b", re.IGNORECASE
        ),
    ),
    (
        Signal.RECENT_FUNDING,
        re.compile(
            r"\b(raises?|series\s+[a-z]|funding\s+round|valuation|venture\s+round|seed\s+round)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Signal.RECENT_LEADERSHIP_CHANGE,
        re.compile(
            r"\b(appoints?|named\s+(?:ceo|cfo|ciso|cto|coo)|new\s+ceo|steps\s+down|departs|joins\s+as\s+ceo)\b",
            re.IGNORECASE,
        ),
    ),
)


class NewsCollector:
    name: ClassVar[str] = "news"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
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
        q = quote_plus(ctx.target.company_name)

        rss_text, hn_json = await asyncio.gather(
            self._safe(ctx.http.get(_GOOGLE_NEWS_RSS.format(q=q)), errors, "rss"),
            self._safe(ctx.http.get(_HN_ALGOLIA.format(q=q)), errors, "hn"),
        )

        items: list[dict[str, Any]] = []
        if rss_text is not None:
            try:
                parsed = feedparser.parse(rss_text.text)
                for entry in parsed.entries[:50]:
                    items.append(
                        {
                            "title": getattr(entry, "title", ""),
                            "url": getattr(entry, "link", ""),
                            "published": getattr(entry, "published", ""),
                            "source": "google_news",
                        }
                    )
            except Exception as exc:
                errors.append(
                    CollectorError(
                        stage="rss_parse",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )

        if hn_json is not None and hn_json.status_code == 200:
            try:
                hits = hn_json.json().get("hits", [])
                for h in hits[:50]:
                    items.append(
                        {
                            "title": h.get("title", ""),
                            "url": h.get("url", ""),
                            "published": h.get("created_at", ""),
                            "source": "hn",
                        }
                    )
            except Exception as exc:
                errors.append(
                    CollectorError(
                        stage="hn_parse",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )

        text_blob = " | ".join(i["title"] for i in items)
        for sig, pattern in _SIGNAL_PATTERNS:
            if pattern.search(text_blob):
                signals.append(sig)

        return CollectorResult(
            name=self.name,
            data={"items": items, "headline_count": len(items)},
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

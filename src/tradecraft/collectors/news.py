"""News collector: Google News RSS + HN Algolia API."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from urllib.parse import quote_plus

import feedparser  # type: ignore[import-untyped]

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Evidence,
    Role,
    Signal,
)

_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}"
_HN_ALGOLIA = "https://hn.algolia.com/api/v1/search?query={q}&tags=story"

NEWS_MAX_AGE_DAYS = 365

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


def _parse_date_iso(item: dict[str, Any]) -> str | None:
    """Return ISO YYYY-MM-DD date for an item, or None if unparseable."""
    source = item.get("source", "")
    try:
        if source == "google_news":
            # feedparser gives entry.published_parsed as time.struct_time
            parsed_time = item.get("published_parsed")
            if parsed_time is not None:
                return datetime(*parsed_time[:6], tzinfo=UTC).strftime("%Y-%m-%d")
        if source == "hn":
            # HN Algolia API gives ISO 8601 in "created_at": "2026-03-11T12:00:00.000Z"
            # The item dict is built in run() with key "created_at" mapped from h["created_at"].
            raw = item.get("created_at", "")
            if raw:
                return raw[:10]
    except Exception:
        pass
    return None


def _apply_recency_filter(items: list[dict[str, Any]], today: datetime) -> list[dict[str, Any]]:
    """Drop items whose parsed date is older than NEWS_MAX_AGE_DAYS. Keep undated items.

    The cutoff is computed as midnight UTC on (today - NEWS_MAX_AGE_DAYS) so that
    an item dated exactly on the cutoff day is kept (inclusive boundary).
    """
    cutoff = datetime(today.year, today.month, today.day, tzinfo=UTC) - timedelta(
        days=NEWS_MAX_AGE_DAYS
    )
    result = []
    for item in items:
        date_iso = item.get("date_iso")
        if date_iso is None:
            # fail open: keep items with unparseable dates
            result.append(item)
        else:
            try:
                item_date = datetime.fromisoformat(date_iso).replace(tzinfo=UTC)
                if item_date >= cutoff:
                    result.append(item)
            except Exception:
                # unparseable → keep
                result.append(item)
    return result


def _apply_relevance_filter(items: list[dict[str, Any]], company_name: str) -> list[dict[str, Any]]:
    """Drop items whose title contains none of the company name tokens (len >= 3)."""
    tokens = [t.lower() for t in company_name.split() if len(t) >= 3]
    if not tokens:
        # no usable tokens → keep all
        return items
    result = []
    for item in items:
        title_lower = item.get("title", "").lower()
        if any(re.search(rf"\b{re.escape(tok)}\b", title_lower) for tok in tokens):
            result.append(item)
    return result


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
        evidence: list[Evidence] = []
        q = quote_plus(ctx.target.company_name)

        rss_text, hn_json = await asyncio.gather(
            self._safe(ctx.http.get(_GOOGLE_NEWS_RSS.format(q=q)), errors, "rss"),
            self._safe(ctx.http.get(_HN_ALGOLIA.format(q=q)), errors, "hn"),
        )

        raw_items: list[dict[str, Any]] = []
        if rss_text is not None:
            try:
                parsed = feedparser.parse(rss_text.text)
                for entry in parsed.entries[:50]:
                    item: dict[str, Any] = {
                        "title": getattr(entry, "title", ""),
                        "url": getattr(entry, "link", ""),
                        "published": getattr(entry, "published", ""),
                        "published_parsed": getattr(entry, "published_parsed", None),
                        "source": "google_news",
                    }
                    item["date_iso"] = _parse_date_iso(item)
                    raw_items.append(item)
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
                    item = {
                        "title": h.get("title", ""),
                        "url": h.get("url", ""),
                        # "created_at" is the HN Algolia field name; used by _parse_date_iso
                        "created_at": h.get("created_at", ""),
                        "source": "hn",
                    }
                    item["date_iso"] = _parse_date_iso(item)
                    raw_items.append(item)
            except Exception as exc:
                errors.append(
                    CollectorError(
                        stage="hn_parse",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )

        today = datetime.now(tz=UTC)
        items = _apply_recency_filter(raw_items, today)
        items = _apply_relevance_filter(items, ctx.target.company_name)

        # Fire signals and attach evidence: one Evidence per signal (most-recent match)
        for sig, pattern in _SIGNAL_PATTERNS:
            matching = [i for i in items if pattern.search(i.get("title", ""))]
            if not matching:
                continue
            signals.append(sig)
            # Pick most-recent item: dated items sorted by date desc, then undated
            dated = sorted(
                [i for i in matching if i.get("date_iso") is not None],
                key=lambda i: i["date_iso"],  # type: ignore[arg-type]
                reverse=True,
            )
            undated = [i for i in matching if i.get("date_iso") is None]
            best = dated[0] if dated else undated[0]
            source_name = "news.google" if best.get("source") == "google_news" else "hn"
            evidence.append(
                Evidence(
                    signal=sig,
                    summary=best.get("title", ""),
                    url=best.get("url") or None,
                    date=best.get("date_iso"),
                    source=source_name,
                )
            )

        # Strip internal fields before returning in data
        public_items = [
            {k: v for k, v in i.items() if k not in ("published_parsed", "date_iso")} for i in items
        ]

        return CollectorResult(
            name=self.name,
            data={"items": public_items, "headline_count": len(public_items)},
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

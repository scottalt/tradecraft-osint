"""Business collector: SEC EDGAR ticker lookup + Wikipedia infobox."""

from __future__ import annotations

import asyncio
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

_SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/{slug}"


class BusinessCollector:
    name: ClassVar[str] = "business"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.ENG_LEADERSHIP,
        Role.GENERIC,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        data: dict[str, Any] = {"ticker": None, "wikipedia": None}

        company_lc = ctx.target.company_name.lower()
        wiki_slug = ctx.target.company_name.replace(" ", "_")

        sec_resp, wiki_resp = await asyncio.gather(
            self._safe(ctx.http.get(_SEC_TICKERS_URL), errors, "sec"),
            self._safe(ctx.http.get(_WIKIPEDIA_URL.format(slug=wiki_slug)), errors, "wiki"),
        )

        if sec_resp is not None and sec_resp.status_code == 200:
            try:
                tickers = sec_resp.json()
                for entry in tickers.values():
                    title = str(entry.get("title", "")).lower()
                    if company_lc in title:
                        data["ticker"] = entry.get("ticker")
                        data["cik"] = entry.get("cik_str")
                        signals.append(Signal.PUBLIC_COMPANY)
                        break
            except Exception as exc:
                errors.append(
                    CollectorError(
                        stage="sec_parse",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )

        if wiki_resp is not None and wiki_resp.status_code == 200:
            try:
                tree = HTMLParser(wiki_resp.text)
                infobox = tree.css_first("table.infobox")
                if infobox:
                    fields: dict[str, str] = {}
                    for row in infobox.css("tr"):
                        th = row.css_first("th")
                        td = row.css_first("td")
                        if th and td:
                            fields[th.text(strip=True)] = td.text(strip=True)
                    data["wikipedia"] = fields
                    signals.append(Signal.WIKIPEDIA_INFOBOX_PRESENT)
            except Exception as exc:
                errors.append(
                    CollectorError(
                        stage="wiki_parse",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )

        return CollectorResult(
            name=self.name,
            data=data,
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

"""Business collector: SEC EDGAR ticker lookup + Wikipedia infobox."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any, ClassVar

from selectolax.parser import HTMLParser, Node

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Evidence,
    Role,
    Signal,
)

_SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/{slug}"


class BusinessCollector:
    name: ClassVar[str] = "business"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.ENG_LEADERSHIP,
        Role.GENERIC,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        evidence: list[Evidence] = []
        data: dict[str, Any] = {"ticker": None, "wikipedia": None}

        company_lc = ctx.target.company_name.lower()
        wiki_slug = ctx.target.company_name.replace(" ", "_")
        wiki_url = _WIKIPEDIA_URL.format(slug=wiki_slug)

        sec_resp, wiki_resp = await asyncio.gather(
            self._safe(ctx.http.get(_SEC_TICKERS_URL), errors, "sec"),
            self._safe(ctx.http.get(wiki_url), errors, "wiki"),
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
                self._parse_wikipedia(wiki_resp.text, wiki_url, data, signals, evidence)
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
            evidence=evidence,
        )

    @staticmethod
    def _parse_wikipedia(
        html: str,
        wiki_url: str,
        data: dict[str, Any],
        signals: list[Signal],
        evidence: list[Evidence],
    ) -> None:
        tree = HTMLParser(html)
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

            industry = next(
                (v for k, v in fields.items() if k.lower() == "industry" and v.strip()),
                None,
            )
            if industry:
                data["industry"] = industry
                signals.append(Signal.INDUSTRY_IDENTIFIED)
                evidence.append(
                    Evidence(
                        signal=Signal.INDUSTRY_IDENTIFIED,
                        summary=industry,
                        url=wiki_url,
                        date=None,
                        source="wikipedia",
                    )
                )

        # Lead paragraph: first real-prose <p> outside any table/infobox.
        lead = BusinessCollector._first_lead_paragraph(tree)
        if lead:
            description = lead[:400]
            data["description"] = description
            signals.append(Signal.BUSINESS_DESCRIPTION)
            evidence.append(
                Evidence(
                    signal=Signal.BUSINESS_DESCRIPTION,
                    summary=description,
                    url=wiki_url,
                    date=None,
                    source="wikipedia",
                )
            )

    @staticmethod
    def _first_lead_paragraph(tree: HTMLParser) -> str | None:
        """First real-prose <p> (>60 chars) that is not inside a table/infobox.

        Prefers Wikipedia's ``.mw-parser-output`` content container so infobox
        <p> cells (Products/Services etc.) cannot masquerade as the lead.
        """
        container = tree.css_first(".mw-parser-output")
        candidates = container.css("p") if container else tree.css("p")
        for p in candidates:
            if BusinessCollector._has_table_ancestor(p):
                continue
            text = p.text(strip=True)
            if len(text) > 60:
                return text
        return None

    @staticmethod
    def _has_table_ancestor(node: Node, max_depth: int = 8) -> bool:
        parent = node.parent
        depth = 0
        while parent is not None and depth < max_depth:
            if parent.tag == "table":
                return True
            parent = parent.parent
            depth += 1
        return False

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

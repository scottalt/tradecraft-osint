"""M&A collector: parent/subsidiaries via Wikipedia infobox."""

from __future__ import annotations

from typing import Any, ClassVar

from selectolax.parser import HTMLParser

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/{slug}"
_FREQUENT_ACQUIRER_THRESHOLD = 5


class MaCollector:
    name: ClassVar[str] = "ma"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.SWE,
        Role.ENG_LEADERSHIP,
        Role.GENERIC,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        wiki_slug = ctx.target.company_name.replace(" ", "_")
        data: dict[str, Any] = {"parent": None, "subsidiaries": []}

        try:
            resp = await ctx.http.get(_WIKIPEDIA_URL.format(slug=wiki_slug))
        except Exception as exc:  # noqa: BLE001, RUF100
            errors.append(
                CollectorError(
                    stage="fetch",
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )
            return CollectorResult(
                name=self.name, data=data, signals=signals, errors=errors, duration_ms=0
            )

        if resp.status_code != 200:
            return CollectorResult(
                name=self.name, data=data, signals=signals, errors=errors, duration_ms=0
            )

        tree = HTMLParser(resp.text)
        infobox = tree.css_first("table.infobox")
        if not infobox:
            return CollectorResult(
                name=self.name, data=data, signals=signals, errors=errors, duration_ms=0
            )

        for row in infobox.css("tr"):
            th = row.css_first("th")
            td = row.css_first("td")
            if not (th and td):
                continue
            label = th.text(strip=True).lower()
            value = td.text(separator=" ", strip=True)
            if label == "parent" and value:
                data["parent"] = value
                signals.append(Signal.SUBSIDIARY_OF)
            elif label == "subsidiaries" and value:
                subs = [s.strip() for s in value.split(",") if s.strip()]
                data["subsidiaries"] = subs
                if len(subs) >= _FREQUENT_ACQUIRER_THRESHOLD:
                    signals.append(Signal.M_A_FREQUENT_ACQUIRER)

        return CollectorResult(
            name=self.name,
            data=data,
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

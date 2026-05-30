"""Breaches collector: HIBP free domain endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_HIBP_DOMAIN_ENDPOINT = "https://haveibeenpwned.com/api/v3/breaches"
_RECENT_THRESHOLD_DAYS = 24 * 30  # 24 months, approximated


class BreachesCollector:
    name: ClassVar[str] = "breaches"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY, Role.ENG_LEADERSHIP}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        host = ctx.target.root_url.host or ""

        breaches_raw: list[dict[str, Any]] = []
        try:
            resp = await ctx.http.get(f"{_HIBP_DOMAIN_ENDPOINT}?domain={host}")
            if resp.status_code == 200:
                breaches_raw = resp.json()
            elif resp.status_code != 404:
                errors.append(
                    CollectorError(
                        stage="hibp",
                        message=f"unexpected status {resp.status_code}",
                        exception_type="HTTPStatusError",
                    )
                )
        except Exception as exc:
            errors.append(
                CollectorError(
                    stage="hibp",
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )

        breaches = [
            {
                "name": b.get("Name"),
                "title": b.get("Title"),
                "domain": b.get("Domain"),
                "date": b.get("BreachDate"),
                "pwn_count": b.get("PwnCount"),
                "data_classes": b.get("DataClasses", []),
                "is_verified": b.get("IsVerified", False),
            }
            for b in breaches_raw
        ]
        breaches.sort(key=lambda b: b.get("date") or "", reverse=True)

        if breaches:
            signals.append(Signal.BREACH_HISTORY)
            cutoff = datetime.now(tz=UTC) - timedelta(days=_RECENT_THRESHOLD_DAYS)
            for b in breaches:
                date_str = b.get("date")
                if not date_str:
                    continue
                try:
                    bd = datetime.fromisoformat(str(date_str)).replace(tzinfo=UTC)
                except ValueError:
                    continue
                if bd >= cutoff:
                    signals.append(Signal.BREACH_RECENT)
                    break

        return CollectorResult(
            name=self.name,
            data={"breaches": breaches, "host": host},
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

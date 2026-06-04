"""Business collector: SEC EDGAR ticker lookup + Wikipedia infobox."""

from __future__ import annotations

import asyncio
import re
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

# Infobox row labels (lowercased) that carry leadership / founder names.
_LEADERSHIP_LABELS = frozenset({"key people", "founder", "founders", "founded by", "ceo"})
# "Name (Role)" pairs, e.g. "Matthew Prince (Co-founder, chairman & CEO)".
# Name: 2-4 Title-Case tokens (allowing ., ', -). Role: anything inside parens.
_LEADERSHIP_PAIR_RE = re.compile(r"([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){1,3})\s*\(([^)]+)\)")
# A bare Title-Case full name (used for "Founder" cells that are just names).
# Matched as exactly two Title-Case tokens (first + last) so a run of several
# founders glued by whitespace ("Larry Page Sergey Brin") splits into separate
# people rather than one over-long name. Optional trailing initials/suffixes
# (a third Title-Case token) are intentionally not greedily absorbed.
_BARE_NAME_RE = re.compile(r"\b([A-Z][\w.'-]+\s+[A-Z][\w.'-]+)\b")
_MAX_LEADERSHIP = 6


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
                    fields[BusinessCollector._clean_text(th)] = BusinessCollector._clean_text(td)
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

            BusinessCollector._extract_leadership(fields, wiki_url, data, signals, evidence)

        # Lead paragraphs: concatenate the first up-to-3 real-prose <p> blocks
        # outside any table/infobox. Capturing more than just the first paragraph
        # lets deeper-sector signals (gov/defense, etc.) surface for the
        # score-based industry matcher, which only sees this summary + the
        # homepage meta description.
        lead = BusinessCollector._lead_paragraphs(tree)
        if lead:
            description = lead[:600]
            # Append infobox Products / Services / Areas served field values (if
            # present) so they also feed the classification text. These are
            # sector-rich (e.g. Palantir's "government agencies, defense,
            # intelligence, law enforcement") yet absent from the Wikipedia lead.
            infobox_extras = BusinessCollector._infobox_classification_extras(data)
            if infobox_extras:
                description = f"{description} {infobox_extras}".strip()[:760]
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

    # Infobox fields whose values describe what the company does / who it serves;
    # appended to the description so they feed the industry classifier.
    _INFOBOX_CLASSIFICATION_FIELDS: ClassVar[tuple[str, ...]] = (
        "products",
        "services",
        "areas served",
    )

    @staticmethod
    def _infobox_classification_extras(data: dict[str, Any]) -> str:
        """Join infobox Products / Services / Areas served values into one string."""
        fields = data.get("wikipedia")
        if not isinstance(fields, dict):
            return ""
        wanted = BusinessCollector._INFOBOX_CLASSIFICATION_FIELDS
        parts = [
            v.strip()
            for k, v in fields.items()
            if k.lower() in wanted and isinstance(v, str) and v.strip()
        ]
        return " ".join(parts)

    @staticmethod
    def _extract_leadership(
        fields: dict[str, str],
        wiki_url: str,
        data: dict[str, Any],
        signals: list[Signal],
        evidence: list[Evidence],
    ) -> None:
        """Extract leadership/founder people from infobox rows.

        Looks at rows labelled "Key people"/"Founder(s)"/"Founded by"/"CEO".
        Parses ``Name (Role)`` pairs; for a label that is itself a role
        ("CEO"/"Founder") whose cell is just names, pairs each bare name with
        that label. Conservative: only Title-Case multi-word names are kept.
        """
        people: list[dict[str, str]] = []
        seen: set[str] = set()

        def _add(name: str, role: str) -> None:
            name = name.strip()
            role = role.strip()
            key = name.lower()
            if not name or key in seen:
                return
            seen.add(key)
            people.append({"name": name, "role": role})

        for label, value in fields.items():
            if label.lower() not in _LEADERSHIP_LABELS or not value.strip():
                continue
            pairs = _LEADERSHIP_PAIR_RE.findall(value)
            if pairs:
                for name, role in pairs:
                    _add(name, role)
            else:
                # No "(Role)" parens — treat the label as the role and pull
                # bare Title-Case names (e.g. a "Founder" cell that is just
                # "John Smith Jane Doe"). Skip the catch-all "Key people" label
                # here, since without parens it is too ambiguous to attribute.
                bare_role = label.strip()
                if bare_role.lower() == "key people":
                    continue
                for name in _BARE_NAME_RE.findall(value):
                    _add(name, bare_role.title())
            if len(people) >= _MAX_LEADERSHIP:
                break

        people = people[:_MAX_LEADERSHIP]
        if not people:
            return

        data["leadership"] = people
        signals.append(Signal.LEADERSHIP_IDENTIFIED)
        evidence.append(
            Evidence(
                signal=Signal.LEADERSHIP_IDENTIFIED,
                summary=BusinessCollector._leadership_summary(people),
                url=wiki_url,
                date=None,
                source="wikipedia",
            )
        )

    @staticmethod
    def _leadership_summary(people: list[dict[str, str]]) -> str:
        """Concise phrase: the CEO (if any) plus 1-2 founders."""
        ceo = next(
            (
                p
                for p in people
                if "ceo" in p["role"].lower() or "chief executive" in p["role"].lower()
            ),
            None,
        )
        founders = [p for p in people if "founder" in p["role"].lower()]

        parts: list[str] = []
        if ceo is not None:
            parts.append(f"CEO {ceo['name']}")
        for f in founders:
            if ceo is not None and f["name"] == ceo["name"]:
                continue
            parts.append(f"co-founder {f['name']}")
            if len(parts) >= 3:
                break
        if not parts:
            # No CEO/founder role keywords — name the first 1-2 people.
            for p in people[:2]:
                parts.append(f"{p['name']} ({p['role']})" if p["role"] else p["name"])
        return "; ".join(parts)

    @staticmethod
    def _lead_paragraphs(tree: HTMLParser, max_paras: int = 3) -> str | None:
        """Up to ``max_paras`` real-prose <p> blocks (>40 chars each), joined.

        Each candidate must be outside any table/infobox. Prefers Wikipedia's
        ``.mw-parser-output`` content container so infobox <p> cells
        (Products/Services etc.) cannot masquerade as the lead.
        """
        container = tree.css_first(".mw-parser-output")
        candidates = container.css("p") if container else tree.css("p")
        collected: list[str] = []
        for p in candidates:
            if BusinessCollector._has_table_ancestor(p):
                continue
            text = BusinessCollector._clean_text(p)
            if len(text) > 40:
                collected.append(text)
                if len(collected) >= max_paras:
                    break
        if not collected:
            return None
        return " ".join(collected)

    @staticmethod
    def _clean_text(node: Node) -> str:
        """Extract node text with spaces preserved between inline elements.

        ``selectolax`` ``.text(strip=True)`` concatenates inline children with no
        separator, producing glued words like ``cloudcybersecurity`` or
        ``inSan Francisco`` that break ``\\bword\\b`` keyword matching. Using a
        space separator and collapsing whitespace runs keeps words standalone.

        Wikipedia infobox cells and lead paragraphs sometimes contain embedded
        ``<style>`` or ``<script>`` blocks whose raw CSS/JS text would otherwise
        be included in the extracted string.  We decompose those descendant nodes
        before calling ``.text()`` so their content is never returned.
        """
        for junk in node.css("style, script"):
            junk.decompose()
        return re.sub(r"\s+", " ", node.text(separator=" ", strip=True)).strip()

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

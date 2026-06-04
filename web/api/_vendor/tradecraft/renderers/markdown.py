"""Markdown renderer: the human-readable dossier."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

from tradecraft import __version__
from tradecraft.models import Findings, Question


def render_markdown(findings: Findings, questions: Sequence[Question]) -> str:
    target = findings.target
    parts: list[str] = []
    parts.append(f"# {target.company_name}")
    parts.append("")
    parts.append(_snapshot_section(findings))
    parts.append(_footprint_section(findings))
    parts.append(_vendor_section(findings))
    parts.append(_company_section(findings))
    parts.append(_job_section(findings))
    parts.append(_github_section(findings))
    parts.append(_news_section(findings))
    parts.append(_breaches_section(findings))
    parts.append(_business_section(findings))
    parts.append(_leadership_section(findings))
    parts.append(_ma_section(findings))
    parts.append(_people_section(findings))
    parts.append(_questions_section(questions))
    parts.append(_collection_notes(findings))
    return "\n".join(parts).rstrip() + "\n"


def _snapshot_section(findings: Findings) -> str:
    target = findings.target
    lines = ["## Snapshot", ""]
    lines.append(f"- **URL:** {target.root_url}")
    if target.job_url:
        lines.append(f"- **Job listing:** {target.job_url}")
    lines.append(f"- **Role focus:** `{target.role.value}`")
    lines.append(
        f"- **Generated:** {datetime.now(tz=UTC).isoformat(timespec='seconds')} "
        f"by tradecraft {__version__}"
    )
    lines.append("")
    return "\n".join(lines)


def _footprint_section(findings: Findings) -> str:
    result = findings.collector("footprint")
    lines = [
        "## Web & infrastructure footprint",
        "",
        "What an external observer can learn from public infrastructure signals.",
        "",
    ]
    if result is None:
        lines.append("_No footprint data collected._")
        lines.append("")
        return "\n".join(lines)
    data = result.data
    lines.append(f"- **Host:** `{data.get('host', '?')!s}`")
    server = data.get("server")
    if server:
        lines.append(f"- **Server header:** `{server!s}`")
    powered_by = data.get("x_powered_by")
    if powered_by:
        lines.append(f"- **X-Powered-By:** `{powered_by!s}`")
    headers = cast(dict[str, object], data.get("security_headers") or {})
    if headers:
        lines.append(
            "- **Security headers present:** " + ", ".join(f"`{k}`" for k in sorted(headers))
        )
    else:
        lines.append("- **Security headers present:** _none_")

    observed = cast(dict[str, object], data.get("observed_tech") or {})
    if observed:
        lines.append("")
        lines.append("### Technology observed")
        lines.append("")
        for label, key in (
            ("CDN / WAF", "cdn_waf"),
            ("CMS / platform", "cms"),
            ("Server", "server"),
        ):
            items = cast(list[object], observed.get(key) or [])
            if items:
                lines.append(f"- **{label}:** " + ", ".join(f"`{i}`" for i in items))

    subs = cast(list[object], data.get("subdomains") or [])
    if subs:
        lines.append("")
        lines.append("### Subdomains observed in public CT logs")
        lines.append("")
        for s in subs:
            lines.append(f"- `{s}`")

    signals = result.signals
    if signals:
        lines.append("")
        lines.append("### Signals")
        lines.append("")
        for s in signals:
            lines.append(f"- `{s.value}`")
    lines.append("")
    return "\n".join(lines)


def _vendor_section(findings: Findings) -> str:
    result = findings.collector("footprint")
    vendors = cast(list[object], (result.data.get("vendors") if result else None) or [])
    if not vendors:
        return ""
    lines = [
        "## Vendor relationships (from DNS)",
        "",
        "Third-party SaaS / email vendors fingerprinted from public DNS (TXT/SPF/MX).",
        "",
    ]
    for v in vendors:
        lines.append(f"- {v!s}")
    lines.append("")
    return "\n".join(lines)


def _company_section(findings: Findings) -> str:
    result = findings.collector("company")
    lines = ["## Company profile", ""]
    if result is None or not result.data.get("pages"):
        lines.append("_No company profile data collected._")
        lines.append("")
        return "\n".join(lines)
    for page in cast(list[object], result.data["pages"]):
        p = cast(dict[str, object], page)
        if p.get("title"):
            lines.append(f"### `{p['path']}` — {p['title']}")
        if p.get("description"):
            lines.append(f"> {p['description']}")
        if p.get("headings"):
            for h in cast(list[object], p["headings"])[:8]:
                lines.append(f"- {h}")
        lines.append("")
    return "\n".join(lines)


def _job_section(findings: Findings) -> str:
    result = findings.collector("job")
    lines = ["## Role-fit signals (from JD)", ""]
    if result is None or not result.data:
        lines.append("_No job URL supplied or no signals extracted._")
        lines.append("")
        return "\n".join(lines)
    if result.data.get("title"):
        lines.append(f"- **Title:** {result.data['title']!s}")
    if result.data.get("stack"):
        stack = cast(list[object], result.data["stack"])
        lines.append(f"- **Stack mentioned:** {', '.join(str(s) for s in stack)}")
    if result.data.get("url"):
        lines.append(f"- **URL:** {result.data['url']!s}")
    lines.append("")
    return "\n".join(lines)


def _github_section(findings: Findings) -> str:
    result = findings.collector("github")
    lines = ["## GitHub presence", ""]
    if result is None or not result.data.get("org"):
        lines.append("_No public GitHub org found, or collector skipped._")
        lines.append("")
        return "\n".join(lines)
    org = cast(dict[str, object], result.data["org"])
    lines.append(f"- **Org:** `{org.get('login')!s}`")
    lines.append(f"- **Repos visible:** {result.data.get('repo_count', 0)!s}")
    langs = cast(dict[str, object], result.data.get("languages") or {})
    if langs:
        top = ", ".join(f"{k} ({v})" for k, v in list(langs.items())[:6])
        lines.append(f"- **Languages:** {top}")
    top_repos = cast(list[object], result.data.get("top_repos") or [])
    if top_repos:
        lines.append("")
        lines.append("### Top repos by stars")
        lines.append("")
        for r in top_repos[:5]:
            repo = cast(dict[str, object], r)
            lines.append(
                f"- `{repo.get('name')!s}` ({repo.get('language', '?')!s})"
                f" — {repo.get('stars', 0)!s} stars"
            )
    lines.append("")
    return "\n".join(lines)


def _news_section(findings: Findings) -> str:
    result = findings.collector("news")
    lines = ["## News & timeline", ""]
    if result is None or not result.data.get("items"):
        lines.append("_No news items found._")
        lines.append("")
        return "\n".join(lines)
    for item in cast(list[object], result.data["items"])[:15]:
        it = cast(dict[str, object], item)
        title = it.get("title") or "(untitled)"
        source = it.get("source") or ""
        when = it.get("published") or ""
        lines.append(f"- **{title!s}** _({source!s}, {when!s})_")
    lines.append("")
    return "\n".join(lines)


def _breaches_section(findings: Findings) -> str:
    result = findings.collector("breaches")
    lines = ["## Breach history", ""]
    if result is None or not result.data.get("breaches"):
        lines.append("_No public breach records for this domain._")
        lines.append("")
        return "\n".join(lines)
    for b in cast(list[object], result.data["breaches"])[:10]:
        breach = cast(dict[str, object], b)
        date = breach.get("date") or "?"
        name = breach.get("name") or "(unknown)"
        pwn = breach.get("pwn_count")
        classes = ", ".join(
            str(c) for c in cast(list[object], breach.get("data_classes") or [])[:5]
        )
        line = f"- **{name!s}** ({date!s})"
        if pwn:
            line += f" — {int(cast(int, pwn)):,} affected"
        if classes:
            line += f"; classes: {classes}"
        lines.append(line)
    lines.append("")
    return "\n".join(lines)


def _business_section(findings: Findings) -> str:
    result = findings.collector("business")
    lines = ["## Business & financial signals", ""]
    if result is None or not (
        result.data.get("ticker")
        or result.data.get("wikipedia")
        or result.data.get("industry")
        or result.data.get("description")
    ):
        lines.append("_No business signals collected._")
        lines.append("")
        return "\n".join(lines)
    if result.data.get("ticker"):
        lines.append(f"- **Public company:** ticker `{result.data['ticker']!s}`")
    if result.data.get("industry"):
        lines.append(f"- **Industry:** {result.data['industry']!s}")
    wiki = cast(dict[str, object], result.data.get("wikipedia") or {})
    if wiki:
        for key in ("Founded", "Headquarters", "Industry", "Employees", "Revenue"):
            if key in wiki:
                lines.append(f"- **{key}:** {wiki[key]!s}")
    if result.data.get("description"):
        lines.append("")
        lines.append(f"> {result.data['description']!s}")
    lines.append("")
    return "\n".join(lines)


def _leadership_section(findings: Findings) -> str:
    result = findings.collector("business")
    people = cast(list[object], (result.data.get("leadership") if result else None) or [])
    if not people:
        return ""
    lines = ["## Key people", ""]
    for p in people:
        person = cast(dict[str, object], p)
        name = person.get("name") or "(unknown)"
        role = person.get("role")
        lines.append(f"- {name!s} — {role!s}" if role else f"- {name!s}")
    lines.append("")
    return "\n".join(lines)


def _ma_section(findings: Findings) -> str:
    result = findings.collector("ma")
    lines = ["## Mergers & acquisitions", ""]
    if result is None or (not result.data.get("parent") and not result.data.get("subsidiaries")):
        lines.append("_No M&A data collected._")
        lines.append("")
        return "\n".join(lines)
    if result.data.get("parent"):
        lines.append(f"- **Parent:** {result.data['parent']!s}")
    subs = cast(list[object], result.data.get("subsidiaries") or [])
    if subs:
        names = ", ".join(str(s) for s in subs[:8])
        suffix = "…" if len(subs) > 8 else ""
        lines.append(f"- **Subsidiaries ({len(subs)}):** {names}{suffix}")
    lines.append("")
    return "\n".join(lines)


def _people_section(findings: Findings) -> str:
    result = findings.collector("people")
    lines = ["## People", ""]
    if result is None or not result.data.get("authors"):
        lines.append("_No publicly identifiable engineering content authors._")
        lines.append("")
        return "\n".join(lines)
    authors = cast(list[object], result.data["authors"])
    lines.append(f"- **Blog authors identified:** {len(authors)}")
    for a in authors[:10]:
        lines.append(f"  - {a!s}")
    lines.append("")
    return "\n".join(lines)


_DENSITY_NOTE = (
    "_Limited recent public material was found for this target. For richer, "
    "news- and M&A-anchored questions, add a job listing URL or run the full "
    "CLI (which includes news, breaches, and M&A collectors)._"
)


def _questions_section(questions: Sequence[Question]) -> str:
    lines = [
        "## Questions to ask",
        "",
        "Evidence-cited prompts to take into the interview. Starred items are the "
        "highest-confidence picks.",
        "",
    ]
    if not questions:
        lines.append(
            "_No heuristic-driven questions generated. Add more collector "
            "coverage or run with `--ai` to deepen this section._"
        )
        lines.append("")
        return "\n".join(lines)

    heuristic = [q for q in questions if q.source_collector != "ai"]
    ai = [q for q in questions if q.source_collector == "ai"]

    if heuristic and not any(q.evidence for q in heuristic):
        lines.append(_DENSITY_NOTE)
        lines.append("")

    starred = [q for q in heuristic if q.is_starred]
    rest = [q for q in heuristic if not q.is_starred]
    if starred:
        lines.append("### Top picks")
        lines.append("")
        for q in starred:
            lines.append(_format_question(q))
        lines.append("")
    if rest:
        lines.append("### Further questions")
        lines.append("")
        for q in rest:
            lines.append(_format_question(q))
        lines.append("")
    if ai:
        lines.append("### Deep dive (AI)")
        lines.append("")
        for q in ai:
            lines.append(_format_question(q))
        lines.append("")
    return "\n".join(lines)


def _format_question(q: Question) -> str:
    tags = " ".join(f"`{r.value}`" for r in sorted(q.role_tags))
    if q.evidence is not None:
        ev = q.evidence
        label = ev.source
        if ev.date:
            label = f"{label} · {ev.date}"
        evidence = f"[{label}]({ev.url})" if ev.url else label
    elif q.evidence_signal is not None:
        evidence = f"`{q.evidence_signal.value}` from `{q.source_collector}`"
    else:
        evidence = f"AI deep-dive (`{q.source_collector}`)"
    return (
        f"- **{q.text}**  \n"
        f"  _confidence:_ `{q.confidence}` · _evidence:_ {evidence} · _roles:_ {tags}"
    )


def _collection_notes(findings: Findings) -> str:
    lines = ["## Collection notes", ""]
    for r in findings.results:
        lines.append(f"- **{r.name}** — {r.duration_ms} ms")
        for err in r.errors:
            lines.append(f"  - error in `{err.stage}`: {err.message}")
    lines.append("")
    return "\n".join(lines)

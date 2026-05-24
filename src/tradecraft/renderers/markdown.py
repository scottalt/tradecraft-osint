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
            "- **Security headers present:** "
            + ", ".join(f"`{k}`" for k in sorted(headers))
        )
    else:
        lines.append("- **Security headers present:** _none_")

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

    starred = [q for q in questions if q.is_starred]
    rest = [q for q in questions if not q.is_starred]
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
    return "\n".join(lines)


def _format_question(q: Question) -> str:
    tags = " ".join(f"`{r.value}`" for r in sorted(q.role_tags))
    return (
        f"- **{q.text}**  \n"
        f"  _confidence:_ `{q.confidence}` · _evidence:_ `{q.evidence_signal.value}` "
        f"from `{q.source_collector}` · _roles:_ {tags}"
    )


def _collection_notes(findings: Findings) -> str:
    lines = ["## Collection notes", ""]
    for r in findings.results:
        lines.append(f"- **{r.name}** — {r.duration_ms} ms")
        for err in r.errors:
            lines.append(f"  - error in `{err.stage}`: {err.message}")
    lines.append("")
    return "\n".join(lines)

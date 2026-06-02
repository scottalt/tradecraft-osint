"""Standalone questions renderer: just the questions section, ready to print."""

from __future__ import annotations

from collections.abc import Sequence

from tradecraft.models import Question

_DENSITY_NOTE = (
    "_Limited recent public material was found for this target. For richer, "
    "news- and M&A-anchored questions, add a job listing URL or run the full "
    "CLI (which includes news, breaches, and M&A collectors)._"
)


def render_questions(questions: Sequence[Question], *, company_name: str) -> str:
    lines = [f"# Questions to ask {company_name}", ""]
    if not questions:
        lines.append("_No heuristic-driven questions generated for this run._")
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
        lines.append("## Top picks")
        lines.append("")
        for q in starred:
            lines.append(_format(q))
        lines.append("")
    if rest:
        lines.append("## Further questions")
        lines.append("")
        for q in rest:
            lines.append(_format(q))
        lines.append("")
    if ai:
        lines.append("## Deep dive (AI)")
        lines.append("")
        for q in ai:
            lines.append(_format(q))
        lines.append("")
    return "\n".join(lines)


def _format(q: Question) -> str:
    tags = " ".join(f"`{r.value}`" for r in sorted(q.role_tags))
    if q.evidence is not None:
        ev = q.evidence
        label = ev.source
        if ev.date:
            label = f"{label} · {ev.date}"
        source_part = f"[{label}]({ev.url})" if ev.url else label
        evidence = f"_source:_ {source_part}"
    elif q.evidence_signal is not None:
        evidence = f"`{q.evidence_signal.value}` from `{q.source_collector}`"
    else:
        evidence = f"AI deep-dive (`{q.source_collector}`)"
    return (
        f"- **{q.text}**  \n"
        f"  _confidence:_ `{q.confidence}` · _evidence:_ {evidence} · _roles:_ {tags}"
    )

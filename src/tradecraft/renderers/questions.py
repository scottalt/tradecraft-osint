"""Standalone questions renderer: just the questions section, ready to print."""

from __future__ import annotations

from collections.abc import Sequence

from tradecraft.models import Question


def render_questions(questions: Sequence[Question], *, company_name: str) -> str:
    lines = [f"# Questions to ask {company_name}", ""]
    if not questions:
        lines.append("_No heuristic-driven questions generated for this run._")
        lines.append("")
        return "\n".join(lines)

    starred = [q for q in questions if q.is_starred]
    rest = [q for q in questions if not q.is_starred]

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
    return "\n".join(lines)


def _format(q: Question) -> str:
    tags = " ".join(f"`{r.value}`" for r in sorted(q.role_tags))
    evidence = q.evidence_signal.value if q.evidence_signal is not None else "n/a"
    return (
        f"- **{q.text}**  \n"
        f"  _confidence:_ `{q.confidence}` · _evidence:_ "
        f"`{evidence}` from `{q.source_collector}` · _roles:_ {tags}"
    )

"""Heuristic question generator: signal-driven, role-aware, deterministic."""

from __future__ import annotations

from collections.abc import Sequence

from tradecraft.analyzers.templates import TEMPLATES, QuestionTemplate
from tradecraft.models import Findings, Question

_CONFIDENCE_ORDER = {"high": 0, "med": 1, "low": 2}


def generate_questions(
    findings: Findings,
    *,
    templates: Sequence[QuestionTemplate] = TEMPLATES,
    star_top_n: int = 3,
) -> list[Question]:
    """Produce questions for every template whose signals are present AND whose roles include findings.target.role."""
    present = findings.all_signals
    role = findings.target.role
    seen_ids: set[str] = set()
    fired: list[Question] = []
    for tmpl in templates:
        if tmpl.id in seen_ids:
            continue
        if role not in tmpl.roles:
            continue
        triggers = [s for s in tmpl.signals if s in present]
        if not triggers:
            continue
        seen_ids.add(tmpl.id)
        fired.append(
            Question(
                text=tmpl.text,
                confidence=tmpl.confidence,
                role_tags=set(tmpl.roles),
                evidence_signal=triggers[0],
                source_collector=tmpl.source,
            )
        )
    fired.sort(key=lambda q: _CONFIDENCE_ORDER[q.confidence])
    for q in fired[:star_top_n]:
        q.is_starred = True
    return fired

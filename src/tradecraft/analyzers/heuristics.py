"""Heuristic question generator: signal-driven, role-aware, deterministic."""

from __future__ import annotations

from collections.abc import Sequence

from tradecraft.analyzers.contextual import contextual_questions
from tradecraft.analyzers.templates import TEMPLATES, QuestionTemplate
from tradecraft.models import Findings, Question

_CONFIDENCE_ORDER = {"high": 0, "med": 1, "low": 2}

_SOURCE_LABELS = {
    "news.google": "Google News",
    "hn": "Hacker News",
    "job": "the job listing",
    "wikipedia": "Wikipedia",
    "company": "their site",
}


def generate_questions(
    findings: Findings,
    *,
    templates: Sequence[QuestionTemplate] = TEMPLATES,
    star_top_n: int = 3,
) -> list[Question]:
    """Produce questions for every template whose signals are present AND whose roles include findings.target.role.

    Evidence-aware: templates marked ``needs_evidence`` only fire when matching
    Evidence exists (never as boilerplate), and evidence-backed questions sort
    ahead of evidence-free ones.
    """
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

        ev = None
        if tmpl.needs_evidence:
            for s in triggers:
                ev = findings.evidence_for(s)
                if ev is not None:
                    break
            if ev is None:
                # No evidence backing this template — skip rather than emit boilerplate.
                continue
            fmt = {
                "summary": ev.summary,
                "source": _SOURCE_LABELS.get(ev.source, ev.source),
                "date": ev.date or "recently",
            }
            text = tmpl.text.format(**fmt)
        else:
            text = tmpl.text

        seen_ids.add(tmpl.id)
        fired.append(
            Question(
                text=text,
                confidence=tmpl.confidence,
                role_tags=set(tmpl.roles),
                evidence_signal=triggers[0],
                source_collector=tmpl.source,
                evidence=ev,
            )
        )
    # Append evidence-backed contextual questions (industry + JD-tech), deduping
    # against template-driven questions by exact text.
    seen_texts = {q.text for q in fired}
    for cq in contextual_questions(findings):
        if cq.text in seen_texts:
            continue
        seen_texts.add(cq.text)
        fired.append(cq)

    fired.sort(key=lambda q: (0 if q.evidence is not None else 1, _CONFIDENCE_ORDER[q.confidence]))
    for q in fired[:star_top_n]:
        q.is_starred = True
    return fired

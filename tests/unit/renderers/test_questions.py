"""Tests for tradecraft.renderers.questions."""

from __future__ import annotations

from tradecraft.models import Question, Role, Signal
from tradecraft.renderers.questions import render_questions


def test_renders_starred_first_then_rest() -> None:
    qs = [
        Question(
            text="Top",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.OPEN_STAGING_SUBDOMAIN,
            source_collector="footprint",
            is_starred=True,
        ),
        Question(
            text="Other",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=False,
        ),
    ]
    out = render_questions(qs, company_name="Acme")
    assert "# Questions to ask Acme" in out
    assert out.index("Top") < out.index("Other")


def test_empty_questions_renders_placeholder() -> None:
    out = render_questions([], company_name="Acme")
    assert "No heuristic-driven questions" in out


def test_questions_standalone_has_deep_dive_subsection() -> None:
    qs = [
        Question(
            text="Heur",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=False,
        ),
        Question(
            text="AI question",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=None,
            source_collector="ai",
        ),
    ]
    out = render_questions(qs, company_name="Acme")
    assert "## Deep dive (AI)" in out
    assert "AI question" in out

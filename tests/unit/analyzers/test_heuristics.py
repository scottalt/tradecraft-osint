"""Tests for tradecraft.analyzers.heuristics."""

from __future__ import annotations

from tradecraft.analyzers.heuristics import generate_questions
from tradecraft.models import (
    CollectorResult,
    Findings,
    Role,
    Signal,
    Target,
)


def _findings_with(signals: list[Signal], role: Role = Role.CYBERSECURITY) -> Findings:
    target = Target(company_name="Acme", root_url="https://acme.com", role=role)
    result = CollectorResult(name="footprint", data={}, signals=signals, errors=[], duration_ms=0)
    return Findings(target=target, results=[result])


def test_no_signals_yields_no_questions() -> None:
    f = _findings_with([])
    questions = generate_questions(f)
    assert questions == []


def test_single_signal_fires_matching_template() -> None:
    f = _findings_with([Signal.MISSING_CSP])
    questions = generate_questions(f)
    assert questions
    assert any("Content-Security-Policy" in q.text for q in questions)


def test_role_filter_excludes_irrelevant_templates() -> None:
    # Stack mismatch is tagged for swe/devops/cybersecurity, NOT for data
    f = _findings_with([Signal.LANGUAGES_MISMATCH_JOB], role=Role.DATA)
    questions = generate_questions(f)
    assert all("stack that doesn't dominate" not in q.text for q in questions)


def test_data_role_still_gets_relevant_templates() -> None:
    f = _findings_with([Signal.RECENT_FUNDING], role=Role.DATA)
    questions = generate_questions(f)
    assert any("funding" in q.text for q in questions)


def test_top_3_are_starred() -> None:
    f = _findings_with(
        [
            Signal.OPEN_STAGING_SUBDOMAIN,
            Signal.MISSING_CSP,
            Signal.MISSING_HSTS,
            Signal.RECENT_FUNDING,
        ]
    )
    questions = generate_questions(f)
    starred = [q for q in questions if q.is_starred]
    assert len(starred) <= 3


def test_no_duplicate_templates_when_multiple_signals_share_one_template() -> None:
    """Currently each template has a single signal in tuple; this test guards
    against a future tuple-of-signals template producing two Question objects."""
    f = _findings_with([Signal.MISSING_CSP, Signal.MISSING_CSP])
    questions = generate_questions(f)
    csp_qs = [q for q in questions if "Content-Security-Policy" in q.text]
    assert len(csp_qs) == 1


def test_question_evidence_signal_matches_trigger() -> None:
    f = _findings_with([Signal.MISSING_CSP])
    questions = generate_questions(f)
    assert questions, "expected at least one question for MISSING_CSP"
    assert all(q.evidence_signal == Signal.MISSING_CSP for q in questions)
    assert all(q.source_collector == "footprint" for q in questions)

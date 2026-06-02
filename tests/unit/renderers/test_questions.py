"""Tests for tradecraft.renderers.questions."""

from __future__ import annotations

from tradecraft.models import Evidence, Question, Role, Signal
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


# ---------------------------------------------------------------------------
# Evidence footnote rendering
# ---------------------------------------------------------------------------


def _make_heuristic_q(*, evidence: Evidence | None = None, starred: bool = False) -> Question:
    return Question(
        text="How do you handle this?",
        confidence="med",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=Signal.RECENT_FUNDING,
        source_collector="news",
        is_starred=starred,
        evidence=evidence,
    )


def test_evidence_with_url_renders_markdown_link() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $200M",
        url="https://news.example.com/article",
        date="2026-03-11",
        source="news.google",
    )
    q = _make_heuristic_q(evidence=ev)
    out = render_questions([q], company_name="Acme")
    assert "[news.google · 2026-03-11](https://news.example.com/article)" in out


def test_evidence_with_url_no_date_renders_link_without_date() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $200M",
        url="https://news.example.com/article",
        date=None,
        source="news.google",
    )
    q = _make_heuristic_q(evidence=ev)
    out = render_questions([q], company_name="Acme")
    assert "[news.google](https://news.example.com/article)" in out
    # The link label should just be "news.google" with no date appended
    assert "[news.google ·" not in out


def test_evidence_no_url_renders_source_and_date_no_link() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $200M",
        url=None,
        date="2026-03-11",
        source="hn",
    )
    q = _make_heuristic_q(evidence=ev)
    out = render_questions([q], company_name="Acme")
    # plain text, no markdown link syntax
    assert "hn · 2026-03-11" in out
    assert "](http" not in out


def test_evidence_none_heuristic_question_shows_signal_from_collector() -> None:
    """Regression: evidence=None heuristic question keeps old footnote format."""
    q = Question(
        text="Check your CSP headers",
        confidence="high",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=Signal.MISSING_CSP,
        source_collector="footprint",
        is_starred=False,
        evidence=None,
    )
    out = render_questions([q], company_name="Acme")
    assert "`missing_csp` from `footprint`" in out


def test_ai_question_shows_ai_deep_dive_footnote() -> None:
    """Regression: AI question (evidence_signal=None, source_collector='ai') keeps AI footnote."""
    q = Question(
        text="Deep AI question",
        confidence="high",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=None,
        source_collector="ai",
        is_starred=False,
        evidence=None,
    )
    out = render_questions([q], company_name="Acme")
    assert "AI deep-dive (`ai`)" in out


# ---------------------------------------------------------------------------
# Content-density floor note
# ---------------------------------------------------------------------------


def test_density_note_shown_when_all_heuristic_questions_have_no_evidence() -> None:
    q = _make_heuristic_q(evidence=None)
    out = render_questions([q], company_name="Acme")
    assert "Limited recent public material" in out


def test_density_note_not_shown_when_at_least_one_evidence_backed_question() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $200M",
        url="https://example.com",
        date="2026-01-01",
        source="news.google",
    )
    q_with_ev = _make_heuristic_q(evidence=ev)
    q_no_ev = _make_heuristic_q(evidence=None)
    out = render_questions([q_with_ev, q_no_ev], company_name="Acme")
    assert "Limited recent public material" not in out


def test_density_note_not_shown_for_empty_question_list() -> None:
    out = render_questions([], company_name="Acme")
    assert "Limited recent public material" not in out
    assert "No heuristic-driven questions" in out


def test_density_note_not_shown_when_only_ai_questions_present() -> None:
    """Only AI questions (no heuristic questions) — note must NOT appear."""
    q = Question(
        text="AI only question",
        confidence="high",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=None,
        source_collector="ai",
        is_starred=False,
        evidence=None,
    )
    out = render_questions([q], company_name="Acme")
    assert "Limited recent public material" not in out

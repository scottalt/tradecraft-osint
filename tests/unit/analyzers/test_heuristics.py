"""Tests for tradecraft.analyzers.heuristics."""

from __future__ import annotations

from tradecraft.analyzers.heuristics import generate_questions
from tradecraft.analyzers.templates import TEMPLATES, QuestionTemplate
from tradecraft.models import (
    CollectorResult,
    Evidence,
    Findings,
    Question,
    Role,
    Signal,
    Target,
)


def _findings_with(
    signals: list[Signal],
    role: Role = Role.CYBERSECURITY,
    evidence: list[Evidence] | None = None,
) -> Findings:
    target = Target(company_name="Acme", root_url="https://acme.com", role=role)
    result = CollectorResult(
        name="footprint",
        data={},
        signals=signals,
        errors=[],
        duration_ms=0,
        evidence=evidence or [],
    )
    return Findings(target=target, results=[result])


def test_no_signals_yields_no_questions() -> None:
    f = _findings_with([])
    questions = generate_questions(f)
    assert questions == []


def test_single_signal_fires_matching_template() -> None:
    f = _findings_with([Signal.OSS_FORWARD_CULTURE])
    questions = generate_questions(f)
    assert questions
    assert any("public GitHub footprint" in q.text for q in questions)


def test_role_filter_excludes_irrelevant_templates() -> None:
    # Stack mismatch is tagged for swe/devops/cybersecurity, NOT for data
    f = _findings_with([Signal.LANGUAGES_MISMATCH_JOB], role=Role.DATA)
    questions = generate_questions(f)
    assert all("stack that doesn't dominate" not in q.text for q in questions)


def test_data_role_still_gets_relevant_templates() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $40M Series B",
        date="2026-04-01",
        source="news.google",
    )
    f = _findings_with([Signal.RECENT_FUNDING], role=Role.DATA, evidence=[ev])
    questions = generate_questions(f)
    assert any("Series B" in q.text for q in questions)


def test_top_3_are_starred() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $40M Series B",
        date="2026-04-01",
        source="news.google",
    )
    f = _findings_with(
        [
            Signal.OSS_FORWARD_CULTURE,
            Signal.STRONG_ENG_BRAND,
            Signal.PRODUCT_LIST_EMPTY,
            Signal.RECENT_FUNDING,
        ],
        evidence=[ev],
    )
    questions = generate_questions(f)
    starred = [q for q in questions if q.is_starred]
    assert len(questions) >= 3  # precondition: enough templates fired
    assert len(starred) == 3


def test_no_duplicate_templates_when_multiple_signals_share_one_template() -> None:
    """Currently each template has a single signal in tuple; this test guards
    against a future tuple-of-signals template producing two Question objects."""
    f = _findings_with([Signal.OSS_FORWARD_CULTURE, Signal.OSS_FORWARD_CULTURE])
    questions = generate_questions(f)
    oss_qs = [q for q in questions if "public GitHub footprint" in q.text]
    assert len(oss_qs) == 1


def test_question_evidence_signal_matches_trigger() -> None:
    f = _findings_with([Signal.OSS_FORWARD_CULTURE])
    questions = generate_questions(f)
    assert questions, "expected at least one question for OSS_FORWARD_CULTURE"
    assert all(q.evidence_signal == Signal.OSS_FORWARD_CULTURE for q in questions)
    assert all(q.source_collector == "github" for q in questions)


# ---- evidence-aware behavior ----


def _news_template() -> QuestionTemplate:
    return QuestionTemplate(
        id="t.news",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles=frozenset({Role.CYBERSECURITY}),
        text="I saw '{summary}' (via {source}, {date}). What changed since?",
        confidence="med",
        source="news",
        needs_evidence=True,
    )


def test_needs_evidence_template_skipped_when_no_evidence() -> None:
    """Signal present but NO matching evidence -> template does not fire."""
    tmpl = _news_template()
    # Signal in findings, but evidence list empty.
    f = _findings_with([Signal.RECENT_SECURITY_INCIDENT], evidence=[])
    questions = generate_questions(f, templates=(tmpl,))
    assert questions == []


def test_needs_evidence_template_fires_and_renders_evidence() -> None:
    tmpl = _news_template()
    ev = Evidence(
        signal=Signal.RECENT_SECURITY_INCIDENT,
        summary="Acme discloses S3 bucket breach",
        date="2026-03-11",
        source="news.google",
    )
    f = _findings_with([Signal.RECENT_SECURITY_INCIDENT], evidence=[ev])
    questions = generate_questions(f, templates=(tmpl,))
    assert len(questions) == 1
    q = questions[0]
    assert "Acme discloses S3 bucket breach" in q.text  # summary
    assert "2026-03-11" in q.text  # date
    assert "Google News" in q.text  # friendly source label
    assert q.evidence == ev


def test_date_none_renders_recently_not_literal_none() -> None:
    tmpl = _news_template()
    ev = Evidence(
        signal=Signal.RECENT_SECURITY_INCIDENT,
        summary="Acme had an incident",
        date=None,
        source="news.google",
    )
    f = _findings_with([Signal.RECENT_SECURITY_INCIDENT], evidence=[ev])
    questions = generate_questions(f, templates=(tmpl,))
    assert len(questions) == 1
    assert "recently" in questions[0].text
    assert "None" not in questions[0].text


def test_evidence_backed_question_sorts_above_no_evidence_med() -> None:
    """A med + evidence question outranks a med no-evidence question."""
    ev_tmpl = _news_template()  # med, needs_evidence
    config_tmpl = QuestionTemplate(
        id="t.config",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY}),
        text="No CSP — deliberate?",
        confidence="med",
        source="footprint",
    )
    ev = Evidence(
        signal=Signal.RECENT_SECURITY_INCIDENT,
        summary="Acme breach headline",
        date="2026-03-11",
        source="news.google",
    )
    f = _findings_with(
        [Signal.RECENT_SECURITY_INCIDENT, Signal.MISSING_CSP],
        evidence=[ev],
    )
    questions = generate_questions(f, templates=(config_tmpl, ev_tmpl))
    assert len(questions) == 2
    # Evidence-backed med question must come first.
    assert questions[0].evidence is not None
    assert "Acme breach headline" in questions[0].text
    assert questions[1].evidence is None


def test_no_evidence_high_beats_no_evidence_med() -> None:
    high_tmpl = QuestionTemplate(
        id="t.high",
        signals=(Signal.MISSING_HSTS,),
        roles=frozenset({Role.CYBERSECURITY}),
        text="HSTS high",
        confidence="high",
        source="footprint",
    )
    med_tmpl = QuestionTemplate(
        id="t.med",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY}),
        text="CSP med",
        confidence="med",
        source="footprint",
    )
    f = _findings_with([Signal.MISSING_CSP, Signal.MISSING_HSTS])
    questions = generate_questions(f, templates=(med_tmpl, high_tmpl))
    assert [q.text for q in questions] == ["HSTS high", "CSP med"]


def test_real_headline_med_outranks_config_med() -> None:
    """A real-headline (evidence) med question outranks a config med."""
    ev_tmpl = _news_template()  # med + evidence
    config_tmpl = QuestionTemplate(
        id="t.config2",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY}),
        text="config med",
        confidence="med",
        source="footprint",
    )
    ev = Evidence(
        signal=Signal.RECENT_SECURITY_INCIDENT,
        summary="real headline",
        date="2026-01-01",
        source="hn",
    )
    f = _findings_with([Signal.RECENT_SECURITY_INCIDENT, Signal.MISSING_CSP], evidence=[ev])
    questions = generate_questions(f, templates=(config_tmpl, ev_tmpl))
    assert "real headline" in questions[0].text
    assert questions[0].confidence == "med"
    assert "Hacker News" in questions[0].text


def test_recent_news_evidence_renders_headline() -> None:
    """A Findings carrying RECENT_NEWS evidence yields a question whose text
    contains the real headline (the news.recent catch-all template)."""
    ev = Evidence(
        signal=Signal.RECENT_NEWS,
        summary="Acme acquires Foobar Inc to expand platform",
        date="2026-05-20",
        source="news.google",
    )
    f = _findings_with([Signal.RECENT_NEWS], evidence=[ev])
    questions = generate_questions(f)
    assert questions
    q = next(
        (q for q in questions if "Acme acquires Foobar Inc to expand platform" in q.text), None
    )
    assert q is not None
    assert "2026-05-20" in q.text
    assert "Google News" in q.text
    assert q.evidence == ev


def test_ma_subsidiary_renders_summary_and_source_no_date() -> None:
    """ma.subsidiary cites {summary} + {source} (provenance) but NOT a misleading
    date — the parent/subsidiary relationship is structural, not a recent event."""
    tmpl = next(t for t in TEMPLATES if t.id == "ma.subsidiary")
    ev = Evidence(
        signal=Signal.SUBSIDIARY_OF,
        summary="Acme is a subsidiary of Globex",
        date=None,
        source="wikipedia",
    )
    f = _findings_with([Signal.SUBSIDIARY_OF], evidence=[ev])
    questions = generate_questions(f, templates=(tmpl,))
    assert len(questions) == 1
    text = questions[0].text
    assert "Acme is a subsidiary of Globex" in text  # summary
    assert "Wikipedia" in text  # friendly source label for provenance
    assert "recently" not in text  # no misleading date fallback


def test_integration_contextual_and_news_lead_no_header_questions() -> None:
    """generate_questions surfaces evidence-backed contextual + news questions at
    the top, and never emits removed security-header questions."""
    target = Target(company_name="Acme", root_url="https://acme.com", role=Role.CYBERSECURITY)
    business = CollectorResult(
        name="business",
        data={},
        signals=[Signal.INDUSTRY_IDENTIFIED],
        errors=[],
        duration_ms=0,
        evidence=[
            Evidence(
                signal=Signal.INDUSTRY_IDENTIFIED,
                summary="Cloud computing, Content delivery network, Cybersecurity",
                source="wikipedia",
            )
        ],
    )
    news = CollectorResult(
        name="news",
        data={},
        signals=[Signal.RECENT_FUNDING],
        errors=[],
        duration_ms=0,
        evidence=[
            Evidence(
                signal=Signal.RECENT_FUNDING,
                summary="Acme raises $40M Series B",
                date="2026-04-01",
                source="news.google",
            )
        ],
    )
    # also include a footprint signal that should NOT produce a header question
    footprint = CollectorResult(
        name="footprint",
        data={},
        signals=[Signal.MISSING_CSP, Signal.MISSING_HSTS],
        errors=[],
        duration_ms=0,
        evidence=[],
    )
    f = Findings(target=target, results=[business, news, footprint])
    questions = generate_questions(f)

    assert questions
    # No removed security-header questions.
    for q in questions:
        assert "Content-Security-Policy" not in q.text
        assert "Strict-Transport-Security" not in q.text
    # Evidence-backed questions lead.
    assert questions[0].evidence is not None
    # Contextual industry + news both present.
    assert any("infrastructure, cloud & security" in q.text for q in questions)
    assert any("Series B" in q.text for q in questions)
    # Dedupe: no duplicate text.
    texts = [q.text for q in questions]
    assert len(texts) == len(set(texts))


def test_question_model_accepts_evidence() -> None:
    """Sanity: Question carries the Evidence object through."""
    ev = Evidence(signal=Signal.JOB_STACK_LISTED, summary="Go, Kubernetes", source="job")
    q = Question(
        text="x",
        confidence="med",
        role_tags={Role.SWE},
        source_collector="job",
        evidence=ev,
    )
    assert q.evidence is ev

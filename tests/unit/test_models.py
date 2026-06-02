"""Tests for tradecraft.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Evidence,
    Findings,
    Question,
    Role,
    Signal,
    Target,
)


class TestTarget:
    def test_minimal_target(self) -> None:
        t = Target(company_name="Acme", root_url="https://acme.com")
        assert t.company_name == "Acme"
        assert str(t.root_url) == "https://acme.com/"
        assert t.job_url is None
        assert t.role == Role.CYBERSECURITY

    def test_target_with_job_and_role(self) -> None:
        t = Target(
            company_name="Acme",
            root_url="https://acme.com",
            job_url="https://acme.com/jobs/1",
            role=Role.SWE,
        )
        assert str(t.job_url) == "https://acme.com/jobs/1"
        assert t.role == Role.SWE

    def test_target_rejects_non_url(self) -> None:
        with pytest.raises(ValidationError):
            Target(company_name="Acme", root_url="not-a-url")

    def test_target_company_slug(self) -> None:
        t = Target(company_name="Acme Corp, Inc.", root_url="https://acme.com")
        assert t.company_slug == "acme-corp-inc"


class TestSignal:
    def test_signal_is_enum(self) -> None:
        assert Signal.M_A_RECENT.value == "m_a_recent"
        assert Signal.MISSING_CSP.value == "missing_csp"


class TestQuestion:
    def test_question_minimal(self) -> None:
        q = Question(
            text="Why?",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
        )
        assert q.confidence == "high"
        assert q.is_starred is False

    def test_question_starred_flag(self) -> None:
        q = Question(
            text="Why?",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=True,
        )
        assert q.is_starred is True


class TestCollectorResult:
    def test_result_with_data(self) -> None:
        r = CollectorResult(
            name="footprint",
            data={"subdomains": ["a.acme.com"]},
            signals=[Signal.OPEN_STAGING_SUBDOMAIN],
            errors=[],
            duration_ms=42,
        )
        assert r.signals == [Signal.OPEN_STAGING_SUBDOMAIN]
        assert r.duration_ms == 42

    def test_result_with_error(self) -> None:
        err = CollectorError(stage="dns", message="timeout")
        r = CollectorResult(name="footprint", data={}, signals=[], errors=[err], duration_ms=10)
        assert r.errors[0].stage == "dns"


class TestFindings:
    def test_findings_collects_results(self) -> None:
        target = Target(company_name="Acme", root_url="https://acme.com")
        r1 = CollectorResult(
            name="footprint", data={}, signals=[Signal.MISSING_CSP], errors=[], duration_ms=10
        )
        f = Findings(target=target, results=[r1])
        assert Signal.MISSING_CSP in f.all_signals
        assert f.collector("footprint") is r1
        assert f.collector("nope") is None


class TestEvidence:
    def test_evidence_required_and_optional_fields(self) -> None:
        e = Evidence(
            signal=Signal.RECENT_FUNDING,
            summary="Acme raises $50M Series B",
            source="news.google",
        )
        assert e.signal == Signal.RECENT_FUNDING
        assert e.summary == "Acme raises $50M Series B"
        assert e.source == "news.google"
        assert e.url is None
        assert e.date is None

    def test_evidence_with_all_fields(self) -> None:
        e = Evidence(
            signal=Signal.M_A_RECENT,
            summary="Acme acquires WidgetCo",
            url="https://techcrunch.com/acme-widgetco",
            date="2026-03-11",
            source="news.google",
        )
        assert e.url == "https://techcrunch.com/acme-widgetco"
        assert e.date == "2026-03-11"

    def test_date_accepts_valid_iso(self) -> None:
        e = Evidence(
            signal=Signal.RECENT_FUNDING,
            summary="Valid date",
            source="news.google",
            date="2026-03-11",
        )
        assert e.date == "2026-03-11"

    def test_date_rejects_natural_language(self) -> None:
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            Evidence(
                signal=Signal.RECENT_FUNDING,
                summary="Bad date",
                source="news.google",
                date="March 2026",
            )

    def test_date_rejects_us_format(self) -> None:
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            Evidence(
                signal=Signal.RECENT_FUNDING,
                summary="Bad date",
                source="news.google",
                date="11/03/2026",
            )

    def test_date_none_is_allowed(self) -> None:
        e = Evidence(signal=Signal.RECENT_FUNDING, summary="No date", source="company")
        assert e.date is None


class TestCollectorResultEvidence:
    def test_default_evidence_is_empty_list(self) -> None:
        r = CollectorResult(name="news", data={}, signals=[], errors=[], duration_ms=5)
        assert r.evidence == []

    def test_evidence_field_accepts_evidence_objects(self) -> None:
        e = Evidence(signal=Signal.RECENT_FUNDING, summary="Series B", source="news.google")
        r = CollectorResult(
            name="news",
            data={},
            signals=[Signal.RECENT_FUNDING],
            errors=[],
            duration_ms=5,
            evidence=[e],
        )
        assert len(r.evidence) == 1
        assert r.evidence[0].signal == Signal.RECENT_FUNDING


class TestQuestionEvidence:
    def test_question_evidence_field_defaults_none(self) -> None:
        q = Question(
            text="Why?",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
        )
        assert q.evidence is None

    def test_question_evidence_field_accepts_evidence(self) -> None:
        e = Evidence(signal=Signal.MISSING_CSP, summary="No CSP header found", source="footprint")
        q = Question(
            text="Why no CSP?",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            evidence=e,
        )
        assert q.evidence is not None
        assert q.evidence.signal == Signal.MISSING_CSP


class TestFindingsEvidenceFor:
    def _target(self) -> Target:
        return Target(company_name="Acme", root_url="https://acme.com")

    def test_returns_none_when_no_evidence(self) -> None:
        r = CollectorResult(name="news", data={}, signals=[], errors=[], duration_ms=5)
        f = Findings(target=self._target(), results=[r])
        assert f.evidence_for(Signal.RECENT_FUNDING) is None

    def test_returns_none_when_no_matching_signal(self) -> None:
        e = Evidence(signal=Signal.RECENT_LAYOFFS, summary="Layoffs at Acme", source="news.google")
        r = CollectorResult(
            name="news",
            data={},
            signals=[Signal.RECENT_LAYOFFS],
            errors=[],
            duration_ms=5,
            evidence=[e],
        )
        f = Findings(target=self._target(), results=[r])
        assert f.evidence_for(Signal.RECENT_FUNDING) is None

    def test_returns_single_match(self) -> None:
        e = Evidence(signal=Signal.RECENT_FUNDING, summary="Acme raises $50M", source="news.google")
        r = CollectorResult(
            name="news",
            data={},
            signals=[Signal.RECENT_FUNDING],
            errors=[],
            duration_ms=5,
            evidence=[e],
        )
        f = Findings(target=self._target(), results=[r])
        result = f.evidence_for(Signal.RECENT_FUNDING)
        assert result is e

    def test_returns_most_recent_by_iso_date(self) -> None:
        e_old = Evidence(
            signal=Signal.RECENT_FUNDING,
            summary="Old funding",
            source="news.google",
            date="2025-01-01",
        )
        e_new = Evidence(
            signal=Signal.RECENT_FUNDING,
            summary="New funding",
            source="news.google",
            date="2026-03-11",
        )
        r1 = CollectorResult(
            name="news1", data={}, signals=[], errors=[], duration_ms=5, evidence=[e_old]
        )
        r2 = CollectorResult(
            name="news2", data={}, signals=[], errors=[], duration_ms=5, evidence=[e_new]
        )
        f = Findings(target=self._target(), results=[r1, r2])
        assert f.evidence_for(Signal.RECENT_FUNDING) is e_new

    def test_prefers_dated_over_undated(self) -> None:
        e_undated = Evidence(
            signal=Signal.RECENT_FUNDING, summary="Undated funding", source="company"
        )
        e_dated = Evidence(
            signal=Signal.RECENT_FUNDING,
            summary="Dated funding",
            source="news.google",
            date="2026-01-01",
        )
        r = CollectorResult(
            name="news",
            data={},
            signals=[],
            errors=[],
            duration_ms=5,
            evidence=[e_undated, e_dated],
        )
        f = Findings(target=self._target(), results=[r])
        assert f.evidence_for(Signal.RECENT_FUNDING) is e_dated

    def test_falls_back_to_first_match_when_all_undated(self) -> None:
        e1 = Evidence(signal=Signal.RECENT_FUNDING, summary="First match", source="company")
        e2 = Evidence(signal=Signal.RECENT_FUNDING, summary="Second match", source="hn")
        r = CollectorResult(
            name="news", data={}, signals=[], errors=[], duration_ms=5, evidence=[e1, e2]
        )
        f = Findings(target=self._target(), results=[r])
        assert f.evidence_for(Signal.RECENT_FUNDING) is e1

    def test_tie_break_by_url_is_deterministic(self) -> None:
        """Same date → url tie-break; result must not depend on insertion order."""
        e_alpha = Evidence(
            signal=Signal.RECENT_FUNDING,
            summary="Alpha source",
            source="news.google",
            date="2026-03-11",
            url="https://alpha.example.com/story",
        )
        e_zebra = Evidence(
            signal=Signal.RECENT_FUNDING,
            summary="Zebra source",
            source="news.google",
            date="2026-03-11",
            url="https://zebra.example.com/story",
        )
        # e_zebra has the lexicographically greater url; it should win in both orderings
        r_order1 = CollectorResult(
            name="news",
            data={},
            signals=[],
            errors=[],
            duration_ms=5,
            evidence=[e_alpha, e_zebra],
        )
        r_order2 = CollectorResult(
            name="news",
            data={},
            signals=[],
            errors=[],
            duration_ms=5,
            evidence=[e_zebra, e_alpha],
        )
        f1 = Findings(target=self._target(), results=[r_order1])
        f2 = Findings(target=self._target(), results=[r_order2])
        result1 = f1.evidence_for(Signal.RECENT_FUNDING)
        result2 = f2.evidence_for(Signal.RECENT_FUNDING)
        # Both must pick the zebra url (lexicographically greater)
        assert result1 is not None and result1.url == "https://zebra.example.com/story"
        assert result2 is not None and result2.url == "https://zebra.example.com/story"

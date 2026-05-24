"""Tests for tradecraft.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tradecraft.models import (
    CollectorError,
    CollectorResult,
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

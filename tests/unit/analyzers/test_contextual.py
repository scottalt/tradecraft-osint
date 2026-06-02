"""Tests for tradecraft.analyzers.contextual."""

from __future__ import annotations

from tradecraft.analyzers.contextual import contextual_questions
from tradecraft.models import (
    CollectorResult,
    Evidence,
    Findings,
    Role,
    Signal,
    Target,
)


def _findings(
    *,
    role: Role = Role.CYBERSECURITY,
    evidence: list[Evidence] | None = None,
    results: list[CollectorResult] | None = None,
) -> Findings:
    target = Target(company_name="Acme", root_url="https://acme.com", role=role)
    if results is None:
        results = [
            CollectorResult(
                name="business",
                data={},
                signals=[],
                errors=[],
                duration_ms=0,
                evidence=evidence or [],
            )
        ]
    return Findings(target=target, results=results)


def _industry_ev(summary: str) -> Evidence:
    return Evidence(
        signal=Signal.INDUSTRY_IDENTIFIED,
        summary=summary,
        url="https://en.wikipedia.org/wiki/Acme",
        source="wikipedia",
    )


def _desc_ev(summary: str) -> Evidence:
    return Evidence(
        signal=Signal.BUSINESS_DESCRIPTION,
        summary=summary,
        url="https://acme.com/about",
        source="company",
    )


# ---- industry classification ----


def test_industry_identified_matches_infra_cloud_security() -> None:
    ev = _industry_ev("Cloud computing, Content delivery network, Cybersecurity")
    qs = contextual_questions(_findings(evidence=[ev]))
    assert len(qs) == 1
    q = qs[0]
    assert "infrastructure, cloud & security" in q.text
    assert "multi-tenant isolation" in q.text  # cyber angle
    assert q.confidence == "high"
    assert q.evidence is ev
    assert q.evidence_signal == Signal.INDUSTRY_IDENTIFIED
    assert q.source_collector == "wikipedia"


def test_business_description_only_matches_fintech() -> None:
    ev = _desc_ev("We build a payments platform for banks and credit unions.")
    qs = contextual_questions(_findings(evidence=[ev]))
    assert len(qs) == 1
    q = qs[0]
    assert "payments & fintech" in q.text
    assert q.evidence is ev
    assert q.evidence_signal == Signal.BUSINESS_DESCRIPTION
    assert q.source_collector == "company"


def test_word_boundary_no_false_match() -> None:
    # "edge" matches infra profile; "knowledge" must NOT falsely match "edge".
    ev = _desc_ev("We are a knowledge management company for florists.")
    qs = contextual_questions(_findings(evidence=[ev]))
    # No profile keyword appears as a standalone word -> generic fallback, not infra.
    assert len(qs) == 1
    assert "infrastructure, cloud & security" not in qs[0].text
    # generic fallback cites the description summary
    assert "knowledge management company" in qs[0].text


def test_edge_does_match_as_standalone_word() -> None:
    ev = _industry_ev("Edge computing and CDN")
    qs = contextual_questions(_findings(evidence=[ev]))
    assert any("infrastructure, cloud & security" in q.text for q in qs)


def test_no_industry_and_no_description_yields_nothing() -> None:
    qs = contextual_questions(_findings(evidence=[]))
    assert qs == []


def test_industry_present_but_unmatched_yields_one_generic_fallback() -> None:
    ev = _industry_ev("Floristry")
    qs = contextual_questions(_findings(evidence=[ev]))
    assert len(qs) == 1
    q = qs[0]
    assert "Floristry" in q.text
    assert q.confidence == "high"
    assert q.evidence is ev
    # cyber phrasing
    assert "security threats are most" in q.text


def test_cap_at_two_industry_questions() -> None:
    # Hits payments & fintech, healthcare, AND e-commerce (3 profiles).
    ev = _desc_ev("A fintech payments and healthcare clinical retail marketplace.")
    qs = contextual_questions(_findings(evidence=[ev]))
    assert len(qs) == 2
    # Preserves table order: payments & fintech, then healthcare.
    assert "payments & fintech" in qs[0].text
    assert "healthcare & life sciences" in qs[1].text


def test_non_cyber_role_uses_generic_angle() -> None:
    ev = _industry_ev("Cloud computing and CDN")
    qs = contextual_questions(_findings(role=Role.SWE, evidence=[ev]))
    assert len(qs) == 1
    q = qs[0]
    assert "what makes" in q.text  # generic phrasing
    assert "multi-tenancy, global scale and latency" in q.text  # generic angle
    assert "how is the security team prioritizing" not in q.text
    assert q.role_tags == {Role.SWE}


def test_industry_preferred_over_description_for_citation() -> None:
    ind = _industry_ev("Cloud computing")
    desc = _desc_ev("payments platform")  # would match fintech if used
    qs = contextual_questions(_findings(evidence=[ind, desc]))
    # both texts are classified together, but citation prefers INDUSTRY_IDENTIFIED
    assert all(q.evidence is ind for q in qs)


def test_all_descriptions_contribute_and_longest_is_cited() -> None:
    """Cloudflare-like regression guard for Fix 1.

    A weak homepage tagline AND a rich Wikipedia description both tagged
    BUSINESS_DESCRIPTION (across two collectors). Classification must aggregate
    BOTH so the rich text's keywords match 'infrastructure, cloud & security'
    (not the generic fallback), and the cited evidence is the longer one.
    """
    weak = Evidence(
        signal=Signal.BUSINESS_DESCRIPTION,
        summary="Welcome to Acme",
        url="https://acme.com",
        source="company",
    )
    rich = Evidence(
        signal=Signal.BUSINESS_DESCRIPTION,
        summary=(
            "Acme provides content delivery network (CDN) services, "
            "cloud cybersecurity, and DDoS mitigation"
        ),
        url="https://en.wikipedia.org/wiki/Acme",
        source="wikipedia",
    )
    results = [
        CollectorResult(
            name="company",
            data={},
            signals=[],
            errors=[],
            duration_ms=0,
            evidence=[weak],
        ),
        CollectorResult(
            name="business",
            data={},
            signals=[],
            errors=[],
            duration_ms=0,
            evidence=[rich],
        ),
    ]
    qs = contextual_questions(_findings(results=results))
    assert qs, "expected at least one industry question"
    assert any("infrastructure, cloud & security" in q.text for q in qs)
    # Cited evidence is the longer (richer) description, never the weak tagline.
    assert all(q.evidence is rich for q in qs)


# ---- JD-tech questions ----


def _job_result(stack: list[str], summary: str) -> CollectorResult:
    return CollectorResult(
        name="job",
        data={"stack": stack, "title": "Senior Security Engineer"},
        signals=[Signal.JOB_STACK_LISTED],
        errors=[],
        duration_ms=0,
        evidence=[
            Evidence(
                signal=Signal.JOB_STACK_LISTED,
                summary=summary,
                url="https://acme.com/jobs/1",
                source="job",
            )
        ],
    )


def test_jobstack_cyber_emits_why_and_capped_tech_angles() -> None:
    job = _job_result(
        ["Go", "Kubernetes", "AWS", "Terraform"],
        "Go, Kubernetes, AWS, Terraform",
    )
    qs = contextual_questions(_findings(role=Role.CYBERSECURITY, results=[job]))
    # 1 "why this stack" + 2 tech angles (capped), priority: Kubernetes, Terraform.
    assert len(qs) == 3
    why = qs[0]
    assert why.text.startswith("The role's stack centers on Go, Kubernetes, AWS, Terraform")
    assert all(q.confidence == "high" for q in qs)
    assert all(q.source_collector == "job" for q in qs)
    assert all(q.evidence is not None and q.evidence.signal == Signal.JOB_STACK_LISTED for q in qs)
    angle_texts = " ".join(q.text for q in qs[1:])
    assert "Kubernetes" in angle_texts
    assert "Terraform" in angle_texts
    # AWS dropped due to cap of 2
    assert "AWS" not in angle_texts


def test_jobstack_non_cyber_only_why_question() -> None:
    job = _job_result(
        ["Go", "Kubernetes", "AWS", "Terraform"],
        "Go, Kubernetes, AWS, Terraform",
    )
    qs = contextual_questions(_findings(role=Role.SWE, results=[job]))
    assert len(qs) == 1
    assert qs[0].text.startswith("The role's stack centers on")


def test_jobstack_cloud_fires_once_with_first_provider() -> None:
    job = _job_result(["AWS", "GCP", "Azure"], "AWS, GCP, Azure")
    qs = contextual_questions(_findings(role=Role.CYBERSECURITY, results=[job]))
    tech_qs = [q for q in qs if q.text.startswith("The JD lists")]
    assert len(tech_qs) == 1
    assert "AWS" in tech_qs[0].text
    assert "cloud security posture" in tech_qs[0].text


def test_jobstack_falls_back_to_summary_when_no_data_stack() -> None:
    job = CollectorResult(
        name="job",
        data={},  # no stack key
        signals=[Signal.JOB_STACK_LISTED],
        errors=[],
        duration_ms=0,
        evidence=[
            Evidence(
                signal=Signal.JOB_STACK_LISTED,
                summary="Kubernetes, Kafka",
                source="job",
            )
        ],
    )
    qs = contextual_questions(_findings(role=Role.CYBERSECURITY, results=[job]))
    # why + Kubernetes + Kafka
    assert len(qs) == 3
    angle_texts = " ".join(q.text for q in qs[1:])
    assert "Kubernetes" in angle_texts
    assert "Kafka" in angle_texts


def test_no_jobstack_evidence_yields_no_jobstack_questions() -> None:
    qs = contextual_questions(_findings(evidence=[]))
    assert qs == []


# ---- investment / asset-management sector + fallback phrasing ----


def test_private_equity_description_matches_investment_profile() -> None:
    desc = (
        "H.I.G. Capital is a leading global alternative investment firm. "
        "The firm was founded in 1993 and is headquartered in Miami."
    )
    qs = contextual_questions(_findings(evidence=[_desc_ev(desc)]))
    texts = [q.text for q in qs]
    assert any("investment & asset management" in t for t in texts)
    assert any("business-email-compromise" in t for t in texts)
    # Must NOT fall through to the generic "You operate in <sentence>" fallback.
    assert not any(t.startswith("You operate in H.I.G.") for t in texts)


def test_generic_fallback_quotes_description_not_jammed_into_sentence() -> None:
    desc = "Acme makes hand-poured artisanal candles for boutique retailers."
    qs = contextual_questions(_findings(evidence=[_desc_ev(desc)]))
    assert len(qs) == 1
    text = qs[0].text
    # The grammatical-break bug: a full sentence after "You operate in".
    assert "You operate in Acme makes" not in text
    assert text.startswith("Your public profile describes the company as")
    assert desc in text


def test_generic_fallback_with_industry_label_uses_you_operate_in() -> None:
    # A clean Wikipedia industry label still reads naturally.
    qs = contextual_questions(_findings(evidence=[_industry_ev("Floristry")]))
    assert len(qs) == 1
    assert qs[0].text.startswith("You operate in Floristry —")

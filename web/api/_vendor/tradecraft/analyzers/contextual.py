"""Contextual question generator.

Produces high-value, evidence-cited interview questions from:

(a) the company's industry / business description (``INDUSTRY_IDENTIFIED`` /
    ``BUSINESS_DESCRIPTION`` signals), mapped to sector-specific threat / engineering
    angles, and
(b) the JD's tech stack (``JOB_STACK_LISTED``), with pointed questions about
    specific high-signal technologies (Kubernetes, Terraform, cloud, Kafka).

These questions are evidence-backed and ``confidence="high"`` so they sort to the
top alongside news questions. This module supersedes the old generic
security-header recon templates as *interview questions*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tradecraft.models import Evidence, Findings, Question, Role, Signal


@dataclass(frozen=True)
class IndustryProfile:
    label: str
    keywords: frozenset[str]
    cyber: str
    generic: str


# Order matters: matched profiles preserve this order and are capped at 2.
_INDUSTRY_PROFILES: tuple[IndustryProfile, ...] = (
    IndustryProfile(
        label="payments & fintech",
        keywords=frozenset(
            {
                "payment",
                "payments",
                "fintech",
                "bank",
                "banking",
                "financial",
                "finance",
                "lending",
                "loan",
                "trading",
                "brokerage",
                "crypto",
                "cryptocurrency",
                "blockchain",
                "wallet",
                "card",
                "money",
                "remittance",
                "neobank",
                "insurance",
                "insurtech",
            }
        ),
        cyber=(
            "PCI-DSS scope and segmentation, real-time fraud detection, "
            "and protecting payment and ledger flows"
        ),
        generic="real-time transaction integrity, regulatory constraints, and fraud at scale",
    ),
    IndustryProfile(
        label="investment & asset management",
        keywords=frozenset(
            {
                "investment",
                "private equity",
                "venture capital",
                "asset management",
                "asset manager",
                "hedge fund",
                "wealth management",
                "alternative investment",
                "private capital",
                "portfolio company",
            }
        ),
        cyber=(
            "wire-fraud and business-email-compromise defense, protecting LP and deal data, "
            "and security due-diligence across portfolio companies"
        ),
        generic=(
            "confidentiality of LP and deal data, portfolio-company integration, "
            "and regulatory reporting"
        ),
    ),
    IndustryProfile(
        label="healthcare & life sciences",
        keywords=frozenset(
            {
                "health",
                "healthcare",
                "medical",
                "patient",
                "clinical",
                "pharma",
                "pharmaceutical",
                "biotech",
                "hospital",
                "diagnostic",
                "telehealth",
                "genomic",
                "medtech",
                "ehr",
            }
        ),
        cyber=(
            "HIPAA/PHI handling, segmentation of clinical data, "
            "and securing connected medical or diagnostic devices"
        ),
        generic="patient-data privacy, regulatory validation, and reliability of clinical systems",
    ),
    IndustryProfile(
        label="e-commerce & retail",
        keywords=frozenset(
            {
                "ecommerce",
                "e-commerce",
                "retail",
                "marketplace",
                "shopping",
                "storefront",
                "dtc",
                "merchant",
            }
        ),
        cyber=(
            "checkout/PCI exposure, account-takeover and fraud at scale, "
            "and bot/scraping defense during traffic peaks"
        ),
        generic="peak-traffic scaling, payment integration, and fraud/abuse at the storefront",
    ),
    IndustryProfile(
        label="infrastructure, cloud & security",
        keywords=frozenset(
            {
                "cdn",
                "edge",
                "network",
                "networking",
                "cloud infrastructure",
                "hosting",
                "datacenter",
                "ddos",
                "firewall",
                "waf",
                "zero trust",
                "cybersecurity",
                "security",
                "infosec",
                "vpn",
                "observability",
                "sase",
            }
        ),
        cyber=(
            "multi-tenant isolation, DDoS mitigation at scale, "
            "and the responsibility of securing infrastructure other companies depend on"
        ),
        generic=(
            "multi-tenancy, global scale and latency, "
            "and the reliability of infrastructure others build on"
        ),
    ),
    IndustryProfile(
        label="AI, ML & data",
        keywords=frozenset(
            {
                "artificial intelligence",
                "machine learning",
                "llm",
                "deep learning",
                "data platform",
                "analytics",
                "big data",
                "data science",
                "generative",
                "nlp",
                "computer vision",
            }
        ),
        cyber=(
            "model and training-data governance, prompt-injection and model-abuse, "
            "and securing the data pipeline feeding the models"
        ),
        generic=(
            "data-pipeline scale, model governance, "
            "and the evolving infrastructure behind AI products"
        ),
    ),
    IndustryProfile(
        label="B2B SaaS",
        keywords=frozenset(
            {
                "saas",
                "b2b",
                "enterprise software",
                "productivity",
                "collaboration",
                "crm",
                "erp",
                "workflow",
                "developer tools",
            }
        ),
        cyber=(
            "tenant isolation, customer-data segregation, "
            "and the shared-responsibility boundary you present to enterprise buyers"
        ),
        generic=(
            "multi-tenant architecture, enterprise integration, "
            "and the reliability bar enterprise customers expect"
        ),
    ),
    IndustryProfile(
        label="government & defense",
        keywords=frozenset(
            {
                "government",
                "defense",
                "defence",
                "public sector",
                "military",
                "federal",
                "govtech",
                "intelligence",
                "aerospace",
            }
        ),
        cyber=(
            "compliance regimes (FedRAMP, CMMC, FISMA), supply-chain assurance, "
            "and handling of sensitive or classified data"
        ),
        generic="compliance regimes, procurement constraints, and high-assurance requirements",
    ),
    IndustryProfile(
        label="gaming, media & social",
        keywords=frozenset(
            {
                "gaming",
                "media",
                "streaming",
                "entertainment",
                "social media",
                "advertising",
                "adtech",
                "creator",
            }
        ),
        cyber=(
            "anti-cheat and abuse, account fraud, content-moderation tooling, "
            "and DDoS against real-time services"
        ),
        generic="real-time scale, abuse and moderation, and content delivery",
    ),
    IndustryProfile(
        label="education",
        keywords=frozenset(
            {
                "education",
                "edtech",
                "e-learning",
                "university",
                "academic",
            }
        ),
        cyber=(
            "student-data privacy (FERPA/COPPA), account security for younger users, "
            "and a sprawling third-party integration surface"
        ),
        generic="data privacy for minors, integration sprawl, and seasonal scale",
    ),
    IndustryProfile(
        label="logistics & industrial",
        keywords=frozenset(
            {
                "logistics",
                "supply chain",
                "manufacturing",
                "industrial",
                "iot",
                "automotive",
                "energy",
                "utility",
                "utilities",
                "transportation",
                "shipping",
                "fleet",
                "mobility",
                "robotics",
            }
        ),
        cyber="OT/IoT security, the IT/OT boundary, and supply-chain or firmware integrity",
        generic="OT/IoT reliability, the IT/OT boundary, and physical-world constraints",
    ),
)

_MAX_INDUSTRY_QUESTIONS = 2
_MAX_TECH_ANGLE_QUESTIONS = 2

_TECH_ROLES: set[Role] = {
    Role.CYBERSECURITY,
    Role.SWE,
    Role.DEVOPS,
    Role.DATA,
    Role.ENG_LEADERSHIP,
}


def _matches_keyword(text: str, keyword: str) -> bool:
    return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None


def _classification(findings: Findings) -> tuple[str, Evidence] | None:
    """Build (classification_text, citation_evidence) from ALL industry/description evidence.

    ``evidence_for`` returns only a single best match, so when two
    BUSINESS_DESCRIPTION evidences exist (e.g. a weak homepage tagline plus a
    rich Wikipedia description) it may pick the weak one and miss the keywords
    in the other. Here we aggregate the summaries of *every* INDUSTRY_IDENTIFIED
    / BUSINESS_DESCRIPTION evidence so they all contribute to keyword matching.

    Citation evidence: prefer the INDUSTRY_IDENTIFIED evidence if present;
    otherwise the LONGEST BUSINESS_DESCRIPTION summary (the richer Wikipedia
    description beats a short homepage tagline).
    """
    industry_evs: list[Evidence] = []
    desc_evs: list[Evidence] = []
    for r in findings.results:
        for e in r.evidence:
            if e.signal == Signal.INDUSTRY_IDENTIFIED:
                industry_evs.append(e)
            elif e.signal == Signal.BUSINESS_DESCRIPTION:
                desc_evs.append(e)

    if not industry_evs and not desc_evs:
        return None

    text = " ".join(e.summary for e in (*industry_evs, *desc_evs)).lower()

    cite_ev = industry_evs[0] if industry_evs else max(desc_evs, key=lambda e: len(e.summary))

    return text, cite_ev


def _shorten(text: str, limit: int) -> str:
    """Trim to a word boundary within ``limit`` chars, adding an ellipsis if cut."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def _industry_questions(findings: Findings) -> list[Question]:
    role = findings.target.role
    is_cyber = role == Role.CYBERSECURITY

    classification = _classification(findings)
    if classification is None:
        return []
    text, cite_ev = classification

    matched: list[IndustryProfile] = [
        p for p in _INDUSTRY_PROFILES if any(_matches_keyword(text, kw) for kw in p.keywords)
    ]

    questions: list[Question] = []
    if matched:
        for profile in matched[:_MAX_INDUSTRY_QUESTIONS]:
            angle = profile.cyber if is_cyber else profile.generic
            if is_cyber:
                q_text = (
                    f"You operate in {profile.label} — "
                    f"how is the security team prioritizing {angle}?"
                )
            else:
                q_text = (
                    f"You operate in {profile.label} — "
                    f"what makes {angle} hard here, and how is the team tackling it?"
                )
            questions.append(
                Question(
                    text=q_text,
                    confidence="high",
                    role_tags={role},
                    evidence_signal=cite_ev.signal,
                    source_collector=cite_ev.source,
                    evidence=cite_ev,
                )
            )
        return questions

    # Industry/description text exists but no profile matched -> one generic fallback.
    # A clean industry label (from the Wikipedia infobox) reads naturally after
    # "You operate in"; a free-text description (often a full sentence) does not,
    # so we quote it instead of producing "You operate in <sentence>".
    if cite_ev.signal == Signal.INDUSTRY_IDENTIFIED:
        label = _shorten(cite_ev.summary, 80)
        if is_cyber:
            q_text = (
                f"You operate in {label} — which security threats are most specific to "
                "that sector, and how does that shape the team's priorities versus a "
                "generic security program?"
            )
        else:
            q_text = (
                f"You operate in {label} — what engineering challenges are most specific "
                "to that sector, and how do they shape this team's roadmap?"
            )
    else:
        desc = _shorten(cite_ev.summary, 140)
        if is_cyber:
            q_text = (
                f"Your public profile describes the company as “{desc}” — which security "
                "threats are most specific to that space, and how does that shape the "
                "team's priorities versus a generic security program?"
            )
        else:
            q_text = (
                f"Your public profile describes the company as “{desc}” — what engineering "
                "challenges are most specific to that space, and how do they shape this "
                "team's roadmap?"
            )
    questions.append(
        Question(
            text=q_text,
            confidence="high",
            role_tags={role},
            evidence_signal=cite_ev.signal,
            source_collector=cite_ev.source,
            evidence=cite_ev,
        )
    )
    return questions


# Tech angles in priority order. Each entry: (matcher keys, display name, angle).
# `keys` are matched case-insensitively against stack entries; the first key found
# present is used as the display name when `display` is None (cloud case).
_TECH_ANGLES: tuple[tuple[tuple[str, ...], str | None, str], ...] = (
    (
        ("kubernetes",),
        "Kubernetes",
        "container and orchestration security — image supply chain, runtime policy, "
        "and secrets management",
    ),
    (
        ("terraform",),
        "Terraform",
        "infrastructure-as-code security — policy-as-code, drift detection, "
        "and secrets handling in pipelines",
    ),
    (
        ("aws", "gcp", "azure"),
        None,  # display = matched provider name (uppercased/normalized)
        "cloud security posture — IAM blast radius, misconfiguration detection, "
        "and the shared-responsibility split",
    ),
    (
        ("kafka",),
        "Kafka",
        "securing the streaming pipeline — topic-level authorization, data-in-transit, "
        "and PII flowing through events",
    ),
)

_CLOUD_DISPLAY = {"aws": "AWS", "gcp": "GCP", "azure": "Azure"}


def _jobstack_questions(findings: Findings) -> list[Question]:
    stack_ev = findings.evidence_for(Signal.JOB_STACK_LISTED)
    if stack_ev is None:
        return []

    job = findings.collector("job")
    stack_list: list[str] = []
    if job is not None:
        raw = job.data.get("stack")
        if isinstance(raw, list):
            stack_list = [str(s) for s in raw]
    if not stack_list:
        stack_list = [s.strip() for s in stack_ev.summary.split(", ") if s.strip()]

    role = findings.target.role
    is_cyber = role == Role.CYBERSECURITY

    questions: list[Question] = []

    # Always emit the "why this stack" question.
    questions.append(
        Question(
            text=(
                f"The role's stack centers on {stack_ev.summary} — is this a greenfield build, "
                "a migration off an existing stack, or scaling what's already in production?"
            ),
            confidence="high",
            role_tags=set(_TECH_ROLES),
            evidence_signal=stack_ev.signal,
            source_collector="job",
            evidence=stack_ev,
        )
    )

    # Tech-angle questions are cyber-only.
    if not is_cyber:
        return questions

    lowered = {s.lower() for s in stack_list}
    tech_questions: list[Question] = []
    for keys, display, angle in _TECH_ANGLES:
        if len(tech_questions) >= _MAX_TECH_ANGLE_QUESTIONS:
            break
        present_key = next((k for k in keys if k in lowered), None)
        if present_key is None:
            continue
        tech_name = display if display is not None else _CLOUD_DISPLAY.get(present_key, present_key)
        tech_questions.append(
            Question(
                text=f"The JD lists {tech_name} — how does the security team approach {angle}?",
                confidence="high",
                role_tags={Role.CYBERSECURITY},
                evidence_signal=stack_ev.signal,
                source_collector="job",
                evidence=stack_ev,
            )
        )
    questions.extend(tech_questions)
    return questions


def contextual_questions(findings: Findings) -> list[Question]:
    """Industry + JD-tech questions, all evidence-backed and confidence='high'."""
    return _industry_questions(findings) + _jobstack_questions(findings)

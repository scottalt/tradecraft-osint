"""Starter library of QuestionTemplates.

Each template is keyed by one or more Signals. The heuristic analyzer fires a
template when any of its signals appears in Findings AND the user's --role is in
the template's roles set.

The MVP-walking-skeleton ships ~15 templates (mostly footprint-driven, since
that's our only collector yet). Plan 2 grows this library as each new collector
lands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tradecraft.models import Role, Signal


@dataclass(frozen=True)
class QuestionTemplate:
    id: str
    signals: tuple[Signal, ...]
    roles: frozenset[Role]
    text: str
    confidence: Literal["high", "med", "low"]
    source: str
    needs_evidence: bool = False


_ALL_TECH_ROLES = frozenset(
    {Role.CYBERSECURITY, Role.SWE, Role.DEVOPS, Role.DATA, Role.ENG_LEADERSHIP}
)


TEMPLATES: tuple[QuestionTemplate, ...] = (
    QuestionTemplate(
        id="company.founder_technical",
        signals=(Signal.FOUNDER_TECHNICAL,),
        roles=_ALL_TECH_ROLES,
        text=(
            "Your founders have deep technical backgrounds. "
            "How involved are they in current engineering decisions versus delegating?"
        ),
        confidence="low",
        source="company",
    ),
    QuestionTemplate(
        id="job.stack_mismatch",
        signals=(Signal.LANGUAGES_MISMATCH_JOB,),
        roles=frozenset({Role.SWE, Role.DEVOPS, Role.CYBERSECURITY}),
        text=(
            "The job description calls for a stack that doesn't dominate your public repos. "
            "Is the team mid-migration, or is this stack scoped to a specific new initiative?"
        ),
        confidence="high",
        source="job",
    ),
    QuestionTemplate(
        id="job.stack_alignment",
        signals=(Signal.STACK_ALIGNMENT_STRONG,),
        roles=frozenset({Role.SWE, Role.DEVOPS}),
        text=(
            "Your public stack aligns closely with the job description. "
            "Where does the team feel that stack is straining at scale?"
        ),
        confidence="med",
        source="job",
    ),
    QuestionTemplate(
        id="news.layoffs",
        signals=(Signal.RECENT_LAYOFFS,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "I saw '{summary}' (via {source}, {date}). "
            "How has the team's scope shifted, and what's the focus for the remaining quarter?"
        ),
        confidence="high",
        source="news",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="news.funding",
        signals=(Signal.RECENT_FUNDING,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "I saw '{summary}' (via {source}, {date}). "
            "Where is most of that capital going — hiring, infrastructure, or new product lines?"
        ),
        confidence="high",
        source="news",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="news.leadership_change",
        signals=(Signal.RECENT_LEADERSHIP_CHANGE,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "I saw '{summary}' (via {source}, {date}). "
            "How has it shifted what the team is prioritizing?"
        ),
        confidence="med",
        source="news",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="news.security_incident",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.DEVOPS, Role.ENG_LEADERSHIP}),
        text=(
            "I saw '{summary}' (via {source}, {date}). "
            "What's changed in the team's detection posture and process since?"
        ),
        confidence="high",
        source="news",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="news.recent",
        signals=(Signal.RECENT_NEWS,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "I saw '{summary}' (via {source}, {date}). "
            "What's the story behind that, and how is it shaping the team's priorities right now?"
        ),
        confidence="high",
        source="news",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="breaches.history",
        signals=(Signal.BREACH_HISTORY,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "Have I Been Pwned lists past breach events involving your domain. "
            "How does that history shape your current detection and response approach?"
        ),
        confidence="high",
        source="breaches",
    ),
    QuestionTemplate(
        id="ma.recent",
        signals=(Signal.M_A_RECENT,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "I saw '{summary}' (via {source}, {date}). "
            "How is the integration going — product, identity, security tooling, on-call?"
        ),
        confidence="high",
        source="ma",
        needs_evidence=True,
    ),
    # ---- breaches (offensive + defensive + GRC) ----
    QuestionTemplate(
        id="breaches.history.defensive",
        signals=(Signal.BREACH_HISTORY,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "HIBP lists past breach events involving your domain. "
            "What changed in your detection and response coverage after those incidents?"
        ),
        confidence="high",
        source="breaches",
    ),
    QuestionTemplate(
        id="breaches.history.grc",
        signals=(Signal.BREACH_HISTORY,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "How did past breach disclosures shape your compliance program — "
            "additional audits, framework changes (SOC 2, ISO 27001), or board-level reporting?"
        ),
        confidence="med",
        source="breaches",
    ),
    QuestionTemplate(
        id="breaches.recent.offensive",
        signals=(Signal.BREACH_RECENT,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "A breach in the last 24 months is recent. "
            "How has external attack-surface management changed since — purple team cadence, "
            "pre-prod exposure controls, or third-party assessments?"
        ),
        confidence="high",
        source="breaches",
    ),
    # ---- github (AppSec + offensive) ----
    QuestionTemplate(
        id="github.oss_forward",
        signals=(Signal.OSS_FORWARD_CULTURE,),
        roles=frozenset({Role.CYBERSECURITY, Role.SWE, Role.DEVOPS}),
        text=(
            "You have a substantial public GitHub footprint. "
            "How does the security team work with engineering on supply-chain controls — "
            "dependency review, SBOM generation, signed commits?"
        ),
        confidence="med",
        source="github",
    ),
    # ---- news (defensive + offensive + GRC) ----
    QuestionTemplate(
        id="news.security_incident.defensive",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "I saw '{summary}' (via {source}, {date}). "
            "What changed in your detection coverage, IR runbooks, or SOC staffing model since?"
        ),
        confidence="high",
        source="news",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="news.security_incident.offensive",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "After '{summary}' (via {source}, {date}), did you bring in external "
            "red-team or purple-team engagements to validate the fix?"
        ),
        confidence="med",
        source="news",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="news.security_incident.grc",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "How did '{summary}' (via {source}, {date}) shape your compliance reporting "
            "and board-level audit cadence?"
        ),
        confidence="med",
        source="news",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="news.layoffs.cyber_specific",
        signals=(Signal.RECENT_LAYOFFS,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "On '{summary}' (via {source}, {date}) — security teams often see "
            "disproportionate cuts during layoffs. "
            "Did the security org stay whole, and how has scope been re-prioritized?"
        ),
        confidence="med",
        source="news",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="news.funding.cyber_specific",
        signals=(Signal.RECENT_FUNDING,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "On '{summary}' (via {source}, {date}) — where is the security org investing — "
            "in-house tooling, headcount, or third-party platforms?"
        ),
        confidence="med",
        source="news",
        needs_evidence=True,
    ),
    # ---- company (AppSec + GRC) ----
    QuestionTemplate(
        id="company.founder_technical.cyber_specific",
        signals=(Signal.FOUNDER_TECHNICAL,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "Your founders have technical backgrounds. "
            "How involved are they in security trade-offs — defining risk appetite, "
            "approving exception requests?"
        ),
        confidence="low",
        source="company",
    ),
    QuestionTemplate(
        id="company.product_empty",
        signals=(Signal.PRODUCT_LIST_EMPTY,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "Your public site is sparse on product details. "
            "Is that a deliberate stealth posture, or is messaging evolving?"
        ),
        confidence="low",
        source="company",
    ),
    # ---- job (AppSec / offensive / defensive / GRC across stack mismatch) ----
    QuestionTemplate(
        id="job.stack_mismatch.cyber_specific",
        signals=(Signal.LANGUAGES_MISMATCH_JOB,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "The JD calls for skills in a stack that doesn't dominate your public repos. "
            "Is this for a new initiative — a greenfield service or a security tooling rewrite?"
        ),
        confidence="high",
        source="job",
    ),
    QuestionTemplate(
        id="job.stack_alignment.cyber_specific",
        signals=(Signal.STACK_ALIGNMENT_STRONG,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "Your stack aligns closely with the JD. "
            "Where does the security team feel the existing stack falls short at scale — "
            "policy enforcement, observability, or supply-chain coverage?"
        ),
        confidence="med",
        source="job",
    ),
    # ---- people (defensive + AppSec) ----
    QuestionTemplate(
        id="people.strong_brand.defensive",
        signals=(Signal.STRONG_ENG_BRAND,),
        roles=frozenset({Role.CYBERSECURITY, Role.SWE}),
        text=(
            "Your engineers publish a lot — talks, blog posts, OSS. "
            "Does the security team contribute to that public engineering brand, "
            "or stay quieter for risk reasons?"
        ),
        confidence="med",
        source="people",
    ),
    # ---- business (GRC + defensive) ----
    QuestionTemplate(
        id="business.public_company.grc",
        signals=(Signal.PUBLIC_COMPANY,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "As a public company, what's the security team's relationship with audit / "
            "the Audit Committee — quarterly reporting, ad-hoc briefings, both?"
        ),
        confidence="med",
        source="business",
    ),
    QuestionTemplate(
        id="business.recent_10k",
        signals=(Signal.RECENT_10K,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "The most recent 10-K mentions cyber-risk disclosure. "
            "Has the SEC's incident-reporting rule changed how the team scopes "
            "what constitutes a material incident?"
        ),
        confidence="med",
        source="business",
    ),
    QuestionTemplate(
        id="business.glassdoor_low",
        signals=(Signal.GLASSDOOR_RATING_LOW,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP, Role.GENERIC}),
        text=(
            "Public-review sentiment is mixed. "
            "What is the team actively changing — process, on-call load, comp, growth path?"
        ),
        confidence="med",
        source="business",
    ),
    # ---- ma (offensive + AppSec + GRC) ----
    # NOTE: the ma.recent.* templates key on Signal.M_A_RECENT, which no
    # collector emits yet (reliable acquisition-event dating is deferred — see
    # CHANGELOG). They are marked needs_evidence=True, so they stay safely
    # inert (never fire as boilerplate) until a future collector emits
    # M_A_RECENT with real evidence. The ma collector currently emits only
    # SUBSIDIARY_OF and M_A_FREQUENT_ACQUIRER (see ma.subsidiary / ma.frequent_acquirer).
    QuestionTemplate(
        id="ma.recent.offensive",
        signals=(Signal.M_A_RECENT,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "After '{summary}' (via {source}, {date}), "
            "what does the external attack-surface picture look like once you fold in "
            "their domains, SaaS contracts, and identity providers?"
        ),
        confidence="high",
        source="ma",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="ma.recent.appsec",
        signals=(Signal.M_A_RECENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.SWE}),
        text=(
            "After '{summary}' (via {source}, {date}), how do you handle a new codebase "
            "with different SDLC controls — gradual policy adoption, immediate gating, "
            "or buy-now-fix-later?"
        ),
        confidence="high",
        source="ma",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="ma.recent.grc",
        signals=(Signal.M_A_RECENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "After '{summary}' (via {source}, {date}), what's the security-integration "
            "timeline post-deal — identity merge, framework alignment (SOC 2, ISO), "
            "incident-response unification?"
        ),
        confidence="high",
        source="ma",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="ma.frequent_acquirer",
        signals=(Signal.M_A_FREQUENT_ACQUIRER,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "{summary} (per {source}). "
            "Is there a standing post-acquisition security playbook, or is each deal bespoke?"
        ),
        confidence="med",
        source="ma",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="ma.subsidiary",
        signals=(Signal.SUBSIDIARY_OF,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "{summary} (per {source}) — where does this team's security autonomy end: "
            "tooling choices, hiring, incident escalation?"
        ),
        confidence="low",
        source="ma",
        needs_evidence=True,
    ),
)

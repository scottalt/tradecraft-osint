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
        id="footprint.missing_csp",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY, Role.SWE}),
        text=(
            "Your main site doesn't ship a Content-Security-Policy header. "
            "Is that a deliberate posture, or is the team working toward one?"
        ),
        confidence="low",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.missing_hsts",
        signals=(Signal.MISSING_HSTS,),
        roles=frozenset({Role.CYBERSECURITY, Role.DEVOPS}),
        text=(
            "I noticed your apex doesn't return Strict-Transport-Security. "
            "How does the team think about transport hardening across subdomains?"
        ),
        confidence="low",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.open_staging",
        signals=(Signal.OPEN_STAGING_SUBDOMAIN,),
        roles=frozenset({Role.CYBERSECURITY, Role.DEVOPS}),
        text=(
            "I saw pre-prod hostnames in public certificate transparency logs. "
            "Does the team have a stance on hiding or hardening pre-prod surface area?"
        ),
        confidence="low",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.cert_expiring",
        signals=(Signal.CERT_EXPIRING_SOON,),
        roles=frozenset({Role.CYBERSECURITY, Role.DEVOPS}),
        text=(
            "Your apex TLS certificate expires soon. Is rotation automated end-to-end, "
            "or is there a manual step in the rollout?"
        ),
        confidence="low",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.exposed_admin",
        signals=(Signal.EXPOSED_ADMIN_PATH,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "robots.txt or sitemap.xml references admin paths. "
            "How does the team approach reducing the discoverable attack surface?"
        ),
        confidence="low",
        source="footprint",
    ),
    QuestionTemplate(
        id="company.recent_press",
        signals=(Signal.RECENT_PRESS_RELEASE,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "I saw your recent announcement. How is that landing internally, "
            "and how does it shape what this team will prioritize next quarter?"
        ),
        confidence="med",
        source="company",
    ),
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
    QuestionTemplate(
        id="github.no_public",
        signals=(Signal.NO_PUBLIC_GITHUB,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "No public GitHub org under the brand name. "
            "Is that a deliberate posture — all internal-only — or are repos under personal accounts?"
        ),
        confidence="low",
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
        id="company.recent_press.cyber_specific",
        signals=(Signal.RECENT_PRESS_RELEASE,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "I saw the recent announcement. What does that mean for the security team's "
            "near-term roadmap — new product surface, integrations, or compliance work?"
        ),
        confidence="med",
        source="company",
    ),
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
    QuestionTemplate(
        id="job.stack_listed",
        signals=(Signal.JOB_STACK_LISTED,),
        roles=frozenset({Role.CYBERSECURITY, Role.SWE, Role.DEVOPS}),
        text=(
            "The job description emphasizes {summary}. "
            "Where is the team feeling that stack strain most at scale — "
            "supply-chain controls, secrets management, or runtime observability?"
        ),
        confidence="med",
        source="job",
        needs_evidence=True,
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
    QuestionTemplate(
        id="people.quiet_brand",
        signals=(Signal.QUIET_ENG_BRAND,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "I couldn't find much public engineering content from the team. "
            "Is that a posture choice, or are folks focused inward?"
        ),
        confidence="low",
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
        id="business.wikipedia",
        signals=(Signal.WIKIPEDIA_INFOBOX_PRESENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.GENERIC}),
        text=(
            "Your Wikipedia page covers history and product lines. "
            "How does the security org map onto the historical business — "
            "centralized, federated by business unit, or matrixed?"
        ),
        confidence="low",
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
    # ---- additional offensive templates against existing footprint signals ----
    QuestionTemplate(
        id="footprint.missing_csp.offensive",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "No CSP on the apex. "
            "In a recent external assessment, would that have shown up as a finding, "
            "and what's the team's appetite for CSP rollout pain?"
        ),
        confidence="low",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.open_staging.grc",
        signals=(Signal.OPEN_STAGING_SUBDOMAIN,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "Pre-prod hostnames in public CT logs. "
            "Does your attack-surface management program — internal or vendor-driven — "
            "audit the CT feed continuously?"
        ),
        confidence="low",
        source="footprint",
    ),
    QuestionTemplate(
        id="business.industry_identified",
        signals=(Signal.INDUSTRY_IDENTIFIED,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "You operate in {summary} (per {source}). "
            "What does that sector's threat model mean for how the team prioritizes security work?"
        ),
        confidence="med",
        source="business",
        needs_evidence=True,
    ),
    QuestionTemplate(
        id="business.description",
        signals=(Signal.BUSINESS_DESCRIPTION,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "I read that you're '{summary}' (via {source}). "
            "Which part of that mission puts the most pressure on the security team today?"
        ),
        confidence="med",
        source="business",
        needs_evidence=True,
    ),
)

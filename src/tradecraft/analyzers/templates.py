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
        confidence="med",
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
        confidence="med",
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
        confidence="high",
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
        confidence="med",
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
        confidence="med",
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
            "I saw the recent layoffs in the news. "
            "How has the team's scope shifted, and what's the focus for the remaining quarter?"
        ),
        confidence="high",
        source="news",
    ),
    QuestionTemplate(
        id="news.funding",
        signals=(Signal.RECENT_FUNDING,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "Congrats on the recent funding round. "
            "Where is most of that capital going — hiring, infrastructure, or new product lines?"
        ),
        confidence="high",
        source="news",
    ),
    QuestionTemplate(
        id="news.leadership_change",
        signals=(Signal.RECENT_LEADERSHIP_CHANGE,),
        roles=frozenset(_ALL_TECH_ROLES | {Role.GENERIC}),
        text=(
            "The recent leadership change is interesting context. "
            "How has it shifted what the team is prioritizing?"
        ),
        confidence="med",
        source="news",
    ),
    QuestionTemplate(
        id="news.security_incident",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.DEVOPS, Role.ENG_LEADERSHIP}),
        text=(
            "I read about the security incident earlier this year. "
            "What's changed in the team's posture and process since?"
        ),
        confidence="high",
        source="news",
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
            "I saw the recent acquisition. "
            "How is the integration going — product, identity, security tooling, on-call?"
        ),
        confidence="high",
        source="ma",
    ),
)

"""Tests for tradecraft.analyzers.templates."""

from __future__ import annotations

import string

from tradecraft.analyzers.templates import (
    TEMPLATES,
    QuestionTemplate,
)
from tradecraft.models import Role, Signal


def test_template_library_is_non_empty() -> None:
    assert len(TEMPLATES) >= 10


def test_every_template_has_a_known_signal() -> None:
    known = set(Signal)
    for tmpl in TEMPLATES:
        for sig in tmpl.signals:
            assert sig in known


def test_every_template_has_at_least_one_role() -> None:
    for tmpl in TEMPLATES:
        assert tmpl.roles, f"template '{tmpl.id}' has no roles"


def test_every_template_id_is_unique() -> None:
    ids = [t.id for t in TEMPLATES]
    assert len(ids) == len(set(ids))


def test_template_dataclass_fields() -> None:
    t = QuestionTemplate(
        id="x",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY}),
        text="Why no CSP?",
        confidence="med",
        source="footprint",
    )
    assert t.confidence == "med"
    assert Signal.MISSING_CSP in t.signals


def test_library_has_expanded_for_v0_2() -> None:
    """v0.2.0 grew the library substantially. Note: the generic security-header
    footprint templates and the contextual placeholder templates were later
    removed (footprint recon is no longer surfaced as interview questions;
    industry / JD-stack questions moved to analyzers/contextual.py)."""
    assert len(TEMPLATES) >= 30


# Signals intentionally NOT turned into template questions.
#
# Footprint recon-only signals: these still surface in the dossier's footprint
# recon section, but as security-config trivia they make poor interview questions,
# so we do not generate template questions from them.
#
# Contextual signals: INDUSTRY_IDENTIFIED / BUSINESS_DESCRIPTION / JOB_STACK_LISTED
# are handled by analyzers/contextual.py (industry + JD-tech questions), not by
# the template library.
#
# Low-value recon signals: RECENT_PRESS_RELEASE and WIKIPEDIA_INFOBOX_PRESENT
# only ever produced vague filler ("I saw your recent announcement, how is it
# landing", "how does the security org map onto the historical business"), so
# their templates were removed. The signals still surface in the dossier but
# carry no interview question.
_TEMPLATE_EXCLUDED_SIGNALS: frozenset[Signal] = frozenset(
    {
        # footprint recon-only
        Signal.MISSING_CSP,
        Signal.MISSING_HSTS,
        Signal.OPEN_STAGING_SUBDOMAIN,
        Signal.CERT_EXPIRING_SOON,
        Signal.EXPOSED_ADMIN_PATH,
        # handled by analyzers/contextual.py
        Signal.INDUSTRY_IDENTIFIED,
        Signal.BUSINESS_DESCRIPTION,
        Signal.JOB_STACK_LISTED,
        # low-value recon: templates removed as vague filler
        Signal.RECENT_PRESS_RELEASE,
        Signal.WIKIPEDIA_INFOBOX_PRESENT,
    }
)


def test_every_cybersec_signal_has_at_least_one_template() -> None:
    """Every Signal value should be covered by at least one cybersecurity-tagged
    template, except the intentionally excluded recon-only / contextual signals.
    Non-cyber roles are intentionally under-covered for now."""
    cyber_signals_covered: set[Signal] = set()
    for tmpl in TEMPLATES:
        if Role.CYBERSECURITY in tmpl.roles:
            cyber_signals_covered.update(tmpl.signals)
    missing = (set(Signal) - cyber_signals_covered) - _TEMPLATE_EXCLUDED_SIGNALS
    assert not missing, f"signals with no cybersec template: {sorted(s.value for s in missing)}"


def _by_id(template_id: str) -> QuestionTemplate:
    return next(t for t in TEMPLATES if t.id == template_id)


def test_needs_evidence_field_defaults_false() -> None:
    t = QuestionTemplate(
        id="x",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY}),
        text="Why no CSP?",
        confidence="med",
        source="footprint",
    )
    assert t.needs_evidence is False


def test_evidence_backed_templates_are_marked() -> None:
    """A template has format slots IFF it is needs_evidence=True.

    Self-maintaining: any new template that adds a {slot} must set
    needs_evidence=True, and vice versa — no hardcoded signal set to drift.
    """
    for tmpl in TEMPLATES:
        has_slots = bool({fname for _, fname, _, _ in string.Formatter().parse(tmpl.text) if fname})
        assert tmpl.needs_evidence == has_slots, (
            f"{tmpl.id}: needs_evidence={tmpl.needs_evidence} but has_slots={has_slots}"
        )


def test_evidence_templates_use_only_safe_slots() -> None:
    """needs_evidence templates may only reference {summary}/{source}/{date}."""
    allowed = {"summary", "source", "date"}
    for tmpl in TEMPLATES:
        if not tmpl.needs_evidence:
            continue
        # Must not raise and must only use allowed keys.
        tmpl.text.format(summary="s", source="src", date="d")
        # crude slot extraction
        slots = {fname for _, fname, _, _ in string.Formatter().parse(tmpl.text) if fname}
        assert slots <= allowed, f"{tmpl.id} uses unexpected slots: {slots - allowed}"


def test_footprint_config_templates_removed() -> None:
    """The generic security-header footprint templates and the contextual
    placeholder templates were removed; footprint recon is no longer surfaced
    as interview questions and industry/JD-stack questions live in
    analyzers/contextual.py."""
    ids = {t.id for t in TEMPLATES}
    for tid in (
        "footprint.missing_csp",
        "footprint.missing_hsts",
        "footprint.open_staging",
        "footprint.cert_expiring",
        "footprint.exposed_admin",
        "footprint.missing_csp.offensive",
        "footprint.open_staging.grc",
        "business.industry_identified",
        "business.description",
        "job.stack_listed",
        # weak filler removed per product direction
        "company.recent_press",
        "company.recent_press.cyber_specific",
        "business.wikipedia",
    ):
        assert tid not in ids, f"{tid} should have been removed"


def test_multiple_sub_disciplines_represented() -> None:
    """Templates should span offensive (attack-surface), defensive (incident
    response), AppSec (supply-chain / SDLC posture), and GRC (compliance) framings.
    Check by keyword presence in the template texts."""
    text_corpus = " ".join(t.text.lower() for t in TEMPLATES if Role.CYBERSECURITY in t.roles)
    assert "attack surface" in text_corpus or "exposure" in text_corpus  # offensive
    assert "detect" in text_corpus or "respond" in text_corpus or "soc" in text_corpus  # defensive
    assert (
        "supply-chain" in text_corpus
        or "supply chain" in text_corpus
        or "sdlc" in text_corpus
        or "dependency" in text_corpus
    )  # appsec
    assert "compliance" in text_corpus or "audit" in text_corpus or "soc 2" in text_corpus  # grc

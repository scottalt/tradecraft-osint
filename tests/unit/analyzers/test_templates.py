"""Tests for tradecraft.analyzers.templates."""

from __future__ import annotations

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
    """v0.2.0 ships ~45 templates (15 starter + ~30 new)."""
    assert len(TEMPLATES) >= 40


def test_every_cybersec_signal_has_at_least_one_template() -> None:
    """Every Signal value should be covered by at least one cybersecurity-tagged
    template. Non-cyber roles are intentionally under-covered for now."""
    cyber_signals_covered: set[Signal] = set()
    for tmpl in TEMPLATES:
        if Role.CYBERSECURITY in tmpl.roles:
            cyber_signals_covered.update(tmpl.signals)
    missing = set(Signal) - cyber_signals_covered
    assert not missing, f"signals with no cybersec template: {sorted(s.value for s in missing)}"


def test_multiple_sub_disciplines_represented() -> None:
    """Templates should span offensive (attack-surface), defensive (incident
    response), AppSec (CSP/HSTS posture), and GRC (compliance) framings.
    Check by keyword presence in the template texts."""
    text_corpus = " ".join(t.text.lower() for t in TEMPLATES if Role.CYBERSECURITY in t.roles)
    assert "attack surface" in text_corpus or "exposure" in text_corpus  # offensive
    assert "detect" in text_corpus or "respond" in text_corpus or "soc" in text_corpus  # defensive
    assert (
        "csp" in text_corpus or "content-security-policy" in text_corpus or "appsec" in text_corpus
    )  # appsec
    assert "compliance" in text_corpus or "audit" in text_corpus or "soc 2" in text_corpus  # grc

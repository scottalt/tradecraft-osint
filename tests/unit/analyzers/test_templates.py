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

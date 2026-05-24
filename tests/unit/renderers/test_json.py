"""Tests for tradecraft.renderers.json."""

from __future__ import annotations

import json

from tradecraft.models import (
    CollectorResult,
    Findings,
    Question,
    Role,
    Signal,
    Target,
)
from tradecraft.renderers.json import render_json


def test_renders_full_findings() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="footprint",
                data={"host": "acme.com"},
                signals=[Signal.MISSING_CSP],
                errors=[],
                duration_ms=10,
            )
        ],
    )
    questions = [
        Question(
            text="Q",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=True,
        )
    ]
    out = render_json(findings, questions)
    parsed = json.loads(out)
    assert parsed["schema_version"] == 1
    assert parsed["target"]["company_name"] == "Acme"
    assert parsed["results"][0]["name"] == "footprint"
    assert parsed["questions"][0]["is_starred"] is True


def test_output_is_stable_ordering() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(target=target, results=[])
    a = render_json(findings, [])
    b = render_json(findings, [])
    assert a == b

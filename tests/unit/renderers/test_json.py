"""Tests for tradecraft.renderers.json."""

from __future__ import annotations

import json

from tradecraft.models import (
    CollectorResult,
    Evidence,
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


def test_evidence_backed_question_serializes_evidence() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(target=target, results=[])
    questions = [
        Question(
            text="What changed after the breach?",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.RECENT_SECURITY_INCIDENT,
            source_collector="news",
            is_starred=True,
            evidence=Evidence(
                signal=Signal.RECENT_SECURITY_INCIDENT,
                summary="Acme discloses data breach",
                url="https://news.example/acme-breach",
                date="2026-03-11",
                source="news.google",
            ),
        )
    ]
    out = render_json(findings, questions)
    parsed = json.loads(out)
    ev = parsed["questions"][0]["evidence"]
    assert ev is not None
    assert ev["summary"] == "Acme discloses data breach"
    assert ev["url"] == "https://news.example/acme-breach"
    assert ev["date"] == "2026-03-11"
    assert ev["source"] == "news.google"


def test_output_is_stable_ordering() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(target=target, results=[])
    a = render_json(findings, [])
    b = render_json(findings, [])
    assert a == b

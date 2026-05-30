"""Tests for tradecraft.analyzers.ai."""

from __future__ import annotations

from unittest.mock import AsyncMock

from tradecraft.analyzers.ai import generate_ai_questions
from tradecraft.models import (
    CollectorResult,
    Findings,
    Question,
    Role,
    Signal,
    Target,
)


def _findings() -> Findings:
    target = Target(company_name="Acme", root_url="https://acme.com", role=Role.CYBERSECURITY)
    return Findings(
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


def _heuristic_questions() -> list[Question]:
    return [
        Question(
            text="Why no CSP?",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
        )
    ]


async def test_no_provider_returns_empty_list() -> None:
    result = await generate_ai_questions(
        findings=_findings(),
        heuristic_questions=_heuristic_questions(),
        provider=None,
    )
    assert result == []


async def test_provider_output_is_parsed_into_questions() -> None:
    fake_provider = AsyncMock()
    fake_provider.generate = AsyncMock(
        return_value=(
            "1. How does the security team approach exception requests for CSP rollout?\n"
            "2. What is the MTTR on detection coverage post-incident?\n"
            "3. Is there an internal red-team engagement cadence?\n"
        )
    )
    questions = await generate_ai_questions(
        findings=_findings(),
        heuristic_questions=_heuristic_questions(),
        provider=fake_provider,
    )
    assert len(questions) == 3
    assert all(q.source_collector == "ai" for q in questions)
    assert all(q.confidence == "high" for q in questions)
    assert all(q.evidence_signal is None for q in questions)
    assert "exception" in questions[0].text.lower()


async def test_provider_error_returns_empty_list() -> None:
    fake_provider = AsyncMock()
    fake_provider.generate = AsyncMock(side_effect=RuntimeError("rate limited"))
    questions = await generate_ai_questions(
        findings=_findings(),
        heuristic_questions=_heuristic_questions(),
        provider=fake_provider,
    )
    assert questions == []

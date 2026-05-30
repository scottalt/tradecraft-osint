"""AI analyzer: synthesize deep-dive questions via a BYOK provider."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from tradecraft.models import Findings, Question, Role
from tradecraft.providers.base import Provider

_NUMBERED_LINE = re.compile(r"^\s*\d+[\.\):]\s*(.+)$")
_MAX_TOKENS = 1200


def _system_prompt(role: Role) -> str:
    return (
        "You are an expert helping a candidate prepare for a cybersecurity "
        "interview. The user will provide structured OSINT findings about the "
        "target company and a list of questions an automated heuristic already "
        f"generated. The candidate is targeting role focus: '{role.value}'. "
        "Generate 3 to 7 NEW interview questions the candidate can ask the "
        "interviewer that the heuristic couldn't have produced. Focus on "
        "narrative connections across findings, role-fit nuance, "
        "and questions that demonstrate sophisticated reconnaissance. Do NOT "
        "duplicate any heuristic question. Return ONLY a numbered list, one "
        "question per line, no other commentary."
    )


def _user_prompt(findings: Findings, heuristic: Sequence[Question]) -> str:
    findings_json = json.dumps(
        {
            "target": findings.target.model_dump(mode="json"),
            "results": [r.model_dump(mode="json") for r in findings.results],
        },
        indent=2,
        sort_keys=True,
        default=str,
    )
    heuristic_block = "\n".join(f"- {q.text}" for q in heuristic) if heuristic else "(none)"
    return (
        "## Findings\n\n"
        f"```json\n{findings_json}\n```\n\n"
        "## Heuristic questions already generated (DO NOT DUPLICATE)\n\n"
        f"{heuristic_block}\n\n"
        "## Your task\n\n"
        "Generate 3-7 NEW interview questions as a numbered list."
    )


async def generate_ai_questions(
    findings: Findings,
    heuristic_questions: Sequence[Question],
    provider: Provider | None,
) -> list[Question]:
    """Return AI-generated questions. Returns empty list on no-provider or error."""
    if provider is None:
        return []

    system = _system_prompt(findings.target.role)
    prompt = _user_prompt(findings, heuristic_questions)

    try:
        raw = await provider.generate(system, prompt, _MAX_TOKENS)
    except Exception:  # surface as "no AI" rather than crash the run
        return []

    out: list[Question] = []
    for line in raw.splitlines():
        match = _NUMBERED_LINE.match(line)
        if not match:
            continue
        text = match.group(1).strip()
        if not text:
            continue
        out.append(
            Question(
                text=text,
                confidence="high",
                role_tags={findings.target.role},
                evidence_signal=None,
                source_collector="ai",
                is_starred=False,
            )
        )
    return out

"""JSON renderer: full Findings + questions dump with a stable schema."""

from __future__ import annotations

import json
from collections.abc import Sequence

from tradecraft.models import Findings, Question


def render_json(findings: Findings, questions: Sequence[Question]) -> str:
    payload = {
        "schema_version": findings.schema_version,
        "target": findings.target.model_dump(mode="json"),
        "results": [r.model_dump(mode="json") for r in findings.results],
        "questions": [q.model_dump(mode="json") for q in questions],
    }
    return json.dumps(payload, indent=2, sort_keys=True, default=str)

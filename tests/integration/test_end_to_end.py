"""End-to-end: CLI -> Orchestrator -> Collector -> Heuristics -> Renderers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import respx
from typer.testing import CliRunner

from tradecraft.cli import app
from tradecraft.collectors.footprint import FootprintCollector


@respx.mock
def test_full_run_produces_real_dossier(tmp_path: Path, fixtures_dir: Path) -> None:
    crtsh = json.loads((fixtures_dir / "footprint" / "crtsh_e2e.json").read_text())
    respx.get("https://crt.sh/", params={"q": "e2e.test", "output": "json"}).mock(
        return_value=httpx.Response(200, json=crtsh)
    )
    respx.get("https://e2e.test/").mock(
        return_value=httpx.Response(
            200,
            text="<html><body>hi</body></html>",
            headers={"server": "nginx", "strict-transport-security": "max-age=1"},
        )
    )
    respx.get("https://e2e.test/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://e2e.test/sitemap.xml").mock(return_value=httpx.Response(404))

    dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})
    runner = CliRunner()
    with patch(
        "tradecraft.cli._default_collectors",
        return_value=[FootprintCollector(_dns_lookup=dns)],
    ):
        result = runner.invoke(
            app,
            [
                "https://e2e.test",
                "--company",
                "E2E Test Inc",
                "--output",
                str(tmp_path),
            ],
        )
    assert result.exit_code == 0, result.stdout

    [folder] = list(tmp_path.iterdir())
    report = (folder / "report.md").read_text(encoding="utf-8")
    questions_md = (folder / "questions.md").read_text(encoding="utf-8")
    raw = json.loads((folder / "raw.json").read_text(encoding="utf-8"))

    # report covers the spine
    assert "# E2E Test Inc" in report
    assert "staging.e2e.test" in report
    # heuristics fired
    assert "Content-Security-Policy" in report
    assert "pre-prod" in report.lower() or "staging" in report.lower()
    # questions standalone
    assert "Questions to ask E2E Test Inc" in questions_md
    # json schema and roundtrip
    assert raw["schema_version"] == 1
    assert raw["target"]["company_name"] == "E2E Test Inc"
    assert any(q["evidence_signal"] == "missing_csp" for q in raw["questions"])

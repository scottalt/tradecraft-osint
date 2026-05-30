"""v0.3.0 AI integration end-to-end."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from typer.testing import CliRunner

from tradecraft.cli import app
from tradecraft.collectors.footprint import FootprintCollector


@respx.mock
def test_ai_questions_land_in_dossier(
    tmp_path: Path, fixtures_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Minimal footprint mocks
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://crt.sh/", params={"q": "acme.com", "output": "json"}).mock(
        return_value=httpx.Response(200, json=[{"name_value": "acme.com"}])
    )
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers={"server": "nginx"})
    )
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})

    # Mock the Anthropic SDK client at the AsyncAnthropic boundary.
    # Because AnthropicProvider does a lazy `import anthropic` and then accesses
    # `anthropic.AsyncAnthropic` on the module object, we patch at the source module.
    fake_response = MagicMock()
    fake_response.content = [
        MagicMock(
            text=(
                "1. How does your purple-team cadence inform CSP rollout?\n"
                "2. What's your SOC's MTTR on injected CSP violations?\n"
                "3. Have you piloted SBOM signing on the public site?\n"
            )
        )
    ]
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    runner = CliRunner()
    with (
        patch(
            "tradecraft.cli._default_collectors", return_value=[FootprintCollector(_dns_lookup=dns)]
        ),
        patch("anthropic.AsyncAnthropic", return_value=fake_client),
    ):
        result = runner.invoke(
            app,
            [
                "https://acme.com",
                "--company",
                "Acme",
                "--ai",
                "anthropic",
                "--output",
                str(tmp_path),
            ],
        )
    assert result.exit_code == 0, result.stdout
    [folder] = list(tmp_path.iterdir())
    raw = json.loads((folder / "raw.json").read_text())
    ai_questions = [q for q in raw["questions"] if q["source_collector"] == "ai"]
    assert len(ai_questions) == 3
    report = (folder / "report.md").read_text()
    assert "### Deep dive (AI)" in report
    assert "MTTR" in report

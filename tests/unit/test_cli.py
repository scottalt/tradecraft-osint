"""Tests for tradecraft.cli."""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from tradecraft.cli import _default_collectors, app
from tradecraft.collectors.base import Collector, CollectorContext
from tradecraft.models import (
    CollectorResult,
    Role,
    Signal,
)


class StubFootprint(Collector):
    name: ClassVar[str] = "footprint"
    requires_network: ClassVar[bool] = False
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY}

    async def run(self, ctx: CollectorContext) -> CollectorResult:  # noqa: ARG002
        return CollectorResult(
            name="footprint",
            data={"host": "acme.com", "subdomains": ["staging.acme.com"]},
            signals=[Signal.MISSING_CSP, Signal.OPEN_STAGING_SUBDOMAIN],
            errors=[],
            duration_ms=10,
        )


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_help_exits_zero(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "interview" in result.stdout.lower()


def test_refuses_person_name(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["https://example.com", "--company", "John Smith", "--output", str(tmp_path)],
    )
    assert result.exit_code != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "person" in combined.lower()


def test_end_to_end_produces_dossier(runner: CliRunner, tmp_path: Path) -> None:
    with patch("tradecraft.cli._default_collectors", return_value=[StubFootprint()]):
        result = runner.invoke(
            app,
            [
                "https://acme.com",
                "--company",
                "Acme Corp",
                "--output",
                str(tmp_path),
            ],
        )
    assert result.exit_code == 0, result.stdout
    dossier_dirs = list(tmp_path.iterdir())
    assert len(dossier_dirs) == 1
    folder = dossier_dirs[0]
    assert folder.name.startswith("acme-corp-")
    assert (folder / "report.md").exists()
    assert (folder / "questions.md").exists()
    assert (folder / "raw.json").exists()
    raw = json.loads((folder / "raw.json").read_text())
    assert raw["schema_version"] == 1


def test_json_flag_writes_only_json_to_stdout(runner: CliRunner) -> None:
    with patch("tradecraft.cli._default_collectors", return_value=[StubFootprint()]):
        result = runner.invoke(
            app,
            ["https://acme.com", "--company", "Acme Corp", "--json"],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["target"]["company_name"] == "Acme Corp"


def test_default_collectors_includes_all_v0_2_modules() -> None:
    collectors = _default_collectors()
    names = {c.name for c in collectors}
    assert names == {
        "footprint",
        "breaches",
        "github",
        "news",
        "company",
        "job",
        "people",
        "business",
        "ma",
    }


def test_ai_flag_with_no_provider_warns_and_continues(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No API key => Anthropic.from_env returns None
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("tradecraft.cli._default_collectors", return_value=[StubFootprint()]):
        result = runner.invoke(
            app,
            [
                "https://acme.com",
                "--company",
                "Acme Corp",
                "--ai",
                "anthropic",
                "--output",
                str(tmp_path),
            ],
        )
    # Should succeed (heuristic-only fallback), and stderr should mention AI disabled.
    assert result.exit_code == 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "ai" in combined.lower()


def test_ai_flag_with_provider_appends_questions(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake_provider = AsyncMock()
    fake_provider.generate = AsyncMock(
        return_value="1. AI question one\n2. AI question two\n"
    )
    with (
        patch("tradecraft.cli._default_collectors", return_value=[StubFootprint()]),
        patch("tradecraft.cli.build_provider", return_value=fake_provider),
    ):
        result = runner.invoke(
            app,
            [
                "https://acme.com",
                "--company",
                "Acme Corp",
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
    assert len(ai_questions) == 2

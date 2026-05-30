"""Tests for tradecraft.renderers.markdown."""

from __future__ import annotations

from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Findings,
    Question,
    Role,
    Signal,
    Target,
)
from tradecraft.renderers.markdown import render_markdown


def _findings_full() -> Findings:
    target = Target(
        company_name="Acme Corp",
        root_url="https://acme.com",
        job_url="https://acme.com/jobs/1",
        role=Role.CYBERSECURITY,
    )
    return Findings(
        target=target,
        results=[
            CollectorResult(
                name="footprint",
                data={
                    "host": "acme.com",
                    "subdomains": ["api.acme.com", "staging.acme.com"],
                    "security_headers": {"strict-transport-security": "max-age=1"},
                    "server": "nginx",
                    "x_powered_by": "Next.js",
                    "has_robots_txt": True,
                    "has_sitemap_xml": False,
                },
                signals=[Signal.MISSING_CSP, Signal.OPEN_STAGING_SUBDOMAIN],
                errors=[],
                duration_ms=120,
            )
        ],
    )


def test_renders_all_top_level_sections() -> None:
    findings = _findings_full()
    md = render_markdown(findings, [])
    for heading in (
        "# Acme Corp",
        "## Snapshot",
        "## Web & infrastructure footprint",
        "## Questions to ask",
        "## Collection notes",
    ):
        assert heading in md, f"missing section: {heading}"


def test_includes_subdomains_and_signals() -> None:
    findings = _findings_full()
    md = render_markdown(findings, [])
    assert "staging.acme.com" in md
    assert "api.acme.com" in md


def test_includes_questions_with_starred_first() -> None:
    findings = _findings_full()
    qs = [
        Question(
            text="Top one",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.OPEN_STAGING_SUBDOMAIN,
            source_collector="footprint",
            is_starred=True,
        ),
        Question(
            text="Second",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=False,
        ),
    ]
    md = render_markdown(findings, qs)
    top_idx = md.index("Top one")
    second_idx = md.index("Second")
    assert top_idx < second_idx


def test_collection_notes_reports_errors() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="footprint",
                data={},
                signals=[],
                errors=[CollectorError(stage="dns", message="timeout")],
                duration_ms=10,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "Collection notes" in md
    assert "footprint" in md
    assert "timeout" in md


def test_renders_breaches_section_when_present() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="breaches",
                data={"breaches": [{"name": "AcmeOldLeak", "date": "2019-03-15", "pwn_count": 1500000, "data_classes": ["Email", "Passwords"]}]},
                signals=[Signal.BREACH_HISTORY],
                errors=[],
                duration_ms=50,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "## Breach history" in md
    assert "AcmeOldLeak" in md
    assert "2019-03-15" in md


def test_renders_github_section_when_present() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="github",
                data={
                    "org": {"login": "acme", "public_repos": 47},
                    "repo_count": 47,
                    "languages": {"Go": 20, "TypeScript": 15},
                    "top_repos": [{"name": "acme-cli", "stars": 4200, "language": "Go"}],
                },
                signals=[Signal.OSS_FORWARD_CULTURE],
                errors=[],
                duration_ms=50,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "## GitHub presence" in md
    assert "acme-cli" in md
    assert "Go" in md


def test_renders_news_section_when_present() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="news",
                data={
                    "items": [
                        {"title": "Acme raises $200M Series D", "source": "google_news", "published": "Fri, 16 May 2026 00:00:00 GMT"},
                    ],
                    "headline_count": 1,
                },
                signals=[Signal.RECENT_FUNDING],
                errors=[],
                duration_ms=50,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "## News & timeline" in md
    assert "Series D" in md


def test_renders_business_section_when_present() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="business",
                data={"ticker": "ACME", "wikipedia": {"Founded": "2018", "Industry": "Security software"}},
                signals=[Signal.PUBLIC_COMPANY, Signal.WIKIPEDIA_INFOBOX_PRESENT],
                errors=[],
                duration_ms=50,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "## Business & financial signals" in md
    assert "ACME" in md
    assert "Security software" in md

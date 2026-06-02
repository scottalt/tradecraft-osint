"""Tests for tradecraft.renderers.markdown."""

from __future__ import annotations

from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Evidence,
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
                data={
                    "breaches": [
                        {
                            "name": "AcmeOldLeak",
                            "date": "2019-03-15",
                            "pwn_count": 1500000,
                            "data_classes": ["Email", "Passwords"],
                        }
                    ]
                },
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
                        {
                            "title": "Acme raises $200M Series D",
                            "source": "google_news",
                            "published": "Fri, 16 May 2026 00:00:00 GMT",
                        },
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
                data={
                    "ticker": "ACME",
                    "wikipedia": {"Founded": "2018", "Industry": "Security software"},
                },
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


def test_ai_questions_render_in_deep_dive_section() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(target=target, results=[])
    questions = [
        Question(
            text="Heuristic Q",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=True,
        ),
        Question(
            text="AI Q one",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=None,
            source_collector="ai",
            is_starred=False,
        ),
    ]
    md = render_markdown(findings, questions)
    assert "### Deep dive (AI)" in md
    assert "AI Q one" in md
    # Heuristic question still in top picks
    assert "Heuristic Q" in md


# ---------------------------------------------------------------------------
# Evidence footnote rendering (markdown renderer)
# ---------------------------------------------------------------------------


def _simple_findings() -> Findings:
    target = Target(company_name="Acme", root_url="https://acme.com")
    return Findings(target=target, results=[])


def test_md_evidence_with_url_renders_markdown_link() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $200M",
        url="https://news.example.com/article",
        date="2026-03-11",
        source="news.google",
    )
    q = Question(
        text="Q with evidence",
        confidence="high",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=Signal.RECENT_FUNDING,
        source_collector="news",
        is_starred=True,
        evidence=ev,
    )
    md = render_markdown(_simple_findings(), [q])
    assert "[news.google · 2026-03-11](https://news.example.com/article)" in md


def test_md_evidence_with_url_no_date_renders_link_without_date() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $200M",
        url="https://news.example.com/article",
        date=None,
        source="news.google",
    )
    q = Question(
        text="Q no date",
        confidence="high",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=Signal.RECENT_FUNDING,
        source_collector="news",
        is_starred=True,
        evidence=ev,
    )
    md = render_markdown(_simple_findings(), [q])
    assert "[news.google](https://news.example.com/article)" in md


def test_md_evidence_no_url_renders_source_and_date_no_link() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $200M",
        url=None,
        date="2026-03-11",
        source="hn",
    )
    q = Question(
        text="Q no url",
        confidence="high",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=Signal.RECENT_FUNDING,
        source_collector="news",
        is_starred=True,
        evidence=ev,
    )
    md = render_markdown(_simple_findings(), [q])
    assert "hn · 2026-03-11" in md
    assert "](http" not in md


def test_md_evidence_none_heuristic_shows_signal_from_collector() -> None:
    q = Question(
        text="Check CSP",
        confidence="high",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=Signal.MISSING_CSP,
        source_collector="footprint",
        is_starred=True,
        evidence=None,
    )
    md = render_markdown(_simple_findings(), [q])
    assert "`missing_csp` from `footprint`" in md


def test_md_ai_question_shows_ai_deep_dive_footnote() -> None:
    q = Question(
        text="AI question",
        confidence="high",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=None,
        source_collector="ai",
        is_starred=False,
        evidence=None,
    )
    md = render_markdown(_simple_findings(), [q])
    assert "AI deep-dive (`ai`)" in md


# ---------------------------------------------------------------------------
# Content-density floor note (markdown renderer)
# ---------------------------------------------------------------------------


def test_md_density_note_shown_when_all_heuristic_have_no_evidence() -> None:
    q = Question(
        text="Evidence-free question",
        confidence="med",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=Signal.MISSING_CSP,
        source_collector="footprint",
        is_starred=False,
        evidence=None,
    )
    md = render_markdown(_simple_findings(), [q])
    assert "Limited recent public material" in md


def test_md_density_note_not_shown_when_evidence_backed_question_exists() -> None:
    ev = Evidence(
        signal=Signal.RECENT_FUNDING,
        summary="Acme raises $200M",
        url="https://example.com",
        date="2026-01-01",
        source="news.google",
    )
    q_with_ev = Question(
        text="Q with evidence",
        confidence="high",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=Signal.RECENT_FUNDING,
        source_collector="news",
        is_starred=True,
        evidence=ev,
    )
    q_no_ev = Question(
        text="Q without evidence",
        confidence="med",
        role_tags={Role.CYBERSECURITY},
        evidence_signal=Signal.MISSING_CSP,
        source_collector="footprint",
        is_starred=False,
        evidence=None,
    )
    md = render_markdown(_simple_findings(), [q_with_ev, q_no_ev])
    assert "Limited recent public material" not in md


def test_md_density_note_not_shown_for_empty_questions() -> None:
    md = render_markdown(_simple_findings(), [])
    assert "Limited recent public material" not in md
    assert "No heuristic-driven questions generated" in md

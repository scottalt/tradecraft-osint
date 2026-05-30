"""End-to-end v0.2.0: CLI through all 9 collectors with mocked endpoints."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import respx
from typer.testing import CliRunner

from tradecraft.cli import app
from tradecraft.collectors.breaches import BreachesCollector
from tradecraft.collectors.business import BusinessCollector
from tradecraft.collectors.company import CompanyCollector
from tradecraft.collectors.footprint import FootprintCollector
from tradecraft.collectors.github import GitHubCollector
from tradecraft.collectors.job import JobCollector
from tradecraft.collectors.ma import MaCollector
from tradecraft.collectors.news import NewsCollector
from tradecraft.collectors.people import PeopleCollector


@respx.mock
def test_full_v0_2_run(tmp_path: Path, fixtures_dir: Path) -> None:
    # --- robots.txt for acme.com (fetched by HttpClient for robots enforcement) ---
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))

    # --- footprint deps ---
    # crt.sh uses query params: ?q=acme.com&output=json
    respx.get("https://crt.sh/", params={"q": "acme.com", "output": "json"}).mock(
        return_value=httpx.Response(200, json=[{"name_value": "acme.com\nwww.acme.com"}])
    )
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers={"server": "nginx"})
    )
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    # --- breaches (HIBP uses ?domain= query param) ---
    respx.get(
        "https://haveibeenpwned.com/api/v3/breaches",
        params={"domain": "acme.com"},
    ).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "Name": "OldLeak",
                    "BreachDate": "2019-01-01",
                    "PwnCount": 10000,
                    "DataClasses": ["Email"],
                    "IsVerified": True,
                    "Domain": "acme.com",
                }
            ],
        )
    )

    # --- github: company_slug for "Acme Corporation" is "acme-corporation" ---
    respx.get("https://api.github.com/orgs/acme-corporation").mock(
        return_value=httpx.Response(200, json={"login": "acme-corporation", "public_repos": 47})
    )
    respx.get(
        "https://api.github.com/orgs/acme-corporation/repos",
        params={"per_page": "100", "sort": "updated"},
    ).mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": f"r{i}",
                    "language": "Go",
                    "pushed_at": "2026-05-20T00:00:00Z",
                    "stargazers_count": 5,
                    "fork": False,
                    "archived": False,
                }
                for i in range(12)
            ],
        )
    )

    # --- news: URL-encoded company name ---
    respx.get(
        "https://news.google.com/rss/search",
        params={"q": "Acme+Corporation"},
    ).mock(
        return_value=httpx.Response(
            200,
            text=(
                "<rss><channel><item><title>Acme raises Series D</title>"
                "<link>https://x.test/a</link>"
                "<pubDate>Fri, 16 May 2026 00:00:00 GMT</pubDate>"
                "</item></channel></rss>"
            ),
        )
    )
    respx.get(
        "https://hn.algolia.com/api/v1/search",
        params={"query": "Acme+Corporation", "tags": "story"},
    ).mock(return_value=httpx.Response(200, json={"hits": []}))

    # --- company paths on acme.com ---
    respx.get("https://acme.com/about").mock(
        return_value=httpx.Response(
            200,
            text="<html><h1>About Acme</h1><h2>Products</h2></html>",
        )
    )
    # remaining company paths → 404
    for path in ("/about-us", "/team", "/leadership", "/careers", "/press", "/blog"):
        respx.get(f"https://acme.com{path}").mock(return_value=httpx.Response(404))

    # --- people paths on acme.com (blog already covered above; add rest) ---
    for path in ("/engineering", "/engineering-blog", "/eng-blog"):
        respx.get(f"https://acme.com{path}").mock(return_value=httpx.Response(404))

    # --- job (greenhouse.io — not robots-checked since not acme.com) ---
    respx.get("https://boards.greenhouse.io/acme/jobs/1").mock(
        return_value=httpx.Response(
            200,
            text=(
                "<html><h1 class='app-title'>Sec Eng</h1>"
                "<div id='content'>Go, Kubernetes</div></html>"
            ),
        )
    )

    # --- business ---
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(
            200,
            json={"0": {"cik_str": 1, "ticker": "ACME", "title": "Acme Corporation"}},
        )
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(
            200,
            text=(
                "<html><table class='infobox'>"
                "<tr><th>Industry</th><td>Security</td></tr>"
                "<tr><th>Subsidiaries</th><td>A, B, C, D, E</td></tr>"
                "</table></html>"
            ),
        )
    )

    # --- wildcard fallback for any unmocked URL → 404 ---
    respx.get(re.compile(r".*")).mock(return_value=httpx.Response(404))

    # --- DNS mock for footprint ---
    dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})
    runner = CliRunner()
    with patch(
        "tradecraft.cli._default_collectors",
        return_value=[
            FootprintCollector(_dns_lookup=dns),
            BreachesCollector(),
            GitHubCollector(),
            NewsCollector(),
            CompanyCollector(),
            JobCollector(),
            PeopleCollector(),
            BusinessCollector(),
            MaCollector(),
        ],
    ):
        result = runner.invoke(
            app,
            [
                "https://acme.com",
                "--company",
                "Acme Corporation",
                "--job",
                "https://boards.greenhouse.io/acme/jobs/1",
                "--role",
                "cybersecurity",
                "--output",
                str(tmp_path),
            ],
        )
    assert result.exit_code == 0, result.stdout

    [folder] = list(tmp_path.iterdir())
    report = (folder / "report.md").read_text(encoding="utf-8")
    raw = json.loads((folder / "raw.json").read_text(encoding="utf-8"))

    # Each collector's section heading should be present.
    for heading in (
        "## Snapshot",
        "## Web & infrastructure footprint",
        "## Company profile",
        "## Role-fit signals (from JD)",
        "## GitHub presence",
        "## News & timeline",
        "## Breach history",
        "## Business & financial signals",
        "## Mergers & acquisitions",
        "## People",
        "## Questions to ask",
        "## Collection notes",
    ):
        assert heading in report, f"missing section: {heading}"

    # At least one question must fire under cybersec role with the broader template library.
    assert len(raw["questions"]) > 0

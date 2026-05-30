"""Tests for tradecraft.collectors.github."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.github import GitHubCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, object]:
    return {
        "org": json.loads((fixtures_dir / "github" / "org_acme.json").read_text()),
        "repos": json.loads((fixtures_dir / "github" / "repos_acme.json").read_text()),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = GitHubCollector()
    assert c.name == "github"
    assert c.safe_for_hosted is True
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_oss_forward_culture(http, fixtures) -> None:
    client, cache = http
    respx.get("https://api.github.com/orgs/acme").mock(
        return_value=httpx.Response(200, json=fixtures["org"])
    )
    respx.get("https://api.github.com/orgs/acme/repos").mock(
        return_value=httpx.Response(200, json=fixtures["repos"])
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await GitHubCollector().run(ctx)

    assert Signal.OSS_FORWARD_CULTURE in result.signals
    assert Signal.NO_PUBLIC_GITHUB not in result.signals
    assert result.data["org"]["login"] == "acme"
    assert result.data["repo_count"] >= 10


@respx.mock
async def test_no_public_github_when_404(http) -> None:
    client, cache = http
    respx.get("https://api.github.com/orgs/acme").mock(return_value=httpx.Response(404))
    target = Target(company_name="Acme Corp", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await GitHubCollector().run(ctx)

    assert Signal.NO_PUBLIC_GITHUB in result.signals


@respx.mock
async def test_languages_aggregated(http, fixtures) -> None:
    client, cache = http
    respx.get("https://api.github.com/orgs/acme").mock(
        return_value=httpx.Response(200, json=fixtures["org"])
    )
    respx.get("https://api.github.com/orgs/acme/repos").mock(
        return_value=httpx.Response(200, json=fixtures["repos"])
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await GitHubCollector().run(ctx)

    languages = result.data["languages"]
    assert "Go" in languages
    assert "TypeScript" in languages

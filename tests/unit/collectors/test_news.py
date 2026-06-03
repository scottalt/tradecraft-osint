"""Tests for tradecraft.collectors.news."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.news import (
    NEWS_MAX_AGE_DAYS,
    NewsCollector,
    _apply_recency_filter,
    _apply_relevance_filter,
    _parse_date_iso,
)
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, object]:
    return {
        "rss": (fixtures_dir / "news" / "google_news_acme.xml").read_text(),
        "hn": json.loads((fixtures_dir / "news" / "hn_algolia_acme.json").read_text()),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = NewsCollector()
    assert c.name == "news"
    assert c.safe_for_hosted is True
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_signal_extraction_from_headlines(http, fixtures) -> None:
    client, cache = http
    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text=str(fixtures["rss"]))
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json=fixtures["hn"])
    )
    target = Target(company_name="Acme Corp", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_FUNDING in result.signals  # "raises $200M Series D"
    assert Signal.RECENT_LEADERSHIP_CHANGE in result.signals  # "CEO ... steps down"
    assert Signal.RECENT_SECURITY_INCIDENT in result.signals  # "data breach"
    assert Signal.RECENT_LAYOFFS in result.signals  # "workforce reduction"
    assert len(result.data["items"]) >= 4


@respx.mock
async def test_empty_feeds_no_signals(http) -> None:
    client, cache = http
    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json={"hits": []})
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    for s in (
        Signal.RECENT_FUNDING,
        Signal.RECENT_LAYOFFS,
        Signal.RECENT_SECURITY_INCIDENT,
        Signal.RECENT_LEADERSHIP_CHANGE,
    ):
        assert s not in result.signals


# ---------------------------------------------------------------------------
# Unit tests for _parse_date_iso
# ---------------------------------------------------------------------------


def test_parse_date_iso_google_news_struct_time() -> None:
    """RSS items with a valid published_parsed time.struct_time parse to ISO date."""
    # struct_time for 2026-03-15
    st = time.struct_time((2026, 3, 15, 10, 0, 0, 0, 0, 0))
    item = {"source": "google_news", "published_parsed": st, "published": ""}
    assert _parse_date_iso(item) == "2026-03-15"


def test_parse_date_iso_google_news_missing_struct_time() -> None:
    """RSS items without published_parsed return None."""
    item = {"source": "google_news", "published_parsed": None, "published": ""}
    assert _parse_date_iso(item) is None


def test_parse_date_iso_hn_iso_string() -> None:
    """HN items with ISO 8601 created_at parse to YYYY-MM-DD date portion."""
    # Dict shape mirrors what run() builds: key is "created_at", not "published"
    item = {"source": "hn", "created_at": "2026-03-11T12:00:00.000Z"}
    assert _parse_date_iso(item) == "2026-03-11"


def test_parse_date_iso_hn_missing() -> None:
    """HN items without created_at return None."""
    # Dict shape mirrors what run() builds: key is "created_at", not "published"
    item = {"source": "hn", "created_at": ""}
    assert _parse_date_iso(item) is None


def test_parse_date_iso_unknown_source() -> None:
    """Items from unknown source return None."""
    item = {"source": "unknown", "published": "2026-03-11T12:00:00Z"}
    assert _parse_date_iso(item) is None


# ---------------------------------------------------------------------------
# Unit tests for _apply_recency_filter
# ---------------------------------------------------------------------------


def _make_item(title: str, date_iso: str | None, source: str = "hn") -> dict:
    return {"title": title, "url": "", "source": source, "date_iso": date_iso}


def test_recency_filter_keeps_recent_item() -> None:
    today = datetime.now(tz=UTC)
    recent_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    items = [_make_item("Recent headline", recent_date)]
    result = _apply_recency_filter(items, today)
    assert len(result) == 1


def test_recency_filter_drops_stale_item() -> None:
    today = datetime.now(tz=UTC)
    stale_date = (today - timedelta(days=NEWS_MAX_AGE_DAYS + 10)).strftime("%Y-%m-%d")
    items = [_make_item("Old headline", stale_date)]
    result = _apply_recency_filter(items, today)
    assert len(result) == 0


def test_recency_filter_keeps_undated_item() -> None:
    """Items with no parseable date are kept (fail-open)."""
    today = datetime.now(tz=UTC)
    items = [_make_item("No date headline", None)]
    result = _apply_recency_filter(items, today)
    assert len(result) == 1


def test_recency_filter_boundary_one_day_inside() -> None:
    """An item one day inside the cutoff window (364 days ago) is kept."""
    today = datetime.now(tz=UTC)
    inside_date = (today - timedelta(days=NEWS_MAX_AGE_DAYS - 1)).strftime("%Y-%m-%d")
    items = [_make_item("Near-boundary headline", inside_date)]
    result = _apply_recency_filter(items, today)
    assert len(result) == 1


def test_recency_filter_boundary_exact_cutoff() -> None:
    """An item dated exactly today - NEWS_MAX_AGE_DAYS is KEPT (cutoff is inclusive)."""
    today = datetime.now(tz=UTC)
    exact_cutoff_date = (today - timedelta(days=NEWS_MAX_AGE_DAYS)).strftime("%Y-%m-%d")
    items = [_make_item("Exact-cutoff headline", exact_cutoff_date)]
    result = _apply_recency_filter(items, today)
    assert len(result) == 1


def test_recency_filter_mixed_items() -> None:
    today = datetime.now(tz=UTC)
    recent = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    stale = (today - timedelta(days=400)).strftime("%Y-%m-%d")
    items = [
        _make_item("Recent", recent),
        _make_item("Stale", stale),
        _make_item("Undated", None),
    ]
    result = _apply_recency_filter(items, today)
    assert len(result) == 2
    titles = [i["title"] for i in result]
    assert "Recent" in titles
    assert "Undated" in titles
    assert "Stale" not in titles


# ---------------------------------------------------------------------------
# Unit tests for _apply_relevance_filter
# ---------------------------------------------------------------------------


def test_relevance_filter_keeps_matching_title() -> None:
    items = [_make_item("Acme Corp raises funding", None)]
    result = _apply_relevance_filter(items, "Acme Corp")
    assert len(result) == 1


def test_relevance_filter_drops_namesake_title() -> None:
    """Title with no company token is dropped."""
    items = [_make_item("Totally unrelated news story", None)]
    result = _apply_relevance_filter(items, "Acme Corp")
    assert len(result) == 0


def test_relevance_filter_case_insensitive() -> None:
    items = [_make_item("ACME CORP announces layoffs", None)]
    result = _apply_relevance_filter(items, "Acme Corp")
    assert len(result) == 1


def test_relevance_filter_ignores_short_tokens() -> None:
    """Tokens shorter than 3 chars are skipped; only longer tokens must match."""
    # "Co" is length 2 — skipped. "AB" is length 2 — skipped. "Inc" is length 3 — kept.
    items = [
        _make_item("Inc raises a seed round", None),
        _make_item("No match here at all", None),
    ]
    result = _apply_relevance_filter(items, "AB Co Inc")
    # Only "Inc" is a usable token (len >= 3)
    assert len(result) == 1
    assert result[0]["title"] == "Inc raises a seed round"


def test_relevance_filter_no_usable_tokens_keeps_all() -> None:
    """Company name with all short tokens (< 3) means no filtering — keep everything."""
    items = [_make_item("Completely irrelevant", None), _make_item("Also irrelevant", None)]
    result = _apply_relevance_filter(items, "AB Co")
    assert len(result) == 2


def test_relevance_filter_word_boundary_excludes_substring_match() -> None:
    """Company name 'Arm' must NOT match a title containing 'alarming' (substring false-positive)."""
    items = [_make_item("Alarming breach at OtherCo", None)]
    result = _apply_relevance_filter(items, "Arm")
    assert len(result) == 0


def test_relevance_filter_word_boundary_keeps_exact_word_match() -> None:
    """Company name 'Arm' MUST match a title where 'Arm' appears as a whole word."""
    items = [_make_item("Arm announces new chip architecture", None)]
    result = _apply_relevance_filter(items, "Arm")
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Integration-style tests: Evidence attachment via NewsCollector.run
# ---------------------------------------------------------------------------


def _make_rss_xml(items: list[dict]) -> str:
    """Build a minimal RSS XML string from a list of {title, link, pubDate} dicts."""
    entries = ""
    for item in items:
        entries += f"""
    <item>
      <title>{item["title"]}</title>
      <link>{item.get("link", "")}</link>
      <pubDate>{item.get("pubDate", "")}</pubDate>
    </item>"""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    {entries}
  </channel>
</rss>"""


def _make_hn_json(hits: list[dict]) -> dict:
    return {"hits": hits}


@respx.mock
async def test_evidence_attached_for_fired_signal(http) -> None:
    """A fired signal gets an Evidence whose summary matches the headline."""
    client, cache = http
    today = datetime.now(tz=UTC)
    recent = (today - timedelta(days=20)).strftime("%a, %d %b %Y 00:00:00 GMT")

    rss = _make_rss_xml(
        [
            {
                "title": "Acme Corp raises $100M Series B",
                "link": "https://ex.test/a",
                "pubDate": recent,
            }
        ]
    )
    respx.get("https://news.google.com/rss/search").mock(return_value=httpx.Response(200, text=rss))
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json={"hits": []})
    )
    target = Target(company_name="Acme Corp", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_FUNDING in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.RECENT_FUNDING), None)
    assert ev is not None
    assert ev.summary == "Acme Corp raises $100M Series B"
    assert ev.url == "https://ex.test/a"
    assert ev.source == "news.google"
    assert ev.date is not None  # parsed from pubDate
    # Fix 5: assert exact YYYY-MM-DD value, not just non-None
    expected_date = (today - timedelta(days=20)).strftime("%Y-%m-%d")
    assert ev.date == expected_date


@respx.mock
async def test_evidence_source_hn(http) -> None:
    """Evidence from HN items has source == 'hn'."""
    client, cache = http
    today = datetime.now(tz=UTC)
    recent_iso = (today - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme confirms data breach affecting customers",
                        "url": "https://hn.test/acme-breach",
                        "created_at": recent_iso,
                    }
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_SECURITY_INCIDENT in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.RECENT_SECURITY_INCIDENT), None)
    assert ev is not None
    assert ev.source == "hn"
    assert ev.summary == "Acme confirms data breach affecting customers"


@respx.mock
async def test_evidence_most_recent_item_wins(http) -> None:
    """When multiple items match a signal, the most recent one becomes Evidence."""
    client, cache = http
    today = datetime.now(tz=UTC)
    older_iso = (today - timedelta(days=60)).strftime("%Y-%m-%dT00:00:00Z")
    newer_iso = (today - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme announces layoffs affecting 5% of workforce",
                        "url": "https://hn.test/old-layoffs",
                        "created_at": older_iso,
                    },
                    {
                        "title": "Acme second round of layoffs hits engineering",
                        "url": "https://hn.test/new-layoffs",
                        "created_at": newer_iso,
                    },
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_LAYOFFS in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.RECENT_LAYOFFS), None)
    assert ev is not None
    assert ev.url == "https://hn.test/new-layoffs"
    assert ev.summary == "Acme second round of layoffs hits engineering"


@respx.mock
async def test_signal_does_not_fire_when_only_stale_match(http) -> None:
    """A signal does NOT fire (and no evidence) when the only matching item is stale."""
    client, cache = http
    today = datetime.now(tz=UTC)
    stale_iso = (today - timedelta(days=NEWS_MAX_AGE_DAYS + 30)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme raises Series A funding round",
                        "url": "https://hn.test/old-funding",
                        "created_at": stale_iso,
                    }
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_FUNDING not in result.signals
    assert not any(e.signal == Signal.RECENT_FUNDING for e in result.evidence)


@respx.mock
async def test_signal_does_not_fire_when_only_irrelevant_match(http) -> None:
    """A signal does NOT fire when the only matching item is filtered by relevance."""
    client, cache = http
    today = datetime.now(tz=UTC)
    recent_iso = (today - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        # No mention of "Acme" — should be filtered by relevance
                        "title": "Startup raises $50M Series B funding round",
                        "url": "https://hn.test/unrelated-funding",
                        "created_at": recent_iso,
                    }
                ]
            ),
        )
    )
    target = Target(company_name="Acme Corp", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_FUNDING not in result.signals
    assert not any(e.signal == Signal.RECENT_FUNDING for e in result.evidence)


@respx.mock
async def test_javascript_url_in_rss_item_yields_none_evidence_url(http) -> None:
    """A news item with a javascript: link must NOT produce Evidence.url (XSS hardening)."""
    client, cache = http
    today = datetime.now(tz=UTC)
    recent = (today - timedelta(days=5)).strftime("%a, %d %b %Y 00:00:00 GMT")

    rss = _make_rss_xml(
        [
            {
                "title": "Acme Corp raises $50M Series C",
                "link": "javascript:alert('xss')",
                "pubDate": recent,
            }
        ]
    )
    respx.get("https://news.google.com/rss/search").mock(return_value=httpx.Response(200, text=rss))
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json={"hits": []})
    )
    target = Target(company_name="Acme Corp", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_FUNDING in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.RECENT_FUNDING), None)
    assert ev is not None
    assert ev.url is None, f"Expected url=None for javascript: link, got {ev.url!r}"


@respx.mock
async def test_data_url_in_hn_item_yields_none_evidence_url(http) -> None:
    """A HN item with a data: link must NOT produce Evidence.url (XSS hardening)."""
    client, cache = http
    today = datetime.now(tz=UTC)
    recent_iso = (today - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme announces layoffs",
                        "url": "data:text/html,<script>alert(1)</script>",
                        "created_at": recent_iso,
                    }
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_LAYOFFS in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.RECENT_LAYOFFS), None)
    assert ev is not None
    assert ev.url is None, f"Expected url=None for data: link, got {ev.url!r}"


@respx.mock
async def test_evidence_iso_date_correct(http) -> None:
    """Evidence date field is correct ISO YYYY-MM-DD for both sources."""
    client, cache = http
    today = datetime.now(tz=UTC)
    hn_date = (today - timedelta(days=15)).strftime("%Y-%m-%d")
    hn_iso = f"{hn_date}T08:30:00.000Z"

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme appoints new CEO from Google",
                        "url": "https://hn.test/acme-ceo",
                        "created_at": hn_iso,
                    }
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_LEADERSHIP_CHANGE in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.RECENT_LEADERSHIP_CHANGE), None)
    assert ev is not None
    assert ev.date == hn_date


# ---------------------------------------------------------------------------
# RECENT_NEWS catch-all: notable news matching none of the 4 category patterns
# ---------------------------------------------------------------------------


@respx.mock
async def test_recent_news_catchall_fires_for_uncategorized_item(http) -> None:
    """An uncategorized but recent+relevant headline (e.g. an acquisition) fires
    RECENT_NEWS with that headline as Evidence."""
    client, cache = http
    today = datetime.now(tz=UTC)
    recent_iso = (today - timedelta(days=4)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme acquires Foobar Inc to expand platform",
                        "url": "https://hn.test/acme-acquires",
                        "created_at": recent_iso,
                    }
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_NEWS in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.RECENT_NEWS), None)
    assert ev is not None
    assert ev.summary == "Acme acquires Foobar Inc to expand platform"
    assert ev.source == "hn"
    assert ev.date == (today - timedelta(days=4)).strftime("%Y-%m-%d")


@respx.mock
async def test_recent_news_catchall_does_not_fire_when_all_categorized(http) -> None:
    """If every recent+relevant item already matches a category pattern (e.g. only
    a layoffs headline), RECENT_NEWS does NOT fire."""
    client, cache = http
    today = datetime.now(tz=UTC)
    recent_iso = (today - timedelta(days=4)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme announces layoffs affecting 5% of staff",
                        "url": "https://hn.test/acme-layoffs",
                        "created_at": recent_iso,
                    }
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_LAYOFFS in result.signals
    assert Signal.RECENT_NEWS not in result.signals
    assert not any(e.signal == Signal.RECENT_NEWS for e in result.evidence)


@respx.mock
async def test_recent_news_catchall_most_recent_uncategorized_wins(http) -> None:
    """Among several uncategorized items, the most-recent one becomes Evidence;
    a categorized item is ignored for RECENT_NEWS."""
    client, cache = http
    today = datetime.now(tz=UTC)
    older_iso = (today - timedelta(days=40)).strftime("%Y-%m-%dT00:00:00Z")
    newer_iso = (today - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00Z")
    layoff_iso = (today - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme launches new analytics product",
                        "url": "https://hn.test/acme-old-launch",
                        "created_at": older_iso,
                    },
                    {
                        "title": "Acme partners with Globex on cloud platform",
                        "url": "https://hn.test/acme-partner",
                        "created_at": newer_iso,
                    },
                    {
                        # categorized (layoffs) — must NOT be picked for RECENT_NEWS
                        "title": "Acme announces layoffs",
                        "url": "https://hn.test/acme-layoffs",
                        "created_at": layoff_iso,
                    },
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_NEWS in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.RECENT_NEWS), None)
    assert ev is not None
    assert ev.summary == "Acme partners with Globex on cloud platform"
    assert ev.url == "https://hn.test/acme-partner"


# ---------------------------------------------------------------------------
# Financial-press noise: never used as Evidence (kept in raw items)
# ---------------------------------------------------------------------------


@respx.mock
async def test_financial_noise_not_used_as_recent_news_evidence(http) -> None:
    """Stock/market-press headlines (buyback, insider sale, Zacks) are kept in the
    raw items list but never selected as RECENT_NEWS Evidence; a substantive
    headline wins instead."""
    client, cache = http
    today = datetime.now(tz=UTC)
    noise_iso = (today - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    substantive_iso = (today - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme Board Authorizes $3 Billion Share Repurchase Program",
                        "url": "https://hn.test/acme-buyback",
                        "created_at": noise_iso,
                    },
                    {
                        "title": "Acme director sells 3,265 shares",
                        "url": "https://hn.test/acme-insider",
                        "created_at": noise_iso,
                    },
                    {
                        "title": "Acme Zacks Investment Ideas feature",
                        "url": "https://hn.test/acme-zacks",
                        "created_at": noise_iso,
                    },
                    {
                        "title": "Acme launches enterprise observability platform",
                        "url": "https://hn.test/acme-launch",
                        "created_at": substantive_iso,
                    },
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    # Noise headlines are still present in the raw items list.
    titles = {i["title"] for i in result.data["items"]}
    assert "Acme Board Authorizes $3 Billion Share Repurchase Program" in titles
    assert "Acme director sells 3,265 shares" in titles

    assert Signal.RECENT_NEWS in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.RECENT_NEWS), None)
    assert ev is not None
    # The substantive headline wins despite being older than the noise.
    assert ev.summary == "Acme launches enterprise observability platform"


@respx.mock
async def test_valuation_no_longer_triggers_recent_funding(http) -> None:
    """A 'valuation' note is stock noise, not a funding round — RECENT_FUNDING
    must NOT fire (the pattern no longer includes 'valuation')."""
    client, cache = http
    today = datetime.now(tz=UTC)
    recent_iso = (today - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme hits $369B valuation amid market rally",
                        "url": "https://hn.test/acme-valuation",
                        "created_at": recent_iso,
                    }
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_FUNDING not in result.signals
    # It's also financial noise, so it isn't used as RECENT_NEWS evidence either.
    assert not any(e.signal == Signal.RECENT_FUNDING for e in result.evidence)
    assert not any(e.signal == Signal.RECENT_NEWS for e in result.evidence)


@respx.mock
async def test_fedramp_headline_fires_compliance_noted(http) -> None:
    """A compliance-framework headline (e.g. 'FedRAMP High Certification') fires
    COMPLIANCE_NOTED with that headline as Evidence — a GRC interview hook."""
    client, cache = http
    today = datetime.now(tz=UTC)
    recent_iso = (today - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00Z")

    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(
            200,
            json=_make_hn_json(
                [
                    {
                        "title": "Acme achieves FedRAMP High Certification",
                        "url": "https://hn.test/acme-fedramp",
                        "created_at": recent_iso,
                    }
                ]
            ),
        )
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.COMPLIANCE_NOTED in result.signals
    ev = next((e for e in result.evidence if e.signal == Signal.COMPLIANCE_NOTED), None)
    assert ev is not None
    assert ev.summary == "Acme achieves FedRAMP High Certification"
    assert ev.source == "hn"

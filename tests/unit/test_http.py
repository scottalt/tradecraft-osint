"""Tests for tradecraft.http (HttpClient)."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft import __version__
from tradecraft.cache import Cache
from tradecraft.config import HttpConfig
from tradecraft.ethics import RobotsDisallowed
from tradecraft.http import HttpClient


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(directory=tmp_path, default_ttl=60)


@pytest.fixture
def cfg() -> HttpConfig:
    return HttpConfig(
        per_host_rps=100.0,  # disable for most tests
        global_concurrency=5,
        max_response_bytes=10_000,
        request_timeout_seconds=5.0,
        max_retries=2,
    )


@pytest.fixture
async def client(cfg: HttpConfig, cache: Cache):
    async with HttpClient(cfg, cache) as c:
        yield c


@respx.mock
async def test_get_returns_response(cfg: HttpConfig, cache: Cache) -> None:
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://example.com/").mock(return_value=httpx.Response(200, text="hello"))
    async with HttpClient(cfg, cache) as client:
        resp = await client.get("https://example.com/")
    assert resp.status_code == 200
    assert resp.text == "hello"


@respx.mock
async def test_user_agent_is_identifying(cfg: HttpConfig, cache: Cache) -> None:
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    route = respx.get("https://example.com/").mock(return_value=httpx.Response(200, text="ok"))
    async with HttpClient(cfg, cache) as client:
        await client.get("https://example.com/")
    ua = route.calls[0].request.headers["user-agent"]
    assert "tradecraft" in ua
    assert __version__ in ua
    assert "interview-prep" in ua


@respx.mock
async def test_response_served_from_cache_on_second_call(cfg: HttpConfig, cache: Cache) -> None:
    # robots.txt is fetched once for the host, then the main URL fetched once;
    # the second client.get() should be served from cache without hitting the network.
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    route = respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="hello", headers={"content-type": "text/plain"})
    )
    async with HttpClient(cfg, cache) as client:
        r1 = await client.get("https://example.com/")
        r2 = await client.get("https://example.com/")
    assert r1.text == r2.text == "hello"
    assert route.call_count == 1


@respx.mock
async def test_oversized_response_raises(cfg: HttpConfig, cache: Cache) -> None:
    big = "x" * 20_000
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://example.com/").mock(return_value=httpx.Response(200, text=big))
    async with HttpClient(cfg, cache) as client:
        with pytest.raises(ValueError, match="response too large"):
            await client.get("https://example.com/")


@respx.mock
async def test_retries_on_5xx_then_succeeds(cfg: HttpConfig, cache: Cache) -> None:
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    route = respx.get("https://example.com/").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, text="recovered"),
        ]
    )
    async with HttpClient(cfg, cache) as client:
        resp = await client.get("https://example.com/")
    assert resp.text == "recovered"
    assert route.call_count == 2


@respx.mock
async def test_redirect_to_private_ip_is_blocked(cfg: HttpConfig, cache: Cache) -> None:
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(302, headers={"location": "http://127.0.0.1/"})
    )
    async with HttpClient(cfg, cache) as client:
        with pytest.raises(ValueError, match="private"):
            await client.get("https://example.com/")


async def test_per_host_rate_limit_enforced(tmp_path: Path) -> None:
    # Use cache with enabled=False so every request hits the bucket (no cache shortcuts).
    no_cache = Cache(directory=tmp_path, default_ttl=60, enabled=False)
    cfg = HttpConfig(per_host_rps=2.0, global_concurrency=5, max_response_bytes=10_000)
    async with respx.mock(assert_all_called=False) as mock:
        mock.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
        mock.get("https://example.com/").mock(return_value=httpx.Response(200, text="ok"))
        async with HttpClient(cfg, no_cache) as client:
            start = time.monotonic()
            await asyncio.gather(*(client.get("https://example.com/") for _ in range(3)))
            elapsed = time.monotonic() - start
        # 3 requests at 2 rps => at least one ~0.5s wait => total >= 0.5s
        assert elapsed >= 0.4


# ---------------------------------------------------------------------------
# Robots.txt enforcement tests
# ---------------------------------------------------------------------------


@respx.mock
async def test_robots_disallowed_raises(cfg: HttpConfig, cache: Cache) -> None:
    respx.get("https://example.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /admin/\n")
    )
    respx.get("https://example.com/admin/secret").mock(
        return_value=httpx.Response(200, text="should never be fetched")
    )
    async with HttpClient(cfg, cache) as client:
        with pytest.raises(RobotsDisallowed):
            await client.get("https://example.com/admin/secret")


@respx.mock
async def test_robots_respected_false_bypasses_check(cfg: HttpConfig, cache: Cache) -> None:
    respx.get("https://example.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /admin/\n")
    )
    route = respx.get("https://example.com/admin/secret").mock(
        return_value=httpx.Response(200, text="ok")
    )
    async with HttpClient(cfg, cache, respect_robots=False) as client:
        resp = await client.get("https://example.com/admin/secret")
    assert resp.text == "ok"
    # the robots.txt route should NOT have been called when respect_robots=False
    assert route.call_count == 1


@respx.mock
async def test_robots_404_treated_as_allow_all(cfg: HttpConfig, cache: Cache) -> None:
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://example.com/anywhere").mock(return_value=httpx.Response(200, text="ok"))
    async with HttpClient(cfg, cache) as client:
        resp = await client.get("https://example.com/anywhere")
    assert resp.text == "ok"


@respx.mock
async def test_relative_redirect_to_private_blocked(cfg: HttpConfig, cache: Cache) -> None:
    # robots fetched first; allow everything
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    # Server returns an absolute redirect to a private IP; confirm the guard
    # fires after our absolutization refactor.
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(302, headers={"location": "http://10.0.0.1/secret"})
    )
    async with HttpClient(cfg, cache) as client:
        with pytest.raises(ValueError, match="private"):
            await client.get("https://example.com/")


@respx.mock
async def test_redirect_count_capped(cache: Cache) -> None:
    cfg = HttpConfig(
        per_host_rps=100.0,
        global_concurrency=5,
        max_response_bytes=10_000,
        max_retries=10,
        max_redirects=2,
    )
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(302, headers={"location": "https://example.com/a"})
    )
    respx.get("https://example.com/a").mock(
        return_value=httpx.Response(302, headers={"location": "https://example.com/b"})
    )
    respx.get("https://example.com/b").mock(
        return_value=httpx.Response(302, headers={"location": "https://example.com/c"})
    )
    respx.get("https://example.com/c").mock(
        return_value=httpx.Response(200, text="should not reach")
    )
    async with HttpClient(cfg, cache) as client:
        with pytest.raises(ValueError, match="too many redirects"):
            await client.get("https://example.com/")

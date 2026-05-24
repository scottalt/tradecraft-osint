"""Async HTTP client with polite UA, per-host rate limit, retry, and caching."""

from __future__ import annotations

import asyncio
import ipaddress
import time
from collections import defaultdict
from types import TracebackType
from urllib.parse import urlparse

import httpx

from tradecraft import __version__
from tradecraft.cache import Cache
from tradecraft.config import HttpConfig


def _user_agent() -> str:
    return (
        f"tradecraft/{__version__} (+https://github.com/scottaltiparmak/tradecraft) interview-prep"
    )


def _is_private_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host.lower() in {"localhost", "localhost.localdomain"}
    return ip.is_private or ip.is_loopback or ip.is_link_local


class _TokenBucket:
    """Simple per-host token bucket. Acquire blocks until a token is available."""

    def __init__(self, rate_per_second: float) -> None:
        self.rate = rate_per_second
        self.tokens = rate_per_second
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
                self.last_refill = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait)


class HttpClient:
    """httpx wrapper enforcing the project's hard rules."""

    def __init__(self, config: HttpConfig, cache: Cache) -> None:
        self.config = config
        self.cache = cache
        self._buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(config.per_host_rps)
        )
        self._sem = asyncio.Semaphore(config.global_concurrency)
        self._client = httpx.AsyncClient(
            http2=True,
            follow_redirects=False,
            timeout=config.request_timeout_seconds,
            headers={"User-Agent": _user_agent()},
        )

    async def __aenter__(self) -> HttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def get(self, url: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
        cache_key = f"GET {url}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return httpx.Response(200, content=cached, request=httpx.Request("GET", url))

        host = urlparse(url).hostname or ""
        if _is_private_host(host):
            raise ValueError(f"refusing to fetch private host: {host}")

        bucket = self._buckets[host]
        async with self._sem:
            return await self._do_get_with_retry(url, headers, bucket, cache_key)

    async def _do_get_with_retry(
        self,
        url: str,
        headers: dict[str, str] | None,
        bucket: _TokenBucket,
        cache_key: str,
    ) -> httpx.Response:
        attempt = 0
        while True:
            await bucket.acquire()
            try:
                response = await self._client.get(url, headers=headers)
            except httpx.HTTPError:
                if attempt >= self.config.max_retries:
                    raise
                attempt += 1
                await asyncio.sleep(self._backoff(attempt))
                continue

            if response.is_redirect:
                self._check_redirect(response)
                if attempt >= self.config.max_retries:
                    return response
                attempt += 1
                url = response.headers.get("location", url)
                continue

            if response.status_code >= 500 and attempt < self.config.max_retries:
                attempt += 1
                wait = self._retry_wait(response, attempt)
                await asyncio.sleep(wait)
                continue

            self._check_size(response)
            self.cache.set(cache_key, response.content)
            return response

    def _check_redirect(self, response: httpx.Response) -> None:
        location = response.headers.get("location", "")
        target_host = urlparse(location).hostname or ""
        if _is_private_host(target_host):
            raise ValueError(f"redirect to private host blocked: {target_host}")

    def _check_size(self, response: httpx.Response) -> None:
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > self.config.max_response_bytes:
            raise ValueError(
                f"response too large: {content_length} > {self.config.max_response_bytes}"
            )
        if len(response.content) > self.config.max_response_bytes:
            raise ValueError(
                f"response too large: {len(response.content)} > {self.config.max_response_bytes}"
            )

    def _retry_wait(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        return float(retry_after) if retry_after else self._backoff(attempt)

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(float(2 ** (attempt - 1)), 8.0)

"""Async HTTP client with polite UA, per-host rate limit, retry, and caching."""

from __future__ import annotations

import asyncio
import ipaddress
import time
from collections import defaultdict
from types import TracebackType
from urllib.parse import urljoin, urlparse

import httpx

from tradecraft import __version__
from tradecraft.cache import Cache
from tradecraft.config import HttpConfig
from tradecraft.ethics import RobotsDisallowed, RobotsPolicy, parse_robots


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

    def __init__(self, config: HttpConfig, cache: Cache, *, respect_robots: bool = True) -> None:
        self.config = config
        self.cache = cache
        self.respect_robots = respect_robots
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
        self._robots_policies: dict[str, RobotsPolicy] = {}
        self._robots_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def __aenter__(self) -> HttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def _get_robots_policy(self, host: str, scheme: str) -> RobotsPolicy:
        """Return (possibly cached) robots policy for the given host."""
        if host in self._robots_policies:
            return self._robots_policies[host]

        async with self._robots_locks[host]:
            # Double-check after acquiring the lock
            if host in self._robots_policies:
                return self._robots_policies[host]

            robots_url = f"{scheme}://{host}/robots.txt"
            try:
                resp = await self._raw_get(robots_url)
                policy = parse_robots(resp.text) if resp.status_code == 200 else RobotsPolicy()
            except Exception:
                policy = RobotsPolicy()  # fetch failure => allow all

            self._robots_policies[host] = policy
            return policy

    async def _raw_get(self, url: str) -> httpx.Response:
        """Fetch a URL directly (no robots check, no cache, no size check).

        Used internally for the robots.txt fetch itself.  Still rate-limited.
        """
        parsed = urlparse(url)
        host = parsed.hostname or ""
        bucket = self._buckets[host]
        async with self._sem:
            await bucket.acquire()
            return await self._client.get(url)

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        cache_key = f"GET {url}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return httpx.Response(200, content=cached, request=httpx.Request("GET", url))

        parsed = urlparse(url)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "https"

        if _is_private_host(host):
            raise ValueError(f"refusing to fetch private host: {host}")

        if self.respect_robots:
            policy = await self._get_robots_policy(host, scheme)
            path = parsed.path or "/"
            if not policy.is_allowed(path):
                raise RobotsDisallowed(url)

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
        redirect_count = 0
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
                raw_location = response.headers.get("location", "")
                absolute_location = urljoin(url, raw_location)
                self._check_redirect(absolute_location)
                redirect_count += 1
                if redirect_count > self.config.max_redirects:
                    raise ValueError(
                        f"too many redirects following {url!r} (limit {self.config.max_redirects})"
                    )
                url = absolute_location
                # Update the bucket for the (potentially new) host
                new_host = urlparse(url).hostname or ""
                bucket = self._buckets[new_host]
                continue

            if response.status_code >= 500 and attempt < self.config.max_retries:
                attempt += 1
                wait = self._retry_wait(response, attempt)
                await asyncio.sleep(wait)
                continue

            self._check_size(response)
            self.cache.set(cache_key, response.content)
            return response

    def _check_redirect(self, absolute_location: str) -> None:
        target_host = urlparse(absolute_location).hostname or ""
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

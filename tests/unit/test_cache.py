"""Tests for tradecraft.cache."""

from __future__ import annotations

from pathlib import Path

import pytest

from tradecraft.cache import Cache


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(directory=tmp_path, default_ttl=60)


def test_set_then_get_returns_value(cache: Cache) -> None:
    cache.set("k", b"hello")
    assert cache.get("k") == b"hello"


def test_get_missing_returns_none(cache: Cache) -> None:
    assert cache.get("nope") is None


def test_expired_entry_returns_none(tmp_path: Path) -> None:
    cache = Cache(directory=tmp_path, default_ttl=0)
    cache.set("k", b"x")
    # ttl=0 means already expired
    assert cache.get("k") is None


def test_per_call_ttl_overrides_default(tmp_path: Path) -> None:
    cache = Cache(directory=tmp_path, default_ttl=0)
    cache.set("k", b"x", ttl=3600)
    assert cache.get("k") == b"x"


def test_disabled_cache_is_noop(tmp_path: Path) -> None:
    cache = Cache(directory=tmp_path, default_ttl=60, enabled=False)
    cache.set("k", b"x")
    assert cache.get("k") is None


def test_clear_wipes_entries(cache: Cache) -> None:
    cache.set("k1", b"x")
    cache.set("k2", b"y")
    cache.clear()
    assert cache.get("k1") is None
    assert cache.get("k2") is None


def test_key_with_path_separators_is_safe(cache: Cache) -> None:
    cache.set("https://example.com/path?q=1", b"safe")
    assert cache.get("https://example.com/path?q=1") == b"safe"

"""Tests for tradecraft.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from tradecraft.config import AppConfig, _coerce, load_config


def test_default_config_has_sensible_values() -> None:
    cfg = AppConfig()
    assert cfg.http.per_host_rps == 1.0
    assert cfg.http.global_concurrency == 5
    assert cfg.http.max_response_bytes == 5 * 1024 * 1024
    assert cfg.http.request_timeout_seconds == 20.0
    assert cfg.http.max_retries == 3
    assert cfg.http.max_redirects == 5
    assert cfg.cache.enabled is True
    assert cfg.cache.ttl_default_seconds == 3600
    assert cfg.cache.directory is None


def test_load_config_from_toml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        """
        [http]
        per_host_rps = 2.0
        global_concurrency = 10

        [cache]
        enabled = false
        """,
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert cfg.http.per_host_rps == 2.0
    assert cfg.http.global_concurrency == 10
    assert cfg.cache.enabled is False
    # untouched section uses defaults
    assert cfg.http.max_response_bytes == 5 * 1024 * 1024


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "does_not_exist.toml")
    assert cfg.http.per_host_rps == 1.0


def test_env_vars_override_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("[http]\nper_host_rps = 2.0\n", encoding="utf-8")
    monkeypatch.setenv("TRADECRAFT_HTTP_PER_HOST_RPS", "0.5")
    cfg = load_config(cfg_file)
    assert cfg.http.per_host_rps == 0.5


def test_coerce_unwraps_optional_int() -> None:
    assert _coerce("42", int | None) == 42


def test_coerce_unwraps_optional_bool() -> None:
    assert _coerce("true", bool | None) is True

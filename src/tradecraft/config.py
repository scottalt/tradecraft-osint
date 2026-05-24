"""Config loader: TOML file + env var overrides."""

from __future__ import annotations

import os
import tomllib
import types
from pathlib import Path
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, Field


class HttpConfig(BaseModel):
    per_host_rps: float = 1.0
    global_concurrency: int = 5
    max_response_bytes: int = 5 * 1024 * 1024
    request_timeout_seconds: float = 20.0
    max_retries: int = 3


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_default_seconds: int = 3600
    directory: str | None = None  # None => ~/.cache/tradecraft/responses


class AppConfig(BaseModel):
    http: HttpConfig = Field(default_factory=HttpConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)


_ENV_PREFIX = "TRADECRAFT_"


def _unwrap_optional(target_type: object) -> object:
    """If the annotation is `X | None` or `Optional[X]`, return X."""
    origin = get_origin(target_type)
    if origin in (Union, types.UnionType):
        args = [a for a in get_args(target_type) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return target_type


def _coerce(value: str, target_type: object) -> Any:
    unwrapped = _unwrap_optional(target_type)
    if unwrapped is bool:
        return value.lower() in {"1", "true", "yes", "on"}
    if unwrapped is int:
        return int(value)
    if unwrapped is float:
        return float(value)
    return value


def _apply_env_overrides(cfg: AppConfig) -> AppConfig:
    """Override config from env vars like TRADECRAFT_HTTP_PER_HOST_RPS=2.0."""
    updates: dict[str, dict[str, Any]] = {"http": {}, "cache": {}}
    for env_name, env_value in os.environ.items():
        if not env_name.startswith(_ENV_PREFIX):
            continue
        key = env_name[len(_ENV_PREFIX) :].lower()
        for section, model_cls in (("http", HttpConfig), ("cache", CacheConfig)):
            section_prefix = f"{section}_"
            if not key.startswith(section_prefix):
                continue
            field_name = key[len(section_prefix) :]
            field = model_cls.model_fields.get(field_name)
            if field is None or field.annotation is None:
                continue
            updates[section][field_name] = _coerce(env_value, field.annotation)

    data = cfg.model_dump()
    for section, section_updates in updates.items():
        if section_updates:
            data[section].update(section_updates)
    return AppConfig.model_validate(data)


def load_config(path: Path | None = None) -> AppConfig:
    """Load config from a TOML file (if it exists), then apply env overrides."""
    data: dict[str, Any] = {}
    if path is not None and path.exists():
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    cfg = AppConfig.model_validate(data) if data else AppConfig()
    return _apply_env_overrides(cfg)


def default_config_path() -> Path:
    """Return the default config file path."""
    return Path.home() / ".config" / "tradecraft" / "config.toml"

"""Filesystem cache with per-entry TTL."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class Cache:
    """Simple filesystem cache. One file per entry, JSON envelope with ttl + payload."""

    def __init__(
        self,
        directory: Path,
        default_ttl: int,
        *,
        enabled: bool = True,
    ) -> None:
        self.directory = directory
        self.default_ttl = default_ttl
        self.enabled = enabled
        if self.enabled:
            self.directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        # 2-level fan-out for filesystem friendliness
        return self.directory / digest[:2] / f"{digest}.json"

    def get(self, key: str) -> bytes | None:
        if not self.enabled:
            return None
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            expires_at = envelope.get("expires_at", 0)
            if time.time() >= expires_at:
                return None
            payload_hex = envelope.get("payload_hex")
            if not isinstance(payload_hex, str):
                return None
            return bytes.fromhex(payload_hex)
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def set(self, key: str, value: bytes, *, ttl: int | None = None) -> None:
        if not self.enabled:
            return
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        ttl_seconds = self.default_ttl if ttl is None else ttl
        envelope = {
            "key": key,
            "expires_at": time.time() + ttl_seconds,
            "payload_hex": value.hex(),
        }
        path.write_text(json.dumps(envelope), encoding="utf-8")

    def clear(self) -> None:
        if not self.directory.exists():
            return
        for child in self.directory.rglob("*.json"):
            try:
                child.unlink()
            except OSError:
                continue

"""POST /api/ai — BYOK proxy. Key arrives, gets used for one call, gets dropped.

Security posture:
- User-supplied `base_url` (openai-compat) is validated to be https and to
  resolve to a public IP. Loopback, private, and link-local ranges are
  rejected to defend against SSRF (metadata endpoints, internal services).
- httpx follow_redirects=False so a 3xx from the upstream can't pivot the
  request to an attacker-controlled internal target.
- Errors returned to the client are generic. Upstream exception strings
  (which can carry URLs / response bodies / token echoes from misbehaving
  providers) stay server-side.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

import httpx


def _is_safe_public_url(raw_url: str) -> bool:
    """Return True only if raw_url is https and resolves to a public IP."""
    try:
        parsed = urlparse(raw_url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    host = parsed.hostname
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False
    return True


async def _call_anthropic(key: str, system: str, prompt: str, model: str) -> str:
    resp = await _post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        body={
            "model": model,
            "max_tokens": 1200,
            "system": system,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}
                    ],
                }
            ],
        },
    )
    blocks = resp.get("content", [])
    for b in blocks:
        if isinstance(b, dict) and isinstance(b.get("text"), str):
            return b["text"]
    return ""


async def _call_openai(key: str, system: str, prompt: str, model: str, base_url: str | None = None) -> str:
    url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    resp = await _post(
        url,
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
        body={
            "model": model,
            "max_tokens": 1200,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        },
    )
    choices = resp.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "") or ""


async def _post(url: str, headers: dict, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=False) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()


async def _generate(payload: dict) -> dict:
    provider = payload.get("provider")
    key = payload.get("key", "")
    system = payload.get("system", "")
    prompt = payload.get("prompt", "")
    model = payload.get("model", "")

    if provider == "anthropic":
        text = await _call_anthropic(key, system, prompt, model or "claude-sonnet-4-6")
    elif provider == "openai":
        text = await _call_openai(key, system, prompt, model or "gpt-4o")
    elif provider == "openai-compat":
        base_url = payload.get("base_url")
        if not base_url:
            return {"error": "base_url required for openai-compat"}
        if not _is_safe_public_url(base_url):
            return {"error": "base_url must be https and resolve to a public IP"}
        text = await _call_openai(key, system, prompt, model, base_url=base_url)
    else:
        return {"error": f"unsupported provider: {provider!r}"}

    return {"text": text}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        try:
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(body.decode("utf-8"))
            # DELIBERATELY: do not log payload (it contains the key).
            result = asyncio.run(_generate(payload))
            status = 400 if "error" in result else 200
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception:  # noqa: BLE001
            # Do NOT echo str(exc) — httpx errors can carry URLs, headers, or
            # response bodies from upstream providers. Return a generic
            # message; server-side observability (if any) inspects the raw
            # exception via the platform's exception hook.
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "upstream request failed"}).encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        # IMPORTANT: do not log the payload — it contains the user's key.
        return

"""POST /api/compile — run hosted-safe collectors and return Findings JSON.

Security posture:
- User-supplied `root_url` and `job_url` are validated to use http(s) and
  to resolve to public IPs before the orchestrator runs. Loopback, private,
  and link-local ranges are rejected to defend against SSRF (instance
  metadata, localhost services, internal RFC1918 targets).
- Errors returned to the client are generic. Upstream exception strings
  (which can carry URLs, headers, or response bodies from third-party
  services) stay server-side.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

# Add the vendored tradecraft package to sys.path. The build step
# (scripts/vendor-tradecraft.sh) copies it into ./_vendor/tradecraft/.
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "_vendor"))

# Now import tradecraft (must come AFTER sys.path mutation).
from tradecraft.analyzers.heuristics import generate_questions  # noqa: E402
from tradecraft.cache import Cache  # noqa: E402
from tradecraft.collectors.company import CompanyCollector  # noqa: E402
from tradecraft.collectors.footprint import FootprintCollector  # noqa: E402
from tradecraft.collectors.github import GitHubCollector  # noqa: E402
from tradecraft.collectors.job import JobCollector  # noqa: E402
from tradecraft.collectors.ma import MaCollector  # noqa: E402
from tradecraft.collectors.news import NewsCollector  # noqa: E402
from tradecraft.config import HttpConfig  # noqa: E402
from tradecraft.http import HttpClient  # noqa: E402
from tradecraft.models import Role, Target  # noqa: E402
from tradecraft.orchestrator import Orchestrator  # noqa: E402
from tradecraft.renderers.json import render_json  # noqa: E402


HOSTED_COLLECTORS = [
    FootprintCollector(),
    CompanyCollector(),
    JobCollector(),
    GitHubCollector(),
    NewsCollector(),
    MaCollector(),
]


def _is_safe_public_url(raw_url: str) -> bool:
    """Return True only if raw_url is http/https and resolves to a public IP."""
    try:
        parsed = urlparse(raw_url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
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


async def _run(payload: dict) -> str:
    root_url = payload["root_url"]
    job_url = payload.get("job_url") or None
    company_in = payload.get("company") or None

    company_name = company_in
    if not company_name:
        host = urlparse(root_url).hostname or root_url
        parts = host.split(".")
        company_name = parts[-2].capitalize() if len(parts) >= 2 else host

    target = Target(
        company_name=company_name,
        root_url=root_url,
        job_url=job_url,
        role=Role.CYBERSECURITY,
    )

    # Use an in-memory ephemeral cache per request — no persistence in hosted mode.
    cache = Cache(directory=Path("/tmp/tradecraft-cache"), default_ttl=60, enabled=False)
    target_host = urlparse(root_url).hostname

    async with HttpClient(HttpConfig(), cache, target_host=target_host) as http:
        orch = Orchestrator(HOSTED_COLLECTORS, http=http, cache=cache)
        findings = await orch.run(target, hosted=True)

    questions = generate_questions(findings)
    return render_json(findings, questions)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 — Vercel Python signature
        try:
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(body.decode("utf-8"))
            root_url = payload.get("root_url")
            if not root_url:
                self._respond(400, {"error": "root_url required"})
                return
            if not _is_safe_public_url(root_url):
                self._respond(400, {"error": "root_url must be http(s) and resolve to a public IP"})
                return
            job_url = payload.get("job_url")
            if job_url and not _is_safe_public_url(job_url):
                self._respond(400, {"error": "job_url must be http(s) and resolve to a public IP"})
                return
            result = asyncio.run(_run(payload))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.encode("utf-8"))
        except Exception:  # noqa: BLE001
            # Do NOT echo str(exc) — orchestrator exceptions can carry URLs
            # and response bodies from third-party services we hit on the
            # user's behalf. Generic message only; observability is the
            # platform's exception hook.
            self._respond(500, {"error": "compile failed"})

    def _respond(self, status: int, body: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002 — Vercel quiet
        return

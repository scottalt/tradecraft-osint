"""POST /api/compile — run hosted-safe collectors and return Findings JSON."""

from __future__ import annotations

import asyncio
import json
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
]


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
            if not payload.get("root_url"):
                self._respond(400, {"error": "root_url required"})
                return
            result = asyncio.run(_run(payload))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._respond(500, {"error": str(exc)[:200]})

    def _respond(self, status: int, body: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002 — Vercel quiet
        return

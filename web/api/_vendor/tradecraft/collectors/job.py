"""Job listing collector: parse the user-supplied JD URL."""

from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urlparse

from selectolax.parser import HTMLParser

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_STACK_KEYWORDS = (
    "Python",
    "Go",
    "Rust",
    "Java",
    "Kotlin",
    "Scala",
    "Ruby",
    "Node",
    "TypeScript",
    "JavaScript",
    "C#",
    "C++",
    "Swift",
    "Kubernetes",
    "Docker",
    "Terraform",
    "Ansible",
    "AWS",
    "GCP",
    "Azure",
    "Vercel",
    "Cloudflare",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Kafka",
    "React",
    "Next.js",
    "Django",
    "Flask",
    "FastAPI",
    "Spring",
)


class JobCollector:
    name: ClassVar[str] = "job"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.SWE,
        Role.DEVOPS,
        Role.DATA,
        Role.ENG_LEADERSHIP,
        Role.GENERIC,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        if ctx.target.job_url is None:
            return CollectorResult(name=self.name, data={}, signals=[], errors=[], duration_ms=0)

        errors: list[CollectorError] = []
        signals: list[Signal] = []

        try:
            resp = await ctx.http.get(str(ctx.target.job_url))
        except Exception as exc:
            return CollectorResult(
                name=self.name,
                data={},
                signals=[],
                errors=[
                    CollectorError(
                        stage="fetch",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                ],
                duration_ms=0,
            )

        if resp.status_code != 200:
            errors.append(
                CollectorError(
                    stage="fetch",
                    message=f"status {resp.status_code}",
                    exception_type="HTTPStatusError",
                )
            )
            return CollectorResult(
                name=self.name, data={}, signals=signals, errors=errors, duration_ms=0
            )

        host = (urlparse(str(ctx.target.job_url)).hostname or "").lower()
        title, body = self._extract(host, resp.text)
        stack = self._extract_stack(body)

        return CollectorResult(
            name=self.name,
            data={
                "url": str(ctx.target.job_url),
                "host": host,
                "title": title,
                "body_excerpt": body[:2000],
                "stack": stack,
            },
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

    @staticmethod
    def _extract(host: str, html: str) -> tuple[str, str]:
        tree = HTMLParser(html)
        title = ""
        body = ""
        if "greenhouse.io" in host:
            t = tree.css_first("h1.app-title")
            c = tree.css_first("#content")
            title = t.text(strip=True) if t else ""
            body = c.text(separator=" ", strip=True) if c else ""
        elif "lever.co" in host:
            t = tree.css_first("h2.posting-headline")
            c = tree.css_first(".section-wrapper")
            title = t.text(strip=True) if t else ""
            body = c.text(separator=" ", strip=True) if c else ""
        else:
            t = tree.css_first("h1") or tree.css_first("title")
            title = t.text(strip=True) if t else ""
            if tree.body:
                body = tree.body.text(separator=" ", strip=True)
        return title, body

    @staticmethod
    def _extract_stack(text: str) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        for kw in _STACK_KEYWORDS:
            pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
            if pattern.search(text) and kw not in seen:
                found.append(kw)
                seen.add(kw)
        return found

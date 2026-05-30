"""GitHub org + public-repos collector."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_GH_ORG_URL = "https://api.github.com/orgs/{slug}"
_GH_REPOS_URL = "https://api.github.com/orgs/{slug}/repos?per_page=100&sort=updated"
_ACTIVE_PUSH_DAYS = 90
_OSS_FORWARD_REPO_THRESHOLD = 10


class GitHubCollector:
    name: ClassVar[str] = "github"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY, Role.SWE, Role.DEVOPS}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []

        candidates = [
            ctx.target.company_slug,
            ctx.target.company_name.lower().replace(" ", ""),
        ]
        # de-duplicate while preserving order
        seen: set[str] = set()
        unique_candidates: list[str] = []
        for c in candidates:
            if c and c not in seen:
                unique_candidates.append(c)
                seen.add(c)

        org: dict[str, Any] | None = None
        repos: list[dict[str, Any]] = []
        for slug in unique_candidates:
            org_url = _GH_ORG_URL.format(slug=slug)
            try:
                resp = await ctx.http.get(org_url)
            except Exception as exc:
                errors.append(
                    CollectorError(
                        stage="org",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )
                continue
            if resp.status_code == 200:
                org = resp.json()
                try:
                    repos_resp = await ctx.http.get(_GH_REPOS_URL.format(slug=slug))
                    if repos_resp.status_code == 200:
                        repos = repos_resp.json()
                except Exception as exc:
                    errors.append(
                        CollectorError(
                            stage="repos",
                            message=str(exc) or exc.__class__.__name__,
                            exception_type=exc.__class__.__name__,
                        )
                    )
                break

        if org is None:
            signals.append(Signal.NO_PUBLIC_GITHUB)
        else:
            cutoff = datetime.now(tz=UTC) - timedelta(days=_ACTIVE_PUSH_DAYS)
            non_archived_owned = [
                r for r in repos if not r.get("archived", False) and not r.get("fork", False)
            ]
            recently_active = any(
                self._parse_iso(r.get("pushed_at")) >= cutoff for r in non_archived_owned
            )
            if len(non_archived_owned) >= _OSS_FORWARD_REPO_THRESHOLD and recently_active:
                signals.append(Signal.OSS_FORWARD_CULTURE)

        languages = Counter(r.get("language") for r in repos if r.get("language")).most_common(10)

        return CollectorResult(
            name=self.name,
            data={
                "org": org,
                "repo_count": len(repos),
                "languages": dict(languages),
                "top_repos": sorted(
                    [
                        {
                            "name": r.get("name"),
                            "language": r.get("language"),
                            "stars": r.get("stargazers_count", 0),
                            "pushed_at": r.get("pushed_at"),
                            "fork": r.get("fork", False),
                            "archived": r.get("archived", False),
                        }
                        for r in repos
                    ],
                    key=lambda x: x["stars"],
                    reverse=True,
                )[:10],
            },
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

    @staticmethod
    def _parse_iso(value: Any) -> datetime:
        if not isinstance(value, str):
            return datetime.min.replace(tzinfo=UTC)
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=UTC)

"""Core data models for tradecraft."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class Role(StrEnum):
    CYBERSECURITY = "cybersecurity"
    SWE = "swe"
    DEVOPS = "devops"
    DATA = "data"
    ENG_LEADERSHIP = "eng-leadership"
    GENERIC = "generic"


class Signal(StrEnum):
    # footprint
    MISSING_CSP = "missing_csp"
    MISSING_HSTS = "missing_hsts"
    OPEN_STAGING_SUBDOMAIN = "open_staging_subdomain"
    CERT_EXPIRING_SOON = "cert_expiring_soon"
    EXPOSED_ADMIN_PATH = "exposed_admin_path"
    # company
    RECENT_PRESS_RELEASE = "recent_press_release"
    FOUNDER_TECHNICAL = "founder_technical"
    PRODUCT_LIST_EMPTY = "product_list_empty"
    # job
    LANGUAGES_MISMATCH_JOB = "languages_mismatch_job"
    STACK_ALIGNMENT_STRONG = "stack_alignment_strong"
    # news
    RECENT_LAYOFFS = "recent_layoffs"
    RECENT_FUNDING = "recent_funding"
    RECENT_LEADERSHIP_CHANGE = "recent_leadership_change"
    RECENT_SECURITY_INCIDENT = "recent_security_incident"
    # breaches
    BREACH_HISTORY = "breach_history"
    BREACH_RECENT = "breach_recent"
    # github
    OSS_FORWARD_CULTURE = "oss_forward_culture"
    NO_PUBLIC_GITHUB = "no_public_github"
    # people
    STRONG_ENG_BRAND = "strong_eng_brand"
    QUIET_ENG_BRAND = "quiet_eng_brand"
    # business
    PUBLIC_COMPANY = "public_company"
    RECENT_10K = "recent_10k"
    WIKIPEDIA_INFOBOX_PRESENT = "wikipedia_infobox_present"
    GLASSDOOR_RATING_LOW = "glassdoor_rating_low"
    # m&a
    M_A_RECENT = "m_a_recent"
    M_A_FREQUENT_ACQUIRER = "m_a_frequent_acquirer"
    SUBSIDIARY_OF = "subsidiary_of"


_SLUG_RE = re.compile(r"[^a-z0-9]+")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _slugify(value: str) -> str:
    return _SLUG_RE.sub("-", value.lower()).strip("-")


class Evidence(BaseModel):
    signal: Signal
    summary: str  # the real headline / press title / JD stack phrase
    url: str | None = None
    date: str | None = None  # ISO date string when known, e.g. "2026-03-11"
    source: str  # e.g. "news.google", "hn", "company", "job", "wikipedia"

    @field_validator("date")
    @classmethod
    def _validate_iso_date(cls, v: str | None) -> str | None:
        if v is not None and not _ISO_DATE_RE.fullmatch(v):
            raise ValueError(f"date must be YYYY-MM-DD, got {v!r}")
        return v


class Target(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_name: str
    root_url: HttpUrl
    job_url: HttpUrl | None = None
    role: Role = Role.CYBERSECURITY

    @property
    def company_slug(self) -> str:
        return _slugify(self.company_name)


class Question(BaseModel):
    text: str
    confidence: Literal["high", "med", "low"]
    role_tags: set[Role]
    evidence_signal: Signal | None = None
    source_collector: str
    is_starred: bool = False
    evidence: Evidence | None = None


class CollectorError(BaseModel):
    stage: str
    message: str
    exception_type: str | None = None


class CollectorResult(BaseModel):
    name: str
    data: dict[str, object] = Field(default_factory=dict)
    signals: list[Signal] = Field(default_factory=list)
    errors: list[CollectorError] = Field(default_factory=list)
    duration_ms: int
    evidence: list[Evidence] = Field(default_factory=list)


class Findings(BaseModel):
    target: Target
    results: list[CollectorResult] = Field(default_factory=list)
    schema_version: int = 1

    @property
    def all_signals(self) -> set[Signal]:
        return {s for r in self.results for s in r.signals}

    def collector(self, name: str) -> CollectorResult | None:
        return next((r for r in self.results if r.name == name), None)

    def evidence_for(self, signal: Signal) -> Evidence | None:
        matches = [e for r in self.results for e in r.evidence if e.signal == signal]
        if not matches:
            return None
        dated = [e for e in matches if e.date is not None]
        if dated:
            # most-recent-wins; url is the tie-break for determinism
            return max(dated, key=lambda e: (e.date, e.url or ""))  # type: ignore[arg-type]
        return matches[0]

# tradecraft v0.2.0 — Collectors Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the v1-design collector roster — ship the remaining 7 OSINT collectors (`breaches`, `github`, `news`, `company`, `job`, `people`, `business`, `ma` — wait, that's 8; the walking skeleton already shipped `footprint`, so 7 new). Expand the heuristic template library to cover all four cybersec sub-disciplines (offensive, defensive, AppSec, GRC) for the new signals. Update the markdown renderer to surface each collector's findings. Validate end-to-end against a real target. Tag v0.2.0.

**Architecture:** Each new collector implements the existing `Collector` protocol (`src/tradecraft/collectors/base.py`) and is registered in `cli.py::_default_collectors()`. Collectors are fully independent — none depend on another's output at runtime. The heuristic analyzer (`analyzers/heuristics.py`) is unchanged; only `analyzers/templates.py` grows. The renderer gains per-collector sections, each guarded so a missing collector result produces an empty stub rather than a crash. AI integration is **out of scope** for this plan and ships in v0.3.0.

**Tech Stack:** Same as v0.1.0a1 — Python 3.11+, `httpx[http2]`, `selectolax` (already pinned for HTML parsing), `feedparser` (already pinned for RSS), `pydantic` v2, `pytest`/`respx`/`pytest-asyncio`. No new runtime deps. No new dev deps.

**Spec reference:** `docs/superpowers/specs/2026-05-23-tradecraft-design.md` (sections §6, §7.1, §8.1)

**Out of scope (deferred):**
- BYOK AI analyzer and the 4 provider adapters (Anthropic/OpenAI/Ollama/OpenAI-compat) — v0.3.0
- Hosted web preview — v1.1
- New roles or sub-role refinement of `cybersecurity` — post-v1.0

---

## Cybersec-first delivery order

Order is chosen so each collector landing makes the cybersec dossier materially better:

1. **`breaches`** — highest signal-per-LOC for cybersec. `BREACH_HISTORY` / `BREACH_RECENT` are direct talking-points.
2. **`github`** — cybersec roles inspect public repos for posture, supply chain, security tooling. `OSS_FORWARD_CULTURE`, `NO_PUBLIC_GITHUB`.
3. **`news`** — `RECENT_SECURITY_INCIDENT`, `RECENT_LAYOFFS` (security teams often cut first), `RECENT_FUNDING` (budget signals).
4. **`company`** — about/team/careers pages reveal CISO presence, security org structure.
5. **`job`** — JD parsing surfaces required certifications, scope (red/blue/AppSec), team description.
6. **`people`** — public talks at DEF CON / BSides / RSA / OWASP / Black Hat reveal house technical depth.
7. **`business`** — SEC filings disclose breach/incident impact, compliance posture, M&A.
8. **`ma`** — acquisition history; security integration is a perennial interview topic.

Each collector lands as its own commit, behind the existing `Collector` protocol. The renderer and template library grow incrementally.

---

## File map (locked in here so later tasks reference exact paths)

Files to **create** in `src/tradecraft/`:

```
src/tradecraft/collectors/
├── breaches.py            (Task 2)
├── github.py              (Task 3)
├── news.py                (Task 4)
├── company.py             (Task 5)
├── job.py                 (Task 6)
├── people.py              (Task 7)
├── business.py            (Task 8)
└── ma.py                  (Task 9)
```

Files to **modify** in `src/tradecraft/`:

```
src/tradecraft/
├── __init__.py            (Task 12 — bump __version__ to 0.2.0)
├── cli.py                 (Task 10 — register all 8 collectors)
├── analyzers/templates.py (Task 1 — add ~30 new templates)
└── renderers/markdown.py  (Task 11 — add per-collector sections)
```

Files to **create** in `tests/`:

```
tests/unit/collectors/
├── test_breaches.py       (Task 2)
├── test_github.py         (Task 3)
├── test_news.py           (Task 4)
├── test_company.py        (Task 5)
├── test_job.py            (Task 6)
├── test_people.py         (Task 7)
├── test_business.py       (Task 8)
└── test_ma.py             (Task 9)

tests/fixtures/
├── breaches/hibp_acme.json
├── github/org_acme.json
├── github/repos_acme.json
├── news/google_news_acme.xml
├── news/hn_algolia_acme.json
├── company/acme_about.html
├── company/acme_team.html
├── job/greenhouse_acme.html
├── job/lever_acme.html
├── people/acme_blog.html
├── business/sec_acme.json
├── business/wikipedia_acme.html
├── business/glassdoor_acme.html
└── ma/wikipedia_acme_infobox.html

tests/integration/
└── test_v0_2_end_to_end.py (Task 13)
```

Files to **modify** in `docs/` and root:

```
README.md                  (Task 12 — bump status, sample shows all collectors)
CHANGELOG.md               (Task 12 — 0.2.0 entry)
```

---

## Conventions used in every task

- **Test framework:** `pytest`. Async tests via `pytest-asyncio` with `asyncio_mode = "auto"`.
- **HTTP mocking:** `respx`. No live network in CI.
- **DNS mocking:** `unittest.mock.AsyncMock` injected via `_dns_lookup` constructor arg (pattern from `footprint.py`).
- **Run a single test:** `uv run pytest tests/<path>::test_name -v`
- **Run all tests:** `uv run pytest -v`
- **Lint:** `uv run ruff check src tests` and `uv run ruff format --check src tests`
- **Typecheck:** `uv run mypy src`
- **TDD cycle:** write failing test → confirm it fails → minimal impl → confirm it passes → refactor if needed → commit.
- **Commits:** Conventional Commits. One commit per task.
- **Co-author trailer:** include `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` on every commit.

## Reference collector pattern (READ BEFORE EACH COLLECTOR TASK)

The eight collectors all follow the same shape established by `footprint.py`:

```python
"""<one-line module purpose>."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any, ClassVar

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)


class <Name>Collector:
    name: ClassVar[str] = "<name>"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = <true/false>  # per spec §6
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY, ...}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        data: dict[str, Any] = {}

        # Use ctx.http.get(url) for every outbound HTTP call.
        # Use asyncio.gather(*(self._safe(...) for ...)) when fetching
        # multiple independent URLs.

        return CollectorResult(
            name=self.name,
            data=data,
            signals=signals,
            errors=errors,
            duration_ms=0,  # overridden by timed_run() in orchestrator
        )

    @staticmethod
    async def _safe(
        awaitable: Awaitable[Any],
        errors: list[CollectorError],
        stage: str,
    ) -> Any | None:
        try:
            return await awaitable
        except Exception as exc:  # noqa: BLE001
            errors.append(
                CollectorError(
                    stage=stage,
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )
            return None
```

**Constraints carried by every collector:**
- Use `ctx.http.get(url)` exclusively for HTTP — never instantiate httpx directly.
- Emit `Signal` enum members defined in `models.py`. If a new signal is needed, add it there first (Task 1's template expansion includes this).
- Never raise from `run()`; capture failures into `errors`.
- `safe_for_hosted = True` only for collectors that hit explicitly-public APIs (the company's own site, GitHub public API, crt.sh).
- `role_relevance` informs orchestrator gating; all 8 collectors include `Role.CYBERSECURITY`.

---

## Task 1: Expand the QuestionTemplate library

**Files:**
- Modify: `src/tradecraft/analyzers/templates.py`
- Modify: `tests/unit/analyzers/test_templates.py`

**Why first:** templates define which signals are interview-worthy. Authoring them up front means each collector lands with its questions already firing on day one. Authoring them per-collector creates churn — collectors get committed without questions, then a second pass adds them, doubling the touch on `templates.py`.

**What to add:** ~30 new `QuestionTemplate` entries spanning the four cybersec sub-disciplines (offensive / defensive / AppSec / GRC) for the signals every new collector will emit. The 15 existing templates remain unchanged.

The full template additions are listed in the inline implementation below. They reference signals already present in `Signal` (no new enum values needed — the 27 signals from v0.1.0a0 cover the full collector roster).

- [ ] **Step 1: Write failing tests for the new size and key behaviors**

In `tests/unit/analyzers/test_templates.py`, add these tests below the existing ones:

```python
def test_library_has_expanded_for_v0_2() -> None:
    """v0.2.0 ships ~45 templates (15 starter + ~30 new)."""
    assert len(TEMPLATES) >= 40


def test_every_cybersec_signal_has_at_least_one_template() -> None:
    """Every Signal value should be covered by at least one cybersecurity-tagged
    template. Non-cyber roles are intentionally under-covered for now."""
    cyber_signals_covered: set[Signal] = set()
    for tmpl in TEMPLATES:
        if Role.CYBERSECURITY in tmpl.roles:
            cyber_signals_covered.update(tmpl.signals)
    missing = set(Signal) - cyber_signals_covered
    assert not missing, f"signals with no cybersec template: {sorted(s.value for s in missing)}"


def test_multiple_sub_disciplines_represented() -> None:
    """Templates should span offensive (attack-surface), defensive (incident
    response), AppSec (CSP/HSTS posture), and GRC (compliance) framings.
    Check by keyword presence in the template texts."""
    text_corpus = " ".join(t.text.lower() for t in TEMPLATES if Role.CYBERSECURITY in t.roles)
    assert "attack surface" in text_corpus or "exposure" in text_corpus  # offensive
    assert "detect" in text_corpus or "respond" in text_corpus or "soc" in text_corpus  # defensive
    assert "csp" in text_corpus or "content-security-policy" in text_corpus or "appsec" in text_corpus  # appsec
    assert "compliance" in text_corpus or "audit" in text_corpus or "soc 2" in text_corpus  # grc
```

- [ ] **Step 2: Run tests to verify the new ones fail**

```
uv run pytest tests/unit/analyzers/test_templates.py -v
```

Expected: 3 failures (size, coverage, sub-discipline). The 5 existing tests should still pass.

- [ ] **Step 3: Add the new templates**

Append the following templates to the `TEMPLATES` tuple in `src/tradecraft/analyzers/templates.py`, immediately before the closing `)`:

```python
    # ---- breaches (offensive + defensive + GRC) ----
    QuestionTemplate(
        id="breaches.history.defensive",
        signals=(Signal.BREACH_HISTORY,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "HIBP lists past breach events involving your domain. "
            "What changed in your detection and response coverage after those incidents?"
        ),
        confidence="high",
        source="breaches",
    ),
    QuestionTemplate(
        id="breaches.history.grc",
        signals=(Signal.BREACH_HISTORY,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "How did past breach disclosures shape your compliance program — "
            "additional audits, framework changes (SOC 2, ISO 27001), or board-level reporting?"
        ),
        confidence="med",
        source="breaches",
    ),
    QuestionTemplate(
        id="breaches.recent.offensive",
        signals=(Signal.BREACH_RECENT,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "A breach in the last 24 months is recent. "
            "How has external attack-surface management changed since — purple team cadence, "
            "pre-prod exposure controls, or third-party assessments?"
        ),
        confidence="high",
        source="breaches",
    ),

    # ---- github (AppSec + offensive) ----
    QuestionTemplate(
        id="github.oss_forward",
        signals=(Signal.OSS_FORWARD_CULTURE,),
        roles=frozenset({Role.CYBERSECURITY, Role.SWE, Role.DEVOPS}),
        text=(
            "You have a substantial public GitHub footprint. "
            "How does the security team work with engineering on supply-chain controls — "
            "dependency review, SBOM generation, signed commits?"
        ),
        confidence="med",
        source="github",
    ),
    QuestionTemplate(
        id="github.no_public",
        signals=(Signal.NO_PUBLIC_GITHUB,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "No public GitHub org under the brand name. "
            "Is that a deliberate posture — all internal-only — or are repos under personal accounts?"
        ),
        confidence="low",
        source="github",
    ),

    # ---- news (defensive + offensive + GRC) ----
    QuestionTemplate(
        id="news.security_incident.defensive",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "I read about the security incident earlier this year. "
            "What changed in your detection coverage, IR runbooks, or SOC staffing model since?"
        ),
        confidence="high",
        source="news",
    ),
    QuestionTemplate(
        id="news.security_incident.offensive",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "Post-incident, did you bring in external red-team or purple-team engagements "
            "to validate the fix?"
        ),
        confidence="med",
        source="news",
    ),
    QuestionTemplate(
        id="news.security_incident.grc",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "How did the incident shape your compliance reporting and board-level audit cadence?"
        ),
        confidence="med",
        source="news",
    ),
    QuestionTemplate(
        id="news.layoffs.cyber_specific",
        signals=(Signal.RECENT_LAYOFFS,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "Security teams often see disproportionate cuts during layoffs. "
            "Did the security org stay whole, and how has scope been re-prioritized?"
        ),
        confidence="med",
        source="news",
    ),
    QuestionTemplate(
        id="news.funding.cyber_specific",
        signals=(Signal.RECENT_FUNDING,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "With the recent funding, where is the security org investing — "
            "in-house tooling, headcount, or third-party platforms?"
        ),
        confidence="med",
        source="news",
    ),

    # ---- company (AppSec + GRC) ----
    QuestionTemplate(
        id="company.recent_press.cyber_specific",
        signals=(Signal.RECENT_PRESS_RELEASE,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "I saw the recent announcement. What does that mean for the security team's "
            "near-term roadmap — new product surface, integrations, or compliance work?"
        ),
        confidence="med",
        source="company",
    ),
    QuestionTemplate(
        id="company.founder_technical.cyber_specific",
        signals=(Signal.FOUNDER_TECHNICAL,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "Your founders have technical backgrounds. "
            "How involved are they in security trade-offs — defining risk appetite, "
            "approving exception requests?"
        ),
        confidence="low",
        source="company",
    ),
    QuestionTemplate(
        id="company.product_empty",
        signals=(Signal.PRODUCT_LIST_EMPTY,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "Your public site is sparse on product details. "
            "Is that a deliberate stealth posture, or is messaging evolving?"
        ),
        confidence="low",
        source="company",
    ),

    # ---- job (AppSec / offensive / defensive / GRC across stack mismatch) ----
    QuestionTemplate(
        id="job.stack_mismatch.cyber_specific",
        signals=(Signal.LANGUAGES_MISMATCH_JOB,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "The JD calls for skills in a stack that doesn't dominate your public repos. "
            "Is this for a new initiative — a greenfield service or a security tooling rewrite?"
        ),
        confidence="high",
        source="job",
    ),
    QuestionTemplate(
        id="job.stack_alignment.cyber_specific",
        signals=(Signal.STACK_ALIGNMENT_STRONG,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "Your stack aligns closely with the JD. "
            "Where does the security team feel the existing stack falls short at scale — "
            "policy enforcement, observability, or supply-chain coverage?"
        ),
        confidence="med",
        source="job",
    ),

    # ---- people (defensive + AppSec) ----
    QuestionTemplate(
        id="people.strong_brand.defensive",
        signals=(Signal.STRONG_ENG_BRAND,),
        roles=frozenset({Role.CYBERSECURITY, Role.SWE}),
        text=(
            "Your engineers publish a lot — talks, blog posts, OSS. "
            "Does the security team contribute to that public engineering brand, "
            "or stay quieter for risk reasons?"
        ),
        confidence="med",
        source="people",
    ),
    QuestionTemplate(
        id="people.quiet_brand",
        signals=(Signal.QUIET_ENG_BRAND,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "I couldn't find much public engineering content from the team. "
            "Is that a posture choice, or are folks focused inward?"
        ),
        confidence="low",
        source="people",
    ),

    # ---- business (GRC + defensive) ----
    QuestionTemplate(
        id="business.public_company.grc",
        signals=(Signal.PUBLIC_COMPANY,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "As a public company, what's the security team's relationship with audit / "
            "the Audit Committee — quarterly reporting, ad-hoc briefings, both?"
        ),
        confidence="med",
        source="business",
    ),
    QuestionTemplate(
        id="business.recent_10k",
        signals=(Signal.RECENT_10K,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "The most recent 10-K mentions cyber-risk disclosure. "
            "Has the SEC's incident-reporting rule changed how the team scopes "
            "what constitutes a material incident?"
        ),
        confidence="med",
        source="business",
    ),
    QuestionTemplate(
        id="business.wikipedia",
        signals=(Signal.WIKIPEDIA_INFOBOX_PRESENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.GENERIC}),
        text=(
            "Your Wikipedia page covers history and product lines. "
            "How does the security org map onto the historical business — "
            "centralized, federated by business unit, or matrixed?"
        ),
        confidence="low",
        source="business",
    ),
    QuestionTemplate(
        id="business.glassdoor_low",
        signals=(Signal.GLASSDOOR_RATING_LOW,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP, Role.GENERIC}),
        text=(
            "Public-review sentiment is mixed. "
            "What is the team actively changing — process, on-call load, comp, growth path?"
        ),
        confidence="med",
        source="business",
    ),

    # ---- ma (offensive + AppSec + GRC) ----
    QuestionTemplate(
        id="ma.recent.offensive",
        signals=(Signal.M_A_RECENT,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "I saw the recent acquisition. "
            "What does the external attack-surface picture look like once you fold in "
            "their domains, SaaS contracts, and identity providers?"
        ),
        confidence="high",
        source="ma",
    ),
    QuestionTemplate(
        id="ma.recent.appsec",
        signals=(Signal.M_A_RECENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.SWE}),
        text=(
            "Post-acquisition, how do you handle a new codebase with different "
            "SDLC controls — gradual policy adoption, immediate gating, or buy-now-fix-later?"
        ),
        confidence="high",
        source="ma",
    ),
    QuestionTemplate(
        id="ma.recent.grc",
        signals=(Signal.M_A_RECENT,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "What's the security-integration timeline post-deal — "
            "identity merge, framework alignment (SOC 2, ISO), incident-response unification?"
        ),
        confidence="high",
        source="ma",
    ),
    QuestionTemplate(
        id="ma.frequent_acquirer",
        signals=(Signal.M_A_FREQUENT_ACQUIRER,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "You acquire frequently. "
            "Is there a standing post-acquisition security playbook, or is each deal bespoke?"
        ),
        confidence="med",
        source="ma",
    ),
    QuestionTemplate(
        id="ma.subsidiary",
        signals=(Signal.SUBSIDIARY_OF,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "Your parent company owns the broader security program. "
            "Where does this team's autonomy end — tooling choices, hiring, incident escalation?"
        ),
        confidence="low",
        source="ma",
    ),

    # ---- additional offensive templates against existing footprint signals ----
    QuestionTemplate(
        id="footprint.missing_csp.offensive",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "No CSP on the apex. "
            "In a recent external assessment, would that have shown up as a finding, "
            "and what's the team's appetite for CSP rollout pain?"
        ),
        confidence="med",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.open_staging.grc",
        signals=(Signal.OPEN_STAGING_SUBDOMAIN,),
        roles=frozenset({Role.CYBERSECURITY, Role.ENG_LEADERSHIP}),
        text=(
            "Pre-prod hostnames in public CT logs. "
            "Does your attack-surface management program — internal or vendor-driven — "
            "audit the CT feed continuously?"
        ),
        confidence="med",
        source="footprint",
    ),
```

- [ ] **Step 4: Verify all tests pass**

```
uv run pytest tests/unit/analyzers/ -v
uv run ruff check src/tradecraft/analyzers tests/unit/analyzers
uv run mypy src/tradecraft/analyzers
```

Expected: all green. The size assertion (`>= 40`) should pass; the cybersec-signal-coverage assertion should pass; the sub-discipline keyword sweep should pass (the new texts include "attack surface", "detect/respond/SOC", "CSP", "compliance/SOC 2/audit").

- [ ] **Step 5: Commit**

```
git add src/tradecraft/analyzers/templates.py tests/unit/analyzers/test_templates.py
git commit -m "$(cat <<'EOF'
feat(templates): expand library to ~45 cybersec-focused templates

Adds ~30 templates spanning offensive (attack surface, exposure),
defensive (SOC, IR, detection coverage), AppSec (CSP rollout,
supply chain), and GRC (compliance, audit, SEC disclosure)
sub-disciplines. Every Signal value now has at least one
cybersecurity-tagged template, so every collector signal will
produce a question once that collector lands.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: breaches collector

**Files:**
- Create: `src/tradecraft/collectors/breaches.py`
- Create: `tests/unit/collectors/test_breaches.py`
- Create: `tests/fixtures/breaches/hibp_acme.json`

**Source:** Have I Been Pwned's free unauthenticated domain breach endpoint at `https://haveibeenpwned.com/api/v3/breaches?domain=<domain>`. Returns a JSON array of breach objects, each with `Name`, `BreachDate` (YYYY-MM-DD), `PwnCount`, `DataClasses` (list), `Domain`, `IsVerified`.

**Signals emitted:**
- `Signal.BREACH_HISTORY` if at least one breach is returned for the domain.
- `Signal.BREACH_RECENT` if at least one breach's `BreachDate` is within 24 months of today.

**Per spec §6.5:** `safe_for_hosted = False` (HIBP rate-limits aggressively and some endpoints require keys; safer to keep CLI-only).

**Constraint:** robots.txt is target-scoped (per v0.1.0a1), so HIBP is exempt from robots regardless.

- [ ] **Step 1: Create the fixture**

`tests/fixtures/breaches/hibp_acme.json`:

```json
[
  {
    "Name": "AcmeOldLeak",
    "Title": "Acme 2019 leak",
    "Domain": "acme.com",
    "BreachDate": "2019-03-15",
    "AddedDate": "2019-04-01T00:00:00Z",
    "PwnCount": 1500000,
    "Description": "Test breach for fixture use.",
    "DataClasses": ["Email addresses", "Passwords"],
    "IsVerified": true,
    "IsFabricated": false,
    "IsSensitive": false,
    "IsRetired": false,
    "IsSpamList": false,
    "IsMalware": false
  },
  {
    "Name": "AcmeRecent",
    "Title": "Acme 2025 incident",
    "Domain": "acme.com",
    "BreachDate": "2025-08-20",
    "AddedDate": "2025-09-10T00:00:00Z",
    "PwnCount": 42000,
    "Description": "Recent test breach for fixture use.",
    "DataClasses": ["Email addresses"],
    "IsVerified": true,
    "IsFabricated": false,
    "IsSensitive": false,
    "IsRetired": false,
    "IsSpamList": false,
    "IsMalware": false
  }
]
```

- [ ] **Step 2: Write the failing tests**

`tests/unit/collectors/test_breaches.py`:

```python
"""Tests for tradecraft.collectors.breaches."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.breaches import BreachesCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixture(fixtures_dir: Path) -> list[dict]:
    return json.loads((fixtures_dir / "breaches" / "hibp_acme.json").read_text())


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = BreachesCollector()
    assert c.name == "breaches"
    assert c.safe_for_hosted is False
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_emits_history_and_recent_signals(http, fixture) -> None:
    client, cache = http
    respx.get("https://haveibeenpwned.com/api/v3/breaches").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BreachesCollector().run(ctx)

    assert Signal.BREACH_HISTORY in result.signals
    assert Signal.BREACH_RECENT in result.signals
    assert len(result.data["breaches"]) == 2
    # most recent first
    assert result.data["breaches"][0]["name"] == "AcmeRecent"


@respx.mock
async def test_no_breach_no_signals(http) -> None:
    client, cache = http
    respx.get("https://haveibeenpwned.com/api/v3/breaches").mock(
        return_value=httpx.Response(200, json=[])
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BreachesCollector().run(ctx)

    assert Signal.BREACH_HISTORY not in result.signals
    assert Signal.BREACH_RECENT not in result.signals


@respx.mock
async def test_404_recorded_as_error_not_crash(http) -> None:
    client, cache = http
    respx.get("https://haveibeenpwned.com/api/v3/breaches").mock(
        return_value=httpx.Response(404)
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BreachesCollector().run(ctx)

    assert result.signals == []
    # No error if 404 just means "no breaches recorded for this domain"
    assert result.data["breaches"] == []
```

- [ ] **Step 3: Run tests, confirm ImportError fails**

```
uv run pytest tests/unit/collectors/test_breaches.py -v
```

Expected: `ModuleNotFoundError: No module named 'tradecraft.collectors.breaches'`.

- [ ] **Step 4: Implement `src/tradecraft/collectors/breaches.py`**

```python
"""Breaches collector: HIBP free domain endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_HIBP_DOMAIN_ENDPOINT = "https://haveibeenpwned.com/api/v3/breaches"
_RECENT_THRESHOLD_DAYS = 24 * 30  # 24 months, approximated


class BreachesCollector:
    name: ClassVar[str] = "breaches"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY, Role.ENG_LEADERSHIP}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        host = ctx.target.root_url.host or ""

        breaches_raw: list[dict[str, Any]] = []
        try:
            resp = await ctx.http.get(f"{_HIBP_DOMAIN_ENDPOINT}?domain={host}")
            if resp.status_code == 200:
                breaches_raw = resp.json()
            elif resp.status_code != 404:
                errors.append(
                    CollectorError(
                        stage="hibp",
                        message=f"unexpected status {resp.status_code}",
                        exception_type="HTTPStatusError",
                    )
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(
                CollectorError(
                    stage="hibp",
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )

        breaches = [
            {
                "name": b.get("Name"),
                "title": b.get("Title"),
                "domain": b.get("Domain"),
                "date": b.get("BreachDate"),
                "pwn_count": b.get("PwnCount"),
                "data_classes": b.get("DataClasses", []),
                "is_verified": b.get("IsVerified", False),
            }
            for b in breaches_raw
        ]
        breaches.sort(key=lambda b: b.get("date") or "", reverse=True)

        if breaches:
            signals.append(Signal.BREACH_HISTORY)
            cutoff = datetime.now(tz=UTC) - timedelta(days=_RECENT_THRESHOLD_DAYS)
            for b in breaches:
                date_str = b.get("date")
                if not date_str:
                    continue
                try:
                    bd = datetime.fromisoformat(str(date_str)).replace(tzinfo=UTC)
                except ValueError:
                    continue
                if bd >= cutoff:
                    signals.append(Signal.BREACH_RECENT)
                    break

        return CollectorResult(
            name=self.name,
            data={"breaches": breaches, "host": host},
            signals=signals,
            errors=errors,
            duration_ms=0,
        )
```

- [ ] **Step 5: Run tests + lint + type**

```
uv run pytest tests/unit/collectors/test_breaches.py -v
uv run ruff check src/tradecraft/collectors/breaches.py tests/unit/collectors/test_breaches.py
uv run mypy src/tradecraft/collectors/breaches.py
```

Expected: 4 tests pass, lint clean, mypy clean.

- [ ] **Step 6: Commit**

```
git add src/tradecraft/collectors/breaches.py tests/unit/collectors/test_breaches.py tests/fixtures/breaches/
git commit -m "$(cat <<'EOF'
feat(collectors): breaches via HIBP free domain endpoint

Emits BREACH_HISTORY and BREACH_RECENT (24-month cutoff) signals.
Treats 404 as "no breaches recorded" (not an error). HIBP is exempt
from robots since v0.1.0a1's target-scoped enforcement. Tagged
safe_for_hosted=False per spec — HIBP rate-limits aggressively from
shared IPs.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: github collector

**Files:**
- Create: `src/tradecraft/collectors/github.py`
- Create: `tests/unit/collectors/test_github.py`
- Create: `tests/fixtures/github/org_acme.json`
- Create: `tests/fixtures/github/repos_acme.json`

**Sources:**
- `https://api.github.com/orgs/<slug>` — org metadata (returns 404 if no public org by that name)
- `https://api.github.com/orgs/<slug>/repos?per_page=100&sort=updated` — top 100 most recently updated public repos

**Org-slug inference:** lowercased `company_slug` from `Target` is the first guess. If that 404s, try `company_name.lower().replace(" ", "")`. If both 404, emit `NO_PUBLIC_GITHUB`.

**Signals:**
- `Signal.OSS_FORWARD_CULTURE` if ≥ 10 public repos AND at least one has been pushed in last 90 days.
- `Signal.NO_PUBLIC_GITHUB` if both lookups 404.

**Per spec §6.6:** `safe_for_hosted = True` (single org lookup, low risk; GH API rate-limits per-IP but unauthenticated is fine for one lookup).

- [ ] **Step 1: Create fixtures**

`tests/fixtures/github/org_acme.json`:
```json
{
  "login": "acme",
  "id": 12345,
  "name": "Acme Corporation",
  "public_repos": 47,
  "followers": 1200,
  "html_url": "https://github.com/acme"
}
```

`tests/fixtures/github/repos_acme.json`:
```json
[
  {"name": "acme-cli", "language": "Go", "pushed_at": "2026-05-20T00:00:00Z", "stargazers_count": 4200, "fork": false, "archived": false},
  {"name": "acme-platform", "language": "TypeScript", "pushed_at": "2026-05-15T00:00:00Z", "stargazers_count": 1500, "fork": false, "archived": false},
  {"name": "acme-policy-engine", "language": "Rust", "pushed_at": "2026-04-29T00:00:00Z", "stargazers_count": 800, "fork": false, "archived": false},
  {"name": "acme-old-thing", "language": "Python", "pushed_at": "2021-01-01T00:00:00Z", "stargazers_count": 50, "fork": false, "archived": true},
  {"name": "fork-of-x", "language": "Go", "pushed_at": "2025-12-01T00:00:00Z", "stargazers_count": 1, "fork": true, "archived": false}
]
```

(Plus 8 more synthetic entries to push past the 10-repo threshold. The plan-executor should fabricate `acme-x` through `acme-x8` with `language: "Go"`, `pushed_at: "2025-11-01T00:00:00Z"`, `stargazers_count: 5`, `fork: false`, `archived: false` so the fixture file has 13 entries total.)

- [ ] **Step 2: Write failing tests**

`tests/unit/collectors/test_github.py`:

```python
"""Tests for tradecraft.collectors.github."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.github import GitHubCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, object]:
    return {
        "org": json.loads((fixtures_dir / "github" / "org_acme.json").read_text()),
        "repos": json.loads((fixtures_dir / "github" / "repos_acme.json").read_text()),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = GitHubCollector()
    assert c.name == "github"
    assert c.safe_for_hosted is True
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_oss_forward_culture(http, fixtures) -> None:
    client, cache = http
    respx.get("https://api.github.com/orgs/acme").mock(
        return_value=httpx.Response(200, json=fixtures["org"])
    )
    respx.get("https://api.github.com/orgs/acme/repos").mock(
        return_value=httpx.Response(200, json=fixtures["repos"])
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await GitHubCollector().run(ctx)

    assert Signal.OSS_FORWARD_CULTURE in result.signals
    assert Signal.NO_PUBLIC_GITHUB not in result.signals
    assert result.data["org"]["login"] == "acme"
    assert result.data["repo_count"] >= 10


@respx.mock
async def test_no_public_github_when_404(http) -> None:
    client, cache = http
    respx.get("https://api.github.com/orgs/acme").mock(return_value=httpx.Response(404))
    target = Target(company_name="Acme Corp", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await GitHubCollector().run(ctx)

    assert Signal.NO_PUBLIC_GITHUB in result.signals


@respx.mock
async def test_languages_aggregated(http, fixtures) -> None:
    client, cache = http
    respx.get("https://api.github.com/orgs/acme").mock(
        return_value=httpx.Response(200, json=fixtures["org"])
    )
    respx.get("https://api.github.com/orgs/acme/repos").mock(
        return_value=httpx.Response(200, json=fixtures["repos"])
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await GitHubCollector().run(ctx)

    languages = result.data["languages"]
    assert "Go" in languages
    assert "TypeScript" in languages
```

- [ ] **Step 3: Run tests, confirm ImportError**

```
uv run pytest tests/unit/collectors/test_github.py -v
```

- [ ] **Step 4: Implement `src/tradecraft/collectors/github.py`**

```python
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
        unique_candidates = [c for c in candidates if c and not (c in seen or seen.add(c))]

        org: dict[str, Any] | None = None
        repos: list[dict[str, Any]] = []
        for slug in unique_candidates:
            org_url = _GH_ORG_URL.format(slug=slug)
            try:
                resp = await ctx.http.get(org_url)
            except Exception as exc:  # noqa: BLE001
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
                except Exception as exc:  # noqa: BLE001
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

        languages = Counter(
            r.get("language") for r in repos if r.get("language")
        ).most_common(10)

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
```

- [ ] **Step 5: Verify tests + lint + type**

```
uv run pytest tests/unit/collectors/test_github.py -v
uv run ruff check src/tradecraft/collectors/github.py tests/unit/collectors/test_github.py
uv run mypy src/tradecraft/collectors/github.py
```

- [ ] **Step 6: Commit**

```
git add src/tradecraft/collectors/github.py tests/unit/collectors/test_github.py tests/fixtures/github/
git commit -m "$(cat <<'EOF'
feat(collectors): github org + repos + language aggregation

Two unauthenticated API calls per run. Tries the slugified company
name first, falls back to a no-spaces lowercase form. Emits
NO_PUBLIC_GITHUB on 404 of both, OSS_FORWARD_CULTURE when 10+ non-fork
non-archived repos exist and at least one was pushed in the last
90 days. Aggregates language histogram and top-10 by stars.
safe_for_hosted=True per spec.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: news collector

**Files:**
- Create: `src/tradecraft/collectors/news.py`
- Create: `tests/unit/collectors/test_news.py`
- Create: `tests/fixtures/news/google_news_acme.xml`
- Create: `tests/fixtures/news/hn_algolia_acme.json`

**Sources:**
- Google News RSS: `https://news.google.com/rss/search?q=<company-name>` — RSS feed; parse with `feedparser`.
- Hacker News Algolia search: `https://hn.algolia.com/api/v1/search?query=<company-name>&tags=story&numericFilters=created_at_i>=<24mo ago>` — JSON; recent stories only.

**Signals (keyword-based on combined headlines):**
- `RECENT_SECURITY_INCIDENT`: matches `breach|incident|hacked|ransomware|leak|cyber.*attack|data exposure` (case-insensitive).
- `RECENT_LAYOFFS`: matches `layoffs?|workforce reduction|headcount cut|staff cuts`.
- `RECENT_FUNDING`: matches `raises|series [a-z]|funding round|valuation|venture round|seed round`.
- `RECENT_LEADERSHIP_CHANGE`: matches `appoints?|named (ceo|cfo|ciso|cto|coo)|new ceo|steps down|departs|joins as ceo`.

`safe_for_hosted = False` (RSS + cross-site scraping from shared IPs invites blocks).

- [ ] **Step 1: Create fixtures**

`tests/fixtures/news/google_news_acme.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Acme Corp - Google News</title>
    <item>
      <title>Acme Corp raises $200M Series D at $1.5B valuation</title>
      <link>https://example-news.test/acme-funding</link>
      <pubDate>Fri, 16 May 2026 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Acme CEO Jane Smith steps down after eight years</title>
      <link>https://example-news.test/acme-ceo-out</link>
      <pubDate>Wed, 14 May 2026 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Acme confirms data breach affecting 42K customers</title>
      <link>https://example-news.test/acme-breach</link>
      <pubDate>Mon, 10 March 2025 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Acme reports record Q4 revenue growth</title>
      <link>https://example-news.test/acme-q4</link>
      <pubDate>Fri, 02 February 2026 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
```

`tests/fixtures/news/hn_algolia_acme.json`:

```json
{
  "hits": [
    {
      "title": "Acme open-sources its policy engine",
      "url": "https://example-news.test/acme-policy-engine",
      "created_at": "2026-04-12T10:00:00Z",
      "points": 412
    },
    {
      "title": "Layoffs at Acme: 9% workforce reduction",
      "url": "https://example-news.test/acme-layoffs",
      "created_at": "2026-01-09T10:00:00Z",
      "points": 287
    }
  ]
}
```

- [ ] **Step 2: Write failing tests**

`tests/unit/collectors/test_news.py`:

```python
"""Tests for tradecraft.collectors.news."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.news import NewsCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, object]:
    return {
        "rss": (fixtures_dir / "news" / "google_news_acme.xml").read_text(),
        "hn": json.loads((fixtures_dir / "news" / "hn_algolia_acme.json").read_text()),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = NewsCollector()
    assert c.name == "news"
    assert c.safe_for_hosted is False
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_signal_extraction_from_headlines(http, fixtures) -> None:
    client, cache = http
    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text=str(fixtures["rss"]))
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json=fixtures["hn"])
    )
    target = Target(company_name="Acme Corp", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    assert Signal.RECENT_FUNDING in result.signals  # "raises $200M Series D"
    assert Signal.RECENT_LEADERSHIP_CHANGE in result.signals  # "CEO ... steps down"
    assert Signal.RECENT_SECURITY_INCIDENT in result.signals  # "data breach"
    assert Signal.RECENT_LAYOFFS in result.signals  # "workforce reduction"
    assert len(result.data["items"]) >= 4


@respx.mock
async def test_empty_feeds_no_signals(http) -> None:
    client, cache = http
    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text="<rss><channel></channel></rss>")
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json={"hits": []})
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await NewsCollector().run(ctx)

    for s in (
        Signal.RECENT_FUNDING,
        Signal.RECENT_LAYOFFS,
        Signal.RECENT_SECURITY_INCIDENT,
        Signal.RECENT_LEADERSHIP_CHANGE,
    ):
        assert s not in result.signals
```

- [ ] **Step 3: Run tests, confirm ImportError**

```
uv run pytest tests/unit/collectors/test_news.py -v
```

- [ ] **Step 4: Implement `src/tradecraft/collectors/news.py`**

```python
"""News collector: Google News RSS + HN Algolia API."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable
from typing import Any, ClassVar
from urllib.parse import quote_plus

import feedparser  # type: ignore[import-untyped]

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}"
_HN_ALGOLIA = "https://hn.algolia.com/api/v1/search?query={q}&tags=story"

_SIGNAL_PATTERNS: tuple[tuple[Signal, re.Pattern[str]], ...] = (
    (
        Signal.RECENT_SECURITY_INCIDENT,
        re.compile(
            r"\b(breach|incident|hacked|ransomware|leak|cyber.{0,8}attack|data\s+exposure)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Signal.RECENT_LAYOFFS,
        re.compile(r"\b(layoffs?|workforce\s+reduction|headcount\s+cut|staff\s+cuts?)\b", re.IGNORECASE),
    ),
    (
        Signal.RECENT_FUNDING,
        re.compile(
            r"\b(raises?|series\s+[a-z]|funding\s+round|valuation|venture\s+round|seed\s+round)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Signal.RECENT_LEADERSHIP_CHANGE,
        re.compile(
            r"\b(appoints?|named\s+(?:ceo|cfo|ciso|cto|coo)|new\s+ceo|steps\s+down|departs|joins\s+as\s+ceo)\b",
            re.IGNORECASE,
        ),
    ),
)


class NewsCollector:
    name: ClassVar[str] = "news"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.SWE,
        Role.DEVOPS,
        Role.DATA,
        Role.ENG_LEADERSHIP,
        Role.GENERIC,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        q = quote_plus(ctx.target.company_name)

        rss_text, hn_json = await asyncio.gather(
            self._safe(ctx.http.get(_GOOGLE_NEWS_RSS.format(q=q)), errors, "rss"),
            self._safe(ctx.http.get(_HN_ALGOLIA.format(q=q)), errors, "hn"),
        )

        items: list[dict[str, Any]] = []
        if rss_text is not None:
            try:
                parsed = feedparser.parse(rss_text.text)
                for entry in parsed.entries[:50]:
                    items.append(
                        {
                            "title": getattr(entry, "title", ""),
                            "url": getattr(entry, "link", ""),
                            "published": getattr(entry, "published", ""),
                            "source": "google_news",
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    CollectorError(
                        stage="rss_parse",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )

        if hn_json is not None and hn_json.status_code == 200:
            try:
                hits = hn_json.json().get("hits", [])
                for h in hits[:50]:
                    items.append(
                        {
                            "title": h.get("title", ""),
                            "url": h.get("url", ""),
                            "published": h.get("created_at", ""),
                            "source": "hn",
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    CollectorError(
                        stage="hn_parse",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )

        text_blob = " | ".join(i["title"] for i in items)
        for sig, pattern in _SIGNAL_PATTERNS:
            if pattern.search(text_blob):
                signals.append(sig)

        return CollectorResult(
            name=self.name,
            data={"items": items, "headline_count": len(items)},
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

    @staticmethod
    async def _safe(
        awaitable: Awaitable[Any],
        errors: list[CollectorError],
        stage: str,
    ) -> Any | None:
        try:
            return await awaitable
        except Exception as exc:  # noqa: BLE001
            errors.append(
                CollectorError(
                    stage=stage,
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )
            return None
```

Note: `feedparser` is already in `pyproject.toml` dependencies — no install needed.

- [ ] **Step 5: Verify + commit**

```
uv run pytest tests/unit/collectors/test_news.py -v
uv run ruff check src/tradecraft/collectors/news.py tests/unit/collectors/test_news.py
uv run mypy src/tradecraft/collectors/news.py
```

```
git add src/tradecraft/collectors/news.py tests/unit/collectors/test_news.py tests/fixtures/news/
git commit -m "$(cat <<'EOF'
feat(collectors): news via Google News RSS + HN Algolia

Concurrent fetch of two feeds via asyncio.gather. Regex signal
extraction from combined headlines: RECENT_SECURITY_INCIDENT,
RECENT_LAYOFFS, RECENT_FUNDING, RECENT_LEADERSHIP_CHANGE. Items
preserved in data for renderer display. safe_for_hosted=False per
spec; aggressive cross-site fetches from shared IPs invite blocks.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: company collector

**Files:**
- Create: `src/tradecraft/collectors/company.py`
- Create: `tests/unit/collectors/test_company.py`
- Create: `tests/fixtures/company/acme_about.html`
- Create: `tests/fixtures/company/acme_team.html`

**Source:** the target's own site at standard paths: `/about`, `/about-us`, `/team`, `/leadership`, `/careers`, `/press`, `/blog`. Fetch in parallel; tolerate 404s.

**Parsing (selectolax already pinned):**
- Strip whitespace from `<title>`, `<meta name="description">`.
- Extract `JSON-LD` `Organization` block if present.
- Headings (`h1`/`h2`/`h3`) for product/team enumeration.

**Signals:**
- `RECENT_PRESS_RELEASE` if any press-page heading has a date string within last 90 days (regex `\b(20\d{2})\b` matched against current year or current-year-1).
- `FOUNDER_TECHNICAL` if any team page heading or bio mentions a phrase like `engineer|cto|cs|computer science|stanford|MIT` near "founder"/"co-founder".
- `PRODUCT_LIST_EMPTY` if no `<h2>` or `<h3>` headings found on `/`, `/about`, `/products`, OR if these paths 404.

`safe_for_hosted = True` (single target host, robots-respected).

- [ ] **Step 1: Create fixtures**

`tests/fixtures/company/acme_about.html`:
```html
<!doctype html><html><head>
<title>About Acme</title>
<meta name="description" content="Acme builds modern security tooling.">
</head><body>
<h1>About Acme</h1>
<p>Founded in 2018 by Jane Smith, CTO, formerly Principal Engineer at Stanford.</p>
<h2>Our products</h2>
<ul><li>Acme Cloud</li><li>Acme Edge</li></ul>
<h2>Recent news</h2>
<p>Read our latest 2026 announcement.</p>
</body></html>
```

`tests/fixtures/company/acme_team.html`:
```html
<!doctype html><html><head><title>Team - Acme</title></head><body>
<h1>The team</h1>
<h2>Jane Smith, Co-founder & CTO</h2>
<p>Computer science background, ex-Google staff engineer.</p>
<h2>Sam Lee, Co-founder & CEO</h2>
<p>Business operations background.</p>
</body></html>
```

- [ ] **Step 2: Write failing tests**

`tests/unit/collectors/test_company.py`:

```python
"""Tests for tradecraft.collectors.company."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.company import CompanyCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, str]:
    return {
        "about": (fixtures_dir / "company" / "acme_about.html").read_text(),
        "team": (fixtures_dir / "company" / "acme_team.html").read_text(),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = CompanyCollector()
    assert c.name == "company"
    assert c.safe_for_hosted is True


@respx.mock
async def test_extracts_signals(http, fixtures) -> None:
    client, cache = http
    # robots.txt is required by target-scoped enforcement
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/about").mock(
        return_value=httpx.Response(200, text=fixtures["about"])
    )
    respx.get("https://acme.com/team").mock(
        return_value=httpx.Response(200, text=fixtures["team"])
    )
    # Default 404 for other paths
    respx.get("").mock(return_value=httpx.Response(404))

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await CompanyCollector().run(ctx)

    assert Signal.FOUNDER_TECHNICAL in result.signals  # "CTO, ... Stanford"
    assert "about" in {p["path"] for p in result.data["pages"]}
    assert any("Acme Cloud" in str(p) for p in result.data["pages"])


@respx.mock
async def test_no_pages_emits_product_empty(http) -> None:
    client, cache = http
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("").mock(return_value=httpx.Response(404))

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await CompanyCollector().run(ctx)

    assert Signal.PRODUCT_LIST_EMPTY in result.signals
```

- [ ] **Step 3: Run tests, confirm fail**

- [ ] **Step 4: Implement `src/tradecraft/collectors/company.py`**

```python
"""Company collector: parse standard pages on the target's own site."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable
from typing import Any, ClassVar

from selectolax.parser import HTMLParser

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_PATHS = ("/about", "/about-us", "/team", "/leadership", "/careers", "/press", "/blog")
_TECH_HINTS = re.compile(
    r"\b(engineer|cto|cs|computer\s+science|stanford|mit|principal|staff\s+engineer)\b",
    re.IGNORECASE,
)
_FOUNDER_HINTS = re.compile(r"\b(co.?founder|founder|founding)\b", re.IGNORECASE)


class CompanyCollector:
    name: ClassVar[str] = "company"
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
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        base = str(ctx.target.root_url).rstrip("/")

        results = await asyncio.gather(
            *(self._safe(ctx.http.get(f"{base}{p}"), errors, p) for p in _PATHS)
        )

        pages: list[dict[str, Any]] = []
        for path, resp in zip(_PATHS, results, strict=True):
            if resp is None or resp.status_code != 200:
                continue
            tree = HTMLParser(resp.text)
            title_el = tree.css_first("title")
            description_el = tree.css_first('meta[name="description"]')
            headings = [h.text(strip=True) for h in tree.css("h1, h2, h3") if h.text(strip=True)]
            body_text = tree.body.text(strip=True) if tree.body else ""
            pages.append(
                {
                    "path": path.strip("/"),
                    "title": title_el.text(strip=True) if title_el else "",
                    "description": description_el.attributes.get("content", "")
                    if description_el
                    else "",
                    "headings": headings,
                    "body_excerpt": body_text[:1000],
                }
            )

        combined_text = " ".join(p["body_excerpt"] for p in pages)
        if _FOUNDER_HINTS.search(combined_text) and _TECH_HINTS.search(combined_text):
            signals.append(Signal.FOUNDER_TECHNICAL)

        # PRODUCT_LIST_EMPTY: zero pages with headings indicates a sparse site.
        if not any(p["headings"] for p in pages):
            signals.append(Signal.PRODUCT_LIST_EMPTY)

        # RECENT_PRESS_RELEASE: current year present in any heading.
        from datetime import UTC, datetime

        current_year = datetime.now(tz=UTC).year
        prev_year = current_year - 1
        year_re = re.compile(rf"\b({current_year}|{prev_year})\b")
        if any(year_re.search(h) for p in pages for h in p["headings"]):
            signals.append(Signal.RECENT_PRESS_RELEASE)

        return CollectorResult(
            name=self.name,
            data={"pages": pages, "page_count": len(pages)},
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

    @staticmethod
    async def _safe(
        awaitable: Awaitable[Any],
        errors: list[CollectorError],
        stage: str,
    ) -> Any | None:
        try:
            return await awaitable
        except Exception as exc:  # noqa: BLE001
            errors.append(
                CollectorError(
                    stage=stage,
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )
            return None
```

- [ ] **Step 5: Verify + commit**

```
uv run pytest tests/unit/collectors/test_company.py -v
uv run ruff check src/tradecraft/collectors/company.py tests/unit/collectors/test_company.py
uv run mypy src/tradecraft/collectors/company.py
```

```
git add src/tradecraft/collectors/company.py tests/unit/collectors/test_company.py tests/fixtures/company/
git commit -m "$(cat <<'EOF'
feat(collectors): company via /about /team /careers /blog /press

asyncio.gather across 7 standard paths; tolerate 404s. selectolax
parses each page for title/description/headings + body excerpt.
Signals: FOUNDER_TECHNICAL (founder+tech hint co-occur),
PRODUCT_LIST_EMPTY (no headings anywhere), RECENT_PRESS_RELEASE
(current/prev year mentioned in any heading). safe_for_hosted=True.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: job collector

**Files:**
- Create: `src/tradecraft/collectors/job.py`
- Create: `tests/unit/collectors/test_job.py`
- Create: `tests/fixtures/job/greenhouse_acme.html`
- Create: `tests/fixtures/job/lever_acme.html`

**Source:** only the user-supplied `--job <url>`. If `target.job_url is None`, the collector emits an empty result with no signals (not an error).

**Parsing:** Domain-based heuristics for major boards:
- `*.greenhouse.io`: title in `<h1.app-title>`, content in `<div#content>`.
- `*.lever.co`: title in `<h2.posting-headline>`, content in `<div.section-wrapper>`.
- `*.workday.com`, `*.ashbyhq.com`, `*.smartrecruiters.com`: fall back to generic title + body extraction.
- Generic fallback for unknown hosts: extract `<h1>` + concatenated `<p>` text.

**Cross-reference signals (requires github collector's data; but we keep collectors independent at run-time, so we just extract from text):**
- Extract a stack-keyword list from the JD text (Python, Go, Rust, Java, Kubernetes, AWS, GCP, Azure, etc.) and store it. The actual `LANGUAGES_MISMATCH_JOB` / `STACK_ALIGNMENT_STRONG` signals are computed in the heuristic-analyzer step (Task 14 in v0.1.0a0 already exists). v0.2.0 keeps the collector pure: it just extracts the JD stack.

Wait — re-reading the existing heuristic analyzer: it only consumes `findings.all_signals`, not cross-collector data. To produce stack-match signals, EITHER the analyzer needs cross-references OR a collector needs to compute it.

**Decision for v0.2.0:** the `job` collector itself computes `LANGUAGES_MISMATCH_JOB` / `STACK_ALIGNMENT_STRONG` by reading `findings` via a new optional argument. But that changes the Collector protocol. Cleaner approach: leave both signals on the table for v0.2.0 and emit them from a small post-processor that runs after collectors but before heuristic analysis. Adding a `cross_reference.py` analyzer is overkill for one signal pair. Simplest path: **the `job` collector accepts an optional `github_data` injected via `ctx`**.

Even simpler still: the `Orchestrator` is allowed to pass collector results to other collectors via `CollectorContext`. v0.2.0 adds `ctx.findings_so_far: list[CollectorResult]` populated by orchestrator. The `job` collector reads `findings_so_far` to find the github collector's `languages` dict.

This is a small protocol extension. It's worth the complexity because:
1. It enables cross-collector signals beyond just stack-match (M&A might consume news + business).
2. It keeps each collector's logic local (no separate cross-reference layer).

**Protocol change:** `CollectorContext` gains `findings_so_far: list[CollectorResult]`. The orchestrator builds it up incrementally — collectors run concurrently per-group, with groups ordered such that dependencies land first. Default: all collectors run in one group (current behavior); `findings_so_far` is empty for everyone. Future: collectors can declare `depends_on: set[str]` for ordering.

For v0.2.0 we ship the bare minimum: `findings_so_far: list[CollectorResult]` field on context, populated as an empty list for now. The `job` collector tolerates missing `findings_so_far` data; stack-match signals only emit when github's result is available. Wiring github-before-job ordering is deferred to a future task or v0.3.0.

**For this plan: skip the stack-match signals.** The job collector extracts the JD stack into `data["stack"]` but does NOT emit `LANGUAGES_MISMATCH_JOB` or `STACK_ALIGNMENT_STRONG`. The renderer (Task 11) will surface the JD stack and the GitHub language histogram side by side so the candidate can compare. The templates can still be triggered by users running with role-tags that include them in v0.3.0 when proper cross-collector wiring lands.

`safe_for_hosted = True` (single user-provided URL).

- [ ] **Step 1: Create fixtures**

`tests/fixtures/job/greenhouse_acme.html`:
```html
<!doctype html><html><body>
<h1 class="app-title">Senior Security Engineer</h1>
<div id="content">
<p>We're looking for a Senior Security Engineer to join our infrastructure team.</p>
<p>You'll work with Go, Kubernetes, AWS, and our in-house policy engine in Rust.</p>
<h3>Responsibilities</h3>
<ul><li>Threat modeling new services</li><li>On-call rotation</li></ul>
<h3>Required</h3>
<ul><li>5+ years in security engineering</li><li>Go or Rust experience</li></ul>
</div>
</body></html>
```

`tests/fixtures/job/lever_acme.html`:
```html
<!doctype html><html><body>
<h2 class="posting-headline"><a>Staff Application Security Engineer</a></h2>
<div class="section-wrapper">
<p>Lead AppSec across our Python services. Experience with SBOMs and supply-chain controls required.</p>
</div>
</body></html>
```

- [ ] **Step 2: Write failing tests**

`tests/unit/collectors/test_job.py`:

```python
"""Tests for tradecraft.collectors.job."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.job import JobCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, str]:
    return {
        "gh": (fixtures_dir / "job" / "greenhouse_acme.html").read_text(),
        "lever": (fixtures_dir / "job" / "lever_acme.html").read_text(),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="boards.greenhouse.io") as c:
        yield c, cache


def test_metadata() -> None:
    c = JobCollector()
    assert c.name == "job"
    assert c.safe_for_hosted is True
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_greenhouse_extraction(http, fixtures) -> None:
    client, cache = http
    # robots required by target-scoped enforcement
    respx.get("https://boards.greenhouse.io/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://boards.greenhouse.io/acme/jobs/123").mock(
        return_value=httpx.Response(200, text=fixtures["gh"])
    )
    target = Target(
        company_name="Acme",
        root_url="https://acme.com",
        job_url="https://boards.greenhouse.io/acme/jobs/123",
    )
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await JobCollector().run(ctx)

    assert result.data["title"] == "Senior Security Engineer"
    stack = set(result.data["stack"])
    assert {"Go", "Kubernetes", "AWS", "Rust"} <= stack


async def test_no_job_url_no_op() -> None:
    cache = Cache(directory=Path("."), default_ttl=60, enabled=False)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as client:
        target = Target(company_name="Acme", root_url="https://acme.com")
        ctx = CollectorContext(target=target, http=client, cache=cache)
        result = await JobCollector().run(ctx)
    assert result.data == {} or result.data.get("title") is None
    assert result.errors == []
```

- [ ] **Step 3: Run tests, confirm fail**

- [ ] **Step 4: Implement `src/tradecraft/collectors/job.py`**

```python
"""Job listing collector: parse the user-supplied JD URL."""

from __future__ import annotations

import re
from typing import Any, ClassVar
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
    "Python", "Go", "Rust", "Java", "Kotlin", "Scala", "Ruby", "Node",
    "TypeScript", "JavaScript", "C#", "C++", "Swift",
    "Kubernetes", "Docker", "Terraform", "Ansible",
    "AWS", "GCP", "Azure", "Vercel", "Cloudflare",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Kafka",
    "React", "Next.js", "Django", "Flask", "FastAPI", "Spring",
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
            return CollectorResult(
                name=self.name, data={}, signals=[], errors=[], duration_ms=0
            )

        errors: list[CollectorError] = []
        signals: list[Signal] = []

        try:
            resp = await ctx.http.get(str(ctx.target.job_url))
        except Exception as exc:  # noqa: BLE001
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
```

- [ ] **Step 5: Verify + commit**

```
uv run pytest tests/unit/collectors/test_job.py -v
uv run ruff check src/tradecraft/collectors/job.py tests/unit/collectors/test_job.py
uv run mypy src/tradecraft/collectors/job.py
```

```
git add src/tradecraft/collectors/job.py tests/unit/collectors/test_job.py tests/fixtures/job/
git commit -m "$(cat <<'EOF'
feat(collectors): job listing parser (greenhouse / lever / generic)

Reads the --job URL only; emits empty result when job_url is None.
Host-based extractors for greenhouse.io and lever.co; generic
<h1> + body fallback for unknown hosts. Stack-keyword scan
extracts language/framework/cloud mentions. Cross-collector
stack-match signals deferred to v0.3.0 when findings_so_far is
wired through CollectorContext.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: people collector

**Files:**
- Create: `src/tradecraft/collectors/people.py`
- Create: `tests/unit/collectors/test_people.py`
- Create: `tests/fixtures/people/acme_blog.html`

**Source:** ONLY the target's own engineering blog at `/blog`, `/engineering`, `/engineering-blog`, `/eng-blog`. Extract author bylines (the `<meta name="author">` tag and the first author/byline element on the page using common selectors).

**Out:** LinkedIn scraping, conference-speaker indexes (deferred), GitHub member API (avoid noise; safer to leave out v0.2.0).

**Signals:**
- `STRONG_ENG_BRAND` if at least 3 distinct authors detected across the blog index.
- `QUIET_ENG_BRAND` if the blog endpoint 404s or zero authors found.

`safe_for_hosted = False` (multi-path probing more aggressive than the company collector; defer to CLI).

- [ ] **Step 1: Create fixture**

`tests/fixtures/people/acme_blog.html`:
```html
<!doctype html><html><body>
<article>
  <h2>How we built our policy engine</h2>
  <span class="byline">by Sam Lee</span>
</article>
<article>
  <h2>From monolith to event-driven</h2>
  <span class="byline">by Jane Smith</span>
</article>
<article>
  <h2>Notes on incident response</h2>
  <span class="byline">by Priya Rao</span>
</article>
</body></html>
```

- [ ] **Step 2: Write failing tests**

`tests/unit/collectors/test_people.py`:

```python
"""Tests for tradecraft.collectors.people."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.people import PeopleCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def blog_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "people" / "acme_blog.html").read_text()


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = PeopleCollector()
    assert c.name == "people"
    assert c.safe_for_hosted is False


@respx.mock
async def test_strong_brand_signal(http, blog_html) -> None:
    client, cache = http
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/blog").mock(
        return_value=httpx.Response(200, text=blog_html)
    )
    respx.get("").mock(return_value=httpx.Response(404))  # default 404

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await PeopleCollector().run(ctx)

    assert Signal.STRONG_ENG_BRAND in result.signals
    assert "Sam Lee" in result.data["authors"]


@respx.mock
async def test_quiet_brand_when_no_blog(http) -> None:
    client, cache = http
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("").mock(return_value=httpx.Response(404))

    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await PeopleCollector().run(ctx)

    assert Signal.QUIET_ENG_BRAND in result.signals
```

- [ ] **Step 3: Implement `src/tradecraft/collectors/people.py`**

```python
"""People collector: blog authors only."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable
from typing import Any, ClassVar

from selectolax.parser import HTMLParser

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_BLOG_PATHS = ("/blog", "/engineering", "/engineering-blog", "/eng-blog")
_BYLINE_RE = re.compile(r"by\s+([A-Z][A-Za-z\.\-']+(?:\s+[A-Z][A-Za-z\.\-']+){0,3})", re.IGNORECASE)
_STRONG_BRAND_AUTHOR_THRESHOLD = 3


class PeopleCollector:
    name: ClassVar[str] = "people"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.SWE,
        Role.DEVOPS,
        Role.DATA,
        Role.ENG_LEADERSHIP,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        base = str(ctx.target.root_url).rstrip("/")

        results = await asyncio.gather(
            *(self._safe(ctx.http.get(f"{base}{p}"), errors, p) for p in _BLOG_PATHS)
        )
        authors: list[str] = []
        seen: set[str] = set()
        for resp in results:
            if resp is None or resp.status_code != 200:
                continue
            authors.extend(self._extract_authors(resp.text, seen))

        if len(authors) >= _STRONG_BRAND_AUTHOR_THRESHOLD:
            signals.append(Signal.STRONG_ENG_BRAND)
        else:
            signals.append(Signal.QUIET_ENG_BRAND)

        return CollectorResult(
            name=self.name,
            data={"authors": authors, "author_count": len(authors)},
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

    @staticmethod
    def _extract_authors(html: str, seen: set[str]) -> list[str]:
        tree = HTMLParser(html)
        out: list[str] = []
        # 1. <meta name="author">
        meta = tree.css_first('meta[name="author"]')
        if meta:
            v = meta.attributes.get("content")
            if v and v not in seen:
                seen.add(v)
                out.append(v)
        # 2. byline elements (common class names)
        for sel in (".byline", ".author", ".post-author", "[rel=author]"):
            for el in tree.css(sel):
                t = el.text(strip=True)
                m = _BYLINE_RE.search(t)
                name = m.group(1) if m else t
                if name and name not in seen:
                    seen.add(name)
                    out.append(name)
        return out

    @staticmethod
    async def _safe(
        awaitable: Awaitable[Any],
        errors: list[CollectorError],
        stage: str,
    ) -> Any | None:
        try:
            return await awaitable
        except Exception as exc:  # noqa: BLE001
            errors.append(
                CollectorError(
                    stage=stage,
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )
            return None
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest tests/unit/collectors/test_people.py -v
uv run ruff check src/tradecraft/collectors/people.py tests/unit/collectors/test_people.py
uv run mypy src/tradecraft/collectors/people.py
```

```
git add src/tradecraft/collectors/people.py tests/unit/collectors/test_people.py tests/fixtures/people/
git commit -m "$(cat <<'EOF'
feat(collectors): people via target's eng blog authors

Probes /blog /engineering /engineering-blog /eng-blog. Extracts
authors from meta[name=author] + .byline/.author/.post-author/[rel=author]
selectors. Emits STRONG_ENG_BRAND (>=3 distinct authors) or
QUIET_ENG_BRAND otherwise. Conference-speaker indexes deferred to a
later release. safe_for_hosted=False per spec.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: business collector

**Files:**
- Create: `src/tradecraft/collectors/business.py`
- Create: `tests/unit/collectors/test_business.py`
- Create: `tests/fixtures/business/sec_edgar_acme.json`
- Create: `tests/fixtures/business/wikipedia_acme.html`

**Sources:**
- SEC EDGAR full-text search: `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=<name>&type=10-K&dateb=&owner=include&count=10&action=getcompany`. Returns HTML; parse for filings.
- A simpler approach for v0.2.0: hit EDGAR's JSON tickers endpoint `https://www.sec.gov/files/company_tickers.json` (free, public), see if company name matches; if so, fetch the most recent 10-K filing index.
- Wikipedia: `https://en.wikipedia.org/wiki/<TitleCased_company>` — try slug variants; parse infobox.

**For v0.2.0 simplicity:** ship only the Wikipedia infobox parse and a basic SEC ticker-table lookup. Glassdoor is left out (HTML structure changes frequently; defer).

**Signals:**
- `PUBLIC_COMPANY` if the SEC ticker JSON contains a match for the company name (substring).
- `WIKIPEDIA_INFOBOX_PRESENT` if a Wikipedia page exists with an `.infobox` table.
- `RECENT_10K` is NOT emitted in v0.2.0 (the EDGAR filings parsing is brittle); push to v0.3.0.

`safe_for_hosted = False` (multi-host probing).

- [ ] **Step 1: Create fixtures**

`tests/fixtures/business/sec_edgar_acme.json`:
```json
{
  "0": {"cik_str": 1234567, "ticker": "ACME", "title": "Acme Corporation"}
}
```

`tests/fixtures/business/wikipedia_acme.html`:
```html
<!doctype html><html><body>
<table class="infobox">
<tr><th>Founded</th><td>2018</td></tr>
<tr><th>Headquarters</th><td>San Francisco, California</td></tr>
<tr><th>Industry</th><td>Security software</td></tr>
</table>
<p>Acme Corporation is a US security software company.</p>
</body></html>
```

- [ ] **Step 2: Write failing tests**

`tests/unit/collectors/test_business.py`:

```python
"""Tests for tradecraft.collectors.business."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.business import BusinessCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, object]:
    return {
        "sec": json.loads((fixtures_dir / "business" / "sec_edgar_acme.json").read_text()),
        "wiki": (fixtures_dir / "business" / "wikipedia_acme.html").read_text(),
    }


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = BusinessCollector()
    assert c.name == "business"
    assert c.safe_for_hosted is False


@respx.mock
async def test_public_company_and_wikipedia(http, fixtures) -> None:
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json=fixtures["sec"])
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(200, text=str(fixtures["wiki"]))
    )
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    assert Signal.PUBLIC_COMPANY in result.signals
    assert Signal.WIKIPEDIA_INFOBOX_PRESENT in result.signals
    assert result.data["ticker"] == "ACME"


@respx.mock
async def test_no_match(http) -> None:
    client, cache = http
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json={"0": {"cik_str": 1, "ticker": "XYZ", "title": "Unrelated"}})
    )
    respx.get("").mock(return_value=httpx.Response(404))
    target = Target(company_name="Acme Corporation", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await BusinessCollector().run(ctx)

    assert Signal.PUBLIC_COMPANY not in result.signals
    assert Signal.WIKIPEDIA_INFOBOX_PRESENT not in result.signals
```

- [ ] **Step 3: Implement `src/tradecraft/collectors/business.py`**

```python
"""Business collector: SEC EDGAR ticker lookup + Wikipedia infobox."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any, ClassVar

from selectolax.parser import HTMLParser

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/{slug}"


class BusinessCollector:
    name: ClassVar[str] = "business"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.ENG_LEADERSHIP,
        Role.GENERIC,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        data: dict[str, Any] = {"ticker": None, "wikipedia": None}

        company_lc = ctx.target.company_name.lower()
        wiki_slug = ctx.target.company_name.replace(" ", "_")

        sec_resp, wiki_resp = await asyncio.gather(
            self._safe(ctx.http.get(_SEC_TICKERS_URL), errors, "sec"),
            self._safe(
                ctx.http.get(_WIKIPEDIA_URL.format(slug=wiki_slug)), errors, "wiki"
            ),
        )

        if sec_resp is not None and sec_resp.status_code == 200:
            try:
                tickers = sec_resp.json()
                for entry in tickers.values():
                    title = str(entry.get("title", "")).lower()
                    if company_lc in title:
                        data["ticker"] = entry.get("ticker")
                        data["cik"] = entry.get("cik_str")
                        signals.append(Signal.PUBLIC_COMPANY)
                        break
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    CollectorError(
                        stage="sec_parse",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )

        if wiki_resp is not None and wiki_resp.status_code == 200:
            try:
                tree = HTMLParser(wiki_resp.text)
                infobox = tree.css_first("table.infobox")
                if infobox:
                    fields: dict[str, str] = {}
                    for row in infobox.css("tr"):
                        th = row.css_first("th")
                        td = row.css_first("td")
                        if th and td:
                            fields[th.text(strip=True)] = td.text(strip=True)
                    data["wikipedia"] = fields
                    signals.append(Signal.WIKIPEDIA_INFOBOX_PRESENT)
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    CollectorError(
                        stage="wiki_parse",
                        message=str(exc) or exc.__class__.__name__,
                        exception_type=exc.__class__.__name__,
                    )
                )

        return CollectorResult(
            name=self.name,
            data=data,
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

    @staticmethod
    async def _safe(
        awaitable: Awaitable[Any],
        errors: list[CollectorError],
        stage: str,
    ) -> Any | None:
        try:
            return await awaitable
        except Exception as exc:  # noqa: BLE001
            errors.append(
                CollectorError(
                    stage=stage,
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )
            return None
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest tests/unit/collectors/test_business.py -v
uv run ruff check src/tradecraft/collectors/business.py tests/unit/collectors/test_business.py
uv run mypy src/tradecraft/collectors/business.py
```

```
git add src/tradecraft/collectors/business.py tests/unit/collectors/test_business.py tests/fixtures/business/
git commit -m "$(cat <<'EOF'
feat(collectors): business via SEC ticker lookup + Wikipedia infobox

Two concurrent fetches: SEC's company_tickers.json (free, no auth)
for public-company status + ticker, and Wikipedia article for
infobox fields. Signals: PUBLIC_COMPANY when company name matches
a ticker entry; WIKIPEDIA_INFOBOX_PRESENT when an .infobox table
exists. RECENT_10K and Glassdoor parsing deferred — both are
brittle and not needed for the alpha. safe_for_hosted=False.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: ma collector

**Files:**
- Create: `src/tradecraft/collectors/ma.py`
- Create: `tests/unit/collectors/test_ma.py`
- Create: `tests/fixtures/ma/wikipedia_infobox_acme.html`

**Sources:**
- Same Wikipedia page as `business` but extracts `Subsidiaries` and `Parent` infobox fields.
- The `news` collector's data also surfaces M&A patterns, but to keep collectors independent we re-scan the headlines via a small inline regex inside `ma`.

**Signals:**
- `M_A_RECENT` if any Wikipedia infobox `Subsidiaries` field references a year within last 24 months OR if a news-style query against Google News for `<company> acquires` returns any hit.
- `SUBSIDIARY_OF` if Wikipedia infobox has a non-empty `Parent` field.
- `M_A_FREQUENT_ACQUIRER` if Wikipedia infobox `Subsidiaries` lists 5+ companies.

For v0.2.0 simplicity, ship only `SUBSIDIARY_OF` and `M_A_FREQUENT_ACQUIRER` based on Wikipedia. Defer `M_A_RECENT` (requires reliable date extraction).

`safe_for_hosted = False` (Wikipedia + news; same as business).

- [ ] **Step 1: Create fixture**

`tests/fixtures/ma/wikipedia_infobox_acme.html`:
```html
<!doctype html><html><body>
<table class="infobox">
<tr><th>Parent</th><td>Globex Industries</td></tr>
<tr><th>Subsidiaries</th><td>Beta Inc., Gamma LLC, Delta Co., Epsilon Ltd., Zeta GmbH</td></tr>
<tr><th>Founded</th><td>2018</td></tr>
</table>
</body></html>
```

- [ ] **Step 2: Write failing tests**

`tests/unit/collectors/test_ma.py`:

```python
"""Tests for tradecraft.collectors.ma."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.ma import MaCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixture(fixtures_dir: Path) -> str:
    return (fixtures_dir / "ma" / "wikipedia_infobox_acme.html").read_text()


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache, target_host="acme.com") as c:
        yield c, cache


def test_metadata() -> None:
    c = MaCollector()
    assert c.name == "ma"
    assert c.safe_for_hosted is False


@respx.mock
async def test_subsidiary_and_frequent_acquirer(http, fixture) -> None:
    client, cache = http
    respx.get("https://en.wikipedia.org/wiki/Acme").mock(
        return_value=httpx.Response(200, text=fixture)
    )
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    result = await MaCollector().run(ctx)

    assert Signal.SUBSIDIARY_OF in result.signals
    assert Signal.M_A_FREQUENT_ACQUIRER in result.signals
    assert result.data["parent"] == "Globex Industries"
    assert len(result.data["subsidiaries"]) == 5
```

- [ ] **Step 3: Implement `src/tradecraft/collectors/ma.py`**

```python
"""M&A collector: parent/subsidiaries via Wikipedia infobox."""

from __future__ import annotations

from typing import Any, ClassVar

from selectolax.parser import HTMLParser

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/{slug}"
_FREQUENT_ACQUIRER_THRESHOLD = 5


class MaCollector:
    name: ClassVar[str] = "ma"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {
        Role.CYBERSECURITY,
        Role.SWE,
        Role.ENG_LEADERSHIP,
        Role.GENERIC,
    }

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        errors: list[CollectorError] = []
        signals: list[Signal] = []
        wiki_slug = ctx.target.company_name.replace(" ", "_")
        data: dict[str, Any] = {"parent": None, "subsidiaries": []}

        try:
            resp = await ctx.http.get(_WIKIPEDIA_URL.format(slug=wiki_slug))
        except Exception as exc:  # noqa: BLE001
            errors.append(
                CollectorError(
                    stage="fetch",
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            )
            return CollectorResult(
                name=self.name, data=data, signals=signals, errors=errors, duration_ms=0
            )

        if resp.status_code != 200:
            return CollectorResult(
                name=self.name, data=data, signals=signals, errors=errors, duration_ms=0
            )

        tree = HTMLParser(resp.text)
        infobox = tree.css_first("table.infobox")
        if not infobox:
            return CollectorResult(
                name=self.name, data=data, signals=signals, errors=errors, duration_ms=0
            )

        for row in infobox.css("tr"):
            th = row.css_first("th")
            td = row.css_first("td")
            if not (th and td):
                continue
            label = th.text(strip=True).lower()
            value = td.text(separator=" ", strip=True)
            if label == "parent" and value:
                data["parent"] = value
                signals.append(Signal.SUBSIDIARY_OF)
            elif label == "subsidiaries" and value:
                subs = [s.strip() for s in value.split(",") if s.strip()]
                data["subsidiaries"] = subs
                if len(subs) >= _FREQUENT_ACQUIRER_THRESHOLD:
                    signals.append(Signal.M_A_FREQUENT_ACQUIRER)

        return CollectorResult(
            name=self.name,
            data=data,
            signals=signals,
            errors=errors,
            duration_ms=0,
        )
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest tests/unit/collectors/test_ma.py -v
uv run ruff check src/tradecraft/collectors/ma.py tests/unit/collectors/test_ma.py
uv run mypy src/tradecraft/collectors/ma.py
```

```
git add src/tradecraft/collectors/ma.py tests/unit/collectors/test_ma.py tests/fixtures/ma/
git commit -m "$(cat <<'EOF'
feat(collectors): m&a via wikipedia infobox parent/subsidiaries

One Wikipedia fetch; parses infobox for Parent and Subsidiaries
fields. SUBSIDIARY_OF fires when Parent has a value;
M_A_FREQUENT_ACQUIRER fires when Subsidiaries lists 5+ entities.
M_A_RECENT deferred to v0.3.0 (requires reliable date extraction
from news + Wikipedia history). safe_for_hosted=False.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: CLI registers all 8 collectors

**Files:**
- Modify: `src/tradecraft/cli.py`
- Modify: `tests/unit/test_cli.py`

- [ ] **Step 1: Update `_default_collectors()`**

In `src/tradecraft/cli.py`, find the existing `_default_collectors()` function and replace it. Also update the imports at the top to include each new collector.

Replace:
```python
from tradecraft.collectors.footprint import FootprintCollector
```

With:
```python
from tradecraft.collectors.breaches import BreachesCollector
from tradecraft.collectors.business import BusinessCollector
from tradecraft.collectors.company import CompanyCollector
from tradecraft.collectors.footprint import FootprintCollector
from tradecraft.collectors.github import GitHubCollector
from tradecraft.collectors.job import JobCollector
from tradecraft.collectors.ma import MaCollector
from tradecraft.collectors.news import NewsCollector
from tradecraft.collectors.people import PeopleCollector
```

Replace:
```python
def _default_collectors() -> list[Collector]:
    return [FootprintCollector()]
```

With:
```python
def _default_collectors() -> list[Collector]:
    return [
        FootprintCollector(),
        BreachesCollector(),
        GitHubCollector(),
        NewsCollector(),
        CompanyCollector(),
        JobCollector(),
        PeopleCollector(),
        BusinessCollector(),
        MaCollector(),
    ]
```

- [ ] **Step 2: Update the existing E2E CLI test if needed**

`tests/unit/test_cli.py` patches `tradecraft.cli._default_collectors` for its end-to-end test using a `StubFootprint`. That test should continue to pass without changes (it patches the function and supplies its own collector list). Verify with:

```
uv run pytest tests/unit/test_cli.py -v
```

- [ ] **Step 3: Add a smoke test that all 9 collectors are registered**

In `tests/unit/test_cli.py` add (at module level):

```python
def test_default_collectors_includes_all_v0_2_modules() -> None:
    from tradecraft.cli import _default_collectors

    collectors = _default_collectors()
    names = {c.name for c in collectors}
    assert names == {
        "footprint",
        "breaches",
        "github",
        "news",
        "company",
        "job",
        "people",
        "business",
        "ma",
    }
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest tests/unit/test_cli.py -v
uv run ruff check src/tradecraft/cli.py tests/unit/test_cli.py
uv run mypy src/tradecraft/cli.py
```

```
git add src/tradecraft/cli.py tests/unit/test_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): register all 9 v0.2.0 collectors as defaults

footprint, breaches, github, news, company, job, people, business,
ma. Orchestrator runs them concurrently via asyncio.gather; --only
and --skip flags work on the new names without code changes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Markdown renderer — per-collector sections

**Files:**
- Modify: `src/tradecraft/renderers/markdown.py`
- Modify: `tests/unit/renderers/test_markdown.py`

The current `markdown.py` renders only Snapshot + Web/Infra Footprint + Questions + Collection Notes. Now it needs sections for every new collector. The existing test asserts the four headings exist; we extend it.

- [ ] **Step 1: Write failing tests for the new sections**

In `tests/unit/renderers/test_markdown.py`, append:

```python
def test_renders_breaches_section_when_present() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="breaches",
                data={"breaches": [{"name": "AcmeOldLeak", "date": "2019-03-15", "pwn_count": 1500000, "data_classes": ["Email", "Passwords"]}]},
                signals=[Signal.BREACH_HISTORY],
                errors=[],
                duration_ms=50,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "## Breach history" in md
    assert "AcmeOldLeak" in md
    assert "2019-03-15" in md


def test_renders_github_section_when_present() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="github",
                data={
                    "org": {"login": "acme", "public_repos": 47},
                    "repo_count": 47,
                    "languages": {"Go": 20, "TypeScript": 15},
                    "top_repos": [{"name": "acme-cli", "stars": 4200, "language": "Go"}],
                },
                signals=[Signal.OSS_FORWARD_CULTURE],
                errors=[],
                duration_ms=50,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "## GitHub presence" in md
    assert "acme-cli" in md
    assert "Go" in md


def test_renders_news_section_when_present() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="news",
                data={
                    "items": [
                        {"title": "Acme raises $200M Series D", "source": "google_news", "published": "Fri, 16 May 2026 00:00:00 GMT"},
                    ],
                    "headline_count": 1,
                },
                signals=[Signal.RECENT_FUNDING],
                errors=[],
                duration_ms=50,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "## News & timeline" in md
    assert "Series D" in md


def test_renders_business_section_when_present() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="business",
                data={"ticker": "ACME", "wikipedia": {"Founded": "2018", "Industry": "Security software"}},
                signals=[Signal.PUBLIC_COMPANY, Signal.WIKIPEDIA_INFOBOX_PRESENT],
                errors=[],
                duration_ms=50,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "## Business & financial signals" in md
    assert "ACME" in md
    assert "Security software" in md
```

- [ ] **Step 2: Implement the new sections**

In `src/tradecraft/renderers/markdown.py`, replace the current `render_markdown` body to add the new section calls (preserving order in the report). Replace this block:

```python
def render_markdown(findings: Findings, questions: Sequence[Question]) -> str:
    target = findings.target
    parts: list[str] = []
    parts.append(f"# {target.company_name}")
    parts.append("")
    parts.append(_snapshot_section(findings))
    parts.append(_footprint_section(findings))
    parts.append(_questions_section(questions))
    parts.append(_collection_notes(findings))
    return "\n".join(parts).rstrip() + "\n"
```

With:

```python
def render_markdown(findings: Findings, questions: Sequence[Question]) -> str:
    target = findings.target
    parts: list[str] = []
    parts.append(f"# {target.company_name}")
    parts.append("")
    parts.append(_snapshot_section(findings))
    parts.append(_footprint_section(findings))
    parts.append(_company_section(findings))
    parts.append(_job_section(findings))
    parts.append(_github_section(findings))
    parts.append(_news_section(findings))
    parts.append(_breaches_section(findings))
    parts.append(_business_section(findings))
    parts.append(_ma_section(findings))
    parts.append(_people_section(findings))
    parts.append(_questions_section(questions))
    parts.append(_collection_notes(findings))
    return "\n".join(parts).rstrip() + "\n"
```

Then append the new section functions at the end of the module (before the `_collection_notes` function which already exists):

```python
def _company_section(findings: Findings) -> str:
    result = findings.collector("company")
    lines = ["## Company profile", ""]
    if result is None or not result.data.get("pages"):
        lines.append("_No company profile data collected._")
        lines.append("")
        return "\n".join(lines)
    for page in result.data["pages"]:
        if page.get("title"):
            lines.append(f"### `{page['path']}` — {page['title']}")
        if page.get("description"):
            lines.append(f"> {page['description']}")
        if page.get("headings"):
            for h in page["headings"][:8]:
                lines.append(f"- {h}")
        lines.append("")
    return "\n".join(lines)


def _job_section(findings: Findings) -> str:
    result = findings.collector("job")
    lines = ["## Role-fit signals (from JD)", ""]
    if result is None or not result.data:
        lines.append("_No job URL supplied or no signals extracted._")
        lines.append("")
        return "\n".join(lines)
    if result.data.get("title"):
        lines.append(f"- **Title:** {result.data['title']}")
    if result.data.get("stack"):
        lines.append(f"- **Stack mentioned:** {', '.join(result.data['stack'])}")
    if result.data.get("url"):
        lines.append(f"- **URL:** {result.data['url']}")
    lines.append("")
    return "\n".join(lines)


def _github_section(findings: Findings) -> str:
    result = findings.collector("github")
    lines = ["## GitHub presence", ""]
    if result is None or not result.data.get("org"):
        lines.append("_No public GitHub org found, or collector skipped._")
        lines.append("")
        return "\n".join(lines)
    org = result.data["org"]
    lines.append(f"- **Org:** `{org.get('login')}`")
    lines.append(f"- **Repos visible:** {result.data.get('repo_count', 0)}")
    langs = result.data.get("languages") or {}
    if langs:
        top = ", ".join(f"{k} ({v})" for k, v in list(langs.items())[:6])
        lines.append(f"- **Languages:** {top}")
    top_repos = result.data.get("top_repos") or []
    if top_repos:
        lines.append("")
        lines.append("### Top repos by stars")
        lines.append("")
        for r in top_repos[:5]:
            lines.append(f"- `{r.get('name')}` ({r.get('language', '?')}) — {r.get('stars', 0)} stars")
    lines.append("")
    return "\n".join(lines)


def _news_section(findings: Findings) -> str:
    result = findings.collector("news")
    lines = ["## News & timeline", ""]
    if result is None or not result.data.get("items"):
        lines.append("_No news items found._")
        lines.append("")
        return "\n".join(lines)
    for item in result.data["items"][:15]:
        title = item.get("title", "(untitled)")
        source = item.get("source", "")
        when = item.get("published", "")
        lines.append(f"- **{title}** _({source}, {when})_")
    lines.append("")
    return "\n".join(lines)


def _breaches_section(findings: Findings) -> str:
    result = findings.collector("breaches")
    lines = ["## Breach history", ""]
    if result is None or not result.data.get("breaches"):
        lines.append("_No public breach records for this domain._")
        lines.append("")
        return "\n".join(lines)
    for b in result.data["breaches"][:10]:
        date = b.get("date", "?")
        name = b.get("name", "(unknown)")
        pwn = b.get("pwn_count")
        classes = ", ".join(b.get("data_classes", [])[:5])
        line = f"- **{name}** ({date})"
        if pwn:
            line += f" — {pwn:,} affected"
        if classes:
            line += f"; classes: {classes}"
        lines.append(line)
    lines.append("")
    return "\n".join(lines)


def _business_section(findings: Findings) -> str:
    result = findings.collector("business")
    lines = ["## Business & financial signals", ""]
    if result is None or (not result.data.get("ticker") and not result.data.get("wikipedia")):
        lines.append("_No business signals collected._")
        lines.append("")
        return "\n".join(lines)
    if result.data.get("ticker"):
        lines.append(f"- **Public company:** ticker `{result.data['ticker']}`")
    wiki = result.data.get("wikipedia")
    if wiki:
        for key in ("Founded", "Headquarters", "Industry", "Employees", "Revenue"):
            if key in wiki:
                lines.append(f"- **{key}:** {wiki[key]}")
    lines.append("")
    return "\n".join(lines)


def _ma_section(findings: Findings) -> str:
    result = findings.collector("ma")
    lines = ["## Mergers & acquisitions", ""]
    if result is None or (not result.data.get("parent") and not result.data.get("subsidiaries")):
        lines.append("_No M&A data collected._")
        lines.append("")
        return "\n".join(lines)
    if result.data.get("parent"):
        lines.append(f"- **Parent:** {result.data['parent']}")
    subs = result.data.get("subsidiaries") or []
    if subs:
        lines.append(f"- **Subsidiaries ({len(subs)}):** {', '.join(subs[:8])}{'…' if len(subs) > 8 else ''}")
    lines.append("")
    return "\n".join(lines)


def _people_section(findings: Findings) -> str:
    result = findings.collector("people")
    lines = ["## People", ""]
    if result is None or not result.data.get("authors"):
        lines.append("_No publicly identifiable engineering content authors._")
        lines.append("")
        return "\n".join(lines)
    lines.append(f"- **Blog authors identified:** {len(result.data['authors'])}")
    for a in result.data["authors"][:10]:
        lines.append(f"  - {a}")
    lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 3: Verify + commit**

```
uv run pytest tests/unit/renderers/test_markdown.py -v
uv run ruff check src/tradecraft/renderers/markdown.py tests/unit/renderers/test_markdown.py
uv run mypy src/tradecraft/renderers/markdown.py
```

```
git add src/tradecraft/renderers/markdown.py tests/unit/renderers/test_markdown.py
git commit -m "$(cat <<'EOF'
feat(renderers): markdown sections for all v0.2.0 collectors

Adds Company profile, Role-fit signals, GitHub presence,
News & timeline, Breach history, Business & financial signals,
M&A, and People sections. Each section is a function that
gracefully degrades to a 'no data' note when its collector is
absent or empty — so partial runs still render coherently.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Bump version, update README + CHANGELOG

**Files:**
- Modify: `src/tradecraft/__init__.py`
- Modify: `CHANGELOG.md`
- Modify: `README.md`

- [ ] **Step 1: Bump `__version__`**

In `src/tradecraft/__init__.py`, change:
```python
__version__ = "0.1.0a1"
```
to:
```python
__version__ = "0.2.0"
```

- [ ] **Step 2: Update CHANGELOG**

In `CHANGELOG.md`, insert a new entry after the existing `## [Unreleased]` line:

```markdown
## [Unreleased]

## [0.2.0] - 2026-05-25

### Added

- All seven remaining collectors are wired and registered:
  - `breaches` — HIBP free domain endpoint; emits BREACH_HISTORY, BREACH_RECENT.
  - `github` — org + public-repo listing; emits OSS_FORWARD_CULTURE, NO_PUBLIC_GITHUB.
  - `news` — Google News RSS + HN Algolia; emits RECENT_SECURITY_INCIDENT,
    RECENT_LAYOFFS, RECENT_FUNDING, RECENT_LEADERSHIP_CHANGE.
  - `company` — about/team/careers/blog/press paths; emits FOUNDER_TECHNICAL,
    PRODUCT_LIST_EMPTY, RECENT_PRESS_RELEASE.
  - `job` — greenhouse/lever/generic JD parser; extracts stack keywords.
  - `people` — eng-blog author bylines; emits STRONG_ENG_BRAND, QUIET_ENG_BRAND.
  - `business` — SEC ticker JSON + Wikipedia infobox; emits PUBLIC_COMPANY,
    WIKIPEDIA_INFOBOX_PRESENT.
  - `ma` — Wikipedia infobox parent/subsidiaries; emits SUBSIDIARY_OF,
    M_A_FREQUENT_ACQUIRER.
- Template library expanded to ~45 templates spanning offensive, defensive,
  AppSec, and GRC sub-disciplines. Every signal has cybersec coverage.
- Markdown renderer gains per-collector sections; partial runs still render.

### Deferred

- LANGUAGES_MISMATCH_JOB / STACK_ALIGNMENT_STRONG signals require
  cross-collector reads (job ← github). Wiring `findings_so_far` into
  `CollectorContext` lands in v0.3.0.
- RECENT_10K and Glassdoor parsing in `business` — both are brittle.
- M_A_RECENT requires reliable date extraction — deferred.
- BYOK AI analyzer and Anthropic / OpenAI / Ollama / OpenAI-compat providers
  ship in v0.3.0.
- Hosted web preview ships in v1.1.
```

- [ ] **Step 3: Update README status block**

In `README.md`, replace:
```markdown
**Alpha (v0.1.0a1)** — walking skeleton with the `footprint` collector wired end-to-end. The remaining collectors (`breaches`, `github`, `news`, `company`, `job`, `people`, `business`, `m&a` — cybersec-prioritized order) and the BYOK AI analyzer ship in v0.2.0. Hosted web preview ships in v1.1.
```
with:
```markdown
**v0.2.0** — full collector roster shipped. `footprint`, `breaches`, `github`, `news`, `company`, `job`, `people`, `business`, `ma` all run by default. BYOK AI analyzer ships in v0.3.0; hosted web preview ships in v1.1.
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest -q
uv run python -c "import tradecraft; print(tradecraft.__version__)"
```

Expected: `0.2.0` and all tests still pass.

```
git add src/tradecraft/__init__.py CHANGELOG.md README.md
git commit -m "$(cat <<'EOF'
chore: bump version + update README/CHANGELOG for v0.2.0

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Multi-collector end-to-end test

**Files:**
- Create: `tests/integration/test_v0_2_end_to_end.py`

A single integration test that mocks all 9 collectors' upstream endpoints and runs the full CLI through to disk. Catches wiring regressions (renderer order, signal flow, file outputs).

- [ ] **Step 1: Write the test**

`tests/integration/test_v0_2_end_to_end.py`:

```python
"""End-to-end v0.2.0: CLI through all 9 collectors with mocked endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import respx
from typer.testing import CliRunner

from tradecraft.cli import app
from tradecraft.collectors.breaches import BreachesCollector
from tradecraft.collectors.business import BusinessCollector
from tradecraft.collectors.company import CompanyCollector
from tradecraft.collectors.footprint import FootprintCollector
from tradecraft.collectors.github import GitHubCollector
from tradecraft.collectors.job import JobCollector
from tradecraft.collectors.ma import MaCollector
from tradecraft.collectors.news import NewsCollector
from tradecraft.collectors.people import PeopleCollector


@respx.mock
def test_full_v0_2_run(tmp_path: Path, fixtures_dir: Path) -> None:
    # --- footprint deps ---
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=[{"name_value": "acme.com\nwww.acme.com"}])
    )
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers={"server": "nginx"})
    )
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    # --- breaches ---
    respx.get("https://haveibeenpwned.com/api/v3/breaches").mock(
        return_value=httpx.Response(200, json=[
            {"Name": "OldLeak", "BreachDate": "2019-01-01", "PwnCount": 10000,
             "DataClasses": ["Email"], "IsVerified": True, "Domain": "acme.com"}
        ])
    )

    # --- github ---
    respx.get("https://api.github.com/orgs/acme").mock(
        return_value=httpx.Response(200, json={"login": "acme", "public_repos": 47})
    )
    respx.get("https://api.github.com/orgs/acme/repos").mock(
        return_value=httpx.Response(200, json=[
            {"name": f"r{i}", "language": "Go", "pushed_at": "2026-05-20T00:00:00Z",
             "stargazers_count": 5, "fork": False, "archived": False}
            for i in range(12)
        ])
    )

    # --- news ---
    respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, text=
            "<rss><channel><item><title>Acme raises Series D</title>"
            "<link>https://x.test/a</link><pubDate>Fri, 16 May 2026 00:00:00 GMT</pubDate>"
            "</item></channel></rss>"
        )
    )
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json={"hits": []})
    )

    # --- company (other paths default to 404 via wildcard) ---
    respx.get("https://acme.com/about").mock(
        return_value=httpx.Response(200, text="<html><h1>About Acme</h1><h2>Products</h2></html>")
    )

    # --- job ---
    respx.get("https://boards.greenhouse.io/acme/jobs/1").mock(
        return_value=httpx.Response(200, text=
            "<html><h1 class='app-title'>Sec Eng</h1><div id='content'>Go, Kubernetes</div></html>"
        )
    )

    # --- business ---
    respx.get("https://www.sec.gov/files/company_tickers.json").mock(
        return_value=httpx.Response(200, json={"0": {"cik_str": 1, "ticker": "ACME", "title": "Acme Corporation"}})
    )
    respx.get("https://en.wikipedia.org/wiki/Acme_Corporation").mock(
        return_value=httpx.Response(200, text=
            "<html><table class='infobox'>"
            "<tr><th>Industry</th><td>Security</td></tr>"
            "<tr><th>Subsidiaries</th><td>A, B, C, D, E</td></tr>"
            "</table></html>"
        )
    )

    # --- ma (uses same Wikipedia URL; respx returns the same mock) ---

    # --- people (404 default) ---
    respx.get("").mock(return_value=httpx.Response(404))

    # --- DNS mock for footprint ---
    dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})
    runner = CliRunner()
    with patch(
        "tradecraft.cli._default_collectors",
        return_value=[
            FootprintCollector(_dns_lookup=dns),
            BreachesCollector(),
            GitHubCollector(),
            NewsCollector(),
            CompanyCollector(),
            JobCollector(),
            PeopleCollector(),
            BusinessCollector(),
            MaCollector(),
        ],
    ):
        result = runner.invoke(
            app,
            [
                "https://acme.com",
                "--company",
                "Acme Corporation",
                "--job",
                "https://boards.greenhouse.io/acme/jobs/1",
                "--role",
                "cybersecurity",
                "--output",
                str(tmp_path),
            ],
        )
    assert result.exit_code == 0, result.stdout

    [folder] = list(tmp_path.iterdir())
    report = (folder / "report.md").read_text(encoding="utf-8")
    raw = json.loads((folder / "raw.json").read_text(encoding="utf-8"))

    # Each collector's section heading should be present.
    for heading in (
        "## Snapshot",
        "## Web & infrastructure footprint",
        "## Company profile",
        "## Role-fit signals (from JD)",
        "## GitHub presence",
        "## News & timeline",
        "## Breach history",
        "## Business & financial signals",
        "## Mergers & acquisitions",
        "## People",
        "## Questions to ask",
        "## Collection notes",
    ):
        assert heading in report, f"missing section: {heading}"

    # At least one question must fire under cybersec role with the broader template library.
    assert len(raw["questions"]) > 0
```

- [ ] **Step 2: Verify + commit**

```
uv run pytest tests/integration/test_v0_2_end_to_end.py -v
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

Expected: e2e test green; full suite green; ruff/mypy clean.

```
git add tests/integration/test_v0_2_end_to_end.py
git commit -m "$(cat <<'EOF'
test(integration): v0.2.0 e2e through all 9 collectors

CLI -> Orchestrator -> all 9 collectors -> heuristics -> renderers.
Mocks every upstream HTTP/DNS dependency. Asserts every per-collector
section appears in the rendered markdown and that the broader
template library produces at least one question for cybersec role.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Tag v0.2.0 and push

- [ ] **Step 1: Final sweep**

```
uv run pytest -v
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

Expected: all green. Full suite should now be ~120 tests.

- [ ] **Step 2: Tag and push**

```
git tag -a v0.2.0 -m "tradecraft v0.2.0: collector roster complete (8 OSINT sources, ~45 cybersec templates)"
git push origin main
git push origin v0.2.0
gh run list --branch main --limit 1
```

Expected: CI run starts; verify it goes green:

```
gh run watch <run-id> --exit-status
```

If CI fails: investigate and fix. Don't move the tag unless code itself changes — the v0.2.0 tag should land on the green commit. If the tag needs to move (e.g. a CI-only fix is pushed), use the same pattern as v0.1.0a0/a1: delete tag locally, retag at new HEAD, force-push the tag.

- [ ] **Step 3: Verify by running against a real target**

Pick any company with a Wikipedia page and an open-source presence (e.g., `cloudflare.com`):

```
uv run tradecraft https://cloudflare.com --role cybersecurity --output ./demo --no-cache
```

Inspect `demo/cloudflare-<date>/report.md`. Expect:
- Footprint signals (CSP/HSTS posture)
- GitHub section populated (Cloudflare has a large public org)
- Business section showing public-company ticker
- Wikipedia infobox fields
- News timeline
- At least 5 questions in the "Questions to ask" section

If anything looks off, file a follow-up task (don't try to fix mid-tag).

---

## Self-review (run by the engineer / agent after completing all tasks)

- [ ] `uv run pytest -v` passes — expect ~120 tests.
- [ ] `uv run ruff check src tests` clean.
- [ ] `uv run ruff format --check src tests` clean.
- [ ] `uv run mypy src` clean.
- [ ] `uv run tradecraft --help` prints help with the v0.2.0 collector defaults.
- [ ] A real run against a known target produces every section in `report.md`.
- [ ] `raw.json` v1 schema unchanged.
- [ ] CHANGELOG entry mentions every collector + every signal it emits.
- [ ] No `dossiers/` or `demo/` artifacts committed.
- [ ] `git tag` shows both `v0.1.0a0`, `v0.1.0a1`, and `v0.2.0`.

---

## Plan-author self-review

**Spec coverage (against `docs/superpowers/specs/2026-05-23-tradecraft-design.md`):**

- §6.1 footprint — already shipped in v0.1.0a0; no task here.
- §6.2 company → Task 5.
- §6.3 job → Task 6.
- §6.4 news → Task 4.
- §6.5 breaches → Task 2.
- §6.6 github → Task 3.
- §6.7 people → Task 7.
- §6.8 business → Task 8 (RECENT_10K + Glassdoor explicitly deferred).
- §6.9 ma → Task 9 (M_A_RECENT explicitly deferred).
- §7.1 Heuristic analyzer + templates → Task 1 (~30 new templates).
- §7.2 AI analyzer — explicitly out of scope (v0.3.0).
- §8.1 Markdown renderer per-collector sections → Task 11.
- §9 CLI surface — flags unchanged; `_default_collectors()` extended in Task 10.

**Placeholder scan:** no "TBD" / "TODO" / "Similar to Task N" in shipped code. Some deferred features are clearly marked (RECENT_10K, M_A_RECENT, stack-match signals, cross-collector deps) with the reason — those are acknowledged limitations, not placeholders.

**Type consistency:** every new collector class name (`BreachesCollector`, `GitHubCollector`, `NewsCollector`, `CompanyCollector`, `JobCollector`, `PeopleCollector`, `BusinessCollector`, `MaCollector`) is referenced identically in `cli.py` (Task 10), tests, and the integration test (Task 13). Method names follow the `Collector` protocol exactly. Signal names are pulled from the existing `Signal` enum; no new enum values needed.

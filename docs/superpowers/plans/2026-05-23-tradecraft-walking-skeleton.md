# tradecraft — Walking Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working `tradecraft` v0.1.0-alpha CLI that takes a company root URL + optional job listing URL and produces a real interview-prep dossier using one collector (`footprint`) end-to-end, with the full architecture in place to scale to the remaining seven collectors in a follow-up plan.

**Architecture:** Plugin-based async collectors orchestrated by `asyncio.gather`. A `Collector` protocol with `safe_for_hosted` and `role_relevance` metadata. Findings flow into a heuristic analyzer (signal-driven question templates) and renderers (markdown + JSON + standalone questions). Typer CLI. No AI in this plan — that lands in plan 2.

**Tech Stack:** Python 3.11+, `httpx[http2]` (async HTTP + HTTP/2), `dnspython` (DNS), `selectolax` (fast HTML), `typer` + `rich` (CLI/UX), `pydantic` v2 (models + config), `tomli` (config file), `pytest` + `pytest-asyncio` + `respx` (test stack), `hatchling` build backend, `uv` for the dev loop. MIT license. Public repo.

**Scope of this plan (walking skeleton):**

- Repo scaffold (pyproject, CI, lint/type/test config, MIT LICENSE, README skeleton, SECURITY.md, ethics docs)
- Core models (`Target`, `Findings`, `Signal`, `Question`, `CollectorResult`, `CollectorError`)
- Core infra (`config.py`, `cache.py`, `http.py`, `ethics.py`)
- Collector framework (`collectors/base.py`, `orchestrator.py`)
- First collector (`collectors/footprint.py`)
- Heuristic analyzer (`analyzers/templates.py`, `analyzers/heuristics.py`) with ~12 starter templates
- Renderers (`renderers/markdown.py`, `renderers/json.py`, `renderers/questions.py`)
- CLI (`cli.py` via Typer)
- End-to-end integration test
- README polish + v0.1.0-alpha tag

**Out of scope (plan 2 will cover):** `company`, `job`, `news`, `breaches`, `github`, `people`, `business`, `ma` collectors; AI providers (Anthropic, OpenAI, Ollama, OpenAI-compat) and the AI analyzer; hosted web preview (v1.1).

**Spec reference:** `docs/superpowers/specs/2026-05-23-tradecraft-design.md`

---

## Conventions used in every task

- **Test framework:** `pytest`. Async tests via `pytest-asyncio` with `asyncio_mode = "auto"` in `pyproject.toml`.
- **HTTP mocking:** `respx` to record/replay `httpx` interactions. No live network in tests, ever.
- **Run a single test:** `uv run pytest tests/<path>::test_name -v`
- **Run all tests:** `uv run pytest -v`
- **Lint:** `uv run ruff check src tests` (configured strict)
- **Typecheck:** `uv run mypy src`
- **TDD cycle:** write failing test → confirm it fails for the right reason → minimal impl → confirm it passes → refactor if needed → commit
- **Commits:** Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`). One commit per task unless noted.
- **Co-author trailer:** include `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` on every commit.

---

## File map (locked in here so later tasks reference exact paths)

```
tradecraft/
├── .github/workflows/ci.yml
├── .gitignore
├── LICENSE                                          (MIT)
├── README.md
├── SECURITY.md
├── pyproject.toml
├── ruff.toml                                        (or [tool.ruff] in pyproject)
├── docs/
│   ├── ETHICS.md
│   ├── THREAT_MODEL.md
│   ├── superpowers/specs/2026-05-23-tradecraft-design.md  (already committed)
│   └── superpowers/plans/2026-05-23-tradecraft-walking-skeleton.md  (this file)
├── src/tradecraft/
│   ├── __init__.py                                  (__version__)
│   ├── cli.py
│   ├── orchestrator.py
│   ├── http.py
│   ├── cache.py
│   ├── ethics.py
│   ├── config.py
│   ├── models.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── footprint.py
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── heuristics.py
│   │   └── templates.py
│   └── renderers/
│       ├── __init__.py
│       ├── markdown.py
│       ├── json.py
│       └── questions.py
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_models.py
    │   ├── test_config.py
    │   ├── test_cache.py
    │   ├── test_http.py
    │   ├── test_ethics.py
    │   ├── test_orchestrator.py
    │   ├── collectors/
    │   │   ├── test_base.py
    │   │   └── test_footprint.py
    │   ├── analyzers/
    │   │   ├── test_templates.py
    │   │   └── test_heuristics.py
    │   └── renderers/
    │       ├── test_json.py
    │       ├── test_markdown.py
    │       └── test_questions.py
    ├── fixtures/
    │   └── footprint/
    │       ├── crtsh_acme.json
    │       └── acme_root_response.html
    └── integration/
        └── test_end_to_end.py
```

---

## Task 1: Initialize Python project skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/tradecraft/__init__.py`
- Create: `LICENSE`

- [ ] **Step 1: Create `LICENSE`**

Copy the standard MIT license text. Year `2026`, holder `Scott Altiparmak`.

```
MIT License

Copyright (c) 2026 Scott Altiparmak

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Create `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtualenvs
.venv/
venv/
env/

# Testing / typing / lint
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.mypy_cache/
.ruff_cache/

# uv
uv.lock

# Editor / OS
.idea/
.vscode/
.DS_Store
Thumbs.db

# Tradecraft outputs (don't commit user dossiers)
dossiers/
.cache/tradecraft/
```

Note: `uv.lock` is in `.gitignore` deliberately until Task 4 — we will remove it from `.gitignore` and commit the lock once the dev loop stabilises.

- [ ] **Step 3: Create `src/tradecraft/__init__.py`**

```python
"""tradecraft — OSINT tradecraft for the interview chair."""

__version__ = "0.1.0a0"
```

- [ ] **Step 4: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "tradecraft"
dynamic = ["version"]
description = "OSINT tradecraft for the interview chair. A cybersec-first interview-prep CLI."
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
authors = [{ name = "Scott Altiparmak" }]
keywords = ["osint", "cybersecurity", "interview", "recon", "cli"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Information Technology",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Security",
]
dependencies = [
    "httpx[http2]>=0.27",
    "dnspython>=2.6",
    "selectolax>=0.3.21",
    "typer>=0.12",
    "rich>=13.7",
    "pydantic>=2.7",
    "tomli>=2.0;python_version<'3.11'",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "coverage>=7.5",
    "ruff>=0.5",
    "mypy>=1.10",
    "types-requests",
]

[project.scripts]
tradecraft = "tradecraft.cli:app"

[project.urls]
Homepage = "https://github.com/scottaltiparmak/tradecraft"
Repository = "https://github.com/scottaltiparmak/tradecraft"
Issues = "https://github.com/scottaltiparmak/tradecraft/issues"

[tool.hatch.version]
path = "src/tradecraft/__init__.py"

[tool.hatch.build.targets.wheel]
packages = ["src/tradecraft"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra --strict-markers"
markers = [
    "live: hits real network; opt-in via -m live",
]

[tool.mypy]
python_version = "3.11"
strict = true
files = ["src/tradecraft"]
plugins = ["pydantic.mypy"]
```

- [ ] **Step 5: Verify the package installs and imports**

Run:
```bash
uv venv
uv pip install -e ".[dev]"
uv run python -c "import tradecraft; print(tradecraft.__version__)"
```
Expected output: `0.1.0a0`

- [ ] **Step 6: Commit**

```bash
git add LICENSE .gitignore pyproject.toml src/tradecraft/__init__.py
git commit -m "$(cat <<'EOF'
chore: initialize tradecraft Python package

Hatchling build backend, src layout, Python 3.11+ target, MIT license.
Pins core runtime deps (httpx, dnspython, selectolax, typer, rich,
pydantic) and dev deps (pytest, respx, ruff, mypy).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Lint, type, and test configuration

**Files:**
- Create: `ruff.toml`
- Modify: `pyproject.toml` (already has `[tool.mypy]` and `[tool.pytest.ini_options]` from Task 1 — no change needed)
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`

- [ ] **Step 1: Create `ruff.toml`**

```toml
target-version = "py311"
line-length = 100

[lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # bugbear
    "C4",  # comprehensions
    "UP",  # pyupgrade
    "SIM", # simplify
    "RET", # return values
    "PTH", # pathlib
    "ARG", # unused arguments
    "TRY", # exceptions
    "PL",  # pylint subset
    "RUF", # ruff-specific
]
ignore = [
    "E501",   # line length handled by formatter
    "TRY003", # long exception messages are fine
    "PLR2004", # magic value comparisons are fine in tests
]

[lint.per-file-ignores]
"tests/**/*.py" = ["ARG001", "PLR2004", "S101"]

[format]
quote-style = "double"
indent-style = "space"
```

- [ ] **Step 2: Create test package files**

`tests/__init__.py`:
```python
```

`tests/unit/__init__.py`:
```python
```

`tests/integration/__init__.py`:
```python
```

`tests/conftest.py`:
```python
"""Shared pytest fixtures for tradecraft tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to tests/fixtures/."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """Default policy; override per-test if needed."""
    return asyncio.DefaultEventLoopPolicy()
```

- [ ] **Step 3: Run lint and type baseline**

Run:
```bash
uv run ruff check src tests
uv run mypy src
uv run pytest -v
```

Expected: ruff clean, mypy clean (no files yet beyond `__init__.py`), pytest reports `no tests ran`.

- [ ] **Step 4: Commit**

```bash
git add ruff.toml tests/
git commit -m "$(cat <<'EOF'
chore: configure ruff, mypy, and pytest

Strict lint preset (E/W/F/I/B/C4/UP/SIM/RET/PTH/ARG/TRY/PL/RUF),
strict mypy on src/, pytest-asyncio in auto mode, opt-in `live` marker
for network tests.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the CI workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install project
        run: uv sync --all-extras --python ${{ matrix.python-version }}

      - name: Ruff check
        run: uv run ruff check src tests

      - name: Ruff format check
        run: uv run ruff format --check src tests

      - name: Mypy
        run: uv run mypy src

      - name: Pytest
        run: uv run pytest -v --cov=src/tradecraft --cov-report=term-missing
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "$(cat <<'EOF'
ci: add lint + typecheck + test workflow

Runs on push to main and PRs. Matrices Python 3.11/3.12/3.13.
Uses uv for fast, cached installs.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: README skeleton and ethics docs

**Files:**
- Create: `README.md`
- Create: `SECURITY.md`
- Create: `docs/ETHICS.md`
- Create: `docs/THREAT_MODEL.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# tradecraft

> OSINT tradecraft for the interview chair.

`tradecraft` builds an interview-prep dossier on a company from public sources. Cybersecurity-flavored fingerprinting, a structured report, and **evidence-cited questions to ask in the interview** — tagged for cybersec, swe, devops, data, eng-leadership.

Free public sources only. No paid APIs required. Optional AI analysis via your own key (Anthropic, OpenAI, Ollama, or any OpenAI-compatible endpoint).

## Status

**Alpha (v0.1.0a0)** — walking skeleton with the `footprint` collector wired end-to-end. The remaining collectors (company, job, news, breaches, github, people, business, m&a) and the BYOK AI analyzer land in v0.2.0.

## Install

```bash
pipx install tradecraft
# or
uv tool install tradecraft
```

## Usage

```bash
tradecraft https://acme.com --job https://acme.com/careers/sec-eng
```

Outputs `./dossiers/acme-corp-YYYY-MM-DD/` with:
- `report.md` — sectioned dossier
- `questions.md` — questions to ask in the interview
- `raw.json` — full structured findings

See `tradecraft --help` for all flags.

## Intended use

This is **interview preparation tooling**. Use it on companies you are legitimately interviewing with. The tool identifies itself in every request, respects `robots.txt` by default, rate-limits politely, and contains no authentication, paywall, or rate-limit bypass logic. See [`docs/ETHICS.md`](docs/ETHICS.md).

## License

MIT — see [`LICENSE`](LICENSE).
```

- [ ] **Step 2: Create `SECURITY.md`**

```markdown
# Security policy

## Reporting a vulnerability

Email `scottaltiparmak@gmail.com` with the subject `[tradecraft security]`. Please include:

- A clear description of the issue
- Steps to reproduce
- Affected versions
- Any suggested mitigations

I aim to acknowledge within 72 hours and to ship a fix within 14 days for high-severity issues.

## Scope

In scope:

- Code in this repository that could be used to violate ethical/legal boundaries (e.g., a collector that silently scrapes against ToS)
- Vulnerabilities in dependencies that affect users of the CLI
- Issues with the BYOK AI flow that could leak user keys

Out of scope:

- The tool's intended OSINT behaviors (DNS lookups, certificate transparency searches, etc. — these are by design)
- Issues that require physical access to a user's machine
```

- [ ] **Step 3: Create `docs/ETHICS.md`**

```markdown
# Ethics & intended use

`tradecraft` exists to help candidates prepare for interviews by structuring publicly available information about the company they are interviewing with. It is not a red-team tool, not a continuous monitoring service, and not a bulk OSINT framework.

## Hard rules baked into the codebase

- **Identifying User-Agent.** Every HTTP request goes out as `tradecraft/<version> (+https://github.com/<owner>/tradecraft) interview-prep`. Server operators can block trivially.
- **`robots.txt` respected by default.** Bypassing requires two flags (`--ignore-robots --i-know-what-im-doing`) and prints a warning.
- **Per-host rate limit.** Default 1 req/sec/host, max 5 concurrent total. Configurable downward, not upward by default.
- **No authentication bypass, no paywall bypass, no credential probing.** Ever. PRs that add these will be rejected.
- **No bulk targeting.** The CLI accepts a single target per invocation. There is no batch mode.
- **No individual-person OSINT.** A heuristic refuses inputs that look like person names rather than companies.
- **Hosted preview is deliberately narrower than the CLI.** Server-side collectors are restricted to sources that explicitly permit programmatic access.

## What this tool will not do

- LinkedIn, Facebook, or other social-network scraping
- Active scanning (port scans, dirbusting, fuzzing)
- Email enumeration or pivot to individuals from breach data
- Dynamic/headless browser rendering (Playwright / Selenium)

## What you, the user, should not do with it

- Don't point it at companies you are not legitimately interviewing with.
- Don't aggregate dossiers across many targets to build a mailing list.
- Don't share dossiers that contain personal data without consent.

If a use case feels like it's stretching these limits, it probably is.
```

- [ ] **Step 4: Create `docs/THREAT_MODEL.md`**

```markdown
# Threat model

## Assets

1. **End-user OSINT operations.** The tool runs on the user's machine using their IP. The user is responsible for compliance with applicable law and site terms.
2. **Third-party services we hit.** crt.sh, public DNS resolvers, the target's own website. We owe them politeness.
3. **(Hosted only) The operator's server reputation.** A shared hosted IP gets blocked quickly if the tool misbehaves.
4. **(BYOK AI flows) User API keys.** Must never be logged, written to disk, or transmitted to anyone except the configured provider.

## Threats considered

| Threat | Mitigation |
|---|---|
| User tries to scrape a target aggressively | Per-host rate limit, no bulk mode, single-target CLI surface |
| Hostile target returns a 5 GB HTML response | `max_response_bytes` cap in `http.py` (default 5 MB) |
| Hostile target redirects to localhost / internal IPs | `http.py` denies redirects to private IP ranges |
| `robots.txt` blocks our collector | We respect it by default; bypass requires two explicit flags |
| AI key leaks via logs | Provider adapters never log the key; CLI never echoes env vars |
| Hosted operator runs unsafe collectors | Per-collector `safe_for_hosted` flag; orchestrator enforces in hosted mode |
| Tool used for individual-person OSINT | Input guard heuristic refuses person-like inputs |

## Not in the threat model (intentionally)

- Compromise of the user's machine (out of scope)
- Targeted attacks against tradecraft itself (low value)
- Censorship / circumvention scenarios (not the product)
```

- [ ] **Step 5: Commit**

```bash
git add README.md SECURITY.md docs/ETHICS.md docs/THREAT_MODEL.md
git commit -m "$(cat <<'EOF'
docs: README, SECURITY, ETHICS, THREAT_MODEL

README sets product positioning (cybersec-first, free-tier OSINT,
evidence-cited interview questions). ETHICS makes the in-codebase
hard rules visible. THREAT_MODEL enumerates what the tool defends
against and what's intentionally out of scope.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Core models

**Files:**
- Create: `src/tradecraft/models.py`
- Create: `tests/unit/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_models.py`:
```python
"""Tests for tradecraft.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Findings,
    Question,
    Role,
    Signal,
    Target,
)


class TestTarget:
    def test_minimal_target(self) -> None:
        t = Target(company_name="Acme", root_url="https://acme.com")
        assert t.company_name == "Acme"
        assert str(t.root_url) == "https://acme.com/"
        assert t.job_url is None
        assert t.role == Role.CYBERSECURITY

    def test_target_with_job_and_role(self) -> None:
        t = Target(
            company_name="Acme",
            root_url="https://acme.com",
            job_url="https://acme.com/jobs/1",
            role=Role.SWE,
        )
        assert str(t.job_url) == "https://acme.com/jobs/1"
        assert t.role == Role.SWE

    def test_target_rejects_non_url(self) -> None:
        with pytest.raises(ValidationError):
            Target(company_name="Acme", root_url="not-a-url")

    def test_target_company_slug(self) -> None:
        t = Target(company_name="Acme Corp, Inc.", root_url="https://acme.com")
        assert t.company_slug == "acme-corp-inc"


class TestSignal:
    def test_signal_is_enum(self) -> None:
        assert Signal.M_A_RECENT.value == "m_a_recent"
        assert Signal.MISSING_CSP.value == "missing_csp"


class TestQuestion:
    def test_question_minimal(self) -> None:
        q = Question(
            text="Why?",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
        )
        assert q.confidence == "high"
        assert q.is_starred is False

    def test_question_starred_flag(self) -> None:
        q = Question(
            text="Why?",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=True,
        )
        assert q.is_starred is True


class TestCollectorResult:
    def test_result_with_data(self) -> None:
        r = CollectorResult(
            name="footprint",
            data={"subdomains": ["a.acme.com"]},
            signals=[Signal.OPEN_STAGING_SUBDOMAIN],
            errors=[],
            duration_ms=42,
        )
        assert r.signals == [Signal.OPEN_STAGING_SUBDOMAIN]
        assert r.duration_ms == 42

    def test_result_with_error(self) -> None:
        err = CollectorError(stage="dns", message="timeout")
        r = CollectorResult(
            name="footprint", data={}, signals=[], errors=[err], duration_ms=10
        )
        assert r.errors[0].stage == "dns"


class TestFindings:
    def test_findings_collects_results(self) -> None:
        target = Target(company_name="Acme", root_url="https://acme.com")
        r1 = CollectorResult(
            name="footprint", data={}, signals=[Signal.MISSING_CSP], errors=[], duration_ms=10
        )
        f = Findings(target=target, results=[r1])
        assert Signal.MISSING_CSP in f.all_signals
        assert f.collector("footprint") is r1
        assert f.collector("nope") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run pytest tests/unit/test_models.py -v
```
Expected: ImportError / ModuleNotFoundError on `tradecraft.models`.

- [ ] **Step 3: Implement `src/tradecraft/models.py`**

```python
"""Core data models for tradecraft."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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


def _slugify(value: str) -> str:
    return _SLUG_RE.sub("-", value.lower()).strip("-")


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
    evidence_signal: Signal
    source_collector: str
    is_starred: bool = False


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


class Findings(BaseModel):
    target: Target
    results: list[CollectorResult] = Field(default_factory=list)
    schema_version: int = 1

    @property
    def all_signals(self) -> set[Signal]:
        return {s for r in self.results for s in r.signals}

    def collector(self, name: str) -> CollectorResult | None:
        return next((r for r in self.results if r.name == name), None)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_models.py -v
uv run ruff check src/tradecraft/models.py tests/unit/test_models.py
uv run mypy src/tradecraft/models.py
```
Expected: all tests pass, lint clean, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/models.py tests/unit/test_models.py
git commit -m "$(cat <<'EOF'
feat: core models (Target, Findings, Signal, Question, CollectorResult)

Pydantic v2 models with frozen Target. Signal is a StrEnum covering
every signal the eight v1 collectors will emit (declared upfront so
collectors can be added without re-touching this file). Findings
aggregates collector results and exposes a derived all_signals set
used by the heuristic analyzer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Config loader

**Files:**
- Create: `src/tradecraft/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_config.py`:
```python
"""Tests for tradecraft.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from tradecraft.config import AppConfig, load_config


def test_default_config_has_sensible_values() -> None:
    cfg = AppConfig()
    assert cfg.http.per_host_rps == 1.0
    assert cfg.http.global_concurrency == 5
    assert cfg.http.max_response_bytes == 5 * 1024 * 1024
    assert cfg.cache.enabled is True
    assert cfg.cache.ttl_default_seconds == 3600


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: ImportError on `tradecraft.config`.

- [ ] **Step 3: Implement `src/tradecraft/config.py`**

```python
"""Config loader: TOML file + env var overrides."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

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


def _coerce(value: str, target_type: type) -> Any:
    if target_type is bool:
        return value.lower() in {"1", "true", "yes", "on"}
    if target_type is int:
        return int(value)
    if target_type is float:
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
    return Path.home() / ".config" / "tradecraft" / "config.toml"
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/test_config.py -v
uv run ruff check src/tradecraft/config.py tests/unit/test_config.py
uv run mypy src/tradecraft/config.py
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/config.py tests/unit/test_config.py
git commit -m "$(cat <<'EOF'
feat: AppConfig with TOML file + env var overrides

Pydantic models for http/cache config sections, defaults chosen
conservative (1 rps per host, 5 concurrent, 5 MB response cap,
1 h cache TTL). TRADECRAFT_<SECTION>_<KEY> env vars override
file values for CI-friendly tweaks.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Filesystem cache

**Files:**
- Create: `src/tradecraft/cache.py`
- Create: `tests/unit/test_cache.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_cache.py`:
```python
"""Tests for tradecraft.cache."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from tradecraft.cache import Cache


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(directory=tmp_path, default_ttl=60)


def test_set_then_get_returns_value(cache: Cache) -> None:
    cache.set("k", b"hello")
    assert cache.get("k") == b"hello"


def test_get_missing_returns_none(cache: Cache) -> None:
    assert cache.get("nope") is None


def test_expired_entry_returns_none(tmp_path: Path) -> None:
    cache = Cache(directory=tmp_path, default_ttl=0)
    cache.set("k", b"x")
    # ttl=0 means already expired
    assert cache.get("k") is None


def test_per_call_ttl_overrides_default(tmp_path: Path) -> None:
    cache = Cache(directory=tmp_path, default_ttl=0)
    cache.set("k", b"x", ttl=3600)
    assert cache.get("k") == b"x"


def test_disabled_cache_is_noop(tmp_path: Path) -> None:
    cache = Cache(directory=tmp_path, default_ttl=60, enabled=False)
    cache.set("k", b"x")
    assert cache.get("k") is None


def test_clear_wipes_entries(cache: Cache) -> None:
    cache.set("k1", b"x")
    cache.set("k2", b"y")
    cache.clear()
    assert cache.get("k1") is None
    assert cache.get("k2") is None


def test_key_with_path_separators_is_safe(cache: Cache) -> None:
    cache.set("https://example.com/path?q=1", b"safe")
    assert cache.get("https://example.com/path?q=1") == b"safe"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cache.py -v`
Expected: ImportError on `tradecraft.cache`.

- [ ] **Step 3: Implement `src/tradecraft/cache.py`**

```python
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
        except (OSError, json.JSONDecodeError):
            return None
        expires_at = envelope.get("expires_at", 0)
        if time.time() >= expires_at:
            return None
        payload_hex = envelope.get("payload_hex")
        if not isinstance(payload_hex, str):
            return None
        try:
            return bytes.fromhex(payload_hex)
        except ValueError:
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
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/test_cache.py -v
uv run ruff check src/tradecraft/cache.py tests/unit/test_cache.py
uv run mypy src/tradecraft/cache.py
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/cache.py tests/unit/test_cache.py
git commit -m "$(cat <<'EOF'
feat: filesystem cache with per-entry TTL

SHA-256-derived 2-level fan-out for filesystem-friendly keys.
JSON envelope with expires_at + hex-encoded payload. Disabled
mode is a true no-op so tests and the --no-cache flag can
exercise the un-cached path.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: HTTP client with polite UA, rate limit, retry, cache integration

**Files:**
- Create: `src/tradecraft/http.py`
- Create: `tests/unit/test_http.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_http.py`:
```python
"""Tests for tradecraft.http (HttpClient)."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx
import pytest
import respx

from tradecraft import __version__
from tradecraft.cache import Cache
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(directory=tmp_path, default_ttl=60)


@pytest.fixture
def cfg() -> HttpConfig:
    return HttpConfig(
        per_host_rps=100.0,  # disable for most tests
        global_concurrency=5,
        max_response_bytes=10_000,
        request_timeout_seconds=5.0,
        max_retries=2,
    )


@pytest.fixture
async def client(cfg: HttpConfig, cache: Cache):
    async with HttpClient(cfg, cache) as c:
        yield c


@respx.mock
async def test_get_returns_response(client: HttpClient) -> None:
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="hello")
    )
    resp = await client.get("https://example.com/")
    assert resp.status_code == 200
    assert resp.text == "hello"


@respx.mock
async def test_user_agent_is_identifying(client: HttpClient) -> None:
    route = respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="ok")
    )
    await client.get("https://example.com/")
    ua = route.calls[0].request.headers["user-agent"]
    assert "tradecraft" in ua
    assert __version__ in ua
    assert "interview-prep" in ua


@respx.mock
async def test_response_served_from_cache_on_second_call(client: HttpClient) -> None:
    route = respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="hello", headers={"content-type": "text/plain"})
    )
    r1 = await client.get("https://example.com/")
    r2 = await client.get("https://example.com/")
    assert r1.text == r2.text == "hello"
    assert route.call_count == 1


@respx.mock
async def test_oversized_response_raises(cfg: HttpConfig, cache: Cache) -> None:
    big = "x" * 20_000
    respx.get("https://example.com/").mock(return_value=httpx.Response(200, text=big))
    async with HttpClient(cfg, cache) as client:
        with pytest.raises(ValueError, match="response too large"):
            await client.get("https://example.com/")


@respx.mock
async def test_retries_on_5xx_then_succeeds(client: HttpClient) -> None:
    route = respx.get("https://example.com/").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, text="recovered"),
        ]
    )
    resp = await client.get("https://example.com/")
    assert resp.text == "recovered"
    assert route.call_count == 2


@respx.mock
async def test_redirect_to_private_ip_is_blocked(cfg: HttpConfig, cache: Cache) -> None:
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(302, headers={"location": "http://127.0.0.1/"})
    )
    async with HttpClient(cfg, cache) as client:
        with pytest.raises(ValueError, match="private"):
            await client.get("https://example.com/")


async def test_per_host_rate_limit_enforced(cache: Cache) -> None:
    cfg = HttpConfig(per_host_rps=2.0, global_concurrency=5, max_response_bytes=10_000)
    async with respx.mock(assert_all_called=False) as mock:
        mock.get("https://example.com/").mock(return_value=httpx.Response(200, text="ok"))
        async with HttpClient(cfg, cache) as client:
            start = time.monotonic()
            await asyncio.gather(*(client.get("https://example.com/") for _ in range(3)))
            elapsed = time.monotonic() - start
        # 3 requests at 2 rps => at least one ~0.5s wait => total >= 0.5s
        assert elapsed >= 0.4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_http.py -v`
Expected: ImportError on `tradecraft.http`.

- [ ] **Step 3: Implement `src/tradecraft/http.py`**

```python
"""Async HTTP client with polite UA, per-host rate limit, retry, and caching."""

from __future__ import annotations

import asyncio
import ipaddress
import time
from collections import defaultdict
from types import TracebackType
from urllib.parse import urlparse

import httpx

from tradecraft import __version__
from tradecraft.cache import Cache
from tradecraft.config import HttpConfig


def _user_agent() -> str:
    return (
        f"tradecraft/{__version__} "
        "(+https://github.com/scottaltiparmak/tradecraft) interview-prep"
    )


def _is_private_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host.lower() in {"localhost", "localhost.localdomain"}
    return ip.is_private or ip.is_loopback or ip.is_link_local


class _TokenBucket:
    """Simple per-host token bucket. Acquire blocks until a token is available."""

    def __init__(self, rate_per_second: float) -> None:
        self.rate = rate_per_second
        self.tokens = rate_per_second
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
                self.last_refill = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait)


class HttpClient:
    """httpx wrapper enforcing the project's hard rules."""

    def __init__(self, config: HttpConfig, cache: Cache) -> None:
        self.config = config
        self.cache = cache
        self._buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(config.per_host_rps)
        )
        self._sem = asyncio.Semaphore(config.global_concurrency)
        self._client = httpx.AsyncClient(
            http2=True,
            follow_redirects=False,
            timeout=config.request_timeout_seconds,
            headers={"User-Agent": _user_agent()},
        )

    async def __aenter__(self) -> "HttpClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def get(self, url: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
        cache_key = f"GET {url}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return httpx.Response(200, content=cached, request=httpx.Request("GET", url))

        host = urlparse(url).hostname or ""
        if _is_private_host(host):
            raise ValueError(f"refusing to fetch private host: {host}")

        bucket = self._buckets[host]
        async with self._sem:
            return await self._do_get_with_retry(url, headers, bucket, cache_key)

    async def _do_get_with_retry(
        self,
        url: str,
        headers: dict[str, str] | None,
        bucket: _TokenBucket,
        cache_key: str,
    ) -> httpx.Response:
        attempt = 0
        while True:
            await bucket.acquire()
            try:
                response = await self._client.get(url, headers=headers)
            except httpx.HTTPError as exc:
                if attempt >= self.config.max_retries:
                    raise
                attempt += 1
                await asyncio.sleep(self._backoff(attempt))
                continue

            if response.is_redirect:
                location = response.headers.get("location", "")
                target_host = urlparse(location).hostname or ""
                if _is_private_host(target_host):
                    raise ValueError(f"redirect to private host blocked: {target_host}")
                if attempt >= self.config.max_retries:
                    return response
                attempt += 1
                url = location
                continue

            if response.status_code >= 500 and attempt < self.config.max_retries:
                attempt += 1
                retry_after = response.headers.get("retry-after")
                wait = float(retry_after) if retry_after else self._backoff(attempt)
                await asyncio.sleep(wait)
                continue

            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > self.config.max_response_bytes:
                raise ValueError(
                    f"response too large: {content_length} > {self.config.max_response_bytes}"
                )
            if len(response.content) > self.config.max_response_bytes:
                raise ValueError(
                    f"response too large: {len(response.content)} > {self.config.max_response_bytes}"
                )

            self.cache.set(cache_key, response.content)
            return response

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(2 ** (attempt - 1), 8.0)
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/test_http.py -v
uv run ruff check src/tradecraft/http.py tests/unit/test_http.py
uv run mypy src/tradecraft/http.py
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/http.py tests/unit/test_http.py
git commit -m "$(cat <<'EOF'
feat: HttpClient with polite UA, per-host token bucket, retries

Async httpx wrapper that enforces the codebase's hard rules:
identifying User-Agent, per-host token-bucket rate limit, global
concurrency cap, response size cap, retry on 5xx with backoff
that honors Retry-After, redirect-to-private-IP blocked. Responses
are cached via the Cache from Task 7 on the GET path.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Ethics module (robots.txt + intended-use guard)

**Files:**
- Create: `src/tradecraft/ethics.py`
- Create: `tests/unit/test_ethics.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_ethics.py`:
```python
"""Tests for tradecraft.ethics."""

from __future__ import annotations

import pytest

from tradecraft.ethics import (
    RobotsPolicy,
    is_likely_person_name,
    parse_robots,
)


def test_parse_robots_basic_disallow() -> None:
    robots_txt = """
    User-agent: *
    Disallow: /admin/
    Disallow: /private
    """
    policy = parse_robots(robots_txt)
    assert policy.is_allowed("/admin/") is False
    assert policy.is_allowed("/admin/users") is False
    assert policy.is_allowed("/public") is True
    assert policy.is_allowed("/private") is False


def test_parse_robots_allow_overrides_disallow() -> None:
    robots_txt = """
    User-agent: *
    Disallow: /
    Allow: /api/
    """
    policy = parse_robots(robots_txt)
    assert policy.is_allowed("/anything") is False
    assert policy.is_allowed("/api/foo") is True


def test_parse_empty_or_missing_robots_allows_all() -> None:
    assert parse_robots("").is_allowed("/anything") is True


def test_specific_user_agent_section_takes_precedence() -> None:
    robots_txt = """
    User-agent: *
    Disallow: /everywhere

    User-agent: tradecraft
    Disallow: /tradecraft-only
    """
    policy = parse_robots(robots_txt, user_agent="tradecraft")
    # tradecraft-specific section: /tradecraft-only disallowed, but /everywhere allowed
    assert policy.is_allowed("/tradecraft-only") is False
    assert policy.is_allowed("/everywhere") is True


@pytest.mark.parametrize(
    "name,expected",
    [
        ("John Smith", True),
        ("Mary Jane Watson", True),
        ("Acme Corp", False),
        ("Acme", False),
        ("OpenAI", False),
        ("Anthropic", False),
        ("Bill Gates Foundation", False),  # contains a company word
    ],
)
def test_is_likely_person_name(name: str, expected: bool) -> None:
    assert is_likely_person_name(name) is expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_ethics.py -v`
Expected: ImportError on `tradecraft.ethics`.

- [ ] **Step 3: Implement `src/tradecraft/ethics.py`**

```python
"""Ethics: robots.txt parsing and intended-use guard."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RobotsPolicy:
    allows: list[str] = field(default_factory=list)
    disallows: list[str] = field(default_factory=list)

    def is_allowed(self, path: str) -> bool:
        # Longest-match wins; Allow beats Disallow on tie.
        best_len = -1
        best_allow = True
        for prefix in self.allows:
            if path.startswith(prefix) and len(prefix) > best_len:
                best_len = len(prefix)
                best_allow = True
        for prefix in self.disallows:
            if path.startswith(prefix) and len(prefix) >= best_len:
                # >= so Allow wins ties only when strictly longer.
                # Equal-length: Disallow wins per RFC 9309 ambiguity; we choose to
                # let Allow win when it appeared with the same prefix length first.
                if len(prefix) > best_len:
                    best_len = len(prefix)
                    best_allow = False
                elif not best_allow:
                    best_allow = False
        return best_allow


def parse_robots(robots_txt: str, user_agent: str = "*") -> RobotsPolicy:
    """Parse a robots.txt body and return the policy for the given UA.

    If the UA has a specific section, ONLY that section applies (per RFC 9309).
    Otherwise, the `*` wildcard section applies.
    """
    sections: dict[str, RobotsPolicy] = {}
    current_uas: list[str] = []
    for raw_line in robots_txt.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            ua = value.lower()
            current_uas = [ua]
            sections.setdefault(ua, RobotsPolicy())
        elif key in {"disallow", "allow"} and current_uas:
            for ua in current_uas:
                policy = sections.setdefault(ua, RobotsPolicy())
                if value:  # empty Disallow means "allow all", skip
                    if key == "disallow":
                        policy.disallows.append(value)
                    else:
                        policy.allows.append(value)

    ua_key = user_agent.lower()
    if ua_key in sections:
        return sections[ua_key]
    return sections.get("*", RobotsPolicy())


_COMPANY_HINTS = re.compile(
    r"\b(corp|corporation|inc|llc|ltd|gmbh|holdings|group|labs|systems|"
    r"technologies|solutions|software|ai|cloud|networks|security|"
    r"foundation|industries|partners|capital|ventures)\b",
    re.IGNORECASE,
)
_PERSON_RE = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$")


def is_likely_person_name(value: str) -> bool:
    """Heuristic: refuses inputs that look like an individual's name.

    Pattern: 2-4 capitalized tokens, no company-suffix words, no digits.
    """
    value = value.strip()
    if _COMPANY_HINTS.search(value):
        return False
    if any(ch.isdigit() for ch in value):
        return False
    return bool(_PERSON_RE.match(value))
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/test_ethics.py -v
uv run ruff check src/tradecraft/ethics.py tests/unit/test_ethics.py
uv run mypy src/tradecraft/ethics.py
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/ethics.py tests/unit/test_ethics.py
git commit -m "$(cat <<'EOF'
feat: ethics module (robots.txt parsing + person-name guard)

RobotsPolicy supports longest-prefix-match with Allow > Disallow
on ties. parse_robots() honors UA-specific sections per RFC 9309.
is_likely_person_name() lets the CLI refuse individual-person OSINT
inputs (rejects 2-4 capitalized tokens with no company suffix).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Collector protocol and base helpers

**Files:**
- Create: `src/tradecraft/collectors/__init__.py`
- Create: `src/tradecraft/collectors/base.py`
- Create: `tests/unit/collectors/__init__.py`
- Create: `tests/unit/collectors/test_base.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/collectors/__init__.py`:
```python
```

`tests/unit/collectors/test_base.py`:
```python
"""Tests for tradecraft.collectors.base."""

from __future__ import annotations

import pytest

from tradecraft.collectors.base import (
    Collector,
    CollectorContext,
    timed_run,
)
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
    Target,
)


class FakeCollector(Collector):
    name = "fake"
    requires_network = False
    safe_for_hosted = True
    role_relevance = {Role.GENERIC}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        return CollectorResult(
            name=self.name,
            data={"ok": True},
            signals=[Signal.MISSING_CSP],
            errors=[],
            duration_ms=0,
        )


async def test_collector_runs() -> None:
    c = FakeCollector()
    ctx = CollectorContext(
        target=Target(company_name="Acme", root_url="https://acme.com"),
        http=None,  # type: ignore[arg-type]
        cache=None,  # type: ignore[arg-type]
    )
    result = await c.run(ctx)
    assert result.name == "fake"
    assert Signal.MISSING_CSP in result.signals


async def test_timed_run_records_duration_and_catches_errors() -> None:
    class Broken(Collector):
        name = "broken"
        requires_network = False
        safe_for_hosted = True
        role_relevance = {Role.GENERIC}

        async def run(self, ctx: CollectorContext) -> CollectorResult:
            raise RuntimeError("boom")

    ctx = CollectorContext(
        target=Target(company_name="Acme", root_url="https://acme.com"),
        http=None,  # type: ignore[arg-type]
        cache=None,  # type: ignore[arg-type]
    )
    result = await timed_run(Broken(), ctx)
    assert result.name == "broken"
    assert result.errors
    assert result.errors[0].message == "boom"
    assert result.duration_ms >= 0


async def test_timed_run_overrides_returned_duration() -> None:
    class Liar(Collector):
        name = "liar"
        requires_network = False
        safe_for_hosted = True
        role_relevance = {Role.GENERIC}

        async def run(self, ctx: CollectorContext) -> CollectorResult:
            return CollectorResult(
                name=self.name, data={}, signals=[], errors=[], duration_ms=99999
            )

    ctx = CollectorContext(
        target=Target(company_name="Acme", root_url="https://acme.com"),
        http=None,  # type: ignore[arg-type]
        cache=None,  # type: ignore[arg-type]
    )
    result = await timed_run(Liar(), ctx)
    assert result.duration_ms < 99999
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/collectors/test_base.py -v`
Expected: ImportError on `tradecraft.collectors.base`.

- [ ] **Step 3: Implement the collector framework**

`src/tradecraft/collectors/__init__.py`:
```python
"""Collector plugins."""

from tradecraft.collectors.base import Collector, CollectorContext, timed_run

__all__ = ["Collector", "CollectorContext", "timed_run"]
```

`src/tradecraft/collectors/base.py`:
```python
"""Collector protocol + helpers."""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

from tradecraft.cache import Cache
from tradecraft.http import HttpClient
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Target,
)


@dataclass(frozen=True)
class CollectorContext:
    target: Target
    http: HttpClient
    cache: Cache


@runtime_checkable
class Collector(Protocol):
    """The plugin protocol every OSINT module implements."""

    name: ClassVar[str]
    requires_network: ClassVar[bool]
    safe_for_hosted: ClassVar[bool]
    role_relevance: ClassVar[set[Role]]

    async def run(self, ctx: CollectorContext) -> CollectorResult: ...


async def timed_run(collector: Collector, ctx: CollectorContext) -> CollectorResult:
    """Run a collector with timing + exception containment.

    Always returns a CollectorResult; never raises. If the collector raises,
    its name is preserved and the error is recorded in `errors`.
    """
    start = time.perf_counter()
    try:
        result = await collector.run(ctx)
    except Exception as exc:  # noqa: BLE001 — intentional containment
        duration_ms = int((time.perf_counter() - start) * 1000)
        return CollectorResult(
            name=collector.name,
            data={},
            signals=[],
            errors=[
                CollectorError(
                    stage="run",
                    message=str(exc) or exc.__class__.__name__,
                    exception_type=exc.__class__.__name__,
                )
            ],
            duration_ms=duration_ms,
        )
    duration_ms = int((time.perf_counter() - start) * 1000)
    return result.model_copy(update={"duration_ms": duration_ms})
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/collectors/test_base.py -v
uv run ruff check src/tradecraft/collectors/ tests/unit/collectors/
uv run mypy src/tradecraft/collectors/
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/collectors/ tests/unit/collectors/__init__.py tests/unit/collectors/test_base.py
git commit -m "$(cat <<'EOF'
feat: Collector protocol + timed_run helper

Frozen CollectorContext bundles target/http/cache. Collector is a
runtime-checkable Protocol with class-var metadata (name,
requires_network, safe_for_hosted, role_relevance) so orchestrator
and hosted-mode gating can introspect without instantiating.
timed_run() guarantees a CollectorResult and contains exceptions.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Orchestrator

**Files:**
- Create: `src/tradecraft/orchestrator.py`
- Create: `tests/unit/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_orchestrator.py`:
```python
"""Tests for tradecraft.orchestrator."""

from __future__ import annotations

from typing import ClassVar
from pathlib import Path

import pytest

from tradecraft.cache import Cache
from tradecraft.collectors.base import Collector, CollectorContext
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import (
    CollectorResult,
    Findings,
    Role,
    Signal,
    Target,
)
from tradecraft.orchestrator import Orchestrator


class Footprint(Collector):
    name: ClassVar[str] = "footprint"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY, Role.SWE}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        return CollectorResult(
            name=self.name,
            data={"host": ctx.target.root_url.host},
            signals=[Signal.MISSING_CSP],
            errors=[],
            duration_ms=0,
        )


class News(Collector):
    name: ClassVar[str] = "news"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = False
    role_relevance: ClassVar[set[Role]] = {Role.GENERIC}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        return CollectorResult(
            name=self.name, data={"items": []}, signals=[], errors=[], duration_ms=0
        )


class Broken(Collector):
    name: ClassVar[str] = "broken"
    requires_network: ClassVar[bool] = False
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.GENERIC}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        raise RuntimeError("boom")


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache) as c:
        yield c, cache


async def test_runs_all_collectors_concurrently(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), News()], http=client, cache=cache)
    findings = await orch.run(target)
    assert isinstance(findings, Findings)
    names = {r.name for r in findings.results}
    assert names == {"footprint", "news"}


async def test_hosted_mode_skips_unsafe_collectors(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), News()], http=client, cache=cache)
    findings = await orch.run(target, hosted=True)
    assert {r.name for r in findings.results} == {"footprint"}


async def test_only_filter_runs_just_those(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), News()], http=client, cache=cache)
    findings = await orch.run(target, only={"news"})
    assert {r.name for r in findings.results} == {"news"}


async def test_skip_filter_excludes_those(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), News()], http=client, cache=cache)
    findings = await orch.run(target, skip={"footprint"})
    assert {r.name for r in findings.results} == {"news"}


async def test_one_broken_collector_does_not_kill_run(http) -> None:
    client, cache = http
    target = Target(company_name="Acme", root_url="https://acme.com")
    orch = Orchestrator(collectors=[Footprint(), Broken()], http=client, cache=cache)
    findings = await orch.run(target)
    assert {r.name for r in findings.results} == {"footprint", "broken"}
    broken_result = findings.collector("broken")
    assert broken_result is not None
    assert broken_result.errors
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_orchestrator.py -v`
Expected: ImportError on `tradecraft.orchestrator`.

- [ ] **Step 3: Implement `src/tradecraft/orchestrator.py`**

```python
"""Orchestrator: run collectors concurrently and aggregate findings."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from tradecraft.cache import Cache
from tradecraft.collectors.base import Collector, CollectorContext, timed_run
from tradecraft.http import HttpClient
from tradecraft.models import Findings, Target


class Orchestrator:
    def __init__(
        self,
        collectors: Iterable[Collector],
        http: HttpClient,
        cache: Cache,
    ) -> None:
        self.collectors: list[Collector] = list(collectors)
        self.http = http
        self.cache = cache

    async def run(
        self,
        target: Target,
        *,
        hosted: bool = False,
        only: set[str] | None = None,
        skip: set[str] | None = None,
    ) -> Findings:
        active = self._select(hosted=hosted, only=only, skip=skip)
        ctx = CollectorContext(target=target, http=self.http, cache=self.cache)
        results = await asyncio.gather(*(timed_run(c, ctx) for c in active))
        return Findings(target=target, results=list(results))

    def _select(
        self,
        *,
        hosted: bool,
        only: set[str] | None,
        skip: set[str] | None,
    ) -> list[Collector]:
        result: list[Collector] = []
        for c in self.collectors:
            if hosted and not c.safe_for_hosted:
                continue
            if only is not None and c.name not in only:
                continue
            if skip is not None and c.name in skip:
                continue
            result.append(c)
        return result
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/test_orchestrator.py -v
uv run ruff check src/tradecraft/orchestrator.py tests/unit/test_orchestrator.py
uv run mypy src/tradecraft/orchestrator.py
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/orchestrator.py tests/unit/test_orchestrator.py
git commit -m "$(cat <<'EOF'
feat: Orchestrator (asyncio.gather + hosted gate + only/skip)

Runs collectors concurrently via timed_run for exception containment.
Hosted mode filters by safe_for_hosted; --only and --skip filters
operate by collector name. Returns a Findings aggregate.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Footprint collector

**Files:**
- Create: `src/tradecraft/collectors/footprint.py`
- Create: `tests/unit/collectors/test_footprint.py`
- Create: `tests/fixtures/footprint/crtsh_acme.json`
- Create: `tests/fixtures/footprint/acme_root_headers.json`

This collector covers: DNS lookups, subdomain enumeration via crt.sh, root-page HTTP headers + security headers, sitemap/robots summarization. (TLS chain inspection is deferred — it requires direct socket work that isn't worth adding before we have the other collectors driving real demand.)

- [ ] **Step 1: Create fixture files**

`tests/fixtures/footprint/crtsh_acme.json`:
```json
[
    {"name_value": "acme.com"},
    {"name_value": "www.acme.com"},
    {"name_value": "api.acme.com\nstaging.acme.com"},
    {"name_value": "*.acme.com"}
]
```

`tests/fixtures/footprint/acme_root_headers.json`:
```json
{
    "server": "nginx",
    "x-powered-by": "Next.js",
    "strict-transport-security": "max-age=63072000",
    "x-frame-options": "DENY"
}
```

(No CSP header in the fixture — drives the MISSING_CSP signal.)

- [ ] **Step 2: Write the failing test**

`tests/unit/collectors/test_footprint.py`:
```python
"""Tests for tradecraft.collectors.footprint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from tradecraft.cache import Cache
from tradecraft.collectors.base import CollectorContext
from tradecraft.collectors.footprint import FootprintCollector
from tradecraft.config import HttpConfig
from tradecraft.http import HttpClient
from tradecraft.models import Role, Signal, Target


@pytest.fixture
def fixtures(fixtures_dir: Path) -> dict[str, object]:
    crtsh = json.loads((fixtures_dir / "footprint" / "crtsh_acme.json").read_text())
    headers = json.loads((fixtures_dir / "footprint" / "acme_root_headers.json").read_text())
    return {"crtsh": crtsh, "headers": headers}


@pytest.fixture
async def http(tmp_path: Path):
    cache = Cache(directory=tmp_path, default_ttl=60)
    async with HttpClient(HttpConfig(), cache) as c:
        yield c, cache


def test_collector_metadata_is_correct() -> None:
    c = FootprintCollector()
    assert c.name == "footprint"
    assert c.safe_for_hosted is True
    assert Role.CYBERSECURITY in c.role_relevance


@respx.mock
async def test_runs_and_emits_signals(http, fixtures) -> None:
    client, cache = http
    respx.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=fixtures["crtsh"])
    )
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=fixtures["headers"])
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    # Replace the DNS lookup with a noop for the test.
    monkey_dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    assert result.name == "footprint"
    assert Signal.MISSING_CSP in result.signals
    assert Signal.OPEN_STAGING_SUBDOMAIN in result.signals
    subdomains = result.data["subdomains"]
    assert "staging.acme.com" in subdomains  # type: ignore[operator]
    assert "*.acme.com" not in subdomains  # type: ignore[operator]


@respx.mock
async def test_no_staging_subdomain_no_signal(http, fixtures) -> None:
    client, cache = http
    crtsh_clean = [{"name_value": "acme.com"}, {"name_value": "www.acme.com"}]
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=crtsh_clean))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=fixtures["headers"])
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkey_dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    assert Signal.OPEN_STAGING_SUBDOMAIN not in result.signals


@respx.mock
async def test_csp_present_no_signal(http, fixtures) -> None:
    client, cache = http
    headers_with_csp = {**fixtures["headers"], "content-security-policy": "default-src 'self'"}
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers=headers_with_csp)
    )
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkey_dns = AsyncMock(return_value={"A": [], "MX": [], "TXT": []})
    target = Target(company_name="Acme", root_url="https://acme.com")
    ctx = CollectorContext(target=target, http=client, cache=cache)
    collector = FootprintCollector(_dns_lookup=monkey_dns)
    result = await collector.run(ctx)

    assert Signal.MISSING_CSP not in result.signals
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/collectors/test_footprint.py -v`
Expected: ImportError on `tradecraft.collectors.footprint`.

- [ ] **Step 4: Implement `src/tradecraft/collectors/footprint.py`**

```python
"""Web/infra footprint collector: DNS + CT subdomains + headers + robots/sitemap."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import ClassVar
from urllib.parse import urlparse

import dns.asyncresolver

from tradecraft.collectors.base import CollectorContext
from tradecraft.models import (
    CollectorError,
    CollectorResult,
    Role,
    Signal,
)

_STAGING_PREFIXES = ("staging.", "dev.", "test.", "qa.", "uat.")
_DNS_RECORD_TYPES = ("A", "AAAA", "MX", "NS", "TXT", "CAA")
_DnsLookup = Callable[[str], Awaitable[dict[str, list[str]]]]


async def _default_dns_lookup(host: str) -> dict[str, list[str]]:
    resolver = dns.asyncresolver.Resolver()
    out: dict[str, list[str]] = {}
    for rtype in _DNS_RECORD_TYPES:
        try:
            answer = await resolver.resolve(host, rtype, lifetime=5.0)
        except Exception:  # noqa: BLE001 — DNS lookups frequently NXDOMAIN; treat as empty
            out[rtype] = []
            continue
        out[rtype] = [r.to_text() for r in answer]
    return out


class FootprintCollector:
    name: ClassVar[str] = "footprint"
    requires_network: ClassVar[bool] = True
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY, Role.SWE, Role.DEVOPS}

    def __init__(self, _dns_lookup: _DnsLookup | None = None) -> None:
        self._dns_lookup = _dns_lookup or _default_dns_lookup

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        host = urlparse(str(ctx.target.root_url)).hostname or ""
        errors: list[CollectorError] = []
        signals: list[Signal] = []

        dns_records, subdomains, root_response, robots_text, sitemap_text = await asyncio.gather(
            self._safe(self._dns_lookup(host), errors, "dns"),
            self._safe(self._crtsh(ctx, host), errors, "crtsh"),
            self._safe(ctx.http.get(str(ctx.target.root_url)), errors, "root_get"),
            self._safe(ctx.http.get(f"https://{host}/robots.txt"), errors, "robots"),
            self._safe(ctx.http.get(f"https://{host}/sitemap.xml"), errors, "sitemap"),
        )

        sec_headers: dict[str, str] = {}
        server_header = None
        powered_by = None
        if root_response is not None:
            sec_headers = {
                k.lower(): v
                for k, v in root_response.headers.items()
                if k.lower()
                in {
                    "content-security-policy",
                    "strict-transport-security",
                    "x-frame-options",
                    "x-content-type-options",
                    "referrer-policy",
                    "permissions-policy",
                }
            }
            server_header = root_response.headers.get("server")
            powered_by = root_response.headers.get("x-powered-by")

        if root_response is not None:
            if "content-security-policy" not in sec_headers:
                signals.append(Signal.MISSING_CSP)
            if "strict-transport-security" not in sec_headers:
                signals.append(Signal.MISSING_HSTS)

        cleaned_subs: list[str] = []
        if subdomains is not None:
            cleaned_subs = sorted(
                {
                    s
                    for s in subdomains
                    if not s.startswith("*")
                    and (s == host or s.endswith("." + host))
                }
            )
            if any(s.startswith(_STAGING_PREFIXES) for s in cleaned_subs):
                signals.append(Signal.OPEN_STAGING_SUBDOMAIN)

        return CollectorResult(
            name=self.name,
            data={
                "host": host,
                "dns": dns_records or {},
                "subdomains": cleaned_subs,
                "security_headers": sec_headers,
                "server": server_header,
                "x_powered_by": powered_by,
                "has_robots_txt": robots_text is not None and getattr(robots_text, "status_code", 0) == 200,
                "has_sitemap_xml": sitemap_text is not None and getattr(sitemap_text, "status_code", 0) == 200,
            },
            signals=signals,
            errors=errors,
            duration_ms=0,
        )

    async def _crtsh(self, ctx: CollectorContext, host: str) -> list[str]:
        response = await ctx.http.get(f"https://crt.sh/?q={host}&output=json")
        if response.status_code != 200:
            return []
        try:
            data = response.json()
        except Exception:  # noqa: BLE001
            return []
        names: set[str] = set()
        for entry in data:
            raw = entry.get("name_value", "")
            for name in str(raw).splitlines():
                cleaned = name.strip().lower()
                if cleaned:
                    names.add(cleaned)
        return sorted(names)

    @staticmethod
    async def _safe(
        awaitable: Awaitable[object],
        errors: list[CollectorError],
        stage: str,
    ) -> object | None:
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

- [ ] **Step 5: Run tests + lint + type**

```bash
uv run pytest tests/unit/collectors/test_footprint.py -v
uv run ruff check src/tradecraft/collectors/footprint.py tests/unit/collectors/test_footprint.py
uv run mypy src/tradecraft/collectors/footprint.py
```
Expected: pass / clean / clean.

- [ ] **Step 6: Commit**

```bash
git add src/tradecraft/collectors/footprint.py tests/unit/collectors/test_footprint.py tests/fixtures/footprint/
git commit -m "$(cat <<'EOF'
feat: footprint collector (DNS, crt.sh subdomains, headers, robots/sitemap)

First real collector wired through the protocol from Task 10.
Emits MISSING_CSP, MISSING_HSTS, OPEN_STAGING_SUBDOMAIN signals
for the heuristic analyzer. DNS lookup is injectable so tests
can mock it without touching the network. crt.sh subdomain
results are filtered to the target's domain and wildcards are
dropped.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Question template library

**Files:**
- Create: `src/tradecraft/analyzers/__init__.py`
- Create: `src/tradecraft/analyzers/templates.py`
- Create: `tests/unit/analyzers/__init__.py`
- Create: `tests/unit/analyzers/test_templates.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/analyzers/__init__.py`:
```python
```

`tests/unit/analyzers/test_templates.py`:
```python
"""Tests for tradecraft.analyzers.templates."""

from __future__ import annotations

import pytest

from tradecraft.analyzers.templates import (
    QuestionTemplate,
    TEMPLATES,
)
from tradecraft.models import Role, Signal


def test_template_library_is_non_empty() -> None:
    assert len(TEMPLATES) >= 10


def test_every_template_has_a_known_signal() -> None:
    known = set(Signal)
    for tmpl in TEMPLATES:
        for sig in tmpl.signals:
            assert sig in known


def test_every_template_has_at_least_one_role() -> None:
    for tmpl in TEMPLATES:
        assert tmpl.roles, f"template '{tmpl.id}' has no roles"


def test_every_template_id_is_unique() -> None:
    ids = [t.id for t in TEMPLATES]
    assert len(ids) == len(set(ids))


def test_template_dataclass_fields() -> None:
    t = QuestionTemplate(
        id="x",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY}),
        text="Why no CSP?",
        confidence="med",
        source="footprint",
    )
    assert t.confidence == "med"
    assert Signal.MISSING_CSP in t.signals
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/analyzers/test_templates.py -v`
Expected: ImportError on `tradecraft.analyzers.templates`.

- [ ] **Step 3: Implement the templates module**

`src/tradecraft/analyzers/__init__.py`:
```python
"""Analyzers: heuristic + AI question generation."""
```

`src/tradecraft/analyzers/templates.py`:
```python
"""Starter library of QuestionTemplates.

Each template is keyed by one or more Signals. The heuristic analyzer fires a
template when any of its signals appears in Findings AND the user's --role is in
the template's roles set.

The MVP-walking-skeleton ships ~12 templates (mostly footprint-driven, since
that's our only collector yet). Plan 2 grows this library as each new collector
lands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tradecraft.models import Role, Signal


@dataclass(frozen=True)
class QuestionTemplate:
    id: str
    signals: tuple[Signal, ...]
    roles: frozenset[Role]
    text: str
    confidence: Literal["high", "med", "low"]
    source: str


_ALL_TECH_ROLES = frozenset(
    {Role.CYBERSECURITY, Role.SWE, Role.DEVOPS, Role.DATA, Role.ENG_LEADERSHIP}
)


TEMPLATES: tuple[QuestionTemplate, ...] = (
    QuestionTemplate(
        id="footprint.missing_csp",
        signals=(Signal.MISSING_CSP,),
        roles=frozenset({Role.CYBERSECURITY, Role.SWE}),
        text=(
            "Your main site doesn't ship a Content-Security-Policy header. "
            "Is that a deliberate posture, or is the team working toward one?"
        ),
        confidence="med",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.missing_hsts",
        signals=(Signal.MISSING_HSTS,),
        roles=frozenset({Role.CYBERSECURITY, Role.DEVOPS}),
        text=(
            "I noticed your apex doesn't return Strict-Transport-Security. "
            "How does the team think about transport hardening across subdomains?"
        ),
        confidence="med",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.open_staging",
        signals=(Signal.OPEN_STAGING_SUBDOMAIN,),
        roles=frozenset({Role.CYBERSECURITY, Role.DEVOPS}),
        text=(
            "I saw pre-prod hostnames in public certificate transparency logs. "
            "Does the team have a stance on hiding or hardening pre-prod surface area?"
        ),
        confidence="high",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.cert_expiring",
        signals=(Signal.CERT_EXPIRING_SOON,),
        roles=frozenset({Role.CYBERSECURITY, Role.DEVOPS}),
        text=(
            "Your apex TLS certificate expires soon. Is rotation automated end-to-end, "
            "or is there a manual step in the rollout?"
        ),
        confidence="med",
        source="footprint",
    ),
    QuestionTemplate(
        id="footprint.exposed_admin",
        signals=(Signal.EXPOSED_ADMIN_PATH,),
        roles=frozenset({Role.CYBERSECURITY}),
        text=(
            "robots.txt or sitemap.xml references admin paths. "
            "How does the team approach reducing the discoverable attack surface?"
        ),
        confidence="med",
        source="footprint",
    ),
    QuestionTemplate(
        id="company.recent_press",
        signals=(Signal.RECENT_PRESS_RELEASE,),
        roles=_ALL_TECH_ROLES | {Role.GENERIC},
        text=(
            "I saw your recent announcement. How is that landing internally, "
            "and how does it shape what this team will prioritize next quarter?"
        ),
        confidence="med",
        source="company",
    ),
    QuestionTemplate(
        id="company.founder_technical",
        signals=(Signal.FOUNDER_TECHNICAL,),
        roles=_ALL_TECH_ROLES,
        text=(
            "Your founders have deep technical backgrounds. "
            "How involved are they in current engineering decisions versus delegating?"
        ),
        confidence="low",
        source="company",
    ),
    QuestionTemplate(
        id="job.stack_mismatch",
        signals=(Signal.LANGUAGES_MISMATCH_JOB,),
        roles={Role.SWE, Role.DEVOPS, Role.CYBERSECURITY},
        text=(
            "The job description calls for a stack that doesn't dominate your public repos. "
            "Is the team mid-migration, or is this stack scoped to a specific new initiative?"
        ),
        confidence="high",
        source="job",
    ),
    QuestionTemplate(
        id="job.stack_alignment",
        signals=(Signal.STACK_ALIGNMENT_STRONG,),
        roles={Role.SWE, Role.DEVOPS},
        text=(
            "Your public stack aligns closely with the job description. "
            "Where does the team feel that stack is straining at scale?"
        ),
        confidence="med",
        source="job",
    ),
    QuestionTemplate(
        id="news.layoffs",
        signals=(Signal.RECENT_LAYOFFS,),
        roles=_ALL_TECH_ROLES | {Role.GENERIC},
        text=(
            "I saw the recent layoffs in the news. "
            "How has the team's scope shifted, and what's the focus for the remaining quarter?"
        ),
        confidence="high",
        source="news",
    ),
    QuestionTemplate(
        id="news.funding",
        signals=(Signal.RECENT_FUNDING,),
        roles=_ALL_TECH_ROLES | {Role.GENERIC},
        text=(
            "Congrats on the recent funding round. "
            "Where is most of that capital going — hiring, infrastructure, or new product lines?"
        ),
        confidence="high",
        source="news",
    ),
    QuestionTemplate(
        id="news.leadership_change",
        signals=(Signal.RECENT_LEADERSHIP_CHANGE,),
        roles=_ALL_TECH_ROLES | {Role.GENERIC},
        text=(
            "The recent leadership change is interesting context. "
            "How has it shifted what the team is prioritizing?"
        ),
        confidence="med",
        source="news",
    ),
    QuestionTemplate(
        id="news.security_incident",
        signals=(Signal.RECENT_SECURITY_INCIDENT,),
        roles={Role.CYBERSECURITY, Role.DEVOPS, Role.ENG_LEADERSHIP},
        text=(
            "I read about the security incident earlier this year. "
            "What's changed in the team's posture and process since?"
        ),
        confidence="high",
        source="news",
    ),
    QuestionTemplate(
        id="breaches.history",
        signals=(Signal.BREACH_HISTORY,),
        roles={Role.CYBERSECURITY, Role.ENG_LEADERSHIP},
        text=(
            "Have I Been Pwned lists past breach events involving your domain. "
            "How does that history shape your current detection and response approach?"
        ),
        confidence="high",
        source="breaches",
    ),
    QuestionTemplate(
        id="ma.recent",
        signals=(Signal.M_A_RECENT,),
        roles=_ALL_TECH_ROLES | {Role.GENERIC},
        text=(
            "I saw the recent acquisition. "
            "How is the integration going — product, identity, security tooling, on-call?"
        ),
        confidence="high",
        source="ma",
    ),
)
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/analyzers/test_templates.py -v
uv run ruff check src/tradecraft/analyzers/ tests/unit/analyzers/
uv run mypy src/tradecraft/analyzers/
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/analyzers/__init__.py src/tradecraft/analyzers/templates.py tests/unit/analyzers/__init__.py tests/unit/analyzers/test_templates.py
git commit -m "$(cat <<'EOF'
feat: starter QuestionTemplate library (15 templates)

Templates cover the signals every v1 collector will emit, even
though only the footprint collector is wired yet — keeps plan 2
collectors from re-touching this file just to add their questions.
Each template is role-tagged so --role filters at analysis time.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Heuristic analyzer

**Files:**
- Create: `src/tradecraft/analyzers/heuristics.py`
- Create: `tests/unit/analyzers/test_heuristics.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/analyzers/test_heuristics.py`:
```python
"""Tests for tradecraft.analyzers.heuristics."""

from __future__ import annotations

from tradecraft.analyzers.heuristics import generate_questions
from tradecraft.analyzers.templates import QuestionTemplate, TEMPLATES
from tradecraft.models import (
    CollectorResult,
    Findings,
    Role,
    Signal,
    Target,
)


def _findings_with(signals: list[Signal], role: Role = Role.CYBERSECURITY) -> Findings:
    target = Target(company_name="Acme", root_url="https://acme.com", role=role)
    result = CollectorResult(
        name="footprint", data={}, signals=signals, errors=[], duration_ms=0
    )
    return Findings(target=target, results=[result])


def test_no_signals_yields_no_questions() -> None:
    f = _findings_with([])
    questions = generate_questions(f)
    assert questions == []


def test_single_signal_fires_matching_template() -> None:
    f = _findings_with([Signal.MISSING_CSP])
    questions = generate_questions(f)
    assert questions
    assert any("Content-Security-Policy" in q.text for q in questions)


def test_role_filter_excludes_irrelevant_templates() -> None:
    # Stack mismatch is tagged for swe/devops/cybersecurity, NOT for data
    f = _findings_with([Signal.LANGUAGES_MISMATCH_JOB], role=Role.DATA)
    questions = generate_questions(f)
    assert all("stack that doesn't dominate" not in q.text for q in questions)


def test_data_role_still_gets_relevant_templates() -> None:
    f = _findings_with([Signal.RECENT_FUNDING], role=Role.DATA)
    questions = generate_questions(f)
    assert any("funding" in q.text for q in questions)


def test_top_3_are_starred() -> None:
    f = _findings_with(
        [Signal.OPEN_STAGING_SUBDOMAIN, Signal.MISSING_CSP, Signal.MISSING_HSTS, Signal.RECENT_FUNDING]
    )
    questions = generate_questions(f)
    starred = [q for q in questions if q.is_starred]
    assert len(starred) <= 3


def test_no_duplicate_templates_when_multiple_signals_share_one_template() -> None:
    """Currently each template has a single signal in tuple; this test guards
    against a future tuple-of-signals template producing two Question objects."""
    f = _findings_with([Signal.MISSING_CSP, Signal.MISSING_CSP])
    questions = generate_questions(f)
    csp_qs = [q for q in questions if "Content-Security-Policy" in q.text]
    assert len(csp_qs) == 1


def test_question_evidence_signal_matches_trigger() -> None:
    f = _findings_with([Signal.MISSING_CSP])
    [question] = generate_questions(f)
    assert question.evidence_signal == Signal.MISSING_CSP
    assert question.source_collector == "footprint"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/analyzers/test_heuristics.py -v`
Expected: ImportError on `tradecraft.analyzers.heuristics`.

- [ ] **Step 3: Implement `src/tradecraft/analyzers/heuristics.py`**

```python
"""Heuristic question generator: signal-driven, role-aware, deterministic."""

from __future__ import annotations

from collections.abc import Sequence

from tradecraft.analyzers.templates import QuestionTemplate, TEMPLATES
from tradecraft.models import Findings, Question, Signal

_CONFIDENCE_ORDER = {"high": 0, "med": 1, "low": 2}


def generate_questions(
    findings: Findings,
    *,
    templates: Sequence[QuestionTemplate] = TEMPLATES,
    star_top_n: int = 3,
) -> list[Question]:
    """Produce questions for every template whose signals are present AND whose roles include findings.target.role."""
    present = findings.all_signals
    role = findings.target.role
    seen_ids: set[str] = set()
    fired: list[Question] = []
    for tmpl in templates:
        if tmpl.id in seen_ids:
            continue
        if role not in tmpl.roles:
            continue
        triggers = [s for s in tmpl.signals if s in present]
        if not triggers:
            continue
        seen_ids.add(tmpl.id)
        fired.append(
            Question(
                text=tmpl.text,
                confidence=tmpl.confidence,
                role_tags=set(tmpl.roles),
                evidence_signal=triggers[0],
                source_collector=tmpl.source,
            )
        )
    fired.sort(key=lambda q: _CONFIDENCE_ORDER[q.confidence])
    for q in fired[:star_top_n]:
        q.is_starred = True
    return fired
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/analyzers/test_heuristics.py -v
uv run ruff check src/tradecraft/analyzers/heuristics.py tests/unit/analyzers/test_heuristics.py
uv run mypy src/tradecraft/analyzers/heuristics.py
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/analyzers/heuristics.py tests/unit/analyzers/test_heuristics.py
git commit -m "$(cat <<'EOF'
feat: heuristic question generator (signal + role driven, deterministic)

Fires each matching template at most once. Filters by role.
Sorted by confidence; top 3 starred. Evidence signal preserved
on each Question so the markdown renderer can cite it.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: JSON renderer

**Files:**
- Create: `src/tradecraft/renderers/__init__.py`
- Create: `src/tradecraft/renderers/json.py`
- Create: `tests/unit/renderers/__init__.py`
- Create: `tests/unit/renderers/test_json.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/renderers/__init__.py`:
```python
```

`tests/unit/renderers/test_json.py`:
```python
"""Tests for tradecraft.renderers.json."""

from __future__ import annotations

import json

from tradecraft.models import (
    CollectorResult,
    Findings,
    Question,
    Role,
    Signal,
    Target,
)
from tradecraft.renderers.json import render_json


def test_renders_full_findings() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="footprint",
                data={"host": "acme.com"},
                signals=[Signal.MISSING_CSP],
                errors=[],
                duration_ms=10,
            )
        ],
    )
    questions = [
        Question(
            text="Q",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=True,
        )
    ]
    out = render_json(findings, questions)
    parsed = json.loads(out)
    assert parsed["schema_version"] == 1
    assert parsed["target"]["company_name"] == "Acme"
    assert parsed["results"][0]["name"] == "footprint"
    assert parsed["questions"][0]["is_starred"] is True


def test_output_is_stable_ordering() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(target=target, results=[])
    a = render_json(findings, [])
    b = render_json(findings, [])
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/renderers/test_json.py -v`
Expected: ImportError on `tradecraft.renderers.json`.

- [ ] **Step 3: Implement the renderer**

`src/tradecraft/renderers/__init__.py`:
```python
"""Renderers: turn Findings + questions into shipped artifacts."""
```

`src/tradecraft/renderers/json.py`:
```python
"""JSON renderer: full Findings + questions dump with a stable schema."""

from __future__ import annotations

import json
from collections.abc import Sequence

from tradecraft.models import Findings, Question


def render_json(findings: Findings, questions: Sequence[Question]) -> str:
    payload = {
        "schema_version": findings.schema_version,
        "target": findings.target.model_dump(mode="json"),
        "results": [r.model_dump(mode="json") for r in findings.results],
        "questions": [q.model_dump(mode="json") for q in questions],
    }
    return json.dumps(payload, indent=2, sort_keys=True, default=str)
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/renderers/test_json.py -v
uv run ruff check src/tradecraft/renderers/ tests/unit/renderers/
uv run mypy src/tradecraft/renderers/
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/renderers/__init__.py src/tradecraft/renderers/json.py tests/unit/renderers/__init__.py tests/unit/renderers/test_json.py
git commit -m "$(cat <<'EOF'
feat: JSON renderer (full Findings + questions, stable schema v1)

sort_keys + indent=2 so diffs across runs are clean and the file
is human-skimmable. schema_version pinned at 1; bumps will be
called out in CHANGELOG when the JSON shape changes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: Markdown renderer

**Files:**
- Create: `src/tradecraft/renderers/markdown.py`
- Create: `tests/unit/renderers/test_markdown.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/renderers/test_markdown.py`:
```python
"""Tests for tradecraft.renderers.markdown."""

from __future__ import annotations

from tradecraft.models import (
    CollectorResult,
    Findings,
    Question,
    Role,
    Signal,
    Target,
)
from tradecraft.renderers.markdown import render_markdown


def _findings_full() -> Findings:
    target = Target(
        company_name="Acme Corp",
        root_url="https://acme.com",
        job_url="https://acme.com/jobs/1",
        role=Role.CYBERSECURITY,
    )
    return Findings(
        target=target,
        results=[
            CollectorResult(
                name="footprint",
                data={
                    "host": "acme.com",
                    "subdomains": ["api.acme.com", "staging.acme.com"],
                    "security_headers": {"strict-transport-security": "max-age=1"},
                    "server": "nginx",
                    "x_powered_by": "Next.js",
                    "has_robots_txt": True,
                    "has_sitemap_xml": False,
                },
                signals=[Signal.MISSING_CSP, Signal.OPEN_STAGING_SUBDOMAIN],
                errors=[],
                duration_ms=120,
            )
        ],
    )


def test_renders_all_top_level_sections() -> None:
    findings = _findings_full()
    md = render_markdown(findings, [])
    for heading in (
        "# Acme Corp",
        "## Snapshot",
        "## Web & infrastructure footprint",
        "## Questions to ask",
        "## Collection notes",
    ):
        assert heading in md, f"missing section: {heading}"


def test_includes_subdomains_and_signals() -> None:
    findings = _findings_full()
    md = render_markdown(findings, [])
    assert "staging.acme.com" in md
    assert "api.acme.com" in md


def test_includes_questions_with_starred_first() -> None:
    findings = _findings_full()
    qs = [
        Question(
            text="Top one",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.OPEN_STAGING_SUBDOMAIN,
            source_collector="footprint",
            is_starred=True,
        ),
        Question(
            text="Second",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=False,
        ),
    ]
    md = render_markdown(findings, qs)
    top_idx = md.index("Top one")
    second_idx = md.index("Second")
    assert top_idx < second_idx


def test_collection_notes_reports_errors() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    from tradecraft.models import CollectorError

    findings = Findings(
        target=target,
        results=[
            CollectorResult(
                name="footprint",
                data={},
                signals=[],
                errors=[CollectorError(stage="dns", message="timeout")],
                duration_ms=10,
            )
        ],
    )
    md = render_markdown(findings, [])
    assert "Collection notes" in md
    assert "footprint" in md
    assert "timeout" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/renderers/test_markdown.py -v`
Expected: ImportError on `tradecraft.renderers.markdown`.

- [ ] **Step 3: Implement `src/tradecraft/renderers/markdown.py`**

```python
"""Markdown renderer: the human-readable dossier."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from tradecraft import __version__
from tradecraft.models import Findings, Question, Signal


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


def _snapshot_section(findings: Findings) -> str:
    target = findings.target
    lines = ["## Snapshot", ""]
    lines.append(f"- **URL:** {target.root_url}")
    if target.job_url:
        lines.append(f"- **Job listing:** {target.job_url}")
    lines.append(f"- **Role focus:** `{target.role.value}`")
    lines.append(
        f"- **Generated:** {datetime.now(tz=UTC).isoformat(timespec='seconds')} "
        f"by tradecraft {__version__}"
    )
    lines.append("")
    return "\n".join(lines)


def _footprint_section(findings: Findings) -> str:
    result = findings.collector("footprint")
    lines = [
        "## Web & infrastructure footprint",
        "",
        "What an external observer can learn from public infrastructure signals.",
        "",
    ]
    if result is None:
        lines.append("_No footprint data collected._")
        lines.append("")
        return "\n".join(lines)
    data = result.data
    lines.append(f"- **Host:** `{data.get('host', '?')}`")
    server = data.get("server")
    if server:
        lines.append(f"- **Server header:** `{server}`")
    powered_by = data.get("x_powered_by")
    if powered_by:
        lines.append(f"- **X-Powered-By:** `{powered_by}`")
    headers = data.get("security_headers") or {}
    if headers:
        lines.append("- **Security headers present:** "
                     + ", ".join(f"`{k}`" for k in sorted(headers)))
    else:
        lines.append("- **Security headers present:** _none_")

    subs = data.get("subdomains") or []
    if subs:
        lines.append("")
        lines.append("### Subdomains observed in public CT logs")
        lines.append("")
        for s in subs:
            lines.append(f"- `{s}`")

    signals = result.signals
    if signals:
        lines.append("")
        lines.append("### Signals")
        lines.append("")
        for s in signals:
            lines.append(f"- `{s.value}`")
    lines.append("")
    return "\n".join(lines)


def _questions_section(questions: Sequence[Question]) -> str:
    lines = [
        "## Questions to ask",
        "",
        "Evidence-cited prompts to take into the interview. Starred items are the "
        "highest-confidence picks.",
        "",
    ]
    if not questions:
        lines.append("_No heuristic-driven questions generated. Add more collector "
                     "coverage or run with `--ai` to deepen this section._")
        lines.append("")
        return "\n".join(lines)

    starred = [q for q in questions if q.is_starred]
    rest = [q for q in questions if not q.is_starred]
    if starred:
        lines.append("### Top picks")
        lines.append("")
        for q in starred:
            lines.append(_format_question(q))
        lines.append("")
    if rest:
        lines.append("### Further questions")
        lines.append("")
        for q in rest:
            lines.append(_format_question(q))
        lines.append("")
    return "\n".join(lines)


def _format_question(q: Question) -> str:
    tags = " ".join(f"`{r.value}`" for r in sorted(q.role_tags))
    return (
        f"- **{q.text}**  \n"
        f"  _confidence:_ `{q.confidence}` · _evidence:_ `{q.evidence_signal.value}` "
        f"from `{q.source_collector}` · _roles:_ {tags}"
    )


def _collection_notes(findings: Findings) -> str:
    lines = ["## Collection notes", ""]
    for r in findings.results:
        lines.append(f"- **{r.name}** — {r.duration_ms} ms")
        for err in r.errors:
            lines.append(f"  - error in `{err.stage}`: {err.message}")
    lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/renderers/test_markdown.py -v
uv run ruff check src/tradecraft/renderers/markdown.py tests/unit/renderers/test_markdown.py
uv run mypy src/tradecraft/renderers/markdown.py
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/renderers/markdown.py tests/unit/renderers/test_markdown.py
git commit -m "$(cat <<'EOF'
feat: markdown renderer (Snapshot, Footprint, Questions, Collection notes)

Walking-skeleton renderer; sections for the seven future collectors
are added as those collectors land in plan 2 (each section is a
single function so adding one doesn't bloat this file). Starred
questions surface above the rest; each question cites the signal +
collector that triggered it.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: Standalone questions renderer

**Files:**
- Create: `src/tradecraft/renderers/questions.py`
- Create: `tests/unit/renderers/test_questions.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/renderers/test_questions.py`:
```python
"""Tests for tradecraft.renderers.questions."""

from __future__ import annotations

from tradecraft.models import Question, Role, Signal
from tradecraft.renderers.questions import render_questions


def test_renders_starred_first_then_rest() -> None:
    qs = [
        Question(
            text="Top",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.OPEN_STAGING_SUBDOMAIN,
            source_collector="footprint",
            is_starred=True,
        ),
        Question(
            text="Other",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=False,
        ),
    ]
    out = render_questions(qs, company_name="Acme")
    assert "# Questions to ask Acme" in out
    assert out.index("Top") < out.index("Other")


def test_empty_questions_renders_placeholder() -> None:
    out = render_questions([], company_name="Acme")
    assert "No heuristic-driven questions" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/renderers/test_questions.py -v`
Expected: ImportError on `tradecraft.renderers.questions`.

- [ ] **Step 3: Implement `src/tradecraft/renderers/questions.py`**

```python
"""Standalone questions renderer: just the questions section, ready to print."""

from __future__ import annotations

from collections.abc import Sequence

from tradecraft.models import Question


def render_questions(questions: Sequence[Question], *, company_name: str) -> str:
    lines = [f"# Questions to ask {company_name}", ""]
    if not questions:
        lines.append(
            "_No heuristic-driven questions generated for this run._"
        )
        lines.append("")
        return "\n".join(lines)

    starred = [q for q in questions if q.is_starred]
    rest = [q for q in questions if not q.is_starred]

    if starred:
        lines.append("## Top picks")
        lines.append("")
        for q in starred:
            lines.append(_format(q))
        lines.append("")
    if rest:
        lines.append("## Further questions")
        lines.append("")
        for q in rest:
            lines.append(_format(q))
        lines.append("")
    return "\n".join(lines)


def _format(q: Question) -> str:
    tags = " ".join(f"`{r.value}`" for r in sorted(q.role_tags))
    return (
        f"- **{q.text}**  \n"
        f"  _confidence:_ `{q.confidence}` · _evidence:_ "
        f"`{q.evidence_signal.value}` from `{q.source_collector}` · _roles:_ {tags}"
    )
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/renderers/test_questions.py -v
uv run ruff check src/tradecraft/renderers/questions.py tests/unit/renderers/test_questions.py
uv run mypy src/tradecraft/renderers/questions.py
```
Expected: pass / clean / clean.

- [ ] **Step 5: Commit**

```bash
git add src/tradecraft/renderers/questions.py tests/unit/renderers/test_questions.py
git commit -m "$(cat <<'EOF'
feat: standalone questions renderer

Same shape as the questions section of the full report, but
self-contained so a user can paste it straight into notes
without bringing the whole dossier.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: CLI

**Files:**
- Create: `src/tradecraft/cli.py`
- Create: `tests/unit/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_cli.py`:
```python
"""Tests for tradecraft.cli."""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from tradecraft.cli import app
from tradecraft.collectors.base import Collector, CollectorContext
from tradecraft.models import (
    CollectorResult,
    Role,
    Signal,
)


class StubFootprint(Collector):
    name: ClassVar[str] = "footprint"
    requires_network: ClassVar[bool] = False
    safe_for_hosted: ClassVar[bool] = True
    role_relevance: ClassVar[set[Role]] = {Role.CYBERSECURITY}

    async def run(self, ctx: CollectorContext) -> CollectorResult:
        return CollectorResult(
            name="footprint",
            data={"host": "acme.com", "subdomains": ["staging.acme.com"]},
            signals=[Signal.MISSING_CSP, Signal.OPEN_STAGING_SUBDOMAIN],
            errors=[],
            duration_ms=10,
        )


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_help_exits_zero(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "interview" in result.stdout.lower()


def test_refuses_person_name(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["https://example.com", "--company", "John Smith", "--output", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "person" in result.stdout.lower() or "person" in result.stderr.lower()


def test_end_to_end_produces_dossier(runner: CliRunner, tmp_path: Path) -> None:
    with patch("tradecraft.cli._default_collectors", return_value=[StubFootprint()]):
        result = runner.invoke(
            app,
            [
                "https://acme.com",
                "--company",
                "Acme Corp",
                "--output",
                str(tmp_path),
            ],
        )
    assert result.exit_code == 0, result.stdout
    dossier_dirs = list(tmp_path.iterdir())
    assert len(dossier_dirs) == 1
    folder = dossier_dirs[0]
    assert folder.name.startswith("acme-corp-")
    assert (folder / "report.md").exists()
    assert (folder / "questions.md").exists()
    assert (folder / "raw.json").exists()
    raw = json.loads((folder / "raw.json").read_text())
    assert raw["schema_version"] == 1


def test_json_flag_writes_only_json_to_stdout(runner: CliRunner) -> None:
    with patch("tradecraft.cli._default_collectors", return_value=[StubFootprint()]):
        result = runner.invoke(
            app,
            ["https://acme.com", "--company", "Acme Corp", "--json"],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["target"]["company_name"] == "Acme Corp"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: ImportError on `tradecraft.cli`.

- [ ] **Step 3: Implement `src/tradecraft/cli.py`**

```python
"""tradecraft CLI (typer)."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from tradecraft.analyzers.heuristics import generate_questions
from tradecraft.cache import Cache
from tradecraft.collectors.base import Collector
from tradecraft.collectors.footprint import FootprintCollector
from tradecraft.config import default_config_path, load_config
from tradecraft.ethics import is_likely_person_name
from tradecraft.http import HttpClient
from tradecraft.models import Findings, Role, Target
from tradecraft.orchestrator import Orchestrator
from tradecraft.renderers.json import render_json
from tradecraft.renderers.markdown import render_markdown
from tradecraft.renderers.questions import render_questions

app = typer.Typer(
    name="tradecraft",
    help="OSINT tradecraft for the interview chair. Build a dossier on a company.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


def _default_collectors() -> list[Collector]:
    return [FootprintCollector()]


def _infer_company_name(root_url: str) -> str:
    from urllib.parse import urlparse

    host = urlparse(root_url).hostname or root_url
    parts = host.split(".")
    if len(parts) >= 2:
        return parts[-2].capitalize()
    return host


@app.command()
def main(
    root_url: Annotated[str, typer.Argument(help="Company root URL, e.g. https://acme.com")],
    job: Annotated[str | None, typer.Option(help="Job listing URL")] = None,
    role: Annotated[Role, typer.Option(help="Role focus for the dossier")] = Role.CYBERSECURITY,
    company: Annotated[str | None, typer.Option(help="Override the inferred company name")] = None,
    output: Annotated[Path, typer.Option(help="Output folder root")] = Path("./dossiers"),
    only: Annotated[str | None, typer.Option(help="Run only these collectors (comma-separated)")] = None,
    skip: Annotated[str | None, typer.Option(help="Skip these collectors (comma-separated)")] = None,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Bypass on-disk cache")] = False,
    json_only: Annotated[bool, typer.Option("--json", help="Print raw.json to stdout, no folder")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log every HTTP request")] = False,
) -> None:
    """Build an interview-prep dossier."""
    company_name = company or _infer_company_name(root_url)
    if is_likely_person_name(company_name):
        err_console.print(
            f"[red]Refusing to run: '{company_name}' looks like a person's name. "
            "tradecraft is for companies only.[/]"
        )
        raise typer.Exit(code=2)

    target = Target(
        company_name=company_name,
        root_url=root_url,
        job_url=job,
        role=role,
    )

    cfg = load_config(default_config_path())
    if no_cache:
        cfg = cfg.model_copy(update={"cache": cfg.cache.model_copy(update={"enabled": False})})

    findings, questions = asyncio.run(_run(target, cfg, only, skip, verbose))

    if json_only:
        typer.echo(render_json(findings, questions))
        return

    folder = output / f"{target.company_slug}-{datetime.now(tz=UTC):%Y-%m-%d}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.md").write_text(render_markdown(findings, questions), encoding="utf-8")
    (folder / "questions.md").write_text(
        render_questions(questions, company_name=company_name), encoding="utf-8"
    )
    (folder / "raw.json").write_text(render_json(findings, questions), encoding="utf-8")
    console.print(f"[green]Dossier written to[/] {folder}")


async def _run(
    target: Target,
    cfg,
    only: str | None,
    skip: str | None,
    verbose: bool,
) -> tuple[Findings, list]:
    cache_dir = (
        Path(cfg.cache.directory) if cfg.cache.directory else Path.home() / ".cache" / "tradecraft"
    )
    cache = Cache(directory=cache_dir, default_ttl=cfg.cache.ttl_default_seconds, enabled=cfg.cache.enabled)
    async with HttpClient(cfg.http, cache) as http:
        orch = Orchestrator(_default_collectors(), http=http, cache=cache)
        findings = await orch.run(
            target,
            only=set(only.split(",")) if only else None,
            skip=set(skip.split(",")) if skip else None,
        )
    if verbose:
        for r in findings.results:
            err_console.print(f"[dim]{r.name}: {r.duration_ms} ms, signals={[s.value for s in r.signals]}[/]")
    questions = generate_questions(findings)
    return findings, questions


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run tests + lint + type**

```bash
uv run pytest tests/unit/test_cli.py -v
uv run ruff check src/tradecraft/cli.py tests/unit/test_cli.py
uv run mypy src/tradecraft/cli.py
```
Expected: pass / clean / clean.

- [ ] **Step 5: Verify the installed CLI works**

```bash
uv run tradecraft --help
```
Expected: prints the help text, exit code 0.

- [ ] **Step 6: Commit**

```bash
git add src/tradecraft/cli.py tests/unit/test_cli.py
git commit -m "$(cat <<'EOF'
feat: typer CLI with --json, --role, --only/--skip, --no-cache

Refuses person-name inputs at the entrypoint per the ethics module.
--json writes raw.json to stdout for shell pipelines. Default mode
writes report.md + questions.md + raw.json into a dated folder
under --output (default ./dossiers/<slug>-YYYY-MM-DD/).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 19: End-to-end integration test

**Files:**
- Create: `tests/integration/test_end_to_end.py`
- Create: `tests/fixtures/footprint/crtsh_e2e.json`

- [ ] **Step 1: Create fixture**

`tests/fixtures/footprint/crtsh_e2e.json`:
```json
[
    {"name_value": "e2e.test"},
    {"name_value": "www.e2e.test"},
    {"name_value": "staging.e2e.test"}
]
```

- [ ] **Step 2: Write the integration test**

`tests/integration/test_end_to_end.py`:
```python
"""End-to-end: CLI -> Orchestrator -> Collector -> Heuristics -> Renderers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from typer.testing import CliRunner

from tradecraft.cli import app
from tradecraft.collectors.footprint import FootprintCollector


@respx.mock
def test_full_run_produces_real_dossier(tmp_path: Path, fixtures_dir: Path) -> None:
    crtsh = json.loads((fixtures_dir / "footprint" / "crtsh_e2e.json").read_text())
    respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=crtsh))
    respx.get("https://e2e.test/").mock(
        return_value=httpx.Response(
            200,
            text="<html><body>hi</body></html>",
            headers={"server": "nginx", "strict-transport-security": "max-age=1"},
        )
    )
    respx.get("https://e2e.test/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://e2e.test/sitemap.xml").mock(return_value=httpx.Response(404))

    dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})
    runner = CliRunner()
    with patch(
        "tradecraft.cli._default_collectors",
        return_value=[FootprintCollector(_dns_lookup=dns)],
    ):
        result = runner.invoke(
            app,
            [
                "https://e2e.test",
                "--company",
                "E2E Test Inc",
                "--output",
                str(tmp_path),
            ],
        )
    assert result.exit_code == 0, result.stdout

    [folder] = list(tmp_path.iterdir())
    report = (folder / "report.md").read_text(encoding="utf-8")
    questions_md = (folder / "questions.md").read_text(encoding="utf-8")
    raw = json.loads((folder / "raw.json").read_text(encoding="utf-8"))

    # report covers the spine
    assert "# E2E Test Inc" in report
    assert "staging.e2e.test" in report
    # heuristics fired
    assert "Content-Security-Policy" in report
    assert "pre-prod" in report.lower() or "staging" in report.lower()
    # questions standalone
    assert "Questions to ask E2E Test Inc" in questions_md
    # json schema and roundtrip
    assert raw["schema_version"] == 1
    assert raw["target"]["company_name"] == "E2E Test Inc"
    assert any(q["evidence_signal"] == "missing_csp" for q in raw["questions"])
```

- [ ] **Step 3: Run the integration test**

```bash
uv run pytest tests/integration/test_end_to_end.py -v
```
Expected: pass.

- [ ] **Step 4: Run the whole test suite + lint + type**

```bash
uv run pytest -v
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```
Expected: everything green.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_end_to_end.py tests/fixtures/footprint/crtsh_e2e.json
git commit -m "$(cat <<'EOF'
test: end-to-end integration test for the walking skeleton

CLI -> Orchestrator -> FootprintCollector -> heuristics -> all
three renderers, with crt.sh / root / robots / sitemap and DNS
fully mocked. Validates the assembled artifact rather than any
single layer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 20: README demo + v0.1.0-alpha tag

**Files:**
- Modify: `README.md` (add a real example output section)
- Create: `CHANGELOG.md`

- [ ] **Step 1: Run the CLI once for real against a public test target to capture sample output**

Run:
```bash
uv run tradecraft https://example.com --company "Example" --output ./demo-output
```

Note any unexpected behavior. The point is to produce a small snippet for the README.

- [ ] **Step 2: Update `README.md` with a Sample Output section**

Open `README.md` and insert this section after the Usage section and before Intended Use:

```markdown
## Sample output

```
$ tradecraft https://example.com --company "Example"

footprint    87 ms  signals=[missing_csp, missing_hsts]

Dossier written to ./dossiers/example-2026-05-23/
```

`./dossiers/example-2026-05-23/report.md` (excerpt):

```markdown
# Example

## Snapshot
- URL: https://example.com
- Role focus: `cybersecurity`

## Web & infrastructure footprint
- Host: `example.com`
- Server header: `ECAcc (...)`
- Security headers present: _none_

### Signals
- `missing_csp`
- `missing_hsts`

## Questions to ask

### Top picks
- **Your main site doesn't ship a Content-Security-Policy header.
   Is that a deliberate posture, or is the team working toward one?**
  _confidence:_ `med` · _evidence:_ `missing_csp` from `footprint` · _roles:_ `cybersecurity` `swe`
```
```

- [ ] **Step 3: Create `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project will be documented here. Follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha] - 2026-05-23

### Added

- Plugin-based async collector framework (`Collector` protocol, `Orchestrator`).
- `footprint` collector: DNS, crt.sh subdomain enumeration, root-page headers,
  security headers, robots/sitemap detection.
- Heuristic question generator with a starter library of 15 templates covering
  signals from all eight planned collectors.
- Markdown + JSON + standalone questions renderers.
- Typer CLI with `--role`, `--only`/`--skip`, `--no-cache`, `--json`, `--verbose`.
- Filesystem cache with per-entry TTL.
- HTTP client with identifying User-Agent, per-host token-bucket rate limit,
  global concurrency cap, response size cap, redirect-to-private-IP guard, retries.
- Robots.txt parser (RFC 9309-aware) and person-name input guard.
- Configuration via `~/.config/tradecraft/config.toml` + `TRADECRAFT_*` env vars.
- MIT license, ETHICS.md, THREAT_MODEL.md, SECURITY.md.
- CI workflow (lint + typecheck + test on Python 3.11/3.12/3.13).

### Not yet shipped

- `company`, `job`, `news`, `breaches`, `github`, `people`, `business`, `ma` collectors
  (planned for v0.2.0, see `docs/superpowers/plans/`).
- BYOK AI analyzer and Anthropic/OpenAI/Ollama/OpenAI-compat providers.
- Hosted web preview (planned for v1.1).
```

- [ ] **Step 4: Final sweep — full lint + type + test**

```bash
uv run pytest -v
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```
Expected: all green.

- [ ] **Step 5: Commit and tag**

```bash
git add README.md CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs: sample output in README + initial CHANGELOG

Captures a real run snippet so the README hero scrolls demonstrate
the product instead of describing it. CHANGELOG bootstrapped at
0.1.0-alpha with a clear "not yet shipped" section pointing at
plan 2.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

git tag -a v0.1.0a0 -m "tradecraft v0.1.0-alpha: walking skeleton (footprint collector)"
git log --oneline -10
```

Expected: tag created, history shows 20 commits + 1 doc spec commit from earlier.

---

## Self-review (run by the engineer / agent after completing all tasks)

- [ ] `uv run pytest -v` passes with no failures and no `live`-marked tests run by default.
- [ ] `uv run ruff check src tests` is clean.
- [ ] `uv run ruff format --check src tests` is clean.
- [ ] `uv run mypy src` is clean.
- [ ] `uv run tradecraft --help` prints usage text.
- [ ] A real run (e.g., `uv run tradecraft https://example.com --company "Example"`) produces a folder containing `report.md`, `questions.md`, `raw.json`.
- [ ] The `report.md` for a real run has all four section headings (Snapshot, Web & infrastructure footprint, Questions to ask, Collection notes) and at least one starred question if any signal fires.
- [ ] `raw.json` has `schema_version: 1` and the questions array carries `evidence_signal` strings.
- [ ] No `.env`, `.cache/`, or `dossiers/` outputs are committed.
- [ ] The git tag `v0.1.0a0` exists.

If any of the above is not true, fix the corresponding task before declaring the plan complete.

---

## Plan-author self-review checklist (already performed)

**Spec coverage (against `docs/superpowers/specs/2026-05-23-tradecraft-design.md`):**

- §5 Architecture (plugin-based collectors, orchestrator, shared core) → Tasks 10, 11
- §5.3 HTTP client (UA, rate limit, retries, size cap, private-IP guard) → Task 8
- §5.4 Cache → Task 7
- §5.5 Ethics (robots.txt, person-name guard) → Task 9
- §6 Collectors: `footprint` only in this plan → Task 12; remaining 7 explicitly deferred to plan 2 (called out in plan header)
- §7 Analyzers: heuristic only in this plan → Tasks 13, 14; AI deferred to plan 2 (called out)
- §8 Renderers (markdown, json, questions) → Tasks 15, 16, 17
- §9 CLI surface → Task 18
- §10 Hosted preview → not in this plan; spec marks it v1.1 (called out)
- §11 Ethics posture → reflected in Task 4 docs (`ETHICS.md`, `THREAT_MODEL.md`) and code in Tasks 8, 9, 18
- §12 Config → Task 6
- §13 Caching → Task 7
- §14 Error handling → Tasks 8, 10, 11 (timed_run + retries + collector error containment)
- §15 Testing strategy → respx-based mocking throughout; live tests gated by `pytest -m live` marker (configured in Task 1)
- §16 Dependencies → Task 1 `pyproject.toml`
- §17 Repository layout → File map at top of this plan matches spec exactly (minus the deferred collectors)
- §18 README marketing plan → Tasks 4 and 20
- §19 MVP delivery order → Tasks 1-20 implement steps 1-5 of the spec's order; remaining steps in plan 2

**Placeholder scan:** Every code step shows full file content. No "similar to Task N" references. No "TBD"/"TODO" in shipped code. Test code shows real assertions, not pseudocode.

**Type consistency:** `Target`, `Findings`, `Signal`, `Question`, `CollectorResult`, `CollectorError`, `Role`, `CollectorContext`, `Collector`, `Cache`, `HttpClient`, `Orchestrator` are defined once and referenced with identical names everywhere. Method names: `Findings.collector()`, `Findings.all_signals`, `Collector.run()`, `Orchestrator.run()`, `Cache.get/set/clear`, `HttpClient.get`, `generate_questions()`, `render_markdown/json/questions`, `load_config`, `parse_robots`, `is_likely_person_name`, `timed_run`. All consistent.

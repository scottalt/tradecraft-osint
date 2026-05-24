# tradecraft — design

**Status:** Draft, awaiting user review
**Date:** 2026-05-23
**Owner:** Scott Altiparmak

## 1. What this is

`tradecraft` is a CLI (with an optional hosted preview) that produces an interview-prep dossier on a company from three inputs: company name, root URL, and a job listing URL. It takes a cybersecurity OSINT approach to gathering public information about the target, then synthesizes the findings into:

1. A structured **dossier report** the candidate can study from.
2. A set of **questions the candidate should ask in the interview**, grounded in the findings and tagged by role focus (cybersec by default, plus swe / devops / data / eng-leadership / generic).

No paid APIs are required for the core OSINT flow. Optional AI analysis is bring-your-own-key (Anthropic, OpenAI, Ollama, or any OpenAI-compatible endpoint) and never assumed.

## 2. Goals

- **One command, one dossier.** `tradecraft https://acme.com --job <url>` produces a ready-to-read folder of artifacts in under ~60 seconds for a typical target.
- **Cybersec-first, role-flexible.** Default persona is cybersecurity, but role-tagged templates and `--role` support swe / devops / data / eng-leadership / generic.
- **Free-tier only by default.** Every collector that runs without a flag must use a public source that does not require a signup, API key, or paid plan.
- **AI is additive, never load-bearing.** The tool produces useful output without any AI key. AI improves the questions section when a key is configured.
- **Legitimate use, ethical by default.** Polite scraping, identifying User-Agent, robots.txt respected, conservative per-host rate limits, no auth/paywall bypass, no bulk targeting.
- **Portfolio-grade.** Public MIT repo, README marketed to cybersec hiring managers, clean output, real demo.

## 3. Non-goals

- Not a red-team / pentest tool. No exploit attempts, no credential testing, no auth bypass.
- Not a continuous monitoring service. Single-target, single-run, no daemons.
- Not a bulk OSINT framework. Bulk mode is explicitly out.
- Not a substitute for actually preparing for the interview.
- Not an attempt to compete with paid OSINT platforms (Maltego, Recorded Future, etc.).

## 4. Audience and use cases

Primary user: a candidate (often cybersec) preparing for an interview within the next few days. They want a fast, structured brief and a list of intelligent, evidence-based questions to ask their interviewer.

Secondary user: a recruiter or founder who wants a fast snapshot of a target company. The hosted preview is sized for this audience.

Out of audience: attackers, scrapers, journalists doing dossier work on individuals. The tool refuses individual-person inputs.

## 5. Architecture

Single Python package with a plugin-based collector model. Two frontends share the same core:

```
+----------------+      +---------------+      +-------------------+
|  CLI (typer)   | ---> |  Orchestrator | <--- |  Web (Vercel fn)  |
+----------------+      +-------+-------+      +-------------------+
                                |
                +---------------+---------------+
                |                               |
        +-------v-------+              +--------v-------+
        |  Collectors   |              |   Analyzers    |
        | (plugin-based)|              | heuristic + AI |
        +-------+-------+              +--------+-------+
                |                               |
                +---------------+---------------+
                                |
                        +-------v-------+
                        |   Renderers   |
                        | markdown/json |
                        +---------------+
```

### 5.1 The Collector protocol

```python
class Collector(Protocol):
    name: str                           # short id, used in CLI flags + report
    requires_network: bool              # informational
    safe_for_hosted: bool               # gates whether the hosted preview runs it
    role_relevance: set[str]            # roles this collector primarily serves

    async def run(
        self,
        target: Target,
        http: HttpClient,
        cache: Cache,
    ) -> CollectorResult: ...
```

`Target` is `dataclass(company_name: str, root_url: str, job_url: str | None, role: str)`.

`CollectorResult` is `dataclass(name, data: dict, signals: list[Signal], errors: list[CollectorError], duration_ms: int)`.

`Signal` is a typed enum-ish marker the heuristic analyzer keys off of: `M_A_RECENT`, `BREACH_HISTORY`, `MISSING_CSP`, `OPEN_STAGING_SUBDOMAIN`, `LANGUAGES_MISMATCH_JOB`, etc. Signals are the contract between collectors and the heuristic analyzer; collectors should not depend on each other's `data` shapes.

### 5.2 Orchestrator

- Runs all enabled collectors concurrently via `asyncio.gather`.
- Skips collectors whose `requires_network` doesn't match the run mode (`--offline` future flag) and whose `safe_for_hosted` is false in hosted mode.
- Aggregates results into a `Findings` object passed to analyzers and renderers.
- Captures per-collector errors without aborting the run (one broken source must not kill the dossier).

### 5.3 HTTP client (`http.py`)

`httpx.AsyncClient` wrapped with:

- Identifying `User-Agent: tradecraft/<version> (+https://github.com/<owner>/tradecraft) interview-prep`
- Per-host token bucket rate limit (default 1 req/sec/host)
- Global concurrency cap (default 5)
- Retry-on-network-error with exponential backoff (max 3 retries)
- Honors `Retry-After` on 429/503
- Response size cap (5 MB default) to defend against hostile responses
- All responses cached through `cache.py` keyed by `(url, method, headers-subset)`

### 5.4 Cache (`cache.py`)

Filesystem cache at `~/.cache/tradecraft/`. Per-entry TTL with sensible defaults per source (DNS: 1h, crt.sh: 24h, news RSS: 1h, HTML pages: 1h, GitHub API: 1h). `--no-cache` flag bypasses. Re-runs in the same day on the same target should be near-instant.

### 5.5 Ethics module (`ethics.py`)

- `robots.txt` parser; each `http.py` request checks against the cached robots policy for the target host.
- `--ignore-robots` flag exists but requires the secondary `--i-know-what-im-doing` confirm flag, and a warning is printed.
- "Intended use" guard: if the company name input looks like a person's name (heuristic), the tool refuses with a message about scope.

## 6. Collectors

Each collector lives in its own file under `src/tradecraft/collectors/` and exports a single `Collector`-implementing class. v1 ships all eight.

### 6.1 `footprint` — web/infra fingerprint

Sources:
- DNS via local resolver: A, AAAA, MX, NS, TXT, CAA
- Subdomain enumeration via crt.sh (certificate transparency log; free, no auth)
- HTTP HEAD + GET of root: server header, framework hints (X-Powered-By, etc.), security headers (CSP, HSTS, X-Frame-Options, Referrer-Policy)
- robots.txt and sitemap.xml fetched and summarized
- TLS cert chain via direct socket (issuer, expiry, SANs)
- CDN/hosting detection by header + IP-ASN heuristic (no third-party API; uses bundled IP-to-ASN data or skips silently)

Signals: `MISSING_CSP`, `MISSING_HSTS`, `OPEN_STAGING_SUBDOMAIN` (if any subdomain matches `staging|dev|test|qa|uat`), `CERT_EXPIRING_SOON`, `EXPOSED_ADMIN_PATH` (if robots or sitemap mentions one).

Hosted-safe: yes (single domain, polite).

### 6.2 `company` — company profile from their own site

Sources:
- Root page + a small set of standard paths: `/about`, `/team`, `/leadership`, `/careers`, `/press`, `/blog`
- Pulls page titles, headings, meta descriptions, structured data (JSON-LD `Organization`)
- Extracts named people from team/leadership pages (titles, roles), products, mission statement, press mentions

Signals: `RECENT_PRESS_RELEASE`, `FOUNDER_TECHNICAL`, `PRODUCT_LIST_EMPTY` (signal that the site is sparse).

Hosted-safe: yes (polite, robots-respected, capped paths).

### 6.3 `job` — job listing parse

Sources:
- The provided `--job` URL only
- Generic HTML extractor + heuristics for greenhouse.io / lever.co / workday.com / ashbyhq.com / smartrecruiters.com (the top boards by share)

Extracts: title, location, team description, responsibilities, required skills, nice-to-haves, mentioned tech stack, salary if listed, application URL.

Cross-references the extracted stack with `footprint` and `github` findings to compute a `LANGUAGES_MISMATCH_JOB` or `STACK_ALIGNMENT_STRONG` signal.

Hosted-safe: yes.

### 6.4 `news` — news and mentions

Sources:
- Google News RSS (`news.google.com/rss/search?q=<company>`)
- Hacker News Algolia API (free, no auth)

Extracts: last ~30 days of headlines, deduplicated, with date and source. Builds a small timeline.

Signals: `RECENT_LAYOFFS`, `RECENT_FUNDING`, `RECENT_LEADERSHIP_CHANGE`, `RECENT_SECURITY_INCIDENT` (keyword match in headlines).

Hosted-safe: no (RSS fetches and HN searches across the open web get rate-limited fast from shared IPs).

### 6.5 `breaches` — breach history

Sources:
- Have I Been Pwned free unauthenticated domain endpoint where available; otherwise the public breach list filtered by domain match
- Public databreaches.net feed if available without auth

Extracts: known breach events involving the company's domain, dates, exposure types.

Signals: `BREACH_HISTORY`, `BREACH_RECENT` (within 24 months).

Hosted-safe: no (HIBP rate limits + key requirements on some endpoints; safer to keep in CLI).

### 6.6 `github` — public GitHub presence

Sources:
- GitHub REST API (public endpoints; no token required, but supports `GITHUB_TOKEN` for higher rate limits)
- Search for an org matching the company name; if found, list public repos, languages, contributors, recent activity

Extracts: repo count, primary languages by LOC, active contributors (last 90d), notable repos (most stars), open issue counts.

Signals: `LANGUAGES_MISMATCH_JOB`, `STACK_ALIGNMENT_STRONG`, `OSS_FORWARD_CULTURE` (if many public repos and active), `NO_PUBLIC_GITHUB` (notable absence).

Hosted-safe: yes (single org lookup, capped).

### 6.7 `people` — publicly attributed people signals

Sources:
- Engineering blog post authors (parsed from the company's `/blog`)
- Conference talk speakers from public conference sites (DEF CON, BSides, RSA, KubeCon, Strange Loop, etc. — bundled list of speaker indexes that are free to scrape)
- Public GitHub org member list (those who chose to be public)

**Explicitly out:** LinkedIn scraping (ToS), email enumeration, breach-database pivot to individuals.

Extracts: small list of identifiable engineers, the work they've publicly shared, areas of focus.

Signals: `STRONG_ENG_BRAND` (multiple public talks/posts), `QUIET_ENG_BRAND` (few or none).

Hosted-safe: no.

### 6.8 `business` — business and financial signals

Sources:
- SEC EDGAR for public companies (free, no auth, well-documented)
- Wikipedia infobox for company snapshot if a page exists (size, founding date, parent company)
- Glassdoor public review pages (titles and summary stats only; no review-by-review scrape)

Signals: `PUBLIC_COMPANY`, `RECENT_10K`, `WIKIPEDIA_INFOBOX_PRESENT`, `GLASSDOOR_RATING_LOW`.

Hosted-safe: no.

### 6.9 `ma` — mergers and acquisitions signals

Sources:
- News headlines from `news` collector filtered for M&A keywords (acquires, merges with, acquired by)
- Wikipedia infobox parent / subsidiaries fields
- SEC EDGAR 8-K filings for public companies

Extracts: known acquisitions with date and counterparty; parent-company relationships.

Signals: `M_A_RECENT` (within 18 months), `M_A_FREQUENT_ACQUIRER`, `SUBSIDIARY_OF`.

Hosted-safe: no.

## 7. Analyzers

### 7.1 Heuristic analyzer (`analyzers/heuristics.py`)

Pure-Python templates fired by `Signal` matches. Each template has:

```python
@dataclass
class QuestionTemplate:
    signal: Signal | tuple[Signal, ...]
    roles: set[str]                       # which --role values activate this
    text: str                             # may include {placeholders} bound from Findings
    confidence: Literal["high", "med", "low"]
    source: str                           # which collector's signal triggered it
```

Examples:

- `signal=M_A_RECENT, roles={cybersecurity, generic}, text="I saw you acquired {target} in {month}. How is the SOC / identity / vendor-security integration going?"`
- `signal=MISSING_CSP, roles={cybersecurity, swe}, text="Your main site doesn't ship a Content-Security-Policy header. Is that a deliberate posture, or something the team is working toward?"`
- `signal=OPEN_STAGING_SUBDOMAIN, roles={cybersecurity}, text="I noticed {host} appears in public CT logs. Does the team have a stance on pre-prod exposure hygiene?"`
- `signal=LANGUAGES_MISMATCH_JOB, roles={swe, devops, cybersecurity}, text="The JD calls for {job_lang}, but your public repos skew {gh_lang}. Is the team mid-migration, or is {job_lang} for a specific new initiative?"`
- `signal=RECENT_LEADERSHIP_CHANGE, roles={generic}, text="{name} joined as {title} {timeframe}. How has that shifted what the team is prioritizing?"`

Output: a list of `Question` objects with `text, confidence, role_tags, evidence` (the signal + collector source that triggered it). Top 3 by confidence are starred.

### 7.2 AI analyzer (`analyzers/ai.py`)

Activated only if a provider+key is configured. Receives `Findings` + role + already-generated heuristic questions. Produces a "Deep dive" section of additional questions tailored to the role and the unique angles in the findings (things heuristics can't catch — narrative connections, role-fit nuance, "tell me about a time..." style follow-ups). Output appended to `questions.md` under a distinct heading.

The prompt explicitly instructs the model to:

1. Not duplicate any heuristic question.
2. Cite which finding supports each question.
3. Stay in candidate-asking-interviewer mode (not the other way around).

A prompt cache (Anthropic) / cache-control header is set on the bulk Findings payload so iterative tuning doesn't re-pay.

### 7.3 Provider adapters (`providers/`)

Four adapters share an interface:

```python
class Provider(Protocol):
    async def generate(self, system: str, prompt: str, max_tokens: int) -> str: ...
```

- `anthropic.py` — `ANTHROPIC_API_KEY`, defaults to `claude-sonnet-4-6`, optional `claude-opus-4-7`.
- `openai.py` — `OPENAI_API_KEY`, configurable model.
- `ollama.py` — `OLLAMA_HOST` (default `http://localhost:11434`), configurable model.
- `openai_compat.py` — `OPENAI_COMPAT_BASE_URL` + `OPENAI_COMPAT_KEY` + model. Catches OpenRouter, Groq, LM Studio, vLLM, etc.

Provider selected by `--ai <provider>` flag or `TRADECRAFT_AI_PROVIDER` env var. Tool prints "AI analysis disabled (no provider configured)" when not configured and continues.

## 8. Renderers

### 8.1 Markdown (`renderers/markdown.py`)

Single `report.md` with this section order:

1. **Snapshot** — company name, one-line description, primary tech stack, headquarters, size if known
2. **Role-fit summary** — derived from `job` × `footprint`/`github` cross-reference
3. **Web & infrastructure footprint** — DNS, subdomains, security headers, TLS posture
4. **Company profile** — about/team/products from their site
5. **News & timeline** — last 30-90 days
6. **People** — publicly identifiable engineers, areas of focus
7. **Business & M&A** — funding, filings, acquisitions, subsidiaries
8. **Breach history** — if any
9. **Questions to ask** — heuristic-baseline list, then "Deep dive (AI)" if available

Each section starts with a 1-2 sentence "what this tells you" sentence, then the data.

### 8.2 JSON (`renderers/json.py`)

`raw.json` is the full `Findings` dump (every collector's `data`, every `signal`, every `error`, run metadata). Stable schema, versioned with a `schema_version: 1` field at the top. Allows re-rendering or re-feeding AI without re-scraping.

### 8.3 Questions standalone (`renderers/questions.py`)

`questions.md` — only the questions section from the markdown report, role-tagged, ready to print or paste into notes.

### 8.4 Output folder

`./dossiers/<company-slug>-<YYYY-MM-DD>/` containing `report.md`, `questions.md`, `raw.json`, and a `run.log` (timestamps, per-collector timings, errors).

## 9. CLI surface

Powered by `typer`.

```
$ tradecraft <root-url> [OPTIONS]

  Build an interview-prep dossier for the company at <root-url>.

Options:
  --job URL                  Job listing URL (strongly recommended)
  --role TEXT                cybersecurity | swe | devops | data | eng-leadership | generic
                             [default: cybersecurity]
  --company TEXT             Override the inferred company name
  --output PATH              Output folder root [default: ./dossiers]
  --only LIST                Run only these collectors (comma-separated)
  --skip LIST                Skip these collectors
  --no-cache                 Bypass the on-disk cache for this run
  --ai PROVIDER              anthropic | openai | ollama | openai-compat
  --ai-model TEXT            Override the default model for the provider
  --polite/--aggressive      Rate-limit posture [default: polite]
  --ignore-robots            Ignore robots.txt (requires --i-know-what-im-doing)
  --i-know-what-im-doing     Confirm risky flags
  --json                     Print raw.json to stdout instead of writing a folder
  --verbose / -v             Log every HTTP request
  --version
  --help
```

Subcommands (v1.1+, not in MVP):

- `tradecraft providers test` — verify configured AI provider works
- `tradecraft cache clear` — wipe the on-disk cache
- `tradecraft preview <run-folder>` — re-render a past run without re-scraping

## 10. Hosted preview (`tradecraft.dev`)

**Purpose:** marketing + zero-install demo. Deliberately narrower than the CLI to keep legal and operational risk low.

### 10.1 What it runs

Only collectors with `safe_for_hosted = True`:

- `footprint` (single domain, polite)
- `company` (single domain, robots-respected, capped paths)
- `job` (single user-provided URL)
- `github` (single org lookup)

Everything else surfaces a "Install the CLI for the full dossier" CTA in the relevant section.

### 10.2 BYOK AI in the browser

If the user pastes an API key into the form, the server proxies one request to the configured provider and discards the key. The key is:

- never logged
- never written to disk
- not stored in a session
- present only for the lifetime of the single request

Disclaimer text appears next to the key field. Default UX is "skip AI, see the heuristic questions only."

### 10.3 Stack

- Next.js App Router on Vercel (frontend + API routes)
- Python Vercel Function (Fluid Compute, Python 3.13) for the OSINT engine — imports the same `tradecraft` package
- Per-IP rate limit at the Vercel Edge / Routing Middleware layer (e.g., 3 dossiers per IP per hour) — defends our hosting bill and the upstream sources
- Vercel BotID enabled to deflect drive-by abuse
- `vercel.ts` for project config (per house preference)

### 10.4 Not in MVP

The hosted version is **v1.1**. MVP ships the CLI complete. Web is plumbed for in the architecture (shared core) but not built until the CLI is solid.

## 11. Ethics and legal posture

The README ships a visible "Intended use" section, summarized:

- This is interview-prep tooling. Use it on companies you are legitimately interviewing with.
- Every request the tool makes is identifiable as `tradecraft` via the User-Agent. Hosts can block easily.
- `robots.txt` is respected by default.
- Per-host rate limits are conservative by default.
- No authentication, paywall, or rate-limit bypass logic exists in the codebase. Adding one is out of scope and PRs adding one will be rejected.
- No bulk mode. The CLI accepts a single target per invocation.
- The hosted version runs a deliberately narrow subset of collectors against sources that explicitly permit programmatic access.

A `SECURITY.md` documents the responsible-use policy and a `THREAT_MODEL.md` (in `/docs`) describes what the tool will not do.

## 12. Configuration

Two layers:

1. **Per-run flags** (above).
2. **User config file** at `~/.config/tradecraft/config.toml`:

```toml
[ai]
provider = "anthropic"
model = "claude-sonnet-4-6"

[http]
per_host_rps = 1.0
global_concurrency = 5
max_response_bytes = 5_242_880

[cache]
enabled = true
ttl_default_seconds = 3600
```

Env vars supported for keys and for CI-friendly override of any config key (`TRADECRAFT_<SECTION>_<KEY>`).

## 13. Caching

- All HTTP responses cached by default at `~/.cache/tradecraft/responses/`.
- Per-source TTL configurable; sensible defaults baked in.
- Cache keys include the URL, method, and a small set of headers that affect response content.
- `--no-cache` disables for the run.
- `tradecraft cache clear` (v1.1) wipes.

## 14. Error handling

- A failing collector emits a `CollectorError` into its `CollectorResult`; orchestrator continues with other collectors.
- A failing AI provider falls back to heuristic-only and logs a warning.
- Network-level errors retry with backoff up to 3 times; permanent failures are recorded in `run.log` and surfaced in the report's "Collection notes" footer.
- Unexpected exceptions in the orchestrator itself print a structured error with `--verbose` showing the traceback; the partial dossier is still written so the user gets something.

## 15. Testing strategy

- **Per-collector unit tests** with `respx` mocking httpx. Each collector has at least one happy-path test, one empty-response test, one timeout test.
- **Recorded fixtures** for representative responses from crt.sh, GitHub API, greenhouse.io, etc., stored under `tests/fixtures/`. **No live network in CI.**
- **Orchestrator tests** with all collectors mocked, verifying signal aggregation, error containment, and `Findings` shape.
- **Heuristic analyzer tests** are pure functions: synthetic `Findings` → expected questions.
- **Provider adapter tests** mock each provider's API; one `pytest -m live` suite gated on env vars allows manual end-to-end verification.
- **CLI tests** via `typer.testing.CliRunner`.
- Target overall coverage: ~80% on `src/tradecraft/`, ~95% on `analyzers/heuristics.py`.

## 16. Dependencies

Runtime:

- `httpx[http2]` — async HTTP
- `selectolax` — fast HTML parsing (faster than BeautifulSoup, MIT-licensed)
- `dnspython` — DNS lookups
- `feedparser` — RSS
- `typer` — CLI
- `rich` — pretty terminal output
- `pydantic` — config + data models
- `tomli` (Python 3.10 fallback; native in 3.11+) — config file parsing

AI providers (optional, lazy-imported so missing one doesn't break the rest):

- `anthropic`
- `openai` (also used for openai-compat)
- `httpx` already covers ollama (no SDK needed for the simple JSON API)

Dev:

- `pytest`, `pytest-asyncio`, `respx`, `coverage`, `ruff`, `mypy`, `pre-commit`

Packaging:

- `pyproject.toml` with `hatchling` build backend
- `uv` recommended for the dev loop (lock file: `uv.lock`)
- Distributed on PyPI as `tradecraft` (if available) or `tradecraft-osint` as fallback
- `pipx install tradecraft` is the documented install method

## 17. Repository layout

```
tradecraft/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # lint, typecheck, test
│   │   └── release.yml             # publish to PyPI on tag
│   └── ISSUE_TEMPLATE/
├── docs/
│   ├── superpowers/
│   │   ├── specs/                  # design docs (this file)
│   │   └── plans/                  # implementation plans
│   ├── ETHICS.md
│   └── THREAT_MODEL.md
├── src/
│   └── tradecraft/
│       ├── __init__.py
│       ├── cli.py
│       ├── orchestrator.py
│       ├── http.py
│       ├── cache.py
│       ├── ethics.py
│       ├── config.py
│       ├── models.py               # Target, Findings, Signal, Question, ...
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── footprint.py
│       │   ├── company.py
│       │   ├── job.py
│       │   ├── news.py
│       │   ├── breaches.py
│       │   ├── github.py
│       │   ├── people.py
│       │   ├── business.py
│       │   └── ma.py
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── heuristics.py
│       │   ├── templates.py        # the QuestionTemplate library
│       │   └── ai.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   ├── ollama.py
│       │   └── openai_compat.py
│       └── renderers/
│           ├── __init__.py
│           ├── markdown.py
│           ├── json.py
│           └── questions.py
├── tests/
│   ├── fixtures/
│   ├── collectors/
│   ├── analyzers/
│   ├── providers/
│   ├── renderers/
│   └── cli/
├── web/                            # v1.1 — Next.js + Vercel Python Function
├── LICENSE                          # MIT
├── README.md
├── SECURITY.md
├── pyproject.toml
└── uv.lock
```

## 18. README marketing plan

The README is part of the product. It must:

- Open with a one-line tagline and a terminal-cast GIF (asciinema → SVG) of a real run
- Show a sample report excerpt and a sample questions excerpt in the first scroll
- Document the BYOK options clearly with a one-line "no key? still useful" callout
- Have a visible "Ethics & Intended Use" section above the install instructions
- Badge row: License, Python version, CI, PyPI version, downloads
- "Why tradecraft?" three-bullet section: free, role-tagged, evidence-cited questions
- Roadmap section calling out the hosted preview

## 19. MVP delivery order

1. Repo scaffold: `pyproject.toml`, `src/tradecraft/`, `tests/`, MIT LICENSE, README skeleton, CI workflow, `ruff`/`mypy` config
2. Core models: `Target`, `Findings`, `Signal`, `Question`, `CollectorResult`
3. `http.py` + `cache.py` + `ethics.py` + `config.py`
4. `Collector` protocol + `Orchestrator`
5. Collectors in this order: `footprint`, `company`, `job`, `github`, `news`, `breaches`, `business`, `ma`, `people`
6. `analyzers/heuristics.py` + `analyzers/templates.py` (template library grows alongside each collector)
7. Renderers: `markdown.py`, `json.py`, `questions.py`
8. `cli.py` (typer)
9. AI providers + `analyzers/ai.py`
10. README polish + demo asciinema + first PyPI release (v0.1.0)
11. (v1.1) `web/` — Next.js + Vercel Python Function

## 20. Out of scope (explicit)

- Continuous monitoring / scheduled runs
- Multi-target / bulk mode
- LinkedIn or any social-network scraping
- Individual-person OSINT
- Authentication bypass, paywall bypass, credential testing
- Active scanning (port scans, dirbusting, fuzzing)
- Browser-based dynamic rendering (Playwright/Selenium) — adds weight and ToS exposure; static HTML only in v1

## 21. Open questions / decisions to revisit

- **PyPI name availability** — verify `tradecraft` is free; fallback `tradecraft-osint` if not.
- **GitHub repo name** — `tradecraft` if available on Scott's account; otherwise `Tradecraft` or `tradecraft-cli`.
- **Hosted domain** — `tradecraft.dev` availability check; fallback `usetradecraft.com`. Not blocking the CLI MVP.
- **Heuristic template library** — first pass will be ~30 templates. Grows organically as we use the tool on real interviews.
- **Wikipedia scraping politeness** — confirm Wikipedia's User-Agent and rate-limit guidelines before shipping the `business` and `ma` collectors that use it.

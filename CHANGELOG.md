# Changelog

All notable changes to this project will be documented here. Follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Evidence-driven interview questions.** News headlines, M&A facts, and
  JD stack keywords are now cited inline in the generated question text —
  with date, source, and a clickable link (e.g. _"I saw 'Acme Corp lays
  off 12% of security team…' (Google News, 2026-05-26). How has scope
  shifted?"_). Templates that lack real evidence to cite are suppressed
  entirely rather than emitting boilerplate.
- **Content-density note.** When no evidence-backed questions fire, the
  questions section shows a one-line nudge ("Limited recent public material
  … add a job URL or run the full CLI") instead of padding with config
  trivia.
- **`JOB_STACK_LISTED` signal** emitted by the `job` collector when the JD
  names specific technologies; used by new stack-awareness question templates.
- **`news` + `ma` collectors enabled on the hosted Vercel site.** The
  deployment now runs six `safe_for_hosted=True` collectors: `footprint`,
  `company`, `job`, `github`, `news`, `ma`. Both new collectors hit only
  public read-only aggregators (Google News RSS, HN Algolia, Wikipedia) and
  never the target's own servers, keeping the hosted posture safe.
- **News collector recency + relevance filtering.** Items older than 365 days
  are dropped; items without a company-name match are filtered out, reducing
  false positives in the evidence cache.

### Changed

- **Evidence-backed questions sort first, then by confidence.** Questions
  citing real news/M&A/JD evidence appear at the top of every section;
  config-only signals rank below them regardless of their individual
  confidence level.
- **Security-config templates demoted to `confidence="low"`.** Templates
  for missing CSP/HSTS, exposed staging subdomains, certificate expiry, and
  open admin paths are now secondary material. They still appear in the
  dossier but no longer dominate the top-picks list.

### Security

- **News evidence URLs scheme-validated (http/https only)** at ingest in the
  `news` collector and in the web UI renderer. Feed links are untrusted
  user-facing input; this blocks `javascript:` and `data:` URIs from
  appearing as clickable evidence citations, preventing XSS through the
  evidence footnote.

## [1.1.0] - 2026-05-30

### Added

- **Live design preview at https://scottalt.github.io/tradecraft-osint/.**
  Next.js 16 + Tailwind v4 static export deployed to GitHub Pages via
  `.github/workflows/deploy-pages.yml`. The UI is fully interactive but
  the form is inert (no backend on Pages); it exists to demonstrate the
  distinctive "Field Dossier" visual style — manila paper, Special Elite
  typewriter type, JetBrains Mono data tables, classification stamps.
  Explicitly NOT a generic shadcn default UI.
- **Full hosted version live at https://tradecraft-osint.vercel.app/.** The
  same Next.js app plus two Vercel Python Functions: `/api/compile` runs the
  four `safe_for_hosted=True` collectors (footprint, company, job, github);
  `/api/ai` proxies BYOK AI. The vendored `tradecraft` package is committed
  at `web/api/_vendor/tradecraft/` so the deploy works with no advanced
  Vercel configuration. See `web/DEPLOY.md` for the one-click redeploy URL.
- **BYOK AI proxy at `/api/ai`.** Accepts a provider + key + prompt from the
  browser, calls the provider, returns the response. The key is forwarded once
  and never stored, logged, or written to disk. SSRF guards reject loopback,
  private, link-local, multicast, and reserved IP ranges on user-supplied
  `base_url`. Generic error replies (no upstream exception details echoed).
  Supports Anthropic (with `cache_control: ephemeral` prompt caching) and
  OpenAI-compatible endpoints.
- **Per-IP rate limit on `/api/compile`:** 3 requests / IP / hour, enforced in
  Routing Middleware. In-memory window (acceptable for demo traffic; upgrade to
  Upstash Redis if it ever needs to scale).
- **SSRF guards on `/api/compile`:** user-supplied `root_url` / `job_url` must
  use http(s) and resolve to public IPs before the orchestrator runs.

### Versioning note

Jumped from 0.3.0 to 1.1.0 to reflect the "CLI + hosted web" milestone that
was planned from day one. v1.0.0 is implicitly the CLI-feature-complete
snapshot at tag v0.3.0.

## [0.3.0] - 2026-05-30

### Added

- BYOK AI deep-dive question layer. Pass `--ai <provider>` to append
  a `Deep dive (AI)` subsection to the questions section, with synthesized,
  role-tailored questions the heuristic engine couldn't produce.
- Four provider adapters:
  - `anthropic` (Anthropic Claude, default `claude-sonnet-4-6`) — uses
    `cache_control: ephemeral` on the Findings payload so iterative tuning
    is cheap.
  - `openai` (OpenAI, default `gpt-4o`).
  - `ollama` (local-only, no key needed, default `llama3.1:8b`).
  - `openai-compat` (OpenRouter / Groq / LM Studio / vLLM / anyone speaking
    the OpenAI chat-completions API).
- New optional-dependencies extra `[ai]` so `pipx install 'tradecraft[ai]'`
  pulls the Anthropic and OpenAI SDKs. Ollama and openai-compat (via the
  openai SDK) work without extras.
- `--ai-model` flag overrides the provider's default model.

### Changed

- `Question.evidence_signal` is now optional (AI-generated questions don't
  cite a Signal; they cite "AI deep-dive" in the rendered footnote instead).

### Deferred

- Cross-collector signals (`LANGUAGES_MISMATCH_JOB` / `STACK_ALIGNMENT_STRONG`)
  remain pending until `findings_so_far` is wired through `CollectorContext`.
- Hosted web preview ships in v1.1.

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

## [0.1.0a1] - 2026-05-25

Surfaced by the first real-world test run (against a PE firm's public surface).
Both fixes are silent-failure bugs: the old code returned an empty result with
no error, masking the underlying problem.

### Fixed

- **robots.txt enforcement is now target-scoped.** The previous release
  respected robots on every host the tool called, including documented
  OSINT-API services (crt.sh, GitHub API, Wikipedia). Real targets often
  have a strict robots policy on those services, so subdomain enumeration
  silently produced zero results. robots.txt now applies only to the
  `--target` host and its subdomains; third-party APIs we use as tools are
  exempt. New `HttpClient(target_host=...)` parameter; CLI passes it
  automatically. (`src/tradecraft/http.py`)
- **Pre-prod subdomain detection now catches dashed forms.** Replaced the
  `startswith("staging.", "dev.", ...)` check with a word-boundary regex
  (`\b(staging|dev|test|qa|uat|sandbox|preview)\b`) applied to the leftmost
  label. Now catches `staging-br.example.com`, `subscribe-qa.example.com`,
  `dev-portal.example.com` (which were 100% missed before) while preserving
  the false-negative guard for `developer.example.com`, `devops.example.com`,
  `testimonials.example.com`. (`src/tradecraft/collectors/footprint.py`)

### Positioning

tradecraft's primary persona is **cybersecurity interview prep** (offensive,
defensive, AppSec, security leadership). Non-cybersec roles (swe, devops,
data, eng-leadership) get progressively reduced template coverage by design
for now — broader role coverage is a post-v0.2.0 concern. If you run
`--role data` against the current release, expect a sparse questions
section; that's expected, not a bug.

## [0.1.0-alpha] - 2026-05-24

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

### Fixed (pre-tag review)

- HTTP client now enforces robots.txt for every fetched host (per-host policy
  cache, fail-open on robots fetch error). `respect_robots=False` constructor
  flag bypasses for tests.
- Relative `Location` headers in redirects are now absolutized against the
  request URL before the private-IP guard runs (prevents bypass via a server
  that redirects to a relative path resolving to a link-local IP).
- Redirect chains capped at `max_redirects` (default 5), separate from
  `max_retries`.

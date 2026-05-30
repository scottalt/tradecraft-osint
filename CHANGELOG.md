# Changelog

All notable changes to this project will be documented here. Follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Known limitations

- The `data` role still has near-zero question coverage. The `footprint`
  signals (`missing_csp`, `missing_hsts`, `open_staging_subdomain`) are tagged
  for cybersec/devops only. A real-world run with `--role data` still yields
  an empty questions section. v0.2.0 will broaden the template library.

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

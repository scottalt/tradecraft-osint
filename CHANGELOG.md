# Changelog

All notable changes to this project will be documented here. Follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

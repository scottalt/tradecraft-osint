# tradecraft

> Recon your future employer before the interview.

`tradecraft` is an OSINT CLI built for **cybersecurity interview prep**. It maps a company's public attack surface, fingerprints its tech and security posture, and produces **evidence-cited questions to ask in the interview** — questions that demonstrate you did the reconnaissance work most candidates skip.

Designed for offensive, defensive, AppSec, and security-leadership roles. Broader role coverage (swe, devops, data, eng-leadership) is a v0.2.x+ concern.

Free public sources only. No paid APIs required. Optional AI analysis via your own key (Anthropic, OpenAI, Ollama, or any OpenAI-compatible endpoint).

## Status

**Alpha (v0.1.0a1)** — walking skeleton with the `footprint` collector wired end-to-end. The remaining collectors (`breaches`, `github`, `news`, `company`, `job`, `people`, `business`, `m&a` — cybersec-prioritized order) and the BYOK AI analyzer ship in v0.2.0. Hosted web preview ships in v1.1.

[![CI](https://github.com/scottalt/tradecraft-osint/actions/workflows/ci.yml/badge.svg)](https://github.com/scottalt/tradecraft-osint/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
- `report.md` — sectioned dossier (snapshot, footprint, questions)
- `questions.md` — questions to ask in the interview
- `raw.json` — full structured findings

See `tradecraft --help` for all flags.

## What it surfaces

Even the walking-skeleton release (one collector, no AI) finds material recon signals against real targets. Example findings from a real run against a Fortune 500 PE firm:

- 31 subdomains pulled from certificate transparency logs
- 5 pre-prod hostnames (`staging-*`, `*-qa`, `*-uat`) exposed in public CT
- Missing HSTS header on the apex
- Email security gateway (Mimecast) detected from MX records
- Premium enterprise DNS registrar (MarkMonitor) detected — signals brand-protection investment
- 10+ vendor relationships extracted from DNS TXT verification tokens (Anthropic, OpenAI, Microsoft, Cisco, Zoom, DocuSign, Calendly, ...) — v0.2.0 will turn these into role-fit questions

## Sample output

```
$ tradecraft https://example.com --company "Example" --role cybersecurity

Dossier written to ./dossiers/example-2026-05-25/
```

`./dossiers/example-2026-05-25/report.md` (excerpt):

```markdown
# Example

## Snapshot
- URL: https://example.com/
- Role focus: `cybersecurity`

## Web & infrastructure footprint
- Host: `example.com`
- Server header: `cloudflare`
- Security headers present: _none_

### Signals
- `missing_csp`
- `missing_hsts`

## Questions to ask

### Top picks
- **Your main site doesn't ship a Content-Security-Policy header.
  Is that a deliberate posture, or is the team working toward one?**
  _confidence:_ `med` · _evidence:_ `missing_csp` from `footprint` · _roles:_ `cybersecurity` `swe`
- **I noticed your apex doesn't return Strict-Transport-Security.
  How does the team think about transport hardening across subdomains?**
  _confidence:_ `med` · _evidence:_ `missing_hsts` from `footprint` · _roles:_ `cybersecurity` `devops`
```

## Intended use

This is **interview preparation tooling**. Use it on companies you are legitimately interviewing with. The tool identifies itself in every request, scopes `robots.txt` enforcement to the target's host by default, rate-limits politely, and contains no authentication, paywall, or rate-limit bypass logic. See [`docs/ETHICS.md`](docs/ETHICS.md) and [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).

## License

MIT — see [`LICENSE`](LICENSE).

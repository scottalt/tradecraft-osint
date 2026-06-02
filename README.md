# tradecraft

> Recon your future employer before the interview.

`tradecraft` is an OSINT CLI built for **cybersecurity interview prep**. It maps a company's public attack surface, fingerprints its tech and security posture, and produces **evidence-cited questions to ask in the interview** — questions that demonstrate you did the reconnaissance work most candidates skip.

Designed for offensive, defensive, AppSec, and security-leadership roles. Broader role coverage (swe, devops, data, eng-leadership) is a v0.2.x+ concern.

Free public sources only. No paid APIs required. Optional AI analysis via your own key (Anthropic, OpenAI, Ollama, or any OpenAI-compatible endpoint).

## Status

**v1.1.0** — full CLI + hosted web. CLI: all 9 collectors + BYOK AI deep-dive
layer (`--ai anthropic|openai|ollama|openai-compat`). Web: live design preview
at https://scottalt.github.io/tradecraft-osint/ (static export, distinctive
Field Dossier visual style); full backend version with `/api/compile` +
BYOK AI proxy **live at https://tradecraft-osint.vercel.app/**.

[![CI](https://github.com/scottalt/tradecraft-osint/actions/workflows/ci.yml/badge.svg)](https://github.com/scottalt/tradecraft-osint/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Install

Not yet on PyPI — install directly from GitHub:

```bash
# Core CLI (heuristic questions only)
pipx install git+https://github.com/scottalt/tradecraft-osint.git

# Plus BYOK AI providers (Anthropic, OpenAI, OpenAI-compatible)
pipx install 'tradecraft[ai] @ git+https://github.com/scottalt/tradecraft-osint.git'

# Ollama works out of the box with the core install — no extra package needed.
```

Once published to PyPI (planned), `pipx install tradecraft` will be the canonical
install command.

### AI providers (BYOK)

`tradecraft` never talks to AI providers unless you pass `--ai`. Set one
of the following env-var groups before running:

| Provider | Env vars | Model flag |
|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | `--ai-model claude-sonnet-4-6` |
| `openai` | `OPENAI_API_KEY` | `--ai-model gpt-4o` |
| `ollama` | `OLLAMA_HOST` (default `http://localhost:11434`) | `--ai-model llama3.1:8b` |
| `openai-compat` | `OPENAI_COMPAT_BASE_URL` + `OPENAI_COMPAT_KEY` + `TRADECRAFT_AI_OPENAI_COMPAT_MODEL` | `--ai-model <model>` |

Example:

```bash
export ANTHROPIC_API_KEY=...
tradecraft https://acme.com --ai anthropic
```

## Hosted

**Live, fully functional:** https://tradecraft-osint.vercel.app/

The Vercel deployment runs six `safe_for_hosted=True` collectors
(`footprint`, `company`, `job`, `github`, `news`, `ma`) via Python
Functions at `/api/compile`, plus a BYOK AI proxy at `/api/ai` (key
forwarded once, never stored). Submit a target in the Field Dossier form
and get a real dossier rendered inline — news and M&A findings surface as
clickable citations in the generated questions. The `news` and `ma`
collectors are safe to run hosted because they only hit public read-only
aggregators (Google News RSS, HN Algolia, Wikipedia) — never the target's
own servers.

**Design preview (static, no backend):** https://scottalt.github.io/tradecraft-osint/

The GitHub Pages mirror exists to show the design without anyone needing to
deploy. The form is inert there — points users at the CLI or the Vercel URL
above for actual reconnaissance.

For the full collector roster (breaches, people, business) plus BYOK AI
on your machine, install the CLI above. The hosted version is deliberately
narrow — see `docs/ETHICS.md`.

Source for the web app is in [`web/`](web/).

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
- **I saw "Acme Corp lays off 12% of security team amid cloud reorg" (Google News,
  2026-05-26). How has the team's scope and headcount changed, and where does
  security investment sit now?**  
  _confidence:_ `high` · _evidence:_ [Google News · 2026-05-26](https://news.google.com/rss/articles/example) · _roles:_ `cybersecurity` `security-leadership`
- **Wikipedia notes Acme Corp is a subsidiary of GlobalTech Holdings.
  How does the parent's security governance model affect your team's
  autonomy and tooling budget?**  
  _confidence:_ `high` · _evidence:_ [Wikipedia · M&A](https://en.wikipedia.org/wiki/Acme_Corp) · _roles:_ `cybersecurity` `security-leadership`

### Further questions
- **The job description lists Terraform and AWS as primary infrastructure.
  Walk me through how the security team is involved in your IaC pipeline
  today — shift-left review, policy-as-code, or something else?**  
  _confidence:_ `med` · _evidence:_ [job listing · stack](https://acme.com/careers/sec-eng) · _roles:_ `cybersecurity` `devops`
- **Your main site doesn't return a Content-Security-Policy header.
  Is that a deliberate posture for this property, or is it on the roadmap?**  
  _confidence:_ `low` · _evidence:_ `missing_csp` from `footprint` · _roles:_ `cybersecurity` `swe`
```

## Intended use

This is **interview preparation tooling**. Use it on companies you are legitimately interviewing with. The tool identifies itself in every request, scopes `robots.txt` enforcement to the target's host by default, rate-limits politely, and contains no authentication, paywall, or rate-limit bypass logic. See [`docs/ETHICS.md`](docs/ETHICS.md) and [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).

## License

MIT — see [`LICENSE`](LICENSE).

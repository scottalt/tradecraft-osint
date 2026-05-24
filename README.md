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

## Sample output

```
$ tradecraft https://example.com --company "Example"

Dossier written to ./dossiers/example-2026-05-24/
```

`./dossiers/example-2026-05-24/report.md` (excerpt):

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

This is **interview preparation tooling**. Use it on companies you are legitimately interviewing with. The tool identifies itself in every request, respects `robots.txt` by default, rate-limits politely, and contains no authentication, paywall, or rate-limit bypass logic. See [`docs/ETHICS.md`](docs/ETHICS.md).

## License

MIT — see [`LICENSE`](LICENSE).

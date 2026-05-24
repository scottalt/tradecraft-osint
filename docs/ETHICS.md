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

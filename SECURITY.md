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

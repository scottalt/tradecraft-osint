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

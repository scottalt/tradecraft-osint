"""Ethics: robots.txt parsing and intended-use guard."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RobotsPolicy:
    allows: list[str] = field(default_factory=list)
    disallows: list[str] = field(default_factory=list)

    def is_allowed(self, path: str) -> bool:
        # Longest-match wins; Allow beats Disallow on tie.
        best_len = -1
        best_allow = True
        for prefix in self.allows:
            if path.startswith(prefix) and len(prefix) > best_len:
                best_len = len(prefix)
                best_allow = True
        for prefix in self.disallows:
            if path.startswith(prefix) and len(prefix) >= best_len:
                # >= so Allow wins ties only when strictly longer.
                # Equal-length: Disallow wins per RFC 9309 ambiguity; we choose to
                # let Allow win when it appeared with the same prefix length first.
                if len(prefix) > best_len:
                    best_len = len(prefix)
                    best_allow = False
                elif not best_allow:
                    best_allow = False
        return best_allow


def parse_robots(robots_txt: str, user_agent: str = "*") -> RobotsPolicy:
    """Parse a robots.txt body and return the policy for the given UA.

    If the UA has a specific section, ONLY that section applies (per RFC 9309).
    Otherwise, the `*` wildcard section applies.
    """
    sections: dict[str, RobotsPolicy] = {}
    current_uas: list[str] = []
    for raw_line in robots_txt.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            ua = value.lower()
            current_uas = [ua]
            sections.setdefault(ua, RobotsPolicy())
        elif key in {"disallow", "allow"} and current_uas:
            for ua in current_uas:
                policy = sections.setdefault(ua, RobotsPolicy())
                if value:  # empty Disallow means "allow all", skip
                    if key == "disallow":
                        policy.disallows.append(value)
                    else:
                        policy.allows.append(value)

    ua_key = user_agent.lower()
    if ua_key in sections:
        return sections[ua_key]
    return sections.get("*", RobotsPolicy())


_COMPANY_HINTS = re.compile(
    r"\b(corp|corporation|inc|llc|ltd|gmbh|holdings|group|labs|systems|"
    r"technologies|solutions|software|ai|cloud|networks|security|"
    r"foundation|industries|partners|capital|ventures)\b",
    re.IGNORECASE,
)
_PERSON_RE = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$")


def is_likely_person_name(value: str) -> bool:
    """Heuristic: refuses inputs that look like an individual's name.

    Pattern: 2-4 capitalized tokens, no company-suffix words, no digits.
    """
    value = value.strip()
    if _COMPANY_HINTS.search(value):
        return False
    if any(ch.isdigit() for ch in value):
        return False
    return bool(_PERSON_RE.match(value))

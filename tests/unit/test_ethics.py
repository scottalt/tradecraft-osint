"""Tests for tradecraft.ethics."""

from __future__ import annotations

import pytest

from tradecraft.ethics import (
    is_likely_person_name,
    parse_robots,
)


def test_parse_robots_basic_disallow() -> None:
    robots_txt = """
    User-agent: *
    Disallow: /admin/
    Disallow: /private
    """
    policy = parse_robots(robots_txt)
    assert policy.is_allowed("/admin/") is False
    assert policy.is_allowed("/admin/users") is False
    assert policy.is_allowed("/public") is True
    assert policy.is_allowed("/private") is False


def test_parse_robots_allow_overrides_disallow() -> None:
    robots_txt = """
    User-agent: *
    Disallow: /
    Allow: /api/
    """
    policy = parse_robots(robots_txt)
    assert policy.is_allowed("/anything") is False
    assert policy.is_allowed("/api/foo") is True


def test_parse_empty_or_missing_robots_allows_all() -> None:
    assert parse_robots("").is_allowed("/anything") is True


def test_specific_user_agent_section_takes_precedence() -> None:
    robots_txt = """
    User-agent: *
    Disallow: /everywhere

    User-agent: tradecraft
    Disallow: /tradecraft-only
    """
    policy = parse_robots(robots_txt, user_agent="tradecraft")
    # tradecraft-specific section: /tradecraft-only disallowed, but /everywhere allowed
    assert policy.is_allowed("/tradecraft-only") is False
    assert policy.is_allowed("/everywhere") is True


@pytest.mark.parametrize(
    "name,expected",
    [
        ("John Smith", True),
        ("Mary Jane Watson", True),
        ("Acme Corp", False),
        ("Acme", False),
        ("OpenAI", False),
        ("Anthropic", False),
        ("Bill Gates Foundation", False),  # contains a company word
    ],
)
def test_is_likely_person_name(name: str, expected: bool) -> None:
    assert is_likely_person_name(name) is expected

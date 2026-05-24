"""Shared pytest fixtures for tradecraft tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to tests/fixtures/."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """Default policy; override per-test if needed."""
    return asyncio.DefaultEventLoopPolicy()

# tradecraft v0.3.0 — BYOK AI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the BYOK AI deep-dive layer. The heuristic question generator continues to run on every invocation, producing the baseline `Top picks` and `Further questions`. When the user supplies an API key (via env var) AND passes `--ai <provider>`, an AI analyzer reads the same `Findings` and the already-generated heuristic questions, then appends a `## Deep dive (AI)` section to `questions.md` and the in-report questions section with synthesized, role-tailored questions.

**Architecture:** A small `Provider` protocol with a single `async generate(system, prompt, max_tokens) -> str` method. Four adapters (`anthropic`, `openai`, `ollama`, `openai_compat`) implement the protocol. A factory function selects the adapter from a string. The AI analyzer (`analyzers/ai.py`) is a single function that takes `Findings` + heuristic `questions` + role + provider and returns a list of new `Question` objects. Lazy imports keep `anthropic` and `openai` truly optional — running tradecraft without `pip install tradecraft[ai]` works, you just can't use AI.

**Tech Stack:** Python 3.11+, `anthropic>=0.39` (optional), `openai>=1.50` (optional, also serves openai-compat), `httpx` (for ollama — no SDK needed). Anthropic prompt caching used to keep iterative AI tuning cheap.

**Spec reference:** `docs/superpowers/specs/2026-05-23-tradecraft-design.md` §7.2 (AI analyzer) and §7.3 (provider adapters).

**Out of scope (deferred):**
- Cross-collector signals like `LANGUAGES_MISMATCH_JOB` — still v0.4.0 / future.
- Hosted web preview — v1.1 (next plan after this one).
- New collectors — v0.4.0+.

---

## File map

Files to **create** in `src/tradecraft/`:

```
src/tradecraft/
├── providers/
│   ├── __init__.py
│   ├── base.py            # Provider protocol + factory
│   ├── anthropic.py       # Anthropic adapter (with prompt caching)
│   ├── openai.py          # OpenAI adapter
│   ├── ollama.py          # Ollama adapter (raw httpx, no SDK)
│   └── openai_compat.py   # OpenAI-compatible adapter (OpenRouter / Groq / etc.)
└── analyzers/
    └── ai.py              # AI analyzer wiring
```

Files to **modify** in `src/tradecraft/`:

```
src/tradecraft/
├── __init__.py            # Task 11 — version bump to 0.3.0
├── cli.py                 # Task 7 — add --ai, --ai-model flags + wire analyzer
├── renderers/markdown.py  # Task 8 — append "Deep dive (AI)" subsection to Questions
└── renderers/questions.py # Task 8 — same standalone version
```

Files to **create** in `tests/`:

```
tests/unit/providers/
├── __init__.py
├── test_anthropic.py
├── test_openai.py
├── test_ollama.py
└── test_openai_compat.py

tests/unit/analyzers/
└── test_ai.py

tests/integration/
└── test_v0_3_ai_e2e.py    # AI flow end-to-end with mocked Anthropic
```

Files to **modify** in root:

```
pyproject.toml             # Task 9 — add ai optional-dependencies extra
README.md                  # Task 11 — AI section, env var docs
CHANGELOG.md               # Task 11 — 0.3.0 entry
```

---

## Conventions used in every task

- **Test framework:** `pytest` + `pytest-asyncio` (auto mode).
- **HTTP mocking:** `respx` for adapter tests, no live network in CI.
- **Provider SDK mocking:** use `unittest.mock.AsyncMock` to stub the SDK clients so we don't need the SDKs installed in CI.
- **TDD cycle:** write failing test → confirm it fails → minimal impl → confirm it passes → commit.
- **Commits:** Conventional Commits. One commit per task.
- **Co-author trailer:** include `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` on every commit.
- **Default models per provider:** Anthropic `claude-sonnet-4-6`; OpenAI `gpt-4o`; Ollama `llama3.1:8b`; openai-compat — user must supply.

## Provider protocol (READ BEFORE EACH PROVIDER TASK)

The `Provider` protocol is intentionally minimal so the AI analyzer doesn't care which provider it's talking to. Each adapter is responsible for translating the abstract `generate(system, prompt, max_tokens)` call into its native API shape, including any provider-specific quirks (Anthropic's `cache_control`, OpenAI's `messages` format, Ollama's streaming-by-default, etc.).

```python
@runtime_checkable
class Provider(Protocol):
    name: ClassVar[str]
    default_model: ClassVar[str]
    requires_api_key: ClassVar[bool]

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str: ...

    @classmethod
    def from_env(cls, model: str | None = None) -> Provider | None:
        """Build the provider from env vars; return None if config missing."""
```

`from_env` is the construction path used by the CLI. Returns `None` when required env vars are absent so the CLI can print a clean "AI disabled" message and continue.

---

## Task 1: Provider protocol + factory

**Files:**
- Create: `src/tradecraft/providers/__init__.py`
- Create: `src/tradecraft/providers/base.py`
- Create: `tests/unit/providers/__init__.py` (empty)

- [ ] **Step 1: Write failing test**

`tests/unit/providers/__init__.py`: empty.

`tests/unit/providers/test_base.py`:

```python
"""Tests for tradecraft.providers.base."""

from __future__ import annotations

import pytest

from tradecraft.providers.base import Provider, build_provider


class FakeProvider:
    name = "fake"
    default_model = "fake-1"
    requires_api_key = False

    def __init__(self, model: str | None = None) -> None:
        self.model = model or self.default_model

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str:
        return f"system={system!r} prompt={prompt!r}"

    @classmethod
    def from_env(cls, model: str | None = None) -> "FakeProvider | None":
        return cls(model)


async def test_protocol_runtime_check() -> None:
    p = FakeProvider()
    assert isinstance(p, Provider)
    out = await p.generate("sys", "user", 100)
    assert "user" in out


def test_build_provider_dispatches_to_known_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        __import__("tradecraft.providers.base", fromlist=["_REGISTRY"]).__dict__["_REGISTRY"],
        "fake",
        FakeProvider,
    )
    p = build_provider("fake")
    assert p is not None
    assert p.name == "fake"


def test_build_provider_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown provider"):
        build_provider("does-not-exist")
```

- [ ] **Step 2: Run, confirm fail**

```
uv run pytest tests/unit/providers/test_base.py -v
```

- [ ] **Step 3: Implement `src/tradecraft/providers/__init__.py`**

```python
"""BYOK AI providers."""

from tradecraft.providers.base import Provider, build_provider

__all__ = ["Provider", "build_provider"]
```

- [ ] **Step 4: Implement `src/tradecraft/providers/base.py`**

```python
"""Provider protocol + factory.

Adapters are registered lazily so importing tradecraft.providers does NOT
import anthropic / openai SDKs — those imports happen inside the adapter
module's `from_env` classmethod, which is only called when the user
actually requests that provider via --ai.
"""

from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    name: ClassVar[str]
    default_model: ClassVar[str]
    requires_api_key: ClassVar[bool]

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str: ...

    @classmethod
    def from_env(cls, model: str | None = None) -> Provider | None: ...


# Adapter registry. Populated lazily by build_provider so optional SDK
# packages don't have to be importable at module-load time.
_REGISTRY: dict[str, type[Provider]] = {}


def build_provider(name: str, model: str | None = None) -> Provider | None:
    """Return a configured Provider instance, or None if required env vars missing.

    Raises ValueError if `name` is not a known provider key.
    """
    if name not in _REGISTRY:
        # Import the adapter module lazily; it self-registers via _register.
        _import_adapter(name)
    if name not in _REGISTRY:
        raise ValueError(f"unknown provider: {name!r}")
    return _REGISTRY[name].from_env(model)


def _register(name: str, cls: type[Provider]) -> None:
    """Adapter modules call this at import time to register themselves."""
    _REGISTRY[name] = cls


def _import_adapter(name: str) -> None:
    """Import the adapter module so it can self-register."""
    import importlib

    mapping = {
        "anthropic": "tradecraft.providers.anthropic",
        "openai": "tradecraft.providers.openai",
        "ollama": "tradecraft.providers.ollama",
        "openai-compat": "tradecraft.providers.openai_compat",
    }
    if name in mapping:
        try:
            importlib.import_module(mapping[name])
        except ImportError:
            # Adapter's SDK is missing; leave registry empty. build_provider
            # will treat this as "unknown".
            return
```

- [ ] **Step 5: Verify + commit**

```
uv run pytest tests/unit/providers/test_base.py -v
uv run ruff check src/tradecraft/providers tests/unit/providers
uv run mypy src/tradecraft/providers
```

```
git add src/tradecraft/providers/ tests/unit/providers/
git commit -m "$(cat <<'EOF'
feat(providers): Provider protocol + lazy factory

Runtime-checkable Protocol with classvar metadata (name, default_model,
requires_api_key). build_provider(name) lazy-imports the adapter
module so optional SDKs (anthropic, openai) are not required at
import time. Adapters self-register via _register().

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Anthropic adapter

**Files:**
- Create: `src/tradecraft/providers/anthropic.py`
- Create: `tests/unit/providers/test_anthropic.py`

Anthropic's API supports `cache_control` on individual message blocks. We mark the large `Findings` payload in the user prompt as cacheable so iterative tuning is cheap (5-minute TTL).

- [ ] **Step 1: Write failing test**

`tests/unit/providers/test_anthropic.py`:

```python
"""Tests for tradecraft.providers.anthropic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tradecraft.providers.anthropic import AnthropicProvider


def test_metadata() -> None:
    assert AnthropicProvider.name == "anthropic"
    assert AnthropicProvider.default_model == "claude-sonnet-4-6"
    assert AnthropicProvider.requires_api_key is True


def test_from_env_returns_none_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert AnthropicProvider.from_env() is None


def test_from_env_returns_provider_when_key_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    p = AnthropicProvider.from_env()
    assert p is not None
    assert p.model == AnthropicProvider.default_model


def test_from_env_honors_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    p = AnthropicProvider.from_env(model="claude-opus-4-7")
    assert p is not None
    assert p.model == "claude-opus-4-7"


async def test_generate_calls_sdk_with_cache_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    p = AnthropicProvider.from_env()
    assert p is not None

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="generated answer")]
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_response)
    p._client = fake_client  # noqa: SLF001 — test override

    result = await p.generate("sys-prompt", "user-prompt", 500)
    assert result == "generated answer"

    call = fake_client.messages.create.call_args
    assert call.kwargs["model"] == p.model
    assert call.kwargs["max_tokens"] == 500
    assert call.kwargs["system"] == "sys-prompt"
    # cache_control should be on the user message
    user_msg = call.kwargs["messages"][0]
    assert user_msg["role"] == "user"
    assert isinstance(user_msg["content"], list)
    assert user_msg["content"][0]["cache_control"] == {"type": "ephemeral"}
```

- [ ] **Step 2: Run, confirm fail (ModuleNotFoundError on `tradecraft.providers.anthropic` OR ImportError on `anthropic` if SDK not installed)**

```
uv run pytest tests/unit/providers/test_anthropic.py -v
```

- [ ] **Step 3: Implement `src/tradecraft/providers/anthropic.py`**

```python
"""Anthropic adapter."""

from __future__ import annotations

import os
from typing import ClassVar

from tradecraft.providers.base import _register


class AnthropicProvider:
    name: ClassVar[str] = "anthropic"
    default_model: ClassVar[str] = "claude-sonnet-4-6"
    requires_api_key: ClassVar[bool] = True

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        # Lazy: only import the SDK when an instance is built.
        import anthropic  # type: ignore[import-not-found]

        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str:
        # The user prompt block is large (Findings + heuristic questions).
        # Mark it as ephemeral-cacheable so re-runs within the 5-minute
        # window hit cache for the bulk content.
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                }
            ],
        )
        # response.content is a list of content blocks; take the first text block.
        for block in response.content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                return text
        return ""

    @classmethod
    def from_env(cls, model: str | None = None) -> AnthropicProvider | None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        return cls(api_key=api_key, model=model)


_register(AnthropicProvider.name, AnthropicProvider)
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest tests/unit/providers/test_anthropic.py -v
uv run ruff check src/tradecraft/providers/anthropic.py tests/unit/providers/test_anthropic.py
uv run mypy src/tradecraft/providers/anthropic.py
```

Note: `anthropic` SDK is in the optional `[ai]` extras (added in Task 9). For now, the test runs in the dev environment where we'll install `anthropic` directly. Add `anthropic>=0.39` to the dev deps in pyproject.toml as part of this task to enable the test path.

In `pyproject.toml`, add `"anthropic>=0.39",` to the existing `[project.optional-dependencies] dev = [...]` array. Then `uv sync --all-extras` to install.

```
git add src/tradecraft/providers/anthropic.py tests/unit/providers/test_anthropic.py pyproject.toml uv.lock
git commit -m "$(cat <<'EOF'
feat(providers): Anthropic adapter with prompt caching

claude-sonnet-4-6 default. ANTHROPIC_API_KEY from env; from_env
returns None when missing so the CLI can fall back gracefully.
User message uses cache_control: ephemeral so the bulk Findings
payload is cached for 5 minutes — iterative tuning is cheap.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: OpenAI adapter

**Files:**
- Create: `src/tradecraft/providers/openai.py`
- Create: `tests/unit/providers/test_openai.py`

- [ ] **Step 1: Write failing test**

`tests/unit/providers/test_openai.py`:

```python
"""Tests for tradecraft.providers.openai."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tradecraft.providers.openai import OpenAIProvider


def test_metadata() -> None:
    assert OpenAIProvider.name == "openai"
    assert OpenAIProvider.default_model == "gpt-4o"
    assert OpenAIProvider.requires_api_key is True


def test_from_env_returns_none_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert OpenAIProvider.from_env() is None


def test_from_env_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    p = OpenAIProvider.from_env()
    assert p is not None
    assert p.model == OpenAIProvider.default_model


async def test_generate_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    p = OpenAIProvider.from_env()
    assert p is not None

    fake_choice = MagicMock()
    fake_choice.message.content = "ai answer"
    fake_response = MagicMock(choices=[fake_choice])
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)
    p._client = fake_client  # noqa: SLF001

    result = await p.generate("sys", "user", 500)
    assert result == "ai answer"

    call = fake_client.chat.completions.create.call_args
    assert call.kwargs["model"] == p.model
    assert call.kwargs["max_tokens"] == 500
    msgs = call.kwargs["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "sys"
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "user"
```

- [ ] **Step 2: Run, confirm fail**

```
uv run pytest tests/unit/providers/test_openai.py -v
```

- [ ] **Step 3: Implement `src/tradecraft/providers/openai.py`**

```python
"""OpenAI adapter."""

from __future__ import annotations

import os
from typing import ClassVar

from tradecraft.providers.base import _register


class OpenAIProvider:
    name: ClassVar[str] = "openai"
    default_model: ClassVar[str] = "gpt-4o"
    requires_api_key: ClassVar[bool] = True

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        import openai  # type: ignore[import-not-found]

        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str:
        response = await self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        choice = response.choices[0] if response.choices else None
        if choice is None or choice.message.content is None:
            return ""
        return str(choice.message.content)

    @classmethod
    def from_env(cls, model: str | None = None) -> OpenAIProvider | None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        return cls(api_key=api_key, model=model)


_register(OpenAIProvider.name, OpenAIProvider)
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest tests/unit/providers/test_openai.py -v
uv run ruff check src/tradecraft/providers/openai.py tests/unit/providers/test_openai.py
uv run mypy src/tradecraft/providers/openai.py
```

Add `"openai>=1.50",` to dev deps in pyproject.toml. `uv sync --all-extras`.

```
git add src/tradecraft/providers/openai.py tests/unit/providers/test_openai.py pyproject.toml uv.lock
git commit -m "$(cat <<'EOF'
feat(providers): OpenAI adapter

gpt-4o default. OPENAI_API_KEY from env. Supports optional base_url
constructor arg so the openai-compat adapter (next task) can reuse
this client class for any OpenAI-compatible endpoint.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Ollama adapter

**Files:**
- Create: `src/tradecraft/providers/ollama.py`
- Create: `tests/unit/providers/test_ollama.py`

Ollama exposes `POST /api/generate` (and `/api/chat`) as a plain HTTP endpoint. No SDK required — raw httpx works.

- [ ] **Step 1: Write failing test**

`tests/unit/providers/test_ollama.py`:

```python
"""Tests for tradecraft.providers.ollama."""

from __future__ import annotations

import httpx
import pytest
import respx

from tradecraft.providers.ollama import OllamaProvider


def test_metadata() -> None:
    assert OllamaProvider.name == "ollama"
    assert OllamaProvider.default_model == "llama3.1:8b"
    assert OllamaProvider.requires_api_key is False


def test_from_env_uses_default_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    p = OllamaProvider.from_env()
    assert p is not None
    assert p.host == "http://localhost:11434"


def test_from_env_honors_host_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://gpu.lan:11434")
    p = OllamaProvider.from_env()
    assert p is not None
    assert p.host == "http://gpu.lan:11434"


@respx.mock
async def test_generate_uses_chat_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    route = respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "ai answer"}},
        )
    )
    p = OllamaProvider.from_env()
    assert p is not None
    result = await p.generate("sys", "user", 500)
    assert result == "ai answer"
    body = route.calls[0].request.read().decode()
    assert "llama3.1:8b" in body
    assert "sys" in body
    assert "user" in body
```

- [ ] **Step 2: Run, confirm fail**

- [ ] **Step 3: Implement `src/tradecraft/providers/ollama.py`**

```python
"""Ollama adapter (raw httpx, no SDK)."""

from __future__ import annotations

import os
from typing import ClassVar

import httpx

from tradecraft.providers.base import _register

_DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider:
    name: ClassVar[str] = "ollama"
    default_model: ClassVar[str] = "llama3.1:8b"
    requires_api_key: ClassVar[bool] = False

    def __init__(self, host: str, model: str | None = None) -> None:
        self.host = host.rstrip("/")
        self.model = model or self.default_model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        response = await self._client.post(f"{self.host}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        message = data.get("message") or {}
        content = message.get("content")
        return str(content) if content else ""

    @classmethod
    def from_env(cls, model: str | None = None) -> OllamaProvider | None:
        host = os.environ.get("OLLAMA_HOST", _DEFAULT_HOST)
        return cls(host=host, model=model)


_register(OllamaProvider.name, OllamaProvider)
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest tests/unit/providers/test_ollama.py -v
uv run ruff check src/tradecraft/providers/ollama.py tests/unit/providers/test_ollama.py
uv run mypy src/tradecraft/providers/ollama.py
```

```
git add src/tradecraft/providers/ollama.py tests/unit/providers/test_ollama.py
git commit -m "$(cat <<'EOF'
feat(providers): Ollama adapter (no SDK, raw httpx)

llama3.1:8b default. OLLAMA_HOST from env (default localhost:11434).
Posts to /api/chat with stream=false; reads message.content from the
JSON response. No API key required. Truly local-only AI.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: OpenAI-compat adapter

**Files:**
- Create: `src/tradecraft/providers/openai_compat.py`
- Create: `tests/unit/providers/test_openai_compat.py`

Reuses the `openai` SDK with a custom `base_url`. Works with OpenRouter, Groq, LM Studio, vLLM, anyone exposing the OpenAI chat-completions API.

- [ ] **Step 1: Write failing test**

`tests/unit/providers/test_openai_compat.py`:

```python
"""Tests for tradecraft.providers.openai_compat."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tradecraft.providers.openai_compat import OpenAICompatProvider


def test_metadata() -> None:
    assert OpenAICompatProvider.name == "openai-compat"
    assert OpenAICompatProvider.requires_api_key is True
    # No default model — user must supply.
    assert OpenAICompatProvider.default_model == ""


def test_from_env_requires_base_url_and_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_COMPAT_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_COMPAT_KEY", raising=False)
    monkeypatch.delenv("TRADECRAFT_AI_OPENAI_COMPAT_MODEL", raising=False)
    assert OpenAICompatProvider.from_env() is None


def test_from_env_returns_when_all_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_KEY", "sk-test")
    monkeypatch.setenv("TRADECRAFT_AI_OPENAI_COMPAT_MODEL", "test-model")
    p = OpenAICompatProvider.from_env()
    assert p is not None
    assert p.model == "test-model"


async def test_generate_calls_chat_completions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_KEY", "sk-test")
    monkeypatch.setenv("TRADECRAFT_AI_OPENAI_COMPAT_MODEL", "test-model")
    p = OpenAICompatProvider.from_env()
    assert p is not None

    fake_choice = MagicMock()
    fake_choice.message.content = "compat answer"
    fake_response = MagicMock(choices=[fake_choice])
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)
    p._client = fake_client  # noqa: SLF001

    result = await p.generate("s", "u", 100)
    assert result == "compat answer"
```

- [ ] **Step 2: Run, confirm fail**

- [ ] **Step 3: Implement `src/tradecraft/providers/openai_compat.py`**

```python
"""OpenAI-compatible adapter (OpenRouter, Groq, LM Studio, vLLM, ...)."""

from __future__ import annotations

import os
from typing import ClassVar

from tradecraft.providers.base import _register


class OpenAICompatProvider:
    name: ClassVar[str] = "openai-compat"
    default_model: ClassVar[str] = ""
    requires_api_key: ClassVar[bool] = True

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        import openai  # type: ignore[import-not-found]

        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(self, system: str, prompt: str, max_tokens: int) -> str:
        response = await self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        choice = response.choices[0] if response.choices else None
        if choice is None or choice.message.content is None:
            return ""
        return str(choice.message.content)

    @classmethod
    def from_env(cls, model: str | None = None) -> OpenAICompatProvider | None:
        base_url = os.environ.get("OPENAI_COMPAT_BASE_URL")
        api_key = os.environ.get("OPENAI_COMPAT_KEY")
        resolved_model = model or os.environ.get("TRADECRAFT_AI_OPENAI_COMPAT_MODEL")
        if not (base_url and api_key and resolved_model):
            return None
        return cls(base_url=base_url, api_key=api_key, model=resolved_model)


_register(OpenAICompatProvider.name, OpenAICompatProvider)
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest tests/unit/providers/test_openai_compat.py -v
uv run ruff check src/tradecraft/providers/openai_compat.py tests/unit/providers/test_openai_compat.py
uv run mypy src/tradecraft/providers/openai_compat.py
```

```
git add src/tradecraft/providers/openai_compat.py tests/unit/providers/test_openai_compat.py
git commit -m "$(cat <<'EOF'
feat(providers): OpenAI-compatible adapter

Reuses the openai SDK with a custom base_url. Requires
OPENAI_COMPAT_BASE_URL + OPENAI_COMPAT_KEY + a model
(TRADECRAFT_AI_OPENAI_COMPAT_MODEL or --ai-model). Works with
OpenRouter, Groq, LM Studio, vLLM, and anything else exposing
the OpenAI chat-completions surface.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: AI analyzer

**Files:**
- Create: `src/tradecraft/analyzers/ai.py`
- Create: `tests/unit/analyzers/test_ai.py`

The AI analyzer takes `Findings` + heuristic `questions` + role + provider and returns a list of new `Question` objects. The LLM is instructed to:
1. Read the Findings JSON and the existing heuristic questions.
2. Generate 3-7 NEW questions that the heuristic generator couldn't have produced (narrative connections, role-fit nuance, deeper follow-ups).
3. NOT duplicate heuristic questions.
4. Output a numbered list, one question per line.

The analyzer parses the numbered list back into `Question` objects with `confidence="high"` (AI-generated), `source_collector="ai"`, `evidence_signal=` a sentinel value, and `is_starred=False`.

Since `evidence_signal` is required on `Question` and is a real `Signal` enum, we'll either: (a) pick `Signal.M_A_RECENT` as a placeholder (bad — misleading), or (b) make `evidence_signal` optional. Per YAGNI: just update `Question.evidence_signal` to be optional, no migration needed since it's pydantic v2.

- [ ] **Step 1: Modify `Question.evidence_signal` to be optional**

In `src/tradecraft/models.py`, find:
```python
class Question(BaseModel):
    text: str
    confidence: Literal["high", "med", "low"]
    role_tags: set[Role]
    evidence_signal: Signal
    source_collector: str
    is_starred: bool = False
```

Change `evidence_signal: Signal` to `evidence_signal: Signal | None = None`.

- [ ] **Step 2: Write failing test for the AI analyzer**

`tests/unit/analyzers/test_ai.py`:

```python
"""Tests for tradecraft.analyzers.ai."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from tradecraft.analyzers.ai import generate_ai_questions
from tradecraft.models import (
    CollectorResult,
    Findings,
    Question,
    Role,
    Signal,
    Target,
)


def _findings() -> Findings:
    target = Target(company_name="Acme", root_url="https://acme.com", role=Role.CYBERSECURITY)
    return Findings(
        target=target,
        results=[
            CollectorResult(
                name="footprint",
                data={"host": "acme.com"},
                signals=[Signal.MISSING_CSP],
                errors=[],
                duration_ms=10,
            )
        ],
    )


def _heuristic_questions() -> list[Question]:
    return [
        Question(
            text="Why no CSP?",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
        )
    ]


async def test_no_provider_returns_empty_list() -> None:
    result = await generate_ai_questions(
        findings=_findings(),
        heuristic_questions=_heuristic_questions(),
        provider=None,
    )
    assert result == []


async def test_provider_output_is_parsed_into_questions() -> None:
    fake_provider = AsyncMock()
    fake_provider.generate = AsyncMock(
        return_value=(
            "1. How does the security team approach exception requests for CSP rollout?\n"
            "2. What is the MTTR on detection coverage post-incident?\n"
            "3. Is there an internal red-team engagement cadence?\n"
        )
    )
    questions = await generate_ai_questions(
        findings=_findings(),
        heuristic_questions=_heuristic_questions(),
        provider=fake_provider,
    )
    assert len(questions) == 3
    assert all(q.source_collector == "ai" for q in questions)
    assert all(q.confidence == "high" for q in questions)
    assert all(q.evidence_signal is None for q in questions)
    assert "exception" in questions[0].text.lower()


async def test_provider_error_returns_empty_list() -> None:
    fake_provider = AsyncMock()
    fake_provider.generate = AsyncMock(side_effect=RuntimeError("rate limited"))
    questions = await generate_ai_questions(
        findings=_findings(),
        heuristic_questions=_heuristic_questions(),
        provider=fake_provider,
    )
    assert questions == []
```

- [ ] **Step 3: Run, confirm fail**

- [ ] **Step 4: Implement `src/tradecraft/analyzers/ai.py`**

```python
"""AI analyzer: synthesize deep-dive questions via a BYOK provider."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from tradecraft.models import Findings, Question, Role
from tradecraft.providers.base import Provider

_NUMBERED_LINE = re.compile(r"^\s*\d+[\.\):]\s*(.+)$")
_MAX_TOKENS = 1200


def _system_prompt(role: Role) -> str:
    return (
        "You are an expert helping a candidate prepare for a cybersecurity "
        "interview. The user will provide structured OSINT findings about the "
        "target company and a list of questions an automated heuristic already "
        f"generated. The candidate is targeting role focus: '{role.value}'. "
        "Generate 3 to 7 NEW interview questions the candidate can ask the "
        "interviewer that the heuristic couldn't have produced. Focus on "
        "narrative connections across findings, role-fit nuance, "
        "and questions that demonstrate sophisticated reconnaissance. Do NOT "
        "duplicate any heuristic question. Return ONLY a numbered list, one "
        "question per line, no other commentary."
    )


def _user_prompt(findings: Findings, heuristic: Sequence[Question]) -> str:
    findings_json = json.dumps(
        {
            "target": findings.target.model_dump(mode="json"),
            "results": [r.model_dump(mode="json") for r in findings.results],
        },
        indent=2,
        sort_keys=True,
        default=str,
    )
    heuristic_block = "\n".join(f"- {q.text}" for q in heuristic) if heuristic else "(none)"
    return (
        "## Findings\n\n"
        f"```json\n{findings_json}\n```\n\n"
        "## Heuristic questions already generated (DO NOT DUPLICATE)\n\n"
        f"{heuristic_block}\n\n"
        "## Your task\n\n"
        "Generate 3-7 NEW interview questions as a numbered list."
    )


async def generate_ai_questions(
    findings: Findings,
    heuristic_questions: Sequence[Question],
    provider: Provider | None,
) -> list[Question]:
    """Return AI-generated questions. Returns empty list on no-provider or error."""
    if provider is None:
        return []

    system = _system_prompt(findings.target.role)
    prompt = _user_prompt(findings, heuristic_questions)

    try:
        raw = await provider.generate(system, prompt, _MAX_TOKENS)
    except Exception:  # noqa: BLE001 — surface as "no AI" rather than crash the run
        return []

    out: list[Question] = []
    for line in raw.splitlines():
        match = _NUMBERED_LINE.match(line)
        if not match:
            continue
        text = match.group(1).strip()
        if not text:
            continue
        out.append(
            Question(
                text=text,
                confidence="high",
                role_tags={findings.target.role},
                evidence_signal=None,
                source_collector="ai",
                is_starred=False,
            )
        )
    return out
```

- [ ] **Step 5: Update existing model test for `evidence_signal` becoming optional**

In `tests/unit/test_models.py`, the existing `test_question_minimal` and `test_question_starred_flag` set `evidence_signal=Signal.MISSING_CSP`. They should still pass (the field is now optional, not removed). No change needed unless a test asserts `evidence_signal` is required.

Run the full suite to confirm no regression:

```
uv run pytest -q
```

- [ ] **Step 6: Verify + commit**

```
uv run pytest tests/unit/analyzers/test_ai.py tests/unit/test_models.py -v
uv run ruff check src/tradecraft/analyzers/ai.py src/tradecraft/models.py tests/unit/analyzers/test_ai.py
uv run mypy src/tradecraft/analyzers/ai.py src/tradecraft/models.py
```

```
git add src/tradecraft/analyzers/ai.py src/tradecraft/models.py tests/unit/analyzers/test_ai.py
git commit -m "$(cat <<'EOF'
feat(analyzers): AI deep-dive question generator

generate_ai_questions(findings, heuristic_questions, provider) sends
the full Findings JSON + already-generated heuristic questions to
the provider, parses a numbered-list response back into Question
objects with source_collector='ai' and confidence='high'. Returns
empty list on provider error or when provider is None.

Question.evidence_signal is now optional (None for AI-generated
questions) since the LLM isn't tied to a specific Signal value.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: CLI flags + wiring

**Files:**
- Modify: `src/tradecraft/cli.py`
- Modify: `tests/unit/test_cli.py`

Add two flags: `--ai <provider>` and `--ai-model <model-id>`. When set, the CLI calls `build_provider(name, model)`. If it returns None, print a warning to stderr ("AI disabled — set <REQUIRED_ENV> to enable") and continue with heuristic-only. If it returns a provider, call `generate_ai_questions` after heuristics and concatenate.

- [ ] **Step 1: Write failing test**

Append to `tests/unit/test_cli.py`:

```python
def test_ai_flag_with_no_provider_warns_and_continues(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No API key => Anthropic.from_env returns None
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("tradecraft.cli._default_collectors", return_value=[StubFootprint()]):
        result = runner.invoke(
            app,
            [
                "https://acme.com",
                "--company",
                "Acme Corp",
                "--ai",
                "anthropic",
                "--output",
                str(tmp_path),
            ],
        )
    # Should succeed (heuristic-only fallback), and stderr should mention AI disabled.
    assert result.exit_code == 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "ai" in combined.lower()


def test_ai_flag_with_provider_appends_questions(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake_provider = AsyncMock()
    fake_provider.generate = AsyncMock(
        return_value="1. AI question one\n2. AI question two\n"
    )
    with patch("tradecraft.cli._default_collectors", return_value=[StubFootprint()]):
        with patch("tradecraft.cli.build_provider", return_value=fake_provider):
            result = runner.invoke(
                app,
                [
                    "https://acme.com",
                    "--company",
                    "Acme Corp",
                    "--ai",
                    "anthropic",
                    "--output",
                    str(tmp_path),
                ],
            )
    assert result.exit_code == 0, result.stdout
    [folder] = list(tmp_path.iterdir())
    raw = json.loads((folder / "raw.json").read_text())
    ai_questions = [q for q in raw["questions"] if q["source_collector"] == "ai"]
    assert len(ai_questions) == 2
```

The existing `from unittest.mock import patch` import at the top of the test file already exists; verify it's there. If `AsyncMock` is not imported in `tests/unit/test_cli.py`, add it: `from unittest.mock import AsyncMock, patch`.

- [ ] **Step 2: Run, confirm fail**

```
uv run pytest tests/unit/test_cli.py -v
```

- [ ] **Step 3: Update `src/tradecraft/cli.py`**

Add the imports near the top (alphabetically inserted):

```python
from tradecraft.analyzers.ai import generate_ai_questions
from tradecraft.providers.base import Provider, build_provider
```

Add the two new flags to `main`'s signature (keep alphabetical order with the others):

```python
    ai: Annotated[
        str | None, typer.Option("--ai", help="AI provider: anthropic | openai | ollama | openai-compat")
    ] = None,
    ai_model: Annotated[
        str | None, typer.Option("--ai-model", help="Override the default model for the chosen provider")
    ] = None,
```

Update the `_run` function signature to accept them and forward to the new code. Replace the current `_run` body with:

```python
async def _run(
    target: Target,
    cfg: AppConfig,
    only: str | None,
    skip: str | None,
    verbose: bool,
    ai: str | None,
    ai_model: str | None,
) -> tuple[Findings, list[Question]]:
    cache_dir: Path
    if cfg.cache.directory:
        cache_dir = Path(cfg.cache.directory)
    else:
        cache_dir = Path.home() / ".cache" / "tradecraft"

    cache = Cache(
        directory=cache_dir,
        default_ttl=cfg.cache.ttl_default_seconds,
        enabled=cfg.cache.enabled,
    )
    target_host = urlparse(str(target.root_url)).hostname
    async with HttpClient(cfg.http, cache, target_host=target_host) as http:
        orch = Orchestrator(_default_collectors(), http=http, cache=cache)
        findings = await orch.run(
            target,
            only=set(only.split(",")) if only else None,
            skip=set(skip.split(",")) if skip else None,
        )
    if verbose:
        for r in findings.results:
            err_console.print(
                f"[dim]{r.name}: {r.duration_ms} ms, signals={[s.value for s in r.signals]}[/]"
            )
    questions = generate_questions(findings)

    if ai is not None:
        provider: Provider | None
        try:
            provider = build_provider(ai, ai_model)
        except ValueError as exc:
            err_console.print(f"[yellow]AI disabled: {exc}[/]")
            provider = None
        if provider is None:
            err_console.print(
                "[yellow]AI disabled — provider env vars missing. "
                "Continuing with heuristic questions only.[/]"
            )
        else:
            ai_questions = await generate_ai_questions(findings, questions, provider)
            questions.extend(ai_questions)

    return findings, questions
```

And update the `main` function's call to `_run` to forward the new args:

Find:
```python
    findings, questions = asyncio.run(_run(target, cfg, only, skip, verbose))
```

Replace with:
```python
    findings, questions = asyncio.run(_run(target, cfg, only, skip, verbose, ai, ai_model))
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest tests/unit/test_cli.py -v
uv run pytest -q
uv run ruff check src/tradecraft/cli.py tests/unit/test_cli.py
uv run mypy src/tradecraft/cli.py
```

```
git add src/tradecraft/cli.py tests/unit/test_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): --ai and --ai-model flags wire BYOK AI integration

When --ai <provider> is set, build_provider() looks up the adapter
and calls from_env(model). If env vars are missing, a yellow warning
prints to stderr and the run continues with heuristic-only output.
Otherwise generate_ai_questions() runs after heuristics and the AI
questions are appended to the questions list. AI questions land in
questions.md and raw.json with source_collector='ai'.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Renderer "Deep dive (AI)" subsection

**Files:**
- Modify: `src/tradecraft/renderers/markdown.py`
- Modify: `src/tradecraft/renderers/questions.py`
- Modify: `tests/unit/renderers/test_markdown.py`
- Modify: `tests/unit/renderers/test_questions.py`

Currently both renderers group questions into "Top picks" (starred) + "Further questions" (rest). AI questions should land in a separate "Deep dive (AI)" group, AFTER both, so the heuristic baseline is visually prominent and AI sits as the upgrade.

- [ ] **Step 1: Write failing tests**

Append to `tests/unit/renderers/test_markdown.py`:

```python
def test_ai_questions_render_in_deep_dive_section() -> None:
    target = Target(company_name="Acme", root_url="https://acme.com")
    findings = Findings(target=target, results=[])
    questions = [
        Question(
            text="Heuristic Q",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=True,
        ),
        Question(
            text="AI Q one",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=None,
            source_collector="ai",
            is_starred=False,
        ),
    ]
    md = render_markdown(findings, questions)
    assert "### Deep dive (AI)" in md
    assert "AI Q one" in md
    # Heuristic question still in top picks
    assert "Heuristic Q" in md
```

Append to `tests/unit/renderers/test_questions.py`:

```python
def test_questions_standalone_has_deep_dive_subsection() -> None:
    qs = [
        Question(
            text="Heur",
            confidence="med",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=Signal.MISSING_CSP,
            source_collector="footprint",
            is_starred=False,
        ),
        Question(
            text="AI question",
            confidence="high",
            role_tags={Role.CYBERSECURITY},
            evidence_signal=None,
            source_collector="ai",
        ),
    ]
    out = render_questions(qs, company_name="Acme")
    assert "## Deep dive (AI)" in out
    assert "AI question" in out
```

- [ ] **Step 2: Run, confirm fail**

- [ ] **Step 3: Update `src/tradecraft/renderers/markdown.py`**

Find `_questions_section`. Replace the body so AI questions are split out:

```python
def _questions_section(questions: Sequence[Question]) -> str:
    lines = [
        "## Questions to ask",
        "",
        "Evidence-cited prompts to take into the interview. Starred items are the "
        "highest-confidence picks.",
        "",
    ]
    if not questions:
        lines.append(
            "_No heuristic-driven questions generated. Add more collector "
            "coverage or run with `--ai` to deepen this section._"
        )
        lines.append("")
        return "\n".join(lines)

    heuristic = [q for q in questions if q.source_collector != "ai"]
    ai = [q for q in questions if q.source_collector == "ai"]

    starred = [q for q in heuristic if q.is_starred]
    rest = [q for q in heuristic if not q.is_starred]
    if starred:
        lines.append("### Top picks")
        lines.append("")
        for q in starred:
            lines.append(_format_question(q))
        lines.append("")
    if rest:
        lines.append("### Further questions")
        lines.append("")
        for q in rest:
            lines.append(_format_question(q))
        lines.append("")
    if ai:
        lines.append("### Deep dive (AI)")
        lines.append("")
        for q in ai:
            lines.append(_format_question(q))
        lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 4: Update `src/tradecraft/renderers/questions.py`**

Find the body of `render_questions` and apply the same split. Replace it with:

```python
def render_questions(questions: Sequence[Question], *, company_name: str) -> str:
    lines = [f"# Questions to ask {company_name}", ""]
    if not questions:
        lines.append("_No heuristic-driven questions generated for this run._")
        lines.append("")
        return "\n".join(lines)

    heuristic = [q for q in questions if q.source_collector != "ai"]
    ai = [q for q in questions if q.source_collector == "ai"]

    starred = [q for q in heuristic if q.is_starred]
    rest = [q for q in heuristic if not q.is_starred]

    if starred:
        lines.append("## Top picks")
        lines.append("")
        for q in starred:
            lines.append(_format(q))
        lines.append("")
    if rest:
        lines.append("## Further questions")
        lines.append("")
        for q in rest:
            lines.append(_format(q))
        lines.append("")
    if ai:
        lines.append("## Deep dive (AI)")
        lines.append("")
        for q in ai:
            lines.append(_format(q))
        lines.append("")
    return "\n".join(lines)
```

If the existing `_format` function references `q.evidence_signal.value`, it will crash when evidence_signal is None. Update it to:

```python
def _format(q: Question) -> str:
    tags = " ".join(f"`{r.value}`" for r in sorted(q.role_tags))
    evidence = (
        f"`{q.evidence_signal.value}` from `{q.source_collector}`"
        if q.evidence_signal is not None
        else f"AI deep-dive (`{q.source_collector}`)"
    )
    return (
        f"- **{q.text}**  \n"
        f"  _confidence:_ `{q.confidence}` · _evidence:_ {evidence} · _roles:_ {tags}"
    )
```

Apply the same conditional to `_format_question` in `markdown.py`.

- [ ] **Step 5: Verify + commit**

```
uv run pytest tests/unit/renderers/ -v
uv run pytest -q
uv run ruff check src/tradecraft/renderers tests/unit/renderers
uv run mypy src/tradecraft/renderers
```

```
git add src/tradecraft/renderers/markdown.py src/tradecraft/renderers/questions.py tests/unit/renderers/test_markdown.py tests/unit/renderers/test_questions.py
git commit -m "$(cat <<'EOF'
feat(renderers): Deep dive (AI) subsection

Both markdown.py and questions.py split questions into heuristic
(Top picks + Further questions) and AI (Deep dive). _format helpers
handle Question.evidence_signal=None now that AI questions don't
carry a Signal value.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `[ai]` optional-dependencies extra

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md` (just the install snippet section)

Move `anthropic` and `openai` from dev deps to a new `[project.optional-dependencies] ai = [...]` group so end users can `pipx install tradecraft[ai]` and get the SDKs. Keep them in dev too so CI / tests have them.

- [ ] **Step 1: Edit `pyproject.toml`**

Locate the `[project.optional-dependencies]` table. Currently:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "respx>=0.21",
    "coverage>=7.5",
    "ruff>=0.5",
    "mypy>=1.10",
    "types-requests",
    "anthropic>=0.39",
    "openai>=1.50",
]
```

(The exact list may differ — pull in whatever's there.)

Add a new `ai` group AFTER `dev`:

```toml
ai = [
    "anthropic>=0.39",
    "openai>=1.50",
]
```

Leave `anthropic` / `openai` in `dev` too so the CI matrix has them.

- [ ] **Step 2: Update README install snippet**

In `README.md`, in the `## Install` section, replace the existing install block with:

```markdown
## Install

```bash
# Core CLI (heuristic questions only)
pipx install tradecraft

# Plus BYOK AI providers (Anthropic, OpenAI, OpenAI-compatible)
pipx install 'tradecraft[ai]'

# Ollama works out of the box with the core install — no extra package needed.
```

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
```

- [ ] **Step 3: Verify + commit**

```
uv sync --all-extras
uv run pytest -q
uv run ruff check src tests
uv run mypy src
```

```
git add pyproject.toml README.md uv.lock
git commit -m "$(cat <<'EOF'
chore(deps): add [ai] optional-dependencies extra

Users can `pipx install 'tradecraft[ai]'` to pull anthropic and openai.
Ollama and openai-compat (which reuses the openai SDK) just work.
README gains an "AI providers (BYOK)" table documenting required
env vars per provider.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: AI end-to-end integration test

**Files:**
- Create: `tests/integration/test_v0_3_ai_e2e.py`

A single integration test that runs the CLI with `--ai anthropic`, mocks the Anthropic SDK at the boundary, and confirms AI questions land in the dossier.

- [ ] **Step 1: Write the test**

`tests/integration/test_v0_3_ai_e2e.py`:

```python
"""v0.3.0 AI integration end-to-end."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from typer.testing import CliRunner

from tradecraft.cli import app
from tradecraft.collectors.footprint import FootprintCollector


@respx.mock
def test_ai_questions_land_in_dossier(
    tmp_path: Path, fixtures_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Minimal footprint mocks
    respx.get("https://acme.com/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=[{"name_value": "acme.com"}])
    )
    respx.get("https://acme.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>", headers={"server": "nginx"})
    )
    respx.get("https://acme.com/sitemap.xml").mock(return_value=httpx.Response(404))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    dns = AsyncMock(return_value={"A": ["1.2.3.4"], "MX": [], "TXT": []})

    # Mock the Anthropic SDK client at the AsyncAnthropic boundary
    fake_response = MagicMock()
    fake_response.content = [
        MagicMock(text=(
            "1. How does your purple-team cadence inform CSP rollout?\n"
            "2. What's your SOC's MTTR on injected CSP violations?\n"
            "3. Have you piloted SBOM signing on the public site?\n"
        ))
    ]
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    runner = CliRunner()
    with patch("tradecraft.cli._default_collectors", return_value=[FootprintCollector(_dns_lookup=dns)]):
        with patch("anthropic.AsyncAnthropic", return_value=fake_client):
            result = runner.invoke(
                app,
                [
                    "https://acme.com",
                    "--company",
                    "Acme",
                    "--ai",
                    "anthropic",
                    "--output",
                    str(tmp_path),
                ],
            )
    assert result.exit_code == 0, result.stdout
    [folder] = list(tmp_path.iterdir())
    raw = json.loads((folder / "raw.json").read_text())
    ai_questions = [q for q in raw["questions"] if q["source_collector"] == "ai"]
    assert len(ai_questions) == 3
    report = (folder / "report.md").read_text()
    assert "### Deep dive (AI)" in report
    assert "MTTR" in report
```

- [ ] **Step 2: Verify**

```
uv run pytest tests/integration/test_v0_3_ai_e2e.py -v
uv run pytest -q  # full suite
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

- [ ] **Step 3: Commit**

```
git add tests/integration/test_v0_3_ai_e2e.py
git commit -m "$(cat <<'EOF'
test(integration): v0.3.0 AI flow end-to-end

CLI --ai anthropic -> mocked AsyncAnthropic -> parsed numbered list
lands in raw.json with source_collector='ai' and renders under
the Deep dive (AI) subsection.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Version bump + README + CHANGELOG

**Files:**
- Modify: `src/tradecraft/__init__.py`
- Modify: `CHANGELOG.md`
- Modify: `README.md` (status block)

- [ ] **Step 1: Bump version**

In `src/tradecraft/__init__.py`:
```python
__version__ = "0.2.0"
```
to:
```python
__version__ = "0.3.0"
```

- [ ] **Step 2: CHANGELOG entry**

In `CHANGELOG.md`, insert AFTER the `## [Unreleased]` line and BEFORE the existing `## [0.2.0]` entry:

```markdown
## [0.3.0] - 2026-05-25

### Added

- BYOK AI deep-dive question layer. Pass `--ai <provider>` to append
  a `Deep dive (AI)` subsection to the questions section, with synthesized,
  role-tailored questions the heuristic engine couldn't produce.
- Four provider adapters:
  - `anthropic` (Anthropic Claude, default `claude-sonnet-4-6`) — uses
    `cache_control: ephemeral` on the Findings payload so iterative tuning
    is cheap.
  - `openai` (OpenAI, default `gpt-4o`).
  - `ollama` (local-only, no key needed, default `llama3.1:8b`).
  - `openai-compat` (OpenRouter / Groq / LM Studio / vLLM / anyone speaking
    the OpenAI chat-completions API).
- New optional-dependencies extra `[ai]` so `pipx install 'tradecraft[ai]'`
  pulls the Anthropic and OpenAI SDKs. Ollama and openai-compat (via the
  openai SDK) work without extras.
- `--ai-model` flag overrides the provider's default model.

### Changed

- `Question.evidence_signal` is now optional (AI-generated questions don't
  cite a Signal; they cite "AI deep-dive" in the rendered footnote instead).

### Deferred

- Cross-collector signals (`LANGUAGES_MISMATCH_JOB` / `STACK_ALIGNMENT_STRONG`)
  remain pending until `findings_so_far` is wired through `CollectorContext`.
- Hosted web preview ships in v1.1.
```

- [ ] **Step 3: README status block**

Replace the `## Status` paragraph with:

```markdown
**v0.3.0** — full CLI feature set. All 9 collectors + BYOK AI deep-dive layer
(`--ai anthropic|openai|ollama|openai-compat`). Hosted web preview ships in v1.1.
```

- [ ] **Step 4: Verify + commit**

```
uv run pytest -q
uv run python -c "import tradecraft; print(tradecraft.__version__)"
```

Expected: prints `0.3.0`; full suite green.

```
git add src/tradecraft/__init__.py CHANGELOG.md README.md
git commit -m "$(cat <<'EOF'
chore: bump version + update README/CHANGELOG for v0.3.0

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Tag v0.3.0 and push

- [ ] **Step 1: Final sweep**

```
uv run pytest -v
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

Expected: all green. Full suite should be ~150 tests.

If `ruff format --check` flags whitespace, run `uv run ruff format src tests`, commit the normalization as `chore: ruff format normalization` (same pattern as prior tags), THEN tag.

- [ ] **Step 2: Tag and push**

```
git tag -a v0.3.0 -m "tradecraft v0.3.0: BYOK AI deep-dive layer (4 providers)"
git push origin main
git push origin v0.3.0
gh run list --branch main --limit 1
```

Watch CI:

```
gh run watch <run-id> --exit-status
```

If CI fails: investigate. Don't move the tag unless code changes. Same pattern as v0.1.0/v0.2.0.

- [ ] **Step 3: Real-world validation**

Run against a known target with AI enabled:

```
export ANTHROPIC_API_KEY=<your key>
uv run tradecraft https://cloudflare.com --role cybersecurity --ai anthropic --output ./demo --no-cache
```

Inspect `demo/cloudflare-<date>/report.md`. Expect:
- All 9 collector sections populated where Cloudflare has data.
- "Top picks" + "Further questions" sections from heuristics.
- "Deep dive (AI)" subsection with 3-7 AI-generated questions.

If anything looks off (e.g. AI questions duplicate heuristics, format is wrong), file follow-ups; don't fix mid-tag unless it's a real bug.

---

## Self-review (run by the engineer / agent after completing all tasks)

- [ ] `uv run pytest -v` passes — expect ~150 tests.
- [ ] `uv run ruff check src tests` clean.
- [ ] `uv run ruff format --check src tests` clean.
- [ ] `uv run mypy src` clean.
- [ ] `uv run tradecraft --help` shows the `--ai` and `--ai-model` flags.
- [ ] A real run with `--ai anthropic` against a known target produces a `Deep dive (AI)` subsection in `report.md`.
- [ ] A real run with `--ai anthropic` and no `ANTHROPIC_API_KEY` set prints a yellow stderr warning AND completes successfully with heuristic-only output.
- [ ] `raw.json` schema v1 unchanged (AI questions just gain `source_collector="ai"` and `evidence_signal=None`).
- [ ] `tag` shows `v0.1.0a0`, `v0.1.0a1`, `v0.2.0`, `v0.3.0`.

---

## Plan-author self-review

**Spec coverage (against `docs/superpowers/specs/2026-05-23-tradecraft-design.md`):**

- §7.2 AI analyzer → Task 6.
- §7.3 Anthropic adapter → Task 2.
- §7.3 OpenAI adapter → Task 3.
- §7.3 Ollama adapter → Task 4.
- §7.3 openai-compat adapter → Task 5.
- §9 CLI surface (--ai, --ai-model) → Task 7.
- §12 Configuration (env vars per provider) → Task 9 (README) + per-task `from_env` impls.
- §16 Dependencies (lazy imports) → Task 1 (lazy registry).

**Placeholder scan:** no "TBD"/"TODO"/"Similar to Task N". Deferred items are explicit (`LANGUAGES_MISMATCH_JOB`, hosted web).

**Type consistency:** `Provider` protocol defined in Task 1 has the same `generate(system, prompt, max_tokens) -> str` signature in every adapter (Tasks 2-5) and in the analyzer call site (Task 6) and in the CLI wiring (Task 7). Provider class names (`AnthropicProvider`, `OpenAIProvider`, `OllamaProvider`, `OpenAICompatProvider`) used consistently in their respective tests and the registry strings (`"anthropic"`, `"openai"`, `"ollama"`, `"openai-compat"`) match between `build_provider` and `_register` calls. `Question.evidence_signal` becomes `Signal | None` in Task 6 and the renderers (Task 8) handle the None case.

"""
conftest.py — shared fixtures for the opt-in LLM-output evaluation suite.

Every test in :mod:`tests.eval` is marked ``@pytest.mark.eval`` and excluded
from the default ``pytest`` run (see ``pytest.ini``). Run the suite with::

    pytest -m eval

The fixtures here keep the eval tests friendly to contributors who do not
have a daemon or models on their machine:

- :func:`ollama_available` skips a test (rather than failing) when the
  local Ollama daemon at ``http://localhost:11434`` does not respond.
- :func:`require_model` skips when a specific model tag has not been
  pulled into Ollama.
- :func:`fixtures_dir` and :func:`eval_repo_root` resolve fixture paths
  the same way across all four eval modules.

These fixtures intentionally do **not** start a daemon or pull models —
that belongs to ``install_alt_ai.py`` / ``install_captions.py`` and is
out of scope for a test session.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

import pytest


# ── Path helpers ────────────────────────────────────────────────────────────

# ``tests/eval/conftest.py`` → repo root is three levels up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_FIXTURES = _REPO_ROOT / "tests" / "fixtures"


@pytest.fixture(scope="session")
def eval_repo_root() -> Path:
    """Return the repository root directory."""
    return _REPO_ROOT


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return ``tests/fixtures/`` so each eval module resolves paths the same way."""
    return _FIXTURES


@pytest.fixture(scope="session")
def html_fixture(fixtures_dir: Path) -> Callable[[str], Path]:
    """Return a callable mapping a basename ``foo`` to ``fixtures/html/foo.html``."""
    def _lookup(name: str) -> Path:
        p = fixtures_dir / "html" / f"{name}.html"
        if not p.exists():
            pytest.skip(f"HTML fixture missing: {p}")
        return p
    return _lookup


@pytest.fixture(scope="session")
def image_fixture(fixtures_dir: Path) -> Callable[[str], Path]:
    """Return a callable mapping a basename ``foo`` to ``fixtures/images/foo.png|jpg``."""
    def _lookup(name: str) -> Path:
        for suffix in (".png", ".jpg", ".jpeg", ".webp"):
            p = fixtures_dir / "images" / f"{name}{suffix}"
            if p.exists():
                return p
        pytest.skip(f"Image fixture missing: tests/fixtures/images/{name}.*")
    return _lookup


@pytest.fixture(scope="session")
def audio_fixture(fixtures_dir: Path) -> Callable[[str], Path]:
    """Return a callable mapping a basename to ``fixtures/audio/<name>.wav``."""
    def _lookup(name: str) -> Path:
        p = fixtures_dir / "audio" / f"{name}.wav"
        if not p.exists():
            pytest.skip(
                f"Audio fixture missing: {p}. "
                f"See tests/fixtures/audio/README.md for how to provision it."
            )
        return p
    return _lookup


# ── Ollama-availability helpers ─────────────────────────────────────────────

# Module-level cache so we hit the daemon at most once per pytest session. The
# value is the parsed ``/api/tags`` JSON when the daemon is reachable, or
# ``None`` when it isn't. ``object()`` sentinel signals "not yet queried".
_TAGS_SENTINEL: object = object()
_TAGS_CACHE: object | dict | None = _TAGS_SENTINEL


def _ollama_url() -> str:
    """Resolve the daemon's tags endpoint, honouring ``OLLAMA_HOST`` when set."""
    base = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    # ``OLLAMA_HOST`` accepts either a bare host:port or a full URL; normalise both.
    if not base.startswith(("http://", "https://")):
        base = f"http://{base}"
    return f"{base}/api/tags"


def _fetch_tags(url: str | None = None, timeout: float = 1.5) -> dict | None:
    """
    Probe the Ollama daemon's tags endpoint.

    Returns the parsed JSON (with a ``models`` list) on success, or ``None``
    when the daemon is unreachable. Network failures, timeouts, and bad JSON
    all collapse to ``None`` — we treat them all the same way: skip.
    """
    global _TAGS_CACHE
    if _TAGS_CACHE is not _TAGS_SENTINEL:
        return _TAGS_CACHE  # type: ignore[return-value]
    try:
        with urllib.request.urlopen(url or _ollama_url(), timeout=timeout) as resp:
            _TAGS_CACHE = json.loads(resp.read().decode("utf-8"))
            return _TAGS_CACHE  # type: ignore[return-value]
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        _TAGS_CACHE = None
        return None


@pytest.fixture(scope="session")
def ollama_available() -> dict:
    """
    Skip the test cleanly when the local Ollama daemon is not reachable.

    Returns the parsed ``/api/tags`` response so individual tests can use it
    to check whether a specific model is pulled.
    """
    tags = _fetch_tags()
    if tags is None:
        pytest.skip(
            "Ollama daemon not reachable at http://localhost:11434. "
            "Start it with `ollama serve` or "
            "`python sprezzature-accessibility/scripts/install_alt_ai.py`."
        )
    return tags


@pytest.fixture(scope="session")
def require_model(ollama_available: dict) -> Callable[[str], None]:
    """
    Return a callable that skips the test when the named model is not pulled.

    The check is forgiving: we match any tag whose name *starts with* the
    requested base (so ``qwen3-vl`` matches ``qwen3-vl:8b``).
    Pass the bare base — the test should not care about the size/variant
    suffix.
    """
    pulled: list[str] = [m.get("name", "") for m in ollama_available.get("models", [])]

    def _check(model_base: str) -> None:
        prefix = model_base.split(":", 1)[0]
        if not any(name.startswith(prefix) for name in pulled):
            pytest.skip(
                f"Ollama model `{model_base}` not pulled. Pull it with "
                f"`ollama pull {model_base}` and retry."
            )

    return _check

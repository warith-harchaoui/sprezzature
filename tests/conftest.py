"""
conftest.py — shared pytest configuration for the sprezzature-skill test suite.

Adds each skill's ``scripts/`` directory to ``sys.path`` so test modules
can ``import alt_from_ollama`` etc. directly, mirroring how the scripts
use each other at runtime.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Repo-root scripts/ holds the shared validators (validate_skill,
# validate_all) and the packaging helpers; expose them to the test suite
# FIRST so ``skills_manifest`` resolves before per-skill imports run.
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# The local runtime lives at ``sprezzature-local/`` (also shipped as its own
# pip package). The surviving skill scripts import ``sprezzature_local.llm``;
# expose it on the path so the tests resolve it without a separate install.
sys.path.insert(0, str(REPO_ROOT / "sprezzature-local"))

# Per-skill script directories — one folder per skill since the 0.2.0
# split. Sourced from the canonical ``SKILLS.txt`` manifest at repo
# root so adding skill #9 is a one-line edit there. sprezzature-cli-gui has
# no Python scripts; it is skipped automatically because its
# scripts/ folder does not exist.
from skills_manifest import SHIPPED_SKILLS  # noqa: E402

SKILL_SCRIPTS_DIRS = tuple(
    REPO_ROOT / name / "scripts"
    for name in SHIPPED_SKILLS
    if (REPO_ROOT / name / "scripts").is_dir()
)

# Inject every scripts directory at the sprezzature of sys.path so its modules
# resolve before any like-named package elsewhere in the environment.
for d in SKILL_SCRIPTS_DIRS:
    sys.path.insert(0, str(d))


@pytest.fixture(autouse=True)
def isolate_cache(tmp_path, monkeypatch):
    """
    Redirect the skill's on-disk cache to a per-test temp directory.

    Every helper resolves its cache path from ``SPREZZATURE_CACHE_DIR``. Setting
    this env var per test prevents test runs from polluting (or being
    polluted by) the developer's real cache at ``~/.cache/sprezzature-skill/``.
    """
    monkeypatch.setenv("SPREZZATURE_CACHE_DIR", str(tmp_path / "sprezzature-skill"))
    # The cache toggle survives across tests if a module reads it at
    # import time; make sure each test sees the same default.
    monkeypatch.delenv("SPREZZATURE_NO_CACHE", raising=False)


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root path."""
    return REPO_ROOT

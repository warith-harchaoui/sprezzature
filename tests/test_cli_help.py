"""
test_cli_help — every sprezzature script answers ``-h`` and ``--version`` cleanly.

These are no-Ollama, no-network smoke tests. They verify that the
argparse migration did not break invocation for any shipped script.

Tests are parametrised so a future script just needs to be added to
``SCRIPTS`` to be covered.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


SCRIPTS = [
    # sprezzature-publish's commands moved to its standalone repository;
    # its own suite checks their --help there.
    # sprezzature-accessibility's commands moved to its standalone repository;
    # its own suite checks their --help there.
    # sprezzature-ui's commands moved to its standalone repository;
    # its own suite checks their --help there.
]


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True,
    )


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_version_flag(script: Path) -> None:
    """``-V`` / ``--version`` must exit 0 and match the shared SKILL_VERSION."""
    # Read the version from the canonical source — the per-skill
    # ``_argparse.py`` factory — rather than hard-coding a literal
    # that would lock the test to one release tag and fail every
    # version bump (this is exactly the failure mode that bit us
    # at v0.15.0).
    from _argparse import SKILL_VERSION  # noqa: E402

    proc = _run(script, "--version")
    assert proc.returncode == 0, (
        f"{script} exited {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert SKILL_VERSION in proc.stdout, (
        f"{script} --version output ('{proc.stdout.strip()}') does not "
        f"carry the shared SKILL_VERSION ('{SKILL_VERSION}'). Check that "
        f"the script's _argparse copy is in sync with the others."
    )


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_help_flag_announces_prog(script: Path) -> None:
    """`-h` must exit 0 and start with the canonical kebab-cased prog name."""
    proc = _run(script, "-h")
    assert proc.returncode == 0, (
        f"{script} exited {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    # `sprezzature-<skill>-<action>` — what `make_parser(prog=…)` sets.
    assert "sprezzature-" in proc.stdout
    assert "[-h]" in proc.stdout or "[--help]" in proc.stdout

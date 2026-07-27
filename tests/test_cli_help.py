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
    # sprezzature-accessibility
    REPO_ROOT / "sprezzature-accessibility"    / "scripts" / "lint_a11y.py",
    # sprezzature-audio
    REPO_ROOT / "sprezzature-audio"           / "scripts" / "install_captions.py",
    REPO_ROOT / "sprezzature-audio"           / "scripts" / "captions_from_whisper.py",
    REPO_ROOT / "sprezzature-audio"           / "scripts" / "name_from_transcript.py",
    REPO_ROOT / "sprezzature-audio"           / "scripts" / "translate_captions.py",
    # sprezzature-colors
    REPO_ROOT / "sprezzature-colors"  / "scripts" / "audit_contrast.py",
    REPO_ROOT / "sprezzature-colors"  / "scripts" / "simulate_cvd.py",
    REPO_ROOT / "sprezzature-colors"  / "scripts" / "palette_to_tailwind.py",
    # sprezzature-publish
    REPO_ROOT / "sprezzature-publish" / "scripts" / "favicons.py",
    REPO_ROOT / "sprezzature-publish" / "scripts" / "meta_from_ollama.py",
    REPO_ROOT / "sprezzature-publish" / "scripts" / "site_indexes.py",
    REPO_ROOT / "sprezzature-publish" / "scripts" / "plain_language.py",
    REPO_ROOT / "sprezzature-publish" / "scripts" / "lint_markdown.py",
    REPO_ROOT / "sprezzature-publish" / "scripts" / "md_to_html.py",
    # sprezzature-figures
    REPO_ROOT / "sprezzature-figures" / "scripts" / "render_diagram.py",
    # sprezzature-vision
    REPO_ROOT / "sprezzature-vision"  / "scripts" / "alt_from_ollama.py",
    # sprezzature-cli-gui
    REPO_ROOT / "sprezzature-cli-gui" / "scripts" / "cli_to_gui.py",
    # sprezzature-ux-laws
    REPO_ROOT / "sprezzature-ux-laws" / "scripts" / "audit_laws_of_ux.py",
    # sprezzature-ui
    REPO_ROOT / "sprezzature-ui"      / "scripts" / "audit_i18n.py",
    REPO_ROOT / "sprezzature-ui"      / "scripts" / "i18n_make.py",
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

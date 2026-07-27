"""Smoke tests for the sprezzature-cli driver. No Click → tests skip cleanly."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner  # noqa: E402

from sprezzature_cli.cli import cli  # noqa: E402
from sprezzature_cli import __version__  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_root_help_lists_all_groups() -> None:
    """The root ``--help`` lists one command group per wrapped skill."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    # One group per wrapped skill (the old single ``a11y`` mega-group was
    # split into per-skill groups when the driver was restructured).
    for group in ("ui", "accessibility", "audio", "colors", "vision", "publish"):
        assert group in result.output


def test_root_version_includes_version_string() -> None:
    """``--version`` prints the package version string."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_subgroup_help_lists_actions() -> None:
    runner = CliRunner()
    # Actions now live under their per-skill groups: ``colors`` carries
    # both contrast and CVD; ``publish`` carries the doc-tooling verbs.
    for group, actions in (
        ("colors", ("contrast", "cvd")),
        ("publish", ("meta", "plain", "favicons")),
    ):
        result = runner.invoke(cli, [group, "--help"])
        assert result.exit_code == 0
        for action in actions:
            assert action in result.output


def test_ui_validate_runs_against_repo() -> None:
    """`sprezzature ui validate` should pass on the in-repo sprezzature-ui skill."""
    env = os.environ.copy()
    env["SPREZZATURE_SKILLS_PATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "sprezzature_cli", "ui", "validate"],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "PASS — skill is shippable." in result.stdout


def test_leaf_help_forwards_to_wrapped_script() -> None:
    """
    Regression test: ``sprezzature vision alt --help`` must show the wrapped
    script's actual options (``--kind``, ``--lang``, ``--longdesc``, …),
    not Click's one-line driver stub.

    The bug — fixed by setting ``add_help_option=False`` on every leaf
    command — was that the driver intercepted ``--help`` at its own
    wrapper level instead of forwarding it through the subprocess. Users
    typing ``sprezzature vision alt --help`` saw nothing useful.
    """
    env = os.environ.copy()
    env["SPREZZATURE_SKILLS_PATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "sprezzature_cli", "vision", "alt", "--help"],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # Markers that prove the wrapped script's help fired, not Click's stub.
    for marker in ("--kind", "--lang", "--longdesc", "informative"):
        assert marker in result.stdout, (
            f"{marker!r} missing from `sprezzature vision alt --help` output — "
            f"driver may be intercepting --help again.\nstdout:\n{result.stdout}"
        )

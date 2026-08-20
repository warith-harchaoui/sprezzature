"""
test_cli_driver — the sprezzature-cli routing driver (`sprezzature_cli.cli`).

The driver itself carries no domain logic — it resolves a skill folder and
shells out to the script. The parts worth testing are exactly those: skill
resolution across the search path, and the exit-code contract when a skill or
script is missing (must be a clean non-zero, not a traceback).

Author
------
Project maintainers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "sprezzature-cli" / "src"))

from sprezzature_cli import cli as driver  # noqa: E402


def test_candidate_bases_honours_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """$SPREZZATURE_SKILLS_PATH entries lead the search order."""
    monkeypatch.setenv("SPREZZATURE_SKILLS_PATH", f"{tmp_path}:/some/other")
    bases = driver._candidate_bases()
    assert bases[0] == tmp_path
    # cwd + the two well-known install dirs always follow.
    assert Path.home() / ".claude" / "skills" in bases
    assert Path.home() / ".opencode" / "skills" in bases


def test_find_skill_resolves_in_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real skill folder resolves when the repo root is on the search path."""
    monkeypatch.setenv("SPREZZATURE_SKILLS_PATH", str(REPO_ROOT))
    found = driver._find_skill("sprezzature-ui")
    assert found is not None
    assert (found / "scripts").is_dir()


def test_find_skill_missing_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A bogus skill name resolves to None (no exception)."""
    monkeypatch.setenv("SPREZZATURE_SKILLS_PATH", str(tmp_path))
    assert driver._find_skill("sprezzature-does-not-exist") is None


def test_run_script_missing_skill_exits_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Routing to an absent skill returns exit code 2, cleanly."""
    monkeypatch.setenv("SPREZZATURE_SKILLS_PATH", str(tmp_path))
    rc = driver._run_script("sprezzature-nope", "whatever.py", ())
    assert rc == 2


def test_run_script_missing_file_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """A present skill but absent script also returns 2."""
    monkeypatch.setenv("SPREZZATURE_SKILLS_PATH", str(REPO_ROOT))
    rc = driver._run_script("sprezzature-ui", "no_such_script.py", ())
    assert rc == 2


def test_version_flag_reports_package_version() -> None:
    """`sprezzature --version` prints the package __version__ (drift guard)."""
    from sprezzature_cli import __version__

    from click.testing import CliRunner

    result = CliRunner().invoke(driver.cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


# ── _run_tool: the extracted-skill dispatch (regression, see CHANGELOG) ────
#
# Six skills (accessibility, audio, colors, cli-gui, ux-laws, figures) had
# their scripts/ extracted to standalone pip packages; their local
# scripts/ folder is now just __pycache__/. `_run_tool` is what makes
# `sprezzature accessibility lint` etc. keep working: it tries the
# standalone package's console script, then the pre-extraction in-repo
# path, then `python -m <module>`, before giving up with an actionable
# message. These tests exercise the resolution order without depending on
# any of those packages actually being installed.


def test_run_tool_prefers_console_script_on_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """When the console script resolves on $PATH, it wins over everything else."""
    monkeypatch.setenv("SPREZZATURE_SKILLS_PATH", str(tmp_path))
    fake_bin = tmp_path / "sprezzature-accessibility-lint"
    fake_bin.write_text("#!/bin/sh\nprintf ok\n")
    fake_bin.chmod(0o755)
    monkeypatch.setattr(driver.shutil, "which", lambda name: str(fake_bin) if name == fake_bin.name else None)
    rc = driver._run_tool(
        "sprezzature-accessibility", "lint_a11y.py", (),
        console_script="sprezzature-accessibility-lint",
        module="sprezzature_accessibility_scripts.lint_a11y",
    )
    assert rc == 0


def test_run_tool_falls_back_to_in_repo_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """No console script on $PATH, but the in-repo scripts/ still has the file: use it."""
    monkeypatch.setenv("SPREZZATURE_SKILLS_PATH", str(REPO_ROOT))
    monkeypatch.setattr(driver.shutil, "which", lambda name: None)
    # sprezzature-ui is not an extracted skill: its scripts/validate.py is real.
    rc = driver._run_tool(
        "sprezzature-ui", "validate.py", ("--help",),
        console_script="sprezzature-ui-validate",  # deliberately bogus; must not resolve
        module=None,
    )
    assert rc == 0


def test_run_tool_reports_actionable_error_when_nothing_resolves(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """No console script, no in-repo file, no importable module: exit 2, not a traceback."""
    monkeypatch.setenv("SPREZZATURE_SKILLS_PATH", str(tmp_path))
    monkeypatch.setattr(driver.shutil, "which", lambda name: None)
    rc = driver._run_tool(
        "sprezzature-colors", "audit_contrast.py", (),
        console_script=None,
        module="sprezzature_this_module_does_not_exist",
    )
    assert rc == 2


def test_module_available_false_for_unknown_module() -> None:
    """`_module_available` is a clean False, not an exception, for a missing module."""
    assert driver._module_available("sprezzature_this_module_does_not_exist") is False


def test_module_available_true_for_stdlib_module() -> None:
    """Sanity check the positive path against a module guaranteed to be importable."""
    assert driver._module_available("json") is True

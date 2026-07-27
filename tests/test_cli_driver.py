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

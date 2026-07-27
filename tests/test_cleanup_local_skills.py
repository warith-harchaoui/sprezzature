"""
Tests for ``scripts/cleanup_local_skills.py`` — the helper that
audits ``~/.claude/skills/`` and ``~/.opencode/skills/`` for orphan
``front-*`` folders left behind by past renames.

All tests redirect HOME to a per-test ``tmp_path`` so they never
touch the user's real skill directories. The script reads HOME via
``Path.home()``, which reads the ``HOME`` env var on POSIX — we
monkeypatch that.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from skills_manifest import SHIPPED_SKILLS


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
SCRIPT: Path = REPO_ROOT / "scripts" / "cleanup_local_skills.py"


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Redirect ``Path.home()`` to a per-test tmp dir.

    Both runtime skill folders live under HOME (``~/.claude/skills``,
    ``~/.opencode/skills``); monkeypatching HOME isolates the test
    from the developer's machine state.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    # On macOS / some shells, ``Path.home()`` reads ``$HOME`` too.
    # ``getpass.getuser`` is unrelated — the module never calls it.
    return tmp_path


def _install_skill(home: Path, runtime: str, name: str) -> Path:
    """Create a fake ``~/.<runtime>/skills/<name>/`` with a SKILL.md."""
    folder: Path = home / f".{runtime}" / "skills" / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    return folder


def _run(args: list[str]) -> subprocess.CompletedProcess:
    """Invoke the script in a subprocess with the HOME override visible."""
    import os

    env = {**os.environ}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, env=env,
    )


# ── Audit mode ────────────────────────────────────────────────────────────


def test_no_runtime_directories(fake_home: Path) -> None:
    """When neither runtime is installed, the script reports cleanly."""
    proc = _run([])
    assert proc.returncode == 0
    assert "Claude Code" in proc.stdout
    assert "OpenCode" in proc.stdout
    assert "runtime not installed" in proc.stdout
    assert "orphan folders found:   0" in proc.stdout


def test_audit_lists_orphans_without_removing(fake_home: Path) -> None:
    """Audit-only mode names orphan folders but does not touch them."""
    _install_skill(fake_home, "claude", "sprezzature-a11y")        # orphan
    _install_skill(fake_home, "claude", "sprezzature-ui")          # canonical
    proc = _run([])
    assert proc.returncode == 0
    assert "sprezzature-a11y" in proc.stdout
    assert "would rm -rf" in proc.stdout
    assert "Re-run with --apply" in proc.stdout
    # No actual removal happened.
    assert (fake_home / ".claude" / "skills" / "sprezzature-a11y").is_dir()


def test_audit_reports_missing_canonical_skills(fake_home: Path) -> None:
    """Canonical skills not installed are listed as informational."""
    _install_skill(fake_home, "claude", "sprezzature-ui")
    proc = _run([])
    assert proc.returncode == 0
    # ``sprezzature-cli-gui`` is not installed in this test fixture.
    assert "sprezzature-cli-gui" in proc.stdout
    assert "not installed" in proc.stdout


def test_audit_skips_non_front_folders(fake_home: Path) -> None:
    """Folders not starting with ``front-`` are left alone (other skill families)."""
    _install_skill(fake_home, "claude", "sprezzature-ui")
    _install_skill(fake_home, "claude", "other-vendor-skill")
    proc = _run([])
    assert proc.returncode == 0
    # The non-front folder must NOT appear as an orphan.
    out: str = proc.stdout
    assert "other-vendor-skill" not in out


# ── --apply mode ──────────────────────────────────────────────────────────


def test_apply_removes_on_yes(fake_home: Path) -> None:
    """``--apply`` with a 'yes' answer removes the orphan."""
    target: Path = _install_skill(fake_home, "claude", "sprezzature-a11y")
    import os

    env = {**os.environ}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--apply"],
        capture_output=True, text=True, input="y\n", env=env,
    )
    assert proc.returncode == 0
    assert not target.exists(), "orphan should have been removed"
    assert "removed" in proc.stdout
    assert "folders removed:" in proc.stdout


def test_apply_skips_on_no(fake_home: Path) -> None:
    """``--apply`` with a 'no' answer (or empty input) leaves the orphan."""
    target: Path = _install_skill(fake_home, "claude", "sprezzature-a11y")
    import os

    env = {**os.environ}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--apply"],
        capture_output=True, text=True, input="n\n", env=env,
    )
    assert proc.returncode == 0
    assert target.exists(), "orphan must survive a 'no' answer"


def test_apply_default_n_on_empty_input(fake_home: Path) -> None:
    """Default answer is 'no' — empty input leaves the orphan."""
    target: Path = _install_skill(fake_home, "claude", "sprezzature-a11y")
    import os

    env = {**os.environ}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--apply"],
        capture_output=True, text=True, input="\n", env=env,
    )
    assert proc.returncode == 0
    assert target.exists(), "empty input must be treated as 'no'"


# ── CLI surface ───────────────────────────────────────────────────────────


def test_help_advertises_apply_flag(fake_home: Path) -> None:
    """``--help`` documents the ``--apply`` flag."""
    proc = _run(["--help"])
    assert proc.returncode == 0
    assert "--apply" in proc.stdout
    assert "audit" in proc.stdout.lower()


def test_version_flag(fake_home: Path) -> None:
    """``--version`` exits 0 and reports the shared SKILL_VERSION."""
    from _argparse import SKILL_VERSION  # noqa: E402

    proc = _run(["--version"])
    assert proc.returncode == 0
    assert SKILL_VERSION in proc.stdout


# ── Both runtimes ─────────────────────────────────────────────────────────


def test_audits_both_runtimes(fake_home: Path) -> None:
    """The audit visits both ``~/.claude/skills/`` and ``~/.opencode/skills/``."""
    _install_skill(fake_home, "claude", "sprezzature-a11y")
    _install_skill(fake_home, "opencode", "sprezzature-cli-typo")  # orphan
    proc = _run([])
    assert proc.returncode == 0
    assert "Claude Code" in proc.stdout
    assert "OpenCode" in proc.stdout
    assert "sprezzature-a11y" in proc.stdout
    assert "sprezzature-cli-typo" in proc.stdout


def test_every_shipped_skill_is_recognised_as_canonical(fake_home: Path) -> None:
    """
    Every name in ``SKILLS.txt`` is considered canonical and skipped.

    Defensive: catches a future regression where the helper accidentally
    classifies a real shipped skill as orphan.
    """
    for skill in SHIPPED_SKILLS:
        _install_skill(fake_home, "claude", skill)
    proc = _run([])
    assert proc.returncode == 0
    assert "no orphans" in proc.stdout

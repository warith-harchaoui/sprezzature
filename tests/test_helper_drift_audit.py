"""
Tests for the helper-drift audit.

The audit reports; it never converges. Which copy of a helper is right is a
judgement about which repository had the better reason to move, and a script
should not make it.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _audit():
    spec = importlib.util.spec_from_file_location(
        "_helper_drift", ROOT / "scripts" / "audit_helper_drift.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _repo(home: Path, name: str, helper: str, body: str) -> Path:
    path = home / name / "scripts" / helper
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_identical_copies_form_one_group(tmp_path: Path) -> None:
    """No drift, one bucket."""
    module = _audit()
    for name in ("sprezzature-a", "sprezzature-b"):
        _repo(tmp_path, name, "_argparse.py", "same\n")
    groups = module.group_by_content(module.find_copies("_argparse.py", tmp_path))
    assert len(groups) == 1


def test_drift_splits_the_groups(tmp_path: Path) -> None:
    """Two contents, two buckets, and the paths land in the right one."""
    module = _audit()
    _repo(tmp_path, "sprezzature-a", "_argparse.py", "one\n")
    _repo(tmp_path, "sprezzature-b", "_argparse.py", "one\n")
    _repo(tmp_path, "sprezzature-c", "_argparse.py", "two\n")
    groups = module.group_by_content(module.find_copies("_argparse.py", tmp_path))
    assert len(groups) == 2
    sizes = sorted(len(v) for v in groups.values())
    assert sizes == [1, 2]


def test_build_and_venv_copies_are_ignored(tmp_path: Path) -> None:
    """
    A copy under build/ or .venv/ is an artefact, not a source of truth.

    Counting them would report drift between a file and its own installed
    duplicate, which is noise that hides the real thing.
    """
    module = _audit()
    _repo(tmp_path, "sprezzature-a", "_argparse.py", "real\n")
    for junk in (".venv", "build", "__pycache__"):
        path = tmp_path / "sprezzature-a" / junk / "scripts" / "_argparse.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("artefact\n", encoding="utf-8")
    found = module.find_copies("_argparse.py", tmp_path)
    assert len(found) == 1, [str(p) for p in found]


def test_a_lone_copy_is_not_drift(tmp_path: Path) -> None:
    """One copy cannot disagree with anything."""
    module = _audit()
    _repo(tmp_path, "sprezzature-a", "_argparse.py", "only\n")
    assert len(module.find_copies("_argparse.py", tmp_path)) == 1


def test_it_reports_rather_than_converges() -> None:
    """
    The audit has no write path at all.

    Picking a winner among drifted copies is a judgement about which
    repository had the better reason to move on, and this script does not
    have the standing to make it.
    """
    source = (ROOT / "scripts" / "audit_helper_drift.py").read_text(encoding="utf-8")
    for writer in ("write_text", "write_bytes", "copy2", "copytree", "shutil.move", "unlink"):
        assert writer not in source, f"the audit reaches for {writer}"

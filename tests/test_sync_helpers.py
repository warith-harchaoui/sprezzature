"""
Tests for the shared-helper sync.

The helpers are duplicated on purpose, so each skill runs on its own. The
editing must not be: one copy is canonical and the script propagates it. What
these tests pin down is the part that is easy to get wrong — finding the real
copies, not their build artefacts; treating ``SKILL_VERSION`` as belonging to
the repository rather than to the helper; and changing nothing at all unless
``--apply`` is passed.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _audit():
    spec = importlib.util.spec_from_file_location(
        "_sync_helpers", ROOT / "scripts" / "sync_helpers.py"
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


def test_skill_version_is_not_drift(tmp_path: Path) -> None:
    """
    Two copies differing only in ``SKILL_VERSION`` are in step.

    That line names the release of the repository the copy sits in, not of
    the helper: the monorepo skills are at 1.1.0 and the standalone repos at
    1.0.0, and calling that drift would flag every copy forever.
    """
    module = _audit()
    body = 'SKILL_VERSION = "{}"\nX = 1\n'
    _repo(tmp_path, "sprezzature-a", "_argparse.py", body.format("1.0.0"))
    _repo(tmp_path, "sprezzature-b", "_argparse.py", body.format("1.1.0"))
    groups = module.group_by_content(module.find_copies("_argparse.py", tmp_path))
    assert len(groups) == 1


def test_apply_keeps_each_copy_own_version(tmp_path: Path) -> None:
    """Propagating the canonical copy must not re-version the target."""
    module = _audit()
    source = _repo(tmp_path, "sprezzature-audio", "_argparse.py",
                   'SKILL_VERSION = "1.0.0"\nX = 1\n')
    target = _repo(tmp_path, "sprezzature-b", "_argparse.py",
                   'SKILL_VERSION = "1.1.0"\nX = 2\n')
    rendered = module.rendered_for(source.read_text(encoding="utf-8"), target)
    assert 'SKILL_VERSION = "1.1.0"' in rendered
    assert "X = 1" in rendered


def test_version_on_one_side_only_is_refused(tmp_path: Path) -> None:
    """
    Inventing or dropping a ``SKILL_VERSION`` is a real change, not a sync.

    Writing the canonical line into a file that never had one would ship a
    version the package does not claim; dropping it would break the ``-V``
    flag. Either way the script stops and says so.
    """
    module = _audit()
    target = _repo(tmp_path, "sprezzature-b", "_argparse.py", "X = 2\n")
    with pytest.raises(ValueError):
        module.rendered_for('SKILL_VERSION = "1.0.0"\nX = 1\n', target)


def test_it_changes_nothing_without_apply(tmp_path: Path) -> None:
    """A plain run reports drift and leaves every byte where it was."""
    module = _audit()
    a = _repo(tmp_path, "sprezzature-audio", "_argparse.py", "one\n")
    b = _repo(tmp_path, "sprezzature-b", "_argparse.py", "two\n")
    before = (a.read_bytes(), b.read_bytes())
    assert module.main(["--home", str(tmp_path)]) == 1
    assert (a.read_bytes(), b.read_bytes()) == before
    assert module.main(["--home", str(tmp_path), "--apply"]) == 0
    assert b.read_bytes() == a.read_bytes()


def _nested(home: Path, repo: str, relative: str, body: str) -> Path:
    """A copy at an arbitrary depth, not under ``scripts/``."""
    path = home / repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_two_files_of_one_name_in_a_repo_are_ambiguous(tmp_path: Path) -> None:
    """The name, not the content, is what is wrong here.

    ``find_copies`` searches by file name across a whole checkout, which is what
    lets copies sit at different depths. The cost is that a name shared with an
    unrelated file makes that file look like a copy.
    """
    module = _audit()
    _nested(tmp_path, "sprezzature-a", "editor/assistant/_x.py", "canonical\n")
    _nested(tmp_path, "sprezzature-a", "editor/ralph/_x.py", "unrelated\n")
    clashes = module.ambiguous_copies("_x.py", tmp_path)
    assert list(clashes) == ["sprezzature-a"]
    assert len(clashes["sprezzature-a"]) == 2


def test_one_copy_per_repo_is_not_ambiguous(tmp_path: Path) -> None:
    """The ordinary case: many copies, one per checkout, at differing depths."""
    module = _audit()
    _nested(tmp_path, "sprezzature-a", "editor/assistant/_x.py", "same\n")
    _nested(tmp_path, "sprezzature-b", "scripts/_x.py", "same\n")
    assert module.ambiguous_copies("_x.py", tmp_path) == {}


def test_apply_refuses_to_write_over_a_namesake(tmp_path: Path, monkeypatch) -> None:
    """The whole point of the guard, and the reason it is not cosmetic.

    With the check removed, this same call rewrites the unrelated file with the
    canonical content *and returns 0* — measured on 2026-11-01. Propagation is
    precisely the step whose diff nobody reads, so a silent overwrite there
    survives review.
    """
    module = _audit()
    _nested(tmp_path, "sprezzature-a", "editor/assistant/_x.py", "canonical\n")
    namesake = _nested(tmp_path, "sprezzature-a", "editor/ralph/_x.py", "unrelated\n")
    away = _nested(tmp_path, "sprezzature-b", "scripts/_x.py", "stale\n")

    monkeypatch.setattr(module, "CANONICAL", {"_x.py": "sprezzature-a/editor/assistant/_x.py"})
    monkeypatch.setattr(module, "SHARED_HELPERS", ("_x.py",))
    code = module.main(["--apply", "--home", str(tmp_path)])

    assert code != 0, "an ambiguous registration must fail the build, not warn"
    assert namesake.read_text(encoding="utf-8") == "unrelated\n", "the namesake was overwritten"
    assert away.read_text(encoding="utf-8") == "stale\n", (
        "a refused helper must be left entirely alone, not partly propagated"
    )


def test_a_path_suffix_key_names_one_file(tmp_path: Path) -> None:
    """The way out for a helper whose own name is not unique.

    ``repair.py`` names two unrelated files in ``sprezzature-figures``; the two
    path suffixes name one each. This is what lets package modules be shared
    without renaming them.
    """
    module = _audit()
    wanted = _nested(tmp_path, "sprezzature-a", "editor/assistant/repair.py", "shared\n")
    _nested(tmp_path, "sprezzature-a", "editor/ralph/repair.py", "unrelated\n")
    _nested(tmp_path, "sprezzature-b", "editor/assistant/repair.py", "shared\n")

    assert module.ambiguous_copies("editor/assistant/repair.py", tmp_path) == {}
    found = module.find_copies("editor/assistant/repair.py", tmp_path)
    assert wanted in found
    assert not any(p.parent.name == "ralph" for p in found), "the suffix caught a namesake"
    assert len(found) == 2

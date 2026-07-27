"""
Tests for ``SKILLS.txt`` — the canonical manifest of shipped sprezzature-*
skill folders.

The manifest at repo root is the single source of truth read by
``scripts/release.sh``, ``scripts/validate_all.py``, the test
fixtures (``tests/conftest.py``,
``tests/test_validate_skill.py``,
``tests/test_release_packaging.py``,
``tests/test_two_modes_discipline.py``) and any future consumer.

These tests guard against three failure modes:

1. The manifest names a folder that does not exist on disk.
2. A `sprezzature-*` folder ships on disk but is missing from the manifest.
3. The manifest's order and content do not parse cleanly through
   :mod:`skills_manifest` (blank lines / comments matter).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skills_manifest import SHIPPED_SKILLS


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
MANIFEST_PATH: Path = REPO_ROOT / "SKILLS.txt"


def test_manifest_exists() -> None:
    """``SKILLS.txt`` must live at repo root."""
    assert MANIFEST_PATH.is_file(), (
        f"SKILLS.txt missing from repo root ({MANIFEST_PATH})"
    )


def test_manifest_is_non_empty() -> None:
    """The shipped list must contain at least one skill."""
    assert SHIPPED_SKILLS, "SKILLS.txt parses to an empty list"


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_each_manifest_entry_has_a_folder(skill: str) -> None:
    """Every name in the manifest must have a folder + a ``SKILL.md``."""
    folder: Path = REPO_ROOT / skill
    assert folder.is_dir(), f"{skill}: folder named in SKILLS.txt is missing"
    assert (folder / "SKILL.md").is_file(), (
        f"{skill}: folder exists but has no SKILL.md"
    )


def test_no_orphan_skill_folders_on_disk() -> None:
    """
    Every ``sprezzature-*`` folder on disk must be declared in the manifest.

    Catches the failure mode where someone adds a folder but forgets
    to declare it in ``SKILLS.txt``, leaving it out of the release
    bundle / the validator.
    """
    on_disk: set[str] = {
        p.name
        for p in REPO_ROOT.iterdir()
        if p.is_dir() and p.name.startswith("sprezzature-")
        and (p / "SKILL.md").is_file()
    }
    declared: set[str] = set(SHIPPED_SKILLS)
    orphans: set[str] = on_disk - declared
    assert not orphans, (
        f"sprezzature-* folder(s) on disk but absent from SKILLS.txt: {sorted(orphans)}. "
        f"Either add the folder to SKILLS.txt or remove its SKILL.md."
    )


def test_manifest_round_trips_through_loader() -> None:
    """
    The loader must drop comments + blank lines and preserve order.

    Catches the failure mode where someone hand-edits SKILLS.txt and
    introduces a trailing-whitespace line or a stray comment-marker
    that breaks the parse.
    """
    raw_lines: list[str] = MANIFEST_PATH.read_text(
        encoding="utf-8"
    ).splitlines()
    expected: list[str] = []
    for line in raw_lines:
        stripped: str = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        expected.append(stripped)
    assert tuple(expected) == SHIPPED_SKILLS, (
        f"Manifest does not round-trip:\n"
        f"  raw expected: {expected}\n"
        f"  loaded:       {list(SHIPPED_SKILLS)}"
    )


def test_release_sh_reads_the_manifest() -> None:
    """release.sh must not carry a hard-coded SKILLS=(…) tuple any more."""
    body: str = (REPO_ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    # The hard-coded form was a single-line tuple; the new form is a
    # ``while IFS= read`` loop reading from ``SKILLS.txt``. Catch both
    # signs of regression.
    assert "SKILLS.txt" in body, (
        "release.sh stopped reading SKILLS.txt — single source of truth lost."
    )
    assert "SKILLS=(sprezzature-ui sprezzature-cli-gui" not in body, (
        "release.sh has a hard-coded SKILLS tuple — that bypasses SKILLS.txt."
    )


def test_validate_all_imports_the_manifest() -> None:
    """scripts/validate_all.py must source SHIPPED_SKILLS from the manifest."""
    body: str = (
        REPO_ROOT / "scripts" / "validate_all.py"
    ).read_text(encoding="utf-8")
    assert "from skills_manifest import" in body, (
        "validate_all.py does not import from skills_manifest — drift risk."
    )

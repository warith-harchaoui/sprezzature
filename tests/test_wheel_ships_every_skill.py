"""
The suite package names ten skills; each must resolve to a brick that ships it.

Until 2026-11-12 ``sprezzature`` carried copies of the ten skills, and
setuptools learnt which folders to package from three hand-kept blocks in
``pyproject.toml``. The copies moved into the bricks -- ``pip install
sprezzature-maps`` now carries the maps skill -- and this package gathers them
through its dependencies. The guard keeps its spirit under the new contract:
every name in ``SKILL_NAMES`` resolves, through ``skill_path``, to a folder
with a ``SKILL.md``; and the wheel carries no copy of its own, which would be
a second version of the truth.

The installed-wheel half -- that ``skill_path(name)`` resolves once
``pip install sprezzature`` has pulled the bricks from the index -- lives in
``scripts/check_wheels.py``.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from skills_manifest import SHIPPED_SKILLS, SIBLINGS

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_the_wheel_packages_no_copy_of_a_skill() -> None:
    """``pyproject.toml`` packages the ``sprezzature`` module and nothing under it."""
    assert "sprezzature.skills" not in PYPROJECT, (
        "pyproject.toml packages sprezzature.skills.* again: the skills ship "
        "inside their bricks, and a copy here is a second version of the truth."
    )
    assert re.search(r'^packages = \["sprezzature"\]$', PYPROJECT, re.M)


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_the_package_resolves_each_skill_through_its_brick(skill: str) -> None:
    """``skill_path`` lands on the brick's own ``skill/`` folder, with a ``SKILL.md``."""
    from sprezzature import skill_path

    if not (SIBLINGS / skill).is_dir():
        pytest.skip(f"{skill} is not checked out beside this repository")
    try:
        folder = skill_path(skill)
    except (ImportError, LookupError) as exc:
        pytest.skip(f"{skill} is not importable here, or predates its skill: {exc}")
    assert folder.name == "skill" and folder.parent.name == skill.replace("-", "_")
    assert (folder / "SKILL.md").is_file(), f"{folder} has no SKILL.md"


def test_skill_names_matches_the_manifest() -> None:
    """``sprezzature.SKILL_NAMES`` and ``SKILLS.txt`` are the same list."""
    from sprezzature import SKILL_NAMES

    assert list(SKILL_NAMES) == list(SHIPPED_SKILLS), (
        "sprezzature.SKILL_NAMES has drifted from SKILLS.txt:\n"
        f"  SKILL_NAMES: {list(SKILL_NAMES)}\n"
        f"  SKILLS.txt:  {list(SHIPPED_SKILLS)}"
    )

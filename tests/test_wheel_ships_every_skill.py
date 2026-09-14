"""
A skill that is named but not packaged is worse than a skill that is missing.

``sprezzature`` publishes the skills, and setuptools learns which folders to
carry from three hand-maintained blocks in ``pyproject.toml``: ``packages``,
``package-dir`` and ``package-data``. ``SKILL_NAMES`` in the package, and
``SKILLS.txt`` at the root, are two more lists of the same thing. Five places,
all hand-edited, all silent when they disagree.

They did disagree the first time a tenth skill shipped: ``SKILL_NAMES`` grew,
the three pyproject blocks did not, and the wheel advertised a skill whose
folder it did not contain — so ``skill_path("sprezzature-maps")`` returned a
path that does not exist. Every test passed, because a checkout has the folder
sitting right there and nothing reads the packaging tables.

The matching runtime check — that ``skill_path(name)`` really resolves once
the wheel is installed — lives in ``scripts/check_wheels.py``. It cannot run
from a checkout: ``sprezzature/skills/`` is a layout setuptools creates at
build time from ``package-dir``, so in the source tree it does not exist.

Author
------
Project maintainers.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from skills_manifest import SHIPPED_SKILLS

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")


def _module_name(skill: str) -> str:
    """``sprezzature-maps`` → the dotted package setuptools carries it as."""
    return f"sprezzature.skills.{skill.replace('-', '_')}"


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_pyproject_packages_the_skill(skill: str) -> None:
    """Each shipped skill appears in all three setuptools blocks."""
    module = _module_name(skill)
    missing = [
        block
        for block, pattern in (
            ("[tool.setuptools] packages", rf'"{re.escape(module)}"[,\]]'),
            ("[tool.setuptools.package-dir]", rf'"{re.escape(module)}" = "{re.escape(skill)}"'),
            ("[tool.setuptools.package-data]", rf'"{re.escape(module)}" = \['),
        )
        if not re.search(pattern, PYPROJECT)
    ]
    assert not missing, (
        f"{skill} is in SKILLS.txt but missing from {', '.join(missing)} in "
        f"pyproject.toml. The wheel would name the skill and not carry its files."
    )


def test_skill_names_matches_the_manifest() -> None:
    """``sprezzature.SKILL_NAMES`` and ``SKILLS.txt`` are the same list."""
    from sprezzature import SKILL_NAMES

    assert list(SKILL_NAMES) == list(SHIPPED_SKILLS), (
        "sprezzature.SKILL_NAMES has drifted from SKILLS.txt:\n"
        f"  SKILL_NAMES: {list(SKILL_NAMES)}\n"
        f"  SKILLS.txt:  {list(SHIPPED_SKILLS)}"
    )

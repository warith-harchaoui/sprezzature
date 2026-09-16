"""
sprezzature — the suite's skills, installable with pip.

The tools of this suite ship as their own packages (``sprezzature-figures``,
``sprezzature-colors``, and so on); each does one job and installs alone.
This package carries the other half: the **skills** — the folder an agent
reads to know when to reach for a tool, what the house rules are, and which
script to run. Claude Code reads them from ``~/.claude/skills/``, OpenCode
from ``~/.opencode/skills/``.

``pip install sprezzature`` puts them on disk; ``sprezzature-skills
--install`` copies them where an agent will find them, and says what it
changed before changing it.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

__version__ = "1.3.7"

#: Folder names of the shipped skills, in the order SKILLS.txt lists them.
SKILL_NAMES: tuple[str, ...] = (
    "sprezzature-ui",
    "sprezzature-cli-gui",
    "sprezzature-publish",
    "sprezzature-accessibility",
    "sprezzature-colors",
    "sprezzature-vision",
    "sprezzature-audio",
    "sprezzature-ux-laws",
    "sprezzature-figures",
    "sprezzature-maps",
)


def skills_path() -> Path:
    """
    The directory holding the installed skill folders.

    Returns
    -------
    pathlib.Path
        Path to the ``skills`` directory inside this package.
    """
    return Path(__file__).resolve().parent / "skills"


def skill_path(name: str) -> Path:
    """
    The directory of one skill, as shipped.

    A skill is read from a folder called ``sprezzature-figures``; a Python
    package cannot be called that, because of the hyphen. So the shipped
    folders carry underscores and the hyphen comes back when they are
    installed — the agent never sees the difference.

    Parameters
    ----------
    name : str
        Skill folder name, e.g. ``"sprezzature-figures"``.

    Returns
    -------
    pathlib.Path
        Path to that skill's folder inside this package.

    Raises
    ------
    KeyError
        If `name` is not one of :data:`SKILL_NAMES`.
    """
    if name not in SKILL_NAMES:
        raise KeyError(f"{name!r} is not a sprezzature skill; try one of {SKILL_NAMES}")
    return skills_path() / name.replace("-", "_")

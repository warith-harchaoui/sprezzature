"""
sprezzature — the suite's skills, installable with pip.

The tools of this suite ship as their own packages (``sprezzature-figures``,
``sprezzature-colors``, and so on); each does one job and installs alone.
Each also ships its **skill** — the folder an agent reads to know when to
reach for a tool, what the house rules are, and which command to run —
inside its own package, since 2026-11-12: ``pip install sprezzature-maps``
carries the maps skill, and ``sprezzature-maps-skill --install`` puts it
where an agent reads it. Claude Code reads skills from
``~/.claude/skills/``, OpenCode from ``~/.opencode/skills/``.

This package installs the ten bricks with one ``pip install`` and gathers
their skills: ``sprezzature-skills --install`` copies all ten where an agent
will find them, and says what it changed before changing it. It holds no
copy of its own; a copy here is a second version of the truth.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib
from pathlib import Path

__version__ = "1.9.0"

#: Folder names of the shipped skills, in the order SKILLS.txt lists them.
SKILL_NAMES: tuple[str, ...] = (
    "sprezzature-ui",
    "sprezzature-cli-gui",
    "sprezzature-publish",
    "sprezzature-accessibility",
    "sprezzature-colors",
    "sprezzature-audio",
    "sprezzature-ux-laws",
    "sprezzature-figures",
    "sprezzature-maps",
    "sprezzature-video",
)


def skill_path(name: str) -> Path:
    """
    The folder of one skill, as its brick ships it.

    Parameters
    ----------
    name : str
        Skill folder name, e.g. ``"sprezzature-figures"``.

    Returns
    -------
    pathlib.Path
        The ``skill`` folder inside that brick's installed package.

    Raises
    ------
    KeyError
        If `name` is not one of :data:`SKILL_NAMES`.
    ModuleNotFoundError
        If the brick is not installed.
    LookupError
        If the installed brick predates the skill moving into it, and so
        ships none.
    """
    if name not in SKILL_NAMES:
        raise KeyError(f"{name!r} is not a sprezzature skill; try one of {SKILL_NAMES}")
    package = importlib.import_module(name.replace("-", "_"))
    if not hasattr(package, "skill_path"):
        version = getattr(package, "__version__", "?")
        raise LookupError(
            f"{name} {version} ships no skill; upgrade it: pip install -U {name}"
        )
    return Path(package.skill_path())

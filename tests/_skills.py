"""
Where a test finds a shipped skill, now that it lives in its brick.

Since 2026-11-12 the ten skills ship inside their bricks, at
``sprezzature-<brick>/sprezzature_<brick>/skill/``, and this repository holds
no copy. A test reading a ``SKILL.md`` or a reference asks :func:`skill_file`,
which skips -- rather than fails -- when the brick is not checked out beside
this one: a machine holding this clone alone has nothing to read, and CI
brings the ten in with ``scripts/fetch_siblings.sh``.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skills_manifest import SIBLINGS, skill_dir


def skill_file(name: str, *parts: str) -> Path:
    """
    A path inside a shipped skill, or a skip when its brick is absent.

    Parameters
    ----------
    name : str
        Skill folder name, e.g. ``"sprezzature-maps"``.
    *parts : str
        Path components under the skill folder, e.g. ``"SKILL.md"``.

    Returns
    -------
    pathlib.Path
        The path, which the caller may still find missing: a brick that is
        checked out and lacks its skill is a failure, not a skip.
    """
    if not (SIBLINGS / name).is_dir():
        pytest.skip(f"{name} is not checked out beside this repository")
    return skill_dir(name).joinpath(*parts)

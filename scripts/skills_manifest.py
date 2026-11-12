"""
skills_manifest
===============

Read ``SKILLS.txt`` — the canonical list of sprezzature-* skill folder names
shipped from this repo — and expose it to every consumer (release
script, test fixtures, validators).

Why a tiny module instead of hand-typing the list eight times: the
list used to live in seven places (``release.sh``, ``validate_all.py``,
``tests/conftest.py``, ``tests/test_validate_skill.py``,
``tests/test_release_packaging.py``, ``tests/test_cli_help.py``, and
the new ``tests/test_two_modes_discipline.py``). Adding skill #9
silently passed in any subset of the seven, then failed CI on the
others. One source of truth removes the failure mode entirely.

Usage
-----
::

    # Python:
    from skills_manifest import SHIPPED_SKILLS
    for name in SHIPPED_SKILLS: ...

    # Bash (release.sh):
    while read -r line; do ...; done < <(
      grep -v '^[[:space:]]*#' SKILLS.txt | grep -v '^[[:space:]]*$'
    )

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path


#: Path to the manifest. The module sits at ``scripts/`` so the parent
#: of its parent is the repo root, where ``SKILLS.txt`` lives.
_MANIFEST_PATH: Path = (
    Path(__file__).resolve().parent.parent / "SKILLS.txt"
)


def _load() -> tuple[str, ...]:
    """
    Parse ``SKILLS.txt`` into a tuple of skill folder names.

    Skips blank lines and lines starting with ``#``. Order is preserved
    so consumers that care about packaging order (release.sh) see the
    file's order.

    Returns
    -------
    tuple of str
        Skill folder names in declaration order.

    Raises
    ------
    FileNotFoundError
        If ``SKILLS.txt`` is missing — the manifest is required, not
        optional, so a missing file is a structural error and the
        helper refuses to fall back to a hard-coded list.
    """
    raw: str = _MANIFEST_PATH.read_text(encoding="utf-8")
    out: list[str] = []
    for line in raw.splitlines():
        stripped: str = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(stripped)
    return tuple(out)


#: The shipped skills, in canonical declaration order. Read eagerly at
#: import time — the file is < 200 bytes; the cost is irrelevant and
#: imports of this module become a single tuple lookup downstream.
SHIPPED_SKILLS: tuple[str, ...] = _load()

#: The directory holding this checkout and the ten brick checkouts beside it.
SIBLINGS: Path = _MANIFEST_PATH.parent.parent


def skill_dir(name: str, siblings: Path = SIBLINGS) -> Path:
    """
    The folder of one shipped skill, inside its brick's package.

    Since 2026-11-12 a skill lives in its brick, at
    ``sprezzature-maps/sprezzature_maps/skill/``, so that ``pip install
    sprezzature-maps`` carries it; this repository holds no copy. Every
    script and test here that reads a ``SKILL.md`` or its ``references/``
    asks this function, so the location is written once.

    Parameters
    ----------
    name : str
        Skill folder name, e.g. ``"sprezzature-maps"``.
    siblings : pathlib.Path, optional
        Directory holding the brick checkouts; the parent of this one by
        default.

    Returns
    -------
    pathlib.Path
        ``<siblings>/<name>/<package>/skill``. It may not exist: a machine
        holding this checkout alone has no brick beside it.
    """
    return siblings / name / name.replace("-", "_") / "skill"


__all__ = ("SHIPPED_SKILLS", "SIBLINGS", "skill_dir")

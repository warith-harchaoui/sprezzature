"""
retrieve — static reference-document lookup for each skill.

Skeleton for Phase 5.  The mapping from skill name to reference files is
already explicit in each ``SKILL.md``; this module will expose it as a
programmatic lookup once Phase 5 is implemented.

Author
------
Warith Harchaoui <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

from pathlib import Path


def get_references(skill: str) -> list[Path]:
    """
    Return the reference files for a named skill.

    Parameters
    ----------
    skill : str
        Skill folder name, e.g. ``"sprezzature-figures"``.

    Returns
    -------
    list of Path
        Paths to the reference documents for the skill.  Returns an empty
        list until Phase 5 is implemented.

    Examples
    --------
    >>> get_references("sprezzature-figures")
    []
    """
    # Phase 5 placeholder.
    return []

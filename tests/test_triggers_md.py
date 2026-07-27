"""
Tests for ``TRIGGERS.md`` — the generated trigger-phrase index.

The file is a deterministic projection of every shipped skill's
``SKILL.md`` description. Hand-editing it is forbidden by
convention; CI enforces that convention via these tests.

Covers:

* Every shipped skill in ``SKILLS.txt`` has an entry in
  ``build_triggers.STATUS`` and ``build_triggers.WHAT_IT_DOES``.
* The committed ``TRIGGERS.md`` matches what
  ``build_triggers.build()`` produces — no manual drift.
* Every shipped skill appears in the rendered table at least once.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import pytest

from build_triggers import STATUS, WHAT_IT_DOES, build
from skills_manifest import SHIPPED_SKILLS


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
TRIGGERS: Path = REPO_ROOT / "TRIGGERS.md"


def test_triggers_md_exists() -> None:
    """The committed TRIGGERS.md must live at repo root."""
    assert TRIGGERS.is_file(), (
        f"TRIGGERS.md missing from repo root ({TRIGGERS}). "
        f"Run `python scripts/build_triggers.py`."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_status_map_covers_every_skill(skill: str) -> None:
    """Adding skill #9 forces a status decision at PR time."""
    assert skill in STATUS, (
        f"Skill '{skill}' missing from build_triggers.STATUS. "
        f"Add an entry before merging."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_what_it_does_covers_every_skill(skill: str) -> None:
    """Each skill must carry a one-line ``what it does`` summary."""
    assert skill in WHAT_IT_DOES, (
        f"Skill '{skill}' missing from build_triggers.WHAT_IT_DOES. "
        f"Add a one-sentence summary before merging."
    )


def test_committed_file_matches_generator() -> None:
    """
    The committed ``TRIGGERS.md`` must equal the generator's output.

    If this fails, someone hand-edited the file or changed a
    SKILL.md description without re-running the generator. Run
    ``python scripts/build_triggers.py`` and commit both files
    together.
    """
    expected: str = build()
    actual: str = TRIGGERS.read_text(encoding="utf-8")
    assert actual == expected, (
        "TRIGGERS.md is out of sync with the generator. Run "
        "`python scripts/build_triggers.py` and commit the result. "
        "The diff lives in the test output above."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_every_skill_appears_in_the_table(skill: str) -> None:
    """Every shipped skill produces at least one row in the table."""
    body: str = TRIGGERS.read_text(encoding="utf-8")
    # ``**front-X**`` is the bolded skill name we render in the
    # Activates column. Match against that exact form.
    assert f"**{skill}**" in body, (
        f"Skill '{skill}' has no row in TRIGGERS.md — its SKILL.md "
        f"description likely lacks quoted trigger phrases."
    )

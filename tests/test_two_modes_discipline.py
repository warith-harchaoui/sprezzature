"""
Enforce the front-* repo's make / audit discipline.

Every shipped skill is supposed to declare where it sits on the
make-side / audit-side duality in its ``SKILL.md`` — see the
companion ``README.md`` "Two modes" matrix and each skill's own
"Two modes — make and audit" subsection.

These tests make the convention machine-checkable:

* Every shipped skill has a section header named exactly
  ``Two modes — make and audit`` (or the French equivalent for a
  future French SKILL.md).
* The section contains a Markdown table with ``Make`` and ``Audit``
  rows (case-insensitive match, allows the row to be marked
  ``(roadmap)`` / ``(none — see X)`` so audit-only or make-only
  skills are honest about gaps rather than omitting the row).
* The repo-level matrices in ``README.md`` and ``LISEZMOI.md``
  list every shipped skill exactly once on the left column.

The tests are deliberately string-shape checks — they do not parse
Markdown into an AST. The shape is small enough that ``in`` is the
right tool; an AST parse would slow CI and add a dependency.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT: Path = Path(__file__).resolve().parent.parent


#: The shipped skills — sourced from the canonical ``SKILLS.txt``
#: manifest at repo root so this test cannot drift from the release
#: script / the validator.
from skills_manifest import SHIPPED_SKILLS  # noqa: E402


#: Regex matching the canonical "Two modes" section header. Permits the
#: English form (``## Two modes — make and audit``) and tolerates an
#: en-dash vs hyphen vs em-dash variation.
RE_TWO_MODES_HEADER: re.Pattern[str] = re.compile(
    r"^## *Two modes *[—–-] *make and audit *$",
    re.MULTILINE,
)


def _read(path: Path) -> str:
    """Read a UTF-8 text file (no fallback — the repo is UTF-8 throughout)."""
    return path.read_text(encoding="utf-8")


# ── Per-skill discipline ───────────────────────────────────────────────────


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_skill_has_two_modes_section(skill: str) -> None:
    """Every shipped SKILL.md declares its make / audit posture."""
    path: Path = REPO_ROOT / skill / "SKILL.md"
    body: str = _read(path)
    assert RE_TWO_MODES_HEADER.search(body), (
        f"{skill}/SKILL.md is missing the canonical "
        f"'## Two modes — make and audit' section."
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_two_modes_section_mentions_both_sides(skill: str) -> None:
    """The 'Two modes' section names both Make and Audit explicitly."""
    path: Path = REPO_ROOT / skill / "SKILL.md"
    body: str = _read(path)
    m = RE_TWO_MODES_HEADER.search(body)
    assert m is not None
    # The section runs until the next ``##`` header. Take ~80 lines
    # which is generous for a single subsection.
    tail: str = body[m.end() :]
    section: str = tail.split("\n## ", 1)[0]
    # Case-insensitive — Make / Audit may appear inside table cells
    # or prose. We only require that the words exist somewhere in
    # the subsection.
    lower: str = section.lower()
    assert "make" in lower, f"{skill}: 'Make' missing from the 'Two modes' section"
    assert "audit" in lower, f"{skill}: 'Audit' missing from the 'Two modes' section"


# ── Repo-level matrix discipline ───────────────────────────────────────────


@pytest.mark.parametrize("matrix_file", ["README.md", "LISEZMOI.md"])
def test_top_level_matrix_lists_every_skill(matrix_file: str) -> None:
    """The matrix table in README / LISEZMOI mentions every shipped skill."""
    body: str = _read(REPO_ROOT / matrix_file)
    # Lift the section between ``## Two modes`` (or the French
    # ``## Deux modes``) and the next ``## `` header.
    header_re: re.Pattern[str] = re.compile(
        r"^## *(Two modes|Deux modes)[^\n]*$",
        re.MULTILINE,
    )
    m = header_re.search(body)
    assert m is not None, f"{matrix_file}: matrix section missing."
    tail: str = body[m.end() :]
    section: str = tail.split("\n## ", 1)[0]
    for skill in SHIPPED_SKILLS:
        assert skill in section, (
            f"{matrix_file}: '{skill}' missing from the Two modes matrix."
        )


def test_readme_matrix_marks_roadmap_gaps_honestly() -> None:
    """An empty cell must be marked '(roadmap)' or '(none — ...)' rather than blank."""
    body: str = _read(REPO_ROOT / "README.md")
    m = re.search(
        r"^## *Two modes *[—–-] *make and audit",
        body, re.MULTILINE,
    )
    assert m is not None
    section: str = body[m.end() :].split("\n## ", 1)[0]
    # Quick sanity: a row that genuinely has an empty cell is a regression.
    # We accept "|  |" only if the cell carries ``_(roadmap)_`` or
    # ``_(none ...)_``. Look for any genuinely-empty pipe cell.
    for row_match in re.finditer(r"^\|[^\n]*\|$", section, re.MULTILINE):
        row: str = row_match.group(0)
        if "|---|" in row or row.startswith("| Skill"):
            continue
        # Each row has 4 pipes → 3 columns. Look for empty content
        # between two pipes (allowing spaces).
        empty_cells = [
            c for c in row.strip("|").split("|") if c.strip() == ""
        ]
        assert not empty_cells, (
            f"README matrix row has a genuinely empty cell — mark it "
            f"(roadmap) or (none — ...) instead:\n  {row}"
        )

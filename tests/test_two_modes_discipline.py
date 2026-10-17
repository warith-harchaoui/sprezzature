"""
Enforce the sprezzature-* repo's make / audit discipline.

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
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
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
#: English form (``## Two modes: make and audit``) and tolerates a
#: colon vs en-dash vs hyphen vs em-dash separator.
RE_TWO_MODES_HEADER: re.Pattern[str] = re.compile(
    r"^## *Two modes *[:—–-] *make and audit *$",
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
        r"^## *Two modes *[:—–-] *make and audit",
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


# ── The declaration must be honest ─────────────────────────────────────────
#
# The tests above check that the section exists and names both sides. They
# were satisfied by a row that reads
#
#     | **Audit** — gate the presence of <track> | _(see sprezzature-accessibility/scripts/lint_a11y.py)_ |
#
# which is a pointer at another brick's tool, not an audit this brick ships.
# That is a legitimate thing to write — bricks should route rather than
# duplicate — but it is not a brick holding both halves, and a reader
# skimming the matrix cannot tell the two apart. These two tests make the
# difference visible.


def _two_modes_rows(skill: str) -> list[str]:
    """The table rows of a skill's 'Two modes' section."""
    body = _read(REPO_ROOT / skill / "SKILL.md")
    match = RE_TWO_MODES_HEADER.search(body)
    assert match is not None
    section = body[match.end():].split("\n## ", 1)[0]
    return [
        line for line in section.splitlines()
        if line.startswith("|") and "---" not in line
    ]


#: A row that hands the job to another brick rather than shipping a tool.
RE_DELEGATES = re.compile(r"\(see\s+`?sprezzature-|Pair with\s+`?sprezzature-", re.I)

#: A row that admits the half is not built yet.
RE_GAP = re.compile(r"roadmap|none\s*[—–-]|\(none", re.I)


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_every_cross_reference_names_a_brick_that_exists(skill: str) -> None:
    """
    A row may route to a sibling, but not to one that is gone.

    When `sprezzature-vision` merged into `sprezzature-accessibility`, four
    other skills still pointed readers at it by name. A pointer at a brick
    nobody can install is worse than no pointer: it sends someone looking for
    a package that does not exist.
    """
    for row in _two_modes_rows(skill):
        for named in re.findall(r"sprezzature-[a-z0-9-]+", row):
            named = named.rstrip("-")
            # A console script is a brick name plus a suffix:
            # `sprezzature-accessibility-lint` is the lint command, not a
            # tenth brick. The first version of this test flagged both, which
            # is a guard someone switches off rather than fixes. So the
            # question is whether some shipped brick is a prefix of what was
            # written, not whether the whole token is a brick.
            assert any(
                named == brick or named.startswith(brick + "-")
                for brick in SHIPPED_SKILLS
            ), (
                f"{skill}'s 'Two modes' table points at {named!r}, which "
                f"belongs to no brick in SKILLS.txt"
            )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_a_brick_whose_only_audit_is_someone_elses_says_so(skill: str) -> None:
    """
    Delegating every audit row is allowed; pretending it is your own is not.

    The house philosophy is make **and** audit. A brick that only makes is a
    real state of affairs — `sprezzature-maps` says so in as many words, with
    `_(none here — see sprezzature-figures)_`, and that honesty is the point.
    What this refuses is the middle case: an Audit row that looks like a
    shipped tool and turns out, on reading, to be a pointer at a sibling.
    """
    audit_rows = [
        row for row in _two_modes_rows(skill)
        if re.search(r"\|\s*\*\*Audit\*\*", row)
    ]
    assert audit_rows, f"{skill}: no Audit row at all"

    own = [
        row for row in audit_rows
        if not RE_DELEGATES.search(row) and not RE_GAP.search(row)
    ]
    if own:
        return
    # Every audit row delegates or is empty: the row must say so plainly, so
    # the matrix does not read as "both halves shipped".
    assert any(RE_GAP.search(row) for row in audit_rows), (
        f"{skill} ships no audit of its own — every Audit row points at "
        f"another brick. That is allowed, but the row has to say so: mark it "
        f"`(roadmap)` or `_(none here — see <brick>)_` the way "
        f"sprezzature-maps does, so the matrix is not read as both halves "
        f"shipped."
    )

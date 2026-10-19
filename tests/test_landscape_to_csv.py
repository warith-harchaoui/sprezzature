"""
The converter must not quietly transpose a table the wrong way.

`scripts/landscape_to_csv.py` turns a LANDSCAPE star table into a
`standpoint` input. It invents no ratings — the numbers in those tables were
argued over when they were written and are already published — so the only
thing it can get wrong is the *shape*, and getting the shape wrong produces
arithmetic over nonsense that runs without complaint.

Both failures happened while it was being written:

* collecting star rows and the last header-looking row seen, which in a
  document with several tables married one table's header to another's body —
  `sprezzature-figures` came out as "22 tools × 37 criteria" for a table that
  is neither;
* transposing unconditionally, which is right for `sprezzature-colors`
  (criteria down the side) and wrong for `sprezzature-figures` (tools down the
  side). The output's rows were then "Free or open source" and its columns
  were tool names.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from landscape_to_csv import (  # noqa: E402
    MIN_DISCARDED,
    convert,
    projectable,
    star_table,
)

CRITERIA_DOWN = """
# Landscape

Some prose, and a first table that is not the rated one:

| Tool | Type |
|---|---|
| **sprezzature-colors** | audit |
| axe-core | runtime |

And the rated comparison:

| Dimension | sprezzature-colors | axe-core |
|---|---|---|
| Contrast coverage | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| CVD simulation | ⭐⭐⭐⭐ | N/A |
"""

TOOLS_DOWN = """
# Landscape

| Tool | Free or open source | Chart breadth |
|---|---|---|
| **sprezzature-figures** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Matplotlib | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Highcharts | ⭐⭐ | ⭐⭐⭐⭐⭐ |
"""


def test_criteria_down_the_side_is_transposed() -> None:
    """Tools must end up as rows, whichever way the document wrote them."""
    criteria, tools = star_table(CRITERIA_DOWN)
    assert criteria == ["Contrast coverage", "CVD simulation"]
    assert [name for name, _ in tools] == ["sprezzature-colors", "axe-core"]
    assert dict(tools)["sprezzature-colors"] == ["4", "4"]


def test_tools_down_the_side_is_left_alone() -> None:
    """The other orientation is equally valid and must not be flipped."""
    criteria, tools = star_table(TOOLS_DOWN)
    assert criteria == ["Free or open source", "Chart breadth"]
    assert [name for name, _ in tools] == [
        "sprezzature-figures",
        "Matplotlib",
        "Highcharts",
    ]
    assert dict(tools)["Highcharts"] == ["2", "5"]


def test_a_cell_that_is_not_rated_becomes_the_floor() -> None:
    """`N/A` means "does not do this", which on a 1-5 scale is a 1.

    A blank was the first answer, on the strength of standpoint's documented
    "a missing rating never flatters an option" — it fills a blank with the
    column's minimum. On these tables that promise does not hold, because the
    columns are sparse: in colors' comparison only two of four tools rate
    "Token export" at all, so the minimum is a 3, and axe-core came out of
    the map claiming 3 out of 5 for something it does not do.
    """
    _criteria, tools = star_table(CRITERIA_DOWN)
    assert dict(tools)["axe-core"] == ["5", "1"]


def test_the_rated_table_is_found_past_an_unrated_one() -> None:
    """Several of these documents open with an orientation table.

    Picking the first table would make the output depend on where somebody
    chose to introduce the subject.
    """
    criteria, _tools = star_table(CRITERIA_DOWN)
    assert "Type" not in criteria


def test_a_document_with_no_star_table_says_so() -> None:
    """A qualitative landscape is a legitimate thing to have."""
    assert star_table("# Landscape\n\nProse only, no table.\n") is None


@pytest.mark.parametrize(
    "landscape",
    sorted(
        path
        for path in [Path(__file__).resolve().parent.parent / "LANDSCAPE.md"]
        + list(
            Path(__file__)
            .resolve()
            .parent.parent.parent.glob("sprezzature-*/LANDSCAPE.md")
        )
        if path.is_file()
    ),
    ids=lambda p: p.parent.name,
)
def test_every_real_landscape_converts_to_a_rectangle(landscape: Path) -> None:
    """Whatever comes out has to be a table, with the brick in it.

    The two bugs above both produced something rectangular and wrong, so the
    assertion that catches them is not "is it a rectangle" but "is this brick
    one of the rows" — the subject of a positioning map cannot be absent from
    it.
    """
    table = star_table(landscape.read_text(encoding="utf-8"))
    if table is None:
        pytest.skip(f"{landscape.parent.name} has a qualitative landscape")
    criteria, tools = table
    names = [name for name, _ in tools]
    widths = {len(values) for _name, values in tools}
    assert widths == {len(criteria)}, "ragged rows"
    assert any(name.startswith("sprezzature") for name in names), (
        f"no sprezzature row in {landscape.parent.name}: the table was read "
        f"in the wrong orientation, and the subject of the map is missing "
        f"from it. Rows read: {names[:4]}"
    )


def test_two_axes_must_actually_discard_something() -> None:
    """A map is a summary only when the projection throws directions away.

    With four options a table holds three independent directions, so two axes
    keep two of three — `sprezzature-accessibility` came out at 99.4 % of the
    variance, which reads as a strong result and is really just arithmetic
    about having had almost nowhere to project from.
    """
    assert projectable(4, 5) == 1  # accessibility, colors
    assert projectable(3, 5) == 0  # ux-laws
    assert projectable(6, 7) == 3  # maps — the smallest that qualifies
    assert projectable(37, 22) == 20  # figures
    assert MIN_DISCARDED == 3


def test_a_table_too_small_is_refused_rather_than_drawn(tmp_path: Path) -> None:
    """Three options produce no CSV, and say so on stderr."""
    small = tmp_path / "LANDSCAPE.md"
    small.write_text(
        "| Dimension | sprezzature-x | A | B |\n"
        "|---|---|---|---|\n"
        "| One | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ |\n"
        "| Two | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |\n",
        encoding="utf-8",
    )
    assert convert(small) is None
    assert not (tmp_path / "assets" / "landscape.csv").exists()

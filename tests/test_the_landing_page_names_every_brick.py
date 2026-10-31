"""Every list of the suite on the landing page names all ten bricks.

The defect this guards. ``web/index.html`` carried the ten packages twice: a
``SKILLS`` array feeding the skill cards, complete; and, five screens above
it, a hand-typed "tool ecosystem" list naming **seven**. ``sprezzature-ui``,
``sprezzature-publish`` and ``sprezzature-video`` were missing from the
shorter one, and nothing on the page, in the build, or in this suite could
notice: both lists rendered, neither raised, and the heading two sections
down still said "The ten skills".

Two copies of one fact drift, and the copy that drifts is always the one
nobody is looking at. So the list is now derived from ``SKILLS`` at runtime
and this asserts the property that repair was for -- stated on what the page
says rather than on how it is built, because a later rewrite is free to build
it some other way and must not be free to lose a brick.

Both languages, because ``web/fr/index.html`` is a translation and had
inherited exactly the same seven.

The count itself is not hard-coded here. It is read from the sibling
checkouts on disk, so adding an eleventh brick does not require remembering
this file -- the suite's size is a fact about the tree, not a number typed
into a test.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"

#: The landing pages that carry the suite's own inventory.
_PAGES = ("index.html", "fr/index.html")

#: A package name as it appears anywhere on the page.
_BRICK = re.compile(r"sprezzature-[a-z][a-z-]*[a-z]")

#: Names that match the pattern but are not bricks: the hub's own repository,
#: and the two helper spellings the pages use in prose.
_NOT_A_BRICK = frozenset({"sprezzature-ai", "sprezzature-local", "sprezzature-cli"})


def _bricks_on_disk() -> frozenset[str]:
    """Return every brick this repository carries, by its packaged skill.

    The tree is the source of truth for how many bricks there are, so the
    count is never typed into this file. A directory counts when it holds a
    ``SKILL.md``: that is what makes it a brick rather than a scratch clone or
    a build artefact. They live inside the hub, not beside it -- the sibling
    checkouts under ``$HOME`` are the libraries, and only the hub assembles
    the skills.
    """
    return frozenset(
        path.name
        for path in REPO_ROOT.glob("sprezzature-*")
        if (path / "SKILL.md").is_file()
    )


def _skills_array(page: str) -> frozenset[str]:
    """Return the package ids in the page's own ``SKILLS`` array."""
    html = (WEB / page).read_text(encoding="utf-8")
    block = re.search(r"const SKILLS = \[(.*?)\n    \];", html, re.DOTALL)
    assert block, f"{page}: no SKILLS array -- this guard is reading the wrong file"
    return frozenset(_BRICK.findall(block.group(1)))


@pytest.mark.parametrize("page", _PAGES)
def test_the_skills_array_holds_every_brick_in_the_tree(page: str) -> None:
    """The array the cards are built from names every brick on disk."""
    on_disk = _bricks_on_disk()
    if not on_disk:
        pytest.skip("no sibling brick checkouts beside this repository")
    missing = sorted(on_disk - _skills_array(page))
    assert not missing, (
        f"{page}: the SKILLS array does not name {missing}, so the skill "
        f"cards -- and now the ecosystem list derived from them -- are short "
        f"a brick that exists in the tree"
    )


@pytest.mark.parametrize("page", _PAGES)
def test_no_second_inventory_names_fewer_bricks(page: str) -> None:
    """No ``<ul>`` on the page lists packages and stops short of all of them.

    The shape of the original defect, stated generally: a list that is *about*
    the packages and yet names fewer than the array does.

    An inventory is a list whose bricks are **linked** -- each one a door to
    the package. That is what separates it from prose: the "Ask, in plain
    English" examples name three bricks in ``<strong>`` to illustrate three
    trigger phrases, and naming a fourth would not improve them. A list of
    one or two links is a pair of pointers, not a catalogue, so three is the
    floor for calling something an inventory at all.
    """
    html = (WEB / page).read_text(encoding="utf-8")
    declared = _skills_array(page)
    short: list[str] = []
    for index, block in enumerate(re.finditer(r"<ul\b.*?</ul>", html, re.DOTALL)):
        linked = " ".join(re.findall(r"<a\b[^>]*>.*?</a>", block.group(0), re.DOTALL))
        named = frozenset(_BRICK.findall(linked)) - _NOT_A_BRICK
        if len(named) < 3:
            continue
        missing = sorted(declared - named)
        if missing:
            short.append(f"list #{index} names {len(named)} and is missing {missing}")
    assert not short, (
        f"{page}: a second inventory of the packages disagrees with the first. "
        f"Two hand-kept copies of one fact drift, and the one that drifts is "
        f"the one nobody reads: " + "; ".join(short)
    )

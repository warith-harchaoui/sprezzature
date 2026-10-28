"""
The counts on ``packages.html`` are read off the things they count.

Three numbers on that page are claims about the suite, and all three had gone
stale by 2026-10-28 without anything noticing:

* **how many packages hold the five-surface contract.** The prose said nine in
  both languages while the table under it listed ten rows and the ``all``
  extra named ten requirements. ``sprezzature-video`` joined on 2026-10-24,
  was added to the table, to the schema and to the card deck, and the sentence
  introducing the table kept the old number.
* **how many packages ``pip install 'sprezzature[all]'`` installs.** Same
  number, same page, same drift.
* **how many kits ``sprezzature-figures`` ships.** The cell said 125 while the
  paragraph four lines above said 160 and the gallery linked 160. Three
  numbers for one fact, which is the tell that none of them was checked: a
  single stale number is a fact that aged, several disagreeing ones mean
  nobody could check any of them.

``test_the_suite_quotes_the_real_catalogue_size`` covers the catalogue and the
gallery and did not see this. Its regex counts a number only when a catalogue
word follows it, and ``kits`` is not one of those words; and it never reads
``packages.html`` at all. So the gap was a page outside the guard's list
quoting a number in a word the guard did not know, which is why this is a
second file rather than a wider regex: what is being counted here is the
suite, not the catalogue.

Both languages are checked against the same sources rather than against each
other, so a twin that drifts fails on its own line instead of dragging its
pair down with it.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Numbers are spelled out in this prose, in both languages. Counting stops
#: well short of any plausible suite size on purpose: a word outside this map
#: is a sentence this guard was not written for, and it says so rather than
#: passing.
_WORDS: dict[str, dict[int, str]] = {
    "en": {7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"},
    "fr": {7: "sept", 8: "huit", 9: "neuf", 10: "dix", 11: "onze", 12: "douze"},
}

#: The sentences that quote how many packages there are, by language. Each
#: pattern captures the spelled-out number and nothing else.
_PACKAGE_CLAIMS: dict[str, tuple[str, ...]] = {
    "en": (r"all (\w+) packages hold it", r"installs all (\w+)\."),
    "fr": (r"les (\w+) paquets le tiennent", r"installe les (\w+)\."),
}

_ROW_RE = re.compile(r'<td class="px-3 py-2 font-mono text-xs">(sprezzature-[\w-]+)</td>')
_KIT_CELL_RE = re.compile(
    r"sprezzature-figures</td><td[^>]*>(\d+)\s+kits</td>"
)
_KIT_LINK_RE = re.compile(r'href="(?:\.\./)?kits/(?:fr/)?([\w.-]+\.zip)"')


def _page(lang: str, name: str) -> str:
    where = REPO_ROOT / "web" / name if lang == "en" else REPO_ROOT / "web" / "fr" / name
    return where.read_text(encoding="utf-8")


def _all_extra() -> int:
    """How many requirements ``sprezzature[all]`` names."""
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10 — tomllib landed in 3.11
        import tomli as tomllib  # type: ignore[no-redef]

    table = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return len(table["project"]["optional-dependencies"]["all"])


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_the_page_says_how_many_packages_its_own_table_lists(lang: str) -> None:
    """The sentence introducing the table counts the rows of that table."""
    page = _page(lang, "packages.html")
    rows = len(_ROW_RE.findall(page))
    assert rows, "the surfaces table has no rows, or its markup changed"

    want = _WORDS[lang].get(rows)
    assert want, f"{rows} packages is outside the range this guard spells out"

    for pattern in _PACKAGE_CLAIMS[lang]:
        found = re.search(pattern, page)
        assert found, f"{lang}: nothing matches {pattern!r} any more"
        assert found.group(1) == want, (
            f"{lang}/packages.html says {found.group(1)!r} where its table "
            f"lists {rows} packages ({want!r})"
        )


def test_the_table_lists_what_the_all_extra_installs() -> None:
    """The page and ``pyproject.toml`` describe one suite, not two."""
    rows = len(_ROW_RE.findall(_page("en", "packages.html")))
    assert rows == _all_extra(), (
        f"the surfaces table lists {rows} packages; "
        f"sprezzature[all] names {_all_extra()}"
    )


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_the_kit_cell_counts_the_kits_the_gallery_links(lang: str) -> None:
    """One kit per figure, and the cell says how many figures that is."""
    cell = _KIT_CELL_RE.search(_page(lang, "packages.html"))
    assert cell, f"{lang}: the figures row no longer quotes a kit count"

    kits = len(set(_KIT_LINK_RE.findall(_page(lang, "figures.html"))))
    assert kits, f"{lang}/figures.html links no kit at all"
    assert int(cell.group(1)) == kits, (
        f"{lang}/packages.html says {cell.group(1)} kits; "
        f"{lang}/figures.html links {kits}"
    )

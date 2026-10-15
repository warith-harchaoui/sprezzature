"""
Every number this repository quotes at a reader about the figure catalogue.

This repository holds the *prose* of the figures skill; the generators live in
``sprezzature-figures``. Nothing joined the two, so the catalogue grew from 127
kinds to 167 while the prose here stood still -- and not even still in one
place. One release pass found **four different stale numbers**: the two READMEs
said 128, ``docs/FIGURES.md`` said 126, the SKILL and its references said 127,
and the gallery page said 125 in its meta description and 127 four lines later,
in the same file.

That spread is the tell. A single stale number is a fact that aged; four
disagreeing numbers mean nobody could check any of them, because there was
nothing to check them against.

Two different quantities are quoted, and conflating them is the easy mistake:

- the **catalogue** -- how many kinds ``make-figure`` can draw (167). This is a
  statement about the package, and it is read off the package.
- the **gallery** -- how many figures are rendered onto ``web/figures.html``
  (160). This is a statement about the page, and it is counted from the page.

They differ on purpose and are not drifting: the five glyph maps are shown on
``web/maps.html`` and the two animated Gapminder generators on the Hans ROSLING
tribute, so 160 + 5 + 2 is the whole catalogue. A test that demanded they match
would be demanding the site be laid out differently.

On the sibling
--------------
The catalogue size is read from the ``sprezzature-figures`` checkout, which CI
clones next to this one for ``tests/test_release_packaging.py`` already. When it
is absent the catalogue half skips and the internal-consistency half still runs,
because that half needs nothing.

A release in the sibling will therefore turn this red here until the prose is
bumped. That is the alarm doing its job rather than a flaky test: the skill
shipped from this repository would otherwise describe a catalogue that no longer
exists. ``python scripts/bump_catalogue_count.py`` rewrites every claim below.

Author
------
Project maintainers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLING_CATALOG = (
    REPO_ROOT.parent / "sprezzature-figures" / "sprezzature_figures" / "catalog" / "figures.json"
)

#: Files whose prose quotes the size of the ``make-figure`` catalogue.
CATALOGUE_CLAIM_FILES = (
    "README.md",
    "LISEZMOI.md",
    "PHILOSOPHY.md",
    "PHILOSOPHIE.md",
    "docs/FIGURES.md",
    "sprezzature-figures/SKILL.md",
    "sprezzature-figures/FIGURES.md",
    "sprezzature-figures/references/publication-presets.md",
    "sprezzature-figures/references/ralph-eyeball-loop.md",
    "sprezzature-figures/references/dataviz-decision-tree.md",
    "sprezzature-figures/references/figure-catalog.md",
    "scripts/build_films_page.py",
    # Generated from build_films_page.py above, and committed. Both are
    # listed: the generator so a regeneration is right, the pages so a
    # stale commit is caught even if nobody reruns the generator.
    "web/films.html",
    "web/fr/films.html",
)

#: The gallery pages, which quote how many figures they themselves render.
GALLERY_PAGES = ("web/figures.html", "web/fr/figures.html")

#: A digit run only counts as a claim when a catalogue word sits next to it --
#: the same shape ``sprezzature-figures``' own ``bump_catalogue_count.py``
#: looks for. Bare numbers are line numbers, ports, pixel sizes and CSS.
_WORDS = (
    r"chart|charts|figure|figures|kind|kinds|generator|generators|entry|entries|"
    r"catalogue|catalog|type|types|graphique|graphiques|générateur|générateurs|"
    r"hand-authored|registered"
)
CLAIM_RE = re.compile(rf"\b(\d{{2,4}})\b(?=[-\s]+(?:`[^`]*`\s+)?(?:{_WORDS})\b)", re.IGNORECASE)


def _catalogue_size() -> int:
    """How many kinds ``make-figure`` actually registers, read off the package."""
    if not SIBLING_CATALOG.is_file():
        pytest.skip("sprezzature-figures checkout absent; nothing to check the prose against")
    entries = json.loads(SIBLING_CATALOG.read_text(encoding="utf-8"))
    return len(entries)


def _gallery_size() -> int:
    """How many figures ``web/figures.html`` actually renders, counted from it."""
    page = (REPO_ROOT / "web" / "figures.html").read_text(encoding="utf-8")
    return len(re.findall(r'data-src="', page))


def _claims(path: str) -> list[tuple[int, int, str]]:
    """Every quoted count in a file, as ``(line number, number, the line)``."""
    found = []
    for lineno, line in enumerate((REPO_ROOT / path).read_text(encoding="utf-8").splitlines(), 1):
        if "127.0.0.1" in line:  # an address, not a catalogue
            continue
        for match in CLAIM_RE.finditer(line):
            found.append((lineno, int(match.group(1)), line.strip()[:120]))
    return found


# ── the catalogue ───────────────────────────────────────────────────────


@pytest.mark.parametrize("path", CATALOGUE_CLAIM_FILES)
def test_the_prose_quotes_the_catalogue_that_exists(path: str) -> None:
    """Each file above states the catalogue size; it has to be the real one."""
    size = _catalogue_size()
    wrong = [(n, num, line) for n, num, line in _claims(path) if num != size]
    assert not wrong, (
        f"{path} quotes a catalogue size that is not {size}:\n  "
        + "\n  ".join(f"line {n}: {num} -- {line}" for n, num, line in wrong)
        + "\n\nRun `python scripts/bump_catalogue_count.py` to rewrite all of them."
    )


def test_at_least_one_file_quotes_it() -> None:
    """A regex that silently matches nothing would pass every test above."""
    total = sum(len(_claims(p)) for p in CATALOGUE_CLAIM_FILES)
    assert total >= 10, (
        f"only {total} catalogue claims found across {len(CATALOGUE_CLAIM_FILES)} files. "
        "Either the prose stopped quoting a number or CLAIM_RE stopped matching it -- "
        "and a guard that matches nothing is not a guard."
    )


# ── the gallery ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("path", GALLERY_PAGES)
def test_the_gallery_page_counts_what_it_shows(path: str) -> None:
    """
    The search box offers to filter N figures; N has to be how many are there.

    Both languages render the same gallery from the same sources, so the French
    page is checked against the English page's count rather than its own -- if
    they ever diverge, that is itself the bug.
    """
    shown = _gallery_size()
    page = (REPO_ROOT / path).read_text(encoding="utf-8")
    quoted = {int(m) for m in re.findall(r"(?:Search|)\s*(\d{2,4})\s+(?:figures|types de graphiques)", page)}
    assert quoted, f"{path} no longer states how many figures it shows"
    assert quoted == {shown}, (
        f"{path} says it shows {sorted(quoted)} figures; it renders {shown}."
    )


def test_both_gallery_pages_render_the_same_figures() -> None:
    """A figure added to one language and not the other is a half-shipped figure."""
    def kinds(path: str) -> set[str]:
        page = (REPO_ROOT / path).read_text(encoding="utf-8")
        return {m.rsplit("/", 1)[-1] for m in re.findall(r'data-src="([^"]+)\.svg"', page)}

    en, fr = kinds("web/figures.html"), kinds("web/fr/figures.html")
    assert en == fr, (
        f"only in English: {sorted(en - fr)}\nonly in French: {sorted(fr - en)}"
    )


def test_the_gallery_and_the_catalogue_account_for_each_other() -> None:
    """
    Every catalogue kind is on the site somewhere, and the site invents none.

    The gallery is deliberately short of the catalogue -- the glyph maps live on
    the maps page, the Gapminder pair on the Hans ROSLING tribute -- so this
    checks the remainder is exactly those seven and not a figure quietly dropped.
    """
    size = _catalogue_size()
    entries = json.loads(SIBLING_CATALOG.read_text(encoding="utf-8"))
    catalogue = {e["kind"].replace("-", "_") for e in entries}
    page = (REPO_ROOT / "web" / "figures.html").read_text(encoding="utf-8")
    gallery = {
        m.rsplit("/", 1)[-1].replace("-", "_")
        for m in re.findall(r'data-src="([^"]+)\.svg"', page)
    }

    invented = gallery - catalogue
    assert not invented, f"the gallery shows figures no generator draws: {sorted(invented)}"

    elsewhere = {"gapminder", "gapminder_variants",
                 "map_bars", "map_bubble", "map_flow", "map_pie", "map_tilegrid"}
    missing = catalogue - gallery - elsewhere
    assert not missing, (
        f"{len(missing)} catalogue kinds appear nowhere on the site: {sorted(missing)}. "
        "Add them to the gallery, or to the set of kinds shown on another page."
    )
    assert len(gallery) + len(elsewhere) == size, (
        f"{len(gallery)} in the gallery + {len(elsewhere)} shown elsewhere "
        f"!= {size} in the catalogue"
    )


def test_the_gallery_page_also_states_the_catalogue_correctly() -> None:
    """
    The gallery page quotes *both* numbers, which is why it is checked apart.

    It says how many figures it renders (the gallery) and, in the sentence that
    sends the reader to the maps page and the Hans ROSLING tribute for the rest,
    how many kinds exist (the catalogue). A sweep over this file would read the
    first as the second. The claims are picked out by the word beside them.
    """
    size = _catalogue_size()
    for path, pattern in (
        ("web/figures.html", r"whole (\d{2,4})-kind catalogue"),
        ("web/fr/figures.html", r"catalogue de (\d{2,4}) types"),
    ):
        page = (REPO_ROOT / path).read_text(encoding="utf-8")
        quoted = {int(m) for m in re.findall(pattern, page)}
        assert quoted, f"{path} no longer states the catalogue size"
        assert quoted == {size}, f"{path} says the catalogue is {sorted(quoted)}; it is {size}"

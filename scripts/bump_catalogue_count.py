#!/usr/bin/env python3
"""
bump_catalogue_count — rewrite every quoted figure count to the real one.

This repository ships the *prose* of the figures skill while the generators
live in ``sprezzature-figures``. "167 chart types" is written out at a reader
in about twenty places -- both READMEs, both philosophy pages, the SKILL and
its four reference files, the films generator and the pages it writes, and the
gallery in two languages. Editing twenty sentences by hand is the kind of chore
that gets done four times and forgotten the fifth, which is exactly what
happened: one release pass found four different stale numbers in one tree
(128, 127, 126 and 125) against a catalogue that had reached 167.

Two different quantities are rewritten, from two different sources of truth:

- the **catalogue** -- read from the ``sprezzature-figures`` checkout's
  ``catalog/figures.json``. How many kinds ``make-figure`` can draw.
- the **gallery** -- counted from ``web/figures.html`` itself. How many figures
  that page renders. It is legitimately smaller: the glyph maps are shown on
  the maps page and the Gapminder pair on the Hans ROSLING tribute.

Conflating the two is the easy mistake, so the gallery pages -- the only files
that quote both -- are rewritten by named sentence rather than by sweep.

The dangerous part of a sweep is that a three-digit number is also an IP
address, a port, a line number and a pixel size. Only a digit run that a
catalogue word sits next to is rewritten, and any line holding ``127.0.0.1``
is skipped outright. ``tests/test_the_suite_quotes_the_real_catalogue_size.py``
checks the same claims this script writes.

Usage
-----
::

    python scripts/bump_catalogue_count.py            # rewrite
    python scripts/bump_catalogue_count.py --check    # report, write nothing

Exits non-zero under ``--check`` when anything is stale, so it can gate a
release the way the test gates a push.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLING_CATALOG = (
    REPO_ROOT.parent / "sprezzature-figures" / "sprezzature_figures" / "catalog" / "figures.json"
)

#: Files that quote the catalogue size and nothing else countable.
CATALOGUE_FILES = (
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
    "web/films.html",
    "web/fr/films.html",
)

#: Sentences on the gallery pages, each tagged with which count it states.
#: ``{n}`` is where the number goes. Rewritten by name because these two files
#: are the only ones that quote the gallery size *and* the catalogue size.
GALLERY_SENTENCES = (
    ("web/figures.html", "gallery", r"(\d{{2,4}}) hand-authored SVG chart types"),
    ("web/figures.html", "gallery", r"Search (\d{{2,4}}) figures by name"),
    ("web/figures.html", "catalogue", r"whole (\d{{2,4}})-kind catalogue"),
    ("web/fr/figures.html", "gallery", r"(\d{{2,4}}) types de graphiques en SVG"),
    ("web/fr/figures.html", "gallery", r"(\d{{2,4}}) figures par nom"),
    ("web/fr/figures.html", "catalogue", r"catalogue de (\d{{2,4}}) types"),
)

_WORDS = (
    r"chart|charts|figure|figures|kind|kinds|generator|generators|entry|entries|"
    r"catalogue|catalog|type|types|graphique|graphiques|générateur|générateurs|"
    r"hand-authored|registered"
)
CLAIM_RE = re.compile(rf"\b(\d{{2,4}})\b(?=[-\s]+(?:`[^`]*`\s+)?(?:{_WORDS})\b)", re.IGNORECASE)


def catalogue_size() -> int:
    """How many kinds the sibling package registers."""
    if not SIBLING_CATALOG.is_file():
        sys.exit(
            f"error: no sprezzature-figures checkout at {SIBLING_CATALOG.parents[2]}.\n"
            "The catalogue size is read from the package, not guessed; clone the "
            "sibling repository next to this one and run again."
        )
    return len(json.loads(SIBLING_CATALOG.read_text(encoding="utf-8")))


def gallery_size() -> int:
    """How many figures the gallery page renders, counted from the page."""
    page = (REPO_ROOT / "web" / "figures.html").read_text(encoding="utf-8")
    return len(re.findall(r'data-src="', page))


def _rewrite_sweep(path: Path, size: int, write: bool) -> list[str]:
    """Rewrite catalogue-word-adjacent counts in one file. Returns the changes."""
    text = path.read_text(encoding="utf-8")
    moved: list[str] = []
    out: list[str] = []
    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        if "127.0.0.1" in line:
            out.append(line)
            continue

        def swap(match: re.Match[str]) -> str:
            found = int(match.group(1))
            if found == size:
                return match.group(0)
            moved.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {found} -> {size}")
            return str(size)

        out.append(CLAIM_RE.sub(swap, line))
    if moved and write:
        path.write_text("".join(out), encoding="utf-8")
    return moved


def _rewrite_sentences(catalogue: int, gallery: int, write: bool) -> list[str]:
    """Rewrite the named gallery sentences, each against its own source."""
    moved: list[str] = []
    for rel, which, template in GALLERY_SENTENCES:
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8")
        want = catalogue if which == "catalogue" else gallery
        pattern = re.compile(template.format())
        found = pattern.findall(text)
        if not found:
            moved.append(f"{rel}: WARNING -- sentence not found: {template}")
            continue
        for value in set(found):
            if int(value) != want:
                moved.append(f"{rel}: {which} {value} -> {want}")
        new = pattern.sub(lambda m: m.group(0).replace(m.group(1), str(want), 1), text)
        if new != text and write:
            path.write_text(new, encoding="utf-8")
    return moved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--check", action="store_true", help="report what is stale and write nothing"
    )
    args = parser.parse_args()
    write = not args.check

    catalogue, gallery = catalogue_size(), gallery_size()
    moved: list[str] = []
    for rel in CATALOGUE_FILES:
        moved += _rewrite_sweep(REPO_ROOT / rel, catalogue, write)
    moved += _rewrite_sentences(catalogue, gallery, write)

    verb = "stale" if args.check else "moved"
    print(f"catalogue is {catalogue} kinds, gallery shows {gallery}; {len(moved)} claim(s) {verb}")
    for line in moved:
        print(f"  {line}")

    if args.check and moved:
        print(
            "\nRun `python scripts/bump_catalogue_count.py` to rewrite them.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

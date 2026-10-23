"""
No raster placed in an ``<img>`` is far larger than the box it is drawn in.

Three were, and each was the same mistake: the full-resolution export sitting
where the thumbnail belonged.

* ``case-studies.html`` linked to ``maps.html`` behind a 16:9 card, and the
  card's image was ``img/figures/situation-ukraine.png`` -- 4761 x 2559, 3.9 MB
  -- while ``img/maps/situation-ukraine.png``, 1300 x 749 and 128 KB, was
  already on the site and already the one ``maps.html`` uses. Two pages, two
  languages, 7.7 MB for two thumbnails.
* ``hans.png`` is 1952 x 1952 and 2.9 MB, a photograph stored as PNG. It is the
  right file for ``og:image``, which declares exactly those dimensions, and it
  was also the ``<img>`` in a card drawn at ``h-64``: 256 pixels tall.
* ``img/figures/situation-syria.png`` and ``situation-libya.png``, 1.7 MB
  between them, were referenced by nothing at all -- full-resolution siblings
  of the thumbnails under ``img/maps/`` that the pages actually use.

The rule is about ``<img>`` only. An ``og:image`` is read by a crawler once and
wants to be large; a ``<link rel=icon>`` is a different size question; an SVG
is vector and its weight is paths rather than pixels. What this catches is the
one case where a reader pays: a raster the browser downloads in full to draw
small.

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

#: Kilobytes. Comfortably above the heaviest legitimate thumbnail on the site
#: (``img/figures/sfdp-largegraph.png``, 309 KB, a force-directed graph of
#: several thousand nodes) and far below the exports that were being served by
#: mistake. A ceiling, not a target: most of these sit under 100 KB.
CEILING_KB: float = 400.0

#: Raster formats. The browser decodes every pixel of these; an SVG's weight is
#: its path data, which is a different conversation and not this one.
RASTER = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}

_PAGES = sorted(
    [p for p in WEB.glob("*.html") if p.name != "head.html"]
    + list((WEB / "fr").glob("*.html"))
)

_IMG_SRC = re.compile(r'<img\b[^>]*?\bsrc="([^"]+)"', re.S)


def _rasters_on(page: Path) -> list[tuple[Path, float]]:
    """Every local raster the page draws, with its weight in kilobytes."""
    found: list[tuple[Path, float]] = []
    for src in _IMG_SRC.findall(page.read_text(encoding="utf-8", errors="replace")):
        if src.startswith(("http://", "https://", "data:", "//")):
            continue
        target = (page.parent / src).resolve()
        if target.is_file() and target.suffix.lower() in RASTER:
            found.append((target, target.stat().st_size / 1024))
    return found


@pytest.mark.parametrize("page", _PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_a_page_draws_no_oversized_raster(page: Path) -> None:
    """A thumbnail weighs like a thumbnail."""
    heavy = [
        (target.relative_to(WEB), f"{kb:.0f} KB")
        for target, kb in _rasters_on(page)
        if kb > CEILING_KB
    ]
    assert not heavy, (
        f"{page.relative_to(WEB)} draws {heavy}, over the {CEILING_KB:.0f} KB "
        f"ceiling. A reader downloads all of it to see it small. Make a sized "
        f"copy for the <img> and keep the original for og:image."
    )


def test_the_pages_draw_rasters_at_all() -> None:
    """A regex that stopped matching would make every page above pass."""
    drawn = {target for page in _PAGES for target, _ in _rasters_on(page)}
    assert len(drawn) >= 20, (
        f"read {len(drawn)} local raster <img> sources across {len(_PAGES)} "
        f"pages; the gallery pages alone draw more than that"
    )

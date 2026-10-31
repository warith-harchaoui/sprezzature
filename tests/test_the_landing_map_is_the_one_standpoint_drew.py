"""The positioning map on the landing page is the one the table actually draws.

The defect this guards. ``web/index.html`` showed the competitive-positioning
map as ``img/figures/landscape-positioning.png``, and ``web/fr/index.html``
showed ``landscape-positioning-fr.png``. Neither file was produced by
anything: they were hand-made copies of a ``standpoint`` run, and the run had
moved on without them. The English copy was dated 6 August; ``Claude
Dashboards`` and ``Claude Motion`` had since entered ``assets/landscape.csv``
and neither appeared anywhere in the picture a visitor was looking at.

The alt text had drifted further than the picture, and in the harder-to-see
direction. It named the two axes -- the one thing a reader who cannot see the
scatter has to take on trust -- and on the French page all four pole words
were from an older run: it said the horizontal axis ran *Solidite-Dynamisme*
and the vertical *Vivacite-Ingeniosite*, where ``assets/paysage.yaml``
declares *Stabilite -> Simplicite* across and *Dynamisme -> Flexibilite* up.
``Dynamisme`` is a real pole of this map, named on the wrong axis, which is
worse than a word that is simply absent: it reads as correct.

Nothing could notice. Both images rendered, both pages validated, and an alt
text is exactly the kind of sentence no one re-reads because it is not on
screen.

So the copies are no longer maintained, they are *taken*: identical to the
white-background export ``standpoint`` writes beside the table. This asserts
that identity, and asserts that each page's alt text still describes the map
on the page -- stated against ``assets/*.yaml``, which is the same file the
renderer reads, so a re-run that renames a pole fails here rather than
silently making a sentence false.

A note on what is *not* asserted. The documents warn that ``standpoint``
names the axes it draws but reports the variance of the principal components,
and that the drawn frame is a rotation -- 86.666 degrees here. So no share of
variance is attributable to the horizontal or the vertical, and nothing in
this file reads one. Pole *names* and point *coordinates* are both given in
the oriented frame and are safe to read; percentages are not.

Both languages, because the French page is a translation and inherited the
same two copies.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from math import hypot
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "assets"
WEB = REPO_ROOT / "web"

#: One edition of the map: the page that shows it, the ``standpoint`` stem
#: whose run produced it, and the gallery basename the page points at.
#:
#: The stem is the join. ``standpoint <stem>.csv --outdir assets --stem <stem>``
#: writes ``<stem>.yaml`` (poles and coordinates) next to ``<stem>.white.svg``
#: and ``<stem>.white.png`` (the exports), so every fact this file checks and
#: every byte it compares come out of the same single run.
_EDITIONS = (
    ("web/index.html", "landscape", "landscape-positioning"),
    ("web/fr/index.html", "paysage", "landscape-positioning-fr"),
)

#: The two exports the gallery carries. The page serves the raster; the vector
#: sits beside it as the deliverable, and a stale vector is a stale deliverable
#: even while the visible picture is right, so both are compared.
_EXPORTS = ("svg", "png")


def _run(stem: str) -> dict[str, Any]:
    """Load the YAML ``standpoint`` wrote for one edition."""
    return yaml.safe_load((ASSETS / f"{stem}.yaml").read_text(encoding="utf-8"))


def _alt_text(page: str, basename: str) -> str:
    """The alt text of the positioning map as that page declares it.

    Matched on the basename rather than on the full ``src``: the French page
    reaches the same gallery through ``../img/figures/``, and a guard that
    hard-codes one page's prefix is a guard the other page does not have.
    """
    html = (REPO_ROOT / page).read_text(encoding="utf-8")
    match = re.search(
        rf'<img[^>]*\b{re.escape(basename)}\.[a-z]+"[^>]*?\balt="([^"]*)"',
        html,
        re.S,
    )
    assert match, f"{page} has no <img> for {basename} carrying an alt attribute"
    return match.group(1)


def _poles(run: dict[str, Any]) -> list[str]:
    """The four pole names of the drawn frame, left, right, bottom, top."""
    axes = run["axes"]
    return [
        axes["axis_1"]["pole_left"],
        axes["axis_1"]["pole_right"],
        axes["axis_2"]["pole_bottom"],
        axes["axis_2"]["pole_top"],
    ]


def _short(name: str) -> str:
    """A tool's name without its parenthetical gloss.

    The reference is called ``sprezzature (the skills)`` in one edition and
    ``sprezzature (les *skills*)`` in the other -- a dictionary key carrying a
    markdown emphasis, not a different tool. Prose names it ``sprezzature``.
    """
    return name.split(" (")[0].strip()


@pytest.mark.parametrize("page,stem,basename", _EDITIONS)
@pytest.mark.parametrize("export", _EXPORTS)
def test_the_landing_map_is_the_export_standpoint_wrote(
    page: str, stem: str, basename: str, export: str
) -> None:
    """The gallery copy is the generated export, byte for byte.

    Not "looks current", not "mentions the newest tool": identical. A
    weaker assertion is one a half-refreshed copy passes, and a half-refreshed
    copy is how this drifted for eleven weeks.
    """
    generated = ASSETS / f"{stem}.white.{export}"
    served = WEB / "img" / "figures" / f"{basename}.{export}"
    assert generated.is_file(), f"{generated.relative_to(REPO_ROOT)} is missing"
    assert served.is_file(), f"{served.relative_to(REPO_ROOT)} is missing"
    assert served.read_bytes() == generated.read_bytes(), (
        f"{served.relative_to(REPO_ROOT)} is not "
        f"{generated.relative_to(REPO_ROOT)}. The gallery copy is taken from the "
        f"standpoint run, never edited: re-run it and copy the export across."
    )


@pytest.mark.parametrize("page,stem,basename", _EDITIONS)
def test_the_alt_text_names_the_poles_the_map_declares(
    page: str, stem: str, basename: str
) -> None:
    """Every pole the drawn frame carries is named in the alt text.

    This is the whole contents of the picture for a reader who cannot see it,
    and the half that went wrong in French while the scatter itself was merely
    old.
    """
    alt = _alt_text(page, basename)
    missing = [pole for pole in _poles(_run(stem)) if pole not in alt]
    assert not missing, (
        f"{page}: the alt text of {basename} does not name "
        f"{', '.join(missing)} -- pole(s) that assets/{stem}.yaml declares for "
        f"the axes this map draws."
    )


@pytest.mark.parametrize("page,stem,basename", _EDITIONS)
def test_the_alt_text_names_no_pole_from_an_earlier_run(
    page: str, stem: str, basename: str
) -> None:
    """The alt text names the poles of *this* run and of no other.

    The French page named ``Dynamisme`` on the horizontal axis, where this run
    puts it at the bottom of the vertical. Naming the four current poles is not
    enough to catch that: the sentence had a true word in a false place. So the
    pole words are read back with the side they are claimed on.
    """
    alt = _alt_text(page, basename)
    axes = _run(stem)["axes"]
    belongs_to = {
        axes["axis_1"]["pole_left"]: "horizontal",
        axes["axis_1"]["pole_right"]: "horizontal",
        axes["axis_2"]["pole_bottom"]: "vertical",
        axes["axis_2"]["pole_top"]: "vertical",
    }

    # Which axis a pole is claimed on is the axis word most recently introduced
    # before it. Both editions say "horizontal" and "vertical", so this reads
    # the same in either language. A window-free match would not work: the two
    # axis words and all four poles live in one sentence, and "the word appears
    # somewhere after 'horizontal'" is true of every pole on the page.
    axis_at = [
        (match.start(), match.group(0))
        for match in re.finditer(r"horizontal|vertical", alt)
    ]
    assert axis_at, f"{page}: the alt text of {basename} introduces neither axis"

    strays: list[tuple[str, str, str]] = []
    for pole, own_axis in belongs_to.items():
        for match in re.finditer(rf"\b{re.escape(pole)}\b", alt):
            preceding = [axis for at, axis in axis_at if at < match.start()]
            if preceding and preceding[-1] != own_axis:
                strays.append((pole, preceding[-1], own_axis))

    assert not strays, (
        f"{page}: the alt text of {basename} claims "
        + ", ".join(f"{pole} on the {claimed} axis" for pole, claimed, _ in strays)
        + " -- assets/"
        + stem
        + ".yaml puts "
        + ", ".join(f"{pole} on the {actual}" for pole, _, actual in strays)
        + "."
    )


@pytest.mark.parametrize("page,stem,basename", _EDITIONS)
def test_the_alt_text_names_the_reference_and_its_opposite(
    page: str, stem: str, basename: str
) -> None:
    """The two anchors a reader needs are named, and are still those two tools.

    A scatter of thirty-one points is not describable point by point. What
    makes it readable is the reference and the tool furthest from it, and both
    are properties of the table: add a tool at a new extreme and the sentence
    stops being true without a word of it changing.
    """
    run = _run(stem)
    alt = _alt_text(page, basename)

    reference_name = run["meta"]["reference"]
    points = {
        approach["name"]: (
            float(approach["coordinates"]["axis_1"]),
            float(approach["coordinates"]["axis_2"]),
        )
        for approach in run["approaches"]
    }
    assert reference_name in points, (
        f"assets/{stem}.yaml names {reference_name!r} as the reference but "
        f"draws no point for it"
    )
    reference = points[reference_name]
    furthest = max(
        (name for name in points if name != reference_name),
        key=lambda name: hypot(
            points[name][0] - reference[0], points[name][1] - reference[1]
        ),
    )

    for role, name in (("reference", reference_name), ("furthest point", furthest)):
        assert _short(name) in alt, (
            f"{page}: the alt text of {basename} does not name {_short(name)!r}, "
            f"which is the {role} of this run."
        )

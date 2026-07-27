#!/usr/bin/env python3
"""
make_venn — a house-styled three-set Venn diagram as a hand-authored SVG.

A Venn diagram shows how many members fall into each combination of a
few overlapping sets. With three circles there are seven regions —
three "only" lobes, three pairwise crescents, and one center where all
three sets meet — and the whole point is to read a **count** off each
region. This figure labels every one of the seven regions with its
count so the diagram works as a table you can see.

This module builds the SVG string by hand (no matplotlib / seaborn /
plotly, and no Vega here because Vega-Lite has no set-overlap mark — a
Venn is placed geometry, clearest authored directly). It follows the
front-* house style pulled from :mod:`_style`: the Apple-ish saturated
palette, Roboto typography, ink ``#1D1D1F`` on a white background,
rounded set labels, a takeaway title, and a one-line subtitle.

The figure is interactive without any JavaScript: hovering or
keyboard-focusing a set's label (or its outline) brings that whole
circle forward and dims the other two, so a single set's footprint —
and every region it touches — stands out. Each set carries a native
``<title>`` tooltip with its grand total. Motion is guarded by
``prefers-reduced-motion``.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/venn.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# Geometry + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Deliberately poster-scale so the
#: seven region counts read comfortably at gallery thumbnail size.
_WIDTH: int = 1080
_HEIGHT: int = 940

#: Circle radius and the three circle centers. The three centers sit on
#: an equilateral triangle so the seven regions come out symmetric and
#: the pairwise crescents are the same size — the classic Venn layout.
#: The radius-to-offset ratio is a touch looser than a tight Venn so the
#: single-set lobes and the pairwise crescents both stay roomy enough to
#: hold a two- or three-digit count without crowding a stroke.
_R: float = 205.0
_CX: float = 540.0    # horizontal center of the whole trio
_CY: float = 520.0    # vertical center of the whole trio
_OFF: float = 120.0   # how far each center is pushed off the trio center

#: House-style inks.
_INK: str = "#1D1D1F"       # primary text
_SUBTLE: str = "#6E6E73"    # secondary text
_BG: str = "#FFFFFF"        # background
_FOCUS: str = "#0A4DA0"     # focus-ring blue


def _dataset(accessibility: str = "universal") -> Dict[str, object]:
    """Return the communicative fake data for the three-set Venn.

    A skills-overlap survey: of 1,000 working data professionals, who
    is fluent in **Python**, in **SQL**, and in **Cloud** platforms
    (Amazon Web Services / Google Cloud / Azure). The seven region
    counts are the disjoint tallies (people counted once, in exactly
    one region), so they sum to the number of respondents who know at
    least one of the three.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`.

    Returns
    -------
    dict
        ``sets`` maps each set letter to ``{"label", "color", "cx",
        "cy"}``; ``regions`` maps each of the seven region keys
        (``"A"``, ``"B"``, ``"C"``, ``"AB"``, ``"AC"``, ``"BC"``,
        ``"ABC"``) to its integer count.
    """
    palette = load_palette(accessibility)

    # Equilateral placement: A top, B lower-left, C lower-right. Blue /
    # Green / Orange are pairwise distinct under the common color-vision
    # deficiencies and avoid the red+green trap the auditor flags.
    sets = {
        "A": {"label": "Python", "color": palette["Blue"], "cx": _CX, "cy": _CY - _OFF},
        "B": {"label": "SQL", "color": palette["Green"], "cx": _CX - _OFF * 0.92, "cy": _CY + _OFF * 0.62},
        "C": {"label": "Cloud", "color": palette["Orange"], "cx": _CX + _OFF * 0.92, "cy": _CY + _OFF * 0.62},
    }

    # Disjoint region counts (each respondent counted exactly once).
    regions = {
        "A": 96,     # Python only
        "B": 74,     # SQL only
        "C": 58,     # Cloud only
        "AB": 188,   # Python + SQL
        "AC": 121,   # Python + Cloud
        "BC": 63,    # SQL + Cloud
        "ABC": 214,  # all three
    }
    return {"sets": sets, "regions": regions}


def _set_total(regions: Dict[str, int], letter: str) -> int:
    """Sum every region that touches ``letter`` to get that set's grand total."""
    return sum(count for key, count in regions.items() if letter in key)


def _region_centroids() -> Dict[str, Tuple[float, float]]:
    """Return a hand-tuned (x, y) label anchor for each of the seven regions.

    The counts are placed by eye rather than by an exact centroid solve —
    on the symmetric equilateral layout the visual centers are stable and
    hand placement keeps every label clear of the circle strokes.

    Returns
    -------
    dict
        ``{region_key: (x, y)}`` for the seven region keys.
    """
    cx, cy = _CX, _CY
    return {
        # Three "only" lobes: pushed out toward each circle's far edge.
        "A": (cx, cy - _OFF - 108.0),
        "B": (cx - _OFF - 74.0, cy + _OFF + 52.0),
        "C": (cx + _OFF + 74.0, cy + _OFF + 52.0),
        # Three pairwise crescents: between two centers, off the middle.
        "AB": (cx - _OFF - 12.0, cy - 42.0),
        "AC": (cx + _OFF + 12.0, cy - 42.0),
        "BC": (cx, cy + _OFF + 74.0),
        # Center: all three.
        "ABC": (cx, cy + 10.0),
    }


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full three-set Venn SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"`` / ``"external"`` / ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level passed to :func:`_style.load_palette`
        (``"universal"`` default, plus ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` and ``"tritanopia"``). Wired
        through the ``--accessibility`` CLI flag by :func:`_render.render_cli`.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    data = _dataset(accessibility)
    sets: Dict[str, Dict[str, object]] = data["sets"]  # type: ignore[assignment]
    regions: Dict[str, int] = data["regions"]  # type: ignore[assignment]
    centroids = _region_centroids()

    totals = {ltr: _set_total(regions, ltr) for ltr in ("A", "B", "C")}
    grand = sum(regions.values())

    # ---- header ----
    parts: List[str] = []
    parts.append(svg_open(_WIDTH, _HEIGHT, "vn-title", "vn-desc"))
    parts.append(
        '<title id="vn-title">Overlapping skills among data '
        'professionals</title>'
    )
    desc = (
        "Three-set Venn diagram of skills held by 1,000 surveyed data "
        "professionals. "
        + "; ".join(
            f"{_xml(str(sets[l]['label']))} total {totals[l]}"
            for l in ("A", "B", "C")
        )
        + f". The central region — fluent in all three — is the largest at "
        f"{regions['ABC']}, and Python plus SQL together add another "
        f"{regions['AB']}."
    )
    parts.append(f'<desc id="vn-desc">{desc}</desc>')

    # ---- interactivity + house style (pure CSS, no JS) ----
    style_rows = [
        ".lobe { transition: opacity .18s ease; }",
        ".setlabel { transition: opacity .18s ease; }",
        # Hovering / focusing anywhere in the SVG dims every set lobe...
        "svg:hover .lobe, svg:focus-within .lobe { opacity: .30; }",
        "svg:hover .setlabel, svg:focus-within .setlabel { opacity: .35; }",
    ]
    for ltr in ("A", "B", "C"):
        # ...then the hovered/focused set restores itself to full and lifts
        # above the others so its whole footprint reads as one shape.
        style_rows.append(
            f".grp-{ltr}:hover .lobe-{ltr}, .grp-{ltr}:focus .lobe-{ltr}, "
            f".grp-{ltr}:hover .setlabel-{ltr}, .grp-{ltr}:focus .setlabel-{ltr} "
            f"{{ opacity: 1; }}"
        )
    style_rows.extend([
        ".grp { cursor: pointer; }",
        f".grp:focus {{ outline: 3px solid {_FOCUS}; outline-offset: 3px; "
        f"border-radius: 12px; }}",
        "@media (prefers-reduced-motion: reduce) { "
        ".lobe, .setlabel { transition: none; } }",
    ])
    # OS-adaptive overrides (additive; the default render is unchanged because
    # every rule below lives inside a media query). Under prefers-contrast the
    # set labels and outlines deepen to their high-contrast hues while the lobe
    # fills LIGHTEN, so the seven region counts stay readable (a straight hue
    # deepen under the multiply blend would darken the overlaps and swallow the
    # counts). Under forced colours the whole thing drops to system-palette line
    # art — legitimate here because a Venn's identity is carried by position, not
    # colour.
    label_series = {f".setlabel-{ltr}": str(sets[ltr]["color"]) for ltr in ("A", "B", "C")}
    lobe_series = {f".lobe-{ltr}": str(sets[ltr]["color"]) for ltr in ("A", "B", "C")}
    style_rows.append(
        os_adaptive_style(
            label_series,
            role="fill",
            extra_contrast=".lobe{fill-opacity:.24 !important;stroke-width:6 !important;"
            "stroke-opacity:1 !important;}",
        )
    )
    style_rows.append(
        os_adaptive_style(
            lobe_series,
            role="stroke",
            forced=True,
            forced_keyword="Canvas",
            extra_forced=".lobe[stroke]:not([stroke='transparent']):not([stroke='none'])"
            "{stroke:CanvasText;} .setlabel{fill:CanvasText;}",
        )
    )
    # Additive OS dark-mode block. The white page darkens and the two ink tiers
    # flip to light via the ink-map default; the multiply-blended lobe group is
    # flipped to `screen` so the three translucent circles *lighten* where they
    # overlap on the dark surface instead of turning to mud, keeping the seven
    # regions readable. The soft white centre-count pill (a floating light
    # element the three ink-map defaults miss) is darkened via `extra` so the
    # all-three count still reads. Set hues are data and left alone.
    style_rows.append(
        os_dark_style(
            extra='rect[rx][fill="#FFFFFF"]{fill:#1C1C1E;}',
        )
    )
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="52" y="66" font-size="31" font-weight="700" '
        f'fill="{_INK}">Most data pros speak Python, SQL and Cloud at once'
        f'</text>'
    )
    parts.append(
        f'<text x="52" y="102" font-size="19" fill="{_SUBTLE}">'
        f'Skills held by 1,000 surveyed data professionals · counts are '
        f'people per region · illustrative</text>'
    )

    # ---- the three circles ----
    # Each set is its own focusable group: a translucent fill lobe plus a
    # solid outline. Fills use "multiply" so overlaps darken naturally and
    # the seven regions are visible without hand-clipping each crescent.
    parts.append('<g style="mix-blend-mode:multiply">')
    for ltr in ("A", "B", "C"):
        s = sets[ltr]
        parts.append(
            f'<circle class="lobe lobe-{ltr}" cx="{s["cx"]}" cy="{s["cy"]}" '
            f'r="{_R}" fill="{s["color"]}" fill-opacity="0.40"/>'
        )
    parts.append('</g>')

    # Solid outlines on top (not blended) so each boundary stays crisp.
    for ltr in ("A", "B", "C"):
        s = sets[ltr]
        parts.append(
            f'<circle class="lobe lobe-{ltr}" cx="{s["cx"]}" cy="{s["cy"]}" '
            f'r="{_R}" fill="none" stroke="{s["color"]}" stroke-width="4" '
            f'stroke-opacity="0.9"/>'
        )

    # ---- region counts ----
    # One bold count per region. The center count sits on the darkest
    # triple-overlap, so it rides a soft white rounded pill (a pure fill,
    # never a dark stroke halo) that lifts it clear of the muddy blend
    # while leaving the six single-/pair-region counts on their lighter
    # tints where plain ink reads fine.
    for key, (x, y) in centroids.items():
        count = regions[key]
        if key == "ABC":
            label = str(count)
            pill_w = 30.0 + 20.0 * len(label)
            pill_h = 46.0
            parts.append(
                f'<rect x="{x - pill_w / 2:.1f}" y="{y - pill_h / 2:.1f}" '
                f'width="{pill_w:.1f}" height="{pill_h:.1f}" rx="{pill_h / 2:.1f}" '
                f'fill="#FFFFFF" fill-opacity="0.86"/>'
            )
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="28" font-weight="700" '
            f'fill="{_INK}" text-anchor="middle" dominant-baseline="middle">'
            f'{count}</text>'
        )

    # ---- focusable set groups (labels + tooltip + hover targets) ----
    # A set label sits just outside each circle's far edge. The whole group
    # is keyboard-focusable and carries the set's grand total as a tooltip.
    label_pos = {
        "A": (_CX, _CY - _OFF - _R - 44.0, "middle"),
        "B": (_CX - _OFF * 0.92 - _R + 18.0, _CY + _OFF * 0.62 + _R + 46.0, "middle"),
        "C": (_CX + _OFF * 0.92 + _R - 18.0, _CY + _OFF * 0.62 + _R + 46.0, "middle"),
    }
    for ltr in ("A", "B", "C"):
        s = sets[ltr]
        lx, ly, anchor = label_pos[ltr]
        parts.append(
            f'<g class="grp grp-{ltr}" tabindex="0" role="listitem">'
            f'<title>{_xml(str(s["label"]))}: {totals[ltr]} of {grand} '
            f'({100 * totals[ltr] / grand:.0f}%)</title>'
        )
        # Invisible hit area over the circle so hovering the lobe works too.
        parts.append(
            f'<circle class="lobe-{ltr}" cx="{s["cx"]}" cy="{s["cy"]}" '
            f'r="{_R}" fill="transparent" stroke="transparent" '
            f'stroke-width="22"/>'
        )
        parts.append(
            f'<text class="setlabel setlabel-{ltr}" x="{lx:.1f}" y="{ly:.1f}" '
            f'font-size="25" font-weight="700" fill="{s["color"]}" '
            f'text-anchor="{anchor}">{_xml(str(s["label"]))}</text>'
        )
        parts.append(
            f'<text class="setlabel setlabel-{ltr}" x="{lx:.1f}" '
            f'y="{ly + 27:.1f}" font-size="18" fill="{_SUBTLE}" '
            f'text-anchor="{anchor}">{totals[ltr]} people</text>'
        )
        parts.append('</g>')

    # ---- footer note ----
    parts.append(
        f'<text x="52" y="{_HEIGHT - 30}" font-size="17" fill="{_SUBTLE}">'
        f'Each region counts people once · hover or tab to a set to bring it '
        f'forward</text>'
    )

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the Venn SVG to the skill's ``svg-examples`` folder."""
    render_cli(__file__, "venn", build_svg, description="Render the venn SVG.")


if __name__ == "__main__":
    main()

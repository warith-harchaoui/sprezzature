#!/usr/bin/env python3
"""
make_windrose — a house-styled wind rose (polar histogram) as a hand-authored SVG.

A wind rose answers two questions at once: *from which directions does
the wind blow*, and *how strong is it when it comes from there*. Each
of the sixteen compass sectors (N, NNE, NE, …) gets one radial column
whose length is the share of hours the wind blows **from** that sector;
that column is split into stacked wedges coloured by speed band (a
polar analogue of a stacked bar chart). Reading it: the longer the
petal, the more the wind favours that bearing; the more warm colour in
the petal, the stronger those winds tend to be.

This module builds the SVG string by hand — no matplotlib / seaborn /
plotly, and no Vega, because true polar wedges (annular sectors keyed
to compass bearings) are not a native Vega-Lite mark and are far
clearer authored directly. It follows the front-* house style: a
perceptually ordered single-hue speed ramp (colour-blind- and
greyscale-safe), Roboto typography, ink ``#1D1D1F`` on a white
background, rounded stroke joins, a takeaway title, and a one-line
subtitle.

The figure is interactive without any JavaScript: hovering or
keyboard-focusing a legend entry or any wedge of a speed band dims the
other bands so a single band stands out across all directions, and
every wedge carries a native ``<title>`` tooltip with the exact
frequency. Motion is guarded by ``prefers-reduced-motion``.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/windrose.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _interactive import fullscreen_control  # noqa: E402
from _svg import point_on_circle, svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _style import os_dark_style  # noqa: E402


# ------------------------------------------------------------------
# Geometry + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Poster-scale so the polar
#: histogram reads at a glance and each wedge is comfortably large.
_WIDTH: int = 1080
_HEIGHT: int = 840

#: Polar plot centre and maximum petal radius.
_CX: float = 420.0
_CY: float = 460.0
_R_MAX: float = 310.0

#: House-style inks.
_INK: str = "#1D1D1F"      # primary text
_SUBTLE: str = "#6E6E73"   # secondary text
_GRID: str = "#E5E5EA"     # rings + spokes
_BG: str = "#FFFFFF"       # background
_FOCUS: str = "#0A4DA0"    # focus-ring blue

#: The sixteen compass points, clockwise from due North.
_DIRECTIONS: List[str] = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]

#: The cardinal labels drawn on the compass frame.
_CARDINALS: Dict[str, str] = {"N": "N", "E": "E", "S": "S", "W": "W"}


def _speed_bands() -> List[Dict[str, object]]:
    """Return the ordered wind-speed bands (calm-to-gale) with colours.

    Wind speed is an *ordered magnitude*, so the six bands ride one
    **single-hue sequential ramp** (a warm yellow-to-brown, calm → gale)
    whose lightness falls monotonically from band to band. That single
    property is what makes the rose read for everyone: because darkness
    alone tracks speed, the stack survives greyscale print and every
    colour-vision deficiency, where a cool-to-warm rainbow (teal, green,
    yellow, orange, red) would collapse — green and red land on the same
    muddy tone under deuteranopia and read as one shade in greyscale.
    Warmer-and-darker still reads intuitively as "stronger wind". Speeds
    are in knots, the convention on a marine wind rose.

    Returns
    -------
    list of dict
        One dict per band with ``label`` (str) and ``color`` (hex),
        weakest wind first (drawn nearest the centre).
    """
    # ColorBrewer YlOrBr, a perceptually ordered single-hue sequential
    # ramp: monotonic lightness (0.76 → 0.08 relative luminance) so the
    # six bands separate by darkness alone, and colour-blind-safe by
    # construction. The lightest band is deepened just enough from the
    # canonical palest yellow to hold against the white ground near the
    # centre; the darkest is a rich brown that never muddies against the
    # dark red it would clash with in a naive warm ramp.
    rows = [
        ("< 5 kt", "#FFE08A"),
        ("5–10 kt", "#FEC44F"),
        ("10–16 kt", "#FE9929"),
        ("16–22 kt", "#EC7014"),
        ("22–28 kt", "#CC4C02"),
        ("≥ 28 kt", "#8C2D04"),
    ]
    return [{"label": label, "color": color} for label, color in rows]


def _dataset() -> List[List[float]]:
    """Return the communicative fake data: percent of hours per sector × band.

    A year of hourly observations at a fictional coastal met station
    ("Cap Gris-Nez"). The prevailing wind is from the west-south-west,
    and the strongest winds arrive from that same quarter — the classic
    Atlantic-seaboard signature. Row *i* is compass sector
    ``_DIRECTIONS[i]``; the six columns are the speed bands from
    :func:`_speed_bands` (weakest first). Every number is a percentage
    of the 8 760 hours in the year, and the whole grid sums to 100.

    Returns
    -------
    list of list of float
        A 16 × 6 grid of frequencies (percent of annual hours).
    """
    # Sixteen sectors, six bands. Hand-tuned so WSW/SW dominate with a
    # heavy strong-wind tail, and the grid sums to 100 %.
    grid = [
        # <5    5-10  10-16 16-22 22-28  >=28
        [0.9, 1.1, 0.7, 0.3, 0.1, 0.0],  # N
        [0.8, 0.9, 0.5, 0.2, 0.1, 0.0],  # NNE
        [0.7, 0.8, 0.4, 0.2, 0.0, 0.0],  # NE
        [0.6, 0.7, 0.4, 0.1, 0.0, 0.0],  # ENE
        [0.7, 0.9, 0.5, 0.2, 0.1, 0.0],  # E
        [0.8, 1.0, 0.6, 0.3, 0.1, 0.0],  # ESE
        [0.9, 1.2, 0.8, 0.4, 0.2, 0.1],  # SE
        [1.0, 1.4, 1.0, 0.6, 0.3, 0.1],  # SSE
        [1.1, 1.7, 1.3, 0.8, 0.4, 0.2],  # S
        [1.3, 2.1, 1.8, 1.2, 0.7, 0.3],  # SSW
        [1.6, 2.9, 2.8, 2.1, 1.3, 0.7],  # SW
        [1.9, 3.6, 3.9, 3.2, 2.2, 1.4],  # WSW  (prevailing + strongest)
        [1.7, 3.1, 3.2, 2.4, 1.5, 0.9],  # W
        [1.3, 2.2, 1.9, 1.2, 0.6, 0.3],  # WNW
        [1.1, 1.6, 1.1, 0.6, 0.3, 0.1],  # NW
        [1.0, 1.3, 0.8, 0.4, 0.1, 0.0],  # NNW
    ]
    return grid


def _polar(cx: float, cy: float, r: float, angle_deg: float) -> Tuple[float, float]:
    """Convert a compass bearing + radius to an SVG (x, y) point.

    Parameters
    ----------
    cx, cy : float
        Polar-plot centre in user space.
    r : float
        Radius from the centre.
    angle_deg : float
        Compass bearing in degrees, 0 = North (up), increasing
        clockwise (90 = East). SVG y grows downward, so North maps to
        ``-y`` and the clockwise sweep matches a real compass.

    Returns
    -------
    tuple of float
        The ``(x, y)`` point on the SVG canvas.
    """
    # Compass 0° = up; rotate into math convention for sin/cos.
    theta = math.radians(angle_deg - 90.0)
    return point_on_circle(cx, cy, r, theta)


def _annular_sector(
    cx: float, cy: float, r0: float, r1: float, a0: float, a1: float
) -> str:
    """Build an SVG path for a filled annular sector (a stacked wedge).

    Parameters
    ----------
    cx, cy : float
        Polar-plot centre.
    r0, r1 : float
        Inner and outer radius of the wedge (``r0`` < ``r1``).
    a0, a1 : float
        Start and end compass bearing in degrees (``a0`` < ``a1``).

    Returns
    -------
    str
        The ``d`` attribute of a closed SVG ``<path>``.
    """
    x00, y00 = _polar(cx, cy, r0, a0)
    x01, y01 = _polar(cx, cy, r0, a1)
    x10, y10 = _polar(cx, cy, r1, a0)
    x11, y11 = _polar(cx, cy, r1, a1)
    # The sector spans < 180°, so large-arc-flag is 0 throughout.
    # Outer arc sweeps clockwise (sweep-flag 1), inner arc back (0).
    return (
        f"M {x10:.2f} {y10:.2f} "
        f"A {r1:.2f} {r1:.2f} 0 0 1 {x11:.2f} {y11:.2f} "
        f"L {x01:.2f} {y01:.2f} "
        f"A {r0:.2f} {r0:.2f} 0 0 0 {x00:.2f} {y00:.2f} "
        f"Z"
    )


def _slug(label: str) -> str:
    """Turn a band label into a CSS-class-safe slug."""
    out = []
    for ch in label:
        out.append(ch.lower() if ch.isascii() and ch.isalnum() else "-")
    return "".join(out).strip("-") or "b"


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full wind-rose SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Controls
        whether the emitted SVG carries its own fullscreen button; the raster
        output is unaffected. Defaults to ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level. Accepted for interface parity with the
        rest of the gallery, but a **documented no-op** here: the speed bands
        ride a single-hue *sequential* ramp (ColorBrewer YlOrBr, monotonic
        lightness) that is already colour-vision- and greyscale-safe by
        construction — speed reads from darkness alone. Passing that tuned
        ramp through :func:`_style.leveled_colors` (which re-spaces
        *categorical* hues by lightness) breaks its monotonicity — the two
        palest bands invert under ``"monochrome"`` — and de-tunes it, so the
        level is deliberately not applied. Defaults to ``"universal"``.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    # ``accessibility`` is intentionally unused: the sequential speed ramp is
    # already CVD-/greyscale-safe, so no per-level remap is applied (see the
    # docstring). Naming it keeps the render_cli signature-detection working.
    _ = accessibility
    bands = _speed_bands()
    grid = _dataset()
    n_dir = len(_DIRECTIONS)
    sector_deg = 360.0 / n_dir       # 22.5° per compass sector
    pad_deg = 3.0                    # gap between petals so they read as columns
    slugs = [_slug(str(b["label"])) for b in bands]

    # Radial scale: the longest petal (its total across bands) fills _R_MAX.
    totals = [sum(row) for row in grid]
    r_data_max = max(totals)
    # Round the axis up to a friendly tick so rings land on whole percents.
    ring_step = 4.0                                    # percent per ring
    axis_max = math.ceil(r_data_max / ring_step) * ring_step
    scale = _R_MAX / axis_max                           # px per percent

    parts: List[str] = []

    # ---- header ----
    parts.append(svg_open(_WIDTH, _HEIGHT, "wr-title", "wr-desc"))
    parts.append(
        '<title id="wr-title">Wind rose for Cap Gris-Nez: prevailing '
        'winds blow from the west-south-west</title>'
    )
    prevailing = _DIRECTIONS[totals.index(max(totals))]
    desc = (
        "Polar histogram of a year of hourly wind observations. Sixteen "
        "compass sectors each carry a petal whose length is the percent "
        "of hours the wind blew from that bearing, stacked and coloured "
        "by speed band from under 5 knots to 28 knots or more. The "
        f"longest petals point {prevailing} and west, where the strongest "
        "winds also concentrate."
    )
    parts.append(f'<desc id="wr-desc">{desc}</desc>')

    # ---- interactivity + house style (pure CSS, no JS) ----
    style_rows = [
        ".wedge { transition: opacity .18s ease; }",
        # Hover/focus anywhere dims every band; the matching rules below
        # then restore the one band being pointed at.
        "svg:hover .band, svg:focus-within .band { opacity: .18; }",
    ]
    for s in slugs:
        # Restoring the hovered/focused band across the whole figure:
        # pointing at any wedge (or its legend swatch) of band `s` lifts
        # every wedge of `s` back to full opacity.
        style_rows.append(
            f"svg:has(.band-{s}:hover) .band-{s}, "
            f"svg:has(.band-{s}:focus) .band-{s} {{ opacity: 1; }}"
        )
    style_rows.extend([
        ".legend-row { cursor: pointer; }",
        f".legend-row:focus {{ outline: 3px solid {_FOCUS}; outline-offset: 2px; }}",
        "@media (prefers-reduced-motion: reduce) { .wedge { transition: none; } }",
    ])
    # OS-adaptive style (additive; media-gated so the default light render is
    # byte-for-byte unchanged). PERCEPTUAL figure — the YlOrBr speed ramp is NOT
    # re-spaced.
    #
    # Under prefers-contrast we only STRENGTHEN STRUCTURE for a low-vision
    # reader: the secondary ink (#6E6E73 ring % labels + non-cardinal compass
    # points) deepens to the primary ink, and the #E5E5EA polar rings / spokes
    # darken and thicken so the compass frame reads harder under the petals. The
    # petal fills (the speed ramp) and their white gap-strokes are untouched.
    #
    # prefers-color-scheme:dark gives it a dark paper, inverts the ink tiers,
    # darkens the #E5E5EA rings / spokes, and darkens the white petal
    # gap-strokes so they read as gaps rather than glaring white hairlines.
    style_rows.append(
        "@media (prefers-contrast: more){"
        f' [fill="{_SUBTLE}"]{{fill:{_INK};}}'
        f' [stroke="{_GRID}"]{{stroke:#6E6E73;stroke-width:2.0;}}'
        " }"
    )
    style_rows.append(
        os_dark_style(
            screen_blend=False,
            extra='[stroke="#E5E5EA"]{stroke:#3A3A3C;} '
            '.wedge[stroke="#FFFFFF"]{stroke:#0B0B0C;}',
        )
    )
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="48" y="62" font-size="30" font-weight="700" '
        f'fill="{_INK}">The wind here comes off the Atlantic</text>'
    )
    parts.append(
        f'<text x="48" y="94" font-size="17" fill="{_SUBTLE}">'
        f'Cap Gris-Nez · frequency of wind by direction and speed · '
        f'8,760 hourly readings · illustrative</text>'
    )

    # ---- polar grid: concentric rings + radial labels ----
    n_rings = int(round(axis_max / ring_step))
    parts.append('<g>')
    for k in range(1, n_rings + 1):
        r = k * ring_step * scale
        parts.append(
            f'<circle cx="{_CX}" cy="{_CY}" r="{r:.2f}" fill="none" '
            f'stroke="{_GRID}" stroke-width="1.4"/>'
        )
        # Ring value label, dropped along the N spoke (just left of it).
        val = int(round(k * ring_step))
        ry = _CY - r
        parts.append(
            f'<text x="{_CX - 7:.1f}" y="{ry + 18:.1f}" font-size="15" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'text-anchor="end">{val}%</text>'
        )
    parts.append('</g>')

    # ---- spokes + compass labels (every sector; cardinals emphasised) ----
    parts.append('<g>')
    for i, direction in enumerate(_DIRECTIONS):
        bearing = i * sector_deg
        x_out, y_out = _polar(_CX, _CY, _R_MAX, bearing)
        parts.append(
            f'<line x1="{_CX}" y1="{_CY}" x2="{x_out:.2f}" y2="{y_out:.2f}" '
            f'stroke="{_GRID}" stroke-width="1.4"/>'
        )
    # All sixteen bearings labelled just outside the outer ring. Text is
    # side-aware: right of the compass anchors at the start, left at the
    # end, top/bottom centred — so labels sit at a constant radial gap
    # and never crowd the rim. Cardinals (N/E/S/W) are emphasised.
    cardinals = {"N", "E", "S", "W"}
    for i, direction in enumerate(_DIRECTIONS):
        bearing = i * sector_deg
        is_card = direction in cardinals
        gap = 30.0 if is_card else 24.0
        lx, ly = _polar(_CX, _CY, _R_MAX + gap, bearing)
        dx = lx - _CX
        if dx > 3.0:
            anchor = "start"
        elif dx < -3.0:
            anchor = "end"
        else:
            anchor = "middle"
        size = 21 if is_card else 14
        weight = 700 if is_card else 500
        fill = _INK if is_card else _SUBTLE
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'dominant-baseline="middle">{direction}</text>'
        )
    parts.append('</g>')

    # ---- petals: one stacked column per compass sector ----
    # Grouped by band so a single CSS rule highlights that band across
    # every direction. We emit band-by-band; each wedge sits at the right
    # cumulative radius for its sector.
    for b_idx, band in enumerate(bands):
        s = slugs[b_idx]
        color = str(band["color"])
        parts.append(f'<g class="band band-{s}">')
        for d_idx, direction in enumerate(_DIRECTIONS):
            v = grid[d_idx][b_idx]
            if v <= 0:
                continue
            # Cumulative radius: sum of the bands below this one.
            below = sum(grid[d_idx][:b_idx])
            r0 = below * scale
            r1 = (below + v) * scale
            centre = d_idx * sector_deg
            a0 = centre - (sector_deg - pad_deg) / 2.0
            a1 = centre + (sector_deg - pad_deg) / 2.0
            path = _annular_sector(_CX, _CY, r0, r1, a0, a1)
            tip = (
                f'{_xml(direction)} · {_xml(str(band["label"]))}: '
                f'{v:.1f}% of hours'
            )
            parts.append(
                f'<path class="wedge band-{s}" tabindex="0" role="listitem" '
                f'd="{path}" fill="{color}" stroke="{_BG}" '
                f'stroke-width="1.1" stroke-linejoin="round">'
                f'<title>{tip}</title></path>'
            )
        parts.append('</g>')

    # ---- legend (speed ramp, right of the compass) ----
    legend_x = 840.0
    legend_y = 330.0
    row_h = 46.0
    parts.append(
        f'<text x="{legend_x:.0f}" y="{legend_y - 32:.0f}" font-size="18" '
        f'font-weight="700" fill="{_INK}">Wind speed</text>'
    )
    parts.append(f'<g transform="translate({legend_x:.1f},{legend_y:.1f})">')
    for k, band in enumerate(bands):
        s = slugs[k]
        color = str(band["color"])
        cy = k * row_h
        # Band total across all directions, for the legend's right column.
        band_total = sum(grid[d][k] for d in range(n_dir))
        parts.append(
            f'<g class="band band-{s} legend-row" tabindex="0" role="listitem" '
            f'transform="translate(0,{cy:.1f})">'
            f'<title>{_xml(str(band["label"]))}: {band_total:.1f}% of all hours</title>'
        )
        parts.append(
            f'<rect class="band-{s}" x="0" y="0" width="26" height="26" '
            f'rx="7" fill="{color}"/>'
        )
        parts.append(
            f'<text x="38" y="14" font-size="18" font-weight="600" '
            f'fill="{_INK}" dominant-baseline="middle">'
            f'{_xml(str(band["label"]))}</text>'
        )
        parts.append(
            f'<text x="200" y="14" font-size="16" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'text-anchor="end" dominant-baseline="middle">'
            f'{band_total:.1f}%</text>'
        )
        parts.append('</g>')
    parts.append('</g>')

    # ---- footnote: how to read it ----
    parts.append(
        f'<text x="{legend_x:.0f}" y="{legend_y + len(bands) * row_h + 20:.0f}" '
        f'font-size="15" fill="{_SUBTLE}">Petal length = % of hours</text>'
    )
    parts.append(
        f'<text x="{legend_x:.0f}" y="{legend_y + len(bands) * row_h + 42:.0f}" '
        f'font-size="15" fill="{_SUBTLE}">wind blew '
        f'<tspan font-style="italic">from</tspan> that way.</text>'
    )

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the wind-rose SVG to the skill's ``svg-examples`` folder.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "windrose",
        build_svg,
        description="Write the house-style wind-rose SVG example.",
    )


if __name__ == "__main__":
    main()

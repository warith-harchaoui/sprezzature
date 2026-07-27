#!/usr/bin/env python3
"""
make_rose — a house-styled Nightingale rose (coxcomb / polar-area chart) as a hand-authored SVG.

A rose diagram — Florence Nightingale's *coxcomb*, also called a
polar-area chart — is a pie chart's honest cousin. Every wedge spans
the **same angle** (here one twelfth of the circle, one per month), so
the eye is not fooled by fat slices; the story lives entirely in each
wedge's **radius**, which grows with the value. Nightingale used it in
1858 to argue that most soldiers in the Crimean War died not on the
battlefield but from preventable disease in filthy hospitals, and the
sheer size of the disease petals won the argument that a table never
could.

This module rebuilds that argument in the front-* house style. Twelve
monthly wedges are stacked by cause of death — preventable disease,
wounds, and everything else — so each petal's total radius is the
month's death rate and its coloured bands show what the men were dying
of. The reader sees at a glance that the pale-blue disease band swamps
the red wounds band, and that the whole rose shrinks dramatically once
Nightingale's sanitary commission arrives.

The SVG is built by hand — no matplotlib / seaborn / plotly, and no
Vega, because equal-angle annular sectors keyed to a calendar are not a
native Vega-Lite mark and read far more cleanly authored directly. It
follows the tokens from :mod:`_style`: the Apple-ish palette, Roboto
typography, ink ``#1D1D1F`` on a white ground, rounded joins, a
takeaway title and a one-line subtitle.

The figure is interactive without any JavaScript: hovering or
keyboard-focusing a legend entry or any wedge of a cause dims the other
causes so that one band stands out across every month, and each wedge
carries a native ``<title>`` tooltip with the exact death rate. Motion
is guarded by ``prefers-reduced-motion``.

The data is Nightingale's own, transcribed from her 1858 diagram:
annual mortality rate per 1,000 men, by cause, April 1854 through
March 1855 (the first, deadliest year of the two she charted).

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/rose.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import forced_color_patterns, load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import point_on_circle, svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# Geometry + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Poster-scale so the coxcomb reads
#: at a glance and every monthly petal is comfortably large.
_WIDTH: int = 1180
_HEIGHT: int = 900

#: Polar plot centre and maximum petal radius. The rose sits left-of-
#: centre so the legend + reading note have room on the right.
_CX: float = 470.0
_CY: float = 500.0
_R_MAX: float = 335.0

#: House-style inks.
_INK: str = "#1D1D1F"      # primary text
_SUBTLE: str = "#6E6E73"   # secondary text
_GRID: str = "#E5E5EA"     # rings + spokes
_BG: str = "#FFFFFF"       # background
_FOCUS: str = "#0A4DA0"    # focus-ring blue

#: The twelve months of Nightingale's first Crimean year, April 1854
#: through March 1855, in the order they sweep clockwise from the top.
_MONTHS: List[str] = [
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
]

#: Month index (into ``_MONTHS``) where the sanitary commission's work
#: begins to bite — used only to place the reading annotation.
_TURN_IDX: int = 9  # January 1855


def _causes(accessibility: str = "universal") -> List[Dict[str, object]]:
    """Return the three ordered causes of death with their colours.

    The order is the stacking order, innermost first: preventable
    disease sits nearest the centre (the dominant band, drawn first so
    its huge petals read as the base of each column), then wounds, then
    all other causes. Colours are chosen for meaning, not decoration —
    a calm clinical blue for the disease that sanitation could stop, an
    alarming red for battle wounds, and a neutral grey for the rest —
    and they stay distinguishable where petals overlap.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to
        :func:`_style.load_palette` so the band hues honour the caller's
        colour-vision request. Defaults to ``"universal"``.

    Returns
    -------
    list of dict
        One dict per cause with ``key`` (str, stable slug), ``label``
        (str, human name) and ``color`` (hex), innermost band first.
    """
    palette = load_palette(accessibility)
    fallback = {"Teal": "#5AC8FA", "Red": "#FF3B30", "Gray": "#8E8E93"}

    def _hue(name: str) -> str:
        return palette.get(name) or fallback.get(name) or palette["Blue"]

    # The three bands are given three well-separated lightness levels, not
    # just three hues: a mid teal for disease, a dark red for wounds, and a
    # light grey for all other causes. The palette's mid grey read at almost
    # the same greyscale luminance as red, so the two minor bands merged for
    # colour-blind and greyscale viewers; a light grey pulls "other" clear of
    # both, so the stack's three bands stay legible without colour.
    return [
        {"key": "disease", "label": "Preventable disease", "color": _hue("Teal")},
        {"key": "wounds", "label": "Wounds in battle", "color": _hue("Red")},
        {"key": "other", "label": "All other causes", "color": "#C7C7CC"},
    ]


def _dataset() -> List[List[float]]:
    """Return Nightingale's mortality data: rate per 1,000 by month × cause.

    Transcribed from Florence Nightingale's 1858 *Diagram of the Causes
    of Mortality in the Army in the East*, first year (April 1854 to
    March 1855). Each number is the annual death rate per 1,000 men that
    would result if that month's mortality held for a full year — the
    rate Nightingale herself plotted. Row *i* is month ``_MONTHS[i]``;
    the three columns are the causes from :func:`_causes` in stacking
    order: preventable disease, wounds, other.

    The shape tells the whole story: disease climbs through the autumn
    to a monstrous peak in January 1855, then collapses through the
    spring once the sanitary commission cleans the hospitals — while
    deaths from actual wounds stay comparatively tiny throughout.

    Returns
    -------
    list of list of float
        A 12 × 3 grid of annualised death rates per 1,000 men.
    """
    # disease, wounds, other  — annual rate per 1,000, per month.
    grid = [
        [5.0, 0.0, 5.0],       # Apr 1854
        [9.5, 0.0, 6.4],       # May
        [17.5, 0.0, 8.2],      # Jun
        [23.0, 0.0, 11.0],     # Jul
        [30.0, 0.7, 12.0],     # Aug
        [30.7, 3.6, 8.5],      # Sep
        [63.0, 3.0, 6.0],      # Oct
        [95.0, 6.0, 8.0],      # Nov
        [120.0, 8.5, 8.0],     # Dec
        [144.0, 9.0, 11.0],    # Jan 1855  (the deadliest month)
        [96.0, 6.0, 9.5],      # Feb
        [54.0, 3.5, 7.0],      # Mar
    ]
    return grid


def _polar(cx: float, cy: float, r: float, angle_deg: float) -> Tuple[float, float]:
    """Convert a clock bearing + radius to an SVG (x, y) point.

    Parameters
    ----------
    cx, cy : float
        Polar-plot centre in user space.
    r : float
        Radius from the centre.
    angle_deg : float
        Bearing in degrees, 0 = top (12 o'clock), increasing clockwise
        (90 = 3 o'clock). SVG y grows downward, so the top maps to
        ``-y`` and the sweep matches a clock face — the natural reading
        order for a calendar of months.

    Returns
    -------
    tuple of float
        The ``(x, y)`` point on the SVG canvas.
    """
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
        Start and end bearing in degrees (``a0`` < ``a1``).

    Returns
    -------
    str
        The ``d`` attribute of a closed SVG ``<path>``.
    """
    x00, y00 = _polar(cx, cy, r0, a0)
    x01, y01 = _polar(cx, cy, r0, a1)
    x10, y10 = _polar(cx, cy, r1, a0)
    x11, y11 = _polar(cx, cy, r1, a1)
    # Each sector spans 30°, well under 180°, so large-arc-flag stays 0.
    # Outer arc sweeps clockwise (sweep-flag 1), inner arc back (0).
    return (
        f"M {x10:.2f} {y10:.2f} "
        f"A {r1:.2f} {r1:.2f} 0 0 1 {x11:.2f} {y11:.2f} "
        f"L {x01:.2f} {y01:.2f} "
        f"A {r0:.2f} {r0:.2f} 0 0 0 {x00:.2f} {y00:.2f} "
        f"Z"
    )


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full Nightingale-rose SVG document as a string.

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
    causes = _causes(accessibility)
    grid = _dataset()
    n_month = len(_MONTHS)
    sector_deg = 360.0 / n_month     # 30° per month
    pad_deg = 1.6                    # hairline gap so petals read as spokes

    totals = [sum(row) for row in grid]
    r_data_max = max(totals)

    # Radial scale: on a coxcomb the RADIUS carries the value (not the
    # area), so the scale is linear in the rate. Round the axis up to a
    # friendly tick and leave headroom so the tallest petal never kisses
    # the outer label ring.
    ring_step = 50.0                                    # rate per ring
    axis_max = math.ceil((r_data_max * 1.02) / ring_step) * ring_step
    scale = _R_MAX / axis_max                            # px per unit rate

    parts: List[str] = []

    # ---- header + accessibility ----
    peak_idx = totals.index(max(totals))
    parts.append(svg_open(_WIDTH, _HEIGHT, "rose-title", "rose-desc"))
    parts.append(
        '<title id="rose-title">Nightingale rose: preventable disease, not '
        'battle, killed most soldiers in the Crimean War</title>'
    )
    desc = (
        "Coxcomb (polar-area) chart of army mortality in the Crimean War, "
        "April 1854 to March 1855. Twelve equal-angle wedges, one per month, "
        "sweep clockwise from the top; each wedge's radius is that month's "
        "annual death rate per 1,000 men, stacked and coloured by cause. The "
        "pale-blue preventable-disease band dwarfs the red wounds band in "
        f"every month and balloons to its peak in {_MONTHS[peak_idx]} 1855, "
        "then shrinks through the spring after sanitary reform."
    )
    parts.append(f'<desc id="rose-desc">{desc}</desc>')

    # ---- interactivity + house style (pure CSS, no JS) ----
    keys = [str(c["key"]) for c in causes]
    style_rows = [
        ".wedge { transition: opacity .18s ease; }",
        # Hover/focus anywhere dims every cause; the per-cause rules below
        # then restore the one being pointed at, across all months.
        "svg:hover .cause, svg:focus-within .cause { opacity: .16; }",
    ]
    for k in keys:
        style_rows.append(
            f"svg:has(.cause-{k}:hover) .cause-{k}, "
            f"svg:has(.cause-{k}:focus) .cause-{k} {{ opacity: 1; }}"
        )
    style_rows.extend([
        ".legend-row { cursor: pointer; }",
        f".legend-row:focus {{ outline: 3px solid {_FOCUS}; outline-offset: 3px; }}",
        ".wedge:focus { outline: none; }",
        f".wedge:focus {{ stroke: {_FOCUS}; stroke-width: 2.4; }}",
        "@media (prefers-reduced-motion: reduce) { .wedge { transition: none; } }",
    ])
    # OS-adaptive overrides (additive; every rule lives inside an @media block,
    # so the default render is byte-for-byte unchanged). The three causes reuse
    # their existing ``.cause-<key>`` classes as hooks: under prefers-contrast
    # the band fills deepen together to their high-contrast spacing (role="fill"
    # only, so each wedge's white keyline is left alone), keeping the stacked
    # bands separable. Under forced-colors (Windows High Contrast) the ~4-colour
    # system palette cannot preserve three coloured bands, so each cause is
    # instead handed a distinct Canvas/CanvasText PATTERN (hatch / dots) via
    # forced_color_patterns: every wedge of a cause and its legend swatch take
    # that pattern, so the three bands stay separable even when colour is
    # stripped.
    cause_series = {f".cause-{c['key']}": str(c["color"]) for c in causes}
    style_rows.append(os_adaptive_style(cause_series, role="fill"))
    fcp_defs, fcp_style = forced_color_patterns(
        [f".cause-{c['key']}" for c in causes], prefix="rose-fcp"
    )
    style_rows.append(fcp_style)
    # Dark mode: invert paper + inks, dim the light polar rings / spokes
    # (#E5E5EA). Wedge white keylines are left untouched by os_dark_style.
    style_rows.append(os_dark_style(extra='[stroke="#E5E5EA"]{stroke:#2C2C2E;}'))
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")
    parts.append(f"<defs>{fcp_defs}</defs>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="56" y="66" font-size="33" font-weight="700" '
        f'fill="{_INK}">Most of the dead never saw a battlefield</text>'
    )
    parts.append(
        f'<text x="56" y="100" font-size="18" fill="{_SUBTLE}">'
        f'Florence Nightingale&#8217;s coxcomb &#183; British Army mortality '
        f'in the East &#183; annual deaths per 1,000 men, by cause &#183; '
        f'Apr 1854&#8211;Mar 1855</text>'
    )

    # ---- polar grid: concentric rings + radial tick labels ----
    n_rings = int(round(axis_max / ring_step))
    parts.append('<g>')
    for k in range(1, n_rings + 1):
        r = k * ring_step * scale
        parts.append(
            f'<circle cx="{_CX}" cy="{_CY}" r="{r:.2f}" fill="none" '
            f'stroke="{_GRID}" stroke-width="1.3"/>'
        )
        # Ring value label, dropped just above each ring on the 12-o'clock
        # spoke, in a small white pill so it never fights a petal edge.
        val = int(round(k * ring_step))
        ry = _CY - r
        label = f"{val}"
        pill_w = 8.0 + 8.4 * len(label)
        parts.append(
            f'<rect x="{_CX - pill_w / 2.0:.1f}" y="{ry - 11:.1f}" '
            f'width="{pill_w:.1f}" height="20" rx="6" fill="{_BG}" '
            f'fill-opacity="0.82"/>'
        )
        parts.append(
            f'<text x="{_CX:.1f}" y="{ry + 4:.1f}" font-size="14" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'text-anchor="middle">{label}</text>'
        )
    parts.append('</g>')

    # ---- month spokes + labels around the rim ----
    parts.append('<g>')
    for i in range(n_month):
        bearing = i * sector_deg
        x_out, y_out = _polar(_CX, _CY, _R_MAX, bearing)
        parts.append(
            f'<line x1="{_CX}" y1="{_CY}" x2="{x_out:.2f}" y2="{y_out:.2f}" '
            f'stroke="{_GRID}" stroke-width="1.1"/>'
        )
    # Month labels are centred on each wedge (bearing + half a sector) and
    # set just outside the rim; the anchor flips by side so labels keep a
    # constant radial gap and never crowd the circle.
    for i, month in enumerate(_MONTHS):
        centre = i * sector_deg + sector_deg / 2.0
        lx, ly = _polar(_CX, _CY, _R_MAX + 26.0, centre)
        dx = lx - _CX
        if dx > 3.0:
            anchor = "start"
        elif dx < -3.0:
            anchor = "end"
        else:
            anchor = "middle"
        # Flag the deadliest month so the eye lands on the story.
        is_peak = i == peak_idx
        fill = _INK if is_peak else _SUBTLE
        weight = 700 if is_peak else 500
        year = " '55" if month in ("Jan", "Feb", "Mar") else ""
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="16" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'dominant-baseline="middle">{month}{year}</text>'
        )
    parts.append('</g>')

    # ---- petals: one stacked wedge per month, grouped by cause ----
    # Emitting cause-by-cause lets one CSS rule highlight a cause across
    # every month. Each wedge sits at the cumulative radius for its month.
    for c_idx, cause in enumerate(causes):
        k = str(cause["key"])
        color = str(cause["color"])
        parts.append(f'<g class="cause cause-{k}">')
        for m_idx, month in enumerate(_MONTHS):
            v = grid[m_idx][c_idx]
            if v <= 0:
                continue
            below = sum(grid[m_idx][:c_idx])
            r0 = below * scale
            r1 = (below + v) * scale
            start = m_idx * sector_deg + pad_deg / 2.0
            end = (m_idx + 1) * sector_deg - pad_deg / 2.0
            path = _annular_sector(_CX, _CY, r0, r1, start, end)
            year = " 1855" if month in ("Jan", "Feb", "Mar") else " 1854"
            tip = (
                f'{_xml(month)}{year} &#183; {_xml(str(cause["label"]))}: '
                f'{v:.0f} per 1,000'
            )
            parts.append(
                f'<path class="wedge cause-{k}" tabindex="0" role="listitem" '
                f'd="{path}" fill="{color}" stroke="{_BG}" '
                f'stroke-width="1.1" stroke-linejoin="round">'
                f'<title>{tip}</title></path>'
            )
        parts.append('</g>')

    # ---- centre dot so the origin reads as a hub, not a gap ----
    parts.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="3.4" fill="{_INK}"/>'
    )

    # ---- reading annotation on the peak petal ----
    # A short leader from the deadliest wedge out to an ink note, so the
    # single most important number is spelled out, not left to a ring.
    peak_total = totals[peak_idx]
    peak_disease = grid[peak_idx][0]
    peak_centre = peak_idx * sector_deg + sector_deg / 2.0
    # Draw the leader from a point partway out along the peak petal to an
    # ink note anchored in the open lower-left of the canvas, well clear
    # of the rim labels. Text is left-anchored so it can never clip.
    px, py = _polar(_CX, _CY, peak_total * scale * 0.62, peak_centre)
    nx, ny = 60.0, 806.0
    parts.append(
        f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{nx + 8:.1f}" '
        f'y2="{ny - 30:.1f}" stroke="{_INK}" stroke-width="1.4" '
        f'stroke-opacity="0.5"/>'
    )
    parts.append(
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{_INK}"/>'
    )
    parts.append(
        f'<text x="{nx:.1f}" y="{ny:.1f}" font-size="18" font-weight="700" '
        f'fill="{_INK}">January 1855 was the deadliest month</text>'
    )
    parts.append(
        f'<text x="{nx:.1f}" y="{ny + 23:.1f}" font-size="15" '
        f'fill="{_SUBTLE}">{peak_disease:.0f} of every 1,000 men were lost to '
        f'disease alone, against {grid[peak_idx][1]:.0f} to wounds</text>'
    )

    # ---- legend (causes, right of the rose) ----
    legend_x = 880.0
    legend_y = 250.0
    row_h = 60.0
    parts.append(
        f'<text x="{legend_x:.0f}" y="{legend_y - 34:.0f}" font-size="18" '
        f'font-weight="700" fill="{_INK}">Cause of death</text>'
    )
    parts.append(f'<g transform="translate({legend_x:.1f},{legend_y:.1f})">')
    for c_idx, cause in enumerate(causes):
        k = str(cause["key"])
        color = str(cause["color"])
        cy = c_idx * row_h
        # Share of the whole year's deaths carried by this cause.
        cause_sum = sum(grid[m][c_idx] for m in range(n_month))
        grand = sum(sum(row) for row in grid)
        pct = 100.0 * cause_sum / grand
        parts.append(
            f'<g class="cause cause-{k} legend-row" tabindex="0" '
            f'role="listitem" transform="translate(0,{cy:.1f})">'
            f'<title>{_xml(str(cause["label"]))}: {pct:.0f}% of the '
            f"year&#8217;s deaths</title>"
        )
        parts.append(
            f'<rect class="cause-{k}" x="0" y="0" width="30" height="30" '
            f'rx="8" fill="{color}"/>'
        )
        parts.append(
            f'<text x="44" y="14" font-size="19" font-weight="600" '
            f'fill="{_INK}" dominant-baseline="middle">'
            f'{_xml(str(cause["label"]))}</text>'
        )
        parts.append(
            f'<text x="44" y="36" font-size="15" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'dominant-baseline="middle">{pct:.0f}% of all deaths</text>'
        )
        parts.append('</g>')
    parts.append('</g>')

    # ---- how-to-read note under the legend ----
    note_y = legend_y + len(causes) * row_h + 8.0
    read_lines = [
        "How to read it",
        "Every wedge is the same width, one month.",
        "The radius is that month’s death rate;",
        "colour splits it by cause. Bigger petal,",
        "deadlier month. Hover a colour to isolate it.",
    ]
    parts.append(
        f'<text x="{legend_x:.0f}" y="{note_y:.0f}" font-size="16" '
        f'font-weight="700" fill="{_INK}">{read_lines[0]}</text>'
    )
    for j, line in enumerate(read_lines[1:], start=1):
        parts.append(
            f'<text x="{legend_x:.0f}" y="{note_y + 8 + j * 22:.0f}" '
            f'font-size="15" fill="{_SUBTLE}">{line}</text>'
        )

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the Nightingale-rose SVG to the skill's ``svg-examples`` folder."""
    render_cli(__file__, "rose", build_svg, description="Render the rose SVG.")


if __name__ == "__main__":
    main()

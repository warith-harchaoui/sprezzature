#!/usr/bin/env python3
"""
make_radial-bar — a house-styled radial (circular) bar chart as a hand-authored SVG.

A radial bar chart wraps a bar chart around a clock face: each category
becomes a wedge whose *length* (outward from a central hole) encodes a
value, and whose *angular position* encodes an inherently circular axis
— here, the twenty-four hours of the day. The circular layout is not
decoration: because hour 23 sits right next to hour 0, the daily rhythm
reads as a continuous loop, and the two commute peaks land on opposite
sides of the dial the way a reader already pictures a day.

This module builds the SVG string by hand — no matplotlib / seaborn /
plotly, and no Vega, because true annular bars (rounded wedges keyed to
a clock) are not a native Vega-Lite mark and read far cleaner authored
directly. It follows the front-* house style pulled from :mod:`_style`:
the Apple-ish saturated palette (a calm blue for the quiet hours, a warm
orange flagging the two rush peaks), Roboto typography, ink ``#1D1D1F``
on a white background, rounded bar caps, a takeaway title, and a
one-line subtitle that states the point.

The figure is interactive without any JavaScript: hovering or
keyboard-focusing a bar lifts it and dims the rest so a single hour
stands out, and every bar carries a native ``<title>`` tooltip with the
exact trip count. A gentle one-shot SMIL grow-out plays on load (bars
are already visible at ``t = 0``, never animated in from nothing), and
all motion is guarded by ``prefers-reduced-motion``.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/radial-bar.svg``.

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
# without the dataviz tier); the polar helpers live in _svg.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import point_on_circle, svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# Canvas + geometry constants (poster-scale so every wedge reads).
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels.
_WIDTH: int = 1120
_HEIGHT: int = 1000

#: Dial centre and radii. Bars grow from ``_R_IN`` (the central hole,
#: which holds the readout) out to at most ``_R_OUT``.
_CX: float = 560.0
_CY: float = 548.0
_R_IN: float = 168.0
_R_OUT: float = 400.0

#: House-style inks.
_INK: str = "#1D1D1F"      # primary text
_SUBTLE: str = "#6E6E73"   # secondary text
_GRID: str = "#E8E8ED"     # concentric rings + hour spokes
_BG: str = "#FFFFFF"       # background
_FOCUS: str = "#0A4DA0"    # focus-ring blue


def _palette_hues(accessibility: str = "universal") -> Dict[str, str]:
    """Return the two working hues (calm base + peak accent) as hex.

    The base blue carries the quiet, off-peak hours; the warm orange
    flags the two commute peaks so the bimodal rhythm pops without any
    colour-on-colour clash. Both come from the canonical palette, with a
    curated fallback when a co-installed palette CSV omits a key.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`.

    Returns
    -------
    dict of str to str
        ``{"base": "#RRGGBB", "peak": "#RRGGBB"}``.
    """
    palette = load_palette(accessibility)
    fallback = {"Blue": "#007AFF", "Orange": "#FF9500"}
    base = palette.get("Blue") or fallback["Blue"]
    peak = palette.get("Orange") or fallback["Orange"]
    return {"base": base, "peak": peak}


def _dataset() -> List[int]:
    """Return the communicative fake data: bike-share trips by hour of day.

    A weekday's worth of departures from a fictional city bike-share
    ("Vélomarée", a coastal French system), averaged over one spring
    month and rounded to whole trips. Index *h* is the clock hour
    ``h:00``–``h:59``. The shape is the textbook commuter signature:
    a deep overnight trough, a sharp morning peak around 08:00, a
    modest midday lift over lunch, and a broad, taller evening peak
    around 18:00 as the city rides home.

    Returns
    -------
    list of int
        Twenty-four trip counts, one per clock hour (00:00 … 23:00).
    """
    # Hand-tuned bimodal weekday curve; a real system's canonical shape.
    return [
        120,  90,  60,  45,  55, 160,   # 00–05  overnight trough
        520, 1180, 2240, 1480,  760,  700,  # 06–11  morning peak at 08
        880,  820,  700,  760, 1340, 2060,  # 12–17  lunch lift, ramp
        2380, 1560,  940,  560,  340,  190,  # 18–23  evening peak at 18
    ]


def _polar(cx: float, cy: float, r: float, hour_angle_deg: float) -> Tuple[float, float]:
    """Convert a clock bearing + radius to an SVG ``(x, y)`` point.

    Parameters
    ----------
    cx, cy : float
        Dial centre in user space.
    r : float
        Radius from the centre.
    hour_angle_deg : float
        Clock bearing in degrees, 0 = midnight at the top, increasing
        clockwise (90 = 06:00 on the right, 180 = noon at the bottom).
        SVG y grows downward, so midnight maps to ``-y`` and the
        clockwise sweep matches a real clock face.

    Returns
    -------
    tuple of float
        The ``(x, y)`` point on the SVG canvas.
    """
    theta = math.radians(hour_angle_deg - 90.0)
    return point_on_circle(cx, cy, r, theta)


def _annular_bar(
    cx: float, cy: float, r0: float, r1: float, a0: float, a1: float
) -> str:
    """Build an SVG path for a filled annular bar (one hour's wedge).

    Parameters
    ----------
    cx, cy : float
        Dial centre.
    r0, r1 : float
        Inner and outer radius of the bar (``r0`` < ``r1``).
    a0, a1 : float
        Start and end clock bearing in degrees (``a0`` < ``a1``).

    Returns
    -------
    str
        The ``d`` attribute of a closed SVG ``<path>``.
    """
    x00, y00 = _polar(cx, cy, r0, a0)
    x01, y01 = _polar(cx, cy, r0, a1)
    x10, y10 = _polar(cx, cy, r1, a0)
    x11, y11 = _polar(cx, cy, r1, a1)
    # Each wedge spans < 180°, so the large-arc flag is 0. The outer arc
    # sweeps clockwise (sweep-flag 1); the inner arc returns (flag 0).
    return (
        f"M {x10:.2f} {y10:.2f} "
        f"A {r1:.2f} {r1:.2f} 0 0 1 {x11:.2f} {y11:.2f} "
        f"L {x01:.2f} {y01:.2f} "
        f"A {r0:.2f} {r0:.2f} 0 0 0 {x00:.2f} {y00:.2f} "
        f"Z"
    )


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def _fmt_trips(n: int) -> str:
    """Format a trip count with a thin-space thousands separator."""
    return f"{n:,}".replace(",", " ")


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full radial-bar SVG document as a string.

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
    hues = _palette_hues(accessibility)
    data = _dataset()
    n = len(data)                       # 24 hours
    sector_deg = 360.0 / n              # 15° per hour
    pad_deg = 3.2                       # angular gap so bars read as columns
    total = sum(data)

    # Radial scale: the busiest hour reaches _R_OUT; a friendly round tick
    # keeps the gridlines on whole thousands.
    data_max = max(data)
    ring_step = 500                     # trips per ring
    axis_max = math.ceil(data_max / ring_step) * ring_step
    scale = (_R_OUT - _R_IN) / axis_max  # px per trip

    # Threshold above which an hour counts as a "rush" peak (warm accent).
    peak_cut = 1600
    peak_hours = [h for h, v in enumerate(data) if v >= peak_cut]
    morning = max((h for h in peak_hours if h < 12), key=lambda h: data[h])
    evening = max((h for h in peak_hours if h >= 12), key=lambda h: data[h])

    parts: List[str] = []

    # ---- header ----
    parts.append(svg_open(_WIDTH, _HEIGHT, "rb-title", "rb-desc"))
    parts.append(
        '<title id="rb-title">Bike-share trips by hour of day: two commute '
        'peaks around 8am and 6pm</title>'
    )
    desc = (
        "Radial bar chart of an average weekday's bike-share departures, "
        "one bar per clock hour arranged around a 24-hour dial from "
        "midnight at the top. Bar length is the number of trips. The city "
        f"is quietest before dawn, spikes at {morning:02d}:00 as people "
        f"ride to work, dips at midday, then climbs to its busiest hour at "
        f"{evening:02d}:00 as it rides home."
    )
    parts.append(f'<desc id="rb-desc">{desc}</desc>')

    # ---- interactivity + gentle grow-out (pure CSS + SMIL, no JS) ----
    style_rows = [
        ".bar { transition: opacity .18s ease, transform .18s ease; "
        "transform-box: fill-box; transform-origin: center; }",
        # Hover/focus anywhere dims every bar; the matching rule then
        # restores and lifts the one being pointed at.
        "svg:hover .bar, svg:focus-within .bar { opacity: .28; }",
        "svg .bar:hover, svg .bar:focus { opacity: 1; }",
        f".bar:focus {{ outline: 3px solid {_FOCUS}; outline-offset: 2px; }}",
        "@media (prefers-reduced-motion: reduce) { .bar { transition: none; } "
        ".grow { animation: none !important; } }",
    ]
    # OS-adaptive overrides (additive; every rule lives inside an @media block,
    # so the default render is byte-for-byte unchanged). The two working hues
    # carry ``.rb-base`` (off-peak) / ``.rb-peak`` (rush) classes on the bars,
    # the legend swatches and the centre peak readouts. Under prefers-contrast
    # they deepen to their high-contrast blue/orange, keeping the two-peak read
    # crisp (role="fill" only, so each bar's white keyline is untouched).
    # forced-colors is left to the browser default — the peak accent is a
    # colour encoding the ~4-colour system palette cannot preserve, and the
    # legend plus bar length carry the split regardless.
    rb_series = {".rb-base": hues["base"], ".rb-peak": hues["peak"]}
    style_rows.append(os_adaptive_style(rb_series, role="fill"))
    # Dark mode: invert paper + inks, dim the light concentric rings / hour
    # spokes (stroke #E8E8ED) to a dark-surface grey. The bars keep their white
    # keylines (os_dark_style leaves stroke="#FFFFFF" alone).
    style_rows.append(os_dark_style(extra='[stroke="#E8E8ED"]{stroke:#2E2E30;}'))
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle (upper-left, poster weight) ----
    parts.append(
        f'<text x="60" y="72" font-size="34" font-weight="700" '
        f'fill="{_INK}">A city with two rush hours</text>'
    )
    parts.append(
        f'<text x="60" y="106" font-size="18" fill="{_SUBTLE}">'
        f'Vélomarée bike-share · trips by hour on an average weekday · '
        f'{_fmt_trips(total)} daily rides · illustrative</text>'
    )

    # ---- polar grid: concentric rings + ring value labels ----
    n_rings = int(round(axis_max / ring_step))
    parts.append('<g>')
    # Faint base ring at the hole so the inner edge reads as an axis.
    parts.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R_IN:.2f}" fill="none" '
        f'stroke="{_GRID}" stroke-width="1.4"/>'
    )
    for k in range(1, n_rings + 1):
        r = _R_IN + k * ring_step * scale
        parts.append(
            f'<circle cx="{_CX}" cy="{_CY}" r="{r:.2f}" fill="none" '
            f'stroke="{_GRID}" stroke-width="1.4"/>'
        )
        # Ring value label, dropped just left of the midnight spoke.
        val = k * ring_step
        parts.append(
            f'<text x="{_CX - 8:.1f}" y="{_CY - r + 5:.1f}" font-size="14" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'text-anchor="end">{_fmt_trips(val)}</text>'
        )
    parts.append('</g>')

    # ---- hour spokes (every 3 hours, faint) ----
    parts.append('<g>')
    for h in range(0, n, 3):
        bearing = h * sector_deg
        x0, y0 = _polar(_CX, _CY, _R_IN, bearing)
        x1, y1 = _polar(_CX, _CY, _R_OUT + 6, bearing)
        parts.append(
            f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" '
            f'stroke="{_GRID}" stroke-width="1.3"/>'
        )
    parts.append('</g>')

    # ---- hour-of-day labels around the rim (every 3 hours) ----
    # Side-aware anchoring so each label sits at a constant radial gap and
    # never crowds the rim; the four quarter hours are emphasised.
    quarters = {0, 6, 12, 18}
    for h in range(0, n, 3):
        bearing = h * sector_deg
        is_q = h in quarters
        lx, ly = _polar(_CX, _CY, _R_OUT + (30 if is_q else 24), bearing)
        dx = lx - _CX
        if dx > 3.0:
            anchor = "start"
        elif dx < -3.0:
            anchor = "end"
        else:
            anchor = "middle"
        size = 20 if is_q else 15
        weight = 700 if is_q else 500
        fill = _INK if is_q else _SUBTLE
        label = f"{h:02d}:00"
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'dominant-baseline="middle">{label}</text>'
        )

    # ---- the bars: one annular wedge per hour ----
    parts.append('<g class="grow">')
    for h, v in enumerate(data):
        centre = h * sector_deg
        a0 = centre - (sector_deg - pad_deg) / 2.0
        a1 = centre + (sector_deg - pad_deg) / 2.0
        r1 = _R_IN + v * scale
        # Rounded outer cap: draw the wedge slightly short, then a
        # rounded stroke join fakes the cap without an extra shape.
        path = _annular_bar(_CX, _CY, _R_IN, r1, a0, a1)
        is_peak = v >= peak_cut
        color = hues["peak"] if is_peak else hues["base"]
        bar_hue_class = "rb-peak" if is_peak else "rb-base"
        # Off-peak bars sit a touch translucent so the two peaks dominate
        # the read without any colour clash.
        base_op = 1.0 if is_peak else 0.88
        share = 100.0 * v / total
        tip = (
            f'{h:02d}:00 – {h:02d}:59 · {_fmt_trips(v)} trips '
            f'({share:.1f}% of the day)'
        )
        parts.append(
            f'<path class="bar {bar_hue_class}" tabindex="0" role="listitem" '
            f'd="{path}" fill="{color}" fill-opacity="{base_op}" '
            f'stroke="{_BG}" stroke-width="1.6" stroke-linejoin="round">'
            f'<title>{_xml(tip)}</title>'
            # One-shot grow-out: bars are full-size at t=0 (base state),
            # briefly shrink toward the hub, then settle — never appearing
            # from nothing. keyTimes start at the settled size.
            f'<animateTransform attributeName="transform" type="scale" '
            f'additive="sum" values="1;1;0.02;1" keyTimes="0;0.001;0.002;1" '
            f'dur="0.9s" begin="0s" fill="freeze" '
            f'calcMode="spline" keySplines="0 0 1 1;0 0 1 1;0.22 1 0.36 1"/>'
            f'</path>'
        )
    parts.append('</g>')

    # ---- centre readout: the two peak hours, the takeaway in numbers ----
    parts.append(
        f'<text x="{_CX:.0f}" y="{_CY - 52:.0f}" font-size="16" '
        f'font-weight="600" fill="{_SUBTLE}" text-anchor="middle" '
        f'letter-spacing="1.5">TWO PEAKS</text>'
    )
    parts.append(
        f'<text class="rb-peak" x="{_CX:.0f}" y="{_CY - 8:.0f}" font-size="46" '
        f'font-weight="700" fill="{hues["peak"]}" text-anchor="middle">'
        f'{morning:02d}:00</text>'
    )
    parts.append(
        f'<text x="{_CX:.0f}" y="{_CY + 22:.0f}" font-size="17" '
        f'fill="{_SUBTLE}" text-anchor="middle">to work · '
        f'{_fmt_trips(data[morning])} trips</text>'
    )
    parts.append(
        f'<text class="rb-peak" x="{_CX:.0f}" y="{_CY + 64:.0f}" font-size="46" '
        f'font-weight="700" fill="{hues["peak"]}" text-anchor="middle">'
        f'{evening:02d}:00</text>'
    )
    parts.append(
        f'<text x="{_CX:.0f}" y="{_CY + 94:.0f}" font-size="17" '
        f'fill="{_SUBTLE}" text-anchor="middle">to home · '
        f'{_fmt_trips(data[evening])} trips</text>'
    )

    # ---- legend (base vs peak), lower-left ----
    lx0 = 60.0
    ly0 = _HEIGHT - 116.0
    parts.append(
        f'<text x="{lx0:.0f}" y="{ly0 - 14:.0f}" font-size="16" '
        f'font-weight="700" fill="{_INK}">Bar length = trips that hour</text>'
    )
    legend = [
        (hues["base"], 0.88, "Off-peak hour", "rb-base"),
        (hues["peak"], 1.0, f"Rush peak (≥ {_fmt_trips(peak_cut)} trips)", "rb-peak"),
    ]
    for i, (color, op, label, hue_class) in enumerate(legend):
        yy = ly0 + 14 + i * 34
        parts.append(
            f'<rect class="{hue_class}" x="{lx0:.0f}" y="{yy - 15:.0f}" '
            f'width="26" height="26" rx="7" fill="{color}" fill-opacity="{op}"/>'
        )
        parts.append(
            f'<text x="{lx0 + 38:.0f}" y="{yy:.0f}" font-size="17" '
            f'font-weight="500" fill="{_INK}" dominant-baseline="middle">'
            f'{_xml(label)}</text>'
        )

    # ---- footnote: how to read the dial ----
    parts.append(
        f'<text x="{_WIDTH - 60:.0f}" y="{_HEIGHT - 44:.0f}" font-size="15" '
        f'fill="{_SUBTLE}" text-anchor="end">Read it like a clock: midnight '
        f'up top, noon at the bottom.</text>'
    )
    parts.append(
        f'<text x="{_WIDTH - 60:.0f}" y="{_HEIGHT - 22:.0f}" font-size="15" '
        f'fill="{_SUBTLE}" text-anchor="end">Hover any hour for its exact '
        f'count.</text>'
    )

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the radial-bar SVG to the skill's ``svg-examples`` folder."""
    render_cli(__file__, "radial-bar", build_svg, description="Render the radial-bar SVG.")


if __name__ == "__main__":
    main()

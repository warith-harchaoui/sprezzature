#!/usr/bin/env python3
"""Generate a publication-quality *polar plot* as a standalone SVG.

A polar plot places data on an **angular axis** (θ) and a **radial axis** (r):
each observation is a point at distance ``r`` from the centre, at bearing ``θ``.
It is the natural chart for anything *cyclic* — a compass, a 24-hour clock, a
seasonal round — where wrapping the axis into a circle keeps midnight next to
23:00 and the reader can see the shape of the cycle at a glance instead of a
line that falsely "jumps" from the right edge back to the left. It is the R
``coord_polar`` / matplotlib ``projection="polar"`` / plotly ``scatterpolar``
idiom.

This module builds the SVG string **by hand** (no matplotlib / seaborn /
plotly, no Vega): it maps a cyclic series onto polar coordinates, draws the
radial grid rings and the hour spokes of a clock face, and paints a filled
radial area with its outline and data dots. The figure is deliberately
**static** — the shape of the day is the insight, and a still renders it in
full at a glance; a spinning "radar sweep" would only distract from the twin
commuter peaks the reader is here to see. Everything is in the sprezzature-* house
style: Roboto type, the Apple-system palette, ink ``#1D1D1F`` on a white
ground, rounded framing, native ``<title>`` hover tooltips (no JavaScript).

The example data is illustrative: the hourly departure count of a city
bike-share network over an average weekday, which shows the twin commuter
peaks (the morning and evening rushes) that a polar clock makes instantly
legible.

Usage
-----
    python make_polar.py                 # writes the house SVG
    python make_polar.py --out other.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc
classes, generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations
from _render import write_svg  # noqa: E402
from _style import leveled_colors, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import fmt_compact, svg_open  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

import argparse
import math
from pathlib import Path
from typing import List, Tuple

import numpy as np

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "polar.svg"
)

# House-style tokens (mirrors _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_GRID = "#E5E5EA"       # light grid rings / spokes
_ACCENT = "#007AFF"     # Apple-system Blue — the series colour
_ACCENT_FILL = "#7FBBFF"  # a lighter Blue for the filled area
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"


# --------------------------------------------------------------------------- #
# Illustrative data                                                            #
# --------------------------------------------------------------------------- #
def _sample_hourly_trips(seed: int = 11) -> np.ndarray:
    """Synthesise an average-weekday, hour-by-hour bike-share departure count.

    The profile is the classic bimodal commuter shape: a trough overnight, a
    sharp morning peak around 08:00, a mid-day plateau, a taller evening peak
    around 18:00, then a decline into the night. Small reproducible noise keeps
    the dots from lying on a suspiciously perfect curve.

    Parameters
    ----------
    seed : int, optional
        Seed for the random generator, for a reproducible figure.

    Returns
    -------
    numpy.ndarray
        Length-24 array; index ``h`` is the departure count during hour ``h``
        (00:00 … 23:00).
    """
    rng = np.random.default_rng(seed)
    hours = np.arange(24)
    # Two Gaussian commuter bumps + a low overnight baseline.
    morning = 620.0 * np.exp(-0.5 * ((hours - 8.0) / 1.3) ** 2)
    evening = 780.0 * np.exp(-0.5 * ((hours - 18.0) / 1.6) ** 2)
    midday = 240.0 * np.exp(-0.5 * ((hours - 13.0) / 3.5) ** 2)
    baseline = 40.0
    counts = baseline + morning + evening + midday
    counts = counts + rng.normal(0.0, 14.0, size=24)  # small measurement jitter
    return np.clip(counts, 0.0, None)


# --------------------------------------------------------------------------- #
# Polar geometry                                                               #
# --------------------------------------------------------------------------- #
def _polar_to_xy(cx: float, cy: float, r: float, theta_deg: float) -> Tuple[float, float]:
    """Convert a polar coordinate to an SVG (x, y) pixel, clock-oriented.

    ``theta_deg`` is measured *clockwise from the top* (12 o'clock = 0°), the
    convention a clock face and a compass share — unlike the mathematical
    counter-clockwise-from-east convention — so hour 0 sits at the top and the
    day runs clockwise.

    Parameters
    ----------
    cx, cy : float
        Centre of the dial in pixels.
    r : float
        Radius in pixels.
    theta_deg : float
        Angle in degrees, clockwise from the 12 o'clock position.

    Returns
    -------
    tuple of float
        The ``(x, y)`` pixel position.
    """
    # Rotate so 0° points up, and go clockwise: standard SVG y grows downward,
    # so clockwise-from-top is (sin, -cos) about the vertical.
    rad = math.radians(theta_deg)
    x = cx + r * math.sin(rad)
    y = cy - r * math.cos(rad)
    return x, y


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def build_svg(
    counts: np.ndarray,
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full polar-plot SVG document as a string.

    Parameters
    ----------
    counts : numpy.ndarray
        Length-24 array of hourly departure counts (index = hour of day).
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`.
        One of ``"self-contained"`` (default, ships a hidden-until-live
        fullscreen button), ``"external"`` or ``"static"`` (no button).
    accessibility : str, optional
        Palette accessibility level for the series colour. The single-series
        accent (stroke / dots / callouts) and its lighter area fill are a
        categorical set of two, collected into a ``{name: hex}`` map and wrapped
        with :func:`_style.leveled_colors`. ``"universal"`` (default) is the
        identity, so the shipped SVG is byte-for-byte unchanged.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    # The series colour is a categorical set of two (the accent line/dots and
    # its lighter area fill); level it so the figure answers to accessibility.
    _levelled = leveled_colors(
        {"accent": _ACCENT, "accent_fill": _ACCENT_FILL}, accessibility
    )
    accent = _levelled["accent"]
    accent_fill = _levelled["accent_fill"]

    n = counts.size  # 24 hours
    # Poster-scale canvas: a generous square dial with room for title,
    # hour labels, and the radial-scale caption.
    width, height = 980, 1040

    # Dial geometry. Leave a top band for the title and a bottom band for the
    # radial-scale caption, and centre the dial in the remaining space.
    cx = width / 2.0
    cy = 560.0
    r_outer = 340.0     # outermost grid ring (the rounded scale max maps here)
    r_inner = 0.0       # centre

    # ---- radial scale ----------------------------------------------------- #
    # Round the domain up to a friendly tick so the outer ring is a round
    # number the reader can anchor on, with a touch of headroom so the peak
    # dot never kisses the rim (no clipping at the outer edge).
    data_max = float(counts.max())
    tick_step = 250.0
    r_max = math.ceil((data_max * 1.06) / tick_step) * tick_step  # e.g. 1000
    rings = np.arange(tick_step, r_max + 1e-6, tick_step)  # 250, 500, 750, 1000

    def r_px(value: float) -> float:
        """Map a data value to a pixel radius on the dial."""
        return r_inner + (value / r_max) * (r_outer - r_inner)

    # Angle per hour: 360 / 24 = 15° per step, clockwise from the top.
    def theta(hour: float) -> float:
        """Return the clock angle (deg, clockwise from top) for an hour."""
        return (hour / n) * 360.0

    parts: List[str] = []

    # ---- header / accessibility ------------------------------------------- #
    title = "The city breathes twice a day"
    subtitle = (
        "Bike-share departures by hour of an average weekday — Illustrative data"
    )
    aria = (
        "Polar clock plot of bike-share departures by hour of day, running "
        "clockwise from midnight at the top. Departures are lowest overnight, "
        "rise to a sharp morning peak near 8 a.m., dip at midday, then climb to "
        "the day's tallest peak near 6 p.m. before falling into the night."
    )
    parts.append(svg_open(width, height, "polar-title", "polar-desc", font_family=_FONT))
    parts.append(f'<title id="polar-title">{title}</title>')
    parts.append(f'<desc id="polar-desc">{aria}</desc>')
    # OS-adaptive override (additive; the default render is byte-identical
    # because every rule lives inside a media query). This is a single-series
    # figure — one blue accent carries the area outline, the data dots and the
    # peak callouts. Under prefers-contrast that accent deepens to a
    # higher-contrast Blue on both stroke (outline + dots keyline family) and
    # fill (the dots). The translucent lighter area fill is deliberately left
    # alone so the interior stays readable.
    parts.append(
        "<style>\n"
        + os_adaptive_style({".po-accent": accent}, role="both")
        + "\n"
        # Additive OS dark mode: dark paper + light ink (default ink_map); the
        # accent hue (outline + dots + filled area) is data, left alone. The
        # light clock-face grid rings and hour spokes darken so the scaffold
        # reads on the dark surface.
        + os_dark_style(extra='[stroke="#E5E5EA"]{stroke:#333338;}')
        + "\n</style>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="22" fill="{_BG}"/>')
    parts.append(
        f'<text x="64" y="76" font-size="36" font-weight="700" fill="{_INK}">'
        f"{title}</text>"
    )
    parts.append(
        f'<text x="64" y="114" font-size="21" fill="{_SECONDARY}">{subtitle}</text>'
    )

    # ---- grid rings + radial tick labels ---------------------------------- #
    for ring_val in rings:
        rr = r_px(float(ring_val))
        parts.append(
            f'<circle cx="{fmt_compact(cx)}" cy="{fmt_compact(cy)}" r="{fmt_compact(rr)}" '
            f'fill="none" stroke="{_GRID}" stroke-width="1"/>'
        )
        # Radial tick label along the 12 o'clock spoke, nudged off the ring.
        lx, ly = _polar_to_xy(cx, cy, rr, 0.0)
        parts.append(
            f'<text x="{fmt_compact(lx + 9)}" y="{fmt_compact(ly + 6)}" font-size="16" '
            f'font-family="{_MONO}" fill="{_SECONDARY}">{int(ring_val)}</text>'
        )

    # ---- hour spokes + hour labels ---------------------------------------- #
    # Draw a spoke every 3 hours (a light grid) and label those.
    for hour in range(0, n, 3):
        ang = theta(hour)
        ex, ey = _polar_to_xy(cx, cy, r_outer, ang)
        parts.append(
            f'<line x1="{fmt_compact(cx)}" y1="{fmt_compact(cy)}" x2="{fmt_compact(ex)}" '
            f'y2="{fmt_compact(ey)}" stroke="{_GRID}" stroke-width="1"/>'
        )
        # Hour label just outside the outer ring.
        lx, ly = _polar_to_xy(cx, cy, r_outer + 34, ang)
        label = f"{hour:02d}h"
        # Vertically centre labels near the horizontal axis; anchor by side.
        anchor = "middle"
        if 30 < ang < 150:
            anchor = "start"
        elif 210 < ang < 330:
            anchor = "end"
        parts.append(
            f'<text x="{fmt_compact(lx)}" y="{fmt_compact(ly + 7)}" text-anchor="{anchor}" '
            f'font-size="19" font-family="{_MONO}" fill="{_INK}">{label}</text>'
        )

    # ---- filled radial area (closed cyclic polygon) ----------------------- #
    # Build the closed polygon of (hour → r) so the cycle wraps seamlessly.
    area_pts: List[Tuple[float, float]] = []
    for hour in range(n):
        px, py = _polar_to_xy(cx, cy, r_px(float(counts[hour])), theta(hour))
        area_pts.append((px, py))
    area_d = "M" + " L".join(f"{fmt_compact(px)},{fmt_compact(py)}" for px, py in area_pts) + " Z"
    parts.append(
        f'<path class="po-accent" d="{area_d}" fill="{accent_fill}" '
        f'fill-opacity="0.30" stroke="{accent}" stroke-width="3.4" '
        f'stroke-linejoin="round"/>'
    )

    # ---- data dots with native hover tooltips ----------------------------- #
    # Fully drawn, no motion: each hour is a filled dot with a thin white keyline
    # so overlapping dots near the centre stay separable (no colour-on-colour).
    for hour in range(n):
        value = float(counts[hour])
        px, py = _polar_to_xy(cx, cy, r_px(value), theta(hour))
        tip = f"{hour:02d}:00 — {value:.0f} departures"
        # Emphasise the two peak hours with a larger, filled dot.
        is_peak = hour in (int(np.argmax(counts[6:11]) + 6), int(np.argmax(counts)))
        radius = 8.5 if is_peak else 5.0
        parts.append(
            f'<g class="pt"><title>{tip}</title>'
            f'<circle class="po-accent" cx="{fmt_compact(px)}" cy="{fmt_compact(py)}" '
            f'r="{radius}" fill="{accent}" stroke="#FFFFFF" stroke-width="2"/></g>'
        )

    # ---- peak callouts ---------------------------------------------------- #
    # Each peak dot gets an ink label set into the open interior of the dial,
    # joined to its dot by a thin accent leader. Values are called out so the
    # reader gets the height without tracing back to a ring.
    def _callout(
        hour: int, text: str, dx: float, dy: float, anchor: str
    ) -> None:
        """Draw a peak label with a leader line back to its data dot.

        The nudge (``dx``/``dy``) tucks the two-line label into the open
        interior of the dial, clear of the outer hour labels; the leader keeps
        the association explicit.
        """
        value = float(counts[hour])
        px0, py0 = _polar_to_xy(cx, cy, r_px(value), theta(hour))
        lx, ly = px0 + dx, py0 + dy
        # Leader from the dot toward the label anchor (short, thin, accent).
        parts.append(
            f'<line x1="{fmt_compact(px0)}" y1="{fmt_compact(py0)}" x2="{fmt_compact(lx)}" '
            f'y2="{fmt_compact(ly - 6)}" stroke="{accent}" stroke-width="1.6" '
            f'stroke-opacity="0.55"/>'
        )
        parts.append(
            f'<text x="{fmt_compact(lx)}" y="{fmt_compact(ly - 12)}" '
            f'text-anchor="{anchor}" font-size="22" font-weight="700" '
            f'fill="{accent}">{text}</text>'
        )
        parts.append(
            f'<text x="{fmt_compact(lx)}" y="{fmt_compact(ly + 12)}" '
            f'text-anchor="{anchor}" font-size="17" font-weight="500" '
            f'fill="{_SECONDARY}">{value:.0f} departures/h</text>'
        )

    peak_hour = int(np.argmax(counts))                 # 18:00 — evening peak
    morning_hour = int(np.argmax(counts[6:11]) + 6)    # 08:00 — morning peak
    # Evening dot sits at the far-left edge, so lift its label up-and-inward,
    # clear of the "18h" hour label. Morning dot has open room below-right.
    _callout(peak_hour, "Evening rush", dx=-6, dy=-96, anchor="middle")
    _callout(morning_hour, "Morning rush", dx=44, dy=60, anchor="start")

    # ---- radial-axis caption (bottom) ------------------------------------- #
    parts.append(
        f'<text x="{fmt_compact(cx)}" y="{height - 48}" text-anchor="middle" '
        f'font-size="19" fill="{_INK}">'
        f"Radius = departures per hour   ·   angle = hour of day (clockwise "
        f"from midnight)</text>"
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_polar",
        description="Write the house-style polar (clock) plot SVG example.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--seed", type=int, default=11, help="Random seed for the sample data."
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the fullscreen control (default: self-contained).",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal", "high-contrast", "monochrome",
            "deuteranopia", "protanopia", "tritanopia",
        ),
        default="universal",
        help="palette accessibility level (default: universal, the CVD-safe standard)",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to disk."""
    args = _build_parser().parse_args(argv)
    counts = _sample_hourly_trips(seed=args.seed)
    svg = build_svg(counts, args.mode, accessibility=args.accessibility)
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

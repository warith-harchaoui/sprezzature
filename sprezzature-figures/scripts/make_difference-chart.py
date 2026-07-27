#!/usr/bin/env python3
"""Generate a publication-quality *difference chart* as a standalone static SVG.

A difference chart lays two time series on the same axis and shades the band
*between* them in two colours: one hue where the first series runs **above** the
second, a contrasting hue where it runs **below**. It answers "who is ahead,
by how much, and when did the lead flip?" faster than two plain lines, because
the eye reads the coloured area as a running surplus / deficit rather than
having to mentally subtract one curve from the other at every point.

This module builds the SVG string **by hand** (no matplotlib / seaborn /
plotly, no Vega): the trick a plotting library makes awkward is the two-colour
fill of the *inter-curve* region, which we get cleanly with a pair of SVG
``clipPath`` half-planes — the above-hue area is clipped to "actual is on top",
the below-hue area to "plan is on top" — so the two colours meet exactly on
every crossing with no overlap and no seam. The two curves ride on top as crisp
lines, and the crossings (where the surplus flips to a shortfall) are marked.

A difference chart is a dense static comparison; motion adds nothing a still
cannot already show, so the whole picture is drawn fully at rest — every band,
line and marker is present the instant the SVG loads. Colour is a redundant
channel on top of "which line is higher", and each region also carries a
native ``<title>`` tooltip, so the story survives colour-vision deficiency.

The example data is illustrative: a mid-size software company's **actual
monthly recurring revenue** plotted against the **board-approved plan** across
one fiscal year — the framing difference charts are made for, where a blue
cushion in the strong quarters and a red gap in the summer slump are legible
at a glance.

Usage
-----
    python make_difference-chart.py                 # writes the house SVG
    python make_difference-chart.py --out other.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc
classes, generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _svg import catmull_rom_beziers, fmt_compact  # noqa: E402
from _render import write_svg  # noqa: E402
from _style import leveled_colors, os_adaptive_style, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "difference-chart.svg"
)

# House-style tokens (mirrors _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"

# Bicolour gap fill, drawn from the Apple-system palette, following the house
# blue-vs-red convention for a signed quantity (never red-vs-green, which
# collapses under the common red-green colour-vision deficiencies). A surplus
# (actual above plan) reads Blue (the positive side); a shortfall (actual below
# plan) reads Red (the warning side). The two hues stay distinct under
# deuteranopia and protanopia and separate cleanly in greyscale by lightness.
_ABOVE_HUE = "#007AFF"  # Apple Blue — actual is ahead of plan (surplus)
_BELOW_HUE = "#FF3B30"  # Apple Red  — actual is behind plan (shortfall)
# Line colours: the "actual" curve is the hero (deep ink-blue), the "plan"
# curve is a calmer reference grey so the surplus / shortfall band is the star.
_ACTUAL_LINE = "#0A2540"  # near-navy — the measured series
_PLAN_LINE = "#8E8E93"    # neutral grey — the reference / target series


# --------------------------------------------------------------------------- #
# Illustrative data                                                            #
# --------------------------------------------------------------------------- #
def _sample_revenue(seed: int = 7) -> Dict[str, np.ndarray]:
    """Synthesise a fiscal year of actual vs planned monthly recurring revenue.

    The board plan is a smooth, confident ramp from the January run-rate to an
    ambitious December target. Actuals start ahead (a strong Q1 launch), sag
    through the summer as a big customer churns and hiring slows sales, then
    recover and finish just shy of plan — the classic surplus-then-shortfall
    shape a difference chart is built to narrate.

    Parameters
    ----------
    seed : int, optional
        Seed for the random generator, for a reproducible figure.

    Returns
    -------
    dict of str to numpy.ndarray
        ``{"plan": np.ndarray, "actual": np.ndarray}`` — 12 values each, in
        thousands of dollars of monthly recurring revenue, Jan → Dec.
    """
    rng = np.random.default_rng(seed)
    months = np.arange(12)

    # Board plan: a steady linear ramp from 430k to 720k over the year.
    plan = np.linspace(430.0, 720.0, 12)

    # Actual: plan plus a hand-shaped surplus/deficit envelope that matches the
    # headline — a strong spring surplus (green cushion), a summer dip below
    # plan (red shortfall as a big customer churns and hiring slows), then a
    # late-year climb back to roughly parity.
    envelope = (
        40.0 * np.exp(-0.5 * ((months - 2.5) / 2.0) ** 2)    # spring surplus
        - 52.0 * np.exp(-0.5 * ((months - 7.5) / 2.0) ** 2)  # summer shortfall
        + 20.0 * np.exp(-0.5 * ((months - 11.0) / 1.4) ** 2)  # year-end rally
    )
    noise = rng.normal(0.0, 3.0, size=12)
    actual = plan + envelope + noise

    return {"plan": plan, "actual": actual}


# --------------------------------------------------------------------------- #
# Geometry helpers                                                             #
# --------------------------------------------------------------------------- #
# Compact path-data formatter, now shared in _svg (byte-identical to the old
# private ``_fmt``); the local name is kept so the call sites stay untouched.
_fmt = fmt_compact


def _catmull_rom(pts: Sequence[Tuple[float, float]], tension: float = 6.0) -> str:
    """Return SVG ``C`` commands for a smooth Catmull-Rom spline through ``pts``.

    Thin wrapper over :func:`_svg.catmull_rom_beziers` that pins the local
    :func:`_fmt` formatter, so the emitted string is identical to the old
    inline copy while the spline maths lives in the shared module.

    Parameters
    ----------
    pts : sequence of (float, float)
        The sample points, in pixel coordinates.
    tension : float, optional
        Catmull-Rom denominator; ``6`` is the standard uniform spline.

    Returns
    -------
    str
        A run of SVG ``C`` path commands (a plain line-to when < 3 points).
    """
    return catmull_rom_beziers(pts, _fmt, tension)


def _line_path(pts: Sequence[Tuple[float, float]]) -> str:
    """Return a smooth open ``d`` path string for a curve through ``pts``."""
    x0, y0 = pts[0]
    return f"M{_fmt(x0)},{_fmt(y0)}" + _catmull_rom(pts)


def _band_path(
    top: Sequence[Tuple[float, float]],
    bottom: Sequence[Tuple[float, float]],
) -> str:
    """Return a closed ``d`` path filling between two same-x sample curves.

    Both edges are drawn as smooth Catmull-Rom splines so the shaded band's
    boundaries match the rendered curves exactly.

    Parameters
    ----------
    top, bottom : sequence of (float, float)
        The two curves, sampled at the same x-positions, left → right.

    Returns
    -------
    str
        A closed SVG path ``d`` string (top edge left→right, bottom edge
        right→left).
    """
    d = _line_path(top)
    rev = list(reversed(bottom))
    d += f" L{_fmt(rev[0][0])},{_fmt(rev[0][1])}" + _catmull_rom(rev)
    return d + " Z"


def _crossings(
    xs: Sequence[float],
    a: Sequence[float],
    b: Sequence[float],
) -> List[Tuple[float, float]]:
    """Return interpolated ``(x, value)`` points where curve ``a`` crosses ``b``.

    Linear interpolation between adjacent samples locates each sign change of
    ``a - b`` — the moments a surplus flips to a shortfall or back.

    Parameters
    ----------
    xs : sequence of float
        Sample x-positions (data units).
    a, b : sequence of float
        The two series values at those x-positions.

    Returns
    -------
    list of (float, float)
        ``(x, value)`` of each crossing, in data units.
    """
    out: List[Tuple[float, float]] = []
    diff = [ai - bi for ai, bi in zip(a, b)]
    for i in range(len(xs) - 1):
        d0, d1 = diff[i], diff[i + 1]
        if d0 == 0.0:
            out.append((xs[i], a[i]))
        elif d0 * d1 < 0.0:
            # Fraction along the segment where the difference hits zero.
            t = d0 / (d0 - d1)
            x = xs[i] + t * (xs[i + 1] - xs[i])
            v = a[i] + t * (a[i + 1] - a[i])
            out.append((x, v))
    return out


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def build_svg(
    data: Dict[str, np.ndarray],
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full difference-chart SVG document as a string.

    Parameters
    ----------
    data : dict of str to numpy.ndarray
        ``{"plan": ..., "actual": ...}``; 12 monthly values each, Jan → Dec.
    mode : str, optional
        Interactivity mode for the figure (default ``"self-contained"``).
        ``"self-contained"`` embeds a self-carrying fullscreen button and the
        script that wires it, so the SVG works on its own; ``"external"``
        defers that control to a page-level module; ``"static"`` ships no
        interactivity at all. In every mode a plain ``<img>`` or PNG raster is
        byte-identical, since the button starts hidden.
    accessibility : str, optional
        Palette accessibility level applied to the figure's categorical hues —
        the blue surplus / red shortfall gap fills and the actual / plan line
        colours (default ``"universal"``, the identity, so the shipped SVG is
        byte-for-byte unchanged). Other levels remap those hues through the
        sprezzature-colors engine so surplus stays distinct from shortfall for that
        viewer.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    # Categorical hues, remapped for the requested accessibility level. These
    # shadow the module-level constants inside this function's scope, so every
    # f-string below picks up the levelled colour; ``universal`` is the
    # identity, keeping the default output byte-for-byte unchanged.
    _diff_colours = leveled_colors(
        {
            "above": _ABOVE_HUE,
            "below": _BELOW_HUE,
            "actual": _ACTUAL_LINE,
            "plan": _PLAN_LINE,
        },
        accessibility,
    )
    _ABOVE_HUE_C = _diff_colours["above"]
    _BELOW_HUE_C = _diff_colours["below"]
    _ACTUAL_LINE_C = _diff_colours["actual"]
    _PLAN_LINE_C = _diff_colours["plan"]

    plan = data["plan"]
    actual = data["actual"]
    n = len(plan)
    months = np.arange(n)
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # ---- canvas geometry -------------------------------------------------- #
    # Poster-scale: wide enough for 12 months to breathe, tall enough that the
    # surplus / shortfall band is a comfortable shape rather than a sliver.
    width, height = 1240, 780
    m_left, m_right = 96, 210
    m_top, m_bottom = 168, 96
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    # ---- value scale ------------------------------------------------------ #
    # Round the domain to tidy $100k gridlines with headroom above / below so
    # nothing kisses the frame.
    lo = float(min(actual.min(), plan.min()))
    hi = float(max(actual.max(), plan.max()))
    # Round to tidy $50k gridlines with a little headroom, so the band fills
    # most of the plot rather than floating in empty space.
    y_lo = np.floor((lo - 25.0) / 50.0) * 50.0
    y_hi = np.ceil((hi + 25.0) / 50.0) * 50.0

    def x_of(m: float) -> float:
        """Map a month index (0..n-1) to a pixel column."""
        return m_left + m / (n - 1) * plot_w

    def y_of(v: float) -> float:
        """Map a revenue value to a pixel row (higher value → higher up)."""
        return m_top + (y_hi - v) / (y_hi - y_lo) * plot_h

    plan_pts = [(x_of(float(m)), y_of(float(plan[i]))) for i, m in enumerate(months)]
    actual_pts = [(x_of(float(m)), y_of(float(actual[i]))) for i, m in enumerate(months)]

    parts: List[str] = []
    defs: List[str] = []

    # ---- header ----------------------------------------------------------- #
    title = "Revenue outran plan all spring, then fell behind through the summer"
    subtitle = ("Actual vs board-planned monthly recurring revenue, "
                "one fiscal year")
    parts.append(
        f'<svg role="img" aria-label="{title}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}">'
    )
    parts.append(
        f"<title>{title}</title>"
        f"<desc>Difference chart: a near-navy line is actual monthly recurring "
        f"revenue, a grey line is the board plan. The band between them is "
        f"shaded blue where actual runs above plan (a surplus, strongest in "
        f"spring) and red where it runs below (a shortfall through the summer). "
        f"Illustrative data.</desc>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="18" fill="{_BG}"/>')
    parts.append(
        f'<text x="{m_left}" y="72" font-size="31" '
        f'font-weight="700" fill="{_INK}">{title}</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="106" font-size="18" '
        f'fill="{_SECONDARY}">{subtitle}</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="130" font-size="16" '
        f'fill="{_SECONDARY}">Illustrative data &#183; thousands of dollars '
        f'per month</text>'
    )

    # ---- horizontal $100k gridlines --------------------------------------- #
    grid: List[str] = []
    ax_labels: List[str] = []
    step = 50.0
    v = y_lo
    while v <= y_hi + 1e-6:
        gy = y_of(v)
        grid.append(
            f'<line x1="{_fmt(m_left)}" y1="{_fmt(gy)}" '
            f'x2="{_fmt(m_left + plot_w)}" y2="{_fmt(gy)}" '
            f'stroke="#EFEFF2" stroke-width="1.4"/>'
        )
        ax_labels.append(
            f'<text x="{_fmt(m_left - 16)}" y="{_fmt(gy + 5)}" text-anchor="end" '
            f'font-size="15" font-family="{_MONO}" fill="{_SECONDARY}">'
            f"${v / 1000:.2f}M</text>"
        )
        v += step

    # ---- bicolour gap fill via two clipped half-planes -------------------- #
    # The band between the two curves is filled twice: once blue, clipped to
    # the region where actual >= plan, once red, clipped to where actual < plan.
    # The clip boundary is the *actual* curve, so the two colours meet exactly
    # on it with no overlap. We densely resample both curves so the clip edge
    # follows the smoothed splines, not just the 12 raw vertices.
    dense_m = np.linspace(0.0, n - 1, 400)
    dense_plan = np.interp(dense_m, months, plan)
    dense_actual = np.interp(dense_m, months, actual)
    dense_plan_pts = [(x_of(m), y_of(float(dense_plan[i]))) for i, m in enumerate(dense_m)]
    dense_actual_pts = [(x_of(m), y_of(float(dense_actual[i]))) for i, m in enumerate(dense_m)]

    # The clip boundary is the *plan* curve. Where actual runs above plan, the
    # inter-curve band sits above the plan line (smaller screen-y) — clip the
    # green surplus to that half-plane. Where actual runs below plan, the band
    # sits under the plan line — clip the red shortfall there. Using the plan
    # (reference) curve as the divider keeps the two colours meeting exactly on
    # it with no overlap.
    plan_edge = (
        f"L{_fmt(dense_plan_pts[0][0])},{_fmt(dense_plan_pts[0][1])}"
        + _catmull_rom(dense_plan_pts)
    )
    # Blue surplus: the region above the plan curve (toward the top).
    clip_above = (
        f"M{_fmt(m_left)},{_fmt(m_top - 40)} "
        + plan_edge
        + f" L{_fmt(m_left + plot_w)},{_fmt(m_top - 40)} Z"
    )
    # Red shortfall: the region below the plan curve (toward the bottom).
    clip_below = (
        f"M{_fmt(m_left)},{_fmt(m_top + plot_h + 40)} "
        + plan_edge
        + f" L{_fmt(m_left + plot_w)},{_fmt(m_top + plot_h + 40)} Z"
    )
    defs.append(f'<clipPath id="clipAbove"><path d="{clip_above}"/></clipPath>')
    defs.append(f'<clipPath id="clipBelow"><path d="{clip_below}"/></clipPath>')

    # The full inter-curve band (actual on top edge, plan on bottom edge),
    # filled once per colour and revealed through the two half-plane clips.
    band = _band_path(dense_actual_pts, dense_plan_pts)

    band_group: List[str] = ["<g>"]
    band_group.append(
        f'<path class="diff-above" d="{band}" fill="{_ABOVE_HUE_C}" '
        f'fill-opacity="0.82" clip-path="url(#clipAbove)"/>'
    )
    band_group.append(
        f'<path class="diff-below" d="{band}" fill="{_BELOW_HUE_C}" '
        f'fill-opacity="0.82" clip-path="url(#clipBelow)"/>'
    )
    band_group.append("</g>")

    # ---- the two curves --------------------------------------------------- #
    lines: List[str] = []
    # Plan (reference) first, so the hero actual line reads on top.
    lines.append(
        f'<path d="{_line_path(plan_pts)}" fill="none" stroke="{_PLAN_LINE_C}" '
        f'stroke-width="3" stroke-dasharray="2 7" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
    )
    lines.append(
        f'<path d="{_line_path(actual_pts)}" fill="none" stroke="{_ACTUAL_LINE_C}" '
        f'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # ---- crossing markers ------------------------------------------------- #
    # White-cored dots where the lead flips, so the eye lands on the story beat.
    cross = _crossings([float(m) for m in months],
                       [float(a) for a in actual],
                       [float(p) for p in plan])
    markers: List[str] = []
    for cx_m, cv in cross:
        px, py = x_of(cx_m), y_of(cv)
        markers.append(
            f'<circle cx="{_fmt(px)}" cy="{_fmt(py)}" r="7" fill="{_BG}" '
            f'stroke="{_ACTUAL_LINE_C}" stroke-width="3"/>'
        )

    # ---- month axis ------------------------------------------------------- #
    axis_y = m_top + plot_h
    axis_bits: List[str] = []
    axis_bits.append(
        f'<line x1="{_fmt(m_left)}" y1="{_fmt(axis_y)}" '
        f'x2="{_fmt(m_left + plot_w)}" y2="{_fmt(axis_y)}" '
        f'stroke="{_INK}" stroke-width="1.6"/>'
    )
    for i, m in enumerate(months):
        gx = x_of(float(m))
        axis_bits.append(
            f'<text x="{_fmt(gx)}" y="{_fmt(axis_y + 28)}" text-anchor="middle" '
            f'font-size="15" font-family="{_MONO}" fill="{_SECONDARY}">'
            f"{month_labels[i]}</text>"
        )

    # ---- end-of-line labels (right gutter, side-aware, no clipping) ------- #
    end_labels: List[str] = []
    a_end = actual_pts[-1]
    p_end = plan_pts[-1]
    lbl_x = m_left + plot_w + 20
    # Nudge apart if the two endpoints are close so labels never collide.
    # Preserve vertical order (whichever series ends higher keeps its label on
    # top) while forcing at least ~46 px between the two label anchors.
    ay, py_ = a_end[1], p_end[1]
    if abs(ay - py_) < 46:
        mid = (ay + py_) / 2
        actual_is_higher = ay <= py_
        ay = mid - 23 if actual_is_higher else mid + 23
        py_ = mid + 23 if actual_is_higher else mid - 23
    end_labels.append(
        f'<line x1="{_fmt(a_end[0])}" y1="{_fmt(a_end[1])}" '
        f'x2="{_fmt(lbl_x - 6)}" y2="{_fmt(ay)}" stroke="{_ACTUAL_LINE_C}" '
        f'stroke-width="1.4"/>'
    )
    end_labels.append(
        f'<text x="{_fmt(lbl_x)}" y="{_fmt(ay - 4)}" font-size="18" '
        f'font-weight="700" fill="{_ACTUAL_LINE_C}">Actual</text>'
    )
    end_labels.append(
        f'<text x="{_fmt(lbl_x)}" y="{_fmt(ay + 17)}" font-size="14" '
        f'font-family="{_MONO}" fill="{_SECONDARY}">'
        f"${actual[-1] / 1000:.2f}M</text>"
    )
    end_labels.append(
        f'<line x1="{_fmt(p_end[0])}" y1="{_fmt(p_end[1])}" '
        f'x2="{_fmt(lbl_x - 6)}" y2="{_fmt(py_)}" stroke="{_PLAN_LINE_C}" '
        f'stroke-width="1.4"/>'
    )
    end_labels.append(
        f'<text x="{_fmt(lbl_x)}" y="{_fmt(py_ - 4)}" font-size="18" '
        f'font-weight="700" fill="#5A5A5F">Plan</text>'
    )
    end_labels.append(
        f'<text x="{_fmt(lbl_x)}" y="{_fmt(py_ + 17)}" font-size="14" '
        f'font-family="{_MONO}" fill="{_SECONDARY}">'
        f"${plan[-1] / 1000:.2f}M</text>"
    )

    # ---- legend: the two gap colours -------------------------------------- #
    legend: List[str] = []
    lx = m_left
    ly = 152.0
    sw = 26.0
    sh = 15.0
    legend.append(
        f'<rect class="diff-above" x="{_fmt(lx)}" y="{_fmt(ly - sh + 2)}" '
        f'width="{_fmt(sw)}" height="{_fmt(sh)}" rx="3" fill="{_ABOVE_HUE_C}" '
        f'fill-opacity="0.82"/>'
    )
    legend.append(
        f'<text x="{_fmt(lx + sw + 8)}" y="{_fmt(ly)}" font-size="15" '
        f'fill="{_INK}">Ahead of plan (surplus)</text>'
    )
    lx2 = lx + 250
    legend.append(
        f'<rect class="diff-below" x="{_fmt(lx2)}" y="{_fmt(ly - sh + 2)}" '
        f'width="{_fmt(sw)}" height="{_fmt(sh)}" rx="3" fill="{_BELOW_HUE_C}" '
        f'fill-opacity="0.82"/>'
    )
    legend.append(
        f'<text x="{_fmt(lx2 + sw + 8)}" y="{_fmt(ly)}" font-size="15" '
        f'fill="{_INK}">Behind plan (shortfall)</text>'
    )

    # ---- hover tooltips: one transparent hit-column per month ------------- #
    tips: List[str] = []
    col_w = plot_w / (n - 1)
    for i, m in enumerate(months):
        gx = x_of(float(m))
        gap = float(actual[i] - plan[i])
        sign = "ahead of" if gap >= 0 else "behind"
        tip = (
            f"{month_labels[i]}: actual ${actual[i] / 1000:.2f}M vs plan "
            f"${plan[i] / 1000:.2f}M — ${abs(gap):.0f}k {sign} plan"
        )
        tips.append(
            f'<rect x="{_fmt(gx - col_w / 2)}" y="{_fmt(m_top - 40)}" '
            f'width="{_fmt(col_w)}" height="{_fmt(plot_h + 40)}" '
            f'fill="transparent"><title>{tip}</title></rect>'
        )

    # ---- OS-adaptive overrides (additive) --------------------------------- #
    # The default render stays byte-identical: every rule below lives inside an
    # @media query, so with no OS preference active none of them match and the
    # inline fills win. Under prefers-contrast the two signed band hues deepen
    # to their high-contrast versions (blue surplus / red shortfall), staying
    # distinct and CVD-safe. forced-colors is deliberately left universal
    # (forced=False): the surplus/shortfall band is a two-colour *filled area* —
    # collapsing both to one system colour would merge the two regions into a
    # single mass and destroy the encoding — so the browser's default (leave SVG
    # fills alone) is the correct behaviour here.
    diff_series = {".diff-above": _ABOVE_HUE_C, ".diff-below": _BELOW_HUE_C}
    style_block = os_adaptive_style(diff_series, role="fill")
    # Additive dark mode: flip paper + the two ink tiers, and flip any multiply
    # overlap to screen so the two bands lighten (not muddy) on a dark surface.
    style_block += os_dark_style()

    # ---- assemble --------------------------------------------------------- #
    parts.append("<defs>" + "".join(defs) + "</defs>")
    if style_block:
        parts.append("<style>" + style_block + "</style>")
    parts.extend(grid)
    parts.extend(band_group)
    parts.extend(lines)
    parts.extend(markers)
    parts.extend(ax_labels)
    parts.extend(axis_bits)
    parts.extend(end_labels)
    parts.extend(legend)
    parts.extend(tips)
    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_difference-chart",
        description="Write the house-style difference-chart SVG example.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--seed", type=int, default=7, help="Random seed for the sample data."
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the figure (default: self-contained).",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal",
            "high-contrast",
            "monochrome",
            "deuteranopia",
            "protanopia",
            "tritanopia",
        ),
        default="universal",
        help="Palette accessibility level (default: universal, the CVD-safe standard).",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to disk."""
    args = _build_parser().parse_args(argv)
    data = _sample_revenue(seed=args.seed)
    svg = build_svg(data, mode=args.mode, accessibility=args.accessibility)
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

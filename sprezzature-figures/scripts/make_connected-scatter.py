#!/usr/bin/env python3
"""
make_connected-scatter — a time-ordered connected scatter as hand-authored SVG.

A **connected scatter** plots one variable against another and joins the
points in time order, turning a two-variable relationship into a single
travelled path. Unlike two separate time series, it shows the *joint*
trajectory: when the line doubles back on itself the two variables have
decoupled, and that hook is the whole story. It reads better than a
grouped line chart because the reader follows one thread through the
(x, y) plane instead of mentally cross-referencing two axes over time.

This generator builds the SVG by hand (no matplotlib / seaborn / plotly,
no Vega) so the smooth path, the direction arrowheads riding the line,
the year labels placed only at inflections, and the emphasised
start / end markers are all under our control. It matches the sprezzature-*
house style: Roboto, the Apple-ish palette, rounded corners, ink
``#1D1D1F``, secondary ``#6E6E73``, white background.

The scenario is the **United Kingdom's carbon decoupling**: carbon-dioxide
emissions per person (vertical) against economic output per person
(horizontal), one point per five years from 1990 to 2022. The path first
climbs to the right, then curls back hard to the left while still moving
up the income axis — the economy keeps growing while emissions fall by
nearly half. That left-turning hook is the defining mark of the chart:
growth and carbon, once locked together, have come apart. Figures are
rounded from the public record and illustrative.

The figure is **static** — a connected scatter shows the whole trajectory
in one still, and animating the pen along the path would only re-tell what
the arrowheads and year labels already say. Each waypoint carries a native
``<title>`` tooltip and a :hover / :focus enlargement; no JavaScript.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/connected-scatter.svg``.

Usage
-----
::

    python make_connected-scatter.py            # writes next to the skill
    python make_connected-scatter.py --out /tmp/connected-scatter.svg

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# House-style palette + the shared XML escaper live alongside in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import load_palette, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402


# ------------------------------------------------------------------
# Communicative illustrative data
# ------------------------------------------------------------------
#: One waypoint every five years. ``gdp`` is gross-domestic-product per
#: person in thousands of constant US dollars (the horizontal axis);
#: ``co2`` is carbon-dioxide emissions per person in tonnes (the vertical
#: axis). The pairing rises together through the 1990s, plateaus, then
#: the emissions fall steeply after 2005 while income keeps climbing — the
#: shape that makes "decoupling" visible. ``label`` flags the waypoints
#: worth naming; ``side`` steers each visible label clear of the path.
POINTS: List[Dict[str, Any]] = [
    {"year": 1990, "gdp": 28.0, "co2": 10.0, "label": True,  "side": "left"},
    {"year": 1995, "gdp": 30.2, "co2": 10.4, "label": False, "side": "left"},
    {"year": 2000, "gdp": 34.6, "co2": 10.5, "label": True,  "side": "top"},
    {"year": 2005, "gdp": 38.4, "co2": 10.0, "label": False, "side": "right"},
    {"year": 2010, "gdp": 39.0, "co2": 8.4,  "label": True,  "side": "right"},
    {"year": 2015, "gdp": 42.1, "co2": 6.5,  "label": False, "side": "right"},
    {"year": 2019, "gdp": 45.3, "co2": 5.4,  "label": True,  "side": "right"},
    {"year": 2022, "gdp": 46.6, "co2": 4.7,  "label": True,  "side": "right"},
]


# A cubic-Bezier segment is four control points: start, two handles, end.
BezierSeg = Tuple[
    Tuple[float, float],
    Tuple[float, float],
    Tuple[float, float],
    Tuple[float, float],
]


def catmull_rom_segments(
    pts: List[Tuple[float, float]],
    tension: float = 0.5,
) -> List[BezierSeg]:
    """Return the cubic-Bezier segments of a Catmull-Rom spline through ``pts``.

    Converts a Catmull-Rom spline (which passes *through* every control
    point, unlike a plain Bezier) into the cubic-Bezier segments that SVG
    understands. Returning the segments (not just the ``d`` string) lets the
    caller both draw the path *and* sample true on-curve positions and
    tangents from the very same geometry — so the direction arrowheads ride
    exactly the line that is drawn, never a straight chord beside it.

    Parameters
    ----------
    pts : list of tuple of float
        The waypoint pixel coordinates, in travel (time) order.
    tension : float, optional
        Catmull-Rom tension in ``[0, 1]``; ``0.5`` is the classic
        centripetal-ish feel used here. Lower is loopier, higher is
        straighter.

    Returns
    -------
    list of BezierSeg
        One ``(p0, c1, c2, p1)`` control-point tuple per span between
        consecutive waypoints.
    """
    segs: List[BezierSeg] = []
    n = len(pts)
    if n < 2:
        return segs
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[0]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[n - 1]
        # Catmull-Rom -> Bezier control points, scaled by the tension.
        c1 = (
            p1[0] + (p2[0] - p0[0]) / 6.0 * (tension * 2),
            p1[1] + (p2[1] - p0[1]) / 6.0 * (tension * 2),
        )
        c2 = (
            p2[0] - (p3[0] - p1[0]) / 6.0 * (tension * 2),
            p2[1] - (p3[1] - p1[1]) / 6.0 * (tension * 2),
        )
        segs.append((p1, c1, c2, p2))
    return segs


def segments_to_path(segs: List[BezierSeg]) -> str:
    """Return the SVG path ``d`` for a list of cubic-Bezier segments."""
    if not segs:
        return ""
    p0 = segs[0][0]
    d = [f"M {p0[0]:.2f} {p0[1]:.2f}"]
    for _, c1, c2, p1 in segs:
        d.append(
            f"C {c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} "
            f"{p1[0]:.2f} {p1[1]:.2f}"
        )
    return " ".join(d)


def _bezier_point(seg: BezierSeg, t: float) -> Tuple[float, float]:
    """Return the point at parameter ``t`` in ``[0, 1]`` on a cubic-Bezier."""
    p0, c1, c2, p1 = seg
    mt = 1.0 - t
    a = mt * mt * mt
    b = 3.0 * mt * mt * t
    c = 3.0 * mt * t * t
    d = t * t * t
    return (
        a * p0[0] + b * c1[0] + c * c2[0] + d * p1[0],
        a * p0[1] + b * c1[1] + c * c2[1] + d * p1[1],
    )


def _bezier_tangent(seg: BezierSeg, t: float) -> Tuple[float, float]:
    """Return the (unnormalised) tangent vector at ``t`` on a cubic-Bezier."""
    p0, c1, c2, p1 = seg
    mt = 1.0 - t
    # Derivative of the cubic Bezier w.r.t. t.
    ax = 3.0 * (c1[0] - p0[0])
    ay = 3.0 * (c1[1] - p0[1])
    bx = 3.0 * (c2[0] - c1[0])
    by = 3.0 * (c2[1] - c1[1])
    cx = 3.0 * (p1[0] - c2[0])
    cy = 3.0 * (p1[1] - c2[1])
    return (
        mt * mt * ax + 2.0 * mt * t * bx + t * t * cx,
        mt * mt * ay + 2.0 * mt * t * by + t * t * cy,
    )


def sample_curve(
    segs: List[BezierSeg],
    per_seg: int = 24,
) -> List[Tuple[float, float, float]]:
    """Densely sample a Bezier polyline as ``(x, y, cumulative_arc_length)``.

    Walks every segment at ``per_seg`` parameter steps and accumulates the
    straight-line distance between successive samples, giving a fine polyline
    approximation of the drawn curve plus its running arc length. The caller
    uses this to place arrowheads at *even distances along the actual line*.

    Parameters
    ----------
    segs : list of BezierSeg
        The Bezier segments of the drawn path.
    per_seg : int, optional
        Samples per segment; higher is smoother arc-length spacing.

    Returns
    -------
    list of tuple of float
        ``(x, y, s)`` samples where ``s`` is cumulative arc length in pixels.
    """
    out: List[Tuple[float, float, float]] = []
    s = 0.0
    prev: Tuple[float, float] | None = None
    for si, seg in enumerate(segs):
        # Skip t=0 on later segments to avoid duplicating the shared waypoint.
        t_start = 0 if si == 0 else 1
        for k in range(t_start, per_seg + 1):
            t = k / per_seg
            x, y = _bezier_point(seg, t)
            if prev is not None:
                s += math.hypot(x - prev[0], y - prev[1])
            out.append((x, y, s))
            prev = (x, y)
    return out


def curve_point_tangent(
    segs: List[BezierSeg],
    target_s: float,
    samples: List[Tuple[float, float, float]],
) -> Tuple[float, float, float]:
    """Return ``(x, y, angle)`` on the curve at arc length ``target_s``.

    Finds the sample bracketing ``target_s``, locates the segment/parameter
    there, and reads the analytic tangent so the arrowhead is oriented to the
    real direction of travel at that on-curve point.

    Parameters
    ----------
    segs : list of BezierSeg
        The Bezier segments of the drawn path.
    target_s : float
        Desired arc length from the start, in pixels.
    samples : list of tuple of float
        The output of :func:`sample_curve`.

    Returns
    -------
    tuple of float
        ``(x, y, angle)`` with ``angle`` in radians (screen space, y-down).
    """
    total = samples[-1][2]
    target_s = max(0.0, min(target_s, total))
    # Locate the bracketing samples for position...
    for i in range(1, len(samples)):
        if samples[i][2] >= target_s:
            x0, y0, s0 = samples[i - 1]
            x1, y1, s1 = samples[i]
            f = 0.0 if s1 == s0 else (target_s - s0) / (s1 - s0)
            x = x0 + (x1 - x0) * f
            y = y0 + (y1 - y0) * f
            break
    else:
        x, y, _ = samples[-1]
    # ...and read the analytic tangent from whichever segment owns this arc
    # length (proportional to per-segment length is close enough for spacing;
    # here we recover it by re-walking cumulative segment lengths).
    seg_index, seg_t = _segment_param_at(segs, target_s)
    tx, ty = _bezier_tangent(segs[seg_index], seg_t)
    return x, y, math.atan2(ty, tx)


def _segment_param_at(
    segs: List[BezierSeg],
    target_s: float,
) -> Tuple[int, float]:
    """Return ``(segment_index, t)`` on the curve at arc length ``target_s``."""
    # Per-segment arc length via a light local sampling.
    lengths: List[float] = []
    for seg in segs:
        acc = 0.0
        prev = _bezier_point(seg, 0.0)
        steps = 16
        for k in range(1, steps + 1):
            cur = _bezier_point(seg, k / steps)
            acc += math.hypot(cur[0] - prev[0], cur[1] - prev[1])
            prev = cur
        lengths.append(acc)
    total = sum(lengths)
    target_s = max(0.0, min(target_s, total))
    run = 0.0
    for i, seg_len in enumerate(lengths):
        if run + seg_len >= target_s or i == len(lengths) - 1:
            local = 0.0 if seg_len == 0 else (target_s - run) / seg_len
            return i, max(0.0, min(1.0, local))
        run += seg_len
    return len(segs) - 1, 1.0


def arrowhead(
    x: float,
    y: float,
    angle: float,
    size: float,
    fill: str,
) -> str:
    """Return a small filled triangle centred on ``(x, y)`` along ``angle``.

    The point ``(x, y)`` is a location *on the curve*; the triangle is built
    so its body straddles that point (tip half a length ahead, base half a
    length behind), which keeps every arrowhead sitting cleanly on the drawn
    line instead of floating off the tip. Drawn as a flat, solid triangle
    (no stroke, no halo) so a reader sees the direction of travel without any
    chart-junk ring. The two base corners are lightly notched toward the
    centre so the glyph reads as a crisp chevron.

    Parameters
    ----------
    x, y : float
        A point on the curve the arrowhead is centred on, in user-space
        pixels.
    angle : float
        Direction of travel in radians (screen space, y-down).
    size : float
        Overall length of the arrowhead from tip to base, in pixels.
    fill : str
        Fill colour hex.

    Returns
    -------
    str
        An SVG ``<path>`` element for the triangle.
    """
    ca, sa = math.cos(angle), math.sin(angle)
    half = size / 2.0
    # Tip half a length ahead of the on-curve point; base corners half a
    # length behind, splayed to ~0.62·size half-width for a clean chevron.
    tx = x + half * ca
    ty = y + half * sa
    hw = 0.62 * size            # half-width of the base
    # Perpendicular unit vector (rotate the tangent by 90 degrees).
    px_, py_ = -sa, ca
    b1x = x - half * ca + hw * px_
    b1y = y - half * sa + hw * py_
    b2x = x - half * ca - hw * px_
    b2y = y - half * sa - hw * py_
    # A thin white keyline lifts the chevron off the same-hued stroke so it
    # reads as a crisp direction glyph, not a bulge — a bright keyline, never
    # a dark ring.
    return (
        f'<path d="M {tx:.2f} {ty:.2f} L {b1x:.2f} {b1y:.2f} '
        f'L {b2x:.2f} {b2y:.2f} Z" fill="{fill}" stroke="#FFFFFF" '
        f'stroke-width="2" stroke-linejoin="round"/>'
    )


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full connected-scatter SVG string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level threaded into :func:`_style.load_palette`
        (``"universal"``, ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` or ``"tritanopia"``). Defaults to
        ``"universal"``, the colour-vision-safe standard.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    palette: Dict[str, str] = load_palette(accessibility)
    # A single warm-to-cool sweep along the path: the early "coupled"
    # years are Orange (heat / carbon), the recent "decoupled" years are
    # Teal / Blue (cool / clean). One hue channel carries time, so the
    # eye reads direction from colour as well as from the arrowheads.
    warm = palette.get("Orange", "#FF9500")
    cool = palette.get("Blue", "#007AFF")
    # Endpoint pills use the house diverging pair, Red (start) vs Blue (end),
    # never Red vs Green: under deuteranopia and in greyscale a red/green pair
    # collapses, whereas red↔blue stays legible. Blue also matches the cool end
    # of the path gradient, so the "now" dot belongs to the curve it caps.
    start_col = palette.get("Red", "#FF3B30")
    end_col = cool
    ink = "#1D1D1F"
    secondary = "#6E6E73"
    band = "#F5F5F7"

    rows = list(POINTS)

    # --- canvas geometry -----------------------------------------
    width = 1280
    height = 1000
    m_left = 120
    m_right = 96
    m_top = 236
    m_bottom = 132
    plot_x = m_left
    plot_y = m_top
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    # --- axis ranges (with headroom so nothing clips) ------------
    x_min, x_max = 26.0, 49.0
    y_min, y_max = 4.0, 11.4
    x_ticks = [30, 35, 40, 45]
    y_ticks = [4, 6, 8, 10]

    def sx(v: float) -> float:
        """Map GDP per person (thousands USD) to an x pixel coordinate."""
        return plot_x + (v - x_min) / (x_max - x_min) * plot_w

    def sy(v: float) -> float:
        """Map CO2 per person (tonnes) to a y pixel coordinate (y-down)."""
        return plot_y + (y_max - v) / (y_max - y_min) * plot_h

    px = [(sx(float(r["gdp"])), sy(float(r["co2"]))) for r in rows]

    # Aggregate numbers for the takeaway copy.
    co2_first = float(rows[0]["co2"])
    co2_last = float(rows[-1]["co2"])
    gdp_first = float(rows[0]["gdp"])
    gdp_last = float(rows[-1]["gdp"])
    co2_drop = round(100.0 * (co2_first - co2_last) / co2_first)
    gdp_rise = round(100.0 * (gdp_last - gdp_first) / gdp_first)

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    parts.append(svg_open(width, height, "cs-title", "cs-desc"))
    parts.append(
        '<title id="cs-title">The United Kingdom grew its economy while '
        'cutting carbon per person nearly in half</title>'
    )
    parts.append(
        f'<desc id="cs-desc">Connected scatter tracing carbon-dioxide '
        f'emissions per person (vertical, tonnes) against economic output '
        f'per person (horizontal, thousands of US dollars) for the United '
        f'Kingdom, one point every five years from {rows[0]["year"]} to '
        f'{rows[-1]["year"]}. The path first moves right as income rises, '
        f'then turns sharply left and downward: output per person climbed '
        f'about {gdp_rise}% while emissions per person fell about '
        f'{co2_drop}%, from {co2_first:.1f} to {co2_last:.1f} tonnes. The '
        f'left-turning hook shows growth and carbon decoupling. '
        f'Illustrative figures.</desc>'
    )

    # Static figure: hover / focus enlargement only, no motion to guard.
    # prefers-contrast: this is a PERCEPTUAL figure — the path carries time in a
    # warm->cool colour sweep (a continuous gradient) and its markers/arrowheads
    # ride that ramp, so the ramp is left untouched. We only STRENGTHEN STRUCTURE:
    # deepen the secondary ink toward the primary ink and darken + thicken the
    # light gridline band so the plot frame reads harder for a low-vision reader
    # without re-tuning the path colours. Additive + media-gated, so the default
    # render is byte-for-byte unchanged.
    contrast = (
        "@media (prefers-contrast: more){"
        f'[fill="{secondary}"]{{fill:{ink};}}'
        f'[stroke="{band}"]{{stroke:#8A8A8E;stroke-width:2;}}'
        "}"
    )
    parts.append(
        "<style>"
        ".wp{cursor:pointer}"
        ".wp .halo{opacity:0}"
        ".wp:hover .halo,.wp:focus .halo{opacity:1}"
        ".wp:focus{outline:none}"
        + contrast
        # Additive dark mode. A marker's end-label is white (fill="#FFFFFF") and
        # sits on its data-hue dot, so we do not invert #FFFFFF globally; the
        # paper flips via its own .paper class instead. The light band gridlines
        # are strokes the ink map misses, so darken them here.
        + os_dark_style(
            ink_map={"#1D1D1F": "#F2F2F7", "#6E6E73": "#9C9CA3"},
            extra='.paper{fill:#0B0B0C;}[stroke="%s"]{stroke:#2A2A2C;}' % band,
        )
        + "</style>"
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect class="paper" width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="92" font-size="42" font-weight="700" '
        f'fill="{ink}">Growth went one way, carbon the other</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="140" font-size="24" fill="{secondary}">'
        f'United Kingdom, {rows[0]["year"]}–{rows[-1]["year"]}: output '
        f'per person up ~{gdp_rise}% while carbon per person fell ~{co2_drop}% '
        f'· illustrative</text>'
    )

    # --- legend: what the two emphasised markers mean ------------
    leg_y = 182
    lr = 11.0
    parts.append(
        f'<circle cx="{m_left + lr:.1f}" cy="{leg_y:.1f}" r="{lr:.1f}" '
        f'fill="{start_col}"/>'
    )
    parts.append(
        f'<text x="{m_left + 2 * lr + 12:.1f}" y="{leg_y + 7:.1f}" '
        f'font-size="22" fill="{ink}">Start {rows[0]["year"]}</text>'
    )
    leg_x2 = m_left + 210
    parts.append(
        f'<circle cx="{leg_x2 + lr:.1f}" cy="{leg_y:.1f}" r="{lr:.1f}" '
        f'fill="{end_col}"/>'
    )
    parts.append(
        f'<text x="{leg_x2 + 2 * lr + 12:.1f}" y="{leg_y + 7:.1f}" '
        f'font-size="22" fill="{ink}">Now {rows[-1]["year"]}</text>'
    )
    # A short "direction of time" cue with an arrow glyph.
    dir_x = leg_x2 + 260
    parts.append(
        f'<text x="{dir_x:.1f}" y="{leg_y + 7:.1f}" font-size="22" '
        f'fill="{secondary}">Arrows follow time →</text>'
    )

    # --- gridlines (very light) ----------------------------------
    for t in x_ticks:
        gx = sx(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{plot_y:.1f}" x2="{gx:.1f}" '
            f'y2="{plot_y + plot_h:.1f}" stroke="{band}" stroke-width="1.6"/>'
        )
    for t in y_ticks:
        gy = sy(t)
        parts.append(
            f'<line x1="{plot_x:.1f}" y1="{gy:.1f}" x2="{plot_x + plot_w:.1f}" '
            f'y2="{gy:.1f}" stroke="{band}" stroke-width="1.6"/>'
        )

    # --- axes (L-shaped, ink) ------------------------------------
    ax_bottom = plot_y + plot_h
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{ax_bottom:.1f}" '
        f'x2="{plot_x + plot_w:.1f}" y2="{ax_bottom:.1f}" '
        f'stroke="{ink}" stroke-width="1.6"/>'
    )
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{plot_y:.1f}" x2="{plot_x:.1f}" '
        f'y2="{ax_bottom:.1f}" stroke="{ink}" stroke-width="1.6"/>'
    )
    for t in x_ticks:
        gx = sx(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{ax_bottom:.1f}" x2="{gx:.1f}" '
            f'y2="{ax_bottom + 7:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="{ax_bottom + 32:.1f}" font-size="20" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">${t}k</text>'
        )
    for t in y_ticks:
        gy = sy(t)
        parts.append(
            f'<line x1="{plot_x - 7:.1f}" y1="{gy:.1f}" x2="{plot_x:.1f}" '
            f'y2="{gy:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{plot_x - 16:.1f}" y="{gy + 7:.1f}" font-size="20" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="end">{t}</text>'
        )

    # --- axis titles ---------------------------------------------
    parts.append(
        f'<text x="{plot_x + plot_w / 2:.1f}" y="{ax_bottom + 74:.1f}" '
        f'font-size="23" fill="{ink}" text-anchor="middle">'
        f'Economic output per person (thousands of US dollars) '
        f'→ richer</text>'
    )
    ytitle_x = 46
    ytitle_y = plot_y + plot_h / 2
    parts.append(
        f'<text x="{ytitle_x:.1f}" y="{ytitle_y:.1f}" font-size="23" '
        f'fill="{ink}" text-anchor="middle" '
        f'transform="rotate(-90 {ytitle_x:.1f} {ytitle_y:.1f})">'
        f'Carbon per person (tonnes) ↑ dirtier</text>'
    )

    # --- the connecting path -------------------------------------
    # Draw a soft white under-stroke first so the coloured path stays
    # crisp where it crosses a gridline; then the coloured path on top.
    segs = catmull_rom_segments(px, tension=0.5)
    d = segments_to_path(segs)
    parts.append(
        f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="12" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    # Two overlaid strokes with a linear gradient give the warm->cool
    # time sweep without per-segment recolouring seams.
    parts.append(
        '<defs><linearGradient id="csgrad" gradientUnits="userSpaceOnUse" '
        f'x1="{px[0][0]:.1f}" y1="{px[0][1]:.1f}" '
        f'x2="{px[-1][0]:.1f}" y2="{px[-1][1]:.1f}">'
        f'<stop offset="0" stop-color="{warm}"/>'
        f'<stop offset="0.55" stop-color="{palette.get("Mint", "#00C7BE")}"/>'
        f'<stop offset="1" stop-color="{cool}"/>'
        '</linearGradient></defs>'
    )
    parts.append(
        f'<path d="{d}" fill="none" stroke="url(#csgrad)" stroke-width="6" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # --- direction arrowheads riding the line --------------------
    # Place a fixed number of arrowheads at *even arc-length intervals along
    # the drawn curve*, each oriented by the curve's true tangent there, so
    # every glyph sits on the line pointing in the direction of travel. Both
    # position and angle come from the same Bezier geometry that is stroked,
    # so no arrowhead floats off a chord. Interior placement (a margin at
    # each end) keeps heads off the emphasised Start / End markers and their
    # pill labels.
    samples = sample_curve(segs, per_seg=28)
    total_len = samples[-1][2]
    n_arrows = 6
    head_size = 17.0
    margin = 0.085          # skip this fraction of the length at each end
    # Arc-length position of every waypoint (a segment boundary), used to
    # repel arrowheads away from the dots so glyphs never overlap a marker.
    seg_lengths: List[float] = []
    for seg in segs:
        acc = 0.0
        prev_pt = _bezier_point(seg, 0.0)
        for kk in range(1, 17):
            cur = _bezier_point(seg, kk / 16)
            acc += math.hypot(cur[0] - prev_pt[0], cur[1] - prev_pt[1])
            prev_pt = cur
        seg_lengths.append(acc)
    waypoint_s: List[float] = [0.0]
    for seg_len in seg_lengths:
        waypoint_s.append(waypoint_s[-1] + seg_len)
    # Rescale approximate segment lengths onto the true sampled total.
    scale = total_len / waypoint_s[-1] if waypoint_s[-1] else 1.0
    waypoint_s = [s * scale for s in waypoint_s]
    clear = 26.0            # keep this many px of arc length clear of any dot
    for k in range(n_arrows):
        # Evenly spaced fractions within [margin, 1 - margin].
        frac = margin + (1.0 - 2.0 * margin) * (k + 0.5) / n_arrows
        target_s = frac * total_len
        # Nudge away from the nearest waypoint if we landed on top of a dot.
        nearest = min(waypoint_s, key=lambda ws: abs(ws - target_s))
        gap = target_s - nearest
        if abs(gap) < clear:
            target_s = nearest + (clear if gap >= 0 else -clear)
            target_s = max(margin * total_len, min((1 - margin) * total_len, target_s))
        ax, ay, ang = curve_point_tangent(segs, target_s, samples)
        # Warm->cool along the journey, matching the path gradient.
        head_col = cool if target_s / total_len > 0.5 else warm
        parts.append(arrowhead(ax, ay, ang, head_size, head_col))

    # --- waypoint markers + year labels --------------------------
    for i, r in enumerate(rows):
        cx, cy = px[i]
        year = int(r["year"])
        is_start = i == 0
        is_end = i == len(rows) - 1
        gdp = float(r["gdp"])
        co2 = float(r["co2"])

        tip = (
            f'{year}: {gdp:.1f}k US dollars per person, '
            f'{co2:.1f} tonnes CO2 per person'
        )

        parts.append(
            f'<g class="wp" tabindex="0" role="img" aria-label="{xml_escape(tip)}">'
        )
        parts.append(f"<title>{xml_escape(tip)}</title>")

        # Hover halo (hidden by default, revealed on hover/focus).
        parts.append(
            f'<circle class="halo" cx="{cx:.1f}" cy="{cy:.1f}" r="22" '
            f'fill="{ink}" fill-opacity="0.08"/>'
        )

        if is_start:
            r_dot = 13.0
            fill = start_col
        elif is_end:
            r_dot = 13.0
            fill = end_col
        else:
            r_dot = 8.5
            # Interior dots track the path's warm->cool sweep.
            frac = i / (len(rows) - 1)
            fill = warm if frac < 0.5 else cool

        # White keyline so a dot stays crisp on the coloured path — a
        # bright keyline, never a dark ring.
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r_dot:.1f}" '
            f'fill="{fill}" stroke="#FFFFFF" stroke-width="2.5"/>'
        )
        parts.append("</g>")

    # --- year labels at the named waypoints (drawn last, on top) --
    # Placed on the ``side`` recorded in the data so labels sit clear of
    # the path. Start / end get a filled pill in their marker colour;
    # interior named years get plain ink text.
    for i, r in enumerate(rows):
        if not bool(r["label"]):
            continue
        cx, cy = px[i]
        year = int(r["year"])
        side = str(r["side"])
        is_start = i == 0
        is_end = i == len(rows) - 1

        if side == "left":
            tx = cx - 22
            anchor = "end"
            ty = cy + 7
        elif side == "top":
            tx = cx
            anchor = "middle"
            ty = cy - 26
        else:
            tx = cx + 22
            anchor = "start"
            ty = cy + 7

        if is_start or is_end:
            # Emphasised year in a soft pill matching the marker hue,
            # white text — legible, no halo, no dark ring.
            fill = start_col if is_start else end_col
            txt = f"{year}"
            pill_w = 74.0
            pill_h = 34.0
            if anchor == "end":
                rx0 = tx - pill_w
                text_x = tx - pill_w / 2
            else:
                rx0 = tx
                text_x = tx + pill_w / 2
            parts.append(
                f'<rect x="{rx0:.1f}" y="{cy - pill_h / 2:.1f}" '
                f'width="{pill_w:.1f}" height="{pill_h:.1f}" rx="17" '
                f'fill="{fill}"/>'
            )
            parts.append(
                f'<text x="{text_x:.1f}" y="{cy + 7:.1f}" font-size="22" '
                f'font-weight="700" fill="#FFFFFF" text-anchor="middle">'
                f'{txt}</text>'
            )
        else:
            parts.append(
                f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="21" '
                f'font-weight="600" fill="{ink}" text-anchor="{anchor}">'
                f'{year}</text>'
            )

    # --- an in-plot annotation on the decoupling turn ------------
    # Point to the elbow (around 2010, where the path pivots from flat to
    # steeply falling) so the reader knows which feature carries the
    # headline: this is where carbon starts dropping fast.
    turn_x, turn_y = px[4]  # the 2010 waypoint
    note_x = turn_x + 132
    note_y = turn_y + 78
    parts.append(
        f'<text x="{note_x:.1f}" y="{note_y:.1f}" font-size="21" '
        f'font-weight="600" fill="{secondary}">here the path pivots down:</text>'
    )
    parts.append(
        f'<text x="{note_x:.1f}" y="{note_y + 26:.1f}" font-size="21" '
        f'font-weight="600" fill="{secondary}">growth without the carbon</text>'
    )
    # A thin connector from the note up-left to the curve just below the
    # 2010 dot — routed clear of the "2010" label so nothing overlaps.
    aim_x, aim_y = px[4][0] + 24, px[4][1] + 40
    parts.append(
        f'<line x1="{note_x - 10:.1f}" y1="{note_y - 18:.1f}" '
        f'x2="{aim_x:.1f}" y2="{aim_y:.1f}" '
        f'stroke="{secondary}" stroke-width="1.4" stroke-dasharray="3 5"/>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the connected-scatter SVG to the canonical assets path (or --out)."""
    render_cli(
        __file__, "connected-scatter", build_svg,
        description="Render the connected-scatter SVG.",
    )


if __name__ == "__main__":
    main()

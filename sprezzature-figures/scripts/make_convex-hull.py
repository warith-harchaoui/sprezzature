#!/usr/bin/env python3
"""
make_convex-hull — publication-quality convex-hull-over-clusters figure as hand-authored SVG.

A convex hull over clusters answers one question at a glance: *do the
groups actually separate in this feature space, or do they blur into each
other?* A scatter alone leaves the eye to guess the group boundaries; a
translucent hull drawn around each cluster names the territory each group
occupies, so overlap (or the lack of it) is immediate. This is the
Observable Plot ``hull`` mark and the ggforce ``geom_mark_hull`` idea,
pushed to a higher finish.

Here the feature space is a customer base: monthly spend on one axis,
weekly active days on the other, coloured by the segment a clustering
model assigned (occasional, regular, power users). The takeaway is that
the three segments carve out clearly distinct, barely-touching regions —
the value/engagement plane really does split into three.

Vega-Lite has no hull primitive, so the figure is hand-authored SVG. The
hull is computed offline with a pure-Python **Graham scan** (no scipy, no
numpy geometry): sort by polar angle about the lowest point, then walk the
stack keeping only left turns. To beat the reference libraries on looks,
each hull is then (1) offset outward by a fixed padding so the boundary
breathes around its points rather than clipping them, and (2) drawn with
**rounded corners** via a quadratic-Bézier corner-cut, so the cluster
regions read as soft, map-like territories instead of hard angular
polygons. Fills are translucent same-hue washes; points sit on top with a
crisp white keyline so no dot ever melts into its hull.

House style follows ``_style.py``: Roboto type, the Apple-system
categorical palette, ink ``#1D1D1F`` on white, a start-anchored takeaway
title plus a one-line subtitle, and a clean cluster legend. There is no
colour-on-colour muddle (hull washes stay light, points stay saturated),
no dark ring around legend disks, and no grounding shadow.

Interaction (no JavaScript): every point carries a native ``<title>``
tooltip, and a pure-CSS ``:hover`` / ``:focus-within`` rule lifts the
hovered segment (its hull and points) to full strength while dimming the
others, so a reader can isolate one segment at a time. The chart is fully
legible when static, so ``animated`` is false and ``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/convex-hull.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from xml.sax.saxutils import escape

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _labels import label_cell  # noqa: E402
from _style import leveled_colors, load_palette, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _render import render_cli  # noqa: E402
from _svg import svg_open  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1280
HEIGHT = 1040
INK = "#1D1D1F"            # primary text
SUBINK = "#6E6E73"         # secondary text
BG = "#FFFFFF"
AXIS = "#D2D2D7"           # axis + gridline grey (light, unobtrusive)

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

# Plot frame in canvas pixels. Generous left/bottom gutters hold the axis
# titles; top gutter holds title + subtitle + legend; right gutter gives
# the rightmost hull room to breathe so nothing clips.
PLOT_X0 = 132.0
PLOT_X1 = WIDTH - 96.0
PLOT_Y0 = 250.0            # top edge of the plotting area (below the legend)
PLOT_Y1 = HEIGHT - 132.0  # bottom edge (above the axis title)

# Data windows. Monthly spend in dollars (x); weekly active days (y).
X_MIN, X_MAX = 0.0, 260.0
# Y ceiling sits above the highest cluster (power users peak near 7 active
# days) so every hull has clear sky above it for its floating name chip.
Y_MIN, Y_MAX = 0.0, 8.2

# Hull cosmetics.
HULL_PAD = 22.0           # px the hull is pushed out past its points
CORNER = 18.0             # px corner-rounding radius on the hull polygon
HULL_FILL_OPACITY = 0.14  # translucent wash so hulls never fight the points
HULL_STROKE_OPACITY = 0.9

# ------------------------------------------------------------------
# The story (illustrative but plausible, in the shape of a customer
# clustering): three segments a model separated in the spend/engagement
# plane. Occasional users spend little and log in a day or two a week;
# regulars sit in the productive middle; power users spend the most and
# are on the product nearly every day. Colour marks the segment so the eye
# reads three territories before it reads any single customer.
# ------------------------------------------------------------------
SEGMENTS: List[str] = ["Occasional", "Regular", "Power users"]

# Cluster generation parameters: (centre_spend, centre_days, spread_spend,
# spread_days, n_points). Chosen so the three clouds separate cleanly with
# only a thin no-man's-land between neighbours — the case a hull is meant
# to make visible.
_CLUSTER_PARAMS: Dict[str, Tuple[float, float, float, float, int]] = {
    "Occasional":  (40.0,  1.5, 18.0, 0.6, 34),
    "Regular":     (120.0, 3.8, 24.0, 0.6, 40),
    "Power users": (208.0, 6.0, 22.0, 0.55, 30),
}

def _segment_colors(accessibility: str = "universal") -> Dict[str, str]:
    """Return the per-segment hue map at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`;
        ``"universal"`` (default) is the identity.

    Returns
    -------
    dict of str to str
        ``{segment_name: "#RRGGBB"}``.
    """
    palette = load_palette(accessibility)
    return {
        "Occasional":  palette.get("Blue", "#007AFF"),
        "Regular":     palette.get("Orange", "#FF9500"),
        "Power users": palette.get("Purple", "#AF52DE"),
    }


PALETTE = load_palette()
SEGMENT_COLOR: Dict[str, str] = _segment_colors()


# ------------------------------------------------------------------
# Data
# ------------------------------------------------------------------
def make_data(seed: int = 11) -> Dict[str, List[Tuple[float, float]]]:
    """Sample three plausible customer segments in the spend/engagement plane.

    Each segment is a Gaussian blob around its centre, clipped to the data
    window so no point falls off-scale. A fixed seed makes the committed
    SVG byte-reproducible.

    Parameters
    ----------
    seed : int, optional
        NumPy random seed. Default 11.

    Returns
    -------
    dict of str to list of tuple of float
        ``{segment_name: [(spend, days), ...]}`` in data units.
    """
    rng = np.random.default_rng(seed)
    out: Dict[str, List[Tuple[float, float]]] = {}
    for name in SEGMENTS:
        cx, cy, sx, sy, n = _CLUSTER_PARAMS[name]
        xs = np.clip(rng.normal(cx, sx, n), X_MIN + 4, X_MAX - 4)
        ys = np.clip(rng.normal(cy, sy, n), Y_MIN + 0.15, Y_MAX - 0.2)
        out[name] = [(float(x), float(y)) for x, y in zip(xs, ys)]
    return out


# ------------------------------------------------------------------
# Coordinate transform (data -> canvas pixels)
# ------------------------------------------------------------------
def _sx(x: float) -> float:
    """Map a spend value to a canvas x-pixel."""
    return PLOT_X0 + (x - X_MIN) / (X_MAX - X_MIN) * (PLOT_X1 - PLOT_X0)


def _sy(y: float) -> float:
    """Map an active-days value to a canvas y-pixel (y-axis points up)."""
    return PLOT_Y1 - (y - Y_MIN) / (Y_MAX - Y_MIN) * (PLOT_Y1 - PLOT_Y0)


# ------------------------------------------------------------------
# Graham-scan convex hull (pure Python)
# ------------------------------------------------------------------
def _cross(o: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Return the 2D cross product ``(a - o) x (b - o)``.

    Positive when ``o -> a -> b`` turns counter-clockwise, negative for a
    clockwise turn, zero when collinear. This is the single primitive the
    Graham scan needs to decide which points to keep.

    Parameters
    ----------
    o, a, b : tuple of float
        Three points in the plane.

    Returns
    -------
    float
        The signed area of the parallelogram spanned by ``a - o`` and
        ``b - o``.
    """
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Compute the convex hull of a point set by Graham scan.

    The classic monotone-chain variant: sort the points lexicographically,
    build the lower and upper chains keeping only counter-clockwise turns,
    and concatenate. Runs in ``O(n log n)`` with no external geometry
    library. Returns the hull vertices in counter-clockwise order.

    Parameters
    ----------
    points : list of tuple of float
        Points ``(x, y)`` in canvas pixels.

    Returns
    -------
    list of tuple of float
        The hull vertices, counter-clockwise, without the closing repeat.
        Degenerate inputs (fewer than three unique points) are returned
        as-is.
    """
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    lower: List[Tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: List[Tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    # Drop the last point of each chain (it is the first of the other).
    return lower[:-1] + upper[:-1]


def _offset_hull(
    hull: List[Tuple[float, float]],
    pad: float,
) -> List[Tuple[float, float]]:
    """Push a hull outward by ``pad`` pixels along each vertex's normal.

    Each vertex is moved away from the polygon centroid by ``pad`` pixels.
    Because a convex polygon's centroid is inside it, moving every vertex
    radially outward inflates the hull uniformly, giving the points room to
    breathe inside the boundary rather than sitting on the edge. This is
    the visual polish the reference libraries skip.

    Parameters
    ----------
    hull : list of tuple of float
        Convex hull vertices in order.
    pad : float
        Outward offset in pixels.

    Returns
    -------
    list of tuple of float
        The inflated hull vertices, same order.
    """
    if len(hull) < 3:
        return hull
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)
    out: List[Tuple[float, float]] = []
    for x, y in hull:
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy) or 1.0
        out.append((x + dx / dist * pad, y + dy / dist * pad))
    return out


def _rounded_hull_path(hull: List[Tuple[float, float]], radius: float) -> str:
    """Build an SVG path for a closed polygon with rounded corners.

    Every corner is cut and replaced with a quadratic Bézier: the path
    runs to a point ``radius`` before the corner, then curves through the
    corner to a point ``radius`` after it. The radius is clamped per corner
    to half the shorter adjacent edge so short edges never overshoot. The
    result is a smooth, map-like territory outline — softer and more
    finished than the hard polygon a plain hull draws.

    Parameters
    ----------
    hull : list of tuple of float
        Polygon vertices in order (no closing repeat).
    radius : float
        Nominal corner-rounding radius in pixels.

    Returns
    -------
    str
        An SVG path ``d`` attribute string (closed with ``Z``).
    """
    n = len(hull)
    if n < 3:
        return ""

    def _pt_toward(a: Tuple[float, float], b: Tuple[float, float], r: float) -> Tuple[float, float]:
        """Point ``r`` px from ``a`` along the segment ``a -> b``."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        t = min(r, d / 2.0) / d
        return (a[0] + dx * t, a[1] + dy * t)

    segs: List[str] = []
    for i in range(n):
        prev = hull[(i - 1) % n]
        curr = hull[i]
        nxt = hull[(i + 1) % n]
        p_in = _pt_toward(curr, prev, radius)   # approach point before the corner
        p_out = _pt_toward(curr, nxt, radius)   # departure point after the corner
        if i == 0:
            segs.append(f"M {p_in[0]:.2f} {p_in[1]:.2f}")
        else:
            segs.append(f"L {p_in[0]:.2f} {p_in[1]:.2f}")
        # Quadratic through the true corner rounds it off.
        segs.append(f"Q {curr[0]:.2f} {curr[1]:.2f} {p_out[0]:.2f} {p_out[1]:.2f}")
    segs.append("Z")
    return " ".join(segs)


# ------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------
def _label_anchor(hull_px: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Return a clear anchor point above a hull for its segment label.

    Anchoring to the single topmost vertex lands the label off to one side
    (wherever that vertex happens to be) and often straddles the hull
    boundary. Instead we centre the label horizontally on the hull's
    x-centroid and place it above the hull's overall top edge, so every
    label sits in the clear space directly over the visual middle of its
    cluster — consistent placement across all three segments.

    Parameters
    ----------
    hull_px : list of tuple of float
        Inflated hull vertices in canvas pixels.

    Returns
    -------
    tuple of float
        The ``(x, y)`` anchor: x is the hull centroid, y is the topmost
        (smallest-y) hull point. The caller adds its own vertical gap.
    """
    cx = sum(p[0] for p in hull_px) / len(hull_px)
    top_y = min(p[1] for p in hull_px)
    return (cx, top_y)


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def build_svg(seed: int = 11, mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full convex-hull SVG document as a string.

    Parameters
    ----------
    seed : int, optional
        Seed forwarded to :func:`make_data`. Default 11.
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Controls
        whether the emitted SVG carries its own fullscreen button; the raster
        output is unaffected. Defaults to ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`
        (``"universal"``, ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` or ``"tritanopia"``). The default
        ``"universal"`` is the identity, so the shipped figure is unchanged.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    segment_color = _segment_colors(accessibility)
    data = make_data(seed=seed)

    title_txt = "Three customer segments carve out distinct territory"
    subtitle_txt = (
        "Monthly spend vs. weekly active days, one dot per customer, "
        "hull per model-assigned segment — illustrative data"
    )
    desc_txt = (
        "Scatter plot of customers positioned by monthly spend (horizontal) "
        "and weekly active days (vertical), coloured by the segment a "
        "clustering model assigned. A translucent convex hull is drawn "
        "around each segment's points. The three hulls — occasional, "
        "regular, and power users — sit in clearly separated regions with "
        "only thin gaps between them, so the value and engagement plane "
        "splits cleanly into three. Hover or focus any point to lift its "
        "whole segment and dim the others."
    )

    parts: List[str] = []
    parts.append(svg_open(WIDTH, HEIGHT, "ch-title", "ch-desc", font_family=FONT))
    parts.append(f'<title id="ch-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="ch-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hover/focus a point lifts its whole segment, dims the rest.
    #     Each segment group carries a class; one :has() rule per segment
    #     keeps the hovered segment at full opacity while fading the others.
    seg_slug = {seg: f"s{idx}" for idx, seg in enumerate(SEGMENTS)}
    css: List[str] = [
        ".seg{transition:opacity .18s ease}",
        ".dot:focus{outline:none}",
    ]
    for _seg, slug in seg_slug.items():
        cond = f"#plot:has(.dot.{slug}:is(:hover,:focus))"
        css.append(f"{cond} .seg{{opacity:.2}}")
        css.append(f"{cond} .seg.{slug}{{opacity:1}}")
    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule below lives inside a media query). Under
    # prefers-contrast each segment deepens to its high-contrast hue: the points
    # (fill), the hull keyline (stroke) and the legend disk (fill). The
    # translucent hull WASH is left at its light opacity on purpose — deepening
    # its fill would darken the territory under the points and the venn-style
    # occlusion would swallow the dots. forced-colors is left to the browser
    # default: the three segments already separate by position and carry a name
    # chip over each hull, and a three-hue scatter cannot survive the ~4-colour
    # system palette.
    seg_hc = leveled_colors(segment_color, "high-contrast")
    contrast_rows = "".join(
        f".dot.{seg_slug[seg]}{{fill:{seg_hc[seg]};}}"
        f".hull-{seg_slug[seg]}{{stroke:{seg_hc[seg]};}}"
        f".leg-{seg_slug[seg]}{{fill:{seg_hc[seg]};}}"
        for seg in SEGMENTS
    )
    css.append("@media (prefers-contrast: more){" + contrast_rows + "}")
    # Additive dark mode: flip paper + ink and darken the light axis/gridline
    # grey (a stroke the ink map misses). Translucent hull washes and saturated
    # points (with their white keylines) are data hues, left untouched.
    css.append(os_dark_style(extra='[stroke="%s"]{stroke:#3A3A3C;}' % AXIS))
    parts.append("<style>" + "".join(css) + "</style>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="56" y="76" font-size="37" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="56" y="114" font-size="20" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    # --- segment legend (row below the subtitle) ---
    ly: float = 168
    cursor = 56.0
    for seg in SEGMENTS:
        color = segment_color[seg]
        parts.append(
            f'<circle class="leg-{seg_slug[seg]}" cx="{cursor + 9:.1f}" '
            f'cy="{ly - 6:.1f}" r="9" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{cursor + 26:.1f}" y="{ly:.1f}" text-anchor="start" '
            f'font-size="18" fill="{INK}">{escape(seg)}</text>'
        )
        cursor += 26 + 10.2 * len(seg) + 44

    # --- axes: light gridlines + baseline + tick labels ---
    parts.append('<g id="axes">')

    # X gridlines + labels (spend, $).
    x_ticks = [0, 50, 100, 150, 200, 250]
    for xt in x_ticks:
        px = _sx(float(xt))
        parts.append(
            f'<line x1="{px:.1f}" y1="{PLOT_Y0:.1f}" x2="{px:.1f}" y2="{PLOT_Y1:.1f}" '
            f'stroke="{AXIS}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{PLOT_Y1 + 30:.1f}" text-anchor="middle" '
            f'font-size="15" font-family="{FONT_MONO}" fill="{SUBINK}">${xt}</text>'
        )

    # Y gridlines + labels (weekly active days).
    y_ticks = [0, 1, 2, 3, 4, 5, 6, 7]
    for yt in y_ticks:
        py = _sy(float(yt))
        parts.append(
            f'<line x1="{PLOT_X0:.1f}" y1="{py:.1f}" x2="{PLOT_X1:.1f}" y2="{py:.1f}" '
            f'stroke="{AXIS}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{PLOT_X0 - 16:.1f}" y="{py + 5:.1f}" text-anchor="end" '
            f'font-size="15" font-family="{FONT_MONO}" fill="{SUBINK}">{yt}</text>'
        )

    # Emphasised baseline + left spine (slightly darker than the grid).
    parts.append(
        f'<line x1="{PLOT_X0:.1f}" y1="{PLOT_Y1:.1f}" x2="{PLOT_X1:.1f}" y2="{PLOT_Y1:.1f}" '
        f'stroke="{SUBINK}" stroke-width="1.5"/>'
    )
    parts.append(
        f'<line x1="{PLOT_X0:.1f}" y1="{PLOT_Y0:.1f}" x2="{PLOT_X0:.1f}" y2="{PLOT_Y1:.1f}" '
        f'stroke="{SUBINK}" stroke-width="1.5"/>'
    )

    # Axis titles.
    parts.append(
        f'<text x="{(PLOT_X0 + PLOT_X1) / 2:.1f}" y="{HEIGHT - 54:.1f}" '
        f'text-anchor="middle" font-size="19" font-weight="600" fill="{INK}">'
        f'Average monthly spend</text>'
    )
    ay = (PLOT_Y0 + PLOT_Y1) / 2
    parts.append(
        f'<text x="46" y="{ay:.1f}" text-anchor="middle" font-size="19" '
        f'font-weight="600" fill="{INK}" transform="rotate(-90 46 {ay:.1f})">'
        f'Weekly active days</text>'
    )
    parts.append("</g>")  # /axes

    # --- the plot: hulls first (underneath), then points on top ---
    parts.append('<g id="plot">')

    # Precompute pixel points + inflated rounded hull per segment.
    seg_px: Dict[str, List[Tuple[float, float]]] = {}
    seg_hull_px: Dict[str, List[Tuple[float, float]]] = {}
    for seg in SEGMENTS:
        pxs = [(_sx(x), _sy(y)) for x, y in data[seg]]
        seg_px[seg] = pxs
        hull = convex_hull(pxs)
        seg_hull_px[seg] = _offset_hull(hull, HULL_PAD)

    # Hull washes (drawn under the points). One translucent same-hue fill
    # plus a stronger same-hue keyline so the boundary reads without a
    # dark ring.
    for seg in SEGMENTS:
        color = segment_color[seg]
        slug = seg_slug[seg]
        path_d = _rounded_hull_path(seg_hull_px[seg], CORNER)
        if path_d:
            parts.append(
                f'<g class="seg {slug}"><path class="hull-{slug}" d="{path_d}" '
                f'fill="{color}" '
                f'fill-opacity="{HULL_FILL_OPACITY}" stroke="{color}" '
                f'stroke-opacity="{HULL_STROKE_OPACITY}" stroke-width="2.5" '
                f'stroke-linejoin="round"/></g>'
            )

    # Segment name labels, centred over each hull and set in a soft same-hue
    # chip (shared ``label_cell``). Centring on the hull centroid and lifting
    # the chip a fixed gap above the hull's top edge keeps every label in
    # clear space, out of the point cloud and clear of the boundary. The chip
    # is clamped inside the plot frame so nothing clips at the top edge.
    label_gap = 26.0        # px from the hull's top point to the chip centre
    label_size = 19.0
    chip_half_h = label_size + 0.8 * label_size  # cell height, from label_cell
    for seg in SEGMENTS:
        color = segment_color[seg]
        cx, top_y = _label_anchor(seg_hull_px[seg])
        ly = top_y - label_gap
        # Keep the whole chip below the legend / above the frame top.
        ly = max(ly, PLOT_Y0 + chip_half_h / 2.0 + 4.0)
        parts.append(
            f'<g class="seg {seg_slug[seg]}">'
            + label_cell(
                cx,
                ly,
                seg,
                color,
                variant="tint",
                size=label_size,
                anchor="middle",
            )
            + "</g>"
        )

    # Points on top, each with a crisp white keyline so no dot melts into
    # its hull or a neighbour. Each carries a native tooltip + is focusable.
    for seg in SEGMENTS:
        color = segment_color[seg]
        slug = seg_slug[seg]
        parts.append(f'<g class="seg {slug}">')
        for (x, y), (px, py) in zip(data[seg], seg_px[seg]):
            spend = int(round(x))
            days = round(y, 1)
            tip = f"{seg} · ${spend}/mo · {days} active days/week"
            parts.append(
                f'<circle class="dot {slug}" cx="{px:.1f}" cy="{py:.1f}" r="7.5" '
                f'fill="{color}" stroke="#FFFFFF" stroke-width="1.6" '
                f'tabindex="0" role="img" aria-label="{escape(tip)}">'
                f'<title>{escape(tip)}</title></circle>'
            )
        parts.append("</g>")

    parts.append("</g>")  # /plot

    # --- footer hint ---
    parts.append(
        f'<text x="56" y="{HEIGHT - 22:.1f}" font-size="16" fill="{SUBINK}">'
        f'Each shaded region is the convex hull of one segment · hover or '
        f'focus a dot to isolate its segment</text>'
    )

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the convex-hull SVG to the skill's example asset folder.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "convex-hull",
        build_svg,
        description="Write the house-style convex-hull scatter SVG example.",
    )


if __name__ == "__main__":
    main()

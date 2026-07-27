#!/usr/bin/env python3
"""
make_pairplot — a pair plot / scatterplot matrix (SPLOM) as hand-authored SVG.

A SPLOM lays every pair of numeric variables against each other in a grid: the
off-diagonal cells are scatter plots (one variable versus another), and the
diagonal cells show each variable's own distribution. It is the fastest way to
eyeball, all at once, which variables move together, which separate the groups,
and where the outliers hide — the multivariate answer to "just plot the data".

This generator assembles **one self-contained Scalable Vector Graphics (SVG)**
figure by hand (no matplotlib / seaborn / plotly, no Vega). Building the string
directly is what lets the figure carry the house fullscreen control and the
``mode`` interactivity argument, and keeps the whole grid — data, scales,
markers — under our control. The data lives *inside* this file, so the figure is
reproducible from this module alone: no charting library, no notebook, no build
step.

The illustrative dataset is a fleet of production **electric-vehicle battery
cells** binned by chemistry (three families of lithium-ion cell). Four measured
properties are crossed: usable energy density, fast-charge time, internal
resistance and rated cycle life. The story the grid tells — and states in its
subtitle — is that the three chemistries fall into three clean clusters, so a
single cell measurement is enough to tell the families apart.

Off-diagonal cells are scatter plots coloured by chemistry, each column sharing
one x-scale and each row one y-scale (the standard SPLOM convention, so a point's
position is comparable across a whole row or column). Diagonal cells show the
per-chemistry distribution of that one variable as overlaid kernel-density areas,
so the diagonal is an informative distribution summary rather than a wasted
45-degree line. The result is a clean static figure — a SPLOM earns its keep as
an at-a-glance overview, so no animation or hover motion is added.

Accessibility: each chemistry is encoded by **both** a curated hue **and** a
marker shape (circle / square / triangle). Hue alone drops out under red-green
colour blindness and vanishes entirely in greyscale, so the shape is what keeps
the three families apart there. The three hues (blue / orange / purple) avoid the
red-green confusion axis on purpose.

Running the module writes ``assets/svg-examples/pairplot.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# House-style tokens + shared SVG primitives live alongside in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import qualitative_sequence, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402


# ------------------------------------------------------------------
# Illustrative data — a fleet of EV battery cells, three chemistries.
# Each chemistry occupies a distinct region of the four-variable space,
# which is the whole point of the figure: the clusters separate.
# ------------------------------------------------------------------
#: The four measured cell properties, in grid order. Each entry is
#: (field key, short axis label, unit, rounding decimals for tooltips).
VARIABLES: List[Dict[str, Any]] = [
    {"field": "density", "label": "Energy density", "unit": "Wh/kg", "round": 0},
    {"field": "charge", "label": "Fast-charge time", "unit": "min", "round": 0},
    {"field": "resistance", "label": "Internal resistance", "unit": "mΩ", "round": 1},
    {"field": "cycles", "label": "Rated cycle life", "unit": "cycles", "round": 0},
]

#: Chemistry name -> centroid of its cluster in the four measured
#: variables, plus a spread. Values are plausible for real lithium-ion
#: families: high-nickel (NMC-811) trades cycle life for energy density,
#: lithium-iron-phosphate (LFP) is the durable workhorse, and the
#: silicon-anode cell charges fast at a high-density, shorter-life cost.
CHEMISTRIES: Dict[str, Dict[str, float]] = {
    "NMC-811 (high nickel)": {
        "density": 265, "charge": 42, "resistance": 22.0, "cycles": 1500, "spread": 0.06,
    },
    "LFP (iron phosphate)": {
        "density": 165, "charge": 55, "resistance": 30.0, "cycles": 4200, "spread": 0.06,
    },
    "Silicon-anode (fast)": {
        "density": 305, "charge": 25, "resistance": 15.0, "cycles": 900, "spread": 0.07,
    },
}

#: How many sampled cells per chemistry.
N_PER_GROUP = 26


def make_rows() -> List[Dict[str, Any]]:
    """Sample a reproducible fleet of cells around each chemistry centroid.

    Returns
    -------
    list of dict
        One dict per cell, with the four measured variables plus its
        ``chemistry`` label. A fixed seed makes the figure deterministic.
    """
    rng = random.Random(20260725)
    rows: List[Dict[str, Any]] = []
    for chem, c in CHEMISTRIES.items():
        for _ in range(N_PER_GROUP):
            row: Dict[str, Any] = {"chemistry": chem}
            for var in VARIABLES:
                key = str(var["field"])
                centre = float(c[key])
                # Log-normal-ish jitter keeps every value positive and the
                # cluster roughly elliptical without heavy tails.
                jitter = rng.gauss(0.0, float(c["spread"]))
                val = centre * math.exp(jitter)
                row[key] = round(val, int(var["round"])) if var["round"] else round(val)
            rows.append(row)
    return rows


# ------------------------------------------------------------------
# House style: colours + marker shapes (the dual encoding)
# ------------------------------------------------------------------
# Three chemistry hues picked for maximum separation and colour-vision
# safety: blue / orange / purple avoid the red-green confusion axis.
_PALETTE = qualitative_sequence(8)
COLORS: List[str] = [_PALETTE[5], _PALETTE[1], _PALETTE[6]]  # Blue, Orange, Purple
# A distinct marker shape per chemistry doubles the encoding: hue drops out
# under red-green colour blindness (orange and purple both drift to gold) and
# vanishes entirely in greyscale, so the shape is what actually keeps the three
# families apart there. Circle / square / triangle read cleanly at scatter size.
SHAPES: List[str] = ["circle", "square", "triangle"]

INK = "#1D1D1F"          # primary text
SECONDARY = "#6E6E73"    # subtitle / axis titles
KEYLINE = "#FFFFFF"      # white keyline that lifts a mark off its neighbours
GRID = "#ECECEE"         # very light cell gridline / frame
BG = "#FFFFFF"


def _nice_ticks(lo: float, hi: float, target: int = 4) -> Tuple[float, float, List[float]]:
    """Return a padded ``(min, max)`` window and a short list of round ticks.

    A SPLOM has no room for a dense axis, so this keeps the tick set sparse
    (about ``target`` marks) and rounded to a 1 / 2 / 5 × power-of-ten step so
    the labels read cleanly. The returned window is nudged out to the nearest
    step below/above the data so points never sit on the frame.

    Parameters
    ----------
    lo, hi : float
        The data minimum and maximum for the variable.
    target : int, optional
        Roughly how many ticks to aim for (default 4).

    Returns
    -------
    tuple
        ``(axis_min, axis_max, ticks)`` — the padded scale window and the
        list of tick values that fall inside it.
    """
    span = hi - lo
    if span <= 0:
        span = abs(hi) or 1.0
    # Round the raw step to the nearest 1 / 2 / 5 × 10**k so labels are clean.
    raw = span / max(1, target)
    mag = 10.0 ** math.floor(math.log10(raw))
    for mult in (1.0, 2.0, 2.5, 5.0, 10.0):
        step = mult * mag
        if raw <= step:
            break
    axis_min = math.floor(lo / step) * step
    axis_max = math.ceil(hi / step) * step
    ticks: List[float] = []
    t = axis_min
    # Guard the loop with a tiny epsilon so the top tick is not dropped to
    # floating-point drift.
    while t <= axis_max + step * 1e-6:
        ticks.append(round(t, 6))
        t += step
    return axis_min, axis_max, ticks


def _fmt_tick(v: float) -> str:
    """Format a tick value compactly: thousands with a comma, no trailing zeros."""
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if v == int(v):
        return f"{int(v)}"
    return f"{v:g}"


def _kde(values: List[float], lo: float, hi: float, steps: int = 48) -> List[Tuple[float, float]]:
    """Evaluate a Gaussian kernel-density estimate over a fixed grid.

    A light, dependency-free KDE so the diagonal cells show a smooth
    per-chemistry distribution without pulling in SciPy. The bandwidth follows
    Silverman's rule of thumb, floored so a tight cluster still renders a
    visible bump rather than a spike.

    Parameters
    ----------
    values : list of float
        The samples for one chemistry on one variable.
    lo, hi : float
        The evaluation window (the variable's padded axis range).
    steps : int, optional
        Number of grid points across ``[lo, hi]`` (default 48).

    Returns
    -------
    list of tuple
        ``(x, density)`` pairs, densities un-normalised to a peak (the caller
        scales all three curves to a shared cell height).
    """
    n = len(values)
    if n == 0:
        return [(lo, 0.0), (hi, 0.0)]
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / max(1, n - 1)
    std = math.sqrt(var) if var > 0 else (hi - lo) / 8.0
    # Silverman bandwidth, floored so a very tight cluster still shows a bump.
    bw = max(1.06 * std * n ** (-0.2), (hi - lo) / 40.0)
    out: List[Tuple[float, float]] = []
    for i in range(steps + 1):
        x = lo + (hi - lo) * i / steps
        # Sum of Gaussians centred on each sample; the constant 1/(n·bw·√2π)
        # is dropped because the caller normalises to the tallest curve.
        acc = 0.0
        for v in values:
            z = (x - v) / bw
            acc += math.exp(-0.5 * z * z)
        out.append((x, acc))
    return out


def _marker(shape: str, cx: float, cy: float, r: float, fill: str, cls: str = "") -> str:
    """Return one filled marker (circle / square / triangle) with a white keyline.

    The white keyline lifts each point off its overlapping neighbours without a
    dark ring (a house rule), and the shape is the colour-independent channel
    that survives greyscale and red-green colour blindness.

    Parameters
    ----------
    shape : {'circle', 'square', 'triangle'}
        Which glyph to draw — the per-chemistry marker.
    cx, cy : float
        Marker centre, in user-space pixels.
    r : float
        Marker "radius" (half-size); squares and triangles are sized to read
        at the same visual weight as the circle.
    fill : str
        Fill colour hex (the chemistry's hue).
    cls : str, optional
        A CSS class for the emitted element. Left empty by default so the marker
        is unclassed; the SPLOM passes a per-chemistry class (``"chem-0"`` …) so
        the OS-adaptive ``@media`` rules can retint every mark of one family at
        once. Because a class rule only outranks the inline ``fill`` inside a
        media query, adding it leaves the default render pixel-identical.

    Returns
    -------
    str
        A single SVG element (``<circle>`` / ``<rect>`` / ``<path>``).
    """
    stroke = f'stroke="{KEYLINE}" stroke-width="0.9"'
    cls_attr = f'class="{cls}" ' if cls else ""
    if shape == "square":
        s = r * 1.78  # match the circle's visual area
        return (
            f'<rect {cls_attr}x="{cx - s / 2:.2f}" y="{cy - s / 2:.2f}" width="{s:.2f}" '
            f'height="{s:.2f}" rx="1.2" fill="{fill}" {stroke}/>'
        )
    if shape == "triangle":
        s = r * 2.35  # upward triangle, sized to a comparable footprint
        h = s * 0.866
        p1 = (cx, cy - h * 0.62)
        p2 = (cx - s / 2, cy + h * 0.38)
        p3 = (cx + s / 2, cy + h * 0.38)
        return (
            f'<path {cls_attr}d="M {p1[0]:.2f} {p1[1]:.2f} L {p2[0]:.2f} {p2[1]:.2f} '
            f'L {p3[0]:.2f} {p3[1]:.2f} Z" fill="{fill}" {stroke} '
            f'stroke-linejoin="round"/>'
        )
    # Default: circle.
    return (
        f'<circle {cls_attr}cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
        f'fill="{fill}" {stroke}/>'
    )


def _legend_glyph(shape: str, cx: float, cy: float, r: float, fill: str, cls: str = "") -> str:
    """Return a slightly larger marker for the legend swatch (same shape + hue + class)."""
    return _marker(shape, cx, cy, r, fill, cls)


def build_svg(mode: str = "self-contained") -> str:
    """Assemble the full SPLOM SVG string.

    Lays out an N×N grid of cells inside a plotting area. Off-diagonal cells are
    mini scatter plots sharing a per-column x-scale and a per-row y-scale;
    diagonal cells are per-chemistry kernel-density areas for that one variable.
    Axis ticks are drawn only on the outer edges (left column, bottom row), and
    each variable is labelled once per row and once per column. A single legend
    at the top fuses each chemistry's hue and marker shape into one swatch.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). In
        ``"self-contained"`` (the default) the SVG carries its own hidden
        fullscreen button plus wiring script; the other modes ship no button.
        The button starts ``display:none`` and never affects a raster, so
        thumbnails are unchanged.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    rows = make_rows()
    variables = VARIABLES
    n = len(variables)
    chem_names = list(CHEMISTRIES.keys())

    # --- per-variable scales (shared across the whole row/column) ----
    # Each variable gets ONE padded window + tick set, reused by every cell in
    # its column (as x) and its row (as y). This shared scaling is the SPLOM
    # convention that makes a point's position comparable along a whole strip.
    scales: Dict[str, Dict[str, Any]] = {}
    for var in variables:
        key = str(var["field"])
        vals = [float(r[key]) for r in rows]
        lo, hi = min(vals), max(vals)
        # Aim for ~3 ticks so a 210 px cell never crowds its labels — the
        # wide "cycles" values (thousands) especially need the breathing room.
        axis_min, axis_max, ticks = _nice_ticks(lo, hi, target=3)
        scales[key] = {"min": axis_min, "max": axis_max, "ticks": ticks}

    # --- canvas geometry (poster scale) ------------------------------
    cell = 210          # inner plotting size of one grid cell, px
    gap = 22            # gutter between cells
    m_left = 150        # room for the left y-labels + tick labels
    m_right = 40
    m_top = 250         # title + subtitle + legend band
    m_bottom = 150      # bottom x-labels + tick labels
    grid_w = n * cell + (n - 1) * gap
    grid_h = grid_w
    width = m_left + grid_w + m_right
    height = m_top + grid_h + m_bottom
    plot_x = m_left
    plot_y = m_top

    def cell_origin(col: int, row: int) -> Tuple[float, float]:
        """Return the top-left pixel of the cell at grid ``(col, row)``."""
        return (plot_x + col * (cell + gap), plot_y + row * (cell + gap))

    def scale_x(key: str, x0: float, v: float) -> float:
        """Map a value of variable ``key`` to an x pixel inside a cell at ``x0``."""
        sc = scales[key]
        lo, hi = float(sc["min"]), float(sc["max"])
        return x0 + (v - lo) / (hi - lo) * cell

    def scale_y(key: str, y0: float, v: float) -> float:
        """Map a value of variable ``key`` to a y pixel (y-down) in a cell at ``y0``."""
        sc = scales[key]
        lo, hi = float(sc["min"]), float(sc["max"])
        return y0 + (hi - v) / (hi - lo) * cell

    parts: List[str] = []

    # --- SVG root + accessible title/description ---------------------
    parts.append(svg_open(width, height, "pp-title", "pp-desc"))
    parts.append(
        '<title id="pp-title">Pair plot of four battery-cell properties by '
        'chemistry</title>'
    )
    parts.append(
        '<desc id="pp-desc">A scatterplot matrix (pair plot) of a fleet of '
        'lithium-ion battery cells from three chemistries: NMC-811 high-nickel, '
        'LFP iron-phosphate, and a fast-charging silicon-anode cell. The four '
        'measured properties crossed in the grid are usable energy density, '
        'fast-charge time, internal resistance, and rated cycle life. '
        'Off-diagonal cells are scatter plots where each chemistry has its own '
        'hue and marker shape (circle, square, triangle) so the families stay '
        'apart for colour-blind and greyscale readers; diagonal cells show each '
        'property’s per-chemistry distribution as a density curve. On every '
        'pair the three chemistries form three separated clusters: silicon-anode '
        'is high-density and fast-charging but short-lived, LFP is the durable '
        'long-cycle-life workhorse, and NMC-811 sits between them, so one cell '
        'measurement is enough to identify the family. Illustrative data.</desc>'
    )

    # OS-adaptive overrides only (this figure has no motion / interactivity, so
    # the <style> block carries nothing else). Additive: every rule lives inside
    # a media query, so the default render stays pixel-identical to the shipped
    # figure. Under prefers-contrast each chemistry deepens to its high-contrast
    # hue on BOTH the marker/area fills and the diagonal density lines (stroke).
    # Under forced colours every chemistry mark drops to system CanvasText — safe
    # here because each family is ALSO encoded by marker shape (circle / square /
    # triangle), so the three families stay apart with no colour at all.
    parts.append(
        "<style>\n"
        + os_adaptive_style(
            {
                ".chem-0": COLORS[0],
                ".chem-1": COLORS[1],
                ".chem-2": COLORS[2],
            },
            role="both",
            forced=True,
        )
        + "\n"
        # Additive OS dark mode: dark paper + light ink (default ink_map); the
        # per-chemistry marker/area hues are data, left alone. The very light
        # cell frames and interior gridlines darken so the SPLOM grid reads on
        # the dark surface; the white keyline lifting each mark stays white.
        + os_dark_style(extra='[stroke="#ECECEE"]{stroke:#2C2C30;}')
        + "\n</style>"
    )

    # Static figure: no motion, so nothing to guard behind reduced-motion.
    parts.append(f'<rect width="{width}" height="{height}" fill="{BG}"/>')

    # --- title + subtitle (the takeaway) -----------------------------
    parts.append(
        f'<text x="{m_left}" y="70" font-size="40" font-weight="700" '
        f'fill="{INK}">Three battery chemistries, three clean clusters</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="108" font-size="20" fill="{SECONDARY}">'
        f'Pair plot of four measured properties across a fleet of lithium-ion '
        f'cells. The chemistries separate on every</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="134" font-size="20" fill="{SECONDARY}">'
        f'pair, so one cell measurement tells the families apart. The diagonal '
        f'shows each distribution. Illustrative.</text>'
    )

    # --- legend (hue + shape fused, one swatch per chemistry) --------
    leg_y = 192
    parts.append(
        f'<text x="{m_left}" y="{leg_y - 22}" font-size="19" font-weight="600" '
        f'fill="{INK}">Cell chemistry</text>'
    )
    leg_x = float(m_left)
    for i, name in enumerate(chem_names):
        glyph = _legend_glyph(SHAPES[i], leg_x + 11, leg_y, 8.5, COLORS[i], f"chem-{i}")
        parts.append(glyph)
        parts.append(
            f'<text x="{leg_x + 28:.1f}" y="{leg_y + 6:.1f}" font-size="19" '
            f'fill="{INK}">{xml_escape(name)}</text>'
        )
        # Advance past the label — width is proportional to the text length.
        leg_x += 28 + len(name) * 10.6 + 34

    # --- one cell helper ---------------------------------------------
    def draw_scatter_cell(col: int, row: int) -> None:
        """Draw an off-diagonal scatter cell: column variable (x) vs row variable (y)."""
        var_x = variables[col]
        var_y = variables[row]
        kx = str(var_x["field"])
        ky = str(var_y["field"])
        x0, y0 = cell_origin(col, row)

        # Cell frame + faint interior gridlines at the shared ticks.
        parts.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{cell}" height="{cell}" '
            f'fill="{BG}" stroke="{GRID}" stroke-width="1.2"/>'
        )
        for t in scales[kx]["ticks"]:  # vertical gridlines (x ticks)
            gx = scale_x(kx, x0, float(t))
            parts.append(
                f'<line x1="{gx:.1f}" y1="{y0:.1f}" x2="{gx:.1f}" '
                f'y2="{y0 + cell:.1f}" stroke="{GRID}" stroke-width="1"/>'
            )
        for t in scales[ky]["ticks"]:  # horizontal gridlines (y ticks)
            gy = scale_y(ky, y0, float(t))
            parts.append(
                f'<line x1="{x0:.1f}" y1="{gy:.1f}" x2="{x0 + cell:.1f}" '
                f'y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>'
            )

        # Points, grouped by chemistry so each keeps its own hue + shape.
        for ci, chem in enumerate(chem_names):
            fill = COLORS[ci]
            shape = SHAPES[ci]
            for r in rows:
                if r["chemistry"] != chem:
                    continue
                cx = scale_x(kx, x0, float(r[kx]))
                cy = scale_y(ky, y0, float(r[ky]))
                parts.append(_marker(shape, cx, cy, 3.6, fill, f"chem-{ci}"))

    def draw_diagonal_cell(idx: int) -> None:
        """Draw a diagonal cell: overlaid per-chemistry densities of one variable."""
        var = variables[idx]
        key = str(var["field"])
        x0, y0 = cell_origin(idx, idx)
        lo = float(scales[key]["min"])
        hi = float(scales[key]["max"])

        parts.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{cell}" height="{cell}" '
            f'fill="{BG}" stroke="{GRID}" stroke-width="1.2"/>'
        )
        for t in scales[key]["ticks"]:  # keep the x gridlines for continuity
            gx = scale_x(key, x0, float(t))
            parts.append(
                f'<line x1="{gx:.1f}" y1="{y0:.1f}" x2="{gx:.1f}" '
                f'y2="{y0 + cell:.1f}" stroke="{GRID}" stroke-width="1"/>'
            )

        # Compute all three curves first so they share one vertical scale (the
        # tallest peak reaches ~0.86 of the cell, leaving headroom).
        curves: List[Tuple[int, str, str, List[Tuple[float, float]]]] = []
        peak = 0.0
        for ci, chem in enumerate(chem_names):
            vals = [float(r[key]) for r in rows if r["chemistry"] == chem]
            pts = _kde(vals, lo, hi, steps=48)
            peak = max(peak, max(d for _, d in pts))
            curves.append((ci, COLORS[ci], chem, pts))
        if peak <= 0:
            peak = 1.0
        usable_h = cell * 0.86
        baseline = y0 + cell

        for ci, fill, _chem, pts in curves:
            # Area (translucent) + a crisp top line, so overlapping clusters
            # stay readable — this is what makes the diagonal informative. Both
            # carry the per-chemistry class so the OS-adaptive @media rules
            # retint the density fill and its top line with the marker family.
            cls = f"chem-{ci}"
            poly = []
            for vx, d in pts:
                px_ = scale_x(key, x0, vx)
                py_ = baseline - (d / peak) * usable_h
                poly.append((px_, py_))
            area_d = f'M {poly[0][0]:.2f} {baseline:.2f}'
            area_d += "".join(f' L {x:.2f} {y:.2f}' for x, y in poly)
            area_d += f' L {poly[-1][0]:.2f} {baseline:.2f} Z'
            parts.append(
                f'<path class="{cls}" d="{area_d}" fill="{fill}" fill-opacity="0.42"/>'
            )
            line_d = f'M {poly[0][0]:.2f} {poly[0][1]:.2f}'
            line_d += "".join(f' L {x:.2f} {y:.2f}' for x, y in poly[1:])
            parts.append(
                f'<path class="{cls}" d="{line_d}" fill="none" stroke="{fill}" '
                f'stroke-width="2" stroke-linejoin="round"/>'
            )

    # --- draw every cell ---------------------------------------------
    for row in range(n):
        for col in range(n):
            if row == col:
                draw_diagonal_cell(row)
            else:
                draw_scatter_cell(col, row)

    # --- outer-edge axis ticks + labels ------------------------------
    # Bottom row carries the x tick labels for each column variable; left
    # column carries the y tick labels for each row variable. Interior cells
    # stay clean — the standard SPLOM convention.
    tick_font = 'font-family="Roboto Mono, monospace"'
    for col in range(n):
        var = variables[col]
        key = str(var["field"])
        x0, _ = cell_origin(col, n - 1)
        base_y = plot_y + grid_h  # bottom of the grid
        for t in scales[key]["ticks"]:
            gx = scale_x(key, x0, float(t))
            parts.append(
                f'<line x1="{gx:.1f}" y1="{base_y:.1f}" x2="{gx:.1f}" '
                f'y2="{base_y + 6:.1f}" stroke="{SECONDARY}" stroke-width="1.2"/>'
            )
            parts.append(
                f'<text x="{gx:.1f}" y="{base_y + 24:.1f}" font-size="14" '
                f'{tick_font} fill="{SECONDARY}" text-anchor="middle">'
                f'{_fmt_tick(float(t))}</text>'
            )
        # Column variable title, centred under its column.
        cx = x0 + cell / 2
        parts.append(
            f'<text x="{cx:.1f}" y="{base_y + 58:.1f}" font-size="18" '
            f'font-weight="600" fill="{INK}" text-anchor="middle">'
            f'{xml_escape(str(var["label"]))}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{base_y + 80:.1f}" font-size="15" '
            f'fill="{SECONDARY}" text-anchor="middle">'
            f'({xml_escape(str(var["unit"]))})</text>'
        )

    for row in range(n):
        var = variables[row]
        key = str(var["field"])
        _, y0 = cell_origin(0, row)
        left = float(plot_x)
        for t in scales[key]["ticks"]:
            gy = scale_y(key, y0, float(t))
            parts.append(
                f'<line x1="{left - 6:.1f}" y1="{gy:.1f}" x2="{left:.1f}" '
                f'y2="{gy:.1f}" stroke="{SECONDARY}" stroke-width="1.2"/>'
            )
            parts.append(
                f'<text x="{left - 11:.1f}" y="{gy + 5:.1f}" font-size="14" '
                f'{tick_font} fill="{SECONDARY}" text-anchor="end">'
                f'{_fmt_tick(float(t))}</text>'
            )
        # Row variable title, rotated along the left edge of its row.
        cy = y0 + cell / 2
        title_x = float(m_left) - 92
        label = f'{var["label"]} ({var["unit"]})'
        parts.append(
            f'<text x="{title_x:.1f}" y="{cy:.1f}" font-size="18" '
            f'font-weight="600" fill="{INK}" text-anchor="middle" '
            f'transform="rotate(-90 {title_x:.1f} {cy:.1f})">'
            f'{xml_escape(label)}</text>'
        )

    # --- fullscreen control (mode-dependent) + close -----------------
    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the pair-plot SVG to the canonical assets path (or ``--out``)."""
    render_cli(
        __file__, "pairplot", build_svg,
        description="Render the house-style pair plot / scatterplot matrix (SPLOM) to SVG.",
    )


if __name__ == "__main__":
    main()

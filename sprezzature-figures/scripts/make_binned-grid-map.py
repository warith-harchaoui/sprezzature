#!/usr/bin/env python3
"""
make_binned-grid-map — a house-styled square-binned (screen-grid) density
map as a hand-authored SVG.

A binned-grid map answers "where are the events densest?" by tiling the
map extent with a regular lattice of *square* cells, counting how many
raw events fall in each cell, and shading the cell by that count on a
sequential single-hue ramp. It is the square-bin sibling of the hexbin
map (``hexmap.svg``): where the hexagon lattice trades axis alignment for
six equidistant neighbours, the square grid keeps a crisp, legible
raster that maps one-to-one onto a city block grid — exactly what a
crime-desk or operations analyst reaches for.

This module builds the SVG string by hand (no matplotlib / seaborn /
plotly, and no Vega, because a square lattice clipped to an irregular
city boundary over a river and two parks is clearer authored directly).
It follows the sprezzature-* house style pulled from :mod:`_style`: a
single-hue sequential ramp keyed to the palette's Red (the crime-map
convention), Roboto typography, ink ``#1D1D1F`` on a white background, a
rounded title block, a takeaway title, and a one-line subtitle.

The figure is interactive without any JavaScript: hovering or
keyboard-focusing any cell lifts it with a crisp outline, and every
filled cell carries a native ``<title>`` tooltip reporting its incident
count. Motion is guarded by ``prefers-reduced-motion``. The event cloud
is generated deterministically (fixed seed) so re-running is
reproducible.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/binned-grid-map.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_dark_style  # noqa: E402
from _svg import hex_to_rgb as _hex_to_rgb, svg_open  # noqa: E402
from _svg import xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. A generous, poster-like figure that
#: leaves a right-hand column for the legend + summary callout.
_WIDTH: int = 1280
_HEIGHT: int = 900

#: The plotting extent (the "map" rectangle) inside the canvas. Chosen so
#: an integer number of square cells tiles it exactly (see _GRID_N).
_MAP_X0: float = 64.0
_MAP_Y0: float = 168.0
_MAP_X1: float = 912.0
_MAP_Y1: float = 852.0

#: Number of square cells along the longer (x) extent. The cell edge is
#: derived from this so the grid tiles the extent without a ragged margin.
_GRID_COLS: int = 24

#: Real-world ground distance one square cell edge represents, in metres.
#: The subtitle quotes a 400 m grid; the scale bar is derived from this so
#: the on-map ruler and the copy always agree.
_CELL_METRES: float = 400.0

#: House-style inks and basemap tints.
_INK: str = "#1D1D1F"       # primary text
_SUBTLE: str = "#6E6E73"    # secondary text
_WATER: str = "#CBDCF0"     # river / water (faint blue)
_PARK: str = "#CFE9D4"      # green space (faint green)
_LAND: str = "#F5F6F8"      # land base under the grid
_EMPTY: str = "#ECEEF1"     # a land cell that caught zero incidents
_STROKE: str = "#FFFFFF"    # white casing between cells
_BG: str = "#FFFFFF"        # background
_OUTLINE: str = "#B9C2CE"   # city boundary casing

#: Reproducible event cloud.
_SEED: int = 20260726


# ------------------------------------------------------------------
# Sequential single-hue ramp (pale -> palette Red)
# ------------------------------------------------------------------
def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    """Convert an ``(r, g, b)`` triple (0-255 floats) back to ``#RRGGBB``."""
    r, g, b = (max(0, min(255, round(c))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def _ramp(t: float, top: str, *, light: Tuple[int, int, int] = (255, 233, 224)) -> str:
    """Interpolate a sequential single-hue ramp at position ``t`` in [0, 1].

    A pale warm tint at ``t = 0`` deepens to the saturated house Red at
    ``t = 1``. A mild gamma pulls midtones apart so the busy cells stay
    visually distinct rather than all reading as "dark red".

    Parameters
    ----------
    t : float
        Normalised count, clamped to ``[0, 1]``.
    top : str
        The darkest hex at ``t = 1`` (the palette's Red).
    light : tuple of int, optional
        The lightest colour at ``t = 0``.

    Returns
    -------
    str
        A ``#RRGGBB`` hex string.
    """
    t = max(0.0, min(1.0, t))
    t = t ** 0.70  # gentle gamma so mid densities separate
    r1, g1, b1 = light
    r2, g2, b2 = _hex_to_rgb(top)
    return _rgb_to_hex((
        r1 + (r2 - r1) * t,
        g1 + (g2 - g1) * t,
        b1 + (b2 - b1) * t,
    ))


# ------------------------------------------------------------------
# Map extent — a stylised city boundary with a river + two parks so the
# grid is clipped to an irregular shape (a binned map is a *map*, not a
# bare rectangle). Coordinates are in the extent's own 0..1 square, y-down.
# ------------------------------------------------------------------
#: A closed city-boundary polygon in normalised [0, 1] extent coordinates.
#: An irregular municipal outline so the corner cells vary in fill.
_BOUNDARY: List[Tuple[float, float]] = [
    (0.05, 0.14), (0.30, 0.05), (0.55, 0.09), (0.78, 0.04),
    (0.94, 0.16), (0.97, 0.42), (0.88, 0.58), (0.95, 0.78),
    (0.80, 0.94), (0.56, 0.90), (0.40, 0.97), (0.20, 0.92),
    (0.07, 0.72), (0.03, 0.44), (0.08, 0.28),
]

#: A river ribbon (poly-line, thick stroke) cutting diagonally through the
#: city. Points in normalised extent coordinates.
_RIVER: List[Tuple[float, float]] = [
    (0.02, 0.30), (0.22, 0.40), (0.40, 0.46), (0.55, 0.58),
    (0.70, 0.66), (0.86, 0.82), (0.99, 0.92),
]

#: Two green spaces (closed polygons) — a central park and a riverside strip.
_PARKS: List[List[Tuple[float, float]]] = [
    [(0.60, 0.16), (0.76, 0.14), (0.80, 0.30), (0.66, 0.36), (0.56, 0.28)],
    [(0.12, 0.55), (0.26, 0.58), (0.24, 0.72), (0.10, 0.70)],
]


def _point_in_poly(x: float, y: float, poly: List[Tuple[float, float]]) -> bool:
    """Return ``True`` when ``(x, y)`` lies inside ``poly`` (ray casting)."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _dist_to_polyline(x: float, y: float, line: List[Tuple[float, float]]) -> float:
    """Return the shortest distance from ``(x, y)`` to a poly-line."""
    best = 1e18
    for i in range(len(line) - 1):
        x1, y1 = line[i]
        x2, y2 = line[i + 1]
        dx, dy = x2 - x1, y2 - y1
        seg2 = dx * dx + dy * dy
        if seg2 == 0.0:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / seg2))
        px, py = x1 + t * dx, y1 + t * dy
        d = (x - px) ** 2 + (y - py) ** 2
        if d < best:
            best = d
    return best ** 0.5


# ------------------------------------------------------------------
# Event cloud — a communicative density surface
# ------------------------------------------------------------------
#: Incident hotspot centres in extent coords, each a 2-D Gaussian blob
#: with a weight (share of the sampled incidents) and a spread.
_HOTSPOTS: List[Tuple[float, float, float, float]] = [
    # (cx, cy, weight, sigma)
    (0.30, 0.30, 0.40, 0.075),   # nightlife / downtown core (the peak)
    (0.50, 0.52, 0.24, 0.10),    # transit-hub district
    (0.72, 0.70, 0.16, 0.11),    # riverside market
    (0.20, 0.62, 0.12, 0.10),    # west-end retail strip
    (0.82, 0.34, 0.08, 0.09),    # north gateway
]


def _sample_points(n: int, rng: random.Random) -> List[Tuple[float, float]]:
    """Draw ``n`` incidents from the hotspot mixture, kept on land, off water.

    Parameters
    ----------
    n : int
        Target number of accepted points.
    rng : random.Random
        Seeded generator for reproducibility.

    Returns
    -------
    list of (float, float)
        Points in normalised ``[0, 1]`` extent coordinates, all inside the
        city boundary and not in the river channel.
    """
    weights = [w for _, _, w, _ in _HOTSPOTS]
    total = sum(weights)
    cum: List[float] = []
    acc = 0.0
    for w in weights:
        acc += w / total
        cum.append(acc)

    pts: List[Tuple[float, float]] = []
    guard = 0
    while len(pts) < n and guard < n * 40:
        guard += 1
        u = rng.random()
        k = next(i for i, c in enumerate(cum) if u <= c)
        cx, cy, _, sigma = _HOTSPOTS[k]
        x = rng.gauss(cx, sigma)
        y = rng.gauss(cy, sigma)
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            continue
        if not _point_in_poly(x, y, _BOUNDARY):
            continue
        # Incidents don't happen mid-river; keep them out of the channel.
        if _dist_to_polyline(x, y, _RIVER) < 0.022:
            continue
        pts.append((x, y))
    return pts


# ------------------------------------------------------------------
# Square grid lattice
# ------------------------------------------------------------------
def _build_grid() -> Tuple[List[Dict[str, float]], float]:
    """Tile the map extent with square cells, keeping cells inside the city.

    A cell is kept when its centre falls inside the city boundary and is
    not squarely in the river channel, so the lattice reads as a city, not
    a rectangle.

    Returns
    -------
    tuple
        ``(cells, cell_px)`` where ``cells`` is one record per kept cell
        (pixel top-left ``x``/``y`` plus normalised-extent centre
        ``nx``/``ny``) and ``cell_px`` is the square edge in pixels.
    """
    ext_w = _MAP_X1 - _MAP_X0
    ext_h = _MAP_Y1 - _MAP_Y0
    cell_px = ext_w / _GRID_COLS
    n_rows = int(round(ext_h / cell_px))

    cells: List[Dict[str, float]] = []
    for row in range(n_rows):
        for col in range(_GRID_COLS):
            x = _MAP_X0 + col * cell_px
            y = _MAP_Y0 + row * cell_px
            # Cell centre in normalised extent coordinates.
            nx = (col + 0.5) * cell_px / ext_w
            ny = (row + 0.5) * cell_px / ext_h
            if not _point_in_poly(nx, ny, _BOUNDARY):
                continue
            # Drop cells whose centre sits in the river channel so the water
            # shows through as a continuous ribbon.
            if _dist_to_polyline(nx, ny, _RIVER) < 0.020:
                continue
            # Drop cells over a park so the green space reads as open ground.
            if any(_point_in_poly(nx, ny, park) for park in _PARKS):
                continue
            cells.append({"x": x, "y": y, "nx": nx, "ny": ny})
    return cells, cell_px


def _bin_points(
    cells: List[Dict[str, float]],
    points: List[Tuple[float, float]],
    cell_px: float,
) -> None:
    """Count each incident into the square cell that contains it.

    Mutates ``cells`` in place, adding a ``count`` key. Assignment is by
    integer grid index in pixel space, which is exact for a regular square
    lattice.

    Parameters
    ----------
    cells : list of dict
        The lattice from :func:`_build_grid`.
    points : list of (float, float)
        Points in normalised extent coordinates.
    cell_px : float
        The square edge in pixels.
    """
    ext_w = _MAP_X1 - _MAP_X0
    ext_h = _MAP_Y1 - _MAP_Y0
    # Index cells by their integer (col, row) so binning is O(1) per point.
    index: Dict[Tuple[int, int], Dict[str, float]] = {}
    for c in cells:
        c["count"] = 0.0
        col = int(round((c["x"] - _MAP_X0) / cell_px))
        row = int(round((c["y"] - _MAP_Y0) / cell_px))
        index[(col, row)] = c
    for nx, ny in points:
        px = _MAP_X0 + nx * ext_w
        py = _MAP_Y0 + ny * ext_h
        col = int((px - _MAP_X0) // cell_px)
        row = int((py - _MAP_Y0) // cell_px)
        cell = index.get((col, row))
        if cell is not None:
            cell["count"] += 1.0


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def _to_px(pts: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Map normalised extent points to pixel coordinates."""
    ext_w = _MAP_X1 - _MAP_X0
    ext_h = _MAP_Y1 - _MAP_Y0
    return [(_MAP_X0 + nx * ext_w, _MAP_Y0 + ny * ext_h) for nx, ny in pts]


# ------------------------------------------------------------------
# Cartographic furniture — north arrow + scale bar
# ------------------------------------------------------------------
def _north_arrow(cx: float, cy: float, *, r: float = 26.0) -> str:
    """Return a small, tasteful north indicator centred on ``(cx, cy)``.

    A slim two-tone needle (ink north half, hollow south half) over a faint
    ring, capped by an ``N``. No black halo — the ring is a light hairline —
    so it reads as a compass mark, not a heavy stamp.

    Parameters
    ----------
    cx, cy : float
        Centre of the compass, in user-space pixels.
    r : float, optional
        Needle half-height (the ring radius is a touch larger).

    Returns
    -------
    str
        A self-contained SVG ``<g>``.
    """
    ring = r + 8.0
    # Needle: a narrow diamond, top half filled ink, bottom half hollow.
    half_w = r * 0.30
    top = (cx, cy - r)
    bot = (cx, cy + r)
    left = (cx - half_w, cy)
    right = (cx + half_w, cy)
    north_tri = (
        f'M{top[0]:.1f},{top[1]:.1f} L{right[0]:.1f},{right[1]:.1f} '
        f'L{left[0]:.1f},{left[1]:.1f} Z'
    )
    south_tri = (
        f'M{bot[0]:.1f},{bot[1]:.1f} L{right[0]:.1f},{right[1]:.1f} '
        f'L{left[0]:.1f},{left[1]:.1f} Z'
    )
    parts: List[str] = [
        '<g role="img" aria-label="North is up">',
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring:.1f}" fill="#FFFFFF" '
        f'fill-opacity="0.72" stroke="{_OUTLINE}" stroke-width="1.4"/>',
        # South half first (hollow), then the ink north half on top.
        f'<path d="{south_tri}" fill="#FFFFFF" stroke="{_SUBTLE}" '
        f'stroke-width="1.2" stroke-linejoin="round"/>',
        f'<path d="{north_tri}" fill="{_INK}" stroke-linejoin="round"/>',
        f'<text x="{cx:.1f}" y="{cy - ring - 4:.1f}" text-anchor="middle" '
        f'font-size="17" font-weight="700" fill="{_INK}">N</text>',
        '</g>',
    ]
    return "".join(parts)


def _scale_bar(x0: float, y0: float, cell_px: float) -> str:
    """Return a labelled distance scale bar with its left edge at ``(x0, y0)``.

    The bar is an integer number of grid cells wide so it doubles as a "read
    the grid" key: its length maps to a round ground distance derived from
    :data:`_CELL_METRES`. It is drawn as a two-tone (alternating ink / white)
    checker rule with ``0`` and the total distance labelled, the house
    cartographic convention.

    Parameters
    ----------
    x0, y0 : float
        Left end of the bar's rule (the baseline the ticks sit on).
    cell_px : float
        The grid cell edge in pixels (one segment of the bar).

    Returns
    -------
    str
        A self-contained SVG ``<g>``.
    """
    # Span a round number of cells: 5 cells = 2000 m = 2 km at 400 m / cell.
    n_seg = 5
    seg_total_m = _CELL_METRES * n_seg
    bar_len = cell_px * n_seg
    bar_h = 8.0
    parts: List[str] = [
        f'<g role="img" aria-label="Scale bar: 0 to '
        f'{seg_total_m / 1000:.0f} kilometres">'
    ]
    # A soft white plate so the rule reads over grid or land alike.
    plate_pad = 12.0
    parts.append(
        f'<rect x="{x0 - plate_pad:.1f}" y="{y0 - 26:.1f}" '
        f'width="{bar_len + 2 * plate_pad:.1f}" height="54" rx="9" '
        f'fill="#FFFFFF" fill-opacity="0.78"/>'
    )
    # Alternating filled / hollow segments.
    for i in range(n_seg):
        fill = _INK if i % 2 == 0 else "#FFFFFF"
        parts.append(
            f'<rect x="{x0 + i * cell_px:.1f}" y="{y0:.1f}" '
            f'width="{cell_px:.1f}" height="{bar_h:.1f}" fill="{fill}" '
            f'stroke="{_INK}" stroke-width="1"/>'
        )
    # End labels: 0 at the left, the total at the right, with a unit caption.
    parts.append(
        f'<text x="{x0:.1f}" y="{y0 - 6:.1f}" text-anchor="middle" '
        f'font-size="14" fill="{_INK}" '
        f'font-family="Roboto Mono, monospace">0</text>'
    )
    parts.append(
        f'<text x="{x0 + bar_len:.1f}" y="{y0 - 6:.1f}" text-anchor="middle" '
        f'font-size="14" fill="{_INK}" '
        f'font-family="Roboto Mono, monospace">'
        f'{seg_total_m / 1000:.0f} km</text>'
    )
    parts.append(
        f'<text x="{x0 + bar_len / 2:.1f}" y="{y0 + bar_h + 15:.1f}" '
        f'text-anchor="middle" font-size="12.5" fill="{_SUBTLE}">'
        f'each cell = {_CELL_METRES:.0f} m</text>'
    )
    parts.append('</g>')
    return "".join(parts)


# ------------------------------------------------------------------
# SVG assembly
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full binned-grid-map SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"`` / ``"external"`` / ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level passed to :func:`_style.load_palette`
        (``"universal"`` — the default, colour-vision-safe standard — plus
        ``"high-contrast"``, ``"monochrome"``, ``"deuteranopia"``,
        ``"protanopia"`` and ``"tritanopia"``). Wired through the
        ``--accessibility`` CLI flag by :func:`_render.render_cli`.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    palette = load_palette(accessibility)
    red = palette.get("Red", "#FF3B30")

    rng = random.Random(_SEED)
    points = _sample_points(2600, rng)
    cells, cell_px = _build_grid()
    _bin_points(cells, points, cell_px)

    counts = [int(c["count"]) for c in cells]
    max_count = max(counts) if counts else 1
    total = sum(counts)
    n_cells = len(cells)
    n_hit = sum(1 for c in counts if c > 0)

    ext_w = _MAP_X1 - _MAP_X0

    # ---- header ----
    parts: List[str] = []
    parts.append(svg_open(_WIDTH, _HEIGHT, "bg-title", "bg-desc"))
    parts.append(
        '<title id="bg-title">Night-time incidents concentrate in the '
        'downtown core of Riverbend</title>'
    )
    desc = (
        f"Square-binned density map of Riverbend (an illustrative city). The "
        f"city is tiled with a regular grid of {n_cells} square cells, each "
        f"400 metres on a side, shaded by the number of reported night-time "
        f"incidents that fell inside it, from {total:,} incidents in all. The "
        f"single-hue red ramp runs from pale (few incidents) to deep red (the "
        f"busiest cell, {max_count} incidents). Incidents concentrate in the "
        f"downtown core and around the transit hub and fade toward the city "
        f"edge; the river channel and two parks stay empty. A north arrow "
        f"(north is up) and a 2-kilometre scale bar orient the map."
    )
    parts.append(f'<desc id="bg-desc">{desc}</desc>')

    # ---- interactivity (pure CSS, no JS) ----
    style_rows = [
        ".cell { transition: transform .16s ease, stroke .16s ease; "
        "transform-box: fill-box; transform-origin: center; }",
        # Lift and outline the hovered/focused cell so a single bin pops.
        f".cell:hover, .cell:focus {{ transform: scale(1.35); "
        f"stroke: {_INK}; stroke-width: 1.4; outline: none; }}",
        f".legend-swatch {{ stroke: {_STROKE}; stroke-width: 0.6; }}",
        "@media (prefers-reduced-motion: reduce) { .cell { transition: none; } "
        ".cell:hover, .cell:focus { transform: none; } }",
        # prefers-contrast: this is a PERCEPTUAL figure — the red density ramp is
        # a sequential single-hue map and is left untouched. We only STRENGTHEN
        # STRUCTURE: deepen the secondary ink toward the primary ink and darken +
        # thicken the city-boundary casing so the map frame reads harder for a
        # low-vision reader without re-tuning the ramp. Additive + media-gated, so
        # the default render is byte-for-byte unchanged.
        "@media (prefers-contrast: more) {"
        f' [fill="{_SUBTLE}"]{{fill:{_INK};}}'
        f' [stroke="{_OUTLINE}"]{{stroke:#5E6B7A;stroke-width:3.5;}}'
        " }",
        # Additive dark mode: the default block inverts the paper and the soft
        # white backplates (north arrow, scale bar) and off-whites the ink; the
        # light land base is a bespoke fill it misses, so darken it here. The
        # white cell casings are strokes (not fills) and stay light keylines,
        # and the red data ramp is left untouched.
        os_dark_style(extra='[fill="%s"]{fill:#161719;}' % _LAND),
    ]
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_MAP_X0}" y="70" font-size="34" font-weight="700" '
        f'fill="{_INK}">Riverbend: incidents cluster on the downtown '
        f'core</text>'
    )
    parts.append(
        f'<text x="{_MAP_X0}" y="106" font-size="20" fill="{_SUBTLE}">'
        f'Night-time incidents (10 PM-4 AM) per 400 m grid cell across '
        f'Riverbend · illustrative</text>'
    )

    # ---- land base + city boundary ----
    boundary_px = _to_px(_BOUNDARY)
    boundary_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in boundary_px) + "Z"
    # A clip path so water, parks and grid never bleed past the city edge.
    parts.append(
        f'<defs><clipPath id="cityclip"><path d="{boundary_d}"/></clipPath></defs>'
    )
    parts.append(
        f'<path d="{boundary_d}" fill="{_LAND}" stroke="{_OUTLINE}" '
        f'stroke-width="2.5" stroke-linejoin="round"/>'
    )

    # ---- water + parks (clipped to the city) ----
    parts.append('<g clip-path="url(#cityclip)">')
    # Parks first, then the river on top so the river reads continuous.
    for park in _PARKS:
        pk = _to_px(park)
        pk_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pk) + "Z"
        parts.append(f'<path d="{pk_d}" fill="{_PARK}"/>')
    river_px = _to_px(_RIVER)
    river_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in river_px)
    # River width scaled to the extent so it reads as a channel, not a hairline.
    parts.append(
        f'<path d="{river_d}" fill="none" stroke="{_WATER}" '
        f'stroke-width="{0.040 * ext_w:.1f}" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
    )
    parts.append('</g>')

    # ---- faint basemap labels (over the open water / green negative space) ----
    # Placed on empty basemap so they never fight a filled cell for contrast.
    riv_lx, riv_ly = _to_px([(0.80, 0.755)])[0]
    park_lx, park_ly = _to_px([(0.68, 0.255)])[0]
    parts.append(
        f'<text x="{riv_lx:.1f}" y="{riv_ly:.1f}" font-size="15" '
        f'fill="#7E97BD" font-style="italic" transform="rotate(30 '
        f'{riv_lx:.1f} {riv_ly:.1f})" text-anchor="middle" '
        f'letter-spacing="0.5">River</text>'
    )
    parts.append(
        f'<text x="{park_lx:.1f}" y="{park_ly:.1f}" font-size="15" '
        f'fill="#5E9C6E" font-style="italic" text-anchor="middle" '
        f'letter-spacing="0.5">Central Park</text>'
    )

    # ---- binned-grid layer ----
    parts.append('<g role="list" aria-label="square density bins">')
    gap = 1.4  # white casing between cells
    inner = cell_px - gap
    for c in cells:
        cnt = int(c["count"])
        if cnt <= 0:
            fill = _EMPTY
        else:
            fill = _ramp(cnt / max_count, red)
        label = (
            f'{cnt} incident{"" if cnt == 1 else "s"}'
            if cnt > 0
            else "no incidents"
        )
        parts.append(
            f'<rect class="cell" x="{c["x"] + gap / 2:.1f}" '
            f'y="{c["y"] + gap / 2:.1f}" width="{inner:.1f}" '
            f'height="{inner:.1f}" rx="2" fill="{fill}" stroke="{_STROKE}" '
            f'stroke-width="{gap:.1f}" tabindex="0" role="listitem">'
            f'<title>{label}</title></rect>'
        )
    parts.append('</g>')

    # ---- sequential legend (right column) ----
    lx = 992.0
    ly = 268.0
    parts.append(f'<g transform="translate({lx:.1f},{ly:.1f})">')
    parts.append(
        f'<text x="0" y="-24" font-size="20" font-weight="700" '
        f'fill="{_INK}">Incidents per cell</text>'
    )
    # A vertical ramp built from discrete swatches (self-contained, no
    # <defs> gradient) — top swatch = busiest.
    bar_w = 36.0
    seg_h = 34.0
    n_seg = 8
    for i in range(n_seg):
        t = 1.0 - i / (n_seg - 1)          # top swatch = darkest
        col = _ramp(t, red)
        parts.append(
            f'<rect class="legend-swatch" x="0" y="{i * seg_h:.1f}" '
            f'width="{bar_w}" height="{seg_h:.1f}" fill="{col}"/>'
        )
    # End labels on the ramp (labels sit outside the swatches, in ink).
    parts.append(
        f'<text x="{bar_w + 14:.1f}" y="12" font-size="18" fill="{_INK}" '
        f'font-family="Roboto Mono, monospace">{max_count}</text>'
    )
    parts.append(
        f'<text x="{bar_w + 14:.1f}" y="{n_seg * seg_h:.1f}" font-size="18" '
        f'fill="{_SUBTLE}" font-family="Roboto Mono, monospace" '
        f'dominant-baseline="ideographic">1</text>'
    )
    # An "empty" swatch below the ramp for zero-count land cells.
    empty_y = n_seg * seg_h + 30.0
    parts.append(
        f'<rect class="legend-swatch" x="0" y="{empty_y:.1f}" width="{bar_w}" '
        f'height="{seg_h:.1f}" fill="{_EMPTY}"/>'
    )
    parts.append(
        f'<text x="{bar_w + 14:.1f}" y="{empty_y + seg_h * 0.66:.1f}" '
        f'font-size="17" fill="{_SUBTLE}">no incidents</text>'
    )

    # ---- summary callout under the legend ----
    stat_y = empty_y + seg_h + 84.0
    busiest_share = 0
    if total and n_hit:
        # Share of incidents in the top-decile busiest occupied cells.
        sorted_cnt = sorted(counts, reverse=True)
        top_k = max(1, n_hit // 10)
        busiest_share = round(100.0 * sum(sorted_cnt[:top_k]) / total)
    parts.append(
        f'<text x="0" y="{stat_y:.1f}" font-size="54" font-weight="700" '
        f'fill="{red}">{busiest_share}%</text>'
    )
    parts.append(
        f'<text x="0" y="{stat_y + 34:.1f}" font-size="17.5" fill="{_SUBTLE}">'
        f'of incidents fall in the</text>'
    )
    parts.append(
        f'<text x="0" y="{stat_y + 56:.1f}" font-size="17.5" fill="{_SUBTLE}">'
        f'busiest 10% of cells</text>'
    )
    parts.append('</g>')

    # ---- cartographic furniture: north arrow + scale bar ----
    # Both sit on empty basemap in the map's right margin, clear of the dense
    # downtown cells, so they never crowd the data.
    na_x, na_y = _to_px([(0.905, 0.115)])[0]
    parts.append(_north_arrow(na_x, na_y, r=24.0))
    sb_x, sb_y = _to_px([(0.665, 0.955)])[0]
    parts.append(_scale_bar(sb_x, sb_y, cell_px))

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the binned-grid-map SVG to the skill's ``svg-examples`` folder."""
    render_cli(__file__, "binned-grid-map", build_svg, description="Render the binned-grid-map SVG.")


if __name__ == "__main__":
    main()

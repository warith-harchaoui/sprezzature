#!/usr/bin/env python3
"""
make_hexmap — a house-styled hexbin (hexagonal-binning) density map as a
hand-authored SVG.

A hexbin map answers "where are the points densest?" without drawing a
single overplotted dot. The map extent is tiled with pointy-top regular
hexagons; every raw point falls into exactly one hexagon; each hexagon is
shaded by the *count* of points it captured. Hexagons tile the plane
without the axis-aligned bias of a square grid, and each cell has six
equidistant neighbours, so the density surface reads more evenly than a
2-D histogram.

This module builds the SVG string by hand (no matplotlib / seaborn /
plotly, and no Vega because a hexagonal lattice clipped to a coastline is
clearer authored directly). It follows the sprezzature-* house style pulled
from :mod:`_style`: a single-hue sequential ramp keyed to the palette's
Blue, Roboto typography, ink ``#1D1D1F`` on a white background, rounded
title block, a takeaway title, and a one-line subtitle.

The figure is interactive without any JavaScript: hovering or
keyboard-focusing any hexagon lifts it with a crisp outline, and every
hexagon carries a native ``<title>`` tooltip reporting its trip count.
Motion is guarded by ``prefers-reduced-motion``. The point density is
generated deterministically (fixed seed) so re-running is reproducible.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/hexmap.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402


# ------------------------------------------------------------------
# Canvas + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. A generous, poster-like figure.
_WIDTH: int = 1280
_HEIGHT: int = 900

#: The plotting extent (the "map" rectangle) inside the canvas.
_MAP_X0: float = 64.0
_MAP_Y0: float = 168.0
_MAP_X1: float = 912.0
_MAP_Y1: float = 852.0

#: Hexagon circum-radius (centre to a pointy corner), in pixels. Sized so
#: the lattice is dense enough to read as a smooth density surface.
_HEX_R: float = 30.0

#: House-style inks.
_INK: str = "#1D1D1F"       # primary text
_SUBTLE: str = "#6E6E73"    # secondary text
_SEA: str = "#DCE7F4"       # water / out-of-extent fill (faint blue)
_LAND: str = "#FBFCFE"      # land silhouette under the hex lattice
_EMPTY: str = "#E9ECF1"     # a land hex that caught zero points
_STROKE: str = "#FFFFFF"    # white casing between hexes
_BG: str = "#FFFFFF"        # background
_FOCUS: str = "#0A4DA0"     # focus-ring blue

#: Reproducible point cloud.
_SEED: int = 20260725


# ------------------------------------------------------------------
# Sequential single-hue ramp (light -> palette Blue)
# ------------------------------------------------------------------
def _hex_to_rgb(hexv: str) -> Tuple[int, int, int]:
    """Convert ``#RRGGBB`` to an ``(r, g, b)`` integer triple."""
    h = hexv.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    """Convert an ``(r, g, b)`` triple (0-255 floats) back to ``#RRGGBB``."""
    r, g, b = (max(0, min(255, round(c))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def _ramp(t: float, top: str, *, light: Tuple[int, int, int] = (234, 240, 250)) -> str:
    """Interpolate a sequential single-hue ramp at position ``t`` in [0, 1].

    A pale tint at ``t = 0`` deepens to the saturated house Blue at
    ``t = 1``. A mild gamma pulls midtones apart so the busy cells stay
    visually distinct rather than all reading as "dark blue".

    Parameters
    ----------
    t : float
        Normalised count, clamped to ``[0, 1]``.
    top : str
        The darkest hex at ``t = 1`` (the palette's Blue).
    light : tuple of int, optional
        The lightest colour at ``t = 0``.

    Returns
    -------
    str
        A ``#RRGGBB`` hex string.
    """
    t = max(0.0, min(1.0, t))
    t = t ** 0.72  # gentle gamma so mid densities separate
    r1, g1, b1 = light
    r2, g2, b2 = _hex_to_rgb(top)
    return _rgb_to_hex((
        r1 + (r2 - r1) * t,
        g1 + (g2 - g1) * t,
        b1 + (b2 - b1) * t,
    ))


# ------------------------------------------------------------------
# Map extent — a stylised bay/coast so the hex lattice is clipped to
# an irregular "land" shape (a hexbin map is a *map*, not a rectangle).
# Coordinates are in the map-extent's own 0..1 square, y-down.
# ------------------------------------------------------------------
#: A closed coastline polygon in normalised [0, 1] extent coordinates.
#: A rounded landmass with a water inlet biting in from the lower-right,
#: evoking a coastal metro where downtown hugs the shore.
_COAST: List[Tuple[float, float]] = [
    (0.06, 0.10), (0.34, 0.04), (0.60, 0.08), (0.82, 0.06),
    (0.95, 0.18), (0.97, 0.40), (0.86, 0.52), (0.90, 0.70),
    (0.78, 0.86), (0.60, 0.80), (0.52, 0.92), (0.36, 0.96),
    (0.22, 0.90), (0.10, 0.74), (0.04, 0.52), (0.09, 0.30),
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


# ------------------------------------------------------------------
# Point cloud — a communicative density surface
# ------------------------------------------------------------------
#: Downtown / hotspot centres in extent coords, each a 2-D Gaussian blob
#: with a weight (how many of the sampled trips it draws) and a spread.
_HOTSPOTS: List[Tuple[float, float, float, float]] = [
    # (cx, cy, weight, sigma)
    (0.40, 0.34, 0.42, 0.09),   # downtown core (the peak)
    (0.58, 0.52, 0.24, 0.11),   # waterfront district
    (0.26, 0.60, 0.16, 0.12),   # university quarter
    (0.72, 0.24, 0.10, 0.10),   # airport / north gateway
]


def _sample_points(n: int, rng: random.Random) -> List[Tuple[float, float]]:
    """Draw ``n`` points from the mixture of hotspot Gaussians, kept on land.

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
        coastline polygon.
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
        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and _point_in_poly(x, y, _COAST):
            pts.append((x, y))
    return pts


# ------------------------------------------------------------------
# Hexagon lattice (pointy-top, axial layout)
# ------------------------------------------------------------------
def _hex_corners(cx: float, cy: float, r: float) -> List[Tuple[float, float]]:
    """Return the six corners of a pointy-top hexagon centred at ``(cx, cy)``."""
    pts = []
    for i in range(6):
        ang = math.pi / 180.0 * (60 * i - 90)  # -90 => a corner points up
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def _hex_path(cx: float, cy: float, r: float) -> str:
    """Return an SVG path ``d`` string for a pointy-top hexagon."""
    corners = _hex_corners(cx, cy, r)
    d = f"M{corners[0][0]:.2f},{corners[0][1]:.2f}"
    for x, y in corners[1:]:
        d += f" L{x:.2f},{y:.2f}"
    return d + "Z"


def _build_lattice() -> List[Dict[str, float]]:
    """Tile the map extent with pointy-top hexagons, keeping land cells.

    Returns
    -------
    list of dict
        One record per land hexagon with pixel centre ``px``/``py`` and
        the normalised-extent centre ``nx``/``ny`` (used to bin points).
    """
    r = _HEX_R
    hex_w = math.sqrt(3.0) * r          # width of a pointy-top hex
    v_step = 1.5 * r                    # vertical distance between rows
    ext_w = _MAP_X1 - _MAP_X0
    ext_h = _MAP_Y1 - _MAP_Y0

    cells: List[Dict[str, float]] = []
    row = 0
    py = _MAP_Y0 + r
    while py <= _MAP_Y1 - r * 0.2:
        # Odd rows shift right by half a hex width (offset lattice).
        x_off = (hex_w / 2.0) if (row % 2) else 0.0
        px = _MAP_X0 + hex_w / 2.0 + x_off
        while px <= _MAP_X1 - hex_w / 2.0 + 0.1:
            nx = (px - _MAP_X0) / ext_w
            ny = (py - _MAP_Y0) / ext_h
            if _point_in_poly(nx, ny, _COAST):
                cells.append({"px": px, "py": py, "nx": nx, "ny": ny})
            px += hex_w
        py += v_step
        row += 1
    return cells


def _bin_points(
    cells: List[Dict[str, float]],
    points: List[Tuple[float, float]],
) -> None:
    """Assign each point to its nearest hexagon centre, tallying counts.

    Mutates ``cells`` in place, adding a ``count`` key. Nearest-centre
    assignment in *pixel* space is exact for a regular hex lattice
    (a point's closest centre is the hexagon that contains it).

    Parameters
    ----------
    cells : list of dict
        The lattice from :func:`_build_lattice`.
    points : list of (float, float)
        Points in normalised extent coordinates.
    """
    ext_w = _MAP_X1 - _MAP_X0
    ext_h = _MAP_Y1 - _MAP_Y0
    for c in cells:
        c["count"] = 0.0
    for nx, ny in points:
        px = _MAP_X0 + nx * ext_w
        py = _MAP_Y0 + ny * ext_h
        best: Optional[Dict[str, float]] = None
        best_d = 1e18
        for c in cells:
            d = (c["px"] - px) ** 2 + (c["py"] - py) ** 2
            if d < best_d:
                best_d = d
                best = c
        if best is not None:
            best["count"] += 1.0


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


# ------------------------------------------------------------------
# SVG assembly
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full hexbin-map SVG document as a string.

    Parameters
    ----------
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
    palette = load_palette(accessibility)
    blue = palette.get("Blue", "#007AFF")

    rng = random.Random(_SEED)
    points = _sample_points(3200, rng)
    cells = _build_lattice()
    _bin_points(cells, points)

    counts = [int(c["count"]) for c in cells]
    max_count = max(counts) if counts else 1
    total = sum(counts)
    n_hex = len(cells)

    # ---- header ----
    parts: List[str] = []
    parts.append(svg_open(_WIDTH, _HEIGHT, "hx-title", "hx-desc"))
    parts.append(
        '<title id="hx-title">Bike-share trips pile up downtown, '
        'thin out at the edges</title>'
    )
    desc = (
        f"Hexbin density map: the coastal-metro service area is tiled with "
        f"{n_hex} regular hexagons, each shaded by the number of morning "
        f"bike-share trips that started inside it, from {total:,} trips in all. "
        f"The single-hue blue ramp runs from pale (few trips) to deep blue "
        f"(the busiest cell, {max_count} trips). Trips concentrate in the "
        f"downtown core and along the waterfront and fade toward the "
        f"suburban edge."
    )
    parts.append(f'<desc id="hx-desc">{desc}</desc>')

    # ---- interactivity (pure CSS, no JS) ----
    style_rows = [
        ".hex { transition: transform .16s ease, stroke .16s ease; "
        "transform-box: fill-box; transform-origin: center; }",
        # Lift and outline the hovered/focused cell so a single bin pops.
        f".hex:hover, .hex:focus {{ transform: scale(1.16); "
        f"stroke: {_INK}; stroke-width: 1.4; outline: none; }}",
        f".legend-swatch {{ stroke: {_STROKE}; stroke-width: 0.5; }}",
        "@media (prefers-reduced-motion: reduce) { .hex { transition: none; } "
        ".hex:hover, .hex:focus { transform: none; } }",
        # prefers-contrast (perceptual figure): strengthen STRUCTURE only — firm
        # up the white inter-hex casing to a visible grey so the lattice edges
        # read, deepen the secondary ink, and thicken the legend-swatch outlines.
        # The sequential trips-per-hex ramp is left untouched (re-spacing or
        # recolouring it would de-tune the encoding).
        "@media (prefers-contrast: more){"
        ".hex{stroke:#8E8E93;stroke-width:1;}"
        ".legend-swatch{stroke:#6E6E73;stroke-width:1;}"
        f'[fill="{_SUBTLE}"]{{fill:#3A3A3C;}}'
        f'[fill="{_EMPTY}"]{{fill:#C7CCD4;}}'
        "}",
    ]
    # Additive dark mode: flip paper + the two ink tiers, darken the two basemap
    # layers (land silhouette + zero-count hex) so the lattice reads on a dark
    # surface, and lift the hover outline (dark ink) to the light ink so a
    # focused cell still pops. The sequential trips-per-hex ramp is perceptual
    # and is left untouched.
    style_rows.append(
        os_dark_style(
            extra=(
                f'[fill="{_SEA}"]{{fill:#0E1626;}} '
                f'[fill="{_LAND}"]{{fill:#141618;}} '
                f'[fill="{_EMPTY}"]{{fill:#26262A;}} '
                ".hex:hover, .hex:focus{stroke:#F2F2F7;}"
            )
        )
    )
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_MAP_X0}" y="70" font-size="34" font-weight="700" '
        f'fill="{_INK}">Bike-share demand clusters on the downtown core</text>'
    )
    parts.append(
        f'<text x="{_MAP_X0}" y="106" font-size="20" fill="{_SUBTLE}">'
        f'Morning trips (7-10 AM) per hexagonal bin across the metro '
        f'service area · one hex ≈ 400 m · illustrative</text>'
    )

    # ---- water / extent backdrop (the coastline outline as "land base") ----
    ext_w = _MAP_X1 - _MAP_X0
    ext_h = _MAP_Y1 - _MAP_Y0
    parts.append(
        f'<rect x="{_MAP_X0:.1f}" y="{_MAP_Y0:.1f}" width="{ext_w:.1f}" '
        f'height="{ext_h:.1f}" rx="22" fill="{_SEA}"/>'
    )
    # The coastline path (land silhouette) as a faint casing under the hexes.
    coast_pts = [
        (_MAP_X0 + nx * ext_w, _MAP_Y0 + ny * ext_h) for nx, ny in _COAST
    ]
    coast_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in coast_pts) + "Z"
    parts.append(
        f'<path d="{coast_d}" fill="{_LAND}" stroke="#9FB4CE" '
        f'stroke-width="2" stroke-linejoin="round"/>'
    )

    # ---- hexbin layer ----
    parts.append('<g role="list" aria-label="hexagonal density bins">')
    r = _HEX_R
    for c in cells:
        cnt = int(c["count"])
        if cnt <= 0:
            fill = _EMPTY
        else:
            fill = _ramp(cnt / max_count, blue)
        d = _hex_path(c["px"], c["py"], r * 0.985)  # tiny gap => white casing
        label = (
            f'{cnt} trip{"" if cnt == 1 else "s"}'
            if cnt > 0
            else "no trips"
        )
        parts.append(
            f'<path class="hex" d="{d}" fill="{fill}" stroke="{_STROKE}" '
            f'stroke-width="1.6" tabindex="0" role="listitem">'
            f'<title>{label}</title></path>'
        )
    parts.append('</g>')

    # ---- sequential legend (right column) ----
    lx = 992.0
    ly = 268.0
    parts.append(f'<g transform="translate({lx:.1f},{ly:.1f})">')
    parts.append(
        f'<text x="0" y="-24" font-size="20" font-weight="700" '
        f'fill="{_INK}">Trips per hex</text>'
    )
    # A vertical gradient bar built from discrete swatches (self-contained,
    # no <defs> gradient needed) top = busiest.
    bar_w = 36.0
    seg_h = 34.0
    n_seg = 8
    for i in range(n_seg):
        t = 1.0 - i / (n_seg - 1)          # top swatch = darkest
        col = _ramp(t, blue)
        parts.append(
            f'<rect class="legend-swatch" x="0" y="{i * seg_h:.1f}" '
            f'width="{bar_w}" height="{seg_h:.1f}" fill="{col}"/>'
        )
    # End labels on the ramp.
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
        f'font-size="17" fill="{_SUBTLE}">no trips</text>'
    )

    # ---- summary callout under the legend ----
    stat_y = empty_y + seg_h + 84.0
    busiest_share = 0
    if total:
        # Share of trips in the top-decile busiest hexes.
        sorted_cnt = sorted(counts, reverse=True)
        top_k = max(1, n_hex // 10)
        busiest_share = round(100.0 * sum(sorted_cnt[:top_k]) / total)
    parts.append(
        f'<text x="0" y="{stat_y:.1f}" font-size="54" font-weight="700" '
        f'fill="{blue}">{busiest_share}%</text>'
    )
    parts.append(
        f'<text x="0" y="{stat_y + 34:.1f}" font-size="17.5" fill="{_SUBTLE}">'
        f'of trips start in the</text>'
    )
    parts.append(
        f'<text x="0" y="{stat_y + 56:.1f}" font-size="17.5" fill="{_SUBTLE}">'
        f'busiest 10% of hexes</text>'
    )
    parts.append('</g>')

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the hexbin-map SVG to the skill's ``svg-examples`` folder.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "hexmap",
        build_svg,
        description="Write the house-style hexbin-map SVG example.",
    )


if __name__ == "__main__":
    main()

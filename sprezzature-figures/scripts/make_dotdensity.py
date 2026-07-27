#!/usr/bin/env python3
"""
make_dotdensity — a house-styled dot-density map as a hand-authored SVG.

A dot-density (or *dot-distribution*) map places one dot per *N* units
of a count inside the polygon of the region it belongs to, scattering
the dots at random positions within the polygon. Because equal counts
occupy equal ink, the eye reads *density* directly: where the dots
crowd, the thing is concentrated; where the map goes bare, it is
sparse. Unlike a choropleth it is not fooled by big empty regions
(no "the whole of a large rural county looks important because it is
large") — the dots pile up only where the people actually are.

This example maps the resident population of metropolitan France:
**one dot per 25 000 residents**, dropped inside the department each
person lives in and tinted by the department's macro-region so the
coastal and Paris clusters read as coherent blocks. The takeaway is
the classic French geography lesson — people ring the coasts and pack
into the Paris basin, while the rural *diagonale du vide* running from
the Ardennes to the Pyrenees stays almost empty.

The module builds the SVG string by hand — no matplotlib / seaborn /
plotly, and no Vega (a scatter of tens of thousands of jittered points
clipped to real polygons is authored far more directly and compactly
as raw SVG). It follows the front-* house style pulled from
:mod:`_style`: the Apple-ish saturated palette, Roboto typography,
ink ``#1D1D1F`` on secondary ``#6E6E73`` on a white background,
rounded-corner legend chips, a takeaway title, and a one-line
subtitle.

Geometry is self-contained: the department polygons come from the
vendored ``assets/geo/fr/departements-simplifiee.geojson`` and are
projected with a plain equal-area-ish sinusoidal projection centred on
France (no pyproj dependency). Dots are rejection-sampled inside each
polygon with a deterministic seed, so the artifact is byte-stable
across runs. A native ``<title>`` per region gives a no-JavaScript
hover tooltip.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/dotdensity.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# Canvas + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Poster-scale so the Paris and
#: coastal clusters read at a glance and individual dots stay legible.
_WIDTH: int = 1240
_HEIGHT: int = 1000

#: Inner map viewport (leaves room for the header band and legend).
_MAP_X: float = 40.0
_MAP_Y: float = 150.0
_MAP_W: float = 830.0
_MAP_H: float = 810.0

#: House-style inks.
_INK: str = "#1D1D1F"       # primary text
_SUBTLE: str = "#6E6E73"    # secondary text
_BG: str = "#FFFFFF"        # background
_SEA: str = "#F2F2F7"       # land backdrop / graticule fill
_BORDER: str = "#D1D1D6"    # department hairlines

#: One dot represents this many residents.
_PER_DOT: int = 25_000

#: Dot radius, in pixels.
_DOT_R: float = 1.7

#: Deterministic RNG seed so the scatter is byte-stable across runs.
_SEED: int = 20260725


# ------------------------------------------------------------------
# Data — department → macro-region, and department populations
# ------------------------------------------------------------------
def _dataset() -> Tuple[Dict[str, int], Dict[str, str], List[Tuple[str, str]]]:
    """Return department populations, the region map, and the legend order.

    Populations are rounded illustrative figures in the neighbourhood of
    France's 2021 census by department (INSEE order of magnitude), used
    only to size the dot scatter — this is a teaching figure, not an
    official statistical release.

    Returns
    -------
    tuple
        ``(pop, region_of, legend)`` where

        * ``pop`` maps a two-character department code to its resident
          count,
        * ``region_of`` maps a department code to one of the six
          macro-regions used for colour, and
        * ``legend`` is the ``(region_name, palette_key)`` order for the
          legend and colour assignment.
    """
    # Six coarse macro-regions keep the colour legend readable while still
    # letting the coastal / Paris clusters read as blocks. Each maps to a
    # curated palette hue with a clear geographic mnemonic. Hues are chosen
    # for colour-vision-deficiency separability, not just prettiness: the
    # central belt, which physically borders both the Red north and the
    # Orange south, is Brown (a distinctly darker lightness) so it never
    # collapses into its warm neighbours under deuteranopia or in greyscale;
    # Green is parked on Corsica, an isolated island where no adjacency can
    # confuse it with the warm regions. Position already separates every
    # region, so hue only has to reinforce, never carry, the grouping.
    legend: List[Tuple[str, str]] = [
        ("Île-de-France & North", "Red"),
        ("Atlantic West", "Blue"),
        ("Mediterranean South", "Orange"),
        ("Rhône–Alps East", "Purple"),
        ("Central rural belt", "Brown"),
        ("Corsica", "Green"),
    ]

    # Department -> macro-region grouping (metropolitan France, 96 depts).
    groups: Dict[str, List[str]] = {
        "Île-de-France & North": [
            "75", "77", "78", "91", "92", "93", "94", "95",  # Île-de-France
            "59", "62", "60", "80", "02",                    # Hauts-de-France
            "51", "08", "10", "52", "54", "55", "57", "88",  # Grand Est (north)
            "67", "68",
        ],
        "Atlantic West": [
            "44", "49", "53", "72", "85",                    # Pays de la Loire
            "35", "22", "29", "56",                          # Brittany
            "14", "27", "50", "61", "76",                    # Normandy
            "17", "16", "79", "86", "87", "23", "19", "24",  # Nouvelle-Aquitaine (west)
            "33", "40", "47", "64",
        ],
        "Mediterranean South": [
            "13", "83", "84", "04", "05", "06",              # PACA
            "30", "34", "11", "66", "48",                    # Occitanie (east/coast)
            "09", "31", "32", "65", "81", "82", "12", "46",  # Occitanie (west)
        ],
        "Rhône–Alps East": [
            "69", "01", "07", "26", "38", "42", "43", "63",  # Auvergne-Rhône-Alpes
            "03", "15", "73", "74",
            "21", "25", "39", "58", "70", "71", "89", "90",  # Bourgogne-Franche-Comté
        ],
        "Central rural belt": [
            "18", "28", "36", "37", "41", "45",              # Centre-Val de Loire
        ],
        "Corsica": ["2A", "2B"],
    }
    region_of: Dict[str, str] = {}
    for region, codes in groups.items():
        for code in codes:
            region_of[code] = region

    # Illustrative resident populations (order of magnitude of the 2021
    # census), keyed by department code. Île-de-France and the big metros
    # carry the mass; the rural belt is deliberately thin.
    pop: Dict[str, int] = {
        # Île-de-France (packed).
        "75": 2_140_000, "92": 1_640_000, "93": 1_670_000, "94": 1_410_000,
        "78": 1_450_000, "91": 1_320_000, "95": 1_270_000, "77": 1_450_000,
        # Hauts-de-France + Grand Est north.
        "59": 2_610_000, "62": 1_470_000, "60": 830_000, "80": 570_000,
        "02": 530_000, "51": 570_000, "08": 270_000, "10": 310_000,
        "52": 170_000, "54": 730_000, "55": 180_000, "57": 1_050_000,
        "88": 360_000, "67": 1_140_000, "68": 770_000,
        # Atlantic West.
        "44": 1_430_000, "49": 820_000, "53": 310_000, "72": 570_000,
        "85": 690_000, "35": 1_090_000, "22": 600_000, "29": 910_000,
        "56": 760_000, "14": 700_000, "27": 600_000, "50": 490_000,
        "61": 280_000, "76": 1_250_000, "17": 650_000, "16": 350_000,
        "79": 380_000, "86": 440_000, "87": 370_000, "23": 116_000,
        "19": 240_000, "24": 410_000, "33": 1_640_000, "40": 410_000,
        "47": 330_000, "64": 680_000,
        # Mediterranean South.
        "13": 2_040_000, "83": 1_080_000, "84": 560_000, "04": 165_000,
        "05": 140_000, "06": 1_090_000, "30": 750_000, "34": 1_180_000,
        "11": 375_000, "66": 480_000, "48": 76_000, "09": 155_000,
        "31": 1_400_000, "32": 190_000, "65": 230_000, "81": 390_000,
        "82": 260_000, "12": 280_000, "46": 175_000,
        # Rhône–Alps East.
        "69": 1_880_000, "01": 660_000, "07": 330_000, "26": 520_000,
        "38": 1_270_000, "42": 765_000, "43": 227_000, "63": 660_000,
        "03": 335_000, "15": 145_000, "73": 440_000, "74": 830_000,
        "21": 535_000, "25": 545_000, "39": 260_000, "58": 200_000,
        "70": 235_000, "71": 550_000, "89": 335_000, "90": 140_000,
        # Central rural belt (thin).
        "18": 300_000, "28": 435_000, "36": 220_000, "37": 610_000,
        "41": 330_000, "45": 685_000,
        # Corsica.
        "2A": 160_000, "2B": 180_000,
    }

    return pop, region_of, legend


# ------------------------------------------------------------------
# Geometry helpers
# ------------------------------------------------------------------
Ring = List[Tuple[float, float]]


def _load_departments() -> List[Dict[str, object]]:
    """Load the vendored metropolitan-France department polygons.

    Returns
    -------
    list of dict
        One dict per department with ``code`` (str) and ``rings`` — a
        list of ``(part_index, ring)`` where every ring is a list of
        ``(lon, lat)`` tuples in degrees. Multipolygons keep the part
        index so exterior rings of different parts are not stitched
        together.
    """
    geo_path = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "geo"
        / "fr"
        / "departements-simplifiee.geojson"
    )
    fc = json.loads(geo_path.read_text(encoding="utf-8"))

    out: List[Dict[str, object]] = []
    for feat in fc["features"]:
        code = str(feat["properties"]["code"])
        geom = feat["geometry"]
        gtype = geom["type"]
        parts: List[Tuple[int, Ring]] = []
        if gtype == "Polygon":
            # coordinates = [exterior, hole, hole, ...]; keep only the
            # exterior for scatter/clip (holes are negligible at this scale).
            ring = [(float(x), float(y)) for x, y in geom["coordinates"][0]]
            parts.append((0, ring))
        elif gtype == "MultiPolygon":
            for i, poly in enumerate(geom["coordinates"]):
                ring = [(float(x), float(y)) for x, y in poly[0]]
                parts.append((i, ring))
        out.append({"code": code, "rings": parts})
    return out


def _project(lon: float, lat: float, lat0: float) -> Tuple[float, float]:
    """Sinusoidal (Sanson) projection in degrees, centred on ``lat0``.

    An equal-area projection keeps dot density honest — equal ground
    area maps to equal screen area, so the crowding of dots is a fair
    read of population density.

    Parameters
    ----------
    lon, lat : float
        Longitude / latitude in degrees.
    lat0 : float
        Reference latitude used to scale longitudes (the map centre).

    Returns
    -------
    tuple of float
        Planar ``(x, y)`` in an arbitrary unit; ``y`` points up. Callers
        fit these to the viewport with :func:`_fit`.
    """
    x = math.radians(lon) * math.cos(math.radians(lat))
    y = math.radians(lat)
    return x, y


def _fit(
    depts: List[Dict[str, object]], lat0: float
) -> Tuple[float, float, float, float, float]:
    """Compute the projection-to-viewport affine fit for all departments.

    Returns
    -------
    tuple
        ``(scale, offset_x, offset_y, min_px, min_py)`` — the uniform
        scale and offsets that map projected coordinates into the map
        viewport with a small inner margin, preserving aspect ratio.
    """
    pxs: List[float] = []
    pys: List[float] = []
    for d in depts:
        for _, ring in d["rings"]:  # type: ignore[assignment]
            for lon, lat in ring:
                px, py = _project(lon, lat, lat0)
                pxs.append(px)
                pys.append(py)
    min_px, max_px = min(pxs), max(pxs)
    min_py, max_py = min(pys), max(pys)
    span_x = max_px - min_px
    span_y = max_py - min_py
    pad = 10.0
    scale = min((_MAP_W - 2 * pad) / span_x, (_MAP_H - 2 * pad) / span_y)
    # Centre the map inside the viewport.
    draw_w = span_x * scale
    draw_h = span_y * scale
    offset_x = _MAP_X + (_MAP_W - draw_w) / 2.0
    offset_y = _MAP_Y + (_MAP_H - draw_h) / 2.0
    return scale, offset_x, offset_y, min_px, min_py


def _to_screen(
    lon: float,
    lat: float,
    lat0: float,
    fit: Tuple[float, float, float, float, float],
) -> Tuple[float, float]:
    """Project one ``(lon, lat)`` and map it into screen pixels.

    ``y`` is flipped so north is up on screen.
    """
    scale, offset_x, offset_y, min_px, min_py = fit
    px, py = _project(lon, lat, lat0)
    sx = offset_x + (px - min_px) * scale
    # Flip vertically: projected y grows north, screen y grows down.
    sy = offset_y + (_span_py * scale) - (py - min_py) * scale
    return sx, sy


# Filled in by build_svg once the projection span is known (kept module-level
# so _to_screen stays a small pure helper the audit tooling can read easily).
_span_py: float = 0.0


def _point_in_ring(x: float, y: float, ring: Ring) -> bool:
    """Ray-casting point-in-polygon test in projected space.

    Parameters
    ----------
    x, y : float
        Query point (projected units, same space as ``ring``).
    ring : list of (float, float)
        Closed polygon ring.

    Returns
    -------
    bool
        ``True`` if the point is inside the ring.
    """
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def _bbox(ring: Ring) -> Tuple[float, float, float, float]:
    """Return ``(min_x, min_y, max_x, max_y)`` of a projected ring."""
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _scatter(
    projected_parts: Sequence[Ring],
    n_dots: int,
    rng: random.Random,
) -> List[Tuple[float, float]]:
    """Rejection-sample ``n_dots`` points uniformly inside a (multi)polygon.

    Points are distributed across the polygon's parts in proportion to
    each part's bounding-box area, then rejection-sampled inside the
    actual ring so no dot lands in the sea.

    Parameters
    ----------
    projected_parts : sequence of ring
        The department's exterior rings, already in projected units.
    n_dots : int
        How many dots to place.
    rng : random.Random
        Seeded RNG for byte-stable output.

    Returns
    -------
    list of (float, float)
        Projected ``(x, y)`` sample points.
    """
    boxes = [_bbox(r) for r in projected_parts]
    weights = [max((b[2] - b[0]) * (b[3] - b[1]), 1e-12) for b in boxes]
    pts: List[Tuple[float, float]] = []
    for _ in range(n_dots):
        # Pick a part weighted by its bbox area, then rejection-sample.
        part_idx = _weighted_choice(weights, rng)
        ring = projected_parts[part_idx]
        min_x, min_y, max_x, max_y = boxes[part_idx]
        for _try in range(60):
            x = rng.uniform(min_x, max_x)
            y = rng.uniform(min_y, max_y)
            if _point_in_ring(x, y, ring):
                pts.append((x, y))
                break
    return pts


def _weighted_choice(weights: Sequence[float], rng: random.Random) -> int:
    """Return an index chosen with probability proportional to ``weights``."""
    total = sum(weights)
    r = rng.uniform(0.0, total)
    upto = 0.0
    for i, w in enumerate(weights):
        upto += w
        if r <= upto:
            return i
    return len(weights) - 1


# ------------------------------------------------------------------
# SVG assembly helpers
# ------------------------------------------------------------------
# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def _slug(label: str) -> str:
    """Turn a region label into a CSS-class-safe slug."""
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in label).strip("-")


def _ring_path(ring: Ring, lat0: float, fit: Tuple[float, float, float, float, float]) -> str:
    """Build an SVG path ``d`` string for one department ring."""
    cmds: List[str] = []
    for k, (lon, lat) in enumerate(ring):
        sx, sy = _to_screen(lon, lat, lat0, fit)
        cmds.append(f"{'M' if k == 0 else 'L'}{sx:.1f},{sy:.1f}")
    cmds.append("Z")
    return "".join(cmds)


# ------------------------------------------------------------------
# Build
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full dot-density-map SVG document as a string.

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
    global _span_py

    palette = load_palette(accessibility)
    pop, region_of, legend = _dataset()
    region_color = {name: palette[key] for name, key in legend}

    depts = _load_departments()
    lat0 = 46.6  # roughly the latitudinal centre of metropolitan France

    # Fit the projection to the viewport.
    fit = _fit(depts, lat0)
    scale, offset_x, offset_y, min_px, min_py = fit
    # Vertical span of the projection (for the north-up flip in _to_screen).
    pys = [
        _project(lon, lat, lat0)[1]
        for d in depts
        for _, ring in d["rings"]  # type: ignore[misc]
        for lon, lat in ring
    ]
    _span_py = max(pys) - min(pys)

    rng = random.Random(_SEED)

    # ---- header ----
    parts: List[str] = []
    parts.append(svg_open(_WIDTH, _HEIGHT, "dd-title", "dd-desc"))
    parts.append(
        '<title id="dd-title">Where the French actually live — one dot per '
        '25,000 residents</title>'
    )
    total = sum(pop.values())
    desc = (
        "Dot-density map of metropolitan France. Each dot is 25,000 "
        "residents, scattered at random inside the department they live "
        "in and coloured by macro-region. Dots crowd around Paris and along "
        "the Atlantic and Mediterranean coasts; the rural diagonal from the "
        "Ardennes to the Pyrenees stays nearly empty. "
        f"About {total // 1_000_000} million residents in total."
    )
    parts.append(f'<desc id="dd-desc">{desc}</desc>')

    # ---- interactivity + house style (pure CSS, no JS) ----
    style_rows = [
        ".dept { transition: fill-opacity .18s ease; }",
        ".dots { transition: opacity .18s ease; }",
        # Hovering / focusing any region dims the other regions' dots.
        "svg:hover .rg, svg:focus-within .rg { opacity: .12; }",
    ]
    for name, _ in legend:
        s = _slug(name)
        style_rows.append(
            f".rg-{s}:hover, .rg-{s}:focus, "
            f".rg-{s}:hover .rg-{s}, .rg-{s}:focus .rg-{s} {{ opacity: 1; }}"
        )
    style_rows.extend([
        ".legend-row { cursor: pointer; }",
        ".legend-row:focus { outline: 3px solid #0A4DA0; outline-offset: 2px; }",
        "@media (prefers-reduced-motion: reduce) { "
        ".dept, .dots { transition: none; } }",
    ])
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside an @media query — a descendant
    # class rule only outranks the inline circle fill once the query matches).
    # The six macro-regions deepen to their high-contrast hues under
    # prefers-contrast, on both the map dots and their legend swatches.
    # forced=True is safe: geographic position already separates every region
    # (Corsica, Paris, the coasts) and each carries an always-visible legend
    # label, so identity survives with no colour.
    region_series = {
        f".rg-{_slug(name)} circle": region_color[name] for name, _ in legend
    }
    style_rows.append(os_adaptive_style(region_series, role="fill", forced=True))
    # Additive dark mode: flip paper + the two ink tiers (data hues untouched).
    style_rows.append(os_dark_style())
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_MAP_X}" y="66" font-size="34" font-weight="700" '
        f'fill="{_INK}">Where the French actually live</text>'
    )
    parts.append(
        f'<text x="{_MAP_X}" y="102" font-size="20" fill="{_SUBTLE}">'
        f'One dot = 25,000 residents · people ring the coasts and pack the '
        f'Paris basin, leaving the rural diagonal bare</text>'
    )

    # ---- land backdrop: department polygons (hairline borders) ----
    # Group department paths by region so the fill tints the block subtly and
    # the dots sit on a faint same-hue wash.
    parts.append('<g class="depts">')
    for d in depts:
        code = str(d["code"])
        region = region_of.get(code)
        if region is None:
            continue
        color = region_color[region]
        s = _slug(region)
        for _, ring in d["rings"]:  # type: ignore[misc]
            path = _ring_path(ring, lat0, fit)
            parts.append(
                f'<path class="dept" d="{path}" fill="{color}" '
                f'fill-opacity="0.06" stroke="{_BORDER}" '
                f'stroke-width="0.7"/>'
            )
    parts.append('</g>')

    # ---- dot layers, one <g> per region for hover isolation ----
    # Precompute projected rings once per department.
    proj_rings: Dict[str, List[Ring]] = {}
    for d in depts:
        code = str(d["code"])
        rings_p: List[Ring] = []
        for _, ring in d["rings"]:  # type: ignore[misc]
            rings_p.append([_project(lon, lat, lat0) for lon, lat in ring])
        proj_rings[code] = rings_p

    # Collect region → list of screen-space dots (scatter in projected space,
    # then map to screen — cheaper and keeps density honest).
    region_dots: Dict[str, List[Tuple[float, float]]] = {
        name: [] for name, _ in legend
    }
    region_people: Dict[str, int] = {name: 0 for name, _ in legend}
    for d in depts:
        code = str(d["code"])
        region = region_of.get(code)
        if region is None or code not in pop:
            continue
        region_people[region] += pop[code]
        n_dots = max(1, round(pop[code] / _PER_DOT))
        samples = _scatter(proj_rings[code], n_dots, rng)
        for px, py in samples:
            sx = offset_x + (px - min_px) * scale
            sy = offset_y + (_span_py * scale) - (py - min_py) * scale
            region_dots[region].append((sx, sy))

    for name, _key in legend:
        s = _slug(name)
        color = region_color[name]
        people = region_people[name]
        parts.append(
            f'<g class="dots rg rg-{s}" tabindex="0" role="listitem">'
            f'<title>{_xml(name)}: about {people / 1_000_000:.1f} million '
            f'residents ({len(region_dots[name])} dots)</title>'
        )
        # One compact <circle> per dot. fill-opacity lets overlapping dots
        # darken where density is highest — reinforcing the density read.
        for sx, sy in region_dots[name]:
            parts.append(
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{_DOT_R}" '
                f'fill="{color}" fill-opacity="0.55"/>'
            )
        parts.append('</g>')

    # ---- legend (right column) ----
    legend_x = _MAP_X + _MAP_W + 44.0
    legend_y = _MAP_Y + 40.0
    row_h = 62.0
    parts.append(
        f'<text x="{legend_x:.1f}" y="{legend_y - 34:.1f}" font-size="17" '
        f'font-weight="700" fill="{_INK}">Macro-region</text>'
    )
    parts.append(f'<g transform="translate({legend_x:.1f},{legend_y:.1f})">')
    for k, (name, _key) in enumerate(legend):
        s = _slug(name)
        color = region_color[name]
        cy = k * row_h
        people = region_people[name]
        parts.append(
            f'<g class="rg rg-{s} legend-row" tabindex="0" role="listitem" '
            f'transform="translate(0,{cy:.1f})">'
            f'<title>{_xml(name)}: about {people / 1_000_000:.1f} million '
            f'residents</title>'
        )
        parts.append(
            f'<circle cx="11" cy="8" r="10" fill="{color}" '
            f'fill-opacity="0.92"/>'
        )
        parts.append(
            f'<text x="34" y="5" font-size="18" font-weight="600" '
            f'fill="{_INK}" dominant-baseline="middle">{_xml(name)}</text>'
        )
        parts.append(
            f'<text x="34" y="28" font-size="15" fill="{_SUBTLE}" '
            f'dominant-baseline="middle">'
            f'{people / 1_000_000:.1f} M residents</text>'
        )
        parts.append('</g>')
    parts.append('</g>')

    # ---- footnote / method note ----
    parts.append(
        f'<text x="{_MAP_X}" y="{_HEIGHT - 20}" font-size="14" '
        f'fill="{_SUBTLE}">Dots randomly placed within each department, '
        f'not at real addresses · illustrative figures · '
        f'equal-area projection</text>'
    )

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the dot-density-map SVG to the skill's ``svg-examples`` folder.

    The ``--mode`` flag selects the interactivity mode of the emitted SVG
    (``self-contained`` / ``external`` / ``static``); see
    :func:`_interactive.fullscreen_control`.
    """
    render_cli(
        __file__, "dotdensity", build_svg, description="Render the dot-density-map SVG."
    )


if __name__ == "__main__":
    main()

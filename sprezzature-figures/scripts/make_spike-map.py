#!/usr/bin/env python3
"""
make_spike-map — a house-styled spike map as a hand-authored SVG.

A *spike map* encodes a per-location quantity as the **height of a
vertical spike** planted at that place on a projected basemap. Because
every spike shares the same footprint and grows only upward, the eye
compares heights along a single common baseline — the most honest
one-dimensional comparison there is (Cleveland & McGill rank *position
along a common scale* above area, angle, and colour). Against a faint
land silhouette the spikes read like a skyline: where the ink is tall,
the quantity is large; where the map is flat, it is small.

This example plants one spike at each of the world's largest **urban
agglomerations**, spike height ∝ metropolitan population (2024 order of
magnitude, United Nations World Urbanization Prospects). The takeaway
is the shape of the century's urban century: the tallest skyline stands
over East and South Asia — Tokyo, Delhi, Shanghai — while the Americas,
Africa and Europe carry shorter, sparser spikes.

The module builds the SVG string by hand — no matplotlib / seaborn /
plotly, and no Vega (a projected basemap overlaid with hundreds of
hand-placed spikes, a size legend, and side-aware city labels is
authored far more directly and compactly as raw SVG). It follows the
front-* house style pulled from :mod:`_style`: the Apple-ish saturated
palette, Roboto typography, ink ``#1D1D1F`` on secondary ``#6E6E73`` on
a white background, rounded-corner legend chips, a takeaway title, and a
one-line subtitle.

Geometry is self-contained: the land silhouette comes from the vendored
``assets/geo/countries-110m.json`` TopoJSON and is drawn with a pure
closed-form **Equal Earth** projection (Šavrič, Patterson & Jenny 2018)
— an equal-area projection whose pleasing globe-like curvature reads as
a proper world map, no pyproj dependency. A native ``<title>`` per
spike gives a no-JavaScript hover tooltip, and CSS ``:hover`` lifts the
hovered spike out of the skyline.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/spike-map.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import List, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import svg_example_path, write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# Canvas + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Poster-scale so the skyline of
#: spikes and the city labels stay crisp at a glance.
_WIDTH: int = 1480
_HEIGHT: int = 940

#: Inner map viewport (leaves room for the header band and footnote).
_MAP_X: float = 30.0
_MAP_Y: float = 200.0
_MAP_W: float = 1420.0
_MAP_H: float = 660.0

#: House-style inks.
_INK: str = "#1D1D1F"       # primary text
_SUBTLE: str = "#6E6E73"    # secondary text
_BG: str = "#FFFFFF"        # background
_LAND: str = "#EDEDF2"      # faint land silhouette
_LAND_EDGE: str = "#DDDDE3"  # land hairline
_GRAT: str = "#F4F4F7"      # graticule / ocean grid

#: The spike ink — a single saturated hue keeps the skyline coherent.
_SPIKE_KEY: str = "Red"

#: The tallest spike may not rise above this screen-y (its tip clears
#: the title / subtitle band). :func:`_spike_scale` picks the pixels-
#: per-million so the worst-case spike (tallest population on the
#: highest base) just kisses this ceiling; the encoding stays linear.
_TIP_CEILING: float = 138.0

#: Hard cap on the tallest spike, in pixels, so a low-latitude giant
#: cannot grow into an absurdly long needle even when it has headroom.
_MAX_SPIKE_PX: float = 300.0

#: Half-width of a spike's base triangle, in pixels.
_SPIKE_HALF: float = 4.6


# ------------------------------------------------------------------
# Data — the world's largest urban agglomerations
# ------------------------------------------------------------------
#: ``(name, lon, lat, population_millions, label_side)``. Populations
#: are rounded 2024-order-of-magnitude metropolitan figures (United
#: Nations World Urbanization Prospects), used only to size the spikes —
#: a teaching figure, not an official statistical release. The trailing
#: ``"L"`` / ``"R"`` is a hint kept next to each city for readability;
#: the label side actually rendered comes from :data:`_LABELLED`, which
#: is hand-tuned so no two name labels collide.
_CITIES: List[Tuple[str, float, float, float, str]] = [
    ("Tokyo",         139.69,  35.68, 37.1, "R"),
    ("Delhi",          77.10,  28.70, 33.8, "R"),
    ("Shanghai",      121.47,  31.23, 29.9, "R"),
    ("Dhaka",          90.41,  23.81, 24.7, "R"),
    ("São Paulo",     -46.63, -23.55, 22.8, "L"),
    ("Cairo",          31.24,  30.04, 22.6, "R"),
    ("Mexico City",   -99.13,  19.43, 22.3, "L"),
    ("Beijing",       116.41,  39.90, 22.2, "R"),
    ("Mumbai",         72.88,  19.08, 21.7, "L"),
    ("Osaka",         135.50,  34.69, 19.0, "R"),
    ("New York",      -74.01,  40.71, 18.9, "L"),
    ("Karachi",        67.01,  24.86, 17.6, "L"),
    ("Chongqing",     106.55,  29.56, 17.3, "R"),
    ("Istanbul",       28.98,  41.01, 16.0, "R"),
    ("Buenos Aires",  -58.38, -34.60, 15.6, "L"),
    ("Kolkata",        88.36,  22.57, 15.6, "R"),
    ("Kinshasa",       15.31,  -4.32, 15.6, "L"),
    ("Lagos",           3.39,   6.52, 15.4, "L"),
    ("Manila",        120.98,  14.60, 14.9, "R"),
    ("Guangzhou",     113.26,  23.13, 14.6, "R"),
    ("Los Angeles",  -118.24,  34.05, 12.9, "L"),
    ("Moscow",         37.62,  55.75, 12.7, "R"),
    ("Rio de Janeiro", -43.20, -22.91, 12.6, "L"),
    ("Shenzhen",      114.06,  22.54, 12.4, "R"),
    ("Lahore",         74.36,  31.55, 12.3, "R"),
    ("Bangalore",      77.59,  12.97, 12.3, "R"),
    ("Paris",           2.35,  48.86, 11.2, "L"),
    ("Jakarta",       106.85,  -6.21, 11.1, "R"),
    ("Chennai",        80.27,  13.08, 11.0, "R"),
    ("London",         -0.13,  51.51,  9.7, "L"),
    ("Bangkok",       100.50,  13.76,  10.9, "R"),
    ("Tehran",         51.39,  35.69,  9.6, "R"),
    ("Bogotá",        -74.07,   4.71, 11.3, "L"),
    ("Ho Chi Minh City", 106.66, 10.82, 9.3, "R"),
    ("Hyderabad",      78.49,  17.39, 10.5, "R"),
    ("Chengdu",       104.07,  30.57, 10.4, "R"),
    ("Nagoya",        136.91,  35.18,  9.6, "R"),
    ("Tianjin",       117.20,  39.08, 14.0, "R"),
    ("Lima",          -77.04, -12.05, 11.2, "L"),
    ("Wuhan",         114.30,  30.59,  9.8, "R"),
    ("Nanjing",       118.80,  32.06,  9.4, "R"),
    ("Luanda",         13.23,  -8.84,  9.3, "L"),
    ("Chicago",       -87.63,  41.88,  8.9, "L"),
    ("Kuala Lumpur",  101.69,   3.14,  8.6, "R"),
    ("Hangzhou",      120.16,  30.29, 10.7, "R"),
    ("Hong Kong",     114.17,  22.32,  7.6, "R"),
    ("Ahmedabad",      72.57,  23.03,  8.9, "L"),
    ("Baghdad",        44.36,  33.31,  7.7, "R"),
    ("Riyadh",         46.72,  24.71,  7.7, "R"),
    ("Santiago",      -70.65, -33.46,  6.9, "L"),
    ("Madrid",         -3.70,  40.42,  6.7, "L"),
    ("Toronto",       -79.38,  43.65,  6.6, "L"),
    ("Johannesburg",   28.05, -26.20,  6.2, "R"),
    ("Dar es Salaam",  39.28,  -6.79,  7.8, "R"),
    ("Barcelona",       2.15,  41.39,  5.7, "L"),
    ("Sydney",        151.21, -33.87,  5.3, "R"),
    ("Nairobi",        36.82,  -1.29,  5.3, "R"),
    ("Berlin",         13.40,  52.52,  4.9, "L"),
    ("Khartoum",       32.53,  15.50,  6.2, "R"),
    ("Addis Ababa",    38.74,   9.03,  5.5, "R"),
]

#: Cities we call out with a name label, mapped to the side the label
#: sits on ("L" / "R", the empty side of that spike). The set is kept
#: deliberately sparse and spread out so no two labels collide; the rest
#: of the skyline stays unlabelled so the poster does not choke on text.
_LABELLED: dict[str, str] = {
    "Tokyo":        "L",
    "Delhi":        "R",
    "São Paulo":    "L",
    "New York":     "L",
    "Lagos":        "L",
    "Moscow":       "R",
    "Jakarta":      "R",
    "London":       "L",
    "Los Angeles":  "L",
    "Mexico City":  "R",
    "Buenos Aires": "L",
    "Sydney":       "R",
}


# ------------------------------------------------------------------
# TopoJSON basemap loading
# ------------------------------------------------------------------
Ring = List[Tuple[float, float]]


def _load_land_rings() -> List[Ring]:
    """Decode the vendored world land silhouette from TopoJSON.

    The minimal TopoJSON contract of ``countries-110m.json``: quantised,
    delta-encoded arcs plus a ``scale`` / ``translate`` transform,
    stitched into closed lon/lat rings. We use the ``land`` object (a
    single fused silhouette) so no internal country borders clutter the
    faint backdrop under the spikes.

    Returns
    -------
    list of ring
        One list of ``(lon, lat)`` tuples (degrees) per land ring.
    """
    geo_path = (
        Path(__file__).resolve().parent.parent / "assets" / "geo" / "countries-110m.json"
    )
    topo = json.loads(geo_path.read_text(encoding="utf-8"))
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    def decode_arc(index: int) -> List[Tuple[float, float]]:
        # A negative index means the arc is traversed in reverse (~index).
        reverse = index < 0
        arc = raw_arcs[~index if reverse else index]
        pts: List[Tuple[float, float]] = []
        x = y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * scale[0] + translate[0], y * scale[1] + translate[1]))
        return pts[::-1] if reverse else pts

    def stitch(arc_indices: List[int]) -> Ring:
        ring: Ring = []
        for j, idx in enumerate(arc_indices):
            pts = decode_arc(idx)
            ring.extend(pts if j == 0 else pts[1:])
        return ring

    rings: List[Ring] = []
    for geom in topo["objects"]["land"]["geometries"]:
        gtype = geom["type"]
        if gtype == "Polygon":
            for part in geom["arcs"]:
                rings.append(stitch(part))
        elif gtype == "MultiPolygon":
            for poly in geom["arcs"]:
                for part in poly:
                    rings.append(stitch(part))
    return rings


# ------------------------------------------------------------------
# Equal Earth projection (Šavrič, Patterson & Jenny 2018)
# ------------------------------------------------------------------
# Closed-form equal-area world projection; pleasant globe-like curvature.
# Polynomial constants from the original paper.
_A1, _A2, _A3, _A4 = 1.340264, -0.081106, 0.000893, 0.003796
_M = math.sqrt(3.0) / 2.0


def _equal_earth(lon: float, lat: float) -> Tuple[float, float]:
    """Project ``(lon, lat)`` in degrees to Equal Earth planar ``(x, y)``.

    Parameters
    ----------
    lon, lat : float
        Longitude / latitude in degrees.

    Returns
    -------
    tuple of float
        Planar ``(x, y)`` in projection units; ``y`` points up. Callers
        fit these to the viewport with :func:`_fit`.
    """
    lam = math.radians(lon)
    phi = math.radians(lat)
    # Parametric latitude.
    theta = math.asin(_M * math.sin(phi))
    t2 = theta * theta
    t6 = t2 * t2 * t2
    x = (
        2.0 * math.sqrt(3.0) * lam * math.cos(theta)
        / (3.0 * (_A1 + 3.0 * _A2 * t2 + t6 * (7.0 * _A3 + 9.0 * _A4 * t2)))
    )
    y = theta * (_A1 + _A2 * t2 + t6 * (_A3 + _A4 * t2))
    return x, y


def _fit(rings: List[Ring]) -> Tuple[float, float, float, float, float]:
    """Compute the projection-to-viewport affine fit for the whole map.

    Returns
    -------
    tuple
        ``(scale, offset_x, offset_y, min_px, span_py)`` — the uniform
        scale and offsets that map projected coordinates into the map
        viewport with a small inner margin, preserving aspect ratio.
    """
    pxs: List[float] = []
    pys: List[float] = []
    for ring in rings:
        for lon, lat in ring:
            px, py = _equal_earth(lon, lat)
            pxs.append(px)
            pys.append(py)
    min_px, max_px = min(pxs), max(pxs)
    min_py, max_py = min(pys), max(pys)
    span_x = max_px - min_px
    span_y = max_py - min_py
    pad = 8.0
    scale = min((_MAP_W - 2 * pad) / span_x, (_MAP_H - 2 * pad) / span_y)
    draw_w = span_x * scale
    draw_h = span_y * scale
    offset_x = _MAP_X + (_MAP_W - draw_w) / 2.0
    # Nudge the map slightly up in its box so the tallest spikes have
    # headroom to the title band rather than the footnote.
    offset_y = _MAP_Y + (_MAP_H - draw_h) / 2.0
    return scale, offset_x, offset_y, min_px, span_y


def _to_screen(
    lon: float, lat: float, fit: Tuple[float, float, float, float, float]
) -> Tuple[float, float]:
    """Project one ``(lon, lat)`` and map it into screen pixels (north up)."""
    scale, offset_x, offset_y, min_px, span_py = fit
    px, py = _equal_earth(lon, lat)
    min_py = _min_py  # module-level, set by build_svg
    sx = offset_x + (px - min_px) * scale
    sy = offset_y + (span_py * scale) - (py - min_py) * scale
    return sx, sy


# Filled by build_svg once the projection span is known.
_min_py: float = 0.0


# ------------------------------------------------------------------
# SVG assembly helpers
# ------------------------------------------------------------------
_xml = xml_escape


def _ring_path(ring: Ring, fit: Tuple[float, float, float, float, float]) -> str:
    """Build an SVG path ``d`` string for one land ring."""
    cmds: List[str] = []
    for k, (lon, lat) in enumerate(ring):
        sx, sy = _to_screen(lon, lat, fit)
        cmds.append(f"{'M' if k == 0 else 'L'}{sx:.1f},{sy:.1f}")
    cmds.append("Z")
    return "".join(cmds)


def _graticule_paths(fit: Tuple[float, float, float, float, float]) -> List[str]:
    """Return faint meridian / parallel arcs for the ocean grid."""
    paths: List[str] = []
    # Parallels every 30° from -60 to 60.
    for lat in range(-60, 61, 30):
        pts = [_to_screen(lon, lat, fit) for lon in range(-180, 181, 5)]
        d = "".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
        paths.append(d)
    # Meridians every 60°.
    for lon in range(-180, 181, 60):
        pts = [_to_screen(lon, lat, fit) for lat in range(-85, 86, 5)]
        d = "".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
        paths.append(d)
    return paths


def _spike_scale(fit: Tuple[float, float, float, float, float]) -> float:
    """Return the pixels-per-million so the skyline clears the header.

    Finds the city whose spike would rise highest — the one that
    maximises ``base_screen_y - population`` weighting — and sizes the
    common scale so its tip lands exactly on :data:`_TIP_CEILING`, then
    clamps the tallest spike to :data:`_MAX_SPIKE_PX`. Linear for every
    city, so equal populations still make equal-height spikes.

    Parameters
    ----------
    fit : tuple
        The projection-to-viewport fit from :func:`_fit`.

    Returns
    -------
    float
        Pixels of spike height per million residents.
    """
    # For each city, the scale that would put its tip on the ceiling.
    per_city = []
    for _name, lon, lat, pop, _side in _CITIES:
        _bx, by = _to_screen(lon, lat, fit)
        per_city.append((by - _TIP_CEILING) / pop)
    # The smallest such scale keeps every tip at or below the ceiling.
    scale = min(per_city)
    max_pop = max(c[3] for c in _CITIES)
    # Clamp so the tallest spike never exceeds the hard pixel cap.
    return min(scale, _MAX_SPIKE_PX / max_pop)


# ------------------------------------------------------------------
# Build
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full spike-map SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode for the fullscreen control, one of three:
        ``"self-contained"`` (default) ships a self-carrying fullscreen
        button plus its wiring script; ``"external"`` ships no button and
        defers fullscreen to a page-level module; ``"static"`` ships no
        interactivity at all.
    accessibility : str, optional
        Palette accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). Defaults to ``"universal"``, the
        colour-vision-safe standard, which leaves the shipped palette
        unchanged.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    global _min_py

    palette = load_palette(accessibility)
    spike_color = palette[_SPIKE_KEY]

    rings = _load_land_rings()
    fit = _fit(rings)
    scale, offset_x, offset_y, min_px, span_py = fit
    # Recover min_py from a fresh projection pass (kept out of the fit
    # tuple to keep _to_screen a small pure helper).
    pys = [_equal_earth(lon, lat)[1] for ring in rings for lon, lat in ring]
    _min_py = min(pys)

    # Pick the pixels-per-million so the worst-case spike (tallest
    # population sitting on the highest base) just reaches _TIP_CEILING,
    # then clamp so no single needle exceeds _MAX_SPIKE_PX. This keeps
    # the height↔population map strictly linear while guaranteeing the
    # skyline never crosses the header band.
    px_per_m = _spike_scale(fit)

    # ---- header scaffold ----
    parts: List[str] = []
    parts.append(svg_open(_WIDTH, _HEIGHT, "sm-title", "sm-desc"))
    parts.append(
        '<title id="sm-title">The world\'s tallest skyline of people stands '
        'over Asia — spike height is metropolitan population</title>'
    )
    desc = (
        "Spike map of the world's largest urban agglomerations. A vertical "
        "spike is planted at each city; its height is proportional to the "
        "metropolitan population (2024 order of magnitude, United Nations "
        "World Urbanization Prospects). Hover or focus a spike to read its "
        "city and population; its neighbours dim so the skyline is explorable. "
        "The tallest spikes cluster over East and South Asia — Tokyo (37 "
        "million), Delhi (34 million) and Shanghai (30 million) — while the "
        "Americas, Africa and Europe carry shorter, sparser spikes."
    )
    parts.append(f'<desc id="sm-desc">{desc}</desc>')

    # ---- interactivity (pure CSS + native <title>, no JS) ----
    # Same idiom as the interactive-bar example: a native <title> per spike
    # gives an OS tooltip with zero JavaScript, and CSS :hover / :focus makes
    # the skyline explorable — hover any spike and its neighbours dim so the
    # eye lands on one, while a small value flag rises above the hovered spike.
    style_rows = [
        ".spike { cursor: pointer; transition: opacity .16s ease, filter .16s ease; }",
        # Hovering or focusing anywhere in the skyline fades every spike back,
        # so the one under the pointer reads clearly out of the Asian cluster.
        "svg:hover .spike, svg:focus-within .spike { opacity: .28; }",
        # The spike actually under the pointer / keyboard focus stays full and
        # brightens a touch so it lifts out of the dimmed skyline.
        ".spike:hover, .spike:focus { opacity: 1; filter: brightness(0.86); }",
        # Fatten the tip disc of the active spike so the target is obvious.
        ".spike:hover .cap, .spike:focus .cap { r: 4.6; }",
        # A visible keyboard focus ring on the tip disc (accessibility).
        ".spike:focus { outline: none; }",
        ".spike:focus .cap { stroke: #0A4DA0; stroke-width: 2; }",
        # The per-spike value flag is hidden at rest and only appears for the
        # active spike, so the resting poster stays uncluttered.
        ".flag { opacity: 0; transition: opacity .16s ease; pointer-events: none; }",
        ".spike:hover .flag, .spike:focus .flag { opacity: 1; }",
        "@media (prefers-reduced-motion: reduce) { "
        ".spike, .flag { transition: none; } }",
    ]
    # OS-adaptive override (additive; the default render stays byte-identical
    # because the rule lives inside a media query). This is a single-hue figure
    # — the data is carried by spike HEIGHT along a common baseline, and every
    # spike shares one red ink — so there is no category to preserve and forced
    # colours are left to the browser default. Under prefers-contrast the one
    # spike hue deepens to its high-contrast red on the map spikes (triangle
    # body, stem and tip disc, via role "both") and the legend reference
    # spikes, so the skyline reads harder against the faint land silhouette.
    # The hover flag chips stay ink-on-white and untouched.
    spike_sel = (
        ".spike path, .spike line, .spike circle, .legspike"
    )
    contrast_css = os_adaptive_style({spike_sel: spike_color}, role="both")
    # Additive OS dark-mode block. The near-white land silhouette (#EDEDF2 fill /
    # #DDDDE3 edge) and the faint ocean graticule (#F4F4F7) would glare as bright
    # shapes on a dark page, so they are remapped to quiet dark greys that still
    # give the skyline a base to stand on. The white page + legend chips darken
    # via the ink-map default and their ink text flips to light; the single red
    # spike hue is data and untouched. No multiply groups.
    dark_css = os_dark_style(
        screen_blend=False,
        extra='[fill="#EDEDF2"]{fill:#1C1C1E;} '
        '[stroke="#DDDDE3"]{stroke:#3A3A3C;} '
        '[stroke="#F4F4F7"]{stroke:#1A1A1C;}',
    )
    parts.append(
        "<style>\n" + "\n".join(style_rows) + "\n" + contrast_css + "\n" + dark_css + "\n</style>"
    )

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_MAP_X + 6:.1f}" y="70" font-size="38" font-weight="700" '
        f'fill="{_INK}">The century’s tallest skyline is made of people</text>'
    )
    parts.append(
        f'<text x="{_MAP_X + 6:.1f}" y="108" font-size="21" fill="{_SUBTLE}">'
        f'Spike height = metropolitan population · the megacity belt runs '
        f'through East and South Asia, from Tokyo to Delhi to Dhaka</text>'
    )

    # ---- ocean graticule (faint, drawn first) ----
    parts.append('<g stroke="' + _GRAT + '" stroke-width="1" fill="none">')
    for d in _graticule_paths(fit):
        parts.append(f'<path d="{d}"/>')
    parts.append('</g>')

    # ---- land silhouette (faint backdrop) ----
    parts.append('<g fill="' + _LAND + '" stroke="' + _LAND_EDGE + '" stroke-width="0.6">')
    for ring in rings:
        parts.append(f'<path d="{_ring_path(ring, fit)}"/>')
    parts.append('</g>')

    # ---- spikes ----
    # Sort by latitude descending so northern (upper) spikes render first
    # and southern ones paint over them; the skyline layers back-to-front.
    order = sorted(range(len(_CITIES)), key=lambda i: -_CITIES[i][2])

    label_parts: List[str] = []  # labels drawn last, above every spike
    parts.append('<g>')
    for i in order:
        name, lon, lat, pop, _side = _CITIES[i]
        bx, by = _to_screen(lon, lat, fit)
        h = pop * px_per_m
        tip_y = by - h
        # A soft-filled triangle body plus a crisp ink edge, capped with a
        # tiny disc at the tip — the disc doubles as the hover target.
        tri = (
            f'M{bx - _SPIKE_HALF:.1f},{by:.1f} '
            f'L{bx:.1f},{tip_y:.1f} '
            f'L{bx + _SPIKE_HALF:.1f},{by:.1f} Z'
        )
        # The hover flag: a small rounded chip with the city name + population
        # that rises just above the tip and only shows on hover / focus (CSS).
        # It sits on the map's wide side (west of a spike in the eastern half,
        # east otherwise) so it stays inside the canvas, and carries an ink-on-
        # white chip so it never lands colour-on-colour over the red skyline.
        flag = _hover_flag(name, pop, bx, tip_y)
        parts.append(
            f'<g class="spike" tabindex="0" role="listitem">'
            f'<title>{_xml(name)}: {pop:.1f} million</title>'
            f'<path d="{tri}" fill="{spike_color}" fill-opacity="0.30"/>'
            f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{bx:.1f}" y2="{tip_y:.1f}" '
            f'stroke="{spike_color}" stroke-width="1.7" stroke-linecap="round"/>'
            f'<circle class="cap" cx="{bx:.1f}" cy="{tip_y:.1f}" r="2.6" '
            f'fill="{spike_color}"/>'
            f'{flag}'
            f'</g>'
        )

        # City name label for the called-out cities, on the empty side of
        # the spike so text never crosses the ink.
        if name in _LABELLED:
            if _LABELLED[name] == "R":
                lx = bx + 8.0
                anchor = "start"
            else:
                lx = bx - 8.0
                anchor = "end"
            ly = tip_y - 8.0
            label_parts.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="16" '
                f'font-weight="600" fill="{_INK}" text-anchor="{anchor}">'
                f'{_xml(name)}</text>'
            )
            label_parts.append(
                f'<text x="{lx:.1f}" y="{ly + 17:.1f}" font-size="13.5" '
                f'fill="{_SUBTLE}" text-anchor="{anchor}">{pop:.0f} M</text>'
            )
    parts.append('</g>')

    # ---- labels on top ----
    parts.append('<g>' + "".join(label_parts) + '</g>')

    # ---- size legend (bottom-left, three reference spikes) ----
    parts.extend(_size_legend(spike_color, px_per_m))

    # ---- footnote / method note ----
    parts.append(
        f'<text x="{_MAP_X + 6:.1f}" y="{_HEIGHT - 22}" font-size="14" '
        f'fill="{_SUBTLE}">One spike per urban agglomeration · height '
        f'∝ metropolitan population (2024, UN World Urbanization '
        f'Prospects order of magnitude) · Equal Earth projection</text>'
    )

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def _hover_flag(name: str, pop: float, bx: float, tip_y: float) -> str:
    """Build the CSS-toggled hover chip that names a spike and its value.

    The chip is a rounded ``white`` card carrying the city name in ink and
    the population in the secondary grey, so it reads clearly over land,
    ocean or the red skyline without any colour-on-colour. It is hidden at
    rest (``class="flag"``, ``opacity: 0``) and only shows for the hovered /
    focused spike. It floats just above the tip and is pinned to whichever
    side keeps it inside the canvas.

    Parameters
    ----------
    name : str
        City name.
    pop : float
        Population in millions.
    bx, tip_y : float
        Screen coordinates of the spike's base-x and tip-y.

    Returns
    -------
    str
        An SVG ``<g class="flag">`` fragment.
    """
    label = f"{name} · {pop:.1f} M"
    # Roughly size the chip to the text (Roboto ~ 7.4 px/char at 13 px).
    pad_x = 9.0
    char_w = 7.4
    chip_w = pad_x * 2 + char_w * len(label)
    chip_h = 24.0
    # Keep the chip on-canvas: flip it left of the tip near the right edge.
    if bx + 10.0 + chip_w > _MAP_X + _MAP_W:
        chip_x = bx - 10.0 - chip_w
        text_x = chip_x + pad_x
    else:
        chip_x = bx + 10.0
        text_x = chip_x + pad_x
    # Float above the tip; clamp so it never rises off the top of the map.
    chip_y = max(_MAP_Y - 6.0, tip_y - chip_h - 10.0)
    text_y = chip_y + chip_h / 2.0 + 4.6
    return (
        f'<g class="flag">'
        f'<rect x="{chip_x:.1f}" y="{chip_y:.1f}" width="{chip_w:.1f}" '
        f'height="{chip_h:.1f}" rx="6" fill="#FFFFFF" fill-opacity="0.96" '
        f'stroke="{_LAND_EDGE}" stroke-width="1"/>'
        f'<text x="{text_x:.1f}" y="{text_y:.1f}" font-size="13" '
        f'font-weight="600" fill="{_INK}">{_xml(label)}</text>'
        f'</g>'
    )


def _size_legend(spike_color: str, px_per_m: float) -> List[str]:
    """Return the size-legend group: three reference spikes with labels.

    Parameters
    ----------
    spike_color : str
        The spike hue.
    px_per_m : float
        Pixels of spike height per million residents (the map's scale),
        so the legend spikes read at exactly the map's rate.

    Returns
    -------
    list of str
        SVG fragments for the legend block.
    """
    out: List[str] = []
    refs = [10.0, 20.0, 37.0]  # millions
    lx = _MAP_X + 20.0
    baseline = _MAP_Y + _MAP_H - 6.0
    gap = 66.0
    out.append(
        f'<text x="{lx:.1f}" y="{baseline - 37.0 * px_per_m - 22:.1f}" '
        f'font-size="15" font-weight="700" fill="{_INK}">Metropolitan '
        f'population</text>'
    )
    out.append('<g>')
    # Shared baseline rule under the reference spikes.
    x0 = lx
    x1 = lx + gap * (len(refs) - 1) + 40.0
    out.append(
        f'<line x1="{x0:.1f}" y1="{baseline:.1f}" x2="{x1:.1f}" y2="{baseline:.1f}" '
        f'stroke="{_LAND_EDGE}" stroke-width="1"/>'
    )
    for k, pop in enumerate(refs):
        cx = lx + k * gap
        h = pop * px_per_m
        tip = baseline - h
        tri = (
            f'M{cx - _SPIKE_HALF:.1f},{baseline:.1f} '
            f'L{cx:.1f},{tip:.1f} '
            f'L{cx + _SPIKE_HALF:.1f},{baseline:.1f} Z'
        )
        out.append(f'<path class="legspike" d="{tri}" fill="{spike_color}" fill-opacity="0.30"/>')
        out.append(
            f'<line class="legspike" x1="{cx:.1f}" y1="{baseline:.1f}" x2="{cx:.1f}" y2="{tip:.1f}" '
            f'stroke="{spike_color}" stroke-width="1.7" stroke-linecap="round"/>'
        )
        out.append(
            f'<circle class="legspike" cx="{cx:.1f}" cy="{tip:.1f}" r="2.6" '
            f'fill="{spike_color}"/>'
        )
        out.append(
            f'<text x="{cx + 9:.1f}" y="{tip + 4:.1f}" font-size="13.5" '
            f'fill="{_SUBTLE}">{pop:.0f} M</text>'
        )
    out.append('</g>')
    return out


def main() -> None:
    """Write the spike-map SVG to the skill's ``svg-examples`` folder."""
    parser = argparse.ArgumentParser(description="Render the spike-map SVG.")
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the fullscreen control.",
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
    parser.add_argument("--out", default=None, help="Output path (defaults to the example asset).")
    args = parser.parse_args()
    out = Path(args.out) if args.out else svg_example_path(__file__, "spike-map")
    write_svg(out, build_svg(args.mode, args.accessibility))


if __name__ == "__main__":
    main()

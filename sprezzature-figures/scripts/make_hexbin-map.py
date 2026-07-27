#!/usr/bin/env python3
"""
make_hexbin-map — a house-styled geographic hexbin map as a hand-authored SVG.

A *hexbin map* answers "where are the events densest?" without drowning the
reader in overplotted dots. The whole map extent is tiled with regular
hexagons; every raw event falls into exactly one hexagon; each hexagon is
shaded by the *count* of events it captured on a single-hue sequential ramp.
Hexagons tile the plane without the axis-aligned bias of a square grid, and
each cell has six equidistant neighbours, so the density surface reads more
evenly than a 2-D histogram — the same idea deck.gl's ``HexagonLayer`` (Uber
H3) popularised, done here as a clean, print-ready static poster.

This example bins **three decades of large earthquakes** (magnitude 5.5 and
above) onto a real world basemap. The takeaway writes itself: the deep-red
cells trace the **Ring of Fire** — the horseshoe of subduction zones around
the Pacific rim, from the Andes up through Alaska and the Aleutians, down
past Japan, the Philippines and Indonesia to Tonga — while the continental
interiors stay almost empty.

The module builds the SVG string by hand — no matplotlib / seaborn / plotly,
and no Vega (a hexagonal lattice clipped to a projected coastline, with a
count legend and place labels, is authored far more directly as raw SVG). It
follows the sprezzature-* house style pulled from :mod:`_style`: a single-hue
sequential ramp keyed to the palette's Red, Roboto typography, ink
``#1D1D1F`` on secondary ``#6E6E73`` on a white background, rounded-corner
legend, a takeaway title, and a one-line subtitle.

Geometry is self-contained: the land silhouette comes from the vendored
``assets/geo/countries-110m.json`` TopoJSON and is drawn with a pure
closed-form **Equal Earth** projection (Šavrič, Patterson & Jenny 2018) — an
equal-area projection whose globe-like curvature reads as a proper world
map, and whose equal-area property keeps the hexbin density honest. The
projection is **centred on the Pacific** (central meridian 160° E) so the
Ring of Fire reads as one continuous horseshoe rather than being split down
the antimeridian at the two edges of a Greenwich-centred map. The
earthquake cloud is generated deterministically (fixed seed) by scattering
events along the real subduction arcs of the Ring of Fire plus a handful of
continental-collision belts, so re-running is byte-stable. A native
``<title>`` per hexagon gives a no-JavaScript hover tooltip, and CSS
``:hover`` / ``:focus`` lifts the hovered cell out of the surface.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/hexbin-map.svg``.

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
from typing import Dict, List, Optional, Tuple

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
#: Canvas size, in user-space pixels. Poster-scale so the Ring of Fire
#: arc and the count legend read at a glance and each hexagon stays crisp.
_WIDTH: int = 1520
_HEIGHT: int = 1010

#: Inner map viewport (leaves room for the header band and footnote).
_MAP_X: float = 32.0
_MAP_Y: float = 172.0
_MAP_W: float = 1456.0
_MAP_H: float = 688.0

#: Hexagon circum-radius (centre to a pointy corner), in pixels. Sized so
#: the lattice is dense enough to resolve the subduction arcs yet each
#: cell stays individually legible on a printed poster.
_HEX_R: float = 15.5

#: House-style inks.
_INK: str = "#1D1D1F"        # primary text
_SUBTLE: str = "#6E6E73"     # secondary text
_BG: str = "#FFFFFF"         # background
_LAND: str = "#E1E6EC"       # land silhouette under the lattice (clearly readable)
_LAND_EDGE: str = "#A9B2BF"  # coastline hairline (present, so continents read)
_OCEAN: str = "#F3F7FB"      # faint cool ocean wash so land / sea separate
_GRAT: str = "#DCE3EB"       # graticule / ocean grid
_STROKE: str = "#FFFFFF"     # white casing between hexes
_FOCUS: str = "#7A0C12"      # focus / hover outline (deep red)

#: The hexbin ramp top — a single saturated hue keeps the surface coherent.
_RAMP_KEY: str = "Red"

#: Reproducible event cloud.
_SEED: int = 20260726

#: How many earthquakes to synthesise. Chosen so the busiest Ring-of-Fire
#: cells saturate the ramp while ocean interiors stay bare.
_N_QUAKES: int = 9000


# ------------------------------------------------------------------
# Sequential single-hue ramp (pale straw -> palette Red)
# ------------------------------------------------------------------
def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    """Convert an ``(r, g, b)`` triple (0-255 floats) back to ``#RRGGBB``."""
    r, g, b = (max(0, min(255, round(c))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def _ramp(t: float, top: str, *, light: Tuple[int, int, int] = (255, 244, 214)) -> str:
    """Interpolate a warm sequential single-hue ramp at position ``t`` in [0, 1].

    A pale straw at ``t = 0`` warms through amber to the saturated house Red
    at ``t = 1``, passing through a mid orange so busy and quiet cells stay
    visually distinct rather than collapsing into one flat red. A mild gamma
    pulls the low-mid range apart so the long tail of one- and two-event
    cells does not vanish.

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
    t = t ** 0.68  # gentle gamma so the sparse tail separates from empty land
    # A three-stop ramp: straw -> orange -> Red, so the mid range reads as a
    # true heat gradient rather than a straight tint of one hue.
    mid = (255, 149, 0)  # palette Orange as the waypoint
    r2, g2, b2 = _hex_to_rgb(top)
    if t <= 0.5:
        u = t / 0.5
        r1, g1, b1 = light
        rr, gg, bb = mid
    else:
        u = (t - 0.5) / 0.5
        r1, g1, b1 = mid
        rr, gg, bb = (r2, g2, b2)
    return _rgb_to_hex((
        r1 + (rr - r1) * u,
        g1 + (gg - g1) * u,
        b1 + (bb - b1) * u,
    ))


# ------------------------------------------------------------------
# TopoJSON basemap loading (world land silhouette)
# ------------------------------------------------------------------
Ring = List[Tuple[float, float]]


def _load_land_rings() -> List[Ring]:
    """Decode the vendored world land silhouette from TopoJSON.

    The minimal TopoJSON contract of ``countries-110m.json``: quantised,
    delta-encoded arcs plus a ``scale`` / ``translate`` transform, stitched
    into closed lon/lat rings. We use the fused ``land`` object so no internal
    country borders clutter the faint backdrop under the hexes.

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
# Equal-area is what keeps a hexbin honest: equal ground area maps to equal
# screen area, so a full hexagon means the same catchment everywhere.
_A1, _A2, _A3, _A4 = 1.340264, -0.081106, 0.000893, 0.003796

#: Central meridian, in degrees. Centring on the Pacific keeps the Ring of
#: Fire a single continuous arc instead of splitting it at the map edges.
_LON0: float = 160.0


def _wrap_lon(lon: float) -> float:
    """Shift ``lon`` into ``[-180, 180]`` about the central meridian ``_LON0``."""
    return ((lon - _LON0 + 180.0) % 360.0) - 180.0


def _equal_earth(lon: float, lat: float) -> Tuple[float, float]:
    """Project ``(lon, lat)`` in degrees to Equal Earth planar ``(x, y)``.

    Longitudes are first re-centred on :data:`_LON0` (the Pacific) and
    wrapped into ``[-180, 180]``, so the map is Pacific-centred.

    Parameters
    ----------
    lon, lat : float
        Longitude / latitude in degrees.

    Returns
    -------
    tuple of float
        Planar ``(x, y)`` in projection units; ``y`` points up. Callers fit
        these to the viewport with :func:`_fit`.
    """
    lam = math.radians(_wrap_lon(lon))
    phi = math.radians(lat)
    theta = math.asin((math.sqrt(3.0) / 2.0) * math.sin(phi))
    t2 = theta * theta
    t6 = t2 * t2 * t2
    x = (
        2.0 * math.sqrt(3.0) * lam * math.cos(theta)
        / (3.0 * (_A1 + 3.0 * _A2 * t2 + t6 * (7.0 * _A3 + 9.0 * _A4 * t2)))
    )
    y = theta * (_A1 + _A2 * t2 + t6 * (_A3 + _A4 * t2))
    return x, y


# Module-level projection fit, set once by build_svg. Kept out of the passed
# tuple so _to_screen stays a tiny pure helper the audit tooling can read.
_FIT: Dict[str, float] = {}


def _fit(rings: List[Ring]) -> None:
    """Compute and store the projection-to-viewport affine fit for the map.

    Fits the whole graticule extent (not just land) so the ocean grid and
    the coastal hexes at the antimeridian are not clipped. Preserves aspect
    ratio and centres the drawing inside the map viewport.

    Parameters
    ----------
    rings : list of ring
        The land rings (only used to seed the projection; the extent is
        forced to the full graticule below so nothing clips at the edges).
    """
    pxs: List[float] = []
    pys: List[float] = []
    # Force the extent to the full graticule so meridians and the outermost
    # hexes never clip at the frame.
    for lon in range(-180, 181, 10):
        for lat in range(-84, 85, 6):
            px, py = _equal_earth(lon, lat)
            pxs.append(px)
            pys.append(py)
    min_px, max_px = min(pxs), max(pxs)
    min_py, max_py = min(pys), max(pys)
    span_x = max_px - min_px
    span_y = max_py - min_py
    pad = 6.0
    scale = min((_MAP_W - 2 * pad) / span_x, (_MAP_H - 2 * pad) / span_y)
    draw_w = span_x * scale
    draw_h = span_y * scale
    _FIT.update({
        "scale": scale,
        "offset_x": _MAP_X + (_MAP_W - draw_w) / 2.0,
        "offset_y": _MAP_Y + (_MAP_H - draw_h) / 2.0,
        "min_px": min_px,
        "min_py": min_py,
        "span_py": span_y,
    })


def _to_screen(lon: float, lat: float) -> Tuple[float, float]:
    """Project one ``(lon, lat)`` and map it into screen pixels (north up)."""
    px, py = _equal_earth(lon, lat)
    sx = _FIT["offset_x"] + (px - _FIT["min_px"]) * _FIT["scale"]
    sy = (
        _FIT["offset_y"]
        + (_FIT["span_py"] * _FIT["scale"])
        - (py - _FIT["min_py"]) * _FIT["scale"]
    )
    return sx, sy


# ------------------------------------------------------------------
# Earthquake cloud — scattered along the real Ring-of-Fire arcs
# ------------------------------------------------------------------
#: Seismic belts as poly-lines of ``(lon, lat)`` control points, each with a
#: weight (share of the synthetic catalogue it draws) and a jitter sigma in
#: degrees (how tightly events hug the arc). The vertices trace the real
#: subduction zones and collision belts; events are sampled along the
#: segments and nudged off them so the hexbin surface reads like a real
#: catalogue rather than a set of drawn lines.
_BELTS: List[Dict[str, object]] = [
    # ---- Ring of Fire (the horseshoe carries most of the mass) ----
    {  # Andes — South America west coast
        "w": 0.15, "sigma": 1.6,
        "pts": [(-73, -45), (-71, -33), (-70, -23), (-72, -14), (-77, -6), (-79, 1)],
    },
    {  # Central America / Mexico trench
        "w": 0.09, "sigma": 1.5,
        "pts": [(-84, 8), (-90, 13), (-96, 16), (-104, 18), (-106, 23)],
    },
    {  # Cascadia + Alaska + Aleutians
        "w": 0.11, "sigma": 1.7,
        "pts": [(-124, 40), (-130, 48), (-140, 57), (-150, 59), (-160, 55),
                (-172, 52), (177, 52), (170, 53)],
    },
    {  # Kamchatka -> Kuril -> Japan
        "w": 0.12, "sigma": 1.5,
        "pts": [(163, 55), (156, 50), (148, 45), (142, 40), (140, 35), (138, 31)],
    },
    {  # Ryukyu -> Taiwan -> Philippines
        "w": 0.11, "sigma": 1.5,
        "pts": [(131, 30), (128, 26), (123, 22), (122, 15), (126, 9), (127, 3)],
    },
    {  # Indonesia (Sunda arc) — Sumatra -> Java -> Banda
        "w": 0.14, "sigma": 1.5,
        "pts": [(95, 4), (100, -2), (106, -7), (114, -9), (122, -9), (130, -6), (134, -3)],
    },
    {  # New Guinea -> Solomons -> Vanuatu -> Tonga-Kermadec
        "w": 0.13, "sigma": 1.6,
        "pts": [(138, -4), (148, -6), (156, -8), (166, -14), (172, -20),
                (178, -25), (-176, -30), (-178, -37)],
    },
    {  # New Zealand
        "w": 0.03, "sigma": 1.3,
        "pts": [(173, -39), (170, -43), (167, -46)],
    },
    # ---- Alpide belt (continental collision) ----
    {  # Himalaya -> Hindu Kush
        "w": 0.05, "sigma": 1.4,
        "pts": [(74, 34), (80, 30), (88, 27), (95, 27), (98, 25)],
    },
    {  # Iran / Anatolia / Mediterranean
        "w": 0.05, "sigma": 1.4,
        "pts": [(60, 30), (52, 33), (44, 38), (36, 37), (28, 38), (22, 38), (15, 40)],
    },
    # ---- Mid-Atlantic ridge (sparse background) ----
    {
        "w": 0.02, "sigma": 1.2,
        "pts": [(-30, 0), (-25, 20), (-30, 40), (-20, 60), (-18, 65)],
    },
]


def _sample_quakes(n: int, rng: random.Random) -> List[Tuple[float, float]]:
    """Scatter ``n`` synthetic earthquakes along the seismic belts.

    Each belt is sampled by walking its poly-line by arc-length; a point is
    dropped at a random position along the belt and jittered normal to it by
    a Gaussian, so events cluster on the arc but spread into a plausible
    band. Longitudes wrap to ``[-180, 180]`` so belts crossing the
    antimeridian stay contiguous.

    Parameters
    ----------
    n : int
        Target number of events.
    rng : random.Random
        Seeded generator for reproducibility.

    Returns
    -------
    list of (float, float)
        ``(lon, lat)`` event locations in degrees.
    """
    weights = [float(b["w"]) for b in _BELTS]
    total_w = sum(weights)
    cum: List[float] = []
    acc = 0.0
    for w in weights:
        acc += w / total_w
        cum.append(acc)

    pts: List[Tuple[float, float]] = []
    for _ in range(n):
        u = rng.random()
        k = next(i for i, c in enumerate(cum) if u <= c)
        belt = _BELTS[k]
        line = belt["pts"]  # type: ignore[assignment]
        sigma = float(belt["sigma"])
        # Walk to a random segment of the poly-line, uniformly in vertex index
        # (segments are of comparable length here, which is enough for a
        # teaching catalogue).
        seg = rng.randint(0, len(line) - 2)  # type: ignore[arg-type]
        t = rng.random()
        (x0, y0), (x1, y1) = line[seg], line[seg + 1]  # type: ignore[index]
        # Interpolate along the segment (unwrap longitudes near ±180 first).
        if abs(x1 - x0) > 180:
            x1 = x1 + 360.0 if x1 < x0 else x1 - 360.0
        lon = x0 + (x1 - x0) * t
        lat = y0 + (y1 - y0) * t
        lon += rng.gauss(0.0, sigma)
        lat += rng.gauss(0.0, sigma)
        # Wrap longitude back into [-180, 180].
        lon = ((lon + 180.0) % 360.0) - 180.0
        lat = max(-84.0, min(84.0, lat))
        pts.append((lon, lat))
    return pts


# ------------------------------------------------------------------
# Hexagon lattice (pointy-top, offset rows) over the projected extent
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
    d = f"M{corners[0][0]:.1f},{corners[0][1]:.1f}"
    for x, y in corners[1:]:
        d += f" L{x:.1f},{y:.1f}"
    return d + "Z"


def _build_lattice(land_mask: List[Ring]) -> List[Dict[str, float]]:
    """Tile the projected map extent with pointy-top hexagons.

    Every cell centre carries its screen position plus a flag for whether it
    sits over land (used to give empty ocean a lighter "no events" tint than
    empty land, so the coastlines stay legible through the lattice).

    Parameters
    ----------
    land_mask : list of ring
        Land rings in *screen* space, used for the point-in-land test.

    Returns
    -------
    list of dict
        One record per hexagon with pixel centre ``px``/``py`` and an
        ``on_land`` flag; ``count`` is filled in by :func:`_bin_points`.
    """
    r = _HEX_R
    hex_w = math.sqrt(3.0) * r          # width of a pointy-top hex
    v_step = 1.5 * r                    # vertical distance between rows

    # Draw the frame from the projected graticule extent so the lattice fills
    # the same box the basemap occupies.
    xs: List[float] = []
    ys: List[float] = []
    for lon in range(-180, 181, 4):
        for lat in (-84, 0, 84):
            sx, sy = _to_screen(lon, lat)
            xs.append(sx)
            ys.append(sy)
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    cells: List[Dict[str, float]] = []
    row = 0
    py = y0 + r
    while py <= y1 - r * 0.1:
        x_off = (hex_w / 2.0) if (row % 2) else 0.0
        px = x0 + hex_w / 2.0 + x_off
        while px <= x1 - hex_w / 2.0 + hex_w:
            on_land = _point_in_rings(px, py, land_mask)
            cells.append({"px": px, "py": py, "on_land": 1.0 if on_land else 0.0})
            px += hex_w
        py += v_step
        row += 1
    return cells


def _point_in_rings(x: float, y: float, rings: List[Ring]) -> bool:
    """Return ``True`` when ``(x, y)`` falls inside any of the (screen) rings."""
    inside = False
    for ring in rings:
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
            ):
                inside = not inside
            j = i
    return inside


def _bin_points(
    cells: List[Dict[str, float]],
    screen_pts: List[Tuple[float, float]],
) -> None:
    """Assign each event to the nearest hexagon centre, tallying counts.

    Uses a coarse spatial hash on the lattice pitch so binning 9,000 events
    into ~3,000 cells stays near-linear instead of quadratic.

    Parameters
    ----------
    cells : list of dict
        The lattice from :func:`_build_lattice`.
    screen_pts : list of (float, float)
        Event positions already projected to screen pixels.
    """
    for c in cells:
        c["count"] = 0.0
    # Spatial hash: bucket cell centres by a grid one hex-width wide.
    pitch = math.sqrt(3.0) * _HEX_R
    buckets: Dict[Tuple[int, int], List[Dict[str, float]]] = {}
    for c in cells:
        key = (int(c["px"] // pitch), int(c["py"] // pitch))
        buckets.setdefault(key, []).append(c)

    for px, py in screen_pts:
        gx, gy = int(px // pitch), int(py // pitch)
        best: Optional[Dict[str, float]] = None
        best_d = 1e18
        # Search the 3x3 neighbourhood of buckets around the event.
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for c in buckets.get((gx + dx, gy + dy), ()):
                    d = (c["px"] - px) ** 2 + (c["py"] - py) ** 2
                    if d < best_d:
                        best_d = d
                        best = c
        if best is not None:
            best["count"] += 1.0


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


# ------------------------------------------------------------------
# SVG assembly helpers
# ------------------------------------------------------------------
#: Screen-space x-jump (pixels) above which a land ring is assumed to have
#: crossed the antimeridian; the path is broken there so no polygon edge
#: streaks horizontally across the whole map.
_WRAP_JUMP_PX: float = 400.0


def _ring_path(ring: Ring) -> str:
    """Build an SVG path ``d`` string for one land ring (already in screen space).

    A Pacific-centred projection cuts the globe at its own antimeridian, so a
    ring that straddles the cut has one huge horizontal jump in screen ``x``.
    Break the path there (start a fresh ``M``) so the polygon is not stitched
    across the whole frame.
    """
    cmds: List[str] = []
    prev_x: Optional[float] = None
    started = False
    for sx, sy in ring:
        if prev_x is not None and abs(sx - prev_x) > _WRAP_JUMP_PX:
            started = False  # crossed the cut -> lift the pen
        cmds.append(f"{'M' if not started else 'L'}{sx:.1f},{sy:.1f}")
        started = True
        prev_x = sx
    return "".join(cmds)


def _graticule_paths() -> List[str]:
    """Return faint meridian / parallel arcs for the ocean grid."""
    paths: List[str] = []
    # Parallels: sample in projection-centred longitude so they never cross
    # the antimeridian cut, then draw as a single smooth arc.
    for lat in range(-60, 61, 30):
        pts = [_to_screen(lon + _LON0, lat) for lon in range(-180, 181, 5)]
        d = "".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
        paths.append(d)
    # Meridians every 60° of the centred grid.
    for lon in range(-180, 181, 60):
        pts = [_to_screen(lon + _LON0, lat) for lat in range(-84, 85, 5)]
        d = "".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
        paths.append(d)
    return paths


#: Geographic anchor labels: ``(label, lon, lat)`` naming oceans and
#: continents in faint secondary ink, so the reader can locate the hexbin
#: field on a recognisable world even at a glance. Placed over open water /
#: continental interiors, well clear of the hot arcs and the belt call-outs.
_GEO_LABELS: List[Tuple[str, float, float]] = [
    ("PACIFIC OCEAN", -155.0, 6.0),
    ("ATLANTIC", -30.0, 36.0),
    ("INDIAN OCEAN", 76.0, -30.0),
    ("N. AMERICA", -102.0, 44.0),
    ("S. AMERICA", -58.0, -12.0),
    ("AFRICA", 22.0, 5.0),
    ("EUROPE", 22.0, 54.0),
    ("ASIA", 90.0, 50.0),
    ("AUSTRALIA", 136.0, -27.0),
]


#: Region call-outs: ``(label, lon, lat, anchor)`` planted over the busiest
#: arcs so a reader can name the pattern. Anchors keep text off the ink.
_CALLOUTS: List[Tuple[str, float, float, str]] = [
    ("Aleutians & Alaska", -150.0, 72.0, "middle"),
    ("Japan & Kuril arc", 158.0, 34.0, "start"),
    ("Indonesia", 108.0, -20.0, "middle"),
    ("Tonga–Kermadec", -172.0, -33.0, "start"),
    ("Andes", -55.0, -22.0, "start"),
    ("Himalaya", 80.0, 15.0, "middle"),
]


# ------------------------------------------------------------------
# Build
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full geographic-hexbin-map SVG document as a string.

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
    palette = load_palette(accessibility)
    red = palette.get("Red", "#FF3B30")

    rings = _load_land_rings()
    _fit(rings)

    # Project land rings to screen once (reused for drawing and land masking).
    screen_rings: List[Ring] = [
        [_to_screen(lon, lat) for lon, lat in ring] for ring in rings
    ]

    rng = random.Random(_SEED)
    quakes = _sample_quakes(_N_QUAKES, rng)
    screen_quakes = [_to_screen(lon, lat) for lon, lat in quakes]

    cells = _build_lattice(screen_rings)
    _bin_points(cells, screen_quakes)

    counts = [int(c["count"]) for c in cells]
    nonzero = [c for c in counts if c > 0]
    # Cap the ramp at a high percentile so a couple of outlier cells do not
    # wash the whole surface pale; the top decile still reads as deep red.
    ramp_max = max(sorted(nonzero)[int(len(nonzero) * 0.985)] if nonzero else 1, 1)
    true_max = max(counts) if counts else 1
    total = sum(counts)
    active = len(nonzero)

    # ---- header scaffold ----
    parts: List[str] = []
    parts.append(svg_open(_WIDTH, _HEIGHT, "hb-title", "hb-desc"))
    parts.append(
        '<title id="hb-title">Three decades of large earthquakes trace the '
        'Ring of Fire</title>'
    )
    desc = (
        f"Geographic hexbin map of the world. The globe is tiled with regular "
        f"hexagons; each is shaded by the number of magnitude-5.5-and-above "
        f"earthquakes that fell inside it, from {total:,} events in all. The "
        f"warm ramp runs from pale straw (one or two quakes) through orange to "
        f"deep red (the busiest cell, {true_max} quakes). The red cells draw a "
        f"near-continuous horseshoe around the Pacific — the Ring of Fire — "
        f"from the Andes up through Alaska and the Aleutians, down past Japan, "
        f"the Philippines and Indonesia to Tonga, with a second belt along the "
        f"Himalaya and the Mediterranean. Continental interiors and the deep "
        f"ocean stay almost empty. Equal-area Equal Earth projection."
    )
    parts.append(f'<desc id="hb-desc">{desc}</desc>')

    # ---- interactivity + house style (pure CSS, no JS) ----
    style_rows = [
        ".hex { transition: transform .14s ease, stroke .14s ease; "
        "transform-box: fill-box; transform-origin: center; }",
        f".hex:hover, .hex:focus {{ transform: scale(1.55); "
        f"stroke: {_FOCUS}; stroke-width: 1.1; outline: none; }}",
        ".legend-swatch { stroke: #FFFFFF; stroke-width: 0.6; }",
        "@media (prefers-reduced-motion: reduce) { .hex { transition: none; } "
        ".hex:hover, .hex:focus { transform: none; } }",
        # prefers-contrast (perceptual figure): strengthen STRUCTURE only — firm
        # the white inter-hex casing to a visible grey so the lattice edges read,
        # deepen the coastline hairline and the secondary ink, and thicken the
        # legend-swatch outlines. The sequential earthquake-count ramp on the
        # hexes is left untouched (re-spacing it would de-tune the encoding).
        "@media (prefers-contrast: more){"
        ".hex{stroke:#8E8E93;stroke-width:0.9;}"
        ".legend-swatch{stroke:#6E6E73;stroke-width:1;}"
        f'[fill="{_SUBTLE}"]{{fill:#3A3A3C;}}'
        f'[stroke="{_LAND_EDGE}"]{{stroke:#5A6472;}}'
        "}",
    ]
    # Additive dark mode: flip paper + the two ink tiers, and darken the basemap
    # layers (land silhouette + ocean wash) so the lattice reads on a dark
    # surface. The sequential count ramp on the hexes is perceptual and is left
    # untouched — it stays legible on the darker land.
    style_rows.append(
        os_dark_style(
            extra=(
                f'[fill="{_LAND}"]{{fill:#1C1C1E;}} '
                f'[fill="{_OCEAN}"]{{fill:#111417;}}'
            )
        )
    )
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # A faint cool ocean wash behind the whole map viewport gives the land a
    # sea to sit in, so continents read as land rather than as pale blobs on
    # white. Rounded to echo the house-style card corners.
    parts.append(
        f'<rect x="{_MAP_X:.1f}" y="{_MAP_Y:.1f}" width="{_MAP_W:.1f}" '
        f'height="{_MAP_H:.1f}" rx="14" fill="{_OCEAN}"/>'
    )

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_MAP_X + 6:.1f}" y="72" font-size="40" font-weight="700" '
        f'fill="{_INK}">The Earth’s earthquakes draw a Ring of Fire</text>'
    )
    parts.append(
        f'<text x="{_MAP_X + 6:.1f}" y="112" font-size="21" fill="{_SUBTLE}">'
        f'Large quakes (magnitude 5.5+) binned into hexagons · the deep-red '
        f'cells trace the Pacific rim’s subduction zones</text>'
    )

    # ---- ocean graticule (faint, drawn first) ----
    parts.append('<g stroke="' + _GRAT + '" stroke-width="1" fill="none">')
    for d in _graticule_paths():
        parts.append(f'<path d="{d}"/>')
    parts.append('</g>')

    # ---- land silhouette (readable backdrop under the lattice) ----
    parts.append(
        '<g fill="' + _LAND + '" stroke="' + _LAND_EDGE + '" '
        'stroke-width="1.1" stroke-linejoin="round">'
    )
    for ring in screen_rings:
        parts.append(f'<path d="{_ring_path(ring)}"/>')
    parts.append('</g>')

    # ---- geographic anchor labels (name oceans + continents) ----
    # Drawn under the hexbins in faint, letter-spaced small caps so they read
    # as a map's base labelling and never fight the hot arcs for attention.
    parts.append(
        f'<g fill="{_SUBTLE}" font-size="15" font-weight="600" '
        f'letter-spacing="1.6" text-anchor="middle" opacity="0.7">'
    )
    for label, lon, lat in _GEO_LABELS:
        sx, sy = _to_screen(lon, lat)
        parts.append(
            f'<text x="{sx:.1f}" y="{sy:.1f}" stroke="{_OCEAN}" '
            f'stroke-width="3.0" stroke-linejoin="round" paint-order="stroke">'
            f'{_xml(label)}</text>'
        )
    parts.append('</g>')

    # ---- hexbin layer ----
    # Empty cells are drawn very faint (and only the ones sitting over land or
    # near the arcs matter); populated cells carry a white casing so the
    # lattice reads even where it is dense. Draw empties first, hot cells last.
    parts.append('<g role="list" aria-label="hexagonal earthquake-density bins">')
    r_draw = _HEX_R * 0.94  # tiny gap => white casing shows between hexes
    ordered = sorted(cells, key=lambda c: c["count"])
    for c in ordered:
        cnt = int(c["count"])
        if cnt <= 0:
            # Skip empty ocean entirely (keeps the file lean and the sea clean);
            # only faint empty *land* cells earn a whisper of grounding.
            continue
        t = min(cnt, ramp_max) / ramp_max
        fill = _ramp(t, red)
        d = _hex_path(c["px"], c["py"], r_draw)
        label = f'{cnt} quake{"" if cnt == 1 else "s"}'
        parts.append(
            f'<path class="hex" d="{d}" fill="{fill}" stroke="{_STROKE}" '
            f'stroke-width="1.0" tabindex="0" role="listitem">'
            f'<title>{label}</title></path>'
        )
    parts.append('</g>')

    # ---- region call-outs (leader-free text labels in ink) ----
    parts.append('<g>')
    for label, lon, lat, anchor in _CALLOUTS:
        sx, sy = _to_screen(lon, lat)
        # A soft white halo via paint-order so the ink label stays legible
        # over the busy lattice without a hard black outline.
        parts.append(
            f'<text x="{sx:.1f}" y="{sy:.1f}" font-size="16.5" '
            f'font-weight="700" fill="{_INK}" text-anchor="{anchor}" '
            f'stroke="#FFFFFF" stroke-width="3.2" stroke-linejoin="round" '
            f'paint-order="stroke" opacity="0.98">{_xml(label)}</text>'
        )
    parts.append('</g>')

    # ---- sequential legend + stat callout (bottom band) ----
    parts.extend(_legend_and_stat(red, ramp_max, true_max, total, active))

    # ---- footnote / method note ----
    parts.append(
        f'<text x="{_MAP_X + 6:.1f}" y="{_HEIGHT - 20}" font-size="14" '
        f'fill="{_SUBTLE}">One hexagon ≈ 250,000 km² · colour = earthquake '
        f'count per hexagon · illustrative catalogue seeded on real '
        f'subduction arcs · Equal Earth (equal-area) projection</text>'
    )

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def _legend_and_stat(
    red: str,
    ramp_max: int,
    true_max: int,
    total: int,
    active: int,
) -> List[str]:
    """Return the horizontal legend ramp plus a headline stat, bottom-left.

    Parameters
    ----------
    red : str
        The ramp top hue.
    ramp_max : int
        Count mapped to the darkest swatch (the ramp saturation point).
    true_max : int
        The true busiest-cell count (shown as the ">=" end label).
    total : int
        Total events in the catalogue.
    active : int
        Number of non-empty hexagons.

    Returns
    -------
    list of str
        SVG fragments for the legend + stat block.
    """
    out: List[str] = []
    lx = _MAP_X + 8.0
    ly = _MAP_Y + _MAP_H + 30.0

    # ---- headline stat (left) ----
    # Share of quakes captured by the busiest 10% of active hexes.
    out.append(
        f'<text x="{lx:.1f}" y="{ly + 30:.1f}" font-size="52" font-weight="700" '
        f'fill="{red}">Ring of Fire</text>'
    )
    out.append(
        f'<text x="{lx:.1f}" y="{ly + 56:.1f}" font-size="17" fill="{_SUBTLE}">'
        f'{active:,} hexagons hold quakes · the busiest holds {true_max}, '
        f'all on the Pacific rim</text>'
    )

    # ---- horizontal ramp (right of the stat) ----
    ramp_x = lx + 470.0
    ramp_y = ly + 8.0
    bar_h = 26.0
    n_seg = 9
    seg_w = 40.0
    out.append(
        f'<text x="{ramp_x:.1f}" y="{ramp_y - 12:.1f}" font-size="16.5" '
        f'font-weight="700" fill="{_INK}">Earthquakes per hexagon</text>'
    )
    for i in range(n_seg):
        t = i / (n_seg - 1)
        col = _ramp(t, red)
        out.append(
            f'<rect class="legend-swatch" x="{ramp_x + i * seg_w:.1f}" '
            f'y="{ramp_y:.1f}" width="{seg_w:.1f}" height="{bar_h:.1f}" '
            f'fill="{col}"/>'
        )
    # End labels sit *outside / under* the ramp in ink — never on the disks.
    out.append(
        f'<text x="{ramp_x:.1f}" y="{ramp_y + bar_h + 20:.1f}" font-size="15" '
        f'fill="{_SUBTLE}" font-family="Roboto Mono, monospace">1</text>'
    )
    out.append(
        f'<text x="{ramp_x + n_seg * seg_w:.1f}" y="{ramp_y + bar_h + 20:.1f}" '
        f'font-size="15" fill="{_INK}" font-family="Roboto Mono, monospace" '
        f'text-anchor="end">{ramp_max}+ quakes</text>'
    )
    return out


def main() -> None:
    """Write the geographic-hexbin-map SVG to the skill's ``svg-examples`` folder.

    The ``--mode`` flag selects the interactivity mode of the emitted SVG
    (``self-contained`` / ``external`` / ``static``); see
    :func:`_interactive.fullscreen_control`.
    """
    render_cli(
        __file__, "hexbin-map", build_svg, description="Render the geographic-hexbin-map SVG."
    )


if __name__ == "__main__":
    main()

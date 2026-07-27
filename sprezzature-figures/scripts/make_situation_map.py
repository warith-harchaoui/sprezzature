#!/usr/bin/env python3
"""Generate a professional, layered *situation map* for any region of the world.

Author: Warith Harchaoui

This reverse-engineers the plate structure that geopolitics data desks use into a
parameterized generator. From one YAML config (a region, a projection, thematic
*areas of control*, forces, events, infrastructure, labels) it emits a single SVG
built as a stack of layers whose names a geopolitics analyst recognizes on sight
(bottom -> top paint order):

1. ``basemap-sea``        — sea fill.
2. ``basemap-bathymetry`` — depth-contour halo radiating from the coast.
3. ``basemap-land``       — land fill.
4. ``areas-of-control``   — territory zones, pastel + white casing; contested = hatch.
5. ``infrastructure``     — roads / highways / airports as hairlines.
6. ``forces``             — unit / actor positions (point markers).
7. ``events``             — incidents (ceasefire points, clashes, strikes).
8. ``annotation-labels``  — letter-spaced place + water labels.
9. ``annotation-furniture`` — title block, north arrow, dual-unit (km + mi) scale bar.
10. ``legend``            — floating legend panel with swatches.
11. ``frame``             — rounded-rectangle panel mask.

The craft signatures reproduced here: an equal-angle **local projection**
(Lambert Conformal Conic auto-centred on the region), a **classed pastel palette**,
**white boundary casing** between adjacent zones, **bathymetry** contours in the
sea, **drop-shadowed** panel + markers, **letter-spaced** uppercase labels, and a
**dual-unit scale bar** — reachable for *any* part of the world, not one example.

Basemap geometry is the vendored, offline Natural Earth land polygon
(``assets/geo/countries-50m.json``); the caller supplies the thematic layers.

Usage
-----
    python make_situation_map.py --config demo.yaml --out demo.svg --render

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc classes.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guard
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc

try:
    from pyproj import Transformer
    from shapely import make_valid
    from shapely.geometry import (
        MultiPolygon,
        Polygon,
        box,
        shape,
    )
    from shapely.ops import transform as shp_transform
    from shapely.ops import unary_union
except ImportError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "shapely>=2 and pyproj>=3.6 are required: pip install shapely pyproj"
    ) from exc


# --------------------------------------------------------------------------- #
# Vendored basemap (Natural Earth, offline)                                    #
# --------------------------------------------------------------------------- #

_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "geo"
_LAND_TOPOJSON = _ASSETS / "countries-50m.json"
_RIVERS_GEOJSON = _ASSETS / "rivers-50m.geojson"


def _decode_topojson_object(topo: dict[str, Any], name: str) -> Any:
    """Decode one object of a TopoJSON topology into a shapely geometry (lon/lat).

    Implements the minimal TopoJSON contract: quantised delta-encoded arcs plus a
    ``scale``/``translate`` transform, stitched into GeoJSON-style rings and unioned.

    Parameters
    ----------
    topo : dict
        Parsed TopoJSON topology.
    name : str
        Key inside ``topo["objects"]`` to decode (e.g. ``"land"``).

    Returns
    -------
    shapely geometry
        The dissolved geometry of the requested object, in WGS84 lon/lat.
    """
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    def decode_arc(index: int) -> list[list[float]]:
        # Negative index => reversed arc (~index).
        reverse = index < 0
        arc = raw_arcs[~index if reverse else index]
        points: list[list[float]] = []
        x = y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            points.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
        return points[::-1] if reverse else points

    def stitch(arc_indices: Iterable[int]) -> list[list[float]]:
        ring: list[list[float]] = []
        for j, idx in enumerate(arc_indices):
            pts = decode_arc(idx)
            ring.extend(pts if j == 0 else pts[1:])
        return ring

    geoms = []
    obj = topo["objects"][name]
    for geom in obj["geometries"]:
        gtype = geom["type"]
        if gtype == "Polygon":
            rings = [stitch(part) for part in geom["arcs"]]
            geoms.append(Polygon(rings[0], rings[1:]))
        elif gtype == "MultiPolygon":
            polys = []
            for poly in geom["arcs"]:
                rings = [stitch(part) for part in poly]
                polys.append(Polygon(rings[0], rings[1:]))
            geoms.append(MultiPolygon(polys))
    # Natural Earth polygons can be individually invalid (self-touching rings);
    # repair each rather than a fragile world-wide union — the caller clips to a
    # bounding box, so a MultiPolygon of validated pieces is sufficient.
    fixed = [make_valid(g) for g in geoms]
    return unary_union(fixed)


def load_land() -> Any:
    """Return the dissolved world land polygon (WGS84), from the vendored basemap."""
    topo = json.loads(_LAND_TOPOJSON.read_text())
    return _decode_topojson_object(topo, "land")


def load_country(name: str) -> Any:
    """Return the polygon of a single country by Natural Earth ``name`` (WGS84).

    Lets a caller partition a *real* national outline into thematic zones — the
    honest way to build a situation map for a named country rather than tracing
    borders by hand.

    Parameters
    ----------
    name : str
        Country name as spelled in the vendored ``countries`` object
        (e.g. ``"Ukraine"``, ``"France"``).

    Returns
    -------
    shapely geometry
        The (repaired) country polygon.

    Raises
    ------
    KeyError
        If no country with that name exists in the basemap.
    """
    topo = json.loads(_LAND_TOPOJSON.read_text())
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    def decode_arc(index: int) -> list[list[float]]:
        reverse = index < 0
        arc = raw_arcs[~index if reverse else index]
        pts: list[list[float]] = []
        x = y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
        return pts[::-1] if reverse else pts

    def stitch(arc_indices: Iterable[int]) -> list[list[float]]:
        ring: list[list[float]] = []
        for j, idx in enumerate(arc_indices):
            pts = decode_arc(idx)
            ring.extend(pts if j == 0 else pts[1:])
        return ring

    for geom in topo["objects"]["countries"]["geometries"]:
        if geom.get("properties", {}).get("name") != name:
            continue
        if geom["type"] == "Polygon":
            rings = [stitch(part) for part in geom["arcs"]]
            return make_valid(Polygon(rings[0], rings[1:]))
        polys = []
        for poly in geom["arcs"]:
            rings = [stitch(part) for part in poly]
            polys.append(Polygon(rings[0], rings[1:]))
        return make_valid(MultiPolygon(polys))
    raise KeyError(f"country not found in basemap: {name!r}")


def load_countries() -> list[tuple[str, Any]]:
    """Return ``(name, polygon)`` for every country in the vendored basemap (WGS84).

    Lets the map draw real international frontiers and label the neighbours, so a
    situation plate carries its surrounding geography instead of a lone outline.
    """
    topo = json.loads(_LAND_TOPOJSON.read_text())
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    def decode_arc(index: int) -> list[list[float]]:
        reverse = index < 0
        arc = raw_arcs[~index if reverse else index]
        pts: list[list[float]] = []
        x = y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
        return pts[::-1] if reverse else pts

    def stitch(arc_indices: Iterable[int]) -> list[list[float]]:
        ring: list[list[float]] = []
        for j, idx in enumerate(arc_indices):
            pts = decode_arc(idx)
            ring.extend(pts if j == 0 else pts[1:])
        return ring

    out: list[tuple[str, Any]] = []
    for geom in topo["objects"]["countries"]["geometries"]:
        name = geom.get("properties", {}).get("name", "")
        try:
            if geom["type"] == "Polygon":
                rings = [stitch(part) for part in geom["arcs"]]
                poly = make_valid(Polygon(rings[0], rings[1:]))
            else:
                polys = []
                for part in geom["arcs"]:
                    rings = [stitch(r) for r in part]
                    polys.append(Polygon(rings[0], rings[1:]))
                poly = make_valid(MultiPolygon(polys))
        except Exception:  # skip a malformed geometry rather than fail the plate
            continue
        out.append((name, poly))
    return out


def load_rivers() -> list[tuple[Any, str, int]]:
    """Return ``(geometry, name, scalerank)`` for the vendored river centerlines.

    Natural Earth 50m rivers + lake centerlines, trimmed to named features. Lower
    ``scalerank`` means a more prominent river (used to decide what gets labelled).
    """
    if not _RIVERS_GEOJSON.is_file():
        return []
    data = json.loads(_RIVERS_GEOJSON.read_text())
    out: list[tuple[Any, str, int]] = []
    for feat in data.get("features", []):
        try:
            geom = shape(feat["geometry"])
        except Exception:
            continue
        props = feat.get("properties", {})
        out.append((geom, props.get("name", ""), int(props.get("scalerank", 10))))
    return out


# --------------------------------------------------------------------------- #
# Projection                                                                   #
# --------------------------------------------------------------------------- #


def build_projection(bbox: list[float], epsg: Optional[str]) -> Transformer:
    """Return a lon/lat -> planar-metre transformer suited to ``bbox``.

    When ``epsg`` is ``None`` (or ``"auto"``) a Lambert Conformal Conic is centred
    on the region, with standard parallels at the one-sixth / five-sixth latitudes
    (the classic two-thirds rule) — conformal, so shapes and angles stay true at
    the scale of a city or a province.

    Parameters
    ----------
    bbox : list of float
        ``[west, south, east, north]`` in degrees.
    epsg : str or None
        An explicit CRS such as ``"EPSG:3857"``, or ``None``/``"auto"``.

    Returns
    -------
    pyproj.Transformer
        Transformer from ``EPSG:4326`` to the chosen projected CRS.
    """
    if epsg and epsg.lower() != "auto":
        return Transformer.from_crs("EPSG:4326", epsg, always_xy=True)
    west, south, east, north = bbox
    lon0 = (west + east) / 2.0
    lat0 = (south + north) / 2.0
    lat1 = south + (north - south) / 6.0
    lat2 = north - (north - south) / 6.0
    proj4 = (
        f"+proj=lcc +lat_1={lat1} +lat_2={lat2} +lat_0={lat0} +lon_0={lon0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    return Transformer.from_crs("EPSG:4326", proj4, always_xy=True)


# --------------------------------------------------------------------------- #
# Viewport: project + fit to an SVG canvas (y flipped)                          #
# --------------------------------------------------------------------------- #


def make_viewport(
    proj: Transformer, bbox: list[float], width: float, pad: float
) -> dict[str, Any]:
    """Project ``bbox`` and return a viewport mapping planar metres -> SVG units.

    Returns a dict-record with the canvas size, a ``to_svg(x, y)`` closure (flips y),
    and ``m_per_unit`` so the scale bar can be drawn in true kilometres.
    """
    west, south, east, north = bbox
    # Sample the projected outline (edges, not just corners) so a curved projection
    # is bounded correctly.
    xs: list[float] = []
    ys: list[float] = []
    steps = 24
    for t in range(steps + 1):
        f = t / steps
        for lon, lat in (
            (west + (east - west) * f, south),
            (west + (east - west) * f, north),
            (west, south + (north - south) * f),
            (east, south + (north - south) * f),
        ):
            x, y = proj.transform(lon, lat)
            xs.append(x)
            ys.append(y)
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span_x = maxx - minx
    span_y = maxy - miny
    inner_w = width - 2 * pad
    scale = inner_w / span_x
    height = span_y * scale + 2 * pad

    def to_svg(x: float, y: float) -> tuple[float, float]:
        sx = pad + (x - minx) * scale
        sy = pad + (maxy - y) * scale  # flip: projected up -> SVG down
        return sx, sy

    return {
        "width": width,
        "height": height,
        "to_svg": to_svg,
        "m_per_unit": 1.0 / scale,
        # Type scale: label/furniture sizes track the plate width so a large
        # plate does not end up with tiny print. Calibrated to a 1000-unit plate.
        "ts": max(1.0, width / 1000.0),
        "bbox": bbox,
        "proj": proj,
    }


# --------------------------------------------------------------------------- #
# Geometry -> SVG path                                                          #
# --------------------------------------------------------------------------- #


def _ring_to_path(coords: Iterable[tuple[float, float]], vp: dict[str, Any]) -> str:
    to_svg = vp["to_svg"]
    proj = vp["proj"]
    out: list[str] = []
    for i, (lon, lat) in enumerate(coords):
        x, y = proj.transform(lon, lat)
        sx, sy = to_svg(x, y)
        out.append(f"{'M' if i == 0 else 'L'}{sx:.2f},{sy:.2f}")
    out.append("Z")
    return "".join(out)


def geom_to_path(geom: Any, vp: dict[str, Any]) -> str:
    """Convert a (Multi)Polygon in lon/lat into an SVG path ``d`` string."""
    parts: list[str] = []
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polys:
        if poly.is_empty:
            continue
        parts.append(_ring_to_path(poly.exterior.coords, vp))
        for hole in poly.interiors:
            parts.append(_ring_to_path(hole.coords, vp))
    return " ".join(parts)


def _project_geom(geom: Any, proj: Transformer) -> Any:
    """Return ``geom`` reprojected from lon/lat into the projected CRS (metres)."""
    return shp_transform(lambda xs, ys: proj.transform(xs, ys), geom)


def _projected_ring_to_path(coords: Iterable[tuple[float, float]], vp: dict[str, Any]) -> str:
    to_svg = vp["to_svg"]
    out: list[str] = []
    for i, (x, y) in enumerate(coords):
        sx, sy = to_svg(x, y)
        out.append(f"{'M' if i == 0 else 'L'}{sx:.2f},{sy:.2f}")
    return "".join(out)


def projected_geom_to_path(geom: Any, vp: dict[str, Any], close: bool = True) -> str:
    """Convert a geometry *already in projected metres* into an SVG path string."""
    parts: list[str] = []
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            if poly.is_empty:
                continue
            parts.append(_projected_ring_to_path(poly.exterior.coords, vp) + "Z")
            for hole in poly.interiors:
                parts.append(_projected_ring_to_path(hole.coords, vp) + "Z")
    elif geom.geom_type in ("LineString", "MultiLineString"):
        lines = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
        for line in lines:
            if line.is_empty:
                continue
            parts.append(_projected_ring_to_path(line.coords, vp) + ("Z" if close else ""))
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# SVG helpers: defs, letter-spaced text, scale bar, north arrow                 #
# --------------------------------------------------------------------------- #

# Cartographic sans; falls back gracefully. Honors the three-Roboto rule of the
# stack when no font is pinned in the config.
_DEFAULT_FONT = "Roboto, 'Helvetica Neue', Arial, sans-serif"


def svg_defs(contested_hatch: str = "#b03a3a") -> str:
    """Return the ``<defs>`` block: soft drop-shadows, the contested hatch, markers.

    Parameters
    ----------
    contested_hatch : str
        Stroke colour of the diagonal hatch used to render a contested zone; it
        tracks the map's contested fill so the hatch reads as "the same category,
        emphasised" rather than an unrelated red.
    """
    return (
        '<defs>'
        '<filter id="panel-shadow" x="-10%" y="-10%" width="120%" height="120%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="#000" flood-opacity="0.18"/>'
        '</filter>'
        '<filter id="marker-shadow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#000" flood-opacity="0.35"/>'
        '</filter>'
        # A soft label halo used for the front-line callout and title underline.
        '<filter id="soft-shadow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feDropShadow dx="0" dy="0.6" stdDeviation="0.9" flood-color="#000" flood-opacity="0.25"/>'
        '</filter>'
        f'<pattern id="hatch-contested" width="6.5" height="6.5" patternTransform="rotate(45)" '
        'patternUnits="userSpaceOnUse">'
        f'<line x1="0" y1="0" x2="0" y2="6.5" stroke="{contested_hatch}" stroke-width="1.25" '
        'stroke-opacity="0.6"/>'
        '</pattern>'
        '</defs>'
    )


def tracked_text(
    x: float,
    y: float,
    text: str,
    *,
    size: float,
    fill: str,
    tracking: float,
    weight: str = "400",
    anchor: str = "middle",
    upper: bool = True,
    font: str = _DEFAULT_FONT,
) -> str:
    """Return a ``<text>`` with letter-spacing — the cartographer's tracked label."""
    label = text.upper() if upper else text
    # Paint-order halo: a white stroke drawn *under* the fill so the label stays
    # legible over land, sea or any zone colour — standard cartographic practice.
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{font}" font-size="{size:.1f}" font-weight="{weight}" '
        f'letter-spacing="{tracking:.2f}" fill="{fill}" '
        f'paint-order="stroke" stroke="#ffffff" stroke-width="{max(2.0, size * 0.28):.1f}" '
        f'stroke-opacity="0.85" stroke-linejoin="round">{_esc(label)}</text>'
    )


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _nice_round(value: float) -> float:
    """Return a cartographer-friendly round number <= ``value`` (1/2/5 x 10^k)."""
    if value <= 0:
        return 1.0
    exp = math.floor(math.log10(value))
    base = 10 ** exp
    for mult in (5, 2, 1):
        if mult * base <= value:
            return mult * base
    return base


def scale_bar(x: float, y: float, vp: dict[str, Any]) -> str:
    """Return a dual-unit (km + mi) scale bar sized to a round distance on the map."""
    m_per_unit = vp["m_per_unit"]
    target_units = min(vp["width"] * 0.22, 180)  # aim ~1/5 canvas, capped
    km = _nice_round(target_units * m_per_unit / 1000.0)
    mi = _nice_round(target_units * m_per_unit / 1609.34)
    km_len = km * 1000.0 / m_per_unit
    mi_len = mi * 1609.34 / m_per_unit
    ink = "#1b2733"
    ts = vp["ts"]
    fs = 10 * ts
    hw = 2.8 * ts  # bar half-height

    def bar(y0: float, length: float, total: str, unit: str) -> str:
        half = length / 2
        return (
            f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x + length:.1f}" y2="{y0:.1f}" '
            f'stroke="{ink}" stroke-width="{2.2 * ts:.1f}"/>'
            f'<rect x="{x:.1f}" y="{y0 - hw:.1f}" width="{half:.1f}" height="{2 * hw:.1f}" '
            f'fill="#fff" stroke="{ink}" stroke-width="0.8"/>'
            f'<rect x="{x + half:.1f}" y="{y0 - hw:.1f}" width="{half:.1f}" height="{2 * hw:.1f}" '
            f'fill="{ink}"/>'
            f'<text x="{x:.1f}" y="{y0 - 6 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{fs:.1f}" fill="{ink}">0</text>'
            f'<text x="{x + length:.1f}" y="{y0 - 6 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{fs:.1f}" fill="{ink}" text-anchor="end">{total}{unit}</text>'
        )

    return (
        f'<g id="scale-bar">{bar(y, km_len, _fmt_num(km), "KM")}'
        f'{bar(y + 20 * ts, mi_len, _fmt_num(mi), "MI")}</g>'
    )


def _fmt_num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _capital_star(cx: float, cy: float, r: float) -> str:
    """Return a five-point star inside a white ring — the national-capital glyph."""
    pts: list[str] = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.42
        ang = -math.pi / 2 + i * math.pi / 5
        pts.append(f"{cx + rad * math.cos(ang):.1f},{cy + rad * math.sin(ang):.1f}")
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r + 2.2:.1f}" fill="#ffffff" '
        f'fill-opacity="0.9"/>'
        f'<polygon points="{" ".join(pts)}" fill="#2f343a" stroke="#ffffff" '
        f'stroke-width="1.1" stroke-linejoin="round"/>'
    )


def north_arrow(x: float, y: float, ts: float = 1.0) -> str:
    """Return a filled north arrow with an 'N', scaled by ``ts``."""
    ink = "#1b2733"
    return (
        f'<g id="north-arrow" transform="translate({x:.1f},{y:.1f}) scale({ts:.2f})">'
        f'<path d="M0,-14 L5,6 L0,1 L-5,6 Z" fill="{ink}"/>'
        f'<text x="0" y="20" text-anchor="middle" font-family="{_DEFAULT_FONT}" '
        f'font-size="11" font-weight="600" fill="{ink}">N</text></g>'
    )


# --------------------------------------------------------------------------- #
# Plate assembly                                                                #
# --------------------------------------------------------------------------- #


def build_map(cfg: dict[str, Any]) -> str:
    """Assemble the full layered situation-map SVG from a config dict.

    Parameters
    ----------
    cfg : dict
        Parsed YAML config. See the module docstring / bundled demo for the schema.

    Returns
    -------
    str
        A complete standalone SVG document.
    """
    bbox = cfg["region"]["bbox"]
    proj = build_projection(bbox, cfg.get("projection", "auto"))
    width = float(cfg.get("canvas_width", 1000))
    pad = float(cfg.get("padding", 26))
    vp = make_viewport(proj, bbox, width, pad)
    W, H = vp["width"], vp["height"]

    basemap = cfg.get("basemap", {})
    sea_color = basemap.get("sea_color", "#a9bccb")
    land_color = basemap.get("land_color", "#faf6e4")
    coast_color = basemap.get("coast_color", "#7f97a8")

    region_box = box(bbox[0], bbox[1], bbox[2], bbox[3])
    land = load_land().intersection(region_box)
    land_proj = _project_geom(land, proj)
    region_proj = _project_geom(region_box, proj)
    sea_proj = region_proj.difference(land_proj)

    layers: list[str] = []

    # 1. basemap-sea -------------------------------------------------------- #
    layers.append(
        f'<g id="basemap-sea">'
        f'<path d="{projected_geom_to_path(sea_proj, vp)}" fill="{sea_color}"/></g>'
    )

    # 2. basemap-bathymetry ------------------------------------------------- #
    bath = basemap.get("bathymetry", {"rings": 7, "step_km": None})
    layers.append(_bathymetry_layer(land_proj, sea_proj, vp, bath))

    # 3. basemap-land ------------------------------------------------------- #
    layers.append(
        f'<g id="basemap-land">'
        f'<path d="{projected_geom_to_path(land_proj, vp)}" fill="{land_color}"/></g>'
    )

    # 3b. frontiers (international borders + neighbour labels) --------------- #
    layers.append(_frontiers_layer(cfg, proj, vp, region_box))

    # 4. areas-of-control --------------------------------------------------- #
    layers.append(_areas_of_control_layer(cfg, proj, vp))

    # 4b. coastline — a crisp hairline where land meets the sea, drawn over the
    #     control fills so the shore reads sharply against the water. Placed here
    #     (not with the land) so a coastal control zone does not paint over it.
    coast = land_proj.boundary.intersection(sea_proj.buffer(vp["m_per_unit"] * 1.5))
    coast_d = projected_geom_to_path(coast, vp, close=False)
    layers.append(
        f'<g id="coastline"><path d="{coast_d}" fill="none" stroke="{coast_color}" '
        f'stroke-width="{0.9 * vp["ts"]:.2f}" stroke-opacity="0.75" '
        f'stroke-linejoin="round" stroke-linecap="round"/></g>'
        if coast_d else '<g id="coastline"></g>'
    )

    # 5. infrastructure ----------------------------------------------------- #
    layers.append(_infrastructure_layer(cfg, proj, vp))

    # 5b. rivers (over the fills so the water reads) ------------------------ #
    layers.append(_rivers_layer(cfg, proj, vp, region_box))

    # 5c. sprezzature line — the emphasised contact line between the control zones,
    #     the single most-read feature of a situation plate.
    layers.append(_front_line_layer(cfg, proj, vp))

    # 6. forces ------------------------------------------------------------- #
    layers.append(_markers_layer(cfg.get("forces", []), proj, vp, "forces"))

    # 7. events ------------------------------------------------------------- #
    layers.append(_markers_layer(cfg.get("events", []), proj, vp, "events"))

    # 8. annotation-labels -------------------------------------------------- #
    layers.append(_labels_layer(cfg, proj, vp))

    # 9. annotation-furniture ---------------------------------------------- #
    layers.append(_furniture_layer(cfg, vp))

    # 10. legend ------------------------------------------------------------ #
    layers.append(_legend_layer(cfg, vp))

    # 11. frame ------------------------------------------------------------- #
    layers.append(
        f'<g id="frame"><rect x="1" y="1" width="{W - 2:.1f}" height="{H - 2:.1f}" '
        f'rx="6" ry="6" fill="none" stroke="#fff" stroke-width="2"/></g>'
    )

    # Float the plate on a light page: an outer margin, a soft-shadowed white
    # panel, and a rounded clip — the premium "printed plate" cue of the reference.
    frame = cfg.get("frame", {})
    margin = float(frame.get("margin", 22))
    page_color = frame.get("page_color", "#eef1f3")
    radius = float(frame.get("radius", 8))
    outer_w = W + 2 * margin
    outer_h = H + 2 * margin
    clip = (
        f'<clipPath id="plate-clip"><rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" '
        f'rx="{radius}" ry="{radius}"/></clipPath>'
    )
    hatch = cfg.get("areas_of_control", {}).get("hatch_color", "#b03a3a")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {outer_w:.1f} {outer_h:.1f}" '
        f'width="{outer_w:.1f}" height="{outer_h:.1f}">'
        f'{svg_defs(hatch)[:-7]}{clip}</defs>'
        f'<rect width="{outer_w:.1f}" height="{outer_h:.1f}" fill="{page_color}"/>'
        f'<g transform="translate({margin:.1f},{margin:.1f})">'
        f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" rx="{radius}" ry="{radius}" '
        f'fill="#ffffff" filter="url(#panel-shadow)"/>'
        f'<g clip-path="url(#plate-clip)">'
        f'<rect width="{W:.1f}" height="{H:.1f}" fill="#ffffff"/>'
        f'{"".join(layers)}'
        f'</g></g>'
        f'</svg>'
    )


def _bathymetry_layer(
    land_proj: Any, sea_proj: Any, vp: dict[str, Any], bath: dict[str, Any]
) -> str:
    """Return concentric depth-contour halos buffered out from the coast into the sea."""
    rings = int(bath.get("rings", 7))
    if rings <= 0 or sea_proj.is_empty:
        return '<g id="basemap-bathymetry"></g>'
    m_per_unit = vp["m_per_unit"]
    step_km = bath.get("step_km")
    if not step_km:
        step_km = (vp["width"] * 0.02 * m_per_unit) / 1000.0  # ~2% of canvas
    step_m = step_km * 1000.0
    color = bath.get("color", "#ffffff")
    opacity = float(bath.get("opacity", 0.5))
    coast = land_proj.boundary
    paths: list[str] = []
    for i in range(1, rings + 1):
        ring = coast.buffer(step_m * i).boundary.intersection(sea_proj)
        if ring.is_empty:
            continue
        d = projected_geom_to_path(ring, vp, close=False)
        if d:
            paths.append(
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="0.8" '
                f'stroke-opacity="{opacity:.2f}"/>'
            )
    return f'<g id="basemap-bathymetry">{"".join(paths)}</g>'


def _load_features(spec: Any, base: Path) -> list[dict[str, Any]]:
    """Return a list of GeoJSON features from an inline list or a file path."""
    if spec is None:
        return []
    if isinstance(spec, str):
        data = json.loads((base / spec).read_text() if not Path(spec).is_absolute()
                          else Path(spec).read_text())
        return data.get("features", [])
    if isinstance(spec, dict) and spec.get("type") == "FeatureCollection":
        return spec.get("features", [])
    if isinstance(spec, list):
        return spec
    return []


def _areas_of_control_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return the territory zones: pastel fill under a white casing; contested = hatch."""
    aoc = cfg.get("areas_of_control", {})
    base = Path(cfg.get("_config_dir", "."))
    features = _load_features(aoc.get("source"), base)
    if not features:
        return '<g id="areas-of-control"></g>'
    field = aoc.get("category_field", "actor")
    palette = aoc.get("palette", {})
    contested = set(aoc.get("contested", []))
    casing_w = float(aoc.get("casing_width", 2.4))
    # Fill opacity: high enough that the pastel classes read as solid territory,
    # low enough that the paper warmth and the coastline still show through.
    fill_op = float(aoc.get("fill_opacity", 0.78))

    casings: list[str] = []
    fills: list[str] = []
    for feat in features:
        props = feat.get("properties", {})
        cat = props.get(field, "")
        geom = _project_geom(shape(feat["geometry"]), proj)
        d = projected_geom_to_path(geom, vp)
        if not d:
            continue
        # White casing drawn first (under the fill) so borders read as clean seams.
        casings.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{casing_w}" '
                       f'stroke-linejoin="round"/>')
        color = palette.get(cat, "#dddddd")
        fills.append(
            f'<path d="{d}" fill="{color}" fill-opacity="{fill_op:.2f}" stroke="{color}" '
            f'stroke-width="0.7" stroke-opacity="0.95"/>'
        )
        if cat in contested:
            fills.append(f'<path d="{d}" fill="url(#hatch-contested)"/>')
    return f'<g id="areas-of-control">{"".join(casings)}{"".join(fills)}</g>'


def _infrastructure_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return roads / highways as hairlines and airports as small ticks."""
    infra = cfg.get("infrastructure", {})
    base = Path(cfg.get("_config_dir", "."))
    out: list[str] = []
    for feat in _load_features(infra.get("roads"), base):
        geom = _project_geom(shape(feat["geometry"]), proj)
        d = projected_geom_to_path(geom, vp, close=False)
        if d:
            out.append(f'<path d="{d}" fill="none" stroke="#8a8f96" stroke-width="0.7" '
                      f'stroke-opacity="0.7"/>')
    for ap in infra.get("airports", []):
        x, y = vp["to_svg"](*proj.transform(ap["lon"], ap["lat"]))
        out.append(
            f'<g transform="translate({x:.1f},{y:.1f})">'
            f'<path d="M-4,0 L4,0 M0,-4 L0,4" stroke="#5b6169" stroke-width="1.1"/>'
            f'<circle r="2.4" fill="none" stroke="#5b6169" stroke-width="1"/></g>'
        )
    return f'<g id="infrastructure">{"".join(out)}</g>'


def _frontiers_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any],
                     region_box: Any) -> str:
    """Return real international frontiers (hairline dashes) + neighbour labels.

    Every country in the vendored basemap whose outline crosses the region is
    drawn as a dashed hairline (the international-border convention, distinct
    from the solid white casing of the control zones), and the neighbours large
    enough to read are labelled. ``frontiers.focus`` names the country the plate
    is about, so it is not labelled again (its name is already in the title).
    """
    fr = cfg.get("frontiers", {})
    if fr.get("show", True) is False:
        return '<g id="frontiers"></g>'
    ts = vp["ts"]
    color = fr.get("color", "#b7bbc0")
    do_label = fr.get("label_neighbours", True)
    focus_raw = fr.get("focus", [])
    focus = {focus_raw.lower()} if isinstance(focus_raw, str) else {n.lower() for n in focus_raw}
    min_frac = float(fr.get("label_min_area_frac", 0.02))
    region_area = region_box.area
    lines: list[str] = []
    labels: list[str] = []
    for name, poly in load_countries():
        try:
            vis = poly.intersection(region_box)
        except Exception:
            continue
        if vis.is_empty:
            continue
        gp = _project_geom(poly.boundary.intersection(region_box), proj)
        d = projected_geom_to_path(gp, vp, close=False)
        if d:
            lines.append(
                f'<path d="{d}" fill="none" stroke="{color}" '
                f'stroke-width="{0.9 * ts:.1f}" stroke-opacity="0.85" '
                f'stroke-dasharray="{3.4 * ts:.1f} {2.4 * ts:.1f}"/>'
            )
        if do_label and name and name.lower() not in focus and vis.area >= min_frac * region_area:
            pt = vis.representative_point()
            x, y = vp["to_svg"](*proj.transform(pt.x, pt.y))
            labels.append(tracked_text(x, y, name, size=9.5 * ts, fill="#9ba1a7",
                                       tracking=2.2, weight="600"))
    return f'<g id="frontiers">{"".join(lines)}{"".join(labels)}</g>'


def _rivers_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any],
                  region_box: Any) -> str:
    """Return river centerlines (water blue) with italic names for the major ones.

    A river is drawn if it crosses the region; it is *labelled* when it is
    prominent enough (``scalerank <= label_max_scalerank``) and its in-view run
    is long enough, or when it is named in ``rivers.always_label``. Labels dodge
    each other and are set in italic, the cartographic convention for water.
    """
    rv = cfg.get("rivers", {})
    if rv.get("show", True) is False:
        return '<g id="rivers"></g>'
    ts = vp["ts"]
    line_color = rv.get("color", "#6f93b0")
    label_color = rv.get("label_color", "#4f7290")
    max_rank = int(rv.get("label_max_scalerank", 6))
    min_px = float(rv.get("label_min_length_frac", 0.14)) * vp["width"]
    always = {n.lower() for n in rv.get("always_label", [])}
    skip = {n.lower() for n in rv.get("skip", [])}
    m_per_unit = vp["m_per_unit"]
    lines: list[str] = []
    labels: list[str] = []
    placed: list[tuple[float, float]] = []
    labeled: set[str] = set()   # one label per named river
    for geom, name, rank in sorted(load_rivers(), key=lambda r: -r[2]):
        try:
            clipped = geom.intersection(region_box)
        except Exception:
            continue
        if clipped.is_empty:
            continue
        gp = _project_geom(clipped, proj)
        d = projected_geom_to_path(gp, vp, close=False)
        if not d:
            continue
        lines.append(
            f'<path d="{d}" fill="none" stroke="{line_color}" '
            f'stroke-width="{1.3 * ts:.1f}" stroke-opacity="0.85" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        if not name or name.lower() in skip or name.lower() in labeled:
            continue
        comp = max(getattr(gp, "geoms", [gp]), key=lambda g: g.length)
        length_px = comp.length / m_per_unit
        if not ((rank <= max_rank and length_px >= min_px) or name.lower() in always):
            continue
        mid = comp.interpolate(0.55, normalized=True)
        x, y = vp["to_svg"](mid.x, mid.y)
        if any((x - px) ** 2 + (y - py) ** 2 < (58 * ts) ** 2 for px, py in placed):
            continue
        placed.append((x, y))
        labeled.add(name.lower())
        size = 10.5 * ts
        labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'font-family="{_DEFAULT_FONT}" font-size="{size:.1f}" font-style="italic" '
            f'font-weight="500" fill="{label_color}" paint-order="stroke" '
            f'stroke="#ffffff" stroke-width="{max(2.0, size * 0.3):.1f}" '
            f'stroke-opacity="0.9" stroke-linejoin="round">{_esc(name)}</text>'
        )
    return f'<g id="rivers">{"".join(lines)}{"".join(labels)}</g>'


def _front_line_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return the emphasised contact line between the belligerents.

    The line is given by ``sprezzature.line`` (a list of ``[lon, lat]`` vertices, north
    to south). It is drawn as a two-part stroke: a soft white casing under a bold
    coloured line, the standard way a data desk makes the sprezzature read above the
    pastel control fills without adding a hard black rule. A small callout label
    (``sprezzature.label``) is set beside a chosen vertex when given.
    """
    fr = cfg.get("sprezzature", {})
    line = fr.get("line")
    if not line:
        return '<g id="front-line"></g>'
    ts = vp["ts"]
    color = fr.get("color", "#3a4149")
    from shapely.geometry import LineString  # local import: only this layer needs it

    geom = _project_geom(LineString([(p[0], p[1]) for p in line]), proj)
    d = projected_geom_to_path(geom, vp, close=False)
    if not d:
        return '<g id="front-line"></g>'
    parts = [
        # White casing so the sprezzature lifts off the pastel zones.
        f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{5.4 * ts:.1f}" '
        f'stroke-opacity="0.85" stroke-linejoin="round" stroke-linecap="round"/>',
        # The contact line itself: bold, slightly dashed so it reads as a *sprezzature*,
        # not a fixed administrative boundary.
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{2.4 * ts:.1f}" '
        f'stroke-linejoin="round" stroke-linecap="round" '
        f'stroke-dasharray="{9 * ts:.1f} {4.5 * ts:.1f}"/>',
    ]
    label = fr.get("label")
    if label:
        at = fr.get("label_at", line[0])
        x, y = vp["to_svg"](*proj.transform(at[0], at[1]))
        dx = fr.get("label_dx", 10) * ts
        dy = fr.get("label_dy", -6) * ts
        parts.append(
            f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="start" '
            f'font-family="{_DEFAULT_FONT}" font-size="{10.5 * ts:.1f}" '
            f'font-weight="700" fill="{color}" letter-spacing="1.4" '
            f'paint-order="stroke" stroke="#ffffff" stroke-width="{3.2 * ts:.1f}" '
            f'stroke-opacity="0.9" stroke-linejoin="round">{_esc(label.upper())}</text>'
        )
    return f'<g id="front-line">{"".join(parts)}</g>'


def _markers_layer(items: list[dict[str, Any]], proj: Transformer,
                   vp: dict[str, Any], layer_id: str) -> str:
    """Return point markers (forces or events) as drop-shadowed dots."""
    out: list[str] = []
    for it in items:
        x, y = vp["to_svg"](*proj.transform(it["lon"], it["lat"]))
        color = it.get("color", "#b03a3a")
        r = float(it.get("r", 5))
        out.append(
            f'<g transform="translate({x:.1f},{y:.1f})" filter="url(#marker-shadow)">'
            f'<circle r="{r:.1f}" fill="{color}" stroke="#fff" stroke-width="1.4"/></g>'
        )
    return f'<g id="{layer_id}">{"".join(out)}</g>'


def _labels_layer(cfg: dict[str, Any], proj: Transformer, vp: dict[str, Any]) -> str:
    """Return populated-place dots with offset names, plus a tracked water label.

    Each place is a small dot at its true location and a letter-spaced name set
    *beside* the dot (never on top of it). ``place["anchor"]`` steers the name —
    ``"start"`` (right, default), ``"end"`` (left), ``"above"``, ``"below"`` —
    so labels can dodge the coast, the frame, and one another. ``dot: false``
    renders a centred area label with no dot (for a region rather than a city).
    """
    out: list[str] = []
    ts = vp["ts"]
    labels = cfg.get("labels", {})
    for place in labels.get("places", []):
        x, y = vp["to_svg"](*proj.transform(place["lon"], place["lat"]))
        size = place.get("size", 13) * ts
        anchor = place.get("anchor", "start")
        tracking = place.get("tracking", 1.6)
        # A dark populated-place dot, unless this point already carries another
        # marker (e.g. a red flashpoint) — then dot:false and `clear` is set to
        # that marker's radius so the name still dodges it.
        clear = place.get("clear", 2.6) * ts
        gap = 4 * ts
        if place.get("capital"):
            # A capital gets a ringed star, the classic cartographic capital glyph.
            clear = max(clear, 7.5 * ts)
            out.append(_capital_star(x, y, 7.0 * ts))
        elif place.get("dot", True):
            out.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{2.6 * ts:.1f}" fill="#2f343a" '
                f'stroke="#ffffff" stroke-width="{1.1 * ts:.1f}"/>'
            )
        if anchor == "center":  # centred, no offset (region / free label)
            lx, ly, ta = x, y, "middle"
        elif anchor == "end":
            lx, ly, ta = x - clear - gap, y + 0.32 * size, "end"
        elif anchor == "above":
            lx, ly, ta = x, y - clear - gap, "middle"
        elif anchor == "below":
            lx, ly, ta = x, y + clear + gap + 0.72 * size, "middle"
        else:  # "start" — name to the right of the marker
            lx, ly, ta = x + clear + gap, y + 0.32 * size, "start"
        weight = "700" if place.get("capital") else "600"
        out.append(tracked_text(lx, ly, place["text"], size=size, fill="#2f363d",
                                tracking=tracking, weight=weight, anchor=ta))
    # Water labels: a single ``water`` (back-compat) and/or a list ``waters`` —
    # seas and gulfs, set in the letter-spaced blue-grey water convention.
    waters = list(labels.get("waters", []))
    if labels.get("water"):
        waters.append(labels["water"])
    for w in waters:
        x, y = vp["to_svg"](*proj.transform(w["lon"], w["lat"]))
        angle = w.get("rotate", 0)
        txt = tracked_text(x, y, w["text"], size=w.get("size", 19) * ts,
                           fill="#5c7c90", tracking=w.get("tracking", 6),
                           weight="400", upper=w.get("upper", True))
        if angle:
            out.append(f'<g transform="rotate({angle} {x:.1f} {y:.1f})">{txt}</g>')
        else:
            out.append(txt)
    return f'<g id="annotation-labels">{"".join(out)}</g>'


def _furniture_layer(cfg: dict[str, Any], vp: dict[str, Any]) -> str:
    """Return the title block, north arrow and dual-unit scale bar."""
    W, H = vp["width"], vp["height"]
    ts = vp["ts"]
    # North arrow top-right, clear of the title block top-left — no collision.
    out: list[str] = [north_arrow(W - 30 * ts, 34 * ts, ts)]
    title = cfg.get("title")
    subtitle = cfg.get("subtitle")
    if title:
        out.append(
            f'<text x="{26 * ts:.0f}" y="{40 * ts:.0f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{22 * ts:.0f}" font-weight="700" fill="#1b2733">{_esc(title)}</text>'
        )
    if subtitle:
        out.append(
            f'<text x="{26 * ts:.0f}" y="{40 * ts + 20 * ts:.0f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{12.5 * ts:.0f}" fill="#5b6169">{_esc(subtitle)}</text>'
        )
    out.append(scale_bar(26 * ts, H - 44 * ts, vp))
    return f'<g id="annotation-furniture">{"".join(out)}</g>'


def _legend_layer(cfg: dict[str, Any], vp: dict[str, Any]) -> str:
    """Return a floating legend card: a swatch per class, marker key, source line.

    Swatches are rounded squares (a filled-territory cue, unlike a point dot), a
    contested class also carries the diagonal hatch so the legend mirrors the map
    exactly, and an optional ``sprezzature.label`` swatch shows the contact-line style.
    A footer sets the as-of / provenance line so the plate is self-describing.
    """
    aoc = cfg.get("areas_of_control", {})
    palette = aoc.get("palette", {})
    if not palette:
        return '<g id="legend"></g>'
    W, H = vp["width"], vp["height"]
    ts = vp["ts"]
    contested = set(aoc.get("contested", []))
    rows = list(palette.items())
    markers = cfg.get("marker_legend", [])
    sprezzature = cfg.get("sprezzature", {})
    show_front = bool(sprezzature.get("line") and sprezzature.get("legend", True))
    footer = cfg.get("legend_footer")
    pad = 15 * ts
    row_h = 25 * ts
    panel_w = 262 * ts
    header_fs = 12.5 * ts
    row_fs = 12.5 * ts
    sw = 15 * ts        # swatch side
    extra = (len(markers) + 1 if markers else 0) + (1 if show_front else 0)
    n_rows = len(rows) + extra
    foot_h = 30 * ts if footer else 0
    panel_h = pad * 2 + 24 * ts + row_h * n_rows + foot_h
    px = W - panel_w - 22 * ts
    py = H - panel_h - 22 * ts
    tx = px + pad + sw + 10 * ts   # label x
    parts: list[str] = [
        f'<rect x="{px:.1f}" y="{py:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" '
        f'rx="{9 * ts:.1f}" fill="#ffffff" fill-opacity="0.96" filter="url(#panel-shadow)"/>',
        f'<rect x="{px:.1f}" y="{py:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" '
        f'rx="{9 * ts:.1f}" fill="none" stroke="#e4e8ec" stroke-width="1"/>',
        f'<text x="{px + pad:.1f}" y="{py + pad + 10 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
        f'font-size="{header_fs:.1f}" font-weight="700" fill="#1b2733" letter-spacing="1.2">'
        f'AREAS OF CONTROL</text>',
    ]
    fill_op = float(aoc.get("fill_opacity", 0.78))
    for i, (name, color) in enumerate(rows):
        ry = py + pad + 26 * ts + i * row_h
        sy = ry - sw / 2 - 1 * ts
        parts.append(
            f'<rect x="{px + pad:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sw:.1f}" '
            f'rx="{2.5 * ts:.1f}" fill="{color}" fill-opacity="{fill_op:.2f}" '
            f'stroke="{color}" stroke-width="1"/>'
        )
        if name in contested:
            parts.append(
                f'<rect x="{px + pad:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sw:.1f}" '
                f'rx="{2.5 * ts:.1f}" fill="url(#hatch-contested)"/>'
            )
        parts.append(
            f'<text x="{tx:.1f}" y="{ry + 4 * ts:.1f}" '
            f'font-family="{_DEFAULT_FONT}" font-size="{row_fs:.1f}" fill="#333">{_esc(name)}</text>'
        )
    idx = len(rows)
    # Front-line key row.
    if show_front:
        ry = py + pad + 26 * ts + idx * row_h
        parts.append(
            f'<line x1="{px + pad:.1f}" y1="{ry:.1f}" x2="{px + pad + sw:.1f}" y2="{ry:.1f}" '
            f'stroke="{sprezzature.get("color", "#3a4149")}" stroke-width="{2.4 * ts:.1f}" '
            f'stroke-dasharray="{7 * ts:.1f} {3.5 * ts:.1f}" stroke-linecap="round"/>'
        )
        parts.append(
            f'<text x="{tx:.1f}" y="{ry + 4 * ts:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{row_fs:.1f}" fill="#333">{_esc(sprezzature.get("legend_label", "Approx. sprezzature line"))}</text>'
        )
        idx += 1
    # Marker key, separated by a hairline divider.
    for j, mk in enumerate(markers):
        ry = py + pad + 26 * ts + (idx + j) * row_h
        if j == 0:
            dv = ry - row_h + 6 * ts
            parts.append(
                f'<line x1="{px + pad:.1f}" y1="{dv:.1f}" x2="{px + panel_w - pad:.1f}" '
                f'y2="{dv:.1f}" stroke="#e2e6ea" stroke-width="1"/>'
            )
        parts.append(
            f'<circle cx="{px + pad + sw / 2:.1f}" cy="{ry:.1f}" r="{5.5 * ts:.1f}" '
            f'fill="{mk.get("color", "#c0392b")}" stroke="#fff" stroke-width="{1.4 * ts:.1f}"/>'
        )
        parts.append(
            f'<text x="{tx:.1f}" y="{ry + 4 * ts:.1f}" '
            f'font-family="{_DEFAULT_FONT}" font-size="{row_fs:.1f}" fill="#333">'
            f'{_esc(mk.get("label", ""))}</text>'
        )
    if footer:
        fy = py + panel_h - 11 * ts
        parts.append(
            f'<line x1="{px + pad:.1f}" y1="{fy - 13 * ts:.1f}" x2="{px + panel_w - pad:.1f}" '
            f'y2="{fy - 13 * ts:.1f}" stroke="#e2e6ea" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{px + pad:.1f}" y="{fy:.1f}" font-family="{_DEFAULT_FONT}" '
            f'font-size="{9 * ts:.1f}" fill="#8b9097">{_esc(footer)}</text>'
        )
    return f'<g id="legend">{"".join(parts)}</g>'


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the generator."""
    p = argparse.ArgumentParser(description="Generate a layered situation map for any region.")
    p.add_argument("--config", required=True, help="YAML config describing the map.")
    p.add_argument("--out", required=True, help="Output SVG path.")
    p.add_argument("--render", action="store_true",
                   help="Also rasterise to PNG next to --out via render_diagram.py.")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point: read config, build the SVG, optionally rasterise."""
    args = build_parser().parse_args(argv)
    cfg = yaml.safe_load(Path(args.config).read_text())
    cfg["_config_dir"] = str(Path(args.config).resolve().parent)
    svg = build_map(cfg)
    out = Path(args.out)
    out.write_text(svg)
    print(f"wrote {out}  ({out.stat().st_size // 1024} KB)")
    if args.render:
        import subprocess

        png = out.with_suffix(".png")
        script = Path(__file__).with_name("render_diagram.py")
        subprocess.run(["python3", str(script), str(out), "--out", str(png)], check=False)
        print(f"rendered {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

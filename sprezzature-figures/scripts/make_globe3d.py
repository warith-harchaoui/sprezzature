#!/usr/bin/env python3
"""
make_globe3d
============

Build a publication-quality **3D globe** (orthographic projection of Earth)
as a single, self-contained SVG — no matplotlib, no seaborn, no plotly.

The figure answers the geospatial "3D globe / orthographic earth" capability
that Vega-Lite cannot render natively: a hemisphere of land seen from space,
with a graticule, a shaded limb, and a genuine, slow **rotation** driven by
pure SMIL. Rotation is honest — the earth is re-projected at a sequence of
central longitudes and the frames are cross-shown as a flip-book — so the
coastlines actually sweep past the limb rather than a flat picture being
spun. Back-facing geometry is culled per frame; everything is clipped to the
globe disc.

The land geometry is the vendored, offline Natural Earth land polygon
(``assets/geo/countries-50m.json``, a TopoJSON ``land`` object). The
orthographic projection is implemented here in a few lines of trigonometry,
so the script needs only ``numpy`` at runtime and no cartographic stack.

House style: Roboto, the Apple-ish system palette, ink ``#1D1D1F``,
secondary ``#6E6E73``, white background, rounded corners.

Usage
-----
    python make_globe3d.py                 # writes the SVG next to the skill
    python make_globe3d.py --out globe.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc classes.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations
from _svg import xml_escape  # noqa: E402
from _style import os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

# --------------------------------------------------------------------------- #
# House-style tokens                                                           #
# --------------------------------------------------------------------------- #

INK = "#1D1D1F"          # primary text
SECONDARY = "#6E6E73"    # subtitle / muted text
PAGE = "#FFFFFF"         # background
OCEAN = "#0A2A43"        # deep ocean fill (dark navy reads as "night side of a globe")
OCEAN_EDGE = "#0E3C5C"   # ocean toward the lit limb
LAND = "#34C759"         # Apple system green — the continents
LAND_EDGE = "#2AA149"    # coastline stroke, a shade darker than the fill
GRATICULE = "#4E7C99"    # faint blue-grey meridians / parallels over the ocean
FONT = "Roboto, 'Helvetica Neue', Arial, sans-serif"

_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "geo"
# Coarser 110m land (108 KB vs 740 KB): the globe is small enough on screen
# that 110m coastlines read identically, and a 24-frame flip-book of the
# 50m geometry ballooned the SVG to ~10 MB (janky to play in a browser).
# 110m keeps the artifact a few MB and the rotation smooth.
_LAND_TOPOJSON = _ASSETS / "countries-110m.json"


# --------------------------------------------------------------------------- #
# Vendored basemap (Natural Earth land, offline TopoJSON)                       #
# --------------------------------------------------------------------------- #


def load_land_rings() -> list[np.ndarray]:
    """Return every land ring as an ``(N, 2)`` array of ``[lon, lat]`` degrees.

    Decodes the minimal TopoJSON contract of the vendored ``land`` object:
    quantised, delta-encoded arcs plus a ``scale`` / ``translate`` transform,
    stitched into closed rings. Holes are returned as their own rings — for an
    orthographic silhouette drawn with a non-zero fill rule the winding order is
    preserved, so lakes still punch through their continents.

    Returns
    -------
    list of numpy.ndarray
        One ``(N, 2)`` float array of longitude/latitude vertices per ring.
    """
    topo = json.loads(_LAND_TOPOJSON.read_text())
    scale = topo["transform"]["scale"]
    translate = topo["transform"]["translate"]
    raw_arcs = topo["arcs"]

    def decode_arc(index: int) -> list[list[float]]:
        # A negative index means the arc is traversed in reverse (~index).
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

    rings: list[np.ndarray] = []
    for geom in topo["objects"]["land"]["geometries"]:
        gtype = geom["type"]
        if gtype == "Polygon":
            for part in geom["arcs"]:
                rings.append(np.asarray(stitch(part), dtype=float))
        elif gtype == "MultiPolygon":
            for poly in geom["arcs"]:
                for part in poly:
                    rings.append(np.asarray(stitch(part), dtype=float))
    return rings


def densify_ring(ring: np.ndarray, max_step_deg: float = 4.0) -> np.ndarray:
    """Insert intermediate vertices so long lon/lat edges curve on the sphere.

    A straight segment in lon/lat becomes a straight chord once projected, which
    cuts visible corners across the curved limb. Subdividing any edge longer than
    ``max_step_deg`` degrees keeps coastlines smooth after projection.

    Parameters
    ----------
    ring : numpy.ndarray
        ``(N, 2)`` array of ``[lon, lat]`` vertices.
    max_step_deg : float, optional
        Maximum great-ish spacing, in degrees, before an edge is split.

    Returns
    -------
    numpy.ndarray
        A denser ``(M, 2)`` ring, ``M >= N``.
    """
    out: list[np.ndarray] = []
    for i in range(len(ring)):
        a = ring[i]
        b = ring[(i + 1) % len(ring)]
        out.append(a)
        step = float(np.hypot(*(b - a)))
        n = int(step // max_step_deg)
        if n > 0:
            ts = np.linspace(0.0, 1.0, n + 2)[1:-1]
            for t in ts:
                out.append(a + (b - a) * t)
    return np.asarray(out, dtype=float)


# --------------------------------------------------------------------------- #
# Orthographic projection                                                       #
# --------------------------------------------------------------------------- #


def orthographic(
    lon: np.ndarray,
    lat: np.ndarray,
    lon0: float,
    lat0: float,
    radius: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Project lon/lat onto an orthographic disc centred at ``(lon0, lat0)``.

    Orthographic is the "seen from infinitely far away" azimuthal projection —
    exactly the view of a physical globe. A point is visible only when it sits
    on the near hemisphere, i.e. the cosine of its angular distance from the
    projection centre is positive.

    Parameters
    ----------
    lon, lat : numpy.ndarray
        Longitude / latitude of the vertices, in degrees.
    lon0, lat0 : float
        Centre of projection (the sub-viewer point), in degrees.
    radius : float
        Globe radius in SVG units.

    Returns
    -------
    x, y : numpy.ndarray
        Planar coordinates in SVG units (``y`` already flipped so north is up),
        centred on the origin.
    visible : numpy.ndarray of bool
        ``True`` where the vertex is on the near (sprezzature) hemisphere.
    """
    lam = np.radians(lon)
    lat_r = np.radians(lat)
    lam0 = math.radians(lon0)
    lat0_r = math.radians(lat0)
    cos_c = math.sin(lat0_r) * np.sin(lat_r) + math.cos(lat0_r) * np.cos(lat_r) * np.cos(lam - lam0)
    x = radius * np.cos(lat_r) * np.sin(lam - lam0)
    y = radius * (math.cos(lat0_r) * np.sin(lat_r) - math.sin(lat0_r) * np.cos(lat_r) * np.cos(lam - lam0))
    return x, -y, cos_c > 0.0


def _split_ring_to_paths(
    xs: np.ndarray, ys: np.ndarray, vis: np.ndarray, cx: float, cy: float
) -> list[str]:
    """Turn one projected ring into SVG sub-paths, breaking at the horizon.

    A ring can straddle the limb; the far-side (culled) run is dropped and the
    visible runs are emitted as separate open polylines. An open run's implicit
    fill-chord (or a segment bridging the horizon) can bulge past the circular
    silhouette, so the caller clips every painted path to the disc; the escape
    is caught geometrically rather than relied upon not to happen. Returns an
    empty list when the ring is entirely on the far side.
    """
    n = len(vis)
    if not vis.any():
        return []
    if vis.all():
        pts = "".join(
            f"{'M' if i == 0 else 'L'}{cx + xs[i]:.1f},{cy + ys[i]:.1f}" for i in range(n)
        )
        return [pts + "Z"]
    # Rotate so we start at a hidden→visible boundary, then collect visible runs.
    start = int(np.argmax(~vis & np.roll(vis, -1)))  # last hidden before a visible
    order = np.roll(np.arange(n), -(start + 1))
    paths: list[str] = []
    cur: list[str] = []
    for k in order:
        if vis[k]:
            cmd = "M" if not cur else "L"
            cur.append(f"{cmd}{cx + xs[k]:.1f},{cy + ys[k]:.1f}")
        elif cur:
            paths.append("".join(cur))
            cur = []
    if cur:
        paths.append("".join(cur))
    return paths


def land_path_for_view(
    rings: list[np.ndarray], lon0: float, lat0: float, radius: float, cx: float, cy: float
) -> str:
    """Return the combined SVG ``d`` for all land visible from ``(lon0, lat0)``."""
    subpaths: list[str] = []
    for ring in rings:
        x, y, vis = orthographic(ring[:, 0], ring[:, 1], lon0, lat0, radius)
        subpaths.extend(_split_ring_to_paths(x, y, vis, cx, cy))
    return " ".join(subpaths)


# --------------------------------------------------------------------------- #
# Graticule                                                                     #
# --------------------------------------------------------------------------- #


def graticule_paths(
    lon0: float, lat0: float, radius: float, cx: float, cy: float
) -> str:
    """Return the meridian / parallel graticule as SVG polylines for one view.

    Meridians every 30 degrees of longitude, parallels every 30 degrees of
    latitude — the light scaffolding that makes a sphere read as a sphere.
    """
    parts: list[str] = []
    # Meridians (constant longitude).
    for lon in range(-180, 180, 30):
        lat = np.linspace(-90, 90, 90)
        lonv = np.full_like(lat, lon)
        x, y, vis = orthographic(lonv, lat, lon0, lat0, radius)
        parts.extend(_split_ring_to_paths(x, y, vis, cx, cy))
    # Parallels (constant latitude).
    for lat_deg in range(-60, 90, 30):
        lonp = np.linspace(-180, 180, 180)
        latv = np.full_like(lonp, lat_deg)
        x, y, vis = orthographic(lonp, latv, lon0, lat0, radius)
        parts.extend(_split_ring_to_paths(x, y, vis, cx, cy))
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# City markers                                                                  #
# --------------------------------------------------------------------------- #

#: A handful of world cities, so the globe carries a communicative overlay
#: rather than being pure decoration. lon, lat, name.
CITIES: list[dict[str, Any]] = [
    {"name": "San Francisco", "lon": -122.4, "lat": 37.8},
    {"name": "London", "lon": -0.1, "lat": 51.5},
    {"name": "Paris", "lon": 2.35, "lat": 48.9},
    {"name": "Tokyo", "lon": 139.7, "lat": 35.7},
    {"name": "Nairobi", "lon": 36.8, "lat": -1.3},
    {"name": "São Paulo", "lon": -46.6, "lat": -23.5},
    {"name": "Sydney", "lon": 151.2, "lat": -33.9},
    {"name": "Singapore", "lon": 103.8, "lat": 1.35},
]


def city_markers(lon0: float, lat0: float, radius: float, cx: float, cy: float) -> str:
    """Return dots + labels for the cities on the near hemisphere of one view."""
    out: list[str] = []
    for c in CITIES:
        x, y, vis = orthographic(
            np.array([c["lon"]]), np.array([c["lat"]]), lon0, lat0, radius
        )
        if not bool(vis[0]):
            continue
        px, py = cx + float(x[0]), cy + float(y[0])
        # White halo disc (soft, LIGHT) under an amber core — no dark ring.
        out.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6.4" fill="#FFFFFF" '
            f'fill-opacity="0.28"/>'
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.2" fill="#FFCC00"/>'
        )
        # Near the limb, grow the label *inward* (anchor to the far side of the
        # dot) so it is not sliced off by the disc clip as the city rotates out.
        on_right = float(x[0]) > radius * 0.55
        lx = px - 9 if on_right else px + 9
        anchor = "end" if on_right else "start"
        # Label sits on a soft rounded ink plate (no hard stroke halo) so it
        # stays legible over both bright land and dark ocean — pure fills only.
        name = xml_escape(c["name"])
        w = 7.6 * len(c["name"]) + 12
        plate_x = lx - w if on_right else lx
        out.append(
            f'<rect x="{plate_x:.1f}" y="{py - 8.5:.1f}" width="{w:.1f}" '
            f'height="17" rx="6" fill="#0A2A43" fill-opacity="0.72"/>'
            f'<text x="{lx:.1f}" y="{py + 4.2:.1f}" text-anchor="{anchor}" '
            f'font-family="{FONT}" '
            f'font-size="14" font-weight="600" fill="#FFFFFF">{name}</text>'
        )
    return "".join(out)


# --------------------------------------------------------------------------- #
# SVG assembly                                                                  #
# --------------------------------------------------------------------------- #


def _pulse_keyframes(i: int, n: int) -> tuple[str, str]:
    """Return ``(keyTimes, values)`` for a discrete opacity pulse on frame ``i``.

    The pulse is opacity 1 across the half-open slot ``[i/n, (i+1)/n)`` of the
    normalised loop and 0 everywhere else — so exactly one frame of the flip-book
    is visible at any moment. keyTimes must start at 0 and end at 1 for a valid
    Vega/SMIL ``<animate>``; duplicate boundaries are de-duplicated in order.

    Parameters
    ----------
    i : int
        Index of this frame.
    n : int
        Total number of frames in one turn.

    Returns
    -------
    keytimes, values : str
        Semicolon-joined keyTimes and matching discrete opacity values.
    """
    lo = i / n
    hi = (i + 1) / n
    # Build (time, opacity) breakpoints, then collapse coincident times.
    pts: list[tuple[float, int]] = [(0.0, 0)]
    pts.append((lo, 1))
    if hi < 1.0:
        pts.append((hi, 0))
    pts.append((1.0, pts[-1][1]))
    seen: dict[float, int] = {}
    for t, v in pts:
        seen[round(t, 6)] = v  # later value wins at a shared breakpoint
    times = sorted(seen)
    keytimes = ";".join(f"{t:g}" for t in times)
    values = ";".join(str(seen[t]) for t in times)
    return keytimes, values


def build_svg(
    n_frames: int = 24,
    spin_seconds: float = 16.0,
    radius: float = 380.0,
    lat0: float = 12.0,
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full rotating-globe SVG.

    A flip-book of ``n_frames`` orthographic renders at evenly spaced central
    longitudes is stacked in one clipped group; SMIL ``<set>`` keyframes light
    exactly one frame at a time on a loop, so the earth genuinely rotates. A
    single always-on base frame is drawn first so a static rasteriser (which
    freezes SMIL at t=0) still shows a complete globe.

    Parameters
    ----------
    n_frames : int, optional
        Number of longitude steps in one full turn.
    spin_seconds : float, optional
        Wall-clock duration of a full 360 degree rotation.
    radius : float, optional
        Globe radius in SVG units.
    lat0 : float, optional
        Viewing latitude (tilt) — a small positive value looks down slightly on
        the northern hemisphere, the familiar globe pose.
    mode : str, optional
        Interactivity mode for the shared fullscreen control (see
        :mod:`_interactive`). Three modes: ``"self-contained"`` (default) ships
        a self-carrying fullscreen button and its wiring script; ``"external"``
        ships no internal button and defers to a page-level module; ``"static"``
        ships no interactivity at all. The static PNG raster is byte-identical
        across modes because the button starts hidden.
    accessibility : str, optional
        Accepted for interface parity with the other figure generators but a
        deliberate no-op here. The globe is a figure-ground *silhouette*, not a
        categorical hue code: the meaning is carried by the coastline shape, and
        the light land over dark-navy ocean already survives every colour-vision
        simulation and greyscale (checked with ``simulate_cvd.py``). Re-spacing
        the scene colours by lightness would de-tune it — the amber city dots
        collapse into a grey landmass under a monochrome level — so the shipped,
        already-accessible colours are kept unchanged for every level.

    Returns
    -------
    str
        A complete standalone SVG document.
    """
    # ``accessibility`` is intentionally not applied — see the parameter note:
    # this scene is already colour-vision- and greyscale-safe by construction.
    _ = accessibility
    rings = [densify_ring(r) for r in load_land_rings()]

    W = 1180
    H = 1040
    cx = W / 2.0
    cy = 540.0

    # Precompute every frame's land + graticule + cities.
    lons = np.linspace(0.0, 360.0, n_frames, endpoint=False)

    # Each frame is a stacked layer; a single discrete <animate> on its opacity
    # makes it opaque only during its 1/n slot of the loop, so exactly one frame
    # shows at any instant and the earth flip-books through a full turn. Using
    # one animation per frame on a shared ``spin_seconds`` timeline keeps them in
    # perfect lock-step (no drift, no double-exposure). Frame 0 is opaque at t=0
    # so a static rasteriser — which freezes SMIL at t=0 — shows a full globe.
    frame_groups: list[str] = []
    for i, lon0 in enumerate(lons):
        land_d = land_path_for_view(rings, float(lon0), lat0, radius, cx, cy)
        grat_d = graticule_paths(float(lon0), lat0, radius, cx, cy)
        cities = city_markers(float(lon0), lat0, radius, cx, cy)
        # Clip the graticule and land paths individually to the disc, not only
        # via the frame group. A limb-straddling polyline (a meridian, a parallel,
        # or a coastline ring) projects to an open run whose implicit fill-chord,
        # or a segment bridging the near and far hemisphere, can bulge past the
        # circular silhouette. Some renderers (librsvg and several SVG viewers) do
        # not honour a clip-path inherited through an animated <g>, so the group
        # clip alone is not a guarantee. A clip on each painted element is a hard
        # geometric one: nothing green can render outside the sphere on any
        # renderer. City dots and labels stay unclipped by design, since a label
        # may sit just past the limb as its city rotates out of view.
        body = (
            f'<path d="{grat_d}" fill="none" stroke="{GRATICULE}" '
            f'stroke-width="0.9" stroke-opacity="0.5" clip-path="url(#gl-disc)"/>'
            f'<path d="{land_d}" fill="{LAND}" fill-rule="evenodd" '
            f'stroke="{LAND_EDGE}" stroke-width="1.0" stroke-linejoin="round" '
            f'clip-path="url(#gl-disc)"/>'
            f"{cities}"
        )
        # Opacity pulse: 1 across this frame's slot [i/n, (i+1)/n), 0 elsewhere.
        # keyTimes are the slot boundaries; discrete calcMode gives a hard cut.
        keytimes, values = _pulse_keyframes(i, n_frames)
        start_op = "1" if i == 0 else "0"
        anim = (
            f'<animate attributeName="opacity" values="{values}" '
            f'keyTimes="{keytimes}" calcMode="discrete" '
            f'dur="{spin_seconds:.3f}s" repeatCount="indefinite"/>'
        )
        frame_groups.append(
            f'<g id="gl-f{i}" opacity="{start_op}">{anim}{body}</g>'
        )

    disc = (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}"/>'
    )

    title = "One in two humans lives on the sunward half of the globe"
    subtitle = "Orthographic view of Earth, spinning eastward through a full day"

    # prefers-contrast (perceptual / depth figure): strengthen STRUCTURE only —
    # firm up the faint graticule and thicken the globe limb ring so the sphere's
    # geometry reads harder, and deepen the secondary ink. The depth ramp (green
    # land over navy ocean, amber city dots) is left untouched: re-lighting it by
    # lightness would de-tune the "sunward-half" read. Additive + media-gated, so
    # the default animated render is byte-for-byte unchanged.
    contrast_style = (
        "@media (prefers-contrast: more){"
        f'[stroke="{GRATICULE}"]{{stroke:#2E5C79;stroke-opacity:0.85;}}'
        f'[stroke="{OCEAN}"]{{stroke-width:2.8;}}'
        f'[fill="{SECONDARY}"]{{fill:#3A3A3C;}}'
        "}"
    )
    # Additive dark-mode: the globe surface is already a dark navy in both
    # modes, and the white city dots / labels sit ON that navy, so a blanket
    # white inversion would erase them. Invert only the two ink tiers (title,
    # subtitle, footer) and darken the paper rect via its own class.
    dark_style = contrast_style + os_dark_style(
        ink_map={"#1D1D1F": "#F2F2F7", "#6E6E73": "#9C9CA3"},
        screen_blend=False,
        extra=".gl-paper{fill:#0B0B0C;}",
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" \
width="{W}" height="{H}" font-family="{FONT}" role="img" \
aria-labelledby="gl-title gl-desc">
<title id="gl-title">{xml_escape(title)}</title>
<desc id="gl-desc">A three-dimensional globe of Earth in orthographic \
projection, the continents in Apple system green over a deep-navy ocean, \
crossed by a faint 30-degree graticule. The sphere rotates eastward, one full \
turn standing in for one day, so coastlines sweep past the limb exactly as they \
would on a physical globe. Eight world cities are marked with amber dots and \
labels as each swings onto the near hemisphere.</desc>
<defs>
<clipPath id="gl-disc">{disc}</clipPath>
<radialGradient id="gl-ocean" cx="38%" cy="34%" r="78%">
<stop offset="0%" stop-color="{OCEAN_EDGE}"/>
<stop offset="100%" stop-color="{OCEAN}"/>
</radialGradient>
<radialGradient id="gl-limb" cx="50%" cy="50%" r="50%">
<stop offset="86%" stop-color="#000000" stop-opacity="0"/>
<stop offset="100%" stop-color="#001523" stop-opacity="0.55"/>
</radialGradient>
</defs>
<style>{dark_style}</style>
<rect class="gl-paper" width="{W}" height="{H}" fill="{PAGE}"/>
<text x="56" y="72" font-size="34" font-weight="700" fill="{INK}">{xml_escape(title)}</text>
<text x="56" y="106" font-size="19" fill="{SECONDARY}">{xml_escape(subtitle)}</text>
<g clip-path="url(#gl-disc)">
<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="url(#gl-ocean)"/>
{"".join(frame_groups)}
<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="url(#gl-limb)"/>
</g>
<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="none" \
stroke="#0A2A43" stroke-width="1.8"/>
<text x="56" y="{H - 40}" font-size="16" fill="{SECONDARY}">\
Natural Earth land (offline, vendored) — illustrative city set</text>
{fullscreen_control(W, H, mode)}
</svg>
"""


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the generator."""
    default_out = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "svg-examples"
        / "globe3d.svg"
    )
    p = argparse.ArgumentParser(description="Render a rotating orthographic globe SVG.")
    p.add_argument("--out", default=str(default_out), help="Output SVG path.")
    p.add_argument("--frames", type=int, default=24, help="Rotation frames per turn.")
    p.add_argument("--spin", type=float, default=16.0, help="Seconds per full turn.")
    p.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the shared fullscreen control.",
    )
    p.add_argument(
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
        # Accepted for CLI parity but a no-op: the globe is already CVD- and
        # greyscale-safe by construction (see build_svg). Colours never change.
        help="Palette accessibility level (no-op here; the globe is already CVD-safe).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to ``--out``."""
    args = build_parser().parse_args(argv)
    svg = build_svg(
        n_frames=args.frames,
        spin_seconds=args.spin,
        mode=args.mode,
        accessibility=args.accessibility,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg)
    print(f"wrote {out}  ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

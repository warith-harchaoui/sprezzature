#!/usr/bin/env python3
"""
make_windbarb — a house-styled meteorological wind-barb station plot as SVG.

A *wind barb* (or *station plot* barb) is the synoptic meteorologist's
glyph for a wind vector. A straight **staff** is drawn pointing *from*
the direction the wind blows toward the station — the way a weathervane
points into the wind. Ticks on the upwind end of the staff encode speed
in knots by a base-5 tally:

* a **pennant** (solid filled triangle) = 50 knots,
* a **full barb** (long tick) = 10 knots,
* a **half barb** (short tick) = 5 knots,
* a bare staff with a ringed station = calm / light and variable.

Read the ticks and add them up: a pennant, two full barbs and a half
barb is 50 + 20 + 5 = 75 knots. Because direction lives in the staff
angle and speed in the tally, one small mark carries a full 2-D vector —
which is why a weather chart can pack a whole wind field onto a coast
without a single number.

This example is a synoptic surface analysis of a **cold front sweeping
off the US Northeast coast**. Ahead of the sprezzature (to the southeast) a
warm, humid southwesterly flow streams up the seaboard; the blue sprezzature
line marks the leading edge; behind it a sharp wind shift brings a cold,
gusty northwesterly gale — the classic post-frontal "backing and
freshening" every mariner on that coast knows. The barbs make the shift
legible at a glance: the staffs pivot roughly 180° and the tallies grow
from a few barbs to pennants as the gale fills in behind the sprezzature.

The module builds the SVG string by hand — no matplotlib / seaborn /
plotly, and no Vega (angled staffs with tallied pennants and barbs, a
curved sprezzature glyph with triangle teeth, and side-aware station labels
are authored far more directly and compactly as raw SVG). It follows the
sprezzature-* house style from :mod:`_style`: the Apple-ish palette, Roboto
typography, ink ``#1D1D1F`` on secondary ``#6E6E73`` on a white
background, a rounded-corner legend, a takeaway title and a one-line
subtitle. Each station carries a native ``<title>`` for a
no-JavaScript hover tooltip, and CSS ``:hover`` lifts the barb.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/windbarb.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

_xml = xml_escape


# ------------------------------------------------------------------
# Canvas + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Poster-scale so every barb tally
#: and station label stays crisp at a glance.
_WIDTH: int = 1480
_HEIGHT: int = 980

#: Inner map viewport (leaves room for the header band and footnote).
_MAP_X: float = 34.0
_MAP_Y: float = 176.0
_MAP_W: float = 1052.0
_MAP_H: float = 748.0

#: House-style inks.
_INK: str = "#1D1D1F"        # primary text
_SUBTLE: str = "#6E6E73"     # secondary text
_BG: str = "#FFFFFF"         # background
_OCEAN: str = "#F2F7FB"      # faint ocean fill
_LAND: str = "#ECECEF"       # faint land silhouette
_LAND_EDGE: str = "#DADAE0"  # land hairline
_GRAT: str = "#E9EEF3"       # graticule grid
_COAST: str = "#C7CDD6"      # coastline stroke

#: Barb staff length, in pixels. Long enough to carry a full tally of
#: pennants + barbs without crowding neighbours.
_STAFF: float = 46.0

#: Tick geometry along the staff (upwind end).
_BARB_LEN: float = 20.0      # full-barb tick length
_HALF_LEN: float = 11.0      # half-barb tick length
_TICK_GAP: float = 6.6       # spacing between successive ticks
_PENNANT_LEN: float = 22.0   # pennant (triangle) reach along staff
_BARB_ANGLE: float = 118.0   # tick angle relative to the staff, degrees


# ------------------------------------------------------------------
# Data — a synoptic surface wind field across a cold front
# ------------------------------------------------------------------
# Longitudes / latitudes span the US Northeast seaboard and adjacent
# western Atlantic. ``dir_from`` is the meteorological wind direction in
# degrees (the compass bearing the wind blows FROM: 0 = north, 90 =
# east, 180 = south, 270 = west). ``speed_kt`` is sustained wind speed
# in knots. Values are a hand-built but physically faithful teaching
# field: a warm SW flow ahead of the sprezzature, a wind shift and gale behind
# it — not an official forecast.
#
# ``(name, lon, lat, dir_from_deg, speed_kt, label_side)``
_STATIONS: List[Tuple[Any, ...]] = [
    # --- Cold, gusty NW gale BEHIND the sprezzature (upper-left / inland) ---
    ("Buffalo",       -78.87, 42.89, 300, 45, "L"),
    ("Rochester",     -77.61, 43.16, 305, 40, "L"),
    ("Syracuse",      -76.15, 43.05, 310, 35, "L"),
    ("Albany",        -73.76, 42.65, 315, 40, "L"),
    ("Scranton",      -75.66, 41.41, 310, 30, "L"),
    ("Pittsburgh",    -79.98, 40.44, 300, 35, "L"),
    ("Binghamton",    -75.91, 42.10, 310, 30, "L"),
    ("Harrisburg",    -76.88, 40.27, 305, 25, "L"),
    ("Montreal",      -73.57, 45.50, 320, 50, "L"),
    ("Burlington",    -73.21, 44.48, 320, 45, "L"),
    # --- Right AT / just behind the sprezzature: the wind-shift line ---
    ("Hartford",      -72.69, 41.76, 255, 25, "R"),
    ("New York",      -74.01, 40.71, 285, 25, "L"),
    ("Philadelphia",  -75.16, 39.95, 295, 20, "L"),
    # --- Warm sector, at the coast, ahead of the sprezzature ---
    ("Boston",        -71.06, 42.36, 215, 30, "R"),
    ("Worcester",     -71.80, 42.26, 210, 20, "R"),
    # --- Warm, humid SW flow AHEAD of the sprezzature (offshore / SE) ---
    ("Portland ME",   -70.26, 43.66, 205, 25, "R"),
    ("Nantucket",     -70.10, 41.28, 210, 30, "R"),
    ("Atlantic City", -74.42, 39.36, 215, 25, "R"),
    ("Norfolk",       -76.29, 36.85, 220, 20, "R"),
    ("Cape May",      -74.91, 38.94, 215, 20, "R"),
    ("Buoy 44008",    -69.25, 40.50, 205, 35, "R"),   # offshore mooring
    ("Buoy 44025",    -73.16, 40.25, 210, 30, "R"),
    ("Buoy 44017",    -72.05, 40.69, 205, 30, "R"),
    ("Buoy 44066",    -72.64, 39.62, 205, 40, "R"),
    ("Buoy 44014",    -74.84, 36.61, 220, 25, "R"),
]

#: Stations we call out with a name label, mapped to the side the label
#: sits on ("L" / "R"). Kept sparse so the field does not choke on text;
#: these anchor the story (behind / at / ahead of the sprezzature).
_LABELLED: Dict[str, str] = {
    "Montreal":     "L",   # up-left staff -> drop the name below-left, clear
    "Buffalo":      "L",
    "Albany":       "L",
    "Pittsburgh":   "L",
    "Boston":       "R",   # warm barb leans down-right -> name to the open E
    "New York":     "L",   # straddles the sprezzature; the cold (W) side is open
    "Philadelphia": "L",
    "Nantucket":    "R",   # at the ocean edge -> name out over the water
    "Norfolk":      "R",
    "Buoy 44066":   "R",
}

#: The cold-front polyline as (lon, lat) control points, sweeping from
#: the St Lawrence down across the Mid-Atlantic and out to sea — the
#: boundary between the NW gale and the SW warm flow.
_FRONT: List[Tuple[float, float]] = [
    (-72.4, 46.2),
    (-72.6, 44.6),
    (-72.5, 43.2),
    (-72.9, 41.7),
    (-73.7, 40.3),
    (-74.5, 38.9),
    (-74.9, 37.4),
    (-74.6, 36.0),
]

#: A coarse coastline (US Northeast seaboard) as a (lon, lat) polyline —
#: enough to ground the barbs on a recognisable coast without a heavy
#: basemap dependency. Runs from Maine down to the Chesapeake.
_COASTLINE: List[Tuple[float, float]] = [
    (-70.0, 43.7),   # Casco Bay, ME
    (-70.6, 43.1),
    (-70.8, 42.9),   # NH coast
    (-70.9, 42.5),   # Cape Ann
    (-70.7, 42.3),
    (-71.0, 42.3),   # Boston
    (-70.6, 41.9),   # outer Cape
    (-70.0, 41.7),   # Cape Cod tip
    (-70.3, 41.6),
    (-70.9, 41.6),
    (-71.4, 41.5),   # RI south shore
    (-72.1, 41.3),   # CT / Long Island Sound
    (-72.9, 41.3),
    (-73.2, 41.0),   # eastern Long Island
    (-72.0, 41.0),
    (-73.0, 40.6),   # south shore LI
    (-73.8, 40.6),
    (-74.0, 40.5),   # NY Harbor
    (-74.1, 40.1),   # NJ shore
    (-74.4, 39.4),   # Atlantic City
    (-74.9, 38.9),   # Cape May
    (-75.3, 38.4),   # Delaware Bay mouth
    (-75.1, 38.0),
    (-75.5, 37.6),   # Delmarva
    (-75.9, 37.0),
    (-76.0, 36.9),   # Chesapeake mouth
    (-76.3, 36.8),   # Norfolk
]

#: Longitude / latitude window drawn (a little padding around the data).
_LON_MIN, _LON_MAX = -81.0, -67.5
_LAT_MIN, _LAT_MAX = 35.4, 46.4


# ------------------------------------------------------------------
# Projection: a simple equirectangular fit with latitude aspect
# ------------------------------------------------------------------
def _fit() -> Tuple[float, float, float, float]:
    """Return the lon/lat-to-screen fit for the map window.

    Uses an equirectangular projection with a cos(lat) correction on
    longitude so the mid-latitude coast keeps a natural aspect ratio
    (one degree of longitude is shorter than one of latitude up here).

    Returns
    -------
    tuple of float
        ``(scale, offset_x, offset_y, lon_scale)`` — the uniform pixel
        scale, the top-left screen offsets, and the longitude squeeze
        factor ``cos(mean_lat)``.
    """
    lon_scale = math.cos(math.radians((_LAT_MIN + _LAT_MAX) / 2.0))
    span_x = (_LON_MAX - _LON_MIN) * lon_scale
    span_y = _LAT_MAX - _LAT_MIN
    pad = 10.0
    scale = min((_MAP_W - 2 * pad) / span_x, (_MAP_H - 2 * pad) / span_y)
    draw_w = span_x * scale
    draw_h = span_y * scale
    offset_x = _MAP_X + (_MAP_W - draw_w) / 2.0
    offset_y = _MAP_Y + (_MAP_H - draw_h) / 2.0
    return scale, offset_x, offset_y, lon_scale


def _to_screen(lon: float, lat: float, fit: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Project one ``(lon, lat)`` to screen pixels (north up)."""
    scale, offset_x, offset_y, lon_scale = fit
    sx = offset_x + (lon - _LON_MIN) * lon_scale * scale
    sy = offset_y + (_LAT_MAX - lat) * scale
    return sx, sy


# ------------------------------------------------------------------
# Wind-barb geometry
# ------------------------------------------------------------------
def _rounded_speed(speed_kt: int) -> int:
    """Round a wind speed to the nearest 5 knots (barb tallies are base-5)."""
    return int(round(speed_kt / 5.0)) * 5


def _tally(speed_kt: int) -> Tuple[int, int, int]:
    """Decompose a wind speed (knots) into (pennants, full barbs, half barbs).

    Parameters
    ----------
    speed_kt : int
        Sustained speed in knots, already rounded to the nearest 5.

    Returns
    -------
    tuple of int
        ``(pennants, fulls, halves)`` with pennants = 50 kt, full barbs
        = 10 kt, and at most one half barb = 5 kt.
    """
    s = _rounded_speed(speed_kt)
    pennants, s = divmod(s, 50)
    fulls, s = divmod(s, 10)
    halves = s // 5
    return pennants, fulls, halves


def _barb_glyph(cx: float, cy: float, dir_from_deg: float, speed_kt: int, color: str) -> str:
    """Return the SVG fragment for one wind barb centred on a station.

    The staff points *from* the wind (meteorological convention): a wind
    blowing from the northwest draws a staff up-and-to-the-left. Ticks
    (pennants, full barbs, half barbs) are hung from the *upwind* end and
    lean back along the staff in the Northern-Hemisphere sense.

    Parameters
    ----------
    cx, cy : float
        Station centre in screen pixels.
    dir_from_deg : float
        Meteorological wind direction (degrees the wind blows FROM).
    speed_kt : int
        Sustained speed in knots.
    color : str
        Staff / tick ink.

    Returns
    -------
    str
        An SVG fragment: staff line + ticks (+ station dot).
    """
    pennants, fulls, halves = _tally(speed_kt)

    # Screen bearing: 0° = north (up). The staff extends FROM the station
    # TOWARD the source of the wind, i.e. along the "from" bearing.
    theta = math.radians(dir_from_deg)
    # Unit vector along the staff (up = -y in screen space).
    ux, uy = math.sin(theta), -math.cos(theta)
    # Staff end (the upwind tip, where ticks hang).
    ex, ey = cx + ux * _STAFF, cy + uy * _STAFF

    # Tick direction: rotate the staff direction by _BARB_ANGLE so ticks
    # fan off one side and lean back toward the station (NH convention).
    tick_ang = theta + math.radians(_BARB_ANGLE)
    tx, ty = math.sin(tick_ang), -math.cos(tick_ang)

    parts: List[str] = []
    # Staff.
    parts.append(
        f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
        f'stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>'
    )

    # Calm (no ticks): draw an open ring to signal a valid-but-light obs.
    if pennants == 0 and fulls == 0 and halves == 0:
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.6" fill="none" '
            f'stroke="{color}" stroke-width="2.2"/>'
        )
        return "".join(parts)

    # Walk down the staff from the upwind tip, placing ticks. A pennant
    # eats a wider slice than a plain barb, so it advances further.
    d = 0.0  # distance from the tip, in staff-length units of pixels

    def pt(dist: float) -> Tuple[float, float]:
        # A point on the staff, ``dist`` pixels back from the upwind tip
        # toward the station.
        return ex - ux * dist, ey - uy * dist

    # Pennants first (drawn as filled triangles hugging the staff).
    for _ in range(pennants):
        base_x, base_y = pt(d)
        apex_x = base_x + tx * _BARB_LEN
        apex_y = base_y + ty * _BARB_LEN
        tip2_x, tip2_y = pt(d + _PENNANT_LEN)
        parts.append(
            f'<path d="M{base_x:.1f},{base_y:.1f} L{apex_x:.1f},{apex_y:.1f} '
            f'L{tip2_x:.1f},{tip2_y:.1f} Z" fill="{color}"/>'
        )
        d += _PENNANT_LEN + 2.0
    if pennants:
        d += _TICK_GAP * 0.4  # small breather after the last pennant

    # Full barbs.
    for _ in range(fulls):
        bx, by = pt(d)
        parts.append(
            f'<line x1="{bx:.1f}" y1="{by:.1f}" '
            f'x2="{bx + tx * _BARB_LEN:.1f}" y2="{by + ty * _BARB_LEN:.1f}" '
            f'stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>'
        )
        d += _TICK_GAP

    # A lone half barb sits one gap in from the tip so it never rides the
    # very end of the staff (that reads as a full barb otherwise).
    for _ in range(halves):
        # If this is the only tick (5 kt), nudge it in from the tip.
        if pennants == 0 and fulls == 0:
            d = _TICK_GAP
        bx, by = pt(d)
        parts.append(
            f'<line x1="{bx:.1f}" y1="{by:.1f}" '
            f'x2="{bx + tx * _HALF_LEN:.1f}" y2="{by + ty * _HALF_LEN:.1f}" '
            f'stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>'
        )
        d += _TICK_GAP

    # Station dot at the origin, drawn last so the staff springs from it.
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.8" fill="{color}"/>')
    return "".join(parts)


# ------------------------------------------------------------------
# Airmass colour: warm ahead of the sprezzature, cold behind it
# ------------------------------------------------------------------
def _airmass_color(lon: float, lat: float, warm: str, cold: str) -> str:
    """Pick warm / cold ink by which side of the sprezzature a station sits on.

    A station is "ahead" (warm) if it lies to the SE (higher lon at its
    latitude) of the sprezzature polyline; "behind" (cold) otherwise. The sprezzature
    latitude bounds are interpolated so the test tracks the sweeping
    boundary rather than a single meridian.
    """
    # Interpolate the sprezzature's longitude at this latitude.
    front_lon = _COASTLINE[0][0]  # placeholder, overwritten below
    pts = _FRONT
    front_lon = pts[0][0]
    for (lo0, la0), (lo1, la1) in zip(pts, pts[1:]):
        lo, hi = sorted((la0, la1))
        if lo <= lat <= hi and la1 != la0:
            t = (lat - la0) / (la1 - la0)
            front_lon = lo0 + t * (lo1 - lo0)
            break
    else:
        # Above/below the sprezzature's latitude range: clamp to the nearest end.
        front_lon = pts[0][0] if lat > pts[0][1] else pts[-1][0]
    return warm if lon > front_lon else cold


# ------------------------------------------------------------------
# Build
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full wind-barb station-plot SVG document as a string.

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
    cold = palette["Blue"]     # post-frontal NW gale (cold airmass)
    warm = palette["Orange"]   # pre-frontal SW flow (warm airmass)
    front_col = palette["Blue"]

    fit = _fit()

    parts: List[str] = []
    parts.append(svg_open(_WIDTH, _HEIGHT, "wb-title", "wb-desc"))
    parts.append(
        '<title id="wb-title">A cold front sweeps the Northeast coast — '
        'wind barbs pivot 180° and freshen to a gale behind it</title>'
    )
    desc = (
        "Synoptic surface wind-barb station plot over the US Northeast "
        "seaboard and adjacent western Atlantic. Each station is a wind "
        "barb whose staff points from the wind and whose ticks tally speed "
        "in knots: a filled pennant is 50 knots, a full barb 10 knots, a "
        "half barb 5 knots. Ahead of the blue cold front a warm "
        "southwesterly flow (orange) streams up the coast at 20 to 40 knots; "
        "behind it a cold northwesterly gale (blue) reaches 45 to 50 knots, "
        "the staffs having pivoted roughly 180 degrees across the sprezzature."
    )
    parts.append(f'<desc id="wb-desc">{desc}</desc>')

    # ---- interactivity (pure CSS, no JS) ----
    style_rows = [
        ".stn { transition: transform .16s ease; transform-box: fill-box; "
        "transform-origin: center; }",
        ".stn:hover, .stn:focus { transform: scale(1.16); }",
        ".stn:focus { outline: none; }",
        "@media (prefers-reduced-motion: reduce) { .stn { transition: none; } }",
    ]
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside a media query). The two airmasses —
    # a warm southwesterly ahead of the sprezzature and a cold northwesterly behind
    # it — are colour-coded, but that colour is redundant: position relative to
    # the sprezzature line, the ~180-degree pivot of the barb staffs, and the two big
    # airmass call-outs all separate the sectors on their own. Under
    # prefers-contrast the barbs (staffs, ticks, pennants and station dots via
    # role "both") and the airmass headline labels deepen to their
    # high-contrast hues. Forced colours are left to the browser default: only
    # two hues are in play, but the map already reads without colour, so there
    # is nothing to rescue by blanking to the system palette.
    warm_barb = ".stn.air-warm line, .stn.air-warm path, .stn.air-warm circle"
    cold_barb = ".stn.air-cold line, .stn.air-cold path, .stn.air-cold circle"
    contrast_css = (
        os_adaptive_style({warm_barb: warm, cold_barb: cold}, role="both")
        + "\n"
        + os_adaptive_style(
            {"text.air-warm": warm, "text.air-cold": cold}, role="fill"
        )
    )
    # Additive OS dark-mode block. The chart's near-white base layers — ocean
    # panel (#F2F7FB), land silhouette (#ECECEF/#DADAE0), coastline (#C7CDD6) and
    # the right-hand legend card (#FBFBFD/#E6E6EB) — would glare as bright shapes
    # on a dark page, so they are remapped to quiet dark greys that still ground
    # the barbs. The white page darkens and the ink tiers flip to light via the
    # ink-map default; the warm/cold barb hues and the blue sprezzature line are data
    # and untouched. No multiply groups.
    dark_css = os_dark_style(
        screen_blend=False,
        extra='[fill="#F2F7FB"]{fill:#141821;} '
        '[fill="#ECECEF"]{fill:#1C1C1E;} '
        '[stroke="#DADAE0"]{stroke:#3A3A3C;} '
        '[stroke="#C7CDD6"]{stroke:#5A5F68;} '
        '[fill="#FBFBFD"]{fill:#161618;} '
        '[stroke="#E6E6EB"]{stroke:#3A3A3C;}',
    )
    parts.append(
        "<style>\n" + "\n".join(style_rows) + "\n" + contrast_css + "\n" + dark_css + "\n</style>"
    )

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_MAP_X + 4:.1f}" y="70" font-size="39" font-weight="700" '
        f'fill="{_INK}">A cold front swings the wind hard around the coast</text>'
    )
    parts.append(
        f'<text x="{_MAP_X + 4:.1f}" y="110" font-size="21" fill="{_SUBTLE}">'
        f'Surface analysis · warm southwesterly ahead of the sprezzature, a cold '
        f'northwesterly gale filling in behind — barb ticks tally knots</text>'
    )

    # ---- ocean panel + graticule ----
    ox, oy = _MAP_X, _MAP_Y
    parts.append(
        f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{_MAP_W:.1f}" '
        f'height="{_MAP_H:.1f}" rx="14" fill="{_OCEAN}"/>'
    )
    parts.append('<g stroke="' + _GRAT + '" stroke-width="1" fill="none">')
    for lat in range(36, 47, 2):
        p0 = _to_screen(_LON_MIN, lat, fit)
        p1 = _to_screen(_LON_MAX, lat, fit)
        parts.append(f'<path d="M{p0[0]:.1f},{p0[1]:.1f} L{p1[0]:.1f},{p1[1]:.1f}"/>')
    for lon in range(-80, -67, 3):
        p0 = _to_screen(lon, _LAT_MIN, fit)
        p1 = _to_screen(lon, _LAT_MAX, fit)
        parts.append(f'<path d="M{p0[0]:.1f},{p0[1]:.1f} L{p1[0]:.1f},{p1[1]:.1f}"/>')
    parts.append('</g>')

    # ---- land silhouette (coast filled to the west edge) ----
    # Build a closed land polygon: the coastline, then back along the map's
    # west edge, so the continent reads as a faint filled mass.
    coast_pts = [_to_screen(lon, lat, fit) for lon, lat in _COASTLINE]
    land_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in coast_pts)
    wx = ox + 2.0
    land_d += f" L{wx:.1f},{coast_pts[-1][1]:.1f} L{wx:.1f},{coast_pts[0][1]:.1f} Z"
    parts.append(
        f'<path d="{land_d}" fill="{_LAND}" stroke="none" clip-path="inset(0)"/>'
    )
    # Crisp coastline stroke on top.
    coast_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in coast_pts)
    parts.append(
        f'<path d="{coast_d}" fill="none" stroke="{_COAST}" stroke-width="1.6" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # ---- the cold front glyph (line + triangular teeth on the warm side) ----
    parts.extend(_front_glyph(fit, front_col))

    # ---- wind barbs ----
    label_parts: List[str] = []
    parts.append('<g role="list">')
    for name, lon, lat, dir_from, speed, _side in _STATIONS:
        cx, cy = _to_screen(lon, lat, fit)
        col = _airmass_color(lon, lat, warm, cold)
        rounded = _rounded_speed(speed)
        # Tag each barb with its airmass so the OS-adaptive contrast rule can
        # deepen the warm and cold barbs together (colour is a redundant key
        # here — position, staff direction and the airmass call-outs already
        # separate the two sectors).
        air_cls = "warm" if col == warm else "cold"
        parts.append(
            f'<g class="stn air-{air_cls}" tabindex="0" role="listitem">'
            f'<title>{_xml(name)}: {rounded} kt from {_dir_name(dir_from)} '
            f'({int(dir_from)}°)</title>'
            f'{_barb_glyph(cx, cy, dir_from, speed, col)}'
            f'</g>'
        )
        if name in _LABELLED:
            label_parts.append(_station_label(name, cx, cy, _LABELLED[name], rounded))
    parts.append('</g>')
    parts.append('<g>' + "".join(label_parts) + '</g>')

    # ---- airmass call-outs on the map ----
    parts.extend(_airmass_labels(fit, warm, cold))

    # ---- legend panel (right column): decode the barb symbols ----
    parts.extend(_legend(warm, cold, front_col))

    # ---- footnote / method note ----
    parts.append(
        f'<text x="{_MAP_X + 4:.1f}" y="{_HEIGHT - 22}" font-size="14" '
        f'fill="{_SUBTLE}">Staff points from the wind · pennant = 50 kt, '
        f'full barb = 10 kt, half barb = 5 kt · illustrative surface '
        f'analysis, US Northeast seaboard</text>'
    )

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def _dir_name(deg: float) -> str:
    """Return an 8-point compass name for a bearing (the wind's FROM dir)."""
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return names[int((deg % 360) / 45.0 + 0.5) % 8]


#: Vertical clearance the label block keeps below the station dot, and the
#: horizontal nudge away from the dot. Both are constant across stations so
#: every call-out reads at the same distance from its barb.
_LABEL_DY: float = 22.0      # dot-centre to name baseline
_LABEL_DX: float = 12.0      # horizontal nudge away from the dot
_LABEL_LINE: float = 17.0    # name baseline to speed baseline


def _station_label(name: str, cx: float, cy: float, side: str, rounded: int) -> str:
    """Return a two-line call-out (name + speed) placed clear of the barb.

    Each labelled station carries an explicit side (``"L"`` / ``"R"``) chosen
    so the text lands on the open side of its barb and away from the crowded
    sprezzature line. The block drops straight below the dot at a fixed clearance
    and the two lines share one anchor and one line gap, so name and speed
    stack cleanly and every station reads at the same offset from its barb.

    Parameters
    ----------
    name : str
        Station name (already trusted; escaped here).
    cx, cy : float
        Station centre in screen pixels.
    side : str
        ``"L"`` to hang the label to the left of the dot (right-anchored) or
        ``"R"`` to hang it to the right (left-anchored).
    rounded : int
        Speed in knots, rounded to the nearest 5.

    Returns
    -------
    str
        An SVG fragment with the name line and the speed line.
    """
    if side == "R":
        lx, anchor = cx + _LABEL_DX, "start"
    else:
        lx, anchor = cx - _LABEL_DX, "end"
    ly = cy + _LABEL_DY
    return (
        f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="14.5" font-weight="600" '
        f'fill="{_INK}" text-anchor="{anchor}">{_xml(name)}</text>'
        f'<text x="{lx:.1f}" y="{ly + _LABEL_LINE:.1f}" font-size="12.5" '
        f'fill="{_SUBTLE}" text-anchor="{anchor}">{rounded} kt</text>'
    )


def _front_glyph(fit: Tuple[float, float, float, float], color: str) -> List[str]:
    """Return the cold-front glyph: a smooth line with triangular teeth.

    The teeth point toward the *warm* side (the direction the sprezzature is
    moving), which for this SE-bound sprezzature is toward the ocean (screen
    right). Cold fronts wear filled triangles; this is the standard
    surface-analysis symbol.
    """
    out: List[str] = []
    pts = [_to_screen(lon, lat, fit) for lon, lat in _FRONT]

    # Smooth the polyline with a Catmull-Rom-to-Bezier pass for a graceful
    # sweeping curve rather than a kinked polyline.
    d = _smooth_path(pts)
    out.append(
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3.4" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # Triangular teeth spaced along the polyline, pointing to the warm
    # (right / SE) side — normal rotated so teeth face increasing lon.
    tooth = 15.0
    spacing = 78.0
    # Walk the polyline at fixed arc-length spacing.
    acc = spacing * 0.5
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg < 1e-6:
            continue
        dx, dy = (x1 - x0) / seg, (y1 - y0) / seg
        # Right-hand normal in screen space (points toward +x / warm side).
        nx, ny = -dy, dx
        if nx < 0:  # ensure teeth face the ocean (screen right)
            nx, ny = -nx, -ny
        pos = acc
        while pos < seg:
            bx, by = x0 + dx * pos, y0 + dy * pos
            # Tooth base spans a little along the sprezzature; apex juts outward.
            b1x, b1y = bx - dx * 7.0, by - dy * 7.0
            b2x, b2y = bx + dx * 7.0, by + dy * 7.0
            ax, ay = bx + nx * tooth, by + ny * tooth
            out.append(
                f'<path d="M{b1x:.1f},{b1y:.1f} L{ax:.1f},{ay:.1f} '
                f'L{b2x:.1f},{b2y:.1f} Z" fill="{color}"/>'
            )
            pos += spacing
        acc = pos - seg
    return out


def _smooth_path(pts: List[Tuple[float, float]]) -> str:
    """Return an SVG path ``d`` smoothing a polyline via Catmull-Rom.

    Converts each Catmull-Rom span to a cubic Bézier so the sprezzature reads
    as a single graceful sweep.
    """
    if len(pts) < 3:
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    ext = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        d.append(
            f"C{c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        )
    return " ".join(d)


def _airmass_labels(fit: Tuple[float, float, float, float], warm: str, cold: str) -> List[str]:
    """Return the two big airmass call-outs placed on their side of the sprezzature."""
    out: List[str] = []
    # Cold airmass (behind / NW).
    cx, cy = _to_screen(-79.6, 45.6, fit)
    out.append(
        f'<text class="air-cold" x="{cx:.1f}" y="{cy:.1f}" font-size="19" '
        f'font-weight="700" '
        f'fill="{cold}">COLD · NW gale</text>'
    )
    out.append(
        f'<text x="{cx:.1f}" y="{cy + 22:.1f}" font-size="14" fill="{_SUBTLE}">'
        f'post-frontal, 45–50 kt</text>'
    )
    # Warm airmass (ahead / SE, over water).
    wx, wy = _to_screen(-69.9, 37.4, fit)
    out.append(
        f'<text class="air-warm" x="{wx:.1f}" y="{wy:.1f}" font-size="19" '
        f'font-weight="700" '
        f'fill="{warm}" text-anchor="end">WARM · SW flow</text>'
    )
    out.append(
        f'<text x="{wx:.1f}" y="{wy + 22:.1f}" font-size="14" fill="{_SUBTLE}" '
        f'text-anchor="end">pre-frontal, 20–40 kt</text>'
    )
    return out


def _legend(warm: str, cold: str, front_col: str) -> List[str]:
    """Return the legend panel decoding the barb symbols and airmasses.

    A right-hand column: three worked barb examples (5, 25 and 65 kt),
    the airmass colour key, and the cold-front symbol — everything a
    reader needs to decode the map without prior meteorology.
    """
    out: List[str] = []
    lx = _MAP_X + _MAP_W + 40.0
    top = _MAP_Y + 6.0
    panel_w = _WIDTH - lx - 34.0

    # Panel card.
    out.append(
        f'<rect x="{lx - 20:.1f}" y="{top - 6:.1f}" width="{panel_w + 20:.1f}" '
        f'height="628" rx="16" fill="#FBFBFD" stroke="#E6E6EB" stroke-width="1"/>'
    )
    out.append(
        f'<text x="{lx:.1f}" y="{top + 26:.1f}" font-size="20" font-weight="700" '
        f'fill="{_INK}">How to read a wind barb</text>'
    )
    out.append(
        f'<text x="{lx:.1f}" y="{top + 50:.1f}" font-size="14" fill="{_SUBTLE}">'
        f'Staff points from the wind; ticks tally the speed.</text>'
    )

    # Three worked examples, each a barb glyph + its decoded value.
    examples = [
        (5,  "one half barb", "5 kt"),
        (25, "two full + one half", "25 kt"),
        (65, "pennant + full + half", "65 kt"),
    ]
    ey = top + 96.0
    gx = lx + 46.0   # glyph centre x
    for speed, breakdown, val in examples:
        # Draw the barb blowing from the west (staff to the left) so the
        # tally reads left-to-right for a Western reader. The staff sits at
        # ``ey + 6`` — the optical centre of the value/breakdown text pair
        # (baselines at ``ey - 4`` and ``ey + 16``) — so glyph and label
        # share one midline instead of the glyph floating above the text.
        out.append(_barb_glyph(gx, ey + 6.0, 270.0, speed, _INK))
        out.append(
            f'<text x="{lx + 110:.1f}" y="{ey - 4:.1f}" font-size="17" '
            f'font-weight="700" fill="{_INK}">{val}</text>'
        )
        out.append(
            f'<text x="{lx + 110:.1f}" y="{ey + 16:.1f}" font-size="13.5" '
            f'fill="{_SUBTLE}">{breakdown}</text>'
        )
        ey += 78.0

    # Divider.
    out.append(
        f'<line x1="{lx:.1f}" y1="{ey - 22:.1f}" x2="{lx + panel_w - 24:.1f}" '
        f'y2="{ey - 22:.1f}" stroke="#E6E6EB" stroke-width="1"/>'
    )

    # Airmass colour key.
    out.append(
        f'<text x="{lx:.1f}" y="{ey + 4:.1f}" font-size="16" font-weight="700" '
        f'fill="{_INK}">Airmass</text>'
    )
    key = [
        (warm, "Warm sector", "southwesterly, ahead of sprezzature"),
        (cold, "Cold sector", "northwesterly, behind sprezzature"),
    ]
    ky = ey + 30.0
    for col, name, sub in key:
        # A short sample barb (25 kt) in the airmass colour, its staff set on
        # the optical centre of the name/sub text pair (baselines ky-3, ky+15).
        # The centre sits at ``lx + 46`` so the west-blowing staff tip (46 px
        # to the left) lands just inside the panel card rather than poking
        # past its left border.
        out.append(_barb_glyph(lx + 46, ky + 6.0, 270.0, 25, col))
        out.append(
            f'<text x="{lx + 108:.1f}" y="{ky - 3:.1f}" font-size="15" '
            f'font-weight="600" fill="{_INK}">{name}</text>'
        )
        out.append(
            f'<text x="{lx + 108:.1f}" y="{ky + 15:.1f}" font-size="12.5" '
            f'fill="{_SUBTLE}">{sub}</text>'
        )
        ky += 56.0

    # Cold-front symbol row.
    out.append(
        f'<text x="{lx:.1f}" y="{ky + 6:.1f}" font-size="16" font-weight="700" '
        f'fill="{_INK}">Cold sprezzature</text>'
    )
    fy = ky + 34.0
    fx0, fx1 = lx + 6.0, lx + 96.0
    out.append(
        f'<line x1="{fx0:.1f}" y1="{fy:.1f}" x2="{fx1:.1f}" y2="{fy:.1f}" '
        f'stroke="{front_col}" stroke-width="3.4" stroke-linecap="round"/>'
    )
    # Two teeth on top.
    for tx in (fx0 + 26, fx0 + 62):
        out.append(
            f'<path d="M{tx - 7:.1f},{fy:.1f} L{tx:.1f},{fy - 14:.1f} '
            f'L{tx + 7:.1f},{fy:.1f} Z" fill="{front_col}"/>'
        )
    out.append(
        f'<text x="{fx1 + 16:.1f}" y="{fy + 5:.1f}" font-size="13.5" '
        f'fill="{_SUBTLE}">teeth point the way it moves</text>'
    )
    return out


def main() -> None:
    """Write the wind-barb SVG to the skill's ``svg-examples`` folder.

    The ``--mode`` flag selects the interactivity mode of the emitted SVG
    (``self-contained`` / ``external`` / ``static``); see
    :func:`_interactive.fullscreen_control`.
    """
    render_cli(
        __file__, "windbarb", build_svg, description="Render the wind-barb station-plot SVG."
    )


if __name__ == "__main__":
    main()

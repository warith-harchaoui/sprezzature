#!/usr/bin/env python3
"""
make_streamplot — house-styled streamplot of a 2D wind field as hand-authored SVG.

A streamplot traces the *streamlines* of a two-dimensional vector field:
curves everywhere tangent to the flow, so a weightless parcel dropped
into the field would ride along one. Here the field is a synthetic
surface-wind map over a coastal region — a steady westerly airflow with
a low-pressure cyclone spun up off the coast. Reading it: follow any
line downwind to see where the air goes; the darker and thicker a line,
the faster the wind along it; the tight spiral is the storm's centre,
where the flow wraps cyclonically (counter-clockwise) around the low.

The streamlines are computed offline in pure Python — the field is
sampled on a grid and each streamline is integrated with a classical
fourth-order Runge-Kutta scheme, both upstream and downstream from a
seed point, then drawn as one smooth polyline. No matplotlib / seaborn
/ plotly, and no Vega (streamline integration is not a native mark).
The figure follows the sprezzature-* house style from :mod:`_style`: a
sequential house-blue speed ramp, Roboto typography, ink ``#1D1D1F`` on
white, rounded joins, a takeaway title and a one-line subtitle. Arrow
glyphs sit at a fixed arc-length cadence along each line so direction
reads without cluttering the field, and a small speed legend maps line
darkness to wind speed.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/streamplot.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Callable, List, Tuple, cast

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier). _svg gives the XML escape helper.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _labels import label_cell  # noqa: E402
from _style import load_palette, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402


# ------------------------------------------------------------------
# Canvas + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Poster-scale so the field reads
#: at a glance and individual streamlines stay comfortably separated.
_WIDTH: int = 1200
_HEIGHT: int = 860

#: Plot rectangle (the field's drawing area) inside the canvas.
_PLOT_X0: float = 96.0
_PLOT_Y0: float = 150.0
_PLOT_X1: float = 1104.0
_PLOT_Y1: float = 792.0

#: House-style inks.
_INK: str = "#1D1D1F"      # primary text
_SUBTLE: str = "#6E6E73"   # secondary text
_GRID: str = "#E5E5EA"     # axis frame + ticks
_BG: str = "#FFFFFF"       # background
_FOCUS: str = "#0A4DA0"    # focus-ring blue

#: The field lives in a domain of "kilometres" for communicative axes.
_DOMAIN_X: Tuple[float, float] = (0.0, 640.0)
_DOMAIN_Y: Tuple[float, float] = (0.0, 400.0)

#: Storm (low-pressure) centre in domain coordinates, and its strength.
_STORM_X: float = 415.0
_STORM_Y: float = 225.0
_STORM_SWIRL: float = 72.0     # rotational strength (km/h scale)
_STORM_CORE: float = 96.0      # core radius (km); flow solid-body inside
_STORM_INFLOW: float = 20.0    # inward pull so streamlines spiral in

#: Steady background westerly (blows toward +x, i.e. eastward).
_BASE_WIND: float = 20.0       # km/h


def _field(x: float, y: float) -> Tuple[float, float]:
    """Return the wind vector ``(u, v)`` at domain point ``(x, y)``.

    The field superposes two physically-motivated pieces:

    * a **steady westerly** of speed :data:`_BASE_WIND` blowing east,
      the region's prevailing airflow; and
    * a **cyclonic vortex** centred on the low, rotating
      counter-clockwise (the Northern-Hemisphere sense) with a small
      inward component so streamlines spiral into the storm. Inside the
      core radius the rotation is solid-body (speed grows with radius);
      outside it decays like ``1/r`` as a real vortex does.

    Parameters
    ----------
    x, y : float
        Position in domain (kilometre) coordinates.

    Returns
    -------
    tuple of float
        The ``(u, v)`` wind components (km/h). ``u`` is eastward,
        ``v`` is northward (domain-up).
    """
    # Background westerly, gently sheared so the field is not perfectly
    # uniform far from the storm (upper air a touch faster).
    u = _BASE_WIND * (1.0 + 0.18 * (y - _DOMAIN_Y[1] / 2.0) / _DOMAIN_Y[1])
    v = 0.0

    # Cyclonic vortex about the low.
    dx = x - _STORM_X
    dy = y - _STORM_Y
    r = math.hypot(dx, dy)
    if r < 1e-6:
        return u, v
    # Tangential speed: solid-body inside the core, ~1/r outside.
    if r < _STORM_CORE:
        v_tan = _STORM_SWIRL * (r / _STORM_CORE)
    else:
        # Slower-than-1/r decay so the cyclonic circulation is felt well
        # beyond the core, giving the field its dominant spiral.
        v_tan = _STORM_SWIRL * (_STORM_CORE / r) ** 0.6
    # Counter-clockwise tangent unit vector is (-dy, dx) / r.
    tx, ty = -dy / r, dx / r
    # Small inward radial pull so lines spiral in (converge on the low).
    inflow = _STORM_INFLOW * min(1.0, _STORM_CORE / max(r, 1.0))
    rx, ry = -dx / r, -dy / r
    u += v_tan * tx + inflow * rx
    v += v_tan * ty + inflow * ry
    return u, v


def _speed(x: float, y: float) -> float:
    """Return the wind speed (vector magnitude) at ``(x, y)``."""
    u, v = _field(x, y)
    return math.hypot(u, v)


# ------------------------------------------------------------------
# Streamline integration (classical RK4, offline)
# ------------------------------------------------------------------
def _rk4_step(x: float, y: float, h: float) -> Tuple[float, float]:
    """Advance one RK4 step of size ``h`` along the *unit* flow direction.

    Integrating the normalised field (rather than the raw velocity)
    gives streamlines whose sample points are evenly spaced in
    arc-length, which keeps the drawn polyline smooth and the arrow
    cadence regular regardless of local wind speed.

    Parameters
    ----------
    x, y : float
        Current position in domain coordinates.
    h : float
        Step length in domain units (signed; negative integrates
        upstream).

    Returns
    -------
    tuple of float
        The next ``(x, y)`` position, or the input unchanged if the
        field magnitude has collapsed to zero (a stagnation point).
    """

    def _dir(px: float, py: float) -> Tuple[float, float]:
        u, v = _field(px, py)
        m = math.hypot(u, v)
        if m < 1e-9:
            return 0.0, 0.0
        return u / m, v / m

    k1x, k1y = _dir(x, y)
    k2x, k2y = _dir(x + 0.5 * h * k1x, y + 0.5 * h * k1y)
    k3x, k3y = _dir(x + 0.5 * h * k2x, y + 0.5 * h * k2y)
    k4x, k4y = _dir(x + h * k3x, y + h * k3y)
    nx = x + (h / 6.0) * (k1x + 2.0 * k2x + 2.0 * k3x + k4x)
    ny = y + (h / 6.0) * (k1y + 2.0 * k2y + 2.0 * k3y + k4y)
    return nx, ny


def _in_domain(x: float, y: float) -> bool:
    """Return whether ``(x, y)`` lies inside the (padded) field domain."""
    pad = 4.0
    return (
        _DOMAIN_X[0] - pad <= x <= _DOMAIN_X[1] + pad
        and _DOMAIN_Y[0] - pad <= y <= _DOMAIN_Y[1] + pad
    )


def _integrate(
    seed: Tuple[float, float],
    step: float,
    max_pts: int,
    occupied: List[List[bool]],
    grid_nx: int,
    grid_ny: int,
    cell: float,
) -> List[Tuple[float, float]]:
    """Trace one streamline through the seed, upstream then downstream.

    A coarse occupancy grid enforces a minimum spacing between
    streamlines (the classic Jobard-Lefer criterion, simplified): a new
    line stops the moment it enters a cell already claimed by an earlier
    line, so the field never turns into a solid mat of overlapping
    curves and every line stays legible.

    Parameters
    ----------
    seed : tuple of float
        Seed point in domain coordinates.
    step : float
        RK4 arc-length step in domain units.
    max_pts : int
        Cap on the number of points per half-line (guards against
        closed orbits looping forever).
    occupied : list of list of bool
        Mutable occupancy grid; cells entered by the line are marked.
    grid_nx, grid_ny : int
        Occupancy-grid dimensions.
    cell : float
        Occupancy cell size in domain units.

    Returns
    -------
    list of tuple of float
        The ordered polyline points (upstream reversed, then the seed,
        then downstream). Empty when the seed cell is already claimed.
    """

    def _cell_of(px: float, py: float) -> Tuple[int, int]:
        cx = int((px - _DOMAIN_X[0]) / cell)
        cy = int((py - _DOMAIN_Y[0]) / cell)
        cx = min(max(cx, 0), grid_nx - 1)
        cy = min(max(cy, 0), grid_ny - 1)
        return cx, cy

    sc = _cell_of(*seed)
    if occupied[sc[1]][sc[0]]:
        return []

    def _march(direction: int) -> List[Tuple[float, float]]:
        pts: List[Tuple[float, float]] = []
        x, y = seed
        h = step * direction
        for _ in range(max_pts):
            nx, ny = _rk4_step(x, y, h)
            if (nx, ny) == (x, y) or not _in_domain(nx, ny):
                break
            c = _cell_of(nx, ny)
            # Stop if we run into another line's territory (but allow the
            # first couple of steps out of the seed cell).
            if occupied[c[1]][c[0]] and len(pts) > 2:
                break
            pts.append((nx, ny))
            x, y = nx, ny
        return pts

    up = _march(-1)
    down = _march(+1)
    line = list(reversed(up)) + [seed] + down
    if len(line) < 6:
        return []

    # Claim every cell this line passes through.
    for px, py in line:
        c = _cell_of(px, py)
        occupied[c[1]][c[0]] = True
    return line


def _seed_points() -> List[Tuple[float, float]]:
    """Return an evenly spaced seed grid, storm-centre seeds first.

    Seeding the storm neighbourhood before the open field guarantees the
    defining spiral is drawn (and claims its cells) before the broad
    westerly lines fill in around it.

    Returns
    -------
    list of tuple of float
        Seed points in domain coordinates.
    """
    seeds: List[Tuple[float, float]] = []
    # Concentric rings of seeds around the low so the cyclonic wrap is
    # captured at several radii and the inward spiral is drawn densely.
    for ring_r in (_STORM_CORE * 0.45, _STORM_CORE * 0.9, _STORM_CORE * 1.5):
        for k in range(10):
            ang = 2.0 * math.pi * k / 10.0 + ring_r * 0.01
            seeds.append(
                (_STORM_X + ring_r * math.cos(ang), _STORM_Y + ring_r * math.sin(ang))
            )
    # Regular lattice over the whole domain.
    nx, ny = 16, 11
    for j in range(ny):
        for i in range(nx):
            fx = (i + 0.5) / nx
            fy = (j + 0.5) / ny
            x = _DOMAIN_X[0] + fx * (_DOMAIN_X[1] - _DOMAIN_X[0])
            y = _DOMAIN_Y[0] + fy * (_DOMAIN_Y[1] - _DOMAIN_Y[0])
            seeds.append((x, y))
    return seeds


def _streamlines() -> List[List[Tuple[float, float]]]:
    """Compute all streamlines for the field, spacing-limited.

    Returns
    -------
    list of list of tuple of float
        Each streamline as an ordered list of domain-coordinate points.
    """
    # Occupancy grid: ~one line per ~2.1 cells keeps density readable.
    cell = 15.0  # domain units per occupancy cell
    grid_nx = int(math.ceil((_DOMAIN_X[1] - _DOMAIN_X[0]) / cell)) + 1
    grid_ny = int(math.ceil((_DOMAIN_Y[1] - _DOMAIN_Y[0]) / cell)) + 1
    occupied = [[False] * grid_nx for _ in range(grid_ny)]

    step = 3.2          # RK4 arc-length step (domain units)
    max_pts = 900       # per half-line cap
    lines: List[List[Tuple[float, float]]] = []
    for seed in _seed_points():
        line = _integrate(seed, step, max_pts, occupied, grid_nx, grid_ny, cell)
        if line:
            lines.append(line)
    return lines


# ------------------------------------------------------------------
# Scales + colour ramp
# ------------------------------------------------------------------
def _make_scales() -> Tuple:
    """Return the domain-to-pixel scale functions ``(sx, sy)``.

    ``sy`` flips the axis so larger domain-y is drawn higher (north up).
    """
    px0, px1 = _PLOT_X0, _PLOT_X1
    py0, py1 = _PLOT_Y1, _PLOT_Y0  # note the flip: y grows upward

    def sx(x: float) -> float:
        t = (x - _DOMAIN_X[0]) / (_DOMAIN_X[1] - _DOMAIN_X[0])
        return px0 + t * (px1 - px0)

    def sy(y: float) -> float:
        t = (y - _DOMAIN_Y[0]) / (_DOMAIN_Y[1] - _DOMAIN_Y[0])
        return py0 + t * (py1 - py0)

    return sx, sy


def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    """Parse a ``#RRGGBB`` string into an ``(r, g, b)`` int triple."""
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    """Format an ``(r, g, b)`` triple (0-255 floats) as ``#RRGGBB``."""
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def _speed_ramp(accessibility: str = "universal") -> Callable[[float], str]:
    """Return a sequential house-blue ramp function ``speed -> hex``.

    Light sky-blue for a light breeze, deep navy for gale-force, so the
    single blue hue encodes magnitude without any colour-on-colour
    ambiguity. The ramp interpolates in RGB between three anchors.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`;
        ``"universal"`` (default) is the identity.

    Returns
    -------
    callable
        ``ramp(t)`` where ``t`` in ``[0, 1]`` returns a ``#RRGGBB`` hex.
    """
    palette = load_palette(accessibility)
    # Three-anchor blue ramp: pale sky -> house blue -> deep navy.
    pale = _hex_to_rgb("#BBDCFF")
    mid = _hex_to_rgb(palette.get("Blue", "#007AFF"))
    deep = _hex_to_rgb("#0A2E63")
    anchors = [(0.0, pale), (0.55, mid), (1.0, deep)]

    def ramp(t: float) -> str:
        t = max(0.0, min(1.0, t))
        for (t0, c0), (t1, c1) in zip(anchors, anchors[1:]):
            if t <= t1:
                f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                return _rgb_to_hex(
                    cast(
                        Tuple[float, float, float],
                        tuple(a + f * (b - a) for a, b in zip(c0, c1)),
                    )
                )
        return _rgb_to_hex(anchors[-1][1])

    return ramp


# ------------------------------------------------------------------
# Path + arrow helpers
# ------------------------------------------------------------------
def _smooth_path(pts: List[Tuple[float, float]]) -> str:
    """Return an SVG ``d`` for a Catmull-Rom-smoothed polyline.

    A cardinal (Catmull-Rom) spline through the integrated points reads
    as a continuous streamline rather than a chain of line segments,
    without the overshoot a naive Bezier through noisy points can show.

    Parameters
    ----------
    pts : list of tuple of float
        Pixel-space points along the streamline.

    Returns
    -------
    str
        The path ``d`` attribute.
    """
    if len(pts) < 2:
        return ""
    if len(pts) == 2:
        (x0, y0), (x1, y1) = pts
        return f"M {x0:.1f} {y0:.1f} L {x1:.1f} {y1:.1f}"
    d = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        # Catmull-Rom to cubic-Bezier control points (tension 0).
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        d.append(
            f"C {c1x:.1f} {c1y:.1f} {c2x:.1f} {c2y:.1f} {p2[0]:.1f} {p2[1]:.1f}"
        )
    return " ".join(d)


def _arrow(px: float, py: float, dx: float, dy: float, color: str, size: float) -> str:
    """Return a filled triangular arrowhead at ``(px, py)`` pointing ``(dx, dy)``.

    Parameters
    ----------
    px, py : float
        Tip anchor (arrow centre) in pixel space.
    dx, dy : float
        Flow direction (need not be normalised).
    color : str
        Fill hex (matched to the line's speed colour).
    size : float
        Arrow half-length in pixels.

    Returns
    -------
    str
        An SVG ``<path>`` element for the arrowhead.
    """
    m = math.hypot(dx, dy)
    if m < 1e-9:
        return ""
    ux, uy = dx / m, dy / m
    # Perpendicular (rotate the unit direction by 90 degrees).
    nx, ny = -uy, ux
    # A balanced isosceles arrowhead centred on the streamline: the tip sits
    # ``size`` ahead of the anchor, the base ``size`` behind it, so the glyph
    # straddles the flow point symmetrically and its centroid rides the line.
    half_w = size * 0.72
    tipx, tipy = px + ux * size, py + uy * size
    baxx, baxy = px - ux * size, py - uy * size
    lx, ly = baxx + nx * half_w, baxy + ny * half_w
    rx, ry = baxx - nx * half_w, baxy - ny * half_w
    return (
        f'<path d="M {tipx:.1f} {tipy:.1f} L {lx:.1f} {ly:.1f} '
        f'L {rx:.1f} {ry:.1f} Z" fill="{color}" '
        f'stroke="{color}" stroke-width="0.6" stroke-linejoin="round"/>'
    )


def _resample_by_arclength(
    pts: List[Tuple[float, float]], spacing: float
) -> List[Tuple[int, Tuple[float, float]]]:
    """Return indices + points spaced ~``spacing`` px apart along the line.

    Used to place arrowheads at a regular arc-length cadence so
    direction reads uniformly, not bunched where samples are dense.

    Parameters
    ----------
    pts : list of tuple of float
        Pixel-space polyline.
    spacing : float
        Desired arc-length between marks, in pixels.

    Returns
    -------
    list of tuple
        ``(index, point)`` pairs at the chosen cadence.
    """
    out: List[Tuple[int, Tuple[float, float]]] = []
    acc = spacing * 0.5  # first arrow a little way in from the tail
    for i in range(1, len(pts)):
        seg = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        acc += seg
        if acc >= spacing:
            out.append((i, pts[i]))
            acc = 0.0
    return out


# ------------------------------------------------------------------
# SVG assembly
# ------------------------------------------------------------------
def _axis_ticks(
    parts: List[str], sx: Callable[[float], float], sy: Callable[[float], float]
) -> None:
    """Append the plot frame, gridless axis ticks, and axis titles."""
    # Frame rectangle.
    parts.append(
        f'<rect x="{_PLOT_X0:.1f}" y="{_PLOT_Y0:.1f}" '
        f'width="{_PLOT_X1 - _PLOT_X0:.1f}" height="{_PLOT_Y1 - _PLOT_Y0:.1f}" '
        f'fill="none" stroke="{_GRID}" stroke-width="1.4"/>'
    )
    # X ticks every 80 km.
    x = _DOMAIN_X[0]
    while x <= _DOMAIN_X[1] + 0.5:
        px = sx(x)
        parts.append(
            f'<line x1="{px:.1f}" y1="{_PLOT_Y1:.1f}" x2="{px:.1f}" '
            f'y2="{_PLOT_Y1 + 7:.1f}" stroke="{_GRID}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{_PLOT_Y1 + 26:.1f}" font-size="15" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'text-anchor="middle">{int(x)}</text>'
        )
        x += 80.0
    # Y ticks every 80 km.
    y = _DOMAIN_Y[0]
    while y <= _DOMAIN_Y[1] + 0.5:
        py = sy(y)
        parts.append(
            f'<line x1="{_PLOT_X0 - 7:.1f}" y1="{py:.1f}" x2="{_PLOT_X0:.1f}" '
            f'y2="{py:.1f}" stroke="{_GRID}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{_PLOT_X0 - 12:.1f}" y="{py + 5:.1f}" font-size="15" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'text-anchor="end">{int(y)}</text>'
        )
        y += 80.0
    # Axis titles.
    parts.append(
        f'<text x="{(_PLOT_X0 + _PLOT_X1) / 2:.1f}" y="{_PLOT_Y1 + 54:.1f}" '
        f'font-size="17" font-weight="600" fill="{_INK}" '
        f'text-anchor="middle">Distance east (km)</text>'
    )
    cy = (_PLOT_Y0 + _PLOT_Y1) / 2.0
    parts.append(
        f'<text x="34" y="{cy:.1f}" font-size="17" font-weight="600" '
        f'fill="{_INK}" text-anchor="middle" '
        f'transform="rotate(-90 34 {cy:.1f})">Distance north (km)</text>'
    )


def _legend(parts: List[str], ramp: Callable[[float], str], v_min: float, v_max: float) -> None:
    """Append the sequential speed legend (line-darkness → wind speed)."""
    lx = _PLOT_X1 - 262.0
    ly = _PLOT_Y0 + 20.0
    bar_w = 232.0
    bar_h = 12.0
    # Legend backing card so the ramp reads over the busy field.
    parts.append(
        f'<rect x="{lx - 16:.1f}" y="{ly - 30:.1f}" width="{bar_w + 32:.1f}" '
        f'height="74" rx="12" fill="#FFFFFF" fill-opacity="0.92" '
        f'stroke="{_GRID}" stroke-width="1.2"/>'
    )
    parts.append(
        f'<text x="{lx:.1f}" y="{ly - 12:.1f}" font-size="15" '
        f'font-weight="700" fill="{_INK}">Wind speed (km/h)</text>'
    )
    # Gradient swatch built from discrete stops (no <defs> gradient so
    # the auditor's stdlib parser sees plain rects).
    n_stops = 40
    for k in range(n_stops):
        t = k / (n_stops - 1)
        segx = lx + t * bar_w
        parts.append(
            f'<rect x="{segx:.2f}" y="{ly:.1f}" '
            f'width="{bar_w / n_stops + 0.6:.2f}" height="{bar_h:.1f}" '
            f'fill="{ramp(t)}"/>'
        )
    # End labels only (min / max) keep it clean.
    parts.append(
        f'<text x="{lx:.1f}" y="{ly + bar_h + 18:.1f}" font-size="13" '
        f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}">'
        f'{v_min:.0f}</text>'
    )
    parts.append(
        f'<text x="{lx + bar_w:.1f}" y="{ly + bar_h + 18:.1f}" font-size="13" '
        f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
        f'text-anchor="end">{v_max:.0f}</text>'
    )


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full streamplot SVG document as a string.

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
    sx, sy = _make_scales()
    ramp = _speed_ramp(accessibility)
    lines = _streamlines()

    # Speed range for the ramp: sampled across the drawn lines.
    speeds: List[float] = []
    for line in lines:
        for x, y in line:
            speeds.append(_speed(x, y))
    speeds.sort()
    # Robust range (2nd / 98th percentile) so a couple of fast samples
    # near the eye don't wash the whole ramp toward one end.
    v_min = speeds[int(0.02 * (len(speeds) - 1))]
    v_max = speeds[int(0.98 * (len(speeds) - 1))]

    def _norm(v: float) -> float:
        if v_max <= v_min:
            return 0.5
        return (v - v_min) / (v_max - v_min)

    parts: List[str] = []

    # ---- header ----
    parts.append(svg_open(_WIDTH, _HEIGHT, "sp-title", "sp-desc"))
    parts.append(
        '<title id="sp-title">Surface wind field over the coast: a westerly '
        'airflow wraps into an offshore low</title>'
    )
    desc = (
        "Streamplot of a synthetic surface-wind field. Curved lines are "
        "streamlines everywhere tangent to the wind; arrowheads mark the "
        "flow direction and each line's colour runs from pale blue for a "
        "light breeze to deep navy for the fastest wind. A steady westerly "
        "sweeps in from the left, and a cyclonic low-pressure centre spins "
        "the flow counter-clockwise into a tight spiral offshore."
    )
    parts.append(f'<desc id="sp-desc">{xml_escape(desc)}</desc>')

    # ---- OS-adaptive style (additive; media-gated so the default light render
    # is byte-for-byte unchanged). This is a PERCEPTUAL figure — a single-hue
    # pale-blue -> navy speed ramp — so the ramp is deliberately NOT re-spaced.
    #
    # Under prefers-contrast we only STRENGTHEN STRUCTURE for a low-vision
    # reader: the secondary ink (#6E6E73 axis numbers) deepens to the primary
    # ink, and the #E5E5EA plot frame / ticks / legend keyline darken and
    # thicken so the chart scaffold reads harder. The streamline hues, arrows
    # and the red storm marker are data and untouched.
    #
    # prefers-color-scheme:dark hands it a dark paper, inverts the ink tiers,
    # darkens the #E5E5EA frame / legend keyline and the white legend card so
    # the speed swatch reads over a dark surface. No multiply groups here.
    contrast_css = (
        "@media (prefers-contrast: more){"
        f' [fill="{_SUBTLE}"]{{fill:{_INK};}}'
        f' [stroke="{_GRID}"]{{stroke:#6E6E73;stroke-width:2.2;}}'
        " }"
    )
    parts.append(
        "<style>\n"
        + contrast_css
        + "\n"
        + os_dark_style(
            screen_blend=False,
            extra='[fill="#E5E5EA"]{fill:#3A3A3C;} [stroke="#E5E5EA"]{stroke:#3A3A3C;}',
        )
        + "\n</style>"
    )

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_PLOT_X0:.0f}" y="66" font-size="32" font-weight="700" '
        f'fill="{_INK}">The storm pulls the whole airflow into its spin</text>'
    )
    parts.append(
        f'<text x="{_PLOT_X0:.0f}" y="100" font-size="18" fill="{_SUBTLE}">'
        f'Surface winds over the coast · streamlines follow the flow, '
        f'darker means faster · illustrative field</text>'
    )

    # ---- axis frame + ticks ----
    _axis_ticks(parts, sx, sy)

    # ---- clip streamlines to the plot rectangle ----
    parts.append(
        f'<clipPath id="sp-clip"><rect x="{_PLOT_X0:.1f}" y="{_PLOT_Y0:.1f}" '
        f'width="{_PLOT_X1 - _PLOT_X0:.1f}" '
        f'height="{_PLOT_Y1 - _PLOT_Y0:.1f}"/></clipPath>'
    )
    parts.append('<g clip-path="url(#sp-clip)">')

    # ---- streamlines ----
    for line in lines:
        # Pixel-space points.
        ppts = [(sx(x), sy(y)) for (x, y) in line]
        # Mean speed sets the line's colour + width (magnitude encoding).
        mid = line[len(line) // 2]
        v_here = _speed(mid[0], mid[1])
        t = _norm(v_here)
        color = ramp(t)
        # Width grows gently with speed but stays thin enough to read.
        width = 1.5 + 1.9 * t
        d = _smooth_path(ppts)
        if not d:
            continue
        parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" '
            f'stroke-width="{width:.2f}" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity="0.95"/>'
        )
        # Arrowheads at a regular arc-length cadence, coloured to match.
        arrow_spacing = 150.0
        n_pts = len(ppts)
        for idx, (ax, ay) in _resample_by_arclength(ppts, arrow_spacing):
            # Tangent from a *window* of samples straddling the anchor, not a
            # single adjacent segment: on the tightly curving spiral a lone
            # pixel-step is short and noisy, which used to twist and pinch the
            # arrowheads. Averaging a few steps either side gives the true
            # local flow direction, so every head points cleanly along its line.
            i0 = max(0, idx - 3)
            i1 = min(n_pts - 1, idx + 3)
            dx = ppts[i1][0] - ppts[i0][0]
            dy = ppts[i1][1] - ppts[i0][1]
            asize = 5.0 + 2.2 * t
            parts.append(_arrow(ax, ay, dx, dy, color, asize))

    parts.append('</g>')  # end clip group

    # ---- storm marker: a ring + call-out cell at the low's centre ----
    # Apple Red is the meteorological convention for a low-pressure "L", and
    # reads unambiguously against the all-blue speed ramp of the field.
    palette = load_palette(accessibility)
    _low_red = palette.get("Red", "#FF3B30")
    scx, scy = sx(_STORM_X), sy(_STORM_Y)
    # A small red-ringed white disc pins the eye of the storm.
    parts.append(
        f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="7.0" fill="#FFFFFF" '
        f'stroke="{_low_red}" stroke-width="2.6"/>'
    )
    # The "L" glyph sits in its own solid red chip so it never fights the
    # streamlines running underneath it.
    parts.append(
        label_cell(
            scx,
            scy - 22,
            "L",
            _low_red,
            variant="solid",
            size=15.0,
            anchor="middle",
        )
    )
    # The call-out must sit ON TOP of the busy flow field, so it uses the
    # `solid` variant: an opaque red fill, auto-contrast (white) text and a
    # white keyline lift. No black halo, no colour-on-colour.
    parts.append(
        label_cell(
            scx + 16,
            scy + 4,
            "low-pressure centre",
            _low_red,
            variant="solid",
            size=13.0,
            anchor="start",
        )
    )

    # ---- legend ----
    _legend(parts, ramp, v_min, v_max)

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the streamplot SVG to the skill's ``svg-examples`` folder.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "streamplot",
        build_svg,
        description="Write the house-style streamplot SVG example.",
    )


if __name__ == "__main__":
    main()

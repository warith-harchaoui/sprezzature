#!/usr/bin/env python3
"""Generate a publication-quality *3D scatter* figure as a standalone SVG.

A 3D scatter plots each observation as a point in three continuous
dimensions ``(x, y, z)`` and projects the cloud onto the page, so the
reader sees whether the classes separate in space that no single 2D
panel reveals. It is the matplotlib ``Axes3D.scatter`` / R
``scatterplot3d`` / plotly ``scatter3d`` idiom; seaborn has no
first-class equivalent, so a hand-built SVG is the natural home for it
here.

This module builds the SVG string **by hand** (no matplotlib / seaborn /
plotly, no Vega). The single artifact it writes is BOTH:

* a complete **still** figure — every point, the axis gizmo, the legend
  and the header are fully drawn at a fixed three-quarter viewing angle,
  so a static rasteriser (``rsvg-convert``) or an ``<img>`` embed shows a
  correct 3D scatter with no animation and no grounding shadow; and
* an **interactive** figure — a small vanilla-JavaScript block embedded
  in a ``<script>`` element re-projects the cloud live so the reader can
  **drag** to rotate, **scroll** to zoom, and **hover** a point for a
  tooltip. No external library (no d3 / three / plotly); the projection
  math mirrors :func:`_rotate` / :func:`_project` exactly, so the first
  interactive frame is pixel-identical to the server-rendered still.

Depth is reinforced three ways at every angle: nearer points are drawn
larger, more opaque, and washed less toward the white ground. Painter
ordering (far → near) is recomputed on every rotation so overlaps stay
honest.

The example data is illustrative but true-to-life: three cultivars of
grape described by three chemistry readings (colour intensity, flavanoid
content, proline), the textbook shape a 3D scatter is made to show — three
compact, well-separated clouds that a chemist would use to fingerprint an
unlabelled sample.

Usage
-----
    python make_scatter3d.py                 # writes the house SVG
    python make_scatter3d.py --out other.svg
    python make_scatter3d.py --seed 11

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc
classes, generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations
from _render import write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import forced_color_patterns, leveled_colors, os_adaptive_style, os_dark_style  # noqa: E402

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "scatter3d.svg"
)

# House-style tokens (mirrors _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"

# Three qualitative hues from the Apple-system palette — one per cultivar.
# Blue / Orange / Purple are unambiguous under the common color-vision
# deficiencies (no red<->green pair), so the class read survives without the
# depth cue doing double duty. This is the ``universal`` base set; the
# accessibility level is applied per render via :func:`_style.leveled_colors`
# (see :func:`_class_colors`), so ``--accessibility`` remaps these hues rather
# than being a no-op.
_BASE_CLASS_COLORS: Dict[str, str] = {
    "Barolo": "#007AFF",      # blue
    "Grignolino": "#FF9500",  # orange
    "Barbera": "#AF52DE",     # purple
}


def _class_colors(accessibility: str = "universal") -> Dict[str, str]:
    """Return the cultivar → hex map at a chosen accessibility level.

    The three cultivar hues are a curated *categorical* set (one hue per
    class), so they are wrapped with :func:`_style.leveled_colors`: at
    ``"universal"`` the map is returned unchanged (the shipped figure stays
    byte-for-byte identical), and every other level remaps these three hues
    through the sprezzature-colors engine.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"``,
        ``"tritanopia"``). Defaults to ``"universal"``.

    Returns
    -------
    dict of str to str
        ``{cultivar: "#RRGGBB"}`` at the requested level.
    """
    return leveled_colors(_BASE_CLASS_COLORS, accessibility)


def _class_slug(name: str) -> str:
    """Return a CSS-safe class suffix for a cultivar name.

    Used to hang a per-cultivar CSS class on both the point cloud and the
    legend swatch so an ``@media`` rule can retint them together without
    touching the default render.

    Parameters
    ----------
    name : str
        The cultivar label as shown in the legend (e.g. ``"Grignolino"``).

    Returns
    -------
    str
        A lower-cased, hyphen-joined slug usable in a ``class`` attribute and
        a CSS selector (e.g. ``"grignolino"``).
    """
    return "".join(c if c.isalnum() else "-" for c in name).strip("-").lower()

# The still is rendered at exactly the angle the interactive view starts
# from, so the <img> frame and the browser's first frame coincide.
_DEFAULT_ELEV = 20.0
_DEFAULT_AZIM = -40.0


# --------------------------------------------------------------------------- #
# Illustrative data                                                            #
# --------------------------------------------------------------------------- #
def _sample_clusters(
    n_per: int = 26, seed: int = 7
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """Sample three compact, well-separated 3D clusters — one per cultivar.

    Each cultivar is a small anisotropic Gaussian blob in the chemistry
    space ``(colour intensity, flavanoid content, proline)``. The centres
    are chosen so the three clouds barely overlap — the shape a 3D scatter
    exists to reveal — while the per-axis spreads differ so the blobs read
    as measured data rather than perfect spheres.

    Parameters
    ----------
    n_per : int, optional
        Points sampled per cultivar (the cloud holds ``3 * n_per`` points).
    seed : int, optional
        Seed for the reproducible sample.

    Returns
    -------
    tuple
        ``(X, Y, Z, labels)`` — three ``(3 * n_per,)`` coordinate arrays in
        model space (each roughly centred on the origin, span about
        ``[-1, 1]``) and a list of the cultivar label per point.
    """
    rng = np.random.default_rng(seed)
    # Cluster centres in normalised model space and their per-axis spreads.
    specs = {
        "Barolo":     {"mu": (-0.55, 0.50, 0.55), "sd": (0.20, 0.16, 0.15)},
        "Grignolino": {"mu": (0.10, -0.55, -0.10), "sd": (0.22, 0.18, 0.22)},
        "Barbera":    {"mu": (0.60, 0.35, -0.55), "sd": (0.17, 0.20, 0.16)},
    }
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    labels: List[str] = []
    for name, spec in specs.items():
        mu = spec["mu"]
        sd = spec["sd"]
        pts = rng.normal(loc=mu, scale=sd, size=(n_per, 3))
        xs.extend(pts[:, 0].tolist())
        ys.extend(pts[:, 1].tolist())
        zs.extend(pts[:, 2].tolist())
        labels.extend([name] * n_per)
    return (
        np.asarray(xs, dtype=float),
        np.asarray(ys, dtype=float),
        np.asarray(zs, dtype=float),
        labels,
    )


# --------------------------------------------------------------------------- #
# 3D -> 2D projection (the reference math the embedded JS mirrors exactly)     #
# --------------------------------------------------------------------------- #
def _rotate(pts: np.ndarray, elev_deg: float, azim_deg: float) -> np.ndarray:
    """Rotate model-space points by an azimuth then an elevation.

    The azimuth turns the cloud about the world ``z`` (up) axis; the
    elevation then tips the camera down toward the floor. Working on the
    stacked ``(N, 3)`` array keeps the whole cloud in one matmul.

    Parameters
    ----------
    pts : numpy.ndarray
        ``(N, 3)`` points ``(x, y, z)`` in model space.
    elev_deg, azim_deg : float
        Elevation and azimuth of the camera, in degrees.

    Returns
    -------
    numpy.ndarray
        ``(N, 3)`` rotated points in camera space.
    """
    az = np.radians(azim_deg)
    el = np.radians(elev_deg)
    # Azimuth: rotate about z.
    ca, sa = np.cos(az), np.sin(az)
    rz = np.array([[ca, -sa, 0.0], [sa, ca, 0.0], [0.0, 0.0, 1.0]])
    # Elevation: rotate about x (tip toward viewer).
    ce, se = np.cos(el), np.sin(el)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, ce, -se], [0.0, se, ce]])
    return pts @ rz.T @ rx.T


def _project(
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
    *,
    elev_deg: float,
    azim_deg: float,
    plot_w: float,
    plot_h: float,
    cx: float,
    cy: float,
    zoom: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rotate the cloud and project it to pixel space with a light perspective.

    This is the *reference* projection: the embedded JavaScript reproduces
    the exact same arithmetic (rotation, perspective divide, fit-scale,
    ``zoom`` multiplier) so the server-rendered still and the browser's
    first interactive frame coincide.

    Parameters
    ----------
    xs, ys, zs : numpy.ndarray
        ``(N,)`` model-space coordinates from :func:`_sample_clusters`.
    elev_deg, azim_deg : float
        Camera elevation and azimuth, in degrees.
    plot_w, plot_h : float
        Pixel extent available for the projected cloud.
    cx, cy : float
        Pixel centre the cloud is drawn around.
    zoom : float, optional
        Multiplier on the fit scale (1.0 = the still's framing). The wheel
        handler drives this in the browser; the still always uses 1.0.

    Returns
    -------
    tuple of numpy.ndarray
        ``(PX, PY, DEPTH)``, each ``(N,)`` — pixel columns, pixel rows, and
        a camera-depth value (larger = nearer the viewer) used for both
        painter ordering and the depth size/opacity cue.
    """
    pts = np.column_stack([xs, ys, zs])
    cam = _rotate(pts, elev_deg, azim_deg)
    cx_m, cy_m, cz_m = cam[:, 0], cam[:, 1], cam[:, 2]

    # Simple perspective: points farther from the camera (larger y in camera
    # space after the tip) shrink slightly. Camera sits down the -y axis.
    dist = 4.0
    denom = dist - cy_m
    persp = dist / denom
    sx = cx_m * persp
    sy = cz_m * persp  # camera-space up maps to screen up

    # Scale to fit the plot box (model x,y span ~[-1.4, 1.4] after rotation,
    # once the axis-gizmo corner is included). A slightly wider span leaves
    # head-room so the vertical +z arm clears the title band.
    span = 1.55
    scale = min(plot_w, plot_h) / (2.0 * span) * zoom
    px = cx + sx * scale
    py = cy - sy * scale  # SVG y grows downward

    # Depth for ordering / sizing: nearer the camera -> larger. Camera looks
    # down -y, so smaller cy_m is nearer; negate so "near" is the max.
    depth = -cy_m
    return px, py, depth


# --------------------------------------------------------------------------- #
# Colour helpers                                                               #
# --------------------------------------------------------------------------- #
def _lerp_hex(a: str, b: str, t: float) -> str:
    """Linearly interpolate two ``#RRGGBB`` colours in sRGB space.

    Parameters
    ----------
    a, b : str
        Endpoint colours as ``#RRGGBB``.
    t : float
        Blend factor in ``[0, 1]`` (0 -> ``a``, 1 -> ``b``).

    Returns
    -------
    str
        The blended colour as ``#RRGGBB``.
    """
    t = max(0.0, min(1.0, t))
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    r = round(ar + (br - ar) * t)
    g = round(ag + (bg - ag) * t)
    bl = round(ab + (bb - ab) * t)
    return f"#{r:02X}{g:02X}{bl:02X}"


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def _fmt(v: float) -> str:
    """Format a float compactly for SVG (1 decimal, no trailing .0)."""
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _radius_for(t: float) -> float:
    """Map a normalised depth ``t`` in ``[0, 1]`` to a point radius.

    Kept as a Python helper so the still and the embedded JS share one
    near=big / far=small law (the JS inlines the same 5 + 8 t formula).
    """
    return 5.0 + 8.0 * t


def _point_records(
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
    labels: List[str],
    class_colors: Dict[str, str],
) -> List[Dict[str, object]]:
    """Build the per-point records the SVG *and* the JS both read.

    Each record carries the model-space coordinates the JS re-projects, the
    cultivar label + colour, and the pre-formatted display values shown in
    the hover tooltip. Keeping display values here (rather than recomputing
    in JS) keeps the tooltip wording identical to the native ``<title>``.

    Parameters
    ----------
    class_colors : dict of str to str
        Cultivar → hex map at the active accessibility level.

    Returns
    -------
    list of dict
        One record per observation, JSON-serialisable.
    """
    records: List[Dict[str, object]] = []
    for i, name in enumerate(labels):
        # Shift the normalised model coords into readable positive readings.
        records.append({
            "x": round(float(xs[i]), 4),
            "y": round(float(ys[i]), 4),
            "z": round(float(zs[i]), 4),
            "label": name,
            "color": class_colors[name],
            "vcolour": round(float(xs[i]) + 1.0, 2),
            "vflav": round(float(ys[i]) + 1.0, 2),
            "vprol": round(float(zs[i]) + 1.0, 2),
        })
    return records


def _cloud_svg(
    records: List[Dict[str, object]],
    *,
    elev_deg: float,
    azim_deg: float,
    plot_w: float,
    plot_h: float,
    cx: float,
    cy: float,
) -> str:
    """Paint the depth-cued point cloud at the still's default angle.

    Each observation becomes one ``<circle>`` (id ``p<i>``) coloured by its
    cultivar. Radius, fill wash and opacity follow the point's depth so
    nearer points read larger, darker and crisper; painter ordering is
    far -> near. Every circle carries its index in ``data-i`` so the
    embedded JS can look up the point's stored 3D coordinates and re-project
    it on drag / zoom without re-parsing the DOM geometry.

    Parameters
    ----------
    records : list of dict
        Per-point records from :func:`_point_records`.
    elev_deg, azim_deg : float
        Camera angle for this (still) frame.
    plot_w, plot_h, cx, cy : float
        Projection box geometry.

    Returns
    -------
    str
        The ``<circle>`` elements, painted far -> near.
    """
    xs = np.array([r["x"] for r in records], dtype=float)
    ys = np.array([r["y"] for r in records], dtype=float)
    zs = np.array([r["z"] for r in records], dtype=float)
    px, py, depth = _project(
        xs, ys, zs,
        elev_deg=elev_deg, azim_deg=azim_deg,
        plot_w=plot_w, plot_h=plot_h, cx=cx, cy=cy,
    )

    d_lo, d_hi = float(depth.min()), float(depth.max())
    span = (d_hi - d_lo) or 1.0
    order = sorted(range(len(records)), key=lambda k: depth[k])  # far -> near

    out: List[str] = []
    for k in order:
        t = (depth[k] - d_lo) / span
        base = str(records[k]["color"])
        # Far points wash toward the white ground for an aerial-perspective cue.
        fill = _lerp_hex("#FFFFFF", base, 0.45 + 0.55 * t)
        opacity = 0.72 + 0.28 * t
        r = _radius_for(t)
        # A thin WHITE halo (never a dark ink ring) separates overlapping
        # same-cultivar marks in the dense clusters — it keeps each disk
        # legible where the blob piles up without darkening the picture.
        tip = (
            f"{records[k]['label']} — colour {records[k]['vcolour']}, "
            f"flavanoid {records[k]['vflav']}, proline {records[k]['vprol']}"
        )
        out.append(
            f'<circle id="p{k}" data-i="{k}" '
            f'class="pt3d-{_class_slug(str(records[k]["label"]))}" '
            f'cx="{_fmt(px[k])}" cy="{_fmt(py[k])}" r="{r:.2f}" '
            f'fill="{fill}" fill-opacity="{opacity:.2f}" '
            f'stroke="#FFFFFF" stroke-opacity="0.85" stroke-width="1.3">'
            f"<title>{tip}</title></circle>"
        )
    return "".join(out)


def _axis_frame_svg(
    *,
    elev_deg: float,
    azim_deg: float,
    plot_w: float,
    plot_h: float,
    cx: float,
    cy: float,
) -> str:
    """Draw the 3D axis gizmo — three labelled arms from one corner.

    A scatter cloud alone reads as points sliding around when it turns; an
    axis tripod anchors the volume so the reader sees the *space*, not just
    the dots. Three arms leave the back-bottom-left corner of the model cube
    along +x, +y and +z, each ending in its axis label. The gizmo is drawn
    at the same still angle as the cloud; the embedded JS re-projects it live
    (the arms carry ``data-a``/``data-b`` model endpoints, the labels
    ``data-tip`` model tips) so the tripod stays locked to the cloud through
    a drag.

    Returns
    -------
    str
        The axis arms + labels as SVG, in a muted grey so they never compete
        with the coloured clouds.
    """
    corner = (-1.0, 1.0, -1.0)
    arms = {
        "colour": (0.9, 1.0, -1.0),       # +x
        "flavanoid": (-1.0, -0.9, -1.0),  # -y (toward viewer)
        "proline": (-1.0, 1.0, 0.9),      # +z (up)
    }
    names = list(arms.keys())
    pts = np.array([corner] + [arms[n] for n in names], dtype=float)
    px, py, _ = _project(
        pts[:, 0], pts[:, 1], pts[:, 2],
        elev_deg=elev_deg, azim_deg=azim_deg,
        plot_w=plot_w, plot_h=plot_h, cx=cx, cy=cy,
    )
    grey = "#C7C7CC"

    out: List[str] = ['<g class="axes">']
    for j, name in enumerate(names, start=1):
        arm = arms[name]
        out.append(
            f'<line class="axis-arm" '
            f'data-a="{corner[0]},{corner[1]},{corner[2]}" '
            f'data-b="{arm[0]},{arm[1]},{arm[2]}" '
            f'x1="{_fmt(px[0])}" y1="{_fmt(py[0])}" '
            f'x2="{_fmt(px[j])}" y2="{_fmt(py[j])}" '
            f'stroke="{grey}" stroke-width="2.0" stroke-linecap="round"/>'
        )
        # Side-aware label placement at the arm tip, nudged radially outward
        # so it never sits on the arm line.
        dx_tip = px[j] - px[0]
        dy_tip = py[j] - py[0]
        norm = (dx_tip * dx_tip + dy_tip * dy_tip) ** 0.5 or 1.0
        gap = 14.0
        lx = px[j] + gap * dx_tip / norm
        ly = py[j] + gap * dy_tip / norm
        if dx_tip > norm * 0.30:
            anchor = "start"
        elif dx_tip < -norm * 0.30:
            anchor = "end"
        else:
            anchor = "middle"
        out.append(
            f'<text class="axis-label" '
            f'data-tip="{arm[0]},{arm[1]},{arm[2]}" data-gap="{gap}" '
            f'x="{_fmt(lx)}" y="{_fmt(ly)}" font-size="16" '
            f'font-family="{_MONO}" fill="{_SECONDARY}" '
            f'text-anchor="{anchor}" dominant-baseline="middle">{name}</text>'
        )
    out.append("</g>")
    return "".join(out)


def _legend_svg(x: float, y: float, class_colors: Dict[str, str]) -> str:
    """Render the cultivar colour key as a small vertical legend.

    Parameters
    ----------
    x, y : float
        Top-left pixel anchor for the legend block.
    class_colors : dict of str to str
        Cultivar → hex map at the active accessibility level.

    Returns
    -------
    str
        The legend swatches + labels as SVG.
    """
    rows: List[str] = []
    dy = 0.0
    for name, colour in class_colors.items():
        rows.append(
            f'<circle class="pt3d-{_class_slug(name)}" '
            f'cx="{_fmt(x + 8)}" cy="{_fmt(y + dy)}" r="8" '
            f'fill="{colour}"/>'
            f'<text x="{_fmt(x + 24)}" y="{_fmt(y + dy + 5)}" font-size="17" '
            f'fill="{_INK}">{name}</text>'
        )
        dy += 32.0
    return "".join(rows)


# --------------------------------------------------------------------------- #
# The embedded interactive controller (vanilla JS, no dependency)             #
# --------------------------------------------------------------------------- #
def _script_svg(
    records: List[Dict[str, object]],
    *,
    elev_deg: float,
    azim_deg: float,
    plot_w: float,
    plot_h: float,
    cx: float,
    cy: float,
    vb_w: float,
    vb_h: float,
    class_colors: Dict[str, str],
) -> str:
    """Emit the ``<script>`` that makes the still figure interactive.

    The script mirrors :func:`_rotate` / :func:`_project` in ES5/ES6 so the
    first frame it draws is identical to the server-rendered still; then it
    wires a first-class, cross-device interaction built on **Pointer Events**
    so mouse, trackpad, touch and pen all drive the same code path:

    * **one pointer dragging** -> updates azimuth (horizontal) and elevation
      (vertical) at a rect-relative sensitivity (degrees per CSS pixel read
      from the live ``getBoundingClientRect``), with elevation clamped to
      ``[-89, 89]`` so the cloud never flips inside-out; ``setPointerCapture``
      keeps the gesture even if the pointer leaves the SVG;
    * **two pointers** (touch/pen) -> pinch-zoom by the ratio of the current
      to the previous finger distance, zoomed toward the pinch midpoint;
    * **wheel** (mouse wheel + trackpad two-finger scroll) -> zoom, with
      ``deltaMode`` normalised (line vs pixel) and the page scroll suppressed
      (``preventDefault`` under ``{passive:false}``), zoomed toward the
      pointer;
    * **double-click / double-tap** -> reset to the default view;
    * **hover** -> a rounded-rect tooltip near the point, hidden on out;
    * the on-figure **hint pill** fades out on the first interaction.

    A graceful fallback keeps mouse drag + wheel working if the browser has
    no Pointer Events. The point records and the fixed projection geometry are
    handed to JS as a JSON blob so the browser owns all live math; geometry
    constants (``cx``, ``cy``, ``plot``, ``span``, ``dist``) match the Python
    projection exactly.

    Returns
    -------
    str
        A ``<script>`` element (CDATA-wrapped) ready to drop into the SVG.
    """
    cfg = {
        "pts": records,
        "elev0": elev_deg,
        "azim0": azim_deg,
        "cx": cx,
        "cy": cy,
        "cx0": cx,   # pristine centre for reset (cx/cy drift with zoom-about)
        "cy0": cy,
        "plotW": plot_w,
        "plotH": plot_h,
        "vbW": vb_w,  # full viewBox extent, for client<->viewBox mapping
        "vbH": vb_h,
        "span": 1.55,
        "dist": 4.0,
        "colors": class_colors,
    }
    data = json.dumps(cfg, separators=(",", ":"))

    # The JS below is deliberately framework-free ES5/ES6. It is embedded in a
    # CDATA block so '<' / '&' in the code never need XML escaping.
    js = r"""
var CFG = __CFG__;
var svg = document.currentScript && document.currentScript.ownerSVGElement;
if (!svg) { svg = document.querySelector('svg'); }
var NS = 'http://www.w3.org/2000/svg';

// --- state -------------------------------------------------------------
var azim = CFG.azim0, elev = CFG.elev0, zoom = 1.0;
var pts = CFG.pts;
var N = pts.length;

// --- projection: an exact mirror of the Python _rotate / _project ------
function project() {
  var az = azim * Math.PI / 180, el = elev * Math.PI / 180;
  var ca = Math.cos(az), sa = Math.sin(az);
  var ce = Math.cos(el), se = Math.sin(el);
  var scale = Math.min(CFG.plotW, CFG.plotH) / (2 * CFG.span) * zoom;
  var out = new Array(N);
  for (var i = 0; i < N; i++) {
    var p = pts[i];
    // azimuth about z
    var x1 = ca * p.x - sa * p.y;
    var y1 = sa * p.x + ca * p.y;
    var z1 = p.z;
    // elevation about x
    var x2 = x1;
    var y2 = ce * y1 - se * z1;
    var z2 = se * y1 + ce * z1;
    var persp = CFG.dist / (CFG.dist - y2);
    var px = CFG.cx + (x2 * persp) * scale;
    var py = CFG.cy - (z2 * persp) * scale;
    out[i] = { px: px, py: py, depth: -y2, i: i };
  }
  return out;
}

// project a single arbitrary model point (for the axis gizmo)
function projectOne(mx, my, mz) {
  var az = azim * Math.PI / 180, el = elev * Math.PI / 180;
  var ca = Math.cos(az), sa = Math.sin(az);
  var ce = Math.cos(el), se = Math.sin(el);
  var scale = Math.min(CFG.plotW, CFG.plotH) / (2 * CFG.span) * zoom;
  var x1 = ca * mx - sa * my, y1 = sa * mx + ca * my, z1 = mz;
  var y2 = ce * y1 - se * z1, z2 = se * y1 + ce * z1, x2 = x1;
  var persp = CFG.dist / (CFG.dist - y2);
  return { px: CFG.cx + (x2 * persp) * scale, py: CFG.cy - (z2 * persp) * scale };
}

// --- render: update every circle's cx/cy/r/fill + painter order --------
function fmt(v) { return (Math.round(v * 10) / 10); }
function hexBlend(base, t) {  // white -> the point's own base color, factor t
  t = Math.max(0, Math.min(1, t));
  var r = parseInt(base.substr(1, 2), 16),
      g = parseInt(base.substr(3, 2), 16),
      b = parseInt(base.substr(5, 2), 16);
  r = Math.round(255 + (r - 255) * t);
  g = Math.round(255 + (g - 255) * t);
  b = Math.round(255 + (b - 255) * t);
  function h(n) { var s = n.toString(16); return s.length < 2 ? '0' + s : s; }
  return '#' + h(r) + h(g) + h(b);
}

var cloud = svg.querySelector('g.cloud');

function render() {
  var proj = project();
  var dlo = Infinity, dhi = -Infinity;
  for (var i = 0; i < N; i++) {
    if (proj[i].depth < dlo) dlo = proj[i].depth;
    if (proj[i].depth > dhi) dhi = proj[i].depth;
  }
  var span = (dhi - dlo) || 1;
  // far -> near so the painter order is correct after re-ordering the DOM
  proj.sort(function (a, b) { return a.depth - b.depth; });
  for (var k = 0; k < N; k++) {
    var pr = proj[k];
    var el = document.getElementById('p' + pr.i);
    if (!el) continue;
    var t = (pr.depth - dlo) / span;
    el.setAttribute('cx', fmt(pr.px));
    el.setAttribute('cy', fmt(pr.py));
    el.setAttribute('r', (5.0 + 8.0 * t).toFixed(2));
    el.setAttribute('fill', hexBlend(pts[pr.i].color, 0.45 + 0.55 * t));
    el.setAttribute('fill-opacity', (0.72 + 0.28 * t).toFixed(2));
    cloud.appendChild(el);  // re-append near points last (drawn on top)
  }
  renderAxes();
}

function renderAxes() {
  var arms = svg.querySelectorAll('line.axis-arm');
  for (var i = 0; i < arms.length; i++) {
    var a = arms[i].getAttribute('data-a').split(',').map(Number);
    var b = arms[i].getAttribute('data-b').split(',').map(Number);
    var pa = projectOne(a[0], a[1], a[2]);
    var pb = projectOne(b[0], b[1], b[2]);
    arms[i].setAttribute('x1', fmt(pa.px)); arms[i].setAttribute('y1', fmt(pa.py));
    arms[i].setAttribute('x2', fmt(pb.px)); arms[i].setAttribute('y2', fmt(pb.py));
  }
  var labels = svg.querySelectorAll('text.axis-label');
  // shared corner is the first arm's data-a
  var corner = arms.length ? arms[0].getAttribute('data-a').split(',').map(Number)
                           : [0, 0, 0];
  var pc = projectOne(corner[0], corner[1], corner[2]);
  for (var j = 0; j < labels.length; j++) {
    var tip = labels[j].getAttribute('data-tip').split(',').map(Number);
    var gap = parseFloat(labels[j].getAttribute('data-gap')) || 14;
    var pt = projectOne(tip[0], tip[1], tip[2]);
    var dx = pt.px - pc.px, dy = pt.py - pc.py;
    var norm = Math.sqrt(dx * dx + dy * dy) || 1;
    labels[j].setAttribute('x', fmt(pt.px + gap * dx / norm));
    labels[j].setAttribute('y', fmt(pt.py + gap * dy / norm));
    labels[j].setAttribute('text-anchor',
      dx > norm * 0.30 ? 'start' : (dx < -norm * 0.30 ? 'end' : 'middle'));
  }
}

// --- tooltip -----------------------------------------------------------
var tip = null;
function ensureTip() {
  if (tip) return tip;
  tip = document.createElementNS(NS, 'g');
  tip.setAttribute('class', 'tooltip');
  tip.setAttribute('pointer-events', 'none');
  tip.style.display = 'none';
  var rect = document.createElementNS(NS, 'rect');
  rect.setAttribute('rx', '8'); rect.setAttribute('ry', '8');
  rect.setAttribute('fill', '#1D1D1F'); rect.setAttribute('fill-opacity', '0.95');
  var t1 = document.createElementNS(NS, 'text');
  t1.setAttribute('x', '12'); t1.setAttribute('y', '22');
  t1.setAttribute('fill', '#FFFFFF'); t1.setAttribute('font-size', '16');
  t1.setAttribute('font-weight', '700');
  t1.setAttribute('font-family', 'Roboto, system-ui, sans-serif');
  var t2 = document.createElementNS(NS, 'text');
  t2.setAttribute('x', '12'); t2.setAttribute('y', '44');
  t2.setAttribute('fill', '#F5F5F7'); t2.setAttribute('font-size', '14');
  t2.setAttribute('font-family', 'Roboto Mono, ui-monospace, monospace');
  tip.appendChild(rect); tip.appendChild(t1); tip.appendChild(t2);
  svg.appendChild(tip);
  tip._rect = rect; tip._t1 = t1; tip._t2 = t2;
  return tip;
}
function showTip(rec, px, py) {
  var g = ensureTip();
  g._t1.textContent = rec.label;
  g._t2.textContent = 'colour ' + rec.vcolour + '  flav ' + rec.vflav +
                      '  proline ' + rec.vprol;
  var w = Math.max(
    g._t1.getComputedTextLength ? g._t1.getComputedTextLength() : 120,
    g._t2.getComputedTextLength ? g._t2.getComputedTextLength() : 200) + 24;
  g._rect.setAttribute('width', w);
  g._rect.setAttribute('height', 56);
  // keep the box on-canvas
  var ox = px + 16, oy = py - 66;
  if (ox + w > CFG.plotW) ox = px - w - 16;
  if (oy < 0) oy = py + 16;
  g.setAttribute('transform', 'translate(' + fmt(ox) + ',' + fmt(oy) + ')');
  g.style.display = '';
  svg.appendChild(g);  // keep tooltip on top
}
function hideTip() { if (tip) tip.style.display = 'none'; }

// hover on any circle
svg.addEventListener('mouseover', function (e) {
  var el = e.target;
  if (el && el.tagName === 'circle' && el.id && el.id.charAt(0) === 'p') {
    var i = parseInt(el.getAttribute('data-i'), 10);
    showTip(pts[i], parseFloat(el.getAttribute('cx')), parseFloat(el.getAttribute('cy')));
  }
});
svg.addEventListener('mouseout', function (e) {
  var el = e.target;
  if (el && el.tagName === 'circle' && el.id && el.id.charAt(0) === 'p') hideTip();
});

// --- shared interaction constants --------------------------------------
var ROT_SENS = 0.30;   // degrees of rotation per CSS pixel dragged
var ELEV_MIN = -89, ELEV_MAX = 89;
var ZOOM_MIN = 0.4, ZOOM_MAX = 4.0;
var hintEl = svg.querySelector('#hint');
var hintGone = false;

// Fade the discoverability pill out the first time the user touches the
// figure — it has done its job once they engage.
function dismissHint() {
  if (hintGone || !hintEl) return;
  hintGone = true;
  hintEl.style.opacity = '0';
}

function clampElev(v) { return v < ELEV_MIN ? ELEV_MIN : (v > ELEV_MAX ? ELEV_MAX : v); }
function clampZoom(v) { return v < ZOOM_MIN ? ZOOM_MIN : (v > ZOOM_MAX ? ZOOM_MAX : v); }

// rAF-coalesced render so a burst of pointermove/wheel events paints once
// per frame — keeps the drag buttery even under heavy event rates.
var frameQueued = false;
function scheduleRender() {
  if (frameQueued) return;
  frameQueued = true;
  (window.requestAnimationFrame || function (f) { return setTimeout(f, 16); })(
    function () { frameQueued = false; render(); });
}

// Convert a client-space (x, y) into the SVG's viewBox coordinate space,
// reading the LIVE client rect so the math is correct at any rendered size
// (responsive) and under any preserveAspectRatio letterboxing.
function toViewBox(clientX, clientY) {
  var rect = svg.getBoundingClientRect();
  // xMidYMid meet: uniform scale = min over the two axes, centred.
  var sx = rect.width ? CFG.vbW / rect.width : 1;
  var sy = rect.height ? CFG.vbH / rect.height : 1;
  var s = Math.max(sx, sy);
  var drawnW = CFG.vbW / s, drawnH = CFG.vbH / s;
  var offX = (rect.width - drawnW) / 2, offY = (rect.height - drawnH) / 2;
  return {
    x: (clientX - rect.left - offX) * s,
    y: (clientY - rect.top - offY) * s
  };
}

// Zoom about a viewBox anchor point so the model under the cursor / pinch
// midpoint stays put: shift the projection centre by the residual.
function zoomAbout(newZoom, ax, ay) {
  newZoom = clampZoom(newZoom);
  if (newZoom === zoom) return;
  var k = newZoom / zoom;
  // cx/cy live in viewBox space; nudge them so `ax,ay` is a fixed point.
  CFG.cx = ax - (ax - CFG.cx) * k;
  CFG.cy = ay - (ay - CFG.cy) * k;
  zoom = newZoom;
}

// --- pointer state -----------------------------------------------------
// Track every active pointer by id so one finger rotates and two pinch.
var active = {};          // id -> {x, y} in viewBox space
var activeIds = [];       // insertion-ordered ids
var pinchPrev = 0;        // previous two-finger distance (viewBox px)
// Per-gesture tap bookkeeping — so a genuine still tap can be told apart
// from a drag or a pinch (whose two release events must NOT read as a
// double-tap and snap the view back to default).
var gestureMoved = false;     // any pointer moved appreciably this gesture
var gestureMulti = false;     // a second finger touched down this gesture
var downClientX = 0, downClientY = 0, downTime = 0;

function activePoints() {
  return activeIds.map(function (id) { return active[id]; });
}

function onPointerDown(e) {
  var vp = toViewBox(e.clientX, e.clientY);
  if (!active.hasOwnProperty(e.pointerId)) activeIds.push(e.pointerId);
  active[e.pointerId] = vp;
  if (activeIds.length === 1) {           // first finger of a fresh gesture
    gestureMoved = false; gestureMulti = false;
    downClientX = e.clientX; downClientY = e.clientY; downTime = Date.now();
  } else {
    gestureMulti = true;                  // pinch — never a tap
  }
  if (svg.setPointerCapture) {
    try { svg.setPointerCapture(e.pointerId); } catch (err) {}
  }
  if (activeIds.length === 2) {
    var p = activePoints();
    pinchPrev = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
  }
  dismissHint();
  hideTip();
  if (e.cancelable) e.preventDefault();
}

function onPointerMove(e) {
  if (!active.hasOwnProperty(e.pointerId)) return;  // not a captured drag
  var vp = toViewBox(e.clientX, e.clientY);
  var prev = active[e.pointerId];
  // client -> viewBox scale for the rotation sensitivity (degrees/CSS px):
  // one viewBox px equals (rect.width / vbW) CSS px, so undo that here.
  var rect = svg.getBoundingClientRect();
  var vbPerCss = rect.width ? CFG.vbW / rect.width : 1;

  if (activeIds.length >= 2) {
    // --- two-finger pinch: zoom by the ratio of finger distances -------
    active[e.pointerId] = vp;
    var p = activePoints();
    var dist = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
    if (pinchPrev > 0 && dist > 0) {
      var mx = (p[0].x + p[1].x) / 2, my = (p[0].y + p[1].y) / 2;
      zoomAbout(zoom * (dist / pinchPrev), mx, my);
    }
    pinchPrev = dist;
    scheduleRender();
  } else {
    // --- one pointer: rotate ------------------------------------------
    // Delta in viewBox px -> CSS px (divide by vbPerCss) -> degrees.
    var dxCss = (vp.x - prev.x) / vbPerCss;
    var dyCss = (vp.y - prev.y) / vbPerCss;
    if (Math.abs(dxCss) + Math.abs(dyCss) > 0.01) gestureMoved = true;
    azim += dxCss * ROT_SENS;
    elev = clampElev(elev - dyCss * ROT_SENS);
    active[e.pointerId] = vp;
    scheduleRender();
  }
  if (e.cancelable) e.preventDefault();
}

function endPointer(e) {
  if (active.hasOwnProperty(e.pointerId)) {
    delete active[e.pointerId];
    var idx = activeIds.indexOf(e.pointerId);
    if (idx >= 0) activeIds.splice(idx, 1);
  }
  if (svg.releasePointerCapture) {
    try { svg.releasePointerCapture(e.pointerId); } catch (err) {}
  }
  // reset the pinch baseline when dropping below two fingers
  if (activeIds.length === 2) {
    var p = activePoints();
    pinchPrev = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
  } else {
    pinchPrev = 0;
  }
}

var hasPointer = ('PointerEvent' in window) && svg.setPointerCapture;
if (hasPointer) {
  svg.addEventListener('pointerdown', onPointerDown);
  svg.addEventListener('pointermove', onPointerMove);
  svg.addEventListener('pointerup', endPointer);
  svg.addEventListener('pointercancel', endPointer);
  svg.addEventListener('pointerleave', function (e) {
    // only end if we are not capturing (capture keeps the id alive)
    if (!(svg.hasPointerCapture && svg.hasPointerCapture(e.pointerId))) {
      endPointer(e);
    }
  });
} else {
  // --- graceful fallback: mouse-only drag (no Pointer Events) ----------
  var mDown = false, mx0 = 0, my0 = 0;
  svg.addEventListener('mousedown', function (e) {
    mDown = true;
    var vp = toViewBox(e.clientX, e.clientY);
    mx0 = vp.x; my0 = vp.y; dismissHint(); hideTip();
  });
  window.addEventListener('mousemove', function (e) {
    if (!mDown) return;
    var vp = toViewBox(e.clientX, e.clientY);
    var rect = svg.getBoundingClientRect();
    var vbPerCss = rect.width ? CFG.vbW / rect.width : 1;
    azim += ((vp.x - mx0) / vbPerCss) * ROT_SENS;
    elev = clampElev(elev - ((vp.y - my0) / vbPerCss) * ROT_SENS);
    mx0 = vp.x; my0 = vp.y;
    scheduleRender();
    if (e.cancelable) e.preventDefault();
  });
  window.addEventListener('mouseup', function () { mDown = false; });
}

// --- wheel / trackpad scroll to zoom -----------------------------------
// Normalise deltaY across deltaMode (0=pixel, 1=line, 2=page) and OS, then
// zoom toward the pointer. {passive:false} + preventDefault means the PAGE
// never scrolls while the figure is being zoomed.
svg.addEventListener('wheel', function (e) {
  var dy = e.deltaY;
  if (e.deltaMode === 1) dy *= 16;        // lines -> approx CSS px
  else if (e.deltaMode === 2) dy *= 400;  // pages -> approx CSS px
  var factor = Math.exp(-dy * 0.0015);
  var anchor = toViewBox(e.clientX, e.clientY);
  zoomAbout(zoom * factor, anchor.x, anchor.y);
  dismissHint();
  hideTip();
  scheduleRender();
  if (e.cancelable) e.preventDefault();
}, { passive: false });

// --- reset to the default view (double-click / double-tap) -------------
function resetView() {
  azim = CFG.azim0; elev = CFG.elev0; zoom = 1.0;
  CFG.cx = CFG.cx0; CFG.cy = CFG.cy0;
  hideTip();
  render();
}
svg.addEventListener('dblclick', function (e) {
  resetView();
  if (e.cancelable) e.preventDefault();
});
// double-tap detector for touch/pen (dblclick is unreliable on mobile).
// A "tap" is only counted when the WHOLE gesture was a single, still,
// short press with no second finger — so lifting a pinch or ending a
// rotate never masquerades as a tap and snaps the view back.
var lastTap = 0;
svg.addEventListener('pointerup', function (e) {
  if (e.pointerType === 'mouse') return;   // mouse uses dblclick
  if (activeIds.length > 0) return;        // other fingers still down
  var dx = e.clientX - downClientX, dy = e.clientY - downClientY;
  var isTap = !gestureMoved && !gestureMulti &&
              (Math.abs(dx) + Math.abs(dy) < 10) &&
              (Date.now() - downTime < 400);
  if (!isTap) { lastTap = 0; return; }
  var now = Date.now();
  if (now - lastTap < 320) { resetView(); lastTap = 0; }
  else lastTap = now;
});

// first frame — matches the server-rendered still
render();
"""
    js = js.replace("__CFG__", data)
    return f'<script type="text/javascript"><![CDATA[{js}]]></script>'


def build_svg(
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
    labels: List[str],
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full 3D-scatter SVG document as a string.

    The document is a complete still at the default three-quarter angle
    *and* carries an embedded ``<script>`` that makes it drag / zoom / hover
    interactive in a browser. There is no SMIL animation and no grounding
    shadow — a static rasteriser sees exactly the first interactive frame.

    Parameters
    ----------
    xs, ys, zs : numpy.ndarray
        Model-space coordinates from :func:`_sample_clusters`.
    labels : list of str
        Cultivar label per point.
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``. This is the fullscreen button layer; the
        drag / zoom / hover script always ships regardless of ``mode``.
    accessibility : str, optional
        Palette accessibility level applied to the three (categorical)
        cultivar hues via :func:`_style.leveled_colors`. ``"universal"``
        (default) leaves them unchanged; other levels
        (``"high-contrast"``, ``"monochrome"``, ``"deuteranopia"``,
        ``"protanopia"``, ``"tritanopia"``) remap the class colours so the
        still, the legend and the interactive re-projection all agree.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    class_colors = _class_colors(accessibility)
    # ---- canvas geometry -------------------------------------------------- #
    # Poster-scale canvas: the figure is meant to read from across a room, so
    # the cloud gets a generous plot box rather than a cramped 640x480 panel.
    width, height = 1040, 780
    m_top = 132
    m_bottom = 48
    plot_w = width
    plot_h = height - m_top - m_bottom
    cx = width / 2.0 - 34  # nudge left: leaves room for the right-side legend
    cy = m_top + plot_h / 2.0 + 30  # nudge down: keeps the +z arm off the title

    elev = _DEFAULT_ELEV
    azim = _DEFAULT_AZIM

    records = _point_records(xs, ys, zs, labels, class_colors)

    axes = _axis_frame_svg(
        elev_deg=elev, azim_deg=azim,
        plot_w=plot_w, plot_h=plot_h, cx=cx, cy=cy,
    )
    cloud = _cloud_svg(
        records,
        elev_deg=elev, azim_deg=azim,
        plot_w=plot_w, plot_h=plot_h, cx=cx, cy=cy,
    )
    script = _script_svg(
        records,
        elev_deg=elev, azim_deg=azim,
        plot_w=plot_w, plot_h=plot_h, cx=cx, cy=cy,
        vb_w=width, vb_h=height,
        class_colors=class_colors,
    )

    parts: List[str] = []

    # ---- header ----------------------------------------------------------- #
    title = "Three grape cultivars fall into three chemistry clouds"
    subtitle = (
        "Drag to rotate, scroll or pinch to zoom, double-click to reset, "
        "hover a point for its readings · illustrative data"
    )
    # width/height 100% + viewBox + preserveAspectRatio make the figure
    # responsive: it fills its container and the JS reads the live client
    # size for the pointer-delta -> degree conversion.
    parts.append(
        f'<svg role="img" aria-label="{title}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'width="100%" height="100%" '
        f'viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="max-width:100%;height:auto;touch-action:none" '
        f'font-family="{_FONT}">'
    )
    parts.append(
        f"<title>{title}</title>"
        f"<desc>Interactive 3D scatter plot: three well-separated point "
        f"clouds, one per grape cultivar (Barolo, Grignolino, Barbera), "
        f"positioned by colour intensity, flavanoid content and proline. "
        f"Nearer points are larger and more opaque. Drag (mouse, touch or "
        f"pen) to rotate the view, scroll or pinch to zoom, double-click or "
        f"double-tap to reset, hover a point for its readings; the figure is "
        f"shown still at a three-quarter angle when scripting is off.</desc>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="16" fill="{_BG}"/>')

    # OS-adaptive overrides (additive; the default render is unchanged because
    # every rule lives inside a media query). Under prefers-contrast each
    # cultivar deepens to its high-contrast hue on both the cloud and the legend
    # swatch. A CSS rule outranks the inline fill AND the fill the drag script
    # writes with setAttribute, so the aerial-perspective wash flattens to solid
    # higher-contrast hues — an improvement for the far, washed-out points, and
    # depth still reads through point size and opacity. Under forced-colors
    # (Windows High Contrast) the ~4-colour system palette cannot preserve three
    # cloud hues, so each cultivar is handed a distinct Canvas/CanvasText PATTERN
    # (hatch / dots) via forced_color_patterns; the pattern url a CSS rule sets on
    # ``.pt3d-<slug>`` outranks BOTH the inline fill and the fill the drag script
    # writes with setAttribute, so every point and legend swatch of a cultivar
    # keeps its pattern through rotation, and the clouds stay separable when
    # colour is stripped.
    os_series = {f".pt3d-{_class_slug(str(n))}": str(h) for n, h in class_colors.items()}
    fcp_defs, fcp_style = forced_color_patterns(list(os_series), prefix="s3d-fcp")
    # Dark mode: invert paper + text inks. The JS-built hover tooltip is a dark
    # chrome element (dark rect, light text) that must STAY dark, so re-assert it
    # after the generic ink flips (a class rule outranks the [fill=...] selector).
    dark_extra = (
        ".tooltip rect{fill:#1D1D1F;}"
        ".tooltip text{fill:#F5F5F7;}"
    )
    parts.append(
        "<style>"
        + os_adaptive_style(os_series, role="fill")
        + fcp_style
        + os_dark_style(extra=dark_extra)
        + "</style>"
    )
    parts.append(f"<defs>{fcp_defs}</defs>")

    parts.append(
        f'<text x="56" y="60" font-size="30" font-weight="700" '
        f'fill="{_INK}">{title}</text>'
    )
    parts.append(
        f'<text x="56" y="92" font-size="18" '
        f'fill="{_SECONDARY}">{subtitle}</text>'
    )

    # ---- the axis gizmo (behind the cloud) -------------------------------- #
    parts.append(axes)

    # ---- the point cloud -------------------------------------------------- #
    parts.append('<g class="cloud">')
    parts.append(cloud)
    parts.append("</g>")

    # ---- cultivar legend -------------------------------------------------- #
    parts.append(_legend_svg(width - 210, m_top + 8, class_colors))

    # ---- depth cue caption ------------------------------------------------ #
    ly = height - 20
    parts.append(
        f'<text x="56" y="{ly}" font-size="15" font-family="{_MONO}" '
        f'fill="{_SECONDARY}">nearer points draw larger and darker</text>'
    )

    # ---- discoverable controls hint --------------------------------------- #
    # A small, unobtrusive pill anchored bottom-right that spells out the
    # gesture set. It is part of the still (so a reader knows the controls
    # even before touching it); the embedded JS fades it out on the first
    # interaction. It sits opposite the bottom-left depth caption.
    hint = "Drag to rotate · scroll or pinch to zoom · double-click to reset"
    hint_w = 8.6 * len(hint) + 34  # rough advance width for the 15px label
    hint_x = width - hint_w - 24
    hint_y = height - 46
    parts.append(
        f'<g id="hint" opacity="0.92" pointer-events="none" '
        f'style="transition:opacity .45s ease">'
        f'<rect x="{_fmt(hint_x)}" y="{_fmt(hint_y)}" '
        f'width="{_fmt(hint_w)}" height="30" rx="15" '
        f'fill="{_INK}" fill-opacity="0.82"/>'
        f'<text x="{_fmt(hint_x + hint_w / 2.0)}" y="{_fmt(hint_y + 20)}" '
        f'font-size="15" font-family="{_FONT}" fill="#FFFFFF" '
        f'text-anchor="middle">{hint}</text>'
        f"</g>"
    )

    # ---- the interactive controller --------------------------------------- #
    parts.append(script)

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_scatter3d",
        description="Write the house-style still-plus-interactive 3D-scatter SVG.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--seed", type=int, default=7, help="Random seed for the sample clusters."
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="interactivity mode of the emitted SVG (default: self-contained)",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal", "high-contrast", "monochrome",
            "deuteranopia", "protanopia", "tritanopia",
        ),
        default="universal",
        help="palette accessibility level (default: universal, the CVD-safe standard)",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to disk."""
    args = _build_parser().parse_args(argv)
    xs, ys, zs, labels = _sample_clusters(seed=args.seed)
    svg = build_svg(xs, ys, zs, labels, mode=args.mode, accessibility=args.accessibility)
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

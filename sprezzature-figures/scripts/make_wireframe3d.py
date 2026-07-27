#!/usr/bin/env python3
"""Generate a publication-quality *3D wireframe* figure as a standalone SVG.

A 3D wireframe draws a surface ``z = f(x, y)`` as a lattice of mesh lines —
the constant-``x`` and constant-``y`` grid curves projected onto the page —
so the reader reads the shape of a two-argument function from its silhouette
alone, without a filled/shaded solid. It is the matplotlib
``Axes3D.plot_wireframe`` idiom; R, seaborn, and plotly have no first-class
equivalent, so a hand-built SVG is the natural home for it here.

This module builds the SVG string **by hand** (no matplotlib / seaborn /
plotly, no Vega): it samples the surface on a regular grid, rotates the
lattice in 3D, projects it with a simple perspective camera, sorts the mesh
segments back-to-front (painter's algorithm) and paints them in the sprezzature-*
house style — Roboto type, the Apple-system palette, ink ``#1D1D1F`` on a
white ground, rounded framing. Depth is reinforced twice over: nearer mesh
lines are drawn darker and thicker on a house blue→teal ramp, and the whole
lattice turns slowly on its vertical axis via a single pure-SMIL
``<animateTransform type="rotate">`` so a still reader still perceives the
solid (the rotation is what sells "3D" on a flat page).

The example data is illustrative: a radially-symmetric ``sinc``-like ripple,
the textbook "drop in a pond" surface a wireframe is made to show — one
central peak ringed by decaying concentric waves.

Usage
-----
    python make_wireframe3d.py                 # writes the house SVG
    python make_wireframe3d.py --out other.svg
    python make_wireframe3d.py --no-animate    # static (frozen) variant

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc
classes, generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations
from _render import write_svg  # noqa: E402
from _svg import fmt_compact  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import leveled_colors, os_dark_style  # noqa: E402

import argparse
from pathlib import Path
from typing import List, Tuple

import numpy as np

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "wireframe3d.svg"
)

# House-style tokens (mirrors _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"

# Depth ramp endpoints: near lines read a deep house blue, far lines fade
# toward a pale teal so the lattice has an unambiguous front-to-back cue on
# top of the painter-ordering — a redundant channel for the 3D read. These are
# the ``universal`` anchors; :func:`_depth_ramp` applies the accessibility
# level per render (see its docstring for why a two-anchor ramp survives it).
_NEAR = "#0A4DA0"       # deep blue  — closest mesh lines
_FAR = "#B9E4E8"        # pale teal  — farthest mesh lines


def _depth_ramp(accessibility: str = "universal") -> Tuple[str, str]:
    """Return the ``(near, far)`` depth-ramp anchors at an accessibility level.

    The depth cue is a *sequential* two-anchor ramp read purely by lightness
    (near = dark, far = pale), so it is already colour-vision- and
    greyscale-safe. Unlike a many-stop tuned ramp, a *two*-anchor ramp keeps
    its monotonicity through :func:`_style.leveled_colors`: the engine
    preserves each anchor's relative lightness, so ``near`` stays darker than
    ``far`` at every level and the in-between shades (interpolated in
    :func:`_lerp_hex`) stay ordered. Levelling therefore only re-tints the two
    ends (e.g. to a neutral grey ramp under ``"monochrome"``) without breaking
    the front-to-back read, so it is applied rather than made a no-op.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level. Defaults to ``"universal"`` (identity, so
        the shipped figure is byte-for-byte unchanged).

    Returns
    -------
    tuple of str
        ``(near_hex, far_hex)`` at the requested level.
    """
    ramp = leveled_colors({"near": _NEAR, "far": _FAR}, accessibility)
    return ramp["near"], ramp["far"]


# --------------------------------------------------------------------------- #
# Illustrative surface                                                         #
# --------------------------------------------------------------------------- #
def _sample_surface(n: int = 26, seed: int = 3) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample a radially-symmetric ripple ``z = f(x, y)`` on a regular grid.

    The surface is a damped ``sinc``-style ripple — a tall central peak
    ringed by decaying concentric waves, the canonical "drop in a pond"
    shape a wireframe communicates best. A whisper of smooth low-frequency
    noise breaks the perfect symmetry so the mesh looks like measured data
    rather than a pure formula.

    Parameters
    ----------
    n : int, optional
        Grid resolution per axis (the lattice is ``n x n`` vertices).
    seed : int, optional
        Seed for the reproducible symmetry-breaking noise.

    Returns
    -------
    tuple of numpy.ndarray
        ``(X, Y, Z)``, each of shape ``(n, n)``, in surface (model) space
        with ``x, y in [-1, 1]`` and ``z`` roughly in ``[-0.3, 1.0]``.
    """
    rng = np.random.default_rng(seed)
    lin = np.linspace(-1.0, 1.0, n)
    xx, yy = np.meshgrid(lin, lin)
    # Radius scaled so ~3 full ripples fit within the plate.
    r = np.sqrt(xx**2 + yy**2) * 9.0 + 1e-9
    zz = np.sin(r) / r  # classic sinc ripple, peak 1 at the centre
    # Gentle, smooth asymmetry: a couple of low-frequency bumps.
    zz = zz + 0.10 * np.exp(-((xx - 0.35) ** 2 + (yy + 0.2) ** 2) / 0.25)
    zz = zz - 0.06 * np.exp(-((xx + 0.5) ** 2 + (yy - 0.5) ** 2) / 0.20)
    # A dusting of tiny noise, then keep it subtle.
    zz = zz + rng.normal(0.0, 0.012, size=zz.shape)
    return xx, yy, zz


# --------------------------------------------------------------------------- #
# 3D → 2D projection                                                          #
# --------------------------------------------------------------------------- #
def _rotate(pts: np.ndarray, elev_deg: float, azim_deg: float) -> np.ndarray:
    """Rotate model-space points by an azimuth then an elevation.

    The azimuth turns the surface about the world ``z`` (up) axis; the
    elevation then tips the camera down toward the plate. Working on the
    stacked ``(N, 3)`` array keeps the whole lattice in one matmul.

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
    xx: np.ndarray,
    yy: np.ndarray,
    zz: np.ndarray,
    *,
    elev_deg: float,
    azim_deg: float,
    plot_w: float,
    plot_h: float,
    cx: float,
    cy: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rotate the lattice and project it to pixel space with a light perspective.

    Parameters
    ----------
    xx, yy, zz : numpy.ndarray
        ``(n, n)`` model-space coordinate grids from :func:`_sample_surface`.
    elev_deg, azim_deg : float
        Camera elevation and azimuth, in degrees.
    plot_w, plot_h : float
        Pixel extent available for the projected lattice.
    cx, cy : float
        Pixel centre the lattice is drawn around.

    Returns
    -------
    tuple of numpy.ndarray
        ``(PX, PY, DEPTH)``, each ``(n, n)`` — pixel columns, pixel rows,
        and a camera-depth value (larger = nearer the viewer) used for both
        painter ordering and the depth colour ramp.
    """
    n = xx.shape[0]
    # z is exaggerated a touch so the ripple reads clearly in projection.
    pts = np.column_stack([xx.ravel(), yy.ravel(), (zz * 0.65).ravel()])
    cam = _rotate(pts, elev_deg, azim_deg)
    cx_m, cy_m, cz_m = cam[:, 0], cam[:, 1], cam[:, 2]

    # Simple perspective: points farther from the camera (smaller y in camera
    # space after the tip) shrink slightly. Camera sits down the -y axis.
    dist = 4.0
    denom = dist - cy_m
    persp = dist / denom
    sx = cx_m * persp
    sy = cz_m * persp  # camera-space up maps to screen up

    # Scale to fill the plot box generously. The lattice spans ~[-1.4, 1.4] in
    # model x after rotation, so we key the scale off the available *width* and
    # let the (shorter) projected height follow — this makes the surface claim
    # the frame rather than float small in whitespace.
    span = 1.55
    scale = plot_w / (2.0 * span)
    px = cx + sx * scale
    py = cy - sy * scale  # SVG y grows downward

    # Depth for ordering / shading: nearer the camera → larger. Camera looks
    # down -y, so smaller cy_m is nearer; negate so "near" is the max.
    depth = -cy_m
    return (
        px.reshape(n, n),
        py.reshape(n, n),
        depth.reshape(n, n),
    )


# --------------------------------------------------------------------------- #
# Colour ramp                                                                  #
# --------------------------------------------------------------------------- #
def _lerp_hex(a: str, b: str, t: float) -> str:
    """Linearly interpolate two ``#RRGGBB`` colours in sRGB space.

    Parameters
    ----------
    a, b : str
        Endpoint colours as ``#RRGGBB``.
    t : float
        Blend factor in ``[0, 1]`` (0 → ``a``, 1 → ``b``).

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
def _edge_indices(n: int) -> List[Tuple[int, int]]:
    """Return every mesh edge as an ``(a, b)`` pair of flat vertex indices.

    Both grid-line families are emitted: constant-row (varying column) and
    constant-column (varying row), over an ``n x n`` lattice flattened
    row-major. The index list is azimuth-independent, so it is computed once
    and reused for every animation frame.

    Parameters
    ----------
    n : int
        Grid resolution per axis.

    Returns
    -------
    list of tuple of int
        Edge endpoints as flat indices into the ``n * n`` vertex array.
    """
    edges: List[Tuple[int, int]] = []
    for i in range(n):
        for j in range(n):
            flat = i * n + j
            if j + 1 < n:                 # horizontal edge
                edges.append((flat, flat + 1))
            if i + 1 < n:                 # vertical edge
                edges.append((flat, i * n + n + j))
    return edges


def _frame_endpoints(
    xx: np.ndarray,
    yy: np.ndarray,
    zz: np.ndarray,
    *,
    azim_deg: float,
    elev_deg: float,
    plot_w: float,
    plot_h: float,
    cx: float,
    cy: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Project the lattice at one azimuth into flat pixel + depth arrays.

    Returns
    -------
    tuple of numpy.ndarray
        ``(px_flat, py_flat, depth_flat)``, each shape ``(n * n,)``.
    """
    px, py, depth = _project(
        xx, yy, zz,
        elev_deg=elev_deg, azim_deg=azim_deg,
        plot_w=plot_w, plot_h=plot_h, cx=cx, cy=cy,
    )
    return px.ravel(), py.ravel(), depth.ravel()


def _mesh_svg(
    xx: np.ndarray,
    yy: np.ndarray,
    zz: np.ndarray,
    *,
    elev_deg: float,
    azimuths: List[float],
    plot_w: float,
    plot_h: float,
    cx: float,
    cy: float,
    animate: bool,
    near: str,
    far: str,
) -> str:
    """Paint the depth-shaded mesh, optionally as a true-3D azimuth turntable.

    Each mesh edge becomes one ``<line>``. Under animation, every edge carries
    two ``<animate>`` tags that drive its endpoints through the projected
    coordinates at each keyframe azimuth — an honest 3D turn (the surface
    genuinely rotates about its vertical axis, unlike a flat 2D ``rotate``).
    Colour and stroke width follow the *reference* frame's depth so nearer
    lines stay darker/thicker; the effect is stable for the gentle rock used
    here.

    Parameters
    ----------
    xx, yy, zz : numpy.ndarray
        Sampled surface grids.
    elev_deg : float
        Fixed camera elevation.
    azimuths : list of float
        Keyframe azimuths. The first is the reference (t=0) frame; the list
        should return to its start (a closed loop) for a seamless repeat.
    plot_w, plot_h, cx, cy : float
        Projection box geometry.
    animate : bool
        When ``False`` only the reference frame is drawn (no ``<animate>``).
    near, far : str
        The nearest / farthest depth-ramp anchor hexes at the active
        accessibility level (see :func:`_depth_ramp`).

    Returns
    -------
    str
        The ``<line>`` elements, painted far → near at the reference frame.
    """
    n = xx.shape[0]
    edges = _edge_indices(n)

    # Project every keyframe once; frames[k] = (px, py, depth) flat arrays.
    frames = [
        _frame_endpoints(
            xx, yy, zz,
            azim_deg=a, elev_deg=elev_deg,
            plot_w=plot_w, plot_h=plot_h, cx=cx, cy=cy,
        )
        for a in azimuths
    ]
    ref_px, ref_py, ref_depth = frames[0]

    # Painter's order + colour/width use the reference frame's depths.
    d_lo, d_hi = float(ref_depth.min()), float(ref_depth.max())
    span = (d_hi - d_lo) or 1.0
    edge_depth = [(ref_depth[a] + ref_depth[b]) * 0.5 for a, b in edges]
    order = sorted(range(len(edges)), key=lambda k: edge_depth[k])

    n_frames = len(azimuths)
    key_times = ";".join(f"{i / (n_frames - 1):.4f}" for i in range(n_frames))
    dur = "20s"

    out: List[str] = []
    for k in order:
        a, b = edges[k]
        t = (edge_depth[k] - d_lo) / span   # 0 far … 1 near
        colour = _lerp_hex(far, near, t)
        width = 1.1 + 1.9 * t
        opacity = 0.55 + 0.45 * t

        x1, y1 = ref_px[a], ref_py[a]
        x2, y2 = ref_px[b], ref_py[b]
        line = (
            f'<line x1="{fmt_compact(x1)}" y1="{fmt_compact(y1)}" '
            f'x2="{fmt_compact(x2)}" y2="{fmt_compact(y2)}" '
            f'stroke="{colour}" stroke-width="{width:.2f}" '
            f'stroke-opacity="{opacity:.2f}" stroke-linecap="round">'
        )
        if animate:
            def _vals(idx: int, coord: int) -> str:
                # coord: 0 -> px, 1 -> py; idx: endpoint vertex index.
                return ";".join(fmt_compact(frames[f][coord][idx]) for f in range(n_frames))
            line += (
                f'<animate attributeName="x1" values="{_vals(a, 0)}" '
                f'keyTimes="{key_times}" dur="{dur}" repeatCount="indefinite"/>'
                f'<animate attributeName="y1" values="{_vals(a, 1)}" '
                f'keyTimes="{key_times}" dur="{dur}" repeatCount="indefinite"/>'
                f'<animate attributeName="x2" values="{_vals(b, 0)}" '
                f'keyTimes="{key_times}" dur="{dur}" repeatCount="indefinite"/>'
                f'<animate attributeName="y2" values="{_vals(b, 1)}" '
                f'keyTimes="{key_times}" dur="{dur}" repeatCount="indefinite"/>'
            )
        line += "</line>"
        out.append(line)
    return "".join(out)


def build_svg(
    xx: np.ndarray,
    yy: np.ndarray,
    zz: np.ndarray,
    *,
    animate: bool = True,
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full 3D-wireframe SVG document as a string.

    Parameters
    ----------
    xx, yy, zz : numpy.ndarray
        The sampled surface grids from :func:`_sample_surface`.
    animate : bool, optional
        When ``True`` (default) the lattice turns slowly on its vertical
        axis via a single pure-SMIL ``<animateTransform>``. When ``False`` a
        clean frozen frame is emitted (used for the static variant / stills).
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"`` / ``"external"`` / ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level applied to the two depth-ramp anchors via
        :func:`_depth_ramp`. ``"universal"`` (default) leaves them unchanged;
        other levels re-tint near/far (e.g. to a grey ramp under
        ``"monochrome"``) while keeping the near-dark / far-pale ordering, so
        the depth cue still reads.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    near, far = _depth_ramp(accessibility)
    # ---- canvas geometry -------------------------------------------------- #
    # Poster-scale canvas: the figure should read big and generous, with the
    # lattice claiming most of the frame rather than floating in whitespace.
    width, height = 1120, 780
    m_top = 132   # room for the larger title + subtitle
    m_bottom = 74  # room for the depth legend
    plot_w = width
    plot_h = height - m_top - m_bottom
    cx = width / 2.0
    # Centre the lattice in its box, with a small downward nudge so the tall
    # central peak has headroom under the subtitle.
    cy = m_top + plot_h / 2.0 + 26

    elev = 26.0  # fixed camera tilt; azimuth is what animates

    # Keyframe azimuths: a slow, closed-loop rock around a three-quarter view.
    # Real 3D projection is baked at each keyframe (see :func:`_mesh_svg`), so
    # this is an honest turntable, not a flat 2D spin. The list opens and
    # closes at the same angle so the SMIL loop is seamless.
    centre, sweep = -52.0, 34.0
    n_key = 13
    azimuths = [
        centre + sweep * float(np.sin(2.0 * np.pi * i / (n_key - 1)))
        for i in range(n_key)
    ]

    mesh = _mesh_svg(
        xx, yy, zz,
        elev_deg=elev, azimuths=azimuths,
        plot_w=plot_w, plot_h=plot_h, cx=cx, cy=cy,
        animate=animate,
        near=near, far=far,
    )

    parts: List[str] = []

    # ---- header ----------------------------------------------------------- #
    title = "A single ripple ripples out, then fades to stillness"
    subtitle = (
        "Wave height across a still pond, one second after a single drop"
    )
    desc = (
        "3D wireframe surface: a mesh of projected grid lines over a "
        "radially-symmetric ripple, one central peak ringed by decaying "
        "concentric waves. Nearer lines are darker blue and thicker; the "
        "lattice turns slowly so the solid shape reads on a flat page."
    )
    parts.append(
        f'<svg role="img" aria-label="{title}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}">'
    )
    parts.append(f"<title>{title}</title><desc>{desc}</desc>")
    # OS-adaptive style (additive; media-gated so the default light render is
    # byte-for-byte unchanged). PERCEPTUAL figure — the near->far blue depth ramp
    # is NOT re-spaced.
    #
    # Under prefers-contrast we only STRENGTHEN STRUCTURE for a low-vision
    # reader: the secondary ink (#6E6E73 subtitle + depth-legend labels) deepens
    # to the primary ink so the surrounding type reads harder. The mesh (the
    # depth ramp) and its legend swatch are data and untouched — the figure has
    # no axes or frame to thicken.
    #
    # prefers-color-scheme:dark hands it a dark paper and inverts the two ink
    # tiers (#1D1D1F primary, #6E6E73 secondary). No multiply groups, no white
    # keylines to preserve.
    parts.append(
        "<style>\n"
        + "@media (prefers-contrast: more){"
        + f' [fill="{_SECONDARY}"]{{fill:{_INK};}}'
        + " }"
        + "\n"
        + os_dark_style(screen_blend=False)
        + "\n</style>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="16" fill="{_BG}"/>')
    parts.append(
        f'<text x="56" y="66" font-size="34" font-weight="700" '
        f'fill="{_INK}">{title}</text>'
    )
    parts.append(
        f'<text x="56" y="100" font-size="19" '
        f'fill="{_SECONDARY}">{subtitle}</text>'
    )


    # ---- the rotating lattice --------------------------------------------- #
    # Each mesh edge carries its own SMIL <animate> tags driving its projected
    # endpoints through the keyframe azimuths, a true 3D turntable turn. The
    # rotation earns its place here: parallax is the honest way to read a
    # surface's depth on a flat page, and every edge is fully drawn in its
    # final state at t=0 (no draw-in), so the static raster is already complete.
    parts.append('<g class="mesh">')
    parts.append(mesh)
    parts.append("</g>")

    # ---- depth legend (near -> far) --------------------------------------- #
    lx, ly = 56, height - 34
    parts.append(
        f'<text x="{lx}" y="{ly}" font-size="15" font-family="{_MONO}" '
        f'fill="{_SECONDARY}">nearer</text>'
    )
    # A gradient swatch drawn as stacked tick columns near->far.
    swatch_x = lx + 76
    n_ticks = 40
    tick_w = 5.0
    for k in range(n_ticks):
        t = 1.0 - k / (n_ticks - 1)  # start near (dark), end far (pale)
        colour = _lerp_hex(far, near, t)
        parts.append(
            f'<rect x="{swatch_x + k * tick_w:.1f}" y="{ly - 13}" '
            f'width="{tick_w + 0.4:.1f}" height="13" fill="{colour}"/>'
        )
    parts.append(
        f'<text x="{swatch_x + n_ticks * tick_w + 12:.1f}" y="{ly}" '
        f'font-size="15" font-family="{_MONO}" fill="{_SECONDARY}">farther</text>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_wireframe3d",
        description="Write the house-style 3D-wireframe SVG example.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--seed", type=int, default=3, help="Random seed for the sample surface."
    )
    parser.add_argument(
        "--no-animate",
        action="store_true",
        help="Emit a static (frozen) frame instead of the slow rotation.",
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="interactivity mode of the emitted SVG (default: self-contained).",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal", "high-contrast", "monochrome",
            "deuteranopia", "protanopia", "tritanopia",
        ),
        default="universal",
        help="palette accessibility level (default: universal, the CVD-safe standard).",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to disk."""
    args = _build_parser().parse_args(argv)
    xx, yy, zz = _sample_surface(seed=args.seed)
    svg = build_svg(
        xx, yy, zz,
        animate=not args.no_animate, mode=args.mode,
        accessibility=args.accessibility,
    )
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

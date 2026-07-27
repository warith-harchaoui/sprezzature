#!/usr/bin/env python3
"""Generate a publication-quality *interpolated heatmap* (imshow) as a standalone SVG.

An interpolated heatmap is the matplotlib ``imshow(..., interpolation="bilinear")``
idiom: a coarse 2-D scalar field is displayed as a smooth, continuous image rather
than a mosaic of hard cells. Each output pixel is a bilinear blend of its four
nearest measured samples, so the grid dissolves into gradients and the underlying
field reads as one continuous surface, the way a physical measurement actually
varies in space.

This module builds the SVG string **by hand** (no matplotlib / seaborn / plotly,
no Vega): it synthesises a small, communicative measurement grid with numpy — a
soil-moisture survey over a research field, with a wet hollow, a drier ridge, and
a damp irrigation seam — then performs the bilinear up-sampling *itself* in numpy
(no SVG blur filter) and paints the smooth result as a dense mosaic of tiny crisp
``<rect>`` cells in the front-* house style: Roboto type, ink ``#1D1D1F`` on
white, rounded framing, x/y axes with ticks, and a labelled colour legend.

The colour ramp is the house Apple-blue sequential ramp
``#EAF3FF`` → ``#007AFF`` → ``#0A4DA0`` — mono-hue, colour-vision-deficiency safe,
never a rainbow. The figure is a **static** poster-size raster: an interpolated
heatmap is an image whose whole story is legible in one glance, so it gains
nothing from motion and ships with no animation and no JavaScript.

The example data is illustrative but physically plausible: the deep-blue basin is
the moisture-holding hollow, the pale corner is the free-draining ridge, and the
faint blue band is the drip-line seam that keeps one row damp.

Usage
-----
    python make_imshow-interpolated.py                 # writes the house SVG
    python make_imshow-interpolated.py --out other.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc classes,
generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations
from _render import write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

import argparse
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "imshow-interpolated.svg"
)

# House-style tokens (mirrors _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"

# Sequential *value* ramp — the house Apple-blue mono-hue ramp.
# Pale sky → system blue → deep navy reads magnitude monotonically and is
# colour-vision-deficiency safe: it leans on lightness, never on a red/green
# contrast, so it survives protanopia / deuteranopia / tritanopia unchanged.
_BLUE_RAMP: Sequence[Tuple[float, str]] = (
    (0.00, "#EAF3FF"),
    (0.62, "#007AFF"),
    (1.00, "#0A4DA0"),
)


# --------------------------------------------------------------------------- #
# Illustrative measurement grid                                               #
# --------------------------------------------------------------------------- #
def _survey_grid(seed: int = 7) -> Dict[str, np.ndarray]:
    """Synthesise a small, communicative soil-moisture survey grid.

    The field layers three easily-read features so the interpolated image
    tells an obvious story:

    * a **wet hollow** — a broad Gaussian bump of high moisture, the deep-blue
      basin that dominates the field;
    * a **dry ridge** — a lower, free-draining corner that stays pale;
    * a damp **drip-line seam** — a faint horizontal band that keeps one row
      wetter than its neighbours, the signature of a buried irrigation line.

    The samples sit on a coarse grid (as a real sensor survey would); the
    smooth image comes from interpolating *between* these measured nodes.

    Parameters
    ----------
    seed : int, optional
        Seed for the small measurement noise, for a reproducible figure.

    Returns
    -------
    dict of str to numpy.ndarray
        ``{"field": (n_rows, n_cols) array of moisture %, "xs": (n_cols,)
        metres east, "ys": (n_rows,) metres north}``. Row 0 is the southern
        edge; ``field`` is oriented so higher row index = further north.
    """
    rng = np.random.default_rng(seed)
    # Coarse survey nodes: 9 columns east-west, 7 rows south-north.
    n_cols, n_rows = 9, 7
    xs = np.linspace(0.0, 40.0, n_cols)   # metres east of the datum peg
    ys = np.linspace(0.0, 30.0, n_rows)   # metres north of the datum peg
    gx, gy = np.meshgrid(xs, ys)          # (n_rows, n_cols)

    # Wet hollow: a broad Gaussian centred low-left, the moisture-holding basin.
    hollow = 34.0 * np.exp(-(((gx - 14.0) / 13.0) ** 2 + ((gy - 11.0) / 9.0) ** 2))

    # Dry ridge: a negative Gaussian in the far (north-east) corner.
    ridge = -12.0 * np.exp(-(((gx - 38.0) / 11.0) ** 2 + ((gy - 28.0) / 9.0) ** 2))

    # Drip-line seam: a damp horizontal band around the y = 22 m row. Kept
    # narrow but strong so it reads as a distinct brighter stripe, not a smear.
    seam = 14.0 * np.exp(-(((gy - 22.0) / 2.2) ** 2))

    # A dry baseline plus the features, with a little measurement noise.
    field = 18.0 + hollow + ridge + seam + rng.normal(0.0, 0.7, size=gx.shape)
    field = np.clip(field, 4.0, 55.0)     # moisture stays in a sane percent range
    return {"field": field, "xs": xs, "ys": ys}


# --------------------------------------------------------------------------- #
# Bilinear up-sampling (numpy only — no SVG blur filter)                       #
# --------------------------------------------------------------------------- #
def _bilinear_upsample(field: np.ndarray, factor: int = 26) -> np.ndarray:
    """Bilinearly interpolate a coarse grid onto a fine one.

    Each fine pixel is a weighted blend of its four surrounding coarse
    samples — the exact contract of ``imshow(interpolation="bilinear")``.
    Doing the blend here in numpy (rather than with an SVG Gaussian-blur
    filter) yields a genuinely interpolated raster that audits clean: the
    smoothness is in the *data*, not a post-hoc blur over hard cells.

    Parameters
    ----------
    field : numpy.ndarray
        The coarse ``(n_rows, n_cols)`` scalar grid.
    factor : int, optional
        Up-sampling factor per axis (fine pixels between successive nodes).

    Returns
    -------
    numpy.ndarray
        The fine ``((n_rows-1)*factor + 1, (n_cols-1)*factor + 1)`` grid.
    """
    n_rows, n_cols = field.shape
    fine_r = (n_rows - 1) * factor + 1
    fine_c = (n_cols - 1) * factor + 1

    # Fractional source coordinates for every fine pixel, in coarse-grid units.
    src_r = np.linspace(0.0, n_rows - 1, fine_r)
    src_c = np.linspace(0.0, n_cols - 1, fine_c)

    r0 = np.floor(src_r).astype(int)
    c0 = np.floor(src_c).astype(int)
    r1 = np.minimum(r0 + 1, n_rows - 1)
    c1 = np.minimum(c0 + 1, n_cols - 1)
    wr = (src_r - r0)[:, None]            # row weights, column vector
    wc = (src_c - c0)[None, :]            # col weights, row vector

    # Gather the four corners for the whole fine grid at once, then blend.
    top = field[np.ix_(r0, c0)] * (1 - wc) + field[np.ix_(r0, c1)] * wc
    bot = field[np.ix_(r1, c0)] * (1 - wc) + field[np.ix_(r1, c1)] * wc
    return top * (1 - wr) + bot * wr


# --------------------------------------------------------------------------- #
# Colour ramp                                                                  #
# --------------------------------------------------------------------------- #
def _ramp_hex(t: float, stops: Sequence[Tuple[float, str]] = _BLUE_RAMP) -> str:
    """Sample a multi-stop sRGB colour ramp at position ``t`` in ``[0, 1]``.

    Parameters
    ----------
    t : float
        Position along the ramp, clamped to ``[0, 1]``.
    stops : sequence of (float, str)
        Ordered ``(position, "#RRGGBB")`` anchor stops.

    Returns
    -------
    str
        The interpolated colour as ``#RRGGBB``.
    """
    t = min(1.0, max(0.0, t))
    for (lo_t, lo_c), (hi_t, hi_c) in zip(stops, stops[1:]):
        if lo_t <= t <= hi_t:
            local = (t - lo_t) / (hi_t - lo_t) if hi_t > lo_t else 0.0
            ar, ag, ab = int(lo_c[1:3], 16), int(lo_c[3:5], 16), int(lo_c[5:7], 16)
            br, bg, bb = int(hi_c[1:3], 16), int(hi_c[3:5], 16), int(hi_c[5:7], 16)
            r = round(ar + (br - ar) * local)
            g = round(ag + (bg - ag) * local)
            b = round(ab + (bb - ab) * local)
            return f"#{r:02X}{g:02X}{b:02X}"
    return stops[-1][1]


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def _fmt(v: float) -> str:
    """Format a float compactly for SVG (2 decimals, trimmed)."""
    return f"{v:.2f}".rstrip("0").rstrip(".")


def build_svg(
    grid: Dict[str, np.ndarray],
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full interpolated-heatmap SVG document as a string.

    Parameters
    ----------
    grid : dict of str to numpy.ndarray
        The output of :func:`_survey_grid` — ``field``, ``xs``, ``ys``.
    mode : str, optional
        Interactivity mode for the shared fullscreen control (see
        :mod:`_interactive`). Three modes: ``"self-contained"`` (default) ships
        a self-carrying fullscreen button and its wiring script; ``"external"``
        ships no internal button and defers to a page-level module; ``"static"``
        ships no interactivity at all. The static PNG raster is byte-identical
        across modes because the button starts hidden.
    accessibility : str, optional
        Accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). **No-op by design:** the heatmap uses a single-hue
        Apple-blue *sequential* ramp (``_BLUE_RAMP``, pale sky → system blue →
        deep navy), a perceptual value map that is already colour-vision- and
        greyscale-safe because it encodes magnitude by lightness, never by a
        red/green contrast. Re-spacing its anchors through the categorical
        accessibility engine compresses and de-tunes the ramp (the wide, clean
        light→dark sweep collapses toward mid-greys), so the level is
        deliberately *not* applied. The flag is accepted for a uniform command
        line. Defaults to ``"universal"``.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    # ``accessibility`` is accepted for a uniform CLI but intentionally unused:
    # the blue sequential ramp is already CVD/greyscale-safe (see the parameter
    # note above), so levelling it would only de-tune it.
    _ = accessibility
    field: np.ndarray = grid["field"]          # (n_rows, n_cols)
    xs: np.ndarray = grid["xs"]
    ys: np.ndarray = grid["ys"]

    # Interpolate the coarse survey onto a fine grid — this is the imshow blend.
    fine = _bilinear_upsample(field, factor=26)
    fine_r, fine_c = fine.shape

    # ---- canvas geometry -------------------------------------------------- #
    # Poster-size canvas: generous, readable at a glance, no cramping.
    width, height = 1240, 860
    m_left, m_right = 108, 168        # right margin holds the colour legend
    m_top, m_bottom = 138, 112
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    x_lo, x_hi = float(xs[0]), float(xs[-1])
    y_lo, y_hi = float(ys[0]), float(ys[-1])

    # Cell footprint of one fine pixel. A hair of overlap (+0.7px) hides seams
    # anti-aliasing would otherwise leave between adjacent fine cells.
    cell_w = plot_w / fine_c
    cell_h = plot_h / fine_r

    # Normalise the field to [0, 1] for the ramp, over the *coarse* extremes so
    # the legend ticks read the measured range, not an interpolation artefact.
    v_lo = float(field.min())
    v_hi = float(field.max())
    span = (v_hi - v_lo) or 1.0

    parts: List[str] = []

    # ---- header ----------------------------------------------------------- #
    title = "Soil moisture pools in the field's low hollow"
    subtitle = (
        "Bilinearly interpolated survey grid (imshow) · deeper blue = wetter soil "
        "· illustrative data"
    )
    parts.append(
        f'<svg role="img" aria-label="{title}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}">'
    )
    parts.append(
        f"<title>{title}</title>"
        f"<desc>An interpolated heatmap (imshow, bilinear): a coarse soil-moisture "
        f"survey grid displayed as one smooth continuous image, east-west by "
        f"north-south. A deep-blue basin near the low-left is the moisture-holding "
        f"hollow, the pale far corner is a free-draining ridge, and a faint blue "
        f"horizontal band is a damp irrigation drip line. Colour runs pale sky "
        f"(driest) to deep navy (wettest).</desc>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="18" fill="{_BG}"/>')
    parts.append(
        f'<text x="{m_left - 44}" y="60" font-size="30" font-weight="700" '
        f'fill="{_INK}">{title}</text>'
    )
    parts.append(
        f'<text x="{m_left - 44}" y="94" font-size="17" '
        f'fill="{_SECONDARY}">{subtitle}</text>'
    )

    # ---- heatmap cells (clipped to the plot rectangle) -------------------- #
    parts.append(
        f'<clipPath id="plot-clip"><rect x="{_fmt(m_left)}" y="{_fmt(m_top)}" '
        f'width="{_fmt(plot_w)}" height="{_fmt(plot_h)}" rx="6"/></clipPath>'
    )
    parts.append('<g clip-path="url(#plot-clip)" shape-rendering="crispEdges">')
    # Ground behind the cells (shows through the rounded clip corners).
    parts.append(
        f'<rect x="{_fmt(m_left)}" y="{_fmt(m_top)}" width="{_fmt(plot_w)}" '
        f'height="{_fmt(plot_h)}" fill="{_BLUE_RAMP[0][1]}"/>'
    )
    # Row j = 0 is the southern edge; draw it at the bottom of the plot so
    # north points up, as a field map reads.
    for j in range(fine_r):
        y = m_top + plot_h - (j + 1) * cell_h
        row = fine[j]
        for i in range(fine_c):
            norm = (float(row[i]) - v_lo) / span
            colour = _ramp_hex(norm)
            x = m_left + i * cell_w
            parts.append(
                f'<rect x="{_fmt(x)}" y="{_fmt(y)}" '
                f'width="{_fmt(cell_w + 0.7)}" height="{_fmt(cell_h + 0.7)}" '
                f'fill="{colour}"/>'
            )
    parts.append("</g>")

    # ---- plot border ------------------------------------------------------ #
    parts.append(
        f'<rect x="{_fmt(m_left)}" y="{_fmt(m_top)}" width="{_fmt(plot_w)}" '
        f'height="{_fmt(plot_h)}" rx="6" fill="none" stroke="{_INK}" '
        f'stroke-width="1.4"/>'
    )

    # ---- x-axis (east) ---------------------------------------------------- #
    def x_px(xm: float) -> float:
        """Map an easting (metres) to a pixel column."""
        return m_left + (xm - x_lo) / (x_hi - x_lo) * plot_w

    axis_y = m_top + plot_h
    for xm in (0, 10, 20, 30, 40):
        gx = x_px(float(xm))
        parts.append(
            f'<line x1="{_fmt(gx)}" y1="{_fmt(axis_y)}" x2="{_fmt(gx)}" '
            f'y2="{_fmt(axis_y + 7)}" stroke="{_INK}" stroke-width="1.2"/>'
        )
        parts.append(
            f'<text x="{_fmt(gx)}" y="{_fmt(axis_y + 28)}" text-anchor="middle" '
            f'font-size="15" font-family="{_MONO}" fill="{_SECONDARY}">{xm}</text>'
        )
    parts.append(
        f'<text x="{_fmt(m_left + plot_w / 2)}" y="{_fmt(axis_y + 62)}" '
        f'text-anchor="middle" font-size="17" fill="{_INK}">Distance east (m)</text>'
    )

    # ---- y-axis (north) --------------------------------------------------- #
    def y_px(ym: float) -> float:
        """Map a northing (metres) to a pixel row (south at the bottom)."""
        return m_top + plot_h - (ym - y_lo) / (y_hi - y_lo) * plot_h

    for ym in (0, 10, 20, 30):
        gy = y_px(float(ym))
        parts.append(
            f'<line x1="{_fmt(m_left - 7)}" y1="{_fmt(gy)}" x2="{_fmt(m_left)}" '
            f'y2="{_fmt(gy)}" stroke="{_INK}" stroke-width="1.2"/>'
        )
        parts.append(
            f'<text x="{_fmt(m_left - 13)}" y="{_fmt(gy + 5)}" text-anchor="end" '
            f'font-size="15" font-family="{_MONO}" fill="{_SECONDARY}">{ym}</text>'
        )
    parts.append(
        f'<text x="32" y="{_fmt(m_top + plot_h / 2)}" text-anchor="middle" '
        f'font-size="17" fill="{_INK}" '
        f'transform="rotate(-90 32 {_fmt(m_top + plot_h / 2)})">Distance north (m)</text>'
    )

    # ---- feature annotations --------------------------------------------- #
    # Labels ride directly on the field. On the deep-blue basin a white label
    # reads; on the pale corner a dark ink label reads. A soft backing pill
    # (a translucent fill, never a hard stroke halo) keeps every word legible.
    def _labelled(
        cx: float,
        cy: float,
        text: str,
        *,
        anchor: str = "middle",
        light: bool = True,
    ) -> None:
        """Place a feature label with a soft translucent backing pill."""
        pad_x = 9.0
        char_w = 8.8                       # rough advance for 15px Roboto 600
        w = len(text) * char_w + 2 * pad_x
        h = 25.0
        if anchor == "start":
            rx = cx - pad_x
        elif anchor == "end":
            rx = cx - (w - pad_x)
        else:  # middle
            rx = cx - w / 2
        pill = "#0A2E5C" if light else "#FFFFFF"
        ink = "#FFFFFF" if light else _INK
        parts.append(
            f'<rect x="{_fmt(rx)}" y="{_fmt(cy - h + 6.5)}" width="{_fmt(w)}" '
            f'height="{_fmt(h)}" rx="7" fill="{pill}" fill-opacity="0.55"/>'
        )
        parts.append(
            f'<text x="{_fmt(cx)}" y="{_fmt(cy)}" text-anchor="{anchor}" '
            f'font-size="15" font-weight="600" fill="{ink}">{text}</text>'
        )

    _labelled(x_px(14.0), y_px(11.0), "wet hollow", light=True)
    _labelled(x_px(37.0), y_px(28.0), "dry ridge", anchor="end", light=False)
    _labelled(x_px(20.0), y_px(22.0), "drip-line seam", light=True)

    # ---- colour legend (vertical value ramp) ------------------------------ #
    leg_x = width - m_right + 52
    leg_w = 22
    leg_top = m_top + 10
    leg_h = plot_h - 20
    grad_id = "value-ramp"
    parts.append(f'<defs><linearGradient id="{grad_id}" x1="0" y1="1" x2="0" y2="0">')
    for pos, col in _BLUE_RAMP:
        parts.append(f'<stop offset="{_fmt(pos * 100)}%" stop-color="{col}"/>')
    parts.append("</linearGradient></defs>")
    # A hairline light-neutral border keeps the ramp crisp on white — no hard
    # black outline, no ring around the swatch.
    parts.append(
        f'<rect x="{_fmt(leg_x)}" y="{_fmt(leg_top)}" width="{leg_w}" '
        f'height="{_fmt(leg_h)}" rx="5" fill="url(#{grad_id})" '
        f'stroke="#D2D2D7" stroke-width="1"/>'
    )
    # Legend tick labels: wettest at the top, driest at the bottom.
    v_mid = (v_lo + v_hi) / 2.0
    for frac, val in ((1.0, v_hi), (0.5, v_mid), (0.0, v_lo)):
        ly = leg_top + (1.0 - frac) * leg_h
        parts.append(
            f'<line x1="{_fmt(leg_x + leg_w)}" y1="{_fmt(ly)}" '
            f'x2="{_fmt(leg_x + leg_w + 6)}" y2="{_fmt(ly)}" '
            f'stroke="{_SECONDARY}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{_fmt(leg_x + leg_w + 11)}" y="{_fmt(ly + 5)}" '
            f'font-size="14" font-family="{_MONO}" fill="{_SECONDARY}">{val:.0f}</text>'
        )
    parts.append(
        f'<text x="{_fmt(leg_x + leg_w / 2)}" y="{_fmt(leg_top - 16)}" '
        f'text-anchor="middle" font-size="15" fill="{_INK}">Moisture</text>'
    )
    parts.append(
        f'<text x="{_fmt(leg_x + leg_w / 2)}" y="{_fmt(leg_top + leg_h + 26)}" '
        f'text-anchor="middle" font-size="13" fill="{_SECONDARY}">%</text>'
    )

    # --- shared fullscreen control. The colour legend sits on the right rail,
    #     so inset the button leftward to clear it. ---
    parts.append(fullscreen_control(width, height, mode, inset=100.0))

    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_imshow-interpolated",
        description="Write the house-style interpolated heatmap (imshow) SVG example.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--seed", type=int, default=7, help="Random seed for the synthesised survey."
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the shared fullscreen control.",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal", "high-contrast", "monochrome",
            "deuteranopia", "protanopia", "tritanopia",
        ),
        default="universal",
        help=(
            "palette accessibility level (default: universal). No-op here: the "
            "sequential blue ramp is already CVD/greyscale-safe."
        ),
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: synthesise the survey, interpolate it, write the SVG."""
    args = _build_parser().parse_args(argv)
    grid = _survey_grid(seed=args.seed)
    svg = build_svg(grid, mode=args.mode, accessibility=args.accessibility)
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

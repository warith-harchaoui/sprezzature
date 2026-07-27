#!/usr/bin/env python3
"""Generate a publication-quality *Andrews curves* figure as a standalone SVG.

An Andrews curve encodes one multivariate row as a smooth Fourier-series
curve traced over ``t ∈ [-π, π]``. For a standardised feature vector
``x = (x₁, x₂, x₃, x₄, x₅, …)`` the curve is

    f_x(t) = x₁/√2 + x₂·sin(t) + x₃·cos(t) + x₄·sin(2t) + x₅·cos(2t) + …

so every measured feature becomes one term of a truncated Fourier series.
Rows that are close in the original feature space stay close as curves
(the transform is distance-preserving up to a constant), which is why
colouring one curve per class makes clusters legible: a well-separated
class paints a tight ribbon of near-parallel curves, and an overlapping
class smears across the band. This is the R ``andrews`` / pandas
``andrews_curves`` idiom, drawn here by hand.

This module builds the SVG string **by hand** (no matplotlib / seaborn /
plotly, no Vega): it standardises the features, evaluates each row's
Fourier curve on a fine ``t`` grid (numpy only), and paints the curves as
translucent coloured strokes in the front-* house style — Roboto type, the
Apple-system palette, ink ``#1D1D1F`` on a white ground, rounded framing.
Per-class median curves are over-drawn in full opacity so the reader sees
each class's *signature* on top of its cloud, and a per-class ``<title>``
gives a native hover tooltip with no JavaScript.

The example data is illustrative: three penguin species measured on four
body dimensions (bill length and depth, flipper length, body mass). The
takeaway the figure is built to show is that the three species trace three
visibly distinct Fourier signatures — the multivariate structure the
Andrews transform is made to surface.

Usage
-----
    python make_andrews.py                 # writes the house SVG
    python make_andrews.py --out other.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc
classes, generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations
from _render import write_svg  # noqa: E402
from _svg import fmt_compact  # noqa: E402
from _style import leveled_colors, os_adaptive_style, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "andrews.svg"
)

# House-style tokens (mirrors _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_GRIDLINE = "#E5E5EA"   # light gridline
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"

# Apple-system hues (from the house palette) — one per class. Chosen with a
# clear third channel between them (blue / orange / green) so the figure
# survives colour-vision-deficiency review; each class is also labelled.
_CLASS_COLOURS: Dict[str, str] = {
    "Adélie": "#007AFF",     # Blue
    "Chinstrap": "#FF9500",  # Orange
    "Gentoo": "#34C759",     # Green
}

# The four body measurements, in the term order they occupy in the Fourier
# series. Order matters for the *shape* of the curve, so keep it stable.
_FEATURES: List[str] = [
    "bill length",
    "bill depth",
    "flipper length",
    "body mass",
]


# --------------------------------------------------------------------------- #
# Illustrative data                                                            #
# --------------------------------------------------------------------------- #
def _sample_penguins(seed: int = 11, per_class: int = 26) -> Tuple[np.ndarray, List[str]]:
    """Synthesise a small penguin body-measurement table, one block per species.

    Each species is drawn from a multivariate normal whose per-feature means
    echo the real Palmer-station contrasts (Gentoo are the largest and
    longest-flippered; Chinstrap have the longest, deepest bills; Adélie sit
    between), with modest within-species spread and a little inter-feature
    correlation so the clouds read like real morphometrics rather than noise.

    Parameters
    ----------
    seed : int, optional
        Seed for the random generator, for a reproducible figure.
    per_class : int, optional
        Rows drawn per species.

    Returns
    -------
    tuple of (numpy.ndarray, list of str)
        ``(X, labels)`` where ``X`` is ``(n_rows, 4)`` of raw measurements in
        feature order :data:`_FEATURES`, and ``labels`` is the matching
        species name per row.
    """
    rng = np.random.default_rng(seed)

    # Per-species mean vectors over (bill length mm, bill depth mm,
    # flipper length mm, body mass g) — illustrative but true to the contrasts.
    means: Dict[str, np.ndarray] = {
        "Adélie":    np.array([38.8, 18.3, 190.0, 3700.0]),
        "Chinstrap": np.array([48.8, 18.4, 195.8, 3733.0]),
        "Gentoo":    np.array([47.5, 15.0, 217.2, 5076.0]),
    }
    # A shared-ish spread per feature; body mass is the widest in absolute terms.
    spread = np.array([2.6, 1.1, 6.3, 430.0])

    rows: List[np.ndarray] = []
    labels: List[str] = []
    for name, mu in means.items():
        block = rng.normal(mu, spread, size=(per_class, len(_FEATURES)))
        rows.append(block)
        labels.extend([name] * per_class)
    return np.vstack(rows), labels


def _standardise(x: np.ndarray) -> np.ndarray:
    """Z-score each feature column (mean 0, unit variance).

    Andrews curves are dominated by whichever feature has the largest raw
    scale (body mass, in the thousands, would otherwise drown the bills), so
    standardising first is what lets every measurement contribute a
    comparably-sized Fourier term.

    Parameters
    ----------
    x : numpy.ndarray
        ``(n_rows, n_features)`` raw measurement matrix.

    Returns
    -------
    numpy.ndarray
        Same shape, each column centred and scaled to unit standard deviation.
    """
    mu = x.mean(axis=0, keepdims=True)
    sd = x.std(axis=0, keepdims=True)
    sd[sd == 0.0] = 1.0  # guard a degenerate constant column
    return (x - mu) / sd


# --------------------------------------------------------------------------- #
# The Andrews transform                                                        #
# --------------------------------------------------------------------------- #
def andrews_curve(row: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Evaluate the Andrews Fourier curve of one feature vector on a t-grid.

    Implements ``f(t) = x₀/√2 + x₁ sin t + x₂ cos t + x₃ sin 2t + x₄ cos 2t
    + …`` — the standard construction, with sine/cosine terms alternating at
    increasing harmonics.

    Parameters
    ----------
    row : numpy.ndarray
        1-D standardised feature vector of length ``m``.
    t : numpy.ndarray
        1-D grid of angles (typically ``linspace(-π, π)``).

    Returns
    -------
    numpy.ndarray
        The curve ``f(t)``, same length as ``t``.
    """
    # First term is the constant x0 / sqrt(2).
    out = row[0] / np.sqrt(2.0)
    # Remaining terms alternate sin, cos at harmonics 1, 1, 2, 2, 3, 3, ...
    harmonic = 1
    use_sin = True
    for coeff in row[1:]:
        basis = np.sin(harmonic * t) if use_sin else np.cos(harmonic * t)
        out = out + coeff * basis
        if not use_sin:
            harmonic += 1  # bump harmonic after each cos term
        use_sin = not use_sin
    return out


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def _poly_d(xs: np.ndarray, ys: np.ndarray) -> str:
    """Build an SVG polyline ``d`` attribute from parallel x/y pixel arrays."""
    pts = [f"{fmt_compact(float(px))},{fmt_compact(float(py))}" for px, py in zip(xs, ys)]
    return "M" + " L".join(pts)


def build_svg(
    x_raw: np.ndarray,
    labels: List[str],
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full Andrews-curves SVG document as a string.

    Parameters
    ----------
    x_raw : numpy.ndarray
        ``(n_rows, n_features)`` raw measurement matrix.
    labels : list of str
        Class label per row (same length as ``x_raw``).
    mode : str, optional
        Interactivity mode for the figure (default ``"self-contained"``).
        ``"self-contained"`` embeds a self-carrying fullscreen button and the
        script that wires it, so the SVG works on its own; ``"external"``
        defers that control to a page-level module; ``"static"`` ships no
        interactivity at all. In every mode a plain ``<img>`` or PNG raster is
        byte-identical, since the button starts hidden.
    accessibility : str, optional
        Palette accessibility level applied to the per-class hues (default
        ``"universal"``, the colour-vision-safe standard that leaves the
        shipped colours unchanged). Other levels (``"monochrome"``,
        ``"deuteranopia"``, ...) remap the three species colours through the
        sprezzature-colors engine so the classes stay distinct for that viewer.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    # Per-class hues, remapped for the requested accessibility level. At the
    # ``universal`` default this is the identity, so the shipped SVG is
    # byte-for-byte unchanged.
    class_colours = leveled_colors(_CLASS_COLOURS, accessibility)
    # ---- canvas geometry -------------------------------------------------- #
    # Poster-scale canvas: a big, generous figure so the curve clouds have
    # room to breathe and the per-species ribbons stop piling into a blob.
    width, height = 1180, 820
    m_left, m_right = 108, 250   # right margin holds the class legend
    m_top, m_bottom = 132, 104
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    # ---- standardise + evaluate curves ------------------------------------ #
    x_std = _standardise(x_raw)
    n_pts = 240
    t = np.linspace(-np.pi, np.pi, n_pts)

    curves = np.stack([andrews_curve(row, t) for row in x_std])  # (n_rows, n_pts)

    # Shared y-domain across every curve, padded a touch.
    y_lo = float(curves.min())
    y_hi = float(curves.max())
    pad = 0.06 * (y_hi - y_lo)
    y_lo -= pad
    y_hi += pad

    def x_px(tv: float) -> float:
        """Map an angle t ∈ [-π, π] to a pixel column."""
        return m_left + (tv + np.pi) / (2.0 * np.pi) * plot_w

    def y_px(v: float) -> float:
        """Map a curve value to a pixel row (y grows downward)."""
        return m_top + (y_hi - v) / (y_hi - y_lo) * plot_h

    t_px = np.array([x_px(tv) for tv in t])

    # Ordered, de-duplicated class list in first-appearance order.
    classes: List[str] = []
    for lab in labels:
        if lab not in classes:
            classes.append(lab)

    parts: List[str] = []

    # ---- header ----------------------------------------------------------- #
    title = "Three penguin species trace three Fourier signatures"
    subtitle = (
        "Each curve turns one bird's four body measurements into an "
        "Andrews series; bold lines are the species medians. Illustrative data."
    )
    parts.append(
        f'<svg role="img" aria-label="{title}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}">'
    )
    parts.append(
        f"<title>{title}</title>"
        f"<desc>Andrews curves: every penguin's standardised bill length, "
        f"bill depth, flipper length and body mass are encoded as a Fourier "
        f"curve over t from minus pi to pi, coloured by species. Adélie in "
        f"blue, Chinstrap in orange and Gentoo in green each form a distinct "
        f"band, with the bold median curve of each species drawn on top.</desc>"
    )
    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule lives inside a media query). Under
    # prefers-contrast each species deepens to its high-contrast hue on the
    # stroke role — clouds, median lines and legend swatches together — so the
    # three Fourier signatures stay pairwise distinct for a low-vision reader.
    _classes_ordered: List[str] = []
    for _lab in labels:
        if _lab not in _classes_ordered:
            _classes_ordered.append(_lab)
    curve_series = {
        f".cls-{ci}": class_colours.get(cls, "#8E8E93")
        for ci, cls in enumerate(_classes_ordered)
    }
    # forced-colors (Windows High Contrast): the class identity is carried by
    # colour alone (the curves have no per-curve label), and the ~4-colour system
    # palette would flatten every species to one ink. The curves are OPEN strokes,
    # not fills, so a hatch pattern would not read; instead give each species a
    # distinct stroke-dasharray (solid / dashed / dotted) so the three Fourier
    # signatures stay separable by line texture without colour. Additive and
    # media-gated, so the default render is unchanged.
    _fc_dashes = ["", "10 7", "2 6"]  # class 0 solid, 1 dashed, 2 dotted
    _fc_rows = "".join(
        f".cls-{ci}{{stroke:CanvasText;forced-color-adjust:none;"
        + (f"stroke-dasharray:{_fc_dashes[ci % len(_fc_dashes)]};" if _fc_dashes[ci % len(_fc_dashes)] else "")
        + "}"
        for ci in range(len(_classes_ordered))
    )
    fc_style = "@media (forced-colors: active){" + _fc_rows + "}"
    parts.append(
        "<style>"
        + os_adaptive_style(curve_series, role="stroke")
        + fc_style
        # Light gridlines are stroked, not filled, so the default ink inversions
        # miss them; drop them to a low-contrast dark grey on a dark ground.
        + os_dark_style(extra='[stroke="#E5E5EA"]{stroke:#2C2C2E;}')
        + "</style>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="18" fill="{_BG}"/>')
    parts.append(
        f'<text x="{m_left - 42}" y="60" font-size="30" font-weight="700" '
        f'fill="{_INK}">{title}</text>'
    )
    # Subtitle can be a touch long; keep it on one line.
    parts.append(
        f'<text x="{m_left - 42}" y="92" font-size="17" '
        f'fill="{_SECONDARY}">{subtitle}</text>'
    )

    # ---- horizontal gridline at f = 0 + light vertical t-ticks ------------ #
    # Zero reference line.
    if y_lo < 0.0 < y_hi:
        zy = y_px(0.0)
        parts.append(
            f'<line x1="{fmt_compact(m_left)}" y1="{fmt_compact(zy)}" '
            f'x2="{fmt_compact(m_left + plot_w)}" y2="{fmt_compact(zy)}" '
            f'stroke="{_GRIDLINE}" stroke-width="1.4"/>'
        )
    # Vertical gridlines at the labelled angle ticks.
    tick_angles = [-np.pi, -np.pi / 2.0, 0.0, np.pi / 2.0, np.pi]
    for tv in tick_angles:
        gx = x_px(tv)
        parts.append(
            f'<line x1="{fmt_compact(gx)}" y1="{fmt_compact(m_top - 12)}" '
            f'x2="{fmt_compact(gx)}" y2="{fmt_compact(m_top + plot_h + 8)}" '
            f'stroke="{_GRIDLINE}" stroke-width="1.4"/>'
        )

    # ---- per-class curve clouds (translucent) ----------------------------- #
    # Paint each class as a group so the hover tooltip covers the whole cloud.
    for ci, cls in enumerate(classes):
        colour = class_colours.get(cls, "#8E8E93")
        idx = [i for i, lab in enumerate(labels) if lab == cls]
        parts.append('<g class="cloud">')
        # Native tooltip: which class and how many curves.
        parts.append(
            f"<title>{cls} — {len(idx)} birds; bold line is the species "
            f"median curve</title>"
        )
        for i in idx:
            ys = np.array([y_px(v) for v in curves[i]])
            parts.append(
                f'<path class="cls-{ci}" d="{_poly_d(t_px, ys)}" fill="none" '
                f'stroke="{colour}" stroke-width="1.3" stroke-opacity="0.20" '
                f'stroke-linejoin="round"/>'
            )
        parts.append("</g>")

    # ---- per-class median curves (bold, drawn on top) --------------------- #
    for ci, cls in enumerate(classes):
        colour = class_colours.get(cls, "#8E8E93")
        idx = [i for i, lab in enumerate(labels) if lab == cls]
        med = np.median(curves[idx], axis=0)
        ys = np.array([y_px(v) for v in med])
        # Light halo under the bold median lifts it off the overlapping
        # cloud where the three ribbons cross; pure white, no dark ring.
        parts.append(
            f'<path d="{_poly_d(t_px, ys)}" fill="none" stroke="#FFFFFF" '
            f'stroke-width="8.5" stroke-opacity="0.9" stroke-linejoin="round"/>'
        )
        parts.append(
            f'<path class="cls-{ci}" d="{_poly_d(t_px, ys)}" fill="none" '
            f'stroke="{colour}" stroke-width="4.2" stroke-linejoin="round"/>'
        )

    # ---- axes ------------------------------------------------------------- #
    axis_y = m_top + plot_h
    parts.append(
        f'<line x1="{fmt_compact(m_left)}" y1="{fmt_compact(axis_y)}" '
        f'x2="{fmt_compact(m_left + plot_w)}" y2="{fmt_compact(axis_y)}" '
        f'stroke="{_INK}" stroke-width="1.6"/>'
    )
    parts.append(
        f'<line x1="{fmt_compact(m_left)}" y1="{fmt_compact(m_top - 12)}" '
        f'x2="{fmt_compact(m_left)}" y2="{fmt_compact(axis_y)}" '
        f'stroke="{_INK}" stroke-width="1.6"/>'
    )

    # x tick labels: -π, -π/2, 0, π/2, π.
    tick_labels = ["−π", "−π/2", "0", "π/2", "π"]
    for tv, lab in zip(tick_angles, tick_labels):
        gx = x_px(tv)
        parts.append(
            f'<text x="{fmt_compact(gx)}" y="{fmt_compact(axis_y + 30)}" text-anchor="middle" '
            f'font-size="15" font-family="{_MONO}" fill="{_SECONDARY}">'
            f"{lab}</text>"
        )
    parts.append(
        f'<text x="{fmt_compact(m_left + plot_w / 2)}" y="{fmt_compact(axis_y + 66)}" '
        f'text-anchor="middle" font-size="17" fill="{_INK}">'
        f"t (Fourier phase, −π to π)</text>"
    )

    # y-axis title, rotated.
    y_title_x = m_left - 70
    y_title_y = m_top + plot_h / 2.0
    parts.append(
        f'<text x="{fmt_compact(y_title_x)}" y="{fmt_compact(y_title_y)}" '
        f'text-anchor="middle" font-size="17" fill="{_INK}" '
        f'transform="rotate(-90 {fmt_compact(y_title_x)} {fmt_compact(y_title_y)})">'
        f"f(t) — Andrews series value</text>"
    )

    # ---- legend (right margin) -------------------------------------------- #
    lx = m_left + plot_w + 44
    ly = m_top + 12
    parts.append(
        f'<text x="{fmt_compact(lx)}" y="{fmt_compact(ly)}" font-size="17" '
        f'font-weight="700" fill="{_INK}">Species</text>'
    )
    for k, cls in enumerate(classes):
        colour = class_colours.get(cls, "#8E8E93")
        row_y = ly + 38 + k * 40
        parts.append(
            f'<line class="cls-{k}" x1="{fmt_compact(lx)}" y1="{fmt_compact(row_y)}" '
            f'x2="{fmt_compact(lx + 34)}" y2="{fmt_compact(row_y)}" '
            f'stroke="{colour}" stroke-width="5" stroke-linecap="round"/>'
        )
        parts.append(
            f'<text x="{fmt_compact(lx + 46)}" y="{fmt_compact(row_y + 6)}" '
            f'font-size="16" fill="{_INK}">{cls}</text>'
        )

    # ---- feature-order caption (what the terms encode) -------------------- #
    cap_y = ly + 38 + len(classes) * 40 + 24
    parts.append(
        f'<text x="{fmt_compact(lx)}" y="{fmt_compact(cap_y)}" '
        f'font-size="14" fill="{_SECONDARY}">Fourier term order:</text>'
    )
    # Wrap the term order into the right column, one feature per line.
    for i, name in enumerate(_FEATURES):
        parts.append(
            f'<text x="{fmt_compact(lx)}" '
            f'y="{fmt_compact(cap_y + 26 + i * 24)}" '
            f'font-size="14" font-family="{_MONO}" fill="{_SECONDARY}">'
            f"x{i + 1} = {name}</text>"
        )

    parts.append(fullscreen_control(width, height, mode, inset=270.0))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_andrews",
        description="Write the house-style Andrews-curves SVG example.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--seed", type=int, default=11, help="Random seed for the sample data."
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the figure (default: self-contained).",
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
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to disk."""
    args = _build_parser().parse_args(argv)
    x_raw, labels = _sample_penguins(seed=args.seed)
    svg = build_svg(x_raw, labels, mode=args.mode, accessibility=args.accessibility)
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

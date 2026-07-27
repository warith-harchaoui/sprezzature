#!/usr/bin/env python3
"""
make_prcurve — the precision-recall curve as hand-authored SVG.

Generate the **precision-recall (PR) curve** figure in the
``sprezzature-figures`` house style. As the decision threshold of a binary
classifier sweeps from strict to lenient, precision (of the positives it
flags, how many are truly positive) is plotted against recall (of all the
true positives, how many it caught). Each curve is the model's whole
precision-vs-recall trade-off in one line, and the area under it — the
**average precision (AP)** — labels the curve directly.

The scenario is a **fraud-detection** classifier scoring card
transactions, where the positive class (fraud) is rare — roughly 3 % of
transactions. That prevalence matters: on an imbalanced problem the PR
curve is the honest picture (unlike the receiver-operating-characteristic
curve, whose large true-negative pool flatters a weak model). To make the
comparison legible the figure layers **two** models — a strong gradient-
boosted model and a weaker logistic baseline — so the reader sees one
curve dominate the other across the whole recall range.

Every PR curve is read against the **no-skill baseline**: a classifier
that ignores its input scores precision equal to the positive-class
prevalence at every recall, a flat horizontal line. A curve hugging that
line has learned nothing; the vertical gap above it is the signal. The
figure draws that baseline as a dashed rule and annotates it, so the
takeaway ("well above chance") is unmistakable. Faint **iso-F1 contours**
(curves of constant F1 score) arc through the plot so a reader can read
each operating point's F1 straight off the background.

This generator builds the SVG by hand (no matplotlib / seaborn / plotly,
no Vega) so the two curves are separated by more than hue: each carries a
dash pattern and a distinct end marker, plus an inline direct label with
its AP. That keeps them apart under deuteranopia and in greyscale. The
figure matches the front-* house style: Roboto, the Apple-ish palette,
rounded corners, ink ``#1D1D1F``, secondary ``#6E6E73``, white
background, white keylines.

Each curve carries a native ``<title>`` tooltip and the shipped
(max-F1) operating point is emphasised with a marker and its own
tooltip; no JavaScript beyond the shared fullscreen control.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/prcurve.svg``.

Usage
-----
::

    python make_prcurve.py            # writes next to the skill
    python make_prcurve.py --out /tmp/prcurve.svg
    python make_prcurve.py --mode static   # no fullscreen button

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# House-style palette + shared primitives live alongside in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402


def _sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically-stable logistic sigmoid.

    Parameters
    ----------
    z : numpy.ndarray
        Log-odds / score values.

    Returns
    -------
    numpy.ndarray
        ``1 / (1 + exp(-z))`` in ``(0, 1)``.
    """
    return 1.0 / (1.0 + np.exp(-z))


def _pr_from_scores(
    y_true: np.ndarray,
    scores: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """Compute the precision-recall curve and average precision from scores.

    Implements the standard scikit-learn ``precision_recall_curve`` +
    ``average_precision_score`` contract in a few lines of NumPy so the
    figure carries no scikit-learn dependency. Thresholds are the unique
    scores in descending order; at each threshold everything scoring at or
    above it is predicted positive.

    Average precision is the step-function area under the curve,
    :math:`\\sum_k (R_k - R_{k-1}) P_k` — the weighted mean of precisions
    with the recall increments as weights — which is what scikit-learn
    reports (and, unlike trapezoidal integration, does not optimistically
    interpolate between operating points).

    Parameters
    ----------
    y_true : numpy.ndarray
        Ground-truth labels in ``{0, 1}``.
    scores : numpy.ndarray
        Classifier scores; higher means more likely positive.

    Returns
    -------
    recall : numpy.ndarray
        Recall at each operating point, ascending, prepended with the
        ``(recall=0, precision=1)`` anchor scikit-learn uses.
    precision : numpy.ndarray
        Precision at each operating point, aligned with ``recall``.
    average_precision : float
        Area under the PR curve (the AP summary statistic).
    """
    # Sort by descending score; sweep the threshold downward.
    order = np.argsort(-scores, kind="mergesort")
    y_sorted = y_true[order]

    total_positives = float(y_sorted.sum())
    # Cumulative true / false positives as we admit each next-highest score.
    true_positives = np.cumsum(y_sorted)
    false_positives = np.cumsum(1.0 - y_sorted)

    precision = true_positives / np.maximum(true_positives + false_positives, 1e-12)
    recall = true_positives / max(total_positives, 1e-12)

    # Collapse tied scores onto their last index so each distinct threshold
    # contributes a single operating point (scikit-learn semantics).
    distinct = np.where(np.diff(scores[order]))[0]
    keep = np.r_[distinct, len(y_sorted) - 1]
    precision = precision[keep]
    recall = recall[keep]

    # Average precision: sum of precision * (delta recall). The recall array
    # starts from the first admitted score, so the first increment is measured
    # against recall 0.
    recall_prev = np.r_[0.0, recall[:-1]]
    average_precision = float(np.sum((recall - recall_prev) * precision))

    # Prepend the canonical (recall=0, precision=1) anchor so the curve starts
    # cleanly on the left axis.
    recall = np.r_[0.0, recall]
    precision = np.r_[1.0, precision]
    return recall, precision, average_precision


def _thin(
    recall: np.ndarray,
    precision: np.ndarray,
    model: str,
    max_points: int = 120,
) -> List[Dict[str, Any]]:
    """Down-sample a dense PR curve to a plottable record list.

    A full sweep over thousands of transactions yields thousands of
    operating points; the SVG only needs enough to draw a smooth line.
    Points are sampled at evenly-spaced recall indices, always keeping the
    first and last so the curve spans the full axis.

    Parameters
    ----------
    recall, precision : numpy.ndarray
        The curve from :func:`_pr_from_scores`.
    model : str
        Label carried on every record.
    max_points : int, optional
        Target number of points to keep. Default 120.

    Returns
    -------
    list of dict
        ``{"recall": float, "precision": float, "model": str}`` records.
    """
    n = len(recall)
    if n <= max_points:
        idx = np.arange(n)
    else:
        idx = np.unique(np.linspace(0, n - 1, max_points).astype(int))
    return [
        {
            "recall": round(float(recall[i]), 4),
            "precision": round(float(precision[i]), 4),
            "model": model,
        }
        for i in idx
    ]


def make_data(
    n: int = 6000,
    prevalence: float = 0.03,
    seed: int = 11,
) -> Dict[str, Any]:
    """Simulate two fraud classifiers and return their PR curves + AP.

    Ground truth is a rare positive class (fraud). Two score generators
    with different separability are simulated:

    * **Gradient-boosted** — well-separated scores, the strong model;
    * **Logistic baseline** — noisier scores, the weaker model.

    Both are pushed through a logistic link so the scores read as
    calibrated-ish probabilities in ``(0, 1)``.

    Parameters
    ----------
    n : int, optional
        Number of transactions. Default 6000.
    prevalence : float, optional
        Fraction of the positive (fraud) class. Default 0.03.
    seed : int, optional
        NumPy random seed for reproducibility. Default 11.

    Returns
    -------
    dict
        ``{"curves": [record, ...], "ap": {model: float}, "prevalence":
        float, "points": [operating-point record, ...]}`` — ``curves``
        feeds the line layers, ``points`` the highlighted operating-point
        markers, ``ap`` the direct labels, ``prevalence`` the baseline.
    """
    rng = np.random.default_rng(seed)

    y_true = (rng.random(n) < prevalence).astype(int)
    positives = y_true == 1
    negatives = ~positives

    # Latent log-odds: positives shifted up, negatives down. A larger gap =
    # a stronger model. Both share the same ground truth so the curves are
    # directly comparable.
    def _scores(gap_pos: float, gap_neg: float, noise: float) -> np.ndarray:
        z = np.empty(n)
        z[positives] = rng.normal(gap_pos, noise, positives.sum())
        z[negatives] = rng.normal(gap_neg, noise, negatives.sum())
        return _sigmoid(z)

    strong = _scores(gap_pos=2.6, gap_neg=-2.2, noise=1.3)
    weak = _scores(gap_pos=1.2, gap_neg=-1.0, noise=1.7)

    curves: List[Dict[str, Any]] = []
    ap: Dict[str, float] = {}
    points: List[Dict[str, Any]] = []

    for label, scores in (
        ("Gradient-boosted", strong),
        ("Logistic baseline", weak),
    ):
        recall, precision, average_precision = _pr_from_scores(y_true, scores)
        curves.extend(_thin(recall, precision, label))
        ap[label] = round(average_precision, 3)

        # Highlight one operating point per model: the threshold that
        # maximises the F1 score (the harmonic mean of precision and
        # recall) — the point a practitioner would ship.
        f1 = 2.0 * precision * recall / np.maximum(precision + recall, 1e-12)
        best = int(np.argmax(f1[1:])) + 1  # skip the (0, 1) anchor
        points.append(
            {
                "recall": round(float(recall[best]), 4),
                "precision": round(float(precision[best]), 4),
                "model": label,
                "f1": round(float(f1[best]), 3),
            }
        )

    return {
        "curves": curves,
        "ap": ap,
        "prevalence": round(float(y_true.mean()), 4),
        "points": points,
    }


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full precision-recall-curve SVG string.

    The plot is a square unit view (recall on x, precision on y, both in
    ``[0, 1]``) carrying, bottom to top: a faint no-skill floor shaded up
    to the prevalence line; the dashed no-skill baseline with its label;
    faint iso-F1 contours; the two model curves (each a distinct hue *and*
    dash *and* end marker); the shipped (max-F1) operating-point markers;
    and inline direct labels with each curve's average precision.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``: the SVG carries its own fullscreen button.
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
    bundle = make_data()
    palette: Dict[str, str] = load_palette(accessibility)

    # Two hues that stay apart under deuteranopia and greyscale: blue for the
    # strong model, orange for the weak baseline. The split is reinforced by a
    # dash pattern and a distinct end marker per curve, so hue is never the
    # only channel carrying "which model is which".
    strong_col = palette.get("Blue", "#007AFF")
    weak_col = palette.get("Orange", "#FF9500")
    ink = "#1D1D1F"
    secondary = "#6E6E73"
    grid_col = "#ECECEC"
    floor_col = "#8E8E93"

    prevalence = bundle["prevalence"]
    ap = bundle["ap"]
    strong_ap = ap["Gradient-boosted"]
    weak_ap = ap["Logistic baseline"]

    # Per-model visual style. ``dash`` is the SVG dash-array (empty = solid),
    # ``marker`` picks the end-glyph shape so the two curves differ by shape
    # as well as hue.
    style: Dict[str, Dict[str, Any]] = {
        "Gradient-boosted": {"col": strong_col, "dash": "", "marker": "circle", "slug": "strong"},
        "Logistic baseline": {"col": weak_col, "dash": "10 7", "marker": "square", "slug": "weak"},
    }

    # --- canvas geometry -----------------------------------------
    width = 1180
    height = 1140
    m_left = 168
    m_right = 96
    m_top = 250
    m_bottom = 150
    plot_x = m_left
    plot_y = m_top
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    ticks = [0.0, 0.25, 0.5, 0.75, 1.0]

    def sx(v: float) -> float:
        """Map recall in ``[0, 1]`` to an x pixel coordinate."""
        return plot_x + v * plot_w

    def sy(v: float) -> float:
        """Map precision in ``[0, 1]`` to a y pixel coordinate (y-down)."""
        return plot_y + (1.0 - v) * plot_h

    # Group the thinned curve records back into per-model point lists, in the
    # (recall-ascending) order make_data produced them.
    per_model: Dict[str, List[Tuple[float, float]]] = {
        "Gradient-boosted": [],
        "Logistic baseline": [],
    }
    for rec in bundle["curves"]:
        per_model[rec["model"]].append((float(rec["recall"]), float(rec["precision"])))

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    parts.append(svg_open(width, height, "pr-title", "pr-desc"))
    parts.append(
        '<title id="pr-title">Gradient boosting flags fraud far more precisely '
        'than the logistic baseline</title>'
    )
    parts.append(
        f'<desc id="pr-desc">Precision-recall curves for two fraud-detection '
        f'classifiers on an imbalanced problem (fraud prevalence '
        f'{prevalence:.0%}). The horizontal axis is recall (share of fraud '
        f'caught); the vertical axis is precision (share of flagged '
        f'transactions that are fraud); both run from 0 to 1. The strong '
        f'gradient-boosted model (solid blue, circle marker, average '
        f'precision {strong_ap:.2f}) sits well above the weaker logistic '
        f'baseline (dashed orange, square marker, average precision '
        f'{weak_ap:.2f}) across the whole recall range. A dashed grey '
        f'no-skill baseline runs flat at precision equal to the {prevalence:.0%} '
        f'prevalence; the vertical gap above it is the signal each model has '
        f'learned. Faint iso-F1 contours arc through the plot, and each '
        f'model is marked at its shipped maximum-F1 operating point. '
        f'Illustrative data.</desc>'
    )

    # OS-adaptive overrides are appended (additive; every rule lives inside an
    # @media block so the default render is byte-for-byte unchanged). The two
    # model hues carry ``.pr-line-<slug>`` on the curve strokes (and the key
    # sample lines) and ``.pr-mark-<slug>`` on the filled operating-point and
    # key glyphs. Under prefers-contrast both deepen to their high-contrast
    # blue/orange. The line hook is stroke-only so an open curve path is never
    # flooded by a fill override; the marker hook is fill-only so each glyph's
    # white keyline is left intact. forced-colors is left to the browser default
    # — the two models are already separated by dash pattern, end-marker shape
    # and a direct AP label, so colour is redundant and need not survive there.
    line_series = {
        f".pr-line-{style[m]['slug']}": style[m]["col"]
        for m in ("Gradient-boosted", "Logistic baseline")
    }
    mark_series = {
        f".pr-mark-{style[m]['slug']}": style[m]["col"]
        for m in ("Gradient-boosted", "Logistic baseline")
    }
    contrast_block = (
        os_adaptive_style(line_series, role="stroke")
        + "\n"
        + os_adaptive_style(mark_series, role="fill")
    )
    # Static figure (curves + markers); hover / focus enlargement only.
    parts.append(
        "<style>"
        ".op{cursor:pointer}"
        ".op .halo{opacity:0}"
        ".op:hover .halo,.op:focus .halo{opacity:1}"
        ".op:focus{outline:none}"
        ".curve{cursor:pointer}"
        + "\n" + contrast_block + "\n"
        + os_dark_style() + "\n"
        "</style>"
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="96" font-size="44" font-weight="700" '
        f'fill="{ink}">Gradient boosting flags fraud far more precisely</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="148" font-size="25" fill="{secondary}">'
        f'Precision vs recall as the threshold varies — AP '
        f'{strong_ap:.2f} vs {weak_ap:.2f} · illustrative</text>'
    )

    # --- gridlines (very light) ----------------------------------
    for t in ticks:
        gx = sx(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{plot_y:.1f}" x2="{gx:.1f}" '
            f'y2="{plot_y + plot_h:.1f}" stroke="{grid_col}" stroke-width="1.4"/>'
        )
        gy = sy(t)
        parts.append(
            f'<line x1="{plot_x:.1f}" y1="{gy:.1f}" x2="{plot_x + plot_w:.1f}" '
            f'y2="{gy:.1f}" stroke="{grid_col}" stroke-width="1.4"/>'
        )

    # --- no-skill floor: a faint band from precision 0 up to the ---
    # prevalence line, the region where a curve means "no better than
    # guessing". Shaded so the eye reads the baseline as a floor.
    y_prev = sy(prevalence)
    y_zero = sy(0.0)
    parts.append(
        f'<rect x="{plot_x:.1f}" y="{y_prev:.1f}" width="{plot_w:.1f}" '
        f'height="{y_zero - y_prev:.1f}" fill="{floor_col}" '
        f'fill-opacity="0.09"/>'
    )

    # --- iso-F1 contours ------------------------------------------
    # Curves of constant F1: for a target F1 = f and recall r,
    # precision p = f * r / (2 r - f), valid where 2 r - f > 0. Drawn as a
    # faint polyline so a reader can read an operating point's F1 off the
    # background without a separate legend.
    for f in (0.2, 0.4, 0.6, 0.8):
        pts_iso: List[Tuple[float, float]] = []
        for k in range(201):
            r = k / 200.0
            denom = 2.0 * r - f
            if denom <= 1e-6:
                continue
            p = f * r / denom
            if 0.0 <= p <= 1.0 and 0.0 <= r <= 1.0:
                pts_iso.append((sx(r), sy(p)))
        if len(pts_iso) < 2:
            continue
        d_iso = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts_iso)
        parts.append(
            f'<path d="{d_iso}" fill="none" stroke="{floor_col}" '
            f'stroke-width="1.2" stroke-opacity="0.42" stroke-dasharray="2 6"/>'
        )
        # Label the contour where it exits the top edge (precision high).
        lx, ly = pts_iso[0]
        parts.append(
            f'<text x="{lx + 8:.1f}" y="{ly + 20:.1f}" font-size="17" '
            f'fill="{secondary}" fill-opacity="0.8">F1 {f:.1f}</text>'
        )

    # --- no-skill baseline ----------------------------------------
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{y_prev:.1f}" x2="{plot_x + plot_w:.1f}" '
        f'y2="{y_prev:.1f}" stroke="{secondary}" stroke-width="2" '
        f'stroke-dasharray="9 6"/>'
    )
    parts.append(
        f'<text x="{plot_x + 12:.1f}" y="{y_prev - 12:.1f}" font-size="20" '
        f'fill="{secondary}">No-skill baseline (prevalence {prevalence:.0%})</text>'
    )

    # --- axes (L-shaped, ink) ------------------------------------
    ax_bottom = plot_y + plot_h
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{ax_bottom:.1f}" '
        f'x2="{plot_x + plot_w:.1f}" y2="{ax_bottom:.1f}" '
        f'stroke="{ink}" stroke-width="1.8"/>'
    )
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{plot_y:.1f}" x2="{plot_x:.1f}" '
        f'y2="{ax_bottom:.1f}" stroke="{ink}" stroke-width="1.8"/>'
    )
    for t in ticks:
        gx = sx(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{ax_bottom:.1f}" x2="{gx:.1f}" '
            f'y2="{ax_bottom + 8:.1f}" stroke="{ink}" stroke-width="1.8"/>'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="{ax_bottom + 38:.1f}" font-size="21" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">{t:.0%}</text>'
        )
        gy = sy(t)
        parts.append(
            f'<line x1="{plot_x - 8:.1f}" y1="{gy:.1f}" x2="{plot_x:.1f}" '
            f'y2="{gy:.1f}" stroke="{ink}" stroke-width="1.8"/>'
        )
        parts.append(
            f'<text x="{plot_x - 18:.1f}" y="{gy + 7:.1f}" font-size="21" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="end">{t:.0%}</text>'
        )

    # --- axis titles ---------------------------------------------
    parts.append(
        f'<text x="{plot_x + plot_w / 2:.1f}" y="{ax_bottom + 84:.1f}" '
        f'font-size="24" fill="{ink}" text-anchor="middle">'
        f'Recall — share of fraud caught → better</text>'
    )
    ytitle_x = 66
    ytitle_y = plot_y + plot_h / 2
    parts.append(
        f'<text x="{ytitle_x:.1f}" y="{ytitle_y:.1f}" font-size="24" '
        f'fill="{ink}" text-anchor="middle" '
        f'transform="rotate(-90 {ytitle_x:.1f} {ytitle_y:.1f})">'
        f'Precision — share of flags that are fraud → better</text>'
    )

    # --- the two model curves ------------------------------------
    # Draw a soft white under-stroke first so the coloured curve stays crisp
    # where it crosses a gridline or the other curve; then the coloured curve.
    # Order matters: draw the weaker (orange) curve first so the strong (blue)
    # hero curve sits on top.
    def _curve_path(pts: List[Tuple[float, float]]) -> str:
        """Return the SVG ``d`` for a polyline through mapped ``pts``."""
        return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)

    for label in ("Logistic baseline", "Gradient-boosted"):
        st = style[label]
        pts = [(sx(r), sy(p)) for r, p in per_model[label]]
        d_curve = _curve_path(pts)
        tip = f"{label}: average precision {ap[label]:.2f}"
        parts.append(
            f'<g class="curve" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}">'
        )
        parts.append(f"<title>{xml_escape(tip)}</title>")
        # White under-stroke (halo-free crispness where curves cross).
        parts.append(
            f'<path d="{d_curve}" fill="none" stroke="#FFFFFF" '
            f'stroke-width="12" stroke-linecap="round" '
            f'stroke-linejoin="round"/>'
        )
        dash_attr = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
        parts.append(
            f'<path class="pr-line-{st["slug"]}" d="{d_curve}" fill="none" '
            f'stroke="{st["col"]}" '
            f'stroke-width="6"{dash_attr} stroke-linecap="round" '
            f'stroke-linejoin="round"/>'
        )
        parts.append("</g>")

    # --- shipped (max-F1) operating-point markers ----------------
    for rec in bundle["points"]:
        label = rec["model"]
        st = style[label]
        cx, cy = sx(float(rec["recall"])), sy(float(rec["precision"]))
        tip = (
            f'{label} — shipped (max-F1) operating point: recall '
            f'{rec["recall"]:.0%}, precision {rec["precision"]:.0%}, '
            f'F1 {rec["f1"]:.2f}'
        )
        parts.append(
            f'<g class="op" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}">'
        )
        parts.append(f"<title>{xml_escape(tip)}</title>")
        parts.append(
            f'<circle class="halo" cx="{cx:.1f}" cy="{cy:.1f}" r="26" '
            f'fill="{ink}" fill-opacity="0.08"/>'
        )
        # A distinct glyph per model: circle for the strong model, square for
        # the baseline — so the shipped points differ by shape, not hue alone.
        if st["marker"] == "circle":
            parts.append(
                f'<circle class="pr-mark-{st["slug"]}" cx="{cx:.1f}" cy="{cy:.1f}" r="13" '
                f'fill="{st["col"]}" stroke="#FFFFFF" stroke-width="3"/>'
            )
        else:
            s = 22.0
            parts.append(
                f'<rect class="pr-mark-{st["slug"]}" x="{cx - s / 2:.1f}" y="{cy - s / 2:.1f}" '
                f'width="{s:.1f}" height="{s:.1f}" rx="3" '
                f'fill="{st["col"]}" stroke="#FFFFFF" stroke-width="3"/>'
            )
        parts.append("</g>")

    # --- inline direct labels (curve + AP), separated by shape ----
    # A small legend key sits inside the plot, low-left where both curves have
    # already dropped away. Each row shows the curve's own dash + end glyph and
    # its average precision, so the reader never round-trips to a colour key.
    key_x = sx(0.30)
    key_y = sy(0.42)
    row_h = 46.0
    for i, label in enumerate(("Gradient-boosted", "Logistic baseline")):
        st = style[label]
        ry = key_y + i * row_h
        # Sample line showing hue + dash.
        dash_attr = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
        parts.append(
            f'<line class="pr-line-{st["slug"]}" x1="{key_x:.1f}" y1="{ry:.1f}" '
            f'x2="{key_x + 58:.1f}" '
            f'y2="{ry:.1f}" stroke="{st["col"]}" stroke-width="6"'
            f'{dash_attr} stroke-linecap="round"/>'
        )
        # End glyph matching the operating-point marker shape.
        gx = key_x + 58
        if st["marker"] == "circle":
            parts.append(
                f'<circle class="pr-mark-{st["slug"]}" cx="{gx:.1f}" cy="{ry:.1f}" r="9" '
                f'fill="{st["col"]}" stroke="#FFFFFF" stroke-width="2.5"/>'
            )
        else:
            s = 16.0
            parts.append(
                f'<rect class="pr-mark-{st["slug"]}" x="{gx - s / 2:.1f}" y="{ry - s / 2:.1f}" '
                f'width="{s:.1f}" height="{s:.1f}" rx="2.5" '
                f'fill="{st["col"]}" stroke="#FFFFFF" stroke-width="2.5"/>'
            )
        parts.append(
            f'<text x="{key_x + 84:.1f}" y="{ry + 8:.1f}" font-size="23" '
            f'fill="{ink}"><tspan font-weight="600">{xml_escape(label)}</tspan>'
            f'  ·  AP {ap[label]:.2f}</text>'
        )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the precision-recall-curve SVG to the canonical path (or --out)."""
    render_cli(
        __file__, "prcurve", build_svg,
        description="Render the precision-recall curve SVG (with average "
        "precision, no-skill baseline and iso-F1 contours).",
    )


if __name__ == "__main__":
    main()

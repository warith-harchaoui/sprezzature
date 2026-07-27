#!/usr/bin/env python3
"""
make_calibration — a reliability / calibration curve as hand-authored SVG.

The **calibration curve** (reliability diagram) answers the question
accuracy and the area under the receiver-operating-characteristic curve
(ROC-AUC) cannot: *when my model says 70 %, does it actually happen 70 %
of the time?* The classifier's predicted probability is bucketed into
bins; for each bin the mean predicted probability (x) is plotted against
the observed frequency of positives (y), then read against the 45-degree
line where prediction equals reality. A perfectly-calibrated model
leaves its bin points flat on the diagonal.

This figure deliberately shows the most common failure mode: an
**overconfident** classifier (a boosted-tree churn model). Its
reliability curve sags **below** the diagonal — for every predicted
probability the observed rate of positives is lower, i.e. the model's
confident "90 %" outcomes only happen about 78 % of the time. The gap
between the curve and the diagonal is the miscalibration the plot exists
to expose, summarised as an Expected Calibration Error (ECE) in the
subtitle.

This generator builds the SVG **by hand** — no matplotlib / seaborn /
plotly, no Vega — so the tolerance ribbon, the 45-degree reference line,
the per-bin gap stems, the reliability points sized by bin count, the
confidence histogram below, and the in-plot annotations are all under
our control and can carry the house interactivity (per-mark tooltips, a
fullscreen button) that a rasterised Vega spec cannot. It matches the
sprezzature-* house style: Roboto, the Apple-ish palette, rounded corners, ink
``#1D1D1F``, secondary ``#6E6E73``, white background, bright white
keylines (never dark rings). Illustrative data.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/calibration.svg``.

Usage
-----
::

    python make_calibration.py             # writes next to the skill
    python make_calibration.py --out /tmp/calibration.svg
    python make_calibration.py --mode static   # no fullscreen button

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# House-style tokens + the shared SVG primitives live alongside in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _interactive import fullscreen_control  # noqa: E402
from _render import render_cli  # noqa: E402
from _style import leveled_colors, load_palette, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402


def make_data(
    n: int = 4000,
    n_bins: int = 10,
    seed: int = 11,
) -> Tuple[List[Dict[str, float]], float]:
    """Simulate an overconfident classifier and bin it into a reliability curve.

    The scenario: a **customer-churn** model (a gradient-boosted tree)
    outputs a probability of churn for each of ``n`` customers. The true
    per-customer churn probability is a well-behaved latent quantity, but
    the trained model reports probabilities that are pushed toward the
    extremes — the textbook *overconfidence* of boosted trees. We recover
    the ground truth by drawing each customer's actual churn outcome from
    their true probability, then binning the *reported* probabilities and
    measuring the observed positive rate inside each bin.

    For each of ``n_bins`` equal-width probability bins we compute:

    * **predicted** — the mean reported probability of the bin
      (the x-coordinate);
    * **observed** — the fraction of customers in the bin who actually
      churned (the y-coordinate);
    * **count** — how many predictions landed in the bin (drives the
      point size and the confidence histogram below the plot).

    The Expected Calibration Error (ECE) — the count-weighted mean
    absolute gap between ``predicted`` and ``observed`` across bins — is
    returned alongside so the subtitle can state the headline number.

    Parameters
    ----------
    n : int, optional
        Number of customers (predictions). Default 4000.
    n_bins : int, optional
        Number of equal-width probability bins in ``[0, 1]``. Default 10.
    seed : int, optional
        NumPy random seed for reproducibility. Default 11.

    Returns
    -------
    tuple of (list of dict, float)
        ``(bins, ece)`` where ``bins`` is one record per populated bin,
        ``{"predicted", "observed", "count", "gap", "over"}``, and
        ``ece`` is the Expected Calibration Error in probability units.
    """
    rng = np.random.default_rng(seed)

    # Latent, well-calibrated "true" churn probability per customer:
    # a Beta(2, 3) spread that leans toward lower churn but keeps mass
    # across the whole [0, 1] range so every bin is populated.
    p_true = rng.beta(2.0, 3.0, size=n)

    # The model's REPORTED probability is overconfident: push each true
    # probability away from 0.5 toward the extremes with a logit-gain
    # (>1 sharpens), the classic miscalibration of boosted trees. Small
    # noise keeps the scatter realistic.
    gain = 1.9
    logit = np.log(p_true / (1.0 - p_true))
    logit_noisy = gain * logit + rng.normal(0.0, 0.35, size=n)
    p_pred = 1.0 / (1.0 + np.exp(-logit_noisy))

    # Ground-truth outcomes are drawn from the TRUE probability, not the
    # reported one — that mismatch is exactly what the plot reveals.
    y = (rng.random(n) < p_true).astype(float)

    # Equal-width binning of the reported probabilities in [0, 1].
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(p_pred, edges[1:-1]), 0, n_bins - 1)

    bins: List[Dict[str, float]] = []
    ece_num = 0.0
    for b in range(n_bins):
        mask = idx == b
        count = int(mask.sum())
        if count == 0:
            continue
        predicted = float(p_pred[mask].mean())
        observed = float(y[mask].mean())
        gap = observed - predicted
        ece_num += count * abs(gap)
        bins.append(
            {
                "predicted": round(predicted, 4),
                "observed": round(observed, 4),
                "count": count,
                "gap": round(gap, 4),
                # "over" = model claimed more than reality delivered.
                "over": bool(gap < 0),
            }
        )

    ece = ece_num / n
    return bins, round(ece, 3)


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full calibration-curve SVG string.

    Two stacked panels share the same x-axis (predicted probability).

    *Top* — the reliability diagram, drawn bottom to top:

    1. a faint grey **tolerance ribbon** around the diagonal — "inside
       here counts as calibrated";
    2. the dashed **45-degree "perfect calibration" line**, captioned on
       the diagonal;
    3. per-bin **gap stems** dropping from each point to the diagonal,
       coloured by direction (overconfident Red vs underconfident Blue)
       so the sag reads even in greyscale;
    4. a connecting **calibration curve** (Purple) through the points;
    5. the **reliability points**, sized by how many predictions landed
       in the bin, each a focusable ``<g>`` with a native tooltip;
    6. direct on-plot **text annotations** for the over/under sides and a
       size legend, so the Red/Blue split never needs a colour-only
       round-trip.

    *Bottom* — a slim **confidence histogram**: the count of predictions
    per bin, so the reader sees the curve is trustworthy where the model
    is busy and noisy where it is sparse.

    Colour never carries meaning alone: the over/under sides are labelled
    in words and separated by position (below vs above the diagonal), and
    the Blue↔Red pair survives deuteranopia and greyscale, where red↔green
    collapses.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level passed to :func:`_style.load_palette`
        (``"universal"`` — the default, colour-vision-safe standard — plus
        ``"high-contrast"``, ``"monochrome"``, ``"deuteranopia"``,
        ``"protanopia"`` and ``"tritanopia"``). Wired through the
        ``--accessibility`` CLI flag by :func:`_render.render_cli`.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    palette: Dict[str, str] = load_palette(accessibility)
    over = palette.get("Red", "#FF3B30")      # model over-states the probability
    under = palette.get("Blue", "#007AFF")    # model under-states the probability
    curve = palette.get("Purple", "#AF52DE")  # the reliability curve itself
    hist = palette.get("Teal", "#5AC8FA")     # the confidence histogram
    ink = "#1D1D1F"
    secondary = "#6E6E73"

    bins, ece = make_data()

    # --- canvas geometry -----------------------------------------
    # The reliability square is the hero mark, so it gets a generous side.
    # The confidence histogram shares the exact left/right plotting edges
    # so the two panels align cleanly. A roomy gap separates them.
    width = 980
    m_left = 128
    m_right = 56
    m_top = 226
    sq = width - m_left - m_right          # the top view is a square
    plot_x = m_left
    plot_y = m_top
    plot_w = sq
    plot_h = sq

    hist_h = 176
    hist_gap = 132                          # room for the x-axis + size legend
    hist_y = plot_y + plot_h + hist_gap
    # Canvas height: fit the histogram baseline, its x-axis labels, and
    # the x-title below it with a comfortable bottom margin.
    height = hist_y + hist_h + 120

    # Both axes of the top view are probabilities, so the domain is the
    # unit square. A square view makes the 45-degree line a true diagonal.
    ticks = [0.0, 0.25, 0.5, 0.75, 1.0]

    def sx(v: float) -> float:
        """Map a probability in [0, 1] to an x pixel coordinate."""
        return plot_x + v * plot_w

    def sy(v: float) -> float:
        """Map a probability in [0, 1] to a y pixel coordinate (y-down)."""
        return plot_y + (1.0 - v) * plot_h

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    parts.append(svg_open(width, height, "cal-title", "cal-desc"))
    parts.append(
        '<title id="cal-title">The churn model is overconfident: its '
        'high-risk calls miss the diagonal</title>'
    )
    parts.append(
        f'<desc id="cal-desc">Reliability diagram (calibration curve) for an '
        f'overconfident customer-churn classifier. The horizontal axis is the '
        f'model’s predicted probability of churn; the vertical axis is the '
        f'observed churn rate in each bin. A dashed 45-degree line marks '
        f'perfect calibration, ringed by a faint grey tolerance band. The '
        f'reliability curve sags below the diagonal at the confident end, so '
        f'the model’s high-probability calls happen less often than it claims '
        f'(overconfident, labelled in red on the right); Expected Calibration '
        f'Error {ece:.0%}. At the timid end it floats above the diagonal, so '
        f'it under-states churn (underconfident, labelled in blue on the '
        f'left). Each point is sized by how many predictions fell in the bin, '
        f'and a histogram below shows where the model spends its predictions. '
        f'Illustrative data.</desc>'
    )

    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule below lives inside a media query). Under
    # prefers-contrast the four categorical roles deepen together to their
    # high-contrast hues: the overconfident side (red) on its gap stems, points
    # and annotation, the underconfident side (blue) likewise, the reliability
    # curve (purple), and the confidence histogram (teal). Stems keep their
    # stroke role while points/annotations keep their fill role, so the white
    # keyline around each point survives. forced-colors is left to the browser
    # default: the over/under split is already carried by position (below vs
    # above the diagonal) and worded labels, and the ~4-colour system palette
    # could not hold four distinct reference hues.
    hc = leveled_colors({"over": over, "under": under, "curve": curve, "hist": hist},
                        "high-contrast")
    contrast_rows = (
        f".cal-stem-over{{stroke:{hc['over']};}}"
        f".cal-stem-under{{stroke:{hc['under']};}}"
        f".cal-curve{{stroke:{hc['curve']};}}"
        f".cal-mark-over{{fill:{hc['over']};}}"
        f".cal-mark-under{{fill:{hc['under']};}}"
        f".cal-hist{{fill:{hc['hist']};}}"
    )
    adaptive = "@media (prefers-contrast: more){\n  " + contrast_rows + "\n}"
    # Static figure: hover / focus halo only, no motion to guard.
    parts.append(
        "<style>"
        ".pt{cursor:pointer}"
        ".pt .halo{opacity:0}"
        ".pt:hover .halo,.pt:focus .halo{opacity:1}"
        ".pt:focus{outline:none}"
        ".bar{cursor:pointer}"
        + adaptive
        # Light gridlines are strokes the ink map misses; darken them for a dark
        # ground. The grey diagonal / reference band reads at medium grey either
        # way, and the white point halos stay light keylines.
        + os_dark_style(extra='[stroke="#EEEEEE"]{stroke:#2A2A2C;}')
        + "</style>"
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="82" font-size="36" font-weight="700" '
        f'fill="{ink}">The churn model is overconfident:</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="126" font-size="36" font-weight="700" '
        f'fill="{ink}">its high-risk calls miss the diagonal</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="166" font-size="22" fill="{secondary}">'
        f'Reliability diagram: confident “90%” churn calls happen far less</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="194" font-size="22" fill="{secondary}">'
        f'Expected Calibration Error {ece:.0%} · illustrative data</text>'
    )

    # --- tolerance ribbon (faint grey band around the diagonal) --
    # A constant-width band y = x ± band, clamped to the unit square. Two
    # offset diagonals filled between: the "inside here counts" zone.
    band = 0.05
    # Build the ribbon polygon by walking the upper offset out and the
    # lower offset back, each clamped to [0, 1].
    upper = [(x, min(1.0, x + band)) for x in (0.0, 1.0)]
    lower = [(x, max(0.0, x - band)) for x in (1.0, 0.0)]
    ribbon_pts = " ".join(
        f"{sx(x):.1f},{sy(y):.1f}" for x, y in upper + lower
    )
    parts.append(
        f'<polygon points="{ribbon_pts}" fill="#8E8E93" fill-opacity="0.12"/>'
    )

    # --- gridlines (very light) ----------------------------------
    for t in ticks:
        gx = sx(t)
        gy = sy(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{plot_y:.1f}" x2="{gx:.1f}" '
            f'y2="{plot_y + plot_h:.1f}" stroke="#EEEEEE" stroke-width="1.4"/>'
        )
        parts.append(
            f'<line x1="{plot_x:.1f}" y1="{gy:.1f}" x2="{plot_x + plot_w:.1f}" '
            f'y2="{gy:.1f}" stroke="#EEEEEE" stroke-width="1.4"/>'
        )

    # --- 45-degree "perfect calibration" line + caption ----------
    parts.append(
        f'<line x1="{sx(0.0):.1f}" y1="{sy(0.0):.1f}" x2="{sx(1.0):.1f}" '
        f'y2="{sy(1.0):.1f}" stroke="#8E8E93" stroke-width="1.6" '
        f'stroke-dasharray="6 4"/>'
    )
    # Caption rides ON the diagonal, rotated -45 degrees so it runs
    # parallel to the line; a small offset lifts it just clear of the
    # dashes. It sits in the upper-left stretch, away from the points.
    cap_x, cap_y = sx(0.34), sy(0.34)
    parts.append(
        f'<text x="{cap_x:.1f}" y="{cap_y - 12:.1f}" font-size="20" '
        f'fill="{secondary}" text-anchor="middle" '
        f'transform="rotate(-45 {cap_x:.1f} {cap_y - 12:.1f})">'
        f'Perfect calibration</text>'
    )

    # --- top-view axes (L-shaped, ink) with ticks + labels -------
    ax_bottom = plot_y + plot_h
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{ax_bottom:.1f}" '
        f'x2="{plot_x + plot_w:.1f}" y2="{ax_bottom:.1f}" '
        f'stroke="{ink}" stroke-width="1.6"/>'
    )
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{plot_y:.1f}" x2="{plot_x:.1f}" '
        f'y2="{ax_bottom:.1f}" stroke="{ink}" stroke-width="1.6"/>'
    )
    for t in ticks:
        gx = sx(t)
        gy = sy(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{ax_bottom:.1f}" x2="{gx:.1f}" '
            f'y2="{ax_bottom + 7:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="{ax_bottom + 32:.1f}" font-size="19" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">{t:.0%}</text>'
        )
        parts.append(
            f'<line x1="{plot_x - 7:.1f}" y1="{gy:.1f}" x2="{plot_x:.1f}" '
            f'y2="{gy:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{plot_x - 16:.1f}" y="{gy + 7:.1f}" font-size="19" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="end">{t:.0%}</text>'
        )
    # y-axis title (the top view) — the x-axis title lives under the
    # histogram, which shares the same predicted-probability axis.
    ytitle_x = 52
    ytitle_y = plot_y + plot_h / 2
    parts.append(
        f'<text x="{ytitle_x:.1f}" y="{ytitle_y:.1f}" font-size="22" '
        f'fill="{ink}" text-anchor="middle" '
        f'transform="rotate(-90 {ytitle_x:.1f} {ytitle_y:.1f})">'
        f'Observed churn rate</text>'
    )

    # --- per-bin gap stems (point down/up to the diagonal) -------
    # A thin vertical stem from each bin point to the diagonal at the same
    # x, coloured by whether the model over- or under-states. Drawn before
    # the curve and points so they read as a light underlay.
    for rec in bins:
        px_ = sx(rec["predicted"])
        y_obs = sy(rec["observed"])
        y_diag = sy(rec["predicted"])
        col = over if rec["over"] else under
        stem_cls = "cal-stem-over" if rec["over"] else "cal-stem-under"
        parts.append(
            f'<line class="{stem_cls}" x1="{px_:.1f}" y1="{y_obs:.1f}" '
            f'x2="{px_:.1f}" '
            f'y2="{y_diag:.1f}" stroke="{col}" stroke-width="2.4" '
            f'stroke-opacity="0.55"/>'
        )

    # --- calibration curve (Purple line through the points) ------
    curve_pts = [
        (sx(r["predicted"]), sy(r["observed"])) for r in bins
    ]
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in curve_pts)
    parts.append(
        f'<path class="cal-curve" d="{d}" fill="none" stroke="{curve}" '
        f'stroke-width="3" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'stroke-opacity="0.9"/>'
    )

    # --- reliability points (sized by bin count) -----------------
    # Radius scales with the square root of the count so *area* is
    # proportional to how many predictions fell in the bin. Each point is
    # a focusable group with a native tooltip and a hover / focus halo. A
    # white keyline keeps the dot crisp on the curve — bright, never dark.
    counts = [r["count"] for r in bins]
    c_max = max(counts) if counts else 1
    r_min, r_max = 9.0, 26.0

    def radius(count: int) -> float:
        """Return the marker radius for a bin ``count`` (area-proportional)."""
        return r_min + (r_max - r_min) * (count / c_max) ** 0.5

    for rec in bins:
        cx = sx(rec["predicted"])
        cy = sy(rec["observed"])
        rr = radius(int(rec["count"]))
        col = over if rec["over"] else under
        side = "over-states" if rec["over"] else "under-states"
        tip = (
            f'Predicted {rec["predicted"]:.0%}, observed {rec["observed"]:.0%} '
            f'(gap {rec["gap"]:+.0%}, {side}); {int(rec["count"])} predictions'
        )
        parts.append(
            f'<g class="pt" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}">'
        )
        parts.append(f"<title>{xml_escape(tip)}</title>")
        parts.append(
            f'<circle class="halo" cx="{cx:.1f}" cy="{cy:.1f}" '
            f'r="{rr + 8:.1f}" fill="{ink}" fill-opacity="0.08"/>'
        )
        mark_cls = "cal-mark-over" if rec["over"] else "cal-mark-under"
        parts.append(
            f'<circle class="{mark_cls}" cx="{cx:.1f}" cy="{cy:.1f}" '
            f'r="{rr:.1f}" fill="{col}" '
            f'fill-opacity="0.95" stroke="#FFFFFF" stroke-width="1.4"/>'
        )
        parts.append("</g>")

    # --- direct on-plot annotations (over / under sides) ---------
    # The curve sags BELOW the diagonal at the confident end
    # (overconfident, Red) and floats ABOVE it at the timid end
    # (underconfident, Blue). Labels sit in the empty triangle on each
    # side of the diagonal so they never crowd the marks, side-aware.
    over_x, over_y = sx(0.80), sy(0.50)
    for i, line in enumerate(
        ["Overconfident:", "says more churn", "than happens"]
    ):
        parts.append(
            f'<text class="cal-mark-over" x="{over_x:.1f}" '
            f'y="{over_y + i * 24:.1f}" font-size="20" '
            f'font-weight="600" fill="{over}" text-anchor="middle">'
            f'{line}</text>'
        )
    under_x, under_y = sx(0.17), sy(0.52)
    for i, line in enumerate(
        ["Underconfident:", "says less churn", "than happens"]
    ):
        parts.append(
            f'<text class="cal-mark-under" x="{under_x:.1f}" '
            f'y="{under_y + i * 24:.1f}" font-size="20" '
            f'font-weight="600" fill="{under}" text-anchor="middle">'
            f'{line}</text>'
        )

    # --- confidence histogram (bottom panel) ---------------------
    # How many predictions the model made in each bin. Bars share the
    # top view's x-axis exactly (same sx), so the two panels align.
    h_max = max(counts) if counts else 1
    h_ax_bottom = hist_y + hist_h

    def hy(count: float) -> float:
        """Map a bin count to a y pixel coordinate in the histogram panel."""
        return h_ax_bottom - (count / h_max) * hist_h

    # bar geometry: one bar per bin, centred on its bin midpoint, leaving
    # a small gutter between neighbours.
    n_bins_drawn = len(bins)
    bin_w = plot_w / max(n_bins_drawn, 1)
    gutter = bin_w * 0.18
    for rec in bins:
        # Recover the bin index from the predicted mean's position so each
        # bar sits under the reliability point it explains.
        bx = sx(rec["predicted"]) - (bin_w - gutter) / 2.0
        by = hy(rec["count"])
        bw = bin_w - gutter
        bh = h_ax_bottom - by
        tip = f'{int(rec["count"])} predictions near {rec["predicted"]:.0%}'
        parts.append(
            f'<g class="bar" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}">'
        )
        parts.append(f"<title>{xml_escape(tip)}</title>")
        parts.append(
            f'<rect class="cal-hist" x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" '
            f'height="{bh:.1f}" rx="3" fill="{hist}" fill-opacity="0.85"/>'
        )
        parts.append("</g>")

    # histogram axes: baseline + a couple of count ticks on the left.
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{h_ax_bottom:.1f}" '
        f'x2="{plot_x + plot_w:.1f}" y2="{h_ax_bottom:.1f}" '
        f'stroke="{ink}" stroke-width="1.6"/>'
    )
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{hist_y:.1f}" x2="{plot_x:.1f}" '
        f'y2="{h_ax_bottom:.1f}" stroke="{ink}" stroke-width="1.6"/>'
    )
    # Three count ticks: 0, half, max (rounded to a clean number).
    for frac in (0.0, 0.5, 1.0):
        cval = frac * h_max
        cyt = hy(cval)
        parts.append(
            f'<line x1="{plot_x - 7:.1f}" y1="{cyt:.1f}" x2="{plot_x:.1f}" '
            f'y2="{cyt:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{plot_x - 16:.1f}" y="{cyt + 6:.1f}" font-size="18" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="end">{int(round(cval))}</text>'
        )
    # x-axis ticks + labels under the histogram (shared predicted axis).
    for t in ticks:
        gx = sx(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{h_ax_bottom:.1f}" x2="{gx:.1f}" '
            f'y2="{h_ax_bottom + 7:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="{h_ax_bottom + 32:.1f}" font-size="19" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">{t:.0%}</text>'
        )
    # histogram panel titles.
    parts.append(
        f'<text x="{plot_x + plot_w / 2:.1f}" y="{h_ax_bottom + 74:.1f}" '
        f'font-size="22" fill="{ink}" text-anchor="middle">'
        f'Predicted probability of churn</text>'
    )
    htitle_x = 52
    htitle_y = hist_y + hist_h / 2
    parts.append(
        f'<text x="{htitle_x:.1f}" y="{htitle_y:.1f}" font-size="20" '
        f'fill="{ink}" text-anchor="middle" '
        f'transform="rotate(-90 {htitle_x:.1f} {htitle_y:.1f})">'
        f'Predictions</text>'
    )

    # --- size legend (between the two panels, laid out horizontally) --
    # A small "point size = predictions in bin" key so the area encoding
    # is decodable. Sits in the gap under the reliability square, clear of
    # both panels. Neutral grey circles keep it out of the over/under
    # colour story.
    leg_y = plot_y + plot_h + 60
    leg_x = plot_x
    parts.append(
        f'<text x="{leg_x:.1f}" y="{leg_y + 6:.1f}" font-size="18" '
        f'fill="{secondary}">Point size = predictions in bin:</text>'
    )
    legend_counts = [200, 500, c_max]
    lx: float = leg_x + 320
    for cnt in legend_counts:
        rr = radius(int(cnt))
        parts.append(
            f'<circle cx="{lx + r_max:.1f}" cy="{leg_y:.1f}" r="{rr:.1f}" '
            f'fill="#8E8E93" fill-opacity="0.35" stroke="#8E8E93" '
            f'stroke-width="1.2"/>'
        )
        parts.append(
            f'<text x="{lx + r_max:.1f}" y="{leg_y + r_max + 22:.1f}" '
            f'font-size="16" font-family="Roboto Mono, monospace" '
            f'fill="{secondary}" text-anchor="middle">{int(cnt)}</text>'
        )
        lx += r_max * 2 + 78

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the calibration-curve SVG to the canonical assets path (or --out)."""
    render_cli(
        __file__, "calibration", build_svg,
        description=(
            "Render the house-style calibration curve (reliability diagram) "
            "to SVG."
        ),
    )


if __name__ == "__main__":
    main()

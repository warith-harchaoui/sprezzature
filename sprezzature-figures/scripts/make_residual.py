#!/usr/bin/env python3
"""
make_residual — a residual-vs-fitted diagnostic scatter as hand-authored SVG.

A **residual plot** scatters the residuals of a regression (observed minus
predicted) against the model's fitted values, anchored by a zero reference
line and overlaid with a smoothed trend of the residuals. This is the seaborn
``residplot`` capability — the single diagnostic a modeller reaches for to
ask "is anything left in the residuals?". A well-specified model leaves them
scattered as a shapeless, constant-width band around zero.

This figure deliberately shows the opposite: the fake data comes from a model
fit *linearly* to a relationship that curves, so the residuals bow into a
smile (positive at both ends, negative in the middle) and fan out toward the
right — the two classic tells of a mis-specified mean and non-constant
variance. The smoothed trend line makes the curvature impossible to miss,
which is the whole point of the plot.

This generator builds the SVG by hand (no matplotlib / seaborn / plotly, no
Vega) so the residual scatter, the dashed zero rule, the locally-weighted
(LOESS) smoother, and the sign-coloured points are all under our control. It
matches the front-* house style: Roboto, the Apple-ish palette, rounded
corners, ink ``#1D1D1F``, secondary ``#6E6E73``, white background, white
keylines (never black rings). Points are coloured by the *sign* of the
residual — Blue above the zero rule (model under-predicts), Orange below it
(model over-predicts) — a blue↔orange split that survives deuteranopia and
greyscale, reinforced by position above/below zero and two in-plot labels, so
the sign never rides on colour alone.

The scenario is a **house-price regression**: an analyst predicts sale price
from floor area with a straight-line least-squares fit, but the true
relationship curves (price accelerates for larger homes) and the spread
widens with size — the textbook mis-specification a residual plot exposes.
Illustrative data.

The figure is **static** — the diagnostic is a single still. Each residual
point carries a native ``<title>`` tooltip and a :hover / :focus enlargement;
no JavaScript beyond the fullscreen control.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/residual.svg``.

Usage
-----
::

    python make_residual.py             # writes next to the skill
    python make_residual.py --out /tmp/residual.svg

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

# House-style palette + the shared SVG primitives live alongside in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402


def make_data(n: int = 160, seed: int = 11) -> List[Dict[str, float]]:
    """Sample a plausible *house-price* regression and return its residuals.

    The scenario: an analyst predicts a home's sale price from its floor area
    with a **straight-line** ordinary-least-squares fit. The true relationship
    curves (price accelerates for larger homes) and the spread of prices
    widens with size. Fitting a line to that curve is the textbook
    mis-specification a residual plot is built to expose, so the returned
    residuals carry both a U-shaped mean and a right-opening fan of variance.

    The regression itself is done here in closed form (a degree-1
    least-squares fit via :func:`numpy.polyfit`) so the figure only has to
    carry the two diagnostic coordinates — fitted value and residual — per
    home.

    Parameters
    ----------
    n : int, optional
        Number of homes (points). Default 160.
    seed : int, optional
        NumPy random seed for reproducibility. Default 11.

    Returns
    -------
    list of dict
        One record per home, ``{"fitted": <predicted price, k$>, "residual":
        <k$>}``, rounded so the values read cleanly in a tooltip.
    """
    rng = np.random.default_rng(seed)

    # Floor area in hundreds of square feet, spread across a realistic 8-32
    # (i.e. 800-3200 sq ft) range of homes on the market.
    area = rng.uniform(8.0, 32.0, size=n)

    # TRUE price (thousands of dollars): a gently convex function of area — the
    # marginal value of space rises for bigger homes — plus heteroscedastic
    # noise whose spread grows with area (pricier homes vary more). This is the
    # signal a straight line cannot capture.
    true_price = 40.0 + 6.0 * area + 0.35 * area**2
    noise = rng.normal(0.0, 5.0 + 1.0 * area, size=n)
    price = true_price + noise

    # The analyst's (mis-specified) model: a single straight line.
    slope, intercept = np.polyfit(area, price, deg=1)
    fitted = intercept + slope * area
    residual = price - fitted

    return [
        {"fitted": round(float(f), 1), "residual": round(float(r), 1)}
        for f, r in zip(fitted, residual)
    ]


def loess(
    xs: List[float],
    ys: List[float],
    grid: List[float],
    frac: float = 0.6,
) -> List[float]:
    """Locally-weighted (LOESS) smoother of ``ys`` on ``xs``, sampled on ``grid``.

    For each grid point it fits a tricube-weighted degree-1 local regression
    using the nearest ``frac`` of the data, giving the smooth structural curve
    that turns a vague residual cloud into an unmistakable U. This is the same
    smoother Vega's ``loess`` transform applies, hand-rolled here so the SVG
    carries only the resulting polyline.

    Parameters
    ----------
    xs, ys : list of float
        The observed ``(x, y)`` samples (fitted value, residual).
    grid : list of float
        The x positions at which to evaluate the smoother, left-to-right.
    frac : float, optional
        Span — the fraction of points in each local neighbourhood. Default
        0.6, matching the reference figure's bandwidth.

    Returns
    -------
    list of float
        The smoothed y value at each ``grid`` point.
    """
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    n = len(x)
    k = max(2, int(round(frac * n)))     # neighbourhood size
    out: List[float] = []
    for g in grid:
        # Distances to g, take the k nearest, tricube-weight by scaled distance.
        dist = np.abs(x - g)
        order = np.argsort(dist)[:k]
        xd, yd = x[order], y[order]
        dmax = dist[order].max()
        if dmax <= 0.0:
            out.append(float(yd.mean()))
            continue
        w = (1.0 - (np.abs(xd - g) / dmax) ** 3) ** 3
        w = np.clip(w, 0.0, None)
        # Weighted degree-1 least squares: solve [1, x] b = y with weights.
        sw = w.sum()
        mx = (w * xd).sum() / sw
        my = (w * yd).sum() / sw
        sxx = (w * (xd - mx) ** 2).sum()
        sxy = (w * (xd - mx) * (yd - my)).sum()
        b = sxy / sxx if sxx > 0 else 0.0
        a = my - b * mx
        out.append(float(a + b * g))
    return out


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full residual-plot SVG string.

    Draws, bottom to top: the light gridlines and axes, a dashed grey zero
    rule, the residual scatter (points coloured by residual sign), the LOESS
    smoother, and the two in-plot sign labels.

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
    palette: Dict[str, str] = load_palette(accessibility)
    over = palette.get("Blue", "#007AFF")     # residual > 0: model under-predicts
    under = palette.get("Orange", "#FF9500")  # residual < 0: model over-predicts
    trend = palette.get("Red", "#FF3B30")     # the LOESS structure line
    ink = "#1D1D1F"
    secondary = "#6E6E73"
    grid_col = "#EEEEEE"
    rule_col = "#8E8E93"

    data = make_data()
    fitted = [float(d["fitted"]) for d in data]
    residual = [float(d["residual"]) for d in data]

    # --- axis windows --------------------------------------------
    # x: a little padding either side of the fitted range so nothing clips.
    x_min, x_max = 70.0, 570.0
    x_ticks = [100, 200, 300, 400, 500]
    # y: symmetric-ish window that contains every point with headroom and keeps
    # the zero rule near mid-height so the smile reads at a glance.
    y_min, y_max = -90.0, 110.0
    y_ticks = [-80, -40, 0, 40, 80]

    # --- canvas geometry -----------------------------------------
    width = 1000
    height = 780
    m_left = 118
    m_right = 44
    m_top = 176
    m_bottom = 92
    plot_x = m_left
    plot_y = m_top
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    def sx(v: float) -> float:
        """Map fitted price (thousand $) to an x pixel coordinate."""
        return plot_x + (v - x_min) / (x_max - x_min) * plot_w

    def sy(v: float) -> float:
        """Map residual (thousand $) to a y pixel coordinate (y-down)."""
        return plot_y + (y_max - v) / (y_max - y_min) * plot_h

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    parts.append(svg_open(width, height, "rs-title", "rs-desc"))
    parts.append(
        '<title id="rs-title">The residuals still curve — a straight line '
        'under-fits home prices</title>'
    )
    parts.append(
        '<desc id="rs-desc">Residual plot for a straight-line fit of home '
        'sale price against floor area. Residuals (actual minus predicted '
        'price, thousands of dollars) are scattered on the vertical axis '
        'against the model\'s fitted price on the horizontal axis, with a '
        'dashed zero reference line. A red locally-weighted smoother bows '
        'into a U — residuals are positive at both ends and negative in the '
        'middle — and the spread of points widens toward the right. The '
        'curvature and the fanning show the linear model mis-specifies both '
        'the mean and the variance. Points above zero (model under-predicts) '
        'are blue; points below zero (model over-predicts) are orange. '
        'Illustrative data.</desc>'
    )

    # Static figure: hover / focus enlargement only, no motion to guard.
    # OS-adaptive overrides are appended (additive; every rule lives inside an
    # @media block so the default render is byte-for-byte unchanged). The two
    # sign clusters carry ``.rs-over`` / ``.rs-under`` classes as hooks: under
    # prefers-contrast they deepen to their high-contrast blue/orange so the
    # sign split stays crisp. forced-colors is left to the browser default —
    # the split is colour-encoded (two clouds), so the ~4-colour system palette
    # cannot preserve it; the direct sign labels carry the identity anyway.
    contrast_block = os_adaptive_style(
        {".rs-over": over, ".rs-under": under},
        role="fill",
    )
    parts.append(
        "<style>"
        ".pt{cursor:pointer}"
        ".pt .halo{opacity:0}"
        ".pt:hover .halo,.pt:focus .halo{opacity:1}"
        ".pt:focus{outline:none}"
        + "\n" + contrast_block + "\n"
        + os_dark_style(extra='[stroke="#EEEEEE"]{stroke:#2C2C2E;}') + "\n"
        "</style>"
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="66" font-size="28" font-weight="700" '
        f'fill="{ink}">The residuals still curve — a straight line '
        f'under-fits home prices</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="102" font-size="19" fill="{secondary}">'
        f'Residuals of a linear price-vs-size fit; the red smoother bows into '
        f'a U and fans out on the right</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="128" font-size="19" fill="{secondary}">'
        f'Illustrative data</text>'
    )

    # --- gridlines (very light) ----------------------------------
    for t in x_ticks:
        gx = sx(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{plot_y:.1f}" x2="{gx:.1f}" '
            f'y2="{plot_y + plot_h:.1f}" stroke="{grid_col}" stroke-width="1.4"/>'
        )
    for t in y_ticks:
        gy = sy(t)
        parts.append(
            f'<line x1="{plot_x:.1f}" y1="{gy:.1f}" x2="{plot_x + plot_w:.1f}" '
            f'y2="{gy:.1f}" stroke="{grid_col}" stroke-width="1.4"/>'
        )

    # --- axes (L-shaped, ink) ------------------------------------
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
    for t in x_ticks:
        gx = sx(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{ax_bottom:.1f}" x2="{gx:.1f}" '
            f'y2="{ax_bottom + 6:.1f}" stroke="{ink}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="{ax_bottom + 28:.1f}" font-size="17" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">{t}</text>'
        )
    for t in y_ticks:
        gy = sy(t)
        parts.append(
            f'<line x1="{plot_x - 6:.1f}" y1="{gy:.1f}" x2="{plot_x:.1f}" '
            f'y2="{gy:.1f}" stroke="{ink}" stroke-width="1.4"/>'
        )
        label = f"+{t}" if t > 0 else f"{t}"
        parts.append(
            f'<text x="{plot_x - 14:.1f}" y="{gy + 6:.1f}" font-size="17" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="end">{label}</text>'
        )

    # --- axis titles ---------------------------------------------
    parts.append(
        f'<text x="{plot_x + plot_w / 2:.1f}" y="{ax_bottom + 62:.1f}" '
        f'font-size="19" fill="{ink}" text-anchor="middle">'
        f'Fitted sale price (thousand $)</text>'
    )
    ytitle_x = 42
    ytitle_y = plot_y + plot_h / 2
    parts.append(
        f'<text x="{ytitle_x:.1f}" y="{ytitle_y:.1f}" font-size="19" '
        f'fill="{ink}" text-anchor="middle" '
        f'transform="rotate(-90 {ytitle_x:.1f} {ytitle_y:.1f})">'
        f'Residual  =  actual − predicted (thousand $)</text>'
    )

    # --- zero reference rule (dashed grey) -----------------------
    zero_y = sy(0.0)
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{zero_y:.1f}" '
        f'x2="{plot_x + plot_w:.1f}" y2="{zero_y:.1f}" stroke="{rule_col}" '
        f'stroke-width="1.5" stroke-dasharray="6 4"/>'
    )

    # --- residual scatter ----------------------------------------
    # Points coloured by the sign of the residual; a white keyline lifts each
    # off its neighbours and the zero rule — a bright keyline, never a dark
    # ring. Blue sits above zero (under-prediction), orange below.
    r_dot = 7.5
    for d in data:
        f = float(d["fitted"])
        r = float(d["residual"])
        if f < x_min or f > x_max or r < y_min or r > y_max:
            continue  # clip any out-of-window straggler
        cx, cy = sx(f), sy(r)
        col = over if r >= 0 else under
        pt_class = "rs-over" if r >= 0 else "rs-under"
        sign = "+" if r >= 0 else ""
        tip = f"Fitted {int(round(f))} k$, residual {sign}{int(round(r))} k$"
        parts.append(
            f'<g class="pt" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}">'
        )
        parts.append(f"<title>{xml_escape(tip)}</title>")
        parts.append(
            f'<circle class="halo" cx="{cx:.1f}" cy="{cy:.1f}" r="16" '
            f'fill="{ink}" fill-opacity="0.08"/>'
        )
        parts.append(
            f'<circle class="{pt_class}" cx="{cx:.1f}" cy="{cy:.1f}" r="{r_dot:.1f}" '
            f'fill="{col}" fill-opacity="0.62" stroke="#FFFFFF" '
            f'stroke-width="1.1"/>'
        )
        parts.append("</g>")

    # --- LOESS smoother (drawn on top) ---------------------------
    # Sample the smoother on a fine grid across the fitted range, then draw it
    # as a polyline. A soft white under-stroke keeps it crisp through the
    # densest part of the cloud; the Red line rides on top.
    x_lo, x_hi = min(fitted), max(fitted)
    grid = [x_lo + (x_hi - x_lo) * i / 80.0 for i in range(81)]
    smooth = loess(fitted, residual, grid, frac=0.6)
    pts = [(sx(gx), sy(gy)) for gx, gy in zip(grid, smooth)]
    d_attr = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    parts.append(
        f'<path d="{d_attr}" fill="none" stroke="#FFFFFF" stroke-width="8" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<path d="{d_attr}" fill="none" stroke="{trend}" stroke-width="4" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # --- in-plot sign labels -------------------------------------
    # The residual sign is the whole story, so name the two clouds in their own
    # ink on the marks rather than forcing a legend round-trip. Blue label sits
    # above the zero rule, orange below it.
    parts.append(
        f'<text class="rs-over" x="{sx(130.0):.1f}" y="{sy(92.0):.1f}" font-size="18" '
        f'font-weight="700" fill="{over}">Model under-predicts '
        f'(residual &gt; 0)</text>'
    )
    parts.append(
        f'<text class="rs-under" x="{sx(130.0):.1f}" y="{sy(-70.0):.1f}" font-size="18" '
        f'font-weight="700" fill="{under}">Model over-predicts '
        f'(residual &lt; 0)</text>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the residual-plot SVG to the canonical assets path (or --out)."""
    render_cli(
        __file__, "residual", build_svg,
        description="Render the residual plot (residuals vs fitted, zero rule) SVG.",
    )


if __name__ == "__main__":
    main()

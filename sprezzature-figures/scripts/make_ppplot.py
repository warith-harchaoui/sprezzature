#!/usr/bin/env python3
"""
make_ppplot — the probability-probability (P-P) plot as hand-authored SVG.

Generate the **P-P plot** figure in the ``sprezzature-figures`` house style: for
each sorted observation, its *empirical* cumulative-distribution-function
(CDF) probability is plotted against the *theoretical* CDF probability
predicted by a fitted reference distribution, and the whole cloud is read
against the 45-degree line where the two agree. This is the
distribution-diagnostic a modeller reaches for to ask "does my fitted
distribution actually describe the middle of the data?" — the P-P plot is
most sensitive in the centre of the distribution (unlike the Q-Q plot,
which is most sensitive in the tails).

A perfectly-fitting reference distribution leaves the points lying flat
along the diagonal. This figure deliberately shows the opposite: the fake
data are **customer session durations**, which are right-skewed, while the
analyst fits a symmetric **Normal** reference. Because the Normal
over-predicts small probabilities and under-predicts large ones against a
skewed sample, the empirical-vs-theoretical points bow into a smooth S /
arc that pulls clearly off the diagonal — the classic tell that a
symmetric law is the wrong shape for skewed data.

This generator builds the SVG by hand (no matplotlib / seaborn / plotly,
no Vega) so the tolerance band, the 45-degree reference line, the two
point clusters (coloured by which side of the diagonal they fall on, and
labelled directly so the split survives greyscale), and the smooth trend
arc are all under our control. The signed split uses blue (empirical above
the line, the Normal under-states the probability) versus orange (below
the line, the Normal over-states it) — never red-green, so it holds up
under deuteranopia and in greyscale. It matches the sprezzature-* house style:
Roboto, the Apple-ish palette, rounded corners, ink ``#1D1D1F``,
secondary ``#6E6E73``, white background, white keylines.

Each point carries a native ``<title>`` tooltip and a :hover / :focus
enlargement; no JavaScript beyond the shared fullscreen control.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/ppplot.svg``.

Usage
-----
::

    python make_ppplot.py            # writes next to the skill
    python make_ppplot.py --out /tmp/ppplot.svg
    python make_ppplot.py --mode static   # no fullscreen button

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

# House-style palette + shared primitives live alongside in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402


def _normal_cdf(z: np.ndarray) -> np.ndarray:
    """Standard-normal CDF via the error function (no SciPy dependency).

    Parameters
    ----------
    z : numpy.ndarray
        Standardised values.

    Returns
    -------
    numpy.ndarray
        ``P(Z <= z)`` for a standard normal ``Z``.
    """
    # Phi(z) = 0.5 * (1 + erf(z / sqrt(2))); math.erf is applied per element
    # with a small comprehension to keep the dependency surface to stdlib.
    return np.array([0.5 * (1.0 + math.erf(v / math.sqrt(2.0))) for v in z])


def make_data(n: int = 90, seed: int = 7) -> List[Dict[str, float]]:
    """Sample right-skewed session durations and return their P-P coordinates.

    The scenario: an analyst has ``n`` customer web-session durations
    (in minutes) and wants to check whether a **Normal** distribution
    describes them. The true generating process is right-skewed
    (log-normal), so a Normal reference — fitted by matching the sample
    mean and standard deviation — is the wrong shape.

    For each sorted observation :math:`x_{(i)}` the two probabilities
    are computed here in closed form so the SVG only has to carry the
    two diagnostic coordinates per point:

    * **empirical** — the plotting-position estimate of the CDF,
      :math:`(i - 0.5) / n`, a standard continuity-corrected rank;
    * **theoretical** — the fitted Normal CDF evaluated at
      :math:`x_{(i)}`, i.e. :math:`\\Phi((x_{(i)} - \\mu) / \\sigma)`.

    On the diagonal the two agree; the skew pushes the cloud into a bow.

    Parameters
    ----------
    n : int, optional
        Number of sessions (points). Default 90.
    seed : int, optional
        NumPy random seed for reproducibility. Default 7.

    Returns
    -------
    list of dict
        One record per session,
        ``{"empirical": <prob 0-1>, "theoretical": <prob 0-1>,
        "minutes": <session length>}``, rounded so the values read
        cleanly in a tooltip.
    """
    rng = np.random.default_rng(seed)

    # True process: log-normal session lengths (minutes) — most sessions
    # are short, a long right tail of engaged users. This is the skew a
    # symmetric Normal cannot match.
    x = rng.lognormal(mean=1.6, sigma=0.55, size=n)
    x_sorted = np.sort(x)

    # The analyst's (mis-specified) reference: a Normal fitted by
    # matching the sample mean and standard deviation.
    mu = float(np.mean(x_sorted))
    sigma = float(np.std(x_sorted, ddof=1))

    # Theoretical CDF probability under the fitted Normal.
    theoretical = _normal_cdf((x_sorted - mu) / sigma)

    # Empirical CDF probability: the continuity-corrected plotting
    # position (i - 0.5) / n for the i-th order statistic.
    ranks = np.arange(1, n + 1)
    empirical = (ranks - 0.5) / n

    return [
        {
            "empirical": round(float(e), 4),
            "theoretical": round(float(t), 4),
            "minutes": round(float(m), 1),
        }
        for e, t, m in zip(empirical, theoretical, x_sorted)
    ]


def _loess(
    xs: np.ndarray,
    ys: np.ndarray,
    grid: np.ndarray,
    bandwidth: float = 0.55,
) -> np.ndarray:
    """Locally-weighted (LOESS) linear smooth of ``ys`` on ``xs``, read on ``grid``.

    A light, dependency-free LOESS: at each grid point a weighted linear
    regression is fit over all samples, with tricube weights on the scaled
    distance so nearby points dominate. This turns the vague point cloud
    into an unmistakable arc without pulling in statsmodels or SciPy.

    Parameters
    ----------
    xs, ys : numpy.ndarray
        The point coordinates (theoretical, empirical).
    grid : numpy.ndarray
        The x positions at which to evaluate the smooth.
    bandwidth : float, optional
        Fraction of the x-range used as the tricube kernel half-width.
        Default 0.55.

    Returns
    -------
    numpy.ndarray
        The smoothed y value at each ``grid`` position.
    """
    span = max(float(xs.max() - xs.min()), 1e-9)
    h = bandwidth * span
    out = np.empty_like(grid, dtype=float)
    for i, g in enumerate(grid):
        # Tricube weights on the scaled distance; points past the bandwidth
        # get zero weight.
        u = np.abs(xs - g) / h
        w = np.where(u < 1.0, (1.0 - u ** 3) ** 3, 0.0)
        if w.sum() < 1e-9:
            # No neighbour in range: fall back to the nearest sample.
            out[i] = ys[int(np.argmin(np.abs(xs - g)))]
            continue
        # Weighted least squares for a local line y = a + b x.
        sw = w.sum()
        mx = np.sum(w * xs) / sw
        my = np.sum(w * ys) / sw
        cov = np.sum(w * (xs - mx) * (ys - my))
        var = np.sum(w * (xs - mx) ** 2)
        b = cov / var if var > 1e-12 else 0.0
        a = my - b * mx
        out[i] = a + b * g
    return out


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full P-P-plot SVG string.

    The plot is a square unit view (theoretical probability on x, empirical
    probability on y, both in ``[0, 1]``) carrying, bottom to top: a faint
    tolerance ribbon around the diagonal; the dashed 45-degree reference
    line; the P-P points coloured by which side of the diagonal they fall
    on (blue above, orange below); a smooth LOESS trend arc; and direct
    above/below annotations so the signed split reads without a colour key.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``: the SVG carries its own fullscreen button.
    accessibility : str, optional
        Palette accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). Defaults to ``"universal"``, the colour-vision-safe
        standard, which leaves the shipped palette unchanged.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    data = make_data()
    palette: Dict[str, str] = load_palette(accessibility)

    # Signed split, blue vs orange (never red-green): a point ABOVE the
    # diagonal (empirical >= theoretical) means the Normal under-states the
    # probability — blue; a point BELOW means it over-states — orange. Both
    # clusters are also labelled directly, so the split survives greyscale.
    above = palette.get("Blue", "#007AFF")     # Normal under-states P
    below = palette.get("Orange", "#FF9500")   # Normal over-states P
    trend = palette.get("Red", "#FF3B30")      # the LOESS structure arc
    ink = "#1D1D1F"
    secondary = "#6E6E73"
    grid_col = "#ECECEC"
    band_col = "#8E8E93"

    # --- canvas geometry -----------------------------------------
    width = 1160
    height = 1160
    m_left = 150
    m_right = 96
    m_top = 250
    m_bottom = 150
    plot_x = m_left
    plot_y = m_top
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    ticks = [0.0, 0.25, 0.5, 0.75, 1.0]

    def sx(v: float) -> float:
        """Map theoretical probability in ``[0, 1]`` to an x pixel coordinate."""
        return plot_x + v * plot_w

    def sy(v: float) -> float:
        """Map empirical probability in ``[0, 1]`` to a y pixel coordinate."""
        return plot_y + (1.0 - v) * plot_h

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    parts.append(svg_open(width, height, "pp-title", "pp-desc"))
    parts.append(
        '<title id="pp-title">Session times aren\'t Normal — the P-P plot '
        'bows off the diagonal</title>'
    )
    parts.append(
        '<desc id="pp-desc">Probability-probability (P-P) plot checking '
        'whether a fitted Normal distribution describes right-skewed customer '
        'session durations. The horizontal axis is the theoretical cumulative '
        'probability under the fitted Normal; the vertical axis is the '
        'empirical cumulative probability of the observed data; both run from '
        '0 to 1. A dashed 45-degree reference line marks perfect agreement, '
        'ringed by a faint grey tolerance band. Instead of hugging the line '
        'the points bow into a smooth arc (traced by a red trend curve): in '
        'the lower-left they sit above the diagonal, where the Normal '
        'under-states the probability (blue); in the upper-right they sit '
        'below it, where the Normal over-states the probability (orange). '
        'That S-shaped departure is the classic sign that a symmetric Normal '
        'is the wrong shape for skewed data. Illustrative data.</desc>'
    )

    # Static figure; hover / focus enlargement only, no motion to guard.
    # OS-adaptive overrides are appended (additive; every rule lives inside an
    # @media block so the default render is byte-for-byte unchanged). The two
    # signed clusters carry ``.pp-above`` / ``.pp-below`` classes as hooks:
    # under prefers-contrast they deepen to their high-contrast blue/orange so
    # the above/below split stays crisp. forced-colors is left to the browser
    # default — the split is colour-encoded (two intermixed clouds), so the
    # ~4-colour system palette cannot preserve it; the direct text labels carry
    # the identity regardless.
    contrast_block = os_adaptive_style(
        {".pp-above": above, ".pp-below": below},
        role="fill",
    )
    parts.append(
        "<style>"
        ".pt{cursor:pointer}"
        ".pt .halo{opacity:0}"
        ".pt:hover .halo,.pt:focus .halo{opacity:1}"
        ".pt:focus{outline:none}"
        + "\n" + contrast_block + "\n"
        + os_dark_style() + "\n"
        "</style>"
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="96" font-size="44" font-weight="700" '
        f'fill="{ink}">Session times aren’t Normal</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="148" font-size="25" fill="{secondary}">'
        f'Empirical vs fitted-Normal CDF — the arc off the 45° line '
        f'flags the skew · illustrative</text>'
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

    # --- tolerance ribbon around the diagonal --------------------
    # A soft band y = x +/- band, clamped to the unit square, so the eye reads
    # "inside here counts as a good fit". Drawn as a filled quadrilateral pair
    # (upper and lower rules) via a single polygon around the band outline.
    band = 0.05
    xs_band = np.linspace(0.0, 1.0, 61)
    upper = [(sx(float(x)), sy(min(1.0, float(x) + band))) for x in xs_band]
    lower = [(sx(float(x)), sy(max(0.0, float(x) - band))) for x in xs_band]
    ribbon_pts = upper + lower[::-1]
    d_band = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in ribbon_pts) + " Z"
    parts.append(
        f'<path d="{d_band}" fill="{band_col}" fill-opacity="0.10" '
        f'stroke="none"/>'
    )

    # --- 45-degree reference line --------------------------------
    parts.append(
        f'<line x1="{sx(0.0):.1f}" y1="{sy(0.0):.1f}" x2="{sx(1.0):.1f}" '
        f'y2="{sy(1.0):.1f}" stroke="{band_col}" stroke-width="2.5" '
        f'stroke-dasharray="9 6"/>'
    )
    # "Perfect fit" caption riding on the diagonal, rotated to run parallel
    # to it. It sits in the lower-right stretch, just below the line where the
    # orange cluster has already fallen away, so it never crowds the points.
    mid_x, mid_y = sx(0.80), sy(0.80)
    parts.append(
        f'<text x="{mid_x:.1f}" y="{mid_y:.1f}" font-size="20" '
        f'fill="{secondary}" text-anchor="middle" '
        f'transform="rotate(-45 {mid_x:.1f} {mid_y:.1f})" dy="24">'
        f'Perfect fit (45°)</text>'
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
            f'text-anchor="middle">{t:.2f}</text>'
        )
        gy = sy(t)
        parts.append(
            f'<line x1="{plot_x - 8:.1f}" y1="{gy:.1f}" x2="{plot_x:.1f}" '
            f'y2="{gy:.1f}" stroke="{ink}" stroke-width="1.8"/>'
        )
        parts.append(
            f'<text x="{plot_x - 18:.1f}" y="{gy + 7:.1f}" font-size="21" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="end">{t:.2f}</text>'
        )

    # --- axis titles ---------------------------------------------
    parts.append(
        f'<text x="{plot_x + plot_w / 2:.1f}" y="{ax_bottom + 84:.1f}" '
        f'font-size="24" fill="{ink}" text-anchor="middle">'
        f'Theoretical probability (fitted Normal CDF)</text>'
    )
    ytitle_x = 58
    ytitle_y = plot_y + plot_h / 2
    parts.append(
        f'<text x="{ytitle_x:.1f}" y="{ytitle_y:.1f}" font-size="24" '
        f'fill="{ink}" text-anchor="middle" '
        f'transform="rotate(-90 {ytitle_x:.1f} {ytitle_y:.1f})">'
        f'Empirical probability (observed CDF)</text>'
    )

    # --- LOESS trend arc (drawn under the points) -----------------
    xs = np.array([float(d["theoretical"]) for d in data])
    ys = np.array([float(d["empirical"]) for d in data])
    order = np.argsort(xs)
    xs_o, ys_o = xs[order], ys[order]
    grid = np.linspace(float(xs_o.min()), float(xs_o.max()), 80)
    smooth = _loess(xs_o, ys_o, grid, bandwidth=0.55)
    trend_pts = [(sx(float(g)), sy(float(v))) for g, v in zip(grid, smooth)]
    d_trend = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in trend_pts)
    # White under-stroke first so the arc stays crisp over the points/grid.
    parts.append(
        f'<path d="{d_trend}" fill="none" stroke="#FFFFFF" stroke-width="11" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<path d="{d_trend}" fill="none" stroke="{trend}" stroke-width="5" '
        f'stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.95"/>'
    )

    # --- the P-P points ------------------------------------------
    for d in data:
        theo = float(d["theoretical"])
        emp = float(d["empirical"])
        cx, cy = sx(theo), sy(emp)
        side_above = emp >= theo
        col = above if side_above else below
        tip = (
            f'Session {d["minutes"]:.1f} min: theoretical P {theo:.2f}, '
            f'empirical P {emp:.2f}'
        )
        parts.append(
            f'<g class="pt" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}">'
        )
        parts.append(f"<title>{xml_escape(tip)}</title>")
        parts.append(
            f'<circle class="halo" cx="{cx:.1f}" cy="{cy:.1f}" r="18" '
            f'fill="{ink}" fill-opacity="0.08"/>'
        )
        pt_class = "pp-above" if side_above else "pp-below"
        parts.append(
            f'<circle class="{pt_class}" cx="{cx:.1f}" cy="{cy:.1f}" r="8.5" '
            f'fill="{col}" fill-opacity="0.9" stroke="#FFFFFF" stroke-width="1.6"/>'
        )
        parts.append("</g>")

    # --- direct above / below annotations ------------------------
    # Each cluster sits on its own side of the diagonal, so the label goes
    # into the open triangle it points into: the "above" pair in the
    # upper-left, the "below" pair in the lower-right. Coloured ink matching
    # the marks, no outline halo — the split reads without a colour key.
    parts.append(
        f'<text class="pp-above" x="{sx(0.075):.1f}" y="{sy(0.90):.1f}" font-size="26" '
        f'font-weight="700" fill="{above}" text-anchor="start">'
        f'Above the line</text>'
    )
    parts.append(
        f'<text class="pp-above" x="{sx(0.075):.1f}" y="{sy(0.90) + 32:.1f}" font-size="22" '
        f'fill="{above}" text-anchor="start">Normal under-states P</text>'
    )
    parts.append(
        f'<text class="pp-below" x="{sx(0.925):.1f}" y="{sy(0.16):.1f}" font-size="26" '
        f'font-weight="700" fill="{below}" text-anchor="end">'
        f'Below the line</text>'
    )
    parts.append(
        f'<text class="pp-below" x="{sx(0.925):.1f}" y="{sy(0.16) + 32:.1f}" font-size="22" '
        f'fill="{below}" text-anchor="end">Normal over-states P</text>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the P-P-plot SVG to the canonical assets path (or --out)."""
    render_cli(
        __file__, "ppplot", build_svg,
        description="Render the P-P plot SVG (empirical vs theoretical CDF, "
        "45-degree reference line, above/below split).",
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
make_liftgain — a cumulative-gain (lift/gain) chart as hand-authored SVG.

The **cumulative-gain curve** answers a targeting question: if a model
ranks every customer by predicted risk and you work down that list,
what fraction of the true positives have you captured by the time you
have contacted the top X %? Three reference curves make the answer
legible:

* the **random baseline** — a diagonal, where contacting X % of a
  randomly ordered list captures X % of the positives (no targeting);
* the **perfect model** — the theoretical ceiling, where every real
  positive is ranked ahead of every negative, so the curve climbs at
  the steepest possible slope until all positives are captured, then
  flattens;
* the **actual model** — the real ranked list, which lives between the
  two; its *gap above the baseline* is the value the model adds.

The scenario is a churn-prevention campaign with a fixed calling
budget. The takeaway the figure is built to communicate: **calling the
riskiest 20 % of the ranked list reaches ~63 % of the churners** — a
marker sits at that operating point, with dropped guide lines and a
direct call-out stating both the gain and the lift over random. That is
the number a campaign owner budgets against.

This generator builds the SVG by hand (no matplotlib / seaborn / plotly,
no Vega) so the shaded "gain over random" band, the three curves, the
operating-point guides, and the direct curve labels are all under our
control. Curves are distinguished by **more than hue**: the model curve
is a thick solid line with an end-label, the perfect-model envelope is a
thinner solid line labelled at its kink, and the random baseline is a
*dashed* diagonal — so the three read apart under greyscale and
deuteranopia and each is named directly on the plot, not only in a
legend. It matches the front-* house style: Roboto, the Apple-ish
palette, rounded corners, ink ``#1D1D1F``, secondary ``#6E6E73``, white
background, white keylines.

The operating-point marker carries a native ``<title>`` tooltip and a
:hover / :focus emphasis; no JavaScript beyond the shared fullscreen
control.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/liftgain.svg``.

Usage
-----
::

    python make_liftgain.py            # writes next to the skill
    python make_liftgain.py --out /tmp/liftgain.svg
    python make_liftgain.py --mode static   # no fullscreen button

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# House-style helpers live alongside this script in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402


# The operating point the campaign owner budgets against: the fraction
# of the ranked customer list the retention team can afford to contact.
_OPERATING_FRACTION = 0.20


def _simulate_scores(n: int, base_rate: float, seed: int, separation: float = 1.6) -> "np.ndarray":
    """Simulate a ranked churn-risk experiment and return the labels.

    A model assigns each of ``n`` customers a churn-risk score; the
    customers are then sorted from highest to lowest score. This returns
    the true churn labels *in that ranked order* — a 1 where the
    customer actually churned, a 0 otherwise. A useful (but imperfect)
    model concentrates the 1s near the sprezzature of the array.

    The scores come from the standard two-population model used to
    reason about a binary classifier's ranking quality: non-churners and
    churners each draw a Gaussian score, and the churners' distribution
    is shifted up by ``separation`` standard deviations. A larger shift
    means the model separates the classes better; the overlap that
    remains is what keeps the model realistic rather than an oracle.

    Parameters
    ----------
    n : int
        Number of customers in the base.
    base_rate : float
        Overall churn rate (fraction of customers who churn).
    seed : int
        NumPy random seed for reproducibility.
    separation : float, optional
        Gap between the churner and non-churner score means, in standard
        deviations (the model's discriminative skill). Default 1.6,
        tuned so the top-20% cutoff reaches ~3 in 5 churners.

    Returns
    -------
    numpy.ndarray
        Length-``n`` array of 0/1 churn labels, ordered from the
        model's highest predicted risk to its lowest.
    """
    rng = np.random.default_rng(seed)

    # True churn labels at the given base rate.
    labels = (rng.random(n) < base_rate).astype(int)

    # Model score per customer: a shared Gaussian, shifted up for the
    # customers who actually churned. Overlap between the two humps is
    # the model's residual uncertainty. Rank by descending score.
    score = rng.normal(0.0, 1.0, size=n) + separation * labels
    order = np.argsort(-score)
    return labels[order]


def make_data(n: int = 4000, base_rate: float = 0.18, seed: int = 11) -> Dict[str, Any]:
    """Build the cumulative-gain coordinates for all three curves.

    Walks down the model-ranked customer list and, at each population
    fraction, records what share of *all* churners has been captured so
    far. Does the same for the two reference curves (random ordering and
    a perfect ranking) so every layer shares one x-grid.

    Parameters
    ----------
    n : int, optional
        Number of customers. Default 4000.
    base_rate : float, optional
        Overall churn rate. Default 0.18.
    seed : int, optional
        NumPy random seed. Default 11.

    Returns
    -------
    dict
        ``{"curve": [...], "operating": {...}, "prevalence": float}``
        where ``curve`` is a list of records ``{"pop": <0-1>, "gain":
        <0-1>, "series": "Model|Perfect model|Random baseline"}``,
        ``operating`` holds the annotated top-``_OPERATING_FRACTION``
        point for the model, and ``prevalence`` is the churn base rate
        (fixing the perfect model's kink at ``pop = prevalence``).
    """
    ranked = _simulate_scores(n=n, base_rate=base_rate, seed=seed)
    total_pos = int(ranked.sum())

    # Cumulative positives captured as we include more of the ranked list.
    cum_pos = np.concatenate([[0], np.cumsum(ranked)])
    pop = np.arange(0, n + 1) / n
    model_gain = cum_pos / total_pos

    # Perfect model: every churner ranked first. The gain climbs at
    # slope 1/base_rate until all positives are captured, then flats.
    prevalence = total_pos / n
    perfect_gain = np.minimum(pop / prevalence, 1.0)

    # Sample the curves on a coarse x-grid so the SVG stays light while
    # the shape is preserved (the curves are near-monotone and smooth).
    grid = np.linspace(0.0, 1.0, 51)
    idx = np.clip((grid * n).astype(int), 0, n)

    records: List[Dict[str, Any]] = []
    for gx, gi in zip(grid, idx):
        records.append({"pop": round(float(gx), 4), "gain": round(float(model_gain[gi]), 4), "series": "Model"})
        records.append({"pop": round(float(gx), 4), "gain": round(float(perfect_gain[gi]), 4), "series": "Perfect model"})
        records.append({"pop": round(float(gx), 4), "gain": round(float(gx), 4), "series": "Random baseline"})

    # The annotated operating point: the model's gain at the top fraction
    # the campaign can afford to contact.
    op_i = int(round(_OPERATING_FRACTION * n))
    op_gain = float(model_gain[op_i])
    operating = {
        "pop": round(_OPERATING_FRACTION, 4),
        "gain": round(op_gain, 4),
        # Lift = how many times better than random at this cutoff.
        "lift": round(op_gain / _OPERATING_FRACTION, 2),
    }

    return {"curve": records, "operating": operating, "prevalence": round(prevalence, 4)}


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full cumulative-gain (lift/gain) SVG string.

    Draws, back to sprezzature: the light plot band and gridlines, the shaded
    "gain over random" band between the model curve and the diagonal,
    the dashed random baseline, the perfect-model envelope, the thick
    model curve, the operating-point drop/cross guides and marker with
    its direct call-out, direct labels on all three curves, and the two
    percentage axes.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``; the button never alters the raster.
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
    data = make_data()
    curve = data["curve"]
    op = data["operating"]
    prevalence = float(data["prevalence"])

    palette: Dict[str, str] = load_palette(accessibility)
    model_c = palette.get("Blue", "#007AFF")     # the hero: what we shipped
    perfect_c = palette.get("Green", "#34C759")  # the ceiling
    baseline_c = "#8E8E93"                        # random: neutral grey
    marker_c = palette.get("Orange", "#FF9500")  # the operating point
    ink = "#1D1D1F"
    secondary = "#6E6E73"
    band = "#F5F5F7"

    # --- canvas geometry (square plot, so the diagonal reads at 45°) --
    width = 1040
    height = 940
    m_left = 118
    m_right = 60
    m_top = 200
    m_bottom = 120
    plot_x = m_left
    plot_y = m_top
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom
    ax_bottom = plot_y + plot_h

    # Both axes are shares in [0, 1]; a hair of headroom on y keeps the
    # plateau of the perfect / model curves off the top frame.
    x_min, x_max = 0.0, 1.0
    y_min, y_max = 0.0, 1.06
    ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    def sx(v: float) -> float:
        """Map a population share (0..1) to an x pixel coordinate."""
        return plot_x + (v - x_min) / (x_max - x_min) * plot_w

    def sy(v: float) -> float:
        """Map a gain share (0..1) to a y pixel coordinate (y-down)."""
        return plot_y + (y_max - v) / (y_max - y_min) * plot_h

    model_pts = [(float(r["pop"]), float(r["gain"])) for r in curve if r["series"] == "Model"]

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    op_pct = round(op["gain"] * 100)
    parts.append(svg_open(width, height, "lg-title", "lg-desc"))
    parts.append(
        '<title id="lg-title">A churn model reaches most churners from a '
        'small fraction of the ranked list</title>'
    )
    parts.append(
        f'<desc id="lg-desc">Cumulative-gain chart for a churn-prevention '
        f'campaign (illustrative). The horizontal axis is the share of '
        f'customers contacted, working down a list ranked by the model’s '
        f'predicted churn risk; the vertical axis is the share of all '
        f'churners reached. Three curves: a dashed grey diagonal is the '
        f'random baseline (contacting X % reaches X % of churners); a thin '
        f'green line is the perfect model, the ceiling, rising steeply then '
        f'flattening once every churner is captured; and a thick blue line '
        f'is the actual model, sitting between the two. The shaded blue band '
        f'between the model and the diagonal is the value the model adds. '
        f'A marker shows the operating point: contacting the riskiest '
        f'{round(op["pop"] * 100)} % reaches {op_pct} % of churners, '
        f'{op["lift"]}× better than random. Illustrative figures.</desc>'
    )

    # Static figure: hover / focus emphasis only, no motion to guard.
    # The OS-adaptive overrides are additive: every rule they emit lives inside
    # a media query, so the default render is byte-for-byte unchanged, and only
    # under prefers-contrast do the three meaningful hues deepen. The random
    # baseline stays neutral grey and is deliberately left out. forced-colors is
    # left to the browser default because the curves are colour-encoded.
    lg_curve_series = {".lg-model": model_c, ".lg-perfect": perfect_c}
    lg_marker_series = {".lg-marker": marker_c}
    parts.append(
        "<style>"
        ".pt{cursor:pointer}"
        ".pt .halo{opacity:0}"
        ".pt:hover .halo,.pt:focus .halo{opacity:1}"
        ".pt:focus{outline:none}"
        + os_adaptive_style(lg_curve_series, role="stroke")
        + os_adaptive_style(lg_marker_series, role="fill")
        # Additive OS dark mode: dark paper + light ink (default ink_map); the
        # ranking curves (model / perfect / random) keep their data hues. The
        # light plot band is darkened to a panel that reads on the dark surface;
        # the white gridlines drawn over it dim to a faint dark-grey so they stay
        # subtle instead of glaring white on dark.
        + os_dark_style(
            extra=(
                '[fill="#F5F5F7"]{fill:#17171A;}'
                ".lg-grid{stroke:#2C2C30;}"
            )
        )
        + "</style>"
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')
    parts.append(
        f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" '
        f'fill="{band}" rx="10"/>'
    )

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="80" font-size="42" font-weight="700" '
        f'fill="{ink}">Calling the riskiest {round(op["pop"] * 100)}% '
        f'reaches {op_pct}% of churners</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="124" font-size="24" fill="{secondary}">'
        f'Cumulative-gain curve: churners reached vs share of the '
        f'model-ranked base contacted</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="156" font-size="20" fill="{secondary}">'
        f'Illustrative data</text>'
    )

    # --- gridlines (very light, on the shared 0..1 grid) ---------
    for t in ticks:
        gx, gy = sx(t), sy(t)
        parts.append(
            f'<line class="lg-grid" x1="{gx:.1f}" y1="{plot_y:.1f}" x2="{gx:.1f}" '
            f'y2="{ax_bottom:.1f}" stroke="#FFFFFF" stroke-width="1.6"/>'
        )
        parts.append(
            f'<line class="lg-grid" x1="{plot_x:.1f}" y1="{gy:.1f}" x2="{plot_x + plot_w:.1f}" '
            f'y2="{gy:.1f}" stroke="#FFFFFF" stroke-width="1.6"/>'
        )

    # --- shaded "gain over random" band --------------------------
    # A closed polygon: forward along the model curve, then back down the
    # diagonal. The fill is the model hue at low opacity, so the benefit reads
    # at a glance and even in greyscale (a filled region, not just a colour).
    up = " L ".join(f"{sx(px):.1f} {sy(py):.1f}" for px, py in model_pts)
    back = " L ".join(
        f"{sx(px):.1f} {sy(px):.1f}" for px, _ in reversed(model_pts)
    )
    parts.append(
        f'<path d="M {up} L {back} Z" fill="{model_c}" fill-opacity="0.13"/>'
    )

    # --- random baseline (dashed grey diagonal) ------------------
    parts.append(
        f'<line x1="{sx(0.0):.1f}" y1="{sy(0.0):.1f}" x2="{sx(1.0):.1f}" '
        f'y2="{sy(1.0):.1f}" stroke="{baseline_c}" stroke-width="2.4" '
        f'stroke-dasharray="8 6"/>'
    )

    # --- perfect-model envelope (thin solid green, kinks at prevalence) --
    # Two straight segments: a steep rise to (prevalence, 1) then a flat top.
    kx = sx(prevalence)
    ky = sy(1.0)
    parts.append(
        f'<path class="lg-perfect" d="M {sx(0.0):.1f} {sy(0.0):.1f} '
        f'L {kx:.1f} {ky:.1f} L {sx(1.0):.1f} {ky:.1f}" fill="none" '
        f'stroke="{perfect_c}" stroke-width="3" stroke-linejoin="round"/>'
    )

    # --- the model gain curve (thick solid blue, the hero) -------
    dmodel = "M " + " L ".join(f"{sx(px):.1f} {sy(py):.1f}" for px, py in model_pts)
    # White under-stroke keeps the hero crisp where it crosses a curve/grid.
    parts.append(
        f'<path d="{dmodel}" fill="none" stroke="#FFFFFF" stroke-width="10" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<path class="lg-model" d="{dmodel}" fill="none" stroke="{model_c}" '
        f'stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # --- direct curve labels (named on the plot, not only in a legend) --
    # Perfect model: label near its kink, above the flat top.
    parts.append(
        f'<text x="{kx + 14:.1f}" y="{ky - 14:.1f}" font-size="21" '
        f'font-weight="600" fill="{perfect_c}">Perfect model</text>'
    )
    # Random baseline: label riding the diagonal in the lower-right.
    rb_x, rb_y = sx(0.72), sy(0.72)
    parts.append(
        f'<text x="{rb_x + 6:.1f}" y="{rb_y + 30:.1f}" font-size="21" '
        f'font-weight="600" fill="{baseline_c}" '
        f'transform="rotate(-40 {rb_x + 6:.1f} {rb_y + 30:.1f})">'
        f'Random baseline</text>'
    )
    # Model: label at the curve's right end, where it plateaus near 100 %.
    mlx, mly = model_pts[-1]
    parts.append(
        f'<text x="{sx(mlx) - 8:.1f}" y="{sy(mly) - 18:.1f}" font-size="23" '
        f'font-weight="700" fill="{model_c}" text-anchor="end">Model</text>'
    )

    # --- operating-point guides + marker + call-out --------------
    opx, opy = float(op["pop"]), float(op["gain"])
    mx, my = sx(opx), sy(opy)
    # Dropped vertical + horizontal guides from the axes to the point.
    parts.append(
        f'<line x1="{mx:.1f}" y1="{ax_bottom:.1f}" x2="{mx:.1f}" '
        f'y2="{my:.1f}" stroke="{marker_c}" stroke-width="1.8" '
        f'stroke-dasharray="4 4" opacity="0.85"/>'
    )
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{my:.1f}" x2="{mx:.1f}" y2="{my:.1f}" '
        f'stroke="{marker_c}" stroke-width="1.8" stroke-dasharray="4 4" '
        f'opacity="0.85"/>'
    )
    tip = (
        f'Top {round(opx * 100)}% contacted → {op_pct}% of churners reached '
        f'({op["lift"]}× better than random)'
    )
    parts.append(
        f'<g class="pt" tabindex="0" role="img" aria-label="{xml_escape(tip)}">'
    )
    parts.append(f"<title>{xml_escape(tip)}</title>")
    parts.append(
        f'<circle class="halo" cx="{mx:.1f}" cy="{my:.1f}" r="22" '
        f'fill="{ink}" fill-opacity="0.08"/>'
    )
    parts.append(
        f'<circle class="lg-marker" cx="{mx:.1f}" cy="{my:.1f}" r="11" '
        f'fill="{marker_c}" stroke="#FFFFFF" stroke-width="2.5"/>'
    )
    parts.append("</g>")
    parts.append(
        f'<text x="{mx + 20:.1f}" y="{my - 14:.1f}" font-size="22" '
        f'font-weight="700" fill="{marker_c}">Top {round(opx * 100)}% → '
        f'{op_pct}% of churners</text>'
    )
    parts.append(
        f'<text x="{mx + 20:.1f}" y="{my + 12:.1f}" font-size="20" '
        f'fill="{secondary}">{op["lift"]}× better than random</text>'
    )

    # --- axes ----------------------------------------------------
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{plot_y:.1f}" x2="{plot_x:.1f}" '
        f'y2="{ax_bottom:.1f}" stroke="{ink}" stroke-width="1.6"/>'
    )
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{ax_bottom:.1f}" '
        f'x2="{plot_x + plot_w:.1f}" y2="{ax_bottom:.1f}" '
        f'stroke="{ink}" stroke-width="1.6"/>'
    )
    for t in ticks:
        gx, gy = sx(t), sy(t)
        pct = f"{round(t * 100)}%"
        # X ticks + labels.
        parts.append(
            f'<line x1="{gx:.1f}" y1="{ax_bottom:.1f}" x2="{gx:.1f}" '
            f'y2="{ax_bottom + 7:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="{ax_bottom + 30:.1f}" font-size="19" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">{pct}</text>'
        )
        # Y ticks + labels.
        parts.append(
            f'<line x1="{plot_x - 7:.1f}" y1="{gy:.1f}" x2="{plot_x:.1f}" '
            f'y2="{gy:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{plot_x - 14:.1f}" y="{gy + 6:.1f}" font-size="19" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="end">{pct}</text>'
        )

    # Axis titles.
    parts.append(
        f'<text x="{plot_x + plot_w / 2:.1f}" y="{ax_bottom + 72:.1f}" '
        f'font-size="22" fill="{ink}" text-anchor="middle">'
        f'Share of customers contacted (ranked by model)</text>'
    )
    yt_x = 52
    yt_y = plot_y + plot_h / 2
    parts.append(
        f'<text x="{yt_x:.1f}" y="{yt_y:.1f}" font-size="22" fill="{ink}" '
        f'text-anchor="middle" '
        f'transform="rotate(-90 {yt_x:.1f} {yt_y:.1f})">'
        f'Share of churners reached</text>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the cumulative-gain SVG to the canonical assets path (or --out)."""
    render_cli(
        __file__, "liftgain", build_svg,
        description="Render the house-style cumulative-gain (lift/gain) chart "
                    "(model curve + perfect model + random baseline) to SVG.",
    )


if __name__ == "__main__":
    main()

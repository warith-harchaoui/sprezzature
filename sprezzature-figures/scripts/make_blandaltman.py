#!/usr/bin/env python3
"""
make_blandaltman — a Bland-Altman agreement plot as hand-authored SVG.

The **Bland-Altman agreement plot** answers the question a correlation
coefficient cannot: *can I use method B in place of method A?* For two
methods that measure the same quantity it plots the *difference* between
each paired measurement against their *mean*, then overlays the mean
difference (the **bias**) and the 95 % **limits of agreement**
(bias ± 1.96·SD of the differences). A high correlation only says two
methods rise and fall together; this plot shows whether they actually
*agree* — how large the typical gap is, whether it drifts with the
magnitude of the measurement, and how wide a band contains 95 % of the
disagreements.

This generator builds the SVG **by hand** — no matplotlib / seaborn /
plotly, no Vega — so the shaded limits-of-agreement band, the bias and
limit rules with their right-hand value chips, the difference scatter,
and the proportional-bias trend line are all under our control and can
carry the house interactivity (per-point tooltips, a fullscreen button)
that a rasterised Vega spec cannot. It matches the sprezzature-* house style:
Roboto, the Apple-ish palette, rounded corners, ink ``#1D1D1F``,
secondary ``#6E6E73``, white background, bright white keylines (never
dark rings).

The scenario compares a **wrist blood-pressure monitor** against a clinic
**arm cuff** (the reference) across 90 patients. The wrist device reads
systematically low (a negative bias) and its error grows with blood
pressure (proportional bias), so the cloud of points tilts downward to
the right — the textbook pattern the plot is built to expose. A dashed
trend line through the differences makes that drift impossible to miss.
Illustrative data.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/blandaltman.svg``.

Usage
-----
::

    python make_blandaltman.py            # writes next to the skill
    python make_blandaltman.py --out /tmp/blandaltman.svg
    python make_blandaltman.py --mode static   # no fullscreen button

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

# House-style tokens + the shared SVG primitives live alongside in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _interactive import fullscreen_control  # noqa: E402
from _render import render_cli  # noqa: E402
from _style import leveled_colors, load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402


def make_data(n: int = 90, seed: int = 7) -> List[Dict[str, float]]:
    """Sample paired blood-pressure readings from two devices.

    The scenario: for each of ``n`` patients we have a systolic blood
    pressure measured twice — once with a clinic **arm cuff** (treated
    as the reference) and once with a **wrist monitor** (the device
    under evaluation). The wrist device carries two flaws a
    Bland-Altman plot is designed to surface:

    * a **fixed bias** — it reads a few mmHg low on average; and
    * a **proportional bias** — the underestimation worsens the higher
      the true pressure, so the differences drift downward with the
      mean.

    Each returned record already carries the two Bland-Altman
    coordinates, computed here so the SVG only has to plot them:
    ``mean`` (average of the two devices) and ``diff`` (wrist minus arm,
    the disagreement in mmHg).

    Parameters
    ----------
    n : int, optional
        Number of patients (paired points). Default 90.
    seed : int, optional
        NumPy random seed for reproducibility. Default 7.

    Returns
    -------
    list of dict
        One record per patient,
        ``{"mean": <average systolic, mmHg>, "diff": <wrist − arm, mmHg>}``,
        rounded so the values read cleanly in a tooltip.
    """
    rng = np.random.default_rng(seed)

    # Reference (arm-cuff) systolic pressure across a clinically
    # realistic 95-185 mmHg range, from normotensive to hypertensive.
    arm = rng.uniform(95.0, 185.0, size=n)

    # Wrist device: reads low by a fixed offset plus a slope that grows
    # with pressure (proportional error), with per-patient measurement
    # noise on top. These are the two structures the plot reveals.
    fixed_bias = -3.0
    proportional = -0.08 * (arm - 95.0)
    noise = rng.normal(0.0, 4.0, size=n)
    wrist = arm + fixed_bias + proportional + noise

    mean = (arm + wrist) / 2.0
    diff = wrist - arm

    return [
        {"mean": round(float(m), 1), "diff": round(float(d), 1)}
        for m, d in zip(mean, diff)
    ]


def agreement_stats(data: List[Dict[str, float]]) -> Dict[str, float]:
    """Compute the bias and 95 % limits of agreement from the differences.

    Parameters
    ----------
    data : list of dict
        Records from :func:`make_data`.

    Returns
    -------
    dict
        ``{"bias": <mean difference>, "sd": <SD of differences>,
        "loa_lo": <bias − 1.96·SD>, "loa_hi": <bias + 1.96·SD>}``,
        each in mmHg.
    """
    diffs = np.array([d["diff"] for d in data], dtype=float)
    bias = float(diffs.mean())
    # Sample standard deviation (ddof=1) — the convention for the
    # limits of agreement, which estimate a population spread.
    sd = float(diffs.std(ddof=1))
    return {
        "bias": bias,
        "sd": sd,
        "loa_lo": bias - 1.96 * sd,
        "loa_hi": bias + 1.96 * sd,
    }


def _linear_fit(xs: List[float], ys: List[float]) -> tuple[float, float]:
    """Return the ordinary-least-squares ``(slope, intercept)`` of y on x.

    A plain degree-1 :func:`numpy.polyfit` of the differences on the
    means — the proportional-bias trend line the plot draws so a vague
    tilt reads as an unmistakable drift.

    Parameters
    ----------
    xs : list of float
        The x-values (per-patient means).
    ys : list of float
        The y-values (per-patient differences).

    Returns
    -------
    tuple of float
        ``(slope, intercept)`` of the least-squares line ``y = slope·x +
        intercept``.
    """
    slope, intercept = np.polyfit(np.asarray(xs), np.asarray(ys), 1)
    return float(slope), float(intercept)


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full Bland-Altman SVG string.

    Draws, bottom to top:

    1. a shaded **limits-of-agreement band** spanning the 95 % interval;
    2. very light **gridlines** and the L-shaped ink **axes** with ticks
       and Roboto-Mono tick labels;
    3. a dashed grey **zero rule** — perfect agreement — with a caption;
    4. the **bias rule** (solid Blue, thick) and the two **limit rules**
       (dashed Red), each with a right-hand value chip on a white plate;
    5. the **difference scatter** — one neutral dot per patient, each a
       focusable ``<g>`` carrying a native ``<title>`` tooltip and a
       hover / focus halo;
    6. a dotted Purple **proportional-bias trend line** (a linear fit of
       the differences) — the curve that turns a vague tilt into an
       unmistakable drift.

    Colour never carries meaning alone: the bias/limit trio is separated
    by dash pattern and thickness as well as hue, every reference line
    is labelled in words, and the signed story is told in the subtitle —
    so the figure survives greyscale and red-green colour blindness.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        The palette accessibility level. ``"universal"`` (default) is the
        colour-vision-safe standard; other levels (``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"``,
        ``"tritanopia"``) remap the hues via the sprezzature-colors engine.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    palette: Dict[str, str] = load_palette(accessibility)
    # Colour roles, chosen so each element reads on its own:
    #   points  — a calm neutral, so the reference lines are never
    #             fighting saturated dots for attention;
    #   bias    — Blue, solid and thick: the single most important line;
    #   loa     — Red, dashed: the "boundaries" of acceptable disagreement.
    #             Blue↔Red is the house diverging pair — it survives
    #             deuteranopia and greyscale, where red↔green collapses.
    #   band    — a faint Blue wash marking the 95 % agreement zone;
    #   trend   — Purple, a quiet secondary annotation for the drift.
    pointc = palette.get("Gray", "#8E8E93")
    biasc = palette.get("Blue", "#007AFF")
    loac = palette.get("Red", "#FF3B30")
    bandc = palette.get("Blue", "#007AFF")
    trend = palette.get("Purple", "#AF52DE")
    ink = "#1D1D1F"
    secondary = "#6E6E73"

    data = make_data()
    stats = agreement_stats(data)
    bias = round(stats["bias"], 1)
    loa_lo = round(stats["loa_lo"], 1)
    loa_hi = round(stats["loa_hi"], 1)

    # --- canvas geometry -----------------------------------------
    width = 1280
    height = 940
    m_left = 128
    m_right = 210          # extra room on the right for the value chips
    m_top = 232
    m_bottom = 132
    plot_x = m_left
    plot_y = m_top
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    # --- axis ranges (headroom so nothing clips) -----------------
    # x-window: the observed mean-pressure range, padded so nothing sits
    # on the axis. y-window kept symmetric so the zero rule sits near
    # mid-height and the downward tilt is obvious.
    x_min, x_max = 92.0, 188.0
    y_min, y_max = -22.0, 14.0
    x_ticks = [100, 120, 140, 160, 180]
    y_ticks = [-18, -12, -6, 0, 6, 12]

    def sx(v: float) -> float:
        """Map mean systolic pressure (mmHg) to an x pixel coordinate."""
        return plot_x + (v - x_min) / (x_max - x_min) * plot_w

    def sy(v: float) -> float:
        """Map a difference (mmHg) to a y pixel coordinate (y-down)."""
        return plot_y + (y_max - v) / (y_max - y_min) * plot_h

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    parts.append(svg_open(width, height, "ba-title", "ba-desc"))
    parts.append(
        '<title id="ba-title">Bland-Altman plot comparing a wrist '
        'blood-pressure monitor with an arm cuff</title>'
    )
    parts.append(
        f'<desc id="ba-desc">A Bland-Altman agreement plot of paired '
        f'systolic-pressure readings from a wrist monitor and an arm cuff. '
        f'The horizontal axis is the mean of the two readings; the vertical '
        f'axis is their difference (wrist minus arm). Each dot is one of '
        f'{len(data)} patients. A solid blue line marks the mean bias '
        f'({bias:+.1f} mmHg) and two dashed red lines mark the 95 percent '
        f'limits of agreement ({loa_lo:+.1f} to {loa_hi:+.1f} mmHg). The bias '
        f'sits below zero and the cloud tilts down to the right, so the wrist '
        f'tends to read low, and more so at higher pressure. '
        f'Illustrative data.</desc>'
    )

    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule below lives inside a media query). Under
    # prefers-contrast the three reference-line hues deepen together — bias
    # (blue), the two limits (red) and the drift trend (purple) — on their
    # strokes, and each value chip's border and mono text deepen to match, so
    # the trio stays legible for a low-vision reader. forced-colors is left to
    # the browser default: this figure already survives greyscale by design
    # (dash pattern + thickness + worded chips carry the distinction, not colour
    # alone), and the ~4-colour system palette could not preserve the point
    # cloud plus three reference hues.
    ref_series = {".ba-bias": biasc, ".ba-loa": loac, ".ba-trend": trend}
    ref_hc = leveled_colors(ref_series, "high-contrast")
    chip_rows = "".join(
        f"{sel}-chip{{stroke:{hexv} !important;}}{sel}-txt{{fill:{hexv} !important;}}"
        for sel, hexv in ref_hc.items()
    )
    adaptive = os_adaptive_style(ref_series, role="stroke", extra_contrast=chip_rows)
    parts.append(
        "<style>"
        ".pt{cursor:pointer}"
        ".pt .halo{opacity:0}"
        ".pt:hover .halo,.pt:focus .halo{opacity:1}"
        ".pt:focus{outline:none}"
        + adaptive
        # Very light gridlines are strokes the ink map misses; drop them to a
        # low-contrast dark grey on a dark ground. Point white halos stay light.
        + os_dark_style(extra='[stroke="#EEEEEE"]{stroke:#2A2A2C;}')
        + "</style>"
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="88" font-size="40" font-weight="700" '
        f'fill="{ink}">Do the wrist monitor and the arm cuff agree?</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="134" font-size="23" fill="{secondary}">'
        f'Bland-Altman plot. Each dot is one patient: its difference '
        f'(wrist − arm) against the two methods’ mean.</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="166" font-size="23" fill="{secondary}">'
        f'Solid line = mean bias ({bias:+.1f} mmHg). Dashed lines = 95% '
        f'limits of agreement ({loa_lo:+.1f} to {loa_hi:+.1f} mmHg).</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="198" font-size="23" fill="{secondary}">'
        f'Bias below zero, cloud tilting down to the right: the wrist reads '
        f'low, worse at higher pressure · illustrative data</text>'
    )

    # --- limits-of-agreement band (drawn first, under everything) -
    band_top = sy(loa_hi)
    band_bot = sy(loa_lo)
    parts.append(
        f'<rect x="{plot_x:.1f}" y="{band_top:.1f}" width="{plot_w:.1f}" '
        f'height="{band_bot - band_top:.1f}" fill="{bandc}" '
        f'fill-opacity="0.07"/>'
    )

    # --- gridlines (very light) ----------------------------------
    for t in x_ticks:
        gx = sx(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{plot_y:.1f}" x2="{gx:.1f}" '
            f'y2="{plot_y + plot_h:.1f}" stroke="#EEEEEE" stroke-width="1.4"/>'
        )
    for t in y_ticks:
        gy = sy(t)
        parts.append(
            f'<line x1="{plot_x:.1f}" y1="{gy:.1f}" x2="{plot_x + plot_w:.1f}" '
            f'y2="{gy:.1f}" stroke="#EEEEEE" stroke-width="1.4"/>'
        )

    # --- axes (L-shaped, ink) with ticks + Roboto-Mono labels ----
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
            f'y2="{ax_bottom + 7:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="{ax_bottom + 34:.1f}" font-size="20" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">{t}</text>'
        )
    for t in y_ticks:
        gy = sy(t)
        parts.append(
            f'<line x1="{plot_x - 7:.1f}" y1="{gy:.1f}" x2="{plot_x:.1f}" '
            f'y2="{gy:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{plot_x - 16:.1f}" y="{gy + 7:.1f}" font-size="20" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="end">{t:+d}</text>'
        )

    # --- axis titles ---------------------------------------------
    parts.append(
        f'<text x="{plot_x + plot_w / 2:.1f}" y="{ax_bottom + 78:.1f}" '
        f'font-size="23" fill="{ink}" text-anchor="middle">'
        f'Mean of the two methods — systolic pressure (mmHg)</text>'
    )
    ytitle_x = 48
    ytitle_y = plot_y + plot_h / 2
    parts.append(
        f'<text x="{ytitle_x:.1f}" y="{ytitle_y:.1f}" font-size="23" '
        f'fill="{ink}" text-anchor="middle" '
        f'transform="rotate(-90 {ytitle_x:.1f} {ytitle_y:.1f})">'
        f'Difference between methods — wrist − arm (mmHg)</text>'
    )

    # --- zero rule (dashed grey) + its caption -------------------
    zy = sy(0.0)
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{zy:.1f}" x2="{plot_x + plot_w:.1f}" '
        f'y2="{zy:.1f}" stroke="#B8B8BD" stroke-width="1.6" '
        f'stroke-dasharray="2 5"/>'
    )
    parts.append(
        f'<text x="{plot_x + 6:.1f}" y="{zy + 22:.1f}" font-size="18" '
        f'font-style="italic" fill="#9A9AA0">0 = perfect agreement</text>'
    )

    # --- the difference scatter ----------------------------------
    # One neutral dot per patient, each a focusable group with a native
    # tooltip and a hover / focus halo. A white keyline keeps each dot
    # crisp where the cloud overlaps — a bright keyline, never a dark ring.
    for rec in data:
        cx = sx(rec["mean"])
        cy = sy(rec["diff"])
        tip = (
            f'Mean {rec["mean"]:.0f} mmHg, wrist − arm {rec["diff"]:+.0f} mmHg'
        )
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
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7.5" fill="{pointc}" '
            f'fill-opacity="0.62" stroke="#FFFFFF" stroke-width="1.2"/>'
        )
        parts.append("</g>")

    # --- proportional-bias trend line (dotted Purple) ------------
    # A quiet secondary annotation: the least-squares fit of the
    # differences on the means, clipped to the x-window. Kept thin and
    # dotted so it signals the drift without competing with the bias /
    # limit lines that carry the primary read.
    slope, intercept = _linear_fit(
        [r["mean"] for r in data], [r["diff"] for r in data]
    )
    tx0, tx1 = x_min, x_max
    ty0 = slope * tx0 + intercept
    ty1 = slope * tx1 + intercept
    parts.append(
        f'<line class="ba-trend" x1="{sx(tx0):.1f}" y1="{sy(ty0):.1f}" '
        f'x2="{sx(tx1):.1f}" '
        f'y2="{sy(ty1):.1f}" stroke="{trend}" stroke-width="2.5" '
        f'stroke-dasharray="1 6" stroke-linecap="round" '
        f'stroke-opacity="0.9"/>'
    )

    # --- reference rules (bias + two limits) + value chips -------
    # Bias: solid Blue, thick — the single most important line. Limits:
    # dashed Red. Colour AND dash AND thickness carry the distinction, so
    # the trio is legible in greyscale and for colour-vision-deficient
    # readers. Each chip states the meaning in words plus the value, on a
    # white plate so the number stays crisp over the point cloud.
    ref_lines = [
        (loa_hi, loac, "+1.96 SD", f"{loa_hi:+.1f}", True, "ba-loa"),
        (bias, biasc, "Bias", f"{bias:+.1f}", False, "ba-bias"),
        (loa_lo, loac, "−1.96 SD", f"{loa_lo:+.1f}", True, "ba-loa"),
    ]
    for yval, col, name, num, dashed, cls in ref_lines:
        ry = sy(yval)
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        sw = 2.6 if dashed else 3.6
        parts.append(
            f'<line class="{cls}" x1="{plot_x:.1f}" y1="{ry:.1f}" '
            f'x2="{plot_x + plot_w:.1f}" '
            f'y2="{ry:.1f}" stroke="{col}" stroke-width="{sw}"{dash}/>'
        )
        # Right-hand value chip: a white plate carrying "<name>  <value>".
        chip = f"{name}  {num}"
        chip_x = plot_x + plot_w + 10
        parts.append(
            f'<rect class="{cls}-chip" x="{chip_x:.1f}" y="{ry - 17:.1f}" '
            f'width="{m_right - 22:.1f}" '
            f'height="34" rx="8" fill="#FFFFFF" stroke="{col}" '
            f'stroke-width="1.4"/>'
        )
        parts.append(
            f'<text class="{cls}-txt" x="{chip_x + 12:.1f}" y="{ry + 6:.1f}" '
            f'font-size="19" '
            f'font-family="Roboto Mono, monospace" font-weight="700" '
            f'fill="{col}">{xml_escape(chip)}</text>'
        )

    parts.append(fullscreen_control(width, height, mode, inset=240.0))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the Bland-Altman SVG to the canonical assets path (or --out)."""
    render_cli(
        __file__, "blandaltman", build_svg,
        description=(
            "Render the house-style Bland-Altman agreement plot "
            "(difference vs mean, bias + limits of agreement) to SVG."
        ),
    )


if __name__ == "__main__":
    main()

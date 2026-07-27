#!/usr/bin/env python3
"""
make_forest — a meta-analysis forest plot rendered as a hand-authored SVG.

A **forest plot** is the canonical way to display a meta-analysis: one
row per study, each showing that study's effect estimate as a point
whose *area* is proportional to the study's weight, flanked by a
horizontal whisker spanning its confidence interval (CI). A vertical
**null rule** marks the line of no effect (a ratio of 1.0 on the log
axis), so a whisker that crosses it is a study whose result is not
statistically distinguishable from "no effect". At the foot of the
column sits the **pooled diamond**: its centre is the random-effects
summary estimate and its width is the summary CI — the single number
the whole analysis exists to produce.

The generator builds the SVG string by hand (no matplotlib / seaborn /
plotly, no Vega) so the log-scale geometry, the weight-scaled boxes,
and the diamond are fully under our control, and matches the front-*
house style: Roboto, the Apple-ish palette, rounded corners, ink
``#1D1D1F``, secondary ``#6E6E73``, white background. Rows draw in with
a staggered pure-SMIL animation (whiskers extend, boxes fade up), and
every row and the diamond carry a native ``<title>`` tooltip plus a
:hover / :focus highlight — no JavaScript.

The fake scenario pools **eight randomised trials of a home
blood-pressure telemonitoring programme** on the odds of reaching a
blood-pressure target at twelve months. Most trials favour the
programme (odds ratio, OR, above 1), several individually cross the
null, and the pooled diamond lands cleanly to the right of 1.0 — the
textbook "the whole is more certain than any single part" story a
forest plot is built to tell.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/forest.svg``.

Usage
-----
::

    python make_forest.py               # writes the SVG next to the skill
    python make_forest.py --out /tmp/forest.svg

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List

# The house-style palette lives in _style.py, one directory up in scripts/.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open  # noqa: E402


# ------------------------------------------------------------------
# Communicative fake data
# ------------------------------------------------------------------
#: One entry per trial. ``label`` is the first-author-plus-year style
#: study handle a real forest plot uses; ``n`` is the trial's sample
#: size (drives the weight and hence the box area); ``or_`` is the
#: point estimate (odds ratio for reaching the blood-pressure target);
#: ``lo`` / ``hi`` are the bounds of its 95% confidence interval. All
#: values are illustrative but internally consistent (CIs widen as the
#: sample size shrinks, as real trials do).
STUDIES: List[Dict[str, object]] = [
    {"label": "Ashford 2016", "n": 512, "or_": 1.42, "lo": 1.08, "hi": 1.87},
    {"label": "Bhatt 2017", "n": 148, "or_": 1.95, "lo": 0.92, "hi": 4.13},
    {"label": "Costa 2018", "n": 806, "or_": 1.31, "lo": 1.06, "hi": 1.62},
    {"label": "Devi 2019", "n": 96, "or_": 0.88, "lo": 0.41, "hi": 1.89},
    {"label": "Eriksson 2020", "n": 1204, "or_": 1.58, "lo": 1.29, "hi": 1.93},
    {"label": "Fournier 2021", "n": 240, "or_": 1.12, "lo": 0.71, "hi": 1.77},
    {"label": "Grant 2022", "n": 372, "or_": 1.74, "lo": 1.14, "hi": 2.66},
    {"label": "Haddad 2023", "n": 188, "or_": 1.29, "lo": 0.78, "hi": 2.13},
]

#: The random-effects pooled summary (DerSimonian-Laird style), quoted
#: with its own 95% CI. Illustrative but consistent with the studies
#: above: a modest but clearly-positive overall effect.
POOLED: Dict[str, object] = {
    "label": "Pooled (random effects)",
    "or_": 1.44,
    "lo": 1.26,
    "hi": 1.64,
    "het": "I² = 34%",  # residual heterogeneity, quoted under the diamond
}


# ------------------------------------------------------------------
# Geometry helpers
# ------------------------------------------------------------------
def study_weight(n: int, ci_width_log: float) -> float:
    """Return an (illustrative) inverse-variance weight for a study.

    A real forest plot sizes each box by the study's inverse-variance
    weight. We approximate that here from the sample size and the width
    of the study's confidence interval on the log scale: larger, more
    precise trials get more weight (and a bigger box). The absolute
    scale does not matter — boxes are normalised to the heaviest study.

    Parameters
    ----------
    n : int
        Trial sample size.
    ci_width_log : float
        Width of the 95% confidence interval in natural-log units.

    Returns
    -------
    float
        A positive, unitless weight.
    """
    # Precision rises with n and falls with CI width; the exact form is
    # illustrative, chosen to give visually sensible box areas.
    return n / (ci_width_log**2 + 0.05)


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full forest-plot SVG string.

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
    blue = palette.get("Blue", "#007AFF")
    green = palette.get("Green", "#34C759")
    orange = palette.get("Orange", "#FF9500")
    ink = "#1D1D1F"
    secondary = "#6E6E73"
    # One uniform lift for every filled glyph: a white keyline, never
    # black. Squares, the pooled diamond and the CI point dots all share
    # it, so the marker treatment reads as a single consistent family.
    keyline = "#FFFFFF"

    # --- canvas geometry -----------------------------------------
    width = 720
    m_left = 24
    m_right = 24
    m_top = 92
    m_bottom = 70

    # Three columns: study label | forest panel | numeric estimate.
    label_w = 168
    est_w = 150
    gap = 18
    panel_x = m_left + label_w + gap
    panel_w = width - m_right - est_w - gap - panel_x
    est_x = panel_x + panel_w + gap

    row_h = 34
    n_rows = len(STUDIES)
    header_y = m_top
    first_row_y = header_y + 24
    diamond_y = first_row_y + n_rows * row_h + 14
    height = int(diamond_y + row_h + m_bottom)

    # --- log-scale x-axis ----------------------------------------
    # Odds ratios live naturally on a log axis: 0.5 and 2.0 are then
    # equidistant from the null at 1.0. Ticks span the data with a
    # little headroom.
    x_min, x_max = 0.4, 5.0
    lmin, lmax = math.log(x_min), math.log(x_max)
    ticks = [0.5, 1.0, 2.0, 4.0]

    def sx(v: float) -> float:
        """Map an odds-ratio value to an x pixel coordinate (log scale)."""
        return panel_x + (math.log(v) - lmin) / (lmax - lmin) * panel_w

    null_x = sx(1.0)

    # Box areas: normalise weights so the heaviest study fills a target
    # box; area ∝ weight, so the side ∝ sqrt(weight).
    weights = [
        study_weight(int(s["n"]), math.log(float(s["hi"])) - math.log(float(s["lo"])))
        for s in STUDIES
    ]
    w_max = max(weights)
    box_max = 15.0  # half-side of the largest box, in px
    # Floor the smallest box so a low-weight study still reads as a
    # square, not a stray dot; area stays ∝ weight above the floor.
    box_min = 6.0
    half_sides = [
        max(box_min, box_max * math.sqrt(w / w_max)) for w in weights
    ]

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    n = len(STUDIES)
    or_p = float(POOLED["or_"])
    lo_p = float(POOLED["lo"])
    hi_p = float(POOLED["hi"])
    parts.append(svg_open(width, height, "fp-title", "fp-desc"))
    parts.append(
        '<title id="fp-title">Forest plot: home blood-pressure telemonitoring '
        'raises the odds of reaching target</title>'
    )
    parts.append(
        f'<desc id="fp-desc">Meta-analysis forest plot of {n} randomised trials. '
        f'Each row shows a trial’s odds ratio for reaching the blood-pressure '
        f'target as a box (area ∝ study weight) with a 95% confidence-interval '
        f'whisker, on a logarithmic axis with a null rule at 1.0. The pooled '
        f'random-effects diamond is centred at {or_p:.2f} '
        f'(95% CI {lo_p:.2f} to {hi_p:.2f}), clearly to the right of the null, so '
        f'the programme increases the odds of reaching target overall.</desc>'
    )

    # prefers-reduced-motion guard + hover/focus highlight.
    #
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside an @media query and the class only
    # outranks the inline fill once the query matches). The three glyph classes
    # encode significance — green (CI clears the null), blue (CI crosses it),
    # orange (pooled diamond) — and deepen to their high-contrast hues under
    # prefers-contrast. forced=True is safe: the CI-vs-null relationship is
    # legible from geometry (does the whisker cross the null rule?) and the
    # pooled summary is a distinct diamond shape, so identity survives with no
    # colour.
    style_rows = [
        ".row{cursor:pointer}",
        ".row .whisker,.row .cap{stroke:" + secondary + ";stroke-width:1.6}",
        ".row:hover .whisker,.row:focus .whisker,"
        ".row:hover .cap,.row:focus .cap{stroke:" + secondary + ";stroke-width:2.4}",
        # On hover the glyph keeps its white keyline and just widens it —
        # no black outline ever appears.
        ".row:hover .box,.row:focus .box,"
        ".row:hover .diamond,.row:focus .diamond,"
        ".row:hover .dot,.row:focus .dot"
        "{stroke:" + keyline + ";stroke-width:2.4}",
        ".row:focus{outline:none}",
        ".row:hover .rowbg,.row:focus .rowbg{fill:#F5F5F7}",
        "@media (prefers-reduced-motion:reduce){"
        ".grow{animation:none}"
        "[data-anim]{opacity:1 !important}"
        "}",
    ]
    glyph_series = {".box-sig": green, ".box-cross": blue, ".diamond": orange}
    style_rows.append(os_adaptive_style(glyph_series, role="fill", forced=True))
    # Additive dark mode: flip paper + the two ink tiers (data hues untouched).
    style_rows.append(os_dark_style())
    parts.append("<style>" + "".join(style_rows) + "</style>")

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="36" font-size="18" font-weight="700" '
        f'fill="{ink}">Telemonitoring helps patients hit their BP target</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="58" font-size="12.5" fill="{secondary}">'
        f'Pooled odds ratio {or_p:.2f} (95% CI {lo_p:.2f}–{hi_p:.2f}) across '
        f'{n} randomised trials · {POOLED["het"]} · illustrative data</text>'
    )

    # --- column headers ------------------------------------------
    parts.append(
        f'<text x="{m_left}" y="{header_y}" font-size="11.5" font-weight="700" '
        f'fill="{secondary}">Trial</text>'
    )
    parts.append(
        f'<text x="{est_x}" y="{header_y}" font-size="11.5" font-weight="700" '
        f'fill="{secondary}">OR (95% CI)</text>'
    )
    # "Favours" annotations sit under the panel, flanking the null.
    # (drawn later with the axis so they align with the ticks)

    axis_top = header_y + 6
    axis_bottom = diamond_y + 20

    # --- null rule (drawn *beneath* the markers) -----------------
    # The line of no effect (odds ratio 1.0). Drawn here, before the rows,
    # so every marker box and the diamond sit cleanly *on top* of it with
    # their white keyline intact — the null line never cuts a dark stroke
    # across a glyph. The per-row hover backgrounds are transparent by
    # default (see .rowbg), so nothing occludes this line.
    parts.append(
        f'<line x1="{null_x:.1f}" y1="{axis_top:.1f}" x2="{null_x:.1f}" '
        f'y2="{axis_bottom:.1f}" stroke="{secondary}" stroke-width="1.4"/>'
    )

    # --- study rows ----------------------------------------------
    for i, (s, half, w) in enumerate(zip(STUDIES, half_sides, weights)):
        cy = first_row_y + i * row_h + row_h / 2
        cx = sx(float(s["or_"]))
        x_lo = sx(float(s["lo"]))
        x_hi = sx(float(s["hi"]))
        pct = round(100 * w / sum(weights))

        crosses = float(s["lo"]) <= 1.0 <= float(s["hi"])
        sig_note = "crosses the null" if crosses else "significant"
        tip = (
            f'{s["label"]}: OR {float(s["or_"]):.2f} '
            f'(95% CI {float(s["lo"]):.2f}–{float(s["hi"]):.2f}), '
            f'weight {pct}% — {sig_note}'
        )

        parts.append(
            f'<g class="row" tabindex="0" role="img" aria-label="{tip}">'
        )
        parts.append(f"<title>{tip}</title>")
        # Full-width hover band for a comfortable target.
        parts.append(
            f'<rect class="rowbg" x="{m_left - 6:.1f}" y="{cy - row_h / 2:.1f}" '
            f'width="{width - m_left - m_right + 12:.1f}" height="{row_h:.1f}" '
            f'rx="7" fill="none"/>'
        )

        # Study label (left column).
        parts.append(
            f'<text x="{m_left}" y="{cy + 4:.1f}" font-size="13" fill="{ink}">'
            f'{s["label"]}</text>'
        )

        # Whisker (CI) at full width — drawn in its finished state so the
        # static figure is complete (no animate-from-zero that blanks the plot).
        parts.append(
            f'<line class="whisker" x1="{x_lo:.1f}" y1="{cy:.1f}" '
            f'x2="{x_hi:.1f}" y2="{cy:.1f}"/>'
        )
        # End caps.
        for xend in (x_lo, x_hi):
            parts.append(
                f'<line class="cap" x1="{xend:.1f}" y1="{cy - 4:.1f}" '
                f'x2="{xend:.1f}" y2="{cy + 4:.1f}"/>'
            )

        # Weight-scaled box, centred on the point estimate. Every study
        # marker is the SAME glyph (a rounded square) with the SAME
        # treatment: a solid house-palette fill and a uniform white
        # keyline for lift — never a black outline. Colour alone encodes
        # significance (green = CI clears the null, blue = CI crosses it),
        # so light and heavy studies stay one consistent family instead
        # of degenerating into stray "dots".
        sig = float(s["lo"]) > 1.0
        box_fill = green if sig else blue
        box_cat = "box-sig" if sig else "box-cross"
        parts.append(
            f'<rect class="box {box_cat}" x="{cx - half:.1f}" y="{cy - half:.1f}" '
            f'width="{2 * half:.1f}" height="{2 * half:.1f}" rx="2.5" '
            f'fill="{box_fill}" stroke="{keyline}" stroke-width="1.5" '
            f'stroke-linejoin="round"/>'
        )

        # Numeric estimate (right column), Roboto Mono for alignment.
        est = (
            f'{float(s["or_"]):.2f} '
            f'({float(s["lo"]):.2f}–{float(s["hi"]):.2f})'
        )
        parts.append(
            f'<text x="{est_x}" y="{cy + 4:.1f}" font-size="12" '
            f'font-family="Roboto Mono, monospace" fill="{ink}">{est}</text>'
        )
        parts.append("</g>")

    # --- pooled diamond ------------------------------------------
    dy = diamond_y + row_h / 2
    dcx = sx(or_p)
    dlo = sx(lo_p)
    dhi = sx(hi_p)
    dh = 9.0  # half-height of the diamond
    diamond_pts = (
        f"{dlo:.1f},{dy:.1f} {dcx:.1f},{dy - dh:.1f} "
        f"{dhi:.1f},{dy:.1f} {dcx:.1f},{dy + dh:.1f}"
    )
    pooled_tip = (
        f'Pooled random-effects OR {or_p:.2f} '
        f'(95% CI {lo_p:.2f}–{hi_p:.2f}), {POOLED["het"]}'
    )
    parts.append(f'<g class="row" tabindex="0" role="img" aria-label="{pooled_tip}">')
    parts.append(f"<title>{pooled_tip}</title>")
    parts.append(
        f'<rect class="rowbg" x="{m_left - 6:.1f}" y="{diamond_y:.1f}" '
        f'width="{width - m_left - m_right + 12:.1f}" height="{row_h:.1f}" '
        f'rx="7" fill="none"/>'
    )
    parts.append(
        f'<text x="{m_left}" y="{dy + 4:.1f}" font-size="13" font-weight="700" '
        f'fill="{ink}">{POOLED["label"]}</text>'
    )
    # Pooled diamond: same treatment as the study squares — a solid
    # house-palette fill (orange sets the summary apart from the green /
    # blue study boxes) lifted by the SAME uniform white keyline, never a
    # black stroke.
    parts.append(
        f'<polygon class="diamond" points="{diamond_pts}" fill="{orange}" '
        f'stroke="{keyline}" stroke-width="1.5" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<text x="{est_x}" y="{dy + 4:.1f}" font-size="12" font-weight="700" '
        f'font-family="Roboto Mono, monospace" fill="{ink}">'
        f'{or_p:.2f} ({lo_p:.2f}–{hi_p:.2f})</text>'
    )
    parts.append("</g>")

    # --- x-axis (log ticks) --------------------------------------
    axis_y = axis_bottom + 8
    parts.append(
        f'<line x1="{sx(x_min):.1f}" y1="{axis_y:.1f}" x2="{sx(x_max):.1f}" '
        f'y2="{axis_y:.1f}" stroke="{ink}" stroke-width="1"/>'
    )
    for t in ticks:
        px = sx(t)
        parts.append(
            f'<line x1="{px:.1f}" y1="{axis_y:.1f}" x2="{px:.1f}" '
            f'y2="{axis_y + 5:.1f}" stroke="{ink}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{axis_y + 19:.1f}" font-size="11" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">{t:g}</text>'
        )
    parts.append(
        f'<text x="{(sx(x_min) + sx(x_max)) / 2:.1f}" y="{axis_y + 38:.1f}" '
        f'font-size="12" fill="{ink}" text-anchor="middle">'
        f'Odds ratio for reaching BP target (log scale, higher is better)</text>'
    )

    # --- "favours" annotations flanking the null -----------------
    fav_y = axis_top - 6
    parts.append(
        f'<text x="{null_x - 8:.1f}" y="{fav_y:.1f}" font-size="10.5" '
        f'fill="{secondary}" text-anchor="end">← favours usual care</text>'
    )
    parts.append(
        f'<text x="{null_x + 8:.1f}" y="{fav_y:.1f}" font-size="10.5" '
        f'fill="{secondary}">favours telemonitoring →</text>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the forest-plot SVG to the canonical assets path (or --out)."""
    render_cli(__file__, "forest", build_svg, description="Render the forest-plot SVG.")


if __name__ == "__main__":
    main()

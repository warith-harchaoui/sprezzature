#!/usr/bin/env python3
"""
make_dumbbell — a dumbbell (DNA / connected-dot) plot as hand-authored SVG.

A **dumbbell plot** compares two states of the same categories by
drawing, for each row, the two values as a pair of dots joined by a
short connecting segment — the "dumbbell". The length of the segment
*is* the change, so the eye reads the gap directly without arithmetic.
It is the cleanest way to show "before vs after" or "group A vs group B"
across many categories at once, and it beats a grouped bar chart because
the bars there force the reader to mentally subtract two heights while
here the distance is the message.

This generator builds the SVG string by hand (no matplotlib / seaborn /
plotly, no Vega) so the sorting-by-gap, the endpoint value labels, and
the side-aware label harmony are fully under our control, and matches the
sprezzature-* house style: Roboto, the Apple-ish palette, rounded corners, ink
``#1D1D1F``, secondary ``#6E6E73``, white background.

The fake scenario is a **gender pay gap by role** at a mid-size company:
median hourly pay for women and for men across ten job families, sorted so
the widest gap sits on top. Each row shows the two medians as dots joined
by a segment whose length is the gap; the gap in currency is printed on
the segment, and the two endpoint pay figures sit just outside their dots.
A faint reference band marks the company-wide median so a reader sees
which roles pull the average up or down. The figure is **static**: a
dumbbell already shows every gap in one still, so no motion is added — it
would reveal nothing the reader cannot already see. Each row carries a
native ``<title>`` tooltip and a :hover / :focus highlight; no JavaScript.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/dumbbell.svg``.

Usage
-----
::

    python make_dumbbell.py               # writes the SVG next to the skill
    python make_dumbbell.py --out /tmp/dumbbell.svg

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

# The house-style palette and the shared XML escaper live in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _labels import label_cell, readable_on_white  # noqa: E402
from _render import render_cli  # noqa: E402
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# Communicative fake data
# ------------------------------------------------------------------
#: One entry per job family. ``role`` is the label; ``women`` and ``men``
#: are the median hourly pay (in dollars) for each group. Values are
#: illustrative but internally consistent — men out-earn women in every
#: role here, and the gap is widest in the highest-paid roles, the
#: pattern most real pay audits surface. The rows are *unsorted* on
#: purpose; :func:`build_svg` sorts them by gap so the story is ordered.
ROLES: List[Dict[str, object]] = [
    {"role": "Sales director",       "women": 58.20, "men": 71.40},
    {"role": "Software engineer",    "women": 52.10, "men": 60.30},
    {"role": "Product manager",      "women": 55.40, "men": 65.90},
    {"role": "Data scientist",       "women": 51.80, "men": 58.20},
    {"role": "Marketing lead",       "women": 44.60, "men": 50.10},
    {"role": "Financial analyst",    "women": 41.30, "men": 47.80},
    {"role": "UX designer",          "women": 43.90, "men": 47.20},
    {"role": "Customer success",     "women": 33.70, "men": 37.10},
    {"role": "Recruiter",            "women": 34.20, "men": 36.40},
    {"role": "Support specialist",   "women": 28.90, "men": 30.50},
]


def company_median(rows: List[Dict[str, object]]) -> float:
    """Return the pooled median hourly pay across both groups.

    Used only for the faint reference band, so a reader can see which
    roles sit above or below the company-wide middle. The pooled median
    is the mean of the two group medians for each role, averaged — an
    illustrative summary, not a rigorous population median.

    Parameters
    ----------
    rows : list of dict
        The role records, each carrying ``women`` and ``men`` pay.

    Returns
    -------
    float
        A single reference pay value, in dollars per hour.
    """
    mids = [(float(r["women"]) + float(r["men"])) / 2.0 for r in rows]
    return sum(mids) / len(mids)


# ------------------------------------------------------------------
# SVG assembly
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full dumbbell-plot SVG string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"`` / ``"external"`` / ``"static"``). Defaults to
        ``"self-contained"``. Wired through the ``--mode`` CLI flag by
        :func:`_render.render_cli`.
    accessibility : str, optional
        Palette accessibility level passed to :func:`_style.load_palette`
        (``"universal"`` default, plus ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` and ``"tritanopia"``). Wired
        through the ``--accessibility`` CLI flag by :func:`_render.render_cli`.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    palette: Dict[str, str] = load_palette(accessibility)
    # Purple for women, Teal for men: two distinct hues, neither
    # red-vs-green (CVD-safe), each carrying an explicit legend label so
    # the encoding never rides on colour alone.
    women_col = palette.get("Purple", "#AF52DE")
    men_col = palette.get("Teal", "#5AC8FA")
    # The bright teal reads fine as a *filled disk* on white, but it is far too
    # pale to use as *text* (luminance ~0.50). For the men-side value numbers we
    # darken it just enough to stay legible while keeping its teal identity, so
    # the two value columns have matched contrast (label harmony). Women's purple
    # is already dark enough and passes through unchanged.
    men_text_col = readable_on_white(men_col)
    ink = "#1D1D1F"
    secondary = "#6E6E73"
    band = "#F5F5F7"

    # Sort by gap, widest on top — the ordering *is* the argument.
    rows = sorted(ROLES, key=lambda r: float(r["men"]) - float(r["women"]), reverse=True)

    # --- canvas geometry -----------------------------------------
    # Poster-scale panel. Left gutter holds the role label; the plot
    # panel holds the dumbbells; a right gutter is reserved so the
    # rightmost value label never clips.
    width = 1280
    m_left = 70
    m_right = 70
    m_top = 208
    m_bottom = 118

    label_w = 300           # left column: role names
    plot_x = m_left + label_w
    plot_w = width - m_right - plot_x

    row_h = 74
    n_rows = len(rows)
    first_row_cy = m_top + row_h / 2
    plot_bottom = m_top + n_rows * row_h
    height = int(plot_bottom + m_bottom)

    # --- value axis (dollars per hour) ---------------------------
    # Round headroom so the widest dumbbell and its outer value label
    # both sit comfortably inside the panel.
    x_min, x_max = 24.0, 76.0
    ticks = [30, 40, 50, 60, 70]

    def sx(v: float) -> float:
        """Map a pay value (dollars/hour) to an x pixel coordinate."""
        return plot_x + (v - x_min) / (x_max - x_min) * plot_w

    ref = company_median(rows)

    # Dot radius, big enough to read at gallery scale.
    r = 15.0

    # Aggregate for the subtitle: mean gap in percentage points.
    gaps_pct = [
        100.0 * (float(r_["men"]) - float(r_["women"])) / float(r_["men"])
        for r_ in rows
    ]
    mean_gap_pct = round(sum(gaps_pct) / len(gaps_pct))
    widest = rows[0]
    widest_gap = float(widest["men"]) - float(widest["women"])

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    parts.append(svg_open(width, height, "db-title", "db-desc"))
    parts.append(
        '<title id="db-title">Gender pay gap by role: men out-earn women in '
        'every job family</title>'
    )
    parts.append(
        f'<desc id="db-desc">Dumbbell plot of median hourly pay for women '
        f'(purple) and men (teal) across {n_rows} roles, sorted by the size of '
        f'the gap. Each row joins the two medians with a segment whose length is '
        f'the gap. Men earn more in every role; the gap averages '
        f'{mean_gap_pct}% and is widest for {xml_escape(str(widest["role"]))} at '
        f'${widest_gap:.0f} per hour. Illustrative data.</desc>'
    )

    # Hover / focus highlight only — the figure is static, so there is no
    # motion to guard with prefers-reduced-motion.
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside an @media query — the class only
    # takes over the inline fill once the query matches). The two states
    # (Women = purple, Men = teal) deepen to their high-contrast hues under
    # prefers-contrast, on the dots and their matched value numbers. forced=True
    # is safe: each state keeps a fixed side per row (women left, men right) and
    # an always-visible legend label, so identity survives with no colour.
    style_rows = [
        ".row{cursor:pointer}",
        f".row .seg{{stroke:{secondary};stroke-width:5;stroke-linecap:round}}",
        ".row:hover .rowbg,.row:focus .rowbg{fill:#F0F0F2}",
        f".row:hover .seg,.row:focus .seg{{stroke:{ink}}}",
        ".row:hover .dot,.row:focus .dot{stroke:#1D1D1F;stroke-width:2}",
        ".row:focus{outline:none}",
    ]
    women_series = {".mk-women": women_col}
    men_series = {".mk-men": men_col}
    style_rows.append(os_adaptive_style(women_series, role="fill", forced=True))
    style_rows.append(os_adaptive_style(men_series, role="fill", forced=True))
    # Additive dark mode: flip paper + the two ink tiers (data hues untouched).
    style_rows.append(os_dark_style())
    parts.append("<style>" + "".join(style_rows) + "</style>")

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="86" font-size="40" font-weight="700" '
        f'fill="{ink}">Men out-earn women in every role</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="132" font-size="23" fill="{secondary}">'
        f'Median hourly pay, women vs men · the gap averages {mean_gap_pct}% and '
        f'widens with seniority · illustrative</text>'
    )

    # --- legend (two states) -------------------------------------
    # Pure-fill disks, labels in ink to the right — no dark ring, no halo.
    leg_y = 170
    leg_x = m_left
    lr = 11.0
    parts.append(
        f'<circle class="mk-women" cx="{leg_x + lr:.1f}" cy="{leg_y:.1f}" '
        f'r="{lr:.1f}" fill="{women_col}"/>'
    )
    parts.append(
        f'<text x="{leg_x + 2 * lr + 12:.1f}" y="{leg_y + 7:.1f}" font-size="22" '
        f'fill="{ink}">Women</text>'
    )
    leg_x2 = leg_x + 150
    parts.append(
        f'<circle class="mk-men" cx="{leg_x2 + lr:.1f}" cy="{leg_y:.1f}" '
        f'r="{lr:.1f}" fill="{men_col}"/>'
    )
    parts.append(
        f'<text x="{leg_x2 + 2 * lr + 12:.1f}" y="{leg_y + 7:.1f}" font-size="22" '
        f'fill="{ink}">Men</text>'
    )

    # --- company-median reference band ---------------------------
    # A soft grey band (not a lone dashed rule) marks the pooled median, drawn
    # first so the dumbbells sit on top. The band gives every row a shared
    # anchor and reads unmistakably as "reference", without competing for ink.
    # Its width is a fixed visual cushion, so it stays a band even though the
    # underlying value is a single point.
    ref_x = sx(ref)
    band_half = 9.0
    parts.append(
        f'<rect x="{ref_x - band_half:.1f}" y="{m_top - 6:.1f}" '
        f'width="{2 * band_half:.1f}" height="{plot_bottom - m_top + 12:.1f}" '
        f'rx="6" fill="{band}"/>'
    )
    parts.append(
        f'<line x1="{ref_x:.1f}" y1="{m_top - 6:.1f}" x2="{ref_x:.1f}" '
        f'y2="{plot_bottom + 6:.1f}" stroke="{secondary}" stroke-width="1.4" '
        f'stroke-dasharray="4 7"/>'
    )
    # Label sits above the plot, right-aligned to the band so it never crowds
    # the top row's gap chip.
    parts.append(
        f'<text x="{ref_x:.1f}" y="{m_top - 16:.1f}" font-size="17" '
        f'fill="{secondary}" text-anchor="middle">Company median '
        f'${ref:.0f}</text>'
    )

    # --- x-axis gridlines (very light) ---------------------------
    for t in ticks:
        gx = sx(t)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{m_top - 4:.1f}" x2="{gx:.1f}" '
            f'y2="{plot_bottom + 4:.1f}" stroke="{band}" stroke-width="1.4"/>'
        )

    # --- the dumbbells -------------------------------------------
    for i, rec in enumerate(rows):
        cy = first_row_cy + i * row_h
        w_val = float(rec["women"])
        m_val = float(rec["men"])
        xw = sx(w_val)
        xm = sx(m_val)
        gap = m_val - w_val
        gap_pct = round(100.0 * gap / m_val)
        role = xml_escape(str(rec["role"]))

        tip = (
            f'{role}: women ${w_val:.2f}/h vs men ${m_val:.2f}/h — '
            f'gap ${gap:.2f} ({gap_pct}%)'
        )

        parts.append(f'<g class="row" tabindex="0" role="img" aria-label="{tip}">')
        parts.append(f"<title>{tip}</title>")

        # Full-width hover target. Transparent at rest so it never paints over
        # the company-median reference band underneath; it only fills on
        # :hover / :focus (see the stylesheet).
        parts.append(
            f'<rect class="rowbg" x="{m_left - 14:.1f}" y="{cy - row_h / 2 + 4:.1f}" '
            f'width="{width - m_left - m_right + 28:.1f}" '
            f'height="{row_h - 8:.1f}" rx="12" fill="none" pointer-events="all"/>'
        )

        # Role label (left column), right-aligned to the panel edge so
        # the names form a clean rule against the dumbbells.
        parts.append(
            f'<text x="{plot_x - 26:.1f}" y="{cy + 8:.1f}" font-size="23" '
            f'fill="{ink}" text-anchor="end">{role}</text>'
        )

        # Connecting segment (the dumbbell bar) — drawn in its finished
        # state so the static figure is complete.
        parts.append(
            f'<line class="seg" x1="{xw:.1f}" y1="{cy:.1f}" x2="{xm:.1f}" '
            f'y2="{cy:.1f}"/>'
        )

        # Endpoint dots. Pure fills, thin white keyline so a dot stays
        # crisp where it meets the segment — never a dark ring.
        parts.append(
            f'<circle class="dot mk-women" cx="{xw:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'fill="{women_col}" stroke="#FFFFFF" stroke-width="2"/>'
        )
        parts.append(
            f'<circle class="dot mk-men" cx="{xm:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'fill="{men_col}" stroke="#FFFFFF" stroke-width="2"/>'
        )

        # Endpoint value labels — side-aware harmony: the lower value
        # (women, on the left) is labelled to the LEFT of its dot; the
        # higher value (men, on the right) to the RIGHT of its dot. Each
        # in its own hue so the number ties back to the legend without a
        # second lookup.
        parts.append(
            f'<text class="mk-women" x="{xw - r - 12:.1f}" y="{cy + 7:.1f}" '
            f'font-size="20" font-family="Roboto Mono, monospace" fill="{women_col}" '
            f'font-weight="500" text-anchor="end">${w_val:.0f}</text>'
        )
        parts.append(
            f'<text class="mk-men" x="{xm + r + 12:.1f}" y="{cy + 7:.1f}" '
            f'font-size="20" font-family="Roboto Mono, monospace" fill="{men_text_col}" '
            f'font-weight="500">${m_val:.0f}</text>'
        )

        # Gap chip, centred over the segment and lifted just above it so it
        # never sits colour-on-colour with the bar. Routed through the shared
        # ``label_cell`` commons as a ``ghost`` pill (white fill, coloured
        # hairline, coloured text) so every "cell around text" in the gallery
        # is the same component. The chip is tinted teal because the gap is the
        # men-minus-women surplus — the number ties to the higher endpoint.
        mid_x = (xw + xm) / 2.0
        chip_y = cy - 27
        parts.append(
            label_cell(
                mid_x,
                chip_y,
                f"+${gap:.0f}",
                men_text_col,
                variant="ghost",
                size=17.0,
                weight="700",
                anchor="middle",
            )
        )

        parts.append("</g>")

    # --- x-axis (value scale) ------------------------------------
    axis_y = plot_bottom + 22
    parts.append(
        f'<line x1="{sx(x_min):.1f}" y1="{axis_y:.1f}" x2="{sx(x_max):.1f}" '
        f'y2="{axis_y:.1f}" stroke="{ink}" stroke-width="1.4"/>'
    )
    for t in ticks:
        px = sx(t)
        parts.append(
            f'<line x1="{px:.1f}" y1="{axis_y:.1f}" x2="{px:.1f}" '
            f'y2="{axis_y + 6:.1f}" stroke="{ink}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{axis_y + 30:.1f}" font-size="19" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">${t}</text>'
        )
    parts.append(
        f'<text x="{(sx(x_min) + sx(x_max)) / 2:.1f}" y="{axis_y + 62:.1f}" '
        f'font-size="21" fill="{ink}" text-anchor="middle">'
        f'Median hourly pay (US dollars)</text>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the dumbbell-plot SVG to the canonical assets path (or --out)."""
    render_cli(__file__, "dumbbell", build_svg, description="Render the dumbbell-plot SVG.")


if __name__ == "__main__":
    main()

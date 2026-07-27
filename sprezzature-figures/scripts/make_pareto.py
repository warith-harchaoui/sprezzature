#!/usr/bin/env python3
"""
make_pareto — a Pareto chart as hand-authored SVG.

The **Pareto chart** is the classic quality-engineering figure that
separates the *vital few* causes from the *trivial many*. Sorted bars
give each cause's share of the total; a cumulative-percentage line
climbs left-to-right toward 100 %; and an 80 % reference line marks the
textbook 80/20 threshold. Where the cumulative line first clears 80 %
is the boundary between the handful of causes worth fixing and the long
tail that is not.

The scenario is a week of customer-support tickets for a small software
product. Every ticket is tagged with the one reason it was opened, and
the chart answers the question a support lead asks on Monday morning:
*if I could fix only a handful of root causes, which ones would clear
most of the backlog?* The takeaway the figure is built to state: **three
or four reasons drive ~80 % of the tickets** — the bars left of the
crossing are tinted as the "vital few", the rest fade to grey, and the
crossing is annotated with the exact count and percentage.

This generator builds the SVG by hand (no matplotlib / seaborn / plotly,
no Vega) so the two coordinated scales — a left percentage axis for the
bar shares and a right percentage axis for the cumulative curve — sit
under our own control, along with the vital-few tint, the direct curve
label, and the 80 % guide. Marks are distinguished by **more than
hue**: the bars are a solid fill split blue↔grey (survives greyscale
and deuteranopia), while the cumulative curve is a distinct dashed-free
orange *line* carrying round markers and a direct "cumulative %" label,
so bar and line never rely on colour alone to be told apart. It matches
the sprezzature-* house style: Roboto, the Apple-ish palette, rounded corners,
ink ``#1D1D1F``, secondary ``#6E6E73``, white background, white
keylines.

Each bar and each curve marker carries a native ``<title>`` tooltip and
a :hover / :focus emphasis; no JavaScript beyond the shared fullscreen
control.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/pareto.svg``.

Usage
-----
::

    python make_pareto.py            # writes next to the skill
    python make_pareto.py --out /tmp/pareto.svg
    python make_pareto.py --mode static   # no fullscreen button

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

# House-style helpers live alongside this script in scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402


# The Pareto threshold: the cumulative share that splits the vital few
# from the trivial many. 80 % is the textbook 80/20 line.
_PARETO_THRESHOLD = 80.0

# ------------------------------------------------------------------
# Communicative real-sounding data — one week of support tickets, tagged
# by the single reason each was opened. Counts, not "Category A/B/C".
# These are already the raw tallies; the generator sorts them, converts
# to shares, and computes the cumulative curve.
# ------------------------------------------------------------------
_TICKETS: List[Dict[str, Any]] = [
    {"reason": "Login & password resets", "count": 412},
    {"reason": "Billing & invoice errors", "count": 296},
    {"reason": "Sync fails across devices", "count": 187},
    {"reason": "Slow / timing-out pages", "count": 96},
    {"reason": "Export to PDF broken", "count": 74},
    {"reason": "Notifications not arriving", "count": 51},
    {"reason": "Mobile app crashes", "count": 38},
    {"reason": "Feature requests", "count": 29},
    {"reason": "Everything else", "count": 22},
]


def make_data(tickets: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Sort the reasons, convert to shares, and build the cumulative curve.

    Sorts the tagged tickets from most to least frequent, turns each
    count into a percentage of the week's total, and walks the sorted
    list to accumulate the running share. Also finds the first reason at
    which the cumulative share crosses the 80 % Pareto threshold — the
    boundary the annotation and the vital-few tint hang off.

    Parameters
    ----------
    tickets : list of dict, optional
        Records ``{"reason": str, "count": int}``. Defaults to the
        module's one-week support-ticket tally.

    Returns
    -------
    dict
        ``{"rows": [...], "total": int, "crossing": {...}}`` where each
        row carries ``reason``, ``count``, ``share`` (percent of total),
        ``cum`` (cumulative percent), ``rank`` (1-based, left-to-right),
        and ``vital`` (True until the cumulative curve clears 80 %).
        ``crossing`` describes the reason at which 80 % is first reached.
    """
    src = tickets if tickets is not None else _TICKETS

    # Rank the reasons tallest-first; that ordering *is* the Pareto x-axis.
    ordered = sorted(src, key=lambda r: int(r["count"]), reverse=True)
    total = sum(int(r["count"]) for r in ordered)

    rows: List[Dict[str, Any]] = []
    running = 0
    n_vital = 0
    crossing: Dict[str, Any] = {}
    for i, r in enumerate(ordered):
        count = int(r["count"])
        running += count
        share = 100.0 * count / total
        cum = 100.0 * running / total
        # A reason belongs to the "vital few" until the cumulative curve
        # has cleared the threshold. The crossing reason itself is the
        # last one counted as vital (it is what tips us over 80 %).
        was_below = (running - count) / total * 100.0 < _PARETO_THRESHOLD
        vital = was_below
        if vital:
            n_vital += 1
        rows.append({
            "reason": str(r["reason"]),
            "count": count,
            "share": round(share, 2),
            "cum": round(cum, 2),
            "rank": i + 1,
            "vital": vital,
        })
        # The first row that lifts the cumulative share to/over 80 %.
        if not crossing and cum >= _PARETO_THRESHOLD:
            crossing = {
                "reason": str(r["reason"]),
                "rank": i + 1,
                "cum": round(cum, 2),
                "n_vital": n_vital,
                "cum_count": running,
            }

    return {"rows": rows, "total": total, "crossing": crossing}


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full Pareto-chart SVG string.

    Draws, back to sprezzature: the light plot band and gridlines, the 80 %
    reference rule with its label, the sorted bars (vital few in blue,
    trivial many in grey — a split that survives greyscale and
    deuteranopia), the cumulative-percentage line with round markers,
    the emphasised crossing marker and its call-out, the two percentage
    axes (left for bar shares, right for the cumulative curve, each
    labelled so the dual axis is never ambiguous), and the x-axis reason
    labels.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``; the button never alters the raster.
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
    data = make_data()
    rows = data["rows"]
    crossing = data["crossing"]
    total = data["total"]

    palette: Dict[str, str] = load_palette(accessibility)
    # Two hues carry meaning — Blue for the vital-few bars, Orange for the
    # cumulative curve (and its markers, so the crossing dot belongs to the
    # curve). Everything else is one neutral: a single muted grey for the
    # trivial-many bars, and the house secondary ink for reference + labels.
    vital_c = palette.get("Blue", "#007AFF")   # the vital few — the hero bars
    trivial_c = "#C7CAD1"                       # the trivial many — one muted grey
    line_c = palette.get("Orange", "#FF9500")  # cumulative curve + its markers
    ref_c = "#6E6E73"                           # 80 % reference — house secondary ink
    ink = "#1D1D1F"                             # primary ink for headings + call-out
    secondary = "#6E6E73"
    band = "#F5F5F7"

    n = len(rows)
    n_vital = int(crossing.get("n_vital", 0)) if crossing else 0

    # --- canvas geometry -----------------------------------------
    width = 1280
    height = 920
    m_left = 150
    m_right = 96
    m_top = 210
    m_bottom = 230
    plot_x = m_left
    plot_y = m_top
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom
    ax_bottom = plot_y + plot_h

    # Both scales are percentages 0..100, sharing one 0..106 pixel range so
    # the last cumulative marker (100 %) never kisses the top frame. The bars
    # read against the *left* axis, the curve against the *right* axis; both
    # are 0..100 %, so this is an honest twin-percentage scale, not a
    # misleading dual axis — the two labelled axes make that explicit.
    y_min, y_max = 0.0, 106.0
    y_ticks = [0, 20, 40, 60, 80, 100]

    def sy(v: float) -> float:
        """Map a percentage (0..100) to a y pixel coordinate (y-down)."""
        return plot_y + (y_max - v) / (y_max - y_min) * plot_h

    # Even category slots across the plot; each bar sits centred in its slot.
    slot_w = plot_w / n

    def slot_center(i: int) -> float:
        """Return the x pixel coordinate at the centre of category slot ``i``."""
        return plot_x + (i + 0.5) * slot_w

    bar_w = slot_w * 0.62

    parts: List[str] = []

    # --- SVG root + accessible description ------------------------
    parts.append(svg_open(width, height, "pa-title", "pa-desc"))
    parts.append(
        '<title id="pa-title">A few support-ticket reasons drive most of '
        'the weekly backlog</title>'
    )
    cross_cum = round(crossing["cum"]) if crossing else 0
    cross_count = int(crossing["cum_count"]) if crossing else 0
    parts.append(
        f'<desc id="pa-desc">Pareto chart of one week of customer-support '
        f'tickets ({total:,} total, illustrative). Bars show each reason’s '
        f'share of tickets, sorted tallest-first against the left percentage '
        f'axis; the {n_vital} tallest are tinted blue as the “vital few” '
        f'and the remaining {n - n_vital} fade to grey as the “trivial '
        f'many”. An orange line traces the cumulative share against the '
        f'right percentage axis, climbing to 100 %. The dashed 80 % Pareto '
        f'line marks the 80/20 threshold: the cumulative curve first clears '
        f'it at reason {n_vital}, so {n_vital} reasons account for '
        f'{cross_cum} % of tickets ({cross_count:,} of {total:,}). '
        f'Illustrative figures.</desc>'
    )

    # Static figure: hover / focus emphasis only, no motion to guard.
    # OS-adaptive overrides (additive; the default render is byte-identical
    # because every rule lives inside a media query). Under prefers-contrast the
    # vital-few bars deepen to a higher-contrast Blue (fill), and the cumulative
    # line + its markers deepen to a higher-contrast Orange (both stroke for the
    # line and fill for the markers). The trivial-many grey bars and the neutral
    # reference / label inks are left untouched.
    parts.append(
        "<style>"
        ".bar{cursor:pointer}"
        ".bar rect{transition:opacity .12s}"
        ".bar:hover rect,.bar:focus rect{opacity:.82}"
        ".bar:focus{outline:none}"
        ".pt{cursor:pointer}"
        ".pt .halo{opacity:0}"
        ".pt:hover .halo,.pt:focus .halo{opacity:1}"
        ".pt:focus{outline:none}"
        + os_adaptive_style({".pa-vital": vital_c}, role="fill")
        + os_adaptive_style({".pa-line": line_c}, role="both")
        # Additive OS dark mode: dark paper + light ink (default ink_map); the
        # vital-few bar hue and the cumulative line are data, left alone. The
        # light plot band darkens to a panel, and the white gridlines drawn over
        # it dim to a faint dark-grey so they stay subtle, not glaring, on dark.
        + os_dark_style(
            extra=(
                '[fill="#F5F5F7"]{fill:#17171A;}'
                ".pa-grid{stroke:#2C2C30;}"
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
        f'fill="{ink}">{n_vital} of {n} reasons drive four in five tickets</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="124" font-size="24" fill="{secondary}">'
        f'Ticket reasons sorted by volume; the cumulative share climbs to '
        f'the 80% line</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="156" font-size="20" fill="{secondary}">'
        f'One week of support tickets ({total:,} total) · illustrative '
        f'data</text>'
    )

    # --- gridlines (very light, on the shared percentage grid) ---
    for t in y_ticks:
        gy = sy(t)
        parts.append(
            f'<line class="pa-grid" x1="{plot_x:.1f}" y1="{gy:.1f}" x2="{plot_x + plot_w:.1f}" '
            f'y2="{gy:.1f}" stroke="#FFFFFF" stroke-width="1.6"/>'
        )

    # --- 80% reference rule + its label --------------------------
    ref_y = sy(_PARETO_THRESHOLD)
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{ref_y:.1f}" x2="{plot_x + plot_w:.1f}" '
        f'y2="{ref_y:.1f}" stroke="{ref_c}" stroke-width="2" '
        f'stroke-dasharray="8 5" opacity="0.85"/>'
    )
    parts.append(
        f'<text x="{plot_x + plot_w - 6:.1f}" y="{ref_y - 10:.1f}" '
        f'font-size="20" fill="{ref_c}" text-anchor="end">80% Pareto line</text>'
    )

    # --- sorted bars (vital few Blue, trivial many grey) ---------
    for i, r in enumerate(rows):
        cx = slot_center(i)
        share = float(r["share"])
        top = sy(share)
        h = ax_bottom - top
        is_vital = bool(r["vital"])
        fill = vital_c if is_vital else trivial_c
        # A stable class on the vital-few bars only; the OS-adaptive media block
        # deepens them under prefers-contrast. The trivial-many stay their fixed
        # neutral grey (no class), unaffected.
        rect_cls = ' class="pa-vital"' if is_vital else ""
        x0 = cx - bar_w / 2.0
        tip = (
            f'{r["reason"]}: {int(r["count"]):,} tickets '
            f'({share:.1f}% of the week, cumulative {float(r["cum"]):.1f}%)'
        )
        parts.append(
            f'<g class="bar" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}">'
        )
        parts.append(f"<title>{xml_escape(tip)}</title>")
        # Rounded top corners via a small rx; white keyline lifts each bar off
        # the band and off its neighbour without a dark ring.
        parts.append(
            f'<rect{rect_cls} x="{x0:.1f}" y="{top:.1f}" width="{bar_w:.1f}" '
            f'height="{h:.1f}" rx="4" fill="{fill}" stroke="#FFFFFF" '
            f'stroke-width="1.5"/>'
        )
        parts.append("</g>")

    # --- cumulative-percentage line + markers --------------------
    # One smooth-enough polyline through the running totals, drawn with a soft
    # white under-stroke so it stays crisp where it crosses a bar edge, then
    # the coloured line on top. The line is a distinct *shape* (a curve with
    # markers) from the bars, so bar vs curve never relies on hue alone.
    pts = [(slot_center(i), sy(float(r["cum"]))) for i, r in enumerate(rows)]
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    parts.append(
        f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="8" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<path class="pa-line" d="{d}" fill="none" stroke="{line_c}" '
        f'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # Direct label riding on the curve near its start, naming what the line is
    # (so the reader never hunts a legend to tell it from the bars).
    lbl_x, lbl_y = pts[0]
    parts.append(
        f'<text x="{lbl_x + 18:.1f}" y="{lbl_y + 30:.1f}" font-size="21" '
        f'font-weight="600" fill="{line_c}">cumulative %</text>'
    )

    # Round markers at every step; the crossing point reuses the same recipe,
    # only larger, so all markers form one family.
    for i, r in enumerate(rows):
        cx, cy = pts[i]
        cum = float(r["cum"])
        is_cross = bool(crossing) and int(r["rank"]) == int(crossing["rank"])
        rr = 10.0 if is_cross else 6.5
        tip = f'{r["reason"]}: cumulative {cum:.1f}% of tickets'
        parts.append(
            f'<g class="pt" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}">'
        )
        parts.append(f"<title>{xml_escape(tip)}</title>")
        parts.append(
            f'<circle class="halo" cx="{cx:.1f}" cy="{cy:.1f}" r="18" '
            f'fill="{ink}" fill-opacity="0.08"/>'
        )
        parts.append(
            f'<circle class="pa-line" cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" '
            f'fill="{line_c}" stroke="#FFFFFF" stroke-width="2"/>'
        )
        parts.append("</g>")

    # --- crossing call-out ---------------------------------------
    if crossing:
        cross_i = int(crossing["rank"]) - 1
        cx, cy = pts[cross_i]
        nv = int(crossing["n_vital"])
        cc = int(crossing["cum_count"])
        # Stack both call-out lines *above* the marker so neither sits on the
        # 80 % reference rule (the crossing is just above it). A short leader
        # connects the text to the emphasised dot.
        note_x = cx + 22
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{note_x - 6:.1f}" '
            f'y2="{cy - 44:.1f}" stroke="{secondary}" stroke-width="1.4" '
            f'stroke-dasharray="3 4"/>'
        )
        parts.append(
            f'<text x="{note_x:.1f}" y="{cy - 44:.1f}" font-size="22" '
            f'font-weight="700" fill="{ink}">'
            f'{nv} reasons → {round(crossing["cum"])}% of tickets</text>'
        )
        parts.append(
            f'<text x="{note_x:.1f}" y="{cy - 18:.1f}" font-size="20" '
            f'fill="{secondary}">{cc:,} of {total:,} in one week</text>'
        )

    # --- axes: left (bar shares) + right (cumulative) ------------
    # Left vertical axis: bar shares.
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{plot_y:.1f}" x2="{plot_x:.1f}" '
        f'y2="{ax_bottom:.1f}" stroke="{ink}" stroke-width="1.6"/>'
    )
    # Right vertical axis: cumulative share (drawn in the curve colour so the
    # reader binds the right scale to the orange line).
    parts.append(
        f'<line x1="{plot_x + plot_w:.1f}" y1="{plot_y:.1f}" '
        f'x2="{plot_x + plot_w:.1f}" y2="{ax_bottom:.1f}" '
        f'stroke="{line_c}" stroke-width="1.6"/>'
    )
    parts.append(
        f'<line x1="{plot_x:.1f}" y1="{ax_bottom:.1f}" '
        f'x2="{plot_x + plot_w:.1f}" y2="{ax_bottom:.1f}" '
        f'stroke="{ink}" stroke-width="1.6"/>'
    )
    for t in y_ticks:
        gy = sy(t)
        # Left ticks + labels (ink).
        parts.append(
            f'<line x1="{plot_x - 7:.1f}" y1="{gy:.1f}" x2="{plot_x:.1f}" '
            f'y2="{gy:.1f}" stroke="{ink}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{plot_x - 14:.1f}" y="{gy + 6:.1f}" font-size="19" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="end">{t}%</text>'
        )
        # Right ticks + labels (curve colour).
        parts.append(
            f'<line x1="{plot_x + plot_w:.1f}" y1="{gy:.1f}" '
            f'x2="{plot_x + plot_w + 7:.1f}" y2="{gy:.1f}" '
            f'stroke="{line_c}" stroke-width="1.6"/>'
        )
        parts.append(
            f'<text x="{plot_x + plot_w + 14:.1f}" y="{gy + 6:.1f}" '
            f'font-size="19" font-family="Roboto Mono, monospace" '
            f'fill="{line_c}" text-anchor="start">{t}%</text>'
        )

    # Left axis title (bar shares).
    lt_x = 62
    lt_y = plot_y + plot_h / 2
    parts.append(
        f'<text x="{lt_x:.1f}" y="{lt_y:.1f}" font-size="21" fill="{ink}" '
        f'text-anchor="middle" '
        f'transform="rotate(-90 {lt_x:.1f} {lt_y:.1f})">'
        f'Share of tickets (bars)</text>'
    )
    # Right axis title (cumulative curve).
    rt_x = width - 34
    rt_y = plot_y + plot_h / 2
    parts.append(
        f'<text x="{rt_x:.1f}" y="{rt_y:.1f}" font-size="21" fill="{line_c}" '
        f'text-anchor="middle" '
        f'transform="rotate(90 {rt_x:.1f} {rt_y:.1f})">'
        f'Cumulative share (line)</text>'
    )

    # --- x-axis reason labels (angled so long names never collide) ---
    for i, r in enumerate(rows):
        cx = slot_center(i)
        reason = str(r["reason"])
        # Rotate -32 degrees about the label anchor, exactly under the slot.
        ly = ax_bottom + 22
        parts.append(
            f'<text x="{cx:.1f}" y="{ly:.1f}" font-size="19" fill="{ink}" '
            f'text-anchor="end" '
            f'transform="rotate(-32 {cx:.1f} {ly:.1f})">'
            f'{xml_escape(reason)}</text>'
        )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the Pareto SVG to the canonical assets path (or --out)."""
    render_cli(
        __file__, "pareto", build_svg,
        description="Render the house-style Pareto chart (sorted bars + "
                    "cumulative % line + 80% line) to SVG.",
    )


if __name__ == "__main__":
    main()

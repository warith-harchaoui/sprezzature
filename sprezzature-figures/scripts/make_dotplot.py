#!/usr/bin/env python3
"""
make_dotplot — a Wilkinson dot plot rendered as a hand-authored SVG.

A **Wilkinson dot plot** shows one dot per observation, binned into
equal-width intervals along the value axis and stacked vertically
within each bin (Wilkinson, *The American Statistician*, 1999). Unlike
a histogram, every data point stays visible: the reader can count
individual observations, and the silhouette still reveals the shape of
the distribution. It shines for small-to-medium samples (a few dozen
observations) where a histogram's bars would hide the sample size.

This generator builds the SVG string by hand (no matplotlib / seaborn
/ plotly, no Vega) so the binning and stacking geometry is fully under
our control, and matches the sprezzature-* house style: Roboto, the
Apple-ish palette, rounded corners, ink ``#1D1D1F``, secondary
``#6E6E73``, white background. The figure is a **static** poster-size
panel: a Wilkinson dot plot already shows the whole distribution in a
single still, so no motion is added (it would reveal nothing a reader
cannot already see). Each dot carries a native ``<title>`` tooltip.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/dotplot.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

# The house-style palette lives one directory up, in _style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _render import render_cli  # noqa: E402
from _svg import svg_open  # noqa: E402


# ------------------------------------------------------------------
# Communicative fake data
# ------------------------------------------------------------------
#: First-response times (in hours) for a week of inbound support
#: tickets at a small SaaS help desk. Most tickets are answered within
#: the first few hours; a handful drag into a long tail — the story the
#: dot plot makes obvious at a glance. Values are illustrative.
RESPONSE_HOURS: List[float] = [
    0.5, 0.7, 0.8, 1.1, 1.2, 1.3, 1.4, 1.6,   # answered almost immediately
    2.1, 2.2, 2.4, 2.6, 2.7, 2.9,             # within the morning
    3.1, 3.3, 3.4, 3.6, 3.8,                  # same-day
    4.2, 4.5, 4.7, 4.9,                       # slower
    5.3, 5.6, 5.8,                            # half a shift
    6.4, 6.9,                                 # the long tail begins
    7.7,
    9.2,                                      # a straggler nobody picked up
]


# ------------------------------------------------------------------
# Wilkinson binning
# ------------------------------------------------------------------
def wilkinson_bins(values: List[float], bin_width: float) -> List[Tuple[float, List[float]]]:
    """Assign each observation to an equal-width bin and stack it.

    Implements the classic Wilkinson dot-plot binning: sort the data,
    then sweep left to right opening a new bin whenever the next point
    lies more than ``bin_width`` from the bin's first point. Every dot
    in a bin is drawn at the bin's centre and stacked vertically, so
    the column height equals the bin count.

    Parameters
    ----------
    values : list of float
        The raw observations.
    bin_width : float
        The width of each bin in data units. Dots within this distance
        of a bin's opening point share the bin.

    Returns
    -------
    list of (float, list of float)
        One ``(centre, members)`` tuple per bin, left to right. The
        ``centre`` is the mean of the bin's members (dot-density
        placement); ``members`` are the observations in that bin.
    """
    bins: List[Tuple[float, List[float]]] = []
    members: List[float] = []
    anchor: float = 0.0
    for v in sorted(values):
        if members and (v - anchor) > bin_width:
            centre = sum(members) / len(members)
            bins.append((centre, members))
            members = []
        if not members:
            anchor = v
        members.append(v)
    if members:
        centre = sum(members) / len(members)
        bins.append((centre, members))
    return bins


# ------------------------------------------------------------------
# SVG assembly
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full Wilkinson dot-plot SVG string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Controls
        whether the emitted SVG carries its own fullscreen button; the raster
        output is unaffected. Defaults to ``"self-contained"``.
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
    palette: Dict[str, str] = load_palette(accessibility)
    blue = palette.get("Blue", "#007AFF")
    red = palette.get("Red", "#FF3B30")
    ink = "#1D1D1F"
    secondary = "#6E6E73"

    # --- canvas geometry -----------------------------------------
    # Poster-size panel: a generous canvas so the dots read large and
    # the figure holds up at gallery scale. Height is sized to the
    # tallest bin so the stacked columns fill the panel instead of
    # floating over a sea of white space.
    width = 1200
    m_left, m_right = 96, 48
    m_top, m_bottom = 150, 108
    plot_w = width - m_left - m_right

    # --- value axis ----------------------------------------------
    x_min, x_max = 0.0, 10.0
    bin_width = 0.5
    ticks = [0, 2, 4, 6, 8, 10]

    def sx(v: float) -> float:
        """Map a data value to an x pixel coordinate."""
        return m_left + (v - x_min) / (x_max - x_min) * plot_w

    # Dot radius and vertical pitch. Pitch is a hair larger than the
    # diameter so stacked dots read as separate observations.
    r = 13.0
    pitch = 2 * r + 3.0

    bins = wilkinson_bins(RESPONSE_HOURS, bin_width)

    # Fit the canvas to the tallest stack so columns fill the panel.
    tallest = max(len(members) for _, members in bins)
    plot_h = tallest * pitch + r
    height = m_top + int(plot_h) + m_bottom
    baseline_y = height - m_bottom

    # Service-level target: tickets answered within 4 hours are "on
    # time". Dots at or before the line are Blue; the long tail past it
    # is Red — a reinforcement layer, always paired with the text label.
    target = 4.0

    parts: List[str] = []
    n = len(RESPONSE_HOURS)
    within = sum(1 for v in RESPONSE_HOURS if v <= target)
    pct_within = round(100 * within / n)

    parts.append(svg_open(width, height, "dp-title", "dp-desc"))
    parts.append(
        '<title id="dp-title">Support ticket first-response times, one dot per '
        'ticket</title>'
    )
    parts.append(
        f'<desc id="dp-desc">Wilkinson dot plot of {n} first-response times in '
        f'hours. Each dot is one ticket, binned every {bin_width} h and stacked. '
        f'{pct_within}% of tickets were answered within the 4-hour target '
        f'(blue); the {n - within} past it form the long tail (red).</desc>'
    )

    # Focus ring for keyboard users landing on an interactive dot. The
    # figure is static (no animation), so there is no motion to guard.
    #
    # OS-adaptive overrides (additive; the default render is byte-identical
    # because every rule below lives inside an @media query and a class rule
    # only outranks the inline fill when the query matches). The two dot
    # categories — "within target" (blue) and "long tail" (red) — deepen to
    # their high-contrast hues under prefers-contrast. forced-colors is opt-in
    # here (forced=True): category identity survives with no colour because the
    # dashed 4-hour target line splits the panel into the two regions and both
    # categories carry an always-visible legend label.
    style_rows = [
        ".dot{cursor:pointer}",
        ".dot:hover,.dot:focus{stroke:#FFFFFF;stroke-width:2.5}",
        ".dot:focus{outline:none}",
    ]
    dot_series = {".dot-within": blue, ".dot-tail": red}
    style_rows.append(os_adaptive_style(dot_series, role="fill", forced=True))
    # Additive dark mode: flip paper + the two ink tiers (data hues untouched).
    style_rows.append(os_dark_style())
    parts.append("<style>" + "".join(style_rows) + "</style>")

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="60" font-size="32" font-weight="700" '
        f'fill="{ink}">Most tickets get a reply within hours</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="96" font-size="20" fill="{secondary}">'
        f'{pct_within}% of {n} support tickets clear the 4-hour target; a '
        f'thin red tail drags on · illustrative</text>'
    )

    # --- target line + label -------------------------------------
    tx = sx(target)
    parts.append(
        f'<line x1="{tx:.1f}" y1="{m_top - 12:.1f}" x2="{tx:.1f}" '
        f'y2="{baseline_y:.1f}" stroke="{secondary}" stroke-width="1.5" '
        f'stroke-dasharray="6 6"/>'
    )
    parts.append(
        f'<text x="{tx + 10:.1f}" y="{m_top - 14:.1f}" font-size="17" '
        f'fill="{secondary}">4-hour target</text>'
    )

    # --- baseline (value axis) -----------------------------------
    parts.append(
        f'<line x1="{m_left}" y1="{baseline_y:.1f}" x2="{m_left + plot_w}" '
        f'y2="{baseline_y:.1f}" stroke="{ink}" stroke-width="1.5"/>'
    )
    for t in ticks:
        px = sx(t)
        parts.append(
            f'<text x="{px:.1f}" y="{baseline_y + 34:.1f}" font-size="18" '
            f'font-family="Roboto Mono, monospace" fill="{ink}" '
            f'text-anchor="middle">{t}</text>'
        )
    parts.append(
        f'<text x="{m_left + plot_w / 2:.1f}" y="{baseline_y + 72:.1f}" '
        f'font-size="20" fill="{ink}" text-anchor="middle">'
        f'First-response time (hours, lower is better)</text>'
    )

    # --- the dots ------------------------------------------------
    # Draw each bin as a stacked column of dots, bottom to top. Fully
    # drawn in the still — the Wilkinson silhouette *is* the chart, so
    # no motion is added. A thin white halo keeps stacked same-category
    # dots distinct where they touch.
    for centre, members in bins:
        cx = sx(centre)
        for j, v in enumerate(members):
            cy = baseline_y - r - j * pitch
            over = v > target
            fill = red if over else blue
            cat = "dot-tail" if over else "dot-within"
            # Native tooltip: exact value, one decimal.
            tip = f"Ticket answered in {v:.1f} h"
            parts.append(
                f'<circle class="dot {cat}" cx="{cx:.1f}" cy="{cy:.1f}" '
                f'r="{r:.1f}" fill="{fill}" fill-opacity="0.92" '
                f'stroke="#FFFFFF" stroke-width="1.5" tabindex="0" '
                f'role="img" aria-label="{tip}">'
                f'<title>{tip}</title>'
                f'</circle>'
            )

    # --- legend ---------------------------------------------------
    # Anchored top-right inside the panel; pure fills (no dark ring),
    # labels in ink to the right of each disk.
    lr = 9.0
    ly = m_top + 4
    lx_blue = m_left + plot_w - 292
    lx_red = m_left + plot_w - 118
    parts.append(
        f'<circle class="dot-within" cx="{lx_blue:.1f}" cy="{ly:.1f}" '
        f'r="{lr:.1f}" fill="{blue}"/>'
    )
    parts.append(
        f'<text x="{lx_blue + 16:.1f}" y="{ly + 6:.1f}" font-size="18" '
        f'fill="{ink}">Within target</text>'
    )
    parts.append(
        f'<circle class="dot-tail" cx="{lx_red:.1f}" cy="{ly:.1f}" '
        f'r="{lr:.1f}" fill="{red}"/>'
    )
    parts.append(
        f'<text x="{lx_red + 16:.1f}" y="{ly + 6:.1f}" font-size="18" '
        f'fill="{ink}">Long tail</text>'
    )

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the dot-plot SVG to the canonical assets path.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "dotplot",
        build_svg,
        description="Write the house-style Wilkinson dot-plot SVG example.",
    )


if __name__ == "__main__":
    main()

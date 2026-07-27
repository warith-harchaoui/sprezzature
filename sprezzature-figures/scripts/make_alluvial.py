#!/usr/bin/env python3
"""
make_alluvial — a house-styled *alluvial / parallel-sets* diagram as SVG.

An alluvial diagram tracks how a fixed population of records keeps or
changes its *category membership* as it flows across several ordered
axes. Unlike a Sankey (which shows one-way volume between arbitrary
nodes), every record here is present at *every* axis, so each vertical
stack sums to the same total and the ribbons only ever re-partition the
same 100 %. matplotlib and seaborn have no primitive for this; plotly
exposes it as ``parcats`` and R as ``ggalluvial``. This module builds
the SVG string by hand — cubic-Bézier ribbons between stacked category
blocks — so the result is dependency-light, reproducible, and natively
interactive (CSS ``:hover`` + native ``<title>`` tooltips, no JS).

The example follows one cohort of new sign-ups through three axes of a
software-as-a-service (SaaS) funnel:

    Acquisition channel  →  Plan chosen  →  90-day outcome

The takeaway the subtitle states: the ribbon from *Referral* into
*Retained* is the fattest single strand, and *Free-trial* users churn
far more than *Paid* ones — the point a reader should get at a glance.

House style: white background, Roboto type, ink ``#1D1D1F`` /
secondary ``#6E6E73``, rounded corners, the Apple-system categorical
palette pulled from :mod:`_style` (which reads
``sprezzature-colors/references/palette.csv`` when co-installed).

Usage
-----
::

    python make_alluvial.py            # writes assets/svg-examples/alluvial.svg
    python make_alluvial.py --out x.svg

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# _style is a sibling module — pull the house palette so make ↔ audit
# brand tokens never drift.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import svg_example_path, write_svg  # noqa: E402
from _style import (  # noqa: E402
    forced_color_patterns,
    leveled_colors,
    load_palette,
    os_adaptive_style,
    os_dark_style,
)
from _interactive import fullscreen_control  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. Fake-but-communicative data                                              #
# --------------------------------------------------------------------------- #
# One cohort of 1,000 new sign-ups. Each *flow* is a full path through the
# three axes with a record count; every axis therefore sums to 1,000. The
# numbers are chosen so the story reads: Referral → Retained is the single
# fattest strand, and Free-trial churns much harder than Paid.
#
# A flow is a dict record (dict-over-class house style):
#   {"path": (channel, plan, outcome), "count": int}
FLOWS: List[Dict[str, Any]] = [
    # -- Referral: high-intent, mostly paid, mostly retained ----------------
    {"path": ("Referral", "Paid", "Retained"), "count": 180},
    {"path": ("Referral", "Paid", "Downgraded"), "count": 40},
    {"path": ("Referral", "Free trial", "Retained"), "count": 70},
    {"path": ("Referral", "Free trial", "Churned"), "count": 40},
    # -- Paid search: solid volume, more free-trial hesitation --------------
    {"path": ("Paid search", "Paid", "Retained"), "count": 95},
    {"path": ("Paid search", "Paid", "Downgraded"), "count": 35},
    {"path": ("Paid search", "Free trial", "Retained"), "count": 55},
    {"path": ("Paid search", "Free trial", "Churned"), "count": 95},
    # -- Organic: curious, trial-heavy, leaky -------------------------------
    {"path": ("Organic", "Paid", "Retained"), "count": 45},
    {"path": ("Organic", "Free trial", "Retained"), "count": 40},
    {"path": ("Organic", "Free trial", "Churned"), "count": 90},
    {"path": ("Organic", "Free trial", "Downgraded"), "count": 25},
    # -- Social: lowest intent, churns worst --------------------------------
    {"path": ("Social", "Paid", "Retained"), "count": 20},
    {"path": ("Social", "Free trial", "Retained"), "count": 15},
    {"path": ("Social", "Free trial", "Churned"), "count": 20},
]

# Axis order (left → right) and the category order within each axis
# (top → bottom). Fixing the order keeps the layout deterministic and
# lets us tune where ribbons cross for legibility.
AXES: List[Tuple[str, List[str]]] = [
    ("Acquisition channel", ["Referral", "Paid search", "Organic", "Social"]),
    ("Plan chosen", ["Paid", "Free trial"]),
    ("90-day outcome", ["Retained", "Downgraded", "Churned"]),
]

# Category → palette base name. Outcome colours carry meaning
# (green = kept, blue = neutral downgrade, gray = churn) and are the
# ones a reader tracks; channels/plans get quieter neutral fills so the
# eye follows the outcome colour through the whole diagram.
OUTCOME_COLOR: Dict[str, str] = {
    "Retained": "Green",
    "Downgraded": "Blue",
    "Churned": "Gray",
}


# --------------------------------------------------------------------------- #
# 2. Geometry                                                                 #
# --------------------------------------------------------------------------- #
def _totals(axis_index: int, categories: List[str]) -> Dict[str, int]:
    """Sum the cohort by category at one axis.

    Parameters
    ----------
    axis_index : int
        Which slot of each flow's ``path`` tuple to bucket on.
    categories : list of str
        The category order for that axis (defines dict key order).

    Returns
    -------
    dict of str to int
        ``{category: record_count}`` for every category at this axis.
    """
    out: Dict[str, int] = {c: 0 for c in categories}
    for flow in FLOWS:
        out[flow["path"][axis_index]] += flow["count"]
    return out


def _stack(
    totals: Dict[str, int],
    *,
    top: float,
    height: float,
    gap: float,
    scale: float,
) -> Dict[str, Dict[str, float]]:
    """Lay out one axis's category blocks as a vertical stack.

    Parameters
    ----------
    totals : dict of str to int
        Category → record count (order defines the stack top→bottom).
    top : float
        Y of the stack's top edge (SVG units).
    height : float
        Total vertical span available for the stack (unused directly;
        the stack grows from ``top`` by value × ``scale``).
    gap : float
        Vertical padding between adjacent blocks.
    scale : float
        Pixels per record.

    Returns
    -------
    dict of str to dict
        ``{category: {"y0", "y1", "cy", "count"}}`` — top/bottom edge,
        centre, and count of each block.
    """
    del height  # kept for signature symmetry with the caller's intent
    out: Dict[str, Dict[str, float]] = {}
    y = top
    for cat, count in totals.items():
        h = count * scale
        out[cat] = {"y0": y, "y1": y + h, "cy": y + h / 2.0, "count": float(count)}
        y += h + gap
    return out


def _ribbon_path(
    x0: float,
    x1: float,
    a_top: float,
    a_bot: float,
    b_top: float,
    b_bot: float,
) -> str:
    """Build the SVG path for one filled ribbon between two axes.

    The ribbon is a closed quadrilateral whose left edge sits on axis A
    (``a_top``..``a_bot`` at ``x0``) and right edge on axis B
    (``b_top``..``b_bot`` at ``x1``), joined by smooth horizontal cubic
    Béziers (control points at the horizontal midpoint) so the strands
    read as flowing water rather than straight wedges.

    Returns
    -------
    str
        An SVG ``d`` attribute value.
    """
    mx = (x0 + x1) / 2.0
    return (
        f"M{x0:.1f},{a_top:.1f} "
        f"C{mx:.1f},{a_top:.1f} {mx:.1f},{b_top:.1f} {x1:.1f},{b_top:.1f} "
        f"L{x1:.1f},{b_bot:.1f} "
        f"C{mx:.1f},{b_bot:.1f} {mx:.1f},{a_bot:.1f} {x0:.1f},{a_bot:.1f} "
        "Z"
    )


# --------------------------------------------------------------------------- #
# 3. SVG assembly                                                             #
# --------------------------------------------------------------------------- #
def _esc(text: str) -> str:
    """XML-escape a label for safe embedding in the SVG text."""
    return html.escape(str(text), quote=True)


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Render the full alluvial diagram as an SVG string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`.
        One of ``"self-contained"`` (default, ships a hidden-until-live
        fullscreen button), ``"external"`` or ``"static"`` (no button).
    accessibility : str, optional
        The palette accessibility level. ``"universal"`` (default) is the
        colour-vision-safe standard; other levels (``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"``,
        ``"tritanopia"``) remap the hues via the sprezzature-colors engine.

    Returns
    -------
    str
        A complete, self-contained SVG document (embedded CSS for the
        hover interaction, native ``<title>`` tooltips, no external
        assets, no JavaScript).
    """
    palette = load_palette(accessibility)
    ink = "#1D1D1F"
    secondary = "#6E6E73"

    # -- canvas ------------------------------------------------------------- #
    # Poster-scale so the ribbons read from across a room and every label
    # has room to breathe. Roughly 1.9x the old 760x480 footprint.
    width, height = 1440, 900
    pad_top = 176         # room for title + subtitle + axis captions
    pad_bottom = 128      # room for the outcome legend + last label's subtitle
    # Outer padding holds the flanking labels: the first axis labels its
    # blocks on the LEFT, the last axis on the RIGHT, so both margins are wide.
    pad_left, pad_right = 208, 190
    margin = 46           # gutter for title / caption / legend text
    block_w = 26          # width of each category block (the "stations")
    label_gap = 15        # px between a block and its text label

    total_records = sum(f["count"] for f in FLOWS)

    # Vertical scale: fit the tallest axis (which is the full cohort) into
    # the plot band, minus the inter-block gaps of the busiest axis.
    plot_top = pad_top
    plot_h = height - pad_top - pad_bottom
    gap = 20
    max_blocks = max(len(cats) for _, cats in AXES)
    # Leave a little headroom below the stack so the bottom block's subtitle
    # never crowds the legend caption.
    usable_h = plot_h - gap * (max_blocks - 1) - 18
    scale = usable_h / total_records

    # X of each axis's *left* block edge, spread evenly across the band.
    n_axes = len(AXES)
    inner_w = width - pad_left - pad_right
    span = inner_w - block_w
    axis_x: List[float] = [pad_left + span * i / (n_axes - 1) for i in range(n_axes)]

    # Lay out every axis's stack, vertically centred within the plot band.
    stacks: List[Dict[str, Dict[str, float]]] = []
    for i, (_, cats) in enumerate(AXES):
        totals = _totals(i, cats)
        stack_h = sum(totals.values()) * scale + gap * (len(cats) - 1)
        top = plot_top + (plot_h - stack_h) / 2.0
        stacks.append(_stack(totals, top=top, height=plot_h, gap=gap, scale=scale))

    parts: List[str] = []

    # -- header ------------------------------------------------------------- #
    parts.append(
        '<svg role="img" '
        'aria-label="Alluvial diagram of a SaaS sign-up cohort across '
        'acquisition channel, plan, and 90-day outcome" '
        'xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    parts.append(
        "<title>Where new sign-ups end up after 90 days</title>"
        "<desc>An alluvial diagram following 1,000 new sign-ups across three "
        "axes — acquisition channel, plan chosen, and 90-day outcome. Ribbon "
        "width is proportional to the number of users on that path; the "
        "Referral-to-Retained strand is the widest, and free-trial users "
        "churn far more than paying ones. Hover a ribbon to highlight one "
        "path.</desc>"
    )

    # Embedded style: dim every ribbon on group hover, restore the hovered
    # one to full strength. Pure CSS, honours reduced-motion by using a
    # short, non-essential transition only.
    # OS-adaptive overrides (additive; the default render is unchanged because
    # every rule below lives inside a media query). Under prefers-contrast the
    # ribbons and their matching outcome blocks / legend swatches deepen to the
    # high-contrast outcome hues, and each ribbon's fill-opacity is raised so the
    # deepened strand reads solidly against the white hairlines.
    outcome_series = {
        f".ribbon-{cat}": palette.get(OUTCOME_COLOR[cat], secondary)
        for cat in OUTCOME_COLOR
    }
    block_series = {
        f".oblock-{cat}": palette.get(OUTCOME_COLOR[cat], secondary)
        for cat in OUTCOME_COLOR
    }
    block_hc = leveled_colors(block_series, "high-contrast")
    adaptive = os_adaptive_style(
        outcome_series,
        role="fill",
        extra_contrast=".ribbon{fill-opacity:.72 !important;}"
        + "".join(f"{sel}{{fill:{hexv};}}" for sel, hexv in block_hc.items()),
    )
    # forced-colors (Windows High Contrast): ribbon identity is carried by colour
    # alone (no per-ribbon label), and the ~4-colour system palette would merge
    # the three outcomes into one ink. Give each outcome a distinct Canvas/
    # CanvasText hatch/dot pattern so the three strand families stay separable
    # without colour. The pattern defs are inert at the default render (they are
    # referenced only inside the forced-colors media query), so the shipped SVG
    # is byte-for-byte unchanged.
    fcp_defs, fcp_style = forced_color_patterns(
        [f".ribbon-{cat}" for cat in OUTCOME_COLOR], prefix="alluvial-fcp"
    )
    parts.append(
        "<style>"
        ".ribbon{transition:opacity .18s ease;}"
        ".flows:hover .ribbon{opacity:.14;}"
        ".flows .ribbon:hover{opacity:.95;}"
        ".flows .ribbon:focus{opacity:.95;outline:none;}"
        "@media (prefers-reduced-motion: reduce){.ribbon{transition:none;}}"
        + adaptive
        + fcp_style
        + os_dark_style()
        + "</style>"
    )
    parts.append(f"<defs>{fcp_defs}</defs>")

    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # -- title block -------------------------------------------------------- #
    parts.append(
        f'<text x="{margin}" y="60" font-family="Roboto, system-ui, sans-serif" '
        f'font-size="38" font-weight="600" fill="{ink}">'
        "Where new sign-ups end up after 90 days</text>"
    )
    parts.append(
        f'<text x="{margin}" y="98" font-family="Roboto, system-ui, sans-serif" '
        f'font-size="22" fill="{secondary}">'
        "Referral drives the most retention; free-trial users churn far more "
        "than paying ones</text>"
    )
    parts.append(
        f'<text x="{margin}" y="128" font-family="Roboto, system-ui, sans-serif" '
        f'font-size="16" fill="{secondary}">'
        "Illustrative cohort of 1,000 sign-ups &#183; ribbon width = number of "
        "users on that path</text>"
    )

    # -- axis captions ------------------------------------------------------ #
    # Each caption is centred over the label side of its column: the first
    # axis labels leftward, so its caption end-aligns to the block's left
    # edge; the others label rightward, so start-align to the right edge.
    for i, (axis_title, _) in enumerate(AXES):
        if i == 0:
            # Left-align at the outer margin — the caption is wider than the
            # first column's left-hand label gutter, so end-aligning clips it.
            cx, anchor = margin, "start"
        elif i == n_axes - 1:
            cx, anchor = axis_x[i], "start"
        else:
            cx, anchor = axis_x[i] + block_w + label_gap, "start"
        parts.append(
            f'<text x="{cx:.1f}" y="{plot_top - 22:.1f}" '
            'font-family="Roboto Mono, monospace" font-size="15" '
            f'letter-spacing="0.6" fill="{secondary}" text-anchor="{anchor}">'
            f"{_esc(axis_title.upper())}</text>"
        )

    # -- ribbons ------------------------------------------------------------ #
    # Each flow contributes one ribbon per adjacent axis pair. Within a
    # block, ribbons are packed in the block's category order of the *other*
    # end so strands stay bundled and cross as little as possible. We track a
    # running offset per (axis, category) for both the left and right sides.
    #
    # Colour: every ribbon is coloured by its final outcome, so a reader can
    # follow "green = will be retained" from the very first axis.
    parts.append('<g class="flows">')

    # For deterministic stacking inside each block, sort flows by the target
    # ordering at each junction. We render both segments (0→1 and 1→2).
    for seg in range(n_axes - 1):
        a_idx, b_idx = seg, seg + 1
        _, a_cats = AXES[a_idx]
        _, b_cats = AXES[b_idx]
        a_order = {c: k for k, c in enumerate(a_cats)}
        b_order = {c: k for k, c in enumerate(b_cats)}

        # Running fill offsets within each block edge.
        left_off: Dict[str, float] = {c: 0.0 for c in a_cats}
        right_off: Dict[str, float] = {c: 0.0 for c in b_cats}

        # Sort flows so that, leaving each left block, strands are ordered by
        # their right-block position (and vice versa) — minimises crossings.
        seg_flows = sorted(
            FLOWS,
            key=lambda f: (a_order[f["path"][a_idx]], b_order[f["path"][b_idx]]),
        )

        x0 = axis_x[a_idx] + block_w
        x1 = axis_x[b_idx]

        for flow in seg_flows:
            a_cat = flow["path"][a_idx]
            b_cat = flow["path"][b_idx]
            outcome = flow["path"][-1]
            count = flow["count"]
            h = count * scale

            a_top = stacks[a_idx][a_cat]["y0"] + left_off[a_cat]
            b_top = stacks[b_idx][b_cat]["y0"] + right_off[b_cat]
            left_off[a_cat] += h
            right_off[b_cat] += h

            color = palette.get(OUTCOME_COLOR[outcome], secondary)
            d = _ribbon_path(x0, x1, a_top, a_top + h, b_top, b_top + h)
            pct = 100.0 * count / total_records
            tip = (
                f"{a_cat} → {b_cat} → {outcome}: "
                f"{count} users ({pct:.0f}% of cohort)"
            )
            # A thin WHITE hairline separates adjacent same-colour strands so
            # stacked green (or gray) ribbons never merge into an opaque blob —
            # each path keeps a crisp edge against its neighbour.
            parts.append(
                f'<path class="ribbon ribbon-{outcome}" tabindex="0" d="{d}" '
                f'fill="{color}" '
                f'fill-opacity="0.46" stroke="#FFFFFF" stroke-opacity="0.85" '
                f'stroke-width="1.1" stroke-linejoin="round">'
                f"<title>{_esc(tip)}</title></path>"
            )
    parts.append("</g>")

    # -- category blocks + labels ------------------------------------------ #
    for i, (_, cats) in enumerate(AXES):
        x = axis_x[i]
        for cat in cats:
            b = stacks[i][cat]
            blk_h = b["y1"] - b["y0"]
            # Outcome axis blocks take the meaning colour; earlier axes use
            # ink so the coloured ribbons stay the star.
            if i == n_axes - 1:
                fill = palette.get(OUTCOME_COLOR[cat], ink)
                block_cls = f' class="oblock-{cat}"'
            else:
                fill = ink
                block_cls = ""
            parts.append(
                f'<rect{block_cls} x="{x:.1f}" y="{b["y0"]:.1f}" width="{block_w}" '
                f'height="{blk_h:.1f}" rx="5" fill="{fill}">'
                f"<title>{_esc(cat)}: {int(b['count'])} users</title></rect>"
            )
            # Label: left/first axis labels sit to the LEFT of the block,
            # everything else to the RIGHT, so text never overlaps ribbons.
            pct = 100.0 * b["count"] / total_records
            label = f"{_esc(cat)}"
            sub = f"{int(b['count'])} · {pct:.0f}%"
            if i == 0:
                tx = x - label_gap
                anchor = "end"
            else:
                tx = x + block_w + label_gap
                anchor = "start"
            parts.append(
                f'<text x="{tx:.1f}" y="{b["cy"] - 4:.1f}" '
                'font-family="Roboto, system-ui, sans-serif" font-size="19" '
                f'font-weight="500" fill="{ink}" text-anchor="{anchor}">'
                f"{label}</text>"
            )
            parts.append(
                f'<text x="{tx:.1f}" y="{b["cy"] + 18:.1f}" '
                'font-family="Roboto Mono, monospace" font-size="14" '
                f'fill="{secondary}" text-anchor="{anchor}">{sub}</text>'
            )

    # -- outcome legend ----------------------------------------------------- #
    legend_y = height - pad_bottom + 60
    lx = margin
    parts.append(
        f'<text x="{lx}" y="{legend_y - 30:.1f}" '
        'font-family="Roboto Mono, monospace" font-size="15" '
        f'letter-spacing="0.6" fill="{secondary}">'
        "RIBBON COLOUR = 90-DAY OUTCOME</text>"
    )
    for cat in AXES[-1][1]:
        color = palette.get(OUTCOME_COLOR[cat], secondary)
        parts.append(
            f'<rect class="oblock-{cat}" x="{lx:.1f}" y="{legend_y - 17:.1f}" '
            f'width="20" height="20" '
            f'rx="5" fill="{color}" fill-opacity="0.85"/>'
        )
        parts.append(
            f'<text x="{lx + 30:.1f}" y="{legend_y:.1f}" '
            'font-family="Roboto, system-ui, sans-serif" font-size="19" '
            f'fill="{ink}">{_esc(cat)}</text>'
        )
        lx += 30 + 13.0 * len(cat) + 40

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# 4. CLI                                                                      #
# --------------------------------------------------------------------------- #
def _default_out() -> Path:
    """Return the canonical output path under ``assets/svg-examples``."""
    return svg_example_path(__file__, "alluvial")


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point — build the SVG and write it to disk.

    Parameters
    ----------
    argv : list of str, optional
        Argument vector for testing; defaults to ``sys.argv``.

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    parser = argparse.ArgumentParser(
        prog="make_alluvial",
        description="Render a house-styled alluvial / parallel-sets diagram as SVG.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_default_out(),
        help="Output SVG path (default: assets/svg-examples/alluvial.svg).",
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the fullscreen control (default: self-contained).",
    )
    parser.add_argument(
        "--accessibility",
        choices=("universal", "high-contrast", "monochrome", "deuteranopia", "protanopia", "tritanopia"),
        default="universal",
        help="Palette accessibility level (default: universal, the CVD-safe standard).",
    )
    args = parser.parse_args(argv)

    write_svg(args.out, build_svg(args.mode, args.accessibility))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

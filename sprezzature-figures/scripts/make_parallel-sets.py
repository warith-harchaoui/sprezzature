#!/usr/bin/env python3
"""
make_parallel-sets — a house-styled *parallel sets / parcats* diagram as SVG.

A parallel-sets (a.k.a. *parcats*, "parallel categories") diagram is the
categorical cousin of parallel coordinates: a fixed population is split
into category bins at several ordered axes, and Bézier ribbons flow
between the bins from one axis to the next, their width proportional to
the number of records that share that combination of categories. Every
ribbon is coloured by a single **outcome** variable, so the reader can
follow that outcome (here: *survived* vs *did not*) all the way across
the diagram and watch which category combinations concentrate it.

This is the chart Plotly ships as ``go.Parcats``. Neither matplotlib nor
seaborn has a primitive for it. This module builds the SVG by hand —
segmented category bars with rounded ends at each axis, joined by cubic
Bézier ribbons — so the output is dependency-light, reproducible, and
natively interactive (CSS ``:hover`` + native ``<title>`` tooltips, no
JavaScript).

The example is the canonical parcats dataset — the passengers of the
*Titanic* — read across four axes:

    Travel class  →  Sex  →  Age group  →  Outcome

The takeaway the subtitle states: survival on the *Titanic* tracked
"women and children first" far more than the fare paid — first-class
women almost all lived, third-class men almost all died.

House style: white background, Roboto type, ink ``#1D1D1F`` /
secondary ``#6E6E73``, rounded corners, the Apple-system palette pulled
from :mod:`_style` (which reads ``sprezzature-colors/references/palette.csv``
when co-installed).

Usage
-----
::

    python make_parallel-sets.py          # writes assets/svg-examples/parallel-sets.svg
    python make_parallel-sets.py --out x.svg

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# _style / _svg are sibling modules — pull the house palette and the
# shared XML-escape so make <-> audit brand tokens never drift.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import svg_example_path, write_svg  # noqa: E402
from _style import (  # noqa: E402
    forced_color_patterns,
    load_palette,
    os_adaptive_style,
    os_dark_style,
)
from _svg import xml_escape  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. Fake-but-communicative data                                              #
# --------------------------------------------------------------------------- #
# A reconstructed Titanic manifest, aggregated to the four categorical axes
# below (1,316 people — the passenger records, crew excluded). Each flow is
# one full path through the axes with a head count; the numbers are shaped
# from the classic Titanic contingency table so the story reads true to
# history: first-class women nearly all survived, third-class men nearly all
# died, and "women & children first" dominates the fare.
#
# A flow is a dict record (dict-over-class house style):
#   {"path": (class, sex, age, outcome), "count": int}
FLOWS: List[Dict[str, Any]] = [
    # -- First class -------------------------------------------------------- #
    {"path": ("First", "Female", "Adult", "Survived"), "count": 140},
    {"path": ("First", "Female", "Adult", "Died"), "count": 4},
    {"path": ("First", "Female", "Child", "Survived"), "count": 1},
    {"path": ("First", "Male", "Adult", "Survived"), "count": 57},
    {"path": ("First", "Male", "Adult", "Died"), "count": 118},
    {"path": ("First", "Male", "Child", "Survived"), "count": 5},
    # -- Second class ------------------------------------------------------- #
    {"path": ("Second", "Female", "Adult", "Survived"), "count": 80},
    {"path": ("Second", "Female", "Adult", "Died"), "count": 13},
    {"path": ("Second", "Female", "Child", "Survived"), "count": 13},
    {"path": ("Second", "Male", "Adult", "Survived"), "count": 14},
    {"path": ("Second", "Male", "Adult", "Died"), "count": 154},
    {"path": ("Second", "Male", "Child", "Survived"), "count": 11},
    # -- Third class -------------------------------------------------------- #
    {"path": ("Third", "Female", "Adult", "Survived"), "count": 76},
    {"path": ("Third", "Female", "Adult", "Died"), "count": 89},
    {"path": ("Third", "Female", "Child", "Survived"), "count": 14},
    {"path": ("Third", "Female", "Child", "Died"), "count": 17},
    {"path": ("Third", "Male", "Adult", "Survived"), "count": 75},
    {"path": ("Third", "Male", "Adult", "Died"), "count": 387},
    {"path": ("Third", "Male", "Child", "Survived"), "count": 13},
    {"path": ("Third", "Male", "Child", "Died"), "count": 35},
]

# Axis order (left -> right) and the category order within each axis
# (top -> bottom). Fixing the order keeps the layout deterministic and lets
# us tune where ribbons cross for legibility.
AXES: List[Tuple[str, List[str]]] = [
    ("Travel class", ["First", "Second", "Third"]),
    ("Sex", ["Female", "Male"]),
    ("Age group", ["Adult", "Child"]),
    ("Outcome", ["Survived", "Died"]),
]

# The outcome variable that colours every ribbon. Blue = lived, a warm
# red = died: the pairing is separated in hue AND lightness, so the split
# survives a grayscale print and every common colour-vision deficiency
# (red-green blindness reads blue vs red cleanly), and it is reinforced by
# the legend labels, never colour alone.
OUTCOME_AXIS = 3
OUTCOME_COLOR: Dict[str, str] = {
    "Survived": "Blue",
    "Died": "Red",
}

# Every category bin (the "stations") gets its own Apple-palette hue so the
# axes read as coloured categories rather than a wall of black bars. The
# outcome axis keeps the meaning colours (blue = lived, red = died) so the
# legend stays honest; the other three axes borrow spare palette hues that
# stay clear of blue/red to avoid clashing with the outcome ribbons.
BIN_COLOR: Dict[str, str] = {
    # Travel class — a warm-to-cool ramp
    "First": "Purple",
    "Second": "Orange",
    "Third": "Turquoise",
    # Sex — keep clear of outcome blue/red
    "Female": "Pink",
    "Male": "Turquoise",
    # Age group — keep clear of outcome blue/red
    "Adult": "Yellow",
    "Child": "Green",
    # Outcome — the meaning colours
    "Survived": "Blue",
    "Died": "Red",
}


# --------------------------------------------------------------------------- #
# 2. Geometry                                                                 #
# --------------------------------------------------------------------------- #
def _totals(axis_index: int, categories: List[str]) -> Dict[str, int]:
    """Sum the population by category at one axis.

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
    gap: float,
    scale: float,
) -> Dict[str, Dict[str, float]]:
    """Lay out one axis's category bins as a vertical stack of bars.

    Parameters
    ----------
    totals : dict of str to int
        Category -> record count (order defines the stack top->bottom).
    top : float
        Y of the stack's top edge (SVG units).
    gap : float
        Vertical padding between adjacent bins.
    scale : float
        Pixels per record.

    Returns
    -------
    dict of str to dict
        ``{category: {"y0", "y1", "cy", "count"}}`` — top/bottom edge,
        centre, and count of each bin.
    """
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
    """Build the SVG ``d`` attribute for one filled ribbon between two axes.

    The ribbon is a closed quadrilateral whose left edge sits on axis A
    (``a_top``..``a_bot`` at ``x0``) and right edge on axis B
    (``b_top``..``b_bot`` at ``x1``), joined by smooth horizontal cubic
    Béziers (control points on the horizontal midline) so the strands
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
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Render the full parallel-sets diagram as an SVG string.

    Parameters
    ----------
    mode : str, default ``"self-contained"``
        Fullscreen-control wiring for the emitted SVG:

        * ``"self-contained"`` — carry a self-revealing fullscreen button
          plus its inline script, so the standalone SVG toggles fullscreen
          on its own (the button stays hidden until the live script shows
          it, keeping the static raster byte-identical).
        * ``"external"`` — emit no button/script here; defer the control to
          a page-level module that wires every figure on the page.
        * ``"static"`` — emit nothing; a plain, non-interactive SVG.
    accessibility : str, default ``"universal"``
        Palette accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). The ``"universal"`` default is the
        colour-vision-safe standard and leaves the shipped palette unchanged.

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
    hairline = "#E9E9EB"

    # -- canvas ------------------------------------------------------------- #
    # Poster-scale so the ribbons read from across a room and every label has
    # room to breathe.
    width, height = 1560, 940
    pad_top = 196          # room for title + subtitle + axis captions
    pad_bottom = 132       # room for the outcome legend
    pad_left, pad_right = 176, 176
    margin = 52            # gutter for title / caption / legend text
    bin_w = 30             # width of each category bin bar (the "stations")
    label_gap = 16         # px between a bin and its text label

    total = sum(f["count"] for f in FLOWS)

    plot_top = pad_top
    plot_h = height - pad_top - pad_bottom
    gap = 30               # vertical space between bins in a stack
    max_bins = max(len(cats) for _, cats in AXES)
    usable_h = plot_h - gap * (max_bins - 1)
    scale = usable_h / total

    # X of each axis's *left* bin edge, spread evenly across the band.
    n_axes = len(AXES)
    inner_w = width - pad_left - pad_right
    span = inner_w - bin_w
    axis_x: List[float] = [pad_left + span * i / (n_axes - 1) for i in range(n_axes)]

    # Lay out every axis's stack, vertically centred within the plot band.
    stacks: List[Dict[str, Dict[str, float]]] = []
    for i, (_, cats) in enumerate(AXES):
        totals = _totals(i, cats)
        stack_h = sum(totals.values()) * scale + gap * (len(cats) - 1)
        top = plot_top + (plot_h - stack_h) / 2.0
        stacks.append(_stack(totals, top=top, gap=gap, scale=scale))

    parts: List[str] = []

    # -- header ------------------------------------------------------------- #
    parts.append(
        '<svg role="img" '
        'aria-label="Parallel-sets diagram of the Titanic passengers across '
        'travel class, sex, age group, and survival outcome" '
        'xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    parts.append(
        "<title>Who survived the Titanic</title>"
        "<desc>A parallel-sets (parcats) diagram routing 1,316 Titanic "
        "passengers across four categorical axes — travel class, sex, "
        "age group, and outcome. Each ribbon's width is the number of people "
        "on that path, and its colour is the outcome: blue for survived, red "
        "for died. Women and children survived far more than men, and first "
        "class far more than third. Hover a ribbon to highlight one path.</desc>"
    )

    # Embedded style: dim every ribbon on group hover, restore the hovered one
    # to full strength. Pure CSS, honours reduced-motion.
    #
    # OS-adaptive overrides (additive; the default render is byte-identical
    # because every rule lives inside a media query). Under prefers-contrast
    # the two meaning ribbons deepen to their high-contrast Blue/Red, and their
    # fill-opacity is lifted so the deepened hues stay legible where strands
    # stack. The per-category "station" bars are decorative hues and are left
    # untouched. Blue/Red are always present in the palette.
    outcome_series = {
        ".rib-survived": palette.get("Blue", secondary),
        ".rib-died": palette.get("Red", secondary),
    }
    # Under Windows High Contrast / forced-colors the ~4-colour system palette
    # cannot preserve the two meaning hues, and colour is the sole key that lets a
    # reader follow "survived" vs "died" across the axes. So each outcome ribbon
    # takes a distinct CanvasText pattern (a diagonal hatch each way) on Canvas —
    # identity by texture, not hue — and the ribbons are lifted to full opacity so
    # the pattern reads where strands stack. The patterns live in <defs> and are
    # referenced only inside the forced-colors media query, so the default render
    # is unchanged.
    fcp_defs, fcp_style = forced_color_patterns(
        [".rib-survived", ".rib-died"], prefix="ps-fcp"
    )
    parts.append(
        "<style>"
        ".ribbon{transition:opacity .18s ease;}"
        ".flows:hover .ribbon{opacity:.12;}"
        ".flows .ribbon:hover{opacity:.96;}"
        ".flows .ribbon:focus{opacity:.96;outline:none;}"
        "@media (prefers-reduced-motion: reduce){.ribbon{transition:none;}}"
        + os_adaptive_style(
            outcome_series,
            role="fill",
            extra_contrast=".ribbon{fill-opacity:.72 !important;}",
        )
        + fcp_style
        + "@media (forced-colors: active){.ribbon{fill-opacity:1;}}"
        # Additive OS dark mode: dark paper + light ink (default ink_map); the
        # outcome-coloured ribbons are data, left alone. The light axis hairline
        # rules darken so they read on the dark surface; the thin white strand
        # separators stay light so adjacent same-colour ribbons keep their split.
        + os_dark_style(extra='[stroke="#E9E9EB"]{stroke:#3A3A3E;}')
        + "</style>"
    )
    # Forced-colors pattern tiles (referenced only inside the media query above).
    parts.append(f"<defs>{fcp_defs}</defs>")

    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # -- title block -------------------------------------------------------- #
    parts.append(
        f'<text x="{margin}" y="72" font-family="Roboto, system-ui, sans-serif" '
        f'font-size="42" font-weight="600" fill="{ink}">'
        "Who survived the Titanic</text>"
    )
    parts.append(
        f'<text x="{margin}" y="112" font-family="Roboto, system-ui, sans-serif" '
        f'font-size="23" fill="{secondary}">'
        "Sex and age decided far more than the fare: women and children lived, "
        "third-class men did not</text>"
    )
    parts.append(
        f'<text x="{margin}" y="142" font-family="Roboto, system-ui, sans-serif" '
        f'font-size="16" fill="{secondary}">'
        "1,316 passengers &#183; ribbon width = number of people on that "
        "path &#183; colour = outcome</text>"
    )

    # -- axis captions ------------------------------------------------------ #
    # Centred over each axis bar; the last axis's caption right-aligns so it
    # never runs past the canvas edge.
    for i, (axis_title, _) in enumerate(AXES):
        if i == n_axes - 1:
            cx, anchor = axis_x[i] + bin_w, "end"
        else:
            cx, anchor = axis_x[i] + bin_w / 2.0, "middle"
        parts.append(
            f'<text x="{cx:.1f}" y="{plot_top - 26:.1f}" '
            'font-family="Roboto Mono, monospace" font-size="15" '
            f'letter-spacing="0.8" fill="{secondary}" text-anchor="{anchor}">'
            f"{xml_escape(axis_title.upper())}</text>"
        )

    # -- ribbons ------------------------------------------------------------ #
    # Each flow contributes one ribbon per adjacent axis pair. Within a bin,
    # ribbons are packed in the category order of the *other* end so strands
    # stay bundled and cross as little as possible. Colour is the flow's
    # outcome, so "teal = survived" reads from the very first axis.
    parts.append('<g class="flows">')

    for seg in range(n_axes - 1):
        a_idx, b_idx = seg, seg + 1
        _, a_cats = AXES[a_idx]
        _, b_cats = AXES[b_idx]
        a_order = {c: k for k, c in enumerate(a_cats)}
        b_order = {c: k for k, c in enumerate(b_cats)}

        # Running fill offsets within each bin edge.
        left_off: Dict[str, float] = {c: 0.0 for c in a_cats}
        right_off: Dict[str, float] = {c: 0.0 for c in b_cats}

        # Sort so strands leaving each left bin are ordered by their right-bin
        # position (and vice-versa) — minimises crossings.
        seg_flows = sorted(
            FLOWS,
            key=lambda f: (a_order[f["path"][a_idx]], b_order[f["path"][b_idx]]),
        )

        x0 = axis_x[a_idx] + bin_w
        x1 = axis_x[b_idx]

        for flow in seg_flows:
            a_cat = flow["path"][a_idx]
            b_cat = flow["path"][b_idx]
            outcome = flow["path"][OUTCOME_AXIS]
            count = flow["count"]
            h = count * scale

            a_top = stacks[a_idx][a_cat]["y0"] + left_off[a_cat]
            b_top = stacks[b_idx][b_cat]["y0"] + right_off[b_cat]
            left_off[a_cat] += h
            right_off[b_cat] += h

            color = palette.get(OUTCOME_COLOR[outcome], secondary)
            d = _ribbon_path(x0, x1, a_top, a_top + h, b_top, b_top + h)
            pct = 100.0 * count / total
            tip = (
                f"{a_cat} → {b_cat} → {outcome}: "
                f"{count} people ({pct:.0f}%)"
            )
            # A thin white hairline separates adjacent same-colour strands so
            # stacked ribbons never merge into an opaque blob. A stable
            # per-outcome class (".rib-survived" / ".rib-died") lets the
            # OS-adaptive media block below deepen the meaning hues; the inline
            # fill stays authoritative in the default (no-preference) render.
            outcome_cls = f"rib-{outcome.lower()}"
            parts.append(
                f'<path class="ribbon {outcome_cls}" tabindex="0" d="{d}" fill="{color}" '
                f'fill-opacity="0.55" stroke="#FFFFFF" stroke-opacity="0.9" '
                f'stroke-width="1.0" stroke-linejoin="round">'
                f"<title>{xml_escape(tip)}</title></path>"
            )
    parts.append("</g>")

    # -- category bins + labels --------------------------------------------- #
    # Each bin is a solid Apple-palette bar so the axes read as coloured
    # "stations", never a wall of black. The outcome axis keeps the meaning
    # colours (blue = lived, red = died) to anchor the legend.
    for i, (_, cats) in enumerate(AXES):
        x = axis_x[i]
        for cat in cats:
            b = stacks[i][cat]
            blk_h = b["y1"] - b["y0"]
            fill = palette.get(BIN_COLOR.get(cat, ""), secondary)
            parts.append(
                f'<rect x="{x:.1f}" y="{b["y0"]:.1f}" width="{bin_w}" '
                f'height="{blk_h:.1f}" rx="7" fill="{fill}">'
                f"<title>{xml_escape(cat)}: {int(b['count'])} people</title></rect>"
            )
            # Label side: first axis labels LEFT, everything else RIGHT, so
            # text never overlaps ribbons.
            pct = 100.0 * b["count"] / total
            sub = f"{int(b['count'])} · {pct:.0f}%"
            if i == 0:
                tx, anchor = x - label_gap, "end"
            else:
                tx, anchor = x + bin_w + label_gap, "start"
            parts.append(
                f'<text x="{tx:.1f}" y="{b["cy"] - 4:.1f}" '
                'font-family="Roboto, system-ui, sans-serif" font-size="20" '
                f'font-weight="500" fill="{ink}" text-anchor="{anchor}">'
                f"{xml_escape(cat)}</text>"
            )
            parts.append(
                f'<text x="{tx:.1f}" y="{b["cy"] + 19:.1f}" '
                'font-family="Roboto Mono, monospace" font-size="14" '
                f'fill="{secondary}" text-anchor="{anchor}">{xml_escape(sub)}</text>'
            )

    # -- baseline rule under the plot --------------------------------------- #
    rule_y = plot_top + plot_h + 24
    parts.append(
        f'<line x1="{margin}" y1="{rule_y:.1f}" x2="{width - margin}" '
        f'y2="{rule_y:.1f}" stroke="{hairline}" stroke-width="1.5"/>'
    )

    # -- outcome legend ----------------------------------------------------- #
    legend_y = height - pad_bottom + 76
    lx: float = margin
    parts.append(
        f'<text x="{lx}" y="{legend_y - 30:.1f}" '
        'font-family="Roboto Mono, monospace" font-size="15" '
        f'letter-spacing="0.8" fill="{secondary}">'
        "RIBBON COLOUR = OUTCOME</text>"
    )
    for cat in AXES[OUTCOME_AXIS][1]:
        color = palette.get(OUTCOME_COLOR[cat], secondary)
        parts.append(
            f'<rect x="{lx:.1f}" y="{legend_y - 18:.1f}" width="22" height="22" '
            f'rx="6" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{lx + 33:.1f}" y="{legend_y:.1f}" '
            'font-family="Roboto, system-ui, sans-serif" font-size="20" '
            f'fill="{ink}">{xml_escape(cat)}</text>'
        )
        lx += 33 + 13.0 * len(cat) + 48

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# 4. CLI                                                                      #
# --------------------------------------------------------------------------- #
def _default_out() -> Path:
    """Return the canonical output path under ``assets/svg-examples``."""
    return svg_example_path(__file__, "parallel-sets")


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
        prog="make_parallel-sets",
        description="Render a house-styled parallel-sets / parcats diagram as SVG.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_default_out(),
        help="Output SVG path (default: assets/svg-examples/parallel-sets.svg).",
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Fullscreen-control wiring (default: self-contained).",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal",
            "high-contrast",
            "monochrome",
            "deuteranopia",
            "protanopia",
            "tritanopia",
        ),
        default="universal",
        help="Palette accessibility level (default: universal, the CVD-safe standard).",
    )
    args = parser.parse_args(argv)

    write_svg(args.out, build_svg(mode=args.mode, accessibility=args.accessibility))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

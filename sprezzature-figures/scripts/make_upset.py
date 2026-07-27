#!/usr/bin/env python3
"""
make_upset — a house-styled UpSet plot rendered as a hand-authored SVG.

An **UpSet plot** (Lex et al., *IEEE TVCG*, 2014) visualises the sizes
of intersections among many sets — the job a Venn diagram does for two
or three sets, but scaling cleanly to a dozen. It has three coordinated
panels:

* a **bar chart of intersection sizes** across the top, one bar per
  observed combination of sets, sorted largest-first;
* a **dot matrix** below it, where each column lines up under a bar and
  the filled dots mark exactly which sets that bar combines (dots in the
  same column are joined by a line so a 3-way overlap reads instantly);
* a **set-size bar chart** on the left, giving the marginal total of
  each individual set.

This generator builds the SVG string by hand (no matplotlib / seaborn /
plotly, and no Vega — the three-panel matrix geometry with connector
lines aligned to bars is clearer authored directly). It follows the
front-* house style pulled from :mod:`_style`: the Apple-ish saturated
palette, Roboto typography, ink ``#1D1D1F`` on a white background,
rounded-corner bars, a takeaway title, and a one-line subtitle.

The figure is interactive without any JavaScript: hovering or
keyboard-focusing a combination (its bar, its matrix column, or the
connector) highlights that column and dims the rest, and every bar and
matrix column carries a native ``<title>`` tooltip with the exact
count. Every mark is drawn at full size in its final state — there is
no entrance animation, because an UpSet plot is a static comparison of
counts that gains nothing from motion, and a frozen first frame must
never look empty.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/upset.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# House-style inks
# ------------------------------------------------------------------
_INK: str = "#1D1D1F"       # primary text
_SUBTLE: str = "#6E6E73"    # secondary text
_EMPTY: str = "#D6D6DB"     # inactive matrix dot (set NOT in this combination)
_BG: str = "#FFFFFF"        # background
_FOCUS: str = "#0A4DA0"     # focus-ring blue


# ------------------------------------------------------------------
# Communicative fake data
# ------------------------------------------------------------------
#: The four channels through which a mid-size SaaS product reaches its
#: monthly-active users. Each user may be reachable through any subset
#: of them; the UpSet plot answers "which *combinations* of channels do
#: we actually reach people on, and how big is each pocket?".
#:
#: The list is ordered so the individual-set marginals come out
#: Email > Mobile app > Web app > SMS — the order the left-hand set-size
#: bars will use (largest set on top).
_SETS: List[str] = ["Email", "Mobile app", "Web app", "SMS"]


#: One observed combination per row: the tuple of member sets and the
#: number of users reachable through *exactly* that combination (an
#: exclusive intersection, the quantity UpSet plots). Values are
#: illustrative, in thousands of monthly-active users. The story: the
#: single largest pocket is people we can only reach by email, and the
#: healthy "Email + Mobile app" overlap is the second — the multi-channel
#: core the growth team wants to grow.
_COMBINATIONS: List[Tuple[Tuple[str, ...], int]] = [
    (("Email",), 62),
    (("Email", "Mobile app"), 48),
    (("Email", "Mobile app", "Web app"), 31),
    (("Mobile app",), 24),
    (("Email", "Web app"), 19),
    (("Email", "Mobile app", "Web app", "SMS"), 14),
    (("Web app",), 11),
    (("Email", "SMS"), 7),
]


def _slug(label: str) -> str:
    """Turn a label into a CSS-class-safe slug."""
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in label).strip("-")


def _combo_id(members: Tuple[str, ...]) -> str:
    """A stable slug that identifies one intersection column."""
    return "c-" + "-".join(_slug(m) for m in members)


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def _set_totals() -> Dict[str, int]:
    """Sum every combination a set participates in to get its marginal.

    Because each combination is an *exclusive* intersection, a set's
    total monthly-active reach is just the sum of the combinations it
    appears in. Returned in the fixed ``_SETS`` order.

    Returns
    -------
    dict of str to int
        Mapping ``{set_name: marginal_total}``.
    """
    totals: Dict[str, int] = {s: 0 for s in _SETS}
    for members, size in _COMBINATIONS:
        for m in members:
            totals[m] += size
    return totals


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full UpSet-plot SVG document as a string.

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
    palette = load_palette(accessibility)
    bar_color = palette.get("Blue", "#007AFF")   # intersection-size bars
    dot_color = palette.get("Purple", "#AF52DE")  # active matrix dots + set bars

    # --- panel geometry ------------------------------------------
    # Three coupled panels share a column grid (one column per
    # combination) and a row grid (one row per set).
    n_combos = len(_COMBINATIONS)
    n_sets = len(_SETS)

    # Poster-scale geometry — a generous, roomy figure that reads well
    # both in the gallery and when dropped into a slide.
    col_w = 82.0          # width of one combination column
    row_h = 52.0          # height of one set row in the matrix
    dot_r = 13.0          # matrix dot radius

    # Left block: the set-size bars + set labels sit to the left of the
    # matrix, so the matrix's left edge (matrix_x0) is pushed right.
    setbar_w = 160.0      # max pixel length of a set-size bar
    label_w = 150.0       # room for the set name between bars and matrix
    left_pad = 48.0
    matrix_x0 = left_pad + setbar_w + label_w

    top_pad = 150.0                # room for title + subtitle
    isize_h = 260.0                # height of the intersection-size bar panel
    isize_gap = 30.0               # gap between size bars and the matrix
    matrix_y0 = top_pad + isize_h + isize_gap

    plot_w = n_combos * col_w
    right_pad = 44.0
    width = int(matrix_x0 + plot_w + right_pad)
    height = int(matrix_y0 + n_sets * row_h + 52.0)

    # Column centre x for combination i.
    def col_cx(i: int) -> float:
        """Pixel x of the centre of combination column ``i``."""
        return matrix_x0 + i * col_w + col_w / 2.0

    # Row centre y for set index r (0 = top row).
    def row_cy(r: int) -> float:
        """Pixel y of the centre of matrix row ``r``."""
        return matrix_y0 + r * row_h + row_h / 2.0

    # Intersection-size scale.
    max_isize = max(size for _, size in _COMBINATIONS)
    isize_base_y = top_pad + isize_h  # baseline the size bars grow up from

    def isize_bar_h(size: int) -> float:
        """Pixel height of a size bar encoding ``size``.

        Leaves generous headroom above the tallest bar so its count
        label never collides with the panel title.
        """
        return (size / max_isize) * (isize_h - 44.0)

    # Set-size scale (left panel). Bars grow leftward from the labels.
    totals = _set_totals()
    max_total = max(totals.values())
    setbar_right = left_pad + setbar_w  # bars end here, at their inner edge

    parts: List[str] = []

    # ---- header ----
    parts.append(svg_open(width, height, "up-title", "up-desc"))
    parts.append(
        '<title id="up-title">How many users each combination of '
        'contact channels reaches</title>'
    )
    top = _COMBINATIONS[0]
    desc = (
        "UpSet plot. Top: a bar chart of intersection sizes, one bar per "
        "observed combination of reach channels, sorted largest first. "
        "Below each bar, a dot matrix marks which of the four channels "
        "(Email, Mobile app, Web app, SMS) that combination includes; "
        "dots in a column are joined by a line. Left: a bar chart of each "
        "channel's total reach. The largest single pocket is users "
        f"reachable only by {top[0][0]} ({top[1]}k)."
    )
    parts.append(f'<desc id="up-desc">{_xml(desc)}</desc>')

    # ---- interactivity + house style (pure CSS, no JS) ----
    style_rows = [
        ".ibar,.dotcol,.conn{transition:opacity .18s ease}",
        # Hover/focus any combination group dims every other column so the
        # picked intersection stands out — a static plot stays fully drawn.
        "svg:hover .combo,svg:focus-within .combo{opacity:.3}",
        ".combo:hover,.combo:focus,.combo:focus-within{opacity:1!important}",
        ".combo:focus{outline:none}",
        # The invisible hit-rect gives each column a keyboard focus target.
        ".hit{cursor:pointer;fill:transparent}",
        f".hit:focus{{outline:3px solid {_FOCUS};outline-offset:2px}}",
    ]
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside a media query). Colour here is NOT
    # the category key — which sets a bar combines is read from the dot-matrix
    # position, not from hue — so this is a pure legibility deepen and forced
    # colours are deliberately left to the browser default. Under
    # prefers-contrast the two role hues deepen: the intersection-size bars
    # (Blue) as a fill, and the set-size bars, active membership dots and the
    # connector line (Purple) as fill or stroke as each mark uses it.
    style_rows.append(
        os_adaptive_style({".isize": bar_color}, role="fill")
    )
    style_rows.append(
        os_adaptive_style(
            {".setbar": dot_color, ".activedot": dot_color}, role="fill"
        )
    )
    style_rows.append(
        os_adaptive_style({".conn": dot_color}, role="stroke")
    )
    # Additive OS dark-mode block. The white page darkens and the ink tiers flip
    # to light via the ink-map default; the light-grey "set absent" placeholder
    # dots (#D6D6DB) darken to a quiet grey so the matrix still reads its empty
    # slots without glaring on the dark page. Bars, active dots and the connector
    # carry the encoding and are left alone. No multiply groups.
    style_rows.append(
        os_dark_style(
            screen_blend=False,
            extra='[fill="#D6D6DB"]{fill:#3A3A3C;} '
            '[fill="#F5F5F7"]{fill:#1A1A1C;}',
        )
    )
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{width}" height="{height}" fill="{_BG}"/>')

    # ---- title + subtitle (the takeaway) ----
    parts.append(
        f'<text x="{left_pad:.0f}" y="52" font-size="28" font-weight="700" '
        f'fill="{_INK}">Most reachable users live on a single channel</text>'
    )
    parts.append(
        f'<text x="{left_pad:.0f}" y="82" font-size="17" fill="{_SUBTLE}">'
        f'Monthly-active users (thousands) by exact combination of contact '
        f'channels · illustrative</text>'
    )

    # ---- shaded alternating matrix rows (subtle zebra for readability) ----
    for r in range(n_sets):
        if r % 2 == 1:
            continue
        y = matrix_y0 + r * row_h
        parts.append(
            f'<rect x="{matrix_x0:.1f}" y="{y:.1f}" width="{plot_w:.1f}" '
            f'height="{row_h:.1f}" fill="#F5F5F7"/>'
        )

    # ---- intersection-size panel: y-axis title + reference ticks ----
    # A light "count" gridline at the max keeps the bars readable without
    # chartjunk.
    parts.append(
        f'<text x="{matrix_x0:.1f}" y="{top_pad - 12:.1f}" font-size="15" '
        f'fill="{_SUBTLE}">Users reached per combination (k)</text>'
    )

    # ---- set-size panel header ----
    parts.append(
        f'<text x="{left_pad:.0f}" y="{matrix_y0 - 16:.1f}" font-size="15" '
        f'fill="{_SUBTLE}">Set size (k)</text>'
    )

    # ---- set-size bars + set-name labels (left panel) ----
    for r, s in enumerate(_SETS):
        cy = row_cy(r)
        total = totals[s]
        bar_len = (total / max_total) * (setbar_w - 10.0)
        bar_h = 30.0
        bx = setbar_right - bar_len
        by = cy - bar_h / 2.0
        parts.append(
            f'<rect class="setbar" x="{bx:.1f}" y="{by:.1f}" width="{bar_len:.1f}" '
            f'height="{bar_h:.0f}" rx="7" fill="{dot_color}" fill-opacity="0.55">'
            f'<title>{_xml(s)}: {total}k monthly-active users total</title>'
            f'</rect>'
        )
        # Count at the (left) tip of the bar.
        parts.append(
            f'<text x="{bx - 10:.1f}" y="{cy:.1f}" font-size="16" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'text-anchor="end" dominant-baseline="middle">{total}</text>'
        )
        # Set name, between the bars and the matrix.
        parts.append(
            f'<text x="{setbar_right + 20:.1f}" y="{cy:.1f}" font-size="19" '
            f'font-weight="600" fill="{_INK}" dominant-baseline="middle">'
            f'{_xml(s)}</text>'
        )

    # ---- one group per combination: size bar + matrix column + connector ----
    for i, (members, size) in enumerate(_COMBINATIONS):
        cid = _combo_id(members)
        cx = col_cx(i)
        member_rows = [r for r, s in enumerate(_SETS) if s in members]
        tip = (
            f"{' + '.join(members)}: {size}k users"
            if len(members) > 1
            else f"{members[0]} only: {size}k users"
        )

        parts.append(f'<g class="combo {cid}">')

        # -- intersection-size bar (the defining mark of an UpSet plot) --
        # Drawn statically at full height, sitting on the panel baseline.
        # No entrance animation: the frozen first frame must never look
        # empty, and a comparison of counts reveals nothing extra in motion.
        bar_h = isize_bar_h(size)
        bar_x = cx - col_w * 0.30
        bar_w = col_w * 0.60
        bar_y = isize_base_y - bar_h
        parts.append(
            f'<g class="ibar">'
            f'<title>{_xml(tip)}</title>'
            f'<rect class="isize" x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_w:.1f}" '
            f'height="{bar_h:.1f}" rx="6" fill="{bar_color}"/>'
            f'</g>'
        )
        # Count label above the bar (always visible).
        parts.append(
            f'<text x="{cx:.1f}" y="{bar_y - 12:.1f}" font-size="16" '
            f'font-family="Roboto Mono, monospace" font-weight="600" '
            f'fill="{_INK}" text-anchor="middle">{size}</text>'
        )

        # -- connector line joining this column's active dots --
        if len(member_rows) > 1:
            y_top = row_cy(min(member_rows))
            y_bot = row_cy(max(member_rows))
            parts.append(
                f'<line class="conn" x1="{cx:.1f}" y1="{y_top:.1f}" '
                f'x2="{cx:.1f}" y2="{y_bot:.1f}" stroke="{dot_color}" '
                f'stroke-width="5" stroke-linecap="round"/>'
            )

        # -- matrix dots for this column (active + inactive) --
        parts.append('<g class="dotcol">')
        for r in range(n_sets):
            cy_dot = row_cy(r)
            active = r in member_rows
            fill = dot_color if active else _EMPTY
            # Active dots carry a class so the OS-adaptive contrast rule can
            # deepen only the filled-in membership marks, never the grey
            # "set absent" placeholders.
            cls = ' class="activedot"' if active else ""
            parts.append(
                f'<circle{cls} cx="{cx:.1f}" cy="{cy_dot:.1f}" r="{dot_r:.1f}" '
                f'fill="{fill}"/>'
            )
        parts.append('</g>')

        # -- invisible hit-rect: keyboard focus + hover target for the column --
        hit_y = top_pad - 10
        hit_h = (matrix_y0 + n_sets * row_h) - hit_y
        parts.append(
            f'<rect class="hit" x="{cx - col_w / 2:.1f}" y="{hit_y:.1f}" '
            f'width="{col_w:.1f}" height="{hit_h:.1f}" tabindex="0" '
            f'role="img" aria-label="{_xml(tip)}">'
            f'<title>{_xml(tip)}</title></rect>'
        )

        parts.append('</g>')  # /combo

    parts.append(fullscreen_control(width, height, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the UpSet-plot SVG to the skill's ``svg-examples`` folder.

    The ``--mode`` flag selects the interactivity mode of the emitted SVG
    (``self-contained`` / ``external`` / ``static``); see
    :func:`_interactive.fullscreen_control`.
    """
    render_cli(__file__, "upset", build_svg, description="Render the UpSet-plot SVG.")


if __name__ == "__main__":
    main()

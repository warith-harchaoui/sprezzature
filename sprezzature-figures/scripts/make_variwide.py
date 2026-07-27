#!/usr/bin/env python3
"""
make_variwide — a variable-width column chart (variwide) as hand-authored SVG.

A **variwide** column chart encodes two measures at once. Each column's
**height** is the first measure and its **width** is the second, so the
**area** of every column reads as their product. Here the height is GDP
per capita (thousands of US dollars), the width is population, and the
area of each column is therefore the country's **total GDP** — the two
levers of national output shown in a single mark.

Eight economies are laid out left to right in a continuous band (no gaps
between columns), sorted by GDP per capita so the tops fall in a clean
staircase. The reader sees instantly that a tall, narrow bar (Germany,
United States) and a short, wide bar (China, India) can enclose similar
*area* — the same total output reached two different ways. Every column
carries its height value on top, its width value along the shared
baseline axis, and an area (total-GDP) label centred inside.

This generator builds the SVG string by hand — no matplotlib / seaborn /
plotly, no Vega — because a variwide axis is a **non-uniform** x-axis
(tick positions are the cumulative widths, not evenly spaced categories),
which a categorical grammar cannot express directly. It matches the
sprezzature-* house style: Roboto, the Apple-ish palette, rounded top corners,
ink ``#1D1D1F``, secondary ``#6E6E73``, white background.

The figure is **static**: it is a snapshot ranking, so every column is
drawn at ``t=0`` and nothing animates in. Each column carries a native
``<title>`` tooltip and a keyboard focus ring for interactive readers.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/variwide.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

# The house-style palette lives alongside this file, in _style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402


# ------------------------------------------------------------------
# Communicative real data — the eight largest economies, 2023.
# ``pop`` is population in millions (column WIDTH); ``gdp_cap`` is GDP
# per capita in thousands of US dollars (column HEIGHT). Their product,
# ``pop * gdp_cap / 1000``, is total GDP in trillions of US dollars —
# the column AREA. Figures are World Bank / IMF 2023 estimates, rounded.
# ------------------------------------------------------------------
COUNTRIES: List[Dict[str, object]] = [
    {"name": "United States", "iso": "USA", "pop": 335.0, "gdp_cap": 81.7, "color": "Blue"},
    {"name": "Germany", "iso": "DEU", "pop": 84.0, "gdp_cap": 52.7, "color": "Purple"},
    {"name": "United Kingdom", "iso": "GBR", "pop": 67.0, "gdp_cap": 48.9, "color": "Teal"},
    {"name": "France", "iso": "FRA", "pop": 68.0, "gdp_cap": 44.5, "color": "Mint"},
    {"name": "Japan", "iso": "JPN", "pop": 124.0, "gdp_cap": 33.9, "color": "Green"},
    {"name": "China", "iso": "CHN", "pop": 1411.0, "gdp_cap": 12.6, "color": "Red"},
    {"name": "Brazil", "iso": "BRA", "pop": 216.0, "gdp_cap": 10.4, "color": "Orange"},
    {"name": "India", "iso": "IND", "pop": 1429.0, "gdp_cap": 2.6, "color": "Yellow"},
]


def _fmt_total(pop: float, gdp_cap: float) -> str:
    """Format total GDP (the column area) in trillions of US dollars.

    Parameters
    ----------
    pop : float
        Population in millions (column width).
    gdp_cap : float
        GDP per capita in thousands of US dollars (column height).

    Returns
    -------
    str
        E.g. ``"$27.4T"`` — population times per-capita, back to trillions.
    """
    total_trillions = pop * gdp_cap / 1000.0
    return f"${total_trillions:.1f}T"


def _fmt_pop(pop: float) -> str:
    """Format a population figure in millions or billions.

    Parameters
    ----------
    pop : float
        Population in millions.

    Returns
    -------
    str
        ``"335M"`` under a billion, ``"1.41B"`` at or above it.
    """
    if pop >= 1000.0:
        return f"{pop / 1000.0:.2f}B"
    return f"{pop:.0f}M"


# ------------------------------------------------------------------
# SVG assembly
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full variwide-column SVG string.

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
    palette = load_palette(accessibility)
    ink = "#1D1D1F"
    secondary = "#6E6E73"
    white = "#FFFFFF"

    # --- canvas geometry -----------------------------------------
    # Poster-size panel with generous headroom above the tallest column
    # (for its value label) and a baseline band below (for width ticks
    # and the axis title).
    width = 1440
    height = 968
    m_left = 92
    m_right = 60
    m_top = 210          # clear band for title + subtitle + legend
    baseline_y = 786     # y of the shared column baseline
    axis_title_y = 936   # y of the width-axis title (below the callout row)

    plot_w = width - m_left - m_right
    plot_h = baseline_y - m_top

    # --- scales --------------------------------------------------
    # WIDTH: population maps onto the total plot width, so columns tile
    # the band edge to edge with no gaps (the defining variwide look).
    total_pop = sum(float(c["pop"]) for c in COUNTRIES)
    # HEIGHT: GDP per capita maps onto the plot height. A little headroom
    # (max scaled to 0.94 of plot_h) keeps the tallest value label clear.
    max_gdp_cap = max(float(c["gdp_cap"]) for c in COUNTRIES)
    height_scale = (plot_h * 0.94) / max_gdp_cap
    px_per_pop = plot_w / total_pop

    parts: List[str] = []

    # --- document + accessibility --------------------------------
    parts.append(svg_open(width, height, "vw-title", "vw-desc"))
    parts.append(
        '<title id="vw-title">GDP per capita times population equals total '
        'GDP, as column area</title>'
    )
    parts.append(
        '<desc id="vw-desc">A variable-width column chart of the eight largest '
        'economies in 2023. Each column height is GDP per capita, each width is '
        'population, so the area is total GDP. The United States, a tall narrow '
        'column, and China, a short wide one, enclose similar area — 27.4 and '
        '17.8 trillion US dollars — reached two different ways. India is the '
        'widest but shortest column. Illustrative figures, World Bank and IMF '
        '2023 estimates.</desc>'
    )

    # Focus ring for keyboard users; the panel is static, no motion guard.
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside a media query). Colour here is NOT
    # the data encoding — height x width = area carries the numbers, and every
    # column is named in an always-visible callout — so hue is a redundant
    # per-country tag. Under prefers-contrast each column fill (and its matching
    # off-column area label) deepens to its high-contrast value. Under forced
    # colours the columns hand off to the system palette: legitimate here
    # because the country name, the population figure and the column's position
    # on the population axis all identify it with no colour, and the on-column
    # value labels remain the colour-independent readout.
    col_series = {
        f".col-{str(c['iso'])}": palette.get(str(c["color"]), "#007AFF")
        for c in COUNTRIES
    }
    contrast_css = os_adaptive_style(col_series, role="fill", forced=True)
    # Additive OS dark-mode block. White is used both as the page surface and as
    # the on-column area labels, so only the white background RECT is darkened
    # while white text is left alone; the two ink tiers flip to light and the
    # light-grey #C7C7CC label leader darkens so it still reads on the dark page.
    # Column hues carry a redundant tag (area = the encoding) and are untouched.
    dark_css = os_dark_style(
        ink_map={"#1D1D1F": "#F2F2F7", "#6E6E73": "#9C9CA3"},
        screen_blend=False,
        extra='rect[fill="#FFFFFF"]{fill:#0B0B0C;} '
        '[stroke="#C7C7CC"]{stroke:#5A5A5E;}',
    )
    parts.append(
        '<style>'
        '.col{cursor:pointer;transition:filter .12s ease}'
        '.col:hover,.col:focus{filter:brightness(1.06)}'
        '.col:focus{outline:none}'
        '.colframe{fill:none;pointer-events:none}'
        + contrast_css
        + dark_css
        + '</style>'
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="{white}"/>')

    # --- height-axis gridlines (GDP per capita) ------------------
    # A light horizontal reference grid so the reader can read a column's
    # height (per-capita value) off the left axis. Drawn first, under the
    # columns. Ticks at 0, 20, 40, 60, 80 thousand US dollars.
    for tick in (0, 20, 40, 60, 80):
        gy = baseline_y - tick * height_scale
        parts.append(
            f'<line x1="{m_left}" y1="{gy:.1f}" x2="{m_left + plot_w}" '
            f'y2="{gy:.1f}" stroke="#E8E8ED" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{m_left - 14}" y="{gy + 5:.1f}" text-anchor="end" '
            f'font-size="17" font-family="Roboto Mono, monospace" '
            f'fill="{secondary}">${tick}k</text>'
        )
    # Left-axis title, rotated up the side.
    lax_x = 30
    lax_y = m_top + plot_h / 2.0
    parts.append(
        f'<text x="{lax_x}" y="{lax_y:.1f}" font-size="19" fill="{ink}" '
        f'font-weight="600" text-anchor="middle" '
        f'transform="rotate(-90 {lax_x} {lax_y:.1f})">'
        f'Height = GDP per capita (US$ thousands)</text>'
    )

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="72" font-size="38" font-weight="700" '
        f'fill="{ink}">Two ways to build a multi-trillion economy</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="112" font-size="21" fill="{secondary}">'
        f'Column area is total GDP: the United States reaches it with high '
        f'output per person, China with sheer population &#183; World Bank / '
        f'IMF 2023</text>'
    )

    # --- how-to-read legend (glyph strip under the subtitle) -----
    # One line that names the three encodings so the chart is self-teaching:
    # height, width, and the area they enclose.
    leg_y = 162
    leg_x = m_left
    # height glyph — a short vertical rule with up-caps
    parts.append(
        f'<rect x="{leg_x}" y="{leg_y - 15}" width="6" height="30" rx="3" '
        f'fill="{ink}"/>'
    )
    parts.append(
        f'<text x="{leg_x + 18}" y="{leg_y + 5}" font-size="17" fill="{ink}">'
        f'height = output per person</text>'
    )
    # width glyph — a short horizontal rule
    wg_x = leg_x + 320
    parts.append(
        f'<rect x="{wg_x}" y="{leg_y - 3}" width="34" height="6" rx="3" '
        f'fill="{ink}"/>'
    )
    parts.append(
        f'<text x="{wg_x + 46}" y="{leg_y + 5}" font-size="17" fill="{ink}">'
        f'width = population</text>'
    )
    # area glyph — a small filled block
    ag_x = wg_x + 250
    parts.append(
        f'<rect x="{ag_x}" y="{leg_y - 13}" width="26" height="26" rx="5" '
        f'fill="{ink}" opacity="0.16"/>'
    )
    parts.append(
        f'<text x="{ag_x + 38}" y="{leg_y + 5}" font-size="17" fill="{ink}">'
        f'area = total GDP</text>'
    )

    # --- pass 1: geometry -----------------------------------------
    # Walk the countries once to fix every column's pixel box and its
    # cumulative-width edges. Labelling is a separate pass so narrow
    # columns can borrow horizontal room from their wide neighbours.
    cols: List[Dict[str, object]] = []
    x_cursor = float(m_left)
    for c in COUNTRIES:
        pop = float(c["pop"])
        gdp_cap = float(c["gdp_cap"])
        col_w = pop * px_per_pop
        col_h = gdp_cap * height_scale
        cols.append({
            "name": str(c["name"]),
            "iso": str(c["iso"]),
            "pop": pop,
            "gdp_cap": gdp_cap,
            "hex": palette.get(str(c["color"]), "#007AFF"),
            "x": x_cursor,
            "w": col_w,
            "h": col_h,
            "y": baseline_y - col_h,
            "cx": x_cursor + col_w / 2.0,
        })
        x_cursor += col_w

    # --- shared baseline + cumulative-width axis -----------------
    # Drawn first so the columns sit on top of it. The baseline runs the
    # full width; short ticks mark each column edge so the non-uniform
    # (population-weighted) x-axis is explicit.
    parts.append(
        f'<line x1="{m_left}" y1="{baseline_y}" x2="{m_left + plot_w}" '
        f'y2="{baseline_y}" stroke="{ink}" stroke-width="2"/>'
    )
    for col in cols:
        parts.append(
            f'<line x1="{col["x"]:.1f}" y1="{baseline_y}" x2="{col["x"]:.1f}" '
            f'y2="{baseline_y + 6}" stroke="{secondary}" stroke-width="1"/>'
        )
    parts.append(
        f'<line x1="{m_left + plot_w:.1f}" y1="{baseline_y}" '
        f'x2="{m_left + plot_w:.1f}" y2="{baseline_y + 6}" '
        f'stroke="{secondary}" stroke-width="1"/>'
    )

    # --- pass 2: columns + on-column labels ----------------------
    for col in cols:
        name = str(col["name"])
        pop = float(col["pop"])
        gdp_cap = float(col["gdp_cap"])
        base_hex = str(col["hex"])
        col_w = float(col["w"])
        col_h = float(col["h"])
        col_x = float(col["x"])
        col_y = float(col["y"])
        cxm = float(col["cx"])

        # Rounded TOP corners only, so columns sit flush on the baseline
        # and tile edge-to-edge with a thin white seam between them.
        r = min(9.0, col_w / 2.0)
        seam = 1.2  # hairline gap so adjacent fills stay distinguishable
        cx = col_x + seam / 2.0
        cw = max(0.0, col_w - seam)
        path = (
            f'M{cx:.2f},{baseline_y:.1f} '
            f'L{cx:.2f},{col_y + r:.2f} '
            f'Q{cx:.2f},{col_y:.2f} {cx + r:.2f},{col_y:.2f} '
            f'L{cx + cw - r:.2f},{col_y:.2f} '
            f'Q{cx + cw:.2f},{col_y:.2f} {cx + cw:.2f},{col_y + r:.2f} '
            f'L{cx + cw:.2f},{baseline_y:.1f} Z'
        )
        tip = (
            f"{name}: ${gdp_cap:.1f}k per capita x {_fmt_pop(pop)} people "
            f"= {_fmt_total(pop, gdp_cap)} total GDP"
        )
        iso = str(col["iso"])
        parts.append(
            f'<path class="col col-{iso}" d="{path}" fill="{base_hex}" '
            f'tabindex="0" '
            f'role="img" aria-label="{xml_escape(tip)}">'
            f'<title>{xml_escape(tip)}</title></path>'
        )

        # (The height value label on top of the column is placed in a
        # separate de-collided pass below, so the three near-equal-height
        # European columns do not overprint each other.)

        # --- area (total GDP) label, centred inside the column -------
        # Only when the column is tall AND wide enough to hold the text
        # without crowding; otherwise it rides down to the callout row.
        area_label = _fmt_total(pop, gdp_cap)
        col["area_inside"] = col_h > 92 and col_w > 84
        if col["area_inside"]:
            parts.append(
                f'<text x="{cxm:.1f}" y="{col_y + col_h / 2.0 + 8:.1f}" '
                f'text-anchor="middle" font-size="26" font-weight="700" '
                f'fill="{white}">{area_label}</text>'
            )
            parts.append(
                f'<text x="{cxm:.1f}" y="{col_y + col_h / 2.0 + 32:.1f}" '
                f'text-anchor="middle" font-size="14" fill="{white}" '
                f'opacity="0.85">total GDP</text>'
            )

    # --- pass 2b: de-collided height labels (on top of columns) ---
    # The three European columns are almost the same height, so their
    # per-capita labels would overprint if centred. Sweep them apart on x
    # (same idea as the baseline callouts) and lift each a little higher,
    # then drop a hairline leader from the label down to the column top.
    top_gap = 62.0
    top_anchors = [float(col["cx"]) for col in cols]
    top_placed: List[float] = []
    for ax in top_anchors:
        target = ax if not top_placed else max(ax, top_placed[-1] + top_gap)
        top_placed.append(target)
    top_overflow = top_placed[-1] - (m_left + plot_w)
    if top_overflow > 0:
        top_placed = [p - top_overflow for p in top_placed]
    for col, tx in zip(cols, top_placed):
        cxm = float(col["cx"])
        col_y = float(col["y"])
        gdp_cap = float(col["gdp_cap"])
        moved = abs(tx - cxm) > 1.5
        lab_y = col_y - 16 if not moved else col_y - 30
        if moved:
            parts.append(
                f'<path d="M{cxm:.1f},{col_y - 4:.1f} '
                f'L{cxm:.1f},{col_y - 10:.1f} L{tx:.1f},{col_y - 16:.1f} '
                f'L{tx:.1f},{lab_y - 3:.1f}" fill="none" stroke="#C7C7CC" '
                f'stroke-width="1.2"/>'
            )
        parts.append(
            f'<text x="{tx:.1f}" y="{lab_y:.1f}" text-anchor="middle" '
            f'font-size="20" font-weight="700" '
            f'font-family="Roboto Mono, monospace" fill="{ink}">'
            f'${gdp_cap:.1f}k</text>'
        )

    # --- pass 3: de-collided baseline callouts -------------------
    # Each column names itself below the axis (country, population, and —
    # for narrow columns — the total-GDP area that could not fit inside).
    # Because China and India swallow most of the width, the six smaller
    # columns cluster tightly; a min-gap sweep pushes their labels apart
    # and a thin leader line ties each pushed label back to its column.
    label_y = baseline_y + 30      # first text line of a callout
    min_gap = 96.0                 # minimum horizontal pitch between anchors
    anchors = [float(col["cx"]) for col in cols]
    # Left-to-right sweep: never let a label start closer than min_gap to
    # the one before it. Clamp within the plot so nothing clips the edges.
    placed: List[float] = []
    for ax in anchors:
        target = ax if not placed else max(ax, placed[-1] + min_gap)
        placed.append(target)
    # If the sweep pushed the last label past the right edge, slide the
    # whole run left so it stays inside the canvas.
    overflow = placed[-1] - (m_left + plot_w)
    if overflow > 0:
        placed = [p - overflow for p in placed]

    for col, lx in zip(cols, placed):
        cxm = float(col["cx"])
        base_hex = str(col["hex"])
        pop = float(col["pop"])
        gdp_cap = float(col["gdp_cap"])
        # Leader line only when the label had to move off its column centre.
        if abs(lx - cxm) > 1.5:
            parts.append(
                f'<path d="M{cxm:.1f},{baseline_y + 9:.1f} '
                f'L{cxm:.1f},{baseline_y + 15:.1f} '
                f'L{lx:.1f},{baseline_y + 20:.1f} '
                f'L{lx:.1f},{label_y - 12:.1f}" fill="none" '
                f'stroke="#C7C7CC" stroke-width="1.2"/>'
            )
        parts.append(
            f'<text x="{lx:.1f}" y="{label_y:.1f}" text-anchor="middle" '
            f'font-size="18" font-weight="600" fill="{ink}">'
            f'{xml_escape(str(col["name"]))}</text>'
        )
        parts.append(
            f'<text x="{lx:.1f}" y="{label_y + 22:.1f}" text-anchor="middle" '
            f'font-size="15" font-family="Roboto Mono, monospace" '
            f'fill="{secondary}">{_fmt_pop(pop)}</text>'
        )
        # Narrow columns show their area (total GDP) here, coloured to match
        # the column so the eye can pair callout to bar.
        if not col["area_inside"]:
            parts.append(
                f'<text class="area-lbl col-{col["iso"]}" '
                f'x="{lx:.1f}" y="{label_y + 44:.1f}" '
                f'text-anchor="middle" font-size="15" font-weight="700" '
                f'fill="{base_hex}">{_fmt_total(pop, gdp_cap)}</text>'
            )

    # --- width-axis title (bottom, once) -------------------------
    parts.append(
        f'<text x="{m_left + plot_w / 2.0:.1f}" y="{axis_title_y}" '
        f'text-anchor="middle" font-size="19" font-weight="600" fill="{ink}">'
        f'Width = population &#183; column widths sum to '
        f'{_fmt_pop(total_pop)} people</text>'
    )

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the variwide-column SVG to the canonical assets path.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "variwide",
        build_svg,
        description="Write the house-style variwide-column SVG example.",
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
make_bullet — a KPI bullet-graph panel rendered as a hand-authored SVG.

A **bullet graph** (Few, *Information Dashboard Design*, 2006) is the
compact, honest replacement for a dashboard gauge or a lone big number.
Each row packs four coordinated marks onto one horizontal scale:

* three **qualitative bands** (poor / satisfactory / good), shaded from
  dark to light so the reader ranks them without a legend;
* a thin **measure bar** — the value actually achieved;
* a short **target tick** — the goal to beat;
* a **value label** with the number and its progress against target.

Five KPIs are stacked and left-aligned so the eye sweeps one column of
measure bars and instantly sees which lag their target. This generator
builds the SVG string by hand (no matplotlib / seaborn / plotly, no
Vega) because the four-mark-per-row packing and the per-row independent
scales are cleaner to place directly than to coax out of a layered
grammar. It matches the sprezzature-* house style: Roboto, the Apple-ish
palette, rounded corners, ink ``#1D1D1F``, secondary ``#6E6E73``, white
background.

The figure is **static**: a bullet graph is a snapshot of where each
metric stands right now, so every mark is drawn at ``t=0`` and nothing
animates in. Each measure bar carries a native ``<title>`` tooltip and a
keyboard focus ring.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/bullet.svg``.

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
# Communicative fake data — a small SaaS company's Q3 scorecard.
# Each KPI states, in plain business terms, what it measures, the value
# reached this quarter, the target to beat, the axis maximum, and the
# two band edges (poor|ok and ok|good) on the same unit. ``higher`` says
# whether beating target means going up (revenue, signups) or down
# (latency, churn) — a bullet graph reads either way once the bands are
# shaded correctly, so we shade poor→good in the beneficial direction.
# ------------------------------------------------------------------
KPIS: List[Dict[str, object]] = [
    {
        "name": "New revenue",
        "unit": "$k",
        "value": 268.0,
        "target": 250.0,
        "axis_max": 320.0,
        "bands": [150.0, 220.0],  # poor < 150 | ok 150–220 | good > 220
        "higher": True,
    },
    {
        "name": "Trial signups",
        "unit": "/wk",
        "value": 1180.0,
        "target": 1400.0,
        "axis_max": 1800.0,
        "bands": [900.0, 1350.0],
        "higher": True,
    },
    {
        "name": "Activation rate",
        "unit": "%",
        "value": 47.0,
        "target": 45.0,
        "axis_max": 70.0,
        "bands": [30.0, 42.0],
        "higher": True,
    },
    {
        "name": "p95 API latency",
        "unit": "ms",
        "value": 132.0,
        "target": 120.0,
        "axis_max": 300.0,
        "bands": [200.0, 120.0],  # good < 120 | ok 120–200 | poor > 200
        "higher": False,
    },
    {
        "name": "Monthly churn",
        "unit": "%",
        "value": 2.4,
        "target": 2.0,
        "axis_max": 6.0,
        "bands": [4.0, 2.5],  # good < 2.5 | ok 2.5–4 | poor > 4
        "higher": False,
    },
]


def _fmt(value: float) -> str:
    """Format a KPI number: drop a trailing ``.0``, keep one decimal else.

    Parameters
    ----------
    value : float
        The number to render in a label.

    Returns
    -------
    str
        ``"268"`` for whole values, ``"2.4"`` for fractional ones.
    """
    if abs(value - round(value)) < 1e-9:
        # No thousands separator: in the mono value font a comma or thin
        # space opens an ugly gap, and four-digit KPIs read fine as-is.
        return f"{int(round(value))}"
    return f"{value:.1f}"


def _band_hex(palette: Dict[str, str]) -> List[str]:
    """Return the three qualitative-band fills, poor → good.

    A **sequential single-hue ramp** of the house Blue — a pale tint for
    "poor", a mid tint for "satisfactory", a rich saturated tint for
    "good" — so the bands read as one ordered zone the eye ranks without a
    legend, and that order survives greyscale (lightness climbs
    monotonically toward "good"). One hue, not a red/amber/green traffic
    light, keeps the backdrop calm and never trips the CVD-unsafe
    red+green pairing. The steps are light enough that the dark measure
    bar and the orange target tick both stay crisp on top. Source:
    <https://harchaoui.org/warith/colors/>.

    Parameters
    ----------
    palette : dict of str to str
        The house palette mapping.

    Returns
    -------
    list of str
        ``[poor, satisfactory, good]`` hex strings, palest first.
    """
    # Three tints of the Apple Blue #007AFF, mixed toward white. Lightness
    # rises poor → good so the ranking reads even in greyscale; all three
    # stay pale enough to carry the dark navy bar and orange tick legibly,
    # with a clear step between each so the zones separate at a glance.
    return ["#DCEAFB", "#B2D3F5", "#7EB8F0"]


# ------------------------------------------------------------------
# SVG assembly
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full KPI bullet-graph SVG string.

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
    green = palette.get("Green", "#34C759")
    red = palette.get("Red", "#FF3B30")
    orange = palette.get("Orange", "#FF9500")
    band_fills = _band_hex(palette)
    # The measure bar is a deep navy ink — darker than the darkest band so
    # the value always reads on top of the blue ramp, yet warmer and less
    # severe than pure black. The target tick is Orange: the complementary
    # hue to the blue backdrop, so it pops without colour-on-colour mud,
    # and it keeps its own tall thin shape (never colour alone).
    bar_ink = "#0A2540"
    tick_color = orange

    # --- canvas geometry -----------------------------------------
    # Poster-size panel. A left gutter holds the KPI name + unit; the
    # track fills the middle; a right gutter holds the value label so
    # every number aligns in its own column.
    width = 1240
    m_left = 60
    m_right = 60
    m_top = 168
    label_w = 236        # KPI name gutter (left of every track)
    value_w = 210        # value-label gutter (right of every track)
    track_x = m_left + label_w
    track_w = width - m_left - m_right - label_w - value_w

    row_h = 118          # vertical pitch between KPI rows
    bar_h = 22           # measure-bar thickness
    band_h = 62          # qualitative-band block height
    n = len(KPIS)
    height = m_top + n * row_h + 56

    parts: List[str] = []

    # Count how many metrics beat their target for the takeaway line.
    def _beats(k: Dict[str, object]) -> bool:
        """Return True when the KPI meets or beats its target."""
        v, t, hi = float(k["value"]), float(k["target"]), bool(k["higher"])
        return v >= t if hi else v <= t

    n_beat = sum(1 for k in KPIS if _beats(k))

    # --- document + accessibility --------------------------------
    parts.append(svg_open(width, height, "bl-title", "bl-desc"))
    parts.append(
        '<title id="bl-title">Q3 growth scorecard as five bullet graphs</title>'
    )
    parts.append(
        f'<desc id="bl-desc">Five key performance indicators drawn as bullet '
        f'graphs. Each row has three shaded qualitative bands (poor, '
        f'satisfactory, good), a dark measure bar for the value reached, and an '
        f'orange tick for the target. {n_beat} of {n} metrics met or beat their '
        f'target this quarter; trial signups and p95 latency fell short.</desc>'
    )

    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule below lives inside a media query). Under
    # prefers-contrast the categorical marks deepen to their high-contrast hues:
    # the target tick (orange) and the pass/miss delta text (green / red). The
    # three qualitative bands are a sequential single-hue blue value ramp
    # (perceptual, greyscale-safe by lightness) so they are left untouched, and
    # forced-colors is left to the browser default — flattening the ramp to the
    # system palette would destroy the poor→good ranking the shading carries.
    contrast_series = {
        ".bu-tick": tick_color,
        ".bu-beat": green,
        ".bu-miss": red,
    }
    adaptive = os_adaptive_style(contrast_series, role="fill")
    # Focus ring for keyboard users; the panel is static, no motion guard.
    parts.append(
        '<style>'
        '.bar{cursor:pointer}'
        '.bar:hover,.bar:focus{stroke:#1D1D1F;stroke-width:2}'
        '.bar:focus{outline:none}'
        + adaptive
        # Paper + ink flip to a dark surface; the pale-blue band ramp, the deep
        # navy measure bar and the orange target tick are all bespoke hues that
        # keep their contrast against each other, so they are left untouched.
        + os_dark_style()
        + '</style>'
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="66" font-size="34" font-weight="700" '
        f'fill="{ink}">Three of five targets cleared in Q3</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="104" font-size="20" fill="{secondary}">'
        f'Revenue, activation and churn beat plan; trial signups and API '
        f'latency still trail the goal &#183; illustrative</text>'
    )

    # --- shared legend (its own line under the subtitle) ---------
    # Explains the two glyphs once: the ink measure bar and the target
    # tick. Bands rank themselves by shade, so they need no swatch. Sits
    # in the clear band above the first row, right-aligned to the track
    # so it never collides with the subtitle.
    leg_y = 146
    leg_x = track_x + track_w - 236
    # measure-bar glyph
    parts.append(
        f'<rect x="{leg_x}" y="{leg_y - 7}" width="30" height="13" rx="3" '
        f'fill="{bar_ink}"/>'
    )
    parts.append(
        f'<text x="{leg_x + 40}" y="{leg_y + 5}" font-size="17" '
        f'fill="{ink}">measure</text>'
    )
    # target-tick glyph
    tick_gx = leg_x + 158
    parts.append(
        f'<rect class="bu-tick" x="{tick_gx}" y="{leg_y - 14}" width="5" '
        f'height="27" rx="2.5" '
        f'fill="{tick_color}"/>'
    )
    parts.append(
        f'<text x="{tick_gx + 16}" y="{leg_y + 5}" font-size="17" '
        f'fill="{ink}">target</text>'
    )

    # --- rows ----------------------------------------------------
    for i, k in enumerate(KPIS):
        name = str(k["name"])
        unit = str(k["unit"])
        value = float(k["value"])
        target = float(k["target"])
        axis_max = float(k["axis_max"])
        bands = [float(b) for b in k["bands"]]  # type: ignore[union-attr]
        higher = bool(k["higher"])

        row_top = m_top + i * row_h
        band_top = row_top
        band_mid = band_top + band_h / 2.0

        def sx(v: float, _max: float = axis_max) -> float:
            """Map a value in KPI units to an x pixel on this row's track."""
            return track_x + (v / _max) * track_w

        # --- qualitative bands (poor / ok / good), darkest = poor ----
        # For higher-is-better the beneficial end is the right (max);
        # for lower-is-better it is the left (0). We paint three blocks
        # so "good" is always the lightest shade at the beneficial end.
        if higher:
            edges = [0.0, bands[0], bands[1], axis_max]
            fills = band_fills  # poor, ok, good left→right
        else:
            # bands stored as [ok|poor edge, good|ok edge]; good is nearest 0.
            edges = [0.0, bands[1], bands[0], axis_max]
            fills = list(reversed(band_fills))  # good, ok, poor left→right
        # Clip the three square band blocks to one rounded-rect track so the
        # whole backdrop carries the house rounded corners as a single
        # seamless object (no per-block corner rounding, no visible seams).
        clip_id = f"track-clip-{i}"
        parts.append(
            f'<clipPath id="{clip_id}"><rect x="{track_x:.1f}" '
            f'y="{band_top:.1f}" width="{track_w:.1f}" height="{band_h}" '
            f'rx="9"/></clipPath>'
        )
        parts.append(f'<g clip-path="url(#{clip_id})">')
        for j in range(3):
            x0 = sx(edges[j])
            x1 = sx(edges[j + 1])
            parts.append(
                f'<rect x="{x0:.1f}" y="{band_top:.1f}" '
                f'width="{max(0.0, x1 - x0):.2f}" height="{band_h}" '
                f'fill="{fills[j]}"/>'
            )
        parts.append('</g>')

        # --- measure bar (the value reached) -------------------------
        beats = _beats(k)
        bar_fill = bar_ink
        bar_x = track_x
        bar_end = sx(value)
        bar_y = band_mid - bar_h / 2.0
        pct = round(100 * value / target) if target else 0
        gap_word = "of target" if beats else "of target"
        tip = f"{name}: {_fmt(value)} {unit} — {pct}% {gap_word} ({_fmt(target)} {unit})"
        parts.append(
            f'<rect class="bar" x="{bar_x:.1f}" y="{bar_y:.1f}" '
            f'width="{max(0.0, bar_end - bar_x):.2f}" height="{bar_h}" rx="5" '
            f'fill="{bar_fill}" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}"><title>{xml_escape(tip)}</title>'
            f'</rect>'
        )

        # --- target tick ---------------------------------------------
        tx = sx(target)
        tick_h = band_h - 12
        tick_top = band_mid - tick_h / 2.0
        parts.append(
            f'<rect class="bu-tick" x="{tx - 2.5:.1f}" y="{tick_top:.1f}" '
            f'width="5" '
            f'height="{tick_h:.1f}" rx="2.5" fill="{tick_color}"/>'
        )

        # --- KPI name + unit (left gutter) ---------------------------
        parts.append(
            f'<text x="{m_left}" y="{band_mid - 4:.1f}" font-size="23" '
            f'font-weight="600" fill="{ink}">{xml_escape(name)}</text>'
        )
        parts.append(
            f'<text x="{m_left}" y="{band_mid + 22:.1f}" font-size="16" '
            f'fill="{secondary}">measured in {xml_escape(unit)}</text>'
        )

        # --- value label + progress (right gutter) -------------------
        # Value in ink for weight; the pass/miss delta below it, coloured
        # green/red AND spelled out (never colour alone).
        val_x = track_x + track_w + 22
        delta_color = green if beats else red
        arrow = "✓" if beats else "✗"
        delta_word = "on target" if beats else "below target"
        # For lower-is-better, "below target" would read backwards, so
        # phrase the miss/beat in plain over/under-the-goal language.
        if not higher:
            delta_word = "on target" if beats else "over target"
        parts.append(
            f'<text x="{val_x:.1f}" y="{band_mid - 4:.1f}" font-size="27" '
            f'font-weight="700" font-family="Roboto Mono, monospace" '
            f'fill="{ink}">{_fmt(value)}<tspan font-size="17" '
            f'font-family="Roboto, sans-serif" fill="{secondary}"> {xml_escape(unit)}</tspan></text>'
        )
        delta_cls = "bu-beat" if beats else "bu-miss"
        parts.append(
            f'<text class="{delta_cls}" x="{val_x:.1f}" y="{band_mid + 22:.1f}" '
            f'font-size="16" '
            f'font-weight="600" fill="{delta_color}">{arrow} {pct}% '
            f'{delta_word}</text>'
        )

    # --- band-scale caption (bottom, once) -----------------------
    # Names the three shades so a first-time reader knows dark→light is
    # poor→good, without a per-row legend.
    cap_y = height - 26
    cap_x = track_x
    swatch = 26
    labels = ["Poor", "Satisfactory", "Good"]
    parts.append(
        f'<text x="{m_left}" y="{cap_y + 4:.1f}" font-size="16" '
        f'fill="{secondary}">Bands:</text>'
    )
    for j, lab in enumerate(labels):
        sxp = cap_x + j * 190
        parts.append(
            f'<rect x="{sxp:.1f}" y="{cap_y - 12:.1f}" width="{swatch}" '
            f'height="16" rx="4" fill="{band_fills[j]}"/>'
        )
        parts.append(
            f'<text x="{sxp + swatch + 9:.1f}" y="{cap_y + 1:.1f}" '
            f'font-size="16" fill="{secondary}">{lab}</text>'
        )

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the bullet-graph SVG to the canonical assets path.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "bullet",
        build_svg,
        description="Write the house-style KPI bullet-graph SVG example.",
    )


if __name__ == "__main__":
    main()

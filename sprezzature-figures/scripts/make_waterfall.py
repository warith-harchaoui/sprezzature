#!/usr/bin/env python3
"""
make_waterfall — a waterfall (bridge) chart rendered as a hand-authored SVG.

A waterfall chart shows how an initial value grows or shrinks through a
sequence of intermediate increments and decrements, arriving at a final
total. Each bar starts where the previous one ended, so the eye reads
cumulative accumulation without having to add the numbers. The final bar
always anchors to zero, making it the natural tool for quarterly P&L
analysis, budget variances, headcount changes, or any quantity that
moves step by step from a starting position.

Positive increments are drawn in green, negative in red, and the opening
and closing totals in the neutral house blue, a convention that reads
without a legend.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import os_adaptive_style, os_dark_style  # noqa: E402
from _render import svg_example_path, write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ---------------------------------------------------------------------------
# Canvas constants
# ---------------------------------------------------------------------------
WIDTH = 1100
HEIGHT = 640
MARGIN_LEFT = 88        # room for Y-axis labels
MARGIN_RIGHT = 44
MARGIN_TOP = 148        # title + subtitle
MARGIN_BOTTOM = 88      # X-axis labels

BAR_GAP = 0.22          # fraction of bar slot reserved as gap between bars

INK = "#1D1D1F"
SECONDARY = "#6E6E73"
BG = "#FFFFFF"
GRIDLINE = "#E5E5EA"
FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

# House palette for waterfall semantics
COLOR_POSITIVE = "#28CD41"    # Green: gains
COLOR_NEGATIVE = "#FF3B30"    # Red: losses
COLOR_TOTAL = "#007AFF"       # Blue: opening and closing totals


# ---------------------------------------------------------------------------
# Demo data: FY-2024 operating income bridge for a mid-size SaaS company.
# Values are in millions of EUR. The story: strong revenue growth and
# efficiency gains are partially offset by a product-refresh investment and
# increased support headcount.
# ---------------------------------------------------------------------------
DEMO_DATA: List[Dict[str, Any]] = [
    {"label": "FY-2023\noperating\nincome", "value": 48.2,  "kind": "total"},
    {"label": "Subscription\nrevenue",       "value": +19.4, "kind": "positive"},
    {"label": "Professional\nservices",      "value": +4.1,  "kind": "positive"},
    {"label": "Upsell /\nexpansion",         "value": +7.8,  "kind": "positive"},
    {"label": "Churn\nimpact",               "value": -5.3,  "kind": "negative"},
    {"label": "R&D\ninvestment",             "value": -11.6, "kind": "negative"},
    {"label": "S&M\nheadcount",             "value": -6.2,  "kind": "negative"},
    {"label": "Infrastructure\nefficiency", "value": +3.7,  "kind": "positive"},
    {"label": "G&A\nreduction",             "value": +1.4,  "kind": "positive"},
    {"label": "FY-2024\noperating\nincome",  "value": 61.5,  "kind": "total"},
]


def _y_axis_ticks(y_min: float, y_max: float, n: int = 6) -> List[float]:
    """Return n evenly spaced tick values covering the range.

    Parameters
    ----------
    y_min, y_max : float
        Data range.
    n : int
        Number of tick levels.

    Returns
    -------
    list[float]
        Tick positions.
    """
    step_raw = (y_max - y_min) / (n - 1)
    # Round step to a nice number
    magnitude = 10 ** int(len(str(int(abs(step_raw)))) - 1)
    step = max(magnitude, round(step_raw / magnitude) * magnitude)
    start = (int(y_min / step) - 1) * step
    return [start + i * step for i in range(n + 2) if start + i * step <= y_max + step]


def build_svg(
    data: List[Dict[str, Any]],
    *,
    title: str = "FY-2024 Operating Income Bridge",
    subtitle: str = "Millions of EUR, FY-2023 → FY-2024",
    accessibility: str = "universal",
) -> str:
    """Render the waterfall chart as an SVG string.

    Parameters
    ----------
    data : list[dict[str, Any]]
        Rows with keys ``label`` (str), ``value`` (float), ``kind``
        ("positive" | "negative" | "total").
    title : str
        Chart headline.
    subtitle : str
        One-line subtitle displayed beneath the title.
    accessibility : str
        Palette level passed to :func:`_style.load_palette`.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    # ------------------------------------------------------------------
    # Compute running totals so each bar knows where to start
    # ------------------------------------------------------------------
    bars: List[Dict[str, Any]] = []
    running = 0.0
    for row in data:
        kind = row["kind"]
        val = float(row["value"])
        if kind == "total":
            # Total bars always anchor at zero
            bars.append({"label": row["label"], "value": val,
                         "base": 0.0, "kind": kind, "raw": val})
            running = val
        else:
            base = running
            bars.append({"label": row["label"], "value": abs(val),
                         "base": base if val >= 0 else base + val,
                         "kind": kind, "raw": val})
            running += val

    # ------------------------------------------------------------------
    # Y-axis range: add 15% headroom above and below the extremes
    # ------------------------------------------------------------------
    all_tops = [b["base"] + (b["value"] if b["raw"] >= 0 else 0) for b in bars]
    all_bots = [b["base"] + (0 if b["raw"] >= 0 else -b["value"]) for b in bars]
    # For total bars base=0, value=actual total
    all_vals = [b["raw"] for b in bars]
    data_min = min(0.0, min(all_bots + all_vals))
    data_max = max(all_tops + all_vals)
    headroom = (data_max - data_min) * 0.15
    y_min = data_min - headroom
    y_max = data_max + headroom

    # Plot area
    plot_w = WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    plot_h = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM

    def data_to_px(v: float) -> float:
        """Map a data value to a pixel Y coordinate (top = small values)."""
        return MARGIN_TOP + plot_h * (1.0 - (v - y_min) / (y_max - y_min))

    y_zero_px = data_to_px(0.0)

    n = len(bars)
    slot_w = plot_w / n
    bar_w = slot_w * (1.0 - BAR_GAP)

    # ------------------------------------------------------------------
    # Axis ticks
    # ------------------------------------------------------------------
    ticks = [t for t in _y_axis_ticks(y_min, y_max, 6)
             if y_min <= t <= y_max]

    # ------------------------------------------------------------------
    # Start building SVG
    # ------------------------------------------------------------------
    # os_adaptive_style takes a selector->hex dict; pass empty dict for no
    # series-specific contrast overrides (no dynamic palette needed here).
    style = os_adaptive_style({}) + "\n" + os_dark_style()
    fs_ctrl = fullscreen_control(WIDTH, HEIGHT)

    lines: List[str] = []
    lines.append(
        f'<svg role="img" aria-label="{escape(title)}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'font-family="{FONT}" '
        f'style="background:{BG};max-width:100%;height:auto">'
    )
    lines.append(f"<style>{style}</style>")
    lines.append(f'<desc>{escape(subtitle)}</desc>')

    # Background
    lines.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # Title
    lines.append(
        f'<text x="{MARGIN_LEFT}" y="56" font-size="28" font-weight="600" '
        f'fill="{INK}" letter-spacing="-0.3">{escape(title)}</text>'
    )
    lines.append(
        f'<text x="{MARGIN_LEFT}" y="88" font-size="16" fill="{SECONDARY}">'
        f'{escape(subtitle)}</text>'
    )

    # Legend
    legend_x = MARGIN_LEFT
    legend_y = 112
    for color, label in [
        (COLOR_POSITIVE, "Gain"), (COLOR_NEGATIVE, "Loss"), (COLOR_TOTAL, "Total"),
    ]:
        lines.append(
            f'<rect x="{legend_x}" y="{legend_y - 10}" width="12" height="12" '
            f'rx="2" fill="{color}"/>'
        )
        lines.append(
            f'<text x="{legend_x + 17}" y="{legend_y}" font-size="13" '
            f'fill="{SECONDARY}">{label}</text>'
        )
        legend_x += 80

    # Y-axis gridlines and tick labels
    for tick in ticks:
        py = data_to_px(tick)
        if MARGIN_TOP <= py <= MARGIN_TOP + plot_h:
            lines.append(
                f'<line x1="{MARGIN_LEFT}" y1="{py:.1f}" '
                f'x2="{MARGIN_LEFT + plot_w}" y2="{py:.1f}" '
                f'stroke="{GRIDLINE}" stroke-width="1"/>'
            )
            label_str = f"{tick:,.0f}"
            lines.append(
                f'<text x="{MARGIN_LEFT - 8}" y="{py + 5:.1f}" '
                f'font-size="12" fill="{SECONDARY}" text-anchor="end" '
                f'font-family="{FONT_MONO}">{label_str}</text>'
            )

    # Zero line (drawn over gridlines)
    lines.append(
        f'<line x1="{MARGIN_LEFT}" y1="{y_zero_px:.1f}" '
        f'x2="{MARGIN_LEFT + plot_w}" y2="{y_zero_px:.1f}" '
        f'stroke="{INK}" stroke-width="1.5" opacity="0.35"/>'
    )

    # Connector lines between bars (dashed, from top/bottom of one bar to base of next)
    for i, bar in enumerate(bars[:-1]):
        # End of current bar
        if bar["kind"] == "total":
            connector_y = data_to_px(bar["raw"])
        elif bar["raw"] >= 0:
            connector_y = data_to_px(bar["base"] + bar["value"])
        else:
            connector_y = data_to_px(bar["base"])
        x_right = MARGIN_LEFT + i * slot_w + bar_w
        x_next = MARGIN_LEFT + (i + 1) * slot_w
        lines.append(
            f'<line x1="{x_right:.1f}" y1="{connector_y:.1f}" '
            f'x2="{x_next:.1f}" y2="{connector_y:.1f}" '
            f'stroke="{SECONDARY}" stroke-width="1" stroke-dasharray="4 3"/>'
        )

    # Bars
    for i, bar in enumerate(bars):
        x = MARGIN_LEFT + i * slot_w + (slot_w - bar_w) / 2.0
        color = (
            COLOR_TOTAL if bar["kind"] == "total"
            else COLOR_POSITIVE if bar["raw"] >= 0
            else COLOR_NEGATIVE
        )
        # Pixel coordinates of the bar rectangle
        top_val = bar["base"] + bar["value"]
        bot_val = bar["base"]
        if bar["kind"] == "total":
            top_val = bar["raw"]
            bot_val = 0.0
        py_top = data_to_px(max(top_val, bot_val))
        py_bot = data_to_px(min(top_val, bot_val))
        bar_h = max(2.0, py_bot - py_top)

        # Bar rectangle with tooltip
        val_str = f"{bar['raw']:+,.1f}" if bar["kind"] != "total" else f"{bar['raw']:,.1f}"
        tooltip = f"{bar['label'].replace(chr(10), ' ')}: {val_str}M"
        lines.append(
            f'<rect x="{x:.1f}" y="{py_top:.1f}" width="{bar_w:.1f}" '
            f'height="{bar_h:.1f}" rx="3" fill="{color}" opacity="0.9">'
            f'<title>{escape(tooltip)}</title></rect>'
        )

        # Value label above or below each bar
        label_y = py_top - 6 if bar["raw"] >= 0 or bar["kind"] == "total" else py_bot + 14
        lines.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{label_y:.1f}" '
            f'font-size="11" fill="{INK}" text-anchor="middle" '
            f'font-family="{FONT_MONO}" font-weight="500">{val_str}</text>'
        )

        # X-axis label (split on \n for multi-line)
        label_parts = bar["label"].split("\n")
        label_base_y = MARGIN_TOP + plot_h + 20
        for j, part in enumerate(label_parts):
            lines.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{label_base_y + j * 14:.1f}" '
                f'font-size="11" fill="{INK}" text-anchor="middle">'
                f'{escape(part)}</text>'
            )

    lines.append(fs_ctrl)
    lines.append("</svg>")
    return "\n".join(lines)


def make_waterfall(
    data: List[Dict[str, Any]] | None = None,
    *,
    out: Path | str | None = None,
    title: str = "FY-2024 Operating Income Bridge",
    subtitle: str = "Millions of EUR, FY-2023 → FY-2024",
    width: int = WIDTH,
    height: int = HEIGHT,
) -> Path:
    """Render a waterfall chart and write the SVG to *out*.

    Parameters
    ----------
    data : list[dict[str, Any]] or None
        Rows with keys ``label``, ``value`` (float), ``kind``
        ("positive" | "negative" | "total"). Defaults to DEMO_DATA.
    out : Path, str, or None
        Output file path. Accepts .svg. Defaults to the canonical
        ``assets/svg-examples/waterfall.svg``.
    title : str
        Chart headline.
    subtitle : str
        One-line subtitle displayed beneath the title.
    width : int
        Ignored (canvas is fixed; kept for API parity with other generators).
    height : int
        Ignored.

    Returns
    -------
    Path
        Absolute path to the written SVG file.

    Examples
    --------
    >>> p = make_waterfall()
    >>> p.exists()
    True
    """
    if data is None:
        data = DEMO_DATA
    svg = build_svg(data, title=title, subtitle=subtitle)
    dest = Path(out) if out else svg_example_path(__file__, "waterfall")
    return write_svg(dest, svg)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate a waterfall (bridge) chart.")
    p.add_argument("--out", default=None, help="Output SVG path.")
    p.add_argument("--title", default="FY-2024 Operating Income Bridge")
    p.add_argument("--subtitle", default="Millions of EUR, FY-2023 → FY-2024")
    args = p.parse_args()
    result = make_waterfall(out=args.out, title=args.title, subtitle=args.subtitle)
    print(result)

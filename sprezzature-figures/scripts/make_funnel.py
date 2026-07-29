#!/usr/bin/env python3
"""
make_funnel — a conversion funnel chart rendered as a hand-authored SVG.

A funnel chart shows how a population shrinks stage by stage through a
sequential process. Each stage is a trapezoid whose width is proportional
to the count entering that stage. The taper from left to right makes it
immediately obvious where the biggest drops occur, which is the primary
question in any conversion or retention analysis. A label on each stage
shows the absolute count and the conversion rate from the previous stage.

The typical use is marketing pipeline analysis (website visitors to trial
to paying customers), clinical trial enrolment, or any process where
participants drop out at each step.

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
from _render import svg_example_path, write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ---------------------------------------------------------------------------
# Canvas constants
# ---------------------------------------------------------------------------
WIDTH = 900
HEIGHT = 600
MARGIN_H = 60     # left and right margin
MARGIN_V = 120    # top and bottom margin

INK = "#1D1D1F"
SECONDARY = "#6E6E73"
BG = "#FFFFFF"
FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

# House palette — six distinct hues, darker at the top to guide the eye
STAGE_COLORS = [
    "#007AFF",   # Blue (top: largest audience)
    "#AF52DE",   # Purple
    "#FF9500",   # Orange
    "#28CD41",   # Green
    "#FF3B30",   # Red
    "#79DBDC",   # Turquoise (bottom: smallest group)
]


# ---------------------------------------------------------------------------
# Demo data: SaaS product-led growth funnel, Q3-2024.
# Each stage records the count entering that stage.
# ---------------------------------------------------------------------------
DEMO_DATA: List[Dict[str, Any]] = [
    {"stage": "Website visits",    "count": 124800},
    {"stage": "Trial sign-ups",    "count": 18720},
    {"stage": "Activated users",   "count": 9360},
    {"stage": "Feature adoption",  "count": 4212},
    {"stage": "Upgrade intent",    "count": 1684},
    {"stage": "Paying customers",  "count": 842},
]


def build_svg(
    data: List[Dict[str, Any]],
    *,
    title: str = "Product-Led Growth Funnel — Q3 2024",
    subtitle: str = "Count of users reaching each conversion stage",
) -> str:
    """Render the funnel chart as an SVG string.

    Parameters
    ----------
    data : list[dict[str, Any]]
        Rows with keys ``stage`` (str) and ``count`` (int or float).
        Must have at least two rows.
    title : str
        Chart headline.
    subtitle : str
        One-line subtitle displayed beneath the title.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    counts = [float(row["count"]) for row in data]
    max_count = max(counts)
    n = len(data)

    plot_w = WIDTH - 2 * MARGIN_H
    plot_h = HEIGHT - 2 * MARGIN_V
    # Each stage occupies an equal vertical slice
    slice_h = plot_h / n

    fs_ctrl = fullscreen_control(WIDTH, HEIGHT)

    lines: List[str] = []
    lines.append(
        f'<svg role="img" aria-label="{escape(title)}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'font-family="{FONT}" '
        f'style="background:{BG};max-width:100%;height:auto">'
    )
    lines.append(f'<desc>{escape(subtitle)}</desc>')
    lines.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # Title and subtitle
    lines.append(
        f'<text x="{WIDTH // 2}" y="52" font-size="26" font-weight="600" '
        f'fill="{INK}" text-anchor="middle" letter-spacing="-0.3">'
        f'{escape(title)}</text>'
    )
    lines.append(
        f'<text x="{WIDTH // 2}" y="80" font-size="14" fill="{SECONDARY}" '
        f'text-anchor="middle">{escape(subtitle)}</text>'
    )

    # Funnel trapezoids
    cx = WIDTH / 2.0   # horizontal center
    for i, row in enumerate(data):
        count = float(row["count"])
        stage = row["stage"]
        color = STAGE_COLORS[i % len(STAGE_COLORS)]

        # Half-width of the top and bottom edges of this trapezoid
        half_top = (count / max_count) * (plot_w / 2.0)
        if i + 1 < n:
            next_count = float(data[i + 1]["count"])
            half_bot = (next_count / max_count) * (plot_w / 2.0)
        else:
            # Last stage: taper to a flat bottom (30px half-width)
            half_bot = 30.0

        y_top = MARGIN_V + i * slice_h
        y_bot = y_top + slice_h

        # Trapezoid points: top-left, top-right, bottom-right, bottom-left
        pts = (
            f"{cx - half_top:.1f},{y_top:.1f} "
            f"{cx + half_top:.1f},{y_top:.1f} "
            f"{cx + half_bot:.1f},{y_bot:.1f} "
            f"{cx - half_bot:.1f},{y_bot:.1f}"
        )
        conv_str = ""
        if i > 0:
            rate = count / float(data[i - 1]["count"]) * 100
            conv_str = f" ({rate:.1f}% conversion)"
        tooltip = f"{stage}: {count:,.0f}{conv_str}"
        lines.append(
            f'<polygon points="{pts}" fill="{color}" opacity="0.88">'
            f'<title>{escape(tooltip)}</title></polygon>'
        )

        # Stage label: name on the left, count on the right
        label_y = (y_top + y_bot) / 2.0 + 5
        lines.append(
            f'<text x="{cx - half_top - 10:.1f}" y="{label_y:.1f}" '
            f'font-size="13" fill="{INK}" text-anchor="end">'
            f'{escape(stage)}</text>'
        )
        count_txt = f"{count:,.0f}"
        if i > 0:
            rate = count / float(data[i - 1]["count"]) * 100
            count_txt += f"  ({rate:.1f}%)"
        lines.append(
            f'<text x="{cx + half_top + 10:.1f}" y="{label_y:.1f}" '
            f'font-size="13" fill="{INK}" text-anchor="start" '
            f'font-family="{FONT_MONO}">{escape(count_txt)}</text>'
        )

    lines.append(fs_ctrl)
    lines.append("</svg>")
    return "\n".join(lines)


def make_funnel(
    data: List[Dict[str, Any]] | None = None,
    *,
    out: Path | str | None = None,
    title: str = "Product-Led Growth Funnel — Q3 2024",
    subtitle: str = "Count of users reaching each conversion stage",
    width: int = WIDTH,
    height: int = HEIGHT,
) -> Path:
    """Render a conversion funnel chart and write the SVG to *out*.

    Parameters
    ----------
    data : list[dict[str, Any]] or None
        Rows with keys ``stage`` (str) and ``count`` (int or float).
        Defaults to DEMO_DATA (a SaaS PLG funnel).
    out : Path, str, or None
        Output file path (.svg). Defaults to the canonical
        ``assets/svg-examples/funnel.svg``.
    title : str
        Chart headline.
    subtitle : str
        One-line subtitle.
    width : int
        Ignored (fixed canvas; kept for API parity).
    height : int
        Ignored.

    Returns
    -------
    Path
        Absolute path to the written SVG file.

    Examples
    --------
    >>> p = make_funnel()
    >>> p.exists()
    True
    """
    if data is None:
        data = DEMO_DATA
    svg = build_svg(data, title=title, subtitle=subtitle)
    dest = Path(out) if out else svg_example_path(__file__, "funnel")
    return write_svg(dest, svg)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate a conversion funnel chart.")
    p.add_argument("--out", default=None)
    p.add_argument("--title", default="Product-Led Growth Funnel — Q3 2024")
    p.add_argument("--subtitle", default="Count of users reaching each conversion stage")
    args = p.parse_args()
    result = make_funnel(out=args.out, title=args.title, subtitle=args.subtitle)
    print(result)

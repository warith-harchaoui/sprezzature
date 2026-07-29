#!/usr/bin/env python3
"""
make_columnrange — a range (floating bar) chart via Vega-Lite.

A column-range chart, also called a floating bar or range chart, draws a
vertical bar for each category from a low value to a high value rather than
from zero to a single value. It communicates an interval, not an absolute
quantity. Typical uses include: temperature ranges by month, confidence
intervals for survey estimates, project schedule phases (a lightweight
alternative to Gantt charts for small sets), salary bands by role, and any
situation where the viewer needs to compare spans rather than point values.

Vega-Lite's ``bar`` mark with both ``y`` (low) and ``y2`` (high) fields
produces the floating bars natively, making this a clean Vega-Lite chart.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import svg_example_path, write_svg  # noqa: E402

INK = "#1D1D1F"
SECONDARY = "#6E6E73"
BG = "#FFFFFF"
GRIDLINE = "#E5E5EA"
FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

COLOR_BAR = "#007AFF"   # house blue for the range bar
COLOR_DOT = "#FF3B30"   # red dot for the recorded high

# ---------------------------------------------------------------------------
# Demo data: average monthly temperature range for five European cities
# (degrees Celsius, 30-year climate normal). Each row records the city, the
# typical low (mean of daily minima) and the typical high (mean of daily maxima)
# for one calendar month.
# ---------------------------------------------------------------------------
DEMO_DATA: List[Dict[str, Any]] = [
    # Month ordering preserved via a sort_order field
    {"city": "Madrid",    "month": "Jan", "low": 2,  "high": 11, "sort": 1},
    {"city": "Madrid",    "month": "Apr", "low": 8,  "high": 18, "sort": 4},
    {"city": "Madrid",    "month": "Jul", "low": 18, "high": 33, "sort": 7},
    {"city": "Madrid",    "month": "Oct", "low": 10, "high": 21, "sort": 10},
    {"city": "Berlin",    "month": "Jan", "low": -3, "high": 3,  "sort": 1},
    {"city": "Berlin",    "month": "Apr", "low": 4,  "high": 14, "sort": 4},
    {"city": "Berlin",    "month": "Jul", "low": 14, "high": 24, "sort": 7},
    {"city": "Berlin",    "month": "Oct", "low": 6,  "high": 14, "sort": 10},
    {"city": "Lisbon",    "month": "Jan", "low": 8,  "high": 15, "sort": 1},
    {"city": "Lisbon",    "month": "Apr", "low": 12, "high": 21, "sort": 4},
    {"city": "Lisbon",    "month": "Jul", "low": 19, "high": 29, "sort": 7},
    {"city": "Lisbon",    "month": "Oct", "low": 14, "high": 23, "sort": 10},
    {"city": "Stockholm", "month": "Jan", "low": -5, "high": 1,  "sort": 1},
    {"city": "Stockholm", "month": "Apr", "low": 2,  "high": 11, "sort": 4},
    {"city": "Stockholm", "month": "Jul", "low": 13, "high": 22, "sort": 7},
    {"city": "Stockholm", "month": "Oct", "low": 4,  "high": 10, "sort": 10},
    {"city": "Athens",    "month": "Jan", "low": 6,  "high": 14, "sort": 1},
    {"city": "Athens",    "month": "Apr", "low": 11, "high": 22, "sort": 4},
    {"city": "Athens",    "month": "Jul", "low": 22, "high": 34, "sort": 7},
    {"city": "Athens",    "month": "Oct", "low": 15, "high": 25, "sort": 10},
]

CITY_COLORS: Dict[str, str] = {
    "Madrid":    "#007AFF",
    "Berlin":    "#AF52DE",
    "Lisbon":    "#28CD41",
    "Stockholm": "#FF9500",
    "Athens":    "#FF3B30",
}


def _build_vegalite_spec(
    data: List[Dict[str, Any]],
    title: str,
    subtitle: str,
    width: int,
    height: int,
) -> Dict[str, Any]:
    """Build a Vega-Lite spec for the column-range chart.

    Parameters
    ----------
    data : list[dict[str, Any]]
        Rows with ``city``, ``month``, ``low``, ``high``, ``sort``.
    title, subtitle : str
        Chart text.
    width, height : int
        Canvas size.

    Returns
    -------
    dict[str, Any]
        Vega-Lite v5 spec.
    """
    cities = sorted(set(row["city"] for row in data))
    color_domain = cities
    color_range = [CITY_COLORS.get(c, "#808080") for c in color_domain]

    # One column group per month, bars side by side per city
    spec: Dict[str, Any] = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": width,
        "height": height,
        "background": BG,
        "title": {
            "text": title,
            "subtitle": subtitle,
            "font": FONT,
            "fontSize": 20,
            "fontWeight": 600,
            "subtitleFont": FONT,
            "subtitleFontSize": 12,
            "subtitleColor": SECONDARY,
            "color": INK,
            "anchor": "start",
        },
        "data": {"values": data},
        "mark": {
            "type": "bar",
            "cornerRadiusEnd": 3,
            "opacity": 0.85,
        },
        "encoding": {
            "x": {
                "field": "month",
                "type": "ordinal",
                "sort": {"field": "sort", "order": "ascending"},
                "title": "Month",
                "axis": {"labelFont": FONT, "titleFont": FONT,
                         "titleColor": INK, "labelColor": INK,
                         "grid": False, "labelAngle": 0},
            },
            "y": {
                "field": "low",
                "type": "quantitative",
                "title": "Temperature (°C)",
                "axis": {"labelFont": FONT_MONO, "titleFont": FONT,
                         "titleColor": INK, "labelColor": SECONDARY,
                         "gridColor": GRIDLINE},
            },
            "y2": {"field": "high"},
            "xOffset": {
                "field": "city",
                "type": "nominal",
                "sort": color_domain,
            },
            "color": {
                "field": "city",
                "type": "nominal",
                "sort": color_domain,
                "scale": {"domain": color_domain, "range": color_range},
                "legend": {
                    "title": "City",
                    "titleFont": FONT,
                    "labelFont": FONT,
                    "symbolType": "square",
                    "orient": "top-right",
                },
            },
            "tooltip": [
                {"field": "city",  "type": "nominal",      "title": "City"},
                {"field": "month", "type": "ordinal",       "title": "Month"},
                {"field": "low",   "type": "quantitative",  "title": "Low (°C)"},
                {"field": "high",  "type": "quantitative",  "title": "High (°C)"},
            ],
        },
        "config": {
            "view": {"stroke": "transparent"},
            "font": FONT,
            "bar": {"binSpacing": 2},
        },
    }
    return spec


def make_columnrange(
    data: Optional[List[Dict[str, Any]]] = None,
    *,
    out: Optional[Path | str] = None,
    title: str = "Monthly Temperature Range by City",
    subtitle: str = "Mean daily low to mean daily high, degrees Celsius, 30-year climate normal",
    width: int = 800,
    height: int = 420,
) -> Path:
    """Render a column-range (floating bar) chart and write the SVG to *out*.

    Parameters
    ----------
    data : list[dict[str, Any]] or None
        Rows with keys ``city``, ``month``, ``low``, ``high``, ``sort``.
        Defaults to DEMO_DATA (European city temperature ranges).
    out : Path, str, or None
        Output path (.svg). Defaults to ``assets/svg-examples/columnrange.svg``.
    title : str
        Chart headline.
    subtitle : str
        One-line subtitle.
    width : int
        Canvas width. Default 800.
    height : int
        Canvas height. Default 420.

    Returns
    -------
    Path
        Absolute path to the written SVG file.

    Examples
    --------
    >>> p = make_columnrange()
    >>> p.exists()
    True
    """
    if data is None:
        data = DEMO_DATA
    spec = _build_vegalite_spec(data, title, subtitle, width, height)
    spec_json = json.dumps(spec, ensure_ascii=False)

    import vl_convert as vlc  # type: ignore
    svg_str = vlc.vegalite_to_svg(spec_json)

    dest = Path(out) if out else svg_example_path(__file__, "columnrange")
    return write_svg(dest, svg_str)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate a column-range (floating bar) chart.")
    p.add_argument("--out", default=None)
    p.add_argument("--title", default="Monthly Temperature Range by City")
    p.add_argument("--subtitle",
                   default="Mean daily low to mean daily high, degrees Celsius, 30-year climate normal")
    p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=420)
    args = p.parse_args()
    result = make_columnrange(
        out=args.out, title=args.title, subtitle=args.subtitle,
        width=args.width, height=args.height,
    )
    print(result)

#!/usr/bin/env python3
"""
make_sunburst — a sunburst (radial hierarchy) chart via full Vega.

A sunburst chart displays a hierarchy as a set of concentric rings. The
innermost ring represents the root category; each outer ring shows the
children of the segment directly below it. Arc length is proportional to
the aggregate value of all leaves below each node. The reader can follow a
spoke outward from the centre to trace an entire branch, and compare
siblings by arc length within any ring.

Sunbursts suit hierarchies with three or four levels. Deeper hierarchies
produce arcs too thin to label. For two-level data with fewer categories,
a donut chart is more legible. For many-leaf flat hierarchies, a treemap
uses area more efficiently.

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
FONT = "Roboto, system-ui, sans-serif"

# Palette for the first ring (top-level categories)
RING1_COLORS: Dict[str, str] = {
    "Europe":        "#007AFF",
    "Americas":      "#28CD41",
    "Asia Pacific":  "#FF9500",
    "Middle East &\nAfrica": "#AF52DE",
}

# ---------------------------------------------------------------------------
# Demo data: global R&D investment by region and country (billion USD, 2023).
# Three-level hierarchy: root → region → country.
# ---------------------------------------------------------------------------
DEMO_DATA: List[Dict[str, Any]] = [
    # Europe
    {"parent": "Europe",        "name": "Germany",        "value": 119.4},
    {"parent": "Europe",        "name": "France",         "value":  62.1},
    {"parent": "Europe",        "name": "United Kingdom", "value":  53.8},
    {"parent": "Europe",        "name": "Sweden",         "value":  22.6},
    {"parent": "Europe",        "name": "Netherlands",    "value":  19.3},
    {"parent": "Europe",        "name": "Other Europe",   "value":  84.5},
    # Americas
    {"parent": "Americas",      "name": "United States",  "value": 738.2},
    {"parent": "Americas",      "name": "Canada",         "value":  30.4},
    {"parent": "Americas",      "name": "Brazil",         "value":  22.9},
    {"parent": "Americas",      "name": "Other Americas", "value":  18.1},
    # Asia Pacific
    {"parent": "Asia Pacific",  "name": "China",          "value": 570.6},
    {"parent": "Asia Pacific",  "name": "Japan",          "value": 172.3},
    {"parent": "Asia Pacific",  "name": "South Korea",    "value":  99.4},
    {"parent": "Asia Pacific",  "name": "India",          "value":  59.2},
    {"parent": "Asia Pacific",  "name": "Australia",      "value":  24.1},
    # Middle East & Africa
    {"parent": "Middle East &\nAfrica", "name": "Israel",        "value": 24.9},
    {"parent": "Middle East &\nAfrica", "name": "Saudi Arabia",  "value": 11.6},
    {"parent": "Middle East &\nAfrica", "name": "South Africa",  "value":  5.3},
]


def _build_vega_spec(
    data: List[Dict[str, Any]],
    title: str,
    subtitle: str,
    width: int,
    height: int,
) -> Dict[str, Any]:
    """Return a full Vega v5 sunburst spec.

    Parameters
    ----------
    data : list[dict[str, Any]]
        Flat rows with ``parent``, ``name``, ``value``.
    title, subtitle : str
        Chart text.
    width, height : int
        Canvas size in pixels.

    Returns
    -------
    dict[str, Any]
        Vega v5 spec.
    """
    # Build node list: root + parents + leaves
    parents = sorted(set(row["parent"] for row in data))
    nodes: List[Dict[str, Any]] = [{"id": "root", "parent": None, "name": "", "value": 0}]
    for parent in parents:
        nodes.append({"id": parent, "parent": "root", "name": parent, "value": 0})
    for row in data:
        leaf_id = f"{row['parent']}/{row['name']}"
        nodes.append({"id": leaf_id, "parent": row["parent"],
                      "name": row["name"], "value": row["value"]})

    # Color scale: first-ring nodes get distinct hues; leaves inherit lighter tint
    color_domain = list(RING1_COLORS.keys())
    color_range = [RING1_COLORS[k] for k in color_domain]

    # Outer radius fills most of the canvas; inner hole is ~30% of radius
    r_outer = min(width, height) / 2.0 - 20
    r_inner = r_outer * 0.28

    spec: Dict[str, Any] = {
        "$schema": "https://vega.github.io/schema/vega/v5.json",
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
            "offset": 8,
        },
        "data": [
            {
                "name": "tree",
                "values": nodes,
                "transform": [
                    {"type": "stratify", "key": "id", "parentKey": "parent"},
                    {
                        "type": "partition",
                        "field": "value",
                        "sort": {"field": "value", "order": "descending"},
                        "size": [{"signal": "2 * PI"}, {"signal": f"{r_outer}"}],
                        "as": ["a0", "r0", "a1", "r1", "depth", "children"],
                    },
                ],
            }
        ],
        "scales": [
            {
                "name": "color",
                "type": "ordinal",
                "domain": color_domain,
                "range": color_range,
            }
        ],
        "marks": [
            {
                "type": "arc",
                "from": {"data": "tree"},
                "encode": {
                    "enter": {
                        "x": {"signal": f"{width} / 2"},
                        "y": {"signal": f"{height} / 2 + 18"},
                        "startAngle": {"field": "a0"},
                        "endAngle": {"field": "a1"},
                        "innerRadius": {
                            "signal": (
                                f"datum.depth === 1 ? {r_inner:.0f} : "
                                f"datum.depth === 2 ? {r_inner + (r_outer - r_inner) * 0.45:.0f} : 0"
                            )
                        },
                        "outerRadius": {
                            "signal": (
                                f"datum.depth === 1 ? {r_inner + (r_outer - r_inner) * 0.42:.0f} : "
                                f"datum.depth === 2 ? {r_outer:.0f} : 0"
                            )
                        },
                        "fill": {
                            "signal": (
                                "datum.depth === 1 ? scale('color', datum.name) : "
                                "datum.depth === 2 ? scale('color', datum.parent) : '#eee'"
                            )
                        },
                        "fillOpacity": {
                            "signal": (
                                "datum.depth === 1 ? 1.0 : "
                                "datum.depth === 2 ? 0.72 : 0"
                            )
                        },
                        "stroke": {"value": BG},
                        "strokeWidth": {"value": 1.5},
                        "tooltip": {
                            "signal": (
                                "datum.depth === 1 ? datum.name + ': ' + format(datum.value, ',.1f') + ' bn USD' : "
                                "datum.depth === 2 ? datum.parent + ' / ' + datum.name + ': ' + "
                                "format(datum.value, ',.1f') + ' bn USD' : ''"
                            )
                        },
                    }
                },
            },
            {
                # Labels for first ring (region names)
                "type": "text",
                "from": {"data": "tree"},
                "encode": {
                    "enter": {
                        "x": {"signal": f"{width} / 2"},
                        "y": {"signal": f"{height} / 2 + 18"},
                        "radius": {
                            "signal": (
                                f"datum.depth === 1 ? {r_inner + (r_outer - r_inner) * 0.21:.0f} : 0"
                            )
                        },
                        "theta": {"signal": "(datum.a0 + datum.a1) / 2"},
                        "text": {
                            "signal": (
                                "datum.depth === 1 && (datum.a1 - datum.a0) > 0.18 ? datum.name : ''"
                            )
                        },
                        "align": {"value": "center"},
                        "baseline": {"value": "middle"},
                        "font": {"value": FONT},
                        "fontSize": {"value": 12},
                        "fontWeight": {"value": 600},
                        "fill": {"value": BG},
                    }
                },
            },
        ],
        "legends": [
            {
                "fill": "color",
                "title": "Region",
                "titleFont": FONT,
                "titleFontSize": 12,
                "titleColor": INK,
                "labelFont": FONT,
                "labelFontSize": 12,
                "labelColor": INK,
                "orient": "top-right",
                "direction": "vertical",
                "symbolType": "circle",
                "symbolSize": 120,
            }
        ],
    }
    return spec


def make_sunburst(
    data: Optional[List[Dict[str, Any]]] = None,
    *,
    out: Optional[Path | str] = None,
    title: str = "Global R&D Investment by Region and Country — 2023",
    subtitle: str = "Total expenditure in billions of USD; arc length proportional to investment",
    width: int = 800,
    height: int = 640,
) -> Path:
    """Render a sunburst chart and write it to *out*.

    Parameters
    ----------
    data : list[dict[str, Any]] or None
        Flat rows with keys ``parent`` (str), ``name`` (str), ``value``
        (float). Defaults to DEMO_DATA (R&D investment by region/country).
    out : Path, str, or None
        Output path (.svg). Defaults to ``assets/svg-examples/sunburst.svg``.
    title : str
        Chart headline.
    subtitle : str
        One-line subtitle.
    width : int
        Canvas width in pixels. Default 800.
    height : int
        Canvas height in pixels. Default 640.

    Returns
    -------
    Path
        Absolute path to the written SVG file.

    Examples
    --------
    >>> p = make_sunburst()
    >>> p.exists()
    True
    """
    if data is None:
        data = DEMO_DATA

    spec = _build_vega_spec(data, title, subtitle, width, height)
    spec_json = json.dumps(spec, ensure_ascii=False)

    import vl_convert as vlc  # type: ignore
    svg_str = vlc.vega_to_svg(spec_json)

    dest = Path(out) if out else svg_example_path(__file__, "sunburst")
    return write_svg(dest, svg_str)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate a sunburst radial hierarchy chart.")
    p.add_argument("--out", default=None)
    p.add_argument("--title", default="Global R&D Investment by Region and Country — 2023")
    p.add_argument("--subtitle",
                   default="Total expenditure in billions of USD; arc length proportional to investment")
    p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=640)
    args = p.parse_args()
    result = make_sunburst(
        out=args.out, title=args.title, subtitle=args.subtitle,
        width=args.width, height=args.height,
    )
    print(result)

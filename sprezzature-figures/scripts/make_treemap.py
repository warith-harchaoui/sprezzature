#!/usr/bin/env python3
"""
make_treemap — a treemap figure rendered via full Vega (squarify layout).

A treemap encodes a hierarchy as a set of nested rectangles. Area is
proportional to a numeric measure so the viewer can compare part-to-whole
relationships across many categories at once. Colour encodes a second
dimension (such as the parent category) so the eye groups siblings before
comparing across groups. The classic use cases are software package sizes,
portfolio composition, file-system usage, and any taxonomy with a value
attached to each leaf.

Vega-Lite cannot produce a treemap natively; this generator uses a full
Vega v5 spec with the squarify layout.

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

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------
_SCRIPT = Path(__file__).resolve()
_ASSET_DIR = _SCRIPT.parent.parent / "assets" / "svg-examples"
_WEB_DIR = _SCRIPT.parent.parent.parent / "web" / "img" / "figures"

# ---------------------------------------------------------------------------
# House palette (six parent-category colours + neutral ink)
# ---------------------------------------------------------------------------
INK = "#1D1D1F"
SECONDARY = "#6E6E73"
BG = "#FFFFFF"
FONT = "Roboto, system-ui, sans-serif"

CATEGORY_COLORS: Dict[str, str] = {
    "Infrastructure": "#007AFF",
    "Applications":  "#AF52DE",
    "Security":      "#FF9500",
    "Data & AI":     "#28CD41",
    "Networking":    "#FF3B30",
    "Compliance":    "#79DBDC",
}

# ---------------------------------------------------------------------------
# Demo data: annual cloud spending by service, IT department FY-2024 (k EUR).
# Two-level hierarchy: parent = domain, name = service, value = spend.
# ---------------------------------------------------------------------------
DEMO_DATA: List[Dict[str, Any]] = [
    # Infrastructure
    {"parent": "Infrastructure", "name": "Compute (EC2/GCE)", "value": 312},
    {"parent": "Infrastructure", "name": "Storage (S3/GCS)",  "value": 148},
    {"parent": "Infrastructure", "name": "Managed DB",        "value": 97},
    {"parent": "Infrastructure", "name": "Container registry","value": 34},
    # Applications
    {"parent": "Applications",   "name": "CRM platform",      "value": 210},
    {"parent": "Applications",   "name": "ERP system",        "value": 178},
    {"parent": "Applications",   "name": "Dev toolchain",     "value": 85},
    {"parent": "Applications",   "name": "Collaboration",     "value": 62},
    # Security
    {"parent": "Security",       "name": "SIEM / SOC",        "value": 134},
    {"parent": "Security",       "name": "WAF / DDoS",        "value": 76},
    {"parent": "Security",       "name": "Identity (IAM)",    "value": 58},
    # Data & AI
    {"parent": "Data & AI",      "name": "Data warehouse",    "value": 189},
    {"parent": "Data & AI",      "name": "ML training",       "value": 143},
    {"parent": "Data & AI",      "name": "BI tooling",        "value": 67},
    # Networking
    {"parent": "Networking",     "name": "CDN / egress",      "value": 112},
    {"parent": "Networking",     "name": "VPN / SD-WAN",      "value": 54},
    # Compliance
    {"parent": "Compliance",     "name": "Audit tooling",     "value": 43},
    {"parent": "Compliance",     "name": "Data residency",    "value": 29},
]


def _build_vega_spec(
    data: List[Dict[str, Any]],
    title: str,
    subtitle: str,
    width: int,
    height: int,
) -> Dict[str, Any]:
    """Return a full Vega v5 spec for the treemap.

    Parameters
    ----------
    data : list[dict[str, Any]]
        Flat rows with ``parent``, ``name``, ``value``.
    title, subtitle : str
        Chart headline and sub-line.
    width, height : int
        Canvas dimensions in pixels.

    Returns
    -------
    dict[str, Any]
        A Vega v5 specification object.
    """
    # Build the node list Vega expects: a root node plus one node per category
    # (intermediate) and one per leaf.
    parents = sorted(set(row["parent"] for row in data))
    nodes: List[Dict[str, Any]] = [{"id": "root", "parent": None, "name": "", "value": 0}]
    for parent in parents:
        nodes.append({"id": parent, "parent": "root", "name": parent, "value": 0})
    for row in data:
        leaf_id = f"{row['parent']}/{row['name']}"
        nodes.append({"id": leaf_id, "parent": row["parent"],
                      "name": row["name"], "value": row["value"]})

    # Color domain: map each parent to its house color
    color_domain = list(CATEGORY_COLORS.keys())
    color_range = [CATEGORY_COLORS[k] for k in color_domain]

    spec: Dict[str, Any] = {
        "$schema": "https://vega.github.io/schema/vega/v5.json",
        "width": width,
        "height": height,
        "background": BG,
        "title": {
            "text": title,
            "subtitle": subtitle,
            "font": FONT,
            "fontSize": 22,
            "fontWeight": 600,
            "subtitleFont": FONT,
            "subtitleFontSize": 13,
            "subtitleColor": SECONDARY,
            "color": INK,
            "anchor": "start",
            "offset": 12,
        },
        "data": [
            {
                "name": "tree",
                "values": nodes,
                "transform": [
                    {
                        "type": "stratify",
                        "key": "id",
                        "parentKey": "parent",
                    },
                    {
                        "type": "treemap",
                        "field": "value",
                        "sort": {"field": "value", "order": "descending"},
                        "round": True,
                        "method": "squarify",
                        "ratio": 1.618,
                        "size": [{"signal": "width"}, {"signal": "height - 60"}],
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
                # Leaf rectangles
                "type": "rect",
                "from": {"data": "tree"},
                "encode": {
                    "enter": {
                        "x": {"field": "x0"},
                        "y": {"field": "y0", "offset": 60},
                        "x2": {"field": "x1"},
                        "y2": {"field": "y1", "offset": 60},
                        "fill": {"scale": "color", "field": "parent"},
                        "fillOpacity": [
                            # Leaves get 0.82 opacity; intermediate nodes get 0
                            {
                                "test": "datum.depth === 2",
                                "value": 0.82,
                            },
                            {"value": 0},
                        ],
                        "stroke": {"value": BG},
                        "strokeWidth": {"value": 2},
                        "tooltip": {
                            "signal": (
                                "datum.depth === 2 ? "
                                "datum.parent + ' / ' + datum.name + ': ' + datum.value + 'k EUR' "
                                ": ''"
                            )
                        },
                    }
                },
            },
            {
                # Leaf labels (name + value)
                "type": "text",
                "from": {"data": "tree"},
                "encode": {
                    "enter": {
                        "x": {"signal": "(datum.x0 + datum.x1) / 2"},
                        "y": {"signal": "60 + (datum.y0 + datum.y1) / 2 - 6"},
                        "text": {
                            "signal": (
                                "datum.depth === 2 && (datum.x1 - datum.x0) > 50 && "
                                "(datum.y1 - datum.y0) > 30 ? datum.name : ''"
                            )
                        },
                        "align": {"value": "center"},
                        "baseline": {"value": "middle"},
                        "font": {"value": FONT},
                        "fontSize": {"value": 11},
                        "fontWeight": {"value": 500},
                        "fill": {"value": BG},
                        "limit": {"signal": "datum.x1 - datum.x0 - 6"},
                    }
                },
            },
            {
                # Value label below name
                "type": "text",
                "from": {"data": "tree"},
                "encode": {
                    "enter": {
                        "x": {"signal": "(datum.x0 + datum.x1) / 2"},
                        "y": {"signal": "60 + (datum.y0 + datum.y1) / 2 + 10"},
                        "text": {
                            "signal": (
                                "datum.depth === 2 && (datum.x1 - datum.x0) > 50 && "
                                "(datum.y1 - datum.y0) > 40 ? datum.value + 'k' : ''"
                            )
                        },
                        "align": {"value": "center"},
                        "baseline": {"value": "middle"},
                        "font": {"value": FONT},
                        "fontSize": {"value": 10},
                        "fill": {"value": BG},
                        "opacity": {"value": 0.8},
                    }
                },
            },
        ],
        "legends": [
            {
                "fill": "color",
                "title": "Domain",
                "titleFont": FONT,
                "titleFontSize": 12,
                "titleColor": INK,
                "labelFont": FONT,
                "labelFontSize": 12,
                "labelColor": INK,
                "orient": "top-left",
                "direction": "horizontal",
                "symbolType": "square",
                "symbolSize": 140,
                "offset": 4,
            }
        ],
    }
    return spec


def make_treemap(
    data: Optional[List[Dict[str, Any]]] = None,
    *,
    out: Optional[Path | str] = None,
    title: str = "IT Cloud Spending by Service — FY 2024",
    subtitle: str = "Annual spend in thousands of EUR; area proportional to budget",
    width: int = 900,
    height: int = 600,
) -> Path:
    """Render a treemap and write it to *out*.

    Parameters
    ----------
    data : list[dict[str, Any]] or None
        Rows with keys ``parent`` (str), ``name`` (str), ``value`` (float).
        Defaults to DEMO_DATA (IT cloud spending by domain and service).
    out : Path, str, or None
        Output path (.svg). Defaults to ``assets/svg-examples/treemap.svg``.
    title : str
        Chart headline.
    subtitle : str
        One-line subtitle.
    width : int
        Canvas width in pixels. Default 900.
    height : int
        Canvas height in pixels. Default 600.

    Returns
    -------
    Path
        Absolute path to the written SVG file.

    Examples
    --------
    >>> p = make_treemap()
    >>> p.exists()
    True
    """
    if data is None:
        data = DEMO_DATA

    spec = _build_vega_spec(data, title, subtitle, width, height)
    spec_json = json.dumps(spec, ensure_ascii=False)

    import vl_convert as vlc  # type: ignore
    svg_str = vlc.vega_to_svg(spec_json)

    dest = Path(out) if out else svg_example_path(__file__, "treemap")
    return write_svg(dest, svg_str)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate a treemap figure.")
    p.add_argument("--out", default=None)
    p.add_argument("--title", default="IT Cloud Spending by Service — FY 2024")
    p.add_argument("--subtitle",
                   default="Annual spend in thousands of EUR; area proportional to budget")
    p.add_argument("--width", type=int, default=900)
    p.add_argument("--height", type=int, default=600)
    args = p.parse_args()
    result = make_treemap(
        out=args.out, title=args.title, subtitle=args.subtitle,
        width=args.width, height=args.height,
    )
    print(result)

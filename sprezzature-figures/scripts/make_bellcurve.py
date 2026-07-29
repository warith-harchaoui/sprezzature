#!/usr/bin/env python3
"""
make_bellcurve — a bell curve (normal distribution) figure via Vega-Lite.

A bell curve visualises a normal distribution by plotting the probability
density function (PDF) against its horizontal axis. It communicates three
things at once: where the distribution is centred (the mean), how spread
out it is (the standard deviation), and how likely each range of values is
(area under the curve). Annotating the mean and one-sigma bands makes the
68-95-99.7 rule tangible.

The typical uses are test score distributions, measurement error analysis,
process quality control, and any situation where you want to show that a
quantity is approximately normally distributed with given parameters.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _render import svg_example_path, write_svg  # noqa: E402

INK = "#1D1D1F"
SECONDARY = "#6E6E73"
BG = "#FFFFFF"
FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

# House palette
COLOR_FILL = "#007AFF"    # curve fill
COLOR_STROKE = "#0051A8"  # curve stroke
COLOR_SIGMA1 = "#28CD41"  # 1-sigma band edge
COLOR_MEAN = "#FF3B30"    # mean line


def _normal_pdf(x: float, mean: float, std: float) -> float:
    """Return the normal probability density at x.

    Parameters
    ----------
    x : float
        Point to evaluate.
    mean : float
        Distribution mean.
    std : float
        Distribution standard deviation.

    Returns
    -------
    float
        PDF value (probability density).
    """
    # Standard Gaussian PDF formula
    z = (x - mean) / std
    return math.exp(-0.5 * z * z) / (std * math.sqrt(2.0 * math.pi))


def _generate_curve_data(
    mean: float,
    std: float,
    n_points: int = 200,
) -> List[Dict[str, Any]]:
    """Generate evenly spaced (x, y) pairs covering mean ± 4 standard deviations.

    Parameters
    ----------
    mean : float
        Distribution mean.
    std : float
        Standard deviation.
    n_points : int
        Number of sample points. Default 200.

    Returns
    -------
    list[dict[str, Any]]
        Rows with keys ``x`` (float), ``y`` (float), ``band`` (str label for
        the sigma region each point falls in).
    """
    x_min = mean - 4.0 * std
    x_max = mean + 4.0 * std
    step = (x_max - x_min) / (n_points - 1)
    rows: List[Dict[str, Any]] = []
    for i in range(n_points):
        x = x_min + i * step
        y = _normal_pdf(x, mean, std)
        # Label which sigma region this point is in for colouring
        z = abs((x - mean) / std)
        band = "±1σ" if z <= 1 else "±2σ" if z <= 2 else "±3σ" if z <= 3 else "tails"
        rows.append({"x": round(x, 4), "y": round(y, 8), "band": band})
    return rows


def _build_vegalite_spec(
    data: List[Dict[str, Any]],
    mean: float,
    std: float,
    title: str,
    subtitle: str,
    width: int,
    height: int,
) -> Dict[str, Any]:
    """Build a Vega-Lite spec for the bell curve.

    Parameters
    ----------
    data : list[dict[str, Any]]
        Output of :func:`_generate_curve_data`.
    mean, std : float
        Distribution parameters used to place annotation rules.
    title, subtitle : str
        Chart text.
    width, height : int
        Canvas dimensions.

    Returns
    -------
    dict[str, Any]
        Vega-Lite v5 spec.
    """
    # Annotation rules: mean and ±1σ vertical lines
    annotations = [
        {"x": mean,        "label": f"μ = {mean:.1f}", "color": COLOR_MEAN},
        {"x": mean - std,  "label": f"−1σ ({mean - std:.1f})", "color": COLOR_SIGMA1},
        {"x": mean + std,  "label": f"+1σ ({mean + std:.1f})", "color": COLOR_SIGMA1},
    ]

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
        "layer": [
            {
                # Filled area under the curve
                "data": {"values": data},
                "mark": {"type": "area", "line": True, "color": COLOR_FILL,
                         "fillOpacity": 0.25, "strokeWidth": 2.5,
                         "stroke": COLOR_STROKE},
                "encoding": {
                    "x": {
                        "field": "x",
                        "type": "quantitative",
                        "title": "Value",
                        "axis": {"labelFont": FONT_MONO, "titleFont": FONT,
                                 "titleColor": INK, "labelColor": SECONDARY,
                                 "grid": False, "ticks": True},
                    },
                    "y": {
                        "field": "y",
                        "type": "quantitative",
                        "title": "Probability density",
                        "axis": {"labelFont": FONT_MONO, "titleFont": FONT,
                                 "titleColor": INK, "labelColor": SECONDARY,
                                 "grid": True, "gridColor": "#E5E5EA",
                                 "format": ".4f"},
                    },
                    "tooltip": [
                        {"field": "x", "type": "quantitative", "title": "x",
                         "format": ".2f"},
                        {"field": "y", "type": "quantitative", "title": "Density",
                         "format": ".6f"},
                        {"field": "band", "type": "nominal", "title": "Region"},
                    ],
                },
            },
            # Annotation rules (mean and ±1σ)
            *[
                {
                    "data": {"values": [ann]},
                    "layer": [
                        {
                            "mark": {
                                "type": "rule",
                                "color": ann["color"],
                                "strokeWidth": 1.5,
                                "strokeDash": [5, 3],
                            },
                            "encoding": {
                                "x": {"field": "x", "type": "quantitative"},
                            },
                        },
                        {
                            "mark": {
                                "type": "text",
                                "dy": -8,
                                "fontSize": 11,
                                "font": FONT_MONO,
                                "color": ann["color"],
                                "align": "center",
                            },
                            "encoding": {
                                "x": {"field": "x", "type": "quantitative"},
                                "y": {"value": 12},
                                "text": {"field": "label", "type": "nominal"},
                            },
                        },
                    ],
                }
                for ann in annotations
            ],
        ],
        "config": {
            "view": {"stroke": "transparent"},
            "font": FONT,
        },
    }
    return spec


def make_bellcurve(
    mean: float = 72.4,
    std: float = 9.1,
    *,
    out: Optional[Path | str] = None,
    title: str = "Distribution of Student Exam Scores",
    subtitle: str = "Normal distribution fitted to 1,840 exam results; shaded area = ±1 standard deviation",
    width: int = 800,
    height: int = 440,
) -> Path:
    """Render a bell curve figure and write the SVG to *out*.

    Parameters
    ----------
    mean : float
        Distribution mean. Default 72.4 (exam score example).
    std : float
        Standard deviation. Default 9.1.
    out : Path, str, or None
        Output path (.svg). Defaults to ``assets/svg-examples/bellcurve.svg``.
    title : str
        Chart headline.
    subtitle : str
        One-line subtitle.
    width : int
        Canvas width in pixels. Default 800.
    height : int
        Canvas height in pixels. Default 440.

    Returns
    -------
    Path
        Absolute path to the written SVG file.

    Examples
    --------
    >>> p = make_bellcurve()
    >>> p.exists()
    True
    """
    curve_data = _generate_curve_data(mean, std)
    spec = _build_vegalite_spec(curve_data, mean, std, title, subtitle, width, height)
    spec_json = json.dumps(spec, ensure_ascii=False)

    import vl_convert as vlc  # type: ignore
    svg_str = vlc.vegalite_to_svg(spec_json)

    dest = Path(out) if out else svg_example_path(__file__, "bellcurve")
    return write_svg(dest, svg_str)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate a bell curve (normal distribution) figure.")
    p.add_argument("--mean", type=float, default=72.4)
    p.add_argument("--std", type=float, default=9.1)
    p.add_argument("--out", default=None)
    p.add_argument("--title", default="Distribution of Student Exam Scores")
    p.add_argument("--subtitle",
                   default="Normal distribution fitted to 1,840 exam results; "
                           "shaded area = one standard deviation around the mean")
    p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=440)
    args = p.parse_args()
    result = make_bellcurve(
        mean=args.mean, std=args.std,
        out=args.out, title=args.title, subtitle=args.subtitle,
        width=args.width, height=args.height,
    )
    print(result)

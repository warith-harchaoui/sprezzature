#!/usr/bin/env python3
"""Generate a publication-quality **icicle / flame graph** as a standalone SVG.

An icicle plot lays a hierarchy out as a stack of rectangular bands: the root
spans the full width at the top, and every level below partitions its parent's
width in proportion to a size measure. Read top-down it is an outline of the
tree; read as a CPU profile it is a *flame graph* — each bar is a function, its
width is the wall-clock time spent inside it (self + children), and the stack of
bars under a bar is its call tree. Wide bars are where the time goes.

Here the measured quantity is the time a web service spends handling one API
request: 480 milliseconds, broken down by call stack. The story the figure
tells is that a single un-cached database query (``fetch_user_orders`` →
``run_sql``) eats almost half of the whole request — the widest tower in the
graph — which is exactly the bar an engineer would click to fix first.

Vega-Lite has no native partition / icicle mark (rect widths must be laid out
from a cumulative running offset the grammar cannot express on one axis), so the
figure is assembled as a hand-authored SVG string. It follows the sprezzature-figures
house style: Roboto typography, ink ``#1D1D1F`` on white, a warm depth-graded
"flame" ramp, rounded corners, native ``<title>`` tooltips, and a CSS ``:hover``
lift guarded by ``prefers-reduced-motion``.

The final artifact is always the SVG at ``assets/svg-examples/icicle.svg``;
running this module writes it.

Usage
-----
    python make_icicle.py            # writes assets/svg-examples/icicle.svg
    python make_icicle.py --out x.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc classes.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _svg import svg_open, xml_escape  # noqa: E402
from _render import write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _style import os_dark_style  # noqa: E402


# --------------------------------------------------------------------------- #
# Communicative data — one API request's CPU flame graph                        #
# --------------------------------------------------------------------------- #
# The call tree of a single "GET /api/checkout" request, in milliseconds of
# wall-clock time. A node's ``ms`` is its total (self + descendants); children
# must sum to <= their parent, and the remainder (parent time not covered by a
# child) is the parent's own "self" time. The tree is authored so the hot path
# — an un-cached SQL query — is visibly the widest tower.
TREE: Dict[str, Any] = {
    "name": "GET /api/checkout",
    "ms": 480,
    "children": [
        {
            "name": "authenticate",
            "ms": 46,
            "children": [
                {"name": "verify_jwt", "ms": 28, "children": []},
                {"name": "load_session", "ms": 14, "children": []},
            ],
        },
        {
            "name": "load_cart",
            "ms": 300,
            "children": [
                {
                    "name": "fetch_user_orders",
                    "ms": 232,
                    "children": [
                        {
                            "name": "run_sql",
                            "ms": 214,
                            "children": [
                                {"name": "wait_on_lock", "ms": 176, "children": []},
                                {"name": "deserialize_rows", "ms": 30, "children": []},
                            ],
                        },
                    ],
                },
                {
                    "name": "price_items",
                    "ms": 54,
                    "children": [
                        {"name": "apply_tax", "ms": 22, "children": []},
                        {"name": "apply_coupons", "ms": 20, "children": []},
                    ],
                },
            ],
        },
        {
            "name": "render_response",
            "ms": 118,
            "children": [
                {"name": "serialize_json", "ms": 70, "children": []},
                {"name": "gzip", "ms": 34, "children": []},
            ],
        },
    ],
}

TITLE = "One slow SQL query eats 45% of every checkout"
SUBTITLE = (
    "CPU flame graph of one GET /api/checkout request (480 ms) - "
    "bar width is time spent; the widest tower is where to optimise first"
)
HOT_PATH = ("load_cart", "fetch_user_orders", "run_sql", "wait_on_lock")


# --------------------------------------------------------------------------- #
# Layout                                                                         #
# --------------------------------------------------------------------------- #
def flatten(
    node: Dict[str, Any],
    depth: int,
    x0: float,
    px_per_ms: float,
    out: List[Dict[str, Any]],
) -> None:
    """Recursively lay out the call tree into positioned rectangle records.

    Each node becomes one rect spanning ``node["ms"] * px_per_ms`` pixels of
    width, placed at horizontal offset ``x0``. Children are packed left-to-right
    under their parent; the parent's leftover time (its "self" time, not covered
    by any child) is left as blank strip on the right of the last child, which is
    the honest flame-graph convention.

    Parameters
    ----------
    node : dict
        The current call-tree node (``name``, ``ms``, ``children``).
    depth : int
        Stack depth of this node (root = 0). Drives the row and the colour.
    x0 : float
        Left edge of this node in the *time* axis, in milliseconds.
    px_per_ms : float
        Horizontal scale — pixels per millisecond.
    out : list of dict
        Accumulator that receives one positioned record per node.
    """
    out.append({
        "name": node["name"],
        "ms": node["ms"],
        "depth": depth,
        "x_ms": x0,
        "w_ms": node["ms"],
    })
    child_x = x0
    for child in node.get("children", []):
        flatten(child, depth + 1, child_x, px_per_ms, out)
        child_x += child["ms"]


# --------------------------------------------------------------------------- #
# Palette — a warm "flame" ramp keyed to stack depth                            #
# --------------------------------------------------------------------------- #
# Classic flame graphs colour by depth on a warm ramp (cool amber at the root,
# hot red-orange deep in the stack) so the eye reads height as heat. These hues
# are hand-tuned from the house Apple-system warm family (Yellow -> Orange ->
# Red / Pink) to stay CVD-distinguishable by luminance step, not hue alone.
DEPTH_RAMP: List[str] = [
    "#FFCC00",  # 0 — root, warm amber
    "#FFB300",  # 1
    "#FF9500",  # 2 — Apple Orange
    "#FF7A1A",  # 3
    "#FF5A2C",  # 4
    "#FF3B30",  # 5 — Apple Red (deepest / hottest)
]


# The root gets its own confident anchor colour — Apple Blue — so the core of
# the hierarchy reads as a deliberate root, never as "just another muted bar".
ROOT_FILL = "#007AFF"


def depth_fill(depth: int, on_hot_path: bool) -> str:
    """Return the fill hex for a bar at ``depth``.

    The root (``depth == 0``) is always the house Apple Blue, a distinct anchor
    for the core of the hierarchy. Below it, hot-path bars ride the warm flame
    ramp at full strength; off-path bars use a cool slate ramp whose luminance
    steps are wide enough to read as distinct depths. Two channels (warmth +
    saturation) keep the on/off split legible for colour-vision-deficient
    viewers.

    Parameters
    ----------
    depth : int
        Stack depth (0 = root).
    on_hot_path : bool
        Whether this bar lies on the highlighted critical path.

    Returns
    -------
    str
        A ``#RRGGBB`` fill.
    """
    if depth == 0:
        return ROOT_FILL
    if on_hot_path:
        return DEPTH_RAMP[min(depth, len(DEPTH_RAMP) - 1)]
    # Off-path bars: cool slate ramp with a wider luminance step per depth so the
    # levels stay distinguishable at a glance (the old ramp was too flat).
    cool = ["#AEB4C2", "#9BA2B4", "#8790A6", "#737E98", "#606C88", "#4E5B78"]
    return cool[min(depth - 1, len(cool) - 1)]


def readable_ink(fill: str) -> str:
    """Pick ink or white for label text over ``fill`` by perceived luminance.

    Parameters
    ----------
    fill : str
        Background ``#RRGGBB`` hex.

    Returns
    -------
    str
        ``"#1D1D1F"`` (ink) on light fills, ``"#FFFFFF"`` on dark fills.
    """
    r = int(fill[1:3], 16)
    g = int(fill[3:5], 16)
    b = int(fill[5:7], 16)
    # Rec. 601 luma; > 150 is "light enough for dark ink".
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    return "#1D1D1F" if luma > 150 else "#FFFFFF"


# --------------------------------------------------------------------------- #
# Formatting helpers                                                            #
# --------------------------------------------------------------------------- #
def _fmt(value: float) -> str:
    """Format a float compactly (trim trailing zeros) for SVG coordinates."""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _clip_label(name: str, width_px: float) -> str:
    """Truncate a function name to what fits in ``width_px``.

    Roboto at the label size averages ~7.7 px per character; with an 8 px inner
    margin each side this fits comfortably without clipping mid-word on medium
    bars. Returns an empty string when even three characters would not fit, so
    the caller drops the label entirely rather than paint an ellipsis stub.
    """
    max_chars = int((width_px - 12.0) / 7.7)
    if max_chars < 3:
        return ""
    if len(name) <= max_chars:
        return name
    if max_chars <= 1:
        return ""
    return name[: max_chars - 1] + "…"


# --------------------------------------------------------------------------- #
# SVG assembly                                                                  #
# --------------------------------------------------------------------------- #
def render_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full icicle / flame-graph SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`.
        One of ``"self-contained"`` (default, ships a hidden-until-live
        fullscreen button), ``"external"`` or ``"static"`` (no button).
    accessibility : str, optional
        Accepted for CLI parity but **not applied** — a documented no-op. This
        figure's fills are a *sequential, perceptually-tuned* scheme, not a
        categorical set: the warm ``DEPTH_RAMP`` and the cool off-path ramp both
        encode call-stack **depth** as a monotonic luminance gradient (deeper is
        hotter / darker), and the warm-vs-cool split carries the on/off critical
        path. Re-spacing those anchors by lightness through a categorical level
        de-tunes them: verified that ``monochrome`` inverts the first warm step
        (breaking the "deeper is hotter" read) and collapses the warm and cool
        ramps to identical greys (erasing the hot-path distinction — the whole
        point of the graph). It is already colour-vision- and greyscale-safe by
        construction, so the categorical level is intentionally not applied.

    Returns
    -------
    str
        A complete, standalone ``<svg>`` document (house style, accessible
        ``<title>``/``<desc>``, native tooltips, CSS hover lift).
    """
    # ``accessibility`` is a deliberate no-op here — see the docstring: the depth
    # ramps are a tuned sequential map, already CVD/greyscale-safe, and a
    # categorical level would de-tune them. Reference it so linters see it used.
    del accessibility
    width, height = 1300, 860
    plot_x, plot_y = 88.0, 234.0
    plot_w = width - plot_x - 88.0
    row_h = 74.0
    row_gap = 8.0

    ink = "#1D1D1F"
    muted = "#6E6E73"
    hairline = "#E5E5EA"

    total_ms = float(TREE["ms"])
    px_per_ms = plot_w / total_ms

    rects: List[Dict[str, Any]] = []
    flatten(TREE, 0, 0.0, px_per_ms, rects)
    max_depth = max(r["depth"] for r in rects)

    parts: List[str] = []
    parts.append(svg_open(width, height, "ice-t", "ice-d"))
    parts.append(f'<title id="ice-t">{xml_escape(TITLE)}</title>')
    parts.append(
        '<desc id="ice-d">Icicle / flame graph of one GET /api/checkout request totalling 480 '
        'milliseconds. The root bar spans the full width; each row below splits its parent by time. '
        'The highlighted warm tower load_cart to fetch_user_orders to run_sql to wait_on_lock is the '
        'critical path: wait_on_lock alone is 176 ms, about 37 percent of the request, and run_sql '
        'as a whole is 214 ms, about 45 percent. Off-path calls (authenticate, render_response) are '
        'shown in muted grey.</desc>'
    )

    # Hover lift + focus ring, guarded by reduced-motion.
    #
    # This is a PERCEPTUAL figure — the warm/cool depth ramp is a tuned
    # sequential map, so prefers-contrast must NOT re-space the ramp. Instead it
    # STRENGTHENS structure: the bars gain a dark ink keyline (each bar reads as a
    # firm cell instead of relying on the white gaps), the light-grey axis ruler
    # firms up to ink, and the muted label ink deepens to primary ink. Under
    # forced-colors the bars keep a CanvasText outline so the icicle structure
    # survives the system palette. Every rule is media-gated, so the default
    # render is byte-identical.
    parts.append(
        "<style>"
        ".bar{transition:transform .16s ease, filter .16s ease;transform-box:fill-box;"
        "transform-origin:center;cursor:pointer;}"
        ".bar:hover,.bar:focus{filter:brightness(1.07);transform:scaleY(1.04);outline:none;}"
        ".bar:focus{stroke:#1D1D1F;stroke-width:2.5;}"
        "@media (prefers-reduced-motion: reduce){.bar{transition:none;}"
        ".bar:hover,.bar:focus{transform:none;}}"
        "@media (prefers-contrast: more){"
        ".bar{stroke:#1D1D1F;stroke-width:1.6;}"
        f'[stroke="{hairline}"]{{stroke:{ink};stroke-width:1.4;}}'
        f'[fill="{muted}"]{{fill:{ink};}}'
        "}"
        "@media (forced-colors: active){"
        ".bar{stroke:CanvasText;stroke-width:1.4;forced-color-adjust:auto;}"
        "}"
        # Additive OS dark mode: dark paper + light ink (default ink_map), plus
        # the figure's light-grey axis ruler / percent labels darkened to read on
        # the dark surface. The warm/cool depth ramps are a tuned perceptual map
        # and are deliberately left alone. The bar focus ring flips to off-white.
        + os_dark_style(
            extra=(
                '[stroke="#E5E5EA"]{stroke:#3A3A3E;}'
                '[fill="#9A9AA0"]{fill:#8B8B92;}'
                ".bar:focus{stroke:#F2F2F7;}"
            )
        )
        + "</style>"
    )

    # Background.
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # Title + subtitle.
    parts.append(
        f'<text x="{_fmt(plot_x)}" y="72" font-size="38" font-weight="700" '
        f'fill="{ink}">{xml_escape(TITLE)}</text>'
    )
    parts.append(
        f'<text x="{_fmt(plot_x)}" y="110" font-size="18" fill="{muted}">{xml_escape(SUBTITLE)}</text>'
    )

    # Time axis (top): a light ruler in milliseconds and percent, so a reader can
    # convert any bar width to a duration without a legend.
    axis_y = plot_y - 30.0
    parts.append(
        f'<text x="{_fmt(plot_x)}" y="{_fmt(plot_y - 78)}" font-size="15" fill="{muted}" '
        f'font-family="Roboto Mono, monospace">Time into request (bar width = milliseconds)</text>'
    )
    for ms in (0, 120, 240, 360, 480):
        tx = plot_x + ms * px_per_ms
        pct = ms / total_ms * 100.0
        anchor = "start" if ms == 0 else ("end" if ms == 480 else "middle")
        parts.append(
            f'<line x1="{_fmt(tx)}" y1="{_fmt(axis_y)}" x2="{_fmt(tx)}" '
            f'y2="{_fmt(plot_y + (max_depth + 1) * (row_h + row_gap))}" '
            f'stroke="{hairline}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{_fmt(tx)}" y="{_fmt(axis_y - 8)}" font-size="15" fill="{muted}" '
            f'text-anchor="{anchor}" font-family="Roboto Mono, monospace">{ms} ms</text>'
        )
        parts.append(
            f'<text x="{_fmt(tx)}" y="{_fmt(axis_y - 26)}" font-size="13" fill="#9A9AA0" '
            f'text-anchor="{anchor}" font-family="Roboto Mono, monospace">{pct:.0f}%</text>'
        )

    # Depth labels down the left gutter (level 0..N), so the icicle structure is
    # legible even where a row's bars are too thin to name.
    for d in range(max_depth + 1):
        ry = plot_y + d * (row_h + row_gap) + row_h / 2.0 + 5.0
        parts.append(
            f'<text x="{_fmt(plot_x - 16)}" y="{_fmt(ry)}" font-size="14" fill="{muted}" '
            f'text-anchor="end" font-family="Roboto Mono, monospace">L{d}</text>'
        )

    # Bars.
    rx = 11.0
    for r in rects:
        x = plot_x + r["x_ms"] * px_per_ms
        y = plot_y + r["depth"] * (row_h + row_gap)
        w = r["w_ms"] * px_per_ms
        on_hot = r["name"] in HOT_PATH
        fill = depth_fill(r["depth"], on_hot)
        pct = r["ms"] / total_ms * 100.0
        tip = f'{r["name"]}  -  {r["ms"]} ms  ({pct:.0f}% of request, depth {r["depth"]})'
        parts.append(
            f'<rect class="bar" tabindex="0" x="{_fmt(x)}" y="{_fmt(y)}" '
            f'width="{_fmt(max(w - 2.0, 1.0))}" height="{_fmt(row_h)}" rx="{_fmt(rx)}" '
            f'fill="{fill}" stroke="#FFFFFF" stroke-width="2">'
            f'<title>{xml_escape(tip)}</title></rect>'
        )
        # Two-line label (name + duration) when the bar is wide enough.
        label = _clip_label(r["name"], w)
        if label:
            txt = readable_ink(fill)
            cx = x + w / 2.0
            two_line = w >= 92.0
            if two_line:
                parts.append(
                    f'<text x="{_fmt(cx)}" y="{_fmt(y + row_h / 2.0 - 3)}" font-size="17" '
                    f'font-weight="600" fill="{txt}" text-anchor="middle" '
                    f'pointer-events="none">{xml_escape(label)}</text>'
                )
                parts.append(
                    f'<text x="{_fmt(cx)}" y="{_fmt(y + row_h / 2.0 + 19)}" font-size="14" '
                    f'fill="{txt}" text-anchor="middle" font-family="Roboto Mono, monospace" '
                    f'opacity="0.85" pointer-events="none">{r["ms"]} ms</text>'
                )
            else:
                parts.append(
                    f'<text x="{_fmt(cx)}" y="{_fmt(y + row_h / 2.0 + 5)}" font-size="15" '
                    f'font-weight="600" fill="{txt}" text-anchor="middle" '
                    f'pointer-events="none">{xml_escape(label)}</text>'
                )

    # Callout: annotate the hot bar so the takeaway is unmissable in the raster.
    hot = next(r for r in rects if r["name"] == "run_sql")
    hx = plot_x + (hot["x_ms"] + hot["w_ms"] / 2.0) * px_per_ms
    hy = plot_y + hot["depth"] * (row_h + row_gap)
    ann_y = plot_y + (max_depth + 1) * (row_h + row_gap) + 46.0
    parts.append(
        f'<line x1="{_fmt(hx)}" y1="{_fmt(hy + row_h)}" x2="{_fmt(hx)}" y2="{_fmt(ann_y - 22)}" '
        f'stroke="{muted}" stroke-width="1.5" stroke-dasharray="3 4"/>'
    )
    parts.append(
        f'<circle cx="{_fmt(hx)}" cy="{_fmt(ann_y - 22)}" r="3.5" fill="{muted}"/>'
    )
    parts.append(
        f'<text x="{_fmt(hx)}" y="{_fmt(ann_y)}" font-size="17" font-weight="600" fill="{ink}" '
        f'text-anchor="middle">run_sql = 214 ms (45%) - a single un-cached query holds a lock</text>'
    )

    # Legend: root anchor + warm depth ramp + the on/off critical-path split.
    # Every fill on the canvas — blue root, warm ramp, cool off-path grey — gets
    # a key entry so no colour is left unexplained.
    legend_y = ann_y + 40.0
    lx = plot_x
    parts.append(
        f'<text x="{_fmt(lx)}" y="{_fmt(legend_y)}" font-size="15" font-weight="700" '
        f'fill="{ink}">Colour</text>'
    )

    # Blue root swatch.
    parts.append(
        f'<rect x="{_fmt(lx + 74)}" y="{_fmt(legend_y - 14)}" width="24" height="16" '
        f'rx="4" fill="{ROOT_FILL}"/>'
    )
    parts.append(
        f'<text x="{_fmt(lx + 106)}" y="{_fmt(legend_y)}" font-size="15" fill="{muted}">'
        f'request root</text>'
    )

    # Warm ramp swatches + label.
    ramp_x = lx + 236.0
    for i, hexc in enumerate(DEPTH_RAMP):
        parts.append(
            f'<rect x="{_fmt(ramp_x + i * 26)}" y="{_fmt(legend_y - 14)}" width="24" height="16" '
            f'rx="4" fill="{hexc}"/>'
        )
    parts.append(
        f'<text x="{_fmt(ramp_x + len(DEPTH_RAMP) * 26 + 12)}" y="{_fmt(legend_y)}" '
        f'font-size="15" fill="{muted}">warm = critical path (deeper is hotter)</text>'
    )

    # Off-path grey swatch + label.
    grey_x = ramp_x + len(DEPTH_RAMP) * 26 + 320.0
    parts.append(
        f'<rect x="{_fmt(grey_x)}" y="{_fmt(legend_y - 14)}" '
        f'width="24" height="16" rx="4" fill="#8790A6"/>'
    )
    parts.append(
        f'<text x="{_fmt(grey_x + 32)}" y="{_fmt(legend_y)}" '
        f'font-size="15" fill="{muted}">grey = off the hot path</text>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                           #
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    """Write the icicle SVG to disk.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    default_out = Path(__file__).resolve().parent.parent / "assets" / "svg-examples" / "icicle.svg"
    parser = argparse.ArgumentParser(description="Render the icicle / flame-graph example SVG.")
    parser.add_argument("--out", default=str(default_out), help="Output SVG path.")
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the fullscreen control (default: self-contained).",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal", "high-contrast", "monochrome",
            "deuteranopia", "protanopia", "tritanopia",
        ),
        default="universal",
        help=(
            "palette accessibility level (accepted for CLI parity but a no-op "
            "here: the depth ramps are a tuned sequential map, already CVD- and "
            "greyscale-safe, so a categorical level is not applied)"
        ),
    )
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    write_svg(out_path, render_svg(args.mode, accessibility=args.accessibility))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

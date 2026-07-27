#!/usr/bin/env python3
"""
make_sankey — publication-quality Sankey diagram as a hand-authored SVG.

A Sankey diagram shows *flows* between nodes as ribbons whose width is
proportional to the volume they carry. It answers "where does the
quantity go, and how much is lost at each hop?" better than any bar or
pie chart, because the eye reads the width of a ribbon as a magnitude
and follows it across the whole cascade.

Vega-Lite has no native Sankey mark, so this figure is built as an SVG
string by hand rather than through ``vl_convert``. The layout is a
left-to-right layered graph:

* **Nodes** are stacked vertical bars, one column ("layer") per stage
  of the journey. Each node's height is proportional to the volume that
  passes through it.
* **Links** are cubic Bézier ribbons whose vertical thickness at both
  ends equals the volume of that flow; a flow that splits keeps its
  total width conserved (widths in = widths out at every node).

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, rounded
node corners, a start-anchored title plus a one-line takeaway subtitle.

Interaction (no JavaScript): every ribbon carries a native ``<title>``
tooltip with its exact volume, and a CSS ``:hover`` / ``:focus`` rule
dims the other ribbons so the hovered flow pops — the "hover-highlight
a flow" affordance that suits this capability. The figure is otherwise
static (a Sankey does not benefit from animation), so ``animated`` is
false and ``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/sankey.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import forced_color_patterns, load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _render import svg_example_path, write_svg  # noqa: E402
from _svg import svg_open  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1360
HEIGHT = 820
MARGIN_LEFT = 44
MARGIN_RIGHT = 44
MARGIN_TOP = 168         # room for title + subtitle + stage headers
MARGIN_BOTTOM = 56

INK = "#1D1D1F"          # primary text
SUBINK = "#6E6E73"       # secondary text
GRIDLINE = "#E5E5EA"     # hairline neutral
BG = "#FFFFFF"

NODE_WIDTH = 24          # px width of each node bar
NODE_PAD = 40            # vertical gap between stacked nodes in a layer
LABEL_GAP = 14           # gap between a node bar and its text label

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"


# ------------------------------------------------------------------
# The story (illustrative but plausible): a week of visitors to a SaaS
# marketing site, from acquisition channel through the funnel to the
# outcome. The takeaway: organic search is the biggest top-of-funnel
# source, yet paid traffic converts to a paid plan at a higher rate.
# ------------------------------------------------------------------
# Nodes: (id, human label, layer index 0..3).
NODES: List[Tuple[str, str, int]] = [
    # Layer 0 — acquisition channel
    ("organic", "Organic search", 0),
    ("paid", "Paid ads", 0),
    ("referral", "Referral", 0),
    # Layer 1 — engagement
    ("browsed", "Browsed", 1),
    ("bounced", "Bounced", 1),
    # Layer 2 — intent
    ("signup", "Signed up", 2),
    ("left", "Left", 2),
    # Layer 3 — outcome
    ("paidplan", "Paid plan", 3),
    ("freeplan", "Free plan", 3),
    ("churned", "Churned", 3),
]

# Links: (source id, target id, volume of visitors).
LINKS: List[Tuple[str, str, int]] = [
    # channel -> engagement
    ("organic", "browsed", 4200),
    ("organic", "bounced", 1800),
    ("paid", "browsed", 2600),
    ("paid", "bounced", 900),
    ("referral", "browsed", 1400),
    ("referral", "bounced", 400),
    # engagement -> intent (only "browsed" continues)
    ("browsed", "signup", 3100),
    ("browsed", "left", 5100),
    # intent -> outcome
    ("signup", "paidplan", 900),
    ("signup", "freeplan", 1700),
    ("signup", "churned", 500),
]

# Color each *source-channel* flow by the channel it came from, so the
# ribbon color tells you the origin all the way down the cascade. The
# node itself borrows the color of its dominant inbound channel.
PALETTE = load_palette()
CHANNEL_COLOR: Dict[str, str] = {
    "organic": PALETTE.get("Blue", "#007AFF"),
    "paid": PALETTE.get("Orange", "#FF9500"),
    "referral": PALETTE.get("Purple", "#AF52DE"),
}
NEUTRAL_NODE = "#C7C7CC"  # for "bounced" / "left" / "churned" sinks
CHURN_TINT = PALETTE.get("Gray", "#8E8E93")

# A ribbon carries the color of the channel that dominates its source
# node, so the origin story survives all the way down the cascade. To
# resolve that dominant channel we walk each node's inbound flows back to
# a layer-0 channel node.
_CHANNEL_IDS = set(CHANNEL_COLOR)


def _dominant_channel(node_id: str) -> str | None:
    """Return the layer-0 channel that contributes the most flow into ``node_id``.

    Walks inbound links recursively until it reaches channel nodes, then
    picks the channel with the largest cumulative volume. Sink-type nodes
    (bounced / left / churned) are treated as neutral and return ``None``.

    Parameters
    ----------
    node_id : str
        Node identifier from :data:`NODES`.

    Returns
    -------
    str or None
        The dominant channel id, or ``None`` when the node is a neutral
        sink or has no traceable channel origin.
    """
    if node_id in ("bounced", "left", "churned"):
        return None
    if node_id in _CHANNEL_IDS:
        return node_id
    tally: Dict[str, float] = {}
    for s, t, vol in LINKS:
        if t != node_id:
            continue
        src_channel = _dominant_channel(s)
        if src_channel is not None:
            tally[src_channel] = tally.get(src_channel, 0.0) + vol
    if not tally:
        return None
    return max(tally, key=lambda k: tally[k])


# ------------------------------------------------------------------
# Layout maths
# ------------------------------------------------------------------
def _node_volume(node_id: str) -> int:
    """Return the throughput of a node = max(inflow, outflow).

    A pure source node has no inflow, a pure sink has no outflow; using
    the max keeps a node's bar height equal to the total volume that
    actually passes through it.

    Parameters
    ----------
    node_id : str
        Node identifier from :data:`NODES`.

    Returns
    -------
    int
        Visitor volume routed through the node.
    """
    inflow = sum(v for s, t, v in LINKS if t == node_id)
    outflow = sum(v for s, t, v in LINKS if s == node_id)
    return max(inflow, outflow)


def _layers() -> Dict[int, List[str]]:
    """Group node ids by their layer index, preserving declaration order."""
    layers: Dict[int, List[str]] = {}
    for node_id, _label, layer in NODES:
        layers.setdefault(layer, []).append(node_id)
    return layers


def _compute_geometry() -> Tuple[Dict[str, dict], float]:
    """Place every node and return (geometry, volume→pixel scale).

    Returns
    -------
    geometry : dict
        ``{node_id: {"x", "y", "h", "vol", "layer",
        "in_cursor", "out_cursor"}}`` in SVG pixel coordinates. The
        cursors track how much of a node's top/bottom edge has already
        been consumed by ribbons, so stacked links do not overlap.
    scale : float
        Pixels per unit volume, chosen so the tallest layer fills the
        plot height minus its inter-node padding.
    """
    layers = _layers()
    plot_top = MARGIN_TOP
    plot_bottom = HEIGHT - MARGIN_BOTTOM
    plot_h = plot_bottom - plot_top
    plot_left = MARGIN_LEFT
    plot_right = WIDTH - MARGIN_RIGHT

    # Vertical scale: the densest layer (most total volume) must fit.
    max_layer_vol = 0
    for ids in layers.values():
        total = sum(_node_volume(n) for n in ids)
        pad_total = NODE_PAD * (len(ids) - 1)
        # Effective volume that competes for the padded height.
        max_layer_vol = max(max_layer_vol, total / max(1e-9, (plot_h - pad_total)))
    scale = 1.0 / max_layer_vol if max_layer_vol else 1.0

    n_layers = len(layers)
    # Evenly space layer x-positions across the plot width.
    xs = [
        plot_left + i * (plot_right - plot_left - NODE_WIDTH) / (n_layers - 1)
        for i in range(n_layers)
    ]

    geometry: Dict[str, dict] = {}
    for layer_idx in sorted(layers):
        ids = layers[layer_idx]
        heights = [_node_volume(n) * scale for n in ids]
        pad_total = NODE_PAD * (len(ids) - 1)
        stack_h = sum(heights) + pad_total
        # Center the stack vertically in the plot.
        y = plot_top + (plot_h - stack_h) / 2.0
        for node_id, h in zip(ids, heights):
            geometry[node_id] = {
                "x": xs[layer_idx],
                "y": y,
                "h": h,
                "vol": _node_volume(node_id),
                "layer": layer_idx,
                "out_cursor": y,  # next outbound ribbon starts here
                "in_cursor": y,   # next inbound ribbon lands here
            }
            y += h + NODE_PAD

    return geometry, scale


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def _ribbon_path(x0: float, y0: float, x1: float, y1: float, thick: float) -> str:
    """Build a filled cubic-Bézier ribbon of constant vertical thickness.

    The ribbon leaves the source node's right edge at ``(x0, y0)`` and
    lands on the target node's left edge at ``(x1, y1)``; ``y0`` / ``y1``
    are the *top* of the ribbon at each end. Control points sit at the
    horizontal midpoint for the classic Sankey S-curve.

    Parameters
    ----------
    x0, y0 : float
        Top-left corner of the ribbon (source side).
    x1, y1 : float
        Top-right corner of the ribbon (target side).
    thick : float
        Vertical thickness in pixels (the flow volume × scale).

    Returns
    -------
    str
        An SVG path ``d`` attribute value describing the closed ribbon.
    """
    xc = (x0 + x1) / 2.0
    top = (
        f"M{x0:.1f},{y0:.1f} "
        f"C{xc:.1f},{y0:.1f} {xc:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
    )
    bottom = (
        f"L{x1:.1f},{y1 + thick:.1f} "
        f"C{xc:.1f},{y1 + thick:.1f} {xc:.1f},{y0 + thick:.1f} {x0:.1f},{y0 + thick:.1f} Z"
    )
    return top + " " + bottom


def _fmt_k(v: int) -> str:
    """Format a visitor count compactly (e.g. 4200 → '4.2k')."""
    if v >= 1000:
        return f"{v / 1000:.1f}k".replace(".0k", "k")
    return str(v)


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full Sankey SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode for the fullscreen control, one of three:
        ``"self-contained"`` (default) ships a self-carrying fullscreen
        button plus its wiring script; ``"external"`` ships no button and
        defers fullscreen to a page-level module; ``"static"`` ships no
        interactivity at all.
    accessibility : str, optional
        Palette accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). Defaults to ``"universal"``, the
        colour-vision-safe standard, which reuses the module-level palette so
        the emitted SVG stays unchanged; any other level remaps the channel
        and outcome hues.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    # ``universal`` reuses the module-level constants (output byte-identical);
    # any other level re-reads the palette at that accessibility level and
    # rebuilds the channel / outcome colours locally.
    if accessibility == "universal":
        palette = PALETTE
        channel_color = CHANNEL_COLOR
        churn_tint = CHURN_TINT
    else:
        palette = load_palette(accessibility)
        channel_color = {
            "organic": palette.get("Blue", "#007AFF"),
            "paid": palette.get("Orange", "#FF9500"),
            "referral": palette.get("Purple", "#AF52DE"),
        }
        churn_tint = palette.get("Gray", "#8E8E93")

    geometry, _scale = _compute_geometry()
    label_of = {nid: lbl for nid, lbl, _ in NODES}
    n_layers = len(_layers())

    parts: List[str] = []

    # --- header: accessible role + title + description ---
    title_txt = "Organic search fills the funnel, but paid ads convert"
    subtitle_txt = (
        "One week of site visitors, from channel to outcome — illustrative data"
    )
    desc_txt = (
        "Sankey diagram of visitor flow across four stages: acquisition "
        "channel, engagement, sign-up intent, and outcome. Ribbon width is "
        "proportional to the number of visitors. Organic search is the "
        "largest source; paid-ads visitors reach a paid plan at a higher rate."
    )
    parts.append(svg_open(WIDTH, HEIGHT, "sankey-title", "sankey-desc", font_family=FONT))
    parts.append(f'<title id="sankey-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="sankey-desc">{escape(desc_txt)}</desc>')

    # OS-adaptive overrides (additive; every rule lives inside an @media block,
    # so the default render is byte-for-byte unchanged). The channel hues (and
    # the two positive-outcome node hues) carry ``.sk-<id>`` classes on both the
    # ribbons and the nodes. Under prefers-contrast they deepen together to
    # their high-contrast spacing, keeping each origin channel distinguishable
    # (role="fill" only, so each ribbon's white separating halo is untouched).
    # Under forced-colors (Windows High Contrast) the ~4-colour system palette
    # cannot preserve five colour-coded origins, so each channel/outcome hue is
    # instead handed a distinct Canvas/CanvasText PATTERN (hatch / dots / cross)
    # via forced_color_patterns: the ribbons and nodes of a series take that
    # pattern, so the origin story survives the cascade even when colour is
    # stripped (neutral drop-off ribbons stay plain, as they should).
    sk_series = {
        ".sk-organic": channel_color["organic"],
        ".sk-paid": channel_color["paid"],
        ".sk-referral": channel_color["referral"],
        ".sk-paidplan": palette.get("Green", "#34C759"),
        ".sk-freeplan": palette.get("Teal", "#5AC8FA"),
    }
    fcp_defs, fcp_style = forced_color_patterns(list(sk_series), prefix="sk-fcp")
    # --- CSS: hover/focus highlight one ribbon, dim the rest ---
    parts.append(
        "<style>"
        ".link{transition:opacity .15s ease}"
        # When the ribbon group is hovered or a ribbon is focused, fade
        # every ribbon, then bring the hovered/focused one back to full.
        "#links:hover .link{opacity:.18}"
        "#links .link:hover,#links .link:focus{opacity:1}"
        ".link:focus{outline:none}"
        + os_adaptive_style(sk_series, role="fill")
        + fcp_style
        + os_dark_style()
        + "</style>"
    )
    parts.append(f"<defs>{fcp_defs}</defs>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="{MARGIN_LEFT}" y="58" font-size="34" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="{MARGIN_LEFT}" y="92" font-size="20" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    # --- stage headers across the top of the plot ---
    stage_names = ["Channel", "Engagement", "Intent", "Outcome"]
    layers = _layers()
    for layer_idx in sorted(layers):
        # Anchor the stage label above the first node of the layer.
        any_node = layers[layer_idx][0]
        gx = geometry[any_node]["x"]
        anchor = "start"
        tx = gx
        if layer_idx == n_layers - 1:
            anchor = "end"
            tx = gx + NODE_WIDTH
        parts.append(
            f'<text x="{tx:.1f}" y="{MARGIN_TOP - 22:.1f}" font-size="16" '
            f'font-weight="600" letter-spacing="1.0" fill="{SUBINK}" '
            f'text-anchor="{anchor}">{escape(stage_names[layer_idx].upper())}</text>'
        )

    # --- ribbons (drawn before nodes so nodes sit on top) ---
    parts.append('<g id="links">')
    # Draw thickest ribbons first so thin ones layer cleanly on top.
    ordered = sorted(LINKS, key=lambda lk: -lk[2])
    # But cursors must advance in the node's stacking order, so precompute
    # ribbon endpoints in declaration order, then emit in thickness order.
    endpoints: Dict[Tuple[str, str], Tuple[float, float, float, float, float]] = {}
    for s, t, vol in LINKS:
        gs = geometry[s]
        gt = geometry[t]
        thick = gs["h"] * (vol / max(1e-9, gs["vol"]))  # share of source height
        x0 = gs["x"] + NODE_WIDTH
        y0 = gs["out_cursor"]
        x1 = gt["x"]
        y1 = gt["in_cursor"]
        gs["out_cursor"] += thick
        gt["in_cursor"] += thick
        endpoints[(s, t)] = (x0, y0, x1, y1, thick)

    for s, t, vol in ordered:
        x0, y0, x1, y1, thick = endpoints[(s, t)]
        # Ribbon color: a flow into a neutral drop-off (bounced / left /
        # churned) is gray; every other flow carries the color of the
        # channel that dominates its *source* node, so the origin story
        # survives the whole cascade instead of turning gray after layer 0.
        ribbon_channel: str | None = None
        if t in ("churned", "left", "bounced"):
            color = churn_tint
        else:
            channel = _dominant_channel(s)
            color = channel_color.get(channel or "", "#AEAEB2")
            if channel in channel_color:
                ribbon_channel = channel
        d = _ribbon_path(x0, y0, x1, y1, thick)
        # Per-channel class = the prefers-contrast hook (only on ribbons that
        # actually carry a channel hue; neutral drop-off ribbons stay grey).
        chan_cls = f" sk-{ribbon_channel}" if ribbon_channel else ""
        tip = (
            f"{label_of[s]} → {label_of[t]}: {vol:,} visitors"
        )
        # A thin white halo separates crossing ribbons so overlapping
        # same-direction flows never blend into a muddy blob; the fill
        # opacity stays low enough that a node's several ribbons read as
        # distinct layers rather than one solid slab.
        parts.append(
            f'<path class="link{chan_cls}" tabindex="0" role="img" '
            f'aria-label="{escape(tip)}" d="{d}" fill="{color}" '
            f'fill-opacity="0.55" stroke="#FFFFFF" stroke-width="1.25" '
            f'stroke-opacity="0.9">'
            f'<title>{escape(tip)}</title></path>'
        )
    parts.append("</g>")

    # --- nodes + labels ---
    parts.append('<g id="nodes">')
    for node_id, label, layer_idx in NODES:
        g = geometry[node_id]
        # Node color: channel nodes get their brand hue; sinks get gray;
        # positive outcomes get green; the rest borrow a neutral ink.
        node_cls = ""
        if node_id in channel_color:
            ncol = channel_color[node_id]
            node_cls = f" sk-{node_id}"
        elif node_id in ("bounced", "left", "churned"):
            ncol = NEUTRAL_NODE
        elif node_id == "paidplan":
            ncol = palette.get("Green", "#34C759")
            node_cls = " sk-paidplan"
        elif node_id == "freeplan":
            ncol = palette.get("Teal", "#5AC8FA")
            node_cls = " sk-freeplan"
        else:
            ncol = "#8E8E93"
        parts.append(
            f'<rect class="node{node_cls}" x="{g["x"]:.1f}" y="{g["y"]:.1f}" '
            f'width="{NODE_WIDTH}" height="{max(1.0, g["h"]):.1f}" rx="5" fill="{ncol}">'
            f'<title>{escape(label)}: {g["vol"]:,} visitors</title></rect>'
        )
        # Label placement: left layers label to the right of the bar,
        # the final layer labels to the left, so text never runs off-canvas.
        cy = g["y"] + g["h"] / 2.0
        vol_txt = _fmt_k(g["vol"])
        if layer_idx == n_layers - 1:
            lx = g["x"] - LABEL_GAP
            anchor = "end"
        else:
            lx = g["x"] + NODE_WIDTH + LABEL_GAP
            anchor = "start"
        # Name on the upper line, count on the lower line, so the two never
        # collide however tall or short the node is.
        parts.append(
            f'<text x="{lx:.1f}" y="{cy:.1f}" text-anchor="{anchor}">'
            f'<tspan x="{lx:.1f}" dy="-0.35em" font-size="19" '
            f'font-weight="600" fill="{INK}">{escape(label)}</tspan>'
            f'<tspan x="{lx:.1f}" dy="1.25em" font-family="{FONT_MONO}" '
            f'font-weight="400" fill="{SUBINK}" font-size="15">'
            f'{escape(vol_txt)}</tspan></text>'
        )
    parts.append("</g>")

    # --- footnote: read the hover affordance ---
    parts.append(
        f'<text x="{MARGIN_LEFT}" y="{HEIGHT - 20}" font-size="15" '
        f'fill="{SUBINK}">Ribbon width ∝ visitors · hover or focus a '
        f'flow to trace it</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the Sankey SVG to the skill's example asset folder."""
    parser = argparse.ArgumentParser(description="Render the Sankey diagram SVG.")
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the fullscreen control.",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal",
            "high-contrast",
            "monochrome",
            "deuteranopia",
            "protanopia",
            "tritanopia",
        ),
        default="universal",
        help="Palette accessibility level (default: universal, the CVD-safe standard).",
    )
    parser.add_argument("--out", default=None, help="Output path (defaults to the example asset).")
    args = parser.parse_args()
    out = Path(args.out) if args.out else svg_example_path(__file__, "sankey")
    write_svg(out, build_svg(args.mode, args.accessibility))


if __name__ == "__main__":
    main()

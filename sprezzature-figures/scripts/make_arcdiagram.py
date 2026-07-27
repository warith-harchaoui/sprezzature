#!/usr/bin/env python3
"""
make_arcdiagram — publication-quality arc diagram as a hand-authored SVG.

An arc diagram lays every node on a single horizontal baseline and draws
each link as a semicircular arc rising *above* that line. Because the
nodes share one axis, the reader's whole attention goes to the arcs — and
to the **order** of the nodes, which is the diagram's real message. A good
ordering makes structure jump out: tightly connected groups sit next to
each other so their arcs are short and dense, while the rare long arc that
leaps across the whole line flags a bridge — an edge that holds two
otherwise separate communities together.

This figure tells that story with an illustrative collaboration network:
who co-authored a paper with whom across two research groups. The nodes
are ordered so the *Vision* group and the *Language* group cluster on the
left and right; one researcher, **Nadia**, sits in the middle and is the
only person with co-authors in *both* groups. Her two long arcs sweeping
across the diagram are the single bridge between the two worlds — remove
her and the collaboration graph falls into two disconnected halves.

Vega-Lite has no native arc-diagram mark, so the figure is built as an SVG
string by hand rather than through ``vl_convert``. House style follows
``_style.py`` / ``bar.vl.json``: Roboto type, the Apple-system categorical
palette, ink ``#1D1D1F`` on white, rounded label treatment, a
start-anchored title plus a one-line takeaway subtitle.

Interaction (no JavaScript): every node and every arc carries a native
``<title>`` tooltip, and CSS ``:hover`` / ``:focus`` on an arc fades every
other arc and thickens the hovered one — the "pick out one collaboration"
affordance that suits this capability, keyboard-reachable via ``tabindex``.
The figure is deliberately **static** (no draw-on animation): an arc
diagram's whole message is the node *order* and the shape of the arcs, and
a still shows both at once — motion would only hide the picture while it
runs. Every arc is fully painted at load; the interaction merely lets a
reader isolate one collaboration.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/arcdiagram.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _svg import svg_open  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens — poster-scale so the arcs read big.
# ------------------------------------------------------------------
WIDTH = 1240
HEIGHT = 760

MARGIN_L = 92
MARGIN_R = 92
BASELINE_Y = 512          # y of the horizontal node line
NODE_R = 11               # node dot radius
LABEL_DY = 30             # node label baseline below the line
LABEL_ROT = 30            # label rotation (deg) below the baseline

INK = "#1D1D1F"           # primary text
SUBINK = "#6E6E73"        # secondary text
HAIR = "#D2D2D7"          # the baseline rule
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"


# ------------------------------------------------------------------
# The story (illustrative but plausible): a lab's co-authorship network.
# Two research groups — Vision and Language — barely overlap. Node order
# is chosen so each group clusters (short, dense arcs) and the one
# cross-group researcher, Nadia, sits in the middle. Her two arcs are the
# only links spanning the two groups: the bridge. Ordering IS the message.
# ------------------------------------------------------------------
GROUP_VISION = "Vision"
GROUP_LANGUAGE = "Language"
GROUP_BRIDGE = "Bridge"

# Nodes in reading order (left -> right). The order is the point: Vision
# people first, the bridge (Nadia) in the centre, Language people last.
NODES: List[Tuple[str, str]] = [
    ("Ito", GROUP_VISION),
    ("Reyes", GROUP_VISION),
    ("Okafor", GROUP_VISION),
    ("Chen", GROUP_VISION),
    ("Novak", GROUP_VISION),
    ("Nadia", GROUP_BRIDGE),
    ("Haddad", GROUP_LANGUAGE),
    ("Silva", GROUP_LANGUAGE),
    ("Weber", GROUP_LANGUAGE),
    ("Park", GROUP_LANGUAGE),
    ("Lund", GROUP_LANGUAGE),
]

# Co-authored papers (undirected). Weight = joint papers this year; it
# maps to arc stroke width so a frequent pairing reads as a bold arc.
LINKS: List[Tuple[str, str, int]] = [
    # --- Vision group: dense internal collaboration ---
    ("Ito", "Reyes", 4),
    ("Ito", "Okafor", 2),
    ("Reyes", "Okafor", 3),
    ("Okafor", "Chen", 2),
    ("Chen", "Novak", 3),
    ("Reyes", "Chen", 1),
    ("Novak", "Nadia", 2),
    # --- The bridge: Nadia is the only person linking the two groups ---
    ("Nadia", "Haddad", 3),
    ("Nadia", "Silva", 2),
    # --- Language group: its own dense internal collaboration ---
    ("Haddad", "Silva", 4),
    ("Haddad", "Weber", 2),
    ("Silva", "Weber", 3),
    ("Weber", "Park", 2),
    ("Park", "Lund", 3),
    ("Silva", "Park", 1),
]

# Brand hue per group — the arc's origin group colours it. Built from the
# palette at render time so the accessibility level can remap the hues.
def _group_color(accessibility: str = "universal") -> Dict[str, str]:
    """Return the group → hex mapping at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level threaded into :func:`_style.load_palette`.
        ``"universal"`` (default) is the colour-vision-safe standard.

    Returns
    -------
    dict of str to str
        Mapping ``{group_name: hex}`` for the Vision, Language and bridge groups.
    """
    palette = load_palette(accessibility)
    return {
        GROUP_VISION: palette.get("Blue", "#007AFF"),
        GROUP_LANGUAGE: palette.get("Orange", "#FF9500"),
        GROUP_BRIDGE: palette.get("Purple", "#AF52DE"),
    }


# ------------------------------------------------------------------
# Layout maths
# ------------------------------------------------------------------
def _node_positions() -> Dict[str, float]:
    """Return each node's x pixel coordinate along the baseline.

    Nodes are spread evenly between the left and right margins, in the
    declared reading order — the order is the diagram's message, so it is
    honoured exactly as listed.

    Returns
    -------
    dict of str to float
        Mapping ``{node_name: x_pixels}``.
    """
    n = len(NODES)
    span = WIDTH - MARGIN_L - MARGIN_R
    step = span / (n - 1) if n > 1 else 0.0
    return {name: MARGIN_L + i * step for i, (name, _grp) in enumerate(NODES)}


def _arc_path(x0: float, x1: float) -> Tuple[str, float]:
    """Return the ``d`` for a semicircular arc between two baseline points.

    The arc is a half-ellipse rising above the baseline; its height grows
    with the horizontal distance between the endpoints, so a link between
    far-apart nodes bows up high (a visible bridge) while neighbours join
    with a low, tight hop.

    Parameters
    ----------
    x0, x1 : float
        The x coordinates of the two endpoints on the baseline.

    Returns
    -------
    tuple of (str, float)
        The SVG path ``d`` string and the arc's peak height in pixels
        (how far above the baseline the arc rises).
    """
    lo, hi = sorted((x0, x1))
    rx = (hi - lo) / 2.0                 # horizontal radius
    # Vertical radius. Short neighbour hops would otherwise stay tiny and
    # leave the upper half of the canvas empty, so the arc height is a
    # square-root-shaped lift of the span: a generous floor lifts even the
    # tightest pairing well off the line, and taller arcs still read as
    # wider spans. Capped so the tallest bridge arc clears the brackets.
    ry = min(58 + math.sqrt(rx) * 20.0, BASELINE_Y - 232)
    # Sweep-flag 0 draws the arc on the upper side (SVG y grows downward).
    d = f"M{lo:.2f},{BASELINE_Y:.2f} A{rx:.2f},{ry:.2f} 0 0 1 {hi:.2f},{BASELINE_Y:.2f}"
    return d, ry


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full arc-diagram SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level threaded into :func:`_style.load_palette`
        (``"universal"``, ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` or ``"tritanopia"``). Defaults to
        ``"universal"``, the colour-vision-safe standard.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    GROUP_COLOR = _group_color(accessibility)
    pos = _node_positions()
    node_group = {name: grp for name, grp in NODES}

    # Degree (number of co-authors) per node, for the tooltip + dot size.
    degree: Dict[str, int] = {name: 0 for name, _ in NODES}
    for a, b, _w in LINKS:
        degree[a] += 1
        degree[b] += 1

    parts: List[str] = []

    title_txt = "One researcher holds two research groups together"
    subtitle_txt = (
        "Co-authorship across a lab this year — nodes ordered by group; "
        "illustrative data"
    )
    desc_txt = (
        "Arc diagram of co-authorship in a research lab. Eleven "
        "researchers sit on one horizontal line, ordered so the Vision "
        "group clusters on the left and the Language group on the right. "
        "Each co-authored pairing is an arc rising above the line, its "
        "thickness proportional to the number of joint papers. Both groups "
        "collaborate densely inside themselves, drawing short low arcs. "
        "Only Nadia, in the centre, co-authors with people in both groups: "
        "her two long arcs sweeping across the diagram are the single "
        "bridge linking the two communities."
    )

    parts.append(svg_open(WIDTH, HEIGHT, "arc-title", "arc-desc", font_family=FONT))
    parts.append(f'<title id="arc-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="arc-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hover / focus an arc isolates it; nodes carry native tooltips ---
    # A single horizontal line means arcs, not nodes, hold the information, so
    # the interaction is arc-centred: hovering the arc layer fades every arc,
    # and the one under the cursor (or keyboard focus) snaps back to full
    # strength and thickens — "pick out one collaboration". Nodes stay simple:
    # a native <title> tooltip naming the person, their group and their degree.
    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule below lives inside a media query). Under
    # prefers-contrast each group's arcs (stroke) and nodes (fill) deepen to the
    # group's high-contrast hue, and every arc goes fully opaque so a deepened
    # bridge/intra distinction stays readable. Under forced-colors the diagram
    # drops to system line art — legitimate because the arc-diagram's message is
    # carried by node ORDER, the group brackets and the node labels, not colour:
    # arcs are re-stroked to CanvasText (never filled — the paths are open, a
    # fill would flood the chord region) and nodes take CanvasText fills.
    arc_series = {f".arc-{g.lower()}": GROUP_COLOR[g] for g in
                  (GROUP_VISION, GROUP_LANGUAGE, GROUP_BRIDGE)}
    node_series = {f".node-{g.lower()}": GROUP_COLOR[g] for g in
                   (GROUP_VISION, GROUP_LANGUAGE, GROUP_BRIDGE)}
    adaptive_arcs = os_adaptive_style(
        arc_series,
        role="stroke",
        extra_contrast=".arc{stroke-opacity:1 !important;}",
    )
    # Forced-colors: re-stroke every arc and re-fill every node to the system
    # ink. Done as one explicit block so the arcs get stroke (not fill).
    forced_block = (
        "@media (forced-colors: active){\n  "
        ".arc{stroke:CanvasText;}\n  "
        ".node{fill:CanvasText;}\n"
        "}"
    )
    adaptive_nodes = os_adaptive_style(node_series, role="fill")
    parts.append(
        "<style>"
        ".arc{transition:stroke-opacity .18s ease,stroke-width .18s ease}"
        "#arcs:hover .arc{stroke-opacity:.12}"
        "#arcs .arc:hover,#arcs .arc:focus{stroke-opacity:1;stroke-width:9}"
        ".arc:focus,.node:focus{outline:none}"
        + adaptive_arcs
        + adaptive_nodes
        + forced_block
        + os_dark_style()
        + "</style>"
    )

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="{MARGIN_L}" y="62" font-size="32" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="{MARGIN_L}" y="94" font-size="18" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    # --- the baseline rule ---
    parts.append(
        f'<line x1="{MARGIN_L - 22:.1f}" y1="{BASELINE_Y}" '
        f'x2="{WIDTH - MARGIN_R + 22:.1f}" y2="{BASELINE_Y}" '
        f'stroke="{HAIR}" stroke-width="1.5"/>'
    )

    # --- arcs (drawn first, under the node dots) ---
    # Sort so the widest bridge arcs are painted last (on top) and the SMIL
    # draw-on finishes with them, drawing the eye to the bridge.
    # Painted widest-arc-last so the bridge arcs sit on top, fully opaque and
    # base-visible in the static raster (no draw-on — the arcs ARE the story).
    parts.append('<g id="arcs" fill="none" stroke-linecap="round">')
    ordered = sorted(
        enumerate(LINKS),
        key=lambda item: abs(pos[item[1][0]] - pos[item[1][1]]),
    )
    for _order_i, (_idx, (a, b, w)) in enumerate(ordered):
        d, _ry = _arc_path(pos[a], pos[b])
        # The arc takes the colour of the bridge node when it touches one,
        # else the shared group's colour (both endpoints in one group).
        grp_a, grp_b = node_group[a], node_group[b]
        if GROUP_BRIDGE in (grp_a, grp_b):
            color = GROUP_COLOR[GROUP_BRIDGE]
            is_bridge = True
        else:
            color = GROUP_COLOR[grp_a]
            is_bridge = False
        stroke_w = 2.6 + w * 1.7          # weight -> thickness
        opacity = 0.9 if is_bridge else 0.5
        tip = f"{a} & {b}: {w} joint paper{'s' if w != 1 else ''}"
        # The arc's group class (its colouring group) gives each @media rule a
        # per-group hook without changing the default paint.
        arc_grp = GROUP_BRIDGE if is_bridge else grp_a
        parts.append(
            f'<path class="arc arc-{arc_grp.lower()}" tabindex="0" role="img" '
            f'aria-label="{escape(tip)}" d="{d}" '
            f'stroke="{color}" stroke-width="{stroke_w:.2f}" '
            f'stroke-opacity="{opacity}">'
            f'<title>{escape(tip)}</title></path>'
        )
    parts.append("</g>")

    # --- node dots + labels ---
    parts.append('<g id="nodes">')
    for name, grp in NODES:
        x = pos[name]
        color = GROUP_COLOR[grp]
        r = NODE_R + (2.5 if grp == GROUP_BRIDGE else 0)
        deg = degree[name]
        role = {
            GROUP_VISION: "Vision group",
            GROUP_LANGUAGE: "Language group",
            GROUP_BRIDGE: "bridge between both groups",
        }[grp]
        tip = f"{name} — {role}, {deg} co-author{'s' if deg != 1 else ''}"
        parts.append(
            f'<circle class="node node-{grp.lower()}" tabindex="0" role="img" '
            f'aria-label="{escape(tip)}" cx="{x:.2f}" cy="{BASELINE_Y}" '
            f'r="{r}" fill="{color}" stroke="{BG}" stroke-width="3">'
            f'<title>{escape(tip)}</title></circle>'
        )
        # Label below the line, rotated so 11 names never collide. The
        # anchor sits a little left of the dot and the text runs down-left at
        # LABEL_ROT degrees; a shallow, uniform angle keeps every baseline
        # parallel so the row of names reads as one tidy diagonal comb.
        ly = BASELINE_Y + LABEL_DY
        weight = 700 if grp == GROUP_BRIDGE else 500
        fill = INK if grp == GROUP_BRIDGE else SUBINK
        parts.append(
            f'<text x="{x:.2f}" y="{ly:.2f}" font-size="17" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="end" '
            f'transform="rotate(-{LABEL_ROT} {x:.2f} {ly:.2f})">'
            f'{escape(name)}</text>'
        )
    parts.append("</g>")

    # --- group brackets + labels above the clusters ---
    def _bracket(x_from: float, x_to: float, label: str, color: str) -> None:
        """Draw a light span bracket over a cluster with a centred label."""
        y = 150
        mid = (x_from + x_to) / 2.0
        parts.append(
            f'<path d="M{x_from:.1f},{y + 12:.1f} L{x_from:.1f},{y:.1f} '
            f'L{x_to:.1f},{y:.1f} L{x_to:.1f},{y + 12:.1f}" fill="none" '
            f'stroke="{color}" stroke-width="1.6" stroke-opacity="0.55"/>'
        )
        parts.append(
            f'<text x="{mid:.1f}" y="{y - 12:.1f}" text-anchor="middle" '
            f'font-size="18" font-weight="700" fill="{color}">'
            f'{escape(label)}</text>'
        )

    _bracket(pos["Ito"] - 6, pos["Novak"] + 6, "Vision group", GROUP_COLOR[GROUP_VISION])
    _bracket(pos["Haddad"] - 6, pos["Lund"] + 6, "Language group", GROUP_COLOR[GROUP_LANGUAGE])

    # --- callout on the bridge node (sits just under the baseline, clear of
    # the arcs so it never collides with the tall bridge arcs above) ---
    # The rotated node labels fan down-left and reach ~30 px below their
    # baseline, so the callout sits in the clear band under them, centred on
    # the bridge node. A short dashed vertical leader ties it to Nadia's dot
    # without crossing any label.
    nx = pos["Nadia"]
    label_reach = BASELINE_Y + LABEL_DY + 34   # deepest ink of the rotated names
    cy = label_reach + 30
    # The bridge node's own name runs down-left and ends at nx, so a leader
    # dropped a few px to the RIGHT of nx clears it and lands centred enough.
    lx = nx + 10
    parts.append(
        f'<line x1="{nx:.1f}" y1="{BASELINE_Y + NODE_R + 6:.1f}" '
        f'x2="{lx:.1f}" y2="{cy - 30:.1f}" '
        f'stroke="{GROUP_COLOR[GROUP_BRIDGE]}" stroke-width="1.4" '
        f'stroke-dasharray="2 4" stroke-opacity="0.7"/>'
    )
    parts.append(
        f'<text x="{nx:.1f}" y="{cy:.1f}" text-anchor="middle" '
        f'font-size="18" font-weight="700" '
        f'fill="{GROUP_COLOR[GROUP_BRIDGE]}">Nadia — the only bridge</text>'
    )
    parts.append(
        f'<text x="{nx:.1f}" y="{cy + 24:.1f}" text-anchor="middle" '
        f'font-size="15" fill="{SUBINK}">her 2 arcs are the sole '
        f'cross-group links</text>'
    )

    # --- footnote: encoding legend + hover affordance ---
    parts.append(
        f'<text x="{MARGIN_L}" y="{HEIGHT - 26}" font-size="14" fill="{SUBINK}">'
        f'Each arc = a co-authored paper · arc thickness ∝ joint papers · '
        f'node order tells the story · hover or focus an arc to isolate one '
        f'collaboration</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the arc-diagram SVG to the skill's example asset folder.

    The ``--mode`` flag selects the interactivity mode of the emitted SVG
    (``self-contained`` / ``external`` / ``static``); see
    :func:`_interactive.fullscreen_control`.
    """
    render_cli(
        __file__, "arcdiagram", build_svg, description="Render the arc-diagram SVG."
    )


if __name__ == "__main__":
    main()

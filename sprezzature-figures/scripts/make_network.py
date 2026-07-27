#!/usr/bin/env python3
"""
make_network — publication-quality node-link network as a hand-authored SVG.

A node-link diagram places every entity as a node and draws an edge for
every relationship between two entities. It answers "who is connected to
whom, and who sits at the centre?" far better than an adjacency matrix or
a list of pairs, because the eye reads clusters, hubs, and bridges
directly from the layout.

Vega-Lite has no force simulation, so this figure is built as an SVG
string by hand rather than through ``vl_convert``. The layout is a small,
deterministic force-directed relaxation computed in pure Python (no
scientific stack): nodes repel each other (Coulomb-like), edges pull
their endpoints together (Hooke-like springs), and a gentle gravity keeps
the whole graph centred. A fixed random seed makes every run identical, so
the committed SVG is reproducible.

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, rounded label
treatment, a start-anchored title plus a one-line takeaway subtitle.

Interaction (no JavaScript): every node carries a native ``<title>``
tooltip, and a pure-CSS ``:hover`` / ``:focus-within`` rule fades the
whole graph except the hovered node, its incident edges, and its direct
neighbours — the "hover a node to highlight its neighbours" affordance
that suits this capability. The graph is otherwise static, so ``animated``
is false and ``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/network.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import random
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
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1200
HEIGHT = 980
PLOT_TOP = 168             # y where the graph area begins (below the title)
PLOT_PAD = 92              # inner margin around the layout box

INK = "#1D1D1F"             # primary text
SUBINK = "#6E6E73"          # secondary text
BG = "#FFFFFF"
EDGE = "#C7C7CC"            # resting edge colour (light neutral)

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"


# ------------------------------------------------------------------
# The story (illustrative but plausible): the service-to-service call
# graph of an online-store backend. A node is a microservice; an edge
# means "the first service makes synchronous calls to the second". The
# node's colour marks its team and its size marks how many other
# services depend on it (in-degree). The takeaway: the Auth service is a
# hidden single point of failure — almost everything calls it, so if it
# stalls, the whole store stalls. Hovering any service lights up exactly
# what it touches.
# ------------------------------------------------------------------
# Each service: (id, label, team). Team drives colour.
SERVICES: List[Tuple[str, str, str]] = [
    ("auth", "Auth", "Platform"),
    ("gateway", "API Gateway", "Platform"),
    ("web", "Web App", "Storefront"),
    ("mobile", "Mobile BFF", "Storefront"),
    ("catalog", "Catalog", "Storefront"),
    ("search", "Search", "Storefront"),
    ("cart", "Cart", "Checkout"),
    ("checkout", "Checkout", "Checkout"),
    ("payments", "Payments", "Checkout"),
    ("orders", "Orders", "Fulfilment"),
    ("shipping", "Shipping", "Fulfilment"),
    ("inventory", "Inventory", "Fulfilment"),
    ("notify", "Notifications", "Growth"),
    ("profile", "Profiles", "Growth"),
]

# Directed calls: (caller, callee). The graph is drawn undirected for the
# layout but the tooltip and degree use the full call list.
CALLS: List[Tuple[str, str]] = [
    ("gateway", "auth"),
    ("web", "gateway"),
    ("mobile", "gateway"),
    ("web", "catalog"),
    ("mobile", "catalog"),
    ("web", "search"),
    ("catalog", "search"),
    ("web", "cart"),
    ("mobile", "cart"),
    ("cart", "auth"),
    ("cart", "catalog"),
    ("checkout", "cart"),
    ("checkout", "auth"),
    ("checkout", "payments"),
    ("checkout", "orders"),
    ("payments", "auth"),
    ("orders", "auth"),
    ("orders", "inventory"),
    ("orders", "shipping"),
    ("orders", "notify"),
    ("shipping", "notify"),
    ("catalog", "inventory"),
    ("profile", "auth"),
    ("web", "profile"),
    ("mobile", "profile"),
    ("notify", "profile"),
    ("search", "catalog"),
]

# Team → brand hue. Built from the palette at render time so the accessibility
# level can remap the hues.
def _team_color(accessibility: str = "universal") -> Dict[str, str]:
    """Return the team → hex mapping at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level threaded into :func:`_style.load_palette`.
        ``"universal"`` (default) is the colour-vision-safe standard.

    Returns
    -------
    dict of str to str
        Mapping ``{team_name: hex}`` for each of the five service teams.
    """
    palette = load_palette(accessibility)
    return {
        "Platform": palette.get("Blue", "#007AFF"),
        "Storefront": palette.get("Teal", "#5AC8FA"),
        "Checkout": palette.get("Orange", "#FF9500"),
        "Fulfilment": palette.get("Green", "#34C759"),
        "Growth": palette.get("Purple", "#AF52DE"),
    }

def _team_slug(team: str) -> str:
    """Return a CSS-class-safe slug for a team name (lower-cased alphanumerics).

    Parameters
    ----------
    team : str
        A team name from :data:`SERVICES` (e.g. ``"Platform"``).

    Returns
    -------
    str
        The slug used in the ``team-<slug>`` node-circle class and in the
        OS-adaptive ``@media`` selectors (e.g. ``"platform"``).
    """
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in team).strip("-")


SEED = 20260725  # fixed so the committed SVG is byte-reproducible


# ------------------------------------------------------------------
# Force-directed layout (pure Python, no numpy)
# ------------------------------------------------------------------
def _layout(
    ids: List[str],
    edges: List[Tuple[str, str]],
    width: float,
    height: float,
    iterations: int = 520,
) -> Dict[str, Tuple[float, float]]:
    """Relax nodes into a force-directed layout inside a box.

    A tiny Fruchterman-Reingold-style simulation: every pair of nodes
    repels with an inverse-distance force, every edge acts as a spring
    pulling its endpoints toward an ideal length, and a temperature that
    cools each step caps how far any node may move, so the layout settles
    instead of oscillating. A weak pull toward the box centre keeps
    disconnected drift in check.

    Parameters
    ----------
    ids : list of str
        Node identifiers.
    edges : list of tuple of str
        Undirected endpoint pairs ``(a, b)``.
    width, height : float
        Size of the layout box the coordinates must fit inside.
    iterations : int, optional
        Number of relaxation steps (default 520 — enough for a graph this
        size to reach a clean, uncrossed-looking arrangement).

    Returns
    -------
    dict of str to tuple of float
        ``{node_id: (x, y)}`` in the box's own pixel coordinates
        (0..width, 0..height), before translation onto the canvas.
    """
    rng = random.Random(SEED)
    n = len(ids)
    # Ideal edge length: scale so n nodes fill the box comfortably.
    area = width * height
    k = 0.92 * math.sqrt(area / max(n, 1))

    # Seed positions on a jittered circle — a stable, symmetric start that
    # relaxes into a pleasing layout far more reliably than pure noise.
    pos: Dict[str, List[float]] = {}
    for i, nid in enumerate(ids):
        ang = 2.0 * math.pi * i / n
        r = 0.32 * min(width, height) * (0.6 + 0.4 * rng.random())
        pos[nid] = [
            width / 2 + r * math.cos(ang) + rng.uniform(-8, 8),
            height / 2 + r * math.sin(ang) + rng.uniform(-8, 8),
        ]

    temp = 0.14 * min(width, height)  # initial max displacement per step
    cool = temp / (iterations + 1)

    adj = set()
    for a, b in edges:
        adj.add((a, b))
        adj.add((b, a))

    for _ in range(iterations):
        disp: Dict[str, List[float]] = {nid: [0.0, 0.0] for nid in ids}

        # Repulsion between every ordered pair.
        for i in range(n):
            a = ids[i]
            for j in range(i + 1, n):
                b = ids[j]
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                dist = math.hypot(dx, dy) or 0.01
                force = (k * k) / dist
                ux, uy = dx / dist, dy / dist
                disp[a][0] += ux * force
                disp[a][1] += uy * force
                disp[b][0] -= ux * force
                disp[b][1] -= uy * force

        # Attraction along edges.
        for a, b in edges:
            dx = pos[a][0] - pos[b][0]
            dy = pos[a][1] - pos[b][1]
            dist = math.hypot(dx, dy) or 0.01
            force = (dist * dist) / k
            ux, uy = dx / dist, dy / dist
            disp[a][0] -= ux * force
            disp[a][1] -= uy * force
            disp[b][0] += ux * force
            disp[b][1] += uy * force

        # Gentle gravity toward the centre so the graph stays framed.
        for nid in ids:
            gx = (width / 2 - pos[nid][0]) * 0.012
            gy = (height / 2 - pos[nid][1]) * 0.012
            disp[nid][0] += gx
            disp[nid][1] += gy

        # Apply, capped by the current temperature, then keep in-box.
        for nid in ids:
            dx, dy = disp[nid]
            d = math.hypot(dx, dy) or 0.01
            step = min(d, temp)
            pos[nid][0] += (dx / d) * step
            pos[nid][1] += (dy / d) * step
            pos[nid][0] = min(width, max(0.0, pos[nid][0]))
            pos[nid][1] = min(height, max(0.0, pos[nid][1]))

        temp = max(temp - cool, 0.0)

    return {nid: (p[0], p[1]) for nid, p in pos.items()}


# ------------------------------------------------------------------
# Degree + radius helpers
# ------------------------------------------------------------------
def _degrees(ids: List[str], calls: List[Tuple[str, str]]) -> Dict[str, int]:
    """Return the in-degree (number of distinct callers) per service.

    In-degree is the "how many services depend on me" measure — the one
    that reveals single points of failure — so it drives node size.

    Parameters
    ----------
    ids : list of str
        Service identifiers.
    calls : list of tuple of str
        Directed ``(caller, callee)`` pairs.

    Returns
    -------
    dict of str to int
        ``{service_id: in_degree}``.
    """
    indeg: Dict[str, set] = {nid: set() for nid in ids}
    for caller, callee in calls:
        if callee in indeg:
            indeg[callee].add(caller)
    return {nid: len(callers) for nid, callers in indeg.items()}


def _radius(indeg: int, max_indeg: int) -> float:
    """Map an in-degree to a node radius in pixels.

    Uses a square-root scale so *area* (not radius) tracks in-degree — the
    perceptually honest encoding for a circle-size legend.

    Parameters
    ----------
    indeg : int
        This node's in-degree.
    max_indeg : int
        The largest in-degree in the graph (sets the top of the scale).

    Returns
    -------
    float
        Circle radius in pixels.
    """
    r_min, r_max = 15.0, 52.0
    if max_indeg <= 0:
        return r_min
    frac = math.sqrt(indeg / max_indeg)
    return r_min + (r_max - r_min) * frac


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full node-link network SVG document as a string.

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
    TEAM_COLOR = _team_color(accessibility)
    ids = [s[0] for s in SERVICES]
    label_of = {s[0]: s[1] for s in SERVICES}
    team_of = {s[0]: s[2] for s in SERVICES}

    # Undirected edge set for the layout (dedupe reversed duplicates).
    undirected: List[Tuple[str, str]] = []
    seen_e: set = set()
    for a, b in CALLS:
        key = (min(a, b), max(a, b))
        if key not in seen_e:
            seen_e.add(key)
            undirected.append((a, b))

    # Adjacency (undirected) for neighbour highlighting.
    neigh: Dict[str, set] = {nid: set() for nid in ids}
    for a, b in undirected:
        neigh[a].add(b)
        neigh[b].add(a)

    indeg = _degrees(ids, CALLS)
    max_indeg = max(indeg.values()) if indeg else 1

    box_w = WIDTH - 2 * PLOT_PAD
    box_h = HEIGHT - PLOT_TOP - PLOT_PAD - 72  # leave room for the legend row
    raw = _layout(ids, undirected, box_w, box_h)

    # Translate box coords onto the canvas.
    pos: Dict[str, Tuple[float, float]] = {
        nid: (PLOT_PAD + x, PLOT_TOP + y) for nid, (x, y) in raw.items()
    }

    title_txt = "Auth is a hidden single point of failure"
    subtitle_txt = (
        "Service-to-service calls in an online-store backend — illustrative data"
    )
    desc_txt = (
        "Force-directed node-link diagram of a microservice call graph. Each "
        "node is a service, coloured by owning team and sized by how many "
        "other services call it. Edges join services that call each other. "
        "The Auth service is the largest node: nearly every checkout, order "
        "and profile path calls it, so a stall in Auth cascades across the "
        "whole store. Hover or focus any service to highlight only the "
        "services it talks to."
    )

    parts: List[str] = []
    parts.append(svg_open(WIDTH, HEIGHT, "net-title", "net-desc", font_family=FONT))
    parts.append(f'<title id="net-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="net-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hover/focus a node fades everything but that node, its
    #     incident edges, and its direct neighbours. CSS cannot walk
    #     arbitrary graph adjacency, so we precompute each node's
    #     neighbourhood in Python and emit one :has() rule per node: when
    #     the graph *contains* a hovered/focused node ``n-<id>``, dim the
    #     whole graph, then restore the hovered node, its neighbour nodes,
    #     their labels, and every edge tagged ``i-<id>``. :has() is
    #     supported by Chrome (used for the audit shot) and every modern
    #     browser. ---
    css_lines: List[str] = [
        ".node,.edge,.nlabel{transition:opacity .2s ease}",
        ".node circle{transition:opacity .2s ease}",
    ]
    for nid in ids:
        # When the graph contains a hovered/focused node with id n-<nid>,
        # fade everything, then restore the hovered node, its labels, its
        # incident edges, and its neighbour nodes + labels.
        # NOTE: :is(:hover,:focus-within) keeps ``cond`` a *single* complex
        # selector — a bare comma here would split the descendant rules and
        # silently break the fade.
        cond = f'#graph:has(.node.n-{nid}:is(:hover,:focus-within))'
        # Fade all.
        css_lines.append(f"{cond} .edge{{opacity:.07}}")
        css_lines.append(f"{cond} .node{{opacity:.20}}")
        css_lines.append(f"{cond} .nlabel{{opacity:.08}}")
        # Restore the hovered node + its neighbours (and their labels).
        keep = [nid] + sorted(neigh[nid])
        node_sel = ",".join(f"{cond} .node.n-{k}" for k in keep)
        label_sel = ",".join(f"{cond} .nlabel.l-{k}" for k in keep)
        css_lines.append(f"{node_sel}{{opacity:1}}")
        css_lines.append(f"{label_sel}{{opacity:1}}")
        # Restore incident edges: every edge touching nid carries class i-<nid>.
        css_lines.append(f"{cond} .edge.i-{nid}{{opacity:.85}}")
    css_lines.append(".node:focus{outline:none}")
    css_lines.append(".node circle:focus{outline:none}")
    # OS-adaptive overrides (additive; the default render is byte-identical
    # because every rule below lives inside a media query). Under
    # prefers-contrast the five team hues deepen to their high-contrast
    # variants on the node fills. Under forced colours the whole graph drops to
    # system-palette line art — legitimate here because every node carries an
    # always-visible text label, so team identity survives without colour: the
    # nodes become CanvasText discs and the labels + edges follow the system
    # palette too.
    team_series = {
        f".team-{_team_slug(team)}": color for team, color in TEAM_COLOR.items()
    }
    css_lines.append(
        os_adaptive_style(
            team_series,
            role="fill",
            forced=True,
            extra_forced=".nlabel{fill:CanvasText;} .edge{stroke:CanvasText;}",
        )
    )
    # Additive OS dark mode: dark paper + light ink (default ink_map); the team
    # node hues are data, left alone. The node labels are ink text carried on a
    # white halo — under dark the text flips to off-white, so the halo must flip
    # to the dark paper (not stay white) or it would swallow the light text. The
    # resting edges dim to a mid-grey that reads as connectors on the dark ground.
    css_lines.append(
        os_dark_style(
            extra=(
                ".nlabel{stroke:#0B0B0C;}"
                ".edge{stroke:#4A4A50;}"
            )
        )
    )
    parts.append("<style>" + "".join(css_lines) + "</style>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="48" y="66" font-size="34" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="48" y="102" font-size="19" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    parts.append('<g id="graph">')

    # --- edges (drawn first, under the nodes) ---
    parts.append('<g id="edges">')
    for a, b in undirected:
        xa, ya = pos[a]
        xb, yb = pos[b]
        parts.append(
            f'<line class="edge i-{a} i-{b}" x1="{xa:.1f}" y1="{ya:.1f}" '
            f'x2="{xb:.1f}" y2="{yb:.1f}" stroke="{EDGE}" '
            f'stroke-width="2.2" stroke-linecap="round"/>'
        )
    parts.append("</g>")

    # --- node labels (own layer so hover fade is independent of nodes) ---
    parts.append('<g id="labels">')
    for nid in ids:
        x, y = pos[nid]
        r = _radius(indeg[nid], max_indeg)
        # Place the label just below the node; nudge the big hub label above
        # so it never collides with the dense centre.
        below = y + r + 22
        parts.append(
            f'<text class="nlabel l-{nid}" x="{x:.1f}" y="{below:.1f}" '
            f'text-anchor="middle" font-size="18" font-weight="600" '
            f'fill="{INK}" paint-order="stroke" stroke="{BG}" stroke-width="5" '
            f'stroke-linejoin="round">{escape(label_of[nid])}</text>'
        )
    parts.append("</g>")

    # --- nodes ---
    parts.append('<g id="nodes">')
    for nid in ids:
        x, y = pos[nid]
        r = _radius(indeg[nid], max_indeg)
        color = TEAM_COLOR[team_of[nid]]
        callers = sorted({c for c, e in CALLS if e == nid}, key=lambda c: label_of.get(c, c))
        callee_of = sorted({e for c, e in CALLS if c == nid}, key=lambda e: label_of.get(e, e))
        tip = (
            f"{label_of[nid]} · {team_of[nid]} team — "
            f"called by {indeg[nid]} service(s)"
        )
        if callers:
            tip += ": " + ", ".join(label_of.get(c, c) for c in callers)
        if callee_of:
            tip += f"; calls {', '.join(label_of.get(e, e) for e in callee_of)}"
        # The team slug rides on the <circle> itself (not the <g>) so a CSS
        # class rule can outrank the inline fill under the OS-adaptive media
        # queries below — a class on the group would not reach the circle's fill.
        team_slug = _team_slug(team_of[nid])
        parts.append(
            f'<g class="node n-{nid}" tabindex="0" role="img" '
            f'aria-label="{escape(tip)}">'
            f'<title>{escape(tip)}</title>'
            f'<circle class="team-{team_slug}" cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{r:.1f}" fill="{color}" stroke="{BG}" stroke-width="4"/>'
            f"</g>"
        )
    parts.append("</g>")

    parts.append("</g>")  # /graph

    # --- team legend (bottom-left, single row) ---
    ly = HEIGHT - 34
    lx = 48
    parts.append(
        f'<text x="{lx}" y="{ly - 30}" font-size="17" font-weight="600" '
        f'fill="{SUBINK}">Owning team</text>'
    )
    cursor = lx
    for team, color in TEAM_COLOR.items():
        parts.append(
            f'<circle cx="{cursor + 9:.1f}" cy="{ly - 6:.1f}" r="9" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{cursor + 26:.1f}" y="{ly:.1f}" font-size="18" '
            f'fill="{INK}">{escape(team)}</text>'
        )
        cursor += 30 + 11.0 * len(team) + 30

    # --- size + hover hint: sits under the subtitle so it never collides
    #     with the legend row at the bottom of a dense graph. ---
    parts.append(
        f'<text x="48" y="134" font-size="17" fill="{SUBINK}">'
        f'Node size ∝ how many services call it · hover or focus a service '
        f'to trace its calls</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the node-link network SVG to the skill's example asset folder.

    The ``--mode`` flag selects the interactivity mode of the emitted SVG
    (``self-contained`` / ``external`` / ``static``); see
    :func:`_interactive.fullscreen_control`.
    """
    render_cli(
        __file__, "network", build_svg, description="Render the node-link network SVG."
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
make_sfdp-largegraph — a few-hundred-node force-directed graph as SVG.

A force-directed (``sfdp``-style) layout is the standard way to *see* the
large-scale structure of a graph that is far too big to read node by node.
It answers "does this network break into communities, and how tightly are
they wired together?" at a glance: densely-connected groups relax into
visible blobs, the sparse edges between them become the bridges, and the
whole shape emerges without anyone hand-placing a single node.

This figure lays out a synthetic collaboration network of ~320 people in
six research groups (a planted stochastic-block model: many edges inside a
group, few across) and colours every node by its group. Vega-Lite has no
force simulation, so the layout is precomputed in **pure Python** — a
Barnes-Hut-free but sfdp-flavoured Fruchterman-Reingold relaxation with a
weak per-community gravity that separates the blobs — and the result is
emitted as a hand-authored SVG. A fixed seed makes the committed file
byte-reproducible.

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, a
start-anchored title plus a one-line takeaway subtitle, and a compact
community legend.

Interaction (no JavaScript): each community is a group whose nodes and
label share a class, and a pure-CSS ``:hover`` rule on the legend swatch
fades every other community so the reader can isolate one blob and its
outgoing bridges. Because the interaction is per-community (six rules, not
one per node) the SVG stays small. The graph is otherwise static, so
``animated`` is false and ``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/sfdp-largegraph.svg``.

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
from _style import forced_color_patterns, load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _render import render_cli  # noqa: E402
from _svg import svg_open  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1400
HEIGHT = 1120
PLOT_TOP = 150             # y where the graph area begins (below the title)
PLOT_PAD = 64              # inner margin around the layout box
LEGEND_H = 64              # reserved strip at the bottom for the legend

INK = "#1D1D1F"            # primary text
SUBINK = "#6E6E73"         # secondary text
BG = "#FFFFFF"
EDGE = "#D6D6DB"           # resting edge colour (very light neutral)

FONT = "Roboto, system-ui, sans-serif"

SEED = 20260725            # fixed so the committed SVG is byte-reproducible


# ------------------------------------------------------------------
# The story (illustrative but plausible): a research-collaboration
# network. A node is a researcher; an edge means "co-authored a paper".
# People cluster into six labs — dense inside a lab, sparse across — so
# the layout should surface six coloured communities with a handful of
# bridging collaborators between them. The takeaway: the network is
# strongly modular, but a thin web of cross-lab co-authorships keeps it
# a single connected component rather than six islands.
# ------------------------------------------------------------------
COMMUNITIES: List[Tuple[str, str]] = [
    # (label, palette-key)
    ("Vision", "Blue"),
    ("Language", "Purple"),
    ("Robotics", "Orange"),
    ("Theory", "Green"),
    ("Systems", "Teal"),
    ("Bio-AI", "Red"),
]

# Node budget per community (a few hundred total, uneven for realism).
SIZES: List[int] = [64, 58, 52, 46, 54, 44]  # 318 nodes

P_IN = 0.09      # edge probability inside a community
P_OUT = 0.0016   # edge probability across two communities


# ------------------------------------------------------------------
# Palette
# ------------------------------------------------------------------
PALETTE = load_palette()
_FALLBACK = {
    "Blue": "#007AFF", "Purple": "#AF52DE", "Orange": "#FF9500",
    "Green": "#34C759", "Teal": "#5AC8FA", "Red": "#FF3B30",
}


def _hex(key: str, accessibility: str = "universal") -> str:
    """Return the brand hex for a palette key, with a curated fallback.

    Parameters
    ----------
    key : str
        Palette base-colour name (``"Blue"``, ``"Purple"``, ...).
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`;
        ``"universal"`` (default) reuses the module-level ``PALETTE`` so the
        shipped figure is byte-identical.
    """
    palette = PALETTE if accessibility == "universal" else load_palette(accessibility)
    return palette.get(key, _FALLBACK[key])


def _lighten(hexv: str, t: float) -> str:
    """Blend ``hexv`` toward white by fraction ``t`` (0 = same, 1 = white)."""
    r, g, b = (int(hexv[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(c + (255 - c) * t) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


# ------------------------------------------------------------------
# Graph generation — a planted stochastic-block model
# ------------------------------------------------------------------
def build_graph() -> Tuple[List[int], List[int], List[Tuple[int, int]]]:
    """Sample a stochastic-block-model graph with planted communities.

    Every node is assigned to one of the six communities. A pair of nodes
    in the *same* community is joined with probability :data:`P_IN`; a pair
    in *different* communities with the much smaller :data:`P_OUT`. This is
    the canonical generator for "does my layout recover the communities?"
    demonstrations because the ground-truth grouping is known by
    construction.

    Returns
    -------
    tuple
        ``(comm, degree, edges)`` where ``comm[i]`` is node ``i``'s
        community index, ``degree[i]`` its edge count, and ``edges`` the
        list of undirected ``(a, b)`` index pairs (``a < b``).
    """
    rng = random.Random(SEED)
    comm: List[int] = []
    for ci, size in enumerate(SIZES):
        comm.extend([ci] * size)
    n = len(comm)

    edges: List[Tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            p = P_IN if comm[i] == comm[j] else P_OUT
            if rng.random() < p:
                edges.append((i, j))

    degree = [0] * n
    for a, b in edges:
        degree[a] += 1
        degree[b] += 1

    # Rescue isolated nodes: wire each to a random peer in its own
    # community so no dot floats detached (a layout artefact, not signal).
    by_comm: Dict[int, List[int]] = {}
    for idx, c in enumerate(comm):
        by_comm.setdefault(c, []).append(idx)
    for i in range(n):
        if degree[i] == 0:
            peers = [p for p in by_comm[comm[i]] if p != i]
            j = rng.choice(peers)
            a, b = (i, j) if i < j else (j, i)
            edges.append((a, b))
            degree[a] += 1
            degree[b] += 1

    return comm, degree, edges


# ------------------------------------------------------------------
# Force-directed layout (pure Python, no numpy)
# ------------------------------------------------------------------
def layout(
    n: int,
    comm: List[int],
    edges: List[Tuple[int, int]],
    width: float,
    height: float,
    iterations: int = 300,
) -> List[Tuple[float, float]]:
    """Relax the graph into an sfdp-flavoured force-directed layout.

    A Fruchterman-Reingold relaxation: every pair of nodes repels with an
    inverse-distance force, every edge acts as a spring pulling its
    endpoints toward an ideal length, and a temperature that cools each
    step caps the per-node displacement so the layout settles instead of
    oscillating. A gentle per-community gravity toward six anchor points
    (arranged on a ring) mimics the way ``sfdp``'s multilevel coarsening
    pulls each dense block apart, so the six communities separate cleanly
    at this node count without a full quad-tree.

    Parameters
    ----------
    n : int
        Number of nodes.
    comm : list of int
        Community index per node (drives the community gravity anchors).
    edges : list of tuple of int
        Undirected endpoint pairs ``(a, b)``.
    width, height : float
        Size of the layout box the coordinates must fit inside.
    iterations : int, optional
        Number of relaxation steps (default 300 — enough for a few-hundred
        node graph to reach clean, separated blobs).

    Returns
    -------
    list of tuple of float
        ``[(x, y), ...]`` in box pixel coordinates (0..width, 0..height),
        one per node, before translation onto the canvas.
    """
    rng = random.Random(SEED + 1)
    area = width * height
    k = 0.72 * math.sqrt(area / max(n, 1))  # ideal edge length

    # Community anchors on a ring — the multilevel "seed" that keeps the
    # blocks from piling on top of each other.
    n_comm = len(SIZES)
    cx, cy = width / 2, height / 2
    ring = 0.40 * min(width, height)
    anchors = [
        (
            cx + ring * math.cos(2 * math.pi * c / n_comm - math.pi / 2),
            cy + ring * math.sin(2 * math.pi * c / n_comm - math.pi / 2),
        )
        for c in range(n_comm)
    ]

    # Seed each node near its community anchor with a little jitter.
    pos: List[List[float]] = []
    for i in range(n):
        ax, ay = anchors[comm[i]]
        pos.append([
            ax + rng.uniform(-70, 70),
            ay + rng.uniform(-70, 70),
        ])

    temp = 0.10 * min(width, height)
    cool = temp / (iterations + 1)

    # Precompute a flat edge array for the attraction loop.
    for step in range(iterations):
        disp = [[0.0, 0.0] for _ in range(n)]

        # Repulsion between every ordered pair. O(n^2) is fine at n~320.
        for i in range(n):
            xi, yi = pos[i]
            di = disp[i]
            for j in range(i + 1, n):
                dx = xi - pos[j][0]
                dy = yi - pos[j][1]
                dist2 = dx * dx + dy * dy
                if dist2 < 0.01:
                    dist2 = 0.01
                    dx = rng.uniform(-0.1, 0.1)
                    dy = rng.uniform(-0.1, 0.1)
                dist = math.sqrt(dist2)
                force = (k * k) / dist
                ux, uy = dx / dist, dy / dist
                di[0] += ux * force
                di[1] += uy * force
                disp[j][0] -= ux * force
                disp[j][1] -= uy * force

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

        # Per-community gravity toward the anchor. It fades as the layout
        # cools but keeps a floor so adjacent blocks (adjacent on the ring)
        # never merge into one indistinct blob.
        g = 0.020 + 0.038 * (temp / (0.10 * min(width, height)))
        for i in range(n):
            ax, ay = anchors[comm[i]]
            disp[i][0] += (ax - pos[i][0]) * g
            disp[i][1] += (ay - pos[i][1]) * g

        # Apply, capped by the current temperature, then keep in-box.
        for i in range(n):
            dx, dy = disp[i]
            d = math.hypot(dx, dy) or 0.01
            s = min(d, temp)
            pos[i][0] += (dx / d) * s
            pos[i][1] += (dy / d) * s
            pos[i][0] = min(width, max(0.0, pos[i][0]))
            pos[i][1] = min(height, max(0.0, pos[i][1]))

        temp = max(temp - cool, 0.0)

    return [(p[0], p[1]) for p in pos]


# ------------------------------------------------------------------
# Fit helpers
# ------------------------------------------------------------------
def _fit(
    pts: List[Tuple[float, float]],
    box_w: float,
    box_h: float,
    pad: float,
) -> List[Tuple[float, float]]:
    """Rescale a point cloud to fill a padded box, preserving aspect ratio.

    Parameters
    ----------
    pts : list of tuple of float
        Raw layout coordinates.
    box_w, box_h : float
        Target box size.
    pad : float
        Inner margin kept clear on every side.

    Returns
    -------
    list of tuple of float
        Coordinates centred and scaled to fit the box.
    """
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span_x = maxx - minx or 1.0
    span_y = maxy - miny or 1.0
    avail_w = box_w - 2 * pad
    avail_h = box_h - 2 * pad
    scale = min(avail_w / span_x, avail_h / span_y)
    # Centre inside the box.
    off_x = pad + (avail_w - span_x * scale) / 2
    off_y = pad + (avail_h - span_y * scale) / 2
    return [
        (off_x + (x - minx) * scale, off_y + (y - miny) * scale)
        for x, y in pts
    ]


def _radius(degree: int, max_deg: int) -> float:
    """Map a node degree to a small radius (sqrt scale for honest area)."""
    r_min, r_max = 5.0, 14.0
    if max_deg <= 0:
        return r_min
    frac = math.sqrt(degree / max_deg)
    return r_min + (r_max - r_min) * frac


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full force-directed large-graph SVG document.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Controls
        whether the emitted SVG carries its own fullscreen button; the raster
        output is unaffected. Defaults to ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`
        (``"universal"``, ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` or ``"tritanopia"``). The default
        ``"universal"`` is the identity, so the shipped figure is unchanged.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    comm, degree, edges = build_graph()
    n = len(comm)
    max_deg = max(degree) if degree else 1

    box_w = WIDTH - 2 * PLOT_PAD
    box_h = HEIGHT - PLOT_TOP - LEGEND_H
    raw = layout(n, comm, edges, box_w, box_h)
    fitted = _fit(raw, box_w, box_h, pad=18)
    pos = [(PLOT_PAD + x, PLOT_TOP + y) for x, y in fitted]

    labels = [c[0] for c in COMMUNITIES]
    colors = [_hex(c[1], accessibility) for c in COMMUNITIES]
    light = [_lighten(c, 0.55) for c in colors]   # pale fill so overlapping same-colour nodes read as rings

    # Cross-community edge count for the subtitle takeaway.
    cross = sum(1 for a, b in edges if comm[a] != comm[b])

    title_txt = "Six labs, one connected research network"
    subtitle_txt = (
        f"{n} researchers, {len(edges)} co-authorships — "
        "illustrative data"
    )
    desc_txt = (
        "Force-directed (sfdp-style) layout of a synthetic research "
        f"collaboration network: {n} researchers grouped into six labs, "
        "coloured by lab. Nodes are people, edges are co-authored papers, "
        "and node size grows with a person's number of collaborators. The "
        "layout was precomputed in Python from a planted stochastic-block "
        "model — dense inside each lab, sparse across — so the six "
        "communities relax into six visible clusters. A thin web of "
        f"{cross} cross-lab co-authorships bridges the clusters, keeping "
        "the whole network a single connected component rather than six "
        "islands. Hover a legend swatch to isolate one lab and its bridges."
    )

    parts: List[str] = []
    parts.append(svg_open(WIDTH, HEIGHT, "sfdp-title", "sfdp-desc", font_family=FONT))
    parts.append(f'<title id="sfdp-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="sfdp-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hovering / focusing a legend swatch (class sw-<c>) fades
    #     every community except that one — six rules total, so the SVG
    #     stays light. :has() is supported by Chrome (used for the audit
    #     shot) and every modern browser. ---
    css: List[str] = [
        ".comm,.cedge,.clabel{transition:opacity .18s ease}",
        ".legend g{cursor:pointer}",
    ]
    for c in range(len(COMMUNITIES)):
        cond = f'#fig:has(.legend .sw-{c}:is(:hover,:focus))'
        css.append(f"{cond} .comm{{opacity:.10}}")
        css.append(f"{cond} .cedge{{opacity:.05}}")
        css.append(f"{cond} .clabel{{opacity:.12}}")
        # restore the hovered community's nodes, its label, and every edge
        # that touches it (edges are classed by both endpoint communities).
        css.append(f"{cond} .comm.c-{c}{{opacity:1}}")
        css.append(f"{cond} .clabel.cl-{c}{{opacity:1}}")
        css.append(f"{cond} .cedge.e-{c}{{opacity:.65}}")
    css.append(".legend g:focus{outline:none}")
    # OS-adaptive overrides (additive; every rule lives inside an @media block,
    # so the default render is byte-for-byte unchanged). Each lab already carries
    # a stable class: nodes ``.c-<c>``, and (added here) the solid legend / label
    # dots ``.sfdp-dot-<c>``. Under prefers-contrast the six lab hues deepen
    # together to their high-contrast spacing — on the node OUTLINE stroke (the
    # pale node fill is left alone so overlapping same-lab dots still read as
    # rings) and on the solid dots' fill. Under forced-colors (Windows High
    # Contrast) the ~4-colour system palette cannot preserve six lab hues, so each
    # lab's solid dots (the on-blob pills + the legend swatches) are handed a
    # distinct Canvas/CanvasText PATTERN via forced_color_patterns, so the six
    # communities stay identifiable from their pill/legend key when colour is
    # stripped. The ~318 tiny node discs are left as system line art (patterning
    # marks that small would only read as noise); the labelled pills carry the
    # community identity.
    node_series = {f".c-{c}": colors[c] for c in range(len(COMMUNITIES))}
    dot_series = {f".sfdp-dot-{c}": colors[c] for c in range(len(COMMUNITIES))}
    fcp_defs, fcp_style = forced_color_patterns(list(dot_series), prefix="sfdp-fcp")
    contrast_block = (
        os_adaptive_style(node_series, role="stroke")
        + os_adaptive_style(dot_series, role="fill")
        + fcp_style
    )
    # Dark mode: invert paper + inks (the white community pills flip to a dark
    # surface with light text, staying self-consistent), and dim the very light
    # resting edges (#D6D6DB) to a dark-surface grey so the web reads without
    # glare. Node ring / dot data hues are left alone.
    dark_block = os_dark_style(extra='[stroke="#D6D6DB"]{stroke:#3A3A3C;}')
    parts.append("<style>" + "".join(css) + contrast_block + dark_block + "</style>")
    parts.append(f"<defs>{fcp_defs}</defs>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle ---
    parts.append(
        f'<text x="52" y="66" font-size="38" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="52" y="102" font-size="21" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )
    parts.append(
        f'<text x="52" y="128" font-size="16" fill="{SUBINK}">'
        f'Node size grows with number of collaborators · hover a lab in '
        f'the legend to isolate it</text>'
    )

    parts.append('<g id="fig">')

    # --- edges first, under the nodes. Class by the two endpoint
    #     communities so the hover rule can restore a lab's edges. ---
    parts.append('<g id="edges">')
    for a, b in edges:
        xa, ya = pos[a]
        xb, yb = pos[b]
        ca, cb = comm[a], comm[b]
        cls = f"cedge e-{ca}" + ("" if ca == cb else f" e-{cb}")
        # Cross-lab bridges get a touch more presence than intra-lab edges.
        w = 0.9 if ca == cb else 1.1
        parts.append(
            f'<line class="{cls}" x1="{xa:.1f}" y1="{ya:.1f}" '
            f'x2="{xb:.1f}" y2="{yb:.1f}" stroke="{EDGE}" '
            f'stroke-width="{w}"/>'
        )
    parts.append("</g>")

    # --- nodes, grouped per community so the hover class is shared. ---
    parts.append('<g id="nodes">')
    for i in range(n):
        x, y = pos[i]
        r = _radius(degree[i], max_deg)
        parts.append(
            f'<circle class="comm c-{comm[i]}" cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{r:.1f}" fill="{light[comm[i]]}" fill-opacity="0.85" '
            f'stroke="{colors[comm[i]]}" stroke-width="1.6"/>'
        )
    parts.append("</g>")

    # --- community labels as solid white "pills" pushed to each blob's
    #     outer edge (away from the figure centre) so they sit on clear
    #     canvas rather than buried in dots. No stroke halo — a filled
    #     rounded rect behind ink-and-colour text reads cleanly and keeps
    #     the lab colour visible via a small leading dot. ---
    fig_cx = PLOT_PAD + box_w / 2
    fig_cy = PLOT_TOP + box_h / 2
    parts.append('<g id="clabels">')
    for c in range(len(COMMUNITIES)):
        members = [i for i in range(n) if comm[i] == c]
        mx = sum(pos[i][0] for i in members) / len(members)
        my = sum(pos[i][1] for i in members) / len(members)
        # Blob radius (distance to farthest member) so we can push the
        # label just past the cluster's outer rim.
        rim = max(math.hypot(pos[i][0] - mx, pos[i][1] - my) for i in members)
        dx, dy = mx - fig_cx, my - fig_cy
        dnorm = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dnorm, dy / dnorm
        lxp = mx + ux * (rim * 0.72)
        lyp = my + uy * (rim * 0.72)
        label = escape(labels[c])
        pill_w = 30 + 16.2 * len(labels[c])
        pill_h = 46
        # Keep the pill inside the canvas.
        lxp = min(WIDTH - PLOT_PAD - pill_w / 2, max(PLOT_PAD + pill_w / 2, lxp))
        lyp = min(HEIGHT - LEGEND_H - pill_h / 2, max(PLOT_TOP + pill_h / 2, lyp))
        parts.append(
            f'<g class="clabel cl-{c}">'
            f'<rect x="{lxp - pill_w / 2:.1f}" y="{lyp - pill_h / 2:.1f}" '
            f'width="{pill_w:.1f}" height="{pill_h}" rx="{pill_h / 2:.1f}" '
            f'fill="{BG}" fill-opacity="0.92"/>'
            f'<circle class="sfdp-dot-{c}" cx="{lxp - pill_w / 2 + 20:.1f}" '
            f'cy="{lyp:.1f}" r="9" fill="{colors[c]}"/>'
            f'<text x="{lxp - pill_w / 2 + 37:.1f}" y="{lyp + 9:.1f}" '
            f'font-size="26" font-weight="700" fill="{INK}">{label}</text>'
            f'</g>'
        )
    parts.append("</g>")

    # --- legend (bottom row): one focusable swatch per lab, wired to the
    #     hover-isolate CSS above. Kept INSIDE #fig so the :has() scope
    #     (which lives on #fig) can see the hovered swatch. ---
    ly = HEIGHT - 26
    lx = 52
    parts.append('<g class="legend">')
    cursor: float = lx
    for c, (label, _key) in enumerate(COMMUNITIES):
        count = SIZES[c]
        seg = f"{label} ({count})"
        parts.append(
            f'<g class="sw-{c}" tabindex="0" role="button" '
            f'aria-label="Highlight the {escape(label)} lab">'
            f'<title>Highlight the {escape(label)} lab '
            f'({count} researchers)</title>'
            f'<circle class="sfdp-dot-{c}" cx="{cursor + 9:.1f}" cy="{ly - 6:.1f}" r="9" '
            f'fill="{colors[c]}"/>'
            f'<text x="{cursor + 26:.1f}" y="{ly:.1f}" font-size="18" '
            f'fill="{INK}">{escape(seg)}</text>'
            f'</g>'
        )
        cursor += 36 + 10.4 * len(seg) + 28
    parts.append("</g>")  # /legend

    parts.append("</g>")  # /fig

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the force-directed large-graph SVG to the example asset folder.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "sfdp-largegraph",
        build_svg,
        description="Write the house-style force-directed large-graph SVG example.",
    )


if __name__ == "__main__":
    main()

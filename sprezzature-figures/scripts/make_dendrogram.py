#!/usr/bin/env python3
"""
make_dendrogram — publication-quality dendrogram as a hand-authored SVG.

A dendrogram is the tree that hierarchical (agglomerative) clustering
produces: leaves are the original observations, and each internal node
is a *merge* of two sub-clusters drawn at the height (dissimilarity) at
which they joined. Reading the tree top-down, the taller a merge sits,
the more different the two branches it unites — so a horizontal "cut"
at any height yields a flat clustering, and the vertical gap below a
cut tells you how stable that grouping is.

Vega-Lite has no native dendrogram mark (the merge geometry is a
recursive layout, not a data-to-mark mapping), so this figure is built
as an SVG string by hand rather than through ``vl_convert``. The layout
is the classic *rectangular* (elbow) dendrogram:

* **Leaves** are placed at evenly spaced x-positions along the bottom.
* Each **merge** is an inverted-U elbow: two vertical risers climb from
  the children up to the merge height, joined by a horizontal bar. The
  merge's own x-position is the midpoint of its two children.
* A **merge-height axis** runs up the left edge, so every horizontal
  bar can be read off as a dissimilarity value.

The tree is coloured by the *flat clustering* obtained by cutting at a
chosen height: every branch below the cut takes its cluster's hue, and
the spine above the cut is drawn in neutral ink. A dashed rule marks
the cut so the reader sees exactly where the colours were assigned.

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, rounded
corners, a start-anchored title plus a one-line takeaway subtitle.

Interaction (no JavaScript): every merge elbow and every leaf carries a
native ``<title>`` tooltip (merge height / cluster membership), and a
CSS ``:hover`` / ``:focus`` rule lifts the hovered cluster's branches
to full strength while dimming the rest — the "isolate a cluster"
affordance that suits this capability. The figure is otherwise static
(a dendrogram does not benefit from animation), so ``animated`` is
false and ``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/dendrogram.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import leveled_colors, load_palette, os_dark_style  # noqa: E402
from _render import render_cli  # noqa: E402
from _svg import svg_open  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1480
HEIGHT = 900
MARGIN_LEFT = 118        # room for the merge-height axis + its title
MARGIN_RIGHT = 268       # room for the cluster legend on the right
MARGIN_TOP = 168         # room for title + subtitle
MARGIN_BOTTOM = 210      # room for the leaf labels + baseline breathing space

INK = "#1D1D1F"          # primary text / cluster labels
SUBINK = "#6E6E73"       # secondary text
# The tree "spine" above the cut is neutral, but a full-ink black cages the
# figure and fights the coloured clusters; a soft grey lets the colour lead.
SPINE = "#A6A6AE"        # neutral merge links above the cut
GRIDLINE = "#ECECF0"     # hairline neutral
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"


# ------------------------------------------------------------------
# The story (illustrative but plausible): a grocery retailer clusters
# its private-label product lines by how similarly households buy them
# over a quarter (correlation-based distance on the basket matrix).
# Agglomerative clustering with average linkage produces the merges
# below. The takeaway: three natural shelves emerge — a fresh/health
# cluster, a household-staples cluster, and a treat/indulgence cluster —
# and "Frozen ready-meals" is the odd one out that joins last.
# ------------------------------------------------------------------
# Leaf labels, left-to-right in the order the clustering lays them out.
LEAVES: List[str] = [
    "Fresh produce",
    "Yoghurt & dairy",
    "Breakfast cereal",
    "Cleaning supplies",
    "Paper goods",
    "Pet food",
    "Chocolate & sweets",
    "Soft drinks",
    "Crisps & snacks",
    "Frozen ready-meals",
]

# The merge sequence, as (left child, right child, merge height). A
# child is either a leaf label (str) or an internal-node id "m{i}"
# referring to an earlier merge. Heights are the linkage dissimilarity
# at which the two branches joined (0 = identical basket behaviour,
# 1 = uncorrelated). This is a valid ultrametric merge tree.
MERGES: List[Tuple[str, str, float]] = [
    # --- fresh / health shelf ---
    ("Fresh produce", "Yoghurt & dairy", 0.18),          # m0
    ("m0", "Breakfast cereal", 0.31),                    # m1
    # --- household staples shelf ---
    ("Cleaning supplies", "Paper goods", 0.15),          # m2
    ("m2", "Pet food", 0.34),                            # m3
    # --- treat / indulgence shelf ---
    ("Chocolate & sweets", "Soft drinks", 0.21),         # m4
    ("m4", "Crisps & snacks", 0.29),                     # m5
    # --- inter-shelf merges (well above the cut) ---
    ("m1", "m3", 0.58),                                  # m6  fresh + staples
    ("m6", "m5", 0.74),                                  # m7  + treats
    ("m7", "Frozen ready-meals", 0.92),                  # m8  odd one out, root
]

# Cut the tree at this height to obtain the flat clustering that colours
# the branches. Chosen to sit in the tall gap between the intra-shelf
# merges (<= 0.34) and the inter-shelf merges (>= 0.58).
CUT_HEIGHT = 0.46

# Flat-cluster hues, assigned left-to-right by the leftmost leaf of each
# cluster below the cut.
def _cluster_colors(accessibility: str = "universal") -> List[str]:
    """Return the four flat-cluster hues at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`.

    Returns
    -------
    list of str
        Four hex strings, one per flat cluster (left-to-right by leftmost leaf).
    """
    palette = load_palette(accessibility)
    return [
        palette.get("Green", "#34C759"),    # fresh / health
        palette.get("Blue", "#007AFF"),     # household staples
        palette.get("Purple", "#AF52DE"),   # treats / indulgence
        palette.get("Orange", "#FF9500"),   # singleton (frozen ready-meals)
    ]


CLUSTER_COLORS: List[str] = _cluster_colors()
# Human names for the flat clusters, assigned left-to-right by the
# leftmost leaf of each cluster below the cut.
CLUSTER_NAMES: List[str] = [
    "Fresh & health",
    "Household staples",
    "Treats",
    "Unclustered",
]


# ------------------------------------------------------------------
# Tree model
# ------------------------------------------------------------------
def _build_nodes() -> Dict[str, dict]:
    """Materialise every tree node (leaves + merges) with its children.

    Returns
    -------
    dict
        ``{node_id: {"kind", "label", "height", "children", "leaves"}}``
        where ``kind`` is ``"leaf"`` or ``"merge"``, ``height`` is the
        merge dissimilarity (0 for leaves), ``children`` is a list of
        child node ids (empty for leaves), and ``leaves`` is the ordered
        list of leaf labels beneath the node.
    """
    nodes: Dict[str, dict] = {}
    for label in LEAVES:
        nodes[label] = {
            "kind": "leaf",
            "label": label,
            "height": 0.0,
            "children": [],
            "leaves": [label],
        }
    for i, (left, right, height) in enumerate(MERGES):
        node_id = f"m{i}"
        leaves = nodes[left]["leaves"] + nodes[right]["leaves"]
        nodes[node_id] = {
            "kind": "merge",
            "label": node_id,
            "height": height,
            "children": [left, right],
            "leaves": leaves,
        }
    return nodes


def _root_id() -> str:
    """Return the id of the last (top-most) merge — the tree root."""
    return f"m{len(MERGES) - 1}"


def _flat_clusters() -> Dict[str, int]:
    """Assign each leaf to a flat cluster by cutting at :data:`CUT_HEIGHT`.

    Walks the tree from the root; the first node encountered whose height
    is at or below the cut becomes a cluster root, and all its leaves
    share that cluster index. Clusters are numbered left-to-right by the
    x-order of their leftmost leaf, so colours read sensibly across the
    figure.

    Returns
    -------
    dict
        ``{leaf_label: cluster_index}``.
    """
    nodes = _build_nodes()
    cluster_roots: List[str] = []

    def descend(node_id: str) -> None:
        node = nodes[node_id]
        if node["kind"] == "leaf" or node["height"] <= CUT_HEIGHT:
            cluster_roots.append(node_id)
            return
        for child in node["children"]:
            descend(child)

    descend(_root_id())

    # Order cluster roots by the x-position (leaf index) of their first leaf.
    leaf_index = {label: i for i, label in enumerate(LEAVES)}
    cluster_roots.sort(key=lambda nid: leaf_index[nodes[nid]["leaves"][0]])

    membership: Dict[str, int] = {}
    for idx, root in enumerate(cluster_roots):
        for leaf in nodes[root]["leaves"]:
            membership[leaf] = idx
    return membership


# ------------------------------------------------------------------
# Layout maths
# ------------------------------------------------------------------
def _y_for_height(height: float, max_height: float) -> float:
    """Map a merge height to a y pixel (0 at the baseline, tall = up)."""
    plot_top = MARGIN_TOP
    plot_bottom = HEIGHT - MARGIN_BOTTOM
    # Give a little headroom above the tallest merge.
    top_value = max_height * 1.12
    frac = height / top_value if top_value else 0.0
    return plot_bottom - frac * (plot_bottom - plot_top)


def _compute_geometry() -> Tuple[Dict[str, dict], float]:
    """Place every node in SVG pixel space.

    Returns
    -------
    geometry : dict
        ``{node_id: {"x", "y"}}`` — the anchor point of each node. For a
        leaf, ``y`` is the baseline; for a merge, ``y`` is the merge
        height and ``x`` is the midpoint of its two children.
    max_height : float
        The root merge height (used to scale the axis).
    """
    nodes = _build_nodes()
    plot_left = MARGIN_LEFT
    plot_right = WIDTH - MARGIN_RIGHT
    baseline = HEIGHT - MARGIN_BOTTOM

    max_height = nodes[_root_id()]["height"]

    # Evenly space leaves along the plot width.
    n = len(LEAVES)
    leaf_x = {
        label: plot_left + (i + 0.5) * (plot_right - plot_left) / n
        for i, label in enumerate(LEAVES)
    }

    geometry: Dict[str, dict] = {}
    for label in LEAVES:
        geometry[label] = {"x": leaf_x[label], "y": baseline}

    # Merges in creation order: children always resolved first.
    for i, (left, right, height) in enumerate(MERGES):
        node_id = f"m{i}"
        cx = (geometry[left]["x"] + geometry[right]["x"]) / 2.0
        geometry[node_id] = {"x": cx, "y": _y_for_height(height, max_height)}

    return geometry, max_height


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def _fmt(v: float) -> str:
    """Format a coordinate compactly."""
    return f"{v:.1f}"


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full dendrogram SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"`` / ``"external"`` / ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level passed to :func:`_style.load_palette`
        (``"universal"`` default, plus ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` and ``"tritanopia"``). Wired
        through the ``--accessibility`` CLI flag by :func:`_render.render_cli`.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    cluster_colors = _cluster_colors(accessibility)
    nodes = _build_nodes()
    geometry, max_height = _compute_geometry()
    membership = _flat_clusters()

    plot_left = MARGIN_LEFT
    plot_right = WIDTH - MARGIN_RIGHT
    baseline = HEIGHT - MARGIN_BOTTOM
    y_cut = _y_for_height(CUT_HEIGHT, max_height)

    parts: List[str] = []

    # --- header: accessible role + title + description ---
    title_txt = "Three natural shelves emerge from how households shop"
    subtitle_txt = (
        "Private-label lines clustered by co-purchase similarity · illustrative data"
    )
    desc_txt = (
        "Rectangular dendrogram from average-linkage hierarchical clustering of "
        "ten grocery product lines. The vertical axis is the merge dissimilarity "
        "(0 = identical basket behaviour, 1 = uncorrelated). Cutting the tree at "
        "0.46 yields three clusters: fresh and health, household staples, and "
        "treats. Frozen ready-meals stays unclustered, joining only at the "
        "root. Each cluster is set apart by its branch grouping, not by colour "
        "alone, so it reads in greyscale and for colour-blind viewers."
    )
    parts.append(svg_open(WIDTH, HEIGHT, "dendro-title", "dendro-desc", font_family=FONT))
    parts.append(f'<title id="dendro-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="dendro-desc">{escape(desc_txt)}</desc>')

    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule below lives inside a media query). Under
    # prefers-contrast each flat cluster deepens to its high-contrast hue: the
    # coloured branch elbows (stroke) plus the leaf dots and legend swatches
    # (fill, tag-qualified so the white ring on the dots survives). The neutral
    # grey spine above the cut is left alone. forced-colors is left to the
    # browser default: the clusters already read by branch GROUPING plus the
    # leaf labels, legend names and the dashed cut rule, so no colour-only
    # fallback is needed, and a four-hue tree cannot survive the ~4-colour
    # system palette.
    clu_hc = leveled_colors(
        {f"c{i}": c for i, c in enumerate(cluster_colors)}, "high-contrast"
    )
    contrast_rows = "".join(
        f"path.dg-c{i}{{stroke:{clu_hc[f'c{i}']};}}"
        f"circle.dg-c{i},rect.dg-c{i}{{fill:{clu_hc[f'c{i}']};}}"
        for i in range(len(cluster_colors))
    )
    adaptive = "@media (prefers-contrast: more){" + contrast_rows + "}"
    # --- CSS: hover/focus a cluster group, dim the rest ---
    parts.append(
        "<style>"
        ".branch{transition:opacity .15s ease}"
        # Hovering the tree fades every coloured branch, then the hovered/
        # focused cluster group is brought back to full strength.
        "#tree:hover .cluster .branch{opacity:.2}"
        "#tree .cluster:hover .branch,#tree .cluster:focus-within .branch{opacity:1}"
        ".leaf-hit:focus{outline:none}"
        + adaptive
        # Additive dark mode: flip paper + ink and darken the hairline gridlines
        # (a stroke the ink map misses). Cluster branch hues read on dark.
        + os_dark_style(extra='[stroke="%s"]{stroke:#2C2C2E;}' % GRIDLINE)
        + "</style>"
    )

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    title_x = MARGIN_LEFT - 58
    parts.append(
        f'<text x="{title_x}" y="54" font-size="30" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="{title_x}" y="88" font-size="19" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    # --- merge-height axis (left edge) with gridlines + ticks ---
    axis_x = plot_left - 18
    tick_values = [0.0, 0.2, 0.4, 0.6, 0.8]
    parts.append('<g id="axis">')
    # Vertical axis domain line.
    parts.append(
        f'<line x1="{axis_x:.1f}" y1="{_y_for_height(0, max_height):.1f}" '
        f'x2="{axis_x:.1f}" y2="{MARGIN_TOP - 10:.1f}" '
        f'stroke="{INK}" stroke-width="1.4"/>'
    )
    for tv in tick_values:
        gy = _y_for_height(tv, max_height)
        # Hairline gridline across the plot.
        parts.append(
            f'<line x1="{plot_left:.1f}" y1="{gy:.1f}" x2="{plot_right + 12:.1f}" '
            f'y2="{gy:.1f}" stroke="{GRIDLINE}" stroke-width="1.4"/>'
        )
        # Tick label (mono, like the house axis labels).
        parts.append(
            f'<text x="{axis_x - 10:.1f}" y="{gy + 5:.1f}" text-anchor="end" '
            f'font-family="{FONT_MONO}" font-size="15" fill="{SUBINK}">'
            f'{tv:.1f}</text>'
        )
    # Axis title, rotated up the left edge.
    axis_title_y = (MARGIN_TOP + baseline) / 2.0
    axis_title_x = 34
    parts.append(
        f'<text x="{axis_title_x}" y="{axis_title_y:.1f}" font-size="18" font-weight="600" '
        f'fill="{SUBINK}" text-anchor="middle" '
        f'transform="rotate(-90 {axis_title_x} {axis_title_y:.1f})">'
        f'Merge dissimilarity</text>'
    )
    parts.append("</g>")

    # --- the cut rule (dashed) marking where clusters were assigned ---
    parts.append(
        f'<line x1="{plot_left - 6:.1f}" y1="{y_cut:.1f}" '
        f'x2="{plot_right + 12:.1f}" y2="{y_cut:.1f}" '
        f'stroke="{INK}" stroke-width="1.8" stroke-dasharray="7 5" '
        f'opacity="0.55"/>'
    )
    parts.append(
        f'<text x="{plot_right + 12:.1f}" y="{y_cut - 12:.1f}" text-anchor="end" '
        f'font-size="16" font-style="italic" fill="{SUBINK}">'
        f'cut @ {CUT_HEIGHT:.2f} → 3 clusters</text>'
    )

    # ------------------------------------------------------------------
    # Draw the tree. Every internal merge is an inverted-U elbow: two
    # vertical risers from the children up to the merge height, joined by
    # a horizontal bar. A branch's colour is its cluster colour when the
    # whole branch sits below the cut; the spine above the cut is neutral.
    # We group elbows by the cluster they belong to so a CSS :hover can
    # isolate one cluster.
    # ------------------------------------------------------------------
    def branch_cluster(node_id: str) -> Optional[int]:
        """Return the flat-cluster index a node belongs to, or None if it
        straddles the cut (i.e. sits above it and mixes clusters)."""
        node = nodes[node_id]
        if node["height"] > CUT_HEIGHT:
            return None
        # Below the cut → all leaves share one cluster.
        return membership[node["leaves"][0]]

    # Bucket the SVG snippets: one list per cluster + a neutral spine list.
    cluster_snippets: Dict[int, List[str]] = {i: [] for i in range(len(CLUSTER_NAMES))}
    spine_snippets: List[str] = []

    for i, (left, right, height) in enumerate(MERGES):
        node_id = f"m{i}"
        gm = geometry[node_id]
        gl = geometry[left]
        gr = geometry[right]
        my = gm["y"]

        cl = branch_cluster(node_id)
        if cl is None:
            # Neutral spine above the cut: thin + soft grey so the coloured
            # clusters read as the subject and the upper tree recedes.
            color = SPINE
            width = 2.6
            bucket = spine_snippets
        else:
            color = cluster_colors[cl]
            width = 4.2
            bucket = cluster_snippets[cl]

        # Inverted-U elbow path: up from left child, across, down to right.
        elbow = (
            f"M{_fmt(gl['x'])},{_fmt(gl['y'])} "
            f"L{_fmt(gl['x'])},{_fmt(my)} "
            f"L{_fmt(gr['x'])},{_fmt(my)} "
            f"L{_fmt(gr['x'])},{_fmt(gr['y'])}"
        )
        tip = f"Merge at dissimilarity {height:.2f} — joins {len(nodes[node_id]['leaves'])} lines"
        branch_cls = "branch" if cl is None else f"branch dg-c{cl}"
        bucket.append(
            f'<path class="{branch_cls}" d="{elbow}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round"><title>{escape(tip)}</title></path>'
        )

    # Emit: neutral spine first (so coloured clusters sit visually on top),
    # then each cluster group (hover-isolatable), then leaf hit-targets.
    parts.append('<g id="tree">')
    parts.append('<g id="spine">')
    parts.extend(spine_snippets)
    parts.append("</g>")
    for cl in range(len(CLUSTER_NAMES)):
        snippets = cluster_snippets[cl]
        if not snippets:
            continue
        cname = CLUSTER_NAMES[cl]
        # tabindex on the group makes the cluster keyboard-focusable so
        # :focus-within lights it up without any script.
        parts.append(
            f'<g class="cluster" tabindex="0" role="img" '
            f'aria-label="{escape(cname)} cluster">'
        )
        parts.extend(snippets)
        parts.append("</g>")
    parts.append("</g>")

    # --- leaf labels (rotated) + coloured leaf dots + hit targets ---
    parts.append('<g id="leaves">')
    for label in LEAVES:
        g = geometry[label]
        cl = membership[label]
        dot = cluster_colors[cl]
        # Coloured marker at the leaf base, ringed in white so it sits
        # cleanly on top of its riser without a muddy overlap.
        parts.append(
            f'<circle class="dg-c{cl}" cx="{_fmt(g["x"])}" cy="{_fmt(baseline)}" '
            f'r="6" '
            f'fill="{dot}" stroke="{BG}" stroke-width="2"><title>'
            f'{escape(label)} — {escape(CLUSTER_NAMES[cl])}</title></circle>'
        )
        # Rotated label below the baseline. -32° keeps the words legible
        # while the extra bottom margin gives even the longest line room.
        ly = baseline + 26
        parts.append(
            f'<text class="leaf-hit" tabindex="0" x="{_fmt(g["x"])}" y="{_fmt(ly)}" '
            f'font-size="18" fill="{INK}" text-anchor="end" '
            f'transform="rotate(-32 {_fmt(g["x"])} {_fmt(ly)})">'
            f'{escape(label)}<title>{escape(label)} — {escape(CLUSTER_NAMES[cl])}'
            f'</title></text>'
        )
    parts.append("</g>")

    # --- cluster legend on the right ---
    legend_x = plot_right + 44
    legend_y = MARGIN_TOP + 10
    parts.append('<g id="legend">')
    parts.append(
        f'<text x="{legend_x:.1f}" y="{legend_y:.1f}" font-size="15" '
        f'font-weight="700" letter-spacing="0.7" fill="{SUBINK}">CLUSTERS</text>'
    )
    ry = legend_y + 34
    for cl, cname in enumerate(CLUSTER_NAMES):
        size = sum(1 for lab in LEAVES if membership[lab] == cl)
        if size == 1:
            # A singleton is not a real cluster — draw it as the leaf-dot
            # marker (a ringed circle) so the legend matches the mark and
            # reads as "outlier", not "coloured branch".
            parts.append(
                f'<circle class="dg-c{cl}" cx="{legend_x + 9:.1f}" cy="{ry - 5:.1f}" '
                f'r="8" '
                f'fill="{cluster_colors[cl]}" stroke="{BG}" stroke-width="2.5"/>'
            )
        else:
            parts.append(
                f'<rect class="dg-c{cl}" x="{legend_x:.1f}" y="{ry - 14:.1f}" '
                f'width="18" height="18" '
                f'rx="5" fill="{cluster_colors[cl]}"/>'
            )
        parts.append(
            f'<text x="{legend_x + 28:.1f}" y="{ry:.1f}" font-size="17" '
            f'fill="{INK}">{escape(cname)}</text>'
        )
        parts.append(
            f'<text x="{legend_x + 28:.1f}" y="{ry + 20:.1f}" '
            f'font-family="{FONT_MONO}" font-size="13.5" fill="{SUBINK}">'
            f'{size} line{"s" if size != 1 else ""}</text>'
        )
        ry += 62
    parts.append("</g>")

    # --- footnote: read the hover affordance + method ---
    parts.append(
        f'<text x="{title_x}" y="{HEIGHT - 16}" font-size="15" '
        f'fill="{SUBINK}">Average linkage · hover or focus a cluster to '
        f'isolate its branches · taller merge = less alike</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the dendrogram SVG to the skill's example asset folder."""
    render_cli(__file__, "dendrogram", build_svg, description="Render the dendrogram SVG.")


if __name__ == "__main__":
    main()

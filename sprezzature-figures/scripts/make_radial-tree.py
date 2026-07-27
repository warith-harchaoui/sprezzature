#!/usr/bin/env python3
"""
make_radial-tree — publication-quality radial tree as a hand-authored SVG.

A **radial tree** lays a strict parent → child hierarchy out around a
circle: the root sits at the centre, and every generation is pushed onto
a concentric ring further out, with the angular span of the canvas split
among the leaves. Reading it, depth becomes *radius* (distance from the
centre) and sibling order becomes *angle*, so a wide, shallow taxonomy
fills the frame far more compactly than the left-to-right tidy tree in
``make_tree.py`` — the same reason a sunburst beats an indented list when
the branching factor is high. Links are **curved** (they bow along the
arc between two rings) rather than drawn as straight spokes, which keeps
sibling bundles visually separate and reads as an organic "branching"
shape instead of a wheel of radii.

Vega-Lite has no native tree/radial-tree mark (the layout is a recursive
angular assignment, not a data-to-mark mapping), so this figure is built
as an SVG string by hand rather than through ``vl_convert``. The layout
is the classic radial Reingold–Tilford variant:

* a post-order pass gives every **leaf** the next free slice of the
  angular range; each internal node is centred on the angular span of
  its children — the tidy-tree rule, expressed in angle instead of row;
* **depth** fixes the radius: ring 0 is the centre, and each deeper
  generation sits on a wider concentric ring;
* **links** are cubic Béziers whose control points are pulled toward the
  parent's ring, so each link bows outward along the arc — the smooth
  "radial diagonal" that professional dendrogram / phylogeny tools draw.

This is a **static** figure. A radial tree communicates its whole shape
in a single glance — a grow-in reveal adds no insight a still cannot
carry, and (worse) would leave the gallery's first frame empty — so
every mark is drawn once, fully, in its final state. The one piece of
motion that *does* pay for itself is interaction, and it stays
CSS-only (no JavaScript): every node carries a native ``<title>``
tooltip, and a ``:hover`` / ``:focus`` rule dims the rest of the tree
while lifting the hovered branch, so any wedge can be isolated on top of
an already-complete picture. ``interactive`` is true; ``animated`` is
false.

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, rounded
node dots, a start-anchored title plus a one-line takeaway subtitle.
Each top-level branch owns a hue that tints its whole subtree, so the
eye can group a family at a glance. Leaf labels are side-aware (right
half anchors start, left half anchors end) at a constant radial gap,
each with a thin leader out to the node, so the ring of text reads
cleanly and never crosses a branch.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/radial-tree.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import forced_color_patterns, load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _render import render_cli  # noqa: E402
from _svg import svg_open  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
# Poster-scale: the whole figure is ~1.6x the earlier draft so the ring
# of leaf labels has room to breathe and the marks read from across a
# room, not just at 100 %.
WIDTH = 1400
HEIGHT = 1200
CENTER_X = WIDTH / 2.0
# The circle centre sits below the header block so the top ring of
# labels never collides with the title / subtitle.
CENTER_Y = 660.0

INK = "#1D1D1F"          # primary text
SUBINK = "#6E6E73"       # secondary text
HAIRLINE = "#E5E5EA"     # neutral hairline
LEADER = "#C7C7CC"       # slightly darker hairline for label leaders
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

# Radius (in pixels) of each generation ring, indexed by depth. Ring 1
# is pushed well clear of the root pill so the two never collide; the
# outer rings are spread so leaf dots stop piling into a blob.
RING_RADIUS: List[float] = [0.0, 232.0, 372.0, 486.0]

# Constant radial gap from a leaf dot to its label text (pixels).
LABEL_GAP = 16.0


# ------------------------------------------------------------------
# The story (illustrative but plausible): a data-platform team maps its
# public API surface as a capability taxonomy. Root → four product
# pillars → the endpoints and features under each. The takeaway the
# subtitle states: the tree is *deliberately* lopsided — the Ingestion
# pillar carries the most surface area, because that is where the
# platform exposes the widest set of connectors.
#
# Each node: (id, label, parent_id or None for the root). Declaration
# order fixes sibling order, walking around the circle.
# ------------------------------------------------------------------
Node = Tuple[str, str, Optional[str]]

NODES: List[Node] = [
    ("root", "Data Platform API", None),

    # ---- Pillar: Ingestion (the heavy branch) ----
    ("ingest", "Ingestion", "root"),
    ("connectors", "Connectors", "ingest"),
    ("cdc", "Change data capture", "connectors"),
    ("files", "File & object stores", "connectors"),
    ("streams", "Event streams", "connectors"),
    ("schema", "Schema registry", "ingest"),
    ("validate", "Validation rules", "schema"),

    # ---- Pillar: Transform ----
    ("transform", "Transform", "root"),
    ("sql", "SQL models", "transform"),
    ("python", "Python jobs", "transform"),

    # ---- Pillar: Serve ----
    ("serve", "Serve", "root"),
    ("query", "Query engine", "serve"),
    ("cache", "Result cache", "serve"),

    # ---- Pillar: Govern ----
    ("govern", "Govern", "root"),
    ("lineage", "Lineage graph", "govern"),
    ("access", "Access policies", "govern"),
]

# Each top-level pillar owns a hue; the subtree inherits it.
def _pillar_color(accessibility: str = "universal") -> Dict[str, str]:
    """Map each top-level pillar to its hue at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        The palette accessibility level threaded into :func:`load_palette`;
        ``"universal"`` (default) is the colour-vision-safe standard.

    Returns
    -------
    dict of str to str
        ``{pillar_id: hex}`` for every top-level pillar.
    """
    palette = load_palette(accessibility)
    return {
        "ingest": palette.get("Blue", "#007AFF"),
        "transform": palette.get("Orange", "#FF9500"),
        "serve": palette.get("Purple", "#AF52DE"),
        "govern": palette.get("Green", "#34C759"),
    }


PALETTE = load_palette()
PILLAR_COLOR: Dict[str, str] = _pillar_color()
ROOT_COLOR = INK


# ------------------------------------------------------------------
# Tree model helpers
# ------------------------------------------------------------------
def _children_of() -> Dict[str, List[str]]:
    """Return ``{parent_id: [child_id, ...]}`` in declaration order."""
    kids: Dict[str, List[str]] = {}
    for node_id, _label, parent in NODES:
        if parent is not None:
            kids.setdefault(parent, []).append(node_id)
    return kids


def _parent_of() -> Dict[str, Optional[str]]:
    """Return ``{node_id: parent_id or None}``."""
    return {node_id: parent for node_id, _label, parent in NODES}


def _label_of() -> Dict[str, str]:
    """Return ``{node_id: label}``."""
    return {node_id: label for node_id, label, _parent in NODES}


def _depth_of(node_id: str, parent: Dict[str, Optional[str]]) -> int:
    """Return the distance from ``node_id`` up to the root."""
    depth = 0
    cur: Optional[str] = node_id
    while parent.get(cur) is not None:
        cur = parent[cur]
        depth += 1
    return depth


def _pillar_of(node_id: str, parent: Dict[str, Optional[str]]) -> Optional[str]:
    """Return the top-level pillar id (child-of-root) a node belongs to.

    The root itself returns ``None``; every other node walks up until it
    hits a node whose parent is the root.
    """
    cur: Optional[str] = node_id
    if cur == "root":
        return None
    while parent.get(cur) not in (None, "root"):
        cur = parent[cur]  # type: ignore[assignment]
    return cur


def _lineage(node_id: str, parent: Dict[str, Optional[str]]) -> List[str]:
    """Return the root→node chain of ids (inclusive of both ends)."""
    chain: List[str] = []
    cur: Optional[str] = node_id
    while cur is not None:
        chain.append(cur)
        cur = parent.get(cur)
    return list(reversed(chain))


# ------------------------------------------------------------------
# Radial tidy layout
# ------------------------------------------------------------------
def _compute_geometry(pillar_color: Optional[Dict[str, str]] = None) -> Dict[str, dict]:
    """Place every node with a radial tidy-tree layout.

    A post-order pass assigns each leaf the next free angular slice; each
    internal node is centred on the angular span of its children. Depth
    fixes the radius via :data:`RING_RADIUS`. Returns

    ``{node_id: {"x", "y", "angle", "radius", "depth", "pillar", "color"}}``
    where ``(x, y)`` is the node centre in SVG pixels and ``angle`` is in
    radians measured clockwise from straight up.

    Parameters
    ----------
    pillar_color : dict of str to str, optional
        ``{pillar_id: hex}`` colour map; defaults to the module-level
        :data:`PILLAR_COLOR` (the universal palette).
    """
    if pillar_color is None:
        pillar_color = PILLAR_COLOR
    kids = _children_of()
    parent = _parent_of()

    leaves = [n for n, _, _ in NODES if n not in kids]
    n_leaves = len(leaves)

    # Spread the leaves across an arc slightly short of a full turn so the
    # first and last leaf do not collide at 12 o'clock. A small gap at the
    # top also gives the eye a clear "seam" to read the circle from.
    span = 2.0 * math.pi * (1.0 - 1.0 / (n_leaves + 2))
    start = -span / 2.0  # centre the whole fan on straight-up (angle 0)
    step = span / (n_leaves - 1) if n_leaves > 1 else 0.0

    angle: Dict[str, float] = {}
    counter = [0]

    def assign(node_id: str) -> None:
        children = kids.get(node_id, [])
        if not children:
            angle[node_id] = start + counter[0] * step
            counter[0] += 1
            return
        for c in children:
            assign(c)
        # Centre the parent on the angular span of its children.
        angle[node_id] = (angle[children[0]] + angle[children[-1]]) / 2.0

    assign("root")

    geometry: Dict[str, dict] = {}
    for node_id, _label, _p in NODES:
        d = _depth_of(node_id, parent)
        r = RING_RADIUS[d] if d < len(RING_RADIUS) else RING_RADIUS[-1]
        a = angle[node_id]
        # angle 0 = straight up; clockwise positive.
        x = CENTER_X + r * math.sin(a)
        y = CENTER_Y - r * math.cos(a)
        pillar = _pillar_of(node_id, parent)
        color = ROOT_COLOR if node_id == "root" else pillar_color.get(pillar or "", SUBINK)
        geometry[node_id] = {
            "x": x,
            "y": y,
            "angle": a,
            "radius": r,
            "depth": d,
            "pillar": pillar,
            "color": color,
        }
    return geometry


# ------------------------------------------------------------------
# SVG geometry helpers
# ------------------------------------------------------------------
def _radial_link_path(
    a_ang: float, a_rad: float, b_ang: float, b_rad: float
) -> str:
    """Return a curved parent→child link path (a "radial diagonal").

    The link is a cubic Bézier whose two control points sit at the *mid
    radius* between the two rings but keep each end's own angle, so the
    curve bows along the arc instead of cutting a straight chord.

    Parameters
    ----------
    a_ang, a_rad : float
        Parent angle (radians, clockwise from up) and radius (pixels).
    b_ang, b_rad : float
        Child angle and radius.
    """
    def polar(ang: float, rad: float) -> Tuple[float, float]:
        return (CENTER_X + rad * math.sin(ang), CENTER_Y - rad * math.cos(ang))

    x0, y0 = polar(a_ang, a_rad)
    x3, y3 = polar(b_ang, b_rad)
    mid_rad = (a_rad + b_rad) / 2.0
    # Control point 1 keeps the parent's angle at the mid radius; control
    # point 2 keeps the child's angle at the mid radius. Together they bend
    # the curve outward along the arc.
    cx1, cy1 = polar(a_ang, mid_rad)
    cx2, cy2 = polar(b_ang, mid_rad)
    return f"M{x0:.1f},{y0:.1f} C{cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {x3:.1f},{y3:.1f}"


def _text_anchor_for(angle: float) -> Tuple[str, float]:
    """Return (text-anchor, dx) so a leaf label reads away from the centre.

    Nodes on the right half of the circle anchor at ``start`` and nudge
    right; nodes on the left half anchor at ``end`` and nudge left, so
    every label flows outward, never over its own branch.
    """
    # angle is clockwise from up; sin(angle) > 0 → right half.
    if math.sin(angle) >= 0:
        return "start", LABEL_GAP
    return "end", -LABEL_GAP


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def _wrap_subtitle(text: str, max_chars: int = 108) -> List[str]:
    """Greedy word-wrap the subtitle to at most two lines."""
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines[:2]


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full radial-tree SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`.
        One of ``"self-contained"`` (default, ships a hidden-until-live
        fullscreen button), ``"external"`` or ``"static"`` (no button).
    accessibility : str, optional
        The palette accessibility level. ``"universal"`` (default) is the
        colour-vision-safe standard; other levels (``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"``,
        ``"tritanopia"``) remap the hues via the sprezzature-colors engine.

    Returns
    -------
    str
        A complete, standalone SVG document with CSS hover/focus branch
        isolation. Every mark is drawn once in its final state — there is
        no entrance animation.
    """
    pillar_color = _pillar_color(accessibility)
    geometry = _compute_geometry(pillar_color)
    parent = _parent_of()
    kids = _children_of()
    label_of = _label_of()

    parts: List[str] = []

    # --- accessible header text ---
    title_txt = "The Data Platform API, from the core outward"
    subtitle_txt = (
        "Four product pillars branch from one core; Ingestion carries the widest "
        "surface. Illustrative capability map."
    )
    desc_txt = (
        "Radial tree of a data-platform public API laid out from the centre "
        "outward. The root, Data Platform API, sits at the middle and splits into "
        "four pillars on the first ring: Ingestion, Transform, Serve, and Govern. "
        "Ingestion is the widest branch, reaching connectors such as change data "
        "capture, file and object stores, and event streams, plus a schema "
        "registry. Each pillar is tinted its own color, and links curve along the "
        "arc between rings."
    )

    parts.append(svg_open(WIDTH, HEIGHT, "rt-title", "rt-desc", font_family=FONT))
    parts.append(f'<title id="rt-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="rt-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hover/focus a branch group lifts it, dims the rest ---
    # Each leaf-to-root lineage is wrapped in <g class="lin">. Hovering the
    # tree dims every branch on the base layer; the hovered/focused lineage
    # overlay (invisible at rest) lights up just that branch on top, giving
    # crisp isolation over an already-complete picture. No entrance motion,
    # so nothing to guard for reduced-motion.
    # OS-adaptive overrides are appended (additive; every rule lives inside an
    # @media block so the default render is byte-for-byte unchanged). Each
    # pillar tints its subtree; under prefers-contrast the four hues deepen
    # together to their high-contrast spacing. Links carry ``.rt-lk-<pillar>``
    # (deepened on the stroke) and the coloured fills — pillar pills, dots and
    # legend swatches — carry ``.rt-nd-<pillar>`` (deepened on the fill), so a
    # link's open path is never accidentally flooded. Under forced-colors
    # (Windows High Contrast) the ~4-colour system palette cannot preserve four
    # pillar hues, so each pillar's coloured fills (its pill, dots and legend
    # swatch) are handed a distinct Canvas/CanvasText PATTERN via
    # forced_color_patterns, so the families stay groupable from the pill/legend
    # key when colour is stripped; links drop to system line art (node labels and
    # angular position still trace every branch).
    link_series = {f".rt-lk-{pid}": pillar_color[pid] for pid in pillar_color}
    node_series = {f".rt-nd-{pid}": pillar_color[pid] for pid in pillar_color}
    fcp_defs, fcp_style = forced_color_patterns(list(node_series), prefix="rt-fcp")
    contrast_block = (
        os_adaptive_style(link_series, role="stroke")
        + "\n"
        + os_adaptive_style(node_series, role="fill")
    )
    parts.append(
        "<style>"
        "#base .link,#base .node{transition:opacity .16s ease}"
        "#lineages .lin{opacity:0;transition:opacity .16s ease}"
        "#tree:hover #base .link{opacity:.15}"
        "#tree:hover #base .node{opacity:.28}"
        ".lin:hover,.lin:focus-within{opacity:1}"
        ".hit:focus{outline:none}"
        + "\n" + contrast_block + "\n"
        + fcp_style + "\n"
        + os_dark_style(extra='[stroke="#E5E5EA"]{stroke:#2C2C2E;}') + "\n"
        "</style>"
    )
    parts.append(f"<defs>{fcp_defs}</defs>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    margin_left = 40
    parts.append(
        f'<text x="{margin_left}" y="54" font-size="30" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    for i, line in enumerate(_wrap_subtitle(subtitle_txt)):
        parts.append(
            f'<text x="{margin_left}" y="{88 + i * 26}" font-size="19" '
            f'fill="{SUBINK}">{escape(line)}</text>'
        )

    # --- faint concentric ring guides (one per generation) ---
    # The leaf fan leaves an empty wedge at the bottom (6 o'clock); we drop
    # the ring names into that seam, straight down from the centre, so they
    # never sit under a branch. Each name is placed just inside its ring.
    parts.append('<g id="rings">')
    gen_names = ["Core", "Pillar", "Area", "Feature"]
    for _d, r in enumerate(RING_RADIUS):
        if r <= 0:
            continue
        parts.append(
            f'<circle cx="{CENTER_X:.1f}" cy="{CENTER_Y:.1f}" r="{r:.1f}" '
            f'fill="none" stroke="{HAIRLINE}" stroke-width="1.25"/>'
        )
    # Ring names down the bottom seam, each labelling the ring it sits on.
    for d, r in enumerate(RING_RADIUS):
        if d == 0 or d >= len(gen_names):
            continue
        ly = CENTER_Y + r - 9.0
        parts.append(
            f'<text x="{CENTER_X + 9:.1f}" y="{ly:.1f}" '
            f'font-size="13" font-weight="600" letter-spacing="0.8" '
            f'fill="{SUBINK}">{escape(gen_names[d].upper())}</text>'
        )
    # Label the core ring right under the root pill.
    parts.append(
        f'<text x="{CENTER_X + 9:.1f}" y="{CENTER_Y + 60:.1f}" '
        f'font-size="13" font-weight="600" letter-spacing="0.8" '
        f'fill="{SUBINK}">{escape(gen_names[0].upper())}</text>'
    )
    parts.append("</g>")

    # --- resting base layer: all links + nodes, fully drawn ---
    parts.append('<g id="tree">')
    parts.append('<g id="base">')
    _emit_links(parts, geometry)
    _emit_nodes(parts, geometry, label_of, kids)
    parts.append("</g>")

    # --- interactive lineage groups on top (opacity-only at rest) ---
    leaves = [n for n, _, _ in NODES if n not in kids]
    parts.append('<g id="lineages">')
    for leaf in leaves:
        chain = _lineage(leaf, parent)
        tip = " › ".join(label_of[c] for c in chain)
        parts.append(
            f'<g class="lin" tabindex="0" role="img" '
            f'aria-label="{escape(tip)}"><title>{escape(tip)}</title>'
        )
        for a, b in zip(chain, chain[1:]):
            _emit_one_link(parts, geometry, a, b)
        for node_id in chain:
            _emit_one_node(parts, geometry, label_of, kids, node_id, interactive=True)
        parts.append("</g>")
    parts.append("</g>")

    parts.append("</g>")  # #tree

    # --- pillar legend (bottom-left) ---
    _emit_legend(parts, pillar_color)

    # --- footnote: read the affordances ---
    parts.append(
        f'<text x="{margin_left}" y="{HEIGHT - 22}" font-size="15" '
        f'fill="{SUBINK}">Hover or focus any node to trace its branch back '
        f'to the centre</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


# ------------------------------------------------------------------
# Link / node emitters
# ------------------------------------------------------------------
def _emit_links(parts: List[str], geometry: Dict[str, dict]) -> None:
    """Emit every parent→child link once for the resting base layer."""
    for node_id, _label, p in NODES:
        if p is None:
            continue
        _emit_one_link(parts, geometry, p, node_id)


def _emit_one_link(
    parts: List[str],
    geometry: Dict[str, dict],
    a: str,
    b: str,
) -> None:
    """Emit one curved parent-``a`` → child-``b`` radial link.

    The link is drawn once at full opacity in its final geometry; the
    hover CSS dims or lifts it, but its resting state is complete.
    """
    ga = geometry[a]
    gb = geometry[b]
    d = _radial_link_path(ga["angle"], ga["radius"], gb["angle"], gb["radius"])
    # Link colour = the child's pillar hue (branch reads as a unit).
    stroke = gb["color"]
    # Thicker links closer to the core; taper toward the leaves.
    width = 4.5 if gb["depth"] <= 1 else 3.0
    # Per-pillar class = the prefers-contrast hook (stroke-only, so the open
    # link path is never flooded by a fill override).
    pillar = gb["pillar"]
    lk_class = f" rt-lk-{pillar}" if pillar else ""
    parts.append(
        f'<path class="link{lk_class}" d="{d}" fill="none" stroke="{stroke}" '
        f'stroke-width="{width:.1f}" stroke-linecap="round"/>'
    )


def _emit_nodes(
    parts: List[str],
    geometry: Dict[str, dict],
    label_of: Dict[str, str],
    kids: Dict[str, List[str]],
) -> None:
    """Emit every node (dot + label) once for the resting base layer."""
    for node_id, _label, _p in NODES:
        _emit_one_node(parts, geometry, label_of, kids, node_id)


def _emit_one_node(
    parts: List[str],
    geometry: Dict[str, dict],
    label_of: Dict[str, str],
    kids: Dict[str, List[str]],
    node_id: str,
    *,
    interactive: bool = False,
) -> None:
    """Emit one node: a coloured dot plus its label, styled by depth.

    The root is an ink pill with white text; pillars are filled coloured
    pills; deeper nodes are coloured dots with outward-flowing ink labels
    on a thin leader. Every mark is drawn once in its final state.
    """
    g = geometry[node_id]
    label = label_of[node_id]
    color = g["color"]
    depth = g["depth"]
    x, y = g["x"], g["y"]
    is_leaf = node_id not in kids

    tab = ' tabindex="0"' if (interactive and not is_leaf) else ""
    tip = label
    # Per-pillar fill hook for prefers-contrast (empty for the ink root, which
    # is not a pillar hue and must stay ink).
    pillar = g["pillar"]
    nd_class = f" rt-nd-{pillar}" if pillar else ""

    if depth == 0:
        # Root: ink pill centred on the middle.
        pad_x, fs = 18.0, 17.0
        w = len(label) * fs * 0.56 + 2 * pad_x
        h = 40.0
        parts.append(
            f'<g class="node">'
            f'<rect class="hit"{tab} x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" fill="{color}">'
            f'<title>{escape(tip)}</title></rect>'
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="{fs}" font-weight="700" '
            f'fill="#FFFFFF">{escape(label)}</text>'
            f'</g>'
        )
        return

    if depth == 1:
        # Pillar: filled coloured pill.
        pad_x, fs = 15.0, 16.0
        w = len(label) * fs * 0.56 + 2 * pad_x
        h = 36.0
        parts.append(
            f'<g class="node">'
            f'<rect class="hit{nd_class}"{tab} x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" fill="{color}">'
            f'<title>{escape(tip)}</title></rect>'
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="{fs}" font-weight="700" '
            f'fill="#FFFFFF">{escape(label)}</text>'
            f'</g>'
        )
        return

    # Deeper node: coloured dot + a thin leader out to an outward label.
    anchor, dx = _text_anchor_for(g["angle"])
    r_dot = 7.0 if not is_leaf else 5.5
    # Leader runs from just outside the dot to just before the text, along
    # the node's own radial direction, so it reads as a tidy tick.
    ux, uy = math.sin(g["angle"]), -math.cos(g["angle"])
    lead_x0 = x + ux * (r_dot + 2.0)
    lead_y0 = y + uy * (r_dot + 2.0)
    lead_x1 = x + dx * 0.75
    lead_y1 = y
    parts.append(
        f'<g class="node">'
        f'<line x1="{lead_x0:.1f}" y1="{lead_y0:.1f}" x2="{lead_x1:.1f}" '
        f'y2="{lead_y1:.1f}" stroke="{LEADER}" stroke-width="1"/>'
        f'<circle class="hit{nd_class}"{tab} cx="{x:.1f}" cy="{y:.1f}" r="{r_dot:.1f}" '
        f'fill="{color}"><title>{escape(tip)}</title></circle>'
        f'<text x="{x + dx:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'dominant-baseline="central" font-size="15.5" '
        f'fill="{INK}">{escape(label)}</text>'
        f'</g>'
    )


def _emit_legend(parts: List[str], pillar_color: Optional[Dict[str, str]] = None) -> None:
    """Emit the pillar legend as a small swatch column, bottom-left.

    Parameters
    ----------
    parts : list of str
        The running SVG fragment list to append to.
    pillar_color : dict of str to str, optional
        ``{pillar_id: hex}`` colour map; defaults to the module-level
        :data:`PILLAR_COLOR` (the universal palette).
    """
    if pillar_color is None:
        pillar_color = PILLAR_COLOR
    # Count each pillar's subtree size (nodes below it, inclusive of itself).
    parent = _parent_of()

    def subtree_size(pillar_id: str) -> int:
        return sum(
            1 for n, _, _ in NODES if _pillar_of(n, parent) == pillar_id
        )

    order = ["ingest", "transform", "serve", "govern"]
    names = {
        "ingest": "Ingestion",
        "transform": "Transform",
        "serve": "Serve",
        "govern": "Govern",
    }
    lx = 40.0
    ly = HEIGHT - 176.0
    parts.append('<g id="legend">')
    parts.append(
        f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="14" font-weight="700" '
        f'letter-spacing="0.8" fill="{SUBINK}">PILLARS</text>'
    )
    ry = ly + 26
    for pid in order:
        size = subtree_size(pid)
        parts.append(
            f'<rect class="rt-nd-{pid}" x="{lx:.1f}" y="{ry - 13:.1f}" '
            f'width="17" height="17" rx="4.5" fill="{pillar_color[pid]}"/>'
        )
        parts.append(
            f'<text x="{lx + 26:.1f}" y="{ry:.1f}" font-size="16" fill="{INK}">'
            f'{escape(names[pid])}</text>'
        )
        parts.append(
            f'<text x="{lx + 150:.1f}" y="{ry:.1f}" font-family="{FONT_MONO}" '
            f'font-size="14" fill="{SUBINK}">{size} node{"s" if size != 1 else ""}</text>'
        )
        ry += 31
    parts.append("</g>")


def main() -> None:
    """Write the radial-tree SVG to the skill's example asset folder."""
    render_cli(__file__, "radial-tree", build_svg, description="Render the radial-tree SVG.")


if __name__ == "__main__":
    main()

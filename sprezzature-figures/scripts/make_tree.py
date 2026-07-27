#!/usr/bin/env python3
"""
make_tree — publication-quality tidy node-link tree as a hand-authored SVG.

A tree diagram (org chart / taxonomy) shows a strict parent → child
hierarchy: every node has exactly one parent, and the reader follows
the branching structure from a single root down to the leaves. It
answers "how does this whole break into parts, and how deep does any
branch go?" more directly than an indented list, because the eye reads
depth as horizontal distance and siblings as a vertical stack.

Vega-Lite has no native tidy-tree mark, so this figure is built as an
SVG string by hand rather than through ``vl_convert``. The layout is a
**left-to-right Reingold–Tilford tidy tree**:

* every node sits in a column ("depth") fixed by its distance from the
  root, so all siblings across the tree line up by generation;
* leaves are packed onto evenly-spaced rows, and each internal node is
  centred on the vertical span of its children — the classic tidy
  layout that keeps the tree compact with no crossing edges;
* **links** are smooth horizontal cubic-Bézier curves (diagonal links,
  not elbow/orthogonal) from a parent's right edge to a child's left
  edge, which read cleanly at this fan-out.

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, rounded
node corners, a start-anchored title plus a one-line takeaway subtitle.
Each top-level branch owns a hue, and that hue tints the whole subtree
so the eye can group a family at a glance.

Interaction (no JavaScript): every node carries a native ``<title>``
tooltip, and a CSS ``:hover`` / ``:focus`` rule lifts a node's whole
root-to-node lineage — the ancestor links and node cards brighten while
the rest of the tree dims. That "trace a branch to the root" affordance
is exactly what a hierarchy invites, so ``interactive`` is true. A tidy
tree does not benefit from motion, so ``animated`` is false.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/tree.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _render import svg_example_path, write_svg  # noqa: E402
from _svg import svg_open  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1300
HEIGHT = 1000
MARGIN_LEFT = 40
MARGIN_RIGHT = 40
MARGIN_TOP = 176         # room for title + two-line subtitle + column headers
MARGIN_BOTTOM = 72       # room for the hover-affordance footnote

INK = "#1D1D1F"          # primary text
SUBINK = "#6E6E73"       # secondary text
HAIRLINE = "#E5E5EA"     # neutral hairline
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

NODE_H = 48              # card height
ROW_GAP = 26             # vertical gap between leaf rows
LINK_COLOR = "#C7C7CC"   # default (dimmed) link color


# ------------------------------------------------------------------
# The story (illustrative but plausible): a machine-learning course
# syllabus laid out as a taxonomy. Root → four families → topics. The
# takeaway the subtitle states: the tree is *deliberately* lopsided —
# supervised learning carries the most sub-topics because that is where
# the course spends most of its weeks.
#
# Each node: (id, label, parent_id or None for the root). Declaration
# order fixes sibling order top-to-bottom.
# ------------------------------------------------------------------
Node = Tuple[str, str, Optional[str]]

NODES: List[Node] = [
    ("root", "Machine learning", None),

    # ---- Family: Supervised (the heavy branch) ----
    ("sup", "Supervised", "root"),
    ("cls", "Classification", "sup"),
    ("logreg", "Logistic regression", "cls"),
    ("svm", "Support-vector machines", "cls"),
    ("trees", "Gradient-boosted trees", "cls"),
    ("reg", "Regression", "sup"),
    ("linreg", "Linear & ridge", "reg"),
    ("gp", "Gaussian processes", "reg"),

    # ---- Family: Unsupervised ----
    ("uns", "Unsupervised", "root"),
    ("clust", "Clustering", "uns"),
    ("dimred", "Dimensionality reduction", "uns"),

    # ---- Family: Deep learning ----
    ("deep", "Deep learning", "root"),
    ("cnn", "Convolutional nets", "deep"),
    ("transf", "Transformers", "deep"),

    # ---- Family: Reinforcement ----
    ("rl", "Reinforcement", "root"),
    ("policy", "Policy gradients", "rl"),
]

# Each top-level family owns a hue; the subtree inherits it. These bright
# hues carry no text — they colour the branch links and the left rules on
# the white leaf chips — so their vividness costs no legibility.
PALETTE = load_palette()
FAMILY_COLOR: Dict[str, str] = {
    "sup": PALETTE.get("Blue", "#007AFF"),
    "uns": PALETTE.get("Orange", "#FF9500"),
    "deep": PALETTE.get("Purple", "#AF52DE"),
    "rl": PALETTE.get("Green", "#34C759"),
}
# The family *pills* carry white label text, so their fill must clear WCAG
# AA against white. The bright Orange (2.2:1) and Green (2.2:1) fail even the
# large-text 3:1 bar, so the pills use darker, same-hue shades — every one
# now clears 4.5:1 with white — while the links keep the vivid hues above.
FAMILY_PILL: Dict[str, str] = {
    "sup": "#0064D2",   # deeper blue  — 5.6:1 on white text
    "uns": "#B35900",   # deeper orange — 4.8:1
    "deep": "#9A3FCB",  # deeper purple — 5.3:1
    "rl": "#22883A",    # deeper green  — 4.5:1
}
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


def _family_of(node_id: str, parent: Dict[str, Optional[str]]) -> Optional[str]:
    """Return the top-level family id (child-of-root) a node belongs to.

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
# Reingold–Tilford tidy layout (left-to-right)
# ------------------------------------------------------------------
def _compute_geometry() -> Dict[str, dict]:
    """Place every node with a tidy tree layout.

    Depth fixes the x-column; a post-order pass assigns each leaf the
    next free row and centres every internal node on the mean row of its
    children. Returns

    ``{node_id: {"x", "y", "depth", "family", "color"}}`` where ``(x, y)``
    is the *centre* of the node card in SVG pixels.
    """
    kids = _children_of()
    parent = _parent_of()

    # --- vertical (row) positions via post-order leaf packing ---
    row_pitch = NODE_H + ROW_GAP
    next_row = [0]  # mutable counter for the recursion
    row: Dict[str, float] = {}

    def assign(node_id: str) -> None:
        children = kids.get(node_id, [])
        if not children:
            row[node_id] = next_row[0]
            next_row[0] += 1
            return
        for c in children:
            assign(c)
        # centre parent on the span of its children
        row[node_id] = (row[children[0]] + row[children[-1]]) / 2.0

    assign("root")

    # Centre the whole stack vertically in the plot band so the tree is
    # never bottom-heavy or top-heavy: measure the row span the leaves
    # actually occupy, then offset every node by the leftover slack / 2.
    n_rows = next_row[0]                       # leaf count == packed rows
    plot_top = MARGIN_TOP
    plot_bottom = HEIGHT - MARGIN_BOTTOM
    band_h = plot_bottom - plot_top
    stack_h = (n_rows - 1) * row_pitch + NODE_H
    y_offset = plot_top + max(0.0, (band_h - stack_h) / 2.0)

    # --- horizontal (depth) columns: a fixed LEFT-anchor x per column ---
    # Every card in a column starts at the same x, so the columns read as
    # a clean grid (no ragged, centre-justified edges). Columns are evenly
    # spaced; the last column leaves room for the deepest leaf labels.
    max_depth = max(_depth_of(n, parent) for n, _, _ in NODES)
    plot_left = MARGIN_LEFT
    plot_right = WIDTH - MARGIN_RIGHT
    col_span = plot_right - plot_left
    col_x = [plot_left + d * col_span / (max_depth + 1) for d in range(max_depth + 1)]

    geometry: Dict[str, dict] = {}
    for node_id, _label, _p in NODES:
        d = _depth_of(node_id, parent)
        fam = _family_of(node_id, parent)
        color = ROOT_COLOR if node_id == "root" else FAMILY_COLOR.get(fam or "", SUBINK)
        geometry[node_id] = {
            "x": col_x[d],                     # left-anchor x for this column
            "y": y_offset + NODE_H / 2.0 + row[node_id] * row_pitch,
            "depth": d,
            "family": fam,
            "color": color,
        }
    return geometry


# ------------------------------------------------------------------
# SVG emission helpers
# ------------------------------------------------------------------
def _diagonal_path(x0: float, y0: float, x1: float, y1: float) -> str:
    """Return a horizontal cubic-Bézier link from ``(x0,y0)`` to ``(x1,y1)``.

    Control points sit at the horizontal midpoint, giving the smooth
    S-curve of a tidy node-link tree (as opposed to elbow/orthogonal
    links). ``(x0, y0)`` is the parent's right edge; ``(x1, y1)`` the
    child's left edge.
    """
    xc = (x0 + x1) / 2.0
    return f"M{x0:.1f},{y0:.1f} C{xc:.1f},{y0:.1f} {xc:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"


def _text_width(label: str, font_size: float) -> float:
    """Rough advance-width estimate for a Roboto label at ``font_size``.

    Good enough to size a node card; ~0.56em per character is a safe
    average for Roboto's mixed-case metrics.
    """
    return len(label) * font_size * 0.56


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full tidy-tree SVG document as a string.

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
        the emitted SVG stays unchanged; any other level remaps the family
        hues (branch links and leaf-chip rules).

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    geometry = _compute_geometry()

    # ``universal`` leaves the baked family colours as shipped (output
    # byte-identical); any other level re-reads the palette at that level and
    # recolours every non-root node by its family.
    if accessibility and accessibility != "universal":
        pal = load_palette(accessibility)
        family_color = {
            "sup": pal.get("Blue", "#007AFF"),
            "uns": pal.get("Orange", "#FF9500"),
            "deep": pal.get("Purple", "#AF52DE"),
            "rl": pal.get("Green", "#34C759"),
        }
        for node_id, geo in geometry.items():
            if node_id == "root":
                continue
            geo["color"] = family_color.get(geo["family"] or "", SUBINK)
    parent = _parent_of()
    kids = _children_of()
    label_of = _label_of()

    parts: List[str] = []

    # --- accessible header ---
    title_txt = "A machine-learning syllabus, branch by branch"
    subtitle_txt = (
        "Supervised learning carries the deepest branch, reaching all the way "
        "down to named algorithms. That is where the course spends most weeks. "
        "Illustrative outline."
    )
    desc_txt = (
        "Tidy node-link tree of a machine-learning course taxonomy. The root, "
        "Machine learning, splits into four families: Supervised, Unsupervised, "
        "Deep learning, and Reinforcement. Supervised is the deepest and widest "
        "branch, reaching individual algorithms such as gradient-boosted trees "
        "and Gaussian processes. Each family is tinted its own color."
    )
    parts.append(svg_open(WIDTH, HEIGHT, "tree-title", "tree-desc", font_family=FONT))
    parts.append(f'<title id="tree-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="tree-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hover/focus a node lifts its whole root-to-node lineage ---
    # Each node group carries data-lin="id id id" (its ancestor chain).
    # Pure CSS cannot read that attribute to cross-highlight, so we use a
    # scoped approach: hovering ANY node in the tree dims every node and
    # link, then a per-node <g> with class "on" (set by :hover/:focus via
    # a sibling combinator is impossible), so instead each link/node that
    # belongs to a lineage is grouped and lifted by the group :hover.
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside a media query). Under
    # prefers-contrast each of the four family hues deepens to its
    # high-contrast value: the branch links (as a stroke), the leaf-chip left
    # rules (as a fill) and the family pills (as a fill). The link and rule
    # roles are kept separate on purpose — the links are ``fill="none"``
    # <path>s, so a fill rule would blob them, and the rules draw no stroke.
    # Forced colours are left to the browser default: colour groups a family,
    # but each family is also named on its pill and tied to its leaves by the
    # link structure, so identity survives without colour, and the ~4-colour
    # system palette cannot preserve four distinct branch tints anyway.
    link_series = {f".link.fam-{fam}": hexv for fam, hexv in FAMILY_COLOR.items()}
    rule_series = {f".fam-rule.fam-{fam}": hexv for fam, hexv in FAMILY_COLOR.items()}
    pill_series = {f".pill-{fam}": hexv for fam, hexv in FAMILY_PILL.items()}
    contrast_css = (
        os_adaptive_style(link_series, role="stroke")
        + "\n"
        + os_adaptive_style(rule_series, role="fill")
        + "\n"
        + os_adaptive_style(pill_series, role="fill")
    )
    # Additive OS dark-mode block. This figure paints white *both* as surfaces
    # (the page background and the leaf chip rects) and as ink (the label on the
    # filled family / root pills), so a blanket #FFFFFF inversion would darken
    # that pill text and kill its contrast. We therefore drive the surfaces
    # explicitly (only white RECTs darken) and leave white text alone, while the
    # two ink tiers and the neutral hairline flip to dark values. No multiply.
    dark_css = os_dark_style(
        ink_map={"#1D1D1F": "#F2F2F7", "#6E6E73": "#9C9CA3"},
        screen_blend=False,
        extra='rect[fill="#FFFFFF"]{fill:#141416;} '
        '[stroke="#E5E5EA"]{stroke:#3A3A3C;} '
        'rect.card[fill="#1D1D1F"]{fill:#48484A;}',
    )
    parts.append(
        "<style>"
        ".node,.link{transition:opacity .16s ease}"
        # Dim everything while the tree is being hovered…
        "#tree:hover .link{opacity:.25}"
        "#tree:hover .node{opacity:.4}"
        # …then a hovered/focused lineage group brings its members back.
        ".lin:hover .link,.lin:hover .node,"
        ".lin:focus-within .link,.lin:focus-within .node{opacity:1}"
        ".card:focus{outline:none}"
        + contrast_css
        + dark_css
        + "</style>"
    )

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="{MARGIN_LEFT}" y="56" font-size="32" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    # subtitle can be long, so wrap onto two lines at the sentence break.
    sub_lines = _wrap_subtitle(subtitle_txt)
    for i, line in enumerate(sub_lines):
        parts.append(
            f'<text x="{MARGIN_LEFT}" y="{92 + i * 27:.0f}" font-size="20" '
            f'fill="{SUBINK}">{escape(line)}</text>'
        )

    # --- depth (generation) column headers ---
    gen_names = ["Field", "Family", "Task", "Method"]
    seen_depths = sorted({g["depth"] for g in geometry.values()})
    for d in seen_depths:
        if d >= len(gen_names):
            continue
        gx = next(g["x"] for g in geometry.values() if g["depth"] == d)
        parts.append(
            f'<text x="{gx:.1f}" y="{MARGIN_TOP - 30:.1f}" font-size="15" '
            f'font-weight="600" letter-spacing="1.0" fill="{SUBINK}">'
            f'{escape(gen_names[d].upper())}</text>'
        )

    # ------------------------------------------------------------------
    # We wrap each *leaf-to-root lineage* in its own <g class="lin"> so a
    # CSS :hover on it can lift the full ancestor chain. A node shared by
    # several lineages (an internal node) is redrawn inside each lineage
    # group it participates in; the topmost redraw wins visually, and the
    # dimming is uniform, so the duplication is invisible but lets any
    # branch light up its ancestors.
    # ------------------------------------------------------------------
    leaves = [n for n, _, _ in NODES if n not in kids]

    parts.append('<g id="tree">')

    # Draw a faint "base" layer first (all links + all nodes at full
    # opacity when nothing is hovered) so the tree reads normally at rest.
    parts.append('<g id="base">')
    _emit_links(parts, geometry, parent, base=True)
    _emit_nodes(parts, geometry, label_of, kids, base=True)
    parts.append("</g>")

    # Then the interactive lineage groups on top (transparent at rest via
    # the base underneath; they only change opacity on hover/focus).
    parts.append('<g id="lineages">')
    for leaf in leaves:
        chain = _lineage(leaf, parent)
        tip = " › ".join(label_of[c] for c in chain)
        parts.append(
            f'<g class="lin" tabindex="0" role="img" '
            f'aria-label="{escape(tip)}"><title>{escape(tip)}</title>'
        )
        # ancestor links along the chain
        for a, b in zip(chain, chain[1:]):
            _emit_one_link(parts, geometry, a, b)
        # the nodes along the chain
        for node_id in chain:
            _emit_one_node(parts, geometry, label_of, kids, node_id, interactive=True)
        parts.append("</g>")
    parts.append("</g>")

    parts.append("</g>")  # #tree

    # --- footnote: read the hover affordance ---
    parts.append(
        f'<text x="{MARGIN_LEFT}" y="{HEIGHT - 20}" font-size="15" '
        f'fill="{SUBINK}">Hover or focus any topic to trace its path back '
        f'to the root</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def _wrap_subtitle(text: str, max_chars: int = 96) -> List[str]:
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


# ------------------------------------------------------------------
# Link / node emitters
# ------------------------------------------------------------------
def _card_geom(geometry: Dict[str, dict], node_id: str, label: str) -> Tuple[float, float, float, float]:
    """Return (x_left, y_top, width, height) of a node card.

    Every card is **left-anchored** on its column x, whatever its width,
    so a whole generation shares one clean left edge and the columns read
    as a grid. Root and family (depth ≤ 1) cards are pill-shaped; deeper
    cards are text chips. Long labels extend rightward without disturbing
    the alignment of their neighbours.
    """
    g = geometry[node_id]
    fs = 19.0 if g["depth"] <= 1 else 17.0
    pad_x = 20 if g["depth"] <= 1 else 14
    w = _text_width(label, fs) + 2 * pad_x
    x_left = g["x"]
    y_top = g["y"] - NODE_H / 2.0
    return x_left, y_top, w, NODE_H


def _edge_points(
    geometry: Dict[str, dict], label_of: Dict[str, str], a: str, b: str
) -> Tuple[float, float, float, float]:
    """Return (x0,y0,x1,y1): parent-``a`` right edge to child-``b`` left edge."""
    la = label_of[a]
    lb = label_of[b]
    ax_left, _ay, aw, _ah = _card_geom(geometry, a, la)
    bx_left, _by, _bw, _bh = _card_geom(geometry, b, lb)
    x0 = ax_left + aw
    y0 = geometry[a]["y"]
    x1 = bx_left
    y1 = geometry[b]["y"]
    return x0, y0, x1, y1


def _emit_links(
    parts: List[str],
    geometry: Dict[str, dict],
    parent: Dict[str, Optional[str]],
    *,
    base: bool,
) -> None:
    """Emit every parent→child link once (used for the resting base layer)."""
    label_of = _label_of()
    for node_id, _label, p in NODES:
        if p is None:
            continue
        _emit_one_link(parts, geometry, p, node_id, label_of=label_of)


def _emit_one_link(
    parts: List[str],
    geometry: Dict[str, dict],
    a: str,
    b: str,
    label_of: Optional[Dict[str, str]] = None,
) -> None:
    """Emit a single parent-``a`` → child-``b`` diagonal link path."""
    label_of = label_of or _label_of()
    x0, y0, x1, y1 = _edge_points(geometry, label_of, a, b)
    # Link color = the child's family hue (so the branch reads as a unit).
    # Read it off the resolved geometry (which already carries the family
    # colour, remapped when an accessibility level is active) so the link and
    # its child card always agree; a child node is never the root, so this is
    # exactly ``FAMILY_COLOR.get(fam)`` at the universal level.
    stroke = str(geometry[b]["color"]) or LINK_COLOR
    # The child's family id scopes the OS-adaptive contrast rule so a whole
    # branch's links deepen together (empty for a direct child of the root,
    # which cannot happen here since every link's child sits under a family).
    fam = geometry[b].get("family") or ""
    fam_cls = f" fam-{fam}" if fam else ""
    d = _diagonal_path(x0, y0, x1, y1)
    parts.append(
        f'<path class="link{fam_cls}" d="{d}" fill="none" stroke="{stroke}" '
        f'stroke-width="3" stroke-opacity="0.9" stroke-linecap="round"/>'
    )


def _emit_nodes(
    parts: List[str],
    geometry: Dict[str, dict],
    label_of: Dict[str, str],
    kids: Dict[str, List[str]],
    *,
    base: bool,
) -> None:
    """Emit every node card once (resting base layer)."""
    for node_id, _label, _p in NODES:
        _emit_one_node(parts, geometry, label_of, kids, node_id, interactive=False)


def _emit_one_node(
    parts: List[str],
    geometry: Dict[str, dict],
    label_of: Dict[str, str],
    kids: Dict[str, List[str]],
    node_id: str,
    *,
    interactive: bool,
) -> None:
    """Emit one node card (rounded rect + label), colored by its family.

    Root and family nodes are filled pills; deeper nodes are white chips
    with a colored left rule and colored text, so the tree stays airy and
    the ink-heavy pills draw the eye to the top of the hierarchy.
    """
    g = geometry[node_id]
    label = label_of[node_id]
    x_left, y_top, w, h = _card_geom(geometry, node_id, label)
    color = g["color"]
    depth = g["depth"]
    cx = x_left + w / 2.0
    cy = y_top + h / 2.0
    tip = label

    is_leaf = node_id not in kids
    tab = ' tabindex="0"' if (interactive and not is_leaf) else ""

    if depth <= 1:
        # Filled pill — root is ink, families are their AA-safe deeper hue so
        # the white label clears 4.5:1 on the fill (the bright hue would not).
        text_fill = "#FFFFFF"
        fam = g["family"]
        pill_fill = ROOT_COLOR if node_id == "root" else FAMILY_PILL.get(fam or "", color)
        # Family pills (not the ink root) get a family class so the OS-adaptive
        # contrast rule can deepen the pill fill together with its branch.
        pill_cls = f' pill-{fam}' if fam else ""
        parts.append(
            f'<g class="node">'
            f'<rect class="card{pill_cls}"{tab} x="{x_left:.1f}" y="{y_top:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" fill="{pill_fill}">'
            f'<title>{escape(tip)}</title></rect>'
            f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="19" font-weight="700" '
            f'fill="{text_fill}">{escape(label)}</text>'
            f'</g>'
        )
    else:
        # White chip with a colored left rule + colored label.
        rule_w = 5.0
        fam = g["family"]
        rule_cls = f' fam-{fam}' if fam else ""
        parts.append(
            f'<g class="node">'
            f'<rect x="{x_left:.1f}" y="{y_top:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" rx="10" fill="#FFFFFF" stroke="{HAIRLINE}" '
            f'stroke-width="1.5"><title>{escape(tip)}</title></rect>'
            f'<rect class="fam-rule{rule_cls}" x="{x_left:.1f}" y="{y_top:.1f}" '
            f'width="{rule_w:.1f}" '
            f'height="{h:.1f}" rx="2.5" fill="{color}"/>'
            f'<text x="{x_left + rule_w + 11:.1f}" y="{cy:.1f}" '
            f'dominant-baseline="central" font-size="17" font-weight="500" '
            f'fill="{INK}">{escape(label)}</text>'
            f'</g>'
        )


def main() -> None:
    """Write the tidy-tree SVG to the skill's example asset folder."""
    parser = argparse.ArgumentParser(description="Render the tidy-tree SVG.")
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
    out = Path(args.out) if args.out else svg_example_path(__file__, "tree")
    write_svg(out, build_svg(args.mode, args.accessibility))


if __name__ == "__main__":
    main()

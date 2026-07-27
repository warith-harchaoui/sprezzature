#!/usr/bin/env python3
"""
make_org-chart — publication-quality org chart as a hand-authored SVG.

An organization chart shows the reporting structure of a company: a
single chief executive at the top, a layer of vice-presidents beneath,
and the teams that roll up to each one. It answers "who reports to
whom, and where do the people sit?" more directly than a bullet list,
because the reader follows the elbow connectors down the hierarchy and
reads span-of-control (how many boxes hang off a node) and headcount
(printed in each box) at a glance.

Vega-Lite has no native node-link tree mark, so this figure is built as
an SVG string by hand rather than through ``vl_convert``. The layout is
a **top-down tidy tree**:

* every node sits on a row ("depth") fixed by its distance from the
  chief executive, so the whole VP layer lines up and the whole team
  layer lines up;
* leaves (teams) are packed left-to-right at an even pitch, and each
  parent is centred over the horizontal span of its children — the
  classic tidy layout that keeps the chart compact with no crossings;
* **connectors** are orthogonal elbows (down from the parent, across a
  shared bus, then down into each child) — the convention every org
  chart uses, so the structure reads as "reporting lines".

Each box is a rounded card printing the role on top and the team's
headcount beneath. Every VP owns a hue, and that hue tints the VP card,
its connector bus, and the left rule of each team card below it, so the
eye groups a division at a glance. Box widths are sized to the widest
line so nothing is cramped and nothing collides.

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, rounded
corners, a start-anchored takeaway title plus a one-line subtitle that
states the point.

Interaction (no JavaScript): every box carries a native ``<title>``
tooltip (role, division, headcount), and a CSS ``:hover`` / ``:focus``
rule lifts a whole division — the VP card, its bus, and its teams
brighten while the rest of the chart dims. "Isolate a division" is the
affordance an org chart invites, so ``interactive`` is true. A static
chart needs no motion, so ``animated`` is false.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/org-chart.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _svg import svg_open, xml_escape as escape  # noqa: E402
from _render import render_cli  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 2720
HEIGHT = 1180
MARGIN_LEFT = 64
MARGIN_RIGHT = 64
MARGIN_TOP = 210         # room for title + subtitle + row band label
MARGIN_BOTTOM = 104      # room for the footnote + total headcount strip

INK = "#1D1D1F"          # primary text
SUBINK = "#6E6E73"       # secondary text
HAIRLINE = "#E5E5EA"     # neutral hairline
CARD_BG = "#FFFFFF"      # team-card fill
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

# Box geometry. Cards are tall enough to carry a large role line plus a
# comfortable headcount caption so every label reads at a glance.
BOX_H = 92               # card height
LEAF_PITCH = 22          # horizontal gap between adjacent team cards
CONNECTOR = "#C7C7CC"    # neutral connector (unused branch colour fallback)


# ------------------------------------------------------------------
# The company (illustrative but plausible): a ~230-person software
# company. A chief executive sits over four vice-presidents — Product &
# Engineering, Revenue, Operations, and People — and each VP owns two
# to three teams. The takeaway the subtitle states: Product &
# Engineering carries nearly half the company, the classic shape of a
# product-led software business where the build function dominates.
#
# Each node is (id, role, headcount, parent_id or None for the CEO).
# For a leaf (team), headcount is that team's size. For a manager
# (CEO / VP) headcount is the office itself (the exec plus their direct
# staff); the division total is computed by summing the subtree.
# Declaration order fixes left-to-right sibling order.
# ------------------------------------------------------------------
Node = Tuple[str, str, int, Optional[str]]

NODES: List[Node] = [
    ("ceo", "Chief Executive", 3, None),

    # ---- Product & Engineering (the heavy division) ----
    ("vp_eng", "VP Product & Eng.", 5, "ceo"),
    ("t_platform", "Platform", 28, "vp_eng"),
    ("t_apps", "Applications", 34, "vp_eng"),
    ("t_design", "Design & Research", 18, "vp_eng"),
    ("t_data", "Data & ML", 22, "vp_eng"),

    # ---- Revenue ----
    ("vp_rev", "VP Revenue", 4, "ceo"),
    ("t_sales", "Sales", 26, "vp_rev"),
    ("t_success", "Customer Success", 19, "vp_rev"),
    ("t_mktg", "Marketing", 12, "vp_rev"),

    # ---- Operations ----
    ("vp_ops", "VP Operations", 4, "ceo"),
    ("t_finance", "Finance", 9, "vp_ops"),
    ("t_it", "IT & Security", 11, "vp_ops"),

    # ---- People ----
    ("vp_ppl", "VP People", 3, "ceo"),
    ("t_talent", "Talent", 8, "vp_ppl"),
    ("t_pops", "People Ops", 6, "vp_ppl"),
]

# Each VP owns a hue; the whole division inherits it.
_DIVISION_BASE: Dict[str, str] = {
    "vp_eng": "Blue",
    "vp_rev": "Orange",
    "vp_ops": "Purple",
    "vp_ppl": "Green",
}
_DIVISION_FALLBACK: Dict[str, str] = {
    "vp_eng": "#007AFF", "vp_rev": "#FF9500", "vp_ops": "#AF52DE", "vp_ppl": "#34C759",
}


def _division_colors(accessibility: str = "universal") -> Dict[str, str]:
    """Return the per-division hue map at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`;
        ``"universal"`` (default) is the identity.

    Returns
    -------
    dict of str to str
        ``{division_key: "#RRGGBB"}``.
    """
    palette = load_palette(accessibility)
    return {
        key: palette.get(base, _DIVISION_FALLBACK[key])
        for key, base in _DIVISION_BASE.items()
    }


PALETTE = load_palette()
DIVISION_COLOR: Dict[str, str] = _division_colors()
CEO_COLOR = INK

# Short division names for the legend / tooltips.
DIVISION_NAME: Dict[str, str] = {
    "vp_eng": "Product & Engineering",
    "vp_rev": "Revenue",
    "vp_ops": "Operations",
    "vp_ppl": "People",
}


# ------------------------------------------------------------------
# Tree model helpers
# ------------------------------------------------------------------
def _children_of() -> Dict[str, List[str]]:
    """Return ``{parent_id: [child_id, ...]}`` in declaration order."""
    kids: Dict[str, List[str]] = {}
    for node_id, _role, _hc, parent in NODES:
        if parent is not None:
            kids.setdefault(parent, []).append(node_id)
    return kids


def _parent_of() -> Dict[str, Optional[str]]:
    """Return ``{node_id: parent_id or None}``."""
    return {node_id: parent for node_id, _role, _hc, parent in NODES}


def _role_of() -> Dict[str, str]:
    """Return ``{node_id: role label}``."""
    return {node_id: role for node_id, role, _hc, _parent in NODES}


def _own_headcount() -> Dict[str, int]:
    """Return ``{node_id: the box's own printed headcount}``."""
    return {node_id: hc for node_id, _role, hc, _parent in NODES}


def _depth_of(node_id: str, parent: Dict[str, Optional[str]]) -> int:
    """Return the distance from ``node_id`` up to the chief executive."""
    depth = 0
    cur: Optional[str] = node_id
    while parent.get(cur) is not None:
        cur = parent[cur]
        depth += 1
    return depth


def _division_of(node_id: str, parent: Dict[str, Optional[str]]) -> Optional[str]:
    """Return the VP id (child-of-CEO) a node belongs to.

    The chief executive returns ``None``; every other node walks up
    until it hits a node whose parent is the chief executive.
    """
    cur: Optional[str] = node_id
    if cur == "ceo":
        return None
    while parent.get(cur) not in (None, "ceo"):
        cur = parent[cur]  # type: ignore[assignment]
    return cur


def _subtree_headcount() -> Dict[str, int]:
    """Return ``{node_id: total people in this node's subtree, inclusive}``."""
    kids = _children_of()
    own = _own_headcount()

    def total(node_id: str) -> int:
        return own[node_id] + sum(total(c) for c in kids.get(node_id, []))

    return {node_id: total(node_id) for node_id, _r, _h, _p in NODES}


def _lineage(node_id: str, parent: Dict[str, Optional[str]]) -> List[str]:
    """Return the CEO→node chain of ids (inclusive of both ends)."""
    chain: List[str] = []
    cur: Optional[str] = node_id
    while cur is not None:
        chain.append(cur)
        cur = parent.get(cur)
    return list(reversed(chain))


# ------------------------------------------------------------------
# Box sizing
# ------------------------------------------------------------------
def _text_width(label: str, font_size: float) -> float:
    """Rough advance-width estimate for a Roboto label at ``font_size``.

    ~0.56em per character is a safe average for Roboto's mixed-case
    metrics; good enough to size a card so text never clips.
    """
    return len(label) * font_size * 0.56


def _caption_of(
    node_id: str, depth: int, own_hc: Dict[str, int], sub_hc: Dict[str, int]
) -> str:
    """Return the headcount caption printed on the second line of a card."""
    if node_id == "ceo":
        return f"{sub_hc[node_id]} people total"
    if depth == 1:
        return f"{sub_hc[node_id]} people"
    return f"{own_hc[node_id]} people"


def _box_width(
    node_id: str,
    role_of: Dict[str, str],
    depth: int,
    own_hc: Dict[str, int],
    sub_hc: Dict[str, int],
) -> float:
    """Return the card width for a node, sized to its widest line.

    The role sits on line 1 (23-25 px) and the headcount caption on line
    2 (17 px, mono ≈ 0.60em/char), so the card is sized to whichever is
    wider, plus horizontal padding. Manager cards (depth ≤ 1) get a touch
    more padding so they read as the anchor of their level; team cards
    add room for the coloured left rule.
    """
    role = role_of[node_id]
    role_fs = 25.0 if depth <= 1 else 23.0
    pad_x = 30 if depth <= 1 else 24
    rule_room = 0.0 if depth <= 1 else 26.0
    role_w = _text_width(role, role_fs)
    caption = _caption_of(node_id, depth, own_hc, sub_hc)
    caption_w = len(caption) * 17.0 * 0.60  # mono advance
    content_w = max(role_w, caption_w) + rule_room
    return max(content_w + 2 * pad_x, 168.0)


# ------------------------------------------------------------------
# Top-down tidy layout
# ------------------------------------------------------------------
def _compute_geometry(accessibility: str = "universal") -> Dict[str, dict]:
    """Place every node with a top-down tidy tree layout.

    Depth fixes the row (y); a post-order pass gives each leaf the next
    slot along x and centres every parent over the span of its children.
    Leaf x-slots are sized by the *actual* card widths so wide cards get
    more room and adjacent cards keep a constant visual gap.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`;
        ``"universal"`` (default) is the identity.

    Returns
    -------
    dict
        ``{node_id: {"cx", "y_top", "w", "depth", "division", "color"}}``
        where ``cx`` is the horizontal centre of the card and ``y_top``
        its top edge, both in SVG pixels.
    """
    kids = _children_of()
    parent = _parent_of()
    role_of = _role_of()
    own_hc = _own_headcount()
    sub_hc = _subtree_headcount()

    depth = {n: _depth_of(n, parent) for n, _r, _h, _p in NODES}
    width = {
        n: _box_width(n, role_of, depth[n], own_hc, sub_hc)
        for n, _r, _h, _p in NODES
    }

    # --- horizontal packing of the leaf row (the teams) ---
    # Walk leaves left-to-right, advancing a running x cursor by each
    # card's own width plus a fixed gap, so nothing ever overlaps.
    leaves = [n for n, _r, _h, _p in NODES if n not in kids]
    plot_left = MARGIN_LEFT
    cursor = plot_left
    leaf_cx: Dict[str, float] = {}
    for i, leaf in enumerate(leaves):
        w = width[leaf]
        leaf_cx[leaf] = cursor + w / 2.0
        cursor += w + (LEAF_PITCH if i < len(leaves) - 1 else 0)
    content_right = cursor
    # Centre the whole tree in the canvas by shifting every leaf equally.
    content_left = plot_left
    plot_right = WIDTH - MARGIN_RIGHT
    shift = ((plot_right - content_right) - (content_left - plot_left)) / 2.0
    shift = max(shift, 0.0)
    for leaf in leaves:
        leaf_cx[leaf] += shift

    # --- centre each parent over the span of its children ---
    cx: Dict[str, float] = dict(leaf_cx)

    def place(node_id: str) -> float:
        children = kids.get(node_id, [])
        if not children:
            return cx[node_id]
        xs = [place(c) for c in children]
        cx[node_id] = (xs[0] + xs[-1]) / 2.0
        return cx[node_id]

    place("ceo")

    # --- rows (depth → y) evenly spaced across the plot band ---
    plot_top = MARGIN_TOP
    plot_bottom = HEIGHT - MARGIN_BOTTOM
    max_depth = max(depth.values())
    if max_depth == 0:
        row_y = {0: plot_top}
    else:
        band = plot_bottom - plot_top - BOX_H
        row_y = {d: plot_top + d * band / max_depth for d in range(max_depth + 1)}

    division_color = _division_colors(accessibility)
    geometry: Dict[str, dict] = {}
    for node_id, _role, _hc, _p in NODES:
        d = depth[node_id]
        div = _division_of(node_id, parent)
        color = CEO_COLOR if node_id == "ceo" else division_color.get(div or "", SUBINK)
        geometry[node_id] = {
            "cx": cx[node_id],
            "y_top": row_y[d],
            "w": width[node_id],
            "depth": d,
            "division": div,
            "color": color,
        }
    return geometry


# ------------------------------------------------------------------
# Connector geometry (orthogonal elbows through a shared bus)
# ------------------------------------------------------------------
def _bus_y(geometry: Dict[str, dict], parent_id: str) -> float:
    """Return the y of the horizontal bus between a parent and its children.

    The bus sits midway between the parent's bottom edge and the
    children's top edge, so the two drops are visually balanced.
    """
    kids = _children_of()
    children = kids[parent_id]
    parent_bottom = geometry[parent_id]["y_top"] + BOX_H
    child_top = geometry[children[0]]["y_top"]
    return (parent_bottom + child_top) / 2.0


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def _fmt(v: float) -> str:
    """Format a coordinate compactly."""
    return f"{v:.1f}"


def _emit_connectors(
    parts: List[str],
    geometry: Dict[str, dict],
    parent_id: str,
    *,
    interactive: bool,
) -> None:
    """Emit the orthogonal connector set from a parent to all its children.

    One stub drops from the parent's bottom edge to the bus; the bus
    spans the children's centres; a stub drops from the bus into each
    child's top edge. Coloured by the division hue so a branch reads as
    a unit. Rounded joins keep the elbows soft, matching the cards.
    """
    kids = _children_of()
    children = kids.get(parent_id, [])
    if not children:
        return
    bus_y = _bus_y(geometry, parent_id)
    gp = geometry[parent_id]
    parent_cx = gp["cx"]
    parent_bottom = gp["y_top"] + BOX_H

    # The children under a VP share the VP's hue; the CEO's four stubs to
    # the VPs each take the destination VP's hue so every line is owned.
    xs = [geometry[c]["cx"] for c in children]
    bus_left = min(xs + [parent_cx])
    bus_right = max(xs + [parent_cx])

    op = "" if interactive else ""

    # Parent drop to the bus. When the parent is the CEO the drop is
    # neutral ink (it fans into four coloured buses just below); otherwise
    # it takes the division colour.
    drop_color = INK if parent_id == "ceo" else gp["color"]
    parts.append(
        f'<path class="wire" d="M{_fmt(parent_cx)},{_fmt(parent_bottom)} '
        f'L{_fmt(parent_cx)},{_fmt(bus_y)}" fill="none" stroke="{drop_color}" '
        f'stroke-width="3.2" stroke-linecap="round"{op}/>'
    )

    if parent_id == "ceo":
        # Draw each CEO→VP leg as its own coloured elbow (bus segment +
        # drop) so the four divisions are colour-owned from the top. Each leg
        # takes the destination VP's division class so the OS-adaptive media
        # rules can retint it (the class outranks the inline stroke, but only
        # inside a media query, so the default render is unchanged).
        for c in children:
            gc = geometry[c]
            col = gc["color"]
            ccx = gc["cx"]
            ctop = gc["y_top"]
            # horizontal from parent centre to child centre along the bus,
            # then straight down into the child.
            parts.append(
                f'<path class="wire div-{c}" d="M{_fmt(parent_cx)},{_fmt(bus_y)} '
                f'L{_fmt(ccx)},{_fmt(bus_y)} L{_fmt(ccx)},{_fmt(ctop)}" '
                f'fill="none" stroke="{col}" stroke-width="3.2" '
                f'stroke-linecap="round" stroke-linejoin="round"{op}/>'
            )
        return

    # VP → teams: a single coloured bus plus one drop per child, all carrying
    # the parent VP's division class for the OS-adaptive retint.
    col = gp["color"]
    div_cls = f" div-{parent_id}"
    parts.append(
        f'<path class="wire{div_cls}" d="M{_fmt(bus_left)},{_fmt(bus_y)} '
        f'L{_fmt(bus_right)},{_fmt(bus_y)}" fill="none" stroke="{col}" '
        f'stroke-width="3.2" stroke-linecap="round"{op}/>'
    )
    for c in children:
        gc = geometry[c]
        ccx = gc["cx"]
        ctop = gc["y_top"]
        parts.append(
            f'<path class="wire{div_cls}" d="M{_fmt(ccx)},{_fmt(bus_y)} '
            f'L{_fmt(ccx)},{_fmt(ctop)}" fill="none" stroke="{col}" '
            f'stroke-width="3.2" stroke-linecap="round"{op}/>'
        )


def _emit_box(
    parts: List[str],
    geometry: Dict[str, dict],
    role_of: Dict[str, str],
    own_hc: Dict[str, int],
    sub_hc: Dict[str, int],
    node_id: str,
) -> None:
    """Emit one org-chart box: a rounded card with role + headcount.

    * The CEO card is a filled ink pill (the anchor of the chart).
    * VP cards are filled in their division hue, white text, and print
      the whole division's headcount as the caption.
    * Team cards are white with a coloured left rule and ink text, and
      print their own headcount.
    """
    g = geometry[node_id]
    role = role_of[node_id]
    depth = g["depth"]
    color = g["color"]
    w = g["w"]
    x_left = g["cx"] - w / 2.0
    y_top = g["y_top"]
    cx = g["cx"]
    # A stable per-division CSS class so the OS-adaptive @media rules can
    # retint the coloured mark (VP card fill / team left-rule fill). The CEO
    # carries no division (its ink is not a division hue), so it is unclassed.
    div = g["division"]
    div_cls = f" div-{div}" if div else ""

    if node_id == "ceo":
        headcount = sub_hc[node_id]
        caption = f"{headcount} people total"
        tip = f"Chief Executive — {headcount} people across the company"
    elif depth == 1:
        headcount = sub_hc[node_id]
        caption = f"{headcount} people"
        tip = f"{DIVISION_NAME.get(node_id, role)} — {headcount} people"
    else:
        headcount = own_hc[node_id]
        div = g["division"]
        caption = f"{headcount} people"
        tip = f"{role} — {headcount} people — {DIVISION_NAME.get(div or '', '')}"

    if depth <= 1:
        # Filled card — CEO ink, VPs their hue. White role + white caption.
        parts.append(
            f'<g class="box">'
            f'<rect class="hit{div_cls}" tabindex="0" x="{_fmt(x_left)}" y="{_fmt(y_top)}" '
            f'width="{_fmt(w)}" height="{BOX_H}" rx="18" fill="{color}">'
            f'<title>{escape(tip)}</title></rect>'
            f'<text x="{_fmt(cx)}" y="{_fmt(y_top + 40)}" text-anchor="middle" '
            f'font-size="25" font-weight="700" fill="#FFFFFF">{escape(role)}</text>'
            f'<text x="{_fmt(cx)}" y="{_fmt(y_top + 70)}" text-anchor="middle" '
            f'font-family="{FONT_MONO}" font-size="17" fill="#FFFFFF" '
            f'fill-opacity="0.92">{escape(caption)}</text>'
            f'</g>'
        )
    else:
        # White team card with a coloured left rule.
        rule_w = 8.0
        parts.append(
            f'<g class="box">'
            f'<rect x="{_fmt(x_left)}" y="{_fmt(y_top)}" width="{_fmt(w)}" '
            f'height="{BOX_H}" rx="16" fill="{CARD_BG}" stroke="{HAIRLINE}" '
            f'stroke-width="1.5"><title>{escape(tip)}</title></rect>'
            f'<path d="M{_fmt(x_left + rule_w)},{_fmt(y_top)} '
            f'L{_fmt(x_left)},{_fmt(y_top)} '
            f'Q{_fmt(x_left)},{_fmt(y_top)} {_fmt(x_left)},{_fmt(y_top + 16)} '
            f'L{_fmt(x_left)},{_fmt(y_top + BOX_H - 16)} '
            f'Q{_fmt(x_left)},{_fmt(y_top + BOX_H)} {_fmt(x_left + 16)},{_fmt(y_top + BOX_H)} '
            f'L{_fmt(x_left + rule_w)},{_fmt(y_top + BOX_H)} Z" class="{div_cls.strip()}" fill="{color}"/>'
            f'<text x="{_fmt(x_left + rule_w + 20)}" y="{_fmt(y_top + 40)}" '
            f'font-size="23" font-weight="600" fill="{INK}">{escape(role)}</text>'
            f'<text x="{_fmt(x_left + rule_w + 20)}" y="{_fmt(y_top + 68)}" '
            f'font-family="{FONT_MONO}" font-size="17" fill="{SUBINK}">'
            f'{escape(caption)}</text>'
            f'</g>'
        )


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full org-chart SVG document as a string.

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
    geometry = _compute_geometry(accessibility)
    kids = _children_of()
    role_of = _role_of()
    own_hc = _own_headcount()
    sub_hc = _subtree_headcount()

    total = sub_hc["ceo"]
    eng_total = sub_hc["vp_eng"]
    eng_pct = round(100 * eng_total / total)

    parts: List[str] = []

    # --- accessible header ---
    title_txt = "One division carries nearly half the company"
    subtitle_txt = (
        f"Product & Engineering is {eng_pct}% of headcount, the classic shape "
        f"of a product-led software company. Illustrative org of {total} people."
    )
    desc_txt = (
        "Top-down organization chart of a software company of about "
        f"{total} people. The chief executive sits over four vice-presidents: "
        "Product & Engineering, Revenue, Operations, and People. Each division "
        "card is tinted its own colour and prints its total headcount; team "
        "cards below print their own size. Product & Engineering, with four "
        f"teams, is the largest division at {eng_pct}% of the company."
    )
    parts.append(svg_open(WIDTH, HEIGHT, "org-title", "org-desc", font_family=FONT))
    parts.append(f'<title id="org-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="org-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hover/focus a division lifts it, dims the rest ---
    # OS-adaptive overrides (additive; the default render is unchanged because
    # every rule lives inside a media query and a class rule only outranks the
    # inline colour when its media query is active). Under prefers-contrast the
    # four division hues deepen to their high-contrast variants on BOTH fill
    # (VP cards, team left-rules) and stroke (connector wires). Under forced
    # colours everything classed drops to the system CanvasText line-art — safe
    # here because an org chart's identity is carried by position, box role
    # labels, and headcounts, not by colour. The helper forces `fill` for the
    # classed selectors; the wires need their stroke forced too, hence the
    # extra ``.wire{stroke:CanvasText}`` rule.
    division_color = _division_colors(accessibility)
    os_media = os_adaptive_style(
        {
            ".div-vp_eng": division_color["vp_eng"],
            ".div-vp_rev": division_color["vp_rev"],
            ".div-vp_ops": division_color["vp_ops"],
            ".div-vp_ppl": division_color["vp_ppl"],
        },
        role="both",
        forced=True,
        extra_forced=".wire{stroke:CanvasText;}",
    )
    parts.append(
        "<style>"
        ".box,.wire{transition:opacity .16s ease}"
        # Hovering the chart dims every division, then the hovered/focused
        # division group is brought back to full strength.
        "#org:hover .division .box,#org:hover .division .wire{opacity:.22}"
        "#org .division:hover .box,#org .division:hover .wire,"
        "#org .division:focus-within .box,#org .division:focus-within .wire{opacity:1}"
        ".hit:focus{outline:none}"
        + os_media
        # Additive OS dark mode. Default ink_map flips paper #FFFFFF and the two
        # ink tiers, so white team cards become dark cards and their ink text
        # becomes off-white — good. But two figure-specific fixes are needed:
        # (1) the CEO card is a filled ink pill (fill #1D1D1F) with white text;
        #     the blanket #1D1D1F->off-white flip would leave white-on-white, so
        #     the CEO rect (class exactly "hit") is pinned back to a dark pill.
        # (2) the team-card hairline border darkens to read on the dark surface.
        # Division hues (VP cards, left rules, wires) are data, left alone.
        + os_dark_style(
            extra=(
                '[class="hit"]{fill:#2C2C30;}'
                '[stroke="#E5E5EA"]{stroke:#3E3E44;}'
            )
        )
        + "</style>"
    )

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="{MARGIN_LEFT}" y="74" font-size="44" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    sub_lines = _wrap(subtitle_txt, 118)
    for i, line in enumerate(sub_lines):
        parts.append(
            f'<text x="{MARGIN_LEFT}" y="{118 + i * 34}" font-size="25" '
            f'fill="{SUBINK}">{escape(line)}</text>'
        )

    # --- row band labels down the left gutter ---
    band_names = ["Executive", "Divisions", "Teams"]
    for d, name in enumerate(band_names):
        gy = next((g["y_top"] for g in geometry.values() if g["depth"] == d), None)
        if gy is None:
            continue
        parts.append(
            f'<text x="{MARGIN_LEFT}" y="{_fmt(gy - 22)}" font-size="16" '
            f'font-weight="700" letter-spacing="1.6" fill="{SUBINK}">'
            f'{escape(name.upper())}</text>'
        )

    # ------------------------------------------------------------------
    # Draw the chart. Wrap each division (a VP + its teams + their wires)
    # in a <g class="division"> so a CSS :hover / :focus can isolate it.
    # The CEO box and the CEO→VP wires sit in a shared base group.
    # ------------------------------------------------------------------
    parts.append('<g id="org">')

    # Base layer: CEO box + the four CEO→VP legs (each already coloured).
    parts.append('<g id="base">')
    _emit_connectors(parts, geometry, "ceo", interactive=False)
    _emit_box(parts, geometry, role_of, own_hc, sub_hc, "ceo")
    parts.append("</g>")

    # One group per division.
    for vp in ("vp_eng", "vp_rev", "vp_ops", "vp_ppl"):
        dname = DIVISION_NAME[vp]
        parts.append(
            f'<g class="division" role="group" aria-label="{escape(dname)} division">'
        )
        # VP → team connectors first (so cards sit on top).
        _emit_connectors(parts, geometry, vp, interactive=True)
        # VP card, then its team cards.
        _emit_box(parts, geometry, role_of, own_hc, sub_hc, vp)
        for team in kids.get(vp, []):
            _emit_box(parts, geometry, role_of, own_hc, sub_hc, team)
        parts.append("</g>")

    parts.append("</g>")  # #org

    # --- footnote ---
    parts.append(
        f'<text x="{MARGIN_LEFT}" y="{HEIGHT - 34}" font-size="19" '
        f'fill="{SUBINK}">Each box shows role and headcount · division cards '
        f'total their teams · hover or focus a division to isolate it</text>'
    )

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def _wrap(text: str, max_chars: int) -> List[str]:
    """Greedy word-wrap ``text`` to lines of at most ``max_chars``."""
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
    return lines


def main() -> None:
    """Write the org-chart SVG to the skill's example asset folder.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "org-chart",
        build_svg,
        description="Write the house-style org-chart SVG example.",
    )


if __name__ == "__main__":
    main()

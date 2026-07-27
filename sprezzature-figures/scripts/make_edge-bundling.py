#!/usr/bin/env python3
"""
make_edge-bundling — hierarchical edge bundling as a hand-authored SVG.

Hierarchical edge bundling lays the leaves of a tree on the rim of a
circle and draws every relation between two leaves not as a straight
chord but as a smooth curve that is *pulled toward the leaves' common
ancestor* inside the tree. Relations that share a route bundle together
into thick visual cables, so a hairball of hundreds of crossing lines
collapses into a handful of legible flows between subsystems. It answers
"which parts of a system talk to which, and where are the heavy
cross-cutting couplings?" far better than a straight-line node-link
graph, whose edges cross indiscriminately and hide the structure.

Vega-Lite has no bundling mark (the curve routing needs a tree walk and
a B-spline), so this figure is built as an SVG string by hand rather
than through ``vl_convert``. The layout is the classic Holten (2006) one:

* **Hierarchy** — a two-level tree: a root, one node per subsystem, and
  one leaf per module. Leaves are placed on a circle, grouped by
  subsystem, with a small angular gap between groups. Each interior
  node sits on an inner radius at the angular centre of its children.
* **Bundled edges** — for a dependency from module *u* to module *v*,
  the control polyline is ``u → (u's parent) → (root) → (v's parent) →
  v``; a Catmull-Rom-to-Bézier spline is fit through those control
  points with a tension that relaxes the curve toward the straight
  chord. Two edges between the same pair of subsystems share three of
  their five control points, so they bundle.
* **Colour** — a dependency is drawn as a gradient from its source
  subsystem hue to its target subsystem hue, so a cable's direction is
  legible from the colour drift along it.

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, a
start-anchored title plus a one-line takeaway subtitle.

Interaction (no JavaScript): every edge and every leaf label carries a
native ``<title>`` tooltip, and a CSS ``:hover`` / ``:focus`` rule dims
the rest of the diagram so the hovered dependency — or every dependency
touching a hovered module — pops. This is the "hover to trace" affordance
that suits bundling, where the whole point is that individual threads are
otherwise hard to follow inside a cable. The figure is otherwise static
(bundling does not benefit from animation), so ``animated`` is false and
``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/edge-bundling.svg``.

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
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _render import render_cli  # noqa: E402
from _svg import svg_open  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1180
HEIGHT = 1240
CX = WIDTH / 2.0
CY = HEIGHT / 2.0 + 54       # nudge down to leave room for the title block
R_LEAF = 388                 # radius of the leaf ring (module dots)
R_PARENT = 218               # radius interior subsystem nodes sit on
LABEL_PAD = 20               # radial gap between a leaf dot and its label
GROUP_GAP_DEG = 8.0          # angular gap between subsystem groups
# Bundling strength for the cross-subsystem "root" hop: the shared
# control point is placed this fraction of the way from the two parents'
# midpoint toward the circle centre. Small = cables hug the parent ring
# and the centre stays clear for the annotation; large = everything
# collapses onto the centre (an unreadable star). A moderate pull makes
# edges sharing a subsystem pair collapse into one visible cable — the
# defining mark of the technique — while keeping the centre readable.
CENTRE_PULL = 0.52

INK = "#1D1D1F"              # primary text
SUBINK = "#6E6E73"           # secondary text
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"


# ------------------------------------------------------------------
# The story (illustrative but plausible): the internal module-dependency
# graph of a mid-size web application, with modules grouped by the
# subsystem they belong to. An edge u -> v means "module u imports /
# calls module v". The takeaway: almost every subsystem reaches into the
# Auth subsystem, and Billing reaches deep into Data — the two couplings
# a refactor has to untangle first.
# ------------------------------------------------------------------
# Each subsystem maps to its list of module (leaf) names, in ring order.
SUBSYSTEMS: List[Tuple[str, List[str]]] = [
    ("Web UI",   ["Router", "Views", "Forms", "Widgets"]),
    ("API",      ["Gateway", "Handlers", "Schemas"]),
    ("Auth",     ["Login", "Tokens", "Roles"]),
    ("Billing",  ["Invoices", "Payments", "Plans"]),
    ("Data",     ["Models", "Queries", "Cache", "Migrations"]),
    ("Infra",    ["Config", "Logging", "Metrics"]),
]

# Brand hue per subsystem — the leaf colour and one end of every edge's
# gradient.
def _subsys_color(accessibility: str = "universal") -> Dict[str, str]:
    """Map each subsystem to its brand hue at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        The palette accessibility level threaded into :func:`load_palette`;
        ``"universal"`` (default) is the colour-vision-safe standard.

    Returns
    -------
    dict of str to str
        ``{subsystem_name: hex}`` for every subsystem.
    """
    palette = load_palette(accessibility)
    return {
        "Web UI":  palette.get("Blue", "#007AFF"),
        "API":     palette.get("Teal", "#5AC8FA"),
        "Auth":    palette.get("Red", "#FF3B30"),
        "Billing": palette.get("Orange", "#FF9500"),
        "Data":    palette.get("Green", "#34C759"),
        "Infra":   palette.get("Purple", "#AF52DE"),
    }


PALETTE = load_palette()
SUBSYS_COLOR: Dict[str, str] = _subsys_color()


def _slug(name: str) -> str:
    """Return a CSS-class-safe slug for a subsystem name.

    Lower-cases and replaces any run of non-alphanumeric characters with a
    single hyphen, so ``"Web UI"`` becomes ``"web-ui"`` — a stable hook for
    the per-subsystem OS-adaptive ``@media`` overrides.

    Parameters
    ----------
    name : str
        The subsystem display name.

    Returns
    -------
    str
        The slugified class suffix.
    """
    out = []
    prev_dash = False
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")

# Dependencies as (source module, target module). Chosen so that the two
# heavy cross-cutting cables — everyone -> Auth, and Billing -> Data —
# are visible, while incidental edges keep the graph plausible.
EDGES: List[Tuple[str, str]] = [
    # Web UI leans on API + Auth.
    ("Router", "Gateway"),
    ("Views", "Handlers"),
    ("Forms", "Login"),
    ("Widgets", "Handlers"),
    ("Views", "Tokens"),
    # API leans on Auth + Data.
    ("Gateway", "Tokens"),
    ("Handlers", "Roles"),
    ("Handlers", "Queries"),
    ("Schemas", "Models"),
    ("Gateway", "Login"),
    # Billing reaches deep into Data + touches Auth.
    ("Invoices", "Queries"),
    ("Payments", "Models"),
    ("Payments", "Cache"),
    ("Plans", "Models"),
    ("Invoices", "Roles"),
    ("Payments", "Tokens"),
    # Auth itself sits on Data + Infra.
    ("Login", "Queries"),
    ("Tokens", "Cache"),
    ("Roles", "Models"),
    # Data on Infra.
    ("Queries", "Metrics"),
    ("Migrations", "Config"),
    # Cross-cutting Infra reach: everything logs.
    ("Handlers", "Logging"),
    ("Payments", "Logging"),
    ("Login", "Logging"),
    ("Router", "Config"),
]


# ------------------------------------------------------------------
# Geometry helpers
# ------------------------------------------------------------------
def _polar(radius: float, deg: float) -> Tuple[float, float]:
    """Convert (radius, angle-in-degrees) to an SVG (x, y) point.

    Angle 0 points straight up (12 o'clock) and increases clockwise, the
    orientation readers expect from a circular diagram.

    Parameters
    ----------
    radius : float
        Distance from the centre in pixels.
    deg : float
        Angle in degrees, 0 = up, growing clockwise.

    Returns
    -------
    tuple of float
        The ``(x, y)`` point in SVG pixel coordinates.
    """
    rad = math.radians(deg - 90.0)  # -90 so 0 deg is up
    return CX + radius * math.cos(rad), CY + radius * math.sin(rad)


def _spline_path(points: List[Tuple[float, float]]) -> str:
    """Return an SVG ``d`` for a smooth curve through control points.

    Fits a Catmull-Rom spline through ``points`` and converts each
    segment to a cubic Bézier. Catmull-Rom passes through every control
    point, so the curve honours the ``leaf → parent → root → parent →
    leaf`` routing exactly while staying smooth — that routing is what
    makes edges sharing a subsystem pair bundle together.

    Parameters
    ----------
    points : list of tuple of float
        The control polyline, at least two points.

    Returns
    -------
    str
        An open SVG path (``M`` … ``C`` …) through the points.
    """
    if len(points) < 2:
        raise ValueError("need at least two points for a spline")
    pts = points
    d = [f"M{pts[0][0]:.2f},{pts[0][1]:.2f}"]
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[0]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[n - 1]
        # Catmull-Rom -> Bézier control points (uniform, 1/6 tangents).
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        d.append(
            f"C{c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {p2[0]:.2f},{p2[1]:.2f}"
        )
    return " ".join(d)


# ------------------------------------------------------------------
# Hierarchy layout
# ------------------------------------------------------------------
def _compute_layout(
    subsys_color: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """Place every leaf on the ring and every subsystem node inside it.

    The circle's angular budget (360 deg minus the inter-group gaps) is
    split across subsystems in proportion to how many modules each holds,
    so every module leaf gets an equal angular share. Each subsystem's
    interior node sits at radius :data:`R_PARENT`, at the angular centre
    of its leaves.

    Parameters
    ----------
    subsys_color : dict of str to str, optional
        ``{subsystem_name: hex}`` colour map; defaults to the module-level
        :data:`SUBSYS_COLOR` (the universal palette).

    Returns
    -------
    leaves : dict
        ``{module_name: {"subsys", "deg", "x", "y", "color"}}``.
    parents : dict
        ``{subsystem_name: {"deg", "x", "y", "color", "n"}}``.
    """
    if subsys_color is None:
        subsys_color = SUBSYS_COLOR
    total_leaves = sum(len(mods) for _, mods in SUBSYSTEMS)
    n_groups = len(SUBSYSTEMS)
    usable = 360.0 - GROUP_GAP_DEG * n_groups
    deg_per_leaf = usable / total_leaves

    leaves: Dict[str, dict] = {}
    parents: Dict[str, dict] = {}
    cursor = GROUP_GAP_DEG / 2.0
    for subsys, mods in SUBSYSTEMS:
        color = subsys_color[subsys]
        group_start = cursor
        for mod in mods:
            # Centre the leaf inside its own angular cell.
            mid = cursor + deg_per_leaf / 2.0
            lx, ly = _polar(R_LEAF, mid)
            leaves[mod] = {
                "subsys": subsys,
                "deg": mid,
                "x": lx,
                "y": ly,
                "color": color,
            }
            cursor += deg_per_leaf
        group_end = cursor
        pmid = (group_start + group_end) / 2.0
        px, py = _polar(R_PARENT, pmid)
        parents[subsys] = {
            "deg": pmid,
            "x": px,
            "y": py,
            "color": color,
            "n": len(mods),
        }
        cursor += GROUP_GAP_DEG
    return leaves, parents


def _edge_control_points(
    u: str, v: str, leaves: Dict[str, dict], parents: Dict[str, dict]
) -> List[Tuple[float, float]]:
    """Build the bundling control polyline for a dependency ``u -> v``.

    The route is ``u → parent(u) → hub → parent(v) → v``. The hub
    control point sits at the midpoint of the two parents, pulled toward
    the circle centre by :data:`CENTRE_PULL` — a small pull, so each
    subsystem pair keeps its own cable lane out near the parent ring
    instead of every cable collapsing onto the singular centre (which
    would make them indistinguishable and bury the centre annotation).
    When both endpoints live in the same subsystem the hub hop is
    dropped — the curve just bows gently through the shared parent.

    Parameters
    ----------
    u, v : str
        Source and target module names.
    leaves, parents : dict
        Layout dicts from :func:`_compute_layout`.

    Returns
    -------
    list of tuple of float
        The control points, leaf-to-leaf.
    """
    su = leaves[u]["subsys"]
    sv = leaves[v]["subsys"]
    pu = parents[su]
    pv = parents[sv]
    p_u = (leaves[u]["x"], leaves[u]["y"])
    p_v = (leaves[v]["x"], leaves[v]["y"])
    p_pu = (pu["x"], pu["y"])
    p_pv = (pv["x"], pv["y"])

    if su == sv:
        # Same subsystem: leaf -> parent -> leaf, a shallow bow.
        return [p_u, p_pu, p_v]

    # Cross-subsystem route: leaf -> parent -> hub -> parent -> leaf. Two
    # extra control points sit just inside each parent, on the line from
    # the parent toward the shared hub, so every cable from a given
    # subsystem pair leaves its parent along the *same* tangent and the
    # edges physically overlap into one visible cable near the ring — the
    # bundling that defines the technique. The hub is the two parents'
    # midpoint pulled toward the centre by CENTRE_PULL.
    mid_parents = ((p_pu[0] + p_pv[0]) / 2.0, (p_pu[1] + p_pv[1]) / 2.0)
    hub = (
        mid_parents[0] + (CX - mid_parents[0]) * CENTRE_PULL,
        mid_parents[1] + (CY - mid_parents[1]) * CENTRE_PULL,
    )
    # A shared waypoint between each parent and the hub. Because it is a
    # function of (su, sv) only, every edge in the pair passes through the
    # same two waypoints and tightens into one cable.
    wu = (p_pu[0] + (hub[0] - p_pu[0]) * 0.42, p_pu[1] + (hub[1] - p_pu[1]) * 0.42)
    wv = (p_pv[0] + (hub[0] - p_pv[0]) * 0.42, p_pv[1] + (hub[1] - p_pv[1]) * 0.42)
    return [p_u, p_pu, wu, hub, wv, p_pv, p_v]


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full edge-bundling SVG document as a string.

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
        A complete, standalone SVG document.
    """
    subsys_color = _subsys_color(accessibility)
    leaves, parents = _compute_layout(subsys_color)

    title_txt = "Every subsystem reaches into Auth, and Billing burrows into Data"
    subtitle_txt = (
        "Module dependencies in a web app, bundled by subsystem (illustrative data)"
    )
    desc_txt = (
        "Hierarchical edge-bundling diagram of the module-dependency graph of a "
        "web application. Modules sit on a circle grouped into six subsystems "
        "(Web UI, API, Auth, Billing, Data, Infra); each dependency between two "
        "modules is drawn as a smooth curve pulled toward the tree's common "
        "ancestor so that dependencies between the same two subsystems bundle "
        "into a single cable. The thickest cables run from every subsystem into "
        "Auth and from Billing into Data, marking the couplings a refactor must "
        "untangle first."
    )

    # Count edges per source subsystem so a source's cables draw thickest
    # first (thin threads layer cleanly on top).
    parts: List[str] = []
    parts.append(svg_open(WIDTH, HEIGHT, "eb-title", "eb-desc", font_family=FONT))
    parts.append(f'<title id="eb-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="eb-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hover / focus one edge (or one module) dims the rest ---
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside an @media query, and the class only
    # outranks the inline leaf/legend fill once the query matches). The six
    # subsystem hues deepen to their high-contrast versions under
    # prefers-contrast, on the leaf dots and their legend swatches. forced=True
    # is safe: leaves are grouped by subsystem around the ring (position) and
    # every module carries an always-visible text label, so identity survives
    # with no colour. The source→target edge gradients are left universal — they
    # are a redundant directional cue on top of the labelled leaves, and a
    # gradient stroke cannot be meaningfully re-tinted by a single class rule.
    subsys_series = {
        f".leaf-{_slug(subsys)}": subsys_color[subsys] for subsys, _ in SUBSYSTEMS
    }
    parts.append(
        "<style>"
        ".edge{transition:opacity .18s ease,stroke-width .18s ease}"
        ".leaf,.leaf-dot{transition:opacity .18s ease}"
        # Hovering the edge layer — or keyboard-focusing any edge inside
        # it (:focus-within) — fades every edge; the hovered / focused
        # edge returns to full opacity and thickens so the traced thread
        # separates from its cable. Covering both pointer and keyboard
        # keeps the trace affordance available without a mouse.
        "#edges:hover .edge,#edges:focus-within .edge{opacity:.08}"
        "#edges .edge:hover,#edges .edge:focus{opacity:1;stroke-width:5}"
        # Focusing / hovering a module dot enlarges it so keyboard users
        # can see which leaf they landed on.
        "#leaves .leaf:hover .leaf-dot,#leaves .leaf:focus .leaf-dot{r:9}"
        ".edge:focus,.leaf:focus{outline:none}"
        + os_adaptive_style(subsys_series, role="fill", forced=True)
        # Additive dark mode: flip paper + the two ink tiers (data hues untouched).
        + os_dark_style()
        + "</style>"
    )

    # --- gradient defs: one per (source subsystem, target subsystem) pair ---
    grad_ids: Dict[Tuple[str, str], str] = {}
    parts.append("<defs>")
    seen_pairs: set[Tuple[str, str]] = set()
    for u, v in EDGES:
        su = leaves[u]["subsys"]
        sv = leaves[v]["subsys"]
        key = (su, sv)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        gid = f"grad-{len(grad_ids)}"
        grad_ids[key] = gid
        c0 = subsys_color[su]
        c1 = subsys_color[sv]
        # A userSpaceOnUse gradient down the rough source->target axis so
        # colour drifts from the source hue to the target hue along the
        # cable, giving each edge a readable direction.
        pu = parents[su]
        pv = parents[sv]
        parts.append(
            f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
            f'x1="{pu["x"]:.1f}" y1="{pu["y"]:.1f}" '
            f'x2="{pv["x"]:.1f}" y2="{pv["y"]:.1f}">'
            f'<stop offset="0" stop-color="{c0}"/>'
            f'<stop offset="1" stop-color="{c1}"/>'
            f'</linearGradient>'
        )
    parts.append("</defs>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="46" y="60" font-size="31" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="46" y="94" font-size="19" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    # --- edges (drawn first, under the leaves) ---
    # Sort by geodesic length descending so long cross-diagram cables sit
    # underneath the short local threads.
    def _edge_len(e: Tuple[str, str]) -> float:
        u, v = e
        return math.dist((leaves[u]["x"], leaves[u]["y"]),
                         (leaves[v]["x"], leaves[v]["y"]))

    parts.append('<g id="edges" fill="none">')
    for u, v in sorted(EDGES, key=_edge_len, reverse=True):
        pts = _edge_control_points(u, v, leaves, parents)
        d = _spline_path(pts)
        su = leaves[u]["subsys"]
        sv = leaves[v]["subsys"]
        gid = grad_ids[(su, sv)]
        tip = f"{u} ({su}) → {v} ({sv})"
        parts.append(
            f'<path class="edge" tabindex="0" role="img" '
            f'aria-label="{escape(tip)}" d="{d}" '
            f'stroke="url(#{gid})" stroke-width="2.6" stroke-opacity="0.68" '
            f'stroke-linecap="round">'
            f'<title>{escape(tip)}</title></path>'
        )
    parts.append("</g>")

    # --- leaf dots + labels, and subsystem group ticks ---
    # Count inbound edges per module so a leaf's dot radius hints at how
    # depended-upon it is (Auth's Tokens / Roles should read as hubs).
    indeg: Dict[str, int] = {m: 0 for m in leaves}
    outdeg: Dict[str, int] = {m: 0 for m in leaves}
    for u, v in EDGES:
        outdeg[u] += 1
        indeg[v] += 1

    parts.append('<g id="leaves">')
    for mod, lf in leaves.items():
        deg = lf["deg"]
        # A dot whose radius grows with in-degree (times depended on), so
        # the heavily depended-on modules (Auth's Tokens / Roles) read as
        # hubs. A thin white ring separates the dot from the cables that
        # land on it (no dark halo — a light ring on white keeps
        # same-hue overlaps distinguishable).
        r_dot = 5.0 + 1.2 * indeg[mod]
        # Label sits just outside the ring, rotated tangent, flipped on the
        # left half so it never reads upside down.
        lx, ly = _polar(R_LEAF + LABEL_PAD, deg)
        rot = deg - 90.0
        anchor = "start"
        if deg > 180:
            rot += 180.0
            anchor = "end"
        tip = (
            f"{mod} · {lf['subsys']} — depended on by {indeg[mod]}, "
            f"depends on {outdeg[mod]}"
        )
        parts.append(
            f'<g class="leaf" tabindex="0" role="img" aria-label="{escape(tip)}">'
            f'<title>{escape(tip)}</title>'
            f'<circle class="leaf-dot leaf-{_slug(str(lf["subsys"]))}" '
            f'cx="{lf["x"]:.2f}" cy="{lf["y"]:.2f}" '
            f'r="{r_dot:.2f}" fill="{lf["color"]}" '
            f'stroke="{BG}" stroke-width="2"/>'
            f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="17" '
            f'fill="{INK}" text-anchor="{anchor}" dominant-baseline="middle" '
            f'transform="rotate({rot:.2f} {lx:.2f} {ly:.2f})">'
            f'{escape(mod)}</text>'
            f'</g>'
        )
    parts.append("</g>")

    # --- subsystem legend (top-left, under the subtitle) ---
    lx0 = 46
    ly0 = 132
    parts.append(f'<g font-size="17" fill="{INK}">')
    for i, (subsys, _mods) in enumerate(SUBSYSTEMS):
        col = i % 3
        row = i // 3
        sx = lx0 + col * 220
        sy = ly0 + row * 32
        parts.append(
            f'<rect class="leaf-{_slug(subsys)}" x="{sx}" y="{sy - 13}" '
            f'width="18" height="18" rx="5" fill="{subsys_color[subsys]}"/>'
        )
        parts.append(
            f'<text x="{sx + 26}" y="{sy + 1}">{escape(subsys)}</text>'
        )
    parts.append("</g>")

    # --- takeaway callout, boxed, in the clear top-right corner ---
    # The centre of a bundling diagram is the busiest crossing zone, so
    # the headline number lives in an empty corner instead, with a white
    # backing so it never fights the cables.
    auth_in = sum(1 for _u, v in EDGES if leaves[v]["subsys"] == "Auth")
    bx, by, bw, bh = WIDTH - 300, 132, 254, 116
    parts.append(
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="16" '
        f'fill="{BG}" stroke="#E5E5EA" stroke-width="1.5"/>'
    )
    parts.append(
        f'<text x="{bx + 24}" y="{by + 34}" font-size="16" '
        f'fill="{SUBINK}">Dependencies into</text>'
    )
    parts.append(
        f'<text x="{bx + 24}" y="{by + 76}" '
        f'font-family="{FONT_MONO}" font-size="40" font-weight="700" '
        f'fill="{subsys_color["Auth"]}">Auth · {auth_in}</text>'
    )
    parts.append(
        f'<text x="{bx + 24}" y="{by + 102}" font-size="15" '
        f'fill="{SUBINK}">the widest cable in the graph</text>'
    )

    # --- footnote: read the hover affordance + encoding legend ---
    parts.append(
        f'<text x="46" y="{HEIGHT - 30}" font-size="15" '
        f'fill="{SUBINK}">Curves bundle by shared subsystem · dot size ∝ how '
        f'often a module is depended on · colour drifts source → target · '
        f'hover or focus an edge to trace it</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the edge-bundling SVG to the skill's example asset folder."""
    render_cli(__file__, "edge-bundling", build_svg, description="Render the edge-bundling SVG.")


if __name__ == "__main__":
    main()

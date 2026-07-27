#!/usr/bin/env python3
"""
make_circle-packing — publication-quality hierarchical circle packing (SVG).

A **circle-packing** diagram encodes a strict parent → child hierarchy as
*enclosure*: every node is a circle, a child sits inside its parent, and a
leaf's **area** is proportional to its quantitative weight. Nesting depth
reads as containment (a directory wraps its files), sibling weight reads as
disk size, and the whole tree collapses into one dense, gap-free disk — the
same idea D3's ``d3.pack`` and AntV's pack layout draw, but tuned here to a
poster-scale canvas with gentle depth shading and clean, non-overlapping
leaf labels.

The figure tells one concrete story: the source tree of a mid-size Python
web service, where every leaf circle is a **module sized by its lines of
code**. The takeaway the subtitle states — one package, ``services/``,
holds nearly half the codebase, and a single 2,410-line module inside it
(``payments.py``) is the biggest ball on the board — a refactor target that
jumps out of the packing the instant you look at it.

Vega-Lite has no pack layout (the geometry is a recursive
circle-enclosure solve, not a data-to-mark mapping), so this is built as an
SVG string by hand. The layout is the classic two-step used by D3:

* **pack siblings** — place a set of circles of given radii so they touch
  without overlapping, growing an active *sprezzature chain* around the packed
  cluster (Wang et al.'s algorithm, the same one ``d3.packSiblings`` uses),
  then wrap them in the smallest enclosing circle (Welzl's minimum
  enclosing circle);
* **recurse** — pack each node's children in local coordinates, scale the
  cluster to fill the parent (leaving a hair of padding so rings never
  kiss), and translate it into place.

Depth is shaded from pale to saturated so containment reads even where a
label will not fit, each top-level package owns a hue that tints its whole
subtree, and the largest leaves carry an outside-safe two-line label (name
+ line count) while the crowd of small modules stays clean. A short
call-out line points from the single biggest module to a captioned pill so
the headline finding is unmissable.

This is a **static** figure: a packing shows its whole shape at a glance,
so an entrance animation would only leave the gallery's first frame empty.
The one motion that pays for itself is interaction, and it stays CSS-only
(no JavaScript): every circle carries a native ``<title>`` tooltip, and a
``:hover`` / ``:focus`` rule lifts a package and dims the rest so any
cluster can be isolated on top of an already-complete picture.
``interactive`` is true; ``animated`` is false.

House style follows ``_style.py`` / ``make_radial-tree.py``: Roboto type,
the Apple-system categorical palette, ink ``#1D1D1F`` on white, rounded
label pills, a start-anchored takeaway title plus a one-line subtitle.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/circle-packing.svg``.

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
from _svg import hex_to_rgb as _hex_to_rgb, svg_open  # noqa: E402
from _render import svg_example_path, write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
# Poster-scale so the smallest leaf circles still read and the outer
# ring of package labels has room to breathe.
WIDTH = 1500
HEIGHT = 1220

INK = "#1D1D1F"        # primary text
SUBINK = "#6E6E73"     # secondary text
HAIRLINE = "#E5E5EA"   # neutral hairline
LEADER = "#B8B8BE"     # slightly darker hairline for call-out leaders
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

# The packed disk is centred in the lower ~78 % of the canvas, clear of
# the header block. These are resolved after the pack solve (below).
PACK_CX = WIDTH / 2.0
PACK_CY = 700.0
PACK_R = 470.0  # target radius of the outermost enclosing circle


# ------------------------------------------------------------------
# The story (illustrative but plausible): the source tree of a Python
# web service. Each entry is (path, lines_of_code) for a leaf module;
# directory nodes are inferred from the path. Line counts are the leaf
# weights that drive circle area.
#
# The shape is deliberately lopsided: ``services/`` carries ~45 % of the
# code, and its ``payments.py`` (2,410 lines) is the single biggest ball
# — the refactor target the subtitle calls out.
# ------------------------------------------------------------------
# (full path, lines of code)
MODULES: List[Tuple[str, int]] = [
    # ---- services/ : the heavy package ----
    ("services/payments.py", 2410),
    ("services/billing.py", 1180),
    ("services/accounts.py", 940),
    ("services/notifications.py", 610),
    ("services/search.py", 520),
    ("services/webhooks.py", 430),
    ("services/reporting.py", 380),
    ("services/exports.py", 260),

    # ---- api/ : the HTTP surface ----
    ("api/routes.py", 880),
    ("api/schemas.py", 640),
    ("api/auth.py", 560),
    ("api/middleware.py", 340),
    ("api/errors.py", 190),

    # ---- models/ : the data layer ----
    ("models/user.py", 720),
    ("models/order.py", 680),
    ("models/invoice.py", 540),
    ("models/product.py", 400),
    ("models/migrations.py", 300),

    # ---- workers/ : background jobs ----
    ("workers/scheduler.py", 460),
    ("workers/email_queue.py", 380),
    ("workers/retry.py", 220),

    # ---- core/ : shared utilities ----
    ("core/config.py", 300),
    ("core/logging.py", 240),
    ("core/db.py", 360),
    ("core/cache.py", 210),

    # ---- tests/ : the test suite ----
    ("tests/test_payments.py", 520),
    ("tests/test_api.py", 410),
    ("tests/test_models.py", 330),
    ("tests/conftest.py", 160),
]

# Each top-level package owns a hue; the subtree inherits it.
PALETTE = load_palette()
PACKAGE_ORDER = ["services", "api", "models", "workers", "core", "tests"]
PACKAGE_COLOR: Dict[str, str] = {
    "services": PALETTE.get("Blue", "#007AFF"),
    "api": PALETTE.get("Orange", "#FF9500"),
    "models": PALETTE.get("Purple", "#AF52DE"),
    "workers": PALETTE.get("Green", "#34C759"),
    "core": PALETTE.get("Teal", "#5AC8FA"),
    "tests": PALETTE.get("Brown", "#A2845E"),
}
PACKAGE_LABEL: Dict[str, str] = {
    "services": "services/",
    "api": "api/",
    "models": "models/",
    "workers": "workers/",
    "core": "core/",
    "tests": "tests/",
}

# The single module we call out by name.
HERO_PATH = "services/payments.py"

# Per-package steering for the outside name pills. Values bias the outward
# ray so a name clears its own circle and its neighbours; most packages sit
# on the plain centre→package ray (0, 0). Tuned once against the solved
# layout so every pill lands in open canvas.
PKG_LABEL_NUDGE: Dict[str, Tuple[float, float]] = {
    "services": (140.0, 40.0),   # push its name out to the right edge
    "tests": (60.0, 90.0),       # steer down-right into the corner
    "core": (-30.0, 90.0),       # straight down under the disk
    "workers": (-120.0, 40.0),   # out to the lower-left
}


# ------------------------------------------------------------------
# Circle-packing layout — the geometry engine
# ------------------------------------------------------------------
# A packed node is a dict:
#   {"id", "label", "package", "color", "depth", "value",
#    "x", "y", "r", "children": [...]}
# built bottom-up: leaves get a radius from sqrt(value); each internal
# node packs its children (packSiblings + Welzl enclosing circle),
# then is scaled+translated into its own frame.


def _hierarchy() -> Dict[str, object]:
    """Build the nested package → module tree from :data:`MODULES`.

    Returns
    -------
    dict
        The synthetic root node with ``children`` package nodes, each
        holding leaf module nodes. Only ``id``/``label``/``value`` and
        structural fields are set here; geometry is filled by the pack
        solver.
    """
    packages: Dict[str, Dict[str, object]] = {}
    for path, loc in MODULES:
        pkg, _, fname = path.partition("/")
        node = packages.setdefault(
            pkg,
            {
                "id": pkg,
                "label": PACKAGE_LABEL.get(pkg, pkg + "/"),
                "package": pkg,
                "color": PACKAGE_COLOR.get(pkg, SUBINK),
                "depth": 1,
                "children": [],
            },
        )
        leaf = {
            "id": path,
            "label": fname,
            "package": pkg,
            "color": PACKAGE_COLOR.get(pkg, SUBINK),
            "depth": 2,
            "value": float(loc),
            "children": [],
        }
        node["children"].append(leaf)  # type: ignore[attr-defined]

    ordered = [packages[p] for p in PACKAGE_ORDER if p in packages]
    return {
        "id": "root",
        "label": "src/",
        "package": "root",
        "color": INK,
        "depth": 0,
        "children": ordered,
    }


# ----- minimum enclosing circle of circles (Welzl, ported from d3) -----
def _circle_contains(c: Tuple[float, float, float], d: Tuple[float, float, float]) -> bool:
    """Return True if circle ``c`` fully contains circle ``d`` (both ``(x,y,r)``)."""
    dx = c[0] - d[0]
    dy = c[1] - d[1]
    dr = c[2] - d[2]
    return dr >= 0 and (dr * dr) >= (dx * dx + dy * dy) - 1e-9


def _encloses_weak_all(c: Tuple[float, float, float], circles: List[Tuple[float, float, float]]) -> bool:
    """Return True if circle ``c`` encloses every circle in ``circles``."""
    return all(_circle_contains(c, d) for d in circles)


def _enclose_basis1(a: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Enclosing circle whose only support is the single circle ``a``."""
    return (a[0], a[1], a[2])


def _enclose_basis2(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Smallest circle enclosing two circles, tangent to both externally."""
    x1, y1, r1 = a
    x2, y2, r2 = b
    x21, y21, r21 = x2 - x1, y2 - y1, r2 - r1
    length = math.hypot(x21, y21)
    return (
        (x1 + x2 + x21 / length * r21) / 2.0 if length else (x1 + x2) / 2.0,
        (y1 + y2 + y21 / length * r21) / 2.0 if length else (y1 + y2) / 2.0,
        (length + r1 + r2) / 2.0,
    )


def _enclose_basis3(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    c: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """Smallest circle enclosing three circles, tangent to all three (Apollonius)."""
    x1, y1, r1 = a
    x2, y2, r2 = b
    x3, y3, r3 = c
    a2 = x1 - x2
    a3 = x1 - x3
    b2 = y1 - y2
    b3 = y1 - y3
    c2 = r2 - r1
    c3 = r3 - r1
    d1 = x1 * x1 + y1 * y1 - r1 * r1
    d2 = d1 - x2 * x2 - y2 * y2 + r2 * r2
    d3 = d1 - x3 * x3 - y3 * y3 + r3 * r3
    ab = a3 * b2 - a2 * b3
    if abs(ab) < 1e-12:
        return _enclose_basis2(a, b)
    xa = (b2 * d3 - b3 * d2) / (ab * 2.0) - x1
    xb = (b3 * c2 - b2 * c3) / ab
    ya = (a3 * d2 - a2 * d3) / (ab * 2.0) - y1
    yb = (a2 * c3 - a3 * c2) / ab
    aa = xb * xb + yb * yb - 1.0
    bb = 2.0 * (r1 + xa * xb + ya * yb)
    cc = xa * xa + ya * ya - r1 * r1
    if abs(aa) < 1e-12:
        r = -cc / bb if bb else 0.0
    else:
        r = -(bb + math.sqrt(max(0.0, bb * bb - 4.0 * aa * cc))) / (2.0 * aa)
    return (x1 + xa + xb * r, y1 + ya + yb * r, r)


def _enclose_basis(circles: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
    """Exact enclosing circle for a support set of 1, 2, or 3 circles."""
    if len(circles) == 1:
        return _enclose_basis1(circles[0])
    if len(circles) == 2:
        return _enclose_basis2(circles[0], circles[1])
    return _enclose_basis3(circles[0], circles[1], circles[2])


def _enclose(circles: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
    """Smallest circle enclosing a set of *circles* (Welzl, ported from d3).

    This is the exact minimum-enclosing-circle-of-circles used by
    ``d3.packEnclose``: an incremental Welzl solve whose basis cases are
    the tangent enclosures of 1, 2, or 3 circles (:func:`_enclose_basis`).

    Parameters
    ----------
    circles : list of (float, float, float)
        The ``(x, y, r)`` sibling circles to wrap.

    Returns
    -------
    (float, float, float)
        ``(cx, cy, r)`` of the tight enclosing circle.
    """
    if not circles:
        return (0.0, 0.0, 0.0)
    circs = list(circles)
    # Deterministic order (d3 shuffles; a fixed order keeps output stable).
    encl: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    i = 0
    n = len(circs)
    while i < n:
        p = circs[i]
        if encl[2] > 0 and _circle_contains(encl, p):
            i += 1
            continue
        # p is on the boundary: rebuild with p in the basis.
        encl = _enclose1(circs, i, p)
        i = 0
    return encl


def _enclose1(
    circs: List[Tuple[float, float, float]], end: int, p1: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Welzl second level: enclosing circle with ``p1`` forced on the boundary."""
    encl = _enclose_basis([p1])
    j = 0
    while j < end:
        q = circs[j]
        if _circle_contains(encl, q):
            j += 1
            continue
        encl = _enclose2(circs, j, p1, q)
        j = 0
    return encl


def _enclose2(
    circs: List[Tuple[float, float, float]],
    end: int,
    p1: Tuple[float, float, float],
    p2: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """Welzl third level: ``p1`` and ``p2`` both forced on the boundary."""
    encl = _enclose_basis([p1, p2])
    k = 0
    while k < end:
        q = circs[k]
        if _circle_contains(encl, q):
            k += 1
            continue
        encl = _enclose_basis([p1, p2, q])
        k += 1
    return encl


# ----- pack a set of sibling circles (Wang / d3.packSiblings) -----
def _place(
    b: Tuple[float, float, float], a: Tuple[float, float, float], c_r: float
) -> Tuple[float, float, float]:
    """Return a circle of radius ``c_r`` tangent to both ``a`` and ``b``.

    Ported from ``d3.siblings``' ``place``: given two already-placed
    circles ``a`` and ``b``, position a new circle of radius ``c_r`` so it
    is externally tangent to both, on the outward side of the a-b axis.
    """
    ax, ay, ar = a
    bx, by, br = b
    dx = bx - ax
    dy = by - ay
    d2 = dx * dx + dy * dy
    if d2 > 0:
        a_ = (ar + c_r) ** 2
        b_ = (br + c_r) ** 2
        if a_ > b_:
            x = (d2 + b_ - a_) / (2.0 * d2)
            y = math.sqrt(max(0.0, b_ / d2 - x * x))
            cx = bx - x * dx - y * dy
            cy = by - x * dy + y * dx
        else:
            x = (d2 + a_ - b_) / (2.0 * d2)
            y = math.sqrt(max(0.0, a_ / d2 - x * x))
            cx = ax + x * dx - y * dy
            cy = ay + x * dy + y * dx
        return (cx, cy, c_r)
    return (ax + ar + c_r, ay, c_r)


def _dist2(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> bool:
    """Return True if circles ``a`` and ``b`` overlap (centres too close)."""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    dr = a[2] + b[2]
    return (dr * dr - 1e-6) > (dx * dx + dy * dy)


def _pack_siblings(radii: List[float]) -> List[Tuple[float, float, float]]:
    """Pack circles of the given radii so they touch without overlapping.

    Faithful port of ``d3.packSiblings`` — the front-chain algorithm of
    Wang et al. (2006): seed the first three circles in mutual tangency,
    then walk a doubly-linked *sprezzature chain* of the outer boundary, placing
    each new circle against the nearest sprezzature edge and splicing the chain
    to skip any circle the newcomer would overlap. Guarantees a
    non-overlapping, compact packing.

    Parameters
    ----------
    radii : list of float
        Radii of the circles to pack, in draw order.

    Returns
    -------
    list of (float, float, float)
        ``(x, y, r)`` for each input circle, in the same order.
    """
    n = len(radii)
    if n == 0:
        return []

    # Node objects mirror d3's circular doubly-linked list nodes.
    nodes: List[Dict[str, object]] = [
        {"r": radii[i], "x": 0.0, "y": 0.0, "idx": i, "next": None, "prev": None}
        for i in range(n)
    ]

    a = nodes[0]
    a["x"], a["y"] = a["r"], 0.0  # type: ignore[assignment]
    if n == 1:
        return [(0.0, 0.0, radii[0])]

    b = nodes[1]
    b["x"], b["y"] = -float(b["r"]), 0.0  # type: ignore[assignment]
    a["x"], a["y"] = float(a["r"]), 0.0  # type: ignore[assignment]
    if n == 2:
        return _finalise(nodes, radii)

    c = nodes[2]
    _pl = _place(_as_c(b), _as_c(a), float(c["r"]))
    c["x"], c["y"] = _pl[0], _pl[1]  # type: ignore[assignment]

    # Initialise the sprezzature chain a <-> b <-> c <-> a.
    _link(a, c)
    _link(b, a)
    _link(c, b)

    aa = a
    bb = c
    for i in range(3, n):
        cnode = nodes[i]
        _pl = _place(_as_c(aa), _as_c(bb), float(cnode["r"]))
        cnode["x"], cnode["y"] = _pl[0], _pl[1]  # type: ignore[assignment]

        # Walk the sprezzature chain looking for an overlap.
        j = bb["next"]
        k = aa["prev"]
        while j is not aa:
            assert j is not None
            if _dist2(_as_c(cnode), _as_c(j)):
                # Overlap on the "next" side: cut back to j and retry.
                bb = j
                _link(aa, bb)
                _pl = _place(_as_c(aa), _as_c(bb), float(cnode["r"]))
                cnode["x"], cnode["y"] = _pl[0], _pl[1]  # type: ignore[assignment]
                j = bb["next"]
                k = aa["prev"]
                continue
            assert k is not None
            if _dist2(_as_c(cnode), _as_c(k)):
                # Overlap on the "prev" side: cut forward to k and retry.
                aa = k
                _link(aa, bb)
                _pl = _place(_as_c(aa), _as_c(bb), float(cnode["r"]))
                cnode["x"], cnode["y"] = _pl[0], _pl[1]  # type: ignore[assignment]
                j = bb["next"]
                k = aa["prev"]
                continue
            j = j["next"]  # type: ignore[assignment]
            k = k["prev"]  # type: ignore[assignment]

        # Splice cnode into the sprezzature chain between aa and bb.
        _link(aa, cnode)
        _link(cnode, bb)
        bb = cnode

    return _finalise(nodes, radii)


def _link(left: Dict[str, object], right: Dict[str, object]) -> None:
    """Wire ``left.next = right`` and ``right.prev = left`` in the sprezzature chain."""
    left["next"] = right
    right["prev"] = left


def _as_c(node: Dict[str, object]) -> Tuple[float, float, float]:
    """View a front-chain node as an ``(x, y, r)`` circle tuple."""
    return (float(node["x"]), float(node["y"]), float(node["r"]))


def _finalise(
    nodes: List[Dict[str, object]], radii: List[float]
) -> List[Tuple[float, float, float]]:
    """Centre the packed cluster on its enclosing circle, return in input order."""
    circles = [_as_c(nd) for nd in nodes]
    cx, cy, _r = _enclose(circles)
    out: List[Tuple[float, float, float]] = []
    for i, (x, y, r) in enumerate(circles):
        out.append((x - cx, y - cy, r))
        _ = radii[i]
    return out


# ----- recursive pack -----
def _pack_node(node: Dict[str, object], padding: float) -> float:
    """Pack ``node``'s children in local coords; return the node's radius.

    Bottom-up: a leaf's radius is ``sqrt(value)`` (so area ∝ value); an
    internal node packs its children, wraps them in an enclosing circle,
    scales that to leave ``padding`` between siblings, and stores each
    child's local ``(x, y)``. The returned radius is what the parent uses
    to size *this* node.
    """
    children = node.get("children") or []
    if not children:
        node["r"] = math.sqrt(float(node["value"]))  # type: ignore[arg-type]
        return node["r"]  # type: ignore[return-value]

    # Pack children first (recurse), collecting their radii.
    child_radii: List[float] = []
    for ch in children:  # type: ignore[assignment]
        cr = _pack_node(ch, padding)  # type: ignore[arg-type]
        child_radii.append(cr)

    # Pad each child so packed siblings never visually kiss. We pack the
    # *padded* radii, so the returned positions already carry the gap; the
    # enclosing circle is computed over those same padded circles so the
    # parent is guaranteed to contain every child with room to spare.
    pad_radii = [r + padding for r in child_radii]
    packed = _pack_siblings(pad_radii)

    for ch, (x, y, _pr) in zip(children, packed):  # type: ignore[assignment]
        ch["x"] = x  # type: ignore[index]
        ch["y"] = y  # type: ignore[index]

    enc = _enclose([(x, y, pr) for (x, y, _pr), pr in zip(packed, pad_radii)])
    # Shift children so the cluster centre is at local origin.
    for ch in children:  # type: ignore[assignment]
        ch["x"] = ch["x"] - enc[0]  # type: ignore[index,operator]
        ch["y"] = ch["y"] - enc[1]  # type: ignore[index,operator]

    # A touch of inner padding so the parent ring never grazes a child.
    node["r"] = enc[2] + padding
    return node["r"]  # type: ignore[return-value]


def _layout() -> Dict[str, object]:
    """Solve the full packing and place the root at the canvas centre.

    Returns
    -------
    dict
        The root node with absolute ``x``/``y``/``r`` set on every node,
        scaled to fill :data:`PACK_R` at :data:`PACK_CX`/:data:`PACK_CY`.
    """
    root = _hierarchy()
    # Padding is expressed in the sqrt(value) space; small so leaves stay
    # large but never touch.
    _pack_node(root, padding=1.6)

    # Scale so the root's radius maps to PACK_R, then place absolutely.
    scale = PACK_R / float(root["r"])  # type: ignore[arg-type]

    def place(node: Dict[str, object], ox: float, oy: float) -> None:
        node["r"] = float(node["r"]) * scale  # type: ignore[arg-type]
        node["x"] = ox
        node["y"] = oy
        for ch in node.get("children") or []:  # type: ignore[assignment]
            place(ch, ox + float(ch["x"]) * scale, oy + float(ch["y"]) * scale)  # type: ignore[index]

    # Root children carry local x/y; root itself sits at PACK centre.
    root["x"] = 0.0
    root["y"] = 0.0
    place(root, PACK_CX, PACK_CY)
    return root


# ------------------------------------------------------------------
# Colour shading by depth
# ------------------------------------------------------------------
def _mix(hex_color: str, t: float) -> str:
    """Mix ``hex_color`` toward white by fraction ``t`` (0 = color, 1 = white)."""
    r, g, b = _hex_to_rgb(hex_color)
    r = round(r + (255 - r) * t)
    g = round(g + (255 - g) * t)
    b = round(b + (255 - b) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


def _leaf_fill(color: str, value: float, vmin: float, vmax: float) -> str:
    """Return a leaf fill: the package hue, lightened for smaller modules.

    Bigger modules stay saturated (they carry the weight of the story);
    smaller ones fade toward white, so the packing shades gently by size
    within each package without ever losing the family hue.
    """
    if vmax <= vmin:
        t = 0.0
    else:
        # Map size to a lightening amount: big -> 0.10, small -> 0.55.
        frac = (value - vmin) / (vmax - vmin)
        t = 0.55 - 0.45 * frac
    return _mix(color, t)


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def _wrap_subtitle(text: str, max_chars: int = 116) -> List[str]:
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


def _fit_label(name: str, loc: int, radius: float) -> Optional[Tuple[float, float, List[str]]]:
    """Decide how a leaf's label fits inside its circle.

    Returns ``(name_font, loc_font, name_lines)`` when the module name
    (plus its line count on a final row) fits inside the circle, else
    ``None`` — in which case the circle stays clean and relies on its
    ``<title>`` tooltip. A name too wide for one line is broken on its
    underscore (``test_payments`` → ``test`` / ``payments``) so even a
    long name lands inside a mid-size circle.

    Parameters
    ----------
    name : str
        The leaf's file name (e.g. ``payments.py``).
    loc : int
        Lines of code — shown as the label's second-value row.
    radius : float
        The leaf circle radius in pixels.
    """
    _ = loc
    short = name[:-3] if name.endswith(".py") else name

    def width_of(text: str, fs: float) -> float:
        return len(text) * fs * 0.56

    # Preferred single-line font, capped so labels never dwarf a small ball.
    fs = min(radius * 0.40, 21.0)
    # Horizontal room a chord leaves at the text's vertical offset (~1.7 r).
    room = radius * 1.7

    # One line if it fits.
    if fs >= 9.0 and width_of(short, fs) <= room:
        return (fs, max(fs * 0.72, 9.0), [short])

    # Otherwise try to wrap on the underscore into two balanced lines.
    if "_" in short:
        head, _, tail = short.partition("_")
        lines = [head, tail]
        fs2 = min(radius * 0.34, 17.0)
        if fs2 >= 9.0 and max(width_of(lines[0], fs2), width_of(lines[1], fs2)) <= room:
            return (fs2, max(fs2 * 0.70, 9.0), lines)

    # Last resort: a smaller single line.
    fs3 = min(radius * 0.30, 14.0)
    if fs3 >= 8.5 and width_of(short, fs3) <= radius * 1.85:
        return (fs3, max(fs3 * 0.72, 8.5), [short])

    return None


def _text_color_for(fill: str) -> str:
    """Pick ink or white for a label so it stays legible on ``fill``.

    Uses relative luminance; dark fills get white text, light fills get
    ink. No halo, no stroke — a pure contrasting fill only.
    """
    r, g, b = _hex_to_rgb(fill)
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    return "#FFFFFF" if lum < 0.58 else INK


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full circle-packing SVG document as a string.

    Parameters
    ----------
    mode : str, default ``"self-contained"``
        Fullscreen-control wiring for the emitted SVG:

        * ``"self-contained"`` — carry a self-revealing fullscreen button
          plus its inline script, so the standalone SVG toggles fullscreen
          on its own (the button stays hidden until the live script shows
          it, keeping the static raster byte-identical).
        * ``"external"`` — emit no button/script here; defer the control to
          a page-level module that wires every figure on the page.
        * ``"static"`` — emit nothing; a plain, non-interactive SVG.
    accessibility : str, default ``"universal"``
        Palette accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). The ``"universal"`` default is the
        colour-vision-safe standard and leaves the shipped palette (and so
        the emitted SVG) unchanged; any other level remaps every package hue.

    Returns
    -------
    str
        A complete, standalone SVG with CSS hover/focus package isolation.
        Every mark is drawn once in its final state — no entrance
        animation.
    """
    root = _layout()

    # ``universal`` reuses the module-level PACKAGE_COLOR verbatim (output
    # stays byte-identical); any other level re-reads the palette at that
    # accessibility level and recolours every node by its package.
    if accessibility and accessibility != "universal":
        pal = load_palette(accessibility)
        package_color = {
            "services": pal.get("Blue", "#007AFF"),
            "api": pal.get("Orange", "#FF9500"),
            "models": pal.get("Purple", "#AF52DE"),
            "workers": pal.get("Green", "#34C759"),
            "core": pal.get("Teal", "#5AC8FA"),
            "tests": pal.get("Brown", "#A2845E"),
        }

        def _recolor(node: Dict[str, object]) -> None:
            pkg = str(node.get("package", ""))
            if pkg in package_color:
                node["color"] = package_color[pkg]
            for ch in node.get("children") or []:  # type: ignore[assignment]
                _recolor(ch)  # type: ignore[arg-type]

        _recolor(root)

    # Value range across leaves (for shading + hero detection).
    leaf_values = [float(ch["value"]) for pkg in root["children"] for ch in pkg["children"]]  # type: ignore[index]
    vmin, vmax = min(leaf_values), max(leaf_values)

    parts: List[str] = []

    # --- accessible header text ---
    title_txt = "Where the code lives: two packages carry the weight"
    subtitle_txt = (
        "Every circle is a module sized by lines of code; services/ alone is 43% "
        "of the tree and its payments.py runs to 2,410 lines. Illustrative repo map."
    )
    desc_txt = (
        "Hierarchical circle-packing diagram of a Python web-service source tree. "
        "Six top-level packages are drawn as large circles, each tinted its own "
        "color, and every module inside is a nested circle sized by its lines of "
        "code. The services package is the largest and holds payments.py, the "
        "single biggest module at 2,410 lines, followed by api, models, workers, "
        "core, and tests. The packing is gap-free: bigger balls mean more code."
    )

    parts.append(svg_open(WIDTH, HEIGHT, "cp-title", "cp-desc", font_family=FONT))
    parts.append(f'<title id="cp-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="cp-desc">{escape(desc_txt)}</desc>')

    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule below lives inside a media query). Under
    # prefers-contrast each package's identity marks deepen to its high-contrast
    # hue: the container ring (stroke) and the outside name pill + legend swatch
    # (fill). The nested LEAF fills are left untouched on purpose — inside a
    # package the leaf colour is a lightness ramp that encodes module size, and
    # deepening it would both destroy that size read and darken the balls under
    # their on-circle labels (the venn multiply-blend trap). forced-colors is
    # left to the browser default: the hierarchy already reads by enclosure and
    # area, and flattening every leaf to one system colour would erase the size
    # shading.
    pkg_fill_series = {f".pkgfill-{pkg['id']}": str(pkg["color"]) for pkg in root["children"]}  # type: ignore[index]
    pkg_ring_series = {f".pkgring-{pkg['id']}": str(pkg["color"]) for pkg in root["children"]}  # type: ignore[index]
    adaptive = (
        os_adaptive_style(pkg_fill_series, role="fill")
        + os_adaptive_style(pkg_ring_series, role="stroke")
    )
    # --- CSS: hover/focus a package lifts it, dims the rest ---
    parts.append(
        "<style>"
        "#packs .pkg{transition:opacity .16s ease}"
        "#packing:hover #packs .pkg{opacity:.30}"
        "#packs .pkg:hover,#packs .pkg:focus-within{opacity:1}"
        ".hit:focus{outline:none}"
        + adaptive
        # Additive dark mode. The default map flips the paper and all on-paper
        # ink (title, subtitle, legend, footnote, hero call-out). The leaf
        # labels and outside name pills live inside #packing and are coloured
        # for contrast against their own (unchanged) data-hue circle/pill — so
        # a blanket ink flip would break them. Higher-specificity #packing rules
        # restore their authored fills; the pale package washes and leaf hues
        # read on dark unchanged.
        + os_dark_style(
            extra=(
                '#packing [fill="#1D1D1F"]{fill:#1D1D1F;}'
                '#packing [fill="#6E6E73"]{fill:#6E6E73;}'
                '#packing [fill="#FFFFFF"]{fill:#FFFFFF;}'
            )
        )
        + "</style>"
    )

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    margin_left = 44
    parts.append(
        f'<text x="{margin_left}" y="58" font-size="32" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    for i, line in enumerate(_wrap_subtitle(subtitle_txt)):
        parts.append(
            f'<text x="{margin_left}" y="{94 + i * 27}" font-size="19" '
            f'fill="{SUBINK}">{escape(line)}</text>'
        )

    # --- the packing ---
    parts.append('<g id="packing">')
    parts.append('<g id="packs">')

    hero_geom: Optional[Dict[str, object]] = None

    for pkg in root["children"]:  # type: ignore[index]
        pkg_color = str(pkg["color"])
        px, py, pr = float(pkg["x"]), float(pkg["y"]), float(pkg["r"])
        n_mod = len(pkg["children"])  # type: ignore[arg-type]
        pkg_loc = int(sum(float(ch["value"]) for ch in pkg["children"]))  # type: ignore[index]
        pkg_tip = f'{pkg["label"]} — {n_mod} modules, {pkg_loc:,} lines'

        parts.append(
            f'<g class="pkg" tabindex="0" role="img" '
            f'aria-label="{escape(pkg_tip)}">'
        )
        # Package container: a very pale wash of the hue + a hairline ring
        # in the hue, so nesting reads without a heavy dark border.
        parts.append(
            f'<circle class="hit pkgring-{pkg["id"]}" cx="{px:.1f}" cy="{py:.1f}" '
            f'r="{pr:.1f}" '
            f'fill="{_mix(pkg_color, 0.86)}" stroke="{_mix(pkg_color, 0.30)}" '
            f'stroke-width="1.5"><title>{escape(pkg_tip)}</title></circle>'
        )

        # Leaves.
        for ch in pkg["children"]:  # type: ignore[index]
            cx, cy, cr = float(ch["x"]), float(ch["y"]), float(ch["r"])
            loc = int(ch["value"])
            fill = _leaf_fill(pkg_color, float(loc), vmin, vmax)
            leaf_tip = f'{ch["id"]} — {loc:,} lines'
            parts.append(
                f'<circle class="hit" cx="{cx:.1f}" cy="{cy:.1f}" r="{cr:.1f}" '
                f'fill="{fill}"><title>{escape(leaf_tip)}</title></circle>'
            )
            # Label if it fits.
            fit = _fit_label(str(ch["label"]), loc, cr)
            if fit is not None:
                fs, loc_fs, name_lines = fit
                tcol = _text_color_for(fill)
                subcol = tcol if tcol == "#FFFFFF" else SUBINK
                sub_opacity = "0.85" if tcol == "#FFFFFF" else "1"
                # Stack: name line(s), then the line count. Centre the whole
                # block on the circle by offsetting from the middle row.
                n_name = len(name_lines)
                line_h = fs * 1.02
                total_h = n_name * line_h + loc_fs * 1.15
                top = cy - total_h / 2.0 + line_h / 2.0
                for li, nl in enumerate(name_lines):
                    parts.append(
                        f'<text x="{cx:.1f}" y="{top + li * line_h:.1f}" '
                        f'text-anchor="middle" dominant-baseline="central" '
                        f'font-size="{fs:.1f}" font-weight="600" fill="{tcol}" '
                        f'pointer-events="none">{escape(nl)}</text>'
                    )
                parts.append(
                    f'<text x="{cx:.1f}" '
                    f'y="{top + n_name * line_h + loc_fs * 0.15:.1f}" '
                    f'text-anchor="middle" dominant-baseline="central" '
                    f'font-family="{FONT_MONO}" font-size="{loc_fs:.1f}" '
                    f'fill="{subcol}" opacity="{sub_opacity}" '
                    f'pointer-events="none">{loc:,}</text>'
                )
            if ch["id"] == HERO_PATH:
                hero_geom = {"x": cx, "y": cy, "r": cr, "loc": loc, "color": pkg_color}

        parts.append("</g>")  # .pkg

    parts.append("</g>")  # #packs

    # --- package name labels around the outside on leader lines ---
    _emit_package_labels(parts, root)

    parts.append("</g>")  # #packing

    # --- hero call-out ---
    if hero_geom is not None:
        _emit_hero_callout(parts, hero_geom)

    # --- legend + footnote ---
    _emit_legend(parts, root)
    parts.append(
        f'<text x="{margin_left}" y="{HEIGHT - 26}" font-size="15" '
        f'fill="{SUBINK}">Circle area is proportional to lines of code. '
        f'Hover or focus a package to isolate it.</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def _emit_package_labels(parts: List[str], root: Dict[str, object]) -> None:
    """Emit a package name pill just outside each package circle.

    The pill sits on the circle's outward radial (pointing away from the
    packing centre) with a short leader, so the six family names read
    cleanly around the ring without ever overlapping a leaf label.
    """
    parts.append('<g id="pkg-labels">')
    for pkg in root["children"]:  # type: ignore[index]
        px, py, pr = float(pkg["x"]), float(pkg["y"]), float(pkg["r"])
        color = str(pkg["color"])
        label = str(pkg["label"])
        # Each package name sits just outside its own circle, on the ray
        # from the packing centre through the package centre, so labels
        # fan out around the disk and never sit over a leaf. A per-package
        # nudge steers the two right-edge names (services, tests) fully
        # clear of the circle they annotate.
        nudge = PKG_LABEL_NUDGE.get(str(pkg["id"]), (0.0, 0.0))
        dx, dy = (px - PACK_CX) + nudge[0], (py - PACK_CY) + nudge[1]
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        # Anchor on the rim facing the label, push out a fixed clearance.
        rim_x, rim_y = px + ux * pr, py + uy * pr
        lab_x, lab_y = px + ux * (pr + 44.0), py + uy * (pr + 44.0)
        # Keep pills inside the canvas.
        lab_x = max(120.0, min(WIDTH - 120.0, lab_x))
        lab_y = max(150.0, min(HEIGHT - 70.0, lab_y))

        # Leader.
        parts.append(
            f'<line x1="{rim_x:.1f}" y1="{rim_y:.1f}" x2="{lab_x:.1f}" '
            f'y2="{lab_y:.1f}" stroke="{LEADER}" stroke-width="1.25"/>'
        )
        # Pill: filled hue, white text (no dark ring).
        fs = 18.0
        pad_x = 13.0
        w = len(label) * fs * 0.58 + 2 * pad_x
        h = 32.0
        parts.append(
            f'<g><rect class="pkgfill-{pkg["id"]}" x="{lab_x - w / 2:.1f}" '
            f'y="{lab_y - h / 2:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" fill="{color}"/>'
            f'<text x="{lab_x:.1f}" y="{lab_y:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="{fs}" font-weight="700" '
            f'font-family="{FONT_MONO}" fill="#FFFFFF">{escape(label)}</text></g>'
        )
    parts.append("</g>")


def _emit_hero_callout(parts: List[str], hero: Dict[str, object]) -> None:
    """Draw a call-out from the biggest module to a captioned pill.

    The pill sits in the free space at the upper-left of the packing so it
    never crosses a leaf. A thin leader with a small end-dot points from
    the pill to the hero circle's rim.
    """
    hx, hy, hr = float(hero["x"]), float(hero["y"]), float(hero["r"])
    loc = int(hero["loc"])
    color = str(hero["color"])

    # Caption anchored in the free zone at the top-right of the canvas,
    # clear of every package, right-aligned against the margin.
    cap_x, cap_y = WIDTH - 44.0, 236.0
    line1 = "payments.py"
    line2 = f"{loc:,} lines"
    line3 = "the one refactor target"

    # The leader comes in toward the hero from its upper-right, the side
    # facing the caption, so the dashed line barely grazes the packing.
    ang = math.radians(-38.0)  # up-and-to-the-right from the hero centre
    rim_x = hx + math.cos(ang) * hr
    rim_y = hy + math.sin(ang) * hr
    # Elbow: down from the caption, then a straight run to the rim dot.
    elbow_x, elbow_y = cap_x - 150.0, cap_y + 34.0

    parts.append(
        f'<g id="hero-callout" pointer-events="none">'
        f'<path d="M{elbow_x:.1f},{elbow_y:.1f} L{rim_x:.1f},{rim_y:.1f}" '
        f'fill="none" stroke="{INK}" stroke-width="1.6" '
        f'stroke-dasharray="1 5" stroke-linecap="round"/>'
        f'<circle cx="{rim_x:.1f}" cy="{rim_y:.1f}" r="4" fill="{INK}"/>'
    )
    # Caption block: a coloured name + two ink lines, right-aligned, no box.
    parts.append(
        f'<text x="{cap_x:.1f}" y="{cap_y:.1f}" text-anchor="end" '
        f'font-size="24" font-weight="700" font-family="{FONT_MONO}" '
        f'fill="{color}">{escape(line1)}</text>'
    )
    parts.append(
        f'<text x="{cap_x:.1f}" y="{cap_y + 27:.1f}" text-anchor="end" '
        f'font-size="17" fill="{INK}"><tspan font-weight="700">'
        f'{escape(line2)}</tspan> — {escape(line3)}</text>'
    )
    parts.append("</g>")


def _emit_legend(parts: List[str], root: Dict[str, object]) -> None:
    """Emit the package legend as a swatch column, bottom-left.

    Each row: a hue swatch, the package name, and its share of the total
    codebase in a mono column — so the reader can rank packages by size
    without eyeballing circle areas.
    """
    total = sum(float(ch["value"]) for pkg in root["children"] for ch in pkg["children"])  # type: ignore[index]

    lx = 44.0
    ly = HEIGHT - 250.0
    parts.append('<g id="legend">')
    parts.append(
        f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="14" font-weight="700" '
        f'letter-spacing="0.8" fill="{SUBINK}">PACKAGES BY SHARE</text>'
    )
    ry = ly + 28
    # Sort packages by total lines, descending.
    ranked = sorted(
        root["children"],  # type: ignore[index]
        key=lambda p: sum(float(ch["value"]) for ch in p["children"]),  # type: ignore[index]
        reverse=True,
    )
    for pkg in ranked:
        pkg_loc = sum(float(ch["value"]) for ch in pkg["children"])  # type: ignore[index]
        share = 100.0 * pkg_loc / total if total else 0.0
        parts.append(
            f'<rect class="pkgfill-{pkg["id"]}" x="{lx:.1f}" y="{ry - 13:.1f}" '
            f'width="17" height="17" rx="4.5" '
            f'fill="{pkg["color"]}"/>'
        )
        parts.append(
            f'<text x="{lx + 26:.1f}" y="{ry:.1f}" font-size="16" '
            f'font-family="{FONT_MONO}" fill="{INK}">{escape(str(pkg["label"]))}</text>'
        )
        parts.append(
            f'<text x="{lx + 168:.1f}" y="{ry:.1f}" font-family="{FONT_MONO}" '
            f'font-size="15" fill="{SUBINK}" text-anchor="end">{share:.0f}%</text>'
        )
        ry += 30
    parts.append("</g>")


def main() -> None:
    """Write the circle-packing SVG to the skill's example asset folder."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="make_circle-packing",
        description="Render a house-styled hierarchical circle-packing diagram as SVG.",
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Fullscreen-control wiring (default: self-contained).",
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
    args = parser.parse_args()

    out = svg_example_path(__file__, "circle-packing")
    write_svg(out, build_svg(mode=args.mode, accessibility=args.accessibility))


if __name__ == "__main__":
    main()

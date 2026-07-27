#!/usr/bin/env python3
"""
make_dependency-wheel — publication-quality dependency wheel (circular sankey) SVG.

A **dependency wheel** lays every node on the rim of a single circle and
draws a directed, sankey-weighted ribbon from a source arc to a target
arc for every flow between two nodes. It is a *directed* cousin of the
chord diagram: where a chord ribbon is symmetric, a dependency-wheel
ribbon knows its direction — it is fat where it leaves the source and
tapers as it lands on the target, and it carries the **source node's
colour** the whole way, so the eye can trace "who sends how much to
whom" around the ring. It answers reallocation / migration / hand-off
questions ("where did this region's people go?", "how was the budget
moved between departments?") at a glance.

Vega-Lite has no native circular-sankey mark, so this figure is built as
an SVG string by hand rather than through ``vl_convert``. The layout is
the classic wheel:

* **Node arcs** — each node owns a wedge of the ring whose angular span
  is proportional to that node's *throughput* (everything it sends plus
  everything it receives). Small gaps separate the wedges; each wedge is
  a rounded floating pill in the node's brand hue.
* **Flow ribbons** — a ribbon leaves an angular sub-slice of the source
  arc (width ∝ the flow it carries) and lands on a sub-slice of the
  target arc, bowing through the circle centre as two cubic Béziers so
  thick reallocations read as fat lens-shaped ribbons. The ribbon is
  filled with the *source* node's colour; a subtle taper (wide at the
  source, narrow at the target) encodes direction without arrowheads
  colliding in the crowded hub.

House style follows ``_style.py``: Roboto type, the Apple-system
categorical palette, ink ``#1D1D1F`` on white, rounded label treatment,
a start-anchored takeaway title plus a one-line subtitle that states the
point.

Interaction (no JavaScript): every ribbon and every arc carries a native
``<title>`` tooltip with its exact value, and a CSS ``:hover`` /
``:focus`` rule dims the rest of the wheel so that focusing a node's arc
lights up only that node's flows — the "hover one node to see all its
dependencies" affordance that defines this chart type. The figure is
otherwise static (a dependency wheel does not benefit from animation),
so ``animated`` is false and ``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/dependency-wheel.svg``.

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
from _style import forced_color_patterns, leveled_colors, load_palette, os_dark_style  # noqa: E402
from _svg import point_on_circle, svg_open  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1160
HEIGHT = 1260
CX = WIDTH / 2.0
CY = HEIGHT / 2.0 + 58       # nudge down to leave room for the title block
R_OUTER = 392               # outer radius of the node-arc ring
ARC_THICK = 30              # radial thickness of a node arc
R_INNER = R_OUTER - ARC_THICK
GAP_DEG = 3.2               # angular gap (deg) between adjacent node arcs
LABEL_PAD = 22              # radial gap between arc and its text label

INK = "#1D1D1F"             # primary text
SUBINK = "#6E6E73"          # secondary text
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"


# ------------------------------------------------------------------
# The story (illustrative but plausible): net internal migration between
# the six broad regions of one country over a decade, measured in
# thousands of people. Cell (i, j) = people who moved *from* region i
# *to* region j. Self-moves (the diagonal) are dropped — a dependency
# wheel is about the exchanges *between* nodes.
#
# The takeaway: the Sun Belt (South + Mountain West) pulls people out of
# the Rust Belt and the Coasts — a one-directional drain, not a swap.
# ------------------------------------------------------------------
REGIONS: List[str] = [
    "Northeast",
    "Midwest",
    "Southeast",
    "Mountain West",
    "Pacific Coast",
    "Great Plains",
]

# Row = origin region, column = destination region. Diagonal is zero.
# Values are thousands of people who relocated over the decade.
MATRIX: List[List[int]] = [
    #        NE   MW   SE   MtW  PC   GP   <- destination
    [0,   38,  186,  74,  22,  19],   # Northeast left for ...
    [41,   0,  158,  96,  31,  44],   # Midwest
    [52,  47,   0,   61,  40,  33],   # Southeast
    [17,  22,   58,   0,  46,  20],   # Mountain West
    [34,  29,  171, 138,   0,  27],   # Pacific Coast
    [12,  40,   49,  57,  18,   0],   # Great Plains
]

# Brand hue per region — the origin colour travels with the ribbon so a
# reader can follow one region's outflow around the wheel.
def _region_color(accessibility: str = "universal") -> Dict[str, str]:
    """Map each region to its brand hue at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        The palette accessibility level threaded into :func:`load_palette`;
        ``"universal"`` (default) is the colour-vision-safe standard.

    Returns
    -------
    dict of str to str
        ``{region_name: hex}`` for every region.
    """
    palette = load_palette(accessibility)
    return {
        "Northeast":     palette.get("Blue", "#007AFF"),
        "Midwest":       palette.get("Purple", "#AF52DE"),
        "Southeast":     palette.get("Orange", "#FF9500"),
        "Mountain West": palette.get("Green", "#34C759"),
        "Pacific Coast": palette.get("Teal", "#5AC8FA"),
        "Great Plains":  palette.get("Mint", "#00C7BE"),
    }


PALETTE = load_palette()
REGION_COLOR: Dict[str, str] = _region_color()

# Short id per region for CSS class hooks (data-node hover wiring).
REGION_ID: Dict[str, str] = {name: f"n{i}" for i, name in enumerate(REGIONS)}


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
    return point_on_circle(CX, CY, radius, rad)


def _arc_path(r_out: float, r_in: float, a0: float, a1: float) -> str:
    """Return the ``d`` for a filled ring segment with rounded ends.

    The wedge reads as a "floating pill": both radial ends are rounded
    with a quarter-circle cap so adjacent arcs never meet in
    square-notched corners.

    Parameters
    ----------
    r_out, r_in : float
        Outer and inner radii of the ring segment.
    a0, a1 : float
        Start and end angle in degrees (clockwise, 0 = up).

    Returns
    -------
    str
        A closed SVG path describing the rounded wedge.
    """
    r_cap = (r_out - r_in) / 2.0
    r_mid = (r_out + r_in) / 2.0
    cap_deg = math.degrees(r_cap / r_mid)
    if (a1 - a0) <= 2 * cap_deg:
        cap_deg = max((a1 - a0) / 2.0 - 0.01, 0.0)
    ai0 = a0 + cap_deg
    ai1 = a1 - cap_deg
    large = 1 if (ai1 - ai0) > 180 else 0

    x0o, y0o = _polar(r_out, ai0)
    x1o, y1o = _polar(r_out, ai1)
    x1i, y1i = _polar(r_in, ai1)
    x0i, y0i = _polar(r_in, ai0)
    return (
        f"M{x0o:.2f},{y0o:.2f} "
        f"A{r_out:.2f},{r_out:.2f} 0 {large} 1 {x1o:.2f},{y1o:.2f} "
        f"A{r_cap:.2f},{r_cap:.2f} 0 0 1 {x1i:.2f},{y1i:.2f} "
        f"A{r_in:.2f},{r_in:.2f} 0 {large} 0 {x0i:.2f},{y0i:.2f} "
        f"A{r_cap:.2f},{r_cap:.2f} 0 0 1 {x0o:.2f},{y0o:.2f} Z"
    )


def _ribbon_path(
    a0: float, a1: float, b0: float, b1: float, r: float, src_pull: float, dst_pull: float
) -> str:
    """Return the ``d`` for a directed flow ribbon between two arc slices.

    The ribbon spans angles ``[a0, a1]`` on the source arc and
    ``[b0, b1]`` on the target arc, at inner radius ``r``. Its four edges
    are: an arc along the source slice, a cubic Bézier bowing through the
    circle centre to the target slice, an arc along the target slice, and
    a second cubic Bézier back. Two independent control-point pulls make
    the two ends bow by different amounts, which — combined with a
    narrower target slice on the caller side — reads as directional flow.

    Parameters
    ----------
    a0, a1 : float
        Start / end angle (deg) of the source slice.
    b0, b1 : float
        Start / end angle (deg) of the target slice.
    r : float
        Inner ring radius the ribbon attaches to.
    src_pull, dst_pull : float
        Fraction of the centre-ward pull applied to the source-side and
        target-side control points (0 = touch the rim, 1 = the centre).

    Returns
    -------
    str
        A closed SVG path for the ribbon.
    """
    p_a0 = _polar(r, a0)
    p_a1 = _polar(r, a1)
    p_b0 = _polar(r, b0)
    p_b1 = _polar(r, b1)

    def _pull(px: float, py: float, frac: float) -> Tuple[float, float]:
        return CX + (px - CX) * (1.0 - frac), CY + (py - CY) * (1.0 - frac)

    # Two control points per Bézier leg let the ribbon leave the source
    # arc almost radially, sweep through a deep hub, and land tangentially
    # on the target arc — a smoother, more sankey-like sweep than a single
    # quadratic control point.
    c1 = _pull(*p_a1, src_pull)
    c2 = _pull(*p_b0, dst_pull)
    c3 = _pull(*p_b1, dst_pull)
    c4 = _pull(*p_a0, src_pull)
    large_a = 1 if (a1 - a0) > 180 else 0
    large_b = 1 if (b1 - b0) > 180 else 0
    return (
        f"M{p_a0[0]:.2f},{p_a0[1]:.2f} "
        f"A{r:.2f},{r:.2f} 0 {large_a} 1 {p_a1[0]:.2f},{p_a1[1]:.2f} "
        f"C{c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p_b0[0]:.2f},{p_b0[1]:.2f} "
        f"A{r:.2f},{r:.2f} 0 {large_b} 1 {p_b1[0]:.2f},{p_b1[1]:.2f} "
        f"C{c3[0]:.2f},{c3[1]:.2f} {c4[0]:.2f},{c4[1]:.2f} {p_a0[0]:.2f},{p_a0[1]:.2f} Z"
    )


# ------------------------------------------------------------------
# Wheel layout maths
# ------------------------------------------------------------------
def _compute_layout(region_color: Optional[Dict[str, str]] = None) -> Tuple[Dict[int, dict], List[dict]]:
    """Place node arcs and every directed ribbon around the ring.

    The angular budget (360 deg minus the inter-node gaps) is split
    across regions in proportion to each region's throughput (outflow +
    inflow). Within a node's arc, angular sub-slices are allocated to
    each directed flow: first all of that node's *outgoing* flows
    (source ends), then all of its *incoming* flows (target ends). A flow
    i→j therefore attaches to an out-slice on arc i and an in-slice on
    arc j, each exactly as wide as the value it carries.

    Returns
    -------
    groups : dict
        ``{node_index: {"name", "a0", "a1", "mid", "out", "in", "color"}}``
        with arc angles in degrees.
    ribbons : list of dict
        One entry per directed flow with source / target sub-slice
        angles, value, and the source colour.

    Other Parameters
    ----------------
    region_color : dict of str to str, optional
        ``{region_name: hex}`` colour map; defaults to the module-level
        :data:`REGION_COLOR` (the universal palette).
    """
    if region_color is None:
        region_color = REGION_COLOR
    n = len(REGIONS)
    outflow = [sum(MATRIX[i]) for i in range(n)]
    inflow = [sum(MATRIX[k][i] for k in range(n)) for i in range(n)]
    throughput = [outflow[i] + inflow[i] for i in range(n)]
    grand = sum(throughput)
    usable = 360.0 - GAP_DEG * n

    groups: Dict[int, dict] = {}
    cursor = GAP_DEG / 2.0
    for i in range(n):
        span = usable * (throughput[i] / grand) if grand else usable / n
        a0 = cursor
        a1 = cursor + span
        groups[i] = {
            "name": REGIONS[i],
            "a0": a0,
            "a1": a1,
            "mid": (a0 + a1) / 2.0,
            "out": outflow[i],
            "in": inflow[i],
            "color": region_color[REGIONS[i]],
        }
        cursor = a1 + GAP_DEG

    deg_per_unit = usable / grand if grand else 0.0

    # Reserve sub-slices on each arc. Convention: the first part of a
    # node's arc holds its OUTGOING slices (in destination order), the
    # rest holds its INCOMING slices (in origin order). This keeps a
    # node's departures grouped on one side of its wedge and its arrivals
    # on the other, so the wheel reads cleanly.
    out_slice: Dict[Tuple[int, int], Tuple[float, float]] = {}
    in_slice: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for i in range(n):
        c = groups[i]["a0"]
        for j in range(n):
            v = MATRIX[i][j]
            if v <= 0:
                continue
            w = v * deg_per_unit
            out_slice[(i, j)] = (c, c + w)
            c += w
        for k in range(n):
            v = MATRIX[k][i]
            if v <= 0:
                continue
            w = v * deg_per_unit
            in_slice[(k, i)] = (c, c + w)
            c += w

    ribbons: List[dict] = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            v = MATRIX[i][j]
            if v <= 0:
                continue
            a = out_slice[(i, j)]
            b = in_slice[(i, j)]
            ribbons.append({
                "src": i,
                "dst": j,
                "a0": a[0],
                "a1": a[1],
                "b0": b[0],
                "b1": b[1],
                "value": v,
                "color": groups[i]["color"],
            })
    return groups, ribbons


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full dependency-wheel SVG document as a string.

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
    groups, ribbons = _compute_layout(_region_color(accessibility))
    n = len(REGIONS)

    parts: List[str] = []

    title_txt = "The Sun Belt keeps drawing people from the Rust Belt and the Coasts"
    subtitle_txt = (
        "Internal migration between six regions over a decade, in thousands of "
        "people (illustrative data)"
    )
    desc_txt = (
        "Dependency wheel of internal migration between six regions of a "
        "country over a decade. Each region owns an arc on the ring sized by "
        "its total migration throughput; each ribbon is a directed flow "
        "carrying the origin region's colour, with a width proportional to the "
        "thousands of people who moved along it. The Southeast and Mountain "
        "West arcs are dominated by inbound ribbons from the Northeast, "
        "Midwest and Pacific Coast, while little colour flows back the other "
        "way, so the population drain runs in one direction."
    )

    parts.append(svg_open(WIDTH, HEIGHT, "dw-title", "dw-desc", font_family=FONT))
    parts.append(f'<title id="dw-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="dw-desc">{escape(desc_txt)}</desc>')

    # --- CSS: focus/hover a node arc lights only that node's flows ---
    # Every ribbon touching node k carries both class ``src-nK`` (it
    # leaves k) and ``dst-nK`` (it lands on k). Focusing arc k fades all
    # ribbons, then the two rules for k's classes restore its flows.
    hover_rules = "".join(
        f"#arc-{rid}:hover ~ #flows .src-{rid},"
        f"#arc-{rid}:hover ~ #flows .dst-{rid},"
        f"#arc-{rid}:focus ~ #flows .src-{rid},"
        f"#arc-{rid}:focus ~ #flows .dst-{rid}{{opacity:1}}"
        for rid in REGION_ID.values()
    )
    arc_hover_dim = "".join(
        f"#arc-{rid}:hover ~ #flows .flow,"
        f"#arc-{rid}:focus ~ #flows .flow{{opacity:.08}}"
        for rid in REGION_ID.values()
    )
    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule below lives inside a media query). Under
    # prefers-contrast each region deepens to its high-contrast hue: its node
    # arc (fill, keyed on the arc id) and every ribbon it originates (fill +
    # stroke, keyed on the ribbon's source class), so a region's arc and its
    # whole outflow strengthen together and the six regions stay pairwise
    # distinct. Under forced-colors (Windows High Contrast), a ribbon's source
    # identity is carried by colour alone and the ~4-colour system palette cannot
    # preserve a six-region wheel, so each region instead becomes a distinct
    # Canvas/CanvasText *pattern* (hatch / dots / cross): the arc and its whole
    # outflow take the same tile, so the six origins stay pairwise distinguishable
    # without any colour. The patterns live in <defs> and are only referenced
    # inside the forced-colors media block, so the default render is unchanged.
    region_hc = leveled_colors(
        {r["name"]: r["color"] for r in groups.values()}, "high-contrast"
    )
    contrast_rows = "".join(
        f"#arc-{REGION_ID[groups[i]['name']]}{{fill:{region_hc[groups[i]['name']]};}}"
        f".src-{REGION_ID[groups[i]['name']]}"
        f"{{fill:{region_hc[groups[i]['name']]};stroke:{region_hc[groups[i]['name']]};}}"
        for i in range(n)
    )
    adaptive = "@media (prefers-contrast: more){" + contrast_rows + "}"

    # forced-colors: one pattern per region, applied to both the region's arc
    # and every ribbon it originates (`.src-nK`), so the origin encoding survives
    # the system palette.
    region_ids = [REGION_ID[groups[i]["name"]] for i in range(n)]
    fc_selectors = [f"#arc-{rid},.src-{rid}" for rid in region_ids]
    fc_defs, fc_style = forced_color_patterns(fc_selectors, prefix="dwfc")
    parts.append(
        "<style>"
        ".flow{transition:opacity .18s ease}"
        ".arc-hit{cursor:pointer}"
        # Hovering the ribbon layer itself fades every ribbon; the
        # hovered/focused ribbon returns to full opacity.
        "#flows:hover .flow{opacity:.1}"
        "#flows .flow:hover,#flows .flow:focus{opacity:1}"
        # Focusing/hovering a node arc dims all flows, then restores that
        # node's own outgoing + incoming flows.
        f"{arc_hover_dim}"
        f"{hover_rules}"
        ".flow:focus,.arc-hit:focus{outline:none}"
        + adaptive
        + fc_style
        # Additive dark mode: flip paper + the two ink tiers, and flip any
        # multiply-blended ribbon overlap to screen so it lightens on dark.
        + os_dark_style()
        + "</style>"
    )
    # Forced-colors pattern tiles (referenced only inside the forced-colors
    # media block above; inert in the default render).
    parts.append("<defs>" + fc_defs + "</defs>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="52" y="66" font-size="31" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="52" y="102" font-size="18" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    # --- node arcs FIRST so the CSS ``~`` sibling combinator can reach
    # the #flows group that follows them. Each arc is a full-wedge hit
    # target with a stable id the hover rules key on. ---
    for i in range(n):
        g = groups[i]
        rid = REGION_ID[g["name"]]
        d = _arc_path(R_OUTER, R_INNER, g["a0"], g["a1"])
        net = g["in"] - g["out"]
        sign = "+" if net > 0 else ""
        arc_tip = (
            f"{g['name']}: {g['out']}k left, {g['in']}k arrived "
            f"(net {sign}{net}k)"
        )
        parts.append(
            f'<path id="arc-{rid}" class="arc-hit" tabindex="0" role="img" '
            f'aria-label="{escape(arc_tip)}" d="{d}" fill="{g["color"]}">'
            f'<title>{escape(arc_tip)}</title></path>'
        )

    # --- flow ribbons (drawn after arcs; sit visually under them because
    # they attach at the inner radius). Thickest first so thin ribbons
    # layer cleanly on top. ---
    parts.append('<g id="flows">')
    for rb in sorted(ribbons, key=lambda r: -r["value"]):
        # A wider source foot and a slightly narrower target foot, plus a
        # deeper source-side pull, make each ribbon fan out where it
        # leaves and converge where it arrives — a read of direction.
        d = _ribbon_path(
            rb["a0"], rb["a1"], rb["b0"], rb["b1"], R_INNER,
            src_pull=0.86, dst_pull=0.72,
        )
        src_name = groups[rb["src"]]["name"]
        dst_name = groups[rb["dst"]]["name"]
        src_id = REGION_ID[src_name]
        dst_id = REGION_ID[dst_name]
        tip = f"{src_name} → {dst_name}: {rb['value']}k people moved"
        parts.append(
            f'<path class="flow src-{src_id} dst-{dst_id}" tabindex="0" '
            f'role="img" aria-label="{escape(tip)}" d="{d}" '
            f'fill="{rb["color"]}" fill-opacity="0.62" '
            f'stroke="{rb["color"]}" stroke-opacity="0.28" stroke-width="0.6">'
            f'<title>{escape(tip)}</title></path>'
        )
    parts.append("</g>")

    # --- node labels: outside the ring, horizontal, side-anchored ---
    parts.append('<g id="labels">')
    for i in range(n):
        g = groups[i]
        mid = g["mid"]
        lx, ly = _polar(R_OUTER + LABEL_PAD, mid)
        anchor = "end" if mid > 180 else "start"
        # Two-line label: region name in ink, its net-migration figure in
        # secondary ink underneath. The figure used to be tinted with the
        # region's own light hue, but Orange / Green / Teal / Mint on white
        # fail WCAG AA at this size; the arc right beside the label already
        # carries the hue, so the number stays legible in neutral ink.
        net = g["in"] - g["out"]
        sign = "+" if net > 0 else ""
        parts.append(
            f'<text x="{lx:.2f}" y="{ly - 8:.2f}" font-size="21" '
            f'font-weight="600" fill="{INK}" text-anchor="{anchor}" '
            f'dominant-baseline="middle">{escape(g["name"])}</text>'
        )
        parts.append(
            f'<text x="{lx:.2f}" y="{ly + 15:.2f}" font-size="15" '
            f'font-family="{FONT_MONO}" fill="{SUBINK}" '
            f'text-anchor="{anchor}" dominant-baseline="middle">'
            f'net {sign}{net}k</text>'
        )
    parts.append("</g>")

    # --- centre annotation: the takeaway number, quietly. Southeast +
    # Mountain West combined net gain vs the three losing regions. ---
    se = REGIONS.index("Southeast")
    mtw = REGIONS.index("Mountain West")
    sunbelt_net = (
        (groups[se]["in"] - groups[se]["out"]) + (groups[mtw]["in"] - groups[mtw]["out"])
    )
    # Soft white backing disk so the hub label stays legible over the
    # ribbon crossings without any dark halo or hard outline.
    parts.append(
        f'<circle cx="{CX:.1f}" cy="{CY:.1f}" r="104" fill="{BG}" '
        f'fill-opacity="0.86"/>'
    )
    parts.append(
        f'<text x="{CX:.1f}" y="{CY - 30:.1f}" text-anchor="middle" '
        f'font-size="17" fill="{SUBINK}">Sun Belt net gain</text>'
    )
    # Hero number in ink: the Southeast orange used before dips to 2.2:1 on
    # white (below WCAG AA even for large text). The "net gain" caption above
    # carries the warm-growth read; ink keeps the number crisp for everyone.
    parts.append(
        f'<text x="{CX:.1f}" y="{CY + 14:.1f}" text-anchor="middle" '
        f'font-family="{FONT_MONO}" font-size="42" font-weight="700" '
        f'fill="{INK}">+{sunbelt_net}k</text>'
    )
    parts.append(
        f'<text x="{CX:.1f}" y="{CY + 44:.1f}" text-anchor="middle" '
        f'font-size="16" fill="{SUBINK}">over the decade</text>'
    )

    # --- footnote: read the encoding + hover affordance ---
    parts.append(
        f'<text x="52" y="{HEIGHT - 40}" font-size="15" '
        f'fill="{SUBINK}">Arc size ∝ a region’s total migration · '
        f'ribbon width ∝ people moved · ribbon colour = where they left '
        f'from · hover or focus a region to trace its flows</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the dependency-wheel SVG to the skill's example asset folder."""
    render_cli(__file__, "dependency-wheel", build_svg, description="Render the dependency-wheel SVG.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
make_chord — publication-quality chord diagram as a hand-authored SVG.

A chord diagram lays every category on the rim of a circle and draws a
ribbon between two categories whose width encodes the volume that flows
between them. It answers "who exchanges how much with whom?" for a dense
category-by-category matrix far better than a grid of numbers or a
grouped bar chart, because the eye reads ribbon width as magnitude and
the ring makes every pairwise relationship visible at once.

Vega-Lite has no native chord mark, so this figure is built as an SVG
string by hand rather than through ``vl_convert``. The layout is the
classic circular one:

* **Group arcs** — each category owns a wedge of the ring; the wedge's
  angular span is proportional to that category's total flow (its row
  plus column sum in the matrix). Small gaps separate the wedges.
* **Chord ribbons** — a ribbon leaves a slice of the source arc and
  lands on a slice of the target arc. Its two ends are quadratic Bézier
  curves that bow toward the circle centre, so thick exchanges read as
  fat lens-shaped ribbons. Ribbon width at each end equals that end's
  share of the flow.

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, rounded
label treatment, a start-anchored title plus a one-line takeaway
subtitle.

Interaction (no JavaScript): every ribbon and every arc carries a
native ``<title>`` tooltip with its exact volume, and a CSS ``:hover`` /
``:focus`` rule dims the rest of the diagram so the hovered chord — or
every chord touching a hovered arc — pops. This is the "hover a chord to
trace it" affordance that suits this capability. The figure is otherwise
static (a chord diagram does not benefit from animation), so
``animated`` is false and ``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/chord.svg``.

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
from _svg import point_on_circle, svg_open  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1080
HEIGHT = 1140
CX = WIDTH / 2.0
CY = HEIGHT / 2.0 + 34      # nudge down to leave room for the title block
R_OUTER = 372              # outer radius of the group-arc ring
ARC_THICK = 30             # radial thickness of a group arc
R_INNER = R_OUTER - ARC_THICK
GAP_DEG = 3.4              # angular gap (deg) between adjacent group arcs
LABEL_PAD = 22             # radial gap between arc and its text label

INK = "#1D1D1F"            # primary text
SUBINK = "#6E6E73"         # secondary text
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"


# ------------------------------------------------------------------
# The story (illustrative but plausible): one sprint of cross-team code
# reviews at an engineering org. Cell (i, j) = pull requests authored by
# team i that team j reviewed. The diagonal (self-review within a team)
# is dropped — a chord diagram is about the *exchanges between* groups.
# The takeaway: the Platform team reviews nearly everyone's code but is
# rarely reviewed back — a review bottleneck hiding in plain sight.
# ------------------------------------------------------------------
TEAMS: List[str] = ["Platform", "Payments", "Growth", "Mobile", "Data"]

# Row = author team, Column = reviewer team. Diagonal is zero (ignored).
# Values are pull requests reviewed during the sprint.
MATRIX: List[List[int]] = [
    #            Plat  Pay  Grow  Mob  Data   <- reviewer
    [0,   14,  11,   9,   7],   # Platform authored, reviewed by ...
    [22,   0,   4,   3,   6],   # Payments
    [19,   3,   0,   5,   2],   # Growth
    [17,   4,   6,   0,   3],   # Mobile
    [15,   8,   2,   1,   0],   # Data
]

# Brand hue per team — origin color travels with the ribbon.
def _team_color(accessibility: str = "universal") -> Dict[str, str]:
    """Map each team to its brand hue at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        The palette accessibility level threaded into :func:`load_palette`;
        ``"universal"`` (default) is the colour-vision-safe standard.

    Returns
    -------
    dict of str to str
        ``{team_name: hex}`` for every team.
    """
    palette = load_palette(accessibility)
    return {
        "Platform": palette.get("Blue", "#007AFF"),
        "Payments": palette.get("Green", "#34C759"),
        "Growth": palette.get("Orange", "#FF9500"),
        "Mobile": palette.get("Purple", "#AF52DE"),
        "Data": palette.get("Teal", "#5AC8FA"),
    }


PALETTE = load_palette()
TEAM_COLOR: Dict[str, str] = _team_color()


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
    with a quarter-circle cap of radius ``(r_out - r_in) / 2`` so
    adjacent arcs never meet in square-notched corners. The inter-arc
    gap in :data:`GAP_DEG` keeps the pills visually separated.

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
    # Convert the cap's pixel radius into an angular inset at the ring's
    # mid-line so the straight ends recede by one cap radius.
    cap_deg = math.degrees(r_cap / r_mid)
    # Guard against a cap wider than the arc itself (tiny arcs stay square).
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


def _ribbon_path(a0: float, a1: float, b0: float, b1: float, r: float) -> str:
    """Return the ``d`` for a chord ribbon between two arc slices.

    The ribbon spans angles ``[a0, a1]`` on the source arc and
    ``[b0, b1]`` on the target arc, at inner radius ``r``. Its four edges
    are: an arc along the source slice, a quadratic Bézier bowing through
    the circle centre to the target slice, an arc along the target slice,
    and a second Bézier back. Bowing toward the centre gives the classic
    lens shape and keeps thick ribbons from crossing the ring.

    Parameters
    ----------
    a0, a1 : float
        Start / end angle (deg) of the source slice.
    b0, b1 : float
        Start / end angle (deg) of the target slice.
    r : float
        Inner ring radius the ribbon attaches to.

    Returns
    -------
    str
        A closed SVG path for the ribbon.
    """
    p_a0 = _polar(r, a0)
    p_a1 = _polar(r, a1)
    p_b0 = _polar(r, b0)
    p_b1 = _polar(r, b1)
    # Pull the Bézier control point toward the centre so the ribbon bows
    # inward. A pull proportional to the angular distance keeps near
    # neighbours gently curved and far exchanges deeply bowed.
    def _ctrl(pa: Tuple[float, float], pb: Tuple[float, float]) -> Tuple[float, float]:
        mx, my = (pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0
        return CX + (mx - CX) * 0.28, CY + (my - CY) * 0.28

    c1 = _ctrl(p_a1, p_b0)
    c2 = _ctrl(p_b1, p_a0)
    large_a = 1 if (a1 - a0) > 180 else 0
    large_b = 1 if (b1 - b0) > 180 else 0
    return (
        f"M{p_a0[0]:.2f},{p_a0[1]:.2f} "
        f"A{r:.2f},{r:.2f} 0 {large_a} 1 {p_a1[0]:.2f},{p_a1[1]:.2f} "
        f"Q{c1[0]:.2f},{c1[1]:.2f} {p_b0[0]:.2f},{p_b0[1]:.2f} "
        f"A{r:.2f},{r:.2f} 0 {large_b} 1 {p_b1[0]:.2f},{p_b1[1]:.2f} "
        f"Q{c2[0]:.2f},{c2[1]:.2f} {p_a0[0]:.2f},{p_a0[1]:.2f} Z"
    )


# ------------------------------------------------------------------
# Chord layout maths
# ------------------------------------------------------------------
def _compute_layout(team_color: Optional[Dict[str, str]] = None) -> Tuple[Dict[int, dict], List[dict]]:
    """Place group arcs and every ribbon around the ring.

    The angular budget (360 deg minus the inter-group gaps) is split
    across teams in proportion to each team's total flow. Within a team's
    arc, angular sub-slices are allocated to each partner exchange, so a
    ribbon attaches to a wedge exactly as wide as the volume it carries.

    Parameters
    ----------
    team_color : dict of str to str, optional
        ``{team_name: hex}`` colour map; defaults to the module-level
        :data:`TEAM_COLOR` (the universal palette).

    Returns
    -------
    groups : dict
        ``{team_index: {"name", "a0", "a1", "mid", "total", "color"}}``
        with arc angles in degrees.
    ribbons : list of dict
        One entry per unordered team pair carrying combined volume, the
        source / target sub-slice angles, the dominant direction, and the
        per-direction volumes for the tooltip.
    """
    if team_color is None:
        team_color = TEAM_COLOR
    n = len(TEAMS)
    # Total flow per team = everything it authored + everything it
    # reviewed (row sum + column sum), so the arc reflects total
    # involvement in the review network.
    totals = [
        sum(MATRIX[i]) + sum(MATRIX[k][i] for k in range(n))
        for i in range(n)
    ]
    grand = sum(totals)
    usable = 360.0 - GAP_DEG * n  # angle left after the gaps

    groups: Dict[int, dict] = {}
    cursor = GAP_DEG / 2.0
    # Per-team running angular cursor for laying sub-slices inside the arc.
    slice_cursor: Dict[int, float] = {}
    for i in range(n):
        span = usable * (totals[i] / grand) if grand else usable / n
        a0 = cursor
        a1 = cursor + span
        groups[i] = {
            "name": TEAMS[i],
            "a0": a0,
            "a1": a1,
            "mid": (a0 + a1) / 2.0,
            "total": totals[i],
            "color": team_color[TEAMS[i]],
        }
        slice_cursor[i] = a0
        cursor = a1 + GAP_DEG

    # Degrees-per-unit, shared by every arc so widths are comparable.
    deg_per_unit = usable / grand if grand else 0.0

    # Order the sub-slices within each arc: for team i, iterate partners in
    # a stable order (by index) and reserve, in turn, the slice for flow
    # i->j and the slice for flow j->i (so both directions of a pair sit
    # adjacent and the ribbon is drawn once).
    ribbons: List[dict] = []
    # Reserve source-side and target-side slices deterministically.
    slice_of: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            v = MATRIX[i][j]
            if v <= 0:
                continue
            w = v * deg_per_unit
            s0 = slice_cursor[i]
            s1 = s0 + w
            slice_cursor[i] = s1
            slice_of[(i, j)] = (s0, s1)

    # Now build one ribbon per unordered pair {i, j}, joining the two
    # directed slices (i->j on i's arc, j->i on j's arc).
    seen: set[Tuple[int, int]] = set()
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            key = (min(i, j), max(i, j))
            if key in seen:
                continue
            seen.add(key)
            v_ij = MATRIX[i][j]
            v_ji = MATRIX[j][i]
            combined = v_ij + v_ji
            if combined <= 0:
                continue
            # Source-side slice = the pair's slice on the higher-volume
            # team's arc, so the ribbon's color follows the dominant sender.
            if v_ij >= v_ji:
                src, dst = i, j
                v_src, v_dst = v_ij, v_ji
            else:
                src, dst = j, i
                v_src, v_dst = v_ji, v_ij
            a_slice = slice_of.get((src, dst))
            b_slice = slice_of.get((dst, src))
            if a_slice is None or b_slice is None:
                continue
            ribbons.append({
                "src": src,
                "dst": dst,
                "a0": a_slice[0],
                "a1": a_slice[1],
                "b0": b_slice[0],
                "b1": b_slice[1],
                "v_src": v_src,
                "v_dst": v_dst,
                "combined": combined,
                "color": groups[src]["color"],
            })
    return groups, ribbons


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full chord-diagram SVG document as a string.

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
    team_color = _team_color(accessibility)
    groups, ribbons = _compute_layout(team_color)
    n = len(TEAMS)

    parts: List[str] = []

    title_txt = "Platform reviews everyone's code and is rarely reviewed back"
    subtitle_txt = (
        "Cross-team pull-request reviews over one sprint (illustrative data)"
    )
    desc_txt = (
        "Chord diagram of code reviews exchanged between five engineering "
        "teams during one sprint. Each team owns an arc sized by its total "
        "review activity; each ribbon links two teams with a width "
        "proportional to the pull requests they reviewed for each other. "
        "The Platform team's inbound reviews dwarf its outbound ones: it "
        "reviews nearly everyone's code but few teams review Platform's."
    )

    parts.append(svg_open(WIDTH, HEIGHT, "chord-title", "chord-desc", font_family=FONT))
    parts.append(f'<title id="chord-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="chord-desc">{escape(desc_txt)}</desc>')

    # OS-adaptive overrides (additive; the default render is byte-for-byte
    # unchanged because every rule below lives inside a media query). Under
    # prefers-contrast each team deepens to its high-contrast hue on both fill
    # and stroke, so its arc and every ribbon it colours strengthen together and
    # the five teams stay pairwise distinct for a low-vision reader.
    team_series = {f".team-{i}": team_color[TEAMS[i]] for i in range(n)}
    adaptive = os_adaptive_style(team_series, role="both")
    # forced-colors (Windows High Contrast): a ribbon's source-team identity is
    # carried by colour alone (the arcs carry rim labels, the ribbons do not),
    # and the ~4-colour system palette would merge all five teams into one ink.
    # Give each team a distinct Canvas/CanvasText hatch/dot/cross pattern so the
    # five arc + ribbon families stay separable without colour. The pattern defs
    # are inert at the default render (referenced only inside the forced-colors
    # media query), so the shipped SVG is byte-for-byte unchanged.
    fcp_defs, fcp_style = forced_color_patterns(
        [f".team-{i}" for i in range(n)], prefix="chord-fcp"
    )
    # --- CSS: hover/focus one ribbon (or one arc) dims the rest ---
    parts.append(
        "<style>"
        ".chord{transition:opacity .18s ease}"
        ".arc{transition:opacity .18s ease}"
        # Hovering anywhere on the ribbon layer fades every ribbon; the
        # hovered/focused ribbon returns to full opacity.
        "#chords:hover .chord{opacity:.12}"
        "#chords .chord:hover,#chords .chord:focus{opacity:1}"
        # Hovering a group arc fades all ribbons, then the CSS class shared
        # by that arc's ribbons brings them back (see data-team below).
        ".chord:focus,.arc:focus{outline:none}"
        + adaptive
        + fcp_style
        # Paper + ink flip; the semi-transparent white hub disk inverts to a soft
        # dark disk that keeps dimming the ribbon crossings behind the hub label.
        # Ribbons are semi-transparent data hues and read on dark, so untouched.
        + os_dark_style()
        + "</style>"
    )
    parts.append(f"<defs>{fcp_defs}</defs>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="46" y="62" font-size="30" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="46" y="96" font-size="18" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    # --- ribbons (drawn first, under the arcs) ---
    parts.append('<g id="chords">')
    # Thickest first so thin ribbons layer cleanly on top.
    for rb in sorted(ribbons, key=lambda r: -r["combined"]):
        d = _ribbon_path(rb["a0"], rb["a1"], rb["b0"], rb["b1"], R_INNER)
        src_name = groups[rb["src"]]["name"]
        dst_name = groups[rb["dst"]]["name"]
        # Tooltip states both directions explicitly (asymmetric flow).
        tip = (
            f"{src_name} ↔ {dst_name}: {rb['combined']} reviews "
            f"({src_name} reviewed {rb['v_src']} of {dst_name}'s PRs, "
            f"{dst_name} reviewed {rb['v_dst']} of {src_name}'s)"
        )
        parts.append(
            f'<path class="chord team-{rb["src"]}" tabindex="0" role="img" '
            f'aria-label="{escape(tip)}" d="{d}" fill="{rb["color"]}" '
            f'fill-opacity="0.5" stroke="{rb["color"]}" stroke-opacity="0.35" '
            f'stroke-width="0.6">'
            f'<title>{escape(tip)}</title></path>'
        )
    parts.append("</g>")

    # --- group arcs + labels ---
    parts.append('<g id="arcs">')
    for i in range(n):
        g = groups[i]
        d = _arc_path(R_OUTER, R_INNER, g["a0"], g["a1"])
        arc_tip = f"{g['name']}: {g['total']} reviews in and out this sprint"
        parts.append(
            f'<path class="arc team-{i}" tabindex="0" role="img" '
            f'aria-label="{escape(arc_tip)}" d="{d}" fill="{g["color"]}">'
            f'<title>{escape(arc_tip)}</title></path>'
        )

        # Label: place it radially outside the arc, rotated to sit tangent
        # to the ring, flipping on the left half so text never reads upside
        # down.
        mid = g["mid"]
        lx, ly = _polar(R_OUTER + LABEL_PAD, mid)
        # Horizontal labels (no rotation): anchor by side so each reads outward.
        anchor = "end" if mid > 180 else "start"
        parts.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="20" '
            f'font-weight="600" fill="{INK}" text-anchor="{anchor}" '
            f'dominant-baseline="middle">'
            f'{escape(g["name"])}</text>'
        )
    parts.append("</g>")

    # --- centre annotation: the takeaway number, quietly ---
    # Platform's inbound vs outbound imbalance, spelled out at the hub.
    plat = TEAMS.index("Platform")
    inbound = sum(MATRIX[k][plat] for k in range(n))   # PRs Platform reviewed
    outbound = sum(MATRIX[plat])                        # PRs of Platform reviewed
    # Soft white backing disk so the hub label stays legible over the
    # ribbon crossings without any dark halo or hard outline.
    parts.append(
        f'<circle cx="{CX:.1f}" cy="{CY:.1f}" r="96" fill="{BG}" '
        f'fill-opacity="0.82"/>'
    )
    parts.append(
        f'<text x="{CX:.1f}" y="{CY - 24:.1f}" text-anchor="middle" '
        f'font-size="18" fill="{SUBINK}">Platform reviewed</text>'
    )
    parts.append(
        f'<text x="{CX:.1f}" y="{CY + 18:.1f}" text-anchor="middle" '
        f'font-family="{FONT_MONO}" font-size="38" font-weight="700" '
        f'fill="{team_color["Platform"]}">{inbound} vs {outbound}</text>'
    )
    parts.append(
        f'<text x="{CX:.1f}" y="{CY + 48:.1f}" text-anchor="middle" '
        f'font-size="18" fill="{SUBINK}">given vs received</text>'
    )

    # --- footnote: read the hover affordance ---
    parts.append(
        f'<text x="46" y="{HEIGHT - 34}" font-size="15" '
        f'fill="{SUBINK}">Arc size ∝ a team\'s total reviews · ribbon width '
        f'∝ reviews exchanged · hover or focus a chord to trace it</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the chord-diagram SVG to the skill's example asset folder."""
    render_cli(__file__, "chord", build_svg, description="Render the chord SVG.")


if __name__ == "__main__":
    main()

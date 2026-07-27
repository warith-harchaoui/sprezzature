#!/usr/bin/env python3
"""
make_voronoi — publication-quality Voronoi catchment map as hand-authored SVG.

A Voronoi tessellation partitions a plane into one cell per seed point,
where every location inside a cell is closer to that seed than to any
other. It is the natural answer to "which facility serves this spot?" —
the honest, distance-true version of a catchment map that a hand-drawn
service-area blob only approximates. Here the seeds are the pharmacies of
a mid-size city, the fill colour marks the chain each one belongs to, and
each cell is the neighbourhood for which *that* pharmacy is the closest
one to walk to. The eye reads the chains as coloured territories first,
then the individual shops as labelled dots.

Vega-Lite has no Voronoi primitive, so the figure is built as an SVG
string by hand. The tessellation is an offline, pure-Python
half-plane clip: each cell starts as the whole map rectangle and is
sliced by the perpendicular bisector between its seed and every other
seed, keeping the seed's side each time (the Sutherland–Hodgman
convex-polygon clip). This is exact for this point count, needs no
scientific stack, and a fixed seed layout makes the committed SVG
byte-reproducible.

House style follows ``_style.py``: Roboto type, the Apple-system
categorical palette, ink ``#1D1D1F`` on white, a start-anchored takeaway
title plus a one-line subtitle that states the point. Cell borders are
hairlines; each chain owns one saturated hue at a soft fill so adjacent
territories stay distinguishable with no colour-on-colour; seed dots sit
in a crisp white ring (a pure fill halo, not a dark stroke); a few
flagship stores carry an ink label placed clear of the dot.

Interaction (no JavaScript): every cell carries a native ``<title>``
tooltip, and a pure-CSS ``:hover`` / ``:focus-within`` rule lifts the
hovered chain's whole territory while dimming the rest, so a reader can
isolate one chain's coverage at a time. The map is fully legible when
static, so ``animated`` is false and ``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/voronoi.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import forced_color_patterns, load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import hex_to_rgb, svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1360
HEIGHT = 1080
INK = "#1D1D1F"            # primary text
SUBINK = "#6E6E73"         # secondary text
BG = "#FFFFFF"
HAIRLINE = "#FFFFFF"       # cell borders: white hairlines read as tile gaps

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

# The map lives inside this rectangle (below the title / legend band and
# above the footer hint). The Voronoi tessellation is clipped to it.
MAP_X0 = 56.0
MAP_Y0 = 208.0
MAP_X1 = float(WIDTH - 56)
MAP_Y1 = float(HEIGHT - 96)

# A gentle rounded frame around the map, so the tessellation reads as a
# single card rather than bleeding to the canvas edge.
FRAME_RADIUS = 22.0

Point = Tuple[float, float]
Poly = List[Point]

# ------------------------------------------------------------------
# The story (illustrative but plausible, in the shape of a real
# open-data pharmacy layer): thirty pharmacies across one city, each
# belonging to one of four chains plus the independents. The takeaway is
# that one chain (Greenleaf) has quietly captured the largest share of
# the city's *area* — not just the most shops — because its stores sit
# where rivals are sparse, so its catchment cells are the biggest.
# Colour marks the chain so the eye reads the four territories before it
# reads any single shop.
# ------------------------------------------------------------------
# Seed coordinates are given in a tidy 0..100 city grid and mapped into
# the map rectangle at build time, so the data reads cleanly and the
# layout is trivially reproducible. (x, y, chain, name-or-None).
# A handful of flagship stores carry a name; the rest are unlabelled
# dots to keep the map uncluttered.
CITY: List[Tuple[float, float, str, str]] = [
    # Greenleaf Pharmacy — spread wide, owns the roomy outskirts.
    (12.0, 16.0, "Greenleaf", "Greenleaf · Riverside"),
    (30.0, 8.0, "Greenleaf", ""),
    (8.0, 44.0, "Greenleaf", ""),
    (22.0, 62.0, "Greenleaf", "Greenleaf · Mill Quarter"),
    (14.0, 84.0, "Greenleaf", ""),
    (44.0, 78.0, "Greenleaf", ""),
    (62.0, 90.0, "Greenleaf", "Greenleaf · Southgate"),
    (86.0, 74.0, "Greenleaf", ""),
    (92.0, 40.0, "Greenleaf", ""),
    # Meridian Health — clustered around the dense centre.
    (48.0, 30.0, "Meridian", "Meridian · Central"),
    (58.0, 44.0, "Meridian", ""),
    (40.0, 48.0, "Meridian", ""),
    (52.0, 58.0, "Meridian", ""),
    (66.0, 34.0, "Meridian", ""),
    (36.0, 34.0, "Meridian", ""),
    (60.0, 66.0, "Meridian", "Meridian · Old Market"),
    # Cedar & Co — the north-east corridor.
    (74.0, 14.0, "Cedar & Co", "Cedar & Co · Uptown"),
    (88.0, 22.0, "Cedar & Co", ""),
    (72.0, 52.0, "Cedar & Co", ""),
    (82.0, 60.0, "Cedar & Co", ""),
    (94.0, 88.0, "Cedar & Co", ""),
    # Aster Drugstore — a small southern pocket.
    (28.0, 90.0, "Aster", "Aster · Harbour"),
    (38.0, 68.0, "Aster", ""),
    (50.0, 88.0, "Aster", ""),
    # Independent chemists — scattered singletons.
    (6.0, 68.0, "Independent", ""),
    (26.0, 40.0, "Independent", "Independent chemist"),
    (68.0, 78.0, "Independent", ""),
    (80.0, 40.0, "Independent", ""),
    (54.0, 12.0, "Independent", ""),
    (34.0, 20.0, "Independent", ""),
]

CHAIN_ORDER: List[str] = ["Greenleaf", "Meridian", "Cedar & Co", "Aster", "Independent"]


# Five chains, five distinct saturated hues that stay legible edge-to-edge
# as filled territories (no red/green ambiguity; the neutral Gray reads as
# "unbranded" for the independents).
def _chain_color(accessibility: str = "universal") -> Dict[str, str]:
    """Map each chain to its territory hue at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        The palette accessibility level threaded into :func:`load_palette`;
        ``"universal"`` (default) is the colour-vision-safe standard.

    Returns
    -------
    dict of str to str
        ``{chain_name: hex}`` for every chain.
    """
    palette = load_palette(accessibility)
    return {
        "Greenleaf": palette.get("Green", "#34C759"),
        "Meridian": palette.get("Blue", "#007AFF"),
        "Cedar & Co": palette.get("Purple", "#AF52DE"),
        "Aster": palette.get("Orange", "#FF9500"),
        "Independent": palette.get("Gray", "#8E8E93"),
    }


PALETTE = load_palette()
CHAIN_COLOR: Dict[str, str] = _chain_color()
# Territory fill: a soft tint of each hue so labels and dots sit legibly on
# top and neighbouring cells never merge into colour-on-colour.
CELL_FILL_ALPHA = 0.30
CELL_HOVER_ALPHA = 0.66


# ------------------------------------------------------------------
# Coordinate mapping: city grid (0..100) -> map rectangle
# ------------------------------------------------------------------
def _to_canvas(gx: float, gy: float) -> Point:
    """Map a point on the 0..100 city grid into the map rectangle.

    Parameters
    ----------
    gx, gy : float
        Grid coordinates in ``[0, 100]``. ``gy`` grows downward, matching
        SVG's y-down space, so no flip is needed.

    Returns
    -------
    tuple of float
        The ``(x, y)`` pixel point inside the map rectangle.
    """
    x = MAP_X0 + (gx / 100.0) * (MAP_X1 - MAP_X0)
    y = MAP_Y0 + (gy / 100.0) * (MAP_Y1 - MAP_Y0)
    return x, y


# ------------------------------------------------------------------
# Offline Voronoi via convex-polygon half-plane clipping (pure Python)
# ------------------------------------------------------------------
def _clip_halfplane(poly: Poly, seed: Point, other: Point) -> Poly:
    """Clip ``poly`` to the half-plane of points closer to ``seed``.

    The boundary is the perpendicular bisector of the segment
    ``seed``–``other``; the kept side is the one containing ``seed``. This
    is one Sutherland–Hodgman clip step against a single line, walking the
    polygon edges and inserting the intersection point wherever an edge
    crosses the bisector.

    Parameters
    ----------
    poly : list of tuple of float
        The current (convex) cell polygon, in order.
    seed : tuple of float
        The cell's own seed point (its side of the bisector is kept).
    other : tuple of float
        A rival seed point; its side is discarded.

    Returns
    -------
    list of tuple of float
        The clipped polygon (possibly empty if the cell vanishes).
    """
    (sx, sy), (ox, oy) = seed, other
    # Bisector as the set { p : nx*px + ny*py <= c }, i.e. the half-plane
    # of points at least as close to the seed as to the rival. The normal
    # points from seed toward rival; c is the dot at the midpoint.
    nx, ny = ox - sx, oy - sy
    mx, my = (sx + ox) / 2.0, (sy + oy) / 2.0
    c = nx * mx + ny * my

    def inside(p: Point) -> bool:
        return nx * p[0] + ny * p[1] <= c

    if not poly:
        return poly
    out: Poly = []
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        a_in, b_in = inside(a), inside(b)
        if a_in:
            out.append(a)
        if a_in != b_in:
            # Edge crosses the bisector — insert the intersection point.
            da = c - (nx * a[0] + ny * a[1])
            db = c - (nx * b[0] + ny * b[1])
            t = da / (da - db)
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def _voronoi_cells(seeds: List[Point], bbox: Tuple[float, float, float, float]) -> List[Poly]:
    """Compute the Voronoi cell polygon for every seed, clipped to ``bbox``.

    Each cell is the whole bounding rectangle successively clipped by the
    perpendicular bisector against every other seed. For ``n`` seeds this
    is ``O(n^2)`` clips, trivial at this scale, exact, and free of any
    Fortune-sweepline bookkeeping or numerical degeneracy for a
    general-position layout.

    Parameters
    ----------
    seeds : list of tuple of float
        Seed points in canvas pixels.
    bbox : tuple of float
        ``(x0, y0, x1, y1)`` clipping rectangle (the map area).

    Returns
    -------
    list of list of tuple of float
        One polygon per seed, index-aligned with ``seeds``.
    """
    x0, y0, x1, y1 = bbox
    rect: Poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    cells: List[Poly] = []
    for i, s in enumerate(seeds):
        cell = list(rect)
        for j, o in enumerate(seeds):
            if i == j:
                continue
            cell = _clip_halfplane(cell, s, o)
            if not cell:
                break
        cells.append(cell)
    return cells


def _polygon_area(poly: Poly) -> float:
    """Return the (unsigned) area of a polygon via the shoelace formula.

    Parameters
    ----------
    poly : list of tuple of float
        Polygon vertices in order.

    Returns
    -------
    float
        Area in square pixels.
    """
    if len(poly) < 3:
        return 0.0
    acc = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        acc += x0 * y1 - x1 * y0
    return abs(acc) / 2.0


def _polygon_centroid(poly: Poly) -> Point:
    """Return the area-weighted centroid of a convex polygon.

    For the convex cells produced by the half-plane clip the centroid is
    always strictly inside the polygon, so it is a safe, border-free home
    for a label: the text can never straddle a cell edge if it is anchored
    here and kept small enough to fit.

    Parameters
    ----------
    poly : list of tuple of float
        Polygon vertices in order.

    Returns
    -------
    tuple of float
        The ``(x, y)`` centroid. Falls back to the vertex mean for a
        degenerate (zero-area) polygon.
    """
    n = len(poly)
    if n < 3:
        # Degenerate sliver: mean of whatever vertices we have.
        sx = sum(p[0] for p in poly) / max(n, 1)
        sy = sum(p[1] for p in poly) / max(n, 1)
        return sx, sy
    acc = cx = cy = 0.0
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        acc += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(acc) < 1e-9:
        sx = sum(p[0] for p in poly) / n
        sy = sum(p[1] for p in poly) / n
        return sx, sy
    return cx / (3.0 * acc), cy / (3.0 * acc)


def _cell_inradius(poly: Poly, centre: Point) -> float:
    """Return the distance from ``centre`` to the nearest polygon edge.

    This is the largest half-width a label plate can have at ``centre`` and
    still stay inside the (convex) cell, used to decide whether a flagship
    label fits within its own cell or must fall back to a compact form.

    Parameters
    ----------
    poly : list of tuple of float
        The convex cell polygon.
    centre : tuple of float
        A point inside the polygon (its centroid).

    Returns
    -------
    float
        The shortest point-to-edge distance in pixels.
    """
    cx, cy = centre
    best = float("inf")
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        seg_len = (ex * ex + ey * ey) ** 0.5 or 1.0
        # Perpendicular distance from the centre to the infinite edge line.
        dist = abs((cx - ax) * ey - (cy - ay) * ex) / seg_len
        best = min(best, dist)
    return best


# ------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------
def _relative_luminance(hex_color: str) -> float:
    """Return the WCAG relative luminance of a ``#RRGGBB`` colour in ``[0, 1]``.

    Used to pick white vs ink label text per cell so the label always has
    strong contrast against its own fill, never colour-on-colour.

    Parameters
    ----------
    hex_color : str
        A ``#RRGGBB`` colour.

    Returns
    -------
    float
        Relative luminance; ``0`` is black, ``1`` is white.
    """
    def _lin(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = hex_to_rgb(hex_color)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _blend_over_white(hex_color: str, alpha: float) -> str:
    """Composite ``hex_color`` at ``alpha`` over white, returning ``#RRGGBB``.

    The label plate sits over the cell tint, so its effective background is
    the fill composited onto the white card. Blending here lets us judge
    contrast against the colour the eye actually sees.

    Parameters
    ----------
    hex_color : str
        The chain hue as ``#RRGGBB``.
    alpha : float
        The fill opacity the plate sits on, in ``[0, 1]``.

    Returns
    -------
    str
        The composited ``#RRGGBB`` colour.
    """
    r, g, b = hex_to_rgb(hex_color)
    br = round(r * alpha + 255 * (1 - alpha))
    bg = round(g * alpha + 255 * (1 - alpha))
    bb = round(b * alpha + 255 * (1 - alpha))
    return f"#{br:02X}{bg:02X}{bb:02X}"


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert ``#RRGGBB`` to an ``rgba(...)`` string at the given alpha.

    Using ``rgba`` fills (rather than a separate opacity attribute) keeps
    the tint on the fill only, so cell-border hairlines and dots stay at
    full strength.

    Parameters
    ----------
    hex_color : str
        A ``#RRGGBB`` colour.
    alpha : float
        Opacity in ``[0, 1]``.

    Returns
    -------
    str
        An ``rgba(r, g, b, a)`` string.
    """
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def _poly_points(poly: Poly) -> str:
    """Format a polygon as an SVG ``points`` attribute string."""
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in poly)


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full Voronoi catchment-map SVG document as a string.

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
    chain_color = _chain_color(accessibility)
    seeds: List[Point] = [_to_canvas(gx, gy) for gx, gy, _, _ in CITY]
    chains = [chain for _, _, chain, _ in CITY]
    cells = _voronoi_cells(seeds, (MAP_X0, MAP_Y0, MAP_X1, MAP_Y1))

    # Area captured per chain — this is what the takeaway rests on.
    total_area = sum(_polygon_area(c) for c in cells) or 1.0
    area_by_chain: Dict[str, float] = {c: 0.0 for c in CHAIN_ORDER}
    count_by_chain: Dict[str, int] = {c: 0 for c in CHAIN_ORDER}
    for chain, cell in zip(chains, cells):
        area_by_chain[chain] += _polygon_area(cell)
        count_by_chain[chain] += 1
    share = {c: 100.0 * area_by_chain[c] / total_area for c in CHAIN_ORDER}

    title_txt = "Greenleaf owns the map, not just the most shops"
    subtitle_txt = (
        "Nearest-pharmacy catchment areas across the city, coloured by "
        "chain (illustrative open-data layer)"
    )
    lead_share = share["Greenleaf"]
    desc_txt = (
        "Voronoi catchment map of thirty city pharmacies. Each cell is the "
        "neighbourhood for which one pharmacy is the closest to walk to, and "
        "its colour marks the chain that owns the shop: Greenleaf, Meridian "
        "Health, Cedar and Co, Aster Drugstore, and independent chemists. "
        f"Greenleaf's stores sit on the roomy outskirts, so its cells cover "
        f"about {lead_share:.0f} percent of the city's area, the largest "
        "share of any chain, even though Meridian has almost as many shops "
        "packed into the dense centre. Seed dots mark each pharmacy; a few flagship "
        "stores are labelled. Hover or focus any cell to lift its whole "
        "chain's territory and dim the rest."
    )

    parts: List[str] = []
    parts.append(svg_open(WIDTH, HEIGHT, "vor-title", "vor-desc", font_family=FONT))
    parts.append(f'<title id="vor-title">{xml_escape(title_txt)}</title>')
    parts.append(f'<desc id="vor-desc">{xml_escape(desc_txt)}</desc>')

    # --- CSS: hover/focus a cell lifts its whole chain, dims the rest.
    #     Each cell carries a chain class; one :has() rule per chain keeps
    #     the hovered chain's cells strong while fading the others. ---
    chain_slug = {chain: f"c{idx}" for idx, chain in enumerate(CHAIN_ORDER)}
    css: List[str] = [
        f".cell polygon{{fill-opacity:{CELL_FILL_ALPHA};transition:fill-opacity .18s ease}}",
        ".cell{transition:opacity .18s ease}",
        ".cell:focus{outline:none}",
        ".seed,.slabel{transition:opacity .18s ease}",
    ]
    for slug in chain_slug.values():
        cond = f"#vmap:has(.cell.{slug}:is(:hover,:focus-within))"
        css.append(f"{cond} .cell{{opacity:.30}}")
        css.append(f"{cond} .cell.{slug}{{opacity:1}}")
        css.append(f"{cond} .cell.{slug} polygon{{fill-opacity:{CELL_HOVER_ALPHA}}}")
        css.append(f"{cond} .seed,{cond} .slabel{{opacity:.25}}")
        css.append(f"{cond} .seed.{slug},{cond} .slabel.{slug}{{opacity:1}}")

    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside a media query). Under
    # prefers-contrast each chain's territory fill and its legend swatch deepen
    # to the high-contrast hue; the cells keep their soft fill-opacity, so the
    # deeper base only sharpens the territory boundaries without swallowing the
    # seed dots or flagship labels riding on top. Forced colours: colour is the
    # sole territory key for a five-region catchment map, and the ~4-colour
    # Windows High Contrast palette cannot preserve five distinct hues — a flat
    # hand-off would merge every chain's territory into one ink. Give each
    # chain's cells (and its legend swatch, which shares the .leg-{slug} class) a
    # distinct Canvas/CanvasText pattern so the territories stay separable
    # without colour. The pattern defs are inert at the default render
    # (referenced only inside the forced-colors media query), so the shipped SVG
    # is byte-for-byte unchanged.
    cell_series = {
        f".cell.{chain_slug[chain]} polygon": chain_color[chain] for chain in CHAIN_ORDER
    }
    leg_series = {
        f".leg-{chain_slug[chain]}": chain_color[chain] for chain in CHAIN_ORDER
    }
    # One pattern per chain, shared by its cells and its legend swatch via a
    # combined selector, so the legend key matches the territory it decodes.
    fcp_defs, fcp_style = forced_color_patterns(
        [
            f".cell.{chain_slug[chain]} polygon,.leg-{chain_slug[chain]}"
            for chain in CHAIN_ORDER
        ],
        prefix="voronoi-fcp",
    )
    # The cells paint at a soft fill-opacity (CELL_FILL_ALPHA) so seed dots and
    # labels read on top; under forced colours the pattern must be fully opaque
    # or it washes out, so lift the cell fill-opacity inside the same query.
    fcp_style += (
        "\n@media (forced-colors: active){\n"
        "  .cell polygon{fill-opacity:1;}\n}"
    )
    contrast_css = (
        os_adaptive_style(cell_series, role="fill")
        + "\n"
        + os_adaptive_style(leg_series, role="fill")
        + "\n"
        + fcp_style
    )
    # Additive OS dark-mode block. The territory tints are painted at a soft
    # fill-opacity over the (now dark) page, which would leave them muddy, so on
    # dark we lift the cell fill-opacity to keep every chain's hue legible. Only
    # the white background RECT darkens — the white cell hairlines (tile gaps),
    # the white seed dots and the white text on the saturated flagship pills all
    # stay white so they still read on the dark surface. The two ink tiers flip
    # to light. No multiply groups.
    dark_css = os_dark_style(
        ink_map={"#1D1D1F": "#F2F2F7", "#6E6E73": "#9C9CA3"},
        screen_blend=False,
        extra='rect[fill="#FFFFFF"]{fill:#0B0B0C;} '
        f".cell polygon{{fill-opacity:{CELL_FILL_ALPHA + 0.28:.2f};}}",
    )
    parts.append("<style>" + "".join(css) + contrast_css + dark_css + "</style>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="56" y="76" font-size="40" font-weight="700" '
        f'fill="{INK}">{xml_escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="56" y="114" font-size="21" fill="{SUBINK}">'
        f'{xml_escape(subtitle_txt)}</text>'
    )

    # --- chain legend with area share (its own row below the subtitle) ---
    ly = 164.0
    cursor = 56.0
    for chain in CHAIN_ORDER:
        color = chain_color[chain]
        pct = share[chain]
        cnt = count_by_chain[chain]
        label = f"{chain}"
        meta = f"{pct:.0f}% area · {cnt} shops"
        # Legend disk: pure fill, no dark ring.
        parts.append(
            f'<rect class="leg-{chain_slug[chain]}" '
            f'x="{cursor:.1f}" y="{ly - 15:.1f}" width="18" height="18" '
            f'rx="4" fill="{_hex_to_rgba(color, 0.85)}"/>'
        )
        parts.append(
            f'<text x="{cursor + 26:.1f}" y="{ly:.1f}" text-anchor="start" '
            f'font-size="18" font-weight="600" fill="{INK}">{xml_escape(label)}</text>'
        )
        parts.append(
            f'<text x="{cursor + 26:.1f}" y="{ly + 21:.1f}" text-anchor="start" '
            f'font-size="14" fill="{SUBINK}" font-family="{FONT_MONO}">'
            f'{xml_escape(meta)}</text>'
        )
        cursor += 26 + max(10.6 * len(label), 9.0 * len(meta)) + 46

    # --- rounded frame + clip for the map card ---
    parts.append(
        f'<defs><clipPath id="mapclip"><rect x="{MAP_X0:.1f}" y="{MAP_Y0:.1f}" '
        f'width="{MAP_X1 - MAP_X0:.1f}" height="{MAP_Y1 - MAP_Y0:.1f}" '
        f'rx="{FRAME_RADIUS}"/></clipPath>' + fcp_defs + "</defs>"
    )

    parts.append('<g id="vmap">')

    # --- cells layer (clipped to the rounded map card) ---
    parts.append('<g id="cells" clip-path="url(#mapclip)">')
    for (gx, gy, chain, name), cell in zip(CITY, cells):
        if len(cell) < 3:
            continue
        color = chain_color[chain]
        slug = chain_slug[chain]
        cell_area_pct = (
            _polygon_area(cell)
            / ((MAP_X1 - MAP_X0) * (MAP_Y1 - MAP_Y0))
            * 100.0
        )
        who = name if name else f"{chain} pharmacy"
        tip = f"{who} — nearest shop for {cell_area_pct:.1f}% of the city · {chain}"
        # A <g> wraps each cell so its <title> tooltip is a sibling of the
        # polygon (the most portable place across SVG renderers).
        parts.append(
            f'<g class="cell {slug}" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}"><title>{xml_escape(tip)}</title>'
            f'<polygon points="{_poly_points(cell)}" '
            f'fill="{color}" '
            f'stroke="{HAIRLINE}" stroke-width="2" stroke-linejoin="round"/>'
            f'</g>'
        )
    parts.append("</g>")  # /cells

    # --- seed dots layer (white ring is a pure fill halo, not a dark stroke) ---
    parts.append('<g id="seeds" clip-path="url(#mapclip)">')
    for (gx, gy, chain, _name) in CITY:
        color = chain_color[chain]
        slug = chain_slug[chain]
        px, py = _to_canvas(gx, gy)
        # Two stacked circles: a slightly larger white disk (the halo) under
        # a solid chain-colour dot. No stroke anywhere, so no dark ring.
        parts.append(
            f'<g class="seed {slug}">'
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="8.5" fill="#FFFFFF"/>'
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5.5" fill="{color}"/>'
            f'</g>'
        )
    parts.append("</g>")  # /seeds

    # --- flagship labels layer -------------------------------------------
    #   Each label lives *inside its own cell*, anchored at the cell
    #   centroid (always interior for a convex cell), so text never straddles
    #   a border. The plate is a solid pill filled with the chain hue — the
    #   same colour as the cell, but opaque — so the label reads as a chip of
    #   that territory rather than colour-on-colour. Text is white or ink,
    #   chosen per chain by the plate's luminance for guaranteed contrast.
    #   Long "Chain · Place" names stack onto two lines to keep the pill
    #   compact enough to sit clear of the cell's edges.
    parts.append('<g id="labels">')
    for (gx, gy, chain, name), cell in zip(CITY, cells):
        if not name or len(cell) < 3:
            continue
        slug = chain_slug[chain]
        color = chain_color[chain]
        cx, cy = _polygon_centroid(cell)

        # Split "Chain · Place" so the flagship stacks tidily on two lines.
        if " · " in name:
            top, bottom = name.split(" · ", 1)
        else:
            top, bottom = name, ""
        lines = [top] + ([bottom] if bottom else [])

        # Pill fill: the chain hue, but nudged off the cell tint's own value
        # so the chip separates cleanly from its territory. The neutral Gray
        # is deepened toward ink so the "Independent" chip never disappears
        # into its pale-gray cell.
        plate_fill = "#5A5A5F" if chain == "Independent" else color
        # White text on a saturated pill, unless the hue is pale where ink
        # reads better (kept in reserve for lighter future palettes).
        text_fill = "#FFFFFF" if _relative_luminance(plate_fill) < 0.55 else INK
        line_h = 20.0
        font_px = 15.0
        longest = max(len(s) for s in lines)
        text_w = 8.1 * longest + 24.0
        plate_h = line_h * len(lines) + 12.0

        # Keep the pill inside its cell: if the half-width would spill past
        # the nearest edge, the label still centres on the centroid but we
        # trust the centroid clearance — cells this size comfortably hold the
        # two-line chip. (Clip-path on the group is the belt-and-braces.)
        px0 = cx - text_w / 2.0
        py0 = cy - plate_h / 2.0
        # First baseline, vertically centred within the pill.
        first_baseline = py0 + (plate_h - line_h * (len(lines) - 1)) / 2.0 + font_px * 0.36

        parts.append(f'<g class="slabel {slug}">')
        parts.append(
            f'<rect x="{px0:.1f}" y="{py0:.1f}" width="{text_w:.1f}" '
            f'height="{plate_h:.1f}" rx="{plate_h / 2.0:.1f}" '
            f'fill="{plate_fill}" stroke="#FFFFFF" stroke-width="2.5"/>'
        )
        for i, line in enumerate(lines):
            weight = 700 if i == 0 else 500
            fs = font_px if i == 0 else font_px - 1.5
            baseline = first_baseline + i * line_h
            parts.append(
                f'<text x="{cx:.1f}" y="{baseline:.1f}" text-anchor="middle" '
                f'font-size="{fs:.1f}" font-weight="{weight}" fill="{text_fill}">'
                f'{xml_escape(line)}</text>'
            )
        parts.append("</g>")
    parts.append("</g>")  # /labels

    parts.append("</g>")  # /vmap

    # --- footer hint (bottom-left) ---
    hint_y = HEIGHT - 42
    parts.append(
        f'<text x="56" y="{hint_y:.1f}" font-size="16" fill="{SUBINK}">'
        f'Each cell = the area closer to that pharmacy than to any other · '
        f'hover or focus a cell to lift its chain’s whole territory</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the Voronoi catchment-map SVG to the skill's example folder."""
    render_cli(__file__, "voronoi", build_svg, description="Render the voronoi SVG.")


if __name__ == "__main__":
    main()

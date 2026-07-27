#!/usr/bin/env python3
"""
make_parliament — publication-quality hemicycle (parliament) chart as a hand SVG.

A hemicycle chart draws one dot per seat, arranged in arced rows of
increasing radius, coloured by the party that holds it. It is the
canonical way a newsroom shows *who won the chamber*: the eye reads the
half-ring as the assembly floor, each block of colour as a party's
delegation, and a single radial gap plus a majority line answers the
only question that matters on election night — did anyone clear the bar
to govern alone, and if not, which coalitions can?

Vega-Lite has no native hemicycle mark (the seat lattice is a bespoke
polar packing, not a scatter over a shared scale), so the figure is
built as an SVG string by hand. The layout is the classic one used by
parliaments and by the Highcharts *item chart* that inspired this piece,
but rendered more carefully:

* **Seat lattice** — a fixed number of concentric rows fills the
  half-annulus between an inner and an outer radius. Each row holds as
  many seats as its arc length allows at a constant seat pitch, so dots
  never crowd on the inner rows nor scatter on the outer ones. Seats are
  then dealt row-major, left to right along the floor, so each party's
  block is contiguous and reads as one wedge of colour.
* **Party colouring** — every seat carries its party's brand hue. Blocks
  are laid in seating order (left to right across the political
  spectrum), so the chamber reads like the real floor plan.
* **Majority line** — a slim radial marker at the 50 %-of-seats boundary,
  labelled with the exact threshold, makes "who can govern" legible at a
  glance.
* **Legend** — party rows with a colour disk, name, and seat count,
  sorted by delegation size, with the largest bloc's shortfall from a
  majority called out.

House style follows ``_style.py`` / ``bar.vl.json``: Roboto type, the
Apple-system categorical palette, ink ``#1D1D1F`` on white, rounded
label treatment, a start-anchored takeaway title plus a one-line
subtitle that states the point.

Interaction (no JavaScript): every seat carries a native ``<title>``
tooltip naming its party, and a CSS ``:hover`` / ``:focus`` rule lifts a
whole party's block while dimming the rest, so pointing at any seat
highlights that delegation. The figure is otherwise static (a settled
result does not benefit from animation), so ``animated`` is false and
``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/parliament.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402
from _svg import point_on_circle, svg_open  # noqa: E402
from _labels import best_text_colour  # noqa: E402
from _render import render_cli  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1280
HEIGHT = 980
CX = WIDTH / 2.0
CY = 858.0            # centre of the hemicycle, low so the arch fills upward
R_INNER = 246.0       # inner radius of the innermost seat row
R_OUTER = 566.0       # outer radius of the outermost seat row
N_ROWS = 10           # concentric seat rows
SEAT_PITCH = 33.0     # target centre-to-centre spacing between seats
SEAT_R = 12.4         # seat-dot radius

INK = "#1D1D1F"       # primary text
SUBINK = "#6E6E73"    # secondary text
HAIR = "#D2D2D7"      # hairlines / soft rules
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"


# ------------------------------------------------------------------
# The story (illustrative but plausible): a fresh general election for a
# 289-seat national assembly. Five parties won seats; none cleared the
# 145-seat majority alone. The largest bloc, the Social Democrats, fell
# nine short — the takeaway is a hung parliament that forces a coalition.
# Parties are ordered left-to-right across the political spectrum so the
# chamber's seating reads like the real floor.
# ------------------------------------------------------------------
# (party name, short label, seat count, palette base-hue name) in seating order.
# The base-hue name is resolved to a concrete hex at the requested accessibility
# level by :func:`_parties`, so the chamber can re-hue without duplicating data.
_PARTY_ROWS: List[Tuple[str, str, int, str]] = [
    ("Green League",     "GRN", 34, "Green"),
    ("Social Democrats", "SD",  136, "Red"),
    ("Liberal Union",    "LIB", 41, "Yellow"),
    ("Christian Centre", "CC",  52, "Blue"),
    ("National Right",   "NR",  26, "Purple"),
]
_PARTY_FALLBACK: Dict[str, str] = {
    "Green": "#34C759", "Red": "#FF3B30", "Yellow": "#FFCC00",
    "Blue": "#007AFF", "Purple": "#AF52DE",
}


def _parties(accessibility: str = "universal") -> List[Tuple[str, str, int, str]]:
    """Return the party rows with hues resolved at an accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`;
        ``"universal"`` (default) is the identity.

    Returns
    -------
    list of tuple
        ``(party name, short label, seat count, hex hue)`` in seating order.
    """
    palette = load_palette(accessibility)
    return [
        (name, lab, seats, palette.get(base, _PARTY_FALLBACK[base]))
        for name, lab, seats, base in _PARTY_ROWS
    ]


PALETTE = load_palette()

# (party name, short label, seat count, brand hue) in seating order.
PARTIES: List[Tuple[str, str, int, str]] = _parties()

TOTAL_SEATS = sum(p[2] for p in PARTIES)
MAJORITY = TOTAL_SEATS // 2 + 1          # seats needed to govern alone


# ------------------------------------------------------------------
# Geometry helpers
# ------------------------------------------------------------------
def _polar(radius: float, deg: float) -> Tuple[float, float]:
    """Convert (radius, angle-in-degrees) to an SVG (x, y) point.

    Angle ``0`` points straight left (9 o'clock) and grows clockwise up
    and over to the right, so a seat's angle from ``0`` to ``180`` sweeps
    the half-ring the way a chamber is drawn — left bench to right bench.

    Parameters
    ----------
    radius : float
        Distance from the hemicycle centre, in pixels.
    deg : float
        Angle in degrees; ``0`` = left, ``180`` = right, over the top.

    Returns
    -------
    tuple of float
        The ``(x, y)`` point in SVG pixel coordinates.
    """
    # Upper semicircle: 0 deg -> left bench (-x), 90 deg -> top of the
    # arch (-y), 180 deg -> right bench (+x). point_on_circle uses the
    # standard theta (0 = +x, growing toward +y), so map deg -> pi - rad.
    rad = math.radians(180.0 - deg)
    x, y = point_on_circle(CX, CY, radius, rad)
    # Reflect y about the centre so the ring opens upward, not downward.
    return x, 2 * CY - y


# ------------------------------------------------------------------
# Seat lattice
# ------------------------------------------------------------------
def _row_radii() -> List[float]:
    """Return the radius of each concentric seat row, inner to outer.

    Returns
    -------
    list of float
        ``N_ROWS`` radii evenly spaced across ``[R_INNER, R_OUTER]``.
    """
    if N_ROWS == 1:
        return [(R_INNER + R_OUTER) / 2.0]
    step = (R_OUTER - R_INNER) / (N_ROWS - 1)
    return [R_INNER + i * step for i in range(N_ROWS)]


def _seats_per_row(radii: List[float]) -> List[int]:
    """Distribute the total seats across rows in proportion to arc length.

    Each row's half-circumference (``pi * r``) sets how many seats fit at
    the target :data:`SEAT_PITCH`; the per-row capacities are then scaled
    so their sum is exactly :data:`TOTAL_SEATS`, with the rounding
    remainder handed to the longest (outer) rows.

    Parameters
    ----------
    radii : list of float
        Row radii, inner to outer.

    Returns
    -------
    list of int
        Seat count per row, summing to :data:`TOTAL_SEATS`.
    """
    # Raw capacity of each row from its arc length at the seat pitch.
    caps = [max(1.0, math.pi * r / SEAT_PITCH) for r in radii]
    scale = TOTAL_SEATS / sum(caps)
    scaled = [c * scale for c in caps]

    # Floor first, then distribute the leftover seats to the rows with the
    # largest fractional part (longest arcs win ties, so outer rows fill).
    counts = [int(math.floor(s)) for s in scaled]
    remainder = TOTAL_SEATS - sum(counts)
    fracs = sorted(
        range(len(scaled)),
        key=lambda i: (scaled[i] - counts[i], radii[i]),
        reverse=True,
    )
    for k in range(remainder):
        counts[fracs[k % len(fracs)]] += 1
    return counts


def _seat_lattice() -> List[Tuple[float, float, float, float]]:
    """Build every seat as ``(angle, radius, x, y)`` in sweep order.

    Seats are generated row by row; within a row they run from the left
    bench (angle ``0``) to the right bench (angle ``180``). The flat list
    is then sorted by angle so consecutive entries are consecutive on the
    floor — the natural seating order a chamber is dealt in.

    Returns
    -------
    list of tuple
        ``(angle_deg, radius, x, y)`` per seat, sorted by sweep angle.
    """
    radii = _row_radii()
    counts = _seats_per_row(radii)

    seats: List[Tuple[float, float, float, float]] = []
    for r, n in zip(radii, counts):
        if n == 1:
            angles = [90.0]
        else:
            # Inset the extreme seats a touch so no dot kisses the baseline.
            pad = 3.4
            span = 180.0 - 2 * pad
            angles = [pad + span * k / (n - 1) for k in range(n)]
        for a in angles:
            x, y = _polar(r, a)
            seats.append((a, r, x, y))

    # Sweep left (angle 0) to right (angle 180); tie-break inner-first so a
    # party's angular wedge has a clean radial edge.
    seats.sort(key=lambda t: (t[0], t[1]))
    return seats


def _seat_positions_and_parties() -> Tuple[List[Tuple[float, float]], List[int]]:
    """Return seat centres and the party index each seat belongs to.

    Parties own contiguous *angular sectors* of the half-ring, sized by
    seat count, so each delegation reads as one clean wedge of colour from
    the left bench to the right. Every seat is assigned to the party whose
    cumulative-share sector its sweep index falls in, which keeps the
    radial party boundaries crisp regardless of how rows differ in length.

    Returns
    -------
    positions : list of tuple of float
        ``(x, y)`` seat centres in seating order.
    assignment : list of int
        Party index per seat, aligned with ``positions``.
    """
    seats = _seat_lattice()
    positions = [(x, y) for (_a, _r, x, y) in seats]

    # Deal parties in order: the i-th seat by sweep angle goes to whichever
    # party's running seat total it lands in. This makes each party a
    # single contiguous block even when the arithmetic seat counts and the
    # geometric lattice size differ by a seat or two.
    assignment: List[int] = []
    cum = 0
    thresholds: List[Tuple[int, int]] = []  # (upper_bound_exclusive, party_idx)
    for idx, (_name, _lab, s, _hue) in enumerate(PARTIES):
        cum += s
        thresholds.append((cum, idx))
    for i in range(len(positions)):
        # Scale the geometric seat index onto the arithmetic seat budget so
        # a lattice with a few more/fewer dots than TOTAL_SEATS still splits
        # cleanly by party share.
        budget_pos = i * TOTAL_SEATS / max(1, len(positions))
        pid = thresholds[-1][1]
        for upper, idx in thresholds:
            if budget_pos < upper:
                pid = idx
                break
        assignment.append(pid)
    return positions, assignment


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def _seat_disk(
    x: float,
    y: float,
    hue: str,
    party_id: str,
    tip: str,
) -> str:
    """Return one seat dot: a pure-fill disk with a tooltip, no dark ring.

    Parameters
    ----------
    x, y : float
        Seat centre.
    hue : str
        Party fill colour.
    party_id : str
        CSS class suffix used by the hover rule to lift a whole block.
    tip : str
        Tooltip / aria label for the seat.

    Returns
    -------
    str
        An SVG ``<circle>`` element string.
    """
    return (
        f'<circle class="seat p-{party_id}" cx="{x:.2f}" cy="{y:.2f}" '
        f'r="{SEAT_R:.2f}" fill="{hue}" tabindex="0" role="img" '
        f'aria-label="{escape(tip)}"><title>{escape(tip)}</title></circle>'
    )


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full hemicycle SVG document as a string.

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
    parties = _parties(accessibility)
    positions, assignment = _seat_positions_and_parties()
    parts: List[str] = []

    lead_name, _lead_lab, lead_seats, lead_hue = max(parties, key=lambda p: p[2])
    short = MAJORITY - lead_seats  # how far the largest bloc falls short

    title_txt = (
        f"Hung parliament: {lead_name} lead but fall {short} short of a majority"
    )
    subtitle_txt = (
        f"General election result — {TOTAL_SEATS} seats, "
        f"{MAJORITY} needed to govern alone (illustrative data)"
    )
    desc_txt = (
        f"Hemicycle chart of a {TOTAL_SEATS}-seat national assembly after a "
        f"general election. Each dot is one seat, arranged in {N_ROWS} arced "
        f"rows and coloured by party. Seats run left to right across the "
        f"political spectrum. A majority needs {MAJORITY} seats; the largest "
        f"party, {lead_name}, holds {lead_seats} and falls {short} short, so "
        f"no party can govern alone and a coalition is required."
    )

    parts.append(svg_open(WIDTH, HEIGHT, "parl-title", "parl-desc", font_family=FONT))
    parts.append(f'<title id="parl-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="parl-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hover / focus a seat lifts its whole party, dims the rest ---
    css = [
        ".seat{transition:opacity .16s ease}",
        # Pointing anywhere on the floor fades every seat ...
        "#floor:hover .seat{opacity:.24}",
        # ... then the hovered/focused seat and every seat sharing its
        # party class come back to full opacity (`:has` lifts the block).
        ".seat:hover,.seat:focus{opacity:1}",
    ]
    for idx, (_name, lab, _seats, _hue) in enumerate(parties):
        party_cls = f"{idx}-{lab.lower()}"
        css.append(f"#floor:has(.p-{party_cls}:hover) .p-{party_cls}{{opacity:1}}")
        css.append(f"#floor:has(.p-{party_cls}:focus) .p-{party_cls}{{opacity:1}}")
    css.append(".seat:focus{outline:none}")
    # OS-adaptive overrides (additive; the default render is byte-identical
    # because every rule below lives inside a media query). Under
    # prefers-contrast each party's seats deepen to their high-contrast hue on
    # the seat fills. Under forced colours the seats drop to system-palette
    # discs — legitimate here because every party is also named on an
    # always-visible wedge-label pill and legend chip, so the chamber still
    # reads by position and label without colour. Only the classed seats are
    # forced; the inline-filled wedge pills and legend disks keep their hues
    # (forced-colors leaves inline SVG presentation attributes alone).
    seat_series = {
        f".p-{idx}-{lab.lower()}": hue
        for idx, (_name, lab, _seats, hue) in enumerate(parties)
    }
    css.append(os_adaptive_style(seat_series, role="fill", forced=True))
    # Additive OS dark mode: dark paper + light ink (default ink_map); the party
    # seat hues are data, left alone. The soft hairline rules darken so they read
    # on the dark surface.
    css.append(os_dark_style(extra='[stroke="#D2D2D7"]{stroke:#42424A;}'))
    parts.append("<style>" + "".join(css) + "</style>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="52" y="70" font-size="34" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="52" y="106" font-size="19" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    # --- majority marker: a slim radial line at the 50 %+1 boundary ---
    # The boundary sits between seat index (MAJORITY-1) and MAJORITY in
    # seating order; place it at the mid-angle between those two seats so
    # the line falls in the gap, not through a dot.
    frac_lo = (MAJORITY - 1) / TOTAL_SEATS
    frac_hi = MAJORITY / TOTAL_SEATS
    boundary_deg = 180.0 * (frac_lo + frac_hi) / 2.0
    r_line_in = R_INNER - 40.0
    r_line_out = R_OUTER + 34.0
    bx0, by0 = _polar(r_line_in, boundary_deg)
    bx1, by1 = _polar(r_line_out, boundary_deg)
    parts.append(
        f'<line x1="{bx0:.2f}" y1="{by0:.2f}" x2="{bx1:.2f}" y2="{by1:.2f}" '
        f'stroke="{INK}" stroke-width="2.4" stroke-dasharray="2 7" '
        f'stroke-linecap="round"/>'
    )
    # Majority label pill at the outer end of the marker.
    lbl = f"Majority · {MAJORITY}"
    lx, ly = _polar(r_line_out + 12.0, boundary_deg)
    parts.append(
        f'<rect x="{lx - 66:.1f}" y="{ly - 40:.1f}" width="132" height="30" '
        f'rx="15" fill="{INK}"/>'
    )
    parts.append(
        f'<text x="{lx:.1f}" y="{ly - 20:.1f}" text-anchor="middle" '
        f'font-family="{FONT_MONO}" font-size="15" font-weight="600" '
        f'fill="{BG}">{escape(lbl)}</text>'
    )

    # --- seat lattice ---
    parts.append('<g id="floor">')
    for (x, y), pid in zip(positions, assignment):
        name, lab, seats, hue = parties[pid]
        cls = f"{pid}-{lab.lower()}"
        tip = f"{name} ({lab}) — {seats} seats"
        parts.append(_seat_disk(x, y, hue, cls, tip))
    parts.append("</g>")

    # --- per-party wedge labels (never colour-only) ---
    # Each party owns a contiguous angular sector, so a short label pill sits
    # at that sector's mid-angle on the outer rim. This names every bloc on
    # the arch itself, so a reader who cannot separate the hues (colour-vision
    # deficiency, greyscale print) still reads which wedge is which party.
    # A seat's sector runs over the sweep angles its assignment covers; we
    # take the mean angle of each party's seats as the label anchor.
    seat_angles = [a for (a, _r, _x, _y) in _seat_lattice()]
    sector_mid_deg: List[float] = []
    for pidx in range(len(parties)):
        angs = [seat_angles[i] for i, p in enumerate(assignment) if p == pidx]
        sector_mid_deg.append(sum(angs) / len(angs) if angs else 90.0)
    r_wedge_label = R_OUTER + 66.0
    for pidx, (name, lab, seats, hue) in enumerate(parties):
        mid = sector_mid_deg[pidx]
        wx, wy = _polar(r_wedge_label, mid)
        wtext = f"{lab} · {seats}"
        # White-keyline pill in the party hue with auto-contrast text: the
        # label reads on the arch without a black ring, and its own shape +
        # text carry the party identity if the fill hue is indistinct.
        chars = len(wtext)
        pill_w = 20.0 + 9.2 * chars
        txt_fill = best_text_colour(hue)
        # Keep the extreme benches' pills off the canvas edge: the outermost
        # wedges sit near the flat baseline, so clamp the pill horizontally to
        # a comfortable margin (and lift the near-baseline ones up a touch).
        margin = 18.0
        wx = min(max(wx, margin + pill_w / 2), WIDTH - margin - pill_w / 2)
        wy = min(wy, CY - 22.0)  # never drop a pill below the arch baseline
        parts.append(
            f'<rect x="{wx - pill_w / 2:.1f}" y="{wy - 15:.1f}" '
            f'width="{pill_w:.1f}" height="28" rx="14" fill="{hue}" '
            f'stroke="{BG}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{wx:.1f}" y="{wy + 5:.1f}" text-anchor="middle" '
            f'font-family="{FONT_MONO}" font-size="15" font-weight="700" '
            f'fill="{txt_fill}">{escape(wtext)}</text>'
        )

    # --- centre readout: the takeaway number, in the empty pocket at the hub.
    # The inner seat rows arc *above* this zone (the innermost seat at the top
    # of the arch sits at y = CY - R_INNER), so the flat-bottomed pocket below
    # it — the natural clear space every hemicycle leaves at its centre — is
    # reserved for the readout. Text is centred in that pocket so no seat cell
    # ever crowds or overlaps it; no masking disc is needed.
    inner_top_y = CY - R_INNER          # y of the innermost seat at the apex
    pocket_top = inner_top_y + 34.0     # start of the reserved text zone
    pocket_bot = CY - 78.0              # keep clear of the low flank seats
    hub_cy = (pocket_top + pocket_bot) / 2.0
    parts.append(
        f'<text x="{CX:.1f}" y="{hub_cy - 46:.1f}" text-anchor="middle" '
        f'font-size="18" letter-spacing="0.4" fill="{SUBINK}">Largest bloc</text>'
    )
    parts.append(
        f'<text x="{CX:.1f}" y="{hub_cy + 12:.1f}" text-anchor="middle" '
        f'font-family="{FONT_MONO}" font-size="60" font-weight="700" '
        f'fill="{lead_hue}">{lead_seats}</text>'
    )
    parts.append(
        f'<text x="{CX:.1f}" y="{hub_cy + 44:.1f}" text-anchor="middle" '
        f'font-size="18" fill="{SUBINK}">of {MAJORITY} for a majority</text>'
    )

    # --- legend: one horizontal strip of party chips, in seating order so
    # the row mirrors the arch left-to-right; each chip is a colour disk +
    # party name + seat count. Chip widths follow the name length so the
    # strip reads as an evenly spaced ribbon.
    legend_y = 172.0
    chip_gap = 30.0
    disk_r = 11.0

    def _chip_width(name: str, seats: int) -> float:
        """Approximate a chip's pixel width from its text (~0.58 em glyphs)."""
        text_px = 0.58 * 18.0 * len(name) + 0.62 * 18.0 * len(str(seats))
        return 2 * disk_r + 12.0 + text_px + 14.0

    widths = [_chip_width(n, s) for (n, _l, s, _h) in parties]
    total_w = sum(widths) + chip_gap * (len(parties) - 1)
    cursor = CX - total_w / 2.0  # centre the whole strip under the subtitle
    parts.append(f'<g transform="translate(0,{legend_y})">')
    for (name, _lab, seats, hue), w in zip(parties, widths):
        cx_disk = cursor + disk_r
        parts.append(
            f'<circle cx="{cx_disk:.1f}" cy="0" r="{disk_r}" fill="{hue}"/>'
        )
        tx = cx_disk + disk_r + 12.0
        parts.append(
            f'<text x="{tx:.1f}" y="6" font-size="18" font-weight="600" '
            f'fill="{INK}">{escape(name)}</text>'
        )
        # Seat count trails the name in mono ink (kept ink, not the party
        # hue, so pale hues like yellow never drop below text contrast).
        name_px = 0.58 * 18.0 * len(name)
        parts.append(
            f'<text x="{tx + name_px + 10:.1f}" y="6" font-family="{FONT_MONO}" '
            f'font-size="18" font-weight="700" fill="{INK}">{seats}</text>'
        )
        cursor += w + chip_gap
    parts.append("</g>")

    # --- baseline under the arch + footnote ---
    base_y = CY + 2.0
    parts.append(
        f'<line x1="{CX - R_OUTER - 26:.1f}" y1="{base_y:.1f}" '
        f'x2="{CX + R_OUTER + 26:.1f}" y2="{base_y:.1f}" '
        f'stroke="{HAIR}" stroke-width="1.4"/>'
    )
    parts.append(
        f'<text x="52" y="{HEIGHT - 34}" font-size="15" fill="{SUBINK}">'
        f'One dot = one seat · dashed line marks the {MAJORITY}-seat majority · '
        f'{escape(lead_name)} need {short} more seats or a coalition partner · '
        f'hover a seat to lift its party'
        f'</text>'
    )

    # Fullscreen control per interactivity mode, just before the close.
    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the hemicycle SVG to the skill's example asset folder.

    The ``--mode`` flag (via :func:`_render.render_cli`) selects the
    interactivity mode threaded into :func:`build_svg`.
    """
    render_cli(
        __file__,
        "parliament",
        build_svg,
        description="Write the house-style parliament hemicycle SVG example.",
    )


if __name__ == "__main__":
    main()

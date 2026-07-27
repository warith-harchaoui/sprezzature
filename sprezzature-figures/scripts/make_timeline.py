#!/usr/bin/env python3
"""
make_timeline — an event timeline rendered as a hand-authored SVG.

An **event timeline** places dated milestones along one horizontal time
axis, with alternating **above / below** callouts joined to the spine by
short connector stems. It is the canonical way to show the history of a
product, a mission programme, or an organisation at a glance: the reader
sweeps left-to-right and reads *when* each thing happened and *what* it
was, while the alternating callouts keep neighbouring labels from
colliding.

This example charts the modern era of Mars exploration — from the first
successful flyby to the sample-return campaign — as thirteen milestones
on a single decade-scaled spine (1965 → 2035). Each milestone carries a
year, a mission name, and a one-line description. Four coloured **era
bands** run behind the spine (Flybys & Orbiters, First Landers, Rover
Age, Sample Return) so the eye groups the milestones without a legend,
and a moving marker sweeps the spine once to draw the eye through time.

This generator builds the SVG string **by hand** (no matplotlib /
seaborn / plotly, no Vega): the alternating-callout packing, the
side-aware label harmony, and the era-band backdrop are cleaner to place
directly than to coax out of a layered grammar. It matches the front-*
house style: Roboto, the Apple-ish palette, rounded corners, ink
``#1D1D1F``, secondary ``#6E6E73``, white background.

Motion is a single **pure-SMIL** sweep: every mark is fully drawn at
``t=0`` (the static raster is complete and never animates in from
nothing); only a small "you are here" marker glides once along the spine
to invite the reader through the chronology. Each callout carries a
native ``<title>`` tooltip and a keyboard focus ring, so hover / focus
reveals the full description with no JavaScript.

The final artifact is always an SVG written to
``sprezzature-figures/assets/svg-examples/timeline.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from typing import Dict, List

# The house-style palette lives alongside this file, in _style.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


def _era_slug(name: str) -> str:
    """Turn an era name into a CSS-class-safe slug (e.g. ``rover-age``)."""
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")


# ------------------------------------------------------------------
# Communicative real-sounding data — the modern era of Mars exploration.
# Each milestone is a real programme beat: the year it happened, the
# mission that carried it, and one plain sentence of what it achieved.
# ``era`` groups the milestone into one of four programme phases, which
# drives the coloured band behind the spine. This is public spaceflight
# history, chosen so the timeline reads as a genuine chronology rather
# than "Event A / Event B / Event C".
# ------------------------------------------------------------------
MILESTONES: List[Dict[str, object]] = [
    {
        "year": 1965,
        "name": "Mariner 4",
        "blurb": "First close-up photos of Mars on a flyby: 21 grainy frames.",
        "era": "Flybys & Orbiters",
    },
    {
        "year": 1971,
        "name": "Mariner 9",
        "blurb": "First spacecraft to orbit another planet; mapped 85% of Mars.",
        "era": "Flybys & Orbiters",
    },
    {
        "year": 1976,
        "name": "Viking 1",
        "blurb": "First fully successful landing; ran the first soil biology tests.",
        "era": "First Landers",
    },
    {
        "year": 1997,
        "name": "Pathfinder",
        "blurb": "Airbag landing delivered Sojourner, the first Mars rover.",
        "era": "First Landers",
    },
    {
        "year": 2004,
        "name": "Spirit & Opportunity",
        "blurb": "Twin rovers found hard proof that liquid water once flowed.",
        "era": "Rover Age",
    },
    {
        "year": 2008,
        "name": "Phoenix",
        "blurb": "Touched and confirmed water ice just under the polar soil.",
        "era": "Rover Age",
    },
    {
        "year": 2012,
        "name": "Curiosity",
        "blurb": "Sky-crane lander set down a car-sized nuclear lab in Gale crater.",
        "era": "Rover Age",
    },
    {
        "year": 2018,
        "name": "InSight",
        "blurb": "First seismometer on Mars; recorded hundreds of marsquakes.",
        "era": "Rover Age",
    },
    {
        "year": 2021,
        "name": "Perseverance",
        "blurb": "Began caching rock cores; Ingenuity flew the first Mars aircraft.",
        "era": "Rover Age",
    },
    {
        "year": 2021,
        "name": "Tianwen-1",
        "blurb": "China's Zhurong rover landed, a first on its debut Mars attempt.",
        "era": "Rover Age",
    },
    {
        "year": 2028,
        "name": "Sample Retrieval",
        "blurb": "Planned lander to gather Perseverance's cached tubes for launch.",
        "era": "Sample Return",
    },
    {
        "year": 2031,
        "name": "Earth Return Orbiter",
        "blurb": "Planned relay to ferry the sealed samples back toward Earth.",
        "era": "Sample Return",
    },
    {
        "year": 2033,
        "name": "Samples on Earth",
        "blurb": "Target for the first Mars rocks to reach a lab on Earth.",
        "era": "Sample Return",
    },
]


# ------------------------------------------------------------------
# Era bands — four programme phases, each a curated hue, in time order.
# The (start, end) years bound the coloured band drawn behind the spine.
# Colours are pulled from the house palette so the phases read as a cool
# progression (deep blue past → warm future) without a red/green trap.
# ------------------------------------------------------------------
ERAS: List[Dict[str, object]] = [
    {"name": "Flybys & Orbiters", "start": 1965, "end": 1975, "color": "Blue"},
    {"name": "First Landers", "start": 1975, "end": 2000, "color": "Teal"},
    {"name": "Rover Age", "start": 2000, "end": 2024, "color": "Green"},
    {"name": "Sample Return", "start": 2024, "end": 2035, "color": "Orange"},
]

# Axis domain, padded a little past the first and last era so the end
# markers and their callouts never kiss the canvas edge.
YEAR_MIN = 1963
YEAR_MAX = 2035
TICK_STEP = 10  # decade gridlines on the axis


def _lighten(hex_color: str, amount: float) -> str:
    """Blend a hex colour toward white by ``amount`` in [0, 1].

    Used for the translucent-looking era bands and the soft dot halos:
    a lightened tint reads as "same hue, quieter" and keeps the spine
    and ink labels legible on top, with no opacity tricks that the
    auditor could mistake for a wash.

    Parameters
    ----------
    hex_color : str
        A ``#RRGGBB`` colour.
    amount : float
        Fraction toward white, ``0.0`` (unchanged) to ``1.0`` (white).

    Returns
    -------
    str
        The blended ``#RRGGBB`` colour.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = round(r + (255 - r) * amount)
    g = round(g + (255 - g) * amount)
    b = round(b + (255 - b) * amount)
    return f"#{r:02X}{g:02X}{b:02X}"


def _fmt_year(year: int) -> str:
    """Render a year, tagging planned (future) beats with a small dagger.

    Parameters
    ----------
    year : int
        The milestone year.

    Returns
    -------
    str
        The year as a string; the caller styles planned years separately.
    """
    return str(year)


def _wrap(text: str, width: int) -> List[str]:
    """Word-wrap a blurb to at most ``width`` characters per line.

    Parameters
    ----------
    text : str
        The one-line description to wrap.
    width : int
        Target maximum characters per line.

    Returns
    -------
    list of str
        The wrapped lines (usually two).
    """
    return textwrap.wrap(text, width=width) or [""]


# ------------------------------------------------------------------
# SVG assembly
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full event-timeline SVG string.

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
    palette = load_palette(accessibility)
    ink = "#1D1D1F"
    secondary = "#6E6E73"
    hairline = "#D2D2D7"

    # --- canvas geometry -----------------------------------------
    # Poster-scale canvas. The spine runs across the vertical middle;
    # callouts fan above and below it, so the top and bottom margins are
    # generous and equal, and the axis sits just below the spine.
    width = 1840
    height = 1180
    m_left = 100
    m_right = 100
    spine_y = 548
    axis_y = spine_y + 40

    plot_x0 = m_left
    plot_x1 = width - m_right
    plot_w = plot_x1 - plot_x0

    def sx(year: float) -> float:
        """Map a (possibly fractional) year to an x pixel on the spine."""
        return plot_x0 + (year - YEAR_MIN) / (YEAR_MAX - YEAR_MIN) * plot_w

    parts: List[str] = []

    # --- document + accessibility --------------------------------
    parts.append(svg_open(width, height, "tl-title", "tl-desc"))
    n = len(MILESTONES)
    parts.append(
        '<title id="tl-title">Seven decades of Mars exploration as an '
        'event timeline</title>'
    )
    parts.append(
        f'<desc id="tl-desc">A horizontal timeline of {n} Mars-mission '
        f'milestones from 1965 to a planned 2033, with alternating callouts '
        f'above and below a central spine. Four coloured era bands group the '
        f'missions: Flybys and Orbiters, First Landers, the Rover Age, and the '
        f'planned Sample Return campaign.</desc>'
    )

    # Focus ring + hover lift for keyboard and pointer users. The sweep
    # marker is decorative motion, guarded by prefers-reduced-motion.
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside a media query and only takes effect
    # when the reader's OS asks for it). Under prefers-contrast each of the four
    # programme-era hues deepens to its high-contrast value wherever that raw
    # hue is used as an identity mark: the era pills, connector stems, spine
    # dots, card keylines and year labels. The soft lightened era *bands* are
    # backdrops (a tint, not the raw hue) and are deliberately left alone.
    # Forced colours are left to the browser default: colour maps to era, but
    # each era is also named in a text pill and pinned to a stretch of the time
    # axis, so identity already survives with no colour, and the ~4-colour
    # system palette cannot preserve the band/pill/stem colour tie anyway.
    era_hex_for_style = {
        _era_slug(str(era["name"])): palette.get(str(era["color"]), "#007AFF")
        for era in ERAS
    }
    fill_series = {f".era-fill.era-{s}": h for s, h in era_hex_for_style.items()}
    stroke_series = {f".era-stroke.era-{s}": h for s, h in era_hex_for_style.items()}
    contrast_css = (
        os_adaptive_style(fill_series, role="fill")
        + "\n"
        + os_adaptive_style(stroke_series, role="stroke")
    )
    # Additive OS dark-mode block. White is used both as surface (page, milestone
    # cards, spine dots, legend swatch) and as ink (the era-pill labels), so a
    # blanket #FFFFFF flip would darken that pill text. We darken only the white
    # RECT / CIRCLE surfaces and leave white text alone; the two ink tiers flip
    # to light. Era hues, band tints and card keylines are data and untouched.
    dark_css = os_dark_style(
        ink_map={"#1D1D1F": "#F2F2F7", "#6E6E73": "#9C9CA3"},
        screen_blend=False,
        extra='rect[fill="#FFFFFF"]{fill:#141416;} '
        'circle[fill="#FFFFFF"]{fill:#141416;}',
    )
    parts.append(
        '<style>'
        '.mstone{cursor:pointer}'
        '.mstone .dot{transition:r .12s ease}'
        '.mstone:hover .dot,.mstone:focus .dot{r:11}'
        '.mstone:focus{outline:none}'
        '.mstone:focus .card,.mstone:hover .card{stroke-width:2.4}'
        '@media (prefers-reduced-motion: reduce){.sweep{display:none}}'
        + contrast_css
        + dark_css
        + '</style>'
    )

    # --- background ----------------------------------------------
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # --- title + subtitle (the takeaway) -------------------------
    parts.append(
        f'<text x="{m_left}" y="74" font-size="40" font-weight="700" '
        f'fill="{ink}">Sixty years of getting closer to Mars</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="112" font-size="21" fill="{secondary}">'
        f'From a 21-frame flyby to a rover caching rock for the trip home, '
        f'each mission building on the last &#183; daggered dates are '
        f'planned</text>'
    )

    # --- era bands (hugging the spine) ---------------------------
    # A soft tinted strip per programme phase, hugging the spine, with a
    # small hue pill naming the era just below its band. Bands are pale so
    # the spine, dots and ink labels all stay legible on top; the compact
    # height keeps the strip clear of the fanned-out callout cards.
    band_h = 56
    band_top = spine_y - band_h / 2.0
    era_hexes: Dict[str, str] = {}
    for era in ERAS:
        color = palette.get(str(era["color"]), "#007AFF")
        era_hexes[str(era["name"])] = color
        bx0 = sx(float(era["start"]))
        bx1 = sx(float(era["end"]))
        parts.append(
            f'<rect x="{bx0 + 3:.1f}" y="{band_top:.1f}" '
            f'width="{bx1 - bx0 - 6:.1f}" height="{band_h}" rx="12" '
            f'fill="{_lighten(color, 0.84)}"/>'
        )

    # Era-name pills, sitting just below the spine on their own band, on
    # the clear row between the spine and the axis ruler. Deferred to a
    # second pass so the loop above only paints the strips; the pills are
    # drawn last (on top) so nothing occludes them.
    def _era_labels() -> None:
        """Append the era-name pills on the band row, centred per era."""
        pill_y = spine_y + 22
        for era in ERAS:
            color = palette.get(str(era["color"]), "#007AFF")
            bx0 = sx(float(era["start"]))
            bx1 = sx(float(era["end"]))
            mid = (bx0 + bx1) / 2.0
            label = str(era["name"]).upper()
            slug = _era_slug(str(era["name"]))
            pill_w = 9.4 * len(label) + 30
            parts.append(
                f'<rect class="era-fill era-{slug}" '
                f'x="{mid - pill_w / 2:.1f}" y="{pill_y - 15:.1f}" '
                f'width="{pill_w:.1f}" height="24" rx="12" '
                f'fill="{color}"/>'
            )
            parts.append(
                f'<text x="{mid:.1f}" y="{pill_y + 2:.1f}" font-size="13.5" '
                f'font-weight="700" letter-spacing="1" text-anchor="middle" '
                f'fill="#FFFFFF">{xml_escape(label)}</text>'
            )

    # --- axis: decade ticks + baseline year labels ---------------
    # A thin ruled baseline under the spine with decade tick marks and
    # year labels in the mono face, so the reader can register absolute
    # time independent of the milestone callouts.
    parts.append(
        f'<line x1="{plot_x0}" y1="{axis_y}" x2="{plot_x1}" y2="{axis_y}" '
        f'stroke="{hairline}" stroke-width="1.4"/>'
    )
    first_tick = ((YEAR_MIN + TICK_STEP - 1) // TICK_STEP) * TICK_STEP
    tick = first_tick
    while tick <= YEAR_MAX:
        tx = sx(tick)
        parts.append(
            f'<line x1="{tx:.1f}" y1="{axis_y}" x2="{tx:.1f}" '
            f'y2="{axis_y + 9}" stroke="{hairline}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{tx:.1f}" y="{axis_y + 30}" font-size="16" '
            f'font-family="Roboto Mono, monospace" text-anchor="middle" '
            f'fill="{secondary}">{tick}</text>'
        )
        tick += TICK_STEP

    # --- the spine -----------------------------------------------
    # A single clean ink spine with rounded caps; it sits on top of the
    # era bands so the timeline's defining horizontal axis is unmistakable
    # in the static raster.
    parts.append(
        f'<line x1="{plot_x0}" y1="{spine_y}" x2="{plot_x1}" y2="{spine_y}" '
        f'stroke="{ink}" stroke-width="3" stroke-linecap="round"/>'
    )
    # Start / end nibs so the spine reads as a bounded axis of time.
    for cap_x in (plot_x0, plot_x1):
        parts.append(
            f'<circle cx="{cap_x:.1f}" cy="{spine_y}" r="4" fill="{ink}"/>'
        )

    # --- milestones: alternating above / below callouts ----------
    # Each callout is a fixed-width card. To keep same-side neighbours
    # from overlapping when milestones cluster (2021 pair; the 2028-2033
    # sample-return run), we run a small greedy stacker per side: sort
    # each side's cards by x, then push a card to the next vertical level
    # whenever its horizontal span would collide with an already-placed
    # card on the current level. The stem length follows the level, so
    # the fan opens outward instead of stacking on one row.
    card_w = 214
    card_pad = 15
    line_h = 20
    card_gap = 14          # min horizontal gap between same-level cards
    # A level's stem must clear a full card height + margin, so a card
    # pushed to level L never hangs down into the L-1 card that shares its
    # horizontal span. Max card here is three text lines.
    max_card_h = card_pad * 2 + 26 + 24 + 3 * line_h
    level_step = max_card_h + 20
    # The below side must also clear the axis ruler, its year labels, and
    # the era pills that live just under the spine, so its base stem is
    # longer than the above side's.
    stem_base_above = 54
    stem_base_below = 118

    # Pre-compute per-milestone geometry (x, card height, wrapped blurb).
    geom: List[Dict[str, object]] = []
    for m in MILESTONES:
        year = int(m["year"])  # type: ignore[arg-type]
        lines = _wrap(str(m["blurb"]), 28)
        card_h = card_pad * 2 + 26 + 24 + len(lines) * line_h
        geom.append({"mx": sx(year), "lines": lines, "card_h": card_h})

    # Balanced greedy side + level assignment. Process milestones in
    # x-order; for each, compute the lowest free level on *each* side
    # (``above`` / ``below``) and take whichever side keeps the callout
    # closest to the spine, breaking ties by alternating. This spreads
    # the cards evenly so neither side stacks three-deep — far tidier than
    # a fixed index-parity alternation when missions cluster in time.
    level_ends: Dict[str, List[float]] = {"above": [], "below": []}
    levels: List[int] = [0] * n
    order = sorted(range(n), key=lambda k: float(geom[k]["mx"]))  # type: ignore[arg-type]
    last_side = "below"

    def _lowest_free(ends: List[float], left: float) -> int:
        """Return the lowest level whose last card clears ``left``."""
        for lv in range(len(ends)):
            if left >= ends[lv] + card_gap:
                return lv
        return len(ends)

    for k in order:
        mx = float(geom[k]["mx"])  # type: ignore[arg-type]
        left = max(m_left, min(mx - card_w / 2.0, plot_x1 - card_w))
        right = left + card_w
        lv_above = _lowest_free(level_ends["above"], left)
        lv_below = _lowest_free(level_ends["below"], left)
        if lv_above < lv_below:
            side, lv = "above", lv_above
        elif lv_below < lv_above:
            side, lv = "below", lv_below
        else:
            side = "below" if last_side == "above" else "above"
            lv = lv_above if side == "above" else lv_below
        ends = level_ends[side]
        if lv < len(ends):
            ends[lv] = right
        else:
            ends.append(right)
        levels[k] = lv
        last_side = side
        geom[k]["left"] = left  # type: ignore[index]
        geom[k]["side"] = side  # type: ignore[index]

    for i, m in enumerate(MILESTONES):
        year = int(m["year"])  # type: ignore[arg-type]
        name = str(m["name"])
        blurb = str(m["blurb"])
        era = str(m["era"])
        slug = _era_slug(era)
        color = era_hexes.get(era, "#007AFF")
        planned = year >= 2025

        mx = float(geom[i]["mx"])  # type: ignore[arg-type]
        side = str(geom[i]["side"])
        lines = list(geom[i]["lines"])  # type: ignore[arg-type]
        card_h = float(geom[i]["card_h"])  # type: ignore[arg-type]
        cx0 = float(geom[i]["left"])  # type: ignore[arg-type]
        base = stem_base_above if side == "above" else stem_base_below
        stem_len = base + levels[i] * level_step

        # Card y-origin, and the point on the card the stem should meet.
        if side == "above":
            cy0 = spine_y - stem_len - card_h
            card_edge_y = cy0 + card_h
        else:
            cy0 = spine_y + stem_len
            card_edge_y = cy0

        # --- connector stem: spine dot -> card edge ---------------
        # The stem runs straight down the milestone's x to the near edge
        # of its card, so the eye traces year -> event with no ambiguity.
        parts.append(
            f'<line class="era-stroke era-{slug}" x1="{mx:.1f}" y1="{spine_y}" '
            f'x2="{mx:.1f}" '
            f'y2="{card_edge_y:.1f}" stroke="{color}" stroke-width="2.2" '
            + ('stroke-dasharray="2 5" ' if planned else "")
            + 'stroke-linecap="round"/>'
        )

        # Wrap the group so hover/focus lifts the whole callout, and a
        # single <title> serves the accessible tooltip.
        tip = f"{year}{' (planned)' if planned else ''} — {name}: {blurb}"
        parts.append(
            f'<g class="mstone" tabindex="0" role="img" '
            f'aria-label="{xml_escape(tip)}"><title>{xml_escape(tip)}</title>'
        )

        # Soft halo + solid dot on the spine (pure fills, no dark ring).
        parts.append(
            f'<circle cx="{mx:.1f}" cy="{spine_y}" r="12" '
            f'fill="{_lighten(color, 0.55)}"/>'
        )
        # Planned beats are hollow (white core), flown beats are solid.
        if planned:
            parts.append(
                f'<circle class="dot era-stroke era-{slug}" cx="{mx:.1f}" '
                f'cy="{spine_y}" r="7.5" '
                f'fill="#FFFFFF" stroke="{color}" stroke-width="3"/>'
            )
        else:
            parts.append(
                f'<circle class="dot era-fill era-{slug}" cx="{mx:.1f}" '
                f'cy="{spine_y}" r="7.5" '
                f'fill="{color}"/>'
            )

        # --- callout card ----------------------------------------
        # A rounded white card with a coloured left keyline: year in the
        # era hue (mono), mission name in ink, wrapped description below.
        parts.append(
            f'<rect class="card" x="{cx0:.1f}" y="{cy0:.1f}" '
            f'width="{card_w}" height="{card_h:.1f}" rx="13" fill="#FFFFFF" '
            f'stroke="{hairline}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<rect class="era-fill era-{slug}" x="{cx0:.1f}" y="{cy0:.1f}" '
            f'width="6" '
            f'height="{card_h:.1f}" rx="3" fill="{color}"/>'
        )

        tx = cx0 + card_pad + 8
        ty = cy0 + card_pad + 20
        # Year (mono, era hue) + a small "planned" tag where relevant.
        dagger = (
            f'<tspan font-size="13" font-family="Roboto, sans-serif" '
            f'fill="{secondary}"> &#8224; planned</tspan>'
            if planned
            else ""
        )
        parts.append(
            f'<text class="era-fill era-{slug}" x="{tx:.1f}" y="{ty:.1f}" '
            f'font-size="21" '
            f'font-weight="700" font-family="Roboto Mono, monospace" '
            f'fill="{color}">{_fmt_year(year)}{dagger}</text>'
        )
        # Mission name (ink, bold).
        parts.append(
            f'<text x="{tx:.1f}" y="{ty + 27:.1f}" font-size="18" '
            f'font-weight="700" fill="{ink}">{xml_escape(name)}</text>'
        )
        # Description (secondary, wrapped).
        for j, ln in enumerate(lines):
            parts.append(
                f'<text x="{tx:.1f}" y="{ty + 51 + j * line_h:.1f}" '
                f'font-size="14" fill="{secondary}">{xml_escape(ln)}</text>'
            )

        parts.append("</g>")

    # Era-name pills, drawn last so nothing occludes them.
    _era_labels()

    # --- sweep marker: one pass along the spine (pure SMIL) ------
    # A small filled marker glides once from the first to the last
    # milestone, drawing the eye through the chronology. It is fully
    # additive: the whole timeline is already drawn at t=0, and the
    # marker is hidden entirely under prefers-reduced-motion (see CSS).
    x_start = sx(float(MILESTONES[0]["year"]))  # type: ignore[arg-type]
    x_end = sx(float(MILESTONES[-1]["year"]))  # type: ignore[arg-type]
    parts.append(
        f'<g class="sweep">'
        f'<circle cx="{x_start:.1f}" cy="{spine_y}" r="6" '
        f'fill="{ink}" opacity="0.9">'
        f'<animate attributeName="cx" from="{x_start:.1f}" to="{x_end:.1f}" '
        f'dur="7s" begin="1s" fill="freeze" '
        f'calcMode="spline" keyTimes="0;1" keySplines="0.4 0 0.2 1"/>'
        f'<animate attributeName="opacity" values="0;0.9;0.9;0" '
        f'keyTimes="0;0.06;0.94;1" dur="7s" begin="1s" fill="freeze"/>'
        f'</circle>'
        f'</g>'
    )

    # --- legend: flown vs planned glyphs (bottom-left) -----------
    # Explains the two dot styles once, so the hollow future markers read
    # correctly without hunting.
    leg_y = height - 34
    lx = m_left
    parts.append(
        f'<circle cx="{lx + 8}" cy="{leg_y - 5}" r="7" fill="{ink}"/>'
    )
    parts.append(
        f'<text x="{lx + 24}" y="{leg_y}" font-size="16" '
        f'fill="{secondary}">Flown mission</text>'
    )
    lx2 = lx + 190
    parts.append(
        f'<circle cx="{lx2 + 8}" cy="{leg_y - 5}" r="7" fill="#FFFFFF" '
        f'stroke="{ink}" stroke-width="3"/>'
    )
    parts.append(
        f'<text x="{lx2 + 24}" y="{leg_y}" font-size="16" '
        f'fill="{secondary}">Planned (dagger &#8224;, dashed stem)</text>'
    )

    # Source / illustrative note, right-aligned on the legend row.
    parts.append(
        f'<text x="{plot_x1:.1f}" y="{leg_y}" font-size="15" '
        f'text-anchor="end" fill="{hairline}">Public mission history &#183; '
        f'future dates approximate</text>'
    )

    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the event-timeline SVG to the canonical assets path."""
    render_cli(__file__, "timeline", build_svg, description="Render the timeline SVG.")


if __name__ == "__main__":
    main()

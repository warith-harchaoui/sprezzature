#!/usr/bin/env python3
"""
make_liquid-gauge — a liquid-fill gauge as a hand-authored SVG.

A liquid-fill gauge reads a single ratio the way a glass tank reads a
water level: a circular vessel is filled from the bottom with wavy
liquid up to a fraction of its height, a bold percentage sits at the
centre, and a thin ring closes the vessel. The wavy surface is the
defining mark of the chart type, so it is drawn as two overlapping
crest bands (a darker back wave and a lighter sprezzature wave) whose static
shape already shows the ripple in the raster; a slow, base-visible SMIL
drift then slides both crests sideways so the surface *breathes* without
ever animating in from an empty tank.

The example measures a **drinking-water reservoir**: the Serre-Ponçon
lake is at 63 % of usable capacity going into summer, a touch below its
ten-year seasonal median of 68 %, so the readout carries a small "below
normal" note. A faint dashed line marks that median on the vessel wall,
and a tick scale down the right edge anchors the fill height to real
percentages so "63 %" is legible as a level, not just a number.

Pure-Python, hand-built SVG string — no Vega, no matplotlib — because a
clipped wavy liquid surface is not a native Vega-Lite mark and has to be
placed exactly. It follows the sprezzature-* house style pulled from
:mod:`_style`: the Apple-ish saturated palette (a calm blue liquid), a
Roboto readout, ink ``#1D1D1F`` on a white background, a takeaway title,
and a one-line subtitle that states the point.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/liquid-gauge.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import List, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier); the XML escape helper lives in _svg.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# The reading. One illustrative ratio: a drinking-water reservoir at
# 63 % of usable capacity, a touch under its ten-year seasonal median.
# ------------------------------------------------------------------
#: Fill fraction shown by the liquid surface, in percent.
_VALUE: float = 63.0
#: Ten-year seasonal median for this date, drawn as a dashed reference.
_MEDIAN: float = 68.0

_TITLE: str = "The reservoir sits at 63 %, just below its seasonal normal"
_SUBTITLE: str = (
    "Serre-Ponçon lake · usable capacity on 1 July · "
    "10-year median 68 % · illustrative reading"
)
#: What the vessel measures, named under the readout so the number means
#: something without a legend.
_METRIC: str = "of usable capacity"

# ------------------------------------------------------------------
# Canvas + geometry (poster-scale so the surface and readout read big).
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels.
_WIDTH: int = 1100
_HEIGHT: int = 1040

#: Vessel centre and radius. The liquid is clipped to this disc.
_CX: float = 550.0
_CY: float = 600.0
_R: float = 340.0

#: House-style inks.
_INK: str = "#1D1D1F"      # primary text
_SUBTLE: str = "#6E6E73"   # secondary text
_BG: str = "#FFFFFF"       # background
_EMPTY: str = "#EEF1F6"    # the dry part of the vessel, above the liquid
_RING: str = "#D6DAE2"     # thin vessel wall
_TICK: str = "#C2C7D0"     # scale ticks on the right rim


def _liquid_hues(accessibility: str = "universal") -> Tuple[str, str, str]:
    """Return the three water tones (back crest, sprezzature crest, deep body).

    A single calm blue reads as water; two shifted crest bands plus a
    slightly deeper body give the surface enough tonal separation to look
    like liquid catching light, without any colour-on-colour clash. All
    derive from the canonical palette's Blue and Teal, with a curated
    fallback when a co-installed palette CSV omits a key.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`.

    Returns
    -------
    tuple of str
        ``(back_crest, front_crest, body)`` as ``#RRGGBB`` hex.
    """
    palette = load_palette(accessibility)
    blue = palette.get("Blue") or "#007AFF"
    teal = palette.get("Teal") or "#5AC8FA"
    # Back crest = the base blue; sprezzature crest = the lighter teal catching
    # light; body = a deepened blue so the mass below reads as water.
    return _darken(blue, 0.10), teal, _darken(blue, 0.22)


def _darken(hex_color: str, amount: float) -> str:
    """Darken a ``#RRGGBB`` hex toward black by ``amount`` in ``[0, 1]``.

    Parameters
    ----------
    hex_color : str
        Source colour, ``#RRGGBB``.
    amount : float
        Fraction to move each channel toward 0 (``0`` = unchanged,
        ``1`` = black).

    Returns
    -------
    str
        The darkened ``#RRGGBB`` hex.
    """
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    f = max(0.0, min(1.0, 1.0 - amount))
    return f"#{int(r * f):02X}{int(g * f):02X}{int(b * f):02X}"


def _wave_path(
    surface_y: float,
    amplitude: float,
    wavelength: float,
    phase: float,
    span_left: float,
    span_right: float,
    floor_y: float,
) -> str:
    """Build a closed path: a sine surface at ``surface_y`` down to ``floor_y``.

    The path traces one sine period-set left to right along the liquid
    surface, then drops to ``floor_y`` and closes, so it can be clipped to
    the vessel disc and filled as a body of water. It spans wider than the
    vessel (``span_left`` … ``span_right``) so a horizontal SMIL slide of
    up to one wavelength never exposes an un-filled edge.

    Parameters
    ----------
    surface_y : float
        The mean water line (SVG y, smaller is higher).
    amplitude : float
        Crest half-height, in pixels.
    wavelength : float
        Horizontal distance of one full ripple, in pixels.
    phase : float
        Phase offset in radians (shifts the crests sideways).
    span_left, span_right : float
        Horizontal extent to draw across (wider than the vessel).
    floor_y : float
        The bottom the body fills down to (below the vessel).

    Returns
    -------
    str
        The ``d`` attribute of a closed SVG ``<path>``.
    """
    steps = 96
    pts: List[str] = []
    for i in range(steps + 1):
        x = span_left + (span_right - span_left) * (i / steps)
        y = surface_y + amplitude * math.sin(2.0 * math.pi * x / wavelength + phase)
        pts.append(f"{x:.2f},{y:.2f}")
    d = "M " + " L ".join(pts)
    d += f" L {span_right:.2f},{floor_y:.2f} L {span_left:.2f},{floor_y:.2f} Z"
    return d


def _drift(width_px: float, dur: str, begin: str = "0s") -> str:
    """Base-visible SMIL: slide a crest band left by one wavelength and loop.

    The band is authored one wavelength wider than the vessel, so an
    endless leftward translate of exactly ``width_px`` is seamless — at
    ``t = 0`` the crest is already in place (never animated in from an
    empty tank), and the loop has no visible jump. Reduced-motion viewers
    who freeze SMIL simply see the static rippled surface.

    Parameters
    ----------
    width_px : float
        One wavelength, in pixels — the translate distance per cycle.
    dur : str
        SMIL duration string, e.g. ``"7s"``.
    begin : str, optional
        SMIL begin offset, so the two crests drift out of phase.

    Returns
    -------
    str
        An ``<animateTransform>`` element string.
    """
    return (
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="0,0;{-width_px:.2f},0" dur="{dur}" begin="{begin}" '
        f'repeatCount="indefinite"/>'
    )


def _y_for_fraction(frac: float) -> float:
    """SVG y of the water line for a fill fraction, measured inside the disc.

    Parameters
    ----------
    frac : float
        Fill fraction in ``[0, 1]`` (0 = empty at the disc bottom, 1 =
        full at the disc top).

    Returns
    -------
    float
        The y coordinate of that level.
    """
    top = _CY - _R
    bottom = _CY + _R
    return bottom - frac * (bottom - top)


def _fmt_pct(value: float) -> str:
    """Format a percentage as a whole number followed by ``%``."""
    return f"{int(round(value))}"


def build_svg(
    *, animated: bool = True, mode: str = "self-contained", accessibility: str = "universal"
) -> str:
    """Assemble the full liquid-fill gauge as an SVG string.

    Parameters
    ----------
    animated : bool, optional
        When ``True`` (default) the two crest bands carry a slow,
        base-visible SMIL drift. When ``False`` the surface is static —
        used for the raster companions so a PNG captures the settled,
        correct level rather than a mid-drift frame.
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"`` / ``"external"`` / ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level passed to :func:`_style.load_palette`
        (``"universal"`` default, plus ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` and ``"tritanopia"``). Wired
        through the ``--accessibility`` CLI flag by :func:`main`.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    back_crest, front_crest, body = _liquid_hues(accessibility)

    frac = _VALUE / 100.0
    surface_y = _y_for_fraction(frac)
    median_y = _y_for_fraction(_MEDIAN / 100.0)

    # Wave geometry. One wavelength spans a bit over the vessel width so a
    # single, calm ripple crosses the surface. Draw wider than the disc so
    # the SMIL slide never reveals an edge.
    wavelength = _R * 1.35
    amp_back = 17.0
    amp_front = 12.0
    span_left = _CX - _R - wavelength
    span_right = _CX + _R + wavelength
    floor_y = _CY + _R + 40.0

    # The readout is a deep navy so the big "63 %" clears WCAG contrast both
    # over the pale water it floats on and over the light-grey empty vessel
    # above the waterline. The body tone alone (a mid blue) only reached ~3:1
    # against the light-blue fill; deepening it lifts the number well past the
    # large-text bar while it still reads as belonging to the water.
    readout_hex = _darken(body, 0.36)

    parts: List[str] = []

    # ---- header ----
    parts.append(svg_open(_WIDTH, _HEIGHT, "lg-title", "lg-desc"))
    parts.append(
        '<title id="lg-title">Reservoir fill level: 63 percent of usable '
        'capacity, just below the seasonal normal of 68 percent</title>'
    )
    desc = (
        "A circular liquid-fill gauge shaped like a water tank. Wavy blue "
        f"liquid fills the vessel to {_fmt_pct(_VALUE)} percent of its "
        "height, with a bold percentage readout at the centre. A dashed "
        f"line marks the ten-year seasonal median of {_fmt_pct(_MEDIAN)} "
        "percent, which sits just above the current level."
    )
    parts.append(f'<desc id="lg-desc">{desc}</desc>')

    # ---- OS-adaptive style ----
    # Media-gated, so the default light render is byte-identical.
    #
    # This is a PERCEPTUAL, single-hue figure — the blue water ramp is a tuned
    # tonal map, so prefers-contrast must NOT re-space it. Instead it STRENGTHENS
    # structure: the thin vessel wall ring firms up to ink and thickens (a
    # confident frame around the vessel), the right-rim scale ticks firm to ink,
    # the dashed seasonal-median line goes fully opaque, and the muted labels
    # deepen to primary ink. Under forced-colors the wall ring takes a CanvasText
    # outline so the vessel edge survives the system palette.
    #
    # Dark mode: the default ink_map flips paper #FFFFFF and the two ink tiers;
    # the single-hue water ramp is left alone. `extra` darkens the figure's light
    # panels/lines (dry vessel, wall ring, right-rim ticks) so they read on the
    # dark surface, and pins the status-chip label back to ink — it floats on a
    # bright Orange/Green chip that stays put, so its text must NOT invert.
    parts.append(
        "<style>"
        "@media (prefers-contrast: more){"
        f'[stroke="{_RING}"]{{stroke:{_INK};stroke-width:8;}}'
        f'[stroke="{_TICK}"]{{stroke:{_INK};}}'
        f'[stroke="{_INK}"][stroke-dasharray]{{stroke-opacity:1;}}'
        f'[fill="{_SUBTLE}"]{{fill:{_INK};}}'
        "}"
        "@media (forced-colors: active){"
        f'[stroke="{_RING}"]{{stroke:CanvasText;forced-color-adjust:auto;}}'
        "}"
        + os_dark_style(
            extra=(
                '[fill="#EEF1F6"]{fill:#1B1D22;}'
                '[stroke="#D6DAE2"]{stroke:#4A4E58;}'
                '[stroke="#C2C7D0"]{stroke:#5A5F69;}'
                ".lg-chiptxt{fill:#1D1D1F;}"
            )
        )
        + "</style>"
    )

    # ---- clip path: the vessel disc that confines the liquid ----
    parts.append(
        f'<defs><clipPath id="lg-disc">'
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R:.1f}"/>'
        f'</clipPath></defs>'
    )

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle (upper-left, poster weight) ----
    parts.append(
        f'<text x="60" y="78" font-size="36" font-weight="700" '
        f'fill="{_INK}">A reservoir running a little low</text>'
    )
    parts.append(
        f'<text x="60" y="114" font-size="19" fill="{_SUBTLE}">'
        f'{xml_escape(_SUBTITLE)}</text>'
    )

    # ---- the vessel: empty (dry) disc first, then the clipped liquid ----
    # Dry background of the tank, so the space above the water reads as an
    # empty vessel, not blank page.
    parts.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R:.1f}" fill="{_EMPTY}"/>'
    )

    # Everything liquid is clipped to the disc.
    parts.append('<g clip-path="url(#lg-disc)">')

    # Deep body fill from just under the surface to the floor, so the mass
    # below the crests always reads as solid water even between ripples.
    parts.append(
        f'<rect x="{span_left:.1f}" y="{surface_y:.1f}" '
        f'width="{span_right - span_left:.1f}" '
        f'height="{floor_y - surface_y:.1f}" fill="{body}"/>'
    )

    # Back crest (darker), then sprezzature crest (lighter) drawn on top and a
    # touch lower so a slim band of the back crest shows as a highlight
    # rim. Each is authored one wavelength wide and slides via SMIL.
    back_d = _wave_path(
        surface_y, amp_back, wavelength, 0.0, span_left, span_right, floor_y
    )
    front_d = _wave_path(
        surface_y + 7.0, amp_front, wavelength, math.pi * 0.6,
        span_left, span_right, floor_y,
    )
    if animated:
        # Each crest lives in its own <g> so the drift animateTransform sits
        # on the element it moves, and the two crests slide independently.
        parts.append(
            f'<g><path d="{back_d}" fill="{back_crest}" fill-opacity="0.9"/>'
            f'{_drift(wavelength, "7.5s")}</g>'
        )
        parts.append(
            f'<g><path d="{front_d}" fill="{front_crest}" fill-opacity="0.85"/>'
            f'{_drift(wavelength, "5.5s", begin="-2s")}</g>'
        )
    else:
        parts.append(f'<path d="{back_d}" fill="{back_crest}" fill-opacity="0.9"/>')
        parts.append(
            f'<path d="{front_d}" fill="{front_crest}" fill-opacity="0.85"/>'
        )

    # Dashed seasonal-median line, clipped to the disc so it reads as a mark
    # on the vessel wall. Drawn inside the clip group, above the liquid.
    mx0 = _CX - _R
    mx1 = _CX + _R
    parts.append(
        f'<line x1="{mx0:.1f}" y1="{median_y:.1f}" x2="{mx1:.1f}" '
        f'y2="{median_y:.1f}" stroke="{_INK}" stroke-width="2" '
        f'stroke-dasharray="9 7" stroke-opacity="0.55"/>'
    )

    parts.append('</g>')  # end clip group

    # ---- vessel wall: a clean thin ring, no dark halo ----
    parts.append(
        f'<circle cx="{_CX}" cy="{_CY}" r="{_R:.1f}" fill="none" '
        f'stroke="{_RING}" stroke-width="6"/>'
    )

    # ---- percentage scale down the right rim (0/25/50/75/100) ----
    for pct in (0, 25, 50, 75, 100):
        ly = _y_for_fraction(pct / 100.0)
        # Tick just outside the ring on the right side.
        tx0 = _CX + _R + 8
        tx1 = _CX + _R + 22
        parts.append(
            f'<line x1="{tx0:.1f}" y1="{ly:.1f}" x2="{tx1:.1f}" y2="{ly:.1f}" '
            f'stroke="{_TICK}" stroke-width="2.4" stroke-linecap="round"/>'
        )
        parts.append(
            f'<text x="{tx1 + 8:.1f}" y="{ly + 6:.1f}" font-size="18" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'text-anchor="start">{pct}%</text>'
        )

    # ---- median callout, pinned to the dashed line on the left rim ----
    parts.append(
        f'<text x="{_CX - _R - 12:.1f}" y="{median_y - 12:.1f}" '
        f'font-size="17" font-weight="600" fill="{_INK}" text-anchor="end">'
        f'seasonal normal</text>'
    )
    parts.append(
        f'<text x="{_CX - _R - 12:.1f}" y="{median_y + 10:.1f}" '
        f'font-size="16" fill="{_SUBTLE}" text-anchor="end">'
        f'{_fmt_pct(_MEDIAN)}% median</text>'
    )

    # ---- centre readout: the big number, its unit, and what it measures ----
    # The number sits a little above centre so the caption below balances it
    # within the disc; both stay clear of the water line at 63 %.
    ny = _CY - 6.0
    parts.append(
        f'<text x="{_CX:.0f}" y="{ny:.0f}" font-size="150" font-weight="800" '
        f'fill="{readout_hex}" text-anchor="middle">'
        f'{_fmt_pct(_VALUE)}<tspan font-size="66" dx="6" '
        f'fill="{readout_hex}" fill-opacity="0.72">%</tspan></text>'
    )
    parts.append(
        f'<text x="{_CX:.0f}" y="{ny + 44:.0f}" font-size="24" '
        f'font-weight="600" fill="{readout_hex}" fill-opacity="0.85" '
        f'text-anchor="middle">{xml_escape(_METRIC)}</text>'
    )

    # ---- status chip: names how the level compares to normal (pure fill) ----
    delta = _VALUE - _MEDIAN
    below = delta < 0
    chip_palette = load_palette(accessibility)
    chip_hex = (chip_palette.get("Orange") or "#FF9500") if below else (
        chip_palette.get("Green") or "#34C759"
    )
    chip_txt = (
        f"{abs(int(round(delta)))} pts below normal"
        if below
        else f"{abs(int(round(delta)))} pts above normal"
    )
    chip_w, chip_h = 330.0, 52.0
    chip_x = _CX - chip_w / 2.0
    chip_y = ny + 96.0
    parts.append(
        f'<rect x="{chip_x:.1f}" y="{chip_y:.1f}" width="{chip_w:.0f}" '
        f'height="{chip_h:.0f}" rx="26" fill="{chip_hex}"/>'
    )
    # Orange and green are both light enough that ink text stays high
    # contrast; no white-on-yellow, no dark ring on the chip.
    parts.append(
        f'<text class="lg-chiptxt" x="{_CX:.0f}" y="{chip_y + 34:.1f}" font-size="23" '
        f'font-weight="700" fill="{_INK}" text-anchor="middle">'
        f'{xml_escape(chip_txt)}</text>'
    )

    # ---- footnote: how to read the vessel ----
    parts.append(
        f'<text x="{_WIDTH - 60:.0f}" y="{_HEIGHT - 40:.0f}" font-size="16" '
        f'fill="{_SUBTLE}" text-anchor="end">The waterline is the fill level; '
        f'the dashed line is the 10-year seasonal median.</text>'
    )

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the liquid-gauge SVG (and PNG companions) into the skill."""
    here = Path(__file__).resolve().parent
    out_svg = here.parent / "assets" / "svg-examples" / "liquid-gauge.svg"
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser(description="Render the liquid-gauge SVG (and PNG companions).")
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="interactivity mode of the emitted SVG (default: self-contained)",
    )
    parser.add_argument(
        "--accessibility",
        choices=("universal", "high-contrast", "monochrome", "deuteranopia", "protanopia", "tritanopia"),
        default="universal",
        help="palette accessibility level (default: universal, the CVD-safe standard)",
    )
    args = parser.parse_args()
    out_svg.write_text(
        build_svg(animated=True, mode=args.mode, accessibility=args.accessibility),
        encoding="utf-8",
    )

    # Static (non-animated) SVG for the raster companions so the PNG is the
    # settled truth, not a mid-drift frame.
    try:
        import vl_convert as vlc  # only needed for the PNG companions

        png = vlc.svg_to_png(
            build_svg(animated=False, mode="static", accessibility=args.accessibility), scale=2
        )
        for dest in (
            here.parent / "assets" / "figures-gallery" / "liquid-gauge.png",
            here.parents[1] / "web" / "img" / "figures" / "liquid-gauge.png",
        ):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(png)
    except Exception:  # noqa: BLE001 — PNG companions are best-effort
        pass

    print(f"wrote {out_svg}")


if __name__ == "__main__":
    main()

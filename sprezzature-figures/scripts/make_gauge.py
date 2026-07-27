"""
make_gauge — a radial (angular) gauge with coloured zones and a needle.

Renders a single key-performance-indicator as a 240-degree angular
gauge: a thick rounded arc split into coloured performance zones
(healthy → busy → hot → critical), a tapered needle pointing at the
current value, a small hub, and a big number read-out in the middle.
Minor and major ticks sit just inside the arc, and each zone is named
outside it so the reader knows what "72 %" *means* without a legend.

The example measures **web-server CPU load** at a traffic peak: the
needle lands at 72 %, inside the amber "Busy" zone — comfortably under
the red line but worth watching. A subtle, base-visible SMIL animation
lets the needle *settle* into place (it starts already on the dial at a
plausible reading, then eases to the final value — it never sweeps in
from nothing), so the static raster is always a correct, complete gauge.

Pure-Python, hand-built SVG string (no Vega, no matplotlib) because the
arc/needle/tick geometry has to be placed exactly. Big canvas by design.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from _style import load_palette, os_adaptive_style, os_dark_style
from _svg import point_on_circle, xml_escape
from _interactive import fullscreen_control

# ------------------------------------------------------------------
# The reading. One illustrative KPI: web-server CPU load at a traffic
# peak. ``value`` is the needle position; ``settle_from`` is the (also
# plausible) reading the needle starts on so the animation is
# base-visible — it eases *between* two real states, never in from zero.
# ------------------------------------------------------------------
VALUE: float = 72.0            # % — where the needle points (static truth)
SETTLE_FROM: float = 58.0      # % — where the settle animation begins
UNIT: str = "%"
VMIN, VMAX = 0.0, 100.0

TITLE = "Web-server CPU load is running hot at the traffic peak"
SUBTITLE = "app-07 · 12:40 UTC · 1-minute average · illustrative reading"

# Coloured performance zones, low → high. Each is (upper-bound, colour-key,
# label). Bounds are cumulative and end at VMAX.
ZONES: List[Tuple[float, str, str]] = [
    (50.0, "Green",  "Healthy"),
    (75.0, "Yellow", "Busy"),
    (90.0, "Orange", "Hot"),
    (100.0, "Red",   "Critical"),
]

PAL = load_palette()

INK = "#1D1D1F"
SECONDARY = "#6E6E73"
TICK = "#C7C7CC"
TRACK = "#ECECEF"      # faint full-arc groove behind the coloured zones
FONT = "Roboto, system-ui, sans-serif"

# ------------------------------------------------------------------
# Geometry — a 240-degree arc, open at the bottom. Angles are measured
# in SVG screen space (y grows downward). START_DEG is the left/low end
# of the sweep; the needle rotates clockwise to END_DEG at full scale.
# 150° → 30° over the top is a 240° span (the classic speedometer look).
# ------------------------------------------------------------------
W, H = 1200, 860
CX, CY = 600, 560
R_MID = 300.0                  # centre-line radius of the coloured band
BAND = 46.0                    # band thickness
R_OUT = R_MID + BAND / 2.0
R_IN = R_MID - BAND / 2.0

START_DEG = 150.0              # low end (0 %)
SWEEP_DEG = 240.0              # total sweep, clockwise in screen space
GAP_DEG = 1.4                  # tiny gap between neighbouring zones


def _text_on(hex_fill: str) -> str:
    """Pick ink or white text for legibility on a solid ``hex_fill``.

    Uses the WCAG relative-luminance rule of thumb: light fills (Yellow,
    Mint) get ink text, dark fills (Red, Blue) get white — never
    low-contrast white-on-yellow.
    """
    h = hex_fill.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    # Perceptual luminance (sRGB coefficients, gamma left linear-ish — the
    # threshold is tuned for the eight house hues, not a colour-science lab).
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return INK if lum > 0.6 else "#FFFFFF"


def _ang(value: float) -> float:
    """Screen-space angle (radians) for a value on the ``VMIN..VMAX`` scale."""
    frac = (value - VMIN) / (VMAX - VMIN)
    return math.radians(START_DEG + SWEEP_DEG * frac)


def _pt(radius: float, deg_or_rad: float, *, deg: bool = False) -> Tuple[float, float]:
    """Cartesian point at ``radius``/angle about the gauge centre."""
    theta = math.radians(deg_or_rad) if deg else deg_or_rad
    return point_on_circle(CX, CY, radius, theta)


def _arc(r: float, a0: float, a1: float) -> str:
    """SVG ``A`` command tracing radius ``r`` from angle ``a0`` to ``a1`` (rad)."""
    x, y = _pt(r, a1)
    large = 1 if abs(a1 - a0) > math.pi else 0
    sweep = 1 if a1 > a0 else 0
    return f"A{r:.2f},{r:.2f} 0 {large} {sweep} {x:.2f},{y:.2f}"


def _band_segment(a0: float, a1: float) -> str:
    """Filled path for one zone: outer arc out, cap, inner arc back, cap."""
    x0o, y0o = _pt(R_OUT, a0)
    x1i, y1i = _pt(R_IN, a1)
    d = [f"M{x0o:.2f},{y0o:.2f}", _arc(R_OUT, a0, a1)]
    # rounded end-cap across the band thickness at a1
    d.append(f"A{BAND / 2:.2f},{BAND / 2:.2f} 0 0 1 {x1i:.2f},{y1i:.2f}")
    d.append(_arc(R_IN, a1, a0))
    x0i, y0i = _pt(R_IN, a0)
    d.append(f"A{BAND / 2:.2f},{BAND / 2:.2f} 0 0 1 {x0o:.2f},{y0o:.2f}")
    d.append("Z")
    return " ".join(d)


def _round_track() -> str:
    """The faint full-span groove behind the coloured zones (rounded caps)."""
    a0, a1 = _ang(VMIN), _ang(VMAX)
    x0, y0 = _pt(R_MID, a0)
    d = [f"M{x0:.2f},{y0:.2f}", _arc(R_MID, a0, a1)]
    return (
        f'<path d="{" ".join(d)}" fill="none" stroke="{TRACK}" '
        f'stroke-width="{BAND:.0f}" stroke-linecap="round"/>'
    )


def _needle(deg: float) -> str:
    """A tapered needle from a back-stub through the hub to a point near R_IN.

    Returns the needle group *without* its own transform so the caller can
    wrap it and drive rotation with SMIL.
    """
    tip = R_IN - 10.0
    back = 58.0
    half = 9.0            # half-width at the hub
    # Local frame: needle points along +x at angle 0, caller rotates it.
    d = (
        f"M{tip:.1f},0 "
        f"L{half:.1f},{-half:.1f} "
        f"L{-back:.1f},{-3.5:.1f} "
        f"L{-back:.1f},{3.5:.1f} "
        f"L{half:.1f},{half:.1f} Z"
    )
    return (
        f'<g transform="translate({CX},{CY})">'
        f'<g transform="rotate({deg:.3f})">'
        f'<path d="{d}" fill="{INK}"/>'
        "</g></g>"
    )


def _needle_animated(deg_from: float, deg_to: float) -> str:
    """Needle whose rotation eases once from ``deg_from`` to ``deg_to``.

    Base-visible: the path is authored at ``deg_to`` (the static truth); the
    ``<animateTransform>`` overrides it for the first ~1.6 s, starting at
    ``deg_from`` (a real, on-dial reading) and settling to ``deg_to`` with a
    gentle ease-out. Reduced-motion users who freeze SMIL simply see the
    correct final needle.
    """
    tip = R_IN - 10.0
    back = 58.0
    half = 9.0
    d = (
        f"M{tip:.1f},0 "
        f"L{half:.1f},{-half:.1f} "
        f"L{-back:.1f},{-3.5:.1f} "
        f"L{-back:.1f},{3.5:.1f} "
        f"L{half:.1f},{half:.1f} Z"
    )
    # Two-key ease-out settle: overshoot slightly then land, feels mechanical.
    # The path carries its OWN static rotate(deg_to) so the base (frozen /
    # reduced-motion) state is the correct final needle; the animateTransform
    # replaces that transform for the first ~1.6 s, easing from deg_from to
    # deg_to. Rotation is about the local origin, which the outer group has
    # translated onto the hub — so the needle pivots on the hub, not (0,0).
    over = deg_to + (deg_to - deg_from) * 0.06
    vals = f"{deg_from:.3f};{over:.3f};{deg_to:.3f}"
    return (
        f'<g transform="translate({CX},{CY})">'
        f'<path d="{d}" fill="{INK}" transform="rotate({deg_to:.3f})">'
        f'<animateTransform attributeName="transform" type="rotate" '
        f'values="{vals}" keyTimes="0;0.7;1" '
        f'dur="1.6s" calcMode="spline" '
        f'keySplines="0.22 1 0.36 1;0.33 1 0.68 1" '
        f'begin="0.25s" fill="freeze"/>'
        "</path>"
        "</g>"
    )


def _ticks() -> List[str]:
    """Minor ticks every 5 units, longer major ticks every 25.

    Numeric scale labels are deliberately *not* drawn on the inner ring —
    they would collide with the needle and the centred read-out. The scale
    is anchored instead by the coloured zones plus the 0/100 end captions.
    """
    out: List[str] = []
    step = 5
    n = int(round((VMAX - VMIN) / step))
    for i in range(n + 1):
        v = VMIN + i * step
        major = (v % 25 == 0)
        a = _ang(v)
        r_from = R_IN - 6.0
        r_to = R_IN - (26.0 if major else 14.0)
        x0, y0 = _pt(r_from, a)
        x1, y1 = _pt(r_to, a)
        out.append(
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
            f'stroke="{TICK}" stroke-width="{3.0 if major else 1.6:.1f}" '
            f'stroke-linecap="round"/>'
        )
    return out


def _zone_labels() -> List[str]:
    """Curved-position zone names sitting just outside the coloured band."""
    out: List[str] = []
    lo = VMIN
    for upper, key, name in ZONES:
        mid = (lo + upper) / 2.0
        a = _ang(mid)
        r = R_OUT + 34.0
        x, y = _pt(r, a)
        # Nudge anchor by side so long names don't crowd the arc.
        cos_a = math.cos(a)
        if cos_a > 0.30:
            anchor = "start"
        elif cos_a < -0.30:
            anchor = "end"
        else:
            anchor = "middle"
        # Zone names in ink, not the zone hue: Yellow / Green / Orange on
        # white all fall below WCAG AA as small text (Yellow "Busy" is worst
        # at ~1.6:1). The coloured arc band sits right beside each name and
        # carries the hue, so the label stays crisp for everyone, including
        # in greyscale and under colour-vision deficiency.
        del key  # colour now comes from the adjacent band, not the text
        out.append(
            f'<text x="{x:.1f}" y="{y + 6:.1f}" font-size="22" font-weight="600" '
            f'fill="{INK}" text-anchor="{anchor}">{xml_escape(name)}</text>'
        )
        lo = upper
    return out


def _zone_of(value: float, pal: Optional[Dict[str, str]] = None) -> Tuple[str, str]:
    """Return the (colour-hex, name) of the zone containing ``value``.

    Parameters
    ----------
    value : float
        The gauge reading to classify.
    pal : dict of str to str, optional
        Palette colour map; defaults to the module-level :data:`PAL`
        (the universal palette).
    """
    if pal is None:
        pal = PAL
    for upper, key, name in ZONES:
        if value <= upper or upper == VMAX:
            return pal[key], name
    return pal[ZONES[-1][1]], ZONES[-1][2]


def build_svg(*, animated: bool = True, mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full radial gauge as an SVG string.

    Parameters
    ----------
    animated : bool, optional
        Whether the needle sweeps in on load (default ``True``).
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
        A complete, self-contained SVG document.
    """
    pal = load_palette(accessibility)
    val_hex, val_name = _zone_of(VALUE, pal)

    # Specific alt text: the takeaway plus the exact reading and its zone, so
    # a screen-reader user gets the same headline as a sighted one.
    desc_txt = (
        f"Radial gauge of web-server CPU load, scaled 0 to 100 percent of "
        f"capacity across four named zones: Healthy, Busy, Hot, Critical. The "
        f"needle points to {int(VALUE)} percent, inside the {val_name} zone."
    )
    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{FONT}" '
        f'role="img" aria-labelledby="gauge-title gauge-desc">',
        f'<title id="gauge-title">{xml_escape(TITLE)}</title>',
        f'<desc id="gauge-desc">{xml_escape(desc_txt)}</desc>',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        # Title block, left-aligned above the dial.
        f'<text x="70" y="82" font-size="34" font-weight="700" fill="{INK}">'
        f"{xml_escape(TITLE)}</text>",
        f'<text x="70" y="120" font-size="20" fill="{SECONDARY}">'
        f"{xml_escape(SUBTITLE)}</text>",
        # Faint groove, then the coloured zones on top.
        _round_track(),
    ]

    # OS-adaptive overrides for the four coloured zones (additive; the default
    # render stays byte-identical because every rule below lives inside an
    # @media query, and the class only outranks the inline fill once the query
    # matches). Under prefers-contrast each zone band deepens to its
    # high-contrast hue while keeping the Green→Yellow→Orange→Red order.
    # forced=True is safe: the four zones are named in text (Healthy, Busy, Hot,
    # Critical) and sit at fixed positions along the arc, so their identity
    # survives with no colour. The centre value chip is left universal — its
    # zone name is spelled out in the pill, and its contrast-aware text colour is
    # computed for the base hue, so it must not be re-tinted here.
    zone_series = {f".zone-{key}": pal[key] for _u, key, _n in ZONES}
    parts.append(
        "<style>"
        + os_adaptive_style(zone_series, role="fill", forced=True)
        # Additive dark mode: flip paper + the two ink tiers (data hues untouched).
        + os_dark_style()
        + "</style>"
    )

    lo = VMIN
    seg_gap = math.radians(GAP_DEG)
    for upper, key, _name in ZONES:
        a0 = _ang(lo) + (seg_gap if lo > VMIN else 0.0)
        a1 = _ang(upper) - (seg_gap if upper < VMAX else 0.0)
        parts.append(
            f'<path class="zone-{key}" d="{_band_segment(a0, a1)}" '
            f'fill="{pal[key]}"/>'
        )
        lo = upper

    parts.extend(_ticks())
    parts.extend(_zone_labels())

    # Needle + hub go BELOW the read-out in paint order so the number stays
    # crisp, but geometrically the needle lives at (CX, CY) and the big
    # number sits in the open bottom of the dial — the two never overlap.
    if animated:
        parts.append(
            _needle_animated(START_DEG + SWEEP_DEG * (SETTLE_FROM / 100.0),
                             START_DEG + SWEEP_DEG * (VALUE / 100.0))
        )
    else:
        parts.append(_needle(START_DEG + SWEEP_DEG * (VALUE / 100.0)))
    # Hub: a filled ink disc with a small white centre (clean, no ring).
    parts.append(f'<circle cx="{CX}" cy="{CY}" r="20" fill="{INK}"/>')
    parts.append(f'<circle cx="{CX}" cy="{CY}" r="7" fill="#FFFFFF"/>')

    # Big number read-out — the headline — sits in the open bottom of the
    # dial, clear of the needle hub. Value + unit, then a coloured zone chip
    # that names where the needle landed.
    ry = CY + 148.0
    parts.append(
        f'<text x="{CX}" y="{ry:.0f}" font-size="128" font-weight="800" '
        f'fill="{INK}" text-anchor="middle" '
        f'font-family="Roboto, system-ui, sans-serif">'
        f'{int(VALUE)}<tspan font-size="60" fill="{SECONDARY}" '
        f'dx="4">{xml_escape(UNIT)}</tspan></text>'
    )
    # Zone chip: a coloured pill naming the current zone (pure fill,
    # contrast-aware text, no dark ring), centred under the number.
    chip_txt = f"{val_name} · of 100% capacity"
    chip_w, chip_h = 300.0, 48.0
    chip_x = CX - chip_w / 2.0
    chip_y = ry + 30.0
    parts.append(
        f'<rect x="{chip_x:.1f}" y="{chip_y:.1f}" width="{chip_w:.0f}" '
        f'height="{chip_h:.0f}" rx="24" fill="{val_hex}"/>'
    )
    parts.append(
        f'<text x="{CX}" y="{chip_y + 32:.1f}" font-size="23" font-weight="700" '
        f'fill="{_text_on(val_hex)}" text-anchor="middle">'
        f"{xml_escape(chip_txt)}</text>"
    )

    # End-of-scale captions (0 and 100) just outside the arc tips.
    for v, txt in ((VMIN, "0"), (VMAX, "100")):
        a = _ang(v)
        x, y = _pt(R_OUT + 4, a)
        parts.append(
            f'<text x="{x:.1f}" y="{y + 34:.1f}" font-size="21" '
            f'fill="{SECONDARY}" text-anchor="middle" '
            f'font-family="Roboto Mono, monospace">{txt}</text>'
        )

    parts.append(fullscreen_control(W, H, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Render the gauge to SVG (and companion PNGs)."""
    import vl_convert as vlc  # only needed for the PNG companions

    parser = argparse.ArgumentParser(description="Render the gauge SVG (and PNG companions).")
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
    svg = build_svg(animated=True, mode=args.mode, accessibility=args.accessibility)
    here = Path(__file__).resolve().parent
    out_svg = here.parent / "assets" / "svg-examples" / "gauge.svg"
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    out_svg.write_text(svg, encoding="utf-8")

    # Static (non-animated) SVG for the raster companions so the PNG is the
    # settled truth, not a mid-animation frame.
    png = vlc.svg_to_png(build_svg(animated=False, mode="static", accessibility=args.accessibility), scale=2)
    for dest in (
        here.parent / "assets" / "figures-gallery" / "gauge.png",
        here.parents[1] / "web" / "img" / "figures" / "gauge.png",
    ):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(png)

    print(f"wrote {out_svg}")


if __name__ == "__main__":
    main()

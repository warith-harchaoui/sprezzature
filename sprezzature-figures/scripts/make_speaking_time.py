"""
make_speaking_time — a speaker-diarisation "who spoke, and for how long" donut.

Turns a diarisation result (one row per speaker, with a talk-time in
seconds) into a large, clean donut where each slice is one speaker. Each
slice is annotated **outside the ring** with the speaker's name, the
human-readable duration (``mm:ss``) and its share of the conversation
(``%``); a thin leader line ties each annotation to its arc, and labels
are side-aware (right labels left-aligned, left labels right-aligned) so
the spacing stays harmonious all the way round. The hole carries the
total running time — the headline number.

Pure-Python, hand-built SVG string (no Vega, no matplotlib) so the label
geometry can be placed exactly. Big canvas by design.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, List

from _interactive import fullscreen_control
from _style import load_palette, os_adaptive_style, os_dark_style
from _svg import point_on_circle, xml_escape

# ------------------------------------------------------------------
# Illustrative diarisation output — a 40-minute round-table. Talk-time
# is whole seconds so ``mm:ss`` and ``%`` stay mutually consistent; the
# four values sum to 2400 s = 40:00 with clean integer percentages.
# ------------------------------------------------------------------
SPEAKERS: List[Dict[str, object]] = [
    {"name": "Alice Nguyen", "seconds": 984},   # 16:24 · 41 %
    {"name": "Marc Dubois", "seconds": 648},     # 10:48 · 27 %
    {"name": "Sofia Rossi", "seconds": 432},     # 07:12 · 18 %
    {"name": "Karim Haddad", "seconds": 336},    # 05:36 · 14 %
]

def _slice_colors(accessibility: str = "universal") -> List[str]:
    """Return the four donut-slice hues at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`.

    Returns
    -------
    list of str
        Four hex strings, one per speaker slice (in speaker order).
    """
    pal = load_palette(accessibility)
    return [pal["Blue"], pal["Orange"], pal["Green"], pal["Purple"]]


SLICE_COLORS = _slice_colors()

INK = "#1D1D1F"
SECONDARY = "#6E6E73"
LEADER = "#C7C7CC"
FONT = "Roboto, system-ui, sans-serif"

# Geometry — deliberately large.
W, H = 1120, 760
CX, CY = 540, 430
R_OUT, R_IN = 250, 158


def _mmss(seconds: int) -> str:
    """Format whole seconds as ``m:ss`` (or ``mm:ss``)."""
    return f"{seconds // 60}:{seconds % 60:02d}"


# Thin wrapper over the shared polar helper; call sites keep the _pt name
# and the (cx, cy, radius, angle) argument order.
def _pt(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    """Cartesian point at ``radius``/``angle`` (radians) about a centre."""
    return point_on_circle(cx, cy, radius, angle)


#: Corner radius on each segment end, and the angular gap between
#: neighbouring segments (radians). Together these give the modern
#: "floating rounded pills" donut look — rounded but never notched.
CORNER = 14.0
GAP = 0.028


def _segment(a0: float, a1: float) -> str:
    """SVG path ``d`` for one donut segment with rounded corners + a gap.

    Insets each end by :data:`GAP` (so neighbours don't touch) and fillets
    all four corners with a :data:`CORNER`-radius quarter arc, drawn
    clockwise: outer arc → outer/end fillet → radial in → inner/end
    fillet → inner arc back → inner/start fillet → radial out →
    outer/start fillet.
    """
    a0 += GAP
    a1 -= GAP
    cr = CORNER
    dao = cr / R_OUT  # angular back-off for a corner at the outer radius
    dai = cr / R_IN
    seg: List[str] = []
    x, y = _pt(CX, CY, R_OUT, a0 + dao)
    seg.append(f"M{x:.2f},{y:.2f}")
    x, y = _pt(CX, CY, R_OUT, a1 - dao)
    large = 1 if (a1 - dao) - (a0 + dao) > math.pi else 0
    seg.append(f"A{R_OUT},{R_OUT} 0 {large} 1 {x:.2f},{y:.2f}")
    x, y = _pt(CX, CY, R_OUT - cr, a1)
    seg.append(f"A{cr},{cr} 0 0 1 {x:.2f},{y:.2f}")
    x, y = _pt(CX, CY, R_IN + cr, a1)
    seg.append(f"L{x:.2f},{y:.2f}")
    x, y = _pt(CX, CY, R_IN, a1 - dai)
    seg.append(f"A{cr},{cr} 0 0 1 {x:.2f},{y:.2f}")
    x, y = _pt(CX, CY, R_IN, a0 + dai)
    large = 1 if (a1 - dai) - (a0 + dai) > math.pi else 0
    seg.append(f"A{R_IN},{R_IN} 0 {large} 0 {x:.2f},{y:.2f}")
    x, y = _pt(CX, CY, R_IN + cr, a0)
    seg.append(f"A{cr},{cr} 0 0 1 {x:.2f},{y:.2f}")
    x, y = _pt(CX, CY, R_OUT - cr, a0)
    seg.append(f"L{x:.2f},{y:.2f}")
    x, y = _pt(CX, CY, R_OUT, a0 + dao)
    seg.append(f"A{cr},{cr} 0 0 1 {x:.2f},{y:.2f}")
    seg.append("Z")
    return " ".join(seg)


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full speaking-time donut as an SVG string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"`` / ``"external"`` / ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level passed to :func:`_style.load_palette`
        (``"universal"`` default, plus ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` and ``"tritanopia"``). Wired
        through the ``--accessibility`` CLI flag by :func:`main`.
    """
    slice_colors = _slice_colors(accessibility)
    total = sum(int(s["seconds"]) for s in SPEAKERS)

    # Accessible name + description. Every slice is also labelled outside
    # the ring with its speaker's name, duration and share, so identity is
    # never carried by colour alone — it survives colour-blindness and
    # greyscale. The description names the speakers in order so a screen
    # reader conveys the same ranking a sighted reader sees.
    ranked = ", ".join(
        f"{s['name']} {_mmss(int(s['seconds']))} "
        f"({round(100 * int(s['seconds']) / total)} %)"
        for s in SPEAKERS
    )
    a11y_title = "Qui a parlé, et combien de temps"
    a11y_desc = (
        "Anneau (donut) du temps de parole par intervenant sur une table "
        "ronde de 40 minutes. Chaque part est un intervenant, étiquetée à "
        "l'extérieur de l'anneau avec son nom, sa durée (mm:ss) et sa part "
        f"du total en pourcentage : {ranked}. Le centre affiche le temps "
        "total, 40:00. Données illustratives."
    )

    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{FONT}" role="img" '
        f'aria-labelledby="st-title st-desc">',
        f'<title id="st-title">{xml_escape(a11y_title)}</title>',
        f'<desc id="st-desc">{xml_escape(a11y_desc)}</desc>',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        # Title block.
        f'<text x="60" y="66" font-size="30" font-weight="700" fill="{INK}">'
        f"Qui a parlé, et combien de temps</text>",
        f'<text x="60" y="98" font-size="18" fill="{SECONDARY}">'
        f"Temps de parole par intervenant · table ronde de 40 min · données illustratives</text>",
    ]

    # OS-adaptive overrides (additive, all inside @media so the default render
    # is byte-for-byte unchanged). Each slice carries a stable ``.slice-i``
    # class as an @media hook: under prefers-contrast the slice fills deepen to
    # their high-contrast hues, and under forced colours the ring drops to
    # system-palette line art — legitimate here because every slice is also
    # labelled outside the ring (name, duration, share), so identity is carried
    # by the labels, not by colour.
    slice_series = {f".slice-{i}": color for i, color in enumerate(slice_colors)}
    parts.append(
        "<style>\n"
        + os_adaptive_style(
            slice_series,
            role="fill",
            forced=True,
            forced_keyword="Canvas",
            extra_forced=".slice{stroke:CanvasText;stroke-width:2;}",
        )
        + os_dark_style()
        + "\n</style>"
    )

    # Arcs start at the top (−90°) and run clockwise.
    angle = -math.pi / 2
    labels: List[str] = []
    for i, (spk, color) in enumerate(zip(SPEAKERS, slice_colors)):
        secs = int(spk["seconds"])
        frac = secs / total
        a0, a1 = angle, angle + 2 * math.pi * frac
        angle = a1
        parts.append(f'<path class="slice slice-{i}" d="{_segment(a0, a1)}" fill="{color}"/>')

        # Side-aware outside annotation with a thin leader.
        mid = (a0 + a1) / 2
        cos_m = math.cos(mid)
        rx, ry = _pt(CX, CY, R_OUT + 6, mid)
        ex, ey = _pt(CX, CY, R_OUT + 30, mid)
        if cos_m > 0.25:
            tx, anchor = ex + 14, "start"
            hx = tx
        elif cos_m < -0.25:
            tx, anchor = ex - 14, "end"
            hx = tx
        else:
            tx, anchor = ex, "middle"
            hx = ex
        pct = round(100 * secs / total)
        labels.append(
            f'<polyline points="{rx:.1f},{ry:.1f} {ex:.1f},{ey:.1f} {hx:.1f},{ey:.1f}" '
            f'fill="none" stroke="{LEADER}" stroke-width="1.4"/>'
            f'<text x="{tx:.1f}" y="{ey - 4:.1f}" font-size="19" font-weight="700" '
            f'fill="{INK}" text-anchor="{anchor}">{spk["name"]}</text>'
            f'<text x="{tx:.1f}" y="{ey + 18:.1f}" font-size="16" '
            f'fill="{SECONDARY}" text-anchor="{anchor}">{_mmss(secs)} · {pct}%</text>'
        )

    parts.extend(labels)

    # Centre: total running time — the headline number.
    parts.append(
        f'<text x="{CX}" y="{CY - 4}" font-size="52" font-weight="700" '
        f'fill="{INK}" text-anchor="middle">{_mmss(total)}</text>'
    )
    parts.append(
        f'<text x="{CX}" y="{CY + 30}" font-size="19" fill="{SECONDARY}" '
        f'text-anchor="middle">temps total</text>'
    )
    parts.append(fullscreen_control(W, H, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Render the speaking-time donut to SVG (and a companion PNG)."""
    import vl_convert as vlc  # only needed for the PNG companion

    parser = argparse.ArgumentParser(description="Render the speaking-time SVG (and a PNG companion).")
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
    svg = build_svg(mode=args.mode, accessibility=args.accessibility)
    here = Path(__file__).resolve().parent
    out_svg = here.parent / "assets" / "svg-examples" / "speaking_time.svg"
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    out_svg.write_text(svg, encoding="utf-8")

    png = vlc.svg_to_png(svg, scale=2)
    for dest in (
        here.parent / "assets" / "figures-gallery" / "speaking_time.png",
        here.parents[1] / "web" / "img" / "figures" / "speaking_time.png",
    ):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(png)

    print(f"wrote {out_svg}")


if __name__ == "__main__":
    main()

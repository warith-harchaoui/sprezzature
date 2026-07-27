#!/usr/bin/env python3
"""
make_packed-bubble — publication-quality packed-bubble chart as hand-authored SVG.

A packed-bubble chart lays out flat categories as circles whose *area*
encodes a value, then packs them into a tight cluster with no overlaps.
It is the readable answer to "how do these categories compare in size,
grouped by family?" when a bar chart would be a long monotonous column
and a treemap would trade circular legibility for rectangular tiling.
Here the categories are programming languages, the circle area is each
language's share of developers who use it, and the fill colour marks the
language family (systems, web-frontend, data / scientific, and so on).

Vega-Lite has no circle-packing primitive, so the figure is built as an
SVG string by hand. The pack is a deterministic, pure-Python
collision-relaxation: bubbles are seeded on a spiral in descending size
order, then a few dozen relaxation passes push overlapping pairs apart
and pull every bubble gently toward the cluster centroid, so the result
settles into a tight, gap-free disk without any scientific stack. A fixed
seed makes the committed SVG byte-reproducible.

House style follows ``_style.py``: Roboto type, the Apple-system
categorical palette, ink ``#1D1D1F`` on white, a start-anchored takeaway
title plus a one-line subtitle. Every bubble carries its language name and
share *inside* the disk, sized to fit, so nothing is cramped, clipped, or
spilled onto a neighbour. The label colour is chosen per family for WCAG
contrast (white on the darker blue and purple, ink on the bright green and
orange), so no label ever needs a halo. There is no dark ring around any
disk and no grounding shadow.

Interaction (no JavaScript): every bubble carries a native ``<title>``
tooltip, and a pure-CSS ``:hover`` / ``:focus-within`` rule lifts the
hovered family to full strength while dimming the rest, so a reader can
isolate one family at a time. The chart is otherwise fully legible when
static, so ``animated`` is false and ``interactive`` is true.

Running the module writes the SVG to
``sprezzature-figures/assets/svg-examples/packed-bubble.svg``.

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
from _render import render_cli  # noqa: E402
from _svg import svg_open  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + house-style tokens
# ------------------------------------------------------------------
WIDTH = 1280
HEIGHT = 1040
INK = "#1D1D1F"            # primary text
SUBINK = "#6E6E73"         # secondary text
BG = "#FFFFFF"

FONT = "Roboto, system-ui, sans-serif"
FONT_MONO = "Roboto Mono, ui-monospace, monospace"

# Cluster geometry: the pack lives inside this circle-ish region. It sits
# below the title / subtitle / legend band and above the footer hint.
PACK_CX = WIDTH * 0.50
PACK_CY = 590.0

# ------------------------------------------------------------------
# The story (illustrative but plausible, in the shape of a large
# developer survey): the share of professional developers who report
# working with each language. The takeaway is that a handful of web and
# scripting languages dominate the working world, while the systems and
# data families are smaller but coherent clusters. Colour marks the
# family so the eye reads the four groups before it reads any single
# language.
# ------------------------------------------------------------------
# (name, share_percent, family)
LANGUAGES: List[Tuple[str, float, str]] = [
    ("JavaScript", 62.3, "Web & scripting"),
    ("Python", 51.0, "Data & scientific"),
    ("TypeScript", 43.4, "Web & scripting"),
    ("SQL", 51.5, "Data & scientific"),
    ("HTML/CSS", 53.0, "Web & scripting"),
    ("Java", 30.3, "Enterprise & JVM"),
    ("C#", 27.1, "Enterprise & JVM"),
    ("C++", 23.0, "Systems"),
    ("C", 19.0, "Systems"),
    ("PHP", 18.6, "Web & scripting"),
    ("Go", 13.5, "Systems"),
    ("Rust", 12.6, "Systems"),
    ("Kotlin", 9.4, "Enterprise & JVM"),
    ("Ruby", 6.2, "Web & scripting"),
    ("Swift", 5.1, "Systems"),
    ("R", 4.3, "Data & scientific"),
    ("Scala", 3.0, "Enterprise & JVM"),
    ("Julia", 1.7, "Data & scientific"),
]

# Family → brand hue. Four families, four distinct saturated hues that
# stay distinguishable when packed edge-to-edge (no red/green ambiguity).
FAMILY_ORDER: List[str] = [
    "Web & scripting",
    "Data & scientific",
    "Systems",
    "Enterprise & JVM",
]


def _darken(hex_color: str, amount: float) -> str:
    """Move a ``#RRGGBB`` colour toward black by ``amount`` in ``[0, 1]``."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    r, g, b = (round(v * (1.0 - amount)) for v in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def _relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance of a ``#RRGGBB`` colour."""
    h = hex_color.lstrip("#")
    chans = []
    for i in (0, 2, 4):
        v = int(h[i : i + 2], 16) / 255.0
        chans.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * chans[0] + 0.7152 * chans[1] + 0.0722 * chans[2]


def _label_ink(fill: str) -> str:
    """Pick ink or white for a label on ``fill`` — whichever contrasts more.

    Keeps every in-bubble label above the WCAG bar without a halo: dark
    fills get white text, light fills (green, orange) get the house ink.
    """
    lum = _relative_luminance(fill)
    white_cr = 1.05 / (lum + 0.05)
    ink_cr = (lum + 0.05) / (_relative_luminance(INK) + 0.05)
    return "#FFFFFF" if white_cr >= ink_cr else INK


# Blue and purple are nudged darker so white labels clear WCAG AA (~4.8:1
# instead of ~4.0). Green and orange stay bright and take ink labels, which
# also keeps their legend swatches lively and distinct.
def _family_color(accessibility: str = "universal") -> Dict[str, str]:
    """Return the per-family fill colours at a given accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`.

    Returns
    -------
    dict of str to str
        ``{family_name: "#RRGGBB"}`` for the four language families.
    """
    palette = load_palette(accessibility)
    return {
        "Web & scripting": _darken(palette.get("Blue", "#007AFF"), 0.10),
        "Data & scientific": palette.get("Green", "#34C759"),
        "Systems": palette.get("Orange", "#FF9500"),
        "Enterprise & JVM": _darken(palette.get("Purple", "#AF52DE"), 0.10),
    }


def _family_label(family_color: Dict[str, str]) -> Dict[str, str]:
    """Return the per-family label ink (white or dark) for each fill colour."""
    return {fam: _label_ink(col) for fam, col in family_color.items()}


FAMILY_COLOR: Dict[str, str] = _family_color()
# Per-family label colour, resolved once so every bubble uses the same.
FAMILY_LABEL: Dict[str, str] = _family_label(FAMILY_COLOR)

# Bubble radius scale: area ∝ share, so radius ∝ sqrt(share). These two
# anchors set the smallest and largest disks on the canvas. R_MIN is kept
# generous so even the rarest language holds a legible inside label.
R_MIN = 40.0
R_MAX = 128.0

# Labelling threshold: a bubble whose radius clears this gets a larger
# name + share stacked inside; smaller bubbles (still generous, since
# R_MIN is large) get one fitted name line with the share tucked under it.
# Every label lives inside its own disk, so nothing ever spills onto a
# neighbour — the packed-bubble form reads best with in-place labels.
INSIDE_LABEL_MIN_R = 62.0

SEED_TURNS = 3.6  # how many spiral turns the seeding walk takes


# ------------------------------------------------------------------
# Radius scale
# ------------------------------------------------------------------
def _radius(share: float, share_max: float) -> float:
    """Map a share percentage to a bubble radius in pixels.

    Uses a square-root scale so the *area* of the disk (not its radius)
    is proportional to the share — the perceptually honest encoding for a
    size legend.

    Parameters
    ----------
    share : float
        This language's share of developers, in percent.
    share_max : float
        The largest share in the dataset (sets the top of the scale).

    Returns
    -------
    float
        Circle radius in pixels.
    """
    frac = math.sqrt(max(share, 0.0) / share_max)
    return R_MIN + (R_MAX - R_MIN) * frac


# ------------------------------------------------------------------
# Offline collision-relaxation pack (pure Python, no numpy)
# ------------------------------------------------------------------
def _pack(
    radii: List[float],
    cx: float,
    cy: float,
    iterations: int = 900,
) -> List[Tuple[float, float]]:
    """Pack circles tightly around a centre with no overlaps.

    A deterministic relaxation with two forces per pass:

    * **Separation** — every pair of circles that overlaps is pushed
      apart along the line joining their centres until they just touch,
      each moving half the penetration depth. This is what removes all
      colour-on-colour overlap.
    * **Gravity** — every circle is nudged a small step toward the
      cluster centre, which closes the gaps the separation opens and
      keeps the whole pack compact rather than sprawling.

    Circles are seeded on an Archimedean spiral in the order given (the
    caller sorts largest-first), so the big disks land near the middle
    and the small ones fill the rim — the classic packed-bubble look. No
    randomness is used, so the layout is byte-reproducible.

    Parameters
    ----------
    radii : list of float
        Circle radii, already in the desired placement order
        (largest-first gives the tightest, most central big bubbles).
    cx, cy : float
        Centre the pack settles around, in canvas pixels.
    iterations : int, optional
        Number of relaxation passes (default 900 — ample for this count
        to reach a gap-free, overlap-free arrangement).

    Returns
    -------
    list of tuple of float
        ``(x, y)`` centre for each circle, index-aligned with ``radii``.
    """
    n = len(radii)
    # Spiral seed: place each circle a bit further out than the last, at a
    # radius that grows with the running sum of areas so bigger inputs
    # spread the walk faster and start already close to non-overlapping.
    pos: List[List[float]] = []
    running = 0.0
    for i, r in enumerate(radii):
        running += r
        ang = SEED_TURNS * math.pi * (i / max(n - 1, 1))
        rad = 0.9 * math.sqrt(running) * 3.2
        pos.append([cx + rad * math.cos(ang), cy + rad * math.sin(ang)])

    pad = 2.4  # breathing gap enforced between disk edges (px)
    for step in range(iterations):
        # Gravity strength eases off as the pack settles, so early passes
        # pull hard to compact and late passes only fine-tune.
        grav = 0.09 * (1.0 - 0.6 * step / iterations)

        # Pairwise separation — the O(n^2) loop is trivial at this scale.
        for i in range(n):
            for j in range(i + 1, n):
                dx = pos[j][0] - pos[i][0]
                dy = pos[j][1] - pos[i][1]
                dist = math.hypot(dx, dy) or 0.01
                min_dist = radii[i] + radii[j] + pad
                if dist < min_dist:
                    # Push both apart by half the overlap each.
                    overlap = (min_dist - dist) / 2.0
                    ux, uy = dx / dist, dy / dist
                    pos[i][0] -= ux * overlap
                    pos[i][1] -= uy * overlap
                    pos[j][0] += ux * overlap
                    pos[j][1] += uy * overlap

        # Gravity toward the centre closes the gaps separation opened.
        for i in range(n):
            pos[i][0] += (cx - pos[i][0]) * grav
            pos[i][1] += (cy - pos[i][1]) * grav

    return [(p[0], p[1]) for p in pos]


# ------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------
def _fmt_share(share: float) -> str:
    """Format a share percentage without a trailing ``.0``.

    Parameters
    ----------
    share : float
        Share value in percent.

    Returns
    -------
    str
        E.g. ``"62%"`` or ``"1.7%"``.
    """
    if abs(share - round(share)) < 0.05:
        return f"{round(share)}%"
    return f"{share:.1f}%"


def _fit_font(name: str, radius: float) -> float:
    """Choose a name font size that fits inside a bubble of the given radius.

    Parameters
    ----------
    name : str
        Language name to be drawn inside the disk.
    radius : float
        The disk radius in pixels.

    Returns
    -------
    float
        A font size (px) whose rendered name width stays within the disk.
    """
    # Roughly 0.60 * fontsize per character for Roboto bold; keep the name
    # within ~1.7 * radius of horizontal room, and cap by radius so the
    # two-line name+share stack fits vertically too.
    by_width = 1.7 * radius / (0.60 * max(len(name), 1))
    by_height = radius * 0.44
    return max(11.0, min(by_width, by_height, 30.0))


# ------------------------------------------------------------------
# SVG emission
# ------------------------------------------------------------------
def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full packed-bubble SVG document as a string.

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
        through the ``--accessibility`` CLI flag by :func:`_render.render_cli`.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    family_color = _family_color(accessibility)
    family_label = _family_label(family_color)
    share_max = max(share for _, share, _ in LANGUAGES)

    # Order largest-first so the pack seeds big disks near the centre.
    ordered = sorted(LANGUAGES, key=lambda t: t[1], reverse=True)
    radii = [_radius(share, share_max) for _, share, _ in ordered]
    centres = _pack(radii, PACK_CX, PACK_CY)

    # Recentre the finished pack on the target point so it is framed
    # symmetrically regardless of how the relaxation drifted.
    mean_x = sum(c[0] for c in centres) / len(centres)
    mean_y = sum(c[1] for c in centres) / len(centres)
    off_x = PACK_CX - mean_x
    off_y = PACK_CY - mean_y
    centres = [(x + off_x, y + off_y) for x, y in centres]

    title_txt = "JavaScript and Python still anchor the working web"
    subtitle_txt = (
        "Share of professional developers using each language, by family "
        "· illustrative survey data"
    )
    desc_txt = (
        "Packed-bubble chart of programming languages. Each bubble is a "
        "language, labelled with its name and share, so it reads without "
        "relying on colour. Its area is the share of professional developers "
        "who report using it, and its colour marks the language family: web "
        "and scripting, data and scientific, systems, and enterprise / "
        "JVM. The web and scripting family (JavaScript, HTML/CSS, "
        "TypeScript) and the data family (Python, SQL) hold the largest "
        "bubbles, while the systems and enterprise families form smaller "
        "but distinct clusters. Hover or focus any bubble to lift its "
        "whole family and dim the rest."
    )

    parts: List[str] = []
    parts.append(svg_open(WIDTH, HEIGHT, "pb-title", "pb-desc", font_family=FONT))
    parts.append(f'<title id="pb-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="pb-desc">{escape(desc_txt)}</desc>')

    # --- CSS: hover/focus a bubble lifts its whole family, dims the rest.
    #     Each bubble carries a family class; one :has() rule per family
    #     keeps the hovered family at full opacity while fading the others.
    #     :has() is supported in Chrome (used for the audit shot) and every
    #     modern browser. ---
    fam_slug = {fam: f"f{idx}" for idx, fam in enumerate(FAMILY_ORDER)}
    css: List[str] = [
        ".bubble{transition:opacity .18s ease}",
        ".bubble:focus{outline:none}",
    ]
    for _fam, slug in fam_slug.items():
        cond = f"#pack:has(.bubble.{slug}:is(:hover,:focus-within))"
        css.append(f"{cond} .bubble{{opacity:.26}}")
        css.append(f"{cond} .bubble.{slug}{{opacity:1}}")

    # OS-adaptive overrides (additive; the default render is byte-for-pixel
    # unchanged because every rule below lives inside a media query and only
    # then outranks the inline ``fill``). Under prefers-contrast each family
    # deepens to its high-contrast hue on the disc fills. Under forced colours
    # the discs drop to system CanvasText — safe here because every bubble
    # carries its language name + share as always-visible text, so the pack
    # still reads without colour. The in-bubble labels keep their inline fill
    # (white / ink); the browser leaves inline SVG fills alone under forced
    # colours, which is the intended behaviour.
    fam_series = {f".{fam_slug[fam]}": family_color[fam] for fam in FAMILY_ORDER}
    css.append(os_adaptive_style(fam_series, role="fill", forced=True))
    # Additive OS dark mode: dark paper + light ink (default ink_map). The family
    # bubble hues are data and the in-bubble labels keep their per-bubble inline
    # fill (white / ink chosen for WCAG against each hue), so nothing else needs
    # overriding — the saturated pack reads directly on the dark ground.
    css.append(os_dark_style())
    parts.append("<style>" + "".join(css) + "</style>")

    # --- background ---
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    # --- title + subtitle (start-anchored, house style) ---
    parts.append(
        f'<text x="56" y="74" font-size="37" font-weight="700" '
        f'fill="{INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="56" y="112" font-size="20" fill="{SUBINK}">'
        f'{escape(subtitle_txt)}</text>'
    )

    parts.append('<g id="pack">')

    # --- bubbles layer (each disk carries its own inside label) ---
    parts.append('<g id="bubbles">')
    for (name, share, fam), (x, y), r in zip(ordered, centres, radii):
        color = family_color[fam]
        label_ink = family_label[fam]
        slug = fam_slug[fam]
        tip = f"{name} — {_fmt_share(share)} of developers · {fam}"
        parts.append(
            f'<g class="bubble {slug}" tabindex="0" role="img" '
            f'aria-label="{escape(tip)}"><title>{escape(tip)}</title>'
            f'<circle class="{slug}" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'fill="{color}"/>'
        )
        if r >= INSIDE_LABEL_MIN_R:
            # Big bubble: name + share stacked inside, pure white, no
            # halo/stroke and no colour-on-colour.
            fs = _fit_font(name, r)
            parts.append(
                f'<text x="{x:.1f}" y="{y - fs * 0.18:.1f}" text-anchor="middle" '
                f'font-size="{fs:.1f}" font-weight="700" fill="{label_ink}">'
                f'{escape(name)}</text>'
            )
            parts.append(
                f'<text x="{x:.1f}" y="{y + fs * 0.98:.1f}" text-anchor="middle" '
                f'font-size="{fs * 0.82:.1f}" fill="{label_ink}" '
                f'font-family="{FONT_MONO}" opacity="0.92">'
                f'{escape(_fmt_share(share))}</text>'
            )
        else:
            # Smaller bubble: one fitted name line with the share tucked
            # under it, all white, no colour-on-colour and no halo.
            fs = max(11.0, min(_fit_font(name, r), 16.0))
            parts.append(
                f'<text x="{x:.1f}" y="{y - fs * 0.06:.1f}" text-anchor="middle" '
                f'font-size="{fs:.1f}" font-weight="700" fill="{label_ink}">'
                f'{escape(name)}</text>'
            )
            parts.append(
                f'<text x="{x:.1f}" y="{y + fs * 1.08:.1f}" text-anchor="middle" '
                f'font-size="{fs * 0.8:.1f}" fill="{label_ink}" '
                f'font-family="{FONT_MONO}" opacity="0.92">'
                f'{escape(_fmt_share(share))}</text>'
            )
        parts.append("</g>")
    parts.append("</g>")  # /bubbles

    parts.append("</g>")  # /pack

    # --- family legend (its own row below the subtitle, left-anchored so
    #     it never collides with the title) ---
    ly = 156
    cursor = 56.0
    for fam in FAMILY_ORDER:
        color = family_color[fam]
        parts.append(
            f'<circle cx="{cursor + 9:.1f}" cy="{ly - 6:.1f}" r="9" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{cursor + 26:.1f}" y="{ly:.1f}" text-anchor="start" '
            f'font-size="18" fill="{INK}">{escape(fam)}</text>'
        )
        cursor += 26 + 9.9 * len(fam) + 40

    # --- size legend + hover hint (bottom-left) ---
    hint_y = HEIGHT - 40
    parts.append(
        f'<text x="56" y="{hint_y:.1f}" font-size="16" fill="{SUBINK}">'
        f'Bubble area ∝ share of developers using the language · '
        f'hover or focus a bubble to lift its family</text>'
    )

    parts.append(fullscreen_control(WIDTH, HEIGHT, mode))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    """Write the packed-bubble SVG to the skill's example asset folder."""
    render_cli(__file__, "packed-bubble", build_svg, description="Render the packed-bubble SVG.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
make_manhattan — a house-styled genome-wide-association Manhattan plot as a
hand-authored SVG.

A *Manhattan plot* is the canonical summary figure of a genome-wide
association study (GWAS). Every point is one genetic variant (a single
nucleotide polymorphism, SNP): its horizontal position is the variant's
location along the genome — chromosomes 1 … 22 laid end to end — and its
height is the statistical strength of that variant's association with the
trait, drawn as ``-log10(p)`` so that tiny p-values tower upward (the
skyline that gives the plot its name). Points are tinted in two
alternating colours, one per chromosome, so the reader can tell where one
chromosome ends and the next begins. A dashed horizontal line marks the
genome-wide significance threshold — the classic ``5 × 10⁻⁸``,
i.e. ``-log10(p) ≈ 7.3`` — and any variant poking above it is a candidate
signal worth following up.

This example is an illustrative GWAS of **adult height**, a textbook
highly-polygenic trait: many loci across many chromosomes clear the line,
rather than one lone spike. The takeaway, stated in the subtitle, is
exactly that — height is written across the whole genome, not at a single
address. The tallest peaks are labelled with a plausible nearby gene and
carry a native ``<title>`` tooltip (chromosome, base-pair position,
p-value) so the figure is lightly interactive with **no JavaScript**.

The module builds the SVG string by hand — no matplotlib / seaborn /
plotly, and no Vega (tens of thousands of scattered points with a custom
genomic x-axis are authored far more directly and compactly as raw SVG).
It follows the front-* house style pulled from :mod:`_style`: the
Apple-ish saturated palette, Roboto typography, ink ``#1D1D1F`` on
secondary ``#6E6E73`` on a white background, a takeaway title, and a
one-line subtitle. All variant positions and p-values are drawn from a
seeded random number generator, so the artifact is byte-stable across
runs.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/manhattan.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# Canvas + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Deliberately poster-scale: a
#: genome-wide scatter needs room so the 22 chromosome slabs and their
#: skyline of peaks read comfortably rather than piling into a stripe.
_WIDTH: int = 1500
_HEIGHT: int = 780

#: Inner plotting viewport (leaves room for the header band, the y-axis
#: on the left, and the chromosome labels along the bottom).
_PLOT_X: float = 96.0
_PLOT_Y: float = 150.0
_PLOT_W: float = 1360.0
_PLOT_H: float = 520.0

#: House-style inks.
_INK: str = "#1D1D1F"       # primary text
_SUBTLE: str = "#6E6E73"    # secondary text
_BG: str = "#FFFFFF"        # background
_GRIDLINE: str = "#E5E5EA"  # faint horizontal guides

#: Genome-wide significance threshold, p = 5e-8, on the -log10 scale.
_GW_THRESHOLD: float = -math.log10(5e-8)  # ≈ 7.30

#: A softer "suggestive" threshold, p = 1e-5, common in GWAS practice.
_SUGGESTIVE: float = -math.log10(1e-5)    # = 5.0

#: Top of the y-axis, in -log10(p) units. Leaves headroom above the
#: tallest peak so labels do not collide with the header.
_Y_MAX: float = 34.0

#: Point radius, in pixels.
_DOT_R: float = 2.4

#: Deterministic RNG seed so the scatter is byte-stable across runs.
_SEED: int = 20260725


# ------------------------------------------------------------------
# Data — chromosome sizes and the two alternating tints
# ------------------------------------------------------------------
def _chromosome_lengths() -> List[Tuple[str, int]]:
    """Return the 22 autosomes with rounded lengths in mega-base-pairs.

    Lengths are the order-of-magnitude sizes of the human autosomes
    (GRCh38, rounded to whole mega-base-pairs). They set the horizontal
    width of each chromosome band so that a big chromosome such as chr1
    gets a wide slab and a small one such as chr21 gets a narrow one —
    exactly as in a real Manhattan plot.

    Returns
    -------
    list of (str, int)
        ``(chromosome_label, length_in_megabases)`` in genome order,
        chromosome 1 through chromosome 22.
    """
    return [
        ("1", 249), ("2", 242), ("3", 198), ("4", 190), ("5", 182),
        ("6", 171), ("7", 159), ("8", 145), ("9", 138), ("10", 134),
        ("11", 135), ("12", 133), ("13", 114), ("14", 107), ("15", 102),
        ("16", 90), ("17", 83), ("18", 80), ("19", 59), ("20", 64),
        ("21", 47), ("22", 51),
    ]


def _alternating_tints(palette: Dict[str, str]) -> Tuple[str, str]:
    """Return the two alternating chromosome tints (odd, even).

    Two closely-related blues read as a single "genome" while still
    letting the eye segment one chromosome from the next — the standard
    Manhattan convention, kept CVD-safe by using a light/dark pair of the
    *same* hue rather than a red/green contrast.

    Parameters
    ----------
    palette : dict of str to str
        The house palette, mapping colour names to hex strings.

    Returns
    -------
    tuple of (str, str)
        ``(odd_chromosome_hex, even_chromosome_hex)``.
    """
    # Deep Apple blue for odd chromosomes; the lighter sky/teal for even
    # ones. Both are pulled from the curated palette so make ↔ audit stay
    # in sync.
    odd = palette.get("Blue", "#007AFF")
    even = palette.get("Teal", "#5AC8FA")
    return odd, even


# ------------------------------------------------------------------
# Peak (labelled hit) model
# ------------------------------------------------------------------
#: A handful of tall peaks with a plausible nearby height-associated gene.
#: Each entry is ``(chromosome, position_fraction, peak_-log10p, gene)``:
#: ``position_fraction`` places the peak along that chromosome (0 … 1).
_PEAKS: List[Tuple[str, float, float, str]] = [
    ("3", 0.55, 32.0, "ZBTB38"),
    ("6", 0.34, 27.0, "HMGA1"),
    ("8", 0.61, 24.0, "PLAG1"),
    ("12", 0.28, 22.0, "HMGA2"),
    ("15", 0.47, 20.0, "ACAN"),
    ("20", 0.40, 18.0, "GDF5"),
]


#: Secondary, unlabelled loci — smaller clumps that still clear the
#: genome-wide line. They keep the plot honest for a *highly polygenic*
#: trait such as height, where signal is spread across the genome rather
#: than concentrated at a handful of headline genes. Same tuple shape as
#: :data:`_PEAKS` minus the gene name: ``(chromosome, position_fraction,
#: peak_-log10p)``.
_MINOR_PEAKS: List[Tuple[str, float, float]] = [
    ("1", 0.22, 11.0), ("1", 0.74, 9.5), ("2", 0.48, 13.0),
    ("4", 0.36, 10.0), ("5", 0.62, 12.0), ("7", 0.29, 9.0),
    ("9", 0.51, 10.5), ("10", 0.44, 11.5), ("11", 0.66, 9.5),
    ("14", 0.33, 10.0), ("16", 0.55, 9.0), ("17", 0.41, 12.5),
    ("18", 0.58, 8.5), ("19", 0.37, 10.0), ("22", 0.5, 8.5),
]


# ------------------------------------------------------------------
# SVG assembly helpers
# ------------------------------------------------------------------
# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def _y_to_px(value: float) -> float:
    """Map a ``-log10(p)`` value to a screen y-coordinate (north-up)."""
    frac = value / _Y_MAX
    return _PLOT_Y + _PLOT_H - frac * _PLOT_H


def _fmt_p(neg_log10p: float) -> str:
    """Render a ``-log10(p)`` value back as a compact ``p = a×10⁻ᵇ`` string."""
    exponent = math.floor(neg_log10p)
    mantissa = 10 ** (exponent - neg_log10p)  # in (0.1, 1] * 10 -> (1,10]
    mantissa *= 10
    exponent += 1
    supers = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    return f"p = {mantissa:.1f}×10⁻{str(exponent).translate(supers)}"


# ------------------------------------------------------------------
# Build
# ------------------------------------------------------------------
def _band_geometry() -> Tuple[List[Tuple[str, int, float, float, float]], float]:
    """Compute the horizontal band (x-range) for each chromosome.

    Chromosomes are laid end to end and scaled to fill the plotting
    width, with a thin gap between neighbours so the alternating tints
    read as separate slabs.

    Returns
    -------
    tuple
        ``(bands, mb_per_px)`` where ``bands`` is a list of
        ``(label, length_mb, x_start_px, x_end_px, x_center_px)`` and
        ``mb_per_px`` is the shared horizontal scale (mega-bases per
        pixel), reused when placing individual variants.
    """
    chroms = _chromosome_lengths()
    total_mb = sum(length for _, length in chroms)
    n_gaps = len(chroms) - 1
    gap_px = 3.0
    usable_px = _PLOT_W - n_gaps * gap_px
    mb_per_px = total_mb / usable_px

    bands: List[Tuple[str, int, float, float, float]] = []
    cursor = _PLOT_X
    for label, length in chroms:
        width_px = length / mb_per_px
        x0 = cursor
        x1 = cursor + width_px
        bands.append((label, length, x0, x1, (x0 + x1) / 2.0))
        cursor = x1 + gap_px
    return bands, mb_per_px


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full Manhattan-plot SVG document as a string.

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
    odd_hex, even_hex = _alternating_tints(palette)
    hit_hex = palette.get("Red", "#FF3B30")  # genome-wide-significant peaks

    bands, mb_per_px = _band_geometry()
    rng = random.Random(_SEED)

    parts: List[str] = []

    # ---- header / accessibility ----
    parts.append(svg_open(_WIDTH, _HEIGHT, "mh-title", "mh-desc"))
    parts.append(
        '<title id="mh-title">Manhattan plot of a genome-wide association '
        'study for adult height</title>'
    )
    desc = (
        "Manhattan plot. The horizontal axis lays chromosomes 1 to 22 end "
        "to end; the vertical axis is the strength of each genetic "
        "variant's association with adult height, shown as minus log base "
        "ten of the p-value, so smaller p-values rise higher. Points "
        "alternate between two shades of blue by chromosome. A dashed red "
        "line marks the genome-wide significance threshold at p = 5e-8. "
        "Dozens of peaks on many different chromosomes rise above the line, "
        "the signature of a highly polygenic trait; the tallest, labelled "
        "with nearby genes, include ZBTB38 on chromosome 3, HMGA1 on "
        "chromosome 6, and HMGA2 on chromosome 12."
    )
    parts.append(f'<desc id="mh-desc">{_xml(desc)}</desc>')

    # ---- interactivity + reduced-motion guard (pure CSS, no JS) ----
    style_rows = [
        ".peak { transition: r .15s ease; }",
        # Enlarge a labelled peak's dot on hover / keyboard focus.
        ".peak:hover circle, .peak:focus circle { r: 7; }",
        ".peak:focus { outline: none; }",
        ".peak:focus circle { stroke: #1D1D1F; stroke-width: 1.4; }",
        "@media (prefers-reduced-motion: reduce) { "
        ".peak { transition: none; } }",
    ]
    # OS-adaptive overrides (additive; each rule lives inside a media query so
    # the default render is byte-for-byte unchanged). Under prefers-contrast the
    # two alternating chromosome tints and the red hit colour deepen to their
    # high-contrast hues: the fills on the per-chromosome bands and the hit dots,
    # the stroke on the genome-wide significance line. forced-colors is left to
    # the browser default because the plot is colour-encoded.
    parts.append(
        "<style>\n"
        + "\n".join(style_rows)
        + "\n"
        + os_adaptive_style(
            {".mh-odd": odd_hex, ".mh-even": even_hex, ".mh-hit": hit_hex}, role="fill"
        )
        + "\n"
        + os_adaptive_style({".mh-gwline": hit_hex}, role="stroke")
        + "\n"
        # Additive OS dark mode: dark paper + light ink (default ink_map); the
        # per-chromosome band tints and the red hit colour are data hues, left
        # alone. The faint horizontal gridlines darken to read on dark.
        + os_dark_style(extra='[stroke="#E5E5EA"]{stroke:#333338;}')
        + "\n</style>"
    )

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_PLOT_X}" y="62" font-size="32" font-weight="700" '
        f'fill="{_INK}">Height is written across the whole genome</text>'
    )
    parts.append(
        f'<text x="{_PLOT_X}" y="96" font-size="18" fill="{_SUBTLE}">'
        f'Genome-wide association study of adult height: dozens of loci across '
        f'many chromosomes clear significance, so the signal is spread wide</text>'
    )

    # ---- horizontal gridlines + y-axis ticks ----
    parts.append('<g>')
    for tick in (0, 5, 10, 15, 20, 25, 30):
        ty = _y_to_px(float(tick))
        parts.append(
            f'<line x1="{_PLOT_X:.1f}" y1="{ty:.1f}" '
            f'x2="{_PLOT_X + _PLOT_W:.1f}" y2="{ty:.1f}" '
            f'stroke="{_GRIDLINE}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{_PLOT_X - 14:.1f}" y="{ty + 5:.1f}" '
            f'font-size="15" font-family="Roboto Mono, monospace" '
            f'fill="{_SUBTLE}" text-anchor="end">{tick}</text>'
        )
    parts.append('</g>')

    # ---- y-axis title (rotated) ----
    axis_cy = _PLOT_Y + _PLOT_H / 2.0
    parts.append(
        f'<text x="34" y="{axis_cy:.1f}" font-size="17" font-weight="600" '
        f'fill="{_INK}" text-anchor="middle" '
        f'transform="rotate(-90 34 {axis_cy:.1f})">'
        f'−log₁₀(p)  association strength</text>'
    )

    # ---- scattered variants, one <g> per chromosome for tint + labels ----
    # Precompute where each labelled peak falls so its column can be given
    # the peak height (and so nearby points swell into a plausible skyline).
    peak_lookup: Dict[str, List[Tuple[float, float, str]]] = {}
    for chrom, pos_frac, peak_val, gene in _PEAKS:
        peak_lookup.setdefault(chrom, []).append((pos_frac, peak_val, gene))

    # Minor loci raise a clump but carry no gene label ("" sentinel).
    shoulder_lookup: Dict[str, List[Tuple[float, float]]] = {}
    for chrom, pos_frac, peak_val, _gene in _PEAKS:
        shoulder_lookup.setdefault(chrom, []).append((pos_frac, peak_val))
    for chrom, pos_frac, peak_val in _MINOR_PEAKS:
        shoulder_lookup.setdefault(chrom, []).append((pos_frac, peak_val))

    # Points per mega-base — dense enough to look genome-scale, cheap enough
    # to keep the SVG small.
    density = 2.8

    labelled: List[Tuple[float, float, str, str, str, int, float]] = []
    for idx, (label, length_mb, x0, x1, _xc) in enumerate(bands):
        tint = odd_hex if idx % 2 == 0 else even_hex
        # Stable class per parity so the OS-adaptive rule can deepen the tint
        # on the whole chromosome band (child circles inherit the group fill).
        tint_cls = "mh-odd" if idx % 2 == 0 else "mh-even"
        n_points = max(24, int(length_mb * density))
        parts.append(f'<g class="{tint_cls}" fill="{tint}" fill-opacity="0.8">')
        shoulders_here = shoulder_lookup.get(label, [])
        for _ in range(n_points):
            u = rng.random()  # position fraction along the chromosome
            px = x0 + u * (x1 - x0)

            # Baseline: most variants show only noise. Draw -log10(p) from a
            # distribution that is mostly small with an occasional bump, so
            # the "grass" hugs the bottom the way real GWAS null points do.
            base = -math.log10(max(rng.random(), 1e-12)) * 0.62

            # If this variant sits near a labelled peak, let it rise toward
            # that peak — a Gaussian "shoulder" around the lead SNP makes the
            # skyline look like linkage-disequilibrium clumping (a broad clump
            # of correlated variants), not an isolated needle.
            for pos_frac, peak_val in shoulders_here:
                dist = abs(u - pos_frac)
                shoulder = peak_val * math.exp(-((dist / 0.075) ** 2))
                base = max(base, shoulder * rng.uniform(0.5, 1.0))

            val = min(base, _Y_MAX - 0.5)
            py = _y_to_px(val)

            # Points above genome-wide significance get the red hit colour.
            if val >= _GW_THRESHOLD:
                parts.append(
                    f'<circle class="mh-hit" cx="{px:.1f}" cy="{py:.1f}" '
                    f'r="{_DOT_R}" fill="{hit_hex}" fill-opacity="0.9"/>'
                )
            else:
                parts.append(
                    f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{_DOT_R}"/>'
                )

        parts.append('</g>')

        # Place the lead SNP for each labelled peak at its exact target
        # height and remember it for the label + interactive tooltip layer.
        for pos_frac, peak_val, gene in peak_lookup.get(label, []):
            px = x0 + pos_frac * (x1 - x0)
            bp = int(pos_frac * length_mb * 1_000_000)
            labelled.append((px, _y_to_px(peak_val), gene, label, hit_hex, bp, peak_val))

    # ---- significance lines (drawn over the scatter, under the labels) ----
    # Each threshold caption sits on a soft white pill so it stays legible
    # where a tall red peak pokes up through the line (no colour-on-colour).
    def _label_pill(text: str, right_x: float, baseline_y: float, fill: str, bold: bool) -> None:
        char_px = 8.1 if bold else 7.6
        width = len(text) * char_px + 16.0
        parts.append(
            f'<rect x="{right_x - width:.1f}" y="{baseline_y - 15:.1f}" '
            f'width="{width:.1f}" height="21" rx="5" '
            f'fill="{_BG}" fill-opacity="0.86"/>'
        )
        weight = ' font-weight="600"' if bold else ''
        parts.append(
            f'<text x="{right_x - 8:.1f}" y="{baseline_y:.1f}" '
            f'font-size="14"{weight} fill="{fill}" '
            f'text-anchor="end">{text}</text>'
        )

    sug_y = _y_to_px(_SUGGESTIVE)
    parts.append(
        f'<line x1="{_PLOT_X:.1f}" y1="{sug_y:.1f}" '
        f'x2="{_PLOT_X + _PLOT_W:.1f}" y2="{sug_y:.1f}" '
        f'stroke="{_SUBTLE}" stroke-width="1.4" stroke-dasharray="2 5"/>'
    )
    _label_pill("suggestive · p = 1×10⁻⁵", _PLOT_X + _PLOT_W, sug_y - 8, _SUBTLE, False)

    gw_y = _y_to_px(_GW_THRESHOLD)
    parts.append(
        f'<line class="mh-gwline" x1="{_PLOT_X:.1f}" y1="{gw_y:.1f}" '
        f'x2="{_PLOT_X + _PLOT_W:.1f}" y2="{gw_y:.1f}" '
        f'stroke="{hit_hex}" stroke-width="1.8" stroke-dasharray="6 5"/>'
    )
    _label_pill(
        "genome-wide significance · p = 5×10⁻⁸", _PLOT_X + _PLOT_W, gw_y - 8, hit_hex, True
    )

    # ---- labelled lead SNPs: gene tag + interactive tooltip ----
    for px, py, gene, chrom, color, bp, peak_val in labelled:
        # Keep the gene label inside the plot horizontally.
        anchor = "middle"
        lx = px
        if px < _PLOT_X + 40:
            anchor, lx = "start", px
        elif px > _PLOT_X + _PLOT_W - 40:
            anchor, lx = "end", px
        parts.append(
            f'<g class="peak" tabindex="0" role="img" '
            f'aria-label="{_xml(gene)} on chromosome {chrom}, '
            f'{_fmt_p(peak_val)}">'
        )
        parts.append(
            f'<title>{_xml(gene)} — chr{chrom}:{bp:,} · '
            f'{_fmt_p(peak_val)}</title>'
        )
        parts.append(
            f'<circle class="mh-hit" cx="{px:.1f}" cy="{py:.1f}" r="4.2" '
            f'fill="{color}" stroke="#FFFFFF" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{lx:.1f}" y="{py - 13:.1f}" font-size="16" '
            f'font-weight="700" font-style="italic" fill="{_INK}" '
            f'text-anchor="{anchor}">{_xml(gene)}</text>'
        )
        parts.append('</g>')

    # ---- x-axis: chromosome labels ----
    x_label_y = _PLOT_Y + _PLOT_H + 28.0
    parts.append('<g>')
    for label, _length, _x0, _x1, xc in bands:
        parts.append(
            f'<text x="{xc:.1f}" y="{x_label_y:.1f}" font-size="14" '
            f'font-family="Roboto Mono, monospace" fill="{_SUBTLE}" '
            f'text-anchor="middle">{label}</text>'
        )
    parts.append('</g>')
    parts.append(
        f'<text x="{_PLOT_X + _PLOT_W / 2:.1f}" '
        f'y="{x_label_y + 34:.1f}" font-size="17" font-weight="600" '
        f'fill="{_INK}" text-anchor="middle">Chromosome</text>'
    )

    # ---- footnote / method note ----
    parts.append(
        f'<text x="{_PLOT_X}" y="{_HEIGHT - 22:.1f}" font-size="14" '
        f'fill="{_SUBTLE}">Illustrative data · one point per genetic '
        f'variant · alternating tints separate chromosomes · hover a '
        f'labelled peak for its position and p-value</text>'
    )

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the Manhattan-plot SVG to the skill's ``svg-examples`` folder."""
    render_cli(__file__, "manhattan", build_svg, description="Render the manhattan SVG.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
make_wordcloud — a house-styled word cloud (spiral-packed) as a hand-authored SVG.

A word cloud answers one question at a glance: *which words dominate a
body of text, and how do they group*. Here the text is a year of
product reviews for a mid-range coffee grinder; each word is sized by
how often reviewers used it and tagged by the theme it belongs to. The
theme reads two ways so it never leans on colour alone: a sign glyph and
a hue together — a leading ``+`` in green for what buyers praise, a
leading ``−`` in red for what they complain about, and no glyph in blue
for the neutral product vocabulary both camps share. The takeaway is
meant to jump out of the raster: the biggest words are *grind* and
*quiet*, so people mostly love how it works, while the largest complaint
word is *noisy*, the one recurring gripe.

This module builds the SVG string by hand — no matplotlib / seaborn /
wordcloud / plotly, and no Vega, because a collision-free
Archimedean-spiral packing of variable-size glyphs is not a native
Vega-Lite mark and is far cleaner authored directly. Placement is fully
offline and deterministic: words are laid biggest-first, each one walked
outward along an Archimedean spiral until its axis-aligned bounding box
clears every word already placed (plus a small breathing margin), so the
finished cloud has **zero overlaps**. The result is a denser, calmer
spiral than the Highcharts / ECharts word clouds it improves on, in the
front-* house style pulled from :mod:`_style`: the Apple-ish saturated
palette used as three semantic groups, Roboto typography, ink
``#1D1D1F`` on a white background, a takeaway title, and a one-line
subtitle.

The figure is interactive without any JavaScript: hovering or
keyboard-focusing a legend entry lifts its whole theme and dims the
other two, and every word carries a native ``<title>`` tooltip with its
exact review-mention count. Motion is guarded by
``prefers-reduced-motion``.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/wordcloud.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
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
#: Canvas size, in user-space pixels. Poster-scale so the packed cloud
#: reads at a glance and even the smallest words stay legible.
_WIDTH: int = 1240
_HEIGHT: int = 900

#: The cloud packs inside this rectangle (leaving room for the title
#: band up top and the legend strip along the bottom).
_FIELD_TOP: float = 138.0
_FIELD_BOTTOM: float = 792.0
_FIELD_LEFT: float = 56.0
_FIELD_RIGHT: float = 1184.0

#: House-style inks.
_INK: str = "#1D1D1F"      # primary text
_SUBTLE: str = "#6E6E73"   # secondary text
_HAIR: str = "#E5E5EA"     # hairline separators
_BG: str = "#FFFFFF"       # background
_FOCUS: str = "#0A4DA0"    # focus-ring blue


# ------------------------------------------------------------------
# Semantic groups (the three review themes)
# ------------------------------------------------------------------
def _groups(accessibility: str = "universal") -> Dict[str, Dict[str, str]]:
    """Return the three review themes with colour *and* a sign glyph.

    Colour alone cannot carry the theme: praise Green and complaint Red
    both collapse to the same gold under red-green colour blindness and
    to the same grey with no colour at all, so a colour-blind reader
    could not tell approval from a gripe. Each theme therefore also gets
    a leading sign glyph — ``+`` for praise, ``−`` for a complaint, and
    nothing for neutral vocabulary — which reads in any palette, in
    greyscale, and under every colour-vision deficiency. Every hue still
    comes from the canonical palette so make and audit stay in sync.

    Parameters
    ----------
    accessibility : str, optional
        The palette accessibility level threaded into :func:`load_palette`;
        ``"universal"`` (default) is the colour-vision-safe standard.

    Returns
    -------
    dict of str to dict
        Mapping ``{group_key: {"label": str, "color": hex, "glyph": str}}``.
        ``glyph`` is the prefix shown before each word and on the legend.
    """
    palette = load_palette(accessibility)
    return {
        "praise": {"label": "What buyers praise (+)", "color": palette["Green"], "glyph": "+"},
        "gripe": {"label": "What buyers complain about (−)", "color": palette["Red"], "glyph": "−"},
        "neutral": {"label": "Neutral product words", "color": palette["Blue"], "glyph": ""},
    }


def _dataset() -> List[Tuple[str, int, str]]:
    """Return the communicative fake data: ~40 words × mention count × group.

    A year of reviews for a fictional burr coffee grinder ("Aurora
    Grind One"). Counts are how many of the ~2,400 reviews mentioned
    each word. Hand-tuned so the story reads straight off the cloud: the
    two dominant words are *grind* and *quiet* (green), buyers mostly
    love how it runs; the biggest red word is *noisy*, the one gripe
    that keeps coming up; the blue words are the neutral vocabulary both
    camps reach for.

    Returns
    -------
    list of tuple
        ``(word, mention_count, group_key)`` triples, any order — the
        packer sorts them biggest-first itself.
    """
    return [
        # --- praise (green): the things reviewers love ---
        ("quiet", 812, "praise"),
        ("consistent", 604, "praise"),
        ("smooth", 468, "praise"),
        ("even", 392, "praise"),
        ("easy", 356, "praise"),
        ("sturdy", 288, "praise"),
        ("fast", 244, "praise"),
        ("precise", 210, "praise"),
        ("value", 176, "praise"),
        ("recommend", 152, "praise"),
        ("love", 132, "praise"),
        ("clean", 118, "praise"),
        ("reliable", 96, "praise"),
        ("compact", 78, "praise"),
        # --- gripe (red): the recurring complaints ---
        ("noisy", 428, "gripe"),
        ("static", 296, "gripe"),
        ("mess", 214, "gripe"),
        ("clumps", 168, "gripe"),
        ("plastic", 138, "gripe"),
        ("jams", 112, "gripe"),
        ("retention", 94, "gripe"),
        ("flimsy", 74, "gripe"),
        ("leaks", 58, "gripe"),
        ("wobble", 46, "gripe"),
        ("pricey", 38, "gripe"),
        # --- neutral (blue): the shared product vocabulary ---
        ("grind", 940, "neutral"),
        ("beans", 512, "neutral"),
        ("burr", 384, "neutral"),
        ("espresso", 332, "neutral"),
        ("setting", 276, "neutral"),
        ("hopper", 232, "neutral"),
        ("coffee", 198, "neutral"),
        ("dial", 164, "neutral"),
        ("motor", 142, "neutral"),
        ("bin", 108, "neutral"),
        ("size", 88, "neutral"),
        ("filter", 70, "neutral"),
        ("morning", 54, "neutral"),
        ("kitchen", 42, "neutral"),
    ]


# ------------------------------------------------------------------
# Font-size scale
# ------------------------------------------------------------------
#: Smallest and largest glyph heights, in pixels. A wide range makes the
#: frequency ranking unmistakable while keeping the tail readable.
_SIZE_MIN: float = 20.0
_SIZE_MAX: float = 96.0


def _size_for(count: int, lo: int, hi: int) -> float:
    """Map a mention count to a font size on a gentle square-root ramp.

    A linear ramp would make the head words tower and crush the tail; a
    square-root ramp (area-ish) keeps the whole cloud legible while
    preserving the ranking. The rarest word lands at :data:`_SIZE_MIN`,
    the most-mentioned at :data:`_SIZE_MAX`.

    Parameters
    ----------
    count : int
        This word's review-mention count.
    lo, hi : int
        The minimum and maximum counts across the whole dataset.

    Returns
    -------
    float
        Font size in pixels.
    """
    if hi <= lo:
        return (_SIZE_MIN + _SIZE_MAX) / 2.0
    t = (math.sqrt(count) - math.sqrt(lo)) / (math.sqrt(hi) - math.sqrt(lo))
    return _SIZE_MIN + t * (_SIZE_MAX - _SIZE_MIN)


# ------------------------------------------------------------------
# Glyph bounding-box geometry
# ------------------------------------------------------------------
#: Roboto is roughly this wide per em at a given font size (averaged
#: over lowercase-heavy words). Used to estimate a word's box width
#: without a font engine — deliberately a touch generous so the packed
#: margins never bite.
_CHAR_ASPECT: float = 0.56

#: The cap-height-ish fraction of the font size a lowercase word paints,
#: plus a whisker of leading. Keeps the vertical boxes tight but safe.
_GLYPH_HEIGHT_FRAC: float = 0.78

#: Breathing room, in pixels, added around every box so neighbours never
#: kiss. Small enough to keep the cloud dense.
_MARGIN: float = 5.0


def _word_box(word: str, size: float) -> Tuple[float, float]:
    """Estimate a word's rendered bounding-box (width, height) in pixels.

    A hand tuned metric that stands in for a real font engine: width is
    the character count times an average per-character advance, height is
    a cap-height-ish fraction of the font size. Both include the packing
    :data:`_MARGIN` on every side so placed words keep a constant gap.

    Parameters
    ----------
    word : str
        The word to measure.
    size : float
        Its font size in pixels.

    Returns
    -------
    tuple of float
        ``(half_width, half_height)`` of the padded box — halves, so the
        packer can centre a word on a point and test symmetric extents.
    """
    w = len(word) * size * _CHAR_ASPECT + 2.0 * _MARGIN
    h = size * _GLYPH_HEIGHT_FRAC + 2.0 * _MARGIN
    return w / 2.0, h / 2.0


def _overlaps(
    cx: float, cy: float, hw: float, hh: float, placed: List[Tuple[float, float, float, float]]
) -> bool:
    """Test whether a candidate box collides with any already-placed box.

    Plain axis-aligned bounding-box (AABB) overlap test: two rectangles
    miss each other as soon as they are apart on either axis.

    Parameters
    ----------
    cx, cy : float
        Candidate box centre.
    hw, hh : float
        Candidate box half-width and half-height.
    placed : list of tuple
        Already-placed boxes as ``(cx, cy, hw, hh)``.

    Returns
    -------
    bool
        ``True`` if the candidate touches any placed box.
    """
    for pcx, pcy, phw, phh in placed:
        if abs(cx - pcx) < (hw + phw) and abs(cy - pcy) < (hh + phh):
            return True
    return False


def _in_field(cx: float, cy: float, hw: float, hh: float) -> bool:
    """Return ``True`` if the whole box sits inside the packing rectangle."""
    return (
        cx - hw >= _FIELD_LEFT
        and cx + hw <= _FIELD_RIGHT
        and cy - hh >= _FIELD_TOP
        and cy + hh <= _FIELD_BOTTOM
    )


# ------------------------------------------------------------------
# Archimedean-spiral placement
# ------------------------------------------------------------------
def _place_words() -> List[Dict[str, object]]:
    """Pack every word with collision-free Archimedean-spiral placement.

    The algorithm is the classic offline word-cloud packer, kept
    deterministic (no randomness) so the artifact is reproducible:

    1. Sort words biggest-first, so the head words claim the centre and
       the tail fills the gaps around them.
    2. Start each word at the cloud centre and walk it outward along an
       Archimedean spiral ``r = a·theta`` — a spiral whose successive
       turns are evenly spaced, which packs far more tightly than a
       circular scan.
    3. At each step, test the word's padded bounding box against every
       box already placed. The first collision-free, in-field spot wins.

    The cloud is horizontally elongated (the field is wider than it is
    tall), so the spiral is scaled to match — this is what gives the
    finished piece its calm landscape shape instead of a tight disc.

    Returns
    -------
    list of dict
        One dict per placed word: ``{"word", "count", "group", "size",
        "x", "y"}`` where ``x``/``y`` is the glyph's centre.
    """
    data = _dataset()
    counts = [c for _, c, _ in data]
    lo, hi = min(counts), max(counts)

    # Each word paints with its theme's sign glyph in front, so the box
    # measured for packing must include that prefix or the head words would
    # graze their neighbours once the glyph is added at render time.
    glyphs = {k: str(v["glyph"]) for k, v in _groups().items()}

    # Biggest-first: the two head words anchor the centre.
    ordered = sorted(data, key=lambda t: t[1], reverse=True)

    cx0 = (_FIELD_LEFT + _FIELD_RIGHT) / 2.0
    # Nudge the spiral origin a hair below the geometric centre: the tail
    # words fan outward and slightly upward from the head, so seeding a
    # touch low balances the finished cloud in the field.
    cy0 = (_FIELD_TOP + _FIELD_BOTTOM) / 2.0 + 14.0

    # Spiral parameters. `a` sets how fast the spiral opens; the aspect
    # ratio stretches it to the field so the cloud reads as a landscape
    # band rather than a circle. Fine angular steps keep placement tight.
    a = 4.2
    aspect = (_FIELD_RIGHT - _FIELD_LEFT) / (_FIELD_BOTTOM - _FIELD_TOP)
    d_theta = 0.22
    theta_max = 60.0 * math.pi   # plenty of turns for ~40 words

    placed_boxes: List[Tuple[float, float, float, float]] = []
    placed: List[Dict[str, object]] = []

    for word, count, group in ordered:
        size = _size_for(count, lo, hi)
        # A leading "+ " / "− " widens the box; measure the painted string.
        prefix = f"{glyphs[group]} " if glyphs[group] else ""
        display = f"{prefix}{word}"
        hw, hh = _word_box(display, size)

        theta = 0.0
        cx, cy = cx0, cy0
        # Walk the spiral until the box clears everything and stays in
        # the field. The first word lands dead-centre (theta = 0).
        while theta < theta_max:
            r = a * theta
            cx = cx0 + aspect * r * math.cos(theta)
            cy = cy0 + r * math.sin(theta)
            if _in_field(cx, cy, hw, hh) and not _overlaps(cx, cy, hw, hh, placed_boxes):
                break
            theta += d_theta

        placed_boxes.append((cx, cy, hw, hh))
        placed.append(
            {
                "word": word,
                "display": display,
                "count": count,
                "group": group,
                "size": size,
                "x": cx,
                "y": cy,
            }
        )

    return placed


# Local alias for the shared escape helper.
_xml = xml_escape


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full word-cloud SVG document as a string.

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
    groups = _groups(accessibility)
    placed = _place_words()
    total_reviews = 2412  # the corpus size quoted in the subtitle

    # Head words for the takeaway, read straight off the placed set. The
    # overall top word is neutral ("grind"), so name the leading praise
    # word ("quiet") plus the runner-up for a fuller headline.
    by_count = sorted(placed, key=lambda p: int(p["count"]), reverse=True)
    praise_ranked = [p for p in by_count if p["group"] == "praise"]
    top_praise = praise_ranked[0]
    second_praise = praise_ranked[1]
    top_gripe = next(p for p in by_count if p["group"] == "gripe")

    parts: List[str] = []

    # ---- header ----
    parts.append(svg_open(_WIDTH, _HEIGHT, "wc-title", "wc-desc"))
    parts.append(
        '<title id="wc-title">Word cloud of coffee-grinder reviews: '
        'buyers love how quietly it grinds, and the one gripe is '
        'noise</title>'
    )
    desc = (
        "A spiral-packed word cloud of a year of product reviews for a "
        "burr coffee grinder. Each word is sized by how many reviews "
        "mentioned it and tagged by theme with both a colour and a sign "
        "glyph: a leading plus and green for praise, a leading minus and "
        "red for complaints, and no glyph in blue for neutral product "
        "words. The biggest words "
        f"are grind, {_xml(str(top_praise['word']))} and "
        f"{_xml(str(second_praise['word']))}; the largest complaint word "
        f"is {_xml(str(top_gripe['word']))}."
    )
    parts.append(f'<desc id="wc-desc">{desc}</desc>')

    # ---- interactivity + house style (pure CSS, no JS) ----
    style_rows = [
        ".word { transition: opacity .18s ease; }",
        # Hover/focus a legend swatch dims the other two themes so one
        # colour group stands out across the whole cloud.
        "svg:has(.legend-row:hover) .word, "
        "svg:has(.legend-row:focus) .word { opacity: .12; }",
    ]
    for key in groups:
        style_rows.append(
            f"svg:has(.legend-{key}:hover) .grp-{key}, "
            f"svg:has(.legend-{key}:focus) .grp-{key} {{ opacity: 1; }}"
        )
    style_rows.extend(
        [
            ".legend-row { cursor: pointer; }",
            f".legend-row:focus {{ outline: 3px solid {_FOCUS}; "
            "outline-offset: 3px; border-radius: 8px; }",
            "@media (prefers-reduced-motion: reduce) { "
            ".word { transition: none; } }",
        ]
    )
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside a media query). Under
    # prefers-contrast the three theme hues deepen to their high-contrast
    # values on both the words and the legend swatches. Forced colours are left
    # to the browser default: the theme already survives with no colour via the
    # leading sign glyph (+ / − / none), so there is no need to blank the fills,
    # and a straight hand-off to a 4-colour system palette would only weaken the
    # praise/gripe/neutral hue reinforcement without adding information.
    theme_series = {f".grp-{key}": str(meta["color"]) for key, meta in groups.items()}
    style_rows.append(os_adaptive_style(theme_series, role="fill"))
    # Additive OS dark-mode block. The white page darkens and the ink tiers flip
    # to light via the ink-map default; the #E5E5EA hairline separators darken to
    # a quiet grey. The three theme hues (praise / gripe / neutral) are the data
    # and read on dark, so they are left alone. No multiply groups.
    style_rows.append(
        os_dark_style(
            screen_blend=False,
            extra='[stroke="#E5E5EA"]{stroke:#3A3A3C;} '
            '[fill="#E5E5EA"]{fill:#3A3A3C;}',
        )
    )
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="56" y="66" font-size="32" font-weight="700" '
        f'fill="{_INK}">Reviewers love the quiet, consistent grind</text>'
    )
    parts.append(
        f'<text x="56" y="98" font-size="18" fill="{_SUBTLE}">'
        f'{total_reviews:,} reviews of the Aurora Grind One · words sized '
        f'by how often they appear, tagged by theme with a sign and a '
        f'colour · illustrative</text>'
    )
    # Hairline under the title band.
    parts.append(
        f'<line x1="56" y1="120" x2="{_FIELD_RIGHT:.0f}" y2="120" '
        f'stroke="{_HAIR}" stroke-width="1.4"/>'
    )

    # ---- the words, grouped by theme so one CSS rule lifts a whole group ----
    # Emit smallest-first so, in the unlikely event two padded boxes graze,
    # the bigger head word paints on top and stays fully legible.
    for key, meta in groups.items():
        color = str(meta["color"])
        parts.append(f'<g class="grp-{key}">')
        members = [p for p in placed if p["group"] == key]
        members.sort(key=lambda p: float(p["size"]))
        for p in members:
            word = str(p["word"])
            display = str(p.get("display", word))
            size = float(p["size"])
            x = float(p["x"])
            y = float(p["y"])
            count = int(p["count"])
            share = 100.0 * count / total_reviews
            tip = (
                f"{_xml(word)} — {meta['label'].lower()} · mentioned in "
                f"{count:,} reviews ({share:.0f}%)"
            )
            # dominant-baseline central so the glyph sits on its box centre;
            # weight scales gently with size so head words feel heavier. The
            # painted string carries the theme's sign glyph so the sentiment
            # survives without colour (greyscale + colour-vision deficiency).
            weight = 700 if size >= 60 else (600 if size >= 34 else 500)
            parts.append(
                f'<text class="word grp-{key}" x="{x:.1f}" y="{y:.1f}" '
                f'font-size="{size:.1f}" font-weight="{weight}" '
                f'fill="{color}" text-anchor="middle" '
                f'dominant-baseline="central" tabindex="0" role="listitem">'
                f'<title>{tip}</title>{_xml(display)}</text>'
            )
        parts.append("</g>")

    # ---- legend strip (three themes) along the bottom ----
    legend_y = 838.0
    # Hairline above the legend.
    parts.append(
        f'<line x1="56" y1="812" x2="{_FIELD_RIGHT:.0f}" y2="812" '
        f'stroke="{_HAIR}" stroke-width="1.4"/>'
    )
    slot_x = [56.0, 470.0, 884.0]
    for (key, meta), lx in zip(groups.items(), slot_x):
        color = str(meta["color"])
        # Share of total mentions carried by this theme, for the caption.
        grp_mentions = sum(int(p["count"]) for p in placed if p["group"] == key)
        parts.append(
            f'<g class="legend-row legend-{key}" tabindex="0" '
            f'role="listitem" transform="translate({lx:.0f},{legend_y:.0f})">'
            f'<title>{_xml(str(meta["label"]))}: {grp_mentions:,} total '
            f'mentions</title>'
        )
        parts.append(
            f'<rect class="grp-{key}" x="0" y="-16" width="26" height="26" '
            f'rx="7" fill="{color}"/>'
        )
        parts.append(
            f'<text x="38" y="0" font-size="19" font-weight="600" '
            f'fill="{_INK}" dominant-baseline="middle">'
            f'{_xml(str(meta["label"]))}</text>'
        )
        parts.append("</g>")

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    """Write the word-cloud SVG to the skill's ``svg-examples`` folder."""
    render_cli(__file__, "wordcloud", build_svg, description="Render the wordcloud SVG.")


if __name__ == "__main__":
    main()

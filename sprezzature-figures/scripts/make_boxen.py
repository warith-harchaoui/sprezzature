#!/usr/bin/env python3
"""
make_boxen — letter-value (boxen) plot as a hand-authored SVG.

A **letter-value plot** (Hofmann, Wickham & Kafadar 2017), popularised
as seaborn's ``boxenplot``, is a box-plot built for *large* samples. A
classic box plot stops at the quartiles and then dumps everything past
1.5·IQR into "outliers" — which, at n in the tens of thousands, is both
misleading (hundreds of perfectly ordinary points flagged as outliers)
and wasteful (the interesting tail shape is thrown away). The
letter-value plot instead draws a *nested* stack of boxes, each one
covering half of the remaining tail: the middle 50 % (the quartiles,
letter value **F**), then the middle 75 % (**E**), the middle 87.5 %
(**D**), and so on, halting when a box would hold too few points to be
estimated reliably. The widening/narrowing of successive boxes reads
off the tail heaviness directly.

This module builds the plot **by hand** as an SVG string — Vega-Lite
has no native letter-value mark, and hand SVG lets each nested box carry
its own ``<title>`` tooltip and a CSS ``:hover`` lift. No matplotlib,
seaborn, or plotly. Running the module writes the SVG artifact.

The data is synthetic but communicative: end-to-end request latency for
three service tiers, the exact distribution where a boxen plot earns its
keep — latency is right-skewed with a long tail, and "the p99 tail is
what pages you at 3 a.m.", not the median.

Style follows the sprezzature-* house tokens (Roboto, Apple-system palette,
ink ``#1D1D1F`` on white, rounded corners) from ``_style.py``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Tuple

import _style
from _render import render_cli  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# ------------------------------------------------------------------
# Canvas + layout constants (all in user-space px).
# ------------------------------------------------------------------
WIDTH: int = 1040
HEIGHT: int = 700
MARGIN_LEFT: int = 120  # room for the y-axis latency labels
MARGIN_RIGHT: int = 40
MARGIN_TOP: int = 118  # title + subtitle band
MARGIN_BOTTOM: int = 104  # category labels + legend

PLOT_LEFT: int = MARGIN_LEFT
PLOT_RIGHT: int = WIDTH - MARGIN_RIGHT
PLOT_TOP: int = MARGIN_TOP
PLOT_BOTTOM: int = HEIGHT - MARGIN_BOTTOM

INK: str = "#1D1D1F"  # primary text
SUBTLE: str = "#6E6E73"  # secondary text
GRID: str = "#E5E5EA"  # hairline gridlines
WHITE: str = "#FFFFFF"

# The y-axis latency window (milliseconds). Fixed so the boxes across
# tiers share one scale and stay comparable.
Y_MIN: float = 0.0
Y_MAX: float = 900.0


def lognormal_sample(
    n: int,
    *,
    median_ms: float,
    sigma: float,
    seed: int,
) -> List[float]:
    """Draw ``n`` right-skewed latency samples from a log-normal law.

    Latency distributions are the textbook use-case for a boxen plot:
    a firm floor, a dense body, and a long right tail. A log-normal
    reproduces that shape faithfully and deterministically.

    Parameters
    ----------
    n : int
        Sample size (kept large — a boxen plot is *for* large n).
    median_ms : float
        Desired median latency in milliseconds; sets the log-normal
        location so the 50th percentile lands here.
    sigma : float
        Log-space standard deviation — the tail-heaviness knob. Larger
        ``sigma`` yields a longer p99 tail and wider outer boxes.
    seed : int
        Seed for the local ``random.Random`` so the artifact is
        byte-reproducible run to run.

    Returns
    -------
    list of float
        ``n`` latency samples in milliseconds, unsorted.
    """
    rng = random.Random(seed)
    mu = math.log(median_ms)  # median of a log-normal is exp(mu)
    return [math.exp(rng.gauss(mu, sigma)) for _ in range(n)]


def _quantile(sorted_vals: List[float], q: float) -> float:
    """Linear-interpolation quantile of an already-sorted list.

    Parameters
    ----------
    sorted_vals : list of float
        Ascending-sorted samples.
    q : float
        Quantile in ``[0, 1]``.

    Returns
    -------
    float
        The interpolated quantile value.
    """
    if not sorted_vals:
        return math.nan
    if q <= 0:
        return sorted_vals[0]
    if q >= 1:
        return sorted_vals[-1]
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def letter_values(
    samples: List[float],
    *,
    min_per_box: int = 12,
) -> List[Dict[str, float]]:
    """Compute the nested letter values (boxen boxes) of a sample.

    Starting from the median, each successive "letter value" halves the
    tail probability: the box edges sit at quantiles
    ``0.5 ± 0.5·(1/2)^k`` for depth ``k = 1, 2, 3, …``. Boxes are added
    outward until the tail beyond a box would hold fewer than
    ``min_per_box`` points — the reliability stop from Hofmann et al.

    Parameters
    ----------
    samples : list of float
        The raw sample (any order).
    min_per_box : int, optional
        Smallest number of points a box's outer tail may contain before
        the nesting halts (default 12). Guards against estimating a box
        edge from a handful of points.

    Returns
    -------
    list of dict
        One dict per box, innermost first, each with keys ``lower``,
        ``upper`` (quantile values), ``coverage`` (fraction of the
        distribution the box spans, e.g. 0.5, 0.75, …) and ``depth``
        (k). The median is *not* a box; it is returned separately by
        :func:`box_stats`.
    """
    vals = sorted(samples)
    n = len(vals)
    boxes: List[Dict[str, float]] = []
    depth = 1
    while True:
        tail = 0.5 * (0.5 ** depth)  # probability mass in ONE tail beyond the box
        if tail * n < min_per_box:
            break
        lower_q = tail
        upper_q = 1.0 - tail
        boxes.append(
            {
                "lower": _quantile(vals, lower_q),
                "upper": _quantile(vals, upper_q),
                "coverage": upper_q - lower_q,
                "depth": float(depth),
            }
        )
        depth += 1
        if depth > 8:  # 8 nested boxes is already deep; stop for legibility
            break
    return boxes


def box_stats(samples: List[float]) -> Dict[str, float]:
    """Return the summary statistics annotated alongside the boxes.

    Parameters
    ----------
    samples : list of float
        The raw sample.

    Returns
    -------
    dict
        ``median``, ``p99`` and ``n`` (sample size) — the numbers the
        subtitle and tooltips quote.
    """
    vals = sorted(samples)
    return {
        "median": _quantile(vals, 0.5),
        "p99": _quantile(vals, 0.99),
        "n": float(len(vals)),
    }


# ------------------------------------------------------------------
# Scale helpers
# ------------------------------------------------------------------
def y_pos(value_ms: float) -> float:
    """Map a latency value to a y pixel (larger latency → higher up).

    Parameters
    ----------
    value_ms : float
        Latency in milliseconds.

    Returns
    -------
    float
        The y coordinate in user space, clamped to the plot band.
    """
    frac = (value_ms - Y_MIN) / (Y_MAX - Y_MIN)
    frac = max(0.0, min(1.0, frac))
    return PLOT_BOTTOM - frac * (PLOT_BOTTOM - PLOT_TOP)


def _fmt_ms(value_ms: float) -> str:
    """Format a latency for a label/tooltip, e.g. ``312 ms``."""
    return f"{value_ms:.0f} ms"


# ------------------------------------------------------------------
# Blue ramp for nested boxes: innermost = deepest blue, outer = paler.
# The nesting reads as a value ramp (a single hue, light→dark), which is
# CVD-safe and matches the house blue.
# ------------------------------------------------------------------
_BLUE_RAMP: List[str] = [
    "#0A4DA0",  # depth 1 (innermost, middle 50 %) — deepest
    "#0F62C4",
    "#1E7CEA",
    "#4E9BF2",
    "#7FB7F7",
    "#A9CFFA",
    "#CBE1FC",
    "#E3EEFD",  # outermost — palest
]


def _ramp_color(depth: int) -> str:
    """Return the fill for a box at nesting ``depth`` (1 = innermost)."""
    idx = min(depth - 1, len(_BLUE_RAMP) - 1)
    return _BLUE_RAMP[idx]


# ------------------------------------------------------------------
# SVG assembly
# ------------------------------------------------------------------
def _box_half_width_at(
    value_ms: float,
    boxes: List[Dict[str, float]],
    half_width: float,
    n_boxes: int,
) -> float:
    """Half-width of the outermost box that still spans ``value_ms``.

    Used to anchor the p99 leader on the actual right edge of the stack
    at that height, so nothing sits on top of a coloured fill.
    """
    hw = half_width * (1.0 - 0.50)  # default: outermost (narrowest)
    for box in boxes:
        if box["lower"] <= value_ms <= box["upper"]:
            taper = 1.0 - 0.50 * (int(box["depth"]) - 1) / max(1, n_boxes - 1)
            hw = half_width * taper
    return hw


def _boxen_group(
    *,
    label: str,
    samples: List[float],
    cx: float,
    half_width: float,
    flip_label: bool = False,
) -> Tuple[str, Dict[str, float]]:
    """Render one category's nested-box stack as an SVG ``<g>``.

    Parameters
    ----------
    label : str
        Category name (drawn under the axis).
    samples : list of float
        This category's raw sample.
    cx : float
        Centre x of the stack in user space.
    half_width : float
        Half the maximum box width — the innermost (widest) box spans
        ``2·half_width``; outer boxes taper toward the tail.
    flip_label : bool, optional
        Park the p99 label in the gutter to the *left* of the stack
        instead of the right — used for the last category so its label
        never runs off the right edge of the canvas.

    Returns
    -------
    tuple of (str, dict)
        The SVG markup for the group, and this category's
        :func:`box_stats` (for the legend/subtitle).
    """
    boxes = letter_values(samples)
    stats = box_stats(samples)
    n_boxes = len(boxes)
    parts: List[str] = [f'  <g class="stack" role="listitem" aria-label="{label} latency distribution">']

    # Whisker line from the outermost box edges to median — a thin spine
    # so the reader sees the full extent even where pale boxes fade out.
    if boxes:
        outer = boxes[-1]
        parts.append(
            f'    <line x1="{cx:.1f}" y1="{y_pos(outer["lower"]):.1f}" '
            f'x2="{cx:.1f}" y2="{y_pos(outer["upper"]):.1f}" '
            f'stroke="{GRID}" stroke-width="1.5"/>'
        )

    # Draw outermost → innermost so the deep-blue centre paints on top.
    # The width tapers gently from the widest (innermost, at the median)
    # toward the tail — a monotone narrowing so the nesting reads as a
    # clean stepped pyramid, not a bulb.
    for box in reversed(boxes):
        depth = int(box["depth"])
        taper = 1.0 - 0.50 * (depth - 1) / max(1, n_boxes - 1)
        hw = half_width * taper
        top_y = y_pos(box["upper"])
        bot_y = y_pos(box["lower"])
        h = max(1.0, bot_y - top_y)
        pct = box["coverage"] * 100.0
        tip = (
            f'{label} · middle {pct:.1f}% of requests · '
            f'{_fmt_ms(box["lower"])}–{_fmt_ms(box["upper"])}'
        )
        parts.append(
            f'    <rect class="lv" x="{cx - hw:.1f}" y="{top_y:.1f}" '
            f'width="{2 * hw:.1f}" height="{h:.1f}" rx="3" '
            f'fill="{_ramp_color(depth)}" stroke="{WHITE}" stroke-width="1.4">'
            f"<title>{tip}</title></rect>"
        )

    # Median line — the crisp centre reference, drawn last (on top). A
    # white halo under a thin ink core keeps it legible on both the deep
    # inner blue and any paler box it might straddle.
    med_y = y_pos(stats["median"])
    parts.append(
        f'    <line x1="{cx - half_width:.1f}" y1="{med_y:.1f}" '
        f'x2="{cx + half_width:.1f}" y2="{med_y:.1f}" '
        f'stroke="{WHITE}" stroke-width="4.6"/>'
    )
    parts.append(
        f'    <line class="median" x1="{cx - half_width:.1f}" y1="{med_y:.1f}" '
        f'x2="{cx + half_width:.1f}" y2="{med_y:.1f}" '
        f'stroke="{INK}" stroke-width="1.9">'
        f'<title>{label} · median {_fmt_ms(stats["median"])}</title></line>'
    )

    # p99 marker: a short dark tick straddling the box edge at the p99
    # height, then a thin dashed leader out to a label parked in the clear
    # white gutter beside the stack. The label lives OFF the coloured
    # fills (crisp INK-on-white, no colour-on-colour); the last category
    # flips its label to the left so nothing runs off the canvas.
    p99_y = y_pos(stats["p99"])
    edge_hw = _box_half_width_at(stats["p99"], boxes, half_width, n_boxes)
    if flip_label:
        edge_x = cx - edge_hw
        tick_x1, tick_x2 = edge_x - 11, edge_x + 6
        lead_x1 = edge_x - 11
        lead_x2 = cx - half_width - 13
        text_x = lead_x2 - 6
        anchor = "end"
    else:
        edge_x = cx + edge_hw
        tick_x1, tick_x2 = edge_x - 6, edge_x + 11
        lead_x1 = edge_x + 11
        lead_x2 = cx + half_width + 13
        text_x = lead_x2 + 6
        anchor = "start"
    parts.append(
        f'    <line x1="{tick_x1:.1f}" y1="{p99_y:.1f}" x2="{tick_x2:.1f}" y2="{p99_y:.1f}" '
        f'stroke="{INK}" stroke-width="2.4"/>'
    )
    parts.append(
        f'    <line x1="{lead_x1:.1f}" y1="{p99_y:.1f}" x2="{lead_x2:.1f}" y2="{p99_y:.1f}" '
        f'stroke="{SUBTLE}" stroke-width="1" stroke-dasharray="2 3"/>'
    )
    parts.append(
        f'    <text x="{text_x:.1f}" y="{p99_y + 4.6:.1f}" font-size="14.5" '
        f'text-anchor="{anchor}" fill="{INK}" font-family="Roboto Mono, monospace">'
        f'<tspan fill="{SUBTLE}">p99</tspan> {_fmt_ms(stats["p99"])}</text>'
    )

    # Category label under the axis.
    parts.append(
        f'    <text x="{cx:.1f}" y="{PLOT_BOTTOM + 34:.1f}" font-size="18" '
        f'fill="{INK}" text-anchor="middle" font-weight="500">{label}</text>'
    )
    parts.append("  </g>")
    return "\n".join(parts), stats


def _y_axis() -> str:
    """Render the y-axis: domain line, latency ticks, gridlines, title."""
    parts: List[str] = ['  <g class="yaxis" aria-hidden="true">']
    # Horizontal gridlines + labels every 150 ms.
    tick = 0.0
    while tick <= Y_MAX + 1e-6:
        yy = y_pos(tick)
        parts.append(
            f'    <line x1="{PLOT_LEFT:.1f}" y1="{yy:.1f}" x2="{PLOT_RIGHT:.1f}" '
            f'y2="{yy:.1f}" stroke="{GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'    <text x="{PLOT_LEFT - 16:.1f}" y="{yy + 5:.1f}" font-size="15" '
            f'fill="{SUBTLE}" text-anchor="end" font-family="Roboto Mono, monospace">{tick:.0f}</text>'
        )
        tick += 150.0
    # Axis title, rotated.
    ty = (PLOT_TOP + PLOT_BOTTOM) / 2.0
    parts.append(
        f'    <text x="34" y="{ty:.1f}" font-size="16" fill="{INK}" '
        f'text-anchor="middle" transform="rotate(-90 34 {ty:.1f})">'
        "Request latency (ms)</text>"
    )
    parts.append("  </g>")
    return "\n".join(parts)


def _legend() -> str:
    """Render the depth legend explaining the nested boxes."""
    lx = PLOT_LEFT
    ly = HEIGHT - 26
    swatch = [
        ("#0A4DA0", "middle 50%"),
        ("#1E7CEA", "75%"),
        ("#7FB7F7", "87.5%"),
        ("#CBE1FC", "deeper tails"),
    ]
    parts: List[str] = [f'  <g class="legend" transform="translate({lx},{ly})" aria-hidden="true">']
    x = 0.0
    for hexc, txt in swatch:
        parts.append(f'    <rect x="{x:.1f}" y="-13" width="17" height="17" rx="3" fill="{hexc}"/>')
        parts.append(f'    <text x="{x + 24:.1f}" y="1" font-size="15" fill="{SUBTLE}">{txt}</text>')
        x += 24 + 9.4 * len(txt) + 24
    parts.append("  </g>")
    return "\n".join(parts)


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full boxen-plot SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). **No-op for the box fills by design:** the nested
        boxes use a single-hue blue *value* ramp (``_BLUE_RAMP``, deepest→palest
        by depth), which is a sequential perceptual map — already colour-vision-
        and greyscale-safe because it leans on lightness, never on a red/green
        contrast. Re-spacing its anchors by an accessibility level de-tunes it
        (monochrome even breaks the light→dark monotonicity of the outer boxes),
        so the categorical level is deliberately *not* applied here; the flag is
        accepted for a uniform command line and only gates the palette-reachable
        assertion below. Defaults to ``"universal"``.

    Returns
    -------
    str
        A complete, self-contained SVG (fonts + colors inline), ready to
        write to disk or embed.
    """
    # Confirm the house palette is reachable at the requested level (keeps
    # make ↔ audit in sync); the blue value ramp is a sequential perceptual map,
    # already CVD/greyscale-safe, so it is intentionally left at its own tuning.
    palette = _style.load_palette(accessibility)
    assert palette.get("Blue", "#007AFF"), "house palette must expose Blue"

    # Three service tiers. Free is the noisiest (largest sigma → longest
    # tail); Enterprise is tightest. n is large — the boxen's raison d'être.
    tiers: List[Dict[str, Any]] = [
        {"label": "Free tier", "median": 210.0, "sigma": 0.62, "seed": 11, "n": 24000},
        {"label": "Pro tier", "median": 150.0, "sigma": 0.44, "seed": 23, "n": 24000},
        {"label": "Enterprise", "median": 118.0, "sigma": 0.30, "seed": 37, "n": 24000},
    ]

    n_cat = len(tiers)
    band = (PLOT_RIGHT - PLOT_LEFT) / n_cat
    half_width = min(96.0, band * 0.31)

    groups: List[str] = []
    all_stats: List[Dict[str, float]] = []
    for i, t in enumerate(tiers):
        samples = lognormal_sample(
            int(t["n"]),
            median_ms=float(t["median"]),
            sigma=float(t["sigma"]),
            seed=int(t["seed"]),
        )
        cx = PLOT_LEFT + band * (i + 0.5)
        markup, stats = _boxen_group(
            label=str(t["label"]),
            samples=samples,
            cx=cx,
            half_width=half_width,
            flip_label=(i == n_cat - 1),
        )
        groups.append(markup)
        all_stats.append(stats)

    # Subtitle takeaway: contrast the p99 tails, which is what a boxen
    # plot surfaces that a bare median hides.
    free_p99 = all_stats[0]["p99"]
    ent_p99 = all_stats[2]["p99"]
    ratio = free_p99 / ent_p99
    subtitle = (
        f"Free-tier p99 latency ({free_p99:.0f} ms) runs {ratio:.1f}× the "
        f"Enterprise tail ({ent_p99:.0f} ms), yet the median barely moves"
    )
    n_each = int(all_stats[0]["n"])

    header = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="Roboto, system-ui, sans-serif" '
        f'role="img" aria-labelledby="bx-title bx-desc">'
    )
    title_block = (
        f'<title id="bx-title">Where each service tier hides its latency tail</title>'
        f'<desc id="bx-desc">Letter-value (boxen) plot of request latency for three '
        f"service tiers, {n_each:,} sampled requests each. Nested boxes step outward "
        f"from the median through the middle 50%, 75%, 87.5% and deeper tails; a tick "
        f"marks each tier's p99. Free tier has the widest, longest tail; Enterprise the "
        f"tightest. {subtitle}.</desc>"
    )
    # A boxen plot is a static distribution summary — motion adds no
    # insight, so there is none. The only interactive affordance is a
    # gentle hover emphasis (opacity) so the per-box tooltips are
    # discoverable; every box is fully painted at t=0.
    # prefers-contrast: this is a PERCEPTUAL figure — the nested boxes use a
    # single-hue blue VALUE ramp (deepest->palest by depth), a sequential map
    # left untouched. We only STRENGTHEN STRUCTURE: deepen the secondary ink
    # toward the primary ink and darken + thicken the hairline gridlines / the
    # box whiskers so the frame reads harder for a low-vision reader without
    # re-tuning the ramp. Additive + media-gated, so the default is unchanged.
    contrast = (
        "@media (prefers-contrast: more){"
        f'[fill="{SUBTLE}"]{{fill:{INK};}}'
        f'[stroke="{GRID}"]{{stroke:#8A8A8E;stroke-width:2;}}'
        "}"
    )
    # Additive dark mode: flip paper + ink, restate the CSS `text{fill}` default
    # in off-white (the attribute selector cannot see CSS-set fills), and darken
    # the hairline gridlines. The blue box ramp and white keylines are left be.
    dark = _style.os_dark_style(
        extra="text{fill:#F2F2F7;}[stroke=\"%s\"]{stroke:#2C2C2E;}" % GRID
    )
    style = f"""  <style>
    .lv {{ transition: opacity .12s ease; }}
    .stack:hover .lv {{ opacity: .6; }}
    .lv:hover {{ opacity: 1; }}
    @media (prefers-reduced-motion: reduce) {{ .lv {{ transition: none; }} }}
    text {{ fill: {INK}; }}
    {contrast}
    {dark}
  </style>"""
    bg = f'  <rect width="{WIDTH}" height="{HEIGHT}" fill="{WHITE}"/>'
    title_text = (
        f'  <text x="{PLOT_LEFT}" y="48" font-size="26" font-weight="700" '
        f'fill="{INK}">Where each service tier hides its latency tail</text>'
    )
    subtitle_text = (
        f'  <text x="{PLOT_LEFT}" y="77" font-size="17" fill="{SUBTLE}">{subtitle}</text>'
    )
    caption = (
        f'  <text x="{PLOT_LEFT}" y="99" font-size="14" fill="{SUBTLE}" '
        f'font-family="Roboto Mono, monospace">Letter-value plot · '
        f"{n_each:,} requests per tier · illustrative</text>"
    )

    body = "\n".join(
        [
            header,
            title_block,
            style,
            bg,
            title_text,
            subtitle_text,
            caption,
            _y_axis(),
            '  <g role="list">',
            *groups,
            "  </g>",
            _legend(),
            fullscreen_control(WIDTH, HEIGHT, mode),
            "</svg>",
        ]
    )
    return body


def main() -> None:
    """Build the SVG and write it to the skill's asset directory.

    The ``--mode`` flag selects the interactivity mode of the emitted SVG
    (``self-contained`` / ``external`` / ``static``); see
    :func:`_interactive.fullscreen_control`.
    """
    render_cli(__file__, "boxen", build_svg, description="Render the boxen-plot SVG.")


if __name__ == "__main__":
    main()

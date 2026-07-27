#!/usr/bin/env python3
"""Generate a publication-quality *Bollinger band* chart as a standalone static SVG.

Bollinger bands wrap a price series in a volatility envelope: a 20-day simple
moving average (the middle band) flanked by an upper and lower band two standard
deviations away, measured over the same rolling window. When markets go quiet the
two bands pinch together — a **squeeze** — and the coiled range often precedes a
sharp directional move; when price pushes through a band, the **breakout** is the
trade traders wait for. The shaded envelope turns "how volatile is this, and
where is price relative to its own recent range?" into a single glance.

This module builds the SVG string **by hand** (no matplotlib / seaborn / plotly,
no Vega): the shaded band between two smoothed curves, the squeeze / breakout
call-outs, and the side-aware end labels are all things a plotting library makes
fiddly, whereas a hand-authored path gives us exact control over where the fill
meets each curve and where every annotation lands. Both band edges and the price
line ride the same Catmull-Rom smoothing so the shaded region hugs the rendered
curves with no seam.

A Bollinger chart is a dense static read; motion adds nothing a still cannot
already show, so the whole picture is drawn fully at rest — every band, line,
marker and label is present the instant the SVG loads. The squeeze and breakout
each carry a native ``<title>`` tooltip, and the two events are also spelled out
in ink text, so the story survives colour-vision deficiency.

The example data is illustrative: **one trading year of a mid-cap stock**, priced
around the mid-$120s, that drifts sideways into a tight late-summer squeeze — the
20-day band width falls to a yearly low — and then breaks out to the upside,
riding the upper band through the autumn. It is the textbook squeeze-then-breakout
shape a Bollinger chart is built to narrate.

Usage
-----
    python make_bollinger.py                 # writes the house SVG
    python make_bollinger.py --out other.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc
classes, generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _svg import catmull_rom_beziers, fmt_compact  # noqa: E402
from _render import write_svg  # noqa: E402
from _style import leveled_colors, os_adaptive_style, os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "bollinger.svg"
)

# House-style tokens (mirrors _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"

# Colour roles, drawn from the Apple-system palette.
#   * the price line is the hero (deep near-navy, always legible on the fill);
#   * the moving average is a calm Blue reference (psychology: trust, logic);
#   * the +/-2 sigma envelope is a soft Teal wash — cool, secondary, never
#     competing with the price line that rides on top of it.
_PRICE_LINE = "#1D1D1F"  # ink — the daily close, the star of the chart
_MA_LINE = "#AF52DE"     # Apple Purple — the 20-day moving average, distinct from the band
_BAND_FILL = "#007AFF"   # Apple Blue — the volatility envelope wash (soft, low opacity)
_BAND_EDGE = "#5AC8FA"   # Apple Teal for the band edges
# Event accents: a squeeze is a caution amber (volatility coiling), a breakout
# is a confident green (the directional move traders wait for).
_SQUEEZE_HUE = "#FF9500"  # Apple Orange — the low-volatility pinch
_BREAKOUT_HUE = "#34C759"  # Apple Green — price pushes through the upper band


# --------------------------------------------------------------------------- #
# Illustrative data                                                            #
# --------------------------------------------------------------------------- #
def _sample_prices(seed: int = 11) -> Dict[str, np.ndarray]:
    """Synthesise one trading year of a mid-cap stock's daily close.

    The path is hand-shaped to the headline: a listless sideways drift through
    the spring and summer whose day-to-day range keeps shrinking (the squeeze),
    followed by an autumn breakout that trends up along the upper band. Gaussian
    innovations whose scale tracks that same volatility envelope give the series
    a realistic texture without any real ticker.

    Parameters
    ----------
    seed : int, optional
        Seed for the random generator, for a reproducible figure.

    Returns
    -------
    dict of str to numpy.ndarray
        ``{"close": np.ndarray}`` — 252 daily closing prices (one trading year),
        in dollars.
    """
    rng = np.random.default_rng(seed)
    n = 252
    t = np.arange(n)

    # Volatility envelope: elevated early, collapsing to a mid-year trough (the
    # squeeze), then re-expanding as the breakout runs. Scales the daily step.
    vol = (
        1.9
        - 1.55 * np.exp(-0.5 * ((t - 178.0) / 26.0) ** 2)  # the late-summer squeeze
        + 0.9 * np.exp(-0.5 * ((t - 220.0) / 24.0) ** 2)   # breakout expansion
    )
    vol = np.clip(vol, 0.30, None)

    # Drift: flat through the coil, then a steady up-trend once price breaks out.
    drift = np.where(t < 188, 0.0, 0.11)

    # Random walk with the volatility-scaled steps plus the regime drift.
    steps = rng.normal(0.0, 1.0, size=n) * vol + drift
    close = 122.0 + np.cumsum(steps)

    # A gentle, deterministic post-breakout lift so the story reads cleanly even
    # on an unlucky seed: bias the final third upward toward the upper band.
    lift = np.where(t > 195, 0.07 * (t - 195), 0.0)
    close = close + lift

    return {"close": close}


def _rolling_bands(
    close: np.ndarray,
    window: int = 20,
    n_sigma: float = 2.0,
) -> Dict[str, np.ndarray]:
    """Compute the classic Bollinger triplet: middle SMA and +/-n-sigma bands.

    The middle band is the ``window``-day simple moving average; the upper and
    lower bands sit ``n_sigma`` rolling standard deviations away, using the same
    trailing window (population standard deviation, the Bollinger convention).
    The first ``window - 1`` days lack a full window and are returned as NaN so
    the caller can start every band cleanly at day ``window - 1``.

    Parameters
    ----------
    close : numpy.ndarray
        Daily closing prices.
    window : int, optional
        Rolling window length in trading days (default 20, the classic setting).
    n_sigma : float, optional
        Band half-width in standard deviations (default 2.0).

    Returns
    -------
    dict of str to numpy.ndarray
        ``{"middle": ..., "upper": ..., "lower": ..., "width": ...}`` — each the
        same length as ``close``; ``width`` is ``(upper - lower) / middle`` (the
        normalised band width used to locate the squeeze). Leading positions
        without a full window hold NaN.
    """
    n = len(close)
    middle = np.full(n, np.nan)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    width = np.full(n, np.nan)
    for i in range(window - 1, n):
        w = close[i - window + 1 : i + 1]
        m = float(w.mean())
        s = float(w.std())  # population std — the Bollinger convention
        middle[i] = m
        upper[i] = m + n_sigma * s
        lower[i] = m - n_sigma * s
        width[i] = (upper[i] - lower[i]) / m if m else np.nan
    return {"middle": middle, "upper": upper, "lower": lower, "width": width}


# --------------------------------------------------------------------------- #
# Geometry helpers                                                             #
# --------------------------------------------------------------------------- #
# Compact path-data formatter, now shared in _svg (byte-identical to the old
# private ``_fmt``); the local name is kept so the call sites stay untouched.
_fmt = fmt_compact


def _catmull_rom(pts: Sequence[Tuple[float, float]], tension: float = 6.0) -> str:
    """Return SVG ``C`` commands for a smooth Catmull-Rom spline through ``pts``.

    Thin wrapper over :func:`_svg.catmull_rom_beziers` that pins the local
    :func:`_fmt` formatter, so the emitted string is identical to the old
    inline copy while the spline maths lives in the shared module.

    Parameters
    ----------
    pts : sequence of (float, float)
        The sample points, in pixel coordinates.
    tension : float, optional
        Catmull-Rom denominator; ``6`` is the standard uniform spline.

    Returns
    -------
    str
        A run of SVG ``C`` path commands (a plain line-to when < 3 points).
    """
    return catmull_rom_beziers(pts, _fmt, tension)


def _line_path(pts: Sequence[Tuple[float, float]]) -> str:
    """Return a smooth open ``d`` path string for a curve through ``pts``."""
    x0, y0 = pts[0]
    return f"M{_fmt(x0)},{_fmt(y0)}" + _catmull_rom(pts)


def _band_path(
    top: Sequence[Tuple[float, float]],
    bottom: Sequence[Tuple[float, float]],
) -> str:
    """Return a closed ``d`` path filling between two same-x sample curves.

    Both edges are drawn as smooth Catmull-Rom splines so the shaded band's
    boundaries match the rendered curves exactly.

    Parameters
    ----------
    top, bottom : sequence of (float, float)
        The two curves, sampled at the same x-positions, left → right.

    Returns
    -------
    str
        A closed SVG path ``d`` string (top edge left→right, bottom edge
        right→left).
    """
    d = _line_path(top)
    rev = list(reversed(bottom))
    d += f" L{_fmt(rev[0][0])},{_fmt(rev[0][1])}" + _catmull_rom(rev)
    return d + " Z"


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def build_svg(
    data: Dict[str, np.ndarray],
    window: int = 20,
    n_sigma: float = 2.0,
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full Bollinger-band SVG document as a string.

    Parameters
    ----------
    data : dict of str to numpy.ndarray
        ``{"close": ...}``; one trading year of daily closing prices.
    window : int, optional
        Rolling window for the moving average and bands (default 20).
    n_sigma : float, optional
        Band half-width in standard deviations (default 2.0).
    mode : str, optional
        Interactivity mode for the figure (default ``"self-contained"``).
        ``"self-contained"`` embeds a self-carrying fullscreen button and the
        script that wires it, so the SVG works on its own; ``"external"``
        defers that control to a page-level module; ``"static"`` ships no
        interactivity at all. In every mode a plain ``<img>`` or PNG raster is
        byte-identical, since the button starts hidden.
    accessibility : str, optional
        Palette accessibility level applied to the figure's categorical role
        hues — the price line, moving-average line, band wash/edge, and the
        squeeze/breakout event accents (default ``"universal"``, the identity,
        so the shipped SVG is byte-for-byte unchanged). Other levels remap
        those hues through the sprezzature-colors engine so the roles stay distinct
        for that viewer.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    # Categorical role hues, remapped for the requested accessibility level.
    # These shadow the module-level constants inside this function's scope, so
    # every f-string below picks up the levelled colour; ``universal`` is the
    # identity, keeping the default output byte-for-byte unchanged.
    _role_colours = leveled_colors(
        {
            "price": _PRICE_LINE,
            "ma": _MA_LINE,
            "band_fill": _BAND_FILL,
            "band_edge": _BAND_EDGE,
            "squeeze": _SQUEEZE_HUE,
            "breakout": _BREAKOUT_HUE,
        },
        accessibility,
    )
    _PRICE_LINE_C = _role_colours["price"]
    _MA_LINE_C = _role_colours["ma"]
    _BAND_FILL_C = _role_colours["band_fill"]
    _BAND_EDGE_C = _role_colours["band_edge"]
    _SQUEEZE_HUE_C = _role_colours["squeeze"]
    _BREAKOUT_HUE_C = _role_colours["breakout"]

    close = data["close"]
    bands = _rolling_bands(close, window=window, n_sigma=n_sigma)
    middle, upper, lower, bwidth = bands["middle"], bands["upper"], bands["lower"], bands["width"]
    n = len(close)

    # First index with a full window — every band starts here.
    start = window - 1

    # ---- canvas geometry -------------------------------------------------- #
    # Poster-scale: wide enough for a trading year to breathe, tall enough that
    # the +/-2 sigma envelope is a comfortable shape rather than a sliver.
    width, height = 1280, 800
    m_left, m_right = 92, 214
    m_top, m_bottom = 208, 92
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    # ---- value scale ------------------------------------------------------ #
    # Domain spans the widest band reach with tidy $5 gridlines and headroom so
    # nothing kisses the frame.
    lo = float(np.nanmin(lower[start:]))
    hi = float(np.nanmax(upper[start:]))
    lo = min(lo, float(close[start:].min()))
    hi = max(hi, float(close[start:].max()))
    y_lo = np.floor((lo - 3.0) / 5.0) * 5.0
    y_hi = np.ceil((hi + 3.0) / 5.0) * 5.0

    def x_of(d: float) -> float:
        """Map a day index (start..n-1) to a pixel column."""
        return m_left + (d - start) / (n - 1 - start) * plot_w

    def y_of(v: float) -> float:
        """Map a price to a pixel row (higher price → higher up)."""
        return m_top + (y_hi - v) / (y_hi - y_lo) * plot_h

    idx = list(range(start, n))
    upper_pts = [(x_of(d), y_of(float(upper[d]))) for d in idx]
    lower_pts = [(x_of(d), y_of(float(lower[d]))) for d in idx]
    middle_pts = [(x_of(d), y_of(float(middle[d]))) for d in idx]
    price_pts = [(x_of(d), y_of(float(close[d]))) for d in idx]

    # ---- locate the two story beats --------------------------------------- #
    # Squeeze: the day the normalised band width is narrowest (excluding the
    # warm-up where the window is still filling). Breakout: the first day after
    # the squeeze that the close pushes above the upper band.
    valid = np.arange(start, n)
    squeeze_day = int(valid[np.nanargmin(bwidth[start:])])
    breakout_day = None
    for d in range(squeeze_day + 1, n):
        if close[d] > upper[d]:
            breakout_day = d
            break

    parts: List[str] = []
    defs: List[str] = []

    # ---- header ----------------------------------------------------------- #
    title = "A late-summer squeeze coiled the range, then price broke out to the upside"
    subtitle = (
        "Daily close with a 20-day moving average and Bollinger bands at "
        "±2 standard deviations"
    )
    parts.append(
        f'<svg role="img" aria-label="{title}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}">'
    )
    parts.append(
        f"<title>{title}</title>"
        f"<desc>Bollinger band chart of one trading year of a mid-cap stock. A "
        f"near-navy line is the daily close; a blue line is the 20-day simple "
        f"moving average; a teal band spans two standard deviations above and "
        f"below it. Through the summer the band pinches to its narrowest of the "
        f"year — a volatility squeeze, marked in amber — after which the close "
        f"pushes through the upper band and trends up along it — a breakout, "
        f"marked in green. Illustrative data.</desc>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="18" fill="{_BG}"/>')
    parts.append(
        f'<text x="{m_left}" y="70" font-size="30" '
        f'font-weight="700" fill="{_INK}">{title}</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="104" font-size="18" '
        f'fill="{_SECONDARY}">{subtitle}</text>'
    )
    parts.append(
        f'<text x="{m_left}" y="128" font-size="15" '
        f'fill="{_SECONDARY}">Illustrative data &#183; one trading year &#183; '
        f'daily closing price in US dollars</text>'
    )

    # ---- horizontal $5 gridlines ------------------------------------------ #
    grid: List[str] = []
    ax_labels: List[str] = []
    step = 5.0
    v = y_lo
    while v <= y_hi + 1e-6:
        gy = y_of(v)
        grid.append(
            f'<line x1="{_fmt(m_left)}" y1="{_fmt(gy)}" '
            f'x2="{_fmt(m_left + plot_w)}" y2="{_fmt(gy)}" '
            f'stroke="#EFEFF2" stroke-width="1.4"/>'
        )
        ax_labels.append(
            f'<text x="{_fmt(m_left - 16)}" y="{_fmt(gy + 5)}" text-anchor="end" '
            f'font-size="15" font-family="{_MONO}" fill="{_SECONDARY}">'
            f"${v:.0f}</text>"
        )
        v += step

    # ---- the +/-2 sigma band ---------------------------------------------- #
    band = _band_path(upper_pts, lower_pts)
    band_group: List[str] = [
        f'<path class="bo-fill" d="{band}" fill="{_BAND_FILL_C}" fill-opacity="0.12"/>',
        # Faint edges so the envelope reads as a bounded channel, not a blur.
        f'<path class="bo-edge" d="{_line_path(upper_pts)}" fill="none" '
        f'stroke="{_BAND_EDGE_C}" '
        f'stroke-width="1.8"/>',
        f'<path class="bo-edge" d="{_line_path(lower_pts)}" fill="none" '
        f'stroke="{_BAND_EDGE_C}" '
        f'stroke-width="1.8"/>',
    ]

    # ---- moving average + price line -------------------------------------- #
    lines: List[str] = []
    lines.append(
        f'<path class="bo-ma" d="{_line_path(middle_pts)}" fill="none" '
        f'stroke="{_MA_LINE_C}" '
        f'stroke-width="2.4" stroke-dasharray="2 5" stroke-linecap="round"/>'
    )
    lines.append(
        f'<path d="{_line_path(price_pts)}" fill="none" stroke="{_PRICE_LINE_C}" '
        f'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # ---- squeeze call-out ------------------------------------------------- #
    # A vertical band-width bracket at the pinch, plus an amber label above.
    ann: List[str] = []
    sx = x_of(float(squeeze_day))
    s_up_y = y_of(float(upper[squeeze_day]))
    s_lo_y = y_of(float(lower[squeeze_day]))
    ann.append(
        f'<line class="bo-squeeze" x1="{_fmt(sx)}" y1="{_fmt(s_up_y)}" '
        f'x2="{_fmt(sx)}" '
        f'y2="{_fmt(s_lo_y)}" stroke="{_SQUEEZE_HUE_C}" stroke-width="3" '
        f'stroke-linecap="round"/>'
    )
    for yy in (s_up_y, s_lo_y):
        ann.append(
            f'<line class="bo-squeeze" x1="{_fmt(sx - 8)}" y1="{_fmt(yy)}" '
            f'x2="{_fmt(sx + 8)}" '
            f'y2="{_fmt(yy)}" stroke="{_SQUEEZE_HUE_C}" stroke-width="3" '
            f'stroke-linecap="round"/>'
        )
    # Leader up to a two-line amber label sitting in the gap between the legend
    # row and the plot's top edge, so it crowds neither.
    s_lbl_y = m_top - 14
    ann.append(
        f'<line x1="{_fmt(sx)}" y1="{_fmt(s_up_y - 6)}" x2="{_fmt(sx)}" '
        f'y2="{_fmt(s_lbl_y + 8)}" stroke="{_SQUEEZE_HUE_C}" stroke-width="1.4" '
        f'stroke-dasharray="2 4"/>'
    )
    ann.append(
        f'<text class="bo-squeeze-txt" x="{_fmt(sx)}" y="{_fmt(s_lbl_y - 16)}" '
        f'text-anchor="middle" '
        f'font-size="17" font-weight="700" fill="{_SQUEEZE_HUE_C}">The squeeze</text>'
    )
    ann.append(
        f'<text x="{_fmt(sx)}" y="{_fmt(s_lbl_y + 2)}" text-anchor="middle" '
        f'font-size="14" fill="{_SECONDARY}">band width at its yearly low</text>'
    )

    # ---- breakout call-out ------------------------------------------------ #
    markers: List[str] = []
    if breakout_day is not None:
        bx = x_of(float(breakout_day))
        by = y_of(float(close[breakout_day]))
        # White-cored green dot on the close where it clears the upper band.
        markers.append(
            f'<circle class="bo-breakout" cx="{_fmt(bx)}" cy="{_fmt(by)}" r="8" '
            f'fill="{_BG}" '
            f'stroke="{_BREAKOUT_HUE_C}" stroke-width="3.5"/>'
        )
        # Leader down into the open floor below the band, where the price has
        # not yet reached — a clear space for a two-line green label that does
        # not sit on top of any curve.
        b_lbl_x = bx + 10
        b_lbl_y = m_top + plot_h - 40
        ann.append(
            f'<line x1="{_fmt(bx)}" y1="{_fmt(by + 9)}" x2="{_fmt(b_lbl_x)}" '
            f'y2="{_fmt(b_lbl_y - 30)}" stroke="{_BREAKOUT_HUE_C}" '
            f'stroke-width="1.4" stroke-dasharray="2 4"/>'
        )
        ann.append(
            f'<text class="bo-breakout-txt" x="{_fmt(b_lbl_x)}" '
            f'y="{_fmt(b_lbl_y - 10)}" '
            f'font-size="17" font-weight="700" fill="{_BREAKOUT_HUE_C}">'
            f'The breakout</text>'
        )
        ann.append(
            f'<text x="{_fmt(b_lbl_x)}" y="{_fmt(b_lbl_y + 9)}" '
            f'font-size="14" fill="{_SECONDARY}">close clears the upper band</text>'
        )

    # ---- month axis ------------------------------------------------------- #
    # Twelve evenly spaced month ticks across the trading year.
    axis_y = m_top + plot_h
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    axis_bits: List[str] = [
        f'<line x1="{_fmt(m_left)}" y1="{_fmt(axis_y)}" '
        f'x2="{_fmt(m_left + plot_w)}" y2="{_fmt(axis_y)}" '
        f'stroke="{_INK}" stroke-width="1.6"/>'
    ]
    for k, lab in enumerate(month_labels):
        # Place each month tick at the middle of its ~21-day trading slice.
        day = start + (k + 0.5) / 12.0 * (n - 1 - start)
        gx = x_of(day)
        axis_bits.append(
            f'<text x="{_fmt(gx)}" y="{_fmt(axis_y + 28)}" text-anchor="middle" '
            f'font-size="14" font-family="{_MONO}" fill="{_SECONDARY}">{lab}</text>'
        )

    # ---- end-of-line labels (right gutter, side-aware, no clipping) -------- #
    end_labels: List[str] = []
    lbl_x = m_left + plot_w + 20
    # Three anchors: upper band, price/MA cluster, lower band. Price and MA end
    # close together; nudge their labels apart while keeping the band labels
    # pinned to their true band heights.
    # Four labels, top → bottom by their true endpoint height: upper band,
    # then whichever of close / moving-average is higher, then the other, then
    # the lower band. A single downward sweep pushes any label that sits closer
    # than ``gap`` px below its predecessor, so the whole stack stays legible
    # and none collide even when the close ends hard against the upper band.
    rows = [
        {"name": "Upper band", "y": upper_pts[-1][1], "ax": upper_pts[-1][0],
         "colour": _BAND_EDGE_C, "val": float(upper[-1]), "bold": False, "cls": "bo-edge"},
        {"name": "Close", "y": price_pts[-1][1], "ax": price_pts[-1][0],
         "colour": _PRICE_LINE_C, "val": float(close[-1]), "bold": True, "cls": ""},
        {"name": "20-day avg", "y": middle_pts[-1][1], "ax": middle_pts[-1][0],
         "colour": _MA_LINE_C, "val": float(middle[-1]), "bold": False, "cls": "bo-ma"},
        {"name": "Lower band", "y": lower_pts[-1][1], "ax": lower_pts[-1][0],
         "colour": _BAND_EDGE_C, "val": float(lower[-1]), "bold": False, "cls": "bo-edge"},
    ]
    rows.sort(key=lambda r: r["y"])
    gap = 46.0
    ly_prev = m_top - 6.0  # keep the top label from riding into the legend row
    for r in rows:
        r["ly"] = max(r["y"], ly_prev + gap)
        ly_prev = r["ly"]

    def _end_label(anchor_x: float, anchor_y: float, ly: float, colour: str,
                   name: str, value: float, bold: bool, cls: str) -> None:
        """Emit a leader line + name + mono value in the right gutter."""
        # A class on the leader + name (when the row is a colour-coded role) so
        # the @media contrast rules deepen it in step with its curve.
        line_cls = f'class="{cls}" ' if cls else ""
        txt_cls = f'class="{cls}-txt" ' if cls else ""
        end_labels.append(
            f'<line {line_cls}x1="{_fmt(anchor_x)}" y1="{_fmt(anchor_y)}" '
            f'x2="{_fmt(lbl_x - 6)}" y2="{_fmt(ly)}" stroke="{colour}" '
            f'stroke-width="1.4"/>'
        )
        weight = "700" if bold else "600"
        end_labels.append(
            f'<text {txt_cls}x="{_fmt(lbl_x)}" y="{_fmt(ly - 3)}" font-size="16" '
            f'font-weight="{weight}" fill="{colour}">{name}</text>'
        )
        end_labels.append(
            f'<text x="{_fmt(lbl_x)}" y="{_fmt(ly + 16)}" font-size="13" '
            f'font-family="{_MONO}" fill="{_SECONDARY}">${value:.2f}</text>'
        )

    for r in rows:
        _end_label(r["ax"], r["y"], r["ly"], r["colour"], r["name"], r["val"],
                   r["bold"], r["cls"])

    # ---- legend ----------------------------------------------------------- #
    legend: List[str] = []
    ly = 150.0
    lx = m_left
    # Band swatch.
    legend.append(
        f'<rect class="bo-edge" x="{_fmt(lx)}" y="{_fmt(ly - 13)}" width="26" '
        f'height="15" rx="3" '
        f'fill="{_BAND_FILL_C}" fill-opacity="0.12" stroke="{_BAND_EDGE_C}" '
        f'stroke-width="1.2"/>'
    )
    legend.append(
        f'<text x="{_fmt(lx + 34)}" y="{_fmt(ly)}" font-size="15" '
        f'fill="{_INK}">±2σ band</text>'
    )
    # Price line swatch.
    lx += 148
    legend.append(
        f'<line x1="{_fmt(lx)}" y1="{_fmt(ly - 5)}" x2="{_fmt(lx + 26)}" '
        f'y2="{_fmt(ly - 5)}" stroke="{_PRICE_LINE_C}" stroke-width="3.4" '
        f'stroke-linecap="round"/>'
    )
    legend.append(
        f'<text x="{_fmt(lx + 34)}" y="{_fmt(ly)}" font-size="15" '
        f'fill="{_INK}">Daily close</text>'
    )
    # MA line swatch.
    lx += 156
    legend.append(
        f'<line class="bo-ma" x1="{_fmt(lx)}" y1="{_fmt(ly - 5)}" '
        f'x2="{_fmt(lx + 26)}" '
        f'y2="{_fmt(ly - 5)}" stroke="{_MA_LINE_C}" stroke-width="2.4" '
        f'stroke-dasharray="2 5" stroke-linecap="round"/>'
    )
    legend.append(
        f'<text x="{_fmt(lx + 34)}" y="{_fmt(ly)}" font-size="15" '
        f'fill="{_INK}">20-day moving average</text>'
    )

    # ---- hover tooltips: one transparent hit-column per ~2 weeks ---------- #
    tips: List[str] = []
    stride = 10  # a column every ~2 trading weeks keeps the DOM light
    col_w = plot_w / ((n - 1 - start) / stride)
    for d in range(start, n, stride):
        gx = x_of(float(d))
        pct = 0.0
        rng_w = upper[d] - lower[d]
        if rng_w:
            pct = float((close[d] - lower[d]) / rng_w * 100.0)
        tip = (
            f"Day {d - start + 1}: close ${close[d]:.2f} · "
            f"band ${lower[d]:.2f}–${upper[d]:.2f} · "
            f"{pct:.0f}% of the way up the band"
        )
        tips.append(
            f'<rect x="{_fmt(gx - col_w / 2)}" y="{_fmt(m_top)}" '
            f'width="{_fmt(col_w)}" height="{_fmt(plot_h)}" '
            f'fill="transparent"><title>{tip}</title></rect>'
        )

    # ---- OS-adaptive overrides -------------------------------------------- #
    # Additive; the default render is byte-for-byte unchanged because every rule
    # below lives inside a media query. Under prefers-contrast the four coloured
    # roles deepen together on their strokes — the moving-average (purple), the
    # ±2σ band edges (teal), the squeeze accent (orange) and the breakout accent
    # (green) — with their end-labels / call-out text deepened to match. The
    # price line is ink and needs no lift. forced-colors is left to the browser
    # default: this financial chart already survives greyscale (each role also
    # carries a dash pattern, a worded label and a distinct position), and the
    # ~4-colour system palette could not preserve five reference hues plus the
    # band wash.
    role_series = {
        ".bo-ma": _MA_LINE_C,
        ".bo-edge": _BAND_EDGE_C,
        ".bo-squeeze": _SQUEEZE_HUE_C,
        ".bo-breakout": _BREAKOUT_HUE_C,
    }
    role_hc = leveled_colors(role_series, "high-contrast")
    txt_rows = "".join(f"{sel}-txt{{fill:{hexv} !important;}}" for sel, hexv in role_hc.items())
    adaptive = os_adaptive_style(role_series, role="stroke", extra_contrast=txt_rows)
    # Light $5 gridlines are strokes the ink map misses; darken them for a dark
    # ground. The blue volatility band and its teal edges are data hues, left be.
    dark = os_dark_style(extra='[stroke="#EFEFF2"]{stroke:#2A2A2C;}')
    parts.append("<style>" + adaptive + dark + "</style>")

    # ---- assemble --------------------------------------------------------- #
    parts.append("<defs>" + "".join(defs) + "</defs>")
    parts.extend(grid)
    parts.extend(band_group)
    parts.extend(lines)
    parts.extend(ann)
    parts.extend(markers)
    parts.extend(ax_labels)
    parts.extend(axis_bits)
    parts.extend(end_labels)
    parts.extend(legend)
    parts.extend(tips)
    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_bollinger",
        description="Write the house-style Bollinger-band SVG example.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--seed", type=int, default=11, help="Random seed for the sample data."
    )
    parser.add_argument(
        "--window", type=int, default=20, help="Rolling window in trading days."
    )
    parser.add_argument(
        "--sigma", type=float, default=2.0, help="Band half-width in standard deviations."
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the figure (default: self-contained).",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal",
            "high-contrast",
            "monochrome",
            "deuteranopia",
            "protanopia",
            "tritanopia",
        ),
        default="universal",
        help="Palette accessibility level (default: universal, the CVD-safe standard).",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to disk."""
    args = _build_parser().parse_args(argv)
    data = _sample_prices(seed=args.seed)
    svg = build_svg(
        data,
        window=args.window,
        n_sigma=args.sigma,
        mode=args.mode,
        accessibility=args.accessibility,
    )
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

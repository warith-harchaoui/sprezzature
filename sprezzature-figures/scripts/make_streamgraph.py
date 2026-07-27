#!/usr/bin/env python3
"""Generate a publication-quality *streamgraph* (themeRiver) as a static SVG.

A streamgraph is a stacked area chart floated onto a *wiggle* baseline: instead
of piling every band on a flat zero line, the whole stack is centred around a
meandering silhouette that minimises the visual "wiggle" of the inner bands. The
payoff is a flowing, river-like picture where each band's **thickness** is its
value and the reader can follow one colour ribbon across time without the
distortion a fixed baseline forces onto the upper bands. It is the natural chart
for part-to-whole quantities that morph over time — market share, genre
popularity, ticket categories.

This module builds the SVG string **by hand** (no matplotlib / seaborn /
plotly, no Vega): it computes the Lee-Byron *wiggle* baseline, lays each genre
as a stacked ribbon with smooth Catmull-Rom spline edges, paints them in the
Apple-system house palette, and drops a bold label straight onto each band at
its thickest, most stable point. Native ``<title>`` tooltips give per-genre
peak-share detail on hover — no JavaScript.

The example data is illustrative: recorded-music streaming share by genre from
2000 to 2024, the two-decade arc where Hip-Hop / R&B overtakes Rock as the
format shifts from the compact disc to on-demand streaming — a story the river
tells at a glance, because the Hip-Hop ribbon swells while the Rock ribbon
thins.

Usage
-----
    python make_streamgraph.py                 # writes the house SVG
    python make_streamgraph.py --out other.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc classes,
generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

# Shared, output-identical SVG primitive (XML-metacharacter escape).
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _labels import best_text_colour  # noqa: E402
from _style import forced_color_patterns, leveled_colors, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import catmull_rom_beziers, fmt_compact, xml_escape  # noqa: E402
from _render import write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# --------------------------------------------------------------------------- #
# One shared type scale for the whole figure, so nothing drifts.              #
# In-river band names and the right-margin legend names share a size; the two #
# secondary (mono, share-value) sizes match too — label harmony by construction.
_FS_TITLE = 31       # headline
_FS_SUB = 17.5       # subtitle lines
_FS_LABEL = 18       # band name + legend name (primary label size)
_FS_VALUE = 13.5     # share value under a label (mono)
_FS_AXIS = 14        # year ticks (mono)
_FS_AXIS_TITLE = 16  # "Year"

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "streamgraph.svg"
)

# House-style tokens (mirrors _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"


# --------------------------------------------------------------------------- #
# Illustrative data                                                            #
# --------------------------------------------------------------------------- #
def _sample_genre_share() -> Tuple[np.ndarray, List[str], np.ndarray]:
    """Synthesise recorded-music streaming volume by genre, 2000-2024.

    Two forces shape the river. First, **total** on-demand streaming explodes
    from a near-flat trickle in the compact-disc era to a torrent after the
    mid-2010s, so the whole river swells left→right — the wiggle baseline turns
    that growth into a widening silhouette. Second, the **mix** shifts: Rock
    erodes from format-era dominance, Hip-Hop / R&B climbs to overtake it, Pop
    stays broad, Latin surges late, Country holds steady, and Dance / Electronic
    peaks mid-decade then settles.

    Values are billions of on-demand audio streams per year — an absolute
    quantity, so band thickness carries both the mix and the market's growth.

    Returns
    -------
    years : numpy.ndarray
        The 25 sample years, 2000..2024 inclusive.
    genres : list of str
        Genre labels, ordered inside-out for a calm wiggle baseline (the
        steadiest, thickest bands sit near the centre of the river).
    volume : numpy.ndarray
        A ``(n_genres, n_years)`` array of streams (billions) per genre-year.
    """
    years = np.arange(2000, 2025)
    t = (years - 2000) / 24.0  # 0..1 progress across the window

    def _logistic(lo: float, hi: float, mid: float, steep: float) -> np.ndarray:
        """A smooth S-curve from ``lo`` to ``hi``, half-way at progress ``mid``."""
        return lo + (hi - lo) / (1.0 + np.exp(-steep * (t - mid)))

    def _bump(peak_t: float, width: float, height: float) -> np.ndarray:
        """A gentle Gaussian bump peaking at progress ``peak_t``."""
        return height * np.exp(-0.5 * ((t - peak_t) / width) ** 2)

    # Per-genre *share of the mix* (0..1-ish, re-normalised below). Ordering is
    # the inside-out stacking order: steady, thick bands (Pop, Hip-Hop, Rock)
    # sit at the river core; volatile thin bands ride the edges — this keeps the
    # wiggle baseline calm and every ribbon legible.
    mix: Dict[str, np.ndarray] = {
        "Pop":               22.0 + _bump(0.55, 0.5, 4.0),
        "Hip-Hop / R&B":     _logistic(15.0, 34.0, 0.5, 6.5),
        "Rock":              _logistic(30.0, 11.0, 0.42, 6.0),
        "Latin":             5.0 + _logistic(0.0, 10.0, 0.74, 9.0),
        "Country":           9.0 + _bump(0.5, 0.6, 1.5),
        "Dance / Electronic": 4.0 + _bump(0.62, 0.22, 6.5),
    }

    genres = list(mix.keys())
    frac = np.vstack([mix[g] for g in genres])         # (n_genres, n_years)
    frac = np.clip(frac, 0.4, None)
    frac = frac / frac.sum(axis=0, keepdims=True)       # each column sums to 1

    # Total on-demand streaming, billions/year: a slow trickle in the CD era,
    # a logistic surge as streaming takes over through the 2010s, still climbing.
    # Midpoint ~2013, gentle steepness so the swell fills the canvas rather than
    # snapping open at the right edge.
    total = 6.0 + _logistic(0.0, 116.0, 0.54, 6.0)      # ~6b → ~122b

    volume = frac * total                               # (n_genres, n_years)
    return years, genres, volume


# --------------------------------------------------------------------------- #
# Wiggle baseline (Lee-Byron ThemeRiver)                                       #
# --------------------------------------------------------------------------- #
def _wiggle_baseline(shares: np.ndarray) -> np.ndarray:
    """Compute the Lee-Byron *wiggle* baseline g0(t) for a stacked area.

    The wiggle baseline is the offset that minimises the sum of squared slopes
    of the inner layer boundaries — the classic streamgraph "silhouette" that
    stops the top bands from swinging wildly just because the ones below them
    moved. This is the standard closed form from Byron & Wattenberg (2008): for
    ``n`` layers indexed ``i = 0..n-1`` from the bottom,

        g0(t) = -1/(n+1) * sum_i (n - i) * f_i(t)

    where ``f_i`` is layer ``i``'s thickness at time ``t``.

    Parameters
    ----------
    shares : numpy.ndarray
        A ``(n_layers, n_years)`` array of layer thicknesses (percentage share).

    Returns
    -------
    numpy.ndarray
        The baseline y-offset per year, length ``n_years`` — the bottom edge of
        the lowest layer in data units.
    """
    n = shares.shape[0]
    weights = np.arange(n, 0, -1).reshape(-1, 1)  # (n - i) for i = 0..n-1
    return -(weights * shares).sum(axis=0) / (n + 1)


# --------------------------------------------------------------------------- #
# Colour palette                                                               #
# --------------------------------------------------------------------------- #
def _band_colors(n: int, accessibility: str = "universal") -> List[str]:
    """Return ``n`` well-separated house-palette hues for the river bands.

    Hand-picked from the Apple-system palette so neighbouring ribbons never sit
    colour-on-colour: a warm-to-cool spread with enough hue distance that the
    boundaries read even where two thick bands touch. Deuteranope-checked
    ordering (Blue / Orange / Teal carry the load; Red and Green are never
    adjacent).

    These six ribbon fills are a *categorical* set (one hue per genre), so they
    answer to the accessibility level: they are collected into a ``{name: hex}``
    map and wrapped with :func:`_style.leveled_colors`. ``universal`` (default)
    is the identity, so the shipped SVG is byte-for-byte unchanged; every other
    level remaps these fills through the sprezzature-colors engine.

    Parameters
    ----------
    n : int
        Number of bands to colour.
    accessibility : str, optional
        Palette accessibility level (``"universal"`` by default). Forwarded to
        :func:`_style.leveled_colors`.

    Returns
    -------
    list of str
        ``n`` ``#RRGGBB`` strings.
    """
    # Fills are chosen so *white* on-band text wins cleanly on every ribbon: the
    # two that used to sit at the white/ink knife-edge (mid-Gray, saturated
    # Green) are deepened just enough to be unambiguous while keeping their hue
    # identity. Orange stays bright because it takes *ink* text (dark on orange
    # is high-contrast). Deuteranope-checked ordering; Red and Green never touch.
    base = {
        "Pop":         "#007AFF",  # Blue        (white text)
        "Hip-Hop/R&B": "#FF9500",  # Orange      (ink text — dark on orange)
        "Rock":        "#5C5C61",  # Slate gray  (deepened so white text reads)
        "Latin":       "#248A3D",  # Deep green  (deepened so white text reads)
        "Country":     "#8A6A46",  # Deep brown  (white text)
        "Dance/Elec":  "#AF52DE",  # Purple      (white text)
    }
    ramp = list(leveled_colors(base, accessibility).values())
    if n <= len(ramp):
        return ramp[:n]
    out: List[str] = []
    while len(out) < n:
        out.extend(ramp)
    return out[:n]


def _lerp_hex(a: str, b: str, t: float) -> str:
    """Linearly interpolate two ``#RRGGBB`` colours in sRGB space."""
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    r = round(ar + (br - ar) * t)
    g = round(ag + (bg - ag) * t)
    bl = round(ab + (bb - ab) * t)
    return f"#{r:02X}{g:02X}{bl:02X}"


# --------------------------------------------------------------------------- #
# Geometry helpers                                                             #
# --------------------------------------------------------------------------- #
# Compact path-data formatter, now shared in _svg (byte-identical to the old
# private ``_fmt``); the local name is kept so the ~21 call sites are untouched.
_fmt = fmt_compact


def _catmull_rom(pts: Sequence[Tuple[float, float]], tension: float = 6.0) -> str:
    """Catmull-Rom cubic-Bezier ``C`` commands flowing through ``pts``.

    Thin wrapper over :func:`_svg.catmull_rom_beziers` that pins the local
    :func:`_fmt` formatter, so the emitted string is identical to the old
    inline copy while the spline maths lives in the shared module. See that
    function for the full contract.

    Parameters
    ----------
    pts : sequence of (float, float)
        Edge sample points in pixel coordinates.
    tension : float, optional
        Catmull-Rom denominator; ``6`` is the standard uniform spline.

    Returns
    -------
    str
        A run of SVG ``C`` path commands (a plain ``L`` fallback if < 3 points).
    """
    return catmull_rom_beziers(pts, _fmt, tension)


def _ribbon_path(
    top: Sequence[Tuple[float, float]],
    bottom: Sequence[Tuple[float, float]],
) -> str:
    """Build one closed river-band path from its top and bottom edge samples.

    The top edge flows left→right as a smooth spline; the bottom edge flows
    right→left (reversed) as a smooth spline; the two are joined into one closed
    ribbon.

    Parameters
    ----------
    top : sequence of (float, float)
        Upper edge points, left→right.
    bottom : sequence of (float, float)
        Lower edge points, left→right (this function reverses them).

    Returns
    -------
    str
        A complete SVG path ``d`` string for the filled band.
    """
    d = f"M{_fmt(top[0][0])},{_fmt(top[0][1])}"
    d += _catmull_rom(top)
    rev = list(reversed(bottom))
    d += f" L{_fmt(rev[0][0])},{_fmt(rev[0][1])}"
    d += _catmull_rom(rev)
    d += " Z"
    return d


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def build_svg(
    years: np.ndarray,
    genres: List[str],
    volume: np.ndarray,
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full streamgraph SVG document as a string.

    Parameters
    ----------
    years : numpy.ndarray
        Sample years (x-axis).
    genres : list of str
        Genre labels, bottom-to-top stacking order.
    volume : numpy.ndarray
        ``(n_genres, n_years)`` streaming volume (billions of streams) per
        genre-year. Band thickness is this quantity; per-year shares for the
        labels are derived from the column totals.
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level for the categorical ribbon fills, forwarded
        to :func:`_band_colors`. ``"universal"`` (default) leaves the fills
        unchanged; other levels remap them through the sprezzature-colors engine.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    # ---- canvas geometry -------------------------------------------------- #
    # Poster-scale: the river wants width (25 yearly samples) and enough height
    # that even the thin edge bands read as ribbons, not hairlines.
    width, height = 1280, 800
    m_left, m_right = 60, 210
    m_top, m_bottom = 172, 96
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    n_years = len(years)
    n_genres = len(genres)

    # Per-year share of the mix (percent) — used only for labels, not geometry.
    col_total = volume.sum(axis=0, keepdims=True)
    shares_pct = 100.0 * volume / col_total       # (n_genres, n_years)

    # ---- baseline + cumulative stack, in data units ----------------------- #
    g0 = _wiggle_baseline(volume)                 # bottom of lowest layer
    lowers = np.zeros_like(volume)                # (n_genres, n_years)
    uppers = np.zeros_like(volume)
    running = g0.copy()
    for i in range(n_genres):
        lowers[i] = running
        running = running + volume[i]
        uppers[i] = running

    # Value span across the whole river, for a symmetric, headroom-safe y-map.
    v_lo = float(lowers.min())
    v_hi = float(uppers.max())
    v_pad = (v_hi - v_lo) * 0.06                   # 6 % vertical headroom
    v_lo -= v_pad
    v_hi += v_pad

    def x_of(yi: int) -> float:
        """Map a year index (0..n_years-1) to a pixel column."""
        return m_left + yi / (n_years - 1) * plot_w

    def y_of(v: float) -> float:
        """Map a data value (share offset) to a pixel row (y grows downward)."""
        return m_top + (v_hi - v) / (v_hi - v_lo) * plot_h

    colors = _band_colors(n_genres, accessibility)

    parts: List[str] = []
    defs: List[str] = []

    # ---- header ----------------------------------------------------------- #
    title = "Hip-Hop overtakes Rock as streaming reshapes the charts"
    parts.append(
        f'<svg role="img" aria-label="{title}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}">'
    )
    parts.append(
        f"<title>{title}</title>"
        f"<desc>Streamgraph on a wiggle baseline: recorded-music streaming "
        f"share by genre, 2000 to 2024. Each ribbon's thickness is its share of "
        f"listening that year. The Hip-Hop / R&amp;B ribbon swells to become the "
        f"widest band while the Rock ribbon thins, as the format shifts from the "
        f"compact disc to on-demand streaming. Illustrative data.</desc>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="18" fill="{_BG}"/>')
    parts.append(
        f'<text x="{_fmt(m_left)}" y="66" font-size="{_FS_TITLE}" '
        f'font-weight="700" fill="{_INK}">{title}</text>'
    )
    parts.append(
        f'<text x="{_fmt(m_left)}" y="98" font-size="{_FS_SUB}" '
        f'fill="{_SECONDARY}">'
        f"Share of recorded-music streaming by genre, band thickness = share of "
        f"listening that year</text>"
    )
    parts.append(
        f'<text x="{_fmt(m_left)}" y="121" font-size="{_FS_SUB}" '
        f'fill="{_SECONDARY}">Illustrative data, 2000&#8211;2024</text>'
    )

    # ---- faint decade gridlines (behind the river) ------------------------ #
    grid_top = m_top - 14
    grid_bot = m_top + plot_h + 14
    for yr in (2000, 2005, 2010, 2015, 2020, 2024):
        yi = int(yr - years[0])
        gx = x_of(yi)
        parts.append(
            f'<line x1="{_fmt(gx)}" y1="{_fmt(grid_top)}" x2="{_fmt(gx)}" '
            f'y2="{_fmt(grid_bot)}" stroke="#F0F0F3" stroke-width="1.4"/>'
        )

    # ---- the river: one filled ribbon per genre --------------------------- #
    yidx = list(range(n_years))
    river: List[str] = ["<g>"]
    for i, genre in enumerate(genres):
        top = [(x_of(yi), y_of(uppers[i, yi])) for yi in yidx]
        bottom = [(x_of(yi), y_of(lowers[i, yi])) for yi in yidx]
        d = _ribbon_path(top, bottom)
        # A whisper-thin white seam between bands sharpens every boundary
        # without a heavy stroke — pure fills, no colour-on-colour ambiguity.
        river.append(
            f'<path class="river-{i}" d="{d}" fill="{colors[i]}" '
            f'fill-opacity="0.96" '
            f'stroke="#FFFFFF" stroke-width="1.1" stroke-opacity="0.85">'
            f"<title>{_genre_tip(genre, years, shares_pct[i])}</title></path>"
        )
    river.append("</g>")

    # ---- on-band labels at each ribbon's thickest, calmest point ---------- #
    band_labels: List[str] = []
    for i, genre in enumerate(genres):
        thick = uppers[i] - lowers[i]                 # band thickness per year
        # Prefer a label spot where the band is thick AND its centre is not
        # steeply sloped, so text sits flat inside the ribbon.
        centre = (uppers[i] + lowers[i]) / 2.0
        slope = np.abs(np.gradient(centre))
        score = thick - 5.5 * slope
        # Keep away from the very edges so the label never clips.
        score[:2] = -1e9
        score[-2:] = -1e9
        yi = int(np.argmax(score))
        cx = x_of(yi)
        cy = y_of(float(centre[yi]))
        band_h_px = abs(y_of(float(uppers[i, yi])) - y_of(float(lowers[i, yi])))
        # Contrast text colour straight from the band fill: white on the
        # saturated ribbons, ink on the light ones (Orange). Shared helper, so
        # the rule matches every other figure in the gallery.
        ink = best_text_colour(colors[i])
        # Two-line label when the band is tall enough: genre name over its share
        # that year; otherwise the name alone, optically centred. Both lines use
        # the one shared type scale so sizes never drift band to band.
        share_here = float(shares_pct[i, yi])
        two_line = band_h_px > 40
        band_labels.append(
            f'<text x="{_fmt(cx)}" y="{_fmt(cy - (5 if two_line else -6))}" '
            f'text-anchor="middle" font-size="{_FS_LABEL}" font-weight="700" '
            f'fill="{ink}">{xml_escape(genre)}</text>'
        )
        if two_line:
            band_labels.append(
                f'<text x="{_fmt(cx)}" y="{_fmt(cy + 18)}" text-anchor="middle" '
                f'font-size="{_FS_VALUE}" font-family="{_MONO}" fill="{ink}" '
                f'fill-opacity="0.85">{share_here:.0f}% in {int(years[yi])}</text>'
            )

    # ---- end-of-river leader labels (right margin, ink on white) ---------- #
    # A calm side-aware legend: each genre named again at the river's right end,
    # next to its ribbon, so the colour key sits outside the plot in clean ink.
    end_labels: List[str] = []
    last = n_years - 1
    # Sort by vertical position at the last year to stack labels without overlap.
    order = sorted(range(n_genres), key=lambda i: (uppers[i, last] + lowers[i, last]) / 2.0)
    label_x = m_left + plot_w + 20
    used_y: List[float] = []
    min_gap = 34.0
    for i in order:
        centre = float((uppers[i, last] + lowers[i, last]) / 2.0)
        ly = y_of(centre)
        # Nudge down if too close to the previous label (simple de-collision).
        for uy in used_y:
            if abs(ly - uy) < min_gap:
                ly = uy + min_gap
        used_y.append(ly)
        share_last = float(shares_pct[i, last])
        end_labels.append(
            f'<rect class="river-{i}" x="{_fmt(label_x)}" y="{_fmt(ly - 9)}" '
            f'width="15" height="15" '
            f'rx="4" fill="{colors[i]}"/>'
        )
        end_labels.append(
            f'<text x="{_fmt(label_x + 22)}" y="{_fmt(ly - 1)}" font-size="15" '
            f'font-weight="600" fill="{_INK}">{xml_escape(genres[i])}</text>'
        )
        end_labels.append(
            f'<text x="{_fmt(label_x + 22)}" y="{_fmt(ly + 16)}" '
            f'font-size="{_FS_VALUE}" font-family="{_MONO}" fill="{_SECONDARY}">'
            f"{share_last:.0f}% in 2024</text>"
        )

    # ---- x-axis line + year tick labels ----------------------------------- #
    axis_y = m_top + plot_h + 30
    axis_bits: List[str] = []
    axis_bits.append(
        f'<line x1="{_fmt(m_left)}" y1="{_fmt(axis_y)}" '
        f'x2="{_fmt(m_left + plot_w)}" y2="{_fmt(axis_y)}" '
        f'stroke="{_INK}" stroke-width="1.6"/>'
    )
    for yr in (2000, 2005, 2010, 2015, 2020, 2024):
        yi = int(yr - years[0])
        gx = x_of(yi)
        axis_bits.append(
            f'<line x1="{_fmt(gx)}" y1="{_fmt(axis_y)}" x2="{_fmt(gx)}" '
            f'y2="{_fmt(axis_y + 7)}" stroke="{_INK}" stroke-width="1.6"/>'
        )
        axis_bits.append(
            f'<text x="{_fmt(gx)}" y="{_fmt(axis_y + 28)}" text-anchor="middle" '
            f'font-size="{_FS_AXIS}" font-family="{_MONO}" fill="{_SECONDARY}">'
            f"{yr}</text>"
        )
    axis_bits.append(
        f'<text x="{_fmt(m_left + plot_w / 2)}" y="{_fmt(axis_y + 56)}" '
        f'text-anchor="middle" font-size="{_FS_AXIS_TITLE}" fill="{_INK}">'
        f"Year</text>"
    )

    # ---- OS-adaptive overrides (additive; default render byte-identical) --- #
    # The whole block lives inside @media queries, and this figure otherwise
    # ships no <style>, so with no OS preference active none of these rules
    # match and the raster is exactly what it always was. Under prefers-contrast
    # each genre ribbon (and its right-margin legend swatch) deepens to its
    # high-contrast hue via the sprezzature-colors engine, keeping the six bands
    # pairwise distinct where they touch. Forced colours are left to the browser
    # default: colour is the category key for a stacked river, and the ~4-colour
    # system palette cannot preserve six distinct ribbons, so blanking the fills
    # would destroy the encoding — the on-band text labels and the legend remain
    # the colour-independent fallback the browser default already respects.
    river_series = {f".river-{i}": colors[i] for i in range(n_genres)}
    # Forced colours (Windows High Contrast and kin): colour is the sole
    # per-band key for a stacked river, and the ~4-colour system palette cannot
    # preserve six distinct ribbons — a flat hand-off would merge every band into
    # one ink. Give each ribbon (and its right-margin legend swatch, which shares
    # the .river-{i} class) a distinct Canvas/CanvasText pattern (hatch, dots,
    # cross) so the six bands stay separable without colour. The pattern defs are
    # inert at the default render (referenced only inside the forced-colors media
    # query), so the shipped SVG is byte-for-byte unchanged.
    fcp_defs, fcp_style = forced_color_patterns(
        [f".river-{i}" for i in range(n_genres)], prefix="streamgraph-fcp"
    )
    # Additive OS dark-mode block: dark paper + inverted ink tiers. The saturated
    # genre ribbons read on dark and are left alone; the whisper-thin white seams
    # between them separate the coloured bands fine on either surface. No multiply
    # groups here, so no blend-mode flip.
    parts.append(
        "<style>\n"
        + os_adaptive_style(river_series, role="fill")
        + "\n"
        + fcp_style
        + "\n"
        + os_dark_style(screen_blend=False)
        + "\n</style>"
    )

    # ---- assemble --------------------------------------------------------- #
    parts.append("<defs>" + "".join(defs) + fcp_defs + "</defs>")
    parts.extend(river)
    parts.extend(band_labels)
    parts.extend(end_labels)
    parts.extend(axis_bits)
    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "".join(parts)


def _genre_tip(genre: str, years: np.ndarray, series: np.ndarray) -> str:
    """Build the native hover tooltip for one genre's ribbon.

    Parameters
    ----------
    genre : str
        Genre label.
    years : numpy.ndarray
        Sample years.
    series : numpy.ndarray
        This genre's share per year.

    Returns
    -------
    str
        A one-line summary: start share, end share, and peak-share year.
    """
    start = float(series[0])
    end = float(series[-1])
    pk = int(np.argmax(series))
    arrow = "rises" if end > start else "falls"
    return xml_escape(
        f"{genre}: {arrow} from {start:.0f}% in {int(years[0])} to "
        f"{end:.0f}% in {int(years[-1])} (peak {float(series[pk]):.0f}% "
        f"in {int(years[pk])})"
    )


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_streamgraph",
        description="Write the house-style streamgraph (themeRiver) SVG example.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="interactivity mode of the emitted SVG (default: self-contained)",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal", "high-contrast", "monochrome",
            "deuteranopia", "protanopia", "tritanopia",
        ),
        default="universal",
        help="palette accessibility level (default: universal, the CVD-safe standard)",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to disk."""
    args = _build_parser().parse_args(argv)
    years, genres, volume = _sample_genre_share()
    svg = build_svg(years, genres, volume, mode=args.mode, accessibility=args.accessibility)
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

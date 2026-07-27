#!/usr/bin/env python3
"""Generate a publication-quality *horizon chart* as a standalone static SVG.

A horizon chart is the space-efficient answer to "show me many dense time
series at once and let me still read each one". It takes the classic filled
area chart and (1) slices the value range into a few equal **bands**, (2)
paints each higher band in a more saturated shade of the same hue and
collapses them onto the same thin row, and (3) **folds** any negative excursion
up as a mirror-image area in a contrasting hue. The result packs the readable
punch of a tall area chart into a strip a few pixels high, so a whole fleet of
series stacks into one screen and outliers pop out by colour weight alone.

This module builds the SVG string **by hand** (no matplotlib / seaborn /
plotly, no Vega): it lays each series into its own banded row, paints the bands
as increasingly saturated house-palette blues (above baseline) and reds
(below), and adds native ``<title>`` hover tooltips — no JavaScript. A horizon
chart is a dense static comparison; motion adds nothing a still cannot already
show, so the whole picture is drawn fully at rest — every band is present the
instant the SVG loads. The colour weight of a row is a redundant channel on top
of vertical position, so the busiest node is obvious at a glance.

The example data is illustrative: hourly CPU utilisation across a small fleet
of database nodes over one day, plotted as the deviation from each node's own
daily mean — the framing horizon charts are made for, where a single saturated
red-then-dark-blue row instantly flags the node that swung hardest.

Usage
-----
    python make_horizon.py                 # writes the house SVG
    python make_horizon.py --out other.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc
classes, generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations
from _render import write_svg  # noqa: E402
from _svg import fmt_compact  # noqa: E402
from _style import os_dark_style  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

import argparse
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

import numpy as np

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "horizon.svg"
)

# House-style tokens (mirrors _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"

# Band anchor hues, drawn from the Apple-system palette. Positive excursions
# ride a Blue ramp (calm → deep), negative ones a Red ramp (mirror-folded).
# Within a horizon chart each *band* re-uses the row's baseline; the eye reads
# a taller stack of bands as a bigger value, reinforced by deeper saturation.
_POS_HUE = "#007AFF"    # Apple Blue  — above the row's own mean
_NEG_HUE = "#FF3B30"    # Apple Red   — below the row's own mean
_N_BANDS = 3            # bands per direction (the horizon-chart sweet spot)


# --------------------------------------------------------------------------- #
# Illustrative data                                                            #
# --------------------------------------------------------------------------- #
def _sample_fleet_cpu(seed: int = 11) -> Dict[str, np.ndarray]:
    """Synthesise a day of hourly CPU load for a small database fleet.

    Each node follows a common diurnal envelope (quiet overnight, a mid-morning
    ramp, a lunchtime dip, an afternoon peak) plus its own personality: one node
    carries a heavy nightly batch job, one runs hot all afternoon, the rest sit
    calmer. Values are percent CPU utilisation, sampled every hour.

    Parameters
    ----------
    seed : int, optional
        Seed for the random generator, for a reproducible figure.

    Returns
    -------
    dict of str to numpy.ndarray
        Ordered ``{node_label: hourly_utilisation}``, 24 samples each. Order is
        the row order printed top-to-bottom, busiest-swinger first.
    """
    rng = np.random.default_rng(seed)
    hours = np.arange(24)

    # Shared diurnal envelope (0..1): overnight trough, mid-morning + afternoon
    # peaks. Built from two Gaussians on the hour-of-day.
    def _bell(centre: float, width: float) -> np.ndarray:
        return np.exp(-0.5 * ((hours - centre) / width) ** 2)

    envelope = 0.55 * _bell(10.5, 2.6) + 0.85 * _bell(15.5, 2.4)

    # Per-node recipes: (label, base%, envelope-gain, extra-signal fn).
    def _nightly_batch() -> np.ndarray:
        # A heavy ETL job spikes utilisation hard from 02:00–04:00 — the
        # sharp, isolated fold that is this figure's headline.
        return 60.0 * _bell(3.0, 1.0)

    def _afternoon_hot() -> np.ndarray:
        # Sustained analytics load that never quite cools down after lunch.
        return 16.0 * _bell(17.0, 4.5)

    recipes: List[Tuple[str, float, float, np.ndarray]] = [
        ("db-01  batch",   30.0, 24.0, _nightly_batch()),
        ("db-02  analytics", 34.0, 30.0, _afternoon_hot()),
        ("db-03  primary",  30.0, 28.0, np.zeros(24)),
        ("db-04  replica",  22.0, 24.0, np.zeros(24)),
        ("db-05  reporting", 18.0, 22.0, 12.0 * _bell(9.0, 1.4)),
        ("db-06  standby",  12.0, 14.0, np.zeros(24)),
    ]

    out: Dict[str, np.ndarray] = {}
    for label, base, gain, extra in recipes:
        noise = rng.normal(0.0, 2.2, size=24)
        series = base + gain * envelope + extra + noise
        out[label] = np.clip(series, 0.0, 100.0)
    return out


# --------------------------------------------------------------------------- #
# Colour ramps                                                                 #
# --------------------------------------------------------------------------- #
def _lerp_hex(a: str, b: str, t: float) -> str:
    """Linearly interpolate two ``#RRGGBB`` colours in sRGB space.

    Parameters
    ----------
    a, b : str
        Endpoint colours as ``#RRGGBB``.
    t : float
        Blend factor in ``[0, 1]`` (0 → ``a``, 1 → ``b``).

    Returns
    -------
    str
        The blended colour as ``#RRGGBB``.
    """
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    r = round(ar + (br - ar) * t)
    g = round(ag + (bg - ag) * t)
    bl = round(ab + (bb - ab) * t)
    return f"#{r:02X}{g:02X}{bl:02X}"


def _band_ramp(
    hue: str,
    n: int,
    *,
    tint: float = 0.62,
    shade: float = 0.28,
) -> List[str]:
    """Return ``n`` shades of one hue, pale → deep, for the horizon bands.

    The lowest band is a light tint (hue mixed toward white); the top band is
    the hue nudged darker, so a taller stack of bands reads as a bigger value.

    The ``tint`` and ``shade`` factors set where the ramp lives on the
    lightness axis. The two directions (above vs below the mean) use
    *different* windows so that a below-mean band is always darker than the
    same-magnitude above-mean band. That keeps the above/below sign readable
    in greyscale and for colour-blind viewers, where the blue and red hues
    would otherwise collapse to the same grey.

    Parameters
    ----------
    hue : str
        The anchor ``#RRGGBB`` (e.g. Apple Blue for positive excursions).
    n : int
        Number of bands.
    tint : float, optional
        White-mix for the palest band (higher = lighter band 0).
    shade : float, optional
        Black-mix for the deepest band (higher = darker top band).

    Returns
    -------
    list of str
        ``n`` ``#RRGGBB`` strings, band-0 (nearest baseline) first.
    """
    dark = _lerp_hex(hue, "#000000", shade)  # deepest band
    pale = _lerp_hex(hue, "#FFFFFF", tint)   # palest band
    shades: List[str] = []
    for i in range(n):
        t = i / max(1, n - 1)
        shades.append(_lerp_hex(pale, dark, t))
    return shades


# --------------------------------------------------------------------------- #
# Geometry helpers                                                             #
# --------------------------------------------------------------------------- #
def _smooth_top(pts: Sequence[tuple[float, float]], tension: float = 6.0) -> str:
    """Catmull-Rom cubic-Bezier ``C`` commands smoothing the band's top edge.

    The caller has already moved/lined to ``pts[0]``; this returns the curve
    commands that flow through every later point. End tangents are clamped to
    the terminal points so the curve neither drifts nor over-shoots off the
    ends. ``tension`` is the classic Catmull-Rom sixth (larger = flatter).

    Parameters
    ----------
    pts : sequence of (float, float)
        The top-edge sample points, in pixel coordinates.
    tension : float, optional
        Catmull-Rom denominator; ``6`` is the standard uniform spline.

    Returns
    -------
    str
        A run of SVG ``C`` path commands (empty if fewer than 2 points).
    """
    n = len(pts)
    if n < 3:
        return "".join(f" L{fmt_compact(x)},{fmt_compact(y)}" for x, y in pts[1:])
    seg: List[str] = []
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        c1x, c1y = p1[0] + (p2[0] - p0[0]) / tension, p1[1] + (p2[1] - p0[1]) / tension
        c2x, c2y = p2[0] - (p3[0] - p1[0]) / tension, p2[1] - (p3[1] - p1[1]) / tension
        seg.append(
            f" C{fmt_compact(c1x)},{fmt_compact(c1y)} {fmt_compact(c2x)},{fmt_compact(c2y)} {fmt_compact(p2[0])},{fmt_compact(p2[1])}"
        )
    return "".join(seg)


def _band_area_path(
    xs: Sequence[float],
    vals: Sequence[float],
    *,
    x_of: Callable[[float], float],
    row_top: float,
    row_h: float,
    band_lo: float,
    band_hi: float,
    v_max: float,
) -> str:
    """Build one clipped, mirrored horizon *band* area path for a row.

    The band is the slice of the (rectified) series between ``band_lo`` and
    ``band_hi``. Every band is drawn from the row's baseline (``row_top +
    row_h``) up to ``row_h`` at full band height, so bands stack visually on
    the same baseline — the horizon-chart fold. Clamping the series to the band
    window and re-scaling to the row height is what turns a tall area into a
    short, layered strip.

    Parameters
    ----------
    xs : sequence of float
        Sample x-positions in data units (hour index).
    vals : sequence of float
        Rectified magnitudes (always ``>= 0``) for this direction.
    x_of : callable
        Maps a data x to a pixel column.
    row_top : float
        Pixel y of the top of the row.
    row_h : float
        Pixel height the bands are drawn into (the *band* height, which is left
        deliberately shorter than the row's own slot so each strip breathes).
    band_lo, band_hi : float
        Value window this band covers, in data units.
    v_max : float
        The full-scale value that maps to ``row_h`` (one band's worth).

    Returns
    -------
    str
        An SVG path ``d`` string, or an empty string if the band is untouched.
    """
    baseline = row_top + row_h
    # Clamp each sample into this band, then normalise to [0, 1] of the band.
    clamped = [min(max(v - band_lo, 0.0), band_hi - band_lo) for v in vals]
    if max(clamped) <= 1e-6:
        return ""  # this band is never reached — skip it
    # Height of one band in pixels (all bands share the same row_h footprint).
    frac = [c / (band_hi - band_lo) for c in clamped]
    top = [(x_of(x), baseline - f * row_h) for x, f in zip(xs, frac)]
    x0 = x_of(xs[0])
    x1 = x_of(xs[-1])
    # Top edge as a smooth Catmull-Rom spline; the baseline edges stay straight.
    return (
        f"M{fmt_compact(x0)},{fmt_compact(baseline)} "
        f"L{fmt_compact(top[0][0])},{fmt_compact(top[0][1])}"
        + _smooth_top(top)
        + f" L{fmt_compact(x1)},{fmt_compact(baseline)} Z"
    )


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def build_svg(
    data: Dict[str, np.ndarray],
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full horizon-chart SVG document as a string.

    Parameters
    ----------
    data : dict of str to numpy.ndarray
        Ordered ``{node_label: hourly_utilisation}``; first item is the top row.
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"`` / ``"external"`` / ``"static"``). Defaults to
        ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level. Accepted for interface parity with the
        rest of the gallery, but a **documented no-op** here. The above/below
        sign rides two *diverging* single-hue ramps (blue above the mean, red
        below) whose two lightness windows are hand-tuned in :func:`_band_ramp`
        so a below-mean band is always darker than the same-magnitude
        above-mean band — that is what makes the sign readable in greyscale and
        under colour-vision deficiency. Passing the two anchors through
        :func:`_style.leveled_colors` (which re-spaces hues by lightness)
        collapses those windows: under ``"monochrome"`` the blue top band goes
        *darker* than the red top band, inverting the sign convention. The
        tuned ramp is already CVD-/greyscale-safe, so the level is deliberately
        not applied. Defaults to ``"universal"``.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    # ``accessibility`` is intentionally unused: the diverging above/below ramp
    # is already CVD-/greyscale-safe by construction, and re-spacing its anchors
    # by lightness would invert the sign convention (see the docstring). Naming
    # it keeps the CLI wiring uniform with the rest of the gallery.
    _ = accessibility
    # ---- canvas geometry -------------------------------------------------- #
    # Poster-scale: generous, readable at a glance. The horizon rows want
    # width (24 hourly samples) and a *tall* body so each banded strip has
    # real breathing room above and below rather than crowding its neighbours.
    width, height = 1180, 1180
    m_left, m_right = 210, 48
    m_top, m_bottom = 168, 104
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    labels = list(data.keys())
    n_rows = len(labels)
    hours = np.arange(24)

    # Plot the *deviation from each node's own daily mean* — the framing that
    # makes a horizon chart sing (every row is centred, so colour = swing).
    dev = {lbl: data[lbl] - float(np.mean(data[lbl])) for lbl in labels}

    # Common full-scale for one band, shared across rows so band colours are
    # comparable node-to-node. Use a rounded 95th-percentile of |deviation|.
    all_abs = np.concatenate([np.abs(dev[lbl]) for lbl in labels])
    scale = float(np.percentile(all_abs, 96))
    scale = max(5.0, np.ceil(scale / 5.0) * 5.0)  # e.g. 20% full-scale
    band_size = scale / _N_BANDS                  # value window per band

    def x_of(x: float) -> float:
        """Map an hour index (0..23) to a pixel column."""
        return m_left + x / 23.0 * plot_w

    # Row rhythm: give each series a generous vertical *slot*, then draw its
    # banded strip into only the lower ~62% of that slot. The empty upper
    # margin of every slot is the breathing room — bands never crowd the row
    # above, and each strip reads as its own airy panel.
    row_gap = 44.0
    slot_h = (plot_h - row_gap * (n_rows - 1)) / n_rows
    # The visible band height (baseline sits at the bottom of the slot).
    band_h = slot_h * 0.62
    # Keep the old name in scope for label maths below; band drawing uses band_h.
    row_h = band_h

    # Two lightness windows, deliberately non-overlapping, so the above/below
    # sign survives greyscale and colour-blindness: every "above the mean"
    # (blue) band is lighter than the "below the mean" (red) band of the same
    # magnitude. Within each direction the ramp still runs pale → deep, so a
    # taller band-stack still reads as a bigger swing.
    pos_shades = _band_ramp(_POS_HUE, _N_BANDS, tint=0.72, shade=0.02)  # lighter
    neg_shades = _band_ramp(_NEG_HUE, _N_BANDS, tint=0.34, shade=0.42)  # darker

    parts: List[str] = []
    defs: List[str] = []

    # ---- header ----------------------------------------------------------- #
    title = "db-01's nightly batch is the fleet's biggest CPU swing"
    parts.append(
        f'<svg role="img" aria-label="{title}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}">'
    )
    parts.append(
        f"<title>{title}</title>"
        f"<desc>Horizon chart: one banded, folded area row per database node. "
        f"Blue bands rise above each node's daily-mean CPU, red bands fall "
        f"below; deeper, taller colour means a bigger swing. db-01 shows a "
        f"deep blue spike overnight from a batch job.</desc>"
    )
    # OS-adaptive overrides (additive; every rule lives inside an @media query,
    # so the default render is byte-for-byte unchanged). This is a *perceptual*
    # figure (a folded blue-above / red-below lightness ramp), so under
    # prefers-contrast we only strengthen the STRUCTURE — the faint gridlines and
    # per-row baselines deepen to a firm grey, the secondary ink darkens toward
    # ink, and the x-axis thickens — without touching the band ramp itself
    # (re-spacing or recolouring it would de-tune the encoding).
    contrast_block = (
        "@media (prefers-contrast: more){"
        '[stroke="#EFEFF2"]{stroke:#9C9CA3;}'      # gridlines: firmer grey
        '[stroke="#D8D8DD"]{stroke:#6E6E73;}'       # row baselines: firmer grey
        '[stroke="#1D1D1F"]{stroke-width:2.4;}'     # x-axis: thicker frame
        f'[fill="{_SECONDARY}"]{{fill:#3A3A3C;}}'    # secondary ink: darker
        "}"
    )
    # Additive dark mode: flip paper + the two ink tiers, and lift the dark
    # axis / baseline strokes to the light ink. The blue-above / red-below band
    # ramp is perceptual and is left untouched — the bands read as light marks
    # on the dark ground.
    parts.append(
        "<style>"
        + contrast_block
        + os_dark_style(extra='[stroke="#1D1D1F"]{stroke:#F2F2F7;}')
        + "</style>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="18" fill="{_BG}"/>')
    parts.append(
        f'<text x="{fmt_compact(m_left - 210 + 42)}" y="62" font-size="30" '
        f'font-weight="700" fill="{_INK}">{title}</text>'
    )
    # Two-line subtitle so it never runs off the canvas.
    parts.append(
        f'<text x="{fmt_compact(m_left - 210 + 42)}" y="94" font-size="17" '
        f'fill="{_SECONDARY}">'
        f"Hourly CPU utilisation vs. each node&#8217;s own daily mean, "
        f"one horizon row per node</text>"
    )
    parts.append(
        f'<text x="{fmt_compact(m_left - 210 + 42)}" y="117" font-size="17" '
        f'fill="{_SECONDARY}">Illustrative data</text>'
    )

    # ---- vertical hour gridlines (light, behind rows) --------------------- #
    grid_top = m_top - 10
    grid_bot = m_top + plot_h + 10
    for h in range(0, 24, 6):
        gx = x_of(float(h))
        parts.append(
            f'<line x1="{fmt_compact(gx)}" y1="{fmt_compact(grid_top)}" x2="{fmt_compact(gx)}" '
            f'y2="{fmt_compact(grid_bot)}" stroke="#EFEFF2" stroke-width="1.4"/>'
        )

    # ---- rows ------------------------------------------------------------- #
    # No animation: a horizon chart is a dense static comparison, so every
    # band is drawn in full at rest — the picture is complete the instant the
    # SVG loads.
    reveal_group: List[str] = ["<g>"]
    for i, label in enumerate(labels):
        slot_top = m_top + i * (slot_h + row_gap)
        # Sink the band strip to the bottom of its slot so the breathing room
        # lands above it; bands are drawn into band_h from this row_top down.
        row_top = slot_top + (slot_h - band_h)
        series = dev[label]
        pos_vals = [max(v, 0.0) for v in series]   # above the row mean
        neg_vals = [max(-v, 0.0) for v in series]  # below the row mean

        # Faint zero baseline for the row (reads as the node's own mean).
        base_y = row_top + row_h
        reveal_group.append(
            f'<line x1="{fmt_compact(m_left)}" y1="{fmt_compact(base_y)}" '
            f'x2="{fmt_compact(m_left + plot_w)}" y2="{fmt_compact(base_y)}" '
            f'stroke="#D8D8DD" stroke-width="1.2"/>'
        )

        # Positive bands, pale → deep, all stacked on the same baseline.
        for b in range(_N_BANDS):
            d = _band_area_path(
                hours, pos_vals, x_of=x_of, row_top=row_top, row_h=row_h,
                band_lo=b * band_size, band_hi=(b + 1) * band_size, v_max=scale,
            )
            if d:
                reveal_group.append(
                    f'<path d="{d}" fill="{pos_shades[b]}" '
                    f'fill-opacity="0.95" stroke="none"/>'
                )
        # Negative bands (folded up as a mirror in red).
        for b in range(_N_BANDS):
            d = _band_area_path(
                hours, neg_vals, x_of=x_of, row_top=row_top, row_h=row_h,
                band_lo=b * band_size, band_hi=(b + 1) * band_size, v_max=scale,
            )
            if d:
                reveal_group.append(
                    f'<path d="{d}" fill="{neg_shades[b]}" '
                    f'fill-opacity="0.95" stroke="none"/>'
                )

        # Hover tooltip: peak swing above / below the mean, no JavaScript.
        peak_up = float(np.max(series))
        peak_dn = float(np.min(series))
        peak_hour = int(np.argmax(np.abs(series)))
        tip = (
            f"{label.split('  ')[0]}: peaks +{peak_up:.0f} pts above / "
            f"{peak_dn:.0f} pts below its {float(np.mean(data[label])):.0f}% "
            f"daily mean, biggest swing at {peak_hour:02d}:00"
        )
        # Transparent hit-rect over the whole slot carries the native tooltip.
        reveal_group.append(
            f'<rect x="{fmt_compact(m_left)}" y="{fmt_compact(slot_top)}" '
            f'width="{fmt_compact(plot_w)}" height="{fmt_compact(slot_h)}" '
            f'fill="transparent"><title>{tip}</title></rect>'
        )

    reveal_group.append("</g>")

    # ---- row labels (outside the clip so they are always visible) --------- #
    row_labels: List[str] = []
    for i, label in enumerate(labels):
        slot_top = m_top + i * (slot_h + row_gap)
        row_top = slot_top + (slot_h - band_h)
        node, role = label.split("  ", 1)
        # Centre the label on the band strip (its visual centre of mass).
        cy = row_top + band_h / 2
        row_labels.append(
            f'<text x="{fmt_compact(m_left - 22)}" y="{fmt_compact(cy - 2)}" '
            f'text-anchor="end" font-size="18" font-weight="600" '
            f'font-family="{_MONO}" fill="{_INK}">{node}</text>'
        )
        row_labels.append(
            f'<text x="{fmt_compact(m_left - 22)}" y="{fmt_compact(cy + 18)}" '
            f'text-anchor="end" font-size="14" fill="{_SECONDARY}">{role}</text>'
        )

    # ---- x-axis line + hour tick labels + title --------------------------- #
    axis_y = m_top + plot_h + 26
    axis_bits: List[str] = []
    axis_bits.append(
        f'<line x1="{fmt_compact(m_left)}" y1="{fmt_compact(axis_y)}" '
        f'x2="{fmt_compact(m_left + plot_w)}" y2="{fmt_compact(axis_y)}" '
        f'stroke="{_INK}" stroke-width="1.6"/>'
    )
    for h in range(0, 24, 3):
        gx = x_of(float(h))
        axis_bits.append(
            f'<text x="{fmt_compact(gx)}" y="{fmt_compact(axis_y + 24)}" text-anchor="middle" '
            f'font-size="14" font-family="{_MONO}" fill="{_SECONDARY}">'
            f"{h:02d}:00</text>"
        )
    axis_bits.append(
        f'<text x="{fmt_compact(m_left + plot_w / 2)}" y="{fmt_compact(axis_y + 52)}" '
        f'text-anchor="middle" font-size="17" fill="{_INK}">'
        f"Hour of day</text>"
    )

    # ---- legend: band ramp swatches (above/below the mean) ---------------- #
    legend: List[str] = []
    lx = m_left
    ly = 128.0
    sw = 22.0
    sh = 16.0
    legend.append(
        f'<text x="{fmt_compact(lx)}" y="{fmt_compact(ly)}" font-size="15" '
        f'fill="{_SECONDARY}">below mean</text>'
    )
    # Red bands, deep → pale, reading toward the baseline.
    cx = lx + 108
    swy = ly - sh + 2
    for b in reversed(range(_N_BANDS)):
        legend.append(
            f'<rect x="{fmt_compact(cx)}" y="{fmt_compact(swy)}" width="{fmt_compact(sw)}" '
            f'height="{fmt_compact(sh)}" rx="3" fill="{neg_shades[b]}"/>'
        )
        cx += sw + 3
    cx += 10
    # Blue bands, pale → deep, away from the baseline.
    for b in range(_N_BANDS):
        legend.append(
            f'<rect x="{fmt_compact(cx)}" y="{fmt_compact(swy)}" width="{fmt_compact(sw)}" '
            f'height="{fmt_compact(sh)}" rx="3" fill="{pos_shades[b]}"/>'
        )
        cx += sw + 3
    legend.append(
        f'<text x="{fmt_compact(cx + 8)}" y="{fmt_compact(ly)}" font-size="15" '
        f'fill="{_SECONDARY}">above mean (deeper = bigger swing)</text>'
    )

    # ---- assemble --------------------------------------------------------- #
    parts.append("<defs>" + "".join(defs) + "</defs>")
    parts.extend(legend)
    parts.extend(reveal_group)
    parts.extend(row_labels)
    parts.extend(axis_bits)
    parts.append(fullscreen_control(width, height, mode))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_horizon",
        description="Write the house-style horizon-chart SVG example.",
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
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="interactivity mode of the emitted SVG (default: self-contained).",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal", "high-contrast", "monochrome",
            "deuteranopia", "protanopia", "tritanopia",
        ),
        default="universal",
        help="palette accessibility level (default: universal, the CVD-safe standard).",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to disk."""
    args = _build_parser().parse_args(argv)
    data = _sample_fleet_cpu(seed=args.seed)
    svg = build_svg(data, mode=args.mode, accessibility=args.accessibility)
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

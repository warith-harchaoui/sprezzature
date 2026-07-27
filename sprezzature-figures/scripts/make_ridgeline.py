#!/usr/bin/env python3
"""Generate a publication-quality *ridgeline* (joyplot) figure as a standalone SVG.

A ridgeline plot stacks one kernel-density curve per group along a shared
horizontal axis, offsetting each curve vertically so a reader can scan the
silhouette top-to-bottom to see how a whole distribution (not just its mean)
shifts from group to group. It is the R ``ggridges`` / matplotlib ``joypy``
/ seaborn ``FacetGrid`` KDE idiom.

This module builds the SVG string **by hand** (no matplotlib / seaborn /
plotly, no Vega): it estimates each group's density with a Gaussian kernel
(numpy only), lays the curves out on a shared axis, and paints them as
filled paths in the front-* house style — Roboto type, the Apple-system
palette, ink ``#1D1D1F`` on a white ground, rounded framing. Each ridge
sits in its **own fully separated lane** (no vertical overlap) and gets its
**own distinct house-palette hue**, so the stack reads as a smooth colour
progression down the page. A per-curve ``<title>`` gives a native hover
tooltip (median + spread) with no JavaScript.

The example data is illustrative: the daily-high-temperature distribution
of a temperate city, one ridge per month, telling the seasonal-swing story
that ridgelines are made for.

Usage
-----
    python make_ridgeline.py                 # writes the house SVG
    python make_ridgeline.py --out other.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc
classes, generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations
from _interactive import fullscreen_control  # noqa: E402
from _render import write_svg  # noqa: E402
from _svg import fmt_compact  # noqa: E402
from _style import leveled_colors, os_adaptive_style, os_dark_style  # noqa: E402

import argparse
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "ridgeline.svg"
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
def _sample_monthly_highs(seed: int = 7) -> Dict[str, np.ndarray]:
    """Synthesise a year of daily-high temperatures, one sample per month.

    Each month is drawn from a normal whose mean follows a smooth seasonal
    cosine (coldest in January, warmest in July) and whose spread is a touch
    wider in the shoulder seasons — the shape a real temperate-city record
    shows. Values are in degrees Celsius.

    Parameters
    ----------
    seed : int, optional
        Seed for the random generator, for a reproducible figure.

    Returns
    -------
    dict of str to numpy.ndarray
        Ordered ``{month_name: samples}`` from December (top of the stack)
        down to January (bottom), so the printed ridge reads winter→winter.
    """
    rng = np.random.default_rng(seed)
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    # Seasonal mean: cosine peaking in July (month index 6), 4 C ↔ 30 C swing.
    out: Dict[str, np.ndarray] = {}
    for i, name in enumerate(months):
        # phase = 0 in July (i = 6): cos = 1 → warmest; January → coldest.
        phase = 2.0 * np.pi * (i - 6) / 12.0
        mean = 17.0 + 13.0 * np.cos(phase)          # ~4 C (Jan) … 30 C (Jul)
        spread = 3.0 + 1.4 * abs(np.sin(phase))     # wider in the shoulders
        out[name] = rng.normal(mean, spread, size=200)
    # Top-of-stack first: December down to January.
    return {name: out[name] for name in reversed(months)}


# --------------------------------------------------------------------------- #
# Density estimation (numpy-only Gaussian KDE)                                 #
# --------------------------------------------------------------------------- #
def _gaussian_kde(samples: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Evaluate a Gaussian kernel-density estimate on a fixed grid.

    Uses Silverman's rule of thumb for the bandwidth — the same default the
    common toolkits reach for — so the curve is smooth without a tuning knob.

    Parameters
    ----------
    samples : numpy.ndarray
        1-D array of observations for one group.
    grid : numpy.ndarray
        1-D array of x-positions at which to evaluate the density.

    Returns
    -------
    numpy.ndarray
        Density values, same length as ``grid``.
    """
    n = samples.size
    std = float(np.std(samples))
    # Silverman's rule; guard the degenerate zero-variance case.
    bandwidth = 1.06 * std * n ** (-1.0 / 5.0) if std > 0 else 1.0
    # (grid − sample) / h broadcast to (grid, n), then average the kernel.
    z = (grid[:, None] - samples[None, :]) / bandwidth
    kernel = np.exp(-0.5 * z * z) / np.sqrt(2.0 * np.pi)
    return kernel.mean(axis=1) / bandwidth


# --------------------------------------------------------------------------- #
# Colour ramp                                                                  #
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


# Anchor hues for the ridge sweep, as a *fixed categorical* set (one distinct
# house hue per stop — blue, teal, mint, green, yellow, orange, red, purple).
# Because every ridge is a separate month (a category), not a point on a
# magnitude scale, this set answers to ``--accessibility`` via
# :func:`_style.leveled_colors`: ``universal`` (default) is the identity, so the
# ramp — and the emitted bytes — stay unchanged; the other levels remap all
# eight anchors through the shared sprezzature-colors engine so neighbouring ridges
# stay distinct under a named colour-vision deficiency, monochrome, or high
# contrast. The anchors' positions on the ramp are held fixed.
_RAMP_ANCHOR_POS: Sequence[float] = (0.00, 0.16, 0.30, 0.44, 0.58, 0.72, 0.86, 1.00)
_RAMP_ANCHOR_HEX: Dict[str, str] = {
    "Blue": "#007AFF",
    "Teal": "#5AC8FA",
    "Mint": "#00C7BE",
    "Green": "#34C759",
    "Yellow": "#FFCC00",
    "Orange": "#FF9500",
    "Red": "#FF3B30",
    "Purple": "#AF52DE",
}


def _season_ramp(n: int, accessibility: str = "universal") -> List[str]:
    """Return ``n`` distinct colours, one per ridge, along a house-hue sweep.

    Every ridge gets its **own** hue: the ramp walks the Apple-system palette
    from cool blues through teal / mint / green / yellow / orange to red, so
    the stack reads as a smooth colour progression top-to-bottom and no two
    neighbouring months share a hue. Positions are spread evenly across the
    ramp (``i / (n - 1)``) rather than keyed to temperature, which is what
    made the old ramp repeat blue at both ends.

    Parameters
    ----------
    n : int
        Number of ridges (colours) to produce.
    accessibility : str, optional
        Accessibility level applied to the eight fixed anchor hues before
        interpolation (see :func:`_style.leveled_colors`). ``"universal"``
        (default) is the identity, keeping the ramp byte-for-byte unchanged.

    Returns
    -------
    list of str
        ``n`` ``#RRGGBB`` strings, one distinct hue per ridge in top-to-bottom
        order.
    """
    # Anchor stops on a normalised position axis (0 = top ridge, 1 = bottom).
    # A full march through the house palette so all twelve months differ. The
    # anchor hues are levelled to the requested accessibility level; positions
    # stay fixed so only the colours move, never the spacing.
    anchor_hex = leveled_colors(_RAMP_ANCHOR_HEX, accessibility)
    stops: Sequence[Tuple[float, str]] = tuple(
        zip(_RAMP_ANCHOR_POS, anchor_hex.values())
    )
    colours: List[str] = []
    for i in range(n):
        pos = i / (n - 1) if n > 1 else 0.0
        for (lo_t, lo_c), (hi_t, hi_c) in zip(stops, stops[1:]):
            if lo_t <= pos <= hi_t:
                local = (pos - lo_t) / (hi_t - lo_t) if hi_t > lo_t else 0.0
                colours.append(_lerp_hex(lo_c, hi_c, local))
                break
        else:
            colours.append(stops[-1][1])
    return colours


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def build_svg(
    data: Dict[str, np.ndarray],
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full ridgeline SVG document as a string.

    Parameters
    ----------
    data : dict of str to numpy.ndarray
        Ordered ``{group_label: samples}``; the first item is drawn at the
        top of the stack.
    mode : str, optional
        Interactivity mode passed to :func:`_interactive.fullscreen_control`
        (``"self-contained"``, ``"external"`` or ``"static"``). Controls
        whether the emitted SVG carries its own fullscreen button; the raster
        output is unaffected. Defaults to ``"self-contained"``.
    accessibility : str, optional
        Palette accessibility level for the per-ridge hue sweep (``"universal"``,
        ``"high-contrast"``, ``"monochrome"``, ``"deuteranopia"``,
        ``"protanopia"`` or ``"tritanopia"``). Each ridge is a distinct month
        (a category), so the ramp's anchor hues are remapped through
        :func:`_style.leveled_colors`. Defaults to ``"universal"``, which leaves
        the colours (and the emitted bytes) unchanged.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    # ---- canvas geometry -------------------------------------------------- #
    # Poster-scale canvas: tall enough that every month gets a roomy lane with
    # clear air above its peak — no ridge pokes into the one above it.
    width, height = 1120, 1360
    m_left, m_right = 168, 48
    m_top, m_bottom = 148, 108
    plot_w = width - m_left - m_right
    plot_h = height - m_top - m_bottom

    labels = list(data.keys())
    n = len(labels)
    colours = _season_ramp(n, accessibility)

    # ---- shared x-domain over all groups ---------------------------------- #
    all_vals = np.concatenate(list(data.values()))
    x_lo = float(np.floor(all_vals.min() / 5.0) * 5.0) - 2.0
    x_hi = float(np.ceil(all_vals.max() / 5.0) * 5.0) + 2.0
    grid = np.linspace(x_lo, x_hi, 220)

    def x_px(x: float) -> float:
        """Map a data x-value to a pixel column."""
        return m_left + (x - x_lo) / (x_hi - x_lo) * plot_w

    # Vertical rhythm: each month owns a generous lane of pitch ``step``. The
    # tallest ridge is clamped to a fraction of that pitch so its peak always
    # clears the lane above — the user asked for zero overlap, so lanes are
    # fully separated (unlike the traditional overlapping joyplot).
    step = plot_h / n
    peak_h = step * 0.70  # tallest ridge fills 70 % of its own lane; 30 % gap

    # Densities per group, normalised to a common peak so ridge *heights* are
    # comparable at a glance.
    densities = {lbl: _gaussian_kde(data[lbl], grid) for lbl in labels}
    global_peak = max(float(d.max()) for d in densities.values())

    parts: List[str] = []

    # ---- header ----------------------------------------------------------- #
    title = "The whole distribution marches with the seasons, not just the mean"
    subtitle = (
        "Daily-high temperature by month, one colour-coded lane each — "
        "Illustrative data"
    )
    parts.append(
        f'<svg role="img" aria-label="{title}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}">'
    )
    parts.append(
        f"<title>{title}</title>"
        f"<desc>Ridgeline plot: one Gaussian kernel-density curve per month, "
        f"each in its own fully separated lane and its own house-palette hue "
        f"(blue through teal, green, yellow, orange, red to purple). Each "
        f"curve's peak shifts right through summer and left in winter, so the "
        f"whole distribution — not just the mean — moves with the season.</desc>"
    )
    parts.append(f'<rect width="{width}" height="{height}" rx="20" fill="{_BG}"/>')

    # OS-adaptive overrides (additive; every rule lives inside an @media block,
    # so the default render is byte-for-byte unchanged). Each ridge carries a
    # stable ``.rg-i`` class on its filled area. Under prefers-contrast the
    # per-ridge hues deepen together to their high-contrast spacing, raising the
    # fills' contrast against the white ground while the month labels and the
    # fully separated lanes keep every ridge identifiable. role="fill" only, so
    # each ridge's white + ink silhouette stroke is left untouched. forced-colors
    # is left to the browser default: twelve sweep hues cannot map onto the
    # ~4-colour system palette, and the labels carry identity regardless.
    ridge_series = {f".rg-{i}": colours[i] for i in range(n)}
    # Dark mode: invert paper + inks, dim the light month gridlines (#E5E5EA)
    # and re-light the ink axis / crest strokes (#1D1D1F) so they read on dark.
    # The ridges' white crest underlay (stroke #FFFFFF) is left as-is.
    dark_extra = (
        '[stroke="#E5E5EA"]{stroke:#2C2C2E;}'
        '[stroke="#1D1D1F"]{stroke:#F2F2F7;}'
    )
    parts.append(
        "<style>"
        + os_adaptive_style(ridge_series, role="fill")
        + os_dark_style(extra=dark_extra)
        + "</style>"
    )

    parts.append(
        f'<text x="{m_left - 104}" y="58" font-size="29" font-weight="700" '
        f'fill="{_INK}">{title}</text>'
    )
    parts.append(
        f'<text x="{m_left - 104}" y="90" font-size="18" '
        f'fill="{_SECONDARY}">{subtitle}</text>'
    )

    # ---- x gridlines (light, behind ridges) ------------------------------- #
    tick_step = 10.0
    first_tick = np.ceil(x_lo / tick_step) * tick_step
    ticks = np.arange(first_tick, x_hi + 1e-6, tick_step)
    grid_top = m_top - 18
    grid_bot = m_top + plot_h + 14
    for t in ticks:
        gx = x_px(float(t))
        parts.append(
            f'<line x1="{fmt_compact(gx)}" y1="{grid_top}" x2="{fmt_compact(gx)}" '
            f'y2="{grid_bot}" stroke="#E5E5EA" stroke-width="1.4"/>'
        )

    # ---- ridges (painted top→bottom so lower ridges overlap those above) -- #
    # Drawing order: bottom-most first would let upper ridges cover it. We
    # want each ridge to sit in front of the one *below* it, so we paint from
    # top of the stack downward and rely on later (lower) ridges overlapping.
    for i, label in enumerate(labels):
        base_y = m_top + step * (i + 0.85)  # baseline for this ridge
        dens = densities[label] / global_peak  # 0..1
        colour = colours[i]

        # Build the filled area path: along the top silhouette, then close
        # flat along the baseline.
        top_pts: List[str] = []
        for gx_val, d in zip(grid, dens):
            px = x_px(float(gx_val))
            py = base_y - d * peak_h
            top_pts.append(f"{fmt_compact(px)},{fmt_compact(py)}")
        x_start = x_px(float(grid[0]))
        x_end = x_px(float(grid[-1]))
        area_d = (
            f"M{fmt_compact(x_start)},{fmt_compact(base_y)} L"
            + " L".join(top_pts)
            + f" L{fmt_compact(x_end)},{fmt_compact(base_y)} Z"
        )
        stroke_d = "M" + " L".join(top_pts)

        # Hover tooltip: median + interquartile spread, no JavaScript.
        med = float(np.median(data[label]))
        q1, q3 = np.percentile(data[label], [25, 75])
        tip = (
            f"{label}: median {med:.0f} °C "
            f"(middle-half {q1:.0f}–{q3:.0f} °C)"
        )

        parts.append(
            f'<g class="ridge">'
            f'<title>{tip}</title>'
            f'<path class="rg-{i}" d="{area_d}" fill="{colour}" fill-opacity="0.82" '
            f'stroke="none"/>'
            f'<path d="{stroke_d}" fill="none" stroke="#FFFFFF" '
            f'stroke-width="1.8" stroke-opacity="0.9"/>'
            f'<path d="{stroke_d}" fill="none" stroke="{_INK}" '
            f'stroke-width="1.1" stroke-opacity="0.35"/>'
            f"</g>"
        )

        # Row label at the left, vertically centred on the baseline.
        parts.append(
            f'<text x="{m_left - 20}" y="{fmt_compact(base_y - 5)}" text-anchor="end" '
            f'font-size="18" fill="{_INK}">{label}</text>'
        )

    # ---- x-axis line + tick labels + title -------------------------------- #
    axis_y = m_top + plot_h + 34
    parts.append(
        f'<line x1="{fmt_compact(x_px(x_lo))}" y1="{fmt_compact(axis_y)}" '
        f'x2="{fmt_compact(x_px(x_hi))}" y2="{fmt_compact(axis_y)}" '
        f'stroke="{_INK}" stroke-width="1.8"/>'
    )
    for t in ticks:
        gx = x_px(float(t))
        parts.append(
            f'<text x="{fmt_compact(gx)}" y="{fmt_compact(axis_y + 26)}" text-anchor="middle" '
            f'font-size="16" font-family="{_MONO}" fill="{_SECONDARY}">'
            f"{int(t)}</text>"
        )
    parts.append(
        f'<text x="{fmt_compact(m_left + plot_w / 2)}" y="{fmt_compact(axis_y + 56)}" '
        f'text-anchor="middle" font-size="18" fill="{_INK}">'
        f"Daily-high temperature (°C)</text>"
    )

    # Fullscreen control per interactivity mode. The title runs wide across the
    # top, so nudge the button down and in with a larger inset to clear it.
    parts.append(fullscreen_control(width, height, mode, inset=22.0))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_ridgeline",
        description="Write the house-style ridgeline (joyplot) SVG example.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--seed", type=int, default=7, help="Random seed for the sample data."
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
    data = _sample_monthly_highs(seed=args.seed)
    svg = build_svg(data, mode=args.mode, accessibility=args.accessibility)
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

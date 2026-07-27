#!/usr/bin/env python3
"""Generate a publication-quality **mosaic / Marimekko** chart as a standalone SVG.

A mosaic (Marimekko) plot shows how a whole splits along *two* categorical
dimensions at once. Each **column** is a first-level category whose *width*
encodes that category's share of the grand total; within a column the stacked
**segments** encode a second categorical proportion by *height*. The area of any
tile is therefore proportional to a joint frequency — width times height — which
lets a reader compare both marginals and the cells in a single view.

Vega-Lite has no native Marimekko mark (rect widths cannot be data-driven off a
running cumulative on the same axis without pre-computation), so the figure is
assembled as a hand-authored SVG string. The output matches the sprezzature-figures
house style: Roboto typography, the Apple-system palette from
:mod:`_style`, ink ``#1D1D1F`` on a white ground, rounded corners, native
``<title>`` tooltips, and a CSS ``:hover`` lift with a ``prefers-reduced-motion``
guard.

The final artifact is always the SVG at
``assets/svg-examples/mosaic.svg``; running this module writes it.

Usage
-----
    python make_mosaic.py            # writes assets/svg-examples/mosaic.svg
    python make_mosaic.py --out x.svg

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc classes.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import (  # noqa: E402
    forced_color_patterns,
    load_palette,
    os_adaptive_style,
    os_dark_style,
)
from _render import write_svg  # noqa: E402
from _svg import svg_open  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# --------------------------------------------------------------------------- #
# Communicative fake data                                                       #
# --------------------------------------------------------------------------- #
# One quarter of online-store checkouts, split by the device a shopper used
# (column width = share of all orders) and by how they paid (segment height =
# share within that device). The story: on phones, wallets (Apple / Google Pay)
# already beat cards — the reason the mobile column leans toward the wallet hue.

#: First-level categories (columns). ``share`` is the fraction of all orders.
DEVICES: List[Dict[str, Any]] = [
    {"name": "Mobile", "share": 0.54},
    {"name": "Desktop", "share": 0.31},
    {"name": "Tablet", "share": 0.15},
]

#: Second-level categories (stacked segments). Order = paint / legend order.
METHODS: List[str] = ["Wallet", "Card", "Buy-now-pay-later", "Bank transfer"]

#: Within-column composition: {device -> {method -> fraction (sums to 1)}}.
COMPOSITION: Dict[str, Dict[str, float]] = {
    "Mobile":  {"Wallet": 0.48, "Card": 0.32, "Buy-now-pay-later": 0.15, "Bank transfer": 0.05},
    "Desktop": {"Wallet": 0.22, "Card": 0.55, "Buy-now-pay-later": 0.14, "Bank transfer": 0.09},
    "Tablet":  {"Wallet": 0.30, "Card": 0.47, "Buy-now-pay-later": 0.15, "Bank transfer": 0.08},
}

TITLE = "On phones, wallets have overtaken cards"
SUBTITLE = "Share of online-store checkouts by device and payment method - illustrative quarter"


# --------------------------------------------------------------------------- #
# Palette                                                                       #
# --------------------------------------------------------------------------- #
def method_colors(accessibility: str = "universal") -> Dict[str, str]:
    """Map each payment method to a house-palette hex.

    Wallet (the story's hero) takes the brand Blue; the rest read as a calm,
    CVD-distinguishable spread so the eye lands on Wallet first.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level threaded to :func:`load_palette`
        (``"universal"``, ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` or ``"tritanopia"``). Defaults
        to ``"universal"``, the colour-vision-safe standard.

    Returns
    -------
    dict of str to str
        ``{method_name: "#RRGGBB"}`` for every entry in :data:`METHODS`.
    """
    pal = load_palette(accessibility)
    return {
        "Wallet":            pal.get("Blue", "#007AFF"),
        "Card":              pal.get("Teal", "#5AC8FA"),
        "Buy-now-pay-later": pal.get("Orange", "#FF9500"),
        "Bank transfer":     pal.get("Gray", "#8E8E93"),
    }


# --------------------------------------------------------------------------- #
# Geometry helpers                                                              #
# --------------------------------------------------------------------------- #
def _fmt(value: float) -> str:
    """Format a float compactly (trim trailing zeros) for SVG coordinates."""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _method_slug(method: str) -> str:
    """Slugify a payment-method name into a stable CSS class token.

    Lower-cases the name and replaces every run of non-alphanumerics with a
    single hyphen, so ``"Buy-now-pay-later"`` becomes ``"buy-now-pay-later"``
    and ``"Bank transfer"`` becomes ``"bank-transfer"``. Used to give each tile
    a per-method class (``tile-wallet`` …) that the OS-adaptive rule can target.

    Parameters
    ----------
    method : str
        A payment-method name from :data:`METHODS`.

    Returns
    -------
    str
        A CSS-safe slug of the method name.
    """
    out = []
    prev_dash = False
    for ch in method.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")


def build_tiles(
    plot_x: float,
    plot_y: float,
    plot_w: float,
    plot_h: float,
    gap: float,
    accessibility: str = "universal",
) -> List[Dict[str, Any]]:
    """Compute one rect record per (device, method) mosaic tile.

    Parameters
    ----------
    plot_x, plot_y : float
        Top-left corner of the plotting area, in SVG user units.
    plot_w, plot_h : float
        Width and height of the plotting area.
    gap : float
        Horizontal white gap drawn between adjacent columns.
    accessibility : str, optional
        Palette accessibility level threaded to :func:`method_colors`
        (``"universal"``, ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` or ``"tritanopia"``). Defaults
        to ``"universal"``, the colour-vision-safe standard.

    Returns
    -------
    list of dict
        Each record carries ``x``, ``y``, ``w``, ``h`` (tile geometry),
        ``device``, ``method``, ``color``, and ``pct`` (within-column share, in
        percent) so the renderer can draw and label without recomputing.
    """
    colors = method_colors(accessibility)
    n_gaps = len(DEVICES) - 1
    inner_w = plot_w - gap * n_gaps  # width available to the columns themselves
    total_share = sum(d["share"] for d in DEVICES)

    tiles: List[Dict[str, Any]] = []
    cursor_x = plot_x
    for dev in DEVICES:
        col_w = inner_w * (dev["share"] / total_share)
        comp = COMPOSITION[dev["name"]]
        cursor_y = plot_y
        for method in METHODS:
            frac = comp[method]
            seg_h = plot_h * frac
            tiles.append({
                "x": cursor_x,
                "y": cursor_y,
                "w": col_w,
                "h": seg_h,
                "device": dev["name"],
                "method": method,
                "color": colors[method],
                "pct": frac * 100.0,
                "share": dev["share"] * 100.0,
            })
            cursor_y += seg_h
        cursor_x += col_w + gap
    return tiles


# --------------------------------------------------------------------------- #
# SVG assembly                                                                  #
# --------------------------------------------------------------------------- #
def render_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full mosaic SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode for the shared fullscreen control (see
        :mod:`_interactive`). Three modes: ``"self-contained"`` (default) ships
        a self-carrying fullscreen button and its wiring script; ``"external"``
        ships no internal button and defers to a page-level module; ``"static"``
        ships no interactivity at all. The static PNG raster is byte-identical
        across modes because the button starts hidden.
    accessibility : str, optional
        Palette accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). Defaults to ``"universal"``, the
        colour-vision-safe standard, which leaves the shipped palette
        unchanged.

    Returns
    -------
    str
        A complete, standalone ``<svg>`` document (house style, accessible
        ``<title>``/``<desc>``, native tooltips, CSS hover lift).
    """
    # Canvas + plotting frame. Poster-scale so tiles and labels read from a
    # distance; the right rail holds the legend, the top rail the title.
    width, height = 1120, 820
    plot_x, plot_y = 96.0, 216.0
    plot_w, plot_h = width - plot_x - 300.0, 520.0  # leave room for a right legend
    gap = 16.0

    ink = "#1D1D1F"
    muted = "#6E6E73"
    hairline = "#E5E5EA"

    tiles = build_tiles(plot_x, plot_y, plot_w, plot_h, gap, accessibility)

    parts: List[str] = []
    parts.append(svg_open(width, height, "mosaic-t", "mosaic-d"))
    parts.append(f'<title id="mosaic-t">{escape(TITLE)}</title>')
    parts.append(
        '<desc id="mosaic-d">Marimekko mosaic: column widths are each device\'s share of all '
        'online checkouts (Mobile widest at 54 percent), and each column stacks payment methods '
        'by their within-device share. On Mobile, Wallet is the tallest segment, overtaking Card.</desc>'
    )

    # Style block: hover lift + focus ring, guarded by reduced-motion. The
    # OS-adaptive block is appended last (additive; every rule lives inside a
    # media query, so the default render is byte-for-byte unchanged). Under
    # prefers-contrast the four payment-method tile fills deepen to their
    # high-contrast hues; deepening only strengthens the white in-tile labels
    # and leaves Card's ink label readable.
    method_hex = method_colors(accessibility)
    tile_series = {
        ".tile-wallet": method_hex["Wallet"],
        ".tile-card": method_hex["Card"],
        ".tile-buy-now-pay-later": method_hex["Buy-now-pay-later"],
        ".tile-bank-transfer": method_hex["Bank transfer"],
    }
    # Under Windows High Contrast / forced-colors the ~4-colour system palette
    # cannot preserve four distinct method hues, and the legend maps colour →
    # method, so colour is the sole per-series key. Each method tile therefore
    # takes a distinct CanvasText pattern (hatch / dots / cross) on Canvas —
    # identity by texture, not hue. The patterns live in <defs> and are referenced
    # only inside the forced-colors media query, so the default render is
    # unchanged.
    fcp_defs, fcp_style = forced_color_patterns(
        [
            ".tile-wallet",
            ".tile-card",
            ".tile-buy-now-pay-later",
            ".tile-bank-transfer",
        ],
        prefix="mos-fcp",
    )
    parts.append(
        "<style>"
        ".tile{transition:transform .18s ease, filter .18s ease;transform-box:fill-box;transform-origin:center;}"
        ".tile:hover,.tile:focus{filter:brightness(1.06);transform:scale(1.015);outline:none;}"
        ".tile:focus{stroke:#1D1D1F;stroke-width:2;}"
        "@media (prefers-reduced-motion: reduce){.tile{transition:none;}.tile:hover,.tile:focus{transform:none;}}"
        + os_adaptive_style(tile_series, role="fill")
        + fcp_style
        # Additive OS dark mode: dark paper + light ink (default ink_map); the
        # payment-method tile hues are data, left alone. The focus ring and the
        # hairline column rules flip to light so they read on the dark surface.
        + os_dark_style(
            extra=(
                '[stroke="#E5E5EA"]{stroke:#3A3A3E;}'
                ".tile:focus{stroke:#F2F2F7;}"
            )
        )
        + "</style>"
    )
    # Forced-colors pattern tiles (referenced only inside the media query above).
    parts.append(f"<defs>{fcp_defs}</defs>")

    # Background.
    parts.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')

    # Title + subtitle.
    parts.append(f'<text x="{_fmt(plot_x)}" y="66" font-size="34" font-weight="700" fill="{ink}">{escape(TITLE)}</text>')
    parts.append(f'<text x="{_fmt(plot_x)}" y="102" font-size="20" fill="{muted}">{escape(SUBTITLE)}</text>')

    # Left axis label (vertical) — within-device composition axis.
    axis_cx = plot_x - 62.0
    axis_cy = plot_y + plot_h / 2.0
    parts.append(
        f'<text x="{_fmt(axis_cx)}" y="{_fmt(axis_cy)}" font-size="18" fill="{muted}" '
        f'text-anchor="middle" transform="rotate(-90 {_fmt(axis_cx)} {_fmt(axis_cy)})">Share within device</text>'
    )

    # Vertical percentage ticks on the left (0 / 25 / 50 / 75 / 100 %).
    for pct in (0, 25, 50, 75, 100):
        ty = plot_y + plot_h * (pct / 100.0)
        parts.append(
            f'<text x="{_fmt(plot_x - 18)}" y="{_fmt(ty + 6)}" font-size="15" fill="{muted}" '
            f'text-anchor="end" font-family="Roboto Mono, monospace">{pct}%</text>'
        )
        parts.append(
            f'<line x1="{_fmt(plot_x - 12)}" y1="{_fmt(ty)}" x2="{_fmt(plot_x)}" y2="{_fmt(ty)}" '
            f'stroke="{hairline}" stroke-width="1.5"/>'
        )

    # Tiles, grouped so hover/focus works per rect.
    rx = 5.0
    for t in tiles:
        label = (
            f"{t['device']} - {t['method']}: {t['pct']:.0f}% of {t['device']} orders "
            f"({t['device']} = {t['share']:.0f}% of all orders)"
        )
        parts.append(
            f'<rect class="tile tile-{_method_slug(t["method"])}" tabindex="0" '
            f'x="{_fmt(t["x"])}" y="{_fmt(t["y"])}" '
            f'width="{_fmt(t["w"])}" height="{_fmt(t["h"])}" rx="{_fmt(rx)}" '
            f'fill="{t["color"]}" stroke="#FFFFFF" stroke-width="3">'
            f'<title>{escape(label)}</title></rect>'
        )
        # In-tile percentage label when the segment is tall + wide enough.
        if t["h"] >= 34 and t["w"] >= 80:
            lx = t["x"] + t["w"] / 2.0
            ly = t["y"] + t["h"] / 2.0 + 6.0
            txt_fill = "#FFFFFF" if t["method"] != "Card" else ink
            parts.append(
                f'<text x="{_fmt(lx)}" y="{_fmt(ly)}" font-size="17" fill="{txt_fill}" '
                f'text-anchor="middle" font-family="Roboto Mono, monospace" '
                f'pointer-events="none">{t["pct"]:.0f}%</text>'
            )

    # Column headers: device name + its width-share, above each column.
    for dev in DEVICES:
        # Find the column's tiles to recover its x-extent.
        col = [t for t in tiles if t["device"] == dev["name"]]
        cx = col[0]["x"] + col[0]["w"] / 2.0
        parts.append(
            f'<text x="{_fmt(cx)}" y="{_fmt(plot_y - 44)}" font-size="20" font-weight="700" '
            f'fill="{ink}" text-anchor="middle">{escape(dev["name"])}</text>'
        )
        parts.append(
            f'<text x="{_fmt(cx)}" y="{_fmt(plot_y - 20)}" font-size="15" fill="{muted}" '
            f'text-anchor="middle" font-family="Roboto Mono, monospace">{dev["share"] * 100:.0f}% of orders</text>'
        )

    # Bottom axis label — the columns encode order share by width.
    parts.append(
        f'<text x="{_fmt(plot_x + plot_w / 2)}" y="{_fmt(plot_y + plot_h + 54)}" font-size="18" '
        f'fill="{muted}" text-anchor="middle">Column width = share of all orders</text>'
    )

    # Legend panel on the right.
    legend_x = plot_x + plot_w + 56.0
    legend_y = plot_y + 12.0
    colors = method_colors(accessibility)
    parts.append(
        f'<text x="{_fmt(legend_x)}" y="{_fmt(legend_y - 20)}" font-size="18" font-weight="700" '
        f'fill="{ink}">Payment method</text>'
    )
    for i, method in enumerate(METHODS):
        row_y = legend_y + i * 42.0
        parts.append(
            f'<rect x="{_fmt(legend_x)}" y="{_fmt(row_y)}" width="22" height="22" rx="5" '
            f'fill="{colors[method]}"/>'
        )
        parts.append(
            f'<text x="{_fmt(legend_x + 34)}" y="{_fmt(row_y + 17)}" font-size="17" '
            f'fill="{ink}">{escape(method)}</text>'
        )

    # --- shared fullscreen control. The right rail (300px) holds the legend,
    #     so inset the button well left of it. ---
    parts.append(fullscreen_control(width, height, mode, inset=320.0))

    parts.append("</svg>")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                           #
# --------------------------------------------------------------------------- #
def main(argv: List[str] | None = None) -> int:
    """Write the mosaic SVG to disk.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns
    -------
    int
        Process exit code (``0`` on success).
    """
    default_out = Path(__file__).resolve().parent.parent / "assets" / "svg-examples" / "mosaic.svg"
    parser = argparse.ArgumentParser(description="Render the mosaic / Marimekko example SVG.")
    parser.add_argument("--out", default=str(default_out), help="Output SVG path.")
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the shared fullscreen control.",
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
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    write_svg(out_path, render_svg(mode=args.mode, accessibility=args.accessibility))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

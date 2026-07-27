#!/usr/bin/env python3
"""
make_pictorial — an ISOTYPE (isotype / pictorial) icon-array as hand-authored SVG.

A pictorial chart in the tradition of Otto Neurath's ISOTYPE encodes a
count by *repeating an icon*: one little figure stands for a fixed
number of units, a full row of figures reads off the value at a glance,
and the final figure is clipped part-way to show the fractional
remainder. Because the mark is a recognisable pictogram (here, a
person) rather than an abstract bar or square, the reader grasps *what*
is being counted before reading a single label. This is the pictorial's
defining trait, and what sets it apart from the waffle (which uses
plain squares).

This module builds the SVG string by hand — no matplotlib / seaborn /
plotly, and no Vega, because a clipped repeated-glyph grid with a
partial last icon is a layout Vega-Lite cannot express cleanly. It
follows the sprezzature-* house style pulled from :mod:`_style`: the
Apple-ish saturated palette, Roboto typography, ink ``#1D1D1F`` on a
white background, rounded forms, a takeaway title, and a one-line
subtitle. A clear legend states the unit ("one figure = 5 people").

The figure is quietly interactive without any JavaScript: hovering or
keyboard-focusing a group's row of icons (or its label) lifts that row
and dims the others, and every row carries a native ``<title>``
tooltip. A gentle SMIL "fill-in" reveals the icons left-to-right on
load — every icon is fully visible at ``t = 0`` (the animation only
adds a brief settle), so a static raster shows the finished chart.
Motion is guarded by ``prefers-reduced-motion``.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/pictorial.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

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
# Geometry + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Poster-scale so the icon rows read
#: comfortably at a glance and the whole comparison fits with headroom.
_WIDTH: int = 1240
_HEIGHT: int = 900

#: One pictogram stands for this many people-per-100. Choosing 5 keeps
#: every row to at most 20 icons and makes fractional remainders (a
#: half or quarter figure) legible.
_UNIT: float = 5.0

#: Icon cell geometry, in pixels. The person glyph is drawn inside a
#: cell of ``_ICON_W`` by ``_ICON_H``; ``_ICON_GAP`` separates cells.
_ICON_W: float = 40.0
_ICON_H: float = 68.0
_ICON_GAP: float = 12.0

#: Left edge of the icon field and vertical rhythm between group rows.
_FIELD_X: float = 300.0
_ROW_TOP: float = 220.0
_ROW_H: float = 118.0

#: House-style inks.
_INK: str = "#1D1D1F"       # primary text
_SUBTLE: str = "#6E6E73"    # secondary text
_EMPTY: str = "#E3E3E8"     # "remainder" / unfilled ghost icons
_BG: str = "#FFFFFF"        # background
_FOCUS: str = "#0A4DA0"     # focus-ring blue


def _dataset(accessibility: str = "universal") -> List[Dict[str, object]]:
    """Return the communicative fake data for the pictorial.

    Commuting mode across five cities: of every 100 people who travel to
    work on a typical weekday, how many arrive by bicycle. The framing
    is concrete (a person icon per five commuters) and the spread is
    wide enough that the icon rows differ obviously in length.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level forwarded to :func:`_style.load_palette`.

    Returns
    -------
    list of dict
        One dict per city with ``label`` (str), ``value`` (float, cyclists
        per 100 commuters), and ``color`` (hex) keys, largest first.
    """
    palette = load_palette(accessibility)
    # Ordered largest -> smallest so the rows form a tidy staircase and
    # the reader's eye sweeps from the standout down to the laggard.
    rows = [
        ("Copenhagen", 62.0, "Green"),
        ("Amsterdam", 48.0, "Turquoise"),
        ("Tokyo", 27.0, "Blue"),
        ("Berlin", 18.0, "Orange"),
        ("Los Angeles", 4.0, "Red"),
    ]
    return [
        {"label": label, "value": value, "color": palette[color]}
        for label, value, color in rows
    ]


def _slug(label: str) -> str:
    """Turn a category label into a CSS-class-safe slug."""
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in label).strip("-")


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def _person_path(cx: float, top: float) -> str:
    """Return the SVG path ``d`` for one ISOTYPE person glyph.

    The glyph is a stylised standing figure — a round head above a
    shouldered torso that tapers to two legs — drawn to fill a cell of
    :data:`_ICON_W` by :data:`_ICON_H` whose top-centre is at
    ``(cx, top)``. It is a single closed path (plus the head as a
    separate circle emitted by the caller) so a clip rectangle can slice
    it cleanly for fractional remainders.

    Parameters
    ----------
    cx : float
        Horizontal centre of the icon cell, in pixels.
    top : float
        Top edge (y) of the icon cell, in pixels.

    Returns
    -------
    str
        The body path's ``d`` attribute value.
    """
    # Proportions expressed as fractions of the cell so the glyph scales
    # with _ICON_W / _ICON_H if those constants change.
    w = _ICON_W
    h = _ICON_H
    head_r = w * 0.26
    head_cy = top + head_r + h * 0.02
    neck_y = head_cy + head_r * 0.9
    shoulder_y = neck_y + h * 0.06
    hip_y = top + h * 0.58
    foot_y = top + h
    half_shoulder = w * 0.42
    half_waist = w * 0.24
    half_foot = w * 0.16
    crotch_y = top + h * 0.66
    # Body: shoulders -> taper to waist -> two legs with a crotch notch.
    # Rounded shoulders via a quadratic curve keep the silhouette soft.
    return (
        f"M {cx - half_waist:.1f} {neck_y:.1f} "
        f"Q {cx - half_shoulder:.1f} {shoulder_y:.1f} "
        f"{cx - half_shoulder:.1f} {shoulder_y + h * 0.06:.1f} "
        f"L {cx - half_waist:.1f} {hip_y:.1f} "
        f"L {cx - half_foot - w * 0.10:.1f} {foot_y:.1f} "
        f"L {cx - half_foot + w * 0.02:.1f} {foot_y:.1f} "
        f"L {cx - w * 0.03:.1f} {crotch_y:.1f} "
        f"L {cx + w * 0.03:.1f} {crotch_y:.1f} "
        f"L {cx + half_foot - w * 0.02:.1f} {foot_y:.1f} "
        f"L {cx + half_foot + w * 0.10:.1f} {foot_y:.1f} "
        f"L {cx + half_waist:.1f} {hip_y:.1f} "
        f"L {cx + half_shoulder:.1f} {shoulder_y + h * 0.06:.1f} "
        f"Q {cx + half_shoulder:.1f} {shoulder_y:.1f} "
        f"{cx + half_waist:.1f} {neck_y:.1f} Z"
    )


def _head(cx: float, top: float) -> Tuple[float, float, float]:
    """Return the ``(cx, cy, r)`` circle for a person glyph's head."""
    head_r = _ICON_W * 0.26
    head_cy = top + head_r + _ICON_H * 0.02
    return cx, head_cy, head_r


def _icon(
    cx: float,
    top: float,
    fill: str,
    opacity: float = 1.0,
    clip_id: str = "",
    cls: str = "",
) -> str:
    """Emit one person glyph (body path + head) at the given cell position.

    Parameters
    ----------
    cx : float
        Horizontal centre of the icon cell.
    top : float
        Top edge of the icon cell.
    fill : str
        Fill colour (a category hex, or the ghost grey for remainders).
    opacity : float, optional
        Fill opacity (used only to soften the ghost remainder icons).
    clip_id : str, optional
        When set, wraps the glyph in ``clip-path=url(#clip_id)`` so a
        fractional last figure is sliced vertically.
    cls : str, optional
        CSS class placed on both the head circle and the body path (not the
        ghost icons). It lets a class rule outrank the inline ``fill`` under
        the OS-adaptive media queries — the inline fill is kept exactly, so
        the default render is unchanged. Empty for the un-classed ghosts.

    Returns
    -------
    str
        SVG fragment for one icon.
    """
    hx, hy, hr = _head(cx, top)
    op = f' fill-opacity="{opacity}"' if opacity != 1.0 else ""
    clip = f' clip-path="url(#{clip_id})"' if clip_id else ""
    klass = f' class="{cls}"' if cls else ""
    return (
        f'<g{clip}>'
        f'<circle{klass} cx="{hx:.1f}" cy="{hy:.1f}" r="{hr:.1f}" fill="{fill}"{op}/>'
        f'<path{klass} d="{_person_path(cx, top)}" fill="{fill}"{op}/>'
        f'</g>'
    )


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full pictorial-chart SVG document as a string.

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
    data = _dataset(accessibility)

    # The longest row sets how many icon columns we need; every row draws
    # a full set of ghost icons underneath so the field is visually
    # gridded and short rows still show "out of how many".
    max_value = max(float(d["value"]) for d in data)
    n_cols = int(-(-max_value // _UNIT))  # ceil division to whole icons

    # ---- header ----
    parts: List[str] = []
    parts.append(svg_open(_WIDTH, _HEIGHT, "pc-title", "pc-desc"))
    parts.append(
        '<title id="pc-title">Cycling to work, per 100 commuters, '
        'across five cities</title>'
    )
    desc = (
        "Pictorial ISOTYPE chart: each row repeats a person icon, one "
        "figure per five cyclists out of every hundred commuters; the "
        "last figure in a row is clipped to show the remainder. "
        + "; ".join(f"{_xml(str(d['label']))} {d['value']:.0f}" for d in data)
        + " per 100. Copenhagen leads with 62; Los Angeles trails at 4."
    )
    parts.append(f'<desc id="pc-desc">{desc}</desc>')

    # ---- clip paths for fractional last icons + reveal wipes ----
    parts.append('<defs>')
    for k, d in enumerate(data):
        s = _slug(str(d["label"]))
        value = float(d["value"])
        full = int(value // _UNIT)
        frac = (value - full * _UNIT) / _UNIT  # 0..1 of the partial icon
        if frac > 1e-6:
            # Clip the partial icon to a fraction of its cell width.
            cx = _FIELD_X + full * (_ICON_W + _ICON_GAP)
            top = _ROW_TOP + k * _ROW_H
            clip_w = _ICON_W * frac
            parts.append(
                f'<clipPath id="clip-{s}">'
                f'<rect x="{cx - _ICON_W / 2:.1f}" y="{top - 4:.1f}" '
                f'width="{clip_w + _ICON_W / 2:.1f}" height="{_ICON_H + 8:.1f}"/>'
                f'</clipPath>'
            )
    parts.append('</defs>')

    # ---- interactivity + house style (pure CSS, no JS) ----
    style_rows = [
        ".row { transition: transform .18s ease; }",
        ".icons { transition: opacity .18s ease; }",
        # Hover/focus any row dims every OTHER row's icons.
        "svg:hover .icons, svg:focus-within .icons { opacity: .30; }",
    ]
    for d in data:
        s = _slug(str(d["label"]))
        # The hovered/focused row keeps full opacity and lifts slightly.
        style_rows.append(
            f".row-{s}:hover .icons, .row-{s}:focus .icons {{ opacity: 1; }}"
        )
        style_rows.append(
            f".row-{s}:hover, .row-{s}:focus {{ transform: translateY(-4px); }}"
        )
    style_rows.extend([
        ".row { cursor: pointer; }",
        ".row:focus { outline: none; }",
        f".row:focus .rowlabel {{ fill: {_FOCUS}; }}",
        "@media (prefers-reduced-motion: reduce) {"
        " .row, .icons { transition: none; }"
        " .reveal { animation: none !important; }"
        "}",
    ])
    # OS-adaptive overrides (additive; the default render is byte-identical
    # because every rule below lives inside a media query). Under
    # prefers-contrast each city's filled icons deepen to their high-contrast
    # hue. Under forced colours the filled figures drop to system-palette
    # silhouettes — legitimate here because every row carries an always-visible
    # city label and value read-out, so the count reads by icon-run length and
    # label without colour. The ghost/backdrop icons stay un-classed, so the
    # filled-vs-empty distinction survives; the value read-outs follow the
    # system palette too.
    pic_series = {f".pic-{_slug(str(d['label']))}": str(d["color"]) for d in data}
    style_rows.append(
        os_adaptive_style(
            pic_series,
            role="fill",
            forced=True,
            extra_forced=".pic-val{fill:CanvasText;}",
        )
    )
    # Additive OS dark mode: dark paper + light ink (default ink_map); the filled
    # icon hues are data, left alone. The light "remainder" ghost icons darken to
    # a dim slate so the filled-vs-empty run still reads on the dark surface.
    style_rows.append(os_dark_style(extra='[fill="#E3E3E8"]{fill:#2A2A2E;}'))
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_FIELD_X - 244:.0f}" y="76" font-size="34" '
        f'font-weight="700" fill="{_INK}">'
        f'Copenhagen bikes; Los Angeles drives</text>'
    )
    parts.append(
        f'<text x="{_FIELD_X - 244:.0f}" y="116" font-size="19" '
        f'fill="{_SUBTLE}">Cyclists per 100 commuters on a typical '
        f'weekday · one figure = {int(_UNIT)} people · illustrative</text>'
    )

    # ---- icon rows, one per city ----
    for k, d in enumerate(data):
        s = _slug(str(d["label"]))
        color = str(d["color"])
        value = float(d["value"])
        top = _ROW_TOP + k * _ROW_H
        full = int(value // _UNIT)
        frac = (value - full * _UNIT) / _UNIT

        parts.append(
            f'<g class="row row-{s}" tabindex="0" role="listitem">'
            f'<title>{_xml(str(d["label"]))}: {value:.0f} cyclists per '
            f'100 commuters</title>'
        )

        # Row label (city) on the left, value on the far right for scanning.
        label_y = top + _ICON_H * 0.5
        parts.append(
            f'<text class="rowlabel" x="{_FIELD_X - 40:.0f}" y="{label_y:.1f}" '
            f'font-size="22" font-weight="600" fill="{_INK}" '
            f'text-anchor="end" dominant-baseline="middle">'
            f'{_xml(str(d["label"]))}</text>'
        )

        # Ghost icons underneath (the "out of the maximum" backdrop).
        parts.append('<g>')
        for c in range(n_cols):
            cx = _FIELD_X + c * (_ICON_W + _ICON_GAP) + _ICON_W / 2
            parts.append(_icon(cx, top, _EMPTY, opacity=1.0))
        parts.append('</g>')

        # Filled icons — full ones, then the clipped fractional one. The
        # <g class="icons"> wraps the coloured layer for the hover dimming,
        # and the SMIL reveal wipes it in from the left at load.
        reveal_id = f"reveal-{s}"
        parts.append(f'<g class="icons" clip-path="url(#{reveal_id})">')
        parts.append('<defs>')
        # The reveal clip is capped at THIS row's own filled width, so the
        # animation can never show more figures than the value. It counts
        # up from most-of-the-way (base_w) to the exact value width — a
        # brief settle, not a wipe from nothing. Rows begin in rank order
        # (a small top-to-bottom stagger) so the eye reads the ranking as
        # the bars land. The static raster freezes on the final width.
        row_full_w = (
            (full + (frac if frac > 1e-6 else 0.0)) * (_ICON_W + _ICON_GAP)
            - _ICON_GAP + _ICON_W / 2 + 6
        )
        base_w = row_full_w * 0.72  # visible at t=0 — never empty
        stagger = 0.10 * k
        parts.append(
            f'<clipPath id="{reveal_id}">'
            f'<rect class="reveal" x="{_FIELD_X - _ICON_W / 2 - 4:.1f}" '
            f'y="{top - 6:.1f}" height="{_ICON_H + 12:.1f}" '
            f'width="{row_full_w:.1f}">'
            f'<animate attributeName="width" '
            f'from="{base_w:.1f}" to="{row_full_w:.1f}" '
            f'dur="0.7s" begin="{stagger:.2f}s" fill="freeze" '
            f'calcMode="spline" keyTimes="0;1" '
            f'keySplines="0.22 0.61 0.36 1"/>'
            f'</rect>'
            f'</clipPath>'
        )
        parts.append('</defs>')
        for c in range(full):
            cx = _FIELD_X + c * (_ICON_W + _ICON_GAP) + _ICON_W / 2
            parts.append(_icon(cx, top, color, cls=f"pic-{s}"))
        if frac > 1e-6:
            cx = _FIELD_X + full * (_ICON_W + _ICON_GAP) + _ICON_W / 2
            parts.append(_icon(cx, top, color, clip_id=f"clip-{s}", cls=f"pic-{s}"))
        parts.append('</g>')

        # Value read-out at the end of the row, past the longest possible run.
        val_x = _FIELD_X + n_cols * (_ICON_W + _ICON_GAP) + 24
        parts.append(
            f'<text class="pic-val" x="{val_x:.0f}" y="{label_y:.1f}" '
            f'font-size="26" font-weight="700" fill="{color}" '
            f'dominant-baseline="middle">{value:.0f}</text>'
        )
        parts.append(
            f'<text x="{val_x:.0f}" y="{label_y + 24:.1f}" font-size="13" '
            f'font-weight="600" fill="{_SUBTLE}" dominant-baseline="middle">'
            f'per 100</text>'
        )

        parts.append('</g>')

    # ---- legend / unit key (bottom-left, below the rows) ----
    legend_y = _ROW_TOP + len(data) * _ROW_H + 26
    key_x = _FIELD_X - 244
    parts.append(f'<g transform="translate({key_x:.0f},{legend_y:.0f})">')
    # One sample figure + its meaning, drawn at a smaller scale via the
    # same glyph helper (reuse the icon at the origin cell).
    sample_cx = 20.0
    hx, hy, hr = _head(sample_cx, 0.0)
    parts.append(
        f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{hr:.1f}" fill="{_SUBTLE}"/>'
    )
    parts.append(f'<path d="{_person_path(sample_cx, 0.0)}" fill="{_SUBTLE}"/>')
    parts.append(
        f'<text x="{sample_cx + 30:.0f}" y="{_ICON_H * 0.42:.0f}" '
        f'font-size="18" fill="{_INK}" dominant-baseline="middle">'
        f'= {int(_UNIT)} people per 100 commuters</text>'
    )
    parts.append(
        f'<text x="{sample_cx + 30:.0f}" y="{_ICON_H * 0.42 + 26:.0f}" '
        f'font-size="15" fill="{_SUBTLE}" dominant-baseline="middle">'
        f'A part-figure marks the remainder · rows sorted high to low</text>'
    )
    parts.append('</g>')

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the pictorial SVG to the skill's ``svg-examples`` folder."""
    render_cli(__file__, "pictorial", build_svg, description="Render the pictorial SVG.")


if __name__ == "__main__":
    main()

"""
_labels — the shared "cell around text" primitive for every make_* figure.

Across the gallery the same small graphic kept being re-invented: a rounded
**cell behind a text label** — a chip, pill, plate, badge or tag that lifts a
name, a value or a call-out off a busy background so it stays readable. Voronoi
territory names, parliament read-outs, bullet target ticks, boxen p99 tags,
spike-map hover flags, dashboard call-outs — all of them wanted the same thing,
and each spelled it out inline with slightly different (and sometimes ugly)
geometry: black halos, colour-on-colour, uneven padding.

This module makes that one component **shared, colour-driven and nicely done**.
You pass an input colour and a variant; it returns a self-contained ``<g>`` with
a rounded cell and its text, with:

* automatic **contrast text colour** (white or ink) chosen from the cell fill's
  relative luminance, so a label is never colour-on-colour;
* **no black halos** — the optional lift is a white keyline, never a dark ring;
* consistent rounded corners, padding and vertical centring;
* left / centre / right anchoring so the cell can hang off any point.

Three variants cover the whole gallery:

``tint``
    Soft wash of the input colour (low-opacity fill) with the colour itself as
    the text. The calm default for on-canvas call-outs.
``solid``
    Opaque input-colour fill with auto white/ink text and an optional white
    keyline. For labels that must sit **on top of** other marks (a cell inside
    its own map region, a value on a bar).
``ghost``
    White (or a given background) fill with a coloured hairline border and
    coloured text. For labels over photos / dense fills where even a tint would
    muddy.

The module is **stdlib-only** (it borrows :func:`_svg.hex_to_rgb` /
:func:`_svg.xml_escape`), so it imports anywhere ``_svg`` and ``_style`` do —
no dataviz tier required.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from typing import List, Optional

from _svg import hex_to_rgb, xml_escape

# House neutrals used as the two text-contrast anchors.
_INK = "#1D1D1F"
_WHITE = "#FFFFFF"
# Per-character advance as a fraction of the font size. Roboto proportional text
# averages ~0.56; the mono face is wider at ~0.62. Used only to size the cell,
# so a small over-estimate (padding) is safer than an under-estimate (clipping).
_ADVANCE = 0.58
_ADVANCE_MONO = 0.62


def relative_luminance(hex_colour: str) -> float:
    """Return the WCAG relative luminance of ``hex_colour`` in ``[0, 1]``.

    Parameters
    ----------
    hex_colour : str
        A ``#RRGGBB`` colour.

    Returns
    -------
    float
        Relative luminance; ~0 for black, ~1 for white. Used to decide whether
        white or ink text reads better on a given fill.
    """
    r, g, b = (c / 255.0 for c in hex_to_rgb(hex_colour))

    def _lin(c: float) -> float:
        # sRGB → linear light, the WCAG transfer curve.
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def best_text_colour(fill_hex: str, *, light: str = _WHITE, dark: str = _INK) -> str:
    """Choose the higher-contrast text colour (``light`` or ``dark``) for a fill.

    Parameters
    ----------
    fill_hex : str
        The cell fill the text sits on.
    light, dark : str, optional
        The two candidate text colours (default white and ink).

    Returns
    -------
    str
        Whichever of ``light`` / ``dark`` contrasts better with ``fill_hex``.
        The 0.42 threshold on luminance matches where white stops winning on the
        mid-saturation Apple hues (e.g. Apple Blue → white, Yellow → ink).
    """
    return dark if relative_luminance(fill_hex) > 0.42 else light


def readable_on_white(hex_colour: str, *, max_lum: float = 0.5) -> str:
    """Darken a hue just enough to read as text on white.

    Light house hues (Yellow above all, then Mint / Teal) are too pale to use as
    *text* on a white ground. This blends the colour toward ink in small steps
    until its relative luminance falls to ``max_lum``, so a ``tint`` / ``ghost``
    label keeps its hue identity while staying legible. Colours that are already
    dark enough (Blue, Red, Purple, …) are returned unchanged.

    Parameters
    ----------
    hex_colour : str
        The hue to make readable.
    max_lum : float, optional
        Target upper bound on relative luminance (default 0.5).

    Returns
    -------
    str
        A ``#RRGGBB`` colour at or below ``max_lum`` luminance.
    """
    r, g, b = hex_to_rgb(hex_colour)
    ir, ig, ib = hex_to_rgb(_INK)
    cur = hex_colour
    for _ in range(8):
        if relative_luminance(cur) <= max_lum:
            break
        r = round(r + (ir - r) * 0.25)
        g = round(g + (ig - g) * 0.25)
        b = round(b + (ib - b) * 0.25)
        cur = f"#{r:02X}{g:02X}{b:02X}"
    return cur


def _text_width(text: str, size: float, mono: bool) -> float:
    """Estimate rendered text width in px (slightly generous, to avoid clipping)."""
    return len(text) * size * (_ADVANCE_MONO if mono else _ADVANCE)


def label_cell(
    x: float,
    y: float,
    text: str,
    fill: str,
    *,
    variant: str = "tint",
    size: float = 13.0,
    weight: str = "700",
    anchor: str = "start",
    mono: bool = False,
    keyline: bool = True,
    font: str = "Roboto, system-ui, sans-serif",
    mono_font: str = "Roboto Mono, ui-monospace, monospace",
    text_colour: Optional[str] = None,
    pad_x: Optional[float] = None,
) -> str:
    """Return a rounded "cell around text" as a self-contained SVG ``<g>``.

    The cell is vertically centred on ``y`` and horizontally placed by
    ``anchor`` relative to ``x`` (``start`` = ``x`` is the left edge, ``middle``
    = ``x`` is the centre, ``end`` = ``x`` is the right edge). Its width follows
    the text; its height and corner radius follow the font size (a full pill).

    Parameters
    ----------
    x, y : float
        Anchor point, in user-space pixels (``y`` is the cell's vertical centre).
    text : str
        The label text (escaped internally).
    fill : str
        The input colour that drives the whole cell — the wash, the solid fill or
        the border, depending on ``variant``.
    variant : {'tint', 'solid', 'ghost'}, optional
        The cell style (see the module docstring).
    size : float, optional
        Font size in px; also sets the cell height and radius.
    weight : str, optional
        Font weight for the text.
    anchor : {'start', 'middle', 'end'}, optional
        How ``x`` positions the cell horizontally.
    mono : bool, optional
        Use the monospace face (for numeric values); also widens the sizing.
    keyline : bool, optional
        For ``solid``, draw a thin white keyline so the cell lifts off any
        background. Never a dark ring.
    font, mono_font : str, optional
        Font stacks.
    text_colour : str, optional
        Override the automatic text colour.
    pad_x : float, optional
        Horizontal padding; defaults to ``0.75 * size``.

    Returns
    -------
    str
        An SVG ``<g>`` containing the cell ``<rect>`` and the ``<text>``.
    """
    if variant not in ("tint", "solid", "ghost"):
        raise ValueError(f"unknown variant {variant!r}")
    pad = 0.75 * size if pad_x is None else pad_x
    h = size + 0.8 * size            # comfortable vertical breathing room
    w = _text_width(text, size, mono) + 2 * pad
    rx = h / 2.0                     # full pill

    # Left edge from the anchor.
    if anchor == "middle":
        left = x - w / 2.0
    elif anchor == "end":
        left = x - w
    else:
        left = x
    top = y - h / 2.0
    face = mono_font if mono else font

    # Resolve the three roles (rect fill / rect stroke / text) per variant.
    stroke = ""
    if variant == "tint":
        rect = f'fill="{fill}" fill-opacity="0.14"'
        # Text sits on a near-white wash, so darken pale hues to keep it legible.
        txt = readable_on_white(fill) if text_colour is None else text_colour
    elif variant == "solid":
        rect = f'fill="{fill}"'
        txt = best_text_colour(fill) if text_colour is None else text_colour
        if keyline:
            stroke = f' stroke="{_WHITE}" stroke-width="2"'
    else:  # ghost
        rect = f'fill="{_WHITE}"'
        stroke = f' stroke="{fill}" stroke-width="1.5"'
        txt = readable_on_white(fill) if text_colour is None else text_colour

    def _f(v: float) -> str:
        return f"{v:.1f}".rstrip("0").rstrip(".")

    parts: List[str] = [f'<g transform="translate({_f(left)},{_f(top)})">']
    parts.append(
        f'<rect x="0" y="0" width="{_f(w)}" height="{_f(h)}" rx="{_f(rx)}" '
        f'{rect}{stroke}/>'
    )
    # Vertical baseline nudge: ~0.35·size below centre optically centres the cap
    # height for these UI-scale sizes.
    parts.append(
        f'<text x="{_f(w / 2)}" y="{_f(h / 2 + 0.35 * size)}" text-anchor="middle" '
        f'font-family="{face}" font-size="{_f(size)}" font-weight="{weight}" '
        f'fill="{txt}">{xml_escape(text)}</text>'
    )
    parts.append("</g>")
    return "".join(parts)

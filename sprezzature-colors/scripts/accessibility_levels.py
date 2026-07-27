"""
accessibility_levels — turn the canonical palette into one accessibility LEVEL.

The house position (see ``references/accessibility-levels.md``) is that the
DEFAULT should be the reasonable, accessibility-conscious standard, and that
stronger or deficiency-specific variants live on top as options rather than as
the price of entry. This module implements that as a single pure function,
:func:`apply_level`, that maps the canonical palette to a chosen level while
keeping the same colour names (so a figure that asks for ``"Blue"`` keeps asking
for ``"Blue"`` and simply receives the level-appropriate hex).

Levels
------
``universal`` (default)
    The curated Colour-Universal-Design-style palette, unchanged. Categories are
    already meant to be separated by lightness and never by hue alone (the
    figures add shape / label / position on top). This is the standard everyone
    gets without opting in.
``high-contrast``
    Each hue is darkened on the OKLCH L axis until it clears the Web Content
    Accessibility Guidelines (WCAG) AAA ratio of 7:1 against the background,
    for low vision and hostile lighting.
``monochrome``
    Every colour becomes the grey of its own relative luminance. Categories then
    ride entirely on lightness (plus the figure's shape / label redundancy),
    which is the print and total-colour-blindness case.
``deuteranopia`` / ``protanopia`` / ``tritanopia``
    A palette re-spaced so that, *as that viewer sees it*, every category is
    separated by lightness. Colours are ranked by their luminance under the
    Machado et al. (2009) simulation of the deficiency, then their OKLCH L is
    spread across a legible band (hue and chroma kept). Lightness is the one
    channel that survives every colour vision deficiency, so this guarantees the
    categories stay distinct for that specific viewer. There is no single
    colour-only palette that is optimal for all deficiencies at once, which is
    exactly why these are offered as *choices*, not as the default.

The maths (OKLCH round-trip, WCAG contrast, the Machado CVD matrices) is reused
from :mod:`_colors`, so this module adds no new colour science, only the
level policy. Pillow is not needed: colours are simulated one at a time via
:func:`_colors.simulate_pixel`.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _colors import (  # noqa: E402
    CVD_MATRICES,
    contrast_ratio_hex,
    linear_to_oklab,
    linear_to_srgb,
    oklab_to_linear,
    oklab_to_oklch,
    oklch_to_oklab,
    parse_hex,
    parse_hex_linear,
    rgb_to_hex,
    simulate_pixel,
    srgb_to_linear,
    to_hex,
)

#: Every supported level. ``universal`` is the default the figures ship in.
LEVELS: Tuple[str, ...] = (
    "universal",
    "high-contrast",
    "monochrome",
    "deuteranopia",
    "protanopia",
    "tritanopia",
)

#: The deficiency levels that are keys of :data:`_colors.CVD_MATRICES`.
_CVD_LEVELS = ("deuteranopia", "protanopia", "tritanopia")

#: Minimum WCAG contrast for a graphical mark against the background (AA, 3:1).
_MIN_MARK_CONTRAST = 3.0
#: AAA text contrast target for the ``high-contrast`` level.
_AAA_CONTRAST = 7.0


def _oklch(hexv: str) -> Tuple[float, float, float]:
    """Return the OKLCH ``(L, C, H)`` of a hex colour."""
    return oklab_to_oklch(linear_to_oklab(parse_hex_linear(hexv)))


def _with_lightness(hexv: str, lightness: float) -> str:
    """Return ``hexv`` with its OKLCH L replaced by ``lightness`` (chroma/hue kept)."""
    _, c, h = _oklch(hexv)
    lightness = max(0.0, min(1.0, lightness))
    return to_hex(oklab_to_linear(oklch_to_oklab((lightness, c, h))))


def _relative_luminance_hex(hexv: str) -> float:
    """WCAG relative luminance of a hex colour (linear-light Rec. 709 weights)."""
    r, g, b = parse_hex(hexv)
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)


def _to_gray(hexv: str) -> str:
    """Return the grey of ``hexv``'s own relative luminance (the greyscale test)."""
    v = linear_to_srgb(_relative_luminance_hex(hexv))
    return rgb_to_hex((v, v, v))


def _darken_to_contrast(hexv: str, target: float, bg: str) -> str:
    """Lower OKLCH L until contrast against ``bg`` reaches ``target`` (or L bottoms out)."""
    L, c, h = _oklch(hexv)
    out = hexv
    # 2% steps down the L axis; hue and chroma are preserved so the colour keeps
    # its identity, it only gets deeper. Stop once the ratio is met or we run out
    # of lightness to give.
    while contrast_ratio_hex(out, bg) < target and L > 0.02:
        L -= 0.02
        out = to_hex(oklab_to_linear(oklch_to_oklab((L, c, h))))
    return out


def _cvd_luminance(hexv: str, kind: str) -> float:
    """Relative luminance of ``hexv`` *as a viewer with ``kind`` sees it*."""
    r, g, b = simulate_pixel(parse_hex(hexv), CVD_MATRICES[kind])
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)


def _gray_at(lightness: float) -> str:
    """Return the neutral grey at OKLCH lightness ``lightness`` (chroma 0)."""
    lightness = max(0.0, min(1.0, lightness))
    return to_hex(oklab_to_linear(oklch_to_oklab((lightness, 0.0, 0.0))))


def _rank_spread(
    palette: Dict[str, str],
    luminance: Callable[[str], float],
    *,
    gray: bool,
    bg: str,
) -> Dict[str, str]:
    """Rank colours by ``luminance`` then spread their lightness across a band.

    Every category ends up separable by lightness, the one channel that survives
    all colour vision deficiencies. ``gray=True`` drops the hue (monochrome);
    otherwise hue and chroma are kept and only OKLCH L moves. Each mark is
    floored at the WCAG graphical-object contrast against ``bg``.
    """
    items: List[Tuple[str, str]] = list(palette.items())
    n = len(items)
    if n == 0:
        return {}
    order = sorted(range(n), key=lambda i: luminance(items[i][1]))
    # Grey can use a wider band (no hue to keep legible); coloured marks stay in
    # a mid band so even the lightest keeps contrast on white.
    lo, hi = (0.22, 0.85) if gray else (0.34, 0.72)
    out: Dict[str, str] = dict(palette)
    for rank, idx in enumerate(order):
        name, hexv = items[idx]
        target = (lo + hi) / 2.0 if n == 1 else lo + (hi - lo) * (rank / (n - 1))
        recol = _gray_at(target) if gray else _with_lightness(hexv, target)
        if contrast_ratio_hex(recol, bg) < _MIN_MARK_CONTRAST:
            recol = _darken_to_contrast(recol, _MIN_MARK_CONTRAST, bg)
        out[name] = recol
    return out


def apply_level(
    palette: Dict[str, str],
    level: str,
    *,
    bg: str = "#FFFFFF",
) -> Dict[str, str]:
    """Return ``palette`` remapped to an accessibility ``level`` (same keys).

    Parameters
    ----------
    palette : dict of str to str
        The canonical ``{name: "#RRGGBB"}`` mapping (e.g. from
        ``_style.load_palette``).
    level : str
        One of :data:`LEVELS`. ``"universal"`` returns the palette unchanged.
    bg : str, optional
        Background the marks sit on, for the contrast-driven levels. Defaults to
        white, the house figure background.

    Returns
    -------
    dict of str to str
        A new mapping with the same keys and level-appropriate hex values.

    Raises
    ------
    ValueError
        If ``level`` is not one of :data:`LEVELS`.

    Examples
    --------
    >>> pal = {"Blue": "#007AFF", "Green": "#34C759"}
    >>> apply_level(pal, "universal") == pal
    True
    >>> set(apply_level(pal, "monochrome")) == set(pal)
    True
    """
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}, got {level!r}")

    if level == "universal":
        return dict(palette)

    if level == "high-contrast":
        # Deepen every hue until it clears AAA against the background.
        return {name: _darken_to_contrast(hexv, _AAA_CONTRAST, bg) for name, hexv in palette.items()}

    if level == "monochrome":
        # Distinct greys by luminance rank, not faithful luminance: equally
        # bright hues (orange vs green) would otherwise map to the same grey and
        # collide. Ranked by the colours' own luminance so the order is stable.
        return _rank_spread(palette, _relative_luminance_hex, gray=True, bg=bg)

    # deuteranopia / protanopia / tritanopia: rank by how bright each colour
    # looks *to that viewer*, then spread the lightness so no two categories
    # collapse for them. Lightness is the channel that survives every deficiency.
    return _rank_spread(palette, lambda h: _cvd_luminance(h, level), gray=False, bg=bg)


def _main() -> int:
    """Preview a level: print ``name  #hex  contrast-vs-white`` for each colour."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _argparse import make_parser  # noqa: E402  (local import keeps module import light)

    parser = make_parser(
        prog="sprezzature-colors-levels",
        description="Preview the canonical palette remapped to an accessibility level.",
    )
    parser.add_argument("--level", choices=LEVELS, default="universal")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "references" / "palette.csv",
        help="palette CSV to read (default: the canonical references/palette.csv)",
    )
    args = parser.parse_args()

    import csv

    base: Dict[str, str] = {}
    with args.csv.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("Base") or "").strip()
            hexv = (row.get("Hexcode") or "").strip()
            if name and hexv.startswith("#"):
                base[name] = hexv.upper()

    leveled = apply_level(base, args.level)
    for name, hexv in leveled.items():
        print(f"{name:12} {hexv}  contrast-vs-white {contrast_ratio_hex(hexv, '#FFFFFF'):.1f}:1")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

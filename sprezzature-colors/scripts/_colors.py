"""
_colors
=======

Shared color primitives for ``sprezzature-colors``: sRGB ↔ linear, hex parsing,
WCAG luminance and contrast, OKLab / OKLCH conversions (Björn Ottosson),
perceptual ``lighten`` / ``darken`` on the OKLCH L axis, the Machado et
al. (2009) CVD simulation matrices, and the curated palette accessors
(Apple base + emotion / concept / psychology projections).

The palette ships as ``references/palette.csv`` — one row per canonical
color, with semantic projections as columns. Loaded lazily on first
access; no network at import time.

Pure Python, stdlib only. The CVD matrices intentionally do not require
NumPy (callers that need bulk image work use ``simulate_cvd.py``'s
per-pixel loop on top of Pillow).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable, cast

__all__ = [
    # sRGB primitives
    "srgb_to_linear",
    "linear_to_srgb",
    "parse_hex",
    "parse_hex_linear",
    "rgb_to_hex",
    "to_hex",
    # WCAG
    "relative_luminance",
    "contrast_ratio",
    "meets_wcag",
    "WCAG_THRESHOLDS",
    # OKLab / OKLCH
    "linear_to_oklab",
    "oklab_to_linear",
    "oklab_to_oklch",
    "oklch_to_oklab",
    # Perceptual
    "lighten",
    "darken",
    # CVD
    "CVD_MATRICES",
    "CVD_LABELS",
    "CVD_SHORTHAND",
    "simulate_pixel",
    # Palette accessors
    "load_palette",
    "apple_palette",
    "palette_names",
    "name_to_hex",
    "name_to_rgb",
    "light_variant",
    "emotion_to_hex",
    "emotions",
    "concept_search",
    "concepts",
    "psychology_for",
    # Class
    "Color",
]


# ── sRGB transfer ──────────────────────────────────────────────────────────

def srgb_to_linear(c: int) -> float:
    """Convert an 8-bit sRGB channel to linear sRGB in ``[0, 1]``."""
    f: float = c / 255.0
    return f / 12.92 if f <= 0.04045 else ((f + 0.055) / 1.055) ** 2.4


def linear_to_srgb(f: float) -> int:
    """Convert a linear-sRGB value to an 8-bit channel, clamped to ``[0, 255]``."""
    if f <= 0.0:
        return 0
    if f >= 1.0:
        return 255
    out: float = f * 12.92 if f <= 0.0031308 else 1.055 * f ** (1.0 / 2.4) - 0.055
    return max(0, min(255, round(out * 255)))


# ── Hex parsing ────────────────────────────────────────────────────────────

def _normalize_hex(s: str) -> str:
    """Strip ``#``, expand 3-digit shorthand, drop 8-digit alpha. Return a 6-hex string."""
    s = s.lstrip("#").strip()
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) == 8:
        # WCAG math is on opaque foregrounds — flatten transparency upstream.
        s = s[:6]
    if len(s) != 6:
        raise ValueError(f"Bad hex color: {s!r}")
    return s


def parse_hex(s: str) -> tuple[int, int, int]:
    """
    Parse a 3-, 6-, or 8-digit hex into an 8-bit ``(R, G, B)`` tuple.

    Returns plain integers in ``[0, 255]``. For the linear-sRGB form used by
    WCAG and OKLab math, see :func:`parse_hex_linear`.
    """
    s = _normalize_hex(s)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def parse_hex_linear(s: str) -> tuple[float, float, float]:
    """Parse a hex into a linear-light sRGB triple in ``[0.0, 1.0]``."""
    r, g, b = parse_hex(s)
    return srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)


def parse_hex_rgba(s: str) -> tuple[int, int, int, float]:
    """
    Parse a 3/4/6/8-digit hex into ``(R, G, B, A)``, alpha in ``[0.0, 1.0]``.

    Unlike :func:`parse_hex`, this keeps the alpha channel: 4- and 8-digit hex
    carry it (``#RGBA`` / ``#RRGGBBAA``); 3- and 6-digit are opaque (alpha 1.0).
    Needed for alpha-aware WCAG contrast — a semi-transparent foreground has to
    be composited over its background before the ratio means anything.
    """
    h = s.lstrip("#").strip()
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0
    if len(h) == 8:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16) / 255.0
    raise ValueError(f"Bad hex color: {s!r}")


def composite_over(
    fg_rgba: tuple[int, int, int, float],
    bg_rgb: tuple[int, int, int],
) -> tuple[int, int, int]:
    """
    Alpha-composite ``fg_rgba`` over an opaque ``bg_rgb`` (the "over" operator).

    Compositing is done in gamma/sRGB space (0–255), which is what browsers do
    when they paint a CSS ``rgba()`` color over a background — so the result
    matches the pixels a reader actually sees, and therefore the contrast they
    actually get. (Physically-linear compositing would differ, but CSS alpha is
    composited in sRGB, so this is the WCAG-relevant blend.)
    """
    r_f, g_f, b_f, a = fg_rgba
    r_b, g_b, b_b = bg_rgb
    return (
        round(r_f * a + r_b * (1.0 - a)),
        round(g_f * a + g_b * (1.0 - a)),
        round(b_f * a + b_b * (1.0 - a)),
    )


def flatten_alpha(
    color: str | tuple[int, int, int] | tuple[int, int, int, float],
    bg: str | tuple[int, int, int] = "#FFFFFF",
) -> tuple[int, int, int]:
    """
    Return an opaque ``(R, G, B)`` for ``color`` seen over ``bg``.

    Accepts a hex string (any of 3/4/6/8 digits) or an ``(R,G,B)`` / ``(R,G,B,A)``
    tuple. If ``bg`` itself is translucent it is first flattened over white — the
    page default — so nesting resolves to a concrete color. Opaque input is
    returned unchanged.
    """
    bg_rgb = parse_hex(bg) if isinstance(bg, str) else (bg[0], bg[1], bg[2])
    if isinstance(bg, str) and len(bg.lstrip("#").strip()) in (4, 8):
        bg_rgb = composite_over(parse_hex_rgba(bg), (255, 255, 255))
    if isinstance(color, str):
        r, g, b, a = parse_hex_rgba(color)
    elif len(color) == 4:
        r, g, b, a = color
    else:
        r, g, b, a = color[0], color[1], color[2], 1.0
    if a >= 1.0:
        return r, g, b
    return composite_over((r, g, b, a), bg_rgb)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Format an 8-bit ``(R, G, B)`` tuple as an upper-case ``#RRGGBB`` string."""
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


def to_hex(rgb_linear: tuple[float, float, float]) -> str:
    """Format a linear-sRGB triple as an upper-case ``#RRGGBB`` string."""
    return "#" + "".join(f"{linear_to_srgb(c):02X}" for c in rgb_linear)


# ── WCAG luminance + contrast ──────────────────────────────────────────────

#: WCAG 2.x minimum contrast thresholds. The mapping is ``(level, size) → ratio``.
WCAG_THRESHOLDS: dict[tuple[str, str], float] = {
    ("AA",  "normal"): 4.5,
    ("AA",  "large"):  3.0,
    ("AAA", "normal"): 7.0,
    ("AAA", "large"):  4.5,
}


def relative_luminance(rgb_linear: tuple[float, float, float]) -> float:
    """WCAG relative luminance from a linear-sRGB triple."""
    r, g, b = rgb_linear
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    """WCAG contrast ratio between two linear-sRGB colours. Range: ``[1.0, 21.0]``."""
    la = relative_luminance(a)
    lb = relative_luminance(b)
    light = max(la, lb)
    dark = min(la, lb)
    return (light + 0.05) / (dark + 0.05)


def contrast_ratio_hex(
    fg: str | tuple[int, int, int] | tuple[int, int, int, float],
    bg: str | tuple[int, int, int],
) -> float:
    """
    Alpha-aware WCAG contrast ratio between ``fg`` and ``bg``.

    A translucent foreground is composited over ``bg`` first (see
    :func:`flatten_alpha`), so the ratio reflects the color the reader actually
    sees rather than the raw, un-painted foreground. Opaque inputs give the same
    answer as :func:`contrast_ratio`.
    """
    fg_rgb = flatten_alpha(fg, bg)
    bg_rgb = flatten_alpha(bg) if isinstance(bg, str) else (bg[0], bg[1], bg[2])
    fg_lin = tuple(srgb_to_linear(c) for c in fg_rgb)
    bg_lin = tuple(srgb_to_linear(c) for c in bg_rgb)
    return contrast_ratio(
        cast("tuple[float, float, float]", fg_lin),
        cast("tuple[float, float, float]", bg_lin),
    )


def meets_wcag(
    fg: str | tuple[int, int, int],
    bg: str | tuple[int, int, int],
    level: str = "AA",
    size: str = "normal",
) -> bool:
    """
    Test whether ``fg`` over ``bg`` meets WCAG 2.x at the given level / size.

    Parameters
    ----------
    fg, bg : str or tuple of int
        Hex strings (``"#RRGGBB"``) or 8-bit ``(R, G, B)`` tuples.
    level : {"AA", "AAA"}
    size : {"normal", "large"}
        ``"large"`` is ≥18 pt regular or ≥14 pt bold per WCAG.
    """
    try:
        target: float = WCAG_THRESHOLDS[(level, size)]
    except KeyError as e:
        raise ValueError(
            f"Unknown WCAG (level, size): ({level!r}, {size!r}). "
            f"Valid: {sorted(WCAG_THRESHOLDS.keys())}"
        ) from e
    # Alpha-aware: flatten a translucent fg over bg (and bg over white) before
    # the ratio, so #RRGGBBAA foregrounds are judged as rendered, not raw.
    return contrast_ratio_hex(fg, bg) >= target


# ── OKLab / OKLCH (Björn Ottosson) ─────────────────────────────────────────

def linear_to_oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert linear sRGB to OKLab. Input and output ranges follow Ottosson's spec."""
    r, g, b = rgb
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_ = l ** (1 / 3) if l >= 0 else -(-l) ** (1 / 3)
    m_ = m ** (1 / 3) if m >= 0 else -(-m) ** (1 / 3)
    s_ = s ** (1 / 3) if s >= 0 else -(-s) ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linear(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    """Inverse of :func:`linear_to_oklab`."""
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l = l_ ** 3
    m = m_ ** 3
    s = s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def oklab_to_oklch(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    """OKLab → OKLCH (polar). ``H`` is in degrees in ``[0, 360)``."""
    L, a, b = lab
    C = math.sqrt(a * a + b * b)
    H = math.degrees(math.atan2(b, a))
    if H < 0:
        H += 360
    return L, C, H


def oklch_to_oklab(lch: tuple[float, float, float]) -> tuple[float, float, float]:
    """OKLCH → OKLab."""
    L, C, H = lch
    rad = math.radians(H)
    return L, C * math.cos(rad), C * math.sin(rad)


# ── Perceptual lighten / darken ────────────────────────────────────────────

def _shift_lightness(hex_or_rgb: str | tuple[int, int, int], delta: float) -> str:
    """Shift OKLCH ``L`` by ``delta`` (clamped to ``[0, 1]``); chroma / hue preserved."""
    if isinstance(hex_or_rgb, str):
        lin = parse_hex_linear(hex_or_rgb)
    else:
        lin = cast("tuple[float, float, float]", tuple(srgb_to_linear(c) for c in hex_or_rgb))
    L, C, H = oklab_to_oklch(linear_to_oklab(lin))
    new_L = max(0.0, min(1.0, L + delta))
    out = oklab_to_linear(oklch_to_oklab((new_L, C, H)))
    return to_hex(out)


def lighten(hex_or_rgb: str | tuple[int, int, int], amount: float = 0.1) -> str:
    """
    Return ``hex_or_rgb`` lightened by ``amount`` on the OKLCH L axis.

    ``amount`` is a fraction in ``[0, 1]``; ``0.1`` is a noticeable but
    moderate tint. Chroma and hue are preserved — unlike a naïve RGB
    offset, this stays on the same perceptual hue line.
    """
    if amount < 0:
        raise ValueError("amount must be >= 0; use darken() to go the other way")
    return _shift_lightness(hex_or_rgb, +amount)


def darken(hex_or_rgb: str | tuple[int, int, int], amount: float = 0.1) -> str:
    """Return ``hex_or_rgb`` darkened by ``amount`` on the OKLCH L axis."""
    if amount < 0:
        raise ValueError("amount must be >= 0; use lighten() to go the other way")
    return _shift_lightness(hex_or_rgb, -amount)


# ── CVD simulation (Machado et al. 2009, severity 1.0) ─────────────────────

#: Map from CVD type to the 3×3 matrix applied in linear sRGB.
CVD_MATRICES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281,  0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501,  0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809,  0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}

#: Long-form CVD labels for mosaic / UI labelling.
CVD_LABELS: dict[str, str] = {
    "protanopia":   "Protanopia — no L (red) cones",
    "deuteranopia": "Deuteranopia — no M (green) cones",
    "tritanopia":   "Tritanopia — no S (blue) cones",
}

#: Short CLI aliases (``prot`` / ``deut`` / ``trit``).
CVD_SHORTHAND: dict[str, str] = {
    "prot": "protanopia",
    "deut": "deuteranopia",
    "trit": "tritanopia",
}


def simulate_pixel(
    rgb: tuple[int, int, int],
    matrix: tuple[tuple[float, float, float], ...],
) -> tuple[int, int, int]:
    """Apply a CVD matrix to a single 8-bit sRGB pixel."""
    # The matrix works in linear light — sRGB-decode in, sRGB-encode out.
    r: float = srgb_to_linear(rgb[0])
    g: float = srgb_to_linear(rgb[1])
    b: float = srgb_to_linear(rgb[2])
    nr: float = matrix[0][0] * r + matrix[0][1] * g + matrix[0][2] * b
    ng: float = matrix[1][0] * r + matrix[1][1] * g + matrix[1][2] * b
    nb: float = matrix[2][0] * r + matrix[2][1] * g + matrix[2][2] * b
    return linear_to_srgb(nr), linear_to_srgb(ng), linear_to_srgb(nb)


# ── Palette (one canonical row per color, multiple semantic projections) ───

_PALETTE_PATH: Path = Path(__file__).resolve().parent.parent / "references" / "palette.csv"

#: Cached palette rows. Each row is a dict keyed by the CSV header column.
_PALETTE_CACHE: list[dict[str, str]] | None = None


def _split_list(field: str) -> list[str]:
    """Split a comma-separated semantic field into trimmed non-empty tokens."""
    return [s.strip() for s in field.split(",") if s.strip()]


def load_palette() -> list[dict[str, str]]:
    """
    Load the canonical palette CSV. Each row has columns:

    ``Hexcode``, ``R``, ``G``, ``B``, ``Base``, ``LightHex``, ``Emotion``,
    ``Concepts``, ``PsychologyPositive``, ``PsychologyNegative``.

    Multi-valued semantic columns (``Concepts``, ``PsychologyPositive``,
    ``PsychologyNegative``) remain comma-separated strings in this raw view;
    the higher-level accessors split them.
    """
    global _PALETTE_CACHE
    if _PALETTE_CACHE is None:
        with _PALETTE_PATH.open(encoding="utf-8") as f:
            _PALETTE_CACHE = list(csv.DictReader(f))
    return _PALETTE_CACHE


def apple_palette() -> dict[str, str]:
    """
    Return the base Apple-curated palette as ``{base_name: hex}``.

    Excludes colors without a ``Base`` name and colors whose ``Base`` is a
    neutral (Black / White / Gray / Brown) — i.e. only the saturated Apple
    system colors. For all named colors including neutrals, use
    :func:`palette_names`.
    """
    saturated = {"Red", "Orange", "Yellow", "Green", "Turquoise", "Blue", "Purple", "Pink"}
    return {row["Base"]: row["Hexcode"] for row in load_palette() if row["Base"] in saturated}


def palette_names() -> list[str]:
    """Return every ``Base`` name in the palette, in CSV order."""
    return [row["Base"] for row in load_palette() if row["Base"]]


def name_to_hex(name: str) -> str:
    """Look up a base color name (case-insensitive). Raises ``KeyError`` if unknown."""
    key = name.strip().lower()
    for row in load_palette():
        if row["Base"].lower() == key:
            return row["Hexcode"]
    raise KeyError(f"Unknown color name: {name!r}. Known: {palette_names()}")


def name_to_rgb(name: str) -> tuple[int, int, int]:
    """Look up a base color name and return its 8-bit ``(R, G, B)`` tuple."""
    return parse_hex(name_to_hex(name))


def light_variant(name_or_hex: str) -> str | None:
    """
    Return the curated light tonal variant for an Apple base color, if any.

    ``name_or_hex`` may be a base name (``"Red"``) or a hex string
    (``"#FF3B30"``). Returns ``None`` for colors without a curated light
    variant (neutrals, Brown, Pink in some sources). Use :func:`lighten`
    when you need an algorithmic shift instead.
    """
    s = name_or_hex.strip()
    is_hex = s.startswith("#") or (len(s) in (3, 6, 8) and all(c in "0123456789abcdefABCDEF" for c in s))
    if is_hex:
        try:
            target = "#" + _normalize_hex(s).upper()
        except ValueError:
            target = None
    else:
        target = None
    name_key = s.lower()
    for row in load_palette():
        match = (target is not None and row["Hexcode"].upper() == target) or row["Base"].lower() == name_key
        if match:
            return row["LightHex"] or None
    return None


def emotions() -> dict[str, str]:
    """Return the ``{emotion: hex}`` projection."""
    return {row["Emotion"]: row["Hexcode"] for row in load_palette() if row["Emotion"]}


def emotion_to_hex(emotion: str) -> str:
    """Look up the hex for an emotion. Raises ``KeyError`` if unknown."""
    table = emotions()
    key = emotion.strip().lower()
    for k, v in table.items():
        if k.lower() == key:
            return v
    raise KeyError(f"Unknown emotion: {emotion!r}. Known: {sorted(table.keys())}")


def concepts() -> list[tuple[list[str], str]]:
    """Return ``[(concept_keywords, hex), ...]`` for every palette row with concepts."""
    return [(_split_list(row["Concepts"]), row["Hexcode"]) for row in load_palette() if row["Concepts"]]


def concept_search(keyword: str) -> list[str]:
    """
    Return every hex whose concept keywords contain ``keyword`` (case-insensitive).

    A single concept row can attach to a single color; this returns all matches.
    """
    key = keyword.strip().lower()
    return [hex_ for keywords, hex_ in concepts() if any(key == k.lower() for k in keywords)]


def psychology_for(name_or_hex: str) -> dict[str, list[str]] | None:
    """
    Return ``{"positive": [...], "negative": [...]}`` for a color, or ``None``.

    Lookup is by base name (``"Red"``) or hex (``"#FF3B30"``).
    """
    s = name_or_hex.strip()
    if s.startswith("#"):
        target = "#" + _normalize_hex(s).upper()
        rows = [r for r in load_palette() if r["Hexcode"].upper() == target]
    else:
        key = s.lower()
        rows = [r for r in load_palette() if r["Base"].lower() == key]
    if not rows:
        return None
    row = rows[0]
    pos = _split_list(row["PsychologyPositive"])
    neg = _split_list(row["PsychologyNegative"])
    if not pos and not neg:
        return None
    return {"positive": pos, "negative": neg}


# ── Ergonomic class wrapper ────────────────────────────────────────────────

class Color:
    """
    Small immutable wrapper around an 8-bit sRGB color with convenient views.

    >>> blue = Color("#007AFF")
    >>> blue.lighten(0.15).hex
    '#5FA8FF'  # doctest: +SKIP
    >>> blue.contrast_with("#FFFFFF")  # doctest: +SKIP
    4.55
    >>> blue.meets_wcag("#FFFFFF")
    True
    """

    __slots__ = ("_rgb",)

    def __init__(self, value: str | tuple[int, int, int] | Iterable[int]) -> None:
        """Build a Color from a hex string or an ``(r, g, b)`` 0–255 triple."""
        if isinstance(value, str):
            self._rgb: tuple[int, int, int] = parse_hex(value)
        else:
            r, g, b = (int(v) for v in value)
            if not all(0 <= v <= 255 for v in (r, g, b)):
                raise ValueError(f"RGB channels must be in [0, 255]; got ({r}, {g}, {b})")
            self._rgb = (r, g, b)

    @classmethod
    def from_name(cls, name: str) -> "Color":
        """Build a Color from a curated palette base name (e.g. ``"Red"``, ``"Blue"``).

        Names are the ``Base`` column of the curated palette (case-insensitive),
        not the full CSS/X11 set; an unknown name raises ``KeyError``.
        """
        return cls(name_to_hex(name))

    @property
    def rgb(self) -> tuple[int, int, int]:
        """The ``(r, g, b)`` channels as integers in ``[0, 255]``."""
        return self._rgb

    @property
    def hex(self) -> str:
        """The colour as a ``#rrggbb`` hex string."""
        return rgb_to_hex(self._rgb)

    @property
    def linear(self) -> tuple[float, float, float]:
        """The colour in linear-light sRGB (each channel gamma-expanded)."""
        return tuple(srgb_to_linear(c) for c in self._rgb)  # type: ignore[return-value]

    @property
    def oklch(self) -> tuple[float, float, float]:
        """The colour as OKLCH ``(L, C, H)`` (perceptual lightness/chroma/hue)."""
        return oklab_to_oklch(linear_to_oklab(self.linear))

    def lighten(self, amount: float = 0.1) -> "Color":
        """Return a copy lightened by ``amount`` on the OKLCH L axis."""
        return Color(lighten(self.hex, amount))

    def darken(self, amount: float = 0.1) -> "Color":
        """Return a copy darkened by ``amount`` on the OKLCH L axis."""
        return Color(darken(self.hex, amount))

    def contrast_with(self, other: "Color | str | tuple[int, int, int]") -> float:
        """WCAG contrast ratio (1–21) between this colour and ``other``."""
        other_c = other if isinstance(other, Color) else Color(other)
        return contrast_ratio(self.linear, other_c.linear)

    def meets_wcag(
        self,
        other: "Color | str | tuple[int, int, int]",
        level: str = "AA",
        size: str = "normal",
    ) -> bool:
        """True iff this colour on ``other`` meets the WCAG ``level`` at ``size``."""
        return meets_wcag(self.hex, other.hex if isinstance(other, Color) else other, level, size)

    def __repr__(self) -> str:
        """Unambiguous ``Color("#rrggbb")`` representation."""
        return f"Color({self.hex!r})"

    def __eq__(self, other: object) -> bool:
        """Two Colors are equal iff their RGB triples match."""
        return isinstance(other, Color) and other._rgb == self._rgb

    def __hash__(self) -> int:
        """Hash by RGB triple so Colors are usable as dict keys / in sets."""
        return hash(self._rgb)

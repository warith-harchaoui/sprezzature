"""
_style — house-style tokens shared by every make/audit script.

Exposes the single source of truth for palette, typography, and Vega
/ matplotlib configuration. When ``sprezzature-colors`` is co-installed
next to ``sprezzature-figures``, the palette is read from
``sprezzature-colors/references/palette.csv`` to keep make ↔ audit brand
tokens from drifting; otherwise the module's built-in curated
fallback (the same 8 saturated Apple-system hues) is used.

The module is **stdlib-only** — no numpy, no matplotlib, no pandas
at import time — so ``audit_figure.py`` can pull tokens without
installing the dataviz tier.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------------
# Built-in curated fallback — the Apple-inspired 8 + 4 neutrals.
# The canonical source is sprezzature-colors/references/palette.csv, which
# projects each hex onto four semantic axes: **Emotion**, **Concepts**,
# **PsychologyPositive**, **PsychologyNegative**. The full mapping is
# documented at <https://harchaoui.org/warith/colors/>. When the CSV is
# available, :func:`load_semantic_palette` reads it. This fallback is
# used only when neither ``sprezzature-colors`` nor ``SPREZZATURE_COLORS_PALETTE``
# can be resolved.
# ------------------------------------------------------------------
_FALLBACK_PALETTE: Dict[str, str] = {
    # 8 saturated hues.
    "Red":    "#FF3B30",
    "Orange": "#FF9500",
    "Yellow": "#FFCC00",
    "Green":  "#34C759",
    "Mint":   "#00C7BE",
    "Teal":   "#5AC8FA",
    "Blue":   "#007AFF",
    "Purple": "#AF52DE",
    # 4 neutrals.
    "Gray":   "#8E8E93",
    "Brown":  "#A2845E",
    "Black":  "#000000",
    "White":  "#FFFFFF",
}


#: Emotion → hex fallback, mirroring the ``Emotion`` column of the
#: sprezzature-colors CSV. Anger / Sadness / Joy etc. Source:
#: <https://harchaoui.org/warith/colors/>.
_FALLBACK_EMOTIONS: Dict[str, str] = {
    "Anger":     "#FF3B30",
    "Surprise":  "#FF9500",
    "Joy":       "#FFCC00",
    "Disgust":   "#34C759",
    "Happiness": "#00C7BE",
    "Sadness":   "#007AFF",
    "Fear":      "#AF52DE",
    "Love":      "#FF2D55",
    "Comfort":   "#A2845E",
    "Silence":   "#000000",
    "Neutral":   "#8E8E93",
    "Peace":     "#FFFFFF",
}


def _sibling_palette_csv() -> Optional[Path]:
    """Locate ``sprezzature-colors/references/palette.csv`` if co-installed.

    Returns
    -------
    pathlib.Path or None
        The path to the CSV if found; ``None`` otherwise. Search:

        1. ``SPREZZATURE_COLORS_PALETTE`` env var (explicit override).
        2. Sibling directory (``../../sprezzature-colors/references/palette.csv``
           relative to this file).
        3. ``~/.claude/skills/sprezzature-colors/references/palette.csv``.
        4. ``~/.opencode/skills/sprezzature-colors/references/palette.csv``.
    """
    env = os.environ.get("SPREZZATURE_COLORS_PALETTE", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p

    here = Path(__file__).resolve()
    # sprezzature-figures/scripts/_style.py -> repo-root/sprezzature-colors/references/palette.csv
    sibling = here.parent.parent.parent / "sprezzature-colors" / "references" / "palette.csv"
    if sibling.is_file():
        return sibling

    for runtime in ("claude", "opencode"):
        p = Path.home() / f".{runtime}" / "skills" / "sprezzature-colors" / "references" / "palette.csv"
        if p.is_file():
            return p

    return None


def _sibling_sprezzature_colors_scripts() -> Optional[Path]:
    """Locate ``sprezzature-colors/scripts`` (the accessibility-level engine) if present.

    Same co-installation search as :func:`_sibling_palette_csv`, one directory
    over. Returns ``None`` when sprezzature-colors is not alongside, in which case only
    the ``universal`` level is available (see :func:`load_palette`).
    """
    csv_path = _sibling_palette_csv()
    if csv_path is not None:
        # references/palette.csv -> ../scripts
        scripts = csv_path.parent.parent / "scripts"
        if (scripts / "accessibility_levels.py").is_file():
            return scripts
    return None


def _apply_accessibility_level(palette: Dict[str, str], level: str) -> Dict[str, str]:
    """Remap ``palette`` to an accessibility ``level`` via the sprezzature-colors engine.

    The colour science (OKLCH round-trip, WCAG contrast, Machado colour-vision
    matrices) lives in ``sprezzature-colors/scripts/accessibility_levels.py`` so it is
    not duplicated here. When sprezzature-colors is not co-installed, or the level is
    unknown, the palette is returned unchanged and a warning is emitted, so a
    figure never crashes over accessibility styling.
    """
    scripts = _sibling_sprezzature_colors_scripts()
    if scripts is None:
        warnings.warn(
            f"accessibility level {level!r} requested but sprezzature-colors is not "
            "co-installed; using the universal palette",
            stacklevel=2,
        )
        return palette
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        from accessibility_levels import apply_level  # noqa: PLC0415 (lazy, optional dep)

        return apply_level(palette, level)
    except Exception as exc:  # pragma: no cover - defensive; never break a figure
        warnings.warn(f"accessibility level {level!r} failed ({exc}); using universal", stacklevel=2)
        return palette


def load_palette(accessibility: str = "universal") -> Dict[str, str]:
    """Read the canonical palette, at a chosen accessibility level.

    Parameters
    ----------
    accessibility : str, optional
        The accessibility level to render the palette at. ``"universal"``
        (default) is the curated, colour-vision-safe standard everyone gets.
        Other levels are ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` and ``"tritanopia"``; they are
        applied by the sprezzature-colors engine when it is co-installed. See
        ``sprezzature-colors/references/accessibility-levels.md`` for the model.

    Returns
    -------
    dict of str to str
        Mapping ``{"Red": "#FF3B30", ...}``. Keys are the palette CSV's ``Base``
        values; values are the level-appropriate hex. Order follows the CSV; the
        fallback follows the order in ``_FALLBACK_PALETTE``.
    """
    csv_path = _sibling_palette_csv()
    if csv_path is None:
        palette = dict(_FALLBACK_PALETTE)
    else:
        palette = {}
        with csv_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = (row.get("Base") or row.get("name") or "").strip()
                hexv = (row.get("Hexcode") or row.get("Hex") or row.get("hex") or "").strip()
                if name and hexv.startswith("#") and len(hexv) in (4, 7):
                    palette[name] = hexv.upper()
        palette = palette or dict(_FALLBACK_PALETTE)

    # ``universal`` is the identity, so the default path never touches the engine
    # and stays byte-for-byte what it always produced.
    if accessibility and accessibility != "universal":
        palette = _apply_accessibility_level(palette, accessibility)
    return palette


def leveled_colors(colors: Dict[str, str], accessibility: str = "universal") -> Dict[str, str]:
    """Apply an accessibility level to an *arbitrary* ``{name: hex}`` colour set.

    Some figures pick categorical colours that are not the shared palette (a
    curated per-species or per-class set tuned during the accessibility pass).
    Wrapping that set with this helper lets the figure still answer to the
    ``accessibility`` argument without adopting the house palette: ``universal``
    returns the colours unchanged (so the default figure is byte-for-byte the
    same), and every other level remaps *these* colours through the same
    sprezzature-colors engine that levels the palette.

    Do NOT use this on a continuous / perceptual colour map (viridis, a single
    hue ramp): those are already colour-vision- and greyscale-safe by
    construction, and re-spacing their anchors by lightness would de-tune them.
    Leave such maps at ``universal``.

    Parameters
    ----------
    colors : dict of str to str
        The figure's own ``{category: "#RRGGBB"}`` mapping.
    accessibility : str, optional
        One of the levels understood by :func:`load_palette`. Defaults to
        ``"universal"`` (the identity).

    Returns
    -------
    dict of str to str
        The same keys, remapped to the level (or unchanged for ``universal``).
    """
    if not accessibility or accessibility == "universal":
        return dict(colors)
    return _apply_accessibility_level(colors, accessibility)


def os_adaptive_style(
    series: Dict[str, str],
    *,
    role: str = "fill",
    forced: bool = False,
    forced_keyword: str = "CanvasText",
    extra_contrast: str = "",
    extra_forced: str = "",
) -> str:
    """Emit the additive ``@media`` overrides that let one SVG adapt to the OS.

    The idea behind the "OS-adaptive" figure: ship *one* SVG that quietly
    retunes itself when the reader's operating system signals a preference,
    instead of a separate file per level. This returns only the ``@media``
    blocks — append them **inside the figure's existing** ``<style>``. Because
    a CSS class rule outranks an inline ``fill=""``/``stroke=""`` presentation
    attribute, and because *every* rule here lives inside a media query, the
    default render (no preference active) matches none of them and stays
    byte-for-byte what the figure always produced. Only when the OS asks does a
    block take over.

    Two signals are handled, deliberately:

    - ``prefers-contrast: more`` — deepen each series to its ``high-contrast``
      hue (via the same sprezzature-colors engine that levels the palette) on the
      chosen ``role``. This is the broad, safe win: it never loses category
      identity, it only strengthens it.
    - ``forced-colors: active`` (Windows High Contrast and kin) — opt-in via
      ``forced=True``. Only meaningful for figures whose category identity is
      carried by **position or shape, not colour** (a Venn, a parliament, a
      waffle): those can drop to system-palette line art and still read. Do
      **not** set ``forced=True`` on a colour-encoded figure (multi-line,
      stacked area, heatmap) — the ~4-colour system palette cannot preserve the
      encoding, and the browser leaves SVG fills alone by default, which is the
      correct behaviour there.

    ``prefers-color-scheme: dark`` is intentionally **not** handled: on a
    light-poster figure it needs a real design pass (ink inversion, blend-mode
    flips), not a hue swap, so it is left to a separate, deliberate effort.

    Parameters
    ----------
    series : dict of str to str
        Maps a **CSS selector** (e.g. ``".bar-3"``, ``".setlabel-A"``) to that
        series' base hex. The whole set is deepened together so the
        ``high-contrast`` spacing stays balanced.
    role : str, optional
        Which property the hue drives on these selectors under
        ``prefers-contrast``: ``"fill"`` (default), ``"stroke"``, or ``"both"``.
    forced : bool, optional
        Emit a ``forced-colors: active`` block. Default ``False``.
    forced_keyword : str, optional
        System colour keyword the selectors take under forced colours
        (``"CanvasText"`` default; ``"Canvas"`` for fills you want to blank).
    extra_contrast, extra_forced : str, optional
        Figure-specific CSS appended inside the respective block — for the
        legibility tuning the engine cannot know (e.g. dropping a lobe's
        ``fill-opacity`` so region counts stay readable, or a text backplate).

    Returns
    -------
    str
        The ``@media`` block(s), ready to concatenate into the figure's
        ``<style>``. Empty selectors + no ``forced`` + no extras yield ``""``.
    """
    if role not in ("fill", "stroke", "both"):
        raise ValueError(f"role must be fill/stroke/both, got {role!r}")

    blocks: List[str] = []

    # ---- prefers-contrast: more -> deepened, higher-contrast hues ----
    hc = leveled_colors(series, "high-contrast") if series else {}
    contrast_rows: List[str] = []
    for selector, hexv in hc.items():
        if role == "fill":
            decl = f"fill:{hexv};"
        elif role == "stroke":
            decl = f"stroke:{hexv};"
        else:
            decl = f"fill:{hexv};stroke:{hexv};"
        contrast_rows.append(f"{selector}{{{decl}}}")
    if extra_contrast:
        contrast_rows.append(extra_contrast)
    if contrast_rows:
        blocks.append(
            "@media (prefers-contrast: more){\n  " + "\n  ".join(contrast_rows) + "\n}"
        )

    # ---- forced-colors: active -> hand identity to the system palette ----
    if forced or extra_forced:
        forced_rows = [f"{selector}{{fill:{forced_keyword};}}" for selector in series]
        if extra_forced:
            forced_rows.append(extra_forced)
        blocks.append(
            "@media (forced-colors: active){\n  " + "\n  ".join(forced_rows) + "\n}"
        )

    return "\n".join(blocks)


#: House inks and their dark-mode counterparts. The generators pull ink from a
#: shared, fixed set (`_BG` #FFFFFF, `_INK` #1D1D1F, `_SUBTLE` #6E6E73), so a
#: single attribute-selector block flips the whole catalogue to a dark surface
#: without per-figure bespoke selectors.
_DARK_INK_MAP: Dict[str, str] = {
    "#FFFFFF": "#0B0B0C",   # paper -> near-black surface
    "#1D1D1F": "#F2F2F7",   # primary ink -> off-white
    "#6E6E73": "#9C9CA3",   # secondary ink -> light grey
}


def os_dark_style(*, ink_map: Optional[Dict[str, str]] = None, screen_blend: bool = True, extra: str = "") -> str:
    """Emit an additive ``prefers-color-scheme: dark`` block for a house figure.

    Because every generator inks its text and paper from the same fixed
    constants, dark mode is mostly uniform: invert the paper and the two ink
    tiers with attribute selectors (`[fill="#RRGGBB"]`), and flip any
    ``mix-blend-mode: multiply`` group to ``screen`` so overlaps *lighten* on a
    dark surface instead of turning to mud. The data hues are left alone (the
    saturated house palette reads on dark). White keylines and halos
    (``stroke="#FFFFFF"``) are deliberately not touched — white-on-dark still
    separates marks. Anything figure-specific (a light panel, a custom
    gridline, a white pill that should darken) goes through ``extra``.

    The block is additive and media-gated, so the default (light) render is
    unchanged; it only applies when the reader's operating system asks for dark.

    Parameters
    ----------
    ink_map : dict of str to str, optional
        Light-hex -> dark-hex overrides. Defaults to :data:`_DARK_INK_MAP`
        (paper + the two ink tiers). Keys are matched as ``[fill="key"]``.
    screen_blend : bool, optional
        If ``True`` (default), flip ``mix-blend-mode: multiply`` groups to
        ``screen`` for correct overlap behaviour on dark.
    extra : str, optional
        Figure-specific CSS appended inside the block.

    Returns
    -------
    str
        A single ``@media (prefers-color-scheme: dark){ ... }`` block, or ``""``
        if nothing would be emitted.
    """
    rows: List[str] = []
    for light, dark in (ink_map or _DARK_INK_MAP).items():
        rows.append(f'[fill="{light}"]{{fill:{dark};}}')
    if screen_blend:
        rows.append('[style*="multiply"]{mix-blend-mode:screen;}')
    if extra:
        rows.append(extra)
    if not rows:
        return ""
    return "@media (prefers-color-scheme: dark){\n  " + "\n  ".join(rows) + "\n}"


#: A cycling set of forced-colors fill patterns. Each is a `Canvas`-backed tile
#: stroked/dotted in `CanvasText`, so it renders in the reader's system theme
#: and survives Windows High Contrast, where a colour encoding would collapse.
_FC_PATTERN_TILES: List[str] = [
    '<rect width="8" height="8" fill="Canvas"/><path d="M0,8L8,0" stroke="CanvasText" stroke-width="1.6"/>',       # diag /
    '<rect width="8" height="8" fill="Canvas"/><path d="M0,0L8,8" stroke="CanvasText" stroke-width="1.6"/>',       # diag \
    '<rect width="8" height="8" fill="Canvas"/><path d="M0,4L8,4" stroke="CanvasText" stroke-width="1.6"/>',       # horizontal
    '<rect width="8" height="8" fill="Canvas"/><path d="M4,0L4,8" stroke="CanvasText" stroke-width="1.6"/>',       # vertical
    '<rect width="10" height="10" fill="Canvas"/><circle cx="5" cy="5" r="1.8" fill="CanvasText"/>',               # dots
    '<rect width="8" height="8" fill="Canvas"/><path d="M0,4L8,4M4,0L4,8" stroke="CanvasText" stroke-width="1.4"/>',  # cross
]


def forced_color_patterns(series: List[str], *, prefix: str = "fcp") -> Tuple[str, str]:
    """Build per-series SVG patterns + the forced-colors block that applies them.

    For a colour-*encoded* figure (multi-line, streamgraph, many wedges) the
    roughly four-colour Windows High Contrast palette cannot preserve the
    encoding, and a flat system colour would merge every series. This gives each
    series a distinct **pattern** (hatch, dots, cross) drawn in ``Canvas`` /
    ``CanvasText``, so identity survives without colour. ``forced-color-adjust:
    none`` keeps the pattern fill from being overridden by the user agent.

    The patterns are additive and only referenced inside the forced-colors media
    query, so the default render is unchanged.

    Parameters
    ----------
    series : list of str
        The CSS selectors (e.g. ``[".river-0", ".river-1", ...]``) whose fills
        should become patterns under forced colours, in order.
    prefix : str, optional
        Id prefix for the generated ``<pattern>`` elements. Defaults to
        ``"fcp"``. Pass a figure-unique prefix if a page inlines several SVGs.

    Returns
    -------
    tuple of (str, str)
        ``(defs, style)`` — the ``<pattern>`` definitions to drop anywhere in
        the SVG, and the ``@media (forced-colors: active){ ... }`` block to
        append inside ``<style>``. Both are ``""`` when ``series`` is empty.
    """
    if not series:
        return "", ""
    defs: List[str] = []
    rules: List[str] = []
    for i, selector in enumerate(series):
        pid = f"{prefix}-{i}"
        tile = _FC_PATTERN_TILES[i % len(_FC_PATTERN_TILES)]
        # A 10-unit tile for dots, 8 for the rest; patternUnits keeps it stable
        # under the figure's own transforms.
        size = 10 if "circle" in tile else 8
        defs.append(
            f'<pattern id="{pid}" width="{size}" height="{size}" '
            f'patternUnits="userSpaceOnUse">{tile}</pattern>'
        )
        rules.append(f"{selector}{{fill:url(#{pid});forced-color-adjust:none;}}")
    style = "@media (forced-colors: active){\n  " + "\n  ".join(rules) + "\n}"
    return "".join(defs), style


def load_semantic_palette() -> Dict[str, Dict[str, Any]]:
    """Load the full semantic palette (base + emotion + concepts + psychology).

    Reads every column of ``sprezzature-colors/references/palette.csv``:
    ``Hexcode``, ``Base``, ``LightHex``, ``Emotion``, ``Concepts``,
    ``PsychologyPositive``, ``PsychologyNegative``. Documented at
    <https://harchaoui.org/warith/colors/>.

    Returns
    -------
    dict of str to dict
        Mapping ``{base_color_name: {"hex": "#RRGGBB", "light":
        "#RRGGBB", "emotion": str, "concepts": [str, ...],
        "psychology_positive": [str, ...],
        "psychology_negative": [str, ...]}}``.
    """
    csv_path = _sibling_palette_csv()
    if csv_path is None:
        return _fallback_semantic()

    out: Dict[str, Dict[str, Any]] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            base = (row.get("Base") or "").strip()
            hex_ = (row.get("Hexcode") or "").strip().upper()
            if not (base and hex_.startswith("#")):
                continue
            out[base] = {
                "hex": hex_,
                "light": (row.get("LightHex") or "").strip().upper() or hex_,
                "emotion": (row.get("Emotion") or "").strip(),
                "concepts": [c.strip() for c in (row.get("Concepts") or "").split(",") if c.strip()],
                "psychology_positive": [
                    c.strip() for c in (row.get("PsychologyPositive") or "").split(",") if c.strip()
                ],
                "psychology_negative": [
                    c.strip() for c in (row.get("PsychologyNegative") or "").split(",") if c.strip()
                ],
            }
    return out or _fallback_semantic()


def _fallback_semantic() -> Dict[str, Dict[str, Any]]:
    """Return a minimal semantic palette when the CSV is unavailable."""
    return {
        base: {
            "hex": hexv,
            "light": hexv,
            "emotion": next((e for e, h in _FALLBACK_EMOTIONS.items() if h == hexv), ""),
            "concepts": [],
            "psychology_positive": [],
            "psychology_negative": [],
        }
        for base, hexv in _FALLBACK_PALETTE.items()
    }


def emotion_to_hex(emotion: str) -> Optional[str]:
    """Return the curated hex for one of the palette's Emotion labels.

    Parameters
    ----------
    emotion : str
        Case-insensitive Emotion label from the palette CSV
        (``"Anger"``, ``"Joy"``, ``"Sadness"``, …).

    Returns
    -------
    str or None
        Hex string, or ``None`` when the label is not in the palette.
    """
    target = emotion.strip().lower()
    for base, meta in load_semantic_palette().items():
        if meta["emotion"].lower() == target:
            return meta["hex"]
    fallback = {k.lower(): v for k, v in _FALLBACK_EMOTIONS.items()}
    return fallback.get(target)


def concept_search(term: str) -> List[str]:
    """Return every palette hex whose ``Concepts`` column mentions ``term``.

    Parameters
    ----------
    term : str
        Case-insensitive concept term (``"Trust"``, ``"Bold"``,
        ``"Optimism"``, …).

    Returns
    -------
    list of str
        Hex strings, order-preserving.
    """
    target = term.strip().lower()
    matches: List[str] = []
    for meta in load_semantic_palette().values():
        joined = " ".join(meta.get("concepts", [])).lower()
        joined_pos = " ".join(meta.get("psychology_positive", [])).lower()
        if target in joined or target in joined_pos:
            matches.append(meta["hex"])
    return matches


def psychology_for(base: str) -> Dict[str, List[str]]:
    """Return the positive / negative psychology terms for a base color.

    Parameters
    ----------
    base : str
        Case-insensitive base color name (``"Red"``, ``"Green"``, …).

    Returns
    -------
    dict
        ``{"positive": [...], "negative": [...]}``. Empty lists if the
        palette CSV is unavailable.
    """
    target = base.strip().lower()
    for name, meta in load_semantic_palette().items():
        if name.lower() == target:
            return {
                "positive": meta.get("psychology_positive", []),
                "negative": meta.get("psychology_negative", []),
            }
    return {"positive": [], "negative": []}


# ------------------------------------------------------------------
# Categorical sequences for chart encodings
# ------------------------------------------------------------------
def qualitative_sequence(n: int = 8) -> List[str]:
    """Return the first ``n`` curated saturated hues.

    Parameters
    ----------
    n : int, optional
        How many colors to return (default 8). Cycles the base list
        when ``n`` exceeds the palette size.

    Returns
    -------
    list of str
        ``n`` hex strings, brand-order.
    """
    base = list(load_palette().values())
    # Skip the neutrals for a qualitative encoding.
    saturated = [h for h in base if h.upper() not in {"#000000", "#FFFFFF", "#8E8E93", "#A2845E"}]
    if n <= len(saturated):
        return saturated[:n]
    out: List[str] = []
    while len(out) < n:
        out.extend(saturated)
    return out[:n]


# ------------------------------------------------------------------
# Colour-blind-safe diverging pair for signed / +/- data
# ------------------------------------------------------------------
#: The habitual **red ↔ green** diverging is hostile to red-green colour
#: blindness (~8 % of men): under protanopia / deuteranopia the two ends both
#: drift to a muddy tan and collapse into one hue, so the sign of the data can no
#: longer be read from colour. The **blue ↔ red** axis stays discriminable — blue
#: survives, red darkens toward brown — so it is the default whenever the +/-
#: distinction must be legible *from colour*, not only from a sign or a label.
#: Blue also carries *Trust / Logic* and red *Danger / Warning* in the sprezzature-colors
#: concepts, which fits "positive vs negative". Verify any diverging choice on the
#: rendered pixels with ``simulate_cvd.py``. Source:
#: <https://harchaoui.org/warith/colors/>.
DIVERGING_CVD_SAFE = ("#007AFF", "#F2F4F6", "#FF3B30")  # (positive, neutral mid, negative)


def diverging_pair(cvd_safe: bool = True) -> tuple:
    """Return a ``(positive, negative)`` hex pair for signed / growth data.

    Parameters
    ----------
    cvd_safe : bool, optional
        When ``True`` (default) return the **blue ↔ red** pair, which survives
        red-green colour blindness. When ``False`` return the conventional
        **green ↔ red** pair (finance-idiomatic but not colour-blind-safe) —
        only pick it when the sign is *also* encoded another way (a +/- glyph,
        position above/below zero) and you have confirmed it in ``simulate_cvd``.

    Returns
    -------
    tuple of str
        ``(positive_hex, negative_hex)``.
    """
    if cvd_safe:
        return DIVERGING_CVD_SAFE[0], DIVERGING_CVD_SAFE[2]
    palette = load_palette()
    return palette.get("Green", "#28CD41"), palette.get("Red", "#FF3B30")


# ------------------------------------------------------------------
# Vega-Lite house config
# ------------------------------------------------------------------
def vega_config(dark: bool = False) -> Dict[str, object]:
    """Emit the front-* house-style Vega-Lite ``config`` block.

    Parameters
    ----------
    dark : bool, optional
        Toggle the dark-mode variant (background, text, gridlines).

    Returns
    -------
    dict
        A JSON-serialisable ``config`` block ready to merge into a
        Vega-Lite v5 spec.
    """
    fg = "#F5F5F7" if dark else "#1D1D1F"
    bg = "#1D1D1F" if dark else "#FFFFFF"
    return {
        "background": bg,
        "font": "Roboto, Roboto Serif, Roboto Mono, system-ui, sans-serif",
        "view": {"stroke": None, "cornerRadius": 10},
        "axis": {
            "domain": True,
            "domainColor": fg,
            "labelColor": fg,
            "titleColor": fg,
            "grid": False,
            "ticks": False,
            "labelFont": "Roboto Mono",
            "titleFont": "Roboto",
        },
        "axisTop": {"domain": False, "domainColor": None, "labels": False, "ticks": False, "title": None},
        "axisRight": {"domain": False, "domainColor": None, "labels": False, "ticks": False, "title": None},
        "legend": {
            "titleFont": "Roboto",
            "labelFont": "Roboto",
            "labelColor": fg,
            "titleColor": fg,
        },
        "title": {"font": "Roboto", "fontSize": 14, "color": fg, "subtitleFont": "Roboto", "subtitleColor": fg},
        "range": {"category": qualitative_sequence(8)},
        "bar": {"cornerRadiusEnd": 4},
        "line": {"strokeWidth": 2},
        "point": {"filled": True, "size": 40},
    }


# ------------------------------------------------------------------
# Matplotlib rcParams
# ------------------------------------------------------------------
def matplotlib_rc(dark: bool = False) -> Dict[str, object]:
    """Return matplotlib ``rcParams`` overrides in the front-* house style.

    Parameters
    ----------
    dark : bool, optional
        Toggle the dark-mode variant (background, text, grid).

    Returns
    -------
    dict
        Overrides ready to merge into ``matplotlib.rcParams``.
    """
    fg = "#F5F5F7" if dark else "#1D1D1F"
    bg = "#1D1D1F" if dark else "#FFFFFF"
    return {
        "font.family": ["Roboto", "system-ui", "sans-serif"],
        "font.sans-serif": ["Roboto", "Roboto Serif", "system-ui", "sans-serif"],
        "font.monospace": ["Roboto Mono", "monospace"],
        "figure.facecolor": bg,
        "axes.facecolor": bg,
        "axes.edgecolor": fg,
        "axes.labelcolor": fg,
        "axes.titlecolor": fg,
        "xtick.color": fg,
        "ytick.color": fg,
        "text.color": fg,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "axes.prop_cycle": _cycler(qualitative_sequence(8)),
    }


def _cycler(hexes: List[str]) -> Any:  # matplotlib cycler, typed at runtime only
    """Build a matplotlib cycler from a hex list.

    Deferred import so ``_style.py`` remains matplotlib-free at import
    time (the auditor uses this module too).
    """
    from cycler import cycler  # type: ignore
    return cycler(color=hexes)


# ------------------------------------------------------------------
# Polarity vocabulary
# ------------------------------------------------------------------
POLARITY_HINTS: Dict[str, str] = {
    # metric substring (lowercase) -> "higher-better" | "lower-better"
    "latency":       "lower-better",
    "response":      "lower-better",
    "response_time": "lower-better",
    "error":         "lower-better",
    "errors":        "lower-better",
    "bug":           "lower-better",
    "bugs":          "lower-better",
    "cost":          "lower-better",
    "churn":         "lower-better",
    "attrition":     "lower-better",
    "conversion":    "higher-better",
    "revenue":       "higher-better",
    "sales":         "higher-better",
    "retention":     "higher-better",
    "engagement":    "higher-better",
    "accuracy":      "higher-better",
    "f1":            "higher-better",
    "recall":        "higher-better",
    "precision":     "higher-better",
    "auc":           "higher-better",
    "roc_auc":       "higher-better",
    "r2":            "higher-better",
    "throughput":    "higher-better",
    "uptime":        "higher-better",
    "availability":  "higher-better",
    "mae":           "lower-better",
    "mse":           "lower-better",
    "rmse":          "lower-better",
    "loss":          "lower-better",
}


def infer_polarity(metric_name: str) -> Optional[str]:
    """Guess polarity from a metric name; return ``None`` when ambiguous.

    Parameters
    ----------
    metric_name : str
        The axis-title or column name to score.

    Returns
    -------
    str or None
        ``"higher-better"``, ``"lower-better"``, or ``None`` if no
        substring in :data:`POLARITY_HINTS` matched.
    """
    if not metric_name:
        return None
    lower = metric_name.lower()
    for substr, polarity in POLARITY_HINTS.items():
        # word-ish boundary: substring surrounded by non-alphanumerics or ends
        if substr in lower:
            return polarity
    return None


# ------------------------------------------------------------------
# Polarity → color mapping
# ------------------------------------------------------------------
#: Base color to reach for by polarity intent. Rationale:
#: **higher-better** and **lower-better** are both "goal-directed" —
#: readers want to see the metric move — so both map to Green
#: (psychology-positive: *Health*, *Hope*, *Growth*, *Prosperity*).
#: **target=** shifts to Blue (psychology-positive: *Trust*, *Logic*,
#: *Security*) — the metric is neutral; the frame is compliance.
#: The **breach** overlay uses Red (psychology-negative: *Warning*,
#: *Danger*) to flag SLA violations without co-opting the base
#: encoding. Source: <https://harchaoui.org/warith/colors/>.
POLARITY_COLOR: Dict[str, str] = {
    "higher-better": "Green",
    "lower-better":  "Green",
    "target":        "Blue",
    "breach":        "Red",
    "neutral":       "Gray",
}


def polarity_color(
    polarity: Optional[str],
    *,
    role: str = "primary",
    dark: bool = False,
) -> Optional[str]:
    """Return the house-style hex for a polarity intent.

    Never a substitute for the polarity text tag on the axis title —
    ~8 % of male viewers cannot read the color signal alone (see
    ``cvd-simulation.md``). Used as a *reinforcement* layer.

    Parameters
    ----------
    polarity : str or None
        One of ``"higher-better"``, ``"lower-better"``, or
        ``"target=<N>"``. Anything else returns ``None`` (caller keeps
        the qualitative palette).
    role : {'primary', 'breach'}, optional
        ``"primary"`` returns the goal color (Green or Blue);
        ``"breach"`` returns the SLA-violation overlay (Red).
    dark : bool, optional
        Currently unused — every curated base hex meets contrast on
        both background modes. Reserved for future light/dark variant
        selection.

    Returns
    -------
    str or None
        A hex string from the curated palette, or ``None`` when the
        polarity is not one the mapping recognises.
    """
    if not polarity:
        return None
    if role == "breach":
        base: str | None = POLARITY_COLOR["breach"]
    elif polarity.startswith("target="):
        base = POLARITY_COLOR["target"]
    else:
        base = POLARITY_COLOR.get(polarity)
    if base is None:
        return None
    palette = load_palette()
    return palette.get(base)


def polarity_tag(polarity: Optional[str], lang: str = "en") -> str:
    """Return the parenthesised polarity tag for an axis title.

    Parameters
    ----------
    polarity : {'higher-better', 'lower-better', None} or ``"target=<N>"``
        The polarity to render.
    lang : str, optional
        BCP-47 base tag; controls the translation.

    Returns
    -------
    str
        E.g. ``" (higher is better)"`` — includes the leading space so
        it can be safely appended to any axis title. Empty when
        polarity is ``None``.
    """
    if not polarity:
        return ""
    translations = {
        "higher-better": {"en": " (higher is better)", "fr": " (plus haut = mieux)", "de": " (höher ist besser)", "es": " (más alto es mejor)"},
        "lower-better":  {"en": " (lower is better)",  "fr": " (plus bas = mieux)",  "de": " (niedriger ist besser)", "es": " (más bajo es mejor)"},
    }
    if polarity.startswith("target="):
        n = polarity.split("=", 1)[1]
        return {
            "en": f" (target = {n})",
            "fr": f" (cible = {n})",
            "de": f" (Ziel = {n})",
            "es": f" (objetivo = {n})",
        }.get(lang, f" (target = {n})")
    return translations.get(polarity, {}).get(lang, translations.get(polarity, {}).get("en", ""))

#!/usr/bin/env python3
"""
audit_contrast
==============

Audit a palette's foreground / background contrast against the WCAG
ratio thresholds (4.5:1 for body text, 3:1 for large text and UI, 7:1
for AAA). For failing pairs, propose the nearest accessible alternative
by walking the OKLCH lightness axis.

The script accepts two input shapes:

* A JSON palette: ``{"role": "#RRGGBB", ...}`` or ``{"role": {"DEFAULT": "#…", "dark": "#…"}, ...}``.
* The skill's built-in default palette (when no ``--palette`` is given).

It is **deterministic** — no model, no network — and uses standard formulas:

* WCAG relative luminance (the 2.4-gamma formula).
* OKLab / OKLCH conversion via Björn Ottosson's published matrices
  (https://bottosson.github.io/posts/oklab/).

Usage
-----
::

    # Audit the skill's built-in palette at WCAG AA (4.5:1)
    python audit_contrast.py

    # AAA threshold
    python audit_contrast.py --target 7

    # External palette + suggested fixes
    python audit_contrast.py --palette my-palette.json --fix

    # JSON output for CI
    python audit_contrast.py --format json

Notes
-----
* Python 3.10+, stdlib only.
* The "fix" search walks the OKLCH L axis at 0.01 resolution; in practice
  the search converges in tens of microseconds per pair.
* Color math (sRGB transfer, WCAG luminance, OKLab / OKLCH) lives in
  ``_colors.py`` next to this script. Both ``audit_contrast`` and
  ``simulate_cvd`` import from it.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
from _colors import (  # noqa: E402
    contrast_ratio,
    contrast_ratio_hex,
    linear_to_oklab,
    oklab_to_linear,
    oklab_to_oklch,
    oklch_to_oklab,
    parse_hex_linear,
    relative_luminance as relative_luminance,  # re-exported for tests/consumers
    to_hex,
)


# Re-export under the legacy name so external callers / tests that import
# ``parse_hex`` from ``audit_contrast`` keep working. The function returns
# a *linear* sRGB triple (gamma-decoded), as it has always done here.
parse_hex = parse_hex_linear


# ── Skill's built-in palette ────────────────────────────────────────────────

#: Default palette used when ``--palette`` is not supplied. Mirrors the
#: skill's semantic Tailwind tokens.
DEFAULT_PALETTE: dict[str, dict[str, str]] = {
    "brand-blue":      {"DEFAULT": "#007AFF", "dark": "#0A84FF", "light": "#CCE4FF"},
    "brand-red":       {"DEFAULT": "#FF3B30", "dark": "#FF453A", "light": "#FFD8D6"},
    "brand-green":     {"DEFAULT": "#28CD41", "dark": "#30D158", "light": "#D4F5D9"},
    "brand-orange":    {"DEFAULT": "#FF9500", "dark": "#FF9F0A", "light": "#FFEACC"},
    "brand-yellow":    {"DEFAULT": "#FFCC00", "dark": "#FFD60A", "light": "#FFF5CC"},
    "brand-purple":    {"DEFAULT": "#AF52DE", "dark": "#BF5AF2", "light": "#EFDCF8"},
    "brand-pink":      {"DEFAULT": "#FF2D55", "dark": "#FF375F", "light": "#FFD5DD"},
    "brand-turquoise": {"DEFAULT": "#79DBDC", "dark": "#64D2FF", "light": "#00FFEF"},
    "label-primary":   {"DEFAULT": "#000000", "dark": "#FFFFFF"},
    "label-secondary": {"DEFAULT": "#3C3C434D", "dark": "#EBEBF54D"},
    "surface-primary": {"DEFAULT": "#FFFFFF", "dark": "#000000"},
    "surface-secondary": {"DEFAULT": "#F2F2F7", "dark": "#1C1C1E"},
}


# ── Suggestion search ──────────────────────────────────────────────────────

def adjust_for_contrast(
    fg_linear: tuple[float, float, float],
    bg_linear: tuple[float, float, float],
    target: float,
) -> tuple[str, float] | None:
    """
    Find the nearest accessible alternative to ``fg_linear`` on the
    OKLCH lightness axis (keeping hue and chroma fixed).

    The search walks L from 0 to 1 in 0.01 steps, picks the candidate that
    passes the target *and* is closest to the original L.

    Parameters
    ----------
    fg_linear : tuple of float
        Source foreground in linear sRGB.
    bg_linear : tuple of float
        Background in linear sRGB.
    target : float
        Minimum acceptable contrast ratio.

    Returns
    -------
    tuple of (str, float) or None
        ``(suggested_hex, achieved_ratio)`` or ``None`` if no candidate
        meets the target (very rare — usually means the background itself
        is very close to mid-gray).
    """
    L, C, H = oklab_to_oklch(linear_to_oklab(fg_linear))
    best: tuple[float, tuple[float, float, float]] | None = None
    for i in range(0, 101):
        l_test: float = i / 100.0
        candidate = oklab_to_linear(oklch_to_oklab((l_test, C, H)))
        ratio = contrast_ratio(candidate, bg_linear)
        if ratio >= target:
            distance: float = abs(l_test - L)
            if best is None or distance < best[0]:
                best = (distance, candidate)
    if best is None:
        return None
    return to_hex(best[1]), contrast_ratio(best[1], bg_linear)


# ── Audit logic ─────────────────────────────────────────────────────────────

def normalize_palette(raw: dict) -> dict[str, str]:
    """
    Flatten a nested palette to ``{role: hex}``.

    Accepts both flat (``{"key": "#fff"}``) and nested
    (``{"key": {"DEFAULT": "#fff", "dark": "#000"}}``) shapes.
    """
    flat: dict[str, str] = {}
    for role, value in raw.items():
        if isinstance(value, str):
            flat[role] = value
        elif isinstance(value, dict):
            for variant, hex_val in value.items():
                key: str = role if variant.upper() == "DEFAULT" else f"{role}-{variant}"
                flat[key] = hex_val
    return flat


def is_foreground(role: str) -> bool:
    """Return True when ``role`` is conventionally drawn on top of a surface."""
    return role.startswith(("label-", "brand-")) and not role.endswith(("-light", "-dark"))


def is_background(role: str) -> bool:
    """Return True when ``role`` is conventionally a surface colour."""
    return role.startswith("surface-")


def audit(
    palette: dict[str, str],
    target: float,
    propose_fix: bool,
) -> dict:
    """
    Audit every (foreground, background) pair against the target ratio.

    Returns ``{"target": <target>, "pairs": [...]}`` where each pair entry has
    ``fg``, ``bg``, ``ratio``, ``passes``, and optionally ``suggested``.
    """
    out: list[dict] = []
    for fg_role, fg_hex in palette.items():
        if not is_foreground(fg_role):
            continue
        for bg_role, bg_hex in palette.items():
            if not is_background(bg_role):
                continue
            # Alpha-aware: a translucent foreground (#RRGGBBAA) is composited
            # over its background before the ratio, so the audit judges the
            # color as rendered, not the raw un-painted foreground. The opaque
            # linear pair is still needed by the fix search below.
            fg = parse_hex(fg_hex)
            bg = parse_hex(bg_hex)
            ratio = contrast_ratio_hex(fg_hex, bg_hex)
            entry: dict = {
                "fg": {"role": fg_role, "hex": fg_hex.upper()},
                "bg": {"role": bg_role, "hex": bg_hex.upper()},
                "ratio": round(ratio, 2),
                "passes": ratio >= target,
            }
            if not entry["passes"] and propose_fix:
                fix = adjust_for_contrast(fg, bg, target)
                if fix is not None:
                    entry["suggested"] = {"hex": fix[0], "ratio": round(fix[1], 2)}
            out.append(entry)
    return {"target": target, "pairs": out}


# ── CLI entry point ────────────────────────────────────────────────────────

def main() -> int:
    """Run the audit. Exit code 0 when every checked pair passes, 1 otherwise."""
    p = make_parser(
        prog="sprezzature-colors-contrast",
        description="Audit a palette's foreground/background contrast against WCAG. "
                    "Walks every (label, surface) pair, suggests the nearest OKLCH "
                    "neighbour for failing pairs when --fix is set.",
        epilog="Examples:\n"
               "  sprezzature-colors-contrast --palette palette.json\n"
               "  sprezzature-colors-contrast --palette palette.json --target 7 --fix\n"
               "  sprezzature-colors-contrast --format json --palette palette.json\n",
    )
    p.add_argument(
        "--palette", type=Path,
        help="JSON palette. When omitted, the skill's built-in default is used.",
    )
    p.add_argument(
        "--target", type=float, default=4.5,
        help="Minimum acceptable WCAG contrast ratio. 4.5 (AA body), 7 (AAA), or 3 (UI/large).",
    )
    p.add_argument(
        "--fix", action="store_true",
        help="Propose a suggested fix for each failing pair (nearest OKLCH neighbour).",
    )
    p.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format. Default: text.",
    )
    args = p.parse_args()

    if args.palette is not None:
        raw = json.loads(args.palette.read_text(encoding="utf-8"))
    else:
        raw = DEFAULT_PALETTE
    flat = normalize_palette(raw)

    result = audit(flat, args.target, args.fix)

    if args.format == "json":
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print(f"Target ratio: {result['target']}")
        print()
        passing = 0
        failing = 0
        for pair in result["pairs"]:
            mark = "✓" if pair["passes"] else "✗"
            print(
                f"  {mark} {pair['fg']['role']:>22}  on  {pair['bg']['role']:>22}"
                f"   ratio {pair['ratio']:.2f}"
            )
            if not pair["passes"]:
                failing += 1
                if "suggested" in pair:
                    print(
                        f"      → suggest {pair['suggested']['hex']}  "
                        f"(ratio {pair['suggested']['ratio']:.2f})"
                    )
            else:
                passing += 1
        print()
        print(f"{passing} pass, {failing} fail.")

    failing_count: int = sum(1 for p in result["pairs"] if not p["passes"])
    return 0 if failing_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

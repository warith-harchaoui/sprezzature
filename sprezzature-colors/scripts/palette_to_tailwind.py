#!/usr/bin/env python3
"""
palette_to_tailwind
===================

Render the canonical sprezzature-colors palette
(``sprezzature-colors/references/palette.csv``) as a Tailwind v3+ JavaScript
configuration snippet so a sprezzature-ui consumer can drop the brand tokens
into ``tailwind.config.js`` without copy-pasting from the reference.

This is the **make-side** counterpart to ``audit_contrast.py``: the
audit script checks pairs against WCAG; this script *emits* the
machine-readable form of the same palette so it can be wired into a
real Tailwind build.

Two emit modes
--------------

``--emit theme``  (default)
    Emit only the ``colors: { brand: { ... } }`` block, ready to paste
    inside the existing ``theme.extend`` of an existing
    ``tailwind.config.js``. Best when the consumer already has a
    config and just wants the brand tokens refreshed.

``--emit config``
    Emit a complete ``module.exports = { … }`` configuration mirroring
    ``sprezzature-ui/references/stack-tailwind.md``: `darkMode` strategy,
    `fontFamily`, the brand colors block (plus the canonical
    `label` / `surface` / `separator` tokens that the sprezzature-ui
    starter relies on), `borderRadius`, `backdropBlur` and
    `transitionTimingFunction`. Best when bootstrapping a new project.

Token naming
------------

Each row in ``palette.csv`` becomes one Tailwind token under
``brand.<slug>``:

* ``DEFAULT`` is set from the ``Hexcode`` column.
* ``light``   is set from the ``LightHex`` column (curated in the CSV).
* ``dark``    is OPTIONAL. The CSV does not carry a dark-mode variant
  (Apple's exact dark system colours are hand-tuned), so this script
  derives one *perceptually* via ``_colors.lighten`` on the OKLCH L
  axis when ``--with-dark`` is passed. The derived value lands in the
  same neighbourhood as Apple's saturated dark, but is unambiguously
  described as derived in the emitted comment so future maintainers
  know to override per-token if needed.

The slug is the lowercased ``Base`` column (``Red`` → ``red``,
``Turquoise`` → ``turquoise``). White / Black / Gray rows are emitted
as ``brand.white``, ``brand.black``, ``brand.gray`` so a project that
wants the curated greys can pull them from the same source of truth.

Usage
-----
::

    # Just the colors block, stdout
    python scripts/palette_to_tailwind.py

    # Full config file, with derived dark variants
    python scripts/palette_to_tailwind.py --emit config --with-dark \\
        --out tailwind.config.js

    # Pipe into a downstream tool
    python scripts/palette_to_tailwind.py --emit theme | pbcopy

Why dict-not-class
------------------

Per the project style: every row coming back from ``load_palette()`` is
already a ``dict[str, str]``. We pass dicts around and render strings;
no domain class is necessary for a one-purpose emitter.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

# Sibling-module imports. Both shipped inside ``sprezzature-colors/scripts/`` so
# they are on ``sys.path`` whenever this script is invoked.
from _argparse import make_parser
from _colors import lighten, load_palette


# ── Constants ──────────────────────────────────────────────────────────────


#: OKLCH lightness delta used to derive a dark-mode variant from the base
#: hex when ``--with-dark`` is requested. The value is small on purpose:
#: Apple's saturated dark colours bump the L axis by roughly +0.02 .. +0.04
#: relative to their saturated base, and the goal here is to land in that
#: neighbourhood without claiming pixel-equivalence to Apple's hand-tune.
DARK_LIGHTNESS_DELTA: float = 0.03


#: Canonical "brand-suitable" Base names — mirrors the saturated set
#: in :func:`_colors.apple_palette` so the emitter agrees with the
#: other consumer of the same CSV. Neutrals (Black / White / Gray /
#: Brown) are intentionally excluded: those tokens live under
#: ``surface`` / ``label`` in the sprezzature-ui Tailwind config, not under
#: ``brand``.
SATURATED_BASES: frozenset[str] = frozenset(
    {"Red", "Orange", "Yellow", "Green", "Turquoise", "Blue", "Purple", "Pink"}
)


#: Canonical non-brand tokens emitted by ``--emit config``. Mirrors the
#: block in ``sprezzature-ui/references/stack-tailwind.md`` so the emitted
#: ``tailwind.config.js`` is drop-in compatible with the existing
#: sprezzature-ui assets. Kept as a string literal (not a dict-to-JS
#: serializer) because the literal preserves comments and key order
#: that a generic serializer would lose.
NON_BRAND_TOKENS_BLOCK: str = """\
        label: {
          primary:          { DEFAULT: '#000000' },
          'primary-dark':     '#FFFFFF',
          secondary:        { DEFAULT: 'rgba(60,60,67,0.6)' },
          'secondary-dark':   'rgba(235,235,245,0.6)',
          tertiary:         { DEFAULT: 'rgba(60,60,67,0.3)' },
          'tertiary-dark':    'rgba(235,235,245,0.3)',
        },
        surface: {
          primary:          { DEFAULT: '#FFFFFF' },
          'primary-dark':     '#000000',
          secondary:        { DEFAULT: '#F2F2F7' },
          'secondary-dark':   '#1C1C1E',
          tertiary:         { DEFAULT: '#FFFFFF' },
          'tertiary-dark':    '#2C2C2E',
        },
        separator: 'rgba(60,60,67,0.36)',\
"""


# ── Helpers ────────────────────────────────────────────────────────────────


def _slug(name: str) -> str:
    """
    Lowercase a Base name into a Tailwind-safe token slug.

    Parameters
    ----------
    name : str
        Source name from the CSV's ``Base`` column (e.g. ``"Turquoise"``).

    Returns
    -------
    str
        Lowercased slug suitable for Tailwind config keys (no quoting
        required for the keys used by the canonical palette).
    """
    return name.strip().lower()


def _derive_dark(base_hex: str) -> str:
    """
    Compute a dark-mode variant from a base hex via OKLCH L bumping.

    Apple's saturated dark colours sit roughly at L + 0.03 relative to
    the saturated base. We do not try to match them pixel-for-pixel;
    we land in the same neighbourhood and trust the consumer to
    override per-token where brand requires.

    Parameters
    ----------
    base_hex : str
        Source hex (``"#007AFF"``).

    Returns
    -------
    str
        Uppercased hex (``"#1A88FF"`` or similar). ``lighten`` already
        normalises the case.
    """
    return lighten(base_hex, DARK_LIGHTNESS_DELTA).upper()


def _entry(row: dict[str, str], indent: int, with_dark: bool) -> str:
    """
    Render one ``brand.<slug>`` Tailwind entry.

    Parameters
    ----------
    row : dict of str → str
        One row from :func:`_colors.load_palette`. Required keys:
        ``Base``, ``Hexcode``. Optional: ``LightHex``.
    indent : int
        Number of leading spaces (per the surrounding indent depth).
    with_dark : bool
        If ``True``, derive and include a ``dark`` field via
        :func:`_derive_dark`. Otherwise the field is omitted.

    Returns
    -------
    str
        One-line JS object literal, suitable to drop into a
        ``brand: { ... }`` block. No trailing newline.
    """
    pad: str = " " * indent
    base: str = row["Hexcode"].upper()
    light: str = row.get("LightHex", "").strip().upper()
    parts: list[str] = [f"DEFAULT: '{base}'"]
    if with_dark:
        parts.append(f"dark: '{_derive_dark(base)}'")
    if light:
        parts.append(f"light: '{light}'")
    slug: str = _slug(row["Base"])
    # Pad the slug so the colons line up vertically — easier to read,
    # matches the sprezzature-ui reference exactly (jq-style left-align).
    return f"{pad}{slug:<10}: {{ {', '.join(parts)} }},"


# ── Renderers ──────────────────────────────────────────────────────────────


def _filter(
    rows: Iterable[dict[str, str]], *, include_neutrals: bool
) -> list[dict[str, str]]:
    """
    Keep only the rows the Tailwind ``brand`` namespace should carry.

    By default returns the eight saturated Apple hues (matches
    :data:`SATURATED_BASES` and the existing sprezzature-ui Tailwind
    reference). When ``include_neutrals`` is ``True`` the Brown /
    Black / Gray / White rows are appended too — they then collide
    with the canonical ``label`` / ``surface`` tokens unless the
    consumer renames them, so opt-in only.

    Parameters
    ----------
    rows : iterable of dict
        Palette rows.
    include_neutrals : bool
        Include the four neutral rows.

    Returns
    -------
    list of dict
        Filtered rows, original CSV order preserved.
    """
    out: list[dict[str, str]] = []
    for row in rows:
        base: str = row.get("Base", "").strip()
        if not base:
            continue
        if base in SATURATED_BASES:
            out.append(row)
        elif include_neutrals:
            out.append(row)
    return out


def render_brand_block(
    rows: Iterable[dict[str, str]],
    *,
    indent: int = 8,
    with_dark: bool = False,
    include_neutrals: bool = False,
) -> str:
    """
    Render the ``brand: { … }`` Tailwind colours block.

    Parameters
    ----------
    rows : iterable of dict
        Rows from :func:`_colors.load_palette`. Rows with an empty
        ``Base`` are skipped (defensive: future CSV revisions may add
        unnamed swatches).
    indent : int, default 8
        Leading-space count for the ``brand`` key. Default matches the
        depth used inside ``theme.extend.colors`` in
        ``sprezzature-ui/references/stack-tailwind.md``.
    with_dark : bool, default False
        Include a derived ``dark`` field per row.

    Returns
    -------
    str
        Multi-line JS snippet ending with a newline.
    """
    pad: str = " " * indent
    lines: list[str] = [
        "// Generated by sprezzature-colors/scripts/palette_to_tailwind.py",
        "// Source of truth: sprezzature-colors/references/palette.csv",
    ]
    if with_dark:
        lines.append(
            "// 'dark' variants are OKLCH-L-derived (delta = "
            f"{DARK_LIGHTNESS_DELTA}); override per-token if brand requires."
        )
    lines.extend([f"{pad}brand: {{"])
    for row in _filter(rows, include_neutrals=include_neutrals):
        lines.append(_entry(row, indent=indent + 2, with_dark=with_dark))
    lines.append(f"{pad}}},")
    return "\n".join(lines) + "\n"


def render_full_config(
    rows: Iterable[dict[str, str]],
    *,
    with_dark: bool = False,
    include_neutrals: bool = False,
) -> str:
    """
    Render a complete ``module.exports = { … }`` Tailwind config.

    Mirrors the canonical block in
    ``sprezzature-ui/references/stack-tailwind.md`` so the emitted file is
    drop-in compatible with the sprezzature-ui starter assets (Roboto
    fontFamily, dark-mode strategy, the curated label / surface /
    separator tokens, the rounded / blur / motion extensions, and the
    forms + typography plugins).

    Parameters
    ----------
    rows : iterable of dict
        Palette rows (see :func:`render_brand_block`).
    with_dark : bool, default False
        Include derived ``dark`` brand variants.

    Returns
    -------
    str
        Complete contents of a ``tailwind.config.js`` file, ending
        with a trailing newline.
    """
    brand: str = render_brand_block(
        rows,
        indent=8,
        with_dark=with_dark,
        include_neutrals=include_neutrals,
    ).rstrip()
    return (
        "/** @type {import('tailwindcss').Config} */\n"
        "// Generated by sprezzature-colors/scripts/palette_to_tailwind.py\n"
        "// Source of truth: sprezzature-colors/references/palette.csv\n"
        "module.exports = {\n"
        "  content: ['./src/**/*.{html,js}', './index.html'],\n"
        "  darkMode: ['class', '[data-color-scheme=\"dark\"]'],\n"
        "  theme: {\n"
        "    extend: {\n"
        "      fontFamily: {\n"
        "        sans:  ['Roboto', 'sans-serif'],\n"
        "        serif: ['Roboto Serif', 'serif'],\n"
        "        mono:  ['Roboto Mono', 'ui-monospace', 'monospace'],\n"
        "      },\n"
        "      colors: {\n"
        f"{brand}\n"
        f"{NON_BRAND_TOKENS_BLOCK}\n"
        "      },\n"
        "      borderRadius: {\n"
        "        '2xl': '1rem',\n"
        "        '3xl': '1.5rem',\n"
        "      },\n"
        "      backdropBlur: {\n"
        "        'ultra':   '20px',\n"
        "        'thin':    '24px',\n"
        "        'regular': '32px',\n"
        "        'thick':   '40px',\n"
        "      },\n"
        "      transitionTimingFunction: {\n"
        "        'native':        'cubic-bezier(0.32, 0.72, 0, 1)',\n"
        "        'native-spring': 'cubic-bezier(0.5, 1.6, 0.4, 0.7)',\n"
        "        'standard':      'cubic-bezier(0.4, 0, 0.2, 1)',\n"
        "      },\n"
        "    },\n"
        "  },\n"
        "  plugins: [\n"
        "    require('@tailwindcss/forms'),\n"
        "    require('@tailwindcss/typography'),\n"
        "  ],\n"
        "};\n"
    )


# ── CLI ────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Returns
    -------
    int
        ``0`` on success, ``1`` on I/O failure.
    """
    parser: argparse.ArgumentParser = make_parser(
        prog="sprezzature-colors-palette-to-tailwind",
        description=(
            "Render sprezzature-colors/references/palette.csv as a Tailwind "
            "theme.extend.colors block (default) or as a complete "
            "tailwind.config.js. Stdlib only; deterministic; reads the "
            "canonical CSV and writes the machine-readable Tailwind "
            "form of the same source of truth."
        ),
    )
    parser.add_argument(
        "--emit",
        choices=("theme", "config"),
        default="theme",
        help=(
            "What to emit. 'theme' (default) prints only the "
            "brand: { ... } block — paste into an existing config. "
            "'config' prints a complete module.exports = { ... } "
            "ready to save as tailwind.config.js."
        ),
    )
    parser.add_argument(
        "--with-dark",
        action="store_true",
        help=(
            "Include a derived dark-mode variant per brand token "
            "(OKLCH L-axis bump of "
            f"{DARK_LIGHTNESS_DELTA}). The CSV does not carry a dark "
            "column; the value is a derivation, not Apple's exact "
            "saturated-dark — a comment in the output makes this clear."
        ),
    )
    parser.add_argument(
        "--include-neutrals",
        action="store_true",
        help=(
            "Also emit Brown / Black / Gray / White brand tokens. "
            "Off by default — these neutrals normally live under the "
            "surface / label tokens in the sprezzature-ui Tailwind config "
            "and would collide if also published under brand."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Write to this file instead of stdout. The parent "
            "directory must already exist."
        ),
    )
    args: argparse.Namespace = parser.parse_args(argv)

    rows: list[dict[str, str]] = load_palette()
    rendered: str = (
        render_full_config(
            rows,
            with_dark=args.with_dark,
            include_neutrals=args.include_neutrals,
        )
        if args.emit == "config"
        else render_brand_block(
            rows,
            with_dark=args.with_dark,
            include_neutrals=args.include_neutrals,
        )
    )

    if args.out is None:
        sys.stdout.write(rendered)
        return 0

    try:
        args.out.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        # Surface the I/O failure on stderr so CI logs are useful. We
        # do not swallow the exception class — the message is enough
        # at the user level.
        print(f"palette_to_tailwind: write failed: {exc}", file=sys.stderr)
        return 1

    print(f"palette_to_tailwind: wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

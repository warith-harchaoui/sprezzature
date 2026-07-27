#!/usr/bin/env python3
"""
favicons
========

Generate the complete favicon / app-icon set from a single logo image.

Modern browsers and operating systems consume only a handful of icon
formats; this script produces exactly that handful and skips the legacy
zoo (70/72/114/144/152 px PNGs that nobody requests anymore).

Output (relative to ``--out``, default ``./public``)
----------------------------------------------------
=============================  ==========================================
File                           Purpose
=============================  ==========================================
``favicon.svg``                Preferred favicon for modern browsers
                               (copied verbatim when the input is SVG).
``favicon.ico``                Multi-resolution 16/32/48 px ICO.
``favicon-16.png``             Browser tab fallback for very small sizes.
``favicon-32.png``             Browser tab fallback for normal sizes.
``favicon-48.png``             Browser tab fallback for high-DPI sizes.
``apple-touch-icon.png``       180 × 180 PNG, opaque, NO rounded corners
                               (the OS adds them).
``icon-192.png``               PWA install icon (Android etc.).
``icon-512.png``               PWA install icon at high resolution.
``icon-maskable-512.png``      PWA maskable variant — content fits inside
                               the central 80 % so the OS can mask it.
``site.webmanifest``           Minimal PWA manifest.
``head.html``                  Drop-in ``<link>`` and ``<meta>`` tags.
=============================  ==========================================

Usage
-----
::

    # Most common: a single PNG logo with a light background
    python favicons.py logo.png --out public --name "Site name" --bg "#FFFFFF"

    # SVG source with a PNG fallback for the raster variants
    python favicons.py logo.svg --raster logo-1024.png --out public

    # Brand-tinted theme color
    python favicons.py logo.png --bg "#FFFFFF" \\
                                --theme-light "#FFFFFF" \\
                                --theme-dark "#000000"

Notes
-----
* Requires Python 3.10+ and ``Pillow >= 10``.
* W3C / current best practice:

  * SVG is the preferred favicon format; rasters are fallback.
  * apple-touch-icon should be opaque; transparent edges get clipped
    by the OS.
  * Maskable icons reserve the central 80 % (40 % radius from center).
  * ``<meta name="theme-color">`` matches the favicon's background for
    both color schemes.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path as _PathHelper

sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
from pathlib import Path

from PIL import Image


# ── Module-level configuration ────────────────────────────────────────────────

#: PNG variant sizes a modern site actually serves.
PNG_SIZES: tuple[int, ...] = (16, 32, 48, 192, 512)

#: Side length of the apple-touch-icon, in pixels.
APPLE_TOUCH_SIZE: int = 180

#: Side length of the maskable icon, in pixels.
MASKABLE_SIZE: int = 512

#: Fraction of the maskable canvas that the artwork occupies. The outer 10 %
#: on each side is bleed so the OS can apply its own clipping shape.
MASKABLE_SAFE: float = 0.8

#: Resolutions embedded in the multi-resolution ``favicon.ico``.
ICO_SIZES: tuple[int, ...] = (16, 32, 48)


# ── Argument-parsing helpers ────────────────────────────────────────────────

def parse_hex(s: str) -> tuple[int, int, int]:
    """
    Parse a 3- or 6-digit hex color into an ``(R, G, B)`` triple.

    Parameters
    ----------
    s : str
        Hex color, with or without a leading ``#``. Both ``#fff`` and
        ``#ffffff`` are accepted.

    Returns
    -------
    tuple of int
        Three integers in ``[0, 255]``.

    Raises
    ------
    argparse.ArgumentTypeError
        When the string is not a valid hex color.
    """
    s = s.lstrip("#").strip()
    if len(s) == 3:
        # Expand shorthand: ``f00`` → ``ff0000``.
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise argparse.ArgumentTypeError(f"Bad hex color: {s!r}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


# ── Image loading + resizing ────────────────────────────────────────────────

def open_source(path: Path) -> tuple[Image.Image, bool]:
    """
    Open the source image as RGBA.

    Parameters
    ----------
    path : Path
        Source image path. Either a raster (PNG/JPG/WebP) or an ``.svg`` file.

    Returns
    -------
    tuple of (Image.Image, bool)
        The image and a flag indicating whether the source was SVG.
        For SVG, the returned image is a 1×1 placeholder — the caller must
        provide a separate ``--raster`` source for the PNG variants because
        Pillow does not natively rasterize SVG.
    """
    if path.suffix.lower() == ".svg":
        # Pillow does not rasterize SVG. We honor the SVG path by copying it
        # for ``favicon.svg`` and ask the user for a PNG via ``--raster``.
        sys.stderr.write(
            "Input is SVG. The .svg will be copied as favicon.svg, but raster\n"
            "variants need a PNG source. Run again with --raster <png-path>.\n"
        )
        return Image.new("RGBA", (1, 1)), True
    im = Image.open(path).convert("RGBA")
    return im, False


def resize_square(im: Image.Image, size: int) -> Image.Image:
    """
    Downscale ``im`` to fit a ``size``×``size`` transparent canvas, centered.

    The longer edge is scaled to ``size`` and the artwork is pasted onto a
    fresh RGBA canvas. Aspect ratio is preserved; the unused area stays
    transparent.

    Parameters
    ----------
    im : Image.Image
        Source image (any mode; RGBA recommended).
    size : int
        Side length of the output canvas, in pixels.

    Returns
    -------
    Image.Image
        New RGBA image of side ``size``.
    """
    src = im.copy()
    src.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(src, ((size - src.width) // 2, (size - src.height) // 2), src)
    return canvas


def flatten_on(bg: tuple[int, int, int], im: Image.Image) -> Image.Image:
    """
    Composite an RGBA image over a solid background, returning RGB.

    Used for icons that must be opaque (apple-touch-icon, maskable).

    Parameters
    ----------
    bg : tuple of int
        RGB background color.
    im : Image.Image
        Foreground RGBA image.

    Returns
    -------
    Image.Image
        RGB image with the foreground composited over ``bg``.
    """
    base = Image.new("RGB", im.size, bg)
    # Pillow ignores ``mask`` when the source has no alpha channel, so this
    # works for RGB inputs too.
    base.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
    return base


def make_maskable(im: Image.Image, bg: tuple[int, int, int]) -> Image.Image:
    """
    Build a maskable PWA icon at :data:`MASKABLE_SIZE` square.

    The artwork is placed in the central :data:`MASKABLE_SAFE` fraction of
    the canvas; the outer ring is solid ``bg``. This satisfies the W3C
    maskable-icon contract: the OS may clip the canvas to any shape and
    still leave the artwork fully visible.

    Parameters
    ----------
    im : Image.Image
        Source artwork.
    bg : tuple of int
        RGB background color for the bleed area.

    Returns
    -------
    Image.Image
        RGB image of side :data:`MASKABLE_SIZE`.
    """
    canvas = Image.new("RGB", (MASKABLE_SIZE, MASKABLE_SIZE), bg)
    inner: int = int(MASKABLE_SIZE * MASKABLE_SAFE)
    fit = im.copy()
    fit.thumbnail((inner, inner), Image.Resampling.LANCZOS)
    pad: tuple[int, int] = (
        (MASKABLE_SIZE - fit.width) // 2,
        (MASKABLE_SIZE - fit.height) // 2,
    )
    canvas.paste(fit, pad, fit if fit.mode == "RGBA" else None)
    return canvas


# ── Manifest + HTML head ────────────────────────────────────────────────────

def write_manifest(
    out_dir: Path,
    name: str,
    short: str,
    bg_hex: str,
    theme_hex: str,
) -> None:
    """
    Write a minimal ``site.webmanifest`` for PWA install support.

    Parameters
    ----------
    out_dir : Path
        Directory to write into.
    name : str
        Full app name (manifest ``name`` field).
    short : str
        Short app name (manifest ``short_name`` field).
    bg_hex : str
        Background color in hex (manifest ``background_color`` field).
    theme_hex : str
        Theme color in hex (manifest ``theme_color`` field).
    """
    manifest: dict = {
        "name": name,
        "short_name": short or name,
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {
                "src": "/icon-maskable-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
        "background_color": bg_hex,
        "theme_color": theme_hex,
        "display": "standalone",
        "start_url": "/",
    }
    (out_dir / "site.webmanifest").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def write_head_snippet(
    out_dir: Path,
    theme_hex_light: str,
    theme_hex_dark: str,
    has_svg: bool,
) -> None:
    """
    Write a drop-in ``head.html`` snippet with the link + meta tags.

    Parameters
    ----------
    out_dir : Path
        Directory to write into.
    theme_hex_light : str
        ``theme-color`` value for ``prefers-color-scheme: light``.
    theme_hex_dark : str
        ``theme-color`` value for ``prefers-color-scheme: dark``.
    has_svg : bool
        Whether a ``favicon.svg`` is being shipped (controls the first link).
    """
    snippet: list[str] = []
    if has_svg:
        snippet.append('<link rel="icon" href="/favicon.svg" type="image/svg+xml">')
    snippet.extend([
        '<link rel="icon" href="/favicon.ico" sizes="any">',
        '<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">',
        '<link rel="icon" href="/favicon-16.png" sizes="16x16" type="image/png">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">',
        '<link rel="manifest" href="/site.webmanifest">',
        f'<meta name="theme-color" content="{theme_hex_light}" media="(prefers-color-scheme: light)">',
        f'<meta name="theme-color" content="{theme_hex_dark}" media="(prefers-color-scheme: dark)">',
    ])
    (out_dir / "head.html").write_text("\n".join(snippet) + "\n", encoding="utf-8")


# ── CLI entry point ─────────────────────────────────────────────────────────

def main() -> int:
    """
    Generate the favicon set end-to-end.

    Returns
    -------
    int
        Process exit code; always ``0`` on success.
    """
    p = make_parser(
        prog="sprezzature-publish-favicons",
        description="Generate the full favicon / PWA / Apple-touch icon set "
                    "(including site.webmanifest and a paste-ready head.html) "
                    "from a single source logo.",
        epilog="Examples:\n"
               "  sprezzature-publish-favicons logo.svg --out public --name 'Project'\n"
               "  sprezzature-publish-favicons logo.png --bg '#ffffff' --theme-dark '#000000'\n",
    )
    p.add_argument(
        "source", type=Path,
        help="Path to the logo (PNG, JPG, WebP, or SVG).",
    )
    p.add_argument(
        "--raster", type=Path,
        help="If --source is SVG, use this PNG for raster outputs.",
    )
    p.add_argument(
        "--out", type=Path, default=Path("public"),
        help="Output directory. Default: ./public",
    )
    p.add_argument(
        "--name", default="App",
        help="Long name in the webmanifest.",
    )
    p.add_argument(
        "--short-name", default=None,
        help="Short name in the webmanifest.",
    )
    p.add_argument(
        "--bg", default="#FFFFFF",
        help="Solid background for opaque icons (apple-touch, maskable).",
    )
    p.add_argument(
        "--theme-light", default=None,
        help="theme-color for prefers-color-scheme: light. Default: --bg",
    )
    p.add_argument(
        "--theme-dark", default="#000000",
        help="theme-color for prefers-color-scheme: dark.",
    )
    args = p.parse_args()

    # Parse colors once.
    bg: tuple[int, int, int] = parse_hex(args.bg)
    theme_light: str = args.theme_light or args.bg
    theme_dark: str = args.theme_dark
    args.out.mkdir(parents=True, exist_ok=True)

    source_im, is_svg = open_source(args.source)
    if is_svg and not args.raster:
        # The SVG path is preserved but the raster pipeline needs a PNG.
        shutil.copyfile(args.source, args.out / "favicon.svg")
        sys.stderr.write(
            "Wrote favicon.svg only. Re-run with --raster <png-path> "
            "to also produce the PNGs.\n"
        )
        return 0

    # Copy the SVG verbatim when present, then pick the raster source.
    if is_svg:
        shutil.copyfile(args.source, args.out / "favicon.svg")
    raster_im: Image.Image = (
        Image.open(args.raster or args.source).convert("RGBA")
        if is_svg
        else source_im
    )

    # Standard PNG sizes (transparent). Sizes ≥ 192 land under
    # ``icon-NNN.png``; smaller sizes land under ``favicon-NN.png``.
    for size in PNG_SIZES:
        im = resize_square(raster_im, size)
        out_path = (
            args.out / f"icon-{size}.png"
            if size >= 192
            else args.out / f"favicon-{size}.png"
        )
        im.save(out_path, format="PNG", optimize=True)

    # Multi-resolution ICO. Pillow handles the embedding when ``sizes=`` is set.
    ico_im = resize_square(raster_im, max(ICO_SIZES))
    ico_im.save(args.out / "favicon.ico", sizes=[(s, s) for s in ICO_SIZES])

    # apple-touch-icon: opaque, no rounded corners (the OS adds them).
    touch = flatten_on(bg, resize_square(raster_im, APPLE_TOUCH_SIZE))
    touch.save(args.out / "apple-touch-icon.png", format="PNG", optimize=True)

    # Maskable PWA icon — content in the central 80 %.
    masked = make_maskable(raster_im, bg)
    masked.save(args.out / "icon-maskable-512.png", format="PNG", optimize=True)

    # Manifest + ready-to-paste HTML head snippet.
    write_manifest(args.out, args.name, args.short_name or args.name, args.bg, theme_light)
    write_head_snippet(args.out, theme_light, theme_dark, has_svg=is_svg)

    print(f"→ Wrote favicon set to {args.out}/")
    print(f"  Paste {args.out}/head.html into your <head>.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

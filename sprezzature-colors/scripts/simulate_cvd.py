#!/usr/bin/env python3
"""
simulate_cvd
============

Render an image as a color-blind viewer sees it.

Three CVD (color vision deficiency) types are supported:

* ``protanopia``     — no functional L cones; reds desaturate toward gray.
* ``deuteranopia``   — no functional M cones; the largest CVD population.
* ``tritanopia``     — no functional S cones (rare).

The implementation uses the Machado et al. (2009) precomputed simulation
matrices, applied in linear sRGB. The matrices and the per-pixel transform
live in ``_colors.py`` next to this script; both ``audit_contrast`` and
``simulate_cvd`` import from it.

Output
------
By default, three sibling files are written next to the source image::

    <stem>-protanopia.png
    <stem>-deuteranopia.png
    <stem>-tritanopia.png

With ``--grid``, a single 2×2 mosaic is written instead, with the original
image in the top-left and each CVD variant labeled.

Usage
-----
::

    # Three sibling files
    python simulate_cvd.py public/hero.png

    # Side-by-side mosaic for design review
    python simulate_cvd.py public/hero.png --grid --out public/hero-cvd.png

    # Pick a subset of CVD types
    python simulate_cvd.py public/hero.png --types prot,deut

Notes
-----
* Python 3.10+, ``Pillow``.
* Numeric work uses Python floats (no NumPy dependency) — slower per pixel
  than NumPy but still milliseconds for typical screenshots, and one less
  dependency to install.
* Matrices: Machado, Oliveira, Fernandes (2009),
  "A Physiologically-based Model for Simulation of Color Vision Deficiency",
  IEEE Transactions on Visualization and Computer Graphics.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from typing import cast
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
from _colors import (  # noqa: E402
    CVD_LABELS,
    CVD_MATRICES,
    CVD_SHORTHAND,
    linear_to_srgb as linear_to_srgb,  # re-exported for tests/consumers
    simulate_pixel,
    srgb_to_linear as srgb_to_linear,  # re-exported for tests/consumers
)

from PIL import Image, ImageDraw, ImageFont


# Legacy alias retained for tests / external callers that imported from this
# module before the math moved to ``_colors``.
SHORTHAND = CVD_SHORTHAND


def simulate_image(im: Image.Image, kind: str) -> Image.Image:
    """
    Apply a CVD simulation to a whole image.

    Parameters
    ----------
    im : Image.Image
        Source image. Will be converted to RGB internally.
    kind : str
        One of the keys in :data:`CVD_MATRICES`.
    """
    matrix = CVD_MATRICES[kind]
    rgb = im.convert("RGB")

    # Pixel-by-pixel iteration. For large images this is ~1 s; well within
    # acceptable for a static review tool. NumPy would be ~50× faster but
    # adds a dependency.
    out = Image.new("RGB", rgb.size)
    src_pixels = rgb.load()
    dst_pixels = out.load()
    assert src_pixels is not None and dst_pixels is not None  # load() is None only on a closed image
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            dst_pixels[x, y] = simulate_pixel(cast("tuple[int, int, int]", src_pixels[x, y]), matrix)
    return out


def grayscale_image(im: Image.Image) -> Image.Image:
    """
    Return a relative-luminance grayscale of ``im``, computed in linear light.

    Answers the other half of the accessibility question the CVD types leave
    open — *does the chart still read with no colour at all?* If a series or a
    diverging +/- sign only exists as a hue, it disappears here. Luminance is the
    Rec. 709 weighting applied to the **linearised** channels and re-encoded to
    sRGB (the same transfer functions the CVD path uses), so it matches how the
    eye weights brightness rather than a naive average of gamma-encoded values.

    Parameters
    ----------
    im : Image.Image
        Source image. Converted to RGB internally.
    """
    rgb = im.convert("RGB")
    out = Image.new("RGB", rgb.size)
    src_pixels = rgb.load()
    dst_pixels = out.load()
    assert src_pixels is not None and dst_pixels is not None
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            r, g, b = cast("tuple[int, int, int]", src_pixels[x, y])
            lum = 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)
            v = linear_to_srgb(lum)
            dst_pixels[x, y] = (v, v, v)
    return out


# ── Grid mosaic ─────────────────────────────────────────────────────────────

def make_grid(
    original: Image.Image,
    simulated: dict[str, Image.Image],
    extra: "list[tuple[str, Image.Image]] | None" = None,
) -> Image.Image:
    """
    Compose a single image showing the original next to each CVD variant.

    The mosaic layout adapts to the number of supplied variants:

    * 1 variant  → 1×2 grid (original, variant).
    * 2 variants → 2×2 grid (original + 2 variants + an empty slot).
    * 3 variants → 2×2 grid (original + 3 variants).

    ``extra`` appends further labelled cells after the CVD variants (used by
    ``--grayscale`` to add a grayscale panel).
    """
    cells = [("Original", original)] + [(CVD_LABELS[k], simulated[k]) for k in simulated]
    if extra:
        cells += extra
    cols: int = 2
    rows: int = (len(cells) + cols - 1) // cols
    cell_w, cell_h = original.size

    grid = Image.new("RGB", (cell_w * cols, cell_h * rows), (255, 255, 255))
    draw = ImageDraw.Draw(grid)

    try:
        font = ImageFont.load_default()
    except OSError:
        font = None  # pragma: no cover

    for idx, (label, im) in enumerate(cells):
        col: int = idx % cols
        row: int = idx // cols
        grid.paste(im.resize((cell_w, cell_h)), (col * cell_w, row * cell_h))
        text_pad: int = 8
        if font is not None:
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.rectangle(
                (col * cell_w, row * cell_h, col * cell_w + tw + 2 * text_pad, row * cell_h + th + 2 * text_pad),
                fill=(255, 255, 255),
            )
            draw.text(
                (col * cell_w + text_pad, row * cell_h + text_pad),
                label, fill=(0, 0, 0), font=font,
            )

    return grid


# ── CLI entry point ───────────────────────────────────────────────────────

def parse_types(arg: str) -> list[str]:
    """
    Parse a comma-separated list of CVD types or shorthands.

    Returns full CVD kind names in source order. Empty input returns all
    three kinds.
    """
    out: list[str] = []
    for tok in arg.split(","):
        tok = tok.strip().lower()
        if not tok:
            continue
        full = SHORTHAND.get(tok, tok)
        if full not in CVD_MATRICES:
            raise argparse.ArgumentTypeError(f"Unknown CVD type: {tok}")
        out.append(full)
    return out or list(CVD_MATRICES.keys())


def main() -> int:
    """Generate the requested CVD-simulated outputs. Returns 0 on success."""
    p = make_parser(
        prog="sprezzature-colors-cvd",
        description="Render an image as a color-blind viewer sees it. "
                    "Applies Machado et al. matrices for protanopia, deuteranopia "
                    "and tritanopia. Catches red/green collisions before ship.",
        epilog="Examples:\n"
               "  sprezzature-colors-cvd screenshot.png\n"
               "  sprezzature-colors-cvd screenshot.png --grid --out previews/\n",
    )
    p.add_argument(
        "source", type=Path,
        help="Path to the source image (PNG, JPG, WebP, …).",
    )
    p.add_argument(
        "--out", type=Path,
        help="Output path. For per-type mode, a directory; for --grid, a file. "
             "Defaults to siblings of the source.",
    )
    p.add_argument(
        "--types", type=parse_types, default=parse_types("protanopia,deuteranopia,tritanopia"),
        help="Comma-separated CVD types (default: all three).",
    )
    p.add_argument(
        "--grid", action="store_true",
        help="Write a single 2×2 mosaic instead of three sibling files.",
    )
    p.add_argument(
        "--grayscale", action="store_true",
        help="Also emit a relative-luminance grayscale variant — the "
             "'does it read with no colour?' check.",
    )
    args = p.parse_args()

    try:
        original = Image.open(args.source).convert("RGB")
    except OSError as e:
        sys.stderr.write(f"Cannot open {args.source}: {e}\n")
        return 1

    simulated: dict[str, Image.Image] = {}
    for kind in args.types:
        simulated[kind] = simulate_image(original, kind)

    gray = grayscale_image(original) if args.grayscale else None

    if args.grid:
        extra = [("Grayscale", gray)] if gray is not None else None
        grid = make_grid(original, simulated, extra)
        out_path: Path = args.out or args.source.with_name(args.source.stem + "-cvd-grid.png")
        grid.save(out_path, format="PNG", optimize=True)
        print(f"→ Wrote grid to {out_path}")
    else:
        out_dir: Path = args.out or args.source.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        for kind, im in simulated.items():
            out_path = out_dir / f"{args.source.stem}-{kind}{args.source.suffix or '.png'}"
            im.save(out_path, format="PNG", optimize=True)
            print(f"→ Wrote {out_path}")
        if gray is not None:
            gpath = out_dir / f"{args.source.stem}-grayscale{args.source.suffix or '.png'}"
            gray.save(gpath, format="PNG", optimize=True)
            print(f"→ Wrote {gpath}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

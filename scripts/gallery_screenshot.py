#!/usr/bin/env python3
"""
gallery_screenshot
==================

Capture light + dark headless screenshots of a public URL for the
`GALLERY.md` showcase. Saves the PNGs under ``assets/gallery/<slug>/``
ready to be referenced from a Markdown gallery entry.

Two screenshots are produced per run, one for each ``prefers-color-scheme``
value (``light`` and ``dark``). The viewport size, output directory,
and quality settings are configurable.

Usage
-----
::

    # Single URL → light + dark variant in assets/gallery/4ml/
    python3 scripts/gallery_screenshot.py \\
        --url https://harchaoui.org/warith/4ml \\
        --slug 4ml

    # Custom viewport, full-page capture, into a custom dir
    python3 scripts/gallery_screenshot.py \\
        --url https://example.com \\
        --slug example \\
        --width 1440 --height 900 \\
        --full-page \\
        --out assets/gallery/

Requires
--------
* Python 3.10+
* ``pip install playwright && playwright install chromium``

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from playwright.sync_api import sync_playwright


# ── Module-level defaults ───────────────────────────────────────────────────

#: Output root for gallery screenshots, relative to the repo root.
DEFAULT_OUT: Path = Path(__file__).resolve().parents[1] / "assets" / "gallery"

#: Desktop-ish viewport — wide enough that responsive sites render the
#: full chrome (sidebar, sticky header) instead of the mobile collapse.
DEFAULT_WIDTH: int = 1440
DEFAULT_HEIGHT: int = 900

#: How long to wait for the page to settle (`networkidle`) before
#: capturing. Static sites are usually well under a second; this is the
#: ceiling for sites with lazy-loaded fonts or analytics beacons.
NETWORK_IDLE_TIMEOUT_MS: int = 15_000

#: ``prefers-color-scheme`` values understood by Chromium.
COLOR_SCHEMES: tuple[str, ...] = ("light", "dark")

#: pngquant quality window (``--quality min-max``). Retina-2× shots come
#: out around 8 MB; this knocks them down ~60-70% with no visible loss.
PNGQUANT_QUALITY: str = "70-90"


# ── Helpers ────────────────────────────────────────────────────────────────

def capture_one(
    url: str,
    out_path: Path,
    *,
    color_scheme: str,
    width: int,
    height: int,
    full_page: bool,
) -> None:
    """
    Capture a single screenshot of ``url`` at ``color_scheme``.

    Parameters
    ----------
    url : str
        Absolute URL to capture (must include scheme).
    out_path : Path
        Destination PNG file. Parent directories are created.
    color_scheme : str
        One of ``COLOR_SCHEMES`` — passed to Chromium so the page sees
        the matching ``prefers-color-scheme`` value.
    width, height : int
        Viewport dimensions in CSS pixels.
    full_page : bool
        When ``True``, capture the full scrollable height; otherwise
        only the viewport.

    Raises
    ------
    RuntimeError
        If the page does not reach ``networkidle`` within
        :data:`NETWORK_IDLE_TIMEOUT_MS`.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        # Headless Chromium — chosen over Firefox / WebKit because the
        # ``color_scheme`` context option is universally supported and
        # CSS rendering parity with most modern browsers is highest.
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                color_scheme=cast(Any, color_scheme),  # drives prefers-color-scheme
                device_scale_factor=2,      # retina-quality PNG
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
            # ``omit_background`` would let surface colour bleed
            # through; keep it ``False`` so the captured PNG is a
            # faithful reproduction of what a real visitor sees.
            page.screenshot(path=str(out_path), full_page=full_page, omit_background=False)
        finally:
            browser.close()


def compress_png(path: Path) -> None:
    """
    Run pngquant in-place on ``path`` when available.

    Headless retina captures land around 8 MB per PNG; pngquant takes
    them down to ~2-3 MB at quality 70-90 with no perceptible loss.
    Silently skipped when pngquant is not on ``PATH`` so the script
    stays functional in CI / fresh dev environments.

    Parameters
    ----------
    path : Path
        PNG file to compress in-place.
    """
    if shutil.which("pngquant") is None:
        return
    tmp = path.with_suffix(".png.tmp")
    # ``--strip`` removes ancillary chunks (gAMA, cHRM, sRGB) we don't
    # need; ``--skip-if-larger`` keeps the original when pngquant would
    # somehow inflate the file.
    result = subprocess.run(
        [
            "pngquant",
            "--strip",
            "--skip-if-larger",
            "--quality", PNGQUANT_QUALITY,
            "--output", str(tmp),
            str(path),
        ],
        check=False,
    )
    # Exit 98/99 means the result didn't meet the quality window —
    # the original file is fine, just don't replace it.
    if result.returncode == 0 and tmp.exists():
        tmp.replace(path)
    elif tmp.exists():
        tmp.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    """
    Parse the command-line arguments.

    Returns
    -------
    argparse.Namespace
        With attributes ``url``, ``slug``, ``out``, ``width``,
        ``height`` and ``full_page``.
    """
    parser = argparse.ArgumentParser(
        prog="gallery_screenshot",
        description="Capture light + dark headless screenshots for GALLERY.md.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--url", required=True, help="Absolute URL to capture.")
    parser.add_argument(
        "--slug",
        required=True,
        help="Folder name under --out (e.g. '4ml').",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output root (default: {DEFAULT_OUT}).",
    )
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture the full scrollable height instead of the viewport.",
    )
    return parser.parse_args()


def main() -> int:
    """
    CLI entrypoint.

    Returns
    -------
    int
        Process exit code. ``0`` on success.
    """
    args = parse_args()
    target_dir: Path = args.out / args.slug
    for scheme in COLOR_SCHEMES:
        out_file: Path = target_dir / f"{scheme}.png"
        print(f"→ capturing {args.url} ({scheme}) → {out_file}")
        capture_one(
            args.url,
            out_file,
            color_scheme=scheme,
            width=args.width,
            height=args.height,
            full_page=args.full_page,
        )
        compress_png(out_file)
    print(f"✓ wrote {len(COLOR_SCHEMES)} PNGs into {target_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

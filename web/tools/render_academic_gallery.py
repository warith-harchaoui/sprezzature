#!/usr/bin/env python3
"""
render_academic_gallery — generate the 🏫 academic-theme variant of every
figures.html gallery asset.

web/img/figures/*.{svg,png} are the corporate-theme (default Apple palette)
assets, hand-tuned over many Ralph Eyeball Loop passes — never touched here.
This script renders the academic-theme (Okabe-Ito) sibling of each one into
web/img/figures/academic/, by re-invoking each figure's own
sprezzature-figures/scripts/make_<kind>.py with --theme academic. The two
gallery-only formats (PNG thumbnail, SVG for the lightbox) are both written.

Every corporate gallery PNG is rasterised to a fixed 900px width regardless
of the figure's native viewBox (confirmed by inspecting the existing
corporate assets: e.g. a 1440x900 viewBox -> 900x563 PNG, a 745x505 viewBox
-> 900x611 PNG). SPREZZATURE_RENDER_SCALE is a *multiplier*, not a target
width, so this script renders the academic SVG first, reads its viewBox
width, computes ``scale = 900 / viewbox_width`` per figure, and only then
renders the PNG — reproducing the same fixed-900px-wide convention.

Only figure kinds that already have both a gallery SVG (web/img/figures/)
and a matching make_<kind>.py script are rendered — the ~20 map / gapminder
/ election assets that also live under img/figures/ but belong to other
pages (maps.html, hans-rosling.html) are skipped, since they are not part
of the figures.html grid this toggle covers.

Usage
-----
    python tools/render_academic_gallery.py [--dry-run] [--only KIND ...]

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
GALLERY = WEB / "img" / "figures"
OUT_DIR = GALLERY / "academic"
SCRIPTS = Path.home() / "sprezzature-figures" / "scripts"
VENV_PY = Path.home() / "sprezzature-figures" / ".venv" / "bin" / "python3"
PY = str(VENV_PY) if VENV_PY.is_file() else sys.executable

THUMB_TARGET_WIDTH = 900.0
_VIEWBOX_RE = re.compile(r'viewBox="0 0 ([\d.]+) ([\d.]+)"')


def _viewbox_width(svg_path: Path) -> float | None:
    m = _VIEWBOX_RE.search(svg_path.read_text(encoding="utf-8"))
    return float(m.group(1)) if m else None


def discover_kinds() -> list[str]:
    """Gallery figure kinds that have a matching make_<kind>.py script."""
    kinds = []
    for svg in sorted(GALLERY.glob("*.svg")):
        kind = svg.stem
        script = SCRIPTS / f"make_{kind}.py"
        if script.is_file():
            kinds.append(kind)
    return kinds


def render_one(kind: str, dry_run: bool) -> tuple[bool, str]:
    script = SCRIPTS / f"make_{kind}.py"
    out_svg = OUT_DIR / f"{kind}.svg"
    out_png = OUT_DIR / f"{kind}.png"
    env = dict(os.environ)

    if dry_run:
        return True, f"would render {kind}"

    cmd_svg = [PY, str(script), "--theme", "academic", "--out", str(out_svg)]
    r1 = subprocess.run(cmd_svg, cwd=SCRIPTS, capture_output=True, text=True)
    if r1.returncode != 0:
        return False, f"{kind}: SVG failed: {r1.stderr.strip()[-400:]}"

    width = _viewbox_width(out_svg)
    if not width:
        return False, f"{kind}: could not read viewBox width from {out_svg.name}"
    env["SPREZZATURE_RENDER_SCALE"] = str(THUMB_TARGET_WIDTH / width)
    cmd_png = [PY, str(script), "--theme", "academic", "--out", str(out_png)]
    r2 = subprocess.run(cmd_png, cwd=SCRIPTS, capture_output=True, text=True, env=env)
    if r2.returncode != 0:
        return False, f"{kind}: PNG failed: {r2.stderr.strip()[-400:]}"

    return True, kind


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", nargs="*", default=None, help="Render only these kinds.")
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    kinds = discover_kinds()
    if args.only:
        kinds = [k for k in kinds if k in set(args.only)]

    print(f"{len(kinds)} figure kinds to render (theme=academic)")
    failures: list[str] = []
    for i, kind in enumerate(kinds, 1):
        ok, msg = render_one(kind, args.dry_run)
        status = "ok" if ok else "FAIL"
        print(f"[{i}/{len(kinds)}] {status} {msg}")
        if not ok:
            failures.append(msg)

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print(f" - {f}")
        return 1
    print(f"\nWrote {len(kinds)} academic SVG+PNG pairs to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

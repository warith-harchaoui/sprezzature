#!/usr/bin/env python3
"""
render_academic_gallery — generate the 🏫 academic-theme variant of every
figures.html gallery asset.

web/img/figures/*.{svg,png} are the corporate-theme (default Apple palette)
assets, hand-tuned over many Ralph Eyeball Loop passes — never touched here.
This script renders the academic-theme (Okabe-Ito) sibling of each one into
web/img/figures/academic/, by loading each figure's own
sprezzature-figures/scripts/make_<kind>.py as a module and calling its
make_<kind>(out=..., theme="academic") function directly (not the script's
own CLI: several generators' bespoke argparse blocks don't expose --theme
or --out consistently — the underlying library function always does, so
that's the stable surface to drive). The two gallery-only formats (PNG
thumbnail, SVG for the lightbox) are both written.

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

import os_helper as osh

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
    """Gallery figure kinds referenced by figures.html with a matching make_<kind>.py.

    img/figures/ also holds orphaned assets (e.g. gapminder.svg, left over
    after those cards were dropped from the gallery) and case-study-only
    assets (maps, gapminder-animated, ...) that belong to other pages. Both
    are excluded by requiring an actual `img/figures/<kind>.` reference in
    figures.html, not just a file's presence on disk.
    """
    figures_html = (WEB / "figures.html").read_text(encoding="utf-8")
    kinds = []
    for svg in sorted(GALLERY.glob("*.svg")):
        kind = svg.stem
        script = SCRIPTS / f"make_{kind}.py"
        if script.is_file() and f"img/figures/{kind}." in figures_html:
            kinds.append(kind)
    return kinds


_CALL_TEMPLATE = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location("_gen", {script!r})
mod = importlib.util.module_from_spec(spec)
sys.path.insert(0, {scripts_dir!r})
spec.loader.exec_module(mod)
fn = getattr(mod, {fn_name!r})
fn(out={out!r}, theme="academic")
"""


def _call_make(kind: str, fn_name: str, out: Path, env: dict) -> subprocess.CompletedProcess:
    script = SCRIPTS / f"make_{kind}.py"
    code = _CALL_TEMPLATE.format(
        script=str(script), scripts_dir=str(SCRIPTS), fn_name=fn_name, out=str(out),
    )
    return subprocess.run([PY, "-c", code], cwd=SCRIPTS, capture_output=True, text=True, env=env)


def render_one(kind: str, dry_run: bool) -> tuple[bool, str]:
    out_svg = OUT_DIR / f"{kind}.svg"
    out_png = OUT_DIR / f"{kind}.png"
    fn_name = "make_" + kind.replace("-", "_")
    env = dict(os.environ)

    if dry_run:
        return True, f"would render {kind}"

    r1 = _call_make(kind, fn_name, out_svg, env)
    if r1.returncode != 0:
        return False, f"{kind}: SVG failed: {r1.stderr.strip()[-400:]}"

    width = _viewbox_width(out_svg)
    if not width:
        return False, f"{kind}: could not read viewBox width from {out_svg.name}"
    env["SPREZZATURE_RENDER_SCALE"] = str(THUMB_TARGET_WIDTH / width)
    r2 = _call_make(kind, fn_name, out_png, env)
    if r2.returncode != 0:
        return False, f"{kind}: PNG failed: {r2.stderr.strip()[-400:]}"

    return True, kind


def main() -> int:
    osh.init_logging()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", nargs="*", default=None, help="Render only these kinds.")
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    kinds = discover_kinds()
    if args.only:
        kinds = [k for k in kinds if k in set(args.only)]

    osh.info(f"{len(kinds)} figure kinds to render (theme=academic)")
    failures: list[str] = []
    for i, kind in enumerate(kinds, 1):
        ok, msg = render_one(kind, args.dry_run)
        if ok:
            osh.info(f"[{i}/{len(kinds)}] ok {msg}")
        else:
            osh.warning(f"[{i}/{len(kinds)}] FAIL {msg}")
            failures.append(msg)

    if failures:
        osh.error(f"{len(failures)} failure(s):")
        for f in failures:
            osh.error(f" - {f}")
        return 1
    osh.info(f"Wrote {len(kinds)} academic SVG+PNG pairs to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
render_gallery — render a figures.html gallery asset in either theme.

The gallery ships each figure twice: the corporate theme (default Apple
palette) in web/img/figures/, and its 🏫 academic-theme (Okabe-Ito) sibling
in web/img/figures/academic/, which the page's theme toggle swaps in.

The corporate assets are hand-tuned over many Ralph Eyeball Loop passes, so
this script will not overwrite one that already exists unless ``--force``
says to. A figure that has no corporate asset yet — one just added to the
catalogue — is rendered normally, which is how a new figure enters the
gallery. It works by loading each figure's own
sprezzature-figures/scripts/make_<kind>.py as a module and calling its
make_<kind>(out=..., theme=...) function directly (not the script's
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
    python tools/render_gallery.py                          # academic, every gallery kind
    python tools/render_gallery.py --only upset             # academic, one kind
    python tools/render_gallery.py --theme corporate \
        --kinds manifold_path                               # a figure new to the gallery

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
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
fn(out={out!r}, theme={theme!r})
"""


def _call_make(
    kind: str, fn_name: str, out: Path, env: dict, theme: str
) -> subprocess.CompletedProcess:
    script = SCRIPTS / f"make_{kind}.py"
    code = _CALL_TEMPLATE.format(
        script=str(script), scripts_dir=str(SCRIPTS), fn_name=fn_name,
        out=str(out), theme=theme,
    )
    return subprocess.run([PY, "-c", code], cwd=SCRIPTS, capture_output=True, text=True, env=env)


def out_dir_for(theme: str) -> Path:
    """Where a theme's gallery assets live."""
    return GALLERY if theme == "corporate" else GALLERY / theme


def render_one(kind: str, dry_run: bool, theme: str, force: bool) -> tuple[bool, str]:
    out_dir = out_dir_for(theme)
    out_svg = out_dir / f"{kind}.svg"
    out_png = out_dir / f"{kind}.png"
    fn_name = "make_" + kind.replace("-", "_")
    env = dict(os.environ)

    if theme == "corporate" and out_svg.is_file() and not force:
        return True, f"{kind}: kept (hand-tuned corporate asset; --force to replace)"

    if dry_run:
        return True, f"would render {kind}"

    r1 = _call_make(kind, fn_name, out_svg, env, theme)
    if r1.returncode != 0:
        return False, f"{kind}: SVG failed: {r1.stderr.strip()[-400:]}"

    width = _viewbox_width(out_svg)
    if not width:
        return False, f"{kind}: could not read viewBox width from {out_svg.name}"
    env["SPREZZATURE_RENDER_SCALE"] = str(THUMB_TARGET_WIDTH / width)
    r2 = _call_make(kind, fn_name, out_png, env, theme)
    if r2.returncode != 0:
        return False, f"{kind}: PNG failed: {r2.stderr.strip()[-400:]}"

    return True, kind


def main() -> int:
    osh.init_logging()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", nargs="*", default=None, help="Render only these kinds.")
    p.add_argument(
        "--kinds", nargs="*", default=None,
        help="Render exactly these kinds, even if the gallery does not show them "
             "yet. This is how a figure new to the catalogue gets its first asset.",
    )
    p.add_argument("--theme", default="academic", choices=("academic", "corporate"))
    p.add_argument(
        "--force", action="store_true",
        help="Replace an existing corporate asset. Those are hand-tuned, so the "
             "default is to keep them.",
    )
    args = p.parse_args()

    out_dir_for(args.theme).mkdir(parents=True, exist_ok=True)
    kinds = args.kinds if args.kinds else discover_kinds()
    if args.only:
        kinds = [k for k in kinds if k in set(args.only)]

    osh.info(f"{len(kinds)} figure kinds to render (theme={args.theme})")
    failures: list[str] = []
    written = 0
    for i, kind in enumerate(kinds, 1):
        ok, msg = render_one(kind, args.dry_run, args.theme, args.force)
        written += ok and msg == kind
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
    osh.info(f"Wrote {written} {args.theme} SVG+PNG pair(s) to {out_dir_for(args.theme)}; "
             f"{len(kinds) - written} left alone")
    return 0


if __name__ == "__main__":
    sys.exit(main())

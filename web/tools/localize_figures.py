#!/usr/bin/env python3
"""Localise the figure gallery from a single i18n map.

Reads ``web/i18n/figures.fr.yaml`` (a flat ``"English": "Français"`` map) and
writes a French version of every gallery figure into ``web/img/figures/fr/``:

- Vega figures (a spec exists under the figures repo's ``assets/vega-examples``)
  are re-rendered from the translated spec, so layout re-flows and nothing
  clips.
- Hand-authored ("hero") SVGs are localised by substituting the text of each
  ``<text>/<tspan>/<title>/<desc>`` node through the map.

Every human string it meets that is NOT in the map is reported at the end, so
the map's gaps are always visible (the "audit i18n" list). Idempotent: run it
again after editing the YAML to refresh only what changed.

Usage:  python tools/localize_figures.py [--only name1,name2]
"""
from __future__ import annotations

import glob
import html
import json
import re
import sys
from pathlib import Path

import yaml

WEB = Path(__file__).resolve().parent.parent
FIGREPO = Path.home() / "sprezzature-figures"
GALLERY = WEB / "img" / "figures"
FR = GALLERY / "fr"
YAML = WEB / "i18n" / "figures.fr.yaml"

sys.path.insert(0, str(FIGREPO))
import vl_convert as vlc  # noqa: E402
from sprezzature_figures.fonts import DEFAULT_SVG_FACES, svg_font_defs  # noqa: E402

TR: dict[str, str] = yaml.safe_load(YAML.read_text(encoding="utf-8")) or {}
SPECS = {re.sub(r"\.(vl|vg)$", "", Path(p).stem): p for p in glob.glob(str(FIGREPO / "assets/vega-examples/*.json"))}
SKIP = re.compile(r"^[\d\s.,%:+\-–—−/()·°×→←]*$")  # pure punctuation / numbers
missing: set[str] = set()


def is_human(s: str) -> bool:
    return bool(s.strip()) and not SKIP.match(s)


def embed(svg: str) -> str:
    if "@font-face" not in svg and svg.lstrip().startswith("<svg"):
        i = svg.index(">") + 1
        svg = svg[:i] + svg_font_defs(DEFAULT_SVG_FACES) + svg[i:]
    return svg


def tr_walk(o):
    if isinstance(o, dict):
        return {k: tr_walk(v) for k, v in o.items()}
    if isinstance(o, list):
        return [tr_walk(v) for v in o]
    if isinstance(o, str):
        if is_human(o) and o not in TR:
            missing.add(o)
        return TR.get(o, o)
    return o


def gallery_ext(name: str) -> str | None:
    if (GALLERY / f"{name}.svg").exists():
        return "svg"
    if (GALLERY / f"{name}.png").exists():
        return "png"
    return None


def scale_for(spec: dict) -> float:
    w = spec.get("width", 500)
    return max(2.5, round(2500 / max(w, 300), 2))


def localize_vega(name: str, spec_path: str, ext: str) -> None:
    spec = tr_walk(json.loads(Path(spec_path).read_text()))
    txt = json.dumps(spec, ensure_ascii=False)
    is_vg = spec_path.endswith(".vg.json")
    if ext == "png":
        png = (vlc.vega_to_png if is_vg else vlc.vegalite_to_png)(txt, scale=scale_for(spec))
        (FR / f"{name}.png").write_bytes(png)
    else:
        svg = (vlc.vega_to_svg if is_vg else vlc.vegalite_to_svg)(txt)
        (FR / f"{name}.svg").write_text(embed(svg), encoding="utf-8")


TEXT_RE = re.compile(r"(<(?:text|tspan|title|desc)\b[^>]*>)([^<]+)(</(?:text|tspan|title|desc)>)")


def localize_hero(name: str) -> None:
    t = (GALLERY / f"{name}.svg").read_text(encoding="utf-8")

    def repl(m: re.Match) -> str:
        key = re.sub(r"\s+", " ", html.unescape(m.group(2))).strip()
        if key in TR:
            return m.group(1) + html.escape(TR[key], quote=False) + m.group(3)
        if is_human(key):
            missing.add(key)
        return m.group(0)

    (FR / f"{name}.svg").write_text(TEXT_RE.sub(repl, t), encoding="utf-8")


def main() -> int:
    FR.mkdir(parents=True, exist_ok=True)
    only = None
    if len(sys.argv) > 2 and sys.argv[1] == "--only":
        only = set(sys.argv[2].split(","))
    names = sorted({Path(p).stem for p in glob.glob(str(GALLERY / "*.svg"))}
                   | {Path(p).stem for p in glob.glob(str(GALLERY / "*.png"))})
    names = [n for n in names if not n.endswith(".fr")]
    done = 0
    for name in names:
        if only and name not in only:
            continue
        ext = gallery_ext(name)
        if ext is None:
            continue
        try:
            if name in SPECS:
                localize_vega(name, SPECS[name], ext)
            elif ext == "svg":
                localize_hero(name)
            else:
                continue  # raster hero with no spec: can't localise text
            done += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {name}: {exc}")
    print(f"localised {done} figures -> {FR}")
    if missing:
        print(f"\n{len(missing)} strings still UNTRANSLATED (add to {YAML.name}):")
        for s in sorted(missing):
            print(f"  {s!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

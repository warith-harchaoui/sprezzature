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
# SVG path data (a mark.shape, a precomputed hex tile, ...) is geometry, not
# prose: it starts with a move command and every letter in it is a path command.
# It must never be treated as human text — a stray "translation" that turned its
# decimal points into French commas once silently emptied the hexbin figure.
_PATH_CMDS = set("MmLlHhVvCcSsQqTtAaZz")


def is_path_data(s: str) -> bool:
    s = s.strip()
    return bool(s) and s[0] in "Mm" and all(ch in _PATH_CMDS for ch in s if ch.isalpha())
# Bare single-word keys (the word-cloud review terms) collide with Vega structural
# values like the "filter" transform type or a "from"/"size" field, so they are
# applied only to hero SVGs, never to re-rendered Vega specs.
SPEC_UNSAFE = frozenset(
    "clean compact consistent easy even fast love precise quiet recommend reliable smooth "
    "sturdy value clumps flimsy jams leaks mess noisy plastic pricey retention static wobble "
    "beans bin burr coffee dial espresso grind hopper kitchen morning motor setting filter "
    "size from".split()
)
# Path-data keys must never drive a substitution even if one is still lingering
# in the map, so geometry can't be corrupted from a stale entry.
TR_SPEC: dict[str, str] = {
    k: v for k, v in TR.items() if k not in SPEC_UNSAFE and not is_path_data(k)
}
missing: set[str] = set()


def is_human(s: str) -> bool:
    return bool(s.strip()) and not SKIP.match(s) and not is_path_data(s)


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
        if is_human(o) and o not in TR_SPEC and o not in SPEC_UNSAFE:
            missing.add(o)
        return TR_SPEC.get(o, o)
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


# <title>/<desc> nodes carry tooltips + alt text; translated as whole-node contents.
TOOLTIP_RE = re.compile(r"(<(title|desc)\b[^>]*>)([^<]+)(</(?:title|desc)>)")
# A <text> element may mix bare text with <tspan> children; every maximal run of
# text between a ">" and the next "<" is a separately-rendered visible fragment, so
# captions split across <tspan> (bold names, emphasised words) still fully localise.
TEXT_BLOCK = re.compile(r"<text\b[^>]*>.*?</text>", re.S)
NESTED_TAG = re.compile(r"<(?:title|desc)\b[^>]*>.*?</(?:title|desc)>", re.S)
RUN = re.compile(r"(>)([^<>]+)(<)")
missing_hover: set[str] = set()  # untranslated strings that live only in <title> tooltips


def localize_hero(name: str) -> None:
    t = (GALLERY / f"{name}.svg").read_text(encoding="utf-8")

    def tip(m: re.Match) -> str:
        tag, raw = m.group(2), m.group(3)
        key = re.sub(r"\s+", " ", html.unescape(raw)).strip()
        if key in TR:
            return m.group(1) + html.escape(TR[key], quote=False) + m.group(4)
        # Compositional fallback: a "Label — Category" tooltip whose whole text
        # is not mapped but whose em-dash suffix is a known key (e.g. a seat
        # tooltip "Emma Martin — Green League" over the party map). Translate
        # just the suffix and keep the proper-name prefix verbatim, so a roster
        # of hundreds of per-item tooltips localises from one category entry
        # and the prefix is not flagged as a gap.
        if " — " in key:
            prefix, _, suffix = key.rpartition(" — ")
            if suffix in TR:
                new = f"{prefix} — {TR[suffix]}"
                return m.group(1) + html.escape(new, quote=False) + m.group(4)
        if is_human(key):
            (missing_hover if tag == "title" else missing).add(key)
        return m.group(0)

    def run(m: re.Match) -> str:
        raw = m.group(2)
        key = re.sub(r"\s+", " ", html.unescape(raw)).strip()
        if key in TR:
            lead = raw[: len(raw) - len(raw.lstrip())]
            trail = raw[len(raw.rstrip()):]
            return m.group(1) + lead + html.escape(TR[key], quote=False) + trail + m.group(3)
        if is_human(key):
            missing.add(key)
        return m.group(0)

    def block_sub(b: re.Match) -> str:
        # <title>/<desc> nested inside a <text> were already localised by tip();
        # mask them so the RUN pass doesn't re-scan (and mis-flag) their contents.
        block = b.group(0)
        stash: list[str] = []

        def mask(m: re.Match) -> str:
            stash.append(m.group(0))
            return f"<\x00{len(stash) - 1}\x00>"

        block = NESTED_TAG.sub(mask, block)
        block = RUN.sub(run, block)
        return re.sub(r"<\x00(\d+)\x00>", lambda m: stash[int(m.group(1))], block)

    t = TOOLTIP_RE.sub(tip, t)
    t = TEXT_BLOCK.sub(block_sub, t)
    (FR / f"{name}.svg").write_text(t, encoding="utf-8")


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
            # Route by what the EN gallery file actually IS, not merely by
            # whether a Vega spec happens to exist. Several kinds ship a
            # hand-authored ("hero") SVG in the gallery while a parallel Vega
            # spec also lives under assets/vega-examples; those must localise
            # from the hero the reader sees, not re-render the stale spec — else
            # EN and FR would show different figures. A Vega render (or a raster
            # figure with no gallery SVG) still goes through the spec.
            en_is_vega = ext == "svg" and 'class="marks"' in (
                (GALLERY / f"{name}.svg").read_text(encoding="utf-8", errors="ignore")[:600]
            )
            if name in SPECS and (ext != "svg" or en_is_vega):
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
        print(f"\n{len(missing)} VISIBLE strings still UNTRANSLATED (add to {YAML.name}):")
        for s in sorted(missing):
            print(f"  {s!r}")
    if missing_hover:
        print(f"\n{len(missing_hover)} hover-tooltip strings still untranslated (lower priority).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

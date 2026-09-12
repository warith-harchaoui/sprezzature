#!/usr/bin/env python3
"""Localise the figure gallery from a single i18n map.

Reads ``web/i18n/figures.fr.yaml`` (a flat ``"English": "Français"`` map) and
writes a French version of every gallery figure into ``web/img/figures/fr/``
by localising the exact gallery SVG the reader sees: substituting the text of
each ``<text>/<tspan>/<title>/<desc>`` node through the map. Every figure in
the source repo (sprezzature-figures) is hand-authored SVG, so this is the
only localisation path there is — there is no chart spec anywhere to
re-render from. A handful of raster-only gallery assets
(``.png`` with no matching ``.svg``) have no text nodes to translate and are
skipped.

Every human string it meets that is NOT in the map is reported at the end, so
the map's gaps are always visible (the "audit i18n" list). Idempotent: run it
again after editing the YAML to refresh only what changed.

Usage:  python tools/localize_figures.py [--only name1,name2]
"""
from __future__ import annotations

import glob
import html
import re
import sys
from pathlib import Path

import yaml

WEB = Path(__file__).resolve().parent.parent
FIGREPO = Path.home() / "sprezzature-figures"
GALLERY = WEB / "img" / "figures"
FR = GALLERY / "fr"
YAML = WEB / "i18n" / "figures.fr.yaml"
PATTERNS_YAML = WEB / "i18n" / "figures.fr.patterns.yaml"

sys.path.insert(0, str(FIGREPO))
sys.path.insert(0, str(FIGREPO / "scripts"))
from _textfit import text_width  # noqa: E402

# Mirrors sprezzature_figures scripts/_svg.py::tooltip_bubble()'s own geometry
# constants exactly (pad, line-height factor) -- the bubble-resize pass below
# has to reproduce that formula to stay pixel-consistent with the corporate
# gallery's own bubbles, just fed the localised text instead of the English.
_TIP_PAD = 9.0
_TIP_LH_FACTOR = 1.28


def _fit_canvas(svg: str) -> str:
    """Widen the canvas so localised (usually longer) text is not clipped.

    French runs longer than English, so a string dropped into an
    English-sized SVG can overrun the right edge. Rather than redraw each
    figure, measure every ``<text>`` node's horizontal extent and, if the
    widest reaches past the viewBox, grow the canvas symmetrically (pad both
    sides) and shift the whole drawing right by the pad, so centred figures
    stay centred and nothing is cut off. Language-independent: it reacts to the
    actual rendered width of whatever string is present.
    """
    m = re.match(r"<svg\b([^>]*)>", svg)
    if not m:
        return svg
    head = m.group(1)
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head)
    if not vb:
        return svg
    vw, vh = float(vb.group(1)), float(vb.group(2))

    max_right = 0.0
    for tm in re.finditer(r"<text\b([^>]*)>(.*?)</text>", svg, re.S):
        attrs, inner = tm.group(1), tm.group(2)
        xa = re.search(r'\bx="(-?[\d.]+)"', attrs)
        if not xa:
            continue
        x = float(xa.group(1))
        fs_a = re.search(r'font-size="([\d.]+)', attrs)
        fs = float(fs_a.group(1)) if fs_a else 16.0
        anchor_a = re.search(r'text-anchor="(\w+)"', attrs)
        anchor = anchor_a.group(1) if anchor_a else "start"
        # Prefer per-tspan positions when present; else the whole visible text.
        tspans = re.findall(r'<tspan\b([^>]*)>([^<]*)</tspan>', inner)
        pieces = []
        if tspans:
            for ta, txt in tspans:
                txa = re.search(r'\bx="(-?[\d.]+)"', ta)
                tfs = re.search(r'font-size="([\d.]+)', ta)
                pieces.append((float(txa.group(1)) if txa else x,
                               float(tfs.group(1)) if tfs else fs, txt, anchor))
        else:
            visible = re.sub(r"<[^>]+>", "", inner)
            pieces.append((x, fs, visible, anchor))
        for px, pfs, txt, anc in pieces:
            w = text_width(txt.strip(), pfs)
            right = px + w if anc == "start" else (px + w / 2 if anc == "middle" else px)
            max_right = max(max_right, right)

    pad = max_right + 22.0 - vw  # keep a comfortable right margin, not a hairline
    if pad <= 2.0:
        return svg
    pad = min(pad, 0.4 * vw)  # never balloon the canvas
    new_vw = vw + 2 * pad
    body = svg[m.end():svg.rindex("</svg>")]
    new_head = re.sub(r'viewBox="0 0 [\d.]+ ([\d.]+)"', f'viewBox="0 0 {new_vw:.0f} \\1"', head)
    new_head = re.sub(r'\bwidth="[\d.]+"', f'width="{new_vw:.0f}"', new_head, count=1)
    return (
        f"<svg{new_head}>"
        f'<rect width="{new_vw:.0f}" height="{vh:.0f}" fill="#FFFFFF"/>'
        f'<g transform="translate({pad:.0f},0)">{body}</g>'
        "</svg>"
    )

def _num(v: float) -> str:
    """Format a coordinate the way the generators' own fmt_compact does."""
    r = round(v, 2)
    return str(int(r)) if r == int(r) else f"{r:.2f}".rstrip("0").rstrip(".")


_TIP_GROUP_RE = re.compile(r'<g class="tip">.*?</g>', re.S)
_TIP_RECT_RE = re.compile(
    r'<rect x="(-?[\d.]+)" y="(-?[\d.]+)" width="([\d.]+)" height="([\d.]+)"([^/]*)/>'
)
_TIP_TEXT_RE = re.compile(
    r'<text x="(-?[\d.]+)" y="(-?[\d.]+)"([^>]*)>(.*?)</text>', re.S
)


def _resize_tip_bubbles(svg: str) -> str:
    """Re-fit each ``tooltip_bubble()`` card's rect to its (now localised) text.

    ``tooltip_bubble()`` (sprezzature_figures scripts/_svg.py) bakes the
    bubble's rect width from the *English* line lengths at generation time --
    a plain text substitution leaves that rect sized for English, so any
    French line that runs longer than its English source overflows the card.
    French tends to run 15-20% longer than English on average, so this is
    not an edge case; it is the common one.

    Re-derives the same width formula the generator uses (now via the
    higher-fidelity ``text_width()`` glyph estimate rather than the
    generator's own cruder ``len(s) * 0.56`` approximation -- fine, since
    the target is "big enough for this text", not byte parity with the
    corporate SVG) from the *translated* line content, keeps the vertical
    geometry untouched (line count and font-size never change here, so
    height/y are already correct), and re-centres the rect horizontally on
    its original centre point so it grows/shrinks symmetrically rather than
    drifting off the anchor. Clamped to the figure's own (possibly
    already-widened by :func:`_fit_canvas`) canvas width.
    """
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    canvas_w = float(vb.group(1)) if vb else None

    def fix_one(m: re.Match) -> str:
        block = m.group(0)
        rect_m = _TIP_RECT_RE.search(block)
        lines = _TIP_TEXT_RE.findall(block)
        if not rect_m or not lines:
            return block
        old_x, old_y, old_w, old_h, rect_tail = rect_m.groups()
        old_x, old_w = float(old_x), float(old_w)

        widths = []
        for i, (_x, _y, attrs, inner) in enumerate(lines):
            fs_m = re.search(r'font-size="([\d.]+)"', attrs)
            font_size = float(fs_m.group(1)) if fs_m else 12.5
            text = html.unescape(re.sub(r"<[^>]+>", "", inner))
            widths.append(text_width(text, font_size, bold=(i == 0)))
        new_w = max(widths, default=0.0) + 2 * _TIP_PAD

        old_center = old_x + old_w / 2.0
        new_x = old_center - new_w / 2.0
        if canvas_w is not None:
            new_x = max(4.0, min(new_x, canvas_w - new_w - 4.0))

        block = _TIP_RECT_RE.sub(
            f'<rect x="{_num(new_x)}" y="{old_y}" width="{_num(new_w)}" '
            f'height="{old_h}"{rect_tail}/>',
            block, count=1,
        )
        new_text_x = _num(new_x + _TIP_PAD)
        block = _TIP_TEXT_RE.sub(
            lambda tm: f'<text x="{new_text_x}" y="{tm.group(2)}"{tm.group(3)}>{tm.group(4)}</text>',
            block,
        )
        return block

    return _TIP_GROUP_RE.sub(fix_one, svg)


TR: dict[str, str] = yaml.safe_load(YAML.read_text(encoding="utf-8")) or {}
SKIP = re.compile(r"^[\d\s.,%:+\-–—−/()·°×→←]*$")  # pure punctuation / numbers
# SVG path data (a mark.shape, a precomputed hex tile, ...) is geometry, not
# prose: it starts with a move command and every letter in it is a path command.
# It must never be treated as human text — a stray "translation" that turned its
# decimal points into French commas once silently emptied the hexbin figure.
_PATH_CMDS = set("MmLlHhVvCcSsQqTtAaZz")


def is_path_data(s: str) -> bool:
    s = s.strip()
    return bool(s) and s[0] in "Mm" and all(ch in _PATH_CMDS for ch in s if ch.isalpha())


missing: set[str] = set()


def is_human(s: str) -> bool:
    return bool(s.strip()) and not SKIP.match(s) and not is_path_data(s)


def gallery_ext(name: str) -> str | None:
    if (GALLERY / f"{name}.svg").exists():
        return "svg"
    if (GALLERY / f"{name}.png").exists():
        return "png"
    return None


# <title>/<desc> nodes carry tooltips + alt text; translated as whole-node contents.
TOOLTIP_RE = re.compile(r"(<(title|desc)\b[^>]*>)([^<]+)(</(?:title|desc)>)")
# A <text> element may mix bare text with <tspan> children; every maximal run of
# text between a ">" and the next "<" is a separately-rendered visible fragment, so
# captions split across <tspan> (bold names, emphasised words) still fully localise.
TEXT_BLOCK = re.compile(r"<text\b[^>]*>.*?</text>", re.S)
NESTED_TAG = re.compile(r"<(?:title|desc)\b[^>]*>.*?</(?:title|desc)>", re.S)
RUN = re.compile(r"(>)([^<>]+)(<)")
missing_hover: set[str] = set()  # untranslated strings that live only in <title> tooltips

# Number formatting is a property of the target language, not of the figure:
# English writes 0.75 and 124,800, French writes 0,75 and 124 800 (a narrow
# no-break space, U+202F). Getting the second one wrong is worse than leaving
# it alone — "124,800" reads as 124.8 to a French reader, off by a factor of
# a thousand — so the grouping separator is converted, not just the decimal.
#
# Applied only to a visible run that is a bare number and nothing else: an axis
# tick, a data label. A version string, a date, or a number inside a sentence
# is left alone — a sentence's numbers arrive through the translation map,
# already written in French. An integer written without a separator is left
# alone too: "2024" is as likely to be a year or an identifier as a quantity,
# and there is nothing in the text node that says which.
DECIMAL_SEP = ","
GROUP_SEP = "\u202f"
_BARE_NUMBER = re.compile(
    r"^(\s*)([+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[+-]?\d+\.\d+)(\s*)$"
)


#: Per-datum labels ("x = 3.5", "Fitted 142 k$", "63% of densest cell") are
#: one sentence written a few hundred times with different numbers in it. A
#: flat English-to-French map would need an entry per occurrence — 11 668 of
#: them across the gallery, for 1 783 distinct shapes — so those go through
#: patterns instead: a regex per shape, and a French template beside it.
#: Numbers captured by the regex come out formatted the French way.
_PATTERNS: list[tuple[re.Pattern[str], str]] = []


def load_patterns() -> None:
    """Read the pattern rules, if the file is there. Absence is not an error."""
    if not PATTERNS_YAML.exists():
        return
    rules = yaml.safe_load(PATTERNS_YAML.read_text(encoding="utf-8")) or []
    for i, rule in enumerate(rules, 1):
        try:
            _PATTERNS.append((re.compile(rule["match"]), rule["write"]))
        except (KeyError, re.error) as exc:
            print(f"  rule {i} in {PATTERNS_YAML.name} ignored: {exc}")


def fr_numbers_in(text: str) -> str:
    """Every number inside `text` written the French way, the rest untouched.

    A captured group is not always one bare number: a rule for "4.0-4.4 h
    slept" captures a range, one for "$27.4T total GDP" captures a figure with
    a unit stuck to it. Formatting only whole-group numbers left those written
    the English way inside otherwise French sentences, which is the one outcome
    worse than not translating at all.
    """
    return _NUMBER_TOKEN.sub(lambda m: fr_number(m.group(0)) or m.group(0), text)


#: A number on its own, not part of a time (00:00) or an identifier (v1.2.3).
_NUMBER_TOKEN = re.compile(
    r"(?<![\d:.,])([+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[+-]?\d+\.\d+)(?![\d:.,])"
)


def by_pattern(run_text: str) -> str | None:
    """`run_text` rewritten by the first matching rule, or None if none match."""
    for pattern, template in _PATTERNS:
        m = pattern.fullmatch(run_text.strip())
        if m is None:
            continue
        groups = [fr_numbers_in(g) if g is not None else "" for g in m.groups()]
        try:
            return template.format(*groups)
        except (IndexError, KeyError):
            print(f"  rule {pattern.pattern!r}: template wants a group it has not got")
            return None
    return None


def fr_number(run_text: str) -> str | None:
    """`run_text` written the French way, or None if it is not a bare number."""
    m = _BARE_NUMBER.match(run_text)
    if m is None:
        return None
    number = m.group(2).replace(",", GROUP_SEP).replace(".", DECIMAL_SEP)
    return m.group(1) + number + m.group(3)


def by_parts(text: str) -> str | None:
    """
    `text` rebuilt from its own pieces, or None if any piece is untranslatable.

    A composite tooltip — "LFP (iron phosphate): Energy density 170 Wh/kg,
    Fast-charge time 55 min" — is a known prefix followed by a list of known
    measurements. Each piece is already in the map or matched by a pattern;
    only the assembled sentence is not, and there is one per combination of
    battery and pair of metrics. Splitting on the punctuation that joins them
    turns a combinatorial list of tooltips back into the handful of phrases it
    was built from.

    Every piece must resolve. A half-translated tooltip reads worse than an
    English one, because the reader cannot tell which half to trust.
    """
    def piece(part: str) -> str | None:
        part = part.strip()
        return TR.get(part) or by_pattern(part) or fr_number(part)

    head, sep, tail = text.partition(": ")
    if not sep:
        return None
    head_fr = piece(head)
    if head_fr is None:
        return None
    parts = [piece(p) for p in tail.split(", ")]
    if any(p is None for p in parts):
        return None
    return f"{head_fr} : " + ", ".join(parts)


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
        rebuilt = by_pattern(key) or by_parts(key)
        if rebuilt is not None:
            return m.group(1) + html.escape(rebuilt, quote=False) + m.group(4)
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
        number = fr_number(raw)
        if number is not None:
            return m.group(1) + number + m.group(3)
        patterned = by_pattern(key) or by_parts(key)
        if patterned is not None:
            lead = raw[: len(raw) - len(raw.lstrip())]
            trail = raw[len(raw.rstrip()):]
            return m.group(1) + lead + html.escape(patterned, quote=False) + trail + m.group(3)
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
    t = _fit_canvas(t)  # grow the canvas if the localised text now overruns it
    t = _resize_tip_bubbles(t)  # re-fit hover-bubble cards to their new text
    out_svg = FR / f"{name}.svg"
    out_svg.write_text(t, encoding="utf-8")
    _rasterise(out_svg, FR / f"{name}.png")


#: Gallery thumbnails are a fixed 900px wide whatever the figure's viewBox.
THUMB_WIDTH = 900
_VIEWBOX_RE = re.compile(r'viewBox="0 0 ([\d.]+) ([\d.]+)"')


def _rasterise(svg: Path, png: Path) -> None:
    """
    Write `svg`'s 900px-wide thumbnail to `png`.

    The English thumbnails come from each generator's own rasteriser, which is
    resvg (through ``resvg_py``); a localised figure is a transformed SVG with
    no generator behind it, so this calls the same library directly rather than
    a different one. It matters: rsvg-convert renders the same pixels but
    writes a PNG close to twice the size, and these are gallery thumbnails.

    A missing rasteriser is reported rather than raised — the localised SVG is
    the substantive output, and a missing thumbnail should not lose it.
    """
    text = svg.read_text(encoding="utf-8")
    m = _VIEWBOX_RE.search(text)
    if m is None:
        print(f"  no viewBox in {svg.name}: {png.name} not written")
        return
    zoom = THUMB_WIDTH / float(m.group(1))
    try:
        import resvg_py
    except ImportError:
        print(f"  resvg_py not installed: {png.name} not written")
        return
    try:
        png.write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=text, zoom=zoom)))
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL rasterising {svg.name}: {exc}")


def main() -> int:
    load_patterns()
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
            if ext == "svg":
                localize_hero(name)
            else:
                continue  # raster gallery asset: no text nodes to localise
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

"""
The design itself, on screen: the demo scenes of the films.

Written 2026-11-06, when the films were cut again from nothing. Warith: make
them understandable, and insist on the design. The set before showed a suite
of design tools mostly as cards of text about them (`34 passent`, `exit 1`,
a ratio with a colon in it), so a viewer was told about a button rather than
shown one. Each scene here *is* the thing: a pale button that a sunbeam
erases and the colour fix brings back, a portrait a screen reader can only
call "image" until the alt is written, a form that a command line turns
into.

Everything is HTML and CSS, drawn at the canvas size, so it is as sharp at 4K
as the type around it, and every colour on screen is a real one: the fixes in
``contrast`` are what ``sprezzature-colors`` returns for those inputs.

Each kind is two functions, ``<kind>_html(sc, f, i)`` and ``<kind>_js(sc, i)``,
dispatched by :func:`html` and :func:`js`. ``sc`` has already been put into
one language by ``build_films.in_language``.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from semantic_breaks import to_html  # noqa: E402

INK, SOFT, BLUE, LINE, PAPER = "#171717", "#525252", "#0072b2", "#e5e5e5", "#ffffff"
GOOD, BAD = "#0072b2", "#b2182b"
DOWN, RIGHT = "\u2193", "\u2192"
CARET = '<span class="d-caret">\u25be</span>'


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _width(f: dict, cap: int = 1500) -> int:
    return min(f["w"] - 2 * f["pad"], cap)


def _tall(f: dict) -> bool:
    return f["h"] > f["w"]


def _u(f: dict) -> int:
    """The demo's type unit: a demo is the picture, so it is set larger than body copy."""
    if f["w"] == f["h"]:
        return int(f["body"] * 1.05)
    return int(f["body"] * (1.25 if _tall(f) else 1.45))


def _verdict(i: int, k: str, text: str, ok: bool, size: int) -> str:
    mark = "✓" if ok else "✗"
    color = GOOD if ok else BAD
    return (
        f'<p class="d-verdict" id="s{i}-{k}" style="font-size:{size}px;color:{color}">'
        f'<span class="d-mark">{mark}</span> {to_html(text)}</p>'
    )


def _reveal(sel: str, at: float, *, y: int = 18, dur: float = 0.5) -> str:
    return (
        f'tl.fromTo("{sel}",{{y:{y},opacity:0}},'
        f'{{y:0,opacity:1,duration:{dur},ease:"power2.out"}},{at:.2f});'
    )


def _show(sel: str, at: float, dur: float = 0.35) -> str:
    return f'tl.to("{sel}",{{opacity:1,duration:{dur},ease:"power1.out"}},{at:.2f});'


def _hide(sel: str, at: float, dur: float = 0.3) -> str:
    return f'tl.to("{sel}",{{opacity:0,duration:{dur},ease:"power1.in"}},{at:.2f});'


# ---------------------------------------------------------------- contrast
def contrast_html(sc: dict, f: dict, i: int) -> str:
    """A booking card in the pale colours somebody picked at their desk."""
    u = int(f["body"] * (1.15 if f["h"] == f["w"] else 1.4))
    w = min(_width(f, 1180), int(f["h"] * 1.05))
    c = sc["card"]
    return (
        f'<div class="d-card" id="s{i}-card" style="width:{w}px;padding:{int(u * 1.3)}px">'
        f'<div class="d-glare" id="s{i}-glare"></div>'
        f'<p class="d-kicker" id="s{i}-kick" style="font-size:{int(u * 0.62)}px;'
        f'color:{c["fg_bad"]}">{esc(c["kicker"])}</p>'
        f'<p class="d-title" style="font-size:{int(u * 1.45)}px">{to_html(c["title"])}</p>'
        f'<p class="d-sub" id="s{i}-sub" style="font-size:{int(u * 0.9)}px;'
        f'color:{c["fg_bad"]}">{to_html(c["sub"])}</p>'
        f'<span class="d-button" id="s{i}-btn" style="font-size:{int(u * 0.9)}px;'
        f'background:{c["btn_bad"]};padding:{int(u * 0.5)}px {int(u * 1.1)}px">'
        f'{esc(c["button"])}</span></div>'
        f'<div class="d-verdicts" style="margin-top:{int(u * 0.9)}px">'
        f'{_verdict(i, "bad", sc["bad"], False, int(u * 0.8))}'
        f'{_verdict(i, "good", sc["good"], True, int(u * 0.8))}</div>'
    )


def contrast_js(sc: dict, i: int) -> list[str]:
    c, s = sc["card"], sc["start"]
    out = [
        f'tl.fromTo("#s{i}-card",{{y:36,opacity:0}},{{y:0,opacity:1,duration:.7,ease:"power3.out"}},{s + 0.15:.2f});',
        f'tl.set("#s{i}-good",{{opacity:0}},{s:.2f});',
        f'tl.set("#s{i}-bad",{{opacity:0}},{s:.2f});',
    ]
    if sc.get("glare_at"):
        g = sc["glare_at"]
        out += [
            f'tl.fromTo("#s{i}-glare",{{opacity:0}},{{opacity:.86,duration:1.4,ease:"sine.inOut"}},{g:.2f});',
            f'tl.to("#s{i}-glare",{{opacity:0,duration:1.2,ease:"sine.inOut"}},{g + 3.4:.2f});',
        ]
    if sc.get("bad_at"):
        out.append(_show(f"#s{i}-bad", sc["bad_at"]))
    if sc.get("fix_at"):
        x = sc["fix_at"]
        out += [
            f'tl.to(["#s{i}-sub","#s{i}-kick"],{{color:"{c["fg_good"]}",duration:1.6,ease:"power2.inOut"}},{x:.2f});',
            f'tl.to("#s{i}-btn",{{backgroundColor:"{c["btn_good"]}",duration:1.6,ease:"power2.inOut"}},{x:.2f});',
            _hide(f"#s{i}-bad", x),
            _show(f"#s{i}-good", x + 1.5),
        ]
        if sc.get("glare2_at"):
            g = sc["glare2_at"]
            out += [
                f'tl.to("#s{i}-glare",{{opacity:.86,duration:1.4,ease:"sine.inOut"}},{g:.2f});',
                f'tl.to("#s{i}-glare",{{opacity:0,duration:1.2,ease:"sine.inOut"}},{g + 3.2:.2f});',
            ]
    return out


# ---------------------------------------------------------------- alt
def alt_html(sc: dict, f: dict, i: int) -> str:
    """A portrait, and what a screen reader says about it."""
    u = _u(f)
    tall = _tall(f)
    pw = int(f["w"] * (0.56 if tall else 0.27)) if f["h"] != f["w"] else int(f["w"] * 0.34)
    ph = int(pw * 2105 / 1549)
    words = sc["alt"].split()
    alt = " ".join(f'<span class="d-w" id="s{i}-w{k}">{esc(w)}</span>' for k, w in enumerate(words))
    bubble_w = int(_width(f) * (0.92 if tall else 0.52)) if f["h"] != f["w"] else int(_width(f) * 0.56)
    return (
        f'<div class="d-row" style="flex-direction:{"column" if tall else "row"};'
        f'gap:{int(u * 1.2)}px">'
        f'<img class="d-photo" id="s{i}-photo" src="assets/{sc["src"]}" alt="" '
        f'style="width:{pw}px;height:{ph}px">'
        f'<div class="d-bubble" id="s{i}-bubble" style="width:{bubble_w}px;padding:{int(u * 0.9)}px {int(u * 1.1)}px">'
        f'<p class="d-who" style="font-size:{int(u * 0.62)}px">\U0001F50A {esc(sc["who"])}</p>'
        f'<p class="d-said" id="s{i}-said" style="font-size:{int(u * 1.5)}px">« {esc(sc["said"])} »</p>'
        f'<p class="d-alt" id="s{i}-alt" style="font-size:{int(u * 0.98)}px">{alt}</p>'
        f"</div></div>"
    )


def alt_js(sc: dict, i: int) -> list[str]:
    s = sc["start"]
    out = [
        f'tl.fromTo("#s{i}-photo",{{scale:.97,opacity:0}},{{scale:1,opacity:1,duration:.7,ease:"power3.out"}},{s + 0.1:.2f});',
        _reveal(f"#s{i}-bubble", sc["said_at"] - 0.4),
        f'tl.set("#s{i}-said",{{opacity:0}},{s:.2f});',
        _show(f"#s{i}-said", sc["said_at"], 0.2),
        f'tl.set("#s{i} .d-w",{{opacity:0}},{s:.2f});',
    ]
    if sc.get("alt_at"):
        out.append(_hide(f"#s{i}-said", sc["alt_at"] - 0.3, 0.25))
        out.append(
            f'tl.set("#s{i}-said",{{display:"none"}},{sc["alt_at"]:.2f});'
        )
        n = len(sc["alt"].split())
        step = sc.get("alt_step", 0.16)
        for k in range(n):
            out.append(
                f'tl.to("#s{i}-w{k}",{{opacity:1,duration:.12}},{sc["alt_at"] + k * step:.2f});'
            )
    return out


# ---------------------------------------------------------------- pair
def pair_html(sc: dict, f: dict, i: int) -> str:
    """Two pictures of the same thing, one wrong and one right."""
    u = _u(f)
    tall = _tall(f)
    gap = int(u * 1.1)
    out = []
    for k, side in enumerate(("left", "right")):
        # The pictures sit in `images` like every other scene's, so a French
        # cut swaps them for their twins and the English-in-French ledger
        # sees them; the labels stay per side.
        src = sc["images"][k]
        ratio, label, ok = sc[side]
        if tall:
            tw = _width(f) - 40
            th = int(tw / ratio)
            room = (f["h"] - 2 * f["pad"] - 6 * u) // 2
            if th > room:
                th = room
                tw = int(th * ratio)
        else:
            tw = (_width(f) - gap) // 2
            th = int(tw / ratio)
            room = f["h"] - 2 * f["pad"] - int(f["eyebrow"] * 3) - 4 * u
            if th > room:
                th = room
                tw = int(th * ratio)
        out.append(
            f'<div class="d-side" id="s{i}-{side}">'
            f'<div class="tile" style="width:{tw}px;height:{th}px">'
            f'<img src="assets/{src}" alt=""></div>'
            f'{_verdict(i, side + "v", label, ok, int(u * 0.78))}</div>'
        )
    return (
        f'<div class="d-row" style="flex-direction:{"column" if tall else "row"};gap:{gap}px">'
        + "".join(out)
        + "</div>"
    )


def pair_js(sc: dict, i: int) -> list[str]:
    a, b = sc["at"]
    return [_reveal(f"#s{i}-left", a, y=30, dur=0.6), _reveal(f"#s{i}-right", b, y=30, dur=0.6)]


# ---------------------------------------------------------------- captions
def captions_html(sc: dict, f: dict, i: int) -> str:
    """A video still, captioned badly and then well."""
    u = _u(f)
    w = _width(f, 1400)
    h = int(w * 9 / 16)
    room = f["h"] - 2 * f["pad"] - 5 * u
    if h > room:
        h = room
        w = int(h * 16 / 9)
    bad = "".join(
        f'<p class="d-capbad" id="s{i}-b{k}" style="font-size:{max(14, int(w / 62))}px">{esc(t)}</p>'
        for k, t in enumerate(sc["bad_lines"])
    )
    import math

    wave = "".join(
        f'<i style="height:{int(18 + 70 * abs(math.sin(k * 0.55) * math.cos(k * 0.17)))}%"></i>'
        for k in range(48)
    )
    good = (
        f'<p class="d-capgood" id="s{i}-g" style="font-size:{int(w / 30)}px">'
        + "<br>".join(esc(t) for t in sc["good_lines"])
        + "</p>"
    )
    return (
        f'<div class="d-video" id="s{i}-video" style="width:{w}px;height:{h}px">'
        f'<div class="d-wave">{wave}</div>'
        f'<div class="d-shade"></div>{bad}{good}</div>'
        f'<div class="d-verdicts" style="margin-top:{int(u * 0.8)}px">'
        f'{_verdict(i, "bad", sc["bad"], False, int(u * 0.8))}'
        f'{_verdict(i, "good", sc["good"], True, int(u * 0.8))}</div>'
    )


def captions_js(sc: dict, i: int) -> list[str]:
    s = sc["start"]
    out = [
        f'tl.fromTo("#s{i}-video",{{scale:.97,opacity:0}},{{scale:1,opacity:1,duration:.7,ease:"power3.out"}},{s + 0.1:.2f});',
        f'tl.set(["#s{i} .d-capbad","#s{i}-g","#s{i}-bad","#s{i}-good"],{{opacity:0}},{s:.2f});',
    ]
    t = sc["bad_at"]
    for k in range(len(sc["bad_lines"])):
        out.append(f'tl.set("#s{i}-b{k}",{{opacity:1}},{t:.2f});')
        out.append(f'tl.set("#s{i}-b{k}",{{opacity:0}},{t + 0.55:.2f});')
        t += 0.7
    out.append(_show(f"#s{i}-bad", sc["bad_at"] + 0.3))
    out.append(_hide(f"#s{i}-bad", sc["good_at"] - 0.2))
    out.append(_show(f"#s{i}-g", sc["good_at"], 0.3))
    out.append(_show(f"#s{i}-good", sc["good_at"] + 0.4))
    # the bad flashes keep cycling until the good caption takes over
    t2 = t + 0.4
    while t2 + 0.6 < sc["good_at"]:
        for k in range(len(sc["bad_lines"])):
            if t2 + 0.6 >= sc["good_at"]:
                break
            out.append(f'tl.set("#s{i}-b{k}",{{opacity:1}},{t2:.2f});')
            out.append(f'tl.set("#s{i}-b{k}",{{opacity:0}},{t2 + 0.55:.2f});')
            t2 += 0.7
    return out


# ---------------------------------------------------------------- i18n
def i18n_html(sc: dict, f: dict, i: int) -> str:
    """One sign-in screen, its strings taken from a catalogue."""
    u = _u(f)
    w = min(_width(f, 1000), int(f["h"] * 0.9))
    layers = []
    for k, (code, s) in enumerate(sc["langs"]):
        layers.append(
            f'<div class="d-ui" id="s{i}-l{k}" style="padding:{int(u * 1.1)}px">'
            f'<p class="d-ui-title" style="font-size:{int(u * 1.25)}px">{esc(s[0])}</p>'
            f'<p class="d-ui-label" style="font-size:{int(u * 0.62)}px">{esc(s[1])}</p>'
            f'<div class="d-ui-input" style="height:{int(u * 1.5)}px"></div>'
            f'<p class="d-ui-label" style="font-size:{int(u * 0.62)}px">{esc(s[2])}</p>'
            f'<div class="d-ui-input" style="height:{int(u * 1.5)}px"></div>'
            f'<span class="d-button" style="font-size:{int(u * 0.8)}px;background:{BLUE};'
            f'padding:{int(u * 0.45)}px {int(u * 1.0)}px;margin-top:{int(u * 0.6)}px">{esc(s[3])}</span>'
            f'<p class="d-ui-link" style="font-size:{int(u * 0.6)}px">{esc(s[4])}</p>'
            f'<span class="d-lang" style="font-size:{int(u * 0.55)}px">{esc(code)}</span></div>'
        )
    return f'<div class="d-stack" id="s{i}-ui" style="width:{w}px">{"".join(layers)}</div>'


def i18n_js(sc: dict, i: int) -> list[str]:
    s = sc["start"]
    out = [
        f'tl.fromTo("#s{i}-ui",{{y:36,opacity:0}},{{y:0,opacity:1,duration:.7,ease:"power3.out"}},{s + 0.15:.2f});'
    ]
    for k in range(1, len(sc["langs"])):
        out.append(f'tl.set("#s{i}-l{k}",{{opacity:0}},{s:.2f});')
    for k, at in enumerate(sc["at"], 1):
        out.append(_hide(f"#s{i}-l{k - 1}", at, 0.35))
        out.append(f'tl.fromTo("#s{i}-l{k}",{{opacity:0,y:10}},{{opacity:1,y:0,duration:.4,ease:"power2.out"}},{at + 0.2:.2f});')
    return out


# ---------------------------------------------------------------- form
def form_html(sc: dict, f: dict, i: int) -> str:
    """A command line, and the form the same tool becomes."""
    u = _u(f)
    tall = _tall(f)
    square = f["w"] == f["h"]
    gap = int(u * 1.0)
    tw = _width(f) if (tall or square) else int(_width(f) * 0.47)
    fw = _width(f, 760) if (tall or square) else int(_width(f) * 0.42)
    mono = int(f["mono"] * (0.85 if square else (1.05 if tall else 1.3)))
    term = (
        f'<div class="d-term" id="s{i}-term" style="width:{tw}px;font-size:{mono}px;padding:{int(u * 0.8)}px">'
        f'<p><span class="d-prompt">$</span> {esc(sc["command"])}</p></div>'
    )
    fields = "".join(
        f'<div class="d-field" id="s{i}-f{k}"><p class="d-ui-label" style="font-size:{int(u * (0.5 if square else 0.6))}px">{esc(label)}</p>'
        f'<div class="d-ui-input d-filled" style="font-size:{int(u * (0.62 if square else 0.72))}px;'
        f'padding:{int(u * 0.3)}px {int(u * 0.5)}px">{esc(value)}'
        f'{CARET if choice else ""}</div></div>'
        for k, (label, value, choice) in enumerate(sc["fields"])
    )
    form = (
        f'<div class="d-ui" id="s{i}-form" style="width:{fw}px;padding:{int(u * (0.7 if square else 1.0))}px">'
        f"{fields}"
        f'<span class="d-button" style="font-size:{int(u * 0.7)}px;background:{BLUE};'
        f'padding:{int(u * 0.4)}px {int(u * 0.9)}px;margin-top:{int(u * 0.4)}px">{esc(sc["button"])}</span></div>'
    )
    return (
        f'<div class="d-row" style="flex-direction:{"column" if (tall or square) else "row"};gap:{gap}px;align-items:center">'
        f'{term}<p class="d-arrow" id="s{i}-arrow" style="font-size:{int(u * 1.4)}px">{DOWN if (tall or square) else RIGHT}</p>{form}</div>'
    )


def form_js(sc: dict, i: int) -> list[str]:
    s = sc["start"]
    out = [_reveal(f"#s{i}-term", s + 0.2, y=24, dur=0.6)]
    out.append(_reveal(f"#s{i}-arrow", sc["form_at"] - 0.3, y=0))
    out.append(_reveal(f"#s{i}-form", sc["form_at"], y=30, dur=0.6))
    for k in range(len(sc["fields"])):
        out.append(_reveal(f"#s{i}-f{k}", sc["form_at"] + 0.4 + k * 0.35, y=10, dur=0.35))
    return out


# ---------------------------------------------------------------- site
def site_html(sc: dict, f: dict, i: int) -> str:
    """A Markdown file, and the page it becomes, reading itself aloud."""
    u = _u(f)
    tall = _tall(f)
    square = f["w"] == f["h"]
    stacked = tall or square
    mw = _width(f) if stacked else int(_width(f) * 0.4)
    bw = _width(f, 1000) if stacked else int(_width(f) * 0.56)
    k_md = 0.62 if square else (0.85 if tall else 1.0)
    lines = sc["markdown"].split("\n") if isinstance(sc["markdown"], str) else sc["markdown"]
    md = "".join(f"<p>{esc(line) or '&nbsp;'}</p>" for line in lines)
    sentences = " ".join(
        f'<span class="d-sent" id="s{i}-x{k}">{esc(t)}</span>' for k, t in enumerate(sc["sentences"])
    )
    page = (
        f'<div class="d-browser" id="s{i}-page" style="width:{bw}px">'
        f'<div class="d-tab" style="font-size:{int(u * 0.5)}px"><img src="assets/logo-512.png" alt="">'
        f'{esc(sc["tab"])}</div>'
        f'<div class="d-pagebody" style="padding:{int(u * (0.6 if square else 0.9))}px {int(u * 1.1)}px">'
        f'<p class="d-ptitle" style="font-size:{int(u * (0.95 if square else 1.25))}px">{esc(sc["title"])}</p>'
        f'<p class="d-ptext" style="font-size:{int(u * (0.56 if square else 0.68))}px">{sentences}</p>'
        f'<p class="d-listen" id="s{i}-listen" style="font-size:{int(u * 0.52)}px">▶ {esc(sc["listen"])}</p>'
        f"</div></div>"
    )
    mdbox = (
        f'<div class="d-term d-md" id="s{i}-md" style="width:{mw}px;font-size:{int(f["mono"] * k_md)}px;'
        f'padding:{int(u * 0.6)}px">{md}</div>'
    )
    return (
        f'<div class="d-row" style="flex-direction:{"column" if stacked else "row"};gap:{int(u * 0.7)}px;align-items:center">'
        f'{mdbox}<p class="d-arrow" id="s{i}-arrow" style="font-size:{int(u * (0.9 if square else 1.3))}px">'
        f'{DOWN if stacked else RIGHT}</p>{page}</div>'
    )


def site_js(sc: dict, i: int) -> list[str]:
    s = sc["start"]
    out = [
        _reveal(f"#s{i}-md", s + 0.2, y=24, dur=0.6),
        _reveal(f"#s{i}-arrow", sc["page_at"] - 0.3, y=0),
        _reveal(f"#s{i}-page", sc["page_at"], y=30, dur=0.6),
    ]
    for k, at in enumerate(sc.get("read_at", [])):
        if k:
            out.append(f'tl.to("#s{i}-x{k - 1}",{{backgroundColor:"rgba(0,114,178,0)",duration:.25}},{at:.2f});')
        out.append(f'tl.to("#s{i}-x{k}",{{backgroundColor:"rgba(0,114,178,0.22)",duration:.25}},{at:.2f});')
    return out


# ---------------------------------------------------------------- check
def check_html(sc: dict, f: dict, i: int) -> str:
    """A frame of a film that says something false, and the check that sees it."""
    u = _u(f)
    w = _width(f, 1200)
    h = int(w * 9 / 16)
    room = f["h"] - 2 * f["pad"] - 6 * u
    if h > room:
        h = room
        w = int(h * 16 / 9)
    return (
        f'<div class="d-frame" id="s{i}-frame" style="width:{w}px;height:{h}px">'
        f'<p class="d-frame-num" style="font-size:{int(h * 0.3)}px">'
        f'<span id="s{i}-old">{esc(sc["old"])}</span><span id="s{i}-new">{esc(sc["new"])}</span></p>'
        f'<p class="d-frame-txt" style="font-size:{int(h * 0.075)}px">{esc(sc["unit"])}</p></div>'
        f'<div class="d-verdicts" style="margin-top:{int(u * 0.8)}px">'
        f'{_verdict(i, "bad", sc["bad"], False, int(u * 0.8))}'
        f'{_verdict(i, "good", sc["good"], True, int(u * 0.8))}</div>'
    )


def check_js(sc: dict, i: int) -> list[str]:
    s = sc["start"]
    return [
        f'tl.fromTo("#s{i}-frame",{{scale:.97,opacity:0}},{{scale:1,opacity:1,duration:.7,ease:"power3.out"}},{s + 0.1:.2f});',
        f'tl.set(["#s{i}-new","#s{i}-bad","#s{i}-good"],{{opacity:0}},{s:.2f});',
        _show(f"#s{i}-bad", sc["bad_at"]),
        f'tl.to("#s{i}-old",{{color:"{BAD}",duration:.3}},{sc["bad_at"]:.2f});',
        _hide(f"#s{i}-old", sc["fix_at"]),
        _hide(f"#s{i}-bad", sc["fix_at"]),
        _show(f"#s{i}-new", sc["fix_at"] + 0.3, 0.4),
        _show(f"#s{i}-good", sc["fix_at"] + 0.6),
    ]


# ---------------------------------------------------------------- components
def components_html(sc: dict, f: dict, i: int) -> str:
    """The same panel in light and dark: one family of type, a focus you can see."""
    u = _u(f)
    tall = _tall(f)
    square = f["w"] == f["h"]
    k = 0.8 if square else 1.0
    w = (_width(f, 900) if tall else (_width(f) - u) // 2) if not square else (_width(f) - u) // 2
    t = sc["text"]
    out = []
    for mode in ("light", "dark"):
        out.append(
            f'<div class="d-ui d-{mode}" id="s{i}-{mode}" style="width:{w}px;padding:{int(u * 0.9 * k)}px">'
            f'<p class="d-ui-title" style="font-size:{int(u * 1.05 * k)}px">{esc(t["title"])}</p>'
            f'<p class="d-serif" style="font-size:{int(u * 0.66 * k)}px">{to_html(t["body"])}</p>'
            f'<p class="d-ui-label" style="font-size:{int(u * 0.55 * k)}px">{esc(t["label"])}</p>'
            f'<div class="d-ui-input d-filled" id="s{i}-{mode}-in" style="font-size:{int(u * 0.6 * k)}px;'
            f'padding:{int(u * 0.3 * k)}px {int(u * 0.45 * k)}px">{esc(t["value"])}</div>'
            f'<div style="display:flex;gap:{int(u * 0.4)}px;margin-top:{int(u * 0.7 * k)}px">'
            f'<span class="d-button" id="s{i}-{mode}-b1" style="font-size:{int(u * 0.62 * k)}px;background:{BLUE};'
            f'padding:{int(u * 0.38 * k)}px {int(u * 0.8 * k)}px">{esc(t["primary"])}</span>'
            f'<span class="d-button d-ghost" id="s{i}-{mode}-b2" style="font-size:{int(u * 0.62 * k)}px;'
            f'padding:{int(u * 0.38 * k)}px {int(u * 0.8 * k)}px">{esc(t["secondary"])}</span></div></div>'
        )
    stacked = tall and not square
    return (
        f'<div class="d-row" style="flex-direction:{"column" if stacked else "row"};gap:{int(u * 0.8)}px">'
        + "".join(out)
        + "</div>"
    )


def components_js(sc: dict, i: int) -> list[str]:
    s = sc["start"]
    out = [_reveal(f"#s{i}-light", s + 0.2, y=30, dur=0.6), _reveal(f"#s{i}-dark", s + 0.8, y=30, dur=0.6)]
    ring = "0 0 0 4px #ffffff, 0 0 0 8px #0072b2"
    for k, at in enumerate(sc.get("focus_at", [])):
        sel = ["-in", "-b1", "-b2"][k % 3]
        if k:
            prev = ["-in", "-b1", "-b2"][(k - 1) % 3]
            out.append(f'tl.set(["#s{i}-light{prev}","#s{i}-dark{prev}"],{{boxShadow:"none"}},{at:.2f});')
        out.append(f'tl.set(["#s{i}-light{sel}","#s{i}-dark{sel}"],{{boxShadow:"{ring}"}},{at:.2f});')
    return out


# ---------------------------------------------------------------- dispatch
KINDS = {
    "contrast": (contrast_html, contrast_js),
    "alt": (alt_html, alt_js),
    "pair": (pair_html, pair_js),
    "captions": (captions_html, captions_js),
    "i18n": (i18n_html, i18n_js),
    "form": (form_html, form_js),
    "site": (site_html, site_js),
    "check": (check_html, check_js),
    "components": (components_html, components_js),
}


def html(sc: dict, f: dict, i: int) -> str:
    return KINDS[sc["kind"]][0](sc, f, i)


def js(sc: dict, i: int) -> list[str]:
    return KINDS[sc["kind"]][1](sc, i)


def css(f: dict) -> str:
    """Shared demo styles; sizes that depend on the canvas are inline."""
    return f"""
    .d-card {{ position: relative; overflow: hidden; background: {PAPER};
      border: 2px solid {LINE}; border-radius: 28px; text-align: left;
      box-shadow: 0 30px 70px rgba(0,60,93,.14); }}
    .d-glare {{ position: absolute; inset: -20%; opacity: 0; pointer-events: none;
      background: radial-gradient(ellipse at 70% 30%, #fff 0%, rgba(255,255,255,.96) 35%,
        rgba(255,252,235,.75) 60%, rgba(255,255,255,0) 85%); }}
    .d-kicker {{ font-family: "Roboto Mono", monospace; letter-spacing: .14em;
      text-transform: uppercase; margin: 0 0 .6em; }}
    .d-title {{ font-family: "Roboto Serif", serif; font-weight: 700; color: {INK};
      margin: 0 0 .25em; line-height: 1.12; }}
    .d-sub {{ margin: 0 0 1.2em; line-height: 1.35; }}
    .d-button {{ display: inline-block; color: #fff; font-weight: 600; border-radius: 14px; }}
    .d-verdicts {{ position: relative; display: grid; justify-items: center; }}
    .d-verdicts > * {{ grid-area: 1 / 1; }}
    .d-verdict {{ margin: 0; font-weight: 600; text-align: center; }}
    .d-mark {{ font-weight: 800; }}
    .d-row {{ display: flex; align-items: center; justify-content: center; }}
    .d-side {{ display: flex; flex-direction: column; align-items: center; gap: 14px; }}
    .d-photo {{ object-fit: cover; border-radius: 22px; filter: grayscale(.1);
      box-shadow: 0 24px 60px rgba(0,0,0,.18); }}
    .d-bubble {{ background: {INK}; color: #fff; border-radius: 26px; text-align: left; }}
    .d-who {{ font-family: "Roboto Mono", monospace; letter-spacing: .1em; text-transform: uppercase;
      color: #a3a3a3; margin: 0 0 .7em; }}
    .d-said {{ font-family: "Roboto Serif", serif; margin: 0; }}
    .d-alt {{ margin: 0; line-height: 1.45; }}
    .d-video {{ position: relative; overflow: hidden; border-radius: 22px; background: #000;
      box-shadow: 0 30px 70px rgba(0,0,0,.25); }}
    .d-video img {{ width: 100%; height: 100%; object-fit: cover; }}
    .d-wave {{ position: absolute; inset: 18% 8% 38% 8%; display: flex; align-items: center;
      gap: 1.1%; }}
    .d-wave i {{ flex: 1; background: linear-gradient(#7fd1ff, #0072b2); border-radius: 99px;
      opacity: .85; }}
    .d-video {{ background: radial-gradient(ellipse at 50% 35%, #12344d 0%, #0b1620 75%) !important; }}
    .d-shade {{ position: absolute; inset: 55% 0 0 0;
      background: linear-gradient(transparent, rgba(0,0,0,.55)); }}
    .d-capbad {{ position: absolute; left: 3%; right: 3%; bottom: 6%; margin: 0; color: #fff;
      white-space: nowrap; overflow: hidden; text-align: center; background: rgba(0,0,0,.5); }}
    .d-capgood {{ position: absolute; left: 10%; right: 10%; bottom: 7%; margin: 0; color: #fff;
      text-align: center; line-height: 1.3; text-shadow: 0 2px 8px rgba(0,0,0,.6); }}
    .d-stack {{ display: grid; }}
    .d-stack > * {{ grid-area: 1 / 1; }}
    .d-ui {{ position: relative; background: {PAPER}; border: 2px solid {LINE}; border-radius: 26px;
      text-align: left; box-shadow: 0 30px 70px rgba(0,60,93,.12); }}
    .d-ui-title {{ font-family: "Roboto Serif", serif; font-weight: 700; color: {INK}; margin: 0 0 .7em; }}
    .d-ui-label {{ color: {SOFT}; font-weight: 500; margin: .7em 0 .3em; }}
    .d-ui-input {{ border: 2px solid #d4d4d4; border-radius: 12px; background: #fafafa; }}
    .d-filled {{ display: flex; justify-content: space-between; align-items: center;
      font-family: "Roboto Mono", monospace; color: {INK}; height: auto; }}
    .d-caret {{ color: {SOFT}; }}
    .d-ui-link {{ color: {BLUE}; margin: 1em 0 0; }}
    .d-lang {{ position: absolute; top: 1.2em; right: 1.4em; font-family: "Roboto Mono", monospace;
      font-weight: 600; color: {BLUE}; border: 2px solid {BLUE}; border-radius: 99px; padding: .15em .7em; }}
    .d-term {{ background: #0f1115; color: #e5e7eb; border-radius: 18px; text-align: left;
      font-family: "Roboto Mono", monospace; line-height: 1.6; box-shadow: 0 24px 60px rgba(0,0,0,.22); }}
    .d-term p {{ margin: 0; white-space: pre-wrap; }}
    .d-prompt {{ color: #7fd1ff; }}
    .d-md p {{ color: #e5e7eb; }}
    .d-arrow {{ color: {BLUE}; margin: 0; font-weight: 300; }}
    .d-browser {{ background: {PAPER}; border: 2px solid {LINE}; border-radius: 20px; overflow: hidden;
      text-align: left; box-shadow: 0 30px 70px rgba(0,60,93,.12); }}
    .d-tab {{ display: flex; align-items: center; gap: .6em; background: #f3f4f6; padding: .7em 1.2em;
      color: {SOFT}; border-bottom: 2px solid {LINE}; }}
    .d-tab img {{ width: 1.6em; height: 1.6em; }}
    .d-ptitle {{ font-family: "Roboto Serif", serif; font-weight: 700; color: {INK}; margin: 0 0 .5em; }}
    .d-ptext {{ color: #262626; line-height: 1.6; margin: 0; }}
    .d-sent {{ border-radius: 6px; padding: 0 .1em; background: rgba(0,114,178,0); }}
    .d-listen {{ color: {BLUE}; font-weight: 600; margin: 1em 0 0; }}
    .d-dark {{ background: #0b0b0c; border-color: #262626; }}
    .d-dark .d-ui-title {{ color: #f5f5f5; }}
    .d-dark .d-serif {{ color: #d4d4d4; }}
    .d-dark .d-ui-label {{ color: #a3a3a3; }}
    .d-dark .d-ui-input {{ background: #171717; border-color: #404040; color: #f5f5f5; }}
    .d-serif {{ font-family: "Roboto Serif", serif; color: #404040; line-height: 1.45; margin: 0 0 .4em; }}
    .d-ghost {{ background: transparent; color: {BLUE}; border: 2px solid {BLUE}; }}
    .d-dark .d-ghost {{ color: #7fd1ff; border-color: #7fd1ff; }}
    .d-frame {{ position: relative; background: #0b2233; border-radius: 22px; display: flex;
      flex-direction: column; align-items: center; justify-content: center;
      box-shadow: 0 30px 70px rgba(0,0,0,.25); }}
    .d-frame-num {{ display: grid; margin: 0; font-family: "Roboto Serif", serif; font-weight: 700;
      color: #fff; line-height: 1; }}
    .d-frame-num > span {{ grid-area: 1 / 1; text-align: center; }}
    .d-frame-txt {{ margin: .3em 0 0; color: #cfe8f7; font-family: "Roboto Mono", monospace;
      letter-spacing: .12em; text-transform: uppercase; }}
    """

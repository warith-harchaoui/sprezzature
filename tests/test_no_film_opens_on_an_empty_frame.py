"""
Frame zero of every cut is a finished frame of the film.

The defect, found 2026-10-27 by pulling frame zero out of a finished render
and looking at it: the wordmark was at opacity 0, the address was at opacity
0, and the opening sentence was at 35% — mid-grey type on a blank sheet.
Half a second later the same frame was correct, which is why nobody had
caught it. Nobody watches frame zero.

Except that frame zero is the frame most often seen on its own. It is what a
player falls back to when the poster has not loaded, what a scrubber shows
when a viewer drags to the start, and what a platform grabs as a thumbnail
when nobody gave it one. A viewer who lands on a blank frame has already
decided what kind of video this is.

Why the guard is here and not on the MP4
----------------------------------------
Decoding frame zero of sixty-six renders means having sixty-six renders, and
that is thirty-eight seconds of GPU each. It also tests the wrong thing: by
the time an MP4 exists the mistake has already cost an hour. The opacity of
the first frame is decided in one place — the tweens ``build_films.compose``
writes — so that is where it is checked, before anything is encoded.

The rule, stated as the generator can check it: **no tween that starts at
time zero may begin from a transparent state.** Motion at frame zero is
allowed and wanted — the rule under the opening sentence and the hairline
across the foot of the frame both draw themselves from ``scaleX: 0``, and a
hairline growing is not an empty frame. What is forbidden is arriving from
nothing, because "from nothing" is exactly what frame zero then shows.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))

#: A GSAP call in the emitted timeline: selector, the from-state, and the
#: time it is placed at. ``to()`` tweens cannot empty the first frame — they
#: start from whatever is already on screen — so only ``fromTo`` is read.
TWEEN = re.compile(
    r'tl\.fromTo\("(?P<sel>[^"]+)",\{(?P<frm>[^}]*)\},\{[^}]*\},(?P<at>[\d.]+)\);'
)

#: Close enough to frame zero that the first frame shows the from-state. One
#: frame at 30 fps is 33 ms.
FIRST_FRAME = 0.02


def _transparent(from_state: str) -> str | None:
    """The opacity this tween starts from, if it starts from less than full."""
    m = re.search(r"opacity:([\d.]+)", from_state)
    if m and float(m.group(1)) < 1.0:
        return m.group(1)
    return None


def test_nothing_fades_up_from_nothing_on_the_first_frame() -> None:
    """Every film, every canvas, every language.

    All three canvases, because the layout differs and the tweens are written
    per canvas; both languages, because a French cut is composed, not
    translated, and could acquire a scene of its own.
    """
    import build_films

    found: list[str] = []
    for film, lang in build_films.cuts():
        spec = build_films.FILMS[film]
        if spec["duration"] < 30:
            continue        # the retired eighteen-second group cuts
        for fmt in build_films.FORMATS:
            html = build_films.compose(film, spec, fmt, lang)
            for m in TWEEN.finditer(html):
                if float(m["at"]) > FIRST_FRAME:
                    continue
                faint = _transparent(m["frm"])
                if faint is not None:
                    found.append(
                        f"{film}.{lang}.{fmt}: {m['sel']} starts at "
                        f"opacity {faint} on frame zero"
                    )
    assert not found, (
        f"{len(found)} element(s) are transparent on the first frame:\n  "
        + "\n  ".join(found)
    )


def test_the_wordmark_is_on_screen_before_the_first_scene_ends() -> None:
    """The rails are a clip of their own, and it opens with the film.

    Held back to the end of scene one — which is what they used to be — the
    wordmark arrives six seconds in, after the only sentence that was going
    to make somebody stay.
    """
    import build_films

    late: list[str] = []
    for film, lang in build_films.cuts():
        spec = build_films.FILMS[film]
        if spec["duration"] < 30:
            continue
        for fmt in build_films.FORMATS:
            html = build_films.compose(film, spec, fmt, lang)
            m = re.search(r'<div id="rails" class="clip" data-start="([\d.]+)"', html)
            assert m, f"{film}.{lang}.{fmt} has no rails at all"
            if float(m.group(1)) > FIRST_FRAME:
                late.append(f"{film}.{lang}.{fmt}: rails open at {m.group(1)}s")
    assert not late, "\n  ".join(["the wordmark arrives late:", *late])


def test_no_two_scenes_share_an_element_id() -> None:
    """A duplicate id lets one scene's tween reach into another's markup.

    GSAP renders a ``fromTo`` start state when the tween is *created*, not
    when the timeline reaches it. So a tween placed at 55.4s still applies
    its from-state at frame zero, and ``fromTo("#logo", {opacity: 0}, ...)``
    resolves ``#logo`` to the first one in the document.

    That is how the identity card shipped without its logo on 2026-10-28:
    the card and the closing ask both used ``id="logo"``, the card's came
    first, and the ask's tween held it at opacity zero for fifty-five
    seconds. The ask looked perfect, which is the part that made it hard to
    see — six renders went by.
    """
    import build_films

    clashes: list[str] = []
    for film, lang in build_films.cuts():
        spec = build_films.FILMS[film]
        if spec["duration"] < 30:
            continue
        for fmt in build_films.FORMATS:
            html = build_films.compose(film, spec, fmt, lang)
            seen: dict[str, int] = {}
            for name in re.findall(r'\bid="([^"]+)"', html):
                seen[name] = seen.get(name, 0) + 1
            for name, n in sorted(seen.items()):
                if n > 1:
                    clashes.append(f"{film}.{lang}.{fmt}: id={name!r} appears {n}x")
    assert not clashes, (
        f"{len(clashes)} duplicate element id(s); a tween on one reaches the "
        f"other:\n  " + "\n  ".join(clashes)
    )

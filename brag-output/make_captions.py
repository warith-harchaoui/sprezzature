#!/usr/bin/env python3
"""The narration script of the eleven films, in both languages.

Not a transcript and not a translation
--------------------------------------
The text here is what the engine is asked to say; the timings are where each
line is asked to land. ``narrate_films.py`` reads this table, speaks it, and
returns the audio and the WebVTT together — so the cues are exact where a
transcriber would only be close.

The two language columns are **written, not translated**. Until 2026-10-28 the
French was a line-for-line rendering of the English: same number of lines, same
sentence boundaries, same clause order, French words in English syntax. On
screen that problem had already been fixed — ``build_films.L`` puts the two
languages on adjacent lines so each is composed with the rest of its own script
visible — and the voice was the half that had not caught up.

So the columns now diverge where the languages do. French splits a sentence
English runs on (``colors``: *La clarté, elle, tient.* alone on its line) and
runs on where English splits (``audio``: the ninety characters and *nobody
reads that* are one French breath). The two cuts of a film make the same case
with the same numbers and do not line up line by line, which is the point:
a viewer watches one of them, never both.

What governs the line count is the picture, not the other language. A line is
written to land on the scene it talks about, so a film with a long middle scene
takes more lines there in whichever language wants them.

Pitch, not plot
---------------
Every script runs Guy KAWASAKI's order — what, problem, solution, underlying
magic, call to action — and the material for each beat is the film's row in
``KAWASAKI.md``, which was taken from the package rather than from a feature
list. Three defects that order caught here, all of them invisible while the
beats lived only in the scene list:

* ``audio`` stated its numbers and never said why they are flags rather than
  laws. The numbers are the inventory; *conventions rather than laws* is the
  insight, and it was missing from the voice.
* ``maps`` spent its magic beat on the plate that draws no map and never
  reached the precision encoding — that ACLED and UCDP both record how well a
  coordinate is known, and that a tool drawing every one as the same dot
  asserts a street corner the source never gave.
* ``sprezzature`` said a vision model finds the fault and stopped there. What
  makes the loop worth a minute is the next clause: what you fix is the source.

Run from brag-output/:  python3 narrate_films.py
"""

from __future__ import annotations

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "scripts"))

#: start, nominal duration, text, per film and language.
#:
#: Since 2026-11-06 the words live in ``film_specs.VOICE``, beside the scenes
#: they are spoken over, and this table is derived from it. The start column
#: is a *request*: ``narrate_films`` moves a line later when the one before it
#: runs long. The duration column is nominal; the measured WAV decides.
from film_specs import VOICE as _VOICE  # noqa: E402

FILMS: dict[str, dict[str, list[tuple[float, float, str]]]] = {
    film: {lang: [(start, 3.0, text) for start, text in lines] for lang, lines in by_lang.items()}
    for film, by_lang in _VOICE.items()
}

#: The widest a caption line may be, from the Netflix Timed Text Style Guide,
#: which is the same source `sprezzature-audio-audit` measures against and the
#: same number the `audio` film puts on screen.
#:
#: It was 58 here until 2026-10-29, sourced to nothing, and it did not matter
#: what it was: `cues()` below is the only thing that reads it, and `cues()`
#: stopped being called on 2026-10-26 when the narration began writing its own
#: WebVTT. The cue text became the script line, unwrapped, and the shipped
#: tracks went to 90 characters.
#:
#: Measured the morning this was fixed: all 22 tracks failed the suite's own
#: auditor, 184 cues and 287 findings, 177 of them a line over budget. A limit
#: nobody applies is not a limit, and the loudest version of that defect is a
#: suite that ships the auditor, says the number on screen, and breaks it.
LINE_LIMIT = 42

#: Two display lines per cue, the same guide's ceiling. Past that a caption
#: covers the picture it is captioning.
MAX_LINES = 2

#: Characters a second to aim for, under the 17 the guide sets and the suite's
#: auditor enforces.
#:
#: Aiming *at* 17 does not work, and the reason is mechanical rather than
#: editorial. A cue's end time is written to the millisecond and truncated, so
#: a cue laid out to read at exactly 17.000 characters a second comes back from
#: the file at 17.0-and-a-bit and the audit calls it. Measured: targeting 17
#: left 23 of the 27 fast cues still failing; targeting 16 left none.
READING_TARGET_CPS = 16.0

#: Longest a cue may hold the screen, a millisecond under the guide's 7s.
#:
#: Same mechanism, same reason to stop short: one cue landed at exactly 7.000s
#: and `duration > max_seconds` is a strict comparison on a truncated number.
ON_SCREEN_MAX_SECONDS = 6.999



def stamp(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def split_line(text: str) -> tuple[str, str]:
    """Break one line in two, where the sense breaks, among the cuts that fit.

    Every gap between two words is priced by `semantic_breaks.gap_cost`, the
    rule the films and the site already break by: a sentence end or a comma
    first, then the gap before a word that opens a phrase (``and``, ``pour``,
    ``the``), then a complement, then two content words, and never the gap
    after an article or a preposition. Among the cuts whose two halves both
    fit :data:`LINE_LIMIT`, the cheapest wins, and balance only decides
    between cuts of the same price.

    History, because each rule here replaced one that looked fine:

    * Until 2026-10-29 the first comma won, fit or not, and the French call to
      action came back as 26 and 44 characters, the right half over budget.
    * From then until 2026-11-06 a cut without punctuation was chosen for
      balance alone, which is how 46 of the 360 breaks in the shipped tracks
      fell in the middle of a phrase: ``A blind reader cannot now hear the ⏎
      screen reader``, ``Une page qui laisse tomber un drapeau en ⏎ silence``.

    When no cut fits, the most balanced one is returned and
    :func:`over_budget` reports the cue: a sentence that needs three lines is
    a sentence to rewrite.
    """
    from semantic_breaks import NEVER, gap_cost

    words = text.split()
    if len(words) < 2:
        return text, ""

    def halves(k: int) -> tuple[str, str]:
        return " ".join(words[:k]), " ".join(words[k:])

    def price(k: int) -> int:
        c = gap_cost(words[k - 1], words[k])
        return 0 if c <= 1 else 1 if c == 2 else 2 if c <= 4 else 3 if c < NEVER else 4

    cuts = range(1, len(words))
    # A half under 12 characters reads as a stray word under a full line.
    fit = [
        k for k in cuts
        if max(len(h) for h in halves(k)) <= LINE_LIMIT and min(len(h) for h in halves(k)) >= 12
    ]
    if fit:
        k = min(fit, key=lambda k: (price(k), max(len(h) for h in halves(k))))
    else:
        k = min(cuts, key=lambda k: max(len(h) for h in halves(k)))
    return halves(k)


def wrap_cue(text: str) -> str:
    """One cue's text, broken onto at most :data:`MAX_LINES` display lines.

    A newline inside a cue is what WebVTT gives you for "break here": the
    timings do not move, the words do not change, and the player stops
    choosing its own break. That is the whole repair, and it is deliberately
    the smallest one that works: re-timing to split a long line into two cues
    would need the audio measured again, and the words are not the problem.

    Returns the text unchanged when it already fits, so a short line never
    grows a newline it did not need.

    Why this stops at two lines, when the brick does not
    -----------------------------------------------------
    `sprezzature_video.captions.split_to_fit` recuts until every piece is
    inside the budget, however many pieces that takes, and it exists because
    `split_line` below cuts exactly **once**: a line of 158 characters becomes
    two of 79, which is still over budget and looks repaired. Measured over
    the eleven films' 218 narration lines, lowering the limit alone moved the
    out-of-budget share from 41 % to 30 % and left the longest cue at 117.

    Here the ceiling is two display lines, because this path cannot make more
    cues: a third line would have to be timed, and the timings come from
    measured audio. So a sentence that needs three lines is not a wrapping
    problem at all, it is a sentence to rewrite, and :func:`over_budget` says
    so instead of hiding it under a break the guide forbids.
    """
    if len(text) <= LINE_LIMIT:
        return text
    a, b = split_line(text)
    if not b:
        return text
    return f"{a}\n{b}"


def over_budget(text: str) -> list[str]:
    """The display lines of a wrapped cue that are still too wide.

    Empty means the cue fits. A non-empty answer is a fact about the *script*,
    not about the wrapping: two breaks cannot rescue a sentence that needs
    three, and the repair is to write a shorter sentence.
    """
    lines = wrap_cue(text).split("\n")
    too_wide = [line for line in lines if len(line) > LINE_LIMIT]
    if len(lines) > MAX_LINES:
        too_wide.append(f"{len(lines)} display lines, over {MAX_LINES}")
    return too_wide


def split_to_cues(text: str) -> list[str]:
    """One spoken line as the fewest cues that each fit two lines of budget.

    Cut at the cheapest seam by `semantic_breaks.gap_cost` (a full stop, a
    comma, the word that opens a phrase), the most balanced among equals,
    and again inside a half that still does not fit.
    """
    from semantic_breaks import NEVER, gap_cost

    if not over_budget(text):
        return [text]
    words = text.split()
    if len(words) < 2:
        return [text]

    def price(k: int) -> int:
        c = gap_cost(words[k - 1], words[k])
        return 0 if c <= 1 else 1 if c == 2 else 2 if c <= 4 else 3 if c < NEVER else 4

    def halves(k: int) -> tuple[str, str]:
        return " ".join(words[:k]), " ".join(words[k:])

    k = min(range(1, len(words)), key=lambda k: (price(k), abs(len(halves(k)[0]) - len(halves(k)[1]))))
    left, right = halves(k)
    return split_to_cues(left) + split_to_cues(right)


def timed_cues(texts, times, names=None):
    """The film's cues: wrapped to the budget, and timed so they can be read.

    Replaces a `cues()` that nothing had called since 2026-10-26 — the dead
    function that held the unapplied :data:`LINE_LIMIT` this file's comments
    are about. It is written here rather than in the narration script because
    it is one rule with two callers: the script that narrates a film, and the
    script that re-emits an existing track without re-narrating it.

    Parameters
    ----------
    texts : list of str
        One narration line per cue, as spoken.
    times : list of tuple of float
        `(start, end)` of each line's speech, on the film's clock.

    Returns
    -------
    list of sprezzature_audio.Cue
        Ready for :func:`render_cues`.

    The two repairs this carries
    ----------------------------
    **The break survives the writer.** `wrap_cue` has put a newline at 42
    characters since 2026-10-29 and the shipped tracks still measured 90, for a
    reason no reading of this file could show: the cues went out through
    `speaker_helper.cues_to_vtt`, which collapses the payload with
    `" ".join(text.split())` — a line meant for "a blank line ends a cue"
    which also eats the single newline that *is* how WebVTT says "break
    here". Two lines of 39 and 41 came back as one of 81. So the cues are
    written by `sprezzature_audio`, which is the library whose auditor the
    films quote on screen: the writer and the audit now come from the same
    place, which is the property that was missing.

    **A cue may hold the screen into the pause that follows it.** The reading
    speed of a cue is its characters over its *on-screen* time, and on-screen
    time is free where the voice is silent. Extending a cue up to the next
    one's start — never over it, never past
    :data:`ON_SCREEN_MAX_SECONDS` — brought all 27 of the fast cues inside the
    ceiling with the audio untouched. That is the standard practice and it is
    also the only repair available here: shortening the sentence would mean
    speaking it again.

    The same bound fixes the opposite fault. A cue that had swallowed a long
    silence was holding the screen for 22.4 seconds — in `audio.fr`, on the
    line "90 caractères à l'écran, une demi-seconde. Personne ne lit ça."
    """
    from sprezzature_audio import Cue

    # A spoken line too long for one cue becomes several, cut where the sense
    # breaks and timed in proportion to their characters inside the line's
    # speech. Written 2026-11-07 for the French cuts, which run their
    # sentences longer than the English on purpose (a French voice that cut
    # where the English cuts read as a translation) and so shipped lines of
    # 64 characters in a 42 budget.
    #
    # The pieces share the line's whole window, not just its speech: inside a
    # sentence there is no pause to borrow, so a first half timed on the speech
    # alone went by at 18 characters a second. The window runs to the time the
    # line needs at the reading target, never into the next line.
    #
    # `names` carries identifiers already given, which is how a track re-read
    # piece by piece comes back byte for byte instead of renumbered.
    pieces: list[tuple[str, tuple[float, float], str]] = []
    for index, (text, (start, end)) in enumerate(zip(texts, times)):
        name = names[index] if names else str(index)
        parts = split_to_cues(" ".join(text.split()))
        total = sum(len(p) for p in parts) or 1
        if len(parts) > 1:
            window = start + (total + len(parts) - 1) / READING_TARGET_CPS
            if index + 1 < len(times):
                window = min(window, times[index + 1][0])
            end = max(end, window)
        at = start
        for k, part in enumerate(parts):
            span = (end - start) * len(part) / total
            pieces.append((part, (at, at + span), name if k == 0 else f"{name}.{k}"))
            at += span
    texts = [p[0] for p in pieces]
    times = [p[1] for p in pieces]
    names = [p[2] for p in pieces]

    out = []
    for index, (text, (start, end)) in enumerate(zip(texts, times)):
        wrapped = wrap_cue(" ".join(text.split()))
        characters = len(" ".join(wrapped.split()))
        # Never past the next cue: two cues on screen at once is a finding of
        # its own, and the player's answer to it is undefined.
        ceiling = start + ON_SCREEN_MAX_SECONDS
        if index + 1 < len(times):
            ceiling = min(ceiling, times[index + 1][0])
        readable = start + characters / READING_TARGET_CPS
        stop = min(max(end, readable), ceiling)
        out.append(
            Cue(
                start=start,
                end=max(stop, start + 0.001),
                text=wrapped,
                # The segment index, which is what lets the read-along
                # highlight a block without matching on its text; a line cut
                # into several cues numbers its pieces after the dot.
                identifier=names[index],
            )
        )
    return out


def render_cues(cue_list) -> str:
    """One film's WebVTT, through the suite's own writer.

    A thin wrapper so no caller has to remember *which* writer: see
    :func:`timed_cues` for what happened when the cues went out through a
    different library's.
    """
    from sprezzature_audio import write_vtt

    return write_vtt(cue_list)


def main() -> int:
    """Refuses to run, and says what replaced it.

    This used to write every ``web/video/*.vtt`` from the table above: it
    measured each line's WAV with ffprobe, split long lines at a list of
    separators, and laid the cues out itself. Since 2026-10-26 the cues come
    from ``narrate_films.py``, which asks ``sprezzature-audio`` for the
    reading and gets the audio and the timed track back together — one
    timeline, and a library that refuses a result whose timeline disagrees
    with its own audio.

    Left executable it would still work, and that is the danger: run after a
    narration it would overwrite correct cues with cues derived from a
    different arithmetic, and the only symptom would be captions drifting
    from the voice. So it stops, and names its successor.

    The table itself stays. It is the narration *text*, in both languages,
    and it is what ``narrate_films.py`` reads.
    """
    sys.stderr.write(
        "make_captions.py no longer writes the cues.\n"
        "The voice and its WebVTT come from sprezzature-audio together:\n"
        "    python3 narrate_films.py\n"
        "This file is still the narration text, which that script reads.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

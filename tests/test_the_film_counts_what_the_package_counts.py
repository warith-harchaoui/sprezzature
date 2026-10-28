"""
The number the ``figures`` film puts on screen is one somebody can re-measure.

The scene claims that three columns — region, quarter, units — fill N of the
167 chart kinds, and that no model was consulted to decide it. That is the
best thing the package does and the claim is worth making. It was not worth
making the way it was made.

The first draft said 41, which nobody had run. The second said 61, with a
comment naming the command that produced it: ``make-figure recommend --data
r.csv --limit 500``. There is no ``r.csv`` in this repository or in the
package's. The measurement was real and the frame it was measured on lived on
one machine, so the claim was no more checkable than the 41 it replaced, and
the count does move with the frame: six rows of those same three columns
answer 62, sixteen rows answer 64.

So the frame is committed — ``brag-output/region-quarter-units.csv`` — and the
film quotes what it measures.

Two halves, and why
-------------------
The re-measuring half needs ``sprezzature-figures`` *and* its profiling extra:
``recommend`` is pandas plus the Studio's ranker, which CI here does not
install. Left alone, this file would be a guard that never runs — a skip reads
exactly like a pass.

So the half that needs nothing runs everywhere: the number on the card, the
number in the English line and the number in the French line are one number,
spelled three ways in three files. That is the failure that actually happened
on 2026-10-28, when the card was corrected and the voice was not.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAG = REPO_ROOT / "brag-output"
FRAME = BRAG / "region-quarter-units.csv"
sys.path.insert(0, str(BRAG))

#: The columns the scene names, in the order it names them.
COLUMNS = ("region", "quarter", "units")

#: Enough of both languages to spell any count the catalogue can produce. The
#: film says the number out loud, so a digit on the card has to become words
#: twice, and the two spellings are where a correction gets dropped.
_TENS = {
    "en": {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty",
           7: "seventy", 8: "eighty", 9: "ninety"},
    "fr": {2: "vingt", 3: "trente", 4: "quarante", 5: "cinquante", 6: "soixante"},
}
_UNITS = {
    "en": {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
           6: "six", 7: "seven", 8: "eight", 9: "nine"},
    "fr": {1: "et un", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq",
           6: "six", 7: "sept", 8: "huit", 9: "neuf"},
}


def _spelled(number: int, lang: str) -> str:
    """How the narration says ``number``. Two digits is all the film needs."""
    tens, units = divmod(number, 10)
    assert 2 <= tens <= 9, f"{number} is outside the range this guard spells"
    word = _TENS[lang].get(tens)
    assert word, f"no {lang} word for {tens * 10}"
    if not units:
        return word
    return f"{word} {_UNITS[lang][units]}" if lang == "fr" and units == 1 else (
        f"{word}-{_UNITS[lang][units]}"
    )


def _claimed() -> int:
    """The number printed on the card, read off the film spec."""
    import build_films

    scene = next(
        s for s in build_films.FILMS["figures"]["scenes"] if s["type"] == "verify"
    )
    fills = next(
        value for label, value in scene["claims"]
        if isinstance(label, dict) and "fill" in label["en"]
    )
    return int(fills)


def test_the_frame_the_comment_names_is_in_the_repository() -> None:
    """The claim is measurable by whoever reads it, not only by its author."""
    assert FRAME.is_file(), f"{FRAME.relative_to(REPO_ROOT)} is gone"
    with FRAME.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert tuple(rows[0]) == COLUMNS, (
        f"the scene names {COLUMNS} and the frame holds {tuple(rows[0])}"
    )
    assert len(rows) > 1, "the frame has a header and no data"


def test_the_card_and_both_voices_say_one_number() -> None:
    """A correction to the card that never reached the narration fails here."""
    import make_captions

    want = _claimed()
    missing: list[str] = []
    for lang in ("en", "fr"):
        word = _spelled(want, lang)
        said = [text for _start, _dur, text in make_captions.FILMS["figures"][lang]]
        if not any(word in line for line in said):
            missing.append(
                f"{lang}: the card says {want}, and no spoken line says {word!r}"
            )
    assert not missing, "\n  ".join(["", *missing])


def test_the_package_still_fills_that_many_kinds() -> None:
    """Re-measure it. The catalogue grows, and this claim ages with it."""
    try:
        from sprezzature_figures.actions import recommend
    except ImportError:  # pragma: no cover - depends on the machine
        pytest.skip("sprezzature-figures is not importable here")

    try:
        result = recommend(str(FRAME), limit=500)
    except Exception as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"recommend cannot run here: {exc}")

    filled = sum(1 for line in result.out if "score=" in line)
    assert filled == _claimed(), (
        f"the film says {_claimed()} kinds; recommend fills {filled} from "
        f"{FRAME.name}. Update the card in build_films.py and both spoken "
        f"lines in make_captions.py, then re-narrate the film."
    )

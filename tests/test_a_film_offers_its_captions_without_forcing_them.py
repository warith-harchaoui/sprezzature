"""
Every film player declares a caption track, and none of them switches it on.

The two halves of one rule
--------------------------
A ``<track kind="captions">`` that is absent fails a reader who needs it. A
``<track>`` carrying ``default`` fails everybody else, and the second failure
is the one that looks like diligence, which is why it survived four rewrites
of these pages.

``default`` does not mean "use this track when captions are asked for". The
browser reads it as *show this now*, so the words appear over the picture
whether or not anybody wanted them. For these films that is wrong twice: each
one already carries its sentence on screen, set in the film's own type at the
size it was composed for, so a forced track lays a second copy of the same
words over the first in the player's font — and whether to read instead of
listen is a choice a viewer makes once in their own player, which a page has
no standing to override.

So both halves are checked here, because fixing one of them is how the other
breaks. A page that drops the attribute and the track together passes a test
that only looks for ``default``.

Where the pages come from, and why that is not enough
-----------------------------------------------------
Twenty-two of the twenty-four players are written by
``scripts/build_films_page.py``; the other two are the hand-maintained home
pages, ``web/index.html`` and ``web/fr/index.html``. Checking the generator
would therefore pass while the two that are edited by hand went on forcing
captions — which is exactly the state this repository was in. The check reads
the HTML that ships.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

#: A ``<video>`` element with everything up to its closing tag, so a track can
#: be attributed to the player it belongs to rather than to the page.
VIDEO = re.compile(r"<video\b[^>]*>(.*?)</video>", re.S | re.I)

#: One caption track, with its attributes kept for inspection.
TRACK = re.compile(r"<track\b([^>]*)>", re.I)


def _pages() -> list[Path]:
    """Every shipped page, English and French."""
    return sorted(WEB.glob("*.html")) + sorted((WEB / "fr").glob("*.html"))


def _players() -> list[tuple[Path, int, str]]:
    """Each ``<video>`` on the site: its page, its position, its innards."""
    out: list[tuple[Path, int, str]] = []
    for page in _pages():
        html = page.read_text(encoding="utf-8")
        for n, match in enumerate(VIDEO.finditer(html), 1):
            out.append((page, n, match.group(1)))
    return out


def test_the_site_still_has_the_film_players_this_is_about() -> None:
    """A guard whose subject has vanished passes for the wrong reason.

    The site carried twenty-four players when this was written. The number is
    not pinned — films come and go — but zero of them means the pages were
    restructured and the two checks below became vacuously true.
    """
    players = _players()
    assert players, (
        f"no <video> element anywhere under {WEB}. Either the players moved, "
        f"or this file is now checking nothing."
    )


def test_every_film_player_declares_a_caption_track() -> None:
    """The accommodation is present, on every player."""
    missing = [
        f"{page.relative_to(ROOT)} player {n}"
        for page, n, inner in _players()
        if not any(
            "captions" in attrs or "subtitles" in attrs
            for attrs in TRACK.findall(inner)
        )
    ]
    assert not missing, (
        f"{len(missing)} player(s) ship no caption track. The cues exist — "
        f"`narrate_films.py` writes one WebVTT per film per language — so an "
        f"absent track is a player that forgot to name it:\n  "
        + "\n  ".join(missing)
    )


def test_no_film_player_switches_its_captions_on() -> None:
    """Declared, and left to the viewer.

    ``default`` is the whole subject. It reads as a courtesy and behaves as an
    override: the track paints over the picture for every visitor, including
    the ones who have already told their browser they do not want it.
    """
    forced = [
        f"{page.relative_to(ROOT)} player {n}: <track{attrs}>"
        for page, n, inner in _players()
        for attrs in TRACK.findall(inner)
        if re.search(r"\bdefault\b", attrs, re.I)
    ]
    assert not forced, (
        f"{len(forced)} caption track(s) carry `default`, which shows them "
        f"unasked. Drop the attribute: the track stays declared, stays in the "
        f"player's subtitle menu, and stays one click away.\n  "
        + "\n  ".join(forced)
    )

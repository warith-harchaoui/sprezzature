"""
Every film the site asks for is a film ``install_films.py`` writes.

The defect this is shaped after
-------------------------------
``web/index.html`` pointed at ``video/sprezzature.mp4`` and
``video/sprezzature.jpg`` — names with no language in them, which the
installer stopped writing on 2026-10-26 when each film became two films that
do not mix. The files were still on the server from the deploy before, so the
home page played a thirteen-second cut of a film that had since been
re-written twice, and nothing local could tell: ``web/video/`` is gitignored,
so the page worked in a browser pointed at the live site and 404ed in a
clone, and neither of those is a test anybody was running.

The same page carried two ``<track>`` elements on one video, English and
French. The films page documents at length why that is wrong — a French film
is French in its subtitles because they transcribe its voice rather than
translate it, and offering both means one of them disagrees with every word
on screen with no way for a reader to tell which.

What this checks
----------------
Not that the MP4 exists on this disk: ``web/video/`` is gitignored and a CI
clone has none of it, so that test would be skipped exactly where it matters.
It checks the *name*, against the naming rule ``install_films.py`` encodes —
which is the thing that drifted.

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

WEB = ROOT / "web"

#: Anything under video/ that a page points at, however it spells the path.
#: The extension is part of the pattern on purpose: without it this also
#: matched ``content="video/mp4"``, the Open Graph MIME type, and reported
#: the string "mp4" as a film nobody installs.
REFERENCE = re.compile(
    r'(?:src|href|content|poster)="[^"]*?video/([^"/]+\.(?:mp4|jpg|vtt))"'
)

#: The names the installer writes: ``<film>.<lang>[.<canvas>].<ext>`` for the
#: media, ``<film>.<lang>.vtt`` for the captions.
WELL_FORMED = re.compile(
    r"^(?P<film>[a-z-]+)\.(?P<lang>en|fr)"
    r"(?:\.(?P<fmt>portrait|square))?"
    r"\.(?P<ext>mp4|jpg|vtt)$"
)


def _installed() -> set[str]:
    """Every filename ``install_films.main`` would produce."""
    import install_films

    names = set()
    for film in install_films.POSTER_AT:
        for lang in install_films.LANGS:
            names.add(f"{film}.{lang}.vtt")
            for suffix in install_films.FORMATS.values():
                names.add(f"{film}.{lang}{suffix}.mp4")
                names.add(f"{film}.{lang}{suffix}.jpg")
    return names


def _pages() -> list[Path]:
    return sorted(p for p in WEB.rglob("*.html") if "kits" not in p.parts)


def test_no_page_asks_for_a_film_the_installer_never_writes() -> None:
    """Across every page of the site, in both languages."""
    installed = _installed()
    orphans: list[str] = []
    for page in _pages():
        for name in sorted(set(REFERENCE.findall(page.read_text(encoding="utf-8")))):
            if name in installed:
                continue
            why = ("no language in the name — every film is two films since "
                   "2026-10-26" if not WELL_FORMED.match(name)
                   else "not a film install_films.py knows about")
            orphans.append(f"{page.relative_to(WEB)} -> video/{name} ({why})")
    assert not orphans, (
        f"{len(orphans)} reference(s) point at a film nobody installs:\n  "
        + "\n  ".join(orphans)
    )


def test_no_player_offers_captions_in_a_language_the_film_is_not_in() -> None:
    """One film, one language, end to end — including its subtitles.

    A caption track that translates rather than transcribes is worse than no
    caption track, because a reader has no way to tell which of the two is
    wrong: the words on screen, or the words under them.
    """
    bad: list[str] = []
    for page in _pages():
        html = page.read_text(encoding="utf-8")
        for player in re.findall(r"<video\b.*?</video>", html, re.S):
            tracks = re.findall(r'<track[^>]*srclang="([a-z]+)"', player)
            if len(tracks) > 1:
                source = re.search(r'<source[^>]*src="[^"]*?video/([^"]+)"', player)
                bad.append(
                    f"{page.relative_to(WEB)}: {source.group(1) if source else '?'} "
                    f"offers {tracks}"
                )
    assert not bad, (
        "a player offers more than one caption language:\n  " + "\n  ".join(bad)
    )

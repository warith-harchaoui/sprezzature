"""
A French film is French on screen, and does not show an English asset twice.

The rule, stated 2026-10-26: a French film is French throughout — French
words, French voice, French subtitles — and an English film is English
throughout. The two do not mix. A caption track that translates rather than
transcribes is worse than none, because a reader has no way to tell which half
is wrong.

Half of that rule is already enforced by construction. ``films_fr.translate``
raises on any string with neither a translation nor an exemption, so a new
line cannot reach the French cut in English: the build stops and names it.

The half that *can* rot silently is the pictures. A figure, a map or a
screenshot carries its own words — an axis label, a map title, a form field —
and swapping the caption above it does nothing to those.

Switching is automatic: ``films_fr.french_asset`` takes the French twin as
soon as ``restore_assets.TRACKED`` declares one, so "it exists and the film
ignores it" is not a state this repository can reach. The ledger and not the
cache, because ``_assets/`` is gitignored — keying on what happens to be on
this disk made the French films depend on local state, and made this very
test pass here and fail in CI. What it *can* reach is the opposite — a new
asset added to a film, with no French version, nobody noticing, and a picture
full of English words sitting in a French film between two correct captions.

So the gaps are written down, with reasons, in
``films_fr.ENGLISH_IN_FRENCH_CUTS``, and pinned from both sides. Today they
are the six situation plates (titles baked in by sprezzature-maps), the five
colour-vision frames (rendered from the English figure), and the two
``make-figure`` captures (an English command's own help text). An unlisted
English asset fails; a listed one whose French twin has landed fails too,
because the film already switched and the line is stale. The list only
shrinks on purpose.

The other direction is checked too, and is the cheaper mistake: an **English**
film must never reach for a ``fr/`` asset. That one would be a copy-paste,
and it would look fine in every frame nobody opened.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "brag-output"))

ASSETS: Path = REPO_ROOT / "brag-output" / "_assets"

#: Keys in a scene that name a file under ``_assets/``.
ASSET_KEYS = ("fig", "gray", "base", "src")


def _assets_of(scene: dict) -> list[str]:
    """Every asset path one scene references."""
    out = list(scene.get("images", ()))
    out += [scene[k] for k in ASSET_KEYS if scene.get(k)]
    # A cvd scene's stages carry their own frame as the third element.
    out += [st[2] for st in scene.get("stages", ()) if len(st) > 2]
    return out


def _french_twin(src: str) -> str | None:
    """Where this asset's French version would live, if the shape allows one."""
    import films_fr

    twin = films_fr.localise_asset(src)
    return None if twin == src else twin


def test_every_english_asset_in_a_french_cut_is_a_written_down_gap() -> None:
    """A French cut shows English pictures only where that is recorded.

    ``films_fr.translate`` already switches to a French asset the moment one
    exists, so "it exists and the film ignores it" cannot happen. What can is
    the opposite: a *new* asset added to a film, with no French version and
    nobody noticing — a picture full of English words sliding into a French
    film between two correct captions.

    So the gaps are a list with reasons, and this pins it from both sides.
    An unlisted English asset fails. A listed one that has since gained a
    French twin fails too, because the film is now using the twin and the
    line is stale. The list only shrinks on purpose.
    """
    import build_films
    import films_fr

    gaps = films_fr.ENGLISH_IN_FRENCH_CUTS
    unlisted: list[str] = []
    seen: set[str] = set()
    for film, lang in build_films.cuts():
        if lang == "en":
            continue
        spec = build_films.in_language(build_films.FILMS[film], lang, film)
        for i, scene in enumerate(spec["scenes"]):
            for src in _assets_of(scene):
                if "/fr/" in src:
                    continue
                seen.add(src)
                if src not in gaps:
                    unlisted.append(f"{film}.fr scene {i}: {src}")

    assert not unlisted, (
        "English assets in a French cut that nobody wrote down:\n  "
        + "\n  ".join(sorted(set(unlisted)))
        + "\n\nEither produce the French version (the films pick it up "
          "automatically) or add it to films_fr.ENGLISH_IN_FRENCH_CUTS with "
          "the reason and what would close it."
    )

    stale = sorted(set(gaps) - seen)
    assert not stale, (
        "these are listed as English-in-French and are no longer used that "
        "way — the French twin landed and the films switched:\n  "
        + "\n  ".join(stale)
        + "\nRemove them from films_fr.ENGLISH_IN_FRENCH_CUTS."
    )


def test_an_english_cut_never_reaches_for_a_french_asset() -> None:
    """The mirror mistake, which no frame would make obvious."""
    import build_films

    wrong: list[str] = []
    for film, lang in build_films.cuts():
        if lang != "en":
            continue
        for i, scene in enumerate(
            build_films.in_language(build_films.FILMS[film], lang, film)["scenes"]
        ):
            for src in _assets_of(scene):
                if "/fr/" in src:
                    wrong.append(f"{film}.en scene {i}: {src!r}")
    assert not wrong, (
        "an English cut references a French asset:\n  " + "\n  ".join(wrong)
    )


def test_every_asset_a_film_names_is_actually_there() -> None:
    """Both cuts, every scene. A missing asset is a render that dies at frame 1."""
    import build_films

    missing: list[str] = []
    for film, lang in build_films.cuts():
        spec = build_films.in_language(build_films.FILMS[film], lang, film)
        for i, scene in enumerate(spec["scenes"]):
            for src in _assets_of(scene):
                if not (ASSETS / src).is_file():
                    missing.append(f"{film}.{lang} scene {i}: {src}")
    if not ASSETS.is_dir():
        pytest.skip(
            "no _assets cache here — it is gitignored, so a clean checkout "
            "and CI have none of it. Run brag-output/restore_assets.py --fix "
            "where the films are built. The two tests above need no cache."
        )
    assert not missing, (
        "films name assets that are not in the tree:\n  " + "\n  ".join(missing)
    )

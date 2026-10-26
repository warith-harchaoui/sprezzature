#!/usr/bin/env python3
"""
Put the rendered films where the site expects them, with their posters.

Six files per film, and they travel together: ``<film>.en.mp4``,
``<film>.fr.mp4``, a poster for each, and the two caption tracks the voices
already wrote. Drop one ``.vtt`` and the player loses its captions silently;
drop one ``.jpg`` and the page shows a black rectangle until somebody presses
play. ``web/video/`` is gitignored, so nothing here is recoverable from a
clone and ``git status`` will never mention it.

The posters are cut by ``sprezzature-video poster`` — the suite's own tool, on
the suite's own films — at a time chosen per film rather than a shared one.
0.0 s is a fade-in and 30.0 s is whatever happens to be on screen; what a
poster wants is the moment the film is *about*, which is a different second in
each of them and is written down below.

Usage
-----
    python3 install_films.py            # every film, both languages
    python3 install_films.py maps       # one of them

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
FILMS_DIR = ROOT / "films"
VIDEO = ROOT.parent / "web" / "video"

#: The second each film is best represented by. Chosen by looking, not by a
#: rule: the suite film is its grid of four real outputs, maps is the four
#: situation plates, ui is the sentence about what a hardcoded string costs.
POSTER_AT: dict[str, float] = {
    "sprezzature": 19.5,   # the four real outputs, all four on screen
    "ui": 28.0,            # "It costs a week the day somebody needs a second language."
    "cli-gui": 11.0,       # both captures of the generated form
    "publish": 11.5,       # the nine tools, all nine revealed
    "accessibility": 10.5, # the three findings the source can prove
    "colors": 26.5,        # the grayscale simulation, mid-wipe
    "audio": 19.5,         # the models, named
    "ux-laws": 19.5,       # the eight laws the auditor checks
    "figures": 10.5,       # six real figures from the gallery
    "maps": 10.5,          # four situation plates — the prettiest frame in the set
    "video": 28.5,         # TRACKED / DERIVED / SOLE
}

LANGS = ("en", "fr")


def newest_render(project: str) -> pathlib.Path | None:
    """The most recent MP4 a project has produced, if any."""
    renders = FILMS_DIR / project / "renders"
    mp4s = sorted(renders.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    return mp4s[-1] if mp4s else None


def project_for(film: str, lang: str) -> str:
    """Mirrors ``build_films.project_name`` for the landscape cut."""
    return f"{film}-landscape" if lang == "en" else f"{film}-{lang}-landscape"


def install(film: str, lang: str) -> list[str]:
    """Copy one cut and its poster into web/video. Returns problems."""
    src = newest_render(project_for(film, lang))
    if src is None:
        return [f"  {film}.{lang}: not rendered — {project_for(film, lang)} has no MP4"]

    VIDEO.mkdir(parents=True, exist_ok=True)
    mp4 = VIDEO / f"{film}.{lang}.mp4"
    jpg = VIDEO / f"{film}.{lang}.jpg"
    vtt = VIDEO / f"{film}.{lang}.vtt"
    shutil.copy2(src, mp4)

    if not vtt.is_file():
        return [
            f"  {film}.{lang}: {vtt.name} is missing. The cues come from the "
            f"narration — run `python3 narrate_films.py {film} --lang {lang}`."
        ]

    at = POSTER_AT.get(film)
    if at is None:
        return [f"  {film}: no poster time. Add one to POSTER_AT, by looking."]
    done = subprocess.run(
        ["sprezzature-video", "poster", str(mp4), "--out", str(jpg), "--at", str(at)],
        capture_output=True, text=True, check=False,
    )
    if done.returncode != 0 or not jpg.is_file():
        return [
            f"  {film}.{lang}: poster failed "
            f"({(done.stderr or done.stdout).strip()[:120]})"
        ]
    print(f"  {film}.{lang}: {mp4.stat().st_size // 1_000_000} MB, poster at {at}s")
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("films", nargs="*", help="Film keys; default is all of them.")
    args = parser.parse_args()

    if shutil.which("sprezzature-video") is None:
        sys.stderr.write(
            "sprezzature-video is not on PATH; it cuts the posters.\n"
            "    pip install sprezzature-video\n"
        )
        return 2

    wanted = args.films or sorted(POSTER_AT)
    problems: list[str] = []
    for film in wanted:
        for lang in LANGS:
            problems += install(film, lang)

    if problems:
        sys.stderr.write("\n".join(problems) + "\n")
        return 1
    print(f"{len(wanted)} film(s) x {len(LANGS)} language(s) in {VIDEO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

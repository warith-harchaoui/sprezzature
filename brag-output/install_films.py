#!/usr/bin/env python3
"""
Put the rendered films where the site expects them, with their posters.

Three canvases per film per language, and the pieces of one cut travel
together: ``<film>.<lang>[.<format>].mp4``, a poster beside it, and the one
caption track the language shares across all three. Drop a ``.vtt`` and the
player loses its captions silently; drop a ``.jpg`` and the page shows a
black rectangle until somebody presses play. ``web/video/`` is gitignored, so
nothing here is recoverable from a clone and ``git status`` will never mention
it.

Why landscape has no suffix
---------------------------
``sprezzature.en.mp4`` is the landscape cut and keeps that name, because the
home page, the Open Graph tags, the sitemap and the feed all point at it by
that name. Renaming it to ``.landscape.mp4`` would be a correctness change
that breaks five files to gain a word. The other two carry their canvas:
``sprezzature.en.portrait.mp4``, ``sprezzature.en.square.mp4``.

The posters
-----------
Cut by ``sprezzature-video poster`` -- the suite's own tool, on the suite's
own films -- at a time chosen per film rather than a shared one. 0.0 s is the
opening sentence and 30.0 s is whatever happens to be on screen; what a poster
wants is the moment the film is *about*, which is a different second in each
of them and is written down below. The three canvases are frame-synced, so one
second serves all three.

Usage
-----
    python3 install_films.py                 # every film, language, canvas
    python3 install_films.py maps            # one of them
    python3 install_films.py --only landscape

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

#: Canvas → the suffix it carries in web/video. Landscape's empty suffix is
#: the whole reason this is a mapping and not a list.
FORMATS: dict[str, str] = {"landscape": "", "portrait": ".portrait",
                           "square": ".square"}


def newest_render(project: str) -> pathlib.Path | None:
    """The most recent MP4 a project has produced, if any."""
    renders = FILMS_DIR / project / "renders"
    mp4s = sorted(renders.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    return mp4s[-1] if mp4s else None


def project_for(film: str, lang: str, fmt: str) -> str:
    """Mirrors ``build_films.project_name``."""
    return f"{film}-{fmt}" if lang == "en" else f"{film}-{lang}-{fmt}"


def install(film: str, lang: str, fmt: str) -> list[str]:
    """Copy one cut and its poster into web/video. Returns problems."""
    project = project_for(film, lang, fmt)
    src = newest_render(project)
    if src is None:
        return [f"  {film}.{lang}.{fmt}: not rendered — {project} has no MP4"]

    at = POSTER_AT.get(film)
    if at is None:
        return [f"  {film}: no poster time. Add one to POSTER_AT, by looking."]

    VIDEO.mkdir(parents=True, exist_ok=True)
    suffix = FORMATS[fmt]
    mp4 = VIDEO / f"{film}.{lang}{suffix}.mp4"
    jpg = VIDEO / f"{film}.{lang}{suffix}.jpg"
    vtt = VIDEO / f"{film}.{lang}.vtt"
    shutil.copy2(src, mp4)

    # One caption track per language, shared by all three canvases: the three
    # are the same film laid out differently, so a second copy could only ever
    # be the first one going stale.
    if not vtt.is_file():
        return [
            f"  {film}.{lang}: {vtt.name} is missing. The cues come from the "
            f"narration — run `python3 narrate_films.py {film} --lang {lang}`."
        ]

    done = subprocess.run(
        ["sprezzature-video", "poster", str(mp4), "--out", str(jpg), "--at", str(at)],
        capture_output=True, text=True, check=False,
    )
    if done.returncode != 0 or not jpg.is_file():
        return [
            f"  {film}.{lang}.{fmt}: poster failed "
            f"({(done.stderr or done.stdout).strip()[:120]})"
        ]
    print(f"  {mp4.name}: {mp4.stat().st_size // 1_000_000} MB, poster at {at}s")
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("films", nargs="*", help="Film keys; default is all of them.")
    parser.add_argument(
        "--only", action="append", choices=sorted(FORMATS),
        help="Canvas to install; repeatable. Default: all three.",
    )
    parser.add_argument(
        "--lang", action="append", choices=LANGS,
        help="Language to install; repeatable. Default: both.",
    )
    args = parser.parse_args()

    if shutil.which("sprezzature-video") is None:
        sys.stderr.write(
            "sprezzature-video is not on PATH; it cuts the posters.\n"
            "    pip install sprezzature-video\n"
        )
        return 2

    wanted = args.films or sorted(POSTER_AT)
    formats = args.only or list(FORMATS)
    langs = args.lang or list(LANGS)

    problems: list[str] = []
    for film in wanted:
        for lang in langs:
            for fmt in formats:
                problems += install(film, lang, fmt)

    if problems:
        sys.stderr.write("\n".join(problems) + "\n")
        return 1
    n = len(wanted) * len(langs) * len(formats)
    mb = sum(f.stat().st_size for f in VIDEO.glob("*.mp4")) // 1_000_000
    print(f"{n} cut(s) in {VIDEO} — {mb} MB of MP4 in total")
    return 0


if __name__ == "__main__":
    sys.exit(main())

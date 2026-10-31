#!/usr/bin/env python3
"""Check — and with --fix, rebuild — _assets/, the asset tree the films render from.

git does not track _assets/: a WAV and an MP3 do not delta-compress, so none of
it belongs in a clone. The .gitignore used to claim everything needed to rebuild
the films from nothing stayed tracked. That was not true, and this script is the
audit that says exactly how far it goes.

Three classes, and the distinction is the whole point:

  A. copies of files git DOES track (fonts, figures, maps) — restored here, and
     verified byte-for-byte against their source rather than assumed.
  B. output of a tool that is still on the machine (Kokoro narration, the colour
     vision simulations, the resized logo, the cli-gui form) — regenerated. The narration comes
     back byte-identical: Kokoro is deterministic for a given text, voice and
     speed, verified against vo-global-3.wav on hyperframes 0.8.60.
  C. neither: a licensed music track, three sound effects, a pinned GSAP build,
     three screen captures of another project's GUI, a logo. Nine files. They
     exist in exactly one place, and if that place is a single disk the films
     are one disk failure from unrenderable. Pass --seed to restore them from
     an off-repo archive.

Run from brag-output/:
    python3 restore_assets.py                    # report only
    python3 restore_assets.py --fix              # restore A and B
    python3 restore_assets.py --fix --seed DIR   # also restore C from an archive
    python3 restore_assets.py --into /tmp/probe  # rebuild elsewhere, touch nothing
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent

# ---------------------------------------------------------------------------
# A. Copies of tracked files. Keys are paths inside _assets/, values are paths
#    inside the monorepo. Verified by SHA-256 on 2026-10-02: every pair matched.
# ---------------------------------------------------------------------------
FIGURES = ("alluvial", "bar-grouped", "bellcurve", "calendar-heatmap", "candlestick",
           "chord", "choropleth", "circle-packing", "clustermap", "corr-matrix",
           "map-flow", "sankey")

TRACKED: dict[str, str] = {
    "fonts/Roboto-Variable.woff2": "web/fonts/roboto/Roboto-Variable.woff2",
    "fonts/Roboto-Serif-Variable.woff2": "web/fonts/roboto-serif/Roboto-Serif-Variable.woff2",
    "fonts/Roboto-Mono-Variable.woff2": "web/fonts/roboto-mono/Roboto-Mono-Variable.woff2",
    # Despite the name this is not a desaturated copy: it is byte-identical to
    # bar-grouped.svg. The grey pass happens at render time, in the composition.
    "figures/bar-grouped-gray.svg": "web/img/figures/bar-grouped.svg",
    "figures/kde2d-contour.png": "web/img/figures/kde2d-contour.png",
    "figures/surface3d.png": "web/img/figures/surface3d.png",
    # The films' only two raster maps, and the one figure that is really a map.
    # NOTE: sprezzature-maps is actively changing how situation plates render.
    # When its work lands and web/img/maps/ is regenerated, these two change
    # with it and the four films stop matching the gallery they quote.
    "figures/situation-western-europe.png": "web/img/maps/situation-western-europe.png",
    "maps/choropleth-diverging.svg": "web/img/maps/choropleth-diverging.svg",
    "maps/choropleth-sequential.svg": "web/img/maps/choropleth-sequential.svg",
}

# The maps film shows situation plates and nothing else: of the three kinds the
# package draws, these are the ones worth a minute of somebody's attention.
# Six of the nine in the gallery, chosen by looking at all nine side by side --
# four reference plates, where the geography is the whole point, and two
# areas-of-control plates, which is what the kind is actually for.
#
# Left out, and why: `drc` is a 1300x2227 portrait plate that shrinks to
# nothing in a landscape frame; `libya` reads flat next to the others; `sudan`
# is good but says the same thing `ukraine` already says better.
SITUATION_PLATES = (
    "himalaya",        # eight kilometres of relief, and the rivers that leave it
    "iberia",          # relief, the great rivers, and the Meseta
    "switzerland",     # terrain, lakes and rivers, no thematic layer at all
    "western-europe",  # the physical base the thematic maps are drawn on
    "ukraine",         # areas of control, wide enough to read at speed
    "syria",           # four actors, and a legend that has to carry them
)
TRACKED.update({
    f"maps/situation-{n}.png": f"web/img/maps/situation-{n}.png"
    for n in SITUATION_PLATES
})
TRACKED.update({f"figures/{n}.svg": f"web/img/figures/{n}.svg" for n in FIGURES})

# The same figures, in French. A French film is French throughout, and a
# chart whose axis says "Quarter" under a caption that says "trimestre" is
# the mixture that rule forbids. `web/tools/localize_figures.py` already
# writes these for the gallery, from one `"English": "Français"` map — so the
# films take the gallery's French rather than translating a second time.
#
# `bar-grouped-gray` is the same file as `bar-grouped` (the grey pass happens
# at render time, in the composition), so its French twin is the French
# `bar-grouped`.
TRACKED.update({f"figures/fr/{n}.svg": f"web/img/figures/fr/{n}.svg" for n in FIGURES})
TRACKED["figures/fr/bar-grouped-gray.svg"] = "web/img/figures/fr/bar-grouped.svg"

# The accumulation plate, in both languages, generated rather than copied:
# `make_density.py --language` produces it, and until 2026-10-27 that flag was
# accepted by every map generator and honoured by none. It is a DERIVED asset
# for that reason, with the command that makes it written down next to it.
DERIVED_MAPS = {
    "maps/density.svg": ("en", "the field the maps film ends on"),
    "maps/fr/density.svg": ("fr", "the same plate, in French"),
}

# Plates a sibling repository already ships, copied rather than generated.
#
# Added 2026-10-29 with the sixth beat, the finest example each package can
# show. Six films had carried no picture at all, justified in FILM-SHAPES.md
# as "films about text, and a stock photograph would be a lie" — true about
# photographs, and the wrong conclusion for a suite that draws for a living.
# A picture the package itself produced is evidence, not decoration.
#
# A class of its own because the source is outside this repository: the value
# is the sibling path, so the file is restorable from clones without anybody
# remembering which brick drew it, and a `--fix` can fetch it.
DERIVED_SIBLINGS: dict[str, tuple[str, str]] = {
    "figures/audio-how-it-works.svg": (
        "sprezzature-audio/assets/how-it-works.svg",
        "the two lanes of the audio brick, which is the shape of its film",
    ),
    "figures/fr/audio-how-it-works.svg": (
        "sprezzature-audio/assets/comment-ca-marche.svg",
        "the same plate, which that brick already ships in French",
    ),
}

# ---------------------------------------------------------------------------
# B. Reproducible by a tool. The narration text lives in make_captions.py,
#    which git tracks, and `narrate_films.py` turns it into both the voice and
#    the WebVTT in one call — so the script that writes the subtitles and the
#    script that writes the voice are now the same script.
#
#    `VO_PREFIX` used to live here: a film key to a short stem, because every
#    line was its own file (`vo-a11y-3.wav`) and the stems had to be unique and
#    typable. A film's voice is one track now (`vo-accessibility.fr.wav`), so
#    there is nothing left to abbreviate, and the table went with the scheme.
# ---------------------------------------------------------------------------

CVD = ("00-original.png", "01-protanopia.png", "02-deuteranopia.png",
       "03-tritanopia.png", "04-grayscale.png")

# ---------------------------------------------------------------------------
# C. Nowhere else. Each line says why, because "missing" is useless on its own.
# ---------------------------------------------------------------------------
SEED_ONLY: dict[str, str] = {
    "music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3":
        "licensed track (ende.app). build_films.py's 42-value BEATS grid is "
        "measured off this file at 109.96 BPM — another track re-times all 15 films",
    "sfx/impact/impactBell_heavy_000.ogg": "registry item; `hyperframes add` refetches over the network",
    "sfx/impact/impactSoft_medium_001.ogg": "idem",
    "sfx/interface/drop_001.ogg": "idem",
    "vendor/gsap.min.js": "CDN-fetchable, but the pinned version is written down nowhere",
    "music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json":
        "derived from the MP3 by `npx hyperframes beats <project>`",
    "music/audio-data.js":
        "derived from the MP3 by hyperframes-creative/scripts/extract-audio-data.py, "
        "3 bands at 30fps, wrapped as window.AUDIO_DATA",
}


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def narration() -> dict[str, str]:
    """VO stem -> the lines it speaks, for every cut that has a voice.

    One entry per (film, language), not per line: the voice is a single track
    now. The value is the whole reading joined, which is what makes a stale
    WAV detectable — change a line in `make_captions.py` and this string
    changes with it.
    """
    sys.path.insert(0, str(ROOT))
    from make_captions import FILMS

    return {
        f"{film}.{lang}": " ".join(text for _s, _d, text in langs[lang])
        for film, langs in FILMS.items()
        if len(langs["en"]) >= 8
        for lang in ("en", "fr")
    }


def restore_tracked(dest: pathlib.Path, fix: bool) -> list[str]:
    """Class A. Copy, then prove the copy equals its tracked source."""
    notes = []
    for rel, src_rel in sorted(TRACKED.items()):
        src, out = REPO / src_rel, dest / rel
        if not src.exists():
            notes.append(f"  MISSING SOURCE  {rel}  <- {src_rel} is not in the repo")
            continue
        if out.exists():
            if sha(out) == sha(src):
                continue
            # Both exist and differ. Never silently overwrite: on this tree that
            # means the gallery was regenerated after the films were cut, and a
            # film now quotes an image the site no longer ships. Say so.
            notes.append(f"  DIVERGED         {rel}\n"
                         f"                     differs from {src_rel}; the film and "
                         f"the gallery no longer show the same image. Decide, do not guess.")
            continue
        if not fix:
            notes.append(f"  would restore    {rel}  <- {src_rel}")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        if sha(out) != sha(src):
            notes.append(f"  COPY MISMATCH    {rel}")
        else:
            notes.append(f"  restored         {rel}  <- {src_rel}")
    return notes


def restore_voice(dest: pathlib.Path, fix: bool) -> list[str]:
    """Class B. Re-narrate the films through the suite's own voice.

    This used to call ``npx hyperframes tts`` once per line and keep one WAV
    per line. Since 2026-10-26 a film's voice is a single track, produced by
    ``narrate_films.py`` through ``sprezzature-audio`` — which also writes the
    WebVTT, from the same timeline, with a pronunciation lexicon applied. The
    two cannot disagree, which is the point.

    Which engine speaks is speaker-helper's decision, not this file's and
    not the caller's: offline and free, its router answers chatterbox for
    both languages, and it has done since 2026-10-29.

    That costs determinism, and the line that used to stand here said the
    opposite. Kokoro returned the same bytes for the same text, voice and
    lexicon; chatterbox does not, so a restored WAV never byte-matches a
    resynthesized one and nothing should be written that expects it to.
    What still holds is the thing worth holding: the audio and the WebVTT
    come out of one call, off one timeline, so the two cannot drift apart.
    A seed archive therefore beats a re-narration — it is the same voice
    twice, where this is merely the same words.
    """
    import subprocess as sp

    wanted = list(narration())
    missing = [stem for stem in wanted if not (dest / f"vo-{stem}.wav").exists()]
    if not missing:
        return []
    if not fix:
        return [f"  would narrate    vo-{stem}.wav  <- narrate_films.py" for stem in missing]

    notes = []
    for stem in missing:
        film, _, lang = stem.rpartition(".")
        done = sp.run([sys.executable, str(ROOT / "narrate_films.py"), film, "--lang", lang],
                      capture_output=True, text=True, check=False)
        if done.returncode != 0 or not (dest / f"vo-{stem}.wav").exists():
            notes.append(f"  NARRATE FAILED   vo-{stem}.wav  "
                         f"({(done.stderr or done.stdout).strip()[:120]})")
        else:
            notes.append(f"  narrated         vo-{stem}.wav (+ its WebVTT)")
    return notes


def restore_derived(dest: pathlib.Path, fix: bool) -> list[str]:
    """Class B, the rest: the 512px logo and the four vision simulations."""
    notes = []
    logo_src, logo_out = REPO / "web/img/logo.png", dest / "logo-512.png"
    if not logo_out.exists():
        if not fix:
            notes.append("  would resize     logo-512.png  <- web/img/logo.png at 512x512")
        else:
            done = subprocess.run(["sips", "-z", "512", "512", str(logo_src),
                                   "--out", str(logo_out)],
                                  capture_output=True, text=True, check=False)
            notes.append("  resized          logo-512.png" if logo_out.exists()
                         else f"  RESIZE FAILED    logo-512.png ({done.stderr.strip()[:90]})")

    notes += restore_cvd(dest, fix)
    notes += restore_shots(dest, fix)
    notes += restore_make_figure_shots(dest, fix)
    notes += restore_density(dest, fix)
    return notes


def restore_density(dest: pathlib.Path, fix: bool) -> list[str]:
    """The accumulation plate, from sprezzature-maps, per language.

    Generated rather than copied out of the gallery: the gallery has no
    French one, because `--language fr` was decoration across that whole
    package until it was fixed. Regenerating here keeps the two cuts honest
    without waiting for a gallery rebuild.
    """
    maps = pathlib.Path.home() / "sprezzature-maps"
    missing = [rel for rel in DERIVED_MAPS if not (dest / rel).exists()]
    if not missing:
        return []
    script = maps / "scripts" / "make_density.py"
    if not script.exists():
        return [f"  NO TOOL          {rel}: {script} absent" for rel in missing]
    if not fix:
        return [f"  would render     {rel}  <- make_density.py --language "
                f"{DERIVED_MAPS[rel][0]}" for rel in missing]
    notes = []
    for rel in missing:
        lang, why = DERIVED_MAPS[rel]
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(
            [sys.executable, str(script), "--language", lang, "--out", str(out)],
            capture_output=True, text=True, check=False, cwd=str(maps),
        )
        if done.returncode != 0 or not out.exists():
            notes.append(f"  RENDER FAILED    {rel} "
                         f"({(done.stderr or done.stdout).strip()[:110]})")
        else:
            notes.append(f"  rendered         {rel}  ({why})")
    return notes


def restore_make_figure_shots(dest: pathlib.Path, fix: bool) -> list[str]:
    """The two captures of the real `make-figure` form the `cli-gui` film shows.

    Deliberately not `restore_shots`. That one rebuilds its page from
    ``figure_cli.py``, a reconstruction of an argparse front door written for
    a shoot in September and thrown away afterwards -- which is the right
    thing for the `interface` film, whose captures it has to reproduce, and
    the wrong thing for a film whose subject is introspecting the command that
    is actually installed. The reconstruction also still says "127 chart
    kinds": a number the catalogue passed months ago, which was sitting on
    screen in a film about checking what you claim.

    So these come from ``sprezzature_figures.cli:main`` through the installed
    ``sprezzature-cli-gui``. The cost is that a capture is only as current as
    the environment it was taken in; the benefit is that the number cannot go
    stale on its own, because it is whatever the command prints today.

    **Two captures, not two crops of one.** The first version shot the whole
    page with every ``<details>`` forced open -- 1040x4969 -- and cut two
    windows out of it. Both came out portrait, and the film lays them in a 4:3
    tile: they fitted by height, shrank to 442px wide, and the form became
    grey smudge. So each capture opens exactly one group and is taken at the
    tile's own shape. Nothing is cropped, no pixel offset has to stay true to
    a layout, and what the capture frames is what the scene shows.
    """
    wanted = {
        # file                           group to open   what it has to show
        "shots/make-figure-list.png":    ("list",   "a dropdown, a checkbox, the button"),
        "shots/make-figure-render.png":  ("render", "a required field, and flags as fields"),
    }
    missing = [r for r in wanted if not (dest / r).exists()]
    if not missing:
        return []
    gui = shutil.which("sprezzature-cli-gui")
    if gui is None:
        return ["  NO TOOL          shots/make-figure-*.png: sprezzature-cli-gui "
                "is not on PATH (pip install sprezzature-cli-gui)"]
    if importlib.util.find_spec("sprezzature_figures") is None:
        return ["  NO TOOL          shots/make-figure-*.png: sprezzature-figures "
                "is not importable, so there is no parser to introspect"]
    if not fix:
        return [f"  would capture    {r}  <- sprezzature_figures.cli:main, "
                f"{wanted[r][0]} open" for r in missing]

    work = dest / "shots/_make-figure.html"
    work.parent.mkdir(parents=True, exist_ok=True)
    done = subprocess.run([gui, "sprezzature_figures.cli:main", "--prog", "make-figure",
                           "--title", "make-figure", "--out", str(work)],
                          capture_output=True, text=True, check=False)
    if done.returncode != 0 or not work.exists():
        return [f"  GUI FAILED       {(done.stderr or done.stdout).strip()[:140]}"]
    page = work.read_text()

    # 1040x780 is the tile's 4:3 at a width where the help text is still
    # legible once the frame scales it down.
    W, H = 1040, 780
    notes = []
    for rel in sorted(missing):
        group, _why = wanted[rel]
        opened = _open_one_group(page, group)
        if opened is None:
            notes.append(f"  NO GROUP         {rel}: the page has no '{group}' group; "
                         f"the command's subcommands have been renamed")
            continue
        work.write_text(opened)
        err = chrome_png(work.resolve().as_uri(), dest / rel, W, H, full=False, scale=1)
        notes.append(f"  CAPTURE FAILED   {rel} ({err})" if err
                     else f"  captured         {rel}  <- {group} open")
    work.unlink(missing_ok=True)
    return notes


def _open_one_group(page: str, group: str) -> str | None:
    """Return *page* with only the ``<details>`` named *group* expanded.

    Returns None when no group carries that name, which is the one failure
    worth distinguishing: a capture of a page whose subcommand was renamed
    would come back as six collapsed headings and look merely boring, rather
    than wrong.
    """
    out, found = [], False
    for i, part in enumerate(page.split('<details class="')):
        if i == 0:
            out.append(part)
            continue
        # The summary is the first text after the tag; the group name is the
        # only word in it.
        head = part[: part.find("</summary>") + 10] if "</summary>" in part else part[:400]
        mine = re.search(r">\s*" + re.escape(group) + r"\s*<", head) is not None
        if mine:
            found = True
        out.append(('<details open class="' if mine else '<details class="') + part)
    return "".join(out) if found else None


def chrome_png(url: str, out: pathlib.Path, w: int, h: int,
               full: bool = False, scale: int = 2) -> str | None:
    """Rasterize a page with Chrome at 2x. Returns an error string, or None.

    Chrome and not rsvg-convert: rasterizing bar-grouped.svg with rsvg left 1.41%
    of pixels differing from the shipped original, text antialiasing mostly.
    Through Chrome at device_scale_factor=2 the difference is zero, because
    Chrome is what cut these assets in the first place.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "playwright absent (pip install playwright && playwright install chromium)"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
            page.goto(url)
            page.wait_for_timeout(1200)
            page.screenshot(path=str(out), full_page=full)
            b.close()
    except Exception as exc:                                   # noqa: BLE001
        return str(exc)[:140]
    return None


def restore_cvd(dest: pathlib.Path, fix: bool) -> list[str]:
    """The four colour-vision simulations, plus the original they are made from.

    The chain is: rasterize the shipped bar-grouped.svg at 2x, then hand it to
    sprezzature-colors, which applies the Machado matrices. The numbered names
    are this tree's, not the tool's — it writes `<stem>-protanopia.png` and so
    on, and the film needs them ordered.
    """
    out_dir = dest / "figures/cvd"
    missing = [n for n in CVD if not (out_dir / n).exists()]
    if not missing:
        return []
    sim = pathlib.Path.home() / "sprezzature-colors/scripts/simulate_cvd.py"
    svg = REPO / "web/img/figures/bar-grouped.svg"
    if not sim.exists():
        return [f"  NO TOOL          figures/cvd/ ({len(missing)}): {sim} absent"]
    if not fix:
        return [f"  would simulate   figures/cvd/ ({len(missing)}): {svg.name} at 2x"
                + f" -> {sim.name}, Machado matrices"]

    out_dir.mkdir(parents=True, exist_ok=True)
    original = out_dir / "00-original.png"
    err = chrome_png(svg.resolve().as_uri(), original, 745, 505)
    if err:
        return [f"  RASTER FAILED    figures/cvd/00-original.png ({err})"]

    done = subprocess.run([sys.executable, str(sim), str(original),
                           "--grayscale", "--out", str(out_dir)],
                          capture_output=True, text=True, check=False)
    if done.returncode != 0:
        return [f"  CVD FAILED       {done.stderr.strip()[:140]}"]

    notes = ["  rasterized       figures/cvd/00-original.png (Chrome, 2x)"]
    for n in CVD[1:]:
        src = out_dir / f"00-original-{n.split('-', 1)[1]}"
        if not src.exists():
            notes.append(f"  MISSING          figures/cvd/{n} (tool wrote no {src.name})")
            continue
        src.rename(out_dir / n)
        notes.append(f"  simulated        figures/cvd/{n}")
    return notes


def restore_shots(dest: pathlib.Path, fix: bool) -> list[str]:
    """The two screen captures of the cli-gui form the `interface` film shows.

    The argparse behind them was written for the shoot and thrown away; it is
    rebuilt in figure_cli.py from what the captures themselves show. The page is
    produced by sprezzature-cli-gui, not mocked, which is the whole claim the
    film makes about that scene.

    Unlike the narration, this does NOT come back byte-identical, and chasing
    that would be the wrong target: the pixels belong to the tool's stylesheet,
    which has moved since the shoot — the rebuilt full page is 1054px tall where
    the original was 1040. What has to hold is the content, and it does: all 18
    strings visible in the capture (prog, description, every flag, every default,
    every help line, both button labels) are in the rebuilt page, checked by
    tests/test_figure_cli.py. That is the invariant worth guarding; a byte
    compare would just break on the next CSS tweak.
    """
    # Viewports read off the originals. These are 1x, unlike the CVD frames:
    # the shoot captured the form at CSS size and the figure at 2x.
    wanted = {"shots/cli-gui-full.png": (760, 1040, True),
              "shots/cli-gui.png": (780, 560, False)}
    missing = [r for r in wanted if not (dest / r).exists()]
    if not missing:
        return []
    tool = pathlib.Path.home() / "sprezzature-cli-gui/scripts/cli_to_gui.py"
    if not tool.exists():
        return [f"  NO TOOL          shots/cli-gui*.png: {tool} absent"]
    if not fix:
        return [f"  would render     {r}  <- figure_cli.py:parser through {tool.name}"
                for r in sorted(missing)]

    html = dest / "shots/_cli-gui.html"
    html.parent.mkdir(parents=True, exist_ok=True)
    done = subprocess.run([sys.executable, str(tool), f"{ROOT / 'figure_cli.py'}:parser",
                           "--out", str(html)], capture_output=True, text=True, check=False)
    if done.returncode != 0 or not html.exists():
        return [f"  GUI FAILED       {(done.stderr or done.stdout).strip()[:140]}"]

    notes = [f"  rendered         {html.name} from figure_cli.py:parser"]
    for rel in sorted(missing):
        w, h, full = wanted[rel]
        err = chrome_png(html.resolve().as_uri(), dest / rel, w, h, full=full, scale=1)
        notes.append(f"  CAPTURE FAILED   {rel} ({err})" if err else f"  captured         {rel}")
    html.unlink(missing_ok=True)
    return notes


#: The two read-along captures, and everything needed to say them in one
#: place: which page is read, which language reads it, and the sentence the
#: capture stops on. The phrase is the anchor rather than a timestamp
#: because a re-narration moves every timestamp and moves no sentence --
#: chatterbox is not deterministic, so "the frame at 0:35" is not a thing a
#: clone can ask for twice.
READALONG: dict[str, tuple[str, str, str]] = {
    "shots/readalong.png": (
        "README.md", "en", "sized for a site you can hold in your head"),
    "shots/fr/readalong.png": (
        "LISEZMOI.md", "fr", "taillé pour un site qu'on tient dans sa tête"),
}


def restore_readalong(dest: pathlib.Path, fix: bool) -> list[str]:
    """Class B. The `publish` film's last frame: a page reading itself aloud.

    Three commands deep, and all three live in sprezzature-publish: narrate
    the Markdown, bind the narration to the page, then photograph the page
    mid-sentence. The cost is the first one -- a README is around five
    minutes of speech and chatterbox runs at an RTF between 4 and 8, so
    budget half an hour per language and do not start two at once.

    The working tree sits beside ``_assets/`` rather than inside it, for
    two reasons: the completeness line at the end counts every file under
    the target, and a half-hour narration is worth keeping across a run
    rather than across a reboot -- which is what ``/tmp`` would have given.

    Two things about the layout are load-bearing, and both failed silently
    the first time. The narration has to sit *inside* the directory the
    capture serves, because the hrefs are written relative to ``--out`` and
    a narration kept one level up gives ``src="../narration.wav"``, which
    ``http.server`` refuses as a traversal. And the page has to be served
    over HTTP at all: from a ``file://`` origin the player is an ES module
    the browser will not load and the ``<track>`` never fires. Neither
    raises. The page simply comes up with a player that never plays, and
    the capture waits for a highlight that cannot arrive.
    """
    missing = [rel for rel in READALONG if not (dest / rel).exists()]
    if not missing:
        return []
    pkg = pathlib.Path.home() / "sprezzature-publish"
    if not (pkg / "scripts/narrate_post.py").exists():
        return [f"  NO TOOL          {rel}: {pkg} absent" for rel in sorted(missing)]
    if not fix:
        return [f"  would capture    {rel}  <- narrate_post.py + md_to_html.py"
                f" --readalong + a frame of {READALONG[rel][0]}" for rel in sorted(missing)]

    notes = []
    for rel in sorted(missing):
        page, lang, phrase = READALONG[rel]
        work = dest.parent / "_readalong-work" / lang
        work.mkdir(parents=True, exist_ok=True)
        if not (work / "narration.vtt").exists():
            said = subprocess.run(
                [sys.executable, str(pkg / "scripts/narrate_post.py"), page,
                 "--lang", lang, "--out-dir", str(work)],
                cwd=pkg, capture_output=True, text=True, check=False)
            if said.returncode != 0 or not (work / "narration.vtt").exists():
                notes.append(f"  NARRATE FAILED   {rel} "
                             f"({(said.stderr or said.stdout).strip()[:120]})")
                continue
        built = subprocess.run(
            [sys.executable, str(pkg / "scripts/md_to_html.py"), page,
             "--out", str(work), "--readalong", str(work)],
            cwd=pkg, capture_output=True, text=True, check=False)
        html = work / f"{pathlib.Path(page).stem}.html"
        if built.returncode != 0 or not html.exists():
            notes.append(f"  BIND FAILED      {rel} "
                         f"({(built.stderr or built.stdout).strip()[:120]})")
            continue
        err = readalong_png(work, html.name, phrase, dest / rel)
        notes.append(f"  CAPTURE FAILED   {rel} ({err})" if err else f"  captured         {rel}")
    return notes


def readalong_png(root: pathlib.Path, page_name: str, phrase: str,
                  out: pathlib.Path) -> str | None:
    """Photograph a read-along page on the sentence it is speaking.

    Not :func:`chrome_png`: this one needs a server, a playing audio element
    and a wait on the highlight. The audio is muted, run at 16x and never
    seeked -- ``http.server`` answers no Range request, so a seek against it
    fails in a way that reads like a bug in the player.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "playwright absent (pip install playwright && playwright install chromium)"
    import functools
    import http.server
    import socketserver
    import threading

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
            page = b.new_page(viewport={"width": 760, "height": 570}, device_scale_factor=2)
            page.goto(f"http://127.0.0.1:{httpd.server_address[1]}/{page_name}")
            page.wait_for_selector("[data-ra-ui]:not([hidden])", timeout=20000)
            page.evaluate("async () => { const a ="
                          " document.querySelector('[data-ra-audio]');"
                          " a.muted = true; a.playbackRate = 16; await a.play(); }")
            page.wait_for_function(
                "p => { const el = document.querySelector('.ra-s.is-reading');"
                "       return !!el && el.textContent.includes(p); }",
                arg=phrase, timeout=120000)
            page.evaluate("document.querySelector('[data-ra-audio]').pause()")
            page.evaluate("document.querySelector('.ra-s.is-reading')"
                          ".scrollIntoView({block: 'center'})")
            page.wait_for_timeout(600)
            out.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out))
            b.close()
    except Exception as exc:                                   # noqa: BLE001
        return str(exc)[:140]
    finally:
        httpd.shutdown()
    return None


def restore_seed(dest: pathlib.Path, seed: pathlib.Path | None, fix: bool) -> list[str]:
    """Restore everything the archive holds that this tree lacks.

    Runs before A and B deliberately. A backup that only hands back the files
    nothing else can produce is a worse backup than one that hands back all of
    them: resynthesizing the voice costs minutes and shifts every duration, so
    when the archive has a WAV, the archive wins. A and B then fill the gaps.

    With no archive, the class C entries are the ones worth naming — the rest is
    reproducible, and SEED_ONLY says why each of these is not.
    """
    if seed is None:
        return [f"  NO SEED          {r}\n                     why: {SEED_ONLY[r]}"
                for r in sorted(SEED_ONLY) if not (dest / r).exists()]

    if seed.is_dir():
        tars = sorted(seed.rglob("*.tar.gz"))
        if not tars:
            return [f"  no .tar.gz under {seed}"]
        seed = tars[-1]

    notes, taken = [], 0
    with tarfile.open(seed) as tf:
        for m in tf.getmembers():
            name = pathlib.PurePosixPath(m.name).name
            # macOS tar stores xattrs as AppleDouble "._x" siblings. Not assets.
            if (not m.isfile() or name.startswith("._") or name == ".DS_Store"
                    or "_assets/" not in m.name):
                continue
            rel = m.name.split("_assets/", 1)[1]
            out = dest / rel
            if out.exists():
                continue
            if not fix:
                notes.append(f"  would extract    {rel}  <- {seed.name}")
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(m) as fh:
                out.write_bytes(fh.read())
            taken += 1
    if taken:
        notes.append(f"  extracted {taken} files from {seed.name}")
    for rel in sorted(SEED_ONLY):
        if not (dest / rel).exists():
            notes.append(f"  NOT IN SEED      {rel}\n                     why: {SEED_ONLY[rel]}")
    return notes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fix", action="store_true", help="actually write; default is report only")
    ap.add_argument("--seed", type=pathlib.Path, help="off-repo archive, or a directory of them")
    ap.add_argument("--into", type=pathlib.Path, help="target tree (default _assets/)")
    args = ap.parse_args()

    dest = (args.into or ROOT / "_assets").resolve()
    dest.mkdir(parents=True, exist_ok=True)
    print(f"target: {dest}\n")

    # Seed first: it can supply any class, and a restored WAV beats a resynthesized one.
    for title, notes in (
        ("seed archive", restore_seed(dest, args.seed, args.fix)),
        ("A. copies of tracked files", restore_tracked(dest, args.fix)),
        ("B. narration", restore_voice(dest, args.fix)),
        ("B. derived assets", restore_derived(dest, args.fix)),
        ("B. read-along captures", restore_readalong(dest, args.fix)),
    ):
        print(title)
        print("\n".join(notes) if notes else "  all present")
        print()

    have = sum(1 for f in dest.rglob("*")
           if f.is_file() and f.name != ".DS_Store" and not f.name.startswith("._"))
    # The trailing `+ 2 + 2`: the two `interface` captures, and the two
    # `make-figure` captures that replaced them for the cli-gui film.
    # The narration count is read, not typed: it was `17`, and adding a film
    # with nine lines made this self-check report 72/59 -- a wrong number in
    # the one line whose job is to say whether the tree is complete.
    want = (len(TRACKED) + len(narration()) + 1 + len(CVD) + 2 + 2
            + len(READALONG) + len(DERIVED_MAPS) + len(SEED_ONLY))
    print(f"{have}/{want} files present" + ("" if args.fix else "   (report only; pass --fix)"))


if __name__ == "__main__":
    main()

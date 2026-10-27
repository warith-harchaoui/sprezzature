#!/usr/bin/env python3
"""Emit the twelve HyperFrames projects: four films, three canvases each.

One spec per film drives all three formats, so the series stays frame-synced:
the same beat lands at the same second in landscape, portrait and square.
Only the layout changes, never the timing.

Run from brag-output/:  python3 build_films.py
"""

from __future__ import annotations

import json
import pathlib
import copy
import shutil
from typing import Any

import films_fr
import make_captions
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
FILMS_DIR = ROOT / "films"
ASSETS = ROOT / "_assets"
MUSIC = "happy-beats-business-moves-vol-12-by-ende-dot-app.mp3"

# ---------------------------------------------------------------------------
# Design tokens, taken from web/css/app.css, [data-color-mode=academic].
# ---------------------------------------------------------------------------
INK, INK_SOFT, BLUE, LINE, PAPER = "#171717", "#525252", "#0072b2", "#e5e5e5", "#ffffff"
NAVY = "#003c5d"   # brand-navy: the eyebrow rides over the wash, blue does not clear AA there

# Per-canvas scale. Portrait is watched full-screen on a phone, so its type is
# relatively larger; square gives up the most room and shrinks the figure.
FORMATS = {
    "landscape": dict(w=1920, h=1080, pad=104, hero=104, h2=44, body=38, mono=29,
                      eyebrow=26, chip=32, split=True, fig=1010, grid6=3, shot=880,
                      view=0.62),
    "portrait":  dict(w=1080, h=1920, pad=72, hero=92, h2=52, body=44, mono=32,
                      eyebrow=28, chip=31, split=False, fig=884, grid6=2, shot=780,
                      view=1.05),
    "square":    dict(w=1080, h=1080, pad=64, hero=74, h2=40, body=34, mono=26,
                      eyebrow=23, chip=25, split=False, fig=600, grid6=3, shot=560,
                      view=0.80),
}

# Beat grid of the bundled track, 109.96 BPM.
#
# Extended from 42 beats (23 s) to 111 (60 s) on 2026-10-26, when the films
# grew to a minute. Not extrapolated: `npx hyperframes beats` detected 483
# onsets across the whole 117 s track -- at 243.9 BPM and flagged uncertain,
# because it found subdivisions rather than the musical pulse. So the pulse is
# walked at 60/109.96 and each step SNAPPED to the nearest detected onset
# within 120 ms. Every one of the 111 found one, and the result agrees with
# the original hand-measured 42 to a mean of 12 ms -- which is the check that
# matters: a new grid has to put the known-good beats where they already were.
BEATS = [0.549, 1.106, 1.637, 2.181, 2.736, 3.288, 3.819, 4.368,
         4.912, 5.471, 5.995, 6.549, 7.088, 7.653, 8.181, 8.731,
         9.28, 9.819, 10.368, 10.917, 11.461, 12.005, 12.549, 13.093,
         13.643, 14.187, 14.731, 15.28, 15.819, 16.368, 16.912, 17.467,
         18.005, 18.555, 19.099, 19.648, 20.187, 20.741, 21.28, 21.829,
         22.368, 22.923, 23.461, 24.005, 24.549, 25.104, 25.643, 26.192,
         26.741, 27.285, 27.824, 28.379, 28.923, 29.467, 30.005, 30.555,
         31.099, 31.643, 32.187, 32.741, 33.28, 33.824, 34.368, 34.923,
         35.461, 36.011, 36.555, 37.104, 37.643, 38.192, 38.736, 39.28,
         39.824, 40.373, 40.917, 41.461, 42.005, 42.549, 43.163, 43.648,
         44.187, 44.741, 45.285, 45.824, 46.368, 46.917, 47.467, 48.011,
         48.56, 49.104, 49.648, 50.187, 50.741, 51.28, 51.829, 52.373,
         52.943, 53.488, 54.034, 54.58, 55.125, 55.671, 56.217, 56.747,
         57.308, 57.957, 58.395, 58.928, 59.451, 60.036, 60.539]

def L(en: str, fr: str) -> dict[str, str]:
    """One line of film text, in both languages, written together.

    The French used to live in a lookup table keyed on the English string,
    and that table is what made the French bad. Filling in a blank next to
    `"Turned into something that runs"` produces `"Transformé en quelque
    chose qui tourne"` — English word order wearing French words — because
    the unit of work is a fragment torn out of its sentence. Twenty-five
    fragments per film, each translated alone, and the result reads like a
    machine did it. One of them came out in the *passé simple*.

    Written here, the two sit on adjacent lines inside the scene they belong
    to, so composing the French is writing a line of a script with the rest
    of the script visible. The two cuts say the same thing and are not
    sentence-by-sentence equivalents, which is the whole point: good French
    is not where good English lands.
    """
    return {"en": en, "fr": fr}


#: Films whose text has been rewritten as L() pairs. The rest still carry
#: plain English strings and fall back to the old lookup table, which is the
#: thing being replaced: it translated each fragment alone, out of its
#: sentence, and that is what made the French bad.
#:
#: Listed rather than detected so the remaining work is visible. A film leaves
#: this set by being rewritten, not by being edited.
REWRITTEN = frozenset({"sprezzature", "colors"})


def say(value: Any, lang: str, *, fallback: bool = False) -> Any:
    """Resolve an L() to one language; translate a bare string if asked.

    `fallback` is the transitional path for films not yet rewritten. It keeps
    their French cuts in French while the rewrite works through them one at a
    time, instead of silently shipping eleven English films labelled fr.
    """
    if isinstance(value, dict) and "en" in value and "fr" in value:
        return value[lang]
    if isinstance(value, list):
        return [say(v, lang, fallback=fallback) for v in value]
    if isinstance(value, tuple):
        return tuple(say(v, lang, fallback=fallback) for v in value)
    if fallback and isinstance(value, str) and value.strip():
        try:
            return films_fr.tr(value)
        except films_fr.Untranslated:
            return value
    return value


def in_language(spec: dict, lang: str, film: str = "") -> dict:
    """A copy of one film's spec with every L() resolved to *lang*."""
    out = copy.deepcopy(spec)
    legacy = lang != "en" and film not in REWRITTEN
    TEXT = ("line", "caption", "eyebrow", "mark", "rows", "items", "steps")
    for scene in out["scenes"]:
        for key, value in list(scene.items()):
            scene[key] = say(value, lang, fallback=legacy and key in TEXT)
        if lang != "en":
            if scene.get("images"):
                scene["images"] = [films_fr.french_asset(i) for i in scene["images"]]
            for key in ("fig", "gray", "base", "src"):
                if scene.get(key):
                    scene[key] = films_fr.french_asset(scene[key])
    return out


OUTRO_LINE = L("Make it. Audit it. Then look at it.",
               "Fabriquez. Auditez. Puis regardez.")



def on_beat(*targets: float) -> list[float]:
    """Snap each target to the nearest beat.

    The four films written before the grid reached a minute carry their reveal
    times as literals, hand-picked off the 42-beat grid. At eight scenes a film
    that stops being honest work: a literal is only on the beat until somebody
    nudges a scene by a tenth of a second, and nothing says it has drifted. So
    the later specs name the moment they want and let the grid decide, which is
    also how a reader checks them -- `on_beat(42.5)` is readable, `42.549` is
    a number you have to go and look up.
    """
    return [min(BEATS, key=lambda b: abs(b - t)) for t in targets]



# ---------------------------------------------------------------------------
# Film specs. `at` values are global seconds and identical across formats.
#
# Eleven films, one per brick plus the suite, English and French. The four
# that came before -- a suite film and three that grouped bricks by theme --
# were removed on 2026-10-26 once their replacements were rendered and their
# copies archived in `_retired/group-films/`. Grouping was the wrong axis:
# `interface` had to speak for ui, cli-gui, publish and ux-laws in eighteen
# seconds, so it said something general about four packages and something
# particular about none. `group_scenes`, the shared four-beat shape those
# three were built from, went with them.
#
# They are still ON THE SERVER. An upload does not remove a file; only a
# delete there does. See sftp/UPLOAD-films.txt.
# ---------------------------------------------------------------------------
LOOP_STEPS = [("01", L("render", "dessiner")),
              ("02", L("look", "regarder")),
              ("03", L("fix the source", "corriger la source")),
              ("04", L("again", "recommencer"))]

FILMS = {
    # ---------------------------------------------------------------- global
    "sprezzature": dict(
        duration=60.0,
        # The thesis film, rewritten 2026-10-27 under the writing charters.
        # It used to end on "Ten packages. Five surfaces each." -- a spec
        # sheet, and the least interesting thing that had been on screen. It
        # ends on what stays on your machine instead, which is the claim a
        # viewer has no other way to hear.
        vo=[("sprezzature.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 24.55), ("wipe", 38.74),
             ("bell", 55.67)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line=L("Most design decisions were settled long ago.",
                        "La plupart des décisions de design sont tranchées "
                        "depuis longtemps.")),
            dict(type="chips", start=5.4, dur=9.1, end=14.4,
                 eyebrow=L("Written down by other people",
                           "Écrites par d'autres"),
                 items=["30 Laws of UX", L("WCAG contrast", "contraste WCAG"),
                        "Machado 2009", "Gestalt", "Equal Earth", "W3C WebVTT",
                        "Schema.org", "OKLCH"],
                 at=on_beat(6.5, 7.1, 7.6, 8.2, 8.7, 9.3, 9.8, 10.4),
                 caption=L("Yablonski for the laws. The W3C for contrast. A "
                           "2009 paper for what a colour-blind reader sees.",
                           "Yablonski pour les lois. Le W3C pour le contraste. "
                           "Un article de 2009 pour ce que voit un daltonien.")),
            dict(type="grid", start=14.3, dur=9.2, end=23.4,
                 eyebrow=L("What the rules produce", "Ce que les règles produisent"),
                 images=["figures/corr-matrix.svg", "figures/calendar-heatmap.svg",
                         "figures/map-flow.svg", "figures/choropleth.svg"],
                 at=on_beat(15.8, 16.4, 16.9, 17.5),
                 caption=L("A matrix, a calendar, a flow, a choropleth. Each "
                           "one answered to the rule that governs it.",
                           "Une matrice, un calendrier, un flux, un "
                           "choroplèthe. Chacun confronté à la règle qui le "
                           "gouverne.")),
            dict(type="versus", start=23.3, dur=9.2, end=32.4,
                 eyebrow=L("The same rules, aimed twice",
                           "Les mêmes règles, braquées deux fois"),
                 left=(L("Make", "Fabriquer"),
                       L("a page, a figure, a map, a palette",
                         "une page, une figure, une carte, une palette")),
                 right=(L("Audit", "Auditer"),
                        L("those rules, run over what shipped",
                          "ces règles, passées sur ce qui est livré")),
                 at=on_beat(24.5, 25.6),
                 caption=L("167 chart kinds. 20 accessibility rules. 30 laws "
                           "of UX.",
                           "167 types de graphiques. 20 règles "
                           "d'accessibilité. 30 lois d'UX.")),
            dict(type="loop", start=32.3, dur=16.7, end=49.0,
                 eyebrow=L("The part no rule covers",
                           "La part qu'aucune règle ne couvre"),
                 steps=LOOP_STEPS,
                 fig="figures/bar-grouped.svg", gray="figures/bar-grouped-gray.svg",
                 ratio=745 / 505, step_at=on_beat(33.3, 34.4, 35.5, 36.6),
                 wipe_at=38.7, wipe_dur=1.09, caption_at=43.6,
                 caption=L("A vision model reads the chart back to you. It "
                           "names what fails. The source is what gets fixed.",
                           "Un modèle de vision vous relit le graphique. Il "
                           "nomme ce qui cloche. C'est la source qu'on "
                           "corrige.")),
            dict(type="held", start=48.9, dur=6.7, end=55.5,
                 line=L("It runs where you are. Nothing leaves the machine.",
                        "Il tourne là où vous êtes. Rien n'en sort.")),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # ------------------------------------------------------------------ colors
    "colors": dict(
        duration=60.0,
        # Rewritten 2026-10-27 after reading the package properly. The old cut
        # showed four simulations in a row and called that an argument. The
        # package has a better one and states it in a module docstring nobody
        # watching a film will ever open: lightness is the only channel that
        # no deficiency, no printer and no screen in sunlight takes away, and
        # all three tools work on it. That is the film now, and the sentence
        # has since been promoted into the README as well.
        #
        # Mostly picture: twenty-two seconds of the simulator, which is longer
        # than any beat in the first set.
        vo=[("colors.en", 1.10)],
        sfx=[("drop", 5.47), ("wipe", 18.01), ("wipe", 21.83), ("tile", 41.46),
             ("bell", 55.67)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line=L("Light grey on white reads fine. To you, indoors.",
                        "Du gris clair sur blanc se lit bien. Pour vous, à "
                        "l'intérieur.")),
            dict(type="versus", start=5.4, dur=9.1, end=14.4,
                 eyebrow=L("The same button, two readers",
                           "Le même bouton, deux lecteurs"),
                 left=(L("Low vision", "Malvoyance"),
                       L("the text and the background sit too close",
                         "le texte et le fond sont trop proches")),
                 right=(L("Bright sunlight", "Plein soleil"),
                        L("a phone screen loses the difference",
                          "un écran de téléphone perd la différence")),
                 at=on_beat(6.5, 7.6),
                 caption=L("It reads fine to whoever picked the colour. That "
                           "is the problem.",
                           "Ça se lit bien pour qui a choisi la couleur. "
                           "C'est tout le problème.")),
            dict(type="claim", start=14.3, dur=4.8, end=18.0,
                 line=L("About one man in twelve sees red and green as one bar.",
                        "Environ un homme sur douze voit le rouge et le vert "
                        "comme une seule barre.")),
            # Twenty-two seconds. The argument here is made by looking.
            dict(type="cvd", start=17.9, dur=22.0, end=39.8,
                 eyebrow=L("Rendered for those eyes", "Rendu pour ces yeux-là"),
                 base="figures/cvd/00-original.png",
                 stages=[("01", L("protanopia", "protanopie"),
                          "figures/cvd/01-protanopia.png", 19.65),
                         ("02", L("deuteranopia", "deutéranopie"),
                          "figures/cvd/02-deuteranopia.png", 24.55),
                         ("03", L("tritanopia", "tritanopie"),
                          "figures/cvd/03-tritanopia.png", 29.47),
                         ("04", L("grayscale", "niveaux de gris"),
                          "figures/cvd/04-grayscale.png", 34.37)],
                 ratio=1490 / 1010, wipe_dur=0.80, caption_at=36.55,
                 caption=L("Measured transforms, from a 2009 paper. Not an "
                           "impression of what it might look like.",
                           "Des transformations mesurées, d'un article de "
                           "2009. Pas une idée de ce que ça donnerait.")),
            dict(type="held", start=39.7, dur=9.3, end=49.0,
                 line=L("Lightness is the one channel nothing takes away.",
                        "La clarté est le seul canal que rien ne retire.")),
            dict(type="versus", start=48.9, dur=6.7, end=55.5,
                 eyebrow=L("So that is the channel it moves",
                           "C'est donc le canal qu'il déplace"),
                 left=(L("Your hue", "Votre teinte"),
                       L("held fixed, with the saturation",
                         "figée, avec la saturation")),
                 right=(L("Its lightness", "Sa clarté"),
                        L("walked until the ratio clears",
                          "parcourue jusqu'à ce que le rapport passe")),
                 at=on_beat(49.6, 50.7),
                 caption=L("Your brand blue stays your brand blue.",
                           "Votre bleu de marque reste votre bleu de marque.")),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 colors", line=OUTRO_LINE,
                 url="sprezzature.ai"),
        ],
    ),
    # ---------------------------------------------------------------- figures
    "figures": dict(
        duration=60.0,
        vo=[("fig-1", 1.10), ("fig-2", 6.50), ("fig-3", 15.00), ("fig-4", 24.00),
            ("fig-5", 32.50), ("fig-6", 41.00), ("fig-7", 49.50), ("fig-8", 55.80)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 24.55), ("wipe", 33.28),
             ("tile", 42.55), ("bell", 55.67)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line="One hundred and sixty-seven kinds of chart. Every one hand-authored."),
            dict(type="grid", start=5.4, dur=9.1, end=14.4,
                 eyebrow="No charting library underneath",
                 images=["figures/sankey.svg", "figures/alluvial.svg",
                         "figures/chord.svg", "figures/calendar-heatmap.svg",
                         "figures/bellcurve.svg", "figures/circle-packing.svg"],
                 at=on_beat(6.5, 7.1, 7.6, 8.2, 8.7, 9.3),
                 caption="Each generator writes the SVG markup itself, so the "
                         "shapes are not a library's defaults."),
            # The category list is the honest answer to "167 of what?" -- and
            # the two nobody ships are the ones that make the number credible.
            dict(type="chips", start=14.3, dur=9.2, end=23.4,
                 eyebrow="Fifty-two categories",
                 items=["Comparison", "Distribution", "Flow", "Geospatial",
                        "Hierarchy", "Matrix", "Meteorology", "Model evaluation"],
                 at=on_beat(15.8, 16.4, 16.9, 17.5, 18.0, 18.6, 19.1, 19.6),
                 caption="Wind roses and wind barbs. ROC curves, calibration "
                         "plots, confusion matrices, Kaplan\u2013Meier."),
            dict(type="grid", start=23.3, dur=9.2, end=32.4,
                 eyebrow="The deliverable is the vector",
                 images=["figures/corr-matrix.svg", "figures/clustermap.svg",
                         "figures/candlestick.svg", "figures/map-flow.svg"],
                 at=on_beat(24.5, 25.1, 25.6, 26.2),
                 caption="Explicit width, height and a matching viewBox \u2014 "
                         "the text stays selectable at any zoom."),
            dict(type="claim", start=32.3, dur=9.2, end=41.4,
                 line="A PNG is an export, for places that cannot take vector art."),
            # The loop gets fourteen seconds here, where in the suite film it
            # gets seven: this is the package it was built for.
            dict(type="loop", start=41.3, dur=14.2, end=55.5,
                 eyebrow="No reference does this", steps=LOOP_STEPS,
                 fig="figures/bar-grouped.svg", gray="figures/bar-grouped-gray.svg",
                 ratio=745 / 505, step_at=on_beat(42.5, 43.6, 44.7, 45.8),
                 wipe_at=47.5, wipe_dur=1.09, caption_at=51.3,
                 caption="A model reads the figure, names what is wrong, and "
                         "the source is what gets fixed. Nothing leaves the machine."),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 figures", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # ---------------------------------------------------------------- publish
    "publish": dict(
        duration=60.0,
        vo=[("pub-1", 1.10), ("pub-2", 6.50), ("pub-3", 15.00), ("pub-4", 24.00),
            ("pub-5", 32.50), ("pub-6", 41.00), ("pub-7", 49.50), ("pub-8", 55.80)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 24.55), ("tile", 33.28),
             ("tile", 42.55), ("bell", 55.67)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line="A document, becoming a site."),
            dict(type="chips", start=5.4, dur=9.1, end=14.4,
                 eyebrow="Nine tools, one document",
                 items=["lint", "html", "icons", "indexes", "meta", "plain",
                        "changelog", "narrate", "readalong"],
                 at=on_beat(6.5, 7.1, 7.6, 8.2, 8.7, 9.3, 9.8, 10.4, 10.9),
                 caption="The linter is standard library only, runs in "
                         "milliseconds, and fixes what has exactly one fix."),
            dict(type="panel", start=14.3, dur=9.2, end=23.4,
                 eyebrow="What a page owes its readers",
                 rows=[("indexes", "robots.txt, sitemap.xml, Atom, humans.txt \u2014 and llms.txt, llms-full.txt"),
                       ("meta", "Open Graph, Twitter Card, Schema.org")],
                 at=on_beat(16.4, 17.5),
                 caption="One logo becomes the favicon, the app icons, the PWA "
                         "icons, and the <head> that points at them."),
            dict(type="panel", start=23.3, dur=9.2, end=32.4,
                 eyebrow="And what it rewrites",
                 rows=[("plain", "the same page at a target reading grade, keeping the terms you name"),
                       ("changelog", "a CHANGELOG becomes dated posts")],
                 at=on_beat(24.5, 25.6),
                 caption="Simpler language is not the same as a vaguer one. "
                         "The nouns you chose survive the rewrite."),
            dict(type="claim", start=32.3, dur=9.2, end=41.4,
                 line="Then readalong binds the narration to the page."),
            dict(type="panel", start=41.3, dur=7.8, end=49.0,
                 eyebrow="Two packages, one reading",
                 rows=[("The voice", "lives in sprezzature-audio")
                       , ("This package", "never imports a model")],
                 at=on_beat(42.5, 43.6),
                 caption="A boundary drawn on purpose: the heavy imports stay "
                         "out of the tool you run on every commit."),
            dict(type="claim", start=48.9, dur=6.7, end=55.5,
                 line="The sentence being spoken is the sentence lit up."),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 publish", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # ------------------------------------------------------------------ audio
    "audio": dict(
        duration=60.0,
        vo=[("aud-1", 1.10), ("aud-2", 6.50), ("aud-3", 15.00), ("aud-4", 24.00),
            ("aud-5", 32.50), ("aud-6", 41.00), ("aud-7", 49.50), ("aud-8", 55.80)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 24.55), ("tile", 33.28),
             ("tile", 42.55), ("bell", 55.67)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line="One modality, read in both directions."),
            dict(type="panel", start=5.4, dur=9.1, end=14.4,
                 eyebrow="The two directions",
                 rows=[("Captions", "sound becomes timed text"),
                       ("Narration", "text becomes timed sound")],
                 at=on_beat(6.5, 7.6),
                 caption="The package's own framing, and the reason both live "
                         "in one place instead of two."),
            dict(type="chips", start=14.3, dur=9.2, end=23.4,
                 eyebrow="The models, named",
                 items=["whisper.cpp", "large-v3-turbo", "NeMo Sortformer",
                        "TitaNet", "RTTM", "WebVTT", "Kokoro", "af_heart"],
                 at=on_beat(15.8, 16.4, 16.9, 17.5, 18.0, 18.6, 19.1, 19.6),
                 caption="Who spoke when, up to four speakers, in the format "
                         "speech research already reads."),
            dict(type="panel", start=23.3, dur=9.2, end=32.4,
                 eyebrow="Narration lands as two files",
                 rows=[("The WAV", "the voice itself, loudness-normalised"),
                       ("The WebVTT", "the same words, timed \u2014 like a transcript")],
                 at=on_beat(24.5, 25.6),
                 caption="Which is what lets a page follow the reading, "
                         "sentence by sentence, without a second pass."),
            dict(type="claim", start=32.3, dur=9.2, end=41.4,
                 line="And it audits its own output."),
            dict(type="panel", start=41.3, dur=7.8, end=49.0,
                 eyebrow="What audit_captions measures",
                 rows=[("Per cue", "reading speed, line width, duration"),
                       ("Across cues", "overlaps, and gaps that read as a dropout")],
                 at=on_beat(42.5, 43.6),
                 caption="Measured against the rates a reader can actually "
                         "keep up with, not against a guess."),
            dict(type="claim", start=48.9, dur=6.7, end=55.5,
                 line="A caption track can be present and still be unreadable."),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 audio", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # ---------------------------------------------------------------- cli-gui
    "cli-gui": dict(
        duration=60.0,
        vo=[("cli-1", 1.10), ("cli-2", 6.50), ("cli-3", 15.00), ("cli-4", 24.00),
            ("cli-5", 32.50), ("cli-6", 41.00), ("cli-7", 49.50), ("cli-8", 55.80)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 24.55), ("tile", 33.28),
             ("tile", 42.55), ("bell", 55.67)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line="A tool nobody will type, wrapped in a page."),
            # Two real captures of the generated page. They are the whole argument
            # -- a form somebody can hand to a colleague.
            #
            # Not the shots the `interface` film used: those come back through
            # `figure_cli.py`, a reconstruction of an argparse front door that
            # was written for a shoot in September and thrown away. It still
            # renders, and it still says "127 chart kinds" -- a number the
            # catalogue passed months ago, sitting on screen in a film about
            # auditing claims. These two are captured from
            # `sprezzature_figures.cli:main`, the command that is actually
            # installed, so the number cannot go stale without the command
            # going stale with it.
            dict(type="grid", start=5.4, dur=9.1, end=14.4,
                 eyebrow="Generated, not written",
                 images=["shots/make-figure-list.png", "shots/make-figure-render.png"],
                 at=on_beat(6.5, 7.6),
                 caption="Flags become fields. Choices become a dropdown. "
                         "Required stays required."),
            dict(type="claim", start=14.3, dur=9.2, end=23.4,
                 line="It does not read the help text. It reads the parser object."),
            dict(type="panel", start=23.3, dur=9.2, end=32.4,
                 eyebrow="Three adapters, one schema",
                 rows=[("argparse, Click, Typer", "introspected: fields, defaults, types"),
                       ("schema.py", "what every adapter produces, normalised")],
                 at=on_beat(24.5, 25.6),
                 caption="So the renderer never has to know which framework "
                         "the command line was written in."),
            dict(type="claim", start=32.3, dur=9.2, end=41.4,
                 line="And when no parser object is reachable, it parses --help."),
            dict(type="panel", start=41.3, dur=7.8, end=49.0,
                 eyebrow="Which is how the rest get a form",
                 rows=[("A subprocess", "runs --help and reads what it printed"),
                       ("A Go or Rust CLI", "covered, without a line of Python in it")],
                 at=on_beat(42.5, 43.6),
                 caption="Less exact than introspection, and named as such "
                         "rather than presented as the same thing."),
            dict(type="claim", start=48.9, dur=6.7, end=55.5,
                 line="The page is the deliverable. The command stays the command."),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 cli-gui", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # --------------------------------------------------------------------- ui
    "ui": dict(
        duration=60.0,
        vo=[("ui-1", 1.10), ("ui-2", 6.50), ("ui-3", 15.00), ("ui-4", 24.00),
            ("ui-5", 32.50), ("ui-6", 41.00), ("ui-7", 49.50), ("ui-8", 55.80)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 24.55), ("tile", 33.28),
             ("tile", 42.55), ("bell", 55.67)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line="The smallest brick, on purpose."),
            dict(type="panel", start=5.4, dur=9.1, end=14.4,
                 eyebrow="Two halves of one judgement",
                 rows=[("In prose", "the three-Roboto rule, the tokens, what an interface has to respect"),
                       ("In code", "the part a machine can carry out")],
                 at=on_beat(6.5, 7.6),
                 caption="Most of it stays prose, because most of it is a "
                         "decision rather than a check."),
            dict(type="claim", start=14.3, dur=9.2, end=23.4,
                 line="A hardcoded sentence costs nothing the day it is written."),
            dict(type="claim", start=23.3, dur=9.2, end=32.4,
                 line="It costs a week the day somebody needs a second language."),
            dict(type="panel", start=32.3, dur=9.2, end=41.4,
                 eyebrow="Where that week actually goes",
                 rows=[("Scattered", "JavaScript literals, HTML attributes, prompt templates in Python"),
                       ("Extracted", "one catalogue, and a page that switches")],
                 at=on_beat(33.3, 34.4),
                 caption="The mechanised half, and the only one worth "
                         "mechanising: finding every sentence you forgot."),
            dict(type="chips", start=41.3, dur=7.8, end=49.0,
                 eyebrow="And what ships with it",
                 items=["9 components", "9 snippets", "6 font files",
                        "a starter page", "design tokens", "theme toggle"],
                 at=on_beat(42.5, 43.1, 43.6, 44.2, 44.7, 45.3),
                 caption="Roboto, Roboto Serif, Roboto Mono \u2014 vendored, so a "
                         "page never waits on a font server."),
            dict(type="claim", start=48.9, dur=6.7, end=55.5,
                 line="Taste is written down once, then it is somebody else's too."),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 ui", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # ------------------------------------------------------------------ video
    # The tenth brick, and the one that made the other nine films. Its subject
    # is the films themselves, which is why it can afford to be plain: every
    # scene is a sentence about the thing the viewer is currently watching.
    "video": dict(
        duration=60.0,
        vo=[("vid-1", 1.10), ("vid-2", 6.50), ("vid-3", 15.00), ("vid-4", 24.00),
            ("vid-5", 32.50), ("vid-6", 41.00), ("vid-7", 49.50), ("vid-8", 55.80)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 24.55), ("tile", 33.28),
             ("tile", 42.55), ("bell", 55.67)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line="A film is a claim with a soundtrack."),
            dict(type="panel", start=5.4, dur=9.1, end=14.4,
                 eyebrow="Two kinds of claim",
                 rows=[("Declared", "a sentence, and the code behind it"),
                       ("Undeclared", "a number on screen that nothing sourced")],
                 at=on_beat(6.5, 7.6),
                 caption="The second kind is the dangerous one, because "
                         "nobody wrote it down to be checked."),
            dict(type="claim", start=14.3, dur=9.2, end=23.4,
                 line="167. 52. 30. 20. Every one of those is checkable."),
            # The provenance classes, which is the part that saves files.
            dict(type="panel", start=23.3, dur=9.2, end=32.4,
                 eyebrow="And the assets are ledgered",
                 rows=[("TRACKED", "in git, restorable from the repository"),
                       ("DERIVED", "rebuilt by a script that is in git"),
                       ("SOLE", "the only copy there is")],
                 at=on_beat(24.5, 25.1, 25.6),
                 caption="Three classes, because exactly one of them cannot "
                         "be got back."),
            dict(type="claim", start=32.3, dur=9.2, end=41.4,
                 line="A sole copy is the one a cleanup deletes without noticing."),
            dict(type="panel", start=41.3, dur=7.8, end=49.0,
                 eyebrow="Captions are measured, not guessed",
                 rows=[("The duration", "read off the voice file itself"),
                       ("The split", "at a sentence end, never mid-clause")],
                 at=on_beat(42.5, 43.6),
                 caption="A line that overruns the next one is a caption "
                         "track nobody can follow."),
            dict(type="claim", start=48.9, dur=6.7, end=55.5,
                 line="Then a poster frame, and a loudness pass."),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 video", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # ------------------------------------------------------------------- maps
    "maps": dict(
        duration=60.0,
        vo=[("maps-1", 1.10), ("maps-2", 6.50), ("maps-3", 15.00),
            ("maps-4", 24.00), ("maps-5", 33.00), ("maps-6", 42.00),
            ("maps-7", 49.50), ("maps-8", 55.80)],
        sfx=[("drop", 5.46), ("tile", 16.38), ("tile", 24.57), ("tile", 33.65),
             ("tile", 42.55), ("bell", 55.63)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line="A column of countries is a map waiting to happen."),
            # Situation plates only: of the three kinds this package draws,
            # these are the ones worth a minute of somebody's attention. Four
            # reference plates, where the geography is the whole point.
            dict(type="grid", start=5.4, dur=9.1, end=14.4,
                 eyebrow="Real coastlines, a real projection",
                 images=["maps/situation-himalaya.png", "maps/situation-iberia.png",
                         "maps/situation-switzerland.png", "maps/situation-western-europe.png"],
                 at=[6.55, 7.64, 8.74, 9.83],
                 caption="Eight kilometres of relief, the Meseta, the lakes, "
                         "and the physical base the rest is drawn on."),
            dict(type="panel", start=14.3, dur=9.2, end=23.4,
                 eyebrow="The projection is a decision, not a default",
                 rows=[("Equal Earth", "areas stay honest, published 2018"),
                       ("Lambert conformal conic", "centred on the region you asked for")],
                 at=[16.38, 17.47],
                 caption="Every recipe for flattening the Earth distorts "
                         "something. This one says which."),
            # And two areas-of-control plates, which is what the kind is for.
            dict(type="grid", start=23.3, dur=9.2, end=32.4,
                 eyebrow="Who controls what",
                 images=["maps/situation-ukraine.png", "maps/situation-syria.png"],
                 at=[24.57, 25.66],
                 caption="Zones by category, flashpoints, a contact line, and "
                         "a scale bar in two units at once."),
            dict(type="claim", start=32.3, dur=9.2, end=41.4,
                 line="The density map draws no coastline at all."),
            dict(type="panel", start=41.3, dur=7.8, end=49.0,
                 eyebrow="And it still reads as land",
                 rows=[("The land", "appears because events fell on it"),
                       ("The sea", "stays dark because none did")],
                 at=[42.55, 43.64],
                 caption="The reader recognises the shape without being shown it."),
            dict(type="claim", start=48.9, dur=6.7, end=55.5,
                 line="Natural Earth, GMTED2010, TIGER/Line \u2014 every source named."),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 maps", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # ----------------------------------------------------------------- ux-laws
    "ux-laws": dict(
        duration=60.0,
        vo=[("uxlaws-1", 1.10), ("uxlaws-2", 6.00), ("uxlaws-3", 13.00),
            ("uxlaws-4", 20.50), ("uxlaws-5", 30.00), ("uxlaws-6", 38.50),
            ("uxlaws-7", 46.00), ("uxlaws-8", 55.80)],
        sfx=[("drop", 5.46), ("tile", 14.20), ("tile", 21.85), ("wipe", 31.46),
             ("tile", 39.08), ("bell", 55.63)],
        scenes=[
            dict(type="claim", start=0.0, dur=5.5, end=5.0,
                 line="Nobody says \u201cthat violates Hick\u2019s Law\u201d."),
            dict(type="panel", start=4.9, dur=7.6, end=12.4,
                 eyebrow="What they say instead",
                 rows=[("\u201cThis page is overwhelming\u201d", "too many choices at once"),
                       ("\u201cI can never find the button\u201d", "no hit area, no focus ring")],
                 at=[5.46, 6.55],
                 caption="A usability finding in plain clothes. The job is to "
                         "locate it, name it, and make it fixable."),
            dict(type="chips", start=12.3, dur=7.9, end=20.1,
                 eyebrow="Thirty laws, curated by Jon Yablonski",
                 items=["Hick", "Miller", "Fitts", "Jakob", "Tesler",
                        "Choice overload", "Selective attention", "Aesthetic-Usability"],
                 at=[13.11, 13.64, 14.20, 14.73, 15.29, 15.84, 16.38, 16.93],
                 caption="Eight of the thirty are decidable from the source. "
                         "Those eight are the ones the auditor checks."),
            dict(type="panel", start=20.0, dur=9.5, end=29.4,
                 eyebrow="What the auditor actually catches",
                 rows=[("Fitts", "a control with no 44-pixel hit area"),
                       ("Miller", "an unchunked digit run past seven"),
                       ("Aesthetic-Usability", "an interactive element with no focus ring")],
                 at=[21.85, 22.93, 24.02],
                 caption="Mechanical, source-decidable, and fast enough for a "
                         "pre-commit hook."),
            dict(type="claim", start=29.3, dur=8.2, end=37.4,
                 line="It does not judge whether the screen answers the right question."),
            dict(type="panel", start=37.3, dur=8.4, end=45.6,
                 eyebrow="The honest boundary",
                 rows=[("The gate", "eight laws, exit 1, every commit"),
                       ("The human", "whether the flow makes sense at all")],
                 at=[39.08, 40.17],
                 caption="A fast gate, not a substitute for design review. "
                         "The repo says so itself."),
            dict(type="claim", start=45.5, dur=10.1, end=55.5,
                 line="Thirty laws you can read. Eight a machine can hold you to."),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 ux-laws", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # ----------------------------------------------------------- accessibility
    "accessibility": dict(
        duration=60.0,
        vo=[("a11y-1", 1.10), ("a11y-2", 6.50), ("a11y-3", 14.50),
            ("a11y-4", 23.00), ("a11y-5", 32.00), ("a11y-6", 41.00),
            ("a11y-7", 48.50), ("a11y-8", 55.80)],
        sfx=[("drop", 5.46), ("tile", 15.29), ("tile", 23.47), ("tile", 32.56),
             ("tile", 41.46), ("bell", 55.63)],
        scenes=[
            dict(type="claim", start=0.0, dur=6.0, end=5.5,
                 line="An unmuted autoplay masks a screen reader."),
            dict(type="panel", start=5.4, dur=8.6, end=13.9,
                 eyebrow="Three the source can prove on its own",
                 rows=[("media-autoplay-sound", "WCAG 1.4.2 \u2014 it talks over the reader"),
                       ("video-missing-captions", "WCAG 1.2.2 \u2014 audio with no captions"),
                       ("media-missing-controls", "WCAG 2.1.1 \u2014 no keyboard controls")],
                 at=[6.55, 7.64, 8.74],
                 caption="No browser. No DOM. Just the markup, read carefully."),
            dict(type="chips", start=13.8, dur=8.6, end=22.3,
                 eyebrow="Twenty rules",
                 items=["img-missing-alt", "input-missing-label", "div-onclick",
                        "tabindex-positive", "heading-skip", "dialog-missing-close",
                        "color-only-state", "motion-no-reduce-guard"],
                 at=[15.29, 15.84, 16.38, 16.93, 17.47, 18.03, 18.58, 19.12],
                 caption="Each one names the element, the line, and the rule it broke."),
            dict(type="panel", start=22.2, dur=9.2, end=31.3,
                 eyebrow="Six of the twenty repair themselves",
                 rows=[("--fix", "lang detection, redundant aria, tabindex"),
                       ("and the rest", "reported, never guessed at")],
                 at=[23.47, 24.57],
                 caption="A fix is only automatic where there is exactly one "
                         "safe repair."),
            dict(type="claim", start=31.2, dur=9.3, end=40.4,
                 line="And the same rule, pointed the other way, writes the CSS."),
            dict(type="panel", start=40.3, dur=7.8, end=48.0,
                 eyebrow="Audit, then make",
                 rows=[("The rule", "body text with tracking too tight to read"),
                       ("The counterpart", "CSS at the WCAG 1.4.12 minimums")],
                 at=[41.46, 42.55],
                 caption="Ship the fix as a reader-facing toggle, not just a warning."),
            dict(type="claim", start=47.9, dur=7.7, end=55.5,
                 line="Standard library only. Exit 1 on any finding."),
            dict(type="outro", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 accessibility", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
}


# ---------------------------------------------------------------------------
# HTML emission
# ---------------------------------------------------------------------------
def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def css(f: dict) -> str:
    """Canvas-specific stylesheet. Everything else is shared."""
    pad, split = f["pad"], f["split"]
    fig = f["fig"]
    return f"""
    :root {{
      --ink: {INK}; --ink-soft: {INK_SOFT}; --blue: {BLUE};
      --line: {LINE}; --paper: {PAPER}; --navy: {NAVY};
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: {f['w']}px; height: {f['h']}px; overflow: hidden;
                  background: var(--paper); }}
    #root {{ position: relative; width: 100%; height: 100%; overflow: hidden;
             background: var(--paper); color: var(--ink);
             font-family: "Roboto", system-ui, sans-serif; }}

    /* Background: the site's own hero wash, raised to video intensity, over a
       faint brand-tinted grid so the light canvas is not a blank slide. */
    .bg {{ position: absolute; inset: 0; background: var(--paper); }}
    .bg-grid {{ position: absolute; inset: 0; opacity: .55;
      background-image: radial-gradient(rgba(0,114,178,.14) 1.6px, transparent 1.7px);
      background-size: 44px 44px; }}
    .bg-wash {{ position: absolute; top: {-int(f['h'] * .38)}px; left: 50%;
      width: {int(f['w'] * 1.25)}px; height: {int(f['h'] * 1.4)}px;
      margin-left: {-int(f['w'] * .625)}px;
      background: radial-gradient(closest-side, rgba(127,209,255,.55) 0%,
        rgba(127,209,255,.22) 45%, rgba(127,209,255,0) 78%); }}

    .inner {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    .stage {{ position: absolute; inset: 0; display: flex; align-items: center;
              justify-content: center; padding: {pad}px; }}
    .col {{ display: flex; flex-direction: column; align-items: center;
            justify-content: center; width: 100%; }}

    .eyebrow {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f['eyebrow']}px; font-weight: 500; letter-spacing: .2em;
      color: var(--navy); text-transform: uppercase; text-align: center; }}
    .rule {{ height: 3px; background: var(--blue); transform-origin: center; }}
    /* `text-wrap: balance` rather than shorter captions. The same sentence
       that sits on one comfortable line in landscape wraps three times in
       portrait, where the column is 936px instead of 1712 and the type is
       larger: 34 captions across the two social formats ended on a one-word
       line, against none in landscape. Shortening the text would have fixed
       the social cuts by damaging the landscape one, which is the format the
       site embeds -- a typographic problem deserves a typographic answer.
       Chrome balances up to a handful of lines, which is all any of these
       need. */
    .caption {{ font-size: {f['body']}px; font-weight: 400; line-height: 1.34;
      color: var(--ink-soft); text-align: center; text-wrap: balance;
      max-width: {f['w'] - 2 * pad}px; }}

    /* Scene 1: the claim */
    .claim {{ font-family: "Roboto Serif"; font-size: {f['hero']}px; font-weight: 600;
      letter-spacing: -.02em; line-height: 1.08; text-align: center;
      max-width: {f['w'] - 2 * pad}px; color: var(--ink); }}

    /* The site's card, drawn at 2px for video instead of the web's 1px */
    .card {{ border: 2px solid var(--line); border-radius: 20px;
      background: var(--paper); padding: 22px;
      box-shadow: 0 26px 64px rgba(0,60,93,.14); }}

    .figbox {{ position: relative; width: {fig}px; overflow: hidden; }}
    .figbox img {{ position: absolute; top: 0; left: 0; display: block;
      width: {fig}px; height: 100%; }}
    .gray-wrap {{ position: absolute; inset: 0; clip-path: inset(0% 100% 0% 0%); }}
    .fig-gray {{ filter: grayscale(1) contrast(1.03); }}
    .wipe-edge {{ position: absolute; top: 0; left: 0; width: 4px; height: 100%;
      background: var(--blue); opacity: 0; }}

    .loop-wrap {{ display: flex; {'flex-direction: row; align-items: center; gap: 88px;'
                                 if split else 'flex-direction: column; align-items: center; gap: 46px;'}
      justify-content: center; width: 100%; }}
    .loop-text {{ display: flex; flex-direction: column;
      align-items: {'flex-start' if split else 'center'};
      text-align: {'left' if split else 'center'};
      {'width: ' + str(f['w'] - 2 * pad - fig - 132) + 'px;' if split
       else 'width: ' + str(f['w'] - 2 * pad) + 'px;'} }}
    .loop-text .eyebrow, .loop-text .caption {{ text-align: {'left' if split else 'center'}; }}
    .steps {{ display: inline-flex; flex-direction: column; align-items: flex-start; }}
    .step {{ display: flex; align-items: baseline; gap: 18px;
      font-family: "Roboto Mono", ui-monospace, monospace; font-size: {f['mono']}px;
      font-weight: 500; line-height: 1.55; color: var(--ink); }}
    .step-n {{ color: var(--blue); font-weight: 600; }}
    .step-dim {{ opacity: .32; }}

    .grid {{ display: grid; gap: 22px; justify-content: center; }}
    .tile {{ overflow: hidden; border: 2px solid var(--line); border-radius: 16px;
      background: var(--paper); padding: 9px; }}
    .tile img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}

    .chips {{ display: flex; flex-wrap: wrap; gap: 16px; justify-content: center;
      max-width: {f['w'] - 2 * pad}px; }}
    .chip {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f['chip']}px; font-weight: 500; color: var(--ink);
      border: 2px solid var(--line); border-radius: 999px;
      padding: {int(f['chip'] * .42)}px {int(f['chip'] * .9)}px;
      background: var(--paper); white-space: nowrap; }}

    .panel {{ width: {min(f['w'] - 2 * pad, 1280)}px; }}
    .prow {{ display: flex; align-items: baseline;
      {'flex-direction: row; gap: 28px;' if split else 'flex-direction: column; gap: 6px;'}
      padding: {int(f['body'] * .62)}px 0; border-bottom: 2px solid var(--line); }}
    .prow:last-child {{ border-bottom: 0; }}
    .pk {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f['mono']}px; font-weight: 600; color: var(--blue);
      {'min-width: 380px;' if split else ''} white-space: nowrap; }}
    .pv {{ font-size: {f['h2']}px; font-weight: 400; color: var(--ink);
      line-height: 1.3; }}

    /* held: one sentence, larger than a claim, for the films that have
       fewer things to say and more time to say them. */
    .held {{ font-family: "Roboto Serif"; font-size: {int(f['hero'] * .72)}px;
      font-weight: 600; line-height: 1.22; letter-spacing: -.015em;
      color: var(--ink); text-align: center; text-wrap: balance;
      max-width: {int((f['w'] - 2 * pad) * .86)}px; margin: 0 auto; }}

    /* flow: a document moving through stages and arriving as something. */
    .flow {{ display: flex; align-items: stretch; justify-content: center;
      flex-wrap: wrap; gap: {int(f['chip'] * .36)}px; }}
    .flow-step {{ display: flex; flex-direction: column; gap: 4px;
      border: 2px solid var(--line); border-radius: 14px;
      background: var(--paper); padding: {int(f['chip'] * .5)}px
      {int(f['chip'] * .66)}px; }}
    .flow-name {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f['chip'] * .92)}px; font-weight: 600; color: var(--blue); }}
    .flow-under {{ font-size: {int(f['chip'] * .72)}px; color: var(--ink-soft); }}
    .flow-arrow {{ align-self: center; font-size: {int(f['chip'] * 1.3)}px;
      color: var(--line); line-height: 1; }}

    /* versus: two halves of one idea, with the divider between them. */
    .versus {{ display: flex; align-items: stretch; gap: {int(f['body'] * .9)}px;
      width: {min(f['w'] - 2 * pad, 1280)}px; }}
    .vs-half {{ flex: 1; display: flex; flex-direction: column; gap: 10px;
      border: 2px solid var(--line); border-radius: 18px;
      background: var(--paper); padding: {int(f['body'] * .8)}px; }}
    .vs-key {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f['mono']}px; font-weight: 600; color: var(--blue); }}
    .vs-val {{ font-size: {int(f['h2'] * .86)}px; line-height: 1.3;
      color: var(--ink); text-wrap: balance; }}
    .vs-bar {{ width: 3px; background: var(--line); border-radius: 2px;
      transform-origin: center; }}

    /* code: the source a finding is about, with the line marked. */
    .codecard {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f['mono'] * .92)}px; line-height: 1.75;
      width: {min(f['w'] - 2 * pad, 1280)}px; text-align: left; }}
    .code-line {{ display: flex; gap: {int(f['mono'] * .9)}px;
      border-radius: 6px; padding: 1px {int(f['mono'] * .4)}px; }}
    .code-n {{ color: var(--line); min-width: {int(f['mono'] * 1.5)}px;
      text-align: right; }}
    .code-t {{ color: var(--ink); white-space: pre; }}
    .code-line.bad .code-t {{ color: var(--ink); font-weight: 600; }}

    /* verify: a claim, and the value it was checked against. */
    .verify {{ width: {min(f['w'] - 2 * pad, 1280)}px; }}
    .vrow {{ display: flex; align-items: baseline; gap: 14px;
      padding: {int(f['body'] * .5)}px 0; border-bottom: 2px solid var(--line); }}
    .vrow:last-child {{ border-bottom: 0; }}
    .vclaim {{ font-size: {int(f['h2'] * .82)}px; color: var(--ink);
      white-space: nowrap; }}
    .vdots {{ flex: 1; border-bottom: 2px dotted var(--line);
      transform: translateY(-.25em); }}
    .vvalue {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f['mono']}px; font-weight: 600; color: var(--blue);
      white-space: nowrap; }}

    .shotcard img {{ display: block; border-radius: 8px; }}
    .viewport {{ position: relative; overflow: hidden; border-radius: 8px; }}

    #logo {{ display: block; width: {int(f['hero'] * 2.0)}px;
      height: {int(f['hero'] * 2.0)}px; object-fit: contain; }}
    #mark {{ font-family: "Roboto Serif"; font-size: {int(f['hero'] * .84)}px;
      font-weight: 600; letter-spacing: -.02em; color: var(--ink);
      margin-top: {int(f['hero'] * .3)}px; text-align: center; }}
    #oline {{ font-size: {f['h2']}px; color: var(--ink-soft);
      margin-top: {int(f['hero'] * .22)}px; text-align: center; }}
    #ourl {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f['eyebrow'] * .96)}px; font-weight: 500; letter-spacing: .06em;
      color: var(--blue); margin-top: {int(f['hero'] * .3)}px; }}

    #rail-l, #rail-r {{ position: absolute; top: {int(pad * .48)}px;
      font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f['eyebrow'] * .9)}px; font-weight: 500; letter-spacing: .22em; }}
    #rail-l {{ left: {pad}px; color: var(--blue); }}
    #rail-r {{ right: {pad}px; letter-spacing: .1em; color: var(--ink-soft); }}
    #rail-line {{ position: absolute; left: {pad}px; top: {f['h'] - int(pad * .52)}px;
      width: {f['w'] - 2 * pad}px; height: 2px; background: var(--line);
      transform-origin: left center; }}
    """


def scene_html(sc: dict, f: dict, i: int) -> str:
    """Body markup for one scene. Timing lives on the wrapper, not here."""
    t = sc["type"]
    head = (f'<p class="eyebrow" id="s{i}-eyebrow">{esc(sc["eyebrow"])}</p>'
            f'<div class="rule" id="s{i}-rule" style="width:132px;margin:18px 0 '
            f'{int(f["body"] * 1.0)}px"></div>') if sc.get("eyebrow") else ""
    cap = (f'<p class="caption" id="s{i}-caption" '
           f'style="margin-top:{int(f["body"] * 1.05)}px">{esc(sc["caption"])}</p>'
           ) if sc.get("caption") and t not in ("loop", "cvd") else ""

    if t == "held":
        # One sentence, bigger than a claim, on screen long enough to read
        # twice. The `ui` film is four of these and nothing else: the
        # smallest package gets the fewest words, held longest.
        return (f'<div class="stage"><div class="col">'
                f'<h1 class="held" id="s{i}-held">{esc(sc["line"])}</h1>'
                f'<div class="rule" id="s{i}-rule" style="width:96px;'
                f'margin:{int(f["body"] * 1.4)}px auto 0"></div>'
                f'</div></div>')

    if t == "flow":
        # Stages left to right, with an arrow between. A document moving
        # through nine tools and arriving as a site is a sequence, so the
        # scene is a sequence.
        parts = []
        for k, (name, under) in enumerate(sc["stages"], 1):
            arrow = (f'<span class="flow-arrow" id="s{i}-a{k}">&rsaquo;</span>'
                     if k > 1 else "")
            parts.append(
                f'{arrow}<div class="flow-step" id="s{i}-f{k}">'
                f'<span class="flow-name">{esc(name)}</span>'
                f'<span class="flow-under">{esc(under)}</span></div>')
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="flow">{"".join(parts)}</div>{cap}</div></div>')

    if t == "versus":
        # Two halves and a divider. Used where the subject is a pair:
        # a command and the form it became, sound read in two directions.
        left, right = sc["left"], sc["right"]
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="versus">'
                f'<div class="vs-half" id="s{i}-vl">'
                f'<p class="vs-key">{esc(left[0])}</p>'
                f'<p class="vs-val">{esc(left[1])}</p></div>'
                f'<div class="vs-bar" id="s{i}-vbar"></div>'
                f'<div class="vs-half" id="s{i}-vr">'
                f'<p class="vs-key">{esc(right[0])}</p>'
                f'<p class="vs-val">{esc(right[1])}</p></div>'
                f'</div>{cap}</div></div>')

    if t == "code":
        # Markup on screen with the offending lines marked. An accessibility
        # finding is a statement about a line of source, so the film shows
        # the line of source.
        rows = "".join(
            f'<div class="code-line{" bad" if n in sc.get("mark", ()) else ""}" '
            f'id="s{i}-c{n}"><span class="code-n">{n}</span>'
            f'<span class="code-t">{esc(line)}</span></div>'
            for n, line in enumerate(sc["code"], 1))
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="card codecard" id="s{i}-code">{rows}</div>'
                f'{cap}</div></div>')

    if t == "verify":
        # A claim and what it was checked against, the value arriving after
        # the claim. The `video` film audits itself while it plays.
        rows = "".join(
            f'<div class="vrow" id="s{i}-v{k}">'
            f'<span class="vclaim">{esc(claim)}</span>'
            f'<span class="vdots"></span>'
            f'<span class="vvalue" id="s{i}-vv{k}">{esc(value)}</span></div>'
            for k, (claim, value) in enumerate(sc["claims"], 1))
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="card verify" id="s{i}-verify">{rows}</div>'
                f'{cap}</div></div>')

    if t == "claim":
        return (f'<div class="stage"><div class="col">'
                f'<h1 class="claim" id="s{i}-line">{esc(sc["line"])}</h1>'
                f'<div class="rule" id="s{i}-rule" '
                f'style="width:220px;margin-top:{int(f["hero"] * .42)}px"></div>'
                f'</div></div>')

    if t == "loop":
        h = int(f["fig"] / sc["ratio"])
        steps = '<div class="steps">' + "".join(
            f'<div class="step" id="s{i}-step{n}"><span class="step-n">{esc(k)}</span>'
            f'<span>{esc(v)}</span></div>'
            for n, (k, v) in enumerate(sc["steps"], 1)) + '</div>'
        return (f'<div class="stage"><div class="loop-wrap">'
                f'<div class="card" id="s{i}-card"><div class="figbox" '
                f'style="height:{h}px">'
                f'<img src="assets/{sc["fig"]}" alt="">'
                f'<div class="gray-wrap" id="s{i}-gray">'
                f'<img class="fig-gray" src="assets/{sc["gray"]}" alt=""></div>'
                f'<div class="wipe-edge" id="s{i}-wipe"></div>'
                f'</div></div>'
                f'<div class="loop-text">{head}{steps}'
                f'<p class="caption" id="s{i}-caption" '
                f'style="margin-top:{int(f["body"] * 1.2)}px">{esc(sc["caption"])}</p>'
                f'</div></div></div>')

    if t == "cvd":
        h = int(f["fig"] / sc["ratio"])
        # Every simulation sits on the one below it, so each wipe hands the
        # frame to the next pair of eyes without a cut.
        layers = "".join(
            f'<div class="gray-wrap" id="s{i}-w{k}">'
            f'<img src="assets/{src}" alt=""></div>'
            for k, (_, _, src, _) in enumerate(sc["stages"], 1))
        steps = '<div class="steps">' + "".join(
            f'<div class="step step-dim" id="s{i}-step{k}">'
            f'<span class="step-n">{esc(num)}</span><span>{esc(lbl)}</span></div>'
            for k, (num, lbl, _, _) in enumerate(sc["stages"], 1)) + '</div>'
        return (f'<div class="stage"><div class="loop-wrap">'
                f'<div class="card" id="s{i}-card"><div class="figbox" '
                f'style="height:{h}px">'
                f'<img src="assets/{sc["base"]}" alt="">'
                f'{layers}'
                f'<div class="wipe-edge" id="s{i}-wipe"></div>'
                f'</div></div>'
                f'<div class="loop-text">{head}{steps}'
                f'<p class="caption" id="s{i}-caption" '
                f'style="margin-top:{int(f["body"] * 1.2)}px">{esc(sc["caption"])}</p>'
                f'</div></div></div>')

    if t == "grid":
        n = len(sc["images"])
        # A pair gets two columns and a bigger tile. It used to fall through to
        # the six-image case, which lays out three columns and fills two: the
        # pair sat a column's width left of centre, with the empty third
        # column as a margin nobody asked for, and each plate was capped at
        # the width that keeps six of them apart. On the two areas-of-control
        # maps that cap is the difference between reading the place names and
        # not.
        # `tile_cap`, not `cap`: `cap` is already the caption's HTML, built at
        # the top of this function, and the first version of this branch bound
        # the integer over it -- so the two maps grew, and the sentence under
        # them rendered as the word "760".
        if n <= 2:
            # A pair stacks in portrait and sits side by side everywhere else.
            # Side by side in a 1080-wide frame gives each tile 457px, which
            # is fine for a map and useless for a screenshot of a form: the
            # cli-gui pair came out as two grey rectangles. Stacked they get
            # the full 936, and portrait has the height to spare — it is the
            # one format where vertical room is what there is most of.
            tall = f["h"] > f["w"]
            cols = 1 if (n == 2 and tall) else n
            tile_cap = 960 if cols == 1 else 760
        else:
            cols = (4 if f["split"] else 2) if n == 4 else f["grid6"]
            tile_cap = 560
        rows = -(-n // cols)
        tw = min((f["w"] - 2 * f["pad"] - (cols - 1) * 22) // cols, tile_cap)
        th = int(tw * 0.75)
        # Reserve the eyebrow, the rule and a two-line caption, then let the
        # remaining height cap the tile. Without this the caption slides under
        # the bottom rail in landscape.
        reserve = int(f["eyebrow"] * 1.3 + f["body"] * 4.5 + 24)
        cap_h = (f["h"] - 2 * f["pad"] - reserve - (rows - 1) * 22) // rows
        if th > cap_h:
            th = max(150, cap_h)
            tw = int(th / 0.75)
        tiles = "".join(
            f'<div class="tile" id="s{i}-t{k}" style="width:{tw}px;height:{th}px">'
            f'<img src="assets/{src}" alt=""></div>'
            for k, src in enumerate(sc["images"], 1))
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="grid" style="grid-template-columns:repeat({cols},{tw}px)">'
                f'{tiles}</div>{cap}</div></div>')

    if t == "chips":
        chips = "".join(f'<span class="chip" id="s{i}-c{k}">{esc(v)}</span>'
                        for k, v in enumerate(sc["items"], 1))
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="chips">{chips}</div>{cap}</div></div>')

    if t == "panel":
        rows = "".join(
            f'<div class="prow" id="s{i}-r{k}"><span class="pk">{esc(a)}</span>'
            f'<span class="pv">{esc(b)}</span></div>'
            for k, (a, b) in enumerate(sc["rows"], 1))
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="card panel" id="s{i}-panel">{rows}</div>{cap}</div></div>')

    if t == "shot":
        reserve = int(f["eyebrow"] * 1.3 + f["body"] * 4.5 + 24)
        max_h = f["h"] - 2 * f["pad"] - reserve - 44
        iw = f["shot"]
        ih = int(iw / sc["ratio"])
        if sc.get("scroll"):
            view = min(max_h, int(iw * f["view"]))
            return (f'<div class="stage"><div class="col">{head}'
                    f'<div class="card shotcard" id="s{i}-shot">'
                    f'<div class="viewport" style="width:{iw}px;height:{view}px">'
                    f'<img id="s{i}-page" src="assets/{sc["src"]}" alt="" '
                    f'style="width:{iw}px;height:{ih}px"></div></div>'
                    f'{cap}</div></div>')
        if ih > max_h:
            ih = max_h
            iw = int(ih * sc["ratio"])
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="card shotcard" id="s{i}-shot">'
                f'<img src="assets/{sc["src"]}" alt="" '
                f'style="width:{iw}px;height:{ih}px;object-fit:contain"></div>'
                f'{cap}</div></div>')

    if t == "outro":
        return (f'<div class="stage"><div class="col">'
                f'<img id="logo" src="assets/{sc["logo"]}" alt="">'
                f'<p id="mark">{esc(sc["mark"])}</p>'
                f'<p id="oline">{esc(sc["line"])}</p>'
                f'<p id="ourl">{esc(sc["url"])}</p></div></div>')

    raise ValueError(t)


def scene_js(sc: dict, i: int, f: dict) -> list[str]:
    """Tweens for one scene, in global time. Entrances vary by element type so
    a scene has choreography rather than one repeated slide-up."""
    t, s, out = sc["type"], sc["start"], []
    if sc.get("eyebrow"):
        out.append(f'tl.fromTo("#s{i}-eyebrow",{{x:-26,opacity:0}},'
                   f'{{x:0,opacity:1,duration:.55,ease:"power2.out"}},{s + .3:.2f});')
        out.append(f'tl.fromTo("#s{i}-rule",{{scaleX:0}},'
                   f'{{scaleX:1,duration:.6,ease:"expo.out"}},{s + .5:.2f});')
    if sc.get("caption") and t not in ("loop", "cvd"):
        out.append(f'tl.fromTo("#s{i}-caption",{{y:16,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.55,ease:"power2.out"}},{s + .7:.2f});')

    if t == "claim":
        out.append(f'tl.fromTo("#s{i}-line",{{y:30,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.55,ease:"power3.out"}},{s + .2:.2f});')
        out.append(f'tl.fromTo("#s{i}-rule",{{scaleX:0,opacity:0}},'
                   f'{{scaleX:1,opacity:1,duration:.7,ease:"expo.out"}},{s + .55:.2f});')

    elif t == "loop":
        w = f["fig"]
        out.append(f'tl.fromTo("#s{i}-card",{{y:44,scale:.975,opacity:0}},'
                   f'{{y:0,scale:1,opacity:1,duration:.75,ease:"power3.out"}},{s + .1:.2f});')
        for k, at in enumerate(sc["step_at"], 1):  # beat-grid
            out.append(f'tl.fromTo("#s{i}-step{k}",{{y:16,opacity:0}},'
                       f'{{y:0,opacity:1,duration:.45,ease:"power2.out"}},{at:.2f});')
        wa, wd = sc["wipe_at"], sc["wipe_dur"]  # beat-locked
        out.append(f'tl.fromTo("#s{i}-gray",{{clipPath:"inset(0% 100% 0% 0%)"}},'
                   f'{{clipPath:"inset(0% 0% 0% 0%)",duration:{wd},'
                   f'ease:"power2.inOut"}},{wa:.2f});')
        out.append(f'tl.fromTo("#s{i}-wipe",{{x:0,opacity:0}},'
                   f'{{opacity:.9,duration:.18,ease:"power1.out"}},{wa:.2f});')
        out.append(f'tl.to("#s{i}-wipe",{{x:{w - 4},duration:{wd},'
                   f'ease:"power2.inOut"}},{wa:.2f});')
        out.append(f'tl.to("#s{i}-wipe",{{opacity:0,duration:.22,ease:"power1.in"}},'
                   f'{wa + wd - .15:.2f});')
        out.append(f'tl.fromTo("#s{i}-caption",{{y:20,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.6,ease:"power2.out"}},'
                   f'{sc["caption_at"]:.2f});')

    elif t == "cvd":
        w, wd = f["fig"], sc["wipe_dur"]
        out.append(f'tl.fromTo("#s{i}-card",{{y:44,scale:.975,opacity:0}},'
                   f'{{y:0,scale:1,opacity:1,duration:.75,ease:"power3.out"}},{s + .1:.2f});')
        for k, (_, _, _, at) in enumerate(sc["stages"], 1):
            # beat-grid; the grayscale stage is beat-locked to the 8.74s cue.
            out.append(f'tl.fromTo("#s{i}-w{k}",{{clipPath:"inset(0% 100% 0% 0%)"}},'
                       f'{{clipPath:"inset(0% 0% 0% 0%)",duration:{wd},'
                       f'ease:"power2.inOut"}},{at:.2f});')
            out.append(f'tl.to("#s{i}-step{k}",{{opacity:1,duration:.3,'
                       f'ease:"power1.out"}},{at:.2f});')
            out.append(f'tl.fromTo("#s{i}-wipe",{{x:0,opacity:0}},'
                       f'{{opacity:.9,duration:.14,ease:"power1.out"}},{at:.2f});')
            out.append(f'tl.to("#s{i}-wipe",{{x:{w - 4},duration:{wd},'
                       f'ease:"power2.inOut"}},{at:.2f});')
            out.append(f'tl.to("#s{i}-wipe",{{opacity:0,duration:.16,'
                       f'ease:"power1.in"}},{at + wd - .1:.2f});')
        out.append(f'tl.fromTo("#s{i}-caption",{{y:20,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.6,ease:"power2.out"}},'
                   f'{sc["caption_at"]:.2f});')

    elif t == "grid":
        for k, at in enumerate(sc["at"], 1):  # beat-grid
            out.append(f'tl.fromTo("#s{i}-t{k}",{{y:22,scale:.955,opacity:0}},'
                       f'{{y:0,scale:1,opacity:1,duration:.5,ease:"power3.out"}},{at:.2f});')

    elif t == "chips":
        for k, at in enumerate(sc["at"], 1):  # beat-grid
            out.append(f'tl.fromTo("#s{i}-c{k}",{{y:14,scale:.94,opacity:0}},'
                       f'{{y:0,scale:1,opacity:1,duration:.42,ease:"back.out(1.3)"}},{at:.2f});')

    elif t == "panel":
        out.append(f'tl.fromTo("#s{i}-panel",{{y:34,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.7,ease:"power3.out"}},{s + .25:.2f});')
        for k, at in enumerate(sc["at"], 1):  # beat-grid
            out.append(f'tl.fromTo("#s{i}-r{k}",{{x:22,opacity:0}},'
                       f'{{x:0,opacity:1,duration:.5,ease:"power2.out"}},{at:.2f});')

    elif t == "shot":
        out.append(f'tl.fromTo("#s{i}-shot",{{y:48,scale:.97,opacity:0}},'
                   f'{{y:0,scale:1,opacity:1,duration:.8,ease:"power3.out"}},{sc["at"]:.2f});')
        if sc.get("scroll"):
            iw = f["shot"]
            ih = int(iw / sc["ratio"])
            reserve = int(f["eyebrow"] * 1.3 + f["body"] * 4.5 + 24)
            view = min(f["h"] - 2 * f["pad"] - reserve - 44, int(iw * f["view"]))
            travel = max(0, ih - view)
            begin = sc["at"] + 0.7
            span = round(sc["end"] - begin - 0.9, 2)
            if travel and span > 0.8:
                out.append(f'tl.fromTo("#s{i}-page",{{y:0}},{{y:{-travel},'
                           f'duration:{span},ease:"power1.inOut"}},{begin:.2f});')

    elif t == "held":
        out.append(f'tl.fromTo("#s{i}-held",{{y:30,opacity:0}},'
                   f'{{y:0,opacity:1,duration:1.0,ease:"power3.out"}},{s + .25:.2f});')
        out.append(f'tl.fromTo("#s{i}-rule",{{scaleX:0}},'
                   f'{{scaleX:1,duration:.7,ease:"expo.out"}},{s + .9:.2f});')

    elif t == "flow":
        for k, at in enumerate(sc["at"], 1):
            if k > 1:
                out.append(f'tl.fromTo("#s{i}-a{k}",{{opacity:0,x:-8}},'
                           f'{{opacity:1,x:0,duration:.3,ease:"power2.out"}},{at - .12:.2f});')
            out.append(f'tl.fromTo("#s{i}-f{k}",{{y:14,opacity:0}},'
                       f'{{y:0,opacity:1,duration:.42,ease:"back.out(1.6)"}},{at:.2f});')

    elif t == "versus":
        a, b = sc["at"]
        out.append(f'tl.fromTo("#s{i}-vl",{{x:-34,opacity:0}},'
                   f'{{x:0,opacity:1,duration:.6,ease:"power3.out"}},{a:.2f});')
        out.append(f'tl.fromTo("#s{i}-vbar",{{scaleY:0}},'
                   f'{{scaleY:1,duration:.5,ease:"expo.out"}},{a + .2:.2f});')
        out.append(f'tl.fromTo("#s{i}-vr",{{x:34,opacity:0}},'
                   f'{{x:0,opacity:1,duration:.6,ease:"power3.out"}},{b:.2f});')

    elif t == "code":
        for n, at in enumerate(sc["at"], 1):
            out.append(f'tl.fromTo("#s{i}-c{n}",{{opacity:0}},'
                       f'{{opacity:1,duration:.22}},{at:.2f});')
        for n, at in sc.get("flag", []):
            out.append(f'tl.fromTo("#s{i}-c{n}",{{backgroundColor:"rgba(0,0,0,0)"}},'
                       f'{{backgroundColor:"rgba(209,46,46,.12)",duration:.45,'
                       f'ease:"power2.out"}},{at:.2f});')

    elif t == "verify":
        for k, (at_claim, at_value) in enumerate(sc["at"], 1):
            out.append(f'tl.fromTo("#s{i}-v{k}",{{x:-20,opacity:0}},'
                       f'{{x:0,opacity:1,duration:.45,ease:"power2.out"}},{at_claim:.2f});')
            out.append(f'tl.fromTo("#s{i}-vv{k}",{{opacity:0,scale:.8}},'
                       f'{{opacity:1,scale:1,duration:.35,ease:"back.out(2)"}},{at_value:.2f});')

    elif t == "outro":
        out.append(f'tl.fromTo("#logo",{{scale:.88,opacity:0}},'
                   f'{{scale:1,opacity:1,duration:.7,ease:"power3.out"}},{s + .2:.2f});')
        out.append(f'tl.fromTo("#mark",{{y:24,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.6,ease:"power3.out"}},{s + .45:.2f});')
        out.append(f'tl.fromTo("#oline",{{y:18,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.6,ease:"power2.out"}},{s + .75:.2f});')
        out.append(f'tl.fromTo("#ourl",{{opacity:0}},'
                   f'{{opacity:1,duration:.55,ease:"power1.out"}},{s + 1.05:.2f});')
    return out


SFX_FILES = {
    "drop": ("sfx/interface/drop_001.ogg", 0.11, 0.55),
    "wipe": ("sfx/impact/impactSoft_medium_001.ogg", 0.19, 0.50),
    "tile": ("sfx/interface/drop_001.ogg", 0.11, 0.50),
    "bell": ("sfx/impact/impactBell_heavy_000.ogg", 1.48, 0.62),
}


def vo_duration(name: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(ASSETS / f"vo-{name}.wav")],
        capture_output=True, text=True, check=True).stdout.strip()
    return round(float(out), 3)


#: The cuts of every film. English and French are equal citizens: the same
#: spec, the same timing, the same beat grid, and `films_fr.translate` swaps
#: the words on the way out.
LANGS = ("en", "fr")


def project_name(film_key: str, lang: str, fmt_key: str) -> str:
    """Where one cut is emitted. English keeps its old directory name.

    `sprezzature-landscape` rather than `sprezzature-en-landscape`, because
    that path is in the deploy notes, in the upload list and in this
    repository's own tests. A rename would have been tidier and would have
    cost a morning of chasing it through files that have nothing to do with
    language.
    """
    return f"{film_key}-{fmt_key}" if lang == "en" else f"{film_key}-{lang}-{fmt_key}"



def voice_track(film_key: str, spec: dict, lang: str) -> list[tuple[str, float]]:
    """The voice files this cut plays, as (stem, start) pairs.

    One file, not one per line. The films used to lay out eight separate WAVs
    at eight hard-coded times, each synthesised by its own shell call; since
    2026-10-26 `narrate_films.py` asks `sprezzature-audio` for the whole
    reading at once and gets back a single track plus the cues that describe
    it. The pauses inside it are the library's, and the library refuses a
    result whose timeline disagrees with its own audio — so the agreement
    between what is heard and what is captioned is now proved rather than
    reproduced by two pieces of arithmetic that happened to match.

    The track starts at the first line's grid time, because the engine drops a
    leading pause: a narration begins when it begins. That silence is the
    film's to carry.

    The three retired group films keep the old per-line shape; they are not
    re-cut and not re-narrated.
    """
    lines = make_captions.FILMS.get(film_key, {}).get(lang)
    if not lines or len(lines) < 8:
        return list(spec["vo"])
    return [(f"{film_key}.{lang}", lines[0][0])]


def emit(film_key: str, spec: dict, fmt_key: str, lang: str = "en") -> pathlib.Path:
    f = FORMATS[fmt_key]
    spec = in_language(spec, lang, film_key)
    scenes, dur = spec["scenes"], spec["duration"]

    body = "\n".join(
        f'<section id="s{i}" class="clip" data-start="{sc["start"]}" '
        f'data-duration="{sc["dur"]}" data-track-index="{i}">'
        f'<div class="inner" id="s{i}-inner">{scene_html(sc, f, i)}</div></section>'
        for i, sc in enumerate(scenes, 1))

    rails_start = scenes[0]["end"]
    rails = (f'<div id="rails" class="clip" data-start="{rails_start}" '
             f'data-duration="{round(dur - rails_start, 2)}" data-track-index="90">'
             f'<div class="inner" id="rails-inner">'
             f'<p id="rail-l">Sprezzature</p><p id="rail-r">sprezzature.ai</p>'
             f'<div id="rail-line"></div></div></div>')

    # Audio. Voice on its own lane; each overlapping SFX gets its own index.
    audio = [f'<audio id="bgm" data-start="0" data-duration="{dur}" '
             f'data-track-index="10" data-volume="1" src="assets/music/{MUSIC}"></audio>']
    duck = []
    for name, at in voice_track(film_key, spec, lang):
        d = vo_duration(name)
        audio.append(f'<audio id="vo-{name}" data-start="{at}" data-duration="{d}" '
                     f'data-track-index="11" data-volume="1" '
                     f'src="assets/vo-{name}.wav"></audio>')
        duck.append((at, at + d))
    for n, (kind, at) in enumerate(spec["sfx"]):
        src, sd, vol = SFX_FILES[kind]
        audio.append(f'<audio id="sfx-{n}" data-start="{at}" data-duration="{sd}" '
                     f'data-track-index="{12 + n}" data-volume="{vol}" '
                     f'src="assets/{src}"></audio>')

    # Music: in, duck across the whole narrated stretch, lift once the voice is
    # done, fade out on the held frame.
    first_vo, last_vo = duck[0][0], duck[-1][1]
    js = ['tl.fromTo("#bgm",{volume:0},{volume:.3,duration:.8,ease:"power1.out"},0);',
          f'tl.to("#bgm",{{volume:.13,duration:.35,ease:"power1.inOut"}},{max(0.85, first_vo - .35):.2f});',
          f'tl.to("#bgm",{{volume:.27,duration:.6,ease:"power1.inOut"}},{last_vo + .15:.2f});',
          f'tl.to("#bgm",{{volume:0,duration:.9,ease:"power1.in"}},{dur - 1.0:.2f});']

    # Crossfades: clip windows overlap 0.6s and the incoming scene, later in the
    # DOM, fades up over the outgoing one.
    for i, sc in enumerate(scenes, 1):
        if i == 1:
            js.append(f'tl.to("#s1-inner",{{opacity:0,duration:.6,ease:"power1.inOut"}},'
                      f'{sc["end"]:.2f});')
        else:
            js.append(f'tl.fromTo("#s{i}-inner",{{opacity:0}},'
                      f'{{opacity:1,duration:.6,ease:"power1.inOut"}},{sc["start"]:.2f});')
            if i < len(scenes):
                js.append(f'tl.to("#s{i}-inner",{{opacity:0,duration:.6,'
                          f'ease:"power1.inOut"}},{sc["end"]:.2f});')
        js += scene_js(sc, i, f)

    js.append(f'tl.fromTo("#rails-inner",{{opacity:0}},{{opacity:1,duration:.6,'
              f'ease:"power1.inOut"}},{rails_start:.2f});')
    js.append(f'tl.fromTo("#rail-line",{{scaleX:0}},{{scaleX:1,duration:1.1,'
              f'ease:"expo.out"}},{rails_start + .2:.2f});')

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={f['w']}, height={f['h']}" />
<title>{esc(film_key)} — {fmt_key}</title>
<script src="assets/vendor/gsap.min.js"></script>
<script src="assets/music/audio-data.js"></script>
<style>
/* The project's three-Roboto rule, self-hosted, so the render stays offline. */
@font-face {{ font-family:"Roboto"; src:url("assets/fonts/Roboto-Variable.woff2") format("woff2");
  font-weight:100 900; font-style:normal; font-display:block; }}
@font-face {{ font-family:"Roboto Serif"; src:url("assets/fonts/Roboto-Serif-Variable.woff2") format("woff2");
  font-weight:100 900; font-style:normal; font-display:block; }}
@font-face {{ font-family:"Roboto Mono"; src:url("assets/fonts/Roboto-Mono-Variable.woff2") format("woff2");
  font-weight:100 700; font-style:normal; font-display:block; }}
{css(f)}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur}"
     data-width="{f['w']}" data-height="{f['h']}" data-fps="30">
  <div class="bg"><div class="bg-grid"></div><div class="bg-wash" id="wash"></div></div>
{body}
{rails}
{chr(10).join(audio)}
</div>
<script>
(function () {{
  var tl = gsap.timeline({{ paused: true }});
{chr(10).join('  ' + line for line in js)}

  /* Audio-reactive: pre-extracted bands let the wash and the card breathe with
     the bed. Nothing here touches type size or position. */
  var AD = window.AUDIO_DATA;
  if (AD && AD.frames && AD.frames.length) {{
    var wash = document.getElementById("wash");
    var total = Math.min(AD.totalFrames, Math.floor({dur} * AD.fps));
    var cards = document.querySelectorAll(".card");
    var mark = document.getElementById("mark");
    var apply = function (fr) {{
      return function () {{
        var rms = fr.rms, bass = fr.b[0], treble = fr.b[2];
        wash.style.opacity = (0.72 + rms * 0.45).toFixed(3);
        wash.style.transform = "scale(" + (1 + bass * 0.05).toFixed(4) + ")";
        var sh = "0 " + (22 + bass * 16).toFixed(1) + "px " + (56 + bass * 26).toFixed(1) +
          "px rgba(0,60,93," + (0.12 + bass * 0.07).toFixed(3) + ")";
        for (var c = 0; c < cards.length; c++) {{ cards[c].style.boxShadow = sh; }}
        if (mark) {{
          mark.style.textShadow = "0 0 " + (10 + treble * 26).toFixed(1) +
            "px rgba(0,114,178," + (0.05 + treble * 0.16).toFixed(3) + ")";
        }}
      }};
    }};
    for (var fr = 0; fr < total; fr++) {{ tl.call(apply(AD.frames[fr]), [], fr / AD.fps); }}
  }}

  window.__timelines["main"] = tl;
  tl.seek(0);
}})();
</script>
</body>
</html>
"""
    d = FILMS_DIR / project_name(film_key, lang, fmt_key)
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html, encoding="utf-8")
    (d / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "components": "compositions/components",
                  "assets": "assets"},
        "media": {"autoProxy": True},
    }, indent=2) + "\n", encoding="utf-8")
    (d / "package.json").write_text(json.dumps({
        "name": project_name(film_key, lang, fmt_key), "private": True, "type": "module",
        "scripts": {"check": "npx --yes hyperframes@0.8.46 check",
                    "render": "npx --yes hyperframes@0.8.46 render"},
    }, indent=2) + "\n", encoding="utf-8")
    link = d / "assets"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to("../../_assets")
    return d


# What a project directory holds besides `renders/`. Listed rather than
# inferred so that a new generated file has to be added here on purpose.
GENERATED = ("index.html", "package.json", "hyperframes.json", "assets")


def clean(keep: set[pathlib.Path]) -> None:
    """Clear the generated half of every project, and drop stale projects.

    `main` used to `rmtree(FILMS_DIR)`, which also deleted every `renders/`
    directory under it. That is thirty-seven seconds of GPU per film per
    format thrown away for a one-line change to a caption -- and the cost does
    not announce itself: the emit prints "42 projects" exactly as before, and
    the loss only shows up later, as an ffmpeg error on a file that was there
    an hour ago. A render is an expensive output of a cheap input, so it
    outlives the input.
    """
    if not FILMS_DIR.exists():
        return
    for d in sorted(FILMS_DIR.iterdir()):
        if not d.is_dir():
            continue
        if d not in keep:
            shutil.rmtree(d)          # a film or format that no longer exists
            continue
        for name in GENERATED:
            target = d / name
            # The assets entry is a symlink; `is_dir` follows it and would
            # send rmtree into the shared _assets tree. Check the link first.
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
        comps = d / "compositions"
        if comps.is_dir():
            shutil.rmtree(comps)


def cuts() -> list[tuple[str, str]]:
    """Every (film, language) that gets emitted.

    The three eighteen-second group films are English-only: they were
    replaced on 2026-10-26 by one film per brick and are kept only until the
    copies on the server are deleted by hand. Giving them a French cut would
    mean translating 60 strings nobody will ever watch, and — worse —
    `films_fr` would then carry the vocabulary of three retired films
    alongside the vocabulary of eleven live ones, with nothing saying which
    was which.
    """
    return [
        (k, lang)
        for k, spec in FILMS.items()
        for lang in (LANGS if spec["duration"] >= 30 else ("en",))
    ]


def main() -> None:
    pairs = cuts()
    wanted = {
        FILMS_DIR / project_name(k, lang, fmt)
        for k, lang in pairs for fmt in FORMATS
    }
    clean(wanted)
    built = [
        emit(k, FILMS[k], fmt, lang) for k, lang in pairs for fmt in FORMATS
    ]
    for p in built:
        print(p.relative_to(ROOT))
    kept = sum(1 for d in FILMS_DIR.iterdir() if (d / "renders").is_dir())
    print(f"{len(built)} projects ({kept} with renders kept)")


if __name__ == "__main__":
    main()

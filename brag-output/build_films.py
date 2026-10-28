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
REWRITTEN = frozenset({"sprezzature", "colors", "ux-laws", "maps",
                       "figures", "publish", "audio", "cli-gui",
                       "accessibility", "ui", "video"})


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


#: Guy KAWASAKI's pitch, in the order he puts it in and in his words. A
#: viewer who does not know the package needs the pain before the cure, the
#: cure before the clever part, and something to do at the end.
#:
#: The labels are on screen for the whole minute, in the rail above the
#: frame, with the current one lit. A pitch deck can label its slides and a
#: film cannot, so the film labels the frame instead: at any second, somebody
#: wondering where this is going can see the answer without rewinding.
BEAT_LABEL = {
    "what":     L("What it is", "Ce que c'est"),
    "problem":  L("Problem", "Le problème"),
    "solution": L("Solution", "La solution"),
    "magic":    L("Underlying magic", "La mécanique"),
    "cta":      L("Your turn", "À vous"),
}
BEAT_ORDER = ("what", "problem", "solution", "magic", "cta")

#: The ask. Two of them, in the order of what they cost: a star is one click
#: from where the viewer already is, the site is a visit.
#:
#: The star points at the package the film is about, not at the hub. Somebody
#: who has just watched a minute on `maps` wants `sprezzature-maps`, and
#: sending them to the monorepo instead is a redirect dressed up as a
#: destination. The suite film is the one whose subject *is* the hub.
GITHUB = "github.com/warith-harchaoui"


def cta_for(film_key: str) -> list[tuple[str, dict, str]]:
    """The two asks that close one film."""
    repo = "sprezzature" if film_key == "sprezzature" else f"sprezzature-{film_key}"
    return [
        ("\u2605", L("Star it on GitHub", "Mettez une étoile sur GitHub"),
         f"{GITHUB}/{repo}"),
        ("\u2192", L("The whole suite", "Toute la suite"), "sprezzature.ai"),
    ]



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
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature",
                 line=L("Design know-how, written as code.",
                        "Le savoir-faire du design, écrit en code."),
                 url="sprezzature.ai"),
            dict(type="chips", beat="problem", start=5.4, dur=9.1, end=14.4,
                 eyebrow=L("Settled by other people", "Décidé par d'autres"),
                 items=["30 Laws of UX", L("WCAG contrast", "contraste WCAG"),
                        "Machado 2009", "Gestalt", "Equal Earth", "W3C WebVTT",
                        "Schema.org", "OKLCH"],
                 at=on_beat(6.5, 7.1, 7.6, 8.2, 8.7, 9.3, 9.8, 10.4),
                 caption=L("The laws of attention: Yablonski. Contrast: the "
                           "W3C. What a colour-blind reader sees: a 2009 paper.",
                           "Les lois de l'attention, c'est Yablonski. Le "
                           "contraste, c'est le W3C. Ce que voit un daltonien, "
                           "c'est un article de 2009.")),
            dict(type="grid", beat="solution", start=14.3, dur=9.2, end=23.4,
                 eyebrow=L("What comes out of them", "Ce qui en sort"),
                 images=["figures/corr-matrix.svg", "figures/calendar-heatmap.svg",
                         "figures/map-flow.svg", "figures/choropleth.svg"],
                 at=on_beat(15.8, 16.4, 16.9, 17.5),
                 caption=L("A matrix, a calendar, a flow, a choropleth. Every "
                           "one of them had to answer to its rule.",
                           "Une matrice, un calendrier, un flux, un "
                           "choroplèthe. Chacun a dû passer sa règle.")),
            dict(type="versus", beat="solution", start=23.3, dur=9.2, end=32.4,
                 eyebrow=L("The same rules, used twice",
                           "Les mêmes règles, deux fois"),
                 left=(L("Make", "Fabriquer"),
                       L("a page, a figure, a map, a palette",
                         "une page, une figure, une carte, une palette")),
                 right=(L("Audit", "Auditer"),
                        L("the same ones, over what is already live",
                          "les mêmes, sur ce qui est déjà en ligne")),
                 at=on_beat(24.5, 25.6),
                 caption=L("167 chart kinds. 20 accessibility rules. 30 laws "
                           "of UX.",
                           "167 types de graphiques. 20 règles "
                           "d'accessibilité. 30 lois d'UX.")),
            dict(type="loop", beat="magic", start=32.3, dur=16.7, end=49.0,
                 eyebrow=L("What no rule does", "Ce qu'aucune règle ne fait"),
                 steps=LOOP_STEPS,
                 fig="figures/bar-grouped.svg", gray="figures/bar-grouped-gray.svg",
                 ratio=745 / 505, step_at=on_beat(33.3, 34.4, 35.5, 36.6),
                 wipe_at=38.7, wipe_dur=1.09, caption_at=43.6,
                 caption=L("A vision model looks at the chart and says what is "
                           "wrong. The source is what you then fix.",
                           "Un modèle de vision regarde le graphique et dit ce "
                           "qui cloche. Ensuite, c'est la source qu'on corrige.")),
            dict(type="held", beat="magic", start=48.9, dur=6.7, end=55.5,
                 line=L("Everything stays on your desk. Nothing travels.",
                        "Tout reste sur votre poste. Rien ne part ailleurs.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature", actions=cta_for("sprezzature")),
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
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 colors",
                 line=L("Colours everybody can read, proved rather than hoped.",
                        "Des couleurs que tout le monde peut lire, et la preuve avec."),
                 url="sprezzature.ai"),
            dict(type="versus", beat="problem", start=5.4, dur=9.1, end=14.4,
                 eyebrow=L("The same button, two readers",
                           "Le même bouton, deux lecteurs"),
                 left=(L("Low vision", "Malvoyance"),
                       L("the text and the background merge",
                         "le texte et le fond se confondent")),
                 right=(L("Bright sunlight", "Plein soleil"),
                        L("the screen flattens the difference",
                          "l'écran écrase la différence")),
                 at=on_beat(6.5, 7.6),
                 caption=L("Whoever chose the colour can read it. That is the "
                           "whole problem.",
                           "Celui qui a choisi la couleur, lui, la lit très "
                           "bien. C'est tout le problème.")),
            dict(type="claim", beat="problem", start=14.3, dur=4.8, end=18.0,
                 line=L("About one man in twelve does not separate red from "
                        "green.",
                        "Un homme sur douze environ ne sépare pas le rouge du "
                        "vert.")),
            # Twenty-two seconds. The argument here is made by looking.
            dict(type="cvd", beat="solution", start=17.9, dur=22.0, end=39.8,
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
                 caption=L("The matrices come from a 2009 paper, measured on "
                           "real observers.",
                           "Les matrices viennent d'un article de 2009, "
                           "mesurées sur de vrais observateurs.")),
            dict(type="held", beat="magic", start=39.7, dur=9.3, end=49.0,
                 line=L("Hue goes. Saturation goes. Lightness holds.",
                        "La teinte s'efface. La saturation s'efface. La "
                        "clarté, elle, tient.")),
            dict(type="versus", beat="magic", start=48.9, dur=6.7, end=55.5,
                 eyebrow=L("So that is what the audit works on",
                           "C'est donc là-dessus que l'audit travaille"),
                 left=(L("Your colour", "Votre couleur"),
                       L("its hue and its saturation stay put",
                         "sa teinte et sa saturation ne bougent pas")),
                 right=(L("Its lightness", "Sa clarté"),
                        L("moves until the contrast clears",
                          "varie jusqu'au seuil de contraste")),
                 at=on_beat(49.6, 50.7),
                 caption=L("Your blue stays your blue. It becomes legible.",
                           "Votre bleu reste votre bleu. Il devient lisible.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 colors", actions=cta_for("colors")),
        ],
    ),
    # ---------------------------------------------------------------- figures
    "figures": dict(
        duration=60.0,
        # Written 2026-10-27 after running the package rather than reading its
        # feature table. The old cut opened on "167 kinds, every one
        # hand-authored", which is a specification handed to somebody with no
        # reason to want one.
        #
        # The secret sauce is `make-figure recommend`. Every kind declares the
        # data roles it needs, so your columns either fill them or they do
        # not: the right chart is computable rather than a matter of taste,
        # deterministically, with no model anywhere near it. The catalogue is
        # a filter your data runs through, not a menu you browse.
        vo=[("figures.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 27.28), ("tile", 42.55),
             ("bell", 55.67)],
        scenes=[
            # PROBLEM
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 figures",
                 line=L("167 chart kinds, every line of SVG written by hand.",
                        "167 types de graphiques, chaque trait de SVG écrit à la main."),
                 url="sprezzature.ai"),
            dict(type="held", beat="problem", start=5.4, dur=9.1, end=14.4,
                 line=L("Most people reach for the bar chart they reached for "
                        "last time.",
                        "La plupart des gens reprennent le graphique en barres "
                        "de la dernière fois.")),
            # SOLUTION
            dict(type="grid", beat="solution", start=14.3, dur=12.9, end=27.2,
                 eyebrow=L("167 kinds, each written by hand",
                           "167 types, écrits un par un à la main"),
                 images=["figures/sankey.svg", "figures/alluvial.svg",
                         "figures/chord.svg", "figures/bellcurve.svg",
                         "figures/circle-packing.svg", "figures/candlestick.svg"],
                 at=on_beat(15.8, 16.4, 16.9, 17.5, 18.0, 18.6),
                 caption=L("Every generator writes the SVG markup itself, so "
                           "the shapes belong to nobody's charting library.",
                           "Chaque générateur écrit le SVG lui-même : les "
                           "formes n'appartiennent à la bibliothèque de "
                           "personne.")),
            # SECRET SAUCE
            dict(type="claim", beat="magic", start=27.1, dur=8.3, end=35.3,
                 line=L("Each one declares the data it needs.",
                        "Chacun déclare les données qu'il lui faut.")),
            dict(type="verify", beat="magic", start=35.2, dur=12.3, end=47.4,
                 eyebrow=L("So your columns are the question",
                           "Vos colonnes posent donc la question"),
                 claims=[(L("region, quarter, units", "région, trimestre, unités"),
                          L("3 columns", "3 colonnes")),
                         # 61, measured: `make-figure recommend --data r.csv
                         # --limit 500` on a three-column frame of region,
                         # quarter, units. The first draft said 41, which
                         # nobody had run.
                         (L("kinds those columns can fill", "types qu'elles remplissent"),
                          "61"),
                         (L("ranked by readability", "classés par lisibilité"),
                          L("best first", "le meilleur d'abord")),
                         (L("models consulted", "modèles consultés"), "0")],
                 at=[(36.6, 37.1), (38.2, 38.7), (39.8, 40.4), (41.5, 42.0)],
                 caption=L("The same filter the studio shows as cards, run "
                           "from the command line.",
                           "Le même filtre que le studio affiche en cartes, "
                           "depuis la ligne de commande.")),
            dict(type="held", beat="magic", start=47.3, dur=8.2, end=55.5,
                 line=L("The catalogue is a filter, not a menu.",
                        "Le catalogue est un filtre, pas un menu.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 figures", actions=cta_for("figures")),
        ],
    ),
    # ---------------------------------------------------------------- publish
    "publish": dict(
        duration=60.0,
        # A pipeline film, written 2026-10-27 from `_readalong.py` rather than
        # from the tool list. Its docstring holds the best sentence in the
        # package: a read-along wrong by one sentence is worse than none,
        # because it tells a reader with confidence to look at the wrong line.
        #
        # So the module refuses to number sentences independently. It takes
        # the cues the narration actually produced, splits the rendered HTML
        # with the same splitter, compares the two lists, and raises on the
        # first divergence. "There is no third outcome where it wraps
        # something and hopes."
        vo=[("publish.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 30.00), ("tile", 42.55),
             ("bell", 55.67)],
        scenes=[
            # PROBLEM
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 publish",
                 line=L("A folder of Markdown becomes a site somebody can find.",
                        "Un dossier de Markdown devient un site qu'on trouve."),
                 url="sprezzature.ai"),
            dict(type="held", beat="problem", start=5.4, dur=9.1, end=14.4,
                 line=L("One sentence out of step is worse than no "
                        "highlighting at all.",
                        "Une phrase de décalage vaut moins que pas de "
                        "surlignage du tout.")),
            # SOLUTION: the pipeline
            dict(type="flow", beat="solution", start=14.3, dur=14.9, end=29.2,
                 eyebrow=L("One document, nine tools", "Un document, neuf outils"),
                 stages=[("lint", L("stdlib, milliseconds", "stdlib, millisecondes")),
                         ("html", L("the page", "la page")),
                         ("icons", L("one logo, every size", "un logo, toutes les tailles")),
                         ("indexes", L("crawlers and models", "robots et modèles")),
                         ("meta", L("cards, drafted locally", "cartes, rédigées en local")),
                         ("narrate", L("the voice", "la voix")),
                         ("readalong", L("the two, bound", "les deux, liés"))],
                 at=on_beat(15.8, 17.0, 18.1, 19.2, 20.3, 21.4, 22.5),
                 caption=L("The linter runs on the standard library alone, "
                           "which is why it fits in a pre-commit hook.",
                           "Le linter n'utilise que la bibliothèque standard : "
                           "c'est pourquoi il tient dans un crochet de "
                           "pré-commit.")),
            # SECRET SAUCE
            dict(type="claim", beat="magic", start=29.1, dur=8.3, end=37.3,
                 line=L("The audio and the page leave the same Markdown by "
                        "different roads.",
                        "L'audio et la page quittent le même Markdown par "
                        "deux routes.")),
            dict(type="versus", beat="magic", start=37.2, dur=9.6, end=46.8,
                 eyebrow=L("Two roads, no guarantee",
                           "Deux routes, aucune garantie"),
                 left=(L("The voice", "La voix"),
                       L("sentences handed to the engine",
                         "des phrases remises au moteur")),
                 right=(L("The page", "La page"),
                        L("blocks walked as a tree",
                          "des blocs parcourus comme un arbre")),
                 at=on_beat(38.2, 39.3),
                 caption=L("A regular expression cannot see a code fence "
                           "inside a list item. A tree walk can.",
                           "Une expression régulière ne voit pas un bloc de "
                           "code dans une puce. Un parcours d'arbre, oui.")),
            dict(type="held", beat="magic", start=46.7, dur=8.8, end=55.5,
                 line=L("They match, or it refuses. There is no third outcome.",
                        "Les deux coïncident, ou bien ça refuse. Il n'y a pas "
                        "de troisième issue.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 publish", actions=cta_for("publish")),
        ],
    ),
    # ------------------------------------------------------------------ audio
    "audio": dict(
        duration=60.0,
        # Five scenes, the fewest of any brick film, written 2026-10-27 from
        # `audit_captions.py`. Its opening paragraph is the whole pitch: a
        # perfectly accurate caption holding ninety characters for half a
        # second is unreadable, and accuracy was the only thing anybody
        # measured.
        #
        # The secret sauce is that the numbers already exist. Netflix's timed
        # text style guide publishes 17 characters a second, 42 per line, a
        # five-sixths of a second floor and a seven second ceiling; BBC and
        # Netflix agree on two lines. Published, conventional, and unchecked.
        vo=[("audio.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 32.19), ("bell", 55.67)],
        scenes=[
            # PROBLEM
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 audio",
                 line=L("Speech, read both ways, on your own machine.",
                        "La parole, lue dans les deux sens, sur votre machine."),
                 url="sprezzature.ai"),
            dict(type="held", beat="problem", start=5.4, dur=9.6, end=15.0,
                 line=L("Ninety characters, on screen for half a second.",
                        "Quatre-vingt-dix caractères, affichés une "
                        "demi-seconde.")),
            # SOLUTION: the file itself, with the offending cue marked
            dict(type="code", beat="solution", start=14.9, dur=16.1, end=31.0,
                 eyebrow=L("The track, read as a file",
                           "La piste, lue comme un fichier"),
                 code=["WEBVTT", "",
                       "00:00:12.100 --> 00:00:12.950",
                       "Every threshold here is a flag rather than a law,",
                       "because a children's programme and a dense talk",
                       "justify different numbers entirely.", "",
                       "00:00:12.900 --> 00:00:19.400",
                       "And this one starts before that one ended."],
                 mark=(4, 5, 6, 9),
                 at=[15.8, 16.1, 16.6, 17.2, 17.7, 18.3, 18.6, 19.1, 19.7],
                 flag=[(4, 22.0), (9, 25.5)],
                 caption=L("A hundred and thirty characters in eight hundred "
                           "milliseconds. Then a cue that starts too early.",
                           "Cent trente caractères en huit cents "
                           "millisecondes. Puis un sous-titre qui part trop "
                           "tôt.")),
            # SECRET SAUCE
            dict(type="verify", beat="magic", start=30.9, dur=16.1, end=47.0,
                 eyebrow=L("Netflix's timed text style guide",
                           "Le guide de sous-titrage de Netflix"),
                 claims=[(L("reading speed, characters a second",
                            "vitesse de lecture, caractères par seconde"), "17"),
                         (L("characters on one line", "caractères sur une ligne"), "42"),
                         (L("shortest a cue may be", "durée minimale d'un sous-titre"),
                          L("5/6 s", "5/6 s")),
                         (L("longest before it has swallowed a sentence",
                            "durée au-delà de laquelle il a avalé une phrase"),
                          L("7 s", "7 s")),
                         (L("lines, on which BBC and Netflix agree",
                            "lignes, sur quoi la BBC et Netflix s'accordent"), "2")],
                 at=[(32.2, 32.7), (33.8, 34.3), (35.5, 36.0),
                     (37.1, 37.6), (38.7, 39.2)],
                 caption=L("Conventions rather than laws, which is why each "
                           "one is a flag with its source written next to it.",
                           "Des conventions plutôt que des lois : chacune est "
                           "donc un signalement, sa source écrite à côté.")),
            dict(type="held", beat="magic", start=46.9, dur=8.6, end=55.5,
                 line=L("Accuracy was the only thing anybody measured.",
                        "L'exactitude était la seule chose qu'on mesurait.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 audio", actions=cta_for("audio")),
        ],
    ),
    # ---------------------------------------------------------------- cli-gui
    "cli-gui": dict(
        duration=60.0,
        # Written 2026-10-27 from `schema.py`, which holds two things the
        # feature list does not.
        #
        # Three frameworks, two adapters: a Typer app is converted with
        # typer's own `get_command` and then walked as Click, "because that is
        # what it becomes; there is no third adapter". Writing a third would
        # have been a second implementation of Click that drifts.
        #
        # And the trap that would make the page lie: a Click Group's name
        # defaults to the decorated function's name, usually `main`, rather
        # than the installed console script. Left alone, the page's Build
        # command assembles a command line that does not exist.
        vo=[("cli-gui.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 30.00), ("tile", 42.55),
             ("bell", 55.67)],
        scenes=[
            # PROBLEM
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 cli-gui",
                 line=L("Your command line, as a form anybody can fill in.",
                        "Votre ligne de commande, en formulaire que tout le monde remplit."),
                 url="sprezzature.ai"),
            # PROBLEM
            dict(type="held", beat="problem", start=5.4, dur=11.1, end=16.4,
                 line=L("Your colleague needs this tool. They will not open a "
                        "terminal.",
                        "Votre collègue a besoin de cet outil. Il n'ouvrira "
                        "pas de terminal.")),
            # SOLUTION: the thing itself. The claim that used to sit here --
            # "it reads the parser object, the help text is a last resort" --
            # is said by the voice over these two captures instead, because
            # the captures are the better argument and the slot is now one
            # scene shorter.
            dict(type="grid", beat="solution", start=16.3, dur=8.2, end=24.4,
                 eyebrow=L("Generated from the command, not written",
                           "Engendré depuis la commande, pas écrit"),
                 images=["shots/make-figure-list.png", "shots/make-figure-render.png"],
                 at=on_beat(17.5, 18.6),
                 caption=L("Options become fields. Choices become a list. "
                           "Required stays required.",
                           "Les options deviennent des champs. Les choix, une "
                           "liste. L'obligatoire reste obligatoire.")),
            # SECRET SAUCE
            dict(type="versus", beat="magic", start=24.3, dur=11.2, end=35.4,
                 # Counting the parts was an inventory, and the suite's own
                 # pitch checker said so: "Three frameworks, two adapters" is
                 # the same shape as "Ten packages. Five surfaces each.", the
                 # line that checker was written against. The insight is why
                 # there are two and not three.
                 eyebrow=L("A Typer app is already Click",
                           "Une application Typer est déjà du Click"),
                 left=(L("argparse, Click", "argparse, Click"),
                       L("walked directly, each in its own adapter",
                         "parcourus directement, chacun son adaptateur")),
                 right=("Typer",
                        L("converted by typer itself, then walked as Click",
                          "converti par typer lui-même, puis lu comme du Click")),
                 at=on_beat(25.6, 26.7),
                 caption=L("A third adapter would be a second implementation "
                           "of Click, drifting from the first.",
                           "Un troisième adaptateur serait une deuxième "
                           "implémentation de Click, qui dériverait de la "
                           "première.")),
            dict(type="held", beat="magic", start=35.3, dur=10.2, end=45.5,
                 line=L("A Click group is named after the function, not after "
                        "the command.",
                        "Un groupe Click porte le nom de la fonction, pas "
                        "celui de la commande.")),
            dict(type="claim", beat="magic", start=45.4, dur=10.1, end=55.5,
                 line=L("Unasked, the page builds a command that does not exist.",
                        "Faute de le dire, la page fabrique une commande "
                        "qui n'existe pas.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 cli-gui", actions=cta_for("cli-gui")),
        ],
    ),
    # --------------------------------------------------------------------- ui
    "ui": dict(
        duration=60.0,
        # The smallest package gets the fewest scenes. Written 2026-10-27 from
        # `audit_i18n.py`, whose best idea is where it stops: `--fix` writes
        # the string into the catalogue and refuses to rewrite the call site,
        # for the reason `pybabel extract` gives. Only the author knows which
        # id the call should use, and whether the surrounding code wants a
        # plural or a placeholder. So it prints the line to paste, and
        # anything it could not parse with certainty is reported as needing a
        # hand rather than dropped in silence.
        vo=[("ui.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 24.55), ("tile", 42.55), ("bell", 55.67)],
        scenes=[
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 ui",
                 line=L("Every sentence hardcoded in your source, found and filed.",
                        "Chaque phrase écrite en dur dans vos sources, trouvée et rangée."),
                 url="sprezzature.ai"),
            dict(type="held", beat="problem", start=5.4, dur=11.1, end=16.4,
                 line=L("It costs a week the day somebody needs a second "
                        "language.",
                        "Elle coûte une semaine le jour où il faut une "
                        "deuxième langue.")),
            dict(type="versus", beat="solution", start=16.3, dur=13.2, end=29.4,
                 eyebrow=L("Two places a string hides",
                           "Deux endroits où une phrase se cache"),
                 left=("I18N001",
                       L("a locale table buried in JavaScript",
                         "une table de langues enfouie dans du JavaScript")),
                 right=("I18N002",
                        L("a model prompt inlined in Python",
                          "un prompt de modèle écrit en dur en Python")),
                 at=on_beat(17.5, 18.6),
                 caption=L("A prompt is a translatable string. Almost nobody "
                           "treats it as one.",
                           "Un prompt est une chaîne traduisible. Presque "
                           "personne ne le traite comme tel.")),
            dict(type="held", beat="magic", start=29.3, dur=13.2, end=42.5,
                 line=L("It moves the string, then stops.",
                        "Il déplace la phrase, puis s'arrête.")),
            dict(type="claim", beat="magic", start=42.4, dur=13.1, end=55.5,
                 line=L("Only you know whether that line wants a plural.",
                        "Vous seul savez si cette ligne réclame un pluriel.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 ui", actions=cta_for("ui")),
        ],
    ),
    # ------------------------------------------------------------------ video
    # The tenth brick, and the one that made the other nine films. Its subject
    # is the films themselves, which is why it can afford to be plain: every
    # scene is a sentence about the thing the viewer is currently watching.
    "video": dict(
        duration=60.0,
        # The brick that made the other ten and checks them. Written
        # 2026-10-27, and its problem statement is this repository's own
        # history: "127 chart kinds" stayed on screen while the catalogue
        # grew to 167, because nobody opens a generator to re-read its
        # strings.
        #
        # The secret sauce is that the dangerous claim is the undeclared one.
        # A declared claim gets checked against the code. A number that
        # simply appears on screen has nothing to check it against, so the
        # scan reads the composition and reports every number no claim
        # accounts for.
        vo=[("video.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 20.19), ("tile", 38.74), ("bell", 55.67)],
        scenes=[
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 video",
                 line=L("A film that can be re-read, and checked against its code.",
                        "Un film qui se relit, et se vérifie sur son propre code."),
                 url="sprezzature.ai"),
            dict(type="held", beat="problem", start=5.4, dur=13.1, end=18.4,
                 line=L("This suite told viewers it had 127 chart kinds, for "
                        "months after it had 167.",
                        "Cette suite a annoncé 127 types de graphiques "
                        "pendant des mois après en avoir eu 167.")),
            dict(type="verify", beat="solution", start=18.3, dur=19.1, end=37.4,
                 eyebrow=L("So the claims live beside the film",
                           "Les affirmations vivent donc à côté du film"),
                 claims=[(L("chart kinds, checked against the catalogue",
                            "types de graphiques, vérifiés sur le catalogue"), "167"),
                         (L("accessibility rules, checked against the linter",
                            "règles d'accessibilité, vérifiées sur le linter"), "20"),
                         (L("laws of UX, checked against the reference",
                            "lois d'UX, vérifiées sur la référence"), "30"),
                         (L("assets, checked against the ledger",
                            "ressources, vérifiées sur l'inventaire"), "81")],
                 at=[(19.7, 20.2), (21.3, 21.8), (22.9, 23.4), (24.5, 25.0)],
                 caption=L("Each one names the file that would have to change "
                           "for it to stop being true.",
                           "Chacune nomme le fichier qui devrait changer pour "
                           "qu'elle cesse d'être vraie.")),
            dict(type="held", beat="magic", start=37.3, dur=18.2, end=55.5,
                 line=L("The dangerous number is the one nobody declared.",
                        "Le nombre dangereux est celui que personne n'a "
                        "déclaré.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 video", actions=cta_for("video")),
        ],
    ),
    # ------------------------------------------------------------------- maps
    "maps": dict(
        duration=60.0,
        # No panels, no chips: six plates and a voice over them. Written
        # 2026-10-27 after reading `make_density.py`, which turns out to hold
        # the best sentence in the package.
        #
        # The secret sauce is the plate that draws no map. An accumulation
        # field has no coastline, no border and no graticule: the land appears
        # because events fell on it, the sea stays dark because none did, and
        # a reader recognises the shape without being shown it. The first cut
        # of this film said that in a caption over somebody else's map,
        # because the French density plate did not exist. It does now.
        vo=[("maps.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 26.19), ("wipe", 40.37),
             ("bell", 55.67)],
        scenes=[
            # PROBLEM
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 maps",
                 line=L("Maps drawn on real ground, saying what they do not know.",
                        "Des cartes sur un vrai sol, qui disent ce qu'elles ignorent."),
                 url="sprezzature.ai"),
            # PROBLEM
            dict(type="held", beat="problem", start=5.4, dur=10.1, end=15.4,
                 line=L("A column of countries hides where things happen.",
                        "Une colonne de pays cache l'endroit où les choses "
                        "arrivent.")),
            # SOLUTION: real ground, and what the plates are actually for.
            # Two grids were merged into one when the identity card took the
            # opening slot: six plates in ten seconds was always more than a
            # viewer could look at, and the four reference plates were the
            # ones saying the least.
            dict(type="grid", beat="solution", start=15.3, dur=10.9, end=26.2,
                 eyebrow=L("Who holds what, at what certainty",
                           "Qui tient quoi, à quelle certitude"),
                 images=["maps/situation-ukraine.png", "maps/situation-syria.png"],
                 at=on_beat(16.4, 17.5),
                 caption=L("ACLED and UCDP both record how sure a coordinate "
                           "is. A ring is a position the source never gave.",
                           "ACLED et UCDP notent tous deux ce qu'une coordonnée "
                           "a de sûr. Un anneau, c'est une position que la "
                           "source n'a jamais donnée.")),
            # SECRET SAUCE
            dict(type="claim", beat="magic", start=26.1, dur=8.3, end=34.3,
                 line=L("Then the plate that draws no map at all.",
                        "Puis la planche qui ne dessine aucune carte.")),
            dict(type="grid", beat="magic", start=34.2, dur=12.0, end=46.1,
                 eyebrow=L("Drawn without a coastline",
                           "Dessinée sans la moindre côte"),
                 images=["maps/density.svg"],
                 at=on_beat(35.5),
                 caption=L("Every point is an event. The shape is what they "
                           "add up to.",
                           "Chaque point est un événement. La forme est ce "
                           "qu'ils finissent par dessiner.")),
            dict(type="held", beat="magic", start=46.0, dur=9.5, end=55.5,
                 line=L("The land appears because events fell on it.",
                        "La terre apparaît parce que des événements y sont "
                        "tombés.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 maps", actions=cta_for("maps")),
        ],
    ),
    # ----------------------------------------------------------------- ux-laws
    "ux-laws": dict(
        duration=60.0,
        # One sustained argument, no chip grid. Written 2026-10-27 after
        # reading the auditor rather than its feature table.
        #
        # The secret sauce was in a docstring: Hick's Law measures the choices
        # a person meets at one moment, so counting the links in a file gets
        # it wrong twice. A responsive header holds two menus that never paint
        # together, and a group collapses several controls into one decision.
        # The README's table said "too many choices presented at once" and
        # stopped there; the sentence is in both READMEs now.
        vo=[("ux-laws.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 24.55), ("tile", 36.55),
             ("bell", 55.67)],
        scenes=[
            # PROBLEM
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 ux-laws",
                 line=L("The laws of attention, checked against your own markup.",
                        "Les lois de l'attention, vérifiées sur votre balisage."),
                 url="sprezzature.ai"),
            dict(type="versus", beat="problem", start=5.4, dur=9.1, end=14.4,
                 eyebrow=L("What actually gets reported",
                           "Ce qu'on vous remonte vraiment"),
                 left=(L("What they say", "Ce qu'on vous dit"),
                       L("“I can never find the button”",
                         "« je ne trouve jamais le bouton »")),
                 right=(L("What it is", "Ce que c'est"),
                        L("too many choices at one moment",
                          "trop de choix au même instant")),
                 at=on_beat(6.5, 7.6),
                 caption=L("Hick's Law is the one thing nobody will mention.",
                           "La loi de Hick, elle, personne ne la citera.")),
            # SOLUTION
            dict(type="claim", beat="solution", start=14.3, dur=9.2, end=23.4,
                 line=L("Thirty laws. Eight of them settle from the source.",
                        "Trente lois. Huit se tranchent depuis la source.")),
            # SECRET SAUCE, shown as the markup it reads
            dict(type="code", beat="magic", start=23.3, dur=13.1, end=36.4,
                 eyebrow=L("The same header, two menus",
                           "Le même en-tête, deux menus"),
                 code=['<nav class="flex items-center justify-between">',
                       '  <div class="hidden sm:flex gap-4">',
                       '    <a href="/skills">Skills</a>',
                       '    <a href="/gallery">Gallery</a>',
                       '    <a href="/packages">Packages</a>',
                       '  </div>',
                       '  <button class="sm:hidden">Menu</button>',
                       '</nav>'],
                 mark=(2, 7),
                 at=[24.0, 24.5, 25.1, 25.6, 26.2, 26.7, 27.3, 27.8],
                 flag=[(2, 29.5), (7, 31.1)],
                 caption=L("One of these paints on a phone. The other paints "
                           "on a desktop. A reader meets one of them.",
                           "L'un s'affiche sur téléphone. L'autre sur "
                           "ordinateur. Un lecteur n'en rencontre qu'un.")),
            dict(type="held", beat="magic", start=36.3, dur=9.7, end=46.0,
                 line=L("Adding them up charges the reader for choices no "
                        "screen ever shows.",
                        "Les additionner reproche au lecteur des choix "
                        "qu'aucun écran ne lui montre.")),
            dict(type="versus", beat="magic", start=45.9, dur=9.6, end=55.5,
                 eyebrow=L("So it counts them apart",
                           "Il les compte donc à part"),
                 left=(L("Per breakpoint", "Par point de rupture"),
                       L("the phone count, then the desktop count",
                         "le compte du téléphone, puis celui du bureau")),
                 right=(L("Per decision", "Par décision"),
                        L("a block that collapses counts as one",
                          "un bloc qui se replie compte pour un")),
                 at=on_beat(47.0, 48.1),
                 caption=L("It reports the worse of the two, naming which "
                           "one it is.",
                           "Il retient le pire des deux, en disant lequel.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 ux-laws", actions=cta_for("ux-laws")),
        ],
    ),
    # ----------------------------------------------------------- accessibility
    "accessibility": dict(
        duration=60.0,
        # Written 2026-10-27 from `lint_a11y.py`. Its autoplay rule carries
        # the sharpest problem statement in the suite: unmuted sound that
        # starts by itself masks a screen reader, so the user cannot hear the
        # tool they are navigating with, and on many pages cannot find the
        # control to stop it either. The trap closes on itself.
        #
        # The secret sauce is the restraint. Six of twenty rules repair
        # themselves, and only six, because a fix is automatic solely where
        # exactly one repair is safe. The other fourteen are reported and
        # never guessed at. `fix_file` is idempotent by contract: a second
        # run on a fixed file applies zero edits.
        vo=[("accessibility.en", 1.10)],
        sfx=[("drop", 5.47), ("tile", 16.37), ("tile", 28.37), ("tile", 42.55),
             ("bell", 55.67)],
        scenes=[
            # PROBLEM
            dict(type="what", beat="what", start=0.0, dur=6.0, end=5.5,
                 logo="logo-512.png", mark="Sprezzature \u00b7 accessibility",
                 line=L("Twenty accessibility rules, decided by reading the HTML.",
                        "Vingt règles d'accessibilité, tranchées en lisant le HTML."),
                 url="sprezzature.ai"),
            dict(type="held", beat="problem", start=5.4, dur=10.1, end=15.4,
                 line=L("A blind reader now cannot hear the tool they would "
                        "use to stop it.",
                        "Un lecteur aveugle n'entend plus l'outil avec lequel "
                        "il l'arrêterait.")),
            # SOLUTION
            dict(type="chips", beat="solution", start=15.3, dur=12.9, end=28.2,
                 eyebrow=L("Twenty rules out of WCAG and WAI-ARIA",
                           "Vingt règles tirées de WCAG et WAI-ARIA"),
                 items=["media-autoplay-sound", "video-missing-captions",
                        "img-missing-alt", "input-missing-label",
                        "div-onclick", "tabindex-positive",
                        "heading-skip", "color-only-state"],
                 at=on_beat(16.4, 17.0, 17.5, 18.1, 18.6, 19.2, 19.7, 20.3),
                 caption=L("Each finding names the element, the line and the "
                           "rule it broke. Standard library only.",
                           "Chaque constat nomme l'élément, la ligne et la "
                           "règle enfreinte. Bibliothèque standard seule.")),
            # SECRET SAUCE
            dict(type="verify", beat="magic", start=28.1, dur=14.3, end=42.4,
                 eyebrow=L("What it will repair by itself",
                           "Ce qu'il répare de lui-même"),
                 claims=[(L("rules it checks", "règles vérifiées"), "20"),
                         (L("rules it will fix", "règles qu'il corrige"), "6"),
                         (L("rules it reports and leaves alone",
                            "règles qu'il signale et laisse"), "14"),
                         (L("edits a second run applies",
                            "retouches à la seconde exécution"), "0")],
                 at=[(29.5, 30.0), (31.1, 31.6), (32.7, 33.2), (34.4, 34.9)],
                 caption=L("A repair is automatic only where exactly one "
                           "repair is safe.",
                           "Une réparation n'est automatique que là où il "
                           "n'en existe qu'une de sûre.")),
            dict(type="versus", beat="magic", start=42.3, dur=13.2, end=55.5,
                 eyebrow=L("And the same rule, turned around",
                           "Et la même règle, retournée"),
                 left=(L("Reading it", "En lecture"),
                       L("body text too tight to follow",
                         "du texte courant trop serré pour suivre")),
                 right=(L("Writing it", "En écriture"),
                        L("the CSS that meets the minimum",
                          "le CSS qui atteint le minimum")),
                 at=on_beat(43.6, 44.7),
                 caption=L("Audit and make are one rule, read in two "
                           "directions.",
                           "Auditer et fabriquer, c'est une seule règle lue "
                           "dans deux sens.")),
            dict(type="cta", beat="cta", start=55.4, dur=4.6, end=60.0, logo="logo-512.png",
                 mark="Sprezzature \u00b7 accessibility", actions=cta_for("accessibility")),
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
    /* The gutter number is text, and the contrast checker treats it as
       text: drawn in the hairline colour it came to 1.26:1 against paper,
       where 3:1 is the floor. A line number nobody can read is also a line
       number nobody can quote back at you. */
    .code-n {{ color: #8a8a8a; min-width: {int(f['mono'] * 1.5)}px;
      text-align: right; }}
    .code-t {{ color: var(--ink); white-space: pre; }}
    .code-line.bad .code-t {{ color: var(--ink); font-weight: 600; }}
    /* The gutter number is drawn in the rule colour, which disappears
       against the flag. A flagged line is the one a viewer wants to
       name, so its number is the one that has to stay readable. */
    .code-line.bad .code-n {{ color: var(--ink-soft); font-weight: 600; }}

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

    /* The identity card that opens every film, and is finished at frame
       zero: the package's name, one line saying what it is, and where to
       find it. The films used to open on their problem sentence alone --
       a good sentence, which tells a viewer who has just landed nothing
       about whose problem it is or what they are watching. */
    #what-mark {{ font-family: "Roboto Serif"; font-size: {int(f['hero'] * .9)}px;
      font-weight: 600; letter-spacing: -.02em; color: var(--ink);
      text-align: center; }}
    #what-line {{ font-size: {int(f['h2'] * 1.05)}px; color: var(--ink-soft);
      text-align: center; text-wrap: balance;
      max-width: {int(f['w'] * (.74 if f['w'] > f['h'] else .92))}px;
      margin-top: {int(f['hero'] * .3)}px; }}
    #what-url {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f['eyebrow'] * 1.02)}px; font-weight: 500;
      letter-spacing: .06em; color: var(--blue);
      margin-top: {int(f['hero'] * .34)}px; }}

    /* The call to action. Two things to do, each one a verb and the place
       it happens, because "sprezzature.ai" alone is an address and not an
       instruction. The glyph is a column of its own so the two verbs start
       on the same vertical line whatever the canvas. */
    .cta {{ display: flex; align-items: baseline; gap: {int(f['body'] * .5)}px;
      margin-top: {int(f['hero'] * .26)}px; }}
    .cta-glyph {{ font-size: {int(f['h2'] * .9)}px; color: var(--blue);
      line-height: 1; width: {int(f['h2'] * 1.1)}px; text-align: center; }}
    .cta-text {{ display: flex; flex-direction: column; }}
    .cta-do {{ font-size: {f['h2']}px; font-weight: 600; color: var(--ink);
      letter-spacing: -.01em; }}
    .cta-at {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f['eyebrow'] * .92)}px; font-weight: 500;
      letter-spacing: .04em; color: var(--blue);
      margin-top: {int(f['body'] * .22)}px; }}

    /* Where the film is in its own argument, carried the whole minute. Guy
       KAWASAKI's deck labels its slides; a film cannot, so it labels the
       frame instead. Faint enough to ignore, present enough that a viewer
       who wonders "where is this going" can see the answer without
       rewinding. */
    /* Inline with the wordmark on a wide canvas, on a row of its own on a
       tall one. Portrait is 1080 across and the French labels run about 690
       of it: centred on the same line, they drove straight through
       "Sprezzature" on the left and "sprezzature.ai" on the right. The
       English labels are shorter and fitted, which is how a layout bug ships
       in one language and not the other. */
    #beats {{ position: absolute; top: {int(pad * (.5 if f['w'] > f['h'] else 1.75))}px;
      left: 50%;
      transform: translateX(-50%); display: flex; align-items: center;
      gap: {int(f['eyebrow'] * .52)}px; white-space: nowrap;
      font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f['eyebrow'] * .68)}px; font-weight: 500;
      letter-spacing: .16em; text-transform: uppercase; }}
    /* Grey enough to stay out of the way of the sentence, dark enough to be
       read on purpose. The first version used `--line`, the hairline colour,
       which on this paper is all but invisible: the label was there and
       nobody could have told. */
    #beats span {{ color: #a3a3a3; }}
    #beats i {{ font-style: normal; color: #d4d4d4;
      font-size: {int(f['eyebrow'] * .6)}px; }}

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
                f'<h1 class="held" id="s{i}-line">{esc(sc["line"])}</h1>'
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

    if t == "what":
        # Frame zero of a film is the frame most often seen on its own: the
        # poster a player falls back to, the still a scrubber lands on, the
        # thumbnail a platform grabs when nobody gave it one. So it carries
        # the name, the sentence and the address, and it carries them whole
        # -- nothing in this scene fades in.
        return (f'<div class="stage"><div class="col">'
                f'<img id="logo" src="assets/{sc["logo"]}" alt="">'
                f'<p id="what-mark">{esc(sc["mark"])}</p>'
                f'<p id="what-line">{esc(sc["line"])}</p>'
                f'<p id="what-url">{esc(sc["url"])}</p></div></div>')

    if t == "cta":
        # Kawasaki's last slide is the ask, and the film used to end on a
        # motto: "Make it. Audit it. Then look at it." Pretty, and it
        # requests nothing — a viewer who liked the minute had nowhere to
        # put that. Two asks now, in the order of what they cost: a star is
        # one click from where the viewer already is, the site is a visit.
        acts = "".join(
            f'<div class="cta" id="cta{k}"><span class="cta-glyph">{glyph}</span>'
            f'<span class="cta-text"><span class="cta-do">{esc(doing)}</span>'
            f'<span class="cta-at">{esc(where)}</span></span></div>'
            for k, (glyph, doing, where) in enumerate(sc["actions"], 1))
        return (f'<div class="stage"><div class="col">'
                f'<img id="logo" src="assets/{sc["logo"]}" alt="">'
                f'<p id="mark">{esc(sc["mark"])}</p>'
                f'{acts}</div></div>')

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

    if t in ("claim", "held"):
        # The first scene of a film is already finished at frame zero. Not
        # faded up from nothing, and not faded up from a third either: an
        # opening that starts at 35% renders as grey text on a sheet with no
        # wordmark on it, which is what frame zero of every film used to be.
        # Frame zero is not a frame nobody sees -- it is the poster a player
        # falls back to, the still a scrubber shows, and the thumbnail a
        # platform picks when nobody gave it one. It has to look like a frame
        # of the film.
        #
        # So the opening sentence is at full strength from the first frame and
        # does not move. The motion in the first half second is the rule
        # drawing itself under the line, which is motion that does not make
        # the frame look unfinished.
        opening = s < 0.01
        if not opening:
            out.append(f'tl.fromTo("#s{i}-line",{{y:30,opacity:0}},'
                       f'{{y:0,opacity:1,duration:.55,ease:"power3.out"}},{s + .2:.2f});')
        out.append(f'tl.fromTo("#s{i}-rule",{{scaleX:0,opacity:{1 if opening else 0}}},'
                   f'{{scaleX:1,opacity:1,duration:.7,ease:"expo.out"}},'
                   f'{(0.0 if opening else s + .55):.2f});')

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

    elif t == "what":
        # Nothing. The card is complete on the first frame and holds until
        # the scene crossfades out, which is the whole point of it. The only
        # motion under it is the audio-reactive wash behind.
        pass

    elif t == "cta":
        out.append(f'tl.fromTo("#logo",{{scale:.88,opacity:0}},'
                   f'{{scale:1,opacity:1,duration:.7,ease:"power3.out"}},{s + .2:.2f});')
        out.append(f'tl.fromTo("#mark",{{y:24,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.6,ease:"power3.out"}},{s + .45:.2f});')
        # The asks arrive in reading order and stay. Whatever is on screen at
        # the last frame is what a viewer who paused there has to act on.
        for k in range(1, len(sc["actions"]) + 1):
            out.append(f'tl.fromTo("#cta{k}",{{y:18,opacity:0}},'
                       f'{{y:0,opacity:1,duration:.55,ease:"power2.out"}},'
                       f'{s + .75 + (k - 1) * .35:.2f});')
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


def compose(film_key: str, spec: dict, fmt_key: str, lang: str = "en") -> str:
    """One film, one canvas, one language, as a page of HTML.

    Split out of :func:`emit` so a test can read the timeline this generator
    produces without the test having to write sixty-six project directories
    to find out what is in them. What the first frame looks like is decided
    here, in the tweens, and nowhere else.
    """
    f = FORMATS[fmt_key]
    spec = in_language(spec, lang, film_key)
    scenes, dur = spec["scenes"], spec["duration"]

    body = "\n".join(
        f'<section id="s{i}" class="clip" data-start="{sc["start"]}" '
        f'data-duration="{sc["dur"]}" data-track-index="{i}">'
        f'<div class="inner" id="s{i}-inner">{scene_html(sc, f, i)}</div></section>'
        for i, sc in enumerate(scenes, 1))

    # From frame one, not from the end of scene one. The rails carry the
    # wordmark and the address, and holding them back left every film opening
    # on an empty sheet while the first sentence faded up. A viewer who lands
    # on a blank frame has already decided what kind of video this is.
    rails_start = 0.0
    beats = "<i>\u00b7</i>".join(
        f'<span id="beat-{b}">{esc(say(BEAT_LABEL[b], lang))}</span>'
        for b in BEAT_ORDER)
    rails = (f'<div id="rails" class="clip" data-start="{rails_start}" '
             f'data-duration="{round(dur - rails_start, 2)}" data-track-index="90">'
             f'<div class="inner" id="rails-inner">'
             f'<p id="rail-l">Sprezzature</p><p id="rail-r">sprezzature.ai</p>'
             f'<div id="beats">{beats}</div>'
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

    # The wordmark and the address are on screen at frame zero, not fading
    # towards it. `fromTo({opacity:0}, ...)` at t=0 reads as "from frame one"
    # and is not: it puts the rails at exactly zero on the frame a viewer is
    # most likely to see as a still. Only the hairline under them is drawn,
    # and a hairline growing is not an empty frame.
    js.append(f'tl.fromTo("#rail-line",{{scaleX:0}},{{scaleX:1,duration:1.1,'
              f'ease:"expo.out"}},{rails_start:.2f});')

    # Light the beat the film is currently in, and put the previous one out.
    # Driven off the scenes themselves rather than a second table, so a scene
    # that moves takes its label with it. `set` and not a tween: a label that
    # cross-fades reads as two beats being true at once.
    lit = None
    for sc in scenes:
        if sc["beat"] == lit:
            continue
        at = max(0.0, sc["start"])
        if lit is not None:
            js.append(f'tl.set("#beat-{lit}",{{color:"#a3a3a3",fontWeight:500}},'
                      f'{at:.2f});')
        js.append(f'tl.set("#beat-{sc["beat"]}",{{color:"{BLUE}",fontWeight:700}},'
                  f'{at:.2f});')
        lit = sc["beat"]

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
    return html


def emit(film_key: str, spec: dict, fmt_key: str, lang: str = "en") -> pathlib.Path:
    """Write one project directory, and return it."""
    html = compose(film_key, spec, fmt_key, lang)
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

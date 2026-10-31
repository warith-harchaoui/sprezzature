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
import wave

ROOT = pathlib.Path(__file__).resolve().parent
FILMS_DIR = ROOT / "films"
ASSETS = ROOT / "_assets"
MUSIC = "happy-beats-business-moves-vol-12-by-ende-dot-app.mp3"

# ---------------------------------------------------------------------------
# Design tokens, taken from web/css/app.css, [data-color-mode=academic].
# ---------------------------------------------------------------------------
INK, INK_SOFT, BLUE, LINE, PAPER = "#171717", "#525252", "#0072b2", "#e5e5e5", "#ffffff"
NAVY = "#003c5d"  # brand-navy: the eyebrow rides over the wash, blue does not clear AA there

# Per-canvas scale. Portrait is watched full-screen on a phone, so its type is
# relatively larger; square gives up the most room and shrinks the figure.
FORMATS = {
    "landscape": dict(
        w=1920,
        h=1080,
        pad=104,
        hero=104,
        h2=44,
        body=38,
        mono=29,
        eyebrow=26,
        chip=32,
        split=True,
        fig=1010,
        grid6=3,
        shot=880,
        view=0.62,
    ),
    "portrait": dict(
        w=1080,
        h=1920,
        pad=72,
        hero=92,
        h2=52,
        body=44,
        mono=32,
        eyebrow=28,
        chip=31,
        split=False,
        fig=884,
        grid6=2,
        shot=780,
        view=1.05,
    ),
    "square": dict(
        w=1080,
        h=1080,
        pad=64,
        hero=74,
        h2=40,
        body=34,
        mono=26,
        eyebrow=23,
        chip=25,
        split=False,
        fig=600,
        grid6=3,
        shot=560,
        view=0.80,
    ),
}

# Beat grid of the bundled track, 109.96 BPM.
#
# Grown twice, the same way each time: 42 beats (23 s) hand-measured, then 111
# (60 s) on 2026-10-26, then 215 (117 s) on 2026-10-29 when the films went to
# the full length of the track. Not extrapolated: the pulse is walked at
# 60/109.96 and each step SNAPPED to the nearest detected onset within 120 ms,
# so a cut lands on the music rather than near it.
#
# The rule that governs every extension: A GROWN GRID DOES NOT MOVE THE BEATS
# THAT WERE ALREADY THERE. The first 111 entries below are byte for byte the
# ones the sixty-second films were cut against, and 96 of the 104 new ones sit
# exactly on an onset in
# `_assets/music/cues/<track>.music-cues.json` (207 detected beats, tempo
# 109.96, duration 117.36).
#
# Rebuilding instead of extending was tried first and refused on the evidence.
# The 2026-10-26 run read 483 onsets at 243.9 BPM, flagged uncertain because it
# had found subdivisions rather than the pulse; the cues file on disk today
# holds 207 at the pulse itself, and the committed grid coincides with only 5
# of them. A fresh walk over today's onsets reproduces the committed grid to a
# mean of 10 ms and moves 102 of its 111 entries. Ten milliseconds is inside a
# frame at 30 fps and would have been defensible; moving a beat that eleven
# films already point at is not, and the gain is nil. So the seam is at
# 60.539 -> 61.103, a 0.564 s gap that sits inside the grid's own spacing
# range (0.438 to 0.649).
BEATS = [
    0.549,
    1.106,
    1.637,
    2.181,
    2.736,
    3.288,
    3.819,
    4.368,
    4.912,
    5.471,
    5.995,
    6.549,
    7.088,
    7.653,
    8.181,
    8.731,
    9.28,
    9.819,
    10.368,
    10.917,
    11.461,
    12.005,
    12.549,
    13.093,
    13.643,
    14.187,
    14.731,
    15.28,
    15.819,
    16.368,
    16.912,
    17.467,
    18.005,
    18.555,
    19.099,
    19.648,
    20.187,
    20.741,
    21.28,
    21.829,
    22.368,
    22.923,
    23.461,
    24.005,
    24.549,
    25.104,
    25.643,
    26.192,
    26.741,
    27.285,
    27.824,
    28.379,
    28.923,
    29.467,
    30.005,
    30.555,
    31.099,
    31.643,
    32.187,
    32.741,
    33.28,
    33.824,
    34.368,
    34.923,
    35.461,
    36.011,
    36.555,
    37.104,
    37.643,
    38.192,
    38.736,
    39.28,
    39.824,
    40.373,
    40.917,
    41.461,
    42.005,
    42.549,
    43.163,
    43.648,
    44.187,
    44.741,
    45.285,
    45.824,
    46.368,
    46.917,
    47.467,
    48.011,
    48.56,
    49.104,
    49.648,
    50.187,
    50.741,
    51.28,
    51.829,
    52.373,
    52.943,
    53.488,
    54.034,
    54.58,
    55.125,
    55.671,
    56.217,
    56.747,
    57.308,
    57.957,
    58.395,
    58.928,
    59.451,
    60.036,
    60.539,
    # ---- 2026-10-29: the films went to the whole track ----
    61.103,
    61.637,
    62.195,
    62.729,
    63.286,
    63.832,
    64.377,
    64.911,
    65.469,
    66.003,
    66.56,
    67.106,
    67.651,
    68.197,
    68.743,
    69.288,
    69.834,
    70.38,
    70.925,
    71.459,
    72.017,
    72.551,
    73.108,
    73.642,
    74.199,
    74.733,
    75.291,
    75.825,
    76.382,
    76.916,
    77.473,
    78.007,
    78.565,
    79.099,
    79.656,
    80.19,
    80.747,
    81.281,
    81.839,
    82.373,
    82.93,
    83.464,
    84.01,
    84.555,
    85.101,
    85.647,
    86.204,
    86.738,
    87.295,
    87.829,
    88.375,
    88.921,
    89.466,
    90.001,
    90.558,
    91.092,
    91.649,
    92.183,
    92.74,
    93.275,
    93.832,
    94.366,
    94.923,
    95.457,
    96.014,
    96.549,
    97.106,
    97.64,
    98.197,
    98.731,
    99.288,
    99.823,
    100.38,
    100.914,
    101.471,
    102.005,
    102.562,
    103.097,
    103.654,
    104.2,
    104.745,
    105.279,
    105.837,
    106.371,
    106.928,
    107.462,
    108.019,
    108.553,
    109.111,
    109.645,
    110.202,
    110.736,
    111.293,
    111.827,
    112.326,
    112.919,
    113.465,
    114.011,
    114.557,
    115.103,
    115.649,
    116.195,
    116.741,
    117.287,
]


#: How long every film runs, and the one number a layout cannot negotiate.
#:
#: 117 s, which is not a round number and is not meant to be: it is the length
#: of the bundled track, 117.36 s, less the few hundred milliseconds it takes
#: the last beat to decay. A film that ends with its music needs no loop, no
#: fade and no silence to fill, and the grid above already reaches that far.
#:
#: It was 60 s until 2026-10-29. Sixty seconds held four beats comfortably and
#: the pitch now has seven, so the extra minute is not room to say more about
#: the same things: it is what the two new beats cost, the finest example the
#: package can show and the line the film ends on.
DURATION_S = 117.0


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
REWRITTEN = frozenset(
    {
        "sprezzature",
        "colors",
        "ux-laws",
        "maps",
        "figures",
        "publish",
        "audio",
        "cli-gui",
        "accessibility",
        "ui",
        "video",
    }
)


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
#: What the suite is, said before anything else in all eleven films: the
#: first sentence of the narration, and the first line on the first frame. A
#: viewer who lands on any one of them learns what the thing is before
#: learning which part of it they are watching.
TAGLINE = L(
    "Sprezzature is an AI engine for Design",
    "Sprezzature est un moteur d'IA pour le design",
)

BEAT_LABEL = {
    "what": L("What it is", "Ce que c'est"),
    "problem": L("Problem", "Le problème"),
    "solution": L("Solution", "La solution"),
    "magic": L("Secret sauce", "La recette"),
    "example": L("At its best", "Son plus bel exemple"),
    "cta": L("Your turn", "À vous"),
}

#: The spine, in the order a viewer needs it. Six labels on the rail for the
#: whole film, with the current one lit.
#:
#: `example` joined on 2026-10-29 and it is the beat that changes the films
#: most, because six of the eleven had no picture at all. The reason given in
#: `FILM-SHAPES.md` was sound as far as it went: these are films about text,
#: and a stock photograph would be a lie. The conclusion did not follow. This
#: suite makes pictures for a living, so a film about `audio` can show its own
#: cue track and a film about `publish` the icon set it just generated. A
#: picture the package itself produced is not an illustration, it is evidence.
BEAT_ORDER = ("what", "problem", "solution", "magic", "example", "cta")

#: The ask. Two of them, in the order of what they cost: a star is one click
#: from where the viewer already is, the site is a visit.
#:
#: The star points at the package the film is about, not at the hub. Somebody
#: who has just watched a minute on `maps` wants `sprezzature-maps`, and
#: sending them to the monorepo instead is a redirect dressed up as a
#: destination. The suite film is the one whose subject *is* the hub.
#: The last thing said, in every film.
#:
#: It is the suite's old motto, brought back on 2026-10-29 with its position
#: corrected rather than its words. It closed the films until 2026-10-28 and
#: was dropped for a reason worth keeping: "Pretty, and it requests nothing, a
#: viewer who liked the minute had nowhere to put that." That objection was
#: about where the line sat, not about the line. The ask comes first now and
#: the motto lands after it, so the viewer is given something to do while they
#: are still here, and something to repeat once they have gone.
PUNCHLINE = L(
    "Make it, audit it, take a look at it.",
    "Faites, auditez et regardez !",
)

GITHUB = "github.com/warith-harchaoui"


def cta_for(film_key: str) -> list[tuple[str, dict, str]]:
    """The two asks that close one film."""
    repo = "sprezzature" if film_key == "sprezzature" else f"sprezzature-{film_key}"
    return [
        ("\u2192", L("Go and look", "Allez voir"), "sprezzature.ai"),
        (
            "\u2605",
            L("Drop a star, if it deserves it", "Une étoile, si ça le mérite"),
            f"{GITHUB}/{repo}",
        ),
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
LOOP_STEPS = [
    ("01", L("render", "dessiner")),
    ("02", L("look", "regarder")),
    ("03", L("fix the source", "corriger la source")),
    ("04", L("again", "recommencer")),
]

FILMS = {
    # ---------------------------------------------------------------- global
    "sprezzature": dict(
        duration=DURATION_S,
        vo=[("sprezzature.en", 1.10)],
        sfx=[
            ("drop", 5.471),
            ("tile", 12.005),
            ("tile", 29.467),
            ("wipe", 57.308),
            ("tile", 74.199),
            ("bell", 104.745),
        ],
        scenes=[
            # ----------------------------------------------------------- what
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=10.5,
                end=10.4,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature",
                line=L(
                    "Design know-how, written as code.",
                    "Le savoir-faire du design, écrit en code.",
                ),
                url="sprezzature.ai",
            ),
            # -------------------------------------------------------- problem
            # Eight labels, one every one and a half seconds, each one a decision
            # somebody else settled and published. The chips are the evidence the
            # claim rests on, so they fall while the voice names four of them.
            dict(
                type="chips",
                beat="problem",
                start=10.3,
                dur=18.3,
                end=28.5,
                eyebrow=L("Settled by other people", "Décidé par d'autres"),
                items=[
                    L("30 laws of UX, YABLONSKI", "30 lois d'UX, YABLONSKI"),
                    L("WCAG contrast, the W3C", "contraste WCAG, le W3C"),
                    "MACHADO 2009",
                    L("Equal Earth, 2018", "Equal Earth, 2018"),
                    "Gestalt",
                    L("Netflix timed text", "sous-titrage Netflix"),
                    "Schema.org",
                    "OKLCH, OTTOSSON",
                ],
                at=on_beat(12.2, 13.9, 15.6, 17.3, 19.0, 20.7, 22.4, 24.1),
                caption=L(
                    "The laws of attention: Jon YABLONSKI. Contrast: the W3C. "
                    "Colour blindness: MACHADO, OLIVEIRA and FERNANDES, 2009.",
                    "Les lois de l'attention, c'est Jon YABLONSKI. Le contraste, "
                    "le W3C. Le daltonisme, MACHADO, OLIVEIRA et FERNANDES, 2009.",
                ),
            ),
            # ------------------------------------------------------- solution
            dict(
                type="versus",
                beat="solution",
                start=28.4,
                dur=13.2,
                end=41.5,
                eyebrow=L("The same rules, used twice", "Les mêmes règles, deux fois"),
                left=(
                    L("Make", "Fabriquer"),
                    L(
                        "a page, a figure, a map, a palette",
                        "une page, une figure, une carte, une palette",
                    ),
                ),
                right=(
                    L("Audit", "Auditer"),
                    L(
                        "the same ones, over what is already live",
                        "les mêmes, sur ce qui est déjà en ligne",
                    ),
                ),
                at=on_beat(29.6, 30.7),
                caption=L(
                    "167 chart kinds in 68 categories. 20 accessibility rules, "
                    "6 of them self-repairing. 30 laws of UX, 8 settled from the "
                    "source alone.",
                    "167 types de graphiques en 68 catégories. 20 règles "
                    "d'accessibilité, 6 réparables. 30 lois d'UX, 8 tranchées "
                    "depuis la source seule.",
                ),
            ),
            # The question the solution leaves open, held long enough to be felt
            # before the magic beat answers it.
            dict(
                type="claim",
                beat="solution",
                start=41.4,
                dur=6.7,
                end=48.0,
                line=L(
                    "A rule reads the file. Something has to read the picture.",
                    "Une règle lit le fichier. Reste à regarder l'image.",
                ),
            ),
            # ---------------------------------------------------------- magic
            # Eighteen seconds, the longest beat in the film, because the loop is
            # the only thing here that no published rule covers.
            dict(
                type="loop",
                beat="magic",
                start=47.9,
                dur=18.6,
                end=66.5,
                eyebrow=L("What no rule does", "Ce qu'aucune règle ne fait"),
                steps=LOOP_STEPS,
                fig="figures/bar-grouped.svg",
                gray="figures/bar-grouped-gray.svg",
                ratio=745 / 505,
                step_at=on_beat(49.0, 50.1, 51.2, 52.3),
                wipe_at=57.308,
                wipe_dur=1.09,
                caption_at=61.5,
                caption=L(
                    "The Ralph Eyeball Loop: the model edits the plan, never the "
                    "rendered image.",
                    "La boucle Ralph Eyeball : le modèle change le plan, jamais "
                    "l'image rendue.",
                ),
            ),
            # The clause the loop exists for, on its own frame. The narration says
            # it once at 53 s; this is the sentence a viewer carries out of the
            # magic beat, and it is the half the first cut of this film stopped
            # short of.
            dict(
                type="held",
                beat="magic",
                start=66.4,
                dur=6.7,
                end=73.0,
                line=L(
                    "What you fix is the source, never the picture.",
                    "Ce qu'on corrige, c'est la source, jamais l'image.",
                ),
            ),
            # -------------------------------------------------------- example
            # The montage, and the four pictures `FILM-SHAPES.md` reserves for
            # this film. One tile per kind of question: a correlation, a calendar,
            # a flow between places, a value per country.
            dict(
                type="grid",
                beat="example",
                start=72.9,
                dur=13.2,
                end=86.0,
                eyebrow=L("What those rules draw", "Ce que ces règles dessinent"),
                images=[
                    "figures/corr-matrix.svg",
                    "figures/calendar-heatmap.svg",
                    "figures/map-flow.svg",
                    "figures/choropleth.svg",
                ],
                at=on_beat(74.4, 76.1, 77.8, 79.5),
                caption=L(
                    "A matrix, a calendar, a migration flow, a choropleth: "
                    "4 of 167 kinds, each one hand-written SVG.",
                    "Une matrice, un calendrier, un flux migratoire, un "
                    "choroplèthe. 4 types sur 167, écrits à la main.",
                ),
            ),
            # Then the film chooses one and holds it, which is the whole argument
            # of the beat: the suite's own output, large enough to read, with the
            # published source of the thing a viewer is looking at named under it.
            dict(
                type="shot",
                beat="example",
                start=85.9,
                dur=12.2,
                end=98.0,
                eyebrow=L("10 corridors, one projection", "10 corridors, une projection"),
                src="figures/map-flow.svg",
                ratio=1480 / 1030,
                at=on_beat(87.0)[0],
                caption=L(
                    "Equal Earth, by ŠAVRIČ, PATTERSON and JENNY, 2018. "
                    "Line width is how many people moved.",
                    "Equal Earth, une projection publiée par ŠAVRIČ, "
                    "PATTERSON et JENNY en 2018. L'épaisseur du trait est "
                    "le nombre de personnes qui sont parties.",
                ),
            ),
            # ------------------------------------------------------------ cta
            # What the film ends on, and the claim a viewer has no other way to
            # hear. It replaced "Ten packages. Five surfaces each." on 2026-10-27,
            # which was a spec sheet and the least interesting thing on screen.
            dict(
                type="held",
                beat="cta",
                start=97.9,
                dur=7.2,
                end=105.0,
                line=L(
                    "Everything stays on your desk. Nothing travels.",
                    "Tout reste sur votre poste. Rien ne circule.",
                ),
            ),
            dict(
                type="cta",
                beat="cta",
                start=104.9,
                dur=12.1,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature",
                actions=cta_for("sprezzature"),
                punchline=PUNCHLINE,
                punch_at=111.293,
            ),
        ],
    ),
    # ------------------------------------------------------------------ colors
    "colors": dict(
        duration=DURATION_S,
        # Mostly picture. Twenty-three and a half seconds of the simulator in
        # one unbroken take, which is longer than any beat anywhere in the
        # set, and five short text scenes around it carrying the sentences a
        # picture cannot say for itself.
        vo=[("colors.en", 1.10)],
        sfx=[
            ("drop", on_beat(7.6)[0]),
            ("wipe", on_beat(18.1)[0]),
            ("tile", on_beat(28.6)[0]),
            ("wipe", on_beat(52.6)[0]),
            ("bell", on_beat(76.6)[0]),
        ],
        scenes=[
            # ------------------------------------------------------ WHAT  0
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=8.0,
                end=7.5,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature · colors",
                line=L(
                    "Colours everybody can read, proved rather than hoped.",
                    "Des couleurs que tout le monde peut lire, et la preuve avec.",
                ),
                url="sprezzature.ai",
            ),
            # --------------------------------------------------- PROBLEM  7.4
            # The failure first, and in the package's own words
            # (`README.md:7`). It is the sentence `FILM-SHAPES.md` quotes as
            # the shape a problem beat should have: a fact about a reader,
            # not a gap in a feature list. Held long enough to be read twice,
            # because the second reading is where "at your desk, indoors"
            # stops being a detail and becomes the accusation.
            dict(
                type="held",
                beat="problem",
                start=7.4,
                dur=10.7,
                end=18.0,
                line=L(
                    "Light grey on white reads perfectly well. At your desk, indoors.",
                    "Du gris clair sur du blanc se lit très bien. Chez vous, "
                    "à l'intérieur.",
                ),
            ),
            # The two readers who are not at that desk. Kept from the old cut
            # unchanged: it is the one scene in the film where two halves is
            # the right shape, because the two failures have nothing to do
            # with each other and arrive at the same button.
            dict(
                type="versus",
                beat="problem",
                start=17.9,
                dur=10.7,
                end=28.5,
                eyebrow=L(
                    "The same button, 2 readers", "Le même bouton, 2 lecteurs"
                ),
                left=(
                    L("Low vision", "Malvoyance"),
                    L(
                        "the text and the background merge",
                        "le texte et le fond se confondent",
                    ),
                ),
                right=(
                    L("Bright sunlight", "Plein soleil"),
                    L(
                        "the screen flattens the difference",
                        "l'écran écrase la différence",
                    ),
                ),
                at=on_beat(18.9, 20.5),
                caption=L(
                    "Whoever chose the colour can read it. That is the whole problem.",
                    "Celui qui a choisi la couleur, lui, la lit très bien. "
                    "C'est tout le problème.",
                ),
            ),
            # -------------------------------------------------- SOLUTION  28.4
            # The whole solution beat is one demonstration, and it is the
            # package failing. Said flat, at claim size, with nothing else on
            # the frame: four words a viewer can repeat.
            dict(
                type="claim",
                beat="solution",
                start=28.4,
                dur=10.7,
                end=39.0,
                line=L(
                    "It fails the palette it ships with.",
                    "Il échoue sur la palette qu'il livre.",
                ),
            ),
            # The verdict, with the number that makes it concrete. 56 pairs
            # because the default run checks only the pairs a rendered theme
            # can actually put together -- light labels on light surfaces,
            # dark on dark, brand accents on everything -- rather than the
            # cross product. 1.51:1 is Apple's `brand-yellow` on white, and
            # 4.5 is `WCAG_THRESHOLDS[("AA", "normal")]`.
            dict(
                type="versus",
                beat="solution",
                start=38.9,
                dur=13.7,
                end=52.5,
                eyebrow=L(
                    "Run with no arguments at all", "Lancé sans le moindre argument"
                ),
                left=(
                    L("34 pass", "34 passent"),
                    L(
                        "every label and brand colour, on every surface",
                        "chaque étiquette et chaque couleur de marque, sur chaque fond",
                    ),
                ),
                right=(
                    L("22 fail", "22 échouent"),
                    L(
                        "brand-yellow on white at 1.51:1, where text needs 4.5",
                        "brand-yellow sur blanc à 1,51:1, quand le texte demande 4,5",
                    ),
                ),
                at=on_beat(39.9, 43.9),
                caption=L(
                    "The process exits 1, so the build that called it stops.",
                    "Le processus sort en code 1, et la compilation qui "
                    "l'appelait s'arrête.",
                ),
            ),
            # ----------------------------------------------------- MAGIC  52.4
            # The sentence the whole package comes out of. It slept in a
            # module docstring (`scripts/accessibility_levels.py:31`) before
            # it reached the README, and it is seven words.
            dict(
                type="held",
                beat="magic",
                start=52.4,
                dur=11.7,
                end=64.0,
                line=L(
                    "Hue goes. Saturation goes. Lightness holds.",
                    "La teinte s'efface. La saturation s'efface. La clarté tient.",
                ),
            ),
            # The mechanism, which is a search nobody would guess and which
            # is the difference between a corrector and a replacement: hue
            # and chroma are frozen, the lightness axis is walked in 101 steps
            # of one hundredth, and of the candidates that clear the
            # threshold the one returned is the one whose lightness is
            # NEAREST the original. The axis is named because a mechanism
            # without a source is a boast.
            dict(
                type="versus",
                beat="magic",
                start=63.9,
                dur=12.7,
                end=76.5,
                eyebrow=L(
                    "The one axis the fix may move",
                    "Le seul axe que la correction déplace",
                ),
                left=(
                    L("Hue and chroma", "Teinte et chroma"),
                    L(
                        "held exactly where you put them",
                        "tenus exactement là où vous les avez mis",
                    ),
                ),
                right=(
                    L("Lightness", "Clarté"),
                    L(
                        "walked one hundredth at a time, until the pair clears",
                        "parcourue par centièmes, jusqu'à ce que la paire passe",
                    ),
                ),
                at=on_beat(64.9, 68.9),
                caption=L(
                    "OKLCH, by Björn OTTOSSON, where a step of lightness "
                    "looks like a step.",
                    "OKLCH, de Björn OTTOSSON, où un pas de clarté se voit "
                    "comme un pas.",
                ),
            ),
            # --------------------------------------------- AT ITS BEST  76.4
            # Twenty-three and a half seconds, one card, four wipes, and a
            # voice that says what to notice rather than what is there. These
            # are not an illustration: `simulate_cvd.py` produced them from
            # the suite's own grouped bar chart, and the five files are
            # already in `restore_assets.TRACKED` and already exempted in
            # `films_fr.ENGLISH_IN_FRENCH_CUTS`.
            #
            # Each wipe hands the frame to the next pair of eyes without a
            # cut, so what a viewer sees is one picture changing rather than
            # five pictures in a row -- which is the whole reason this type
            # exists and the reason it belongs to one film.
            #
            # The caption is the source and its limit in the same breath.
            # MACHADO's matrices are tabulated at eleven severity steps and
            # this package hard-codes 1.0, so what is on screen is complete
            # dichromacy; most real colour vision deficiency is anomalous
            # trichromacy, which is milder. Saying "measured on real
            # observers" is true. Saying "exactly what this person sees"
            # would not be, and the film does not say it.
            dict(
                type="cvd",
                beat="example",
                start=76.4,
                dur=23.7,
                end=100.0,
                eyebrow=L(
                    "The same chart, 4 pairs of eyes",
                    "Le même graphique, 4 regards",
                ),
                base="figures/cvd/00-original.png",
                stages=[
                    (
                        "01",
                        L("protanopia", "protanopie"),
                        "figures/cvd/01-protanopia.png",
                        on_beat(80.6)[0],
                    ),
                    (
                        "02",
                        L("deuteranopia", "deutéranopie"),
                        "figures/cvd/02-deuteranopia.png",
                        on_beat(85.4)[0],
                    ),
                    (
                        "03",
                        L("tritanopia", "tritanopie"),
                        "figures/cvd/03-tritanopia.png",
                        on_beat(90.2)[0],
                    ),
                    (
                        "04",
                        L("greyscale", "niveaux de gris"),
                        "figures/cvd/04-grayscale.png",
                        on_beat(95.0)[0],
                    ),
                ],
                ratio=1490 / 1010,
                wipe_dur=0.80,
                caption_at=on_beat(96.6)[0],
                caption=L(
                    "MACHADO, OLIVEIRA and FERNANDES, 2009. Full deficiency, "
                    "which is the severe end.",
                    "MACHADO, OLIVEIRA et FERNANDES, 2009. Déficience complète, "
                    "le cas le plus sévère.",
                ),
            ),
            # ------------------------------------------------ YOUR TURN  99.9
            dict(
                type="cta",
                beat="cta",
                start=99.9,
                dur=17.1,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature · colors",
                actions=cta_for("colors"),
                punchline=PUNCHLINE,
                punch_at=on_beat(109.0)[0],
            ),
        ],
    ),
    # ---------------------------------------------------------------- figures
    "figures": dict(
        duration=DURATION_S,
        # Rewritten 2026-10-29 from a fresh read of the package and of
        # LANDSCAPE.md, for 117 seconds and the seven-beat pitch.
        #
        # The problem is two problems and the film says both, because the
        # package answers both. You do not know which chart fits, and the
        # assistant you asked instead never looked at what it drew. The
        # first is answered deterministically, by the catalogue; the second
        # is answered by the Ralph Eyeball Loop, which is the one thing in
        # this suite that is not a rule.
        #
        # What is deliberately not promised: geospatial (choropleth and
        # situation_map left for sprezzature-maps; the eleven map-shaped
        # kinds that remain are marks in the shape of a country), animation
        # (seven kinds of 167), dashboards (one star in its own landscape,
        # assumed), and "no library" without its qualifier -- true of the
        # drawing, not of the [dataviz] extra.
        vo=[("figures.en", 1.10)],
        sfx=[
            ("drop", on_beat(8.9)[0]),
            ("tile", on_beat(28.9)[0]),
            ("tile", on_beat(47.5)[0]),
            ("tile", on_beat(77.5)[0]),
            ("bell", on_beat(88.4)[0]),
        ],
        scenes=[
            # WHAT
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=9.1,
                end=9.0,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature · figures",
                # Declared in films.yaml and checked by
                # `sprezzature-video verify` against figures.json. Keep the
                # wording with the value.
                line=L(
                    "167 chart kinds, every line of SVG written by hand.",
                    "167 types de graphiques, chaque trait de SVG écrit à la main.",
                ),
                url="sprezzature.ai",
            ),
            # PROBLEM
            dict(
                type="held",
                beat="problem",
                start=8.9,
                dur=9.2,
                end=18.0,
                line=L(
                    "A spreadsheet, and no chart in it is obviously the right one.",
                    "Un tableur, et aucun graphique ne s'impose vraiment.",
                ),
            ),
            dict(
                type="held",
                beat="problem",
                start=17.9,
                dur=9.7,
                end=27.5,
                # The second problem, and the one the package is actually
                # unusual for answering. render_checks.py names the three
                # failures seen in production: overlapping tick labels, a
                # leftover template title, a white panel on a dark page.
                line=L(
                    "The assistant drew it. Nothing in the chain ever looked.",
                    "L'assistant l'a dessiné. Personne, ensuite, ne l'a regardé.",
                ),
            ),
            # SOLUTION
            dict(
                type="grid",
                beat="solution",
                start=27.4,
                dur=11.7,
                end=39.0,
                eyebrow=L(
                    "One name, your rows, a file back",
                    "Un nom, vos lignes, un fichier en retour",
                ),
                images=[
                    "figures/sankey.svg",
                    "figures/alluvial.svg",
                    "figures/circle-packing.svg",
                    "figures/clustermap.svg",
                ],
                at=on_beat(28.9, 30.0, 31.1, 32.2),
                caption=L(
                    "167 kinds in 68 categories, and the catalogue "
                    "marks all 167 of them stable.",
                    "167 types répartis en 68 catégories, et le "
                    "catalogue les marque tous stables.",
                ),
            ),
            dict(
                # The beat FILM-SHAPES asks this film for: what separates a
                # hand-authored SVG from an exported one. A contrast, so a
                # versus; stated here, demonstrated at 87.4s on the hero.
                type="versus",
                beat="solution",
                start=38.9,
                dur=7.7,
                end=46.5,
                eyebrow=L(
                    "Written line by line, not exported",
                    "Écrit ligne à ligne, pas exporté",
                ),
                left=(
                    L("exported", "exporté"),
                    L("a picture of a chart", "une image de graphique"),
                ),
                right=(
                    L("written", "écrit"),
                    L("a document you can read", "un document qui se lit"),
                ),
                at=on_beat(39.8, 41.5),
                # 144, measured: `grep -l 'svg_open(' scripts/make_*.py |
                # wc -l` in sprezzature-figures. The docstring of
                # scripts/_svg.py says "~46 generators" and the body of the
                # same file says "nearly every generator"; the docstring is
                # the stale one.
                caption=L(
                    "SVG is Scalable Vector Graphics, and it is text. "
                    "144 of the 167 generators share one accessible root.",
                    "SVG, pour Scalable Vector Graphics, c'est du texte : "
                    "144 générateurs sur 167 en partagent la racine.",
                ),
            ),
            dict(
                type="grid",
                beat="solution",
                start=46.4,
                dur=11.2,
                end=57.5,
                eyebrow=L(
                    "Distributions, series, surfaces",
                    "Distributions, séries, surfaces",
                ),
                images=[
                    "figures/bellcurve.svg",
                    "figures/candlestick.svg",
                    "figures/kde2d-contour.png",
                    "figures/surface3d.png",
                ],
                at=on_beat(47.5, 48.6, 49.7, 50.8),
                caption=L(
                    "A title, a description, a dark twin and a "
                    "reduced-motion guard, inside the file.",
                    "Un titre, une description, un jumeau sombre et un "
                    "garde d'animation, dans le fichier.",
                ),
            ),
            # SECRET SAUCE
            dict(
                # Kept as a `verify` deliberately:
                # `test_the_film_counts_what_the_package_counts` reads this
                # scene by type and reads the claim whose English label
                # holds "fill". The count is re-measured there, from the
                # committed frame region-quarter-units.csv, and both spoken
                # cuts have to spell it.
                type="verify",
                beat="magic",
                start=57.4,
                dur=12.2,
                end=69.5,
                eyebrow=L(
                    "Every kind declares the data roles it needs",
                    "Chaque type déclare les rôles de données qu'il exige",
                ),
                claims=[
                    (
                        L("region, quarter, units", "région, trimestre, unités"),
                        L("3 columns", "3 colonnes"),
                    ),
                    # 64, measured: `make-figure recommend --data
                    # brag-output/region-quarter-units.csv --limit 500`.
                    # The columns are on screen because the count moves with
                    # them: the same three columns over six rows answer 62.
                    # KAWASAKI.md still says sixty-one, measured on a CSV
                    # that lived on one machine. That number is not used.
                    (
                        L("kinds those columns can fill", "types qu'elles remplissent"),
                        "64",
                    ),
                    (
                        L("ranked by readability", "classés par lisibilité"),
                        L("best first", "le meilleur d'abord"),
                    ),
                    (L("models consulted", "modèles consultés"), "0"),
                ],
                at=[
                    tuple(on_beat(58.4, 58.9)),
                    tuple(on_beat(60.0, 60.5)),
                    tuple(on_beat(61.6, 62.2)),
                    tuple(on_beat(63.3, 63.8)),
                ],
                caption=L(
                    "The ranking is a readable combination of signals, "
                    "settled before any model sees the list.",
                    "Le classement est une combinaison lisible de signaux, "
                    "tranchée avant qu'un modèle voie la liste.",
                ),
            ),
            dict(
                type="claim",
                beat="magic",
                start=69.4,
                dur=7.2,
                end=76.5,
                line=L(
                    "A rule cannot look at what it drew.",
                    "Une règle ne sait pas regarder ce qu'elle a dessiné.",
                ),
            ),
            dict(
                # The recipe, and the only thing in the suite that is not a
                # rule. `loop` belongs to the suite film and is not spread
                # here; the steps are chips, and the mechanism is in the
                # caption with its source named: which model, through what,
                # and where it runs.
                type="chips",
                beat="magic",
                start=76.4,
                dur=11.2,
                end=87.5,
                eyebrow=L("The Ralph Eyeball Loop", "La boucle Ralph Eyeball"),
                items=[
                    L("render", "dessiner"),
                    L("look", "regarder"),
                    L("write the critique", "écrire la critique"),
                    L("fix the source", "corriger la source"),
                    L("render again", "recommencer"),
                ],
                at=on_beat(77.5, 78.6, 79.7, 80.7, 81.8),
                caption=L(
                    "The looking is qwen3-vl:8b through Ollama, offline. "
                    "It edits the plan, never the picture.",
                    "Celui qui regarde est qwen3-vl:8b via Ollama, hors "
                    "ligne. Il modifie le plan, jamais l'image.",
                ),
            ),
            # AT ITS BEST
            dict(
                # One figure, held. Not a contact sheet: the two grids have
                # already shown breadth, and this beat is for the single
                # most beautiful thing the package emits. 11 ribbons and 5
                # arcs carry tabindex="0" and a <title>; the file also holds
                # a <desc>, an embedded font, a dark peer and a
                # reduced-motion guard. Measured on
                # _assets/figures/chord.svg.
                type="shot",
                beat="example",
                start=87.4,
                dur=15.2,
                end=102.5,
                eyebrow=L("chord, one of the 167", "chord, un des 167"),
                src="figures/chord.svg",
                ratio=1080 / 1140,
                at=on_beat(88.4)[0],
                caption=L(
                    "11 ribbons and 5 arcs, each one focusable, "
                    "each carrying its own numbers in a title.",
                    "11 rubans et 5 arcs, chacun atteignable au "
                    "clavier, chacun portant ses chiffres dans un titre.",
                ),
            ),
            # YOUR TURN
            dict(
                type="cta",
                beat="cta",
                start=102.4,
                dur=14.6,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature · figures",
                actions=cta_for("figures"),
                punchline=PUNCHLINE,
                punch_at=on_beat(110.2)[0],
            ),
        ],
    ),
    # ---------------------------------------------------------------- publish
    "publish": dict(
        duration=DURATION_S,
        # A pipeline film, written 2026-10-27 from `_readalong.py` rather than
        # from the tool list, and re-cut 2026-10-29 to the seven movements.
        # Its docstring still holds the best sentence in the package: a
        # read-along wrong by one sentence is worse than none, because it
        # tells a reader with confidence to look at the wrong line.
        #
        # So the module refuses to number sentences independently. It takes
        # the cues the narration actually produced, splits the rendered HTML
        # with the same splitter, compares the two lists, and raises on the
        # first divergence. "There is no third outcome where it wraps
        # something and hopes."
        #
        # The example beat is the only place in the suite where that sentence
        # can be seen rather than asserted, which is why it is worth the one
        # asset this film needs and does not yet have.
        vo=[("publish.en", 1.10)],
        sfx=[
            ("drop", 10.917),
            ("tile", 27.824),
            ("tile", 44.187),
            ("tile", 57.308),
            ("tile", 75.825),
            ("bell", 99.823),
        ],
        scenes=[
            # WHAT -------------------------------------------------------- 0
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=11.0,
                end=11.0,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature · publish",
                line=L(
                    "A folder of Markdown becomes a site somebody can find.",
                    "Un dossier de Markdown devient un site qu'on trouve.",
                ),
                url="sprezzature.ai",
            ),
            # PROBLEM ---------------------------------------------------- 11
            dict(
                type="held",
                beat="problem",
                start=10.9,
                dur=8.7,
                end=19.6,
                line=L(
                    "One sentence out of step is worse than no highlighting at all.",
                    "Une phrase de décalage vaut moins que pas de surlignage du tout.",
                ),
            ),
            dict(
                type="claim",
                beat="problem",
                start=19.5,
                dur=8.5,
                end=28.0,
                # `_readalong.py:7-9`. The word carrying the film is
                # "confidence": a highlight that is merely absent is a missing
                # feature, one that is wrong is an instruction to look at the
                # wrong line.
                line=L(
                    "It points at the wrong line, with confidence.",
                    "Il pointe la mauvaise ligne, avec assurance.",
                ),
            ),
            # SOLUTION: the pipeline -------------------------------------- 28
            dict(
                type="flow",
                beat="solution",
                start=27.9,
                dur=16.1,
                end=44.0,
                # Seven stages, and the eyebrow says seven of how many so the
                # frame does not read as a complete inventory. The caption
                # then says which ten: the repository's, not the wheel's.
                eyebrow=L("7 of the 10 tools", "7 des 10 outils"),
                stages=[
                    ("lint", L("standard library only", "bibliothèque standard")),
                    ("html", L("the pages", "les pages")),
                    ("meta", L("cards for a link", "cartes de partage")),
                    ("icons", L("1 logo, 11 files", "1 logo, 11 fichiers")),
                    ("indexes", L("6, for crawlers", "6, pour les robots")),
                    ("narrate", L("the voice, local", "la voix, en local")),
                    ("readalong", L("the two, bound", "les deux, liés")),
                ],
                at=on_beat(29.5, 31.1, 32.7, 34.4, 36.0, 37.6, 39.3),
                caption=L(
                    "10 tools in the repository. 9 in the package you "
                    "install today.",
                    "10 outils dans le dépôt. 9 dans le paquet publié "
                    "à ce jour.",
                ),
            ),
            dict(
                type="claim",
                beat="solution",
                start=43.9,
                dur=6.1,
                end=50.0,
                # The second half of what the package is for, and the half
                # nothing else in the suite does: a page a designer exported,
                # or one live for three years, with no Markdown to go back to.
                line=L(
                    "A page with no Markdown behind it is read the same way.",
                    "Une page sans Markdown derrière elle se lit de la même façon.",
                ),
            ),
            # SECRET SAUCE ------------------------------------------------ 50
            dict(
                type="claim",
                beat="magic",
                start=49.9,
                dur=7.3,
                end=57.2,
                line=L(
                    "The audio and the page leave the same Markdown by "
                    "different roads.",
                    "L'audio et la page quittent le même Markdown par 2 routes.",
                ),
            ),
            dict(
                type="versus",
                beat="magic",
                start=57.1,
                dur=9.9,
                end=67.0,
                eyebrow=L("2 roads, no guarantee", "2 routes, aucune garantie"),
                left=(
                    L("The voice", "La voix"),
                    L(
                        "sentences handed to the engine",
                        "des phrases remises au moteur",
                    ),
                ),
                right=(
                    L("The page", "La page"),
                    L("blocks walked as a tree", "des blocs parcourus comme un arbre"),
                ),
                at=on_beat(58.4, 60.0),
                caption=L(
                    "A regular expression cannot see a code fence "
                    "inside a list item. A tree walk can.",
                    "Une expression régulière ne voit pas un bloc de "
                    "code dans une puce. Un parcours d'arbre, oui.",
                ),
            ),
            dict(
                type="held",
                beat="magic",
                start=66.9,
                dur=9.1,
                end=76.0,
                line=L(
                    "They match, or it refuses. There is no third outcome.",
                    "Les deux coïncident, ou bien ça refuse. Il n'y a pas "
                    "de troisième issue.",
                ),
            ),
            # AT ITS BEST ------------------------------------------------- 76
            dict(
                type="shot",
                beat="example",
                start=75.9,
                dur=15.1,
                end=91.0,
                # The one thing this package makes that cannot be argued for
                # in prose. `shots/readalong.png` is the package's own README,
                # narrated by `narrate` and bound by `readalong`, paused on
                # the sentence being spoken. The French cut takes
                # `shots/fr/readalong.png`, the same page from `LISEZMOI.md`.
                # Both are built by the command at the foot of this file.
                #
                # The caption is the source, and it is the one line of the
                # film a viewer can go and check: the highlight is not timed
                # here at all.
                eyebrow=L(
                    "Its own README, reading itself",
                    "Son propre README, qui se lit",
                ),
                src="shots/readalong.png",
                ratio=4 / 3,
                at=on_beat(76.4)[0],
                caption=L(
                    "The browser parses the WebVTT cues and fires the events. "
                    "Nothing here polls a clock.",
                    "Le navigateur analyse les repères WebVTT et déclenche "
                    "les événements. Rien n'interroge d'horloge.",
                ),
            ),
            dict(
                type="held",
                beat="example",
                start=90.9,
                dur=9.1,
                end=100.0,
                line=L(
                    "Not one line of synchronisation code was written.",
                    "Pas une ligne de code de synchronisation n'a été écrite.",
                ),
            ),
            # YOUR TURN -------------------------------------------------- 100
            dict(
                type="cta",
                beat="cta",
                start=99.9,
                dur=17.1,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature · publish",
                actions=cta_for("publish"),
                punchline=PUNCHLINE,
                punch_at=on_beat(107.0)[0],
            ),
        ],
    ),
    # ------------------------------------------------------------------ audio
    "audio": dict(
        duration=DURATION_S,
        # Nine scenes. The five-scene cut this replaces was written for a
        # sixty-second film and still carried a `cta` with `dur=4.6` inside a
        # 117-second shell.
        vo=[("audio.en", 1.10)],
        sfx=[
            ("drop", on_beat(5.5)[0]),
            ("tile", on_beat(28.9)[0]),
            ("tile", on_beat(51.9)[0]),
            ("tile", on_beat(77.9)[0]),
            ("bell", on_beat(100.9)[0]),
        ],
        scenes=[
            # ----------------------------------------------------------- WHAT
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=11.5,
                end=11.0,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature · audio",
                line=L(
                    "Speech, read both ways, on your own machine.",
                    "La parole, lue dans les deux sens, sur votre machine.",
                ),
                url="sprezzature.ai",
            ),
            # -------------------------------------------------------- PROBLEM
            # The failure, in the direction everybody has met. The sentence is
            # `scripts/audit_captions.py:7`, shortened to what fits a frame:
            # "a perfectly accurate caption that holds 90 characters on screen
            # for half a second is unreadable".
            dict(
                type="held",
                beat="problem",
                start=10.9,
                dur=9.1,
                end=20.0,
                line=L(
                    "90 characters, on screen for half a second.",
                    "90 caractères, affichés une demi-seconde.",
                ),
            ),
            # The same failure, turned around -- which is this film's shape
            # arriving before its solution does. A narrated page that highlights
            # the sentence being read is the other direction of one modality, and
            # it fails the same way: not by being wrong, by being out of step.
            dict(
                type="claim",
                beat="problem",
                start=19.9,
                dur=9.1,
                end=29.0,
                line=L(
                    "A sentence out of step points at the wrong line, with confidence.",
                    "Une phrase de retard désigne la mauvaise ligne, avec aplomb.",
                ),
            ),
            # ------------------------------------------------------- SOLUTION
            # The symmetry, side by side. Two lanes, and underneath each of them
            # the same two files -- which is the whole claim, and the reason a
            # page can follow a reading without a second alignment pass.
            dict(
                type="versus",
                beat="solution",
                start=28.9,
                dur=15.1,
                end=44.0,
                eyebrow=L(
                    "One modality, read in both directions",
                    "Une modalité, lue dans les deux sens",
                ),
                left=(
                    L("Sound into text", "Du son vers le texte"),
                    L(
                        "What was said, who said it, in which language.",
                        "Ce qui a été dit, par qui, dans quelle langue.",
                    ),
                ),
                right=(
                    L("Text into sound", "Du texte vers le son"),
                    L(
                        "A WAV, and its WebVTT lying beside it.",
                        "Un WAV, et son WebVTT posé juste à côté.",
                    ),
                ),
                at=on_beat(30.0, 37.0),
                caption=L(
                    "Both lanes run here, and nothing is sent anywhere.",
                    "Les deux voies tournent ici, et rien n'est envoyé ailleurs.",
                ),
            ),
            dict(
                type="claim",
                beat="solution",
                start=43.9,
                dur=8.1,
                end=52.0,
                line=L(
                    "The same timed track, whichever direction wrote it.",
                    "La même piste minutée, quel que soit le sens qui l'a écrite.",
                ),
            ),
            # ---------------------------------------------------------- MAGIC
            # Five numbers, all five already declared in `films.yaml` and all
            # five re-measured against `scripts/audit_captions.py` on 2026-10-29:
            # DEFAULT_CPS 17.0, DEFAULT_LINE_CHARS 42, DEFAULT_MIN_SECONDS 5 / 6,
            # DEFAULT_MAX_SECONDS 7.0, DEFAULT_MAX_LINES 2. Unchanged.
            #
            # They are the inventory. The caption and the scene after it are the
            # insight, which is what this rewrite exists to put back.
            dict(
                type="verify",
                beat="magic",
                start=51.9,
                dur=18.1,
                end=70.0,
                eyebrow=L(
                    "Netflix's timed text style guide",
                    "Le guide de sous-titrage de Netflix",
                ),
                claims=[
                    (
                        L(
                            "reading speed, characters a second",
                            "vitesse de lecture, caractères par seconde",
                        ),
                        "17",
                    ),
                    (L("characters on one line", "caractères sur une ligne"), "42"),
                    (
                        L("shortest a cue may be", "durée minimale d'un sous-titre"),
                        L("5/6 s", "5/6 s"),
                    ),
                    (
                        L(
                            "longest before it has swallowed a sentence",
                            "durée au-delà de laquelle il a avalé une phrase",
                        ),
                        L("7 s", "7 s"),
                    ),
                    (
                        L(
                            "lines, on which BBC and Netflix agree",
                            "lignes, sur quoi la BBC et Netflix s'accordent",
                        ),
                        "2",
                    ),
                ],
                at=[
                    on_beat(54.0, 54.6),
                    on_beat(56.2, 56.8),
                    on_beat(58.4, 59.0),
                    on_beat(60.6, 61.2),
                    on_beat(62.8, 63.4),
                ],
                caption=L(
                    "A children's programme and a dense talk justify different numbers.",
                    "Une émission pour enfants et une conférence dense "
                    "n'appellent pas les mêmes.",
                ),
            ),
            # The sentence the old cut never reached. Not a callback: the thing
            # that makes the five numbers worth a minute of anybody's attention.
            dict(
                type="held",
                beat="magic",
                start=69.9,
                dur=8.1,
                end=78.0,
                line=L(
                    "Conventions, not laws. Each one is a dial.",
                    "Des conventions, pas des lois. Chacune est un réglage.",
                ),
            ),
            # -------------------------------------------------------- EXAMPLE
            # The brick's own drawing, scrolled slowly from the two lanes down to
            # the one gate they both end at. The eyebrow names the file so the
            # viewer knows this is a figure in the repository rather than
            # something the film drew for the occasion.
            #
            # The voice over it does not describe it. It says what to notice: the
            # two lanes do not stay apart.
            dict(
                type="shot",
                beat="example",
                start=77.9,
                dur=23.1,
                end=101.0,
                eyebrow=L(
                    "assets/how-it-works.svg, in the repository",
                    "assets/comment-ca-marche.svg, dans le dépôt",
                ),
                src="figures/audio-how-it-works.svg",
                ratio=980 / 928,
                scroll=True,
                at=on_beat(78.6)[0],
                caption=L(
                    "2 lanes out of one input, and one gate at the bottom for both.",
                    "2 voies depuis une seule entrée, et un seul contrôle en bas.",
                ),
            ),
            # ------------------------------------------------------------ CTA
            dict(
                type="cta",
                beat="cta",
                start=100.9,
                dur=16.1,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature · audio",
                actions=cta_for("audio"),
                punchline=PUNCHLINE,
                punch_at=on_beat(108.0)[0],
            ),
        ],
    ),
    # ---------------------------------------------------------------- cli-gui
    "cli-gui": dict(
        duration=DURATION_S,
        # Shape: before and after. Two `versus` scenes carry the film, because
        # the subject is a pair twice over -- a line you type against a page
        # you click, and a parser read directly against a help screen read as
        # text. The scene type is this film's own (`FILM-SHAPES.md`), so using
        # it twice sharpens the identity rather than diluting it.
        #
        # Three things in the package that the feature list does not have, and
        # that this cut is built around.
        #
        # A Typer app is converted with typer's own `get_command` and then
        # walked as Click, "because that is what it becomes; there is no third
        # adapter". A third one would be a second implementation of Click,
        # free to drift from the first.
        #
        # The trap that makes the page lie: a Click Group's name defaults to
        # the decorated function's name, usually `main`, rather than the
        # installed console script. The package falls into it itself --
        # `walk(load_parser_from_spec("sprezzature_cli_gui.cli:main"))["prog"]`
        # answers `main`, measured 2026-10-29.
        #
        # And `audit.py`, the half nobody would think to build. Its opening
        # docstring is the best sentence in the package and sits in a module
        # no viewer will ever open, so the film puts it on screen:
        # "A page that silently drops a flag looks entirely correct: the form
        # renders, the fields work, the built command line is valid shell."
        # (`sprezzature_cli_gui/audit.py:6-9`)
        vo=[("cli-gui.en", 1.10)],
        sfx=[
            ("drop", on_beat(10.9)[0]),
            ("tile", on_beat(27.9)[0]),
            ("tile", on_beat(49.9)[0]),
            ("tile", on_beat(79.9)[0]),
            ("bell", on_beat(100.9)[0]),
        ],
        scenes=[
            # WHAT
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=11.1,
                end=11.0,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature \u00b7 cli-gui",
                line=L(
                    "Your command line, as a form anybody can fill in.",
                    "Votre ligne de commande, en formulaire que tout le monde remplit.",
                ),
                url="sprezzature.ai",
            ),
            # PROBLEM
            dict(
                type="held",
                beat="problem",
                start=10.9,
                dur=10.2,
                end=21.0,
                line=L(
                    "Your colleague needs this tool. They will not open a terminal.",
                    "Votre collègue a besoin de cet outil. Il n'ouvrira "
                    "pas de terminal.",
                ),
            ),
            # PROBLEM, second half: the hand-built form, which is the thing
            # `audit.py` exists to stop happening to a generated one.
            dict(
                type="claim",
                beat="problem",
                start=20.9,
                dur=7.2,
                end=28.0,
                line=L(
                    "So you build the form by hand. Then the tool grows a flag.",
                    "Alors vous bricolez le formulaire. Puis l'outil gagne un drapeau.",
                ),
            ),
            # SOLUTION: the signature scene. A line on the left, the page it
            # became on the right. `make-figure render bar` is a real
            # invocation of the command the two captures below were taken
            # from, so the left half and the right half are the same tool.
            dict(
                type="versus",
                beat="solution",
                start=27.9,
                dur=12.2,
                end=40.0,
                eyebrow=L("Before, and after", "Avant, et après"),
                left=(
                    "$ make-figure render bar",
                    L(
                        "Typed from memory, in the order the tool wants it.",
                        "Tapée de mémoire, dans l'ordre que l'outil attend.",
                    ),
                ),
                right=(
                    "make-figure.html",
                    L(
                        "One field per flag, with its default already in the box.",
                        "Un champ par drapeau, sa valeur par défaut déjà dedans.",
                    ),
                ),
                at=on_beat(29.2, 31.0),
                caption=L(
                    "Options become fields. Choices become a list. "
                    "Required stays required.",
                    "Les options deviennent des champs. Les choix, une "
                    "liste. L'obligatoire reste obligatoire.",
                ),
            ),
            # SOLUTION: the two captures, which are the argument. Both are
            # taken from `sprezzature_figures.cli:main` through the installed
            # `sprezzature-cli-gui`, so what they show is whatever the command
            # prints today rather than a page shot once in September.
            dict(
                type="grid",
                beat="solution",
                start=39.9,
                dur=10.2,
                end=50.0,
                eyebrow=L(
                    "Generated from the command, not written",
                    "Engendré depuis la commande, pas écrit",
                ),
                images=["shots/make-figure-list.png", "shots/make-figure-render.png"],
                at=on_beat(41.2, 42.8),
                caption=L(
                    "One HTML file. No server, no port, and not one line "
                    "added to the tool.",
                    "Un fichier HTML. Aucun serveur, aucun port, pas une "
                    "ligne ajoutée à l'outil.",
                ),
            ),
            # SECRET SAUCE, and its source named: the parser object the tool
            # already built for itself. Counting the parts was an inventory,
            # and the suite's own pitch checker said so -- "Three frameworks,
            # two adapters" has the shape of "Ten packages. Five surfaces
            # each.", the line that checker was written against. The insight
            # is why there are two adapters and not three, so that is what the
            # caption says.
            dict(
                type="versus",
                beat="magic",
                start=49.9,
                dur=14.2,
                end=64.0,
                eyebrow=L(
                    "Read the parser, or read the help screen",
                    "Lire l'analyseur, ou lire l'écran d'aide",
                ),
                left=(
                    "argparse, Click, Typer",
                    L(
                        "The parser object the tool already built, walked "
                        "field by field.",
                        "L'objet analyseur que l'outil a déjà construit, lu "
                        "champ par champ.",
                    ),
                ),
                right=(
                    "--from-help",
                    L(
                        "The tool's own help screen, read as text. Lower "
                        "fidelity, and it says so.",
                        "L'écran d'aide de l'outil, lu comme du texte. Moins "
                        "fidèle, et il le dit.",
                    ),
                ),
                at=on_beat(51.2, 56.6),
                caption=L(
                    "A Typer application is already Click once you ask it, "
                    "so there is no third adapter.",
                    "Une application Typer est déjà du Click dès qu'on le "
                    "lui demande : pas de troisième adaptateur.",
                ),
            ),
            # SECRET SAUCE: the sentence from `audit.py:6-9`, which is the
            # whole reason the package ships an auditor at all.
            dict(
                type="held",
                beat="magic",
                start=63.9,
                dur=8.2,
                end=72.0,
                line=L(
                    "A page that silently drops a flag looks entirely correct.",
                    "Une page qui laisse tomber un drapeau en silence a l'air "
                    "parfaitement correcte.",
                ),
            ),
            # SECRET SAUCE: and what the auditor does about it. Five rules,
            # recounted 2026-10-29:
            #   grep -o 'rule="[a-z-]*"' sprezzature_cli_gui/audit.py | sort -u
            #   -> choice-dropped, field-has-no-flag, flag-not-in-page,
            #      prog-mismatch, prog-missing
            # Each message names the consequence rather than the difference,
            # which `tests/test_the_page_still_covers_the_cli.py` enforces.
            dict(
                type="claim",
                beat="magic",
                start=71.9,
                dur=8.2,
                end=80.0,
                line=L(
                    "5 rules, and each one names what the user loses.",
                    "5 règles, et chacune nomme ce que l'utilisateur perd.",
                ),
            ),
            # AT ITS BEST. The page `docker` becomes, scrolling. Not a
            # terminal shot: this is the package's own output, and its size is
            # the argument -- `docker` is Go, nothing here can import a line
            # of it, and it still came out as 57 sections and 1,307 fields.
            #
            # Measured 2026-10-29 from a clone, both numbers in one command:
            #
            #   python -c "
            #   from sprezzature_cli_gui.adapters.help_text import walk_from_help
            #   from sprezzature_cli_gui.renderer import render_html
            #   t = walk_from_help('docker')
            #   print(len(t['sub_commands']), render_html(t).count('data-cli-flag='))"
            #   # 57 1307
            #
            # The capture, which needs docker on PATH, playwright, and a
            # network for the Tailwind Play CDN the emitted page loads:
            #
            #   sprezzature-cli-gui --from-help docker --out docker.html
            #   python - <<'PY'
            #   import pathlib
            #   from playwright.sync_api import sync_playwright
            #   url = pathlib.Path("docker.html").resolve().as_uri()
            #   W, H = 1040, 4400
            #   with sync_playwright() as p:
            #       b = p.chromium.launch()
            #       pg = b.new_page(viewport={"width": W, "height": H},
            #                       device_scale_factor=1)
            #       pg.goto(url); pg.wait_for_timeout(2500)
            #       pg.evaluate("""() => {
            #         [...document.querySelectorAll('details')]
            #           .filter(d => !d.parentElement.closest('details'))
            #           .forEach(d => d.open =
            #             d.querySelector('summary').textContent.trim() === 'run');
            #       }""")
            #       pg.wait_for_timeout(800)
            #       pg.screenshot(path="_assets/shots/docker-run.png")
            #       b.close()
            #   PY
            #
            # 4400px and not the whole 6650px collapsed page, and not the
            # 65558px with every group open: the scroll speed is the image
            # height divided by the scene, and at 4400 a field stays on screen
            # about 2.8 s in landscape, 4.7 s in portrait. The whole page would
            # be a smear, and the collapsed one is 57 grey bars with no fields
            # in them at all. One group open is what makes it a wall of flags.
            dict(
                type="shot",
                beat="example",
                start=79.9,
                dur=21.2,
                end=101.0,
                eyebrow=L(
                    "docker, which is written in Go and cannot be imported",
                    "docker, écrit en Go et impossible à importer",
                ),
                src="shots/docker-run.png",
                ratio=1040 / 4400,
                scroll=True,
                at=on_beat(80.6)[0],
                caption=L(
                    "57 sub-commands and 1,307 form fields, read off its "
                    "help screen in one pass.",
                    "57 sous-commandes et 1 307 champs, lus sur son écran "
                    "d'aide en une seule passe.",
                ),
            ),
            # YOUR TURN
            dict(
                type="cta",
                beat="cta",
                start=100.9,
                dur=16.2,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature \u00b7 cli-gui",
                actions=cta_for("cli-gui"),
                punchline=PUNCHLINE,
                punch_at=on_beat(109.0)[0],
            ),
        ],
    ),
    # --------------------------------------------------------------------- ui
    "ui": dict(
        duration=DURATION_S,
        # The smallest package, and the one whose pitch is easiest to get
        # wrong in either direction. Rewritten 2026-10-29 from
        # `notes/ui.md`, which read the repository rather than the feature
        # list.
        #
        # The difficulty is that the brick has two storeys of different
        # natures. The Python half is deterministic: it walks a tree, finds
        # strings that belong in a catalogue, scaffolds the catalogue,
        # compiles it and emits the two loaders that read it. The other half,
        # writing the interface, is prose a model reads -- 64 reference files,
        # 4772 lines, and no command behind any of it. A film that promises
        # "an interface" and ships a string scanner lies; a film that only
        # dares say "it finds strings" undersells the larger half. So the
        # word the whole film hangs on is HALF, said on the first frame and
        # again over the last picture, because it names the other storey
        # instead of hiding it.
        #
        # Two things KAWASAKI.md says about this brick are not said here, on
        # the evidence in `notes/ui.md`:
        #
        #   * "anything it could not parse with certainty is reported as
        #     needing a hand rather than dropped in silence" -- false today.
        #     On the commonest catalogue shape `extract_js()` returns zero
        #     entries and zero notes while the audit still flags the lines
        #     (`scripts/audit_i18n.py:363-366`), so `--fix` says "1 string(s)
        #     moved" meaning "1 of the ones I could read". The film shows the
        #     part that holds: it writes the catalogue and stops at the call
        #     site.
        #   * "it finds the sentences hardcoded in your source" -- too wide.
        #     It finds two named shapes, and the `versus` scene names both
        #     rather than claiming the class.
        #
        # The secret sauce is the one mechanism in this brick that exists
        # nowhere else in the landscape read for LANDSCAPE.md: a prompt
        # declares the single locale it was engineered and tested in, and a
        # missing translation resolves to that text rather than to the first
        # declared locale or to the message id. Its source is named in the
        # voice and it is not a borrowed one: the package measured it, in
        # `tests/eval/test_prompt_locale_eval.py`, with a local model over
        # both locales. The film states the method and never the score, for
        # the reason the note gives -- the score is the output of a
        # non-deterministic local model and moves with the machine.
        vo=[("ui.en", 1.10)],
        sfx=[
            ("drop", 10.92),
            ("tile", 28.92),
            ("tile", 51.28),
            ("tile", 79.10),
            ("bell", 100.38),
        ],
        scenes=[
            # WHAT ------------------------------------------------------- 0-11
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=11.5,
                end=11.0,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature \u00b7 ui",
                # Both storeys on the first frame, in that order, because
                # frame zero is the poster and the thumbnail. The viewer is
                # told what the model does before being told what the command
                # does, so nothing later has to walk a promise back.
                line=L(
                    "The model writes your screen. A command files its sentences.",
                    "Le modèle écrit votre écran. Une commande en range les phrases.",
                ),
                url="sprezzature.ai",
            ),
            # PROBLEM --------------------------------------------------- 11-29
            dict(
                type="held",
                beat="problem",
                start=10.9,
                dur=9.2,
                end=20.0,
                # The best cost sentence in the suite, kept word for word from
                # `README.md:33-35`. It was already the line this film held.
                line=L(
                    "It costs a week the day somebody needs a second language.",
                    "Elle coûte une semaine le jour où il faut une deuxième langue.",
                ),
            ),
            dict(
                type="claim",
                beat="problem",
                start=19.9,
                dur=9.2,
                end=29.0,
                # The second pile, and the reason it is a different problem.
                # From `tests/eval/test_prompt_locale_eval.py:4-7`, the best
                # formulation of the mechanism and the one nobody will ever
                # open the file to read.
                line=L(
                    "You see a missing label. A missing prompt, the model answers anyway.",
                    "Un libellé absent se voit. Un prompt absent, le modèle répond quand même.",
                ),
            ),
            # SOLUTION ---------------------------------------------- 29-51.5
            dict(
                type="versus",
                beat="solution",
                start=28.9,
                dur=12.7,
                end=41.5,
                eyebrow=L(
                    "2 shapes a sentence hides in",
                    "2 formes où une phrase se cache",
                ),
                left=(
                    "I18N001",
                    L(
                        "a locale table living in JavaScript",
                        "une table de langues qui vit dans le JavaScript",
                    ),
                ),
                right=(
                    "I18N002",
                    L(
                        "a model prompt inlined in Python",
                        "un prompt de modèle écrit en dur en Python",
                    ),
                ),
                at=on_beat(30.4, 32.2),
                # The honesty that keeps the film from overclaiming, on screen
                # rather than in a footnote. `eslint-plugin-i18next` does the
                # wide job and LANDSCAPE.md says so; this one is narrow on
                # purpose and that is what makes it standard library only, and
                # therefore cheap enough to run on every commit.
                caption=L(
                    "2 shapes, not every literal. Precise on purpose, "
                    "and cheap enough for every commit.",
                    "2 formes, pas toute chaîne. Précis exprès, "
                    "et assez léger pour chaque commit.",
                ),
            ),
            dict(
                type="held",
                beat="solution",
                start=41.4,
                dur=10.2,
                end=51.5,
                # Where `--fix` stops, which is the whole of the make half's
                # manners. `pybabel extract` stops in the same place and for
                # the same reason, named in the voice over this scene.
                line=L(
                    "It writes the catalogue, and leaves your call site alone.",
                    "Il écrit le catalogue, et ne touche pas à votre appel.",
                ),
            ),
            # SECRET SAUCE ------------------------------------------- 51.5-79
            dict(
                type="claim",
                beat="magic",
                start=51.4,
                dur=13.2,
                end=64.5,
                # `scripts/i18n_make.py:59-61`, compressed: a reordered clause
                # or a softened imperative moves what the model does, so a
                # prompt is not a label and cannot be treated like one.
                line=L(
                    "A prompt is not a label. It has one language it was tested in.",
                    "Un prompt n'est pas un libellé. Il a la langue où il a été éprouvé.",
                ),
            ),
            dict(
                type="held",
                beat="magic",
                start=64.4,
                dur=14.7,
                end=79.0,
                # The longest hold in the film, on the sentence the film
                # exists to leave behind. The resolution rule in full is three
                # lines: en -> en, fr -> fr with validated_locale_used False,
                # de -> en with it True. Reproduced on 2026-10-29 against the
                # emitted `locales/i18n_prompts.py`.
                line=L(
                    "A missing translation falls back to the tested language, and says so.",
                    "Une traduction absente retombe sur la langue éprouvée, et le dit.",
                ),
            ),
            # AT ITS BEST ----------------------------------------- 79-100.5
            dict(
                type="shot",
                beat="example",
                start=78.9,
                dur=21.7,
                end=100.5,
                # The finest thing this brick makes, and it is a file. It is
                # the only place in the package where both natures of string
                # sit in one frame, which is the film's whole argument shown
                # instead of argued: interface labels under `gui:`, model
                # prompts under `prompts:`, and the second kind carrying a key
                # the first never needs. The slow scroll ends on
                # `validated: en`, so the picture arrives at the point at the
                # same moment the voice does.
                #
                # 41 lines, counted on the file the command writes, not quoted
                # from anywhere. The scroll shows roughly half the file at a
                # time in landscape, nearly all of it in portrait.
                eyebrow=L(
                    "locales/i18n.yaml, written by one command",
                    "locales/i18n.yaml, écrit par une seule commande",
                ),
                src="shots/ui-catalogue.png",
                ratio=1240 / 1560,
                scroll=True,
                at=on_beat(79.8)[0],
                caption=L(
                    "Labels under gui, prompts under prompts, "
                    "and one key only the second kind needs.",
                    "Les libellés sous gui, les prompts sous prompts, "
                    "et une clé que seuls les seconds portent.",
                ),
            ),
            # YOUR TURN ------------------------------------------- 100.4-117
            dict(
                type="cta",
                beat="cta",
                start=100.4,
                dur=16.6,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature \u00b7 ui",
                actions=cta_for("ui"),
                punchline=PUNCHLINE,
            ),
        ],
    ),
    # ------------------------------------------------------------------ video
    # The tenth brick, and the one that made the other nine films. Its subject
    # is the films themselves, which is why it can afford to be plain: every
    # scene is a sentence about the thing the viewer is currently watching.
    "video": dict(
        duration=DURATION_S,
        # The brick that checks the other ten, and the film that lies most
        # easily, because it is about the thing that catches lying films.
        #
        # Its shape is the one `FILM-SHAPES.md` gave it on 2026-10-27: the
        # film audits itself while it plays. That shape is kept and doubled,
        # because the package checks in two directions and now so does the
        # film. The solution beat is `verify` pointed at the code -- declared
        # claims, read back out of the files that decide them. The example
        # beat is `verify` pointed at THIS COMPOSITION -- `scan`, with its
        # real verdict, finding a number the film cannot account for.
        #
        # Three things this film deliberately does not say, each from
        # `notes/video.md` section 7:
        #
        #   * that the renderer sits behind a seam. `sprezzature_video/
        #     renderers/` is an empty directory with no `__init__.py`. It is
        #     an architectural intention, not a module, so it is off screen
        #     and out of the voice.
        #   * that the suite verifies its own films. It verifies the DECLARED
        #     claims, since 2026-10-28. `scan`, `assets` and `prose` are
        #     wired nowhere. The example beat shows `scan` being run, which
        #     is honest: run, by somebody, on purpose.
        #   * that the shipped captions hold the budget. They do not, and
        #     that is the `audio` film's number to carry, not this one's.
        vo=[("video.en", 1.10)],
        sfx=[
            ("drop", on_beat(9.7)[0]),
            ("tile", on_beat(29.9)[0]),
            ("tile", on_beat(66.8)[0]),
            ("bell", on_beat(87.8)[0]),
        ],
        scenes=[
            # ------------------------------------------------------ WHAT
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=9.7,
                end=9.6,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature · video",
                line=L(
                    "What a film says, checked against the code it describes.",
                    "Ce qu'un film affirme, vérifié sur le code qu'il décrit.",
                ),
                url="sprezzature.ai",
            ),
            # --------------------------------------------------- PROBLEM
            # The repository's own history, and the only number on screen
            # that `scan` cannot account for. It is here on purpose and the
            # example beat says so out loud.
            dict(
                type="held",
                beat="problem",
                start=9.5,
                dur=9.2,
                end=18.6,
                line=L(
                    "This suite told viewers it had 127 chart kinds, for "
                    "months after it had 167.",
                    "Cette suite a annoncé 127 types de graphiques des mois "
                    "après en avoir eu 167.",
                ),
            ),
            dict(
                type="claim",
                beat="problem",
                start=18.5,
                dur=8.6,
                end=27.0,
                line=L(
                    "The film is the one artefact that lives outside the code.",
                    "Le film est le seul objet de la suite qui vit hors du code.",
                ),
            ),
            # -------------------------------------------------- SOLUTION
            # Direction one: declared claims, read back out of the files
            # that decide them. All four hold today -- `sprezzature-video
            # verify brag-output/films.yaml --root ~` answers 10/10, run
            # 2026-10-29.
            #
            # The fourth row used to be "assets, checked against the ledger
            # 81" and it is gone, which is the single biggest change here.
            # 81 is true (`python3 restore_assets.py` answers 81/81 today)
            # and it is UNDECLARABLE: it comes from walking a tree git does
            # not track, so none of the five dull methods can read it, which
            # is exactly what the header of `films.yaml` says. Its guard in
            # the hub skipped in every clone, so the largest number in the
            # film was protected only on the author's machine. A number the
            # spec cannot hold is a number this film of all films may not
            # show. The row that replaced it is a declared claim with an
            # integer value, like the other three.
            dict(
                type="verify",
                beat="solution",
                start=26.9,
                dur=23.2,
                end=50.0,
                eyebrow=L(
                    "What the code says today",
                    "Ce que le code dit aujourd'hui",
                ),
                claims=[
                    (
                        L(
                            "chart kinds, in the catalogue",
                            "types de graphiques, au catalogue",
                        ),
                        "167",
                    ),
                    (
                        L(
                            "accessibility rules, in the linter",
                            "règles d'accessibilité, au linter",
                        ),
                        "20",
                    ),
                    (
                        L(
                            "laws of UX, in the reference",
                            "lois d'UX, dans la référence",
                        ),
                        "30",
                    ),
                    (
                        L(
                            "rules with a mechanical fixer",
                            "règles avec un correcteur mécanique",
                        ),
                        "6",
                    ),
                ],
                at=list(
                    zip(
                        on_beat(29.3, 32.6, 35.9, 39.2),
                        on_beat(29.9, 33.2, 36.5, 39.8),
                    )
                ),
                caption=L(
                    "Each one names the file that would have to change "
                    "for it to stop being true.",
                    "Chacune nomme le fichier qui devrait changer pour "
                    "qu'elle cesse d'être vraie.",
                ),
            ),
            # ----------------------------------------------- SECRET SAUCE
            dict(
                type="held",
                beat="magic",
                start=49.9,
                dur=11.2,
                end=61.0,
                line=L(
                    "The dangerous number is the one nobody declared.",
                    "Le nombre dangereux est celui que personne n'a déclaré.",
                ),
            ),
            # The source, named, as every magic beat has done since
            # 2026-10-27. This one is not a paper: it is this repository's
            # own git history, where "127" outlived the catalogue by months.
            # `claims.py` lines 6 to 12 open on it, and it is the only source
            # a viewer can check by cloning the thing they are watching.
            dict(
                type="versus",
                beat="magic",
                start=60.9,
                dur=15.2,
                end=76.0,
                eyebrow=L(
                    "This repository's own history",
                    "L'historique de ce dépôt",
                ),
                left=(
                    L("Declared", "Déclaré"),
                    L(
                        "names the file that decides it",
                        "nomme le fichier qui le décide",
                    ),
                ),
                right=(
                    L("On screen only", "Seulement à l'écran"),
                    L(
                        "has nothing behind it at all",
                        "n'a rien du tout derrière lui",
                    ),
                ),
                at=on_beat(62.3, 66.8),
                caption=L(
                    "So the scan reads every number on screen. "
                    "It reports what no claim covers.",
                    "Le scan lit donc chaque nombre à l'écran. "
                    "Il relève ce qu'aucune affirmation ne couvre.",
                ),
            ),
            # ------------------------------------------------ AT ITS BEST
            # Direction two, and the finest thing this package can show: its
            # own verdict on the film you are watching. Reproduced, from a
            # clone, in under a second:
            #
            #   cd ~/sprezzature && sprezzature-video scan \
            #     brag-output/films/video-landscape/index.html \
            #     --spec brag-output/films.yaml
            #
            # On the entry as written here it answers with 127, twice: the
            # problem scene above, and row four of this card. Every other
            # number in the film is accounted for -- 167 and 20 and 6 by
            # value, 30 by the text of its claim.
            #
            # No picture was allocated to this film in `FILM-SHAPES.md` and
            # none is taken: the finest output of a checker is a verdict,
            # and a terminal screenshot would be a picture OF the verdict
            # rather than the verdict. The `verify` card is the film's own
            # typography, which is the same information and legible at 2160
            # pixels tall.
            dict(
                type="verify",
                beat="example",
                start=75.9,
                dur=17.2,
                end=93.0,
                eyebrow=L(
                    "scan, pointed at this film",
                    "scan, pointé sur ce film",
                ),
                claims=[
                    (L("167 chart kinds", "167 types de graphiques"),
                     L("declared", "déclaré")),
                    (L("20 accessibility rules", "20 règles d'accessibilité"),
                     L("declared", "déclaré")),
                    (L("30 laws of UX", "30 lois d'UX"),
                     L("declared", "déclaré")),
                    (L("127, with nothing behind it", "127, sans rien derrière"),
                     L("UNDECLARED", "NON DÉCLARÉ")),
                ],
                at=list(
                    zip(
                        on_beat(77.5, 80.5, 83.5, 87.0),
                        on_beat(78.1, 81.1, 84.1, 87.8),
                    )
                ),
                caption=L(
                    "This film quotes that number on purpose. "
                    "Quoting it is not declaring it.",
                    "Ce film cite ce nombre exprès. "
                    "Le citer n'est pas le déclarer.",
                ),
            ),
            dict(
                type="held",
                beat="example",
                start=92.9,
                dur=8.2,
                end=101.0,
                line=L(
                    "The only number it cannot declare is the one it is about.",
                    "Le seul nombre qu'il ne peut pas déclarer est celui "
                    "dont il parle.",
                ),
            ),
            # ------------------------------------------------- YOUR TURN
            dict(
                type="cta",
                beat="cta",
                start=100.9,
                dur=16.1,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature · video",
                actions=cta_for("video"),
                punchline=PUNCHLINE,
                punch_at=on_beat(107.3)[0],
            ),
        ],
    ),
    # ------------------------------------------------------------------- maps
    "maps": dict(
        duration=DURATION_S,
        # Six plates and a voice over them, which is the shape this film has had
        # since 2026-10-27 and the one worth keeping. What changed is which plate
        # the argument rests on.
        vo=[("maps.en", 1.10)],
        sfx=[
            ("drop", on_beat(6.9)[0]),
            ("tile", on_beat(26.4)[0]),
            ("tile", on_beat(46.4)[0]),
            ("wipe", on_beat(53.9)[0]),
            ("bell", on_beat(79.4)[0]),
        ],
        scenes=[
            # ---------------------------------------------------------- WHAT
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=7.5,
                end=7.0,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature · maps",
                line=L(
                    "Maps drawn on real ground, saying what they do not know.",
                    "Des cartes sur un vrai sol, qui disent ce qu'elles ignorent.",
                ),
                url="sprezzature.ai",
            ),
            # ------------------------------------------------------- PROBLEM
            # The failure is not that the file lacks the information. The file
            # has it, writes it down beside every row, and the tool throws it
            # away -- which is why the two problem scenes are in that order.
            dict(
                type="held",
                beat="problem",
                start=6.9,
                dur=10.2,
                end=17.0,
                line=L(
                    "Your file already says how sure each coordinate is.",
                    "Votre fichier dit déjà ce qu'il sait de chaque coordonnée.",
                ),
            ),
            dict(
                type="claim",
                beat="problem",
                start=16.9,
                dur=9.7,
                end=26.5,
                line=L(
                    "Every tool draws them all as the same dot.",
                    "Tous les outils les tracent du même point.",
                ),
            ),
            # ------------------------------------------------------ SOLUTION
            # Three generators, one scene each, in the order a reader meets
            # them: the ground, the world, and the plate with no ground at all.
            dict(
                type="grid",
                beat="solution",
                start=26.4,
                dur=9.7,
                end=36.0,
                eyebrow=L("Real ground, under everything", "Un vrai sol, sous tout le reste"),
                images=[
                    "maps/situation-himalaya.png",
                    "maps/situation-switzerland.png",
                    "maps/situation-iberia.png",
                ],
                at=on_beat(27.6, 28.7, 29.8),
                caption=L(
                    "Natural Earth, GMTED2010, HydroRIVERS. All of it bundled.",
                    "Natural Earth, GMTED2010, HydroRIVERS. Tout est embarqué.",
                ),
            ),
            dict(
                type="grid",
                beat="solution",
                start=35.9,
                dur=10.7,
                end=46.5,
                eyebrow=L("A world at the right size", "Un monde à la bonne taille"),
                images=["maps/choropleth-sequential.svg"],
                at=on_beat(37.0),
                caption=L(
                    "Equal Earth: equal area, closed form, no iteration.",
                    "Equal Earth : équivalente, en forme fermée, sans itération.",
                ),
            ),
            dict(
                type="grid",
                beat="solution",
                start=46.4,
                dur=7.7,
                end=54.0,
                eyebrow=L(
                    "The plate that draws no map",
                    "La planche qui ne dessine aucune carte",
                ),
                images=["maps/density.svg"],
                at=on_beat(47.5),
                caption=L(
                    "No coastline, no border, no graticule.",
                    "Ni côte, ni frontière, ni quadrillage.",
                ),
            ),
            # --------------------------------------------------- SECRET SAUCE
            # The mechanism, drawn rather than described. ACLED publishes
            # `geo_precision` 1 to 3 and UCDP `where_prec` 1 to 7, and the two
            # ends of that scale are two different marks here. Everything else in
            # this space -- GeoPandas, Cartopy, QGIS, Datawrapper -- draws a 3 the
            # way it draws a 1.
            dict(
                type="versus",
                beat="magic",
                start=53.9,
                dur=13.2,
                end=67.0,
                eyebrow=L(
                    "What the source wrote beside the coordinate",
                    "Ce que la source a écrit à côté de la coordonnée",
                ),
                left=(
                    L("geo_precision 1", "geo_precision 1"),
                    L(
                        "a named location, drawn as a filled disc",
                        "un lieu nommé, dessiné en disque plein",
                    ),
                ),
                right=(
                    L("geo_precision 3", "geo_precision 3"),
                    L(
                        "a province pinned to its capital, drawn as a broken ring",
                        "une province épinglée sur sa capitale, en anneau brisé",
                    ),
                ),
                at=on_beat(55.0, 58.3),
            ),
            # The source, which is what separates a mechanism from a boast. The
            # three labels are ACLED's own, copied out of its codebook into
            # `_GEO_PRECISION` in `scripts/make_situation_map.py`.
            dict(
                type="held",
                beat="magic",
                start=66.9,
                dur=12.7,
                end=79.5,
                line=L(
                    "Those are ACLED's words, not ours.",
                    "Ce sont les mots d'ACLED, pas les nôtres.",
                ),
            ),
            # ------------------------------------------------- AT ITS BEST
            # Twenty seconds on one plate, large, with the voice saying what to
            # notice rather than what is there. Every marker on it is a ring
            # because every one of the six rows said "approximate", and the key
            # prints that in words beside the colours it also explains.
            dict(
                type="shot",
                beat="example",
                start=79.4,
                dur=20.2,
                end=99.5,
                eyebrow=L("6 markers, 6 rings", "6 marqueurs, 6 anneaux"),
                src="maps/situation-ukraine.png",
                ratio=1.34,
                at=on_beat(81.0)[0],
                caption=L(
                    "Nothing here claims a position the source did not give.",
                    "Rien ici n'affirme une position que la source n'a pas donnée.",
                ),
            ),
            # ------------------------------------------------------------ CTA
            dict(
                type="cta",
                beat="cta",
                start=99.4,
                dur=17.6,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature · maps",
                actions=cta_for("maps"),
                punchline=PUNCHLINE,
                punch_at=on_beat(108.6)[0],
            ),
        ],
    ),
    # ----------------------------------------------------------------- ux-laws
    "ux-laws": dict(
        duration=DURATION_S,
        # One sustained argument, no chip grid. Written 2026-10-27 after
        # reading the auditor rather than its feature table, and re-cut to
        # seven movements on 2026-10-29.
        #
        # The secret sauce was in a docstring: Hick's Law measures the choices
        # a person meets at one moment, so counting the links in a file gets
        # it wrong twice. A responsive header holds two menus that never paint
        # together, and a group collapses several controls into one decision.
        # The README's table said "too many choices presented at once" and
        # stopped there; the sentence is in both READMEs now.
        #
        # The example beat is the argument's proof and not its illustration:
        # the two plates carry the auditor's own output on two pages that
        # differ in nothing but how many links their nav holds. The
        # forty-link nav is wrapped in `hidden sm:flex`, which is why the
        # finding says "on desktop" -- the same visibility resolution the
        # magic beat is about, deciding a real case three scenes later.
        vo=[("ux-laws.en", 1.10)],
        sfx=[
            ("drop", on_beat(9.9)[0]),
            ("tile", on_beat(45.6)[0]),
            ("tile", on_beat(68.7)[0]),
            ("tile", on_beat(78.0)[0]),
            ("tile", on_beat(83.5)[0]),
            ("bell", on_beat(100.5)[0]),
        ],
        scenes=[
            # WHAT: the suite's sentence, then this brick's, on frame one.
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=10.0,
                end=10.0,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature \u00b7 ux-laws",
                line=L(
                    "The laws of attention, checked against your own markup.",
                    "Les lois de l'attention, vérifiées sur votre balisage.",
                ),
                url="sprezzature.ai",
            ),
            # PROBLEM: what reaches you, and what it was.
            dict(
                type="versus",
                beat="problem",
                start=9.9,
                dur=9.6,
                end=19.5,
                eyebrow=L(
                    "What actually gets reported", "Ce qu'on vous remonte vraiment"
                ),
                left=(
                    L("What they say", "Ce qu'on vous dit"),
                    L(
                        "“I can never find the button”",
                        "« je ne trouve jamais le bouton »",
                    ),
                ),
                right=(
                    L("What it is", "Ce que c'est"),
                    L(
                        "too many choices at one moment",
                        "trop de choix au même instant",
                    ),
                ),
                at=on_beat(11.0, 13.4),
                caption=L(
                    "The law of HICK is the one thing nobody will mention.",
                    "La loi de HICK, elle, personne ne la citera.",
                ),
            ),
            dict(
                type="held",
                beat="problem",
                start=19.4,
                dur=8.8,
                end=28.2,
                line=L(
                    "The symptom reaches you. The cause was published in 1952.",
                    "Le symptôme vous parvient. La cause est publiée depuis 1952.",
                ),
            ),
            # SOLUTION: the set, then the share of it a text scan can settle.
            dict(
                type="claim",
                beat="solution",
                start=28.1,
                dur=8.6,
                end=36.7,
                line=L(
                    "30 laws, collected by Jon YABLONSKI.",
                    "30 lois, réunies par Jon YABLONSKI.",
                ),
            ),
            dict(
                type="held",
                beat="solution",
                start=36.6,
                dur=9.0,
                end=45.6,
                line=L(
                    "8 of them settle from the source alone.",
                    "8 d'entre elles se tranchent depuis la source.",
                ),
            ),
            # SECRET SAUCE, shown as the markup it reads.
            dict(
                type="code",
                beat="magic",
                start=45.5,
                dur=13.6,
                end=59.1,
                eyebrow=L("The same header, 2 menus", "Le même en-tête, 2 menus"),
                code=[
                    '<nav class="flex items-center justify-between">',
                    '  <div class="hidden sm:flex gap-4">',
                    '    <a href="/skills">Skills</a>',
                    '    <a href="/gallery">Gallery</a>',
                    '    <a href="/packages">Packages</a>',
                    "  </div>",
                    '  <button class="sm:hidden">Menu</button>',
                    "</nav>",
                ],
                mark=(2, 7),
                at=on_beat(46.2, 46.7, 47.3, 47.8, 48.4, 48.9, 49.5, 50.0),
                flag=[(2, on_beat(52.5)[0]), (7, on_beat(54.2)[0])],
                caption=L(
                    "One of these paints on a phone. The other paints "
                    "on a desktop. A reader meets one of them.",
                    "L'un s'affiche sur téléphone. L'autre sur "
                    "ordinateur. Un lecteur n'en rencontre qu'un.",
                ),
            ),
            dict(
                type="held",
                beat="magic",
                start=59.0,
                dur=8.6,
                end=67.6,
                line=L(
                    "Adding them up charges the reader for choices no "
                    "screen ever shows.",
                    "Les additionner reproche au lecteur des choix "
                    "qu'aucun écran ne lui montre.",
                ),
            ),
            dict(
                type="versus",
                beat="magic",
                start=67.5,
                dur=9.3,
                end=76.8,
                eyebrow=L("So it counts them apart", "Il les compte donc à part"),
                left=(
                    L("Per breakpoint", "Par point de rupture"),
                    L(
                        "the phone count, then the desktop count",
                        "le compte du téléphone, puis celui du bureau",
                    ),
                ),
                right=(
                    L("Per decision", "Par décision"),
                    L(
                        "a block that collapses counts as one",
                        "un bloc qui se replie compte pour un",
                    ),
                ),
                at=on_beat(68.7, 70.9),
                caption=L(
                    "It reports the worse of the two, naming which one it is.",
                    "Il retient le pire des deux, en disant lequel.",
                ),
            ),
            # AT ITS BEST: the law deciding a real case, and the gate closing.
            # Two pages identical but for the size of one <nav>, each with the
            # text the auditor actually printed on it.
            dict(
                type="grid",
                beat="example",
                start=76.7,
                dur=15.2,
                end=91.9,
                eyebrow=L("The same check, twice", "Le même contrôle, deux fois"),
                images=["ux-laws/nav-forty.svg", "ux-laws/nav-seven.svg"],
                at=on_beat(78.0, 83.5),
                caption=L(
                    "40 exits 1. 7 exits 0. That is the whole gate.",
                    "40 renvoie 1. 7 renvoie 0. Tout le verrou "
                    "est là.",
                ),
            ),
            # And where it stops. `README.md:118`, word for word, with the
            # French of `LISEZMOI.md:129` beside it.
            dict(
                type="held",
                beat="example",
                start=91.8,
                dur=8.8,
                end=100.6,
                line=L(
                    "It is a fast gate, not a substitute for design review.",
                    "C'est un verrou rapide, pas un substitut à une revue "
                    "de design.",
                ),
            ),
            dict(
                type="cta",
                beat="cta",
                start=100.5,
                dur=16.5,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature \u00b7 ux-laws",
                actions=cta_for("ux-laws"),
                punchline=PUNCHLINE,
            ),
        ],
    ),
    # ----------------------------------------------------------- accessibility
    "accessibility": dict(
        duration=DURATION_S,
        # Written 2026-10-27 from `lint_a11y.py`, rewritten 2026-10-29. Its
        # autoplay rule carries the sharpest problem statement in the suite:
        # unmuted sound that starts by itself masks a screen reader, so the user
        # cannot hear the tool they are navigating with, and on many pages
        # cannot find the control to stop it either. The trap closes on itself.
        #
        # The secret sauce is the restraint. Six of twenty rules repair
        # themselves, and only six, because a fix is automatic solely where
        # exactly one repair is safe. The other fourteen are reported and never
        # guessed at -- `lint_a11y.py:977` says they "need a content decision the
        # linter cannot make for the user", and `_is_focusable`'s docstring
        # records the day that mattered: `aria-hidden-interactive` flagged
        # seventeen correct pairs on one blog index, and an automatic repair
        # would have made a screen reader announce every article twice.
        #
        # `--fix-alt` is the exception that proves it, and the reason it is
        # allowed to call a model is that it has two inputs rather than one.
        vo=[("accessibility.en", 1.10)],
        sfx=[
            ("drop", on_beat(9.4)[0]),
            ("tile", on_beat(30.9)[0]),
            ("tile", on_beat(44.9)[0]),
            ("tile", on_beat(53.9)[0]),
            ("bell", on_beat(75.9)[0]),
        ],
        scenes=[
            # ------------------------------------------------------------ WHAT
            dict(
                type="what",
                beat="what",
                start=0.0,
                dur=10.0,
                end=9.5,
                logo="logo-512.png",
                tagline=TAGLINE,
                mark="Sprezzature · accessibility",
                line=L(
                    "20 accessibility rules, decided by reading the HTML.",
                    "20 règles d'accessibilité, tranchées en lisant le HTML.",
                ),
                url="sprezzature.ai",
            ),
            # --------------------------------------------------------- PROBLEM
            # The trap, stated as a fact about a reader. Not "unmuted autoplay
            # is a WCAG 1.4.2 failure", which is a sentence for somebody who
            # already agrees.
            dict(
                type="held",
                beat="problem",
                start=9.4,
                dur=10.3,
                end=19.6,
                line=L(
                    "A blind reader cannot now hear the tool they would "
                    "use to stop it.",
                    "Un lecteur aveugle n'entend plus l'outil avec lequel "
                    "il l'arrêterait.",
                ),
            ),
            # And the second half of the problem, which is why a linter is
            # needed at all: the markup is well formed. Validity and
            # accessibility are different questions and only one of them has a
            # validator everybody already runs.
            dict(
                type="claim",
                beat="problem",
                start=19.5,
                dur=11.6,
                end=31.0,
                line=L(
                    "No validator says a word about that page.",
                    "Aucun validateur n'a rien à redire à cette page.",
                ),
            ),
            # -------------------------------------------------------- SOLUTION
            # The film's own shape, finally used: the source, with the lines
            # that break a rule marked. Eight lines, six findings, and the
            # gutter numbers are the ones `lint_a11y.py` prints.
            #
            # Flagged in the order a reader meets the damage rather than in file
            # order: line 5 is three findings on its own (autoplay with sound,
            # no controls, no caption track), then the image, then the div, and
            # the missing `lang` on line 2 last because it is the cheapest.
            dict(
                type="code",
                beat="solution",
                start=30.9,
                dur=14.2,
                end=45.0,
                eyebrow=L(
                    "The page, and the lines that break a rule",
                    "La page, et les lignes qui enfreignent une règle",
                ),
                code=[
                    "<!doctype html>",
                    "<html>",
                    "<body>",
                    "  <h1>Spring sale</h1>",
                    '  <video src="promo.mp4" autoplay></video>',
                    '  <img src="shoe.jpg">',
                    '  <div onclick="buy()">Buy now</div>',
                    "</body>",
                ],
                mark=(2, 5, 6, 7),
                at=on_beat(31.8, 32.3, 32.9, 33.4, 34.0, 34.5, 35.1, 35.6),
                flag=list(zip((5, 6, 7, 2), on_beat(37.6, 39.2, 40.7, 42.3))),
                caption=L(
                    "Every finding names the element, the line, and the "
                    "rule it broke.",
                    "Chaque constat nomme l'élément, la ligne et la règle "
                    "enfreinte.",
                ),
            ),
            # Kept from the 2026-10-27 cut, which got this scene right: eight of
            # the twenty by name, falling one at a time. A rule id is the thing
            # a viewer can go and look up, and `references/lint-rules.md` carries
            # the WCAG or WAI-ARIA reference for each.
            dict(
                type="chips",
                beat="solution",
                start=44.9,
                dur=9.2,
                end=54.0,
                eyebrow=L(
                    "20 rules out of WCAG and WAI-ARIA",
                    "20 règles tirées de WCAG et WAI-ARIA",
                ),
                items=[
                    "media-autoplay-sound",
                    "video-missing-captions",
                    "img-missing-alt",
                    "input-missing-label",
                    "div-onclick",
                    "tabindex-positive",
                    "heading-skip",
                    "color-only-state",
                ],
                at=on_beat(45.8, 46.3, 46.9, 47.4, 48.0, 48.5, 49.1, 49.6),
                caption=L(
                    "Standard library for the lint. One dependency, for "
                    "the command line.",
                    "Bibliothèque standard pour le linter. Une dépendance, "
                    "pour la ligne de commande.",
                ),
            ),
            # ---------------------------------------------------- SECRET SAUCE
            # The restraint, counted. Twenty checked, six repaired, fourteen
            # left alone, and a second pass that changes nothing.
            dict(
                type="verify",
                beat="magic",
                start=53.9,
                dur=12.7,
                end=66.5,
                eyebrow=L(
                    "What it will repair by itself", "Ce qu'il répare de lui-même"
                ),
                claims=[
                    (L("rules it checks", "règles vérifiées"), "20"),
                    (L("rules it will fix", "règles qu'il corrige"), "6"),
                    (
                        L(
                            "rules it reports and leaves alone",
                            "règles qu'il signale et laisse",
                        ),
                        "14",
                    ),
                    (
                        L(
                            "edits a second run applies",
                            "retouches à la seconde exécution",
                        ),
                        "0",
                    ),
                ],
                at=list(
                    zip(
                        on_beat(55.0, 56.6, 58.2, 59.9),
                        on_beat(55.5, 57.1, 58.7, 60.4),
                    )
                ),
                caption=L(
                    "A repair is automatic only where exactly one repair is safe.",
                    "Une réparation n'est automatique que là où il "
                    "n'en existe qu'une de sûre.",
                ),
            ),
            # The exception, and its mechanism: two inputs rather than one. The
            # source is named in the voice -- the W3C alt decision tree sorts
            # images by what they are *doing* on the page, which is a question
            # about the page and not about the pixels, and `scripts/prompts/`
            # holds one prompt per function. `_vocab.py:115` is where 400 lives.
            dict(
                type="versus",
                beat="magic",
                start=66.4,
                dur=9.7,
                end=76.0,
                eyebrow=L(
                    "The one exception, and it has 2 inputs",
                    "La seule exception, et elle a 2 entrées",
                ),
                left=(
                    L("The image", "L'image"),
                    L("pixels, and nothing else", "des pixels, et rien d'autre"),
                ),
                right=(
                    L("The page it sits in", "La page autour"),
                    L(
                        "400 characters either side",
                        "400 caractères de chaque côté",
                    ),
                ),
                at=on_beat(67.5, 70.8),
                caption=L(
                    "The W3C tree asks what an image is doing, not what it shows.",
                    "L'arbre du W3C demande ce qu'une image fait, pas ce "
                    "qu'elle montre.",
                ),
            ),
            # ------------------------------------------------------ AT ITS BEST
            # Thirteen seconds on the photograph, large, with the caption
            # carrying the control: this same package, shown the pixels and
            # nothing else, drafted a dark coat and a patterned shirt. The voice
            # does not describe the picture; it says what to notice when the
            # next scene arrives.
            dict(
                type="shot",
                beat="example",
                start=75.9,
                dur=13.2,
                end=89.0,
                eyebrow=L(
                    "An image with no alt attribute",
                    "Une image sans texte alternatif",
                ),
                src="shots/alt-marie-curie.jpg",
                ratio=0.736,
                at=on_beat(77.2)[0],
                caption=L(
                    "Shown the pixels alone, the draft was: a dark coat "
                    "over a patterned shirt.",
                    "Sur les seuls pixels, le brouillon disait : un manteau "
                    "sombre sur une chemise à motifs.",
                ),
            ),
            # And the file afterwards. The same `code` card as the solution
            # beat, so the film ends its argument where it started it: on a line
            # of source. Lines 6 to 9 are the attribute the package wrote,
            # verbatim, and nothing on them is in the photograph.
            dict(
                type="code",
                beat="example",
                start=88.9,
                dur=11.7,
                end=100.5,
                eyebrow=L(
                    "What it wrote into the file",
                    "Ce qu'il a écrit dans le fichier",
                ),
                code=[
                    L(
                        "<h2>The Paris years</h2>",
                        "<h2>Les années parisiennes</h2>",
                    ),
                    L(
                        "<p>The Radium Institute she directed",
                        "<p>L'Institut du radium qu'elle dirige",
                    ),
                    L(
                        "   had opened on the rue Pierre-Curie.</p>",
                        "   a ouvert rue Pierre-Curie.</p>",
                    ),
                    L("", ""),
                    L('<img src="marie-curie.jpg"', '<img src="marie-curie.jpg"'),
                    L(
                        '  alt="Studio portrait of Marie',
                        '  alt="Portrait de Marie Curie en',
                    ),
                    L(
                        "       Skłodowska-Curie, Paris, 1920s.",
                        "       studio des années 1920,",
                    ),
                    L(
                        "       Director of Radium Institute,",
                        "       dirigeant l'Institut du radium",
                    ),
                    L('       Nobel Prize winner.">', '       à Paris.">'),
                ],
                mark=(6, 7, 8, 9),
                at=on_beat(89.8, 90.3, 90.9, 91.4, 92.0, 92.5, 93.1, 93.6, 94.2),
                flag=list(zip((6, 7, 8, 9), on_beat(95.3, 95.8, 96.4, 96.9))),
                caption=L(
                    "Paris, the Institute and the decade are in the page, "
                    "not in the photograph.",
                    "Paris, l'Institut et la décennie sont dans la page, "
                    "pas dans la photographie.",
                ),
            ),
            # ------------------------------------------------------------- CTA
            dict(
                type="cta",
                beat="cta",
                start=100.4,
                dur=16.6,
                end=DURATION_S,
                logo="logo-512.png",
                mark="Sprezzature · accessibility",
                actions=cta_for("accessibility"),
                punchline=PUNCHLINE,
                punch_at=on_beat(108.6)[0],
            ),
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
    html, body {{ width: {f["w"]}px; height: {f["h"]}px; overflow: hidden;
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
    .bg-wash {{ position: absolute; top: {-int(f["h"] * 0.38)}px; left: 50%;
      width: {int(f["w"] * 1.25)}px; height: {int(f["h"] * 1.4)}px;
      margin-left: {-int(f["w"] * 0.625)}px;
      background: radial-gradient(closest-side, rgba(127,209,255,.55) 0%,
        rgba(127,209,255,.22) 45%, rgba(127,209,255,0) 78%); }}

    .inner {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    .stage {{ position: absolute; inset: 0; display: flex; align-items: center;
              justify-content: center; padding: {pad}px; }}
    .col {{ display: flex; flex-direction: column; align-items: center;
            justify-content: center; width: 100%; }}

    .eyebrow {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f["eyebrow"]}px; font-weight: 500; letter-spacing: .2em;
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
    .caption {{ font-size: {f["body"]}px; font-weight: 400; line-height: 1.34;
      color: var(--ink-soft); text-align: center; text-wrap: balance;
      max-width: {f["w"] - 2 * pad}px; }}

    /* Scene 1: the claim */
    .claim {{ font-family: "Roboto Serif"; font-size: {f["hero"]}px; font-weight: 600;
      letter-spacing: -.02em; line-height: 1.08; text-align: center;
      max-width: {f["w"] - 2 * pad}px; color: var(--ink); }}

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

    .loop-wrap {{ display: flex; {
        "flex-direction: row; align-items: center; gap: 88px;"
        if split
        else "flex-direction: column; align-items: center; gap: 46px;"
    }
      justify-content: center; width: 100%; }}
    .loop-text {{ display: flex; flex-direction: column;
      align-items: {"flex-start" if split else "center"};
      text-align: {"left" if split else "center"};
      {
        "width: " + str(f["w"] - 2 * pad - fig - 132) + "px;"
        if split
        else "width: " + str(f["w"] - 2 * pad) + "px;"
    } }}
    .loop-text .eyebrow, .loop-text .caption {{ text-align: {
        "left" if split else "center"
    }; }}
    .steps {{ display: inline-flex; flex-direction: column; align-items: flex-start; }}
    .step {{ display: flex; align-items: baseline; gap: 18px;
      font-family: "Roboto Mono", ui-monospace, monospace; font-size: {f["mono"]}px;
      font-weight: 500; line-height: 1.55; color: var(--ink); }}
    .step-n {{ color: var(--blue); font-weight: 600; }}
    .step-dim {{ opacity: .32; }}

    .grid {{ display: grid; gap: 22px; justify-content: center; }}
    .tile {{ overflow: hidden; border: 2px solid var(--line); border-radius: 16px;
      background: var(--paper); padding: 9px; }}
    .tile img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}

    .chips {{ display: flex; flex-wrap: wrap; gap: 16px; justify-content: center;
      max-width: {f["w"] - 2 * pad}px; }}
    .chip {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f["chip"]}px; font-weight: 500; color: var(--ink);
      border: 2px solid var(--line); border-radius: 999px;
      padding: {int(f["chip"] * 0.42)}px {int(f["chip"] * 0.9)}px;
      background: var(--paper); white-space: nowrap; }}

    .panel {{ width: {min(f["w"] - 2 * pad, 1280)}px; }}
    .prow {{ display: flex; align-items: baseline;
      {
        "flex-direction: row; gap: 28px;"
        if split
        else "flex-direction: column; gap: 6px;"
    }
      padding: {int(f["body"] * 0.62)}px 0; border-bottom: 2px solid var(--line); }}
    .prow:last-child {{ border-bottom: 0; }}
    .pk {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f["mono"]}px; font-weight: 600; color: var(--blue);
      {"min-width: 380px;" if split else ""} white-space: nowrap; }}
    .pv {{ font-size: {f["h2"]}px; font-weight: 400; color: var(--ink);
      line-height: 1.3; }}

    /* held: one sentence, larger than a claim, for the films that have
       fewer things to say and more time to say them. */
    .held {{ font-family: "Roboto Serif"; font-size: {int(f["hero"] * 0.72)}px;
      font-weight: 600; line-height: 1.22; letter-spacing: -.015em;
      color: var(--ink); text-align: center; text-wrap: balance;
      max-width: {int((f["w"] - 2 * pad) * 0.86)}px; margin: 0 auto; }}

    /* flow: a document moving through stages and arriving as something. */
    .flow {{ display: flex; align-items: stretch; justify-content: center;
      flex-wrap: wrap; gap: {int(f["chip"] * 0.36)}px; }}
    .flow-step {{ display: flex; flex-direction: column; gap: 4px;
      border: 2px solid var(--line); border-radius: 14px;
      background: var(--paper); padding: {int(f["chip"] * 0.5)}px
      {int(f["chip"] * 0.66)}px; }}
    .flow-name {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f["chip"] * 0.92)}px; font-weight: 600; color: var(--blue); }}
    .flow-under {{ font-size: {int(f["chip"] * 0.72)}px; color: var(--ink-soft); }}
    .flow-arrow {{ align-self: center; font-size: {int(f["chip"] * 1.3)}px;
      color: var(--line); line-height: 1; }}

    /* versus: two halves of one idea, with the divider between them. */
    .versus {{ display: flex; align-items: stretch; gap: {int(f["body"] * 0.9)}px;
      width: {min(f["w"] - 2 * pad, 1280)}px; }}
    .vs-half {{ flex: 1; display: flex; flex-direction: column; gap: 10px;
      border: 2px solid var(--line); border-radius: 18px;
      background: var(--paper); padding: {int(f["body"] * 0.8)}px; }}
    .vs-key {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f["mono"]}px; font-weight: 600; color: var(--blue); }}
    .vs-val {{ font-size: {int(f["h2"] * 0.86)}px; line-height: 1.3;
      color: var(--ink); text-wrap: balance; }}
    .vs-bar {{ width: 3px; background: var(--line); border-radius: 2px;
      transform-origin: center; }}

    /* code: the source a finding is about, with the line marked. */
    .codecard {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f["mono"] * 0.92)}px; line-height: 1.75;
      width: {min(f["w"] - 2 * pad, 1280)}px; text-align: left; }}
    .code-line {{ display: flex; gap: {int(f["mono"] * 0.9)}px;
      border-radius: 6px; padding: 1px {int(f["mono"] * 0.4)}px; }}
    /* The gutter number is text, and the contrast checker treats it as
       text: drawn in the hairline colour it came to 1.26:1 against paper,
       where 3:1 is the floor. A line number nobody can read is also a line
       number nobody can quote back at you. */
    .code-n {{ color: #8a8a8a; min-width: {int(f["mono"] * 1.5)}px;
      text-align: right; }}
    .code-t {{ color: var(--ink); white-space: pre; }}
    .code-line.bad .code-t {{ color: var(--ink); font-weight: 600; }}
    /* The gutter number is drawn in the rule colour, which disappears
       against the flag. A flagged line is the one a viewer wants to
       name, so its number is the one that has to stay readable. */
    .code-line.bad .code-n {{ color: var(--ink-soft); font-weight: 600; }}

    /* verify: a claim, and the value it was checked against. */
    .verify {{ width: {min(f["w"] - 2 * pad, 1280)}px; }}
    .vrow {{ display: flex; align-items: baseline; gap: 14px;
      padding: {int(f["body"] * 0.5)}px 0; border-bottom: 2px solid var(--line); }}
    .vrow:last-child {{ border-bottom: 0; }}
    .vclaim {{ font-size: {int(f["h2"] * 0.82)}px; color: var(--ink);
      white-space: nowrap; }}
    .vdots {{ flex: 1; border-bottom: 2px dotted var(--line);
      transform: translateY(-.25em); }}
    .vvalue {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f["mono"]}px; font-weight: 600; color: var(--blue);
      white-space: nowrap; }}

    .shotcard img {{ display: block; border-radius: 8px; }}
    .viewport {{ position: relative; overflow: hidden; border-radius: 8px; }}

    /* The identity card that opens every film, and is finished at frame
       zero: the package's name, one line saying what it is, and where to
       find it. The films used to open on their problem sentence alone --
       a good sentence, which tells a viewer who has just landed nothing
       about whose problem it is or what they are watching. */
    #what-tag {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f["eyebrow"] * 0.95)}px; font-weight: 500;
      letter-spacing: .16em; text-transform: uppercase; color: var(--navy);
      text-align: center; margin-bottom: {int(f["hero"] * 0.3)}px; }}
    #what-logo {{ display: block; width: {int(f["hero"] * 2.0)}px;
      height: {int(f["hero"] * 2.0)}px; object-fit: contain; }}
    #what-mark {{ font-family: "Roboto Serif"; font-size: {int(f["hero"] * 0.9)}px;
      font-weight: 600; letter-spacing: -.02em; color: var(--ink);
      text-align: center; }}
    #what-line {{ font-size: {int(f["h2"] * 1.05)}px; color: var(--ink-soft);
      text-align: center; text-wrap: balance;
      max-width: {int(f["w"] * (0.74 if f["w"] > f["h"] else 0.92))}px;
      margin-top: {int(f["hero"] * 0.3)}px; }}
    #what-url {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f["eyebrow"] * 1.02)}px; font-weight: 500;
      letter-spacing: .06em; color: var(--blue);
      margin-top: {int(f["hero"] * 0.34)}px; }}

    /* The call to action. Two things to do, each one a verb and the place
       it happens, because "sprezzature.ai" alone is an address and not an
       instruction. The glyph is a column of its own so the two verbs start
       on the same vertical line whatever the canvas. */
    .cta {{ display: flex; align-items: baseline; gap: {int(f["body"] * 0.5)}px;
      margin-top: {int(f["hero"] * 0.26)}px; }}
    .cta-glyph {{ font-size: {int(f["h2"] * 0.9)}px; color: var(--blue);
      line-height: 1; width: {int(f["h2"] * 1.1)}px; text-align: center; }}
    .cta-text {{ display: flex; flex-direction: column; }}
    .cta-do {{ font-size: {f["h2"]}px; font-weight: 600; color: var(--ink);
      letter-spacing: -.01em; }}
    .cta-at {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f["eyebrow"] * 0.92)}px; font-weight: 500;
      letter-spacing: .04em; color: var(--blue);
      margin-top: {int(f["body"] * 0.22)}px; }}

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
    #beats {{ position: absolute; top: {
        int(pad * (0.5 if f["w"] > f["h"] else 1.75))
    }px;
      left: 50%;
      transform: translateX(-50%); display: flex; align-items: center;
      gap: {int(f["eyebrow"] * 0.52)}px; white-space: nowrap;
      font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f["eyebrow"] * 0.68)}px; font-weight: 500;
      letter-spacing: .16em; text-transform: uppercase; }}
    /* Grey enough to stay out of the way of the sentence, dark enough to be
       read on purpose. The first version used `--line`, the hairline colour,
       which on this paper is all but invisible: the label was there and
       nobody could have told. */
    #beats span {{ color: #a3a3a3; }}
    #beats i {{ font-style: normal; color: #d4d4d4;
      font-size: {int(f["eyebrow"] * 0.6)}px; }}

    #logo {{ display: block; width: {int(f["hero"] * 2.0)}px;
      height: {int(f["hero"] * 2.0)}px; object-fit: contain; }}
    #mark {{ font-family: "Roboto Serif"; font-size: {int(f["hero"] * 0.84)}px;
      font-weight: 600; letter-spacing: -.02em; color: var(--ink);
      margin-top: {int(f["hero"] * 0.3)}px; text-align: center; }}
    #punch {{ font-family: "Roboto Serif"; font-size: {int(f["h2"] * 1.12)}px;
      font-weight: 600; color: var(--ink); text-align: center;
      margin-top: {int(f["hero"] * 0.42)}px; max-width: {int(f["w"] * 0.78)}px;
      line-height: 1.25; }}
    #oline {{ font-size: {f["h2"]}px; color: var(--ink-soft);
      margin-top: {int(f["hero"] * 0.22)}px; text-align: center; }}
    #ourl {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f["eyebrow"] * 0.96)}px; font-weight: 500; letter-spacing: .06em;
      color: var(--blue); margin-top: {int(f["hero"] * 0.3)}px; }}

    #rail-l, #rail-r {{ position: absolute; top: {int(pad * 0.48)}px;
      font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {
        int(f["eyebrow"] * 0.9)
    }px; font-weight: 500; letter-spacing: .22em; }}
    #rail-l {{ left: {pad}px; color: var(--blue); }}
    #rail-r {{ right: {pad}px; letter-spacing: .1em; color: var(--ink-soft); }}
    #rail-line {{ position: absolute; left: {pad}px; top: {f["h"] - int(pad * 0.52)}px;
      width: {f["w"] - 2 * pad}px; height: 2px; background: var(--line);
      transform-origin: left center; }}
    """


def scene_html(sc: dict, f: dict, i: int) -> str:
    """Body markup for one scene. Timing lives on the wrapper, not here."""
    t = sc["type"]
    head = (
        (
            f'<p class="eyebrow" id="s{i}-eyebrow">{esc(sc["eyebrow"])}</p>'
            f'<div class="rule" id="s{i}-rule" style="width:132px;margin:18px 0 '
            f'{int(f["body"] * 1.0)}px"></div>'
        )
        if sc.get("eyebrow")
        else ""
    )
    cap = (
        (
            f'<p class="caption" id="s{i}-caption" '
            f'style="margin-top:{int(f["body"] * 1.05)}px">{esc(sc["caption"])}</p>'
        )
        if sc.get("caption") and t not in ("loop", "cvd")
        else ""
    )

    if t == "held":
        # One sentence, bigger than a claim, on screen long enough to read
        # twice. The `ui` film is four of these and nothing else: the
        # smallest package gets the fewest words, held longest.
        return (
            f'<div class="stage"><div class="col">'
            f'<h1 class="held" id="s{i}-line">{esc(sc["line"])}</h1>'
            f'<div class="rule" id="s{i}-rule" style="width:96px;'
            f'margin:{int(f["body"] * 1.4)}px auto 0"></div>'
            f"</div></div>"
        )

    if t == "flow":
        # Stages left to right, with an arrow between. A document moving
        # through nine tools and arriving as a site is a sequence, so the
        # scene is a sequence.
        parts = []
        for k, (name, under) in enumerate(sc["stages"], 1):
            arrow = (
                f'<span class="flow-arrow" id="s{i}-a{k}">&rsaquo;</span>'
                if k > 1
                else ""
            )
            parts.append(
                f'{arrow}<div class="flow-step" id="s{i}-f{k}">'
                f'<span class="flow-name">{esc(name)}</span>'
                f'<span class="flow-under">{esc(under)}</span></div>'
            )
        return (
            f'<div class="stage"><div class="col">{head}'
            f'<div class="flow">{"".join(parts)}</div>{cap}</div></div>'
        )

    if t == "versus":
        # Two halves and a divider. Used where the subject is a pair:
        # a command and the form it became, sound read in two directions.
        left, right = sc["left"], sc["right"]
        return (
            f'<div class="stage"><div class="col">{head}'
            f'<div class="versus">'
            f'<div class="vs-half" id="s{i}-vl">'
            f'<p class="vs-key">{esc(left[0])}</p>'
            f'<p class="vs-val">{esc(left[1])}</p></div>'
            f'<div class="vs-bar" id="s{i}-vbar"></div>'
            f'<div class="vs-half" id="s{i}-vr">'
            f'<p class="vs-key">{esc(right[0])}</p>'
            f'<p class="vs-val">{esc(right[1])}</p></div>'
            f"</div>{cap}</div></div>"
        )

    if t == "code":
        # Markup on screen with the offending lines marked. An accessibility
        # finding is a statement about a line of source, so the film shows
        # the line of source.
        rows = "".join(
            f'<div class="code-line{" bad" if n in sc.get("mark", ()) else ""}" '
            f'id="s{i}-c{n}"><span class="code-n">{n}</span>'
            f'<span class="code-t">{esc(line)}</span></div>'
            for n, line in enumerate(sc["code"], 1)
        )
        return (
            f'<div class="stage"><div class="col">{head}'
            f'<div class="card codecard" id="s{i}-code">{rows}</div>'
            f"{cap}</div></div>"
        )

    if t == "verify":
        # A claim and what it was checked against, the value arriving after
        # the claim. The `video` film audits itself while it plays.
        rows = "".join(
            f'<div class="vrow" id="s{i}-v{k}">'
            f'<span class="vclaim">{esc(claim)}</span>'
            f'<span class="vdots"></span>'
            f'<span class="vvalue" id="s{i}-vv{k}">{esc(value)}</span></div>'
            for k, (claim, value) in enumerate(sc["claims"], 1)
        )
        return (
            f'<div class="stage"><div class="col">{head}'
            f'<div class="card verify" id="s{i}-verify">{rows}</div>'
            f"{cap}</div></div>"
        )

    if t == "claim":
        return (
            f'<div class="stage"><div class="col">'
            f'<h1 class="claim" id="s{i}-line">{esc(sc["line"])}</h1>'
            f'<div class="rule" id="s{i}-rule" '
            f'style="width:220px;margin-top:{int(f["hero"] * 0.42)}px"></div>'
            f"</div></div>"
        )

    if t == "loop":
        h = int(f["fig"] / sc["ratio"])
        steps = (
            '<div class="steps">'
            + "".join(
                f'<div class="step" id="s{i}-step{n}"><span class="step-n">{esc(k)}</span>'
                f"<span>{esc(v)}</span></div>"
                for n, (k, v) in enumerate(sc["steps"], 1)
            )
            + "</div>"
        )
        return (
            f'<div class="stage"><div class="loop-wrap">'
            f'<div class="card" id="s{i}-card"><div class="figbox" '
            f'style="height:{h}px">'
            f'<img src="assets/{sc["fig"]}" alt="">'
            f'<div class="gray-wrap" id="s{i}-gray">'
            f'<img class="fig-gray" src="assets/{sc["gray"]}" alt=""></div>'
            f'<div class="wipe-edge" id="s{i}-wipe"></div>'
            f"</div></div>"
            f'<div class="loop-text">{head}{steps}'
            f'<p class="caption" id="s{i}-caption" '
            f'style="margin-top:{int(f["body"] * 1.2)}px">{esc(sc["caption"])}</p>'
            f"</div></div></div>"
        )

    if t == "cvd":
        h = int(f["fig"] / sc["ratio"])
        # Every simulation sits on the one below it, so each wipe hands the
        # frame to the next pair of eyes without a cut.
        layers = "".join(
            f'<div class="gray-wrap" id="s{i}-w{k}">'
            f'<img src="assets/{src}" alt=""></div>'
            for k, (_, _, src, _) in enumerate(sc["stages"], 1)
        )
        steps = (
            '<div class="steps">'
            + "".join(
                f'<div class="step step-dim" id="s{i}-step{k}">'
                f'<span class="step-n">{esc(num)}</span><span>{esc(lbl)}</span></div>'
                for k, (num, lbl, _, _) in enumerate(sc["stages"], 1)
            )
            + "</div>"
        )
        return (
            f'<div class="stage"><div class="loop-wrap">'
            f'<div class="card" id="s{i}-card"><div class="figbox" '
            f'style="height:{h}px">'
            f'<img src="assets/{sc["base"]}" alt="">'
            f"{layers}"
            f'<div class="wipe-edge" id="s{i}-wipe"></div>'
            f"</div></div>"
            f'<div class="loop-text">{head}{steps}'
            f'<p class="caption" id="s{i}-caption" '
            f'style="margin-top:{int(f["body"] * 1.2)}px">{esc(sc["caption"])}</p>'
            f"</div></div></div>"
        )

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
            for k, src in enumerate(sc["images"], 1)
        )
        return (
            f'<div class="stage"><div class="col">{head}'
            f'<div class="grid" style="grid-template-columns:repeat({cols},{tw}px)">'
            f"{tiles}</div>{cap}</div></div>"
        )

    if t == "chips":
        chips = "".join(
            f'<span class="chip" id="s{i}-c{k}">{esc(v)}</span>'
            for k, v in enumerate(sc["items"], 1)
        )
        return (
            f'<div class="stage"><div class="col">{head}'
            f'<div class="chips">{chips}</div>{cap}</div></div>'
        )

    if t == "panel":
        rows = "".join(
            f'<div class="prow" id="s{i}-r{k}"><span class="pk">{esc(a)}</span>'
            f'<span class="pv">{esc(b)}</span></div>'
            for k, (a, b) in enumerate(sc["rows"], 1)
        )
        return (
            f'<div class="stage"><div class="col">{head}'
            f'<div class="card panel" id="s{i}-panel">{rows}</div>{cap}</div></div>'
        )

    if t == "shot":
        reserve = int(f["eyebrow"] * 1.3 + f["body"] * 4.5 + 24)
        max_h = f["h"] - 2 * f["pad"] - reserve - 44
        iw = f["shot"]
        ih = int(iw / sc["ratio"])
        if sc.get("scroll"):
            view = min(max_h, int(iw * f["view"]))
            return (
                f'<div class="stage"><div class="col">{head}'
                f'<div class="card shotcard" id="s{i}-shot">'
                f'<div class="viewport" style="width:{iw}px;height:{view}px">'
                f'<img id="s{i}-page" src="assets/{sc["src"]}" alt="" '
                f'style="width:{iw}px;height:{ih}px"></div></div>'
                f"{cap}</div></div>"
            )
        if ih > max_h:
            ih = max_h
            iw = int(ih * sc["ratio"])
        return (
            f'<div class="stage"><div class="col">{head}'
            f'<div class="card shotcard" id="s{i}-shot">'
            f'<img src="assets/{sc["src"]}" alt="" '
            f'style="width:{iw}px;height:{ih}px;object-fit:contain"></div>'
            f"{cap}</div></div>"
        )

    if t == "what":
        # Frame zero of a film is the frame most often seen on its own: the
        # poster a player falls back to, the still a scrubber lands on, the
        # thumbnail a platform grabs when nobody gave it one. So it carries
        # the name, the sentence and the address, and it carries them whole
        # -- nothing in this scene fades in.
        return (
            f'<div class="stage"><div class="col">'
            f'<p id="what-tag">{esc(sc["tagline"])}</p>'
            f'<img id="what-logo" src="assets/{sc["logo"]}" alt="">'
            f'<p id="what-mark">{esc(sc["mark"])}</p>'
            f'<p id="what-line">{esc(sc["line"])}</p>'
            f'<p id="what-url">{esc(sc["url"])}</p></div></div>'
        )

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
            for k, (glyph, doing, where) in enumerate(sc["actions"], 1)
        )
        return (
            f'<div class="stage"><div class="col">'
            f'<img id="logo" src="assets/{sc["logo"]}" alt="">'
            f'<p id="mark">{esc(sc["mark"])}</p>'
            f"{acts}"
            f'<p id="punch">{esc(sc["punchline"])}</p></div></div>'
        )

    raise ValueError(t)


def scene_js(sc: dict, i: int, f: dict) -> list[str]:
    """Tweens for one scene, in global time. Entrances vary by element type so
    a scene has choreography rather than one repeated slide-up."""
    t, s, out = sc["type"], sc["start"], []
    if sc.get("eyebrow"):
        out.append(
            f'tl.fromTo("#s{i}-eyebrow",{{x:-26,opacity:0}},'
            f'{{x:0,opacity:1,duration:.55,ease:"power2.out"}},{s + 0.3:.2f});'
        )
        out.append(
            f'tl.fromTo("#s{i}-rule",{{scaleX:0}},'
            f'{{scaleX:1,duration:.6,ease:"expo.out"}},{s + 0.5:.2f});'
        )
    if sc.get("caption") and t not in ("loop", "cvd"):
        out.append(
            f'tl.fromTo("#s{i}-caption",{{y:16,opacity:0}},'
            f'{{y:0,opacity:1,duration:.55,ease:"power2.out"}},{s + 0.7:.2f});'
        )

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
            out.append(
                f'tl.fromTo("#s{i}-line",{{y:30,opacity:0}},'
                f'{{y:0,opacity:1,duration:.55,ease:"power3.out"}},{s + 0.2:.2f});'
            )
        out.append(
            f'tl.fromTo("#s{i}-rule",{{scaleX:0,opacity:{1 if opening else 0}}},'
            f'{{scaleX:1,opacity:1,duration:.7,ease:"expo.out"}},'
            f"{(0.0 if opening else s + 0.55):.2f});"
        )

    elif t == "loop":
        w = f["fig"]
        out.append(
            f'tl.fromTo("#s{i}-card",{{y:44,scale:.975,opacity:0}},'
            f'{{y:0,scale:1,opacity:1,duration:.75,ease:"power3.out"}},{s + 0.1:.2f});'
        )
        for k, at in enumerate(sc["step_at"], 1):  # beat-grid
            out.append(
                f'tl.fromTo("#s{i}-step{k}",{{y:16,opacity:0}},'
                f'{{y:0,opacity:1,duration:.45,ease:"power2.out"}},{at:.2f});'
            )
        wa, wd = sc["wipe_at"], sc["wipe_dur"]  # beat-locked
        out.append(
            f'tl.fromTo("#s{i}-gray",{{clipPath:"inset(0% 100% 0% 0%)"}},'
            f'{{clipPath:"inset(0% 0% 0% 0%)",duration:{wd},'
            f'ease:"power2.inOut"}},{wa:.2f});'
        )
        out.append(
            f'tl.fromTo("#s{i}-wipe",{{x:0,opacity:0}},'
            f'{{opacity:.9,duration:.18,ease:"power1.out"}},{wa:.2f});'
        )
        out.append(
            f'tl.to("#s{i}-wipe",{{x:{w - 4},duration:{wd},'
            f'ease:"power2.inOut"}},{wa:.2f});'
        )
        out.append(
            f'tl.to("#s{i}-wipe",{{opacity:0,duration:.22,ease:"power1.in"}},'
            f"{wa + wd - 0.15:.2f});"
        )
        out.append(
            f'tl.fromTo("#s{i}-caption",{{y:20,opacity:0}},'
            f'{{y:0,opacity:1,duration:.6,ease:"power2.out"}},'
            f"{sc['caption_at']:.2f});"
        )

    elif t == "cvd":
        w, wd = f["fig"], sc["wipe_dur"]
        out.append(
            f'tl.fromTo("#s{i}-card",{{y:44,scale:.975,opacity:0}},'
            f'{{y:0,scale:1,opacity:1,duration:.75,ease:"power3.out"}},{s + 0.1:.2f});'
        )
        for k, (_, _, _, at) in enumerate(sc["stages"], 1):
            # beat-grid; the grayscale stage is beat-locked to the 8.74s cue.
            out.append(
                f'tl.fromTo("#s{i}-w{k}",{{clipPath:"inset(0% 100% 0% 0%)"}},'
                f'{{clipPath:"inset(0% 0% 0% 0%)",duration:{wd},'
                f'ease:"power2.inOut"}},{at:.2f});'
            )
            out.append(
                f'tl.to("#s{i}-step{k}",{{opacity:1,duration:.3,'
                f'ease:"power1.out"}},{at:.2f});'
            )
            out.append(
                f'tl.fromTo("#s{i}-wipe",{{x:0,opacity:0}},'
                f'{{opacity:.9,duration:.14,ease:"power1.out"}},{at:.2f});'
            )
            out.append(
                f'tl.to("#s{i}-wipe",{{x:{w - 4},duration:{wd},'
                f'ease:"power2.inOut"}},{at:.2f});'
            )
            out.append(
                f'tl.to("#s{i}-wipe",{{opacity:0,duration:.16,'
                f'ease:"power1.in"}},{at + wd - 0.1:.2f});'
            )
        out.append(
            f'tl.fromTo("#s{i}-caption",{{y:20,opacity:0}},'
            f'{{y:0,opacity:1,duration:.6,ease:"power2.out"}},'
            f"{sc['caption_at']:.2f});"
        )

    elif t == "grid":
        for k, at in enumerate(sc["at"], 1):  # beat-grid
            out.append(
                f'tl.fromTo("#s{i}-t{k}",{{y:22,scale:.955,opacity:0}},'
                f'{{y:0,scale:1,opacity:1,duration:.5,ease:"power3.out"}},{at:.2f});'
            )

    elif t == "chips":
        for k, at in enumerate(sc["at"], 1):  # beat-grid
            out.append(
                f'tl.fromTo("#s{i}-c{k}",{{y:14,scale:.94,opacity:0}},'
                f'{{y:0,scale:1,opacity:1,duration:.42,ease:"back.out(1.3)"}},{at:.2f});'
            )

    elif t == "panel":
        out.append(
            f'tl.fromTo("#s{i}-panel",{{y:34,opacity:0}},'
            f'{{y:0,opacity:1,duration:.7,ease:"power3.out"}},{s + 0.25:.2f});'
        )
        for k, at in enumerate(sc["at"], 1):  # beat-grid
            out.append(
                f'tl.fromTo("#s{i}-r{k}",{{x:22,opacity:0}},'
                f'{{x:0,opacity:1,duration:.5,ease:"power2.out"}},{at:.2f});'
            )

    elif t == "shot":
        out.append(
            f'tl.fromTo("#s{i}-shot",{{y:48,scale:.97,opacity:0}},'
            f'{{y:0,scale:1,opacity:1,duration:.8,ease:"power3.out"}},{sc["at"]:.2f});'
        )
        if sc.get("scroll"):
            iw = f["shot"]
            ih = int(iw / sc["ratio"])
            reserve = int(f["eyebrow"] * 1.3 + f["body"] * 4.5 + 24)
            view = min(f["h"] - 2 * f["pad"] - reserve - 44, int(iw * f["view"]))
            travel = max(0, ih - view)
            begin = sc["at"] + 0.7
            span = round(sc["end"] - begin - 0.9, 2)
            if travel and span > 0.8:
                out.append(
                    f'tl.fromTo("#s{i}-page",{{y:0}},{{y:{-travel},'
                    f'duration:{span},ease:"power1.inOut"}},{begin:.2f});'
                )

    elif t == "flow":
        for k, at in enumerate(sc["at"], 1):
            if k > 1:
                out.append(
                    f'tl.fromTo("#s{i}-a{k}",{{opacity:0,x:-8}},'
                    f'{{opacity:1,x:0,duration:.3,ease:"power2.out"}},{at - 0.12:.2f});'
                )
            out.append(
                f'tl.fromTo("#s{i}-f{k}",{{y:14,opacity:0}},'
                f'{{y:0,opacity:1,duration:.42,ease:"back.out(1.6)"}},{at:.2f});'
            )

    elif t == "versus":
        a, b = sc["at"]
        out.append(
            f'tl.fromTo("#s{i}-vl",{{x:-34,opacity:0}},'
            f'{{x:0,opacity:1,duration:.6,ease:"power3.out"}},{a:.2f});'
        )
        out.append(
            f'tl.fromTo("#s{i}-vbar",{{scaleY:0}},'
            f'{{scaleY:1,duration:.5,ease:"expo.out"}},{a + 0.2:.2f});'
        )
        out.append(
            f'tl.fromTo("#s{i}-vr",{{x:34,opacity:0}},'
            f'{{x:0,opacity:1,duration:.6,ease:"power3.out"}},{b:.2f});'
        )

    elif t == "code":
        for n, at in enumerate(sc["at"], 1):
            out.append(
                f'tl.fromTo("#s{i}-c{n}",{{opacity:0}},'
                f"{{opacity:1,duration:.22}},{at:.2f});"
            )
        for n, at in sc.get("flag", []):
            out.append(
                f'tl.fromTo("#s{i}-c{n}",{{backgroundColor:"rgba(0,0,0,0)"}},'
                f'{{backgroundColor:"rgba(209,46,46,.12)",duration:.45,'
                f'ease:"power2.out"}},{at:.2f});'
            )

    elif t == "verify":
        for k, (at_claim, at_value) in enumerate(sc["at"], 1):
            out.append(
                f'tl.fromTo("#s{i}-v{k}",{{x:-20,opacity:0}},'
                f'{{x:0,opacity:1,duration:.45,ease:"power2.out"}},{at_claim:.2f});'
            )
            out.append(
                f'tl.fromTo("#s{i}-vv{k}",{{opacity:0,scale:.8}},'
                f'{{opacity:1,scale:1,duration:.35,ease:"back.out(2)"}},{at_value:.2f});'
            )

    elif t == "what":
        # Nothing. The card is complete on the first frame and holds until
        # the scene crossfades out, which is the whole point of it. The only
        # motion under it is the audio-reactive wash behind.
        pass

    elif t == "cta":
        out.append(
            f'tl.fromTo("#logo",{{scale:.88,opacity:0}},'
            f'{{scale:1,opacity:1,duration:.7,ease:"power3.out"}},{s + 0.2:.2f});'
        )
        out.append(
            f'tl.fromTo("#mark",{{y:24,opacity:0}},'
            f'{{y:0,opacity:1,duration:.6,ease:"power3.out"}},{s + 0.45:.2f});'
        )
        # The asks arrive in reading order and stay. Whatever is on screen at
        # the last frame is what a viewer who paused there has to act on.
        for k in range(1, len(sc["actions"]) + 1):
            out.append(
                f'tl.fromTo("#cta{k}",{{y:18,opacity:0}},'
                f'{{y:0,opacity:1,duration:.55,ease:"power2.out"}},'
                f"{s + 0.75 + (k - 1) * 0.35:.2f});"
            )
        # The line lands after the asks, not with them: a viewer reads the two
        # things to do, then gets the sentence to carry away. `punch_at` is a
        # film-clock second, so it is on the grid like every other reveal.
        out.append(
            f'tl.fromTo("#punch",{{y:20,opacity:0}},'
            f'{{y:0,opacity:1,duration:.75,ease:"power3.out"}},'
            f'{sc.get("punch_at", s + sc["dur"] * 0.55):.2f});'
        )
    return out


SFX_FILES = {
    "drop": ("sfx/interface/drop_001.ogg", 0.11, 0.55),
    "wipe": ("sfx/impact/impactSoft_medium_001.ogg", 0.19, 0.50),
    "tile": ("sfx/interface/drop_001.ogg", 0.11, 0.50),
    "bell": ("sfx/impact/impactBell_heavy_000.ogg", 1.48, 0.62),
}


def vo_duration(name: str) -> float:
    """Length of one narration track, in seconds.

    Read from the WAV header with the standard library rather than by
    shelling out to ``ffprobe``. The tracks this measures are PCM WAV
    written by the suite's own narrator, which is exactly what :mod:`wave`
    is for; the numbers agree with ``ffprobe`` to the millisecond this
    rounds to.

    That is one fewer binary between a clone and a build. It was also the
    one that turned the hub's CI red: three guards that compose timelines —
    and deliberately never render — were dragged through a subprocess call
    to a tool no runner installs.
    """
    path = ASSETS / f"vo-{name}.wav"
    if not path.is_file():
        raise FileNotFoundError(
            f"no narration track at {path}. The tracks are gitignored on "
            f"purpose (they are tens of megabytes); run "
            f"`python3 brag-output/narrate_films.py` to make them, or "
            f"`restore_assets.py` to bring them back."
        )
    with wave.open(str(path), "rb") as w:
        return round(w.getnframes() / w.getframerate(), 3)


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
        for i, sc in enumerate(scenes, 1)
    )

    # From frame one, not from the end of scene one. The rails carry the
    # wordmark and the address, and holding them back left every film opening
    # on an empty sheet while the first sentence faded up. A viewer who lands
    # on a blank frame has already decided what kind of video this is.
    rails_start = 0.0
    beats = "<i>\u00b7</i>".join(
        f'<span id="beat-{b}">{esc(say(BEAT_LABEL[b], lang))}</span>'
        for b in BEAT_ORDER
    )
    rails = (
        f'<div id="rails" class="clip" data-start="{rails_start}" '
        f'data-duration="{round(dur - rails_start, 2)}" data-track-index="90">'
        f'<div class="inner" id="rails-inner">'
        f'<p id="rail-l">Sprezzature</p><p id="rail-r">sprezzature.ai</p>'
        f'<div id="beats">{beats}</div>'
        f'<div id="rail-line"></div></div></div>'
    )

    # Audio. Voice on its own lane; each overlapping SFX gets its own index.
    audio = [
        f'<audio id="bgm" data-start="0" data-duration="{dur}" '
        f'data-track-index="10" data-volume="1" src="assets/music/{MUSIC}"></audio>'
    ]
    duck = []
    for name, at in voice_track(film_key, spec, lang):
        d = vo_duration(name)
        audio.append(
            f'<audio id="vo-{name}" data-start="{at}" data-duration="{d}" '
            f'data-track-index="11" data-volume="1" '
            f'src="assets/vo-{name}.wav"></audio>'
        )
        duck.append((at, at + d))
    for n, (kind, at) in enumerate(spec["sfx"]):
        src, sd, vol = SFX_FILES[kind]
        audio.append(
            f'<audio id="sfx-{n}" data-start="{at}" data-duration="{sd}" '
            f'data-track-index="{12 + n}" data-volume="{vol}" '
            f'src="assets/{src}"></audio>'
        )

    # Music: in, duck across the whole narrated stretch, lift once the voice is
    # done, fade out on the held frame.
    first_vo, last_vo = duck[0][0], duck[-1][1]
    js = [
        'tl.fromTo("#bgm",{volume:0},{volume:.3,duration:.8,ease:"power1.out"},0);',
        f'tl.to("#bgm",{{volume:.13,duration:.35,ease:"power1.inOut"}},{max(0.85, first_vo - 0.35):.2f});',
        f'tl.to("#bgm",{{volume:.27,duration:.6,ease:"power1.inOut"}},{last_vo + 0.15:.2f});',
        f'tl.to("#bgm",{{volume:0,duration:.9,ease:"power1.in"}},{dur - 1.0:.2f});',
    ]

    # Crossfades: clip windows overlap 0.6s and the incoming scene, later in the
    # DOM, fades up over the outgoing one.
    for i, sc in enumerate(scenes, 1):
        if i == 1:
            js.append(
                f'tl.to("#s1-inner",{{opacity:0,duration:.6,ease:"power1.inOut"}},'
                f"{sc['end']:.2f});"
            )
        else:
            js.append(
                f'tl.fromTo("#s{i}-inner",{{opacity:0}},'
                f'{{opacity:1,duration:.6,ease:"power1.inOut"}},{sc["start"]:.2f});'
            )
            if i < len(scenes):
                js.append(
                    f'tl.to("#s{i}-inner",{{opacity:0,duration:.6,'
                    f'ease:"power1.inOut"}},{sc["end"]:.2f});'
                )
        js += scene_js(sc, i, f)

    # The wordmark and the address are on screen at frame zero, not fading
    # towards it. `fromTo({opacity:0}, ...)` at t=0 reads as "from frame one"
    # and is not: it puts the rails at exactly zero on the frame a viewer is
    # most likely to see as a still. Only the hairline under them is drawn,
    # and a hairline growing is not an empty frame.
    js.append(
        f'tl.fromTo("#rail-line",{{scaleX:0}},{{scaleX:1,duration:1.1,'
        f'ease:"expo.out"}},{rails_start:.2f});'
    )

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
            js.append(
                f'tl.set("#beat-{lit}",{{color:"#a3a3a3",fontWeight:500}},{at:.2f});'
            )
        js.append(
            f'tl.set("#beat-{sc["beat"]}",{{color:"{BLUE}",fontWeight:700}},{at:.2f});'
        )
        lit = sc["beat"]

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={f["w"]}, height={f["h"]}" />
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
     data-width="{f["w"]}" data-height="{f["h"]}" data-fps="30">
  <div class="bg"><div class="bg-grid"></div><div class="bg-wash" id="wash"></div></div>
{body}
{rails}
{chr(10).join(audio)}
</div>
<script>
(function () {{
  var tl = gsap.timeline({{ paused: true }});
{chr(10).join("  " + line for line in js)}

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
    (d / "hyperframes.json").write_text(
        json.dumps(
            {
                "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                "paths": {
                    "blocks": "compositions",
                    "components": "compositions/components",
                    "assets": "assets",
                },
                "media": {"autoProxy": True},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (d / "package.json").write_text(
        json.dumps(
            {
                "name": project_name(film_key, lang, fmt_key),
                "private": True,
                "type": "module",
                "scripts": {
                    "check": "npx --yes hyperframes@0.8.46 check",
                    "render": "npx --yes hyperframes@0.8.46 render",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
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
            shutil.rmtree(d)  # a film or format that no longer exists
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
        FILMS_DIR / project_name(k, lang, fmt) for k, lang in pairs for fmt in FORMATS
    }
    clean(wanted)
    built = [emit(k, FILMS[k], fmt, lang) for k, lang in pairs for fmt in FORMATS]
    for p in built:
        print(p.relative_to(ROOT))
    kept = sum(1 for d in FILMS_DIR.iterdir() if (d / "renders").is_dir())
    print(f"{len(built)} projects ({kept} with renders kept)")


if __name__ == "__main__":
    main()

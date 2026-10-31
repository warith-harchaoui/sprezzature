#!/usr/bin/env python3
"""The narration script of the eleven films, in both languages.

Not a transcript and not a translation
--------------------------------------
The text here is what the engine is asked to say; the timings are where each
line is asked to land. ``narrate_films.py`` reads this table, speaks it, and
returns the audio and the WebVTT together — so the cues are exact where a
transcriber would only be close.

The two language columns are **written, not translated**. Until 2026-10-28 the
French was a line-for-line rendering of the English: same number of lines, same
sentence boundaries, same clause order, French words in English syntax. On
screen that problem had already been fixed — ``build_films.L`` puts the two
languages on adjacent lines so each is composed with the rest of its own script
visible — and the voice was the half that had not caught up.

So the columns now diverge where the languages do. French splits a sentence
English runs on (``colors``: *La clarté, elle, tient.* alone on its line) and
runs on where English splits (``audio``: the ninety characters and *nobody
reads that* are one French breath). The two cuts of a film make the same case
with the same numbers and do not line up line by line, which is the point:
a viewer watches one of them, never both.

What governs the line count is the picture, not the other language. A line is
written to land on the scene it talks about, so a film with a long middle scene
takes more lines there in whichever language wants them.

Pitch, not plot
---------------
Every script runs Guy KAWASAKI's order — what, problem, solution, underlying
magic, call to action — and the material for each beat is the film's row in
``KAWASAKI.md``, which was taken from the package rather than from a feature
list. Three defects that order caught here, all of them invisible while the
beats lived only in the scene list:

* ``audio`` stated its numbers and never said why they are flags rather than
  laws. The numbers are the inventory; *conventions rather than laws* is the
  insight, and it was missing from the voice.
* ``maps`` spent its magic beat on the plate that draws no map and never
  reached the precision encoding — that ACLED and UCDP both record how well a
  coordinate is known, and that a tool drawing every one as the same dot
  asserts a street corner the source never gave.
* ``sprezzature`` said a vision model finds the fault and stopped there. What
  makes the loop worth a minute is the next clause: what you fix is the source.

Run from brag-output/:  python3 narrate_films.py
"""

from __future__ import annotations

import sys

#: start, nominal duration, text.
#:
#: The duration column is vestigial — ``narrate_films`` measures the WAV the
#: engine actually produced and lays the cues out on that. It is kept so the
#: table's shape stays readable as "when, how long, what".
#:
#: The start column is a *request*. ``narrate_films --fit`` treats it as the
#: scene a line wants to land on and moves it later when the line before it
#: runs long, which is what chatterbox makes necessary: the same sentence
#: measured 7.520, 6.760 and 6.640 seconds on three runs, so a grid typed by
#: hand is a grid that fails on a different film every time it is rendered.
FILMS: dict[str, dict[str, list[tuple[float, float, str]]]] = {
    "sprezzature": {
        "en": [
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. 10 packages of design know-how.",
            ),
            (6.20, 3.0, "Every rule in it was written by somebody else."),
            (11.10, 3.0, "Almost every design decision is already settled."),
            (15.00, 3.0, "Contrast: the W3C. The laws of attention: Jon YABLONSKI."),
            (19.40, 3.0, "Colour blindness: a paper from 2009, measured on real eyes."),
            (
                24.00,
                3.0,
                "Published years ago. Your tools have never heard of any of it.",
            ),
            (
                29.00,
                3.0,
                "It is code now, pointed both ways. At what you make, at what is live.",
            ),
            (34.20, 3.0, "167 chart kinds. 20 accessibility rules. 30 laws of UX."),
            (
                38.80,
                3.0,
                "The rule that draws the figure is the rule that audits the page.",
            ),
            (49.00, 3.0, "A vision model renders the chart and looks at it."),
            (53.20, 3.0, "It says what is wrong. Then you fix the source."),
            (57.20, 3.0, "The model edits the plan. It never touches the picture."),
            (61.40, 3.0, "Then the chart is drawn again. That is the whole loop."),
            (
                76.00,
                3.0,
                "A matrix, a calendar, a migration flow, a choropleth. 4 of 167 kinds.",
            ),
            (
                88.20,
                3.0,
                "This one is drawn on Equal Earth, a projection published in 2018.",
            ),
            (99.00, 3.0, "Everything stays on your desk. Nothing travels."),
            (
                104.60,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (110.50, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            (1.10, 3.0, "Sprezzature est un moteur d'IA pour le design."),
            (
                5.00,
                3.0,
                "10 paquets de savoir-faire. Aucune de leurs règles n'est de nous.",
            ),
            (11.80, 3.0, "Presque toutes les décisions de design sont déjà prises."),
            (
                16.20,
                3.0,
                "Le contraste, c'est le W3C. Les lois de l'attention, Jon YABLONSKI.",
            ),
            (21.00, 3.0, "Ce que voit un lecteur daltonien : un article de 2009."),
            (25.40, 3.0, "Publié il y a des années. Vos outils ne l'ont jamais lu."),
            (30.20, 3.0, "Maintenant c'est du code, pointé des deux côtés."),
            (
                38.00,
                3.0,
                "167 types de graphiques. 20 règles d'accessibilité. 30 lois d'UX.",
            ),
            (42.60, 3.0, "La règle qui trace la figure est celle qui audite la page."),
            (
                49.40,
                3.0,
                "Un modèle de vision rend le graphique, le regarde, dit ce qui cloche.",
            ),
            (54.00, 3.0, "Ce qu'on corrige ensuite, c'est la source, jamais l'image."),
            (58.20, 3.0, "Le modèle change le plan. Il ne touche jamais au rendu."),
            (62.40, 3.0, "Puis la figure est redessinée. Voilà toute la boucle."),
            (
                76.60,
                3.0,
                "Une matrice, un calendrier, un flux, un choroplèthe : 4 sur 167.",
            ),
            (
                88.80,
                3.0,
                "Celle-ci est en Equal Earth, une projection publiée en 2018.",
            ),
            (99.40, 3.0, "Tout reste sur votre poste. Rien ne circule."),
            (
                104.60,
                3.0,
                "Passez sur sprezzature.ai, et mettez une étoile GitHub si ça le mérite.",
            ),
            (110.50, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "colors": {
        "en": [
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. Colors proves your colours can be read.",
            ),
            (
                7.80,
                3.0,
                "Light grey on white reads perfectly well. At your desk, indoors.",
            ),
            (
                15.00,
                3.0,
                "Whoever chose the colour can read it. That is the whole problem.",
            ),
            (22.00, 3.0, "Red against green is the other half, for about 1 man in 12."),
            (
                29.80,
                3.0,
                "Run with no arguments, it audits the palette this package ships with.",
            ),
            (35.60, 3.0, "56 pairs a real theme puts together. 22 of them fail."),
            (
                41.40,
                3.0,
                "Brand yellow on white is 1.51 to 1, where plain text needs 4.5.",
            ),
            (46.80, 3.0, "So it exits 1, and the build that called it stops there."),
            (
                52.80,
                3.0,
                "A colour has 3 parts, and only one of them survives everything.",
            ),
            (
                58.60,
                3.0,
                "Colour blindness takes the hue. Grey printing takes the saturation.",
            ),
            (
                64.40,
                3.0,
                "Nothing takes the lightness, so that is the axis the fix walks.",
            ),
            (
                70.20,
                3.0,
                "Along OKLCH, by Björn OTTOSSON, keeping the nearest colour that passes.",
            ),
            (77.40, 3.0, "The same chart now, redrawn for each of those eyes."),
            (
                83.00,
                3.0,
                "Watch South and East. The hue between them goes, the bars stay apart.",
            ),
            (89.60, 3.0, "Then no colour at all, and 3 regions still."),
            (95.40, 3.0, "The matrices are MACHADO, 2009, measured on real observers."),
            (
                100.60,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (109.00, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            (1.10, 3.0, "Sprezzature est un moteur d'IA pour le design."),
            (5.00, 3.0, "Colors prouve que vos couleurs se lisent."),
            (
                8.40,
                3.0,
                "Du gris clair sur du blanc, ça se lit. Au bureau, à l'intérieur.",
            ),
            (
                15.20,
                3.0,
                "Celui qui a choisi la couleur, lui, la lit. Tout le problème est là.",
            ),
            (
                22.00,
                3.0,
                "Et le rouge contre le vert : 1 homme sur 12 ne les sépare pas pareil.",
            ),
            (
                29.80,
                3.0,
                "Lancé sans aucun argument, il audite la palette qu'il livre lui-même.",
            ),
            (35.80, 3.0, "56 paires réelles. 22 échouent."),
            (
                41.60,
                3.0,
                "Son jaune de marque sur blanc : 1,51 contre 1. Le texte demande 4,5.",
            ),
            (
                47.00,
                3.0,
                "Il sort en code 1, et la compilation qui l'appelait s'arrête.",
            ),
            (
                52.80,
                3.0,
                "Une couleur a 3 parties mobiles, et une seule résiste à tout.",
            ),
            (
                58.80,
                3.0,
                "Le daltonisme retire la teinte, l'impression en gris la saturation.",
            ),
            (
                64.60,
                3.0,
                "Rien ne retire la clarté. Donc la correction ne parcourt que cet axe.",
            ),
            (
                70.40,
                3.0,
                "En OKLCH, de Björn OTTOSSON, jusqu'à la plus proche qui passe.",
            ),
            (78.40, 3.0, "Le même graphique, redessiné pour chacun de ces yeux."),
            (
                85.00,
                3.0,
                "Le Sud et l'Est : la teinte s'en va, les barres restent séparées.",
            ),
            (
                92.00,
                3.0,
                "Puis plus aucune couleur, et 3 régions encore. MACHADO, 2009.",
            ),
            (
                100.60,
                3.0,
                "Passez sur sprezzature.ai. Une étoile GitHub, si ça le mérite.",
            ),
            (109.00, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "ux-laws": {
        "en": [
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. Ux-laws, the audit of the laws of UX.",
            ),
            (
                7.00,
                3.0,
                "They will say the page is overwhelming and they cannot find the button.",
            ),
            (12.60, 3.0, "Nobody will ever say HICK's Law. Nobody knows its name."),
            (17.60, 3.0, "You get the symptom and never the cause, published in 1952."),
            (28.60, 3.0, "30 laws, collected by Jon YABLONSKI."),
            (32.80, 3.0, "8 of them settle from the source alone."),
            (
                36.80,
                3.0,
                "No browser, no rendering: the median page takes 5 milliseconds.",
            ),
            (
                41.60,
                3.0,
                "Fast enough to live in a pre-commit hook, which is where a gate must live.",
            ),
            (46.60, 3.0, "HICK's Law counts the choices a person meets at one moment."),
            (
                52.60,
                3.0,
                "A responsive header holds 2 menus that never paint together.",
            ),
            (
                57.40,
                3.0,
                "Adding them up charges the reader for choices no screen ever shows.",
            ),
            (
                63.60,
                3.0,
                "So the auditor places each control and reports the worse count, naming it.",
            ),
            (70.00, 3.0, "A block that collapses is one choice, whatever it holds."),
            (
                77.80,
                3.0,
                "40 links in one nav, or 7. One exits zero, the other exits one.",
            ),
            (
                85.00,
                3.0,
                "40 is a fact about the markup. Whether 40 is too many is not.",
            ),
            (92.00, 3.0, "It is a fast gate, not a substitute for design review."),
            (
                101.40,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (109.60, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            (1.10, 3.0, "Sprezzature est un moteur d'IA pour le design."),
            (4.60, 3.0, "Ux-laws, l'audit des lois d'UX."),
            (
                7.60,
                3.0,
                "On vous dira que la page est écrasante, qu'on n'y trouve jamais le bouton.",
            ),
            (
                13.20,
                3.0,
                "Personne ne dira jamais : loi de HICK. Personne n'en connaît le nom.",
            ),
            (
                18.20,
                3.0,
                "Vous récupérez le symptôme, et jamais la cause, publiée depuis 1952.",
            ),
            (
                28.60,
                3.0,
                "30 lois réunies par Jon YABLONSKI. 8 tranchées depuis la source.",
            ),
            (
                36.80,
                3.0,
                "Aucun navigateur, aucun rendu : la page médiane en 5 millisecondes.",
            ),
            (41.60, 3.0, "Assez rapide pour tenir dans un crochet de pré-commit."),
            (46.60, 3.0, "Or la loi de HICK compte les choix offerts au même instant."),
            (
                52.60,
                3.0,
                "Un en-tête adaptatif porte 2 menus qui ne s'affichent jamais ensemble.",
            ),
            (
                57.40,
                3.0,
                "Les additionner reproche au lecteur des choix qu'aucun écran ne montre.",
            ),
            (
                63.60,
                3.0,
                "L'auditeur situe donc chaque contrôle et retient le pire des deux comptes.",
            ),
            (
                70.00,
                3.0,
                "Un bloc qui se replie vaut un seul choix, quoi qu'il contienne.",
            ),
            (
                77.80,
                3.0,
                "40 liens dans un menu, ou 7. L'un renvoie zéro, l'autre renvoie un.",
            ),
            (
                85.00,
                3.0,
                "40 est un fait sur le balisage. Savoir si c'est trop n'en est pas un.",
            ),
            (
                92.00,
                3.0,
                "C'est un verrou rapide, pas un substitut à une revue de design.",
            ),
            (
                101.40,
                3.0,
                "Passez sur sprezzature.ai, et mettez une étoile GitHub si ça le mérite.",
            ),
            (109.60, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "accessibility": {
        "en": [
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. Accessibility reads your HTML.",
            ),
            (5.60, 3.0, "20 rules, and not one of them opens a browser."),
            (9.80, 3.0, "A video starts playing by itself, with sound."),
            (
                14.20,
                3.0,
                "A blind reader cannot now hear the screen reader they would use to stop it.",
            ),
            (20.00, 3.0, "And the page is valid. No validator says a word about it."),
            (31.40, 3.0, "Here is the page. Line 5 is the trap: autoplay with sound."),
            (37.60, 3.0, "Each finding names the element, the line, and the rule."),
            (42.40, 3.0, "3 of the 6 on this page sit on that one line."),
            (
                47.00,
                3.0,
                "Standard library for the lint. One dependency, for the command line.",
            ),
            (54.60, 3.0, "6 of the 20 repair themselves. Only 6."),
            (
                59.00,
                3.0,
                "A repair is automatic only where exactly one repair is safe.",
            ),
            (63.80, 3.0, "The other 14 are reported, and never guessed at."),
            (
                68.40,
                3.0,
                "The exception is the alt text, drafted from the image and the page.",
            ),
            (
                77.80,
                3.0,
                "Shown the pixels alone, the draft was a dark coat and a patterned shirt.",
            ),
            (
                84.20,
                3.0,
                "Given the page as well, it wrote Paris, the Institute, the decade.",
            ),
            (
                91.00,
                3.0,
                "None of that was in the photograph. And it is still a draft.",
            ),
            (
                100.60,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (108.60, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            (1.10, 3.0, "Sprezzature est un moteur d'IA pour le design."),
            (4.80, 3.0, "Accessibility tranche 20 règles en lisant votre HTML."),
            (9.80, 3.0, "Une vidéo démarre toute seule, avec le son."),
            (
                14.20,
                3.0,
                "Le lecteur aveugle n'entend plus l'outil qui lui servirait à l'arrêter.",
            ),
            (20.00, 3.0, "Et la page est valide : aucun validateur n'y trouve rien."),
            (
                31.40,
                3.0,
                "Voici la page. Ligne 5, le piège : la lecture automatique avec le son.",
            ),
            (
                37.60,
                3.0,
                "Chaque constat nomme l'élément. Puis la ligne, et la règle enfreinte.",
            ),
            (
                43.00,
                3.0,
                "Bibliothèque standard pour le linter. Une dépendance, pour la ligne de commande.",
            ),
            (55.00, 3.0, "6 des 20 se réparent seules. 6, pas une de plus."),
            (
                59.60,
                3.0,
                "Une réparation n'est automatique que là où il n'en existe qu'une de sûre.",
            ),
            (64.60, 3.0, "Les 14 autres sont signalées, jamais devinées."),
            (
                69.00,
                3.0,
                "L'exception, c'est le texte alternatif. Rédigé d'après l'image et la page.",
            ),
            (
                78.00,
                3.0,
                "Sur les seuls pixels : un manteau sombre, une chemise à motifs.",
            ),
            (
                84.40,
                3.0,
                "Avec la page autour, autre chose. Paris, l'Institut, la décennie.",
            ),
            (
                91.20,
                3.0,
                "Rien de cela n'était dans la photographie, et c'est un brouillon.",
            ),
            (
                100.60,
                3.0,
                "Passez sur sprezzature.ai. Une étoile GitHub, si ça le mérite.",
            ),
            (108.60, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "maps": {
        "en": [
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. Maps draws on real ground.",
            ),
            (
                7.40,
                3.0,
                "You hold an export of conflict events. Every row says how well it is located.",
            ),
            (
                18.00,
                3.0,
                "Drop the point layer. Every row becomes the same confident dot.",
            ),
            (
                23.00,
                3.0,
                "The map asserts a street corner the source never gave, once per row.",
            ),
            (
                27.60,
                3.0,
                "3 generators draw here, on real coastlines and measured relief.",
            ),
            (
                37.00,
                3.0,
                "A ramp stretched end to end is a story. Here the legend names its classes.",
            ),
            (
                42.40,
                3.0,
                "The world sits on Equal Earth: ŠAVRIČ, PATTERSON and JENNY, 2018.",
            ),
            (
                47.40,
                3.0,
                "Then the plate that draws no map. The land appears because events fell.",
            ),
            (
                54.60,
                3.0,
                "ACLED, the armed conflict location and event data project, grades 1 to 3.",
            ),
            (59.60, 3.0, "The Uppsala conflict data program, UCDP, grades it 1 to 7."),
            (
                64.40,
                3.0,
                "So a named place is a filled disc, and an approximate one a hollow ring.",
            ),
            (
                69.00,
                3.0,
                "A province pinned to its capital gets a broken ring, never a dot.",
            ),
            (73.60, 3.0, "That wording is ACLED's own, read out of its codebook."),
            (
                82.40,
                3.0,
                "Ukraine. 6 markers, 6 rings, because the source said approximate.",
            ),
            (
                88.60,
                3.0,
                "Nothing on this plate claims a position the source never gave.",
            ),
            (
                100.40,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (108.60, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            (1.10, 3.0, "Sprezzature est un moteur d'IA pour le design."),
            (4.60, 3.0, "Maps dessine sur un vrai sol, et dit ce qu'il ne sait pas."),
            (
                8.20,
                3.0,
                "Un export d'événements de conflit. Chaque ligne dit ce qu'elle sait du lieu.",
            ),
            (
                18.20,
                3.0,
                "Vous posez la couche de points, et toutes deviennent le même point.",
            ),
            (
                23.40,
                3.0,
                "La carte affirme un coin de rue que la source n'a jamais donné.",
            ),
            (
                27.80,
                3.0,
                "3 générateurs dessinent ici, sur de vraies côtes et un relief mesuré.",
            ),
            (
                37.20,
                3.0,
                "Une rampe étirée d'un bout à l'autre, c'est une histoire, pas une échelle.",
            ),
            (
                42.60,
                3.0,
                "Le monde est en Equal Earth : ŠAVRIČ, PATTERSON et JENNY, 2018.",
            ),
            (47.60, 3.0, "Puis la planche qui ne dessine aucune carte."),
            (51.20, 3.0, "La terre apparaît parce que des événements y sont tombés."),
            (54.80, 3.0, "ACLED, c'est le projet de données sur les conflits armés."),
            (
                59.20,
                3.0,
                "ACLED note de 1 à 3. UCDP, le programme d'Uppsala, va de 1 à 7.",
            ),
            (
                64.60,
                3.0,
                "Un lieu nommé devient un disque plein ; un lieu approché, un anneau creux.",
            ),
            (
                69.20,
                3.0,
                "Une province épinglée sur sa capitale : un anneau brisé, jamais un point.",
            ),
            (73.80, 3.0, "Ces mots sont ceux d'ACLED, lus dans son codebook."),
            (
                82.60,
                3.0,
                "L'Ukraine. 6 marqueurs, 6 anneaux : la source a dit approximatif.",
            ),
            (
                100.40,
                3.0,
                "Passez sur sprezzature.ai. Une étoile GitHub, si ça le mérite.",
            ),
            (108.60, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "figures": {
        "en": [
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. Figures draws the chart your rows ask for.",
            ),
            (
                9.40,
                3.0,
                "A spreadsheet is open, and no chart in it is obviously the right one.",
            ),
            (13.80, 3.0, "So you reach for the bar chart you reached for last time."),
            (
                18.40,
                3.0,
                "Ask an assistant instead. It writes plotting code, and an image comes out.",
            ),
            (
                23.40,
                3.0,
                "Nobody looks at that image. The labels collide, on a white panel, on a dark page.",
            ),
            (
                28.60,
                3.0,
                "Here you name the kind, hand over your rows, and get a file back.",
            ),
            (
                33.20,
                3.0,
                "167 kinds in 68 categories, and every one of them is marked stable.",
            ),
            (
                40.20,
                3.0,
                "Exported, a chart is a picture. Written line by line, it is a document.",
            ),
            (
                48.60,
                3.0,
                "144 of the 167 generators share one root: a title, a description, a dark twin.",
            ),
            (
                58.60,
                3.0,
                "Each kind declares the data roles it needs, so your columns do the choosing.",
            ),
            (
                63.60,
                3.0,
                "Region, quarter and units fill 64 of the kinds, ranked by readability.",
            ),
            (
                70.00,
                3.0,
                "All of that is deterministic, and no model was consulted for any of it.",
            ),
            (
                77.00,
                3.0,
                "So the Ralph Eyeball Loop renders it, and a vision model looks at the picture.",
            ),
            (
                82.00,
                3.0,
                "Qwen3-VL through Ollama, offline. What it edits is the plan, never the picture.",
            ),
            (88.60, 3.0, "16 parts of this one take keyboard focus."),
            (
                93.00,
                3.0,
                "Each one says its own numbers to a reader who cannot see the ribbon.",
            ),
            (
                103.00,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (109.60, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            (
                1.10,
                3.0,
                "Sprezzature est un moteur d'IA pour le design. Figures dessine le bon graphique.",
            ),
            (9.40, 3.0, "Un tableur ouvert, et aucun graphique qui s'impose."),
            (
                13.00,
                3.0,
                "On reprend donc celui de la dernière fois. Des barres, toujours des barres.",
            ),
            (
                18.40,
                3.0,
                "Demandez plutôt à un assistant : il écrit du code de tracé, une image sort.",
            ),
            (23.40, 3.0, "Personne ne la regarde."),
            (
                25.40,
                3.0,
                "Étiquettes superposées, titre de gabarit oublié, blanc sur fond sombre.",
            ),
            (30.60, 3.0, "Ici, un nom de type, vos lignes, et un fichier qui revient."),
            (
                34.60,
                3.0,
                "Le catalogue en compte 167, répartis en 68 catégories, tous stables.",
            ),
            (
                40.20,
                3.0,
                "Exporté, un graphique est une image. Écrit ligne à ligne, c'est un document.",
            ),
            (
                48.60,
                3.0,
                "Sur 167 générateurs, 144 partagent la même racine accessible.",
            ),
            (
                58.60,
                3.0,
                "Chaque type déclare les rôles de données qu'il exige, et vos colonnes tranchent.",
            ),
            (
                64.00,
                3.0,
                "64 types classés par lisibilité : région, trimestre, unités.",
            ),
            (70.00, 3.0, "Déterministe. Aucun modèle n'a été consulté."),
            (
                77.00,
                3.0,
                "La boucle Ralph dessine, puis un modèle de vision regarde l'image finie.",
            ),
            (
                82.00,
                3.0,
                "Qwen3-VL via Ollama, hors ligne. Il corrige le plan, jamais l'image.",
            ),
            (
                88.60,
                3.0,
                "16 parties de cette figure prennent le focus, chacune avec ses chiffres.",
            ),
            (
                103.00,
                3.0,
                "Passez sur sprezzature.ai, et mettez une étoile GitHub si ça le mérite.",
            ),
            (109.60, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "publish": {
        "en": [
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. Publish turns Markdown into a site.",
            ),
            (
                6.80,
                3.0,
                "It will even read the page aloud, highlighting the sentence as it goes.",
            ),
            (
                12.00,
                3.0,
                "One sentence out of step is worse than no highlighting at all.",
            ),
            (18.00, 3.0, "And it points at the wrong line, with total confidence."),
            (
                29.00,
                3.0,
                "10 tools carry a document from Markdown to a page people can find.",
            ),
            (35.00, 3.0, "10 in the repository. 9 in the package you install today."),
            (
                44.20,
                3.0,
                "A page with no Markdown behind it is read exactly the same way.",
            ),
            (
                50.40,
                3.0,
                "Then the hard part. The audio and the page leave by different roads.",
            ),
            (
                56.60,
                3.0,
                "Sentences go to the voice engine. Blocks are walked as a tree.",
            ),
            (
                61.60,
                3.0,
                "So the module refuses to number the sentences on its own side.",
            ),
            (
                66.40,
                3.0,
                "It takes the cues the narration wrote and compares the two lists.",
            ),
            (71.60, 3.0, "They match, or it refuses. There is no third outcome."),
            (
                77.40,
                3.0,
                "This is the package's own documentation, narrated and bound by it.",
            ),
            (
                82.80,
                3.0,
                "Watch the highlight. The browser is doing that, not a script.",
            ),
            (87.60, 3.0, "The cues are WebVTT, the timed-text format of the web."),
            (93.40, 3.0, "Not one line of synchronisation code was written here."),
            (
                100.90,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (107.60, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            (
                1.10,
                3.0,
                "Sprezzature est un moteur d'IA pour le design. Publish fait du Markdown un site.",
            ),
            (
                6.80,
                3.0,
                "La page se lit même à voix haute, en surlignant la phrase au passage.",
            ),
            (
                12.20,
                3.0,
                "Une phrase de décalage vaut moins que pas de surlignage du tout.",
            ),
            (18.00, 3.0, "Et il pointe la mauvaise ligne, avec une entière assurance."),
            (
                29.00,
                3.0,
                "10 outils mènent le document au site. 9 sont publiés à ce jour.",
            ),
            (
                36.00,
                3.0,
                "Une page sans Markdown derrière elle se lit exactement pareil.",
            ),
            (44.20, 3.0, "Vient le plus dur. L'audio et la page partent par 2 routes."),
            (
                50.40,
                3.0,
                "Les phrases vont au moteur de voix ; les blocs comme un arbre.",
            ),
            (56.60, 3.0, "Le module refuse donc de numéroter les phrases de son côté."),
            (
                61.60,
                3.0,
                "Il reprend les repères de la narration et compare les deux listes.",
            ),
            (67.00, 3.0, "Elles coïncident, ou il refuse. Pas de troisième issue."),
            (
                77.40,
                3.0,
                "Ici, c'est la documentation du paquet, narrée et reliée par lui.",
            ),
            (83.00, 3.0, "Regardez le surlignage. C'est le navigateur, pas un script."),
            (
                88.60,
                3.0,
                "Les repères sont du WebVTT, le format de texte minuté du web.",
            ),
            (
                94.20,
                3.0,
                "Pas une ligne de code de synchronisation n'a été écrite ici.",
            ),
            (
                100.90,
                3.0,
                "Passez sur sprezzature.ai, et mettez une étoile GitHub si ça le mérite.",
            ),
            (107.60, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "audio": {
        "en": [
            # WHAT -- the suite's sentence first, as in all eleven films.
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. Audio reads speech both ways.",
            ),
            (
                6.40,
                3.0,
                "A recording becomes timed text. Written text becomes timed speech.",
            ),
            # PROBLEM -- the fact first, the cost second. The sentence under it is
            # `scripts/audit_captions.py:7`.
            (11.20, 3.0, "Your video has captions and they are accurate."),
            (
                15.40,
                3.0,
                "90 characters on screen, for half a second. Nobody reads that.",
            ),
            # The same failure, turned around. This film's shape arrives in the
            # problem beat rather than waiting for the solution to show it.
            (
                21.20,
                3.0,
                "Turn it around. A page reads aloud, and highlights the wrong line.",
            ),
            # SOLUTION -- two lanes, and the same file under each of them.
            (
                29.60,
                3.0,
                "One modality, read in both directions, and never leaving your machine.",
            ),
            (
                35.40,
                3.0,
                "Sound into text: what was said, who said it, in which language.",
            ),
            (41.20, 3.0, "Text into sound: a WAV, and a WebVTT beside it."),
            (
                45.80,
                3.0,
                "The same timed track either way. That is how a page follows a reading.",
            ),
            # MAGIC -- the numbers have a publisher, and that is the point.
            (
                52.80,
                3.0,
                "These are not numbers somebody liked. They have a publisher.",
            ),
            (
                58.60,
                3.0,
                "Netflix's timed text style guide, and the code says so in a comment.",
            ),
            (64.20, 3.0, "17 characters a second. 42 to a line. 2 lines at most."),
            # The sentence the old cut stopped short of.
            (70.60, 3.0, "Conventions, not laws, which is why each one is a dial."),
            # EXAMPLE -- over the brick's own drawing, saying what to notice in
            # it rather than describing it.
            (
                79.00,
                3.0,
                "Here is the whole package on one page. Follow either lane down.",
            ),
            (85.40, 3.0, "They do not stay apart. Both arrive at the same gate."),
            (
                93.20,
                3.0,
                "A narration and a transcript are one file, so one reader checks both.",
            ),
            # CTA, then the punchline, word for word as every other film ends.
            (
                101.60,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (108.20, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            # The tagline alone: 45 characters cannot share a display line with
            # anything, and alone it wraps at a word boundary instead. See above.
            (1.10, 3.0, "Sprezzature est un moteur d'IA pour le design."),
            (
                5.20,
                3.0,
                "Audio lit la parole dans les deux sens : il transcrit, et il parle.",
            ),
            (11.30, 3.0, "Vos sous-titres sont exacts."),
            (
                14.60,
                3.0,
                "90 caractères à l'écran, une demi-seconde. Personne ne lit ça.",
            ),
            (
                21.00,
                3.0,
                "Retournez-le. Une page qui se lit à voix haute surligne la mauvaise ligne.",
            ),
            (
                29.80,
                3.0,
                "Une modalité, lue dans les deux sens, et rien ne quitte votre machine.",
            ),
            (
                35.60,
                3.0,
                "Du son vers le texte. Ce qui a été dit, par qui, dans quelle langue.",
            ),
            (41.40, 3.0, "Du texte vers le son : un WAV, et un WebVTT posé à côté."),
            (
                46.00,
                3.0,
                "La même piste minutée dans les deux cas, pour qu'une page suive la lecture.",
            ),
            (
                53.00,
                3.0,
                "Ces seuils ne sont pas des nombres que quelqu'un a trouvés jolis.",
            ),
            (
                58.40,
                3.0,
                "Ils ont un éditeur, nommé dans le code : le guide de sous-titrage de Netflix.",
            ),
            (64.20, 3.0, "17 caractères par seconde au plus. 42 par ligne, 2 lignes."),
            (
                70.60,
                3.0,
                "Des conventions, pas des lois : chacune est donc un réglage.",
            ),
            (
                79.20,
                3.0,
                "Voici tout le paquet sur une page. Descendez une voie, puis l'autre.",
            ),
            (
                86.00,
                3.0,
                "Elles ne restent pas séparées : les deux arrivent au même contrôle.",
            ),
            (
                93.40,
                3.0,
                "Narration ou transcription : un seul fichier, un seul contrôle.",
            ),
            (
                101.60,
                3.0,
                "Passez sur sprezzature.ai, et mettez une étoile GitHub si ça le mérite.",
            ),
            (108.00, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "cli-gui": {
        "en": [
            # what
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. Cli-gui turns a command line into a form.",
            ),
            (
                6.60,
                3.0,
                "It reads your tool's own parser. One page, a field for every flag.",
            ),
            # problem
            (
                11.80,
                3.0,
                "Your colleague needs this tool. They will not open a terminal.",
            ),
            (17.00, 3.0, "Not that they cannot. 7 flags in order is not an interface."),
            (22.40, 3.0, "So you build the form by hand. Then the tool grows a flag."),
            # solution
            (
                29.20,
                3.0,
                "So the command writes its own page. Options become fields, choices a list.",
            ),
            (
                35.60,
                3.0,
                "Required stays required. Every default is already in its box.",
            ),
            (
                42.40,
                3.0,
                "The page runs nothing. Your browser assembles the exact line.",
            ),
            # magic
            (
                50.80,
                3.0,
                "It reads the parser your tool built. Not prose about that parser.",
            ),
            (
                56.40,
                3.0,
                "argparse and Click are walked directly; a Typer application is already Click.",
            ),
            (
                62.00,
                3.0,
                "What it cannot import, it reads off that tool's own help screen.",
            ),
            (67.60, 3.0, "A page that silently drops a flag looks entirely correct."),
            (
                73.20,
                3.0,
                "So it checks the page against the parser. Each rule names what you lose.",
            ),
            # example
            (
                81.00,
                3.0,
                "This is docker. Written in Go, and not importable from Python.",
            ),
            (
                87.00,
                3.0,
                "Its help screen came out as 57 sections and 1,307 form fields, in one pass.",
            ),
            (93.00, 3.0, "And git comes out empty. Its section titles are prose."),
            # cta
            (
                102.60,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (109.60, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            # what
            (1.10, 3.0, "Sprezzature est un moteur d'IA pour le design."),
            (
                6.60,
                3.0,
                "Cli-gui fait d'une commande un formulaire, un champ par drapeau.",
            ),
            # problem
            (
                11.80,
                3.0,
                "Votre collègue a besoin de cet outil. Il n'ouvrira pas de terminal.",
            ),
            (
                17.00,
                3.0,
                "Ce n'est pas qu'il ne sait pas. 7 drapeaux ne sont pas une interface.",
            ),
            (
                22.40,
                3.0,
                "Alors vous bricolez le formulaire. Puis l'outil gagne un drapeau.",
            ),
            # solution
            (
                29.20,
                3.0,
                "La commande engendre donc sa propre page. Les options deviennent des champs.",
            ),
            (
                35.60,
                3.0,
                "L'obligatoire reste obligatoire. Chaque défaut est déjà dans sa case.",
            ),
            (
                42.40,
                3.0,
                "La page n'exécute rien. Votre navigateur assemble la ligne exacte.",
            ),
            # magic
            (
                50.80,
                3.0,
                "Elle lit l'analyseur de votre outil. Pas un texte qui le décrit.",
            ),
            (
                56.40,
                3.0,
                "argparse et Click sont lus directement. Une application Typer est déjà du Click.",
            ),
            (
                62.00,
                3.0,
                "Ce qu'elle ne peut pas importer, elle le lit sur l'écran d'aide de l'outil.",
            ),
            (
                67.60,
                3.0,
                "Une page qui laisse tomber un drapeau en silence a l'air parfaitement correcte.",
            ),
            (
                73.20,
                3.0,
                "Elle compare donc la page à l'analyseur. Chaque règle nomme ce qu'on perd.",
            ),
            # example
            (
                81.00,
                3.0,
                "Voici docker. Écrit en Go, et impossible à importer depuis Python.",
            ),
            (
                87.00,
                3.0,
                "Son écran d'aide a donné 57 sections et 1 307 champs, en une seule passe.",
            ),
            (93.00, 3.0, "Et git ne donne rien. Ses titres de sections sont en prose."),
            # cta
            (102.00, 3.0, "Passez sur sprezzature.ai,"),
            (105.60, 3.0, "et mettez une étoile GitHub si ça le mérite."),
            (109.80, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "ui": {
        "en": [
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. UI does the half a command can do.",
            ),
            (
                6.80,
                3.0,
                "It finds your translatable sentences. Then it writes the catalogue.",
            ),
            (
                12.60,
                3.0,
                "A sentence written into a template costs nothing on the day you write it.",
            ),
            (18.40, 3.0, "It costs a week the day somebody needs a second language."),
            (
                23.40,
                3.0,
                "And prompts are language too. A missing one, the model answers.",
            ),
            (
                30.20,
                3.0,
                "It looks for 2 shapes and names them. Not for every literal.",
            ),
            (
                36.00,
                3.0,
                "A locale table living in JavaScript. A model prompt inlined in Python.",
            ),
            (
                41.80,
                3.0,
                "Any finding and it returns one. That is what makes it a pre-commit hook.",
            ),
            (
                47.60,
                3.0,
                "Only you know which id that line wants. So it stops, as gettext does.",
            ),
            (
                53.20,
                3.0,
                "Now the part you would not guess. A prompt is not an interface label.",
            ),
            (
                58.80,
                3.0,
                "It has one language it was tested in, and the catalogue declares it.",
            ),
            (
                65.00,
                3.0,
                "A locale with no entry falls back to it. Never to the message id.",
            ),
            (
                71.00,
                3.0,
                "Nobody published that rule. The package has a test that measured it.",
            ),
            (
                80.20,
                3.0,
                "Here is the file it writes. Interface labels on top, prompts below.",
            ),
            (
                86.60,
                3.0,
                "Both kinds in one file. A screen and a prompt disagreeing is a silent bug.",
            ),
            (
                93.40,
                3.0,
                "At the bottom, one key: validated. No label above it needs that.",
            ),
            (
                103.40,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (110.00, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            (1.10, 3.0, "Sprezzature est un moteur d'IA pour le design."),
            (
                6.80,
                3.0,
                "UI fait la moitié mécanique : trouver vos phrases et les ranger.",
            ),
            (
                12.60,
                3.0,
                "Une phrase écrite à même le gabarit. Aujourd'hui, elle ne coûte rien.",
            ),
            (18.40, 3.0, "Elle coûte une semaine le jour de la deuxième langue."),
            (
                23.40,
                3.0,
                "Les prompts aussi sont de la langue. Un manque, le modèle répond.",
            ),
            (
                30.20,
                3.0,
                "Il cherche 2 formes et les nomme. Pas toute chaîne de l'arbre.",
            ),
            (
                36.00,
                3.0,
                "Une table de langues dans le JavaScript. Un prompt en dur en Python.",
            ),
            (
                41.80,
                3.0,
                "Un constat et il sort en un. Voilà ce qui en fait un crochet.",
            ),
            (
                47.60,
                3.0,
                "Vous seul savez quel identifiant choisir. Comme gettext, il s'arrête.",
            ),
            (
                53.20,
                3.0,
                "Vient ce qu'on ne devinerait pas. Un prompt n'est pas un libellé.",
            ),
            (
                58.80,
                3.0,
                "Il a une langue, celle où on l'a éprouvé. Le catalogue la nomme.",
            ),
            (
                65.00,
                3.0,
                "Une locale sans entrée retombe dessus. Jamais sur l'identifiant.",
            ),
            (
                71.00,
                3.0,
                "Personne n'avait publié cette règle, alors un test du paquet l'a mesurée.",
            ),
            (
                80.20,
                3.0,
                "Voici le fichier qu'il écrit. Les libellés en haut, les prompts en bas.",
            ),
            (
                86.60,
                3.0,
                "Écran et prompt dans un seul fichier, où un désaccord se verrait.",
            ),
            (
                93.40,
                3.0,
                "En bas, une clé : validated. Aucun libellé au-dessus n'en a besoin.",
            ),
            (
                103.40,
                3.0,
                "Passez sur sprezzature.ai. Mettez une étoile GitHub si ça le mérite.",
            ),
            (110.00, 3.0, "Faites, auditez et regardez !"),
        ],
    },
    "video": {
        "en": [
            (
                1.10,
                3.0,
                "Sprezzature is an AI engine for Design. Video audits what a film says.",
            ),
            (
                6.30,
                3.0,
                "Every number a film shows, held against the code that decides it.",
            ),
            (10.20, 3.0, "This suite told viewers it had 127 chart kinds. It had 167."),
            (
                15.00,
                3.0,
                "Prose in a README gets re-read. A number in a keyframe does not.",
            ),
            (
                20.40,
                3.0,
                "Months of it, baked into every cut, with nothing anywhere watching.",
            ),
            (
                27.60,
                3.0,
                "So the claims moved out of the film, into a file that sits beside it.",
            ),
            (
                32.60,
                3.0,
                "A claim is a pair. The sentence on screen. The file that settles it.",
            ),
            (
                37.60,
                3.0,
                "Verify reads that file. It says whether the line is still true.",
            ),
            (
                42.60,
                3.0,
                "If the file has moved, the check fails. It never quietly passes.",
            ),
            (50.60, 3.0, "The dangerous number is the one nobody declared."),
            (
                54.50,
                3.0,
                "A declared one names a file. A number on screen names nothing.",
            ),
            (
                59.90,
                3.0,
                "So the scan reads the composition itself, for numbers no claim covers.",
            ),
            (
                65.60,
                3.0,
                "The source is this repository's history, where 127 survived for months.",
            ),
            (76.50, 3.0, "Now point that scan at this film."),
            (
                80.50,
                3.0,
                "The declared ones come off the code. One number is left over.",
            ),
            (93.50, 3.0, "The only number it cannot declare is the one it is about."),
            (
                101.50,
                3.0,
                "Go to sprezzature.ai, and drop a GitHub star if it deserves it.",
            ),
            (107.00, 3.0, "Make it, audit it, take a look at it."),
        ],
        "fr": [
            (1.10, 3.0, "Sprezzature est un moteur d'IA pour le design."),
            (4.80, 3.0, "Video lit un film. Chaque chiffre y est tenu contre le code."),
            (
                10.20,
                3.0,
                "Ici, 127 types de graphiques annoncés, quand le catalogue en comptait 167.",
            ),
            (
                15.60,
                3.0,
                "Un texte de README se relit, un nombre cuit dans une image clé jamais.",
            ),
            (20.60, 3.0, "Des mois comme ça. Rien, nulle part, ne le relisait."),
            (
                27.60,
                3.0,
                "Les affirmations sont sorties du film. Elles vivent dans un fichier à côté.",
            ),
            (
                33.00,
                3.0,
                "Une affirmation est une paire : le texte, puis le code qui tranche.",
            ),
            (38.00, 3.0, "Verify lit ce fichier et dit si la ligne est encore vraie."),
            (
                43.00,
                3.0,
                "Si le fichier a bougé, le contrôle échoue au lieu de passer.",
            ),
            (
                50.60,
                3.0,
                "Le nombre dangereux existe. C'est celui que personne n'a déclaré.",
            ),
            (
                55.20,
                3.0,
                "Un nombre déclaré nomme un fichier, celui qui paraît seul n'a rien.",
            ),
            (
                60.00,
                3.0,
                "Le scan lit donc la composition. Il relève ce que rien ne couvre.",
            ),
            (
                65.60,
                3.0,
                "La source est l'historique de ce dépôt. 127 y a survécu des mois.",
            ),
            (76.50, 3.0, "Pointez ce scan sur ce film. Les déclarés viennent du code."),
            (81.50, 3.0, "Il en reste un : 127, cité ici exprès."),
            (93.50, 3.0, "Un seul nombre résiste. C'est celui dont le film parle."),
            (
                101.50,
                3.0,
                "Passez sur sprezzature.ai, et mettez une étoile GitHub si ça le mérite.",
            ),
            (107.00, 3.0, "Faites, auditez et regardez !"),
        ],
    },
}

#: The widest a caption line may be, from the Netflix Timed Text Style Guide,
#: which is the same source `sprezzature-audio-audit` measures against and the
#: same number the `audio` film puts on screen.
#:
#: It was 58 here until 2026-10-29, sourced to nothing, and it did not matter
#: what it was: `cues()` below is the only thing that reads it, and `cues()`
#: stopped being called on 2026-10-26 when the narration began writing its own
#: WebVTT. The cue text became the script line, unwrapped, and the shipped
#: tracks went to 90 characters.
#:
#: Measured the morning this was fixed: all 22 tracks failed the suite's own
#: auditor, 184 cues and 287 findings, 177 of them a line over budget. A limit
#: nobody applies is not a limit, and the loudest version of that defect is a
#: suite that ships the auditor, says the number on screen, and breaks it.
LINE_LIMIT = 42

#: Two display lines per cue, the same guide's ceiling. Past that a caption
#: covers the picture it is captioning.
MAX_LINES = 2

#: Characters a second to aim for, under the 17 the guide sets and the suite's
#: auditor enforces.
#:
#: Aiming *at* 17 does not work, and the reason is mechanical rather than
#: editorial. A cue's end time is written to the millisecond and truncated, so
#: a cue laid out to read at exactly 17.000 characters a second comes back from
#: the file at 17.0-and-a-bit and the audit calls it. Measured: targeting 17
#: left 23 of the 27 fast cues still failing; targeting 16 left none.
READING_TARGET_CPS = 16.0

#: Longest a cue may hold the screen, a millisecond under the guide's 7s.
#:
#: Same mechanism, same reason to stop short: one cue landed at exactly 7.000s
#: and `duration > max_seconds` is a strict comparison on a truncated number.
ON_SCREEN_MAX_SECONDS = 6.999

# Punctuation keeps its place on the left of a break; a connector word moves to
# the right, so neither half of a split caption reads as a fragment.
AFTER = (". ", ", ", " ; ", " : ", ": ", " — ")
BEFORE = (" and ", " et ", " puis ", " then ", " so ", " alors ")


def stamp(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def split_line(text: str) -> tuple[str, str]:
    """Break one line in two, at the best place it offers.

    A break at punctuation reads better than a break between two arbitrary
    words, so those candidates are tried first. They are not tried *blindly*,
    and that is the repair of 2026-10-29: the nicest-looking cut is worthless
    if it leaves a half nobody can fit on screen.

    The French call to action is the case that found it. "Passez sur
    sprezzature.ai, et mettez une étoile GitHub si ça le mérite." has a comma
    at 25, which is the only punctuation it offers, so the old rule took it
    and handed back 26 and 44 characters. The right half is over budget, the
    cue is a finding, and the break looked deliberate. Splitting the same line
    between words gives 35 and 35, which is uglier to describe and correct on
    screen, in all eleven French films.

    So punctuation wins only when **both** halves fit. Otherwise the word
    split below decides, which is the rule that was always there and was
    reachable only when a line had no punctuation at all.
    """
    mid = len(text) / 2
    best = fitting = None
    for seps, keep_left in ((AFTER, True), (BEFORE, False)):
        for sep in seps:
            i = text.find(sep)
            while i != -1:
                cut = i + len(sep.rstrip()) if keep_left else i
                if 14 < cut < len(text) - 14:
                    left, right = text[:cut].strip(), text[cut:].strip()
                    d = abs(cut - mid)
                    if best is None or d < best[0]:
                        best = (d, left, right)
                    if max(len(left), len(right)) <= LINE_LIMIT and (
                        fitting is None or d < fitting[0]
                    ):
                        fitting = (d, left, right)
                i = text.find(sep, i + 1)
    if fitting:
        return fitting[1], fitting[2]
    # No punctuation cut leaves two readable halves. Fall through to the word
    # split rather than return the least-bad one: a balanced break between
    # words is what the budget actually asks for.
    # The most balanced break between two words, rather than the first one
    # past the midpoint.
    #
    # The old rule took the word that *crossed* the middle and kept it on the
    # left, which is a half-word of overshoot every time and sometimes much
    # more. "Sprezzature est un moteur d'IA pour le design. Figures dessine le
    # bon graphique." crossed at "design." and came back as 46 and 33: the
    # left half over budget, the right half with room to spare, and 80
    # characters that fit comfortably in two lines of 42 reported as a
    # finding. Breaking one word earlier gives 38 and 41.
    #
    # Balance is the right objective because the budget is per *line*: what
    # costs a reader is the longest half, so the split that minimises it is
    # the split that fits whenever fitting is possible at all.
    words = text.split()
    if len(words) > 1:

        def halves(k: int) -> tuple[str, str]:
            return " ".join(words[:k]), " ".join(words[k:])

        k = min(range(1, len(words)), key=lambda k: max(len(h) for h in halves(k)))
        return halves(k)
    if best:
        return best[1], best[2]
    return text, ""


def wrap_cue(text: str) -> str:
    """One cue's text, broken onto at most :data:`MAX_LINES` display lines.

    A newline inside a cue is what WebVTT gives you for "break here": the
    timings do not move, the words do not change, and the player stops
    choosing its own break. That is the whole repair, and it is deliberately
    the smallest one that works: re-timing to split a long line into two cues
    would need the audio measured again, and the words are not the problem.

    Returns the text unchanged when it already fits, so a short line never
    grows a newline it did not need.

    Why this stops at two lines, when the brick does not
    -----------------------------------------------------
    `sprezzature_video.captions.split_to_fit` recuts until every piece is
    inside the budget, however many pieces that takes, and it exists because
    `split_line` below cuts exactly **once**: a line of 158 characters becomes
    two of 79, which is still over budget and looks repaired. Measured over
    the eleven films' 218 narration lines, lowering the limit alone moved the
    out-of-budget share from 41 % to 30 % and left the longest cue at 117.

    Here the ceiling is two display lines, because this path cannot make more
    cues: a third line would have to be timed, and the timings come from
    measured audio. So a sentence that needs three lines is not a wrapping
    problem at all, it is a sentence to rewrite, and :func:`over_budget` says
    so instead of hiding it under a break the guide forbids.
    """
    if len(text) <= LINE_LIMIT:
        return text
    a, b = split_line(text)
    if not b:
        return text
    return f"{a}\n{b}"


def over_budget(text: str) -> list[str]:
    """The display lines of a wrapped cue that are still too wide.

    Empty means the cue fits. A non-empty answer is a fact about the *script*,
    not about the wrapping: two breaks cannot rescue a sentence that needs
    three, and the repair is to write a shorter sentence.
    """
    lines = wrap_cue(text).split("\n")
    too_wide = [line for line in lines if len(line) > LINE_LIMIT]
    if len(lines) > MAX_LINES:
        too_wide.append(f"{len(lines)} display lines, over {MAX_LINES}")
    return too_wide


def timed_cues(texts, times):
    """The film's cues: wrapped to the budget, and timed so they can be read.

    Replaces a `cues()` that nothing had called since 2026-10-26 — the dead
    function that held the unapplied :data:`LINE_LIMIT` this file's comments
    are about. It is written here rather than in the narration script because
    it is one rule with two callers: the script that narrates a film, and the
    script that re-emits an existing track without re-narrating it.

    Parameters
    ----------
    texts : list of str
        One narration line per cue, as spoken.
    times : list of tuple of float
        `(start, end)` of each line's speech, on the film's clock.

    Returns
    -------
    list of sprezzature_audio.Cue
        Ready for :func:`render_cues`.

    The two repairs this carries
    ----------------------------
    **The break survives the writer.** `wrap_cue` has put a newline at 42
    characters since 2026-10-29 and the shipped tracks still measured 90, for a
    reason no reading of this file could show: the cues went out through
    `speaker_helper.cues_to_vtt`, which collapses the payload with
    `" ".join(text.split())` — a line meant for "a blank line ends a cue"
    which also eats the single newline that *is* how WebVTT says "break
    here". Two lines of 39 and 41 came back as one of 81. So the cues are
    written by `sprezzature_audio`, which is the library whose auditor the
    films quote on screen: the writer and the audit now come from the same
    place, which is the property that was missing.

    **A cue may hold the screen into the pause that follows it.** The reading
    speed of a cue is its characters over its *on-screen* time, and on-screen
    time is free where the voice is silent. Extending a cue up to the next
    one's start — never over it, never past
    :data:`ON_SCREEN_MAX_SECONDS` — brought all 27 of the fast cues inside the
    ceiling with the audio untouched. That is the standard practice and it is
    also the only repair available here: shortening the sentence would mean
    speaking it again.

    The same bound fixes the opposite fault. A cue that had swallowed a long
    silence was holding the screen for 22.4 seconds — in `audio.fr`, on the
    line "90 caractères à l'écran, une demi-seconde. Personne ne lit ça."
    """
    from sprezzature_audio import Cue

    out = []
    for index, (text, (start, end)) in enumerate(zip(texts, times)):
        wrapped = wrap_cue(" ".join(text.split()))
        characters = len(" ".join(wrapped.split()))
        # Never past the next cue: two cues on screen at once is a finding of
        # its own, and the player's answer to it is undefined.
        ceiling = start + ON_SCREEN_MAX_SECONDS
        if index + 1 < len(times):
            ceiling = min(ceiling, times[index + 1][0])
        readable = start + characters / READING_TARGET_CPS
        stop = min(max(end, readable), ceiling)
        out.append(
            Cue(
                start=start,
                end=max(stop, start + 0.001),
                text=wrapped,
                # The segment index, which is what lets the read-along
                # highlight a block without matching on its text.
                identifier=str(index),
            )
        )
    return out


def render_cues(cue_list) -> str:
    """One film's WebVTT, through the suite's own writer.

    A thin wrapper so no caller has to remember *which* writer: see
    :func:`timed_cues` for what happened when the cues went out through a
    different library's.
    """
    from sprezzature_audio import write_vtt

    return write_vtt(cue_list)


def main() -> int:
    """Refuses to run, and says what replaced it.

    This used to write every ``web/video/*.vtt`` from the table above: it
    measured each line's WAV with ffprobe, split long lines at a list of
    separators, and laid the cues out itself. Since 2026-10-26 the cues come
    from ``narrate_films.py``, which asks ``sprezzature-audio`` for the
    reading and gets the audio and the timed track back together — one
    timeline, and a library that refuses a result whose timeline disagrees
    with its own audio.

    Left executable it would still work, and that is the danger: run after a
    narration it would overwrite correct cues with cues derived from a
    different arithmetic, and the only symptom would be captions drifting
    from the voice. So it stops, and names its successor.

    The table itself stays. It is the narration *text*, in both languages,
    and it is what ``narrate_films.py`` reads.
    """
    sys.stderr.write(
        "make_captions.py no longer writes the cues.\n"
        "The voice and its WebVTT come from sprezzature-audio together:\n"
        "    python3 narrate_films.py\n"
        "This file is still the narration text, which that script reads.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

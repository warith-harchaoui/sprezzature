"""
The French of the films: one table, and a list of what stays in English.

Why a table and not a second FILMS
----------------------------------
The obvious shape is a French copy of ``build_films.FILMS`` — and it is the
wrong one. A film spec is mostly timing: scene starts, reveal times snapped to
the beat grid, durations measured off the voice. None of that is language. A
duplicated spec would duplicate the timing too, and the two copies would drift
in exactly the way that is hardest to notice: a scene moved in one language
and not the other, caught only by somebody watching both cuts end to end.

So the spec stays single and this file translates its strings on the way out.
``translate(spec)`` walks a spec and returns a copy with every user-visible
string replaced; everything else — every number — is shared by construction.

Why `KEEP` exists
-----------------
Half of what is on screen is not English. ``img-missing-alt`` is a rule id,
``af_heart`` is a voice id, ``whisper.cpp`` is a program, ``Fitts`` is a
person. Translating any of them would be wrong, and *silently* leaving them
alone would be indistinguishable from forgetting them.

So the choice is written down. Every string on screen is in ``FR`` or in
``KEEP``, and :func:`translate` raises on one that is in neither. A new line
in a film cannot reach the French cut untranslated — it stops the build and
names itself.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: Strings that are identical in both cuts because they are not prose: rule
#: ids, command names, voice ids, file formats, people, papers, products.
#: Listed rather than detected — "Flow" is a chart category and translates,
#: "Gestalt" is a word French borrowed and does not, and no rule separates
#: them.
KEEP: frozenset[str] = frozenset({
    # Papers, standards, projections, products
    "Machado 2009", "Gestalt", "Equal Earth", "W3C WebVTT", "Schema.org",
    "OKLCH", "OKLab", "Ottosson 2020", "IEEE TVCG", "CVD_MATRICES",
    "WCAG 2.x", "Open Graph, Twitter Card, Schema.org",
    # The nine publish tools, which are command names
    "lint", "html", "icons", "indexes", "meta", "plain", "changelog",
    "narrate", "readalong",
    # Models, engines, voices, formats
    "whisper.cpp", "large-v3-turbo", "NeMo Sortformer", "TitaNet", "RTTM",
    "WebVTT", "Kokoro", "af_heart",
    # Code and identifiers
    "argparse, Click, Typer", "schema.py", "--fix", "TRACKED", "DERIVED",
    "SOLE",
    # The eight laws the auditor checks, by the names they are cited under
    "Hick", "Miller", "Fitts", "Jakob", "Tesler",
    # Accessibility rule ids
    "media-autoplay-sound", "video-missing-captions", "media-missing-controls",
    "img-missing-alt", "input-missing-label", "div-onclick",
    "tabindex-positive", "heading-skip", "dialog-missing-close",
    "color-only-state", "motion-no-reduce-guard",
    # The suite's own name, and the package each film is about
    "Sprezzature",
    "Sprezzature · colors", "Sprezzature · figures", "Sprezzature · publish",
    "Sprezzature · audio", "Sprezzature · cli-gui", "Sprezzature · ui",
    "Sprezzature · video", "Sprezzature · maps", "Sprezzature · ux-laws",
    "Sprezzature · accessibility",
})

#: English on screen → French on screen.
FR: dict[str, str] = {
    # ----------------------------------------------------------- the suite
    "Design is know-how. Most of it is already written down.":
        "Le design est un savoir-faire. L'essentiel est déjà écrit.",
    "Written down, by somebody else": "Écrit par quelqu'un d'autre",
    "Yablonski, the W3C, a 2009 IEEE paper, a 2018 projection — read, then written into the tools.":
        "Yablonski, le W3C, un article IEEE de 2009, une projection de 2018 — lus, puis écrits dans les outils.",
    "30 Laws of UX": "30 lois d'UX",
    "WCAG contrast": "contraste WCAG",
    "Turned into something that runs": "Transformé en quelque chose qui tourne",
    "A flow, a map, a calendar, a matrix — and the rule each one was checked against.":
        "Un flux, une carte, un calendrier, une matrice — et la règle qui a vérifié chacun.",
    "The same rules, both directions": "Les mêmes règles, dans les deux sens",
    "167 chart kinds · 20 accessibility rules · 30 laws of UX · nothing has to leave the machine.":
        "167 types de graphiques · 20 règles d'accessibilité · 30 lois d'UX · rien ne quitte la machine.",
    "Make": "Fabriquer",
    "a page, a figure, a map, a palette": "une page, une figure, une carte",
    "Audit": "Auditer",
    "the same rules, against what you made": "les mêmes règles, contre votre travail",
    "No reference does this": "Aucune référence ne fait ça",
    "Qwen3-VL through Ollama writes the alt text, drafts the captions, and critiques the figure. One model, offline.":
        "Qwen3-VL via Ollama écrit le texte alternatif, rédige les légendes et critique la figure. Un seul modèle, hors ligne.",
    "render": "dessiner",
    "look": "regarder",
    "fix the source": "corriger la source",
    "again": "recommencer",
    "What that adds up to": "Ce que ça fait au total",
    "One implementation underneath — deduplication that changes a single pixel is rejected.":
        "Une seule implémentation dessous — une factorisation qui change un pixel est refusée.",
    "Ten packages": "Dix paquets",
    "ui, cli-gui, publish, accessibility, colors, audio, ux-laws, figures, maps, video":
        "ui, cli-gui, publish, accessibility, colors, audio, ux-laws, figures, maps, video",
    "Five surfaces each": "Cinq surfaces chacun",
    "library, CLI, HTTP API, MCP tools, skill":
        "bibliothèque, CLI, API, MCP, skill",
    "Make it. Audit it. Then look at it.":
        "Fabriquer. Auditer. Puis regarder.",

    # --------------------------------------------------------------- colors
    "Light grey on white reads fine. To you, indoors.":
        "Du gris clair sur blanc se lit bien. Pour vous, à l'intérieur.",
    "The same button, two readers": "Le même bouton, deux lecteurs",
    "It reads fine to whoever picked the colour. That is the problem.":
        "Ça se lit bien pour qui a choisi la couleur. C'est tout le problème.",
    "Low vision": "Malvoyance",
    "the text and the background are too close":
        "le texte et le fond sont trop proches",
    "Bright sunlight": "Plein soleil",
    "a phone screen loses the difference":
        "un écran de téléphone perd la différence",
    "About one man in twelve sees red and green as the same bar.":
        "Environ un homme sur douze voit le rouge et le vert comme une seule barre.",
    "Rendered for those eyes": "Rendu pour ces yeux-là",
    "If the story survives grey, it survives everyone.":
        "Si l'histoire survit au gris, elle survit à tout le monde.",
    "protanopia": "protanopie",
    "deuteranopia": "deutéranopie",
    "tritanopia": "tritanopie",
    "grayscale": "niveaux de gris",
    "None of this was invented here": "Rien de tout ça n'a été inventé ici",
    "The thresholds are the standard's, the matrices a paper's, the lightness axis Ottosson's.":
        "Les seuils sont ceux de la norme, les matrices celles d'un article, l'axe de clarté celui d'Ottosson.",
    "2.4-gamma luminance": "luminance gamma 2,4",
    "The same know-how, both directions": "Le même savoir-faire, dans les deux sens",
    "One source for the colours, instead of each project copying hex codes.":
        "Une seule source pour les couleurs, au lieu de codes hexa recopiés par chaque projet.",
    "every text-on-background pair, and a fix":
        "chaque paire texte-sur-fond",
    "the approved palette, as a Tailwind config":
        "la palette validée, en config Tailwind",
    "Pure standard library. No network. No model.":
        "Bibliothèque standard pure. Pas de réseau. Pas de modèle.",

    # -------------------------------------------------------------- figures
    "One hundred and sixty-seven kinds of chart. Every one hand-authored.":
        "Cent soixante-sept types de graphiques. Tous écrits à la main.",
    "No charting library underneath": "Aucune bibliothèque de tracé en dessous",
    "Each generator writes the SVG markup itself, so the shapes are not a library's defaults.":
        "Chaque générateur écrit le SVG lui-même, donc les formes ne sont pas les défauts d'une bibliothèque.",
    "Fifty-two categories": "Cinquante-deux catégories",
    "Wind roses and wind barbs. ROC curves, calibration plots, confusion matrices, Kaplan–Meier.":
        "Roses des vents, courbes ROC, calibration, matrices de confusion, Kaplan–Meier.",
    "Comparison": "Comparaison",
    "Distribution": "Distribution",
    "Flow": "Flux",
    "Geospatial": "Géospatial",
    "Hierarchy": "Hiérarchie",
    "Matrix": "Matrice",
    "Meteorology": "Météorologie",
    "Model evaluation": "Évaluation de modèles",
    "The deliverable is the vector": "Le livrable est le vectoriel",
    "Explicit width, height and a matching viewBox — the text stays selectable at any zoom.":
        "Largeur, hauteur et viewBox explicites — le texte reste sélectionnable à tout zoom.",
    "A PNG is an export, for places that cannot take vector art.":
        "Un PNG est un export, pour les endroits qui refusent le vectoriel.",
    "A model reads the figure, names what is wrong, and the source is what gets fixed. Nothing leaves the machine.":
        "Un modèle lit la figure, nomme ce qui cloche, et c'est la source qu'on corrige. Rien ne quitte la machine.",

    # -------------------------------------------------------------- publish
    "A document, becoming a site.": "Un document, qui devient un site.",
    "Nine tools, one document": "Neuf outils, un document",
    "The linter is standard library only, runs in milliseconds, and fixes what has exactly one fix.":
        "Le linter n'utilise que la bibliothèque standard, tourne en millisecondes, et corrige l'univoque.",
    "What a page owes its readers": "Ce qu'une page doit à ses lecteurs",
    # Filenames, joined by a word. The filenames stay; the word was the one
    # piece of English still standing on a French frame.
    "robots.txt, sitemap.xml, Atom, humans.txt — and llms.txt, llms-full.txt":
        "robots.txt, sitemap.xml, Atom, humans.txt — et llms.txt, llms-full.txt",
    "One logo becomes the favicon, the app icons, the PWA icons, and the <head> that points at them.":
        "Un logo devient le favicon, les icônes d'app, les icônes PWA, et le <head> qui les désigne.",
    "And what it rewrites": "Et ce qu'il réécrit",
    "Simpler language is not the same as a vaguer one. The nouns you chose survive the rewrite.":
        "Une langue plus simple n'est pas une langue plus vague. Les noms que vous avez choisis survivent.",
    "the same page at a target reading grade, keeping the terms you name":
        "la même page à un niveau de lecture visé, en gardant vos termes",
    "a CHANGELOG becomes dated posts": "un CHANGELOG devient des billets datés",
    "Then readalong binds the narration to the page.":
        "Puis readalong lie la narration à la page.",
    "Two packages, one reading": "Deux paquets, une seule lecture",
    "A boundary drawn on purpose: the heavy imports stay out of the tool you run on every commit.":
        "Une frontière tracée exprès : les imports lourds restent hors de l'outil lancé à chaque commit.",
    "The voice": "La voix",
    "lives in sprezzature-audio": "vit dans sprezzature-audio",
    "This package": "Ce paquet",
    "never imports a model": "n'importe jamais de modèle",
    "The sentence being spoken is the sentence lit up.":
        "La phrase prononcée est la phrase allumée.",

    # ---------------------------------------------------------------- audio
    "One modality, read in both directions.":
        "Une seule modalité, lue dans les deux sens.",
    "The two directions": "Les deux sens",
    "The package's own framing, and the reason both live in one place instead of two.":
        "La formule du paquet lui-même, et la raison pour laquelle les deux tiennent en un seul endroit.",
    "Captions": "Sous-titres",
    "sound becomes timed text": "le son devient un texte minuté",
    "Narration": "Narration",
    "text becomes timed sound": "le texte devient un son minuté",
    "The models, named": "Les modèles, nommés",
    "Who spoke when, up to four speakers, in the format speech research already reads.":
        "Qui a parlé quand, jusqu'à quatre locuteurs, au format que la recherche sur la parole lit déjà.",
    "Narration lands as two files": "La narration arrive en deux fichiers",
    "Which is what lets a page follow the reading, sentence by sentence, without a second pass.":
        "C'est ce qui permet à une page de suivre la lecture, phrase après phrase, sans seconde passe.",
    "The WAV": "Le WAV",
    "the voice itself, loudness-normalised": "la voix elle-même, sonie normalisée",
    "The WebVTT": "Le WebVTT",
    "the same words, timed — like a transcript":
        "les mêmes mots, minutés",
    "And it audits its own output.": "Et il audite sa propre sortie.",
    "What audit_captions measures": "Ce que mesure audit_captions",
    "Measured against the rates a reader can actually keep up with, not against a guess.":
        "Mesuré contre les débits qu'un lecteur suit vraiment, pas contre une estimation.",
    "Per cue": "Par sous-titre",
    "reading speed, line width, duration": "vitesse de lecture, largeur, durée",
    "Across cues": "Entre sous-titres",
    "overlaps, and gaps that read as a dropout":
        "chevauchements, et trous qui passent pour une coupure",
    "A caption track can be present and still be unreadable.":
        "Une piste de sous-titres peut être là et rester illisible.",

    # -------------------------------------------------------------- cli-gui
    "A tool nobody will type, wrapped in a page.":
        "Un outil que personne ne tapera, enveloppé dans une page.",
    "Generated, not written": "Engendré, pas écrit",
    "Flags become fields. Choices become a dropdown. Required stays required.":
        "Les options deviennent des champs. Les choix, une liste. L'obligatoire reste obligatoire.",
    "It does not read the help text. It reads the parser object.":
        "Il ne lit pas le texte d'aide. Il lit l'objet analyseur.",
    "Three adapters, one schema": "Trois adaptateurs, un seul schéma",
    "So the renderer never has to know which framework the command line was written in.":
        "Le rendu n'a donc jamais à savoir dans quel cadre la commande a été écrite.",
    "introspected: fields, defaults, types":
        "introspectés : champs, défauts, types",
    "what every adapter produces, normalised":
        "la sortie de tout adaptateur, normalisée",
    "And when no parser object is reachable, it parses --help.":
        "Et quand aucun analyseur n'est joignable, il lit --help.",
    "Which is how the rest get a form": "C'est ainsi que les autres ont un formulaire",
    "Less exact than introspection, and named as such rather than presented as the same thing.":
        "Moins exact que l'introspection, et nommé comme tel plutôt que présenté pour équivalent.",
    "A subprocess": "Un sous-processus",
    "runs --help and reads what it printed":
        "lance --help et lit ce qu'il a imprimé",
    "A Go or Rust CLI": "Une commande Go ou Rust",
    "covered, without a line of Python in it":
        "couverte, sans une ligne de Python",
    "The page is the deliverable. The command stays the command.":
        "La page est le livrable. La commande reste la commande.",

    # ------------------------------------------------------------------- ui
    "The smallest brick, on purpose.": "La plus petite brique, exprès.",
    "Two halves of one judgement": "Deux moitiés d'un même jugement",
    "Most of it stays prose, because most of it is a decision rather than a check.":
        "L'essentiel reste en prose, parce que l'essentiel est une décision, pas un contrôle.",
    "In prose": "En prose",
    "the three-Roboto rule, the tokens, what an interface has to respect":
        "la règle des trois Roboto, les jetons, ce qu'une interface doit respecter",
    "In code": "En code",
    "the part a machine can carry out": "la part qu'une machine peut exécuter",
    "A hardcoded sentence costs nothing the day it is written.":
        "Une phrase codée en dur ne coûte rien le jour où on l'écrit.",
    "It costs a week the day somebody needs a second language.":
        "Elle coûte une semaine le jour où il faut une deuxième langue.",
    "Where that week actually goes": "Où passe vraiment cette semaine",
    "The mechanised half, and the only one worth mechanising: finding every sentence you forgot.":
        "La moitié mécanisable, et la seule qui vaille : retrouver chaque phrase oubliée.",
    "Scattered": "Éparpillées",
    "JavaScript literals, HTML attributes, prompt templates in Python":
        "littéraux JavaScript, attributs HTML, gabarits de prompt en Python",
    "Extracted": "Extraites",
    "one catalogue, and a page that switches":
        "un catalogue, une page qui bascule",
    "And what ships with it": "Et ce qui est livré avec",
    "Roboto, Roboto Serif, Roboto Mono — vendored, so a page never waits on a font server.":
        "Roboto, Roboto Serif, Roboto Mono — embarquées, donc une page n'attend aucun serveur de fontes.",
    "9 components": "9 composants",
    "9 snippets": "9 extraits",
    "6 font files": "6 fichiers de fonte",
    "a starter page": "une page de départ",
    "design tokens": "jetons de design",
    "theme toggle": "bascule de thème",
    "Taste is written down once, then it is somebody else's too.":
        "Le goût s'écrit une fois, et il devient celui des autres.",

    # ---------------------------------------------------------------- video
    "A film is a claim with a soundtrack.":
        "Un film est une affirmation avec une bande-son.",
    "Two kinds of claim": "Deux sortes d'affirmation",
    "The second kind is the dangerous one, because nobody wrote it down to be checked.":
        "La seconde est la dangereuse : personne ne l'a écrite pour qu'on la vérifie.",
    "Declared": "Déclarée",
    "a sentence, and the code behind it": "une phrase, et le code derrière",
    "Undeclared": "Non déclarée",
    "a number on screen that nothing sourced":
        "un nombre à l'écran que rien ne source",
    "167. 52. 30. 20. Every one of those is checkable.":
        "167. 52. 30. 20. Chacun de ces nombres est vérifiable.",
    "And the assets are ledgered": "Et les ressources sont inventoriées",
    "Three classes, because exactly one of them cannot be got back.":
        "Trois classes, parce qu'une seule ne se récupère pas.",
    "in git, restorable from the repository":
        "dans git, restaurable depuis le dépôt",
    "rebuilt by a script that is in git":
        "reconstruite par un script qui est dans git",
    "the only copy there is": "la seule copie qui existe",
    "A sole copy is the one a cleanup deletes without noticing.":
        "Une copie unique, c'est celle qu'un nettoyage supprime sans s'en apercevoir.",
    "Captions are measured, not guessed": "Les sous-titres sont mesurés, pas devinés",
    "A line that overruns the next one is a caption track nobody can follow.":
        "Une ligne qui déborde sur la suivante est une piste que personne ne peut suivre.",
    "The duration": "La durée",
    "read off the voice file itself": "lue sur le fichier de voix lui-même",
    "The split": "La coupe",
    "at a sentence end, never mid-clause":
        "en fin de phrase, jamais au milieu",
    "Then a poster frame, and a loudness pass.":
        "Puis une image d'affiche, et une passe de sonie.",

    # ----------------------------------------------------------------- maps
    "A column of countries is a map waiting to happen.":
        "Une colonne de pays est une carte qui s'ignore.",
    "Real coastlines, a real projection": "De vraies côtes, une vraie projection",
    "Eight kilometres of relief, the Meseta, the lakes, and the physical base the rest is drawn on.":
        "Huit kilomètres de relief, la Meseta, les lacs, et le socle physique sur lequel on dessine le reste.",
    "The projection is a decision, not a default":
        "La projection est une décision, pas un défaut",
    "Every recipe for flattening the Earth distorts something. This one says which.":
        "Toute façon d'aplatir la Terre déforme quelque chose. Celle-ci dit quoi.",
    "areas stay honest, published 2018": "les aires restent honnêtes, 2018",
    "Lambert conformal conic": "Conique conforme de Lambert",
    "centred on the region you asked for": "centrée sur la région demandée",
    "Who controls what": "Qui contrôle quoi",
    "Zones by category, flashpoints, a contact line, and a scale bar in two units at once.":
        "Des zones par catégorie, des points chauds, une ligne de contact, et une échelle en deux unités.",
    "The density map draws no coastline at all.":
        "La carte de densité ne dessine aucune côte.",
    "And it still reads as land": "Et on y lit quand même une terre",
    "The reader recognises the shape without being shown it.":
        "Le lecteur reconnaît la forme sans qu'on la lui montre.",
    "The land": "La terre",
    "appears because events fell on it":
        "apparaît où des événements sont tombés",
    "The sea": "La mer",
    "stays dark because none did": "reste sombre où il n'en tomba aucun",
    "Natural Earth, GMTED2010, TIGER/Line — every source named.":
        "Natural Earth, GMTED2010, TIGER/Line — chaque source nommée.",

    # -------------------------------------------------------------- ux-laws
    "Nobody says “that violates Hick’s Law”.":
        "Personne ne dit « ça viole la loi de Hick ».",
    "What they say instead": "Ce qu'on dit à la place",
    "A usability finding in plain clothes. The job is to locate it, name it, and make it fixable.":
        "Un constat d'utilisabilité en civil. Le travail : le situer, le nommer, le rendre corrigeable.",
    "“This page is overwhelming”": "« Cette page est écrasante »",
    "too many choices at once": "trop de choix à la fois",
    "“I can never find the button”": "« Je ne trouve jamais le bouton »",
    "no hit area, no focus ring": "ni zone de clic, ni anneau de focus",
    "Thirty laws, curated by Jon Yablonski":
        "Trente lois, réunies par Jon Yablonski",
    "Eight of the thirty are decidable from the source. Those eight are the ones the auditor checks.":
        "Huit des trente se tranchent depuis la source. Ce sont celles que l'auditeur vérifie.",
    "Choice overload": "Surcharge de choix",
    "Selective attention": "Attention sélective",
    "Aesthetic-Usability": "Esthétique-Utilisabilité",
    "What the auditor actually catches": "Ce que l'auditeur attrape vraiment",
    "Mechanical, source-decidable, and fast enough for a pre-commit hook.":
        "Mécanique, décidable depuis la source, et assez rapide pour un crochet de pré-commit.",
    "a control with no 44-pixel hit area":
        "un contrôle sans zone de clic de 44 pixels",
    "an unchunked digit run past seven":
        "des chiffres non groupés au-delà de sept",
    "an interactive element with no focus ring":
        "un interactif sans anneau de focus",
    "It does not judge whether the screen answers the right question.":
        "Il ne juge pas si l'écran répond à la bonne question.",
    "The honest boundary": "La frontière honnête",
    "A fast gate, not a substitute for design review. The repo says so itself.":
        "Une barrière rapide, pas une revue de design. Le dépôt le dit lui-même.",
    "The gate": "La barrière",
    "eight laws, exit 1, every commit": "huit lois, sortie 1, à chaque commit",
    "The human": "L'humain",
    "whether the flow makes sense at all": "si le parcours a du sens, tout court",
    "Thirty laws you can read. Eight a machine can hold you to.":
        "Trente lois à lire. Huit qu'une machine peut vous opposer.",

    # -------------------------------------------------------- accessibility
    "An unmuted autoplay masks a screen reader.":
        "Une lecture automatique non muette couvre un lecteur d'écran.",
    "Three the source can prove on its own":
        "Trois que la source prouve toute seule",
    "No browser. No DOM. Just the markup, read carefully.":
        "Pas de navigateur. Pas de DOM. Juste le balisage, lu attentivement.",
    "WCAG 1.4.2 — it talks over the reader":
        "WCAG 1.4.2 — ça couvre le lecteur",
    "WCAG 1.2.2 — audio with no captions":
        "WCAG 1.2.2 — de l'audio sans sous-titres",
    "WCAG 2.1.1 — no keyboard controls":
        "WCAG 2.1.1 — aucun contrôle au clavier",
    "Twenty rules": "Vingt règles",
    "Each one names the element, the line, and the rule it broke.":
        "Chacune nomme l'élément, la ligne, et la règle enfreinte.",
    "Six of the twenty repair themselves": "Six des vingt se réparent seules",
    "A fix is only automatic where there is exactly one safe repair.":
        "Une correction n'est automatique que là où il n'existe qu'une réparation sûre.",
    "lang detection, redundant aria, tabindex":
        "langue, aria redondant, tabindex",
    "and the rest": "et le reste",
    "reported, never guessed at": "signalé, jamais deviné",
    "And the same rule, pointed the other way, writes the CSS.":
        "Et la même règle, retournée, écrit le CSS.",
    "Audit, then make": "Auditer, puis fabriquer",
    "Ship the fix as a reader-facing toggle, not just a warning.":
        "Livrer la correction comme une bascule pour le lecteur, pas comme un avertissement.",
    "The rule": "La règle",
    "body text with tracking too tight to read":
        "du texte courant à l'interlettrage trop serré",
    "The counterpart": "La contrepartie",
    "CSS at the WCAG 1.4.12 minimums": "du CSS aux minimums WCAG 1.4.12",
    "Standard library only. Exit 1 on any finding.":
        "Bibliothèque standard seule. Sortie 1 à la moindre trouvaille.",
}


class Untranslated(KeyError):
    """A string reached the French cut with no French and no exemption."""


def tr(text: str) -> str:
    """The French of *text*, or *text* when it is deliberately kept."""
    if text in FR:
        return FR[text]
    if text in KEEP:
        return text
    raise Untranslated(
        f"no French for {text!r}. Add it to FR in films_fr.py, or to KEEP if "
        f"it is a rule id, a command name, a product or a person."
    )


#: Assets that have a French twin, and where it lives. A French film is
#: French throughout — a chart whose axis says "Quarter" under a caption that
#: says "trimestre" is exactly the mixture that rule forbids.
#:
#: Only the hand-authored figures are covered. `web/tools/localize_figures.py`
#: writes them for the gallery from one "English": "Français" map, and the
#: films take the gallery's French rather than translating a second time.
#:
#: What is NOT covered, and is visibly English in the French cuts:
#:   * the six situation plates (`maps/situation-*.png`) — their titles and
#:     legends are baked in by `build_situation_examples.py` in
#:     sprezzature-maps, which has no French mode yet;
#:   * the colour-vision frames (`figures/cvd/*.png`) — rendered from the
#:     English `bar-grouped.svg` by that package's `simulate_cvd.py`;
#:   * the two `make-figure` captures — the form shows an English command's
#:     own help text, and no amount of localisation here makes a French CLI.
#: Each is a real gap, named rather than quietly tolerated.
FRENCH_ASSET_DIRS = {
    "figures/": "figures/fr/",
    "maps/": "maps/fr/",
    "shots/": "shots/fr/",
}

#: Assets that are still English inside the French cuts, each with the reason
#: and what would close it. Written down rather than tolerated: an asset
#: carries its own words — an axis label, a map title, a form field — and
#: swapping the caption above it does nothing to those, so "the French film
#: shows an English picture" is a defect that no amount of re-reading the
#: French text will surface.
#:
#: A test pins this set. Add an asset to a film without a French twin and
#: without a line here, and it fails; produce the French twin and the films
#: pick it up, and it fails again until the line is removed. The list can only
#: shrink on purpose.
ENGLISH_IN_FRENCH_CUTS: dict[str, str] = {
    # `maps/density.svg` used to sit here. It left the list the way an entry
    # is supposed to leave it: somebody produced the French twin, the ledger
    # declared it, the films switched on the next build, and the test went
    # red until this line was deleted.
    # Four of the six left on 2026-10-28, and not the way an entry is
    # supposed to leave: the identity card took the maps film's opening slot,
    # the two grids merged into one, and the himalaya / iberia / switzerland
    # / western-europe plates simply stopped being in any film. The gap they
    # named is still open in sprezzature-maps; it is just no longer this
    # repository's gap to carry.
    "maps/situation-ukraine.png":
        "titles and legend baked in by build_situation_examples.py in "
        "sprezzature-maps, which has no French mode",
    # `maps/situation-syria.png` left on 2026-10-30, the same way the four
    # above it did: not because a French twin arrived, but because the
    # rewrite to seven movements dropped the plate from the maps film. The
    # gap is still open in sprezzature-maps, which still has no French mode;
    # it is simply no longer a gap any film here walks into.
    "figures/cvd/00-original.png":
        "rendered from the English bar-grouped.svg by sprezzature-colors' "
        "simulate_cvd.py; a French set needs that script pointed at the "
        "French figure",
    "figures/cvd/01-protanopia.png": "idem",
    "figures/cvd/02-deuteranopia.png": "idem",
    "figures/cvd/03-tritanopia.png": "idem",
    "figures/cvd/04-grayscale.png": "idem",
    "shots/make-figure-list.png":
        "the form shows an English command's own --help; no localisation "
        "here makes a French make-figure",
    "shots/make-figure-render.png": "idem",

    # --- 2026-10-29: the films gained a sixth beat, the finest example each
    # package can show, and six of the eleven had carried no picture at all
    # until then. Most of what it brought in is language-free; what is not is
    # named with the gap it leaves.
    "shots/alt-marie-curie.jpg":
        "a photograph, and a public-domain one: it carries no language, so "
        "there is nothing to localise and no French twin to produce",
    "maps/situation-himalaya.png":
        "titles and legend baked in by build_situation_examples.py in "
        "sprezzature-maps, which has no French mode",
    "maps/situation-iberia.png": "idem",
    "maps/situation-switzerland.png": "idem",
    "maps/choropleth-sequential.svg":
        "the legend names its classification method in English, written by "
        "sprezzature-maps; a French twin needs that label translated at the "
        "source rather than here",
    "figures/kde2d-contour.png":
        "axis labels written by the generator in sprezzature-figures, which "
        "takes no language",
    "figures/surface3d.png": "idem",
    "ux-laws/nav-forty.svg":
        "the plate shows an English nav and the auditor's own English "
        "finding; translating either would mean the picture no longer "
        "matches what the tool printed",
    "ux-laws/nav-seven.svg": "idem",
    "shots/docker-run.png":
        "the form is generated from docker's own --help, which is English; "
        "a French one would mean a French docker",
    "shots/ui-catalogue.png":
        "the catalogue sprezzature-ui-i18n-make actually writes, and the "
        "comments it writes are English; its *content* is already bilingual, "
        "which is the point of the shot. A French twin needs the scaffolder "
        "to emit its own header in French",
}

#: Which assets have a French twin is asked of the **ledger**, not of the
#: asset cache. `_assets/` is gitignored: it is a working cache this machine
#: happens to have filled, and a clean checkout has none of it. The first
#: version of this keyed on `(_assets / twin).is_file()`, which made the
#: French films depend on local state — they used French figures here and
#: would have silently used English ones anywhere else, and the test that
#: was supposed to catch exactly that passed locally and failed in CI.
#:
#: `restore_assets.TRACKED` is in git and says, for every asset, which
#: tracked file it is a copy of. A French twin that is declared there exists
#: for everybody; one that is merely sitting in somebody's cache does not.


#: Which of `restore_assets`' ledgers name assets a French cut may localise.
#:
#: Written out rather than discovered, because the two kinds of ledger are
#: not distinguishable by shape: both map an asset path to a string. The
#: difference is editorial — these hold plates that can have a French twin,
#: and the one below holds files that cannot.
LEDGERS_READ: tuple[str, ...] = (
    "TRACKED",
    "DERIVED_MAPS",
    "DERIVED_SIBLINGS",
    "READALONG",
)

#: And the ledgers deliberately not read, each with the reason. A new ledger
#: in `restore_assets` has to land in one list or the other;
#: `tests/test_every_asset_ledger_reaches_the_french_cut.py` fails until it
#: does, which is the only thing standing between a French plate and a cut
#: that silently shows the English one.
LEDGERS_NOT_READ: dict[str, str] = {
    "SEED_ONLY": "a licensed MP3, three sound effects, a pinned GSAP build and "
    "two files derived from the MP3. None of them carries a word, so none of "
    "them has a French twin to pick up.",
}


def _declared() -> frozenset[str]:
    """Asset paths the ledger declares, cached after the first call."""
    global _DECLARED
    if _DECLARED is None:
        import restore_assets

        # Both ledgers. `TRACKED` holds copies of tracked files; `DERIVED_MAPS`
        # holds the plates a generator produces, which is where the French
        # density plate lives. Reading only the first left the French cut on
        # the English plate while the French one sat in the tree, declared,
        # one dictionary over.
        # `DERIVED_SIBLINGS` joined on 2026-10-29: the audio brick already
        # ships its own diagram in both languages, so the French cut has a
        # twin to pick up and needs no exemption. A ledger read short is how
        # a French plate sits in the tree, declared, and never reaches the
        # film.
        # `READALONG` joined on 2026-10-30, and it is the fourth time this
        # list has been the thing that was wrong. The lesson has stopped
        # being about any one dictionary: every new ledger in
        # `restore_assets` is a ledger this function has to be told about,
        # and nothing fails when it is not. The French cut simply shows the
        # English plate.
        _DECLARED = frozenset(
            path for name in LEDGERS_READ for path in getattr(restore_assets, name, ())
        )
    return _DECLARED


_DECLARED: frozenset[str] | None = None


def localise_asset(src: str) -> str:
    """Where this asset's French twin would live. A pure path mapping.

    Says nothing about whether it has been produced; :func:`french_asset` is
    the one that asks. Kept separate so a test can ask "is there a twin for
    this?" without re-deriving the naming scheme.
    """
    for prefix, replacement in FRENCH_ASSET_DIRS.items():
        if src.startswith(prefix) and not src.startswith(replacement):
            return replacement + src[len(prefix):]
    return src


def french_asset(src: str) -> str:
    """The French twin if the ledger declares one, otherwise the original.

    Declare a French plate in `restore_assets.TRACKED` and the French films
    pick it up on the next build — no edit here, and a test that fails until
    the stale "still English" line is removed.
    """
    twin = localise_asset(src)
    return twin if twin != src and twin in _declared() else src


def translate(spec: dict[str, Any]) -> dict[str, Any]:
    """A copy of one film's spec with every user-visible string in French.

    Deep-copied, because a spec holds lists of tuples that would otherwise be
    shared between the two cuts — and a shared mutable is how an edit to the
    French film silently edits the English one.
    """
    out = copy.deepcopy(spec)
    for scene in out["scenes"]:
        for key in ("eyebrow", "caption", "line", "mark"):
            if scene.get(key):
                scene[key] = tr(scene[key])
        if scene.get("rows"):
            scene["rows"] = [(tr(a), tr(b)) for a, b in scene["rows"]]
        if scene.get("items"):
            scene["items"] = [tr(i) for i in scene["items"]]
        if scene.get("steps"):
            scene["steps"] = [(n, tr(label)) for n, label in scene["steps"]]
        if scene.get("stages"):
            scene["stages"] = [
                (n, tr(label), *rest) for n, label, *rest in scene["stages"]
            ]
        # The pictures, where a French one exists.
        if scene.get("images"):
            scene["images"] = [french_asset(i) for i in scene["images"]]
        for key in ("fig", "gray", "base", "src"):
            if scene.get(key):
                scene[key] = french_asset(scene[key])
    return out

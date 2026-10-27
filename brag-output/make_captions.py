#!/usr/bin/env python3
"""Write WebVTT captions for the four films, English and French.

The text is not transcribed: it is the narration script the Kokoro voice was
generated from, and the timings are the measured start and duration of each
WAV. That is exact where a transcriber would only be close.

Run from brag-output/:  python3 make_captions.py [out-dir]
Default out-dir is ../web/video.
"""

from __future__ import annotations

import sys

# start, duration, text. Durations are the measured lengths of _assets/vo-*.wav.
FILMS: dict[str, dict[str, list[tuple[float, float, str]]]] = {
    "sprezzature": {
        "en": [(1.10, 3.0, 'Nearly every design decision has already been made.'),
                (6.50, 3.0, 'The laws of attention: Yablonski. Contrast: the W3C. What a colour-blind reader sees: a paper from 2009.'),
                (15.00, 3.0, 'All of it published years ago. Your tools have never heard of it.'),
                (24.00, 3.0, 'Here it is as code, for what you are building and for what is already live.'),
                (32.50, 3.0, 'What no rule does is look at the result.'),
                (41.00, 3.0, 'A vision model does that for you, on your own machine, then tells you what is wrong.'),
                (49.50, 3.0, 'Everything stays on your desk. Nothing travels.'),
                (55.80, 3.0, 'Sprezzature. Make it, audit it, then look at it.')],
        "fr": [(1.10, 3.0, "Presque tout ce qu'on décide en design a déjà été décidé."),
                (6.50, 3.0, "Les lois de l'attention, c'est Yablonski. Le contraste, c'est le W3C. Ce que voit un daltonien, c'est un article de 2009."),
                (15.00, 3.0, "Tout cela est publié depuis des années. Vos outils, eux, l'ignorent."),
                (24.00, 3.0, "Ici, c'est écrit en code : du côté de ce qu'on fabrique comme du côté de ce qui est déjà en ligne."),
                (32.50, 3.0, "Reste ce qu'aucune règle ne sait faire : regarder le résultat."),
                (41.00, 3.0, 'Un modèle de vision le fait à votre place, sur votre machine, puis vous dit ce qui cloche.'),
                (49.50, 3.0, 'Tout reste sur votre poste. Rien ne part ailleurs.'),
                (55.80, 3.0, 'Sprezzature. Fabriquez, auditez, puis regardez.')],
    },
    "colors": {
        "en": [(1.10, 3.0, 'Light grey on white reads perfectly well. At your desk, indoors.'),
                (6.50, 3.0, 'Outside, in full sun, the screen flattens the difference. For an eye that is failing, the text and the background merge.'),
                (15.00, 3.0, 'And about one man in twelve does not separate red from green. Your two bars become one.'),
                (20.00, 3.0, 'So the package redraws the chart the way that eye sees it.'),
                (27.00, 3.0, 'Protanopia. Deuteranopia. Tritanopia. And grey, for the printer.'),
                (34.00, 3.0, 'These come from a 2009 paper, measured on real observers.'),
                (41.00, 3.0, 'Watch what survives. Hue goes. Saturation goes. Lightness holds.'),
                (49.50, 3.0, 'So the audit keeps your hue and your saturation, then moves the lightness until the contrast clears.'),
                (55.80, 3.0, 'Sprezzature. Make it, audit it, then look at it.')],
        "fr": [(1.10, 3.0, "Du gris clair sur du blanc, ça se lit très bien. Chez vous, à l'intérieur."),
                (6.50, 3.0, "Dehors, en plein soleil, l'écran écrase la différence. Pour un œil qui baisse, le texte et le fond se confondent."),
                (15.00, 3.0, "Et un homme sur douze environ ne sépare pas le rouge du vert. Vos deux barres n'en font qu'une."),
                (20.00, 3.0, 'Alors le paquet redessine le graphique tel que cet œil-là le voit.'),
                (27.00, 3.0, "Protanopie. Deutéranopie. Tritanopie. Et le gris, pour l'imprimante."),
                (34.00, 3.0, "Les matrices viennent d'un article de 2009, mesurées sur de vrais observateurs."),
                (41.00, 3.0, "Regardez ce qui résiste. La teinte s'efface. La saturation s'efface. La clarté, elle, tient."),
                (49.50, 3.0, "L'audit garde donc votre teinte et votre saturation, puis fait varier la clarté jusqu'au seuil."),
                (55.80, 3.0, 'Sprezzature. Fabriquez, auditez, puis regardez.')],
    },
    "ux-laws": {
        "en": [(1.10, 2.453, "Nobody says: that violates Hick's Law."),
               (6.00, 4.181, "They say the page is overwhelming, or that they can never find the button."),
               (13.00, 5.120, "Thirty laws, curated by Jon Yablonski. Eight of them a machine can decide."),
               (20.50, 6.208, "No forty-four pixel hit area. A digit run past seven. A control with no focus ring."),
               (30.00, 3.947, "What it will not do is judge whether the screen answers the right question."),
               (38.50, 3.883, "That stays a human call. This is a gate, not a design review."),
               (46.00, 3.349, "Thirty laws you can read. Eight a machine can hold you to."),
               (55.80, 2.731, "Sprezzature. Make it, audit it, then look at it.")],
        "fr": [(1.10, 2.453, "Personne ne dit : ça viole la loi de Hick."),
               (6.00, 4.181, "On dit que la page est écrasante, ou qu'on ne trouve jamais le bouton."),
               (13.00, 5.120, "Trente lois, réunies par Jon Yablonski. Huit qu'une machine peut trancher."),
               (20.50, 6.208, "Pas de zone de clic de quarante-quatre pixels. Une suite de chiffres au-delà de sept. Un contrôle sans anneau de focus."),
               (30.00, 3.947, "Ce qu'il ne fera pas : juger si l'écran répond à la bonne question."),
               (38.50, 3.883, "Ça reste une décision humaine. C'est une barrière, pas une revue de design."),
               (46.00, 3.349, "Trente lois à lire. Huit qu'une machine peut vous opposer."),
               (55.80, 2.731, "Sprezzature. Fabriquer, auditer, puis regarder.")],
    },
    "accessibility": {
        "en": [(1.10, 2.731, "An unmuted autoplay masks a screen reader."),
               (6.50, 5.419, "Audio with no captions. Nothing to operate from a keyboard. The markup says all three."),
               (14.50, 4.075, "Twenty rules, each naming the element, the line, and the rule it broke."),
               (23.00, 4.053, "Six of them repair themselves, where there is exactly one safe repair."),
               (32.00, 3.371, "And the same rule, pointed the other way, writes the CSS."),
               (41.00, 3.733, "Tracking too tight to read becomes a comfortable reading toggle."),
               (48.50, 3.392, "Standard library only. Exit one on any finding."),
               (55.80, 2.731, "Sprezzature. Make it, audit it, then look at it.")],
        "fr": [(1.10, 2.731, "Une lecture automatique non muette couvre un lecteur d'écran."),
               (6.50, 5.419, "De l'audio sans sous-titres. Rien à piloter au clavier. Le balisage dit les trois."),
               (14.50, 4.075, "Vingt règles, chacune nommant l'élément, la ligne, et la règle enfreinte."),
               (23.00, 4.053, "Six se réparent toutes seules, là où il n'existe qu'une correction sûre."),
               (32.00, 3.371, "Et la même règle, retournée, écrit le CSS."),
               (41.00, 3.733, "Un interlettrage trop serré devient une bascule de lecture confortable."),
               (48.50, 3.392, "Bibliothèque standard seule. Sortie un à la moindre trouvaille."),
               (55.80, 2.731, "Sprezzature. Fabriquer, auditer, puis regarder.")],
    },
    "maps": {
        "en": [(1.10, 2.795, "A column of countries is a map waiting to happen."),
               (6.50, 5.931, "Real coastlines. A real projection. Eight kilometres of relief, and the rivers that leave it."),
               (15.00, 6.016, "Equal Earth keeps areas honest. A conic projection centres itself on the region you asked for."),
               (24.00, 4.587, "Zones by category, flashpoints, and a scale bar in two units at once."),
               (33.00, 2.603, "The density map draws no coastline at all."),
               (42.00, 4.651, "The land appears because events fell on it. The sea stays dark because none did."),
               (49.50, 2.197, "Every source named, with its licence."),
               (55.80, 2.731, "Sprezzature. Make it, audit it, then look at it.")],
        "fr": [(1.10, 2.795, "Une colonne de pays est une carte qui s'ignore."),
               (6.50, 5.931, "De vraies côtes. Une vraie projection. Huit kilomètres de relief, et les fleuves qui en partent."),
               (15.00, 6.016, "Equal Earth garde les aires honnêtes. Une projection conique se centre sur la région demandée."),
               (24.00, 4.587, "Des zones par catégorie, des points chauds, et une échelle en deux unités à la fois."),
               (33.00, 2.603, "La carte de densité ne dessine aucune côte."),
               (42.00, 4.651, "La terre apparaît parce que des événements y sont tombés. La mer reste sombre parce qu'aucun n'y est tombé."),
               (49.50, 2.197, "Chaque source nommée, avec sa licence."),
               (55.80, 2.731, "Sprezzature. Fabriquer, auditer, puis regarder.")],
    },
    "figures": {
        "en": [(1.10, 4.224, 'One hundred and sixty-seven kinds of chart. Every one written by hand.'),
                (6.50, 5.483, 'No charting library underneath. Each generator writes the SVG markup itself.'),
                (15.00, 6.677, 'Fifty-two categories, including the ones nobody ships: wind roses, ROC curves, survival curves.'),
                (24.00, 3.136, 'The deliverable is the vector, never a picture of one.'),
                (32.50, 4.267, 'A PNG is an export, for places that cannot take vector art.'),
                (41.00, 4.373, 'Then the loop no reference can supply: render, look, fix the source, again.'),
                (49.50, 3.115, 'A model does the looking, and it never leaves the machine.'),
                (55.80, 2.731, 'Sprezzature. Make it, audit it, then look at it.')],
        "fr": [(1.10, 4.224, 'Cent soixante-sept types de graphiques. Tous écrits à la main.'),
                (6.50, 5.483, 'Aucune bibliothèque de tracé en dessous. Chaque générateur écrit le SVG lui-même.'),
                (15.00, 6.677, 'Cinquante-deux catégories, dont celles que personne ne livre : roses des vents, courbes ROC, courbes de survie.'),
                (24.00, 3.136, 'Le livrable est le vectoriel, jamais une image de vectoriel.'),
                (32.50, 4.267, 'Un PNG est un export, pour les endroits qui refusent le vectoriel.'),
                (41.00, 4.373, "Puis la boucle qu'aucune référence ne fournit : rendre, regarder, corriger la source, recommencer."),
                (49.50, 3.115, "C'est un modèle qui regarde, et il ne quitte jamais la machine."),
                (55.80, 2.731, 'Sprezzature. Fabriquer, auditer, puis regarder.')],
    },
    "publish": {
        "en": [(1.10, 1.813, 'A document, becoming a site.'),
                (6.50, 4.800, 'Nine tools. The linter is standard library only, and runs in milliseconds.'),
                (15.00, 6.293, 'Favicons from one logo. A sitemap, an Atom feed, and the two files a language model reads.'),
                (24.00, 4.032, 'Open Graph, Twitter cards, Schema.org — all drafted locally.'),
                (32.50, 3.712, 'A rewrite at a target reading grade, that keeps the terms you named.'),
                (41.00, 3.072, 'And readalong, which binds the narration to the page.'),
                (49.50, 2.837, 'The sentence being spoken is the sentence lit up.'),
                (55.80, 2.731, 'Sprezzature. Make it, audit it, then look at it.')],
        "fr": [(1.10, 1.813, 'Un document, qui devient un site.'),
                (6.50, 4.800, "Neuf outils. Le linter n'utilise que la bibliothèque standard, et tourne en millisecondes."),
                (15.00, 6.293, "Des favicons depuis un seul logo. Un sitemap, un flux Atom, et les deux fichiers qu'un modèle de langue lit."),
                (24.00, 4.032, 'Open Graph, cartes Twitter, Schema.org — rédigés en local.'),
                (32.50, 3.712, 'Une réécriture à un niveau de lecture visé, qui garde les termes que vous avez nommés.'),
                (41.00, 3.072, 'Et readalong, qui lie la narration à la page.'),
                (49.50, 2.837, 'La phrase prononcée est la phrase allumée.'),
                (55.80, 2.731, 'Sprezzature. Fabriquer, auditer, puis regarder.')],
    },
    "audio": {
        "en": [(1.10, 2.560, 'One modality, read in both directions.'),
                (6.50, 5.269, 'Captions turn sound into timed text. Narration turns text into timed sound.'),
                (15.00, 5.312, 'Whisper large-v3-turbo. Who spoke when, up to four speakers, as RTTM.'),
                (24.00, 5.952, 'Narration lands as a WAV plus a WebVTT, exactly like a transcript does.'),
                (32.50, 1.728, 'And it audits its own output.'),
                (41.00, 3.243, 'Reading speed, line width, duration, overlaps.'),
                (49.50, 3.157, 'A caption track can be present and still be unreadable.'),
                (55.80, 2.731, 'Sprezzature. Make it, audit it, then look at it.')],
        "fr": [(1.10, 2.560, 'Une seule modalité, lue dans les deux sens.'),
                (6.50, 5.269, 'Les sous-titres font du son un texte minuté. La narration fait du texte un son minuté.'),
                (15.00, 5.312, "Whisper large-v3-turbo. Qui a parlé quand, jusqu'à quatre locuteurs, au format RTTM."),
                (24.00, 5.952, 'La narration arrive en WAV plus un WebVTT, exactement comme une transcription.'),
                (32.50, 1.728, 'Et il audite sa propre sortie.'),
                (41.00, 3.243, 'Vitesse de lecture, largeur de ligne, durée, chevauchements.'),
                (49.50, 3.157, 'Une piste de sous-titres peut être présente et rester illisible.'),
                (55.80, 2.731, 'Sprezzature. Fabriquer, auditer, puis regarder.')],
    },
    "cli-gui": {
        "en": [(1.10, 2.624, 'A tool nobody will type, wrapped in a page.'),
                (6.50, 5.269, 'Flags become fields. Choices become a dropdown. Required stays required.'),
                (15.00, 3.605, 'It does not read the help text. It reads the parser object.'),
                (24.00, 4.011, 'Argparse, Click, Typer — three adapters, one normalised schema.'),
                (32.50, 3.371, 'So the renderer never has to know which framework it came from.'),
                (41.00, 4.949, 'And when no parser object is reachable, it runs the help and reads what it printed.'),
                (49.50, 3.648, 'Which is how a Go or a Rust command line gets a form too.'),
                (55.80, 2.731, 'Sprezzature. Make it, audit it, then look at it.')],
        "fr": [(1.10, 2.624, 'Un outil que personne ne tapera, enveloppé dans une page.'),
                (6.50, 5.269, "Les options deviennent des champs. Les choix deviennent une liste. L'obligatoire reste obligatoire."),
                (15.00, 3.605, "Il ne lit pas le texte d'aide. Il lit l'objet parseur."),
                (24.00, 4.011, 'Argparse, Click, Typer — trois adaptateurs, un seul schéma normalisé.'),
                (32.50, 3.371, "Le rendu n'a donc jamais à savoir de quel cadre ça vient."),
                (41.00, 4.949, "Et quand aucun objet parseur n'est joignable, il lance l'aide et lit ce qu'elle a imprimé."),
                (49.50, 3.648, "C'est ainsi qu'une commande en Go ou en Rust obtient un formulaire aussi."),
                (55.80, 2.731, 'Sprezzature. Fabriquer, auditer, puis regarder.')],
    },
    "ui": {
        "en": [(1.10, 1.771, 'The smallest brick, on purpose.'),
                (6.50, 3.029, 'Its job is the aesthetic judgement written in prose.'),
                (15.00, 3.179, 'A hardcoded sentence costs nothing the day it is written.'),
                (24.00, 3.307, 'It costs a week the day somebody needs a second language.'),
                (32.50, 6.123, 'Scattered through JavaScript literals, HTML attributes, and prompt templates buried in Python.'),
                (41.00, 4.352, 'Nine components, nine snippets, six font files, and a starter page.'),
                (49.50, 3.691, "Taste is written down once, and then it is somebody else's too."),
                (55.80, 2.731, 'Sprezzature. Make it, audit it, then look at it.')],
        "fr": [(1.10, 1.771, 'La plus petite brique, exprès.'),
                (6.50, 3.029, "Son travail, c'est le jugement esthétique écrit en prose."),
                (15.00, 3.179, "Une phrase codée en dur ne coûte rien le jour où on l'écrit."),
                (24.00, 3.307, "Elle coûte une semaine le jour où quelqu'un veut une deuxième langue."),
                (32.50, 6.123, 'Éparpillée dans des littéraux JavaScript, des attributs HTML, et des gabarits de prompt enfouis en Python.'),
                (41.00, 4.352, 'Neuf composants, neuf extraits, six fichiers de fonte, et une page de départ.'),
                (49.50, 3.691, "Le goût s'écrit une fois, et ensuite il est aussi celui des autres."),
                (55.80, 2.731, 'Sprezzature. Fabriquer, auditer, puis regarder.')],
    },
    "video": {
        "en": [(1.10, 1.963, 'A film is a claim with a soundtrack.'),
                (6.50, 3.989, 'Every number on this screen was checked against the code that produces it.'),
                (15.00, 5.355, 'Declared claims, and the ones nobody declared: a number that appears and is never sourced.'),
                (24.00, 4.629, 'The assets are ledgered too. Tracked, derived, or sole surviving copy.'),
                (32.50, 3.627, 'A sole copy is the one a cleanup deletes without noticing.'),
                (41.00, 4.416, 'Captions are measured, not guessed. The voice file says how long the line is.'),
                (49.50, 5.077, 'Then a poster frame, and a loudness pass, so nothing arrives louder than the last thing.'),
                (55.80, 2.731, 'Sprezzature. Make it, audit it, then look at it.')],
        "fr": [(1.10, 1.963, 'Un film est une affirmation avec une bande-son.'),
                (6.50, 3.989, "Chaque nombre à l'écran a été vérifié contre le code qui le produit."),
                (15.00, 5.355, "Les affirmations déclarées, et celles que personne n'a déclarées : un nombre qui paraît sans source."),
                (24.00, 4.629, 'Les ressources aussi sont inventoriées. Suivie, dérivée, ou seule copie restante.'),
                (32.50, 3.627, "Une seule copie, c'est celle qu'un nettoyage supprime sans s'en apercevoir."),
                (41.00, 4.416, 'Les sous-titres sont mesurés, pas devinés. Le fichier de voix dit la durée de la ligne.'),
                (49.50, 5.077, "Puis une image d'affiche, et une passe de sonie, pour que rien n'arrive plus fort que le reste."),
                (55.80, 2.731, 'Sprezzature. Fabriquer, auditer, puis regarder.')],
    },
}

LINE_LIMIT = 58
# Punctuation keeps its place on the left of a break; a connector word moves to
# the right, so neither half of a split caption reads as a fragment.
AFTER = (". ", ", ", " ; ", " : ", ": ", " — ")
BEFORE = (" and ", " et ", " puis ", " then ", " so ", " alors ")


def stamp(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def split_line(text: str) -> tuple[str, str]:
    mid, best = len(text) / 2, None
    for seps, keep_left in ((AFTER, True), (BEFORE, False)):
        for sep in seps:
            i = text.find(sep)
            while i != -1:
                cut = i + len(sep.rstrip()) if keep_left else i
                if 14 < cut < len(text) - 14:
                    d = abs(cut - mid)
                    if best is None or d < best[0]:
                        best = (d, text[:cut].strip(), text[cut:].strip())
                i = text.find(sep, i + 1)
    if best:
        return best[1], best[2]
    words, run = text.split(), 0
    for k, w in enumerate(words):
        run += len(w) + 1
        if run >= mid:
            return " ".join(words[:k + 1]), " ".join(words[k + 1:])
    return text, ""


def cues(lines):
    out = []
    for start, dur, text in lines:
        if len(text) <= LINE_LIMIT:
            out.append((start, start + dur, text))
            continue
        a, b = split_line(text)
        mid = start + dur * (len(a) / (len(a) + len(b)))
        out += [(start, mid, a), (mid, start + dur, b)]
    return out


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

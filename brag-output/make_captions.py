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
        "en": [(1.10, 3.0, 'Sprezzature: ten packages that put the know-how of design into code.'),
                (6.50, 3.0, 'Nearly every design decision has already been made. By Yablonski, by the W3C, by a 2009 paper.'),
                (15.00, 3.0, 'All of it published years ago. Your tools have never heard of it.'),
                (24.00, 3.0, 'Here it is as code, for what you are building and for what is already live.'),
                (32.50, 3.0, 'What no rule does is look at the result.'),
                (41.00, 3.0, 'A vision model does that for you, on your own machine, then tells you what is wrong.'),
                (49.50, 3.0, 'Everything stays on your desk. Nothing travels.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, 'Sprezzature : dix paquets qui mettent en code le savoir-faire du design.'),
                (6.50, 3.0, "Presque tout ce qu'on décide en design a déjà été décidé. Par Yablonski, par le W3C, par un article de 2009."),
                (15.00, 3.0, "Tout cela est publié depuis des années. Vos outils, eux, l'ignorent."),
                (24.00, 3.0, "Ici, c'est écrit en code : du côté de ce qu'on fabrique comme du côté de ce qui est déjà en ligne."),
                (32.50, 3.0, "Reste ce qu'aucune règle ne sait faire : regarder le résultat."),
                (41.00, 3.0, 'Un modèle de vision le fait à votre place, sur votre machine, puis vous dit ce qui cloche.'),
                (49.50, 3.0, 'Tout reste sur votre poste. Rien ne part ailleurs.'),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "colors": {
        "en": [(1.10, 3.0, 'Sprezzature colors checks that your colours can be read. By everybody.'),
                (6.50, 3.0, 'Light grey on white reads perfectly well, at your desk, indoors. Outside, in full sun, the screen flattens the difference.'),
                (15.00, 3.0, 'One man in twelve does not separate red from green. Your two bars become one.'),
                (20.00, 3.0, 'So the package redraws the chart the way that eye sees it.'),
                (27.00, 3.0, 'Protanopia. Deuteranopia. Tritanopia. And grey, for the printer.'),
                (34.00, 3.0, 'These come from a 2009 paper, measured on real observers.'),
                (41.00, 3.0, 'Watch what survives. Hue goes. Saturation goes. Lightness holds.'),
                (49.50, 3.0, 'So the audit keeps your hue and your saturation, then moves the lightness until the contrast clears.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, 'Sprezzature colors vérifie que vos couleurs se lisent. Par tout le monde.'),
                (6.50, 3.0, "Du gris clair sur du blanc, ça se lit très bien, chez vous, à l'intérieur. Dehors, en plein soleil, l'écran écrase la différence."),
                (15.00, 3.0, "Et un homme sur douze environ ne sépare pas le rouge du vert. Vos deux barres n'en font qu'une."),
                (20.00, 3.0, 'Alors le paquet redessine le graphique tel que cet œil-là le voit.'),
                (27.00, 3.0, "Protanopie. Deutéranopie. Tritanopie. Et le gris, pour l'imprimante."),
                (34.00, 3.0, "Les matrices viennent d'un article de 2009, mesurées sur de vrais observateurs."),
                (41.00, 3.0, "Regardez ce qui résiste. La teinte s'efface. La saturation s'efface. La clarté, elle, tient."),
                (49.50, 3.0, "L'audit garde donc votre teinte et votre saturation, puis fait varier la clarté jusqu'au seuil."),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "ux-laws": {
        "en": [(1.10, 3.0, 'Sprezzature ux-laws reads your page against the laws of attention.'),
                (6.50, 3.0, 'They will tell you the page is overwhelming, that they can never find the button. Nobody will ever say Hick’s Law.'),
                (15.00, 3.0, 'Thirty laws, collected by Jon Yablonski. Eight of them settle from the source alone.'),
                (24.00, 3.0, 'The auditor reads the markup itself, with no browser and no rendering, in milliseconds.'),
                (30.00, 3.0, 'And counting the links in a menu is not enough.'),
                (37.00, 3.0, 'A responsive header holds two menus. The phone one and the desktop one never appear together.'),
                (46.50, 3.0, 'So it counts them apart. A block that collapses counts as a single choice.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, "Sprezzature ux-laws lit votre page à l'aune des lois de l'attention."),
                (6.50, 3.0, "On vous dira que la page est écrasante, qu'on ne trouve jamais le bouton. La loi de Hick, personne ne la citera."),
                (15.00, 3.0, 'Trente lois réunies par Jon Yablonski. Huit se tranchent depuis la source seule.'),
                (24.00, 3.0, "L'auditeur lit le balisage lui-même, sans navigateur ni rendu, en quelques millisecondes."),
                (30.00, 3.0, "Et compter les liens d'un menu ne suffit pas."),
                (37.00, 3.0, "Un en-tête responsive contient deux menus. Celui du téléphone et celui du bureau ne s'affichent jamais ensemble."),
                (46.50, 3.0, 'Il les compte donc à part. Un bloc qui se replie vaut un seul choix.'),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "accessibility": {
        "en": [(1.10, 3.0, 'Sprezzature accessibility decides twenty rules by reading your HTML.'),
                (6.50, 3.0, 'A video starts playing by itself, with sound. A blind reader now cannot hear the screen reader they would use to stop it.'),
                (16.50, 3.0, 'Twenty rules out of WCAG and WAI-ARIA answer that from the markup alone.'),
                (23.00, 3.0, 'Each finding names the element, the line and the rule it broke. No browser, no rendering.'),
                (29.50, 3.0, 'Six of the twenty repair themselves. Only six.'),
                (36.00, 3.0, 'A repair is automatic solely where exactly one repair is safe. The other fourteen are reported and never guessed at.'),
                (46.00, 3.0, 'And the same rule, turned around, writes the CSS instead of complaining about it.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, 'Sprezzature accessibility tranche vingt règles en lisant votre HTML.'),
                (6.50, 3.0, "Une vidéo démarre toute seule, avec le son. Un lecteur aveugle n'entend plus le lecteur d'écran qui lui servirait à l'arrêter."),
                (16.50, 3.0, 'Vingt règles tirées de WCAG et WAI-ARIA y répondent depuis le seul balisage.'),
                (23.00, 3.0, "Chaque constat nomme l'élément, la ligne et la règle enfreinte. Sans navigateur, sans rendu."),
                (29.50, 3.0, 'Six des vingt se réparent seules. Six, pas davantage.'),
                (36.00, 3.0, "Une réparation n'est automatique que là où il n'en existe qu'une de sûre. Les quatorze autres sont signalées, jamais devinées."),
                (46.00, 3.0, "Et la même règle, retournée, écrit le CSS au lieu de s'en plaindre."),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "maps": {
        "en": [(1.10, 3.0, 'Sprezzature maps draws on real ground, and says what it does not know.'),
                (6.50, 3.0, 'A column of countries hides where things actually happen.'),
                (16.00, 3.0, 'Real coastlines, a real projection, eight kilometres of relief. And ACLED and UCDP record how well each coordinate is known.'),
                (26.50, 3.0, 'Then the plate that draws no map at all.'),
                (35.00, 3.0, 'An accumulation field has no coastline, no border, no graticule.'),
                (42.00, 3.0, 'Every point on it is an event. The shape is what they add up to.'),
                (47.50, 3.0, 'The land appears because events fell on it. The sea stays dark because none did.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, "Sprezzature maps dessine sur un vrai sol, et dit ce qu'elle ignore."),
                (6.50, 3.0, "Une colonne de pays cache l'endroit où les choses arrivent vraiment."),
                (16.00, 3.0, 'De vraies côtes, une vraie projection, huit kilomètres de relief. Et ACLED et UCDP notent à quel point chaque coordonnée est connue.'),
                (26.50, 3.0, 'Puis la planche qui ne dessine aucune carte.'),
                (35.00, 3.0, "Un champ d'accumulation n'a ni côte, ni frontière, ni quadrillage."),
                (42.00, 3.0, "Chaque point y est un événement. La forme est ce qu'ils finissent par dessiner."),
                (47.50, 3.0, "La terre apparaît parce que des événements y sont tombés. La mer reste sombre parce qu'aucun n'y est tombé."),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "figures": {
        "en": [(1.10, 3.0, 'Sprezzature figures draws charts by hand, straight into SVG.'),
                (6.50, 3.0, 'You have a spreadsheet and no idea which chart fits, so you reach for the bar chart you reached for last time.'),
                (15.00, 3.0, 'There are 167 kinds here. Every one of them was written by hand.'),
                (22.00, 3.0, 'Each generator writes the SVG itself, with no charting library underneath.'),
                (28.00, 3.0, 'And each one declares the data roles it needs.'),
                (35.50, 3.0, 'So your columns decide. Three of them fill sixty-one of the kinds, ranked by readability.'),
                (46.00, 3.0, 'Deterministic, with no model near it. Then the Ralph Eyeball Loop asks one to look at the result.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, 'Sprezzature figures dessine 167 types de graphiques, écrits à la main.'),
                (6.50, 3.0, 'Vous avez un tableur et aucune idée du graphique qui convient, alors vous reprenez celui de la dernière fois.'),
                (15.00, 3.0, 'Il y a ici 167 types, tous écrits un par un à la main.'),
                (22.00, 3.0, 'Chaque générateur écrit le SVG lui-même, sans aucune bibliothèque de tracé dessous.'),
                (28.00, 3.0, "Et chacun déclare les rôles de données qu'il lui faut."),
                (35.50, 3.0, "Ce sont donc vos colonnes qui tranchent. Trois d'entre elles remplissent soixante et un types, classés par lisibilité."),
                (46.00, 3.0, "Déterministe, sans le moindre modèle. Puis la boucle Ralph en fait regarder un le résultat."),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "publish": {
        "en": [(1.10, 3.0, 'Sprezzature publish turns a folder of Markdown into a site people can find.'),
                (6.50, 3.0, 'It will even read the page aloud and highlight as it goes. One sentence out of step is worse than no highlighting at all.'),
                (16.00, 3.0, 'Nine tools turn one document into a site. The linter runs on the standard library alone.'),
                (24.00, 3.0, 'Favicons from a single logo. The indexes a crawler wants, plus the two files a language model reads.'),
                (30.60, 3.0, 'Then the hard part. The audio and the page leave the same Markdown by different roads.'),
                (38.00, 3.0, 'Sentences go to the voice engine. Blocks are walked as a tree.'),
                (47.70, 3.0, 'So it compares the two lists and raises on the first divergence. There is no third outcome.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, "Sprezzature publish transforme un dossier de Markdown en site qu'on trouve."),
                (6.50, 3.0, 'Elle lit même la page à voix haute en surlignant. Une phrase de décalage vaut moins que pas de surlignage du tout.'),
                (16.00, 3.0, "Neuf outils transforment un document en site. Le linter n'utilise que la bibliothèque standard."),
                (24.00, 3.0, "Des favicons depuis un seul logo. Les index pour les robots comme pour les modèles de langue."),
                (30.60, 3.0, "Puis le plus dur. L'audio et la page quittent le même Markdown par deux routes."),
                (38.00, 3.0, "Les phrases vont au moteur de voix. Les blocs sont parcourus comme un arbre : un motif ne verrait pas un bloc de code dans une puce."),
                (47.70, 3.0, "Il compare donc les deux listes et refuse au premier écart. Il n'y a pas de troisième issue."),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "audio": {
        "en": [(1.10, 3.0, 'Sprezzature audio says what was said, by whom, and in which language. All of it local.'),
                (6.50, 3.0, 'Your video has captions and they are accurate. Ninety characters, on screen for half a second. Nobody reads that.'),
                (16.00, 3.0, 'Whether a caption track exists is a question for the accessibility linter.'),
                (23.00, 3.0, "Whether what is inside it can be read at the speed it goes by is this one's."),
                (32.00, 3.0, 'And the numbers have a source. Netflix publishes them: seventeen characters a second, forty-two to a line.'),
                (41.00, 3.0, 'Five sixths of a second at the shortest, seven at the longest, two lines at most.'),
                (47.50, 3.0, 'Accuracy was the only thing anybody measured.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, 'Sprezzature audio dit ce qui a été dit, par qui, et en quelle langue. Tout en local.'),
                (6.50, 3.0, 'Votre vidéo a des sous-titres, et ils sont exacts. Quatre-vingt-dix caractères affichés une demi-seconde. Personne ne lit ça.'),
                (16.00, 3.0, "Savoir si une piste de sous-titres existe, c'est la question du linter d'accessibilité."),
                (23.00, 3.0, "Savoir si ce qu'elle contient se lit au rythme où ça défile, c'est celle de ce paquet."),
                (32.00, 3.0, "Et ces chiffres ont une source. Netflix les publie : dix-sept caractères par seconde, quarante-deux par ligne."),
                (41.00, 3.0, 'Cinq sixièmes de seconde au plus court, sept au plus long, deux lignes au maximum.'),
                (47.50, 3.0, "L'exactitude était la seule chose qu'on mesurait."),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "cli-gui": {
        "en": [(1.10, 3.0, 'Sprezzature cli-gui turns a command line into a form.'),
                (6.50, 3.0, 'Your colleague needs this tool. They will not open a terminal.'),
                (17.00, 3.0, 'So the command generates its own page, and it reads the parser object to do it. Options become fields, choices a list.'),
                (26.00, 3.0, 'Three frameworks, two adapters. A Typer app is converted by typer and then walked as Click, because that is what it already is.'),
                (36.00, 3.0, 'And one detail decides whether the page tells the truth.'),
                (42.00, 3.0, 'A Click group takes its name from the decorated function, which is usually not the command you installed.'),
                (50.00, 3.0, 'Unasked, the page would build a command line that does not exist.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, 'Sprezzature cli-gui transforme une ligne de commande en formulaire.'),
                (6.50, 3.0, "Votre collègue a besoin de cet outil. Il n'ouvrira pas de terminal."),
                (17.00, 3.0, "La commande engendre donc sa page, en lisant l'objet analyseur. Les options deviennent des champs, les choix une liste."),
                (26.00, 3.0, "Trois cadres, deux adaptateurs. Une application Typer est convertie par typer puis lue comme du Click, puisque c'est déjà ce qu'elle est."),
                (36.00, 3.0, 'Et un détail décide si la page dit vrai.'),
                (42.00, 3.0, "Un groupe Click tire son nom de la fonction décorée, qui n'est presque jamais la commande installée."),
                (50.00, 3.0, "Faute de le préciser, la page fabriquerait une ligne de commande qui n'existe pas."),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "ui": {
        "en": [(1.10, 3.0, 'Sprezzature ui finds every sentence hardcoded in your source, and files it.'),
                (6.50, 3.0, 'One written straight into a template costs nothing today. It costs a week the day somebody needs a second language.'),
                (17.50, 3.0, 'One catalogue holds them all. An audit finds every string that belongs in it.'),
                (25.00, 3.0, 'Including the prompts. A model prompt is a translatable string, which almost nobody treats as one.'),
                (33.00, 3.0, 'The fix writes each string into the catalogue. Then it stops.'),
                (43.00, 3.0, 'It will not rewrite your call site, because only you know whether that line wants a plural or a placeholder.'),
                (52.00, 3.0, 'So it prints the line to paste.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, 'Sprezzature ui trouve chaque phrase écrite en dur dans vos sources, et la range.'),
                (6.50, 3.0, "Écrite en dur dans un gabarit, elle ne coûte rien aujourd'hui. Elle coûte une semaine le jour où il faut une deuxième langue."),
                (17.50, 3.0, 'Un seul catalogue les rassemble. Un audit trouve chaque chaîne qui y a sa place.'),
                (25.00, 3.0, 'Y compris les prompts. Un prompt de modèle est une chaîne traduisible, ce que presque personne ne reconnaît.'),
                (33.00, 3.0, "La correction écrit chaque chaîne dans le catalogue. Puis elle s'arrête."),
                (43.00, 3.0, 'Elle ne réécrira pas votre appel, parce que vous seul savez si cette ligne réclame un pluriel ou une variable.'),
                (52.00, 3.0, 'Elle imprime donc la ligne à coller.'),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
    },
    "video": {
        "en": [(1.10, 3.0, 'Sprezzature video checks what a film says against the code it describes.'),
                (6.50, 3.0, 'A film asserts things at thirty frames a second, and burns them into pixels where nothing reads them again.'),
                (19.00, 3.0, 'So every claim now lives in a file beside the film, naming what would have to change for it to stop being true.'),
                (30.00, 3.0, '167 against the catalogue. Twenty against the linter. Thirty against the reference.'),
                (38.00, 3.0, 'And then the harder half.'),
                (44.00, 3.0, 'A declared claim can be checked. A number that merely appears on screen has nothing behind it.'),
                (52.00, 3.0, 'So the scan reports every one of those.'),
                (55.80, 3.0, 'Star it on GitHub, and the whole suite is at sprezzature.ai.')],
        "fr": [(1.10, 3.0, "Sprezzature video vérifie ce qu'un film affirme sur le code dont il parle."),
                (6.50, 3.0, 'Un film affirme des choses trente fois par seconde, et les grave dans des pixels que plus personne ne relit.'),
                (19.00, 3.0, "Chaque affirmation vit donc dans un fichier à côté du film, en nommant ce qui devrait changer pour qu'elle cesse d'être vraie."),
                (30.00, 3.0, '167 contre le catalogue. Vingt contre le linter. Trente contre la référence.'),
                (38.00, 3.0, 'Puis vient la moitié la plus dure.'),
                (44.00, 3.0, "Une affirmation déclarée se vérifie. Un nombre qui se contente de paraître à l'écran n'a rien derrière lui."),
                (52.00, 3.0, 'Le scan les signale donc tous.'),
                (55.80, 3.0, "Mettez une étoile sur GitHub. Tout est sur sprezzature.ai.")],
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

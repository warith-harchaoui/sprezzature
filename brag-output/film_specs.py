"""
The eleven films, cut again from nothing on 2026-11-06.

Warith's brief, in his words: crush every video on the site, redo it all from
scratch, make it understandable, insist on the design, keep the good ideas
from before, avoid the defects of the synthetic voice, and write the star as
"⭐️". No navigation trail across the top of the frame.

What was kept
-------------
* Guy KAWASAKI's spine: problem, solution, secret sauce, example, the ask.
  Every scene still carries its ``beat`` so the pitch check can read it; the
  frame no longer prints it.
* The suite's tagline first, on screen and in the voice, in every film.
* One language per film, end to end, the French written rather than
  translated.
* A picture the package itself produced is evidence, not illustration.
* The two asks, cheapest first, and the motto after them.

What changed
------------
* **The design is on screen.** A pale booking card a sunbeam erases and the
  colour fix brings back; a portrait a screen reader can only call "image"; a
  command line becoming a form; a sign-in screen changing language under a
  fixed layout. See ``film_demos.py``.
* **Seventy-five seconds, not a hundred and seventeen**, and one idea a scene.
* **The voice is written for the ear.** Measured on the set before, through
  the suite's own transcriber: the engine said "Esprit Tatouré" for the name,
  "expresser.ai" for the address, "1, 1, 51, 1 contre 1" for a ratio, and
  turned "167" into "Tuscan". So the voice says no digits, no ratios, no
  file names, no flags, no acronyms it has not been tested on, no URL, and
  sentences short enough to stay steady. Numbers stay on screen, where the
  claim checker reads them. The name itself is respelled for each voice in
  ``lexicon.yaml``, chosen by transcribing candidates: ``Spretsatoorey`` and
  ``Sprettsatouré``, the Italian sound in both.

Every line of voice is ``(start, text)``; ``VOICE`` is what
``make_captions`` and ``narrate_films`` read.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

DURATION = 75.0
STAR = "⭐️"


def L(en: str, fr: str) -> dict[str, str]:
    return {"en": en, "fr": fr}


TAGLINE = L(
    "Sprezzature is an AI engine for Design",
    "Sprezzature est un moteur d'IA pour le design",
)
SAY_TAGLINE = L(
    "Sprezzature is an AI engine for Design.",
    "Sprezzature est un moteur d'IA pour le design.",
)
PUNCHLINE = L("Make it, audit it, take a look at it.", "Faites, auditez, et regardez !")
SAY_STAR = L(
    "Star it on GitHub, and find the suite on sprezzature.ai.",
    "Si ça vous aide, une étoile sur GitHub, et toute la suite sur sprezzature.ai.",
)
SAY_PUNCH = L("Make it, audit it, take a look at it.", "Faites, auditez, et regardez.")
GITHUB = "github.com/warith-harchaoui"

LOOP_STEPS = [
    ("01", L("render", "dessiner")),
    ("02", L("look", "regarder")),
    ("03", L("fix the code", "corriger le code")),
    ("04", L("again", "recommencer")),
]


def what(name: str, line: dict) -> dict:
    mark = "Sprezzature" if name == "sprezzature" else f"Sprezzature · {name}"
    return dict(
        type="what", beat="what", start=0.0, dur=7.6, end=7.5,
        logo="logo-512.png", tagline=TAGLINE, mark=mark, line=line, url="sprezzature.ai",
    )


def cta(name: str, start: float = 65.9) -> dict:
    repo = "sprezzature" if name == "sprezzature" else f"sprezzature-{name}"
    mark = "Sprezzature" if name == "sprezzature" else f"Sprezzature · {name}"
    return dict(
        type="cta", beat="cta", start=start, dur=round(DURATION - start, 2), end=DURATION,
        logo="logo-512.png", mark=mark,
        actions=[
            (STAR, L("on GitHub", "sur GitHub"), f"{GITHUB}/{repo}"),
            ("→", L("The whole suite", "Toute la suite"), "sprezzature.ai"),
        ],
        punchline=PUNCHLINE, punch_at=start + 4.6,
    )


def held(beat: str, start: float, end: float, line: dict) -> dict:
    return dict(type="held", beat=beat, start=start, dur=round(end - start + 0.1, 2), end=end, line=line)


def opening(subject: dict) -> list[tuple[float, dict]]:
    return [(1.1, SAY_TAGLINE), (4.4, subject)]


def closing(start: float = 66.0) -> list[tuple[float, dict]]:
    # One line for both asks, as French already does: the address is spelled
    # out letter by letter and a second line's pause no longer fits in 75 s.
    return [(start, SAY_STAR), (start + 5.6, SAY_PUNCH)]


# ===================================================================== colors
CARD = dict(
    kicker="Bistro Lumière",
    title=L("Table for two", "Table pour deux"),
    sub=L("Friday evening, by the window", "Vendredi soir, près de la fenêtre"),
    button=L("Book", "Réserver"),
    # The fixes are what sprezzature-colors returns for these inputs, on the
    # OKLCH lightness axis at 4.5:1: #b8b8b8 -> #747474, #5fa8d3 -> #327DA6.
    fg_bad="#b8b8b8", fg_good="#747474", btn_bad="#5fa8d3", btn_good="#327DA6",
)

FILMS: dict[str, dict] = {}
VOICE: dict[str, dict[str, list[tuple[float, str]]]] = {}


def film(name: str, scenes: list[dict], voice: list[tuple[float, dict]], sfx: list) -> None:
    FILMS[name] = dict(duration=DURATION, vo=[], sfx=sfx, scenes=scenes)
    VOICE[name] = {lang: [(t, v[lang]) for t, v in voice if v[lang]] for lang in ("en", "fr")}


film(
    "colors",
    [
        what("colors", L("Colours everybody can read.", "Des couleurs que tout le monde peut lire.")),
        dict(type="demo", kind="contrast", beat="problem", start=7.4, dur=12.6, end=19.9,
             eyebrow=L("At your desk, it looks lovely", "À votre bureau, c'est joli"),
             card=CARD, glare_at=14.6, bad_at=15.6,
             bad=L("Gone in the sun", "Disparu au soleil"), good=L("Readable", "Lisible")),
        held("problem", 19.9, 32.9, L("Whoever picked the colour can read it. That is the trap.",
                                      "Celui qui a choisi la couleur la lit très bien. C'est le piège.")),
        dict(type="demo", kind="contrast", beat="solution", start=32.9, dur=12.1, end=44.9,
             eyebrow=L("The same colours, a little deeper", "Les mêmes couleurs, un peu plus profondes"),
             card=CARD, bad_at=33.6, fix_at=36.4,
             bad=L("Too pale", "Trop pâle"), good=L("Readable, for everyone", "Lisible, pour tout le monde")),
        held("magic", 44.9, 54.9, L("Hue can vanish. Lightness never does.",
                                    "La teinte peut disparaître. La clarté, jamais.")),
        dict(type="cvd", beat="example", start=54.9, dur=11.1, end=65.9,
             eyebrow=L("One chart, through other eyes", "Un graphique, vu par d'autres yeux"),
             base="figures/cvd/00-original.png",
             stages=[
                 ("01", L("protanopia", "protanopie"), "figures/cvd/01-protanopia.png", 56.9),
                 ("02", L("deuteranopia", "deutéranopie"), "figures/cvd/02-deuteranopia.png", 58.9),
                 ("03", L("tritanopia", "tritanopie"), "figures/cvd/03-tritanopia.png", 60.9),
                 ("04", L("greyscale", "niveaux de gris"), "figures/cvd/04-grayscale.png", 62.9),
             ],
             ratio=1490 / 1010, wipe_dur=0.8, caption_at=63.6,
             caption=L("Simulated the way each eye really sees.", "Simulé comme chaque œil voit vraiment.")),
        cta("colors"),
    ],
    opening(L("This one is about colour.", "Ici, on parle de couleur."))
    + [
        (8.0, L("Here is a booking card, in soft pastel colours.",
                "Voici une carte de réservation, en couleurs pastel.")),
        (11.6, L("At your desk, it looks lovely.", "À votre bureau, elle est très jolie.")),
        (14.8, L("Outside, in the sun, the words disappear.", "Dehors, au soleil, le texte disparaît.")),
        (20.4, L("The person who picked the colour can always read it.",
                 "Celui qui a choisi la couleur la lit toujours très bien.")),
        (24.6, L("That is the trap.", "C'est tout le piège.")),
        (27.0, L("And 1 man in 12 cannot tell red from green.",
                 "Et un homme sur douze ne distingue pas le rouge du vert.")),
        (33.4, L("Here, every pair of colours is checked, and the weak ones are fixed.",
                 "Ici, chaque paire de couleurs est contrôlée, et les plus faibles sont corrigées.")),
        (38.6, L("Same blue, same grey. Just deep enough to read.",
                 "Le même bleu, le même gris. Juste assez profonds pour se lire.")),
        (45.4, L("The secret: colour blindness takes away hue, but never lightness.",
                 "Le secret : le daltonisme efface la teinte, jamais la clarté.")),
        (50.2, L("So the fix only moves lightness, and your brand stays your brand.",
                 "Alors la correction ne touche qu'à la clarté, et votre marque reste la vôtre.")),
        (55.4, L("Here is one chart, seen through 4 kinds of eyes.",
                 "Voici un graphique, vu par quatre regards différents.")),
        (60.2, L("The colours change. The bars stay apart.",
                 "Les couleurs changent. Les barres restent distinctes.")),
    ]
    + closing(),
    [("drop", 7.6), ("wipe", 14.7), ("tile", 36.4), ("wipe", 56.9), ("bell", 66.0)],
)

# ==================================================================== figures
film(
    "figures",
    [
        what("figures", L("The right chart for your data, drawn by hand.",
                          "Le bon graphique pour vos données, dessiné à la main.")),
        held("problem", 7.4, 19.9, L("A spreadsheet, and no idea which chart.",
                                     "Un tableur, et aucune idée du bon graphique.")),
        dict(type="grid", beat="solution", start=19.9, dur=13.1, end=32.9,
             eyebrow=L("167 kinds of chart", "167 types de graphiques"),
             images=["figures/sankey.svg", "figures/alluvial.svg", "figures/chord.svg",
                     "figures/bellcurve.svg", "figures/circle-packing.svg", "figures/candlestick.svg",
                     "figures/clustermap.svg", "figures/kde2d-contour.png", "figures/surface3d.png"],
             at=[21.0, 21.6, 22.2, 22.8, 23.4, 24.0, 24.6, 25.2, 25.8]),
        held("solution", 32.9, 44.9, L("Every chart is real text, not a picture of text.",
                                       "Chaque graphique est du vrai texte, pas une image de texte.")),
        held("magic", 44.9, 54.9, L("Every kind says what data it needs. Your columns choose.",
                                    "Chaque type dit ce qu'il lui faut. Vos colonnes choisissent.")),
        dict(type="shot", beat="example", start=54.9, dur=11.1, end=65.9,
             eyebrow=L("A flow, drawn as a document", "Un flux, dessiné comme un document"),
             src="figures/sankey.svg", ratio=980 / 928, at=55.6),
        cta("figures"),
    ],
    opening(L("This one is about charts.", "Ici, on parle de graphiques."))
    + [
        (8.0, L("You have a spreadsheet, and no idea which chart to draw.",
                "Vous avez un tableur, et aucune idée du graphique à faire.")),
        (13.0, L("So you make the same bar chart as last time.",
                 "Alors vous refaites le même histogramme que la dernière fois.")),
        (20.4, L("Here, you have 167 kinds of chart to choose from.",
                 "Ici, vous avez plus de cent cinquante types au choix.")),
        (25.6, L("Flows, networks, distributions, maps, and many more.",
                 "Des flux, des réseaux, des distributions, des cartes, et bien d'autres.")),
        (33.4, L("Each one is drawn by hand, line by line, as a real vector file.",
                 "Chacun est dessiné à la main, trait par trait, en vrai fichier vectoriel.")),
        (38.6, L("The text stays text. You can select it, search it, and hear it read aloud.",
                 "Le texte reste du texte. On peut le sélectionner, le chercher, et l'entendre.")),
        (45.4, L("The secret: every kind says what data it needs.",
                 "Le secret : chaque type dit de quelles données il a besoin.")),
        (49.6, L("So your columns do the choosing, and nothing is left to guesswork.",
                 "Alors ce sont vos colonnes qui choisissent, et rien n'est laissé au hasard.")),
        (55.4, L("And the result reads like a page, not like a screenshot.",
                 "Et le résultat se lit comme une page, pas comme une capture d'écran.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 21.0), ("wipe", 44.9), ("tile", 55.6), ("bell", 66.0)],
)

# ======================================================================= maps
film(
    "maps",
    [
        what("maps", L("Real places, real ground.", "De vrais lieux, un vrai relief.")),
        held("problem", 7.4, 19.9, L("A table of countries hides where things happen.",
                                     "Un tableau de pays cache où les choses se passent.")),
        dict(type="grid", beat="solution", start=19.9, dur=13.1, end=32.9,
             eyebrow=L("Relief, rivers and lakes", "Relief, rivières et lacs"),
             images=["maps/situation-himalaya.png", "maps/situation-iberia.png",
                     "maps/situation-switzerland.png", "maps/situation-western-europe.png"],
             at=[21.0, 22.2, 23.4, 24.6]),
        dict(type="shot", beat="solution", start=32.9, dur=12.1, end=44.9,
             eyebrow=L("Who holds what", "Qui tient quoi"),
             src="maps/situation-ukraine.png", ratio=1300 / 971, at=33.6),
        held("magic", 44.9, 54.9, L("A rough location is drawn as rough.",
                                    "Un lieu approximatif est dessiné approximatif.")),
        dict(type="shot", beat="example", start=54.9, dur=11.1, end=65.9,
             eyebrow=L("4 actors, one clear legend", "4 acteurs, une légende claire"),
             src="maps/situation-syria.png", ratio=1300 / 1289, at=55.6),
        cta("maps"),
    ],
    opening(L("This one is about maps.", "Ici, on parle de cartes."))
    + [
        (8.0, L("A table of countries hides where things really happen.",
                "Un tableau de pays cache où les choses se passent vraiment.")),
        (13.0, L("And most maps draw every place as the same little dot.",
                 "Et la plupart des cartes dessinent chaque lieu par le même petit point.")),
        (20.4, L("Here, maps start from the real ground: mountains, rivers and lakes.",
                 "Ici, les cartes partent du vrai terrain : montagnes, rivières et lacs.")),
        (25.8, L("Every line is drawn by our own code, on a projection chosen for the region.",
                 "Chaque trait est dessiné par notre code, sur une projection choisie pour la région.")),
        (33.4, L("Then the story goes on top: who holds what, and where.",
                 "Puis l'histoire se pose dessus : qui tient quoi, et où.")),
        (38.6, L("The legend sits in the quiet corner, never on the action.",
                 "La légende se range dans le coin calme, jamais sur l'action.")),
        (45.4, L("The secret: conflict data says how precise each location is.",
                 "Le secret : les données de conflit disent à quel point chaque lieu est précis.")),
        (50.0, L("A precise place gets a solid dot. A rough one gets a hollow ring.",
                 "Un lieu précis a un point plein. Un lieu approximatif, un cercle vide.")),
        (55.4, L("4 actors, one clear legend, and a country you recognise at a glance.",
                 "Quatre acteurs, une légende claire, et un pays qu'on reconnaît d'un coup d'œil.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 21.0), ("wipe", 33.6), ("wipe", 55.6), ("bell", 66.0)],
)

# ==================================================================== ux-laws
film(
    "ux-laws",
    [
        what("ux-laws", L("The laws of UX, checked in your page.",
                          "Les lois de l'UX, vérifiées dans votre page.")),
        held("problem", 7.4, 19.9, L("“I can never find the button.”",
                                     "« Je ne trouve jamais le bouton. »")),
        dict(type="demo", kind="pair", beat="solution", start=19.9, dur=13.1, end=32.9,
             eyebrow=L("Hick's Law, in one menu", "La loi de Hick, dans un menu"),
             images=["ux-laws/nav-forty.svg", "ux-laws/nav-seven.svg"],
             left=(1200 / 900, L("Too many choices at once", "Trop de choix d'un coup"), False),
             right=(1200 / 900, L("A few, grouped", "Quelques-uns, regroupés"), True),
             at=[20.6, 25.4]),
        held("solution", 32.9, 44.9, L("30 laws of UX. 8 checked straight from the page.",
                                       "30 lois de l'UX. 8 vérifiées directement dans la page.")),
        held("magic", 44.9, 54.9, L("It counts what a person sees at one moment.",
                                    "Il compte ce qu'une personne voit à un instant donné.")),
        held("example", 54.9, 65.9, L("A fast check. The judgement stays yours.",
                                      "Un contrôle rapide. Le jugement reste le vôtre.")),
        cta("ux-laws"),
    ],
    opening(L("This one is about how a page feels.", "Ici, on parle de ce qu'on ressent devant une page."))
    + [
        (8.0, L("People will tell you a page is overwhelming.",
                "Les gens vous diront qu'une page est étouffante.")),
        (12.4, L("They will never tell you which law of design it breaks.",
                 "Ils ne vous diront jamais quelle loi du design elle enfreint.")),
        (20.4, L("Here is the same menu, twice.", "Voici le même menu, deux fois.")),
        (24.0, L("The more choices at once, the longer it takes to pick one.",
                 "Plus il y a de choix d'un coup, plus on met de temps à choisir.")),
        (28.6, L("That is Hick's Law.", "C'est la loi de Hick.")),
        (33.4, L("The suite knows 30 laws of user experience.",
                 "La suite connaît trente lois de l'expérience utilisateur.")),
        (38.2, L("8 of them can be checked straight from the page, in a second.",
                 "Huit se vérifient directement dans la page, en une seconde.")),
        (45.4, L("The secret: it counts what a person sees at one moment.",
                 "Le secret : il compte ce qu'une personne voit à un instant donné.")),
        (49.8, L("A phone menu and a desktop menu are never added together.",
                 "Le menu du téléphone et celui de l'ordinateur ne sont jamais additionnés.")),
        (55.4, L("It is a fast check, not a designer.", "C'est un contrôle rapide, pas un designer.")),
        (59.2, L("Whether the page answers the right question stays your call.",
                 "Savoir si la page répond à la bonne question, ça reste votre décision.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 20.6), ("tile", 25.4), ("wipe", 44.9), ("bell", 66.0)],
)

# ============================================================== accessibility
ALT = L(
    "Studio portrait of Marie Skłodowska-Curie in Paris, director of the Radium Institute.",
    "Portrait de Marie Curie en studio à Paris, directrice de l'Institut du radium.",
)
film(
    "accessibility",
    [
        what("accessibility", L("Pages everybody can use, including by ear.",
                                "Des pages que tout le monde peut utiliser, même à l'oreille.")),
        dict(type="demo", kind="alt", beat="problem", start=7.4, dur=12.6, end=19.9,
             eyebrow=L("What a blind reader hears", "Ce qu'entend un lecteur aveugle"),
             src="shots/alt-marie-curie.jpg", who=L("Screen reader", "Lecteur d'écran"),
             said=L("image", "image"), alt=ALT, said_at=12.6),
        held("problem", 19.9, 32.9, L("A video starts on its own, with sound.",
                                      "Une vidéo démarre seule, avec le son.")),
        held("solution", 32.9, 44.9, L("20 rules. 6 of them repair themselves.",
                                       "20 règles. 6 se réparent seules.")),
        dict(type="demo", kind="alt", beat="magic", start=44.9, dur=15.1, end=59.9,
             eyebrow=L("The description, drafted from the page", "La description, rédigée d'après la page"),
             src="shots/alt-marie-curie.jpg", who=L("Screen reader", "Lecteur d'écran"),
             said=L("image", "image"), alt=ALT, said_at=45.4, alt_at=50.4, alt_step=0.22),
        held("example", 59.9, 65.9, L("A first draft. You stay the editor.",
                                      "Un premier jet. Vous restez l'éditeur.")),
        cta("accessibility"),
    ],
    opening(L("This one is about accessibility.", "Ici, on parle d'accessibilité."))
    + [
        (8.0, L("A blind reader visits your page with a screen reader.",
                "Une lectrice aveugle visite votre page avec un lecteur d'écran.")),
        (12.8, L("On this portrait, all she hears is one word: image.",
                 "Sur ce portrait, elle n'entend qu'un mot : image.")),
        (20.4, L("Or a video starts on its own, with sound.",
                 "Ou bien une vidéo démarre seule, avec le son.")),
        (24.4, L("Now she cannot hear the screen reader that would help her stop it.",
                 "Elle n'entend plus le lecteur d'écran qui l'aiderait à l'arrêter.")),
        (33.4, L("The suite reads your page and checks 20 rules.",
                 "La suite lit votre page et contrôle vingt règles.")),
        (38.0, L("It can repair 6 of them by itself, safely.",
                 "Elle sait en réparer six toute seule, sans risque.")),
        (45.4, L("And the missing descriptions? A model on your machine writes them.",
                 "Et les descriptions manquantes ? Un modèle sur votre machine les rédige.")),
        (50.6, L("It looks at the image, and reads the page around it.",
                 "Il regarde l'image, et lit la page autour.")),
        (60.4, L("It is a first draft. You stay the editor.",
                 "C'est un premier jet. Vous restez l'éditeur.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 12.6), ("wipe", 32.9), ("tile", 50.4), ("bell", 66.0)],
)

# ====================================================================== audio
BAD_LINES = L(
    "so what we found when we looked at all of the data from the last three quarters was",
    "alors ce qu'on a trouvé en regardant toutes les données des trois derniers trimestres c'est",
)
film(
    "audio",
    [
        what("audio", L("Speech into text, and text into speech, on your machine.",
                        "La parole en texte, et le texte en parole, sur votre machine.")),
        dict(type="demo", kind="captions", beat="problem", start=7.4, dur=25.6, end=32.9,
             eyebrow=L("The same words, captioned twice", "Les mêmes mots, sous-titrés deux fois"),
             src="maps/situation-himalaya.png",
             bad_lines=[
                 L("so what we found when we looked at all of the data from the last three quarters was that the",
                   "alors ce qu'on a trouvé en regardant toutes les données des trois derniers trimestres c'est que"),
                 L("numbers had been there all along and nobody had thought to put them side by side before",
                   "les chiffres étaient là depuis le début et personne n'avait pensé à les comparer avant"),
                 L("which is why we decided to change the way the whole team reads the weekly report",
                   "c'est pour ça qu'on a changé la façon dont toute l'équipe lit le rapport de la semaine"),
             ],
             good_lines=[L("What we found surprised us:", "Ce qu'on a trouvé nous a surpris :"),
                         L("the numbers were there all along.", "les chiffres étaient là depuis le début.")],
             bad_at=10.4, good_at=25.6,
             bad=L("Too long, too fast", "Trop long, trop rapide"),
             good=L("Two lines, and time to read", "Deux lignes, et le temps de lire")),
        held("solution", 32.9, 44.9, L("Who spoke, what was said, in which language.",
                                       "Qui parle, ce qui est dit, dans quelle langue.")),
        held("magic", 44.9, 54.9, L("Text into speech, with its captions.",
                                    "Le texte en parole, avec ses sous-titres.")),
        dict(type="shot", beat="example", start=54.9, dur=11.1, end=65.9,
             eyebrow=L("One medium, both directions", "Un seul médium, dans les deux sens"),
             src="figures/audio-how-it-works.svg", ratio=1360 / 820, at=55.6),
        cta("audio"),
    ],
    opening(L("This one is about sound.", "Ici, on parle de son."))
    + [
        (8.0, L("Your video has captions, and every word is right.",
                "Votre vidéo a des sous-titres, et chaque mot est juste.")),
        (12.4, L("But one long line flashing by is not something anyone can read.",
                 "Mais une longue ligne qui défile en un éclair, personne ne peut la lire.")),
        (18.6, L("Accuracy was the only thing anybody measured.",
                 "La justesse était la seule chose qu'on mesurait.")),
        (25.8, L("Here, captions follow the rules of professional subtitling.",
                 "Ici, les sous-titres suivent les règles du sous-titrage professionnel.")),
        (30.0, L("2 lines at most, and time to read them.",
                 "Deux lignes au plus, et le temps de les lire.")),
        (33.6, L("It also tells who is speaking, and translates the captions.",
                 "Il sait aussi qui parle, et traduit les sous-titres.")),
        (38.8, L("Everything runs on your machine. No sound ever leaves it.",
                 "Tout tourne sur votre machine. Aucun son n'en sort.")),
        (45.4, L("And it works backwards too: it reads text aloud.",
                 "Et ça marche aussi dans l'autre sens : il lit un texte à voix haute.")),
        (49.8, L("The voice comes with its own captions, like this film.",
                 "La voix arrive avec ses propres sous-titres, comme ce film.")),
        (55.4, L("Speech to text, text to speech. One tool, both directions.",
                 "De la parole au texte, du texte à la parole. Un outil, deux sens.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 10.4), ("wipe", 25.6), ("tile", 55.6), ("bell", 66.0)],
)

# ==================================================================== cli-gui
film(
    "cli-gui",
    [
        what("cli-gui", L("Your command line, as a form anyone can fill in.",
                          "Votre ligne de commande, en formulaire pour tous.")),
        held("problem", 7.4, 19.9, L("Your colleague needs this tool. They will not open a terminal.",
                                     "Votre collègue a besoin de cet outil. Il n'ouvrira pas de terminal.")),
        dict(type="demo", kind="form", beat="solution", start=19.9, dur=20.1, end=39.9,
             eyebrow=L("The same tool, as a form", "Le même outil, en formulaire"),
             command='make-figure --kind bar --input sales.csv --title "Sales by region"',
             fields=[
                 (L("Chart kind", "Type de graphique"), "bar", True),
                 (L("Data file", "Fichier de données"), "sales.csv", False),
                 (L("Title", "Titre"), L("Sales by region", "Ventes par région"), False),
                 (L("Palette", "Palette"), "universal", True),
             ],
             button=L("Copy the command", "Copier la commande"), form_at=25.6),
        held("magic", 39.9, 51.9, L("It reads the tool itself, not its help text.",
                                    "Il lit l'outil lui-même, pas son texte d'aide.")),
        held("example", 51.9, 65.9, L("No server. Nothing to install. One file.",
                                      "Pas de serveur. Rien à installer. Un seul fichier.")),
        cta("cli-gui"),
    ],
    opening(L("This one is about command lines.", "Ici, on parle de ligne de commande."))
    + [
        (8.0, L("Your colleague needs your tool.", "Votre collègue a besoin de votre outil.")),
        (11.4, L("But they will never open a terminal, or remember the options.",
                 "Mais il n'ouvrira jamais un terminal, ni ne retiendra les options.")),
        (20.4, L("Here, the command builds its own page.", "Ici, la commande fabrique sa propre page.")),
        (25.8, L("Every option becomes a field. Every choice becomes a list.",
                 "Chaque option devient un champ. Chaque choix devient une liste.")),
        (31.4, L("Your colleague fills it in, and gets the exact command back.",
                 "Votre collègue le remplit, et récupère la commande exacte.")),
        (40.4, L("The secret: it reads the tool's own definition, not its help text.",
                 "Le secret : il lit la définition de l'outil, pas son texte d'aide.")),
        (45.6, L("So the form can never show an option the tool does not have.",
                 "Alors le formulaire ne propose jamais une option que l'outil n'a pas.")),
        (52.4, L("The page is a single file. Nothing to install, nothing to host.",
                 "La page est un seul fichier. Rien à installer, rien à héberger.")),
        (57.8, L("It never runs anything. It only writes the command.",
                 "Elle n'exécute rien. Elle écrit seulement la commande.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 20.4), ("tile", 25.6), ("wipe", 39.9), ("bell", 66.0)],
)

# ========================================================================= ui
film(
    "ui",
    [
        what("ui", L("Interfaces that speak every language.", "Des interfaces qui parlent toutes les langues.")),
        held("problem", 7.4, 19.9, L("A sentence typed into a page costs nothing today.",
                                     "Une phrase tapée dans une page ne coûte rien aujourd'hui.")),
        dict(type="demo", kind="i18n", beat="solution", start=19.9, dur=20.1, end=39.9,
             eyebrow=L("One screen, every language", "Un écran, toutes les langues"),
             langs=[
                 ("EN", ["Welcome back", "Email", "Password", "Sign in", "Forgot your password?"]),
                 ("FR", ["Bon retour", "E-mail", "Mot de passe", "Se connecter", "Mot de passe oublié ?"]),
                 ("DE", ["Willkommen zurück", "E-Mail", "Passwort", "Anmelden", "Passwort vergessen?"]),
             ],
             at=[28.0, 33.0]),
        held("magic", 39.9, 51.9, L("It finds the strings, then hands you the pen.",
                                    "Il trouve les phrases, puis vous laisse la plume.")),
        dict(type="demo", kind="components", beat="example", start=51.9, dur=14.1, end=65.9,
             eyebrow=L("3 typefaces, one family, light and dark",
                       "3 polices, une famille, clair et sombre"),
             text=dict(title=L("Notifications", "Notifications"),
                       body=L("Choose when we may write to you.", "Choisissez quand nous pouvons vous écrire."),
                       label=L("Email", "E-mail"), value="ada@example.org",
                       primary=L("Save", "Enregistrer"), secondary=L("Cancel", "Annuler")),
             focus_at=[57.0, 58.6, 60.2]),
        cta("ui"),
    ],
    opening(L("This one is about interfaces.", "Ici, on parle d'interfaces."))
    + [
        (8.0, L("A sentence typed straight into a page costs nothing today.",
                "Une phrase tapée directement dans une page ne coûte rien aujourd'hui.")),
        (12.6, L("It costs a week the day you need a second language.",
                 "Elle coûte une semaine le jour où il faut une deuxième langue.")),
        (20.4, L("Here, every sentence lives in one catalogue.",
                 "Ici, chaque phrase vit dans un seul catalogue.")),
        (24.6, L("So the same screen changes language, and the design holds.",
                 "Alors le même écran change de langue, et le design tient.")),
        (30.0, L("English, French, German. Nothing moves.",
                 "Anglais, français, allemand. Rien ne bouge.")),
        (40.4, L("The audit finds every sentence that belongs in the catalogue.",
                 "L'audit trouve chaque phrase qui devrait être dans le catalogue.")),
        (45.4, L("Then it stops, and lets the author decide. It never guesses.",
                 "Puis il s'arrête, et laisse l'auteur décider. Il ne devine jamais.")),
        (52.4, L("The same care goes into every component.",
                 "Le même soin va dans chaque composant.")),
        (56.6, L("One family of typefaces, visible focus, and a dark mode that works.",
                 "Une famille de polices, un focus visible, et un mode sombre qui marche.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 20.4), ("tile", 28.0), ("tile", 33.0), ("bell", 66.0)],
)

# ==================================================================== publish
film(
    "publish",
    [
        what("publish", L("A folder of text becomes a site people find.",
                          "Un dossier de texte devient un site qu'on trouve.")),
        held("problem", 7.4, 19.9, L("A good page nobody finds is a page nobody reads.",
                                     "Une bonne page introuvable, personne ne la lit.")),
        dict(type="demo", kind="site", beat="solution", start=19.9, dur=24.1, end=43.9,
             eyebrow=L("From a text file to a site", "D'un fichier texte à un site"),
             markdown=L("# A walk in Lisbon\n\nThe tram climbs the hill at dawn.\nThe river turns to gold.\nThen the city wakes up.",
                        "# Une promenade à Lisbonne\n\nLe tram grimpe la colline à l'aube.\nLe fleuve devient doré.\nPuis la ville se réveille."),
             tab=L("A walk in Lisbon", "Une promenade à Lisbonne"),
             title=L("A walk in Lisbon", "Une promenade à Lisbonne"),
             sentences=[L("The tram climbs the hill at dawn.", "Le tram grimpe la colline à l'aube."),
                        L("The river turns to gold.", "Le fleuve devient doré."),
                        L("Then the city wakes up.", "Puis la ville se réveille.")],
             listen=L("Listen to this page", "Écouter cette page"),
             page_at=25.4, read_at=[35.2, 37.6, 40.0]),
        held("magic", 43.9, 54.9, L("The voice and the highlight cannot drift apart.",
                                    "La voix et le surlignage ne peuvent pas se décaler.")),
        dict(type="shot", beat="example", start=54.9, dur=11.1, end=65.9,
             eyebrow=L("Its own documentation, reading itself", "Sa propre documentation, qui se lit elle-même"),
             src="shots/readalong.png", ratio=1520 / 1140, at=55.6),
        cta("publish"),
    ],
    opening(L("This one is about publishing.", "Ici, on parle de publication."))
    + [
        (8.0, L("You wrote a good page.", "Vous avez écrit une bonne page.")),
        (10.6, L("But search engines and AI assistants cannot find it, and nobody shares it.",
                 "Mais ni les moteurs de recherche ni les assistants ne la trouvent, et personne ne la partage.")),
        (20.4, L("Here, your text files become a real site.", "Ici, vos fichiers texte deviennent un vrai site.")),
        (25.6, L("With cards for sharing, icons, and what search engines and assistants read.",
                 "Avec les cartes de partage, les icônes, et ce que lisent moteurs et assistants.")),
        (34.4, L("And the page can read itself aloud, one highlighted sentence at a time.",
                 "Et la page peut se lire à voix haute, en surlignant chaque phrase.")),
        (44.4, L("The secret: the voice and the page are checked against each other.",
                 "Le secret : la voix et la page sont vérifiées l'une contre l'autre.")),
        (49.4, L("If they ever disagree, it refuses. It never points at the wrong line.",
                 "Si elles ne concordent pas, il refuse. Il ne montre jamais la mauvaise ligne.")),
        (55.4, L("This is its own documentation, narrated and published by itself.",
                 "Voici sa propre documentation, lue et publiée par lui-même.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 20.4), ("tile", 25.4), ("wipe", 43.9), ("bell", 66.0)],
)

# ====================================================================== video
film(
    "video",
    [
        what("video", L("Films that stay true to the code.", "Des films qui restent fidèles au code.")),
        held("problem", 7.4, 19.9, L("A number in a video is never read again.",
                                     "Un nombre dans une vidéo n'est jamais relu.")),
        dict(type="demo", kind="check", beat="solution", start=19.9, dur=20.1, end=39.9,
             eyebrow=L("It happened to this very suite", "C'est arrivé à cette suite"),
             old="127", new="167", unit=L("chart kinds", "types de graphiques"),
             bad=L("The code says otherwise", "Le code dit autre chose"),
             good=L("Checked against the code", "Vérifié contre le code"),
             bad_at=26.4, fix_at=31.6),
        held("magic", 39.9, 51.9, L("Every number on screen must be backed by the code.",
                                    "Chaque nombre à l'écran doit être justifié par le code.")),
        held("example", 51.9, 65.9, L("This film went through the same check.",
                                      "Ce film est passé par le même contrôle.")),
        cta("video"),
    ],
    opening(L("This one is about videos, like this one.", "Ici, on parle de vidéos, comme celle-ci."))
    + [
        (8.0, L("A video says things, and burns them into pixels.",
                "Une vidéo affirme des choses, et les grave dans les pixels.")),
        (12.6, L("Nobody reads them again, even when they stop being true.",
                 "Personne ne les relit, même quand elles ne sont plus vraies.")),
        (20.4, L("This suite once showed a number that was months out of date.",
                 "Cette suite a déjà affiché un nombre périmé depuis des mois.")),
        (26.6, L("The code had moved on. The film had not.",
                 "Le code avait changé. Le film, non.")),
        (31.8, L("Now every film is checked against the code before it ships.",
                 "Désormais, chaque film est vérifié contre le code avant de sortir.")),
        (40.4, L("The secret: every number on screen must point to the code that proves it.",
                 "Le secret : chaque nombre à l'écran doit pointer vers le code qui le prouve.")),
        (46.0, L("A number with nothing behind it is flagged before anyone sees it.",
                 "Un nombre sans rien derrière est signalé avant que quiconque le voie.")),
        (52.4, L("This very film went through the same check.",
                 "Ce film-ci est passé par le même contrôle.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 20.4), ("wipe", 31.6), ("wipe", 39.9), ("bell", 66.0)],
)

# ================================================================ sprezzature
film(
    "sprezzature",
    [
        what("sprezzature", L("Design know-how, written as code.", "Le savoir-faire du design, écrit en code.")),
        held("problem", 7.4, 19.9, L("Good design is already written down.", "Le bon design est déjà écrit.")),
        dict(type="grid", beat="solution", start=19.9, dur=13.1, end=32.9,
             eyebrow=L("Charts, maps, colours, pages", "Graphiques, cartes, couleurs, pages"),
             images=["figures/corr-matrix.svg", "figures/calendar-heatmap.svg", "figures/map-flow.svg",
                     "figures/choropleth.svg", "maps/situation-western-europe.png", "figures/cvd/00-original.png"],
             at=[21.0, 21.8, 22.6, 23.4, 24.2, 25.0]),
        dict(type="versus", beat="solution", start=32.9, dur=12.1, end=44.9,
             eyebrow=L("The same rules, used twice", "Les mêmes règles, deux fois"),
             left=(L("Make", "Fabriquer"), L("a chart, a map, a palette, a page",
                                              "un graphique, une carte, une palette, une page")),
             right=(L("Audit", "Auditer"), L("the same rules, on what is already live",
                                              "les mêmes règles, sur ce qui est déjà en ligne")),
             at=[33.8, 37.2]),
        dict(type="loop", beat="magic", start=44.9, dur=13.1, end=57.9,
             eyebrow=L("The Ralph Eyeball Loop", "La boucle Ralph Eyeball"),
             steps=LOOP_STEPS, fig="figures/bar-grouped.svg", gray="figures/bar-grouped-gray.svg",
             ratio=745 / 505, step_at=[46.0, 47.2, 48.4, 49.6], wipe_at=52.4, wipe_dur=1.09,
             caption_at=54.4,
             caption=L("A model looks at the picture. The code gets fixed.",
                       "Un modèle regarde l'image. C'est le code qu'on corrige.")),
        held("example", 57.9, 65.9, L("Everything stays on your machine.", "Tout reste sur votre machine.")),
        cta("sprezzature"),
    ],
    opening(L("10 tools, to make good design and to check it.",
              "Dix outils, pour faire du bon design et le vérifier."))
    + [
        (8.0, L("Most design rules were written down by experts, years ago.",
                "La plupart des règles du design ont été écrites par des experts, il y a des années.")),
        (13.2, L("Contrast, colour blindness, the laws of attention. Your tools ignore all of it.",
                 "Le contraste, le daltonisme, les lois de l'attention. Vos outils les ignorent.")),
        (20.4, L("This suite turns those rules into tools.", "Cette suite transforme ces règles en outils.")),
        (25.4, L("Charts, maps, colours, captions, pages and forms.",
                 "Graphiques, cartes, couleurs, sous-titres, pages et formulaires.")),
        (33.4, L("The same rules work both ways.", "Les mêmes règles servent dans les deux sens.")),
        (37.0, L("To make something new, and to check what is already online.",
                 "Pour fabriquer du neuf, et pour vérifier ce qui est déjà en ligne.")),
        (45.4, L("And the one thing no rule can do: look at the result.",
                 "Et la seule chose qu'aucune règle ne sait faire : regarder le résultat.")),
        (50.0, L("A model on your machine looks at the picture, like a designer would.",
                 "Un modèle sur votre machine regarde l'image, comme le ferait un designer.")),
        (54.6, L("What gets fixed is the code, never the picture.",
                 "Ce qu'on corrige, c'est le code, jamais l'image.")),
        (58.4, L("Everything runs on your own machine. Nothing is sent anywhere.",
                 "Tout tourne sur votre machine. Rien n'est envoyé nulle part.")),
    ]
    + closing(),
    [("drop", 7.6), ("tile", 21.0), ("wipe", 33.8), ("wipe", 52.4), ("bell", 66.0)],
)


# ===================================================================== French
# The French voice, written rather than translated (2026-11-06). The first
# draft above mirrored the English line for line, and `calque` scored all
# eleven at 1.00: same number of lines, same sentences, same numerals in the
# same places. These are cut to the French sentence instead, which runs
# longer and joins what English says in two.
TAG_FR = "Sprezzature est un moteur d'IA pour le design"
CLOSE_FR = [
    (66.0, "Si ça vous aide, une étoile sur GitHub, et toute la suite sur sprezzature.ai."),
    (71.6, "Faites, auditez, et regardez."),
]
FRENCH: dict[str, list[tuple[float, str]]] = {
    "colors": [
        (1.1, f"{TAG_FR}, et ce film parle de couleur."),
        (8.0, "Voici une carte de réservation aux couleurs pastel, très jolie sur l'écran du bureau."),
        (14.8, "Dehors, en plein soleil, le texte s'évanouit."),
        (20.4, "Celui qui a choisi la couleur la lit toujours très bien : c'est tout le piège."),
        (26.6, "Et 1 homme sur 12 confond le rouge et le vert."),
        (33.4, "Ici, chaque paire de couleurs est contrôlée."),
        (36.8, "Les plus faibles sont corrigées, en gardant le même bleu et le même gris, juste assez profonds pour se lire."),
        (45.4, "Le secret tient en une phrase : le daltonisme efface la teinte, jamais la clarté."),
        (50.6, "La correction ne touche donc qu'à la clarté, et votre marque reste la vôtre."),
        (55.4, "Le même graphique, vu par 4 regards : les couleurs changent, les barres restent distinctes."),
    ] + CLOSE_FR,
    "figures": [
        (1.1, f"{TAG_FR}, et ce film parle de graphiques."),
        (8.0, "Un tableur ouvert, aucune idée du bon graphique, et l'on refait l'histogramme de la dernière fois."),
        (20.4, "Ici, 167 types de graphiques vous attendent : flux, réseaux, distributions, cartes."),
        (27.0, "Ils sont rangés du plus lisible au moins lisible."),
        (33.4, "Chacun est dessiné à la main, trait par trait, en vrai fichier vectoriel."),
        (38.8, "Le texte reste du texte : on le sélectionne, on le cherche, on l'entend."),
        (45.4, "Le secret ? Chaque type déclare les données dont il a besoin."),
        (49.6, "Ce sont donc vos colonnes qui choisissent, sans rien laisser au hasard."),
        (55.4, "Le résultat se lit comme une page, et non comme une capture d'écran."),
    ] + CLOSE_FR,
    "maps": [
        (1.1, f"{TAG_FR}, et ce film parle de cartes."),
        (8.0, "Un tableau de pays cache où les choses se passent, et la plupart des cartes posent le même petit point partout."),
        (20.4, "Ici, tout part du vrai terrain."),
        (23.0, "Montagnes, rivières, lacs : chaque trait vient de notre code, sur une projection choisie pour la région."),
        (33.4, "Puis l'histoire se pose dessus : qui tient quoi, et où, avec la légende rangée dans le coin calme."),
        (45.4, "Le secret : les données de conflit disent à quel point chaque lieu est précis."),
        (50.0, "Un lieu sûr reçoit un point plein ; un lieu approximatif, un simple cercle."),
        (55.4, "4 acteurs, une légende claire, et un pays qu'on reconnaît d'un coup d'œil."),
    ] + CLOSE_FR,
    "ux-laws": [
        (1.1, f"{TAG_FR}, et ce film parle de l'expérience d'une page."),
        (8.0, "On vous dira qu'une page étouffe, jamais quelle loi du design elle enfreint."),
        (20.4, "Voici deux fois le même menu."),
        (23.4, "Plus il y a de choix à la fois, plus on hésite : c'est la loi de Hick."),
        (33.4, "La suite connaît 30 lois de l'expérience utilisateur, et en vérifie 8 directement dans la page, en une seconde."),
        (45.4, "Le secret : elle compte ce qu'une personne voit à un instant donné."),
        (50.0, "Le menu du téléphone et celui de l'ordinateur ne s'additionnent jamais."),
        (55.4, "C'est un contrôle rapide, pas un designer : la page répond-elle à la bonne question ? Ça, c'est vous qui le décidez."),
    ] + CLOSE_FR,
    "accessibility": [
        (1.1, f"{TAG_FR}, et ce film parle d'accessibilité."),
        (8.0, "Une lectrice aveugle parcourt votre page avec un lecteur d'écran. Devant ce portrait, elle n'entend qu'un mot : image."),
        (20.4, "Ou bien une vidéo démarre seule, avec le son, et couvre le lecteur d'écran qui l'aiderait à l'arrêter."),
        (33.4, "La suite lit votre page et contrôle 20 règles."),
        (37.0, "Elle en répare 6 toute seule, là où une seule réparation est sûre."),
        (45.4, "Pour les descriptions manquantes, un modèle sur votre machine regarde l'image et lit la page autour."),
        (60.4, "C'est un premier jet, dont vous restez l'éditeur."),
    ] + CLOSE_FR,
    "audio": [
        (1.1, f"{TAG_FR}, et ce film parle de son."),
        (8.0, "Votre vidéo a des sous-titres justes, mot pour mot."),
        (12.0, "Mais une longue ligne qui file en un éclair, personne ne la lit, et la justesse était tout ce qu'on mesurait."),
        (25.8, "Ici, les sous-titres suivent les règles du métier : 2 lignes au plus, et le temps de les lire."),
        (33.6, "L'outil sait aussi qui parle et traduit les sous-titres, sans qu'aucun son ne quitte votre machine."),
        (45.4, "Et dans l'autre sens, il lit un texte à voix haute."),
        (49.4, "La voix arrive avec ses sous-titres minutés, exactement comme ce film."),
        (55.4, "De la parole au texte, du texte à la parole : un seul outil."),
    ] + CLOSE_FR,
    "cli-gui": [
        (1.1, f"{TAG_FR}, et ce film parle de ligne de commande."),
        (8.0, "Votre collègue a besoin de votre outil, mais n'ouvrira jamais un terminal."),
        (13.0, "Il ne retiendra pas les options."),
        (20.4, "Ici, la commande fabrique sa propre page : chaque option devient un champ, chaque choix une liste."),
        (31.4, "Votre collègue remplit, et récupère la commande exacte."),
        (40.4, "Le secret : la page lit la définition même de l'outil, pas son texte d'aide."),
        (46.0, "Elle ne peut donc jamais afficher une option qui n'existe pas."),
        (52.4, "Un seul fichier, rien à installer, rien à héberger, et rien n'est exécuté : la page écrit la commande, c'est tout."),
    ] + CLOSE_FR,
    "ui": [
        (1.1, f"{TAG_FR}, et ce film parle d'interfaces."),
        (8.0, "Une phrase tapée directement dans une page ne coûte rien aujourd'hui, et une semaine le jour où il faut une deuxième langue."),
        (20.4, "Ici, chaque phrase vit dans un seul catalogue."),
        (24.4, "Le même écran passe d'une langue à l'autre, et le design ne bouge pas."),
        (30.0, "Anglais, français, allemand : tout tient."),
        (40.4, "L'audit repère chaque phrase qui devrait être au catalogue, puis s'arrête et laisse l'auteur trancher, sans jamais deviner."),
        (52.4, "Le même soin va dans chaque composant : une famille de polices, un focus visible, un mode sombre qui marche."),
    ] + CLOSE_FR,
    "publish": [
        (1.1, f"{TAG_FR}, et ce film parle de publication."),
        (8.0, "Vous avez écrit une bonne page, mais ni les moteurs de recherche ni les assistants ne la trouvent."),
        (14.0, "Et personne ne la partage."),
        (20.4, "Ici, vos fichiers texte deviennent un vrai site, avec ses cartes de partage, ses icônes, et ce que lisent les moteurs."),
        (34.4, "La page peut même se lire à voix haute, en surlignant chaque phrase."),
        (44.4, "Le secret : la voix et la page sont vérifiées l'une contre l'autre, et au moindre écart, l'outil refuse."),
        (55.4, "Voici sa propre documentation, lue et publiée par lui-même."),
    ] + CLOSE_FR,
    "video": [
        (1.1, f"{TAG_FR}, et ce film parle de vidéos, comme celle-ci."),
        (8.0, "Une vidéo grave ses affirmations dans les pixels, et personne ne les relit, même devenues fausses."),
        (20.4, "Cette suite a affiché un nombre périmé pendant des mois : le code avait changé, le film non."),
        (31.8, "Désormais, chaque film est vérifié contre le code avant de sortir."),
        (40.4, "Le secret : chaque nombre à l'écran doit pointer vers le code qui le prouve."),
        (45.4, "Sinon, il est signalé avant que quiconque le voie."),
        (52.4, "Ce film-ci est passé par le même contrôle."),
    ] + CLOSE_FR,
    "sprezzature": [
        (1.1, f"{TAG_FR} : 10 outils pour faire du bon design, et le vérifier."),
        (8.0, "Les règles du design ont été écrites par des experts, il y a des années : le contraste, le daltonisme, les lois de l'attention."),
        (15.6, "Vos outils les ignorent."),
        (20.4, "Cette suite en fait des outils, pour les graphiques, les cartes, les couleurs, les sous-titres, les pages et les formulaires."),
        (33.4, "Les mêmes règles servent deux fois : pour fabriquer du neuf, et pour vérifier ce qui est déjà en ligne."),
        (45.4, "Reste ce qu'aucune règle ne sait faire : regarder le résultat."),
        (49.6, "Un modèle sur votre machine regarde l'image, comme un designer, et c'est le code qu'on corrige, jamais l'image."),
        (58.4, "Tout tourne chez vous, et rien n'est envoyé nulle part."),
    ] + CLOSE_FR,
}
for _name, _lines in FRENCH.items():
    VOICE[_name]["fr"] = _lines

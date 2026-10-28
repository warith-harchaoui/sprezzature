#!/usr/bin/env python3
"""Write films.html and fr/films.html from one source of truth.

The header and footer are lifted from an existing page of the same language so
the two versions never drift apart, which is the house rule for this site.

Run from anywhere:  python3 scripts/build_films_page.py
"""

from __future__ import annotations

import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent / "web"

FILMS: list[dict[str, str | int]] = [
    # One film per brick, plus the suite. Re-cut at sixty seconds on
    # 2026-10-26, replacing the four films of the first set -- a suite film and
    # three that grouped bricks by theme. Grouping was the wrong axis: the
    # `interface` film had to speak for ui, cli-gui, publish and ux-laws in
    # eighteen seconds, so it said something general about all four and nothing
    # particular about any. A brick gets a minute of its own, or it gets a
    # sentence in somebody else's film.
    dict(slug="sprezzature", secs=60,
         en_title="Sprezzature", fr_title="Sprezzature",
         en_kicker="the whole suite", fr_kicker="la suite entière",
         en_body="Design is know-how, and most of it is already written down: "
                 "thirty laws of UX, contrast ratios, a 2009 paper on colour "
                 "vision, a projection from 2018. The suite is what happens when "
                 "you point that know-how both ways — at making a thing, and at "
                 "auditing it.",
         fr_body="Le design est un savoir-faire, et l'essentiel est déjà écrit : "
                 "trente lois d'UX, des rapports de contraste, un article de 2009 "
                 "sur la vision des couleurs, une projection de 2018. La suite, "
                 "c'est ce savoir-faire retourné dans les deux sens : pour "
                 "fabriquer une chose, et pour l'auditer.",
         en_shows="eight sources named, four real outputs, the Ralph Eyeball Loop "
                  "running on a shipped figure, and what ten packages add up to",
         fr_shows="huit sources nommées, quatre sorties réelles, la boucle Ralph "
                  "sur une figure livrée, et ce que font dix paquets mis bout à bout"),
    dict(slug="ui", secs=60,
         en_title="UI", fr_title="UI",
         en_kicker="sprezzature-ui", fr_kicker="sprezzature-ui",
         en_body="The smallest brick, on purpose. Its job is the aesthetic "
                 "judgement written in prose — the three-Roboto rule, the design "
                 "tokens, what an interface has to respect — plus the one part of "
                 "that judgement a machine can carry out.",
         fr_body="La plus petite brique, exprès. Son travail, c'est le jugement "
                 "esthétique écrit en prose — la règle des trois Roboto, les "
                 "jetons de design, ce qu'une interface doit respecter — plus la "
                 "seule part de ce jugement qu'une machine peut exécuter.",
         en_shows="the best cost sentence in the suite, in two halves, and what "
                  "the package ships: nine components, nine snippets, six font files",
         fr_shows="la meilleure phrase sur le coût de toute la suite, en deux "
                  "moitiés, et ce que le paquet livre : neuf composants, neuf "
                  "extraits, six fichiers de fonte"),
    dict(slug="cli-gui", secs=60,
         en_title="CLI &rarr; GUI", fr_title="CLI &rarr; GUI",
         en_kicker="sprezzature-cli-gui", fr_kicker="sprezzature-cli-gui",
         en_body="A tool nobody will type, wrapped in a page. It does not read "
                 "the help text — it reads the parser object, through argparse, "
                 "Click or Typer, and falls back to running "
                 "<code class=\"font-mono text-sm\">--help</code> only when there "
                 "is no parser to reach.",
         fr_body="Un outil que personne ne tapera, enveloppé dans une page. Il ne "
                 "lit pas le texte d'aide : il lit l'objet analyseur, via "
                 "argparse, Click ou Typer, et ne se rabat sur "
                 "<code class=\"font-mono text-sm\">--help</code> que faute "
                 "d'analyseur joignable.",
         en_shows="two captures of the page it generates for "
                  "<code class=\"font-mono text-sm\">make-figure</code>, taken "
                  "from the command that is installed rather than from a mock-up",
         fr_shows="deux captures de la page qu'il génère pour "
                  "<code class=\"font-mono text-sm\">make-figure</code>, prises "
                  "depuis la commande réellement installée, pas d'une maquette"),
    dict(slug="publish", secs=60,
         en_title="Publish", fr_title="Publier",
         en_kicker="sprezzature-publish", fr_kicker="sprezzature-publish",
         en_body="A document, becoming a site. Nine tools: a linter that runs on "
                 "the standard library in milliseconds, favicons from one logo, "
                 "the indexes a crawler and a language model both want, and "
                 "readalong, which binds the narration to the page.",
         fr_body="Un document, qui devient un site. Neuf outils : un linter qui "
                 "tourne sur la bibliothèque standard en millisecondes, des "
                 "favicons depuis un seul logo, les index qu'attendent un robot "
                 "comme un modèle de langue, et readalong, qui lie la narration à "
                 "la page.",
         en_shows="all nine named, then the boundary the package keeps — the "
                  "voices live in sprezzature-audio and are called as a subprocess",
         fr_shows="les neuf nommés, puis la frontière que le paquet tient : les "
                  "voix vivent dans sprezzature-audio et sont appelées en "
                  "sous-processus"),
    dict(slug="accessibility", secs=60,
         en_title="Accessibility", fr_title="Accessibilité",
         en_kicker="sprezzature-accessibility", fr_kicker="sprezzature-accessibility",
         en_body="An unmuted autoplay masks a screen reader, and the markup says "
                 "so on its own. Twenty rules from WCAG, each naming the element, "
                 "the line and the rule it broke; six of them repair themselves, "
                 "where there is exactly one safe repair.",
         fr_body="Une lecture automatique non muette couvre un lecteur d'écran, "
                 "et le balisage le dit tout seul. Vingt règles issues des WCAG, "
                 "chacune nommant l'élément, la ligne et la règle enfreinte ; six "
                 "se réparent seules, là où il n'existe qu'une correction sûre.",
         en_shows="three findings the source alone can prove, what "
                  "<code class=\"font-mono text-sm\">--fix</code> is allowed to "
                  "touch, and the same rule pointed the other way, writing the CSS",
         fr_shows="trois constats que la source seule peut prouver, ce que "
                  "<code class=\"font-mono text-sm\">--fix</code> a le droit de "
                  "toucher, et la même règle retournée, qui écrit le CSS"),
    dict(slug="colors", secs=60,
         en_title="Colors", fr_title="Couleurs",
         en_kicker="sprezzature-colors", fr_kicker="sprezzature-colors",
         en_body="Light grey on white reads fine — to you, indoors. About one man "
                 "in twelve sees red and green as the same bar, and no amount of "
                 "care changes that, because the information is not in their eye.",
         fr_body="Du gris clair sur blanc se lit très bien — pour vous, à "
                 "l'intérieur. Environ un homme sur douze voit le rouge et le "
                 "vert comme une seule barre, et aucun soin n'y change rien : "
                 "l'information n'est pas dans son œil.",
         en_shows="all four simulations in turn, produced by the project's own "
                  "<code class=\"font-mono text-sm\">simulate_cvd.py</code> from "
                  "the Machado matrices: protanopia, deuteranopia, tritanopia, "
                  "grayscale",
         fr_shows="les quatre simulations l'une après l'autre, produites par le "
                  "<code class=\"font-mono text-sm\">simulate_cvd.py</code> du "
                  "projet à partir des matrices de Machado : protanopie, "
                  "deutéranopie, tritanopie, niveaux de gris"),
    dict(slug="audio", secs=60,
         en_title="Audio", fr_title="Audio",
         en_kicker="sprezzature-audio", fr_kicker="sprezzature-audio",
         en_body="One modality, read in both directions. Captions turn sound into "
                 "timed text; narration turns text into timed sound, landing as a "
                 "WAV plus a WebVTT — exactly like a transcript does, which is "
                 "what lets a page follow the reading sentence by sentence.",
         fr_body="Une seule modalité, lue dans les deux sens. Les sous-titres "
                 "font du son un texte minuté ; la narration fait du texte un son "
                 "minuté, livré en WAV plus un WebVTT — exactement comme une "
                 "transcription, ce qui permet à une page de suivre la lecture "
                 "phrase après phrase.",
         en_shows="the models named, the two files narration lands as, and what "
                  "<code class=\"font-mono text-sm\">audit_captions</code> "
                  "measures about a track that is present but unreadable",
         fr_shows="les modèles nommés, les deux fichiers que produit la "
                  "narration, et ce que mesure "
                  "<code class=\"font-mono text-sm\">audit_captions</code> sur "
                  "une piste présente mais illisible"),
    dict(slug="ux-laws", secs=60,
         en_title="Laws of UX", fr_title="Lois de l'UX",
         en_kicker="sprezzature-ux-laws", fr_kicker="sprezzature-ux-laws",
         en_body="Nobody says &ldquo;that violates Hick&rsquo;s Law&rdquo;. They "
                 "say the page is overwhelming, or that they can never find the "
                 "button. Thirty laws, curated by Jon YABLONSKI; eight of them a "
                 "machine can decide from the markup alone.",
         fr_body="Personne ne dit &laquo;&nbsp;ça viole la loi de Hick&nbsp;"
                 "&raquo;. On dit que la page est écrasante, ou qu'on ne trouve "
                 "jamais le bouton. Trente lois, réunies par Jon YABLONSKI ; huit "
                 "qu'une machine peut trancher depuis le seul balisage.",
         en_shows="the eight the auditor checks, three findings it can state "
                  "exactly, and the boundary it does not cross — whether the "
                  "screen answers the right question stays a human call",
         fr_shows="les huit que l'auditeur vérifie, trois constats qu'il peut "
                  "énoncer exactement, et la frontière qu'il ne franchit pas : "
                  "savoir si l'écran répond à la bonne question reste humain"),
    dict(slug="figures", secs=60,
         en_title="Figures", fr_title="Figures",
         en_kicker="sprezzature-figures", fr_kicker="sprezzature-figures",
         en_body="167 kinds of chart across 52 categories, every one "
                 "hand-authored. No charting library sits underneath any of it: "
                 "each generator writes the SVG markup itself, and the vector is "
                 "the deliverable rather than an export.",
         fr_body="167 types de graphiques en 52 catégories, tous écrits à la "
                 "main. Aucune bibliothèque de tracé en dessous : chaque "
                 "générateur écrit le SVG lui-même, et le vectoriel est le "
                 "livrable, pas un export.",
         en_shows="ten real figures from the gallery, the categories nobody else "
                  "ships, and the Ralph Eyeball Loop with fourteen seconds to "
                  "show its work",
         fr_shows="dix figures réelles de la galerie, les catégories que personne "
                  "d'autre ne livre, et la boucle Ralph avec quatorze secondes "
                  "pour se montrer"),
    dict(slug="maps", secs=60,
         en_title="Maps", fr_title="Cartes",
         en_kicker="sprezzature-maps", fr_kicker="sprezzature-maps",
         en_body="A column of countries is a map waiting to happen. Real "
                 "coastlines, a real projection, eight kilometres of relief — and "
                 "a choice about which distortion you are willing to accept, "
                 "stated rather than defaulted to.",
         fr_body="Une colonne de pays est une carte qui s'ignore. De vraies "
                 "côtes, une vraie projection, huit kilomètres de relief — et un "
                 "choix de distorsion assumé plutôt que subi.",
         en_shows="two areas-of-control plates, with a ring where the source "
                  "gave no exact position, and the density map, which draws no "
                  "coastline at all and still reads as land",
         fr_shows="deux planches de zones de contrôle, avec un anneau là où la "
                  "source n'a donné aucune position exacte, et la carte de "
                  "densité, qui ne dessine aucune côte et se lit pourtant "
                  "comme une terre"),
    dict(slug="video", secs=60,
         en_title="Video", fr_title="Vidéo",
         en_kicker="sprezzature-video", fr_kicker="sprezzature-video",
         en_body="The brick that made the other ten films, and the one that "
                 "checks them. A film is a claim with a soundtrack: every number "
                 "on screen is verified against the code that produces it, "
                 "including the numbers nobody declared.",
         fr_body="La brique qui a fabriqué les dix autres films, et celle qui les "
                 "vérifie. Un film est une affirmation avec une bande-son : "
                 "chaque nombre à l'écran est vérifié contre le code qui le "
                 "produit, y compris ceux que personne n'a déclarés.",
         en_shows="the two kinds of claim, the three provenance classes an asset "
                  "can have, and why captions are measured off the voice file "
                  "rather than guessed",
         fr_shows="les deux sortes d'affirmation, les trois classes de provenance "
                  "d'une ressource, et pourquoi les sous-titres sont mesurés sur "
                  "le fichier de voix plutôt que devinés"),
]

COPY: dict[str, dict[str, Any]] = {
    "en": dict(
        lang="en", vdir="video", jsdir="js", other="fr/films.html",
        og_locale="en_US", og_locale_alt="fr_FR", skip="Skip to content",
        og_image_alt="A title card for the Ralph Eyeball Loop: a grouped bar chart of sales by region and quarter, drawn in grey on its left half and in colour on its right, beside the four steps of the loop — render, look, fix the source, again.",
        title="Eleven short films — Sprezzature",
        desc="Eleven short films about Sprezzature: one on the suite, and one for "
             "each of its ten packages. Every figure, map, form and simulation "
             "in them is real output from the tools themselves.",
        h1="Eleven short films",
        lede="One on the suite, and one for each of its ten packages. Nothing in "
             "them is a mock-up: the figures are the shipped SVG files, the maps "
             "are drawn on a real projection, the form was generated from the "
             "command that is installed, and the colour vision simulations came "
             "out of <code class=\"font-mono text-sm\">sprezzature-colors</code>.",
        captions_label="English",
        shows_label="What it shows",
        note_h="About these films",
        note=[
            "Each film exists twice, and the two do not mix: an English film "
            "is English throughout — on screen, in the voice, in the "
            "subtitles — and a French film is French throughout. This page "
            "serves the English cut; the French one is a click away.",
            "The voices come from the suite itself: "
            "<code class=\"font-mono text-sm\">sprezzature-audio</code> "
            "through Kokoro, with a pronunciation lexicon so that WebVTT, "
            "RTTM, OKLCH and GMTED2010 are said the same way in every film "
            "and in both languages. The same call writes the subtitles, off "
            "the same timeline as the audio.",
            "Each film is cut three ways and all three are on this page: "
            "wide for a screen, tall for a phone held upright, square for a "
            "feed. Pick one above the player. The three are frame-synced, so "
            "the same sentence lands on the same second whichever you watch; "
            "only the layout moves. All of them are 4K.",
            "They follow Guy KAWASAKI\u2019s order, which is why the rail "
            "above each frame says where you are: what the thing is, then the "
            "problem, then what the package does about it, then the part you "
            "would not guess \u2014 and the sources it rests on, named so you "
            "can go and check them. The first frame is already a finished one: "
            "the name, one sentence, and where to find it.",
            "They were built with the same discipline they describe. Every "
            "scene was rendered to a still and looked at before the film was "
            "encoded, which is how the sixty-second set was caught quoting a "
            "catalogue size the package had outgrown months earlier — off a "
            "screenshot taken in September — naming a font the package does not "
            "ship, and counting twelve font files where there are six.",
            "Two of those were typography rather than fact, and they now have a "
            "test instead of an eye: it measures every line of film text in the "
            "font the films are set in, and fails if one wraps and leaves its "
            "last word standing alone.",
        ],
        fallback="Your browser cannot play this video.",
        download="Download the MP4",
        secs_word="s",
        format_label="Pick a shape",
        formats=[("landscape", "Landscape", "3840&times;2160"),
                 ("portrait", "Portrait", "2160&times;3840"),
                 ("square", "Square", "2160&times;2160")],
    ),
    "fr": dict(
        lang="fr", vdir="../video", jsdir="../js", other="../films.html",
        og_locale="fr_FR", og_locale_alt="en_US", skip="Aller au contenu",
        og_image_alt="Une carte-titre de la Ralph Eyeball Loop : un histogramme groupé des ventes par région et par trimestre, dessiné en gris sur sa moitié gauche et en couleur sur sa droite, à côté des quatre étapes de la boucle — dessiner, regarder, corriger la source, recommencer.",
        title="Onze courts métrages — Sprezzature",
        desc="Onze courts métrages sur Sprezzature : un sur la suite, et un par "
             "paquet. Chaque figure, carte, formulaire et simulation qu'on y voit "
             "sort réellement des outils.",
        h1="Onze courts métrages",
        lede="Un sur la suite, et un par paquet. Rien n'y est une maquette : les "
             "figures sont les fichiers SVG livrés, les cartes sont tracées sur "
             "une vraie projection, le formulaire a été produit depuis la "
             "commande réellement installée, et les simulations de vision des "
             "couleurs sortent de <code class=\"font-mono text-sm\">"
             "sprezzature-colors</code>.",
        captions_label="Français",
        shows_label="Ce qu'on y voit",
        note_h="À propos de ces films",
        note=[
            "Chaque film existe deux fois, et les deux ne se mélangent pas : "
            "un film anglais est anglais de bout en bout — à l'écran, dans "
            "la voix, dans les sous-titres — et un film français est français "
            "de bout en bout. Cette page sert la version française ; "
            "l'anglaise est à un clic.",
            "Les voix viennent de la suite elle-même : "
            "<code class=\"font-mono text-sm\">sprezzature-audio</code> via "
            "Kokoro, avec un lexique de prononciation pour que WebVTT, RTTM, "
            "OKLCH et GMTED2010 se disent pareil dans tous les films et dans "
            "les deux langues. Le même appel écrit les sous-titres, sur la "
            "même timeline que l'audio.",
            "Chaque film est monté trois fois, et les trois sont sur cette "
            "page : large pour un écran, haut pour un téléphone tenu debout, "
            "carré pour un fil. Le choix est au-dessus du lecteur. Les trois "
            "partagent la même horloge : la même phrase tombe à la même "
            "seconde quel que soit le montage, seule la mise en page bouge. "
            "Tous sont en 4K.",
            "Ils suivent l\u2019ordre de Guy KAWASAKI, et c\u2019est "
            "pourquoi le bandeau au-dessus de l\u2019image dit où vous en "
            "êtes : ce que c\u2019est, puis le problème, puis ce que le paquet "
            "en fait, puis la part qu\u2019on ne devinerait pas \u2014 avec "
            "les sources sur lesquelles elle repose, nommées pour qu\u2019on "
            "puisse aller les vérifier. La première image est déjà une image "
            "finie : le nom, une phrase, et où le trouver.",
            "Ils ont été fabriqués avec la discipline qu'ils décrivent. Chaque "
            "plan a été rendu en image fixe et regardé avant l'encodage, ce qui a "
            "permis d'attraper la série d'une minute en train d'annoncer une "
            "taille de catalogue dépassée depuis des mois — d'après une capture "
            "de septembre —, de nommer une fonte que le paquet ne livre pas, et "
            "de compter douze fichiers de fonte là où il y en a six.",
            "Deux de ces défauts relevaient de la typographie plutôt que du "
            "fait, et ils ont désormais un test plutôt qu'un œil : il mesure "
            "chaque ligne de texte des films dans la fonte où ils sont composés, "
            "et échoue si l'une se coupe en laissant son dernier mot seul.",
        ],
        fallback="Votre navigateur ne peut pas lire cette vidéo.",
        download="Télécharger le MP4",
        secs_word="s",
        format_label="Choisissez un format",
        formats=[("landscape", "Paysage", "3840&times;2160"),
                 ("portrait", "Portrait", "2160&times;3840"),
                 ("square", "Carré", "2160&times;2160")],
    ),
}


def grab(path: pathlib.Path, tag: str) -> str:
    s = path.read_text(encoding="utf-8")
    m = re.search(rf"(<{tag}\b.*?</{tag}>)", s, re.S)
    assert m, f"{tag} not found in {path}"
    return m.group(1)


def player(film: dict[str, Any], c: dict[str, Any]) -> str:
    """The player for this page's cut of one film.

    Each film exists twice since 2026-10-26, and the two do not mix. A French
    film is French throughout: French on screen, French voice, French
    subtitles. An English film is English throughout. One language per film,
    end to end.

    That rule is why there is one ``<track>`` here and not two. Offering both
    looked generous — watch the French cut, read along in English — and it is
    the wrong offer: the subtitles would then be a translation of the voice
    rather than a transcript of it, disagreeing with every word on screen.
    A caption track that does not say what the film says is worse than no
    caption track, because a reader has no way to tell which one is wrong.
    """
    v, s, lang = c["vdir"], film["slug"], c["lang"]
    btns = "".join(
        f'''<button type="button" data-format="{key}" aria-pressed="{str(key == "landscape").lower()}"
              class="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-3 font-mono text-xs
                     uppercase tracking-wide text-neutral-600 hover:bg-neutral-100
                     focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue
                     aria-pressed:bg-brand-blue aria-pressed:text-white
                     dark:text-neutral-300 dark:hover:bg-neutral-800">{label}<span
              class="opacity-60">{dims}</span></button>'''
        for key, label, dims in c["formats"])
    return f'''<div class="mb-3 flex flex-wrap items-center gap-1" role="group" aria-label="{c['format_label']}"
            data-film-formats data-film="{s}" data-lang="{lang}" data-dir="{v}">{btns}</div>
          <video controls preload="none" width="3840" height="2160"
            data-film-player
            poster="{v}/{s}.{lang}.jpg"
            class="mx-auto max-h-[80vh] w-full rounded-2xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
            <source src="{v}/{s}.{lang}.mp4" type="video/mp4">
            <track kind="captions" src="{v}/{s}.{lang}.vtt" srclang="{lang}" label="{c['captions_label']}" default>
            <p class="p-4 text-sm text-neutral-600 dark:text-neutral-300">{c["fallback"]}
              <a class="text-brand-linktext underline hover:no-underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue" href="{v}/{s}.{lang}.mp4">{c["download"]}</a>.</p>
          </video>'''


def render(lang: str) -> str:
    """The page, as text. Writing it is :func:`build`'s job, not this one's.

    Split apart so a test can ask "does the file on disk still equal what this
    generator produces" without the test having to write over the site to find
    out. The two had drifted: the page said "the nine skills" and carried an
    ``og:image:alt``; re-running the generator put "the ten" back and dropped
    the alt, which turned two of this repository's own tests red. A generated
    file that cannot be regenerated is a hand-written file with a misleading
    header.
    """
    c = COPY[lang]
    src = ROOT / ("fr/ralph-eyeball-loop.html" if lang == "fr" else "ralph-eyeball-loop.html")
    header = grab(src, "header")
    footer = grab(src, "footer")
    base = "https://sprezzature.ai/" + ("fr/" if lang == "fr" else "")
    prefix = "../" if lang == "fr" else ""

    sections = []
    for i, f in enumerate(FILMS):
        border = "" if i == 0 else " border-t border-neutral-200/70 dark:border-neutral-800"
        sections.append(f'''    <section id="{f['slug']}" class="mx-auto max-w-4xl px-5 py-14{border}">
      <p class="font-mono text-sm uppercase tracking-wide text-brand-linktext">{f[lang + '_kicker']}</p>
      <h2 class="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">{f[lang + '_title']}
        <span class="ml-2 font-mono text-base font-normal text-neutral-500 dark:text-neutral-400">{f['secs']}&nbsp;{c['secs_word']}</span></h2>
      <p class="mt-3 text-neutral-600 dark:text-neutral-300">{f[lang + '_body']}</p>
      <div class="mt-6">
          {player(f, c)}
      </div>
      <p class="mt-3 text-sm text-neutral-500 dark:text-neutral-400"><strong class="font-semibold">{c['shows_label']}:</strong> {f[lang + '_shows']}.</p>
    </section>''')

    notes = "".join(f'\n        <li>{n}</li>' for n in c["note"])

    html = f'''<!doctype html>
<html lang="{c['lang']}" data-color-scheme="light" data-color-mode="academic">
<head>
  <script>(function(){{var s;try{{s=localStorage.getItem('sprezzature-color-mode');}}catch(e){{}}
    document.documentElement.setAttribute('data-color-mode',s==='corporate'?'corporate':'academic');}})();</script>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{c['title']}</title>
  <meta name="description" content="{c['desc']}">
  <link rel="canonical" href="{base}films.html">
  <link rel="alternate" hreflang="en" href="https://sprezzature.ai/films.html">
  <link rel="alternate" hreflang="fr" href="https://sprezzature.ai/fr/films.html">
  <link rel="alternate" hreflang="x-default" href="https://sprezzature.ai/films.html">
  <meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0B0B0C" media="(prefers-color-scheme: dark)">
  <meta property="og:type" content="video.other">
  <meta property="og:title" content="{c['title']}">
  <meta property="og:description" content="{c['desc']}">
  <meta property="og:url" content="{base}films.html">
  <meta property="og:image" content="https://sprezzature.ai/video/sprezzature.{c['lang']}.jpg">
  <meta property="og:image:alt" content="{c['og_image_alt']}">
  <meta property="og:site_name" content="Sprezzature">
  <meta property="og:locale" content="{c['og_locale']}">
  <meta property="og:locale:alternate" content="{c['og_locale_alt']}">
  <meta property="og:image:width" content="3840">
  <meta property="og:image:height" content="2160">
  <meta property="og:video" content="https://sprezzature.ai/video/sprezzature.{c['lang']}.mp4">
  <meta property="og:video:type" content="video/mp4">
  <meta property="og:video:width" content="3840">
  <meta property="og:video:height" content="2160">
  <meta name="twitter:card" content="player">
  <meta name="twitter:title" content="{c['title']}">
  <meta name="twitter:description" content="{c['desc']}">
  <meta name="twitter:image" content="https://sprezzature.ai/video/sprezzature.{c['lang']}.jpg">
  <link rel="icon" href="{prefix}favicon.ico" sizes="any">
  <link rel="icon" href="{prefix}favicon-32.png" sizes="32x32" type="image/png">
  <link rel="apple-touch-icon" href="{prefix}apple-touch-icon.png" sizes="180x180">
  <link rel="preload" href="{prefix}fonts/roboto/Roboto-Variable.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="{prefix}fonts/roboto/fonts.css">
  <link rel="stylesheet" href="{prefix}fonts/roboto-serif/fonts.css">
  <link rel="stylesheet" href="{prefix}fonts/roboto-mono/fonts.css">
  <script>(function(){{var s;try{{s=localStorage.getItem('sprezzature-theme');}}catch(e){{}}
    if(!s)s=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
    document.documentElement.setAttribute('data-color-scheme',s);}})();</script>
  <link rel="stylesheet" href="{prefix}css/app.css">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@graph": [
      {{
        "@type": "WebPage",
        "name": "{c['title']}",
        "description": "{c['desc']}",
        "url": "{base}films.html",
        "inLanguage": "{c['lang']}",
        "author": {{"@type": "Person", "name": "Warith HARCHAOUI", "url": "https://www.linkedin.com/in/warith-harchaoui/"}}
      }},
      {{
        "@type": "VideoObject",
        "name": "Sprezzature",
        "description": "{c['desc']}",
        "thumbnailUrl": "https://sprezzature.ai/video/sprezzature.{c['lang']}.jpg",
        "contentUrl": "https://sprezzature.ai/video/sprezzature.{c['lang']}.mp4",
        "duration": "PT1M",
        "inLanguage": "{c['lang']}",
        "uploadDate": "2026-10-27",
        "author": {{"@type": "Person", "name": "Warith HARCHAOUI"}}
      }}
    ]
  }}
  </script>
  <style>
    :root {{ color-scheme: light dark; }}
    html {{ scroll-behavior: smooth; }}
    @media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior: auto; }} }}
  </style>
</head>

<body class="bg-white text-neutral-900 dark:bg-[#0B0B0C] dark:text-neutral-100 font-sans antialiased">
  <a href="#main"
    class="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-3 focus:left-3 focus:rounded-lg focus:bg-brand-blue focus:px-4 focus:py-2 focus:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue">{c['skip']}</a>

{header}

  <main id="main">
    <section class="mx-auto max-w-4xl px-5 pt-14 pb-4">
      <h1 class="font-serif text-4xl font-bold tracking-tight sm:text-5xl">{c['h1']}</h1>
      <p class="mt-4 text-lg text-neutral-600 dark:text-neutral-300">{c['lede']}</p>
    </section>

{chr(10).join(sections)}

    <section class="border-t border-neutral-200/70 dark:border-neutral-800">
      <div class="mx-auto max-w-4xl px-5 py-14">
        <h2 class="text-2xl font-bold tracking-tight sm:text-3xl">{c['note_h']}</h2>
        <ul class="mt-4 space-y-3 text-neutral-600 dark:text-neutral-300" role="list">{notes}
        </ul>
      </div>
    </section>
  </main>

{footer}
  <script src="{c['jsdir']}/theme.js" defer></script>
  <script src="{c['jsdir']}/nav.js" defer></script>
  <script src="{c['jsdir']}/color-mode.js" defer></script>
  <script src="{c['jsdir']}/film-format.js" defer></script>
</body>
</html>
'''
    return html


def page_path(lang: str) -> pathlib.Path:
    """Where :func:`render` output belongs."""
    return ROOT / ("fr/films.html" if lang == "fr" else "films.html")


def build(lang: str) -> pathlib.Path:
    """Write the rendered page where it belongs, and say where that was."""
    out = page_path(lang)
    out.write_text(render(lang), encoding="utf-8")
    print(out)
    return out


if __name__ == "__main__":
    build("en")
    build("fr")

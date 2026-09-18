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
    dict(slug="sprezzature", secs=25,
         en_title="Sprezzature", fr_title="Sprezzature",
         en_kicker="the whole suite", fr_kicker="la suite entière",
         en_body="A sentence can be proofread by reading it back. A chart cannot. "
                 "So the suite renders the figure, looks at it, looks again with "
                 "the colour taken away, and only then ships. The same discipline "
                 "runs one level up: before it trusts a local model, it seeds a "
                 "known flaw into a text and a known defect into an image, and "
                 "hires only the model that catches both.",
         fr_body="Une phrase se relit. Un graphique, non. La suite dessine donc la "
                 "figure, la regarde, la regarde encore une fois la couleur "
                 "retirée, et ne livre qu'ensuite. La même discipline vaut un "
                 "étage plus haut : avant de faire confiance à un modèle local, "
                 "elle sème un défaut connu dans un texte et un défaut visuel "
                 "connu dans une image, et n'engage que le modèle qui attrape "
                 "les deux.",
         en_shows="the shipped <code class=\"font-mono text-sm\">bar-grouped.svg</code>, "
                  "the ten skills, and the two gates the model has to pass",
         fr_shows="le fichier livré <code class=\"font-mono text-sm\">bar-grouped.svg</code>, "
                  "les dix skills, et les deux portes que le modèle doit franchir"),
    dict(slug="figures-et-cartes", secs=18,
         en_title="Figures &amp; maps", fr_title="Figures et cartes",
         en_kicker="sprezzature-figures · sprezzature-maps",
         fr_kicker="sprezzature-figures · sprezzature-maps",
         en_body="127 chart kinds and three map generators, every line written as "
                 "SVG directly. No plotting library sits underneath any of it, "
                 "and the SVG is the deliverable rather than an export.",
         fr_body="127 types de graphiques et trois générateurs de cartes, chaque "
                 "trait écrit directement en SVG. Aucune bibliothèque de tracé ne "
                 "se trouve dessous, et le SVG est le livrable plutôt qu'un export.",
         en_shows="six real figures from the gallery, then four real maps on a "
                  "genuine geographic projection",
         fr_shows="six vraies figures de la galerie, puis quatre vraies cartes sur "
                  "une vraie projection géographique"),
    dict(slug="accessibilite", secs=21,
         en_title="Accessibility", fr_title="Accessibilité",
         en_kicker="accessibility · colors · vision · audio",
         fr_kicker="accessibility · colors · vision · audio",
         en_body="A person with ordinary colour vision cannot see their own chart "
                 "the way a colour blind reader does, and no amount of care "
                 "changes that, because the information is not in their eye. The "
                 "simulator renders those other viewpoints so the loop can look "
                 "through them.",
         fr_body="Une personne qui voit normalement les couleurs ne peut pas voir "
                 "son propre graphique comme le voit un lecteur daltonien, et "
                 "aucun soin n'y change rien, parce que l'information n'est pas "
                 "dans son oeil. Le simulateur dessine ces points de vue pour que "
                 "la boucle puisse regarder à travers.",
         en_shows="all four simulations in turn, produced by the project's own "
                  "<code class=\"font-mono text-sm\">simulate_cvd.py</code>: protanopia, "
                  "deuteranopia, tritanopia, grayscale",
         fr_shows="les quatre simulations l'une après l'autre, produites par le "
                  "<code class=\"font-mono text-sm\">simulate_cvd.py</code> du projet : "
                  "protanopie, deutéranopie, tritanopie, niveaux de gris"),
    dict(slug="interface", secs=18,
         en_title="Interface", fr_title="Interface",
         en_kicker="ui · cli-gui · publish · ux-laws",
         fr_kicker="ui · cli-gui · publish · ux-laws",
         en_body="A command line is a wall for most people. Point this at an "
                 "argparse, Click or Typer parser and every flag becomes a field, "
                 "in one self-contained page.",
         fr_body="Une ligne de commande est un mur pour la plupart des gens. "
                 "Pointez ceci sur un analyseur argparse, Click ou Typer et chaque "
                 "option devient un champ, dans une page autonome.",
         en_shows="a page the tool actually generated from a real parser, scrolled "
                  "end to end so every field is shown",
         fr_shows="une page réellement produite par l'outil depuis un vrai "
                  "analyseur, défilée de bout en bout pour montrer tous les champs"),
    dict(slug="moteur-local", secs=18,
         en_title="The local engine", fr_title="Le moteur local",
         en_kicker="best-engine-ai-helper", fr_kicker="best-engine-ai-helper",
         en_body="Who checks the checker? Before a local model is trusted, it is "
                 "put through the same loop: a known flaw seeded into a text, a "
                 "known defect seeded into an image. Only a model that catches "
                 "both gets written to the engine file.",
         fr_body="Qui contrôle le contrôleur ? Avant qu'un modèle local ne soit "
                 "employé, il passe la même boucle : un défaut connu semé dans un "
                 "texte, un défaut visuel connu semé dans une image. Seul un "
                 "modèle qui attrape les deux est écrit dans le fichier moteur.",
         en_shows="the package's own interface, scrolled from the hardware read to "
                  "the model it recommends, then the two gates",
         fr_shows="l'interface du paquet, défilée de la lecture du matériel "
                  "jusqu'au modèle recommandé, puis les deux portes"),
]

COPY: dict[str, dict[str, Any]] = {
    "en": dict(
        lang="en", vdir="video", jsdir="js", other="fr/films.html",
        title="Five short films — Sprezzature",
        desc="Five short films about Sprezzature: one on the suite, four on what "
             "it is made of. Every figure, form and simulation in them is real "
             "output from the tools themselves.",
        h1="Five short films",
        lede="One on the suite, four on what it is made of. Nothing in them is a "
             "mock-up: the figures are the shipped SVG files, the form was "
             "generated by the tool from a real parser, and the colour vision "
             "simulations came out of <code class=\"font-mono text-sm\">"
             "sprezzature-colors</code>.",
        shows_label="What it shows",
        note_h="About these films",
        note=[
            "They are narrated in English. Subtitles are available in English and "
            "in French: pick them in the player's caption menu.",
            "Each one also exists vertical (1080&times;1920) and square "
            "(1080&times;1080). The versions here are the 1920&times;1080 cut.",
            "They were built with the same discipline they describe. Every frame "
            "was rendered to a still and looked at before the video was encoded, "
            "which is how seven defects that passed the automated checks were "
            "caught, including a caption sliding under a rule and a cropped chart "
            "title.",
        ],
        fallback="Your browser cannot play this video.",
        download="Download the MP4",
        nav="Films", secs_word="s",
    ),
    "fr": dict(
        lang="fr", vdir="../video", jsdir="../js", other="../films.html",
        title="Cinq courts films — Sprezzature",
        desc="Cinq courts films sur Sprezzature : un sur la suite, quatre sur ce "
             "dont elle est faite. Chaque figure, formulaire et simulation qu'on y "
             "voit sort réellement des outils.",
        h1="Cinq courts films",
        lede="Un sur la suite, quatre sur ce dont elle est faite. Rien n'y est une "
             "maquette : les figures sont les fichiers SVG livrés, le formulaire a "
             "été produit par l'outil depuis un vrai analyseur, et les simulations "
             "de vision des couleurs sortent de <code class=\"font-mono text-sm\">"
             "sprezzature-colors</code>.",
        shows_label="Ce qu'on y voit",
        note_h="À propos de ces films",
        note=[
            "Ils sont racontés en anglais. Les sous-titres existent en anglais et "
            "en français : choisissez-les dans le menu des sous-titres du lecteur.",
            "Chacun existe aussi en vertical (1080&times;1920) et en carré "
            "(1080&times;1080). Les versions ici sont le montage 1920&times;1080.",
            "Ils ont été fabriqués avec la discipline qu'ils décrivent. Chaque plan "
            "a été rendu en image fixe et regardé avant l'encodage, ce qui a permis "
            "d'attraper sept défauts que les contrôles automatiques laissaient "
            "passer, dont une légende glissant sous un filet et un titre de "
            "graphique recadré.",
        ],
        fallback="Votre navigateur ne peut pas lire cette vidéo.",
        download="Télécharger le MP4",
        nav="Films", secs_word="s",
    ),
}


def grab(path: pathlib.Path, tag: str) -> str:
    s = path.read_text(encoding="utf-8")
    m = re.search(rf"(<{tag}\b.*?</{tag}>)", s, re.S)
    assert m, f"{tag} not found in {path}"
    return m.group(1)


def add_nav_film(header: str, label: str, href: str) -> str:
    """Slot a Films entry next to the gallery link, in both navs.

    Idempotent: the source page it lifts the header from already carries the
    link, so re-running must not stack duplicates.
    """
    if f'href="{href}"' in header:
        return header
    out = header
    # Desktop nav, then the mobile list. Each new entry copies the classes of
    # the gallery link beside it, so the two stay styled alike.
    for pattern, template in (
        (r'<a href="figures\.html"[^>]*>(?:Gallery|Galerie)</a>',
         '\n        <a href="{href}" class="{cls}">{label}</a>'),
        (r'<li><a href="figures\.html"[^>]*>(?:Gallery|Galerie)</a></li>',
         '\n        <li><a href="{href}" class="{cls}">{label}</a></li>'),
    ):
        m = re.search(pattern, out, re.S)
        if m is None:
            continue
        cls_match = re.search(r'class="([^"]*)"', m.group(0))
        if cls_match is None:
            continue
        addition = template.format(href=href, cls=cls_match.group(1), label=label)
        out = out.replace(m.group(0), m.group(0) + addition, 1)
    return out


def player(film: dict[str, Any], c: dict[str, Any]) -> str:
    v, s = c["vdir"], film["slug"]
    return f'''<video controls preload="none" width="1920" height="1080"
            poster="{v}/{s}.jpg"
            class="w-full rounded-2xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
            <source src="{v}/{s}.mp4" type="video/mp4">
            <track kind="captions" src="{v}/{s}.en.vtt" srclang="en" label="English"{' default' if c['lang'] == 'en' else ''}>
            <track kind="captions" src="{v}/{s}.fr.vtt" srclang="fr" label="Français"{' default' if c['lang'] == 'fr' else ''}>
            <p class="p-4 text-sm text-neutral-600 dark:text-neutral-300">{c["fallback"]}
              <a class="text-brand-linktext underline hover:no-underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue" href="{v}/{s}.mp4">{c["download"]}</a>.</p>
          </video>'''


def build(lang: str) -> None:
    c = COPY[lang]
    src = ROOT / ("fr/ralph-eyeball-loop.html" if lang == "fr" else "ralph-eyeball-loop.html")
    header = add_nav_film(grab(src, "header"), c["nav"], "films.html")
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
  <meta property="og:image" content="https://sprezzature.ai/video/sprezzature.jpg">
  <meta property="og:video" content="https://sprezzature.ai/video/sprezzature.mp4">
  <meta property="og:video:type" content="video/mp4">
  <meta property="og:video:width" content="1920">
  <meta property="og:video:height" content="1080">
  <meta name="twitter:card" content="player">
  <meta name="twitter:title" content="{c['title']}">
  <meta name="twitter:description" content="{c['desc']}">
  <meta name="twitter:image" content="https://sprezzature.ai/video/sprezzature.jpg">
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
        "thumbnailUrl": "https://sprezzature.ai/video/sprezzature.jpg",
        "contentUrl": "https://sprezzature.ai/video/sprezzature.mp4",
        "duration": "PT25S",
        "inLanguage": "en",
        "uploadDate": "2026-09-18",
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
    class="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-3 focus:left-3 focus:rounded-lg focus:bg-brand-blue focus:px-4 focus:py-2 focus:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue">Skip
    to content</a>

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
</body>
</html>
'''
    out = ROOT / ("fr/films.html" if lang == "fr" else "films.html")
    out.write_text(html, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    build("en")
    build("fr")




# Sprezzature

[🇫🇷](LISEZMOI.md) · [🇬🇧](README.md)

<p align="center">
  <img src="assets/logo.png" alt="Sprezzature : dix skills Claude / OpenCode pour des frontends en JavaScript pur + Tailwind" width="240">
</p>

## De quoi s'agit-il ?

`sprezzature`, c'est **dix *skills* Claude / OpenCode** qui cadrent
l'agent sur une seule pile frontend (JavaScript (JS, le langage de programmation qu'exécutent les navigateurs) pur, Tailwind CSS (Cascading Style Sheets, le langage qui fixe les couleurs, les polices et la mise en page d'une page web),
et la règle des trois Roboto : Roboto pour les sans-serif, Roboto Serif
pour les serif, Roboto Mono pour le code) et lui fournissent un
système de design soigné.
Demander à l'agent de « construire une UI (User Interface, les écrans, boutons et formulaires qu'une personne utilise) », « habiller ce CLI (Command-Line Interface, un programme qu'on lance en tapant une commande dans un terminal) d'une
IHM (interface homme-machine, les fenêtres, boutons et formulaires sur lesquels on clique) », « transformer ce dossier de markdown en site » ou « auditer
l'accessibilité » oriente vers le bon *skill* et produit du code dans
la même pile : HTML (langage de balisage des pages web) sémantique,
variante `dark:` sur chaque élément
stylé, anneau de focus visible, garde-fous pour `prefers-reduced-motion`,
graphiques en SVG (Scalable Vector Graphics, une image faite de formes plutôt que de pixels, qui reste nette à tous les zooms) écrite à la main, texte alternatif rédigé selon les recommandations
du World Wide Web Consortium (W3C, l'organisme qui écrit les standards du web) et de sa Web Accessibility Initiative (WAI, son groupe chargé de l'accessibilité).

Les dix *skills* :

| *Skill* | Quand l'installer | Phrases déclencheuses |
|---|---|---|
| **sprezzature-ui** | Toujours : il porte les conventions de pile (base technique) et les variables de design (design tokens). | « construis une UI », « crée un composant », « conçois une page », « fais un formulaire / modal / bouton / nav », « tableau de bord », « audite cette UI ». |
| **sprezzature-cli-gui** | Vous habillez des outils en ligne de commande (CLI) d'une interface graphique (IHM, interface homme-machine). | « habille ce CLI d'une IHM », « construis une UI pour mon script Python », « argparse vers IHM web ». |
| **sprezzature-publish** | Vous livrez des sites de doc, des landings, des meta-tags, des favicons, ou un site dont les lecteurs doivent réserver, acheter ou installer : SEO (Search Engine Optimization, faire remonter un site en haut des résultats de Google), GEO (Generative Engine Optimization, faire d'un site la source que cite un assistant d'IA quand il répond), AEO (Answer Engine Optimization, faire d'une page la réponse qu'un moteur de recherche ou un assistant vocal lit à voix haute), cartes OG (Open Graph, l'aperçu d'un lien partagé). | « transforme ce dossier markdown en site », « meta tags », « SEO », « GEO », « AEO », « écris une FAQ », « favicons », « robots.txt », « sitemap », « llms.txt », « flux Atom », « langage clair », « réécris au niveau 6e ». |
| **sprezzature-accessibility** | Vous avez besoin d'un contrôle statique d'accessibilité (a11y), ou d'un brouillon de texte alternatif conforme aux recommandations du W3C rédigé en local depuis des images (pas de service en ligne / SaaS), vérifié selon les WCAG (Web Content Accessibility Guidelines, les règles internationales qu'une page web doit suivre pour être utilisable par les personnes handicapées). | « lint a11y », « vérif accessibilité HTML », « conformité WCAG », « alt manquant », « texte alternatif », « décris cette image », « champ sans label ». |
| **sprezzature-colors** | Vous auditez le contraste, simulez le daltonisme ou CVD (Colour Vision Deficiency, le nom médical du daltonisme : un rouge et un vert qui se confondent, par exemple) ou voulez une palette sélectionnée avec éclaircissement / assombrissement perceptuels dans OKLCH (une façon de numéroter les couleurs par luminosité, chroma et teinte, construite pour que des écarts égaux paraissent égaux à l'œil). | « vérif WCAG », « audit de contraste », « ma palette est-elle accessible », « aperçu daltonien », « deutéranope », « CVD », « OKLCH », « éclaircis cette couleur ». |
| **sprezzature-audio** | Vous rédigez un brouillon de sous-titres (formats WebVTT et SubRip (SRT, le fichier de sous-titres le plus répandu, des répliques numérotées avec un début et une fin)) pour `<video>` / `<audio>` en local, ou vous faites lire un texte par une voix locale (pas de SaaS). | « sous-titres », « transcris cette vidéo », « WebVTT », « SRT », « qui parle quand », « synthèse vocale », « narre ce texte », « lis ça à voix haute ». |
| **sprezzature-ux-laws** | Vous voulez un vocabulaire partagé pour vos décisions d'expérience utilisateur (UX, ce qu'on ressent en utilisant un produit, fluide et clair ou lent et confus) ET un auditeur pre-commit qui échoue sur les violations détectables des Laws of UX (Hick, Fitts, Miller, Jakob, Tesler, Aesthetic-Usability, Selective Attention, Choice Overload). | « Laws of UX », « Hick / Fitts / Miller / Jakob / Tesler / Peak-End / Postel / Paradox of the Active User », « audite ma nav / mon formulaire / ma page de prix », « cet onboarding combat-il l'utilisateur actif ». |
| **sprezzature-figures** | Vous produisez des figures pour la science des données (168 types de graphiques en image vectorielle SVG écrite à la main, graphiques d'explicabilité compris (SHAP (SHapley Additive exPlanations, une méthode qui montre de combien chaque variable a poussé une prédiction vers le haut ou vers le bas), Shapash / TimeSHAP, LIME (Local Interpretable Model-agnostic Explanations, une méthode qui explique une prédiction en ajustant un modèle simple autour d'elle))), des estimations d'effet causal (DoWhy / EconML, sur un DAG (Directed Acyclic Graph, un schéma de flèches qui vont des causes aux effets sans jamais revenir en boucle) des causes), ou des schémas de flux et des figures TikZ, affinés par la **Ralph Eyeball Loop** (rendre → regarder → corriger la source), avec un auditeur pre-commit pour les fautes de visualisation de données et des niveaux d'accessibilité à la vision des couleurs sur chaque figure. | « make a figure », « hand-authored SVG », « render this diagram », « mermaid diagram », « ralph eyeball loop », « no ascii art », « SHAP plot », « DoWhy », « DAG », « audit this figure ». |
| **sprezzature-maps** | Vous avez des nombres attachés à des lieux et la forme du terrain compte : un aplat par territoire sur un vrai fond de carte, ou une carte de situation (zones de contrôle) pour n'importe quelle région. Les cartes schématiques (carte en hexagones, densité de points, carte à pics, grille agrégée) restent dans **sprezzature-figures**. | « une carte par pays », « colore les régions selon le score », « quel pays est le plus touché », « où est-ce que ça se passe », « carte du monde », « choroplèthe », « zones de contrôle », « ligne de front », « carte de situation », « une carte par département ». |
| **sprezzature-video** | Une vidéo affirme des faits sur un projet (nombres, commandes, versions) et le projet continue de changer sous elle. | « la vidéo de démo est périmée », « vérifie ce que dit cette vidéo », « ce nombre est-il encore juste », « peut-on refaire cette vidéo », « image d'attente ». |

Les *skills* compagnons héritent des règles de pile de `sprezzature-ui`.
N'installez que ceux dont vous avez besoin.

## Comment ça marche

![Schéma de flux. En haut, une phrase adressée à un agent alimente deux voies. La voie de gauche est la couche agent, ce dépôt : elle rapproche la phrase d'une compétence par un vocabulaire déclaré et lit les documents de référence de cette compétence plutôt qu'un souvenir, puis rend un contrat. La voie de droite est la couche outils, dix paquets autonomes : chacun s'installe seul et se publie par cinq surfaces, une bibliothèque, une ligne de commande, une interface HTTP, une surface d'outils pour agent et une compétence. Les deux se rejoignent en un seul résultat, un artefact fabriqué puis contrôlé par une barrière qui sort avec un code non nul.](https://raw.githubusercontent.com/warith-harchaoui/sprezzature/main/assets/comment-ca-marche.svg)

## Architecture à deux couches

Depuis le 2026-07-29, sprezzature s'organise en deux couches aux cycles de release distincts.

**Couche 1 : packages pip autonomes.** Les scripts Python de chaque *skill* vivent dans un repo indépendant, publié sur PyPI. N'installez que ce dont vous avez besoin (`pip install <package>`), et chacun arrive entier : la bibliothèque, la ligne de commande (Click), le serveur FastAPI et la surface d'outils MCP (Model Context Protocol, le protocole par lequel les agents IA appellent des outils en français) sont tous dans l'installation de base. Il n'y a plus aucun extra de fonctionnalité dans la suite depuis le 2026-11-01. L'image Docker de chaque brique lance son serveur `<brique>-mcp`, qui sert l'API (Application Programming Interface, les requêtes qu'un programme peut envoyer à un autre, comme « dessine ce graphique ») HTTP (HyperText Transfer Protocol, la langue que parlent un navigateur et un serveur à chaque chargement de page) et `/mcp` sur le même port :

| Package | Ce que ça fait |
|---|---|
| `sprezzature-figures` | 168 types de graphiques, SHAP, estimations causales, la Ralph Eyeball Loop |
| `sprezzature-colors` | Audit de contraste WCAG, simulation de daltonisme (CVD), export palette Tailwind |
| `sprezzature-accessibility` | Lint a11y statique (20 règles, sans navigateur) et texte alternatif W3C rédigé par un modèle de vision local |
| `sprezzature-cli-gui` | Parseur d'arguments CLI vers interface graphique une page |
| `sprezzature-ux-laws` | Audit des Laws of UX (Hick, Fitts, Miller, Jakob, Tesler, …) |
| `sprezzature-audio` | Parole vers texte, diarisation, identification du locuteur, traduction de sous-titres ; narration (Kokoro par défaut, OpenVoice, Chatterbox) |
| `sprezzature-maps` | Choroplèthes et cartes de situation, en cinq modes, de qualité rédactionnelle |
| `sprezzature-publish` | Markdown vers site, balises meta, icônes, index, langage clair, narration et lecture suivie, SEO / GEO / AEO |
| `sprezzature-ui` | Fabrication et audit du catalogue i18n (`locales/i18n.yaml`) à côté du guide de génération d'interface |
| `sprezzature-video` | Vérifie ce qu'un film dit contre le code, et s'il peut être rendu à nouveau |

`pip install sprezzature` installe les dix, et les *skills* avec eux.

Tous les repos sont sur [github.com/warith-harchaoui/](https://github.com/warith-harchaoui/).

**Couche 2 : la couche agentique (ce repo).** Les fichiers `SKILL.md`, `references/` et `web/` restent dans le monorepo `sprezzature`. Ils définissent les contrats entre l'agent Claude / OpenCode et les packages outils. Ils sont publiés sur PyPI dans le paquet `sprezzature`, dont la commande `sprezzature-skills` les copie là où un agent les lit.

> **Quelle phrase déclenche quel *skill* ?** Voir
> [`TRIGGERS.md`](TRIGGERS.md), généré depuis chaque `SKILL.md`,
> liste toutes les phrases garanties par leur description avec le
> *skill* qu'elles activent.

## Premiers pas

Sprezzature, ce sont des *skills* pour **Claude Code** ou **OpenCode**. Installez ceux
que vous voulez, puis demandez en français. Le *skill* **produit**
l'artefact et l'**audite**.

Le chemin le plus court installe d'un coup les dix paquets outils et les dix *skills* :

```bash
pip install sprezzature
sprezzature-skills             # dit quels skills installés diffèrent de ceux livrés
sprezzature-skills --install   # les copie dans ~/.claude/skills (--agent opencode pour ~/.opencode/skills)
```

`--install` met de côté toute copie précédente au lieu de l'effacer, et dit où.
Pour ne prendre que les dossiers de *skills*, sans les outils :

```bash
# 1. Récupérez la dernière release (résolue, pour qu'elle ne se périme plus)
VERSION=$(curl -fsSL https://api.github.com/repos/warith-harchaoui/sprezzature/releases/latest \
  | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p')
curl -L https://github.com/warith-harchaoui/sprezzature/releases/download/v${VERSION}/sprezzature-skills-${VERSION}.tar.gz | tar xz

# 2. Copiez les skills voulus dans votre environnement
#    Claude Code → ~/.claude/skills   ·   OpenCode → ~/.opencode/skills
mkdir -p ~/.claude/skills
cp -r sprezzature-ui sprezzature-figures ~/.claude/skills/
```

Ensuite, en session, il suffit de demander :

- « rends cette page accessible » → **sprezzature-accessibility** audite le HTML et liste quoi corriger.
- « fais une figure de ce CSV (Comma-Separated Values, un tableau enregistré en texte brut, une ligne par rangée et les cellules séparées par des virgules : ce qu'exporte un tableur) » → **sprezzature-figures** la dessine, puis audite le graphique.
- « transforme ce CLI en interface » → **sprezzature-cli-gui** échafaude une interface utilisable.

Toutes les options (vérification des sommes de contrôle, tarballs par *skill*, la voie
OpenCode + Ollama local à zéro token, mises à jour, nettoyage) sont dans
[Installation](#installation) ci-dessous.

## Docs & site web

Les guides pour humains vivent dans [`docs/`](docs/), une page par *skill*
([UI](docs/UI.md) · [CLI](docs/CLI.md) · [publish](docs/PUBLISH.md) ·
[accessibility](docs/ACCESSIBILITY.md) · [colors](docs/COLORS.md) ·
[vision](docs/VISION.md) · [audio](docs/AUDIO.md) · [UX-laws](docs/UX-LAWS.md) ·
[figures](docs/FIGURES.md) · [cartes](docs/MAPS.md) · [vidéo](docs/VIDEO.md)), chacune un simple pointeur vers le
`SKILL.md` du *skill*, ses `references/` et sa recette dans `EXAMPLES.md` (aucune
duplication). `SKILL.md` est l'artefact *agent* ; `docs/` est pour les humains.

Pour le *pourquoi* de la suite, les convictions de conception qui
traversent chaque *skill*, voyez [`PHILOSOPHIE.md`](PHILOSOPHIE.md)
(English : [`PHILOSOPHY.md`](PHILOSOPHY.md)).

Un site statique déployable, multi-pages, construit avec les *skills* `sprezzature-*`
eux-mêmes (house style sprezzature-ui, meta / favicons / sitemap / llms.txt de
sprezzature-publish, palette sprezzature-colors, sprezzature-accessibility clean, un vrai toggle
🌞/🌛), se trouve dans [`web/`](web/) et se publie sur
<https://sprezzature.ai/>. Il a une page de détail par *skill* (make /
audit / triggers / bibliothèque de références) et une **galerie de figures**
dédiée qui rend tout le catalogue `sprezzature-figures`. La galerie porte un
**visualiseur « Voir pour… »** qui applique une simulation vivante de la vision
des couleurs sur les figures par défaut&#8239;: il simule ce que voit un lecteur
daltonien, il ne substitue pas une autre figure. Un contrôle **plein écran**
partagé permet d'ouvrir n'importe quel graphique en grand.

## Fonctionnalités : ce qui est inhabituel pour un *skill* Claude

La plupart des *skills* Claude, y compris les `document-skills` d'Anthropic
(docx, pdf, pptx, xlsx) et les `example-skills` (artifacts, GIFs, serveurs Model Context Protocol (MCP),
design), ne font que du **make** : le modèle produit un artefact. `sprezzature` est
conçu autrement et ces traits le distinguent :

- **Make *et* audit.** Chaque *skill* associe la génération à un **auditeur
  déterministe** qui sort en erreur au moindre problème :
  `sprezzature-accessibility-lint`, `sprezzature-colors-contrast`,
  `sprezzature-ux-laws`, `sprezzature-figures check`, `sprezzature-ui-i18n-audit`,
  `sprezzature-publish-lint` et `-audit`, `sprezzature-cli-gui-audit`,
  `make-map audit`, `make-film verify`. Aucun *skill* officiel d'Anthropic ne livre un
  linter statique comme raison d'être ; ici c'est la moitié de la conception.
- **Des gardes d'intégration continue (CI, les vérifications automatiques qu'un serveur lance à chaque modification envoyée sur le dépôt) / pre-commit, pas du ressenti.** Les auditeurs émettent du JSON (JavaScript Object Notation, un format texte dans lequel les programmes rangent des données en champs nommés)
  + des codes de sortie, donc un hook pre-commit ou une étape de CI bloque le
  commit, quel que soit l'auteur (humain ou machine) ; voir
  [Hooks pre-commit](#hooks-pre-commit).
- **Intelligence artificielle (IA) locale, zéro fuite vers des services en ligne (SaaS).** Le texte alternatif tourne sur un modèle de
  vision Ollama local ; les sous-titres / la diarisation sur une build
  whisper.cpp locale et NeMo ; la narration sur Kokoro. Rien ne quitte la machine ; les *skills* officiels passent
  d'abord par le cloud Claude.
- **Générateurs déterministes.** palette → config Tailwind, CLI → interface graphique (GUI, Graphical User Interface, des fenêtres et formulaires sur lesquels on clique), jeux
  d'icônes favicon / application web progressive (PWA, un site qu'un téléphone installe sur son écran d'accueil comme une application), sitemaps / flux et `locales/i18n.yaml` : des artefacts
  reproductibles qu'un modèle ne dériverait pas à l'octet près.
- **Durci comme un produit, pas une démo.** Une vraie suite pytest dans chaque
  dépôt, une couche d'évaluation IA (DeepEval) dans les briques qui appellent un
  modèle, de la CI sur Python 3.12 avec une vérification d'installation et
  d'import sur le plancher 3.10, des archives de release
  par *skill* vérifiées par somme de contrôle et un validateur de conformité à la spécification, face
  à des exemples de niveau démonstration.
- **Portable entre environnements d'exécution.** Un même dossier de *skill* sert **Claude Code** et
  **OpenCode** ; les chemins IA visent des modèles locaux pour qu'un modèle
  OpenCode plus petit suive un script au lieu d'en inventer un.
- **Internationalisation (i18n) unifiée.** Les chaînes d'interface *et* les prompts du grand modèle de langage (LLM, le type d'IA derrière les assistants comme ChatGPT ou Claude) vivent dans un
  seul `locales/i18n.yaml`, appliqué côté make comme côté audit.

## Deux modes : make et audit

Chaque *skill* sprezzature-* appartient à l'une (ou aux deux) moitiés d'une
seule boucle : **make** (produire l'artefact) et **audit** (le
vérifier). Le tableau indique quand charger chaque *skill* et ce qui
reste en feuille de route.

| *Skill* | Make (générer) | Audit (porte) |
|---|---|---|
| **sprezzature-ui** | `references/` + `assets/components/` : guide de génération HTML / Tailwind / visualisation de données ; `sprezzature-ui-i18n-make` (échafaude et compile `locales/i18n.yaml`) | `sprezzature-ui-i18n-audit` (`I18N001`, `I18N002`), `references/checklist.md`, `anti-patterns.md`, `ergonomics-criteria.md` |
| **sprezzature-cli-gui** | `sprezzature-cli-gui` (parseur argparse, Click ou Typer → un formulaire HTML autonome ; `--from-help` lit un texte d'aide à la place) + `assets/examples/cli-gui-demo/` (exemple complet) | `sprezzature-cli-gui-audit` (cinq règles : une page plus ancienne couvre-t-elle encore le CLI ?) ; à coupler avec `sprezzature-accessibility` + `sprezzature-ux-laws` sur le HTML émis |
| **sprezzature-publish** | `sprezzature-publish-html`, `-icons`, `-indexes` (`--offer`, `--cta`), `-meta`, `-plain`, `-changelog`, `-narrate`, `-readalong`&#8239;; `-cta` (demande quel appel à l'action le site sert, écrit `ctas.yaml`), `-faq` (construit la FAQ qui manque à partir des pages du site) | `sprezzature-publish-lint` (le Markdown), `-audit` (un site émis ou une URL en ligne), `-cta` et `-faq --audit` (les pages contre les CTA (Call To Action, la seule chose qu'une page demande à son lecteur : réserver, acheter, installer) déclarés, `FAQPage` contre la FAQ visible), `-findable` (un seul rapport SEO + GEO + AEO, pages argent d'abord) |
| **sprezzature-accessibility** | `--fix-alt` et `sprezzature-accessibility-alt` (texte alternatif W3C rédigé par un modèle de vision local, dans la langue de la page) | `sprezzature-accessibility-lint` (20 règles lues dans la source, six avec un `--fix` sûr), `sprezzature-accessibility-text-spacing` |
| **sprezzature-colors** | `sprezzature-colors-palette-to-tailwind` (palette → tailwind.config.js), `sprezzature-colors-levels` (projette la palette en `universal` / `high-contrast` / `monochrome` / une variante de déficience de la vision des couleurs) | `sprezzature-colors-contrast` (chaque paire qui coexiste contre WCAG, correction OKLCH la plus proche ; sortie 2 quand aucune clé ne correspond à un rôle), `sprezzature-colors-cvd` (simulation, mosaïque, `--grayscale`) |
| **sprezzature-audio** | sous-titres (whisper.cpp local), diarisation, nommage des locuteurs, traduction ; narration par Kokoro, OpenVoice ou Chatterbox, le moteur choisi par le routeur de speaker-helper | `sprezzature-audio-audit` (pistes de sous-titres), `-benchmark` (taux d'erreur de mots) |
| **sprezzature-ux-laws** | `references/laws-of-ux.md` (guide des 30 lois) | `sprezzature-ux-laws` (huit lois vérifiées dans la source : Hick, Fitts, Miller, Jakob, Tesler, esthétique-utilisabilité, attention sélective, surcharge de choix ; `--fix` en répare quatre) |
| **sprezzature-figures** | `sprezzature-figures render <type>` (données → SVG écrit avec soin, 168 types de graphiques), `explain_model.py` (SHAP / Shapash / TimeSHAP / LIME), `causal_estimate.py` (DoWhy + EconML + graphe orienté sans cycle / DAG), `render_diagram.py` (TikZ / SVG → PNG), `ralph_eyeball_loop.py` (rendre → regarder → corriger, en mode agent ou `--local`). Chaque générateur accepte un niveau `--accessibility` | `sprezzature-figures check`, `audit_figure.py` (pie-3d, rainbow-palette, chartjunk, radius-over-cap, unformatted-tick, iso-date-tick, role-img-missing, alt-missing) |
| **sprezzature-maps** | `make-map choropleth` (lignes indexées par territoire → fond de carte réel ombré, Equal Earth ; échelle divergente quand les valeurs changent de signe), `make-map density` (points → carte d'accumulation), `make-map situation_map` (une configuration YAML (YAML Ain't Markup Language, un format texte pour les réglages, un « nom : valeur » par ligne) → planche de zones de contrôle ; quinze planches exemples) | `make-map audit` (onze règles statiques sur une planche finie), `make-map improve` |
| **sprezzature-video** | `make-film captions` (script de narration + durée **mesurée** de l'audio → WebVTT, pas une transcription), `make-film poster` (l'image d'attente, cuite en image 0 là où un fil refabrique sa propre vignette) | `make-film verify` (chaque revendication déclarée contre le code qui tranche — sortie 1 = le film ment), `make-film scan` (chaque nombre à l'écran qu'aucune revendication n'explique), `make-film assets` (suivi / dérivé / nulle part ailleurs ; une divergence est signalée, jamais réparée en silence) |

Le tableau est honnête sur les manques. Les cellules vides marquent
de vraies entrées de feuille de route, pas des oublis.

## À qui ça s'adresse

`sprezzature` vise quatre publics concrets. Chaque ligne est un argumentaire
autonome : si l'un d'eux correspond à votre situation, le *skill*
associé se justifie déjà à lui seul.

1. **Développeurs en solo sans designer.** Des choix par défaut
   assumés pour arrêter de tergiverser sur les variables de design (design tokens) : installez
   `sprezzature-ui` et livrez une interface utilisable dès le premier commit.
   Variables de design Tailwind, variantes `dark:`, anneaux de focus, zones
   tactiles : tout est cadré.
2. **Pentesters qui écrivent des tableaux de bord internes.** Sortie
   HTML mono-fichier qui se dépose telle quelle sur une machine
   interne, sans chaîne de build. Les portes d'accessibilité (`sprezzature-accessibility`)
   tournent en CI sans navigateur, donc même un outil de reconnaissance jetable
   reste lisible pour les coéquipiers sous technologie d'assistance.
3. **Data scientists qui habillent des CLI.** Pointez `sprezzature-cli-gui`
   sur votre `--help` (argparse, Click, Typer, clap, commander, cobra
   se laissent introspecter) et vous obtenez une maquette d'IHM
   fonctionnelle. Pas d'environnement d'exécution Gradio, pas de carcan React.
4. **Sites de documentation bilingues (anglais et français par défaut ; la paire
   est configurable).** `sprezzature-publish` garde la typographie et la
   tonalité alignées sur deux langues et produit en une passe balises meta
   + favicons + sitemap. Changez la paire (EN/DE, EN/JA, EN/ES,
   …) en éditant une seule variable de configuration ; voir, dans chaque
   `SKILL.md`, la section « Changing the language pair ».

Ce **n'est pas** le bon choix pour :

- Le travail de marque pour une app grand public qui demande une
  identité visuelle propre.
- Les landings marketing où Webflow ou Framer sont plus rapides.
- Les apps où l'équipe a déjà choisi React / Vue / Svelte ; préférez
  shadcn / Headless UI / Mantine.
- Les sites de doc versionnés à plusieurs centaines de pages ;
  préférez MkDocs Material, Hugo ou Astro.

Pour les alternatives par catégorie et l'aide à la décision « est-ce
que `sprezzature` est le bon outil ? », voir [PAYSAGE.md](PAYSAGE.md) (anglais :
[LANDSCAPE.md](LANDSCAPE.md)). Le document ouvre sur une table de
**positionnement concurrentiel** (projets × critères, notés 1–5 ⭐️) qui alimente
[standpoint](https://github.com/warith-harchaoui/standpoint) pour tracer une
carte 2-D de la place de `sprezzature`. Pour des sites réels déjà livrés sur cette pile, voir
[GALLERY.md](GALLERY.md). Pour des recettes copier-coller par *skill*
(avec la sortie attendue), voir [`EXAMPLES.md`](EXAMPLES.md).

## Ce que les *skills* garantissent

- Le code produit est en JavaScript pur (modules ES (le standard de JavaScript, ici sa façon de découper le code en fichiers), `<dialog>` natif,
  custom elements quand c'est justifié). Pas de React, Vue, Svelte,
  Next.js, Nuxt, Angular ni Solid.
- Le code utilise des classes utilitaires Tailwind avec des variables de design (design tokens)
  sémantiques (`bg-brand-blue`, `text-label-primary`). Pas de couleur
  hexadécimale brute dans le balisage.
- Le code applique la **règle des trois Roboto** : exactement trois
  polices téléchargées, toutes issues de la super-famille Roboto :
  **Roboto** (sans-serif / UI / texte courant), **Roboto Serif**
  (longform éditorial / pages très textuelles), **Roboto Mono**
  (`<code>`, `<pre>`, panneaux terminal, logs). Aucune autre famille
  téléchargée n'est admise (ni Inter, ni Montserrat, ni IBM Plex, ni
  JetBrains Mono). Les trois familles partagent par construction les
  mêmes métriques et la même hauteur d'x, si bien que les surfaces mêlant prose
  et code restent cohérentes typographiquement. Toutes sont
  auto-hébergées (pas de CDN (Content Delivery Network, des serveurs répartis dans le monde qui livrent chaque fichier depuis un serveur proche du lecteur) Google Fonts en production) ; les fichiers de police Web Open Font Format version 2 (WOFF2, le fichier de police compressé que télécharge le navigateur) et leur licence libre OFL (SIL Open Font License, qui permet à chacun d'utiliser et de distribuer la police gratuitement) vivent sous `sprezzature-ui/assets/fonts/roboto/`, `…/roboto-serif/`
  et `…/roboto-mono/`.
- Le code pose une variante `dark:` sur chaque élément stylé,
  privilégie `<button>` / `<a>` / `<label>` / `<dialog>` / `<form>`,
  expose un anneau de focus visible, respecte `prefers-reduced-motion`,
  et garantit une cible tactile d'au moins 44 × 44 px.
- Le code expose un **toggle 🌞 Light / 🌚 Dark / 🌗 Auto**
  (placement canonique : haut-droite du header sticky → coin
  bas-droite du footer → ancrage fixed bottom-right quand il n'y a
  pas de header). **Auto est le défaut**, pour qu'un visiteur frais
  hérite du choix de son système d'exploitation (OS, comme macOS, Windows ou Android) et ne soit jamais surpris par un thème
  forcé. Composant :
  `sprezzature-ui/assets/components/theme-toggle.html`. Câblage :
  `sprezzature-ui/references/stack-vanilla-js.md` § « Theme switching ».
- Les choix de couleur renvoient aux palettes de
  `sprezzature-ui/references/color-psychology.md` (source :
  <https://deraison.ai/colors/>).
- La sortie du *skill* est **du HTML mono-fichier de niveau prototype**
  par défaut, adaptée aux démos, maquettes, outils internes et
  petites landings. La page d'amorçage utilise le CDN Play de
  Tailwind, que Tailwind lui-même réserve au prototypage. Pour un site
  de production à l'échelle, faites passer **Tailwind CLI** ou
  **Vite + Tailwind** sur le HTML émis avant déploiement ; les noms de
  classes sont stables, donc les mêmes fichiers survivent à la
  bascule. Voir `sprezzature-ui/references/stack-tailwind.md`.
- Texte bilingue (EN/FR par défaut). La langue de sortie des scripts
  IA est **détectée automatiquement depuis le texte d'entrée / de
  contexte** via `langdetect` ; pas de langue par défaut configurée ;
  passez `--lang` pour en forcer une. Pour les chaînes d'interface et
  les prompts traduisibles, utilisez un seul catalogue
  `locales/i18n.yaml` (voir `sprezzature-ui-i18n-make` et
  `sprezzature-publish/references/i18n.md`).
- **L'i18n vit dans du format de configuration YAML, jamais dans du JS.** Les chaînes
  traduisibles (libellés d'interface **et** prompts LLM) vivent dans
  un seul catalogue par projet, **`locales/i18n.yaml`** (id de message →
  texte par locale), chargé à l'exécution ; jamais un dictionnaire de
  traductions figé dans du JavaScript, jamais un prompt en dur dans du
  Python. Interface et prompts partagent `locales/i18n.yaml` car ils
  partagent une seule question : la *langue*. Les prompts fonctionnent
  déjà ainsi (`prompts/*.yaml`, chargés via `_prompts.load_prompt`) ; la
  même règle gouverne les interfaces générées, côté **make** (générer et
  lire `locales/i18n.yaml`) comme côté **audit** (signaler toute chaîne
  ou tout prompt hors de ce fichier, en dur dans du JS ou du Python).

## État d'avancement

Photographie de l'état de chaque surface. Les dix dossiers
de *skills* sont stables ; la seule zone en travaux est l'**audio /
sous-titres** (sprezzature-audio, vidéo → texte). La **narration**
(texte → audio : sprezzature-audio fabrique la voix, sprezzature-publish la
pose dans la page avec une lecture suivie) est stable et explicitement encadrée
comme amélioration éditoriale optionnelle, pas exigence WCAG.

| Domaine | État | Notes |
|---|---|---|
| `sprezzature-ui` (règles de pile, variables de design, composants, visualisation de données, check-list, i18n) | Stable | Règles de pile documentées ; `scripts/validate_content.py` contrôle les imports de framework ; le paquet livre `sprezzature-ui-i18n-audit` (`I18N001`, `I18N002`) et `-i18n-make`. |
| `sprezzature-cli` (pilote `sprezzature` unifié, complétion shell) | Stable | Basé sur Click ; route vers les commandes propres aux dix briques et leur transmet `--help`. |
| `sprezzature-cli-gui` (CLI → IHM, phare) | Stable (*skill* + démo exécutable) | `assets/examples/cli-gui-demo/` tourne de bout en bout. Durcissement production (auth, rate-limit, sandbox) délibérément laissé à l'hôte. |
| `sprezzature-publish` (site Markdown, meta, favicons, index, langage clair, narration, SEO + GEO + AEO) | Stable | Treize outils : les artefacts du site, le lint Markdown et l'audit du site, la narration et la lecture suivie, et depuis la 1.4.0 `cta`, `faq` et `findable`, qui ordonnent le travail pour les moteurs de recherche, génératifs et de réponse selon l'appel à l'action déclaré du site. |
| `sprezzature-accessibility` : lint | Stable | Lint a11y statique de 20 règles lues dans la source, six avec un `--fix` sûr. |
| `sprezzature-colors` : audit contraste, simulation de déficience de la vision des couleurs (DVC, le nom médical du daltonisme), palette sélectionnée, éclaircissement / assombrissement perceptuels | Stable | Correcteur de contraste par voisin dans l'espace colorimétrique perceptuel OKLCH (clarté (L), chroma (C) et teinte (H)), matrices DVC de Machado, CSV palette unifiée (base Apple + projections émotion / concept / psychologie), module `_colors` stdlib uniquement, classe `Color`. Sorti de `sprezzature-accessibility` pour un périmètre plus clair. |
| `sprezzature-accessibility` : texte alternatif W3C via vision Ollama locale | Stable | Modèle `qwen3-vl:8b` via Ollama (le seul LLM autorisé). Arbre de décision par objectif, biais par texte environnant + vocabulaire projet, cache disque ; `--fix-alt` l'écrit dans la page. S'appelait `sprezzature-vision` avant sa fusion dans `sprezzature-accessibility`. Éval texte alternatif sur fixtures Wikipedia. |
| `sprezzature-audio` : **sous-titres WebVTT / SRT via whisper.cpp local** | **En travaux / à faire** | `sprezzature-audio-captions` est fonctionnel ; ce qui manque, ce sont les mesures de référence de taux d'erreur sur les mots (WER, word error rate, la part des mots qu'une transcription rate) par langue (`en` / `fr` / `es` câblés via l'extracteur, mesures pas encore publiées), le clip utilisateur `vocab-biasing-clip.wav` et une révision prévue de l'intégration whisper.cpp via `pdbms`. Voir [Roadmap](CHANGELOG.md#roadmap). |
| `sprezzature-figures`, `-maps`, `-ux-laws` | Stable | figures dessine 168 types de graphiques ; maps classe ses choroplèthes et nomme la méthode ; ux-laws confronte une page aux lois de l'UX. |
| `sprezzature-video` (revendications, scan, registre des ressources, sous-titres, image d'attente) | Stable, avant 1.0 | La surface peut encore bouger entre versions mineures. |
| `LISEZMOI.md` (README français) | Stable | À parité structurelle avec le README EN : même ordre des sections, contenu maintenu en synchronisation à chaque release. |

Pour le détail par release (et la suite prévue), voir [`CHANGELOG.md`](CHANGELOG.md).

## Entrées → sorties

Ce que vous donnez à l'agent et ce qu'il vous renvoie. Chaque ligne
est un flux autonome ; prenez celle qui vous concerne, ignorez le
reste.

| Vous fournissez | Phrase | *Skill* | Sortie |
|---|---|---|---|
| Un CLI fonctionnel (un parseur Python `argparse` / Click / Typer, ou le texte `--help` de n'importe quel outil) | « Habille ce CLI d'une IHM » + chemin du projet | `sprezzature-cli-gui` | Un seul `index.html` autonome, configuration Tailwind et script en ligne, sous-commandes mappées en formulaires / champs fichier / listes de choix. Le formulaire fabrique la ligne de commande exacte ; vous la câblez sur votre hôte (Tauri / Electron / FastAPI / Express / bouchon navigateur). Une commande d'audit vérifie que la page couvre toujours l'analyseur. |
| Un dossier de fichiers Markdown (README, `docs/**`, articles) | « Transforme ces fichiers markdown en site » | `sprezzature-publish` | Site statique : une page HTML par `.md`, barre supérieure collante, sommaire latéral pour `docs/`, mode sombre, favicons, balises `<meta>`, `robots.txt` + `sitemap.xml` + `llms.txt` + flux Atom. |
| Une demande libre (« bouton primaire », « dialogue de confirmation », « page réglages ») | « Construis un `<composant>` » | `sprezzature-ui` | HTML sémantique + Tailwind + JS minimal, anneau de focus, variante `dark:`, zone tactile 44 × 44 px, fermeture par `Échap`, garde-fou `prefers-reduced-motion`. |
| Un jeu de données (CSV, JSON, quelques lignes collées) | « Trace ça » / « Tableau de bord pour X » | `sprezzature-ui` | SVG en ligne + enveloppe `<figure>`. Style maison, palette de `color-psychology.md`, axes avec polarité, `role="img"`. |
| Une page HTML existante ou une capture d'écran | « Audite » / « Vérif WCAG » / « Rends ça moins IA » | `sprezzature-ui` (anti-patterns, ergonomie) + `sprezzature-accessibility` (lint) + `sprezzature-colors` (contraste, daltonisme) | Constats au regard des 8 critères ergonomiques + catalogue d'anti-patterns ; diffs concrets ; checklist pré-livraison ; sorties `sprezzature-accessibility-lint` + `sprezzature-colors-contrast` + `sprezzature-colors-cvd`. |
| Une image (`*.png`, `*.jpg`, …) | « Texte alternatif pour cette image » | `sprezzature-accessibility` | Texte alternatif conforme W3C dans la bonne catégorie (informatif / décoratif / fonctionnel / texte / complexe / groupe), rédigé dans la langue de la page, marqué `data-alt-source="ai"`. |
| Un fichier audio ou vidéo (`.mp4`, `.wav`, `.mp3`, …), **en travaux** | « Sous-titres / transcription » | `sprezzature-audio` *(en travaux)* | Sous-titres WebVTT / SRT / texte brut depuis whisper.cpp local, avec biais de vocabulaire issu du projet. Extrait `<video>` + `<track kind="captions">` à coller. Le script et les tests sont là aujourd'hui ; les baselines WER par langue et le clip de référence pour le biais de vocabulaire sont encore à collecter ; voir [État d'avancement](#état-davancement). |
| Un logo (`logo.png` / `.svg`) | « Jeu de favicons » / « Icônes PWA » | `sprezzature-publish` | `favicon.svg` + `.ico` + lot de PNG + `apple-touch-icon.png` + icône PWA masquable + `site.webmanifest` + extrait `head.html`. |
| Une description d'objectif ou une page HTML | « Meta tags » / « SEO » / « OG card » / « GEO » / « llms.txt » / « AI Overview » | `sprezzature-publish` | **Pour le référencement naturel (SEO) :** titre + description + balises Open Graph (OG) + Twitter Card + Schema.org en JSON pour données liées (JSON-LD, du JSON caché dans la page qui dit aux moteurs de recherche de quoi elle parle) (JSON sur la sortie standard) ; voir [les trois piliers de Google Search Essentials](https://developers.google.com/search/docs/essentials) appliqués dans `sprezzature-publish/references/seo-essentials.md`. **Pour l'optimisation pour moteurs génératifs (GEO : surfaces de réponses AI Overview / Gemini / ChatGPT)** : `llms.txt` est émis par `sprezzature-publish-indexes` aux côtés de `robots.txt` + `sitemap.xml` + flux Atom / RSS (Really Simple Syndication, un flux qui permet de suivre les nouveaux articles d'un site dans une application de lecture), donc le site embarque un résumé Markdown lisible par les LLM dès qu'une commande « transforme ce dossier en site » se termine. Mêmes robots, mêmes permissions dans `robots.txt` ; aucune balise meta « AI » n'existe ; toute affirmation contraire est fausse. |
| Un site existant (HTML, PHP (Hypertext Preprocessor, un langage avec lequel le serveur fabrique chaque page au moment où on la demande, comme le fait WordPress), Markdown, JSON, YAML) | « Mon site ne vend pas » / « Écris-moi une FAQ » / « AEO » | `sprezzature-publish` | D'abord une question : quel appel à l'action le site sert-il (la détection propose ce qu'il propose déjà). Puis la FAQ qui manque, chaque réponse tirée de ses propres pages et les questions sans réponse listées à part ; et un seul rapport SEO + GEO + AEO, pages argent d'abord. |
| Du texte d'IHM brut | « Langage clair » / « Réécris au niveau 6e » | `sprezzature-publish` | Même sens, voix marketing retirée, longueur de sortie ≤ 1,1× l'original. |
| Une palette JSON | « Audit de contraste » / « Ma palette est-elle accessible ? » | `sprezzature-colors` | Chaque paire `(label, surface)` parcourue, échecs listés avec la correction OKLCH voisine la plus proche. Sortie 1 sur échec. |
| Une page finalisée / capture d'écran | « Vérif pré-livraison » | `sprezzature-ui` + `sprezzature-accessibility` + `sprezzature-colors` | La porte `checklist.md` exécutée ; lint + contraste + daltonisme passent ; texte / animation / performance vérifiés. |

> Pas sûr quelle ligne correspond ? Décrivez l'entrée en français courant. L'arbre de décision de chaque `SKILL.md` mappe les formulations vers les workflows.

## Installation

Les *skills* suivent la [spécification Anthropic des *skills*](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
et sont lus nativement par **Claude Code** et **OpenCode**. N'installez
que ceux qui vous servent.

Les flux Claude Code et OpenCode sont **identiques sauf pour le
dossier d'install** : les deux environnements d'exécution lisent les `SKILL.md` dans
un dossier par *skill* et les mêmes archives servent les deux. La
procédure ci-dessous montre une voie ; le second environnement d'exécution est une
substitution d'une ligne.

> **Variables partagées.** Remplacez `<RUNTIME>` par `claude` ou
> `opencode`. Épinglez `VERSION` sur la dernière tag ; voir
> [releases](https://github.com/warith-harchaoui/sprezzature/releases).

### 1. Téléchargez une release taguée (somme de contrôle vérifiée)

```bash
VERSION=$(curl -fsSL https://api.github.com/repos/warith-harchaoui/sprezzature/releases/latest \
  | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p')
curl -L -o sprezzature-skills.tar.gz \
    https://github.com/warith-harchaoui/sprezzature/releases/download/v${VERSION}/sprezzature-skills-${VERSION}.tar.gz
curl -L -o SHA256SUMS \
    https://github.com/warith-harchaoui/sprezzature/releases/download/v${VERSION}/SHA256SUMS

# macOS : shasum -a 256 -c SHA256SUMS
# Linux : sha256sum -c SHA256SUMS
shasum -a 256 -c SHA256SUMS

tar xzf sprezzature-skills.tar.gz
```

Si vous n'avez besoin que d'un seul *skill*, remplacez le bundle par
une archive unitaire (par exemple `sprezzature-accessibility-${VERSION}.tar.gz`).
Le même `SHA256SUMS` couvre tous les artefacts.

### 2. Copiez dans le dossier *skills* de l'environnement d'exécution

Choisissez **un** environnement d'exécution :

```bash
# Claude Code :
RUNTIME=claude   # → ~/.claude/skills/
# OpenCode :
RUNTIME=opencode # → ~/.opencode/skills/

mkdir -p ~/.${RUNTIME}/skills
cp -r sprezzature-ui            ~/.${RUNTIME}/skills/   # toujours
cp -r sprezzature-cli-gui       ~/.${RUNTIME}/skills/   # uniquement si vous habillez des CLI
cp -r sprezzature-publish       ~/.${RUNTIME}/skills/   # uniquement pour les sites de doc
cp -r sprezzature-accessibility ~/.${RUNTIME}/skills/   # uniquement pour lint a11y statique ou alt text IA
cp -r sprezzature-colors        ~/.${RUNTIME}/skills/   # uniquement pour contraste WCAG / CVD / palette
cp -r sprezzature-audio         ~/.${RUNTIME}/skills/   # uniquement pour sous-titres ou narration (local)
cp -r sprezzature-ux-laws       ~/.${RUNTIME}/skills/   # uniquement pour l'audit Laws-of-UX
cp -r sprezzature-figures       ~/.${RUNTIME}/skills/   # uniquement si vous produisez des figures dataviz / SHAP / DoWhy
cp -r sprezzature-maps          ~/.${RUNTIME}/skills/   # uniquement si vos nombres sont attachés à des lieux
cp -r sprezzature-video         ~/.${RUNTIME}/skills/   # uniquement si une vidéo affirme des faits sur votre projet
```

Installez dans **les deux** environnements d'exécution si vous alternez entre eux :
même dossier copié dans deux chemins.

### 3. Vérifiez

```bash
# Un skill est installé et son SKILL.md est sur disque :
ls ~/.${RUNTIME}/skills/sprezzature-ui/SKILL.md

# Optionnel : si vous avez aussi cloné le dépôt, vérifiez chaque
# skill installé contre la spécification Anthropic (stdlib + PyYAML,
# pas de réseau) :
python3 scripts/validate_all.py
```

L'environnement d'exécution lit la description du `SKILL.md` de chaque *skill* au
démarrage de la conversation ; les phrases correspondantes activent
automatiquement le *skill*. Voir [`TRIGGERS.md`](TRIGGERS.md) pour
l'index par phrase.

### Nettoyage : retirer les *skills* obsolètes ou renommés

Si vous aviez installé une ancienne version, votre dossier
`~/.${RUNTIME}/skills/` peut contenir des dossiers orphelins issus
de renommages passés (par exemple `sprezzature-a11y/` d'avant le rename
v0.9.0 vers `sprezzature-accessibility`). Lancez l'aide pour les détecter
et les retirer :

```bash
# Audit seul (liste les dossiers orphelins ; ne supprime jamais) :
python3 scripts/cleanup_local_skills.py

# Appliquer : demande confirmation par dossier avant suppression.
python3 scripts/cleanup_local_skills.py --apply
```

L'outil vérifie `~/.claude/skills/` et `~/.opencode/skills/` contre
le manifeste canonique [`SKILLS.txt`](SKILLS.txt) et signale tout
dossier `sprezzature-*` qui n'est plus livré par ce dépôt.

### Mise à jour

Recommencez les étapes 1–3 avec la nouvelle `VERSION`. Le nom du
dossier installé est stable, donc chaque `cp -r` écrase l'install
précédente sur place ; pas de suppression manuelle entre versions,
sauf quand un *skill* est **renommé** (utilisez l'aide de nettoyage
ci-dessus dans ce cas). Les renommages sont listés dans
[`CHANGELOG.md`](CHANGELOG.md).

### Installation depuis les sources (contributeur / développeur)

Pour itérer sur les *skills* ou pour épingler un commit qui n'est
pas encore tagué, clonez et copiez depuis l'arbre de travail. Pas
de vérification de somme de contrôle : c'est à vous de garantir
le bon commit cloné.

```bash
git clone https://github.com/warith-harchaoui/sprezzature.git
cd sprezzature
python3 -m pip install -r requirements-dev.txt   # PyYAML + pytest
python3 -m pytest                                # suite complète déterministe
python3 scripts/validate_all.py                  # les 10 skills, YAML + contenu

# Reflète l'étape 2 ci-dessus :
RUNTIME=claude   # ou opencode
mkdir -p ~/.${RUNTIME}/skills
for skill in $(grep -v '^[[:space:]]*#' SKILLS.txt | grep -v '^[[:space:]]*$'); do
    cp -r "$skill" ~/.${RUNTIME}/skills/
done
```

`CONTRIBUTING.md` reprend le même flux côté contributeur.

### OpenCode + Ollama local : l'approche zéro token

[OpenCode](https://opencode.ai) est le second environnement d'exécution pris en charge,
et le compagnon naturel d'un workflow **entièrement local, sans
jeton**. OpenCode est agnostique au modèle : pointez-le sur un
daemon [Ollama](https://ollama.com) local et vous obtenez le même
comportement de *skills* que Claude Code, avec deux différences
concrètes :

- **Pas de jetons d'interface de programmation (API).** Rien ne quitte la machine ; rien ne
  facture.
- **Pas de quota d'usage.** Lancez la boucle toute la nuit sur un
  long lot de traitements sans surveiller un compteur.

Le compromis est la qualité du modèle. Un modèle local de 7-13 B
est en-dessous de Claude / GPT-4 (Generative Pre-trained Transformer 4, le modèle d'OpenAI derrière ChatGPT) sur le raisonnement difficile ;
les *skills* sprezzature-* compensent parce qu'ils chargent l'*opinion* en
amont (règles de pile, audits, phrases déclencheuses) : le modèle
n'a plus qu'à suivre un script, pas à l'inventer. Pour le travail
UI, le texte alternatif, les sous-titres, les audits de contraste, les
vérifications Laws of UX, la voie locale est aujourd'hui réellement
utilisable.

L'ajustement avec ce dépôt est direct : **trois briques sprezzature-*
parlent déjà à un daemon Ollama local** pour leurs surfaces IA :
`sprezzature-accessibility` (texte alternatif, `make-alt`),
`sprezzature-publish` (`-meta`, `-plain`, `-faq`, `-lint --ai`,
`-narrate --ai-hints`) et `sprezzature-audio` (`-name`, `-translate`). Quand vous
lancez OpenCode contre le même daemon Ollama, toute la boucle
(agent + scripts pilotés par les *skills*) utilise un seul modèle
local. Zéro appel externe.

```bash
# Démarrage rapide. Suppose Ollama + un binaire OpenCode dans le PATH.
ollama serve &         # démarrer le daemon
ollama pull qwen3-vl:8b  # le seul modèle, utilisé par la boucle d'agent ET tous les scripts
```

Un seul modèle pour toute la pile : il pilote la boucle d'agent
OpenCode ET sert tous les scripts sprezzature-* basés Ollama
(`make-alt`, `sprezzature-publish-meta`, `-plain`, `-faq`,
`sprezzature-audio-translate`, …). Même daemon, même tag, même réponse à « quel
modèle tourne ? » : `qwen3-vl:8b`.

#### Câbler OpenCode sur le daemon Ollama local (config unique)

Le provider `ollama` livré avec OpenCode pointe par défaut sur
Ollama Cloud. Pour viser votre daemon **local**, ajoutez un
provider `local-ollama` à `~/.config/opencode/opencode.jsonc`
(le fichier existe déjà ; seule la clé `provider` est nouvelle) :

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "local-ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": {
        "baseURL": "http://localhost:11434/v1"
      },
      "models": {
        "qwen3-vl:8b": { "name": "qwen3-vl:8b (local)" }
      }
    }
  }
}
```

Ollama expose un endpoint compatible OpenAI sur
`http://localhost:11434/v1`, que le provider
`@ai-sdk/openai-compatible` parle nativement ; pas de plugin à
installer en plus de la config. Listez exactement les tags que
vous avez pull-és (faites `ollama list` pour les voir) ;
OpenCode ne les découvre pas automatiquement.

Puis lancez OpenCode sur le provider local :

```bash
opencode run "construis-moi un bouton CTA principal" \
    -m local-ollama/qwen3-vl:8b

# → ~/.opencode/skills/sprezzature-* se chargent automatiquement.
# → Les scripts sprezzature-accessibility / sprezzature-publish basés Ollama
#   tapent dans le même daemon pour leurs traitements.
# → Coût : 0 token ; rien ne quitte la machine.
```

Un seul modèle, `qwen3-vl:8b`, sert la boucle d'agent ET tous les
scripts : même daemon, même tag. `qwen3-vl:8b` est multimodal, donc le
script de vision (texte alternatif) tourne sur le même modèle que les scripts
texte. Il n'y a rien d'autre à choisir.

#### Choix du modèle : pourquoi Qwen3-VL 8B (Q4_K_M)

Le modèle unique est **Qwen3-VL 8B**, quantification Q4_K_M, récupéré par
`ollama pull qwen3-vl:8b` (~6,1 Go). Il a été choisi selon quatre critères pour
une boîte à outils bilingue, riche en images et locale sur Mac : **vision**,
**français**, **reconnaissance optique de caractères (OCR, lire le texte contenu dans une image) / graphiques**, et
**compatibilité Apple Silicon**. C'est le seul modèle d'environ 8 milliards de
paramètres au sommet à la fois sur la vision, l'OCR/graphiques et la
compatibilité Mac tout en restant solide en français (DocVQA 96,1 %, OCRBench
~896, ScreenSpot 94,4 %, OCR dans 32 langues). Le raisonnement complet, le
tableau comparatif face à Gemma 3, Pixtral, InternVL, MiniCPM et les modèles
OCR spécialisés, ainsi que toutes les sources, sont dans
[`docs/LLM_CHOICE.md`](docs/LLM_CHOICE.md). La règle est vérifiée
automatiquement par `tests/test_single_llm.py`.

#### Configurer les scripts des *skills* (même daemon, variables séparées)

OpenCode pilote l'agent ; les scripts des *skills* qui parlent
*aussi* à Ollama (texte alternatif, balises meta, langage clair, FAQ,
traduction de sous-titres) lisent leurs propres variables d'environnement. **Aucun
chevauchement avec `OPENCODE_MODEL`** : réglez les deux ; les deux
doivent pointer sur le même daemon, mais le modèle peut différer. Chaque
appel au modèle passe par
[best-engine-ai-helper](https://github.com/warith-harchaoui/best-engine-ai-helper),
qui lit lui-même l'adresse du daemon :

| Variable | Lue par | Effet | Défaut |
|---|---|---|---|
| `BEST_LLM_BASE_URL` | best-engine-ai-helper, donc `make-alt`, `sprezzature-publish-meta`, `-plain`, `-faq` | URL du daemon. Doit correspondre à celui d'OpenCode. | `http://localhost:11434` |
| `OLLAMA_URL` | `sprezzature-audio-translate` et `-name` (défaut de leur `--url`), `sprezzature-publish-lint --ai` | URL du daemon pour ces trois-là. `make-alt`, `-meta` et `-plain` la lisent aussi, mais seulement pour la nommer dans leur message d'erreur. | `http://localhost:11434` |
| `OLLAMA_MODEL` | tout script basé Ollama | Échappatoire nu (surtout pour les tests). Le seul modèle autorisé est `qwen3-vl:8b`. | `qwen3-vl:8b` |
| `OPENCODE_MODEL` | OpenCode lui-même | Tag du modèle côté agent, mettez `qwen3-vl:8b`. | `qwen3-vl:8b` |

Le motif est volontairement ennuyeux : `qwen3-vl:8b` sur le même
daemon pour l'agent comme pour les scripts. `qwen3-vl:8b` étant
multimodal, le script de vision et les scripts texte le partagent :
pas de jonglage de modèle par préoccupation, pas de MLX (le framework d'apprentissage automatique d'Apple pour les puces des Mac).

```bash
# Un daemon, un modèle, pour tout.
export BEST_LLM_BASE_URL=http://localhost:11434
export OLLAMA_URL=http://localhost:11434
export OPENCODE_MODEL=qwen3-vl:8b
```

Choisissez OpenCode quand les coûts de jetons comptent, quand le
travail est en masse / répétitif (générer le texte alternatif d'une bibliothèque de
500 images, regénérer les balises meta à chaque commit, auditer un
site de 50 pages) ou quand la donnée ne doit pas quitter la
machine. Choisissez Claude Code quand le travail demande le
jugement d'un modèle frontière (synthèse design originale,
refactos ambigus, revue de code d'une bibliothèque inconnue).

### Modèle de confiance

En bref : le dépôt livre du texte et des scripts Python qui se lisent
de haut en bas en moins d'une heure. **Les releases taguées portent
des sommes de contrôle Secure Hash Algorithm (SHA, une empreinte du fichier qui change si un seul octet change)-256** (intégrité contre la corruption en
transit) ; elles ne sont **pas signées avec GPG (GNU Privacy Guard, l'outil libre de référence qui signe un fichier pour que chacun vérifie qui l'a produit)** ni attestées Sigstore
aujourd'hui. Si vous avez besoin d'authenticité au-delà d'une preuve
d'intégrité, construisez à partir d'un commit tagué que vous avez
relu vous-même : `scripts/release.sh` est dans l'arbre et reproductible,
et le workflow `release.yml` ne fait rien que le script ne fasse en
local. Voir [`SECURITY.md`](SECURITY.md) pour la note complète
chaîne d'approvisionnement.

### Complétion shell

Le pilote `sprezzature`, `sprezzature-skills` et toutes les commandes que
les dix briques installent sont en Click, donc embarquent la complétion
`bash` / `zsh` / `fish` gratuitement via l'astuce
`_<OUTIL>_COMPLETE=<shell>_source` de Click. Voir
[`sprezzature-cli/README.md`](sprezzature-cli/README.md#shell-completion) pour la
mise en place en une ligne par shell. Le même motif marche pour toute
commande de brique lancée directement (par exemple
`_SPREZZATURE_AUDIO_CAPTIONS_COMPLETE=zsh_source sprezzature-audio-captions`).

## Hooks pre-commit

Trois dépôts livrent un manifeste `.pre-commit-hooks.yaml`, donc un projet
câble ces portes dans [pre-commit](https://pre-commit.com/) avec un bloc
`repo:` chacun. Les autres auditeurs tournent en hooks `repo: local` sur la
commande installée.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/warith-harchaoui/sprezzature-publish
    rev: v1.5.0          # fixer une tag ; bumper via renovate / dependabot
    hooks:
      - id: sprezzature-publish-lint        # le Markdown
  - repo: https://github.com/warith-harchaoui/sprezzature-ui
    rev: v1.2.2
    hooks:
      - id: sprezzature-ui-i18n-audit       # chaînes hors de locales/i18n.yaml
  - repo: https://github.com/warith-harchaoui/sprezzature
    rev: v1.8.1
    hooks:
      - id: sprezzature-ui-validate-skill   # uniquement si vous livrez des skills
      - id: sprezzature-triggers-sync
  - repo: local
    hooks:
      - id: sprezzature-accessibility-lint
        name: a11y lint
        entry: sprezzature-accessibility-lint
        language: system
        files: '\.html?$'
      - id: sprezzature-ux-laws
        name: Laws of UX
        entry: sprezzature-ux-laws
        language: system
        files: '\.html?$'
        # args: [--fix] active les quatre réparations mécaniques
```

Un hook `repo: local` lance la commande depuis votre propre environnement :
faites-y d'abord `pip install sprezzature-accessibility sprezzature-ux-laws`.

## CLI → IHM, le cas d'usage phare

Le *skill* `sprezzature-cli-gui` part d'un outil en ligne de commande existant
et produit une IHM mono-page en JavaScript pur + Tailwind. Le workflow
lit le parseur d'arguments du CLI, classe chaque commande (action
unique / formulaire / streaming / liste), associe chaque flag à un
contrôle de formulaire, puis câble l'exécution sur l'hôte du projet
(Tauri, Electron, FastAPI, Express ou un proxy HTTP (protocole de transfert web) + événements envoyés par le serveur (SSE, une connexion par laquelle le serveur pousse de nouvelles lignes, comme un journal en direct) en stdlib).

Un exemple exécutable est livré dans
`sprezzature-cli-gui/assets/examples/cli-gui-demo/`. Pour le lancer :

```bash
cd sprezzature-cli-gui/assets/examples/cli-gui-demo
python server.py  # stdlib uniquement, ouvre http://localhost:8787
```

Pour une comparaison honnête face à Gradio / Streamlit / Tauri / Taipy,
voir `sprezzature-cli-gui/SKILL.md` → « Why this *skill*, not Gradio / Streamlit
/ Tauri / Taipy » et [LANDSCAPE.md](LANDSCAPE.md) § 7.

## Auteur

[Warith HARCHAOUI, Ph.D.](https://www.linkedin.com/in/warith-harchaoui/)

Dix ***skills*** Claude / OpenCode pour une seule pile
frontend : JavaScript pur, Tailwind CSS et la règle des trois Roboto
(Roboto / Roboto Serif / Roboto Mono). Conformes à la
[spécification Anthropic des *skills*](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf).

Un grand merci à :

  + [Audrey DEJOUX](https://www.behance.net/dreyadesign/projects),

  + [Laurent PANTANACCE](https://www.linkedin.com/in/pantanacce/),

  + [Auguste BAUM](https://www.linkedin.com/in/auguste-baum/),

  + [Julien BOYER](https://www.linkedin.com/in/julien-boyer-2a76878/) et
  
  + [Jérôme GOMBERT](https://www.linkedin.com/in/j%C3%A9r%C3%B4me-gombert-84675b1b/)


pour nos discussions fructueuses.

Palettes de couleurs issues de <https://deraison.ai/colors/>.

Les trois familles Roboto sont livrées dans
`sprezzature-ui/assets/fonts/roboto/`, `sprezzature-ui/assets/fonts/roboto-serif/`
et `sprezzature-ui/assets/fonts/roboto-mono/`, chacune sous SIL Open Font
License ; voir le fichier `OFL.txt` joint dans chaque dossier.

Les *skills* puisent également des connaissances dans les
[Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/),
[Google Material Design](https://material.io/design) et les
[Laws of UX](https://lawsofux.com/).

## Licence

**Berkeley Software Distribution (BSD-3-Clause, une licence libre permissive à trois clauses)**, la même licence que **scikit-learn**. Permissive :
utilisation, modification, redistribution, vente, intégration dans des
produits commerciaux. Les trois conditions sont (1) conserver la notice
de copyright dans les redistributions de code source, (2) la reproduire
dans la documentation des distributions binaires, (3) ne pas utiliser
le nom du détenteur du copyright pour endosser des produits dérivés
sans autorisation. Voir `LICENSE.md` pour le texte canonique. Les
trois familles Roboto (Roboto, Roboto Serif, Roboto Mono) restent sous
SIL Open Font License (voir le `OFL.txt` joint dans chaque dossier
`sprezzature-ui/assets/fonts/roboto*/`) ; la licence BSD-3-Clause ci-dessus
s'applique au code source, pas aux polices.

**Licence vs. attribution.** Les crédits d'auteur dans la documentation
sont une reconnaissance volontaire (pas la condition #3 de la licence).
Vous êtes libre de les retirer ou de les remplacer dans votre fork ;
les obligations BSD-3-Clause ci-dessus sont ce qui voyage avec le code.

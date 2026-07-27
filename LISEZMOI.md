


# Sprezzature

[🇫🇷](LISEZMOI.md) · [🇬🇧](README.md)

<p align="center">
  <img src="assets/logo.png" alt="Sprezzature — neuf skills Claude / OpenCode pour des frontends en JavaScript pur + Tailwind" width="240">
</p>

## De quoi s'agit-il ?

`sprezzature`, c'est **neuf *skills* Claude / OpenCode** qui cadrent
l'agent sur une seule pile frontend (JavaScript (JS) pur, Tailwind CSS,
et la règle des trois Roboto : Roboto pour les sans-serif, Roboto Serif
pour les serif, Roboto Mono pour le code) et lui fournissent un
système de design soigné.
Demander à l'agent de « construire une UI », « habiller ce CLI d'une
IHM », « transformer ce dossier de markdown en site » ou « auditer
l'accessibilité » oriente vers le bon *skill* et produit du code dans
la même pile : HTML (langage de balisage des pages web) sémantique,
variante `dark:` sur chaque élément
stylé, anneau de focus visible, garde-fous pour `prefers-reduced-motion`,
graphiques en Vega-Lite, texte alternatif rédigé selon les recommandations
du World Wide Web Consortium (W3C) et de sa Web Accessibility Initiative (WAI).

Les neuf *skills* :

| *Skill* | Quand l'installer | Phrases déclencheuses |
|---|---|---|
| **sprezzature-ui** | Toujours : il porte les conventions de pile (base technique) et les variables de design (design tokens). | « construis une UI », « crée un composant », « conçois une page », « fais un formulaire / modal / bouton / nav », « tableau de bord », « audite cette UI ». |
| **sprezzature-cli-gui** | Vous habillez des outils en ligne de commande (CLI) d'une interface graphique (IHM, interface homme-machine). | « habille ce CLI d'une IHM », « construis une UI pour mon script Python », « argparse vers IHM web ». |
| **sprezzature-publish** | Vous livrez des sites de doc, des landings, des meta-tags, des favicons. | « transforme ce dossier markdown en site », « meta tags », « favicons », « robots.txt », « sitemap », « llms.txt », « flux Atom », « langage clair », « réécris au niveau 6e ». |
| **sprezzature-accessibility** | Vous avez besoin d'un contrôle statique d'accessibilité (a11y). | « lint a11y », « vérif accessibilité HTML », « contrôle a11y statique », « lint WCAG-friendly », « a11y pre-commit ». |
| **sprezzature-colors** | Vous auditez le contraste, simulez le daltonisme ou voulez une palette sélectionnée avec éclaircissement / assombrissement perceptuels. | « vérif WCAG », « audit de contraste », « ma palette est-elle accessible », « aperçu daltonien », « deutéranope », « CVD », « OKLCH », « éclaircis cette couleur ». |
| **sprezzature-vision** | Vous rédigez un brouillon de texte alternatif conforme aux recommandations du W3C depuis des images, en local (pas de service en ligne / SaaS). | « texte alternatif », « décris cette image », « draft alt », « description d'image », « img sans alt ». |
| **sprezzature-audio** | Vous rédigez un brouillon de sous-titres (formats WebVTT et SubRip / SRT) pour `<video>` / `<audio>` en local (pas de SaaS). | « sous-titres », « transcris cette vidéo », « transcris cet audio », « WebVTT », « SRT », « fichier de sous-titres », « VTT », « piste sous-titres ». |
| **sprezzature-ux-laws** | Vous voulez un vocabulaire partagé pour vos décisions d'expérience utilisateur (UX) ET un auditeur pre-commit qui échoue sur les violations détectables des Laws of UX (Hick, Fitts, Miller, Jakob, Tesler, Aesthetic-Usability, Selective Attention, Doherty, Choice Overload). | « Laws of UX », « Hick / Fitts / Miller / Jakob / Tesler / Peak-End / Postel / Paradox of the Active User », « audite ma nav / mon formulaire / ma page de prix », « cet onboarding combat-il l'utilisateur actif ». |
| **sprezzature-figures** | Vous produisez des figures pour la science des données (**Vega-Lite d'abord**, image vectorielle SVG écrit avec soin quand la grammaire ne suffit plus, matplotlib seulement en dernier recours), des graphiques d'explicabilité (explications additives de Shapley / SHAP, Shapash / TimeSHAP, explications locales interprétables / LIME), des estimations d'effet causal (DoWhy / EconML), des diagrammes TikZ / Mermaid, des cartes thématiques ou des cartes de zones de contrôle (« situation ») pour n'importe quelle région, affinés par la **Ralph Eyeball Loop** (rendre → regarder → corriger la source), avec un auditeur pre-commit pour les fautes de visualisation de données et des niveaux d'accessibilité à la vision des couleurs sur chaque figure. | « make a figure », « prefer vega », « render this diagram », « mermaid diagram », « ralph eyeball loop », « no ascii art », « SHAP plot », « choropleth », « world map », « situation map », « areas of control », « DoWhy », « DAG », « audit this figure ». |

Les *skills* compagnons héritent des règles de pile de `sprezzature-ui`.
N'installez que ceux dont vous avez besoin.

> **Quelle phrase déclenche quel *skill* ?** Voir
> [`TRIGGERS.md`](TRIGGERS.md), généré depuis chaque `SKILL.md`,
> liste toutes les phrases garanties par leur description avec le
> *skill* qu'elles activent.

## Premiers pas

Sprezzature, ce sont des *skills* pour **Claude Code** ou **OpenCode**. Installez ceux
que vous voulez, puis demandez en français. Le *skill* **produit**
l'artefact et l'**audite**.

```bash
# 1. Récupérez la dernière release (mettez VERSION au dernier tag de la page des releases)
VERSION=0.33.0
curl -L https://github.com/warith-harchaoui/sprezzature/releases/download/v${VERSION}/sprezzature-skills-${VERSION}.tar.gz | tar xz

# 2. Copiez les skills voulus dans votre environnement
#    Claude Code → ~/.claude/skills   ·   OpenCode → ~/.opencode/skills
mkdir -p ~/.claude/skills
cp -r sprezzature-ui sprezzature-figures ~/.claude/skills/
```

Ensuite, en session, il suffit de demander :

- « rends cette page accessible » → **sprezzature-accessibility** audite le HTML et liste quoi corriger.
- « fais une figure de ce CSV » → **sprezzature-figures** la dessine, puis audite le graphique.
- « transforme ce CLI en interface » → **sprezzature-cli-gui** échafaude une interface utilisable.

Toutes les options (vérification des sommes de contrôle, tarballs par *skill*, la voie
OpenCode + Ollama local à zéro token, mises à jour, nettoyage) sont dans
[Installation](#installation) ci-dessous.

## Docs & site web

Les guides pour humains vivent dans [`docs/`](docs/), une page par *skill*
([UI](docs/UI.md) · [CLI](docs/CLI.md) · [publish](docs/PUBLISH.md) ·
[accessibility](docs/ACCESSIBILITY.md) · [colors](docs/COLORS.md) ·
[vision](docs/VISION.md) · [audio](docs/AUDIO.md) · [UX-laws](docs/UX-LAWS.md) ·
[figures & cartes](docs/FIGURES.md)), chacune un simple pointeur vers le
`SKILL.md` du *skill*, ses `references/` et sa recette dans `EXAMPLES.md` (aucune
duplication). `SKILL.md` est l'artefact *agent* ; `docs/` est pour les humains.

Pour le *pourquoi* de la suite, les convictions de conception qui
traversent chaque *skill*, voyez [`PHILOSOPHIE.md`](PHILOSOPHIE.md)
(English : [`PHILOSOPHY.md`](PHILOSOPHY.md)).

Un site statique déployable, multi-pages, construit avec les *skills* `front-*`
eux-mêmes (house style sprezzature-ui, meta / favicons / sitemap / llms.txt de
sprezzature-publish, palette sprezzature-colors, sprezzature-accessibility clean, un vrai toggle
🌞/🌛), se trouve dans [`web/`](web/) et se publie sur
<https://harchaoui.org/warith/sprezzature/>. Il a une page de détail par *skill* (make /
audit / triggers / bibliothèque de références) et une **galerie de figures**
dédiée qui rend tout le catalogue `sprezzature-figures`. La galerie porte un
**visualiseur « Voir pour… »** qui applique une simulation vivante de la vision
des couleurs sur les figures par défaut&#8239;: il simule ce que voit un lecteur
daltonien, il ne substitue pas une autre figure. Un contrôle **plein écran**
partagé permet d'ouvrir n'importe quel graphique en grand.

## Fonctionnalités — ce qui est inhabituel pour un *skill* Claude

La plupart des *skills* Claude, y compris les `document-skills` d'Anthropic
(docx, pdf, pptx, xlsx) et les `example-skills` (artifacts, GIFs, serveurs Model Context Protocol (MCP),
design), ne font que du **make** : le modèle produit un artefact. `sprezzature` est
conçu autrement et ces traits le distinguent :

- **Make *et* audit.** Chaque *skill* associe la génération à un **auditeur
  déterministe** qui sort en erreur au moindre problème (il y en a six :
  `lint_a11y`, `audit_contrast`, `audit_laws_of_ux`, `audit_figure`,
  `audit_i18n`, `lint_markdown`). Aucun *skill* officiel d'Anthropic ne livre un
  linter statique comme raison d'être ; ici c'est la moitié de la conception.
- **Des gardes d'intégration continue (CI) / pre-commit, pas du ressenti.** Les auditeurs émettent du JSON (notation d'objets JavaScript)
  + des codes de sortie et se livrent via un manifeste
  [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) : un seul bloc `repo:` et
  ils bloquent les commits, quel que soit l'auteur (humain ou machine).
- **Intelligence artificielle (IA) locale, zéro fuite vers des services en ligne (SaaS).** Le texte alternatif tourne sur un modèle de
  vision Ollama local ; les sous-titres / la diarisation sur une build
  whisper.cpp locale. Rien ne quitte la machine ; les *skills* officiels passent
  d'abord par le cloud Claude.
- **Générateurs déterministes.** palette → config Tailwind, CLI → interface graphique (GUI), jeux
  d'icônes favicon / application web progressive (PWA), sitemaps / flux et `locales/i18n.yaml` : des artefacts
  reproductibles qu'un modèle ne dériverait pas à l'octet près.
- **Durci comme un produit, pas une démo.** Une vraie suite pytest + une couche
  d'évaluation IA (DeepEval), de la CI sur Python 3.10–3.12, des archives de release
  par *skill* vérifiées par somme de contrôle et un validateur de conformité à la spécification, face
  à des exemples de niveau démonstration.
- **Portable entre environnements d'exécution.** Un même dossier de *skill* sert **Claude Code** et
  **OpenCode** ; les chemins IA visent des modèles locaux pour qu'un modèle
  OpenCode plus petit suive un script au lieu d'en inventer un.
- **Internationalisation (i18n) unifiée.** Les chaînes d'interface *et* les prompts du grand modèle de langage (LLM) vivent dans un
  seul `locales/i18n.yaml`, appliqué côté make comme côté audit.

## Deux modes — make et audit

Chaque *skill* front-* appartient à l'une (ou aux deux) moitiés d'une
seule boucle : **make** (produire l'artefact) et **audit** (le
vérifier). Le tableau indique quand charger chaque *skill* et ce qui
reste en feuille de route.

| *Skill* | Make (générer) | Audit (porte) |
|---|---|---|
| **sprezzature-ui** | `references/` + `assets/components/` : guide de génération HTML / Tailwind / visualisation de données | `scripts/validate.py`, `references/checklist.md`, `anti-patterns.md`, `ergonomics-criteria.md` |
| **sprezzature-cli-gui** | `scripts/cli_to_gui.py` (émetteur CLI → HTML, adaptateurs argparse + Click + `--from-help`) + `assets/examples/cli-gui-demo/` (ossature exécutable) | Accouplez `sprezzature-accessibility` + `sprezzature-ux-laws` sur le HTML produit (l'émetteur est son propre client ; sa sortie passe les deux audits avec zéro constat). |
| **sprezzature-publish** | `favicons.py`, `meta_from_ollama.py`, `site_indexes.py`, `plain_language.py`, `md_to_html.py`, `narrate.py` | `lint_markdown.py` |
| **sprezzature-accessibility** | _(rien : voir `sprezzature-ui` pour les templates, `sprezzature-vision` pour les alt, `sprezzature-audio` pour les sous-titres)_ | `lint_a11y.py` (14 règles, stdlib seul) |
| **sprezzature-colors** | `palette_to_tailwind.py` (CSV → tailwind.config.js), `accessibility_levels.py` (projette la palette en `universal` / `high-contrast` / `monochrome` / une variante déficience de la vision des couleurs) | `audit_contrast.py`, `simulate_cvd.py` (mosaïque + panneau de luminance `--grayscale`) |
| **sprezzature-vision** | `alt_from_ollama.py` (texte alternatif conforme W3C via Ollama local) | _(présence de `alt=` vérifiée par `sprezzature-accessibility`)_ |
| **sprezzature-audio** | `captions_from_whisper.py` (WebVTT / SRT via whisper.cpp local) | _(présence de `<track>` vérifiée par `sprezzature-accessibility`)_ |
| **sprezzature-ux-laws** | `references/laws-of-ux.md` (guide des 30 lois) | `audit_laws_of_ux.py` (Hick / Miller / Fitts / Jakob / Tesler / …) |
| **sprezzature-figures** | `make_figure.py` (valeurs séparées par des virgules / CSV → Vega / matplotlib), `explain_model.py` (aiguilleur SHAP / Shapash / TimeSHAP / LIME), `causal_estimate.py` (boucle DoWhy + moteurs EconML + rendu de graphe orienté sans cycle / DAG), `make_situation_map.py` (config YAML → carte de zones de contrôle en couches pour n'importe quelle région, SVG + PNG), `render_diagram.py` (Vega / TikZ / Mermaid / image vectorielle SVG auto-routés → image matricielle PNG / SVG / format de document portable PDF pour la Ralph Eyeball Loop&#8239;; catalogue rendu dans `docs/FIGURES.md`), `ralph_eyeball_loop.py` (rendre → regarder → corriger n'importe quel visuel produit par du code, en mode agent ou `--local` hors ligne), `install_figures.py` (installeur par palier). Chaque générateur accepte un niveau `--accessibility` (`universal` par défaut, strictement identique à l'octet près) | `audit_figure.py` (missing-axis-title, dual-y-axis, truncated-baseline, pie-3d, rainbow-palette, cvd-unsafe, missing-polarity, chartjunk, role-img-missing) |

Le tableau est honnête sur les manques. Les cellules vides marquent
de vraies entrées de feuille de route, pas des oublis.

## À qui ça s'adresse

`sprezzature` vise quatre publics concrets. Chaque ligne est un argumentaire
autonome : si l'un d'eux correspond à votre situation, le *skill*
associé se justifie déjà à lui seul.

1. **Développeurs en solo sans designer.** Des choix par défaut
   assumés pour arrêter de tergiverser sur les variables de design (design tokens) : installez
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
4. **Sites de documentation bilingues (EN/FR par défaut ; la paire
   est configurable).** `sprezzature-publish` garde la typographie et la
   tonalité alignées sur deux langues et produit en une passe balises meta
   + favicons + sitemap. Changez la paire (EN/DE, EN/JA, EN/ES,
   …) en éditant une seule variable de configuration ; voir, dans chaque
   `SKILL.md`, la section « Changing the language pair ».

Ce **n'est pas** le bon choix pour :

- Le travail de marque pour une app grand public qui demande une
  identité visuelle propre.
- Les landings marketing où Webflow ou Framer sont plus rapides.
- Les apps où l'équipe a déjà choisi React / Vue / Svelte ; préférez
  shadcn / Headless UI / Mantine.
- Les sites de doc versionnés à plusieurs centaines de pages ;
  préférez MkDocs Material, Hugo ou Astro.

Pour les alternatives par catégorie et l'aide à la décision « est-ce
que `sprezzature` est le bon outil ? », voir [PAYSAGE.md](PAYSAGE.md) (anglais :
[LANDSCAPE.md](LANDSCAPE.md)). Le document ouvre sur une table de
**positionnement concurrentiel** (projets × critères, notés 1–5 ⭐️) qui alimente
[standpoint](https://github.com/warith-harchaoui/standingpoint) pour tracer une
carte 2-D de la place de `sprezzature`. Pour des sites réels déjà livrés sur cette pile, voir
[GALLERY.md](GALLERY.md). Pour des recettes copier-coller par *skill*
(avec la sortie attendue), voir [`EXAMPLES.md`](EXAMPLES.md).

## Ce que les *skills* garantissent

- Le code produit est en JavaScript pur (modules ES, `<dialog>` natif,
  custom elements quand c'est justifié). Pas de React, Vue, Svelte,
  Next.js, Nuxt, Angular ni Solid.
- Le code utilise des classes utilitaires Tailwind avec des variables de design (design tokens)
  sémantiques (`bg-brand-blue`, `text-label-primary`). Pas de couleur
  hexadécimale brute dans le balisage.
- Le code applique la **règle des trois Roboto** : exactement trois
  polices téléchargées, toutes issues de la super-famille Roboto :
  **Roboto** (sans-serif / UI / texte courant), **Roboto Serif**
  (longform éditorial / pages très textuelles), **Roboto Mono**
  (`<code>`, `<pre>`, panneaux terminal, logs). Aucune autre famille
  téléchargée n'est admise (ni Inter, ni Montserrat, ni IBM Plex, ni
  JetBrains Mono). Les trois familles partagent par construction les
  mêmes métriques et la même hauteur d'x, si bien que les surfaces mêlant prose
  et code restent cohérentes typographiquement. Toutes sont
  auto-hébergées (pas de réseau de diffusion de contenu / CDN Google Fonts en production) ; les fichiers de police Web Open Font Format version 2 (WOFF2)
  et leur licence libre OFL (SIL Open Font License) vivent sous `sprezzature-ui/assets/fonts/roboto/`, `…/roboto-serif/`
  et `…/roboto-mono/`.
- Le code pose une variante `dark:` sur chaque élément stylé,
  privilégie `<button>` / `<a>` / `<label>` / `<dialog>` / `<form>`,
  expose un anneau de focus visible, respecte `prefers-reduced-motion`,
  et garantit une cible tactile d'au moins 44 × 44 px.
- Le code expose un **toggle 🌞 Light / 🌚 Dark / 🌗 Auto**
  (placement canonique : haut-droite du header sticky → coin
  bas-droite du footer → ancrage fixed bottom-right quand il n'y a
  pas de header). **Auto est le défaut**, pour qu'un visiteur frais
  hérite du choix de son système d'exploitation (OS) et ne soit jamais surpris par un thème
  forcé. Composant :
  `sprezzature-ui/assets/components/theme-toggle.html`. Câblage :
  `sprezzature-ui/references/stack-vanilla-js.md` § « Theme switching ».
- Les choix de couleur renvoient aux palettes de
  `sprezzature-ui/references/color-psychology.md` (source :
  <https://harchaoui.org/warith/colors/>).
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
  contexte** via `langdetect` ; pas de langue par défaut configurée ;
  passez `--lang` pour en forcer une. Pour les chaînes d'interface et
  les prompts traduisibles, utilisez un seul catalogue
  `locales/i18n.yaml` (voir `sprezzature-ui/scripts/i18n_make.py` et
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

Photographie de l'état de chaque surface. Les neuf dossiers
de *skills* sont stables ; la seule zone en travaux est l'**audio /
sous-titres** (sprezzature-audio, vidéo → texte). La **narration audio**
(sprezzature-publish, texte → audio) est stable et explicitement encadrée
comme amélioration éditoriale optionnelle, pas exigence WCAG.

| Domaine | État | Notes |
|---|---|---|
| `sprezzature-ui` (règles de pile, variables de design, composants, visualisation de données, checklist) | Stable | Les 9 règles dures documentées ; `validate.py` stdlib uniquement ; couvert par `tests/test_validate.py`. |
| `sprezzature-cli` (pilote `sprezzature` unifié, complétion shell) | Stable | Basé sur Click ; transmission du `--help` corrigée en 0.3.0 (test de non-régression en 0.3.1). |
| `sprezzature-cli-gui` (CLI → IHM, phare) | Stable (*skill* + démo exécutable) | `assets/examples/cli-gui-demo/` tourne de bout en bout. Durcissement production (auth, rate-limit, sandbox) délibérément laissé à l'hôte. |
| `sprezzature-publish` (site Markdown, meta, favicons, indexes, langage clair, narration audio) | Stable | 11 scripts publics couvrant les quatre artefacts cœur (favicons, meta, indexes, langage clair) + Markdown → HTML + lint Markdown + pipeline narration audio (orchestrateur, wrappers OpenVoice et Chatterbox, sélecteur de voix, installeur). Couverture déterministe large (favicons, site-indexes, meta, langage clair, lint, narration) ; suite d'éval pour meta + langage clair. |
| `sprezzature-accessibility` : lint | Stable (renommé depuis `sprezzature-a11y` en 0.9.0) | Lint a11y statique 14 règles, stdlib uniquement. Désormais resserré au lint après les sorties color / vision / audio. |
| `sprezzature-colors` : audit contraste, simulation de déficience de la vision des couleurs (DVC), palette sélectionnée, éclaircissement / assombrissement perceptuels | Stable (nouveau en 0.7.0) | Correcteur de contraste par voisin dans l'espace colorimétrique perceptuel OKLCH (clarté (L), chroma (C) et teinte (H)), matrices DVC de Machado, CSV palette unifiée (base Apple + projections émotion / concept / psychologie), module `_colors` stdlib uniquement, classe `Color`. Sorti de `sprezzature-accessibility` pour un périmètre plus clair. |
| `sprezzature-vision` : texte alternatif W3C via vision Ollama locale | Stable (nouveau en 0.8.0) | Modèle `qwen3-vl:8b` via Ollama (le seul LLM autorisé). Arbre de décision par objectif, biais par texte environnant + vocabulaire projet, cache disque. Sorti de `sprezzature-accessibility` pour un périmètre plus clair. Éval texte alternatif sur fixtures Wikipedia. |
| `sprezzature-audio` : **sous-titres WebVTT / SRT via whisper.cpp local** | **En travaux / à faire** (sorti en 0.9.0) | `captions_from_whisper.py` est fonctionnel ; ce qui manque, ce sont les mesures de référence de taux d'erreur sur les mots (WER) par langue (`en` / `fr` / `es` câblés via l'extracteur, mesures pas encore publiées), le clip utilisateur `vocab-biasing-clip.wav` et une révision prévue de l'intégration whisper.cpp via `pdbms`. Voir [Roadmap](CHANGELOG.md#roadmap). |
| `LISEZMOI.md` (README français) | Stable | À parité structurelle avec le README EN : même ordre des sections, contenu maintenu en synchronisation à chaque release. |

Pour le détail par release (et la suite prévue), voir [`CHANGELOG.md`](CHANGELOG.md).

## Entrées → sorties

Ce que vous donnez à l'agent et ce qu'il vous renvoie. Chaque ligne
est un flux autonome ; prenez celle qui vous concerne, ignorez le
reste.

| Vous fournissez | Phrase | *Skill* | Sortie |
|---|---|---|---|
| Un CLI fonctionnel (`tool --help`, source avec `argparse` / `click` / `clap` / `commander` / `cobra`) | « Habille ce CLI d'une IHM » + chemin du projet | `sprezzature-cli-gui` | Page unique `index.html` + `app.js` + Tailwind CSS, sous-commandes mappées en formulaires / flux / tables, exécution câblée sur votre hôte (Tauri / Electron / FastAPI / Express / bouchon navigateur). Roboto + Roboto Mono auto-hébergées. |
| Un dossier de fichiers Markdown (README, `docs/**`, articles) | « Transforme ces fichiers markdown en site » | `sprezzature-publish` | Site statique : une page HTML par `.md`, barre supérieure collante, sommaire latéral pour `docs/`, mode sombre, favicons, balises `<meta>`, `robots.txt` + `sitemap.xml` + `llms.txt` + flux Atom. |
| Une demande libre (« bouton primaire », « dialogue de confirmation », « page réglages ») | « Construis un `<composant>` » | `sprezzature-ui` | HTML sémantique + Tailwind + JS minimal, anneau de focus, variante `dark:`, zone tactile 44 × 44 px, fermeture par `Échap`, garde-fou `prefers-reduced-motion`. |
| Un jeu de données (CSV, JSON, quelques lignes collées) | « Trace ça » / « Tableau de bord pour X » | `sprezzature-ui` | Spec Vega-Lite v5 JSON + enveloppe `<figure>`. Style maison, palette de `color-psychology.md`, axes avec polarité, `role="img"`. |
| Une page HTML existante ou une capture d'écran | « Audite » / « Vérif WCAG » / « Rends ça moins IA » | `sprezzature-ui` (anti-patterns, ergonomie) + `sprezzature-accessibility` (lint) + `sprezzature-colors` (contraste, daltonisme) | Constats au regard des 8 critères ergonomiques + catalogue d'anti-patterns ; diffs concrets ; checklist pré-livraison ; sorties `lint_a11y` + `audit_contrast` + `simulate_cvd`. |
| Une image (`*.png`, `*.jpg`, …) | « Texte alternatif pour cette image » | `sprezzature-vision` | Texte alternatif conforme W3C dans la bonne catégorie (informatif / décoratif / fonctionnel / texte / complexe / groupe), rédigé dans la langue de la page, marqué `data-alt-source="ai"`. |
| Un fichier audio ou vidéo (`.mp4`, `.wav`, `.mp3`, …), **en travaux** | « Sous-titres / transcription » | `sprezzature-audio` *(en travaux)* | Sous-titres WebVTT / SRT / texte brut depuis whisper.cpp local, avec biais de vocabulaire issu du projet. Extrait `<video>` + `<track kind="captions">` à coller. Le script et les tests sont là aujourd'hui ; les baselines WER par langue et le clip de référence pour le biais de vocabulaire sont encore à collecter ; voir [État d'avancement](#état-davancement). |
| Un logo (`logo.png` / `.svg`) | « Jeu de favicons » / « Icônes PWA » | `sprezzature-publish` | `favicon.svg` + `.ico` + lot de PNG + `apple-touch-icon.png` + icône PWA masquable + `site.webmanifest` + extrait `head.html`. |
| Une description d'objectif ou une page HTML | « Meta tags » / « SEO » / « OG card » / « GEO » / « llms.txt » / « AI Overview » | `sprezzature-publish` | **Pour le référencement naturel (SEO) :** titre + description + balises Open Graph (OG) + Twitter Card + Schema.org en JSON pour données liées (JSON-LD) (JSON sur la sortie standard) ; voir [les trois piliers de Google Search Essentials](https://developers.google.com/search/docs/essentials) appliqués dans `sprezzature-publish/references/seo-essentials.md`. **Pour l'optimisation pour moteurs génératifs (GEO : surfaces de réponses AI Overview / Gemini / ChatGPT)** : `llms.txt` est émis par `scripts/site_indexes.py` aux côtés de `robots.txt` + `sitemap.xml` + flux Atom / RSS, donc le site embarque un résumé Markdown lisible par les LLM dès qu'une commande « transforme ce dossier en site » se termine. Mêmes robots, mêmes permissions dans `robots.txt` ; aucune balise meta « AI » n'existe ; toute affirmation contraire est fausse. |
| Du texte d'IHM brut | « Langage clair » / « Réécris au niveau 6e » | `sprezzature-publish` | Même sens, voix marketing retirée, longueur de sortie ≤ 1,1× l'original. |
| Une palette JSON | « Audit de contraste » / « Ma palette est-elle accessible ? » | `sprezzature-colors` | Chaque paire `(label, surface)` parcourue, échecs listés avec la correction OKLCH voisine la plus proche. Sortie 1 sur échec. |
| Une page finalisée / capture d'écran | « Vérif pré-livraison » | `sprezzature-ui` + `sprezzature-accessibility` + `sprezzature-colors` | La porte `checklist.md` exécutée ; lint + contraste + daltonisme passent ; texte / animation / performance vérifiés. |

> Pas sûr quelle ligne correspond ? Décrivez l'entrée en français courant. L'arbre de décision de chaque `SKILL.md` mappe les formulations vers les workflows.

## Installation

Les *skills* suivent la [spécification Anthropic des *skills*](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
et sont lus nativement par **Claude Code** et **OpenCode**. N'installez
que ceux qui vous servent.

Les flux Claude Code et OpenCode sont **identiques sauf pour le
dossier d'install** : les deux environnements d'exécution lisent les `SKILL.md` dans
un dossier par *skill* et les mêmes archives servent les deux. La
procédure ci-dessous montre une voie ; le second environnement d'exécution est une
substitution d'une ligne.

> **Variables partagées.** Remplacez `<RUNTIME>` par `claude` ou
> `opencode`. Épinglez `VERSION` sur la dernière tag ; voir
> [releases](https://github.com/warith-harchaoui/sprezzature/releases).

### 1. Téléchargez une release taguée (somme de contrôle vérifiée)

```bash
VERSION=0.33.0
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
cp -r sprezzature-accessibility ~/.${RUNTIME}/skills/   # uniquement pour lint a11y statique
cp -r sprezzature-colors        ~/.${RUNTIME}/skills/   # uniquement pour contraste WCAG / CVD / palette
cp -r sprezzature-vision        ~/.${RUNTIME}/skills/   # uniquement pour alt text (Ollama local)
cp -r sprezzature-audio         ~/.${RUNTIME}/skills/   # uniquement pour sous-titres (whisper.cpp local)
cp -r sprezzature-ux-laws       ~/.${RUNTIME}/skills/   # uniquement pour l'audit Laws-of-UX
cp -r sprezzature-figures       ~/.${RUNTIME}/skills/   # uniquement si vous produisez des figures dataviz / SHAP / DoWhy
```

Installez dans **les deux** environnements d'exécution si vous alternez entre eux :
même dossier copié dans deux chemins.

### 3. Vérifiez

```bash
# Un skill est installé et son SKILL.md est sur disque :
ls ~/.${RUNTIME}/skills/sprezzature-ui/SKILL.md

# Optionnel — si vous avez aussi cloné le dépôt, vérifiez chaque
# skill installé contre la spécification Anthropic (stdlib + PyYAML,
# pas de réseau) :
python3 scripts/validate_all.py
```

L'environnement d'exécution lit la description du `SKILL.md` de chaque *skill* au
démarrage de la conversation ; les phrases correspondantes activent
automatiquement le *skill*. Voir [`TRIGGERS.md`](TRIGGERS.md) pour
l'index par phrase.

### Nettoyage — retirer les *skills* obsolètes ou renommés

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
dossier `front-*` qui n'est plus livré par ce dépôt.

### Mise à jour

Recommencez les étapes 1–3 avec la nouvelle `VERSION`. Le nom du
dossier installé est stable, donc chaque `cp -r` écrase l'install
précédente sur place ; pas de suppression manuelle entre versions,
sauf quand un *skill* est **renommé** (utilisez l'aide de nettoyage
ci-dessus dans ce cas). Les renommages sont listés dans
[`CHANGELOG.md`](CHANGELOG.md).

### Installation depuis les sources (contributeur / développeur)

Pour itérer sur les *skills* ou pour épingler un commit qui n'est
pas encore tagué, clonez et copiez depuis l'arbre de travail. Pas
de vérification de somme de contrôle : c'est à vous de garantir
le bon commit cloné.

```bash
git clone https://github.com/warith-harchaoui/sprezzature.git
cd sprezzature
python3 -m pip install -r requirements-dev.txt   # PyYAML + pytest
python3 -m pytest                                # suite complète déterministe
python3 scripts/validate_all.py                  # tous les 9 skills, YAML + contenu

# Reflète l'étape 2 ci-dessus :
RUNTIME=claude   # ou opencode
mkdir -p ~/.${RUNTIME}/skills
for skill in $(grep -v '^[[:space:]]*#' SKILLS.txt | grep -v '^[[:space:]]*$'); do
    cp -r "$skill" ~/.${RUNTIME}/skills/
done
```

`CONTRIBUTING.md` reprend le même flux côté contributeur.

### OpenCode + Ollama local — l'approche zéro token

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
est en-dessous de Claude / GPT-4 sur le raisonnement difficile ;
les *skills* front-* compensent parce qu'ils chargent l'*opinion* en
amont (règles de pile, audits, phrases déclencheuses) : le modèle
n'a plus qu'à suivre un script, pas à l'inventer. Pour le travail
UI, le texte alternatif, les sous-titres, les audits de contraste, les
vérifications Laws of UX, la voie locale est aujourd'hui réellement
utilisable.

L'ajustement avec ce dépôt est direct : **trois *skills* front-*
parlent déjà à un daemon Ollama local** pour leurs surfaces IA :
`sprezzature-vision` (texte alternatif, `qwen3-vl:8b`),
`sprezzature-publish/meta_from_ollama.py` (meta de page),
`sprezzature-publish/plain_language.py` (réécriture de texte). Quand vous
lancez OpenCode contre le même daemon Ollama, toute la boucle
(agent + scripts pilotés par les *skills*) utilise un seul modèle
local. Zéro appel externe.

```bash
# Démarrage rapide. Suppose Ollama + un binaire OpenCode dans le PATH.
ollama serve &         # démarrer le daemon
ollama pull qwen3-vl:8b  # le seul modèle — boucle d'agent ET tous les scripts
```

Un seul modèle pour toute la pile : il pilote la boucle d'agent
OpenCode ET sert tous les scripts front-* basés Ollama
(`alt_from_ollama`, `meta_from_ollama`, `plain_language`,
`narrate_post`). Même daemon, même tag, même réponse à « quel
modèle tourne ? » : `qwen3-vl:8b`.

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
`@ai-sdk/openai-compatible` parle nativement ; pas de plugin à
installer en plus de la config. Listez exactement les tags que
vous avez pull-és (faites `ollama list` pour les voir) ;
OpenCode ne les découvre pas automatiquement.

Puis lancez OpenCode sur le provider local :

```bash
opencode run "construis-moi un bouton CTA principal" \
    -m local-ollama/qwen3-vl:8b

# → ~/.opencode/skills/front-* se chargent automatiquement.
# → Les scripts sprezzature-vision / sprezzature-publish basés Ollama
#   tapent dans le même daemon pour leurs traitements.
# → Coût : 0 token ; rien ne quitte la machine.
```

Un seul modèle, `qwen3-vl:8b`, sert la boucle d'agent ET tous les
scripts : même daemon, même tag. `qwen3-vl:8b` est multimodal, donc le
script de vision (texte alternatif) tourne sur le même modèle que les scripts
texte. Il n'y a rien d'autre à choisir.

#### Choix du modèle — pourquoi Qwen3-VL 8B (Q4_K_M)

Le modèle unique est **Qwen3-VL 8B**, quantification Q4_K_M, récupéré par
`ollama pull qwen3-vl:8b` (~6,1 Go). Il a été choisi selon quatre critères pour
une boîte à outils bilingue, riche en images et locale sur Mac : **vision**,
**français**, **reconnaissance optique de caractères (OCR) / graphiques**, et
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
*aussi* à Ollama (texte alternatif, balises meta, langage clair, narration
audio) lisent leurs propres variables d'environnement. **Aucun
chevauchement avec `OPENCODE_MODEL`** : réglez les deux ; les deux
doivent pointer sur le même daemon, mais le modèle peut différer :

| Variable | Lue par | Effet | Défaut |
|---|---|---|---|
| `OLLAMA_URL` | tout script basé Ollama | URL du daemon. Doit correspondre à celui d'OpenCode. | `http://localhost:11434` |
| `OLLAMA_MODEL` | tout script basé Ollama | Échappatoire nu (surtout pour les tests). Le seul modèle autorisé est `qwen3-vl:8b`. | `qwen3-vl:8b` |
| `OPENCODE_MODEL` | OpenCode lui-même | Tag du modèle côté agent, mettez `qwen3-vl:8b`. | `qwen3-vl:8b` |

Le motif est volontairement ennuyeux : `qwen3-vl:8b` sur le même
daemon pour l'agent comme pour les scripts. `qwen3-vl:8b` étant
multimodal, le script de vision et les scripts texte le partagent :
pas de jonglage de modèle par préoccupation, pas de MLX.

```bash
# Un daemon, un modèle, pour tout.
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
des sommes de contrôle Secure Hash Algorithm (SHA)-256** (intégrité contre la corruption en
transit) ; elles ne sont **pas signées GPG** ni attestées Sigstore
aujourd'hui. Si vous avez besoin d'authenticité au-delà d'une preuve
d'intégrité, construisez à partir d'un commit tagué que vous avez
relu vous-même : `scripts/release.sh` est dans l'arbre et reproductible,
et le workflow `release.yml` ne fait rien que le script ne fasse en
local. Voir [`SECURITY.md`](SECURITY.md) pour la note complète
chaîne d'approvisionnement.

### Complétion shell

Le pilote `sprezzature` (et les quatre CLI par-script migrés à Click :
`alt_from_ollama.py`, `captions_from_whisper.py`,
`meta_from_ollama.py`, `plain_language.py`) embarquent la complétion
`bash` / `zsh` / `fish` gratuitement via l'astuce
`_<OUTIL>_COMPLETE=<shell>_source` de Click. Voir
[`sprezzature-cli/README.md`](sprezzature-cli/README.md#shell-completion) pour la
mise en place en une ligne par shell. Le même motif marche pour les
CLI par-script lancés directement (par exemple
`_ALT_FROM_OLLAMA_COMPLETE=zsh_source alt_from_ollama.py`).

## Hooks pre-commit

Le dépôt fournit un manifeste `.pre-commit-hooks.yaml` à la racine,
donc n'importe quel projet peut câbler les portes d'audit front-*
dans [pre-commit](https://pre-commit.com/) avec un seul bloc `repo:`,
sans chemins de scripts en dur, sans installation au-delà de
`pre-commit install`.

```yaml
# .pre-commit-config.yaml — ajouter le dépôt en une entrée
repos:
  - repo: https://github.com/warith-harchaoui/sprezzature
    rev: v0.33.0          # fixer une tag — bumper via renovate / dependabot
    hooks:
      - id: sprezzature-accessibility-lint
      - id: sprezzature-ux-laws-audit
      - id: sprezzature-publish-lint-markdown
      - id: sprezzature-ui-validate-skill   # uniquement si vous livrez des skills
      # Ajoutez --fix en hook arg pour activer les auto-correctifs sûrs
      # ex. - id: sprezzature-ux-laws-audit
      #        args: [--fix]
```

Les hooks sont stdlib-only côté Python (pre-commit installe chacun
dans son propre venv isolé). Les deux hooks couleur déclarent Pillow
via `additional_dependencies`. Chaque hook respecte le filtre de type
de fichier transmis par pre-commit (HTML pour les hooks a11y + Laws
of UX ; Markdown pour le hook publish).

## CLI → IHM, le cas d'usage phare

Le *skill* `sprezzature-cli-gui` part d'un outil en ligne de commande existant
et produit une IHM mono-page en JavaScript pur + Tailwind. Le workflow
lit le parseur d'arguments du CLI, classe chaque commande (action
unique / formulaire / streaming / liste), associe chaque flag à un
contrôle de formulaire, puis câble l'exécution sur l'hôte du projet
(Tauri, Electron, FastAPI, Express ou un proxy HTTP (protocole de transfert web) + événements envoyés par le serveur (SSE) en stdlib).

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

[Warith Harchaoui, Ph.D.](https://www.linkedin.com/in/warith-harchaoui/)

Neuf ***skills*** Claude / OpenCode pour une seule pile
frontend : JavaScript pur, Tailwind CSS et la règle des trois Roboto
(Roboto / Roboto Serif / Roboto Mono). Conformes à la
[spécification Anthropic des *skills*](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf).

Un grand merci à :

  + [Audrey Dejoux](https://www.behance.net/dreyadesign/projects),

  + [Laurent Pantanacce](https://www.linkedin.com/in/pantanacce/),

  + [Auguste Baum](https://www.linkedin.com/in/auguste-baum/),

  + [Julien Boyer](https://www.linkedin.com/in/julien-boyer-2a76878/) et
  
  + [Jérôme Gombert](https://www.linkedin.com/in/j%C3%A9r%C3%B4me-gombert-84675b1b/)


pour nos discussions fructueuses.

Palettes de couleurs issues de <https://harchaoui.org/warith/colors/>.

Les trois familles Roboto sont livrées dans
`sprezzature-ui/assets/fonts/roboto/`, `sprezzature-ui/assets/fonts/roboto-serif/`
et `sprezzature-ui/assets/fonts/roboto-mono/`, chacune sous SIL Open Font
License ; voir le fichier `OFL.txt` joint dans chaque dossier.

Les *skills* puisent également des connaissances dans les
[Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/),
[Google Material Design](https://material.io/design) et les
[Laws of UX](https://lawsofux.com/).

## Licence

**BSD-3-Clause**, la même licence que **scikit-learn**. Permissive :
utilisation, modification, redistribution, vente, intégration dans des
produits commerciaux. Les trois conditions sont (1) conserver la notice
de copyright dans les redistributions de code source, (2) la reproduire
dans la documentation des distributions binaires, (3) ne pas utiliser
le nom du détenteur du copyright pour endosser des produits dérivés
sans autorisation. Voir `LICENSE.md` pour le texte canonique. Les
trois familles Roboto (Roboto, Roboto Serif, Roboto Mono) restent sous
SIL Open Font License (voir le `OFL.txt` joint dans chaque dossier
`sprezzature-ui/assets/fonts/roboto*/`) ; la licence BSD-3-Clause ci-dessus
s'applique au code source, pas aux polices.

**Licence vs. attribution.** Les crédits d'auteur dans la documentation
sont une reconnaissance volontaire (pas la condition #3 de la licence).
Vous êtes libre de les retirer ou de les remplacer dans votre fork ;
les obligations BSD-3-Clause ci-dessus sont ce qui voyage avec le code.

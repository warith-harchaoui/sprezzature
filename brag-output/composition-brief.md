# Brief de composition : la série sprezzature

Ce que `/brag` décide, et ce qu'il laisse à HyperFrames.

`/brag` possède l'angle produit, la matière source, le découpage, le ton, le
format, le choix audio et les attentes de livraison. HyperFrames possède la
structure concrète de composition, le calage exact des animations, la mécanique
d'animation, le choix du moteur d'exécution, les règles de lint et le flux de
rendu.

---

## Objectif

Quinze vidéos depuis un seul spec par film : cinq films, trois toiles.

| Film | Portée | Durée |
|---|---|---|
| `sprezzature` | la suite entière | 25,0 s |
| `figures-et-cartes` | `sprezzature-figures`, `sprezzature-maps` | 18,3 s |
| `accessibilite` | `-accessibility`, `-colors`, `-vision`, `-audio` | 21,3 s |
| `interface` | `-ui`, `-cli-gui`, `-publish`, `-ux-laws` | 18,3 s |
| `moteur-local` | `best-engine-ai-helper` | 18,3 s |

Toiles : 1920x1080, 1080x1920, 1080x1080. Sorties dans `out/<film>-<format>.mp4`.

La grille temporelle est identique dans les trois formats. Le balayage de
désaturation du film global commence à 7,09 s en paysage, en portrait et en
carré. Seule la mise en page change.

---

## Matière source

- Racine : `/Users/warithharchaoui/sprezzature`, plus les huit dépôts frères.
- Lus : `README.md` des neuf dépôts, `pyproject.toml` des huit paquets,
  `web/index.html`, `web/ralph-eyeball-loop.html`, `web/packages.html`,
  `web/tailwind.config.js`, `web/css/app.css`, `SKILLS.txt`,
  `sprezzature_figures/catalog/figures.json`, `best-engine-ai-helper/ralph.py`.
- Nom du produit : **Sprezzature**, `sprezzature.ai`.
- Meilleure phrase du projet, reprise mot pour mot :
  *« You can't proofread a sentence... you can't do that with a chart. »*
  (`web/ralph-eyeball-loop.html`)

### Copie qui doit apparaître mot pour mot

- « You can't proofread a chart. »
- « If the story survives grey, it survives everyone. »
- « render → look → fix the source → again »
- « Eyes you don't have. »
- « Make it. Audit it. Then look at it. »

### Chiffres affichés, tous vérifiés

`127` types de figures, `960` fonctions de test, `8` paquets sur PyPI,
`10` skills, `20` règles d'accessibilité, `30` lois d'expérience utilisateur,
`5` surfaces par paquet.

---

## Direction

- Préréquis de ton : `polished`.
- Direction libre : un film d'artisan sur un outil qui refuse de croire son
  propre travail.
- Lecture : la retenue est l'argument. Fondus enchaînés lents de 0,6 s, une
  idée par scène, typographie large en graisse moyenne, grands blancs. Le
  balayage de désaturation est le seul effet de manche du lot, et il le mérite
  parce qu'il **est** le produit.
- À éviter : langue de bois logicielle, visuels de remplissage, refonte
  graphique sans rapport, visualiseurs audio, particules.

---

## Identité visuelle

Extraite de `web/tailwind.config.js` et `web/css/app.css`, mode `academic`,
la palette Okabe-Ito que le site livre par défaut.

| Rôle | Valeur |
|---|---|
| Fond | `#FFFFFF` plus le lavis du site relevé à l'intensité vidéo |
| Encre | `#171717`, secondaire `#525252` |
| Accent | `#0072B2` |
| Sourcils | `#003C5D`, parce que l'accent ne passe pas AA au-dessus du lavis |
| Filets | `#E5E5E5`, tracés à 2 px |
| Titrage | Roboto Serif |
| Texte | Roboto, monospace Roboto Mono |

Les trois familles sont auto-hébergées depuis `web/fonts/`, GSAP est copié dans
`_assets/vendor/`. Le rendu ne fait aucune requête réseau.

---

## Audio

- Lit : `happy-beats-business-moves-vol-12`, 109,96 battements par minute.
- Traitement : entrée à 0,30 sur 0,8 s, atténuation à 0,13 dès que la voix
  commence, remontée à 0,27 une fois la dernière réplique finie, fondu de
  sortie de 0,9 s sur l'image tenue.
- Repères : préréglage fourni,
  `_assets/music/cues/...music-cues.json`. Les entrées séquentielles sont calées
  sur la grille de battements ; les temps forts utilisés sont 8,74, 17,47 et
  22,93 s.
- Réactivité au son : discrète. Bandes pré-extraites à 30 images par seconde par
  `extract-audio-data.py` du skill `hyperframes-creative`, réduites aux 25
  premières secondes. Les graves font respirer le lavis et la profondeur
  d'ombre des cartes ; les aigus soulèvent l'ombre du mot-symbole de sortie.
  Aucune forme d'onde, aucun égaliseur, rien qui touche la taille du texte.
- Effets sonores : quatre au plus par film, chacun au **début** de son
  mouvement, entre 0,50 et 0,62 de volume. Rien sur les cinq premières tuiles
  d'une galerie : six sons de carte transformeraient un film d'artisan en
  diaporama.

## Voix

Kokoro via `npx hyperframes tts`, voix `af_heart`, vitesse 0,95. Dix-sept
répliques, une piste par réplique, mesurées à `ffprobe` avant que la grille ne
soit écrite. Les durées de scène sont construites autour des mesures, jamais
l'inverse.

La narration ne lit jamais la ligne affichée.

---

## Instructions HyperFrames

Construit contre `hyperframes-core` (contrat de composition, attributs `data-*`,
règles de déterminisme), `hyperframes-animation`, `hyperframes-creative`
(composition vidéo sur toile claire, réactivité au son) et `hyperframes-cli`
(`check` puis `render`). `/brag` est son propre flux : ni l'entretien d'intention
du point d'entrée `hyperframes`, ni le flux générique de vidéo de lancement.

Exigences tenues :

- Matière réelle du projet dans chaque film : SVG et PNG livrés, vraie carte du
  site, vraie palette, vraies polices auto-hébergées, vraie copie.
- Une page réellement produite par `sprezzature-cli-gui` à partir d'un
  `argparse.ArgumentParser` écrit pour l'occasion, puis capturée dans Chrome.
- Les quatre simulations de vision réellement produites par
  `scripts/simulate_cvd.py` de `sprezzature-colors`, matrices de Machado, depuis
  la figure livrée. Le film sur l'accessibilité les joue toutes les quatre : une
  liste qui annonce quatre états et n'en montre que deux est une fausse
  affirmation, et c'est le film le moins bien placé pour en faire une.
- Les deux captures d'interface défilent de bout en bout dans leur carte, au
  lieu d'un recadrage qui déciderait à la place du spectateur ce qu'il voit.
- Chaque ligne lisible passe son plancher de lecture. Le texte séquentiel est
  révélé vite puis **tenu en bloc**.
- Quinze films entre 18,3 et 25,0 s, tous dans la fourchette 15 à 25 s.
- Musique, effets sonores et voix sur les quinze. Aucun silence par défaut.
- Trois verrous sur temps fort, deux grilles de battements, marqués en source.
- Réactivité au son sur le lavis, les cartes et le mot-symbole.
- Actifs locaux uniquement.
- `npx hyperframes check` est la seule barrière avant rendu. Quinze sur quinze
  passent avec zéro erreur et zéro échec de contraste.

### Note de rendu

Le disque de la machine était à 2,8 Gio libres. La capture par disque demande
environ 4,5 Gio en 1920x1080 et 1080x1920, donc les rendus de ces deux toiles
échouent en mode par défaut. `--low-memory-mode` diffuse les images au lieu de
les écrire toutes, et passe. Le carré passe dans les deux modes.

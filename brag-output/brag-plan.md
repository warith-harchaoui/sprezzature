# Plan : cinq films, trois formats

Quinze vidéos. Un film global sur la suite, quatre films de groupe, chacun en
paysage (1920x1080), portrait (1080x1920) et carré (1080x1080).

Un seul spec par film pilote les trois formats : la grille temporelle est
identique, seule la mise en page change. Le même temps fort tombe à la même
seconde dans les trois versions, ce qui fait une série et non cinq essais.

---

## 1. Ce que l'analyse de la suite a donné

Neuf dépôts lus avant d'écrire une ligne de scénario : le monodépôt
`sprezzature` et les huit paquets publiés.

| Fait retenu | Vérifié où |
|---|---|
| 127 types de figures | `sprezzature_figures/catalog/figures.json`, liste de 127 entrées |
| 960 fonctions de test sur la suite | comptage des `def test_` dans les neuf dépôts |
| Cinq surfaces par paquet | `api.py` et `mcp.py` présents dans les sept paquets outils, plus un bloc `[project.scripts]` dans chacun |
| Trois générateurs de cartes sur vraie projection | `choropleth`, `situation_map`, `density` |
| 20 règles d'accessibilité (a11y), 30 lois d'expérience utilisateur (UX) | `sprezzature-accessibility`, `sprezzature-ux-laws` |
| Le modèle passe lui aussi la boucle | `best-engine-ai-helper/ralph.py`, deux portes avant l'écriture du fichier d'environnement |

Le dernier point a changé l'angle du film global. La suite n'audite pas
seulement ce qu'elle produit : elle auditionne l'outil qu'elle emploie. Avant
de faire confiance à un modèle local, elle sème un défaut connu dans un texte
et un défaut visuel connu dans une image, et n'engage que le modèle qui
attrape les deux. C'est le seul argument de la suite qu'aucun concurrent ne
peut reprendre sans le construire.

---

## 2. Les cinq films

### Global : `sprezzature` (25,0 s, cinq répliques)

L'accroche reste la meilleure phrase du projet, reprise mot pour mot de
`web/ralph-eyeball-loop.html` : **« You can't proofread a chart. »**

1. **L'affirmation** (0,0 à 4,0) : la phrase seule sur blanc cassé, tenue 3,5 s.
2. **La boucle prouvée** (4,0 à 11,8) : le vrai `bar-grouped.svg` livré dans la
   carte du site, puis un balayage de désaturation le traverse en direct. Les
   trois séries restent lisibles parce qu'elles diffèrent en clarté et pas
   seulement en teinte. La revendication du produit est jouée, pas décrite.
3. **La suite** (11,6 à 17,9) : les dix skills en pastilles, une par temps, sous
   la ligne « one implementation, five ways in ».
4. **L'auditeur audité** (17,7 à 22,1) : les deux portes Ralph.
5. **Sortie** (21,9 à 25,0).

### Figures & cartes (18,3 s, trois répliques)

`sprezzature-figures` et `sprezzature-maps`. Accroche : **« 127 kinds, every one
hand‑authored. »** Six vraies figures de la galerie arrivent une par temps, puis
quatre vraies cartes. La phrase de bas de scène dit ce qui est en jeu : le SVG
est le livrable, jamais un export.

### Accessibilité (21,3 s, trois répliques)

`sprezzature-accessibility`, `-colors`, `-vision`, `-audio`. Accroche reprise du
site : **« Eyes you don't have. »**

La scène centrale joue **les quatre simulations**, pas deux. Le vrai
`bar-grouped.svg` est rendu en image, puis passé à `scripts/simulate_cvd.py` de
`sprezzature-colors`, qui applique les matrices de Machado. Quatre fichiers en
sortent : protanopie, deutéranopie, tritanopie, niveaux de gris. Le film les
enchaîne, chacun révélé par un balayage qui passe le cadre à la paire d'yeux
suivante, et l'étiquette correspondante s'allume au moment où son état apparaît.

Les trois séries restent distinguables dans les quatre, ce qui est précisément
la démonstration. Ce film dure 21,3 s au lieu de 18,3 s parce que quatre états
demandent de la place.

Huit pastilles ensuite pour ce que les quatre outils couvrent, et une phrase sur
le local.

### Interface (18,3 s, trois répliques)

`sprezzature-ui`, `-cli-gui`, `-publish`, `-ux-laws`. Accroche : **« A command
line is a wall. »** La scène centrale montre une page réellement produite par
`sprezzature-cli-gui` à partir d'un vrai `argparse` (voir plus bas). La carte
est une fenêtre et la page défile derrière : tous les champs passent, `--kind`,
`--input` avec son fichier CSV, `--output`, `--accessibility`, `--title`,
`--audit`, le bouton et la ligne de commande construite. Huit pastilles pour le
reste.

### Le moteur local (18,3 s, trois répliques)

`best-engine-ai-helper`. Accroche : **« Who checks the checker? »** La scène
centrale est une vraie capture de l'interface du paquet, qui défile de bout en
bout : les caractéristiques de la machine, le champ de tâche, le mode, la marge
mémoire, puis les deux cartes de recommandation avec le modèle retenu, son
poids, son score et son débit, et le journal local. Puis les deux portes Ralph
en tableau.

---

## 3. Ce qui est réellement montré

Aucune image inventée. Chaque visuel vient d'un dépôt.

| Visuel | Origine |
|---|---|
| `bar-grouped.svg` et sa copie désaturée | `web/img/figures/`, fichier livré |
| Six figures de galerie | `web/img/figures/`, les mêmes que le site |
| Quatre cartes | `web/img/maps/`, fichiers livrés |
| Les quatre simulations de vision | produites pendant cette session par `scripts/simulate_cvd.py` de `sprezzature-colors`, matrices de Machado, depuis le `bar-grouped.svg` livré |
| La page de formulaire | produite pendant cette session par `sprezzature_cli_gui.renderer.render_html` à partir d'un `argparse.ArgumentParser` réel, puis capturée dans Chrome |
| L'interface du moteur | `best-engine-ai-helper/assets/screenshots/gui-recommendation.png`, page entière |
| Le logo | `web/img/logo.png` pour la série, le logo gant de `best-engine-ai-helper` pour son propre film |

Les chiffres à l'écran (127, 960, 8, 20, 30, 10) ont tous été vérifiés contre
les dépôts avant d'être écrits.

---

## 4. Ton, identité, son

- Préréquis : `polished`. La retenue est l'argument.
- Fond : blanc `#FFFFFF`, lavis bleu du site relevé à l'intensité vidéo, trame
  de points teintée pour que la toile claire ne soit pas une diapositive vide.
- Encre `#171717`, secondaire `#525252`, accent `#0072B2`, sourcils `#003C5D`.
- Filets `#E5E5E5` tracés à 2 px et non à 1 px comme sur le web.
- Trois Roboto, tous auto-hébergés depuis `web/fonts/`. Aucun réseau au rendu.
- Lit musical `happy-beats-business-moves-vol-12`, 109,96 battements par minute.
  Entrée à 0,30, atténuation à 0,13 sous la voix, remontée à 0,27 une fois la
  voix finie, fondu de sortie sur l'image tenue.
- Réactivité au son, discrète : les bandes pré-extraites font respirer le lavis
  et la profondeur d'ombre des cartes. Rien qui touche la taille du texte.
- Quatre effets sonores au plus par film, chacun au début de son mouvement.

### Voix

Kokoro, voix `af_heart`, vitesse 0,95, par `npx hyperframes tts`. Une piste par
réplique, mesurée, et la grille construite autour des mesures.

| Film | Répliques | Parole | Durée |
|---|---|---|---|
| global | 5 | 13,9 s | 25,0 s |
| figures & cartes | 3 | 9,0 s | 18,3 s |
| accessibilité | 3 | 8,5 s | 21,3 s |
| interface | 3 | 10,5 s | 18,3 s |
| moteur local | 3 | 8,3 s | 18,3 s |

Un premier jet du global tenait 24,6 s de parole pour 25 s de film. Les
répliques ont été raccourcies, pas accélérées. Le silence est aussi voulu que
les phrases.

La voix ne lit jamais la ligne affichée. L'écran et la voix portent chacun une
moitié du temps fort.

---

## 5. Plancher de lecture

Chaque ligne que le spectateur doit lire tient assez longtemps une fois posée :
environ 0,8 s pour une étiquette courte, environ 0,3 s par mot pour une phrase.

| Ligne | Mots | Plancher | Tenue |
|---|---|---|---|
| « You can't proofread a chart. » | 5 | 1,5 s | 3,45 s |
| `01 render` à `04 again` | 2 à 3 | 0,8 s | l'ensemble tient 4,9 s |
| « If the story survives grey, it survives everyone. » | 8 | 2,4 s | 3,4 s |
| Dix pastilles de skills | 1 à 2 | 0,8 s | l'ensemble tient 1,0 s après la dernière |
| « Make it. Audit it. Then look at it. » | 8 | 2,4 s | 2,7 s |

Les séquences rapides sont des images ou des étiquettes courtes, révélées vite
puis tenues en bloc. Aucune phrase n'est retirée avant d'avoir été lue.

---

## 6. Ce que la boucle de l'oeil a attrapé sur ces films

Les quinze projets passent `npx hyperframes check` avec zéro erreur. Les
défauts ci-dessous ont survécu à ce filtre et ne sont sortis qu'en regardant
les images, ce qui est exactement la thèse du produit.

1. **Le sourcil ne passait pas le contraste au-dessus du lavis.** `#0072B2` donne
   4,62:1 sur blanc, mais le lavis bleu éclaircit le fond et le rapport tombait
   à 4,2:1. Passé à `brand-navy` `#003C5D`, un jeton du projet.
2. **La phrase de bas de scène passait sous le filet du bas** en paysage : la
   grille était dimensionnée sur la largeur seule. Elle l'est maintenant sur la
   hauteur restante.
3. **La capture du formulaire était en portrait dans un cadre 16:9** et se
   réduisait à un timbre-poste. Recadrée sur le formulaire lui-même.
4. **« hand-authored » se coupait au trait d'union**, en fin de ligne. Trait
   d'union insécable.
5. **Quatre cartes sur deux colonnes** laissaient les deux tiers du cadre vides
   en paysage. Passées à quatre colonnes.
6. **La liste `01 / 02 / 03 / 04` était centrée** dans les mises en page
   empilées, donc en dents de scie. Bloc centré, éléments alignés à gauche.
7. **Deux tweens se disputaient le volume** du lit musical entre 0,45 s et
   0,80 s. L'atténuation commence maintenant après la fin de l'entrée.
8. **Le film sur l'accessibilité annonçait quatre simulations et n'en montrait
   que deux.** La liste disait protanopie, deutéranopie, tritanopie, niveaux de
   gris, et l'image passait simplement de la couleur au gris. Une fausse
   affirmation, dans le film dont l'argument entier est de regarder honnêtement.
   Les quatre états sont maintenant réellement produits par l'outil du projet et
   joués l'un après l'autre.
9. **Les deux captures d'écran étaient recadrées**, donc une partie des champs
   n'était jamais montrée. Elles défilent maintenant de bout en bout.

---

## 7. Fabrication

`build_films.py` produit les quinze projets depuis un seul spec. Les actifs sont
partagés par lien symbolique vers `_assets/`, donc les 6,8 Mo de polices, de
figures, de musique et de voix ne sont copiés nulle part.

```bash
python3 build_films.py           # écrit films/<film>-<format>/
cd films/<film>-<format>
npx hyperframes check            # la seule barrière avant rendu
npx hyperframes render --quality looks --output ../../out/<film>-<format>.mp4
```

---

## 8. Publication sur le site

Les cinq montages paysage sont dans `web/video/`, avec leur affiche et des
sous-titres WebVTT dans les deux langues. Les versions verticale et carrée
restent dans `brag-output/out/` : ce sont des formats de réseaux sociaux, pas
des formats de page.

| Ce qui a changé | Où |
|---|---|
| Cinq MP4, cinq affiches, dix fichiers de sous-titres | `web/video/` |
| Nouvelle page, deux langues | `web/films.html`, `web/fr/films.html` |
| Générateur de la page | `scripts/build_films_page.py` |
| Générateur des sous-titres | `brag-output/make_captions.py` |
| Lien « Films » dans les deux barres de navigation | les 36 pages |
| Le film global en page d'accueil | `web/index.html`, `web/fr/index.html` |
| Deux entrées | `web/sitemap.xml`, `web/llms.txt` |

Les sous-titres ne sont pas transcrits. Ils reprennent le script de narration
dont la voix Kokoro a été tirée, avec les temps de début et les durées mesurées
de chaque fichier audio. C'est exact là où une transcription serait seulement
proche.

Le lecteur porte `controls`, une affiche, et une piste de sous-titres par
langue, ce que le linter du projet exige (`video-missing-captions`,
`track-missing-srclang`, `media-missing-controls`). Pas de lecture automatique :
les films sont racontés, un démarrage muet perdrait le propos.

### Une contradiction corrigée au passage

Le site annonçait « nine skills » alors que `SKILLS.txt` en liste dix et que
`maps.html` existe déjà. Le film global dit « ten skills ». Poser le film sur la
page d'accueil y mettait donc une contradiction. Le compte est passé à dix
partout, la carte `sprezzature-maps` a été ajoutée à la grille des skills, et le
paquet manquant à la liste de l'écosystème, qui en compte maintenant huit.

### Ce que l'auditeur du projet reproche encore

`audit_laws_of_ux.py` compte les choix de premier niveau dans `<nav>` et refuse
au-delà de sept. Avant ces changements, 30 pages étaient déjà en infraction.
Après, 36 : les deux nouvelles pages, et quatre pages d'étude de cas qui étaient
exactement à sept et passent à huit à cause du lien « Films ».

Le correctif que l'outil recommande lui-même est de grouper : passer les liens
secondaires derrière un `<details>` « More » ramènerait toutes les pages sous le
seuil, puisque la règle exempte explicitement `<details>`, `<menu>` et
`<dialog>`. C'est une décision de conception sur l'en-tête de 36 pages, donc
elle n'a pas été prise ici.

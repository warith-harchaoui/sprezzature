# financial-markets — étude de cas « marchés financiers »

Un gros *assignment* dont on tire les fruits pour la base de code : reconstruire
l'équivalent d'un tableau de bord d'analyse de portefeuille, en **style maison**
et bien plus beau, **entièrement en SVG interactif**, affiné par la **boucle
Ralph Eyeball**. Ce dossier est un **générateur** : il écrit ses pages dans le
site `web/` (`web/financial-markets.html` et `web/fr/…`), où le tableau de bord
est **une section du site** : même en-tête, mêmes polices, même thème clair /
sombre, mêmes `theme.js` et `fullscreen.js` que le reste de `web/`.

Le dashboard **est** la page : une bande d'indicateurs puis **une colonne de
cartes pleine largeur**, chaque carte porte un titre, un bouton plein écran et
**un SVG par panneau**, interactif (survol pour en savoir plus) et responsive.
Chaque panneau porte sa **légende verticale à droite** (rien d'écrit sur le
tracé) et l'**unité sur ses axes**. Pas un gros SVG monolithique, pas de PNG.

La page existe en **anglais (par défaut) et français** (bascule dans la barre) et
sur **deux tirages**, un **cas favorable** et un **cas défavorable** (menu
déroulant) : le beau cas n'est pas la règle, c'est tout le propos de la relecture.

## Ce qu'il montre

C'est une stratégie action systématique long-only illustrative sur 100
actions simulées, du 02/01/2024 au 23/07/2026. Toutes les 25 séances elle
ré-estime combien des plus fortes valeurs détenir (`Kₜ`, borné de 3 à 40) et les
équipondère. Données synthétiques, reproductibles (graine 48). Aucune valeur
réelle, aucun conseil.

Dix panneaux, dix techniques (légende verticale à droite sur chacun) :

| # | Panneau | Technique |
|---|---------|-----------|
| 1 | Richesse nette comparée | courbes multiples + légende verticale à droite |
| 2 | Taille automatique Kₜ | aire en escalier |
| 3 | Profils des 100 actions | faisceau + médiane |
| 4 | Gains nets journaliers | aire bicolore autour de zéro |
| 5 | Frais ponctuels (pb) et cumulés (%) | **double axe** |
| 6 | Distribution des rendements | ridgeline par année |
| 7 | Rendements mensuels | carte de chaleur calendaire |
| 8 | Rotation aux réallocations | sucettes + moyenne mobile (**double axe** zoomé) |
| 9 | Pertes en ligne | aire immergée (drawdown) |
| 10 | Performance ajustée du risque | jauge de Sharpe + bullet |

## Choix de couleurs (finance de marché, justifiés)

- **Bleu** = la stratégie (« nous ») : confiance, institutionnel, métrique mise en avant.
- **Bleu ↔ rouge** = hausses / baisses et gains / pertes. **Pas de vert-rouge** : le
  couple bleu-rouge survit au daltonisme rouge-vert (protanopie / deutéranopie) et
  reste lisible en niveaux de gris, vérifié avec `simulate_cvd`, doublé du signe.
- **Ambre ↔ bleu profond** sur le panneau des frais (double axe) : ce couple se
  distingue par la teinte **et** la clarté sous les trois dichromaties, là où deux
  oranges voisins se confondaient.
- **Ambre** = frais et coûts : attention, sans dramatiser.
- **Violet** = Kₜ, variable de contrôle (hors P&L).
- **Ardoise froide** pour le texte et les axes, **jamais du noir pur**.

Sources : [ColorArchive — Financial UI](https://colorarchive.org/guides/financial-ui-color-guide/),
[Cashbee — Ratio de Sharpe](https://www.cashbee.fr/lexique/ratio-de-sharpe), et la
simulation daltonisme de `sprezzature-colors` (matrices Machado 2009).

## Fichiers

| Fichier | Rôle |
|---------|------|
| `market_data.py` | la simulation de portefeuille (numpy seul) |
| `market_style.py` | palette finance, formats FR, axe année, enveloppe SVG |
| `panels.py` | les dix générateurs de panneaux (SVG interactifs) |
| `build.py` | assemble les SVG dans le chrome du site → `web/financial-markets*.html` |
| `template.html` | le gabarit tokenisé (en-tête, pied, thème du site + placeholders) |
| `web/js/financial-markets.js` | comptage des indicateurs + info-bulle riche (le thème et le plein écran viennent des `theme.js` / `fullscreen.js` partagés) |

Les polices, le logo, la feuille Tailwind (`css/app.css`) et les scripts partagés
sont ceux de `web/` ; ce dossier n'embarque plus ses propres copies.

## Construire

```bash
cd financial-markets
python3 build.py     # écrit les 4 pages sous ../web/ (EN) et ../web/fr/ (FR)
# puis, si de nouvelles classes Tailwind apparaissent, régénérer la feuille :
cd ../web && npx tailwindcss@3 -i css/tailwind-input.css -o css/app.css --minify
open web/financial-markets.html   # la section — interactive, responsive, plein écran
```

`out/` (renders de la boucle Ralph) est git-ignoré et n'est jamais publié.

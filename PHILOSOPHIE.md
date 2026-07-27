# Approche — les idées derrière `sprezzature`

Cette page rassemble les convictions de conception qui traversent toute la
suite `front-*`. Chacune correspond à ce que le code fait vraiment ; rien
ici n'est un vœu pieux. Pour le *quoi* (les *skills*, l'installation), voyez
[`LISEZMOI.md`](LISEZMOI.md). Ceci est le *pourquoi*.

Version anglaise miroir : [`PHILOSOPHY.md`](PHILOSOPHY.md).

Les sigles sont explicités à leur première apparition : *scalable vector
graphics* (SVG, graphiques vectoriels adaptatifs), *portable network
graphics* (PNG), déficience de la vision des couleurs (DVC), feuilles de
style en cascade (CSS), modèle langue-vision (VLM).

---

## La figure est un SVG, pas une photo de SVG

Une figure `sprezzature-figures` se livre en *scalable vector graphics* (SVG)
écrit avec soin. Les générateurs de `sprezzature-figures/scripts/make_*.py`
produisent directement le balisage SVG ; le helper partagé `svg_open` de
`_svg.py` ouvre chaque document avec une largeur et une hauteur explicites
et un `viewBox` correspondant, si bien que le graphique s'adapte à toute
taille sans un seul pixel flou. Les 91 figures d'exemple portent ce
`viewBox`. Vega-Lite reste un moyen commode de *décrire* beaucoup de ces
graphiques, mais le *JavaScript Object Notation* (JSON) de Vega n'est pas ce
qu'on livre, et le *portable network graphics* (PNG) n'est qu'un export pour
les endroits qui ne prennent pas le vectoriel. Le livrable, c'est le SVG :
le texte reste sélectionnable, les traits restent nets à tout zoom, et le
fichier est léger.

## Une interactivité qui se compose au lieu de se dupliquer

Le composant de référence
`sprezzature-ui/assets/components/figure-fullscreen.html` décrit comment se
comporte une figure interactive. Il part d'un fait mesuré plutôt que d'une
supposition : la façon dont on intègre un SVG décide de ce qu'il peut faire.

| Intégration | Adaptatif | `:hover` CSS | `<script>` interne | Plein écran |
|---|---|---|---|---|
| `<img src=".svg">` | oui | non | non | non |
| `<object data=".svg">` | oui | oui | oui | oui |
| `<svg>` en ligne dans le HTML | oui | oui | oui | oui |

Le socle qui doit survivre à toute intégration, l'adaptativité et une
infobulle au survol en pures feuilles de style en cascade (CSS), vit donc
*à l'intérieur* du SVG, à côté d'un petit bouton plein écran interne. C'est
le comportement par défaut : un seul `.svg` autonome qui fonctionne ouvert
seul, servi via `<object>` ou intégré en ligne.

Un tableau de bord veut souvent plus : une seule infobulle qui suit le
curseur, partagée entre les cartes, un bouton plein écran dans l'habillage
de la carte, un repli pour iOS. C'est un module optionnel au niveau de la
page. Les deux couches ne se marchent pas dessus, car la frontière tient à
un seul sélecteur. Une figure dans une carte `[data-fs-target]` est gérée de
l'extérieur, donc son bouton interne et son infobulle CSS se mettent en
retrait : pas deux boutons, pas deux infobulles. On écrit un seul SVG ; le
contexte choisit le mode. (Un détail qui mérite d'être dit parce qu'il est
facile à rater : en plein écran, le navigateur ne peint que l'élément de
premier plan, donc une infobulle posée sur `<body>` disparaît ; le module
externe la reloge dans l'élément plein écran pour qu'elle reste visible.)

## Regarder la figure avant de la livrer — la Ralph Eyeball Loop

On relit une phrase pour la corriger. Impossible de faire pareil avec un
graphique : sa justesse est dans les pixels, pas dans le code. Alors
`sprezzature-figures/scripts/ralph_eyeball_loop.py` rend n'importe quel artefact
visuel-issu-du-code en PNG avec un outil déterministe (un graphique Vega,
une figure TikZ, un diagramme Mermaid, une page web entière, un SVG dessiné
avec soin), puis quelqu'un le regarde vraiment. Par défaut c'est l'agent
lui-même, celui qui a écrit le code ; entièrement hors ligne, un VLM local
optionnel fait la critique. Il attrape ce qu'un contrôle de code ne verra
jamais : une étiquette coupée au bord, une légende sortie du cadre, deux
nœuds superposés, des couleurs qui s'effacent pour un lecteur daltonien. On
corrige la source, on rend à nouveau, on regarde à nouveau. La *dataviz*
n'est qu'un usage ; la même boucle relit aussi les écrans d'interface et les
diagrammes.

## Accessible et sûr pour la vision des couleurs par construction

La couleur n'est jamais le seul canal qui porte du sens, si bien qu'une
figure se lit encore en niveaux de gris ou pour un lecteur daltonien. Les
données divergentes emploient un dégradé du bleu au rouge, qui résiste à la
déficience de la vision des couleurs (DVC) rouge-vert. Ce ne sont pas des
affirmations prises pour argent comptant :
`sprezzature-colors/scripts/simulate_cvd.py` re-rend n'importe quelle image telle
que la voit un protanope, un deutéranope ou un tritanope (matrices de
Machado et al. 2009) pour qu'on vérifie, et `sprezzature-accessibility` passe au
crible le *HyperText Markup Language* (HTML) statique pour les fautes
d'accessibilité qu'un analyseur peut attraper : texte alternatif manquant,
champs sans étiquette, état porté par la seule couleur, et d'autres.

Le défaut vise le cas le plus dur, un lecteur qui ne voit aucune couleur,
car une conception qui résiste aux niveaux de gris résiste à toute
déficience de la vision des couleurs. Des niveaux plus forts ou propres à
une déficience peuvent venir par-dessus pour qui le souhaite, jamais comme
condition d'entrée. Le raisonnement et les sources sont dans
`sprezzature-colors/references/accessibility-levels.md`.

## Local d'abord, un seul modèle, aucun logiciel-service

Le travail d'intelligence artificielle tourne sur votre machine. Un seul
modèle langue-vision, Qwen3-VL 8B servi via Ollama, écrit le texte
alternatif, rédige les sous-titres et critique les figures dans le mode hors
ligne de la boucle Ralph. Un modèle pour le texte et la vision, et un test
qui empêche un second de se glisser. Le raisonnement et les sources sont
dans [`docs/LLM_CHOICE.md`](docs/LLM_CHOICE.md). Rien n'a besoin de quitter
la machine.

## Du code mutualisé, une sortie inchangée octet pour octet

Une soixantaine de générateurs de figures répétaient jadis le même
passe-partout : la balise racine SVG, la fin d'écriture-et-rapport, quelques
helpers de géométrie. Tout cela vit maintenant dans `_svg.py` et
`_render.py`. La règle de chaque refactorisation de ce genre est stricte :
seul le code qui était *identique* d'un générateur à l'autre est déplacé, et
le déplacement est vérifié en régénérant les figures et en confirmant que
les octets n'ont pas bougé. Toute mutualisation qui changerait un seul pixel
rendu est refusée. Les helpers restent en *stdlib* seule pour s'importer
partout où les générateurs tournent déjà.

## Une prose bilingue, écrite avec soin dans les deux langues

La documentation et le site existent en anglais et en français, tenus en
parité stricte : les mêmes affirmations dans le même ordre. Chaque version
est écrite nativement dans sa langue, si bien qu'aucune ne se lit comme la
traduction de l'autre. Les sigles sont explicités à leur première
apparition. La prose vise à se lire comme si une personne l'avait écrite,
sans esbroufe et sans tics. Ce document veut être son propre exemple.

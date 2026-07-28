<!--
Charte d'écriture — français (code langue : fr).

Source de vérité lue à l'exécution par la couche writing-standards :
meta_from_ollama, plain_language, les légendes de lint_markdown et la boucle
Ralph de prose l'appliquent toutes. Rédigée nativement en français, non
traduite. À garder synchronisée avec la charte de référence du projet
(gist 7cc42b038e86c5195ec09f0531111ba4). Voir ../../references/writing-standards.md
pour la manière dont elle est appliquée.
-->

# Charte d'écriture — français

Charte d'écriture en français, valable pour **n'importe quel texte** : article,
chapitre, note, courriel, billet, synthèse d'une conversation avec un modèle de
langage. Elle se suffit à elle-même : la méthode de clarté et les règles de
cohérence y sont intégrées, il n'y a pas d'autre fichier à ouvrir. On l'applique
concept par concept, ligne par ligne.

## 1. Le principe : rendre reconstructible

Comprendre, ce n'est pas retenir une formule, c'est pouvoir la reconstruire et
l'expliquer à quelqu'un qui ne sait rien. Un texte réussi ne se contente pas
d'informer : il rend le lecteur capable de refaire le raisonnement seul.

Le test du novice : si l'on ne sait pas l'expliquer simplement, c'est qu'on ne l'a
pas compris. L'endroit où l'on se réfugie derrière un mot savant est un trou dans la
compréhension, pas une élégance ; le jargon n'est pas un raccourci, c'est une cachette.
Quand une phrase ne « coule » pas sans un terme non expliqué, on remonte à la source
jusqu'à ce qu'elle coule.

## 2. Ce qui vaut d'être écrit : originalité et importance

Avant de savoir bien dire, il faut savoir si le propos vaut d'être dit. Deux questions,
posées ensemble :

- **Originalité.** Le propos existe-t-il déjà tel quel dans la littérature courante, ou
  le formule-t-on d'une manière qui n'a pas d'équivalent accessible ? Un propos
  entièrement disponible ailleurs apporte peu ; un cadrage, une mise en série, une
  reformulation qui éclaire, apportent beaucoup. Une bonne reformulation est déjà un
  produit original : le mérite tient souvent à l'angle, non au fait brut.
- **Importance.** L'enjeu est-il marginal (un réglage, un détail) ou structurel (une
  responsabilité, une souveraineté, une santé collective, une économie) ? On dépense
  l'effort d'écriture là où l'enjeu le justifie.

Garde d'honnêteté : ne jamais présenter comme neuf ce qui existe déjà. Avant d'affirmer
une nouveauté, on vérifie qu'elle n'a pas été formulée ailleurs ; dans le doute, on se
pose en interprète qui donne la lecture claire, non en inventeur. On ne survend rien.

## 3. La boucle par concept

Pour chaque notion (mot technique, sigle, formule, norme, nom propre) :
1. **Nommer** le concept.
2. **L'expliquer en langage ordinaire**, comme à un débutant, sans aucun terme non
   défini.
3. **Repérer le point de friction** : le mot ou le saut où l'explication se bloque.
   C'est là que se cache l'obscurité.
4. **Combler puis simplifier** : revenir à la source, puis reformuler avec une
   intuition en mots et un exemple concret, jusqu'à ce que le récit soit continu.

Exemple du geste. *Avant*, en partant de la formule : « On optimise un proxy sous
contrainte de périmètre. » *Après*, en partant de l'intuition : « On suit un indicateur
de substitution, une grandeur facile à mesurer qu'on surveille à la place de l'objectif
réel, qu'on ne sait pas mesurer directement ; primer chaque bogue corrigé, par exemple,
finit par encourager à en introduire pour les corriger. » La seconde version nomme le
concept, le traduit en mots, en donne un cas concret, signale le piège au passage, sans
un seul terme laissé nu.

## 4. Checklist par concept

- **Intuition d'abord.** Une image ou une idée en mots précède toute formule ou
  abstraction. La formule vient à la fin, résumé compact d'une chose déjà comprise,
  jamais point de départ.
- **Un exemple concret.** Chaque idée reçoit au moins un exemple qu'un non-spécialiste
  se représente (un objet du quotidien, un cas chiffré, une scène).
- **Aucun jargon nu.** Tout terme technique est glosé à sa première apparition ; le
  lecteur n'a jamais besoin d'un glossaire pour comprendre ce qu'il lit.
- **Sigles.** Glose intuitive en français d'abord, puis le terme d'origine en italique,
  puis seulement l'abréviation : « l'apprentissage par renforcement avec humains dans la
  boucle (_Reinforcement Learning with Human Feedback_ ou RLHF) ». On garde le terme
  anglais réel, on ne le remplace pas par un équivalent français forcé qui perdrait sa
  précision technique.
- **Premiers principes.** Le concept se déduit d'une base simple déjà posée, non
  d'une autorité ou d'un autre terme obscur.
- **Ancrer le neuf sur l'acquis.** Toute notion nouvelle se raccroche à un support
  que le lecteur possède déjà, plutôt que de flotter seule.

## 5. Les analogies (méthode A/B/C/D)

Une analogie de relation transporte une propriété d'un couple connu vers un couple à
éclairer : ce que A est à B, C l'est à D. Elle met en jeu quatre termes ; c'est la
relation entre A et B qu'on transpose à C et D. Avant de s'en servir, on doit pouvoir
répondre à trois questions : quels sont les quatre termes ? quelle propriété
transporte-t-on de A–B vers C–D ? où le rapprochement cesse-t-il de tenir ?

Deux exigences opposées, tenues ensemble :
1. **Nommer tôt, dans la prose, les quatre termes et la propriété transportée**, pour
   que le lecteur voie ce qu'on met en regard de quoi. S'il ne le voit pas, l'analogie
   flotte et il l'écarte.
2. **Ne jamais les exposer comme des étiquettes** : écrire « A est à B ce que C est à
   D », aligner des lettres ou une proportion, rend le procédé visible et mécanique ;
   le lecteur le rejette. La clarté vient de la prose, pas de l'échafaudage.

Règle : **clair, jamais explicite.** Le lecteur doit pouvoir refaire le rapprochement
seul, sans qu'on lui ait montré la charpente A/B/C/D. Et comme toute analogie finit par
céder, on signale l'endroit précis où elle cesse de porter.

Exemple. « De même qu'un hôpital, alimenté par un réseau électrique fiable, garde
malgré tout un groupe électrogène pour ne pas dépendre d'une seule source, une
organisation qui confie une fonction vitale à un service distant a besoin d'un recours
local. » Les quatre termes (réseau et hôpital d'un côté, service distant et
organisation de l'autre) et la propriété transportée (le besoin d'un secours quand
l'infrastructure est vitale) sont limpides, sans une seule lettre ni proportion. Et
l'on dit où elle casse : le groupe électrogène redémarre à l'identique, un recours
logiciel de secours reste souvent dégradé.

## 6. Cohérence et honnêteté

- **On n'invente rien.** On clarifie et l'on développe ce qui est là ; aucun fait non
  vérifiable ajouté. Là où la compréhension s'arrête, on le dit.
- **Marquer le statut de preuve.** On distingue toujours ce qui est *observé*, *mesuré*,
  *extrapolé* ou *spéculatif* ; une affirmation empirique ne se présente jamais sans
  son degré de certitude.
- **Ne pas prêter d'intention sans le signaler.** On n'attribue ni volonté ni
  agentivité à un dispositif comme s'il s'agissait d'un fait ; si l'on emploie un tel
  raccourci, on le marque comme tel.
- **Le contre-exemple qui éclaire.** Une règle se comprend souvent le mieux au point
  où elle casse : un cas réel qui a mal tourné, chiffré et sourcé, enseigne mieux que
  le cas qui réussit. Deux conditions pour qu'il porte plutôt qu'il ne décore : il
  illustre une thèse déjà posée, il ne la remplace pas ; il est solidifié comme
  n'importe quelle référence (chiffres exacts, source primaire, lien qui résout). Un
  contre-exemple approximatif se retourne contre l'argument.
- **Position mesurée.** Ni excès dans un sens ni dans l'autre ; on ne bascule pas dans
  le camp qui simplifie. On mobilise les auteurs comme lectures, non comme adhésions.
- **Un concept, un lieu.** Une notion se définit une fois ; ailleurs on y renvoie
  plutôt que de la redévelopper. Rien ne contredit en silence ce qui a été tenu plus
  haut.

## 7. La forme

- **Aucun tiret de ponctuation.** Ni cadratin, ni demi-cadratin en incise. On réécrit
  en virgules, deux-points, points-virgules, parenthèses, phrases courtes. Les traits
  d'union des mots composés (socio-technique, c'est-à-dire) restent.
- **Aucun tic de machine :** pas de « , et » ni de « , ou » soudant deux propositions
  (on coupe la phrase, ou l'on met un point-virgule ou un deux-points), pas de
  « Autrement dit », pas de « en une formule », pas de règle de trois systématique,
  pas d'emphase par italiques à répétition, pas de tournure ampoulée.
- **Pas de réflexe d'antithèse.** La tournure « ce n'est pas X, c'est Y », « non pas X
  mais Y » posée par automatisme signe le gabarit. On la garde seulement quand
  l'opposition est réelle et porte l'argument, jamais comme effet de balancier.
- **Pas de phrase-marathon.** Une phrase qui dépasse une dizaine de lignes à l'écran
  force un effort de lecture disproportionné, même si elle est grammaticalement juste.
  On la coupe en deux ou on la restructure. Se méfier aussi des listes déguisées, ces
  phrases qui enfilent une énumération sous une syntaxe continue : on en fait une vraie
  liste ou des phrases distinctes. La longueur ne prouve pas la profondeur.
- **Pas de tic lexical.** Un même verbe ou une même tournure qui revient (« déplacer »,
  « à la fois », « précisément », « permet de ») trahit le gabarit. On repère les
  échos par recherche et on varie, sauf quand la reprise est un motif voulu.
- **Registre sobre, humain, soutenu.** Jamais « llmesque », « chatgptesque » ni
  « claudesque ». La phrase doit sonner comme celle d'un auteur, pas d'un gabarit.
- **Traquer les signatures chatgptesques.** Elles trahissent la machine et s'effacent
  à la relecture :
  - ouvertures creuses : « De nos jours », « À l'heure où », « Il est important de
    noter que », « Il convient de souligner que », « force est de constater » ;
  - transitions plaquées en tête de phrase quand aucun lien réel ne les appelle :
    « Par ailleurs », « De plus », « En outre », « En somme », « En définitive » ;
  - reformulation-tic : « Autrement dit », « en d'autres termes », « en une phrase » ;
  - intensificateurs vides posés pour l'emphase : « véritablement », « profondément »,
    « réellement », « littéralement », « incontournable », « majeur » ;
  - balancier enchaîné par réflexe : « non seulement X mais aussi Y », « ce n'est pas
    seulement X, c'est aussi Y » ;
  - chutes de synthèse creuses : « En conclusion », « Au fond », « in fine » ;
  - abstractions gonflées : « le paysage de », « au cœur de », « la richesse de »,
    « un enjeu de taille », « à l'ère de » ;
  - symétrie et rythme ternaire réguliers qui lissent la prose jusqu'à l'anonymat.

  Le remède n'est pas une autre formule toute faite, c'est une phrase située, au rythme
  irrégulier, qui dit la chose et rien de plus. Une prose d'auteur a des aspérités.

## 8. L'idiome

Le plus idiomatique possible. On préfère toujours la tournure que dirait un
francophone lettré à la tournure correcte mais plate. Guillemets français « … »,
accents complets, espace insécable devant `; : ? !`.

## 9. Les sources

Aucune référence gratuite. Une citation dit ce que la source établit, par quelle
méthode, avec quelle limite, et pourquoi elle est déterminante à cet endroit. On lit
réellement la source avant de s'en servir. On bannit le « comme le dit très bien X »
et le name-dropping décoratif. Une seule citation forte par affirmation.

À pertinence égale, on équilibre les voix : quand plusieurs sources font également
autorité, on cite volontiers les autrices de référence là où elles existent. On ne
retire jamais une source pour cette raison ; c'est une attention à l'équilibre, pas un
quota.

## 10. La boucle Ralph : fluidité par paires de paragraphes

Un texte se relit non paragraphe par paragraphe mais par paires de paragraphes
consécutifs, car la fluidité se joue à la couture, pas à l'intérieur d'un bloc. La
boucle, empruntée à la méthode « rendre, regarder, corriger le code, recommencer » :

1. **Lire à voix haute** le paragraphe *n* suivi du paragraphe *n+1*, d'un trait.
2. **Regarder la couture** : le passage de l'un à l'autre s'enchaîne-t-il tout seul ?
   Le premier appelle-t-il le second ? Y a-t-il une redite, un trou logique, un saut,
   un mot répété d'un bloc à l'autre, une transition plaquée (« par ailleurs », « de
   plus ») qui masque l'absence de lien réel ?
3. **Corriger la prose, jamais l'impression** : on retouche le texte lui-même (ordre
   des phrases, dernière phrase de *n*, première de *n+1*, un rappel, une coupe), on
   ne se contente pas de noter que « ça coince ».
4. **Relire la paire**, puis **avancer d'un cran** : on glisse à la paire (*n+1*, *n+2*)
   et l'on recommence. Les fenêtres se chevauchent, si bien que chaque paragraphe est
   éprouvé deux fois, une fois comme arrivée, une fois comme départ.

On tourne sur une paire jusqu'à ce que la couture disparaisse, puis on passe à la
suivante. Le texte est fluide quand aucune jointure ne se voit plus.

## 11. Le geste, en une image

La pédagogie du cuisinier qui **publie la recette** plutôt que du chef qui garde le
secret : montrer chaque geste, du premier principe au résultat, pour que le lecteur
refasse le plat seul. Un passage est prêt quand un lecteur non spécialiste, l'ayant
lu une fois, saurait le réexpliquer à son tour.

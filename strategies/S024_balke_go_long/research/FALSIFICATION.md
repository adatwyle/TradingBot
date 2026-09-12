# S024 « Go Long » — critères de falsification

**Écrit le 2026-09-12 à 19:4x (heure locale), AVANT toute exécution du harnais.**
Un critère rédigé après lecture des résultats n'est pas un critère.

---

## L'hypothèse de l'auteur, énoncée telle qu'il l'énonce

Acheter l'indice tous les jours à heure fixe et le revendre le soir capture la
dérive haussière des indices **sans payer le swap overnight** (≈ 6 %/an sur le
DE40, pour un indice qui gagne 5-10 %/an) et **sans subir les gaps** de nuit et de
week-end. Il ne prétend à aucun signal, aucun filtre, aucun avantage de timing
autre que « être investi le plus longtemps possible » pendant la séance.
[qgsi-u0kOVw · 05:24, 07:32, 08:24, 10:39]

C'est donc, par construction, **du bêta indiciel**. Un R/trade positif ne prouve
rien à lui seul : il faut le comparer à ce que la même période donnait sans
stratégie. C'est ce que ce document fixe d'avance.

## Ce qui est reproduit, et ce qui ne l'est pas

**Reproduit tel quel** : un achat par jour à heure fixe, clôture à heure fixe le
même jour, long seulement, ni stop ni cible ni trailing ni break-even, option
« wait for new day high » désactivée, sur DE40 / US Tech (NASDAQ) / US30. Horaires
de l'auteur : 01:05 → 23:50 pour les indices US, 09:05 → 22:55 pour le DE40.

**Non reproduit** : le dimensionnement notionnel de 50 000 € (couche risque, R2) ;
le courtier (IC Markets chez lui, Swissquote chez nous — spreads et horaires de
séance diffèrent) ; le swap réellement payé sur la nuit résiduelle (non modélisé,
on rapporte seulement ce qu'il dit éviter).

**Imposé par la plateforme, et déclaré comme tel** :

| Contrainte | Ce qu'elle change | Comment on la rend visible |
|---|---|---|
| R3 — stop obligatoire | Il n'a **aucun** stop. On déclare une garde catastrophe `guard_pct` sous l'entrée. | Nombre de trades qui la touchent, par cellule et par instrument. Si elle mord souvent, ce n'est plus sa stratégie. |
| Sortie temporelle = `max_hold_bars=k` | Le moteur ferme k barres après l'entrée, pas à une heure d'horloge. | k dérivé de la séance observée ; distribution des heures de sortie publiée ; écart résiduel avec son horaire chiffré. |
| Maillage H1 | Son 01:05 tombe **dans** la barre 01:00. | `entry_hour_offset` ∈ {0, 1} : 0 = entrée au close de la barre 00:00 (5 min trop tôt), 1 = au close de la barre 01:00 (55 min trop tard). Fidélité = 0. |
| Coût de bord | Il n'en parle pas pour cette stratégie. | Tout est rejoué au spread **catalogue** et au spread **mesuré** sur les barres. |

## La grille — 6 cellules, figées ici

`guard_pct` ∈ {0,03 ; 0,05 ; 0,10} × `entry_hour_offset` ∈ {0, 1}.
**Cellule de fidélité : `guard_pct` = 0,05, `entry_hour_offset` = 0.** C'est elle
qui porte le verdict ; les cinq autres ne servent qu'à montrer la sensibilité aux
deux contraintes de plateforme ci-dessus.

*Note de harnais* : le walk-forward est lancé **deux fois par instrument**, une
fois par valeur d'`entry_hour_offset`, parce que le nombre de barres de détention
dépend de l'offset (entrer une heure plus tard impose de tenir une barre de moins
pour sortir à la même heure) et que `max_hold_bars` est un réglage du moteur, pas
une colonne de grille. Les deux passes couvrent exactement les 6 cellules.

---

## Les mesures obligatoires (aucune n'est optionnelle)

### Bras moteur

1. **Bras fidèle** : `max_positions=1, cooldown_bars=0, cb_losses=999,
   cb_cooldown_bars=0, max_hold_bars=<par instrument et par offset>`. Aucune règle
   commune ne s'y applique — doctrine Adrian 2026-09-12.
2. **Bras règles communes** (information seulement, cellule de fidélité) :
   `cooldown_bars=2, cb_losses=3, cb_cooldown_bars=24`. Avec un trade par jour et
   un taux de réussite voisin de 50 %, le coupe-circuit se déclenchera souvent ;
   on publie ce qu'il coûte. **Il ne peut ni valider ni invalider la stratégie.**

### Étalons — la partie qui décide

- **(a) Acheter-et-tenir** sur la même période : `(dernier close / premier close − 1)`.
- **(b) Décomposition jambe intraday / jambe overnight**, calculée directement sur
  les barres, sans moteur : pour chaque jour, `intraday = close(sortie)/close(entrée) − 1`
  et `overnight = close(entrée du jour suivant)/close(sortie) − 1`. On publie la
  somme de chaque jambe, sa décomposition par année et le drawdown maximal de
  chaque cumul. **C'est le test direct de sa thèse** : la jambe intraday porte le
  rendement, la jambe overnight porte le risque de gap.
- **(c1) Bras témoin commun** (`core.backtest.anchored_wf.control_arm`), même
  `engine_kwargs`. **Réserve écrite d'avance** : ce module recopie le filtre
  d'heures de la stratégie quand celle-ci couvre moins de 80 % des heures
  disponibles — ce qui est notre cas exact (une seule heure d'entrée). Le témoin
  tirera donc ses entrées **à la même heure** et ne mesurera pas le timing. On le
  publie quand même (R9, comparabilité avec les autres dossiers) **en le déclarant
  non informatif ici**.
- **(c2) Balayage horaire** — la version qui répond vraiment à la question.
  La même stratégie, même garde, même durée de détention, rejouée par le **moteur
  commun** pour **chaque heure de séance possible**. Le percentile de l'heure de
  fidélité parmi toutes les heures est le vrai « percentile témoin » : c'est
  l'énumération exhaustive de l'entrée aléatoire, donc strictement plus forte
  qu'un tirage de Monte-Carlo.

### Unités

P&L publié **en R** (convention plateforme) **et en % du prix d'entrée**
(`Σ (sortie − entrée)/entrée`). Le R dépend de `guard_pct` (le dénominateur est la
garde) : **deux cellules de gardes différentes ne se comparent qu'en %.** Le swap
évité n'est pas modélisé ; on rappelle seulement son ordre de grandeur déclaré
(≈ 6 %/an sur le DE40).

---

## Les seuils

### Références de fidélité — avant tout jugement de rentabilité

Son live (mars 2024 → sept. 2026) : > 50 % de ses ~100 k€ de profit, ≈ 2 000 trades,
50 000 € de notionnel par trade, DE40 +16 k€, US30 +13,9 k€, US Tech le plus gros
contributeur, drawdown ≈ 24 k€ pendant les annonces de droits de douane américains
(printemps 2025). Rapporté au notionnel : **≈ +0,03 % par trade en moyenne** et un
épisode de drawdown de **≈ −48 % du notionnel**.

Sur nos 5 ans, cellule de fidélité, la reproduction est **fidèle** si :

- **F1** ≈ 250 trades/an et par instrument (séance quotidienne complète) ;
- **F2** % moyen par trade de l'ordre de **+0,02 % à +0,06 %** ;
- **F3** signe par année cohérent avec la performance intraday de l'indice cette
  année-là (une année baissière de l'indice doit ressortir négative) ;
- **F4** le drawdown du printemps 2025 (droits de douane) est visible dans la
  courbe et dans la ligne 2025.

Une reproduction qui échoue F1-F4 **ne mesure pas sa stratégie** : c'est alors le
dispositif qui est en cause, pas l'hypothèse (voir plus bas).

### Réussite — les trois conditions ensemble

1. Cellule de fidélité **positive au spread mesuré** sur **≥ 2 des 3 indices** ;
2. **et** percentile du balayage horaire (c2) **≥ 90** — le timing d'entrée compte ;
3. **et** jambe intraday **≥ acheter-et-tenir moins la jambe overnight** — la
   réouverture quotidienne ne détruit pas le bêta.

### Réussite partielle, à nommer exactement ainsi

Si la cellule de fidélité est **positive** mais que le percentile horaire est
**≈ 50** et que la jambe intraday est **≈ acheter-et-tenir**, alors le verdict
s'écrit, mot pour mot :

> **« réussite en tant que bêta indiciel, pas d'edge de timing »**

et rien d'autre. C'est d'ailleurs exactement ce que l'auteur revendique.

### Échec — l'une suffit

- Cellule de fidélité **négative au spread mesuré** sur **≥ 2 des 3 indices** ;
- **ou** jambe intraday **nettement inférieure** à la jambe overnight — sa thèse
  centrale serait alors fausse sur nos données : le rendement serait dans la nuit,
  et rester investi la nuit vaudrait mieux que la séance, swap compris.

### Échec du dispositif, pas de l'hypothèse

- R1 en défaut → on corrige et on remesure.
- Nombre de trades très inférieur au nombre de jours de séance (le moteur saute des
  jours à cause d'une position qui déborde) → le modèle de sortie est faux, on le
  répare avant de conclure quoi que ce soit.
- Garde catastrophe touchée sur plus de **2 %** des trades → ce n'est plus sa
  stratégie sans stop, c'est une autre ; le verdict porte alors sur la garde, ce
  qui doit être dit.
- Écart d'heure de sortie systématiquement supérieur à une barre → l'approximation
  `max_hold_bars` ne tient pas sur cet instrument.

---

## Ce qui ne sera pas fait

- Aucune cellule, aucun instrument, aucun filtre ajouté après lecture des résultats.
- Aucun « wait for new day high », aucun trailing, aucun break-even : il les a tous
  désactivés, on ne les réintroduit pas pour sauver un chiffre.
- Aucune promotion PAPER/LIVE : décision d'Adrian seule (R10).

## Ce que chaque issue nous apprendra

| Issue | Lecture |
|---|---|
| Réussite (3 conditions) | L'heure d'entrée porte une information en plus du bêta. Surprenant au vu de ce qu'il revendique lui-même — à confronter à un forward scellé avant toute conclusion. |
| Réussite en tant que bêta | Conforme à sa propre thèse. La question devient une question d'allocation (préfère-t-on ce véhicule à un ETF ?), pas de signal. Décision Adrian. |
| Échec par la jambe overnight | Sa thèse ne tient pas sur nos données/notre courtier. À croiser avec le swap réel de Swissquote avant de trancher. |
| Échec par le coût | Le spread de l'indice mange une espérance de +0,03 %/trade. Sa stratégie dépend alors du courtier, pas de la règle. |
| Échec du dispositif | On répare et on remesure. Aucun verdict n'est publié dans cet état. |

---

# ADDENDUM du 2026-09-12 (après la première mesure, sur revue qualité)

**Les critères ci-dessus ne sont PAS modifiés** — ni les seuils, ni la grille, ni
les libellés de verdict. Cet addendum corrige des défauts de MÉTHODE trouvés par
la relecture, et déclare ce qui doit l'être. Il est daté et placé après, pour que
personne ne puisse le confondre avec une pré-inscription.

## A1 — Le % était faux (correction de mesure, pas de critère)

Le harnais calculait `(exit_price − entry_price) / entry_price`. Le moteur replie
le coût de bord d'ENTRÉE dans `entry_price` mais stocke `exit_price` BRUT, et ne
déduit le coût de SORTIE que dans `pnl_r` : cette formule **ne payait donc que la
moitié du spread**. Toutes les valeurs en % sont désormais dérivées de `pnl_r`
(`pct = pnl_r × risk_distance / entry_price`), net des deux côtés, le moteur
restant la source unique de vérité. Effet sur la cellule de fidélité au spread
mesuré : DAX 56,31 → **47,91** ; NASDAQ 75,89 → **71,42** ; US30 49,25 → **43,47**.
Le sens des conclusions ne change pas ; leur amplitude, si.

## A2 — La condition de réussite n°3 est vide de contenu (déclaré, pas réécrit)

Telle qu'écrite — « jambe intraday ≥ acheter-et-tenir moins la jambe overnight » —
elle ne peut rien départager. Les deux jambes se télescopent par construction :
`(1+I)·(1+O) = 1+BH`, donc `BH − O = I·(1+O)`. La condition se réduit exactement à
**« la jambe overnight est ≤ 0 »** — c'est-à-dire à l'hypothèse qu'elle était censée
tester. Lue en sommes plutôt qu'en composés, elle mélange deux unités et ne veut
rien dire non plus.

Conséquence assumée : **la condition 3 est rapportée, et déclarée non
discriminante.** Elle n'est pas réécrite après coup, et elle ne sert pas à faire
pencher le verdict d'un côté ou de l'autre. La quantité qui porte réellement
l'information — le signe et la taille de la jambe overnight, et le drawdown de
chaque jambe — est publiée telle quelle. Le verdict se joue donc sur les
conditions 1 et 2, dont aucune n'est affectée par ce défaut.

## A3 — Trois variantes d'étalon, et laquelle porte le verdict

Deux défauts de l'étalon initial, tous deux corrigés :

1. **Chevauchements.** Sur les journées tronquées, la sortie du jour k tombait
   après l'entrée du jour k+1 : la jambe overnight y était calculée sur un
   intervalle de temps **négatif**, et le gap de week-end crédité à la jambe
   intraday. 46 cas sur NASDAQ, 47 sur US30, 0 sur DAX (+ 12 égalités de part et
   d'autre, conservées : overnight nul, journée valide).
2. **Population non comparable.** L'étalon portait sur toutes les journées, alors
   que la stratégie en saute 38 (NASDAQ) et 39 (US30) — et ces journées-là ne sont
   pas tirées au hasard : ce sont des lendemains de séance anormale.

Le harnais publie donc **trois** variantes (toutes journées / sans chevauchement /
journées tradées) avec leurs effectifs. **Le verdict s'appuie sur « journées
tradées »**, seule population comparable à la stratégie.

**À charge, et il faut le dire** : ce choix est arrêté APRÈS avoir vu la première
mesure, et il est **plus favorable** à la thèse de l'auteur — sur NASDAQ la jambe
overnight passe de +1,83 % (toutes journées) à −4,80 % (journées tradées), ce qui
fait disparaître le seul contre-exemple du premier rapport. Les trois variantes
restent publiées côte à côte pour que le lecteur puisse en juger, et le verdict
signale l'écart au lieu de ne montrer que le chiffre qui arrange.

## A4 — Porte R1/R5

La mesure est désormais précédée d'une porte : une fuite de causalité ou une
divergence live/backtest interrompt le run, qui **n'écrit aucun `results.json`** et
sort en code 2. Sans elle, un bug de dispositif pouvait être publié comme un
résultat de recherche. Un instrument en erreur (autre cause) donne un code 1.

## A5 — Convention du percentile horaire

Le chiffre publié est le **rang parmi les AUTRES heures** (référence exclue de sa
propre population). La convention « toutes heures » de `ControlArm.percentile`
(ex æquo comptés pour moitié) est publiée à côté. Aucune lecture du dossier ne doit
dépendre du choix : les deux figurent dans `results.json` et dans le journal.

## A6 — Plafond de spread relevé

Au spread mesuré, `spec_with` relève `max_spread_pips` : sans cela le plafond du
catalogue (DAX : 20 pips) refuserait **tous** les trades au spread mesuré (23 pips)
et la colonne serait silencieusement vide. Le relèvement est nécessaire, mais il
neutralise le garde-fou anti-news : à spread mesuré, aucune barre n'est jamais
écartée pour spread excessif. Déclaré au § Réserves du verdict.

# Analyse — s16_confluence « quatre lectures pour décider d'entrer »

Source : mandat Adrian, 2026-08-20. Trader : interne. Magic : **130016**.

> **Ce document n'est PAS un scellé.** Il ne fige aucun seuil, ne déclare aucune
> falsification, n'autorise aucun backtest. Il pose le problème, mesure l'état
> des entrées, propose l'architecture et l'ordre des opérations. C'est l'étape
> qui **précède** le gel.
>
> **Pourquoi il ne peut pas être un scellé** : trois des quatre entrées de la
> stratégie ont aujourd'hui une valeur **inconnue** (sentiment : verdict au plus
> tôt mi-octobre 2026 ; anticipations : étude en suspens et source Polymarket
> inexistante ; avis de Claude : mesuré NE PAS ARMER). Un protocole scellé
> aujourd'hui le serait sur des entrées qui bougeraient sous lui — c'est-à-dire
> sur rien. Le §B développe.

**Aucun chiffre de résultat n'est produit par ce document.** Tous les nombres
cités sont des mesures **antérieures**, avec leur source.

---

## 0. La demande, reformulée sans l'adoucir

Adrian, verbatim du mandat : une stratégie sur **plusieurs marchés forex**,
mêlant quatre lectures — (1) technique, (2) sentiment, (3) ce que les autres
anticipent (positionnement COT institutionnel + cotes des marchés prédictifs
type Polymarket sur Fed / CPI / récession, en **lecture seule** : pas de compte,
pas de capital, pas d'exécution sur ces places), (4) avis de Claude Code — dont
« la combinaison des 4 résultats devrait nous donner un niveau de certitude sur
le choix d'entrer ou non ». Objectif : **swing, 1 à 10 trades par semaine, sur
les tendances générales**. Plus une gestion de sortie « intelligente et
dynamique ».

Reformulation opérationnelle, en deux objets distincts qui n'ont ni le même
calendrier ni les mêmes dépendances :

| Objet | Nature | Mesurable quand ? |
|---|---|---|
| **O1 — le score de confluence** | combiner 4 lectures en un niveau de confiance sur la décision d'entrer | pas avant qu'au moins 2 des 3 conseils aient rendu un verdict (§G) |
| **O2 — la gestion de sortie** | s'applique à des entrées DÉJÀ validées, sur historique réel | **aujourd'hui**, à un préalable moteur près (§E) |

O2 ne dépend d'aucun des quatre piliers. Les mélanger ferait attendre à la
partie mesurable le calendrier de la partie non mesurable. Ils sont séparés ici,
et le resteront.

---

## A. L'état de chaque pilier, chiffré

### A.1 Pilier technique — un edge étroit, et porté par ce qui n'est pas du forex

| Mesure | Valeur | Source |
|---|---|---|
| Portefeuille naïf Tier-1, config walk-forwardée (v4) | OOS honnête **+3142 CHF, 3/3 folds positifs**, 180 trades sur 3 tranches de ~6 mois | `results/config_walkforward_v4.txt` |
| Biais de sélection de **config** | **+98 CHF** (matched-book +103) — marginal : l'honnête retient 97 % de l'oracle | idem |
| Concentration (v4) | **SP500 seul = 54,3 %** de l'agrégat honnête | idem, table CONCENTRATION |
| v5 — en walk-forwardant AUSSI l'instrument et la famille | **+1828 CHF, 3/3 positifs** ; biais total +1412 dont **+1314 = sélection d'instruments** ; **SP500 = 93 %** de l'agrégat | `TODO.md` §session 2026-08-17 |
| Biais restant, **non mesuré** | conception de la grille (templates, échelles SL/TP dessinés en regardant les 5 ans) | v4 §limitation 2 |
| Naïve vs glouton | +3374 contre +939 (11 candidats) — toute la valeur vient du **filtre Tier-1**, pas de l'optimisation | `TODO.md` |
| S1 hors H1 | **0/11 paires en H4**, AUDCHF et EURUSD compris | `s1_multiframe_test.txt` |
| S2 (s11 cassure) | **PAS D'EDGE** : 26 STRICT contre ~51 attendues par pur hasard sur 1024 cellules, **25 des 26 sur un seul instrument** ; voisinage 3×3 hors échantillon **0/9** ; +0,013 R/t à spread réel. Survivante DAX seule, cassée en forward-test de juillet | `s11_legacy_breakout/research/VERDICT.md`, `TODO.md` |
| S5 (trend-pullback) | **0 exploitable** sur H1, H4 **et** D1. WR 27-28 % contre seuil 25 % ; péage H1 = 2,14 pts de WR → le broker prenait tout l'edge | `s5_multiframe_test.txt`, `timeframe_economics.py` |
| s13 (MACD forex D1) | une seule survivante, **AUDCAD famille C** (retour à la moyenne) : hold-out scellé +0,58 R/t × **11 trades**, percentile témoin 96. Familles A (mean-rev s12 transposé) et B (croisements) : **mortes** | `s13_macd_fx/manifest.yaml`, `research/VERDICT.md` |

#### A.1bis Le fait que la demande « forex » rend décisif

Le mandat dit **forex**. Or l'agrégat mesuré est porté par ce qui n'est pas du
forex. Ventilation du +3142 CHF honnête de v4 :

| Bloc | Contribution | Part |
|---|---|---|
| Indices (SP500 +1705, FTSE +483, NIKKEI +472) + DAX/S2 +180 | **+2840 CHF** | **90,4 %** |
| Forex (AUDCHF +168, EURUSD +129, AUDUSD +125, EURCHF **−120**) | **+302 CHF** | **9,6 %** |

**POURQUOI c'est structurant** : restreindre l'univers au forex, comme le mandat
le demande, retire **90 % du résultat mesuré** et laisse quatre noms dont un
négatif, sur trois tranches OOS. Ce n'est pas un argument contre le forex ;
c'est l'énoncé de ce qu'on sait, et il doit être devant les yeux avant qu'un
score de confluence promette quoi que ce soit.

**Ce que le pilier technique apporte réellement au dossier** : un flux de
candidats à espérance **≥ 0 mesurée**, sur H1, sur AUDCHF et EURUSD, et un
filtre d'admission (Tier-1) qui est la seule pièce dont la valeur ait été
isolée. C'est peu, mais c'est le seul socle vivant du dépôt — et le rejeu de
`macd_ai_paper` a établi qu'un conseil posé sur un socle mort ne produit rien
(§A.4).

### A.2 Pilier sentiment — collecte en cours, aucune valeur démontrée

| Élément | État au 2026-08-20 |
|---|---|
| Protocole | scellé 2026-08-17, **re-scellé 2026-08-18** (amendement n° 1 : `category` forex → general ; corpus remis à zéro, 0 news 0 verdict au moment de l'amendement) |
| Corpus | ~180 lignes `VERDICT` au journal. **Ce n'est pas l'effectif de la mesure** : F1 compte les **verdicts comptables** — par cellule (juge, symbole, barre cible), le dernier verdict avant l'ouverture, **directionnel et à confiance ≥ 0,8**. Les `neutral`, les `< 0,8` et les verdicts annulés par un verdict postérieur n'en sont pas. L'effectif comptable est nécessairement très inférieur à 180 |
| F1 (droit de parler) | **N ≥ 150 comptables ET ≥ 60 jours**, par juge → **2026-10-17 au plus tôt** (60 jours après le re-scellement), et seulement si N y est |
| Plancher de valeur | hit-rate dont la **borne basse** de l'IC 95 % unilatéral (Wilson) dépasse **0,52** — 0,50 est la pièce, 0,52 est le péage D1 (0,46 pt de WR) avec ~4× de marge |
| F3 | Claude doit battre **FinBERT** (gratuit, local) sur corpus apparié, sinon les tokens ne sont pas justifiés |
| Durée maximale | 6 mois → lecture finale obligatoire **2027-02-17** ; une étude qui n'a pas tranché rend NON CONCLUSIF |
| Issue autorisée si VALEUR CANDIDATE | proposition d'une étude d'intégration comme **FILTRE sur des signaux à edge mesuré** — **jamais** comme signal autonome (`s14/PROTOCOL.md` §6) |

**Valeur démontrée à ce jour : aucune.** Le protocole interdit explicitement de
calculer un hit-rate avant F1 (« on ne regarde pas la casserole »).

### A.3 Pilier anticipations — une moitié en suspens, l'autre inexistante

**A.3a — COT (positionnement institutionnel).**

| Élément | État |
|---|---|
| Donnée | téléchargée et réelle : **OR 1929 obs** (1986→2026), **EURO 1451**, AUD 1793, CHF 1928, CAD 1930, JPY 1930 |
| Garde anti-fuite | `core/data/cot.py` — `connu_au()` est la **seule porte de lecture** : retient l'observation du mardi jusqu'au jeudi, l'ouvre le vendredi ; gel budgétaire 2025 (30 sept. → 29 déc.) codé |
| Littérature | **Klitgaard & Weir (Fed de New York, 2004)** : le positionnement explique **30-45 %** du mouvement de change de **la même semaine**, ~**75 %** de réussite sur la direction de cette semaine-là, et **ne prédit pas la semaine suivante**. Corrélation **synchrone**, pas prédictive |
| Étude s15 | protocole gelé 2026-08-19, **EN SUSPENS** : la famille « niveau extrême » ne réunit que **2 à 9 épisodes indépendants** de hold-out contre un plancher **dérivé** de **12** (test de signe, multiplicité 128 cellules et ≤ 3 candidates) |
| Contrainte de fréquence | le COT est hebdomadaire : **D1 obligatoire**, ~52 occasions/an/instrument. Un scellé se dimensionne en **occasions de décision**, pas en jours |
| Impossibilités | DAX et FTSE n'ont **aucun** rapport COT ; la CFTC révise silencieusement (tout notre échantillon est de la donnée **révisée** — angle mort qu'aucun falsifieur rétrospectif n'attrape) ; la publication peut s'arrêter trois mois (2025) |

**Conséquence pour s16** : la seule chose que le COT puisse fournir à un score
de confluence est un état **hebdomadaire**, sur **deux instruments directs**
(XAUUSD, EURUSD) dont un seul est du forex. Il ne peut pas nourrir une décision
H1. Et son attente a priori déclarée est **edge faible ou nul**.

**A.3b — marchés prédictifs (Polymarket, Kalshi).**

**Rien n'existe.** Ni collecteur, ni cache, ni mesure, ni protocole. Trois
inconnues doivent être levées **dans cet ordre**, avant toute étude (§G, étape 5) :

1. existe-t-il un **historique horodaté téléchargeable** des cotes ? Sans lui,
   aucun backtest n'est possible et la seule voie est un archivage append-only
   qui commence aujourd'hui — 12 mois d'investissement avant la première lecture
   (raisonnement identique au sentiment retail, `TODO.md`) ;
2. la cote porte-t-elle une information **non déjà contenue** dans les futures
   Fed funds, qui, eux, ont un historique long et gratuit ? Si non, la source
   est redondante et le dossier se ferme sans un backtest ;
3. quelle est la **latence** entre l'événement et la re-cotation ? Une cote qui
   bouge après le prix est du sentiment contemporain, pas une anticipation —
   exactement le piège Klitgaard & Weir, transposé.

**Leçon opposable, déjà payée** : `s14/PROTOCOL.md` amendement n° 1 — la
catégorie de news avait été scellée sans qu'on ait jamais regardé ce que
l'endpoint renvoyait (1 article par appel). **Mesurer une source avant de la
sceller.**

### A.4 Pilier « avis de Claude » — mesuré, verdict NE PAS ARMER

`studies/macd_ai_paper/VERDICT_REPLAY.md`, rejeu à l'aveugle de 400 dossiers,
2026-08-17. C'est la seule des quatre lectures qui ait déjà été **mesurée**.

| Fonction confiée à l'IA | Mesure | Lecture |
|---|---|---|
| **Filtrage** (prendre / ne pas prendre) | percentile groupé **95,6** → **90,0 stratifié** une fois la composition du pool neutralisée ; par strate : 77,6 (MT5) et 89,3 (LONGHIST), **aucune ≥ 95** | signal de tri **mince**, jamais au seuil. Écho exact de s93 (88,5) |
| **Dosage de la taille** | corrélation taille/résultat **+0,022** | **nul** |
| **Ajustement SL/TP** | 47 trades ajustés : base **−6,2 R** → ajusté **−10,0 R** (Δ **−3,9 R**) | **nuisible** |
| Espérance des trades pris | **−0,065 R/pris** (contre −0,124 en prenant tout) | la sélection **réduit la perte de moitié, elle ne crée pas d'espérance positive** |

**Ce que ça impose au design de s16, sans négociation** :

1. l'avis de Claude se limite à **PRENDRE / NE PAS PRENDRE**. Pas de taille, pas
   de déplacement de stop — mesuré nul une fois, nuisible une fois ;
2. le verdict est **« ne pas armer »**, pas « impossible ». Le socle testé était
   mort (s12 : −0,006 R/t à spread nul, percentile 51,5). La question « l'IA
   ajoute-t-elle ? » n'a jamais été posée sur un flux à espérance ≥ 0 ;
3. l'infrastructure (runner 3 bras + journal chaîné + juge headless) est prête
   et se rebranche telle quelle. C'est le seul actif immédiatement réutilisable
   des quatre piliers.

### A.5 Synthèse — ce qu'on a le droit de dire aujourd'hui

| Pilier | Valeur mesurée | Date du prochain fait nouveau |
|---|---|---|
| Technique | **positive mais étroite** (H1, AUDCHF+EURUSD ; le reste du livre n'est pas du forex) | dépend d'un forward scellé, pas d'une relecture |
| Sentiment | **inconnue** — collecte en cours | 2026-10-17 au plus tôt |
| Anticipations / COT | **inconnue** — étude en suspens faute d'épisodes | dépend d'une décision Adrian (§G, étape 4) |
| Anticipations / prédictifs | **inexistante** — pas de source | ≥ 12 mois si archivage, sinon jamais |
| Avis de Claude | **mesurée : NE PAS ARMER** sur socle mort ; take/skip mince, dosage nul, gestion nuisible | dépend d'un socle vivant à lui soumettre |

**Une seule des quatre lectures a une valeur mesurée, et c'est un « non ».**

---

## B. Le problème méthodologique central

### B.1 Combiner des inconnues ne produit pas de la certitude, mais des degrés de liberté

La phrase du mandat — « la combinaison des 4 résultats devrait nous donner un
niveau de certitude » — contient une inversion. Une combinaison ne crée pas
d'information : elle crée un **espace de configurations**. Décompte, en restant
modeste :

| Degré de liberté | Cardinal plausible |
|---|---|
| Portée de chaque conseil : `requis / optionnel / aucun`, × 3 conseils | 27 |
| Pondération des 4 lectures, échelle à 10 crans | 10⁴ = 10 000 |
| Seuil de prise du score combiné | ~20 |
| **Total, ordre de grandeur** | **≈ 5 × 10⁶** |

À comparer avec ce qui est observable : **180 trades OOS** mesurés à ce jour sur
le portefeuille complet, et **~115 trades/an** en prospectif à la cadence
mesurée (§F.2). Sous H0, `s15` déclarait déjà attendre 6 à 7 cellules vertes sur
128 par pur hasard. Sur 5 × 10⁶ cellules, on en attend de l'ordre de **250 000**.

> **Il y a plus de configurations possibles que de trades observables en une vie
> de projet.** Toute recherche menée dans cet espace trouvera du vert. Le vert
> ne voudra rien dire.

### B.2 Un échec ne serait pas attribuable

Second défaut, indépendant du premier. Si un score à 4 entrées perd de l'argent,
on ne peut pas savoir laquelle des entrées a échoué : elles n'ont jamais été
mesurées séparément sur le même flux. Et si le score gagne, on ne peut pas
savoir laquelle a produit le gain — donc on ne peut ni la renforcer, ni retirer
les trois autres. Un système inattribuable ne s'améliore pas : il se refait.

C'est le motif que `macd_ai_paper` a résolu avec ses bras parallèles
(MECH / AI / RND / SHADOW), et c'est celui que le §D généralise.

### B.3 La conséquence, énoncée pour qu'elle ne soit pas révisée plus tard

> **On ne peut pas sceller une étude de combinaison tant que les entrées n'ont
> pas de valeur connue : le protocole serait scellé sur des entrées qui bougent
> sous lui.**

Cas concret, à trois mois d'échéance. Si un scellé de combinaison était posé
aujourd'hui, et qu'en octobre 2026 `s14` rendait **PAS DE VALEUR** sur le juge
Claude, deux issues seulement :

- **rompre le scellé** pour retirer l'entrée sentiment → l'étude est invalidée
  (`s14/PROTOCOL.md` §5, `macd_ai_paper/PROTOCOL.md` §4 : « toute modification
  invalide l'essai, redémarrage à zéro ») ; ou
- **continuer** à faire tourner une étude dont une entrée est mesurée sans
  valeur — c'est-à-dire dépenser un an de forward sur un degré de liberté mort.

Aucune des deux n'est acceptable. Le scellé vient **après** les verdicts, jamais
avant. Le §G écrit la condition exacte.

### B.4 Ce que cela n'interdit pas

Cela n'interdit pas de **construire l'appareil de mesure** aujourd'hui. Au
contraire : l'appareil doit précéder les verdicts, parce que le bras de
référence est un compteur prospectif qui **ne se rattrape pas rétroactivement**
(§D.1). Ce qui est interdit, c'est de figer les **règles de lecture** d'une
combinaison dont les termes ne sont pas encore définis.

---

## C. La reformulation qui rend la demande falsifiable : un score CALIBRÉ

### C.1 L'énoncé

L'intuition d'Adrian — « un niveau de certitude sur le choix d'entrer » — a une
version rigoureuse. Elle ne consiste pas à construire un score, mais un score
**calibré**. La revendication devient :

> **Quand le système annonce X % de confiance, l'événement déclaré se produit
> X % du temps.**

### C.2 L'événement doit être binaire et déclaré d'avance — sinon la calibration mesure la sortie

Piège à désamorcer immédiatement : « le trade est rentable » n'est pas un
événement admissible, parce qu'il dépend de la géométrie de sortie. Un score
parfaitement calibré sur des cibles à 2 ATR paraîtrait décalibré si l'on passait
à un trailing. On mesurerait la sortie, pas la lecture.

> **Événement figé d'avance** : *le trade atteint sa cible avant son stop*, à
> géométrie de sortie **constante** pendant toute la fenêtre de calibration.

Corollaire direct : **l'étude de sortie (§E) et l'étude de calibration ne se
mènent pas en même temps sur le même flux.** L'une fait varier ce que l'autre
tient constant. C'est une raison de plus de les séparer.

### C.3 Comment se mesure une calibration

Trois instruments, tous déterministes, tous calculables sans hypothèse.

**(a) La courbe de fiabilité.** On découpe les prédictions en tranches de
confiance ; pour chaque tranche k : `p̂ₖ` = confiance moyenne annoncée,
`ōₖ` = fréquence observée de l'événement, `nₖ` = effectif. On trace `ōₖ` contre
`p̂ₖ`. Un système calibré suit la diagonale. **La courbe se lit toujours avec
son effectif par tranche affiché** — une tranche à 12 observations ne dit rien,
et une courbe sans ses `nₖ` est une illustration, pas une mesure.

**(b) Le score de Brier.** `BS = (1/n) Σ (p̂ᵢ − oᵢ)²`, `oᵢ ∈ {0,1}`. Plus bas
est meilleur. Sa décomposition (Murphy) est ce qui le rend utile :

```
BS  =  fiabilité  −  résolution  +  incertitude

       Σ nₖ/n (p̂ₖ−ōₖ)²   Σ nₖ/n (ōₖ−ō)²    ō(1−ō)
       ce qu'on teste     ce qui rend le    irréductible
                          score UTILE
```

**(c) Le témoin obligatoire : le score constant.** Un système qui annonce
toujours le taux de base `ō` est **parfaitement calibré par construction** et
strictement inutile : sa fiabilité est nulle, sa **résolution est nulle**, son
Brier vaut exactement l'incertitude. Toute candidate doit donc battre ce témoin
sur le Brier **et** afficher une résolution strictement positive, d'une marge
déclarée d'avance.

> **POURQUOI la calibration est supérieure à « le score marche »** : un score
> mal calibré se démasque tout seul, sur ses propres annonces, sans qu'on ait
> besoin de savoir s'il est rentable. Et la calibration se mesure **avant** la
> rentabilité — voir C.5.

### C.4 L'effectif requis — dérivé, pas choisi

Question : combien de trades par tranche pour que la courbe de fiabilité soit
lisible ? La réponse dépend de la **résolution visée** — la demi-largeur `e` de
l'IC 95 % sur la fréquence observée dans une tranche. À `p ≈ 0,5` (le cas le
moins favorable), l'erreur-type binomiale est `0,5/√n`, donc :

```
n = ( z / (2e) )²        avec z = 1,96
```

| Résolution visée `e` | `n` par tranche | Tranches | `n` total | Durée à **2,2 trades/sem** (§F.2) |
|---|---|---|---|---|
| ± 5 pts (tranches de 10 pts, 5 tranches) | **384** | 5 | 1 920 | **≈ 17 ans** |
| ± 8,5 pts (tranches de 17 pts, 3 tranches) | **133** | 3 | 399 | **≈ 3,5 ans** |
| ± 10 pts (2 tranches : « consulte » / « confiant ») | **96** | 2 | 192 | **≈ 1,7 an** |

Et ces durées sont **optimistes** : les positions simultanées d'un portefeuille
partagent leurs moteurs macro, l'IC binomial surestime donc l'indépendance
(même réserve que `s14` §4 « angle mort corrélation » et que les épisodes de
`s15`). L'effectif effectif est inférieur à l'effectif compté.

**Conclusions, à écrire avant tout chiffre :**

1. **Une courbe de fiabilité à 5 tranches est hors de portée** — 17 ans à la
   cadence mesurée. Toute présentation d'une telle courbe avant cet horizon sera
   une illustration, pas une mesure.
2. **Le nombre de tranches est figé à 3 au maximum**, décidé maintenant, avant
   d'avoir vu la moindre confiance produite. Fixer les tranches après coup
   serait choisir le découpage qui flatte la courbe.
3. **Le premier point lisible est à ~18-24 mois** de fonctionnement du bras
   combiné, à 2 tranches. Ce n'est pas une objection : c'est la raison pour
   laquelle le compteur doit démarrer tôt (§G).

### C.5 Pourquoi la calibration est mesurable AVANT la rentabilité — et ce qui la rend observable

La calibration est une propriété des couples (prédiction, résultat). Elle ne
demande pas que le flux soit rentable : un score peut être **bien calibré sur un
flux perdant**, et c'est une information de pleine valeur (il lit correctement
un flux qui n'a pas d'espérance). Inversement, un score rentable mais décalibré
est une série de chance.

Mais il y a une condition matérielle : **une tranche ne se remplit que si l'on
observe le résultat des trades qu'on n'a PAS pris.** Si le score annonce 55 % et
que l'on s'abstient, la tranche 55 % reste vide à vie.

> C'est le rôle du bras **SHADOW** (`macd_ai_paper` §2) : un contrefactuel
> comptable ouvert sur **chaque** signal, à configuration de base, sans blocage
> ni cooldown, quelle que soit la décision des bras. Le shadow n'est pas un
> confort : **sans lui, la calibration est inobservable.**

### C.6 Ce que la calibration n'autorise pas

Un score calibré **ne se branche pas sur la taille de position**. La mesure
existante est sans ambiguïté : corrélation taille/résultat **+0,022** — nulle
(§A.4). Le champ `Signal.confidence` du contrat (`core/contracts/strategy.py`)
porte le commentaire « may modulate risk if the strategy supports it » : cette
faculté reste **désactivée** tant que la calibration n'est pas démontrée sur son
propre protocole. Un score calibré autorise à **décider**, pas à **doser**.

---

## D. L'architecture de mesure — la partie constructible maintenant

C'est le livrable exploitable de ce document. Il généralise le motif
MECH / AI / RND / SHADOW de `macd_ai_paper`, seul dispositif du dépôt ayant
réellement rendu un verdict attribuable sur un conseil.

### D.1 Les bras parallèles — obligatoires, et pourquoi

| Bras | Décision d'entrée | Rôle |
|---|---|---|
| **A0 — MECH** | prend tout signal technique | **référence, à vie**. Le dénominateur de toute attribution |
| **A1 — MECH+SENT** | technique, filtrée par le sentiment | isole l'apport du pilier 2 |
| **A2 — MECH+ANTI** | technique, filtrée par les anticipations | isole l'apport du pilier 3 |
| **A3 — MECH+CLAUDE** | technique, filtrée par l'avis de Claude | isole l'apport du pilier 4 |
| **A4 — ALL** | technique, filtrée par le score combiné calibré | l'objet du mandat |
| **A5 — RND** | tirage au **taux de prise de A4**, déterministe par (graine, instrument, barre) | témoin : isole le **choix** de la **fréquence** |
| **SHADOW** | — (comptable, pas un compte) | contrefactuel sur **chaque** signal → le R par signal, indépendant de l'état des comptes ; **rend la calibration observable** (§C.5) |

**POURQUOI A0 est non négociable** : sans bras de référence tournant en
parallèle et à vie, aucune attribution n'est possible — on ne saura jamais si un
résultat vient de la stratégie ou du conseil. Et A0 est un compteur
**prospectif** : il ne se rattrape pas rétroactivement. Chaque semaine sans lui
est une semaine définitivement perdue pour la mesure.

**POURQUOI A5 (aléatoire à même fréquence)** : un conseil qui prend moins prend
mécaniquement moins de perdants. Le témoin au **même taux de prise** est ce qui
sépare « il choisit bien » de « il choisit moins ».

### D.2 Ce que la structure en bras rend mesurable, et à quel prix

Les bras décident sur **le même flux de candidats**. La comparaison est donc
**appariée par signal**, pas entre deux moyennes indépendantes — ce qui augmente
fortement la puissance à effectif égal. La statistique pertinente est la
**différence de R sur l'ensemble commun**, jamais l'écart de deux courbes de
compte.

Corollaire à déclarer d'avance : **l'effectif utile d'un bras de conseil est le
nombre de signaux sur lesquels il diverge de A0.** Un conseil qui prend 95 % du
flux n'est mesuré que sur 5 % de celui-ci.

> **Règle à figer** : taux de prise hors de **[0,10 ; 0,90]** → le bras est
> déclaré **NON INFORMATIF**, ni « bon » ni « mauvais ». Reprise directe de
> `macd_ai_paper` §4 (« un juge qui prend tout ou ne prend rien → NON CONCLUSIF »).

### D.3 Le champ de configuration — dans le manifeste, pas dans le moteur

Demande explicite d'Adrian ; cohérent avec **R7** (le manifeste est la seule
source de vérité sur une stratégie).

```yaml
conseil:
  sentiment:     requis | optionnel | aucun
  anticipations: requis | optionnel | aucun
  claude:        requis | optionnel | aucun
  portee: prendre_ou_pas      # FIGÉ — seule valeur admise
```

Sémantique, à figer au moment du scellé :

| Valeur | Effet sur la décision | Effet si le conseil est indisponible |
|---|---|---|
| `requis` | le signal n'est pris que si le conseil est favorable | **signal non pris**, journalisé `na` |
| `optionnel` | le conseil module le score, ne bloque pas seul | score calculé sans lui, journalisé `na` |
| `aucun` | le conseil n'est pas consulté | sans objet |

Trois contraintes portées par le manifeste, pas par le code du moteur :

1. **`portee` n'admet qu'une valeur : `prendre_ou_pas`.** Toute autre valeur est
   refusée au chargement. POURQUOI : dosage de taille mesuré **nul** (+0,022),
   ajustement SL/TP mesuré **nuisible** (−6,2 → −10,0 R). Ce n'est pas une
   précaution, c'est le report d'une mesure.
2. **Dès qu'un conseil ≠ `aucun`, le bras A0 devient obligatoire.** Le manifeste
   refuse une configuration qui consulte sans faire tourner sa référence.
3. **Une panne de conseil ne fausse jamais les témoins** : décision `na`
   journalisée, non comptée comme décision, taux de A5 inchangé, A0 et SHADOW
   continuent (motif `macd_ai_paper` §2, déjà éprouvé).

### D.4 Ce qui est réutilisable tel quel

| Pièce | État | Origine |
|---|---|---|
| Runner multi-bras + journal append-only à chaîne de hachage | **écrit, testé** | `studies/macd_ai_paper/paper_step.py` |
| Juge headless (prompt par STDIN, timeout, relance, `na` propre) | **écrit, testé** | `macd_ai_paper/ai_judge.py`, `s14/ai_judge` |
| Collecteur sentiment + témoin FinBERT | **en production** | `studies/s14_sentiment/` |
| Collecteur COT avec garde anti-fuite | **écrit, 21 tests** | `core/data/cot.py` |
| Témoin empirique apparié (200 tirages, graine) | **écrit** | `core/backtest/anchored_wf.py` (`control_arm`) |
| Collecteur marchés prédictifs | **inexistant** | — |

---

## E. La gestion de sortie — étude séparée, testable aujourd'hui

Elle ne dépend d'aucun des quatre piliers : elle s'applique à des entrées **déjà
validées**, sur données historiques réelles. Elle est donc la seule partie du
mandat mesurable dès maintenant — et elle est posée ici comme **étude autonome**,
à sortir de s16.

### E.1 Le mur de plateforme, vérifié — à traiter avant le protocole

Deux constats de code, pas d'opinion :

1. **`core/backtest/engine.py` n'implémente aucune gestion dynamique.** Dans la
   boucle d'exécution, `stop` et `target` sont des constantes pour toute la
   durée du trade ; rien ne les recalcule barre après barre. Une sortie
   dynamique est donc une capacité **du moteur**, pas de la stratégie —
   et **R9** interdit à une stratégie d'écrire sa propre boucle.
2. **Côté réel, il n'existe aucune voie pour modifier un ordre déjà chez le
   broker.** `core/broker/` ne contient qu'un `__init__.py` vide, et
   `pulse/live_runner.py` n'émet que des `TRADE_ACTION_DEAL` — aucun
   `TRADE_ACTION_SLTP`. Le stop part chez le broker et n'en bouge plus (**R3**,
   set & forget : la position survit à un crash Python).

**Comment composer avec ça** — règles à écrire dans le protocole, avant tout
chiffre :

| Règle | POURQUOI |
|---|---|
| Le niveau dynamique ne se recalcule **qu'à la clôture de barre**, jamais intra-barre | seule forme backtestable sans ambiguïté d'ordre de visite dans la barre (ambiguïté intra-barre mesurée à 0,3 %, `docs/METHODOLOGY.md` §9) |
| Le niveau recalculé est **posté chez le broker** immédiatement après le calcul | entre deux postes, le dernier niveau posté est le seul filet |
| Le stop **ne recule jamais** (monotone dans le sens du trade) | si le process meurt, la position reste protégée au moins au niveau du dernier post, jamais moins bien que le stop initial. C'est ce qui préserve R3 |
| Le **même code** décide en backtest et en live | **R5** — sinon la mesure ne vaut rien |
| La capacité moteur est un ticket `core/` **séparé**, avec ses tests de régression et **R1 re-validé** | modifier le moteur d'exécution invalide tout ce qui a été mesuré avec lui si ce n'est pas fait proprement |

### E.2 Les variantes à comparer

Référence obligatoire en première ligne ; le nombre de variantes reste petit —
chacune est une multiplicité de plus (§B.1).

| # | Variante | Définition mécanique attendue |
|---|---|---|
| **V0** | **TP fixe** — la géométrie actuelle | référence. Aucune candidate ne se lit sans elle |
| V1 | Trailing ATR | stop = extrême favorable − k × ATR14, k déclaré d'avance, recalculé à la clôture, monotone |
| V2 | Sortie sur faiblesse | **à définir causalement (R1)** : condition calculable à la clôture de la barre, sans regarder au-delà. Ex. : n clôtures consécutives contre le sens ; ou retracement d'une fraction déclarée de la MFE. Le choix se fait **avant** de voir les chiffres |
| V3 | TP étendu si le momentum persiste | la cible recule d'un pas d'ATR quand elle est atteinte **et** que la barre clôture au-delà |
| V4 | Break-even mobile | stop ramené à l'entrée après +1 R |

### E.3 L'attente a priori, honnête

> **Sur une stratégie de retour à la moyenne, le TP fixe EST l'edge.** On parie
> sur le retour à l'équilibre ; le point de retour est statistiquement l'endroit
> où le mouvement s'épuise. Prolonger au-delà, c'est parier sur la continuation
> — exactement l'hypothèse que la stratégie ne fait pas.

Conséquence : l'espérance d'amélioration est **faible sur S1** (mean-reversion
H1) et sur la survivante `s13` (famille C, retour). Elle serait meilleure sur
une stratégie de **continuation** — mais S2 est morte (§A.1) et S5 aussi. Le
dépôt n'a aujourd'hui **aucun socle de continuation** sur lequel une sortie
dynamique aurait une chance a priori.

### E.4 L'écueil, chiffré dans sa forme

« Adapter pour maximiser » n'existe qu'en rétrospective : à la clôture d'une
barre, on ne sait pas si le mouvement continue. Toute sortie dynamique
**échange** des composantes d'espérance :

```
E = WR × G  −  (1 − WR) × P
```

| Variante | Ce qu'elle gagne | Ce qu'elle paie | Solde |
|---|---|---|---|
| V1 trailing | sauve des trades qui seraient revenus au stop (`P` ↓ sur ceux-là) | coupe des gagnants avant la cible (`G` ↓) | **inconnu a priori** |
| V3 TP étendu | `G` ↑ sur la queue | rend au marché une part des gagnants qui repassent (`WR` ↓) | **inconnu a priori** |
| V4 break-even | `P` ↓ sur les allers-retours | fabrique des sorties à zéro sur des trades qui auraient atteint la cible | **inconnu a priori** |

> **Le solde net doit être chiffré, par stratégie**, jamais supposé. Et il se
> lit au **R par trade**, jamais au PnL total : retirer ou raccourcir des trades
> fait baisser le total mécaniquement (piège n° 4 du `TODO.md`).

### E.5 Contrainte dure

**La logique de sortie est MÉCANIQUE, jamais l'avis de Claude.** Mesure :
47 trades ajustés par l'IA, base −6,2 R → ajusté **−10,0 R**. C'est le seul des
trois usages testés qui soit mesuré **activement nuisible**. L'interdiction vit
dans le manifeste (`portee: prendre_ou_pas`, §D.3), pas dans une consigne de
prompt.

### E.6 Périmètre

Cette étude **sort de s16**. Elle est proposée comme dossier autonome (`s17`
suggéré), sur les entrées à edge mesuré — S1 AUDCHF/EURUSD en H1, `s13` AUDCAD
en D1 — avec son propre protocole gelé avant le premier backtest, et son
préalable moteur traité comme un ticket `core/` distinct. Elle n'attend aucun
des quatre piliers.

---

## F. L'avertissement sur le régime visé

### F.1 Le swing « sur les tendances générales » est le régime où ce dépôt a échoué

Quatre fois, sur quatre chemins indépendants :

| Test de continuation | Résultat | Chiffre |
|---|---|---|
| **S2 / s11 — cassure** | PAS D'EDGE | 26 STRICT contre ~51 attendues par pur hasard sur 1024 cellules, **25 des 26 sur un seul instrument** ; voisinage 3×3 OOS **0/9** ; +0,013 R/t à spread réel. DAX seul survivant, cassé en forward-test de juillet |
| **S5 — pullback de tendance** | SANS EDGE | 0 exploitable sur **H1, H4 et D1**. WR 27-28 % contre seuil 25 % ; péage H1 = **2,14 pts** de WR |
| **s13 famille B — croisements MACD** | morte | seule la famille **C** (retour à la moyenne) survit, sur **une** paire, avec **11 trades** de hold-out |
| **s12 — momentum MACD D1 indices** | PAS D'EDGE | −0,006 R/t à spread nul, percentile 51,5 ; sur 99 ans, les jours en position font +0,8 %/an contre +6,4 % au buy & hold |

Et l'hypothèse « il faut monter en timeframe » a été réfutée séparément :
**S1 en H4 = 0/11 paires**, AUDCHF et EURUSD compris — les deux qui passent en
H1. Diviser le péage par deux n'aide ni la stratégie qui échoue, ni celle qui
marche.

> **Les seules poches positives jamais mesurées sur ce dépôt sont des retours à
> la moyenne.** Le régime demandé est celui qui a été réfuté quatre fois.

### F.2 Ce qui est atteignable : la cadence vient de la LARGEUR, pas de la tendance

La cadence demandée — 1 à 10 trades/semaine — est fournie par le nombre
d'instruments, pas par la nature du signal. Mesure, dérivée des tranches OOS de
`config_walkforward_v4` (3 tranches de 185 jours, soit 79,3 semaines) :

| Univers | Trades OOS | Cadence mesurée |
|---|---|---|
| Livre complet, 8 admis (4 forex S1 + 3 indices + DAX/S2) | 180 | **2,27 / semaine** |
| Contrôle `portfolio_walkforward_v3` RUN 2, 11 candidats | 171 (sur 78,2 sem.) | **2,19 / semaine** |
| **Forex seul** (AUDCHF 24, EURUSD 7, AUDUSD 6, EURCHF 13) | **50** | **0,63 / semaine** |

Trois lectures, toutes désagréables et toutes utiles :

1. **Le livre complet tient la cadence demandée, en bas de fourchette** :
   2,2/semaine, contre 1-10 demandés. Le haut de la fourchette exigerait ~5× la
   largeur actuelle.
2. **Le livre forex seul ne l'atteint pas** : 0,63/semaine, sous le plancher de
   1. Le catalogue compte 13 paires forex contre 4 admises ici ; les élargir
   toutes donnerait au mieux ~2/semaine — et seulement si chacune passait le
   filtre Tier-1 et portait un edge, ce que **v5 dément** (la sélection
   d'instruments est le plus gros biais mesuré du dépôt : **+1314 CHF**).
3. **Le swing par la DURÉE existe déjà** : les positions S1 en H1 sont tenues
   2 à 4 jours (`config_walkforward_v4` §limitation 6). Ce qui n'existe pas,
   c'est le swing par la **tendance**.

> Adrian demande du swing. Il en a déjà — mais pas celui qu'il croit : la durée
> de détention est bien celle du swing, la logique reste le retour à la moyenne.

### F.3 Un coût non modélisé que le régime swing rend saillant

Des positions tenues 2 à 4 jours paient un **swap** réel. Il n'est modélisé
nulle part : `config_walkforward_v4` §limitation 6 — « NO slippage, NO
swap/rollover, NO commission ». Tout chiffre swing du dépôt est optimiste d'un
montant **inconnu**. À chiffrer avant, pas après.

---

## G. L'ordre des opérations

Principe de tri, en une ligne : **ce qui est prospectif démarre maintenant (le
temps perdu ne se rattrape pas) ; ce qui est rétrospectif attend sans coût (les
barres ne s'effacent pas).**

| # | Action | Quand | Dépendances | POURQUOI ce rang |
|---|---|---|---|---|
| **1** | **Armer le bras de référence A0** — le portefeuille forward scellé déjà inscrit au `TODO.md` | **maintenant** | aucune (v4/v5 dépouillés) | C'est le seul compteur qui **ne se rattrape pas**. Sans lui, aucun conseil ne sera jamais attribuable, et la calibration n'aura pas de dénominateur. Chaque semaine sans A0 est perdue définitivement |
| **2** | **Étude de sortie** (§E) : ticket moteur `core/` + protocole gelé + mesure sur S1 et `s13` | **maintenant, en parallèle** | capacité moteur (E.1) | Entièrement rétrospective, donc rejouable — mais c'est la seule partie du mandat qui puisse rendre un verdict cette année. Ne dépend d'aucun pilier |
| **3** | **Verdict sentiment** (`s14` F1) | **2026-10-17 au plus tôt** ; lecture finale obligatoire **2027-02-17** | 150 verdicts **comptables** ≥ 0,8 **et** 60 jours | Rien à faire d'ici là : le protocole interdit de lire avant F1. Si PAS DE VALEUR → le pilier sort du score, et c'est un degré de liberté en moins, pas une perte |
| **4** | **Décision Adrian sur `s15` (COT)** | **à trancher, pas à attendre** | — | L'étude est en suspens faute d'épisodes (2-9 contre 12). Trois sorties, aucune n'est « attendre » : **(a)** instruire la famille B (impulsion) et la sonde `q=0,10` si les épisodes y sont ; **(b)** collecter le **TFF** (*Leveraged Funds*) — la seule **donnée nouvelle** qui justifie un second dossier scellé, au lieu de relire les mêmes barres (règle de clôture s90) ; **(c)** clore le motif. Le seul levier sur les épisodes est le temps : 52 occasions/an/instrument |
| **5** | **Marchés prédictifs — étude d'existence** (§A.3b) | après 1 et 2 | aucune | Trois questions à répondre **avant** tout protocole : historique téléchargeable ? redondance avec les futures Fed funds ? latence de re-cotation ? Si pas d'historique : décider d'un archivage append-only, dont la première lecture est à **+12 mois** |
| **6** | **Ré-instruire l'avis de Claude sur un socle VIVANT** | après 1 (A0 fournit le flux) | A0 en production, ≥ 40 décisions | Le verdict actuel est « ne pas armer sur s12 », pas « impossible » : la question n'a jamais été posée sur un flux à espérance ≥ 0. L'infrastructure se rebranche telle quelle (`macd_ai_paper` §5) |
| **7** | **Sceller l'étude de combinaison** | **conditionnel, pas avant 2027** | voir §G.1 | §B.3 |
| **8** | **Première lecture de calibration** | **≈ 18-24 mois** après le démarrage du bras A4, à 2 tranches | §C.4 | Arithmétique, pas prudence |

### G.1 La condition de scellement de la combinaison — écrite d'avance

> Le scellé de s16 ne peut être posé que lorsque **au moins 2 des 3 conseils ont
> un verdict RENDU** — `VALEUR CANDIDATE` ou `PAS DE VALEUR`, pas « en cours ».
> Un conseil au verdict `PAS DE VALEUR` **sort du score** : ce n'est pas une
> perte, c'est un degré de liberté en moins (§B.1).

Trois corollaires :

1. si les trois conseils rendent `PAS DE VALEUR`, **s16 se ferme sans avoir été
   scellée** — et A0 continue de tourner, parce qu'il est la stratégie, pas le
   conseil ;
2. si un seul conseil survit, il n'y a pas de « combinaison » : il y a un
   **filtre**, à mesurer contre A0 par le motif à deux bras déjà éprouvé, sans
   pondération ni score. La combinaison n'est justifiée qu'à partir de deux
   survivants ;
3. le nombre de tranches de confiance (≤ 3) et l'événement calibré (§C.2) sont
   figés **au moment du scellé**, jamais après avoir vu une confiance produite.

### G.2 Dépendances, en clair

```
A0 (bras de référence, prospectif)  ─┬─> calibration (dénominateur + SHADOW)
                                     ├─> ré-instruction avis Claude (socle vivant)
                                     └─> attribution de tout conseil

s14 F1 (2026-10-17+)  ─┐
s15 décision Adrian   ─┼─> >= 2 verdicts RENDUS ─> scellé s16 (2027+)
marchés prédictifs    ─┘

étude de sortie (§E) ── indépendante de tout ce qui précède ──> verdict possible en 2026
```

---

## H. Ce que ce dossier ne fera PAS

- Aucun backtest, aucun chiffre de résultat, tant qu'aucun protocole n'est gelé.
- Aucun score construit avant que la condition §G.1 soit remplie.
- Aucune pondération ajustée sur des résultats observés.
- Aucun usage de l'avis de Claude au-delà de **prendre / ne pas prendre** —
  ni taille, ni stop, ni cible (mesures §A.4).
- Aucun compte, aucun capital, aucun ordre sur Polymarket, Kalshi ou toute autre
  place prédictive : **lecture seule**, conformément au mandat.
- Aucune modification de `core/`, `server/`, `orchestrator/`, ni d'une autre
  stratégie ou étude. En particulier : `core/data/cot.py` et les protocoles
  scellés de `s14`, `s15`, `macd_ai_paper`, `gold_forward`, `s13_forward` sont
  **en lecture seule** ici.
- Aucune promotion PAPER ou LIVE — **R10**, décision d'Adrian et de personne
  d'autre.

---

## I. Angles morts assumés, notés avant toute mesure

1. **Un seul régime macro.** L'échantillon du dépôt couvre 2021-2026 : pas de
   krach. C'est la limite la plus grave (`docs/METHODOLOGY.md` §9), et elle
   affecte les quatre piliers simultanément.
2. **Corrélation entre bras et entre instruments.** Les positions simultanées du
   livre partagent leurs moteurs macro ; les IC binomiaux de la calibration
   surestiment l'indépendance. Aucune correction n'est prétendue.
3. **Le biais de conception de la grille reste non mesuré** (v4 §limitation 2).
   Il est plausiblement plus grand que les deux biais déjà chiffrés
   (config +98, instruments +1314).
4. **Swap et slippage non modélisés** (§F.3), et le régime swing les rend
   saillants.
5. **Les révisions silencieuses de la CFTC** contaminent tout échantillon COT
   rétrospectif, et aucun falsifieur rétrospectif ne peut les attraper
   (`s15/ANALYSIS.md` §9.1).
6. **Le juge IA est un composant non stationnaire** : le modèle sous-jacent
   change de version. `s14` a tranché en épinglant le modèle dans le champ
   `reason` et **jamais** dans la colonne `judge` (qui porte les curseurs et
   l'appariement) — sinon chaque montée de version remettrait F1 à zéro. La même
   convention devra valoir ici.
7. **Le taux de base du dépôt est négatif** : 13+ verdicts, 0 stratégie de
   production. Ce n'est pas du pessimisme, c'est l'antériorité — et c'est le
   taux auquel toute attente sur s16 doit être ancrée.

---

## J. Ce qui est figé où

| Objet | Où | État |
|---|---|---|
| Ce cadrage | `research/ANALYSIS.md` (ce fichier) | **non scellé** — révisable tant qu'aucun protocole n'est gelé |
| Protocole de combinaison | `research/FALSIFICATION.md` | **n'existe pas** — condition de création : §G.1 |
| Étude de sortie | dossier autonome (`s17` proposé) | **à ouvrir** — indépendante |
| Champ `conseil:` | `manifest.yaml` (R7) | déclaré ; sémantique figée au scellé |
| Bras de référence A0 | `TODO.md` — portfolio forward scellé | **à armer en premier** |

Aucun chiffre de résultat n'existe au moment où ce document est écrit.

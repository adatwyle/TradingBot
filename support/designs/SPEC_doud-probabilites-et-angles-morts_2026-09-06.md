---
name: doud-probabilites-et-angles-morts
date: 2026-09-06
version: 1.0.0
type: spec
status: draft
author: cc-support
target_scope: projet tradingBot — branche v2/gold
applies_to: [strategies/S019 (à créer), core/data, core/backtest, core/risk, studies/s14_sentiment]
sources:
  - docs/sources/doudtrading/ (35 lives, 54 h, 68 984 segments)
  - docs/sources/moneytalk/ (2 podcasts, 5 788 segments)
  - métadonnées publiques Discord + TikTok (2026-09-06)
complements: SPEC_methode-doud-reconstruite_2026-09-06.md
---

# Doud — ses calculs de probabilité, sa mécanique d'entrée, et ce qu'elle ne dit pas

Cinq passes de lecture sur **74 772 segments** (35 lives + 2 podcasts), avec une
lentille différente à chaque passe. Ce document complète
`SPEC_methode-doud-reconstruite_2026-09-06.md` : celui-là décrivait *quoi* elle
fait, celui-ci décrit *sur quoi elle fonde ses décisions*, et surtout **ce qui
manque pour la reproduire**.

---

## 0. Méthode d'extraction, et une mesure qui a échoué

| Passe | Lentille | Bruts | Retenus |
|---|---|---:|---:|
| P1 | « probabilité / probable / proba » | 245 | 166 |
| P2 | chiffres de chance (%, chances sur, fractions) | 282 | 181 |
| P3 | vocabulaire de calcul (« ça se calcule », « je calcule ») | 102 | 76 |
| P4 | structures conditionnelles (« si… alors on ira ») | 19 | 19 |
| P5 | météo / anticipation / scénario / statistique | 176 | 139 |

**Une mesure a été tentée et rejetée.** J'ai voulu quantifier l'asymétrie
gain/perte en extrayant automatiquement les montants cités. Le résultat
(médiane gain 180 $ contre médiane perte 270 $) est **faux** : la régex mélange
trois populations incompatibles — le P&L *flottant* annoncé en cours de trade
(« actuellement je suis à −63 dollars »), le risque *hypothétique* d'une annonce
(« sur un lot de 1 tu perds 3000 dollars ») et les résultats *réalisés*. Aucune
de ces trois n'est distinguable à la régex. **Le chiffre n'est pas publié**, et
l'asymétrie reste au statut d'observation qualitative (§ 1.4). C'est le genre de
mesure qui aurait l'air rigoureuse et qui serait de la décoration.

---

## 1. Ses calculs de probabilité — la découverte centrale

### 1.1 Elle publie une distribution directionnelle chiffrée, avant chaque annonce

Extraction exhaustive des couples `NN % + direction` sur le corpus complet :

| Valeur annoncée | Occurrences |
|---|---|
| **65 % hausse** | 7 |
| 60 % hausse | 2 |
| 65 % baisse | 1 |
| 60 % baisse | 1 |
| 40 % hausse | 1 |
| 35 / 40 % baisse | 3 |
| 15 / 20 % baisse | 3 |

> *« mes prévisions annonce probable sur l'inscription hebdomadaire au chômage :
> il y a **65 % de hausse** sur le gold »* — `Cc1Meko5FhA @006:37`
> *« nous sommes sur du **60-65 % de hausse contre 35-40 % de baisse** »* — `G7LP5bb6UhU @014:24`
> *« scénario haussier de **65 %**, scénario baissier de **35 %** »* — `JtD2bifO96Y @001:34`
> *« j'ai **65 % de baisse contre 35 de hausse**. Ça c'est la première probabilité »* — `QbkYJMzeodI @036:22`
> *« ma probabilité de hausse, elle est de **70 %** »* — `a__0t9kh88w @013:33`

**Régularité remarquable** : son côté favori est **toujours entre 60 et 70 %**,
jamais 50/50, jamais 90/10. C'est une bande étroite et disciplinée — le signe
d'une méthode, pas d'une humeur.

Et une fois, elle publie une distribution **à trois branches** :

> *« en probabilité : **65 % de hausse, 20 % de mouvement brusque, 15 % de
> baisse** »* — `Cc1Meko5FhA @019:52`

La branche « mouvement brusque » (le spike bidirectionnel d'annonce) est traitée
comme un état distinct, ni haussier ni baissier. C'est exactement la structure
d'un événement de publication, et aucune stratégie du dépôt ne modélise ça.

### 1.2 L'échelle d'amplitude, par classe d'événement

Le second terme de son calcul est une **magnitude en points**, stable par type
d'événement (son « point » = 0,01 $, soit notre pip — cf. § 4.1) :

| Événement | Amplitude annoncée | En ATR H1 (médian 572 pips) |
|---|---|---|
| Annonce standard (jobless claims, CPI) | **3 000 points** | ≈ 5 ATR |
| NFP | **6 000 - 7 000 points** | ≈ 10-12 ATR |
| Journée complète | **12 000 points** | ≈ 21 ATR |
| Semaine (météo du dimanche) | **15 000 - 20 000 points** | ≈ 26-35 ATR |

> *« on sait qu'on a une probabilité de **3 000 points** sur le gold »* — `DcdjhCnP-Tw @005:24`
> *« on a une probabilité de perdre ou de gagner à peu près **6 000 points** »* — `a__0t9kh88w @009:11`
> *« s'il vient chuter ici, on a une probabilité de perte de **12 000 points**.
> C'est ce qu'il fait à peu près sur une journée, le gold »* — `LTN-S3DC5Fg @013:37`
> *« au NFP, on avait une probabilité de perdre de **15 à 20 000 points**. Le gold
> a chuté de 20 000, 22 000 »* — `QbkYJMzeodI @043:38`

Ces amplitudes servent **au dimensionnement, pas à la direction** :
> *« vous savez qu'il faut **calculer vos lots en fonction de cette
> probabilité**. Si je perds, je perds sur un lot de 1 : 6 000 dollars »* — `a__0t9kh88w @010:35`

### 1.3 Le troisième terme : la branche adverse est une poche de liquidité

> *« les **35 % sont par rapport à la prise de liquidité de 6 000 points** »* — `JtD2bifO96Y @018:01`

Autrement dit, le scénario défavorable n'est pas abstrait : c'est un **niveau
identifié sur le graphique**, la poche de stops sous le prix. Elle sait où elle
perdrait, et de combien.

### 1.4 L'arithmétique — et pourquoi son edge n'est PAS dans la direction

Avec ses propres chiffres, l'espérance d'un trade d'annonce tenu jusqu'au bout :

```
EV = 0,65 × 3 000  −  0,35 × 6 000  =  1 950 − 2 100  =  −150 points
```

**Négative.** Une probabilité directionnelle de 65 % ne suffit pas quand la
branche adverse est deux fois plus grande que la branche favorable. Si sa
méthode consistait à prendre la direction et à attendre, elle perdrait.

Le terme qui renverse le signe est la **troncature de la branche adverse** par
la gestion de sortie — stop suiveur systématique, clôtures partielles
obligatoires, refus du break-even, coupe manuelle des perdants. Ses pertes
citées en direct se situent entre 168 et 500 $ sur lot 1 (soit 168 à 500 points),
là où le scénario adverse théorique vaut 6 000. Avec une branche adverse tronquée
à ~500 points :

```
EV = 0,65 × 3 000  −  0,35 × 500  =  1 950 − 175  =  +1 775 points
```

**Conclusion, et c'est la plus importante de tout le dossier** : *sa direction
n'est pas son edge — sa sortie l'est.* Les 60-70 % de probabilité directionnelle
ne sont qu'un billet d'entrée ; ce qui produit le résultat, c'est que la branche
gagnante court et que la branche perdante est coupée à un dixième de sa taille
théorique.

**Ce que ça implique pour nous, directement** : S018 mesurait l'entrée avec une
sortie fixe symétrique (TP 4 ATR / SL 1,5 ATR). Ce dispositif est structurellement
incapable de reproduire l'asymétrie qui fait sa performance. `TCK-014` n'est donc
pas un confort d'implémentation : **c'est la condition d'existence de la mesure**.

### 1.5 Comment obtient-elle ses 65 % ? — elle refuse de le dire

> *« ce serait **trop compliqué de vous partager comment je calcule mes
> pourcentages** sur le gold. Ça demande… ce n'est pas que dire comment on fait,
> il faut le faire voir »* — `KBqRb5_UJ8Y @011:55`

Mais deux indices ferment beaucoup de portes :

> *« sur l'annonce économique, **ce n'est pas par rapport aux données
> directement** »* — `KBqRb5_UJ8Y @007:07`
> *« je parle **juste d'analyse technique**. On a 65 % de hausse contre 35 % »* — `JtD2bifO96Y @018:01`

**Sa probabilité est technique, pas fondamentale.** Elle ne la dérive ni du
consensus, ni de l'écart consensus/réalisé, ni du sentiment de presse. Elle la
dérive de la structure de prix — H2 pour la tendance, position relative aux
poches de liquidité, historique du comportement de l'or sur ce type d'annonce.
C'est une excellente nouvelle pour l'automatisation : **cette information est
entièrement dans nos barres**.

---

## 2. Comment elle prévoit le prix d'entrée

Quatre briques, toutes visibles dans le corpus.

**a) La colonne de prix, son instrument de référence.**
> *« la **colonne de prix**, la seule qui ne ment pas. Les prix ne mentent
> jamais, les calculs ne mentent jamais. La colonne de prix, pour moi, c'est mon
> meilleur ami »* — `g0QZlUtQLvM @082:36`
> *« c'est **la colonne de prix ici qui va me donner mon point d'entrée** sur du
> scalping en impulsion. Et c'est ce qui va également me donner mon SL de
> sortie »* — `5IPouztc1_0 @010:33`

Elle lit une échelle de prix verticale (type DOM/ladder MT5), pas une figure.
**Le même objet donne l'entrée ET le stop** — les deux sont des niveaux, pas des
distances.

**b) L'équilibre du fair value gap.**
> *« tu prends ton fair value gap et tu décides de le calculer : on est sur un
> équilibre »* — `WkEOUOhq6FU @024:15`
> *« sur les 4998 57, nous sommes sur l'équilibre du fair value gap, et donc il
> faut **attendre une prise de liquidité** »* — `JtD2bifO96Y @046:10`

Le niveau candidat est le **milieu d'un déséquilibre M15**. Codable : trois
bougies, gap entre la mèche haute de la 1re et la mèche basse de la 3e, milieu du
gap.

**c) Les poches de liquidité, mesurées en points.**
> *« on est ici à une **prise de liquidité de 2 000 points** »* — `KBqRb5_UJ8Y @023:33`
> *« cette plus grosse liquidité, elle est là. C'est pour ça que **la zone en
> jaune est épaisse** : parce que je sais la prise de liquidité »* — `cvpayfkumYs @065:00`

L'épaisseur de sa zone est **proportionnelle à la liquidité attendue**. Codable :
amas de plus-bas/plus-hauts locaux non encore balayés, pondérés par leur
récurrence.

**d) Le refus des prix intermédiaires.**
> *« les **prix intermédiaires**, c'est là où c'est **le plus risqué**. Si tu
> vends là alors qu'il rebondit, **ton point d'entrée il est pourri** »* — `JtD2bifO96Y @046:10`

Elle n'entre qu'aux extrémités de structure. C'est la règle qui invalide
définitivement la traduction « entrée à 50 % de la jambe » de S018.

---

## 3. Comment elle rentre au meilleur moment

**L'horloge, à la minute.** Pour une publication à 14h30 : *« on attend 28 »*
(`G7LP5bb6UhU @028:21`, `@031:56` — « il reste 28 secondes, on attend »),
*« j'attends 28, tant qu'il n'est pas 28 je ne me positionne pas »*
(`KBqRb5_UJ8Y @028:13`), *« le point d'entrée ne se fait pas avant 27 »*
(`LTN-S3DC5Fg @011:53`). Donc **T−2 à T−3 minutes**, jamais pendant, et
*« 5 minutes avant, 5 minutes après »* comme fenêtre large (`1kVYJ160yOI @032:39`).

**La clôture de bougie comme validation.** Le décompte *« il reste 3 minutes sur
la M15 »* revient dans presque tous les lives ; *« il faut qu'il clôture en
M15 »* (`WkEOUOhq6FU @058:27`). Une mèche qui perce ne déclenche rien — seule
une **clôture** au-delà vaut signal (« impulsion » vs « structure »).

**Le balayage comme déclencheur.** Elle n'achète pas la force, elle achète le
retour après que les stops ont été pris : *« il est venu chercher les stop loss,
il est remonté, il a stoppé, il a ressorti plus bas et il est parti en
impulsion »* (`5HoIRmOBSvM @070:34`), *« plus il chute, plus on a le point
d'entrée pour acheter »* (`5IPouztc1_0 @010:33`).

**Et le refus explicite de la sur-confirmation** — c'est sa signature :
> *« tu imagines, les gens qui vont attendre une confirmation supplémentaire,
> genre un drapeau qui va te dire "tu peux rentrer"… **mais tu ne rentres
> jamais** »* — `5IPouztc1_0 @086:16`
> *« ils ont loupé toute la montée. Ils sont encore à 17h sur les graphiques »* — `LTN-S3DC5Fg @046:42`

Sa réponse au dilemme confirmation/retard : **la confirmation vient du niveau
préparé à l'avance, pas d'un signal supplémentaire au moment d'entrer.** Le
travail est fait avant ; l'entrée est mécanique.

---

## 4. Ce qui n'a pas été demandé et qui change des choses

### 4.1 Réconciliation d'unités — son « point » n'est pas notre pip

Elle martèle : *« je calcule en point, pas en pips. Ceux qui sont là à calculer
leur pip sur le gold, vous n'avez rien compris »* (`KiGK6ydHfK4 @018:11`,
`YEfywiIYSfQ @054:21`). Vérification par ses propres équivalences : *« 500 points
= 500 dollars »* sur lot 1 (`5IPouztc1_0 @023:34`), *« 3 000 points → 3 000 $ de
perte sur lot 1 »* (`QbkYJMzeodI @038:34`).

Sur 100 oz (1 lot standard), 1 $ par point ⇒ **1 point Doud = 0,01 $ = notre
pip**. Ses 3 000 points = un mouvement de **30 $** sur l'once. Toutes ses
amplitudes sont donc directement convertibles dans notre échelle — et c'est ce
qui rend le § 1.2 exploitable.

*Note* : le broker, lui, cote XAUUSD en `digits=3` (`point = 0,001`). Les trois
échelles coexistent dans nos données ; toute confusion multiplie ou divise les
résultats par 10.

### 4.2 Sa comptabilité R:R est mensuelle, pas journalière

> *« notre R:R en scalping, moi **je le calcule sur le mois**, combien j'ai fait
> de R:R sur le mois »* — `EdZNDaz1rkY @053:08`
> *« quand je calcule, je calcule **sur la semaine complète** »* — `QbkYJMzeodI @052:22`

Ses ratios de 7 à 17 ne sont donc pas tous des ratios de trade. Une partie est un
**agrégat de période**. Cela affaiblit la lecture « elle vise 7 R par trade » et
renforce la lecture « son mois cumule 7 à 17 R ». À garder pour tout benchmark.

### 4.3 D'où vient le « 90 % de réussite »

> *« ça se calcule, les pourcentages : on est à **90 de taux de réussite**,
> **ce n'est pas moi qui le dis, c'est le copieur** »* — `qu5zZhgAg5M @011:34`
> *« je suis déjà monté à **93 %**. Le 100 % n'existe pas, parce que dans cette
> façon de trader **je calcule mes pertes** »* — `EdZNDaz1rkY @051:59`

Le chiffre vient d'une **plateforme de copy-trading**, pas d'elle. C'est plus
crédible qu'une auto-déclaration — et toujours invérifiable de notre côté.

### 4.4 Règles de vie qui sont en réalité des règles de trading

- **Jamais 24 h avant une décision de taux** (`5HoIRmOBSvM @003:07`) — un filtre
  calendaire de plus, distinct de la fenêtre d'annonce.
- **Pas de live le mercredi** — *« c'est la journée des enfants »*
  (`KBqRb5_UJ8Y @039:44`). Une absence hebdomadaire structurelle.
- **Fin de mois plus prudente** : *« j'en prends beaucoup au début de mois, et
  puis après je me mets sur prop firm »* (`LTN-S3DC5Fg @019:42`) — saisonnalité
  intra-mensuelle du risque.
- **Clôture de journée vers 16h** (`5IPouztc1_0 @113:55`) et *« 15h30, on prend
  nos gains »* (`1kVYJ160yOI @080:58`).
- **Scénario invalidé ⇒ sortie**, même sans stop : *« si mon scénario est
  invalidé et que j'arrive au montant que je me suis fixé, je ferme mes
  positions »* (`LTN-S3DC5Fg @018:14`). C'est un **stop mental à double
  condition** (structure ET montant) — la seule forme de risk management qui
  remplace, chez elle, le stop technique.

### 4.5 Le filtre de spread, jamais mentionné dans le podcast

> *« le spread est beaucoup trop élevé là. **On doit attendre un spread beaucoup
> plus serré** »* — `5HoIRmOBSvM @014:13`

Elle refuse d'entrer quand le spread s'écarte. C'est une règle d'exécution que
nous pouvons coder immédiatement — et qui rejoint `TCK-018` (notre catalogue
sous-estime le spread XAUUSD d'un facteur 2).

---

## 5. finbert — réponse revue, et cette fois tranchée

Réponse précédente : *non, 19 jours de données contre un backtest de 5 ans*.
Elle reste vraie. Mais le corpus ajoute un argument plus fort, et il est
définitif :

**Sa probabilité n'est pas fondamentale.** *« Ce n'est pas par rapport aux
données directement »* (`KBqRb5_UJ8Y @007:07`), *« je parle juste d'analyse
technique »* (`JtD2bifO96Y @018:01`). Le sentiment de presse — ce que mesurent
finbert et claude-cli dans `studies/s14_sentiment` — **n'est pas l'entrée de son
calcul**. Brancher finbert sur une reconstruction de sa méthode ajouterait une
variable qu'elle n'utilise pas.

**Ce qui la remplace** : l'événement *programmé* (le calendrier, `TCK-016`) et la
structure de prix. Les deux sont dans notre portée.

**finbert garde sa place ailleurs** : `s14_sentiment` mesure si un juge de
sentiment prédit le mouvement — une question légitime, indépendante de Doud, et
qui sera lisible vers **mi-octobre 2026** (son protocole exige 150 verdicts et
60 jours par juge ; on est à 18 jours). À ce moment-là, une étude « sentiment ×
or » aura du sens. Pas avant, et pas dans ce dossier.

---

## 6. Une session Claude Code headless à sa place — ce que ça donnerait vraiment

**Ce qui est remplaçable, et l'est déjà mieux par du code que par un LLM** :
l'horloge (T−2 min), la détection de balayage/rejet, le calcul des niveaux FVG,
la lecture du spread, le dimensionnement, la remontée du stop suiveur, les
clôtures partielles. Ce sont des règles déterministes : une session Claude n'y
apporte rien qu'une fonction Python ne fasse mieux, plus vite et sans coût.

**Ce qui semble appeler un LLM** : le jugement de contexte — *« aujourd'hui le
marché est piégeur »*, *« je ne travaille pas 24 h avant les taux »*, *« je ne
rentre pas en lot de 1 cette semaine, trop imprévisible »*. C'est là qu'un
raisonnement en langage naturel sur l'actualité pourrait, en principe, produire
la couche qu'elle appelle son biais.

**Mais l'architecture correcte n'est pas « Claude devant l'écran ».** Trois
raisons :

1. **La latence.** Son entrée se joue à la seconde sur M1, à T−2 min d'une
   publication. Une session headless qui raisonne met plusieurs secondes à
   plusieurs dizaines de secondes. Elle-même se plaint constamment de la latence
   YouTube qui décale ses membres — c'est le même problème, en pire.
2. **La reproductibilité.** R1 (causalité) et R5 (conformance backtest/live)
   exigent qu'une décision soit **rejouable à l'identique**. Un LLM dans la
   boucle de décision casse les deux : on ne peut ni backtester ni prouver qu'on
   n'a pas triché.
3. **Le précédent interne.** `S093_alexg_ai_judge` a déjà exploré exactement
   ça — un juge IA en aveugle sur des candidats mécaniques. C'est la bonne forme :
   **le LLM juge en amont, il n'exécute pas.**

**L'architecture que je proposerais** : une session headless **quotidienne, hors
marché** (le dimanche, comme sa météo), qui produit un **artefact figé et daté** —
biais directionnel H2, probabilité en %, niveaux de liquidité, événements de la
semaine, éventuelles interdictions (J−1 taux). L'exécution intraday reste 100 %
déterministe et ne lit que cet artefact. Ça préserve R1/R5 (l'artefact est daté,
donc rejouable), ça met le LLM là où il est bon (la synthèse de contexte), et ça
le tient hors de la boucle temps réel où il est mauvais.

C'est, incidemment, **exactement la structure de sa propre semaine** : une météo
le dimanche, une exécution mécanique du lundi au vendredi.

---

## 7. Ce qui reste caché — l'inventaire honnête

Ce qu'elle **ne dit pas**, classé par ce que ça nous coûte.

| # | Ce qui manque | Ce qu'elle en dit | Ce qu'il faut faire |
|---|---|---|---|
| **C1** | **La formule des 65 %** | *« trop compliqué à partager, il faut le faire voir »* | La **reconstruire par inversion** : ses forecasts sont datés dans les lives ; on peut scorer 65 %/35 % contre le mouvement réel sur nos barres et chercher quel modèle technique reproduit ses chiffres. C'est un problème d'apprentissage supervisé à petite échelle, avec ~20 observations — insuffisant seul (§ 8). |
| **C2** | **La règle exacte du stop suiveur** | *« tu le montes au niveau supérieur, mais pas trop près »* | À **inventer et calibrer** : trailing par palier de structure (dernier plus-bas M1/M5 significatif) vs trailing ATR. Deux variantes à mesurer une fois `TCK-014` livré. |
| **C3** | **Les seuils de clôture partielle** | ferme « une », puis « une », sur niveaux ou sur montant | À **tester** : fractions (1/3, 1/3, 1/3 ou 2/4 puis runner) × déclencheurs (niveau de structure vs multiple de R). |
| **C4** | **La construction des zones** | zones colorées tracées à la main, épaisseur « proportionnelle à la liquidité » | À **créer** : détection FVG M15 + amas de plus-hauts/bas non balayés. Sa main est remplaçable par une règle, mais la règle est à écrire. |
| **C5** | **Le montant du « stop mental »** | *« quand j'arrive au montant que je me suis fixé »* — jamais chiffré | À **fixer nous-mêmes** : c'est un paramètre de `core/risk/`, pas une inconnue de sa méthode. |
| **C6** | **Sa sélection de setups** | elle refuse la majorité des occasions (*« aujourd'hui la mise est d'attente »*) sans critère explicite | **Le trou le plus profond.** Son taux de refus est invisible : on voit ses trades, pas ceux qu'elle n'a pas pris. Un backtest qui prend tous les signaux mécaniques n'est pas sa méthode. |
| **C7** | **Ses résultats vérifiables** | rien d'auditable | Hors de portée, et **pas nécessaire** : on ne cherche pas à valider ses chiffres, on cherche à mesurer les nôtres. |

### C6 mérite d'être développé — c'est le biais de sélection

Sur 54 heures de direct, elle passe **la majorité du temps à attendre**. Les
passages « on attend », « aujourd'hui la mise est d'attente », « il n'y a pas de
volume, on attend » sont omniprésents. Sa performance n'est donc pas celle d'une
règle mécanique : c'est celle d'une règle mécanique **plus un filtre de refus
discrétionnaire** dont nous n'avons aucune trace exploitable.

**Conséquence méthodologique** : même parfaitement reconstruite, notre version
prendra plus de trades qu'elle, dont une part qu'elle aurait refusés. Notre
mesure sera donc **structurellement pessimiste** par rapport à sa pratique — ce
qui est préférable au biais inverse, mais doit être écrit dans le protocole
avant la première mesure.

---

## 8. « Atteindre un niveau similaire » — ce que ça demande vraiment

L'objectif d'Adrian est explicite. Voici ce qu'il suppose, sans complaisance.

**Ce qui est à notre portée, et rapidement** : l'horloge, les niveaux, le
balayage, le filtre de spread, le dimensionnement, la discipline. Tout le
squelette mécanique de sa méthode est codable avec ce que nous avons ou pouvons
obtenir (M1, calendrier, moteur de sortie enrichi).

**Ce qui demande une invention, pas une transcription** : C1 (le modèle de
probabilité), C2/C3 (la géométrie de sortie), C4 (les zones). Ce sont quatre
briques à concevoir et calibrer nous-mêmes. Elles ne se déduisent pas du corpus ;
elles s'y **inspirent**.

**Ce qui ne sera pas égalé par construction** : C6, le refus discrétionnaire.
Cinq ans passés sur un seul instrument produisent un filtre que nous ne
reproduirons pas par règle. Notre compensation possible n'est pas d'imiter son
jugement, mais de **jouer sur un terrain où la machine est meilleure** : tester
mille variantes, mesurer sans ego, ne jamais dévier du plan, tourner 24 h sur 24
sur plusieurs instruments — quatre choses qu'elle ne peut pas faire.

**Le chemin réaliste**, dans l'ordre :
1. `TCK-018` (spread réel) — corrige tous nos chiffres, coût faible.
2. Données M1 + agrégation H2/M15/M1.
3. **S019, entrée seule** : balayage + rejet + clôture M15 + biais H2. Répond à
   *« son déclencheur a-t-il un edge ? »* — la seule question mesurable
   aujourd'hui.
4. `TCK-014` (sorties partielles + suiveur) **si et seulement si** l'étape 3 est
   positive. C'est là que se trouve, d'après le § 1.4, l'essentiel de son edge.
5. `TCK-016` (calendrier) — débloque l'horloge d'annonce.
6. Reconstruction du modèle de probabilité (C1), avec un dispositif de mesure
   dédié et un effectif suffisant.

---

## 9. Sources annexes — ce qui est atteignable, et par qui

| Source | État | Qui peut y accéder |
|---|---|---|
| YouTube — 35 lives, 54 h | **exploité** (`docs/sources/doudtrading/`) | fait |
| Podcasts MoneyTalk ×2 | **exploités** (`docs/sources/moneytalk/`) | fait |
| **Discord** — *🌕 Doud Trading 🌕*, **3 467 membres**, 245 en ligne | **inaccessible à moi** : créer un compte et accepter des conditions m'est interdit, et le serveur a une porte de vérification | **Adrian**. Et ça vaut le geste : c'est là qu'elle publie **la météo hebdomadaire, gratuitement** — soit un historique daté de ses prévisions 65 %/35 %. C'est le seul matériau qui permettrait de **scorer sa probabilité contre le mouvement réel** (§ C1) au lieu de la deviner. |
| **TikTok** `@doudtrading_` | accessible techniquement (15 vidéos listées) mais **faible valeur** : ce sont des remontages courts du podcast (mêmes thèmes : sophrologue, break-even, ego, impôts) | inutile d'insister |
| **Instagram** `@doudtrading` | mur de connexion | non exploitable sans compte |

**La demande concrète** : si tu rejoins le Discord et que tu exportes le canal
où elle poste la météo, on obtient un jeu de prévisions datées. Croisé avec nos
barres XAUUSD, ça transforme C1 d'« inconnue » en « mesure » — et ça répond à la
seule vraie question sur elle : *ses 65 % valent-ils mieux qu'une pièce ?*

---
name: methode-doud-reconstruite
date: 2026-09-06
version: 1.0.0
type: spec
status: draft
author: cc-support
target_scope: projet tradingBot — branche v2/gold
applies_to: [strategies/S018_gold_doud_v2, strategies/S019 (à créer), core/backtest, core/data, core/risk]
sources:
  - docs/sources/doudtrading/ (35 lives publics, 54 h, 68 984 segments)
  - docs/sources/moneytalk/ (MoneyTalk #29 et #30)
---

# Méthode Doud — reconstruction complète, et ce qu'il faudrait pour l'automatiser

**Objet.** Reconstituer, depuis 54 heures d'exécution filmée, la méthode réelle
de Cindy « Doud Trading » sur XAUUSD, sous une forme assez précise pour être
codée — puis établir, capacité par capacité, ce que TradingBot sait faire, ce
qu'il ne sait pas faire, et dans quel ordre combler l'écart.

**Ce document ne juge pas sa performance.** Aucun de ses chiffres n'est
auditable (cf. § 1.4). Il décrit un **système de décision** et évalue notre
capacité à le reproduire.

---

## 1. Base d'évidence

### 1.1 Le corpus, mesuré

35 transcriptions de lives publics, **2 922 420 caractères**, 69 088 lignes,
**54 heures** de direct sur XAUUSD. Séries : *jobless claims* du jeudi (14h30),
NFP, FOMC, discours de Powell, sessions asiatiques de nuit.

### 1.2 Le lexique, compté — ce qui structure vraiment sa pensée

| Concept | Occurrences | Lives concernés |
|---|---:|---:|
| zone | 911 | 35/35 |
| liquidité | 670 | 33/35 |
| annonce | 601 | 34/35 |
| impulsion | 496 | 34/35 |
| TP | 418 | 33/35 |
| point d'entrée | 402 | 33/35 |
| structure | 294 | 28/35 |
| SL / stop loss | 278 | 26/35 |
| **suiveur** | **242** | **20/35** |
| M15 | 173 | 31/35 |
| mèche | 145 | 29/35 |
| multiposition | 132 | 26/35 |
| partiel | 125 | 23/35 |
| renforcement | 122 | 23/35 |
| équilibre | 87 | 25/35 |
| H2 | 64 | 19/35 |
| M1 | 48 | 20/35 |
| fair value gap | 32 | 14/35 |
| break even | 15 | 7/35 |

**Lecture.** Son système est un système de **zones et de liquidité** (1 581
occurrences cumulées), pas un système d'« équilibre » (87). Le dossier S018
avait fait de l'équilibre son commutateur central : c'était une erreur de
pondération autant que de traduction. Et le mot `suiveur` (242) pèse deux fois
plus lourd que `mèche` : **la gestion de sortie est le cœur du dispositif**,
pas la lecture de chandelier.

### 1.3 Les nombres qu'elle cite

**Ratios R:R annoncés sur ses propres positions** — n = 24 : médiane **7,50**,
moyenne 8,85, min 1,92, max 17,0.
Distribution : `<2` → 1 · `2-4` → 2 · `4-8` → 9 · `8-15` → 8 · `≥15` → 4.
Sa propre référence : *« en général, un trader trade entre 1 et 1,5 de ratio »*
(`1kVYJ160yOI @018:32`).

**Amplitudes en points** (pip 0,01 → 1 000 points = 10 $) — n = 209 :
médiane **3 000**, Q1 1 200, Q3 6 000. Valeurs les plus citées : 3 000 (×25),
6 000 (×18), 10 000 (×14), 5 000 (×12).
Deux repères récurrents : **une annonce déplace l'or d'environ 3 000 points**
(30 $) et **une bougie M15 de NFP vaut environ 6 000 points** (60 $) —
*« sur un lot de 1, tu perds 6 000 dollars »* (`a__0t9kh88w @009:13`).

**Tailles** : lot 1 dominant (43 citations), puis 0,25 / 0,50 / 0,75 / 0,10 /
0,01 pour les paliers et clôtures partielles.

### 1.4 Ce que ces nombres ne prouvent pas

Elle annonce *« 31 TP pour 4 stop loss »* sur un mois de lives
(`NpesTgZ6KbQ @007:04`), et son site affiche 89 % de réussite. **Un taux de
réussite de 89 % coexistant avec un R:R médian de 7,5 est arithmétiquement
invraisemblable** : ce serait une espérance de +6,7 R par trade. La lecture
cohérente est mécanique, et elle est instructive : **le stop suiveur transforme
la majorité des trades en petits gains** (comptés comme « TP »), tandis que les
ratios de 7 à 17 ne concernent que les rares runners. Les deux chiffres sont
vrais séparément et décrivent deux populations différentes. C'est exactement ce
qu'un backtest à sortie unique ne peut pas reproduire.

---

## 2. La méthode, reconstituée en sept étages

### Étage 1 — Biais directionnel (H2, avant la séance)

> *« mes timeframes préférés : **H2 tendance globale, M15 zone de travail, M1
> point d'entrée**, précision sniper »* — `5HoIRmOBSvM @070:34`
> *« on analyse en H2, en M15, et on rentre en M1 »* — `g0QZlUtQLvM @048:48`
> *« quand on veut regarder le gold, on le regarde toujours en gros timeframe »* — `JtD2bifO96Y @008:16`
> *« la tendance globale, **on ne trade jamais contre-tendance** »* — `EdZNDaz1rkY @043:18`

Le biais est arrêté avant l'ouverture et publié le dimanche (« la météo »). Il
n'est pas structurellement haussier : *« moi, je suis vendeuse »*
(`NpesTgZ6KbQ @004:45`). Il conditionne **tout** l'aval : quand le marché part
à l'inverse, elle n'inverse pas, elle attend
(*« on laissera la main au vendeur et on attendra un setup acheteur »*).

**Codable** : porte de tendance H2 + interdiction de contre-tendance.
**Non codable** : la couche macro (dollar, Fed, géopolitique) qui alimente sa
lecture. Approximation honnête : structure de prix H2.

### Étage 2 — Zones de travail (M15, avant l'entrée)

Elle marque à l'avance des zones colorées et, surtout, des **poches de
liquidité** : les endroits où sont les stops des autres.

> *« regardez en H2, cette plus grosse liquidité, elle est là. C'est pour ça que
> la zone en jaune, elle est épaisse : parce que je sais la prise de liquidité »* — `cvpayfkumYs @065:00`
> *« on est ici à une prise de liquidité de 2 000 points »* — `KBqRb5_UJ8Y @023:33`
> *« M15, on est vraiment sur deux équilibres »* — `cvpayfkumYs @049:18`

Le mot `équilibre` désigne le **milieu d'un fair value gap** (32 occurrences de
FVG, 14/35 lives), pas le milieu d'un mouvement — et elle prévient que
*« les prix intermédiaires, c'est là où c'est le plus risqué »*
(`JtD2bifO96Y @046:10`).

**Codable** : détection de FVG en M15 ; plus-hauts/plus-bas locaux non balayés
(= poches de liquidité) ; largeur de zone proportionnelle à la liquidité
attendue.

### Étage 3 — Attente du balayage (le déclencheur)

C'est le cœur, et c'est l'inverse d'une entrée en cassure.

> *« il est venu chercher les stop loss, il est remonté, il a stoppé, il a
> ressorti plus bas et **il est parti en impulsion** »* — `5HoIRmOBSvM @070:34`
> *« **plus il chute, plus on a le point d'entrée** pour acheter le gold »* — `5IPouztc1_0 @010:33`
> *« il va juste venir **chasser les SL**. Voilà ce qu'il a l'habitude de faire »* — `G7LP5bb6UhU @072:44`
> *« on a même pas eu de DD parce qu'on a pris **sur mèche de rejet**. Zéro DD »* — `UugYUucNXlI @019:02`
> *« premier rebond, 2e, 3e, 4e rejeté, il est venu récupérer les stop loss »* — `UugYUucNXlI @006:05`

**Séquence formelle** : (a) prix entre dans la zone M15 ; (b) **balayage** d'un
plus-bas récent — les stops sont pris ; (c) **rejet** dans la même bougie ou la
suivante (mèche) ; (d) **réintégration** au-dessus du niveau balayé ;
(e) entrée en M1 sur l'impulsion, dans le sens du biais H2.

**Codable intégralement**, sur M1 ou M5, sans donnée exogène.

### Étage 4 — Validation en structure et clôture de bougie

Elle n'entre pas sur un prix qui touche : elle attend une **clôture**.

> *« il faut qu'il **clôture en M15** »* — `WkEOUOhq6FU @058:27`
> *« faut attendre **la clôture de la M15** »* — `qu5zZhgAg5M @159:16`
> *« tant qu'on ne passe pas **en structure**, le trade est dangereux »* — `1kVYJ160yOI @059:33`
> *« il a cassé le niveau **en impulsion** [...] mais il n'a pas breaké **en structure** »* — `5HoIRmOBSvM @070:03`

La distinction *impulsion* / *structure* est constante : une mèche qui perce ne
vaut rien, une **clôture** au-delà vaut signal. Le décompte du temps restant sur
la bougie M15 revient dans presque tous les lives (« il reste 3 minutes sur la
M15 »).

**Codable** : condition sur le **close** de la bougie M15, pas sur le high/low —
et c'est, incidemment, la lecture correcte de son « structure et non mèche »
que S018 avait traduite par un canal Donchian sur les corps.

### Étage 5 — Horloge des annonces

La règle la plus précise du corpus, répétée à l'identique dans au moins cinq
lives :

> *« **on attend 28** »* (pour une publication à 14h30) — `G7LP5bb6UhU @028:21, @031:56`
> *« **j'attends 28**, moi. Tant qu'il n'est pas 28, je ne me positionne pas »* — `KBqRb5_UJ8Y @028:13`
> *« le point d'entrée sur une annonce économique **ne se fait pas avant 27** »* — `LTN-S3DC5Fg @011:53`
> *« tu peux trader **5 minutes avant et 5 minutes après**, mais **tu ne peux pas trader pendant** »* — `1kVYJ160yOI @032:39`
> *« **je ne travaille jamais 24 h avant les taux d'intérêt** »* — `5HoIRmOBSvM @003:07`

Et la structure de la séance US, qu'elle énonce comme une horloge :

> *« ça fait 3 temps : annonce économique **14h30**, 2e temps **15h**, 3e temps
> **15h30**, et après on repart généralement vers 16-17h sur la hausse »* — `Cc1Meko5FhA @062:47`
> *« il va être 15h30 : **15h30, on prend nos gains** »* — `1kVYJ160yOI @080:58`
> *« il est 16h [...] pour moi ça s'arrête là, je clôture »* — `5IPouztc1_0 @113:55`

**Codable** — mais exige un calendrier économique (`TCK-016`). Sans lui, aucune
de ces règles n'est exprimable, et c'est le plus gros trou du dispositif actuel.

### Étage 6 — Entrée fractionnée

> *« mes premiers trades, je ne rentre pas avec mes lots initiaux. **Je trade
> 0,10**, je tâte le terrain »* — `9lp_5lvii3I @045:01`
> *« je rentre **en multiple de quatre**. Pourquoi ? Parce que **j'en ai
> toujours deux qui vont plus haut que les deux premiers. Les deux premiers me
> servent à sécuriser** »* — `9lp_5lvii3I @044:29`
> *« quand je rentre en multiple de trois, j'en ferme une, j'en ferme une, et
> après les autres, je les mets à suiveur »* — `1kVYJ160yOI @018:32`
> *« on ne rentre **jamais** avec ses gros lots sur ces niveaux-là »* — `5IPouztc1_0 @018:16`

Et le renforcement, conditionnel à la structure : *« s'il casse ce niveau-là, on
attendra un point plus bas et on **renforcera** beaucoup plus bas »*
(`Cc1Meko5FhA @020:56`).

**Position dans notre architecture** : c'est du **dimensionnement**, donc
`core/risk/` (R2) — une stratégie n'a pas le droit de le calculer. Mais le
*fractionnement de sortie* qui en découle est, lui, une propriété du trade que
le moteur doit savoir exécuter.

### Étage 7 — Sortie : le vrai moteur de la méthode

**Stop initial** : elle n'en pose pas hors annonce.
> *« Non, je ne mets pas de stop loss. Je mets [un SL suiveur] »* — `5IPouztc1_0 @079:07`
> *« les annonces économiques, c'est **le seul moment** où on met le SL serré,
> pour éviter une mèche qu'on n'aurait pas anticipée »* — `G7LP5bb6UhU @027:16`
> *« toutes les annonces économiques, il y a un stop loss. C'est le seul moment
> où je vous [le demande] »* — `JtD2bifO96Y @019:55`

**Stop suiveur** : systématique, obligatoire, remonté par paliers de structure.
> *« c'est le suiveur pour tout le monde, **obligatoire, non négociable** »* — `1kVYJ160yOI @021:58`
> *« **j'attends de casser en structure** ce niveau-là pour me mettre à SL suiveur »* — `G7LP5bb6UhU @042:02`
> *« dès qu'il a tapé le TP, tu montes ton SL suiveur au niveau supérieur.
> **Mais faut pas le coller trop près** »* — `1kVYJ160yOI @073:00`
> *« tu le montes à chaque fois que ton trade monte, parce que s'il se retourne,
> **tu finis quand même en gain** »* — `1kVYJ160yOI @070:05`

**Clôtures partielles** : obligatoires, sur niveaux ou sur montant.
> *« clôture partielle **obligatoire** la team, je ne rigole pas avec les
> clôtures partielles »* — `NpesTgZ6KbQ @066:26`
> *« je ferme la moitié. 0,50 »* — `1kVYJ160yOI @021:29`
> *« clôture partielle sur les niveaux des 4267 et des 4257 : ça fait un ratio
> de 4,84 »* — `1kVYJ160yOI @071:15`

**Break-even : refusé.**
> *« tu ne sors pas à break even, et **encore moins à perte** »* — `KBqRb5_UJ8Y @031:57`
> *« ceux qui sortent à break even, c'est ceux qui **ont peur du marché** »* — `KiGK6ydHfK4 @024:10`
> *« tu mets des SL et tu mets des BE, [et c'est pour ça que tu n'es pas rentable] »* — `5IPouztc1_0 @081:14`

Couper une perte reste sain : *« fermer ses pertes, ce n'est pas grave et ce
n'est pas une honte »* (`1kVYJ160yOI @009:18`).

**Filtre de spread** — passé inaperçu jusqu'ici, et directement exploitable :
> *« le spread est beaucoup trop élevé là. On doit attendre un spread beaucoup
> plus serré »* — `5HoIRmOBSvM @014:13`
> *« si tu rentres maintenant, tu vas rentrer qu'au 32. Faut attendre que le
> spread se colle »* — `5HoIRmOBSvM @018:13`

---

## 3. Le profil de trade qui en résulte

| Dimension | Sa méthode | S018 aujourd'hui |
|---|---|---|
| Unités de temps | H2 → M15 → M1, hiérarchisées | une seule, isolée |
| Déclencheur | balayage de liquidité + rejet + réintégration | cassure de canal |
| Validation | **clôture** de bougie M15 en structure | close > extrême décalé |
| Entrée | fractionnée (0,10 test, puis 3-4 unités) | une position |
| Stop initial | absent hors annonce ; serré en annonce | ATR × 1,5, toujours |
| Sortie | partielles + suiveur par paliers de structure | TP unique à 4 ATR |
| R:R | 1,9 à 17 (médiane 7,5), variable | 2,67 fixe |
| Horaires | horloge d'annonces + 3 temps US + clôture 16h | filtre horaire binaire |
| Filtre de coût | attend un spread serré | spread constant, jamais filtré |

**Conclusion structurelle** : deux des trois piliers de sa méthode — la cascade
de timeframes et la gestion de sortie — sont **absents** de notre moteur, pas
seulement de notre stratégie. Un backtest de son entrée seule, avec sortie
unique à R:R fixe, mesure au mieux un tiers du système.

---

## 4. Outils nécessaires — inventaire, avec l'état de tbot

### 4.1 Données

| Besoin | Pourquoi | État tbot |
|---|---|---|
| **M1 XAUUSD** ≥ 3 ans | son entrée se décide en M1 | **manquant** — le cache a H1/M15/M5 ; MT5 peut le fournir (`_TF` supporte M1 ? non : `M5, M15, H1, H4, D1`) → **ajout d'une constante nécessaire** |
| M15 + H2 alignés | zones et biais | M15 ✅ tiré ce jour ; **H2 absent** de `_TF` (H1 et H4 seulement) → agrégation depuis H1 |
| **Calendrier économique** (date, heure, importance) | toute l'horloge de l'étage 5 | **manquant** — `TCK-016` |
| **Spread historique par barre** | son filtre de spread, et notre coût réel | **présent mais inexploité, et le scalaire de catalogue est faux d'un facteur 2** : médiane mesurée 50-58 pips selon le timeframe contre 25 déclarés, y compris aux heures actives. Corrigé, l'edge H1 passe de +0,236 à +0,205 R/trade et le M15 de −0,096 à −0,150. Détail et impact : `TCK-018` |
| Tick / carnet | non requis par sa méthode | sans objet (`real_volume = 0`) |

### 4.2 Moteur d'exécution

| Capacité | Pourquoi | État tbot |
|---|---|---|
| **Sorties partielles** (N fractions, niveaux distincts) | étage 7, obligatoire chez elle | **manquant** — `TCK-014` |
| **Stop suiveur** par paliers de structure | c'est ce qui produit ses R:R 7-17 | **manquant** — `TCK-014` |
| Stop initial **optionnel** | elle n'en pose pas hors annonce | **impossible** — R3 impose `Signal.stop`. Substitut admissible : stop large « structurel » + suiveur |
| Position multiple sur un même signal | entrée fractionnée | `max_positions` existe mais gère des signaux distincts, pas un signal fractionné |
| **Spread variable par barre** | son filtre, et l'honnêteté du coût | **manquant** — `InstrumentSpec.spread_pips` est scalaire |
| Sortie à heure fixe (15h30, 16h) | ses trois temps | `max_hold_bars` existe (en barres, pas en heure d'horloge) |

### 4.3 Couche stratégie

| Capacité | État |
|---|---|
| Multi-timeframe dans `precompute` | **à construire** — le contrat passe un seul `df` ; l'agrégation M1→M15→H2 doit se faire dans la stratégie, causalement (resample + shift) |
| Détection de fair value gap | à écrire (~30 lignes, causal) |
| Détection balayage + rejet + réintégration | à écrire (~40 lignes, causal) |
| Porte de tendance HTF | **existe déjà** dans S018 (`_daily_bias`), à généraliser en H2 |

### 4.4 Couche risque

| Capacité | Pourquoi | État |
|---|---|---|
| Fractionnement d'entrée (0,10 test → paliers) | étage 6 | à spécifier dans `core/risk/` (R2) |
| Arrêt de journée sur objectif | *« 15h30 on prend nos gains »* | **manquant** — `TCK-015` |
| Interdiction de trader J−1 avant décision de taux | règle explicite | dépend du calendrier (`TCK-016`) |

---

## 5. Ce qu'il faut construire, dans l'ordre

L'ordre n'est pas arbitraire : chaque étape est choisie pour **maximiser ce
qu'on apprend par unité de travail**, et pour qu'un échec précoce évite le
travail suivant.

**Étape 1 — Données M1 + agrégation H2.** Tirer M1 sur 3 ans, vérifier le volume
et les trous, ajouter `M1` au dictionnaire `_TF`, écrire l'agrégation causale
M1 → M15 → H2. *Sans données, rien de la suite n'existe.* Coût : faible.
Verrou levé : aucun, mais tout en dépend.

**Étape 2 — S019, l'entrée seule.** Balayage + rejet + réintégration + clôture
M15 en structure + porte H2, avec la sortie que le moteur sait faire (SL/TP
fixes). Grille minimale (≤ 8 cellules), cellule neutre = entrée aléatoire dans
la même zone. *Question posée : **son déclencheur a-t-il un edge, indépendamment
de sa gestion ?*** C'est la seule question que notre moteur sait poser
aujourd'hui, et elle est décisive : si la réponse est non, l'étape 4 devient
sans objet.

**Étape 3 — Spread réel par barre (`TCK-018`).** Découvert en écrivant ce
document, et c'est le point le plus transverse du dossier : **le spread de
catalogue est faux d'un facteur 2**. Médiane mesurée sur nos propres barres,
50 à 58 pips selon le timeframe et 50 pips même aux heures les plus actives,
contre 25 déclarés. Recalculé, l'edge H1 tient (+0,236 → **+0,205** R/trade) et
l'intraday empire (M15 −0,096 → **−0,150**). Aucun verdict ne bascule, mais tous
les chiffres or du dépôt sont optimistes d'un montant désormais **connu** — alors
que `studies/gold_forward/PROTOCOL.md` § 2.2 le déclarait inconnu. Coût : faible.
Bénéfice : transverse à tout le projet, Doud ou pas.

**Étape 4 — `TCK-014`, sorties partielles + suiveur.** C'est le gros morceau et
le verrou principal. Sans lui, sa géométrie R:R 7-17 est inatteignable et toute
mesure reste une caricature. À ne lancer qu'après l'étape 2 : si son entrée
n'a pas d'edge, un moteur de sortie plus riche ne la sauvera pas.

**Étape 5 — `TCK-016`, calendrier économique.** Débloque l'étage 5 en entier
(fenêtre T−2 min, interdiction pendant, ±5 min, J−1 avant taux, les trois temps
de la séance). Sources publiques Fed/BLS, fichier versionné, hors ligne.

**Étape 6 — `TCK-015`, règles de portefeuille.** Arrêt de journée, quotas.
Dernier parce que c'est une surcouche : elle ne change pas si l'edge existe,
elle change combien on le laisse travailler.

---

## 6. Ce qui restera non reproductible, quoi qu'on fasse

1. **Sa lecture macro.** Le biais H2 qu'on codera est une ombre mécanique de ce
   qu'elle construit à partir du dollar, de la Fed et de l'actualité. Un
   résultat sur cette porte ne valide ni n'invalide sa lecture.
2. **Le discrétionnaire dans la zone.** Elle décide « au millimètre » à quel
   niveau exact entrer, en regardant la colonne de prix. Nous coderons une
   règle ; elle applique un jugement entraîné sur cinq ans d'un seul instrument.
3. **Le renforcement adaptatif.** Ajouter plus bas quand la structure casse est,
   chez nous, indistinguable d'une martingale — et R2/R3 l'interdisent sous
   cette forme.
4. **La latence et l'exécution.** Elle mentionne constamment le décalage entre
   son écran et le flux YouTube ; ses points d'entrée « au millimètre » supposent
   une exécution à la seconde que notre chaîne ne vise pas.

**Conséquence méthodologique** : même une reconstruction complète des étapes 1
à 6 ne mesurera pas « la méthode Doud ». Elle mesurera **un système inspiré de
sa méthode, dont chaque écart est documenté ici**. C'est la seule promesse
tenable, et elle doit figurer dans le protocole de S019 avant la première
mesure.

---

## 7. Décisions demandées à Adrian

1. **Lancer l'étape 1 + 2** (données M1, puis S019 entrée seule) — recommandé :
   c'est peu coûteux, ça répond à la question décisive, et ça ne dépend
   d'aucun ticket ouvert.
2. **Arbitrer `TCK-014`** (sorties partielles + suiveur) : c'est le verrou qui
   sépare « mesurer son entrée » de « mesurer sa méthode ». À trancher après
   l'étape 2, avec son résultat en main.
3. **Valider l'étape 3** (spread réel par barre) : bénéfice transverse au projet
   entier, indépendant de Doud — probablement à faire quoi qu'il arrive.

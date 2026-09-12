# VERDICT — S023, Turnaround Tuesday (René Balke)

**Données** : MT5 Swissquote, H1 heure serveur, 2021-08-16 → 2026-09-11 — DAX 18 121
barres, NASDAQ 29 954, US30 29 957. Cache figé (`max_age_hours=10**9`).
**Exécution** : moteur commun (R9), bras fidèle `max_positions=1, cooldown 0,
coupe-circuit désarmé, max_hold_bars = 45 / 45 / 27`, spread catalogue puis **mesuré**
(DAX 23, NASDAQ 12, US30 35 pips), slippage 0.
**R1** (causalité) et **R5** (conformance) passés sur les trois indices, deux cellules
chacun — et ils sont une **PORTE** : en défaut, le harnais s'arrête sans écrire de
résultat. **Critères** : `FALSIFICATION.md`, écrits avant la mesure — appliqués ci-dessous
**sans retouche**. Corrections de relecture : **addendum daté en fin de document**
(aucun chiffre de mesure modifié).
**Sortie brute** : `backtests/run_all.log` · `backtests/results.json`.

---

## Verdict en une ligne

**ÉCHEC au sens des critères écrits d'avance** : la condition « au moins 2 des
3 indices » n'est pas remplie. **Seul le DAX** franchit le percentile témoin 90
(97,5 sur la cellule de fidélité) ; NASDAQ (75,5) et US30 (79,5) restent dans le
bruit — et sur ces deux-là, **acheter tous les lundis sans filtre fait mieux** que la
règle de Balke, ce qui désigne la dérive de l'indice, pas un effet de calendrier.

Ce n'est pas « la stratégie ne marche pas ». C'est : **sur 5 ans chez notre courtier,
un seul des trois indices porte le signal, et il n'est pas celui qu'on aurait parié.**

---

## 0. Le dispositif tient — vérifié avant de lire un P&L

| Contrôle pré-enregistré | Seuil | DAX | NASDAQ | US30 |
|---|---|---|---|---|
| Nombre de trades (cellule de fidélité) | 85-120 attendus | **91** ✓ | **110** ✓ | **104** ✓ |
| Garde catastrophe touchée | < 5 % des trades | 1 / 91 = 1,1 % ✓ | 2 / 110 = 1,8 % ✓ | 0 / 104 ✓ |
| Sorties tombant le mardi (`first_bar`) | > 85 % | **98,9 %** ✓ | 86,4 % ✓ | 89,4 % ✓ |
| Heure d'entrée | 1re barre du lundi | 08:00 (91/91) | 00:00 (108/110) | 00:00 (103/104) |
| `max_hold_bars` | mode des semaines | 27 (99,6 %) | 45 (89,7 %) | 45 (89,7 %) |
| Clôture journalière H1 vs barres D1 courtier | identique | écart médian nul | écart médian nul | écart médian nul |

Les quatre premières lignes valident la reproduction : la garde reste une garde (elle ne
gère rien), la sortie tombe bien le mardi soir, l'entrée tombe à 01:00 / 09:00 serveur —
à cinq minutes de ses 01:05 / 09:05. **La cadence prédite avant la mesure (85-120 trades)
est exacte sur les trois.** Le dispositif n'est pas en cause dans ce qui suit.

**Une exception, à dire** : les cellules de garde **3 %** sur NASDAQ déclenchent la garde
**15 à 21 fois sur 86-136 trades, soit 15,4 à 19,0 %** (maximum : SMA25 · first_bar ·
g3 %, 19/100). À cette distance, la garde n'est plus une garde mais un stop de gestion —
ces cellules ne sont **pas** une reproduction fidèle et ne peuvent pas servir de
conclusion sur la règle de Balke. Sur DAX g3 % : **5,3 à 7,1 %**, au-dessus du seuil
également. Sur US30 g3 % : 2,9 à 5,7 %.

Aux gardes 5 % et 10 %, le déclenchement redevient marginal, **mais pas nul partout** :
la **cellule de fidélité de chaque indice** reste ≤ 2 % (DAX 1/91 = 1,1 % ; NASDAQ
2/110 = 1,8 % ; US30 0/104), tandis que certaines cellules NASDAQ hors fidélité montent
à **3,5 %** (SMA40 · first_bar · g5 %, 3/86) et 3,0 % (SMA25 · first_bar · g5 %, 3/100).
Toutes les cellules g10 % sont à 0.

---

## 1. Cellule de fidélité — ce qu'il trade réellement

Bras fidèle, spread catalogue. « %/tr » = rendement moyen par trade en % du prix
d'entrée, net des coûts — **la seule unité comparable à son « +0,4 % du notionnel »**.

| Indice | Sa cellule | n | R | % total | **%/tr** | WR | PF | DD (R) | garde | **p témoin** | %/tr au spread **mesuré** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **DAX** | SMA40 · first_bar · g5 % | 91 | +8,09 | +40,49 | **+0,445** | 59,3 | 1,92 | 1,60 | 1 | **97,5** ✓ | **+0,436** |
| NASDAQ | SMA9 · first_bar · g5 % | 110 | +6,15 | +30,75 | +0,280 | 55,5 | 1,41 | 2,45 | 2 | 75,5 ✗ | +0,277 |
| US30 | SMA25 · first_bar · g5 % | 104 | +3,24 | +16,21 | +0,156 | 55,8 | 1,32 | 2,42 | 0 | 79,5 ✗ | +0,156 |

**Face à sa référence annoncée** (~+0,4 %/trade, profitable sur les trois) : le DAX
reproduit son ordre de grandeur (+0,445 %), le NASDAQ est en dessous (+0,280 %), l'US30
loin en dessous (+0,156 %). Les trois sont **positifs**, et tous restent positifs au
spread mesuré — le coût de bord n'est pas le sujet ici (il vaut 3 %, 2 % et 6 % du gain
moyen par trade respectivement). Ce qui manque au NASDAQ et à l'US30, c'est de se
distinguer du hasard.

---

## 2. L'apport du filtre SMA — la question qui décide

Référence non filtrée = `sma_period=0`, achat de **chaque** lundi, même sortie, même
garde. Étalon hors grille.

| Indice | | n | % total | %/tr | p témoin |
|---|---|---:|---:|---:|---:|
| DAX | filtré (SMA40) | 91 | +40,49 | **+0,445** | **97,5** |
| | **non filtré** | 255 | +41,60 | +0,163 | 86,0 |
| NASDAQ | filtré (SMA9) | 110 | +30,75 | +0,280 | 75,5 |
| | **non filtré** | 260 | **+52,97** | +0,204 | **85,5** |
| US30 | filtré (SMA25) | 104 | +16,21 | +0,156 | 79,5 |
| | **non filtré** | 260 | **+27,01** | +0,104 | **81,5** |

Le critère 4 était écrit « le résultat filtré doit dépasser la référence non filtrée ».
**Il ne précisait pas total ou par trade — c'est une imprécision de ma rédaction, et je
publie les deux lectures plutôt que de choisir celle qui arrange :**

- **Par trade**, le filtre ajoute partout : ×2,7 sur DAX, ×1,4 sur NASDAQ, ×1,5 sur US30.
  Il concentre bien le rendement sur les lundis qu'il sélectionne.
- **En total**, le filtre ne rapporte pas plus : égalité sur DAX (40,5 vs 41,6), et
  **franchement moins** sur NASDAQ (30,8 vs 53,0) et US30 (16,2 vs 27,0). On coupe 60 %
  des trades pour gagner autant, voire moins.
- **Face au témoin** — l'arbitre le moins ambigu des trois — le filtre n'améliore la
  position que sur le DAX (97,5 vs 86,0). Sur NASDAQ et US30, **la version non filtrée
  est MIEUX classée que la version filtrée** (85,5 > 75,5 ; 81,5 > 79,5).

Lecture : **sur les deux indices américains, ce qui est mesuré est la dérive haussière
de l'indice, pas le « turnaround » du lundi.** C'est exactement l'issue prévue en
FALSIFICATION §« Échec par le filtre », et la conséquence porte au-delà de S023 : elle
concerne aussi **Go Long** (même famille, achat quotidien sans filtre), pas encore mesuré.

---

## 3. La grille, le walk-forward et la multiplicité

| Indice | STRICT / 18 (≈ 0,9 par hasard) | meilleure STRICT (≥ 20 trades OOS) | p témoin | meilleure STRICT **encore fidèle** (garde ≤ 5 %) | p témoin | meilleure cellule %/tr | p témoin |
|---|---:|---|---:|---|---:|---|---:|
| DAX | **9** | SMA9 · first_bar · g3 % (39 OOS) · +33,64 % | 92,0 (garde 5,7 % → **non fidèle**) | **SMA9 · first_bar · g5 %** (39 OOS) · +34,59 % | **93,0** ✓ | SMA40 · first_bar · g10 % · +0,459 %/tr | 95,5 ✓ |
| NASDAQ | 7 | SMA25 · any_bar · g5 % (46 OOS) · +34,18 % | 69,0 ✗ | *la même* (garde 2,7 %) | 69,0 ✗ | SMA40 · first_bar · g10 % · +0,453 %/tr | 81,0 ✗ |
| US30 | 5 | SMA40 · any_bar · g3 % (30 OOS) · +15,57 % | 73,5 ✗ | SMA40 · first_bar · g5 % (26 OOS) · +16,87 % | 75,0 ✗ | SMA40 · first_bar · g5 % · +0,194 %/tr | 75,0 ✗ |

La colonne « encore fidèle » n'est pas un repêchage : une cellule dont la garde se
déclenche au-delà de 5 % des trades a gagné un stop de gestion que Balke n'a pas, et
FALSIFICATION.md la déclare hors reproduction. Citer son percentile reviendrait à créditer
la règle de Balke d'un résultat obtenu par une autre stratégie. Sur le DAX la distinction
ne change pas la conclusion (93,0 contre 92,0) ; elle change ce qu'on a le droit d'écrire.

**Le compte de cellules STRICT est trompeur, et il faut le dire.** `guard_pct` ne change
pas quels lundis sont pris : il ne fait que **redimensionner le R**, et ne modifie les
trades que lorsque la garde se déclenche. Vérification directe dans la sortie : sur US30,
les colonnes `%tot` des cellules g5 % et g10 % sont **strictement identiques** (aucune
garde touchée). Les 18 cellules sont donc **6 jeux de trades distincts** (3 périodes ×
2 modes d'entrée) vus sous 3 échelles de risque. Les 9 STRICT du DAX = 3 jeux distincts.
La borne « ≈ 0,9 par hasard » de la convention analytique surestime l'indépendance : le
bras témoin est ici la seule mesure honnête, et il ne valide que le DAX.

---

## 4. Par année — où est vraiment l'argent

Cellule de fidélité, % du prix d'entrée par année (n trades) :

| Indice | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (part.) | part de la meilleure année | années positives |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DAX | +2,03 (5) | +5,43 (32) | +2,86 (20) | +4,94 (10) | +6,66 (16) | **+18,57 (8)** | 46 % | **6 / 6** |
| NASDAQ | +2,29 (6) | +3,47 (30) | +3,04 (17) | −0,67 (19) | +6,26 (22) | **+16,37 (16)** | 53 % | 5 / 6 |
| US30 | −0,69 (7) | −0,53 (29) | −0,73 (23) | +0,70 (17) | +7,44 (18) | **+10,03 (10)** | 62 % | 3 / 6 |

Test de robustesse (non pré-enregistré, ajouté parce que le tableau l'impose) :

| | %/tr complet | sans 2026 | sans 2025-2026 |
|---|---:|---:|---:|
| DAX | +0,445 | **+0,264** | **+0,227** |
| NASDAQ | +0,280 | +0,153 | +0,113 |
| US30 | +0,156 | +0,066 | **−0,016** |

**Le DAX survit à l'ablation** des deux dernières années (+0,227 %/trade sur 67 trades) ;
le NASDAQ s'affaiblit ; **l'US30 devient négatif**. Aucun des trois ne déclenche la
clause d'échec « une seule année » au sens strict (aucune année ne dépasse 100 % du
total), mais la concentration 2025-2026 est réelle sur les trois — et elle rejoint
mot pour mot la réserve que Balke pose lui-même sur son propre live, ouvert en mars
2024 : *« probably I was lucky in the period »*. Nous mesurons la même période que lui,
donc nous héritons du même doute.

---

## 5. Le bras « règles communes » n'a rien changé — et c'est une information

`cooldown_bars=2, cb_losses=3, cb_cooldown_bars=24` donne des chiffres **strictement
identiques** au bras fidèle sur les trois indices. Raison mécanique : les trades sont
espacés d'une semaine (≈ 70 barres DAX, 120 barres US), très au-delà du plus long
refroidissement (24 barres). **Les règles communes anti-pertes consécutives sont inertes
sur cette stratégie** — elles ne la protègent de rien et ne la pénalisent en rien. Pour
un dispositif à un trade par semaine, la protection doit venir de la couche portefeuille,
pas du moteur.

---

## 6. Application littérale des critères

| # | Critère de réussite | DAX | NASDAQ | US30 |
|---|---|---|---|---|
| 1 | cellule de fidélité **ou** STRICT ≥ 20 OOS | ✓ | ✓ | ✓ |
| 2 | percentile témoin ≥ 90 | **✓ 97,5** | ✗ 75,5 | ✗ 79,5 |
| 3 | %/trade > 0 au spread mesuré | ✓ +0,436 | ✓ +0,277 | ✓ +0,156 |
| 4 | filtré > non filtré | ✓ par trade ; = en total ; ✓ au témoin | ✓ par trade ; ✗ en total ; ✗ au témoin | ✓ par trade ; ✗ en total ; ✗ au témoin |
| 5 | **les 4 ci-dessus sur ≥ 2 des 3 indices** | — | — | — |

**Critère 5 : NON REMPLI (1 indice sur 3).** Verdict : **échec**. On ne déplace pas la
barre après coup : un seul indice qui passe, c'est un seul indice, pas « la stratégie
fonctionne sur le DAX donc c'est une réussite partielle ».

---

## 7. Ce que ce verdict ne dit pas

- **Le DAX n'est pas disqualifié, il est isolé.** Percentile 97,5 sur la cellule qu'il
  trade vraiment, **93,0 sur la meilleure STRICT encore fidèle** (SMA9 · first_bar ·
  g5 %, 39 trades hors échantillon, garde 1/106), PF 1,92, **six années positives sur
  six**, résistant à l'ablation de 2025-2026. *(La meilleure STRICT toutes cellules
  confondues est la même à la garde près — SMA9 · first_bar · g3 %, percentile 92,0 —
  mais sa garde part 6 fois sur 106, soit 5,7 %, au-dessus du seuil de 5 % que
  FALSIFICATION.md fixe pour « la garde n'est plus une garde » : elle n'est pas citée
  comme référence, c'est la version g5 % qui l'est.)* Si un seul instrument devait être
  proposé à un forward scellé, c'est celui-là — et il se trouve que c'est aussi celui où
  Balke déclare son meilleur résultat (DE40 +6 k€ contre US30 +4 k€). **Cette convergence
  est une coïncidence rassurante, pas une preuve** : deux échantillons de la même période.
- **Rien n'est dit du live sans stop.** Nos chiffres supposent une garde à 5 %. Balke
  n'en a pas : son pire cas est le notionnel entier. Un passage en PAPER exigerait
  d'abord un plafond de portefeuille (couche risque), pas seulement ce verdict.
- **`any_bar` n'a pas été départagé de `first_bar`.** Les deux lectures donnent des
  chiffres voisins ; `any_bar` produit 10-25 % de trades en plus pour un rendement par
  trade légèrement inférieur. **Sa dérive de sortie est maintenant mesurée** (moyenne des
  9 cellules de chaque mode, `results.json` → `exit_drift`) :

  | | sorties le mardi | sorties le mercredi |
  |---|---:|---:|
  | DAX — `first_bar` / `any_bar` | 98,0 % / **81,7 %** | 0,0 % / **15,9 %** |
  | NASDAQ — `first_bar` / `any_bar` | 87,3 % / **75,1 %** | 8,9 % / **20,7 %** |
  | US30 — `first_bar` / `any_bar` | 87,8 % / **77,6 %** | 10,9 % / **21,2 %** |

  Soit **16 à 21 % des sorties au mercredi en `any_bar`**, contre 0 à 11 % en
  `first_bar` : le prix payé pour la fidélité d'entrée (« check constantly ») est un
  sixième à un cinquième des positions tenues un jour de trop. Aucun élément ne permet
  de trancher laquelle des deux est SA lecture — le panneau d'inputs (« Trading Start
  Hour », « Close Position Hour ») penche pour `first_bar`, la phrase « the program will
  check constantly » pour `any_bar`.
- **Cinq ans, ~100 trades par indice.** À 55 % de réussite sur 104 trades, l'intervalle
  de confiance à 95 % du taux de réussite couvre encore largement l'indifférence. Effectif
  faible, comme chez lui.

---

## 8. Conséquences

1. **Statut `BACKTESTED`** — mesuré, pas validé (R10). Aucune promotion.
2. **Ticket ouvert pour Adrian** : forward scellé DAX seul, ou abandon des trois ?
   La réponse n'est pas dans ce document : elle est à lui (R10).
3. **Remontée hors S023** : la référence non filtrée bat la règle filtrée sur les deux
   indices américains. Avant de mesurer **Go Long** (achat quotidien d'indice, même
   auteur, même famille), il faut savoir que sur cette période **toute** exposition
   longue aux indices US paie — le témoin de Go Long devra être choisi en conséquence,
   sinon il mesurera la même dérive et l'appellera un edge.

---

## Addendum 2026-09-12 — corrections de relecture

Relecture croisée (conformité + qualité) après première publication. **Aucun bug de
mesure trouvé ; aucun chiffre de la mesure n'a bougé** — vérifié par re-exécution
complète du harnais : DAX 91 trades / +0,445 %/tr / percentile 97,5 · NASDAQ 110 /
+0,280 / 75,5 · US30 104 / +0,156 / 79,5 · STRICT 9 / 7 / 5. Les critères
pré-enregistrés de `FALSIFICATION.md` n'ont **pas** été modifiés, et le verdict — échec
au sens du critère « ≥ 2 des 3 indices » — est inchangé.

Ce qui a été corrigé **dans ce document** (erreurs de rédaction, pas de calcul) :

| § | Avant | Après (vérifié dans `results.json`) |
|---|---|---|
| 0 | garde 3 % NASDAQ « 17-22 % » | **15,4-19,0 %** (max 19/100) |
| 0 | « sur g5 % et g10 %, partout ≤ 2 % » | ≤ 2 % sur la **cellule de fidélité de chaque indice** ; jusqu'à **3,5 %** sur des cellules NASDAQ hors fidélité ; DAX g3 % **5,3-7,1 %** |
| 3 | une seule colonne « meilleure STRICT » | colonne **« encore fidèle » (garde ≤ 5 %)** ajoutée et mesurée au témoin |
| 4 | années arrondies au dixième | valeurs au centième + colonne « années positives » |
| 7 | DAX « cinq années positives sur six » | **six sur six** (5/6 est le chiffre du NASDAQ, 2024 −0,67) |
| 7 | DAX « 92,0 sur la meilleure STRICT » | **93,0** sur la meilleure STRICT encore fidèle ; la cellule à 92,0 est écartée (garde 5,7 %) |
| 7 | « `any_bar` décale 10-14 % des sorties au mercredi » — **affirmation non mesurée** | dérive **mesurée** sur les 18 cellules : 15,9 / 20,7 / 21,2 % au mercredi |

Ce qui a été corrigé **dans le dispositif** (et re-mesuré) :

- `backtests/run_wf.py` : R1/R5 devient une **PORTE** — un défaut de causalité ou de
  conformance interrompt la mesure et **n'écrit aucun `results.json`** (sortie 2,
  « ARRÊT — DISPOSITIF EN DÉFAUT »). Auparavant R5 était affiché mais ne bloquait rien :
  une divergence live/backtest aurait été publiée comme un résultat. Porte vérifiée par
  injection d'une divergence factice.
- `backtests/run_wf.py` : profil de sortie mesuré sur **toutes** les cellules (et non
  les seules cellules-clés), d'où le tableau de dérive `any_bar` ci-dessus ; jour
  d'ouverture lu depuis le manifeste au lieu d'être codé en dur.
- `test_s023_strategy.py` : **2 tests ajoutés** (24 au total) sur des barres construites
  à la main où `first_bar` et `any_bar` doivent diverger — lundi qui ouvre au-dessus de
  la SMA puis passe dessous, et le cas miroir. Les fixtures en marche aléatoire ne les
  séparaient pas : un mutant rabattant `any_bar` sur `first_bar` passait les 22 tests
  précédents ; il échoue sur ces deux-là (vérifié par mutation).

`results.json` porte un arbre git modifié : le dossier S023 est committé par
l'orchestrateur **après** ces corrections.

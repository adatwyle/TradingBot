# PROTOCOLE — forward-test scellé s13 (extrême-MACD long / AUDCAD D1, EURJPY en observation)

> **Ce fichier est un scellé.** Il est écrit **avant** le premier signal mesuré
> et ne doit plus être modifié ensuite. Il fixe la configuration, les critères
> d'arrêt et la façon dont le verdict sera rendu. Toute conclusion future se
> lit contre ce qui est écrit ici, et nulle part ailleurs. La valeur entière de
> ce test tient à l'impossibilité de tricher rétroactivement — c'est la suite
> que `strategies/s13_macd_fx/research/VERDICT.md` § 5 propose : « forward
> scellé, zéro argent », calqué sur le motif `studies/gold_forward/`.

**Date de scellement** : 2026-08-17
**Dépôt au scellement** : commit `dd624e4`
**Origine** : `strategies/s13_macd_fx/research/VERDICT.md` — statut
`EDGE CANDIDAT (faible)`, une survivante (AUDCAD ext-long D1, hold-out scellé
+0,58 R/t × 11 trades, percentile 96) dont l'effectif de hold-out est trop
mince pour conclure. Décision de lancer ce dispositif : Adrian.

---

## 1. Ce qui est testé — et ce qui ne l'est pas

**L'hypothèse** : la cellule survivante de s13 — AUDCAD D1, extrême-MACD long
(MACD/ATR sous son 10e percentile glissant 252 j → long au close, ±1,5 ATR),
sortie vivante de 756 cellules, des falsifications F1-F8 gelées d'avance et
d'un hold-out de 18 mois jamais vu — produit une espérance positive **hors de
tout échantillon qui a servi à la sélectionner**. Le hold-out a donné un
signal (percentile 96) sur 11 trades ; 11 trades ne sont pas une preuve
(VERDICT § 5.1). Ce forward est la seule mesure qui ne doive rien à la
sélection.

**Le bras d'observation** : EURJPY, même cellule — la jumelle qui affichait le
percentile 100 en exploration mais n'a PAS battu son beta au hold-out
(percentile 74 : un long au hasard faisait +0,32 R/t sur sa période). Elle est
journalisée **à l'identique** (mêmes conventions, même témoin à la lecture)
mais étiquetée `OBSERVATION` : elle n'entre dans **aucun** critère d'arrêt.
Elle est là pour apprendre — confirmer ou infirmer prospectivement que la
divergence des jumelles était du bruit — pas pour compter.

**Ce test ne mesure pas** : la propriété qui expliquerait l'edge (le récit
« retour à la moyenne » est affaibli par l'asymétrie long/short constatée),
le côté short (négatif partout dans l'étude), le panier des 9 paires
(+0,020 R/t poolé — non instruit ici), ni la variante intra-journalière
(négative, VERDICT § 4). Il mesure UNE chose : prospectivement, cette règle
figée bat-elle, ou non, une entrée aléatoire à dispositif de risque identique
sur les mêmes barres AUDCAD.

---

## 2. Configuration FIGÉE

Source unique : `studies/s13_forward/params.json` — le fichier que
`run_forward.py` charge et vérifie à chaque passage.

### 2.1 Le scellé cryptographique

```
SHA-256(params.json) = df098b0e9699fa8ffeb109114f127dc67de88716d7663500e8ffe62436ef69e2
```

Ce hash est répliqué dans la constante `PARAMS_SHA256` de `run_forward.py`.
Le script **refuse de tourner** si le fichier ne correspond plus (exit 3).
Modifier `params.json`, la constante, ou les deux, laisse une trace dans
l'historique git — c'est le but. Le test
`test_forward_step.py::test_hash_du_vrai_fichier_scelle_correspond` casse à la
moindre divergence.

### 2.2 Contenu (copie de lecture — `params.json` fait foi)

| Élément | Valeur | Provenance |
|---|---|---|
| Stratégie | `s13_macd_fx`, code au commit courant du dépôt — **une seule implémentation** : le pas de mesure importe `strategy.precompute` + `generate_signals`, exactement comme `backtests/run_holdout.py` (R5) | `strategies/s13_macd_fx/strategy.py` |
| Bras principal | **AUDCAD / D1** (barres MT5 Swissquote, heure serveur) — seul comptable dans les critères § 3 | verdict s13 § 5 |
| Bras d'observation | **EURJPY / D1**, même cellule, étiqueté `OBSERVATION`, capital virtuel séparé, hors critères | verdict s13 § 5.2 |
| Cellule | `family ext · direction long · lookback 252 · q 0,10 · exit atr_1.5_1.5` — les **défauts figés** de `strategy.py` (`default_params`, cellule survivante du hold-out) ; constantes hors grille MACD 12/26/9, ATR 14 | `strategy.py`, gel 2026-08-17 |
| Spread | catalogue `core/data/instruments.py` : AUDCAD 3,2 pips (pip 0,0001), EURJPY 3,6 pips (pip 0,01) — demi-spread payé à chaque extrémité | catalogue |
| Slippage | **0,5 pip par bout** — le même que TOUTE l'étude s13 (exploration, candidates, hold-out : `SLIPPAGE = 0.5`). Les chiffres du forward restent donc directement comparables au dossier s13. | `backtests/run_holdout.py` |
| Exécution | moteur commun : entrée au close de la barre de signal ; stop **unilatéral** (gap payé à l'ouverture — sur D1 les gaps de week-end sont routiniers) ; cible sans faveur de gap ; SL prime sur TP dans la même barre ; une position par bras ; **cooldown 0, circuit breaker désarmé (`cb_losses` 999)** — les `engine_kwargs` de l'étude, PAS ceux de gold_forward ; `max_hold_bars` aucun | `core/backtest/engine.py`, `EK` de l'étude, répliqué ligne à ligne dans `forward_step.py` et vérifié par tests |

### 2.3 Sizing virtuel

1 % de risque par trade sur un capital fictif initial de **10 000 par bras**,
dimensionné par la logique de `core/risk/guards.py` (`RiskLayer.evaluate`,
`max_position_pct = 0,01`, une position par instrument). Le journal parle donc
en R **et** en monnaie. **La mesure de vérité reste le R** : la monnaie est une
lecture, le capital virtuel n'entre dans aucun critère d'arrêt. Les deux bras
ont chacun leur capital — l'observation ne contamine jamais la comptabilité
du bras principal (`test_observation_n_entre_pas_dans_la_comptabilite_du_principal`).

---

## 3. LES CRITÈRES D'ARRÊT — chiffrés d'avance, c'est le cœur

Le témoin est le **bras à entrée aléatoire** de
`core/backtest/anchored_wf.py::control_arm` : 200 tirages, graine figée
20260817, même effectif, même répartition long/short, mêmes stops/cibles en
ATR, mêmes barres, même spread/slippage, mêmes contraintes de moteur
(`engine_kwargs` identiques à la stratégie — cooldown 0, cb désarmé).
Recalculé par `report_forward.py` **sur la fenêtre écoulée du forward** (du
scellé à la dernière barre mesurée). **Tous les critères se lisent sur le
bras AUDCAD seul.**

### Le calibrage, justifié sur la fréquence mesurée

L'étude a mesuré **~7 trades/an** sur AUDCAD (130 trades sur ~18,5 ans
d'exploration ; 11 trades sur les 18 mois de hold-out ≈ 7,3/an — cohérent).
Les seuils gold_forward (40/100 trades, 12 mois) sont donc intransposables :
à 7 trades/an, 100 trades = 14 ans. Calibrage retenu :

- **20 trades ≈ 34 mois** — le premier moment où un R cumulé a un sens ;
- **40 trades ≈ 5,7 ans** — comparable à l'effectif d'exploration OOS par
  fenêtre, et ~4× l'effectif du hold-out qui a motivé ce test ;
- le seuil d'effondrement de fréquence est fixé à **12 trades à 36 mois**, et
  PAS aux 20 esquissés au cadrage de mission : à λ ≈ 21 trades attendus en
  36 mois, un seuil à 20 (95 % de l'attendu) serait déclenché par le simple
  bruit de Poisson dans ~38 % des trajectoires HONNÊTES — un critère d'arrêt
  qui se déclenche une fois sur trois sans effondrement réel ne mesure rien.
  Le ratio retenu 12/21 ≈ 57 % réplique la discipline de gold_forward
  (40/78 ≈ 51 % de l'attendu annuel) : seul un régime qui ne produit
  réellement plus le signal le franchit (P(N < 12 | λ = 21) ≈ 1,5 %).

### a) Arrêt-échec
Dès que **≥ 20 trades** sont clôturés : si le **R cumulé** du forward passe
**sous le percentile 20** de la distribution du témoin recalculée sur la même
fenêtre → **STOP DÉFINITIF**. Verdict : « pas d'edge confirmé en prospectif ».
Pas de deuxième chance, pas de « on attend encore un peu ».

### b) Arrêt-succès
**≥ 40 trades** clôturés **ET** percentile **≥ 95** contre le témoin →
**promotion en discussion**. La discussion — pas la promotion : la décision est
à Adrian, et devra affronter ce que ce test ne mesure pas (§ 1), la lenteur
intrinsèque du signal (~7 trades/an), et le fait qu'un percentile 95 APRÈS la
sélection parmi 756 cellules vaut moins qu'un 95 naïf (VERDICT § 6.3).

### c) Arrêt-temps — deux volets
**c1 (fréquence effondrée)** : **< 12 trades clôturés après 36 mois** (contre
~21 attendus) → **NON CONCLUSIF, on ferme**. Un régime qui ne produit plus le
signal n'est pas un régime où le signal se mesure.
**c2 (horizon)** : **72 mois sans que (a) ni (b) ne soit atteint** → lecture
finale obligatoire, **NON CONCLUSIF, on ferme**. À ~7 trades/an, 72 mois
suffisent nominalement à armer (b) (~42 trades) ; un test qui n'a tranché ni
dans un sens ni dans l'autre en 6 ans n'a pas le droit de courir pour
toujours. gold_forward n'avait pas besoin de ce volet (~78 trades/an) ; ici
il est la seule borne supérieure honnête.

### d) Invariance
**Aucun paramètre ne peut changer en cours de route.** Toute modification de
`params.json`, de la cellule, des spreads/slippage de valorisation, des
conventions d'exécution ou des critères ci-dessus **invalide le test** :
redémarrage à zéro, nouveau scellé, nouveau journal. Le hash § 2.1 rend
l'événement visible ; ce paragraphe le rend inexcusable. (Exception unique :
un bug démontré du moteur commun corrigé dans `core/` — auquel cas
l'invalidation est déclarée, pas contournée : le test repart à zéro sur le
moteur corrigé.) Le bras d'observation est soumis à la même invariance : on
n'« essaie » pas autre chose sur EURJPY en cours de route.

**Ordre de préséance** : (a) et (b) sont évalués à chaque lecture ; si les deux
sont simultanément vrais (impossible par construction : percentile < 20 et
≥ 95 s'excluent), le dispositif est bogué et le test est invalide. (c1)/(c2)
ne sont évalués qu'à défaut de (a)/(b).

---

## 4. Ce qui est mesuré, et comment le verdict sera rendu

**Mesuré** : chaque signal de la cellule figée sur barres D1 clôturées, sur
les deux bras, exécuté virtuellement aux conventions du moteur commun ;
date de barre, bras, sens, prix d'entrée (coût inclus), stop, cible, taille,
sortie (SL/TP), R, monnaie. Une position encore ouverte est valorisée au
dernier close dans `status.json` (lecture) mais **n'entre pas** dans le R
cumulé des critères.

**Rendu** : par `report_forward.py`, qui affiche — effectif TOUJOURS en
regard — pour chaque bras le R cumulé, le R moyen avec IC 95 %, le percentile
témoin, puis LA phrase, évaluée sur AUDCAD seul : soit « AUCUN critère
d'arrêt atteint — continuer », soit le critère atteint. Le verdict final sera
un `VERDICT_FORWARD.md` écrit **à l'arrêt du test seulement**, adossé ligne à
ligne aux critères § 3, journal en annexe. Le bras EURJPY y sera lu comme ce
qu'il est : une observation d'hypothèse, sans pouvoir décisionnel.

**Intégrité — trois couches** :
1. `journal.csv` est **append-only à chaîne de hachage** : chaque ligne porte
   le SHA-256 du fichier tel qu'il était avant elle. Modifier, insérer ou
   supprimer une ligne passée casse tous les maillons suivants et le pas
   suivant refuse de tourner (exit 4).
2. Chaque ligne porte **deux horodatages** : la barre (heure serveur) et la
   **mesure** (`measured_at_utc`, quand le script a tourné). Un trade mesuré
   avant sa barre, ou des mesures non monotones, sont un antidatage visible.
3. La couche externe est **git** : protocole, hash et code committés avant le
   premier signal. Un falsificateur qui réécrit journal + état + git réécrit
   l'histoire d'un dépôt — c'est détectable par les remotes et c'est hors du
   modèle de menace d'un test qu'on se fait à soi-même.

**Données et état** (jamais dans l'arborescence de code — convention projet) :

```
C:\db\tbot\s13_forward\
├── journal.csv      # append-only, chaîné, les DEUX bras — LA pièce du dossier
├── state.json       # curseurs par bras, positions, capitaux, empreinte journal
├── status.json      # dernière lecture (effectifs, R, distance aux critères)
└── run.log          # sorties des passages planifiés
```

---

## 5. Le pas de mesure

`run_forward.py` est **idempotent** : exécutable chaque jour (ou plus souvent,
sans effet si aucune barre D1 nouvelle). À chaque passage : vérification du
scellé (hash) et de la chaîne du journal **avant toute écriture** ; chargement
des barres fraîches (`core.data.source.load_bars`, cache ≤ 12 h) ; retrait de
la barre en formation ; recalcul des signaux avec les paramètres scellés
(même code que le backtest — R5, pas de deuxième implémentation) ;
consommation des seules barres postérieures au curseur DU BRAS ; suivi des
positions ouvertes ; append au journal ; réécriture de `status.json`.

MT5 indisponible → exit 2, message dans `run.log`, journal intact, nouvel
essai au passage suivant. Un seul des deux flux indisponible → l'autre est
mesuré, le curseur du manquant ne bouge pas et ses barres manquées sont
rejouées au passage suivant (les signaux sont recalculés sur l'historique
complet, l'exécution virtuelle est déterministe sur barres closes). Les trous
de mesure sont sans effet.

**Premier passage** : pose du scellé, **sur les deux flux à la fois** (pas de
bras qui démarre en retard). Le curseur de chaque bras est placé sur sa
dernière barre close ; **aucun signal historique n'entre au journal**. Aucun
trade au premier passage est le comportement attendu.

**Note de lisibilité assumée** : la fenêtre de barres MT5 est glissante
(~5 ans) ; les EMA du MACD ont une mémoire théoriquement infinie, donc deux
fenêtres décalées peuvent différer d'un epsilon sur les indicateurs. Avec un
percentile glissant de 252 barres pris à des centaines de barres du bord
(garde-fou `WARMUP_MIN_BARS = 320`), l'effet est négligeable — et seuls les
signaux **postérieurs au curseur** sont jamais consommés : le journal passé ne
peut pas être réécrit par ce mécanisme.

---

## 6. Armement (décision Adrian — non exécuté par le dispositif)

Le Planificateur de tâches Windows exécute `run_forward.bat` chaque jour,
après la clôture de la barre D1. **Commande à exécuter par Adrian, et par lui
seul** (invite de commandes) :

```bat
schtasks /Create /TN "TBOT_s13_forward" ^
  /TR "C:\Datas\Projects\TradingBot_9.0.0.x\studies\s13_forward\run_forward.bat" ^
  /SC DAILY /ST 07:20 /F
```

Vérifier : `schtasks /Query /TN "TBOT_s13_forward"`.
Désarmer (à l'arrêt du test) : `schtasks /Delete /TN "TBOT_s13_forward" /F`.

07:20 locale est confortablement après la clôture D1 serveur (la barre en
formation est retirée de toute façon — l'heure exacte n'a aucune incidence
sur la mesure, seulement sur sa fraîcheur). MT5 doit être ouvert et connecté
sur le poste pour que le passage voie des barres fraîches ; sinon le passage
log « barres indisponibles » et réessaie le lendemain — sans conséquence
autre qu'un retard de mesure. Le week-end, le passage tourne à vide (aucune
barre nouvelle) : c'est le comportement idempotent attendu.

La lecture se fait à la demande : `python -m studies.s13_forward.report_forward`.

---

## 7. Fichiers du dispositif

| Fichier | Rôle |
|---|---|
| `PROTOCOL.md` | **Ce scellé.** Ne plus modifier. |
| `params.json` | Configuration figée — hash § 2.1. Ne plus modifier. |
| `forward_step.py` | Logique du pas : scellé, journal chaîné, exécution aux conventions moteur (engine_kwargs de l'étude), sizing `RiskLayer`, deux bras. |
| `run_forward.py` | CLI du pas de mesure (codes de sortie documentés en tête). |
| `report_forward.py` | Lecture contre les critères § 3, témoin recalculé par bras, critères sur AUDCAD seul. |
| `run_forward.bat` | Enveloppe pour le Planificateur de tâches. |
| `test_forward_step.py` | 14 tests : idempotence, prospectivité, scellé bi-flux, append-only (réécriture/troncature/suppression), refus sur hash, gap payé, préséance SL/TP, cohérence R/monnaie, ré-entrée même barre (cooldown 0), indépendance des bras. |

Périmètre d'écriture : `studies/s13_forward/` et `C:\db\tbot\s13_forward\`
uniquement. Rien dans `core/`, rien dans `strategies/`, rien dans les études
armées (`gold_forward`, `macd_ai_paper`).

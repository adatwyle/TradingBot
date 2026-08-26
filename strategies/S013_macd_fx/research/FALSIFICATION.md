# s13 — Conditions de falsification, figées AVANT le premier backtest

> Date de gel : 2026-08-17. Aucun backtest de la stratégie n'a été exécuté au
> moment où ce fichier est écrit. Seules des mesures de DONNÉES existent
> (profondeur MT5 D1/H4, ATR médian, drag du spread, tailles des splits).
> Toute modification de ce fichier après le premier backtest serait une
> falsification au sens inverse du terme. Le commit de gel précède tout run.

## Convention statistique

La référence du dossier est le **bras témoin empirique** (`attach_control_arm`
et `control_arm`, 200 tirages, graine 20260816), exécuté avec les MÊMES
`engine_kwargs` que la stratégie. Le comptage STRICT/n×0,05 est rapporté pour
archive, jamais comme évidence. La recherche est LARGE (≈ 84 cellules × 9
paires × 3 familles réparties) : la protection principale contre cette largeur
est le **hold-out scellé** (ci-dessous), qui n'est ouvert qu'UNE fois, sur au
plus 3 candidates, après que toutes les autres falsifications ont été
appliquées sur la seule fenêtre d'exploration.

## HOLD-OUT SCELLÉ — la protection n°1, déclarée avant tout chiffre

- **Coupe des données** : barres D1 datées < 2026-08-16 (dernière barre
  complète 2026-08-15).
- **Scellé** : toutes les barres datées ≥ **2025-02-16** (18 derniers mois,
  466 barres/paire) sont EXCLUES de toute exploration, toute grille, tout
  témoin, toute sélection. Aucun script d'exploration ne les charge.
- **Exploration** : 2006-08 → 2025-02-15 (≈ 5 700 barres/paire).
- **Ouverture** : UNE seule fois, sur ≤ 3 candidates finales sélectionnées par
  la règle écrite ci-dessous. Aucun retour en arrière : un échec au hold-out
  est un échec définitif de la candidate — pas une invitation à en choisir une
  quatrième (la liste des candidates est close AVANT l'ouverture).

## Économie a priori (data-only, mesurée avant implémentation)

| Paire | barres | explo | hold-out | ATR14 D1 méd (pips) | spread | drag stop 3 ATR | drag stop 1,5 ATR |
|---|---|---|---|---|---|---|---|
| EURUSD | 6213 | 5747 | 466 | 75,1 | 1,9 | 0,84 % | 1,69 % |
| USDJPY | 6210 | 5744 | 466 | 78,1 | 2,8 | 1,19 % | 2,39 % |
| USDCHF | 6212 | 5746 | 466 | 64,4 | 2,2 | 1,14 % | 2,28 % |
| AUDUSD | 6212 | 5746 | 466 | 65,0 | 2,0 | 1,03 % | 2,05 % |
| USDCAD | 6214 | 5748 | 466 | 72,4 | 3,1 | 1,43 % | 2,85 % |
| EURJPY | 6213 | 5747 | 466 | 103,0 | 3,6 | 1,17 % | 2,33 % |
| CHFJPY | 6141 | 5675 | 466 | 86,3 | 3,9 | 1,51 % | 3,01 % |
| EURCHF | 6214 | 5748 | 466 | 46,0 | 3,5 | 2,54 % | 5,07 % |
| AUDCAD | 6169 | 5703 | 466 | 64,3 | 3,2 | 1,66 % | 3,32 % |

Le péage D1 est de 1-5 % du R : le terrain permet à un petit edge d'exister.
Si rien ne survit ici, ce n'est pas la faute du spread. Tout chiffre « réel »
ajoute un slippage de 0,5 pip par bout (déclaré ici, appliqué partout).
EURCHF : régime administré 2011-2015 (plancher BNS) — lu avec cette réserve.

## Grille (figée — par paire et par famille)

Constantes hors grille : MACD 12/26/9 (ligne EMA12−EMA26, signal EMA9 de la
ligne), ATR 14, warmup 60, entrée au close de la barre de signal.
`engine_kwargs` = `cooldown_bars=0, cb_losses=999` (on mesure le SIGNAL ; le
circuit breaker est un habillage de production qui masquerait la mesure), même
kwargs pour le témoin. La sous-grille `hold` de la famille B tourne dans un
run séparé avec `max_hold_bars=20` (stratégie ET témoin).

| Famille | Paramètres | Cellules /paire |
|---|---|---|
| **A `mr`** (s12 transposé, 2 sens) | `n_down` ∈ {3, 4, 5} × `range_filter` ∈ {off, on(20 j, q 0,25)} × sortie ∈ {sym_sl3, sym_sl10, atr_1.5_1.5, atr_2_3} × sens {long, short} | 48 |
| **B `cross`** (référence) | déclencheur ∈ {signal, zéro} × sortie ∈ {atr_1.5_1.5, atr_2_3, hold20_sl3} × sens {long, short} | 12 |
| **C `ext`** (percentile MACD/ATR) | `lookback` ∈ {126, 252} × `q` ∈ {0,05, 0,10} × sortie ∈ {sym_sl3, atr_1.5_1.5, atr_2_3} × sens {long, short} | 24 |

Total : 84 cellules × 9 paires = **756 cellules**. C'est LARGE et c'est
assumé : la convention n×0,05 attendrait ~38 « réussites » par pur hasard.
D'où : témoin par cellule candidate, sélection par règle écrite, hold-out
scellé unique.

## Règle de sélection des candidates (écrite AVANT tout résultat)

1. Sur l'exploration seule, WF ancré 4 fenêtres par paire ; par (paire,
   famille, sens), les cellules avec ≥ 60 trades OOS cumulés ET ≥ 100 trades
   plein-échantillon-exploration sont éligibles.
2. Témoin apparié 200 tirages sur les cellules éligibles les mieux classées
   (avg_oos) : retenir celles à **percentile ≥ 95**.
3. Parmi elles, appliquer voisinage (F3) et multi-graines (F4). Les
   survivantes sont classées par percentile témoin puis R/trade OOS net.
4. **Au plus 3 candidates** toutes familles/paires confondues passent au
   hold-out. La liste est écrite au VERDICT AVANT l'ouverture du scellé.

## Falsifications (TOUTES chiffrées, figées)

| # | Condition | Seuil | Si déclenchée |
|---|---|---|---|
| **F1** | Témoin mesuré (exploration, OOS) : `honest_r` vs 200 entrées aléatoires à dispositif identique | percentile **< 95** | cellule éliminée — le timing n'apporte rien |
| **F2** | Espérance à spread nul (exploration, plein échantillon) | R/trade ≤ 0 | PAS D'EDGE — le signal est négatif avant le péage |
| **F3** | Voisinage : les voisins à ±1 pas de grille (même famille/sens, chaque paramètre bougé d'un cran) | < 50 % des voisins avec OOS > 0, OU médiane des voisins < 0 | sur-ajustement de cellule — éliminée |
| **F4** | Multi-graines : témoin rejoué sur 5 graines (20260816+k, k=0..4) | percentile ≥ 95 sur < 4/5 graines | artefact de graine — éliminée |
| **F5** | Effectif : ≥ 60 trades OOS cumulés ET ≥ 100 trades exploration | en dessous | NON CONCLUSIF pour la cellule, sans négociation |
| **F6** | Les deux sens séparés : un « edge » qui n'existe qu'agrégé long+short sans tenir dans au moins un sens séparément | aucun sens ne tient seul | artefact d'agrégation — éliminé |
| **F7** | **HOLD-OUT scellé** (ouvert UNE fois, ≤ 3 candidates) : R/trade net > 0 ET témoin hold-out (200 tirages, `control_arm` tranche unique) percentile ≥ 90 | net ≤ 0 OU percentile < 90 | PAS D'EDGE pour la candidate — définitif |
| **F8** | Cohérence trans-paires (informatif, pesé au verdict) : la config candidate appliquée à froid aux 8 autres paires, R/trade poolé | fortement négatif (≤ −0,05 R/t poolé) | suspicion de sélection de paire — dégradé au verdict, documenté |

Lecture des filtres (range_filter, fenêtre session) : UNIQUEMENT au R/trade,
jamais au PnL total (retirer des trades baisse le total mécaniquement).

## Verdict — règles d'issue (écrites d'avance)

- **EDGE CANDIDAT** : ≥ 1 candidate passe F1-F7 (F8 documenté). Livrable :
  la stratégie + proposition de forward scellé motif gold_forward (zéro
  argent). PAS de promotion PAPER/LIVE — décision d'Adrian (R10).
- **PAS D'EDGE** : aucune candidate ne passe F7 (ou aucune candidate
  n'émerge de F1-F6). Livrable : le constat chiffré, par famille, avec la
  comparaison explicite à s12.
- **NON CONCLUSIF** : uniquement si les effectifs (F5) tuent TOUTES les
  familles — improbable avec ~5 700 barres × 9 paires, déclaré pour la forme.

## Variante session (UNE, déclarée)

H4, entrées limitées aux heures serveur 12-19 (chevauchement Londres/NY),
appliquée à la (aux) candidate(s) finale(s) uniquement, à titre informatif —
elle ne crée PAS de candidate supplémentaire et ne passe pas au hold-out.

## Angles morts assumés (notés avant mesure)

1. **La sélection de la meilleure cellule par (paire, famille) reste de la
   sélection** : le percentile témoin d'une cellule choisie parmi ~84 est
   optimiste. C'est ce que F7 (hold-out vierge) est chargé d'attraper.
2. Les 4 fenêtres OOS sont emboîtées, pas indépendantes (METHODOLOGY §9).
3. 20 ans de D1 ≈ 5 700 barres d'exploration seulement : le D1 paie sa
   propreté en effectif. F5 est là pour ça.
4. La cible « reprise » (sym) est statique posée au signal — dégradation
   héritée de s12, déclarée, défavorable en mouvement prolongé.

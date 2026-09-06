# ANALYSIS — S018, or v2 instruite par la méthode Doud

**Source** : `docs/sources/moneytalk/` — MoneyTalk #29 (Cindy « Doud Trading »,
2026-06-13) et #30 (Karen Rababian, carnet d'ordre, 2026-06-19).
**Lignée** : `strategies/S011_legacy_breakout` v1.0.0, cellule résiduelle or.
**Témoin** : `studies/gold_forward/` — forward scellé le 2026-08-16, en vol.
**Données** : MT5 Swissquote, XAUUSD **H1**, 2021-08-09 → 2026-09-04 (30 024 barres).

---

## 1. La question posée

`S011/research/VERDICT.md` § 2.5 laisse l'or en **`NON CONCLUSIF`** : 400 trades,
+90,4 R, +0,226 R/trade, voisinage 9/9 positif, zéro trade fantôme — mais
1 instrument sur 8, sélectionné après coup parmi 1024 cellules, et 62 % du
résultat concentré sur la seule année 2025. Le dossier conclut qu'un test dédié
à l'or est justifié.

La v1 mesure cette cellule telle quelle, en prospectif et sous scellé. Elle ne
peut pas être touchée : `studies/gold_forward/run_forward.py:43` importe
`S011.strategy` en direct, et le hash de `params.json` ne protège pas le code.
**S018 est donc l'endroit où l'or a le droit de changer**, la v1 restant témoin.

La question de ce dossier : **les lectures de la méthode Doud améliorent-elles
la cellule résiduelle, et lesquelles ?**

---

## 2. Ce que la source affirme, et ce qui en a été retenu

Le détail sourcé, horodaté et vérifiable est dans
`docs/sources/moneytalk/SYNTHESE.md` § 1 et § 2. Résumé opératoire :

| # | Affirmation (horodatée) | Traduction mécanique | Retenu ? |
|---|---|---|---|
| D1 | « je vends quasiment jamais » (@ 21:52) | `side_mode = long_only` | **oui** |
| D2 | biais directionnel avant le graphique (@ 23:32) | `htf_bias = daily_ema` (porte de tendance journalière) | **oui, en proxy** |
| D3 | « structure et non mèche » (@ 17:52) | `channel_source = bodies` (Donchian sur les closes) | **oui** |
| D4 | « récupérer le milieu » (@ 18:08) | `entry_mode = equilibrium` (entrée au repli 50 % de la jambe) | **oui** |
| D5 | US + Asie, jamais Londres (@ 35:35) | `session_filter = doud` | **oui** |
| D10 | scalp intraday | `max_hold_bars` borné | **oui, hors grille** (sweep secondaire) |
| D6-D8 | TP partiels, SL suiveur, break-even payant | — | **non** : le moteur commun ne déplace pas de stop, R9 interdit d'en écrire un autre → `tickets/TCK-014` |
| D9 | entrée 2 min avant l'annonce (@ 10:54) | — | **non** : pas de calendrier économique dans nos données → `tickets/TCK-016` |
| D11 | pas de stop, renforcement à la baisse (@ 12:31, @ 39:07) | — | **refusé** : R3. La source chiffre elle-même le coût de cette règle à −80 000 € en une séance (@ 32:30) |

Du podcast #30 (carnet d'ordre), rien n'entre : `core/data/source.py` déclare
`real_volume = 0` sur tous nos instruments, donc absorption, delta bid/ask et
footprint sont **hors d'atteinte par absence de donnée**, pas par manque de
réglage. Sa règle de discipline (« tu gagnes, tu arrêtes la journée », @ 15:47)
est une règle de portefeuille — elle relève de `core/risk/`, pas d'une
stratégie (R2) → `tickets/TCK-015`.

---

## 3. Le dispositif — et pourquoi il est lisible

### 3.1 La cellule neutre EST la v1

Cinq commutateurs binaires, 32 cellules. La cellule
`breakout · extremes · both · off · off` **reproduit exactement les signaux de
S011 aux paramètres scellés** : 784 signaux, égalité stricte sur les 30 024
barres, vérifiée par `test_strategy.py::test_cellule_neutre_reproduit_la_v1`
et rejouée dans `backtests/grid.txt` § 1.

Sans cette égalité, un écart mesuré pourrait venir d'une réécriture plutôt que
de l'hypothèse. C'est elle qui autorise à lire chaque commutateur comme un
**contraste**, et non comme une nouvelle stratégie qu'il faudrait re-prouver
entièrement.

Deux conséquences assumées : les indicateurs (ATR, RSI, ADX/±DI) sont **importés**
de S011 plutôt que recopiés ; et le filtre de régime ER/failed-rate n'est pas
repris, la cellule scellée le neutralisant identiquement (`er_min = 0,00` rend
`x < 0` toujours faux, `fr_max = 1,00` rend `x > 1` toujours faux).

### 3.2 Ce qui a été fixé AVANT de mesurer

Pré-enregistré dans `manifest.yaml` et dans `backtests/run_wf.py`, commités
avant la première exécution :

- la grille (32 cellules) et les constantes hors grille — `EQUILIBRIUM_RATIO = 0,5`
  (« le milieu » est l'hypothèse, pas un réglage), `PULLBACK_MAX_BARS = 24`,
  `HTF_EMA_DAYS = 20` ;
- le seuil d'effectif `MIN_TRADES = 20` et `MAX_DD_R = 12` du harnais ;
- l'attente de multiplicité : **32 cellules à 5 % ⇒ ≈ 1,6 réussite par pur
  hasard**, à opposer au nombre observé ;
- l'exécution : celle du forward scellé (`max_positions 1`, `cooldown 2`,
  circuit breaker 3/24, spread 25 pips, slippage 0), pour que v1 et v2 soient
  comparables trade pour trade ;
- la lecture principale : **effet marginal de chaque ingrédient** (16 cellules
  où il est actif contre 16 où il ne l'est pas), pas la chasse à la meilleure
  cellule.

**Ce qui n'était pas pré-enregistré**, et doit être lu comme tel : le choix de
la cellule appelée « candidate » dans le VERDICT. Il est fait après mesure, sur
un critère annoncé (survie en hors échantillon avec effectif), mais après.

### 3.3 Ce que le dispositif ne mesure pas

- **Le biais macro réel.** D2 est une porte de tendance journalière, pas le
  dollar ni la Fed. Un résultat sur `htf_bias` ne valide ni n'invalide ce que la
  source appelle son biais directionnel.
- **La gestion de position.** L'essentiel de son edge revendiqué vit dans les
  sorties (partielles, SL suiveur) que notre moteur ne sait pas exprimer. Ce
  dossier mesure ses **entrées**, pas sa méthode complète — et il faut le dire
  avant toute conclusion sur « la méthode Doud ».
- **Le slippage.** À 0, comme la v1 et son témoin. Les chiffres sont donc
  optimistes d'un montant inconnu, uniformément pour toutes les cellules.
- **L'intraday.** L'or scalpé se joue en M1-M5 chez elle ; nous mesurons en H1,
  parce que c'est le timeframe de la v1 et que la comparabilité prime.

---

## 4. Ce qui a été vérifié avant de lire un seul chiffre

| Contrôle | Résultat | Archive |
|---|---|---|
| R1 — invariant de troncature, données réelles, 5 points de grille dont le mode à état | **PASSÉ**, 0 fuite, couche indicateur couverte | `backtests/causality.txt` |
| R5 — conformance backtest/live | **PASSÉ** (modes `breakout` et `equilibrium`) | `backtests/conformance.txt` |
| R3 — stop obligatoire du bon côté, RR conforme | **PASSÉ** | `test_strategy.py` |
| Cellule neutre = v1, signal par signal | **PASSÉ** (784/784) | `backtests/grid.txt` § 1 |
| 19 tests unitaires (commutateurs, causalité du biais, bornes) | **PASSÉS** | `test_strategy.py` |

Le mode `equilibrium` porte un balayage à état (un setup en attente à la fois).
C'est exactement le genre de code où une fuite se cache : R1 y a été passé sur
données réelles, pas seulement sur synthétique.

---

## 5. Où lire les résultats

`research/VERDICT.md`. Les critères de falsification, eux, sont dans
`research/FALSIFICATION.md` — à lire avant le verdict, pas après.

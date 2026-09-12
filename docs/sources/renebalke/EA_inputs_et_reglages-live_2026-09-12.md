# René Balke — ses six EA : entrées documentées, réglages live, reproductibilité

**Sources** : les six archives publiques de bmtrading.de téléchargées par Adrian le
2026-09-12 (`[IC] <nom> EA.zip`, chacune = un `.ex5` compilé + « Inputs.pdf » EN/DE),
la vidéo « In 48 Minutes I show you how I made €100,000 » (`qgsi-u0kOVw`, réglages live
dictés un par un), les billets de blog « 10-Year Backtest of My Live Trading Portfolio »
(2026-06-23) et « ATR Candle Breakout EA » (2026-06-09).
**Ce qui a été fait** : archives décompressées hors dépôt, guides lus intégralement
(copiés sous `ea_inputs/`), binaires inspectés sans exécution — **les `.ex5` sont
chiffrés** (80 à 120 chaînes aléatoires par binaire ; seuls lisibles : le copyright 2022-2025, l'URL bmtrading.de et, pour Ninja Turtle, la dépendance `Indicators\Free Indicators\Donchian Channel.ex5` — aucun nom d'entrée ni défaut).
Les défauts d'usine restent donc inconnus ; **les réglages qu'il trade en live, eux,
sont connus** — il les dicte. **Aucun jugement ici** : extraction et reproductibilité.

---

## 1. Ce que le compte live contient (vidéo `qgsi-u0kOVw`, blog)

- Compte ouvert mars 2024, IC Trading, VPS, 100 % automatisé. Signal Myfxbook «
  track record verified ». ~4 000 trades, taux de réussite légèrement > 50 %, **profit
  factor 1,16**, drawdown max **22 k€**, espérance **22 €/trade**, commissions + swaps
  ≈ 10 % du brut (111 k€ brut → ~100 k€ net). Retrait de 50 k€ le jour de la vidéo ;
  capital laissé ~20 k€ pour ~1,3 k€ de marge utilisée.
- **Quatre stratégies**, dans un seul EA portefeuille en live. Backtest 10 ans (Dukascopy
  tick, qualité 100 %) : +735 k€ **après ~200 k€ de frais**, chaque année positive
  (7 k€ → 162 k€), pire DD 45 k€ (2016). Sur les deux ans communs : **backtest 119,6 k€
  contre live 88,5 k€** (un tiers de plus, expliqué par ses changements de réglages :
  EURUSD abandonné, filtres de range retirés, Go Long d'abord limité aux nouveaux
  plus-hauts), **DD max 22,9 k€ en test contre 22,1 k€ en live**.
- Répartition (son journal Trade Buddy) : Go Long > 50 % du profit ; Turnaround Tuesday
  160 trades, +16 k€ ; Range Breakout 2 300 trades, +25,5 k€, PF 1,09, DD 10 k€ —
  **l'or et USDJPY portent tout, GBPUSD négatif sur 2,5 ans, DE40 à zéro, US30 −1,5 k€,
  EURJPY en plus gros DD** ; ATR Candle Breakout 55 trades, WR < 30 %, gain moyen 370 /
  perte 90, série de 12 pertes.

## 2. Les six EA — entrées et réglages live

### 2.1 Go Long EA (indices, D1 déclaré, exécution intraday)
**Règle** : achat à heure fixe chaque jour, clôture à heure fixe ; option « nouveau
plus-haut du jour ». Entrées : `Wait For New Day High` ; volume (FIXED / MANAGED /
PERCENT / MONEY) ; TP et SL en mode OFF / PERCENT / POINTS ; heures d'ouverture et de
clôture ; break-even et trailing (mode, déclencheur, distance, pas) ; magic, commentaire.
**Live** : US30 et US Tech ouvrent **01:05**, ferment **23:50** ; DE40 **09:05 → 22:55**
(spread nocturne 4× plus cher) ; **ni SL ni TP**, pas de trailing, pas de filtre nouveau
plus-haut ; « risque » **50 000 €** = dimensionnement notionnel (perte si l'indice va à
zéro). Motif de la réouverture quotidienne : swap overnight ≈ 6 %/an sur DE40 s'il
tenait une position permanente, et éviter les gaps de week-end.
**Reproductible tbot** : oui, position unique — mais **sans stop**, ce qui exige la
doctrine du 2026-09-12 (règles propres) et un stop de portefeuille ; données : indices
en **intraday** (ouverture 01:05 / clôture 23:50) — DAX et NASDAQ au catalogue, US30
absent. MT5 est en ligne : H1 indices à charger.

### 2.2 Turnaround Tuesday EA (indices)
**Règle** : achat un jour de semaine choisi, clôture un autre jour ; filtre MA optionnel
(timeframe, période, méthode, prix appliqué) ; mêmes blocs volume / TP-SL / BE-TSL.
**Live** : ouverture **lundi 01:05** (DE40 09:05), clôture **mardi 23:50** (DE40 22:55) ;
condition : **prix sous la SMA journalière** — 25 périodes US30, **9** US Tech, **40**
DE40, sur le close ; **ni SL ni TP** ; risque notionnel **25 000 €**.
**Reproductible tbot** : oui (position unique, filtre D1, horaires intraday) — mêmes
réserves que Go Long (pas de stop, données intraday indices).

### 2.3 Range Breakout EA (forex, indices, or) — **= S009**
**Règle** : range entre deux heures (calcul en M1), ordres stop des deux côtés ± buffer,
SL/TP en OFF / FACTOR (× range) / PERCENT / POINTS, expiration des ordres, clôture à
heure fixe, BE/TSL, plafonds de trades par jour, filtres de taille de range.
**Live** (7 graphiques, risque 500 € sauf mention) :

| Instrument | Range | SL | Clôture | Particularités |
|---|---|---|---|---|
| USDJPY | 03:00-06:00 | autre bord | 18:00 / 18:55 | 1 trade/jour, pas de filtre |
| GBPUSD | 04:00-11:30 | autre bord | 18:00 | — |
| DE40 | 10:35-13:05 | **1,5 % du prix** | 20:55 | risque 375 € ; **BE à +0,2 %** ; filtre range **0,25-0,45 %** |
| US30 | 13:35-16:05 | **0,5 %** | 20:55 | risque 125 € ; filtre range 0,25-0,45 % |
| XAUUSD | 03:05-06:05 | **1 %** | 18:55 | pas de filtre |
| EURJPY | 04:00-10:00 | autre bord | 18:00 | — |
| EURUSD | — | — | — | **abandonné** (+1,5 k€, filtre de range trop restrictif) |

**Chez nous** : S009 a reproduit la version H1 (entrée au close, sortie temporelle
approximée) et rendu « pas d'edge » sur USDJPY/GBPUSD ; **son propre live dit la même
chose sur GBPUSD, DE40 et US30** et attribue le profit à l'or et USDJPY. La version
distribuée v1.40 (ordres stop M1, buffer, trois modes de stop, BE, filtres) n'est pas
celle mesurée par S009 — l'écart d'exécution est connu (`S009/research/VERDICT.md`).

### 2.4 ATR Candle Breakout EA (or, H1) — **le plus complet et le plus prouvé**
**Règle** : bougie close > `ATR Multiplier` × ATR(`ATR Period`) sur le timeframe de
signal, **fermant à moins de `Close proximity` % de son extrême** (haut pour achat, bas
pour vente), corps ≥ `Min body-to-range` % ; suit le sens de la bougie. Filtres
optionnels : tendance MA HTF, confirmation ATR multi-timeframe, fenêtre horaire (avec
exclusions vendredi/lundi), filtre S/R (swing highs/lows, zone × ATR, nombre de
touches). SL et TP **en % du prix d'ouverture**, risque en montant fixe, trailing
optionnel (déclencheur %, pas %).
**Live** : **H1, ATR 200, × 2,5, clôture dans le quart extrême (25 %)**, filtres tous
désactivés, **TP 2 %, SL 0,5 % (RR 4)**, risque **100 €**. Blog : 11 ans d'or en tick
réel **+19 527 € sur 50 k€, PF 1,15, DD ~9,6 %, 1 552 trades, WR ~23 %** ; live depuis
mars 2026 : **24 trades +516 € contre 23 trades +634 € en test**, WR 25,0 % / 26,1 %,
DD 1 139 € / 1 028 €.
**Reproductible tbot** : **oui, maintenant** — position unique, stop et cible en %,
or H1 en cache (30 000 barres), et deux références publiées à confronter (backtest
11 ans, comparaison live). C'est le candidat **S022**. Inconnues à fixer avant mesure :
`Min body-to-range` (valeur live non dite — 0 = désactivé est l'hypothèse fidèle),
`Slippage (points)`.

### 2.5 Ninja Turtle Scalper EA (forex majeures, M1-M15) — **pas dans son compte live**
**Règle** : cassure de canal de Donchian (`DcTimeframe`, `DcPeriod`), déclencheur au tick
(`TRIGGER_TICK`) ou à la clôture de barre (`TRIGGER_M1`, `TRIGGER_DC_BARS`) ; TP/SL en
% ; trailing serré (déclencheur %, distance %, pas %) ; volume fixe ou par montant. Le
site prévient : *« very tight trailing stop — slippage can occur »*.
**Reproductible tbot** : cassure = famille de la v1 (S011) ; le déclencheur **au tick**
et le trailing serré ne sont pas exprimables par le moteur (barres closes, sortie
unique — TCK-014). Aucun réglage live, aucun résultat publié : à traiter en dernier.

### 2.6 The Fisherman EA (forex, indices, M15-H4) — **pas dans son compte live**
**Règle** : repli contre-tendance de `Retracement Percent` dans une tendance définie par
MA (timeframe, périodes, méthode, prix) et/ou RSI (timeframe, périodes, niveau) ; TP/SL
en % (0 = désactivé) ; clôture à heure fixe optionnelle ; BE/TSL en %. Sens autorisés
(achat/vente).
**Reproductible tbot** : oui (position unique, filtres MA/RSI, sorties %) — mais
**aucune valeur live, aucun résultat publié** : rien contre quoi se comparer. Grille
ouverte, donc multiplicité maximale ; à traiter après les stratégies prouvées.

## 3. Ordre de reproduction — état au 2026-09-13

| Priorité | Stratégie | Pourquoi | Ce qu'il faut | Verdict |
|---|---|---|---|---|
| 1 | **ATR Candle Breakout — or H1** (S022) | spécification complète, réglages live connus, **backtest et comparaison live publiés** | rien : moteur et données prêts | mesurée : ÉCHEC au sens des critères écrits d'avance (0/12 STRICT, cellule live −10,4 R OOS), fidélité tenue — `strategies/S022_balke_atr_candle/research/VERDICT.md` |
| 2 | **Turnaround Tuesday** — DAX, NASDAQ, US30 (S023) | règle complète, 160 trades live, +16 k€ | H1 indices (MT5 en ligne), pas de stop → stop de portefeuille | mesurée : ÉCHEC (seul le DAX bat le témoin ; NASDAQ/US30 = dérive de l'indice) — `strategies/S023_balke_turnaround_tuesday/research/VERDICT.md` |
| 3 | **Go Long** — DAX, NASDAQ, US30 (S024) | > 50 % de son profit, règle triviale | idem ; le résultat est un bêta indiciel assumé — à mesurer contre « acheter et tenir » comme témoin, pas contre le hasard | mesurée : réussite en tant que bêta indiciel, pas d'edge de timing (fidèle +47,9/+71,4/+43,5 % sur 5 ans ; overnight négatif) — `strategies/S024_balke_go_long/research/VERDICT.md` |
| 4 | Range Breakout v1.40 fidèle (ordres stop M1, buffer, BE) | reprise de S009 avec l'exécution réelle | données M1 indices/or, ordres stop dans le moteur | à faire |
| 5 | Fisherman, Ninja Turtle | pas de réglages ni de preuve | à instruire seulement après les quatre autres | à faire |

Chacune avec `FALSIFICATION.md` écrite avant la première mesure, témoin aléatoire, et
— pour S022 — la comparaison directe à ses chiffres publiés comme test de fidélité.

# Cache intraday indices + ajout US30 — 2026-09-12

> Mesuré le 2026-09-12 (samedi — terminal Swissquote MT5 connecté mais marché
> fermé ; les valeurs `spread` instantanées de `symbol_info()` sont donc
> gonflées et notées comme telles). Les médianes de spread ci-dessous portent
> sur les barres H1/D1 historiques (colonne `spread` de `copy_rates_range`,
> en points), pas sur l'instantané du weekend.

## 1. Ce qui a été fait

- Chargement (`core.data.source.load_bars`) et mise en cache H1 sur 1855 jours
  (~5 ans + marge) pour `NASDAQ`, `DAX`, `SP500`, `US30`, et D1 1855 jours
  pour `US30`. Cache : `C:\db\tradingBot\bars_cache\`.
- Ajout de `US30` (`#US30` côté broker) à la plateforme :
  - `app/core/data/source.py` `SYMBOL_MAP["US30"] = "#US30"`.
  - `app/core/data/instruments.py` `_CATALOG["US30"]` (voir §3).
  - `app/tests/test_instruments.py` (nouveau fichier — aucun test ne couvrait
    encore ce module).
- **Aucune modification** des lignes `NASDAQ` / `DAX` / `SP500` du catalogue
  (elles servent d'autres stratégies) — simple mesure comparative (§4).

## 2. Faits MT5 bruts — `#US30` (+ `#NAS100`, `#DE40` pour comparaison)

Relevé via `mt5.symbol_info()`, terminal Swissquote MT5 connecté
(`terminal_info().connected = True`, compte `5209556`, devise **CHF**).

| Champ | `#US30` | `#NAS100` | `#DE40` |
|---|---|---|---|
| `description` | Spot US 30 | Spot US Tech 100 | Spot Germany 40 |
| `path` | `CASH CFD\#US30` | `CASH CFD\#NAS100` | `CASH CFD\#DE40` |
| `digits` | 2 | 2 | 2 |
| `point` | 0.01 | 0.01 | 0.01 |
| `spread` (instantané, **samedi → gonflé**) | 400 pts → 40.0 pips | 195 pts → 19.5 pips | 380 pts → 38.0 pips |
| `spread_float` | true | true | true |
| `trade_contract_size` | 1.0 | 1.0 | 1.0 |
| `trade_tick_size` | 0.01 | 0.01 | 0.01 |
| `trade_tick_value` (profit) | 0.0081637 | 0.0081637 | 0.0094678 |
| `trade_tick_value` (loss) | 0.008166 | 0.008166 | 0.0094704 |
| `currency_base` / `profit` / `margin` | USD / USD / USD | USD / USD / USD | EUR / EUR / EUR |
| `trade_mode` | 4 (`FULL`) | 4 (`FULL`) | 4 (`FULL`) |
| `volume_min` / `max` / `step` | 1.0 / 200.0 / 1.0 | 1.0 / 200.0 / 1.0 | 1.0 / 200.0 / 1.0 |

**Horaires de session** : `mt5.symbol_info_session_trade()` n'existe pas dans
ce package Python `MetaTrader5` (5.0.5735 — vérifié via `dir(mt5)`, aucun
attribut contenant `session`). Les horaires ont donc été déduits
empiriquement des barres H1 (§4), pas de l'API de session.

**Note conversion pip** : `digits=2` / `point=0.01` pour les trois symboles →
même convention que le catalogue existant (NASDAQ/DAX : `pip=0.1` = 10
points). `trade_tick_value` est exprimé en **devise de profit** (USD pour
US30/NAS100, EUR pour DE40), pas en CHF (devise du compte) — cohérent avec la
divergence déjà signalée dans `instruments.py` pour les paires GBP/NZD
(entrées historiques en USD, pas CHF).

## 3. Ligne ajoutée au catalogue — `US30`

```python
"US30": dict(pip=0.1, spread_pips=35.0, max_spread_pips=87.5, pip_value_per_lot=1.0),
```

- `pip=0.1` : aligné sur NASDAQ/DAX/SP500 (même `digits=2`/`point=0.01` MT5).
- `pip_value_per_lot=1.0` : aligné **par convention** sur les autres indices
  du catalogue, **pas recalculé** depuis `trade_tick_value` (qui donnerait
  ≈0.082 USD/lot pour 1 pip = 10 points × 0.0081637 — très inférieur à 1.0).
  Écart signalé pour audit, non corrigé ici (même traitement que la note
  USD/CHF déjà présente sur les croisées GBP/NZD) : le corriger changerait le
  sizing de toute stratégie qui consommerait cette entrée.
- `spread_pips=35.0` : médiane du spread H1 sur les 365 derniers jours
  (5902 barres, 2025-09-11 → 2026-09-11), mesurée le 2026-09-12 — voir §4.
- `max_spread_pips=87.5` : 2.5× la médiane, convention du fichier.

## 4. Barres chargées, sessions observées, spreads mesurés

### 4.1 NASDAQ (`#NAS100`) — H1

- 29 954 barres, 2021-08-16 00:00 → 2026-09-11 22:00 (heure serveur).
- **24/24 heures présentes** (0-23) — le CFD cote en continu du lundi au
  vendredi, + 18 barres résiduelles le dimanche (ouverture anticipée de
  semaine).
- Répartition hebdo : Lun 5900, Mar 6072, Mer 6031, Jeu 6001, Ven 5932,
  Dim 18 — cohérent avec une cotation quasi-continue (léger déficit le lundi,
  probablement ouverture tardive de semaine).
- Spread médian (365j, 5906 barres) : **12.0 pips** global — 00-08h : 12.0,
  08-16h : 12.0, 16-24h : 9.5 (session US la moins large, cohérent avec la
  liquidité de la séance cash américaine).
- **Vs catalogue (8.0 pips)** : ratio **×1.5** — le spread réellement mesuré
  est 50 % plus large que la valeur codée en dur. Catalogue **non modifié**
  (autres stratégies en dépendent) — signalé pour arbitrage ultérieur.

### 4.2 DAX (`#DE40`) — H1

- 18 121 barres, 2021-08-16 08:00 → 2026-09-11 21:00.
- **Seulement 14/24 heures présentes (8h → 21h)**, aucune barre le dimanche.
  **Réponse à la question de la tâche : `#DE40` NE trade PAS 24h — c'est une
  session fermée type Xetra/Eurex élargie (08:00-21:59 heure serveur),
  fermée le week-end**, contrairement aux indices US ci-dessous.
- Répartition hebdo : Lun 3582, Mar 3668, Mer 3634, Jeu 3654, Ven 3583 (≈14h ×
  5j ≈ 70 barres/semaine attendues, cohérent sur ~260 semaines).
- Spread médian (365j, 3535 barres) : **23.0 pips** global (08-16h : 23.0,
  16-24h : 23.0 ; 00-08h : aucune barre, marché fermé).
- **Vs catalogue (8.0 pips)** : ratio **×2.88** — écart net, le catalogue
  sous-estime largement le spread réel du DAX. Catalogue **non modifié**.

### 4.3 SP500 (`#US500`) — H1 (contexte, non demandé pour le ratio)

- 29 958 barres, 2021-08-16 00:00 → 2026-09-11 22:00, **24/24 heures**
  présentes, + 18 barres dimanche — même profil que NASDAQ (indices US en
  cotation quasi-continue).
- Spread médian (365j, 5900 barres) : **6.0 pips** global (00-08h : 6.0,
  08-16h : 6.0, 16-24h : 3.5). Catalogue = 5.0 pips → ratio ×1.2 (mentionné
  pour contexte, catalogue non modifié).

### 4.4 US30 (`#US30`) — H1

- 29 957 barres, 2021-08-16 00:00 → 2026-09-11 22:00.
- **24/24 heures présentes** (0-23) + 18 barres dimanche — **même profil de
  session que NASDAQ/SP500** : les trois indices US cotent quasi en continu
  sur ce broker, contrairement au DAX.
- Répartition hebdo : Lun 5901, Mar 6072, Mer 6037, Jeu 6001, Ven 5928,
  Dim 18.
- Spread médian (365j, 5902 barres) : **35.0 pips**, stable sur les trois
  bandes horaires (00-08h : 35.0, 08-16h : 35.0, 16-24h : 35.0) — spread
  large et peu variable intrajournalier, cohérent avec un indice moins
  arbitré que NASDAQ/SP500 sur ce broker.

### 4.5 US30 — D1

- 1331 barres, 2021-08-16 → 2026-09-11.
- Répartition hebdo : Lun 261, Mar 265, Mer 263, Jeu 263, Ven 261, Dim 18
  (barres D1 résiduelles dominicales — même artefact d'ouverture anticipée
  qu'en H1).
- Spread médian (365j, 264 barres) : 25.0 pips (mesure sur barre D1 — moins
  significative que le H1, un seul point par jour ; fournie car demandée par
  la tâche, à ne pas utiliser comme référence de coût intrajournalier).

## 5. Réserves et limites

- **Snapshot week-end** : les valeurs instantanées `symbol_info().spread`
  (§2) sont mesurées un samedi, marché fermé — gonflées de façon connue et
  documentée (pas utilisées pour la ligne catalogue, seulement pour la
  cohérence d'ordre de grandeur avec la médiane annuelle H1, qui elle est
  fiable).
- **API de session absente** : `mt5.symbol_info_session_trade()` n'existe
  pas dans la version du package `MetaTrader5` installée (5.0.5735) — les
  horaires de session sont déduits des heures effectivement présentes dans
  les barres historiques, pas de l'API native. Si une future version du
  package l'expose, une mesure directe serait plus rigoureuse (les barres ne
  distinguent pas "fermé" de "aucune activité mais coté").
- **`pip_value_per_lot=1.0` non recalculé** : voir §3 — écart avec la valeur
  théorique dérivée de `trade_tick_value` documenté mais pas corrigé, pour
  rester cohérent avec la convention déjà en place sur les autres indices.
- **Ratios NASDAQ/DAX vs catalogue** (§4.1, §4.2) : signalés, catalogue
  **volontairement non modifié** (consigne de la tâche — d'autres stratégies
  dépendent de ces lignes). À arbitrer séparément si jugé pertinent.
- **Corrobore TCK-018** (`tickets/TCK-018_spread-reel-vs-catalogue.md`, ouvert
  2026-09-06, cc-support → cc-spec) : ce ticket documentait déjà un facteur
  ×2,0-2,2 mesuré sur XAUUSD entre spread catalogue et spread réel des
  barres. Les ratios NASDAQ (×1.5) et DAX (×2.88) mesurés ici vont dans le
  même sens — le problème n'est pas propre à l'or, il touche au moins deux
  indices. N'a pas été traité ici (hors scope T3, ticket déjà adressé à
  cc-spec) ; ajouté pour information.

# PHASE_A_LOG — S017 ireland_gex

**Dernier run** : 2026-08-26 17:49 — `python research/phase_a.py` (relançable à volonté ; recharge TOUS les jours snapshotés et réécrit ce fichier)

## Inventaire données

- Snapshots GEX (pré-market canoniques) : **1 jour(s)** — 2026-08-26 (negative, majeurs 760/765)
- OHLCV 5min : 2026-06-02 → 2026-08-26 (60 jours, 4626 barres RTH)
- Collecte planifiée : tâche Windows 14:55 CH jours ouvrés → C:/db/tradingBot/S017/

**Qualité données :**

- 2026-08-26 : 2 captures « premarket » le même jour — le fichier canonique correspond à la DERNIÈRE (asof 2026-08-26 15:28:18, spot 766.27) ; si capturé après l'open, les contacts H1 de ce jour sont à interpréter avec prudence.

## Mesures

### H1 — réaction aux niveaux (premier contact, tous jours agrégés)

| horizon | groupe | n | P(hold) [IC 95%] | rejet médian (ATR) | pénétration médiane (ATR) |
|---|---|---|---|---|---|
| 15min | major | 1 | 0% [0-79%] | 0.47 | 4.17 |
| 30min | major | 1 | 0% [0-79%] | 0.47 | 4.87 |
| 60min | major | 1 | 0% [0-79%] | 0.47 | 4.87 |


### H2 — régime gamma pré-market vs comportement réalisé (1 pt/jour)

| régime | n jours | RV 5min médiane (%) | range médian (%) | efficience médiane |
|---|---|---|---|---|
| negative | 1 | 0.20 | 0.30 | 0.46 |

Jours (détail) :

| date       | regime   |   net_gex_musd |   n_bars | partial   |   rv_pct |   range_pct |   efficiency |
|:-----------|:---------|---------------:|---------:|:----------|---------:|------------:|-------------:|
| 2026-08-26 | negative |          -5203 |       24 | True      |    0.203 |       0.298 |        0.461 |

### Setups A+ (checklist 5 conditions, jours snapshotés uniquement)

**0 setup complet** sur 1 jour(s) snapshoté(s). Attendu à ce stade : la checklist est très sélective (la vidéo revendique 2-3 setups A+/semaine).

## Verdicts provisoires

| hypothèse | n actuel | seuil de mesure | verdict |
|---|---|---|---|
| H1 (réaction niveaux) | 1 contacts majeurs / 1 jour(s) | ≥ 100 contacts (≈ 20-30 jours) | **n insuffisant** — plomberie validée, aucun verdict |
| H2 (régime vs RV) | 0 jour(s) + / 1 jour(s) − | ≥ 60 jours, les 2 régimes représentés | **n insuffisant** |
| Setups A+ | 0 setup(s) sur 1 jour(s) | ≥ 30 setups (H4 non conclusif en deçà) | **n insuffisant** |

## Validation croisée externe (best-effort, 2026-08-26)

Aucun dashboard GEX gratuit sans compte n'est lisible par simple requête HTTP : GravityGEX et FlashAlpha renvoient des pages vides (rendu JS côté client), AlgoStorm est derrière un challenge Cloudflare (non contourné — interdit). **Passé** ; la seule validation externe reste la comparaison visuelle bootstrap avec les frames ITMatrix de la vidéo (géométrie des niveaux concordante).

## Jalons attendus

- **n ≥ 5 jours** : rodage agrégation multi-jours ; premiers ratios hold major vs placebo (bruit dominant, aucun verdict) ; vérifier que chaque jour produit 2-5 majeurs et des contacts.
- **n ≥ 20 jours** : ~50-100 contacts majeurs attendus → première lecture H1 avec IC exploitables ; H2 encore court (viser 60 j) ; premiers setups A+ si le marché en offre.

*Étude de signal Phase A — pas un backtest (R9). Coûts, slippage et sizing absents par construction.*
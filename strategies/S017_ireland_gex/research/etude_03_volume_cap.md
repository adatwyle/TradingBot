# Étude 03 — fenêtre de volume bornée (H3/H3b) + compression — 2026-08-26

Données : SPY 5min RTH 2026-06-02 → 2026-08-26 (60 jours, 4626 barres). Cassures de compression TOUTES (condition GEX exclue — isole l'effet volume).
Défauts compression : 6 barres ≤ 1.5×ATR14. Total cassures : **134**.

Variantes déclarées avant mesure : `vol_mult` (plage manifest), `vol_cap` (H3b, spec §3.5 déclarée 2026-08-26), grille compression (plages manifest). **Nombre total de variantes balayées : 16 fenêtres volume + 16 définitions compression** — à corriger pour comparaisons multiples dans toute interprétation (aucun seuil ne sera promu défaut sur ce seul balayage).

## 1. Fenêtre de volume `[vol_mult, vol_cap)` — compression par défaut

| fenêtre | n | +1R avant stop [IC 95%] | stoppé | MFE médiane (R) |
|---|---|---|---|---|
| toutes cassures (référence) | 134 | 33% [25-41%] | 34% | 0.67 |
| < 1.2× (anti-population) | 105 | 31% [23-41%] | 35% | 0.66 |
| [1.2, ∞) | 29 | 38% [23-56%] | 31% | 0.68 |
| [1.2, 2.0) | 18 | 44% [25-66%] | 28% | 0.83 |
| [1.2, 2.5) | 24 | 42% [24-61%] | 29% | 0.77 |
| [1.2, 3.0) | 25 | 40% [23-59%] | 28% | 0.74 |
| [1.5, ∞) | 18 | 39% [20-61%] | 33% | 0.61 |
| [1.5, 2.0) | 7 | 57% [25-84%] | 29% | 1.01 |
| [1.5, 2.5) | 13 | 46% [23-71%] | 31% | 0.87 |
| [1.5, 3.0) | 14 | 43% [21-67%] | 29% | 0.78 |
| [2.0, ∞) | 11 | 27% [10-57%] | 36% | 0.48 |
| [2.0, 2.5) | 6 | 33% [10-70%] | 33% | 0.61 |
| [2.0, 3.0) | 7 | 29% [8-64%] | 29% | 0.54 |
| [2.5, ∞) | 5 | 20% [4-62%] | 40% | 0.32 |
| [2.5, 3.0) | 1 | 0% [0-79%] | 0% | 0.48 |

### Lecture H3b (tranche épuisement)

- Tranche 1.5-2.0× : n=7, +1R 57%
- Tranche ≥ 2.0×  : n=11, +1R 27%

## 2. Sous-population 5min-EMA-alignée (plus proche du système réel)

| fenêtre | n | +1R avant stop [IC 95%] | stoppé | MFE médiane (R) |
|---|---|---|---|---|
| alignées, toutes | 57 | 21% [12-33%] | 21% | 0.57 |
| alignées, ≥ 1.5× | 4 | 50% [15-85%] | 0% | 0.74 |
| alignées, [1.5, 2.0) | 2 | 100% [34-100%] | 0% | 1.02 |
| alignées, ≥ 2.0× | 2 | 0% [0-66%] | 0% | 0.40 |

## 3. Définitions de compression (cassures à volume ≥ 1.5×, sans cap)

| compress_bars | range ≤ ×ATR | n cassures | n vol≥1.5× | +1R [IC 95%] | stoppé |
|---|---|---|---|---|---|
| 4 | 1.0 | 55 | 3 | 0% [0-56%] | 33% |
| 4 | 1.5 | 375 | 56 | 30% [20-43%] | 34% |
| 4 | 2.0 | 554 | 93 | 23% [15-32%] | 30% |
| 4 | 2.5 | 613 | 103 | 20% [14-29%] | 30% |
| 6 | 1.0 | 8 | 0 | - | - |
| 6 | 1.5 | 134 | 18 | 39% [20-61%] | 33% |
| 6 | 2.0 | 297 | 51 | 27% [17-41%] | 31% |
| 6 | 2.5 | 375 | 70 | 26% [17-37%] | 33% |
| 8 | 1.0 | 0 | 0 | - | - |
| 8 | 1.5 | 42 | 1 | 0% [0-79%] | 0% |
| 8 | 2.0 | 170 | 26 | 27% [14-46%] | 31% |
| 8 | 2.5 | 258 | 53 | 28% [18-42%] | 30% |
| 12 | 1.0 | 0 | 0 | - | - |
| 12 | 1.5 | 4 | 0 | - | - |
| 12 | 2.0 | 44 | 10 | 20% [6-51%] | 30% |
| 12 | 2.5 | 106 | 21 | 19% [8-40%] | 29% |

## Verdict provisoire

- Les n par cellule restent faibles : **rien n'est établi** ; ce balayage sert à suivre la stabilité des directions d'effet au fil de l'accumulation quotidienne.
- Décision de promotion d'un seuil en défaut : uniquement si la direction persiste avec n ≥ 30 par tranche ET après correction pour le nombre de variantes balayées.

*Relançable : `python research/etude_03_volume_cap.py` — réécrit ce fichier sur toutes les données accumulées.*
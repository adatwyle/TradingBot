# s09 — Conditions de falsification, figées AVANT le premier backtest

> Date de gel : 2026-08-17. Aucun backtest de la stratégie n'a été exécuté au
> moment où ce fichier est écrit. Seules les mesures de DONNÉES de
> `research/economics.py` (fuseau, taille de range, drag, heure de cassure)
> existent. Toute modification de ce fichier après le premier backtest serait
> une falsification au sens inverse du terme.

## Convention statistique (audit 2026-08-17, D2/D3)

La convention « X STRICT vs n×0,05 attendues » est **ininterprétable**
(dispersion sous-estimée ×3, cellules corrélées). **La référence de ce dossier
est le bras témoin empirique** (`attach_control_arm`, 200 tirages, graine
20260816), exécuté avec les MÊMES `engine_kwargs` que la stratégie
(max_hold_bars, cooldown). Le comptage STRICT est rapporté pour archive, jamais
comme évidence.

## Le claim à confronter

Transcript `03` (USDJPY 3h-6h, SL = range opposé, pas de TP, clôture 18h,
1 breakout/jour, 10 ans Dukascopy) : PF 1,27, WR < 50 %, gain moyen 2 888 vs
perte moyenne 1 800 → **espérance implicite ≈ +0,15 R/trade net**, ~250
trades/an.

## Économie a priori (mesurée avant implémentation, economics.txt)

| Instrument | SL = range : drag | SL = 1 % : drag | péage attendu (R/trade) |
|---|---|---|---|
| USDJPY | 9,12 % | 1,91 % | 0,091 / 0,019 |
| GBPUSD | 4,70 % | 1,71 % | 0,047 / 0,017 |
| XAUUSD | 3,27 % | 1,23 % | 0,033 / 0,012 |
| EURJPY | 12,08 % | 2,26 % | 0,121 / 0,023 |

**Constat a priori important** : la thèse « son stop = le range, donc large,
donc drag faible » est **fausse sur USDJPY avec SL=range** (30,7 pips médians →
drag 9,1 %, du même ordre que le péage qui a tué s91). Elle n'est vraie que
pour la variante SL = 1 % (~146 pips). Si son claim +0,15 R/trade net est réel
avec SL=range, le signal brut doit valoir ≈ +0,24 R/trade — soit **5× l'effet
de session mesuré par s91 (+0,05 brut)**. Je l'écris avant de mesurer : c'est
une exigence forte, et le résultat le plus probable a priori est entre les
deux.

## Falsifications

| # | Condition | Seuil déclaré | Si déclenchée |
|---|---|---|---|
| **F1** | **Témoin mesuré** : la config par défaut USDJPY (3-6h, SL=range, 1 breakout, sans filtre, clôture 18h) sur son `honest_r` OOS vs 200 tirages aléatoires à dispositif identique (mêmes engine_kwargs) | percentile **< 95** | PAS D'EDGE (le timing n'apporte rien au-delà du dispositif de risque) |
| **F2** | **Contrôle long/short** USDJPY : côté short ≤ 0 R/trade ET le long porte l'essentiel, asymétrie alignée sur la dérive yen (+4 932 pips sur l'échantillon) | short ≤ 0 et long > 80 % du total positif | le claim USDJPY est du **beta yen**, pas un edge de session |
| **F3** | **Permutation horaire** à instrument constant, géométrie et spread figés (spread nul) : range 9-12h clôture 21h vs range 3-6h clôture 18h | apport de l'ancrage 3-6h ≤ 0 R/trade | la thèse « session » tombe — c'est un breakout quelconque, famille déjà tuée (s11) |
| **F4** | **Ablation du spread** : edge brut (spread nul) ≥ 1,5 × péage mesuré (réel − nul) sur la config par défaut | brut < 1,5 × péage | non exécutable chez Swissquote — même mort que s91, effet de session enterré côté breakout |
| **F5** | **Conformité inverse GBPUSD** (config figée : 4-12h, SL=range, 1 breakout, sans filtre, clôture 18h — ses réglages `15`) : période pré-live (→ 2024-03-31) vs post-live (2024-04-01 →). Le harnais (WF + témoin) doit **rejeter** cette config ex ante ; le post-live doit être négatif (ses −8 778 € / ~360 trades ≈ **−17,6 R** à 500 €/trade de risque) | si notre harnais la déclare robuste → **c'est NOTRE méthode qui a un problème** — livrable en soi, dans les deux sens | documenté quel que soit le sens |
| **F6** | **Effectif** : ≥ 20 trades OOS médians par instrument | < 20 | NON CONCLUSIF, sans négociation |

## Grille (figée)

USDJPY (24 cellules) : fenêtre {3-6, 3-5}, SL {range, 1 % de l'entrée, 1 % du
bord du range}, breakouts {1, 2}, filtre {off, 0,2-0,4 %}. Clôture 18h
(max_hold_bars=11, non balayé — c'est le contrat).
XAUUSD (6) : fenêtre 3-6, SL {range, 1 % entrée, 1 % range} × filtre
{off, 0,15-0,85 %}. Clôture 19h (max_hold_bars=12).
GBPUSD (2) : fenêtre {4-12, 4-11} — réplication de SA config, pas une
optimisation. SL=range, 1 breakout, sans filtre. max_hold_bars=5.
EURJPY (1) : config par défaut USDJPY — témoin d'échec documenté (−2,5 k€).

`engine_kwargs` : `max_hold_bars` par instrument ci-dessus,
`cooldown_bars=0` (il trade tous les jours), `cb_losses=999` (pas de circuit
breaker chez lui — fidélité source ; le témoin reçoit les mêmes kwargs).

## Dégradations déclarées (avant mesure)

1. **Entrée au close H1** au lieu du stop order intrabar au bord du range :
   entrée retardée jusqu'à ~1h, prix pire que le bord, mais distance de risque
   mesurée depuis l'entrée réelle. Dégradation défavorable au signal — une
   réfutation de cette version ne réfute pas totalement la version M1.
   Le RANGE lui-même est exact (high/low H1 = high/low M1 sur la même fenêtre
   à bornes pleines).
2. **Sortie 18h approximée par max_hold_bars fixe** (barres depuis l'entrée) :
   exacte pour une entrée à la première barre possible, dérive de +1h par
   heure d'entrée plus tardive. Distribution des heures de sortie réelles à
   rapporter dans le VERDICT.
3. Bornes non pleines (4:30, 11:30, 3:05, 18:55) arrondies à l'heure — déclaré
   par cellule.
4. Pas de swap modélisé (positions intraday sauf dérive week-end du point 2).

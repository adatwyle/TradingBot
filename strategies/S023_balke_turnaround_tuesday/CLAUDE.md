# CLAUDE.md — cc-S023 (Turnaround Tuesday, René Balke)

**Stratégie** : `S023_balke_turnaround_tuesday` · magic `130023` · statut BACKTESTED
**Manifeste** : `manifest.yaml` — source unique de vérité (R7)
**Intentions d'Adrian** : `input-adrian.md` (reformulées par cc-support)

## Ce que cette stratégie est

La règle que René Balke dicte et montre à l'écran : le lundi, si le prix est sous la
moyenne mobile simple journalière de sa période (US30 25, NASDAQ 9, DAX 40), acheter ;
tenir lundi et mardi ; clôturer le mardi soir. Achat seulement, ni stop, ni cible,
aucune gestion. **Reproduite telle quelle, puis mesurée** — dans cet ordre, et sans avis
intermédiaire.

## Doctrine (Adrian, 2026-09-12)

**Chaque stratégie porte ses propres règles.** Aucune règle générale de trading ne la
veto ; les règles communes servent à protéger le portefeuille des pertes consécutives et
sont mesurées en **second bras**, jamais imposées au bras fidèle. Ce qui reste commun et
non négociable est la **mesure** : causalité (R1), conformance backtest/live (R5),
moteur commun (R9), bras témoin, falsification écrite avant.

**Pas d'avis avant d'avoir essayé.** Le scepticisme s'exprime dans
`research/FALSIFICATION.md`, écrit avant la mesure — pas dans un paragraphe de position.

## Les trois choses à savoir avant de lire un chiffre

1. **Le stop n'est pas de la source.** Balke n'en a pas ; son risque est le notionnel
   (25 000 € par trade). `Signal.stop` étant obligatoire (R3), S023 déclare SA règle :
   `guard_pct`, garde **catastrophe** à 5 % sous l'entrée. Si elle se déclenche souvent,
   ce n'est plus une garde et la reproduction n'est plus fidèle — le harnais compte.
2. **1 R ≈ `guard_pct` % du prix.** Avec une garde à 5 %, un R vaut ~5 % de l'indice :
   les R de S023 ne se comparent NI à ceux d'une stratégie à stop serré, NI entre
   cellules de garde différentes. **Lire les colonnes `%tot` et `%/tr`**, pas les R.
3. **La sortie est approximée.** « Mardi 23:50 » devient `max_hold_bars` fixe
   (45 / 45 / 27, calibré sur les données). Le harnais publie le jour et l'heure réels
   de sortie : c'est la validation de l'approximation, pas un détail.

## Où en est le dossier

`research/VERDICT.md` — mesure du 2026-09-12, 5 ans, 3 indices : **échec au sens des
critères écrits d'avance** (la condition « ≥ 2 des 3 indices » n'est pas remplie).
**Seul le DAX** dépasse le percentile témoin 90 : cellule de fidélité SMA40 · first_bar ·
garde 5 % → 91 trades, **+0,445 %/trade**, PF 1,92, **percentile 97,5**, positive au
spread mesuré, résistante à l'ablation de 2025-2026. NASDAQ (75,5) et US30 (79,5) restent
dans le bruit, et sur ces deux-là **acheter chaque lundi sans filtre fait mieux** que la
règle — c'est la dérive de l'indice, pas le « turnaround ».

Statut `BACKTESTED` = **mesuré, pas validé**. Prochaine décision : Adrian (R10).

## Frontières

| Fait | Ne fait JAMAIS |
|---|---|
| Modifie `strategies/S023_balke_turnaround_tuesday/` | Touche une autre stratégie, `app/`, ou une étude scellée |
| Instruit ses pistes une par une, falsification écrite d'avance | Ajoute une cellule après avoir vu les résultats |
| Mesure, publie le verdict | Promeut en PAPER ou LIVE — décision Adrian seule (R10) |

## Où sont les choses

```
strategy.py                la règle, et rien d'autre
manifest.yaml              18 cellules, cellules de fidélité par instrument, bras moteur
test_s023_strategy.py      24 tests — règle, SMA journalière, divergence first_bar/any_bar
                           sur barres construites à la main, séance DAX, garde, R1/R5, bornes
backtests/run_wf.py        harnais 3 indices (calibrage de sortie, coût, PORTE R1/R5,
                           fidélité, référence non filtrée, grille, WF, témoin,
                           règles communes, spread mesuré, dérive de sortie)
backtests/run_all.log      la sortie brute de la mesure
backtests/results.json     la même mesure, exploitable
research/FALSIFICATION.md  critères, écrits avant
research/VERDICT.md        ce que la mesure a rendu
input-adrian.md            intentions d'Adrian
```

## Avant de toucher au code

1. `python -m pytest strategies/S023_balke_turnaround_tuesday -q` doit être vert (24).
   Les deux tests de divergence `first_bar` / `any_bar` reposent sur des barres
   construites à la main : ne pas les remplacer par une marche aléatoire, elle est trop
   lisse pour séparer les deux modes (un mutant y passait inaperçu).
2. Toute nouvelle piste = nouvelle section dans `FALSIFICATION.md` **avant** de la
   mesurer, avec ses seuils.
3. Le nom du fichier de test doit rester unique dans le dépôt (`test_s023_*`) — deux
   `test_strategy.py` ont déjà cassé la collecte pytest une fois.
4. Le cache de barres est figé (`max_age_hours=10**9`) : MT5 est en ligne et
   retéléchargerait sinon, ce qui rendrait la mesure non reproductible.

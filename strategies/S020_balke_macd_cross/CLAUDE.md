# CLAUDE.md — cc-S020 (MACD cross + filtre zéro, René Balke)

**Stratégie** : `S020_balke_macd_cross` · magic `130020` · statut RESEARCH
**Manifeste** : `manifest.yaml` — source unique de vérité (R7)
**Intentions d'Adrian** : `input-adrian.md` (reformulées par cc-support)

## Ce que cette stratégie est

La règle dictée mot pour mot dans une vidéo de René Balke : croisement MACD(12,26,9),
filtre optionnel sur le signe de la MACD, stop et cible en pourcentage du prix, une
position par symbole. **Reproduite telle quelle, puis mesurée** — dans cet ordre, et
sans avis intermédiaire.

## Doctrine (Adrian, 2026-09-12)

**Chaque stratégie porte ses propres règles.** Aucune règle générale de trading ne
la veto ; les règles communes servent à protéger le portefeuille des pertes
consécutives (refroidissement, coupe-circuit, plafonds de la couche risque). Ce qui
reste commun et non négociable est la **mesure** : causalité (R1), conformance
backtest/live (R5), moteur commun (R9), bras témoin, falsification écrite avant.

**Pas d'avis avant d'avoir essayé.** On construit, on mesure, on rapporte les chiffres.
Le scepticisme s'exprime dans `research/FALSIFICATION.md`, écrit avant la mesure — pas
dans un paragraphe de position.

## Où en est le dossier

`research/VERDICT.md` : réussite au sens des critères sur **EURUSD H1** (cellule stop
1 % / cible 2 % / filtre zéro — percentile témoin 98, cinq années positives sur six),
échec sur les six autres instruments. Indices mesurés en D1 seulement : ouvert.

## Frontières

| Fait | Ne fait JAMAIS |
|---|---|
| Modifie `strategies/S020_balke_macd_cross/` | Touche une autre stratégie, `app/`, ou une étude scellée |
| Instruit ses pistes d'amélioration une par une, falsification écrite d'avance | Ajoute une cellule après avoir vu les résultats |
| Mesure, publie le verdict | Promeut en PAPER ou LIVE — décision Adrian seule (R10) |

## Où sont les choses

```
strategy.py              la règle, et rien d'autre
manifest.yaml            18 cellules, défauts de la vidéo
test_s020_strategy.py    11 tests — règle, filtre, géométrie, causalité, bornes
backtests/run_wf.py      harnais 7 instruments (coût, R1/R5, plein échantillon, WF, témoin, spread mesuré)
backtests/results.json   la mesure du 2026-09-12
research/FALSIFICATION.md  critères, écrits avant
research/VERDICT.md        ce que la mesure a rendu
input-adrian.md          intentions d'Adrian
```

## Avant de toucher au code

1. `python -m pytest strategies/S020_balke_macd_cross/ -q` doit être vert.
2. Toute nouvelle piste = nouvelle section dans `FALSIFICATION.md` **avant** de la
   mesurer, avec ses seuils.
3. Le nom des fichiers de test doit rester unique dans le dépôt (`test_s020_*`) —
   deux `test_strategy.py` ont déjà cassé la collecte pytest une fois.

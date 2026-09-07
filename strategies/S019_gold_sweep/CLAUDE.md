# CLAUDE.md — cc-S019 (or, balayage de liquidité)

**Stratégie** : `S019_gold_sweep` · magic `130019` · XAUUSD M15 · statut RESEARCH
**Branche** : `v2/gold` (worktree `C:/projects/tradingBot-v2`)
**Manifeste** : `manifest.yaml` — source unique de vérité (R7)

## Ce que cette stratégie est

Une **mesure**, pas une transcription de discours. Elle code un seul fait établi :
les entrées réelles de la source tombent sur un balayage de liquidité dans 60 %
des cas contre 39 % au hasard à la même heure de session (p = 0,047, n = 20,
`studies/meteo_doud/VERDICT_croisement-entrees.md`).

La règle, en quatre temps :

1. **Balayage** — une barre perce le plus-bas des 60 barres précédentes.
2. **Réintégration** — dans les 5 barres, une barre **clôture** au-dessus du
   niveau percé. La clôture, pas la mèche : « cassé en impulsion mais pas en
   structure » ne compte pas.
3. **Entrée** à cette clôture.
4. **Invalidation** si la réintégration n'arrive pas dans la fenêtre.

Le stop est **structurel** — sous l'extrême du balayage — avec un plancher en
ATR. Le plancher n'est pas un confort : les profondeurs de balayage mesurées
vont de 34 à 218 pips quand le spread réel de XAUUSD est de 52 pips (TCK-018).

## Ce que cette stratégie n'est pas

- **Pas une v2 de S018.** Autre déclencheur, autre dossier, autre magic. S018
  mesure la cassure S011 plus une entrée à l'équilibre ; S019 mesure le balayage.
- **Pas sa méthode complète.** Les clôtures partielles et le stop suiveur — le
  cœur de sa gestion, et probablement l'essentiel de son avantage — ne sont pas
  reproduits : le moteur commun ne sait pas les exprimer (TCK-014). S019 mesure
  son **entrée** avec une sortie qu'on sait inférieure à la sienne.
- **Pas un endroit où ajouter des idées.** La mèche de rejet est mesurée non
  significative (p = 0,136) et volontairement absente du code.

## Frontières

| Fait | Ne fait JAMAIS |
|---|---|
| Modifie `strategies/S019_gold_sweep/` | Touche à `strategies/S011_*` (étude scellée `studies/gold_forward/`) |
| Importe `_atr` depuis S011 en lecture | Réimplémente un indicateur déjà écrit |
| Mesure, publie le verdict | Promeut en PAPER ou LIVE — décision Adrian seule (R10) |
| Ouvre un ticket quand le moteur manque | Contourne le moteur commun (R9) |

## Contrats applicables

R1 causalité (testé sur le balayage à état et sur la porte journalière) · R3 stop
obligatoire · R4 magic unique · R5 conformance backtest/live · R7 manifeste ·
R9 backtester commun · R10 promotion Adrian.

## Où sont les choses

```
strategy.py            la règle, et rien d'autre
manifest.yaml          grille 16 cellules, paramètres par défaut
test_s019_strategy.py       15 tests — règle, stop, causalité, bornes
backtests/run_wf.py    harnais de mesure (coût de bord d'abord)
research/
  FALSIFICATION.md     critères fixés AVANT la mesure
  ANALYSIS.md          ce que la mesure a rendu
input-adrian.md        intentions d'Adrian, reformulées par cc-support
```

## Avant de toucher au code

1. Lire `research/FALSIFICATION.md`. Les seuils y sont écrits d'avance ; on ne
   les rediscute pas après avoir vu les résultats.
2. `python -m pytest strategies/S019_gold_sweep/ -q` doit être vert.
3. Tout ajout de commutateur agrandit la grille et affaiblit chaque résultat :
   16 cellules donnent déjà ≈ 0,8 réussite par pur hasard à 5 %.

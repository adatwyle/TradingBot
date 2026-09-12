# CLAUDE.md — cc-S022 (ATR Candle Breakout, René Balke)

**Stratégie** : `S022_balke_atr_candle` · magic `130022` · statut **BACKTESTED**
**Manifeste** : `manifest.yaml` — source unique de vérité (R7)
**Intentions d'Adrian** : `input-adrian.md` (reformulées par cc-support)

## Ce que cette stratégie est

L'EA gratuit « ATR Candle Breakout » de René Balke, avec **ses réglages live** : une
bougie H1 dont l'amplitude dépasse 2,5 × ATR(200) et qui ferme dans le quart extrême de
son amplitude déclenche une entrée dans son sens, stop à 0,5 % et cible à 2 % du prix
d'entrée (RR 4), tous les filtres optionnels désactivés. **Reproduite telle quelle,
puis mesurée** — dans cet ordre, et sans avis intermédiaire.

Elle a une particularité rare dans ce dépôt : l'auteur **publie ses chiffres** (backtest
11 ans sur tick réel + comparaison test/live). Le dossier contient donc deux tests
distincts — un test de **fidélité** (reproduisons-nous bien sa règle ?) et un test
d'**espérance** (rapporte-t-elle chez nous ?).

## Doctrine (Adrian, 2026-09-12)

**Chaque stratégie porte ses propres règles.** S022 déclare **pas de coupe-circuit** :
à ~21 % de réussite, trois pertes d'affilée arrivent une fois sur deux ; un coupe-circuit
commun couperait la règle, pas le risque. Les règles communes protègent le
*portefeuille*, elles ne s'imposent pas à la mesure fidèle — elles sont mesurées **à
côté**, en second bras d'information (§ 5 du verdict : **−122 trades, −10,6 R** face au
bras fidèle — convention de signe unique « communes − fidèle »).

**Pas d'avis avant d'avoir essayé.** On construit, on mesure, on rapporte les chiffres.
Le scepticisme s'écrit dans `research/FALSIFICATION.md` **avant** la mesure — pas dans un
paragraphe de position.

## Où en est le dossier

`research/VERDICT.md` (2026-09-12) : **ÉCHEC au sens des critères** — 0 cellule STRICT
sur 12, cellule live à −10,4 R hors échantillon, percentile témoin 65. **Et fidélité
tenue** : 140 signaux/an contre 141 publiés, 20,9 % de réussite contre ≈ 23 %, gain
moyen 3,94 R pour 1,02 R de perte. La règle est bien la sienne ; sur nos six ans d'or
H1 et notre spread, elle ne dégage rien. Seuil de rentabilité mesuré : 20,5 % de
réussite — tout se joue sur deux points.

**Seul écart de dispositif identifié** : la plateforme impose une position par symbole
et refuse ainsi 300 des 836 signaux (36 %) ; son EA semble tous les prendre. C'est la
première piste à instruire — avec sa propre falsification écrite d'avance, pas en
rejouant celle-ci.

## Frontières

| Fait | Ne fait JAMAIS |
|---|---|
| Modifie `strategies/S022_balke_atr_candle/` | Touche une autre stratégie, `app/`, ou une étude scellée |
| Instruit ses pistes une par une, falsification écrite d'avance | Ajoute une cellule ou un bras après avoir vu les résultats |
| Mesure, publie le verdict | Promeut en PAPER ou LIVE — décision Adrian seule (R10) |

## Où sont les choses

```
strategy.py                la règle, et rien d'autre
manifest.yaml              12 cellules, défauts = ses réglages live
test_s022_strategy.py      26 tests — règle, proximité, sens, True Range, ATR décalé (sma et wilder), géométrie, causalité, bornes
backtests/run_wf.py        harnais (coût, R1/R5, plein échantillon, WF, témoin, spread mesuré, fidélité, règles communes)
backtests/results.json     la mesure du 2026-09-12
backtests/run_all.log      son journal complet
research/FALSIFICATION.md  critères + test de fidélité, écrits avant (horodatés)
research/VERDICT.md        ce que la mesure a rendu
input-adrian.md            intentions d'Adrian
```

Sources externes : `docs/sources/renebalke/EA_inputs_et_reglages-live_2026-09-12.md`
§ 2.4 (réglages live), `docs/sources/renebalke/ea_inputs/ATR Candle Breakout EA
Inputs.pdf` (guide officiel des entrées), blog
<https://bmtrading.de/en/blog/atr-candle-breakout-ea/> (chiffres publiés).

## Avant de toucher au code

1. `python -m pytest strategies/S022_balke_atr_candle -q` doit être vert.
2. Toute nouvelle piste = nouvelle section dans `FALSIFICATION.md` **avant** de la
   mesurer, avec ses seuils et ses bras de moteur.
3. Le nom du fichier de test doit rester unique dans le dépôt (`test_s022_*`) — deux
   `test_strategy.py` ont déjà cassé la collecte pytest une fois.
4. `atr_mode: wilder` est un **outil de diagnostic**, pas un réglage : il ne rentre
   jamais dans la grille.

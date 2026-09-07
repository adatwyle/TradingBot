---
id: TCK-014
from: cc-S018
to: cc-spec
status: open
blocking: false
created: 2026-09-06
updated: 2026-09-07 (2e passe)
---

## Question

Le moteur commun (`core/backtest/engine.py`) ne connaît qu'**une sortie unique** par
trade — SL, TP, EOD ou RESIDUAL — et **ne déplace jamais un stop**. Deux familles de
règles de sortie sont donc aujourd'hui inexprimables dans ce dépôt :

1. **Sorties partielles** — fermer une fraction de la position à TP1, une autre à TP2,
   laisser courir le reste.
2. **Stop suiveur** — remonter le stop derrière le prix, y compris la variante
   « break-even qui finance le coût du trade » plutôt qu'un retour à zéro.

Ce n'est pas une lacune théorique. Elle a déjà coûté deux fois :

- `S011/research/ANALYSIS.md` § 4 et § 8.1 : le trailing de la stratégie historique
  n'a **pas** pu être reproduit, et la limite est portée dans le verdict de la v1 ;
- `strategies/S018_gold_doud_v2/` : la source mesurée (MoneyTalk #29) décrit ses
  sorties comme le cœur de sa méthode — TP1/TP2/TP3 (@ 29:03), SL suiveur (@ 29:51),
  break-even qui paie les frais (@ 30:04). Le dossier S018 a donc mesuré ses
  **entrées** seulement, et son verdict doit le dire pour rester honnête.

Tant que le moteur ne sait pas exprimer ces règles, toute stratégie dont la sortie est
la moitié du contrat sera mesurée **à côté de ce qu'elle est** — en silence, ce qui est
le pire cas. C'est exactement le défaut déjà documenté dans `anchored_wf.run_walk_forward`
à propos de `max_hold_bars` (« un harnais qui ne sait pas exprimer la règle de sortie
ne mesure pas la stratégie, il mesure son propre défaut »).

## Mise à jour 2026-09-07 — arbitrage Adrian, et le ticket devient bloquant

**Adrian a tranché : TCK-014 passe avant tout le reste sur le dossier or.**
`blocking` passe donc de `false` à `true`.

Ce qui a changé depuis la rédaction : S019 a mesuré le déclencheur d'entrée de la
même source, isolément, sur 119 992 barres M15 puis 358 624 barres M5. Résultat
(`strategies/S019_gold_sweep/research/ANALYSIS.md`) :

- 0 cellule sur 16 passe le walk-forward, dans les deux mailles ;
- le bras témoin aléatoire place la meilleure cellule au percentile 42,5 en M15 et
  13,5 en M5 — la cellule par défaut tombe à **0,0** en M5 ;
- surtout : le taux de réussite colle au **seuil d'équilibre géométrique** à un point
  de pourcentage près dans chaque cellule (33,4 % contre 33,33 % à 2 R ; 21,0 % contre
  20,00 % à 4 R). Une fois le coût de bord neutralisé, le résidu est nul dans 15
  cellules sur 16, |t| < 2.

Autrement dit : **son déclencheur d'entrée, avec notre sortie, ne contient aucune
information.** Et sa sélectivité mesurée est faible — 1,68 entrée par jour de live
contre ~4,2 balayages offerts, soit un tri de 2,5× seulement, trop peu pour extraire
un avantage d'un vivier neutre.

Conséquence directe pour cette spec : l'hypothèse restante est que son avantage vit
dans la **sortie**, et c'est la seule qu'on ne sache pas tester. Tant que TCK-014
n'est pas livré, le dossier or est arrêté — non par manque d'idées d'entrée, mais
parce que toute mesure d'entrée supplémentaire raffinerait une variable mesurée
neutre.

**Ce que ça n'autorise pas** : élargir la portée. La spec reste celle décrite
ci-dessous. En particulier, l'exigence de rétrocompatibilité (point 4) devient plus
forte, pas moins : le forward `studies/gold_forward/` est scellé et en cours de
validation.

**Test de recette proposé, gratuit et décisif** : une fois le moteur étendu,
remesurer S019 **sans toucher à une seule ligne de sa règle**. Si le déclencheur
neutre devient rentable par le seul changement de sortie, l'hypothèse est démontrée ;
sinon elle est réfutée. C'est un test propre parce que la variable d'entrée est
gelée et déjà mesurée.

## Mise à jour 2026-09-07, seconde passe — NON BLOQUANT, et NE PAS démarrer sans lire ceci

**Je retire le caractère bloquant que j'avais posé le matin même.** La justification que
j'avais écrite — « l'avantage vit dans la sortie, c'est la seule hypothèse restante » — est
**réfutée par une mesure qui n'exige aucune ligne de moteur**, faite le jour même.

### La mesure

Loi de chemin des 5 138 trades de S019. Pour une marche **sans dérive**, la probabilité
d'atteindre +b avant −1 R en partant de +a vaut `(a+1)/(b+1)`. Observé :

| Depuis | Observé P(suite) | Martingale |
|---|---:|---:|
| +1,0 R | 77,1 % | 75,0 % |
| +1,5 R | 82,8 % | 80,0 % |
| +2,0 R | 83,7 % | 83,3 % |
| +3,0 R | 73,7 % | 75,0 % |
| +4,0 R | 79,2 % | 80,0 % |

Écarts de −1,3 à +2,8 points, sans direction systématique, calculés **hors spread** donc
optimistes. Le chemin est indiscernable d'une martingale — et par le théorème d'arrêt
optionnel, toute stratégie d'arrêt sur une martingale a la même espérance. **Aucune
clôture partielle, aucun stop suiveur ne peut extraire d'avantage de ce déclencheur.**

### Le danger que la première passe n'avait pas vu

Toucher `core/backtest/engine.py` met en danger le forward scellé `studies/gold_forward/`,
qui tourne depuis le 14 août. Deux couplages vérifiés :

- `studies/gold_forward/run_forward.py:43` importe `strategies.S011_legacy_breakout.strategy` —
  **le code de la stratégie n'est pas haché**, seul `params.json` l'est ;
- `studies/gold_forward/report_forward.py:44` et `:174` recalculent le **bras témoin** via
  `core.backtest.anchored_wf.control_arm` **à chaque lecture**, et les critères d'arrêt du
  `PROTOCOL.md` § 3 sont des **percentiles contre ce témoin**.

Et `app/orchestrator/tbot-prod-watcher.py:212` lance `pytest app -q` quand
`.github/workflows/ci.yml:71` lance `pytest app strategies studies` : le test d'intégrité
du scellé **ne garde pas** le rollback de production.

### Ce que devient ce ticket

TCK-014 reste une **dette de plateforme légitime** — le trailing de S011 n'a jamais été
reproductible (`S011/research/ANALYSIS.md` § 4) et toute stratégie dont la sortie est la
moitié du contrat sera mesurée à côté d'elle-même. Mais il n'est plus le chemin critique
du dossier or, donc plus une raison de toucher `core/` dans l'urgence.

**Trois préalables avant la moindre ligne de moteur, sur décision d'Adrian :**
1. un **oracle de non-régression** trade par trade du moteur actuel sur barres réelles —
   `studies/verify-journal.py` ne convient pas, il vérifie une chaîne de hachage et ne
   rejoue aucun trade ;
2. le **garde-fou de prod aligné sur la CI** (`pytest app strategies studies`) ;
3. une **note de couplage** en fichier neuf sous `studies/gold_forward/` (jamais le
   `PROTOCOL.md`, non amendable) actant que toute modification de `core/backtest/` déclare
   l'invalidation du forward plutôt que de la contourner.

**Périmètre à élargir quand il sera spécifié** : `_reference_profile` et `_random_signals`
(`anchored_wf.py:236-355`) doivent apprendre à rejouer un plan de sortie, sinon le bras
témoin restera à cible unique et la comparaison sera faussée. La conformance R5 suit.

Détail complet : `support/designs/AUDIT_dossier-doud-etat-et-suite_2026-09-07.md`.

## Proposition de résolution

Spécifier une extension du moteur commun — **pas un moteur parallèle** (R9) :

- **A (préférée)** — enrichir le `Signal` d'un plan de sortie optionnel :
  `exits: [(fraction, target_atr_multiple), ...]` + `trail: {activate_at, distance,
  floor}`. Le moteur reste seul maître de l'exécution ; une stratégie sans plan de
  sortie garde exactement le comportement actuel, donc **aucun chiffre existant ne
  bouge**. Le P&L en R devient une somme pondérée par fraction.
- **B** — un `ExitPolicy` pluggable passé à `engine.run()`, plus général mais qui
  déplace la règle hors du signal et complique la conformance backtest/live.

Points à trancher dans la spec, quelle que soit l'option :
1. ordre de visite intrabar quand une fraction TP et le stop suiveur tombent dans la
   même barre (le moteur suppose aujourd'hui le pire cas : SL avant TP) ;
2. le stop suiveur se déplace-t-il au close de barre uniquement, ou en intrabar ? Le
   premier est mesurable avec nos données H1, le second exige l'intrabar
   (`core/validation/intrabar.py` existe déjà) ;
3. comment le R est défini quand la position se ferme en plusieurs morceaux — le
   risque initial reste le dénominateur, sinon les chiffres ne sont plus comparables ;
4. rétrocompatibilité : les dossiers déjà rendus (S011, S018, études scellées) ne
   doivent **pas** changer de valeur. Le forward `studies/gold_forward/` est scellé et
   réplique le moteur ligne à ligne dans `forward_step.py` — toute évolution du moteur
   doit être vérifiée contre lui avant d'être fusionnée.

Préférence cc-S018 : **option A**, parce qu'elle garde la règle de sortie dans le
contrat de la stratégie (donc visible dans le manifest et rejouable à l'identique en
live) et parce qu'elle est inerte par défaut.

## Réponse

<cc-spec>

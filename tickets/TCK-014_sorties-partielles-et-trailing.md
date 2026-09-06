---
id: TCK-014
from: cc-S018
to: cc-spec
status: open
blocking: false
created: 2026-09-06
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

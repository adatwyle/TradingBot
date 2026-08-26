# Analyse — Markov Regime Switching

Source : https://www.youtube.com/watch?v=Z-hU97WO30I
Trader : Lewis Jackson / Ran (hedge fund method)

**Commit de travail** : `434ced1` · **Contrat retenu** : ALLOCATION · **Magic** : 130008

La Phase 1 a été exécutée. Son contenu détaillé (crédibilité de la source,
méthode reformulée, vérification des trois corrections revendiquées, test de
contribution marginale de l'appareil, tableau de reproductibilité, substitutions
assumées, hypothèse testable, défauts de `core/` et de données rencontrés) est
consigné dans :

| Document | Contenu |
|---|---|
| `research/FALSIFICATION.md` | hypothèse H-a / H-b et 5 conditions de réfutation, **figées avant tout code** |
| `research/VERDICT.md` | mesures, écarts avec la source, conditions déclenchées, verdict, limites |
| `backtests/probe_apparatus.txt` | Q1 persistance recouvrante vs non recouvrante · Q2 contribution marginale · Q3 ampleur du biais de fuite · Q4 `P^n` contre l'exponentiation scalaire |
| `backtests/results_*.txt` | plein échantillon par instrument, ablation du spread, contrôle long/short, HMM, walk-forward |
| `backtests/causality.txt` | R1, 4 couches + contre-épreuve |
| `backtests/conformance.txt` | R5 |
| `markov.py` (docstring) | les quatre pièges d'implémentation de la chaîne de Markov |
| `strategy.py` (docstring) | justification du contrat allocation et des deux modes de dimensionnement |

**Synthèse en trois lignes** : les corrections n°1 (fenêtres non recouvrantes) et
n°2 (matrice causale) de l'auteur sont justes ; la n°3 (exponentiation scalaire)
est fausse et annule tout signal dès n = 2. Une fois la n°1 appliquée, la
persistance qui justifiait la stratégie tombe au niveau de la fréquence
inconditionnelle des états. Résultat : aucune variante ne bat le buy & hold sur
aucun des six instruments testés.

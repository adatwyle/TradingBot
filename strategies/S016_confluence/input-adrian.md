# input-adrian — S016 Confluence de quatre lectures

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S016 · magic `130016`
- **Source** : Idée Adrian (mandat Adrian 2026-08-20)
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s16_confluence\` (lecture seule)

## Principe (résumé)
Score de confiance calibré combinant quatre lectures : (1) technique, (2) sentiment, (3) anticipations des autres (positionnement COT institutionnel + marchés prédictifs type Polymarket/Kalshi, en lecture seule stricte — pas de compte, pas de capital, pas d'ordre), (4) avis de Claude Code. La combinaison doit produire un niveau de certitude sur le choix d'entrer ou non. Objectif : swing, 1 à 10 trades par semaine, sur les tendances générales. Univers déclaré : 4 paires forex en H1 (AUDCHF, EURUSD, AUDUSD, EURCHF).

## État hérité du prototype

**Statut manifest : `RESEARCH`** — au sens faible du terme : cadrage seul (`research/ANALYSIS.md`, livré 2026-08-20), aucun code de stratégie, aucun backtest, **aucun protocole scellé**. `research/FALSIFICATION.md` et `research/VERDICT.md` n'existent pas (Phase 2 verrouillée dans le prototype).

**Stratégie bloquée par construction** — 3 des 4 entrées ont une valeur inconnue :
- **Sentiment** : étude s14 en collecte ; verdict F1 au plus tôt **2026-10-17** (lecture finale obligatoire 2027-02-17). Aucune valeur démontrée à ce jour.
- **Anticipations / COT** : étude s15 **en suspens** (2 à 9 épisodes indépendants de hold-out contre un plancher dérivé de 12). Marchés prédictifs : **rien n'existe** (ni collecteur, ni historique, ni mesure).
- **Avis de Claude** : la seule lecture déjà mesurée, verdict **NE PAS ARMER** (rejeu macd_ai_paper : percentile 95,6 groupé qui tombe à 90,0 stratifié ; trades pris à −0,065 R). Dosage de taille mesuré nul (+0,022), ajustement SL/TP mesuré nuisible (−6,2 → −10,0 R) → portée figée à `prendre_ou_pas` uniquement.

**Condition de scellement écrite d'avance** (ANALYSIS.md §G.1) : au moins **2 des 3 conseils avec un verdict RENDU** (VALEUR CANDIDATE ou PAS DE VALEUR — pas « en cours »). Tant qu'elle n'est pas remplie, interdiction héritée de sceller un protocole de combinaison ou de coder la stratégie.

**Chiffres clés vérifiés dans le prototype** :
- Sur les 4 paires de l'univers, l'agrégat OOS honnête est **+302 CHF (9,6 % du total mesuré)** et EURCHF est **négatif (−120)** ; indices + DAX portent 90,4 % du résultat mais sont hors mandat « forex ».
- Cadence forex seule mesurée : **0,63 trade/semaine** — sous le plancher de 1 demandé (livre complet : 2,2/semaine).
- Calibration : nombre de tranches de confiance **figé à 3 au maximum** (5 tranches ≈ 17 ans d'effectif à la cadence mesurée) ; premier point lisible à ~18-24 mois de bras combiné.
- Arbitrage non résolu : le COT est hebdomadaire (~120 barres H1 par point) et ne peut pas nourrir une décision H1.

**Avertissement inscrit au dossier** : le swing « sur les tendances générales » est le régime réfuté quatre fois dans le dépôt (S2 cassure, S5 pullback, s13 famille B, s12 momentum) ; les seules poches positives jamais mesurées sont des **retours à la moyenne**.

**Actif réutilisable** : l'architecture de mesure (bras parallèles A0 référence / A1-A4 conseils / A5 aléatoire + SHADOW contrefactuel) est constructible dès maintenant — runner multi-bras et juge headless déjà écrits et testés dans le prototype (`studies/macd_ai_paper/`).

Cet état est une donnée d'entrée, pas un arrêt de mort.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- Respecter les invariants hérités du prototype tant qu'ils ne sont pas explicitement révisés : condition de scellement (≥ 2 verdicts rendus), avis de Claude limité à prendre / ne pas prendre, marchés prédictifs en lecture seule stricte, aucune promotion PAPER/LIVE sans décision Adrian.

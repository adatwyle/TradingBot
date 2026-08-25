# input-adrian — S008 Markov Regime Switching

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S008 · magic `130008`
- **Source** : YouTube — https://www.youtube.com/watch?v=Z-hU97WO30I (Lewis Jackson / Ran, « hedge fund method »)
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s08_markov_regime\` (lecture seule)

## Principe (résumé)

Discrétisation du rendement des 20 derniers jours en trois états (hausse / baisse / neutre, seuil ±5 %), matrice de transition estimée causalement sur fenêtres non recouvrantes (step = 20, lissage de Laplace α = 1.0), prévision à n pas par `P^n`, signal `P(bull) − P(bear)`, position proportionnelle à la confiance. Contrat ALLOCATION (pas d'épisodique, pas de stop de prix, potentiellement toujours investi). 6 instruments D1 : SP500, NASDAQ, BTCUSD, XAUUSD, DAX, ETHUSD.

## État hérité du prototype

*Donnée d'entrée, pas un arrêt de mort.*

- **Statut manifest** : `RESEARCH` — recommandation du prototype : ne pas promouvoir.
- **Verdict (research/VERDICT.md, 2026-08-16)** : **PAS D'EDGE**. 0 victoire contre le buy & hold sur les 6 instruments, sur 10 à 12 ans d'historique (couvrant 2018, 2020, 2022). Écarts de 2,1 à 36 points de CAGR annualisé. Reproduction propre : R1 (causalité) et R5 (conformance) passés.
- **Falsification** : 4 conditions sur 5 déclenchées (F2 effort zéro, F3 walk-forward sur SP500/NASDAQ, F4 pari directionnel, F5 fuite). F1 non déclenchée : l'appareil markovien produit bien d'autres positions que le momentum naïf (24 à 49 % de concordance) — mais sans en tirer profit.
- **Chiffres clés vérifiés** :
  - Plein échantillon, variante causale la plus favorable : SP500 +3,22 % CAGR vs +14,08 % B&H ; NASDAQ +12,03 % vs +20,11 % ; BTCUSD +13,94 % vs +46,74 % ; XAUUSD +5,30 % vs +7,32 % ; DAX +7,38 % vs +9,50 % ; ETHUSD −2,42 % vs +33,56 %.
  - Chaque jambe du portefeuille rapporte, par jour détenu, deux à trois fois moins que la détention du même actif : le timing détruit de la valeur.
  - La correction « fenêtres non recouvrantes » (revendiquée par l'auteur lui-même) détruit la persistance qui justifiait la méthode : persistance bull SP500 de 72,8 % à 15,0 %. Matrice 3×3 estimée sur 137 transitions seulement (SP500/NASDAQ), 217 (BTCUSD).
  - À `horizon ≥ 3`, `P^n` fige la matrice sur sa distribution stationnaire : 1 seul rebalancement en 12 ans — un buy & hold avec retard à l'allumage, et ce sont ses meilleurs chiffres bruts.
  - Biais de fuite chiffré : matrice non causale = +0,8 à +26,4 points de CAGR selon l'instrument (5/6) — mesure réutilisable ailleurs dans le projet.
- **Transférable retenu par le prototype** : la matrice non recouvrante comme **outil de mesure de persistance de régime** (diagnostic pour toute stratégie de suivi de tendance), plutôt que comme stratégie autonome.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC dédié, documenté).
- Le verdict PAS D'EDGE du prototype est solide et honnête : toute reprise doit soit attaquer une variante réellement nouvelle (pas un re-tuning de la même grille), soit réorienter l'actif vers son usage « outil de mesure » identifié par le prototype, soit documenter le constat de non-pérennité et clore proprement.

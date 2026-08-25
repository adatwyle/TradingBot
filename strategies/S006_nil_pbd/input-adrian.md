# input-adrian — S006 PBD Impulse-Range (Patrick Nil)

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S006 · magic `130006`
- **Source** : YouTube — Patrick Nil (https://www.youtube.com/watch?v=2ZmIn274eds)
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s06_nil_pbd\` (lecture seule)

## Principe (résumé)
Modèle « PBD » : après une impulsion (≥ 2 ATR sur 12 barres M15, directionnalité ≥ 0,60), la stratégie ne trade pas l'impulsion mais le range qui se forme ensuite. Deux modes séparés, jamais fondus dans une même grille : **fade** (le range tient — ping-pong entre les bords, lecture première de la source) et **break** (le range cède — cassure). Filtre optionnel value area sur profil de volume hebdomadaire (`va_filter`), bâti sur `tick_volume` faute de volume réel. Instruments : DAX + WTIUSD, timeframe M15.

## État hérité du prototype
- **Statut manifest** : `RESEARCH` (version 1.0.0, créé 2026-08-16).
- **Verdict** (`research/VERDICT.md`, moteur de référence commit `66668d1`) : **PAS D'EDGE** — ne pas promouvoir en PAPER.
- **Chiffre central** : STRICT **0 configuration sur 224** (espérance du pur hasard ≈ 11). Agrégat hors échantillon sur 112 configurations : **−0,087 R/trade**, et encore **−0,022 R/trade à coût nul** — l'ablation du spread ne sauve rien, il n'y a pas d'edge que des coûts masqueraient.
- **Plateau** : 29/112 configs OOS positives contre 56 attendues par hasard. `t` médian −0,80 ; les 3 configs « significatives » (WTI/fade + value area, n = 36) sont moins nombreuses que ce que la grille produit par hasard — faux positif de manuel.
- **Falsifications** : 4 sur 5 déclenchées (profil de trade, hasard, plateau, ablation spread). F5 non déclenchée : long ET short négatifs partout — uniformément sans edge, pas un pari déguisé.
- **Fait notable** : le win rate annoncé (50-60 %) et les séries de pertes annoncées (10-20 consécutives) se reproduisent fidèlement (mesuré : 52-61 % et 6 à 26) — et le système perd quand même. En revanche la fréquence mesurée est ~10× inférieure à l'annonce (0,03-0,50 trade/jour contre 3-5) : c'est la mesure de la sélection discrétionnaire du trader, que le code ne capture pas. Le test réfute **notre formalisation** du PBD, pas la compétence du trader.
- **Filtre value area** : dégrade 3 blocs sur 4 avec un signe qui s'inverse selon l'instrument, et divise l'effectif par 8-10. Sur `tick_volume`, l'ingrédient ne se transpose pas.
- **Transférable** : la brique de détection impulsion → range est réutilisable (couvre 12-18 % des barres M15) ; le stop large bat systématiquement le stop serré (+0,05 à +0,15 R/trade dans tous les blocs) ; la discipline d'évaluation du trader est alignée avec notre méthodologie.
- **Limites du test hérité** : un seul régime macro (2021-2026, pas de krach), WTI plafonné à 4,2 ans, slippage et swap non modélisés, pas de filtre news, et surtout l'écart discrétionnaire d'un facteur 10 sur la fréquence.
- **État du dossier** : `research/ANALYSIS.md` est resté un stub (jamais rédigé) alors que le verdict existe — la Phase 1 documentaire est à reconstituer si utile.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- Le verdict PAS D'EDGE est une donnée d'entrée, pas un arrêt de mort : les pistes laissées ouvertes par le prototype (réduction de l'écart de fréquence facteur 10 via des filtres de sélection plus proches du discrétionnaire, exploitation de l'effet stop large, réutilisation de la brique de détection impulsion → range dans un autre cadre) sont des points de départ légitimes. Archivage seulement sur constat propre du CC dédié, documenté.

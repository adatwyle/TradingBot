# input-adrian — S091 Asian-window fade (conception Claude)

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S091 · magic `130091`
- **Source** : Conception autonome de Claude (hypothèse H91) — aucune source externe
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s91_claude_scratch\` (lecture seule)

## Principe (résumé)
Dans la fenêtre de faible liquidité (heure serveur MT5 22h-06h « large », variante 23h-04h « étroite »), une extension de prix z = (close − SMA20) / sigma20 avec |z| ≥ 2 est traitée comme du bruit de carnet mince et jouée en contre-tendance : stop 2,5 × ATR(24), cible 1 × risque, H1. Quatre paires éligibles (EURUSD, USDCHF, USDCAD, AUDUSD) sans session domestique dans la fenêtre ; USDJPY et EURJPY maintenues comme contrôle négatif déclaré d'avance (session de Tokyo ouverte dans la fenêtre).

## État hérité du prototype
- **Statut manifest** : `RESEARCH` — recommandation du prototype : ne pas promouvoir en PAPER.
- **Verdict (research/VERDICT.md)** : **PAS D'EDGE** — falsification F3 déclenchée, déclarée avant le premier backtest : 1 réussite STRICT sur les 4 éligibles contre 10,8 attendues par pur hasard (grille 54 configurations × 6 instruments = 324 cellules).
- **Mais dossier le plus instructif du dépôt** — le diagnostic est précis :
  - Le signal brut **existe réellement** : à spread nul, +0,0818 R/trade et 180/216 cellules positives (83 %) sur les quatre éligibles simultanément.
  - La prédiction du contrôle négatif JPY se vérifie (−0,1595 R/trade) — mais elle est **confondue** par la tendance carry yen 2021-2024 (VERDICT §2.6) et n'appuie donc pas le mécanisme.
  - Le péage du spread vaut +0,0798 R/trade → net **+0,0019 R/trade** : le broker prend 98 % du signal. Hors échantillon et spread compris, toutes les variantes sont perdantes ; il manque un facteur ~1,5 sur le rapport signal/coût.
- **Chiffres de contexte** : 947 trades plein échantillon (groupe éligible, cellule par défaut), 82 trades OOS en médiane par instrument, une seule année positive sur six (2021-2026), moyenne OOS négative sur les quatre éligibles.
- **Sous-résultat conservé, non promouvable (VERDICT §4.1)** : la porte horaire apporte **+0,053 R/trade brut hors échantillon** contre la même règle appliquée 24h/24 (laquelle est négative OOS). L'heure vaut comme **FILTRE** par-dessus un signal ayant déjà un edge propre — jamais comme signal seul.
- **Voies laissées ouvertes par le prototype (VERDICT §7.1)** : instrument à faible péage relatif (exige de reformuler l'hypothèse, pas de la transporter) ; sortie temporelle « fermer avant l'ouverture de Londres » — version fidèle du mécanisme, jamais testée (`max_hold_bars` non transmis par le walk-forward de l'ancien `core/`) ; mode `rolling` non utilisé.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- Le verdict PAS D'EDGE du prototype est une donnée d'entrée, pas un arrêt de mort : les pistes §7.1 du VERDICT (sortie temporelle, reformulation faible-péage) et le sous-résultat « porte horaire comme filtre » sont les points de départ naturels.

# input-adrian — S001 FXAlexG Swing HTF

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S001 · magic `130001`
- **Source** : YouTube — chaîne fxalexg (https://www.youtube.com/@fxalexg__, ~1,3 M abonnés). Aucun track record audité trouvé ; la source décrit une approche, sans aucun chiffre de performance annoncé.
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s01_fxalexg_swing\` (lecture seule)

## Principe (résumé)
Structure de marché HH/HL vs LL/LH lue sur timeframe élevé (H4 ou D1, rééchantillonnés depuis les mêmes barres H1). Entrée sur H1 à la confirmation d'un swing contraire (lower high / higher low) situé dans la zone de retracement 0,382–0,786 de la jambe d'impulsion. Stop au-delà du swing d'entrée avec buffer 0,5 ATR ; cible structurelle ; set & forget (détentions annoncées 5-7 jours). 7 instruments : EURUSD, USDJPY, USDCHF, AUDUSD, USDCAD, EURJPY, XAUUSD.

## État hérité du prototype
Donnée d'entrée, pas un arrêt de mort. Chiffres vérifiés dans `manifest.yaml` et `research/VERDICT.md` du prototype :

- **Statut manifest** : `BACKTESTED` — au sens « mesuré », pas « validé ». Recommandation du prototype : ne pas promouvoir en PAPER.
- **Verdict** : `PAS D'EDGE` sur 6 des 7 instruments et sur le portefeuille dans son ensemble.
- **Mesure décisive** : 19 réussites STRICT en walk-forward ancré là où le pur hasard en produirait ~45, sur 896 cellules (128 configurations × 7 instruments). Données MT5 Swissquote H1, 2021-07-18 → 2026-08-14 (5,1 ans).
- **Ablation du spread** : à spread nul, le signal est à −0,008 R/trade (27/56 cellules positives) — indiscernable d'une pièce non biaisée. À spread réel : −0,103 R/trade. Le signal brut est à somme nulle ; il n'y a pas d'edge que les coûts auraient masqué.
- **Plein échantillon** : les 8 familles de paramètres sont négatives (−0,06 à −0,13 R/trade), 10 cellules positives sur 56.
- **Effectifs suffisants** : 66 à 83 trades hors échantillon par instrument — négatif mesuré, pas « non conclusif ».
- **Fidélité vérifiée** : la famille D1/ext62 reproduit bien les détentions de 5-7 jours annoncées, et perd aussi — l'échec n'est pas imputable à une infidélité de reproduction.
- **Résidu XAUUSD** : `NON CONCLUSIF` (sous-verdict séparé). 11 STRICT contre 6,4 attendues, moyenne OOS +3,21 R sur la grille ; meilleure cellule plein échantillon +86,6 R sur 406 trades (+0,213 R/trade, WR 32,3 %), positive côté long ET short. Disqualifié comme edge établi : 72 % du résultat total vient de la seule année 2022, et TIER 1 = 0/128. Ce résidu est à l'origine de l'étude gold.
- **Limite fondamentale déclarée** : le verdict porte sur la règle mécanique, pas sur le trader — le jugement discrétionnaire n'est pas testable. Une seule formalisation de la structure a été testée (128 variantes autour d'une définition).
- **Validations** : R1 (causalité) PASSÉ, vérifié sur 32 points de la grille. R5 (conformance) non exécutable dans le dépôt prototype ; divergence structurellement impossible (`on_bar()` réutilise le code de `generate_signals()`).

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC dédié, documenté).
- Pistes ouvertes par le prototype lui-même, à évaluer sans obligation : autres formalisations de la structure (le prototype n'en a testé qu'une) ; le résidu XAUUSD `NON CONCLUSIF` mérite un test dédié sur d'autres régimes ou instruments à faible spread ; la structure HH/HL–LL/LH seule n'a pas de valeur prédictive mesurée — si elle sert, ce sera comme filtre par-dessus un signal ayant déjà un edge propre, jamais comme signal.

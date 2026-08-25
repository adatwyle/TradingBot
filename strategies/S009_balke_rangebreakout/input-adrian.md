# input-adrian — S009 Session Range Breakout (René Balke)

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S009 · magic `130009`
- **Source** : YouTube — René Balke (BM Trading, @ReneBalke)
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s09_balke_rangebreakout\` (lecture seule)

## Principe (résumé)
Range de session 3h-6h heure serveur (high/low), entrée au close H1 de cassure (substitut déclaré du stop order M1 de la source), SL = borne opposée du range ou 1 % du prix, pas de TP, clôture forcée à 18h (19h pour l'or). Instruments : USDJPY, XAUUSD, GBPUSD, EURJPY, en H1. Variantes de la source : 1 ou 2 breakouts par jour, filtre optionnel de taille de range.

## État hérité du prototype
- **Statut manifest** : `RESEARCH` (version 0.1.0). R1 passé sur les 4 instruments, R5 conforme (0 divergence / 400 barres).
- **Verdict Phase 4 (`research/VERDICT.md`)** : **PAS D'EDGE** sur la version reproductible (H1 Swissquote, entrée au close, sortie temporelle approximée — dégradations déclarées). Recommandation du prototype : ne pas promouvoir.
- **Chiffres clés (walk-forward ancré + bras témoin, falsifications F1-F6 figées avant tout backtest)** :
  - USDJPY, sa config live (1 breakout, 3-6h, SL range) : **−7,01 R OOS sur 511 trades**, percentile témoin **66,5** (seuil déclaré : 95) — F1 déclenchée.
  - GBPUSD, sa config (4-12h, SL range) : **−17,10 R OOS sur 428 trades**, 4 fenêtres OOS sur 4 négatives. La source publie elle-même une **perte live de −8 778 € sur ~360 trades** sur cette config ; notre post-live (−0,047 R/trade) colle à son live (≈ −0,049 R/trade) — F5 gagnée, harnais validé sur un cas réel.
  - XAUUSD (SL 1 %, filtre) : +15,33 R OOS sur 409 trades, mais percentile témoin 72 — indistinguable du témoin sur un or en tendance.
  - **F4 ablation spread : déclenchée** — brut/péage = 0,82 hors échantillon (seuil 1,5) ; en plein échantillon le péage consomme 100 % du signal brut. Même diagnostic que s91.
  - **F2 beta yen : déclenchée** — le positif USDJPY est entièrement côté long (+0,0306 R/trade long vs −0,0483 short) : tendance capturée, pas edge de cassure.
- **Résidu documenté (VERDICT §2.7)** : le trade #2 « retournement » des configs 2-breakouts est la meilleure cellule du dossier (+0,0888 R/trade × 367 trades) ; percentiles témoin 93,5-97,0 mais effectif témoin écarté (~18 %) et sélection post-hoc → non concluant, consigné comme piste (convergence avec s91 : fade de l'échec de la fenêtre mince).

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC dédié, documenté). Le verdict négatif hérité est une donnée d'entrée, pas un arrêt de mort.
- Chemins d'amélioration candidats, à instruire proprement (falsifications figées d'avance, témoin à effectif corrigé) : le résidu retournement 2-breakouts (§2.7 du VERDICT), le rapport signal/coût (instrument à faible péage relatif, exécution moins dégradée que l'entrée au close H1).

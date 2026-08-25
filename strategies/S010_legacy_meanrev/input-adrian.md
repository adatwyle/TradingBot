# input-adrian — S010 Legacy S1 — divergence MACD + S/R

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S010 · magic `130010`
- **Source** : YouTube (StrategyDescription.txt, stratégie historique #1) — ré-implémentée dans le projet TBOT 2026 depuis le code historique `grid_search_v12_multi_variant.py` (le code a été LU, jamais importé)
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s10_legacy_meanrev\` (lecture seule)

## Principe (résumé)
Retour à la moyenne sur H1. Divergence prix/histogramme MACD (12/26/9) confirmée dans une zone support/résistance du timeframe supérieur, avec confirmation d'excès RSI(14) et filtre de régime ADX(14). Entrée au close, SL = 2 ATR, TP = 2× SL (set & forget), cooldown 2 barres et disjoncteur après 3 pertes consécutives. 8 instruments H1 (SP500, NIKKEI, FTSE, AUDCHF, EURUSD, EURCHF, AUDUSD, USDJPY). Trois chemins de code réels portés en variantes : `DIV_SR`, `DIV_NOSR`, `HIST_INF`.

## État hérité du prototype
*Donnée d'entrée, pas un arrêt de mort.*

- **Statut manifest** : `BACKTESTED` — au sens « mesuré », pas « validé ». Recommandation du prototype : ne pas promouvoir en PAPER.
- **Verdict (research/VERDICT.md)** : **PAS D'EDGE** sur 7 des 8 instruments et sur le portefeuille ; **NIKKEI = NON CONCLUSIF** (ni écarté, ni retenu).
- **Chiffres clés vérifiés** (MT5 Swissquote H1, 2021-07-18 → 2026-08-14, 5,1 ans ; 108 configurations × 8 instruments = 864 cellules ; R1 causalité passé, y compris à la couche indicateur — 176 comparaisons, écart nul) :
  - Walk-forward ancré : **19 réussites STRICT contre ~43 attendues par pur hasard** — moins de la moitié du hasard.
  - Espérance plein échantillon : **−0,0017 R/trade au spread réel** ; **+0,0748 R/trade à spread nul** — le spread (−0,0766 R/trade) consomme presque exactement l'edge brut.
  - Avec 0,5 pip de slippage réaliste : **−0,0271 R/trade**. Même un broker à spread nul ne suffirait pas.
  - SP500 et FTSE, vedettes du portefeuille contaminé historique : **0/108 STRICT** chacun.
  - NIKKEI : **9/108 STRICT** (8 en amas contigu), symétrique long/short — mais meilleur de 864 cellules sur ~100 trades, et instrument non choisi à l'aveugle → non conclusif.
  - **Le filtre S/R, signature de la stratégie, n'apporte rien de mesurable** : `DIV_SR` +0,0291 R/trade contre `DIV_NOSR` +0,0357 — le remplacer par un test trivial de dominance −DI/+DI fait marginalement mieux.
- **Invalidation historique** : tous les chiffres S1 publiés avant le 15.08.2026 (dont le « PORTFOLIO ROBUSTE » à +612 CHF/an) proviennent d'un moteur avec lookahead (`closes[-1]` au lieu de `closes[n-1]`) — non citables. Le run contaminé était de surcroît lui-même sous le seuil du hasard (19/3 570 STRICT contre ~178 attendues).
- **Non testés dans le prototype** : TP dynamique par paliers, combinaisons multi-variantes.
- **Piste ouverte notée par le prototype** : si quelque chose devait être repris de S1, ce serait le déclencheur de divergence seul, sur un instrument à faible drag de spread et un timeframe plus élevé — pas le système complet, et pas sur H1.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC dédié, documenté).
- Le verdict PAS D'EDGE hérité est une donnée d'entrée : re-évaluer, explorer les chemins d'amélioration identifiés (déclencheur de divergence seul, timeframes supérieurs à drag de spread réduit, résidu NIKKEI) avant tout constat définitif.

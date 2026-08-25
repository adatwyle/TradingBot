# input-adrian — S003 Brendan — LLM gérant de portefeuille

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S003 · magic `130003`
- **Source** : YouTube — Brendan (AI trading, ex-Raymond James) — https://www.youtube.com/watch?v=RetsRS5u-8Q
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s03_brendan_llm_pm\` (lecture seule)

## Principe (résumé)
Utiliser un LLM comme gérant de portefeuille, sur le modèle présenté par Brendan dans sa vidéo. La stratégie n'a jamais été implémentée : ni logique d'entrée/sortie, ni indicateurs, ni timeframe, ni paires n'ont été définis (`symbols: []`, `timeframe: ""` dans le manifest prototype). Tout le travail de reformulation de la méthode reste à faire à partir de la source.

## État hérité du prototype
- **Statut manifest** : `RESEARCH` (version 0.1.0, créé 2026-08-16).
- **Aucun verdict** : ni `VERDICT.md`, ni `FALSIFICATION.md`, ni `HYPOTHESIS.md` n'existent dans `research/`. `ANALYSIS.md` est un placeholder (« À rédiger en Phase 1 »).
- **`strategy.py`** : squelette non implémenté (toutes les méthodes lèvent `NotImplementedError` ; docstring : « STATUT : NON IMPLÉMENTÉE »). Magic 130003 déjà réservé.
- **Seul contenu réel** : captures d'écran de la vidéo dans `research/screenshots/` — 67 captures uniques du 2026-08-16, présentes en double dans deux sous-dossiers (`adrian/` et `screenshotsAdrian/`), soit 134 fichiers PNG.
- **Aucun backtest, aucun chiffre de performance** : rien à hériter côté résultats — donnée d'entrée, pas un arrêt de mort.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- Premier travail : réaliser la Phase 1 du prototype restée en friche — exploiter les captures d'écran (et la vidéo source) pour reformuler la méthode, produire l'analyse de reproductibilité avec nos données (barres OHLC MT5, pas de volume réel), et formuler l'hypothèse testable avant toute implémentation.

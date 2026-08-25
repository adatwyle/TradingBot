# input-adrian — S092 ClaudeTrader — agent headless cyclique

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S092 · magic `130092`
- **Source** : YouTube — AI Pathways (concept Hermes, framework Nous Research) — https://www.youtube.com/watch?v=lIMu8ysJW68
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s92_claudetrader\` (lecture seule)

## Principe (résumé)
Agent de trading discrétionnaire piloté par LLM, inspiré d'Hermes : mémoire persistante, planificateur cron, boucle d'auto-apprentissage, interface Telegram. Réalisé chez nous comme Claude Code headless lancé cycliquement par un orchestrateur — sans état entre deux invocations, le contexte étant reconstruit depuis des fichiers (`memory/` = faits, `skills/` = croyances), donc auditable. L'agent propose un `Signal` structuré (JSON, stop obligatoire) ; la plateforme dispose (validateur, `core/risk`, ledger) — aucun accès direct au broker. Architecture cible en quatre agents spécialisés (briefing, scanner, trader, reviewer), seul le trader émet un signal exécutable.

## État hérité du prototype
- **Statut manifest** : `RESEARCH` (version 0.1.0, créé 2026-08-16). `symbols: []`, `timeframe: ""` — jamais renseignés.
- **`strategy.py`** : stub non implémenté (NotImplementedError sur toutes les méthodes) — cohérent avec la nature du concept, qui n'est pas une stratégie mécanique.
- **`research/ANALYSIS.md`** : rédigée et aboutie. Pas de VERDICT.md, pas de backtest — l'analyse établit que le concept **n'est pas backtestable** (décisions LLM non déterministes, non rejouables) : R1 et walk-forward sans objet, validation possible **uniquement par paper trading forward** (journalisation d'abord, exécution jamais avant validation humaine).
- **Conclusion clé de l'analyse** : « Rien de ce que fait Hermes ne nous manque. Claude Code en headless possède déjà les outils ; ce qui manque est l'enveloppe qui le lance en boucle. » Cette enveloppe a été effectivement construite depuis (factory + gateway + pilote) : le concept a été absorbé par l'infrastructure.
- **Risque identifié** : la boucle d'auto-apprentissage apprend du bruit (quelques dizaines d'observations en mois de paper) ; parade prévue = séparation faits (`memory/`) / croyances (`skills/`), toute modification de `skills/` soumise à validation humaine.
- **Question ouverte (§9 ANALYSIS.md)** : coût d'exploitation — quelques euros par jour à quatre agents et plusieurs réveils, soit plus que ce que 1 000 CHF de capital peut raisonnablement produire ; à trancher avant toute phase paper.
- **Ressources annexes** : `sources/` (NATEHERK_ARCHITECTURE.md, FABLE5_RISKLAYER.md) et captures `frames_nateherk/` dans le prototype.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- **Premier travail spécifique** : décider si une stratégie propre subsiste dans ce dossier, ou si S092 s'archive comme doublon d'infrastructure (le concept Hermes ayant été absorbé par la factory/gateway/pilote existants). L'archivage n'intervient que sur constat documenté du CC dédié, jamais par défaut.

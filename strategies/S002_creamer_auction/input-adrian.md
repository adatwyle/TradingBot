# input-adrian — S002 Creamer Auction/Orderflow

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S002 · magic `130002`
- **Source** : YouTube — Chris Creamer (Robbins World Cup 2026) — https://www.youtube.com/watch?v=PL7LKUsCgIQ
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s02_creamer_auction\` (lecture seule)

## Principe (résumé)
Stratégie fondée sur l'auction market theory et l'orderflow, d'après la méthode présentée par Chris Creamer. Jamais implémentée : ni logique d'entrée/sortie formalisée, ni indicateurs, ni timeframe, ni paires définis à ce stade — le prototype n'a pas dépassé le stade du squelette.

## État hérité du prototype
- **Statut manifest** : `RESEARCH` (version 0.1.0, créé 2026-08-16). `symbols` vides, `timeframe` vide, `default_params` et `param_grid` vides.
- **Recherche** : `research/ANALYSIS.md` existe mais est un stub non rédigé (« À rédiger en Phase 1 »). Aucun VERDICT.md, aucune falsification, aucun backtest — la Phase 1 du workflow prototype n'a jamais été menée.
- **Aucun chiffre de performance** : rien n'a été mesuré, il n'y a donc ni verdict ni métriques héritées.
- **Obstacle documenté** (CLAUDE.md prototype, section « Ce dont tu disposes ») : les données MT5 Swissquote publient `real_volume = 0` (vérifié) sur tous les instruments ; seul `tick_volume` (nombre de changements de cotation, pas un volume de contrats) est disponible. Pas de carnet d'ordres, pas de delta bid/ask, pas de données options. L'orderflow/footprint au sens strict est donc irréalisable sur ces données — le CLAUDE.md prototype exigeait explicitement de le constater en Phase 1 et de proposer soit un substitut assumé, soit un abandon motivé.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- Spécifique S002 : mener réellement la Phase 1 jamais faite — étudier la source, reformuler la méthode, dresser le tableau de reproductibilité composant par composant face à la contrainte `real_volume = 0`. Trancher honnêtement : substitut assumé (par ex. approximations sur `tick_volume`/structure de prix, en documentant la dégradation) ou abandon motivé. Ne pas construire d'implémentation avant ce constat.

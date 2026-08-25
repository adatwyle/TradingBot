# 05 — Stratégies : cycle de vie

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Origine d'une stratégie

Deux sources :

1. **YouTube** (principale) : la vidéo est visualisée, puis le principe de fonctionnement est analysé — **sans préavis positif ou négatif** sur la personne ni sur les ratios de gains annoncés.
2. **Idée / descriptif d'Adrian** : l'idée est analysée, puis un échange traite les éventuelles questions — **sans préavis** sur la faisabilité.

## Identité et numérotation

- Chaque stratégie porte un numéro `S0NN` (S001, S002…). Mapping conservé du prototype (`s13` → `S013`) ; `S014` réservé (étude sentiment) ; prochain numéro libre `S017`.
- **Multi-paires** : si une stratégie trade plusieurs paires avec des paramètres différents, chaque instance est identifiée `S0NN.XXX-YYY` (ex. `S001.CHF-USD`, `S001.EUR-USD`). L'architecture gère cet aspect nativement (manifest : une entrée par paire, paramètres propres ; journaux, UI et Telegram raisonnent par instance).

## Vie d'une stratégie

- Chaque stratégie vit **totalement cloisonnée dans son dossier** `strategies/S0NN_<slug>/`, avec une **session Claude Code dédiée** (cc-S0NN) pour son développement, son parcours de validation et sa mise en production.
- Chaque dossier contient `input-adrian.md` (maintenu par cc-support) et `spec-strategie.md` (établi et maintenu par cc-S0NN).
- Le CC dédié **teste la stratégie et la fait avancer** vers la validation paper trading — ou **constate qu'elle n'est pas pérenne**, arrête son développement et l'archive.
- **Amélioration plutôt que refus** (décision 2026-08-23) : les verdicts du prototype sont des données d'entrée. Chaque stratégie reprise a droit à des chemins d'amélioration ; l'archivage exige un constat propre du CC dédié, pas un préavis.
- **Restart à zéro** : si Adrian le souhaite, il peut demander au CC de la stratégie de tout reprendre à zéro et de retenter un développement en suivant un nouveau chemin.
- Si un **Claude Code trader** est nécessaire à la stratégie, un CC supplémentaire dédié est créé — le trader de cette stratégie. Contrainte mesurée (prototype) : l'avis IA se limite à prendre/ne pas prendre, jamais de dosage de taille ni d'ajustement de stops, et un bras témoin sans conseil tourne en parallèle à vie.

## Statuts

`RESEARCH → BACKTESTED → PAPER → LIVE → RETIRED` (« BACKTESTED = mesuré, pas validé »). Promotion PAPER et LIVE : décision Adrian uniquement.

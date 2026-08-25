# 08 — Acteurs Claude Code et ticketting

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Acteurs

| Acteur | Où | Rôle |
|--------|-----|------|
| **cc-support** | `support/` — session desktop, accessible en remote control smartphone | Interaction avec Adrian : reformule et clarifie ses inputs en format clair et précis prêt au développement (`input-adrian/`). Traite les tickets de clarification. |
| **cc-spec** | `spec/` | Développement global de l'application : établit les spécifications de l'architecture et du fonctionnement souhaités (`specification-app/`), à partir d'`input-adrian/`. |
| **cc-app** | `app/` | Développe les services communs selon les spécifications. |
| **cc-orchestrateur** | `orchestrator-cc/` | Régit l'activité de l'orchestrateur selon les besoins de chaque stratégie et du développement de l'application. |
| **cc-S0NN** | `strategies/S0NN_*/` | Un CC dédié par stratégie : développement, validation, mise en production. |
| **cc-S0NN-trader** | idem | Créé seulement si la stratégie nécessite un trader IA. |
| **Orchestrateur (application)** | worker de la console | Fait tourner tous ces CC en sessions terminal headless. |

## Flux de fichiers

- `support/input-adrian/` (cc-support) → lu par cc-spec → `spec/specification-app/` → implémenté par cc-app.
- `strategies/S0NN/input-adrian.md` (cc-support) → lu par cc-S0NN → `strategies/S0NN/spec-strategie.md` (cc-S0NN).
- Les clarifications résolues sont reformulées en langage simple dans les fichiers input-adrian — jamais de dialogue persistant dans les specs.

## Ticketting et escalade

1. Un système de tickets (`tickets/`) permet aux CC de se faire des demandes ou d'**escalader une question à clarifier** vers cc-support, qui traite le point avec Adrian.
2. Le **start hook de cc-support** vérifie en permanence si un ticket de clarification **bloque** un développement. Bloquant + évident → cc-support répond tout seul pour débloquer immédiatement. Sinon → QA avec Adrian (Telegram ou hook), chaque fois avec une **préconisation**.
3. Règle de base : chaque CC reste le plus autonome possible et décide lui-même pour les thématiques évidentes. Minimiser la procrastination et la bureaucratie ; remonter que le nécessaire.

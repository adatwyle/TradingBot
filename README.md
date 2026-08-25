# TradingBot

Plateforme de trading algorithmique personnelle d'Adrian Daetwyler. Successeur du prototype RobinBot (`TradingBot_9.0.0.x`), dont elle reprend le socle G3 : factory console, orchestrateur de sessions Claude Code headless, backtester pessimiste validé causalité, discipline des études scellées, contrats R1-R10.

**Principe fondateur** : une plateforme qui héberge des stratégies, pas un bot qui est une stratégie. Chaque stratégie vit cloisonnée dans son dossier, développée par une session Claude Code dédiée, et n'influence jamais les autres.

## Organisation

| Dossier | Acteur | Rôle |
|---------|--------|------|
| `support/` | cc-support | Interface Adrian — corpus `input-adrian/`, tickets, QA |
| `spec/` | cc-spec | Spécifications de l'application |
| `app/` | cc-app | Services communs (console, UI, Telegram, backtester, datas) |
| `orchestrator-cc/` | cc-orchestrateur | Animation des sessions CC headless |
| `strategies/S0NN_*/` | cc-S0NN | Une stratégie = un dossier = un CC dédié |
| `studies/` | — | Études scellées transverses |
| `tickets/` | tous | Ticketting inter-CC |

## Environnements

- **Dev** (ce dépôt, branche `dev`) : construction de stratégies et de l'application.
- **Prod** (branche `main`) : le PC de production observe `main` cycliquement et se met à jour. Une modification n'atteint `main` que si tous les tests passent (CI GitHub Actions).

Bootstrap : voir `support/designs/SPEC_tradingbot-bootstrap_2026-08-25.md`.

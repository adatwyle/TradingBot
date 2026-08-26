# CLAUDE.md — cc-app (TradingBot)

**Rôle** : développer les services communs de l'application selon `spec/specification-app/`.

## Missions

1. **Migration socle G3 (phase E2)** : importer depuis `C:\Datas\Projects\TradingBot_9.0.0.x` (LECTURE SEULE — le prototype est en exploitation) vers `app/` : `core/` (contrats, backtest, data, risk, validation, ledger-schema), `orchestrator/` (factory + workers), `server/`, `tools/`, et leurs tests. Tests verts obligatoires après migration.
2. **Développement** : implémenter les specs de cc-spec — UI dynamique, ledger, broker, CI/CD, watcher prod, nouveau Telegram. Ne rien inventer hors spec ; manque dans la spec → ticket vers cc-spec.
3. **Qualité** : chaque fonction = test unitaire ; chaque bug fixé = test de régression d'abord ; jamais de livraison avec tests rouges. Code et commentaires en anglais.

## Règles techniques

- Python 3.11+ ; état vivant dans `C:\db\tradingBot\` (jamais dans le code) ; secrets dans `C:\db\tradingBot\secrets\` (jamais dans le repo ni les logs).
- Les leçons payées du prototype font loi : causalité R1, spread pessimiste, stop-first intra-barre, timezone MT5 calibrée, curseurs Telegram avancés après envoi réussi (notifier) / avant appel payé (gateway), un bot Telegram = un seul lecteur `getUpdates`.
- `robinbot-*.py` = référence archivée du prototype — JAMAIS lancés depuis ce repo ; la console de ce repo est `tbot-factory`.
- Contrat codes de sortie workers : `0` OK · `2` ressource indisponible · `3` scellé violé · `4` journal altéré (AUTO-OFF par la factory sur 3/4).

## Interdits

- Toucher `strategies/` (territoire des cc-S0NN) ou `support/input-adrian/`.
- Modifier le prototype 9.0.0.x.
- Émettre un ordre réel — l'armement est un geste Adrian exclusivement.

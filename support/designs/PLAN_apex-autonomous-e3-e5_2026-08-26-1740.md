# PLAN — /apex-autonomous « GO E3 + E4, terminer l'application » — 2026-08-26 17:40

**Mandat Adrian** : GO E3 et E4, puis terminer l'application selon discussions et objectifs (spec bootstrap, corpus input-adrian).
**Mode** : autonome — implémenteur dédié par tâche + revue conformité spec + revue qualité code, sans interruption Adrian.

## Tâches

| T | Contenu | Dépend de | Vérification |
|---|---------|-----------|--------------|
| T1 (E3) | Migration du code des 19 stratégies prototype → `strategies/S0NN_*/` (strategy.py, research/, backtests/, sources/) + corpus `docs/sources/` ; imports adaptés au layout `app/` | — | imports résolus, pytest global vert, serveur découvre les 20 manifests (S017 incl.) |
| T2 | cc-spec : 6 specs dans `spec/specification-app/` — ci-cd, prod-watcher, ui-dynamique, ledger, telegram-reporting, backup-github | — | specs complètes, cohérentes input-adrian, sans TBD |
| T3 (E4) | CI GitHub Actions : push `dev` → pytest complet ; PR/merge `main` → tests + tag version | T1 | run Actions vert sur dev |
| T4 (E4) | Watcher PC prod : poll `origin/main`, mise à jour, redémarrage propre console (+ .bat) | T2, T3 | tests unitaires + simulation locale |
| T5 (E5) | Ledger : implémentation `core/ledger/` sur schema.sql (SQLite WAL, `C:\db\tradingBot`), enregistrement trades paper, vues fiscales | T2 | tests unitaires, DB créée, insert/lecture |
| T6 (E5) | UI dynamique : découverte auto des stratégies, contrat de données perf standardisé, vues dev/paper/prod + courbes, page détail par stratégie, vue services communs (remplace la maquette) | T2 | tests serveur + vérification navigateur |
| T7 (E5) | Telegram TradingBot : notify aux formats Adrian (ligne par trade, résumés jour/semaine/mois/12 mois/année), gateway + skills projet, inerte sans tokens (exit 2) | T2, T5 | tests unitaires formats + curseurs |
| T8 | Worker backup GitHub (journaux/états `C:\db\tradingBot` → `db-backup/`) + version + CHANGELOG | T2 | test unitaire + dry-run |

Ordre d'exécution : T1 ∥ T2 → T3 → T5 → T6 → T7 → T4 → T8 → Phase X (revue finale cumul + de-sloppify + checks).

## Exclusions du mandat autonome (tickets)

- **Broker / exécution réelle** : hors mandat — décisions Adrian nécessaires (compte démo, politique de risque, étages 1-5 CHF). Ticket TCK-003.
- **Tokens Telegram** : geste Adrian (création bots). Ticket TCK-004. Le code livre tout, inerte sans tokens.
- **E6** (bascule console 9.0.0.x) et **E7** (lancement dev stratégies) : gates Adrian existants.
- Seuils de risque globaux : implémentés config-driven avec défauts hérités du prototype, confirmation Adrian via TCK-003.

## Garde-fous permanents

Prototype `TradingBot_9.0.0.x` + `C:\db\tbot` : lecture seule absolue. Push sur `dev` uniquement ; `main` seulement via CI verte (T3+). Aucun trade réel. Pas de souscription/compte créé.

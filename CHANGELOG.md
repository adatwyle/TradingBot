# CHANGELOG — TradingBot

## 1.1.0 — 2026-08-26

Run /apex-autonomous « GO E3 + E4, terminer l'application » (E3, E4, E5 + tbot factory + préparation bascule études). Détail des tâches : `SHARED_TASK_NOTES.md`.

- **E3** : code des 19 stratégies migré du prototype (verbatim + imports adaptés, verdicts préservés) + corpus de sources (7 chaînes).
- **Specs** : 6 spécifications d'implémentation (`spec/specification-app/`) par cc-spec, zéro TBD.
- **CI/CD (E4)** : pipeline GitHub Actions — push `dev` → pytest complet → publication auto `main` (ff-only) + tag `v<VERSION>`. Validé en production (premier tag v1.0.0 auto-créé).
- **Watcher PC prod (E4)** : wrapper englobant `tbot-prod-watcher` — poll `origin/main`, gate `update_safe` par stratégie (directive Adrian), `.stop` propre, pytest local post-pull, rollback anti-boucle, pull `db-backup/` sans redémarrage.
- **Ledger (E5)** : `core/ledger` sur le schéma hérité (WAL, migration v2 `instance_id`, agrégats jour/semaine ISO/mois/12 mois/année par stratégie et instance, décomposition fiscale brut/commission/swap/net).
- **UI (E5)** : serveur de supervision réécrit — découverte dynamique des stratégies, contrat `status.json` par instance, vues dev/paper/prod + courbes SVG, drill-down par stratégie, vue services communs, divergences déclaré/réel. Maquette et injection regex supprimées.
- **Telegram (E5)** : canal TradingBot — `tbot-notify` (ligne par trade + récaps jour/semaine/mois/12 mois/année aux formats Adrian) + `tbot-gateway` (bot dédié, sessions headless lecture seule, menu skills, `/etat`). Inertes sans tokens (TCK-007).
- **tbot factory** (directive Adrian 2026-08-26, TCK-005) : console 24/7 du projet — collecteur GEX S017, workers CC (files de tickets, S017), gateway/notify, backup, supervision ; panneau à chaud `C:\db\tradingBot\tbot-panel.txt` ; assertion anti-live R4.
- **Préparation bascule études (TCK-009)** : code des 5 études forward migré (scellés octet pour octet), workers off, `verify-journal`, runbook `CUTOVER.md` — bascule par GO Adrian, étude par étude.
- **Backup GitHub** : worker `tbot-backup` — allowlist fail-closed, commit `[skip ci]` scoped `db-backup/`, inerte hors branche `dev`.
- **Phase X** : revue finale du cumul (12 findings, tous traités ou actés), passe de-sloppify, 497+ tests.

## 1.0.0 — 2026-08-25/26

- Bootstrap E1 : structure projet, acteurs CC, corpus `input-adrian/` (9 chapitres), 19 dossiers stratégies documentés, ticketting.
- E2 : socle G3 RobinBot migré dans `app/` (factory, orchestrateur, serveur, core, ~180 tests), chemins unifiés `core/paths.py`, divergence de panneau corrigée.
- Fondation S017 ireland_gex (session parallèle).

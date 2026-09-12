# INDEX — Spécifications d'implémentation (spec/specification-app/)

**Maintenu par** : cc-spec · **Public** : cc-app · **Dernière révision** : 2026-09-13 (statuts : specs 1-6 implémentées v1.1.0, spec 7 implémentée v1.1.3)

| # | Spec | Couvre | Statut |
|---|------|--------|--------|
| 1 | `SPEC_ci-cd.md` | GitHub Actions : push `dev` → pytest complet → publication ff `main` + tag ; fichier `VERSION` ; marqueur MT5 win32 | **implémentée** (v1.1.0) |
| 2 | `SPEC_prod-watcher.md` | Wrapper PC prod : poll `origin/main`, pull ff-only, arrêt propre `.stop`, tests d'intégrité, rollback ; `run-prod.bat` | **implémentée** (v1.1.0) |
| 3 | `SPEC_ui-dynamique.md` | UI live : découverte auto des stratégies, contrat `status.json` par instance + ledger, vues prod/paper/dev + courbes, drill-down, services communs | **implémentée** (v1.1.0) |
| 4 | `SPEC_ledger.md` | `core/ledger` sur schema.sql : API open/close/record, snapshots, risk events, agrégats jour/semaine/mois/année par stratégie et instance, vues fiscales, migration `user_version` | **implémentée** (v1.1.0) |
| 5 | `SPEC_telegram-reporting.md` | Canal TradingBot : notifier (formats exacts Adrian, curseurs après envoi) + gateway (offset avant appel payé, skills `/etat`, menu auto), inerte sans tokens | **implémentée** (v1.1.0) |
| 6 | `SPEC_backup-github.md` | Worker `backup` : miroir allowlist `C:\db\tradingBot\` → `db-backup/`, commit `[skip ci]` horodaté sur `dev`, 1×/jour + à la demande, idempotent | **implémentée** (v1.1.0) |
| 7 | `SPEC_analytics-trades_2026-09-12.md` | Page `/analytics` (parité Trade Buddy) : filtres globaux mode/stratégie/instance/symbole/période, 9 KPI, courbe solde + drawdown, heatmap mensuelle, répartitions, SUMMARY (streaks, R), journal paginé lecture seule ; adaptateur lecture seule journaux forward → format ledger ; SVG maison ; lots L1 (P1) / L2 (P2) / L3 (P3) ; amende UI-7/UI-8 (4 shells, +3 routes GET) | **implémentée** (L1+L2+L3, v1.1.3, commit 0556210) — défauts §9 DF-1…DF-5 arbitrables par Adrian ; SPEC_ledger v1.1 (projection écrite) en ticket séparé ; contreseing cc-spec en attente |

## Invariants transverses (opposables à toute implémentation)

1. **Chemins** : exclusivement via `app/core/paths.py` (`project_root()`, `db_dir()`,
   `panel_file()`) ; seams d'environnement pour les tests, jamais de `if TEST`.
2. **Codes de sortie workers** : `0` OK · `2` ressource externe indisponible (réessai) ·
   `3` scellé violé · `4` journal altéré — 3/4 réservés aux scellés, AUTO-OFF factory.
3. **Leçons contraignantes (chapitre 09)** : jamais de config-switching adaptatif ;
   avis IA limité à prendre/ne pas prendre ; **l'armement d'argent réel est un geste
   d'Adrian** — aucune spec ci-dessus n'ouvre de chemin d'exécution d'ordre (le broker
   est hors mandat, TCK-006).
4. **Git** : jamais de force-push ; `main` n'avance que par la CI (ff) ; le watcher prod
   ne fait que `pull --ff-only`/rollback ; le backup ne commite que `db-backup/` sur `dev`.
5. **Secrets** : tokens sous `C:\db\tradingBot\<bot>\token.txt`, jamais dans le repo ni
   dans un log ; code inerte (sortie 2) en leur absence.
6. **Dépendances entre specs** : ledger (4) est le socle de l'UI (3) et de Telegram (5) ;
   la CI (1) précède le watcher (2) et conditionne le `[skip ci]` du backup (6).

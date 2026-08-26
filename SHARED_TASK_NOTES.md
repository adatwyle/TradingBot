# SHARED_TASK_NOTES — pont de contexte inter-tâches (apex-autonomous E3-E5)

Plan : `support/designs/PLAN_apex-autonomous-e3-e5_2026-08-26-1740.md`. Une entrée par tâche terminée, appendée par le contrôleur (cc-support).

## Contexte permanent

- Prototype `C:\Datas\Projects\TradingBot_9.0.0.x` + `C:\db\tbot` : LECTURE SEULE (exploitation en cours).
- Socle E2 : app/ (179 tests verts), chemins via `app/core/paths.py` (RBF_ROOT > TBOT_PROJECT_ROOT), état vivant `C:\db\tradingBot\`.
- Push : `dev` uniquement ; `main` via CI (T3+).
- S017 ireland_gex : fondée en parallèle par une autre session — ne pas toucher.

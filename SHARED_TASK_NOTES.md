# SHARED_TASK_NOTES — pont de contexte inter-tâches (apex-autonomous E3-E5)

Plan : `support/designs/PLAN_apex-autonomous-e3-e5_2026-08-26-1740.md`. Une entrée par tâche terminée, appendée par le contrôleur (cc-support).

## Contexte permanent

- Prototype `C:\Datas\Projects\TradingBot_9.0.0.x` + `C:\db\tbot` : LECTURE SEULE (exploitation en cours).
- Socle E2 : app/ (179 tests verts), chemins via `app/core/paths.py` (RBF_ROOT > TBOT_PROJECT_ROOT), état vivant `C:\db\tradingBot\`.
- Push : `dev` uniquement ; `main` via CI (T3+).
- S017 ireland_gex : fondée en parallèle par une autre session — ne pas toucher.

## T1 (E3) — migration code stratégies — 2026-08-26 ~18:30
- 19 dossiers S0NN complétés depuis le prototype (strategy.py, manifests, research + BRIEF_prototype.md, backtests, frames, sources) + docs/sources (corpus 7 chaînes + legacy v1). Commit d016271.
- Décisions : CLAUDE.md prototype → research/BRIEF_prototype.md ; S007/S008 imports relatifs adaptés a minima (try/except fallback) ; __pycache__ purgés ; passe générique cp -n pour les fichiers racine (SOURCE*, scripts recherche S007).
- Vérif : pytest 179 verts, prototype intact (HEAD 0e85fb5), +6.1 MB.
- Suivi : revue qualité S007/S008 dispatchée.

## T2 — specs implémentation — 2026-08-26 ~18:20
- 6 specs + INDEX dans spec/specification-app (cc-spec, zéro TBD). Décisions clés : CI ubuntu + MetaTrader5 marker win32 + publication auto dev→main ff + tag vVERSION ; watcher = wrapper englobant (pas un worker) + rollback si pytest rouge ; UI = status.json par instance + agrégation au service + SVG maison sans CDN ; ledger v2 = colonne instance_id ; telegram = live à la clôture + récap 20h + hebdo vendredi ; backup = allowlist fail-closed + [skip ci].
- Renumérotation tickets : TCK-006 broker (ex-003), TCK-007 tokens (ex-004) — collision avec tickets S017 de la session parallèle.

## Directive Adrian intégrée en vol — tbot factory (input-adrian 03 + TCK-005)
- Nouvelle tâche T9 (après T7) : tbot-factory.py (nouveaux fichiers uniquement, robinbot-*.py intouchés), catalogue v1 : gex_S017 (py:), cc_S017, cc_app_queue, cc_spec_queue, cc_support_block (claude:), gateway/notify, famille paper_S0NN désactivée + assertion anti-live R4. Panneau C:/db/tradingBot/tbot-panel.txt.

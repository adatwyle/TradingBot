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

## T5 — ledger — 2026-08-26
- app/core/ledger livré (commit 2243404) : WAL, migrations user_version v1/v2 (instance_id), API trades/equity/risk + agrégats jour/semaine ISO/mois/12mois/année par S0NN et instance, day_trades format Telegram. 23 tests.

## T10 — préparation migration études (TCK-009) — 2026-08-26
- 7 commits : 5 études migrées (scellés octet-pour-octet, .gitattributes -text), workers au catalogue tbot off, verify-journal.py (journaux vivants du prototype vérifiés lecture seule : tous exit 0), CUTOVER.md (bascule par GO Adrian, ordre conseillé macd→s13→gold→alexg→s14). Chaîne de hachage indépendante du chemin (prouvé). Clé finnhub à copier vers C:\db\tradingBot\secrets\ au GO s14.

## T6 — UI dynamique — 2026-08-26
- Commit a3ce13e : serveur réécrit (app/server/{app,state,services}.py + UI vanilla), maquette+injection regex supprimées, découverte auto (20 stratégies), status.json schema 1, drill-down, vue services, divergences déclaré/réel. 34 tests. Reste : port 8742 tenu par le prototype sur ce PC (T4 arbitre via seam), pyyaml ajouté à requirements (fix 83ce5e5).

## T7 — Telegram TradingBot — 2026-08-26
- Commit b551d9f : tbot-notify (lignes live + récaps jour/semaine/mois/12mois/année, curseurs après envoi), tbot-gateway (bot dédié, offset avant appel payé, session headless RO, menu skills), skill /etat, catalogue+panneau. 55 tests. Écarts: digest 22h (spec) vs 20h (proto) — réglable config ; TCK-010 vers cc-spec (TG-19 PnL vs session RO).

## CI (T3) — VALIDÉE EN PRODUCTION — 2026-08-26 ~18:56 UTC+2
- Après enregistrement du workflow sur la branche par défaut (bootstrap unique dev→main documenté) et fix assertions de chemins portables : run vert → main=83ce5e5 auto-publié + tag v1.0.0 auto-créé. Pipeline complet opérationnel.

## Phase X — clôture — 2026-08-26
- Revue finale cumul : GO-avec-correctifs, 12 findings → F1-F10 corrigés (commit 6e38e00, 524 tests), F11 acté (chat_id dans backup, repo privé), F12 noté. De-sloppify : 13 items (2841644).
- Écarts assumés : alexg_paper mappée S093 (l'étude instancie S093, pas S001) ; suppressions run-factory.bat/demarrer-detache.ps1 embarquées dans le commit 2c1de60 d'une session concurrente.
- Tickets ouverts vers Adrian : TCK-006 (broker/risque), TCK-007 (tokens Telegram — dossiers tbot-gateway/tbot-notify) ; vers cc-spec : TCK-008/011/012 (alignement specs). Bascules études : CUTOVER.md, GO Adrian par étude.
- Release 1.1.0 : CHANGELOG.md créé, VERSION bumpé.

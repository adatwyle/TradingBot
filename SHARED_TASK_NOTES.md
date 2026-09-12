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

## Directive Adrian intégrée en vol — tBot factory (input-adrian 03 + TCK-005)
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

## Bascules études (CUTOVER) — 2026-08-26 soir — cc-support
- macd_ai_paper (GO matin) puis s13_forward (GO 21:05 locale) basculées robinbot → tbot : verify 0 avant/après (sha d0ebd3ba inchangé s13), premier tick tbot « passage » (first_pass: False), panneaux annotés des deux côtés. Restent : gold_forward, alexg_paper, s14_sentiment (clé finnhub à copier au GO).

## Schéma manifest unifié — 2026-08-26 soir — cc-support (directive Adrian, override scope signalé)
- Constat : S017 seule invisible « proprement » sur l'UI (magic 0, nom dossier) — son manifest utilisait name/magic/instruments alors que la plateforme (SPEC_ui-dynamique §3 + 19 manifests) lit display_name/magic_number/symbols. Par ailleurs le registre de tbot-factory lisait name/magic → dégradé pour les 19 historiques.
- Fait : manifest S017 conformé (display_name "Ireland GEX — SPY intraday", magic_number 130017, symbols [SPY] — clé magic supprimée, une seule valeur) ; scan_strategies() de tbot-factory lit désormais les deux schémas (canonique prioritaire) + 2 tests ; gabarit strategies/_TEMPLATE/manifest.yaml créé (cause racine : aucun template n'existait).
- Commit : manifests seuls (S017 + _TEMPLATE). tbot-factory.py/test_tbot_factory.py NON commités (portaient déjà des modifs non commitées d'un autre acteur — à embarquer dans son prochain commit, mes edits sont testés, 62 verts).
- Note UI : l'UI tbot (8790) était déjà totalement dynamique (scan par requête). La console 8742 = prototype robinbot pré-programmé (E6 l'éteindra).

## Migration totale robinbot → tBot + UI unifiée — 2026-08-26 soir — cc-support (GO Adrian)
- Bascules CUTOVER complètes : gold_forward (7 lignes, sha 611c3c81, position SHORT reprise, premier tick tbot OK), alexg_paper (sha b72541f4 — NB : aucune mesure côté robinbot depuis le 22.08, premier tick tbot à surveiller), s14_sentiment (1745 lignes, sha 952ef054, clé finnhub COPIÉE vers C:/db/tradingBot/secrets/, source intacte). Les 5 études vivent désormais sous C:\db\tradingBot\, panneau robinbot tout off côté études.
- UI unifiée (directive Adrian) : les études s'affichent SUR la carte de leur stratégie (state.py `etudes`, remonte alive + niveau PAPER ; living_study_strategies supprimée) ; /api/services ne garde que s14 ; cartes minimales (activité réelle seulement, jamais-passées résumées en 1 ligne, meta dossier·magic retirée) ; drill-down : section ÉTUDES. Tests adaptés +1 nouveau (38 verts). Divergence spec tracée dans TCK-012 (point 5).
- Serveur supervision relancé par la factory (service) pour charger le nouveau code. VERSION 1.1.1.
- Extinction robinbot : PAS faite — reste côté robinbot : supervision (8742), notify, pilot, portier, mesureur (file R&D prototype, équivalents tbot en préparation — skills untracked .claude/skills/tbot-portier|mesureur). Checklist posée à Adrian pour GO final.

## Extinction robinbot — 2026-08-27 matin — cc-support (GO Adrian)
- `.stop` posé dans le prototype (mécanisme d'arrêt propre) : robinbot-factory drainée puis éteinte, serveur 8742 arrêté avec elle. Plus aucun processus TradingBot_9 en vie ; tbot-factory (PID 39416) + serveur 8790 intacts. Aucune tâche planifiée/startup ne relance robinbot au boot.
- pilot/portier/mesureur éteints avec la factory — file R&D du prototype figée dans C:\db\tbot (rien de perdu), équivalents tbot en préparation (skills .claude/skills/tbot-portier|mesureur).
- Adjacent signalé : tâche planifiée Windows `S017-gex-snapshot` encore active, redondante avec le worker gex_S017 de la factory (wrapper idempotent — sans danger) ; suppression = geste Adrian.
- Continuité prouvée en conditions réelles : trade or SHORT_20260826_1700 ouvert par robinbot (20:23 CH), suivi et clôturé SL par tbot (04:36 CH) — zéro rupture de journal à travers la migration.

## s20_forward — forward scellé S020 EURUSD H1 — 2026-09-12 — cc-support (GO Adrian)

- **GO Adrian** « GO forward scellé EURUSD » après le VERDICT S020 (réussite sur
  EURUSD H1 au sens des critères écrits d'avance). Override de périmètre signalé.
- **Dispositif** : copie adaptée de `studies/s13_forward/` (deux bras : EURUSD
  PRINCIPAL, USDJPY OBSERVATION — teste le transfert sans compter dans le verdict).
  Cellule scellée : zero_filter true · sl 1 % · tp 2 % · both. Engine kwargs de la
  mesure (cooldown 2, cb 3 → 24). Spread catalogue (= mesuré sur ces deux paires).
- **Scellé** : SHA-256(params.json) = 5fd385aa… répliqué dans run_forward.py ; commit
  au scellé 26a81f0. Premier passage posé le 2026-09-12 12:49:50 UTC sur le cache
  (MT5 hors ligne) : barre de scellé 2026-09-09 23:00, journal vierge, état créé sous
  `C:/db/tradingBot/s20_forward/`.
- **Seuils adaptés à la fréquence mesurée** (≈ 25 trades/an) : échec 30 & pct < 20 ;
  succès 60 & pct ≥ 95 ; temps < 30 après 18 mois ; horizon 48 mois. Justifié dans
  PROTOCOL.md § 3.
- **Exploitation** : worker `s20_forward` au catalogue de la fabrique (tick 3600 s),
  `s20_forward = on` au panneau. **Ne mesurera rien tant que la fabrique n'est pas
  relancée** (arrêtée depuis le 10.09 02:02).
- Tests : 14 (s20_forward) + 25 (factory) + 11 (S020) verts. Manifest S020 → PAPER
  (PAPER ne vaut pas validation).

## T8 — lot du 26-27.08 non commité — 2026-09-12 19:02
- Files changed: CHANGELOG.md, CLAUDE.md, app/core/paths.py, app/orchestrator/{run-tbot-factory.bat, run-tbot-prod.bat, tbot-backup.py, tbot-collecte-gex-s017.py, tbot-notify.py, tbot-panel.exemple.txt, tbot-prod-watcher.py}, strategies/S017_ireland_gex/mandat-cc.txt, studies/CUTOVER.md, support/input-adrian/{03,09}, .claude/skills/{tbot-mesureur,tbot-portier}/SKILL.md — commit f40118f.
- Decisions: diff revu (graphie « tBot factory », CHANGELOG « Non publié », deux skills complets), 551 tests verts avec ces fichiers → commité sur directive Adrian « reprends toutes les tâches et termine-les ».
- Open follow-ups: aucun.

## T3 — données intraday indices + US30 au catalogue — 2026-09-12 19:25
- Files changed: app/core/data/source.py (SYMBOL_MAP US30 → #US30), app/core/data/instruments.py (ligne US30 : pip 0.1, spread 35 pips mesuré sur 365 j H1, max 87.5, pip_value_per_lot 1.0 convention indices, faits MT5 en commentaire), app/tests/test_instruments.py (6 tests, nouveau), docs/data/INDICES_intraday_2026-09-12.md ; cache : NASDAQ/DAX/SP500/US30 H1 1855 j + US30 D1.
- Decisions: NASDAQ/DAX/SP500 non retouchés (spreads mesurés ×1,5 à ×2,9 le catalogue → TCK-018) ; DAX cote 08h-21h serveur seulement ; revue OK (372 tests app).
- Open follow-ups: TCK-018 (catalogue spreads indices) ; pip_value_per_lot indices = convention, pas mesure.

## T2 — corpus Balke dans le dépôt — 2026-09-12 19:45
- Files changed: docs/sources/renebalke/{corpus/*.md (27), site/*.txt (18), tools/build_corpus.py, CORPUS_INDEX.md (773 items), README.md}.
- Decisions: script idempotent (index sans horodatage après revue KO → corrigé), durées en mm:ss non plafonnées, union des ids pour les comptes ; rejouable à chaque nouvelle vague Whisper (`python docs/sources/renebalke/tools/build_corpus.py`).
- Open follow-ups: relancer le script quand Whisper aura fini les 50 (état : 27 corpus + 15 août = 42/773).

## T7a — synthèse tranche 1 — 2026-09-12 19:20
- Files changed: docs/sources/renebalke/SYNTHESE_tranche1_2026-09-12.md (rendu du workflow wf_da9dcde9 : quatre lectures + contre-lecture, 182 k car.).
- Decisions: rendu mécanique du JSON, titres lissés ; contenu = sortie des agents, non réécrit.
- Open follow-ups: tranche 2 (transcripts Whisper) à analyser quand disponibles ; SYNTHESE.md à raccorder.

## T1 — s20_forward sous la fabrique — 2026-09-12 19:36
- Files changed: aucun.
- Decisions: vérifié — passes horaires 16:35:03Z (2 OPEN : EURUSD short PRIMARY, USDJPY short OBSERVATION) puis 17:35:34Z (0 événement, marché fermé, unrealized EURUSD +0,34 R). Le worker tourne bien au tick de 3600 s depuis la relance de 18:35.
- Open follow-ups: aucun ; suivi via status.json / journal.csv.

## TradeBuddy — phase comprendre — 2026-09-12 19:50
- Files changed: spec/specification-app/SPEC_analytics-trades_2026-09-12.md (+ ligne INDEX.md), docs/sources/renebalke/TRADEBUDDY_analyse-ecrans_2026-09-12.md, docs/sources/renebalke/frames/tradebuddy/ (168 écrans, commit 0c5d0f3).
- Decisions: workflow wf_7d141f1d (22 agents) : 76 écrans décrits, 26 fonctionnalités F01-F26 (9 P1 / 9 P2 / 8 P3), formules reconstruites depuis les valeurs à l'écran, 3 critiques (couverture, données, narration) intégrées ; spec = 33 exigences AN-x, 18 décisions, 20 défauts DF-x modifiables par Adrian, lots L1/L2/L3. Override de périmètre : cc-support rédige la spec et fait développer l'app sur directive Adrian directe (19:03).
- Open follow-ups: implémentation en cours (wf_e1b817a5) ; SPEC_ledger v1.1 (projection écrite journaux → ledger) reste un ticket séparé ; DF-1…DF-5 à arbitrer par Adrian.

## T4 — S022 ATR Candle Breakout (or H1, René Balke) — 2026-09-12 20:05
- Files changed: strategies/S022_balke_atr_candle/{strategy.py, manifest.yaml (BACKTESTED), test_s022_strategy.py (26 tests), backtests/run_wf.py, results.json, run_all.log, research/FALSIFICATION.md (+ addendum daté après mesure), research/VERDICT.md, CLAUDE.md, input-adrian.md}, app/core/contracts/MAGIC_REGISTRY.md (130022).
- Decisions: règle reproduite telle quelle (ATR SMA shift 1, TR avec close précédent, proximité ≤, corps du bon sens) ; bras fidèle sans coupe-circuit + bras règles communes en information ; fidélité tenue (140 signaux/an vs 141 publiés, WR 20,9 % vs ≈ 23 %) ; ÉCHEC au sens des critères écrits d'avance (0 STRICT, cellule live −10,4 R OOS, témoin p65, 2023 = 301 % du total) ; spread catalogue or faux ×3,6 → toute décision au spread mesuré. Deux relectures (conformité OK, qualité OK avec 7 points corrigés).
- Open follow-ups: piste n° 1 = bras sans la contrainte « une position par symbole » (36 % des signaux refusés viennent de nous, pas de son EA) — à instruire avec sa propre falsification, décision Adrian ; slippage à 0 partout dans le dépôt ; TCK-018 spread catalogue.

## T5 — S023 Turnaround Tuesday (DAX/NASDAQ/US30 H1, René Balke) — 2026-09-12 23:45
- Files changed: strategies/S023_balke_turnaround_tuesday/{strategy.py, manifest.yaml (BACKTESTED), test_s023_strategy.py (24 tests), backtests/run_wf.py (porte R1/R5, profils de sortie sur 18 cellules), results.json, run_all.log, research/FALSIFICATION.md (intact) + VERDICT.md (addendum daté), CLAUDE.md, input-adrian.md}, MAGIC_REGISTRY.md (130023).
- Decisions: règle reproduite (lundi sous SMA D1 dérivée des H1, sortie mardi via max_hold_bars 45/27 mesurés, garde 5 % propre) ; ÉCHEC au sens des critères (seul le DAX bat le témoin p97,5 — meilleure cellule STRICT fidèle p93 ; NASDAQ/US30 : la version sans filtre fait mieux = dérive de l'indice). any_bar décale 16-21 % des sorties au mercredi (mesuré). Deux relectures intégrées.
- Open follow-ups: garde 3 % = stop de gestion sur NASDAQ (non fidèle) ; bras règles communes inerte (1 trade/semaine) ; results.json enregistre un arbre modifié.

## T7b — tranche 2 Balke (47 vidéos les plus vues, Whisper) — 2026-09-13 00:05
- Files changed: docs/sources/renebalke/SYNTHESE_tranche2_2026-09-12.md (195 k car.), corpus/ (69 transcripts), CORPUS_INDEX.md (84/773) — commit 7bab68d.
- Decisions: workflow wf_a60226fd (22 agents) : 4 angles × 4 lots, fusion par angle, 2 contrôleurs (30 erreurs, 32 trous, 20 contradictions relevés — livrés bruts dans la contre-lecture, non réécrits). Nouveautés à règle complète : scalping EMA 8/13/21 multi-TF, ICT Silver Bullet, stochastique 5/3/3 + SMA100, RSI 30/70 réarmé + SMA50, BB+RSI, triple SMA, structure HH/HL, Heiken Ashi flip, Trend Tracer, Arrow ZigZag, Donchian D1 trailing ; six mécanismes grille supplémentaires pour S021 ; trois jeux d'heures différents pour son Range Breakout (S009).
- Open follow-ups: 689 éléments du canal non transcrits (fetcher API bloqué 429 ; Whisper sur la suite = ~700 h, à cadencer) ; SYNTHESE.md racine à raccorder aux trois tranches.

## T6 — S024 Go Long (DAX/NASDAQ/US30 H1, René Balke) — 2026-09-13 00:20
- Files changed: strategies/S024_balke_go_long/{strategy.py, manifest.yaml (BACKTESTED), test_s024_strategy.py (30 tests), backtests/run_wf.py (% via pnl_r × risk_distance / entry, porte R1/R5, jambes intraday/overnight sur trois populations, balayage horaire), results.json, run_all.log, research/FALSIFICATION.md (+ addendum A1-A6), VERDICT.md, CLAUDE.md, input-adrian.md}, MAGIC_REGISTRY.md (130024).
- Decisions: « réussite en tant que bêta indiciel, pas d'edge de timing » (formulation pré-enregistrée) : cellule fidèle positive au spread mesuré 3/3 (DAX +47,9 %, NASDAQ +71,4 %, US30 +43,5 % sur 5 ans) ; balayage horaire p31,8 / p63,6 sur les indices 24/24 (DAX p100 = artefact de séance) ; jambe overnight négative sur les trois indices à population comparable (choix fait après premier run, déclaré, favorable à l'auteur — trois variantes publiées). Première relecture KO (le % omettait la moitié du coût de bord) → corrigé, chiffres du relecteur reproduits.
- Open follow-ups: swap non modélisé (décisif pour la comparaison acheter-et-tenir) ; slippage 0 ; catalogue DAX max_spread 20 < 23 mesuré (TCK-018) ; bras règles communes annulerait presque la stratégie (US30 +43 → +2 %).

## TradeBuddy — phase implémenter — 2026-09-13 00:45
- Files changed: app/server/{analytics.py, journal_adapter.py, app.py, state.py, ui/analytics.html, ui/app.js, ui/style.css, ui/index.html, ui/strategy.html, ui/services.html}, app/tests/{test_server_analytics.py, test_server_journal_adapter.py, test_server_analytics_routes.py, _analytics_fixtures.py, conftest.py, test_server_services.py, test_server_state.py}, VERSION 1.1.3, CHANGELOG « Non publié ».
- Decisions: workflow wf_e1b817a5 (A adaptateur + B moteur + C front en parallèle, D routes, puis 3 relecteurs × 2 tours + correcteur) : tour 1 KO/KO/OK (4 bloquants : garde de re-rendu inopérant à cause de `generated`, décimation qui perdait le creux du DD, StopIteration sur journal vide, + mineurs), tour 2 OK/OK/OK, 494 tests app verts, serveur réel lecture seule vérifié (aucun fichier créé sous C:/db). Page vue dans le navigateur sur les 5 journaux réels (14 trades) : toutes les sections rendent. Override de périmètre cc-support → cc-app sur directive Adrian.
- Open follow-ups: DF-1…DF-5 (défauts de formules) à arbitrer par Adrian ; SPEC_ledger v1.1 (projection écrite journaux → ledger) ; tuiles KPI tronquées sur écran étroit (libellé long) ; F23-F25 (Correlation / Backtest comparison / Monte Carlo) jamais montrées, hors périmètre.

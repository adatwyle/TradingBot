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

## S018 — or v2 « méthode Doud » — 2026-09-06 — cc-support (branche `v2/gold`, worktree `C:\projects	radingBot-v2`)

Run /apex-autonomous sur la demande Adrian « analyse les 2 vidéos, reproduis la méthode, renforce le gold forward », arbitrée en cours de route : **v1 scellée intouchée, v2 = nouvelle stratégie S018 dans un worktree séparé**.

- **T1 worktree** : `git worktree add C:/projects/tradingBot-v2 -b v2/gold` depuis `b8c06b8`. Motif : la factory tourne depuis le clone principal avec 5 études en vol ; un `checkout` y aurait échangé le code sous les études pendant leur exécution.
- **T2 corpus** : `docs/sources/moneytalk/` — transcripts FR intégraux des deux podcasts (`youtube_transcript_api`, horodatage par segment), `SOURCE.md`, `SYNTHESE.md`.
- **T3/T4 stratégie** : `strategies/S018_gold_doud_v2/` — manifest (magic 130018, RESEARCH), `strategy.py` (5 commutateurs), CLAUDE.md, input-adrian.md.
- **T5 tests** : 19 tests, dont l'égalité stricte cellule neutre = v1 sur 30 024 barres réelles (784 signaux).
- **T6 mesure** : `backtests/run_wf.py` → `grid.txt`, `results.json`, `causality.txt`, `conformance.txt`.
- **T7 recherche** : `research/{ANALYSIS,FALSIFICATION,VERDICT}.md`.
- **T8 câblage** : registre magic, tickets TCK-014/015/016, CHANGELOG, VERSION 1.2.0.

**Décisions structurantes**
1. `studies/gold_forward/run_forward.py:43` importe `S011.strategy` en direct : le scellé protège `params.json` par hash mais **pas le code**. Toute v2 devait donc être un module séparé — c'est la raison technique de S018, pas une préférence d'organisation.
2. Les indicateurs sont **importés** de S011 plutôt que recopiés : c'est ce qui rend l'égalité de la cellule neutre vraie par construction et pas par intention.
3. Le filtre de régime ER/failed-rate de la v1 n'est pas repris — la cellule scellée le neutralise identiquement (`er_min=0,00`, `fr_max=1,00`).
4. `EQUILIBRIUM_RATIO`, `PULLBACK_MAX_BARS`, `HTF_EMA_DAYS` sont **hors grille** : ce sont les hypothèses, pas des réglages. Grille tenue à 32 cellules (≈ 1,6 réussite attendue par hasard).

**Résultat** : `NON RETENU en l'état`. Détail et chiffres dans `research/VERDICT.md`.

**Suites ouvertes**
- Piste de décorrélation (§ 5 du VERDICT) : la cellule équilibre+session+biais produit un profil annuel presque inverse de celui de la v1, sur 78 trades — à instruire par effectif, sur décision Adrian.
- La branche `v2/gold` n'est **pas** fusionnée dans `dev` : S018 est en RESEARCH et rien n'y dépend. Le worktree peut être retiré (`git worktree remove`) une fois la branche poussée.
- Collision de numéros de tickets possible : TCK-014/015/016 pris sur cette branche pendant qu'un autre acteur travaille sur `dev` (dernier ticket vu côté `dev` : TCK-013). À vérifier au merge.
- Adjacent constaté, non corrigé : `strategies/S017_ireland_gex` et `S093` déclarent un `strategy_id` qui ne correspond pas à leur nom de dossier, ce qui casse `core/validation/*.load_strategy` en CLI pour elles. S018 aligne les deux (`S018_gold_doud_v2`).

### T9 — captation des lives Doud : évaluation (idée Adrian) — 2026-09-06

`tickets/TCK-017_captation-lives-doud.md` (vers Adrian). Réponse : **non nécessaire**.
Un flux de ses appels ne lève aucun des trois obstacles du VERDICT — il ne rend pas
ses sorties rejouables (TCK-014), il produit 100-250 observations par an quand il en
faudrait 2-3 ans pour conclure, et il ne fournit pas le calendrier économique
(TCK-016, disponible gratuitement chez la Fed et le BLS). Ce qu'on obtiendrait est un
signal de copy-trading : non backtestable, donc R1 sans objet et R10 infranchissable.

Deux obstacles pratiques consignés : ses lives sont payants (39,99 €/mois, migration
vers sa plateforme propre) — je ne peux ni créer de compte, ni payer, ni saisir
d'identifiants ; et la captation automatisée d'un flux payant engage un risque
contractuel qui est une décision Adrian, pas une décision technique.

**L'architecture proposée est en revanche la bonne pour le calendrier** : un worker
de la factory, cadencé, qui maintient un fichier versionné depuis les sources
publiques. C'est l'option A du ticket.

### T10 — analyse de fond des 54 h de lives + inventaire outils — 2026-09-06

`support/designs/SPEC_methode-doud-reconstruite_2026-09-06.md`. Corpus **mesuré**
et non échantillonné : lexique compté sur les 35 lives, ratios extraits (n=24,
médiane 7,50), amplitudes (n=209, médiane 3000 points), puis 7 étages de méthode
sourcés à l'horodatage, puis inventaire outil par outil de ce qui manque à tbot.

Trois constats qui engagent la suite :
1. Son système est **zones + liquidité** (1581 occurrences) et non « équilibre »
   (87). S018 avait fait de l'équilibre son commutateur central — erreur de
   pondération autant que de traduction.
2. Ses « 89 % de réussite » et ses « R:R 7-17 » **ne portent pas sur la même
   population** : le stop suiveur fabrique une majorité de petits gains, les
   ratios cités sont les runners. Un backtest à sortie unique ne peut pas
   reproduire cette distribution — c'est une raison de fond, pas un détail.
3. **TCK-018** (découverte incidente, transverse au projet) : le catalogue
   déclare 25 pips de spread sur XAUUSD, nos barres en enregistrent 50-58
   (médiane, heures actives comprises). Facteur 2. Edge H1 recalculé : +0,236 →
   +0,205 R/trade (tient) ; M15 : −0,096 → −0,150 (empire). Aucun verdict ne
   bascule ; tous les chiffres or du dépôt sont optimistes d'un montant
   désormais connu, là où `gold_forward/PROTOCOL.md` §2.2 le disait inconnu.

Manques outillage identifiés : M1 et H2 absents de `_TF`, calendrier économique
(TCK-016), sorties partielles + trailing (TCK-014), spread par barre (TCK-018),
fractionnement d'entrée (core/risk, TCK-015).

Plan proposé en 6 étapes, ordonné par ce que chacune apprend — étape 2 (S019,
entrée seule) est le point de décision : si son déclencheur n'a pas d'edge,
TCK-014 devient sans objet.

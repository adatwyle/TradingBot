# SPEC — Watcher PC prod (mise à jour automatique + redémarrage propre)

**Version** : 1.0.0 — 2026-08-26 · **Auteur** : cc-spec · **Statut** : prête pour implémentation
**Sources** : input-adrian 02 (multi-PC), 03 (console), 09 (trou n°5) ; PLAN T4 ; héritage
`app/orchestrator/robinbot-factory.py` (.stop, verrou, arrêt propre), `app/core/paths.py`.
**Implémente** : `app/orchestrator/prod-watcher.py`, `app/orchestrator/run-prod.bat`,
amendement mineur `run-factory.bat` (aucun), + exigence croisée SPEC_backup-github.

## 1. Objectif

Le PC prod observe cycliquement `origin/main`, se met à jour (`git pull --ff-only`),
et redémarre proprement la console (`.stop` → attente fin des ticks → relance).
Si les tests d'intégrité locaux échouent après pull : rollback au SHA précédent.

## 2. Décisions tranchées

| # | Décision | Motivation (1 ligne) |
|---|----------|----------------------|
| D-PW-1 | Le watcher est une **tâche englobante** (wrapper qui lance la factory en enfant), pas un worker de la factory | On ne se met pas à jour depuis l'intérieur du processus qu'on remplace : un worker ne peut ni arrêter ni relancer son propre parent proprement. |
| D-PW-2 | Période de poll : **300 s** (`TBOT_WATCH_POLL`) | Une mise à jour n'est jamais urgente à la minute ; 5 min limite les fetchs réseau tout en restant réactif. |
| D-PW-3 | Tests d'intégrité post-pull = `python -m pytest app -q` (suite app complète, pas `strategies/`) | C'est la même suite que la CI pour le code qui tourne en prod ; les tests stratégies n'exécutent rien en prod et allongeraient chaque mise à jour. |
| D-PW-4 | Rollback = `git reset --hard <SHA précédent>` (SHA enregistré avant pull) | Le checkout prod est déclaré sans travail local (PW-4) : le SHA enregistré est le filet exigé par la règle git, le reset est donc sûr. |
| D-PW-5 | Un diff `old..new` qui ne touche **que** `db-backup/` ⇒ pull sans redémarrage de la console | Un commit de backup ne change pas le code ; redémarrer la console pour lui interromprait les ticks pour rien (cohérence SPEC_backup-github). |
| D-PW-6 | Alerte Telegram directe best-effort via le token notifier s'il existe, sinon log seul | Un rollback en prod doit réveiller Adrian ; réutiliser le token (simple POST sendMessage) évite tout couplage avec les curseurs du notifier. |

## 3. Exigences

### Script `app/orchestrator/prod-watcher.py`

- **PW-1** — Boucle principale : (a) s'assurer que la factory tourne (la lancer en
  sous-processus `python app/orchestrator/robinbot-factory.py`, cwd = racine projet, même console) ;
  (b) toutes les `TBOT_WATCH_POLL` s (défaut 300) : `git fetch origin main` puis comparaison
  `git rev-parse HEAD` vs `git rev-parse origin/main`.
- **PW-2** — SHA identiques → rien (log heartbeat max 1×/h). SHA différents → séquence de
  mise à jour PW-5.
- **PW-3** — Verrou single-instance du watcher (fichier `.prod-watcher.lock` horodaté,
  même mécanique stale que la factory). Deux watchers = deux factories = interdit.
- **PW-4** — Pré-condition à toute mise à jour : `git status --porcelain` vide et branche
  courante `main`. Sinon : **aucun pull**, alerte « checkout prod sale/divergent » (PW-9),
  la factory continue sur le code courant.
- **PW-5** — Séquence de mise à jour :
  1. si diff `HEAD..origin/main` limité à `db-backup/` (D-PW-5) : `git pull --ff-only` sans
     arrêt de la console, fin ;
  2. sinon : enregistrer `OLD_SHA` ; créer le fichier `.stop` de la factory
     (`RBF_STOP`, défaut `app/orchestrator/.stop`) ;
  3. attendre la sortie du processus factory (elle laisse finir les ticks en vol) —
     timeout `TBOT_WATCH_STOP_TIMEOUT` (défaut 1800 s) ; dépassé → `terminate()` du
     processus + alerte « arrêt forcé » ;
  4. supprimer `.stop` ; `git pull --ff-only origin main` (échec ff → alerte, pas de retry
     automatique, factory relancée sur `OLD_SHA`) ;
  5. `python -m pytest app -q` (D-PW-3). Vert → relancer la factory sur le nouveau code ;
     rouge → `git reset --hard OLD_SHA`, relancer la factory, alerte « rollback » (PW-9) ;
  6. après un rollback, le SHA fautif est mémorisé dans l'état : il n'est **pas retenté**
     tant que `origin/main` n'a pas avancé au-delà (anti-boucle de rollback).
- **PW-6** — Si le processus factory meurt sans `.stop` (crash) : relance après
  60 s de backoff, alerte au 3ᵉ crash en moins d'1 h (puis backoff 1 h).
- **PW-7** — Journalisation : `app/orchestrator/logs/prod-watcher.log` (rotation naïve
  2 Mo → `.1`, motif factory) — chaque check, chaque mise à jour, chaque rollback, horodatés.
- **PW-8** — État publié pour l'UI : `db_dir()/watcher/status.json` réécrit à chaque cycle
  (écriture atomique tmp+replace) :
  `{"schema":1, "generated_at_utc", "current_sha", "current_version" (VERSION), "remote_sha",
  "last_check_utc", "last_update_utc", "last_result": "up-to-date|updated|rolled-back|dirty|error",
  "detail": str, "factory_alive": bool}`.
- **PW-9** — Alerte (rollback, checkout sale, arrêt forcé, échec ff) : ligne `!!` dans le log
  **+** envoi Telegram best-effort (D-PW-6) via `C:\db\tradingBot\notifier\token.txt` +
  `config.json` (chat_id) s'ils existent ; jamais d'exception propagée si Telegram échoue.
- **PW-10** — Chemins exclusivement via `core.paths` (`project_root()`, `db_dir()`) ;
  seams d'env pour les tests : `TBOT_WATCH_POLL`, `TBOT_WATCH_STOP_TIMEOUT`,
  `TBOT_WATCH_DIR` (défaut `db_dir()/watcher`), `RBF_STOP`.
- **PW-11** — Le watcher n'exécute jamais : commit, push, force-push, checkout de branche.
  Son vocabulaire git est fermé : `fetch`, `rev-parse`, `status`, `diff`, `pull --ff-only`,
  `reset --hard <SHA enregistré>` (rollback uniquement).

### Lanceurs .bat

- **PW-12** — `app/orchestrator/run-prod.bat` (PC prod) : même gabarit que `run-factory.bat`
  (title `TradingBot prod`, `chcp 65001`, cd racine, `pause` final) mais lance
  `python app\orchestrator\prod-watcher.py %*`.
- **PW-13** — PC dev : `run-factory.bat` existant inchangé (pas de watcher en dev — le dev
  pushe, il ne s'auto-met pas à jour).

## 4. Tests attendus (cc-app)

- **PW-T1** — Repo git jetable (tmp_path, `git init` + remote fichier) : détection SHA
  différent, pull ff, non-redémarrage si diff limité à `db-backup/`.
- **PW-T2** — Simulation tests rouges (suite pytest factice injectée par seam) → rollback
  au SHA enregistré + SHA fautif non retenté.
- **PW-T3** — Checkout sale → aucun pull, status.json `dirty`.
- **PW-T4** — Arrêt propre : factory factice (script qui attend `.stop`) → `.stop` créé,
  attente sortie, relance ; timeout → terminate.

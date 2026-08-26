# SPEC — Worker backup GitHub (journaux et états légers → db-backup/)

**Version** : 1.0.0 — 2026-08-26 · **Auteur** : cc-spec · **Statut** : prête pour implémentation
**Sources** : input-adrian 02 (backup : tout sous GitHub sauf datas de backtest), 06
(worker backup proposé), 09 (D4) ; PLAN T8 ; héritage factory (nature tick, codes de
sortie), `.gitignore` racine.
**Implémente** : `app/orchestrator/robinbot-backup.py` + entrée catalogue factory
(`backup`, tick, 3600 s) + ligne gabarit panneau (livrée `off`).

## 1. Objectif

Pousser cycliquement les journaux et états légers de `C:\db\tradingBot\` vers le repo
(dossier `db-backup/`), commit automatique sur `dev`, message horodaté, cadence 1×/jour
+ à la demande, idempotent, silencieux si rien n'a changé. Jamais les secrets, les
datasets ni les caches (D4).

## 2. Décisions tranchées

| # | Décision | Motivation (1 ligne) |
|---|----------|----------------------|
| D-BK-1 | Worker **tick** de la factory, catalogue 3600 s, avec **garde interne 24 h** + déclencheur à la demande (fichier `.push-now` ou `--now`) | Le tick horaire rend le « à la demande » réactif (≤ 1 h, ou immédiat via `--now`) tandis que la garde interne assure le 1×/jour sans mécanique de cron. |
| D-BK-2 | Sélection par **allowlist de noms exacts** (jamais « tout sauf ») | Un backup fail-closed : un fichier nouveau/inconnu n'est jamais poussé par accident — c'est l'inverse du panneau mais la même philosophie (le doute n'ouvre rien). |
| D-BK-3 | Miroir avec suppression (fichier disparu de la source ⇒ supprimé de `db-backup/`) | Le repo reflète l'état courant ; l'historique git garde le passé, pas le dossier. |
| D-BK-4 | Commit message `backup: db-backup YYYY-MM-DD HH:MM [skip ci]` | Horodaté (exigence) et `[skip ci]` (D-CI-6) : un backup ne déclenche ni tests ni publication sur `main`, donc jamais de restart prod pour un backup (D-PW-5 couvre le résiduel). |
| D-BK-5 | Actif uniquement si la branche courante est `dev` ; sur `main` (PC prod) : sortie 0 + note de log | Le contrat CI interdit tout push direct sur `main` ; le backup des données prod sera re-décidé à E6 (noté dans le ticket de livraison). |
| D-BK-6 | Plafond 10 Mo par fichier (au-delà : ignoré + avertissement dans status.json) | Les états légers font des Ko ; un fichier de 10 Mo dans l'allowlist est un dataset égaré, pas un état. |

## 3. Exigences

### Sélection (allowlist)

- **BK-1** — Racine source : `db_dir()`. Fichiers copiés, à toute profondeur, si leur
  **nom exact** est l'un de : `journal.csv`, `status.json`, `state.json`, `config.json`,
  `events.csv` — plus, à la racine : `robinbot-panel.txt` (le panneau : hors repo comme
  surface de contrôle, mais son contenu est un état à sauvegarder).
- **BK-2** — Exclusions absolues, prioritaires sur BK-1 (défense en profondeur) : tout
  chemin contenant un segment `secrets`, `datasets`, `bars_cache`, `cache`, `db-backup` ;
  tout nom contenant `token`, `key`, `secret` ; extensions `.db`, `.db-wal`, `.db-shm`,
  `.parquet`, `.pkl`, `.log` ; le fichier `.push-now`.
  (`config.json` est copiable : il porte des chat_id, pas des credentials — les tokens
  vivent dans `token.txt`, exclus deux fois : nom + `.gitignore`.)
- **BK-3** — Plafond par fichier : 10 Mo (D-BK-6). Fichier au-delà : non copié,
  listé dans `status.json` du worker (`"skipped_oversize"`).

### Miroir et commit

- **BK-4** — Destination : `project_root()/db-backup/<chemin relatif depuis db_dir()>`.
  Copie seulement si contenu différent (taille+mtime puis comparaison d'octets en cas de
  doute) ; suppression des fichiers du miroir disparus de la source (D-BK-3).
- **BK-5** — Idempotence/silence : après le miroir, si
  `git status --porcelain -- db-backup/` est vide → **sortie 0**, aucun commit, aucun
  push, une ligne de log au plus.
- **BK-6** — Sinon : `git add -A -- db-backup/` puis `git commit -m "backup: db-backup
  <YYYY-MM-DD HH:MM> [skip ci]" -- db-backup/` (chemin restreint : jamais un fichier
  hors `db-backup/` embarqué, même si le reste du working tree est sale).
- **BK-7** — Push : `git push origin dev`. Rejeté (remote a avancé) →
  `git fetch origin` + `git rebase origin/dev` (le commit backup rebase toujours
  proprement : `db-backup/` n'a qu'un seul écrivain) puis un seul retry ; échec encore →
  sortie 2 (retenté au prochain déclenchement), le commit local reste en place.
- **BK-8** — Garde-fou de cohérence : après BK-6, `git check-ignore` sur les fichiers
  copiés ; un fichier allowlisté ignoré par `.gitignore` = avertissement dans
  status.json (il serait silencieusement absent du backup).

### Déclenchement et état

- **BK-9** — À chaque tick : exécuter le miroir+commit+push seulement si (a) dernier
  backup réussi > 24 h (état `last_success_utc` dans `db_dir()/backup/status.json`), ou
  (b) fichier `db_dir()/backup/.push-now` présent (supprimé après prise en compte), ou
  (c) flag CLI `--now`. Sinon : sortie 0 immédiate.
- **BK-10** — `db_dir()/backup/status.json` (écriture atomique, affiché par l'UI UI-5) :
  `{"schema":1, "generated_at_utc", "last_success_utc", "last_result":
  "pushed|nothing-to-do|skipped-branch|error", "n_files", "n_changed",
  "skipped_oversize":[…], "warnings":[…]}`.
- **BK-11** — Codes de sortie : `0` OK (y c. rien à faire, mauvaise branche), `2` push
  impossible (réseau/rejet persistant), `1` erreur inattendue. Jamais 3/4.
- **BK-12** — Chemins via `core.paths` uniquement ; seams : `TBOT_BACKUP_DIR`
  (défaut `db_dir()/backup`), `RBF_ROOT`/`TBOT_PROJECT_ROOT` (repo cible) — les tests
  montent un repo git jetable et un faux `db_dir()` en tmp_path.
- **BK-13** — Entrée catalogue factory : `("backup", ROOT,
  "py:app/orchestrator/robinbot-backup.py", 3600, "tick")` ; gabarit du panneau livré
  avec `backup = off` (Adrian l'allume sur le poste où vivent les données — un seul
  poste écrivain, cohérent D-BK-5/BK-7).

## 4. Tests attendus (cc-app)

- **BK-T1** — Allowlist : arborescence de fixtures (journaux, status, secrets/, tokens,
  parquet, oversize) → seuls les fichiers légitimes copiés ; exclusions BK-2 vérifiées
  une par une.
- **BK-T2** — Idempotence : deuxième passage sans changement → aucun commit (dry-run
  PLAN T8).
- **BK-T3** — Miroir : modification → recopie ; suppression source → suppression miroir.
- **BK-T4** — Commit restreint : working tree sale hors `db-backup/` → le commit ne
  contient que `db-backup/`.
- **BK-T5** — Garde 24 h + `.push-now` + `--now` ; branche `main` → sortie 0 sans action.
- **BK-T6** — Push rejeté (remote avancé dans le repo de test) → rebase + retry réussi.

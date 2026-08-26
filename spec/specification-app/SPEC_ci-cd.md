# SPEC — CI/CD GitHub Actions (dev → main)

**Version** : 1.0.0 — 2026-08-26 · **Auteur** : cc-spec · **Statut** : prête pour implémentation
**Sources** : input-adrian 02 (CI/CD), 09 (trou n°5) ; PLAN T3 ; repo `adatwyle/TradingBot`.
**Implémente** : workflow GitHub Actions + fichiers `VERSION` et amendement `app/requirements.txt`.

## 1. Objectif

Push sur `dev` → suite pytest complète (app + stratégies). Verte → publication automatique
sur `main` (fast-forward) + tag de version. Une modification qui échoue aux tests
n'atteint **jamais** `main`.

## 2. Décisions tranchées

| # | Décision | Motivation (1 ligne) |
|---|----------|----------------------|
| D-CI-1 | Runner `ubuntu-latest` | La suite est OS-agnostique (seams d'env + `tmp_path`, aucun appel Windows dans les tests) et MetaTrader5 est en import paresseux ; ubuntu est plus rapide et gratuit en minutes. |
| D-CI-2 | `app/requirements.txt` : ligne MT5 amendée en `MetaTrader5 ; sys_platform == "win32"` | Le paquet pip n'existe pas sous Linux ; le marqueur d'environnement est le mécanisme pip standard, zéro fichier requirements supplémentaire. |
| D-CI-3 | Publication = `git push origin dev:main` après vérification ancêtre (ff strict) | Un fast-forward par construction : `main` ne peut jamais diverger de `dev`, aucun merge commit, aucun force-push. |
| D-CI-4 | Tag créé **seulement si** `vVERSION` n'existe pas encore | Publication toujours automatique (exigence Adrian) sans casser les pushes documentaires ; un tag = une version nommée, jamais déplacé. |
| D-CI-5 | Version lue dans `VERSION` racine (fichier à créer, contenu initial `1.0.0`) | Source unique lisible par CI, watcher, UI ; format MAJOR.MINOR.BUILD conforme au versionning Adrian. |
| D-CI-6 | Commits contenant `[skip ci]` non testés/publiés (comportement GitHub natif) | Réservé au worker backup (SPEC_backup-github) : un backup quotidien ne doit pas provoquer une publication ni un restart prod. |

## 3. Exigences

- **CI-1** — Fichier `.github/workflows/ci.yml` unique. Déclencheurs : `push` sur `dev`,
  `workflow_dispatch` (relance manuelle). Aucun déclencheur sur `main`.
- **CI-2** — `concurrency: group: ci-dev, cancel-in-progress: false` : jamais deux
  publications en parallèle (course sur `main` interdite).
- **CI-3** — Job `test` :
  1. checkout profondeur complète (`fetch-depth: 0`, requis pour le ff-check et le tag) ;
  2. `actions/setup-python` Python **3.11**, avec `cache: pip` clé sur `app/requirements.txt` ;
  3. `pip install -r app/requirements.txt` ;
  4. `python -m pytest app strategies -q` depuis la racine du repo. Code retour ≠ 0 ⇒ échec du job.
     (`pytest` code 5 « aucun test collecté » dans `strategies/` seul est impossible car `app/` en contient toujours.)
- **CI-4** — Job `publish`, `needs: test`, exécuté seulement si `github.ref == 'refs/heads/dev'` :
  1. lit `VERSION` racine → `V` (regex stricte `^[0-9]+\.[0-9]+\.[0-9]+$`, sinon échec explicite) ;
  2. vérifie `git merge-base --is-ancestor origin/main HEAD` ; si faux : **échec** avec message
     « main a divergé — intervention manuelle requise » (jamais de force-push, D-CI-3) ;
  3. `git push origin HEAD:main` (fast-forward garanti par l'étape 2) ;
  4. si le tag `v$V` n'existe pas : `git tag v$V && git push origin v$V` ; s'il existe déjà
     **sur le même commit ou un ancêtre** : log « version inchangée, pas de nouveau tag », succès.
- **CI-5** — Permissions du workflow : `contents: write` uniquement. Aucun secret
  supplémentaire (le `GITHUB_TOKEN` intégré suffit).
- **CI-6** — Protections côté repo (à configurer une fois, documentées dans l'en-tête du yml) :
  `main` — force-push interdit, suppression interdite ; personne ne pushe `main` à la main,
  seul le workflow publie. `dev` — force-push interdit.
- **CI-7** — Fichier `VERSION` créé à la racine (`1.0.0`). Toute évolution fonctionnelle
  de l'app bumpe le BUILD (discipline cc-app, rappelée dans le yml en commentaire).
- **CI-8** — La branche `dev` est (re)créée depuis `main` si absente au moment de
  l'implémentation ; tout travail se pushe sur `dev` uniquement.
- **CI-9** — Aucune étape du workflow n'installe ni ne contacte MT5, Telegram, ou un
  broker : la CI est hermétique (les tests le sont déjà).

## 4. Tests attendus (cc-app)

- **CI-T1** — Test unitaire local du parsing `VERSION` (module partagé `app/core/version.py`,
  fonction `read_version()` utilisée aussi par UI/watcher) : format valide, invalide, fichier absent.
- **CI-T2** — Vérification réelle : premier run Actions vert sur `dev` (critère PLAN T3),
  `main` avancé en ff, tag `v1.0.0` présent.

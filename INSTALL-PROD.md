# INSTALL-PROD — mise en service du PC de production (Dell, Windows 10)

**Décisions Adrian 2026-08-26** :
- Accès GitHub du PC prod = **deploy key SSH lecture seule** (le Dell ne pushe jamais —
  cohérent PW-11 + D-BK-5).
- Cible de bascule des études en vol = **directement le Dell, tBot uniquement**
  (robinbot, le prototype, ne quitte JAMAIS le PC dev).
- Installation **itérative** : une session Claude Code sur le Dell exécute, diagnostique
  les erreurs au lancement, et on installe le manquant au fur et à mesure des constats.
- Démarrage automatique au boot **intégré à l'application** → TCK-013 (cc-app).
  En attendant : raccourci manuel (étape 6).

## Architecture cible

```
PC dev (actuel)          GitHub Actions              PC prod (Dell)
push sur dev ──────────► pytest app+strategies ────► clone en main
robinbot y reste           +studies ; vert →          run-tbot-prod.bat
(exploitation, E6)         main ff + tag vVERSION     = watcher + factory
                                                      se met à jour seul
                                                      (SPEC_prod-watcher)
```

## Rôles pendant l'installation

- **Session Claude Code sur le Dell** : vérifie, diagnostique, installe le manquant.
- **[ADRIAN]** : gestes marqués ainsi (GitHub UI, secrets, double-clic).
- **INTERDIT** : lancer `run-tbot-prod.bat` (ou la factory) depuis une session Claude
  Code — filiation de processus, leçon du 2026-08-21. Toujours par double-clic.

## Étape 1 — accès GitHub (deploy key lecture seule)

1. Sur le Dell :
   `ssh-keygen -t ed25519 -C "tbot-prod-dell" -f %USERPROFILE%\.ssh\id_tbot_prod`
2. **[ADRIAN]** GitHub → repo `adatwyle/TradingBot` → Settings → Deploy keys → Add key :
   coller le contenu de `id_tbot_prod.pub`. **Ne PAS cocher « Allow write access »**.
3. `%USERPROFILE%\.ssh\config` sur le Dell :
   ```
   Host github.com-tbot
     HostName github.com
     IdentityFile ~/.ssh/id_tbot_prod
     IdentitiesOnly yes
   ```
4. Test : `ssh -T git@github.com-tbot` → doit saluer avec le nom du repo.

## Étape 2 — outillage minimal

- `git --version` — sinon installer Git for Windows.
- `python --version` — **3.11 minimum** (requirements), 3.13 recommandé.
- Claude Code : déjà installé sur le Dell (constat 2026-08-26).

## Étape 3 — clone et dépendances

```
git clone git@github.com-tbot:adatwyle/TradingBot.git C:\projects\tradingBot
cd C:\projects\tradingBot
git checkout main
pip install -r app\requirements.txt
```

PW-4 : le watcher exige branche `main` + working tree **propre**. On ne travaille
jamais dans ce clone — le Dell consomme, il ne produit pas.

## Étape 4 — état vivant `C:\db\tradingBot\`

- Créer `C:\db\tradingBot\`.
- Panneau : copier `app\orchestrator\tbot-panel.exemple.txt` →
  `C:\db\tradingBot\tbot-panel.txt`, **tout `off`** (défaut du gabarit). Rien ne
  s'allume avant les GO de bascule (`studies/CUTOVER.md`).
- **[ADRIAN]** secrets — copie manuelle hors git (USB / réseau) depuis le PC dev :
  - `C:\db\tradingBot\tbot-notify\token.txt` + `config.json` : **dès le jour 1** —
    le watcher s'en sert pour ses alertes (rollback, checkout sale, arrêt forcé).
  - `tbot-gateway\` : **NE PAS copier** tant que le gateway tourne côté dev — un token
    Telegram = un seul consommateur `getUpdates`. La bascule du gateway est un geste
    explicite, un seul poste à la fois.
  - `secrets\finnhub_key.txt` : seulement au GO s14 (CUTOVER).

## Étape 5 — gate local

`python -m pytest app -q` → **vert exigé**. Rouge → diagnostiquer (dépendance
manquante, etc.), installer, re-tester. C'est la suite que le watcher rejouera
à chaque mise à jour.

## Étape 6 — premier lancement

**[ADRIAN]** double-clic `app\orchestrator\run-tbot-prod.bat`.
Attendu : header du watcher, lancement factory, puis heartbeat « à jour sur <sha> ».
Vérifier `C:\db\tradingBot\watcher\status.json` : `last_result: up-to-date`,
`factory_alive: true`.

Autostart au boot : en attendant TCK-013, **[ADRIAN]** pose un raccourci vers
`run-tbot-prod.bat` dans `shell:startup` (console visible — règle d'or : fermer
la fenêtre = tout s'arrête).

## Étape 7 — validation bout en bout

Depuis le **PC dev** : commit trivial sur `dev` + push. Attendu sous ~10 min
(CI ~3-5 min + poll 300 s) : CI verte → `main` avance → le Dell logge
« mise à jour X → Y », pose `.stop`, pull, pytest, relance.
`status.json` : `last_result: updated`.

## Étape 8 — itératif : le manquant au fil des constats

La session Claude Code du Dell lit `app\orchestrator\logs\prod-watcher.log` et la
console factory, et installe à la demande :

- **Terminal MT5** + login du compte (lecture) : requis pour gold/s13/alexg
  (études armées) — pas avant leur bascule.
- **CLI `claude` authentifiée** : requise pour les workers `claude:` (juges IA,
  gateway) — installée, vérifier l'auth au moment voulu.
- **Clé Finnhub** : au GO s14.

Chaque manque = constat → installation → re-test. Rien ne s'anticipe.

## Rappels non négociables

- Le Dell ne pushe **jamais** (deploy key RO ; PW-11 ; backup inactif sur `main`, D-BK-5).
- Panneau tout `off` jusqu'au GO Adrian **par étude** (`studies/CUTOVER.md`). La
  procédure de bascule actuelle suppose un rename même volume : elle doit être
  **amendée en cross-machine** (copie vers le Dell + `verify-journal` des deux côtés)
  AVANT le premier GO — à ouvrir en ticket quand le Dell est opérationnel.
- robinbot reste sur le PC dev. Jamais déployé sur le Dell.
- Fermer la fenêtre console = tout s'arrête (règle d'or).

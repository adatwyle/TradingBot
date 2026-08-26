---
id: TCK-013
from: cc-support
to: cc-app
status: open
blocking: false
created: 2026-08-26
---

## Question

Directive Adrian (mise en place du PC prod Dell, 2026-08-26) : le démarrage
automatique du watcher au boot du PC prod doit être **intégré à l'application**,
pas un geste manuel non versionné. Comment l'app installe-t-elle proprement son
propre autostart Windows sans mécanique cachée ?

## Proposition de résolution

Deux flags sur `app/orchestrator/tbot-prod-watcher.py` :

- `--install-autostart` : dépose dans le dossier Démarrage de l'utilisateur
  (`shell:startup`) un lanceur pointant sur `run-tbot-prod.bat`. Variante zéro
  dépendance COM recommandée : un `.bat` d'une ligne
  (`start "" "C:\projects\tradingBot\app\orchestrator\run-tbot-prod.bat"`)
  plutôt qu'un `.lnk`. Idempotent (réécrit), log du chemin créé.
- `--uninstall-autostart` : le retire.

Contraintes : console **visible** au boot (règle d'or « fermer la fenêtre = tout
s'arrête » conservée) — pas de service Windows, pas de tâche planifiée invisible.
Seam d'env pour les tests (`TBOT_STARTUP_DIR`, défaut résolu vers shell:startup)
+ tests tmp_path install / uninstall / idempotence.

Référence : `INSTALL-PROD.md` étape 6 (raccourci manuel en intérim).

## Réponse

(à remplir par cc-app)

# 02 — Environnements et déploiement

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Multi-PC

- **PC de développement** (actuel) : construction de nouvelles stratégies et modification de l'application.
- **PC de production** : exécute l'application en continu. Il observe cycliquement les push GitHub sur la branche de production et se met à jour automatiquement si une nouvelle version est publiée.

## CI/CD

- Repo unique : `https://github.com/adatwyle/TradingBot`. Branche `dev` (travail) → branche `main` (production).
- GitHub Actions : quand l'application ou une stratégie passe les tests unitaires, elle est publiée sur la branche de production. Une modification qui échoue aux tests n'atteint jamais `main`.
- Les stratégies sont versionnées : une version en production (`main`) et une version en développement/validation (`dev`) coexistent.

## Mécanisme validé (GO Adrian 2026-08-26)

- **CI** : `SPEC_ci-cd.md` (pipeline GitHub Actions dev→main, livré). **CD** : `SPEC_prod-watcher.md` (watcher englobant sur le PC prod : poll `origin/main`, `.stop` → fin des ticks en vol → `git pull --ff-only` → tests locaux → relance ; rollback au SHA précédent + alerte Telegram si rouge).
- Le PC dev s'éteint le soir sans impact : le prod ne dépend que de GitHub.
- **Gate d'update (directive Adrian)** : avant d'initier un redémarrage, le watcher consulte les stratégies — chacune peut annoncer qu'un update est possible ou non (`update_safe` : pas de position ouverte, pas de décision d'entrée en cours, pas de fenêtre critique). Trivial tant que tout est RESEARCH ; obligatoire dès qu'une stratégie est PAPER/LIVE. Une interruption momentanée est acceptable par conception (état dans les fichiers, stops côté serveur — R2) ; le gate évite seulement le « vraiment mauvais moment ».
- Le watcher lance la console **tbot-factory** (pas robinbot-factory) : le prototype robinbot n'est jamais déployé via ce canal.

## Lancement

- L'application est un terminal console lancé depuis un **raccourci .bat** sur le PC. Elle ne vit que si la console tourne (« si cette console ne tourne pas, rien ne se passe »).
- Le serveur web (UI) est contenu dans l'application console.

## Backup

- **Tout est sauvegardé sous GitHub** : code, specs, manifests, journaux d'études, états.
- Exception (décision 2026-08-23) : les **datas de backtest** (datasets lourds, régénérables) sont sauvegardées ailleurs, localement (`C:\db\tradingBot\`), hors GitHub.

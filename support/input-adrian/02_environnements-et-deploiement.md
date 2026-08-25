# 02 — Environnements et déploiement

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Multi-PC

- **PC de développement** (actuel) : construction de nouvelles stratégies et modification de l'application.
- **PC de production** : exécute l'application en continu. Il observe cycliquement les push GitHub sur la branche de production et se met à jour automatiquement si une nouvelle version est publiée.

## CI/CD

- Repo unique : `https://github.com/adatwyle/TradingBot`. Branche `dev` (travail) → branche `main` (production).
- GitHub Actions : quand l'application ou une stratégie passe les tests unitaires, elle est publiée sur la branche de production. Une modification qui échoue aux tests n'atteint jamais `main`.
- Les stratégies sont versionnées : une version en production (`main`) et une version en développement/validation (`dev`) coexistent.

## Lancement

- L'application est un terminal console lancé depuis un **raccourci .bat** sur le PC. Elle ne vit que si la console tourne (« si cette console ne tourne pas, rien ne se passe »).
- Le serveur web (UI) est contenu dans l'application console.

## Backup

- **Tout est sauvegardé sous GitHub** : code, specs, manifests, journaux d'études, états.
- Exception (décision 2026-08-23) : les **datas de backtest** (datasets lourds, régénérables) sont sauvegardées ailleurs, localement (`C:\db\tradingBot\`), hors GitHub.

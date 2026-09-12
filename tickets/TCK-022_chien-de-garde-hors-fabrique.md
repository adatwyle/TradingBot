---
id: TCK-022
from: cc-support
to: cc-spec
status: open
blocking: false
created: 2026-09-12
---

## Question

Le 10.09 à 02:08 la machine a redémarré. La fabrique est morte avec elle, et avec la
fabrique le worker `notify` — c'est-à-dire **la seule chose qui aurait pu prévenir
Adrian**. Les cinq études sont restées figées 60 heures, et on ne l'a su qu'en le
demandant. Une surveillance qui meurt avec ce qu'elle surveille ne surveille rien.

Le démarrage automatique au boot (TCK-013, ouvert depuis le 26.08) réduira la
fréquence de l'incident. Il ne règle pas le fond : **tant que l'alerte vit dans le
processus qu'elle doit surveiller, aucun arrêt ne sera jamais signalé.**

## Proposition de résolution

Un **chien de garde hors fabrique**, minimal et sans état :

1. La fabrique écrit un **battement** (`C:/db/tradingBot/heartbeat.json` : horodatage
   UTC + tick courant + liste des workers armés) à chaque cycle de 30 s — une ligne
   dans `tbot-factory.py`, déjà en position de le faire.
2. Un script **séparé**, `tbot-watchdog.py`, sans dépendance à la fabrique ni à `app/`,
   lit ce fichier toutes les N minutes et envoie sur Telegram (token du notifier,
   déjà dans `C:/db/tradingBot/secrets/`) un message **uniquement** quand le battement
   a plus de M minutes (défaut M = 10) — puis un rappel toutes les 6 h tant que ça
   dure, et un « repris » quand le battement revient.
3. **Lancement** : le chien de garde doit survivre à tout ce que la fabrique ne survit
   pas. Deux options à trancher dans la spec :
   - **A** — tâche planifiée Windows toutes les 5 min (« At startup » + répétition).
     Contraire à la règle d'or « console visible » de la fabrique — mais c'est un
     lecteur de fichier de 40 lignes qui ne trade pas, ne lance rien et n'a pas
     d'état : la règle d'or vise l'usine, pas son thermomètre. Reco cc-support.
   - **B** — second lanceur console `run-tbot-watchdog.bat` dans le dossier Démarrage
     (cohérent TCK-013). Meurt au même reboot que la fabrique, mais renaît avec lui
     et prévient si la fabrique, elle, ne renaît pas.
4. Test : battement périmé → un message ; battement revenu → un message ; pas de
   message tant que tout va bien (silence = santé, jamais l'inverse).

Ce que ce ticket ne demande pas : relancer la fabrique automatiquement (c'est TCK-013
et un choix d'Adrian), ni surveiller MT5 (le battement porte déjà « barres
indisponibles » via les workers).

## Réponse

<cc-spec>

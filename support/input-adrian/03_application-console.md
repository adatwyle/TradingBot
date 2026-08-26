# 03 — Application console (terminal)

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Nature

L'application est un **terminal console** : elle vit uniquement tant que la console tourne. Elle contient :

1. Le moteur qui **trade cycliquement chaque stratégie indépendamment** (chaque stratégie à sa propre cadence, sans interférence).
2. Le **serveur web** qui est l'UI utilisateur (chapitre 04).
3. Les workers de service : canal Telegram, orchestrateur de sessions Claude Code headless, backup GitHub.

## Socle repris du prototype (décision D1)

La factory RobinBot est reprise comme fondation, avec ses mécanismes éprouvés :

- Boucle de polling avec ticks éphémères par worker (un tick = un processus neuf ; l'état vit dans les fichiers, un tick tué ne corrompt rien).
- **Panneau de contrôle à chaud** (fichier on/off par worker, relu à chaque cycle, hors repo — un panneau = un poste).
- Contrat de codes de sortie : `0` OK · `2` ressource externe indisponible (réessai) · `3` scellé violé · `4` journal altéré — sur 3/4 la factory **éteint elle-même le worker** (AUTO-OFF) et alerte.
- Verrou single-instance, arrêt propre (Ctrl-C ou fichier `.stop`), timeout par tick, stagger entre départs.
- Sessions IA headless : veille en Python pur (gratuite), session Claude Code seulement quand il y a matière.

## La tbot factory (directive Adrian 2026-08-26)

Le nom de l'application console TradingBot est **tbot factory**. Adrian la démarre à la main dans un terminal ; tant qu'elle tourne, tous les jobs cycliques se font 24/7 — c'est l'interrupteur physique unique du système (doctrine du prototype reprise : **aucune tâche planifiée Windows** ; la collecte GEX S017 posée en Task Scheduler le 2026-08-26 est transitoire et sera retirée dès la factory validée).

Familles de workers demandées :

1. **Collecteurs de données** (`py:`) — par stratégie qui en déclare : ex. snapshot GEX pré-market S017 (jours ouvrés US, avec rattrapage si la console démarre après l'heure).
2. **CC tradeurs** (`claude:`) — une session headless par stratégie selon son statut : `RESEARCH/BACKTESTED` → cycles de développement/mesure (ex. agrégation Phase A S017) ; `PAPER` → préparation pré-market + évaluation de la checklist + prise des trades **paper** pendant la séance ; `LIVE` (un jour) → uniquement sur décision Adrian (R4 : la factory n'arme jamais un trade réel).
3. **CC amélioration continue** — cycle par stratégie : observation des erreurs (logs paper, écarts attendu/réalisé, échecs de collecte), correction et amélioration continues par le cc-S0NN propriétaire de la stratégie. Peut être le même worker que le tradeur avec un mandat distinct.
4. **CC constructeurs d'application** (`claude:`) — cc-app et cc-spec animés par la file `tickets/` (pas de ticket ouvert = pas de session, veille gratuite) ; cc-support-auto sur les tickets bloquants.
5. **Services communs** — porte Telegram entrante (**cc-support-telegram** : chaque message Telegram d'Adrian déclenche une session headless qui répond, l'équivalent du cc-support desktop), notify (sorties Telegram), et à terme serveur web de supervision + backup GitHub — mécanique gateway/notify du prototype reprise.

Panneau de contrôle à chaud : chaque worker individuellement on/off + cadence, sans redémarrage. Économie de tokens systématique : un tick sans matière est un no-op gratuit.

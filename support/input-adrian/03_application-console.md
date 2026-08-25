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

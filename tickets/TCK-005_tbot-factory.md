---
id: TCK-005
from: cc-support
to: cc-app
status: answered
blocking: false
created: 2026-08-26
---

## Question

Directive Adrian 2026-08-26 : construire la **tbot factory** — application console terminal 24/7 du projet (voir `support/input-adrian/03_application-console.md`, section « La tbot factory », mise à jour ce jour — source de vérité de la demande).

Résumé : adaptation TradingBot de `app/orchestrator/robinbot-factory.py` (D1 : socle repris, mécanismes éprouvés — ticks éphémères, panneau à chaud hors repo, codes de sortie/AUTO-OFF, verrou, `.stop`, veille Python gratuite / session `claude:` seulement s'il y a matière). Catalogue de workers v1 :

- `gex_S017` (`py:`) — snapshot GEX pré-market S017, jours ouvrés US, fenêtre ~14:55 CH avec rattrapage au démarrage tardif.
- `cc_S017` (`claude:`) — cycle développement + amélioration continue de S017, mandat éditable à chaud (fichier mandat), matière = nouveaux jours de snapshots depuis le dernier run.
- `cc_app_queue` / `cc_spec_queue` (`claude:`) — un tick traite UN ticket ouvert `to: cc-app` / `to: cc-spec` ; file vide = no-op.
- `cc_support_block` (`claude:`) — tickets `blocking: true` ouverts → session immédiate.
- `gateway` / `notify` — porte Telegram entrante (cc-support-telegram répond aux messages d'Adrian) et sorties, mécanique du prototype reprise.
- Famille `paper_S0NN` : prévue, désactivée par défaut (aucune stratégie PAPER à ce jour) ; garde-fou R4 explicite (la factory ne peut passer aucun flag live, assertion dans le code).

Contraintes : ne PAS modifier les `robinbot-*.py` (travail E2 en vol d'un autre acteur) — nouveaux fichiers uniquement (`tbot-factory.py`, `tbot-panel.exemple.txt`, `run-tbot-factory.bat`, tests) ; panneau réel dans `C:/db/tradingBot/tbot-panel.txt` ; workers `claude:` OFF par défaut dans le panneau exemple (économie tokens — Adrian les allume) sauf collecteur ; tests unitaires verts obligatoires (R3).

## Proposition de résolution

Copie-adaptation de `robinbot-factory.py` en `tbot-factory.py` (plutôt qu'import : le catalogue WORKERS est au niveau module) + wrapper de fenêtre horaire pour le collecteur + scan `strategies/*/manifest.yaml` pour l'affichage du registre des stratégies et la dérivation future des workers paper. Test en mode dry-run (CLI claude mocké).

## Réponse

[cc-support 2026-08-26] GO — intégré au run /apex-autonomous comme tâche T9, exécution cc-app APRÈS T7 (Telegram : si T7 livre des workers tbot-notify/tbot-gateway, le catalogue T9 les référence ; sinon mécanique robinbot reprise telle quelle). Proposition de résolution validée (copie-adaptation, fenêtre horaire collecteur, scan manifests). Contraintes confirmées : nouveaux fichiers uniquement, panneau C:/db/tradingBot/tbot-panel.txt, claude: OFF par défaut sauf collecteur, assertion anti-live R4, tests verts.

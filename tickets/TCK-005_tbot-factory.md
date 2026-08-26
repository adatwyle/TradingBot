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

[cc-app 2026-08-26] **LIVRÉ** (nouveaux fichiers uniquement — aucun `robinbot-*.py`, `app/core/*` ni `app/server/*` touché). Note T7 : aucun tbot-gateway/tbot-notify livré → mécanique robinbot reprise telle quelle (`py:app/orchestrator/robinbot-gateway.py` 30 s, `py:.../robinbot-notify.py` 300 s), cas prévu par le GO.

**Fichiers** :
- `app/orchestrator/tbot-factory.py` — adaptation fidèle de robinbot-factory : ticks éphémères, panneau à chaud fail-closed (absent = OFF), codes 0/2/3/4 + AUTO-OFF, verrou single-instance, `.stop`, timeout par tick, stagger, seams env `TBF_*`. Ajouts : gardes matière Python pur des workers `claude:` (registre `CLAUDE_GUARDS`, spec `claude:<clé>` ; clé inconnue = prompt littéral, forme prototype), prompt par STDIN + flags du prototype (`--output-format json --max-turns`), garde-fou R4 (assertion à l'import refusant tout marqueur live au catalogue + purge `R4_FORBIDDEN_ENV` de l'env des ticks), registre `strategies/*/manifest.yaml` affiché au démarrage + note de dérivation paper_S0NN.
- `app/orchestrator/tbot-collecte-gex-s017.py` — wrapper `py:` : jour ouvré US + heure locale ≥ 14:55 + snapshot canonique du jour absent (rattrapage inclus) ; hors fenêtre : exit 0 no-op silencieux ; échec collecte : exit 2. Fonction pure `should_collect(now, gex_dir)` testée sans mock datetime.
- `app/orchestrator/tbot-panel.exemple.txt` — gabarit commenté (rôle + coût tokens par worker). Défauts : `gex_S017 = on`, tout le reste OFF (claude: = tokens ; gateway/notify = secrets TCK-004 pas posés — vérifié dans leur code : sans token ils sortent en 2 sans crasher, la factory réessaie).
- `app/orchestrator/run-tbot-factory.bat` — démarrage 1-clic.
- `app/orchestrator/test_tbot_factory.py` — 24 tests, 100 % verts (`pytest app/orchestrator/test_tbot_factory.py -q`) : panneau, gardes tickets/S017 (fixtures), fenêtre horaire, R4, catalogue réel cohérent, contrat STDIN avec CLI claude mocké, dry-run sans processus.
- `strategies/S017_ireland_gex/mandat-cc.txt` — mandat cc-S017 éditable à chaud (phase_a, analyse log, études spec, erreurs de collecte, commit dev).

**Démarrage** : double-clic `app/orchestrator/run-tbot-factory.bat` (ou `python app/orchestrator/tbot-factory.py`, options `--once` / `--dry-run`). Panneau réel `C:/db/tradingBot/tbot-panel.txt` créé depuis le gabarit au premier démarrage (déjà fait lors de la validation dry-run). Jamais depuis une session Claude Code (filiation).

**Écarts / choix justifiés** :
1. Timeout tick 3600 s (vs 1200 prototype) : le tick long normal ici est une session claude de développement, pas un pas MT5. Surchargable `TBF_TIMEOUT`.
2. Cooldown anti-rejeu par ticket (6 h `TBF_TICKET_COOLDOWN`, 1 h pour les bloquants) : une session qui échoue à passer `status: answered` ne repaie pas la même réflexion à chaque cadence. Doctrine gateway « consommer avant de payer », appliquée aussi au marqueur de jours cc_S017.
3. Constat au registre : des manifests legacy (s11, s12, s13) déclarent `status: PAPER` hérité du prototype — la factory les affiche « PAPER sans worker » ; aucun worker paper dérivé (conforme v1 : famille prévue, désactivée). Dérivation documentée au catalogue.
4. Sessions headless lancées avec les flags exacts du prototype (pas de `--permission-mode`/`--allowedTools` ajoutés) : les droits d'écriture des CC headless reposent sur la config `.claude/` du repo — à vérifier à la première mise en route réelle.

**Préconisation première mise en route** : lancer avec le panneau par défaut (gex_S017 seul) et observer 1-2 jours de collecte ; poser les secrets Telegram (TCK-004) puis allumer `gateway`/`notify` ; allumer `cc_support_block` ensuite (garde bon marché) ; `cc_app_queue`/`cc_spec_queue`/`cc_S017` en dernier, un par un, en surveillant `app/orchestrator/logs/<worker>/`. Retirer la tâche planifiée GEX transitoire dès la factory validée.

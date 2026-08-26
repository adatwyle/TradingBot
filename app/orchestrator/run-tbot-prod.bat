@echo off
rem ── Lanceur console du PC PROD (watcher + tbot factory) ────────────────────
rem Double-clic = le watcher demarre, lance la factory en enfant dans CETTE
rem console, observe origin/main et se met a jour tout seul (SPEC_prod-watcher).
rem Fermer la fenetre = tout s'arrete (regle d'or). Le `pause` final garde la
rem fenetre ouverte apres une sortie pour qu'un incident reste lisible.
rem PC DEV : ne pas utiliser — run-tbot-factory.bat sans watcher (PW-13, le
rem dev pushe, il ne s'auto-met pas a jour).
rem JAMAIS lancer depuis une session Claude Code (filiation de processus —
rem lecon du 2026-08-21 sur le prototype).
title TradingBot prod
chcp 65001 >nul
rem La racine PROJET est deux niveaux au-dessus (app\orchestrator\ -> racine).
cd /d "%~dp0..\.."
python app\orchestrator\tbot-prod-watcher.py %*
pause

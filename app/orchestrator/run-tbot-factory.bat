@echo off
rem ── Lanceur console de la tbot factory (TradingBot) ────────────────────────
rem Double-clic = l'usine démarre, visible. Fermer la fenêtre = tout s'arrête
rem (règle d'or). Le `pause` final garde la fenêtre ouverte après une sortie
rem pour qu'un incident (verrou, .stop, crash) reste lisible.
rem JAMAIS lancer depuis une session Claude Code (filiation de processus —
rem leçon du 2026-08-21 sur le prototype).
title tbot factory
chcp 65001 >nul
rem La racine PROJET est deux niveaux au-dessus (app\orchestrator\ -> racine).
cd /d "%~dp0..\.."
python app\orchestrator\tbot-factory.py %*
pause

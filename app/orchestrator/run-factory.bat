@echo off
rem ── Lanceur console de la factory RobinBot ─────────────────────────────────
rem Double-clic = l'usine démarre, visible. Fermer la fenêtre = tout s'arrête
rem (règle d'or). Le `pause` final garde la fenêtre ouverte après une sortie
rem pour qu'un incident (verrou, .stop, crash) reste lisible.
title RobinBot factory
chcp 65001 >nul
cd /d "%~dp0.."
python orchestrator\robinbot-factory.py %*
pause

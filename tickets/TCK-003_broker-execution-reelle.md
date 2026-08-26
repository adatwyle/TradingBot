---
id: TCK-003
from: cc-support
to: Adrian
status: open
blocking: false
created: 2026-08-26
---

## Question
La couche broker/exécution réelle (trou connu du prototype : `core/broker/` vide) est exclue du mandat autonome « terminer l'application » : elle exige tes décisions — compte MT5 démo Swissquote pour la validation, politique de risque globale (kill switch, DD max, coupe-circuit quotidien — défauts prototype : DD stratégie >30 % HALT, DD portefeuille >25 % HALT global), et étages de déploiement (zéro argent → 1-5 CHF 0.01 lot → montée).

## Proposition de résolution
Quand tu veux ouvrir ce chantier : cc-spec rédige la spec broker (émission + modification d'ordres, validation live_runner sur démo, checklist d'exécution), avec les seuils de risque ci-dessus comme défauts à confirmer/amender par toi. Rien ne s'arme sans ton geste (R10).

## Réponse
(en attente Adrian)

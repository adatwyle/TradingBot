---
id: TCK-009
from: cc-support
to: cc-app
status: open
blocking: false
created: 2026-08-26
---

## Question

Directive Adrian 2026-08-26 : rendre la tbot factory **capable de faire tourner les études forward du prototype** (`gold_forward`, `s13_forward`, `s14_sentiment`, `macd_ai_paper`, `alexg_paper`) — voir `support/input-adrian/09_reprise-prototype.md` §« Études en vol — migration vers la tbot factory » (protocole de bascule par étude, source de vérité).

État des lieux : code des études dans le prototype `C:/Datas/Projects/TradingBot_9.0.0.x/studies/` (lecture seule) ; repo `studies/` = README seul ; journaux vivants dans `C:/db/tbot/<étude>/` (prototype) ; DB cible `C:/db/tradingBot/<étude>/` (README DB l'anticipe déjà).

Périmètre du ticket = la PRÉPARATION (sans toucher au prototype ni aux journaux vivants) :

1. Migrer le code des 5 études vers `studies/` du repo (verbatim G3 + adaptation des chemins via `app/core/paths.py` → `C:/db/tradingBot/`), avec leurs tests.
2. Ajouter les 5 workers au catalogue tbot-factory (`py:studies/<étude>/run_*.py`, cadences identiques au prototype, **off par défaut** dans le panneau exemple).
3. Outil de vérification d'intégrité de la chaîne de hachage d'un journal (`verify-journal.py` ou équivalent si le socle en a déjà un — le réutiliser), utilisable avant/après déplacement.
4. Vérifier que la chaîne de hachage est indépendante du chemin absolu du fichier (sinon documenter la contrainte dans le runbook).
5. Runbook de bascule par étude (fichier `studies/CUTOVER.md`) : séquence exacte off-robinbot → move journal → verify → on-tbot, avec fenêtre entre ticks.

La BASCULE elle-même (toucher robinbot-panel.txt + déplacer un journal vivant) est HORS ticket : GO Adrian explicite par étude, exécution pilotée par cc-support au moment choisi.

Dépendances : TCK-005 (tbot factory) livré ; socle E2 suffisamment fonctionnel pour que les études tournent depuis le repo (MT5, datasets — même PC, mêmes accès que le prototype).

## Proposition de résolution

Migration verbatim + adaptation minimale des imports/chemins (pattern déjà appliqué au socle E2), un commit par étude pour la traçabilité, dry-run de chaque `run_*.py` en mode sans-écriture (ou sur copie de journal dans un dossier de test) pour prouver l'équivalence de format d'entrée de journal avant toute bascule réelle.

## Réponse

(en attente)

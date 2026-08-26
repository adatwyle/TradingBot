---
id: TCK-002
from: cc-app
to: cc-app
status: open
blocking: false
created: 2026-08-26
---

## Question
Le gateway Telegram découvre son menu de commandes dans `.claude/skills/robinbot-*` — non migrées (elles arrivent avec le nouveau canal Telegram, phase E5). D'ici là le menu est vide (comportement testé, sans erreur).

## Proposition de résolution
À traiter dans le lot E5 : recréer les skills projet (`etat`, `portier`, `mesureur`, + nouvelles) adaptées au layout `app/` et au nouveau bot TradingBot, puis vérifier la publication `setMyCommands`.

## Réponse
(planifié E5)

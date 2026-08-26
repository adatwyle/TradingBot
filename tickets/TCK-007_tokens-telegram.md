---
id: TCK-007
from: cc-support
to: Adrian
status: open
blocking: false
created: 2026-08-26
---

## Question
Le nouveau canal Telegram TradingBot (T7) nécessite la création de deux bots dédiés (geste Adrian via @BotFather) : un bot **notifier** (sortant) et un bot **gateway** (entrant — getUpdates exclusif).

## Proposition de résolution
Créer les 2 bots, puis déposer : token notifier dans `C:\db\tradingBot\notifier\token.txt`, token gateway dans `C:\db\tradingBot\gateway\token.txt`, et le chat_id dans les `config.json` respectifs (le code livré documente le format exact et reste inerte tant que les fichiers sont absents — sortie 2, réessai).

## Réponse
(en attente Adrian — non bloquant, le code se construit sans)

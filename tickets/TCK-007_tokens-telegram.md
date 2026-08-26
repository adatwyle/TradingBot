---
id: TCK-007
from: cc-support
to: Adrian
status: answered
blocking: false
created: 2026-08-26
---

## Question
Le nouveau canal Telegram TradingBot (T7) nécessite la création de deux bots dédiés (geste Adrian via @BotFather) : un bot **notifier** (sortant) et un bot **gateway** (entrant — getUpdates exclusif).

## Proposition de résolution
Créer les 2 bots, puis déposer : token notifier dans `C:\db\tradingBot\notifier\token.txt`, token gateway dans `C:\db\tradingBot\gateway\token.txt`, et le chat_id dans les `config.json` respectifs (le code livré documente le format exact et reste inerte tant que les fichiers sont absents — sortie 2, réessai).

## Réponse
[cc-support 2026-08-26] Résolu par directive Adrian « pose les secrets telegram et active gateway/notify » — **réutilisation des bots existants du prototype** au lieu de la création de 2 bots neufs :
- `C:/db/tradingBot/gateway/` : gateway_token.txt + config.json (chat_id) + state.json (offset) copiés depuis `C:/db/tbot/gateway/` ;
- `C:/db/tradingBot/notifier/config.json` copié ; token notifier = `~/.claude/channels/telegram/.env` (présent) ;
- **Bascule du poller** : `gateway = off` dans le panneau robinbot (annoté « MIGRÉ, ne pas rallumer — conflit getUpdates ») → 90 s → `gateway = on` + `notify = on` dans le panneau tbot. Vérifié : ticks gateway OK 2.0 s et notify OK 1.4 s dans tbot-factory.log (code 0, plus de code 2).
- Le notify robinbot reste ON (sortant pur, pas de conflit de polling — les deux consoles peuvent émettre).
- Option future : si Adrian veut rendre l'entrant à robinbot ou séparer les canaux, créer 2 bots dédiés via @BotFather et échanger les tokens — la structure de fichiers est en place.

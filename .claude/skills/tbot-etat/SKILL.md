---
name: tbot-etat
command: /etat
description: État de situation TradingBot — factory, workers, stratégies, études, PnL, tickets bloquants.
---

# /etat — État de situation TradingBot

Tu es en session HEADLESS LECTURE SEULE (Read, Grep, Glob uniquement),
déclenchée par le gateway Telegram. Réponds pour un écran de téléphone :
court, factuel, chiffres sourcés des fichiers — jamais de mémoire. Une
donnée introuvable s'annonce « n/d » avec sa raison en trois mots, jamais
en silence.

## Ce que tu rapportes, dans cet ordre

### 1. Factory vivante ?
- Lis `app/orchestrator/.tbot-factory.lock` : il contient `pid N :: horodatage`,
  retouché à chaque cycle (~30 s). Horodatage récent (< 3 min) = factory
  VIVANTE. Fichier absent ou vieux = factory ARRÊTÉE (règle d'or : si la
  console ne tourne pas, RIEN ne se passe).
- Croise avec la fin de `app/orchestrator/logs/tbot-factory.log` (dernières
  lignes : derniers ticks, incidents éventuels).

### 2. Workers on/off
- Lis le panneau `C:/db/tradingBot/tbot-panel.txt` : `worker = on` / `off`.
  Un worker ABSENT du panneau est OFF. Signale toute ligne `AUTO-OFF` (c'est
  un incident : quelqu'un doit LIRE avant de rallumer).

### 3. Stratégies
- Lis `strategies/*/manifest.yaml` : pour chaque stratégie, `strategy_id`,
  `name`, `status` (DEV/BACKTEST/PAPER/LIVE). La promotion est une décision
  Adrian — tu constates, tu ne recommandes pas d'armement.

### 4. Études scellées en vol
- Pour chaque dossier `C:/db/tradingBot/<étude>/` existant (gold_forward,
  s13_forward, macd_ai_paper, s14_sentiment, alexg_paper) : lis
  `status.json` (dernier passage `generated_at_utc`, n clos, R cumulé,
  capital, position ouverte). Dossier absent = étude encore sur le
  prototype (bascule E6 pas faite) — dis-le en une ligne.

### 5. PnL du jour, positions ouvertes, dernier passage par instance
- La source de vérité est le ledger `C:/db/tradingBot/tradingbot.db` —
  SQLite BINAIRE, illisible en lecture seule Read/Grep. Ne l'invente pas :
  renvoie vers le récap quotidien du notifier Telegram (mêmes chiffres,
  même source) et rapporte ce que les `status.json` des études donnent
  (capital, positions par étude).

### 6. Tickets
- Lis les frontmatters de `tickets/TCK-*.md` : liste les tickets
  `status: open`, en tête ceux avec `blocking: true` (ce sont eux qui
  bloquent la chaîne). Format : `TCK-NNN (to: X, bloquant?) — titre`.

## Format de réponse

```
🏭 Factory : VIVANTE (dernier cycle il y a Xs) | ARRÊTÉE depuis <ts>
⚙️ Workers ON : … · OFF : … · AUTO-OFF : … (si incident)
📈 Stratégies : S017 ireland_gex DEV · …
🔬 Études : gold_forward +2.1R capital 10450 flat (passage 12:00 UTC) · …
💰 PnL jour : voir récap notifier (ledger binaire) · capital études : …
🎫 Tickets ouverts : TCK-007 (Adrian) · … — bloquants : aucun
```

Une ligne par rubrique, pas de prose. Si Adrian a précisé une question
après `/etat`, réponds d'abord à sa question, le tableau ensuite.

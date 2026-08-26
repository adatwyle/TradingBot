# Études scellées transverses

Études scellées (protocole + hash des paramètres + journaux chaînés). **Le CODE des 5 études en vol est migré ici depuis le prototype (TCK-009/T10, 2026-08-26) — mais leurs journaux vivent et tournent ENCORE dans le prototype (`C:\db\tbot\<étude>\`, lancés par la robinbot factory). Le prototype `C:\Datas\Projects\TradingBot_9.0.0.x\` reste en lecture seule absolue.** La bascule se fait étude par étude, sur GO Adrian explicite, selon `studies/CUTOVER.md` (outil : `studies/verify-journal.py`). Les workers tbot correspondants existent au catalogue, off par défaut.

État au 2026-08-25 (prototype) :

| Étude | État | Note |
|-------|------|------|
| `gold_forward` (S011/XAUUSD H1) | ARMÉE | 2 trades clos, +1,64 R |
| `s13_forward` (S013 AUDCAD D1) | ARMÉE | 0 trade clos (~7/an attendus) |
| `s14_sentiment` (Finnhub + juges IA) | ARMÉE | verdict au plus tôt mi-octobre 2026 |
| `alexg_paper` (26 paires, 4 bras) | ARMÉE 22.08 | ~3 mois avant verdict |
| `macd_ai_paper` | VERDICT RENDU | NE PAS ARMER l'IA |
| `portfolio_forward` | SCELLÉE NON ARMABLE | bug spread SP500/DAX/FTSE |
| `gold`, `grid_per_entry`, `trend_core_50y` | CLOSES | verdicts documentés |

Règle de migration : les journaux chaînés par hachage migrent **intacts** (curseurs compris) — un journal recommencé à zéro perd la collecte.

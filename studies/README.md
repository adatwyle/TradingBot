# Études scellées transverses

Ce dossier accueillera les études scellées (protocole + hash des paramètres + journaux chaînés) lors de la migration E2/E6. **Jusqu'à la bascule (E6), les études vivent et tournent dans le prototype `C:\Datas\Projects\TradingBot_9.0.0.x\studies\` — ne pas dupliquer, ne pas toucher.**

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

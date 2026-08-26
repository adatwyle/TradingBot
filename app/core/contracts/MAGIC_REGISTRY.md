# Registre des Magic Numbers

**Règle R4** — chaque stratégie possède un magic number unique. C'est ce qui
isole ses positions sur le compte Swissquote partagé.

Sans cette isolation : impossible d'attribuer un trade à une stratégie, donc
impossible de faire le reporting fiscal par stratégie, d'afficher une perf
individuelle, ou de bloquer une seule stratégie.

**Toute collision est un bug bloquant.** Vérifié au démarrage par
`core/validation/registry.py`.

## Plan de numérotation

```
13 00 NN
│  │  └── numéro de stratégie
│  └───── réservé (00)
└──────── préfixe RobinBot v2
```

| Magic | Stratégie | Source | Statut |
|-------|-----------|--------|--------|
| `130001` | `s01_fxalexg_swing` | fxalexg — swing HTF | RESEARCH |
| `130002` | `s02_creamer_auction` | Chris Creamer — auction / orderflow | RESEARCH |
| `130003` | `s03_brendan_llm_pm` | Brendan — Claude gérant de portefeuille | RESEARCH |
| `130004` | `s04_aipathways_trendcore` | AI Pathways — bascule MM200 QQQ/GLD | RESEARCH |
| `130005` | `s05_flossbach_liqsweep` | Tim Flossbach — liquidation sweep | RESEARCH |
| `130006` | `s06_nil_pbd` | Patrick Nil — impulsion + range (« PBD ») | RESEARCH |
| `130007` | `s07_ionita_gaussian` | Michael Ionita — canal gaussien long & short (allocation) | RESEARCH |
| `130008` | `s08_markov_regime` | Lewis Jackson / « Ran » — chaîne de Markov sur régimes (allocation) | RESEARCH |
| `130009` | `s09_balke_rangebreakout` | René Balke — range breakout de session (BM Trading) | RESEARCH |
| `130010` | `s10_legacy_meanrev` | RobinBot interne — S1 historique | RESEARCH |
| `130011` | `s11_legacy_breakout` | RobinBot interne — S2 historique | RESEARCH |
| `130012` | `s12_prt_macd_meanrev` | ProRealTime — Daily MACD mean reversion SP500 D1 | RESEARCH |
| `130013` | `s13_macd_fx` | Mandat Adrian — exploration de conception MACD sur forex D1 | RESEARCH |
| `130015` | `s15_cot_positioning` | Rapport COT / CFTC — positionnement des gros opérateurs, contrats directs (XAUUSD, EURUSD) D1 | RESEARCH |
| `130016` | `s16_confluence` | Mandat Adrian — confluence de 4 lectures (technique, sentiment, anticipations, avis de Claude), score calibré | RESEARCH |
| `130090` | `s90_adrian_synthesis` | Synthèse des verdicts validés | RESEARCH |
| `130091` | `s91_claude_scratch` | Conception autonome Claude | RESEARCH |
| `130092` | `s92_claudetrader` | Agent headless cyclique (concept Hermes) | RESEARCH |
| `130093` | `s93_alexg_ai_judge` | fxalexg v2 + juge IA (grading confluences) | RESEARCH |

## Réservations

- `130014` : **non attribué, volontairement**. Le numéro « 14 » est porté par
  `studies/s14_sentiment/` (étude scellée sur le sentiment des news, sans
  trading donc sans magic). Laisser `130014` libre évite qu'il existe deux
  objets « s14 » de nature différente dans le dépôt. Ne pas le réattribuer.
- `130017` – `130089` : futures stratégies internes
- `130094` – `130099` : expérimentations Claude

## Historique (v1 — ne pas réutiliser)

L'ancienne architecture Pulse utilisait `120001`-`120004` et `120099`. Ces
numéros sont **retirés** pour éviter toute confusion avec d'anciennes positions.

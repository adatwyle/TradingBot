# PLAN — /apex-autonomous « reprends toutes les tâches abordées dans cette session et termine-les » — 2026-09-12 19:00

**GO Adrian 19:00** (verbatim) : « l'ATR Candle Breakout sur l'or — que je peux construire maintenant … Go Long et
Turnaround Tuesday demandent l'intraday des indices (MT5 est revenu ; DAX et NASDAQ sont au catalogue, US30 non). GO »

## Tâches

| # | Tâche | Dépend de | Vérification | État 2026-09-13 |
|---|---|---|---|---|
| T1 | s20_forward tourne sous la fabrique : deux passes horaires au journal (16:35Z + suivante) | — | `C:/db/tradingBot/s20_forward/journal.csv` ≥ 2 mesures, status.json à jour | fait (19:36) |
| T2 | Corpus Balke dans le dépôt : `docs/sources/renebalke/corpus/`, `site/`, `CORPUS_INDEX.md`, script idempotent `tools/build_corpus.py` | — | 23 transcripts + 11 billets + index 773 lignes ; script rejouable | fait, dépassé (27 puis 69 transcripts, 84/773) |
| T3 | Données intraday indices : NASDAQ/DAX/SP500 H1 en cache ; US30 ajouté au catalogue (mesuré sur MT5) + H1/D1 chargés | — | pkl présents, `pytest app/core/data` vert, spread mesuré rapporté | fait (US30, TCK-018 ouvert) |
| T4 | S022 ATR Candle Breakout or H1 : règle, manifest (RESEARCH, 130022), tests, FALSIFICATION avant mesure, harnais, mesure, VERDICT, fidélité vs chiffres publiés | — | `pytest strategies/S022_* ` vert, results.json, VERDICT rendu | fait — ÉCHEC critères |
| T5 | S023 Turnaround Tuesday (DAX, NASDAQ, US30) H1 : règle, filtre SMA D1, sortie mardi soir via max_hold_bars, garde catastrophe propre, FALSIFICATION, mesure, VERDICT | T3 | idem | fait — ÉCHEC critères |
| T6 | S024 Go Long (DAX, NASDAQ, US30) H1 : entrée/sortie horaires, témoin aléatoire + acheter-et-tenir, FALSIFICATION, mesure, VERDICT | T3 | idem | fait — bêta indiciel |
| T7 | Tranche 1 : `SYNTHESE_tranche1_2026-09-12.md` dès la fin du workflow ; tranche 2 : transcripts Whisper disponibles analysés par lots ; `SYNTHESE.md` mise à jour | T2 (index) | synthèses écrites, index à jour | **partiel** : tranches 1-2 écrites, `SYNTHESE.md` raccordée en Phase X (2026-09-13) |
| T8 | Lot du 26-27.08 non commité : revu (cosmétique + 2 skills), tests verts (551), commité | — | fait — commit ci-dessus | fait (f40118f) |
| T9 | Phase X : pytest complet, revue finale du cumul, de-sloppify, CHANGELOG, SHARED_TASK_NOTES, push | T1-T8 | tout vert, dev poussé | **partiel** : tests verts, push fait (dev = origin/dev), CHANGELOG et CLAUDE.md complétés en Phase X (2026-09-13) |

Hors plan mais livré : SPEC_analytics-trades + module `/analytics` v1.1.3 (override cc-support → cc-spec/cc-app, directive Adrian 19:03).

## Règles du run
- Un seul écrivain git : l'orchestrateur commit, chemins limités ; les implémenteurs ne lancent aucune commande git.
- Interdits : `app/core/backtest/engine.py`, `anchored_wf.py`, `studies/gold_forward/`, `strategies/S011_legacy_breakout/`, toute étude scellée ; fabrique jamais lancée depuis la session.
- Chaque stratégie porte ses règles (Adrian 2026-09-12) : les règles communes anti-pertes consécutives sont mesurées en second bras, pas imposées au bras fidèle.
- Aucune promotion PAPER/LIVE (R10) : les trois stratégies restent RESEARCH → BACKTESTED.

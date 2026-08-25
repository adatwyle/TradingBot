# input-adrian — S004 AI Pathways Trend Core

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S004 · magic `130004`
- **Source** : YouTube — chaîne AI Pathways (Brendan), vidéo `https://www.youtube.com/watch?v=Fb7G5SNpaes`
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s04_aipathways_trendcore\` (lecture seule)

## Principe (résumé)
Allocation à commutation QQQ/GLD sur la moyenne mobile 200 jours, en D1 : long NASDAQ tant que la clôture est au-dessus de la MM200, repli sur l'or en dessous, toujours investi (aucun état flat, pas de stop d'invalidation — la sortie est le retournement de régime). Substituts du prototype : NASDAQ CFD / XAUUSD spot. Famille : contrat allocation, pas le contrat épisodique `Signal(entry, stop, target)`.

## État hérité du prototype
- **Statut manifest** : `RESEARCH` (jamais promu ; recommandation explicite du verdict : ne pas passer en PAPER).
- **Verdict Phase 4 (`research/VERDICT.md`)** : `NON CONCLUSIF (données insuffisantes)` — 14 bascules sur 4,31 ans, un seul épisode baissier (2022). Sur la fenêtre : CAGR +23,02 % / Sharpe 1,23 / DD −16,96 % contre +20,01 % / 0,90 / −25,33 % pour le buy & hold NASDAQ, mais IC 95 % du différentiel de Sharpe [−0,40 ; +0,97], et le 50/50 naïf NASDAQ+or fait aussi bien (Sharpe 1,26).
- **Verdict architectural** (même document) : le contrat `Signal(entry, stop, target)` ne couvre pas cette famille d'allocation — walk-forward moteur dégénéré (1 à 2 trades sur 5 ans), mesure faisant foi = comptabilité d'équity dédiée.
- **Clôture par l'étude `studies/trend_core_50y/`** : sur 55,5 ans et 284 bascules, la règle rend un Sharpe de 0,71 contre 0,81 pour le 50/50 rebalancé quotidiennement — ΔSharpe **−0,100**, IC 95 % [−0,382 ; +0,147], **77,9 %** des tirages défavorables (contrôle S&P 500 : −0,133, 85,1 %). Aucune longueur de MM (100 à 300) ne renverse le verdict. Conclusion verbatim : « Le dossier s04 est clos. » L'étude a servi de démonstration pour créer le contrat AllocationModule (`core/backtest/allocation_engine.py` + `contracts/allocation.py`), réutilisable pour toute règle d'allocation journalière.
- **Acquis réutilisables** : la MM200 est un filtre de volatilité (rapport de vol 1,96x sous/sur la MM), pas de rendement (t = 0,56) ; seule piste non réfutée par l'étude 50 ans = repli en **cash** au lieu de l'or (Sharpe 0,78, reste toutefois sous le 0,81 du 50/50) — et ce n'est plus la stratégie de la source.
- **Dette héritée** : R4 — magic 130004 réservé (plage 130003-130009) mais non inscrit au `MAGIC_REGISTRY.md` du prototype.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC dédié, documenté ; le double verdict hérité est une donnée d'entrée, pas un arrêt de mort).
- L'archivage n'est jamais prononcé sur la seule foi du prototype : si le CC confirme la clôture, il documente son propre constat (au minimum en recoupant l'étude 50 ans) avant le statut `RETIRED`.

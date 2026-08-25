# input-adrian — S011 Legacy S2 — Donchian + filtre de régime

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S011 · magic `130011`
- **Source** : Stratégie historique #2 du projet (TBOT 2026 — `s2_breakout.py` / `s2_breakout_filtered.py`)
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s11_legacy_breakout\` (lecture seule)

## Principe (résumé)
Suiveur de tendance par cassure de canal Donchian (20/40) sur H1, 8 instruments (DAX, NASDAQ, SP500, FTSE, NIKKEI, XAUUSD, EURJPY, USDJPY). Entrée si cassure du canal décalé, filtrée par ADX > seuil **et croissant** (lookback 5), confirmation DI (+DI/−DI), ratio de volatilité `ATR > 0,8 × SMA50(ATR)`, garde RSI anti-extrême (75/25). Sortie mécanique : SL 1,5 ATR, TP 4 ATR (R:R 2,67). Filtre de régime `combo_011_050` par-dessus : suspension des nouvelles entrées si `ER200 < 0,11` ou `failed_rate200 > 0,50` (seuils traités en paramètres de grille, avec témoin filtre désactivé).

## État hérité du prototype
Donnée d'entrée, pas un arrêt de mort. Statut manifest : **PAPER** — la plus avancée du dépôt.

**Verdict Phase 4 (`research/VERDICT.md`, walk-forward ancré 2021-2026, 128 configs × 8 instruments = 1024 cellules, R1 passé sur 16 points de grille + couche indicateur)** :
- **Global : `PAS D'EDGE`.** 26 réussites STRICT là où le hasard en produirait ~51 ; 25 des 26 viennent du seul XAUUSD (1 STRICT pour ~45 attendues sur les 7 autres instruments). Signal de cassure à +0,013 R/trade à spread réel, +0,064 à spread nul (7 instruments comparables) : espérance nulle, pas négative — les coûts ne sont pas le mécanisme. L'essentiel de la performance vient du côté long sur des marchés haussiers (3/16 cas seulement avec les deux côtés positifs).
- **Filtre de régime `combo_011_050` : `SUR-AJUSTEMENT CONFIRMÉ` — réfuté.** Voisinage 3×3 hors échantillon : 0/9 meilleur que le témoin ; 0/9 aussi en plein échantillon hors trades fantômes. Son gain apparent (+0,0233 R/trade brut) provenait intégralement de 15 trades sur 3162 issus d'un défaut du moteur (stop dans un gap jamais rempli — dont un trade DAX à −210,6 R). Ne pas réutiliser sans nouvelle validation.
- **Résidu XAUUSD : `NON CONCLUSIF` — la poche la plus sérieuse du dépôt.** Cellule `adx_min 20 / donchian 40 / er_min 0,00 / fr_max 1,00 / tp_m 4,0` (filtre désactivé) : **+0,226 R/trade sur 400 trades** plein échantillon, win rate 34,2 %, profit factor 1,34, deux côtés positifs (LONG +0,318 / SHORT +0,100), voisinage **9/9**, 0 trade fantôme, +0,113 R/trade même hors 2025 (année qui fait 62 % du total). Réserves : 1 instrument sur 8 sélectionné après coup parmi 1024 cellules, et S01 avait déjà laissé XAUUSD comme unique résidu (propriété possible de l'or 2021-2026, pas des règles).
- **Forward scellé armé** (`studies/gold_forward/`, scellé le 2026-08-16, décision Adrian) : cellule XAUUSD figée, hash SHA-256 sur `params.json`, journal append-only chaîné dans `C:\db\tbot\gold_forward\`. Critères d'arrêt chiffrés d'avance : échec si percentile témoin < 20 dès 40 trades ; succès (discussion de promotion seulement) si percentile ≥ 95 dès 100 trades ; NON CONCLUSIF si < 40 trades après 12 mois. **État au 2026-08-25 (`status.json`) : 3 trades clos, R cumulé +0,64, aucun critère atteint.** Toute modification du dispositif invalide le test (PROTOCOL § 3d).
- **Composant non reproduit** : trailing / passage au point mort (option non-défaut de l'historique) — le moteur commun ne déplace pas de stop et R9 interdit d'écrire un autre moteur.
- Pistes laissées ouvertes par le VERDICT : walk-forward **glissant** non exécuté (complément naturel pour instruire le résidu or), autres formalisations de la cassure et du régime (une seule testée), R1 « côté exécution » manquant à la plateforme.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC, documenté).
- **Ne pas toucher au forward scellé** `studies/gold_forward/` : il court, ses critères décident. Le suivre en lecture seule et intégrer son issue au raisonnement.
- Un verdict négatif hérité n'est pas un arrêt de mort : re-évaluer, explorer les pistes ci-dessus (WF glissant, résidu or, variantes de formalisation) avant tout constat de non-pérennité.

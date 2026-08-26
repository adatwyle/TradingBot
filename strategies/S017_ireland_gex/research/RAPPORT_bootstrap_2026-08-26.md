# RAPPORT bootstrap S017 ireland_gex — 2026-08-26

Session de fondation cc-S017. Statut : **RESEARCH** (inchangé).

## 1. Fait

| Livrable | Chemin | État |
|---|---|---|
| Spécification stratégie | `spec-strategie.md` | 5 conditions formalisées en règles testables (définitions opérationnelles §3.1-3.7), 5 hypothèses falsifiables déclarées d'avance (H1-H5), protocole de mesure en 3 phases |
| Manifest | `manifest.yaml` | RESEARCH, magic 130017, SPY 5min+daily, 18 paramètres avec défauts figés + plages de variantes |
| Calcul GEX maison | `research/gex_calc.py` | Méthodo Perfiliev depuis chaîne CBOE delayed (gratuit, sans compte/clé) — fetch, carte par strike, niveaux majeurs, régime net, flip |
| Pipeline collecte quotidienne | `research/daily_snapshot.py` | Chaîne brute + carte GEX + OHLCV → `C:\db\tradingBot\S017\` (README inclus). **Exécuté et validé ce jour** |
| Étude 01 (H3) | `research/study_01_volume_breakouts.py` + `results_study01_2026-08-26.md` | 134 cassures de compression sur 60 j de SPY 5min |
| Étude 02 (H1 plomberie) | `research/study_02_gex_day0.py` + `results_study02_2026-08-26.md` | Niveaux du jour vs intraday du jour, avec groupes placebo — ré-exécutable chaque jour accumulé |
| Évaluation backtester commun (R9) | ticket `TCK-003` | Lecture seule du socle : moteur OK, 5 manques identifiés, proposition d'extension localisée |
| Tickets | `tickets/TCK-003_socle-spy-intraday-gex.md`, `tickets/TCK-004_historique-gex-backtest.md` | Ouverts, non bloquants |

## 2. Fonctionne (validé ce jour)

- **Chaîne CBOE delayed** : 13 288 options SPY avec greeks (gamma fourni), OI, IV — gratuit, sans compte.
- **Carte GEX du jour** : 491 strikes ; net **−5 263 M$/1% → régime négatif** ; niveaux majeurs **760 (−2 219 M) et 765 (−2 254 M)**, spot 766.23. Structure visuellement cohérente avec la logique des frames ITMatrix (concentrations sur strikes ronds, puts dominants sous le spot, calls au-dessus) — les unités diffèrent (nous : $-gamma OI toutes expirations ; ITMatrix : par expiration + volume cumulé), la géométrie des niveaux correspond.
- **Snapshot pré-market authentique** : fetch 15:18 CH = 9:18 ET, 12 min avant l'open — le timing opérationnel de la vidéo est reproductible depuis la Suisse.
- **OHLCV** : 5min ~60 j (limite yfinance) + daily 10 ans, fusion incrémentale (l'accumulation dépasse la fenêtre de 60 j au fil des jours).
- **Anecdote jour 0** (n=1, aucune conclusion) : seul le majeur 765 a été touché (à l'open, par en dessous) → cassé avec momentum (pénétration 1.75 ATR vs rejet 0.17) — compatible avec la thèse gamma-négatif « mouvements amplifiés », mais c'est une observation, pas une mesure.

## 3. Résultats de mesure honnêtes

**Étude 01 (H3, 60 jours, 134 cassures)** — direction cohérente, pas significative :
- +1R avant stop : 39 % avec volume ≥1.5× (n=18) vs 32 % sans (n=116).
- Tranche 1.5-2.0× : 57 % et MFE médiane 1.01R (n=7) ; tranche >2.0× : effondrement à 27 % (n=11) → piste d'un **plafond de volume** (les spikes extrêmes = épuisement/news, pas confirmation).
- Filtré EMA-alignés + volume ≥1.5× : 4 cas, 0 stoppé — anecdotique.
- **Verdict : n insuffisant partout. Le filtre volume va dans le sens de H3 mais rien n'est établi.**

**Mesurable maintenant vs exige de l'historique GEX** :

| Mesurable dès maintenant | Exige historique GEX |
|---|---|
| H3 (volume) — sur OHLCV seul, n grandit avec l'accumulation | H1 en vrai (event study ≥100 contacts ≈ ≥20-30 jours de cartes) |
| Fréquence d'alignement EMA (fait : 47 % bull / 53 % chop daily sur 60 j) | H2 (régime vs volatilité réalisée, ≥60 jours de régimes) |
| Étude 02 jour par jour (n += 1/jour de collecte) | H5 (pinning, ≥60 jours) |
| | H4 (backtest complet — exige aussi TCK-003) |

## 4. Lacunes identifiées

1. **Historique GEX inexistant en gratuit** — l'actif de recherche se construit par accumulation quotidienne (chaque jour non snapshotté est perdu). → TCK-004 (préco : accumuler 4-6 semaines, ne payer qu'avec preuve de signal).
2. **Backtester commun inutilisable tel quel pour SPY intraday + exogène** — moteur OK, données/contrat/sessions manquants. → TCK-003 (extension cc-app, non bloquant en Phase A).
3. **Méthodologie GEX = approximation** : hypothèse dealers naïve ; notre carte ≠ carte ITMatrix exacte (unités, expirations, volume vs OI). Divergence possible avec les niveaux que Nick Ireland lit réellement.
4. **Pas d'exécution automatique de la collecte** : `daily_snapshot.py` doit tourner chaque jour de bourse avant 15:30 CH — actuellement manuel (proposition §6).
5. **Magic 130017 non inscrit** au `MAGIC_REGISTRY.md` (R4) — inclus dans TCK-003 (fichier sous `app/`, hors périmètre cc-S017).
6. **Bearish inexistant dans l'échantillon** : 0 % de jours daily-bear sur les 60 derniers jours — le côté short du système est non mesurable sur cette fenêtre.

## 5. Variantes à tester (priorisées, pour rendre la stratégie profitable)

1. **Seuils volume** (`vol_mult` 1.2-2.5 **+ plafond** ~2.0-3.0×) — première piste concrète issue de l'étude 01 ; testable dès maintenant, n grandit chaque jour.
2. **Définition du niveau majeur** (`level_major_frac` 0.3-0.7, `level_top_k` 3-8, `gex_expiry_window` all/7j/0DTE) — la carte de la vidéo pondère les expirations proches ; notre défaut « toutes expirations » est peut-être trop lissé.
3. **Distance au niveau** (`near_level_pct` 0.05-0.30 %) — trop serré = pas de trades, trop large = « no man's land » réintroduit.
4. **Régime gamma** (`regime_mode` net/flip/local) — la vidéo qualifie chaque niveau individuellement (750 nég / 755 pos) : le mode `local` est le plus fidèle, `net` le plus simple ; à départager sur données.
5. **Définition de compression** (`compress_bars` 4-12, `compress_range_atr` 1.0-2.5) + volume décroissant dans le flag (non exigé en V1).
6. **Gestion différenciée gamma−** (taille ×0.5-0.7, partiel 1R 30-70 %) — mesurable seulement en Phase B.
7. **Horaires** (`entry_cutoff_min` 0/15/30 + éventuelle exclusion dernière heure).
8. **Proxy sous-jacent vs options** : V1 spot ; couche options (strike/DTE/IV) seulement si H4 validée.
9. **Idées propres différées** (après lacunes mesurées, conformément au mandat) : pinning EOD comme stratégie séparée (H5) ; flip résistance→support comme second type d'entrée (la vidéo le mentionne, non formalisé en V1).

## 6. Questions ouvertes (chacune avec préconisation)

| Question | Préconisation cc-S017 |
|---|---|
| Achat historique GEX (FlashAlpha free/payant vs ITMatrix 119.99 $/mois) ? | **TCK-004** : accumuler gratuit 4-6 semaines ; ne poser la question d'achat qu'avec preuve de signal Phase A ; si achat, ITMatrix 1-2 mois one-shot (≈120-240 $) pour comparabilité maximale avec la source |
| Extension socle SPY+GEX (R9) ? | **TCK-003** : ordre proposé equities→gex.py→MarketContext→sessions ; non bloquant tant que Phase A |
| Automatiser la collecte quotidienne ? | **Proposition** : tâche planifiée Windows, jours ouvrés 14:55 CH, `python research/daily_snapshot.py` (+ relance `--intraday` optionnelle à 22:05 CH pour la carte de clôture). Non créée — décision Adrian/cc-support (infra hôte partagée) |
| Le côté short est-il dans le périmètre V1 ? | Garder short dans la spec (symétrique), mais accepter qu'il soit non mesurable tant que le marché ne fournit pas de régime bearish — pas de décision requise |

## 7. Prochaine session cc-S017 (préconisation)

1. Vérifier l'accumulation des snapshots (idéalement automatisée d'ici là) ; ré-exécuter étude 02 sur les jours accumulés dès n_days ≥ 5 pour roder l'agrégation multi-jours.
2. Renforcer l'étude 01 : ajouter le plafond de volume comme variante mesurée, et l'interaction alignement×volume à mesure que n grandit.
3. Écrire `strategy.py` (squelette `StrategyModule` conforme au contrat du socle : `precompute()` avec jointure GEX en colonnes + resample daily causal, `generate_signals()`/`on_bar()` symétriques) — prêt à brancher dès TCK-003 livré, testable à vide avant.
4. Suivre TCK-003/TCK-004.

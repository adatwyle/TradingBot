# input-adrian — S007 Canal gaussien (Ionita) — allocation crypto

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S007 · magic `130007`
- **Source** : YouTube — Michael Ionita (« Gaussian Channel Trend Radar »), https://www.youtube.com/watch?v=fdGCGXcDByk
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s07_ionita_gaussian\` (lecture seule)

## Principe (résumé)
Canal gaussien (période 144, 4 pôles, multiplicateur 1,414, source hlc3) déterminant le régime de marché en D1. Répartition d'un capital entre BTCUSD et ETHUSD, pondérée par la fraîcheur du breakout (substitut Donchian 55 pour la date de cassure propriétaire, âge max 25 jours), avec jambe short optionnelle (désactivée par défaut). **Contrat `allocation`** (`AllocationModule`), pas `StrategyModule` : la stratégie répartit du capital, elle n'émet ni entrée, ni stop, ni cible — les outils de validation standard (`core.validation.causality`, `anchored_wf`) ne s'appliquent pas tels quels (R1 via `validate_r1` dédié, walk-forward via `run_backtest.py` sur le moteur commun `run_allocation`).

## État hérité du prototype
- **Statut manifest** : `RESEARCH`. Note explicite du prototype : « NE PAS PROMOUVOIR en PAPER en l'état ».
- **Verdict** : PAS D'EDGE au sens du critère n°1. Sur 2018-2026 (BTCUSD + ETHUSD), la stratégie rend **786 %** contre **1 141 %** pour l'équipondéré naïf des deux mêmes lignes, avec un Sharpe inférieur. Attention : le verdict est consigné dans les notes du `manifest.yaml` — le fichier `research/VERDICT.md` référencé n'existe pas dans le prototype, et `research/ANALYSIS.md` est un squelette non rédigé.
- **Résultat robuste et transférable** : protection bear-market réelle et mesurée — fenêtres OOS 3 et 4 : **+22,7 %** et **−17,3 %** contre **−3,6 %** et **−39,2 %** pour BTC. Sous-performance en marché haussier : profil de suiveur de tendance conforme à ce qu'annonce l'auteur, mais insuffisant pour battre la détention passive sur le cycle complet.
- **Jambe SHORT** : dégrade tout, alors même qu'elle est simulée sans coût de bord. L'auteur classe lui-même sa version long+short derrière sa version long seul.
- **Bug core signalé, non corrigé** : `allocation_engine` décale l'exécution d'une barre et crédite un mouvement antérieur à la décision (démonstration : `backtests/bug_allocation_engine.txt`). Contourné dans `strategy.py` par un décalage d'horodatage — à retirer quand core sera corrigé, sinon double décalage. Sans ce contournement, la stratégie affichait 107 278 % au lieu de 786 %.
- **Réserves sur la portée du verdict** (notes manifest) : (1) le « Trend Radar » de Signum n'est pas reproductible — univers fixe, effet de sélection neutralisé mais pas mesuré ; le verdict porte sur le canal gaussien seul, pas sur le produit de l'auteur. (2) Univers de 2 lignes chez le broker contre ~50 chez l'auteur.
- **Falsifications déclarées d'avance** (`research/FALSIFICATION.md`, figé 2026-08-16) : F1 ne bat pas la détention des mêmes actifs, F2 effondrement hors échantillon, F3 pic de grille isolé, F4 coûts (dont portage CFD crypto ≈ 14 %/an sur les longs), F5 pari directionnel déguisé. Point de comparaison retenu : forward-test publié par l'auteur (51,74 % de profit, 8,57 % de DD max, 44,44 % de trades gagnants, BTC, 15.10.2024 → début 09.2025) — que l'auteur lui-même mesure sous le buy & hold de la période (« about 68% »).

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC dédié, documenté).
- Le verdict négatif hérité est une donnée d'entrée, pas un arrêt de mort : la protection bear-market mesurée est un actif réel à exploiter (p. ex. en composant régime/allocation), la jambe long-only reste le périmètre pertinent.
- Suivre le sort du bug `allocation_engine` côté plateforme avant tout nouveau backtest : le contournement local doit être retiré dès correction core, sinon double décalage.

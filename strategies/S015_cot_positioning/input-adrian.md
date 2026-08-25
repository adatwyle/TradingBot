# input-adrian — S015 COT Positioning (CFTC)

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S015 · magic `130015`
- **Source** : Pilier positionnement — rapports COT de la CFTC (littérature de référence : Klitgaard & Weir, FRBNY *Economic Policy Review*, mai 2004)
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s15_cot_positioning\` (lecture seule)
- Note numérotation : le prototype saute volontairement le numéro 14 (déjà porté par l'étude scellée `studies/s14_sentiment`) ; `130014` reste non attribué.

## Principe (résumé)
Lecture contrarienne du positionnement des non-commerciaux : percentile glissant de `pct_noncomm` (position nette / open interest, rapport Legacy) sur 260 semaines ; état bas (percentile ≤ q = 0,20) → long, état haut → short. Deux familles déclarées : A « niveau » (extrême de positionnement, hypothèse porteuse H15) et B « impulsion » (variation hebdomadaire, test direct de la littérature), plus une famille C « suiveur » comme témoin inverse sans cellule propre. Sorties simples uniquement : `hold5` (5 barres D1, stop 3 ATR) ou `atr_2_2` (cible/stop 2 ATR, RR 1:1). Périmètre : XAUUSD et EURUSD (contrats CFTC directs uniquement — synthétiques exclus), D1 imposé par la donnée hebdomadaire.

## État hérité du prototype
- **Statut manifest** : `RESEARCH` (v0.1.0, créé 2026-08-19). **Protocole gelé le 2026-08-19, AUCUN backtest exécuté, pas de `strategy.py`** — le dossier ne contient que `manifest.yaml`, `CLAUDE.md`, `research/ANALYSIS.md` et `research/FALSIFICATION.md` (pas de VERDICT.md).
- **Attente a priori déclarée** (gelée avant toute mesure) : **edge faible ou nul**. Klitgaard & Weir (FRBNY 2004) mesurent une corrélation synchrone forte (30-45 % de la variance hebdomadaire expliquée, ~75 % de réussite directionnelle sur la semaine en cours) mais **aucun pouvoir prédictif** sur la semaine suivante. Conséquence figée : un résultat positif se traite avec suspicion (première hypothèse : défaut d'alignement des dates).
- **Protocole gelé** : grille de 128 cellules (64 par instrument, 32 jeux de dates d'entrée) ; hold-out scellé de 5 ans (toute barre D1 ≥ 2021-08-16, ≈ 261 semaines), ouvert une seule fois sur ≤ 3 candidates ; exploration ≈ 782 semaines (≈ 2006-08 → 2021-08-13) ; contrôle de fuite F0 en gate absolu (3 versions de chaque mesure : honnête via `cot.connu_au()` avec entrée au close du lundi, fuitée-3j, fuitée-contemporaine ; seuil différentiel +0,10 R) ; effectif minimal **≥ 12 épisodes indépendants** (seuil dérivé, non choisi — FALSIFICATION.md §6), estimation a priori ≈ 35-45 épisodes en exploration au seuil primaire.
- **Refus en review** (résumé cc-support, non tracé dans le dossier prototype) : le protocole a été **REFUSÉ EN REVIEW** — la famille porteuse ne réunirait que 2-9 épisodes de hold-out contre le plancher dérivé de 12. **RECADRAGE EN ATTENTE D'ADRIAN** : 3 options posées, aucune tranchée à ce jour.
- **Infrastructure prête** : collecteur `core/data/cot.py` anti-fuite (lecture seule pour ce dossier, `connu_au()` obligatoire, gestion du gel de publication 2025), données COT Legacy depuis 1986 (21 tests selon le résumé cc-support) ; prix D1 limitants (~20 ans, 2006-08 → 2026-08).
- **Angles morts documentés d'avance** : données CFTC révisées (angle mort non attrapable rétrospectivement — seul un forward scellé le ferme), deux instruments partageant la jambe dollar (aucune réplication indépendante possible), futures ≠ spot (proxy assumé), reclassification des catégories de traders.

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC dédié, documenté).
- Spécifique S015 : le blocage n'est pas un verdict de backtest mais un **refus de protocole** (effectif hold-out insuffisant). Premier travail : instruire le recadrage — reconstituer/retrouver les 3 options posées, évaluer si un protocole à effectif suffisant est constructible (le seul levier identifié dans le prototype étant le temps qui passe, l'historique de prix D1 étant plafonné), et proposer une recommandation documentée. Aucun backtest tant que le protocole n'est pas recadré et regelé.

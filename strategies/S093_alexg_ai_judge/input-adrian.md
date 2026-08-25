# input-adrian — S093 AlexG AI Judge

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Identité
- **Numéro** : S093 · magic `130093`
- **Source** : YouTube — fxalexg (https://www.youtube.com/@fxalexg__), spec publique 2025
- **Dossier prototype** : `C:\Datas\Projects\TradingBot_9.0.0.x\strategies\s93_alexg_ai_judge\` (lecture seule)

## Principe (résumé)
Deux couches. Couche 1 : détecteur mécanique de zones AOI (largeur ≤ 60 pips, ≥ 3 touches, lookback 3 ans/1095 jours, R:R ≥ 2, filtre EMA 50), réglé pour le rappel, H1, 6 paires au prototype (EURUSD, USDJPY, USDCHF, AUDCAD, GBPUSD, EURJPY). Couche 2 : juge IA appliquant la grille de notation d'Alex (1 confluence = 10 %) en rejeu à l'aveugle — dossiers anonymisés (prix en unités d'ATR, pas de ticker ni de date, heures → sessions). Confluence COT (non-commercials CFTC, percentile glissant 3 ans) avec décalage de publication strict (mardi → vendredi 15h30 ET).

## État hérité du prototype
Donnée d'entrée, pas un arrêt de mort.

- **Statut manifest** : `RESEARCH` (v0.2.0, créé 2026-08-16).
- **Verdict du rejeu à l'aveugle (2026-08-16)** : falsification centrale F0/F5 CONFIRMÉE (échec). 191 candidats jugés ; le paquet complet fait −0,154 R/trade (WR 25,7 %) — le détecteur seul n'a pas d'edge, cohérent avec S001. Seule cellule à effectif suffisant (n ≥ 30) : juge avec COT, seuil 50 % → n=39, +0,222 R/trade, WR 38,5 %, **percentile 88,5** contre le témoin aléatoire (200 permutations), sous le seuil de 95 déclaré d'avance.
- **F3 falsifiée** : monter le seuil de grade DÉGRADE le R/trade (+0,222 → −0,385 → −0,488 aux seuils 50/60/70 %) — signature d'un rituel, pas d'un instrument de mesure. **F2 falsifiée** : WR 38,5 % hors de la fourchette [55 ; 75] % attendue de la source. **F6 (apport COT) NON CONCLUSIF** (effectifs sans-COT n=11 et n=4, sous 30). Recommandation du prototype : NO-GO paper.
- **MAIS l'univers testé était faux** : GBPJPY/GBPCHF déclarés « indisponibles » manquaient au catalogue interne (`core/data/instruments.py`), pas chez le broker (vérification MT5 du 2026-08-22 : les 26 paires de l'univers documenté de la source sont disponibles chez Swissquote ; 13 paires ajoutées au catalogue).
- **Re-mesure en cours** : essai forward prospectif `studies/alexg_paper` (protocole scellé le 2026-08-22), 26 paires H1, 4 bras MECH/AI/RND/SHADOW ; le juge y DÉCIDE (prendre/passer + taille) au lieu de compter des cases. Base mécanique re-mesurée sur l'univers réel : 777 candidats en 5,1 ans (2,94/semaine), −0,2085 R/trade. Verdict à N = 40 décisions IA, soit ~3,2 mois au rythme mesuré (F1 : percentile ≥ 95 requis pour conclure à un apport, < 80 = échec, 80-95 = suggestif non concluant).

## Attentes d'Adrian
- Reprise sans préavis (décision 2026-08-23) : évaluer, tenter des chemins d'amélioration.
- Faire avancer vers la validation paper — ou constater la non-pérennité et archiver (constat propre du CC dédié, documenté).
- Suivre l'essai `studies/alexg_paper` du prototype (lecture seule, scellé — ne jamais le perturber) : ses résultats sont la première donnée neuve pour ré-évaluer le verdict sur l'univers réel.
- Pistes explicitement laissées ouvertes par le prototype : élargissement de l'échantillon avec re-déclaration des falsifications (seule raison donnée de ne pas fermer le dossier — percentile 88,5, n=39) ; étude dédiée d'un filtre COT mécanique SANS juge (écarté du forward V1 par doctrine, branche V2).

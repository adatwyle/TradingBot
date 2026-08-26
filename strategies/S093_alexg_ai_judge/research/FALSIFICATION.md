# FALSIFICATION — s93_alexg_ai_judge

> **Écrit AVANT le premier jugement IA et AVANT toute mesure.**
> Date : 2026-08-16. Aucun candidat n'a encore été jugé, aucun PnL de sélection
> n'a encore été calculé au moment où ce fichier est commité.

## Objet testé

Deux couches, deux questions distinctes :

1. **Détecteur mécanique v2** (spec publique fxalexg 2025, `docs/sources/fxalexg/SYNTHESE.md` §1)
   — produit-il des candidats au profil compatible avec le trader ?
2. **Juge IA** (grille de notation d'Alex : ~10 confluences, 1 = 10 %) — la
   couche de SÉLECTION ajoute-t-elle une espérance mesurable, en rejeu à
   l'aveugle (dossiers anonymisés, sans ticker ni date) ?

## Falsification CENTRALE (déclarée d'avance)

> **F0 — « Le juge IA ne bat pas la sélection aléatoire de même taux. »**
>
> Pour chaque seuil de score (50 / 60 / 70 %), le PnL **par trade** (R/trade,
> coûts réels : spread catalogue + slippage 0,5 pip) des candidats PRIS par le
> juge est comparé à la distribution de 200 tirages aléatoires de MÊME
> EFFECTIF parmi les MÊMES candidats (graine fixée : 20260816).
>
> **Seuil de significativité, choisi d'avance : percentile ≥ 95** de la
> distribution nulle, sur AU MOINS un seuil de score, avec un effectif de
> candidats pris ≥ 30. En dessous : le juge est indistinguable du hasard —
> la couche de sélection est du rituel, quel que soit le récit qualitatif
> de ses « raisons ».

Aucun re-tirage, aucun changement de graine, aucun changement de seuil après
lecture des résultats. Si le percentile est 94, c'est un échec.

## Falsifications secondaires (reprises de SYNTHESE §3, chiffrées)

| # | Énoncé falsifiable | Seuil |
|---|---|---|
| F1 | La formalisation est trop permissive | fréquence des candidats pris (au seuil retenu) > 2/semaine en moyenne par l'ensemble du book → on n'a PAS reproduit sa sélectivité (lui : 1-2/sem MAX, ratio pris/identifiés ~26 %) |
| F2 | Autre stratégie que la sienne | win rate des candidats pris hors de [55 %, 75 %] (si effectif ≥ 30) |
| F3 | Le grading est du rituel | monter le seuil (50→60→70 %) n'améliore PAS le PnL **par trade** de façon monotone ou quasi-monotone |
| F4 | Profil R:R incompatible | R:R réalisé médian des pris < 1,5 |
| F5 | Indistinguable du hasard | = F0 (percentile < 95 vs sélection aléatoire de même taux) |
| F6 | **Confluence positionnement (COT)** | le grading AVEC les deux champs COT ne bat pas le grading SANS COT en PnL par trade des pris (contribution marginale ≤ 0) — mesuré sur les mêmes candidats, mêmes seuils |

## Règles de mesure (verrouillées d'avance)

- **Jamais le PnL total** pour juger un filtre : uniquement le R **par trade**
  (retirer des trades baisse le total mécaniquement).
- Chaque candidat est valorisé par le moteur commun (`core/backtest/engine.py`),
  R9 — aucune boucle maison. Coûts : spread du catalogue + slippage 0,5 pip,
  dès le premier run.
- Chaque chiffre est accompagné de son **effectif**. Pas d'effectif ≥ 30 pour
  un sous-groupe → « NON CONCLUSIF » pour ce sous-groupe, pas de verdict.
- Le bras témoin est une **permutation** : les R par candidat sont figés une
  fois pour toutes (évaluation indépendante par candidat), le tirage ne
  choisit que le sous-ensemble. 200 tirages, graine 20260816.
- Rappel du placebo géométrique s05 : la géométrie seule (mêmes stops/cibles,
  entrées aléatoires) vaut −0,08 R/trade. La moyenne de TOUS les candidats est
  affichée systématiquement à côté de celle des pris : c'est l'équivalent du
  bras témoin géométrique.
- **Anonymisation** : le juge ne voit jamais ticker, dates, prix bruts ni
  heures d'horloge (prix normalisés ATR, heures → session, COT → percentile
  « sur 3 ans »). La table de correspondance vit dans un fichier séparé jamais
  transmis au juge. Toute information non anonymisable proprement est retirée.
- **COT anti-fuite** : la donnée du mardi n'est utilisable qu'à partir du
  vendredi 15h30 ET (≈ 22h30 heure serveur). Tout usage antérieur à la
  publication = fuite, invalide le run.

## Ce qu'un échec signifie

- F0/F5 échoue → la valeur ajoutée supposée du « jugement » discrétionnaire
  d'Alex, rejouée par un LLM sur sa propre grille publique, n'existe pas dans
  nos données. Recommandation attendue : NO-GO paper.
- F0 passe mais F1 échoue → sélectivité non reproduite : le dispositif reste
  différent du trader, verdict au mieux partiel.
- F6 échoue → la confluence de positionnement n'apporte rien : elle sort du
  design live.

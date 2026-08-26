# VERDICT — s93_alexg_ai_judge

> Rendu APRÈS le rejeu à l'aveugle, contre les falsifications déclarées
> d'avance dans `FALSIFICATION.md` (commit antérieur au premier jugement).
> Date : 2026-08-16. Chiffres : `judge_results.txt` / `judge/results.json`.

## Dispositif exécuté

- **Détecteur v2** (spec publique fxalexg 2025) : 6 paires H1 (EURUSD, USDJPY,
  USDCHF, AUDCAD, GBPUSD, EURJPY — GBPJPY/GBPCHF indisponibles, substitution
  documentée), 2021-07 → 2026-08, spread catalogue + slippage 0,5 pip,
  moteur commun R9. R1 passé (couche indicateur incluse), R5 passé.
- **191 candidats** (0,72/semaine sur le book — du même ordre que le rythme
  d'identification documenté du trader une fois la porte R:R≥2 appliquée).
- **Rejeu à l'aveugle** : dossiers anonymisés (prix en ATR, pas de ticker,
  pas de date, heures → sessions, ordre mélangé graine 20260816), 8 sous-agents
  juges appliquant la grille d'Alex (10 confluences core ×10 % + 2 COT),
  191/191 jugés, journaux complets dans `judge/logs/`.
- **Mesure** : R par candidat évalué indépendamment par le moteur commun ;
  bras témoin = 200 permutations de même effectif, graine 20260816.

## Les chiffres

TOUS les candidats : n=191, **−0,154 R/trade**, WR 25,7 % (le paquet perd —
cohérent avec le verdict s01 : le détecteur seul n'a pas d'edge).

| Variante | Seuil | n pris | R/trade | WR % | freq/sem | percentile vs nul |
|---|---|---|---|---|---|---|
| sans COT | 50 % | 11 | −0,219 | 27,3 | 0,04 | 49,0 [MINCE] |
| sans COT | 60 % | 4 | +0,429 | 50,0 | 0,02 | 77,5 [MINCE] |
| sans COT | 70 % | 0 | — | — | — | — |
| avec COT | 50 % | **39** | **+0,222** | 38,5 | 0,15 | **88,5** |
| avec COT | 60 % | 17 | −0,385 | 23,5 | 0,06 | 35,0 [MINCE] |
| avec COT | 70 % | 5 | −0,488 | 20,0 | 0,02 | 34,5 [MINCE] |

Seule cellule à effectif suffisant (n ≥ 30) : **avec COT, seuil 50 %**.

## Verdict des falsifications

| # | Énoncé | Seuil | Résultat | Verdict |
|---|---|---|---|---|
| **F0/F5** | Le juge ne bat pas l'aléatoire de même taux | percentile ≥ 95, n ≥ 30 | percentile **88,5** (n=39), seule cellule valide | **ÉCHEC — falsification centrale CONFIRMÉE** |
| F1 | Fréquence > 2/sem | — | 0,15/sem | non falsifié (sélectivité respectée, même trop basse) |
| F2 | WR hors [55 ; 75] % | n ≥ 30 | WR 38,5 % (n=39) | **falsifié — autre profil que le sien** |
| F3 | Seuil ↑ n'améliore pas le R/trade | monotonie | +0,222 → −0,385 → −0,488 : DÉCROISSANT | **falsifié — le grading fin est du rituel** |
| F4 | R:R médian < 1,5 | — | 2,57 | non falsifié |
| F6 | COT n'apporte rien | delta ≤ 0 | +0,441 (50 %) mais −0,814 (60 %) ; bras sans-COT n=11 et 4 | **NON CONCLUSIF** (effectifs sous 30) |

La règle était écrite d'avance : « Si le percentile est 94, c'est un échec. »
Il est à 88,5.

## Lecture honnête

1. **Le signal suggestif existe mais n'atteint pas le seuil.** La seule cellule
   correctement peuplée (juge avec COT, seuil 50 %) fait +0,222 R/trade là où
   le paquet fait −0,154 et le nul médian −0,162 — percentile 88,5. C'est
   mieux que le hasard 7 fois sur 8, pas 19 fois sur 20. Sur 39 trades, un
   écart pareil s'obtient par chance ~1 fois sur 9. On ne construit pas un
   compte réel là-dessus.
2. **La montée en exigence détruit au lieu d'améliorer** (F3) : les candidats
   notés 60-70 % font PIRE que ceux notés 50 %. Si la grille mesurait une
   qualité réelle, l'effet serait inverse. C'est la signature d'un rituel, pas
   d'un instrument — exactement la falsification n°3 de la SYNTHESE.
3. **Le win rate ne ressemble pas au sien** (38,5 % vs 60-65 % revendiqués).
   Soit sa sélection réelle utilise le « signal secret » jamais publié, soit
   son win rate revendiqué n'est pas celui de sa grille publique. Les deux
   hypothèses restent ouvertes ; aucune n'est en notre faveur.
4. **Le COT est la seule piste qui a bougé le résultat** (délta +0,44 au seuil
   50 %) mais l'effet s'inverse au seuil 60 % et les effectifs interdisent de
   conclure (F6 NON CONCLUSIF). Piste éventuelle pour une étude dédiée
   (filtre COT mécanique SANS juge), pas pour une mise en production.
5. **Limites** : un seul régime macro (2021-2026), 191 candidats, juge = LLM
   sur la grille publique (sans sa pondération ni son signal d'entrée secret),
   GBPJPY/GBPCHF substitués, H1 seul TF d'entrée.

## Recommandation : **NO-GO pour le paper**

La falsification centrale, déclarée d'avance avec son seuil, est confirmée :
le juge IA appliquant la grille publique d'Alex n'ajoute pas d'espérance
mesurable au seuil de signification choisi, et la structure interne du grading
(F3) contredit l'hypothèse qu'il mesure une qualité réelle. Le mandat « set
and forget à bas risque » n'est pas atteignable avec ce dispositif.

Si Adrian veut poursuivre malgré tout, la seule suite défendable n'est PAS le
paper mais l'élargissement de l'échantillon (paires supplémentaires, données
plus profondes) avec re-déclaration des falsifications — le percentile 88,5 de
la cellule n=39 est la seule raison de ne pas fermer complètement le dossier.
La famille « structure + zones » reste, elle, refermée (s01 + s93 concordants).

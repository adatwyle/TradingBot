# S019 — ce que la mesure a rendu

**Date** : 2026-09-06 · **Dépôt** : `3cef92e` · **Données** : XAUUSD M15,
119 992 barres, 2021-08-09 → 2026-09-04 · **Spread** : 52 pips (réel, TCK-018).
Critères fixés d'avance : `FALSIFICATION.md`.

---

## Verdict

**Échec. Les 16 cellules sont négatives, aucune ne passe STRICT, aucune ne bat le
bras témoin.** Et la forme de l'échec est plus instructive que l'échec lui-même :
**le déclencheur n'est pas mauvais, il est vide.** Toute la perte est le coût de
bord.

| Seuil de réussite (posé d'avance) | Exigé | Obtenu |
|---|---|---|
| Cellules STRICT hors échantillon | ≥ 3 | **0 / 16** |
| Percentile contre le témoin aléatoire | ≥ 90 | **42,5** au mieux |
| R/trade à spread réel | > 0 | **−0,096 au mieux**, −0,180 au défaut |
| Coût de bord | < 35 % du R | **14,3 %** — seul critère respecté |

Le coût, que je redoutais, n'est pas le coupable : le stop structurel donne un
risque médian de 363 pips, pas les 34 à 218 que les balayages de la source
laissaient craindre. Sur ce point le dispositif était bien conçu. Il n'a
simplement rien trouvé à protéger.

---

## L'arithmétique qui tranche

Pour une cible à `tp_r`, le taux de réussite d'équilibre géométrique vaut
`1/(1+tp_r)`, soit 33,33 % à 2 R et 20,00 % à 4 R. Voici l'écart observé, et le
**résidu** — ce que le signal rapporte une fois les frais neutralisés :

| cellule | n | réussite | équilibre | écart | résidu | t |
|---|---:|---:|---:|---:|---:|---:|
| stop0.5 tp2 — — | 2955 | 33,4 % | 33,33 % | +0,07 | −0,036 | −1,39 |
| stop0.5 tp4 — — | 2094 | 21,0 % | 20,00 % | +1,00 | **−0,001** | −0,01 |
| stop0.5 tp4 BIAS SESS | 658 | 21,0 % | 20,00 % | +1,00 | +0,007 | +0,09 |
| stop1.0 tp4 BIAS SESS | 644 | 20,3 % | 20,00 % | +0,30 | −0,004 | −0,05 |
| stop1.0 tp2 — SESS | 1525 | 31,5 % | 33,33 % | −1,83 | −0,075 | −2,11 |

Sur les 16 cellules, **15 ont un |t| < 2**, et la seule qui sorte est du mauvais
côté. Autrement dit : sur 2 955 trades et cinq ans, **une entrée déclenchée par
un balayage suivi d'une réintégration est statistiquement indiscernable d'une
entrée au hasard.** Le taux de réussite colle au seuil d'équilibre à un point de
pourcentage près dans chaque cellule. Ce n'est pas un signal faible, c'est
l'absence de signal.

Le bras témoin le confirme sans détour : percentile 42,5 pour la meilleure
cellule — au milieu du hasard — et 6,5 pour la cellule par défaut, c'est-à-dire
**pire que 93 % des entrées aléatoires** à dispositif de risque identique.

---

## Pourquoi la mesure du 2026-09-06 ne s'est pas transportée

Le croisement de ses entrées avait donné 60 % de balayages contre 39 % au hasard,
p = 0,047. Ce chiffre n'est pas démenti. Ce qui est démenti, c'est **ma lecture**
de ce chiffre.

J'ai codé une **condition nécessaire comme si elle était suffisante**. Que
60 % de ses entrées suivent un balayage établit que le balayage fait partie de sa
grille de lecture. Cela n'établit pas qu'un balayage quelconque soit une entrée.

Reste la question du tri, et c'est là que la mesure surprend :

| | fréquence |
|---|---|
| Balayages offerts par la règle | ≈ 4,2 / jour |
| Trades effectivement pris (moteur, 1 position) | ≈ 2,3 / jour |
| **Ses entrées revendiquées** (32 sur 19 jours de live) | **1,68 / jour** |

Elle est plus sélective, mais d'un facteur **2,5**, pas d'un facteur 10. Un tri
de cette force ne transforme pas un résidu de 0,00 en système rentable — il
faudrait que sa sélection soit d'une qualité extraordinaire pour extraire un
avantage d'un vivier statistiquement neutre.

**L'hypothèse que ces chiffres rendent la plus plausible est donc ailleurs : son
avantage n'est pas dans le choix du balayage, il est dans la gestion de la
position.** Clôtures partielles échelonnées, pas de stop dur, stop suiveur ancré
sur une frontière structurelle — c'est un profil de gains entièrement différent
d'une cible fixe à 2 R ou 4 R protégée par un stop dur. S019 a testé son
déclencheur avec **notre** sortie, et cette sortie n'est pas la sienne.

C'est une hypothèse cohérente avec les données, pas une démonstration : la mesure
prouve que le déclencheur est neutre, elle ne prouve pas où se trouve l'avantage.

---

## Ce qui reste debout dans les résultats

Deux gradients, faibles mais monotones sur les 16 cellules :

- **sa session** (US + Asie, jamais Londres) améliore la R/trade dans 7 cas
  sur 8 ;
- **la porte de tendance journalière** l'améliore aussi, plus discrètement.

Aucun des deux ne rend une cellule positive et aucun ne survivrait à une
correction de multiplicité. Je les note parce qu'ils vont dans le sens du
discours de la source, pas parce qu'ils prouvent quoi que ce soit.

---

## Ce que je ne fais pas

- **Aucun réglage d'après-coup.** Ni `sweep_lookback`, ni `sweep_window`, ni
  commutateur supplémentaire. `FALSIFICATION.md` l'interdisait d'avance, et
  l'interdiction vaut surtout quand le résultat déçoit.
- **Aucune promotion**, évidemment. Statut RESEARCH, et il y reste.
- **Aucune suppression du code.** S019 documente une hypothèse mesurée et
  écartée. C'est un résultat, pas un déchet : il ferme une porte que quelqu'un
  rouvrirait sinon dans six mois.

---

## Ce que ça change pour la suite

1. **TCK-014 cesse d'être un confort et devient la question qui commande.**
   Tant que le moteur ne sait pas exprimer clôtures partielles et stop suiveur,
   on ne peut pas tester sa méthode — seulement son déclencheur, dont on sait
   maintenant qu'il ne porte rien seul. **Arbitrage Adrian demandé.**
2. **Les zones fatidiques deviennent la piste suivante côté entrée.** La porte
   directionnelle pilotée par des niveaux historiques fixes
   (`SYNTHESE_GEOMETRIE.md` § 1) est le seul filtre du corpus qui n'ait pas
   encore été mesuré. À traiter comme une hypothèse à part entière, avec ses
   propres critères écrits d'avance.
3. **TCK-018 est confirmé sur pièce.** À 25 pips de spread la cellule par défaut
   perd 275 R ; à 52 pips elle en perd 531. Le catalogue nous cachait la moitié
   de la facture — sur toutes les stratégies or du dépôt, pas seulement ici.

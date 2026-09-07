# VERDICT — S018, or v2 instruite par la méthode Doud

**Données** : MT5 Swissquote, XAUUSD **H1**, 2021-08-09 → 2026-09-04, 30 024 barres.
**Exécution** : celle du forward scellé v1 — spread 25 pips, slippage **0**,
position unique, cooldown 2, circuit breaker 3 pertes → 24 barres.
**Dépôt** : `b8c06b8`, branche `v2/gold`.
**R1 (causalité)** : **PASSÉ**, 5 points de grille dont le mode à état, couche
indicateur couverte. **R5 (conformance)** : **PASSÉ**.
**Cellule neutre = v1** : 784 signaux, égalité stricte. Vérifié à chaque exécution.

---

## Verdict en une ligne

**`NON RETENU en l'état`.** Aucun des cinq ingrédients ne produit une
amélioration de la v1 qui survive aux critères écrits dans `FALSIFICATION.md`.
Deux sont franchement négatifs, un est nul, deux sont faiblement positifs mais
achètent leur gain avec de l'effectif. Le seul ingrédient nettement positif au
R/trade — le long-only — **aggrave le défaut même que ce dossier devait
instruire**.

La v1 reste le meilleur objet dont nous disposons sur l'or, et son forward
scellé garde tout son sens.

---

## 1. Le témoin, remesuré sur la fenêtre étendue

Cellule neutre = S011 aux paramètres scellés, 2021-08 → 2026-09 :

| mesure | valeur |
|---|---|
| trades | **402** |
| R total | **+94,7** |
| R/trade | **+0,236** |
| win rate | 34,6 % |
| profit factor | 1,35 |
| drawdown max | 12,2 R |
| long / short | 229 à **+0,343** / 173 à **+0,094** |
| percentile vs témoin aléatoire | **100,0** |

Cohérent avec `S011/research/VERDICT.md` § 2.5 (400 trades, +90,4 R, +0,226) :
l'écart vient des trois semaines de barres supplémentaires. Concentration 2025
toujours là : **59 % du R total**.

---

## 2. La lecture principale — effet marginal de chaque ingrédient

Moyenne du R/trade sur les 16 cellules où l'ingrédient est actif contre les 16
où il ne l'est pas. Cellules sous 20 trades exclues.

| ingrédient | source | OFF | ON | Δ | verdict |
|---|---|---|---|---|---|
| `side_mode` long-only | D1 (@ 21:52) | +0,167 | **+0,312** | **+0,145** | positif au R/trade — mais voir § 3 |
| `session_filter` doud | D5 (@ 35:35) | +0,219 | +0,260 | +0,041 | faible |
| `htf_bias` journalier | D2 (@ 23:32) | +0,224 | +0,255 | +0,031 | faible |
| `entry_mode` équilibre | D4 (@ 18:08) | +0,235 | +0,245 | **+0,010** | **nul** |
| `channel_source` corps | D3 (@ 17:52) | +0,291 | +0,188 | **−0,103** | **négatif** |

Et le sweep secondaire, hors grille :

| `max_hold_bars` | aucun | 24 | 48 |
|---|---|---|---|
| cellule neutre | 402 tr, **+0,236**/tr | 429 tr, +0,194/tr | 414 tr, +0,195/tr |

**D3 est falsifié dans cette traduction** : un canal Donchian sur les corps casse
plus souvent (568 trades contre 402) et casse moins bien. « La structure et non
la mèche » peut rester vraie chez elle, sur son timeframe et avec sa lecture —
elle est fausse ici.

**D10 est falsifié** : borner la durée dégrade le R/trade à effectif comparable.
Cohérent avec la géométrie de la v1 : un TP à 4 ATR a besoin de temps.

**D4, le cœur annoncé de la v2, ne produit rien** : +0,010 R/trade de moyenne.
L'entrée au repli à l'équilibre n'est ni meilleure ni pire que l'entrée à la
cassure — elle est surtout beaucoup plus rare (173 trades contre 402 en cellule
`EQU ext both - -`).

---

## 3. Le long-only : un gain qui n'en est pas un pour le portefeuille

C'est la seule affirmation de la source qui produise un effet net. Elle mérite
d'être regardée de près, parce qu'elle échoue précisément là où on ne l'attend
pas.

| | v1 (neutre) | v1 + long-only |
|---|---|---|
| trades | 402 | **235** |
| R total | **+94,7** | +83,2 |
| R/trade | +0,236 | **+0,354** |
| win rate | 34,6 % | **37,9 %** |
| profit factor | 1,35 | **1,56** |
| **drawdown max** | **12,2 R** | **17,3 R** |
| hors échantillon (4 fenêtres) | **+19,90** moy., 180 trades | +18,95 moy., 115 trades |

Le R/trade monte de 50 %, et **le R total baisse de 12 % pendant que le drawdown
monte de 42 %**. `FALSIFICATION.md` § 2 avait écrit la clause d'exécution :
*« gain de R/trade payé par une dégradation du drawdown et du R total telle que
le portefeuille n'y gagne rien »*. Les deux sont dégradés — la clause tire.

Et le pire est dans les années :

| | 2021 | 2022 | 2023 | 2024 | **2025** | 2026 |
|---|---|---|---|---|---|---|
| v1 neutre | −10,1 | +9,8 | +10,0 | +14,9 | **+55,9 (59 %)** | +14,2 |
| v1 + long-only | +1,1 | **−8,7** | +0,6 | +22,1 | **+53,3 (64 %)** | +14,9 |

Retirer les shorts **augmente** la part de 2025 (59 % → 64 %) et **rend 2022
négatif**. La réserve numéro un du dossier v1 — « 62 % du résultat vient de la
seule année 2025 » — n'est pas corrigée, elle est aggravée. On n'a pas ajouté un
edge : on a concentré le beta d'un or haussier, ce que `S011/research/VERDICT.md`
§ 2.4 appelait déjà « du beta déguisé en système ».

---

## 4. Le hors échantillon, et pourquoi les belles cellules ne comptent pas

Walk-forward ancré, 4 fenêtres, 32 cellules : **7 STRICT observées** contre
**≈ 1,6 attendues** par pur hasard. Le chiffre invite à regarder — la liste
refroidit :

| cellule | moy. hors échantillon | trades hors échantillon |
|---|---|---|
| **neutre (= v1)** | **+19,90** | **180** |
| v1 + long-only | +18,95 | 115 |
| équilibre + long-only | +4,97 | 38 |
| équilibre + corps + long-only + session + biais | +3,99 | 31 |
| équilibre + corps + long-only + session | +3,39 | 37 |
| équilibre + long-only + session | +2,77 | 25 |
| équilibre + corps + session + biais | +2,64 | 40 |

**Les deux premières places sont la v1 et la v1 amputée de ses shorts.** Toutes
les cellules qui portent réellement la méthode Doud arrivent derrière, à un
cinquième du résultat, sur 25 à 40 trades hors échantillon — c'est-à-dire sous
le seuil où ce projet accepte de lire quoi que ce soit.

L'illusion in-sample est mesurée à **16 %** : la meilleure configuration plein
échantillon perd 16 % de son rendement affiché une fois l'optimisation retirée.

Les cellules les plus flatteuses du tableau plein échantillon —
`EQU ext LONG SESS BIAS` à +0,431 R/trade, `EQU ext both SESS BIAS` à +0,420 —
tiennent sur **50 et 78 trades**. À ces effectifs, l'intervalle de confiance
recouvre largement zéro. Elles ne sont pas un résultat.

---

## 5. La seule piste que ce dossier laisse ouverte

`EQU ext both SESS BIAS` (équilibre + sessions + biais journalier, les deux sens)
produit une population de trades **dont le profil annuel est presque l'inverse
de celui de la v1** :

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| v1 neutre (402 tr) | −10,1 | +9,8 | +10,0 | +14,9 | **+55,9** | +14,2 |
| EQU ext both SESS BIAS (78 tr) | +3,1 | +14,7 | +9,8 | +5,4 | **−4,6** | +4,3 |

Un jeu de trades qui gagne là où la v1 ne gagne pas, et qui perd sur l'année qui
porte la v1, n'est pas un doublon : c'est potentiellement une **décorrélation**.
Sur 78 trades, ça ne se conclut pas — mais c'est le seul endroit de ce dossier
où la méthode Doud produit autre chose qu'une version amaigrie de la v1.

À instruire, si Adrian le veut, par un dispositif dédié : effectif d'abord
(timeframe plus fin ou fenêtre plus longue), et pas par une cellule de plus dans
une grille déjà à 32.

---

## 6. Ce que ce verdict ne dit pas

- **Il ne juge pas la méthode de Cindy.** Nous avons mesuré cinq de ses lectures
  d'**entrée**, en H1, sans ses sorties partielles, sans son stop suiveur, sans
  calendrier économique et sans son biais macro — c'est-à-dire sans ce qu'elle
  décrit comme l'essentiel de son travail. Un verdict négatif ici dit que ces
  cinq lectures, traduites ainsi, n'améliorent pas *notre* cassure Donchian.
- **Il ne dit rien du timeframe qui est le sien.** Elle scalpe ; nous mesurons en
  H1 pour rester comparables à la v1.
  **[Renvoi 2026-09-07]** Affirmation datée : `results_M15.json` et `results_M5.json`
  existaient déjà (produits le 2026-09-06) et ont depuis été dépouillés — voir
  `research/VERDICT_addendum_M15-M5_2026-09-07.md`. Elle ne dit toujours rien de
  l'intraday réel (M1 chez elle), mais M15 et M5 sont désormais mesurés : la v1
  traduite telle quelle y devient nettement perdante, et une seule cellule sur 64
  survit à la fois au walk-forward strict et au spread réellement observé.
- **Les chiffres restent optimistes** d'un montant inconnu : slippage à 0, comme
  la v1 et son témoin.

---

## 7. Décisions

1. **S018 reste `RESEARCH`.** Pas de promotion, pas de forward scellé dédié :
   il n'y a rien à sceller.
2. **La v1 continue.** `studies/gold_forward/` n'est pas touchée et garde son
   statut de seul dispositif capable de trancher sur l'or.
3. **D3 (corps) et D10 (sortie au temps) sont falsifiés** dans cette traduction —
   inutile de les retenter tels quels.
4. **D1 (long-only) est mesuré et documenté comme concentration de beta**, pas
   comme edge. À ne pas ressortir comme « amélioration » sans ce paragraphe.
5. **Piste ouverte** : la décorrélation du § 5, à instruire par effectif, sur
   décision d'Adrian.
6. Le code reste en place et testé : rejouer le dossier coûte une commande
   (`python strategies/S018_gold_doud_v2/backtests/run_wf.py`), ce qui rend la
   reprise possible si de nouvelles données ou un moteur enrichi (tickets
   `TCK-014`, `TCK-016`) changent la donne.

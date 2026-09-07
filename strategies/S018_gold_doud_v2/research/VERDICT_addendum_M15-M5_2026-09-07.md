# ADDENDUM — S018, mailles fines M15 et M5 (dépouillement différé)

**Date** : 2026-09-07. **Dépôt** : `c40ce5f` (arbre modifié au moment de la production
des mesures), branche `v2/gold`.
**Origine** : `backtests/results_M15.json` et `backtests/results_M5.json` ont été
produits le 2026-09-06 (13:57 et 14:13) puis jamais lus. `research/VERDICT.md` § 6
affirmait *« elle scalpe ; nous mesurons en H1 »* — l'affirmation est devenue fausse
dès que ces deux fichiers ont existé. Cet addendum les dépouille. Il **complète**
`VERDICT.md`, il ne le réécrit pas — voir § 8 pour le renvoi ajouté en place.
**Données** : mêmes barres MT5 Swissquote XAUUSD que le VERDICT (2021-08-09 →
2026-09-04), agrégées en M15 (119 992 barres) et M5 (358 624 barres). **Exécution** :
identique au VERDICT (spread catalogue 25 pips, slippage 0, moteur du forward scellé).
**R1/R5** : PASSÉS sur les deux mailles (`causality_M15.txt`, `causality_M5.txt`,
`conformance_M15.txt`, `conformance_M5.txt`). **Cellule neutre = code de la v1** : égalité
stricte des signaux vérifiée sur les deux mailles (3 271 signaux en M15, 11 111 en M5).

**Cette égalité ne dit PAS ce qu'on aimerait qu'elle dise**, et la sortie de mesure le
porte déjà en capitales (`backtests/grid_M5.txt` ligne 18) : *« la v1 scellée est en H1 ;
ce qui est comparé ici est S011 APPLIQUÉE À DES BARRES M5, pas la référence du forward.
L'égalité prouve l'équivalence des deux CODES, elle ne rattache pas ces chiffres au
dossier gold_forward. »* Une première rédaction de cet addendum affirmait « même garantie
qu'en H1 » — c'était le contraire de sa source, et c'est corrigé ici.

Ce que la comparaison mesure réellement : S011 hors de la maille pour laquelle elle a été
sélectionnée. Et le chiffre est net — sur M5, la cellule neutre rend **−548,7 R sur
5 064 trades** (−0,108 par trade, taux de réussite 27,3 %). La v1 ne survit pas au
changement de maille.

---

## Verdict en une ligne

**Les mailles fines n'améliorent rien.** La cellule neutre (= la v1 telle quelle)
devient nettement perdante dès qu'on descend de timeframe. Une seule cellule sur les
64 mesurées (32 en M15, 32 en M5) survit à la fois au test hors échantillon le plus
strict du dossier **et** à un coût de spread réaliste — et ce n'est pas l'entrée à
l'équilibre (D4, le cœur annoncé de la v2) qui la porte. Le M5 ne produit aucune
cellule STRICT, ce qui est **en dessous** de l'attente par pur hasard. La piste
laissée ouverte au § 5 du VERDICT (`EQU ext both SESS BIAS`) se dégrade quand on lui
donne l'effectif qu'elle réclamait — elle ne se confirme pas.

---

## 1. Le coût de bord ne baisse pas, l'amplitude si

| maille | ATR14 médian (pips) | risque médian 1,5 ATR (pips) | coût catalogue (25 pips) en % du R |
|---|---:|---:|---:|
| H1 | 572 | 858 | **2,9 %** |
| M15 | 276 | 414 | **6,0 %** |
| M5 | 152 | 228 | **11,0 %** |

Même coût en pips, risque par trade divisé par ~2 puis ~3,8 en descendant de H1 à
M15 puis M5 : le poids relatif du spread double, puis quadruple. C'est mécanique,
avant même de discuter un seul signal — et ça s'aggrave encore une fois le spread
**réellement mesuré** substitué au catalogue (§ 6).

---

## 2. La cellule neutre (= v1 traduite telle quelle) sur les mailles fines

| maille | trades | R total | R/trade | win rate | profit factor | drawdown max | percentile vs témoin aléatoire |
|---|---:|---:|---:|---:|---:|---:|---:|
| H1 | 402 | +94,7 | **+0,236** | 34,6 % | 1,35 | 12,2 R | **100,0** |
| M15 | 1 604 | **−153,6** | **−0,096** | 26,2 % | 0,87 | 172,9 R | **11,5** |
| M5 | 5 064 | **−548,7** | **−0,108** | 27,3 % | 0,86 | 562,5 R | **27,0** |

**Mesuré, pas une impression** : la même géométrie de signal (Donchian 40 sur les
extrêmes, TP 4 ATR, SL 1,5 ATR, sans aucun filtre Doud) qui vaut à la v1 le
percentile 100 en H1 tombe au percentile 11,5 en M15 — c'est-à-dire pire que 88,5 %
des configurations aléatoires du même témoin. Le drawdown en multiples de R explose
(172,9 R en M15, 562,5 R en M5) parce que la même cascade de pertes se rejoue sur
un risque par trade beaucoup plus petit. **La v1 ne se traduit pas telle quelle sur
une maille plus fine** ; rien dans ce dossier ne le suggérait avant cette mesure.

---

## 3. Les cinq ingrédients se comportent-ils différemment sur les mailles fines ? Oui.

Même lecture que `VERDICT.md` § 2 : moyenne du R/trade sur les 16 cellules où
l'ingrédient est actif contre les 16 où il ne l'est pas, cellules sous 20 trades déjà
incluses ici (aucune ne l'est aux effectifs de ce tableau).

| ingrédient | Δ H1 | Δ M15 | Δ M5 | lecture |
|---|---:|---:|---:|---|
| D1 `side_mode` long-only | **+0,145** | +0,042 | +0,024 | positif partout, l'effet **s'amenuise** en descendant de maille |
| D2 `htf_bias` journalier | +0,031 | +0,051 | +0,004 | positif partout, pic en M15, quasi nul en M5 |
| D3 `channel_source` corps | **−0,103** (falsifié en H1) | **+0,038** | +0,007 | **change de signe** — négatif en H1, faiblement positif en M15, nul en M5 |
| D4 `entry_mode` équilibre | +0,010 (nul en H1) | **+0,074** | +0,042 | **devient le plus fort effet marginal du tableau en M15** — nul en H1 |
| D5 `session_filter` doud | +0,041 | +0,054 | +0,049 | positif et stable sur les trois mailles |

Deux constats qui répondent directement à la question :

- **D3 (corps) n'est pas falsifiable « en général »** — il l'est *dans la traduction
  H1*. En M15 son signe s'inverse. L'affirmation du VERDICT (« elle peut rester vraie
  chez elle, sur son timeframe ») se vérifie ici de façon inattendue : plus on se
  rapproche de son terrain (l'intraday), moins le canal sur les corps est un handicap.
- **D4 (l'équilibre), le cœur revendiqué de la v2, ne produit rien en H1 mais devient
  l'ingrédient le plus fort en M15.** C'est la même méthode Doud qui, sur une maille
  plus fine, cesse d'être neutre. Voir § 4 pour la limite de cette lecture : l'effet
  marginal moyen et la meilleure cellule individuelle ne racontent pas la même
  histoire.

---

## 4. Walk-forward ancré — hors échantillon, les trois mailles

| maille | configurations | STRICT observées | attendues par pur hasard (32 × 5 %) |
|---|---:|---:|---:|
| H1 | 32 | **7** | ≈ 1,6 |
| M15 | 32 | **3** | ≈ 1,6 |
| M5 | 32 | **0** | ≈ 1,6 |

M15 reste au-dessus de l'attente par hasard ; **M5 tombe en dessous** — pas une
absence d'edge, un signal négatif net une fois qu'on cherche à en trouver un.

### 4.1 Les 3 cellules STRICT de M15 (positives sur les 4 fenêtres d'entraînement ET
de test — le critère le plus dur du dossier)

| cellule | ingrédients actifs | fenêtres OOS (W1·W2·W3·W4) | moy. OOS | trades OOS | plein échantillon (n · R/tr) |
|---|---|---|---:|---:|---|
| `brk BOD LONG SESS BIAS` | D1 D2 D3 D5 (D4 **off** — reste l'entrée cassure de la v1) | +15,37 · +0,59 · +36,49 · +0,25 | **+13,18** | 221 | 411 tr · **+0,208** R/tr |
| `EQU ext both - BIAS` | D2 D4 (D1 D3 D5 off) | +15,95 · +2,08 · +6,92 · +7,94 | +8,22 | 187 | 501 tr · +0,090 R/tr |
| `EQU ext both SESS BIAS` | D2 D4 D5 (D1 D3 off) | +1,46 · +4,73 · +3,40 · +0,67 | +2,57 | 100 | 272 tr · +0,081 R/tr |

Deux nuances à ne pas perdre en route :

1. **Le critère STRICT demande un signe, pas une marge.** La première cellule tient
   ses fenêtres W2 et W4 à +0,59 et +0,25 R — techniquement positif, pas confortable.
2. **La cellule la plus fiable (première ligne) n'utilise PAS l'entrée à l'équilibre
   (D4).** Elle garde la cassure de la v1 et ajoute corps + long-only + session +
   biais. Les deux cellules qui, elles, activent l'équilibre passent le test avec des
   marges hors échantillon plus minces (+8,22 et +2,57 contre +13,18) — cohérent avec
   la remarque du § 3 : l'effet marginal *moyen* de D4 est le plus fort du tableau,
   mais la cellule individuelle la plus robuste ne le porte pas. Les deux lectures ne
   racontent pas la même histoire ; aucune des deux n'efface l'autre.

### 4.2 M5 — zéro STRICT, et les trois meilleurs échecs montrent pourquoi

| cellule (échec) | W1 · W2 · W3 · W4 | moy. OOS | trades OOS |
|---|---|---:|---:|
| `EQU ext both - SESS` | −6,27 · +17,70 · +30,32 · **−8,36** | +8,35 | 609 |
| `EQU ext both SESS BIAS` | −1,89 · +21,41 · +19,54 · **−9,16** | +7,47 | 337 |
| `EQU BOD both SESS BIAS` | −13,94 · +31,29 · +19,83 · **−7,56** | +7,40 | 490 |

Les trois candidats les plus proches du seuil basculent négatifs sur **la première ET
la dernière fenêtre**, portés uniquement par deux fenêtres centrales. Ce n'est pas un
effectif insuffisant (100 à 600 trades hors échantillon par fenêtre) : c'est une
instabilité mesurée sur un effectif large.

---

## 5. Le stress-test du spread réel — la nuance qui manque à toute lecture ci-dessus

**Ces mesures sont faites au spread catalogue de 25 pips.** Le spread réellement
observé sur les barres (`AUDIT_dossier-doud-etat-et-suite_2026-09-07.md` § 1.1,
médiane annuelle, colonne `spread` de `C:/db/tradingBot/bars_cache/XAUUSD_*.pkl`,
identique sur M1/M5/M15/H1) est très supérieur :

| année | 2021 | 2022 | 2023 | 2024 | 2025 | **2026** |
|---|---:|---:|---:|---:|---:|---:|
| spread médian (pips) | 50 | 51 | 54 | 55 | 65 | **90,8** |

Sur une maille fine, le risque par trade est plus petit (§ 1) — le même écart en pips
pèse donc *proportionnellement* bien plus lourd :

| coût en % du R par année, à risque médian de la maille | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|
| H1 (catalogue 2,9 %) | 5,8 % | 5,9 % | 6,3 % | 6,4 % | 7,6 % | 10,6 % |
| M15 (catalogue 6,0 %) | 12,1 % | 12,3 % | 13,1 % | 13,3 % | 15,7 % | **22,0 %** |
| M5 (catalogue 11,0 %) | 21,9 % | 22,4 % | 23,7 % | 24,1 % | 28,5 % | **39,8 %** |

**Méthode de correction (approximation assumée, pas un rejeu du moteur)** : pour
chaque année, le surcoût `(spread réel − 25 pips)` est reconverti en R via le risque
médian de la maille (même convention que `edge_cost.cost_pct_of_r`, déjà dans les
JSON) et soustrait du R total de l'année, trade par trade. Ce n'est pas une nouvelle
exécution du backtester (R9 l'interdit, `core/backtest/engine.py` est scellé) — c'est
une relecture linéaire des chiffres déjà mesurés, avec le risque médian comme seule
approximation.

| cellule | R/trade @ 25 pips (catalogue) | R/trade @ spread réel | lecture |
|---|---:|---:|---|
| **H1, neutre (= v1)** | +0,236 | **+0,193** | rogné d'un cinquième, reste solide |
| **M15, STRICT `brk BOD LONG SESS BIAS`** (221 tr. OOS) | +0,208 | **+0,119** | rogné de plus de moitié, **reste net positif** |
| M15, STRICT `EQU ext both - BIAS` (187 tr. OOS) | +0,090 | **+0,007** | rendu **nul** |
| M15, STRICT `EQU ext both SESS BIAS` (100 tr. OOS) | +0,081 | **−0,001** | **passe négatif** |
| M15, neutre (= v1 traduite) | −0,096 | −0,182 | déjà mort, s'enfonce |
| M5, meilleur R/trade plein échantillon (`EQU BOD LONG SESS BIAS`, 696 tr.) | +0,036 | **−0,119** | **passe nettement négatif** |
| M5, meilleur R total plein échantillon (`EQU ext both SESS BIAS`, 784 tr.) | +0,035 | **−0,122** | **passe nettement négatif** |
| M5, neutre (= v1 traduite) | −0,108 | −0,264 | déjà mort, s'enfonce |

**Une seule cellule sur les 64 mesurées franchit les trois haies à la fois — STRICT
sur 4 fenêtres, effectif hors échantillon ≥ 20 (221, ici), et positive au spread réel
mesuré plutôt qu'au catalogue** : `brk BOD LONG SESS BIAS` en M15. Les deux autres
survivantes STRICT de M15 (celles qui portent l'entrée à l'équilibre) meurent au
contact du coût réel. **Sur M5, aucune des deux cellules qui semblaient positives au
catalogue ne survit** — la consigne de relire toute cellule M5 positive à travers ce
facteur, donnée en amont de ce dépouillement, se vérifie : les deux basculent
nettement négatives.

---

## 6. La piste ouverte du § 5 du VERDICT, suivie sur l'effectif qu'elle réclamait

`EQU ext both SESS BIAS` — équilibre + extrêmes + les deux sens + sessions + biais —
était la seule cellule que le VERDICT laissait ouverte, précisément *faute
d'effectif* (78 trades en H1) et *pour son profil annuel presque inverse de la v1*.
Elle existe dans les trois mesures :

| maille | trades | R/trade @ catalogue | dans la liste STRICT ? | R/trade @ spread réel |
|---|---:|---:|---|---:|
| H1 | 78 | +0,420 | non | — |
| M15 | 272 | +0,081 | **oui** (la plus faible des 3, moy. OOS +2,57) | **−0,001** |
| M5 | 784 | +0,035 | non | **−0,122** |

**L'effectif supplémentaire ne confirme pas la piste, il la referme.** Son R/trade
plein échantillon s'effondre à mesure que l'effectif grandit (+0,420 → +0,081 →
+0,035) — signature classique d'un résultat porté par le petit nombre plutôt que par
un edge. Elle ne devient STRICT qu'une fois, et faiblement, en M15 ; elle meurt sous
le coût réel partout où elle est mesurée. La décorrélation annuelle qui la rendait
intéressante en H1 (§ 5 VERDICT) n'a jamais été retestée ici — ce n'est pas nécessaire,
le résultat ne survit plus assez loin en amont pour que la question se pose.

---

## 7. Ce que cet addendum ne change pas aux décisions du VERDICT

- **S018 reste `RESEARCH`.** Aucune cellule ne réunit cumulativement les conditions de
  promotion de `FALSIFICATION.md` § 5 (effet marginal positif, ≥ 20 trades hors
  échantillon, percentile ≥ 95, **et** un forward-test scellé dédié — aucun n'existe).
- **La v1 continue sans changement** ; ce dossier ne l'a pas touchée.
- **D3 et D10 restent falsifiés dans leur traduction H1** — cet addendum montre que D3
  change de signe ailleurs, ce qui confirme la mise en garde du VERDICT (« elle peut
  rester vraie chez elle ») plutôt que de la contredire.
- **Une observation nouvelle, à signaler et pas à trancher ici** : `brk BOD LONG SESS
  BIAS` en M15 (411 trades plein échantillon, 221 hors échantillon, STRICT sur les 4
  fenêtres, positive au spread réellement mesuré) est le résultat le plus complet de
  tout le dossier Doud — H1, M15 et M5 confondus. Elle ne valide pas la méthode Doud :
  elle garde l'entrée cassure de la v1 (D4 off) et n'ajoute que corps + long-only +
  session + biais. Si Adrian veut l'instruire, elle appellerait le même dispositif que
  toute promotion sérieuse : falsification écrite d'avance, puis un forward-test scellé
  dédié sur M15 — pas une case de plus dans la grille existante.

---

## 8. Renvoi à ajouter dans `VERDICT.md` § 6 (par pointeur, sans réécriture)

La ligne *« Il ne dit rien du timeframe qui est le sien. Elle scalpe ; nous mesurons
en H1 pour rester comparables à la v1. »* est datée du 2026-09-06 et n'est plus
exacte depuis que `results_M15.json`/`results_M5.json` ont été dépouillés. Elle reste
en place — ce fichier ne réécrit pas l'historique — et porte désormais un renvoi
explicite vers le présent addendum (voir modification apportée en pied de § 6 du
VERDICT).

---

## Sources chiffrées de cet addendum

`backtests/results_M15.json`, `backtests/results_M5.json`, `backtests/grid_M15.txt`,
`backtests/grid_M5.txt`, `backtests/causality_M15.txt`, `backtests/causality_M5.txt`,
`backtests/conformance_M15.txt`, `backtests/conformance_M5.txt`,
`support/designs/AUDIT_dossier-doud-etat-et-suite_2026-09-07.md` § 1.1 (spread réel
mesuré par année). Tous les chiffres de correction au spread réel (§ 5) sont dérivés
de ces fichiers par un calcul reproductible, pas relus depuis une nouvelle exécution.

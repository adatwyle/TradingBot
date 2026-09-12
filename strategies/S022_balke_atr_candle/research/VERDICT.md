# VERDICT — S022, ATR Candle Breakout (René Balke), or H1

**Données** : XAUUSD H1, MT5 Swissquote, **2020-09-14 → 2026-09-11**, 35 443 barres
(5,99 ans), cache rafraîchi le 2026-09-12 (données du jour).
**Exécution** : moteur commun (R9), entrée au close du signal, stop payé au pire de
`min(stop, open)`, stop prioritaire sur cible dans une même barre, slippage 0.
**Bras de décision** : FIDÈLE — une position, **pas de refroidissement, pas de
coupe-circuit** (règle propre de S022, déclarée avant la mesure).
**Dépôt** : `0c5d0f3` (arbre modifié). **R1 et R5** passés sur deux cellules — et le
harnais s'arrête (code 2) sans rien publier si l'un des deux échoue.
**Critères** : `FALSIFICATION.md`, écrits le 2026-09-12 à 19:11, avant l'exécution du
harnais — appliqués ci-dessous sans retouche (addendum du 19:48 : deux points
d'interprétation consignés après coup, aucun seuil touché).
**Mesure brute** : `backtests/results.json`, journal `backtests/run_all.log`.

---

## Verdict en une ligne

**ÉCHEC au sens des critères écrits d'avance** : **0 cellule STRICT sur 12** au
walk-forward ancré, la cellule de ses réglages live est **négative hors échantillon**
(−10,4 R sur 227 trades) et son percentile témoin est 65. Ce n'est **pas** un échec par
coût (8,9 % du R au spread mesuré, seuil 35 %). **Mais la reproduction, elle, est
fidèle** : 140 signaux/an contre 141 publiés, 20,9 % de réussite contre ≈ 23 %, gain
moyen 3,94 R pour 1,02 R de perte moyenne contre son 370 €/90 €. Nous mesurons bien sa
règle ; sur nos six ans d'or H1, elle ne dégage rien.

---

## 1. Fidélité — le test que sa publication rend possible

| Grandeur | Publié (11 ans, tick réel) | Mesuré (6 ans, H1) | Fenêtre écrite d'avance | |
|---|---|---|---|---|
| Signaux par an | 141 (1 552 / 11 ans) | **139,6** (836 signaux) | — | **quasi identique** |
| Trades par an | 141 | **89,5** (536 trades) | 85 – 200 | OK |
| Taux de réussite | ≈ 23 % | **20,9 %** | 17 – 30 % | OK |
| Motifs de sortie | non publié | **79 % de stops** (424 SL / 112 TP) | dominé par les stops | OK |
| Gain / perte moyens | 370 € / 90 € (ratio 4,1) | **+3,94 R / −1,02 R** (ratio 3,87) | — | cohérent |
| Profit factor | 1,15 | **1,02** | — | en dessous |
| R/trade | +0,15 R brut (RR 4 × WR 23 %) | **+0,019** (catalogue) · **−0,037** (spread mesuré) | — | en dessous |

**La règle est reproduite.** Quatre grandeurs indépendantes de la géométrie des
sorties — la fréquence des signaux, le taux de réussite, la domination des stops et le
rapport gain/perte — tombent sur ses chiffres. Le générateur de signaux (ATR moyenne
simple à 200, décalé d'une barre, proximité 25 % de l'amplitude, sens de la bougie)
produit bien ce que son EA produit. Les deux critères de fidélité chiffrés écrits
d'avance sont **tenus**.

**Écart de trades, expliqué** : 836 signaux produits, **300 refusés (36 %) parce qu'une
position est déjà ouverte** — contrainte de la plateforme (une position par symbole),
pas de son EA. Notre taux de SIGNAUX (140/an) colle à son nombre de TRADES (141/an) :
son EA semble donc prendre pratiquement tous les signaux, positions superposées
comprises. Voir § 4, c'est la première question ouverte.

**Ce qui n'explique PAS l'écart de rentabilité** : le pessimisme du moteur. Sur les
424 stops de la cellule live, **0** a été pris sur une barre qui touchait aussi la
cible. La règle « stop prioritaire dans la même barre », premier suspect nommé dans
`FALSIFICATION.md`, ne coûte **rien** ici. Durée médiane de détention : 11 barres.

**Où passe la différence** : avec notre propre gain moyen (3,94 R) et notre propre
perte moyenne (1,02 R), le seuil de rentabilité est à **20,5 % de réussite**. Nous
mesurons **20,9 %** — 0,4 point au-dessus. Ses 23 % donneraient +0,12 R/trade. **Toute
la stratégie tient dans deux points de taux de réussite**, et nous ne les avons pas sur
cette période, chez ce courtier, à cette maille.

---

## 2. Les douze cellules, hors échantillon

Walk-forward ancré, 4 fenêtres, bras fidèle. **STRICT = 0/12 brutes, 0/12 après le
seuil « ≥ 20 trades hors échantillon »** — le seuil est appliqué par le harnais
lui-même, pas à la main dans ce document (≈ 0,6 STRICT attendue par pur hasard ; le
moteur affiche le même nombre arrondi à 1). **TIER 1 = 0/12**.

| Cellule | plein échantillon (R) | R/trade | WR % | OOS moyen (R) | OOS total (R) | trades OOS |
|---|---:|---:|---:|---:|---:|---:|
| ×2,0 p35 % sl1,0 % | +19,6 | +0,034 | 34,9 | **+0,52** | +2,1 | 304 |
| ×2,0 p25 % sl1,0 % | +24,9 | +0,049 | 35,4 | −1,41 | −5,6 | 261 |
| ×3,0 p35 % sl1,0 % | +9,2 | +0,028 | 34,7 | −1,99 | −8,0 | 136 |
| ×2,5 p35 % sl0,5 % | +22,2 | +0,035 | 21,2 | −2,29 | −9,2 | 280 |
| **×2,5 p25 % sl0,5 % (ses réglages live)** | **+10,0** | **+0,019** | **20,9** | **−2,60** | **−10,4** | **227** |
| ×3,0 p25 % sl1,0 % | −4,3 | −0,015 | 33,2 | −3,20 | −12,8 | 114 |
| ×2,0 p25 % sl0,5 % | +10,4 | +0,013 | 20,9 | −3,99 | −15,9 | 380 |
| ×2,5 p35 % sl1,0 % | +21,1 | +0,048 | 35,3 | −4,13 | −16,5 | 210 |
| ×3,0 p25 % sl0,5 % | +4,6 | +0,013 | 20,8 | −4,28 | −17,1 | 135 |
| ×2,5 p25 % sl1,0 % | +13,7 | +0,037 | 34,9 | −5,57 | −22,3 | 177 |
| ×3,0 p35 % sl0,5 % | +3,3 | +0,008 | 20,7 | −6,12 | −24,5 | 167 |
| ×2,0 p35 % sl0,5 % | −26,3 | −0,029 | 20,0 | −8,39 | −33,6 | 452 |

Onze cellules sur douze sont négatives hors échantillon. La douzième rapporte
**+2,06 R sur 304 trades hors échantillon**, soit **+0,007 R/trade** — et n'est pas
STRICT (elle ne tient pas les quatre fenêtres).

L'illusion in-sample est exemplaire : la meilleure cellule en plein échantillon affiche
**+24,9 R** et rend **−5,6 R** hors échantillon — **123 % du rendement affiché
disparaît** une fois l'optimisation retirée.

---

## 3. Application des critères, un par un

| Critère de réussite (écrit d'avance) | Mesuré | Verdict |
|---|---|---|
| 1. ≥ 1 cellule STRICT avec ≥ 20 trades OOS | **0 STRICT / 12** | ✗ |
| 2. Percentile témoin ≥ 90 | live **65,0** ; meilleure cellule plein échantillon 92,0 (mais non STRICT) | ✗ |
| 3. R/trade > 0 au spread mesuré | live **−0,037** ; meilleure cellule +0,022 | ✗ (sur la cellule live) |
| 4. ≥ 2 STRICT ou une cellule à p ≥ 97 | 0 STRICT, percentile maximum 92,0 | ✗ |
| 5. La cellule par défaut positive hors échantillon | **−10,4 R** sur 227 trades OOS | ✗ |

| Clause d'échec (une suffit) | Mesuré | |
|---|---|---|
| Aucune cellule STRICT / aucune à p ≥ 90 | 0 STRICT | **déclenchée** |
| Signal disparaît entre plein échantillon et OOS | +10,0 R → −10,4 R sur la cellule live ; 123 % d'illusion sur la meilleure | **déclenchée** |
| Résultat porté par une seule année | 2023 vaut +30,2 R pour un total de +10,0 R = **301 %** | **déclenchée** |
| Coût > 35 % du R médian | **8,9 %** au spread mesuré (2,5 % au catalogue) | non déclenchée |

« Non concluant » ne s'applique pas : l'effectif hors échantillon va de 114 à 452
trades selon la cellule, et 227 pour la cellule live. **L'échec est mesuré, pas subi
faute de données.**

Par année, cellule live (R, trades) : 2020 −3,6 (23) · 2021 −6,9 (84) · 2022 −6,6 (89)
· **2023 +30,2 (86)** · 2024 −3,9 (82) · **2025 −17,3 (96)** · 2026 +18,1 (76). Deux
années positives sur sept — dont l'une porte trois fois le résultat total.

---

## 4. Ce que ce verdict ne dit pas — à lire avant d'archiver la piste

1. **La règle n'est pas invalidée en soi : c'est SA règle, sur NOS six ans, à NOTRE
   maille, chez NOTRE courtier, qui ne rapporte rien.** Son échantillon publié couvre
   2015-2026 en tick réel ; le nôtre commence en septembre 2020. La reproduction du
   signal est exacte à 1 % près en fréquence ; la divergence porte uniquement sur le
   taux de réussite (20,9 % contre 23 %) — deux points qui font toute la différence à
   RR 4.
2. **La contrainte « une position » retire 36 % des signaux, et elle est de nous, pas
   de lui.** Son guide d'entrées ne documente aucun plafond de positions, et son nombre
   de trades publié (141/an) correspond à notre nombre de SIGNAUX (140/an), pas à notre
   nombre de trades (89/an). Les 536 trades mesurés sont donc un sous-ensemble choisi
   par « premier arrivé, pas de recouvrement » — un choix de plateforme. **Mesurer les
   836 signaux sans cette contrainte est la première chose à instruire**, avec
   falsification écrite d'avance. Ce n'est pas fait ici : ce bras n'était pas déclaré
   avant la mesure, et on n'ajoute pas un test après avoir lu les résultats.
3. **Le témoin est à lire avec méfiance** : sur les deux cellules examinées, l'effectif
   des tirages aléatoires s'écarte de plus de 15 % de la référence (438 tirages médians
   contre 536 trades pour la cellule live ; 351 contre 506 pour l'autre). Le percentile
   compare alors deux effectifs différents. Il est de toute façon sous le seuil pour la
   cellule live (65,0), et la distribution nulle est très large (médiane −7,7 R,
   p95 +59,1 R) : sur l'or, une entrée aléatoire suivie d'un stop à 0,5 % et d'une
   cible à 2 % gagne parfois beaucoup, par simple dérive du sous-jacent.
4. **Slippage à 0**, comme partout dans le dépôt — et cette stratégie entre par
   définition sur des bougies de forte amplitude, c'est-à-dire exactement quand
   l'exécution coûte le plus cher. Le chiffre réel est donc **plus mauvais** que
   −0,037 R/trade, d'un montant inconnu.
5. **Le coût de bord n'est pas le coupable**, mais il n'est pas négligeable : le spread
   médian réellement coté sur l'or (90,8 pips, soit 0,91 $/once) est **3,6 fois** le
   spread catalogue (25 pips). Il transforme +0,019 R/trade en −0,037 R/trade, soit
   **+10,0 R → −19,6 R** sur six ans. Toute décision sur cette famille de stratégies
   doit se prendre au spread mesuré ; le catalogue ment d'un facteur 3 à 4 sur l'or.
   (Les deux tarifs partagent le même slippage, nul : seul le spread change entre eux.)
6. **Le sens de la bougie est une interprétation**, pas une citation du guide :
   nous exigeons close > open pour un achat, close < open pour une vente. Cela écarte
   **21 bougies outlier sur les 857** qui ferment près d'un extrême (2,5 %) — sans effet
   sur un verdict qui se joue sur l'absence totale de cellule STRICT. Détail :
   `FALSIFICATION.md` § Addendum A.
7. **Son drawdown publié (≈ 9,6 % du capital) n'est pas comparable à nos 43,8 R** : l'un
   est un pourcentage de capital, l'autre un multiple de risque, et le pont entre les
   deux est un dimensionnement — qui appartient à la couche risque, pas à la stratégie
   (R2). Sous son sizing live (100 €/trade sur 50 000 €), 9,6 % ≈ 48 R, du même ordre
   que nos 43,8 R : rapprochement indicatif, sur une hypothèse qu'il ne publie pas pour
   son test 11 ans. Aucun critère ne s'appuie dessus. Détail : § Addendum B.

---

## 5. Le prix des règles communes (bras secondaire, information)

Cellule live, mêmes signaux, moteur avec refroidissement 2 barres et coupe-circuit
3 pertes → 24 barres :

| Bras | trades | R total | R/trade | WR % |
|---|---:|---:|---:|---:|
| Fidèle (règle propre de S022 : pas de coupe-circuit) | 536 | **+10,0** | +0,019 | 20,9 |
| Règles communes | 414 | **−0,5** | −0,001 | 20,5 |
| **Écart (communes − fidèle)** | **−122** | **−10,6** | −0,020 | −0,4 pt |

Une seule convention de signe, ici comme dans `results.json` (`delta_vs_faithful`) :
**communes moins fidèle**, donc **−122 trades et −10,6 R**. La démonstration écrite d'avance
tient : à 21 % de réussite, trois pertes d'affilée sont la normale (0,79³ ≈ 49 %), et un
coupe-circuit à 3 pertes coupe la règle, pas le risque. **Sur cette stratégie, les
règles communes de portefeuille doivent rester au niveau du portefeuille** — si elles
devaient s'appliquer au niveau de la stratégie, elles effaceraient à elles seules le peu
qu'elle produit. Cela ne sauve rien ici : les deux bras sont à zéro.

---

## 6. Suite

- **Statut** : `manifest.yaml` passe de RESEARCH à **BACKTESTED**. *Mesuré n'est pas
  validé* — et ici le mesuré est négatif. Aucune promotion PAPER ou LIVE n'est demandée
  ni possible (R10 : décision Adrian).
- **Pas de forward scellé** : les critères ne sont pas remplis, il n'y a rien à tester
  en prospectif.
- **Ce qui reste ouvert, dans l'ordre** : (a) le bras « sans contrainte de position
  unique » (836 signaux au lieu de 536), qui est le seul écart identifié entre son
  dispositif et le nôtre ; (b) la période — mesurer 2015-2020 exigerait des barres H1
  d'or antérieures à septembre 2020, absentes du cache ; (c) le slippage, à renseigner
  avant toute décision de production sur une stratégie qui entre sur des bougies
  explosives. Chacune demande sa propre falsification écrite avant mesure. **Décision
  Adrian** sur l'ordre — et sur l'opportunité même de continuer.
- **Ce que le dossier apporte déjà** : la première reproduction de ce dépôt dont la
  fidélité au signal est vérifiable sur des chiffres publiés — et elle passe. L'outil
  de mesure et l'implémentation de la règle sont, eux, confirmés.

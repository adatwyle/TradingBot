# Verdict — s06_nil_pbd « PBD impulsion + range » (Patrick Nil)

**Moteur de référence : commit `66668d1`** (correctif gap). Tout chiffre produit
avant ce commit a été jeté et reproduit.

## VERDICT : PAS D'EDGE

Statut maintenu à `RESEARCH`. Ne pas promouvoir en PAPER.

---

## 1. Le chiffre central

**STRICT : 0 configuration sur 224.** Espérance du pur hasard : ≈ 11.

Aucune cellule ne passe les 4 fenêtres, sur aucun des 8 runs (2 instruments ×
2 modes × 2 niveaux de spread).

Agrégat hors échantillon, 112 configurations :

| Bloc | n moyen | R/trade | R/trade à coût nul | configs OOS positives |
|---|---|---|---|---|
| DAX / fade | 128 | −0,103 | −0,052 | 10/32 *(hasard 16)* |
| DAX / cassure | 197 | −0,122 | −0,080 | 2/24 *(hasard 12)* |
| WTI / fade | 156 | **+0,045** | **+0,137** | 15/32 *(hasard 16)* |
| WTI / cassure | 217 | −0,207 | −0,136 | 2/24 *(hasard 12)* |
| **Ensemble** | 170 | **−0,087** | **−0,022** | **29/112** *(hasard 56)* |

`t` médian −0,80. `t > +1,96` : 3/112 (hasard 5,6). `t < −1,96` : 11/112. La
distribution est décalée du mauvais côté.

Les 3 « significatives » sont toutes WTI/fade + filtre value area, n = 36, win
rate 72-75 % — hors de la fourchette annoncée par la source, et moins nombreuses
que ce que la grille produit par hasard. Faux positif de manuel.

**L'ablation du spread ne sauve rien : −0,022 R/trade à coût NUL.** Il n'y a pas
d'edge que des coûts masqueraient. Ni un courtier moins cher ni un timeframe
supérieur ne changent quoi que ce soit.

## 2. Falsifications déclarées avant le premier backtest — 4 sur 5 déclenchées

| | Déclenchée | Mesure |
|---|---|---|
| F1 profil de trade | **oui** | 0,03 à 0,50 trade/jour contre 3-5 annoncés |
| F2 hasard | **oui** | 0/224 STRICT contre ≈ 11 attendues |
| F3 plateau | **oui** | 29/112 configs positives contre 56 par hasard — pire qu'une pièce |
| F4 ablation spread | **oui** | négatif même à coût nul |
| F5 concentration directionnelle | non | long ET short négatifs partout — uniformément sans edge, pas un pari déguisé |

## 3. Le résultat le plus intéressant du dossier

**Son win rate et ses séries de pertes se reproduisent fidèlement — et le
système perd quand même.**

| Il annonce | Mesuré | |
|---|---|---|
| win rate 50-60 % | **52-61 %** | reproduit |
| 10 à 20 pertes consécutives | **6 à 26** | reproduit |
| 3 à 5 trades/jour | **0,03 à 0,50** | échec, facteur 10 |
| drawdown < 10 %, max 20 % | 8 à 190 R | échec |

Un win rate de 55 % avec un R:R inférieur à 1 est structurellement perdant. Ce
que sa méthode ne transmet pas, c'est **ce qui produit le R:R** : la sélection
discrétionnaire, et le fait qu'il refuse 90 % des situations que le code prend.
Le facteur 10 sur la fréquence est la mesure de cet écart.

Conséquence à assumer : ce test réfute **notre formalisation** du PBD, pas la
compétence du trader. Mais il ne sauve pas la stratégie codée, puisque le signal
est négatif même à coût nul.

## 4. Le profil de volume, son « second ingrédient »

Bâti sur `tick_volume` faute de volume réel (`real_volume = 0`).

| Bloc | sans value area | avec | Δ |
|---|---|---|---|
| DAX/fade | +0,017 | −0,224 | **−0,241** |
| DAX/cassure | −0,100 | −0,144 | −0,044 |
| WTI/cassure | −0,064 | −0,351 | −0,287 |
| WTI/fade | −0,175 | **+0,265** | +0,440 |

Dégrade dans 3 blocs sur 4, **avec un signe qui s'inverse selon l'instrument**,
et divise l'effectif par 8-10. Un filtre dont l'effet change de signe selon le
sous-jacent n'est pas un filtre, c'est du bruit. Sur tick volume, son ingrédient
ne se transpose pas — ce qui ne dit rien de ce qu'il obtient, lui, avec du vrai
volume.

## 5. R1 — ce que le gardien a réellement couvert

`precompute()` renvoie un DataFrame, délibérément : c'est la seule forme que la
couche indicateur sait inspecter.

- 4/4 coupures, 632/731/815/916 signaux identiques
- **15 colonnes inspectées**, écart max 0,000e+00
- couverture à T=50 730 : `close/high/low` 100 %, `atr` 100 %,
  **`vah`/`val`/`poc` 99,4 %** — c'est la colonne à risque, le profil glissant
- **preuve que la couche est active** : injection d'une normalisation plein
  échantillon → fuite détectée sur 50 730 points, écart 0,175

## 6. Ce qui reste transférable

- **La géométrie impulsion → range est détectable mécaniquement**, et couvre
  12-18 % des barres M15. La brique de détection est réutilisable ; c'est le
  trading de cette brique qui ne paie pas.
- **Le stop large bat systématiquement le stop serré** : +0,05 à +0,15 R/trade
  dans tous les blocs. Cohérent avec sa préférence déclarée pour « over the top ».
- **Sa discipline d'évaluation est la bonne** : « I want consistency, not the
  result » et l'arithmétique du drawdown sont exactement `docs/METHODOLOGY.md`.
  Le désaccord porte sur la méthode codable, pas sur la méthode de mesure.

## 7. Limites de ce test

Un seul régime macro (2021-2026, pas de krach) ; WTI plafonné à 4,2 ans ;
slippage et swap non modélisés alors que les positions dorment ; pas de filtre
news alors qu'il évite explicitement les annonces ; et surtout **l'écart
discrétionnaire d'un facteur 10 sur la fréquence**.

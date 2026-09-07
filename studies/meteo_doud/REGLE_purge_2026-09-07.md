# Règle de purge du corpus d'entrées Doud

**Écrite le 2026-09-07, AVANT application.** Aucune clause de ce document n'a été
ajoutée, retirée ou ajustée après avoir vu quelle observation elle élimine ni quel
résultat elle produit. C'est la condition qui rend la mesure qui suit interprétable.

**Objet** : le corpus `docs/sources/doudtrading/_entries_aligned.json` a servi de base
au résultat publié dans `VERDICT_croisement-entrees.md` (« 60 % de ses entrées suivent
un balayage contre 39 % au hasard, p = 0,047 »). Trois défauts ont été établis à la
main sur ce corpus : doublons exacts, horodatages qui datent la PAROLE et non l'ENTRÉE,
et observations non indépendantes entre elles. La présente règle définit mécaniquement
quelles observations sont retenues.

**Critère de qualité de la règle** : un tiers qui l'applique sans nous, avec le même
fichier, doit obtenir exactement le même sous-ensemble. Aucune clause ne demande de
juger « ce qu'elle voulait dire ». Là où un jugement serait nécessaire, la règle purge.

---

## 0. Champ d'application

S'applique aux 32 observations de `_entries_aligned.json`. Les critères sont appliqués
dans l'ordre P1 → P2 → P3 → P4, puis P5 en dernier. Chaque observation purgée porte le
motif du **premier** critère qui l'élimine.

Normalisation préalable du champ `ctx`, pour tous les tests textuels : minuscules,
accents supprimés (`é`→`e`, `è`→`e`, `ô`→`o`, `ç`→`c`…), apostrophes typographiques
(`’`) remplacées par `'`, espaces multiples réduits à un seul.

---

## P1 — Prix non exploitable

Purgée si l'une au moins est vraie :

| condition | motif |
|---|---|
| `aligne` est `false` | `prix-non-aligne` |
| `err_pct > 0.30` | `ecart-prix-excessif` |
| `prix < 1000` | `prix-tronque` (XAUUSD ne cote pas sous 1000 sur la période) |

`err_pct` est l'écart en pourcent entre le prix annoncé et le prix réel de la bougie
citée ; il est déjà présent dans le fichier. Le seuil 0,30 % est celui qui a servi à
poser le drapeau `aligne` dans l'extraction d'origine — il n'est pas rechoisi ici.

## P2 — Observation hors trade

L'observation ne décrit pas une position réellement prise : elle illustre, elle
suppose, elle donne un exemple. Purgée si le `ctx` normalisé contient l'un de ces
motifs (liste fermée) :

```
je suis pas dedans
je ne suis pas dedans
j'suis pas dedans
imaginons
c'est pour vous expliquer
par exemple je rentre
```

Motif : `hors-trade`.

## P3 — Récit rétrospectif

C'est le défaut central. L'horodatage d'une observation est celui de la **parole**.
Il ne vaut comme horodatage d'**entrée** que si, au moment où elle parle, la position
vient d'être ouverte. Dès qu'elle commente une position déjà en cours, déjà clôturée,
ou dont elle cite un résultat courant, l'entrée réelle est ANTÉRIEURE d'une durée
inconnue — et le biais joue mécaniquement dans le sens du résultat testé, puisqu'un
trade dont elle parle après qu'il a bougé en sa faveur a plus de chances d'être précédé
d'un balayage.

Purgée si le `ctx` normalisé contient l'un de ces motifs (liste fermée) :

**(a) position antérieure à la parole**
```
deja dedans
j'y suis
je suis deja
```

**(b) position clôturée ou réduite**
```
j'ai cloture
viens de cloturer
je cloture
j'ai coupe
je suis sortie
j'ai renforce
```

**(c) résultat courant cité (donc position ouverte avant la parole)**
```
actuellement
qui tournent
```

**Clause de conservatisme, assumée.** Un motif peut se rapporter à une position
*précédente* et non à celle dont le prix est cité. Trancher demanderait de décider à
quel trade la phrase se rapporte — c'est-à-dire un jugement, donc la fin du caractère
mécanique de la règle. La règle purge dans les deux cas. Elle est donc délibérément
sévère : elle sacrifie des observations probablement valides pour n'en garder aucune
dont l'horodatage soit douteux. Le coût est un effectif plus faible ; c'est un coût
accepté d'avance, pas un résultat.

Motif : `recit-retrospectif`.

## P4 — Fenêtre de mesure incomplète

Purgée si les barres M1 ne permettent pas d'évaluer le test : `dt` hors de la plage des
barres disponibles, ou moins de `LOOKBACK_REF + WINDOW` = 90 barres avant, ou moins de
`HORIZON` = 60 barres après. Motif : `fenetre-incomplete`.

## P5 — Doublons et non-indépendance

Appliqué **en dernier**, sur les seules survivantes de P1-P4 (si la première d'un
groupe est purgée plus haut, c'est la suivante qui devient candidate).

**P5a — doublon exact** : deux observations de même `vid` et de même `prix` (à 0,01
près) sont la même entrée citée deux fois. Motif : `doublon-exact`.

**P5b — non-indépendance** : deux observations de même `vid` dont les horodatages sont
séparés de **moins de 90 minutes**. Ce seuil n'est pas choisi, il est **déduit du test
lui-même** : pour une entrée à l'indice `i`, `sweep_at` balaie les barres `i-30` à `i`
en consultant pour chacune les 60 barres qui la précèdent. L'information consultée
couvre donc `[i-90, i]`. Deux entrées distantes de moins de 90 minutes interrogent un
historique de prix largement commun : ce ne sont pas deux observations indépendantes du
phénomène, et les compter deux fois gonfle artificiellement l'effectif comme la
significativité.

Dans chaque groupe ainsi formé, on conserve **la plus ancienne** (`offset_s` le plus
petit) et on purge les suivantes. Motif : `non-independant`.

*Limite connue, non traitée* : la fenêtre aval (`HORIZON` = 60 barres, qui sert au MFE
et au MAE) peut encore se chevaucher entre deux observations distantes de 60 à 90
minutes. Le taux de balayage — la mesure principale — n'en dépend pas. Les excursions
rapportées, oui, et elles sont donc à lire comme descriptives.

---

## Détermination du sens (hors purge)

Le sens n'est **pas** un critère de purge. Il est établi séparément, sur les
survivantes, et une observation dont le sens reste indéterminé est conservée et
marquée telle quelle. Trois valeurs seulement : `achat`, `vente`, `indetermine`.

Le champ `sens_hints` du fichier **n'est pas** une source suffisante : il est produit
par recherche de mots-clés et confond ce qu'elle fait avec ce qu'elle décrit du marché.
Le sens est établi par lecture du `ctx` et, si le `ctx` ne tranche pas, de la
transcription complète autour du timecode (`lives/<vid>.txt`, position `offset_s`).

Sont retenues comme tranchantes, et elles seules :
- une déclaration directe de sa propre position — « je suis rentrée **en vente** »,
  « je l'achète », « je suis vendeur/acheteuse sur ce niveau » ;
- une cible annoncée située **sous** le prix d'entrée (→ `vente`) ou **au-dessus**
  (→ `achat`), quand la cible est chiffrée et rattachée à cette entrée ;
- un stop annoncé situé **au-dessus** du prix d'entrée (→ `vente`) ou **en dessous**
  (→ `achat`), même condition.

Ne sont **pas** tranchantes : une description du marché (« il est très vendeur »,
« les vendeurs viennent récupérer la liquidité ») — c'est ce qu'elle voit, pas ce
qu'elle prend ; un « ça monte / ça descend » sans rattachement à sa position.

La citation qui tranche est reportée mot pour mot dans le fichier de sortie. En son
absence : `indetermine`.

---

## Seuils de conclusion — fixés ici, avant toute mesure

Soit `n` l'effectif après purge.

| `n` | verdict autorisé |
|---|---|
| `n < 10` | **EFFECTIF INSUFFISANT** — aucune p-value revendiquée. Les taux sont rapportés comme descriptifs. |
| `10 ≤ n < 20` | **CORRIGE** ou **TOMBE** seulement. **CONFIRME est interdit** : le résultat d'origine reposait déjà sur 20 observations et était déjà qualifié de mince ; on ne peut pas confirmer sur moins. |
| `n ≥ 20` | **CONFIRME**, **CORRIGE** ou **TOMBE**. |

Définition des trois issues :

- **CONFIRME** — `n ≥ 20`, taux observé > taux témoin, et p unilatérale < 0,05.
- **CORRIGE** — l'effet subsiste mais pas sous la forme publiée : taux sensiblement
  différent de 60 %, ou effet porté par un seul sens, ou significativité perdue alors
  que l'écart au témoin persiste.
- **TOMBE** — taux observé ≤ taux témoin, ou p ≥ 0,05 avec `n ≥ 20`.

**Les trois issues sont acceptables et aucune n'est recherchée.** « Effectif
insuffisant » est un verdict, pas un échec de la mesure.

---

## Ce que la règle ne corrige pas

- **Le biais de sélection reste entier.** Ce sont les entrées qu'elle annonce à voix
  haute en direct. Rien ne dit qu'elles représentent ses trades.
- **La purge ne récupère pas l'heure réelle d'entrée** des observations rétrospectives,
  elle les élimine. L'information est perdue, pas reconstruite.
- **Le nombre de vidéos sources reste petit** (13 vidéos pour 20 observations avant
  purge). La purge réduit la dépendance entre observations d'une même vidéo, elle ne
  l'annule pas : deux entrées du même jour partagent le même régime de marché.

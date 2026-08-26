# Verdict — Legacy S2 : cassure Donchian + filtre de régime (Phase 4)

Source : projet TBOT 2026, code historique interne (`s2_breakout.py`, `s2_breakout_filtered.py`)
Données : MT5 Swissquote, **H1**, 2021-07-19 → 2026-08-14 (5,1 ans)
Instruments : DAX, NASDAQ, SP500, FTSE, NIKKEI, XAUUSD, EURJPY, USDJPY
Grille : **128 configurations × 8 instruments = 1024 cellules**
Dépôt : **commit `c4d939d`** — `core/` a bougé pendant la production de ce
dossier (§ 6.10) ; tous les chiffres ci-dessous ont été **reproduits en entier**
contre cette version, et les scripts impriment désormais le commit.
R1 (causalité) : **PASSÉ**, vérifié sur **16 points de la grille**, 0 fuite,
**y compris à la couche indicateur** (§ 2.6)

---

## 1. Ce que la source affirme

Il n'y a **aucun claim numérique**, et il ne peut pas y en avoir : la source est
notre propre code. Les chiffres S2 produits à l'époque sont **inutilisables** —
le moteur de cette génération valorisait les positions résiduelles à
`closes[-1]`, la dernière barre du tableau complet. Aucun n'est cité ici.

Ce qui était affirmé est structurel, et c'est ce qui a été testé :

| # | Affirmation implicite | Testée par |
|---|---|---|
| A1 | Une cassure Donchian filtrée par ADX croissant + DI + ATR a une espérance positive | H1, cellule témoin `er_min=0,00 / fr_max=1,00` |
| A2 | Suspendre les entrées quand `ER200 < 0,11` **ou** `failed_rate200 > 0,50` améliore le résultat | H2, matrice 4×4 des seuils |
| A3 | Les seuils 0,11 / 0,50 sont un réglage valide | test de robustesse du voisinage 3×3 |

Rappel du dossier (ANALYSIS § 1) : A3 était **déjà suspect avant mesure**. Les
seuils ont été choisis par inspection visuelle des distributions, et un contrôle
antérieur avait montré que **DAX ne passait qu'au point exact**. Le critère de
robustesse a donc été écrit **avant** de voir le moindre chiffre (ANALYSIS § 6).

---

## 2. Ce que nous mesurons

### 2.0 Un artefact du moteur commun, à déclarer avant tout le reste

`core/backtest/engine.py` ne déclenche un stop que si `low <= stop <= high`.
Quand une séance **ouvre au-delà du stop**, celui-ci n'est jamais rempli et la
position court indéfiniment. Le moteur historique utilisait un test unilatéral
(`low <= stop`) et n'avait pas ce trou.

Effet mesuré, configuration sans filtre, plein échantillon :

| instrument | trades | R total | dont « fantômes » | R des fantômes | R/trade brut | R/trade sain |
|---|---|---|---|---|---|---|
| **DAX** | 103 | −188,9 | **1** | **−210,6** | −1,834 | **+0,212** |
| EURJPY | 499 | +9,2 | 7 | −7,8 | +0,018 | +0,035 |
| USDJPY | 476 | −36,6 | 7 | −7,8 | −0,077 | −0,061 |
| NASDAQ / SP500 / FTSE / NIKKEI / XAUUSD | — | — | **0** | 0,0 | inchangé | inchangé |

Le cas DAX : un SHORT ouvert le 2022-12-30 à 13 859,85, stop à 13 919,2. Le gap
du week-end suivant ouvre à 13 940,85 (plus bas de la barre : 13 939,85). Le
stop est **dans le gap**, donc jamais « contenu » dans une barre — et le DAX
n'est jamais redescendu à ce niveau. Position tenue **12 875 barres (≈ 3 ans)**,
clôturée en RESIDUAL à **−210,59 R**. Un vrai courtier aurait rempli au gap,
pour ≈ −1,35 R.

**Second contrôle, indépendant.** Plafonner la détention à 240 barres
(`max_hold_bars`, moteur commun) force la clôture de la position bloquée. Sur
DAX sans filtre : **103 → 370 trades** et **−1,834 → +0,007 R/trade**. Les deux
contrôles — exclusion des trades hors bornes, et plafond de détention —
reposent sur des mécanismes différents et donnent le même verdict : le −1,83 de
DAX n'est pas un résultat de la stratégie.

**Conséquence sur la lecture** : ce trade unique bloque aussi tous les signaux
suivants (une position à la fois), ce qui ramène DAX de ~400 trades à 103.
**Partout où DAX apparaît sans filtre, le chiffre mesure le moteur, pas la
stratégie.** Deux défauts de `core/` ont été remontés séparément (ils ne sont
pas corrigés ici : `core/` est hors de mon périmètre).

Tous les résultats ci-dessous sont donc donnés **en double** : bruts, et hors
trades fantômes.

### 2.1 Walk-forward ancré — le critère principal

| instrument | STRICT | attendu par hasard | TIER 1 | trades OOS (médiane) | moy OOS sur la grille |
|---|---|---|---|---|---|
| DAX | 1 | 6,4 | 51 | 38 | +2,76 |
| NASDAQ | **0** | 6,4 | 4 | 54 | +1,08 |
| SP500 | **0** | 6,4 | 2 | 70 | −2,40 |
| FTSE | **0** | 6,4 | 9 | 40 | −1,21 |
| NIKKEI | **0** | 6,4 | 11 | 83 | +1,63 |
| XAUUSD | **25** | 6,4 | 68 | 94 | +8,13 |
| EURJPY | **0** | 6,4 | 7 | 71 | −1,14 |
| USDJPY | **0** | 6,4 | 0 | 90 | −5,24 |
| **TOTAL** | **26** | **51,2** | | | |

**26 réussites STRICT là où le pur hasard en produirait ~51.** Comme pour S01,
la grille fait **deux fois moins bien que le hasard** — signature d'une
espérance négative, pas d'un edge noyé dans le bruit.

Et **25 des 26 viennent du seul XAUUSD** (§ 2.5). Sur les **7 autres
instruments : 1 STRICT pour ~45 attendues.**

Les effectifs sont corrects (38 à 94 trades hors échantillon, médiane sur la
grille, contre un seuil de crédibilité de 20). Le négatif est **mesuré**, pas
subi par manque de puissance.

### 2.2 LA QUESTION CENTRALE — les seuils du filtre tiennent-ils ?

Le critère, fixé avant mesure (ANALYSIS § 6) : le filtre n'est robuste que si
l'amélioration survit sur la **majorité du voisinage 3×3** autour de
(0,11 ; 0,50).

**Un piège d'agrégation a dû être écarté d'abord.** Sur DAX, la cellule témoin
(filtre désactivé) produit **ZÉRO trade hors échantillon** — le trade fantôme
bloque tout. Moyenner « les instruments où la cellule est finie » comparait donc
un témoin sur 7 instruments à un filtre sur 8, et faisait apparaître un gain de
+0,0087 R/trade avec un voisinage à 6/9. **Ce gain n'existait pas** : il venait
du jeu d'instruments, pas du filtre. Toutes les cellules sont désormais moyennées
sur **exactement les mêmes 7 instruments**, DAX écarté et déclaré.

**Matrice hors échantillon, R/trade, 7 instruments comparables :**

| er_min ↓ / fr_max → | 1,00 *(off)* | 0,45 | 0,50 | 0,55 |
|---|---|---|---|---|
| **0,00** *(off)* | **+0,0189** | +0,0110 | +0,0281 | +0,0136 |
| 0,09 | −0,0002 | −0,0280 | +0,0011 | −0,0064 |
| **0,11** | +0,0053 | −0,0309 | **−0,0080** | +0,0042 |
| 0,13 | −0,0173 | −0,1291 | −0,0909 | −0,0529 |

* témoin sans filtre : **+0,0189 R/trade**
* point historique (0,11 ; 0,50) : **−0,0080 R/trade** — soit **−0,0269**
* **voisinage 3×3 meilleur que le témoin : 0/9**

**Décompte par instrument** (plus informatif qu'une moyenne) :

| instrument | témoin | point hist. | écart | voisinage 3×3 |
|---|---|---|---|---|
| NASDAQ | +0,249 | −0,137 | **−0,386** | 0/9 |
| SP500 | −0,138 | −0,025 | +0,113 | 6/9 |
| FTSE | −0,116 | −0,060 | +0,056 | 4/9 |
| NIKKEI | +0,049 | +0,158 | +0,110 | 6/9 |
| XAUUSD | +0,311 | +0,366 | +0,054 | 5/9 |
| EURJPY | −0,050 | −0,169 | −0,119 | 2/9 |
| USDJPY | −0,172 | −0,189 | −0,017 | 2/9 |

* le point historique améliore sur **4/7** instruments — hasard : 3,5
* cellules du voisinage meilleures que leur témoin : **25/63 = 40 %** — hasard : 50 %

**Confirmation en plein échantillon** (configuration de signal fixée aux valeurs
historiques, trades des 8 instruments mis en commun) :

| | témoin (0,00 ; 1,00) | point hist. (0,11 ; 0,50) | écart | voisinage |
|---|---|---|---|---|
| brut | −0,0433 (3162 tr) | −0,0200 (1361 tr) | **+0,0233** | 6/9 |
| **hors fantômes** | **+0,0284** (3147 tr) | **−0,0152** (1355 tr) | **−0,0435** | **0/9** |

C'est le résultat le plus net du dossier. **Le gain apparent du filtre en plein
échantillon est intégralement produit par 15 trades fantômes sur 3162** — pour
l'essentiel l'unique position DAX à −210 R. Le filtre, par hasard, empêchait
d'ouvrir cette position-là. Une fois ce défaut de moteur retiré, le filtre
**dégrade** l'espérance et **aucune** des 9 cellules du voisinage ne fait mieux
que le témoin.

Par instrument, hors fantômes : le filtre historique améliore le R/trade sur
**4/8** instruments (hasard : 4), pour un effet moyen de **−0,062 R/trade**.

**Et le point le plus parlant** : la meilleure configuration hors échantillon
trouvée sur 5 des 8 instruments — dont XAUUSD, le seul à produire des STRICT —
porte `er_min=0,00` et/ou `fr_max=1,00`, c'est-à-dire **le filtre désactivé**.

### 2.3 Ablation du spread — d'où vient la perte

Mêmes signaux, même moteur, `spread_pips` réel → 0. Moyennes sur les **7
instruments non contaminés** :

| | R/trade spread réel | R/trade spread nul | instruments positifs à spread nul |
|---|---|---|---|
| sans filtre | **+0,0125** | **+0,0639** | 5/7 |
| filtre historique | **−0,0306** | **+0,0203** | 4/7 |

Lecture, et elle est différente de celle de S01 :

* **Le signal de cassure n'est pas franchement perdant** : à spread réel il est
  à +0,013 R/trade, à spread nul +0,064. Il est **indiscernable de zéro**, pas
  nettement négatif. H1 n'est ni confirmée ni franchement réfutée — elle est
  **nulle**.
* **Le péage n'est pas le coupable principal ici.** Le drag mesuré sur la
  distance de risque réelle va de **0,83 %** (NASDAQ, DAX) et **2,4-2,8 %**
  (SP500, FTSE, XAUUSD) à **5,6 %** (NIKKEI) et **8-10 %** (USDJPY, EURJPY).
  Sur les indices, le stop à 1,5 ATR H1 est large (200 à 960 pips) et le spread
  y pèse peu. Contrairement à S01 sur H1 (6,6-12,7 % de drag), on ne peut pas
  dire ici « les coûts mangent l'edge » : **il n'y a pas d'edge à manger**.
* **Le filtre est perdant même à spread nul** (+0,020 contre +0,064 pour le
  témoin). Sa nocivité n'est pas un effet de coûts.

### 2.4 Contrôle long/short — système ou pari directionnel ?

2021-2026 : hausse des indices et de l'or. Un système de cassure doit
fonctionner dans les deux sens.

| | les deux côtés positifs |
|---|---|
| 16 cas (8 instruments × 2 états du filtre) | **3/16** |

Sans filtre, le motif est massif :

| instrument | R/trade LONG | R/trade SHORT | verdict |
|---|---|---|---|
| DAX | +0,329 | −4,040 *(fantôme)* | LONG seul |
| NASDAQ | +0,190 | −0,033 | LONG seul |
| SP500 | +0,055 | −0,153 | LONG seul |
| XAUUSD | +0,341 | −0,007 | LONG seul |
| USDJPY | +0,005 | −0,185 | LONG seul |
| FTSE | −0,066 | −0,274 | les deux − |
| NIKKEI | +0,110 | +0,010 | **les deux +** |
| EURJPY | −0,034 | +0,083 | SHORT seul |

Le peu de performance produite vient du **côté long sur des marchés qui
montaient**. C'est du beta déguisé en système — exactement le motif que le
contrôle directionnel de S01 avait été conçu pour attraper. NIKKEI est la seule
exception franche, et son côté short est à +0,010 R/trade, soit zéro.

### 2.5 Le résidu : XAUUSD

Honnêteté oblige, **une poche résiste**, et elle est plus solide que celle de
S01. XAUUSD produit **25 STRICT** (contre 6,4 attendues) et 68 TIER 1, avec
94 trades hors échantillon en médiane.

Meilleure cellule hors échantillon : `adx_min 20 / donchian 40 / er_min 0,00 /
fr_max 1,00 / tp_m 4,0` — **filtre désactivé**. En plein échantillon :

| mesure | valeur |
|---|---|
| trades | **400** |
| R total | **+90,4** |
| R/trade | **+0,226** |
| win rate | 34,2 % (seuil de rentabilité ≈ 27,3 % à R:R 2,67) |
| profit factor | 1,34 |
| drawdown max | 16,3 R |
| trades fantômes | **0** |
| contrôle directionnel | LONG +0,318 (231 tr) **et** SHORT +0,100 (169 tr) |
| voisins immédiats positifs | **9/9** |

Stabilité annuelle (année d'entrée) :

| 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| −11,6 | +9,8 | +10,0 | +15,4 | **+55,9** | +10,9 |

Ce qui le retient : **62 % du résultat vient de la seule année 2025**. Mais
contrairement au résidu XAUUSD de S01 (72 % sur 2022, et négatif hors de là),
**hors 2025 il reste +34,4 R sur 304 trades, soit +0,113 R/trade**, avec une
seule année négative (2021, 29 trades). Le côté short est positif. Le voisinage
est à 9/9. Aucun trade fantôme.

**Statut : `NON CONCLUSIF`.** Ni écarté, ni retenu. Trois réserves qui
interdisent d'en faire un edge établi :

1. C'est **1 instrument sur 8**, sélectionné après coup parmi 1024 cellules.
2. XAUUSD concentre **34 %** de la contribution positive du panier, et 25 des
   26 STRICT. Le motif « le book est un pari sur un instrument » est exactement
   celui que la méthodologie du projet interdit de prendre pour un système.
3. **S01, méthode entièrement différente, avait déjà laissé XAUUSD comme unique
   résidu.** Deux règles sans rapport qui « marchent » sur le même instrument et
   nulle part ailleurs suggèrent une propriété de l'or sur 2021-2026 (tendance
   forte, spread relativement faible), pas la validité des deux règles.

### 2.6 R1 — couverture réelle de la vérification

`core/validation/causality.py` a gagné pendant cette session une **seconde
couche** qui compare les *indicateurs* entre passe complète et passe tronquée,
et pas seulement les signaux : une fuite peut perturber un indicateur sans faire
basculer de signal sur *ce* jeu de données, et en faire basculer sur un autre.

Cette couche **ne s'applique que si `precompute` renvoie un `DataFrame`** ; un
objet opaque obtient un laissez-passer silencieux. La première version de cette
stratégie renvoyait un dict — donc elle était exemptée, précisément là où sa
causalité est la plus fragile (le décalage d'agrégation de `failed_rate`).

`precompute` a donc été modifiée pour renvoyer un `DataFrame` exposant
**13 colonnes** — `atr, atr_sma, rsi, adx, pdi, ndi, er200, fr200, dh_prev,
dl_prev` plus les décisions elles-mêmes (`dec_side, dec_stop, dec_target`) —
la liste de signaux voyageant dans `.attrs`. Résultat : **0 fuite indicateur**
sur les 4 coupures, en plus des 16 points de grille au niveau signal.

C'est une garantie sensiblement plus forte que « R1 passé », et elle porte
exactement sur le composant que l'analyse avait désigné comme le point faible.

---

## 3. L'écart, et son explication

### 3.1 Pourquoi le filtre semblait fonctionner

L'écart à expliquer n'est pas entre un claim et une mesure : il est entre
**l'intuition qui a produit le filtre** et ce que le filtre fait réellement.

Le raisonnement d'origine était bon : *ne pas trader des cassures dans un marché
qui tourne en rond et où les cassures récentes échouent*. Trois choses se sont
mises en travers.

1. **Le filtre a été calibré sur un moteur qui produisait des trades
   impossibles.** Son gain apparent le plus visible (+0,0233 R/trade en plein
   échantillon) est produit par 15 trades sur 3162 dont le stop n'avait pas été
   rempli. Un filtre qui coupe 57 % des entrées a une chance sur deux d'éviter
   une position donnée ; ici, éviter LA position à −210 R suffisait à le faire
   paraître utile. **Retirer ces 15 trades inverse le signe du gain.**
2. **Les seuils ont été lus dans le bruit.** Choisis à l'œil sur des
   distributions gagnants/perdants, ils décrivent l'échantillon qui a servi à
   les tracer. Le voisinage le montre sans ambiguïté : 0/9 hors échantillon,
   0/9 en plein échantillon hors fantômes, 40 % de cellules meilleures que leur
   témoin là où le hasard en donnerait 50 %. Le pic isolé signalé sur DAX à
   l'époque n'était pas une bizarrerie : **c'était le diagnostic**.
3. **Le filtre coupe du bon en même temps que du mauvais.** Il retire 54 à 69 %
   des trades. Sur NASDAQ, il fait passer le R/trade hors échantillon de +0,249
   à −0,137. ER et failed_rate mesurent des propriétés **passées** du régime ;
   rien dans nos données n'indique qu'elles informent sur la cassure **suivante**.

### 3.2 Pourquoi le signal lui-même ne produit rien

À spread nul et hors fantômes, la cassure est à ≈ +0,06 R/trade — une pièce à
peine biaisée. La cassure Donchian, filtrée par ADX croissant et croisement DI,
**sélectionne des trades dont l'espérance brute est proche de zéro**, et
l'essentiel de ce qui reste est directionnel (§ 2.4). Deux lectures compatibles :

* La combinaison ADX croissant + DI + ATR est une description de ce que le prix
  **vient de faire**, pas un prédicteur de ce qu'il va faire — même conclusion
  que S01 sur la structure fractale, obtenue par un chemin indépendant.
* Le R:R de 2,67 avec 34 % de réussite sur XAUUSD montre que la géométrie
  SL/TP est viable **quand la tendance est là**. Le problème n'est pas la
  sortie, c'est que rien dans le déclencheur ne dit **où** la tendance sera.

---

## 4. VERDICT

# PAS D'EDGE

Avec deux sous-verdicts distincts, parce que les deux hypothèses étaient posées
séparément (ANALYSIS § 6) :

### H2 — le filtre de régime : `SUR-AJUSTEMENT CONFIRMÉ`

C'est la question centrale, et la réponse est nette :

1. **Voisinage 3×3 hors échantillon : 0/9 meilleur que le témoin.**
2. **Voisinage 3×3 en plein échantillon hors fantômes : 0/9.** Le +0,0233
   apparent du brut devient **−0,0435** une fois retirés 15 trades sur 3162
   dont le moteur n'avait pas rempli le stop.
3. **40 % des cellules du voisinage battent leur témoin**, contre 50 % attendus
   si le signe était tiré à pile ou face. Le filtre fait **moins bien que le
   hasard**.
4. La meilleure configuration hors échantillon de **5 instruments sur 8**, dont
   le seul qui produise des STRICT, a le **filtre désactivé**.

Le critère de robustesse avait été écrit avant mesure précisément pour que ce
verdict ne puisse pas être négocié après coup. Il ne l'est pas.

### H1 — le signal de cassure seul : `PAS D'EDGE` (espérance nulle, pas négative)

1. **26 STRICT contre ~51 attendues par pur hasard** sur 1024 cellules — et
   25 des 26 sur un seul instrument. **1 STRICT pour ~45 attendues sur les
   7 autres.**
2. **+0,013 R/trade à spread réel, +0,064 à spread nul** (7 instruments
   comparables) : indiscernable de zéro. Il n'y a pas d'edge brut que les coûts
   masqueraient — nuance importante par rapport à S01, où le péage H1 était le
   mécanisme de la perte.
3. **3/16 cas seulement ont les deux côtés positifs.** Le peu de performance
   vient du côté long sur des marchés haussiers : beta, pas edge.
4. Les effectifs (38 à 94 trades OOS par instrument, 3147 trades sains en plein
   échantillon) rendent ce négatif **mesuré**, pas indéterminé.

### Sous-verdict séparé — XAUUSD : `NON CONCLUSIF`

400 trades, +0,226 R/trade, les deux côtés positifs, voisinage 9/9, aucun trade
fantôme, +0,113 R/trade même hors de l'année 2025 qui fait 62 % du total. C'est
le résidu le plus sérieux produit jusqu'ici sur ce projet — mais c'est
**1 instrument sur 8 choisi après coup parmi 1024 cellules**, et **S01 avait
déjà laissé XAUUSD comme unique résidu**. Cette coïncidence appelle un test
dédié sur l'or, pas une promotion.

**Recommandation : ne pas promouvoir en PAPER.** Statut du manifest :
`RESEARCH`. Le filtre de régime `combo_011_050` doit être considéré comme
**réfuté**, et retiré de toute réutilisation future sans nouvelle validation.

---

## 5. Ce qui est transférable vers la stratégie Adrian

1. **Un filtre ne se valide jamais sur des trades que le moteur n'aurait pas dû
   produire.** C'est la leçon principale, et elle est nouvelle. Le gain du
   filtre venait de 0,5 % des trades. Protocole à adopter : **avant de juger un
   filtre, borner le P&L atteignable par la règle** (ici SL 1,5 ATR / TP 4 ATR
   → R ∈ [−1,10 ; +2,80]) **et vérifier que rien ne sort de ces bornes.** Tout
   trade hors bornes est un bug d'exécution, jamais un résultat. Coût : trois
   lignes ; ça a inversé le verdict de ce dossier.
2. **Toujours agréger sur le même jeu d'instruments d'une cellule à l'autre.**
   Moyenner « là où c'est défini » a fabriqué un gain de +0,0087 R/trade et un
   voisinage à 6/9 qui n'existaient pas, simplement parce que le témoin DAX
   avait zéro trade. Une cellule vide n'est pas une cellule neutre.
3. **Un seuil choisi à l'œil doit entrer dans la grille, jamais dans le code.**
   Exposer `er_min` et `fr_max` en paramètres avec une **valeur de
   désactivation** (0,00 / 1,00) a permis de mesurer le signal seul et le filtre
   séparément, dans un seul run. Sans le témoin intégré à la grille, on n'aurait
   jamais su lequel des deux portait quoi.
4. **L'ablation du spread ne dit pas toujours la même chose.** Sur S01 elle a
   montré « signal nul + péage = perte ». Ici elle montre « signal nul, péage
   négligeable sur indices (0,8-2,8 % du risque) ». Même diagnostic, mécanismes
   différents, donc décisions différentes : sur S01 changer de TF était une
   piste, ici non.
5. **Convergence à exploiter** : deux méthodes sans aucun rapport (structure
   fractale HTF ; cassure Donchian + ADX) ne laissent de résidu que sur
   **XAUUSD**. Ça vaut un test dédié à l'or — et ça met en garde contre le fait
   d'attribuer à une règle ce qui est une propriété de l'instrument.

Négatif également utile, et **à ne pas réessayer tel quel** :

* **Le filtre de régime ER / failed_rate n'a aucune valeur prédictive mesurable**
  sur ces 8 instruments. Il coupe 54-69 % des entrées et dégrade l'espérance de
  ≈ 0,06 R/trade. Ne pas le reprendre dans `s90_adrian_synthesis`.
* **La cassure Donchian + ADX croissant + DI ne porte pas d'information
  exploitable** en H1 sur indices et forex. Comme la structure HH/HL de S01,
  elle ne peut servir que de filtre par-dessus un signal ayant déjà un edge
  propre — jamais de déclencheur.

---

## 6. Limites de ce test

1. **Un défaut du moteur commun contamine une partie des mesures, et il est
   toujours ouvert.** Un stop franchi par un gap n'est jamais rempli
   (`lo <= stop <= hi`) — 1 trade DAX à −210 R, 7 à −7,8 R sur chacune des deux
   paires JPY. Remonté séparément ; `core/` est hors de mon périmètre. **DAX
   doit être considéré comme non mesuré sans filtre dans le walk-forward**, qui
   tourne sans plafond de détention. Les deux contrôles employés (exclusion des
   trades hors bornes atteignables ; plafond `max_hold_bars`) sont des mesures
   sur la sortie du moteur commun, pas un moteur alternatif.

   Un second défaut avait été trouvé en montant ce contrôle — `max_hold_bars`
   valorisait la sortie à la fin de tranche au lieu de la barre de plafond,
   soit un lookahead latent. Il a été **corrigé en amont pendant cette session**
   (commit `1fb18ca`, trouvé en parallèle par l'agent s04) ; le contrôle a été
   rejoué sur le moteur corrigé et figure au § 2.0.
2. **Le trailing / passage au point mort n'est pas testé** (option non-défaut de
   l'historique). Le moteur commun ne déplace pas de stop et R9 interdit d'en
   écrire un autre. Une sortie dynamique changerait le profil, mais elle
   n'ajouterait pas d'information au déclencheur — et c'est le déclencheur qui
   est à espérance nulle.
3. **Une seule formalisation.** 128 variantes autour d'**une** définition de la
   cassure et **une** définition du régime. D'autres (cassure sur clôture N
   barres, ATR-band, ADX absolu) donneraient d'autres chiffres.
4. **Un seul timeframe (H1) et un seul régime (2021-2026)** : hausse des
   indices, choc 2022, bull market de l'or. Ce n'est pas un échantillon de
   régimes. Les seuils du filtre pourraient se comporter autrement dans un
   marché durablement sans tendance — mais c'est précisément ce que le filtre
   prétendait détecter, et il ne l'a pas fait ici.
5. **Pas de portefeuille** : instrument par instrument, une position à la fois.
   La diversification changerait le profil de risque, **pas le signe de
   l'espérance par trade**, qui est ce qui est mesuré.
6. **Spread fixe** (catalogue) au lieu du spread barre par barre de
   l'historique. Plus optimiste la nuit, plus pessimiste en séance.
7. **Slippage non modélisé** — ne peut qu'aggraver, jamais améliorer.
8. **R5 (conformance backtest/live) non exécutable** :
   `core/validation/conformance.py` n'existe pas dans le dépôt. Mitigation :
   `on_bar()` appelle littéralement `precompute()` + `generate_signals()` et ne
   retient que la décision de la barre courante. Il n'existe pas deux
   implémentations pouvant diverger. Ce n'est pas une preuve, c'est une garantie
   structurelle.
9. **R1 couvre la stratégie, pas le moteur.** L'invariant de troncature teste
   `generate_signals` et, depuis cette session, la couche indicateur (§ 2.6) —
   mais dans les deux cas côté stratégie. Il ne peut structurellement pas voir
   un défaut du chemin de SORTIE du moteur : c'est ainsi que le défaut
   `max_hold_bars` a pu rester latent, et c'est pourquoi le trou de gap ne
   déclenche aucune alerte. **Un R1 « côté exécution » manque à la plateforme**,
   et c'est probablement la lacune d'outillage la plus coûteuse restante.
10. **`core/` a évolué pendant la production de ce dossier** (slippage
   paramétrable, correction `max_hold_bars`, couche indicateur de R1, mode
   walk-forward glissant). Les premiers runs enjambaient une modification du
   moteur ; **tout a été relancé en entier contre `c4d939d`** et les chiffres
   se reproduisent à l'identique — le `slippage_pips` du catalogue vaut 0 et
   `run_walk_forward` n'utilise pas `max_hold_bars`, donc le chemin emprunté
   est inchangé. Les scripts impriment désormais le commit ; **un résultat sans
   empreinte de dépôt n'est pas reproductible.**
11. **Le mode walk-forward GLISSANT n'a pas été exécuté.** `run_walk_forward`
   l'expose depuis cette session (`mode="rolling"`, entraînement à fenêtre
   fixe). Il testerait l'adaptation au régime récent plutôt que l'accumulation
   d'historique. C'est le complément naturel pour instruire le résidu XAUUSD ;
   il n'entrait pas dans le périmètre de ce dossier.

---

## 7. Fichiers produits

| Fichier | Contenu |
|---|---|
| `research/ANALYSIS.md` | Phase 1 — re-dérivation, reproductibilité, hypothèses H1/H2, critère de robustesse fixé avant mesure |
| `strategy.py` | Implémentation `StrategyModule`, R1-R10, seuils du filtre exposés en grille |
| `manifest.yaml` | Manifest, grille 128 configurations |
| `backtests/causality.txt` | Sortie R1 archivée (paramètres par défaut) |
| `backtests/run_wf.py` | Script de walk-forward et diagnostics |
| `backtests/anchored_wf.txt` | R1 × 16, artefact de gap, plein échantillon, WF × 8, synthèse, **robustesse des seuils**, voisinage, concentration |
| `backtests/run_diag.py` | Script des diagnostics complémentaires |
| `backtests/diagnostics.txt` | Ablation du spread, contrôle long/short, artefact de gap, matrice des seuils brute **et hors fantômes** |
| `research/VERDICT.md` | Ce document |

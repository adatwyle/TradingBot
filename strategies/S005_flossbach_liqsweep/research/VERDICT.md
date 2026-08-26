# VERDICT — s05_flossbach_liqsweep « liquidation sweep » (Tim Flossbach)

Source : https://www.youtube.com/watch?v=BewBId1gbqQ — transcript intégral +
19 captures d'écran, toutes lues.
Données : MT5 Swissquote, **11 instruments / 4 familles**, 2021-07-18 →
2026-08-14. H4 (8 164 barres/instrument) en principal, H1 (≈30 000) en
secondaire.
Grille : **64 cellules** déclarées, **≈34 distinctes en pratique** (§2.7).
Moteur : `core/backtest/` au commit **66668d1** (correctif « un stop sauté par
un gap doit être exécuté »). **Tous les chiffres de ce document ont été produits
contre ce commit** ; les runs antérieurs ont été jetés.
R1 : **PASSÉ**, 72 cellules × 4 coupures, avec contrôle positif prouvant que la
couche indicateur était réellement inspectée (§5).
R5 : **PASSÉ** (test local — `core/validation/conformance.py` n'existe pas, §5).

> **VERDICT : PAS D'EDGE.**
> H4 (principal) : espérance poolée **+0,0057 R/trade sur 2 343 trades**,
> IC 95 % [−0,065 ; +0,077], t = +0,16 — indistinguable de zéro.
> H1 (secondaire, effectif 5× supérieur) : **−0,1220 R/trade sur 11 557
> trades**, t = **−7,22** — négatif de façon massive, et **−0,0719 même à
> spread nul**.
> Taux de réussite **26,6 %** (H4) et **22,0 %** (H1) contre **70-80 %
> annoncés** : le claim central est réfuté d'un facteur trois.
> Walk-forward : **0 réussite STRICT sur 704 cellules** (H4) et 5 (H1) là où le
> pur hasard en produirait ~35.
>
> **Ce que ce verdict ne dit pas** : il porte sur *notre proxy* de sa détection
> de liquidité, pas sur sa méthode équipée de X-Ray, sur Bitcoin, avec sorties
> partielles. Voir §6, écrit avant les résultats.

---

## 1. Ce que la source affirme

| # | Claim | Verbatim |
|---|---|---|
| 1 | Réussite 70-80 % | « with these indicators and this liquidation view you can figure it out to 70/30, 80/20 » |
| 2 | Retournement post-balayage | « after we grab the liquidation, it will be 80% upwards a reversal. It's always the same » |
| 3 | R:R ≥ 2 | « 95% of my trades are minimum 2:1, never below » |
| 4 | Sélectivité | « I skip more than 90% of the trades I see in the chart » |
| 5 | Universalité | « everything I show here today is possible in every market » |
| 6 | Indicateur non indispensable | « I can also be profitable without this indicator » |

Le claim 2 est l'affirmation testable centrale. Le claim 6 est ce qui autorise
le test malgré l'indisponibilité de X-Ray.

---

## 2. Ce que nous mesurons

### 2.1 Espérance poolée, H4 — la mesure décisive

11 instruments × 64 cellules × 4 variantes. Chaque chiffre avec son effectif.

| variante | n trades | total R | **R/trade** | WR % | IC 95 % du WR | R/trade à **spread nul** |
|---|---|---|---|---|---|---|
| **A — la source** (balayage + creux plus haut) | **2 343** | +13,4 | **+0,0057** | **26,6** | [24,9 ; 28,5] | **+0,0323** |
| B — contrôle **sans balayage** | 7 173 | −237,0 | −0,0330 | 25,6 | [24,6 ; 26,6] | −0,0096 |
| C — contrôle **sans attendre le creux plus haut** | 2 394 | −231,2 | −0,0966 | 24,0 | [22,3 ; 25,8] | −0,0732 |
| D — **placebo** (mêmes géométries, entrée décalée au hasard) | 2 289 | −190,0 | −0,0830 | 25,0 | [23,3 ; 26,8] | −0,0596 |

### 2.2 Est-ce distinguable de zéro ? — la question qui tranche

| variante | n | R/trade | écart-type | erreur-type | IC 95 % de R/trade | t |
|---|---|---|---|---|---|---|
| A — source | 2 343 | +0,0057 | 1,75 | 0,0362 | **[−0,0653 ; +0,0767]** | **+0,16** |
| B — sans balayage | 7 173 | −0,0330 | 1,78 | 0,0210 | [−0,0743 ; +0,0082] | −1,57 |
| C — sans pullback | 2 394 | −0,0966 | 1,72 | 0,0351 | [−0,1655 ; −0,0277] | **−2,75** |
| D — placebo | 2 289 | −0,0830 | 1,68 | 0,0352 | [−0,1520 ; −0,0140] | **−2,36** |

| comparaison | écart | erreur-type | t | IC 95 % |
|---|---|---|---|---|
| A − D (source vs hasard) | **+0,0887** | 0,0505 | **+1,76** | [−0,0103 ; +0,1877] |
| A − B (apport du balayage) | +0,0387 | 0,0419 | +0,92 | [−0,0434 ; +0,1209] |

**Lecture honnête, dans les deux sens :**

- **À charge.** A est **indistinguable de zéro** (t = 0,16). Aucune des deux
  comparaisons A − D et A − B n'atteint le seuil de 95 %. Et ces erreurs-types
  sont **optimistes** : les cellules de grille partagent les mêmes barres et
  des paramètres voisins, les 2 343 trades ne sont pas indépendants, la vraie
  incertitude est plus grande que celle affichée.
- **À décharge, et il faut le dire.** L'**ordre** des quatre variantes est
  exactement celui que sa méthode prédit : la séquence complète (A) au-dessus
  du hasard (D), et les deux versions dégradées (B sans balayage, C sans
  attente du retournement) **significativement négatives** (t = −1,57, −2,75).
  Autrement dit, les deux points sur lesquels il insiste le plus — exiger le
  balayage, et surtout **ne pas entrer avant la structure de retournement**
  (« the biggest problem I did in my past years was to enter way too fast ») —
  sont précisément ceux qui font passer l'espérance de nettement négative à
  nulle. Ils ne créent pas d'edge chez nous ; ils suppriment une perte.
  C'est cohérent avec son propos, ce n'est pas une confirmation de son propos.

### 2.3 Le claim central est réfuté

Il annonce 70-80 % de réussite. Nous mesurons **26,6 %**, IC 95 %
[24,9 ; 28,5] sur H4 — 2 343 trades, donc pas un problème d'effectif — et
**22,0 %** [21,3 ; 22,8] sur H1, sur 11 557 trades.

Le R:R réellement réalisé a été mesuré sur les 1 025 trades H4 de la grille :
**médiane 2,79**, moyenne 3,25, quartiles [2,27 ; 3,73]. Le seuil de
rentabilité correspondant est donc **26,4 %**.

La coïncidence est frappante et explique tout le dossier :

| | mesuré | seuil de rentabilité | écart |
|---|---|---|---|
| H4 | **26,6 %** | 26,4 % | +0,2 pt → espérance ≈ 0 |
| H1 | **22,0 %** | 26,4 % | **−4,4 pts** → espérance nettement négative |

Sur H4 la stratégie tombe *exactement* sur son point mort ; sur H1 elle passe
dessous, et le péage du spread (§2.5) suffit à expliquer une bonne part de
l'écart entre les deux timeframes.

Il n'existe aucune lecture des données dans laquelle 70 % soit atteint. L'écart
n'est pas marginal : il est d'un facteur trois.

### 2.4 Walk-forward ancré — F2, sans ambiguïté

| | H4 | H1 |
|---|---|---|
| cellules testées | 11 × 64 = 704 | 704 |
| **réussites STRICT** | **0** | **5** |
| attendues par **pur hasard** | **35,2** | 35,2 |
| trades hors échantillon, **médiane par instrument** | **0 à 1** | 1 à 4 |
| maximum observé | 14 | 50 |

Sur H4 : **zéro** réussite là où le bruit seul en produirait trente-cinq. Sur
H1 : cinq, soit **sept fois moins que le hasard** — et sur ces cinq, quatre
viennent de WTIUSD où deux configurations sont dupliquées par le filtre inerte
(§2.7), donc **trois configurations distinctes** au total.

C'est la même signature que s01 (19 contre 45) et s91 (1 contre 10,8) :
une grille qui fait franchement **moins bien que son propre bruit** ne signale
pas un edge noyé, elle signale une espérance qui n'est pas positive.

**Les effectifs hors échantillon (0 à 4 trades médians) rendent de toute façon
le walk-forward inapte à trancher seul.** C'était prévu et écrit avant les
résultats (F5) : il skippe > 90 % des setups, la rareté est attendue. C'est
pour cela que la mesure poolée du §2.1 est la mesure décisive.

### 2.5 Ablation du spread — il n'y a rien à sauver

| | R/trade réel | R/trade à spread nul | péage |
|---|---|---|---|
| H4 | +0,0057 | +0,0323 | 0,027 R/trade |
| H1 | −0,1220 | **−0,0719** | 0,050 R/trade |

Le péage mesuré est conforme au calcul a priori (§5 de l'ANALYSIS : 0,24 à 3,72
points de win rate selon l'instrument, et deux fois plus lourd sur H1).

Le diagnostic est celui de s01, pas celui de s91 : **nul avec spread, nul sans
spread sur H4 ; négatif avec spread, encore négatif sans spread sur H1.** Il
n'y a pas un edge mangé par les coûts qu'un courtier moins cher, un timeframe
supérieur ou des cibles plus lointaines sauveraient. **Il n'y a rien à sauver.**

F1 est **déclenchée sur H1** (−0,0719 à coût nul, t ≈ −4,3) et non sur H4
(+0,032, erreur-type 0,036, donc indistinguable de zéro). C'est le timeframe
au plus gros effectif qui la déclenche.

### 2.6 Contrôle long/short — F4 déclenchée

| TF | sens | n trades | R/trade | total |
|---|---|---|---|---|
| H4 | LONG | 1 070 | −0,0541 | **−57,9 R** |
| H4 | SHORT | 1 273 | +0,0560 | **+71,2 R** |
| H1 | LONG | 5 517 | +0,0101 | **+55,9 R** |
| H1 | SHORT | 6 040 | −0,2426 | **−1 465,6 R** |

La totalité du résultat positif vient d'un seul sens. Le +13,4 R de H4 est le
résidu d'une compensation entre −57,9 et +71,2 : ce n'est pas un système, ce
sont deux paris opposés qui s'annulent presque.

**Et le côté gagnant s'inverse entre les deux timeframes** : les shorts portent
tout sur H4, les longs sur H1 — où les shorts perdent 1 465 R. Une asymétrie
directionnelle qui change de signe selon la granularité n'est pas un biais
directionnel exploitable, c'est du bruit. F4 est déclenchée, et de la pire
façon possible pour la stratégie.

### 2.7 Par instrument — dispersion massive, aucune cohérence de famille

| instrument | famille | n | R/trade | WR % | R/tr long | R/tr short |
|---|---|---|---|---|---|---|
| AUDUSD | forex | 252 | **+0,6645** | 42,9 | +0,2455 | +1,1254 |
| USDCHF | forex | 272 | **+0,4550** | 42,6 | −0,1828 | +0,9152 |
| USDCAD | forex | 155 | +0,1561 | 25,2 | +0,7154 | −0,2926 |
| DAX | indice | 102 | +0,1500 | 29,4 | −1,0013 | +0,5439 |
| XAGUSD | métal | 326 | +0,0551 | 28,2 | +0,4314 | −0,1527 |
| USDJPY | forex | 125 | −0,1105 | 24,8 | +0,4713 | −0,5982 |
| XAUUSD | métal | 214 | −0,1345 | 21,5 | +0,3122 | −0,5264 |
| EURUSD | forex | 288 | −0,1624 | 21,5 | −0,1101 | −0,2774 |
| WTIUSD | énergie | 216 | −0,2018 | 25,0 | −0,5056 | +0,6661 |
| SP500 | indice | 124 | **−0,4976** | 12,9 | −1,0034 | −0,2385 |
| NASDAQ | indice | 269 | **−0,5229** | 11,2 | −1,0011 | −0,3972 |

Trois observations, toutes défavorables :

1. **Concentration.** Les cinq instruments positifs totalisent **+348,8 R**,
   les six négatifs **−335,4 R** ; net **+13,4 R** — le total du §2.1 est le
   résidu d'une compensation presque parfaite. AUDUSD (+167,5 R) et USDCHF
   (+123,8 R) apportent à eux deux **291,3 R, soit 84 %** de toute la
   contribution positive. Un book dont cinq sixièmes du gain viennent de deux
   noms est un pari, pas un système (`METHODOLOGY.md` §6).
2. **Contre-signal sur les indices.** SP500 et NASDAQ affichent 11-13 % de
   réussite pour un seuil à ~25 % : la séquence y est **anti-prédictive**, pas
   neutre. Sur NASDAQ, les longs sont à −1,00 R/trade — c'est-à-dire que
   *chaque* long finit au stop. Il affirme l'universalité (claim 5) ; la mesure
   dit le contraire de façon massive.
3. **Aucune cohérence de famille.** Deux paires forex à +0,45/+0,66 et deux
   autres à −0,11/−0,16 ; deux métaux de signe opposé ; deux indices
   catastrophiques et un troisième positif. C'est la signature du bruit.

**Dispersion des cellules :** 400 couples (instrument × configuration) ont au
moins un trade ; **44,5 % ont un R/trade positif**. Sous pur bruit on attendrait
50 %. On est en dessous.

**Défaut de la grille, à signaler :** le filtre « shaking too much »
(`chop_max = 1,5` sur ATR(5)/ATR(50)) ne rejette que **4 entrées sur 129**
mesurées, soit 3 %. Les deux valeurs de `chop_max` produisent donc des
résultats quasi identiques et la grille de 64 cellules n'en contient
**≈34 distinctes**. L'attente par hasard corrigée tombe à ~18 réussites STRICT
au lieu de 35 — la conclusion du §2.4 est inchangée (0 et 5 observées), mais le
proxy de ce filtre est trop lâche pour tester ce qu'il décrit.

### 2.8 H1 — le timeframe qui tranche, parce qu'il a l'effectif

H1 était déclaré secondaire *avant* les résultats (§5 de l'ANALYSIS : péage
plus lourd). Il porte pourtant **cinq fois plus de trades**, et son verdict est
sans ambiguïté.

| variante | n trades | R/trade | t | WR % | R/trade à spread nul |
|---|---|---|---|---|---|
| **A — la source** | **11 557** | **−0,1220** | **−7,22** | 22,0 | **−0,0719** |
| B — sans balayage | 33 842 | −0,1040 | −10,37 | 22,6 | −0,0547 |
| C — sans pullback | 11 588 | −0,1338 | −7,97 | 21,8 | −0,0859 |
| D — placebo | 10 850 | −0,0796 | −4,44 | 23,2 | −0,0284 |

| comparaison | écart | t |
|---|---|---|
| A − D (source vs hasard) | **−0,0424** | −1,72 |
| A − B (apport du balayage) | −0,0180 | −0,91 |

Trois faits, tous à charge :

1. **A est négatif de façon décisive** : t = −7,22 sur 11 557 trades. Ce n'est
   pas un bruit autour de zéro, c'est une espérance négative mesurée.
2. **Le signe s'inverse contre le placebo.** Sur H4, A battait le hasard de
   +0,089 (t = +1,76) ; sur H1 il *perd* contre lui de −0,042 (t = −1,72).
   Deux quasi-significativités de sens opposé sur le même dispositif : c'est la
   définition du bruit. **Le +0,089 de H4 ne doit pas être pris pour un signal.**
3. **F1 est déclenchée sur H1** : −0,0719 R/trade **à spread nul**, soit
   t ≈ −4,3. À coût zéro, la stratégie perd toujours. Il n'y a donc rien qu'un
   courtier moins cher puisse sauver.

**Long/short H1 :** LONG +0,0101 (5 517 trades, +55,9 R), SHORT **−0,2426**
(6 040 trades, **−1 465,6 R**). L'asymétrie est encore plus violente qu'en H4 —
et **de sens inverse** (en H4 c'étaient les shorts qui portaient le positif).
Une stratégie dont le côté gagnant change avec le timeframe n'a pas de côté
gagnant.

**Dispersion H1 :** 530 couples (instrument × configuration) avec au moins un
trade, dont **34,2 % positifs** — très en dessous des 50 % attendus sous pur
bruit, exactement comme dans les dossiers s01 et s91.

---

## 3. Conditions de falsification — déclarées ex ante, résultat

Déclarées dans `ANALYSIS.md` §7, **avant toute ligne de `strategy.py`**.

| # | Condition déclarée | Mesure H4 | Mesure H1 | Déclenchée ? |
|---|---|---|---|---|
| **F1** | Espérance ≤ 0 à spread nul | +0,0323 (t ≈ +0,9) | **−0,0719 (t ≈ −4,3)** | **OUI sur H1** (non sur H4) |
| **F2** | STRICT ≤ attente du hasard | **0** vs 35,2 | **5** vs 35,2 | **OUI, franchement, sur les deux** |
| **F3** | Le contrôle sans balayage fait aussi bien ou mieux | A − B = +0,039 (t = 0,92) | A − B = −0,018 (t = −0,91) | **non** — écart non significatif, et de signe opposé selon le TF |
| **F4** | Un seul sens porte le résultat positif | LONG −57,9 R / SHORT **+71,2 R** | LONG **+55,9 R** / SHORT −1 465,6 R | **OUI**, et le côté gagnant **s'inverse** entre TF |
| **F5** | Effectif OOS médian < 20 trades/instrument | 0 à 1 | 1 à 4 | **OUI** |

**F1, F2, F4 et F5 sont déclenchées.** J'avais écrit que F2 signifie « la
grille n'a rien montré » et que F5 impose un verdict prudent sur le
walk-forward. Je m'y tiens.

**F3 n'est pas déclenchée, et c'est le seul point qui joue en faveur de la
source** : exiger le balayage ne dégrade jamais le résultat, et sur H4 les deux
versions amputées (B sans balayage, C sans attente du retournement) sont
significativement perdantes là où la séquence complète est neutre. Mais l'écart
A − B ne franchit le seuil de significativité sur aucun des deux timeframes et
**change de signe entre eux**. « Non réfuté » n'est pas « confirmé ».

---

## 4. Verdict

> ### PAS D'EDGE

Sur notre reproduction, la stratégie est **nulle sur son timeframe de
prédilection et négative partout ailleurs** :

- **H4** — +0,0057 R/trade sur 2 343 trades, IC 95 % [−0,065 ; +0,077],
  t = +0,16. Elle ne perd pas d'argent de façon détectable, elle n'en gagne pas
  non plus. Le seul chiffre qui la départage du hasard (+0,089 contre le
  placebo) n'atteint pas la significativité, avec une erreur-type déjà
  sous-estimée.
- **H1** — −0,1220 R/trade sur 11 557 trades, t = −7,22, et **−0,0719 même à
  spread nul**. Là, ce n'est plus de l'incertitude : c'est une perte mesurée.
- **Walk-forward** — 0 et 5 réussites STRICT sur 704 cellules, contre ~35
  attendues par pur hasard. La grille fait franchement **moins bien que son
  propre bruit**, signature déjà rencontrée sur s01 (19 contre 45) et s91
  (1 contre 10,8).

Le claim vérifiable est **réfuté sans ambiguïté** : 26,6 % (H4) et 22,0 % (H1)
de réussite contre 70-80 % annoncés, sur des effectifs qui ne laissent aucune
place au doute statistique.

Le +0,0057 de H4 ne doit pas être lu comme « presque un edge » : le même
dispositif, cinq fois plus fourni en trades, donne −0,12 un timeframe plus bas,
et le côté directionnel gagnant s'inverse entre les deux. C'est du bruit qui
change de signe, pas un edge fragile.

**Décision opérationnelle : ne pas promouvoir vers PAPER.** Une espérance nulle
avant slippage et swap est une espérance négative après. Le slippage n'est pas
modélisé (0,2-0,5 pip en FX liquide) et suffirait seul à faire passer
+0,006 R/trade en négatif.

**Sous-verdict, aussi important que le principal : NON CONCLUSIF sur la méthode
originale.** Voir §6.

---

## 5. Conformité plateforme, et deux défauts de `core/` trouvés en chemin

**R1 — PASSÉ.** 72 cellules × 4 coupures (60/70/80/90 %), 288 comparaisons,
**0 divergence de signal, 0 fuite indicateur**, sur EURUSD/H4, XAUUSD/H4 et
SP500/H1, variantes de contrôle comprises.

`precompute` renvoie délibérément un **`DataFrame`** et non un `dict` : le
gardien `_compare_precompute` **retourne silencieusement sur un objet opaque**,
et une stratégie qui renvoie un dict échappe donc au contrôle de la couche
indicateur sans le moindre message — c'est ce qui est arrivé à s91. Ici, les
**9 colonnes** (`close`, `atr`, `ema_htf`, `volratio`, `sig_side`, `sig_entry`,
`sig_stop`, `sig_target`, `sig_ncluster`) sont réellement comparées, et le
**contrôle positif** le prouve : une normalisation plein échantillon plantée
volontairement est bien détectée (écart max 1,99 × 10⁻², 5 714/5 714 points).

### Défaut n°1 de `core/` — le gardien R1 est aveugle au `shift(-k)`

**Signalé, non corrigé** (`core/` interdit d'édition). Démonstration reproductible
dans `backtests/run_causality.py`, section 1, contrôle (b) :

```
(a) normalisation plein echantillon  -> DETECTEE (ecart max 1.993e-02, 5714/5714 points)
(b) shift(-5) (valeur du futur)      -> *** NON DETECTEE ***
```

**Cause.** Sur la tranche tronquée, un `shift(-k)` produit des `NaN` sur les
`k` dernières barres — exactement là où la fuite est visible. Or
`_compare_precompute` masque les NaN (`both = np.isfinite(a) & np.isfinite(b)`,
`causality.py:206`) et ne compare jamais ces points. **La signature la plus
courante d'un look-ahead échappe donc à la couche indicateur.** Elle reste
attrapée par la couche signaux si elle fait basculer une décision — mais c'est
précisément ce que la couche indicateur était censée couvrir quand elle ne la
fait pas basculer (cf. le cas `filtfilt` documenté dans l'en-tête du module).

*Piste, à décider par une autre session :* compter comme divergence tout point
où `isfinite(a) != isfinite(b)` au lieu de l'ignorer.

### Défaut n°2 de `core/` — `core/validation/conformance.py` n'existe pas

`CLAUDE.md` Phase 3 et la checklist d'admission de `STRATEGY_RULES.md`
prescrivent `python -m core.validation.conformance --strategy <id>`.
`core/validation/` ne contient que `causality.py`, `intrabar.py` et
`selftest.py`. **La commande est inexécutable pour toute stratégie du dépôt.**

**R5 vérifié localement** (`backtests/run_conformance.py`) : 1 800 barres
rejouées une à une en mode live sur trois couples instrument/TF, 7 signaux
comparés, **0 divergence**. Vrai par construction ici — `on_bar` appelle
littéralement le chemin backtest et ne retient que la barre courante.

**R9** : moteur commun exclusivement, commit `66668d1`. **R2/R3** : aucun
sizing, `stop` toujours renseigné et c'est une vraie invalidation, pas un
plancher de catastrophe. **R4** : magic `130005` inscrit au registre.

---

## 6. Limites — écrites avant les résultats, pas après

1. **Le proxy de liquidité est la limite n°1.** Sa détection repose sur X-Ray /
   X-Ray Pro, qui agrègent les carnets d'ordres d'exchanges crypto. Cette
   donnée n'existe pas chez nous. Le substitut (amas d'extrêmes de swing non
   balayés) est **dérivé de sa propre description** — « you will see the top of
   the last structure here, and just randomly the liquidation is directly in
   these zones » — mais il perd la magnitude en dollars, la liquidité hors
   extrêmes de swing, et surtout il **suppose** que les stops d'un CFD forex
   Swissquote se concentrent aux mêmes endroits que les liquidations
   d'exchanges crypto. **Rien ici ne réfute sa méthode ; ceci réfute notre
   proxy de sa méthode.**
2. **La crypto est intestable.** BTCUSD est absent du catalogue Swissquote
   (`load_bars` retourne `None`). Or **toute sa démonstration est faite sur
   Bitcoin**, le marché où le levier est extrême et où les liquidations sont un
   phénomène mécanique, massif et réellement mesurable. Tester sa méthode sans
   la crypto, c'est la tester là où son mécanisme causal est le plus faible.
   C'est la limite la plus sérieuse de ce dossier.
3. **Trois écarts défavorables à la stratégie**, tous imposés par la
   plateforme : pas de filtre news (pas de calendrier), **pas de prises
   partielles** (25/25/reste — le moteur ne connaît que SL/TP), pas de stop au
   point mort. Un trade qu'il aurait sécurisé à +1 R avant retournement est
   chez nous un perdant plein. Notre 26,6 % est donc un **plancher** de son
   taux de réussite réel, pas une estimation non biaisée.
4. **Le « feeling for the chart »** — il y revient six fois — n'est pas
   modélisé et ne peut pas l'être. Il dit lui-même que ce n'est « pas trois
   règles ». Nous avons testé les trois règles.
5. **Le filtre « shaking too much » est un proxy trop lâche** : 3 % de rejets
   seulement (§2.7). Sa version à lui rejette beaucoup plus.
6. **Un seul régime macro** (2021-2026), aucun krach dans l'échantillon.
   Faiblesse méthodologique n°1 connue du projet.
7. **Erreurs-types optimistes** : les cellules de grille se recouvrent, les
   trades ne sont pas indépendants.
8. **Slippage et swap non modélisés** — les chiffres sont optimistes d'un
   montant inconnu, et une espérance nulle n'y survit pas.

---

## 7. Ce qui est transférable, malgré le verdict

Trois résultats méritent d'être repris ailleurs, y compris dans la stratégie
d'Adrian.

1. **« Attendre la structure de retournement » est le composant qui vaut le
   plus cher — mais l'effet ne se réplique pas.** Sur H4, entrer sur la cassure
   sans attendre le creux plus haut coûte **−0,102 R/trade** (C = −0,0966
   contre A = +0,0057), t = **+2,03** pour l'écart A − C : le seul écart
   significatif à 95 % de toute l'étude. **Sur H1 le même écart tombe à
   +0,0118, t = 0,50 — non significatif.** Sa correction autobiographique
   (« the biggest problem I did in my past years was to enter way too fast »)
   reçoit donc un appui partiel et non répliqué sur nos données. À retenir
   comme piste, pas comme acquis : sur un déclencheur de retournement, exiger
   la confirmation structurelle plutôt que l'extrême — et **vérifier la
   réplication sur au moins deux timeframes** avant d'y croire, ce que ce
   dossier montre justement être indispensable.
2. **Le placebo est un contrôle qu'il faut systématiser.** Rejouer les mêmes
   géométries de stop/cible à des dates tirées au hasard donne la ligne de base
   du hasard *pour cette géométrie précise* — bien plus informatif que le
   « 50 % » théorique. Ici il vaut −0,083 (H4) et −0,080 (H1) R/trade : la
   géométrie elle-même — stop structurel serré, cible lointaine à R:R ≥ 2,
   sortie tout-ou-rien — est **structurellement perdante après coûts**,
   indépendamment de tout signal. Avertissement direct pour toute stratégie à
   R:R élevé et sortie unique : le seuil à battre n'est pas zéro, c'est le
   placebo. **Ce contrôle mériterait d'être remonté dans `core/` et rendu
   obligatoire au même titre que l'ablation du spread.**
3. **Une contrainte R:R ≥ 2 appliquée mécaniquement détruit l'échantillon.**
   Avec la lecture littérale (cible = amas le plus proche), la règle « si
   R:R < 2 je ne prends pas » élimine 90 à 100 % des setups et laisse 0 à 5
   trades en cinq ans. Chez lui la règle fonctionne parce qu'il choisit la
   cible « very big range » avec des sorties partielles en chemin. **Une règle
   de R:R minimum sans gestion partielle n'est pas la même règle.**

---

## 8. Fichiers

| Fichier | Contenu |
|---|---|
| `research/ANALYSIS.md` | Phase 1 — méthode reformulée, tableau de reproductibilité, économie a priori, **F1 à F5 figées avant le code** |
| `backtests/causality.txt` | R1 — 288 comparaisons + contrôles positifs + défaut n°1 de `core/` |
| `backtests/conformance.txt` | R5 local + constat d'absence de `core/validation/conformance.py` |
| `backtests/pooled_study_H4.txt` | **La mesure décisive** — 4 variantes, tests de significativité, par instrument, long/short, dispersion |
| `backtests/pooled_study_H1.txt` | idem, timeframe secondaire |
| `backtests/anchored_wf_H4.txt` | Walk-forward ancré, 11 × 64 cellules |
| `backtests/anchored_wf_H1.txt` | idem H1 |
| `backtests/run_*.py` | Scripts reproductibles |

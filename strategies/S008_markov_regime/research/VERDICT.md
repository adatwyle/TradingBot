# Verdict — Markov Regime Switching (« hedge fund method »)

**Commit** : `434ced1` · **Date** : 2026-08-16
**Contrat** : ALLOCATION (`AllocationModule`) · **Magic** : 130008
**R1** : PASSÉ (`backtests/causality.txt`) · **R5** : PASSÉ (`backtests/conformance.txt`)
**Falsification déclarée avant mesure** : `research/FALSIFICATION.md`

---

## 1. Ce que la source affirme

| Affirmation | Précision fournie |
|---|---|
| S&P 500 profitable sur ~30 ans après correction causale | aucune : ni date, ni capital, ni référence |
| Bitcoin « pas 23× mais près de 60× » | aucune période, aucune référence |
| Persistance élevée = « justification mathématique du trend is your friend » | énoncé, non chiffré |
| Corriger le recouvrement « réduit tous les chiffres » | énoncé, non chiffré |
| Corriger la fuite **améliore** les résultats | énoncé, non chiffré |

**Aucune de ces affirmations n'est vérifiable.** Il ne compare jamais à une
référence — c'est l'angle mort central de la source, et notre moteur y répond
nativement.

---

## 2. Ce que nous mesurons

### 2.1 Plein échantillon, variante causale la plus favorable, par instrument

Toutes les lignes : contrat allocation, `size_mode="binary"`, coûts nominaux
mesurés sur MT5, portage exclu des deux côtés.

| Instrument | Barres | Stratégie CAGR | Sharpe | DD max | **B&H CAGR** | **B&H Sharpe** | Bat le B&H ? |
|---|---|---|---|---|---|---|---|
| SP500 | 2 774 | +3,22 % | 0,34 | −29,4 % | **+14,08 %** | **0,84** | non |
| NASDAQ | 2 774 | +12,03 % | 0,67 | −35,7 % | **+20,11 %** | **0,93** | non |
| BTCUSD | 4 376 | +13,94 % | 0,51 | −89,2 % | **+46,74 %** | **0,91** | non |
| XAUUSD | 3 554 | +5,30 % | 0,63 | −26,6 % | **+7,32 %** | 0,51 | non (CAGR) |
| DAX | 2 692 | +7,38 % | 0,57 | −38,3 % | **+9,50 %** | 0,57 | non |
| ETHUSD | 2 840 | −2,42 % | 0,22 | −84,8 % | **+33,56 %** | **0,76** | non |

**0 victoire sur 6 instruments.** Aucune n'est marginale : l'écart va de 2,1 à
36 points de CAGR annualisé.

### 2.2 Portefeuille des trois instruments qu'il cite (index commun, 2 773 barres)

```
                                     CAGR   Sharpe      DD max        total
  STRATÉGIE                       16,48 %     0,79    -45,47 %      402,9 %
  B&H BTCUSD                      59,60 %     1,04    -83,22 %    14013,8 %
  B&H NASDAQ                      20,11 %     0,93    -35,71 %      595,7 %
  B&H SP500                       14,08 %     0,84    -35,18 %      303,5 %
  VERDICT MOTEUR : NE BAT PAS « B&H BTCUSD » (Sharpe 1,04 contre 0,79)
```

**Rendement annualisé par jour détenu** — la mesure qui isole la qualité du
timing du temps passé investi :

| Jambe | Stratégie | Buy & hold du même actif |
|---|---|---|
| BTCUSD | +18,21 % | **+59,60 %** |
| NASDAQ | +6,42 % | **+20,11 %** |
| SP500 | +4,55 % | **+14,08 %** |

**Chaque jambe rapporte deux à trois fois moins par jour détenu que la simple
détention de l'actif.** Ce n'est pas un problème d'exposition insuffisante : les
jours où la stratégie est investie sont, en moyenne, moins bons que les jours
ordinaires. Le timing **détruit** de la valeur, il n'en ajoute pas.

### 2.3 Le « 60× » confronté à sa référence manquante

Buy & hold de Bitcoin, données Swissquote :

- 2014-07-17 → 2026-08-16 (12,1 ans) : **+10 185 %, soit 102,9×**
- 2016-01-12 → 2026-08-14 (index commun) : **+14 014 %, soit 141,1×**

Notre meilleure variante causale sur BTC seul : **+384 % (4,8×)** en step=20
binaire long-only, **+968 % (10,7×)** en step=1.

Un « 60× » sur une période comparable serait donc une **sous-performance de
l'ordre de 40 à 80 % du résultat**, présentée comme un succès. C'est très
exactement le piège que le contrat d'allocation rend impossible chez nous.

### 2.4 Effectifs — toujours à côté des chiffres

| Instrument | Transitions recouvrantes | **Transitions NON recouvrantes** (la matrice réellement utilisée) |
|---|---|---|
| SP500 | 2 753 | **137** |
| NASDAQ | 2 753 | **137** |
| BTCUSD | 4 354 | **217** |

Une matrice 3×3 estimée sur 137 observations, dont 11 seulement partent de
l'état *bear* sur SP500 : les barres d'erreur sont énormes et aucune conclusion
fine n'est défendable. C'est une limite structurelle de la méthode, pas de notre
reproduction — la correction n°1 qu'il propose lui-même divise l'information
par 20.

### 2.5 Ablation du spread et portage

| Instrument | CAGR coût nul | CAGR nominal | CAGR ×2 | Portage annuel non modélisé |
|---|---|---|---|---|
| SP500 | +0,77 % | +0,55 % | +0,34 % | ~3,2 %/an (investi 50 %) |
| NASDAQ | +12,12 % | +12,03 % | +11,95 % | ~4,2 %/an (investi 67 %) |
| BTCUSD | **+24,94 %** | **+8,04 %** | **−7,19 %** | ~12,4 %/an (investi 72 %) |

Diagnostic `docs/METHODOLOGY.md` §5.1, à lire séparément par instrument :

- **Indices** : négatif ou quasi nul dans les deux cas → **il n'y a pas d'edge**,
  les coûts n'y sont pour rien.
- **BTCUSD** : positif à coût nul, positif mais faible au nominal, négatif au
  double. Et le portage CFD (~12,4 %/an à ce taux d'exposition) **suffit à lui
  seul à faire passer la version nominale en négatif**. Le buy & hold paie ce
  portage 100 % du temps (17,16 %/an) et ressort quand même à ~+29,6 %/an net.

### 2.6 Contrôle long / short

| Instrument | Jambe longue (par jour détenu) | Jambe courte | Temps en short |
|---|---|---|---|
| SP500 | +9,36 % | **−18,73 %** | 12,6 % |
| NASDAQ | +18,73 % | — | **0,0 %** |
| BTCUSD | +50,54 % | **−67,99 %** | 4,6 % |

La jambe courte détruit partout où elle existe, et sur NASDAQ elle n'est
**jamais** activée — le signal markovien y est positif dans les trois états. Le
résultat entier repose sur la jambe longue, sur un échantillon massivement
haussier. C'est le motif exact de `docs/METHODOLOGY.md` §5.2.

### 2.7 Walk-forward ancré (fenêtres de `core.backtest.anchored_wf`)

36 configurations → **1,8 « réussite » attendue par pur hasard** au seuil 5 %.

| Instrument | Fenêtres OOS positives | Battant le B&H | OOS moyen | F3 |
|---|---|---|---|---|
| SP500 | 1/4 | **0/4** | +2,60 % | **déclenchée** |
| NASDAQ | 2/4 | 1/4 | +6,12 % | **déclenchée** |
| BTCUSD | 3/4 | 2/4 | +12,22 % | non déclenchée |

Deux fenêtres SP500 et deux fenêtres NASDAQ rendent exactement **0,00 %** : la
configuration retenue sur le train laisse le portefeuille en cash sur toute la
tranche de test. Un « OOS non négatif » obtenu en ne tradant pas n'est pas un
résultat, et il est compté comme tel ici.

BTC est le seul cas non falsifié par F3 — avec 2 fenêtres sur 4 seulement
au-dessus du buy & hold, des drawdowns OOS de 24 à 61 %, et un OOS moyen
(+12,22 %) très inférieur au B&H des mêmes tranches.

---

## 3. L'écart avec la source, et son explication

| Écart | Explication mesurée |
|---|---|
| Il annonce un S&P 500 « profitable » ; nous mesurons +3,2 %/an contre +14,1 % pour le B&H | il ne compare à **rien**. « Profitable » et « bat la détention » sont deux affirmations différentes ; seule la seconde a un sens décisionnel |
| Il annonce BTC ~60× ; le B&H fait 103× à 141× | idem — **absence de référence** |
| Il dit que corriger la fuite **améliore** ; nous mesurons l'inverse sur **5 instruments sur 6** — la version fuitée gagne de +0,8 pt (DAX), +2,7 (NASDAQ), +6,0 (SP500), +8,6 (XAUUSD) et +26,4 (BTCUSD) de CAGR. Seule exception : ETHUSD (−9,4 pt), où les deux versions perdent lourdement de toute façon | soit sa « v1 » contenait un autre défaut que celui qu'il décrit, soit les deux chiffres ne portent pas sur la même chose. Non résoluble depuis la vidéo |
| Il présente la persistance comme la justification du suivi de tendance | après **sa propre correction n°1**, la persistance des indices tombe au niveau de la fréquence inconditionnelle : il ne reste rien à justifier |
| Il décrit la prévision à n pas comme `0,6ⁿ` | opération fausse. Appliquée telle quelle, elle **annule toute position** dès n = 2 (mesuré : 0 % d'exposition) |
| Il ne dit pas que le HMM doit être glissant | mesuré : la correction causale de la matrice est bien annulable par la porte de derrière (+5,46 pt de CAGR sur BTC pour la version fuitée) |

---

## 4. Conditions de falsification — lesquelles ont été déclenchées

| # | Condition (déclarée avant mesure) | Résultat |
|---|---|---|
| **F1** | Concordance ≥ 95 % avec le momentum naïf **et** \|ΔCAGR\| < 1 pt | **NON déclenchée** — 24 à 49 % de concordance seulement. L'appareil produit bien d'autres positions que le momentum. Voir la nuance ci-dessous : ce n'est pas à son avantage |
| **F2** | Sharpe **et** rendement total inférieurs au meilleur benchmark | **DÉCLENCHÉE sur 6 instruments / 6**, et sur le portefeuille |
| **F3** | < 3 fenêtres OOS positives **ou** OOS moyen négatif | **DÉCLENCHÉE sur SP500 et NASDAQ**, non déclenchée sur BTC |
| **F4** | > 85 % du résultat d'une seule ligne, ou jambe courte destructrice | **DÉCLENCHÉE** — la jambe courte détruit partout, NASDAQ n'en ouvre jamais, tout repose sur le long dans un marché haussier |
| **F5** | Rentable seulement avec la fuite | **DÉCLENCHÉE sur SP500** (+0,55 % causal contre +6,56 % fuité au niveau de rentabilité) ; sur les autres la fuite ajoute massivement sans changer le signe |

**Quatre conditions sur cinq déclenchées.**

**La nuance sur F1, et elle est importante.** L'appareil n'est pas de la
décoration : il produit réellement d'autres positions que le momentum 20 j.
Mais l'examen du signe du signal état par état
(`backtests/probe_apparatus.txt` Q2) montre que ce n'est pas pour la raison
qu'on espérerait :

| Instrument | État *bear* | État *sideways* | État *bull* |
|---|---|---|---|
| SP500 | **+106 / −0** | +905 / −578 | **+233 / −0** |
| NASDAQ | **+281 / −0** | +1 209 / −17 | **+470 / −0** |
| BTCUSD | +557 / −289 | +1 016 / −119 | **+1 523 / −0** |

Sur les indices, la matrice glissante **n'inverse jamais** la direction attribuée
à un état extrême : elle n'en change que l'amplitude. La différence avec le
momentum vient donc de ce que la correction n°1 a **retourné la table** (l'état
*bear* pointe long sur les indices, puisqu'à 20 jours d'horizon la destination la
plus probable est plus haussière que baissière), pas de ce que la matrice
apprendrait quelque chose du temps.

BTCUSD est le seul cas où la matrice glissante inverse réellement des
directions (bear : 557 fois long contre 289 fois short). C'est donc le seul
instrument où l'appareil est authentiquement adaptatif — et il y perd quand même
contre le buy & hold par 33 points de CAGR. L'adaptativité, quand elle existe,
ne rapporte rien ici.

Cas limite qui résume le tout : à `horizon = 5` avec `P^n`, la matrice est figée
sur sa distribution stationnaire dès n = 3. La stratégie émet alors **1 seul
rebalancement en 12 ans** et reste investie 82 % du temps — c'est un buy & hold
avec un retard à l'allumage, et ce sont ses meilleurs chiffres bruts
(+46,05 % CAGR sur BTC, contre +46,74 % pour le buy & hold). **La meilleure
version de cette stratégie est celle qui lui ressemble le moins.**

---

## 5. VERDICT

> ## PAS D'EDGE
>
> La méthode est fidèlement reproductible, ses deux premières corrections sont
> statistiquement justes, sa troisième est fausse — et le tout ne bat aucune
> référence sur aucun des six instruments testés, sur 10 à 12 ans d'historique
> couvrant 2018, 2020 et 2022.

Ce n'est pas un verdict de reproduction ratée : R1 et R5 passent, le mécanisme
est intégralement implémenté, les deux modes et les deux dimensionnements sont
mesurés, et l'appareil se comporte exactement comme la théorie le prédit. Il n'y
a simplement **rien à extraire** :

1. Retirer le recouvrement — correction que l'auteur revendique lui-même —
   **détruit la persistance qui justifiait la stratégie**. Sur SP500, la
   persistance de l'état *bull* passe de 72,8 % à 15,0 %, alors que *bull*
   représente 11,6 % des barres : il ne reste **aucune** information
   conditionnelle. Le concept n°5 de la vidéo ne survit pas à la correction que
   la vidéo applique au concept n°5.
2. Ce qui subsiste sur les indices est une table `état → direction` estimée sur
   **137 observations**, dont la matrice glissante ne modifie que l'amplitude.
   Sur BTC la table bouge réellement, et perd quand même de 33 points de CAGR
   contre le buy & hold.
3. Poussée à `P^n` avec n ≥ 3, la stratégie **converge littéralement vers un buy
   & hold en retard** : 1 rebalancement sur 12 ans, performance juste sous celle
   du buy & hold. C'est la formulation la plus honnête du résultat.

---

## 6. Ce qui est transférable au projet, même si le tout échoue

1. **L'ampleur chiffrée du biais de fuite sur un paramètre glissant** : estimer
   une statistique sur tout l'échantillon plutôt que sur le passé vaut **+0,8 à
   +26,4 points de CAGR** (5 instruments sur 6), et change le **signe** de la
   position sur **42,9 % des barres** (SP500), 27,3 % (BTCUSD), 9,0 % (NASDAQ).
   C'est le chiffre à opposer à toute stratégie du projet qui calibre un
   paramètre « une fois pour toutes ».
2. **Le test du recouvrement est réutilisable tel quel.** Toute statistique
   mesurée sur fenêtres glissantes (autocorrélation, persistance de régime, taux
   de succès conditionnel) doit être re-mesurée sur grille non recouvrante avant
   d'être crue. Écart mesuré ici : **−41 à −68 points** de persistance.
3. **L'ancrage de la grille d'échantillonnage sur la barre 0** est une exigence
   R1 non évidente : ancrée sur la dernière barre, la même grille produit une
   fuite qui ne laisse **aucun NaN** et passe donc sous le radar de la version
   naïve du gardien. La contre-épreuve de `validate_r1.py` couche 4 le démontre.
4. **La table `leg_contribution` du moteur d'allocation est le meilleur
   diagnostic disponible** pour un filtre de régime : « rendement par jour
   détenu contre buy & hold du même actif » répond en une ligne à la question
   « ce filtre garde-t-il les bons jours ? ». Ici : non, sur les six.
5. **Un défaut de données réel** : barre à zéro sur `#BTCUSD` D1 au 2015-01-07,
   qui rend le B&H de Bitcoin égal à −100 % en silence. À corriger dans
   `core/data/` (non fait ici : interdiction).
6. **Trois lacunes de `core/` confirmées** : (a) `core/validation/causality.py`
   et (b) `core/validation/conformance.py` sont inapplicables au contrat
   d'allocation, contrairement à ce qu'affirme le docstring de
   `core/contracts/allocation.py` (« causality.py sait tester les deux
   contrats ») — déjà signalées par s07, non traitées depuis ; (c)
   `core/contracts/MAGIC_REGISTRY.md` annonce une vérification au démarrage par
   `core/validation/registry.py` — **ce module n'existe pas**
   (`No module named core.validation.registry`). Les collisions de magic number
   ne sont donc vérifiées par personne.

---

## 7. Limites de notre propre test

1. **Indices en CFD, pas en ETF** : pas de dividendes. Le B&H de référence est
   sous-estimé — donc le verdict est **conservateur**, l'écart réel est plus
   large.
2. **Portage non intégré au moteur** — chiffré à part. Son inclusion
   dégraderait la stratégie (surtout BTC) plus que les benchmarks relatifs, mais
   l'ordre du verdict ne change pas.
3. **HMM partiel** : gaussien univarié, réajustement tous les 60 jours,
   étiquetage par filtre en avant. L'écart avec un décodage Viterbi relancé
   chaque jour n'a pas été mesuré (coût quadratique). La branche HMM est donc
   **non concluante en toute rigueur** — mais elle n'a pas besoin de l'être : le
   verdict repose sur la branche à seuils, entièrement mesurée.
4. **« Enhanced states »** de la démo vidéo non reproduits — non spécifiés dans
   la source. S'ils contenaient l'essentiel de l'edge, nous ne l'aurions pas vu.
   L'auteur ne les décrit nulle part ; ce n'est pas une omission de notre part.
5. **Grille de 36 configurations** : petite par choix. Une grille plus large
   aurait trouvé de meilleurs chiffres OOS — et de meilleurs faux positifs.
6. **Coût de bord des shorts mis à zéro** : avantage donné aux shorts. Ils
   perdent quand même.
7. **Folds emboîtés** : les quatre fenêtres OOS ne sont pas indépendantes
   (`docs/METHODOLOGY.md` §9). n effectif < 3.

---

## 8. Recommandation

**Ne pas promouvoir. Statut maintenu à `RESEARCH`.** Aucune variante ne remplit
le critère n°1 de `docs/METHODOLOGY.md` (battre l'effort zéro), sur aucun
instrument, dans aucune fenêtre hors échantillon.

La seule suite qui aurait un intérêt scientifique — et non commercial — serait
d'utiliser le mécanisme comme **outil de mesure** plutôt que comme stratégie :
la matrice non recouvrante est un bon estimateur de persistance de régime, et sa
chute par rapport à la version recouvrante est un diagnostic réutilisable pour
juger toute stratégie de suivi de tendance du projet. C'est ce qui est retenu au
point 2 de la section 6.

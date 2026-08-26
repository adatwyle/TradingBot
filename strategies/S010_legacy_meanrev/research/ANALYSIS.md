# Analyse — Legacy S1 : divergence MACD + S/R (Phase 1)

**Source :** projet TBOT 2026, code historique
`BacktestEngine_prototype/backtest_engine/backtest_engine/grid_search_v12_multi_variant.py`
+ `indicators.py` (`detect_macd_divergence`, `detect_support_resistance`,
`add_adx`, `add_rsi`, `add_atr`, `add_macd`)

**Auteur / trader :** TBOT interne (Adrian + sessions Claude antérieures)

---

## 0. Avertissement liminaire — pourquoi cette ré-implémentation existe

Cette stratégie n'est pas une source externe à découvrir : c'est **notre propre
code**, tourné pendant des mois. Sa crédibilité n'est donc pas une question de
marketing, c'est une question d'**intégrité du moteur qui a produit ses
chiffres**.

Le 15 août 2026, un lookahead a été trouvé dans `fast_bt_multi` : la clôture des
positions résiduelles utilisait `closes[-1]` (dernière barre du tableau
**complet**) alors que la boucle respectait `n = end_idx`. Chaque tranche
d'entraînement d'un walk-forward valorisait donc son trade encore ouvert à un
prix futur.

**Conséquence : tous les chiffres S1 publiés avant cette date sont non
citables.** Le tableau ci-dessous en fixe la trace, uniquement pour pouvoir
mesurer ensuite de combien la fuite gonflait le résultat.

### Référence contaminée — `results/anchored_wf_results.txt`, 2026-04-10

C'est l'**analogue exact** de ce que je vais produire : walk-forward ancré,
4 fenêtres (60/70, 70/80, 80/90, 90/100), critère STRICT = train profitable ET
OOS positif sur les 4 fenêtres, 210 configurations, 17 instruments.

| Instrument | configs STRICT / 210 | meilleure moy OOS (CHF/fenêtre) |
|---|---|---|
| SP500 | **7** | **+244** |
| FTSE | **7** | **+108** |
| AUDCHF | **3** | **+98** (puis +76, +71) |
| NIKKEI | **2** | **+162** |
| AUDCAD, XAUUSD, USDJPY, EURAUD, CHFJPY, WTIUSD, CADCHF, EURCAD, EURJPY, BTCUSD, NASDAQ, XAGUSD, DAX | 0 | — |
| **TOTAL** | **19 / 3 570 cellules** | portefeuille annoncé **+612 CHF/fenêtre** |

Repris tel quel dans `SPEC.md` §7.1 comme « PORTFOLIO ROBUSTE (S1
mean-reversion) ».

**Note sur les chiffres cités dans mon mandat** (« AUDCHF +72, EURUSD +49 ») :
je n'ai pas retrouvé ce couple exact dans les artefacts. AUDCHF apparaît à
+98 / +76 / **+71** CHF de moyenne OOS dans le run ancré ; EURUSD n'était pas
dans l'univers de ce run-là (il figure dans `config_walkforward_v4.txt` à
+142 CHF de PnL train et **+72** CHF de PnL OOS fold A). Je compare donc à ce
qui est **écrit dans les fichiers**, pas à la citation de mémoire.

**Amplitude attendue de la fuite, honnêtement :** elle est **bornée** — au plus
un trade résiduel par variante et par évaluation. Sur 51 à 75 trades de tranche,
un seul trade mal valorisé ne peut pas produire +395 CHF à lui seul. Il faut
donc s'attendre à un biais **directionnel mais modeste** sur le PnL, et
potentiellement bien plus grand sur la **sélection** (le passage au critère
STRICT se joue parfois à quelques CHF, et la fuite pousse toujours dans le même
sens). C'est cette seconde voie — contamination de la *sélection* plutôt que du
*chiffre* — que la comparaison finale devra regarder.

---

## 1. La méthode reformulée, dans mes mots

S1 est une stratégie de **retour à la moyenne sur H1**. Postulat :

> Quand le prix pousse à un nouvel extrême **sans que l'élan (MACD) suive**, que
> l'excès est confirmé par un RSI en zone extrême, que le prix touche un niveau
> historique (support/résistance), et que le marché **n'est pas en tendance
> forte** (ADX bas) — alors la poussée est un excès, et le prix revient.

Séquence, barre par barre, en H1 :

1. **Filtre de régime.** `ADX(14) <= adx_max`. C'est le filtre le plus
   structurant : il interdit d'entrer à contre-courant d'une tendance établie.
   Une stratégie de retour à la moyenne meurt dans une tendance.
2. **Déclencheur.** Deux familles alternatives, jamais combinées dans la même
   instance :
   - **divergence MACD** entre le prix et l'histogramme MACD (creux de prix plus
     bas ↔ creux d'histogramme plus haut = divergence haussière, et symétrique) ;
   - **inflexion de l'histogramme MACD** : l'histogramme, négatif, cesse de
     baisser et remonte (`h[i] > h[i-1] && h[i-1] <= h[i-2] && h[i] < 0`).
     Beaucoup plus fréquent, aucune divergence exigée.
3. **Confirmation d'excès.** `RSI(14) < rsi_os` pour un achat, `> rsi_ob` pour
   une vente.
4. **Confirmation de lieu.** Il doit exister un support (resp. résistance) issu
   des 50 dernières barres tel que `|close - niveau| <= close × sr_tol`.
   Variante `NO_SR` : ce test est remplacé par un test de direction
   (`-DI > +DI` pour acheter — on achète quand la pression vendeuse domine encore).
5. **Ordre.** Entrée au close. `SL = sl_atr × ATR(14)`,
   `TP = tp_atr × ATR(14)`. Set & forget.
6. **Gestion.** Cooldown de 2 barres après une sortie ; disjoncteur après
   3 pertes consécutives (24 barres d'arrêt) ; une position à la fois par
   variante.

### Les « variantes » historiques — ce qu'elles sont réellement

Le code historique en expose six. À la lecture de `check_signal`, **il n'y a que
trois chemins de code distincts** :

| Variante historique | Chemin de code | Ce qui la distingue vraiment |
|---|---|---|
| `STRICT` | divergence + RSI + S/R | rsi 35/65, sr_tol 0.005 |
| `WIDE_TOL` | **le même** | sr_tol plus large |
| `RSI40` | **le même** | rsi 38/62 ou 40/60 |
| `NO_SR` | divergence + RSI + ±DI | remplace S/R par la direction DI |
| `HI_cons` | inflexion + RSI + S/R | rsi/tol « conservateurs » |
| `HI_aggr` | **le même** | rsi/tol « agressifs » |

`STRICT`, `WIDE_TOL` et `RSI40` sont **littéralement la même branche `if`** ;
seuls `rsi_os`, `rsi_ob` et `sr_tol` changent. Idem pour `HI_cons` / `HI_aggr`.
Les traiter comme six « stratégies » différentes et compter six chances de
passer un test est, en soi, une **inflation du taux de faux positifs** : cela
multiplie les cellules de grille sans multiplier les hypothèses.

Je porte donc **trois variantes** — `DIV_SR`, `DIV_NOSR`, `HIST_INF` — et je
mets les seuils RSI dans la grille, là où ils appartiennent. C'est la
reformulation la plus fidèle possible, pas un appauvrissement.

---

## 2. Décomposition en composants

| # | Composant | Rôle | Paramètres |
|---|---|---|---|
| C1 | ADX(14) ≤ seuil | filtre de régime (anti-tendance) | `adx_max` |
| C2 | Divergence MACD hist ↔ prix | déclencheur famille A | fenêtre 60, lookback 5, écart 5-50 barres |
| C3 | Inflexion histogramme MACD | déclencheur famille B | aucun |
| C4 | RSI(14) en zone extrême | confirmation d'excès | `rsi_os`, `rsi_ob` |
| C5 | Proximité S/R (50 barres) | confirmation de lieu | `sr_tol`, swing 5 |
| C6 | ±DI (substitut de C5 en `NO_SR`) | confirmation de lieu alternative | aucun |
| C7 | SL / TP = multiples d'ATR(14) | invalidation et objectif | `sl_atr`, `tp_atr` |
| C8 | Cooldown 2 barres | anti-sur-trading | fixe |
| C9 | Disjoncteur 3 pertes / 24 barres | anti-série noire | fixe |
| C10 | TP dynamique par paliers (`dtp`) | extension de la cible en cours de vie | 2 paires seulement |
| C11 | Multi-variante, 2 positions simultanées | doublement des opportunités | — |

---

## 3. Tableau de reproductibilité

Données : barres OHLC MT5 Swissquote H1, `tick_volume`, `spread`.
`real_volume = 0`. Pas de carnet d'ordres.

| # | Composant | Reproductible ? | Détail |
|---|---|---|---|
| C1 | ADX(14) | ✅ **exact** | Ne dépend que d'OHLC. Je porte l'implémentation MT5 `ADX.mq5` du code historique (DI brut par barre puis lissage EMA α=2/(p+1), amorçage à 0), pas la variante Wilder. |
| C2 | Divergence MACD | ⚠️ **substitution assumée** | §4.1. Causal dans les deux versions, mais je remplace une détection à fenêtre tronquée par une détection à fractale confirmée. |
| C3 | Inflexion histogramme | ✅ **exact** | Trois barres, purement causal. |
| C4 | RSI(14) | ✅ **exact** | EMA de Wilder, comme l'historique. |
| C5 | S/R sur 50 barres | ⚠️ **quasi-exact** | §4.2 : je retire le clustering. |
| C6 | ±DI | ✅ **exact** | Sous-produit de C1. |
| C7 | SL/TP en ATR | ✅ **exact** | ATR(14) = SMA du True Range. |
| C8 | Cooldown 2 | ✅ **exact** | `engine.run(cooldown_bars=2)` par défaut. Même valeur. |
| C9 | Disjoncteur 3/24 | ✅ **exact** | `cb_losses=3`, `cb_cooldown_bars=24` par défaut. |
| C10 | TP dynamique | ❌ **abandonné** | §4.3. |
| C11 | Multi-variante | ❌ **hors périmètre** | §4.4. |

**Aucun composant central n'est irréalisable.** Contrairement à une stratégie
d'orderflow, S1 n'utilise que des indicateurs OHLC. Le mur classique de ce
projet (`real_volume = 0`) ne s'applique pas ici. Pas de motif d'abandon en
Phase 1.

---

## 4. Ce qui est substitué, et la dégradation que ça implique

### 4.1 Détection de divergence — fenêtre tronquée → fractale confirmée

**Historique.** À chaque barre `i`, `detect_macd_divergence` regarde les
60 barres passées, y cherche les extrema locaux de l'histogramme au sens
« minimum sur ±5 barres, **fenêtre coupée à `i`** », puis teste les paires
consécutives.

C'est **causal** (rien après `i` n'est lu) mais **non stationnaire** : un creux
« détecté » à `i-2` avec une demi-fenêtre peut cesser d'en être un trois barres
plus tard. Le signal dépend donc de l'instant d'observation autant que du
marché. Coût : ~60 × 11 opérations par barre, soit ~20 M d'opérations Python par
instrument — incompatible avec une grille et une ablation.

**Ma version.** Un creux d'histogramme est un **fractale confirmé** : minimum
sur ±5 barres pleines, donc **connu seulement à `t+5`**. À la barre `i`, je
considère les creux confirmés récents (`i - t ∈ [5, 11]`, soit la même fenêtre
d'activité d'environ 7 barres que l'historique) et je compare au creux confirmé
précédent : écart 5-50 barres, prix plus bas, histogramme plus haut.

**Dégradation, honnêtement.** Le signal se déclenche 0 à 2 barres plus tard que
l'historique et un peu moins souvent (les « creux » qui n'existaient qu'à cause
de la troncature disparaissent). C'est une **perte de fidélité littérale**, mais
c'est aussi ce qu'un trader peut exécuter sans ambiguïté, et cela rend le signal
indépendant de l'instant d'observation. Je considère que c'est le **steelman** :
je teste la divergence, pas un artefact de fenêtre.

### 4.2 Support / résistance — suppression du clustering

**Historique.** À chaque barre : extraire les swings (±5) des 50 dernières
barres, **regrouper** les niveaux distants de moins de 0,1 % et prendre la
moyenne de chaque groupe, puis tester `|close - niveau| <= close × sr_tol`.

**Ma version.** Mêmes swings, même fenêtre, **sans regroupement** : distance au
swing le plus proche.

**Dégradation.** Le regroupement déplace un niveau d'au plus 0,1 % du prix. Le
`sr_tol` le plus serré testé historiquement est 0,4 %. L'écart introduit vaut
donc au plus un quart de la tolérance la plus stricte, et il est **nul dans le
sens qui compte** : si le prix est proche d'un swing, il est proche du
barycentre du groupe qui contient ce swing. Le gain : calcul vectoriel
(secondes au lieu de minutes) — ce qui rend la grille et l'ablation possibles.

### 4.3 TP dynamique par paliers — abandonné

Le mécanisme `dtp` étend la cible et remonte le stop en cours de vie quand le
trade a parcouru 70 % du chemin et que 2 confirmations sur 3 (MACD, RSI, DI)
sont réunies.

**Il est inexprimable dans le contrat `Signal`**, qui décrit une décision
d'entrée (`entry`, `stop`, `target`) et rien d'autre. L'implémenter exigerait
d'ajouter une gestion en cours de vie à `core/backtest/engine.py` — interdit
(R9 + interdiction de toucher `core/`).

**Dégradation assumée.** Il n'était activé que sur 2 des 15 configurations
validées historiquement (SP500, XAGUSD). Je teste donc S1 **en pur set &
forget**, ce qui correspond à 13 des 15 cas. Limite réelle, pas un détail.

### 4.4 Multi-variante à 2 positions — hors périmètre

L'architecture historique faisait tourner deux variantes en parallèle sur le
même instrument, 2 positions ouvertes possibles, capital partagé (d'où les
libellés `HI_aggr+NO_SR`, `HI_cons+STRICT`).

Le contrat de la plateforme est **une stratégie = un module = un magic number**,
et `engine.run` est appelé avec `max_positions=1`. Une combinaison de deux
variantes est donc un **portefeuille de deux stratégies**, pas une stratégie.

**Dégradation.** Les meilleures cellules historiques de SP500, NIKKEI et FTSE
étaient précisément des combinaisons ; je ne peux pas les reproduire à
l'identique. Mais si `HI_aggr` et `NO_SR` ont chacune une espérance par trade
positive, leur combinaison en aura une aussi ; et si aucune n'en a, aucune
combinaison des deux n'en aura. **L'espérance par trade est additive ; c'est
elle que je mesure.** La combinaison change le profil de risque, pas le signe.

### 4.5 Modèle d'exécution — plus sévère chez nous que dans l'historique

| Point | Historique | `core/backtest/engine.py` |
|---|---|---|
| Bruit sur le stop | stop élargi de `0,7 × 0,15 × range` (favorable) | stop pris si dans `[low, high]` |
| SL et TP dans la même barre | départage par la distance à l'ouverture | **le stop l'emporte toujours** |
| Spread | réel MT5 par barre si dispo, sinon forfait ×1,5 hors séance | forfait constant du catalogue, payé à l'entrée **et** à la sortie |
| Sizing | 3 % de capital, PnL en CHF | **PnL en R**, sizing hors sujet (R2) |

Le nouveau moteur est **plus pessimiste** sur les points 1 et 2, et exprime le
résultat en R plutôt qu'en CHF. Les chiffres ne sont donc pas comparables en
valeur absolue — c'est **le signe et le compte de réussites** qui le sont.

---

## 5. L'hypothèse testable

Formulée avant tout backtest, pour ne pas pouvoir être ajustée après.

> **H0.** Le filtrage S1 — ADX bas, plus divergence ou inflexion MACD, plus RSI
> extrême, plus proximité S/R — sélectionne des barres dont le rendement futur à
> horizon SL/TP a une espérance nulle. Les résultats positifs observés en 2026
> proviennent (a) du lookahead résiduel, (b) de la sélection d'une cellule parmi
> 210 × 17, (c) de la concentration sur quelques instruments et quelques périodes.
>
> **H1.** Il existe un état de marché, identifiable par ces quatre conditions
> simultanées, où le mouvement suivant est un retour vers la moyenne d'amplitude
> suffisante pour couvrir le spread.

**Ce qui doit être vrai pour que H1 tienne**, et que je mesurerai :

1. **Espérance par trade positive avant sélection.** Pas « la meilleure cellule
   est positive » — la **moyenne de la grille**, ou au moins une famille de
   variantes entière, doit l'être.
2. **Plus de réussites STRICT que le hasard n'en produit.** Avec 108 configs par
   instrument, ~5,4 réussites par instrument sont attendues d'un edge nul.
3. **Un edge brut, pas seulement un edge net.** À spread nul, si l'espérance
   reste ≈ 0, il n'y a rien que de meilleures conditions d'exécution pourraient
   sauver (diagnostic repris de s01 §5.1).
4. **Pas de directionnalité déguisée.** Sur 2021-2026 (dollar fort, SP500 et
   NIKKEI en hausse séculaire), un système qui ne gagne que d'un côté est un
   pari sur le régime. s01 a attrapé USDJPY exactement comme ça (+69,7 R long,
   −10,0 R short). Le découpage long/short est obligatoire — **et
   particulièrement critique ici**, parce que les trois « meilleurs »
   instruments historiques (SP500, NIKKEI, FTSE) sont des indices actions sur
   une période de bull market.

**Test de fidélité fixé à l'avance** (leçon de s01 §2.4) : S1 est une stratégie
H1 avec SL/TP à 1,5-4 ATR. La détention médiane des gagnants doit tomber dans
l'ordre de grandeur **quelques heures à quelques jours**. Si elle sortait à
plusieurs semaines, mon implémentation ne testerait pas S1 et le verdict devrait
être `NON REPRODUCTIBLE` plutôt qu'un jugement sur l'edge.

---

## 6. Choix d'instruments et de grille

### 6.1 Instruments — 8, dont les 4 « survivants » contaminés

| Instrument | Pourquoi |
|---|---|
| **SP500** | 1ᵉʳ du portefeuille contaminé (+244 CHF/fenêtre, 7/210 STRICT) |
| **NIKKEI** | 2ᵉ (+162, 2/210) |
| **FTSE** | 3ᵉ (+108, 7/210) |
| **AUDCHF** | 4ᵉ et seul forex retenu (+98, 3/210) |
| **EURUSD** | majeur, cité dans le mandat, déclaré inadapté par `SPEC.md` §7.2 |
| **EURCHF** | croisée CHF, dans les 9 instruments retenus à la main de v4 |
| **AUDUSD** | idem |
| **USDJPY** | majeur, **0/210** dans le run contaminé — contrôle négatif utile |

Panier construit pour que la comparaison au run contaminé soit possible : il
contient **les 4 survivants** et **4 instruments écartés**. Si l'edge est réel,
la hiérarchie devrait se retrouver.

### 6.2 Grille — 108 configurations

| Paramètre | Valeurs | Justification |
|---|---|---|
| `variant` | `DIV_SR`, `DIV_NOSR`, `HIST_INF` | les 3 chemins de code réels (§1) |
| `rsi_band` | `30/70`, `35/65`, `40/60` | couvre `STRICT`, `RSI40`, `HI_cons`/`HI_aggr` |
| `adx_max` | 25, 35, 50 | bornes historiques |
| `sl_atr` | 1,5 / 2,5 | bornes de l'échelle historique (1,5/2,0/2,5) |
| `rr` | 1,0 / 2,0 | → TP = 1,5 à 5,0 ATR, couvre l'échelle historique |

**3 × 3 × 3 × 2 × 2 = 108 configurations.** Contre 210 historiquement. La
réduction vient de la fusion des variantes redondantes (§1) et de l'expression
du TP en multiple du SL. Une grille plus grande ne trouve pas un meilleur edge,
elle trouve un meilleur faux positif — et à 108 configs, ~5,4 réussites par
instrument sont déjà attendues du pur hasard.

**Fixés hors grille** (valeurs médianes de l'usage historique, arrêtées avant
tout résultat) : MACD 12/26/9 signal SMA, RSI 14, ADX 14, ATR 14,
`sr_tol = 0,006`, lookback S/R 50, fenêtre de swing 5, lookback divergence 5,
écart entre creux 5-50 barres, fenêtre d'activité de la divergence 7 barres.

---

## 7. Ce que ce test ne pourra pas dire

Annoncé maintenant, pour que le verdict ne s'en serve pas comme excuse.

1. Le **TP dynamique** n'est pas testé (§4.3).
2. Les **combinaisons multi-variantes** ne sont pas testées comme telles (§4.4).
3. Le **régime unique** 2021-2026 n'est pas un échantillon de régimes.
4. **Slippage, swap et commission non modélisés.** S1 garde des positions
   plusieurs jours ; le swap est réel et non compté. Ces omissions ne peuvent
   qu'**aggraver** le résultat mesuré.
5. Le **spread est un forfait** du catalogue, pas le spread réel par barre.
6. **La grille elle-même a été conçue en regardant l'historique complet** —
   limitation n°1 du rapport v5, applicable intégralement ici : je peux être
   honnête sur *quelle cellule*, pas sur *quelle grille*.

---

## 8. Décision de Phase 1

**Aucun mur technique.** Tous les composants centraux sont calculables sur nos
données. Deux substitutions assumées (§4.1, §4.2), deux abandons documentés
(§4.3, §4.4). Passage en Phase 2.

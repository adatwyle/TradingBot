# AI Pathways — dépouillement des 12 transcripts

> **Objet** : extraire ce qui consolide réellement nos stratégies, notre backtester
> ou nos méthodes. Rien d'autre.
> **Sources** : `docs/sources/aipathways/*.txt` — 12 transcripts, 318 000 caractères,
> sous-titres automatiques dédupliqués. Auteur unique : Brendan / AI Pathways.
> **Date** : 2026-08-16. **Aucun fichier hors ce dossier n'a été modifié.**

---

## 0. Ce qu'il faut savoir avant de lire le détail

**Ces vidéos vendent une communauté payante, un affiliate VPS et du conseil.**
Les chiffres de vitrine (« 102 k$ en un mois », « 25 000 stratégies », « Sharpe
13 ») sont des accroches. Aucune des 12 vidéos ne présente un track record audité.
Toute la performance montrée est soit un backtest, soit un compte unique sur
30 jours.

**Mais deux vidéos font un vrai travail méthodologique** : `25000_ict_strategies`
et `9000_strategies`. Elles contiennent, sous une couche de marketing, un
entonnoir de validation plus dur que le nôtre sur trois points précis (bras
témoin aléatoire, hold-out scellé, transfert à froid). C'est là que se trouve
la valeur de ce dépouillement — nulle part ailleurs.

**Réponse directe à la question du multiple testing** (point d'attention n°1b) :

| | Constat |
|---|---|
| Le traitent-ils ? | **Oui, mais de façon opaque.** `25000` annonce « we also corrected for luck across all 25,000 tests » et chiffre l'effet du filtre : 2 191 → **1 614** survivants (26 % éliminés). `9000` cite « multiple test corrections » comme ligne de prompt. |
| Nomment-ils la méthode ? | **Jamais.** Ni Bonferroni, ni Benjamini-Hochberg/FDR, ni White Reality Check, ni Hansen SPA, ni deflated Sharpe. Aucune p-value, aucune hypothèse nulle explicite dans les 12 fichiers. |
| Conséquence | Le principe est acquis chez eux, **la méthode n'est pas transférable**. On ne peut pas la copier, on peut seulement constater qu'ils n'ignorent pas le problème. Leur chiffre « 1 614 survivants » n'est donc pas interprétable, et leurs conclusions **ne sont pas vérifiables**. |
| Ce qui est réellement transférable | Leurs **trois filtres non statistiques** qui attaquent le même problème par un autre angle : bras témoin aléatoire, transfert à froid sur un instrument jamais optimisé, hold-out scellé ouvert une seule fois. Ceux-là sont concrets et nous manquent. |

Corollaire à écrire noir sur blanc : `25000` teste 25 000 configurations et en
déclare 420 survivantes (1,7 %). Un edge nul avec un entonnoir à 6 étages
produit mécaniquement des survivants ; sans la méthode de correction, **on ne
peut pas dire si 1,7 % est au-dessus ou en-dessous de l'attente de hasard**. Leur
propre chiffre final — Sharpe **13** sur le meilleur survivant, 24 mois positifs
sur 24 — est la signature d'un résidu de sur-ajustement, ce qu'ils reconnaissent
d'ailleurs eux-mêmes (« obviously this isn't realistic at all »).

---

## 1. Tableau récapitulatif — trié par valeur décroissante

| # | Élément | Case | Source | Valeur |
|---|---|---|---|---|
| A1 | Bras témoin d'entrée aléatoire à règles de risque identiques | **À ADOPTER** | `25000`, `build_trading_bot` | ★★★★★ |
| A2 | Walk-forward glissant à K folds courts (19 folds 12 m / 3 m) | **À ADOPTER** | `backtest_properly` | ★★★★★ |
| A3 | Hold-out terminal scellé, ouvert une seule fois | **À ADOPTER** | `25000`, `find_profitable` | ★★★★☆ |
| A4 | Bootstrap de la séquence de trades → distribution du drawdown | **À ADOPTER** | `9000`, `will_change` | ★★★★☆ |
| A5 | Escalier d'ablation : contribution marginale de chaque règle | **À ADOPTER** | `25000` | ★★★★☆ |
| A6 | Transfert à froid sur un instrument jamais optimisé | **À ADOPTER** | `25000` | ★★★★☆ |
| A7 | Registre cumulé des essais (dénominateur du multiple testing) | **À ADOPTER** | `find_profitable` | ★★★☆☆ |
| A8 | Trois mesures de fragilité : % périodes positives, plus longue série perdante, PnL hors top-k | **À ADOPTER** | `25000`, `better_trader` | ★★★☆☆ |
| T1 | Le mean reversion classique est la seule famille largement vivante | **À TESTER** | `9000` | ★★★★★ |
| T2 | Le sweep de liquidité est la seule règle ICT qui ajoute quelque chose | **À TESTER** | `25000` | ★★★★☆ |
| T3 | Borne oracle : % de perdants à éviter pour rendre une stratégie viable | **À TESTER** | `25000` | ★★★★☆ |
| T4 | Couche de régime (HMM) comme portail de déploiement | **À TESTER** | `9000`, `build_trading_bot`, `will_change` | ★★★☆☆ |
| T5 | Momentum en coupe transversale (classement d'un panier) | **À TESTER** | `9000` | ★★★☆☆ |
| T6 | Seuil quantifié de sensibilité paramétrique (déviation > 40 %) | **À TESTER** | `will_change` | ★★☆☆☆ |
| D1 | Walk-forward, out-of-sample, illusion in-sample et % de rendement fictif | DÉJÀ FAIT | toutes | — |
| D2 | Coûts toujours actifs, décision au close / exécution au next open | DÉJÀ FAIT | `find_profitable` | — |
| D3 | Interdiction du look-ahead (`filtfilt`, `hmm.predict`) | DÉJÀ FAIT — et nous allons plus loin | `backtest_properly`, `build_trading_bot` | — |
| D4 | Battre l'effort zéro : benchmarks buy & hold / naïf / cash intégrés | DÉJÀ FAIT | `find_profitable` | — |
| D5 | Cohérence de famille, test de plateau, stress sur une autre époque | DÉJÀ FAIT | `find_profitable` | — |
| D6 | Couche de risque hors du modèle, avec droit de veto et coupe-circuit | DÉJÀ FAIT — et mieux | `build_trading_bot`, `personal_hedge_fund` | — |
| D7 | Décroissance de l'edge et règles d'arrêt écrites avant le live | DÉJÀ FAIT | `find_profitable` | — |
| D8 | Déterministe vs non-déterministe ; le code calcule, le LLM lit un résumé | DÉJÀ FAIT | `everything_learned`, `better_trader` | — |
| D9 | Agent sans état : boucle fichiers → travail → réécriture des fichiers | DÉJÀ FAIT | `hermes` | — |
| D10 | Pré-enregistrement des règles et du critère de réussite avant de tester | DÉJÀ FAIT | `find_profitable` | — |
| D11 | Portefeuille de stratégies décorrélées | DÉJÀ FAIT — et nous les contredisons | `find_profitable` | — |
| R1 | « 102 k$ en un mois », « +155 % sur 30 jours » | **À REJETER** | `month_102k` | — |
| R2 | « 25 000 / 9 000 stratégies testées » comme preuve | **À REJETER** | `25000`, `9000` | — |
| R3 | La « correction du hasard » non spécifiée | **À REJETER** en l'état | `25000`, `9000` | — |
| R4 | « Ceci est le plancher, pas le plafond — empilez des couches » | **À REJETER** | `9000` | — |
| R5 | Le nombre de trades n'a pas d'importance | **À REJETER** | `find_profitable` | — |
| R6 | Levier 2,5× à 4× sur BTC horaire, sans coûts ni hors-échantillon | **À REJETER** | `claude_code_like_a_quant` | — |
| R7 | HMM entraîné et étiqueté sur la fenêtre de backtest elle-même | **À REJETER** | `claude_code_like_a_quant` | — |
| R8 | Hermes « self-learning », « the more you use it the better it gets » | **À REJETER** | `hermes` | — |
| R9 | Pondération optimisée des jambes du portefeuille | **À REJETER** — mesuré faux chez nous | `find_profitable` | — |
| R10 | Analyse d'image de graphique, prédiction de prix par LLM | **À REJETER** (eux aussi) | `everything_learned` | — |

---

## 2. À ADOPTER — détail

Rappel de la barre : un élément n'entre ici que si le fichier visé et le
changement sont nommés.

### A1 — Bras témoin d'entrée aléatoire, à règles de risque identiques ★★★★★

> `25000` : « Every config here got compared against literal coin flips with the
> same exact risk setup. »
> `build_trading_bot` : « random entry and random allocation changes with same
> risk rules ».

**Fichier visé** : `core/backtest/anchored_wf.py`.

**Changement** : ajouter un bras témoin au harnais. Pour chaque instrument et
chaque fenêtre, générer N=200 jeux de signaux aléatoires ayant **exactement** les
mêmes caractéristiques que la stratégie sauf le moment d'entrée : même effectif,
même répartition long/short, mêmes distances de stop et de cible en ATR, mêmes
heures de séance autorisées. Les faire tourner dans `run_engine` et rapporter la
distribution du R hors échantillon. `WalkForwardReport.render()` affiche alors,
sous chaque ligne, le percentile de la stratégie dans cette distribution.

**Ce que ça améliore** : aujourd'hui `anchored_wf` rend des R **sans référence**
et approxime l'attente de hasard par `n_configs × 0,05` (ligne 170-174) — une
convention grossière qui suppose que chaque configuration est un test
indépendant à 5 %, ce qui est faux (les cellules d'une grille sont fortement
corrélées entre elles). Un bras témoin empirique remplace cette convention par
une **distribution nulle mesurée sur les mêmes barres**, qui absorbe
automatiquement la dérive directionnelle de la période, le coût du spread et la
structure de volatilité de l'instrument. C'est la version rigoureuse de ce que
`docs/METHODOLOGY.md` §8 exige déjà en production (« halte si la performance
glissante passe sous ce que produirait une entrée aléatoire ») mais que le
harnais de recherche ne sait pas calculer.

**Effet secondaire attendu, à assumer** : notre contrôle long/short
(`METHODOLOGY` §5.2) devient un cas particulier de ce bras témoin.

---

### A2 — Walk-forward glissant à K folds courts ★★★★★

> `backtest_properly` : entraînement 12 mois, test aveugle 3 mois, **19 folds**
> de 2018 à 2024, rendements hors échantillon recousus bout à bout.

**Fichier visé** : `core/backtest/anchored_wf.py`, constante `WINDOWS` (ligne 50)
et fonction `run_walk_forward`.

**Changement** : remplacer les 4 fenêtres emboîtées en pourcentage par une
paramétrisation `(train_bars, test_bars, step)` produisant K folds disjoints en
test. Sur nos 5,1 ans de H1, un pas de 3 mois donne **17 à 19 tranches de test
indépendantes** au lieu de 4 emboîtées. Le mode `MODE_ROLLING` existe déjà
(lignes 52-62, 279) mais n'a jamais été exécuté et reste bridé par les 4 fenêtres
codées en dur.

**Ce que ça améliore** : c'est la réponse directe à la limite que nous avons
nous-mêmes écrite dans `METHODOLOGY` §9 — « folds emboîtés ; les résultats OOS ne
sont pas indépendants ; **n < 3 en pratique** ». Avec K folds disjoints,
`avg_oos` devient une moyenne sur un échantillon réel, on peut lui associer un
écart-type et un intervalle, et le critère STRICT (4/4) — dont `anchored_wf`
documente lui-même la fragilité aux lignes 22-26 — se remplace par une
proportion de folds positifs, quantité continue et bien plus stable.

**Coût** : K fois plus de runs moteur. À compenser en réduisant les grilles, ce
qui est de toute façon souhaitable (voir A7).

---

### A3 — Hold-out terminal scellé, ouvert une seule fois ★★★★☆

> `25000` : « the last two years of data stayed completely locked away until the
> very end… no configuration saw these two years. We ran it exactly one time.
> Whatever this showed was going into the video. »
> `find_profitable` : 2010-2022 pour construire, 2023→ scellé pour noter.

**Fichier visé** : `core/backtest/anchored_wf.py` + le chargeur de
`core/data/`.

**Changement** : introduire une réserve terminale (12 derniers mois) que le
chargeur **tronque par défaut**. Toute la recherche, toutes les grilles, tous les
walk-forwards travaillent sur les 4,1 ans restants. L'ouverture se fait par un
appel explicite `--unseal`, qui écrit une ligne horodatée dans un journal
append-only (`backtests/SEAL_LOG.md`) : stratégie, configuration unique évaluée,
date. Une deuxième ouverture pour la même stratégie est signalée comme telle dans
le rapport.

**Ce que ça améliore** : nous n'avons **aucune** mesure véritablement
indépendante. Nos quatre fenêtres sont emboîtées et la dernière (90-100 %) a été
regardée des dizaines de fois au fil des itérations sur chaque stratégie — elle
est de fait contaminée par nos propres choix. Un hold-out scellé donne **une**
observation propre par stratégie, ce qui est peu, mais c'est plus que zéro. Le
journal rend le nombre d'ouvertures auditable, ce qui est le seul garde-fou
possible contre l'usure du hold-out.

**Point d'honnêteté** : sur 5,1 ans, sceller 12 mois retire 20 % de
l'entraînement. C'est un coût réel. La contrepartie est qu'un résultat sur données
scellées vaut plus que trois résultats sur données regardées.

---

### A4 — Bootstrap de la séquence de trades → distribution du drawdown ★★★★☆

> `9000` : « we took every surviving strategy's trades and reshuffled them 500
> times… some of these momentum strategies only looked clean in the very exact
> path that the market actually took. »
> `will_change` : 1 000 rééchantillonnages, sortie = valeur finale médiane,
> probabilité de perte, drawdown moyen des 5 % pires tirages.

**Fichier visé** : promouvoir en `core/backtest/bootstrap.py`, appelé depuis
`WalkForwardReport.render()`.

**Changement** : le code existe déjà, mais **enfermé dans
`strategies/s04_aipathways_trendcore/backtests/run_analysis.py`** — c'est-à-dire
dans une stratégie, en violation de l'esprit de R9 (« backtester commun, jamais
réimplémenté »). Le promouvoir dans `core/`, l'appliquer à la liste de trades
d'un `BacktestResult`, et rapporter : R total médian, IC 95 %, probabilité de
résultat négatif, et **drawdown moyen des 5 % pires trajectoires**.

**Ce que ça améliore** : c'est le gap n°3 identifié dans le brief (« ni
Monte-Carlo/bootstrap sur la courbe d'equity »), et c'est le seul de nos gaps que
la source traite explicitement et de façon reproductible. Aujourd'hui
`max_drawdown_r` est une **valeur ponctuelle sur une seule trajectoire** ; elle
sert pourtant de critère d'admission (`tier1_pass`, ligne 132-138) et de règle
d'arrêt en production (`METHODOLOGY` §8 : « halte si le drawdown dépasse le pire
drawdown backtesté »). Fonder une règle d'arrêt sur un maximum observé une fois
est fragile : le bootstrap donne un quantile, qui est la bonne quantité.

**Limite à documenter** : le rééchantillonnage des trades **détruit
l'autocorrélation** des séries de gains/pertes. Il répond à « ce résultat
dépend-il de l'ordre exact ? », pas à « ce résultat est-il significatif ? ». Ne
pas confondre les deux — la source les confond (`will_change` : « 973 restent
profitables, donc la stratégie a un edge », affirmation sans hypothèse nulle).

---

### A5 — Escalier d'ablation : contribution marginale de chaque règle ★★★★☆

> `25000` : construction de la stratégie une règle à la fois, score à chaque
> marche, tout le reste fixé. Fair value gap seul = **33**. + exigence de sweep =
> **69**. + filtre de displacement = baisse. + restriction aux heures fameuses =
> baisse. + biais 15 min = **0,16**.

**Fichier visé** : nouveau `core/backtest/ablation.py`.

**Changement** : un harnais qui prend une stratégie exposant ses filtres comme
drapeaux booléens dans `manifest().param_grid`, et évalue la séquence
d'activation une marche à la fois, en rapportant le **R par trade** (jamais le R
total) à chaque marche.

**Ce que ça améliore** : nous disposons de deux ablations maison
(`METHODOLOGY` §5.1 spread, §5.2 long/short), toutes deux excellentes et toutes
deux **conçues pour un seul facteur à la fois**. Il n'existe rien pour répondre à
« lequel de mes six composants porte le résultat, et lequel le détruit ? ».
C'est exactement la question qui restait ouverte sur `s01` (6 affirmations A1-A6
testées en bloc) et sur `s11` (cassure Donchian + ADX + DI + ATR + ER200 +
failed_rate200 — six filtres empilés, jamais isolés). Le résultat le plus
instructif de `25000` est précisément que **cinq des six règles du framework
dégradent le résultat** et qu'une seule le porte.

**Garde-fou obligatoire** : la marche est jugée sur le **R par trade**, jamais sur
le R total. C'est déjà notre règle (`METHODOLOGY` §6, dernière ligne) et elle est
ici structurellement indispensable, puisque chaque filtre ajouté retire des
trades.

---

### A6 — Transfert à froid sur un instrument jamais optimisé ★★★★☆

> `25000` : les survivants sur NQ sont rejoués **à froid sur ES**, sans
> re-réglage. 420 sur 1 614 survivent — **74 % d'élimination**.

**Fichier visé** : `core/backtest/anchored_wf.py`, option `--cold-transfer`.

**Changement** : après sélection de la meilleure configuration sur l'instrument
d'entraînement, l'appliquer **telle quelle** à un ou plusieurs instruments de la
même classe qui n'ont participé à aucune optimisation, et rapporter le R par
trade obtenu. Aucun re-réglage, aucune sélection a posteriori de l'instrument
cible : la liste est fixée dans le manifest avant de regarder les chiffres.

**Ce que ça améliore** : c'est le détecteur de sur-ajustement au **meilleur
rapport signal/coût de calcul** de tout le dépouillement — un seul run, et il
élimine les trois quarts des candidats chez eux. Nous optimisons instrument par
instrument, donc nous ne mesurons **jamais** la transférabilité. Sur `s01`, où
seuls USDJPY et XAUUSD dépassaient l'attente de hasard sur sept instruments, un
transfert à froid EURUSD → USDJPY aurait tranché immédiatement entre « edge de
famille » et « deux instruments chanceux ».

---

### A7 — Registre cumulé des essais ★★★☆☆

> `find_profitable` : « run every single idea logged inside the ideas file, and
> **add every variant tested to the running count**. »

**Fichier visé** : nouveau `core/validation/trials.py` + un appel en fin de
`run_walk_forward`.

**Changement** : journal append-only qui enregistre, à chaque exécution du
harnais : stratégie, instrument, empreinte du jeu de données (dates + nombre de
barres), nombre de configurations, date, commit git. Une fonction
`expected_false_positives(strategy_id, dataset_fingerprint)` renvoie le cumul.
`WalkForwardReport.render()` affiche alors **deux** attentes de hasard : celle de
la passe courante (déjà présente, ligne 170-174) et le **cumul historique sur le
même jeu de données**.

**Ce que ça améliore** : notre ligne « ≈ N × 0,05 attendues par pur hasard » est
honnête *au sein d'une passe* et trompeuse à l'échelle du projet. `s10` a exposé
864 cellules, `s11` 1 024, `s01` 896 — **sur les mêmes 5,1 ans de barres**. Le
dénominateur réel du multiple testing n'est pas la grille du jour, c'est tout ce
que nous avons jamais tenté sur ces mêmes barres. C'est le seul mécanisme du
dépouillement qui attaque frontalement l'angle mort de la source (voir §5).

**Bénéfice induit** : rend visible et coûteux l'élargissement de grille, ce qui
va dans le sens de `s92_claudetrader/CLAUDE.md` (« une grille énorme ne trouve
pas un meilleur edge, elle trouve un meilleur faux positif »).

---

### A8 — Trois mesures de fragilité du résultat ★★★☆☆

> `25000` : pourcentage de jours / semaines / mois positifs ; **19 jours perdants
> consécutifs** sur la meilleure configuration.
> `better_trader` : retrait des 3 meilleurs trades — « still up around 14 000, so
> not one single trade dominates ».

**Fichier visé** : `core/backtest/engine.py`, classe `BacktestResult`, et le
rendu de `anchored_wf`.

**Changement** : trois propriétés supplémentaires.
1. `positive_period_pct(freq)` — part de semaines et de mois positifs.
2. `longest_losing_streak` — en trades et en jours calendaires.
3. `total_r_excluding_top(k)` — R total privé des k meilleurs trades.

**Ce que ça améliore** :
- (3) étend au **niveau du trade** notre garde-fou de concentration, qui
  n'existe aujourd'hui qu'au niveau de l'instrument (`METHODOLOGY` §6 : « un book
  dont 93 % du résultat vient d'un instrument »). Un R total porté par deux
  trades est le même défaut à une autre échelle, et nous ne le mesurons pas.
- (2) est décisif pour un compte de **1 000 CHF** : une série de 19 pertes
  consécutives est une information de dimensionnement et de tenue psychologique
  que ni `avg_oos` ni `max_drawdown_r` ne rendent.
- (1) est le seul apport de la partie « est-ce que ça paie comme un revenu ? » de
  `25000`, qui est par ailleurs le passage le plus honnête de la vidéo.

Coût d'implémentation : faible, tout est déjà dans la liste de trades.

---

## 3. À TESTER — hypothèse et protocole

### T1 — « Le mean reversion est la seule famille largement vivante » ★★★★★

**Ce qu'ils affirment** : sur 9 000 backtests, 30 actifs, barres journalières,
15 ans, le mean reversion est **la seule catégorie positive en moyenne** ; il
représente **64 % des 478 survivants** ; RSI-reversion survit sur **20 tickers
non reliés**, Keltner-reversion sur 18. Trend, volume, volatilité, patterns :
négatifs en moyenne.

**Pourquoi c'est prioritaire** : ce n'est **pas** une contradiction avec nos
mesures, c'est un **trou de couverture**, et c'est plus embarrassant. Notre seul
verdict portant un nom proche est `s10_legacy_meanrev` — mais son contenu réel est
**divergence MACD + support/résistance**, sur **H1**, sur **FX et indices CFD**.
La famille qu'ils déclarent vivante (RSI / Bollinger / Keltner, retour à la
moyenne pur, **D1**, **ETF actions**) n'a jamais été testée ici. Nous avons donc
déclaré mort quelque chose qui porte le même mot, pas la même chose.

**Hypothèse testable** : un retour à la moyenne nu (RSI < seuil bas, sortie au
retour à la médiane ou après n barres) a une espérance positive par trade, après
coûts, sur nos instruments D1, et cette espérance est répartie sur un large
voisinage de réglages plutôt que concentrée sur une cellule.

**Protocole** :
1. Implémenter `sXX_meanrev_classic` selon le workflow imposé
   (`_TEMPLATE/`), grille **délibérément petite** — 3 périodes RSI × 3 seuils
   × 2 modes de sortie = 18 cellules, à consigner dans le registre A7.
2. Timeframe **D1** — le péage y est de 0,46 point de win rate contre 2,14 en H1
   (`METHODOLOGY` §2). Une famille à faible R:R n'a aucune chance en H1 ; les
   tester en H1 serait reproduire l'erreur S5.
3. Univers : les instruments les plus proches de leurs ETF actions, soit SP500,
   NASDAQ, DAX, FTSE, NIKKEI, plus XAUUSD en témoin négatif (l'or tend, il ne
   doit **pas** passer — `METHODOLOGY` §1, vérification 3).
4. Passer R1, puis A2 (folds glissants), A1 (bras témoin), A6 (transfert à
   froid SP500 → DAX/FTSE).
5. **Critère de réussite écrit avant de voir un chiffre** : R par trade positif
   sur ≥ 70 % des folds, bras témoin battu au 95ᵉ percentile, transfert à froid
   positif, et voisinage de réglages lisse.

**Ce que trancherait le test** : soit nous découvrons la première famille à
résidu autre que l'or, soit nous établissons que leur résultat ne survit pas à
notre classe d'actifs et à nos spreads — et dans ce cas nous saurons **pourquoi**
(le drag D1 sur CFD indices est chiffrable avant même de coder).

---

### T2 — « Le sweep de liquidité est la seule règle ICT qui ajoute quelque chose » ★★★★☆

**Ce qu'ils affirment** : escalier d'ablation, gap seul = 33 → ajout du sweep =
69 ; toutes les règles suivantes dégradent. Conclusion explicite : « a sweep and
a snapback is just mean reversion on a one-minute chart with different
vocabulary ».

**Hypothèse testable** : un balayage de plus-bas/plus-haut récent suivi d'un
retour dans la plage (mèche de rejet) a une espérance positive par trade, et
l'ajout de filtres de structure la dégrade.

**Protocole** : implémenter la règle **minimale** — balayage d'un extrême sur
lookback k, retour de clôture dans la plage, entrée contre le balayage, stop
au-delà de la mèche, cible à l'extrême opposé — et lui appliquer **A5**
(escalier d'ablation) avec les composants qu'ils déclarent nuisibles : filtre de
displacement, restriction horaire, biais de timeframe supérieur. Timeframe H1
(M5 est hors de portée : profondeur ~16 mois, `METHODOLOGY` §9). Instruments :
XAUUSD et indices.

**Chiffrer avant de coder** (`METHODOLOGY` §2) : leur version survivante trade
**1 996 fois par an** avec un edge par trade minuscule et une cible 2:1. Le drag
H1 médian de 8,57 % coûte 2,14 points de win rate ; sur XAUUSD (spread 25 pips)
la marge est probablement négative avant même la première ligne de code. **Faire
ce calcul d'abord.** S'il condamne, ne pas implémenter — et écrire pourquoi.

---

### T3 — Borne oracle : quelle discrétion faudrait-il pour sauver une stratégie ? ★★★★☆

**Ce qu'ils font** : deux diagnostics à look-ahead assumé, utilisés comme
**bornes supérieures**, pas comme résultats. (a) Un « biais boule de cristal » qui
connaît la direction du jour à l'avance, pour majorer ce que vaudrait un filtre
directionnel parfait. (b) « **17,2 %** » — la part des trades perdants qu'il
faudrait savoir éviter à l'avance pour rendre la version textbook solide.

**Pourquoi c'est intéressant** : c'est un usage **méthodologiquement propre** du
look-ahead — non pas pour produire un résultat, mais pour majorer un espoir.
Nous n'avons aucun outil de ce type, et c'est un excellent argument de clôture de
dossier : si l'oracle parfait lui-même ne suffit pas, la stratégie est morte
définitivement et aucune amélioration future ne la sauvera.

**Protocole** : ajouter à `core/backtest/ablation.py` (A5) une fonction
`oracle_bound(result)` qui renvoie (a) le R obtenu si l'on retire les x %
de trades perdants les plus coûteux, x variant, et (b) le x minimal
atteignant le seuil de rentabilité. À rapporter systématiquement dans les
`VERDICT.md` des stratégies rejetées.

**Test qui trancherait le concept** : le rejouer sur `s01` et `s11`, déjà
déclarées mortes. Si le x nécessaire dépasse 20-30 %, la conclusion « aucun
filtre discrétionnaire ne sauvera cette famille » devient **chiffrée** au lieu
d'être une opinion.

---

### T4 — Couche de régime comme portail de déploiement ★★★☆☆

**Ce qu'ils affirment** : HMM gaussien sur log-rendements et volatilité, 3 à 7
états, **algorithme forward uniquement** (`hmm.predict` traite toute la séquence
et introduit du look-ahead), filtre de stabilité (un régime doit persister ≥ 3
barres, et plus de 4 bascules sur 20 barres bloque l'action). Momentum en régime
tendanciel, mean reversion en régime agité.

**Ce qui est réutilisable tel quel** : le filtre de stabilité et l'interdiction de
`predict`. Le reste est spéculatif et non démontré chez eux — `will_change`
montre un HMM dont le rendement varie de +143 % (or) à négatif (obligations)
sans jamais tester la significativité.

**Hypothèse testable** : conditionner une stratégie de cassure à un régime
détecté **causalement** améliore son R **par trade**, et pas seulement son R
total.

**Protocole** : rejouer `s11_legacy_breakout` (cassure Donchian, mesurée morte)
avec un portail de régime. Contraintes non négociables :
- Le détecteur doit passer R1 (`core/validation/causality.py`) — c'est
  précisément là que `hmm.predict` échouerait, et notre gardien le verrait.
- Le nombre d'états est **fixé à l'avance** (3), pas sélectionné sur les
  données ; leur balayage 3→7 est un test multiple non compté.
- Jugement sur le **R par trade** uniquement (`METHODOLOGY` §6).
- Les cellules du portail comptent dans le registre A7.

**Ce que trancherait le test** : si le R par trade de `s11` reste négatif dans
tous les régimes, la couche de régime est un habillage — et on ferme le sujet
définitivement plutôt que de le rouvrir tous les six mois.

---

### T5 — Momentum en coupe transversale ★★★☆☆

**Ce qu'ils affirment** : le momentum mono-actif score « basiquement zéro », mais
la version en coupe transversale — classer un panier, tenir les plus forts —
« score way better ». Décliné dans `find_profitable` en rotation mensuelle : les
5 ETF sur 50 les plus proches de leur plus-haut 52 semaines, cash si SPY sous sa
moyenne 200 jours.

**Hypothèse testable** : un classement mensuel de nos 8 instruments avec
détention des 2 plus forts bat le naïf équipondéré en Sharpe hors échantillon.

**Protocole** : c'est une stratégie d'**allocation**, donc
`core/backtest/allocation_engine.py` s'applique directement et rend
automatiquement les trois références (buy & hold de chaque jambe, naïf
équipondéré, cash). Grille minimale : 2 fenêtres de lookback × 2 tailles de
panier = 4 cellules.

**Réserve à écrire d'emblée** : leur univers compte 50 ETF, le nôtre 8
instruments. Un classement sur 8 noms a un pouvoir de sélection très faible et
un bruit d'estimation élevé. Le test est peu coûteux (le moteur existe) mais son
verdict sera probablement « non concluant, univers trop étroit » — ce qui reste
une information utile et clôt le sujet.

---

### T6 — Seuil quantifié de sensibilité paramétrique ★★☆☆☆

**Ce qu'ils affirment** : carte de chaleur de sensibilité, rouge au-delà de
**40 % de déviation maximale** par rapport au résultat de base. Exemple : un
croisement de moyennes sur SPY variant de +33 % à −9,5 % selon le réglage → jugé
fragile.

**Ce que ça apporte** : notre « test de plateau » (`METHODOLOGY` §4) est
qualitatif — « la performance doit être lisse ». Un seuil chiffré le rend
falsifiable.

**Protocole** : calculer, sur les verdicts déjà rendus (`s01`, `s04`, `s10`,
`s11`), l'amplitude relative du R par trade sur le voisinage 3×3 de la meilleure
cellule. Vérifier si un seuil sépare effectivement les cas que nous avons jugés
robustes de ceux que nous avons jugés sur-ajustés. **Le seuil de 40 % n'est
justifié nulle part chez eux** — il ne s'adopte qu'après calibration sur nos
propres cas, sinon c'est un nombre magique importé.

---

## 4. Contradictions avec nos mesures

Consigne respectée : je ne tranche ni en leur faveur ni en la nôtre. Je nomme le
test qui départage.

### C1 — Trend core QQQ/or : leur meilleure stratégie, mesurée non concluante chez nous

| | Eux (`find_profitable`) | Nous (`s04.../research/VERDICT.md`) |
|---|---|---|
| CAGR | +33,8 % | +23,0 % (vs +20,0 % buy & hold NASDAQ) |
| Sharpe | 1,66 | 1,23 |
| Drawdown | −13,6 % | −17,0 % |
| Bascules | 5,3 / an | 3,25 / an, **14 au total** |
| Référence naïve | jamais calculée | **50/50 rebalancé quotidiennement : Sharpe 1,26 — supérieur** |
| Hors 2022 | non testé | la règle **perd** en CAGR contre le buy & hold |
| Verdict | « beat buy and hold QQQ significantly » | **NON CONCLUSIF (données insuffisantes)** |

**Nature du désaccord** : ce n'est pas un désaccord sur les faits, c'est un
désaccord sur la **profondeur d'historique**. Ils annoncent une validation sur
« past 50 years of history » ; nous mesurons sur 4,31 ans après warmup, ce qui
donne 14 épisodes — et un IC 95 % du différentiel de Sharpe de [−0,40 ; +0,97],
donc indistinguable du bruit. Ils ne montrent jamais les chiffres de leurs 50 ans.

**Test qui départage** : le seul obstacle est la profondeur de données, pas le
moteur. `allocation_engine.py` est prêt et rend les références automatiquement.
Reconstruire une série journalière longue à partir de sources gratuites (indice
Nasdaq composite depuis 1971, or au comptant depuis 1968, en substituts assumés
de QQQ/GLD), et rejouer la bascule moyenne 200 jours sur **50 ans** avec :
(a) le naïf 50/50 comme référence obligatoire ; (b) une décomposition par
décennie, en particulier 2000-2009 qu'ils citent eux-mêmes comme la pire
(`find_profitable`, filtre de stress) ; (c) le bootstrap A4 sur la série de
bascules. **C'est le test le plus rentable de tout ce document** : il est peu
coûteux, il ferme ou rouvre un dossier déjà instruit, et il attaque directement
notre faiblesse méthodologique n°1 (un seul régime macro).

### C2 — Pondération de portefeuille : ils optimisent, nous avons mesuré que c'est nuisible

Ils prescrivent, en dernière étape, de « figure out the correlations, then weight
certain strategies to get either less money or more money » (`find_profitable`),
et `personal_hedge_fund` bâtit un optimiseur de Markowitz complet.

Nous avons mesuré l'inverse (`METHODOLOGY` §7) : la construction **naïve
équipondérée bat la sélection optimisée** hors échantillon, **+3 374 contre
+939**. Le glouton concentre sur peu de noms en maximisant le Sharpe du *train*,
qui ne prédit pas celui du *test*.

**Ce n'est pas un match nul** : notre résultat est reproductible sur nos données
et il correspond au résultat académique classique (DeMiguel, Garlappi & Uppal,
2009). Le leur n'est étayé par aucun chiffre — aucune des 12 vidéos ne compare
son optimiseur à l'équipondéré. **Test qui départage, s'il fallait le rouvrir** :
faire tourner leur MVO contre l'équipondéré sur nos jambes, hors échantillon,
avec les coûts de rééquilibrage. Priorité basse : nous avons déjà la réponse et
eux n'ont pas de preuve à opposer.

### C3 — « Le nombre de trades n'est pas le plus important »

`find_profitable` : « the number of trades in a strategy isn't the most important
thing. Some of the best strategies only fire a few times a year, and they survive
backtesting. » Leur stratégie phare tire **5 fois par an**.

Notre règle opposée est écrite en tête de `anchored_wf.py` (lignes 28-34), née
d'un « strict pass » sur 19 trades dont l'IC 95 % du taux de réussite contenait le
seuil de rentabilité. Et nous l'avons re-vérifiée sur leur propre stratégie :
14 bascules, 0 à 2 par fenêtre de test.

**Il n'y a pas de test à faire ici** : leur affirmation est une erreur
statistique, pas une hypothèse concurrente. Un effectif faible ne rend pas une
stratégie mauvaise — il rend le **verdict** impossible. Leur phrase confond les
deux. À classer en À REJETER (R5) ; consigné ici parce que c'est le point où nos
deux méthodologies divergent le plus nettement.

### C4 — Leur résidu ICT vivant contre notre calcul de péage

La version qui survit à tout leur entonnoir trade **1 996 fois par an** sur des
barres 1 minute, avec un edge par trade explicitement décrit comme minuscule
(« the edge per trade is pretty small and the money comes from frequency »). Ils
signalent eux-mêmes que les fills sont supposés parfaits.

Notre économie du trade (`METHODOLOGY` §2) dit qu'un coût **fixe** par trade
divisé par un mouvement visé **décroissant avec le timeframe** rend une famille
haute fréquence structurellement fragile. C'est le cas d'école S5, qui nous a
coûté des semaines.

**Test qui départage, à faire avant toute implémentation** : appliquer
`drag = spread / (sl_atr × ATR)` à leur configuration sur nos données
disponibles les plus proches (M5 ou H1 sur NASDAQ/XAUUSD). Si la pénalité en
points de win rate excède la marge brute annoncée, le dossier est clos sans
écrire de stratégie. Coût : dix lignes.

### C5 — Familles mortes : recoupement, sans contradiction

| Famille | Leur verdict | Notre verdict | Statut |
|---|---|---|---|
| Cassure / breakout | négatif en moyenne, « situationnel » | `s11` morte (H1, FX + indices) | **Concordant** |
| Trend / moyennes mobiles | négatif en moyenne ; « no real reason a line crossing another line should predict anything » | `s11`, `s01` mortes | **Concordant** |
| Swing structure HTF | non testé | `s01` morte — 19 passes STRICT là où le hasard en produit 45 | Non couvert par eux |
| Divergence MACD | non testé | `s10` morte | Non couvert par eux |
| Or comme résidu récurrent | « gold trends, it barely mean reverts » ; or = meilleur actif de leur test régime (+143 %) | seul résidu positif récurrent chez nous (`s01` : XAUUSD, +3,21 R moyen sur grille) | **Concordant, et c'est le seul point d'accord empirique positif des deux côtés** |
| Mean reversion classique | **seule famille vivante** | jamais testée sur ce périmètre | **Trou de couverture → T1** |

Le recoupement est plus favorable qu'attendu : les trois familles que nous avons
mesurées mortes sont celles qu'ils classent négatives en moyenne, et le seul
actif qui résiste des deux côtés est l'or. Cela ne valide pas leur méthode —
mais deux mesures indépendantes qui concordent sur cinq familles, c'est
davantage que ce que nous avions.

---

## 5. Ce qu'ils ne traitent pas — les angles morts, qui deviennent nos risques si on les copie

Chacun de ces points est un endroit où **copier la source dégraderait notre
méthode**.

**1. La correction du multiple testing n'est jamais spécifiée.** Elle est
annoncée deux fois, chiffrée une fois (2 191 → 1 614), nommée zéro fois. Aucune
p-value, aucune hypothèse nulle, aucun deflated Sharpe, aucun White Reality Check
dans 318 000 caractères. **Risque si on copie** : importer leur entonnoir en
croyant qu'il traite le problème. Il ne le traite pas de façon auditable. Notre
ligne « ≈ N × 0,05 » est plus faible qu'une vraie correction mais elle a un
mérite qu'ils n'ont pas : elle est explicite et reproductible.

**2. Le dénominateur cumulé n'existe pas.** Chaque vidéo re-teste les mêmes
actifs sur les mêmes périodes. Les stratégies présentées sont les survivantes
d'un pipeline dont les échecs ne sont montrés qu'en agrégat, et jamais les
essais **antérieurs aux vidéos**. `find_profitable` : 155 idées → 5 retenues,
présentées avec des chiffres issus de la même passe qui les a sélectionnées.
C'est du data snooping via le présentateur. **Notre parade : A7.**

**3. Le survivorship bias n'est traité qu'une fois, et grossièrement.** `9000`
filtre les actifs à plus de 10 ans d'historique (524 → 478), ce qui traite le
biais de jeunesse mais pas la survie : l'univers reste celui des ETF et des
grandes capitalisations **existant aujourd'hui**. `personal_hedge_fund` fait pire
— il score les 503 composants **actuels** du S&P 500 sur des facteurs
historiques, cas d'école de survivorship bias, non mentionné. **Chez nous, ce
biais est structurellement absent** (paires FX et indices continus, pas de
sélection de titres) : c'est une force à ne pas perdre si nous élargissons un
jour l'univers.

**4. La sélection adverse à l'exécution est reconnue une fois, modélisée jamais.**
`25000` le dit très bien : « when price smashes through your order you always get
filled and those are mostly your losers ; when price just taps your level and
bounces, other orders are ahead of yours ». C'est exactement notre limite
« slippage non modélisé » (`METHODOLOGY` §9), en pire, puisque leur résidu vivant
est une stratégie à ordres limites à 2 000 trades/an. Notre moteur est déjà plus
honnête (stop prioritaire sur cible dans la même barre, `engine.py` lignes 15-19)
— mais nous ne modélisons pas non plus le non-remplissage des gagnants.

**5. Les coûts sont absents ou non chiffrés dans la moitié des fichiers.**
`claude_code_like_a_quant` fait tourner un levier 2,5× sur BTC horaire sans
aucun coût ni financement. `will_change`, `month_102k`, `personal_hedge_fund` ne
chiffrent jamais spread ni commission. Seuls `25000` et `find_profitable` sont
propres sur ce point. **Notre parade existe déjà** : coûts toujours actifs, et
surtout le calcul de péage **avant** implémentation (`METHODOLOGY` §2), qu'aucune
des 12 vidéos ne fait.

**6. Aucun track record audité, nulle part.** Douze vidéos, zéro. La performance
la plus « live » est un compte unique sur 30 jours (`month_102k`). Nous avons déjà
formalisé le rejet de ce type de preuve dans
`s92_claudetrader/sources/NATEHERK_ARCHITECTURE.md` §4 (« +8 % contre le S&P
comme preuve → rejeté, n = 1 sur 30 séances »). La même règle s'applique ici.

**7. Les couches ajoutées ne sont jamais comptées comme des essais
supplémentaires.** `9000` conclut en invitant à empiler régimes, combinaisons et
filtres : « these numbers can get a lot better ». Chaque couche est un nouveau
degré de liberté testé sur les mêmes données. Le nombre d'états du HMM lui-même
est sélectionné sur les données (3 à 7 balayés). **Risque direct si on copie
T4** : c'est pour cela que le protocole T4 fixe le nombre d'états à l'avance.

**8. La décroissance de l'edge est affirmée, jamais mesurée.** « The strategy
that worked in 2024 won't work in 2025 » coexiste, chez le même auteur, avec des
backtests de 15 et 16 ans présentés comme preuves de durabilité. Les deux
affirmations sont incompatibles et aucune n'est chiffrée. Notre `METHODOLOGY` §8
a au moins des règles d'arrêt opérationnelles ; mais nous ne mesurons pas non
plus la demi-vie d'un edge. Angle mort **partagé**.

**9. Aucun intervalle de confiance dans 318 000 caractères.** Pas un seul. Une
stratégie qui tire 5 fois par an y est déclarée validée. C'est l'écart le plus
profond entre leur méthode et la nôtre, et c'est la raison pour laquelle leurs
conclusions ne peuvent pas être reprises telles quelles — seulement leurs
**dispositifs**, qui sont bons.

**10. Le « self-learning » d'Hermes n'est jamais évalué.** Mémoire persistante et
fichiers de compétences générés automatiquement : c'est ce que fait déjà
`s92_claudetrader` (`memory/`, `skills/`, `decisions/`) suivant
`NATEHERK_ARCHITECTURE.md` §3.1. La vidéo n'apporte **rien** au-delà : aucun
protocole d'évaluation du gain d'apprentissage, aucune mesure avant/après, et la
moitié du transcript est un tutoriel d'installation VPS avec code promotionnel.
Le seul élément marginalement neuf est la **séparation en plusieurs agents
spécialisés** (un pour le briefing, un pour la recherche, un pour l'exécution) —
que nous appliquons déjà par ailleurs. **Classé À REJETER (R8)**, sans
équivalent transférable.

---

## 6. Ce qui est déjà chez nous — références

Pour éviter que ces points reviennent comme « nouveaux » à la prochaine lecture.

| Élément de la source | Chez nous |
|---|---|
| Walk-forward, train/test, out-of-sample | `core/backtest/anchored_wf.py:8-16`, `:50` |
| Illusion in-sample, « 75 % du rendement était fictif » | `anchored_wf.py:102-123` (`illusion_r`, `honest_r`, `degradation_pct`) et `:206-228` |
| Walk-forward glissant (code présent, jamais exécuté) | `anchored_wf.py:52-62`, `:279` — voir **A2** |
| Coûts toujours actifs, modèle d'exécution pessimiste | `core/backtest/engine.py:12-25` ; `METHODOLOGY` §3.2 |
| Décision au close, exécution au next open | `core/backtest/allocation_engine.py:30-33` |
| Interdiction du look-ahead (`filtfilt`, `hmm.predict`) | R1, `core/validation/causality.py` — **et nous allons plus loin** : le contrôle porte aussi sur les tableaux d'indicateurs depuis le commit `7ba94e9`, précisément parce qu'un `filtfilt` passait le test au niveau des signaux seuls (`s10_legacy_meanrev/research/VERDICT.md` §2.0) |
| Battre l'effort zéro, benchmarks systématiques | `allocation_engine.py:15-28`, `:234-242` ; `METHODOLOGY` §0 |
| Cohérence de famille, test de plateau, stress autre époque | `METHODOLOGY` §4 |
| Ancien / simple / publié ; qui paie ? ; adapté à l'actif | `METHODOLOGY` §1 |
| Couche de risque hors du modèle, veto, coupe-circuit non auto-réarmable | `core/risk/guards.py:1-40` — **et mieux** : `guards.py` cite explicitement le défaut de leur approche (garde-fou dans le prompt = suggestion) |
| Règles d'arrêt écrites avant le live, décroissance de l'edge | `METHODOLOGY` §8 |
| Déterministe vs non-déterministe ; le code calcule, le LLM lit | `s92_claudetrader/sources/NATEHERK_ARCHITECTURE.md` §1 |
| Agent sans état, boucle fichiers → travail → réécriture | idem §3.1 ; `s92_claudetrader/memory/`, `skills/` |
| Pré-enregistrement des règles et du critère de réussite | `s92_claudetrader/CLAUDE.md` Phase 1 ; `s11.../VERDICT.md` §1 (critère de robustesse écrit **avant** de voir un chiffre) |
| Portefeuille de stratégies décorrélées | `METHODOLOGY` §7 — **et nous contredisons leur étape de pondération** (voir C2) |
| Effectif toujours rapporté, comparaison au hasard | `anchored_wf.py:28-34`, `:170-174` ; `METHODOLOGY` §6 |

**Seuils chiffrés relevés, à titre de valeurs de référence uniquement** (aucun
n'est justifié par une mesure dans la source, tous sont des choix d'auteur) :
risque 1 %/trade ; coupe-circuit −2 % jour → demi-taille, −3 % jour → tout
clôturer, −10 % depuis le pic → arrêt avec fichier de blocage manuel
(`build_trading_bot`) ; −2,5 % jour et −8 % depuis le pic (`personal_hedge_fund`) ;
corrélation signalée au-delà de 0,85 ; stop suiveur 10 % et coupe des perdants à
−7 % (`hermes`/Nate Herk). La structure correspondante existe déjà dans
`core/risk/guards.py` ; seules les valeurs sont à arbitrer.

---

## 7. Ce que je recommanderais si Adrian ne veut retenir que trois choses

1. **A2 + A3** — folds glissants courts et hold-out scellé. Ils attaquent
   ensemble la limite que nous avons nous-mêmes documentée comme la plus grave
   après le régime unique : `n < 3` observations hors échantillon réellement
   indépendantes. Sans elles, tous nos verdicts reposent sur trop peu.
2. **A1** — bras témoin aléatoire. Il remplace une convention arbitraire
   (`× 0,05`) par une distribution mesurée, et il rend enfin comparables des R
   qui aujourd'hui flottent sans référence.
3. **C1** — rejouer le trend core QQQ/or sur 50 ans. C'est le seul test du
   document qui adresse notre faiblesse n°1 (un seul régime macro), le moteur
   existe déjà, et il ferme ou rouvre un dossier que nous avons classé
   « non concluant faute de données ».

Le reste est utile mais second. Et **T1** — le mean reversion classique jamais
testé chez nous — est le seul endroit où la source signale peut-être quelque
chose que nous n'avons pas vu.

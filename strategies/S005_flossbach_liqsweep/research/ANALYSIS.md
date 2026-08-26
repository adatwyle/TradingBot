# ANALYSIS — s05_flossbach_liqsweep (Phase 1)

> Rédigé **avant** toute ligne de `strategy.py` et **avant** tout backtest.
> Les conditions de falsification du §7 sont figées ici ; le VERDICT dit
> lesquelles ont été déclenchées.

---

## 1. Source

| | |
|---|---|
| Vidéo | https://www.youtube.com/watch?v=BewBId1gbqQ (IQ Capital, ~64 min) |
| Trader | Tim Flossbach, allemand / Dubaï |
| Transcript | `../SOURCE_transcript.txt` (intégral, fourni par Adrian) |
| Captures | `../frames/*.jpg` — 19 captures horodatées, lues et exploitées |

**Crédibilité vérifiable.** L'introduction annonce « verified professional
trader of over 10 years » et un compte à plusieurs millions. Aucune de ces
affirmations n'est auditée : pas de relevé, pas de compétition tierce, pas de
track record vérifiable. Ce n'est pas un reproche, c'est le statut par défaut
de ce format. En sens inverse, il ne vend rien (« I'm doing everything free »),
il dit que 95 % des coachs de son marché ne savent pas trader, il déclare avoir
perdu de l'argent sur les figures chartistes, et il met en garde contre les
indicateurs rétrospectifs (« most of the indicators are not real time, they are
back time ») — trois positions techniquement justes et contraires à son intérêt
commercial. Posture retenue : **source de bonne foi, claims non audités**.
Ni crédit ni décote a priori.

**Ce qu'il chiffre** — à confronter, pas à croire :

| Claim | Verbatim | Testable ? |
|---|---|---|
| Sélectivité | « I skip more than 90% of the trades I see » | oui — fréquence faible attendue |
| Taux de réussite | « you can figure it out to 70/30, 80/20 » | oui — win rate |
| Récurrence du motif | « 80% liquidation sweep to liquidation sweep pullback to support » | partiellement |
| R:R | « 95% of my trades are minimum 2:1, never below » | oui — contrainte dure |
| Universalité | « everything I show here today is possible in every market » | oui — multi-familles |
| Post-balayage | « after we grab the liquidation, it will be 80% upwards a reversal » | **oui — c'est LE test** |

Le dernier est l'affirmation centrale et la plus falsifiable de l'entretien.

---

## 2. La méthode, reformulée dans mes termes

Le marché n'est pas un lieu de création de valeur mais de **transfert** (« it's
an illusion that people think the market is producing new money, it's just
exchanging of money »). Les zones où beaucoup d'ordres de protection sont
empilés — stops, liquidations de positions à levier, ordres limites — sont donc
des **cibles** : celui qui a la taille a intérêt à y faire passer le prix pour
se remplir contre des sortants forcés. Une fois cette liquidité consommée, le
carburant du mouvement dans cette direction disparaît, et le prix repart en
sens inverse.

Séquence opérationnelle, dans son ordre :

1. **Contexte HTF** (weekly → daily) : structure de hauts/bas (« it's a lower
   high structure, so we are obviously in a downtrend ») + EMA 200/50/(30).
   Méthode revendiquée triviale : « it's one of the easiest parts in trading ».
2. **Repérer un amas** d'ordres non encore consommés. Critère explicite quand
   on lui retire l'indicateur : « if you see that in one specific zone there's
   not one liquidity but there is a lot a lot a lot of combined liquidity ».
3. **Approche lente puis balayage** : « the market always is going very slow to
   these zones, but then with one candle out of nowhere ».
4. **NE PAS ENTRER sur le balayage.** C'est l'erreur qu'il dit avoir corrigée :
   « the biggest problem I did in my past years was to enter way too fast ».
5. **Attendre la structure de retournement** : après un balayage de bas, un
   **creux plus haut** se forme — « this down move was making a higher low than
   before… it was changing the trend into an uptrend ».
6. **Entrer sur la cassure nette** du sommet intermédiaire : « I need a very
   clear breakout ». Il renonce explicitement quand de la liquidité reste
   disponible plus bas.
7. **Stop** sous l'extrême du balayage (« directly under the situation where
   the first liquidation grabbed », 23:07) **ou** sous le creux plus haut
   (« that's why I placed my stop loss below this range », 34:03). Les deux
   formulations coexistent — les deux sont testées.
8. **Cible = amas opposé** (« the target point was obviously the top of short
   liquidation »). Si R:R < 2, **il ne prend pas** — règle dure, répétée trois
   fois.
9. **Rejet** si : marché haché (« if the liquidity is shaking too much, high
   candles up, high candles down, then I will skip it all the time »), news
   majeure (« Fed decision time… I will always always skip »), conflit avec le
   HTF (« if the higher time frame tells you something else than the 15 minute
   time frame, there's no point where you should go with the 15-minute »).

**Les deux sens sont explicitement autorisés** : « I don't think that you only
have to focus on short trades… you should always be open for both sides ».

Timeframes : weekly → daily pour le contexte, **H4 « my most favorite time
frame to enter big positions »**, M15 pour l'exécution.

**Qui perd de l'argent, et pourquoi ?** — question n°2 de `METHODOLOGY.md`, la
plus discriminante. La réponse existe ici et elle est structurelle : les
porteurs de stops et de positions à levier placés juste au-delà d'un extrême
visible. Ils perdent parce que leur ordre est mécanique, groupé et localisable.
C'est un mécanisme de transfert identifiable, pas un simple motif graphique.
**C'est l'argument le plus fort en faveur de la méthode et la raison de la
tester sérieusement.**

---

## 3. Décomposition en composants et reproductibilité

Données disponibles : barres OHLC MT5 Swissquote, `tick_volume` (changements de
cotation, pas un volume de contrats), `spread`. **`real_volume = 0`**, pas de
carnet d'ordres, pas de données de liquidation d'exchange.

| # | Composant | Ce qu'il utilise | Reproductible ? | Substitut retenu |
|---|---|---|---|---|
| C1 | Tendance HTF | structure H/L + EMA 200/50 | **oui** | EMA(`htf_ema`) sur la série tradée |
| C2 | Localisation de la liquidité | X-Ray (carnets agrégés d'exchanges) | **NON — donnée absente** | extrêmes de swing **non balayés** (§4) |
| C3 | Magnitude en $ de l'amas | X-Ray (« 149 million ») | **NON — donnée absente** | **nombre** d'extrêmes agglomérés |
| C4 | Balayé / non balayé | lignes pleines vs pointillées | **oui, à l'identique** | drapeau `swept` : non balayé tant que le prix ne l'a pas traversé |
| C5 | Approche lente puis bougie violente | lecture visuelle | partiellement | non modélisé en entrée (voir §6.3) |
| C6 | Balayage | pénétration de la zone | **oui** | `low < niveau_amas` (resp. `high >`) |
| C7 | Structure de retournement | creux plus haut + cassure du sommet intermédiaire | **oui, à l'identique** | machine à états sur pivots fractals confirmés |
| C8 | Cassure « nette » | jugement | approximatif | `close > sommet + 0,1 × ATR` |
| C9 | Stop | sous l'extrême du balayage / sous le creux plus haut | **oui** | les deux variantes en grille |
| C10 | Cible | amas opposé | **oui**, sous réserve de C2 | amas d'extrêmes opposés |
| C11 | Filtre R:R ≥ 2 | règle dure | **oui, à l'identique** | contrainte, hors grille |
| C12 | Rejet « shaking too much » | jugement visuel | approximatif | ATR(5)/ATR(50) > seuil ⇒ rejet |
| C13 | Filtre news | calendrier + jugement | **NON — pas de calendrier** | **non implémenté**, déclaré |
| C14 | Prises partielles 25/25/reste | gestion discrétionnaire | **NON** — le moteur ne connaît que SL/TP/fin de tranche (R9) | sortie unique à la cible |
| C15 | Stop au point mort | gestion discrétionnaire | **NON**, même raison | aucun |
| C16 | « feeling for the chart » | 10 ans d'expérience | **NON, par nature** | rien. Déclaré, pas prétendu modélisé |

---

## 4. Le point dur : le substitut de liquidité

Sa détection repose sur **X-Ray / X-Ray Pro**, indisponibles (« it's like a top
secret indicator, you can't just find it outside of my platform »).

Trois éléments du transcript autorisent malgré tout un test — et ils viennent
**de lui**, pas de moi :

1. L'indicateur n'est pas nécessaire : « I can also be profitable without this
   indicator but it makes my life so much easier ». Noté 8,5/10 pour le
   confort, pas pour la viabilité.
2. Il dit **où** sont ces zones sans l'indicateur : « this is not random, this
   is of course because the market shows us also without indicator — because
   what do you see? You will see the top of the last structure here, and just
   randomly the liquidation is directly in these zones » (17:00).
3. Il donne le critère de densité en clair quand on lui demande explicitement
   comment faire sans l'indicateur (25:44) : « if you see that in one specific
   zone there's not one liquidity but there is a lot a lot a lot of combined
   liquidity, then it's definitely a very big alert ».

Le proxy est donc **dérivé de sa description, pas inventé** :

> Un **amas de liquidité** = au moins `min_cluster` extrêmes de swing (pivots
> fractals confirmés) **non encore balayés**, dont les prix tiennent dans une
> bande de `band_atr × ATR`.

Les captures le confirment : sur `frames/t23m20s.jpg`, `t24m50s.jpg`,
`t27m55s.jpg` et `t31m25s.jpg`, ses lignes de liquidation sont des
**horizontales alignées sur des sommets et des creux antérieurs**, groupées par
paquets de trois à six dans une bande étroite, les pointillés (non balayés)
au-delà des extrêmes visibles. C'est exactement ce que le proxy construit.

**Ce que le proxy capture** : la localisation, l'état balayé/non balayé (C4,
reproductible à l'identique), la densité par le **nombre** d'extrêmes
agglomérés.

**Ce que le proxy perd**, et c'est à charge :
- la **magnitude en dollars** — il distingue 149 M$ de 5 M$, pas nous ;
- la liquidité **hors extrêmes de swing** (chiffres ronds, VWAP d'exchange,
  concentrations d'options) ;
- la distinction **long liquidations / short liquidations** (lignes vertes vs
  rouges) — chez nous elle est purement géométrique ;
- surtout : ses zones proviennent des **carnets crypto agrégés**. Sur un CFD
  forex Swissquote, il n'est **pas démontré** que les stops se concentrent aux
  mêmes endroits. Le proxy suppose « extrême de structure = amas d'ordres »,
  ce qui est l'hypothèse de la méthode, pas un fait mesuré.

> **Conséquence, écrite ici et non découverte après :** un échec ne réfute pas
> sa méthode, il réfute **notre proxy de sa méthode**. Un succès, lui, serait
> informatif : il confirmerait son propre propos, à savoir que l'edge tient
> sans l'indicateur propriétaire.

---

## 5. L'économie du trade, calculée AVANT d'implémenter

`core/data/source.py::spread_cost_analysis`, ATR médian, `rr = 2` (sa règle),
`sl_atr_mult = 1,0` — hypothèse défavorable : un stop sous l'extrême de
balayage est court ; à 2 ATR le péage est deux fois moindre.

| TF | Instrument | ATR médian | spread | drag | **péage en pts de WR** |
|---|---|---|---|---|---|
| H4 | NASDAQ | 1134,3 p | 8,0 | 0,71 % | **0,24** |
| H4 | SP500 | 245,0 p | 5,0 | 2,04 % | **0,68** |
| H4 | XAUUSD | 1124,4 p | 25,0 | 2,22 % | **0,74** |
| H4 | WTIUSD | 88,1 p | 3,0 | 3,40 % | **1,13** |
| H4 | USDJPY | 43,8 p | 2,8 | 6,39 % | **2,13** |
| H4 | EURUSD | 26,4 p | 1,9 | 7,19 % | **2,40** |
| H4 | AUDUSD | 23,8 p | 2,0 | 8,40 % | **2,80** |
| H4 | USDCHF | 23,7 p | 2,2 | 9,29 % | **3,10** |
| H4 | XAGUSD | 266,7 p | 25,0 | 9,37 % | **3,12** |
| H4 | USDCAD | 27,8 p | 3,1 | 11,16 % | **3,72** |
| H1 | (toutes) | — | — | 1,5 – 22,9 % | **0,50 – 7,63** |

Seuil de rentabilité à R:R = 2 : **33,3 %** de réussite.

**Décision prise ici, et pas après coup :** le timeframe principal est **H4** —
celui qu'il désigne lui-même **et** celui où le péage est soutenable. H1 est
testé en secondaire, avec la mise en garde que sur USDCAD/USDCHF le péage y
atteint 6 à 8 points de win rate. **M15 est écarté** : profondeur Swissquote
insuffisante (~100 000 barres) et péage prohibitif — un stop de 1 ATR M15 sur
EURUSD vaut ~5 pips pour 1,9 pip de spread, soit 38 % de drag.

Il annonce 70-80 % de réussite pour un seuil à 33,3 %. Si son claim est même
approximativement vrai, la marge est très supérieure au péage. **L'économie
n'interdit pas de coder** — contrairement au cas d'école S5, où le même calcul
aurait dû arrêter le projet avant l'implémentation.

---

## 6. Écarts assumés par rapport à la source

1. **Liquidité par proxy structurel** (§4) — l'écart principal, de signe inconnu.
2. **Pas de filtre news** (C13) : aucun calendrier économique dans le projet.
   Ses trades les plus dangereux ne sont donc pas filtrés chez nous. Écart
   **défavorable** à la stratégie.
3. **Approche lente + bougie violente** (C5) non modélisée comme condition
   d'entrée. Partiellement capturée par C12, mais en **rejet**, pas en
   confirmation.
4. **Sortie unique à la cible** au lieu des prises partielles (C14). Le moteur
   commun ne sait pas sortir par tranches et R9 interdit d'en écrire un autre.
   Un trade qu'il aurait sécurisé à +1 R avant retournement est chez nous un
   perdant plein. Écart **défavorable**.
5. **Pas de stop au point mort** (C15). Écart **défavorable**.
6. **Crypto non testable** : BTCUSD absent du catalogue Swissquote (vérifié,
   `load_bars` retourne `None`). Or **toute sa démonstration est faite sur
   Bitcoin**, marché à levier extrême où les liquidations sont un phénomène
   mécanique et mesurable. C'est la limite la plus sérieuse du test.
7. **Un seul régime macro** (2021-2026), limite connue du projet.

Les écarts 2, 4 et 5 sont défavorables : un résultat nul chez nous n'est donc
pas nécessairement un résultat nul chez lui.

---

## 7. Hypothèse testable et conditions de falsification

### H05 — figée avant tout backtest

> Après qu'un amas d'extrêmes de structure non balayés a été **traversé**
> (balayage), puis qu'une **structure de retournement** s'est formée (extrême
> plus favorable + cassure du sommet/creux intermédiaire), l'espérance du
> mouvement vers l'amas opposé est **positive et supérieure au coût du
> spread** — et cet avantage est **spécifiquement dû au balayage préalable**,
> pas à la simple cassure de structure.

Deux affirmations séparables :
- **(a)** le motif complet a une espérance positive nette de coûts ;
- **(b)** le **balayage** y contribue — sinon on a mesuré un banal breakout.

### Conditions de falsification, déclarées ex ante

| # | Condition | H05 est réfutée si… |
|---|---|---|
| **F1** | **Espérance à spread nul** | R/trade ≤ 0 à `spread_pips = 0`, en poolé. Alors il n'y a pas un edge mangé par les coûts : il n'y a pas d'edge. |
| **F2** | **Hasard de la grille** | Le nombre de réussites STRICT au walk-forward est ≤ l'attente par pur hasard (`n_configs × 0,05` par instrument). |
| **F3** | **Contrôle du balayage** *(teste (b))* | Le même déclencheur de retournement **sans** exigence de balayage fait aussi bien ou mieux en R/trade. Alors l'ingrédient « liquidation sweep » n'apporte rien. |
| **F4** | **Asymétrie directionnelle** | Un seul sens porte la totalité du résultat positif. On aurait mesuré la tendance 2021-2026. |
| **F5** | **Effectif** | L'effectif hors échantillon médian est < 20 trades par instrument. |

**Note capitale sur F5.** Il annonce skipper > 90 % des setups : **un faible
nombre de trades est ATTENDU, pas suspect**. F5 n'est donc pas un critère de
rejet de la méthode, c'est un critère de rejet de la **conclusion** : peu de
trades ⇒ intervalle de confiance large ⇒ verdict NON CONCLUSIF plutôt que
verdict tranché. La distinction est posée ici, avant de connaître le résultat,
précisément pour ne pas pouvoir en jouer après.

Seuil de réussite à battre : **33,3 %** à R:R = 2 (moins si le R:R réalisé est
supérieur). Il annonce 70-80 %. Entre 33 % et 70 %, la méthode marche moins
bien qu'annoncé mais marche ; sous 33 %, elle perd de l'argent telle que nous
la reproduisons.

---

## 8. Ce qui est implémenté

- **TF principal H4**, secondaire H1.
- **11 instruments, 4 familles** : forex majeur (EURUSD, USDJPY, USDCHF,
  USDCAD, AUDUSD), métaux (XAUUSD, XAGUSD), indices (SP500, NASDAQ, DAX),
  énergie (WTIUSD). Crypto impossible (§6.6).
- **Les deux sens**, comme il le demande.
- **Grille de 64 cellules** — ≈ 3,2 réussites STRICT attendues par pur hasard
  et par instrument, chiffre affiché à côté de tout résultat.
  `min_rr = 2,0`, `piv = 3`, `brk_atr = 0,1`, `setup_bars = 48` sont **hors
  grille** : ce sont ses règles, pas des variables d'ajustement.
- **Trois groupes de contrôle** : sans balayage (F3), sans attente du creux
  plus haut, et un **placebo** (mêmes géométries de stop/cible, entrée décalée
  au hasard) qui donne la ligne de base du hasard pour le même R:R.
- **`precompute` renvoie un `DataFrame`** — condition pour que le gardien R1
  inspecte réellement la couche indicateur : `_compare_precompute` retourne
  silencieusement sur un objet opaque, et une stratégie qui renvoie un `dict`
  échappe au contrôle sans le moindre message (piège rencontré par s91).

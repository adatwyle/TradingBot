# Verdict — AI Pathways "Trend core" (bascule QQQ/GLD sur MM200), Phase 4

Source : https://www.youtube.com/watch?v=Fb7G5SNpaes — Brendan / AI Pathways
Donnees : MT5 Swissquote, **D1**, 1329 barres alignees NASDAQ/XAUUSD/SP500,
2021-07-19 -> 2026-08-14. Fenetre evaluee apres warmup MM200 : **1128 jours (4,31 ans)**
Grille : **12 configurations** (ma_len x buffer) -> ~0,6 reussite attendue par PUR HASARD
R1 (causalite) : **PASSE**, 24 points de grille x 4 coupures = 96 comparaisons, 0 fuite

---

## 0. Resume en cinq lignes

1. Sur nos 5 ans, la regle **bat le buy & hold NASDAQ sur les trois metriques**
   (CAGR +23,0 % vs +20,0 %, Sharpe 1,23 vs 0,90, DD -17,0 % vs -25,3 %).
2. Mais l'ecart est **indistinguable du bruit** : IC 95 % du differentiel de Sharpe
   = **[-0,40 ; +0,97]**, 19 % des tirages bootstrap defavorables.
3. **Hors 2022** — le seul episode baissier de l'echantillon, 16 % des jours — la
   regle **perd** contre le buy & hold en CAGR (-1,64 pt) et son avantage de Sharpe
   tombe a +0,09.
4. Un **portefeuille naif 50/50 NASDAQ+or, rebalance quotidiennement, fait aussi
   bien** (Sharpe 1,26 contre 1,23). Le signal MM200 n'apporte rien de plus que la
   diversification.
5. **14 bascules** au total. Verdict : **NON CONCLUSIF (donnees insuffisantes)**.

---

## 1. Ce que la source affirme

| Metrique | Annonce | Fenetre |
|---|---|---|
| CAGR | **+33,8 %** | 2023-01 -> 2026-07 (test scelle) |
| Sharpe | **1,66** | idem |
| Drawdown max | **-13,6 %** | idem |
| Bascules | **5,3 / an** | idem |
| Validation additionnelle | ~50 ans d'historique | |

Aucun track record audite. L'auteur affiche un rapport de backtest, pas des
resultats realises. A son credit, il signale lui-meme que *le repli sur GLD tient
en partie a la vigueur recente de l'or ; 2005-09 favorisait plutot un repli en
cash* — ce caveat est teste de front au §2.4.

---

## 2. Ce que nous mesurons

### 2.0 Effectif — a lire avant tout le reste

```
14 bascules de regime sur 4,31 ans  =  3,25 / an   (annonce : 5,3 / an)
```

**Quatorze episodes.** Le walk-forward ancre decoupe des tranches de test de 10 %
de l'historique : **0 a 2 bascules par fenetre**. C'est en dessous de tout seuil de
credibilite — rappel du precedent maison : un "strict pass" sur **19** trades avait
un IC 95 % du taux de reussite de **[27,3 % ; 68,3 %]**, seuil de rentabilite
**dedans**.

Toutes les mesures ci-dessous s'appuient donc sur les **1128 rendements
journaliers**, pas sur les 14 episodes. C'est ce qui rend l'analyse possible ; ca
ne la rend pas concluante (§2.7).

### 2.1 Le critere n1 — battre l'achat-conservation

Fenetre 2022-05 -> 2026-08, 1128 jours, spread reel Swissquote, execution a
l'ouverture suivante.

| | CAGR | Sharpe | DD max | vol | total |
|---|---|---|---|---|---|
| **Trend core (NASDAQ/XAUUSD, MM200)** | **+23,02 %** | **1,23** | **-16,96 %** | 18,17 % | +144,2 % |
| buy & hold NASDAQ | +20,01 % | 0,90 | -25,33 % | 23,39 % | +119,5 % |
| buy & hold XAUUSD | +20,45 % | 1,07 | -26,63 % | 19,16 % | +123,0 % |
| buy & hold SP500 | +14,28 % | 0,85 | -20,20 % | 17,46 % | +77,7 % |
| **buy & hold 50/50 NASDAQ+XAUUSD** (rebal. quot.) | +21,36 % | **1,26** | -17,18 % | 16,48 % | +130,3 % |
| *annonce par la source* | *+33,80 %* | *1,66* | *-13,60 %* | — | — |

**Elle bat les trois buy & hold simples.** C'est un fait, et il faut le dire aussi
clairement que le reste.

**Elle ne bat pas le portefeuille naif 50/50.** Sharpe 1,23 contre **1,26**,
drawdown -16,96 % contre -17,18 %, pour un CAGR superieur de 1,67 pt seulement.
C'est le resultat le plus derangeant du test : **melanger betement les deux actifs
a poids fixes reproduit l'essentiel du profil de la strategie**, sans regarder la
moyenne mobile une seule fois.

Ce n'est pas une surprise methodologique : `docs/METHODOLOGY.md` §7 documente deja
que la construction naive equiponderee bat la selection optimisee hors echantillon
(+3374 contre +939 en agrege). On retrouve ici le meme motif.

### 2.2 Sur sa propre fenetre de test — comparaison a armes egales

2023-01 -> 2026-07, 938 jours, exactement sa fenetre scellee :

| | CAGR | Sharpe | DD max |
|---|---|---|---|
| *annonce (QQQ/GLD)* | *+33,80 %* | *1,66* | *-13,60 %* |
| **notre mesure (NASDAQ/XAUUSD)** | **+28,80 %** | **1,45** | **-16,96 %** |
| notre meilleure variante (ma250/buf0,5 %) | +30,28 % | 1,51 | -13,92 % |
| buy & hold NASDAQ | +30,43 % | 1,37 | -25,33 % |
| buy & hold XAUUSD | +25,17 % | 1,24 | -26,63 % |
| buy & hold 50/50 | +28,88 % | **1,70** | -14,38 % |

Nous reproduisons **l'ordre de grandeur** de ses chiffres, en dessous sur les trois
metriques. L'ecart s'explique (§3.1) sans mettre en cause sa sincerite.

**Point decisif de ce tableau : sur SA fenetre, le buy & hold NASDAQ fait un CAGR
superieur (+30,43 % contre +28,80 %), et le 50/50 naif fait un Sharpe superieur
(1,70 contre 1,45).** Sa fenetre de test ne contient aucun marche baissier durable
— c'est vrai chez lui comme chez nous.

### 2.3 Attribution par jambe — le caveat teste de front

| jambe | jours | % du temps | contribution composee | % du gain | **annualise** |
|---|---|---|---|---|---|
| NASDAQ (au-dessus MM) | 861 | 76,3 % | +121,2 % | **88,9 %** | **+27,30 %** |
| XAUUSD (en dessous MM) | 267 | 23,7 % | +10,4 % | **11,1 %** | **+10,20 %** |

La colonne qui compte est la derniere : le rendement de la jambe **ramene a une
annee de detention**, seule mesure independante du temps passe dedans (ne jamais
juger un filtre sur le PnL total).

**Resultat contraire a la crainte de depart : ce n'est PAS du beta or deguise.**
La jambe or apporte 11 % du gain, a un rythme annualise de +10,2 % — soit **moins
bien que le buy & hold or lui-meme (+20,45 %)**. Le repli sur l'or attrape donc les
*mauvaises* periodes de l'or, pas les bonnes. Le piege USDJPY (+69,7 R long /
-10,0 R short) **ne se reproduit pas ici**.

Ce qui ne disculpe pas la strategie pour autant : cela veut dire que la jambe or ne
sert qu'a **eviter l'actif risque**, pas a gagner. C'est exactement ce que teste le
§2.4.

### 2.4 Variante cash — la jambe or apporte-t-elle quelque chose ?

| | CAGR | Sharpe | DD max | vol |
|---|---|---|---|---|
| Trend core NASDAQ/**XAUUSD** (la regle) | +23,02 % | 1,23 | -16,96 % | 18,17 % |
| Variante **CASH** (hors marche sous la MM, remunere 0 %) | +20,23 % | **1,25** | **-14,25 %** | 15,81 % |
| buy & hold NASDAQ | +20,01 % | 0,90 | -25,33 % | 23,39 % |

**La variante cash a un Sharpe egal ou meilleur et un drawdown plus faible**, avec
un cash remunere a **0 %**. Sur 2023-2026 les T-bills rapportaient ~4-5 % : en les
comptant, la variante cash gagnerait environ +1 pt de CAGR supplementaire et
passerait devant sur le CAGR aussi.

> **Le caveat de l'auteur est confirme sur nos donnees.** La jambe GLD n'apporte
> rien en rendement ajuste du risque. Ce qui produit le resultat, c'est **sortir du
> Nasdaq**, pas **entrer dans l'or**.

Meme conclusion sur la variante SP500 : cash Sharpe 1,20 et DD -8,93 % contre or
1,13 et -16,04 %.

### 2.5 Ablation du spread — annoncee comme un non-evenement, et c'en est un

| | CAGR | Sharpe | DD max |
|---|---|---|---|
| spread reel Swissquote | +23,02 % | 1,23 | -16,96 % |
| spread **nul** | +23,05 % | 1,23 | -16,94 % |

Cout total : **0,088 % cumule sur 4,31 ans**, soit **0,020 % / an**. Impact sur le
CAGR : **-0,025 point**.

C'etait ecrit en Phase 1 (ANALYSIS §8) avant toute mesure, et c'est verifie. A 3
bascules par an sur des actifs a spread relatif de 0,005-0,012 %, le peage est
~1/1000e du resultat. **Le spread ne peut ni causer un echec ni excuser un succes
ici.** C'est la difference structurelle avec le cas S5/H1 (drag 8,57 %, penalite
2,14 points de win rate) : sur D1 avec 3 transactions annuelles, le cout de
transaction n'est simplement pas un sujet.

Le cout qui compte et que nous ne modelisons pas est le **swap / financement** sur
une position detenue en permanence (CFD indice + or spot). Voir §6.3.

### 2.6 Controle long/short — degenere, et c'est une information

```
jours en position LONG  : 1128 / 1128 = 100,0 %
jours en position SHORT :    0 / 1128 =   0,0 %

beta realise vs NASDAQ : 0,525   (correlation 0,677)
beta realise vs XAUUSD : 0,349   (correlation 0,368)
```

La strategie est **longue en permanence, par construction**. Le decoupage par sens
ne peut donc pas la disculper — il la classe d'office du cote "exposition
directionnelle", avec un beta cumule de 0,87 sur deux actifs qui ont tous les deux
double sur la periode.

C'est precisement pour cette raison que le benchmark buy & hold du §2.1 est le seul
juge possible, et pas une formalite.

### 2.7 L'ecart avec le buy & hold est-il distinguable du bruit ?

Bootstrap par blocs de 21 jours (1 mois) sur les rendements **apparies**,
5000 tirages, preservant dependance serielle et correlation entre les series.

| comparaison | observe | IC 95 % | tirages defavorables |
|---|---|---|---|
| CAGR vs B&H NASDAQ | +3,01 pt | **[-14,92 ; +17,62] pt** | **38,6 %** |
| Sharpe vs B&H NASDAQ | +0,33 | **[-0,40 ; +0,97]** | **19,0 %** |
| CAGR vs 50/50 naif | +1,67 pt | [-12,30 ; +15,31] pt | 41,7 % |
| Sharpe vs 50/50 naif | **-0,03** | [-0,74 ; +0,61] | **55,5 %** |

**Aucun des quatre ecarts n'est significatif.** Le plus favorable — le Sharpe contre
le buy & hold NASDAQ — laisse encore 19 % de tirages ou la strategie fait moins
bien. Contre le 50/50 naif, elle est defavorisee dans la majorite des tirages.

### 2.8 Concentration temporelle — tout tient a 2022

| annee | jours | Trend core | B&H NASDAQ | B&H XAUUSD | variante cash | % temps en or |
|---|---|---|---|---|---|---|
| 2022 (des mai) | 181 | **-6,4 %** | **-19,6 %** | -6,4 % | +0,0 % | 100,0 % |
| 2023 | 260 | +47,5 % | **+52,6 %** | +13,6 % | +39,6 % | 7,3 % |
| 2024 | 263 | +23,3 % | **+25,4 %** | +26,5 % | +20,9 % | 0,4 % |
| 2025 | 262 | **+28,9 %** | +19,9 % | +65,4 % | +15,9 % | 18,7 % |
| 2026 (jusqu'a aout) | 162 | +11,3 % | **+19,0 %** | +0,2 % | +13,1 % | 10,5 % |

**La strategie perd contre le buy & hold 3 annees sur 5.** Elle gagne en 2022 (le
seul marche baissier) et en 2025 (rallye de l'or).

Le test decisif — retirer 2022, soit **16 % des jours** :

| | CAGR | Sharpe | DD max |
|---|---|---|---|
| Trend core — **hors 2022** | +30,45 % | 1,52 | -16,96 % |
| buy & hold NASDAQ — **hors 2022** | **+32,09 %** | 1,43 | -25,33 % |

```
avantage de CAGR   : +3,01 pt sur tout l'echantillon  ->  -1,64 pt hors 2022
avantage de Sharpe : +0,33   sur tout l'echantillon  ->  +0,09  hors 2022
```

> **L'integralite de l'avantage en rendement vient d'un unique episode de 181 jours.**
> C'est le motif "93 % du resultat vient d'un instrument" que la methodologie du
> projet interdit de prendre pour un systeme — ici transpose au temps.

Ce n'est pas un argument contre la strategie *en soi* : une assurance ne paie que
les jours d'incendie, et c'est normal. C'est un argument sur **notre capacite a la
juger** : nous avons observe **un** incendie.

### 2.9 La MM200 separe-t-elle vraiment deux populations ? (critere I4)

Rendements journaliers du NASDAQ selon le regime :

| regime | n | moyenne / jour | annualise | ecart-type / jour | **vol annualisee** |
|---|---|---|---|---|---|
| au-dessus MM200 | 861 | +0,0985 % | +29,4 % | 1,117 % | **18,1 %** |
| en dessous MM200 | 267 | +0,0208 % | +5,6 % | 2,195 % | **35,5 %** |

```
difference de moyenne : +0,0777 % / jour     t = 0,56     NON significatif
rapport de volatilite : 35,5 / 18,1 = 1,96x  tres net
```

**C'est le resultat le plus solide et le plus utile de tout le test.**

La MM200 **ne predit pas le rendement** — la difference de moyenne n'est pas
distinguable de zero (t = 0,56, il en faudrait 1,96). En revanche elle **separe
tres nettement le regime de volatilite** : la volatilite double sous la moyenne.

Autrement dit : **la MM200 est un filtre de risque, pas un filtre de rendement.**
Tout ce que la strategie fait vraiment, c'est reduire l'exposition quand la
volatilite realisee est haute. Ce qui explique mecaniquement l'ensemble des
observations precedentes : Sharpe ameliore, drawdown reduit, CAGR non ameliore hors
episode baissier, et equivalence avec un simple 50/50 (qui reduit lui aussi la
volatilite, autrement).

### 2.10 Test de plateau — 12 configurations

| ma_len | buffer | bascules | CAGR | Sharpe | DD max | *variante cash : Sharpe* |
|---|---|---|---|---|---|---|
| 100 | 0,0 % | 41 | +17,89 % | 0,97 | -20,77 % | 0,97 |
| 100 | 0,5 % | 33 | +14,72 % | 0,82 | -20,72 % | 0,90 |
| 100 | 1,0 % | 23 | +16,34 % | 0,90 | -22,64 % | 0,86 |
| 150 | 0,0 % | 27 | +19,23 % | 1,05 | -23,55 % | 1,11 |
| 150 | 0,5 % | 19 | +19,86 % | 1,08 | -20,52 % | 1,08 |
| 150 | 1,0 % | 15 | +19,30 % | 1,06 | -19,05 % | 1,02 |
| **200** | **0,0 %** | **14** | **+23,02 %** | **1,23** | **-16,96 %** | 1,25 |
| 200 | 0,5 % | 6 | +25,80 % | 1,36 | -16,04 % | 1,30 |
| 200 | 1,0 % | 6 | +25,10 % | 1,33 | -16,04 % | 1,27 |
| 250 | 0,0 % | 18 | +25,95 % | 1,39 | -13,92 % | 1,12 |
| 250 | 0,5 % | 12 | +26,42 % | **1,40** | -13,92 % | 1,10 |
| 250 | 1,0 % | 10 | +23,01 % | 1,25 | -17,03 % | 1,03 |

```
configurations battant le B&H NASDAQ en CAGR   :  6/12
configurations battant le B&H NASDAQ en Sharpe : 11/12   (hasard attendu : ~0,6)
```

**Bonne nouvelle** : la surface est **lisse et monotone** en `ma_len` — pas de
cellule isolee, pas de pic. La valeur de la source (200) n'est pas la meilleure,
elle est au milieu d'un plateau. C'est le profil d'un parametre robuste, pas d'un
sur-ajustement. Le critere I5 n'est **pas** declenche.

**Mauvaise nouvelle** : la monotonie va dans le sens "plus la moyenne est longue,
mieux c'est", ce qui sur 4,3 ans avec un seul episode baissier signifie surtout
"moins on bascule, moins on rate le rebond". Ce plateau-la mesure la forme de
**notre** echantillon, pas une propriete de la regle.

### 2.11 Walk-forward ancre — et pourquoi il ne dit rien

`backtests/anchored_wf.txt`, les deux jambes :

| jambe | STRICT | attendu par hasard | TIER 1 | trades, plein echantillon |
|---|---|---|---|---|
| risk (NASDAQ) | **0/12** | 0,6 | 0/12 | **1** |
| hedge (XAUUSD) | **0/12** | 0,6 | 0/12 | **2** |

**Un a deux trades sur cinq ans.** Ce n'est pas un resultat, c'est une preuve que le
moteur ne peut pas executer cette strategie (§4.2). Ces chiffres sont archives par
transparence et **n'entrent pas dans le verdict**.

Meme constat sur la selection hors echantillon faite en comptabilite d'equity
(section 9 de `equity_analysis.txt`) : la strategie bat le buy & hold sur **2
fenetres sur 4**, avec **0 a 2 bascules par fenetre**. Un 4/4 comme un 0/4 seraient
ici du bruit.

---

## 3. L'ecart avec la source, et son explication

### 3.1 Pourquoi nos chiffres sont plus bas que les siens

Sur sa fenetre : +28,80 % / 1,45 / -16,96 % contre +33,80 % / 1,66 / -13,60 %.
Cinq causes, toutes identifiees, aucune ne met en cause sa sincerite :

| cause | sens | ampleur estimee |
|---|---|---|
| **CFD indice prix, sans dividendes** — QQQ verse ~0,5 %/an | defavorable | ~0,5 pt de CAGR |
| **XAUUSD spot vs GLD** — profils de frais differents | indetermine | faible |
| **Close D1 broker != close cash 16:00 ET** — le CFD cote plus longtemps, les bascules ne tombent pas exactement aux memes jours | indetermine | quelques bascules deplacees |
| **Fenetre non identique** — nous ne pouvons pas commencer avant 2022-05 (warmup MM200 sur 5 ans de donnees) | indetermine | — |
| **Bascules : 3,25/an chez nous contre 5,3/an annoncees** | — | signe que nos series ne bougent pas au meme rythme que QQQ/GLD |

L'ordre de grandeur est reproduit. La difference est de la nature d'un ecart
d'instrument, pas d'un ecart de methode.

### 3.2 Ce que la source dit de vrai, et ce qu'elle survend

**Vrai, et confirme sur nos donnees :**
- la regle bat le buy & hold sur nos 4,3 ans, sur les trois metriques ;
- elle reduit le drawdown de facon substantielle (-17 % contre -25 %) ;
- elle est simple, ancienne, publiee, sans parametre a torturer ;
- son caveat sur GLD est **exact** — nous le confirmons independamment (§2.4).

**Survendu, ou non demontre :**
- presenter +33,8 % de CAGR sans afficher, en face, le **+30,4 % du simple buy &
  hold NASDAQ sur la meme fenetre** donne une impression trompeuse de valeur
  ajoutee. Le gain reel est en **drawdown**, pas en rendement ;
- le Sharpe de 1,66 se compare a **1,70 pour un melange 50/50 sans aucun signal** ;
- la validation sur 50 ans est mentionnee mais n'est pas ce qui produit les chiffres
  du tableau : ceux-ci viennent d'une fenetre de 3,5 ans sans marche baissier.

---

## 4. VERDICT

# NON CONCLUSIF (donnees insuffisantes)

Ce n'est pas une echappatoire : c'est la seule conclusion que l'echantillon
supporte, et elle etait annoncee comme l'issue la plus probable en Phase 1
(ANALYSIS §4), **avant** toute mesure.

### 4.1 Pourquoi ni "edge confirme" ni "pas d'edge"

**Pourquoi pas `EDGE CONFIRME`** :

1. **14 bascules.** Aucune statistique par episode n'est possible.
2. L'ecart avec le buy & hold **n'est pas significatif** : IC 95 % du differentiel
   de Sharpe [-0,40 ; +0,97], 19 % de tirages bootstrap defavorables (§2.7).
3. **Hors 2022, l'avantage de rendement disparait** (-1,64 pt de CAGR) et l'avantage
   de Sharpe tombe a +0,09. Tout tient a 181 jours (§2.8).
4. Un **50/50 naif fait aussi bien** — la strategie est defavorisee dans 55,5 % des
   tirages bootstrap sur le Sharpe (§2.1, §2.7).
5. La MM200 **ne predit pas le rendement** (t = 0,56, §2.9).
6. La **jambe or n'apporte rien** en rendement ajuste du risque ; la variante cash
   fait mieux (§2.4). La regle telle qu'enoncee n'est donc pas celle qui produit le
   resultat.
7. **Aucun regime de stress dans l'echantillon.** L'auteur valide sur ~50 ans, nous
   sur 4,3, sans dot-com ni 2008. C'est precisement la que ce type de filtre est
   cense gagner sa vie.

**Pourquoi pas `PAS D'EDGE`** :

1. Elle **bat effectivement** les trois buy & hold simples sur la fenetre complete,
   sur les trois metriques simultanement. Contrairement a s01, ce n'est pas "deux
   fois moins bien que le hasard".
2. Le **mecanisme est reel et mesurable** : la MM200 separe deux regimes de
   volatilite dans un rapport de **1,96x** (18,1 % contre 35,5 %). Ce n'est pas du
   bruit, c'est le fait le plus solide du test.
3. Le **plateau de parametres est lisse et monotone** (§2.10) — 11/12 des
   configurations battent le Sharpe du buy & hold la ou le hasard en donnerait 0,6.
   Ce n'est pas le profil d'un sur-ajustement.
4. Le **coefficient de reduction du drawdown est constant** sur toutes les
   configurations, ce qui est coherent avec un mecanisme et non avec une chance.

Conclure `PAS D'EDGE` serait aussi malhonnete que conclure `EDGE CONFIRME`. Les
donnees ne tranchent pas.

### 4.2 Verdict architectural separe — celui-ci, lui, est ferme

# LE CONTRAT NE COUVRE PAS CETTE FAMILLE DE STRATEGIES

Ce n'est pas une limite de cette strategie, c'est une limite de la plateforme, et
elle est **demontree, pas supposee** :

```
walk-forward ancre, jambe risk  (NASDAQ) : 1 trade sur 5 ans
walk-forward ancre, jambe hedge (XAUUSD) : 2 trades sur 5 ans
```

Cause : `Signal(entry, stop, target)` suppose une strategie **episodique** — entree,
invalidation par un niveau de prix, objectif. `core/backtest/engine.py` ne connait
que trois sorties : SL, TP, fin de tranche. Il n'accepte **aucun ordre de sortie sur
signal**.

Or Trend core est une strategie **d'allocation** : toujours investie, changeant
d'instrument, sortant uniquement sur retournement de regime — qui n'est ni un niveau
de prix, ni une duree fixe. **Aucun stop ne peut representer sa sortie.**

Nous n'avons pas bricole un faux stop pour satisfaire le validateur. `strategy.py`
declare son stop pour ce qu'il est — un plancher de catastrophe a 8xATR impose par
R3, hors grille de recherche, ecrit dans le champ `reason` de chaque signal — et les
resultats moteur sont publies avec l'avertissement qu'ils ne mesurent pas la
strategie.

**Ce que ca coute a la plateforme** : toute la famille rotation / commutation de
regime lui echappe, dont **2 des 5 survivants de cette source** (Trend core et
Rotation 52 semaines). Ce sont aussi les deux seuls dont l'auteur publie des
chiffres.

**Ce qu'il faudrait ajouter** (hors de mon perimetre, `core/` interdit) :
1. un **signal de sortie** — ou un `exit_signals` en parallele de `generate_signals` ;
2. un **backtest multi-symbole a exposition unique** (une seule position vivante a
   travers N instruments) ;
3. rendre `stop` optionnel quand la strategie declare un mode ALLOCATION, plutot que
   d'imposer R3 a une famille pour laquelle il n'a pas de sens ;
4. des metriques de **courbe d'equity** (CAGR, Sharpe, DD en %) a cote des metriques
   en R, et des **benchmarks buy & hold** integres — aujourd'hui le harnais ne peut
   pas repondre au critere n1 de sa propre methodologie.

### 4.3 Anomalie signalee dans `core/` — non exploitee ici

`core/backtest/engine.py` ~ligne 224 : quand `max_hold_bars` est renseigne et que la
sortie temporelle se declenche, `exit_at = idx[limit-1]` mais `exit_price =
last_close`, c'est-a-dire `closes[n-1]` — la fin de **tranche**, pas la fin de
**detention**. C'est un lookahead de la meme famille que le bug `closes[-1]`
documente en en-tete du module.

Aucune de nos mesures n'emploie `max_hold_bars` ; rien ici n'en depend. A verifier
par le proprietaire de `core/`.

### 4.4 Recommandation

**Ne pas promouvoir en PAPER.** Statut du manifest : `RESEARCH`.

Non pas parce que la strategie est mauvaise — elle ne l'est probablement pas — mais
parce que **nous ne pouvons pas la juger** avec 4,3 ans, 14 bascules et un seul
episode baissier, et parce que la plateforme ne sait de toute facon pas l'executer.

**L'action qui debloquerait ce verdict est une action sur les donnees, pas sur le
code** : acquerir de l'historique long (Dukascopy, ou series ETF gratuites remontant
aux annees 1990) pour couvrir 2000-2002 et 2007-2009. C'est le seul test qui
separerait "filtre de risque qui marche" de "artefact de 2022". Tant qu'il manque,
ce verdict restera `NON CONCLUSIF`, quel que soit le nombre de backtests qu'on
empile sur 2021-2026.

---

## 5. Ce qui est transferable vers la strategie Adrian

Meme sans verdict tranche, six acquis solides.

1. **La MM200 est un filtre de VOLATILITE, pas de rendement.** Mesure : moyennes
   indistinguables (t = 0,56), volatilites dans un rapport de **1,96x** (18,1 % vs
   35,5 %). C'est le resultat le plus robuste du test — il repose sur 1128
   observations, pas sur 14. **Utilisable directement comme filtre de modulation du
   risque** (reduire la taille sous la MM200), sans rien parier sur la direction.
   C'est la lecture correcte de ce que fait Trend core.

2. **Le benchmark 50/50 naif doit rejoindre l'ablation du spread et le controle
   long/short dans les diagnostics obligatoires.** Il a change le verdict ici : sans
   lui, on aurait retenu "bat le buy & hold NASDAQ" comme un succes. Avec lui, on
   voit que le signal n'apporte rien au-dela de la diversification. Coherent avec
   `docs/METHODOLOGY.md` §7 (DeMiguel-Garlappi-Uppal). **Cout : trois lignes.**

3. **Le decoupage temporel est aussi important que le decoupage par sens.** Le
   controle long/short etait degenere ici (100 % long) ; c'est le retrait de 2022 qui
   a revele la concentration. **Retirer l'annee la plus favorable doit devenir
   systematique**, au meme titre que le controle directionnel.

4. **L'attribution par jambe doit se faire par unite de temps de detention**, pas en
   PnL total. En PnL total, la jambe NASDAQ "fait 88,9 % du resultat" — vrai mais
   trivial, elle occupe 76 % du temps. Ramene a l'annee de detention (+27,3 % contre
   +10,2 %), on voit que la jambe or est **mauvaise dans l'absolu** (moins bien que
   le buy & hold or a +20,5 %). Deux lectures opposees des memes chiffres.

5. **Annoncer le resultat previsible d'un diagnostic AVANT de le lancer.** L'ablation
   du spread etait ecrite comme un non-evenement en Phase 1 avec le calcul a l'appui
   (0,017 % par bascule, 3 bascules/an). Elle l'a ete. Ca evite de presenter un
   resultat arithmetiquement certain comme une decouverte — et ca rend credibles les
   diagnostics dont l'issue etait *reellement* ouverte.

6. **Une strategie qui ne rentre pas dans le contrat est une information sur le
   contrat.** Le reflexe naturel est de deformer la strategie jusqu'a ce qu'elle
   passe le validateur. Le walk-forward a 1 trade est plus utile que n'importe quel
   chiffre qu'un faux stop aurait produit : il rend la limite architecturale
   **mesurable** au lieu de la laisser en opinion.

**Negatif egalement utile** : inutile de re-tester la bascule vers l'or comme
diversifiant tactique dans `s90_adrian_synthesis`. Sur 2021-2026, entrer dans l'or
sur signal MM200 rapporte **moins de la moitie** de ce que rapporte l'or detenu en
permanence. Si l'or doit servir, ce sera en allocation permanente ou en ponderation
fixe — pas en bascule declenchee par un signal actions.

---

## 6. Limites de ce test

1. **La limite n1, irreductible : 4,3 ans exploitables, un seul episode baissier
   (181 jours en 2022), et il porte a lui seul tout l'avantage.** L'auteur valide sur
   ~50 ans incluant 2000-2002 et 2007-2009. **Nous ne pouvons pas tester ce que sa
   strategie est censee faire.** Aucun raffinement de code ne compense ca.

2. **14 bascules.** En dessous de tout seuil. Toute la lecture repose sur des
   rendements journaliers, qui mesurent bien le profil de risque mais mal la qualite
   des decisions de bascule.

3. **Le swap / financement n'est pas modelise.** C'est la limite la plus penalisante
   ici, bien plus que le spread : la strategie est investie **100 % du temps** en CFD
   indice et or spot. Un cout de portage de 2-4 %/an transformerait "+3,01 pt vs buy
   & hold" en un ecart nul ou negatif. **Un buy & hold d'ETF au comptant ne paie pas
   ce cout ; la strategie en CFD, si.** Ce point suffirait a lui seul a annuler
   l'avantage mesure.

4. **Instruments substitues.** NASDAQ CFD n'est pas QQQ (pas de dividendes), XAUUSD
   n'est pas GLD, et le close D1 du broker n'est pas le close cash 16:00 ET. Nos
   3,25 bascules/an contre ses 5,3 annoncees le montrent : nous ne testons pas
   exactement la meme serie.

5. **Le moteur commun n'a pas pu servir** (§4.2). La mesure principale vient d'une
   comptabilite d'equity ecrite pour ce test. Elle est simple et verifiable, mais
   elle n'a pas les annees de bugs corriges du moteur commun — c'est un risque
   d'erreur non nul, honnetement declare. Mitigation : la convention d'execution
   (decision a t-1, ouverture a t, rendement open->open) est la plus defavorable
   raisonnable, et la causalite de la regle est verifiee independamment par R1 sur
   `strategy.py`.

6. **Une seule formalisation.** Bande morte en pourcentage de la MM ; d'autres filtres
   anti-oscillation (confirmation sur N jours, MM exponentielle, pente de la MM)
   donneraient d'autres chiffres. 12 cellules autour d'**une** definition, pas
   l'espace des definitions.

7. **Pas de taux sans risque.** La variante cash est remuneree a 0 %, ce qui la
   sous-estime de ~1 pt de CAGR sur 2023-2026. Elle bat deja la regle sur le Sharpe
   avec ce handicap.

8. **R5 (conformance backtest/live) non executable** : `core/validation/conformance.py`
   n'existe pas dans le depot. Mitigation structurelle : `on_bar()` appelle
   litteralement `precompute()` + `generate_signals()` et ne retient que la decision
   de la barre courante — il n'existe pas deux implementations pouvant diverger. Ce
   n'est pas une preuve, c'est une garantie de construction.

9. **R1 lance hors CLI.** `python -m core.validation.causality --strategy
   s04_aipathways_trendcore --save` refuse de tourner : la CLI exige `len(df) >= 2000`
   barres (causality.py:223) et nous en avons 1331 en D1 — seuil calibre pour du H1.
   `backtests/run_causality.py` appelle la **meme fonction check() du meme module**
   sans le garde-fou de taille, sur 24 points de grille au lieu d'un seul. Sortie
   archivee dans `backtests/causality.txt`. `core/` n'a pas ete modifie.

10. **R4 (magic number) non inscrit au registre.** `MAGIC_NUMBER = 130004` est dans la
    plage explicitement reservee aux sources externes (130003-130009) et n'entre en
    collision avec aucune entree existante, mais `core/contracts/MAGIC_REGISTRY.md`
    n'a pas ete edite : `core/` est interdit. **A inscrire par le proprietaire de
    core/.**

---

## 7. Fichiers produits

| Fichier | Contenu |
|---|---|
| `research/ANALYSIS.md` | Phase 1 — regle, reproductibilite, problemes de contrat et d'echantillon, criteres d'invalidation fixes a l'avance |
| `strategy.py` | Implementation `StrategyModule`, R1-R10, avec l'avertissement sur le stop |
| `manifest.yaml` | Manifest, grille 12 configurations |
| `backtests/run_causality.py` | R1 hors CLI (24 points de grille) |
| `backtests/causality.txt` | **Sortie R1 archivee — PASSE, 0 fuite sur 96 comparaisons** |
| `backtests/run_wf.py` | Walk-forward ancre, 2 jambes |
| `backtests/anchored_wf.txt` | Sortie walk-forward — **1 a 2 trades : la demonstration de §4.2** |
| `backtests/run_analysis.py` | Comptabilite d'equity — la mesure qui fait foi |
| `backtests/equity_analysis.txt` | Benchmarks, attribution par jambe, variante cash, ablation du spread, controle long/short, separation de regime, plateau, stabilite annuelle, hors echantillon, bootstrap, fenetre de l'auteur |
| `research/VERDICT.md` | Ce document |

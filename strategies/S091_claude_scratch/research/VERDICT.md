# Verdict — s91_claude_scratch « Asian-window fade » (H91)

Source : **conception autonome**. Aucune source externe, aucun claim à confronter.
Données : MT5 Swissquote, H1, 2021-07-18 → 2026-08-16, 31 593-31 594 barres/instrument.
Grille : **54 configurations × 6 instruments = 324 cellules**.
R1 (causalité) : **PASSÉ**, vérifié sur 24 points de la grille — pas seulement le défaut.
Effectif : **947 trades** (groupe éligible, cellule par défaut, plein échantillon),
**82 trades hors échantillon en médiane** par instrument éligible.

> **Note de re-vérification.** `core/` a évolué pendant cette session (commits
> `7ba94e9` gardien de causalité couche indicateur, `396d7e1` slippage +
> illusion in-sample + fenêtre glissante). **Tous les chiffres de ce document
> ont été régénérés contre le `core/` courant** et sont identiques au chiffre
> près : `slippage_pips` vaut 0 par défaut et le mode reste `anchored`, donc les
> changements sont rétrocompatibles.
>
> Deux conséquences ont été traitées, pas contournées :
> 1. Le nouveau gardien n'inspecte la **couche indicateur** que si `precompute`
>    renvoie un `DataFrame` ; il retourne silencieusement sur un objet opaque.
>    Ma version initiale renvoyait un `dict` et **échappait donc au contrôle**.
>    `precompute` a été refactorisé pour renvoyer un `DataFrame` — R1 inspecte
>    désormais réellement `close`, `z`, `atr` et `hour` (§2.9, aucune fuite).
> 2. Le slippage, jusque-là listé comme limite non chiffrée, est maintenant
>    **mesuré** (§2.10).

---

## 1. Ce que j'avais affirmé, et ce que j'avais déclaré comme réfutation

### 1.1 L'hypothèse (ANALYSIS.md §3, figée avant tout backtest)

> Dans la fenêtre de faible liquidité (heure serveur 22h–06h), une extension de
> prix sur H1 n'est pas de l'information mais du bruit de carnet mince, et elle
> se rétracte partiellement. Cet effet n'existe que pour les paires dont aucune
> devise n'a de session domestique à ce moment-là. Pour les paires JPY, cette
> même fenêtre est la session de Tokyo — donc du vrai flux — et l'effet doit y
> être absent ou inversé.

Elle comporte **deux affirmations séparables** :
- **(a)** une extension se rétracte → mean-reversion ;
- **(b)** cet effet est **propre à la fenêtre de faible liquidité**.

### 1.2 L'économie calculée a priori (ANALYSIS.md §4)

Sur la tranche d'entraînement uniquement : dérive brute **+2,66 pips** contre un
spread aller-retour moyen de **2,30 pips** → marge **+0,36 pips, soit 16 % au-dessus
du coût**. J'avais écrit, avant de coder : *« Ce n'est pas une marge, c'est un
liseré. Je m'attends à un résultat nul ou marginal hors échantillon. »*

### 1.3 Mes conditions de falsification, déclarées à l'avance

| # | Condition déclarée | Résultat mesuré | Déclenchée ? |
|---|---|---|---|
| **F1** | Espérance brute à spread nul ≤ 0 sur les éligibles | **+0,0818 R/trade** (324 cellules) | **non** |
| **F2** | Les paires JPY ne font pas moins bien que les éligibles | éligibles +0,0019 vs JPY **−0,1595** | **non** |
| **F3** | STRICT ≤ hasard (54 × 0,05 × 4 = **10,8**) | **1 STRICT observé** | **OUI** |
| **F4a** | Un seul sens porte le résultat | 3 éligibles sur 4 en asymétrie long/short | **OUI (partiel)** |
| **F4b** | Un instrument > 60 % du total positif | max 33 % (USDCAD) | non |
| **F5** | Effectif OOS médian < 20 trades | **82 trades** | non |

**F3 est déclenchée. J'avais écrit que F3 signifie « H91 réfutée ». Je m'y tiens.**

---

## 2. Ce que nous mesurons

### 2.1 Walk-forward ancré — le critère principal

| instrument | groupe | STRICT | attendu par hasard | TIER 1 | trades OOS (médiane) | moy OOS sur la grille |
|---|---|---|---|---|---|---|
| EURUSD | éligible | **0** | 2,7 | 24 | 84 | **−0,85 R** |
| USDCHF | éligible | **0** | 2,7 | 19 | 80 | **−1,64 R** |
| USDCAD | éligible | **1** | 2,7 | 11 | 73 | **−0,48 R** |
| AUDUSD | éligible | **0** | 2,7 | 0 | 136 | **−1,57 R** |
| **TOTAL ÉLIGIBLE** | | **1** | **10,8** | 54 | | |
| USDJPY | contrôle | 0 | 2,7 | 1 | 127 | −4,65 R |
| EURJPY | contrôle | 0 | 2,7 | 0 | 72 | −3,79 R |
| **TOTAL CONTRÔLE** | | **0** | **5,4** | 1 | | |

**Le point décisif : 1 réussite STRICT là où le pur hasard en produirait ~10,8.**
Comme pour s01 (19 contre 45), la grille fait **franchement moins bien que le
hasard**. C'est la signature d'une espérance négative, pas d'un edge noyé dans le
bruit.

Les effectifs sont **bons** (73 à 136 trades hors échantillon par instrument, au
double du seuil de crédibilité de 20). Le négatif est **mesuré**, pas subi.

La moyenne OOS sur toute la grille est négative sur **les quatre** instruments
éligibles. Les 54 « TIER 1 » ne sauvent rien : Tier 1 ne juge que la dernière
fenêtre d'entraînement.

### 2.2 Robustesse — les meilleures cellules sont isolées

| instrument | meilleure cellule | moy OOS | trades | voisins positifs (1 paramètre déplacé) |
|---|---|---|---|---|
| EURUSD | rr1.5_sl3.0_etroite_z2.0 | +1,92 | 64 | **3/7** |
| USDCHF | rr1.5_sl3.0_large_z1.5 | +2,96 | 168 | **1/7** |
| USDCAD | rr1.5_sl3.0_etroite_z1.5 | +3,10 | 131 | **2/7** |
| AUDUSD | rr1.5_sl3.0_etroite_z1.5 | +1,49 | 187 | **2/7** |

Si le signe était aléatoire on attendrait ~3,5/7. On observe 1 à 3 sur 7 :
**en dessous du hasard**. Les meilleures cellules ne sont pas des sommets, ce
sont des accidents.

### 2.3 Ablation du spread — le résultat le plus informatif

Mêmes signaux, même moteur, `spread_pips` réel → 0, sur **toutes** les 324 cellules :

| | R/trade réel | R/trade à spread nul | coût | cellules positives (réel) | cellules positives (nul) |
|---|---|---|---|---|---|
| EURUSD | +0,0698 | +0,1344 | +0,0646 | 35/54 | 49/54 |
| USDCHF | +0,0187 | +0,1031 | +0,0844 | 29/54 | 52/54 |
| USDCAD | −0,0265 | +0,0718 | +0,0982 | 17/54 | 43/54 |
| AUDUSD | −0,0544 | +0,0177 | +0,0721 | 5/54 | 36/54 |
| **ÉLIGIBLES (4)** | **+0,0019** | **+0,0818** | **+0,0798** | **86/216 (40 %)** | **180/216 (83 %)** |
| CONTRÔLE JPY (2) | −0,1595 | −0,1010 | +0,0586 | 3/108 | 13/108 |

**C'est le résultat central de ce dossier, et il diffère de celui de s01.**

Sur s01, à spread nul, le signal était à −0,008 R/trade et 27/56 cellules
positives : une pièce non biaisée, rien à sauver. **Ici, à spread nul, le signal
est à +0,0818 R/trade et 180/216 cellules positives (83 %), sur les quatre
instruments éligibles simultanément.** Ce n'est pas une pièce.

Et pourtant, à spread réel, l'espérance retombe à **+0,0019 R/trade** — zéro à
la troisième décimale. **Le péage (+0,0798 R/trade) consomme 98 % du signal brut.**

Ce n'est donc pas « il n'y a pas d'edge ». C'est « il y a un edge, et il vaut
exactement le prix du spread ». Les deux diagnostics appellent des décisions
opposées, et c'est précisément pour les distinguer que l'ablation existe.

### 2.4 La composante horaire — fait-elle quelque chose ?

Contrôle **post-hoc** (`backtests/window_control.txt`), géométrie figée, spread
nul, fenêtres témoins injectées hors manifest :

| groupe | H91 22-06h | H91 23-04h | ctrl 08-12h | ctrl 13-17h | **ctrl 24h/24** |
|---|---|---|---|---|---|
| **ÉLIGIBLES** | **+0,0600** | **+0,0978** | −0,0038 | +0,0101 | **+0,0089** |
| contrôle JPY | −0,1211 | −0,1149 | −0,0417 | −0,0002 | −0,0778 |

La même règle appliquée **24h/24** donne +0,0089 R/trade : rien. Filtrée par la
porte horaire, elle donne +0,060 à +0,098. **L'apport de la porte est de +0,051 à
+0,089 R/trade brut.** La composante **(b)** de H91 n'est pas décorative.

Cette comparaison est faite **à instrument constant**, donc la tendance de la
paire — le confondant du §2.6 — s'y annule.

### 2.5 Et surtout : cet effet horaire survit-il hors échantillon ?

C'est la question qui compte, puisque H91 a été formée sur le train.
`backtests/window_oos.txt`, groupe éligible, **spread nul** :

| fenêtre | train (0-60 %) | **test (60-100 %)** |
|---|---|---|
| H91 22-06h | +0,0926 | **+0,0406** |
| H91 23-04h | +0,1721 | **+0,0517** |
| témoin 24h/24 | +0,0224 | **−0,0128** |
| **apport de la porte 22-06h** | +0,0702 | **+0,0534** |
| **apport de la porte 23-04h** | +0,1498 | **+0,0645** |

**L'effet horaire survit hors échantillon.** Il perd la moitié de son amplitude
(shrinkage attendu, l'hypothèse ayant été formée sur le train), mais il reste
franchement positif alors que la version non filtrée passe **négative**.

Les mêmes cases, **à spread réel** :

| fenêtre | train | **test** |
|---|---|---|
| H91 22-06h | +0,0212 | **−0,0344** |
| H91 23-04h | +0,0978 | **−0,0231** |
| témoin 24h/24 | −0,0424 | **−0,0858** |

**Hors échantillon et spread compris, toutes les variantes sont perdantes.**
L'edge brut OOS (+0,041 à +0,052 R/trade) est inférieur au péage (+0,059 à
+0,098 R/trade selon la paire). L'écart est d'environ **un facteur 1,5**.

### 2.6 Le confondant — pourquoi je ne revendique PAS F2

F2 n'a pas été déclenchée : les paires JPY font effectivement bien pire
(−0,1595 contre +0,0019). Tentation : y voir la confirmation du mécanisme de
session. **Je ne peux pas.**

| instrument | dérive 5,1 ans (pips) | R/trade LONG | R/trade SHORT | l'asymétrie suit-elle la tendance ? |
|---|---|---|---|---|
| EURUSD | −238 | +0,0418 | −0,0404 | non |
| USDCHF | −1 055 | +0,0235 | −0,0730 | non |
| USDCAD | **+1 265** | +0,0212 | −0,1373 | **OUI** |
| AUDUSD | −315 | −0,0780 | −0,0271 | OUI |
| **USDJPY** | **+4 932** | −0,0633 | **−0,2005** | **OUI** |
| **EURJPY** | **+5 443** | −0,0830 | **−0,2336** | **OUI** |

Les deux paires JPY ont **de loin** les plus fortes dérives de l'échantillon
(+4 932 et +5 443 pips, soit 4 à 5 fois la suivante) : c'est le carry yen
2021-2024. Une règle qui **vend** les extensions d'une paire en tendance
haussière violente perd massivement du côté short — et c'est exactement ce qu'on
observe (−0,20 et −0,23 R/trade en short).

**L'échec des paires JPY est entièrement explicable par la tendance, sans
invoquer la session de Tokyo.** L'explication concurrente est plus simple et
déjà documentée par le projet (fait #7). F2 non déclenchée n'apporte donc
**aucun appui** à H91 : elle est confondue. Je l'écris parce que le résultat
allait dans mon sens, et que c'est précisément là qu'il faut se méfier.

*(Le seul appui non confondu au clivage vient du §2.4-2.5 : les comparaisons
inter-horaires à instrument constant, où la tendance s'annule.)*

### 2.7 F4a — asymétrie directionnelle

Sur les 324 cellules : EURUSD, USDCHF et USDCAD sont **positifs en long et
négatifs en short** (écarts +0,082, +0,097, +0,159 R/trade). Pour EURUSD et
USDCHF cette asymétrie **ne suit pas** la tendance de la paire, donc elle n'est
pas seulement du beta de régime — mais elle reste une asymétrie non expliquée,
et un système dont un seul sens fonctionne n'est pas un système.

### 2.8 Stabilité annuelle — groupe éligible agrégé, cellule par défaut

| année | R cumulé | trades | R/trade |
|---|---|---|---|
| 2021 | −7,2 | 70 | −0,1033 |
| 2022 | **+7,6** | 161 | +0,0471 |
| 2023 | −0,2 | 159 | −0,0014 |
| 2024 | **−18,1** | 182 | −0,0997 |
| 2025 | **−13,5** | 219 | −0,0616 |
| 2026 | −6,5 | 156 | −0,0414 |
| **TOTAL** | **−37,9** | **947** | −0,0400 |

**Une seule année positive sur six**, et les trois dernières sont les pires.
Aucune stabilité. C'est cohérent avec l'échec du walk-forward, dont les tranches
de test tombent justement sur 2024-2026.

### 2.9 R1 — la couche indicateur, désormais réellement inspectée

| coupure | T | signaux (df complet) | signaux (df tronqué) | verdict |
|---|---|---|---|---|
| 60 % | 18 955 | 134 | 134 | OK |
| 70 % | 22 115 | 175 | 175 | OK |
| 80 % | 25 274 | 231 | 231 | OK |
| 90 % | 28 433 | 266 | 266 | OK |

Aucune section « FUITES AU NIVEAU DES INDICATEURS » : les quatre colonnes
(`close`, `z`, `atr`, `hour`) sont strictement identiques entre calcul sur
historique complet et calcul sur historique tronqué, aux quatre coupures. Rien
d'étonnant — tout est `rolling` — mais c'est désormais **vérifié** plutôt que
supposé. Et le sweep de 24 points de grille (`anchored_wf.txt`) confirme que
l'invariant tient ailleurs qu'au défaut.

*Point méthodologique à retenir* : le gardien renvoyait « PASSÉ » sur ma version
initiale **sans jamais regarder les indicateurs**, parce que `precompute`
renvoyait un `dict`. Un « R1 PASSÉ » n'est aussi fort que la surface qu'il
couvre. Renvoyer un `DataFrame` n'est pas cosmétique : c'est ce qui place la
stratégie sous le contrôle du gardien plutôt qu'à côté.

### 2.10 Sensibilité au slippage — la limite, chiffrée

`InstrumentSpec.slippage_pips` (coût de bord payé aux deux extrémités, toujours
défavorable). Grille complète, groupe éligible :

| slippage | 0,0 | 0,1 | 0,2 | 0,3 | 0,5 pip |
|---|---|---|---|---|---|
| plein échantillon | **+0,0019** | −0,0048 | −0,0114 | −0,0180 | **−0,0310** |
| **tranche de test (60-100 %)** | **−0,0295** | −0,0363 | −0,0430 | −0,0497 | **−0,0629** |

Le verdict est donc établi **à slippage nul, c'est-à-dire dans l'hypothèse la
plus favorable possible**. Un slippage réaliste de 0,2-0,5 pip en FX liquide
retire encore 0,013 à 0,033 R par trade. **Aucune valeur du balayage ne ramène
les éligibles à l'équilibre hors échantillon** ; la plus favorable les y laisse
déjà à −0,030.

Autrement dit : la limite « slippage non modélisé » ne protégeait aucune
conclusion, elle en dissimulait l'ampleur. Chiffrée, elle **renforce** le verdict.

### 2.11 L'illusion in-sample — ce qu'un backtest naïf aurait affiché

Diagnostic apporté par le nouveau `anchored_wf` : la meilleure configuration
*plein échantillon* (optimisée ET mesurée sur les 5,1 ans) face à la somme des
seules tranches hors échantillon.

| instrument | meilleure config plein échantillon | illusion | honnête | perdu |
|---|---|---|---|---|
| EURUSD | rr1.5_sl3.0_etroite_z2.0 | **+30,24** | +7,67 | **75 %** |
| EURUSD (2e) | rr1.5_sl3.0_large_z2.0 | +23,50 | +6,86 | 71 % |
| EURUSD (3e) | rr1.0_sl3.0_etroite_z2.0 | +22,95 | +1,76 | 92 % |
| USDCHF | rr1.0_sl2.0_large_z2.5 | +7,02 | **−1,59** | **123 %** |
| USDCHF (2e) | rr1.5_sl2.0_large_z2.0 | +6,64 | −8,57 | 229 % |

**75 % à 229 % du rendement apparent disparaît** une fois l'optimisation
retirée. Sur USDCHF le « perdu » dépasse 100 % : la config bascule en négatif.

C'est la capture d'écran qu'aurait produite ce travail sans walk-forward :
« EURUSD +30 R sur 5 ans ». Le chiffre honnête est +7,67 R, et il ne survit ni
au déplacement de config (§2.2), ni au critère STRICT (§2.1), ni au slippage
(§2.10).

---

## 3. L'écart, et son explication

### 3.1 L'écart avec ma propre prévision a priori

J'avais annoncé une marge de **+16 % au-dessus du coût**. La mesure donne
**−2 %** en plein échantillon (+0,0019 contre +0,0798 de péage) et **négatif**
hors échantillon. Mon estimation a priori était **optimiste d'environ 20 points**.

La cause est identifiée et je l'avais moi-même désignée comme limite en Phase 1
(ANALYSIS.md §7.2) : la dérive à horizon fixe de 8 barres **surestime** ce qu'une
structure stop/cible capture réellement. Trois raisons :

1. `run_walk_forward` ne transmet pas `max_hold_bars`, et une stratégie ne peut
   pas exprimer de sortie temporelle (elle n'émet que `entry`/`stop`/`target`).
   Les positions **traversent l'ouverture de Londres**, où la volatilité triple
   — c'est-à-dire exactement le moment où le mécanisme invoqué cesse de valoir.
2. Le moteur applique la règle défavorable « si stop et cible sont dans la même
   barre, le stop l'emporte ». La dérive moyenne ignore cette pénalité.
3. La dérive moyenne est portée par une queue de grands retours ; un stop à
   2,5 ATR coupe la trajectoire avant.

**Leçon transférable : une dérive à horizon fixe est un mauvais estimateur de
l'espérance d'un trade à stop et cible. Elle donne la borne haute.**

### 3.2 Pourquoi la stratégie perd, mécaniquement

L'ablation répond sans ambiguïté : **le signal existe, le péage le mange.**

```
    edge brut hors échantillon   ≈  +0,041 à +0,052 R/trade
    péage H1 forex               ≈  +0,059 à +0,098 R/trade
                                    ------------------------
    net                             négatif, sur toutes les variantes
```

Il manque un facteur ~1,5. Sur H1 en forex majeur, ce facteur n'est pas
récupérable :
- **Élargir le stop** ne le donne pas : la grille va déjà jusqu'à 3,0 × ATR,
  et le drag ne baisse que linéairement pendant que le signal se dilue.
- **Monter en H4** diviserait le péage par deux, mais **détruirait le
  mécanisme** : une barre H4 chevauche la frontière de session, la porte
  horaire n'existe plus. Ce n'est pas une option, c'est un autre test.
- **Changer de broker** : à spread strictement nul le système gagne, mais aucun
  broker retail n'offre zéro. Il faudrait diviser le spread par ~2, ce qui est
  hors de portée sur un compte Swissquote 1 000 CHF.

---

## 4. VERDICT

# PAS D'EDGE

**H91 est réfutée selon ma propre condition F3, déclarée avant le premier
backtest** : 1 réussite STRICT sur les quatre instruments éligibles contre
**10,8 attendues par pur hasard**.

Justification, par ordre de force décroissante :

1. **1 STRICT contre ~10,8 attendues** sur 216 cellules éligibles — onze fois
   moins bien que le hasard. Même signature que s01.
2. **Moyenne OOS négative sur les quatre instruments éligibles** (−0,48 à
   −1,64 R), sur toute la grille.
3. **Hors échantillon et spread compris, toutes les variantes de fenêtre sont
   perdantes** (−0,023 à −0,086 R/trade).
4. **Les meilleures cellules sont isolées** : 1 à 3 voisins positifs sur 7, en
   dessous du hasard (3,5/7).
5. **Une seule année positive sur six**, les trois dernières étant les pires.
6. **Les effectifs sont suffisants** (73-136 trades OOS par instrument) : c'est
   un négatif **mesuré**, pas un « on ne sait pas ».
7. **F4a partiellement déclenchée** : trois éligibles sur quatre ne gagnent que
   d'un seul côté.

**Recommandation : ne pas promouvoir en PAPER. Statut du manifest maintenu à
`RESEARCH`.**

### 4.1 Sous-verdict séparé, et je m'interdis de le confondre avec le premier

**L'effet horaire lui-même : `NON CONCLUSIF, mais réel et mesuré`.**

Ce n'est pas un lot de consolation, c'est une mesure distincte :

- **F1 non déclenchée** : à spread nul, +0,0818 R/trade et **180/216 cellules
  positives (83 %)**, sur les quatre éligibles simultanément. Ce n'est pas une pièce.
- La porte horaire apporte **+0,053 R/trade brut hors échantillon** contre la
  même règle appliquée 24h/24 — laquelle est **négative** hors échantillon.
- Cette comparaison est faite **à instrument constant**, donc immunisée contre
  le confondant de tendance qui invalide F2.

Autrement dit : **l'affirmation (b) de H91 — « la réversibilité d'un écart
dépend de la liquidité de la session » — reçoit un appui mesuré qui survit hors
échantillon. L'affirmation (a)+(b) comme stratégie exécutable est réfutée par le
péage.**

Ce sous-verdict **ne rachète rien** : il ne rend pas la stratégie promouvable,
et il reste soumis à la contamination déclarée en §5.1. Il indique seulement où
chercher.

---

## 5. Ce qui est transférable vers `s90_adrian_synthesis`

### 5.1 Le chiffre à retenir : la frontière est à un facteur 1,5

C'est le livrable le plus utile de ce dossier. Le mean-reversion en fenêtre de
faible liquidité produit, hors échantillon et hors coûts, **+0,04 à +0,05 R par
trade** sur les majeures forex. Le péage H1 est de **+0,06 à +0,10 R par trade**.

**Il ne manque pas un edge : il manque un facteur ~1,5 sur le rapport
signal/coût.** Toute suite utile doit attaquer ce rapport, et une seule des trois
voies reste ouverte :

| voie | effet sur le rapport | verdict |
|---|---|---|
| élargir le stop | linéaire, mais dilue le signal autant | ❌ déjà exploré (jusqu'à 3 ATR) |
| monter en timeframe | péage ÷2 | ❌ **détruit le mécanisme** (H4 chevauche la frontière de session) |
| **instrument à faible péage relatif** | direct | ⚠️ **seule voie ouverte** |

Concrètement : un instrument dont le spread vaut ~3 % de la distance de risque
au lieu de 6-10 % ferait passer le net de −0,03 à +0,02 R/trade. Les candidats du
catalogue sont les indices CFD (SP500 : spread 5,0 pour un ATR H1 très supérieur)
— mais **le mécanisme de session de devises ne s'y transpose pas** et il faudrait
reformuler l'hypothèse, pas la transporter.

### 5.2 L'axe horaire mérite d'être exploré, et il ne l'a jamais été

`time_filter_analysis.py` est écrit, testé 8/8, et **n'a jamais été lancé**
(TODO.md). Ce dossier montre qu'il y a quelque chose à y trouver : la porte
horaire transforme un signal nul (−0,013 R/trade OOS, 24h/24) en signal positif
(+0,041 R/trade OOS). **En tant que filtre par-dessus un signal ayant déjà un
edge propre**, l'heure est un candidat sérieux — jamais comme signal seul.

Corollaire de la règle du projet « ne jamais juger un filtre sur le PnL total » :
la porte horaire **réduit** le nombre de trades de 922 à 313 en moyenne. Jugée
au PnL total elle paraîtrait nuisible. C'est le **R/trade** qui montre qu'elle
retire les *mauvais* trades.

### 5.3 Trois pièges méthodologiques rencontrés ici

1. **La dérive à horizon fixe est une borne haute de l'espérance d'un trade à
   stop/cible.** Mon erreur d'estimation a priori a été de ~20 points de marge
   (§3.1). Si un chiffrage a priori doit être fait, il faut le corriger à la
   baisse — ou l'étalonner sur un backtest court avant de dimensionner.

2. **Un contrôle qui va dans votre sens peut être confondu.** F2 n'a pas été
   déclenchée et cela semblait confirmer mon mécanisme ; l'examen du confondant
   (§2.6) montre que la tendance yen l'explique entièrement. **Le réflexe
   « chercher l'explication concurrente la plus simple » doit s'appliquer en
   priorité aux résultats qui vous arrangent.**

3. **Séparer les affirmations d'une hypothèse avant de la tester.** Avoir
   distingué (a) « ça revient » de (b) « c'est propre à la fenêtre » a permis de
   réfuter le tout en gardant une mesure exploitable sur (b). Une hypothèse
   monolithique aurait produit un « non » sans information.

### 5.4 Confirmations de faits déjà connus du projet

- L'ablation du spread reste **le** diagnostic décisif : elle a distingué ici
  « edge mangé par les coûts » de ce que s01 avait trouvé (« pas d'edge du tout »).
  Deux verdicts identiques en surface, deux causes opposées.
- Le critère STRICT lu contre le **nombre attendu par hasard** discrimine
  immédiatement (1 vs 10,8). Lu seul, « 1 pass » n'aurait rien dit.
- Le contrôle long/short reste indispensable : il a révélé une asymétrie sur
  3 éligibles sur 4.

---

## 6. Limites de ce test

1. **Je suis le concepteur ET l'évaluateur.** C'est le conflit d'intérêt
   méthodologique maximal. Atténuations appliquées : conditions de falsification
   écrites et chiffrées avant le premier backtest (ANALYSIS.md §6), hypothèse
   formée sur les 60 % d'entraînement seulement, aucune modification de la
   grille/des instruments/des fenêtres après avoir vu les résultats.
   **Contamination résiduelle déclarée** : j'ai vu le tableau plein échantillon
   d'`economics.py` avant de restreindre au train ; il a servi à **éliminer** ma
   première hypothèse (réversion au pic — §2 d'ANALYSIS.md), pas à construire la
   seconde. Tout chiffre OOS de ce dossier reste une **borne haute**.

2. **La version testée est une version dégradée du mécanisme.** Le mécanisme dit
   « fermer avant le retour du flux » ; le harnais ne permet pas de sortie
   temporelle (`max_hold_bars` non transmis par `run_walk_forward`, et une
   stratégie n'émet que `entry`/`stop`/`target` — R9 interdit d'écrire sa propre
   boucle). Les positions traversent l'ouverture de Londres. **Une réfutation de
   cette version ne réfute pas totalement H91** ; c'est la limite la plus
   sérieuse de ce dossier.

3. **Le contrôle de fenêtre (§2.4) est post-hoc.** Exécuté après le
   walk-forward, il ne peut rien promouvoir. Les fenêtres témoins sont injectées
   dans le script de diagnostic et n'entrent pas dans `param_grid`. La mesure OOS
   (§2.5) atténue mais n'annule pas ce statut.

4. **Un seul régime.** 2021-2026 : hausse du dollar, choc inflation 2022, carry
   yen. Le confondant de tendance (§2.6) est massif sur deux des six instruments.

5. **6 instruments, tous forex.** GBPUSD est en cache mais absent de
   `core/data/instruments.py` — l'ajouter exigerait de modifier `core/`, interdit.
   XAUUSD volontairement exclu (mécanisme de session inapplicable, et péage
   faible qui flatte tout signal nul — cf. VERDICT s01 §3.3).

6. **L'heure serveur est une calibration empirique**, pas une donnée du broker.
   Le passage à l'heure d'été décale la fenêtre d'une heure deux fois par an ;
   ce bruit n'est pas corrigé et travaille **contre** l'hypothèse.

7. ~~Slippage non modélisé.~~ **Levée** : le slippage est désormais chiffré
   (§2.10). Le verdict est établi à slippage nul — hypothèse la plus favorable —
   et un slippage réaliste de 0,2-0,5 pip retire 0,013 à 0,033 R/trade de plus.

8. **R5 (conformance backtest/live) non exécutable** : `core/validation/
   conformance.py` n'existe pas dans le dépôt. Atténuation structurelle :
   `on_bar()` appelle littéralement `precompute()` puis `generate_signals()` et
   ne retient que la décision de la barre courante — il n'existe pas deux
   implémentations pouvant diverger. Ce n'est pas une preuve, c'est une garantie
   structurelle.

9. **Une seule définition de l'extension.** `z` sur SMA20 est le choix le plus
   simple ; d'autres (bandes de Bollinger, RSI, distance à une VWAP de session)
   donneraient d'autres résultats. La grille couvre 54 variantes autour d'**une**
   définition, pas l'espace des définitions.

---

## 7. Fichiers produits

| Fichier | Contenu |
|---|---|
| `research/ANALYSIS.md` | Phase 1 — hypothèse H91, économie a priori, **conditions de falsification déclarées** |
| `research/economics.py` / `.txt` | Profil horaire, péage par géométrie, signature de réversion (plein échantillon) — a réfuté la 1re hypothèse |
| `research/explore_train.py` / `.txt` | Même mesure sur les 60 % d'entraînement — source unique de H91 |
| `strategy.py` | Implémentation `StrategyModule`, R1-R10, grille 54 configurations |
| `manifest.yaml` | Manifest complet |
| `backtests/causality.txt` | Sortie R1 archivée (configuration par défaut) |
| `backtests/run_wf.py` | Walk-forward et diagnostics F1-F5 |
| `backtests/anchored_wf.txt` | R1 × 24, plein échantillon, WF × 6, synthèse, robustesse, concentration |
| `backtests/spread_ablation.py` / `.txt` | Ablation du spread (324 cellules), contrôle directionnel, **examen du confondant**, stabilité annuelle |
| `backtests/window_control.py` / `.txt` | Contrôle post-hoc de la composante horaire |
| `backtests/window_oos.txt` | Effet horaire train vs test, spread nul et spread réel |
| `backtests/slippage_sensitivity.py` / `.txt` | Balayage du slippage 0 → 0,5 pip, plein échantillon et hors échantillon |
| `research/VERDICT.md` | Ce document |

### 7.1 Ce qui reste ouvert, pour qui reprendrait le dossier

- **La seule voie non explorée** est l'instrument à faible péage relatif (§5.1),
  et elle exige de **reformuler** l'hypothèse : le mécanisme de session de
  devises ne se transpose pas à un indice CFD.
- **La sortie temporelle** (fermer avant l'ouverture de Londres) reste
  inaccessible sans une évolution de `core/` — `run_walk_forward` ne transmet
  pas `max_hold_bars` et une stratégie n'émet que `entry`/`stop`/`target`.
  C'est la version fidèle du mécanisme, et elle n'a **jamais été testée**.
  Si `core/` devait évoluer, c'est le test qui aurait le plus de valeur ici.
- **Le mode `rolling`** (fenêtre d'entraînement glissante), désormais disponible
  dans `anchored_wf`, n'a pas été utilisé : le protocole avait été figé en
  Phase 1 sur le mode ancré, et le changer après avoir vu les résultats aurait
  été un second essai déguisé.

# S024 « Go Long » — verdict

**Mesuré le 2026-09-12 ; corrigé et remesuré le même jour après revue qualité.**
Harnais : `backtests/run_wf.py`, journal complet `backtests/run_all.log`, chiffres
bruts `backtests/results.json`. Critères : `research/FALSIFICATION.md`, **écrits
avant le run** — plus un **ADDENDUM daté** (A1-A6) qui corrige des défauts de
méthode sans toucher aux critères. Données : cache gelé 1855 jours, H1, heure
serveur Swissquote, 2021-08-16 → 2026-09-11 (5,07 ans). R1 OK et R5 OK sur les
trois instruments (porte franchie avant toute mesure).

> **Ce que la revue a changé.** Le % était calculé sur `exit_price − entry_price`,
> qui **ne paie que la moitié du spread** (le moteur replie le coût d'entrée dans
> `entry_price`, celui de sortie seulement dans `pnl_r`). Tous les % viennent
> désormais de `pnl_r`. La cellule de fidélité au spread mesuré passe de 56,31 à
> **47,91 %** (DAX), 75,89 à **71,42 %** (NASDAQ), 49,25 à **43,47 %** (US30).
> Le sens du verdict tient ; son amplitude était surévaluée d'un tiers sur le DAX.

---

## Le verdict, en une phrase

> **Réussite en tant que bêta indiciel, pas d'edge de timing.**

C'est la formulation prévue d'avance pour ce cas, et elle survit à la correction.
C'est aussi ce que l'auteur revendique : *« there is no filter, there is no
analysis, no nothing »* [05:24]. La règle gagne de l'argent sur les trois indices
nets du spread mesuré, avec un profil conforme à son live — mais **l'heure qu'il a
choisie ne bat pas les autres heures de séance** sur les indices américains.

**Ce que la correction a précisé, et qui est la vraie trouvaille** : sur la seule
population comparable (les journées réellement tradées), **la jambe overnight est
négative sur les trois indices** et la jambe intraday seule bat l'achat-et-
conservation **partout**. Ce qui paie n'est pas l'heure : c'est d'être à plat hors
séance. Sa thèse est juste ; son explication (« être investi le plus longtemps
possible ») ne l'est pas.

---

## 1. Cellule de fidélité — garde 5 %, offset 0, spread mesuré

| | **DAX** | **NASDAQ** | **US30** |
|---|---:|---:|---:|
| Trades | 1 293 | 1 268 | 1 269 |
| R total · R/trade | +9,6 · +0,0074 | +14,3 · +0,0113 | +8,7 · +0,0068 |
| **% total (somme)** | **+47,91 %** | **+71,42 %** | **+43,47 %** |
| **% / trade** | **+0,0371 %** | **+0,0563 %** | **+0,0343 %** |
| Taux de réussite · PF | 54,1 % · 1,11 | 54,2 % · 1,12 | 53,0 % · 1,11 |
| Drawdown max (cumul %) | 27,97 pts | 35,55 pts | 19,03 pts |
| Garde catastrophe touchée | 3 (0,23 %) | 9 (0,71 %) | 2 (0,16 %) |
| Spread catalogue → mesuré | 8 → 23 pips (×2,88) | 8 → 12 pips (×1,50) | 35 → 35 (×1,00) |
| % au spread catalogue | +58,87 % | +74,40 % | +43,47 % |
| **Percentile balayage horaire** | **100,0** (1/14) | **31,8** (16/23) | **63,6** (9/23) |
| Percentile bras témoin commun | 69,0 | 51,5 | 80,5 |

Les six cellules restent positives sur les trois instruments, aux deux spreads.
Walk-forward ancré : **STRICT 3/3 sur les deux passes d'offset** pour NASDAQ et
US30 ; pour le DAX, 3/3 en offset 0 et **0/3 en offset 1**, dont la quatrième
fenêtre finit à **−0,27 / −0,29 / −0,14 R** selon la garde (le rapport précédent
affichait « −0,0 » : un arrondi qui masquait le signe). ~505 trades hors
échantillon par cellule — l'effectif tient, ce n'est pas un « strict pass » sur 19
trades.

**Le R n'est pas comparable entre gardes** : son dénominateur EST la garde. Seule
la colonne % a un sens transversal. Écrit d'avance, redit ici.

## 2. Les étalons — la partie qui décide

Trois variantes publiées (cf. ADDENDUM A3). **Celle qui porte le verdict est
« journées tradées »** : les 38 (NASDAQ) et 39 (US30) journées que la stratégie
saute ne sont pas tirées au hasard — ce sont des lendemains de séance anormale —
et les comparer à une stratégie qui ne les trade pas n'a pas de sens.

### Variante de référence — journées effectivement tradées

| (sans moteur, sans coût) | **DAX** (1 293 j) | **NASDAQ** (1 268 j) | **US30** (1 269 j) |
|---|---:|---:|---:|
| Acheter-et-tenir (5,07 ans) | +60,85 % | +94,17 % | +48,26 % |
| Jambe **intraday**, composée | **+81,63 %** | **+103,95 %** | **+66,87 %** |
| Jambe **overnight**, composée | **−11,44 %** | **−4,80 %** | **−11,15 %** |
| Jambe intraday, somme | +65,75 % | +83,83 % | +56,50 % |
| Jambe overnight, somme | −10,25 % | −4,05 % | −11,48 % |
| DD max intraday · overnight | 25,1 · 22,7 pts | 33,7 · 21,2 pts | 17,9 · 15,6 pts |

**Sa thèse est confirmée sur les trois indices** : la séance porte le rendement, la
nuit le détruit, et la jambe intraday seule bat l'acheter-et-tenir partout
(+81,6 vs +60,9 ; +104,0 vs +94,2 ; +66,9 vs +48,3).

### Ce que la variante change, et pourquoi il faut le savoir

| Jambe overnight, composée | toutes journées | sans chevauchement | **journées tradées** |
|---|---:|---:|---:|
| DAX | −11,44 % | −11,44 % | −11,44 % |
| NASDAQ | **+1,83 %** | −0,40 % | **−4,80 %** |
| US30 | −1,76 % | −5,05 % | **−11,15 %** |

Le premier rapport concluait, sur la variante « toutes journées », que **le NASDAQ
était un contre-exemple** (jambe overnight positive, donc sortir chaque soir y
coûtait du bêta). Ce contre-exemple **disparaît** sur la population comparable.
Deux causes, toutes deux des défauts du premier étalon :

- **46 chevauchements** sur NASDAQ (47 sur US30, 0 sur DAX) où la sortie du jour k
  tombait après l'entrée du jour k+1 : la jambe overnight y était calculée sur un
  intervalle de temps **négatif**, et le gap de week-end crédité à l'intraday
  (+ 12 égalités de part et d'autre, conservées : overnight nul, journée valide) ;
- les **38/39 journées sautées** portaient un overnight nettement positif ; sur
  US30 elles valaient à elles seules **−9,9 points** de jambe intraday.

**À charge** : ce changement de population a été décidé **après** la première
mesure et il **favorise** la thèse de l'auteur. C'est pourquoi les trois variantes
figurent ci-dessus plutôt que la seule qui arrange, et pourquoi l'ADDENDUM A3 le
dit explicitement.

### Le swap — non modélisé, et décisif

Il chiffre lui-même le portage long du DE40 à **≈ 6 %/an** [07:32] : ≈ 30 points de
notionnel sur notre période, qui seraient prélevés sur l'**acheter-et-tenir en CFD**,
pas sur la stratégie (qui ne tient rien la nuit). La comparaison ci-dessus lui est
donc **défavorable**. C'est la réserve n°1 du dossier et la prochaine mesure utile.

## 3. Fidélité au live de l'auteur — les quatre repères, tous tenus

| | Attendu (son live) | Mesuré (après correction) | |
|---|---|---|---|
| **F1** | ≈ 250 trades/an/indice | 248 à 257 par année pleine | ✅ |
| **F2** | +0,02 % à +0,06 % par trade | +0,0343 / +0,0371 / +0,0563 % | ✅ |
| **F3** | signe annuel = intraday de l'indice | 2022 négative partout (−8,3 / −30,4 / −4,9 %) | ✅ |
| **F4** | drawdown du printemps 2025 visible | NASDAQ **−22,3 pts, 2025-02-17 → 2025-04-04** ; US30 **−17,1 pts, 2025-02-05 → 2025-04-08** | ✅ |

La correction du % rapproche F2 du centre de sa fourchette au lieu d'en frôler le
haut. F4 n'apparaît que parce que le harnais publie le **drawdown intra-année
daté** : 2025 finit positive sur les trois indices (+16,8 / +18,6 / +6,6 %) et un
total annuel l'aurait effacé. Sur US30 ce creux (−17,1 pts) est aussi profond que
celui de tout le marché baissier 2022 (−19,0 pts), et il se referme en deux mois.

## 4. Les conditions de réussite, jugées honnêtement

| Condition (écrite avant) | Résultat |
|---|---|
| 1. Positive au spread mesuré sur ≥ 2 des 3 indices | ✅ **3/3**, et sur les 6 cellules |
| 2. Percentile du balayage horaire ≥ 90 | ❌ **1/3** — et ce 1 est confondu (voir plus bas) |
| 3. Jambe intraday ≥ acheter-et-tenir − overnight | ⚠️ **vide de contenu** — cf. ADDENDUM A2 |

**La condition 3 ne teste rien.** Les deux jambes se télescopent :
`(1+I)·(1+O) = 1+BH`, donc `BH − O = I·(1+O)`, et la condition se réduit exactement
à « la jambe overnight est ≤ 0 » — l'hypothèse qu'elle prétendait tester. Elle est
donc rapportée et **écartée du jugement**, pas réécrite après coup. Lue en sommes
mélangées à des composés, elle échouait sur NASDAQ ; lue en composés, elle passe
partout. Les deux lectures sont sans valeur : c'est le critère qui était mal posé.
Le verdict se joue sur les conditions 1 et 2, qu'aucun de ces défauts n'affecte.

Aucun critère d'échec n'est atteint : rien de négatif au spread mesuré, et la jambe
intraday domine la jambe overnight partout.

**Le 100,0 du DAX n'est pas un edge de timing**, et le harnais publie la colonne qui
l'interdit. La séance du DAX ne fait que 14 h sur 24 : toute autre heure d'entrée
fait déborder la fenêtre de 13 barres hors séance (durée horloge médiane **23 h
contre 13 h** à l'heure de fidélité). Le balayage y compare « séance » à « séance +
overnight », pas « 09:00 » à « 15:00 » — il remesure la prime du § 2, pas une vertu
de l'heure.

**Et le même biais existe sur NASDAQ et US30, en plus petit — dans l'autre sens.**
Le premier rapport affirmait que « toutes les fenêtres durent 23 h » : c'est faux.
L'heure de fidélité dure **22,0 h**, les 22 autres **23,0 h**. Les concurrentes ont
donc **une heure d'exposition de plus** que la référence : le biais joue **en leur
faveur**, et le rejet de la condition 2 (rangs 16/23 et 9/23) en est **renforcé**,
pas fragilisé.

**Convention du percentile** : rang parmi les **autres** heures. La convention
« toutes heures » de `ControlArm.percentile` donne 96,4 / 32,6 / 63,0 (et 92,9 pour
le DAX si l'on compte la référence comme une défaite stricte). Aucune conclusion ne
dépend du choix ; les deux sont dans `results.json`.

## 5. Ce que le dispositif a coûté, et qu'il faut savoir

- **Jours sautés** : 38/1 306 (2,9 %) sur NASDAQ, 39/1 308 (3,0 %) sur US30, 0 sur
  DAX. Cause : les 60 et 61 positions qui sortent le lendemain (séances non
  standard — décalage d'heure d'été américain contre européen, fériés tronqués)
  empiètent sur la barre d'entrée suivante. Le moteur les impute à
  `skipped_cooldown` et non à `skipped_open` : avec `cooldown_bars=0` le test de
  refroidissement est atteint le premier. **Même cause, autre compteur.**
- **Heures de sortie** : **89,1 %** à 22:00 sur NASDAQ et **89,4 %** sur US30 (soit
  23:00 serveur, contre 23:50 chez lui → **50 min d'écart résiduel**), 6,2 % à
  23:00, 2,7-2,8 % à 03:00. Sur DAX, **99,7 %** à 21:00 (22:00 serveur, contre
  22:55 chez lui → **55 min**, et la séance Swissquote ferme de toute façon avant).
- **Garde catastrophe** : sous le seuil de 2 % à la garde de fidélité partout.
  **Deux cellules NASDAQ le dépassent** : garde 3 % offset 0 (**51 hits, 4,0 %**) et
  garde 3 % offset 1 (**47 hits, 3,7 %**). Ces deux-là ne sont plus « sa stratégie
  sans stop » ; elles sont publiées, elles ne portent aucun verdict.
- **Bras règles communes** (information seulement) : le coupe-circuit refuse la
  moitié des jours et coûte **−24,4 pts** de % sur DAX (47,91 → 23,53), **−1,9 pt**
  sur NASDAQ (71,42 → 69,48) et **−44,2 pts** sur US30 (43,47 → **−0,78**, seul
  résultat négatif de tout le dossier). Avec un trade par jour et un taux de
  réussite voisin de 50 %, trois pertes d'affilée arrivent en permanence, et le
  coupe-circuit met 24 barres à se rouvrir — une journée entière de bêta manquée à
  chaque fois. **Les règles communes annuleraient cette stratégie.** C'est
  exactement pourquoi la doctrine du 2026-09-12 les tient hors du bras fidèle.

## 6. Réserves

1. **Le swap n'est pas modélisé**, ni pour la stratégie (qui n'en paie presque pas)
   ni pour l'acheter-et-tenir de référence (qui en paierait beaucoup, ≈ 6 %/an sur
   DE40 selon l'auteur). La comparaison du § 2 est donc défavorable à la stratégie.
   Mesure manquante n°1.
2. **Le slippage vaut 0** partout (valeur du catalogue, conservée telle quelle). Sur
   un CFD d'indice, l'ouverture à 01:00 et la clôture de séance ne sont pas les
   moments les plus liquides : les chiffres restent optimistes d'un montant inconnu.
3. **Le plafond de spread est relevé au spread mesuré.** Le catalogue plafonne le
   DAX à 20 pips alors que le spread mesuré vaut 23 : sans relèvement, le moteur
   refuserait **tous** les trades et la colonne serait silencieusement vide. Le
   relèvement est nécessaire, mais il **neutralise le garde-fou anti-news** — à
   spread mesuré, aucune barre n'est jamais écartée pour spread excessif.
4. **Le choix de la variante d'étalon** (journées tradées) a été arrêté après la
   première mesure et favorise la thèse de l'auteur (cf. § 2 et ADDENDUM A3). Les
   trois variantes sont publiées.
5. **Courtier différent** : ses horaires (23:50 / 22:55) viennent d'IC Markets, nos
   barres de Swissquote. Écart résiduel chiffré au § 5, pas corrigé.
6. **Sa période de live (mars 2024 → 2026) est incluse dans notre échantillon** et en
   est la meilleure partie. Nos années 2021-2022 ne sont pas dans son bilan.
7. **`pip_value_per_lot=1.0`** pour les trois indices est une convention du catalogue,
   non recalculée depuis `trade_tick_value`. Sans effet ici : tout est en R et en %.
8. **Le bras témoin commun est non informatif sur cette stratégie**, par construction
   du module (il recopie le filtre horaire d'une stratégie qui n'occupe qu'une heure
   de séance). Réserve écrite avant le run. Le balayage horaire exhaustif le remplace.

## 7. Ce qui pourrait suivre — aucune de ces pistes n'est engagée

Chaque piste exige sa propre section de falsification **avant** d'être mesurée.

- **Mesurer le swap réel Swissquote** sur les trois indices. Seule mesure capable de
  transformer « bêta indiciel » en « bêta indiciel moins cher qu'un ETF », et c'est
  le cœur de son argument. Priorité 1 — de la donnée, pas du réglage.
- **Modéliser un slippage non nul** et rejouer : à +0,034 %/trade sur US30, la marge
  est mince.
- **Turnaround Tuesday** (`S023_balke_turnaround_tuesday`, en cours par ailleurs)
  réutilise le même horaire et la même absence de stop. Rien à lancer ici, mais
  **quatre résultats de ce dossier lui sont opposables** : le % doit venir de
  `pnl_r` et jamais de `exit_price − entry_price` ; la séance se dérive des barres ;
  le R n'est pas comparable entre gardes ; le bras témoin commun est aveugle sur une
  stratégie mono-horaire.
- **Rien sur la garde ni sur l'offset** : les six cellules disent la même chose.

## 8. Statut

`RESEARCH` → **`BACKTESTED`**. **Mesuré, pas validé.** Aucune promotion PAPER ou
LIVE : décision d'Adrian seule (R10).

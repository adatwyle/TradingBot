# moneytalk — synthèse des deux épisodes

> **Sources** : `01_doud_gold_sans_stoploss.txt` (MoneyTalk #29, 80 min) et
> `02_rababian_carnet_ordre.txt` (MoneyTalk #30, 77 min), plus les pages
> commerciales relevées dans `SOURCE.md`. Chaque affirmation ci-dessous porte
> son horodatage `(@ mm:ss)` — vérifiable ligne à ligne dans le fichier brut.
> **Date** : 2026-09-06. Citations normalisées à la lecture (cf. `SOURCE.md`),
> jamais reformulées.

---

## 0. Les trois réponses en tête

**1. Il y a une méthode, et elle est en partie codable.** Sous le vocabulaire
personnel (« zones fatidiques », « mèche sabre laser », « TP de l'ego », « la
météo »), quatre affirmations mécaniques survivent à la traduction : un biais
directionnel décidé *avant* d'ouvrir le graphique, un long-only assumé sur l'or,
une lecture en **structure plutôt qu'en mèche**, et un **retour à l'équilibre**
(le milieu du mouvement, pas son extrême) comme lieu d'entrée. Ces quatre-là se
testent sur nos barres. Elles partent en v2.

**2. Le cœur du dispositif de risque est inadmissible chez nous, et elle en
fournit elle-même la contre-preuve.** Pas de stop loss (@ 12:31), renforcement à
la baisse (@ 39:07), risque porté sur « les bénéfices de la semaine » (@ 12:39).
Le contrat R3 de la plateforme rend `Signal.stop` obligatoire — le constructeur
lève une exception. Et la démonstration empirique est dans l'épisode : **−80 000 €
en une journée** (@ 32:30), soit « deux mois de bénéfice » (@ 34:27), sur une
« chute institutionnelle » prise avec 40 de fièvre. Une méthode dont le pire cas
est borné par la présence de l'opérateur devant l'écran n'est pas automatisable.

**3. Aucun chiffre de performance de cette source n'est utilisable.** Ni ceux du
podcast (« entre 50 000 et plus de 100 000 € » sur janvier, @ 05:12 ; « 75-80 % »
de membres rentables, @ 57:07), ni ceux du site (`+145 % 24/25`, `Sharpe 5,6`,
`28 % de DD`, `89 % de réussite` — quand la même page annonce ailleurs `+127 %
en 2024`). Un Sharpe de 5,6 coexistant avec 28 % de drawdown est arithmétiquement
douteux, et rien n'est auditable. La méthode entre comme **hypothèse à mesurer**,
jamais comme résultat à reproduire.

---

## 1. La méthode Doud, reconstituée

Cindy trade **exclusivement XAUUSD**, en CFD, au scalp intraday, en discrétionnaire
et en live devant sa communauté. Elle revendique 3 ans de rentabilité (@ 02:22).
Le pipeline, tel qu'il ressort de l'entretien :

### 1.1 Biais directionnel AVANT le graphique

> « avant d'ouvrir un graphique […] c'est impossible que je vienne sur une
> journée pour trader le gold […] où j'ai pas déjà mon biais directionnel »
> (@ 23:32)

Le biais vient du **dollar** et du contexte politique/Fed, jamais du graphique
seul : elle ne trade pas l'actif « au centre de la mêlée » mais ceux qui l'entourent
(@ 22:40), et l'or n'a « son propre mécanisme d'offre et de demande » que
conditionné au dollar (@ 23:18). Elle est catégorique sur le fondamental :
« tu ne peux pas trader le gold si tu ne t'intéresses pas à la politique »
(@ 08:36), et sur la macro comme préalable au chart (@ 07:50, réponse « vrai »).

**Conséquence opératoire** : la direction du jour est décidée d'abord, les setups
ne servent qu'à placer l'entrée dans cette direction. « À quel moment j'arrive en
session européenne je me mets à vendre ? Il faut être complètement idiot »
(@ 23:47).

### 1.2 Long-only sur l'or

> « j'achète beaucoup plus le gold que je le vends. Je vends quasiment jamais »
> (@ 21:52)

Et la discipline associée : quand le marché vend, elle **ne se retourne pas**,
elle attend un setup acheteur — « si je le lis 4 heures plus tard, je rentrerai
4 heures plus tard » (@ 22:20). Sa raison est cognitive, pas statistique : trader
les deux sens dans la journée empêche le cerveau de savoir « à quel moment tu
te stoppes » (@ 21:54).

### 1.3 Structure, pas mèche

> « un chandelier ça se travaille en structure et non en mèche » (@ 17:52)

C'est, mot pour mot, une prise de position sur ce qui définit un niveau : le
**corps** des bougies, pas l'extrême des mèches. Le reste du passage l'explicite :
une mèche d'annonce fait 3000 points, mais ce qui compte est où se situe
« l'équilibre du marché » (@ 18:04).

### 1.4 L'équilibre — le milieu, pas l'extrême

> « généralement le marché va venir sur l'équilibre et pas récupérer en bas mais
> **récupérer le milieu**. C'est pour ça qu'on voit le gold des grandes montées,
> ça range, des grandes descentes, ça range » (@ 18:08)

Et la construction, telle qu'elle la décrit : « si tu calcules le plus bas au plus
haut et que tu tires un équilibre, tu vas avoir des confirmations de points
d'entrée que tu ne vas pas voir » (@ 18:49). C'est un **retracement à 50 % de la
jambe**, utilisé comme lieu d'entrée dans le sens du mouvement — pas comme cible.

C'est l'affirmation la plus intéressante de l'épisode, parce que c'est la seule
qui contredit frontalement notre v1 : S011 **achète la cassure au close**, elle
attend le retour au milieu de la jambe cassée. Les deux se mesurent sur les mêmes
barres.

### 1.5 Sessions

Elle trade la **session US dès 14h** et la **session asiatique** le soir/la nuit ;
elle **ne trade pas Londres** : « je ne trade pas la session de Londres, c'est
vraiment une session que je n'aime pas » (@ 35:35). Sa journée type : lever 7h,
cours VIP à partir de 11h, lives à 14h, reprise vers 23h55 (@ 35:55–38:21). Le site
confirme la cadence : lives « dès 14h », « open asian certains soirs ».

### 1.6 Entrées sur annonces, et le calcul en points

Elle revendique de trader les annonces économiques — « moi je vais casser les
mythes, je trade les annonces éco » (@ 09:23) — en entrant **2 minutes avant**
(@ 10:54), avec une arithmétique préalable : une annonce déplace l'or d'environ
**3000 points**, donc « tu sais que tu as une probabilité de perdre 3000 points
ou d'en gagner 3000 » (@ 11:29), et le calcul du coût se fait *avant* l'entrée
(@ 19:33 : « je pense déjà à ce que je vais perdre avant ce que je vais gagner »).
Elle publie le dimanche une « météo » probabiliste de la semaine construite sur
le calendrier des annonces (@ 25:34).

### 1.7 Sorties : partielles, SL suiveur, jamais de break-even à zéro

Entrée par paliers (0,10 lot pour « sentir » puis 1,0 — @ 28:47), positions
**multiples** fermées par moitiés (@ 29:03), puis TP1/TP2/TP3 et un quatrième
qu'elle appelle « le TP de l'ego » (@ 20:44). Le stop, lui, **monte derrière le
prix** : « je vais mettre mon SL suiveur à […] et après je vais le monter »
(@ 29:51). Et un refus explicite du break-even neutre :

> « le break-even, pour moi, c'est la mauvaise graine […] quand tu sors à
> break-even, c'est un trade inutile » — parce qu'il ne paie pas les frais de
> courtage ; son break-even « finance toujours le coût du trade » (@ 30:04)

### 1.8 Le risque — et pourquoi ça casse

Pas de stop loss à l'entrée (@ 12:31), au motif qu'elle « connaît la probabilité ».
Le capital est protégé par une règle de *cagnotte* : ne risquer que les bénéfices
déjà faits dans la semaine, jamais le capital (@ 12:39), et retirer sa mise dès
qu'elle est doublée (@ 13:18). En séance difficile, elle **renforce plus bas**
(@ 39:07, l'anecdote du membre accompagné jusqu'à 4h30 du matin).

Le pire cas est documenté par elle-même : **−80 000 €** en une journée, malade,
sur une chute institutionnelle qu'elle a prise à contre-sens (@ 32:30), soit deux
mois de bénéfices (@ 34:27). Elle a aussi « cramé » une prop firm la veille de
l'enregistrement en tradant « avec des volumes de 15 » (@ 72:07).

---

## 2. Ce qui est reproductible chez nous — et ce qui ne l'est pas

| # | Affirmation | Traduction mécanique | Faisable ? |
|---|---|---|---|
| D1 | Long-only sur l'or (@ 21:52) | `side_mode = LONG_ONLY` | **Oui** — testable directement |
| D2 | Biais directionnel avant le chart (@ 23:32) | porte de tendance sur unité supérieure (D1 depuis les barres H1) | **Oui, en proxy** — le biais macro réel (dollar, Fed) n'est pas dans nos données ; la porte HTF en est l'ombre mécanique honnête |
| D3 | Structure, pas mèche (@ 17:52) | canal de Donchian sur les **corps** (closes) au lieu des extrêmes (high/low) | **Oui** — un paramètre, mesurable contre la v1 |
| D4 | Retour à l'équilibre (@ 18:08) | entrée sur **repli à 50 % de la jambe** cassée, au lieu de l'entrée au close de cassure | **Oui** — cœur de la v2 |
| D5 | Sessions US + asiatique, jamais Londres (@ 35:35) | filtre horaire sur l'heure serveur, calibrée et non devinée | **Oui** |
| D6 | Sorties partielles TP1/TP2/TP3 (@ 29:03) | — | **Non** — `core/backtest/engine.py` ne connaît qu'une sortie unique. Extension plateforme requise (ticket) |
| D7 | SL suiveur (@ 29:51) | — | **Non** — le moteur commun ne déplace jamais un stop ; R9 interdit d'en écrire un autre. Même limite que la v1 (S011 `research/ANALYSIS.md` § 4) |
| D8 | Break-even qui finance les frais (@ 30:04) | — | **Non** — dérive du SL suiveur, même blocage |
| D9 | Entrée 2 min avant l'annonce (@ 10:54) | fenêtre de calendrier économique | **Non** — pas de calendrier dans nos données. NFP seul serait déterministe (1er vendredi), mais un demi-calendrier ne teste pas l'hypothèse |
| D10 | Scalp intraday, jamais tenu des jours | `max_hold_bars` borné | **Oui** — paramètre du moteur commun |
| **D11** | **Pas de stop loss (@ 12:31), renforcement à la baisse (@ 39:07)** | — | **Refusé** — R3 rend `Signal.stop` obligatoire. Ce n'est pas une limite technique, c'est un refus : sa propre perte de 80 000 € (@ 32:30) est le coût de cette règle |

**Ce que la v2 emporte** : D1, D2, D3, D4, D5, D10.
**Ce qu'elle laisse, en le disant** : D6-D9 (limites plateforme, tickets ouverts),
D11 (refus de contrat).

---

## 3. MoneyTalk #30 — carnet d'ordre : hors d'atteinte, sauf trois choses

Karen Rababian trade les futures (ZN, ZB, UB, ES, NQ) au **carnet d'ordre**, formé
à Chicago au CBOT (@ 11:49). Son propos est cohérent et technique : absorption
(« l'armée bleue tue l'armée rouge », @ 51:07), *inside print* comme champ de
bataille (@ 51:54), **spoofing** assumé comme mécanique normale du marché
(« heureusement qu'elle existe », @ 30:41 ; l'appât et le retournement, @ 31:29),
carnets légers contre carnets lourds (NQ à 4-5 contrats par niveau contre ZN à
10 000, @ 34:40).

**Rien de tout cela n'est implémentable ici, et ce n'est pas une question de
réglage.** `core/data/source.py` le dit à la source :

> `real_volume` = 0 sur tous nos instruments (forex OTC et CFD synthétiques
> Swissquote n'ont pas de volume centralisé publié). […] toute stratégie fondée
> sur le volume échangé, le delta bid/ask, l'absorption ou un footprint est
> **irréalisable ici**.

Il le confirme lui-même en creux : le carnet ne vaut que sur les futures, « sur
les CFD ça ne marche pas » (@ 09:27), et le prix CFD n'est même pas unique — trois
brokers, trois prix sur le gold, ce qui l'a lancé sur la piste du carnet (@ 10:15).

Ce qui survit et nous concerne :

1. **La « carenade »** (@ 15:47) — son mentor l'a baptisée ainsi après l'avoir vu
   gagner 1500 $ puis rendre 100 $ le même jour : *tu gagnes, tu arrêtes la
   journée*. Chez nous ce n'est pas une règle de stratégie mais une règle de
   **portefeuille** (R2 : la stratégie ne connaît ni le solde ni la journée) —
   donc `core/risk/`, pas S018. Ticket.
2. **Ne pas laisser tester son stop** (@ 44:50) : « je préfère prendre deux trois
   trades, sortir à trois ticks, que toujours laisser tester mon stop ». Chez nous,
   l'expression admissible est `max_hold_bars` — une sortie au temps, pas une
   sortie à l'humeur. Rejoint D10.
3. **Le risk-reward s'inverse avec la taille** (@ 67:45) : plus le portefeuille est
   gros, plus le RR visé baisse. Observation de gouvernance, à ranger dans la
   politique de promotion, pas dans une stratégie.

Et un rappel de méthode que les deux invités formulent depuis les deux bords :
elle reproche aux autres d'attendre « une pancarte pour rentrer » pendant que le
marché part sans eux (@ 50:05) ; lui rappelle que sans carnet on lit l'indicateur,
donc qu'on est « dans le troisième wagon » (@ 52:43). Même arbitrage vu des deux
côtés : plus la confirmation est riche, plus elle est tardive. C'est exactement ce
que D4 met en jeu — cassure immédiate contre repli à l'équilibre.

---

## 4. Le modèle économique, et la lecture des chiffres

À déclarer, parce que ça conditionne le poids qu'on donne à la source :

- **Offre payante** : lives à 39,99 €/mois, accompagnement VIP sur candidature,
  séminaires, « +3000 traders dans la communauté ». Un changement de plateforme
  était annoncé en fin d'épisode (@ 76:01).
- **Un PAMM en préparation** : page de sondage, ticket d'entrée 1 000 €, chiffres
  invérifiables et **internement contradictoires** (`+145 % 24/25` en tête,
  `+127 % en 2024` plus bas), urgence artificielle (« places EXTRÊMEMENT
  limitées »).
- **Ce qu'elle dit elle-même sur les statistiques** quand on lui oppose les 90 %
  de perdants de l'AMF : « qui a calculé le pourcentage ? » (@ 57:07). Le même
  scepticisme s'applique à ses propres 75-80 %, qui ne reposent sur aucune mesure
  publiée.
- **À son crédit** : elle ne fait pas d'affiliation prop firm et le dit (@ 69:46,
  @ 73:41), elle assume ses pertes chiffrées (@ 32:30), et elle recommande le
  fonds propre plutôt que la prop firm pour débuter (@ 71:20) — ce qui est
  l'inverse du discours d'affiliation courant.

**Position retenue** : la source vaut pour ses **hypothèses de marché**, pas pour
ses **résultats**. C'est le régime de lecture standard de ce dépôt
(cf. `docs/sources/fxalexg/SYNTHESE.md`, même conclusion sur une autre source).

---

## 5. Ce qui part en v2

`strategies/S018_gold_doud_v2/` — v2 du résidu or de `S011_legacy_breakout`,
construite sur la grille D1/D2/D3/D4/D5/D10, dont la **cellule neutre reproduit
exactement la v1**. La v1 scellée (`studies/gold_forward/`) continue sa mesure
sans être touchée : elle est le témoin.

Hypothèses, critère de falsification et résultats : `research/ANALYSIS.md`,
`research/FALSIFICATION.md`, `research/VERDICT.md` de S018.

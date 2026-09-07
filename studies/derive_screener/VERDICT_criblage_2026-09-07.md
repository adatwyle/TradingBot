# VERDICT — criblage de dérive des entrées Doud

**Période d'étude** : 2021-08 → 2024-12, XAUUSD, mailles H1 / M15 / M5.
**Holdout** : 2025-2026 **jamais chargé**. Il n'a pas été ouvert, et il ne l'a pas
été non plus pour départager un candidat.
**Candidats** : 9, liste arrêtée avant exécution (`PLAN_doud-reproduction` § T5), aucun
ajout ni réglage après lecture des résultats.

---

## 1. Verdict

**Aucun candidat ne survit.** Aucun ne montre de dérive directionnelle mesurable, et le
seul résultat positif du criblage ne tient qu'à une géométrie sur deux — soit exactement
ce que la multiplicité produit toute seule.

Et leur faiblesse se chiffre : **la meilleure dérive brute vaut +15 pips, quand l'ATR
horaire de l'or en vaut 1 854.** Huit dixièmes de pourcent d'une amplitude horaire. À
cette échelle, aucune maille ne convient : trop fine, les frais mangent le risque ; trop
large, il ne reste plus d'occasions.

| | valeur |
|---|---|
| Meilleure dérive brute mesurée, toutes cellules confondues | **+15 pips par trade** |
| Spread médian sur la période d'étude | **52 pips** |
| Spread médian du régime courant (2026) | **90,8 pips** |
| Net, dans le meilleur des cas | **−37 pips par trade** |

Les 36 cellules mesurées (9 candidats × 2 géométries × 2 mailles) vont de −19 à +15 pips
de dérive brute. Aucune n'approche le coût. Ce n'est pas une question de seuil, de
réglage ou de puissance statistique : il manque un facteur six.

---

## 2. L'outil, et le fait qu'il a d'abord été faux

Le cribleur mesure, pour une règle d'entrée donnée, l'espérance en R d'un pari à
barrières : stop à `sl`·ATR, cible à `tp`·ATR, laquelle tombe la première. Sous absence
de dérive, cette espérance vaut zéro **pour toute géométrie** — théorème d'arrêt
optionnel. Un écart significatif est de l'information directionnelle.

**Une première version était fausse et le témoin l'a dit.** Elle posait des barrières
symétriques ; son témoin positif — la v1 — en ressortait négatif (−0,075) alors que la v1
rend +0,236 R/trade au percentile 100 du hasard. Le critère de validité, écrit avant la
mesure, a invalidé l'outil avant que ses chiffres ne soient publiés.

La cause : la v1 gagne avec 34,6 % de réussite parce qu'elle vise 4 ATR en risquant 1,5.
Son avantage vit dans l'**asymétrie du gain**, et un test symétrique le jette. Corollaire
méthodologique, valable au-delà de ce dossier : **une mesure de dérive doit se faire à la
géométrie où l'on compte jouer**, jamais à une géométrie de convenance.

Le témoin a aussi révélé un second défaut : à barrières rapprochées (0,5 ATR), *toutes*
les entrées rendaient −0,09, y compris celles tirées au hasard — les deux barrières
tombent dans la même barre, où la convention tranche contre nous. Le cas est désormais
compté et affiché.

### Validation de la version corrigée

| Épreuve | Résultat |
|---|---|
| Couverture — entrées aléatoires, E[R] vrai = 0 | 40 intervalles sur 40 contiennent zéro ; biais moyen **−0,001 R** |
| Récupération — dérive injectée (55 % d'entrées bien orientées) | **+0,111 R**, intervalle excluant zéro |
| Récupération — 60 % bien orientées | **+0,126 R** |
| Plancher de détection | ±0,181 R à n = 300 · ±0,099 à n = 1 000 · ±0,057 à n = 3 000 |

Le cribleur voit donc une dérive quand il y en a une, et n'en invente pas quand il n'y en
a pas.

---

## 3. Ce que chaque candidat a rendu

Maille M5, géométrie stop 1,0 ATR / cible 2,0 ATR — la combinaison la mieux fournie,
donc la plus discriminante.

| candidat | n | E[R] | IC 95 % | brut (pips) | verdict |
|---|---:|---:|---|---:|---|
| 0 témoin v1 (S011) | 5 805 | −0,011 | [−0,047, +0,025] | −1 | nul (net) |
| 1 balayage haussier | 4 024 | −0,013 | [−0,056, +0,031] | −2 | nul (net) |
| 2 balayage **baissier** | 4 570 | −0,009 | [−0,050, +0,032] | −1 | nul (net) |
| 3 équilibre 50 % | 17 524 | +0,009 | [−0,012, +0,030] | +1 | nul (net) |
| 4 cassure Donchian | 11 967 | −0,043 | [−0,068, −0,018] | −5 | dérive **négative** |
| 5 niveau rond 50 | 2 244 | **+0,082** | [+0,022, +0,141] | **+14** | positif **à cette seule géométrie** |
| 6 mi-asiatique | 2 488 | +0,029 | [−0,027, +0,085] | +4 | nul (net) |
| 7 extrêmes de la veille | 4 965 | −0,003 | [−0,042, +0,036] | −0 | nul (net) |
| 8 compression | 8 889 | −0,038 | [−0,068, −0,009] | −4 | dérive **négative** |

**Le cas du candidat 5.** C'est le seul résultat positif significatif du criblage. Il ne
compte pas, et la règle qui l'écarte était écrite d'avance : *« une dérive qui n'apparaît
qu'à une seule géométrie ne compte pas »*. À la géométrie 1,5/4,0 sur la même maille il
rend −0,018 ; sur 18 tests à 5 %, on attend ≈ 0,9 faux positif, et c'en est un candidat
naturel. Et quand bien même il serait réel : **+14 pips bruts contre 52 à 91 pips de
frais**. Il est mort économiquement avant d'être douteux statistiquement.

**Les deux dérives négatives** (cassure Donchian, compression) sont stables à travers les
géométries en M5. Elles ne sont pas exploitables en les inversant : les frais se paient
dans les deux sens, et −5 pips inversés font +5 pips contre 91 de coût.

---

## 4. La vraie contrainte : la faiblesse des déclencheurs, pas le prix de l'or

Première lecture, et elle était **fausse** : j'ai d'abord conclu que notre courtier était
trop cher sur l'or. La mesure comparative dit le contraire.

Coût d'un aller-retour rapporté à l'amplitude horaire, tous instruments en cache,
365 derniers jours :

| instrument | spread mesuré | ATR H1 | coût / ATR |
|---|---:|---:|---:|
| **XAUUSD** | 90,8 pips | 1 854 pips | **4,9 %** |
| USDJPY | 1,9 | 18 | 10,6 % |
| EURUSD | 1,8 | 11 | 16,4 % |
| GBPJPY | 6,7 | 24 | 28,3 % |
| AUDCAD | 6,0 | 11 | 55,5 % |
| CADCHF | 6,3 | 6 | 99,1 % |

**L'or est l'instrument le MOINS cher du portefeuille**, rapporté à ce qu'il bouge. Sa
volatilité absorbe son spread mieux que n'importe quelle paire FX. La contrainte n'est
donc pas le prix de l'or.

Ce qui reste vrai, et qui est le vrai obstacle : **la dérive des déclencheurs est
minuscule**. La meilleure vaut +15 pips quand l'ATR horaire de l'or en vaut 1 854 —
soit **0,8 % d'une amplitude horaire**. Un signal aussi faible ne devient exploitable à
aucune maille :

| Maille | Risque médian par trade | Part du R mangée par les frais |
|---|---:|---:|
| **H1** (la v1) | ~2 400 pips | **3,8 %** |
| M15 | 200 à 450 pips | 20 à 45 % |
| M5 | 110 à 270 pips | **34 à 83 %** |

Descendre en maille pour multiplier les occasions réduit le risque par trade et fait
exploser la part des frais. Monter en maille garde les frais négligeables mais raréfie
le signal — et il n'y avait rien à raréfier. **Sa méthode est du scalp intraday ; les
déclencheurs qu'on en a extraits n'ont pas la force nécessaire pour survivre à la maille
qu'ils exigent.**

### Deux erreurs de catalogue mises au jour au passage

La comparaison a révélé que le catalogue `app/core/data/instruments.py` est juste pour
presque tout — sauf là :

| instrument | catalogue | mesuré | écart |
|---|---:|---:|---:|
| **XAUUSD** | 25,0 | 90,8 | **3,6×** |
| **AUDCAD** | 3,2 | 6,0 | **1,9×** |
| **AUDCHF** | 2,2 | 4,2 | **1,9×** |
| **CADCHF** | 3,4 | 6,3 | **1,9×** |

Les paires FX majeures collent au catalogue à 10 % près, ce qui valide la conversion et
isole ces quatre cas.

**AUDCAD demande une action, pas une note** : c'est l'instrument principal de
`studies/s13_forward/`, un forward scellé **en cours** depuis le 16 août. Il valorise à
3,2 pips ce qui en coûte 6,0, sur un instrument dont le coût représente déjà 55 % de
l'amplitude horaire. Le dispositif ne mesure donc pas ce qu'il croit mesurer. À porter à
Adrian — la correction d'un scellé en cours n'est pas une décision d'exécutant (§ 3d de
son protocole : toute modification déclare l'invalidation plutôt que de la contourner).

## 5. Et la v1, au fait ?

Le criblage oblige à regarder l'étalon d'un œil moins complaisant. Décomposition du seul
objet qui fonctionne sur l'or, par année (source : `S018/backtests/results.json`) :

| | R | trades | R/trade | t |
|---|---:|---:|---:|---:|
| **2025 seule** | +55,9 | 96 | **+0,582** | **+3,57** |
| Toutes les autres années | +38,8 | 306 | +0,127 | **+1,39** |
| Ensemble | +94,7 | 402 | +0,236 | +2,95 |

**Hors 2025, l'avantage de la v1 n'est pas statistiquement détectable.** La réserve
« 59 % du résultat vient de 2025 » que portait déjà son dossier prend ici une forme
chiffrée : la significativité de la v1 repose sur une seule année.

Ce n'est pas une raison d'arrêter le forward scellé — c'est exactement la raison pour
laquelle il existe. Il teste la v1 **prospectivement**, hors de l'échantillon qui l'a
sélectionnée, et c'est la seule chose qui puisse trancher. Il en est à 7 trades sur 100.

---

## 6. Conséquences

1. **T6 n'a pas lieu.** Aucun candidat ne survit, et le plan l'écrivait d'avance :
   *« si aucun candidat ne survit à T5, T6 n'a pas lieu et le dossier se clôt sur un
   verdict »*. Construire S020 sur le candidat 5 serait exactement la sélection
   a posteriori que ce dispositif était fait pour empêcher.
2. **Aucune stratégie de ce dossier n'est prête pour le paper trading**, et aucune ne le
   sera par un travail de stratégie supplémentaire. L'obstacle est en amont.
3. **L'or n'est pas le problème** — c'est l'instrument le moins cher du portefeuille
   rapporté à sa volatilité (4,9 % contre 10 à 99 % pour le FX). Renégocier le spread ne
   rendrait pas ces déclencheurs rentables : leur dérive est trop faible d'un ordre de
   grandeur, pas d'un facteur.
4. **Sur l'or, seule la grosse maille est jouable** — non par cherté, mais parce qu'un
   risque de 2 400 pips absorbe les frais quand un risque de 150 pips ne le peut pas.
   Toute future stratégie or doit partir de là.
5. **Deux corrections de catalogue à porter à Adrian**, dont une urgente : AUDCAD est
   valorisé à 3,2 pips pour un coût réel de 6,0, et c'est l'instrument principal du
   forward scellé `studies/s13_forward/`, en cours depuis le 16 août.
6. **Le cribleur reste**, et il est réutilisable : il coûte quelques minutes et il aurait
   évité les deux campagnes de walk-forward de S019. À passer avant toute construction
   de stratégie, sur n'importe quel instrument.

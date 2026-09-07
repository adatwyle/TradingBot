# Croisement bilatéral, corpus purgé — verdict

**Date** : 2026-09-07 · **Données** : XAUUSD M1, 703 215 barres, 2024-09-09 → 2026-09-07
**Règle de purge** : `REGLE_purge_2026-09-07.md`, écrite et figée **avant** application
**Application mécanique** : `purge_corpus.py` · **Sens** : `docs/sources/doudtrading/_entries_sens_2026-09-07.json`
**Mesure** : `croisement_entrees_bilateral.py` · **Mesure d'origine, conservée** : `croisement_entrees.py`

---

## VERDICT : EFFECTIF INSUFFISANT

**9 observations** survivent la purge. Le seuil de 10, fixé dans la règle avant de voir
quoi que ce soit, place ce résultat sous la barre à partir de laquelle nous nous étions
autorisés à revendiquer une p-value. **Les taux ci-dessous sont descriptifs. Aucun
n'est revendiqué comme significatif.**

Ce n'est pas un échec de la mesure : c'est ce que le corpus contient réellement une
fois retirées les observations dont l'horodatage ne date pas l'entrée.

L'écart au témoin **persiste et grandit** une fois la mesure rendue bilatérale
(71 % contre 33 %). Nous ne pouvons pas dire que c'est du signal, et nous ne pouvons
pas dire que c'en est pas. Nous pouvons dire que **le corpus ne permet pas de trancher**,
et que le résultat publié le 6 septembre revendiquait une conclusion que ses données ne
portaient pas.

---

## 1. Effectif après purge

Corpus initial : **32 observations, 19 vidéos** (dont 20 marquées `aligne`).

| motif de purge | n |
|---|---|
| `prix-non-aligne` — prix non exploitable (P1) | 12 |
| `recit-retrospectif` — elle commente une position déjà ouverte, close, ou dont elle cite le résultat courant (P3) | 10 |
| `hors-trade` — exemple pédagogique, pas une position (P2) | 1 |
| **retenues** | **9** |

**9 observations, 9 vidéos — une par vidéo.** Le corpus d'origine tirait 20 observations
de 13 vidéos ; après purge, plus aucune vidéo n'en fournit deux.

**P5 (doublons et non-indépendance) n'a éliminé personne** — non parce qu'il n'y avait
pas de doublons, mais parce que les deux paires exactes signalées (`g0QZlUtQLvM` à
3335,48 ; `pO6DkqBIUFE` à 4063,00) étaient déjà tombées sur le critère de rétrospection,
appliqué avant. Le critère qui mord n'est pas le doublon : c'est l'horodatage.

---

## 2. Répartition des sens

| sens | n | établi par |
|---|---|---|
| **achat** | 6 | déclaration directe (2), stop chiffré sous l'entrée (2), cible chiffrée au-dessus (2) |
| **vente** | 1 | déclaration directe répétée (`a__0t9kh88w` : « Je suis parti à la vente là ») |
| **indéterminé** | 2 | ni déclaration, ni niveau chiffré rattaché à la position |

**Le corpus est massivement acheteur — l'inverse de ce que le champ `sens_hints`
laissait craindre.** Sur les 4 observations du corpus d'origine qui portaient un
`sens_hints` (toutes « vente » ou « vendeur »), 3 sont purgées ; la seule survivante,
`QbkYJMzeodI`, est **acheteuse** :

> « Après, il est très il est très vendeur. Attention, quand tu traites contre
> tendance, faut pas s'étonner. […] Moi, je suis rentré au 40649 » — puis, deux minutes
> plus tard : « **Tant qu'on reste sur la zone des 59, moi je l'achète hein.** »

Le mot « vendeur » décrivait le marché, pas sa position. Elle achète un marché qu'elle
juge vendeur, et le dit. `sens_hints` produisait un faux positif de sens ; il n'a pas
été utilisé.

**Conséquence sur le défaut (b).** Le risque anticipé — « on a mesuré du P&L long sur
des trades possiblement vendeurs » — ne s'est **pas** matérialisé sur le corpus
survivant : 6 achats sur 7 sens connus. Le détecteur unilatéral haussier était donc,
par accident, aligné avec la majorité des observations. Cela n'excuse pas sa
construction ; cela veut dire que la correction du sens **n'est pas** ce qui déplace
le résultat. Ce qui le déplace, c'est la purge.

---

## 3. La mesure

**Balayage achat** : une barre M1 perce le plus-bas des 60 barres qui la précèdent
**et referme au-dessus** — le perçage est rejeté par le haut.
**Balayage vente** : symétrique — perce le plus-haut des 60 barres **et referme en
dessous**. Mêmes profondeur d'historique, même fenêtre de 30 barres, même seuil de
mèche. Seul le côté du prix change.

Pour une observation de sens connu, **seul le balayage cohérent avec son sens est
testé**. Témoin : 200 tirages, mêmes heures de session, graine 20260906, **et un sens
attribué à chaque tirage selon la même distribution que le corpus purgé** — sans quoi
on comparerait un test bilatéral à un témoin unilatéral.

### Bras principal — sens connu, balayage cohérent

| | n | taux |
|---|---|---|
| **ses entrées** | **5/7** | **71 %** |
| **témoin** | **51/153** | **33 %** |
| p unilatérale (binomiale exacte) | | **0,045** |

Témoin par sens, pour montrer que la symétrie tient : balayage achat **46/139 = 33 %**,
balayage vente **5/14 = 36 %**. Les deux définitions se déclenchent au même rythme sur
du bruit — la branche vente n'est ni plus laxiste ni plus sévère que la branche achat.

### Bras séparé — sens indéterminé

n = 2. Balayage haussier **1/2**, baissier **2/2**, l'un ou l'autre **2/2**. Témoin
indéterminé (l'un ou l'autre) **28/47**. Non fusionnées au bras principal : leur sens
n'étant pas établi, les y compter reviendrait à choisir le côté qui arrange.

### Bras mixte — tout le corpus purgé

Sens connu → balayage cohérent seul ; sens indéterminé → l'un ou l'autre. Le témoin est
construit à l'identique.

| | n | taux |
|---|---|---|
| ses entrées | 7/9 | 78 % |
| témoin | 79/200 | 40 % |
| p unilatérale | | 0,023 |

### L'ancienne définition, rejouée sur le corpus purgé

Balayage **haussier seul**, quel que soit le sens réel — exactement ce que mesurait
`croisement_entrees.py` :

| | n | taux |
|---|---|---|
| ses entrées | 5/9 | 56 % |
| témoin | 64/200 | 32 % |
| p unilatérale | | **0,125** |

Lecture : **rendre la mesure bilatérale la renforce** (p 0,125 → 0,045), parce que le
seul trade vendeur du corpus, `a__0t9kh88w`, est précédé d'un balayage **baissier** que
l'ancien détecteur ne pouvait pas voir. Le défaut (a) travaillait contre le résultat,
pas pour lui.

---

## 4. Le chiffre qui change de camp : les excursions

Le verdict du 6 septembre fondait son § 3 — et la recommandation d'architecture qui en
découle — sur un **rapport MFE/MAE médian de 1,80**, « le marché lui donne près du
double de ce qu'il lui prend ». Ce chiffre était calculé en P&L **long** sur les
20 observations non purgées.

Recalculé **orienté selon le sens réel**, sur les 7 observations de sens connu :

| | médiane |
|---|---|
| MFE (en sa faveur) | **1 088 pips** |
| MAE (contre elle) | **1 241 pips** |
| **rapport MFE/MAE** | **0,88** |

**Le rapport passe sous 1.** Sur ce corpus, dans les 60 minutes qui suivent, le marché
lui prend un peu plus qu'il ne lui donne. Deux observations portent l'essentiel du
retournement : `tfh-B0Uroe4` (MFE **−27** pips — le prix n'est jamais repassé au-dessus
de son entrée dans l'heure, et elle le raconte en direct : « il m'a sorti ») et
`a__0t9kh88w` (vente, MFE 2 688 contre MAE 4 243).

**Sur 7 observations, ce chiffre ne vaut rien de plus que le précédent.** Mais il ne
vaut rien de moins. La conclusion « ses entrées ont un profil favorable » ne peut plus
être présentée comme mesurée : elle reposait sur un P&L calculé dans le mauvais sens
pour une partie du corpus, et sur des observations dont l'entrée précédait la parole.

---

## 5. Deux contrôles de sensibilité — tous deux post-hoc, tous deux explicites

### 5.1 La largeur de la fenêtre de contexte décide du résultat

La règle applique les marqueurs de rétrospection au champ `ctx` du corpus, une fenêtre
d'environ 250 caractères. Ce n'est pas un choix : c'est ce que le fichier contient.
Appliqués aux **mêmes marqueurs** sur la transcription complète **± 150 s** autour du
timecode (`purge_corpus.py --fenetre-large`) :

| | effectif |
|---|---|
| règle pré-enregistrée (champ `ctx`) | **9** |
| fenêtre ± 150 s | **2** |

**Sept des neuf survivantes tombent.** `VgZx8e4k2lE` dit « j'y suis », « actuellement »
et « qui tournent » dans les deux minutes autour de son entrée ; `QbkYJMzeodI`,
`G7LP5bb6UhU`, `pO6DkqBIUFE`, `a__0t9kh88w` et `5IPouztc1_0` citent tous un résultat
courant à quelques dizaines de secondes.

C'est le résultat le plus important de ce document, et il n'est pas un chiffre :
**la frontière entre « elle vient d'entrer » et « elle raconte » dépend d'une largeur
de fenêtre que personne n'a fixée**, et la déplacer de 250 caractères à 5 minutes fait
passer l'effectif de 9 à 2. Une mesure dont le corpus varie d'un facteur 4,5 selon un
paramètre non spécifié n'est pas une mesure — c'est une plage.

À décharge : ± 150 s est un filet très large, et « actuellement » est un mot qu'elle
prononce constamment. La vérité est entre les deux, et nous n'avons aucun moyen de dire
où. C'est précisément le problème.

### 5.2 Si l'on rattachait les indéterminées à leur faisceau

Les 2 observations indéterminées portent un `indice_non_retenu` qui penche `achat` dans
les deux cas (pour `5IPouztc1_0` : le gain qu'elle annonce croît — 177 $, 227 $, 500 $ —
pendant que le prix monte de 4492 à 4497). Cet indice n'entre pas dans les critères
tranchants pré-enregistrés. S'il y entrait (`--sens-indices`) :

| | n | taux |
|---|---|---|
| ses entrées | 6/9 | 67 % |
| témoin | 64/200 | 32 % |
| p unilatérale | | 0,035 |

L'effectif reste sous 10. Le verdict ne change pas.

---

## 6. Un défaut de reproductibilité, découvert en route

`croisement_entrees.py`, **relancé aujourd'hui sans aucune modification**, ne reproduit
pas les chiffres qu'il a publiés hier :

| | témoin | p |
|---|---|---|
| publié le 2026-09-06 | 78/200 = **39 %** | 0,047 |
| même script, même graine, 2026-09-07 | 64/200 = **32 %** | **0,009** |

Le taux observé (12/20 = 60 %) est stable ; c'est **le témoin** qui bouge. Cause :
`load_bars("XAUUSD", "M1", days=365 * 2)` ancre la fenêtre de données à l'instant
présent. En 24 heures, 670 barres se sont ajoutées, le vivier de tirage a glissé, et
les 200 instants tirés avec la même graine ne sont plus les mêmes.

**Le « p = 0,047 » publié n'est donc pas une quantité fixe.** Il dérive d'un jour à
l'autre — ici dans le sens de la significativité, ce qui ne le rend pas plus solide.
Toute étude de ce dossier doit épingler ses bornes de données (`start`/`end` explicites)
au lieu de `days=N` relatif à aujourd'hui. Ce défaut est indépendant de tout ce qui
précède et affecte aussi la mesure du présent document.

---

## 7. Ce que nous retenons

1. **Le résultat fondateur ne tient pas dans la forme où il a été publié.** Pas parce
   qu'il serait faux — parce que son corpus contenait 23 observations sur 32 qu'un
   critère mécanique écrit à l'avance élimine, et que son témoin n'est pas reproductible
   d'un jour sur l'autre.
2. **L'écart au témoin survit à la purge et à la bilatéralisation, et il grandit**
   (71 % contre 33 %). Sur 7 observations, cela ne démontre rien. Cela ne s'efface pas
   non plus.
3. **Le sens n'était pas le problème.** Le corpus est acheteur à 6 contre 1 ; le
   détecteur unilatéral était accidentellement aligné. Corriger le sens **améliore** le
   résultat au lieu de le détruire. Le problème était l'horodatage.
4. **Le rapport MFE/MAE de 1,80 ne survit pas.** Orienté et purgé, il vaut 0,88. Le § 3
   du verdict du 6 septembre, et l'argument d'architecture qu'il portait (« notre stop
   couperait 40 % de ses trades »), doivent être considérés comme non mesurés.
5. **Ce dossier ne peut pas être conclu avec ce corpus.** Il faut soit davantage
   d'observations dont l'entrée est horodatée au moment de l'entrée, soit renoncer à
   fonder S019 sur cette mesure. Les deux sont des décisions ; aucune n'est un constat
   que ce document peut produire seul.

---

## 8. Ce que ce verdict ne dit pas

- **Rien sur la rentabilité de sa méthode.** MFE et MAE décrivent ce que le marché
  offre, pas ce qu'elle en tire.
- **Rien sur ses trades non annoncés.** Le biais de sélection est intact : ce sont les
  entrées qu'elle cite à voix haute en direct.
- **Aucun coût.** Chiffres bruts, ni spread (≈ 52 pips, `TCK-018`), ni slippage.
- **Il ne réhabilite pas et ne condamne pas le déclencheur par balayage.** Il constate
  que le corpus disponible ne permet pas de le juger.

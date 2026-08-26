# Analyse — s91_claude_scratch (Phase 1)

Source : **conception autonome**. Il n'y a aucune source externe à reproduire.
Auteur : Claude Code, agent dédié `s91_claude_scratch`.
Données : MT5 Swissquote, H1, 2021-07-18 → 2026-08-16, ~31 594 barres/instrument.
Heures : **heure serveur MT5** (≈ GMT+2/+3), calibrée par le projet sur le profil
de volatilité EURUSD (pic Londres/NY à l'heure serveur 16).

---

## 1. D'où vient cette stratégie — les mesures du projet, pas une intuition

Je ne pars pas d'une idée séduisante. Je pars des huit faits que ce projet a
**mesurés**, et je cherche la seule case du plan qu'ils laissent ouverte.

| # | Fait mesuré | Ce qu'il ferme | Ce qu'il ouvre |
|---|---|---|---|
| 1 | Péage spread : H1 = 2,14 pts de WR, H4 = 1,04, D1 = 0,46 | toute géométrie à faible distance de risque | rien — c'est une contrainte, pas une piste |
| 2 | Tout le trend-following a échoué (Donchian, MTF, pullback, structure fractale) | la famille « suivre » en entier | son complément logique |
| 3 | **Le mean-reversion est la seule famille ayant montré du signal** | — | **la piste** |
| 4 | Diversification : corrélation moyenne +0,005, DD portefeuille 8,9 % vs 28,7 % | la mono-paire | un panier homogène |
| 5 | Concentration = 93 % du résultat sur un instrument → pas un système | tout résultat mono-instrument | — |
| 6 | Le critère STRICT 4/4 est fragile (4 paires sur 5 cassées en 3 mois) | STRICT lu seul | STRICT **et** Tier 1 côte à côte |
| 7 | Les tendances 2021-2026 fabriquent de faux edges directionnels (USDJPY +69,7 R long / −10,0 R short) | tout résultat non contrôlé en long/short | contrôle directionnel obligatoire |
| 8 | Ambiguïté intra-barre négligeable (0,3 %) pour des stops à 1,5-2 ATR | le doute sur le modèle barre H1 | on peut travailler en H1 |

Et un neuvième, qui traîne dans le dépôt sans avoir jamais servi :

> **Calibration horaire (TODO.md, « CALIBRATION UTILE ») :** zone morte serveur
> 22-07h = 7,0-8,8 pips d'amplitude ; pic 14-16h = 23,0-25,7 pips.
> **Écart 3,7×.** `time_filter_analysis.py` est écrit, testé 8/8 — **jamais lancé.**

C'est le seul axe mesuré que personne n'a croisé avec le fait #3. Toute la
recherche du projet s'est faite sur l'axe *quoi* (quel indicateur, quelle
structure, quel timeframe) et jamais sur l'axe *quand dans la journée*.

**Le raisonnement :** le mean-reversion est un pari sur le fait qu'un écart de
prix n'est pas de l'information. Un écart n'est pas de l'information quand il
est produit par un carnet mince plutôt que par du flux transactionnel. Le projet
a mesuré exactement où le carnet est mince : la fenêtre serveur 22-06h, où
l'amplitude tombe à 2,2-2,4× en dessous du pic. C'est là, et pas ailleurs,
qu'une extension devrait être du bruit — donc réversible.

---

## 2. Ma première formulation, et pourquoi elle est morte

Ma première hypothèse était l'**inverse** : la réversion serait concentrée au
**pic** Londres/NY, parce que les impulsions y sont les plus fortes (donc les
plus susceptibles de sur-réagir) et parce que la distance de risque y étant
grande, le péage du spread y est le plus faible.

`research/economics.py` (plein échantillon) l'a réfutée avant que j'écrive une
ligne de stratégie (`research/economics.txt` §3) :

```
                    rev PEAK   rev DEAD   rev AUTRE   rev TOUT
  MOYENNE            -0.038     -0.293      +0.154     -0.042
```

Au pic, la dérive de retour à la moyenne est **nulle voire négative**
(−0,038 pips). L'hypothèse « la sur-réaction est au pic » est fausse sur ces
données. Je la consigne ici plutôt que de l'effacer : c'est la trace qui prouve
que la formulation retenue en §3 n'est pas la première venue.

---

## 3. HYPOTHÈSE H91 — énoncé figé

> **Dans la fenêtre de faible liquidité (heure serveur 22h–06h), une extension
> de prix sur H1 n'est pas de l'information mais du bruit de carnet mince, et
> elle se rétracte partiellement. Cet effet n'existe que pour les paires dont
> aucune devise n'a de session domestique à ce moment-là. Pour les paires JPY,
> cette même fenêtre est la session de Tokyo — donc du vrai flux — et l'effet
> doit y être absent ou inversé.**

Ce n'est pas une affirmation sur un indicateur. C'est une affirmation sur le
**marché** : *la réversibilité d'un écart dépend de la présence ou non d'une
session domestique active pour les devises concernées.*

### 3.1 Elle fait une prédiction différentielle, pas seulement un PnL

C'est ce qui la rend testable au-delà du « est-ce que ça gagne ». H91 prédit un
**clivage** :

| Groupe | Devises en jeu à 22-06h serveur | Prédiction H91 |
|---|---|---|
| EURUSD, USDCHF, USDCAD, AUDUSD | aucune session domestique majeure | effet **présent** |
| USDJPY, EURJPY | **session de Tokyo** | effet **absent ou inversé** |

Les deux paires JPY ne sont donc pas exclues du test : elles y sont maintenues
comme **contrôle négatif déclaré**. Si elles réussissent aussi bien que les
autres, le mécanisme invoqué est faux — même si le PnL global est positif.

Le fondement de ce clivage est lui-même mesuré, pas supposé
(`economics.txt` §1) :

| | ATR global | ATR @ 22-06h | ratio pic/creux | PEAK/DEAD |
|---|---|---|---|---|
| EURUSD | 13,0 | 13,0 | 3,67 | **2,44** |
| USDCHF | 11,6 | 11,6 | 3,39 | **2,21** |
| USDCAD | 13,7 | 13,8 | 3,41 | **2,30** |
| AUDUSD | 11,7 | 11,7 | 3,53 | **1,63** |
| **USDJPY** | 21,0 | 21,1 | 3,25 | **1,54** |
| **EURJPY** | 22,6 | 22,6 | 2,64 | **1,47** |

Le rapport PEAK/DEAD est de 2,21 à 2,44 pour EURUSD/USDCHF/USDCAD et tombe à
1,47-1,54 pour les paires JPY. **La « zone morte » n'est pas morte pour le yen.**
C'est ce chiffre-là qui fonde le clivage, pas une préférence.

AUDUSD à 1,63 est un cas intermédiaire — l'AUD a bien une session domestique
asiatique. Il est conservé dans le groupe éligible parce que l'exploration §4.2
le classe avec les non-JPY, mais c'est le membre le plus faible du groupe et il
doit être lu comme tel.

---

## 4. L'ÉCONOMIE DU TRADE — calculée avant d'écrire la stratégie

C'est l'étape que le projet impose de trancher en premier.

### 4.1 Le critère que je m'impose

Le péage du spread est un coût **fixe en pips** par trade (le moteur le facture
à l'entrée et à la sortie). La marge est la dérive brute exploitable. Donc :

```
    critère a priori :   dérive brute (pips)  >  spread aller-retour (pips)
```

Exprimé en R, c'est identique : `drag = spread / distance de risque` est le coût
en R par trade, indépendant du R:R, et l'espérance brute doit le dépasser.

### 4.2 Le calcul, sur la tranche d'entraînement uniquement

Mesuré dans `research/explore_train.txt` §B — dérive à 8 barres, |z| >= 2,0,
fenêtre 22-06h, **60 % premiers de l'historique** (2021-07-18 → 2024-08-01) :

| instrument | spread A/R | dérive DEAD | **marge nette** | n |
|---|---|---|---|---|
| EURUSD | 1,9 | +5,67 | **+3,77** | 134 |
| USDCHF | 2,2 | +4,99 | **+2,79** | 123 |
| USDCAD | 3,1 | −0,09 | −3,19 | 186 |
| AUDUSD | 2,0 | +0,05 | −1,95 | 469 |
| USDJPY *(contrôle)* | 2,8 | −5,98 | −8,78 | 417 |
| EURJPY *(contrôle)* | 3,6 | −6,29 | −9,89 | 348 |

**Groupe éligible (4 paires non-JPY) :** dérive brute moyenne **+2,66 pips**,
spread moyen **2,30 pips** → **marge nette +0,36 pips, soit 16 % au-dessus du
coût.**

**Groupe de contrôle (2 paires JPY) :** marge **−9,33 pips**. Le clivage prédit
par H91 est présent sur l'entraînement, et il est massif.

Deux des quatre paires éligibles (USDCAD, AUDUSD) sont **déjà négatives sur
l'entraînement**. La marge du groupe tient à EURUSD et USDCHF. C'est un signal
d'alarme, et je le consigne ici, avant le backtest.

### 4.3 Géométrie retenue et péage correspondant

`explore_train.txt` §C, ATR(24) médian dans la fenêtre, sur entraînement :

| instrument | ATR DEAD | risque @2,5×ATR | drag | WR requis à R:R 1,0 |
|---|---|---|---|---|
| EURUSD | 13,2 | 32,9 pips | 5,77 % | 52,9 % |
| USDCHF | 12,3 | 30,7 | 7,16 % | 53,6 % |
| USDCAD | 15,1 | 37,7 | 8,23 % | 54,1 % |
| AUDUSD | 12,7 | 31,8 | 6,29 % | 53,1 % |
| USDJPY | 19,6 | 48,9 | 5,72 % | 52,9 % |
| EURJPY | 22,7 | 56,7 | 6,35 % | 53,2 % |

Le stop est volontairement **large** (2,0 à 3,0 × ATR) : c'est le seul levier
disponible sur H1 pour réduire le drag, puisque changer de timeframe détruit le
mécanisme (une barre H4 chevauche la frontière de session et efface la fenêtre).
Le R:R est proche de 1 — c'est ce qui minimise le nombre de points de WR à
gagner au-dessus du hasard : `points requis = 100 × drag / (1 + R:R)`.

**Conclusion économique a priori — et elle est inconfortable :** le critère
passe, mais de **16 %**. Ce n'est pas une marge, c'est un liseré. J'écris ici,
avant tout backtest, que **je m'attends à un résultat nul ou marginal hors
échantillon**, et que la valeur de ce travail sera la mesure, pas le gain.
Si le résultat sortait très positif, le premier réflexe devrait être de chercher
l'erreur, pas de célébrer.

---

## 5. Conception — décidée sur l'entraînement, puis gelée

| Composant | Choix | Justification (train uniquement) |
|---|---|---|
| Timeframe | **H1** | seul TF où la frontière de session est résolue ; H4 la lisse, D1 donne 3-13 trades/5 ans (fait #8 autorise H1) |
| Fenêtre | heure serveur **22-06h** (« large ») ou **23-04h** (« etroite ») | la zone morte mesurée du projet ; deux largeurs pour tester la robustesse du bord |
| Extension | z = (close − SMA20) / ecart-type20, seuil abs(z) >= z_min | mesure d'écart la plus simple possible ; aucun indicateur composite |
| Sens | **contre** l'extension | famille mean-reversion (fait #3) |
| Stop | k × ATR(24) au-delà de l'entrée | large par nécessité économique (§4.3) |
| Cible | rr × risque | R:R proche de 1 pour minimiser les points de WR requis |
| Instruments | EURUSD, USDCHF, USDCAD, AUDUSD **+ USDJPY, EURJPY en contrôle négatif** | fait #4 (panier), fait #5 (pas de mono-instrument), clivage §3.1 |
| Gestion | aucune (set & forget) | le moteur commun n'expose pas de sortie temporelle dans le walk-forward — limite assumée, §7.2 |

### 5.1 Grille — 54 configurations, volontairement petite

```
z_min   : 1.5, 2.0, 2.5          (3)
sl_atr  : 2.0, 2.5, 3.0          (3)
rr      : 0.75, 1.0, 1.5         (3)
window  : large, etroite         (2)
                                 -- 54
```

54 configurations produisent **environ 2,7 « STRICT pass » par instrument par
pur hasard**. Tout comptage sera lu contre ce nombre, jamais dans l'absolu.

Je n'ajoute **aucun** paramètre de filtre (pas de filtre de tendance, pas de
filtre de volatilité, pas de RSI de confirmation). Chaque paramètre ajouté
multiplie le nombre de faux positifs disponibles. La grille est là pour
mesurer la sensibilité de l'hypothèse, pas pour chercher une cellule gagnante.

---

## 6. CONDITIONS DE FALSIFICATION — déclarées avant le premier backtest

Je suis à la fois le concepteur et l'évaluateur. C'est le pire conflit d'intérêt
méthodologique qui soit. Le seul garde-fou est d'écrire les conditions
maintenant et de m'y tenir même si elles me contredisent.

| # | Condition | Si elle se réalise |
|---|---|---|
| **F1** | Espérance brute **à spread nul** <= 0 R/trade en moyenne sur les 4 paires éligibles, plein échantillon | Le signal de réversion n'existe pas. **H91 réfutée.** Ce n'est pas un problème de coûts. |
| **F2** | Les 2 paires **JPY** ne se comportent **pas** moins bien que les 4 éligibles | Le mécanisme de session invoqué est faux. **H91 réfutée**, même si le PnL est positif — ce serait alors autre chose, et je n'ai pas le droit de le baptiser H91. |
| **F3** | Nombre de **STRICT** sur les 4 éligibles <= nombre attendu par hasard (54 × 0,05 × 4 = 10,8) | Aucun edge distinguable du bruit de grille. **H91 réfutée.** |
| **F4** | Le résultat positif tient à **un seul instrument** (> 60 % du total positif) ou à **un seul sens** (long ou short seul positif) | Ce n'est pas un système mais un pari (faits #5 et #7). **Non concluant au mieux**, jamais un edge. |
| **F5** | Effectif hors échantillon médian **< 20 trades** par instrument | Puissance insuffisante. **Non concluant** — interdiction de conclure dans un sens ou dans l'autre. |

**Règle que je m'impose en plus :** je ne modifierai ni la grille, ni les
instruments, ni la fenêtre après avoir vu le walk-forward. Si le résultat est
mauvais, il est mauvais.

---

## 7. Limites connues — dites maintenant, pas après

### 7.1 L'hypothèse est formée sur des données que je vais aussi tester

C'est la limite principale et je ne peux pas l'annuler. Atténuation appliquée :
l'exploration qui a fixé H91, ses seuils et sa sélection d'instruments a été
**refaite sur les 60 % premiers uniquement** (`explore_train.py`), c'est-à-dire
la première fenêtre d'entraînement du walk-forward ancré. Les tranches de test
(60-100 %) n'ont pas servi à concevoir.

Contamination résiduelle **déclarée** : j'ai vu le tableau plein échantillon
d'`economics.py` (§2 ci-dessus) avant de restreindre au train. Il a servi à
éliminer ma première hypothèse (le pic), pas à construire la seconde. Le lecteur
doit néanmoins traiter tout chiffre hors échantillon de ce dossier comme une
**borne haute**, exactement comme le fait `TODO.md` pour le reste du projet.

### 7.2 La sortie temporelle, qui serait fidèle au mécanisme, est inaccessible

Le mécanisme dit : la rétractation se produit *pendant* que la liquidité est
mince, et la position devrait être fermée avant le retour du flux (ouverture de
Londres). `core/backtest/engine.run()` accepte bien `max_hold_bars`, mais
`run_walk_forward` ne le transmet pas, et une stratégie n'a pas le droit
d'exprimer une sortie temporelle (elle n'émet que entry/stop/target).
Écrire ma propre boucle violerait R9.

**Conséquence assumée :** les positions traversent l'ouverture de Londres, où la
volatilité triple. Le test porte donc sur une version **dégradée** du mécanisme.
Une réfutation de cette version ne réfute pas totalement H91 ; une validation, en
revanche, serait valable *a fortiori*.

### 7.3 Autres limites

- **Un seul régime** : 2021-2026 (hausse du dollar, choc 2022, carry yen). Ce
  n'est pas un échantillon de régimes.
- **6 instruments**, tous FX. GBPUSD est en cache mais absent de
  `core/data/instruments.py` — l'ajouter exigerait de modifier `core/`, interdit.
- **XAUUSD volontairement exclu** : le mécanisme est une histoire de sessions de
  devises, l'or n'en a pas ; et le projet a déjà établi (VERDICT s01 §3.3) que
  l'or est l'endroit où un signal à somme nulle paraît le plus facilement
  positif, du fait de son péage faible. L'inclure aurait maquillé le résultat.
- **Slippage non modélisé** (limite du moteur). Il ne peut qu'aggraver.
- **R5 (conformance) non exécutable** : `core/validation/conformance.py`
  n'existe pas dans le dépôt. Atténuation structurelle : `on_bar()` appelle
  littéralement `precompute()` puis `generate_signals()` et ne retient que la
  décision de la barre courante — il n'existe pas deux implémentations pouvant
  diverger.
- **`tick_volume` non utilisé.** Il aurait été le proxy naturel de « carnet
  mince », mais c'est un compteur de changements de cotation, pas un volume
  (cf. `core/data/source.py`). L'heure est un proxy plus honnête et plus stable.
- **L'heure serveur est une calibration empirique**, pas une donnée du broker.
  Un changement d'heure d'été décale la fenêtre d'une heure deux fois par an ;
  ce bruit n'est pas corrigé.

---

## 8. Fichiers de la Phase 1

| Fichier | Contenu |
|---|---|
| `research/economics.py` / `.txt` | Profil horaire, péage par géométrie, signature de réversion — **plein échantillon**. A réfuté la première hypothèse. |
| `research/explore_train.py` / `.txt` | Même mesure sur les **60 % d'entraînement**. C'est de ce tableau, et de lui seul, que H91 est tirée. |
| `research/ANALYSIS.md` | Ce document. Hypothèse, économie a priori, falsification. |

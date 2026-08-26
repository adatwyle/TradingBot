# Verdict — FXAlexG Swing HTF (Phase 4)

Source : https://www.youtube.com/@fxalexg__ — fxalexg (~1,3 M abonnés)
Données : MT5 Swissquote, H1, 2021-07-18 → 2026-08-14 (5,1 ans, ~31 600 barres/instrument)
Structure lue en H4 et D1, rééchantillonnées depuis ces mêmes H1
Grille : 128 configurations × 7 instruments = **896 cellules**
R1 (causalité) : **PASSÉ**, vérifié sur 32 points de la grille — pas seulement le défaut

---

## 1. Ce que la source affirme

Le transcript ne contient **aucun chiffre de performance** : ni win rate, ni R:R,
ni drawdown, ni rendement. Il n'y a donc pas de claim numérique à confronter.

Ce qu'il affirme est qualitatif, et c'est ce qui a été testé :

| # | Affirmation | Testable ? |
|---|---|---|
| A1 | Les timeframes élevés sont « très prévisibles » car une structure y met longtemps à se former | Oui — c'est l'hypothèse centrale |
| A2 | La structure se lit en HH/HL puis en bascule LL/LH | Oui |
| A3 | On n'entre jamais en chasse : on attend le retracement, on anticipe le lower high | Oui |
| A4 | Top-down : direction en haut, entrée en bas | Oui |
| A5 | Set & forget, détentions de 5-7 jours | Oui, et vérifié séparément (§2.4) |
| A6 | Sélectivité : 1-2 trades/jour maximum | Oui, borne haute jamais approchée |

Aucun track record audité n'a été trouvé. Le verdict ne porte donc pas sur la
sincérité de l'auteur, mais sur la **règle mécanique la plus fidèle que nous
sachions écrire à partir de sa description**.

---

## 2. Ce que nous mesurons

### 2.1 Walk-forward ancré — le critère principal

| instrument | STRICT | attendu par hasard | TIER 1 | trades OOS (médiane) | moy OOS sur la grille |
|---|---|---|---|---|---|
| EURUSD | **0** | 6,4 | 0 | 82 | −3,08 R |
| USDJPY | **8** | 6,4 | 4 | 83 | +0,40 R |
| USDCHF | **0** | 6,4 | 0 | 82 | −5,37 R |
| AUDUSD | **0** | 6,4 | 1 | 76 | −3,78 R |
| USDCAD | **0** | 6,4 | 0 | 78 | +0,89 R |
| EURJPY | **0** | 6,4 | 0 | 72 | −4,00 R |
| XAUUSD | **11** | 6,4 | 0 | 66 | +3,21 R |
| **TOTAL** | **19** | **44,8** | **5** | | |

**Le point décisif : 19 réussites STRICT là où le pur hasard en produirait ~45.**
La grille ne fait pas seulement « pas mieux » que le hasard, elle fait
**deux fois moins bien**. C'est la signature d'une espérance négative, pas d'un
edge noyé dans le bruit.

Les effectifs sont corrects (66 à 83 trades hors échantillon par instrument,
au-dessus du seuil de crédibilité de 20). Ce n'est donc pas un problème de
puissance statistique : le résultat négatif est **mesuré**, pas subi.

### 2.2 Plein échantillon — 56 cellules diagnostiques

Espérance par trade, moyenne sur les 7 instruments (spread réel inclus) :

| structure | cible | R/trade moyen | instruments positifs |
|---|---|---|---|
| D1 | struct | −0,1206 | 0/7 |
| D1 | ext27 | −0,1035 | 2/7 |
| D1 | ext62 | −0,0633 | 2/7 |
| D1 | rr3 | −0,0999 | 2/7 |
| H4 | struct | −0,1340 | 1/7 |
| H4 | ext27 | −0,1221 | 0/7 |
| H4 | ext62 | −0,0971 | 1/7 |
| H4 | rr3 | −0,0822 | 2/7 |

**Les 8 familles sont négatives. 10 cellules sur 56 sont positives.**
Aucune n'atteint +0,10 R/trade sauf sur XAUUSD (§3.3).

### 2.3 Ablation du spread — d'où vient exactement la perte

Mêmes signaux, même moteur, `spread_pips` passé de sa valeur réelle à zéro :

| | R/trade moyen (56 cellules) | cellules positives |
|---|---|---|
| spread réel Swissquote | **−0,1028** | 10/56 |
| spread nul | **−0,0082** | 27/56 |
| **coût du spread** | **−0,0946 R/trade** | |

C'est le résultat le plus informatif de tout le test, et il coupe court à deux
excuses :

* **« ça marcherait avec un meilleur broker »** — non. À spread **strictement
  nul**, le signal est à −0,008 R/trade et 27/56 cellules positives, soit
  exactement une pièce non biaisée. Il n'y a **rien à sauver** en dessous du
  péage.
* **« le spread n'est pas le problème »** — si, pour la partie visible. Le
  péage transforme un signal à somme nulle en un système perdant de façon
  fiable. Sur H1, la distance de risque mesurée est de 20 à 45 pips, soit un
  drag de **6,6 % à 12,7 % du risque** (USDCAD le pire à 12,7 %, XAUUSD le
  meilleur à 2,4 %).

Autrement dit : **la lecture de structure telle que formalisée ici n'apporte
aucune information exploitable.** Elle sélectionne des trades dont l'espérance
brute est nulle.

### 2.4 Test de fidélité — la détention est-elle bien « de plusieurs jours » ?

Ce test avait été fixé **avant** de connaître les résultats (ANALYSIS §7) : si la
durée ne tombait pas dans l'ordre de grandeur annoncé, le verdict devrait être
`NON REPRODUCTIBLE` plutôt qu'un jugement sur l'edge.

Durée de détention des trades **gagnants** (les perdants sortent vite, chez lui
comme chez nous) :

| famille | médiane | p75 | conforme aux 5-7 j annoncés ? |
|---|---|---|---|
| D1 / ext62 | **2,5 à 5,2 jours** | 4,8 à 10,2 j | **oui** |
| D1 / ext27 | 1,7 à 2,9 j | 3,0 à 5,1 j | ordre de grandeur |
| D1 / struct | 0,7 à 1,6 j | 1,4 à 2,4 j | trop court |
| H4 / toutes | 0,2 à 1,2 j | 0,4 à 2,7 j | **non** |

**La famille D1/ext62 reproduit bien le régime décrit par la source** (médiane
4,1 j sur EURUSD, 5,2 j sur XAUUSD, p75 jusqu'à 10 j). Elle est aussi la moins
mauvaise du tableau §2.2 (−0,0633 R/trade). Mais elle reste négative.

Le premier réflexe aurait été de conclure `NON REPRODUCTIBLE` en voyant les
familles H4. Ce serait faux : **le régime long est bien atteint, et il perd
aussi.** La fidélité n'est donc pas l'explication de l'échec.

### 2.5 Sélectivité

De 110 à 400 trades sur 5,1 ans par instrument, soit **0,06 à 0,22 trade par
jour**. La borne « 1-2 par jour » annoncée par la source n'est jamais approchée
— sur un panier de 7 instruments on atteindrait ~1 trade/jour, ce qui est
cohérent avec sa pratique.

---

## 3. L'écart, et son explication

### 3.1 Il n'y a pas d'écart chiffré à expliquer

La source n'annonce aucune performance. L'écart porte sur la **thèse** : « les
timeframes élevés sont très prévisibles ». Formalisée en règle de structure
fractale, cette prévisibilité **ne se manifeste pas dans nos données**.

### 3.2 Pourquoi la thèse ne se transfère pas

L'ablation du spread donne la réponse mécanique. Le signal est à somme nulle
avant coûts. Trois explications non exclusives :

1. **La structure fractale est un descripteur rétrospectif, pas prédictif.**
   HH/HL décrit ce que le prix a fait. Rien dans nos mesures n'indique qu'elle
   informe sur la suite. Le fait que l'espérance brute soit à ~0,000 R/trade —
   et non négative — est cohérent avec un découpage neutre d'une série
   quasi-aléatoire.
2. **Le délai de confirmation coûte l'information.** Un swing n'existe qu'après
   `k` barres. C'est une contrainte de causalité incompressible (R1), et c'est
   aussi la réalité du trader en direct. Mais elle rogne la partie du mouvement
   qui suit immédiatement le point pivot.
3. **Ce qu'il fait n'est peut-être pas ce qu'il décrit.** C'est la limite
   irréductible : voir §6.1.

### 3.3 Le seul résidu non écarté — XAUUSD

Honnêteté oblige : **une poche résiste.** XAUUSD produit 11 STRICT (contre 6,4
attendues), avec des effectifs sérieux (96 à 179 trades hors échantillon) et un
voisinage cohérent. Examiné de près :

| test | résultat |
|---|---|
| Meilleure cellule, plein échantillon | 406 trades, **+86,6 R**, +0,213 R/trade, WR 32,3 % |
| Contrôle directionnel | LONG +0,269 R/trade (219 tr) **et** SHORT +0,148 R/trade (187 tr) — **pas** du beta sur le bull market de l'or |
| Voisinage (1 paramètre déplacé) | 6/8 positifs (hasard : 4/8) |
| **Stabilité annuelle** | 2021 **−18,3** / 2022 **+62,2** / 2023 −2,0 / 2024 +15,3 / 2025 +13,9 / 2026 +15,4 |
| TIER 1 | **0/128** — les drawdowns d'entraînement dépassent 12 R |

**Ce qui le disqualifie comme edge établi : 72 % du résultat total vient de la
seule année 2022.** Hors 2022, il reste +24,4 R sur 323 trades (+0,076 R/trade),
avec 2021 négative et 2023 plate. C'est précisément le motif « 93 % du résultat
vient d'un instrument » que la méthodologie du projet interdit de prendre pour
un système — ici transposé au temps plutôt qu'à l'instrument.

À quoi s'ajoute que XAUUSD est l'instrument où le péage est le plus faible
(2,4 % du risque contre 6,6-12,7 % en FX). L'or est donc l'endroit où un signal
à somme nulle a le plus de chances de paraître positif.

**Statut de ce résidu : `NON CONCLUSIF`.** Ni écarté, ni retenu. Il mériterait
un test dédié sur d'autres régimes ou d'autres instruments à faible spread —
pas une promotion.

---

## 4. VERDICT

# PAS D'EDGE

Sur 6 des 7 instruments, plus le portefeuille dans son ensemble.

Justification, dans l'ordre de force décroissante :

1. **19 réussites STRICT contre ~45 attendues par pur hasard** sur 896 cellules.
   Deux fois moins bien que le hasard.
2. **Espérance négative sur les 8 familles de paramètres** en plein échantillon
   (−0,06 à −0,13 R/trade), 10 cellules positives sur 56.
3. **À spread nul, le signal est à −0,008 R/trade** avec 27/56 cellules
   positives — indiscernable d'une pièce. Il n'y a pas d'edge brut que les
   coûts auraient masqué.
4. **Les effectifs sont suffisants** (66-83 trades hors échantillon par
   instrument) : c'est un négatif mesuré, pas un « on ne sait pas ».
5. **L'échec n'est pas imputable à une infidélité de reproduction** : la famille
   qui reproduit correctement les détentions de 5-7 jours perd elle aussi.

Sous-verdict séparé : **XAUUSD = `NON CONCLUSIF`** (§3.3), résidu concentré à
72 % sur une seule année, TIER 1 = 0/128.

**Recommandation : ne pas promouvoir en PAPER.** Le statut du manifest est
`BACKTESTED` au sens de « mesuré », pas de « validé ».

---

## 5. Ce qui est transférable vers la stratégie Adrian

Même avec un verdict négatif, quatre choses sont acquises.

1. **L'ablation du spread doit devenir un diagnostic standard.** Comparer
   `R/trade` à spread réel et à spread nul sépare en une mesure « le signal n'a
   pas d'edge » de « le signal a un edge que les coûts mangent ». Les deux
   appellent des décisions opposées (abandonner vs changer de TF/instrument), et
   sans cette mesure on ne peut pas trancher. Coût : 3 lignes de code
   (`dataclasses.replace(spec, spread_pips=0.0)`).
2. **Le test de fidélité fixé à l'avance sauve du verdict paresseux.** Avoir
   écrit en Phase 1 « si la détention médiane n'est pas de 5-7 jours,
   l'implémentation n'est pas fidèle » a forcé une correction réelle (cible
   structurelle au lieu de multiple du risque). Sans ce garde-fou, la première
   version aurait été déclarée « testée » alors qu'elle ne testait pas la méthode.
3. **Le contrôle directionnel long/short est indispensable sur 2021-2026.**
   La meilleure cellule USDJPY tire **+69,7 R du côté long et −10,0 R du côté
   short** : c'est un pari sur la hausse du dollar-yen déguisé en système. Sans
   ce découpage, 8 STRICT sur USDJPY auraient pu passer pour un edge.
4. **La distance de risque réelle, pas l'ATR théorique.** Le tableau de péage
   calculé sur l'hypothèse « risque = 2×ATR » sous-estimait le drag de USDCAD
   (12,7 % réel contre 11,5 % supposé) et surestimait celui d'autres. Il faut
   mesurer le drag sur les trades réellement produits.

Négatif également utile : **la structure de marché fractale HH/HL–LL/LH, seule,
n'a pas de valeur prédictive mesurable sur ces 7 instruments.** Inutile de la
réessayer telle quelle dans `s90_adrian_synthesis`. Si elle doit servir, ce sera
comme filtre par-dessus un signal ayant déjà un edge propre — jamais comme
signal.

---

## 6. Limites de ce test

1. **Le jugement discrétionnaire n'est pas testé, et ne peut pas l'être.**
   C'est la limite fondamentale, annoncée en Phase 1 (ANALYSIS §6.1). fxalexg
   lit un graphique avec du contexte ; nous testons « les deux derniers swings
   fractals vont dans le même sens ». Si son edge vit dans le jugement, ce test
   le manque intégralement. Le verdict porte sur **la règle**, pas sur **le
   trader**. Cette distinction n'est pas une politesse : elle est logiquement
   nécessaire.
2. **Une seule formalisation testée.** D'autres définitions de la structure
   (break of structure sur clôture, order blocks, zones de liquidité) donneraient
   d'autres résultats. La grille couvre 128 variantes autour d'**une** définition,
   pas l'espace des définitions.
3. **7 instruments, un régime.** 2021-2026 : hausse du dollar, choc inflation
   2022, bull market de l'or. Ce n'est pas un échantillon de régimes.
4. **Pas de portefeuille.** Testé instrument par instrument, une position à la
   fois. La méthode est décrite sur un panier suivi simultanément ; la
   diversification pourrait changer le profil de risque — mais **pas le signe de
   l'espérance par trade**, qui est ce qui est mesuré ici.
5. **Slippage non modélisé** (limite connue du moteur). Il ne peut
   qu'**aggraver** le résultat, jamais l'améliorer.
6. **GBPUSD absent** du catalogue `core/data/instruments.py`, donc non testé.
   Ajouter un instrument aurait exigé de modifier `core/`, ce qui est interdit.
7. **R5 (conformance backtest/live) non exécutable** : `core/validation/
   conformance.py` n'existe pas dans le dépôt. Mitigation : `on_bar()` appelle
   littéralement `precompute()` + `generate_signals()` et ne garde que la
   décision de la barre courante. Il n'existe pas deux implémentations pouvant
   diverger. Ce n'est pas une preuve, c'est une garantie structurelle.
8. **`max_hold_bars` non exposé** par `run_walk_forward`. Les positions vivent
   jusqu'au SL/TP — conforme au « set & forget » de la source, mais aucune
   variante avec sortie temporelle n'a été testée.

---

## 7. Fichiers produits

| Fichier | Contenu |
|---|---|
| `research/ANALYSIS.md` | Phase 1 — décomposition, reproductibilité, hypothèse |
| `strategy.py` | Implémentation `StrategyModule`, R1-R10 |
| `manifest.yaml` | Manifest, grille 128 configurations |
| `backtests/causality.txt` | Sortie R1 archivée (défaut) |
| `backtests/run_wf.py` | Script de walk-forward et diagnostics |
| `backtests/anchored_wf.txt` | Sortie complète : R1 × 32, plein échantillon, WF × 7, synthèse, robustesse, concentration |
| `backtests/spread_ablation.txt` | Ablation du spread, contrôle directionnel, examen XAUUSD |
| `research/VERDICT.md` | Ce document |

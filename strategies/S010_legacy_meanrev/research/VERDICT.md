# Verdict — Legacy S1 : divergence MACD + S/R (Phase 4)

**Source :** projet TBOT 2026, code historique (`grid_search_v12_multi_variant.py`)
**Données :** MT5 Swissquote, H1, 2021-07-18 → 2026-08-14 (5,1 ans)
**Grille :** 108 configurations × 8 instruments = **864 cellules**
**R1 (causalité) : PASSÉ** — sur **48 points de grille** (couche signal) **et sur
les 11 tableaux d'indicateurs** (couche indicateur, 176 comparaisons, écart
exactement nul). Voir §2.0.
**Sorties brutes :** `backtests/anchored_wf.txt`, `backtests/residue_nikkei.txt`,
`backtests/causality.txt`, `backtests/causality_indicators.txt`

---

## 1. Ce que la source affirme

La « source » est notre propre code. Ses affirmations sont des artefacts
versionnés, pas des claims marketing — et c'est ce qui rend la confrontation
possible.

Ce qui a été publié dans `SPEC.md` §7.1 (« PORTFOLIO ROBUSTE (S1
mean-reversion) »), sur la base de `results/anchored_wf_results.txt`
(2026-04-10) :

| Instrument | Configuration | Moy OOS annoncée | Passes STRICT |
|---|---|---|---|
| SP500 | HI_cons+NO_SR SL2.0/2.0 TP4.0/2.0 | **+244 CHF/fenêtre** | 7 / 210 |
| NIKKEI | HI_aggr+NO_SR SL2.5/2.0 TP4.0/4.0 | **+162** | 2 / 210 |
| FTSE | HI_aggr+NO_SR SL2.0/2.5 TP4.0/4.0 | **+108** | 7 / 210 |
| AUDCHF | STRICT SL2.5 TP4.0 | **+98** | 3 / 210 |
| **TOTAL** | 4 paires « robustes » | **+612 CHF/fenêtre** | 19 / 3 570 |

Avec la conclusion écrite : *« 4/17 paires ont des configs passant les
4 fenêtres. Considérer de ne déployer QUE ces paires. »*

Ces chiffres proviennent d'un moteur qui clôturait les positions résiduelles à
`closes[-1]` au lieu de `closes[n-1]`. **Ils ne sont pas citables comme
performance.** Ils servent ici uniquement de terme de comparaison.

---

## 2. Ce que nous mesurons

### 2.0 R1 — et un angle mort qu'il a fallu fermer à la main

Le gardien `core/validation/causality.py` a été renforcé le 16.08.2026 (commit
`7ba94e9`) : il compare désormais **aussi les indicateurs** renvoyés par
`precompute()`, après découverte d'un faux négatif (un filtre `filtfilt`, qui
lit le futur, passait R1 parce que sa fuite ne faisait basculer aucun signal sur
le jeu de test).

**Ce renforcement ne me couvre pas.** Mon `precompute()` ne renvoie que la liste
de signaux ; le nouveau contrôle n'a donc rien à inspecter chez moi et **passe en
silence**. C'est exactement le « rassurer à tort » que le commit dénonce.

J'ai donc refait le test moi-même, tableau par tableau
(`backtests/causality_indicators.txt`) : 11 tableaux d'indicateurs (MACD, RSI,
ADX, +DI, −DI, ATR, distances S/R, divergences haussière/baissière, inflexions)
× 4 coupures × 4 instruments = **176 comparaisons**, écart relatif maximal
**0,00e+00** — bit à bit identique. Aucun point divergent.

C'est cohérent avec la construction : aucune moyenne centrée, aucun z-score
plein échantillon, aucun filtre bidirectionnel, et les fractals sont décalés de
`+k` barres — ce qui est précisément leur délai de confirmation.

### 2.1 Walk-forward ancré — le critère principal

108 configurations par instrument. Un edge **strictement nul** produirait
~5,4 réussites STRICT par instrument (convention 5 % du projet).

| instrument | STRICT | attendu par hasard | TIER 1 | trades OOS (médiane) | moy OOS sur la grille |
|---|---|---|---|---|---|
| SP500 | **0** | 5,4 | 7 | 34 | +0,22 R |
| NIKKEI | **9** | 5,4 | 41 | 30 | +1,27 R |
| FTSE | **0** | 5,4 | 22 | 20 | −0,77 R |
| AUDCHF | **4** | 5,4 | 48 | 40 | −0,02 R |
| EURUSD | **0** | 5,4 | 16 | 51 | −1,45 R |
| EURCHF | **4** | 5,4 | 28 | 34 | −1,38 R |
| AUDUSD | **2** | 5,4 | 22 | 51 | +0,47 R |
| USDJPY | **0** | 5,4 | 1 | 48 | −1,13 R |
| **TOTAL** | **19** | **43,2** | 185 | | |

**19 réussites STRICT là où le pur hasard en produirait ~43.** Comme pour s01,
la grille ne fait pas seulement « pas mieux » que le hasard : elle fait **moins
de la moitié**. Un seul instrument dépasse le seuil du hasard — NIKKEI (§3.3).

Les effectifs hors échantillon (20 à 51 trades cumulés sur les 4 fenêtres) sont
au seuil de crédibilité, pas confortablement au-dessus. C'est plus mince que
s01 (66-83) et cela limite ce qu'on peut affirmer **par instrument** ; le
constat porte sur le portefeuille.

### 2.2 Plein échantillon — 24 cellules diagnostiques

Espérance par trade, spread réel inclus (le moteur le facture à l'entrée **et**
à la sortie) :

| variante | R/trade moyen | instruments positifs |
|---|---|---|
| DIV_SR (= STRICT / WIDE_TOL / RSI40) | **+0,0291** | 4/8 |
| DIV_NOSR (= NO_SR) | **+0,0357** | 4/8 |
| HIST_INF (= HI_cons / HI_aggr) | **−0,0700** | 2/8 |

Moyenne des 24 cellules : **−0,0017 R/trade**, 10/24 positives.

Ce n'est pas le tableau franchement négatif de s01 (−0,10 R/trade, 10/56). C'est
**exactement zéro**. La distinction est importante et §2.3 l'explique.

### 2.3 Ablation du spread — le diagnostic décisif

Mêmes signaux, même moteur, `spread_pips` passé de sa valeur catalogue à zéro :

| | R/trade moyen (24 cellules) | cellules positives |
|---|---|---|
| spread réel Swissquote | **−0,0017** | 10/24 |
| spread nul | **+0,0748** | 14/24 |
| **coût du spread** | **−0,0766 R/trade** | |

**C'est un résultat différent de s01, et il faut le dire clairement.**

Dans s01, à spread nul le signal restait à −0,008 R/trade : il n'y avait
littéralement rien sous le péage. Ici, **il y a quelque chose : +0,075 R/trade
brut, et le spread en consomme +0,0766.** L'annulation est presque parfaite.

Les deux lectures possibles, et pourquoi je ne tranche pas en faveur de la
seconde :

* **« Il y a un edge brut que les coûts mangent »** — techniquement soutenu par
  le chiffre. Mais +0,075 R/trade sur ~800 trades poolés correspond à environ
  2 σ (écart-type du R/trade ≈ 1 R), **sans aucune correction pour les
  864 cellules explorées ni pour le fait que les 8 instruments ont été choisis
  en partie d'après la liste des survivants contaminés**. Après correction, ce
  n'est pas distinguable de zéro.
* **« Le signal est à somme nulle »** — c'est la lecture que je retiens, parce
  que c'est celle que le **hors-échantillon** confirme : 19 STRICT contre 43
  attendues. Un edge brut réel de +0,075 R/trade se verrait dans le
  walk-forward ; il ne s'y voit pas.

Le péage, instrument par instrument, mesuré sur la **distance de risque
réellement observée** (pas sur une hypothèse d'ATR) :

| instrument | risque médian | drag du spread | espérance brute → nette |
|---|---|---|---|
| EURCHF | 22,6 pips | **15,5 %** | +0,45 → +0,26 |
| AUDCHF | 22,0 pips | **10,0 %** | +0,34 → +0,21 |
| AUDUSD | 24,2 pips | 8,3 % | +0,00 → −0,08 |
| EURUSD | 27,9 pips | 6,8 % | +0,09 → +0,02 |
| USDJPY | 41,8 pips | 6,7 % | −0,08 → −0,14 |
| NIKKEI | 210 pts | 4,8 % | +0,24 → +0,18 |
| SP500 | 217 pts | 2,3 % | −0,05 → −0,08 |
| FTSE | 394 pts | 2,0 % | −0,11 → −0,13 |

À noter : **les deux instruments au drag le plus faible (SP500 2,3 %, FTSE
2,0 %) sont négatifs même à spread nul.** Le spread n'est donc pas ce qui les
tue. Inversement les deux au drag le plus élevé (EURCHF, AUDCHF) restent
positifs après péage. Il n'y a pas de relation entre le coût et le résultat —
ce qui est un argument de plus contre la lecture « edge mangé par les coûts ».

### 2.3 bis Le slippage referme la porte

Le moteur commun expose depuis le 16.08.2026 `InstrumentSpec.slippage_pips`
(défaut 0,0, rétrocompatible). **Tous les chiffres ci-dessus sont donc à
slippage nul, c'est-à-dire dans le scénario le plus favorable.** Ordres de
grandeur documentés dans le moteur : 0,2-0,5 pip en FX liquide hors news,
davantage sur indices CFD.

| slippage | R/trade moyen (24 cellules) | cellules positives |
|---|---|---|
| 0,0 pip | −0,0017 | 10/24 |
| **0,5 pip** (réaliste) | **−0,0271** | 9/24 |
| 1,0 pip | −0,0515 | 9/24 |

**Conséquence directe sur l'argument « edge brut mangé par les coûts » :** l'edge
brut vaut +0,0748 R/trade ; le spread en consomme 0,0766 et un glissement
réaliste de 0,5 pip en consomme 0,0254 de plus. **Il n'y a aucune marge — même
un broker à spread nul ne rendrait pas la stratégie rentable une fois le
glissement payé.** C'est ce qui fait basculer §2.3 d'« ambigu » à tranché.

### 2.4 Contrôle long/short — obligatoire sur 2021-2026

Une stratégie de **retour à la moyenne** n'a aucune raison d'avoir un côté
préféré. Sur 24 cellules :

| diagnostic | cellules |
|---|---|
| symétrique (les deux côtés positifs) | **8 / 24** |
| **un seul côté positif** | **9 / 24** |
| négatif des deux côtés | 7 / 24 |

Les cas les plus parlants :

| instrument | variante | LONG | SHORT | lecture |
|---|---|---|---|---|
| USDJPY | DIV_NOSR | +10,3 R (**+0,251**) | −24,3 R (**−0,261**) | achat des creux du plus fort uptrend de la période |
| EURUSD | DIV_NOSR | −3,3 R (−0,051) | +13,1 R (**+0,268**) | pari sur la faiblesse de l'euro |
| AUDUSD | DIV_SR | −11,3 R (−0,195) | +0,1 R (+0,002) | idem, côté AUD |
| SP500 | DIV_NOSR | −8,7 R (−0,213) | +1,2 R (+0,019) | — |

**C'est exactement le piège que s01 avait identifié sur USDJPY** (+69,7 R long,
−10,0 R short). Ici il est retrouvé sur USDJPY *dans l'autre sens*, plus sur
EURUSD et AUDUSD. Sans ce découpage, l'espérance globale à peu près nulle de
§2.2 se lirait comme « le système est neutre » ; en réalité elle masque une
compensation entre paris directionnels opposés.

**Le seul instrument symétrique sur les trois variantes est NIKKEI** — et c'est
aussi le seul au-dessus du seuil du hasard. Ce n'est pas une coïncidence : c'est
ce qui en fait le seul résidu sérieux.

### 2.5 Test de fidélité — fixé en Phase 1, avant tout résultat

Critère annoncé (ANALYSIS §5) : *S1 est une stratégie H1 avec SL/TP à 1,5-4 ATR ;
la détention médiane des gagnants doit tomber entre quelques heures et quelques
jours, sinon l'implémentation ne teste pas S1.*

| variante | détention médiane des gagnants | p90 | n |
|---|---|---|---|
| DIV_SR | **21 h** (0,9 j) | 57 h (2,4 j) | 303 |
| DIV_NOSR | **22 h** (0,9 j) | 57 h (2,4 j) | 320 |
| HIST_INF | **23 h** (1,0 j) | 56 h (2,3 j) | 272 |

**Conforme.** Le régime reproduit est bien celui d'une stratégie H1 à
détention d'environ un jour. Le verdict porte donc sur l'**edge**, pas sur une
infidélité de reproduction — cette porte de sortie est fermée.

### 2.6 Robustesse et concentration

Voisinage de la meilleure cellule (un seul paramètre déplacé) : 3/8 à 7/8 de
voisins positifs selon l'instrument, moyenne ≈ 5,4/8. Le hasard donnerait 4/8.
**Rien de discriminant** : la meilleure cellule n'est ni isolée ni entourée.

Concentration : la meilleure moyenne OOS de NIKKEI (+13,3 R) et d'AUDUSD
(+10,4 R) représentent à elles deux **53 %** du total positif du panier. C'est
moins concentré que le « 93 % sur SP500 » du run v5, mais ce n'est pas non plus
un résultat largement réparti.

### 2.7 Le filtre S/R — la signature de la stratégie — n'apporte rien

`DIV_SR` et `DIV_NOSR` ne diffèrent **que** par la confirmation de lieu :
proximité d'un niveau support/résistance contre simple dominance −DI/+DI.
Jugement sur le **R/trade**, jamais sur le PnL total.

| | R/trade moyen (8 instruments) | meilleur sur |
|---|---|---|
| avec S/R (`DIV_SR`) | +0,0291 | 3/8 |
| sans S/R (`DIV_NOSR`) | **+0,0357** | 5/8 |

Le filtre qui donne son nom à la stratégie fait **légèrement moins bien** qu'un
test trivial de dominance directionnelle, à effectif quasi identique (98 vs 104,
103 vs 106…). Sur EURCHF les deux variantes produisent **85 trades et
+0,2565 / +0,2564 R/trade** : les deux filtres sélectionnent littéralement les
mêmes barres — le filtre de lieu n'est pas contraignant.

Le calcul de S/R était le poste le plus coûteux du code historique (~50 s par
instrument, une boucle Python par barre). **Il ne paie pas son coût.**

---

## 3. L'écart, et son explication

### 3.1 La comparaison directe au run contaminé

Protocole identique (walk-forward ancré, 4 fenêtres, critère STRICT), normalisé
par la taille de grille :

| instrument | contaminé (/210) | taux | propre (/108) | taux | attendu du hasard |
|---|---|---|---|---|---|
| SP500 | 7 | 3,3 % | **0** | **0,0 %** | 5,0 % |
| FTSE | 7 | 3,3 % | **0** | **0,0 %** | 5,0 % |
| AUDCHF | 3 | 1,4 % | 4 | 3,7 % | 5,0 % |
| NIKKEI | 2 | 1,0 % | **9** | **8,3 %** | 5,0 % |
| USDJPY | 0 | 0,0 % | 0 | 0,0 % | 5,0 % |

**Les deux instruments qui portaient le portefeuille — SP500 (+244 CHF/fenêtre)
et FTSE (+108) — tombent à zéro.** Et l'ordre s'inverse : NIKKEI, quatrième et
marginal dans le run contaminé (2/210), devient le seul survivant (9/108).

Le run contaminé et le run propre ne désignent donc **pas les mêmes
instruments**. C'est la signature d'une sélection pilotée par le bruit, pas par
un edge : un edge réel serait resté attaché aux mêmes marchés.

### 3.2 De combien la fuite gonflait-elle les résultats ? La bonne réponse est déroutante

**Le run contaminé a produit 19 réussites STRICT sur 17 × 210 = 3 570 cellules.
Un edge strictement nul en aurait produit ~178. Il faisait donc DIX FOIS MOINS
BIEN QUE LE HASARD** — et il a quand même été publié comme « PORTFOLIO
ROBUSTE », chiffré à +612 CHF/an et inscrit dans `SPEC.md`.

Le run propre produit 19 réussites sur 864 cellules contre ~43 attendues : deux
fois moins bien que le hasard.

Autrement dit : **la correction du lookahead n'a pas transformé un résultat
positif en résultat négatif. Le résultat était déjà négatif avant la
correction.** Personne n'avait calculé le taux de faux positifs. La fuite a
déplacé *quels* instruments semblaient marcher, sans jamais changer le fait que
l'ensemble était sous le seuil du hasard.

C'est un constat plus dérangeant que « la fuite gonflait de X % » : **le chiffre
publié n'était pas seulement gonflé, il n'était pas lu.** Le garde-fou qui
manquait n'était pas seulement `core/validation/causality.py`, c'était la
ligne « ≈N attendues par pur hasard » que `anchored_wf.render()` imprime
désormais à chaque sortie.

Cette lecture est cohérente avec l'amplitude théorique de la fuite annoncée en
Phase 1 : bornée à un trade résiduel par évaluation, elle ne pouvait pas
fabriquer +395 CHF à elle seule. Elle contaminait la **sélection**, pas la
magnitude.

**Réserve honnête.** Trois écarts de protocole interdisent d'attribuer *tout*
l'écart à la fuite : (a) les cellules gagnantes de SP500 et FTSE étaient des
**combinaisons multi-variantes** que le contrat de la plateforme ne permet pas
d'exprimer (ANALYSIS §4.4) — leur 0/108 n'est donc pas strictement le même test ;
(b) ma détection de divergence est une fractale confirmée, pas la fenêtre
tronquée historique (§4.1) ; (c) le moteur commun est plus pessimiste (stop
prioritaire, pas de marge de bruit). **La conclusion « sous le seuil du hasard »
ne dépend d'aucun de ces trois points** : elle se calcule sur les propres
chiffres du run contaminé.

### 3.3 Le seul résidu non écarté — NIKKEI

Honnêteté oblige : **une poche résiste**, et elle résiste mieux que XAUUSD dans
s01. 9 STRICT contre 5,4 attendues, TIER 1 41/108 (le plus haut du panier).

Les 9 passes ne sont pas éparpillées : **8 d'entre elles forment un amas
contigu** — `DIV_NOSR`/`DIV_SR`, rsi 35-40, `sl_atr` 2,5, adx 25-35. Quatre
représentants, plein échantillon :

| configuration | n | R | R/trade | WR | DD max | meilleure année | hors cette année | LONG | SHORT | à spread nul |
|---|---|---|---|---|---|---|---|---|---|---|
| DIV_NOSR rsi40 adx35 sl2.5 | 182 | +28,5 | +0,157 | 40,1 % | 13,7 R | 2023 = 54 % | **+0,093** | +0,251 | +0,072 | +0,197 |
| DIV_NOSR rsi40 adx25 sl2.5 | 95 | +31,9 | +0,336 | 46,3 % | 7,2 R | 2023 = 37 % | **+0,268** | +0,519 | +0,132 | +0,377 |
| DIV_NOSR rsi35 adx35 sl2.5 | 112 | +25,9 | +0,231 | 42,9 % | 6,3 R | 2026 = 44 % | **+0,152** | +0,291 | +0,176 | +0,275 |
| DIV_SR rsi35 adx35 sl2.5 | 101 | +25,1 | +0,248 | 43,6 % | 6,1 R | 2022 = 55 % | **+0,137** | +0,366 | +0,129 | +0,295 |

Cet amas **passe les tests qui ont disqualifié XAUUSD dans s01** :

* aucune année ne porte plus de **55 %** du total (seuil fixé à 60 % avant
  l'examen ; XAUUSD était à 72 %) ;
* le résidu hors meilleure année reste **positif** (+0,09 à +0,27 R/trade) ;
* les **deux sens** sont profitables ;
* l'edge est **brut** : à spread nul, +0,20 à +0,38 R/trade.

**Ce qui l'empêche malgré tout d'être un edge établi :**

1. Les 4 cellules **partagent la majorité de leurs trades** : c'est **une**
   observation, pas quatre confirmations indépendantes.
2. n = 95 à 182 trades sur 5,1 ans. Avec un écart-type du R/trade ≈ 1 R,
   l'erreur standard vaut 0,07 à 0,10 R — soit 2 à 3 σ **sans correction pour
   multiplicité**.
3. Et la multiplicité est précisément le problème : NIKKEI est **le meilleur de
   864 cellules**. La question n'est pas « +0,25 est-il significatif pour une
   série ? » mais « le meilleur de 864 l'est-il ? ». À ce niveau, non.
4. Le côté LONG rend **2 à 4×** le côté SHORT sur un marché qui a environ doublé
   sur la période. Les deux sens sont positifs — ce n'est donc pas du pur beta —
   mais le biais directionnel est réel et non expliqué.
5. NIKKEI figurait dans la liste des survivants du run **contaminé** : il n'a pas
   été choisi à l'aveugle.

**Statut : `NON CONCLUSIF`.** Ni écarté, ni retenu.

### 3.4 Une réserve statistique qui joue dans les deux sens

Le repère « 5 % de la grille par pur hasard » suppose des configurations
**indépendantes**. Elles ne le sont pas : deux cellules voisines partagent la
quasi-totalité de leurs trades. Le nombre de réussites est donc **sur-dispersé**
— il arrive par paquets (0, 0, 9, 4…) plutôt que dispersé autour de 5,4.

Conséquence honnête, dans les deux sens :

* un instrument à 9/108 n'est **pas** « 1,7× le hasard » de façon significative
  — ce qui affaiblit NIKKEI ;
* mais un **total** de 19 contre 43 sur 8 instruments reste informatif, parce que
  la sur-dispersion joue surtout *dans* un instrument, pas *entre* eux.

On ne conclut donc pas sur un instrument isolé ; on conclut sur le portefeuille,
et NIKKEI est traité à part.

---

## 4. VERDICT

# PAS D'EDGE

Sur 7 des 8 instruments, et sur le portefeuille dans son ensemble.

Justification, par ordre de force décroissante :

1. **19 réussites STRICT contre ~43 attendues par pur hasard** sur 864 cellules
   hors échantillon. Moins de la moitié du hasard.
2. **Espérance plein échantillon de −0,0017 R/trade** — exactement le seuil de
   rentabilité — avec seulement 10/24 cellules positives. Aucune des trois
   familles de variantes n'atteint +0,04 R/trade.
3. **9 cellules sur 24 ne gagnent que d'un seul côté**, et les cas les plus
   rentables (USDJPY short-négatif/long-positif, EURUSD short-positif) sont des
   **paris directionnels** sur le régime 2021-2026, pas des retours à la moyenne.
4. **Le filtre S/R, qui donne son nom à la stratégie, n'apporte rien de
   mesurable** : le remplacer par un test trivial de dominance −DI/+DI fait
   marginalement mieux (§2.7). Le cœur de l'hypothèse — la confluence
   divergence × niveau — n'est pas confirmé.
5. **SP500 et FTSE, les deux vedettes du portefeuille publié, font 0/108.**
6. **L'échec n'est pas imputable à une infidélité de reproduction** : le test de
   fidélité fixé en Phase 1 est passé (détention médiane ≈ 1 jour, §2.5).
7. À spread nul l'espérance monte à +0,075 R/trade — un edge brut *possible*
   mais non confirmé hors échantillon, et non distinguable de zéro après
   correction pour les 864 cellules explorées (§2.3). **Et il ne survit pas au
   slippage : à 0,5 pip, l'espérance tombe à −0,0271 R/trade** (§2.3 bis). Même
   un broker à spread nul ne suffirait pas.

Sous-verdict séparé : **NIKKEI = `NON CONCLUSIF`** (§3.3). Amas cohérent de
8 cellules, réparti sur les années, symétrique long/short, edge brut réel — mais
c'est le meilleur de 864 cellules sur ~100 trades, et l'instrument n'a pas été
choisi à l'aveugle.

**Recommandation : ne pas promouvoir en PAPER.** Le statut du manifest passe à
`BACKTESTED` au sens de « mesuré », pas de « validé ».

**Corollaire sur `SPEC.md` §7.1 :** le « PORTFOLIO ROBUSTE S1 » (SP500, NIKKEI,
FTSE, AUDCHF, +612 CHF/an) n'est pas reproductible et n'était, sur ses propres
chiffres, pas au-dessus du hasard. Il devrait être retiré ou explicitement
marqué comme invalidé — décision d'Adrian, hors de mon périmètre.

---

## 5. Ce qui est transférable vers la stratégie Adrian

Même avec un verdict négatif, sept choses sont acquises.

1. **Le taux de faux positifs doit être imprimé à côté de chaque résultat, pas
   calculé après coup.** C'est la leçon centrale de ce travail : le run
   contaminé était *déjà* dix fois sous le hasard, et personne ne l'a vu parce
   que le chiffre n'était pas affiché. Le lookahead a fait perdre des mois ;
   l'absence de baseline aurait fait perdre les mêmes mois **même sans le bug**.
   `anchored_wf.render()` l'imprime désormais — ne jamais lire une sortie sans
   cette ligne.
2. **L'ablation du spread sépare deux diagnostics opposés, et le résultat n'est
   pas toujours celui de s01.** Ici l'espérance brute est *positive* (+0,075) et
   le péage l'annule presque exactement. Sans cette mesure on conclurait « signal
   nul » tout court ; avec elle, on sait *où* le signal meurt. À noter cependant :
   les deux instruments au drag le plus faible sont négatifs même à spread nul —
   le coût n'explique pas tout.
3. **L'ablation doit être faite en trois points, pas deux : spread réel, spread
   nul, et spread réel + slippage réaliste.** C'est le troisième point qui a
   tranché ici : à spread nul le verdict restait discutable, à 0,5 pip de
   glissement il ne l'est plus. Coût : un `dataclasses.replace(spec,
   slippage_pips=0.5)` de plus.
4. **Un garde-fou qui n'a rien à inspecter passe en silence.** Le renforcement
   de R1 à la couche indicateur ne couvrait pas ma stratégie, parce que mon
   `precompute()` ne renvoie que des signaux. Un « R1 PASSÉ » ne dit pas ce qui
   a été testé. Soit `precompute()` expose ses indicateurs pour que le gardien
   les voie, soit la stratégie fait le test elle-même — mais on ne se contente
   pas du verdict vert.
5. **Le contrôle long/short est confirmé comme indispensable sur 2021-2026.**
   9 cellules sur 24 ne gagnent que d'un côté. s01 l'avait découvert sur USDJPY ;
   il se reproduit ici sur USDJPY, EURUSD et AUDUSD. Toute stratégie testée sur
   cette période doit passer ce découpage avant tout verdict.
6. **Négatif utile n°1 : la confluence « divergence MACD × support/résistance »
   n'a pas de valeur prédictive mesurable** sur ces 8 instruments en H1. Le
   composant S/R — le plus coûteux en calcul de tout le code historique — est
   remplaçable par un test trivial sans perte. Inutile de le réessayer tel quel
   dans `s90_adrian_synthesis`.
7. **Négatif utile n°2 : compter des « variantes » qui partagent le même chemin
   de code gonfle le taux de faux positifs sans tester d'hypothèse
   supplémentaire.** L'historique exposait 6 variantes pour 3 branches de code
   réelles, soit 210 configurations là où ~100 suffisaient. Chaque doublon
   ajoute des occasions de faux positif, pas de la connaissance.

Point ouvert et honnête pour la suite : l'espérance brute positive (§2.3) et
l'amas NIKKEI (§3.3) ne sont pas des edges établis, mais ils ne sont pas non
plus réfutés. Si une piste devait être reprise de S1, ce serait **le
déclencheur de divergence seul, sur un instrument à faible drag et un timeframe
plus élevé** — pas le système complet, et pas sur H1.

---

## 6. Limites de ce test

1. **Le TP dynamique par paliers n'est pas testé** (ANALYSIS §4.3) : inexprimable
   dans le contrat `Signal`, qui ne décrit qu'une décision d'entrée. Il était
   actif sur 2 des 15 configurations historiques.
2. **Les combinaisons multi-variantes ne sont pas testées comme telles**
   (§4.4). C'est la limite la plus gênante pour la comparaison au run contaminé,
   dont les vedettes SP500 et FTSE étaient précisément des combinaisons.
   L'espérance par trade étant additive, le **signe** de la conclusion n'en
   dépend pas — le profil de risque, si.
3. **Substitution sur la détection de divergence** (§4.1) : fractale confirmée
   au lieu de la fenêtre tronquée historique. Le signal se déclenche 0-2 barres
   plus tard et un peu moins souvent.
4. **Effectifs hors échantillon minces** : 20 à 51 trades cumulés par
   instrument, contre 66-83 dans s01. Cela limite ce qu'on peut affirmer par
   instrument ; le verdict porte sur le portefeuille.
5. **Un seul régime.** 2021-2026 : dollar fort, choc inflation 2022, bull market
   des indices, doublement du Nikkei. Ce n'est pas un échantillon de régimes.
6. **8 instruments, choisis en partie d'après la liste des survivants
   contaminés.** C'est délibéré (rendre la comparaison possible) mais ce n'est
   pas un échantillon neutre, et cela joue en faveur de la stratégie.
7. **La grille elle-même a été conçue en regardant l'historique complet.** Je
   suis honnête sur *quelle cellule*, pas sur *quelle grille*. C'est la
   limitation n°1 du rapport v5 et elle s'applique intégralement.
8. **Swap et commission non modélisés.** S1 garde des positions ~1 jour en
   médiane, jusqu'à ~2,4 jours au p90 : le swap est réel et non compté. Ces
   omissions ne peuvent qu'**aggraver** le résultat. Le **slippage**, lui, est
   désormais mesuré (§2.3 bis) : il coûte 0,025 R/trade à 0,5 pip.
9. **Le spread est un forfait du catalogue**, pas le spread réel par barre. Le
   code historique utilisait le spread MT5 par barre quand il était disponible.
10. **R5 (conformance backtest/live) non exécutable** : `core/validation/
    conformance.py` n'existe pas dans le dépôt. Mitigation : `on_bar()` appelle
    littéralement `precompute()` + `generate_signals()` et ne garde que la
    décision de la barre courante. Il n'existe pas deux implémentations pouvant
    diverger. Ce n'est pas une preuve, c'est une garantie structurelle.
11. **Pas de portefeuille.** Testé instrument par instrument, une position à la
    fois. La corrélation entre EURCHF et AUDCHF (deux croisées CHF) n'est pas
    prise en compte.

---

## 7. Fichiers produits

| Fichier | Contenu |
|---|---|
| `research/ANALYSIS.md` | Phase 1 — décomposition, reproductibilité, substitutions, hypothèse |
| `strategy.py` | Implémentation `StrategyModule`, R1-R10, 3 variantes |
| `manifest.yaml` | Manifest, grille 108 configurations, statut BACKTESTED |
| `backtests/causality.txt` | Sortie R1 archivée (couche signal, config par défaut) |
| `backtests/causality_indicators.txt` | R1 à la **couche indicateur** — 176 comparaisons, écart nul |
| `backtests/run_wf.py` | Script de walk-forward et diagnostics |
| `backtests/anchored_wf.txt` | Sortie complète : R1 × 48, plein échantillon, WF × 8, synthèse, robustesse, concentration, **ablation du spread**, **contrôle long/short** |
| `backtests/residue_nikkei.py` / `.txt` | Examen du résidu NIKKEI, comparaison au run contaminé, test du filtre S/R |
| `research/VERDICT.md` | Ce document |

# VERDICT — S020, MACD cross + filtre zéro, SL/TP en % (René Balke)

**Données** : MT5 Swissquote, 2021-08 → 2026-09-10. Indices en **D1** (NASDAQ 1 330,
SP500 1 330, DAX 1 293 barres) ; or et FX en **H1** (≈ 30 000 barres chacun).
**Exécution** : moteur commun, spread catalogue puis spread mesuré, slippage 0, une
position, refroidissement 2, coupe-circuit 3 pertes → 24 barres.
**Dépôt** : `afe2e2a`. **R1** passé sur les 7 instruments. **Critères** :
`FALSIFICATION.md`, écrits avant la mesure — et appliqués ci-dessous sans retouche.

---

## Verdict en une ligne

**RÉUSSITE sur EURUSD H1 au sens des critères écrits d'avance ; ÉCHEC partout
ailleurs.** Trois cellules STRICT dépassent le percentile 90 du témoin sur EURUSD, la
plus forte tient sur un second instrument (USDJPY). Aucun autre instrument ne produit
une seule cellule STRICT.

## 1. Le tableau, instrument par instrument

| Instrument | Maille | STRICT / 18 (≈ 0,9 attendue) | Cellule vidéo Z 2 %/2 % | Meilleure cellule | Verdict critères |
|---|---|---:|---|---|---|
| NASDAQ | D1 | 0 | −7,2 R · pct 24 | −sl1/tp4 +6,6 R · pct 64 | échec |
| SP500 | D1 | 0 | −5,4 R · pct 25 | −sl0,5/tp4 +15,4 R · pct 80 | échec |
| DAX | D1 | 0 | −7,0 R · pct 26 | Z sl0,5/tp4 +15,6 R · pct 90 | échec (0 STRICT) |
| XAUUSD | H1 | 0 | −32,3 R · pct 0,5 | −sl1/tp4 +39,8 R · pct 94 | échec (0 STRICT) |
| **EURUSD** | **H1** | **4** | **+13,8 R · pct 99,5** | Z sl0,5/tp4 +19,7 R · pct 87 | **réussite** |
| GBPUSD | H1 | 0 | +10,5 R · pct 96,5 | Z sl1/tp4 +38,4 R · pct 100 | échec (0 STRICT) |
| USDJPY | H1 | 0 | −5,9 R · pct 39 | −sl0,5/tp4 +30,9 R · pct 77 | échec |

Les critères exigent une cellule **STRICT** (profitable en apprentissage ET hors
échantillon sur les 4 fenêtres). GBPUSD et XAUUSD ont des cellules très au-dessus du
témoin en plein échantillon mais aucune ne passe les 4 fenêtres : ce n'est pas rien,
mais ce n'est pas ce que le critère demandait. On ne déplace pas la barre après coup.

## 2. EURUSD H1 — les quatre cellules STRICT passées au crible

| Cellule | n | R | R/trade | pct témoin | années (R) | part de la meilleure année | GBPUSD | USDJPY | XAUUSD |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| Z sl0,5 % tp4 % | 99 | +19,7 | +0,199 | **86,5** ✗ | 21:−8 22:−6 23:+13 24:+1 25:+11 26:+9 | 66 % | −0,6 | +5,3 | +14,8 |
| Z sl0,5 % tp2 % | 202 | +26,8 | +0,133 | 93,0 | 21:−3 22:−9 23:−11 24:+29 25:+19 26:+2 | **107 %** ✗ | −31,7 | +30,0 | +29,9 |
| − sl0,5 % tp2 % | 213 | +30,3 | +0,142 | 95,5 | 21:−6 22:−15 23:+10 24:+25 25:+14 26:+2 | 81 % | −23,7 | +29,4 | +75,4 |
| **Z sl1 % tp2 %** | **129** | **+20,0** | **+0,155** | **98,0** | **21:−2 22:+2 23:+7 24:+4 25:+6 26:+2** | **37 %** | −19,3 | **+17,8** | −18,6 |

Application des critères, cellule par cellule :

- **Z sl0,5 % tp4 %** : percentile 86,5 < 90 → écartée.
- **Z sl0,5 % tp2 %** : portée par la seule année 2024 (107 % du total) → clause
  d'échec « une seule année » → écartée.
- **− sl0,5 % tp2 %** : percentile 95,5, trois années positives, positive sur USDJPY
  et XAUUSD → retenue.
- **Z sl1 % tp2 %** : percentile **98,0** (au-dessus du seuil 97 qui vaut à lui seul),
  **cinq années positives sur six**, part maximale 37 %, positive sur USDJPY → retenue,
  et c'est la plus solide du dossier.

Coût de bord sur EURUSD : 0,8 % du R au spread mesuré (1,8 pips, identique au
catalogue). Le critère « < 35 % » est très largement respecté ; la réussite ne tient
pas à un tarif de faveur.

## 3. Ce que ce verdict ne dit pas — à lire avant de s'emballer

- **Les trois cellules retenues sont voisines** (stop 0,5-1 %, cible 2 %) : ce sont
  trois lectures d'une même poche, pas trois confirmations indépendantes. Le compte
  « ≥ 3 STRICT » du critère 4 est satisfait, mais il surestime l'indépendance.
- **Le transfert est mixte** : les cellules retenues sont positives sur USDJPY (et
  l'or pour l'une), **négatives sur GBPUSD** dans les trois cas. Le critère ne demandait
  qu'un second instrument positif ; il est honnête de dire que le troisième dit non.
- **La vidéo montrait des indices en intraday** ; nous n'avons mesuré les indices qu'en
  D1 (MT5 hors ligne). La conclusion « échec sur indices » est **ouverte**, pas acquise.
- **Effectif** : 129 trades sur cinq ans pour la cellule retenue, 43 hors échantillon.
  L'intervalle sur +0,155 R/trade reste large (écart-type ≈ 1,2 R → ± 0,21 à 95 %).
  Le témoin au percentile 98 est l'argument, pas la moyenne seule.
- **Slippage à 0**, comme partout dans le dépôt : optimiste d'un montant inconnu.

## 4. Ce que la mesure change

1. **La règle de la vidéo, sur EURUSD H1, passe les critères écrits d'avance.** C'est
   le premier déclencheur issu d'une vidéo, dans ce dépôt, qui y parvient.
2. **Étape suivante prévue par `FALSIFICATION.md`** : forward scellé sur EURUSD,
   cellule Z sl1 % tp2 %, critères d'arrêt écrits avant le premier signal — sur le
   modèle de `studies/gold_forward/`. **Décision Adrian** (R10), rien n'est promu ici.
3. **À mesurer avant de conclure sur les indices** : NASDAQ / SP500 / DAX en H1 et
   M15 dès que MT5 est en ligne.
4. **S013 n'est pas contredit** : il mesurait le croisement nu avec sorties ATR sur
   forex D1. Ici la combinaison croisement + filtre zéro + géométrie en %, en H1, fait
   autre chose. Les deux dossiers se complètent.

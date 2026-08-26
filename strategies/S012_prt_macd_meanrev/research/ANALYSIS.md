# Analyse — Daily MACD Mean Reversion (ProRealTime)

Source : https://www.youtube.com/watch?v=1l7xWU-BU3w (« If I Started Algo
Trading in 2026 », 2026-02-22, 78 k vues) + transcript indépendant
`docs/sources/prorealalgos/10_started_2025.txt` (même maison, mêmes règles).
Trader : chaîne ProRealAlgos / blog prorealos.com — vend de la formation et des
algos, distribue celui-ci gratuitement (produit d'appel). Pas de track record
audité ; il ne CLAIME d'ailleurs aucun chiffre (voir §1 du VERDICT).

## 1. La méthode reformulée

Sur SP500 en daily, LONG uniquement :

1. **Entrée** (toutes les conditions au close du jour) :
   - MACD en baisse 5 jours consécutifs ;
   - MACD < 0 ;
   - close < close de la veille (condition confirmée par prorealalgos/10 @19:30,
     absente du transcript initial) ;
   - close « près du bas du trading range » (non chiffré par la source).
2. **Sortie** : dès que le close repasse au-dessus du plus haut de la VEILLE.
3. **Pas de stop.** Pas de cible fixe. Pas de sizing dynamique.
4. Sa « première amélioration » : interdire l'entrée le vendredi (améliore SON
   backtest — filtre calendaire in-sample, à tester sans le croire).

C'est du mean reversion CLASSIQUE (acheter la faiblesse sur indice en D1,
revendre la première force) — la famille que la synthèse aipathways (T1)
déclare la seule largement vivante, et la seule jamais testée chez nous
(s10 = divergence MACD H1 forex : même mot, autre objet).

## 2. Décomposition et reproductibilité

| Composant | Source | Chez nous | Dégradation |
|---|---|---|---|
| MACD 12/26/9, valeur ligne | ProBuilder (peut-être leur S-MACD normalisé prix) | EMA12−EMA26 ; proxy S-MACD = MACD/close testé en addendum | nulle (mesuré : signaux identiques sur SP500) |
| Baisse 5 j + < 0 + close<close[1] | exact | exact | aucune |
| « near the low of the trading range » | non chiffré | position du close dans le range N j ≤ q ; N∈{10,20}, q∈{0.2,0.35} | interprétation — 4 cellules |
| Entrée at market | next open (semantique PRT) | close du jour signal | ~1 overnight |
| Sortie close > high[veille] | seuil DYNAMIQUE (cliquet descendant) | cible statique max(high signal, close veille) — moteur commun R9 | défavorable en baisse prolongée ; durées de détention rapportées |
| Pas de stop | — | R3 impose : 10 ATR = proxy « sans stop », 3 ATR variante | MAE et pires trades rapportés |
| Données | IG CFD US500 D1 | MT5 Swissquote SP500/NASDAQ/DAX D1 2016-2026 + LONGHIST 1927/1971 (close-only, structurel) | LONGHIST : range/cible sur closes, spread nul, jamais comparé aux chiffres MT5 |

Rien d'irréalisable : c'est la stratégie la plus simple du portefeuille de
sources. Tout le risque du dossier est statistique, pas technique.

## 3. L'hypothèse testable

Pour que cette stratégie ait un edge, il faut que **les jours qui suivent
« faiblesse MACD 5 j + close au fond du range » sur un indice soient meilleurs
que les jours ordinaires du même indice** — assez meilleurs pour payer le
péage D1 (mesuré minuscule : 0,10-0,34 % du R) ET battre une entrée longue
aléatoire de même géométrie (le beta long-only est structurel sur indice).
Falsifications chiffrées et gelées AVANT tout run : `FALSIFICATION.md` (F1-F5
+ addendum).

## 4. Le point méthodologique de la source

Sa doctrine « ne juger un algo que depuis sa date de release » (release
déclarée : **2022-06-21**, code figé publiquement) est un hold-out honnête —
conceptuellement identique à notre forward-test scellé. On la lui applique
(F4, split exact). Son angle mort : sélectionner parmi ~30 algos publiés celui
qui « a bien marché depuis sa sortie » est du multiple testing SUR
l'out-of-sample — le survivant parmi 30 n'est pas une preuve (~1,5 attendus au
seuil 5 % par pur hasard).

## 5. Écarts au gel (traçabilité)

- Addendum 2026-08-16 (POST-gel, POST-premiers-runs) : condition close<close[1],
  release 2022-06-21, proxy S-MACD — corrections de FIDÉLITÉ reçues d'une
  source indépendante, traitées hors grille (A1/A2, `backtests/addendum.txt`),
  grille gelée intacte. Effet mesuré : négligeable (SP500 : mêmes conclusions,
  A2 ≡ A1 signal pour signal).
- Piste « RSI 14 < 30 D1 indices » (prorealalgos/04, 2e source convergente avec
  aipathways T1 sur la famille) : NOTÉE pour une stratégie suivante, pas
  ajoutée — la grille était gelée.

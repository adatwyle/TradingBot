# VERDICT — s12_prt_macd_meanrev (Daily MACD Mean Reversion, ProRealTime)

Commit : `773cc4a` (HEAD au moment des runs). R1 PASSÉ (couche indicateur
incluse) et R5 PASSÉ sur SP500/NASDAQ/DAX — sorties archivées dans
`backtests/`. Falsifications gelées AVANT tout backtest :
`research/FALSIFICATION.md` (+ addendum daté).

---

## 1. Ce que la source affirme

Rien de chiffré — c'est notable. Ni win rate, ni PF, ni drawdown : seulement
« this algorithm has performed quite well since it was released » (juin 2022,
date exacte 2022-06-21). Sa doctrine : ne juger un algo que depuis sa release.
Le filtre « pas d'entrée le vendredi » améliorerait son backtest.

## 2. Ce que nous mesurons

**MT5 Swissquote D1, 2016-01 → 2026-08 (2 774 barres), moteur commun, WF ancré
4 fenêtres + témoin aléatoire 200 tirages long-only à géométrie identique
(graine 20260816).** Config par défaut = fidèle source (stop proxy 10 ATR,
vendredi autorisé). Règles exactes (close<close[1], A1) : mêmes conclusions —
`backtests/addendum.txt`.

| Mesure (SP500, config défaut) | Valeur | Effectif |
|---|---|---|
| Plein échantillon, spread réel | **−0,0072 R/trade** (WR 89,5 %) | 38 trades |
| Plein échantillon, **spread nul** | **−0,0062 R/trade** → F2 DÉCLENCHÉE | 38 |
| Walk-forward STRICT | **0/16 cellules** | 19-28 trades OOS/cellule |
| Témoin aléatoire (OOS, défaut) | **percentile 51,5** → F1 DÉCLENCHÉE | 19 OOS |
| Témoin (règles exactes A1) | percentile 51,5 ; A2 (S-MACD proxy) : signaux identiques | 16 OOS |
| Pré-release (2016→2022-06-21) | −0,0475 R/trade | 19 |
| Post-release (2022-06-21→2026) | +0,0330 R/trade ≈ témoin long aléatoire (+0,042) | 19 |
| Vendredi interdit (R/trade) | −0,0126 vs −0,0072 autorisé → PIRE ici | 38 |

**LONGHIST close-only, spread nul (test structurel — jamais comparé aux
chiffres MT5)** :

| Mesure | SP500 1927-2026 | NASDAQ 1971-2026 |
|---|---|---|
| Trades | **464** | 257 |
| Espérance | **−0,39 %/trade** (−0,062 R) | −0,63 %/trade |
| Jours EN position (annualisé) | **+0,8 %/an** (23 % du temps) | **−3,5 %/an** |
| B&H même échantillon | +6,4 %/an | +10,6 %/an |
| Toujours investi SAUF ces jours | **+8,1 %/an** | **+15,1 %/an** |
| Époques négatives | 5/5 (1980-2000 : −0,005 R/trade, la moins pire) | 3/4 (2022+ : +0,02 R, 16 trades) |
| Pire trade (pas de stop) | **−26,3 % en 3 jours** (oct. 1987) | −15,9 % (oct. 1987) |

→ **F3 DÉCLENCHÉE dans les deux datasets** : les jours sélectionnés par le
signal sont PIRES que la moyenne. Retirer ces jours AMÉLIORE le buy & hold.

**Transfert à froid** : NASDAQ +0,058 R/trade plein échantillon (témoin 87e
percentile — sous le seuil). DAX : 4 cellules STRICT corrélées (toutes
sl_atr=10, mêmes trades) au percentile 100 — mais honest_r +2,05 R contre un
p95 nul à +2,02 R (marge 0,03 R), 20 trades, pré-release NÉGATIF
(−0,021 R/trade), et sélection parmi 3 instruments × 16 cellules. Le test
structurel 100 ans sur la même famille dit non : c'est le profil du faux
positif de grille, pas d'un edge.

## 3. L'écart, et son explication

Son « performed quite well since June 2022 » est REPRODUIT (+0,63 R sur 19
trades SP500 post-release) — et il vaut exactement ce que rapporte une entrée
longue AU HASARD de même géométrie sur la même période (médiane nulle
+0,62 R). 2022-2026 est un marché haussier : un long-only quelconque « performe
bien ». Le signal n'ajoute rien : à spread nul, sur 10 ans, l'espérance est
négative ; sur 99 ans, les jours choisis sous-performent les jours ordinaires
de 5 à 18 points annualisés. Le profil WR 85-95 % / pertes rares mais
énormes (−26 % en 3 jours, sans stop) est l'archétype du ramassage de centimes
devant le rouleau compresseur.

Le filtre vendredi — son exemple pédagogique d'« amélioration » — dégrade le
R/trade chez nous sur SP500 : c'était du bruit in-sample, comme prévu au gel.

## 4. Verdict : **PAS D'EDGE**

F1, F2, F3 déclenchées (F3 sur 464 + 257 trades — pas un problème
d'effectif) ; F4 montre que le post-release = beta ; F5 (19 OOS sur la cellule
défaut) est absorbée par l'effectif LONGHIST. La seule poche « verte » (DAX
sl_atr=10, percentile 100 à 0,03 R du p95) est expliquée en §2.

Angle mort de la source, rappelé comme promis : même si ce backtest post-release
avait été bon, un survivant mis en avant parmi ~30 algos publiés reste du
multiple testing sur l'out-of-sample.

## 5. Transférable vers la stratégie Adrian

1. **Le trou de couverture T1 est comblé pour CETTE variante** : le mean
   reversion classique D1 long-only « MACD faible + fond de range, sortie sur
   force » ne sélectionne pas de bons jours — mesuré sur un siècle.
2. **La doctrine « depuis la release » est bonne et importable** : c'est notre
   forward-test scellé. Son piège (survivant parmi N) est exactement ce que
   notre bras témoin + gel des falsifications neutralisent.
3. **Le péage D1 est réellement négligeable** (0,10-0,34 % du R mesuré) : le D1
   reste LE timeframe où chercher — le signal était mauvais, pas le terrain.
4. **Piste chiffrable pour une suite** : l'entrée « RSI 14 < 30, D1, indices »
   (prorealalgos/04 — criblage 500 combinaisons de la même maison) converge
   avec aipathways T1. Famille identique, déclencheur différent — à tester
   comme s1x dédiée avec le même harnais (grille gelée AVANT run).
5. **Jamais de long-only indice sans stop** : MAE p90 ~11 % du prix, pire cas
   −26 % en 3 jours (1987). Un « WR 95 % » peut cacher ça pendant des années.

## 6. Limites de ce test

- **Sortie dynamique approximée par cible statique** (moteur commun R9) : tient
  plus longtemps que la source en baisse prolongée (détention méd 4 j mais p90
  21-35 j, max 115 j). Une version au seuil cliquet sortirait plus tôt, plus
  souvent perdante mais moins profondément — le SIGNE de l'espérance à spread
  nul et la sélection de jours (F3, indépendante de la sortie ~ méd 5 j) n'en
  dépendent vraisemblablement pas, mais ce n'est pas prouvé au trade près.
- Entrée au close du jour signal vs next open PRT : ~1 overnight d'écart.
- LONGHIST est close-only (o=h=l=c) : range, cible et « pire trade » y sont des
  approximations déclarées ; les chiffres LONGHIST ne valident ni n'invalident
  l'exécution — seulement la STRUCTURE du signal.
- La définition exacte « near the low » et le S-MACD ProBuilder ne sont pas
  publiés ; 4 interprétations de range testées + proxy S-MACD (identique signal
  pour signal sur SP500). Un code ProBuilder différent resterait possible, mais
  il devrait battre un témoin que 16 cellules × 3 instruments n'ont pas battu.
- MT5 D1 ne remonte qu'à 2016 (2 774 barres) — d'où LONGHIST pour la longueur.

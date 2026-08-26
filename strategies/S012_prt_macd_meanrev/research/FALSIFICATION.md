# s12 — Conditions de falsification, figées AVANT le premier backtest

> Date de gel : 2026-08-16, commit `773cc4a`. Aucun backtest de la stratégie n'a
> été exécuté au moment où ce fichier est écrit. Seules des mesures de DONNÉES
> existent (profondeur MT5 D1, drag spread, fréquence brute du déclencheur
> MACD, structure LONGHIST). Toute modification de ce fichier après le premier
> backtest serait une falsification au sens inverse du terme.

## Convention statistique

La référence de ce dossier est le **bras témoin empirique**
(`attach_control_arm`, 200 tirages, graine 20260816), exécuté avec les MÊMES
`engine_kwargs` que la stratégie. Le comptage STRICT/n×0,05 est rapporté pour
archive, jamais comme évidence. **Le témoin est LA référence, pas zéro** :
long-only sur indice = beta positif structurel ; le témoin long-only rejoue ce
beta et le soustrait de fait.

## Le claim à confronter

Vidéo ProRealTime « If I Started Algo Trading in 2026 » (20:00-21:30) :
« Daily MACD strategy », SP500 daily, LONG only, distribuée gratuitement,
sortie **juin 2022**. L'auteur ne donne AUCUN chiffre (ni WR, ni PF) — il dit
seulement que le backtest depuis la release « performed quite well ». Sa propre
doctrine : ne juger que les résultats depuis la date de publication. On la lui
applique (F4).

## Économie a priori (data-only, mesurée avant implémentation)

| Instrument | ATR14 D1 médian | spread (catalogue) | drag stop 3 ATR | drag stop 10 ATR |
|---|---|---|---|---|
| SP500 | 49,2 pts | 0,50 pts | 0,34 % du R | 0,10 % du R |
| NASDAQ | 221,1 pts | 0,80 pts | 0,12 % | 0,04 % |
| DAX | 196,2 pts | 0,80 pts | 0,14 % | 0,04 % |

Fréquence brute du pré-déclencheur (MACD ligne en baisse 5 j ET < 0) : 7,4 %
des jours SP500 (204/2774). Avec le filtre « close near low of range », attendre
grossièrement 1-3 trades/mois. Le D1 est bien le timeframe où le péage est
négligeable — si le signal ne survit pas ici, ce n'est pas la faute du spread.

## Falsifications (TOUTES chiffrées, figées)

| # | Condition | Seuil | Si déclenchée |
|---|---|---|---|
| **F1** | **Témoin mesuré** : la config par défaut (range 20 j, q 0,2, vendredi autorisé, stop 10 ATR) sur son `honest_r` OOS SP500 vs 200 entrées aléatoires long-only à dispositif identique | percentile **< 95** | PAS D'EDGE — le timing d'entrée n'apporte rien au-delà du beta long |
| **F2** | **Espérance à spread nul** : R/trade de la config par défaut, plein échantillon MT5 SP500, spread = 0 | ≤ 0 | PAS D'EDGE — le signal est négatif avant même le péage |
| **F3** | **LONGHIST — battre détenir** : sur 1927-2026 (adaptation close-only déclarée), le rendement annualisé des JOURS EN POSITION doit dépasser le rendement annualisé de TOUS les jours (B&H) | jours-en-position ≤ B&H par jour | le signal ne sélectionne pas des jours meilleurs que la moyenne — un long-only qui fait moins bien que détenir n'a pas d'intérêt |
| **F4** | **Sa propre doctrine** : split juin 2022 sur MT5 SP500 (2016-05/2022 vs 06/2022-2026). Si R/trade post-publication ≤ 0 alors que pré-publication > 0 | post ≤ 0 et pré > 0 | décroissance post-publication (McLean & Pontiff) et/ou sur-ajustement — PAS D'EDGE selon son propre critère |
| **F5** | **Effectif** : ≥ 20 trades OOS cumulés sur SP500 | < 20 | NON CONCLUSIF, sans négociation |

Lecture du filtre vendredi (sa « première amélioration ») : jugé UNIQUEMENT sur
le R/trade (retirer des trades baisse le total mécaniquement). Une amélioration
in-sample d'un filtre calendaire est le prototype du sur-ajustement — la
cellule est testée, pas crue.

## Grille (figée — 16 cellules)

| Paramètre | Valeurs | Rôle |
|---|---|---|
| `range_len` | 10, 20 | fenêtre du « trading range » (ambiguïté source : non spécifiée) |
| `pos_max` | 0.20, 0.35 | « near the low » = position du close dans le range ≤ q |
| `no_friday` | False, True | sa cellule d'amélioration — testée, pas crue |
| `sl_atr` | 3, 10 | le code source n'a PAS de stop ; 10 ATR = proxy « sans stop » (R3 impose un stop), 3 ATR = variante gérée. MAE rapportée. |

Fixés hors grille (déclarés AVANT mesure) : MACD 12/26/9, valeur = **ligne**
(EMA12−EMA26 — lecture la plus commune de « MACD value » ; l'histogramme n'est
pas balayé), baisse 5 jours consécutifs, MACD < 0. Sortie : cible statique
`max(high[i], close[i-1])` (voir dégradations). `engine_kwargs` :
`cooldown_bars=0`, `cb_losses=999` (fidélité source — pas de circuit breaker
chez lui), pas de `max_hold_bars` (il n'en a pas). Le témoin reçoit les mêmes
kwargs.

## Dégradations déclarées (avant mesure)

1. **Sortie dynamique → cible statique.** La règle source est « close casse le
   plus haut de la VEILLE » — seuil qui se recale chaque jour (cliquet
   descendant en marché baissier → sorties plus précoces). Le moteur commun
   (R9) n'exprime que SL/TP statiques : on pose la cible à
   `max(high[jour signal], close[veille])`, exacte pour une sortie dès le
   1er jour, de plus en plus conservatrice ensuite (tient plus longtemps, MAE
   plus profonde). Dégradation DÉFAVORABLE au signal en marché qui continue de
   baisser. Distribution des durées de détention à rapporter au VERDICT.
2. **Sortie au toucher intrabar au lieu du close confirmé.** Le moteur remplit
   la cible dès que `high ≥ cible` ; la source attend un CLOSE au-dessus.
   Sens de l'écart variable (parfois favorable, parfois non) — déclaré.
3. **Entrée au close du jour signal** au lieu de l'open du lendemain (semantique
   ProRealTime « buy at market » = prochain open). Écart d'un overnight.
4. **Stop obligatoire (R3)** alors que la source n'en a pas : 10 ATR ≈ jamais
   touché en régime normal, mais chiffre le risque de gap/krach au lieu de
   l'ignorer. L'exposition « sans stop, long-only indice » est quantifiée sur
   LONGHIST (pires excursions).
5. **LONGHIST est close-only** (o=h=l=c sur TOUT l'historique, vérifié) : le
   range devient un range de closes, l'ATR une moyenne de |Δclose|, la cible
   `close[i-1]`. Les niveaux intrabar n'existent pas → exécution au close
   uniquement, spread nul (les coûts d'époque sont inconnus ; le test LONGHIST
   est STRUCTUREL, pas exécutable). Les chiffres LONGHIST ne sont jamais
   comparés aux chiffres MT5.

## Addendum 2026-08-16 — corrections de fidélité POST-gel (déclaré, daté)

Reçu du coordinateur APRÈS le gel et APRÈS les premiers runs MT5 : le
transcript indépendant `docs/sources/prorealalgos/10_started_2025.txt`
(@19:30) confirme les règles et en ajoute UNE que le transcript s12 ne
mentionnait pas : **close < close[1]** (« the close of today is weaker than
yesterday »). Release exacte : **2022-06-21** (@14:30). Leur MACD est
possiblement leur « S-MACD » normalisé prix (fichier 05 — définition
propriétaire non publiée ; le signe et la baisse 5 j sont quasi invariants par
cette normalisation).

Traitement : la grille gelée N'EST PAS modifiée. Trois variantes hors grille,
config par défaut sinon, mesurées dans `backtests/addendum.txt` :
A1 = +close_down (règle fidèle), A2 = A1 + MACD/close (proxy S-MACD). WF +
témoin rejoués pour A1/A2 sur SP500. C'est une correction de fidélité à la
source, pas une chasse au résultat — les falsifications F1-F5 s'appliquent aux
variantes fidèles au même titre. Piste « RSI 14 < 30 D1 indices » (fichier 04,
2e source convergente avec aipathways T1) : notée pour une SUITE, pas ajoutée —
la grille est gelée.

## Angle mort de la source (noté avant mesure)

Sa doctrine « ne juger que depuis la release » est un hold-out honnête POUR UN
algo. Mais il en publie ~30 et met en avant celui qui « a bien marché depuis sa
sortie » : c'est du multiple testing SUR l'out-of-sample. Le survivant parmi 30
n'est pas une preuve — au seuil de 5 %, ~1,5 survivants sont attendus par pur
hasard. À rappeler au VERDICT quel que soit le résultat.

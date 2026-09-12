# input-adrian — S023 Turnaround Tuesday (René Balke)

*Maintenu par cc-support. Réécrit en place, pas d'historique (git porte la traçabilité).*

## Identité
- **Numéro** : S023 · magic `130023`
- **Source** : YouTube — René Balke (BM Trading, @ReneBalke), « In 48 Minutes I show you
  how I made €100,000 », https://www.youtube.com/watch?v=qgsi-u0kOVw — règle à
  [13:48]-[15:58], réglages live à l'écran à [27:41]-[29:19]. Guide d'entrées de l'EA :
  `docs/sources/renebalke/ea_inputs/Turnaround Tuesday EA Inputs.pdf` ;
  page produit https://bmtrading.de/en/expert-advisors/.
- **Auteur déjà connu du dépôt** : S009 (Range Breakout), S020 (MACD cross),
  S022 (ATR Candle Breakout). Corpus `docs/sources/renebalke/`.

## La demande d'Adrian (2026-09-12)
> « reproduis Turnaround Tuesday de Balke telle quelle, mesure, rapporte ; GO 2026-09-12 »

Et la doctrine qui gouverne désormais toutes les stratégies :
> « les règles générales ne sont plus valables — chaque stratégie porte ses propres
> règles — bien entendu elles auront des règles communes pour éviter les pertes
> consécutives — laisser les chances à chaque stratégie... »

Et la méthode : **aucun avis avant d'avoir essayé**. On construit, on mesure, puis on
rend compte de ce que disent les chiffres.

## La règle, telle qu'il la trade
Le lundi uniquement : si le prix est sous la moyenne mobile **simple journalière**
(période par indice — **US30 25, US Tech 9, DE40 40**, calculée sur les clôtures),
achat. On tient lundi et mardi, clôture le mardi soir (23:50 heure serveur ; 22:55 pour
le DE40). Ouverture 01:05 (DE40 09:05). Achat seulement. **Ni stop, ni take profit,
aucune gestion.** Risque notionnel 25 000 € par trade.

Sa thèse : après un week-end et une semaine baissière, le lundi-mardi porte un mouvement
de reprise. Il précise ne pas en être l'auteur — *« it's a very common strategy »*.

Ce qu'il annonce en live (depuis mars 2024) : ~160 trades, +16 k€, profit factor
« much better » que Go Long, profitable sur les trois indices — avec sa propre réserve :
*« probably I was lucky in the period »*.

## Ce que la plateforme a dû ajouter, et qu'il faut savoir en lisant les chiffres
1. **Un stop.** `Signal.stop` est obligatoire ici (R3) ; lui n'en a pas. S023 déclare sa
   propre règle : `guard_pct`, **garde catastrophe** à 5 % sous l'entrée — jamais un stop
   de gestion. Le harnais compte les trades qui la touchent.
2. **La sortie par l'heure** est approximée par un nombre fixe de barres H1
   (`max_hold_bars` : 45 pour NASDAQ/US30, 27 pour le DAX), calibré sur les données.
3. **Le sizing** (25 000 € de notionnel) est hors stratégie (R2). Nos chiffres en R ne
   sont donc pas comparables à ses euros : tout est aussi rapporté **en % du prix
   d'entrée**, la seule unité qui se compare à son « +0,4 % par trade ».

## État (2026-09-12)
- Reproduite telle quelle, 24 tests verts, R1 (causalité) et R5 (conformance) passés sur
  les trois indices — et ils bloquent : en défaut, le harnais s'arrête sans publier.
- **Mesurée** : cellule de fidélité par instrument, référence non filtrée, grille de
  18 cellules, walk-forward ancré 4 fenêtres, témoin aléatoire, spread catalogue ET
  mesuré, bras « règles communes ». Critères écrits **avant** :
  `research/FALSIFICATION.md`.
- **Verdict** (`research/VERDICT.md`) : **échec au sens des critères** — il en fallait
  deux indices sur trois, il n'y en a qu'un. **Le DAX passe nettement** (sa cellule
  live SMA40 : 91 trades, **+0,445 %/trade**, PF 1,92, **percentile témoin 97,5**,
  positive au spread mesuré 23 pips, et encore +0,227 %/trade si on retire 2025-2026).
  **NASDAQ (+0,280 %/trade, percentile 75,5) et US30 (+0,156 %, percentile 79,5) ne se
  distinguent pas du hasard** — et sur ces deux-là, acheter chaque lundi **sans** filtre
  rapporte davantage (+53 % et +27 % cumulés contre +31 % et +16 %).
- Le dispositif, lui, est validé : cadence prédite avant mesure (85-120 trades/indice)
  exacte, garde catastrophe touchée 0-2 fois sur ~100 trades, sorties le mardi soir
  dans 86-99 % des cas.
- Statut `BACKTESTED` — **mesuré, pas validé**.

## Ce qui attend Adrian
| Sujet | Décision |
|---|---|
| **Forward scellé sur le DAX seul** (cellule SMA40 · first_bar · garde 5 %), protocole écrit avant le premier signal (modèle `studies/gold_forward/`, `studies/s20_forward/`) — ou abandon des trois | GO / pas GO — R10 |
| L'absence de stop réel : en production le risque est le notionnel (lui pose 25 000 € par trade). Un plafond de portefeuille est nécessaire **avant** tout PAPER — les règles communes du moteur sont inertes ici (un trade par semaine, refroidissement de 24 barres) | arbitrage couche risque |
| Le voisin **Go Long** (même auteur, achat quotidien d'indice sans aucun filtre) devra être mesuré en sachant que sur 2021-2026 **toute** exposition longue aux indices US paie : son témoin doit être choisi en conséquence, sinon il mesurera la dérive et l'appellera un edge | ordre de priorité |

## Ce que S023 ne fait pas, et pourquoi
- Pas de réglage après lecture des résultats : la grille de 18 cellules est celle du
  manifeste, figée avant la mesure.
- Pas de promotion : aucun statut ne change sans décision d'Adrian.
- Pas d'optimisation de la période SMA hors des trois qu'il trade.

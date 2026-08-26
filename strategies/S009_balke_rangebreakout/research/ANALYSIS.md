# s09 — Analyse Phase 1 : Session Range Breakout (René Balke)

## 1. Source

- Auteur : René Balke (BM Trading, @ReneBalke), programmeur MQL5. Modèle
  économique = rebate broker IC Markets/IC Trading (EA « gratuits » sous
  referral). Corpus : 15 transcripts dépouillés dans
  `docs/sources/renebalke/SYNTHESE.md` ; code tutoriel reconstitué dans
  `docs/sources/renebalke/code/RangeBreakout_tutorial_reconstruction.mq5`.
- Crédibilité : la plus haute falsifiabilité du corpus — il publie ses PERTES
  chiffrées (−8 759 € pire mois, GBPUSD −8 778 € sur ~360 trades, USDJPY −3 k€
  janv. 2026) et ses réglages exacts. Ses gains (50k→800k backtest, +57k live)
  restent des claims non auditables. Sa méthode d'optimisation est du plein
  échantillon 10-15 ans sans hors-échantillon — son live EST son OOS, et sur
  GBPUSD il a rendu son verdict.

## 2. La méthode, reformulée

Chaque jour : le high/low des bougies M1 entre deux heures fixes (heure serveur
GMT+2/+3) définit un range. À la fin du range, deux stop orders aux bords
(buy stop au high, sell stop au low). Premier ordre exécuté → l'autre est
supprimé (réglage live actuel ; variante « 2 breakouts » = l'ordre opposé
reste et peut faire un trade de retournement). SL = l'autre côté du range
(facteur 1) OU 1 % du prix. **Pas de TP.** Clôture forcée de toute position à
heure fixe (18:00 ; 18:55 or). Ordres non exécutés supprimés à 18:00. Filtre
optionnel de taille de range (min/max en % du prix). Sizing par risque fixe
(hors périmètre stratégie, R2).

Réglages tradés documentés :

| Symbole | Range | SL | Filtre | Clôture | Live déclaré |
|---|---|---|---|---|---|
| USDJPY | 3:00-6:00 | range opposé | aucun | 18:00 | +10k€ à déc 25, −3k janv 26 |
| USDJPY var. | 3:00-4:30 | 1 % | 0,2-0,4 % | 18:00 | +1,5k€/an |
| XAUUSD | 3:05-6:05 | 1 % | 0,15-0,85 % puis retiré | 18:55 | « +15k€/an » (incohérence interne, SYNTHESE §4.6) |
| GBPUSD | 4:00-11:30 | range opposé | aucun | 18:00 | **−8,8k€ / ~360 trades** |

## 3. L'hypothèse testable

Le range 3-6h (fin de Tokyo / pré-Londres) concentre l'information de la
fenêtre de faible liquidité ; sa cassure au retour du flux (Londres) initie un
mouvement directionnel qui, laissé courir sans TP jusqu'à 18h, a une espérance
positive nette de coûts. C'est le **jumeau inversé de s91** : même structure
d'information (l'heure), exploitation opposée (suivre la sortie de la fenêtre
au lieu de fader l'extension dedans). s91 a mesuré l'effet brut à +0,05 R/trade
OOS, tué par un péage 1,5×. La question de la mission : son package (stop
large, queue droite sans TP, sortie temporelle, 1 trade/jour) fait-il passer
le même effet au-dessus des coûts ? Son claim implique ≈ +0,15 R/trade net.

Qui paie ? Les stops accumulés des deux côtés d'un range nocturne étroit +
le flux directionnel d'ouverture de Londres qui doit traverser un carnet
reconstitué. C'est une anomalie ancienne, simple, publiée (« London breakout »,
des décennies de littérature grise). Vérifications n°1 et n°2 de METHODOLOGY
§1 : passées. N°3 (adaptée à l'actif) : c'est exactement ce que le test doit
dire.

## 4. Reproductibilité composant par composant

| Composant | Chez nous | Dégradation |
|---|---|---|
| Range M1 3h-6h | high/low des barres H1 3,4,5 — **exact** (mêmes extrêmes) si bornes pleines | bornes 4:30/11:30/3:05 arrondies à l'heure |
| Stop order au bord du range | **Non disponible** (moteur : entrée au close du signal). Substitut : détection de cassure au close H1, entrée à ce close | entrée retardée ≤ 1h, prix pire que le bord ; défavorable au signal, déclaré |
| SL = range opposé / 1 % | exact (Signal.stop) ; ambiguïté de la base du 1 % (prix d'entrée vs bord du range) → deux cellules de grille | — |
| Pas de TP | `target=None` — le moteur le supporte | — |
| Clôture 18h | `max_hold_bars` via engine_kwargs (commit 2188ac6) — fixe en barres, pas en heure d'horloge | dérive de +1h par heure d'entrée tardive ; distribution des sorties rapportée |
| 1 vs 2 breakouts | booléen de grille ; le moteur (position unique) sérialise naturellement | — |
| Filtre taille de range | exact | — |
| Suppression d'ordres 18h | signaux non émis après 17h | — |
| Fuseau | calibré : Swissquote = GMT+3 (pic Londres/NY à l'heure serveur 16, `economics.txt`), même convention « NY close » que IC Markets. Ses bornes se transposent telles quelles | le DST décale d'1h deux fois/an chez LES DEUX brokers — bruit symétrique |

Données : H1 Swissquote 2021-07 → 2026-08 (~31 594 barres, 1 313 jours à range
complet). Pas de M1 ; M15 non couvert pour ces instruments. Son backtest est
10 ans Dukascopy : notre période est moitié plus courte et entièrement dans un
seul régime macro — limite déclarée.

## 5. Économie a priori

Voir `economics.txt` et FALSIFICATION.md. Résumé : drag SL=range 9,1 %
(USDJPY), 4,7 % (GBPUSD), 3,3 % (XAUUSD), 12,1 % (EURJPY) ; drag SL=1 % :
1,2-2,3 %. Le « stop large » n'est vrai qu'en variante 1 %. 97 % des jours
USDJPY cassent le range (première cassure méd. 8h) — effectif attendu
~250 trades/an/instrument, largement au-dessus de F6.

## 6. Décisions d'implémentation

- H1, warmup 0 (le range se construit dans la journée). `precompute` → DataFrame
  (close, hour, range_high, range_low, range_ok…) pour que R1 inspecte
  réellement la couche indicateur (leçon s91 §2.9).
- Signal au close de la première barre H1 (heure ∈ [fin_range, 17]) dont le
  close sort du range. breakouts=2 : signal supplémentaire au premier close
  au-delà du bord opposé après la première cassure (le moteur ne l'exécute que
  si la première position est fermée — sémantique du retournement de Balke,
  son SL étant précisément ce bord).
- engine_kwargs : max_hold_bars {USDJPY 11, XAUUSD 12, GBPUSD 5, EURJPY 11},
  cooldown_bars=0, cb_losses=999 (fidélité source — il n'a ni cooldown ni
  circuit breaker ; identiques pour le bras témoin).
- GBPUSD absent du catalogue core (interdit d'y toucher) : InstrumentSpec
  construit dans les scripts de backtest, spread = médiane de la colonne
  `spread` du cache (2,2 pips), max_spread 3×.

## 7. Ce que le test tranchera

Voir FALSIFICATION.md (F1-F6, figées avant tout backtest) et SYNTHESE §6.

# Source — AI Pathways : « How To Actually Find A Profitable Strategy With Claude »

**Lien** : https://www.youtube.com/watch?v=Fb7G5SNpaes
**Chaîne** : AI Pathways (73,5k abonnés) · 28k vues · 80 commentaires
**Auteur** : Brendan — maths/éco UCLA, 3 ans en banque d'investissement

## Nature

**Ce n'est pas une stratégie, c'est une méthode.** Elle est donc versée dans
`docs/METHODOLOGY.md` comme aide méthodologique commune à tous les Claude de
stratégie — au même titre que le backtester commun.

## Ce qu'il rapporte

| | |
|---|---|
| Idées testées | ≈155 |
| Fenêtre de test scellée | 2023-01 → 2026-07 |
| Survivants | 5 (4 jambes + 1 overlay de sizing) |
| Taux de survie | ≈3 % |

Onglets de son tableau de bord : Overview & Graveyard · Filters · Survivors ·
Portfolio · 2000s Stress · Risk · Forward.

Mention explicite dans son rapport : *« stats are test-window; parameters are
conventions or train-selected (no test-window fitting) »*.

## Ses cinq survivants

| | Stratégie | Chiffres annoncés |
|---|---|---|
| A | **Trend core** — détenir QQQ au-dessus de sa MM200, GLD en dessous. Signal à la clôture, exécution à l'ouverture suivante | +33,8 % CAGR · Sharpe 1,66 · DD −13,6 % · 5,3 bascules/an |
| B | **Rotation 52 sem.** — mensuel, les 5 ETF (sur 50) les plus proches de leur plus-haut 52 semaines ; cash si SPY < MM200 | +18,5 % CAGR · Sharpe 1,60 · DD −9,9 % |
| C | **IBS dip-sniper** sur SPY — clôture dans les 10 % bas de la séance et indice au-dessus de sa MM200 → achat ; sortie sur clôture forte ou après 3 jours | — |
| D | **NQ opening-range breakout** — cassure du range des 30 premières minutes | — |
| E | **Overlay de sizing** — dimensionner pour viser ~20 % de volatilité portefeuille | — |

## Caveats qu'il signale lui-même (à son crédit)

- Sur **A** : le repli sur GLD tient en partie à la vigueur récente de l'or ;
  2005-09 favorisait plutôt un repli en cash.
  → **C'est exactement le piège attrapé sur USDJPY** (+69,7 R long / −10,0 R short).
  Notre contrôle long/short le testerait directement.
- Sur **B** : seule stratégie dont le Sharpe s'améliore hors échantillon —
  il annonce surveiller une régression vers son niveau d'entraînement.

## Ce qui est reproductible chez nous

Équivalences présentes dans `core/data/instruments.py` :

| Lui | Nous |
|-----|------|
| QQQ | NASDAQ (`#NAS100`) |
| SPY | SP500 (`#US500`) |
| GLD | XAUUSD |
| NQ futures | NASDAQ CFD |

**La stratégie A est directement testable** : règle entièrement mécanique, peu de
paramètres, timeframe D1 dont nous avons 5 ans.

## Ce qu'il fait mieux que nous

**Le stress sur une autre décennie** (2000-2009 : dot-com + crise financière).
Nos données couvrent 2021-2026 — un seul régime. C'est notre faiblesse
méthodologique n°1, et la seule où cette source a un avantage réel.

Action qui en découle : acquérir de l'historique long (Dukascopy, ou données ETF
gratuites remontant aux années 2000) pour pouvoir faire notre propre test de
stress.

## Ce que nous faisons mieux

Sa règle « pas de vision du futur » est une **consigne de prompt**. La nôtre (R1)
est un **test mécanique** — l'invariant de troncature. Une consigne n'est pas une
preuve : notre propre bug `closes[-1]` a survécu des mois précisément parce que
l'intention était bonne et le code faux.

## Captures

Déposer dans `screenshots/`. Frames intéressants : « the 3 checks » (~5:00),
diagramme de comportement par actif (~5:48), prompt de recherche de candidats
(~6:08), règles du moteur de test (~10:04-11:20), tableau de bord des résultats
(~12:25), les 3 filtres (~14:03), les 5 survivants (~15:15), corrélations
portefeuille (~17:20).

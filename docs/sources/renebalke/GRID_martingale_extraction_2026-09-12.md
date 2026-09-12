# René Balke — grille martingale « Golden Horse » : règle extraite

**Source** : « FULL CODE for this 99% WIN Forex Trading Robot (mql5 Programming
Tutorial) », 2025-12-20, 94 min, https://www.youtube.com/watch?v=Vzz-gEFmWgM
**Méthode** : transcript auto-généré (74 700 caractères) lu sous quatre angles
indépendants (règle, code, leviers, mesure) puis contre-lu (fidélité, réimplémentation).
Chaque point porte son horodatage. **Rien n'est jugé ici** : on extrait, on reconstruit,
on liste ce qu'un portage devra trancher. Le jugement viendra de la mesure (S021,
après TCK-020).

---

## 1. Ce que dit la miniature, et ce que dit la vidéo

La miniature affiche **« +35 000 $ »** et « 99 % HITRATE » sur un rapport du Strategy
Tester MT5 (mise en page Balance/Equity + « Deposit Load », dates 2020-01-22 → 2025-04,
échelle ~10 000 → ~48 000). C'est donc **un backtest de cinq ans à partir d'environ
10 000**, avec des plongeons d'équité profonds (le plus visible vers 2024-10, de
~40 000 à ~20 000). Aucun de ces deux chiffres n'est prononcé dans la vidéo. L'auteur
dit : *« in the best case a very steady and profitable equity balance and equity curve.
Of course, this is not risk-free »* [01:26].

Dans la vidéo, le compte est **soufflé deux fois** en démonstration — *« we go
bankrupt »* [73:55] avec 0,05 → 0,15 → 0,45, puis *« we actually even hit the final
stop out »* [90:47] — avant qu'il n'élargisse la grille et survive 2025 *« even though
there was a big draw down »* [91:31].

## 2. La règle, complète

| Étape | Règle | Source |
|---|---|---|
| Référence | plus-haut et plus-bas **cumulatifs du bid**, mis à jour à chaque tick, sans fenêtre de barres | [40:09] |
| Première entrée | ACHAT si bid < plus_haut − `grid_points`·point et aucun achat ouvert ; VENTE si bid > plus_bas + `grid_points`·point et aucune vente ouverte. Volume `start_lots`, au marché, **sans SL ni TP d'ordre** | [43:56] [45:26] [48:47] |
| Ajout | nouvel achat dès que bid < prix d'ouverture **le plus bas** du panier − `grid_points`·point ; volume = `NormalizeDouble(lot_de_cette_position × multiplier, 2)`. Miroir pour la vente | [66:44] [67:15] [69:39] |
| Sortie | prix moyen **pondéré par les lots** Σ(prix·lots)/Σlots ; si bid > moyenne_achat + `tp_points`·point → fermeture de **tout** le panier achat ; miroir vente | [75:22] [82:46] |
| Après sortie | remise à zéro des extrêmes (highest = 0, lowest = DBL_MAX) et des compteurs | [86:45] [88:47] |
| Deux côtés | paniers achat et vente **indépendants et simultanés** (compte hedging) | [64:16] [84:17] |
| Risque | **aucun** stop, **aucun** nombre maximal de niveaux, aucun plafond de lot, aucune coupure d'équité. Seule borne : le stop-out du courtier | [48:47] [90:47] |

**Paramètres montrés** : `grid_points` = 1 000 · `start_lots` = 0,05 (ou 0,01) ·
`multiplier` = 3 (« very aggressive » [70:07]) · `tp_points` = 100 (200 annoncé en
intro [00:56]) · `is_comment` (bool). Pas de magic number, pas de filtre de symbole.

## 3. Pseudocode reconstitué (OnTick)

```
bid = bid courant
highest = max(highest, bid) ; lowest = min(lowest, bid)          # latch monotone
# recensement, recalculé intégralement à chaque tick
pour chaque position du COMPTE (pas de filtre symbole/magic) :
    achat : n_buy += 1 ; lowest_buy_price/lots = (prix, lots) si prix < lowest_buy_price
            sum_buy += prix·lots ; lots_buy += lots
    vente : miroir avec highest_sell_price
avg_buy = sum_buy / lots_buy si lots_buy > 0 ; avg_sell idem
# sortie panier
si avg_buy > 0 et bid > avg_buy + tp·point  : fermer tous les achats ; reset extrêmes et compteurs
si avg_sell > 0 et bid < avg_sell − tp·point : fermer toutes les ventes ; reset
# entrées
si n_buy == 0 : si bid < highest − grid·point : Buy(start_lots)
sinon         : si bid < lowest_buy_price − grid·point : Buy(round(lowest_buy_lots × mult, 2))
si n_sell == 0 : si bid > lowest + grid·point : Sell(start_lots)
sinon          : si bid > highest_sell_price + grid·point : Sell(round(highest_sell_lots × mult, 2))
```

## 4. Ce que le portage devra trancher (la vidéo ne le dit pas)

1. **Portée des extrêmes** : latch global depuis le démarrage — jamais une fenêtre de
   N barres. Sur un marché en tendance, le plus-haut ne redescend jamais ; après un
   sommet, la condition d'achat est vraie en permanence. Le choix (latch global /
   fenêtre / session) change entièrement la fréquence des paniers.
2. **Reset après clôture** : l'auteur se contredit trois fois ([86:45], [88:17],
   [88:47]) ; la seule version qui produit son backtest final est highest = 0 /
   lowest = DBL_MAX. Et la clôture du panier ACHAT réinitialise aussi la référence
   VENTE (contamination croisée jamais évoquée).
3. **Bid seul, ask jamais lu** : les achats sont exécutés à l'ask, déclenchés et
   sortis au bid ; la sortie vendeuse est amputée d'un spread entier. Choix de portage
   à déclarer, pas à reproduire par accident.
4. **Arrondi de lot en dur** à 2 décimales, sans lecture des bornes du courtier.
5. **Aucune vérification du retour d'ordre** : un ordre refusé est retenté à chaque tick.
6. **Compte hedging obligatoire** — jamais précisé.

## 5. Leviers que l'auteur nomme, et ceux qu'il ne nomme pas

Nommés : tout est en `input`, *« great for optimization and testing »* [00:51] ; le
multiplicateur 3 est modifiable [70:07] ; après la ruine, *« play around with your
parameters »* [90:57] — le seul geste qu'il fait est d'élargir grille et TP [91:08].

Non nommés, évidents pour un chercheur : distance en ATR plutôt qu'en points fixes,
multiplicateur < 3, nombre maximal de niveaux, TP fonction de la profondeur, coupure
d'équité de panier, filtre de régime (range/tendance), une seule grille à la fois,
choix d'instrument. Chacun ajoute un paramètre et pose une question de mesure.

## 6. Ce qu'il faut pour la mesurer honnêtement

Capacités moteur (TCK-020) : positions multiples de même sens à volumes relatifs,
état de panier et clôture groupée, stop **de panier**, deux paniers à équité commune
avec marge et stop-out simulés, coût par position. Témoins : structure gelée avec
instant du premier ordre tiré au hasard, **et** la même grille à multiplicateur 1.
Métriques : espérance par panier avec IC, drawdown d'équité **flottante**, exposition
et marge maximales, profondeurs, probabilité de ruine par bootstrap par blocs. Le taux
de réussite ne dit rien : un panier ne se ferme que gagnant.

Coût : avec un TP de 100 points, le coût d'un panier vaut spread/TP quelle que soit la
profondeur — 19 % sur EURUSD au spread mesuré, 60 % sur AUDCAD. Le TP devra s'exprimer
en multiples du spread mesuré, jamais en valeur absolue héritée de la vidéo.

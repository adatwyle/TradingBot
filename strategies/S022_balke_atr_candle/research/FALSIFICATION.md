# S022 — critères de falsification

**Écrit le 2026-09-12 à 19:11, AVANT toute exécution du harnais** (dépôt `f40118f` ;
`backtests/run_wf.py` n'a jamais tourné à cette heure — le fichier `results.json`
n'existe pas encore). Un critère rédigé après lecture des résultats n'est pas un
critère.

---

## L'hypothèse

Sur XAUUSD H1, une bougie close dont l'amplitude dépasse un multiple de l'ATR et qui
ferme près de son extrême annonce une continuation du mouvement suffisante pour qu'un
stop à 0,5 % et une cible à 2 % (RR 4) produisent une espérance positive **nette du
coût de bord réel**, hors de l'échantillon qui aurait servi à la régler.

C'est la règle de l'EA gratuit « ATR Candle Breakout » de René Balke, reproduite avec
**ses réglages live** (H1, ATR 200, × 2,5, proximité 25 %, TP 2 %, SL 0,5 %, filtres
désactivés, corps 0). Elle a la particularité rare, dans ce dépôt, d'arriver avec des
chiffres publiés à confronter — donc avec un **test de fidélité** possible, distinct du
test d'espérance.

## Ce qui est reproduit, et ce qui ne l'est pas

**Reproduit tel quel** : le déclencheur (amplitude > multiple × ATR sur les barres
antérieures, clôture à moins de 25 % de l'amplitude de l'extrême, sens de la bougie),
la géométrie des sorties en pourcentage du prix d'entrée, une position par symbole,
tous les filtres optionnels laissés désactivés comme dans son live.

**Non reproduit** : le sizing (« Risk per trade », couche risque — R2) ; le trailing
(désactivé en live) ; le modèle de ticks du Strategy Tester MT5 et les données
Dukascopy tick de son backtest — nous travaillons sur barres H1 Swissquote closes, ce
qui change nécessairement les remplissages ; le `Slippage (points)` de l'EA (notre
slippage est à 0, comme partout dans le dépôt : **optimiste d'un montant inconnu**).

**Inconnue déclarée** : `Min candle body-to-range ratio`. Sa valeur live n'est pas
dite. Hypothèse fidèle retenue : **0 = filtre désactivé**, cohérent avec « filtres tous
désactivés ». Le paramètre existe, hors grille ; il ne sera pas balayé.

**Ajouté par la plateforme** : le coût de bord réel du courtier (spread catalogue puis
spread médian réellement coté), le bras témoin aléatoire à dispositif de risque
identique, et — en second bras d'information seulement — le refroidissement et le
coupe-circuit communs.

---

## Les deux bras de moteur, déclarés d'avance

| Bras | Réglages moteur | Statut |
|---|---|---|
| **Fidèle** (primaire, celui qui décide) | `max_positions=1, cooldown_bars=0, cb_losses=999, cb_cooldown_bars=0, max_hold_bars=None` | tous les chiffres de décision (plein échantillon, walk-forward, témoin, spread mesuré) |
| **Règles communes** (secondaire) | `max_positions=1, cooldown_bars=2, cb_losses=3, cb_cooldown_bars=24` | information seule, sur la cellule par défaut |

**Pourquoi le bras fidèle n'a pas de coupe-circuit.** Doctrine Adrian du 2026-09-12 :
chaque stratégie porte ses propres règles, les règles communes protègent le
*portefeuille* des pertes consécutives et ne doivent pas être imposées à la mesure
fidèle. Ici l'argument est chiffré : l'auteur annonce un taux de réussite ≈ 23 %, donc
trois pertes d'affilée surviennent une fois sur deux (0,77³ ≈ 46 %). Un coupe-circuit
commun à 3 pertes ne couperait pas le risque, il couperait la règle — et mesurerait
autre chose que ce que l'EA fait. S022 **déclare donc « pas de coupe-circuit » comme
règle propre**. Le second bras est là pour rendre visible ce que coûteraient les règles
communes si le portefeuille les imposait un jour.

---

## Test de fidélité — ses chiffres publiés

Source : billet <https://bmtrading.de/en/blog/atr-candle-breakout-ea/> (2026-06-09),
backtest XAUUSD 2015→2026 sur tick réel Dukascopy (561 M ticks, qualité d'historique
100 %) :

| Mesure publiée | Valeur |
|---|---|
| Trades | **1 552** sur 11 ans → **≈ 141/an** |
| Taux de réussite | **≈ 23 %** (« If a 23% win rate makes you nervous, this isn't the strategy for you ») |
| Profit factor | **1,15** |
| Résultat net | **+19 527 €** sur 50 000 € |
| Drawdown max | **≈ 9,6 %** |

Et sa comparaison test / live depuis mars 2026 (journal Trade Buddy) : **23 trades
+634,03 €** au testeur contre **24 trades +515,65 €** en réel ; WR 26,1 % contre 25,0 % ;
PF 1,40 contre 1,30 ; DD 1 028 € contre 1 139 €. Son journal donne par ailleurs, sur le
portefeuille live, 55 trades, WR < 30 %, gain moyen 370 € pour 90 € de perte moyenne.

Arithmétique de contrôle : à RR = 4 et WR 23 %, l'espérance **brute** vaut
0,23 × 4 − 0,77 = **+0,15 R/trade**. C'est l'ordre de grandeur auquel comparer notre
R/trade mesuré, **coût de bord déduit** (le coût sera rapporté en R).

### Critères de fidélité (cellule par défaut = ses réglages live, bras fidèle, 6 ans)

| Grandeur | Fenêtre attendue |
|---|---|
| Trades par an | **85 – 200** |
| Taux de réussite | **17 – 30 %** |
| Répartition des sorties | **dominée par les stops** (SL majoritaire) |
| R/trade | à comparer à +0,15 R brut, en affichant le coût de bord en R |

**Si la fréquence ou le taux de réussite tombent nettement hors de ces fenêtres, c'est
un problème de DISPOSITIF, pas un verdict sur l'hypothèse** : définition de l'ATR
(moyenne simple type iATR MT5 — notre défaut — contre lissage de Wilder), décalage de
l'ATR, sémantique de la proximité, ou données. Dans ce cas : instruire l'écart (le
paramètre hors grille `atr_mode` existe pour ça et pour rien d'autre), **rapporter les
deux lectures**, et ne pas conclure sur l'espérance tant que la fidélité n'est pas
comprise. **Aucune cellule de grille ne sera ajoutée** pour autant.

Rappel de l'écart structurel attendu, qui interdit d'exiger une reproduction exacte :
son test est sur tick réel Dukascopy 2015-2026 avec son courtier et son spread, le
nôtre sur barres H1 Swissquote 2020-2026 avec un spread or médian ≈ 90 pips
(0,90 $/once) et un remplissage volontairement pessimiste (stop payé au pire de
`min(stop, open)`, stop prioritaire sur cible dans la même barre).

---

## Les seuils d'espérance

### Réussite — toutes ces conditions, sur une même cellule

1. **Hors échantillon** : cellule STRICT au walk-forward ancré (4 fenêtres, profitable
   en apprentissage ET positive hors échantillon sur chacune), avec **≥ 20 trades hors
   échantillon**.
2. **Témoin** : percentile **≥ 90** contre le bras aléatoire à dispositif de risque
   identique.
3. **Coût absorbé** : **R/trade > 0 au spread MESURÉ** (médiane de la colonne `spread`
   des barres sur 12 mois), pas seulement au spread catalogue.
4. **Multiplicité** : 12 cellules → ≈ 0,6 réussite par pur hasard à 5 %. Il faut donc
   **≥ 2 cellules STRICT**, **ou** une cellule au **percentile témoin ≥ 97**.
5. **La cellule par défaut — ses réglages live — est elle-même positive hors
   échantillon.** C'est une reproduction : si le réglage qu'il trade réellement ne
   passe pas, une cellule voisine qui passe est une découverte de grille, pas une
   confirmation de sa stratégie.

### Échec — l'une suffit

- Aucune cellule STRICT, ou aucune cellule au percentile témoin ≥ 90.
- Le signal disparaît entre plein échantillon et hors échantillon.
- Résultat porté par une seule année (une année qui pèse ≥ 100 % du R total).
- Coût de bord > **35 %** du R médian de la cellule (stop en % trop serré pour le
  spread de l'or).

### Non concluant

- Moins de **20 trades** hors échantillon sur toutes les cellules : effectif
  insuffisant, ni réussite ni échec.

### Échec du dispositif, pas de l'hypothèse

- R1 en défaut → on corrige et on remesure.
- Fidélité hors fenêtres ci-dessus → instruire (ATR simple contre Wilder, décalage,
  données) et rapporter les deux, avant tout jugement d'espérance.

**Enregistrement systématique** : R et nombre de trades **par année** pour chaque
cellule, répartition des motifs de sortie, coût de bord en % du R, et le bras « règles
communes » (R total et effectif) à côté du bras fidèle sur la cellule par défaut.

---

## Ce qui ne sera pas fait

- Aucun ajout de cellule, de commutateur, de filtre ou d'instrument après lecture des
  résultats. La grille de 12 cellules est figée ci-dessus.
- Aucun réglage de `atr_period` (200) ni de `tp_pct` (2 %) : ce sont ses valeurs
  dictées. Les balayer transformerait une reproduction en optimisation.
- Aucune implémentation des filtres optionnels (tendance, MTF, horaire, S/R) : ils sont
  désactivés dans son live.
- Aucun déplacement de seuil après coup, dans aucun sens.
- Aucune promotion PAPER ou LIVE : décision Adrian (R10).

## Ce que chaque issue nous apprendra

| Issue | Lecture |
|---|---|
| Réussite, fidélité OK | La règle porte sur l'or H1 chez notre courtier, et nous reproduisons bien la sienne. Étape suivante : forward scellé, décision Adrian. |
| Réussite, fidélité hors fenêtre | Nous mesurons quelque chose de rentable **mais pas forcément sa règle**. Comprendre l'écart avant toute suite. |
| Échec avec coût < 35 % | Le déclencheur ne contient pas d'information exploitable sur nos barres H1 et notre spread — malgré ses 11 ans sur tick. L'écart d'exécution (tick contre barre close, spread) devient le premier suspect. |
| Échec par coût | La géométrie 0,5 % de l'or est trop serrée pour un spread de 90 pips chez ce courtier : la règle vaut peut-être ailleurs (autre courtier, autre stop). |
| Non concluant | Effectif insuffisant : remesurer avant de juger, et se demander pourquoi la fréquence s'écarte des 141 trades/an annoncés. |

---

# Addendum — 2026-09-12 19:48, APRÈS la mesure

**Rien de ce qui précède n'est modifié d'un caractère.** Cet addendum ne touche aucun
seuil, aucune fenêtre, aucune clause : il consigne deux points d'interprétation relevés
à la relecture, avec les chiffres qui permettent d'en juger.

### A. Le sens de la bougie est une interprétation, pas une citation

Le guide et le blog disent « close near its own extreme — near its high for a buy, near
its low for a sell », puis « The EA then trades in the direction of that breakout ». Ils
**n'exigent pas explicitement** que la bougie soit haussière pour un achat. Notre mise en
œuvre le demande : close > open pour un achat, close < open pour une vente — la lecture
la plus naturelle de « in the direction of that breakout », et la seule qui rende le sens
univoque si une bougie fermait près de ses deux extrêmes.

**Portée mesurée** (or H1, six ans, cellule par défaut) : 1 342 bougies dépassent
2,5 × ATR ; 857 ferment à moins de 25 % de leur amplitude d'un extrême ; **836 émettent
un signal, 21 sont écartées par la condition de sens** — 2,5 %, dont 0 doji et 0 bougie
proche de ses deux extrêmes à la fois. Une lecture sans condition de sens déplacerait
l'échantillon de 2,5 %, sans effet sur un verdict qui se joue sur l'absence **totale** de
cellule STRICT.

### B. Le drawdown publié (≈ 9,6 %) n'est pas comparable à notre drawdown en R

Le sien est un **pourcentage de capital** (≈ 9,6 % de 50 000 €) ; le nôtre est un
**multiple du risque** (43,8 R en plein échantillon sur la cellule live). Les deux ne
deviennent comparables qu'en fixant un dimensionnement — ce que la stratégie ne fait pas
et ne doit pas faire (R2 : la taille appartient à la couche risque). À titre purement
indicatif, **sous une hypothèse de sizing qu'il ne publie pas pour son test 11 ans** : à
son risque live de 100 €/trade sur 50 000 €, 9,6 % ≈ 4 800 € ≈ 48 R, soit l'ordre de
grandeur de nos 43,8 R. C'est un rapprochement, pas une mesure : aucun critère de ce
document ne s'y appuie, et aucun ne doit s'y appuyer.

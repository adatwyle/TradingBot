---
id: TCK-018
from: cc-support
to: cc-spec
status: open
blocking: false
created: 2026-09-06
---

## Question

Le catalogue `core/data/instruments.py:61` déclare pour XAUUSD
`spread_pips = 25.0` (pip 0,01 → **0,25 $**). Le backtester utilise cette valeur
scalaire pour tous les trades de tous les dossiers.

**Nos propres barres enregistrent un spread deux fois plus large.** `load_bars`
ramène déjà une colonne `spread` (en points broker) que personne n'exploite.
Mesure faite le 2026-09-06 sur le cache complet, XAUUSD `digits=3`,
`point=0,001` (vérifié via `mt5.symbol_info`) :

| timeframe | médiane toutes heures | heures actives (serveur 14-17h) | nuit (22-01h) |
|---|---|---|---|
| H1 (30 024 barres) | **52 pips** | 50 | 56 |
| M15 (119 992) | **56 pips** | 51 | 60 |
| M5 (358 624) | **58 pips** | 54 | 61 |

Soit un facteur **2,0 à 2,2×** par rapport au catalogue, **y compris aux heures
les plus liquides**. Aucune barre à spread nul, min 500 points (0,50 $) sur
358 624 barres : ce n'est pas un artefact de week-end.

**Impact mesuré** sur la cellule de référence de S018 (= cellule scellée du
forward or), moteur et données identiques, seul le spread change :

| | spread 25 pips | spread 52 pips |
|---|---|---|
| H1 — 402 trades | +94,7 R · **+0,236 R/trade** | +82,4 R · **+0,205 R/trade** |
| M15 — 1 604 trades | −153,6 R · −0,096 | −240,2 R · **−0,150** |

L'edge H1 **survit** (−13 % de R/trade), les conclusions intraday empirent. Aucun
verdict du dépôt ne bascule, mais tous les chiffres or publiés sont optimistes
d'un montant désormais **connu** — alors que `studies/gold_forward/PROTOCOL.md`
§ 2.2 le déclarait « optimiste d'un montant inconnu ».

## Proposition de résolution

Trois volets, indépendants :

1. **Corriger le catalogue** — porter `XAUUSD.spread_pips` à la médiane mesurée
   (52) plutôt qu'à une valeur héritée. À faire pour tous les instruments : la
   même mesure est possible sur chaque cache. Attention : cela **change les
   chiffres de tous les dossiers existants**, qui devront porter la mention
   « mesuré à spread catalogue v1 (optimiste) » ou être rejoués.
2. **Exploiter le spread par barre** — `InstrumentSpec.spread_pips` est scalaire ;
   permettre au moteur de consommer la colonne `spread` des barres quand elle
   existe. C'est la seule façon de mesurer honnêtement une stratégie intraday,
   dont le coût varie du simple au double selon l'heure. Rétrocompatibilité :
   valeur scalaire par défaut, colonne utilisée seulement si demandée.
3. **Exposer un filtre de spread** aux stratégies — `max_spread_pips` existe déjà
   dans `InstrumentSpec` mais compare une constante à une constante, donc ne
   filtre jamais rien. Avec le spread par barre il devient un vrai garde-fou, et
   il correspond à une règle réellement pratiquée par la source étudiée
   (`docs/sources/doudtrading/SYNTHESE_METHODE.md`, étage 7 : *« on doit attendre
   un spread beaucoup plus serré »*).

**Cas particulier `studies/gold_forward/`** : l'étude est scellée, son
`params.json` fige `spread_pips: 25.0` et son hash l'interdit de changer. Le
scellé doit être **respecté** — mais son § 2.2 mérite une note de lecture
signalant que l'écart est maintenant chiffré (×2,1) et non plus inconnu. À
trancher : note de lecture hors scellé, ou rien du tout.

Préférence cc-support : **1 puis 2**, et 3 dans la foulée de 2. Le volet 1 seul
suffit à rendre les chiffres honnêtes ; le volet 2 est ce qui rend l'intraday
mesurable.

## Réponse

<cc-spec>

---
id: TCK-019
from: cc-support
to: Adrian
status: open
blocking: true
created: 2026-09-07
---

## Question

`studies/s13_forward/` est un forward **scellé et en cours** depuis le 16 août 2026, sur
AUDCAD. Il valorise ses trades au spread du catalogue, **3,2 pips**. Le spread réellement
enregistré dans nos barres vaut **6,0 pips** — soit **1,9×** ce que le dispositif compte.

Ce n'est pas un détail de valorisation. Sur AUDCAD, le coût d'un aller-retour représente
**55 % de l'amplitude horaire** (ATR H1 ≈ 11 pips). Sous-estimer le spread d'un facteur
deux sur un instrument aussi serré change la nature du résultat, pas seulement son
ampleur.

Mesure (médiane sur 365 jours, colonne `spread` des caches `C:/db/tradingBot/bars_cache/`) :

| instrument | catalogue | mesuré | écart | coût / ATR H1 |
|---|---:|---:|---:|---:|
| **AUDCAD** | 3,2 | **6,0** | **1,9×** | **55 %** |
| AUDCHF | 2,2 | 4,2 | 1,9× | 61 % |
| CADCHF | 3,4 | 6,3 | 1,9× | 99 % |
| XAUUSD | 25,0 | 90,8 | 3,6× | 4,9 % |

Les paires FX majeures (EURUSD, USDJPY, GBPUSD…) collent au catalogue à 10 % près, ce qui
valide la méthode de conversion et isole ces quatre cas.

## Pourquoi ça remonte à toi et pas à cc-app

Le protocole du scellé prévoit le cas et interdit de le contourner : toute modification
des conventions de valorisation **invalide le test** — redémarrage à zéro, nouveau scellé,
nouveau journal. L'exception unique prévue est « un bug démontré du moteur commun ». Un
spread de catalogue faux n'est pas un bug du moteur : c'est une donnée d'entrée erronée.

Corriger en silence serait la faute que le protocole nomme. Laisser tourner en sachant,
aussi.

## Proposition de résolution

**A — Déclarer l'invalidation et rescellér (recommandée).** Le forward s13 repart à zéro
avec le spread mesuré, nouveau hash, nouveau journal. Coût : trois semaines de mesure
perdues, dont zéro trade clôturé à ce jour (`n_closed_total = 0` au 2026-09-07) — donc
en pratique **on ne perd rien**. C'est la raison principale de recommander A : le
dispositif n'a pas encore produit de donnée à sacrifier.

**B — Laisser courir et annoter.** Le verdict final porterait une réserve « valorisé à
53 % du coût réel ». Défendable pour un instrument à faible coût relatif ; ici le coût
représente 55 % de l'amplitude horaire, donc la réserve viderait le verdict de son sens.

**C — Suspendre s13 en attendant ta décision.** À retenir seulement si tu veux du temps :
chaque jour qui passe ajoute des trades valorisés à un tarif faux.

Reco : **A**, pour la raison ci-dessus — le scellé n'a encore clôturé aucun trade, donc
l'invalidation ne coûte que sa remise en route.

## À vérifier avant de trancher

Le chiffre mesuré vient de la colonne `spread` des barres MT5, qui est une cotation du
courtier et non un coût constaté à l'exécution. Si tu as accès aux conditions réelles de
ton compte (grille tarifaire, ou un relevé d'exécutions), c'est la source qui tranche.
Le même doute vaut pour XAUUSD à 90,8 pips.

## Réponse

<Adrian>

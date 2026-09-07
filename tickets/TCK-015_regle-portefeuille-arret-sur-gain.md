---
id: TCK-015
from: cc-S018
to: cc-spec
status: open
blocking: false
created: 2026-09-06
---

## Question

Deux sources indépendantes décrivent la même règle de **portefeuille**, et nous n'avons
aujourd'hui aucun endroit pour l'exprimer :

- MoneyTalk #30 (Karen Rababian, @ 15:47) — la « carenade » : *tu gagnes ta journée,
  tu arrêtes*. Baptisée ainsi par son mentor après l'avoir vu gagner 1500 $ puis rendre
  100 $ le même jour en se rasseyant devant l'écran.
- MoneyTalk #29 (Doud Trading, @ 12:39) — ne risquer que les bénéfices déjà acquis dans
  la semaine, jamais le capital, et retirer sa mise dès qu'elle est doublée.

Une stratégie ne peut pas porter ça : R2 lui interdit de lire le solde, et R6 lui
interdit l'état caché. C'est structurellement une règle de `core/risk/`. Or
`core/risk/guards.py` sait aujourd'hui dimensionner et couper sur drawdown, mais pas
**arrêter une journée sur un objectif atteint**.

Question subsidiaire, du même bord : `RiskLayer` doit-il connaître la notion de
« journée » (fuseau serveur, week-end, jours fériés) ? Aujourd'hui non.

## Proposition de résolution

Spécifier un garde-fou de session dans `core/risk/`, activable par instance :

- `daily_profit_stop_r` — au-delà de N R gagnés sur la journée, plus d'entrée jusqu'à
  la prochaine session. Les positions ouvertes ne sont pas touchées (elles ont leur
  stop, R3).
- `daily_loss_stop_r` — symétrique, déjà à moitié couvert par le circuit breaker du
  moteur mais au niveau du portefeuille cette fois, pas de la stratégie.
- Journée définie sur le fuseau serveur MT5 (mesuré à GMT+2, cf.
  `core/data/source.calibrate_server_offset`), et **déclarée** dans la config, pas
  devinée.

Ordre de grandeur à trancher par la spec : ces règles sont testables en backtest **si**
le harnais sait rejouer un portefeuille (aujourd'hui `anchored_wf` mesure une stratégie
seule). Sans ce rejeu, la règle serait posée sans preuve — ce que le projet interdit.
Donc soit la spec inclut le rejeu portefeuille, soit elle acte que la règle reste une
consigne d'exploitation non mesurée, et le dit.

Préférence cc-S018 : spécifier la règle **et** son rejeu, ou ne pas la spécifier.
Une règle de risque non mesurée est une superstition avec un nom de variable.

## Réponse

<cc-spec>

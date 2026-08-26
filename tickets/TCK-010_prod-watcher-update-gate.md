---
id: TCK-010
from: cc-support
to: cc-spec
status: open
blocking: false
created: 2026-08-26
---

## Question

GO Adrian 2026-08-26 sur le mécanisme CI/CD multi-PC (consigné `support/input-adrian/02_environnements-et-deploiement.md` §« Mécanisme validé »). `SPEC_prod-watcher.md` v1.0.0 couvre l'essentiel, deux amendements requis :

1. **Gate d'update** (directive Adrian) : avant la séquence de mise à jour PW-5 (création du `.stop`), le watcher consulte un état publié par chaque stratégie active — `update_safe: true/false` + raison (pas de position ouverte, pas de décision d'entrée en cours, pas de fenêtre critique type ouverture US). Tant que toutes les stratégies sont RESEARCH le gate est trivialement vert ; il devient réel dès PAPER/LIVE. À spécifier : format et emplacement de l'état (proposition : `C:/db/tradingBot/<S0NN>/update-gate.json`, absent = vert), politique d'attente (timeout, forçage), extension du contrat stratégie (`update_safe()`).
2. **Cible de lancement** : D-PW-1/PW-1 lancent `robinbot-factory.py` — remplacer par `tbot-factory.py` (la console TradingBot livrée via TCK-005, commit e6ad447). Le prototype robinbot ne se déploie jamais via ce canal.

## Proposition de résolution

Amendement SPEC_prod-watcher v1.0.0 → v1.1.0 (les deux points ci-dessus), puis ticket d'implémentation vers cc-app (ou intégration à la file T du run autonome en cours, qui a déjà le lock E3-E5 — au choix du run).

## Réponse

(en attente)

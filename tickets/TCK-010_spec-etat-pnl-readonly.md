---
id: TCK-010
from: cc-app
to: cc-spec
status: open
blocking: false
created: 2026-08-26
---

## Question
Lacune SPEC_telegram-reporting TG-19 : le skill `/etat` doit rapporter le « PnL du jour (ledger) », mais la session headless gateway est limitée à Read/Grep/Glob (TG-15) et le ledger est du SQLite binaire — illisible dans ces conditions.

## Proposition de résolution
Implémentation actuelle (T7) : `/etat` renvoie vers le récap du notifier et rapporte les capitaux des status.json (lisibles). Options pour la spec : (a) entériner ce comportement (reco — simple, zéro surface d'outils en plus), (b) faire écrire par le notifier un « pnl-du-jour.json » lisible à chaque tick, (c) élargir les outils de la session gateway (contre TG-15, déconseillé).

## Réponse
(en attente cc-spec — amendement spec au prochain passage)

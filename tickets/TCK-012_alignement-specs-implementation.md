---
id: TCK-012
from: cc-support
to: cc-spec
status: open
blocking: false
created: 2026-08-26
---

## Question
Aligner les specs sur l'implémentation livrée (écarts actés en Phase X, revue finale) :
1. SPEC_ci-cd CI-3.4 : commande pytest = `app strategies studies` + option `-o "python_files=test_*.py"` (TCK-008 + finding F1).
2. SPEC_prod-watcher D-PW-3 : « pytest app seul » à reconsidérer à la bascule des études (elles tournent en prod ensuite) ; nommage tbot-prod-watcher ; last_result `gate-blocked`.
3. SPEC_telegram-reporting : digest 22h acté ; exemple TG-5 semaine 35 = 24.08–28.08 (cosmétique) ; TG-19 → cf. TCK-011 (reco a : /etat renvoie au récap).
4. SPEC_backup-github : nom tbot-backup ; allowlist + tbot-panel.txt ; exclusion du dossier d'état du worker ; BK-8 après miroir ; publication délibérée du chat_id (config.json) actée.
5. SPEC_ui-dynamique (directive Adrian 2026-08-26 soir) : (a) les études héritées instanciant une stratégie s'affichent SUR la carte de la stratégie (champ `etudes` de /api/state, remonte `alive` et le niveau PAPER) — /api/services ne garde que les études sans stratégie (s14) ; (b) cartes overview MINIMALES : identité + activité réelle uniquement, instances jamais passées résumées en une ligne, meta dossier·magic supprimée (détail au drill-down) ; (c) UI-9 caduque après migration totale robinbot→tbot du 2026-08-26.

## Proposition de résolution
Un passage cc-spec unique amende les 4 specs (bump versions), clôt TCK-008/TCK-010/TCK-011 en même temps.

## Réponse
(en attente cc-spec)

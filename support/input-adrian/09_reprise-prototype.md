# 09 — Reprise du prototype 9.0.0.x

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Décisions (QA Adrian 2026-08-23)

| # | Décision |
|---|----------|
| D1 | **Socle = G3 RobinBot.** `core/`, `orchestrator/`, `server/`, discipline des études scellées, contrats R1-R10 repris comme fondation. Rebâti : UI dynamique, ledger, broker, CI/CD, nouveau Telegram. |
| D2 | **Les 20 stratégies sont reprises, sans préavis.** Stratégie d'amélioration en lieu et place d'un refus sur préavis. Archivage seulement sur constat de non-pérennité du CC dédié. |
| D3 | **La console 9.0.0.x continue de tourner.** Une fois la nouvelle plateforme prête : bascule ou vie en parallèle quelques jours — décision au moment venu. Journaux scellés migrés intacts. |
| D4 | **Datas de backtest locales**, hors GitHub. GitHub reçoit code, specs, journaux, états. |

## Ce que le prototype apporte (rappel des acquis)

- Factory console + workers + panneau à chaud + codes de sortie 0/2/3/4 + AUTO-OFF.
- Orchestrateur de sessions Claude Code headless (gateway, pilote, portier, mesureur) avec garde-fous mécaniques par hash.
- Backtester pessimiste validé causalité + walk-forward ancré + bras témoin aléatoire.
- Discipline des études scellées ; règles R1-R10 ; registre des magic numbers (`1300NN`).
- Données : porte MT5 unique, harvester de datasets figés, catalogue d'instruments aux spreads mesurés, module COT anti-fuite, FinBERT local, ingestion YouTube.
- Telegram opérationnel (2 bots), méthodologie documentée, ~5 900 lignes de tests.

## Trous connus à combler (nouveaux chantiers)

1. **Broker/exécution** : `core/broker/` est vide — aucun ordre réel n'a jamais été passé. Chaînon manquant vers l'argent réel.
2. **Ledger + fiscalité suisse** : schéma SQL complet, implémentation vide.
3. **Couche de risque globale** : garde-fous codés/testés jamais branchés ; kill switch et politique DD spécifiés jamais construits.
4. **UI dynamique** : le dashboard prototype n'est pas connecté aux résultats réels.
5. **CI/CD + watcher PC prod** : n'existent pas dans le prototype.
6. Dette documentaire : `PROMOTION_POLICY.md` et `registry.py` référencés mais inexistants ; divergence de chemin du panneau entre factory et notifier ; devise mixte USD/CHF dans le catalogue d'instruments.

## Études en vol (ne pas perturber)

`gold_forward`, `s13_forward`, `s14_sentiment` (verdict mi-octobre), `alexg_paper` — elles tournent dans le prototype jusqu'à E6.

## Leçons contraignantes pour toute nouvelle spec

- **« Supervisor = gardien, pas DJ »** : le config-switching adaptatif par régime a été mesuré → il empire les résultats.
- **Avis IA avant un trade** : mesuré → prendre/ne pas prendre uniquement ; jamais de dosage de taille ni d'ajustement de stops ; bras témoin sans conseil en parallèle, à vie.
- **Le spread consomme les petits edges** : l'économie du trade se calcule avant de coder.
- **Objectif financier** : l'objectif historique (20 000 CHF/an sur 4 000) est invalidé par les mesures du prototype ; calibre externe documenté 2-3 %/mois. À re-trancher.

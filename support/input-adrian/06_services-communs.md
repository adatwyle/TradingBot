# 06 — Services communs

*Maintenu par cc-support. Réécrit en place, pas d'historique.*

## Liste des services communs

1. **Application terminal** — trade cycliquement chaque stratégie indépendamment (chapitre 03).
2. **UI web** — visualisation de TradingBot (chapitre 04).
3. **Canal Telegram** — échange quotidiennement avec Adrian sur l'activité du bot (chapitre 07).
4. **Datas de backtest** — datasets figés et datés (parquet), harvester MT5, caches. Locaux (`C:\db\tradingBot\`), hors GitHub.
5. **Backtester** — moteur commun obligatoire (héritage R9), volontairement pessimiste : spread payé intégralement, stop prioritaire intra-barre, validation de causalité mécanique. Aucune stratégie n'écrit son propre backtester.
6. **Données Finnhub** — news pour les études sentiment.
7. **API broker MT5 Swissquote** — porte d'accès unique aux données et (à terme) à l'exécution. État prototype : lecture des barres opérationnelle ; **la couche d'exécution d'ordres n'existe pas encore** — à spécifier et construire (chaînon manquant vers l'argent réel).
8. **cc-support** — session d'interaction avec Adrian (reformulation des inputs).
9. **cc-spec** — spécifications de l'application.
10. **cc-app** — développement des services communs selon spécifications.
11. **Orchestrateur** — fait tourner des Claude Code headless pour développer les tickets et animer les stratégies ; régi par cc-orchestrateur.
12. **Ticketting** — demandes inter-CC et escalade vers cc-support/Adrian (`tickets/`).

## Héritages du prototype à conserver

- Catalogue d'instruments avec spreads réellement mesurés ; module COT CFTC anti-fuite ; témoin FinBERT local ; outils d'ingestion YouTube (transcripts + frames) ; corpus de sources dépouillées.
- Garde-fous de risque (`core/risk/guards.py`, codés et testés — **à brancher**) ; schéma ledger SQLite avec export fiscal suisse (**à implémenter**).
- Discipline des études scellées : hash des paramètres figé avant mesure, journaux chaînés, falsifications déclarées d'avance, bras témoin aléatoire, armement = geste Adrian.

## Services identifiés en plus (proposition cc-support, à confirmer au fil de l'eau)

- **Worker backup GitHub** — pousse cycliquement journaux et états légers vers le repo (le « backup de toutes les datas »).
- **Couche de risque globale** — kill switch, drawdown max, coupe-circuit quotidien (spécifiée dans le prototype, jamais branchée). À traiter comme service commun, pas par stratégie.

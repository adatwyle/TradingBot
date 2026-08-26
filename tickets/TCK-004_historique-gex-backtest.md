---
id: TCK-004
from: cc-S017
to: cc-support
status: open
blocking: false
created: 2026-08-26
---

## Question

Le backtest complet de S017 (H4 — expectancy du système) exige un **historique de cartes GEX intraday/quotidiennes** sur SPY. Aucune source gratuite ne le fournit en profondeur : le CBOE delayed (gratuit, utilisé pour le live/collecte) ne donne que le présent — chaque jour non snapshotté est perdu. Options identifiées, AUCUN compte créé ni paiement engagé :

| Option | Coût | Profondeur | Notes |
|---|---|---|---|
| A. Accumulation snapshots maison (en place depuis 2026-08-26) | 0 $ | grandit de 1 jour/jour | Pipeline `research/daily_snapshot.py` opérationnel ; ~60 jours de données exploitables vers fin octobre 2026 |
| B. FlashAlpha API historique | tier gratuit limité (compte requis) ; tiers payants au-delà | GEX minute SPY depuis 2018 annoncé | Limites exactes du free tier inconnues sans créer de compte |
| C. ITMatrix API (la plateforme de la vidéo) | 119.99 $/mois | live + tout l'historique, 120 req/min | Même méthodologie que la source de la stratégie — comparabilité maximale avec les setups montrés |

## Proposition de résolution

**Préconisation cc-S017 : option A maintenant + décision différée.** Concrètement :

1. Continuer l'accumulation gratuite (option A) + exécuter la Phase A (études H1/H2/H3/H5) sur les données accumulées — 4-6 semaines de mesures.
2. Si et seulement si la Phase A montre un signal (H1 ou H3 non falsifiées avec effet net), demander alors l'arbitrage Adrian entre B (d'abord tester le free tier — création de compte = décision Adrian) et C (119.99 $/mois, résiliable, 1-2 mois suffisent pour extraire l'historique de backtest ≈ 120-240 $ one-shot).
3. Si la Phase A ne montre rien, aucun achat — la stratégie s'oriente vers falsification documentée sans dépense.

Avantage : la dépense n'est engagée qu'avec une preuve de signal préalable ; l'accumulation d'ici là réduit aussi le besoin (échantillon maison gratuit qui grossit). Inconvénient assumé : +4-6 semaines avant un éventuel backtest profond.

## Réponse

(en attente)

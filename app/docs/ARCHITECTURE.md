> **Document de reference G3 (migre tel quel en E2).** Les chemins quil
> cite refletent le layout du PROTOTYPE (code a la racine, etat dans
> C:\db\tbot\). Dans ce depot : le code vit dans app/, letat dans
> C:\db\tradingBot\ (resolution : app/core/paths.py).

# RobinBot — Architecture

**Version** 2.0 — 2026-08-16
**Machine cible** : PC rack 19", Windows, 24/7/365
**Broker unique** : Swissquote MT5
**Dashboard** : navigateur, lisible sur TV et sur PC

---

## Principe fondateur

> Une plateforme qui **héberge** des stratégies, et non un bot qui **est** une
> stratégie.

Chaque stratégie est un module indépendant qui ne connaît ni le compte, ni les
autres stratégies, ni son allocation. Elle répond à une seule question : *long
ou short, où est l'invalidation, où est l'objectif ?*

Tout le reste — taille de position, autorisation de trader, exécution,
comptabilité — appartient à la plateforme. C'est cette séparation qui permet de
changer une allocation ou de bloquer une stratégie **depuis le dashboard, sans
toucher au code**.

---

## Vue d'ensemble

```
                        ┌──────────────────────────┐
                        │   DASHBOARD (navigateur) │
                        │  perf · on/off · capital │
                        └────────────┬─────────────┘
                                     │ HTTP
                        ┌────────────▼─────────────┐
                        │      SERVER (Flask)      │
                        │    API + UI + export     │
                        └────────────┬─────────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │      ORCHESTRATOR        │
                        │  boucle 24/7 · watchdog  │
                        └──┬──────────┬─────────┬──┘
                           │          │         │
                 ┌─────────▼──┐  ┌────▼─────┐  ┌▼──────────┐
                 │ STRATEGY 1 │  │ STRAT. 2 │  │ STRAT. N  │
                 │  (module)  │  │ (module) │  │ (module)  │
                 └─────────┬──┘  └────┬─────┘  └┬──────────┘
                           │  Signal  │         │
                        ┌──▼──────────▼─────────▼──┐
                        │      RISK LAYER          │
                        │ sizing · halt · scaling  │
                        └────────────┬─────────────┘
                                     │ Order
                        ┌────────────▼─────────────┐
                        │   BROKER (Swissquote)    │
                        └────────────┬─────────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │  LEDGER  C:\db\tbot\     │
                        │  trades · fiscal · audit │
                        └──────────────────────────┘
```

---

## Arborescence

```
tbot/
├── core/                        # infrastructure commune — jamais touchée par une stratégie
│   ├── contracts/               # LE contrat : StrategyModule, Signal, règles R1-R10
│   ├── backtest/                # backtester COMMUN (anchored WF, grid search)
│   ├── data/                    # accès MT5, cache, calibration timezone
│   ├── broker/                  # adaptateur Swissquote
│   ├── risk/                    # sizing, circuit breakers, auto-scaling, halt
│   ├── ledger/                  # journal des trades, export fiscal
│   └── validation/              # causalité (R1), conformance (R5)
│
├── strategies/                  # un dossier = une stratégie = un Claude dédié
│   ├── _TEMPLATE/               # gabarit
│   ├── s01_fxalexg_swing/
│   ├── s02_creamer_auction/
│   ├── s10_legacy_meanrev/      # notre S1 historique
│   ├── s11_legacy_breakout/     # notre S2 historique
│   ├── s90_adrian_synthesis/    # la synthèse — nourrie par les verdicts
│   └── s91_claude_scratch/      # conception autonome Claude
│
├── server/                      # Flask + API + dashboard
├── orchestrator/                # boucle live, watchdog, superviseur
├── docs/                        # méthodologie, politique de promotion
├── _archive/                    # travaux antérieurs préservés
└── tools/                       # scaffolding, migration
```

**Base de données** : `C:\db\tbot\tbot.db` — jamais dans l'arborescence code.

---

## Cycle de vie d'une stratégie

```
RESEARCH ──> BACKTESTED ──> PAPER ──> LIVE
                                └──> RETIRED
```

| État | Signification | Condition de passage |
|------|---------------|----------------------|
| `RESEARCH` | Analyse de la source, implémentation | — |
| `BACKTESTED` | R1 + R5 passés, anchored WF exécuté | Checklist `STRATEGY_RULES.md` |
| `PAPER` | Compte démo Swissquote, temps réel | Décision d'Adrian |
| `LIVE` | Argent réel | Décision d'Adrian, après durée minimale en PAPER |
| `RETIRED` | Abandonnée, conservée pour l'historique | — |

**Aucun passage automatique.** Le franchissement de PAPER vers LIVE est une
décision humaine, jamais une conséquence d'un bon backtest.

---

## Couche de risque

Elle seule décide si un signal devient un ordre, et de quelle taille.

**Sizing** — `taille = (capital_alloué × risk_pct) / distance_au_stop`
Le capital alloué vient du dashboard, pas du solde réel. Une stratégie ne peut
donc jamais dépasser son enveloppe.

**Auto-gestion** (mécanisme conservé de Pulse) :

| Déclencheur | Action |
|-------------|--------|
| 3 pertes consécutives | Cooldown 24 barres |
| DD stratégie > 20% | Risque divisé par 2 |
| DD stratégie > 30% | **HALT** de la stratégie seule |
| DD portefeuille > 15% | Risque divisé par 2, toutes stratégies |
| DD portefeuille > 25% | **HALT global** |

Chaque décision est écrite dans `risk_events` — jamais de blocage silencieux.

**Kill switch manuel** : bouton dashboard, ferme tout et bloque.

---

## Reporting fiscal

Le ledger enregistre chaque opération avec son `mode` (BACKTEST / PAPER / LIVE),
et décompose l'argent : **brut, commission, swap, net**. Un net agrégé ne suffit
pas pour une déclaration.

Deux vues SQL : `v_tax_detail` (ligne par trade) et `v_tax_summary` (par année,
mode et stratégie). Export CSV/XLSX depuis le dashboard.

> Ceci produit une piste d'audit, pas un conseil fiscal. En Suisse, la
> qualification (fortune privée vs activité lucrative indépendante) dépend de
> critères factuels — c'est au fiduciaire de trancher sur pièces.

---

## Règles de compatibilité

Résumé — détail dans `core/contracts/STRATEGY_RULES.md`.

| # | Règle |
|---|-------|
| **R1** | **Causalité stricte** — invariant de troncature obligatoire |
| R2 | Séparation stratégie / risque : aucune stratégie ne calcule de taille |
| R3 | Stop loss obligatoire sur tout signal |
| R4 | Magic number unique par stratégie |
| R5 | Cohérence backtest / live vérifiée |
| R6 | Aucun état caché — `on_bar()` est pure |
| R7 | Le manifest est la seule source de vérité |
| R8 | Tout passe par le ledger commun |
| R9 | Backtester commun, jamais réimplémenté |
| R10 | PAPER obligatoire avant LIVE |

---

## Modèle de travail multi-Claude

Chaque stratégie a **son propre Claude Code**, avec son `CLAUDE.md`, confiné à
son dossier. Il ne modifie jamais `core/`.

Sa consigne : **aucun préjugé au départ.** Lire, comprendre, construire le
meilleur cas possible pour la méthode, implémenter, backtester intégralement —
et seulement ensuite juger, sur ses propres chiffres.

Un verdict négatif proprement établi vaut autant qu'un verdict positif. Ce qui
n'a aucune valeur, c'est un avis rendu avant les données.

La **stratégie Adrian** (`s90_adrian_synthesis`) se nourrit des `VERDICT.md` de
toutes les autres : elle assemble ce qui a effectivement résisté au
walk-forward, pas ce qui semblait séduisant.

---

## Déploiement cible

PC rack 19", Windows, 24/7. MT5 + orchestrateur en service. Dashboard servi en
local, consulté depuis la TV ou un autre PC du réseau. Redémarrage automatique
au boot ; l'orchestrateur reconstruit son état depuis le ledger — d'où la règle
R6 (aucun état caché).

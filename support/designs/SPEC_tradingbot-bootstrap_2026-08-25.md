---
name: tradingbot-bootstrap
date: 2026-08-25
version: 1.0.0
type: SPEC
status: draft
author: cc-support (session Claude Code support)
target_scope: projet tradingBot
target_location: C:\projects\tradingBot\
applies_to: [structure projet, acteurs CC, migration prototype, git/github, input-adrian]
---

# SPEC — Bootstrap du projet TradingBot

## 1. Contexte et objectif

Nouveau projet `C:\projects\tradingBot\` succédant au prototype `C:\Datas\Projects\TradingBot_9.0.0.x` (génération G3 « RobinBot », fonctionnelle, actuellement en exploitation). Objectif du bootstrap : mettre en place la structure, les acteurs Claude Code, le corpus `input-adrian`, l'organisation GitHub et le plan de migration — pour que chaque future session CC trouve son contexte prêt.

## 2. Décisions actées (QA Adrian 2026-08-23)

| # | Décision |
|---|----------|
| D1 | **Socle = G3.** `core/`, `orchestrator/`, `server/`, discipline des études scellées et contrats R1-R10 sont repris comme fondation. On rebâtit ce qui est faible : UI dynamique, ledger, broker, CI/CD. |
| D2 | **Reprise des 20 stratégies, sans préavis.** Aucune stratégie n'est écartée sur la base des verdicts existants. Chaque stratégie reçoit son CC dédié qui évalue, tente des chemins d'amélioration, et seul ce CC peut constater la non-pérennité et archiver. Les verdicts du prototype sont des données d'entrée, pas des arrêts de mort. |
| D3 | **Continuité.** La console 9.0.0.x continue de tourner pendant la construction. Une fois la nouvelle plateforme prête : bascule ou vie en parallèle quelques jours — décision au moment venu. Les journaux scellés migrent intacts (chaînage préservé). |
| D4 | **Datas.** GitHub reçoit code, specs, manifests, journaux d'études, états. Les datasets de backtest (parquet/pickle, régénérables) restent en local (`C:\db\tradingBot\`), sauvegardés hors GitHub. |

## 3. Acteurs Claude Code

| Acteur | Dossier de travail | Rôle |
|--------|--------------------|------|
| **cc-support** (cette session, desktop + remote smartphone) | `support/` | Interface Adrian. Reformule les inputs dans `input-adrian/` (chapitres, pas d'historique). Débloque les tickets de clarification : répond seul si évident, sinon QA avec Adrian (Telegram ou start hook), toujours avec préconisation. |
| **cc-spec** | `spec/` | Lit `input-adrian/`, observe les différences, produit et maintient `specification-app/`. Escalade ses clarifications via ticket vers cc-support. |
| **cc-app** | `app/` | Implémente les services communs selon `specification-app/`. |
| **cc-orchestrateur** | `orchestrator-cc/` | Régit l'activité de l'orchestrateur (quelles sessions headless tournent, pour quel besoin). |
| **cc-S0NN** (un par stratégie) | `strategies/S0NN_<slug>/` | Développement, validation, amélioration, mise en prod de SA stratégie. Cloisonné : n'influence aucune autre stratégie, ne touche jamais `app/`. Maintient `spec-strategie.md`. Peut repartir de zéro sur demande d'Adrian. |
| **cc-S0NN-trader** (si la stratégie l'exige) | idem stratégie | Trader IA dédié, créé seulement si nécessaire. Contrainte héritée du prototype (verdict mesuré) : avis limité à prendre/ne pas prendre, jamais de dosage de taille ni d'ajustement de stops, bras témoin sans conseil en parallèle à vie. |

**Principe transversal** : autonomie maximale, remonter uniquement le nécessaire. Un CC décide seul des thématiques évidentes. Le ticketting sert aux vraies questions, pas à la bureaucratie.

**Ticketting inter-CC** : dossier `tickets/` racine, un fichier markdown par ticket (`TCK-NNN_<slug>.md` : demandeur, destinataire, question, statut open/answered/closed). Le start hook de cc-support scanne `tickets/` et traite les bloquants. Pas de Jira (`**Jira project** : NONE — ticketting interne fichiers`).

## 4. Arborescence cible

```
C:\projects\tradingBot\
├── CLAUDE.md                     # vue 360 projet + règles communes à tous les CC
├── README.md
├── .gitignore                    # datasets, caches, secrets exclus
├── .github/workflows/ci.yml     # tests → publication prod
├── support/                      # cc-support
│   ├── CLAUDE.md
│   ├── designs/                  # SPEC de bootstrap (ce fichier)
│   └── input-adrian/             # corpus reformulé (chapitres, cf. §9)
├── spec/                         # cc-spec
│   ├── CLAUDE.md
│   └── specification-app/        # specs établies par cc-spec
├── app/                          # cc-app — services communs (socle G3 migré)
│   ├── CLAUDE.md
│   ├── core/                     # contrats, backtest, data, risk, ledger, validation
│   ├── orchestrator/             # factory console + workers (gateway, notify, pilot…)
│   ├── server/                   # UI web Flask
│   ├── tools/                    # scaffolding, ingestion YouTube
│   └── tests/
├── orchestrator-cc/              # cc-orchestrateur
│   └── CLAUDE.md
├── strategies/                   # cloisonnement total, 1 dossier = 1 stratégie
│   ├── _TEMPLATE/
│   └── S0NN_<slug>/
│       ├── CLAUDE.md             # brief du CC dédié
│       ├── input-adrian.md       # maintenu par cc-support
│       ├── spec-strategie.md     # maintenu par cc-S0NN
│       ├── manifest.yaml         # source unique de vérité (statut, paires, params)
│       ├── strategy.py
│       ├── research/  backtests/  sources/
├── studies/                      # études scellées transverses (sentiment, forwards)
├── tickets/                      # ticketting inter-CC
└── docs/                         # méthodologie, sources dépouillées (migré G3)
```

**DB et état vivant** : `C:\db\tradingBot\` (journaux d'études, status, datasets, caches, secrets) — RULE_db-separation. Un worker `backup` commit/push cycliquement les journaux et états légers vers GitHub (dossier `db-backup/` du repo) : c'est le « backup de toutes les datas » demandé, datasets exclus (D4).

## 5. Numérotation et multi-paires

- Mapping conservé depuis le prototype : `s01`→`S001` … `s16`→`S016`, `s90`→`S090` … `s93`→`S093`. Traçabilité magic numbers (`1300NN`), verdicts et journaux préservée.
- Nouvelles stratégies : prochain numéro libre (`S017`+). `S014` reste réservé (étude sentiment).
- Instance multi-paires : `S0NN.XXX-YYY` (ex. `S013.AUD-CAD`, `S013.EUR-JPY`). Une stratégie déclare ses instances dans son `manifest.yaml` (une entrée par paire, params propres) ; journaux, reporting Telegram et UI raisonnent par instance.

## 6. Git / GitHub / CI-CD

- **Repo unique** : `https://github.com/adatwyle/TradingBot` (existe, vide). Isolation des stratégies par dossier + tests, pas par repo.
- **Branches** : `dev` (travail quotidien, tous les CC) → `main` (production). Promotion vers `main` uniquement via CI verte.
- **CI GitHub Actions** : sur push `dev` → pytest complet (app + toutes stratégies) ; sur PR/merge vers `main` → tests + tag de version. Une modification qui ne passe pas les tests n'atteint jamais `main`.
- **PC prod** : observe cycliquement `main` (`git fetch` + comparaison SHA) et se met à jour si nouvelle version publiée — mécanisme détaillé par cc-spec (redémarrage propre de la console incluse).
- **Versionnement stratégies** : version dans `manifest.yaml` + statut (`RESEARCH | BACKTESTED | PAPER | LIVE | RETIRED`). La prod n'exécute que les instances `PAPER`/`LIVE` présentes sur `main`. Version dev et version prod d'une même stratégie coexistent donc naturellement (dev sur `dev`, prod sur `main`).

## 7. UI de supervision (exigence dynamique)

Faiblesse constatée du prototype : dashboards non connectés aux résultats réels. Exigences pour la nouvelle UI (spec détaillée par cc-spec) :

1. **Découverte dynamique** : une stratégie apparaît dans l'UI dès que son dossier existe. Zéro câblage manuel.
2. **Contrat de données standardisé** : chaque stratégie/instance publie ses données de performance dans un format commun (fichier ou table SQLite — choix technologique laissé à cc-spec, orienté affichage live). La stratégie fournit, l'UI affiche.
3. **Vues** : stratégies en développement / en validation paper / en production ; courbes de gains-pertes par stratégie et par instance.
4. **Drill-down** : clic sur une carte stratégie → page dédiée avec le détail des performances.
5. **Services communs visibles** : état et contenu de chaque service (factory, telegram, données, backtester, orchestrateur, tickets).

## 8. Telegram — nouveau canal TradingBot

Nouveau bot (l'exclusivité `getUpdates` impose des bots dédiés ; le prototype en utilise deux — entrant et sortant — pattern repris). Formats de reporting exigés :

- **Par trade** : `10:53 S001.CHF-USD SL -100chf` / `22:05 S001.CHF-USD TP +210chf`
- **Fin de journée** : liste des trades + summary total gain/perte
- **Fin de semaine** : résumé par jour + total semaine
- **Fin de mois** : résumé par semaine + total mois + rétrospective 12 derniers mois
- **Fin d'année** : résumé de l'année par mois

Canal également utilisé par cc-support pour les QA de clarification directes avec Adrian (toujours avec préconisation).

## 9. Corpus input-adrian (chapitres)

Fichiers dans `support/input-adrian/`, maintenus exclusivement par cc-support, réécrits en place (pas d'historique — git porte la traçabilité) :

| Fichier | Contenu |
|---------|---------|
| `01_vision-et-principes.md` | Vision, autonomie, anti-bureaucratie, simplicité |
| `02_environnements-et-deploiement.md` | PC dev, PC prod, CI/CD, GitHub, bat de lancement |
| `03_application-console.md` | Terminal console, cycle de vie, factory |
| `04_ui-supervision.md` | Exigences UI (§7) |
| `05_strategies-cycle-de-vie.md` | Sources (YouTube/Adrian), analyse sans préavis, cloisonnement, numérotation, multi-paires, amélioration vs refus, archivage |
| `06_services-communs.md` | Backtester, datas, Finnhub, MT5 Swissquote, risk, ledger |
| `07_telegram-reporting.md` | Formats §8 |
| `08_acteurs-claude-code.md` | Rôles §3, ticketting, escalade |
| `09_reprise-prototype.md` | Décisions D1-D4, continuité, ce qui est repris/rebâti |

Par stratégie : `strategies/S0NN_<slug>/input-adrian.md` (résumé de la stratégie, source, attentes d'Adrian, historique de verdict du prototype comme donnée d'entrée).

## 10. Plan de migration (phases d'exécution)

| Phase | Contenu | Exécutant |
|-------|---------|-----------|
| **E1** | Structure + CLAUDE.md racine/acteurs + corpus `input-adrian/` + git init + push initial (`dev`+`main`) | cc-support (cette session) |
| **E2** | Migration socle G3 → `app/` (core, orchestrator, server, tools, tests) avec tests verts | cc-app (session dédiée, brief préparé par E1) |
| **E3** | Migration des 20 stratégies → `strategies/S0NN_*/` + `input-adrian.md` par stratégie | cc-support (structure) puis cc-S0NN (contenu) |
| **E4** | CI GitHub Actions + mécanisme watcher PC prod | cc-app selon spec cc-spec |
| **E5** | UI dynamique + ledger + nouveau canal Telegram | cc-app selon spec cc-spec |
| **E6** | Migration journaux scellés + bascule/parallèle console (décision Adrian au moment venu) | cc-support + Adrian |
| **E7** | Lancement des CC stratégies (évaluation, amélioration, avancement vers paper) | cc-orchestrateur |

La console 9.0.0.x n'est **jamais** touchée avant E6.

## 11. Critères de succès du bootstrap (E1)

- [ ] Arborescence §4 créée, CLAUDE.md racine + 1 CLAUDE.md par acteur
- [ ] 9 chapitres `input-adrian/` écrits et fidèles aux inputs d'Adrian
- [ ] Repo git initialisé, remote `adatwyle/TradingBot`, branches `dev`+`main` poussées
- [ ] `.gitignore` excluant datasets/caches/secrets
- [ ] Template stratégie + 20 dossiers `S0NN_*` avec `input-adrian.md` chacun
- [ ] Résumé des 20 stratégies livré à Adrian
- [ ] Prototype 9.0.0.x intact et toujours en exploitation

## 12. Hors scope de ce bootstrap

- Le code des services communs (cc-app, phases E2+)
- Les spécifications détaillées (cc-spec : UI, watcher prod, ledger, broker, Telegram)
- La couche broker/exécution réelle (trou connu du prototype — à spécifier par cc-spec)
- La politique de risque et l'objectif financier (à re-trancher avec Adrian, chapitre dédié quand il l'apportera)

## 13. Points ouverts (non bloquants pour E1)

1. **PC prod** : machine, OS, MT5 installé ? — nécessaire pour E4.
2. **Bots Telegram** : création des nouveaux bots (geste Adrian : tokens).
3. **Politique de risque globale** (kill switch, DD max, étages de déploiement 1-5 CHF) : le prototype a une base solide, à confirmer chapitre par chapitre.
4. **Bascule console** : décision au moment venu (D3).

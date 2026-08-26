# SPEC — UI de supervision dynamique

**Version** : 1.0.0 — 2026-08-26 · **Auteur** : cc-spec · **Statut** : prête pour implémentation
**Sources** : input-adrian 04 (exigences 1-6), 03, 09 (trou n°4) ; PLAN T6 ; héritage
`app/server/app.py` (confrontation déclaré/réel, niveaux, lecture seule), `app/core/paths.py`.
**Implémente** : refonte `app/server/` (app.py + `ui/` propre, la maquette héritée
`ui/dashboard.html` et son injection regex sont supprimées).

## 1. Objectif

Corriger la faiblesse du prototype (dashboards non connectés) : une UI servie par le
serveur Flask de la console, alimentée en **live** par un contrat de données standardisé,
avec découverte automatique des stratégies, drill-down par stratégie, et vue des
services communs.

## 2. Décisions tranchées

| # | Décision | Motivation (1 ligne) |
|---|----------|----------------------|
| D-UI-1 | Contrat de perf = **`status.json` par instance** sous `C:\db\tradingBot\<S0NN>\<instance>\` écrit par la stratégie, **agrégé par le serveur au moment de servir**, complété par le ledger pour l'historique | Reproduit exactement le motif éprouvé des études (état dans les fichiers, tick tué inoffensif, lisible à l'œil), garde le serveur en lecture seule, et le ledger — déjà obligatoire pour tout trade — fournit les agrégats historiques sans duplication. |
| D-UI-2 | Front = **HTML + JS vanilla sans build step ni CDN**, polling `fetch` sur l'API JSON | Fonctionne hors-ligne sur le PC prod, zéro dépendance, zéro toolchain ; htmx n'apporte rien ici car tout est du polling read-only. |
| D-UI-3 | Courbes = SVG généré côté client (polyline sur les points d'equity) | Une courbe de tendance n'exige pas une lib de charting ; un SVG de 30 lignes suffit et reste sans dépendance. |
| D-UI-4 | Le niveau (dev/paper/prod) vient du `status:` du manifest (R7) **confronté au réel** (instance vivante = status.json frais) — mécanisme hérité conservé, divergences affichées | Leçon payée du prototype : un manifest qui ment doit s'afficher comme divergence, jamais dormir. |
| D-UI-5 | Identité d'instance : `S0NN.XXX-YYY` (paires) ou `S0NN.<SYMBOL>` (mono-instrument) ; les instances sont déclarées dans `manifest.yaml` | Le chapitre 05 impose le raisonnement par instance partout (journaux, UI, Telegram) ; un id d'instance existe donc toujours, même mono-paire. |

## 3. Contrat de données de perf (source de vérité de l'affichage)

### 3.1 `status.json` par instance — écrit par la stratégie, jamais par le serveur

Chemin : `db_dir()/<S0NN>/<instance>/status.json` (ex.
`C:\db\tradingBot\S013\S013.AUD-CAD\status.json`). Écriture atomique (tmp + `os.replace`),
à chaque tick de l'instance. Schéma exact (schema 1) :

```json
{
  "schema": 1,
  "instance": "S013.AUD-CAD",
  "strategy": "S013",
  "mode": "BACKTEST | PAPER | LIVE",
  "generated_at_utc": "2026-08-26T14:00:03Z",
  "last_bar_time": "2026-08-26T13:00:00Z",
  "n_closed_total": 42,
  "cum_r": 3.75,
  "pnl_chf": 812.50,
  "capital": 4812.50,
  "open_position": {
    "side": "LONG | SHORT",
    "entry_price": 0.0,
    "stop_price": 0.0,
    "target_price": 0.0,
    "opened_at_utc": "…Z",
    "volume_lots": 0.0
  },
  "error": null
}
```

Règles : `open_position` vaut `null` sans position ; `error` porte un libellé court si le
dernier tick a échoué ; tout champ supplémentaire est toléré et ignoré par le serveur
(extensibilité) ; un fichier absent = instance jamais passée (état légitime, pas une erreur).

### 3.2 Compléments serveur (au moment de servir)

- **Manifest** (`strategies/S0NN_*/manifest.yaml`) : `display_name`, `magic_number`,
  `status:` (R7 — source unique du niveau), liste des instances.
- **Ledger** (SPEC_ledger) : trades clos, agrégats jour/semaine/mois/année, courbe
  d'equity (`equity_snapshots`, repli : cumul des `net_pnl` des trades clos par instance).
- **Fraîcheur** : une instance est « vivante » si `generated_at_utc` < 24 h ;
  au-delà elle s'affiche avec la mention « dernier passage » en alerte douce.

## 4. Exigences

### Découverte et vues

- **UI-1** — Découverte dynamique : le serveur scanne `project_root()/strategies/` à
  **chaque requête** (pas de cache au démarrage). Un nouveau dossier `S0NN_*` avec
  `manifest.yaml` apparaît immédiatement ; dossiers `_*` ignorés ; manifest illisible ⇒
  carte affichée en état « manifest invalide » (jamais silencieusement absente).
- **UI-2** — Vue d'ensemble `/` : trois niveaux empilés PRODUCTION (LIVE) / PAPER /
  DEV (RESEARCH, BACKTESTED), déclaré-vs-réel avec bloc DIVERGENCES (D-UI-4), section
  RETIRED repliée. Prod vide affiche le texte hérité « aucune stratégie armée… (R10) ».
- **UI-3** — Chaque carte stratégie de la vue d'ensemble : id + nom, statut manifest,
  par instance : trades clos, R cumulé, PnL CHF, position ouverte (badge), dernier
  passage, **sparkline** de la courbe de gains/pertes (D-UI-3).
- **UI-4** — Drill-down `/strategy/<S0NN>` : page dédiée — manifest complet, tableau par
  instance (métriques §3.1), courbe d'equity par instance et cumulée, agrégats ledger
  (jour/semaine/mois/année), 50 derniers trades clos (ledger), erreurs récentes.
- **UI-5** — Vue services communs `/services` :
  - **factory** : vivante si mtime du lock < `LOCK_STALE_SEC` ; derniers résultats par
    worker (parse du tail de `app/orchestrator/logs/factory.log`, 200 dernières lignes) ;
    contenu du panneau (on/off/cadence, lignes AUTO-OFF en rouge) ;
  - **telegram** : notifier et gateway — token présent (booléen, jamais la valeur),
    `state.json` (curseurs, n_served), dernier envoi ;
  - **datas** : datasets présents sous `db_dir()` (nom, taille, date) ;
  - **backup** : `db_dir()/backup/status.json` (SPEC_backup-github) ;
  - **watcher prod** : `db_dir()/watcher/status.json` (SPEC_prod-watcher) — section
    affichée seulement si le fichier existe ;
  - **tickets** : liste de `tickets/TCK-*.md` (front-matter : id, from, to, status,
    blocking), bloquants ouverts en tête et en rouge.
- **UI-6** — Un bandeau global horodaté « données réelles · <timestamp> » + version
  applicative (fichier `VERSION` via `core.version.read_version()`).

### API JSON (consommée par le front, utilisable par le gateway)

- **UI-7** — Routes Flask, toutes GET, lecture seule stricte (aucune route d'écriture,
  aucun ordre — héritage non négociable) :
  - `/api/state` : `{generated, version, niveaux:{prod,paper,dev,retired,divergences}, strategies:[…cartes §UI-3…]}` ;
  - `/api/strategy/<S0NN>` : détail §UI-4 (404 JSON si dossier inconnu) ;
  - `/api/services` : détail §UI-5 ;
  - `/api/equity/<S0NN>/<instance>` : `[[iso_utc, equity], …]` (source ledger, repli §3.2).
- **UI-8** — Le front (`app/server/ui/`) : `index.html`, `strategy.html`, `services.html`
  + un seul `app.js` et `style.css` (sombre, monospace — continuité console). Polling
  `fetch` toutes les 5 s (10 s sur `/services`), indicateur visuel si l'API ne répond plus.
- **UI-9** — La maquette héritée `dashboard.html` et l'injection regex `STRATS/LEDGER`
  sont **supprimées** ; `build_niveaux()` (confrontation déclaré/réel) est conservé et
  adapté au contrat §3 ; les panneaux d'études scellées héritées (gold_forward, s13,
  macd_ai, s14) restent visibles dans `/services` tant que E6 n'est pas fait.
- **UI-10** — Serveur : `127.0.0.1:8742` inchangé (worker `supervision` de la factory,
  nature service) ; chemins via `core.paths` exclusivement ; seams testables
  (`TBOT_PROJECT_ROOT`, `TBOT_DB_DIR`).

## 5. Tests attendus (cc-app)

- **UI-T1** — Layout jetable (tmp_path) : un dossier stratégie ajouté entre deux requêtes
  apparaît dans `/api/state` (découverte à la requête).
- **UI-T2** — status.json valide/absent/corrompu → carte respectivement vivante /
  « jamais passée » / « status illisible » (jamais d'exception 500).
- **UI-T3** — Divergences : manifest PAPER sans instance vivante, et l'inverse.
- **UI-T4** — `/api/strategy/<id>` : agrégats cohérents avec un ledger de fixtures.
- **UI-T5** — `/api/services` : tickets bloquants détectés, token présent sans fuite de
  la valeur, factory vivante/morte selon mtime du lock.

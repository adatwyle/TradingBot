# SPEC — Ledger (core/ledger sur schema.sql)

**Version** : 1.0.0 — 2026-08-26 · **Auteur** : cc-spec · **Statut** : prête pour implémentation
**Sources** : input-adrian 06 (héritages : schéma ledger + export fiscal suisse à implémenter),
09 (trou n°2) ; PLAN T5 ; héritage `app/core/ledger/schema.sql` (tables trades,
strategy_state, risk_events, equity_snapshots, backtest_runs, vues v_tax_*).
**Implémente** : `app/core/ledger/ledger.py` (+ `__init__.py` exportant l'API).

## 1. Objectif

Source unique de vérité des résultats : **aucune stratégie n'écrit ses propres agrégats**
— tout trade (BACKTEST, PAPER, LIVE) atterrit dans le ledger, qui sert le dashboard,
Telegram et le fisc. SQLite WAL, `C:\db\tradingBot\tradingbot.db`.

## 2. Décisions tranchées

| # | Décision | Motivation (1 ligne) |
|---|----------|----------------------|
| D-LG-1 | Chemin DB : `db_dir()/tradingbot.db` (défaut `C:\db\tradingBot\tradingbot.db`), seam `TBOT_LEDGER_DB` | L'en-tête du schema.sql pointe le path du prototype (`C:\db\tbot\tbot.db`, interdit) ; résolution via core.paths, RULE_db-separation. |
| D-LG-2 | Migration v2 : colonne `instance_id TEXT` ajoutée à `trades` et `equity_snapshots` (`ALTER TABLE … ADD COLUMN`) | Les agrégats exigés raisonnent par instance `S0NN.XXX-YYY` ; le schéma hérité ne connaît que strategy_id+symbol, l'instance devient première classe. |
| D-LG-3 | `strategy_id` = id court canonique `S0NN` (ex. `S013`), `instance_id` = `S0NN.XXX-YYY` | La nouvelle numérotation (chapitre 05) prime sur les slugs prototype (`s02_…`) ; l'id court est stable même si le slug du dossier change. |
| D-LG-4 | Mécanisme de migration : `PRAGMA user_version` + liste ordonnée `MIGRATIONS` (v1 = schema.sql intégral, v2 = colonnes instance_id + index) appliquée à l'ouverture | Douce et idempotente : le schema.sql est déjà tout en `CREATE IF NOT EXISTS`, user_version évite de re-parser l'état ; une DB existante monte de version sans perte. |
| D-LG-5 | API = classe `Ledger` (connexion tenue) + fonctions module de commodité ; horodatages ISO 8601 **UTC** suffixe `Z` | Une classe permet transactions courtes et tests par injection de path ; l'UTC en base, la conversion locale au bord (Telegram/UI), comme les études. |
| D-LG-6 | Semaine = **semaine ISO** (lundi-dimanche, `strftime('%G-%W')` calculé côté Python) | Les résumés hebdo Telegram parlent le calendrier d'Adrian ; l'ISO est la convention déjà utilisée par le digest hérité. |

## 3. Exigences

### Ouverture et schéma

- **LG-1** — `Ledger(db_path: Path | None = None)` : résout `TBOT_LEDGER_DB` puis
  `db_dir()/"tradingbot.db"` ; crée le dossier parent si absent ; ouvre sqlite3 avec
  `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, `PRAGMA foreign_keys=ON`.
- **LG-2** — À l'ouverture : lit `PRAGMA user_version` ; applique dans l'ordre chaque
  migration de version supérieure, chacune dans une transaction, puis
  `PRAGMA user_version = N`. v1 = exécution de `schema.sql` (lu depuis le paquet) ;
  v2 = D-LG-2 (+ index `idx_trades_instance ON trades(instance_id, mode)` et
  `idx_equity_instance ON equity_snapshots(instance_id, mode, timestamp)`).
- **LG-3** — `mode` est validé à l'écriture : valeur ∈ {`BACKTEST`, `PAPER`, `LIVE`}
  sinon `ValueError`. Aucun défaut silencieux.

### API d'écriture

- **LG-4** — `open_trade(*, strategy_id, instance_id, strategy_version, magic_number, mode,
  symbol, timeframe, side, volume_lots, open_time, open_price, stop_price,
  target_price=None, run_id=None, ticket=None, signal_reason=None, confidence=None,
  risk_distance=None, risk_amount=None, account_balance=None, meta: dict | None = None)
  -> int` (id de ligne). `stop_price` obligatoire et non nul (R3 : jamais de trade sans stop).
- **LG-5** — `close_trade(trade_id, *, close_time, close_price, exit_reason,
  gross_pnl, commission=0.0, swap=0.0) -> None` : calcule et stocke
  `net_pnl = gross_pnl - commission - swap` (décomposition fiscale — le net seul ne
  suffit pas) ; `exit_reason` ∈ {`SL`,`TP`,`TRAIL`,`MANUAL`,`HALT`,`EOD`} ; refuse un
  trade déjà clos (`ValueError`).
- **LG-6** — `record_trade(**champs) -> int` : insertion d'un trade **déjà clos** en un
  appel (chemin backtest/bulk) — mêmes validations que LG-4 + LG-5.
- **LG-7** — `record_equity_snapshot(*, strategy_id, instance_id, mode, equity,
  open_pnl=0.0, drawdown_pct=None, timestamp=None) -> None` (timestamp défaut : maintenant UTC).
- **LG-8** — `record_risk_event(*, event_type, trigger, strategy_id=None,
  value_before=None, value_after=None, detail: dict | None = None) -> None` ;
  `event_type` ∈ {`HALT`,`RESUME`,`SCALE_UP`,`SCALE_DOWN`,`COOLDOWN`,`DD_BREACH`,`KILL_SWITCH`}.
- **LG-9** — Toute écriture est une transaction courte auto-commit (`with conn:`) ;
  jamais de transaction tenue entre deux appels (WAL, plusieurs ticks écrivains).

### API de lecture / agrégation

- **LG-10** — `closed_trades(*, strategy_id=None, instance_id=None, mode=None,
  date_from=None, date_to=None, limit=None) -> list[dict]` — trades clos triés par
  `close_time`, tous champs.
- **LG-11** — Agrégats, tous filtrables par `strategy_id`, `instance_id`, `mode`
  (dates en date locale du poste, conversion depuis l'UTC en base — le reporting parle
  le calendrier du lecteur) :
  - `pnl_by_day(date_from, date_to)` → `[{day:"YYYY-MM-DD", n_trades, gross, commission, swap, net}, …]` ;
  - `pnl_by_week(...)` → idem avec `week:"YYYY-Www"` (ISO, D-LG-6) ;
  - `pnl_by_month(...)` → idem avec `month:"YYYY-MM"` ;
  - `pnl_by_year(...)` → idem avec `year:"YYYY"` ;
  - `day_trades(day)` → lignes du jour prêtes pour Telegram : `[{close_time_local:"HH:MM",
    instance_id, exit_reason, net_pnl}, …]` triées chronologiquement.
- **LG-12** — `equity_curve(*, strategy_id, instance_id=None, mode=None, limit=2000)
  -> list[tuple[iso_utc, equity]]` (consommée par l'UI, UI-7).
- **LG-13** — `tax_detail(year)` et `tax_summary(year)` : simple SELECT des vues
  existantes `v_tax_detail` / `v_tax_summary` filtrées sur l'année — les vues du
  schéma hérité ne sont **pas** réécrites.
- **LG-14** — Devise : `currency` défaut `'CHF'` (schéma) ; les agrégats LG-11 groupent
  par devise si plusieurs devises coexistent et le signalent — jamais d'addition
  inter-devises silencieuse.

### Intégration

- **LG-15** — Consommateurs : UI (SPEC_ui-dynamique §3.2), Telegram (SPEC_telegram-reporting §3),
  stratégies (via leur runner commun) et backtester. Aucun module n'ouvre le fichier
  SQLite directement : tout passe par cette API.
- **LG-16** — La table `strategy_state` est créée par le schéma mais son pilotage
  (enabled/halted/auto_scaling) reste **hors scope** de cette spec — il appartient à la
  future couche de risque globale (TCK-006, décisions Adrian).

## 4. Tests attendus (cc-app)

- **LG-T1** — DB neuve dans tmp_path : user_version passe 0→2, tables + colonnes
  `instance_id` présentes ; réouverture = idempotente.
- **LG-T2** — DB « v1 » préexistante (schema.sql seul) : migration v2 sans perte des
  lignes existantes.
- **LG-T3** — open/close : net = gross - commission - swap ; stop obligatoire ;
  double close refusé ; mode invalide refusé.
- **LG-T4** — Agrégats jour/semaine ISO/mois/année sur un jeu de trades UTC à cheval sur
  minuit locale (le trade de 23:30 UTC compte le bon jour local).
- **LG-T5** — `day_trades` produit l'ordre et les champs attendus par le format Telegram.
- **LG-T6** — Vues fiscales : v_tax_summary cohérente avec les trades insérés.

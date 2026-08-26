-- ============================================================================
-- TBOT LEDGER — source unique de vérité pour le dashboard ET le fisc
-- Emplacement : C:\db\tbot\tbot.db   (règle : la DB ne vit jamais dans le code)
-- ============================================================================
--
-- Principe : AUCUNE stratégie n'écrit ses propres résultats. Tout trade —
-- backtest, paper ou live — atterrit ici avec son strategy_id et son mode.
-- Le dashboard agrège depuis cette table ; l'export fiscal la lit telle quelle.
--
-- Conséquence : on peut à tout moment répondre à « qu'a fait la stratégie X
-- entre telle et telle date, et combien ça a coûté ou rapporté ».

PRAGMA journal_mode = WAL;

-- ─────────────────────────────────────────────────────────────────────────────
-- TRADES — le grain le plus fin. Une ligne = une position ouverte puis fermée.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trades (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Attribution
    strategy_id       TEXT    NOT NULL,   -- ex: "s02_creamer_auction"
    strategy_version  TEXT    NOT NULL,
    magic_number      INTEGER NOT NULL,   -- isolation MT5
    mode              TEXT    NOT NULL,   -- BACKTEST | PAPER | LIVE
    run_id            TEXT,               -- regroupe un backtest / une session live

    -- Instrument
    symbol            TEXT    NOT NULL,   -- symbole broker (#US500, EURUSD…)
    timeframe         TEXT    NOT NULL,

    -- Exécution
    ticket            INTEGER,            -- ticket MT5 (NULL en backtest)
    side              TEXT    NOT NULL,   -- LONG | SHORT
    volume_lots       REAL    NOT NULL,
    open_time         TEXT    NOT NULL,   -- ISO 8601 UTC
    open_price        REAL    NOT NULL,
    close_time        TEXT,               -- NULL = encore ouverte
    close_price       REAL,
    stop_price        REAL    NOT NULL,   -- R3 : jamais NULL
    target_price      REAL,
    exit_reason       TEXT,               -- SL | TP | TRAIL | MANUAL | HALT | EOD

    -- Argent — décomposé pour le fisc (le net seul ne suffit pas)
    gross_pnl         REAL,               -- P&L brut, devise du compte
    commission        REAL DEFAULT 0.0,
    swap              REAL DEFAULT 0.0,   -- rollover overnight
    net_pnl           REAL,               -- gross - commission - swap
    currency          TEXT NOT NULL DEFAULT 'CHF',

    -- Contexte au moment de l'entrée (audit + analyse post-mortem)
    signal_reason     TEXT,               -- lisible : pourquoi ce trade
    confidence        REAL,
    risk_distance     REAL,               -- |entry - stop| en unités de prix
    risk_amount       REAL,               -- montant risqué décidé par core/risk
    account_balance   REAL,               -- solde AVANT le trade
    meta_json         TEXT,               -- payload libre de la stratégie

    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_strategy   ON trades(strategy_id, mode);
CREATE INDEX IF NOT EXISTS idx_trades_close_time ON trades(close_time);
CREATE INDEX IF NOT EXISTS idx_trades_mode_year  ON trades(mode, substr(close_time,1,4));
CREATE INDEX IF NOT EXISTS idx_trades_run        ON trades(run_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- STRATEGY_STATE — piloté par le dashboard, lu par l'orchestrateur
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strategy_state (
    strategy_id       TEXT PRIMARY KEY,
    enabled           INTEGER NOT NULL DEFAULT 0,   -- interrupteur du dashboard
    mode              TEXT    NOT NULL DEFAULT 'BACKTEST',
    allocated_capital REAL    NOT NULL DEFAULT 0.0, -- CHF alloués par Adrian
    risk_pct          REAL    NOT NULL DEFAULT 0.01,-- % du capital alloué / trade
    max_positions     INTEGER NOT NULL DEFAULT 1,

    -- Auto-gestion (mécanisme conservé depuis Pulse)
    auto_scaling      INTEGER NOT NULL DEFAULT 1,   -- ajuste le risque selon la perf
    halted            INTEGER NOT NULL DEFAULT 0,   -- blocage automatique
    halt_reason       TEXT,
    halted_at         TEXT,

    consecutive_losses INTEGER NOT NULL DEFAULT 0,
    cooldown_until     TEXT,

    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- RISK_EVENTS — trace de toute décision automatique du superviseur
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT NOT NULL DEFAULT (datetime('now')),
    strategy_id   TEXT,                  -- NULL = événement global
    event_type    TEXT NOT NULL,         -- HALT | RESUME | SCALE_UP | SCALE_DOWN
                                         -- | COOLDOWN | DD_BREACH | KILL_SWITCH
    trigger       TEXT NOT NULL,         -- règle déclenchée, en clair
    value_before  REAL,
    value_after   REAL,
    detail_json   TEXT
);

CREATE INDEX IF NOT EXISTS idx_risk_events_time ON risk_events(timestamp);

-- ─────────────────────────────────────────────────────────────────────────────
-- EQUITY_SNAPSHOTS — courbe d'equity par stratégie, pour le dashboard
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS equity_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT NOT NULL,
    strategy_id   TEXT NOT NULL,
    mode          TEXT NOT NULL,
    equity        REAL NOT NULL,
    open_pnl      REAL DEFAULT 0.0,
    drawdown_pct  REAL
);

CREATE INDEX IF NOT EXISTS idx_equity ON equity_snapshots(strategy_id, mode, timestamp);

-- ─────────────────────────────────────────────────────────────────────────────
-- BACKTEST_RUNS — traçabilité de la recherche
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id        TEXT PRIMARY KEY,
    strategy_id   TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    git_commit    TEXT,                  -- reproductibilité
    params_json   TEXT NOT NULL,
    data_from     TEXT,
    data_to       TEXT,
    n_trades      INTEGER,
    net_pnl       REAL,
    max_dd_pct    REAL,
    win_rate      REAL,
    profit_factor REAL,
    causality_ok  INTEGER,               -- R1 : invariant de troncature passé ?
    conformance_ok INTEGER,              -- R5 : backtest == live ?
    notes         TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- VUE FISCALE — un an, un mode, tout le détail
-- Les plus-values privées sont en principe exonérées en Suisse, mais le statut
-- de quasi-professionnel se juge sur des critères factuels. On produit donc le
-- détail complet et on laisse le fiduciaire qualifier. Ce n'est pas un conseil
-- fiscal : c'est une piste d'audit.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE VIEW IF NOT EXISTS v_tax_detail AS
SELECT
    substr(close_time, 1, 4)              AS tax_year,
    strategy_id,
    mode,
    symbol,
    side,
    open_time,
    close_time,
    volume_lots,
    open_price,
    close_price,
    gross_pnl,
    commission,
    swap,
    net_pnl,
    currency,
    exit_reason,
    ticket
FROM trades
WHERE close_time IS NOT NULL
ORDER BY close_time;

CREATE VIEW IF NOT EXISTS v_tax_summary AS
SELECT
    substr(close_time, 1, 4)                        AS tax_year,
    mode,
    strategy_id,
    currency,
    COUNT(*)                                        AS n_trades,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)    AS n_wins,
    SUM(CASE WHEN net_pnl <= 0 THEN 1 ELSE 0 END)   AS n_losses,
    ROUND(SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END), 2) AS gains,
    ROUND(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END), 2) AS losses,
    ROUND(SUM(commission), 2)                       AS total_commission,
    ROUND(SUM(swap), 2)                             AS total_swap,
    ROUND(SUM(net_pnl), 2)                          AS net_result
FROM trades
WHERE close_time IS NOT NULL
GROUP BY tax_year, mode, strategy_id, currency;

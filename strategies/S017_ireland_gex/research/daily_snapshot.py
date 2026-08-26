"""S017 ireland_gex — daily pre-market data snapshot pipeline.

Collects into C:/db/tradingBot/S017/ (RULE db-separation):
  raw/    CBOE delayed SPY options chain (json.gz)
  gex/    computed GEX map per strike (csv) + one-line summary appended to SPY_gex_summary.csv
  ohlcv/  SPY 5min + daily bars (yfinance, incremental merge)

Run once per trading day, ideally pre-market US (~15:00 Swiss time).
Re-running the same day creates an intraday snapshot (suffix _HHMM) without
touching the day's canonical premarket files.

Usage:  python daily_snapshot.py [--db-dir PATH] [--intraday]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import gex_calc

DB_DIR = Path("C:/db/tradingBot/S017")


def snapshot_chain_and_gex(db_dir: Path, intraday: bool) -> gex_calc.GexMap:
    today = datetime.now().strftime("%Y-%m-%d")
    suffix = f"_{datetime.now().strftime('%H%M')}" if intraday else ""

    chain = gex_calc.fetch_chain("SPY")
    raw_path = db_dir / "raw" / f"SPY_chain_{today}{suffix}.json.gz"
    gex_calc.save_chain(chain, raw_path)

    m = gex_calc.compute_map(chain)
    gex_path = db_dir / "gex" / f"SPY_gex_{today}{suffix}.csv"
    gex_path.parent.mkdir(parents=True, exist_ok=True)
    out = m.per_strike.copy()
    majors = set(m.major_levels["strike"]) if len(m.major_levels) else set()
    out["is_major"] = out["strike"].isin(majors)
    out.insert(0, "asof", m.asof)
    out.insert(1, "spot", m.spot)
    out.to_csv(gex_path, index=False)

    # summary line (one per snapshot)
    top = m.major_levels.nlargest(3, "abs_gex") if len(m.major_levels) else pd.DataFrame()
    summary = {
        "date": today,
        "snapshot": "intraday" + suffix if intraday else "premarket",
        "asof": m.asof,
        "spot": m.spot,
        "net_gex_musd": round(m.net_gex / 1e6, 1),
        "regime": m.regime,
        "flip": m.flip,
        "major_levels": ";".join(f"{r.strike:.0f}({r.level_sign[0]}{r.gex/1e6:+.0f}M)"
                                 for r in top.itertuples()) if len(top) else "",
    }
    sum_path = db_dir / "gex" / "SPY_gex_summary.csv"
    row = pd.DataFrame([summary])
    if sum_path.exists():
        row.to_csv(sum_path, mode="a", header=False, index=False)
    else:
        row.to_csv(sum_path, index=False)

    print(f"[chain] {raw_path.name}: {len(chain['data']['options'])} options")
    print(f"[gex]   {gex_path.name}: {len(out)} strikes, "
          f"net {m.net_gex/1e6:,.0f} M$/1% ({m.regime}), flip ~{m.flip}")
    if len(m.major_levels):
        lv = ", ".join(f"{r.strike:.0f} ({r.level_sign} {r.gex/1e6:+.0f}M)"
                       for r in m.major_levels.itertuples())
        print(f"[levels] {lv}")
    return m


def snapshot_ohlcv(db_dir: Path) -> None:
    import yfinance as yf

    ohlcv_dir = db_dir / "ohlcv"
    ohlcv_dir.mkdir(parents=True, exist_ok=True)
    jobs = [("5m", "60d", "SPY_5min.csv"), ("1d", "10y", "SPY_daily.csv")]
    for interval, period, fname in jobs:
        df = yf.Ticker("SPY").history(period=period, interval=interval, auto_adjust=False)
        if df.empty:
            print(f"[ohlcv] WARNING: yfinance returned empty for {interval}")
            continue
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        df.columns = [c.lower() for c in df.columns]
        df.index.name = "timestamp"
        path = ohlcv_dir / fname
        if path.exists():  # incremental merge — accumulate beyond the 60d yfinance window
            old = pd.read_csv(path, index_col=0, parse_dates=True)
            df = pd.concat([old, df])
            df = df[~df.index.duplicated(keep="last")].sort_index()
        df.to_csv(path)
        print(f"[ohlcv] {fname}: {len(df)} bars ({df.index[0]} .. {df.index[-1]})")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db-dir", default=str(DB_DIR))
    p.add_argument("--intraday", action="store_true",
                   help="extra same-day snapshot (suffixed _HHMM)")
    args = p.parse_args()
    db_dir = Path(args.db_dir)

    m = snapshot_chain_and_gex(db_dir, args.intraday)
    snapshot_ohlcv(db_dir)
    print()
    print(gex_calc.format_map(m, around_pct=1.5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
s12 — Test STRUCTUREL longue durée sur LONGHIST (SP500 1927-2026, Nasdaq
1971-2026), close-only.

Adaptation DÉCLARÉE (gel, dégradation n°5) : o=h=l=c sur tout l'historique ->
range de closes, ATR = moyenne de |Δclose|, cible = close de la veille,
exécution au close, spread nul. Ce test répond à UNE question : le signal
sélectionne-t-il des jours meilleurs que la moyenne (F3) — pas « est-ce
exécutable » (ça, c'est le dossier MT5).

Comparaisons imposées par le gel :
  * buy & hold du même échantillon
  * « toujours investi SAUF les jours où la stratégie est en position »
    (complément — décompose le B&H en jours-signal vs autres jours)

Usage : python strategies/s12_prt_macd_meanrev/backtests/run_longhist.py
Sortie : backtests/longhist.txt
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.backtest.engine import InstrumentSpec, run as run_engine  # noqa: E402
from strategies.S012_prt_macd_meanrev.strategy import Strategy       # noqa: E402

HERE = os.path.dirname(__file__)
DATA = r"C:\db\tbot\datasets\LONGHIST"
ENGINE_KWARGS = dict(cooldown_bars=0, cb_losses=999)
TRADING_DAYS = 252

DATASETS = {
    "SP500_1927": "SP500_IDX_D1.parquet",
    "NASDAQ_1971": "NASDAQ_COMP_D1.parquet",
}
ERAS = [("1928-01-01", "1950-01-01"), ("1950-01-01", "1980-01-01"),
        ("1980-01-01", "2000-01-01"), ("2000-01-01", "2022-06-01"),
        ("2022-06-01", "2027-01-01")]


def spec_for(name: str) -> InstrumentSpec:
    return InstrumentSpec(symbol=name, pip=1.0, spread_pips=0.0,
                          max_spread_pips=1.0)


def run_slice(bars: pd.DataFrame, name: str):
    strat = Strategy()
    params = dict(strat.manifest().default_params)
    data = strat.precompute(bars, params)
    sigs = strat.generate_signals(data, params, len(bars))
    return run_engine(sigs, bars, spec_for(name), **ENGINE_KWARGS)


def line(res, bars) -> str:
    if not res.n_trades:
        return "0 trade"
    pct = [100.0 * (t.exit_price - t.entry_price) / t.entry_price for t in res.trades]
    return (f"{res.n_trades:>4} trades | {res.total_r:>+8.2f} R "
            f"| {res.total_r / res.n_trades:>+8.4f} R/trade "
            f"| {np.mean(pct):>+7.3f} %/trade | WR {res.win_rate:>5.1f} % "
            f"| pire trade {min(pct):>+7.2f} %")


def day_selection(res, bars) -> list[str]:
    """F3 — rendement annualisé des jours EN position vs B&H vs complément."""
    close = bars["close"]
    rets = close.pct_change().fillna(0.0)
    pos_idx = {ts: i for i, ts in enumerate(bars.index)}
    in_pos = np.zeros(len(bars), dtype=bool)
    for t in res.trades:
        i = pos_idx.get(pd.Timestamp(t.entry_time))
        j = pos_idx.get(pd.Timestamp(t.exit_time)) if t.exit_time is not None else None
        if i is None or j is None:
            continue
        in_pos[i + 1:j + 1] = True     # exposition du close d'entrée au close de sortie

    def ann(mask) -> tuple[float, int]:
        r = rets.to_numpy()[mask]
        if len(r) < 30:
            return float("nan"), int(mask.sum())
        return 100.0 * (float(np.prod(1 + r)) ** (TRADING_DAYS / len(r)) - 1.0), len(r)

    all_mask = np.ones(len(bars), dtype=bool)
    a_bh, n_bh = ann(all_mask)
    a_in, n_in = ann(in_pos)
    a_out, n_out = ann(~in_pos)
    verdict = ("BAT la moyenne des jours" if a_in > a_bh
               else "NE BAT PAS la moyenne des jours (F3 déclenchée)")
    return [
        f"  B&H (tous les jours)            : {a_bh:>+8.2f} %/an  ({n_bh} jours)",
        f"  jours EN position (stratégie)   : {a_in:>+8.2f} %/an  ({n_in} jours, "
        f"{100.0 * n_in / n_bh:.1f} % du temps)",
        f"  toujours investi SAUF ces jours : {a_out:>+8.2f} %/an  ({n_out} jours)",
        f"  => {verdict}",
    ]


def main() -> None:
    L: list[str] = []
    for name, fn in DATASETS.items():
        bars = pd.read_parquet(os.path.join(DATA, fn))
        bars = bars[(bars[["open", "high", "low", "close"]] > 0).all(axis=1)]
        L.append("=" * 96)
        L.append(f"LONGHIST — {name} : {len(bars)} barres "
                 f"({bars.index[0].date()} -> {bars.index[-1].date()}) — "
                 f"close-only, spread nul, config par défaut")
        L.append("=" * 96)

        res = run_slice(bars, name)
        L.append(f"PLEIN ÉCHANTILLON : {line(res, bars)}")
        h = pd.Series([t.bars_held for t in res.trades])
        L.append(f"  détention : méd {h.median():.0f} j, p90 {h.quantile(.9):.0f} j, "
                 f"max {h.max():.0f} j")
        worst = sorted(res.trades, key=lambda t: t.pnl_r)[:3]
        for t in worst:
            L.append(f"  pire : entrée {t.entry_time.date()} sortie "
                     f"{t.exit_time.date() if t.exit_time else '—'} "
                     f"{100 * (t.exit_price - t.entry_price) / t.entry_price:+.1f} % "
                     f"({t.bars_held} j, {t.exit_reason})")
        L.append("")
        L.append("F3 — sélection de jours (le test qui compte pour un long-only) :")
        L.extend(day_selection(res, bars))
        L.append("")

        L.append("PAR ÉPOQUE (precompute par tranche, warmup rejoué) :")
        for a, b in ERAS:
            sl = bars[(bars.index >= a) & (bars.index < b)]
            if len(sl) < 300:
                continue
            r = run_slice(sl, name)
            L.append(f"  {a[:7]} -> {b[:7]} : {line(r, sl) if r.n_trades else '0 trade'}")
        L.append("")

    txt = "\n".join(L)
    out = os.path.join(HERE, "longhist.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    sys.stdout.buffer.write((txt + f"\n-> {out}\n").encode("utf-8", "replace"))


if __name__ == "__main__":
    main()

"""S017 ireland_gex — GEX map computation from a CBOE delayed options chain.

Methodology: Perfiliev "naive" dealer positioning assumption
(dealers are long the calls sold by the public, short the puts):

    GEX_call(K) = +gamma * OI * 100 * S^2 * 0.01     [$ per 1% spot move]
    GEX_put(K)  = -gamma * OI * 100 * S^2 * 0.01

Reference reading: github.com/Matteo-Ferrara/gex-tracker (code below is original).
Spec: spec-strategie.md §3.1-3.3. Params: manifest.yaml.
"""
from __future__ import annotations

import gzip
import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol}.json"
OPTION_RE = re.compile(r"^(?P<root>[A-Z]+)(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})(?P<cp>[CP])(?P<strike>\d{8})$")

# Defaults frozen in manifest.yaml (§3.2)
LEVEL_MAJOR_FRAC = 0.50
LEVEL_TOP_K = 5
LEVEL_UNIVERSE_PCT = 2.0


def fetch_chain(symbol: str = "SPY", timeout: int = 60) -> dict:
    """Download the full delayed options chain JSON from CBOE (free, no key)."""
    req = urllib.request.Request(
        CBOE_URL.format(symbol=symbol), headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def save_chain(chain: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(chain, f)


def load_chain(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def parse_options(chain: dict) -> tuple[pd.DataFrame, float]:
    """Flatten the CBOE chain into a DataFrame (one row per option) + spot price."""
    data = chain["data"]
    spot = float(data["current_price"])
    rows = []
    for o in data["options"]:
        m = OPTION_RE.match(o["option"])
        if not m:
            continue
        rows.append(
            {
                "expiry": date(2000 + int(m["yy"]), int(m["mm"]), int(m["dd"])),
                "type": m["cp"],
                "strike": int(m["strike"]) / 1000.0,
                "gamma": float(o.get("gamma") or 0.0),
                "open_interest": float(o.get("open_interest") or 0.0),
                "volume": float(o.get("volume") or 0.0),
                "iv": float(o.get("iv") or 0.0),
            }
        )
    return pd.DataFrame(rows), spot


def gex_by_strike(
    options: pd.DataFrame,
    spot: float,
    expiry_window_days: int | None = None,
    asof: date | None = None,
) -> pd.DataFrame:
    """Aggregate signed dollar-gamma exposure per strike.

    expiry_window_days: keep only expiries within N calendar days (None = all).
    Returns columns: strike, gex_call, gex_put, gex (net, $ per 1% move), volume.
    """
    df = options.copy()
    asof = asof or date.today()
    df = df[df["expiry"] >= asof]
    if expiry_window_days is not None:
        df = df[(df["expiry"] - asof).apply(lambda d: d.days) <= expiry_window_days]

    contract_gex = df["gamma"] * df["open_interest"] * 100.0 * spot**2 * 0.01
    df = df.assign(contract_gex=contract_gex)
    df.loc[df["type"] == "P", "contract_gex"] *= -1.0

    g = (
        df.pivot_table(
            index="strike",
            columns="type",
            values="contract_gex",
            aggfunc="sum",
            fill_value=0.0,
        )
        .rename(columns={"C": "gex_call", "P": "gex_put"})
        .reset_index()
    )
    for col in ("gex_call", "gex_put"):
        if col not in g:
            g[col] = 0.0
    g["gex"] = g["gex_call"] + g["gex_put"]
    vol = df.groupby("strike")["volume"].sum().rename("opt_volume")
    return g.merge(vol, on="strike", how="left").sort_values("strike").reset_index(drop=True)


@dataclass
class GexMap:
    asof: str
    spot: float
    net_gex: float                  # sum of signed GEX ($/1% move)
    regime: str                     # "positive" | "negative"  (regime_mode: net)
    flip: float | None              # zero-crossing strike of cumulative profile
    per_strike: pd.DataFrame        # full map
    major_levels: pd.DataFrame = field(default_factory=pd.DataFrame)  # spec §3.2


def compute_map(
    chain: dict,
    expiry_window_days: int | None = None,
    level_major_frac: float = LEVEL_MAJOR_FRAC,
    level_top_k: int = LEVEL_TOP_K,
    level_universe_pct: float = LEVEL_UNIVERSE_PCT,
) -> GexMap:
    options, spot = parse_options(chain)
    g = gex_by_strike(options, spot, expiry_window_days)

    net = float(g["gex"].sum())
    regime = "positive" if net > 0 else "negative"

    # Gamma flip: strike where the cumulative (low->high strike) profile crosses zero.
    cum = g["gex"].cumsum()
    flip = None
    sign_change = (cum.shift(1) < 0) & (cum >= 0) | (cum.shift(1) > 0) & (cum <= 0)
    idx = g.index[sign_change.fillna(False)]
    if len(idx):
        # closest crossing to spot
        candidates = g.loc[idx, "strike"]
        flip = float(candidates.iloc[(candidates - spot).abs().argmin()])

    # Major levels (spec §3.2): |GEX| >= frac * max|GEX| AND top-k AND within universe pct of spot
    uni = g[(g["strike"] - spot).abs() <= spot * level_universe_pct / 100.0].copy()
    if len(uni):
        uni["abs_gex"] = uni["gex"].abs()
        max_abs = uni["abs_gex"].max()
        majors = (
            uni[uni["abs_gex"] >= level_major_frac * max_abs]
            .nlargest(level_top_k, "abs_gex")
            .sort_values("strike")
            .reset_index(drop=True)
        )
        majors["level_sign"] = majors["gex"].apply(lambda x: "positive" if x > 0 else "negative")
    else:
        majors = pd.DataFrame()

    asof = chain.get("timestamp") or datetime.now().isoformat(timespec="seconds")
    return GexMap(
        asof=str(asof), spot=spot, net_gex=net, regime=regime,
        flip=flip, per_strike=g, major_levels=majors,
    )


def format_map(m: GexMap, around_pct: float = 2.0) -> str:
    """Human-readable console rendering of the map near the spot."""
    lines = [
        f"GEX map asof {m.asof} | spot {m.spot:.2f} | "
        f"net {m.net_gex/1e6:,.0f} M$/1% ({m.regime}) | flip ~{m.flip}",
        f"{'strike':>8} {'GEX (M$/1%)':>14}  bar",
    ]
    g = m.per_strike
    win = g[(g["strike"] - m.spot).abs() <= m.spot * around_pct / 100.0]
    if not len(win):
        return "\n".join(lines)
    scale = win["gex"].abs().max() or 1.0
    majors = set(m.major_levels["strike"]) if len(m.major_levels) else set()
    for _, r in win.iloc[::-1].iterrows():  # high strikes on top, like ITMatrix
        bar = "#" * int(round(abs(r["gex"]) / scale * 40))
        sign = "+" if r["gex"] > 0 else "-"
        tag = " <== MAJOR" if r["strike"] in majors else ""
        spot_tag = " <spot>" if abs(r["strike"] - m.spot) < 0.5 else ""
        lines.append(f"{r['strike']:>8.0f} {r['gex']/1e6:>+14.1f}  {sign}{bar}{tag}{spot_tag}")
    return "\n".join(lines)

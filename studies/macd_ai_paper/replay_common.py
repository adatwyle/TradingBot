"""
REJEU À L'AVEUGLE ACCÉLÉRÉ — matière commune (datasets, candidats, outcomes)
=============================================================================

Partagé par `replay_extract.py` (génération des dossiers anonymisés) et
`replay_measure.py` (mesure IA vs prendre-tout vs aléatoire). Une seule
implémentation de la marche d'outcome — celle des conventions du moteur
commun (`paper_step.check_exit`) — pour que le rejeu mesure exactement ce que
le runner temps réel exécuterait.

FLUX DE CANDIDATS (déclaré au protocole)
-----------------------------------------
    MT5 D1 (exécutable, coûts réels)   : SP500, NASDAQ, DAX — 2016 -> 2026
    LONGHIST close-only (structurel)   : SP500 1927->2015, NASDAQ 1971->2015
                                         (coupés à 2016 pour ne PAS recouvrir
                                         les flux MT5 — pas de doublon)

Cellule = la cellule SCELLÉE de params.json (close_down = true, sl_atr = 3).
LONGHIST est close-only (o=h=l=c) : range et ATR y dégénèrent en fonctions du
close — dégradation déclarée (même posture que s12/run_longhist.py).
"""
from __future__ import annotations

import os
import sys
from typing import Optional

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core.data.source import load_bars                          # noqa: E402
from core.paths import db_dir                                   # noqa: E402
from strategies.S012_prt_macd_meanrev.strategy import Strategy  # noqa: E402
from studies.macd_ai_paper.paper_step import (                  # noqa: E402
    check_exit, edge_cost_of,
)

# Migration tbot : datasets figés sous C:\db\tradingBot\datasets\LONGHIST —
# le seam TBOT_DB_DIR reste honoré via core.paths.db_dir().
LONGHIST_DIR = os.path.join(str(db_dir()), "datasets", "LONGHIST")

# Les datasets du flux — noms opaques côté juge, réels côté mapping.
DATASETS = {
    "SP500":        {"kind": "mt5", "symbol": "SP500"},
    "NASDAQ":       {"kind": "mt5", "symbol": "NASDAQ"},
    "DAX":          {"kind": "mt5", "symbol": "DAX"},
    "SP500_1927":   {"kind": "longhist", "file": "SP500_IDX_D1.parquet",
                     "until": "2016-01-01"},
    "NASDAQ_1971":  {"kind": "longhist", "file": "NASDAQ_COMP_D1.parquet",
                     "until": "2016-01-01"},
}

# Spec de valorisation par dataset. LONGHIST : spread nul (structurel, comme
# s12/run_longhist.py) — le R net et le R sans coût y coïncident.
def spec_for(ds_name: str, params: dict) -> dict:
    ds = DATASETS[ds_name]
    if ds["kind"] == "mt5":
        return dict(params["specs"][ds["symbol"]])
    return {"symbol": ds_name, "pip": 1.0, "spread_pips": 0.0,
            "max_spread_pips": 1.0, "pip_value_per_lot": 1.0,
            "slippage_pips": 0.0}


def load_dataset(ds_name: str) -> Optional[pd.DataFrame]:
    ds = DATASETS[ds_name]
    if ds["kind"] == "mt5":
        df = load_bars(ds["symbol"], "D1", max_age_hours=10**9)
        return df
    path = os.path.join(LONGHIST_DIR, ds["file"])
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    if "time" in df.columns:
        df = df.set_index("time")
    df.index = pd.to_datetime(df.index)
    df = df[df.index < pd.Timestamp(ds["until"])]
    for col in ("open", "high", "low"):
        if col not in df.columns:
            df[col] = df["close"]
    return df


def gen_candidates(df: pd.DataFrame, cell: dict, symbol: str) -> list:
    """Les signaux de la cellule scellée, via le code s12 (R5 — pas de
    deuxième implémentation)."""
    s = Strategy()
    s._symbol = symbol
    p = dict(s.manifest().default_params)
    p.update(cell)
    pre = s.precompute(df, p)
    sigs = s.generate_signals(pre, p, len(df))
    idx_of = {ts: i for i, ts in enumerate(df.index)}
    out = []
    for sig in sigs:
        i = idx_of[pd.Timestamp(sig.timestamp)]
        out.append({"bar": i, "time": pd.Timestamp(sig.timestamp).isoformat(),
                    "entry": float(sig.entry), "stop": float(sig.stop),
                    "target": (float(sig.target)
                               if sig.target is not None else None),
                    "meta": dict(sig.meta or {})})
    return out


def walk_outcome(df: pd.DataFrame, bar: int, entry: float, stop: float,
                 target: Optional[float], spec: dict, *,
                 sl_adjust: float = 1.0, tp_adjust: float = 1.0) -> Optional[dict]:
    """Outcome INDÉPENDANT d'un candidat aux conventions du moteur commun
    (entrée au close + coût, stop unilatéral gap payé, SL prime, coût en
    sortie). `sl_adjust`/`tp_adjust` resserrent les distances depuis l'entrée
    exécutée (mêmes formules que paper_step._open_position). None si la
    position ne clôt jamais avant la fin des données (exclu de la mesure —
    déclaré)."""
    cost = edge_cost_of(spec)
    entry_exec = entry + cost                       # long-only (s12)
    stop_eff = entry_exec - (entry_exec - stop) * float(sl_adjust)
    target_eff = None
    if target is not None:
        target_eff = entry_exec + (target - entry_exec) * float(tp_adjust)
    risk_distance = entry_exec - stop_eff
    if risk_distance <= 0:
        return None
    pos = {"side": "LONG", "entry_price": entry_exec,
           "stop_price": stop_eff, "target_price": target_eff,
           "risk_distance": risk_distance}
    for j in range(bar + 1, len(df)):
        ex = check_exit(pos, df.iloc[j])
        if ex is None:
            continue
        exit_price, reason = ex
        gross = exit_price - entry_exec
        net = gross - cost
        return {"exit_bar": j, "exit_reason": reason,
                "bars_held": j - bar,
                "pnl_r": net / risk_distance,
                "pnl_r_nocost": (gross + 2 * cost) / risk_distance}
    return None

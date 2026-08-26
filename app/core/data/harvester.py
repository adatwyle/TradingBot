"""
MOISSONNEUR D'HISTORIQUE — extraction par tranches, réassemblage local
=======================================================================

POURQUOI CE MODULE EXISTE
--------------------------
MT5 refuse les grosses requêtes sur les bas timeframes :

    copy_rates_from_pos(EURUSD, M5, 0, 100000)   -> rien
    copy_rates_from_pos(EURUSD, M5, 0, 5000)     -> 23 jours seulement

Mais il accepte des **plages datées explicites**, mois par mois :

    copy_rates_range(EURUSD, M5, 2025-06-01, 2025-07-01)  -> 6016 barres

Profondeur réellement atteignable, mesurée le 16.08.2026 :

    H1  : 5,1 ans
    M5  : ~14 mois   (limite entre 2024-06 et 2025-06)
    M1  : mois courant seulement

Ce module marche à reculons mois par mois, stocke chaque tranche, et les
réassemble en un dataset continu.

DATASETS FIGÉS — la seconde raison d'être
------------------------------------------
Jusqu'ici chaque backtest retéléchargeait depuis MT5, donc la fenêtre glissait
et **la recherche n'était pas reproductible**. Relancer le même test un mois
plus tard donnait d'autres chiffres.

C'est ce glissement qui, en juillet, a fait office de forward-test involontaire
et révélé que 4 de nos 5 paires validées ne tenaient plus. Découverte utile,
mais par accident.

Désormais : un dataset figé et daté pour la recherche, un rafraîchissement
**délibéré** pour un forward-test. Plus jamais les deux confondus.

STOCKAGE
--------
    C:\\db\\tbot\\datasets\\<SYMBOLE>\\<TF>\\<AAAA-MM>.parquet

Parquet : compressé, typé, relu instantanément. Ordre de grandeur — M5 sur
20 instruments et 5 ans ≈ 600 Mo. Seul le tick justifierait un disque dédié.

USAGE
-----
    python -m core.data.harvester --symbols EURUSD SP500 --tf M5 --months 18
    python -m core.data.harvester --coverage
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.data.source import broker_symbol  # noqa: E402

DATASETS = os.path.join(os.environ.get("TBOT_DB_DIR", r"C:\db\tbot"), "datasets")

# Une tranche est considérée vide si elle contient moins que ça. MT5 renvoie
# parfois 1 barre isolée au lieu d'un tableau vide quand l'historique manque.
MIN_BARS = 20


def _tf_const(tf: str):
    import MetaTrader5 as mt5
    table = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    if tf not in table:
        raise ValueError(f"timeframe inconnu : {tf}")
    return table[tf]


def _slice_path(symbol: str, tf: str, year: int, month: int) -> str:
    safe = symbol.replace("#", "").replace("/", "")
    d = os.path.join(DATASETS, safe, tf)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{year:04d}-{month:02d}.parquet")


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end


def _months_backward(n: int) -> list[tuple[int, int]]:
    """n derniers mois, du plus récent au plus ancien."""
    out, cur = [], datetime.now().replace(day=1)
    for _ in range(n):
        out.append((cur.year, cur.month))
        cur = (cur - timedelta(days=1)).replace(day=1)
    return out


def harvest(symbols: list[str], tf: str, months: int,
            refresh_current: bool = True, verbose: bool = True) -> dict:
    """Moissonne mois par mois, en reculant. Idempotent : une tranche déjà
    stockée n'est pas retéléchargée (sauf le mois courant, encore incomplet).

    S'arrête sur un symbole après 2 mois vides consécutifs — c'est la limite de
    profondeur du serveur, insister ne sert à rien.
    """
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise RuntimeError("MT5 : initialisation impossible")

    tf_const = _tf_const(tf)
    now = datetime.now()
    stats: dict[str, dict] = {}

    try:
        for name in symbols:
            sym = broker_symbol(name)
            if mt5.symbol_info(sym) is None:
                if verbose:
                    print(f"[{name}] symbole introuvable ({sym})")
                continue

            got = cached = empty_streak = 0
            first_month = last_month = None

            for (y, m) in _months_backward(months):
                path = _slice_path(name, tf, y, m)
                is_current = (y == now.year and m == now.month)

                if os.path.exists(path) and not (is_current and refresh_current):
                    cached += 1
                    last_month = last_month or f"{y}-{m:02d}"
                    first_month = f"{y}-{m:02d}"
                    empty_streak = 0
                    continue

                a, b = _month_bounds(y, m)
                rates = mt5.copy_rates_range(sym, tf_const, a, min(b, now))

                if rates is None or len(rates) < MIN_BARS:
                    empty_streak += 1
                    if verbose:
                        print(f"[{name}] {y}-{m:02d} vide")
                    if empty_streak >= 2:
                        if verbose:
                            print(f"[{name}] limite de profondeur atteinte à {y}-{m:02d}")
                        break
                    continue

                empty_streak = 0
                df = pd.DataFrame(rates)
                df["time"] = pd.to_datetime(df["time"], unit="s")
                df = df.set_index("time")
                keep = [c for c in ("open", "high", "low", "close",
                                    "tick_volume", "spread") if c in df.columns]
                df[keep].to_parquet(path, compression="snappy")

                got += 1
                last_month = last_month or f"{y}-{m:02d}"
                first_month = f"{y}-{m:02d}"
                if verbose:
                    print(f"[{name}] {y}-{m:02d} : {len(df):>6} barres -> {os.path.basename(path)}")

            stats[name] = {"downloaded": got, "cached": cached,
                           "from": first_month, "to": last_month}
    finally:
        mt5.shutdown()

    return stats


def load_dataset(symbol: str, tf: str,
                 start: Optional[str] = None,
                 end: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Réassemble les tranches en un DataFrame continu.

    C'est ici qu'on obtient un dataset FIGÉ : il ne dépend que de ce qui est
    sur le disque, donc deux exécutions à six mois d'écart donnent le même
    résultat. C'est la condition d'une recherche reproductible.
    """
    safe = symbol.replace("#", "").replace("/", "")
    d = os.path.join(DATASETS, safe, tf)
    if not os.path.isdir(d):
        return None

    files = sorted(f for f in os.listdir(d) if f.endswith(".parquet"))
    if start:
        files = [f for f in files if f[:7] >= start[:7]]
    if end:
        files = [f for f in files if f[:7] <= end[:7]]
    if not files:
        return None

    parts = [pd.read_parquet(os.path.join(d, f)) for f in files]
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated(keep="last")]   # chevauchements de bordure
    if start:
        df = df[df.index >= start]
    if end:
        df = df[df.index <= end]
    return df


def coverage() -> pd.DataFrame:
    """Ce qu'on possède réellement en local, par instrument et timeframe."""
    rows = []
    if not os.path.isdir(DATASETS):
        return pd.DataFrame(rows)
    for sym in sorted(os.listdir(DATASETS)):
        sdir = os.path.join(DATASETS, sym)
        if not os.path.isdir(sdir):
            continue
        for tf in sorted(os.listdir(sdir)):
            tdir = os.path.join(sdir, tf)
            files = sorted(f for f in os.listdir(tdir) if f.endswith(".parquet"))
            if not files:
                continue
            size_mb = sum(os.path.getsize(os.path.join(tdir, f)) for f in files) / 1e6
            bars = sum(len(pd.read_parquet(os.path.join(tdir, f))) for f in files)
            rows.append({
                "symbole": sym, "tf": tf, "mois": len(files),
                "de": files[0][:7], "à": files[-1][:7],
                "barres": bars, "Mo": round(size_mb, 1),
            })
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Moissonneur d'historique MT5")
    ap.add_argument("--symbols", nargs="+", default=["EURUSD"])
    ap.add_argument("--tf", default="M5")
    ap.add_argument("--months", type=int, default=18)
    ap.add_argument("--coverage", action="store_true", help="affiche l'existant et sort")
    a = ap.parse_args()

    if a.coverage:
        cov = coverage()
        if cov.empty:
            print("Aucun dataset local. Lancer une moisson d'abord.")
        else:
            print(cov.to_string(index=False))
            print(f"\nTotal : {cov['Mo'].sum():.1f} Mo, {int(cov['barres'].sum()):,} barres")
            print(f"Emplacement : {DATASETS}")
        return 0

    print(f"Moisson {a.tf} sur {a.months} mois — {', '.join(a.symbols)}")
    print(f"Destination : {DATASETS}\n")
    stats = harvest(a.symbols, a.tf, a.months)

    print("\n" + "=" * 62)
    for sym, s in stats.items():
        print(f"  {sym:>10} : {s['downloaded']:>3} téléchargés, {s['cached']:>3} en cache"
              f"   {s['from']} -> {s['to']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

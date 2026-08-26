"""
Session Range Breakout — stratégie s09_balke_rangebreakout

Source : René Balke (BM Trading), https://www.youtube.com/@ReneBalke
Reconstruction : docs/sources/renebalke/ (SYNTHESE.md + .mq5 tutoriel).

Mécanisme (version H1, dégradations déclarées dans research/ANALYSIS.md §4) :
  - range = high/low des barres H1 dont l'heure est dans [range_start_hour,
    range_end_hour) — identique au range M1 de la source si les bornes tombent
    sur des heures pleines (mêmes extrêmes de prix) ;
  - première barre H1 après la fin du range (heure < last_entry_hour) dont le
    CLOSE sort du range -> signal dans le sens de la cassure, entrée au close
    (substitut du stop order intrabar, entrée retardée déclarée) ;
  - SL : autre côté du range (sl_mode='range') ou 1 % (sl_mode='pct_entry' /
    'pct_range' — l'ambiguïté de la base du 1 % chez l'auteur devient deux
    cellules de grille) ;
  - PAS de take profit (target=None) — la sortie est l'heure : clôture 18h
    approximée par engine_kwargs['max_hold_bars'] (transmis par le harnais) ;
  - breakouts=2 : après la première cassure, un close au-delà du bord OPPOSÉ
    émet un second signal (trade de retournement, transcript 04). Le moteur
    (position unique) ne l'exécute que si la première position est fermée —
    ce qui est la sémantique de la source, son SL étant précisément ce bord ;
  - filtre optionnel de taille de range en % du prix médian du range.

R1 : precompute() renvoie un DataFrame — la couche indicateur est réellement
inspectée par le gardien (leçon s91 §2.9 : un dict y échappe en silence).
"""
from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    StrategyModule, StrategyManifest, Signal, Side, MarketContext,
)


class Strategy(StrategyModule):
    STRATEGY_ID = "s09_balke_rangebreakout"
    MAGIC_NUMBER = 130009

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Session Range Breakout",
            version="0.1.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s09_balke_rangebreakout",
            source="https://www.youtube.com/@ReneBalke",
            symbols=["USDJPY", "XAUUSD", "GBPUSD", "EURJPY"],
            timeframe="H1",
            warmup_bars=0,
            # Grille FIGÉE dans research/FALSIFICATION.md avant tout backtest.
            # Les fenêtres par instrument sont restreintes dans les scripts de
            # backtest (ses réglages tradés, pas un balayage).
            param_grid={
                "range_start_hour": [3, 4],
                "range_end_hour": [5, 6, 11, 12],
                "sl_mode": ["range", "pct_entry", "pct_range"],
                "breakouts": [1, 2],
                "range_filter_pct": [None, (0.2, 0.4), (0.15, 0.85)],
            },
            default_params={
                # sa config USDJPY phare (transcript 03)
                "range_start_hour": 3,
                "range_end_hour": 6,
                "last_entry_hour": 17,   # ordres supprimés à 18h chez lui
                "sl_mode": "range",
                "sl_pct": 1.0,
                "breakouts": 1,
                "range_filter_pct": None,
            },
            status="RESEARCH",
            notes="Reproduction Balke — sortie 18h via engine_kwargs[max_hold_bars].",
        )

    # ── Backtest path ────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        """Range du jour, disponible à partir de la fin de fenêtre. Causal :
        la valeur à la barre i n'utilise que des barres du même jour d'heure
        strictement inférieure à range_end_hour <= heure(i)."""
        h0 = int(params["range_start_hour"])
        h1 = int(params["range_end_hour"])

        out = pd.DataFrame(index=df.index)
        out["close"] = df["close"]
        out["hour"] = df.index.hour
        day = df.index.normalize()
        out["day"] = day

        in_win = (out["hour"] >= h0) & (out["hour"] < h1)
        # cummax/cummin PAR JOUR sur la fenêtre : à toute barre i, la valeur ne
        # dépend que des barres <= i (causal par construction).
        hi = df["high"].where(in_win)
        lo = df["low"].where(in_win)
        g = day
        out["range_high"] = hi.groupby(g).cummax().groupby(g).ffill()
        out["range_low"] = lo.groupby(g).cummin().groupby(g).ffill()
        out["win_bars"] = in_win.groupby(g).cumsum()
        # range complet = toutes les barres de la fenêtre présentes (jours
        # fériés/week-end tronqués exclus, comme un jour sans données M1)
        out["range_ok"] = (out["win_bars"] == (h1 - h0)) & (out["hour"] >= h1)
        return out

    def _signals_for_day(self, day_df: pd.DataFrame, params: dict,
                         symbol: str) -> list[Signal]:
        h1 = int(params["range_end_hour"])
        last_h = int(params.get("last_entry_hour", 17))
        sl_mode = params["sl_mode"]
        sl_pct = float(params.get("sl_pct", 1.0)) / 100.0
        n_max = int(params["breakouts"])
        filt = params.get("range_filter_pct")

        sub = day_df[(day_df["hour"] >= h1) & (day_df["hour"] <= last_h)
                     & day_df["range_ok"]]
        if sub.empty:
            return []
        rh = float(sub["range_high"].iloc[0])
        rl = float(sub["range_low"].iloc[0])
        if not (np.isfinite(rh) and np.isfinite(rl)) or rh <= rl:
            return []
        if filt is not None:
            mid = (rh + rl) / 2.0
            pct = 100.0 * (rh - rl) / mid
            if pct < filt[0] or pct > filt[1]:
                return []

        sigs: list[Signal] = []
        broken = 0
        last_side: Optional[Side] = None
        for ts, row in sub.iterrows():
            c = float(row["close"])
            side: Optional[Side] = None
            if broken == 0:
                if c > rh:
                    side = Side.LONG
                elif c < rl:
                    side = Side.SHORT
            elif broken < n_max:
                # second breakout = cassure du bord OPPOSÉ uniquement
                if last_side == Side.SHORT and c > rh:
                    side = Side.LONG
                elif last_side == Side.LONG and c < rl:
                    side = Side.SHORT
            else:
                break
            if side is None:
                continue

            if sl_mode == "range":
                stop = rl if side == Side.LONG else rh
            elif sl_mode == "pct_entry":
                stop = c * (1 - sl_pct) if side == Side.LONG else c * (1 + sl_pct)
            elif sl_mode == "pct_range":
                base = rh if side == Side.LONG else rl
                stop = base * (1 - sl_pct) if side == Side.LONG else base * (1 + sl_pct)
            else:
                raise ValueError(f"sl_mode inconnu : {sl_mode}")

            # entrée au close : une cassure au close peut rester sous le stop
            # pct… impossible ; mais close > rh garantit stop('range') < entrée.
            if (side == Side.LONG and stop >= c) or (side == Side.SHORT and stop <= c):
                continue

            sigs.append(Signal(
                timestamp=ts, symbol=symbol, side=side,
                entry=c, stop=float(stop), target=None,
                reason=f"breakout {'haut' if side == Side.LONG else 'bas'} "
                       f"range {rl:.5g}-{rh:.5g} (#{broken + 1})",
            ))
            broken += 1
            last_side = side
        return sigs

    def generate_signals(self, data: pd.DataFrame, params: dict,
                         end_idx: int) -> list[Signal]:
        df = data.iloc[:end_idx]
        symbol = self.manifest().symbols[0]
        out: list[Signal] = []
        for _, day_df in df.groupby("day", sort=True):
            out.extend(self._signals_for_day(day_df, params, symbol))
        return out

    # ── Live path ────────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """Même décision que le chemin backtest sur la dernière barre close :
        on rejoue precompute + la logique du jour courant et on ne retient
        qu'un signal daté de la barre courante."""
        data = self.precompute(ctx.bars, self.params)
        last_ts = data.index[-1]
        day_df = data[data["day"] == data["day"].iloc[-1]]
        sigs = self._signals_for_day(day_df, self.params, ctx.symbol)
        for s in sigs:
            if pd.Timestamp(s.timestamp) == last_ts:
                return Signal(timestamp=s.timestamp, symbol=ctx.symbol,
                              side=s.side, entry=s.entry, stop=s.stop,
                              target=s.target, reason=s.reason)
        return None

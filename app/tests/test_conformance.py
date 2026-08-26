"""
Tests du gardien R5.

Le point important n'est pas qu'il valide une stratégie conforme — c'est qu'il
ATTRAPE une stratégie divergente. Un validateur qui ne peut pas échouer ne
valide rien. On lui soumet donc une divergence délibérée.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.contracts.strategy import (Side, Signal,
                                     StrategyManifest, StrategyModule)
from core.validation.conformance import check

N = 500
rng = np.random.default_rng(7)
_close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, N)))
BARS = pd.DataFrame(
    {"open": _close, "high": _close * 1.004, "low": _close * 0.996, "close": _close},
    index=pd.date_range("2024-01-01", periods=N, freq="h"),
)


def _manifest(sid):
    return StrategyManifest(
        strategy_id=sid, display_name=sid, version="1.0", magic_number=999999,
        author="test", source="test", symbols=["TEST"], timeframe="H1",
        warmup_bars=20, param_grid={}, default_params={"lookback": 10},
    )


class _Base(StrategyModule):
    """Croisement de moyenne mobile, trivial mais avec deux chemins réels."""
    STRATEGY_ID = "conf_test"
    MAGIC_NUMBER = 999999

    def manifest(self):
        return _manifest(self.STRATEGY_ID)

    def precompute(self, df, params):
        out = df.copy()
        out["ma"] = df["close"].rolling(params["lookback"]).mean()
        return out

    def _decide(self, data, i):
        """Règle unique, partagée : le prix repasse au-dessus de sa moyenne."""
        if i < 1 or pd.isna(data["ma"].iat[i]) or pd.isna(data["ma"].iat[i - 1]):
            return None
        c, p = data["close"].iat[i], data["close"].iat[i - 1]
        ma, ma_p = data["ma"].iat[i], data["ma"].iat[i - 1]
        if p <= ma_p and c > ma:
            return Signal(timestamp=data.index[i], symbol="TEST", side=Side.LONG,
                          entry=float(c), stop=float(c) * 0.99,
                          target=float(c) * 1.02, reason="cross up")
        return None

    def generate_signals(self, data, params, end_idx):
        return [s for s in (self._decide(data, i) for i in range(end_idx))
                if s is not None]

    def on_bar(self, ctx):
        data = self.precompute(ctx.bars, self.params)
        return self._decide(data, len(data) - 1)


class _Divergent(_Base):
    """Le chemin live décale son indice d'une barre. Erreur classique et
    silencieuse : le live regarde la barre en cours là où le backtest regarde
    la précédente."""
    STRATEGY_ID = "conf_test_divergent"

    def on_bar(self, ctx):
        data = self.precompute(ctx.bars, self.params)
        return self._decide(data, len(data) - 2)      # <- décalage délibéré


class _Delegating(_Base):
    """`on_bar` délègue au chemin backtest. Conforme par construction."""
    STRATEGY_ID = "conf_test_delegating"

    def on_bar(self, ctx):
        data = self.precompute(ctx.bars, self.params)
        sigs = self.generate_signals(data, self.params, len(data))
        if not sigs:
            return None
        last = sigs[-1]
        return last if pd.Timestamp(last.timestamp) == ctx.bars.index[-1] else None


def test_strategie_conforme_passe():
    r = check(_Base(), BARS, "TEST", n_bars=200)
    assert r.error is None, r.error
    assert r.ok, r.render()
    assert r.bars_replayed == 200
    print(f"stratégie conforme ................. OK "
          f"({r.n_backtest} signaux sur {r.bars_replayed} barres)")


def test_divergence_detectee():
    """LE test qui compte."""
    r = check(_Divergent(), BARS, "TEST", n_bars=200)
    assert r.error is None, r.error
    assert not r.ok, "le décalage d'une barre n'a PAS été detecte"
    assert len(r.divergences) > 0
    print(f"décalage d'une barre attrapé ....... OK "
          f"({len(r.divergences)} divergences détectées)")


def test_delegation_signalee():
    """Conforme, mais le rapport doit dire que c'est structurel."""
    r = check(_Delegating(), BARS, "TEST", n_bars=200)
    assert r.ok, r.render()
    assert r.delegates, "la délégation n'a pas été signalée"
    assert "STRUCTURELLE" in r.render()
    print("délégation signalée comme telle .... OK")


def test_historique_trop_court():
    r = check(_Base(), BARS.iloc[:15], "TEST", n_bars=200)
    assert r.error is not None and not r.ok
    print("historique trop court -> erreur .... OK")


if __name__ == "__main__":
    for fn in (test_strategie_conforme_passe, test_divergence_detectee,
               test_delegation_signalee, test_historique_trop_court):
        fn()

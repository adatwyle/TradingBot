"""
AUTO-TEST DU GARDIEN R1
=======================

Un test de causalité qui ne détecterait pas les fuites serait pire qu'inutile :
il donnerait une fausse assurance. Ce module le met à l'épreuve avec deux
stratégies jouets.

    CLEAN  — strictement causale                 -> R1 doit PASSER
    LEAKY  — reproduit le bug `closes[-1]`       -> R1 doit ÉCHOUER

La stratégie LEAKY reproduit exactement le défaut trouvé le 15 août 2026 dans
`fast_bt_multi` : la boucle respecte `end_idx`, mais une valorisation finale
utilise la dernière barre du tableau complet. C'était invisible à l'œil et
plausible dans les chiffres.

    python -m core.validation.selftest
"""
from __future__ import annotations

import os
import sys
from typing import Optional

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.contracts.strategy import (  # noqa: E402
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)
from core.validation.causality import check  # noqa: E402


def synthetic_bars(n: int = 3000, seed: int = 7) -> pd.DataFrame:
    """Marche aléatoire déterministe. Pas besoin de MT5 : on teste la mécanique
    du gardien, pas la qualité d'un signal."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 0.0009, n).cumsum()
    close = 1.10 + steps
    spread = np.abs(rng.normal(0, 0.0004, n))
    return pd.DataFrame(
        {
            "open": close - rng.normal(0, 0.0002, n),
            "high": close + spread,
            "low": close - spread,
            "close": close,
            "tick_volume": rng.integers(200, 2500, n),
        },
        index=pd.date_range("2021-01-01", periods=n, freq="h"),
    )


class _Base(StrategyModule):
    """Croisement de moyennes mobiles — le signal importe peu, seule compte la
    façon dont chaque variante regarde (ou non) le futur."""

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID, display_name=self.STRATEGY_ID,
            version="0.0.1", magic_number=self.MAGIC_NUMBER, author="selftest",
            source="synthetic", symbols=["TEST"], timeframe="H1",
            warmup_bars=60, param_grid={}, default_params={"fast": 10, "slow": 50},
        )

    def precompute(self, df: pd.DataFrame, params: dict):
        d = df.copy()
        d["fast"] = d["close"].rolling(params["fast"]).mean()
        d["slow"] = d["close"].rolling(params["slow"]).mean()
        return d

    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        return None  # non utilisé ici

    def _cross(self, d: pd.DataFrame, end_idx: int) -> list[int]:
        f, s = d["fast"].to_numpy(), d["slow"].to_numpy()
        out = []
        for i in range(self.manifest().warmup_bars, min(end_idx, len(d))):
            if np.isnan(f[i]) or np.isnan(s[i - 1]):
                continue
            if f[i - 1] <= s[i - 1] and f[i] > s[i]:
                out.append(i)
        return out


class CleanStrategy(_Base):
    """Strictement causale : chaque signal n'utilise que [0, i]."""
    STRATEGY_ID = "selftest_clean"
    MAGIC_NUMBER = 999001

    def generate_signals(self, data, params, end_idx) -> list[Signal]:
        d = data
        closes = d["close"].to_numpy()
        sigs = []
        for i in self._cross(d, end_idx):
            entry = float(closes[i])
            sigs.append(Signal(
                timestamp=d.index[i], symbol="TEST", side=Side.LONG,
                entry=entry, stop=entry * 0.995, target=entry * 1.010,
                reason="ma cross",
            ))
        return sigs


class LeakyStrategy(_Base):
    """Reproduit le bug historique.

    La boucle respecte bien `end_idx`. Mais la cible du DERNIER signal est
    calculée à partir de `closes[-1]` — la fin du tableau complet, donc le
    futur. Exactement la forme du bug `fast_bt_multi` : une seule valeur, en
    fin de traitement, hors de la tranche évaluée.
    """
    STRATEGY_ID = "selftest_leaky"
    MAGIC_NUMBER = 999002

    def generate_signals(self, data, params, end_idx) -> list[Signal]:
        d = data
        closes = d["close"].to_numpy()
        sigs = []
        crosses = self._cross(d, end_idx)
        for k, i in enumerate(crosses):
            entry = float(closes[i])
            if k == len(crosses) - 1:
                future = float(closes[-1])            # <-- LA FUITE
                target = max(entry * 1.001, future)
            else:
                target = entry * 1.010
            sigs.append(Signal(
                timestamp=d.index[i], symbol="TEST", side=Side.LONG,
                entry=entry, stop=entry * 0.995, target=target,
                reason="ma cross",
            ))
        return sigs


def main() -> int:
    df = synthetic_bars()
    print("=" * 78)
    print("AUTO-TEST DU GARDIEN R1")
    print("=" * 78)
    print(f"Données synthétiques : {len(df)} barres\n")

    ok = True

    print(">>> Cas 1 — stratégie CAUSALE (R1 doit passer)")
    r_clean = check(CleanStrategy(), df, "TEST")
    print(r_clean.render())
    if not r_clean.ok:
        print("\n!! Le gardien signale une fuite sur du code propre -> FAUX POSITIF")
        ok = False
    print()

    print(">>> Cas 2 — stratégie AVEC FUITE (R1 doit échouer)")
    r_leaky = check(LeakyStrategy(), df, "TEST")
    print(r_leaky.render())
    if r_leaky.ok:
        print("\n!! Le gardien n'a PAS vu une fuite délibérée -> FAUX NÉGATIF")
        print("   C'est le pire cas : le test rassurerait à tort.")
        ok = False
    print()

    print("=" * 78)
    if ok:
        print("AUTO-TEST RÉUSSI — le gardien laisse passer le code propre")
        print("et attrape la fuite. R1 est digne de confiance.")
    else:
        print("AUTO-TEST ÉCHOUÉ — ne pas se fier à R1 tant que ce n'est pas corrigé.")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

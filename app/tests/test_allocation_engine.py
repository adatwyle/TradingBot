"""
Tests du moteur d'allocation.

Le test qui compte est `test_r1_truncature` : c'est l'invariant qui a laissé
passer des mois de walk-forward faussé sur le moteur épisodique. On le vérifie
sur le nouveau moteur AVANT qu'une stratégie s'appuie dessus.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.backtest.engine import InstrumentSpec
from core.backtest.allocation_engine import run_allocation
from core.contracts.allocation import Allocation

N = 600


def _bars(seed, drift):
    rng = np.random.default_rng(seed)
    r = rng.normal(drift, 0.01, N)
    close = 100 * np.exp(np.cumsum(r))
    idx = pd.date_range("2020-01-01", periods=N, freq="D")
    return pd.DataFrame({"open": close, "high": close * 1.005,
                         "low": close * 0.995, "close": close}, index=idx)


BARS = {"AAA": _bars(1, 0.0006), "BBB": _bars(2, 0.0002)}
SPECS = {s: InstrumentSpec(s, 0.01, 2.0, 10.0, slippage_pips=0.5) for s in BARS}


def _allocs(step=40):
    """Bascule alternée AAA / BBB toutes les `step` barres."""
    out = []
    for k, i in enumerate(range(50, N - 5, step)):
        sym = "AAA" if k % 2 == 0 else "BBB"
        out.append(Allocation(timestamp=BARS[sym].index[i], weights={sym: 1.0}))
    return out


def test_r1_truncature():
    """Le résultat sur [0, T) ne doit pas dépendre de ce qui suit T.

    On compare l'equity produite par un run tronqué à la restriction du run
    complet. Toute divergence = fuite d'information depuis le futur.
    """
    allocs = _allocs()
    full = run_allocation(allocs, BARS, SPECS)
    for T in (200, 350, 500):
        cut = run_allocation(allocs, BARS, SPECS, end_idx=T)
        a = cut.equity.to_numpy()
        b = full.equity.iloc[:T].to_numpy()
        assert len(a) == T, f"longueur {len(a)} != {T}"
        assert np.allclose(a, b, atol=1e-12), (
            f"FUITE à T={T} : écart max {np.abs(a - b).max():.3e}")
    print("R1 troncature ...................... OK (T = 200 / 350 / 500)")


def test_full_weight_egale_buy_and_hold():
    """100 % d'un instrument du début à la fin doit reproduire son buy & hold,
    au coût d'entrée près. Sinon le calcul de rendement est faux."""
    a = [Allocation(timestamp=BARS["AAA"].index[1], weights={"AAA": 1.0})]
    res = run_allocation(a, BARS, SPECS)
    bh = res.benchmarks["B&H AAA"].total_return_pct
    mine = res.metrics.total_return_pct
    assert abs(mine - bh) < 1.5, f"écart {mine:.2f} vs B&H {bh:.2f}"
    assert res.metrics.time_in_asset["AAA"] > 95
    print(f"100 % AAA ≈ B&H AAA ................ OK ({mine:.1f} % vs {bh:.1f} %)")


def test_cash_ne_bouge_pas():
    """Une allocation vide doit geler l'equity, pas la laisser dériver."""
    a = [Allocation(timestamp=BARS["AAA"].index[1], weights={})]
    res = run_allocation(a, BARS, SPECS)
    assert abs(res.metrics.total_return_pct) < 1e-6, res.metrics.total_return_pct
    print("tout cash => equity plate .......... OK")


def test_benchmarks_toujours_presents():
    """Le critère n°1 de la méthodologie doit être répondable sans effort."""
    res = run_allocation(_allocs(), BARS, SPECS)
    for k in ("B&H AAA", "B&H BBB", "cash (0 %)"):
        assert k in res.benchmarks, f"référence manquante : {k}"
    assert any("naïf" in k for k in res.benchmarks), "équipondéré manquant"
    print(f"références intégrées ............... OK ({len(res.benchmarks)})")


def test_couts_penalisent_le_turnover():
    """Basculer souvent doit coûter plus que basculer rarement, toutes choses
    égales par ailleurs. Sinon les coûts ne mordent pas."""
    lent = run_allocation(_allocs(step=120), BARS, SPECS).metrics.total_return_pct
    a = _allocs(step=10)
    rapide = run_allocation(a, BARS, SPECS).metrics.total_return_pct
    sans = run_allocation(
        a, BARS, {s: InstrumentSpec(s, 0.01, 0.0, 10.0) for s in BARS}
    ).metrics.total_return_pct
    assert sans > rapide, "les coûts ne sont pas appliqués"
    print(f"coûts mordent sur le turnover ...... OK "
          f"(rapide {rapide:.1f} % vs sans coût {sans:.1f} % ; lent {lent:.1f} %)")


def test_le_jour_de_la_decision_n_est_pas_credite():
    """Régression — trouvée par l'agent s07 sur MON code.

    Décision à la clôture du jour 2, exécution à l'ouverture du jour 3. La
    hausse du jour 2 (open 100 -> close 200) est ANTÉRIEURE à la décision : elle
    ne doit pas être créditée. Une première version posait le poids une barre
    trop tôt et encaissait gratuitement la journée d'entrée — soit, sur la
    stratégie de s07, 107 278 % contre 901 % pour le buy & hold.

    R1 ne peut pas attraper ça : décalage systématique, pas fuite depuis le
    futur. L'invariant de troncature reste vrai. D'où ce test déterministe.
    """
    ix = pd.date_range("2024-01-01", periods=6, freq="D")
    op = [100, 100, 100, 200, 200, 200]
    b = {"A": pd.DataFrame(
        {"open": op, "high": op, "low": op, "close": [100, 100, 200, 200, 200, 200]},
        index=ix)}
    sp = {"A": InstrumentSpec("A", 0.01, 0.0, 100.0)}
    r = run_allocation([Allocation(timestamp=ix[2], weights={"A": 1.0})], b, sp)
    assert abs(r.metrics.total_return_pct) < 1e-9, (
        f"{r.metrics.total_return_pct:.1f} % — la hausse anterieure a la "
        f"decision a ete creditee")
    print("jour de decision non credite ....... OK (0.0 %)")


def test_le_rendement_posterieur_est_bien_credite():
    """Contrepartie : ce qui vient APRÈS l'exécution doit être capté.
    Sinon on aurait corrigé en décalant trop loin."""
    ix = pd.date_range("2024-01-01", periods=6, freq="D")
    op = [100, 100, 100, 100, 200, 200]      # hausse APRÈS l'exécution
    b = {"A": pd.DataFrame({"open": op, "high": op, "low": op, "close": op}, index=ix)}
    sp = {"A": InstrumentSpec("A", 0.01, 0.0, 100.0)}
    r = run_allocation([Allocation(timestamp=ix[2], weights={"A": 1.0})], b, sp)
    assert abs(r.metrics.total_return_pct - 100.0) < 1e-9, r.metrics.total_return_pct
    print("rendement posterieur credite ....... OK (+100.0 %)")


if __name__ == "__main__":
    for fn in (test_r1_truncature, test_full_weight_egale_buy_and_hold,
               test_cash_ne_bouge_pas, test_benchmarks_toujours_presents,
               test_couts_penalisent_le_turnover,
               test_le_jour_de_la_decision_n_est_pas_credite,
               test_le_rendement_posterieur_est_bien_credite):
        fn()
    print()
    print(run_allocation(_allocs(), BARS, SPECS).render())

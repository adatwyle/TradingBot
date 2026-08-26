"""
Régression — un stop sauté par un gap doit être exécuté.

Le moteur exigeait `low <= stop <= high` : la barre devait ENCADRER le stop.
Un gap de séance qui passe par-dessus ne déclenchait donc rien et la position
restait ouverte. Cas réel mesuré sur DAX par l'agent s11 : un SHORT du
2022-12-30 tenu 12 875 barres pour -210,59 R, bloquant ~270 trades derrière lui.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from core.backtest.engine import InstrumentSpec, run
from core.contracts.strategy import Side, Signal

SPEC = InstrumentSpec("TEST", 1.0, 0.0, 100.0)   # sans coût, pour isoler le fill
IDX = pd.date_range("2024-01-01", periods=6, freq="h")


def _bars(rows):
    return pd.DataFrame(rows, index=IDX, columns=["open", "high", "low", "close"])


def test_gap_sous_le_stop_long():
    """LONG entré à 100, stop 95. La barre 2 ouvre à 90 : gap sous le stop.
    Le stop doit être exécuté À L'OUVERTURE (90), pas au stop (95) — on subit
    le gap — et surtout pas ignoré."""
    bars = _bars([
        [100, 101,  99, 100],
        [100, 101,  99, 100],
        [ 90,  92,  88,  91],   # ouvre sous le stop
        [ 91,  93,  90,  92],
        [ 92,  94,  91,  93],
        [ 93,  95,  92,  94],
    ])
    r = run([Signal(timestamp=IDX[0], symbol="TEST", side=Side.LONG,
                    entry=100.0, stop=95.0, target=110.0, reason="test")], bars, SPEC)
    assert r.n_trades == 1, f"{r.n_trades} trades"
    t = r.trades[0]
    assert t.exit_reason == "SL", f"sortie={t.exit_reason} — le gap a ete ignore"
    assert abs(t.exit_price - 90.0) < 1e-9, f"prix={t.exit_price}, attendu 90"
    assert t.bars_held == 2, t.bars_held
    assert abs(t.pnl_r - (-2.0)) < 1e-9, f"R={t.pnl_r}, attendu -2 (perte de 10 pour 5 risques)"
    print(f"gap sous stop LONG ................. OK (SL a {t.exit_price}, {t.pnl_r:+.2f} R)")


def test_gap_au_dessus_du_stop_short():
    """Le cas DAX : SHORT entré à 100, stop 105, la barre 2 ouvre à 112."""
    bars = _bars([
        [100, 101,  99, 100],
        [100, 101,  99, 100],
        [112, 114, 111, 113],   # ouvre au-dessus du stop
        [113, 115, 112, 114],
        [114, 116, 113, 115],
        [115, 117, 114, 116],
    ])
    r = run([Signal(timestamp=IDX[0], symbol="TEST", side=Side.SHORT,
                    entry=100.0, stop=105.0, target=90.0, reason="test")], bars, SPEC)
    t = r.trades[0]
    assert t.exit_reason == "SL", f"sortie={t.exit_reason} — le gap a ete ignore"
    assert abs(t.exit_price - 112.0) < 1e-9, f"prix={t.exit_price}, attendu 112"
    assert t.bars_held == 2, t.bars_held
    print(f"gap au-dessus stop SHORT ........... OK (SL a {t.exit_price}, {t.pnl_r:+.2f} R)")


def test_stop_normal_inchange():
    """Le cas courant — la barre encadre le stop — doit être inchangé."""
    bars = _bars([
        [100, 101,  99, 100],
        [100, 101,  99, 100],
        [ 99, 100,  94,  96],   # traverse le stop 95 en cours de barre
        [ 96,  97,  95,  96],
        [ 96,  97,  95,  96],
        [ 96,  97,  95,  96],
    ])
    r = run([Signal(timestamp=IDX[0], symbol="TEST", side=Side.LONG,
                    entry=100.0, stop=95.0, target=110.0, reason="test")], bars, SPEC)
    t = r.trades[0]
    assert t.exit_reason == "SL" and abs(t.exit_price - 95.0) < 1e-9, t
    assert abs(t.pnl_r - (-1.0)) < 1e-9, t.pnl_r
    print(f"stop traverse en séance ............ OK (SL a 95, {t.pnl_r:+.2f} R)")


def test_cible_ne_profite_pas_du_gap():
    """Asymétrie assumée : la cible se remplit à son prix même si la barre a
    ouvert au-delà. Le gap coûte, il ne rapporte pas."""
    bars = _bars([
        [100, 101,  99, 100],
        [100, 101,  99, 100],
        [115, 117, 114, 116],   # ouvre au-dessus de la cible 110
        [116, 118, 115, 117],
        [117, 119, 116, 118],
        [118, 120, 117, 119],
    ])
    r = run([Signal(timestamp=IDX[0], symbol="TEST", side=Side.LONG,
                    entry=100.0, stop=95.0, target=110.0, reason="test")], bars, SPEC)
    t = r.trades[0]
    assert t.exit_reason == "TP", t.exit_reason
    assert abs(t.exit_price - 110.0) < 1e-9, f"prix={t.exit_price}, attendu 110 (pas 115)"
    print(f"cible sans bonus de gap ............ OK (TP a {t.exit_price}, {t.pnl_r:+.2f} R)")


def test_stop_prioritaire_sur_cible():
    """Les deux dans la même barre -> le stop l'emporte. Doctrine inchangée."""
    bars = _bars([
        [100, 101,  99, 100],
        [100, 101,  99, 100],
        [100, 112,  94, 105],   # touche stop 95 ET cible 110
        [105, 106, 104, 105],
        [105, 106, 104, 105],
        [105, 106, 104, 105],
    ])
    r = run([Signal(timestamp=IDX[0], symbol="TEST", side=Side.LONG,
                    entry=100.0, stop=95.0, target=110.0, reason="test")], bars, SPEC)
    assert r.trades[0].exit_reason == "SL", r.trades[0].exit_reason
    print("stop prioritaire sur cible ......... OK")


if __name__ == "__main__":
    for fn in (test_gap_sous_le_stop_long, test_gap_au_dessus_du_stop_short,
               test_stop_normal_inchange, test_cible_ne_profite_pas_du_gap,
               test_stop_prioritaire_sur_cible):
        fn()

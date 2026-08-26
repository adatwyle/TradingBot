"""
BRAS TÉMOIN — validation du générateur d'entrées aléatoires.

Un témoin qu'on ne contrôle pas ne vaut rien : s'il est biaisé, il rend
indulgent ou sévère sans qu'on sache dans quel sens, ce qui est exactement le
défaut qu'on lui demande de corriger dans `n_configs × 0,05`.

Trois propriétés sont donc vérifiées ici, dans cet ordre :

  1. CALIBRATION  une stratégie elle-même aléatoire doit tomber vers le 50e
                  percentile. Sinon le générateur est biaisé et TOUT percentile
                  qu'il produit est faux.
  2. DISCRIMINATION  une stratégie à edge injecté (elle connaît le régime) doit
                  ressortir au-delà du 95e percentile. Sinon le témoin est
                  aveugle et ne sert à rien.
  3. REPRODUCTIBILITÉ  même graine => mêmes tirages. Sinon le rapport n'est pas
                  vérifiable et le chiffre n'est pas opposable.

S'y ajoute le contrôle du BETA DIRECTIONNEL : sur un marché qui monte, l'entrée
longue au hasard DOIT être rentable. C'est l'effet secondaire assumé du témoin
(il relève la barre) et il faut prouver qu'on le mesure, pas qu'on l'ignore.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.backtest.anchored_wf import control_arm
from core.backtest.engine import InstrumentSpec
from core.backtest.engine import run as run_engine
from core.contracts.strategy import Side, Signal

# Spread nul : on isole le générateur, pas le modèle de coût (le moteur a ses
# propres tests). Le coût s'applique de toute façon aux DEUX bras.
SPEC = InstrumentSpec("TEST", 0.01, 0.0, 100.0)

SL_ATR, TP_ATR = 1.5, 3.0        # gabarit de risque commun à tous ces tests


# ─────────────────────────────────────────────────────────────────────────────
# Fabriques de séries
# ─────────────────────────────────────────────────────────────────────────────
def _bars_from_close(close: np.ndarray) -> pd.DataFrame:
    """OHLC plausible autour d'une trajectoire de clôtures.

    Le haut et le bas sont écartés d'une fraction du pas : sans amplitude
    intra-barre, aucun stop ni aucune cible ne serait jamais touché et le test
    ne mesurerait que des résiduels.
    """
    n = len(close)
    step = np.abs(np.diff(close, prepend=close[0])) + 0.05 * np.std(close)
    high = close + 0.6 * step
    low = close - 0.6 * step
    op = np.concatenate(([close[0]], close[:-1]))
    idx = pd.date_range("2021-01-01", periods=n, freq="h")
    return pd.DataFrame({"open": op, "high": high, "low": low, "close": close},
                        index=idx)


def _random_walk(n: int, seed: int, drift: float = 0.0, vol: float = 1.0):
    rng = np.random.default_rng(seed)
    return _bars_from_close(500.0 + np.cumsum(rng.normal(drift, vol, n)))


def _regime_blocks(n: int, seed: int, block: int = 200, amp: float = 0.9):
    """Série à régimes alternés de signe ALÉATOIRE.

    Sert au test de discrimination : une entrée au hasard voit autant de blocs
    haussiers que baissiers et doit finir à zéro, tandis qu'une stratégie qui
    connaît le régime en cours gagne. Le signe est tiré au sort pour qu'aucune
    dérive globale ne vienne aider le bras témoin ou la stratégie.
    """
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=n // block + 1)
    drift = np.repeat(signs, block)[:n] * amp
    close = 500.0 + np.cumsum(drift + rng.normal(0.0, 1.0, n))
    return _bars_from_close(close), np.repeat(signs, block)[:n]


def _atr_of(bars):
    from core.backtest.anchored_wf import _atr
    return _atr(bars)


def _signals(bars, atr, positions, sides):
    """Construit des signaux au gabarit commun (1,5 ATR de stop, 3 ATR de cible)."""
    close = bars["close"].to_numpy()
    out = []
    for j, side in zip(positions, sides):
        a = float(atr[j])
        if not np.isfinite(a) or a <= 0:
            continue
        e = float(close[j])
        long = side == Side.LONG
        out.append(Signal(timestamp=bars.index[j], symbol="TEST", side=side,
                          entry=e,
                          stop=e - SL_ATR * a if long else e + SL_ATR * a,
                          target=e + TP_ATR * a if long else e - TP_ATR * a,
                          reason="test"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 1. CALIBRATION — un hasard comparé au hasard tombe au milieu
# ─────────────────────────────────────────────────────────────────────────────
def test_strategie_aleatoire_tombe_vers_le_50e_percentile():
    """LE test qui valide le générateur.

    On fabrique une « stratégie » qui n'est rien d'autre qu'un tirage au sort
    d'entrées, puis on la juge avec le bras témoin. S'il est non biaisé, son
    percentile est uniforme sur [0, 100] et sa moyenne vaut 50.

    Un échec ici invalide TOUS les percentiles produits par le module : le
    témoin serait systématiquement trop indulgent ou trop sévère.
    """
    pcts = []
    for rep in range(24):
        bars = _random_walk(2400, seed=7000 + rep)
        atr = _atr_of(bars)
        rng = np.random.default_rng(90_000 + rep)

        # Entrées au hasard, 50/50 long/short — aucune information exploitée.
        pos = np.sort(rng.choice(np.arange(30, len(bars) - 2), size=40, replace=False))
        sides = [Side.LONG if b else Side.SHORT for b in rng.integers(0, 2, len(pos))]
        res = run_engine(_signals(bars, atr, pos, sides), bars, SPEC)
        assert res.n_trades > 0, "pas de trade : le test ne mesure rien"

        ca = control_arm(bars, SPEC, res.trades, res.total_r,
                         draws=120, seed=4242 + rep)
        assert ca is not None
        pcts.append(ca.percentile)

    moy = float(np.mean(pcts))
    assert 35.0 <= moy <= 65.0, (
        f"percentile moyen {moy:.1f} sur {len(pcts)} répétitions — "
        "le générateur du témoin est BIAISÉ")
    # Une distribution centrée mais dégénérée (tout à 50) serait tout aussi
    # suspecte : le témoin doit avoir de la dispersion.
    assert float(np.std(pcts)) > 8.0, f"écart-type {np.std(pcts):.1f} : témoin dégénéré"
    print(f"calibration ......... OK (percentile moyen {moy:.1f}, "
          f"ecart-type {np.std(pcts):.1f}, n={len(pcts)})")


def test_effectif_du_temoin_colle_a_celui_de_la_strategie():
    """Comparer 40 trades à 12 trades ne veut rien dire.

    L'échantillonnage stratifié existe pour ça : sans lui, le moteur refuse la
    moitié des entrées aléatoires agglutinées et le témoin sous-estime le R
    atteignable par hasard.
    """
    bars = _random_walk(2400, seed=31)
    atr = _atr_of(bars)
    rng = np.random.default_rng(31)
    pos = np.sort(rng.choice(np.arange(30, len(bars) - 2), size=40, replace=False))
    sides = [Side.LONG if b else Side.SHORT for b in rng.integers(0, 2, len(pos))]
    res = run_engine(_signals(bars, atr, pos, sides), bars, SPEC)

    ca = control_arm(bars, SPEC, res.trades, res.total_r, draws=120, seed=11)
    assert ca.effectif_ok, (
        f"effectif témoin médian {ca.median_draw_trades} vs "
        f"{ca.n_trades_ref} de référence")
    # Répartition long/short imposée à l'identique, pas approchée.
    ref_long = sum(1 for t in res.trades if t.side == Side.LONG) / res.n_trades
    assert abs(ca.long_frac - ref_long) < 1e-9
    print(f"effectif ............ OK ({ca.n_trades_ref} réf / "
          f"{ca.median_draw_trades:.0f} témoin, {100*ca.long_frac:.0f} % long)")


# ─────────────────────────────────────────────────────────────────────────────
# 2. DISCRIMINATION — un edge injecté doit ressortir
# ─────────────────────────────────────────────────────────────────────────────
def test_edge_synthetique_depasse_le_95e_percentile():
    """Le témoin doit VOIR un avantage réel, sinon il ne sert à rien.

    La série alterne des régimes de signe aléatoire. La « stratégie » connaît le
    signe du régime en cours et entre dans son sens — c'est un oracle, donc de
    la triche assumée : c'est le seul moyen de fabriquer un edge dont on est
    certain qu'il existe. Le témoin, lui, tire ses entrées au hasard sur les
    mêmes barres, avec le même effectif, le même partage long/short et les mêmes
    distances : il voit autant de régimes à contresens qu'à l'endroit.
    """
    bars, regime = _regime_blocks(3200, seed=77)
    atr = _atr_of(bars)
    rng = np.random.default_rng(77)
    pos = np.sort(rng.choice(np.arange(30, len(bars) - 2), size=60, replace=False))
    sides = [Side.LONG if regime[j] > 0 else Side.SHORT for j in pos]

    res = run_engine(_signals(bars, atr, pos, sides), bars, SPEC)
    assert res.total_r > 0, f"l'oracle n'est même pas rentable ({res.total_r:+.1f} R)"

    ca = control_arm(bars, SPEC, res.trades, res.total_r, draws=200, seed=777)
    assert ca.percentile > 95.0, (
        f"percentile {ca.percentile:.1f} — le témoin ne DISCRIMINE pas un edge "
        f"injecté (stratégie {res.total_r:+.1f} R contre nul médian "
        f"{ca.null_median:+.1f} R)")
    print(f"discrimination ...... OK (percentile {ca.percentile:.1f}, "
          f"{res.total_r:+.1f} R contre nul médian {ca.null_median:+.1f} R)")


# ─────────────────────────────────────────────────────────────────────────────
# 3. REPRODUCTIBILITÉ
# ─────────────────────────────────────────────────────────────────────────────
def test_meme_graine_memes_tirages():
    """Sans reproductibilité, un percentile publié n'est pas vérifiable."""
    bars = _random_walk(1800, seed=5)
    atr = _atr_of(bars)
    rng = np.random.default_rng(5)
    pos = np.sort(rng.choice(np.arange(30, len(bars) - 2), size=30, replace=False))
    sides = [Side.LONG if b else Side.SHORT for b in rng.integers(0, 2, len(pos))]
    res = run_engine(_signals(bars, atr, pos, sides), bars, SPEC)

    a = control_arm(bars, SPEC, res.trades, res.total_r, draws=60, seed=123)
    b = control_arm(bars, SPEC, res.trades, res.total_r, draws=60, seed=123)
    c = control_arm(bars, SPEC, res.trades, res.total_r, draws=60, seed=124)
    assert np.array_equal(a.draws_r, b.draws_r), "graine identique, tirages différents"
    assert not np.array_equal(a.draws_r, c.draws_r), "la graine n'a aucun effet"
    print(f"reproductibilité .... OK (percentile {a.percentile:.1f} rejoué à l'identique)")


# ─────────────────────────────────────────────────────────────────────────────
# 4. BETA DIRECTIONNEL — l'effet secondaire doit être MESURÉ, pas neutralisé
# ─────────────────────────────────────────────────────────────────────────────
def test_beta_directionnel_mesure_sur_marche_haussier():
    """Sur une tendance, le LONG au hasard gagne — et le témoin doit le dire.

    C'est le point qui rend le témoin supérieur à `n × 0,05` : il monte
    automatiquement la barre là où un simple beta suffirait à paraître bon.
    """
    bars = _random_walk(3000, seed=9, drift=0.55, vol=1.0)
    atr = _atr_of(bars)
    rng = np.random.default_rng(9)
    pos = np.sort(rng.choice(np.arange(30, len(bars) - 2), size=50, replace=False))
    sides = [Side.LONG if b else Side.SHORT for b in rng.integers(0, 2, len(pos))]
    res = run_engine(_signals(bars, atr, pos, sides), bars, SPEC)

    ca = control_arm(bars, SPEC, res.trades, res.total_r, draws=150, seed=99)
    lo = float(np.nanmean(ca.draws_long_rpt))
    sh = float(np.nanmean(ca.draws_short_rpt))
    assert lo > 0 > sh, f"LONG aléatoire {lo:+.3f} / SHORT {sh:+.3f} sur une hausse franche"
    assert ca.beta_directionnel > 0.1, ca.beta_directionnel
    # Le seuil à battre a monté : la médiane nulle est franchement positive.
    assert ca.null_median > 0, ca.null_median
    print(f"beta directionnel ... OK (L {lo:+.3f} / S {sh:+.3f} R/trade, "
          f"écart {ca.beta_directionnel:+.3f}, nul médian {ca.null_median:+.2f} R)")


# ─────────────────────────────────────────────────────────────────────────────
# 5. PAS DE RÉSULTAT SANS EFFECTIF
# ─────────────────────────────────────────────────────────────────────────────
def test_aucun_temoin_sans_trades_de_reference():
    """Sans trade observé, il n'y a pas de gabarit — donc pas de percentile.
    Une case vide vaut mieux qu'un chiffre inventé sur rien."""
    bars = _random_walk(500, seed=3)
    assert control_arm(bars, SPEC, [], 0.0, draws=10, seed=1) is None
    print("garde effectif ...... OK (aucun trade => aucun percentile)")


if __name__ == "__main__":
    for fn in (test_strategie_aleatoire_tombe_vers_le_50e_percentile,
               test_effectif_du_temoin_colle_a_celui_de_la_strategie,
               test_edge_synthetique_depasse_le_95e_percentile,
               test_meme_graine_memes_tirages,
               test_beta_directionnel_mesure_sur_marche_haussier,
               test_aucun_temoin_sans_trades_de_reference):
        fn()
    print("\nBRAS TÉMOIN — toutes les vérifications passent.")

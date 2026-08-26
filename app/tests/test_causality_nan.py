"""
Tests du gardien R1 — l'angle mort des NaN.

POURQUOI CE FICHIER EXISTE
--------------------------
Le 16 août 2026, l'agent s06 a injecté volontairement une fuite (une moyenne
mobile calculée sur la série RETOURNÉE) dans une stratégie, puis a passé R1.
Le gardien a répondu « R1 PASSÉ ».

La raison : `_compare_precompute` comparait les indicateurs sous le masque
`np.isfinite(a) & np.isfinite(b)`. Un point NaN d'un seul côté était donc
EXCLU de la comparaison au lieu d'être compté comme un désaccord. Or c'est
précisément la signature de cette famille de fuites : une fenêtre qui lit vers
l'avant n'a pas de valeur en fin de série tronquée, alors qu'elle en a une sur
la série complète. La divergence est entièrement dans le motif de NaN — et le
masque la faisait disparaître.

Un « R1 PASSÉ » ne vaut que la surface qu'il couvre. Ces tests fixent cette
surface : ce qui compte n'est pas que le gardien valide une stratégie propre,
c'est qu'il ATTRAPE le décalage de NaN.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.contracts.strategy import (MarketContext, Signal, StrategyManifest,
                                     StrategyModule)
from core.validation.causality import check, _compare_precompute

N = 600
WINDOW = 12                      # fenêtre des moyennes mobiles des cobayes
rng = np.random.default_rng(11)
_close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, N)))
BARS = pd.DataFrame(
    {"open": _close, "high": _close * 1.003, "low": _close * 0.997, "close": _close},
    index=pd.date_range("2024-01-01", periods=N, freq="h"),
)


def _manifest(sid):
    return StrategyManifest(
        strategy_id=sid, display_name=sid, version="1.0", magic_number=999998,
        author="test", source="test", symbols=["TEST"], timeframe="H1",
        warmup_bars=20, param_grid={}, default_params={},
    )


class _Causale(StrategyModule):
    """Témoin négatif : strictement causale, avec du warmup et un trou.

    Elle porte volontairement les deux motifs de NaN LÉGITIMES :
      * `ma` : NaN sur les WINDOW-1 premières barres (warmup), des DEUX côtés ;
      * `vide` : colonne entièrement NaN, des DEUX côtés.
    Aucun des deux ne doit être signalé — sinon le gardien crie au loup et
    devient inutilisable, ce qui est une autre façon de ne rien garder.
    """
    STRATEGY_ID = "r1_nan_causale"
    MAGIC_NUMBER = 999998

    def manifest(self):
        return _manifest(self.STRATEGY_ID)

    def precompute(self, df, params):
        out = pd.DataFrame(index=df.index)
        out["ma"] = df["close"].rolling(WINDOW).mean()
        out["vide"] = np.nan
        return out

    def generate_signals(self, data, params, end_idx) -> list[Signal]:
        # Aucun signal : on isole la couche INDICATEUR. Si le gardien rate la
        # fuite, ce n'est pas parce qu'un signal l'aurait rattrapée.
        return []

    def on_bar(self, ctx: MarketContext):
        return None


class _FuiteParNaN(_Causale):
    """Le cobaye. Reproduit la fuite qui est passée le 16 août 2026.

    `ma_inversee` = moyenne mobile calculée sur la série RETOURNÉE : la valeur
    en `i` dépend de `[i, i+WINDOW-1]`, donc du FUTUR.

    Sa signature est instructive. Sur l'historique complet, les NaN de cette
    colonne sont rejetés tout à la fin du tableau — bien au-delà de la coupure,
    donc invisibles. Sur l'historique tronqué, ils tombent sur les WINDOW-1
    dernières barres AVANT la coupure. Et partout ailleurs les deux séries
    coïncident au bit près, puisque la fenêtre avant y dispose des mêmes barres.

    Autrement dit : la fuite ne se manifeste QUE par un décalage de NaN. Elle
    est indétectable pour un comparateur qui masque les NaN.
    """
    STRATEGY_ID = "r1_nan_fuite"

    def precompute(self, df, params):
        out = super().precompute(df, params)
        rev = df["close"].to_numpy()[::-1]
        out["ma_inversee"] = pd.Series(rev).rolling(WINDOW).mean().to_numpy()[::-1]
        return out


# ─────────────────────────────────────────────────────────────────────────────
# 1. La démonstration du défaut — figée pour qu'il ne revienne pas
# ─────────────────────────────────────────────────────────────────────────────

def _ancien_comparateur(a: np.ndarray, b: np.ndarray, tol: float = 1e-9) -> int:
    """L'ancienne logique, reproduite à l'identique.

    Conservée EXPRÈS dans les tests : elle documente ce que le gardien ne
    voyait pas. Elle doit continuer à ne rien trouver — c'est la preuve que le
    cas est bien celui qui est passé entre les mailles, et pas un autre.
    """
    both = np.isfinite(a) & np.isfinite(b)
    if not both.any():
        return 0
    d = np.zeros_like(a, dtype=float)
    d[both] = np.abs(a[both] - b[both])
    scale = max(1.0, float(np.nanmedian(np.abs(a[both]))) or 1.0)
    return int(np.count_nonzero(d > tol * scale))


def test_langle_mort_est_reel():
    """La fuite est réelle ET l'ancien masque ne la voit pas. Sans ce test, la
    correction n'aurait pas de sujet."""
    s = _FuiteParNaN()
    T = int(N * 0.80)
    full = s.precompute(BARS, s.params)["ma_inversee"].to_numpy()[:T]
    trunc = s.precompute(BARS.iloc[:T].copy(), s.params)["ma_inversee"].to_numpy()[:T]

    desaccords = int(np.count_nonzero(np.isfinite(full) ^ np.isfinite(trunc)))
    assert desaccords == WINDOW - 1, desaccords          # la fuite, mesurée
    assert _ancien_comparateur(full, trunc) == 0         # l'angle mort, mesuré
    print(f"angle mort caractérisé ............. OK "
          f"({desaccords} points en désaccord, 0 vu par l'ancien masque)")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Le gardien corrigé
# ─────────────────────────────────────────────────────────────────────────────

def test_decalage_de_nan_attrape():
    """LE test qui compte. Échoue sur le gardien d'avant la correction."""
    r = check(_FuiteParNaN(), BARS, "TEST")
    assert all(c.ok for c in r.cuts), "la couche signal n'était pas censée réagir"
    assert r.indicator_leaks, "le décalage de NaN n'a PAS été détecté"
    assert not r.ok, "le rapport conclut « PASSÉ » malgré une fuite détectée"

    cols = {L.column for L in r.indicator_leaks}
    assert cols == {"ma_inversee"}, cols                 # pas de dégât collatéral
    assert all(L.n_nan_mismatch == WINDOW - 1 for L in r.indicator_leaks)
    assert "R1 ÉCHOUÉ" in r.render()
    print(f"décalage de NaN attrapé ............ OK "
          f"({len(r.indicator_leaks)} fuites sur {len(r.cuts)} coupures, "
          f"colonne « ma_inversee »)")


def test_warmup_et_colonne_vide_non_signales():
    """Le contre-poison : les NaN attendus des deux côtés restent silencieux."""
    r = check(_Causale(), BARS, "TEST")
    assert r.ok, r.render()
    assert not r.indicator_leaks, [L.column for L in r.indicator_leaks]
    print(f"warmup + colonne vide ignorés ...... OK "
          f"({len(r.cuts)} coupures, 0 fuite)")


def test_nan_apparaissant_en_zone_definie():
    """Variante minimale, sans stratégie : un seul NaN injecté au milieu d'une
    zone où les deux séries sont définies doit suffire."""
    n = 100
    a = np.arange(n, dtype=float)
    b = a.copy()
    a[:5] = b[:5] = np.nan          # warmup commun : à ignorer
    b[60] = np.nan                  # le NaN pathologique : à signaler

    fa = pd.DataFrame({"x": a})
    fb = pd.DataFrame({"x": b})
    leaks = _compare_precompute(fa, fb, n, 0.8)
    assert len(leaks) == 1, leaks
    assert leaks[0].n_nan_mismatch == 1
    assert leaks[0].n_affected == 1
    print("NaN isolé en zone définie signalé .. OK (1 point, 1 fuite)")


def test_warmup_plus_long_du_cote_tronque_signale():
    """Cas plus vicieux : la troncature RALLONGE le warmup. Les deux séries
    sont NaN au début, mais pas sur la même longueur — la zone d'écart est
    hors du warmup COMMUN, donc c'est bien une fuite."""
    n = 100
    a = np.arange(n, dtype=float)
    b = a.copy()
    a[:5] = np.nan
    b[:9] = np.nan                  # 4 barres de plus côté tronqué

    leaks = _compare_precompute(pd.DataFrame({"x": a}), pd.DataFrame({"x": b}), n, 0.8)
    assert len(leaks) == 1, leaks
    assert leaks[0].n_nan_mismatch == 4, leaks[0].n_nan_mismatch
    print("warmup asymétrique signalé ......... OK (4 points)")


def test_ecart_numerique_toujours_attrape():
    """Non-régression : la détection numérique d'origine doit survivre à la
    correction. C'est elle qui avait attrapé `filtfilt`."""
    n = 100
    a = np.arange(n, dtype=float) + 1.0
    b = a.copy()
    b[70] += 1.0                    # écart franc, aucun NaN en jeu

    leaks = _compare_precompute(pd.DataFrame({"x": a}), pd.DataFrame({"x": b}), n, 0.8)
    assert len(leaks) == 1, leaks
    assert leaks[0].n_nan_mismatch == 0
    assert leaks[0].n_affected == 1
    assert abs(leaks[0].max_deviation - 1.0) < 1e-12
    print("écart numérique toujours vu ........ OK (écart 1.0)")


def test_precompute_opaque_reste_exempte():
    """Un `precompute` qui ne renvoie pas de DataFrame reste non inspectable.
    Ce n'est pas une régression, c'est une limite CONNUE du gardien : il faut
    qu'elle soit visible dans les tests, pas découverte en production."""
    leaks = _compare_precompute({"signals": []}, {"signals": []}, 50, 0.8)
    assert leaks == []
    print("objet opaque -> non inspecté ....... OK (limite assumée)")


if __name__ == "__main__":
    for fn in (test_langle_mort_est_reel,
               test_decalage_de_nan_attrape,
               test_warmup_et_colonne_vide_non_signales,
               test_nan_apparaissant_en_zone_definie,
               test_warmup_plus_long_du_cote_tronque_signale,
               test_ecart_numerique_toujours_attrape,
               test_precompute_opaque_reste_exempte):
        fn()

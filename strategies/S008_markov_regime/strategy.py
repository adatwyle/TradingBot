"""
Markov Regime Switching — stratégie s08_markov_regime
======================================================

Source  : https://www.youtube.com/watch?v=Z-hU97WO30I (Lewis Jackson, d'après
          « Ran », hedge fund method)
Analyse : `research/ANALYSIS.md` — à lire avant de modifier ce fichier.
Noyau   : `markov.py` — les quatre pièges d'implémentation y sont documentés.

POURQUOI LE CONTRAT ALLOCATION ET PAS LE CONTRAT ÉPISODIQUE
------------------------------------------------------------
La source décrit une position **dimensionnée par la confiance**, **sans stop de
prix**, potentiellement **toujours investie**, dont l'invalidation est le
changement de signal — jamais un niveau. C'est la définition littérale de
`AllocationModule` (`core/contracts/allocation.py`).

Forcer ça dans `Signal(entry, stop, target)` exigerait d'inventer un stop absent
de la source. R3 existe pour protéger une position isolée d'une perte illimitée ;
ici la protection est la règle de bascule elle-même. Un stop inventé pour
satisfaire un validateur serait pire que pas de stop : il donnerait l'illusion
d'une protection qui n'est pas dans la méthode testée.

Bénéfice décisif, et c'est le point qui tranche : `run_allocation()` rend
SYSTÉMATIQUEMENT le buy & hold de chaque constituant et l'équipondéré naïf.
L'auteur annonce « Bitcoin ~60× » sans jamais donner de référence — angle mort
central de la source. Le contrat d'allocation y répond nativement.

Le mode « filtre » qu'il décrit (le régime autorise ou interdit une stratégie
existante) reste exprimable ici : c'est une allocation qui vaut 100 % ou 0 %.
Il est fourni comme valeur du paramètre `mode`, pas comme second contrat.

LES SHORTS ET LA LIMITE DU CONTRAT — non contournée en douce
--------------------------------------------------------------
`Allocation.weights` impose des poids dans [0, 1] : un poids négatif lève une
exception. Le contrat ne sait pas exprimer une jambe short.

Même traitement que s07 : les jambes courtes sont portées par des séries
synthétiques `SYM~S` construites en amont (`run_backtest.py`), dont le rendement
open->open est l'exact opposé de celui de `SYM`. Conséquence à ne jamais
oublier en lisant un run avec shorts : les benchmarks de ce run contiennent le
buy & hold d'une série inversée, qui n'a aucun sens comme référence. Seule la
courbe de la stratégie s'y lit ; les benchmarks se lisent sur le run long-only.

R2 — CE FICHIER NE CALCULE PAS DE TAILLE DE POSITION
------------------------------------------------------
Les poids émis sont des **intentions** relatives. Aucun lot, aucun pourcentage
de risque, aucune lecture de solde. `core/risk/` décide de l'exposition réelle.

LES DEUX MODES DE DIMENSIONNEMENT, ET POURQUOI LES DEUX SONT PUBLIÉS
----------------------------------------------------------------------
`size_mode="proportional"` est fidèle à la source (« 70 % de confiance -> grosse
allocation, 1 % -> petite »). Mais avec une matrice non recouvrante, |signal|
vaut typiquement 0,2-0,4 : le portefeuille resterait investi à 20-40 % pendant
qu'un buy & hold l'est à 100 %. L'écart mesurerait alors la taille du compte,
pas la qualité du signal — exactement le piège documenté dans s07.

`size_mode="binary"` met le poids plafond dès que le signal a un signe. Il isole
le TIMING du dimensionnement. Aucun des deux n'est « le bon » : ils répondent à
deux questions différentes, et les deux sont rapportés.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.allocation import (
    Allocation, AllocationContext, AllocationManifest, AllocationModule,
)

# Import adapted for the new runtime (strategy.py loaded standalone via
# importlib.spec_from_file_location, no parent package). Logic unchanged.
# Explicit guard instead of try/except ImportError: a genuinely missing
# dependency must propagate with a clear traceback.
if __package__ in (None, ""):
    import importlib.util as _ilu
    import os as _os
    _spec = _ilu.spec_from_file_location(
        "markov", _os.path.join(_os.path.dirname(__file__), "markov.py"))
    mk = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(mk)
else:
    from . import markov as mk  # package-style import (prototype layout)

SHORT_SUFFIX = "~S"


def short_symbol(sym: str) -> str:
    return f"{sym}{SHORT_SUFFIX}"


def is_short_symbol(sym: str) -> bool:
    return sym.endswith(SHORT_SUFFIX)


def base_symbol(sym: str) -> str:
    return sym[: -len(SHORT_SUFFIX)] if is_short_symbol(sym) else sym


class Strategy(AllocationModule):
    STRATEGY_ID = "s08_markov_regime"
    MAGIC_NUMBER = 130008

    DEFAULT_UNIVERSE = ["SP500", "NASDAQ", "BTCUSD"]

    def __init__(self, params: Optional[dict] = None,
                 universe: Optional[list[str]] = None):
        self._universe = list(universe) if universe else list(self.DEFAULT_UNIVERSE)
        super().__init__(params)

    # ── Manifest ────────────────────────────────────────────────────────────
    def manifest(self) -> AllocationManifest:
        return AllocationManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Markov Regime Switching (hedge fund method)",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s08_markov_regime",
            source="https://www.youtube.com/watch?v=Z-hU97WO30I",
            universe=list(self._universe),
            timeframe="D1",
            # 20 barres pour définir l'état, puis il faut assez de transitions
            # NON RECOUVRANTES pour que la matrice ne soit pas du bruit. À
            # step=20, 500 barres ne donnent que ~24 transitions. On exige 800
            # barres, soit ~39 transitions — encore peu, et c'est dit dans
            # research/FALSIFICATION.md §F3.
            warmup_bars=800,
            param_grid={
                # 4 x 3 x 3 = 36 cellules, soit ~1,8 « réussite » attendue par
                # pur hasard au seuil 5 % (docs/METHODOLOGY.md §6). Grille
                # délibérément petite : une grille large trouve un meilleur faux
                # positif, pas un meilleur edge.
                "window": [10, 20, 40, 60],
                "thr": [0.03, 0.05, 0.08],
                "size_scale": [1.0, 2.0, 3.0],
            },
            default_params={
                # ── Définition de l'état — valeurs de la source
                "window": 20,            # « les 20 derniers jours »
                "thr": 0.05,             # « plus de 5 % » / « moins de -5 % »
                # ── Matrice de transition
                "step": 20,              # correction n°1 : pas de recouvrement.
                                         # 1 = version recouvrante (l'artefact).
                "alpha": 1.0,            # lissage de Laplace
                "causal": True,          # correction n°2 : R1
                "horizon": 1,            # n pas ; P^n, pas l'exponentiation
                "scalar_power": False,   # True = la maths fausse de la source
                # ── Traduction en poids
                "mode": "standalone",    # standalone | filter
                "signal_source": "markov",   # markov | naive | hmm_agree
                "size_mode": "proportional",  # proportional | binary
                "size_scale": 2.0,
                "weight_cap": 1.0,
                "min_signal": 0.02,      # sous ce seuil : cash, pas de pari
                "enable_shorts": False,
                # ── Markov caché (concept 9)
                "hmm_mode": "causal",    # causal | leaky — leaky = le piège R7
                "hmm_min_bars": 500,
                "hmm_refit_every": 60,
            },
            max_single_weight=1.0,
            rebalance="daily",
            allow_cash=True,
            status="RESEARCH",
            notes="Contrat allocation. Shorts via séries synthétiques SYM~S. "
                  "Voir research/FALSIFICATION.md (écrit avant tout résultat).",
        )

    # ── Indicateurs ─────────────────────────────────────────────────────────
    def precompute(self, bars: dict[str, pd.DataFrame], params: dict) -> Any:
        """Un SEUL DataFrame à plat, colonnes numériques préfixées par symbole.

        LE FORMAT DE RETOUR EST UN CHOIX, PAS UNE COMMODITÉ
        ---------------------------------------------------
        `core/validation/causality.py::_compare_precompute` commence par :

            if not isinstance(data_full, pd.DataFrame): return leaks

        Un `precompute()` qui renvoie un dict — réflexe naturel en multi-actifs —
        **échappe silencieusement** à la couche indicateur du gardien R1. Le
        rapport afficherait « R1 PASSÉ » sans avoir inspecté une seule série.
        Ce piège a été vérifié deux fois sur ce projet. D'où le DataFrame plat :
        chaque colonne est réellement comparée entre passe complète et passe
        tronquée.
        """
        base = [s for s in bars if not is_short_symbol(s)]
        idx = bars[sorted(bars)[0]].index
        out: dict[str, np.ndarray] = {}

        w = int(params["window"])
        thr = float(params["thr"])
        step = int(params["step"])

        for sym in sorted(base):
            close = bars[sym]["close"].to_numpy(dtype=float)
            ret = mk.rolling_return(close, w)
            st = mk.classify(ret, thr, -thr)

            res = mk.markov_signal(
                st, step,
                horizon=int(params["horizon"]),
                alpha=float(params["alpha"]),
                causal=bool(params["causal"]),
                scalar_power=bool(params["scalar_power"]),
            )

            out[f"{sym}_ret"] = ret
            # Les états sont stockés en float : la couche indicateur du gardien
            # ignore les colonnes non flottantes, et un état qui basculerait à
            # cause d'une fuite doit être vu.
            out[f"{sym}_state"] = np.where(st >= 0, st, np.nan).astype(float)
            out[f"{sym}_signal"] = res["signal"]
            out[f"{sym}_pbull"] = res["p_bull"]
            out[f"{sym}_pbear"] = res["p_bear"]
            out[f"{sym}_ntrans"] = res["n_trans"]
            out[f"{sym}_persist"] = res["persistence"]

            # Règle naïve de référence : le signal qui resterait si la matrice
            # était figée. C'est la comparaison qui décide si l'appareil
            # markovien contribue à quoi que ce soit (research/FALSIFICATION §F1).
            naive = np.zeros(len(st), dtype=float)
            naive[st == mk.BULL] = 1.0
            naive[st == mk.BEAR] = -1.0
            out[f"{sym}_naive"] = naive

            if params["signal_source"] == "hmm_agree":
                dlog = np.full(len(close), np.nan)
                dlog[1:] = np.diff(np.log(np.maximum(close, 1e-12)))
                if params["hmm_mode"] == "leaky":
                    hs = mk.hmm_states_leaky(dlog)
                else:
                    hs = mk.hmm_states_causal_fast(
                        dlog, min_bars=int(params["hmm_min_bars"]),
                        refit_every=int(params["hmm_refit_every"]))
                out[f"{sym}_hmm"] = np.where(hs >= 0, hs, np.nan).astype(float)

        return pd.DataFrame(out, index=idx)

    # ── Traduction signal -> poids ──────────────────────────────────────────
    def _leg_weight(self, sig: float, params: dict) -> float:
        cap = float(params["weight_cap"])
        if params["size_mode"] == "binary":
            return cap
        return float(min(cap, abs(sig) * float(params["size_scale"])))

    def _weights_at(self, data: pd.DataFrame, i: int, params: dict,
                    base: list[str]) -> dict[str, float]:
        budget = 1.0 / max(1, len(base))
        min_sig = float(params["min_signal"])
        shorts = bool(params["enable_shorts"])
        src = params["signal_source"]
        w: dict[str, float] = {}

        for sym in base:
            if src == "naive":
                sig = float(data[f"{sym}_naive"].iat[i])
            else:
                sig = float(data[f"{sym}_signal"].iat[i])
                if src == "hmm_agree":
                    col = f"{sym}_hmm"
                    h = float(data[col].iat[i]) if col in data.columns else np.nan
                    if not np.isfinite(h):
                        sig = 0.0
                    else:
                        # « Confirmation subjective et objective » : on ne trade
                        # que si le HMM et les seuils pointent dans le même sens.
                        hdir = 1.0 if h >= mk.BULL else (-1.0 if h <= mk.BEAR else 0.0)
                        sdir = float(np.sign(data[f"{sym}_state"].iat[i] - mk.SIDE)) \
                            if np.isfinite(data[f"{sym}_state"].iat[i]) else 0.0
                        if hdir == 0.0 or hdir != sdir:
                            sig = 0.0

            if not np.isfinite(sig) or abs(sig) < min_sig:
                continue

            lw = self._leg_weight(sig, params) * budget
            if lw <= 0:
                continue

            if sig > 0:
                w[sym] = lw
            elif shorts:
                w[short_symbol(sym)] = lw
            # Mode filtre : un signal baissier signifie « ne pas être exposé ».
            # Sans shorts, c'est du cash — pas une position inverse.
        return w

    # ── Chemin backtest ─────────────────────────────────────────────────────
    def generate_allocations(self, data: Any, params: dict,
                             end_idx: int) -> list[Allocation]:
        base = sorted({c.rsplit("_", 1)[0] for c in data.columns
                       if c.endswith("_signal")})
        n = min(end_idx, len(data))
        warm = self.manifest().warmup_bars
        out: list[Allocation] = []
        prev: Optional[dict[str, float]] = None

        for i in range(warm, n):
            w = self._weights_at(data, i, params, base)
            if prev is not None and _same(prev, w):
                continue
            prev = w
            out.append(Allocation(timestamp=data.index[i], weights=w,
                                  reason=self._reason(data, i, base, params)))
        return out

    def _reason(self, data: pd.DataFrame, i: int, base: list[str],
                params: dict) -> str:
        bits = []
        for sym in base:
            st = data[f"{sym}_state"].iat[i]
            sg = data[f"{sym}_signal"].iat[i]
            lbl = {0.0: "bear", 1.0: "side", 2.0: "bull"}.get(float(st), "?") \
                if np.isfinite(st) else "?"
            bits.append(f"{sym}:{lbl} s={sg:+.3f}")
        return " | ".join(bits)

    # ── Chemin live ─────────────────────────────────────────────────────────
    def on_bar(self, ctx: AllocationContext) -> Optional[Allocation]:
        """R5 : doit décider EXACTEMENT comme `generate_allocations` sur le même
        état de marché. La seule façon fiable de le garantir est de réutiliser le
        même code, pas de le réécrire — d'où le passage par `precompute`.

        Coût assumé : recalcul complet à chaque barre. Sur du D1, c'est
        négligeable, et la conformité vaut plus que la microseconde.
        """
        bars = {s: d for s, d in ctx.bars.items() if not is_short_symbol(s)}
        if not bars:
            return None
        data = self.precompute(bars, self.params)
        if len(data) <= self.manifest().warmup_bars:
            return None
        base = sorted(bars)
        i = len(data) - 1
        w = self._weights_at(data, i, self.params, base)
        return Allocation(timestamp=ctx.now, weights=w,
                          reason=self._reason(data, i, base, self.params))


def _same(a: dict[str, float], b: dict[str, float], tol: float = 1e-9) -> bool:
    if set(a) != set(b):
        return False
    return all(abs(a[k] - b[k]) <= tol for k in a)

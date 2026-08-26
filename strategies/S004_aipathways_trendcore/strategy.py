"""
AI Pathways — Trend Core (bascule QQQ/GLD sur MM200) — `s04_aipathways_trendcore`

Source  : https://www.youtube.com/watch?v=Fb7G5SNpaes
Auteur  : Brendan / AI Pathways
Analyse : research/ANALYSIS.md  (lire le §5 AVANT d'interpréter le moindre chiffre)


LA RÈGLE DE LA SOURCE
---------------------
    Détenir QQQ tant qu'il clôture au-dessus de sa moyenne mobile 200 jours.
    Détenir GLD en dessous.
    Signal à la clôture, exécution à l'ouverture suivante.

Chez nous : QQQ -> NASDAQ (#NAS100), GLD -> XAUUSD, SPY -> SP500.


AVERTISSEMENT — CE MODULE NE PEUT PAS EXPRIMER LA STRATÉGIE
------------------------------------------------------------
C'est le point central, et il est écrit ici pour qu'on ne puisse pas le rater.

« Trend core » est une **bascule d'allocation** : toujours investie, changeant
d'instrument, dont l'UNIQUE condition de sortie est le retournement du régime.

Le contrat de la plateforme (`core/contracts/strategy.py`) modélise une stratégie
**épisodique** : entrée -> invalidation (`stop`, obligatoire par R3) -> objectif.
Le moteur `core/backtest/engine.py` ne connaît que trois sorties : SL, TP, ou fin
de tranche. **Il n'accepte aucun ordre de sortie sur signal.**

Conséquence : il n'existe aucune façon d'exprimer « je sors quand le régime
bascule ». Ce module retient donc l'option A du §5 de l'ANALYSIS :

    * un `Signal` LONG à chaque ENTRÉE en régime ;
    * `stop` = plancher de catastrophe à `stop_atr` × ATR sous l'entrée.
      **Ce n'est PAS l'invalidation de la stratégie.** L'invalidation réelle est
      la bascule de régime, qui n'est pas un niveau de prix. Le stop n'est là que
      parce que R3 l'exige, et il est déclaré comme tel dans `reason`.
    * `target` = None.

Le moteur conservera donc la position **au-delà** de la bascule, jusqu'au stop ou
à la fin de la tranche évaluée. Les résultats du walk-forward mesurent en réalité
« la qualité du moment d'entrée en régime, avec un plancher de désastre », et
**pas** la stratégie de la source.

Ils sont produits et archivés par transparence (R1 doit passer, et la plateforme
doit pouvoir charger la stratégie), mais le verdict s'appuie sur la comptabilité
de courbe d'equity de `backtests/run_analysis.py`, qui est la seule mesure capable
de représenter une position toujours investie qui change d'actif — et la seule
capable de produire les benchmarks buy & hold, qui sont le critère n°1.

Aucun faux stop n'a été « calibré » pour flatter un résultat : `stop_atr` est fixé
large et ne fait pas partie de la grille de recherche.


LES DEUX JAMBES
---------------
Le régime est toujours lu sur `regime_symbol` (NASDAQ par défaut). L'instrument
tradé est celui que le backtester fournit :

    leg="risk"   -> long l'instrument tradé quand NASDAQ est AU-DESSUS de sa MM
    leg="hedge"  -> long l'instrument tradé quand NASDAQ est EN DESSOUS

Lancer la jambe `risk` sur NASDAQ et la jambe `hedge` sur XAUUSD reconstitue les
deux moitiés de la bascule, et donne l'attribution par jambe demandée.


CAUSALITÉ (R1)
--------------
Deux points sensibles, tous deux traités :

1. La moyenne mobile est un `rolling(...).mean()` strict — aucun `center=True`,
   aucun `shift(-1)`. La valeur à l'indice i n'utilise que [i-ma_len+1, i].

2. Le régime vient d'un AUTRE symbole que celui tradé (jambe `hedge`). La série
   de régime est chargée en entier, puis **repliée sur l'index du symbole tradé
   par `reindex(..., method="ffill")`** : la valeur retenue à la date t est la
   dernière clôture de régime **connue à t**. Aucune barre postérieure à t
   n'entre dans le calcul, et `precompute(df[:T])` produit donc exactement les
   mêmes valeurs sur [0, T) que `precompute(df)`. C'est ce que vérifie R1.

Le décalage `shift(1)` appliqué au régime rend le « exécution à l'ouverture
suivante » de la source : on agit sur le régime de la barre PRÉCÉDENTE, jamais
sur celui de la barre en cours.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# Cache des séries de régime. Chargé une fois par (symbole, timeframe) : le
# walk-forward rappelle `precompute` pour chaque cellule de grille.
_REGIME_CACHE: dict[tuple[str, str], pd.DataFrame] = {}


def _load_regime_bars(symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
    key = (symbol, timeframe)
    if key not in _REGIME_CACHE:
        from core.data.source import load_bars  # import tardif : MT5 est lourd
        _REGIME_CACHE[key] = load_bars(symbol, timeframe)
    return _REGIME_CACHE[key]


def _atr(df: pd.DataFrame, n: int) -> pd.Series:
    """ATR de Wilder, strictement causal."""
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


class Strategy(StrategyModule):
    STRATEGY_ID = "s04_aipathways_trendcore"
    MAGIC_NUMBER = 130004

    # ── Déclaration ──────────────────────────────────────────────────────────
    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="AI Pathways - Trend Core (QQQ/GLD regime switch)",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s04_aipathways_trendcore",
            source="https://www.youtube.com/watch?v=Fb7G5SNpaes",
            symbols=["NASDAQ", "XAUUSD"],
            timeframe="D1",
            warmup_bars=260,          # ma_len max (250) + marge ATR
            param_grid={
                # La source n'a qu'UN paramètre réel : la période de la moyenne.
                # `buffer_pct` est une bande morte anti-oscillation ; 0.0 = la
                # règle littérale. 12 cellules -> ~0,6 réussite par pur hasard.
                "ma_len": [100, 150, 200, 250],
                "buffer_pct": [0.0, 0.005, 0.01],
            },
            default_params={
                "ma_len": 200,        # la valeur de la source
                "buffer_pct": 0.0,    # la règle littérale
                "leg": "risk",        # "risk" (au-dessus) | "hedge" (en dessous)
                "regime_symbol": "NASDAQ",
                "stop_atr": 8.0,      # PLANCHER DE CATASTROPHE — pas l'invalidation
                "atr_len": 14,
                "_symbol": "",        # renseigné par le harnais ; cosmétique
            },
            status="RESEARCH",
            notes=("Bascule d'allocation. Le contrat Signal(entry, stop, target) ne "
                   "peut pas exprimer une sortie sur bascule de régime : les "
                   "résultats moteur ne mesurent PAS la stratégie. Voir "
                   "research/ANALYSIS.md §5 et research/VERDICT.md."),
        )

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Régime + ATR. Strictement causal (voir l'en-tête du module)."""
        ma_len = int(params["ma_len"])
        buf = float(params["buffer_pct"])
        reg_sym = str(params["regime_symbol"])

        # Série de clôtures servant au régime.
        if reg_sym and reg_sym != "__self__":
            rb = _load_regime_bars(reg_sym, "D1")
            if rb is None:
                raise RuntimeError(f"série de régime indisponible : {reg_sym}")
            # Repli causal sur l'index tradé : à la date t on ne retient que la
            # dernière clôture de régime CONNUE à t. Rien de postérieur.
            reg_close = rb["close"].reindex(df.index, method="ffill")
        else:
            reg_close = df["close"]

        ma = reg_close.rolling(ma_len, min_periods=ma_len).mean()

        above = reg_close > ma * (1.0 + buf)
        below = reg_close < ma * (1.0 - buf)

        # Régime à état : hors de la bande morte on bascule, dedans on conserve.
        state = np.full(len(df), np.nan)
        cur = np.nan
        av, bv, mv = above.to_numpy(), below.to_numpy(), ma.to_numpy()
        for i in range(len(df)):
            if np.isnan(mv[i]):
                state[i] = np.nan
                continue
            if av[i]:
                cur = 1.0
            elif bv[i]:
                cur = 0.0
            state[i] = cur

        regime = pd.Series(state, index=df.index)

        return {
            "index": df.index,
            "close": df["close"].to_numpy(dtype=float),
            # shift(1) = « signal à la clôture, action ensuite ». On n'agit
            # jamais sur le régime de la barre qu'on est en train de traiter.
            "regime": regime.shift(1).to_numpy(dtype=float),
            "atr": _atr(df, int(params["atr_len"])).to_numpy(dtype=float),
            "symbol": params.get("_symbol", ""),
        }

    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        """Un signal à chaque ENTRÉE dans le régime de la jambe.

        Rien à l'indice >= end_idx ne peut influencer la sortie : la boucle
        s'arrête à end_idx et tous les tableaux sont causaux.
        """
        idx = data["index"]
        close = data["close"]
        regime = data["regime"]
        atr = data["atr"]

        want = 1.0 if str(params["leg"]) == "risk" else 0.0
        stop_atr = float(params["stop_atr"])
        n = min(int(end_idx), len(idx))

        out: list[Signal] = []
        prev_in = False
        for i in range(n):
            r = regime[i]
            if np.isnan(r):
                prev_in = False
                continue
            now_in = (r == want)
            if now_in and not prev_in:
                a = atr[i]
                if np.isnan(a) or a <= 0:
                    prev_in = now_in
                    continue
                entry = float(close[i])
                stop = entry - stop_atr * float(a)
                if stop < entry:
                    out.append(Signal(
                        timestamp=pd.Timestamp(idx[i]).to_pydatetime(),
                        symbol=str(params.get("_symbol", "")) or "?",
                        side=Side.LONG,
                        entry=entry,
                        stop=stop,
                        target=None,
                        reason=(f"régime {'au-dessus' if want else 'en dessous'} "
                                f"MM{int(params['ma_len'])} — stop = PLANCHER DE "
                                f"CATASTROPHE ({stop_atr:g}xATR), PAS l'invalidation : "
                                f"l'invalidation réelle est la bascule de régime, "
                                f"que le moteur ne sait pas exécuter"),
                        confidence=1.0,
                        meta={"leg": params["leg"], "regime": r,
                              "note": "engine cannot exit on regime flip"},
                    ))
            prev_in = now_in

        return out

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5/R6 par construction : appelle littéralement le chemin backtest et
        ne garde que la décision de la barre courante. Il n'existe pas deux
        implémentations pouvant diverger.
        """
        p = dict(self.params)
        p["_symbol"] = ctx.symbol
        data = self.precompute(ctx.bars, p)
        n = len(ctx.bars)
        sigs = self.generate_signals(data, p, n)
        if not sigs:
            return None
        last = sigs[-1]
        if pd.Timestamp(last.timestamp) != pd.Timestamp(ctx.bars.index[n - 1]):
            return None
        return last

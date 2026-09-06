"""
S018 — or, v2 du résidu S011 instruite par la méthode Doud

Source de l'hypothèse : `docs/sources/moneytalk/SYNTHESE.md` (MoneyTalk #29,
Cindy « Doud Trading », 2026-06-13). Lignée : `strategies/S011_legacy_breakout`
version 1.0.0, cellule résiduelle or `adx_min 20 / donchian 40 / er_min 0,00 /
fr_max 1,00 / tp_m 4,0` — celle que `studies/gold_forward/` mesure en forward
scellé depuis le 2026-08-16.

CE QUE CETTE V2 EST, ET CE QU'ELLE N'EST PAS
---------------------------------------------
Elle n'est PAS une modification de la v1. La v1 tourne, scellée, et
`studies/gold_forward/run_forward.py` importe `S011.strategy` en direct : toucher
ce module changerait les signaux d'un test en vol sans qu'aucun hash ne bronche.
S018 est un module séparé, avec son propre magic (130018), et la v1 lui sert de
TÉMOIN.

Cette v2 ajoute **cinq commutateurs** au signal de la v1, et rien d'autre. Chacun
traduit une affirmation datée de la source ; chacun se teste seul.

    entry_mode      D4 — « le marché va venir sur l'équilibre […] récupérer le
                    milieu » (@ 18:08). `breakout` = entrée au close de cassure
                    (v1) ; `equilibrium` = on laisse partir, on entre au repli à
                    50 % de la jambe.
    channel_source  D3 — « un chandelier ça se travaille en structure et non en
                    mèche » (@ 17:52). `extremes` = canal sur high/low (v1) ;
                    `bodies` = canal sur les closes.
    side_mode       D1 — « j'achète beaucoup plus le gold que je le vends. Je
                    vends quasiment jamais » (@ 21:52).
    session_filter  D5 — session US dès 14h + asiatique, jamais Londres
                    (@ 35:35). Heures SERVEUR, calibrées (voir SESSION_*).
    htf_bias        D2 — « c'est impossible que je vienne sur une journée […] où
                    j'ai pas déjà mon biais directionnel » (@ 23:32). Le biais
                    réel est macro (dollar, Fed) et n'est pas dans nos données :
                    la porte journalière en est l'ombre mécanique.

LA CELLULE NEUTRE EST LA V1, AU SIGNAL PRÈS
---------------------------------------------
    entry_mode=breakout · channel_source=extremes · side_mode=both
    · session_filter=off · htf_bias=off

produit **exactement** les signaux de S011 avec les paramètres scellés.
`test_strategy.py::test_cellule_neutre_reproduit_la_v1` le vérifie sur les 30 000
barres réelles de XAUUSD H1, signal par signal. C'est ce qui rend chaque
commutateur mesurable : tout écart observé vient du commutateur, pas d'une
réécriture.

Deux conséquences de cette exigence, assumées :
  * les indicateurs (ATR, RSI, ADX/±DI) sont IMPORTÉS de S011, pas recopiés —
    une réimplémentation « équivalente » aurait dérivé au troisième chiffre ;
  * le filtre de régime ER/failed-rate de la v1 n'est pas repris : la cellule
    scellée le désactive (`er_min=0,00`, `fr_max=1,00`), et ces deux valeurs le
    rendent identiquement inopérant (`x < 0` et `x > 1` sont toujours faux).
    Le `warmup_bars` de 400 est néanmoins conservé, pour que les deux versions
    commencent à la même barre.

CE QUE LA SOURCE PROPOSE ET QUE CETTE CLASSE NE FERA PAS
----------------------------------------------------------
Sorties partielles TP1/TP2/TP3 (@ 29:03), stop suiveur (@ 29:51), break-even qui
finance les frais (@ 30:04) : le moteur commun ne déplace pas de stop et ne
connaît qu'une sortie unique. R9 interdit d'en écrire un autre — c'est la limite
déjà documentée pour la v1 (S011 `research/ANALYSIS.md` § 4). Tickets ouverts.

Absence de stop (@ 12:31) et renforcement à la baisse (@ 39:07) : refusés. R3
rend `Signal.stop` obligatoire, et la source elle-même chiffre le coût de cette
règle à −80 000 € en une séance (@ 32:30).
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# Indicateurs de la v1, importés et non recopiés : l'égalité de la cellule
# neutre avec S011 doit être une propriété du code, pas une intention.
# S011 est figée par le scellé de `studies/gold_forward/` — cette dépendance
# pointe donc vers un module qui ne peut pas bouger sous nos pieds.
from strategies.S011_legacy_breakout.strategy import (  # noqa: E402
    _adx, _atr, _rsi, ATR_SMA_PERIOD,
)

# ── Heures de session, en heure SERVEUR ──────────────────────────────────────
# `core/data/source.calibrate_server_offset` mesuré sur XAUUSD H1 (30 024 barres,
# 2021-08 → 2026-09) : pic de volatilité à l'heure serveur 15, donc
# offset = GMT+2. Le profil mesuré (amplitude moyenne en pips par heure) :
#     14h→1400  15h→1495  16h→1446  17h→1083     ← bloc US
#     23h→1217   2h→940    3h→1007                ← retour du soir + Asie
#      9h→885   10h→822   11h→728   12h→755       ← Londres, le creux relatif
# Les fenêtres ci-dessous sont celles que la source déclare (@ 35:35) ; le fait
# qu'elles tombent sur les heures les plus actives de l'or est une observation,
# pas une justification — c'est précisément ce que le test doit trancher.
SESSION_US = (14, 15, 16, 17, 18)
SESSION_ASIA = (23, 0, 1, 2, 3)
SESSION_DOUD = frozenset(SESSION_US + SESSION_ASIA)

# Part de la jambe où l'on guette le repli. 0,5 = « le milieu » (@ 18:08).
# Ce n'est pas un réglage : c'est l'hypothèse. La faire varier reviendrait à
# tester un autre énoncé que celui de la source.
EQUILIBRIUM_RATIO = 0.5

# Durée de validité d'un setup en attente de repli, en barres H1.
# 24 barres = une journée : au-delà, la « jambe » de la source n'est plus la
# jambe du jour. Fixé, hors grille, pour la même raison qu'EQUILIBRIUM_RATIO.
PULLBACK_MAX_BARS = 24

# Période de l'EMA journalière du biais HTF (D2), en JOURS.
HTF_EMA_DAYS = 20

WARMUP_BARS = 400          # aligné sur la v1 — comparabilité, pas besoin technique


# ─────────────────────────────────────────────────────────────────────────────
# Porte de biais journalier (D2)
# ─────────────────────────────────────────────────────────────────────────────

def _daily_bias(df: pd.DataFrame, ema_days: int = HTF_EMA_DAYS) -> np.ndarray:
    """+1 si la journée PRÉCÉDENTE a clôturé au-dessus de son EMA, −1 sinon.

    Causalité : la série journalière est construite par `resample('1D').last()`
    puis **décalée d'un jour** avant d'être reportée sur les barres H1. À
    n'importe quelle barre du jour J, la valeur lue est celle du jour J−1,
    complètement close. Aucune barre du jour J n'entre dans sa propre porte —
    c'est le point qui casse si on retire le `shift(1)`.

    Retourne 0 tant que l'EMA n'a pas assez d'historique : 0 = pas d'information,
    et l'appelant traite 0 comme « aucune direction autorisée » seulement si la
    porte est active.
    """
    close = df["close"]
    daily = close.resample("1D").last().dropna()
    if len(daily) < 2:
        return np.zeros(len(df))
    ema = daily.ewm(span=ema_days, adjust=False).mean()
    sign = np.sign(daily - ema)
    sign[ema.isna()] = 0.0
    prev = sign.shift(1)                    # ← la journée close, jamais la courante
    mapped = prev.reindex(close.index, method="ffill")
    return mapped.fillna(0.0).to_numpy(dtype=float)


# ─────────────────────────────────────────────────────────────────────────────
# Stratégie
# ─────────────────────────────────────────────────────────────────────────────

class Strategy(StrategyModule):
    STRATEGY_ID = "S018_gold_doud_v2"
    MAGIC_NUMBER = 130018

    _MAX_CACHE = 8

    def __init__(self, params: Optional[dict] = None):
        super().__init__(params)
        self._base: dict[tuple, Any] = {}
        self._chan: dict[tuple, Any] = {}
        self._bias: dict[tuple, Any] = {}

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Or v2 — cassure S011 + équilibre (méthode Doud)",
            version="2.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:S018_gold_doud_v2",
            source="docs/sources/moneytalk/ (MoneyTalk #29, Doud Trading) ; "
                   "lignée strategies/S011_legacy_breakout v1.0.0",
            symbols=["XAUUSD"],
            timeframe="H1",
            warmup_bars=WARMUP_BARS,
            # 2 × 2 × 2 × 2 × 2 = 32 cellules. À 5 %, ≈ 1,6 « pass » attendue
            # par pur hasard : tout résultat isolé se lit contre ce chiffre.
            # La cellule (breakout, extremes, both, off, off) EST la v1.
            param_grid={
                "entry_mode":     ["breakout", "equilibrium"],
                "channel_source": ["extremes", "bodies"],
                "side_mode":      ["both", "long_only"],
                "session_filter": ["off", "doud"],
                "htf_bias":       ["off", "daily_ema"],
            },
            default_params={
                # ── commutateurs v2 : défaut = comportement v1 ──────────────
                "entry_mode": "breakout",
                "channel_source": "extremes",
                "side_mode": "both",
                "session_filter": "off",
                "htf_bias": "off",
                # ── socle figé, valeurs de la cellule scellée du forward v1 ──
                "donchian": 40,
                "adx_min": 20.0,
                "tp_m": 4.0,
                "sl_m": 1.5,
                "atr_vol_ratio": 0.8,
                "adx_rising_lookback": 5,
                "rsi_long_max": 75.0,
                "rsi_short_min": 25.0,
            },
            status="RESEARCH",
            notes=("v2 du résidu or de S011. Cinq commutateurs issus de "
                   "docs/sources/moneytalk/SYNTHESE.md § 2 (D1-D5). Cellule "
                   "neutre = v1 au signal près, vérifiée par test."),
        )

    # ── Caches ───────────────────────────────────────────────────────────────
    @staticmethod
    def _data_key(df: pd.DataFrame) -> tuple:
        return (len(df),
                int(df.index[0].value),
                int(df.index[-1].value),
                float(df["close"].iloc[-1]))

    @classmethod
    def _put(cls, cache: dict, key, value):
        if len(cache) >= cls._MAX_CACHE:
            cache.pop(next(iter(cache)))
        cache[key] = value
        return value

    def _base_indicators(self, df: pd.DataFrame, dkey: tuple):
        if dkey in self._base:
            return self._base[dkey]
        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        atr = _atr(high, low, close)
        atr_sma = pd.Series(atr).rolling(ATR_SMA_PERIOD).mean().to_numpy()
        rsi = _rsi(close)
        adx, pdi, ndi = _adx(high, low, close)
        return self._put(self._base, dkey,
                         (high, low, close, atr, atr_sma, rsi, adx, pdi, ndi))

    def _channel(self, df: pd.DataFrame, dkey: tuple, period: int, source: str):
        """Canal de Donchian décalé d'une barre.

        `extremes` : max(high) / min(low) — la v1.
        `bodies`   : max(close) / min(close) — « la structure, pas la mèche »
                     (@ 17:52). Un canal de corps est mécaniquement plus étroit,
                     donc plus souvent cassé : l'effet mesuré mêlera qualité du
                     niveau et fréquence des signaux. C'est une propriété de
                     l'hypothèse, pas un défaut du test — VERDICT § comptera les
                     trades des deux côtés.
        """
        key = (dkey, period, source)
        if key in self._chan:
            return self._chan[key]
        if source == "bodies":
            up, dn = df["close"], df["close"]
        elif source == "extremes":
            up, dn = df["high"], df["low"]
        else:
            raise ValueError(f"channel_source inconnu : {source!r}")
        dh = up.rolling(period, min_periods=period).max().shift(1).to_numpy()
        dl = dn.rolling(period, min_periods=period).min().shift(1).to_numpy()
        return self._put(self._chan, key, (dh, dl))

    def _bias_series(self, df: pd.DataFrame, dkey: tuple, mode: str) -> np.ndarray:
        if mode == "off":
            return np.zeros(len(df))
        if mode != "daily_ema":
            raise ValueError(f"htf_bias inconnu : {mode!r}")
        key = (dkey, mode)
        if key in self._bias:
            return self._bias[key]
        return self._put(self._bias, key, _daily_bias(df))

    # ── Précalcul ────────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Indicateurs + liste complète des signaux étiquetés par barre d'ENTRÉE.

        Comme la v1, la valeur de retour est un `DataFrame` : la seconde couche
        de `core/validation/causality.py` compare alors aussi les indicateurs
        entre passe complète et passe tronquée, et pas seulement les signaux.
        Le mode `equilibrium` porte un état de balayage (setup en attente) : je
        préfère être vérifié qu'exempté.
        """
        dkey = self._data_key(df)
        (high, low, close, atr, atr_sma, rsi,
         adx, pdi, ndi) = self._base_indicators(df, dkey)

        entry_mode = str(params["entry_mode"])
        channel_source = str(params["channel_source"])
        side_mode = str(params["side_mode"])
        session_filter = str(params["session_filter"])
        htf_bias = str(params["htf_bias"])
        if entry_mode not in ("breakout", "equilibrium"):
            raise ValueError(f"entry_mode inconnu : {entry_mode!r}")
        if side_mode not in ("both", "long_only"):
            raise ValueError(f"side_mode inconnu : {side_mode!r}")
        if session_filter not in ("off", "doud"):
            raise ValueError(f"session_filter inconnu : {session_filter!r}")

        dh, dl = self._channel(df, dkey, int(params["donchian"]), channel_source)
        bias = self._bias_series(df, dkey, htf_bias)

        n = len(df)
        idx = df.index
        lb = int(params["adx_rising_lookback"])
        adx_min = float(params["adx_min"])
        vol_ratio = float(params["atr_vol_ratio"])
        sl_m = float(params["sl_m"])
        tp_m = float(params["tp_m"])
        rsi_hi = float(params["rsi_long_max"])
        rsi_lo = float(params["rsi_short_min"])

        def _pack(sig_list, cols):
            out = pd.DataFrame(cols, index=idx)
            out.attrs["signals"] = sig_list
            return out

        base_cols = {"atr": atr, "adx": adx, "dh_prev": dh, "dl_prev": dl,
                     "bias": bias}
        if n <= WARMUP_BARS + lb + 1:
            return _pack([], base_cols)

        adx_back = np.full(n, np.nan)
        adx_back[lb:] = adx[:-lb]

        finite = (np.isfinite(atr) & (atr > 0)
                  & np.isfinite(atr_sma) & (atr_sma > 0)
                  & np.isfinite(dh) & np.isfinite(dl)
                  & np.isfinite(adx) & np.isfinite(adx_back))

        with np.errstate(invalid="ignore"):
            vol_ok = atr > atr_sma * vol_ratio
            trend_ok = (adx > adx_min) & (adx > adx_back)
            up_break = close > dh
            dn_break = ~up_break & (close < dl)      # `elif` de la v1
            long_ok = up_break & (pdi > ndi) & (rsi < rsi_hi)
            short_ok = dn_break & (ndi > pdi) & (rsi > rsi_lo)

        gate = finite & vol_ok & trend_ok
        gate[:max(WARMUP_BARS, lb + 1)] = False

        # ── Portes d'ENTRÉE (D1/D2/D5) ──────────────────────────────────────
        # Évaluées à la barre où l'ordre part — la barre de cassure en mode
        # `breakout`, la barre de repli en mode `equilibrium`. C'est la lecture
        # opératoire de la source : le biais et la session conditionnent le
        # moment où l'on entre, pas le moment où l'on remarque le mouvement.
        hours = idx.hour.to_numpy()
        session_ok = (np.ones(n, dtype=bool) if session_filter == "off"
                      else np.isin(hours, list(SESSION_DOUD)))
        if htf_bias == "off":
            bias_long = bias_short = np.ones(n, dtype=bool)
        else:
            bias_long, bias_short = bias > 0, bias < 0
        allow_long = session_ok & bias_long
        allow_short = (session_ok & bias_short
                       & (side_mode != "long_only"))

        signals: list[tuple[int, Signal]] = []
        dec_side = np.zeros(n)
        dec_stop = np.full(n, np.nan)
        dec_target = np.full(n, np.nan)
        symbol = getattr(self, "_symbol", "UNKNOWN")

        def _emit(entry_idx: int, is_long: bool, reason: str, meta: dict):
            a = float(atr[entry_idx])
            entry = float(close[entry_idx])
            if not np.isfinite(a) or a <= 0:
                return
            stop = entry - sl_m * a if is_long else entry + sl_m * a
            target = entry + tp_m * a if is_long else entry - tp_m * a
            if stop == entry:
                return                       # ATR nul : rien à risquer
            signals.append((entry_idx, Signal(
                timestamp=idx[entry_idx], symbol=symbol,
                side=Side.LONG if is_long else Side.SHORT,
                entry=entry, stop=stop, target=target,
                reason=reason, meta=meta)))
            dec_side[entry_idx] = 1.0 if is_long else -1.0
            dec_stop[entry_idx] = stop
            dec_target[entry_idx] = target

        don = int(params["donchian"])

        if entry_mode == "breakout":
            # ── Chemin v1 : on entre au close de la cassure ──────────────────
            longs = np.flatnonzero(gate & long_ok & allow_long)
            shorts = np.flatnonzero(gate & short_ok & allow_short)
            for i, is_long in sorted([(int(k), True) for k in longs]
                                     + [(int(k), False) for k in shorts]):
                sens = "haute" if is_long else "basse"
                _emit(i, is_long,
                      (f"cassure {sens} Donchian{don} + ADX {adx[i]:.1f} croissant "
                       f"+ DI confirmé + ATR {atr[i] / atr_sma[i]:.2f}× sa SMA50"),
                      {"adx": round(float(adx[i]), 2),
                       "risk": sl_m * float(atr[i])})
        else:
            # ── Chemin v2 : on laisse partir, on entre au retour au milieu ───
            #
            # À la cassure i, la jambe va du niveau de canal opposé (le « plus
            # bas » que l'impulsion a laissé) à l'extension atteinte depuis.
            # L'équilibre se RECALCULE à chaque barre tant que l'impulsion
            # s'étend — c'est le milieu du mouvement réel, pas celui de la
            # première barre. Toutes les valeurs lues à la barre j sont
            # d'indice ≤ j : la causalité tient sans décalage particulier.
            #
            # Un seul setup à la fois : tant qu'un repli est attendu, les
            # cassures suivantes sont ignorées. Règle déterministe, sans quoi
            # une impulsion prolongée empilerait N setups quasi identiques.
            brk_long = gate & long_ok
            brk_short = gate & short_ok
            i = max(WARMUP_BARS, lb + 1)
            while i < n:
                is_long = bool(brk_long[i])
                if not is_long and not brk_short[i]:
                    i += 1
                    continue

                anchor = float(dl[i]) if is_long else float(dh[i])
                ext = float(high[i]) if is_long else float(low[i])
                last = min(n - 1, i + PULLBACK_MAX_BARS)
                j = i + 1
                # `resolved` — barre où reprendre le balayage. Toujours affectée :
                # par un des deux `break`, ou par la clause `else` de la boucle.
                while j <= last:
                    ext = max(ext, float(high[j])) if is_long else min(ext, float(low[j]))
                    eq = anchor + EQUILIBRIUM_RATIO * (ext - anchor)

                    # Structure défaite : la jambe entière est annulée, le setup
                    # meurt sans entrée.
                    if (is_long and close[j] < anchor) or (not is_long and close[j] > anchor):
                        resolved = j + 1
                        break

                    touched = (low[j] <= eq) if is_long else (high[j] >= eq)
                    if touched:
                        allowed = allow_long[j] if is_long else allow_short[j]
                        if allowed:
                            sens = "haute" if is_long else "basse"
                            _emit(j, is_long,
                                  (f"repli à l'équilibre {EQUILIBRIUM_RATIO:.0%} de la "
                                   f"jambe (cassure {sens} Donchian{don} {j - i} barres "
                                   f"plus tôt, extension {abs(ext - anchor):.2f})"),
                                  {"breakout_idx": i,
                                   "bars_waited": j - i,
                                   "equilibrium": round(eq, 3),
                                   "leg_anchor": round(anchor, 3),
                                   "leg_extension": round(ext, 3),
                                   "adx": round(float(adx[i]), 2)})
                        resolved = j + 1
                        break
                    j += 1
                else:
                    resolved = last + 1          # expiration sans repli
                i = max(resolved, i + 1)

        cols = dict(base_cols)
        cols.update({"atr_sma": atr_sma, "rsi": rsi, "pdi": pdi, "ndi": ndi,
                     "dec_side": dec_side, "dec_stop": dec_stop,
                     "dec_target": dec_target})
        return _pack(signals, cols)

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        return [s for (i, s) in data.attrs["signals"] if i < end_idx]

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5 par construction : le live appelle littéralement le code du
        backtest et ne retient que la décision de la barre courante."""
        bars = ctx.bars
        if len(bars) < WARMUP_BARS + 10:
            return None
        self._symbol = ctx.symbol
        data = self.precompute(bars, self.params)
        last = len(bars) - 1
        for i, sig in data.attrs["signals"]:
            if i == last:
                return sig
        return None

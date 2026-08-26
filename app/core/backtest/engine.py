"""
MOTEUR DE BACKTEST COMMUN
==========================

Simule l'exécution d'une liste de `Signal` sur des barres OHLC. Il ne sait rien
des stratégies : il reçoit des décisions (entrée, stop, cible) et les exécute.

C'est la règle R9 : aucune stratégie n'écrit sa propre boucle de backtest. Sinon
les chiffres ne sont pas comparables entre stratégies, et chaque nouvelle
implémentation réintroduit ses propres bugs d'exécution.

MODÈLE D'EXÉCUTION — volontairement pessimiste
-----------------------------------------------
1. Entrée au close de la barre de signal, spread payé intégralement.
2. Stop touché si le prix du stop est DANS [low, high] de la barre. Pas de
   modèle « bruit » indulgent : si la barre a traversé le stop, il est pris.
3. **Si stop ET cible sont dans la même barre, le stop l'emporte.** On ne sait
   pas dans quel ordre le prix les a visités ; l'hypothèse défavorable est la
   seule honnête.
4. Sortie au prix exact du stop ou de la cible, moins le coût de bord.
5. Coût de bord = demi-spread + slippage, payé aux DEUX extrémités et toujours
   défavorable. `slippage_pips` vaut 0 par défaut (rétrocompatibilité), mais
   toute évaluation destinée à une décision de production doit le renseigner :
   sans lui, les résultats sont optimistes d'un montant inconnu.

LE PIÈGE DE `end_idx` — lire avant de modifier
-----------------------------------------------
Une position encore ouverte à `end_idx` est valorisée à `closes[end_idx - 1]`,
la dernière barre de la TRANCHE ÉVALUÉE.

Une version antérieure de ce projet utilisait `closes[-1]` — la dernière barre
du tableau COMPLET. La boucle respectait `end_idx`, mais la clôture résiduelle
non. Chaque tranche d'entraînement valorisait donc son trade ouvert à un prix
futur. Le bug a faussé des mois de walk-forward sans jamais lever d'alerte.

`core/validation/causality.py` teste cet invariant. Ne le contournez pas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import Side, Signal


@dataclass
class InstrumentSpec:
    """Caractéristiques broker. Vient du catalogue, jamais codé dans une stratégie."""
    symbol: str
    pip: float
    spread_pips: float
    max_spread_pips: float
    pip_value_per_lot: float = 10.0   # valeur d'1 pip pour 1 lot, devise du compte
    slippage_pips: float = 0.0        # glissement subi, TOUJOURS defavorable

    # Le slippage est l'ecart entre le prix attendu et le prix reellement obtenu.
    # Il est structurellement defavorable : on est servi moins bien que prevu,
    # jamais mieux. Laisse a 0 par defaut pour ne pas fausser les resultats
    # historiques, mais TOUTE evaluation destinee a une decision de production
    # doit le renseigner. Ordres de grandeur observes : 0,2-0,5 pip en FX
    # liquide hors news, davantage sur indices CFD et en ouverture de seance.


@dataclass
class ExecutedTrade:
    signal_time: datetime
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: Side
    entry_price: float
    exit_price: Optional[float]
    stop_price: float
    target_price: Optional[float]
    exit_reason: str            # SL | TP | EOD | RESIDUAL
    risk_distance: float
    pnl_r: float                # P&L en multiples de risque — indépendant du sizing
    bars_held: int
    reason: str = ""

    @property
    def is_win(self) -> bool:
        return self.pnl_r > 0


@dataclass
class BacktestResult:
    trades: list[ExecutedTrade] = field(default_factory=list)
    skipped_spread: int = 0
    skipped_cooldown: int = 0
    skipped_open: int = 0

    # ── Métriques. TOUJOURS lues avec n_trades sous les yeux ────────────────
    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def total_r(self) -> float:
        return float(sum(t.pnl_r for t in self.trades))

    @property
    def win_rate(self) -> Optional[float]:
        if not self.trades:
            return None
        return 100.0 * sum(1 for t in self.trades if t.is_win) / len(self.trades)

    @property
    def profit_factor(self) -> Optional[float]:
        gains = sum(t.pnl_r for t in self.trades if t.pnl_r > 0)
        losses = abs(sum(t.pnl_r for t in self.trades if t.pnl_r < 0))
        if not losses:
            return None if not gains else float("inf")
        return gains / losses

    @property
    def max_drawdown_r(self) -> float:
        if not self.trades:
            return 0.0
        eq = np.cumsum([t.pnl_r for t in self.trades])
        peak = np.maximum.accumulate(eq)
        return float(np.max(peak - eq)) if len(eq) else 0.0

    def summary(self) -> dict:
        """Toujours accompagné de n_trades : une métrique sans effectif ne veut
        rien dire. Un « strict pass » sur 19 trades a déjà été pris pour un
        succès sur ce projet — l'IC 95 % du win rate contenait le seuil de
        rentabilité."""
        return {
            "n_trades": self.n_trades,
            "total_r": round(self.total_r, 2),
            "win_rate": round(self.win_rate, 1) if self.win_rate is not None else None,
            "profit_factor": (round(self.profit_factor, 2)
                              if self.profit_factor not in (None, float("inf")) else None),
            "max_dd_r": round(self.max_drawdown_r, 2),
            "skipped_spread": self.skipped_spread,
            "skipped_cooldown": self.skipped_cooldown,
            "skipped_open": self.skipped_open,
        }


def run(
    signals: list[Signal],
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    end_idx: Optional[int] = None,
    *,
    max_positions: int = 1,
    cooldown_bars: int = 2,
    cb_losses: int = 3,
    cb_cooldown_bars: int = 24,
    max_hold_bars: Optional[int] = None,
) -> BacktestResult:
    """Exécute les signaux sur les barres.

    `end_idx` : n'évalue que [0, end_idx). Rien au-delà ne doit influencer le
    résultat — c'est l'invariant testé par R1.

    Le P&L est exprimé en **R** (multiples du risque). Le moteur ignore
    délibérément la taille de position : c'est le rôle de `core/risk/`. Un
    résultat en R reste valable quelle que soit l'allocation ultérieure.
    """
    n = len(bars) if end_idx is None else min(end_idx, len(bars))
    if n <= 1:
        return BacktestResult()

    idx = bars.index
    opens = bars["open"].to_numpy()
    highs = bars["high"].to_numpy()
    lows = bars["low"].to_numpy()
    closes = bars["close"].to_numpy()

    pos_at = {idx[i]: i for i in range(n)}
    half_spread = spec.spread_pips * spec.pip / 2.0
    slip = spec.slippage_pips * spec.pip
    # Cout defavorable paye a CHAQUE extremite : moitie du spread + glissement.
    edge_cost = half_spread + slip

    result = BacktestResult()
    open_until_bar = -1
    cooldown_until = -1
    consecutive_losses = 0

    for sig in sorted(signals, key=lambda s: s.timestamp):
        i = pos_at.get(pd.Timestamp(sig.timestamp))
        if i is None or i >= n - 1:
            continue  # signal hors tranche, ou pas de barre suivante pour l'exécuter

        if spec.spread_pips > spec.max_spread_pips:
            result.skipped_spread += 1
            continue
        if i < cooldown_until:
            result.skipped_cooldown += 1
            continue
        if i < open_until_bar and max_positions <= 1:
            result.skipped_open += 1
            continue

        long = sig.side == Side.LONG
        entry = float(sig.entry) + (edge_cost if long else -edge_cost)
        stop = float(sig.stop)
        target = float(sig.target) if sig.target is not None else None
        risk = abs(entry - stop)
        if risk <= 0:
            continue

        exit_price = exit_reason = exit_at = None
        held = 0

        limit = n if max_hold_bars is None else min(n, i + 1 + max_hold_bars)
        for j in range(i + 1, limit):
            held = j - i
            hi, lo, op = float(highs[j]), float(lows[j]), float(opens[j])

            # Test UNILATÉRAL, pas d'encadrement.
            #
            # Une version antérieure exigeait `lo <= stop <= hi` : le stop ne se
            # remplissait que si la barre l'ENCADRAIT. Un gap de séance qui
            # saute par-dessus ne déclenchait donc jamais rien, et la position
            # restait ouverte indéfiniment. Cas mesuré sur DAX : un SHORT du
            # 2022-12-30 dont le stop tombait dans le gap du week-end est resté
            # tenu 12 875 barres pour -210,59 R, en bloquant au passage ~270
            # trades ultérieurs. Trouvé par l'agent s11.
            #
            # Un stop est franchi dès que le prix l'atteint OU le dépasse.
            if long:
                hit_sl = lo <= stop
                hit_tp = target is not None and hi >= target
                # Si la barre OUVRE déjà au-delà du stop, on est exécuté à
                # l'ouverture, donc plus bas que le stop. Le gap se paie.
                sl_fill = min(stop, op) if hit_sl else None
            else:
                hit_sl = hi >= stop
                hit_tp = target is not None and lo <= target
                sl_fill = max(stop, op) if hit_sl else None

            # Ordre de visite inconnu dans la barre -> hypothèse défavorable.
            if hit_sl:
                exit_price, exit_reason, exit_at = sl_fill, "SL", idx[j]
                break
            if hit_tp:
                # La cible, elle, ne profite PAS du gap : on la remplit à son
                # prix même si la barre a ouvert au-delà. Asymétrie assumée,
                # cohérente avec le pessimisme du reste du moteur.
                exit_price, exit_reason, exit_at = target, "TP", idx[j]
                break

        if exit_price is None:
            # Deux cas distincts, à ne surtout pas confondre :
            #
            #   limit >= n   la position court encore à la COUPURE de tranche.
            #                On la valorise à closes[n-1], dernière barre
            #                évaluée. Jamais closes[-1].
            #
            #   limit <  n   la position a atteint max_hold_bars AVANT la fin de
            #                tranche. Elle doit être valorisée à sa propre barre
            #                d'expiration, closes[limit-1] — PAS à la fin de
            #                tranche, qui est dans son futur.
            #
            # Une version antérieure utilisait last_close dans les deux cas :
            # même famille de bug que le closes[-1] historique, en plus discret
            # car latent tant que max_hold_bars n'est pas utilisé. Trouvé par
            # l'agent s04 en relecture. `held` était faux du même coup.
            expired = limit < n
            exit_bar = (limit - 1) if expired else (n - 1)
            exit_price = float(closes[exit_bar])
            exit_reason = "EOD" if expired else "RESIDUAL"
            exit_at = idx[exit_bar]
            held = exit_bar - i

        gross = (exit_price - entry) if long else (entry - exit_price)
        gross -= edge_cost            # spread + slippage payes aussi a la sortie
        pnl_r = gross / risk

        result.trades.append(ExecutedTrade(
            signal_time=pd.Timestamp(sig.timestamp).to_pydatetime(),
            entry_time=pd.Timestamp(idx[i]).to_pydatetime(),
            exit_time=pd.Timestamp(exit_at).to_pydatetime() if exit_at is not None else None,
            symbol=spec.symbol, side=sig.side,
            entry_price=entry, exit_price=exit_price,
            stop_price=stop, target_price=target,
            exit_reason=exit_reason, risk_distance=risk,
            pnl_r=pnl_r, bars_held=held, reason=sig.reason,
        ))

        open_until_bar = i + held
        cooldown_until = open_until_bar + cooldown_bars

        # Circuit breaker : protège contre les séries noires, pas contre une perte.
        if pnl_r < 0:
            consecutive_losses += 1
            if consecutive_losses >= cb_losses:
                cooldown_until = open_until_bar + cb_cooldown_bars
                consecutive_losses = 0
        else:
            consecutive_losses = 0

    return result

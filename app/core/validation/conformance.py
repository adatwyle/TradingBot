"""
R5 — CONFORMITÉ BACKTEST / LIVE
================================

Vérifie que les deux chemins d'une stratégie rendent la **même décision** sur le
même état de marché :

    generate_signals(precompute(df), params, T)   # chemin backtest, vectorisé
        ==
    on_bar(ctx)  pour chaque barre                # chemin live, une barre à la fois

POURQUOI CE MODULE EXISTE
-------------------------
C'est la première cause de « ça marchait en backtest ». Les deux chemins sont
écrits séparément — l'un pour la vitesse, l'autre pour le temps réel — et rien
n'oblige structurellement à ce qu'ils s'accordent. Un décalage d'un indice, une
condition évaluée sur la barre en cours au lieu de la précédente, et le système
qui part en production n'est pas celui qui a été validé.

Ce module manquait. Chaque `CLAUDE.md` de stratégie ordonne pourtant de le
lancer, et trois agents successifs ont dû noter « R5 non exécutable ». Une règle
qu'on ne peut pas exécuter n'est pas une règle.

CE QUE CE TEST NE PROUVE PAS
----------------------------
Si `on_bar()` se contente d'appeler `generate_signals()`, la conformité est une
**garantie structurelle**, pas une preuve : les deux chemins ne peuvent pas
diverger parce qu'il n'y en a qu'un. C'est légitime et même recommandé, mais il
faut le dire — sinon un « R5 PASSÉ » se lit comme une vérification indépendante
alors qu'il n'y en a pas eu. Le rapport le signale explicitement.

Ce test suppose aussi R1 acquis. Il compare la décision de `on_bar()` à la barre
i, qui ne voit que `[0, i]`, à celle de `generate_signals()` sur l'historique
complet. Si la stratégie fuit, les deux peuvent différer sans que `on_bar()` ait
tort. **Lancer R1 d'abord.**

USAGE
-----
    python -m core.validation.conformance --strategy s10_legacy_meanrev
    python -m core.validation.conformance --all --save
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.contracts.strategy import MarketContext, Signal, StrategyModule  # noqa: E402

# Nombre de barres réellement rejouées barre par barre. Le chemin live est
# O(n²) — chaque appel recalcule les indicateurs sur un historique croissant —
# donc on échantillonne la fin de l'historique plutôt que tout relire.
DEFAULT_BARS = 400


@dataclass
class Divergence:
    index: int
    timestamp: pd.Timestamp
    backtest: Optional[Signal]
    live: Optional[Signal]

    def render(self) -> str:
        def fmt(s):
            if s is None:
                return "aucun signal"
            t = f" cible {s.target:.5f}" if s.target is not None else ""
            return f"{s.side.value} entrée {s.entry:.5f} stop {s.stop:.5f}{t}"
        return (f"    barre {self.index} ({self.timestamp})\n"
                f"      backtest : {fmt(self.backtest)}\n"
                f"      live     : {fmt(self.live)}")


@dataclass
class ConformanceReport:
    strategy_id: str
    symbol: str
    bars_replayed: int
    n_backtest: int                 # signaux émis par le chemin backtest
    n_live: int                     # signaux émis par le chemin live
    divergences: list[Divergence] = field(default_factory=list)
    delegates: bool = False         # on_bar() appelle generate_signals()
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and not self.divergences

    def render(self) -> str:
        L = [f"R5 CONFORMITÉ — {self.strategy_id} / {self.symbol}"]
        L.append("=" * 62)

        if self.error:
            L.append(f"  ERREUR : {self.error}")
            return "\n".join(L)

        L.append(f"  {self.bars_replayed} barres rejouées barre par barre")
        L.append(f"  signaux : {self.n_backtest} en backtest, {self.n_live} en live")

        if self.delegates:
            L.append("")
            L.append("  NOTE : on_bar() délègue à generate_signals(). La conformité est")
            L.append("  ici une garantie STRUCTURELLE — il n'y a qu'un chemin de décision,")
            L.append("  donc rien ne peut diverger. C'est un bon choix de conception, mais")
            L.append("  ce test ne constitue pas une vérification indépendante.")

        L.append("")
        if not self.divergences:
            L.append(f"  RÉSULTAT : CONFORME — 0 divergence sur {self.bars_replayed} barres")
        else:
            n = len(self.divergences)
            L.append(f"  RÉSULTAT : DIVERGENT — {n} désaccord(s) "
                     f"({100.0 * n / max(self.bars_replayed, 1):.2f} % des barres)")
            L.append("")
            for d in self.divergences[:10]:
                L.append(d.render())
            if n > 10:
                L.append(f"    … et {n - 10} autre(s)")
            L.append("")
            L.append("  Le système qui partirait en production n'est pas celui qui a été")
            L.append("  validé. Corriger avant toute promotion en PAPER.")
        return "\n".join(L)


def _key(s: Optional[Signal]) -> Optional[tuple]:
    """Identité d'une décision. On compare l'intention — sens et niveaux — pas
    le texte de `reason`, qui peut légitimement différer entre les deux chemins."""
    if s is None:
        return None
    return (s.side,
            round(float(s.entry), 10),
            round(float(s.stop), 10),
            None if s.target is None else round(float(s.target), 10))


def _delegates(strategy: StrategyModule) -> bool:
    """`on_bar` se contente-t-il d'appeler `generate_signals` ?"""
    try:
        src = inspect.getsource(type(strategy).on_bar)
    except (OSError, TypeError):
        return False
    return "generate_signals" in src


def check(strategy: StrategyModule, df: pd.DataFrame, symbol: str,
          n_bars: int = DEFAULT_BARS,
          spread: float = 0.0) -> ConformanceReport:
    """Rejoue les deux chemins sur la queue de l'historique et compare."""
    m = strategy.manifest()
    n = len(df)
    start = max(int(m.warmup_bars) + 1, n - int(n_bars))
    if start >= n:
        return ConformanceReport(
            strategy.STRATEGY_ID, symbol, 0, 0, 0,
            error=f"historique trop court : {n} barres pour un warmup de {m.warmup_bars}")

    # Chemin backtest : une passe, tout l'historique.
    try:
        data = strategy.precompute(df, strategy.params)
        bt_signals = strategy.generate_signals(data, strategy.params, n)
    except Exception as e:
        return ConformanceReport(strategy.STRATEGY_ID, symbol, 0, 0, 0,
                                 error=f"chemin backtest : {type(e).__name__}: {e}")

    by_ts = {pd.Timestamp(s.timestamp): s for s in bt_signals}

    # Chemin live : une barre à la fois, l'historique s'arrête à la barre courante.
    divergences: list[Divergence] = []
    n_live = 0
    for i in range(start, n):
        window = df.iloc[:i + 1]
        ctx = MarketContext(
            symbol=symbol, timeframe=m.timeframe, bars=window,
            now=pd.Timestamp(df.index[i]).to_pydatetime(),
            spread=spread,
            own_position=None,   # à plat : on compare la DÉCISION, pas le filtrage
        )
        try:
            live = strategy.on_bar(ctx)
        except NotImplementedError:
            return ConformanceReport(
                strategy.STRATEGY_ID, symbol, 0, len(bt_signals), 0,
                error="on_bar() non implémenté — le chemin live n'existe pas")
        except Exception as e:
            return ConformanceReport(
                strategy.STRATEGY_ID, symbol, i - start, len(bt_signals), n_live,
                error=f"chemin live à la barre {i} : {type(e).__name__}: {e}")

        if live is not None:
            n_live += 1

        bt = by_ts.get(pd.Timestamp(df.index[i]))
        if _key(bt) != _key(live):
            divergences.append(Divergence(i, pd.Timestamp(df.index[i]), bt, live))

    n_bt_in_window = sum(1 for ts in by_ts if ts >= df.index[start])
    return ConformanceReport(
        strategy_id=strategy.STRATEGY_ID, symbol=symbol,
        bars_replayed=n - start, n_backtest=n_bt_in_window, n_live=n_live,
        divergences=divergences, delegates=_delegates(strategy),
    )


def load_strategy(strategy_id: str) -> StrategyModule:
    mod = importlib.import_module(f"strategies.{strategy_id}.strategy")
    return mod.Strategy()


def main() -> int:
    ap = argparse.ArgumentParser(description="R5 — conformité backtest / live")
    ap.add_argument("--strategy", help="ex: s10_legacy_meanrev")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--symbol", help="force un instrument (sinon : 1er du manifest)")
    ap.add_argument("--bars", type=int, default=DEFAULT_BARS,
                    help=f"barres rejouées barre par barre (défaut {DEFAULT_BARS})")
    ap.add_argument("--save", action="store_true",
                    help="écrit backtests/conformance.txt dans le dossier de la stratégie")
    a = ap.parse_args()

    if a.all:
        sdir = os.path.join(ROOT, "strategies")
        ids = sorted(d for d in os.listdir(sdir)
                     if not d.startswith("_")
                     and os.path.isdir(os.path.join(sdir, d)))
    elif a.strategy:
        ids = [a.strategy]
    else:
        ap.error("--strategy ou --all requis")

    from core.data.source import load_bars  # import tardif : MT5 est lourd

    failures = 0
    for sid in ids:
        try:
            strat = load_strategy(sid)
        except NotImplementedError:
            print(f"[SKIP] {sid} — pas encore implémentée")
            continue
        except Exception as e:
            print(f"[ERR ] {sid} — chargement impossible : {e}")
            failures += 1
            continue

        m = strat.manifest()
        symbol = a.symbol or (m.symbols[0] if m.symbols else None)
        if not symbol:
            print(f"[SKIP] {sid} — aucun instrument déclaré dans le manifest")
            continue

        df = load_bars(symbol, m.timeframe)
        if df is None or len(df) < m.warmup_bars + 50:
            print(f"[SKIP] {sid} — données insuffisantes pour {symbol}")
            continue

        report = check(strat, df, symbol, n_bars=a.bars)
        print(report.render())
        print()

        if a.save:
            out = os.path.join(ROOT, "strategies", sid, "backtests", "conformance.txt")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                f.write(report.render())
            print(f"  -> {out}\n")

        if not report.ok:
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

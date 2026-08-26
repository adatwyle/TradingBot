"""
R1 — GARDIEN DE CAUSALITÉ
==========================

Vérifie qu'une stratégie ne peut pas voir le futur, via l'invariant de
troncature :

    generate_signals(precompute(df),      params, T)
        ==
    generate_signals(precompute(df[:T]),  params, T)

Si les deux diffèrent d'un seul signal, il y a fuite d'information.

POURQUOI CE MODULE EXISTE
-------------------------
Le 15 août 2026, on a découvert que `fast_bt_multi` clôturait les positions
résiduelles à `closes[-1]` — la dernière barre du tableau COMPLET — alors que
sa boucle respectait bien `end_idx`. Chaque tranche d'entraînement valorisait
donc son trade ouvert à un prix futur.

Le bug était invisible : les résultats semblaient corrects, les rendements
plausibles. Il a contaminé des mois de walk-forward avant d'être trouvé, et
seulement parce qu'on a comparé un run tronqué à un run sur données tronquées.

Ce test transforme cette découverte accidentelle en garde-fou systématique.
Aucune stratégie ne passe en PAPER sans l'avoir passé.

USAGE
-----
    python -m core.validation.causality --strategy s10_legacy_meanrev
    python -m core.validation.causality --all
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.contracts.strategy import Signal, StrategyModule  # noqa: E402


# Fractions de l'historique auxquelles on coupe. Volontairement alignées sur
# les fenêtres du walk-forward ancré : ce sont exactement les points où une
# fuite fausserait la sélection.
DEFAULT_CUTS = (0.60, 0.70, 0.80, 0.90)


@dataclass
class CutResult:
    fraction: float
    end_idx: int
    n_full: int
    n_truncated: int
    first_divergence: Optional[str]

    @property
    def ok(self) -> bool:
        return self.first_divergence is None


@dataclass
class IndicatorLeak:
    """Fuite détectée au niveau des INDICATEURS, avant même les signaux."""
    fraction: float
    column: str
    max_deviation: float
    n_affected: int
    n_compared: int
    reach_bars: int          # jusqu'où la fuite remonte avant la coupure
    # Parmi les points en cause, combien sont des DÉSACCORDS DE DÉFINITION
    # (valeur d'un côté, NaN de l'autre). Compté à part parce qu'un tel point
    # n'a pas d'écart numérique mesurable : `max_deviation` vaut alors l'infini,
    # ce qui doit se lire comme « incomparable », pas comme « écart énorme ».
    n_nan_mismatch: int = 0

    @property
    def pct_affected(self) -> float:
        return 100.0 * self.n_affected / self.n_compared if self.n_compared else 0.0


@dataclass
class CausalityReport:
    strategy_id: str
    symbol: str
    bars: int
    cuts: list[CutResult]
    indicator_leaks: list[IndicatorLeak] = field(default_factory=list)
    # False quand precompute() ne renvoie pas un DataFrame : la couche
    # indicateur n'a alors RIEN pu inspecter. Le rapport doit le crier, sinon
    # un « R1 PASSE » se lit comme une garantie qui n'a pas ete donnee.
    indicator_layer_covered: bool = True

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.cuts) and not self.indicator_leaks

    def render(self) -> str:
        lines = []
        lines.append("=" * 78)
        lines.append("R1 — INVARIANT DE CAUSALITÉ")
        lines.append("=" * 78)
        lines.append(f"Stratégie : {self.strategy_id}")
        lines.append(f"Instrument: {self.symbol}   ({self.bars} barres)")
        lines.append("")
        lines.append("Compare, à chaque coupure T :")
        lines.append("  A = generate_signals(precompute(df),     params, T)")
        lines.append("  B = generate_signals(precompute(df[:T]), params, T)")
        lines.append("A et B DOIVENT être identiques. Toute différence = fuite.")
        lines.append("")
        lines.append(f"  {'coupure':>8} {'T':>8} {'signaux A':>10} {'signaux B':>10}  verdict")
        lines.append("  " + "-" * 68)
        for c in self.cuts:
            verdict = "OK" if c.ok else "*** FUITE ***"
            lines.append(
                f"  {c.fraction:>7.0%} {c.end_idx:>8} {c.n_full:>10} "
                f"{c.n_truncated:>10}  {verdict}"
            )
            if not c.ok:
                lines.append(f"           -> {c.first_divergence}")
        lines.append("")
        if not self.indicator_layer_covered:
            lines.append("!! COUCHE INDICATEUR NON VERIFIEE !!")
            lines.append("  precompute() ne renvoie pas un DataFrame : aucune colonne n'a pu")
            lines.append("  etre comparee. Ce verdict ne repose QUE sur la couche signal.")
            lines.append("  Une fuite qui perturbe un indicateur sans faire basculer de signal")
            lines.append("  a cette coupure passe donc inapercue. Faire renvoyer un DataFrame")
            lines.append("  a precompute() pour rendre la strategie reellement verifiable.")
            lines.append("")
        if self.indicator_leaks:
            lines.append("FUITES AU NIVEAU DES INDICATEURS")
            lines.append("  (une fuite peut perturber un indicateur sans faire basculer")
            lines.append("   de signal ici — mais elle le fera ailleurs)")
            lines.append(f"  {'coupure':>8} {'colonne':<18} {'ecart max':>12} {'points':>14} "
                         f"{'dont NaN':>9} {'portee':>9}")
            lines.append("  " + "-" * 68)
            for L in self.indicator_leaks[:12]:
                # "NaN" au lieu d'un nombre : la colonne n'est pas definie du
                # meme cote des deux passes, il n'y a donc pas d'ecart a chiffrer.
                dev = (f"{L.max_deviation:>12.3e}" if np.isfinite(L.max_deviation)
                       else f"{'NaN':>12}")
                lines.append(f"  {L.fraction:>7.0%} {L.column:<18} {dev} "
                             f"{L.n_affected:>6}/{L.n_compared:<7} "
                             f"{L.n_nan_mismatch:>9} {L.reach_bars:>6} b")
            if len(self.indicator_leaks) > 12:
                lines.append(f"  ... et {len(self.indicator_leaks)-12} autres")
            lines.append("  Cause frequente : scipy.signal.filtfilt (avant+arriere) au lieu")
            lines.append("  de lfilter (avant seulement). Ou une normalisation sur tout l'echantillon.")
            lines.append("  Colonne 'dont NaN' non nulle : une fenetre qui lit vers l'AVANT n'a")
            lines.append("  plus de valeur en fin de serie tronquee alors qu'elle en a une sur la")
            lines.append("  serie complete. Le desaccord est dans le motif de NaN, pas dans les")
            lines.append("  chiffres.")
            lines.append("")
        if self.ok:
            lines.append("VERDICT : R1 PASSÉ — aucune information future détectée.")
        else:
            lines.append("VERDICT : R1 ÉCHOUÉ — la stratégie voit le futur.")
            lines.append("          Résultats non publiables. Corriger avant tout backtest.")
        return "\n".join(lines)


def _key(s: Signal) -> tuple:
    """Empreinte comparable d'un signal. On compare les décisions, pas les
    objets — un float qui diffère au 12e chiffre n'est pas une fuite."""
    return (
        pd.Timestamp(s.timestamp).value,
        s.symbol,
        s.side.value,
        round(float(s.entry), 8),
        round(float(s.stop), 8),
        round(float(s.target), 8) if s.target is not None else None,
    )


def _describe(a: list[Signal], b: list[Signal]) -> Optional[str]:
    """Première divergence, en clair."""
    if len(a) != len(b):
        # Cas le plus fréquent : un trade résiduel valorisé au prix futur.
        extra = "A" if len(a) > len(b) else "B"
        return (f"nombre de signaux différent ({len(a)} vs {len(b)}) — "
                f"{extra} en produit davantage. Cause typique : une position "
                f"résiduelle clôturée hors de la tranche évaluée.")
    for i, (x, y) in enumerate(zip(a, b)):
        kx, ky = _key(x), _key(y)
        if kx != ky:
            fields = ["timestamp", "symbol", "side", "entry", "stop", "target"]
            diff = [f"{f}: {vx!r} != {vy!r}"
                    for f, vx, vy in zip(fields, kx, ky) if vx != vy]
            return f"signal #{i} diverge — " + " ; ".join(diff)
    return None



def _compare_precompute(data_full, data_trunc, end_idx: int,
                        frac: float, tol: float = 1e-9) -> list[IndicatorLeak]:
    """Compare les INDICATEURS calcules sur df complet vs df tronque.

    POURQUOI CETTE COUCHE EXISTE
    ----------------------------
    L'invariant au niveau des SIGNAUX ne suffit pas. Une fuite peut perturber
    un indicateur sans faire basculer de signal sur CE jeu de donnees — et
    passer inapercue. Sur d'autres donnees, le meme defaut ferait basculer un
    signal et gonflerait les resultats en silence.

    Cas d'ecole : `scipy.signal.filtfilt` applique le filtre en avant PUIS en
    arriere pour annuler le dephasage. Le resultat a l'instant t depend donc de
    valeurs FUTURES. Mesure sur nos donnees : ecart max 4,9e-4 sur 18 points,
    tous dans les 18 barres precedant la coupure — invisible au niveau signal,
    bien reel au niveau indicateur.

    La version causale est `lfilter` (avant seulement), qui donne un ecart
    strictement nul.

    LE DESACCORD DE DEFINITION COMPTE AUTANT QUE L'ECART NUMERIQUE
    --------------------------------------------------------------
    Cette fonction a longtemps compare les deux passes sous le masque
    `np.isfinite(a) & np.isfinite(b)`. Un point NaN d'un seul cote etait donc
    ECARTE de la comparaison, au lieu d'etre compte comme un desaccord.

    C'etait un angle mort, pas un detail. Le 16.08.2026, une fuite injectee
    volontairement (moyenne mobile calculee sur la serie retournee) a obtenu un
    "R1 PASSE". Raison : une fenetre qui lit vers l'AVANT produit exactement les
    memes chiffres des deux cotes partout ou elle dispose de ses barres, et se
    contente de perdre ses dernieres valeurs en fin de serie tronquee. Toute la
    divergence tenait dans le motif de NaN — que le masque effacait.

    On compte donc desormais ces desaccords. Avec une reserve indispensable :
    les NaN de warmup en debut de serie sont normaux et se produisent des DEUX
    cotes (les deux passes partent de la meme barre 0). La zone exclue est donc
    le prefixe ou AUCUNE des deux series n'est encore definie. Passe ce point,
    un NaN qui apparait ou disparait ne peut venir que de la troncature.
    """
    leaks = []
    if not isinstance(data_full, pd.DataFrame) or not isinstance(data_trunc, pd.DataFrame):
        return leaks   # precompute renvoie un objet opaque : non verifiable ici

    common = [c for c in data_full.columns if c in data_trunc.columns]
    for col in common:
        a = data_full[col].to_numpy()[:end_idx]
        b = data_trunc[col].to_numpy()[:end_idx]
        if a.dtype.kind not in "fiu" or b.dtype.kind not in "fiu" or len(a) != len(b):
            continue

        fin_a, fin_b = np.isfinite(a), np.isfinite(b)
        both = fin_a & fin_b

        # Fin du warmup commun : premiere barre ou au moins une des deux passes
        # produit une valeur. Avant elle, les NaN sont attendus et symetriques —
        # les signaler reviendrait a crier au loup sur chaque indicateur, ce qui
        # est une autre facon de ne rien garder.
        defined = fin_a | fin_b
        if not defined.any():
            continue            # colonne vide des deux cotes : rien a comparer
        warmup_end = int(np.argmax(defined))

        # Desaccord de DEFINITION : valeur d'un cote, NaN de l'autre, hors warmup.
        nan_mismatch = fin_a ^ fin_b
        nan_mismatch[:warmup_end] = False

        # Desaccord NUMERIQUE : les deux definies, mais elles ne disent pas la
        # meme chose. C'est ce que la version d'origine attrapait deja.
        d = np.zeros_like(a, dtype=float)
        num_mismatch = np.zeros(len(a), dtype=bool)
        if both.any():
            d[both] = np.abs(a[both] - b[both])
            scale = max(1.0, float(np.nanmedian(np.abs(a[both]))) or 1.0)
            num_mismatch = both & (d > tol * scale)

        hits = np.flatnonzero(num_mismatch | nan_mismatch)
        if hits.size:
            n_nan = int(nan_mismatch.sum())
            leaks.append(IndicatorLeak(
                fraction=frac, column=col,
                # Un desaccord purement NaN n'a pas d'ecart chiffrable : l'infini
                # dit "incomparable", et le rapport l'affiche comme tel.
                max_deviation=(float(d[num_mismatch].max())
                               if num_mismatch.any() else float("inf")),
                n_affected=int(hits.size),
                n_compared=int(both.sum()) + n_nan,
                reach_bars=int(end_idx - hits.min()),
                n_nan_mismatch=n_nan,
            ))
    return leaks


def check(strategy: StrategyModule, df: pd.DataFrame, symbol: str,
          cuts: tuple[float, ...] = DEFAULT_CUTS) -> CausalityReport:
    """Exécute l'invariant sur une stratégie et un jeu de données."""
    params = strategy.params
    n = len(df)

    # Précalcul complet, fait une seule fois : c'est le chemin "normal" du
    # backtester, celui qu'on soupçonne.
    data_full = strategy.precompute(df, params)

    results: list[CutResult] = []
    leaks: list[IndicatorLeak] = []
    for frac in cuts:
        T = int(n * frac)
        if T <= strategy.manifest().warmup_bars + 10:
            continue

        sig_full = strategy.generate_signals(data_full, params, T)

        # Chemin de référence : la stratégie ne reçoit littéralement PAS les
        # barres futures. Si elle produit autre chose, elle les utilisait.
        data_trunc = strategy.precompute(df.iloc[:T].copy(), params)
        sig_trunc = strategy.generate_signals(data_trunc, params, T)

        # Couche indicateur : attrape les fuites qui ne changent pas (encore) de signal
        leaks.extend(_compare_precompute(data_full, data_trunc, T, frac))

        results.append(CutResult(
            fraction=frac, end_idx=T,
            n_full=len(sig_full), n_truncated=len(sig_trunc),
            first_divergence=_describe(sig_full, sig_trunc),
        ))

    return CausalityReport(
        strategy_id=strategy.STRATEGY_ID, symbol=symbol, bars=n, cuts=results,
        indicator_leaks=leaks,
        indicator_layer_covered=isinstance(data_full, pd.DataFrame),
    )


def load_strategy(strategy_id: str) -> StrategyModule:
    mod = importlib.import_module(f"strategies.{strategy_id}.strategy")
    return mod.Strategy()


def main() -> int:
    ap = argparse.ArgumentParser(description="R1 — invariant de causalité")
    ap.add_argument("--strategy", help="ex: s10_legacy_meanrev")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--symbol", help="force un instrument (sinon : 1er du manifest)")
    ap.add_argument("--save", action="store_true",
                    help="écrit backtests/causality.txt dans le dossier de la stratégie")
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
    opaques: list[str] = []
    crashed: list[str] = []
    checked = 0
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
        # Deux contrats coexistent : StrategyManifest declare `symbols`,
        # AllocationManifest declare `universe`. Une version anterieure lisait
        # `m.symbols` sans garde : sur une strategie d'allocation, l'attribut
        # manquant levait une AttributeError HORS du try, ce qui tuait la
        # boucle entiere. Consequence mesuree : `--all` s'arretait a s07 et
        # n'atteignait jamais s10, s11, s90, s91, s92. Qui lancait `--all` en
        # croyant couvrir le portefeuille n'en validait que la moitie.
        declared = getattr(m, "symbols", None) or getattr(m, "universe", None)
        symbol = a.symbol or (declared[0] if declared else None)
        if not symbol:
            print(f"[SKIP] {sid} — aucun instrument déclaré dans le manifest")
            continue

        df = load_bars(symbol, m.timeframe)
        if df is None or len(df) < 2000:
            print(f"[SKIP] {sid} — données insuffisantes pour {symbol}")
            continue

        try:
            report = check(strat, df, symbol)
        except Exception as e:
            # Une strategie qui explose ne doit JAMAIS interrompre le balayage :
            # les suivantes ne seraient pas verifiees et le silence passerait
            # pour un succes. On compte l'echec et on continue.
            print(f"[ERR ] {sid} — verification impossible : {type(e).__name__}: {e}")
            crashed.append(sid)
            failures += 1
            continue

        checked += 1
        if not report.indicator_layer_covered:
            opaques.append(sid)
        print(report.render())
        print()

        if a.save:
            out = os.path.join(ROOT, "strategies", sid, "backtests", "causality.txt")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                f.write(report.render())
            print(f"  -> {out}\n")

        if not report.ok:
            failures += 1

    # Synthese finale : sans elle, un balayage de 12 strategies se lit comme un
    # succes global alors qu'une partie n'a pas ete verifiee du tout.
    if len(ids) > 1:
        print("=" * 78)
        print(f"BILAN — {checked} strategie(s) verifiee(s) sur {len(ids)} demandee(s)")
        if crashed:
            print(f"  ECHEC de verification : {', '.join(crashed)}")
        if opaques:
            print(f"  COUCHE INDICATEUR AVEUGLE : {', '.join(opaques)}")
            print("    precompute() y renvoie autre chose qu'un DataFrame. Leur")
            print("    « R1 PASSE » ne couvre que la couche signal.")
        if not crashed and not opaques:
            print("  Toutes les strategies verifiees, couche indicateur incluse.")
        print("=" * 78)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

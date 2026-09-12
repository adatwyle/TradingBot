"""
S024 — « Go Long » (René Balke) : achat d'indice à heure fixe, clôture à heure fixe.

Source : vidéo « In 48 Minutes I show you how I made €100,000 Trading Forex »
(BM Trading, https://www.youtube.com/watch?v=qgsi-u0kOVw), règle dictée à
[05:24]-[09:00] et réglages live montrés à l'écran à [24:30]-[27:26] ; guide
d'entrées de l'EA gratuit (`docs/sources/renebalke/ea_inputs/Go Long EA Inputs.pdf`,
https://bmtrading.de/en/expert-advisors/). Reproduite ICI TELLE QUELLE :

  ENTRÉE   tous les jours, à heure fixe, un ACHAT. Aucun filtre, aucune analyse.
           US30 et US Tech 01:05 heure serveur ; DE40 09:05 (spread nocturne du
           DAX « four times or even more » plus cher chez son courtier). [05:24] [26:40]
  SORTIE   à heure fixe le même jour : 23:50 ; DE40 22:55. [05:24] [27:26]
  RIEN     pas de stop, pas de cible, pas de trailing, pas de break-even, option
           « wait for new day high » désactivée. [25:16] [26:40]
  POURQUOI rouvrir chaque jour au lieu de tenir : le swap long coûterait ≈ 6 %/an
           sur le DE40 pour un indice qui gagne 5-10 %/an, et être à plat la nuit
           et le week-end évite les gaps baissiers. [07:32] [08:24]

CE QUE LA PLATEFORME IMPOSE ET QUI N'EST PAS DANS LA SOURCE
-----------------------------------------------------------
R3 exige un stop. Balke n'en a pas : son « risque » de 50 000 € est un
dimensionnement notionnel (la perte si l'indice tombait à zéro), pas un stop
[24:30]. On déclare donc une **garde catastrophe** `guard_pct` sous l'entrée —
jamais un stop de gestion. Elle ne doit presque jamais être touchée ; le harnais
compte les fois où elle l'est, et c'est un chiffre du rapport, pas un détail.
Ajouté aussi : le coût de bord réel (il n'en parle pas pour cette stratégie) et,
en second bras d'information seulement, les règles communes anti-pertes
consécutives (directive Adrian 2026-09-12 : elles ne s'imposent jamais au bras
fidèle).

MODÈLE DE SORTIE — approximation déclarée
------------------------------------------
Le moteur commun n'a qu'une sortie temporelle : `run(..., max_hold_bars=k)`,
qui ferme k barres après l'entrée (`exit_reason="EOD"`). La clôture à heure fixe
est donc approximée par un nombre de barres, calculé par le harnais depuis la
séance réellement observée dans les données (S009 a posé le précédent). L'écart
horaire résiduel est mesuré et publié dans `research/VERDICT.md` — il n'est pas
nul, il est déclaré.

CAUSALITÉ (R1) : la barre de signal est « la première barre du jour serveur dont
l'heure vaut `start_hour + entry_hour_offset` ». C'est une lecture du calendrier,
pas du prix : à la barre i elle ne dépend que de [0, i] (les barres antérieures du
même jour). `generate_signals` est invariant par troncature. `on_bar` délègue au
même code (R5).
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

WARMUP_BARS = 0          # aucun indicateur : la règle est un horaire


class Strategy(StrategyModule):
    STRATEGY_ID = "S024_balke_go_long"
    MAGIC_NUMBER = 130024

    def __init__(self, params: Optional[dict] = None):
        self.params = dict(self.manifest().default_params)
        if params:
            unknown = set(params) - set(self.params)
            if unknown:
                raise ValueError(
                    f"paramètres inconnus pour {self.STRATEGY_ID} : {sorted(unknown)}")
            self.params.update(params)
        _validate(self.params)
        self._symbol = "NASDAQ"

    # ── manifeste (R7 : source unique de vérité) ───────────────────────────
    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id="S024_balke_go_long",
            display_name="Go Long — achat d'indice à heure fixe (René Balke)",
            version="1.0.0",
            magic_number=130024,
            author="claude:S024_balke_go_long",
            source=("https://www.youtube.com/watch?v=qgsi-u0kOVw · "
                    "https://bmtrading.de/en/expert-advisors/"),
            symbols=["DAX", "NASDAQ", "US30"],
            timeframe="H1",
            warmup_bars=WARMUP_BARS,
            # 6 cellules, figées AVANT la mesure (research/FALSIFICATION.md).
            # La règle n'a aucun réglage chez l'auteur : les deux seuls axes
            # ouverts ici sont (a) la garde catastrophe que R3 nous impose et
            # dont il n'a pas d'équivalent, (b) l'ambiguïté de ±1 h entre son
            # 01:05 et le maillage horaire de nos barres. Rien d'autre.
            param_grid={
                "guard_pct": [0.03, 0.05, 0.10],
                "entry_hour_offset": [0, 1],
            },
            default_params={
                "start_hour": 0,          # première heure de séance (DAX : 8) — réglage
                                          # d'instrument, pas de grille (cf. « Trading
                                          # Start Hour » du guide de l'EA)
                "entry_hour_offset": 0,   # 0 = première barre du jour serveur
                "guard_pct": 0.05,        # garde catastrophe, jamais un stop de gestion
            },
            status="BACKTESTED",      # mesuré 2026-09-12, research/VERDICT.md
                                      # « BACKTESTED = mesuré, pas validé » (R10)
            notes=("Reproduction fidèle : achat quotidien à heure fixe, clôture à "
                   "heure fixe, ni SL ni TP chez l'auteur. La garde catastrophe et "
                   "la sortie en nombre de barres sont des contraintes de plateforme, "
                   "déclarées et mesurées."),
        )

    # ── calendrier (aucun indicateur de prix) ──────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        """Marque la barre de signal de chaque jour serveur.

        Renvoie un DataFrame (et pas un dict) : la couche indicateur est ainsi
        réellement inspectée par le gardien de causalité — leçon s91 §2.9.
        """
        # Les paramètres reçus complètent ceux de l'instance, ils ne les
        # remplacent pas : un appel partiel ne doit PAS retomber en silence sur
        # l'heure 0 alors que l'instance est réglée sur la séance du DAX (8).
        p = {**self.params, **params}
        _validate(p)
        hour = int(p["start_hour"]) + int(p["entry_hour_offset"])

        idx = pd.DatetimeIndex(df.index)
        out = pd.DataFrame(index=df.index)
        out["close"] = df["close"].astype(float)
        out["hour"] = idx.hour
        day = idx.normalize()
        out["day"] = day

        at_hour = pd.Series(idx.hour == hour, index=df.index)
        # cumsum par jour : vaut 1 exactement à la PREMIÈRE barre du jour à cette
        # heure. Ne regarde que des barres antérieures du même jour -> causal, et
        # invariant par troncature de la queue.
        rank = at_hour.groupby(day).cumsum()
        out["entry_bar"] = (at_hour & (rank == 1)).astype(float)
        return out

    # ── signaux ────────────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        p = {**self.params, **params}
        _validate(p)
        guard = float(p["guard_pct"])

        n = min(end_idx, len(data))
        idx = data.index
        close = data["close"].to_numpy(dtype=float)
        entry_bar = data["entry_bar"].to_numpy() > 0.5

        out: list[Signal] = []
        for i in range(WARMUP_BARS, n):
            if not entry_bar[i]:
                continue
            entry = float(close[i])
            if not np.isfinite(entry) or entry <= 0:
                continue
            # LONG SEULEMENT — « The Go Long EA only opens long (buy) positions »
            # (guide de l'EA). Aucune vente, jamais.
            out.append(Signal(
                timestamp=pd.Timestamp(idx[i]).to_pydatetime(),
                symbol=self._symbol, side=Side.LONG,
                entry=entry,
                stop=entry * (1.0 - guard),      # garde catastrophe (R3)
                target=None,                     # « there is no take profit » [05:24]
                reason=(f"Go Long — achat quotidien {pd.Timestamp(idx[i]).strftime('%H:%M')} "
                        f"serveur · garde {guard:.0%}"),
                meta={"guard_pct": guard, "hour": int(pd.Timestamp(idx[i]).hour)},
            ))
        return out

    # ── live : même code que le backtest (R5) ──────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        self._symbol = ctx.symbol
        data = self.precompute(ctx.bars, self.params)
        sigs = self.generate_signals(data, self.params, len(ctx.bars))
        if sigs and pd.Timestamp(sigs[-1].timestamp) == pd.Timestamp(ctx.bars.index[-1]):
            return sigs[-1]
        return None


def _validate(p: dict) -> None:
    """Bornes des paramètres. Une valeur hors bornes lève — pas de repli muet."""
    sh = p.get("start_hour", 0)
    off = p.get("entry_hour_offset", 0)
    guard = p.get("guard_pct", 0.05)
    if not isinstance(sh, (int, np.integer)) or isinstance(sh, bool) or not (0 <= int(sh) <= 23):
        raise ValueError(f"start_hour doit être un entier de 0 à 23 : {sh!r}")
    if not isinstance(off, (int, np.integer)) or isinstance(off, bool) or int(off) not in (0, 1):
        raise ValueError(f"entry_hour_offset doit valoir 0 ou 1 : {off!r}")
    if int(sh) + int(off) > 23:
        raise ValueError(f"start_hour + entry_hour_offset dépasse 23 : {sh!r} + {off!r}")
    g = float(guard)
    if not (0.0 < g < 1.0):
        raise ValueError(f"guard_pct doit être dans ]0, 1[ : {guard!r}")

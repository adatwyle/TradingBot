"""
S023 — « Turnaround Tuesday » (René Balke) : achat du lundi sous la SMA journalière.

Source : rétrospective « In 48 Minutes I show you how I made €100,000 » (BM Trading,
https://www.youtube.com/watch?v=qgsi-u0kOVw) — règle dictée à [13:48]-[15:58],
réglages live montrés à l'écran à [27:41]-[29:19] ; guide d'entrées de l'EA
`docs/sources/renebalke/ea_inputs/Turnaround Tuesday EA Inputs.pdf` ; page produit
https://bmtrading.de/en/expert-advisors/. Reproduite ICI TELLE QUELLE :

  JOUR      lundi uniquement (« it only opens positions on Monday »).
  FILTRE    le prix est SOUS une moyenne mobile SIMPLE calculée sur les CLÔTURES
            du chart JOURNALIER. Période différente par indice — US30 = 25,
            US Tech (NASDAQ) = 9, DE40 (DAX) = 40. [28:18] [28:56] [29:10]
  SENS      achat seulement. Jamais de vente.
  SORTIE    l'heure, et rien d'autre : on tient lundi ET mardi, clôture le mardi
            soir (23:50 heure serveur ; 22:55 pour le DE40). [15:40]
  GESTION   « No TP, no SL, no trade management, nothing. » [15:58]

Thèse de l'auteur : après un week-end et une semaine baissière, le lundi-mardi
porte un mouvement de reprise. Il précise ne pas en être l'auteur (« it's a very
common strategy, it's around for many many years ») et qualifie lui-même son
échantillon live de faible (160 trades, +16 k€ depuis mars 2024, « probably I was
lucky in the period »).

CE QUE LA PLATEFORME AJOUTE, ET QUI N'EST PAS DANS LA SOURCE
------------------------------------------------------------
1. **Un stop.** `Signal.stop` ne peut pas être None (R3). Balke n'a PAS de stop :
   son risque est le notionnel (25 000 € par trade, perte si l'indice va à zéro).
   La stratégie déclare donc SA PROPRE règle — `guard_pct`, une **garde
   catastrophe** à 5 % sous l'entrée, jamais un stop de gestion. Elle n'existe que
   pour satisfaire le contrat de la plateforme et borner le pire cas ; le harnais
   compte combien de trades la touchent, et ce compte fait partie du verdict.
   Doctrine Adrian 2026-09-12 : chaque stratégie porte ses propres règles.
2. Le coût de bord réel (demi-spread + glissement aux deux extrémités).
3. Le bras témoin aléatoire et les règles communes anti-pertes consécutives,
   mesurés en SECOND bras — jamais imposés au bras fidèle.

SORTIE TEMPORELLE — DÉGRADATION DÉCLARÉE
-----------------------------------------
Le moteur commun n'a qu'une seule sortie temporelle : `max_hold_bars` (clôture k
barres après l'entrée). La clôture « mardi 23:50 » est donc approximée par un
NOMBRE FIXE de barres H1, calibré sur les données et transmis par le harnais :
45 pour NASDAQ/US30 (cotation quasi continue, mode 234/261 semaines), 27 pour le
DAX (séance 08:00-21:00, mode 253/254). En `entry_mode="first_bar"` la sortie
tombe donc EXACTEMENT sur la dernière barre du mardi dans ~90 % des semaines ;
en `entry_mode="any_bar"` une entrée tardive décale la sortie d'autant. Le
harnais mesure et publie la distribution des heures de sortie — c'est la seule
façon honnête de déclarer l'approximation (même geste que S009).

DEUX MODÈLES D'ENTRÉE, PAS UN SEUL
-----------------------------------
L'EA vérifie la condition EN CONTINU le lundi et ouvre à heure fixe (01:05 ;
09:05 pour le DE40). Deux lectures s'affrontent, la grille les mesure toutes deux :
  `first_bar` — décision à la PREMIÈRE barre du lundi (heure serveur 0 pour
      NASDAQ/US30, 8 pour le DAX : l'entrée tombe au close de cette barre, soit
      01:00 et 09:00 — à cinq minutes de ses horaires réels). Prix de référence :
      la clôture du DERNIER JOUR SERVEUR COMPLET — le vendredi en général, mais le
      dimanche les 18 semaines (sur 5 ans) où NASDAQ/US30 portent une barre
      dominicale résiduelle d'ouverture anticipée. Sortie EXACTE.
  `any_bar` — la condition est relue à CHAQUE barre du lundi et la première qui
      la remplit entre (fidélité à « check constantly »), au prix de la dérive de
      sortie décrite ci-dessus.
Défaut : `first_bar` (sortie exacte). `any_bar` est la variante de fidélité d'entrée.

CAUSALITÉ (R1)
--------------
La série journalière est dérivée des barres H1 (clôture du jour = close de la
DERNIÈRE barre H1 du jour serveur ; vérifié identique aux barres D1 du courtier
sur 1293-1331 jours, écart médian nul). La SMA et la clôture de référence sont
décalées d'un jour : à la barre i, elles ne portent QUE sur des jours
STRICTEMENT ANTÉRIEURS au jour de i. Modifier les barres du lundi lui-même ne
peut donc pas changer la SMA utilisée ce lundi-là. `on_bar` délègue au même code (R5).
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

MONDAY = 0
NS_PER_DAY = 86_400_000_000_000
ENTRY_MODES = ("first_bar", "any_bar")


def _validated(params: dict) -> dict:
    """Bornes des paramètres. Un réglage hors bornes est une erreur, pas un
    défaut silencieux : une garde à 0 % ferait un stop au prix d'entrée."""
    n_sma = params.get("sma_period", 25)
    if isinstance(n_sma, bool) or not isinstance(n_sma, (int, np.integer)):
        raise ValueError(f"sma_period doit être un entier (0 = pas de filtre) : {n_sma!r}")
    if n_sma < 0:
        raise ValueError(f"sma_period doit être >= 0 (0 = pas de filtre) : {n_sma}")
    mode = params.get("entry_mode", "first_bar")
    if mode not in ENTRY_MODES:
        raise ValueError(f"entry_mode inconnu : {mode!r} (attendu {ENTRY_MODES})")
    guard = params.get("guard_pct", 0.05)
    if not isinstance(guard, (int, float)) or isinstance(guard, bool):
        raise ValueError(f"guard_pct doit être un nombre : {guard!r}")
    if not (0.0 < float(guard) < 1.0):
        raise ValueError(f"guard_pct doit être dans ]0, 1[ : {guard}")
    dow = params.get("open_dow", MONDAY)
    if isinstance(dow, bool) or not isinstance(dow, (int, np.integer)) or not (0 <= dow <= 6):
        raise ValueError(f"open_dow doit être un entier 0-6 (0 = lundi) : {dow!r}")
    return {"sma_period": int(n_sma), "entry_mode": mode,
            "guard_pct": float(guard), "open_dow": int(dow)}


class Strategy(StrategyModule):

    STRATEGY_ID = "S023_balke_turnaround_tuesday"
    MAGIC_NUMBER = 130023

    def __init__(self, params: Optional[dict] = None):
        super().__init__(params)          # refuse les clés inconnues
        _validated(self.params)
        self._symbol = "US30"

    # ── manifeste ──────────────────────────────────────────────────────────
    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id="S023_balke_turnaround_tuesday",
            display_name="Turnaround Tuesday — achat du lundi sous la SMA D1 (René Balke)",
            version="1.0.0",
            magic_number=130023,
            author="claude:S023_balke_turnaround_tuesday",
            source=("https://www.youtube.com/watch?v=qgsi-u0kOVw · "
                    "https://bmtrading.de/en/expert-advisors/"),
            symbols=["DAX", "NASDAQ", "US30"],
            timeframe="H1",
            # Le vrai préchauffage est porté par la série JOURNALIÈRE (la SMA est
            # NaN tant que N jours complets ne sont pas disponibles), pas par un
            # nombre de barres fixe : 40 jours valent 960 barres sur un indice US
            # et 560 sur le DAX. La valeur déclarée est la plus contraignante.
            warmup_bars=41 * 24,
            # 18 cellules : les trois périodes qu'il trade × les deux lectures du
            # « check constantly » × trois distances de garde. Pas un balayage —
            # aucune de ces valeurs n'a été choisie après avoir vu un résultat.
            param_grid={
                "sma_period": [9, 25, 40],
                "entry_mode": ["first_bar", "any_bar"],
                "guard_pct": [0.03, 0.05, 0.10],
            },
            default_params={
                "sma_period": 25,        # sa valeur US30 ; NASDAQ 9, DAX 40 par instrument
                "entry_mode": "first_bar",
                "guard_pct": 0.05,
                "open_dow": MONDAY,      # « Open Day of Week » de l'EA, hors grille
            },
            status="BACKTESTED",         # mesuré 2026-09-12 — « mesuré, pas validé » (R10)
            notes=("Reproduction fidèle. sma_period=0 = filtre désactivé : cellule de "
                   "RÉFÉRENCE (rendement 2 jours nu du lundi au mardi), hors grille, "
                   "pour rendre visible l'apport du filtre SMA."),
        )

    # ── indicateurs ────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        """Série journalière dérivée des barres H1, décalée d'un jour.

        `prev_day_close` et `prev_day_sma` à la barre i ne portent que sur des
        jours strictement antérieurs au jour de i : invariants par troncature.
        """
        p = _validated(params)
        n_sma = p["sma_period"]

        idx = df.index
        day = idx.normalize()
        dclose = df["close"].groupby(day).last()          # clôture de chaque jour serveur

        prev_close = dclose.shift(1)                       # dernier jour COMPLET
        if n_sma > 0:
            prev_sma = dclose.rolling(n_sma).mean().shift(1)
        else:
            prev_sma = pd.Series(np.nan, index=dclose.index)

        day_ord = day.asi8 // NS_PER_DAY
        first_of_day = np.empty(len(idx), dtype=bool)
        if len(idx):
            first_of_day[0] = True
            first_of_day[1:] = day_ord[1:] != day_ord[:-1]

        out = pd.DataFrame(index=idx)
        out["close"] = df["close"].to_numpy(dtype=float)
        out["dow"] = idx.dayofweek.to_numpy().astype(np.int64)
        out["day_ord"] = day_ord.astype(np.int64)
        out["first_of_day"] = first_of_day.astype(float)   # float : réellement comparé par R1
        out["prev_day_close"] = prev_close.reindex(day).to_numpy(dtype=float)
        out["prev_day_sma"] = prev_sma.reindex(day).to_numpy(dtype=float)
        return out

    # ── signaux ────────────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        p = _validated(params)
        n_sma, mode, guard, open_dow = (p["sma_period"], p["entry_mode"],
                                        p["guard_pct"], p["open_dow"])

        n = min(end_idx, len(data))
        idx = data.index
        close = data["close"].to_numpy()
        dow = data["dow"].to_numpy()
        day_ord = data["day_ord"].to_numpy()
        first_of_day = data["first_of_day"].to_numpy() > 0.5
        prev_close = data["prev_day_close"].to_numpy()
        prev_sma = data["prev_day_sma"].to_numpy()

        out: list[Signal] = []
        done_day = None                       # un seul achat par jour d'ouverture
        for i in range(n):
            if dow[i] != open_dow or day_ord[i] == done_day:
                continue
            if mode == "first_bar" and not first_of_day[i]:
                continue

            if n_sma > 0:
                sma = prev_sma[i]
                if not np.isfinite(sma):
                    continue                  # moins de N jours complets : pas d'avis
                # `first_bar` compare la dernière clôture journalière complète
                # (vendredi) ; `any_bar` compare le prix courant, c'est-à-dire le
                # close de la barre en cours — les deux sont strictement passés.
                ref = prev_close[i] if mode == "first_bar" else close[i]
                if not np.isfinite(ref) or ref >= sma:
                    continue
            elif not np.isfinite(prev_close[i]):
                continue                      # cellule de référence : au moins un jour complet

            entry = float(close[i])
            stop = entry * (1.0 - guard)      # garde catastrophe, pas un stop de gestion
            done_day = day_ord[i]
            out.append(Signal(
                timestamp=pd.Timestamp(idx[i]).to_pydatetime(),
                symbol=self._symbol, side=Side.LONG,
                entry=entry, stop=stop, target=None,
                reason=(f"lundi{'' if n_sma == 0 else f' sous SMA{n_sma} D1'}"
                        f" · {mode} · garde {guard:.0%}"),
                meta={"sma": (float(prev_sma[i]) if n_sma > 0 else None),
                      "prev_day_close": float(prev_close[i]) if np.isfinite(prev_close[i]) else None,
                      "entry_mode": mode},
            ))
        return out

    # ── live : même code que le backtest (R5) ─────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        self._symbol = ctx.symbol
        data = self.precompute(ctx.bars, self.params)
        sigs = self.generate_signals(data, self.params, len(ctx.bars))
        if sigs and pd.Timestamp(sigs[-1].timestamp) == pd.Timestamp(ctx.bars.index[-1]):
            return sigs[-1]
        return None

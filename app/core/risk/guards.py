"""
COUCHE DE RISQUE — LES BORNES QUE LA STRATÉGIE NE PEUT PAS TOUCHER
===================================================================

Toute intention de position passe par ici avant de devenir un ordre. La
stratégie propose, cette couche dispose. C'est la matérialisation de R2 :
la stratégie décide du SENS et des NIVEAUX, jamais de la TAILLE ni du droit
d'agir.

POURQUOI LA SÉPARATION COMPTE PLUS QUE LES SEUILS
--------------------------------------------------
Deux sources examinées placent leurs garde-fous dans le prompt de l'agent
(« maximum 5 % par position, pas d'options »). Un garde-fou écrit dans un prompt
est une suggestion : le modèle peut la négliger un jour de forte conviction, et
c'est précisément ce jour-là qu'elle servait.

Une troisième source le formule correctement : les bornes vivent dans une couche
« that the model literally cannot touch », et « how much damage it was even
allowed to do was locked in before it started ». C'est cette version-là qui est
implémentée ici.

Conséquence pratique : aucune stratégie n'importe ce module. C'est
l'orchestrateur qui l'applique, entre la stratégie et le courtier.

LES QUATRE BORNES
-----------------
1. plafond par position       — aucune position ne dépasse X % du capital
2. plafond du livre           — l'exposition totale ne dépasse pas Y %
3. stop obligatoire           — refus net d'un ordre sans stop, jamais de valeur
                                par défaut inventée
4. coupe-circuit quotidien    — au-delà de Z % de perte sur la journée, la
                                session s'arrête et ne rouvre pas d'elle-même

LE COUPE-CIRCUIT NE SE DÉSARME PAS TOUT SEUL
---------------------------------------------
Une fois déclenché, il reste actif jusqu'à un `reset_day()` explicite. Un
coupe-circuit qui se réarme parce que l'equity est remontée n'est pas un
coupe-circuit : c'est ce qui transforme une mauvaise journée en compte vide.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from core.contracts.strategy import Side, Signal


class Rejection(str, Enum):
    """Motifs de refus. Énumérés plutôt que textuels pour être comptés et
    tracés — un refus silencieux serait pire qu'une absence de contrôle."""
    NO_STOP = "stop absent ou incohérent"
    STOP_AT_ENTRY = "stop confondu avec l'entrée : risque nul, taille infinie"
    POSITION_CAP = "dépasse le plafond par position"
    BOOK_CAP = "dépasse le risque cumulé autorisé du livre"
    LEVERAGE_CAP = "dépasse le levier notionnel autorisé"
    DAILY_HALT = "coupe-circuit quotidien armé"
    ALREADY_OPEN = "position déjà ouverte sur cet instrument"
    NO_CAPITAL = "capital nul ou négatif"


@dataclass(frozen=True)
class RiskLimits:
    """Les bornes. Fixées avant le démarrage, jamais par la stratégie.

    Valeurs par défaut délibérément conservatrices : elles doivent être
    desserrées consciemment, pas resserrées après un incident.

    DEUX PLAFONDS DE LIVRE, ET C'EST VOULU
    ---------------------------------------
    Une première version ne bornait que l'exposition NOTIONNELLE rapportée au
    capital. Sur un instrument à levier c'est absurde : risquer 2 % du capital
    avec un stop à 50 pips implique un notionnel largement supérieur au capital
    lui-même. Le plafond écrasait donc toutes les positions à des tailles
    dérisoires (test : 13,64 € risqués au lieu de 200 €).

    Les deux grandeurs mesurent des choses différentes et il faut les deux :

    - `max_book_risk_pct` — **la borne qui compte**. Somme des montants risqués
      si TOUS les stops sont touchés le même jour. C'est la perte réellement
      encourue, et elle est comparable au capital.
    - `max_book_leverage` — contrainte de marge du courtier, pas de risque.
      Notionnel cumulé rapporté au capital.
    """
    max_position_pct: float = 0.01      # 1 % du capital risqué par position
    max_book_risk_pct: float = 0.06     # 6 % risqués au total, tous stops touchés
    max_book_leverage: float = 5.0      # notionnel cumulé <= 5x le capital
    max_daily_loss_pct: float = 0.03    # -3 % sur la journée -> arrêt
    max_open_positions: int = 6
    one_position_per_symbol: bool = True

    def __post_init__(self):
        for name in ("max_position_pct", "max_book_risk_pct", "max_daily_loss_pct"):
            v = getattr(self, name)
            if not (0.0 < v <= 1.0):
                raise ValueError(f"{name} doit être dans ]0, 1] — reçu {v}")
        if self.max_book_leverage <= 0:
            raise ValueError("max_book_leverage doit être strictement positif")
        if self.max_position_pct > self.max_book_risk_pct:
            raise ValueError(
                "max_position_pct > max_book_risk_pct : une seule position "
                "pourrait dépasser le risque autorisé du livre entier")


@dataclass
class Decision:
    """Verdict de la couche sur une intention. `size` n'a de sens que si
    `approved`."""
    approved: bool
    size: float = 0.0                       # unités (lots, actions…)
    risk_amount: float = 0.0                # montant risqué si le stop est touché
    reason: Optional[Rejection] = None
    detail: str = ""

    def __bool__(self) -> bool:
        return self.approved


@dataclass
class OpenPosition:
    symbol: str
    side: Side
    size: float
    entry: float
    stop: float
    strategy_id: str = ""
    risk_amount: float = 0.0

    @property
    def exposure(self) -> float:
        return abs(self.size * self.entry)


class RiskLayer:
    """Garde-fou d'exécution. Instancié par l'orchestrateur, jamais par une
    stratégie.

        risk = RiskLayer(capital=10_000, limits=RiskLimits())
        d = risk.evaluate(signal, value_per_unit=1.0)
        if d:
            broker.send(signal, d.size)
            risk.register(...)
    """

    def __init__(self, capital: float, limits: Optional[RiskLimits] = None):
        if capital <= 0:
            raise ValueError("capital doit être strictement positif")
        self.limits = limits or RiskLimits()
        self.starting_capital = float(capital)
        self.capital = float(capital)
        self._day_start_capital = float(capital)
        self._day = None
        self._halted = False
        self._halt_reason = ""
        self.positions: dict[str, OpenPosition] = {}
        self.rejections: dict[Rejection, int] = {}

    # ── État ────────────────────────────────────────────────────────────────
    @property
    def halted(self) -> bool:
        return self._halted

    @property
    def book_exposure(self) -> float:
        """Notionnel cumule — contrainte de marge."""
        return sum(p.exposure for p in self.positions.values())

    @property
    def book_risk(self) -> float:
        """Perte cumulee si TOUS les stops sont touches. La borne qui compte."""
        return sum(p.risk_amount for p in self.positions.values())

    @property
    def daily_pnl_pct(self) -> float:
        if self._day_start_capital <= 0:
            return 0.0
        return (self.capital - self._day_start_capital) / self._day_start_capital

    def _reject(self, reason: Rejection, detail: str = "") -> Decision:
        self.rejections[reason] = self.rejections.get(reason, 0) + 1
        return Decision(approved=False, reason=reason, detail=detail)

    # ── Le contrôle ─────────────────────────────────────────────────────────
    def evaluate(self, signal: Signal, value_per_unit: float = 1.0) -> Decision:
        """Autorise ou refuse, et dimensionne si autorisé.

        `value_per_unit` convertit une unité de prix en monnaie du compte pour
        une unité de position (valeur du pip par lot en FX, 1.0 en actions).

        La taille découle du RISQUE, jamais d'une fraction du capital : on
        risque `max_position_pct` du capital sur la distance entrée-stop. Une
        stratégie dont le stop est large prend donc mécaniquement une position
        plus petite. C'est le seul dimensionnement défendable — celui qui égalise
        la perte, pas la mise.
        """
        if self._halted:
            return self._reject(Rejection.DAILY_HALT, self._halt_reason)
        if self.capital <= 0:
            return self._reject(Rejection.NO_CAPITAL, f"capital = {self.capital:.2f}")

        # Borne 3 — stop obligatoire. On REFUSE, on n'invente pas.
        if signal.stop is None:
            return self._reject(Rejection.NO_STOP, "aucun stop fourni")
        risk_distance = abs(float(signal.entry) - float(signal.stop))
        if risk_distance <= 0:
            return self._reject(
                Rejection.STOP_AT_ENTRY,
                f"entrée {signal.entry} = stop {signal.stop}")
        # Cohérence de sens : un stop du mauvais côté n'est pas un stop.
        if signal.side == Side.LONG and float(signal.stop) >= float(signal.entry):
            return self._reject(Rejection.NO_STOP, "LONG avec stop au-dessus de l'entrée")
        if signal.side == Side.SHORT and float(signal.stop) <= float(signal.entry):
            return self._reject(Rejection.NO_STOP, "SHORT avec stop sous l'entrée")

        if (self.limits.one_position_per_symbol
                and signal.symbol in self.positions):
            return self._reject(Rejection.ALREADY_OPEN, signal.symbol)
        if len(self.positions) >= self.limits.max_open_positions:
            return self._reject(
                Rejection.BOOK_CAP,
                f"{len(self.positions)} positions ouvertes, "
                f"maximum {self.limits.max_open_positions}")

        # Borne 1 — dimensionnement par le risque.
        risk_budget = self.capital * self.limits.max_position_pct
        unit_risk = risk_distance * value_per_unit
        size = risk_budget / unit_risk
        if size <= 0:
            return self._reject(Rejection.POSITION_CAP, "taille calculée nulle")

        # Borne 2a — risque cumulé du livre. C'est la borne qui compte : combien
        # perd-on si TOUS les stops sont touchés le même jour ?
        risk_room = self.capital * self.limits.max_book_risk_pct - self.book_risk
        if risk_room <= 0:
            return self._reject(
                Rejection.BOOK_CAP,
                f"risque du livre déjà à {self.book_risk:.0f} pour un plafond "
                f"de {self.capital * self.limits.max_book_risk_pct:.0f}")
        if risk_budget > risk_room:
            # On réduit plutôt que de refuser : une position plus petite reste
            # conforme à l'intention de la stratégie, qui ne parlait pas taille.
            size *= risk_room / risk_budget
            risk_budget = risk_room

        # Borne 2b — levier notionnel. Contrainte de marge, pas de risque.
        exposure = abs(size * float(signal.entry))
        lev_room = self.capital * self.limits.max_book_leverage - self.book_exposure
        if lev_room <= 0:
            return self._reject(
                Rejection.LEVERAGE_CAP,
                f"levier déjà à {self.book_exposure / self.capital:.2f}x")
        if exposure > lev_room:
            size *= lev_room / exposure
            exposure = lev_room

        return Decision(approved=True, size=size,
                        risk_amount=size * unit_risk,
                        detail=f"expo {exposure:.0f}, risque {size * unit_risk:.2f}")

    # ── Suivi ───────────────────────────────────────────────────────────────
    def register(self, signal: Signal, size: float, strategy_id: str = "",
                 risk_amount: float = 0.0) -> None:
        self.positions[signal.symbol] = OpenPosition(
            symbol=signal.symbol, side=signal.side, size=size,
            entry=float(signal.entry), stop=float(signal.stop),
            strategy_id=strategy_id, risk_amount=risk_amount)

    def close(self, symbol: str, pnl: float) -> None:
        """Enregistre une clôture et arme le coupe-circuit si le seuil est franchi."""
        self.positions.pop(symbol, None)
        self.capital += pnl
        if self.daily_pnl_pct <= -self.limits.max_daily_loss_pct:
            self._halted = True
            self._halt_reason = (
                f"perte du jour {100 * self.daily_pnl_pct:.2f} % "
                f"<= seuil -{100 * self.limits.max_daily_loss_pct:.2f} %")

    def start_day(self, today: Optional[date] = None) -> None:
        """Ouvre une journée : fige le capital de référence et désarme le
        coupe-circuit. Appel EXPLICITE — il ne se désarme jamais seul."""
        self._day = today
        self._day_start_capital = self.capital
        self._halted = False
        self._halt_reason = ""

    def status(self) -> dict:
        return {
            "capital": round(self.capital, 2),
            "halted": self._halted,
            "halt_reason": self._halt_reason,
            "daily_pnl_pct": round(100 * self.daily_pnl_pct, 3),
            "open_positions": len(self.positions),
            "book_exposure": round(self.book_exposure, 2),
            "book_leverage": round(
                self.book_exposure / self.capital, 2) if self.capital > 0 else None,
            "book_risk": round(self.book_risk, 2),
            "book_risk_pct": round(
                100 * self.book_risk / self.capital, 2) if self.capital > 0 else None,
            "rejections": {k.name: v for k, v in self.rejections.items()},
        }

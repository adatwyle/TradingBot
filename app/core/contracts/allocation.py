"""
CONTRAT ALLOCATION — pour les stratégies qui répartissent, pas qui entrent/sortent
==================================================================================

POURQUOI UN SECOND CONTRAT
---------------------------
`StrategyModule` suppose une stratégie **épisodique** : on entre, on place un
stop, on vise une cible, on sort. C'est le bon modèle pour du swing ou du
breakout.

Il ne décrit PAS une stratégie d'allocation, qui est **toujours investie** et se
contente de changer la répartition. « Détenir le Nasdaq au-dessus de la MM200,
l'or en dessous » n'a ni entrée, ni stop, ni cible — l'invalidation *est* la
bascule suivante.

L'agent s04 l'a démontré plutôt qu'affirmé : passée de force dans le contrat
épisodique, cette règle produisait **1 trade sur 5 ans**. Le harnais ne mesurait
pas la stratégie, il mesurait son propre malentendu.

Deux des cinq stratégies publiées par cette source sont des allocations — et ce
sont les deux seules avec des chiffres. Sans ce contrat, on ne peut pas les
tester.

CE QUI CHANGE PAR RAPPORT À `StrategyModule`
---------------------------------------------
| | Épisodique | Allocation |
|---|---|---|
| Sortie | `Signal(entry, stop, target)` | poids cible par instrument |
| R3 stop obligatoire | oui | **sans objet** — voir plus bas |
| Mesure | P&L en R par trade | **courbe d'equity** |
| Référence | — | **buy & hold intégré** |

R3 ET LES STRATÉGIES D'ALLOCATION
----------------------------------
R3 (stop obligatoire) protège une position individuelle contre une perte
illimitée. Une allocation n'a pas de position isolée à protéger : le contrôle du
risque est la règle de répartition elle-même, plus le halt de portefeuille de
`core/risk/`.

R3 est donc **explicitement hors périmètre** ici. En échange, une allocation doit
déclarer son `max_single_weight` — plafond d'exposition à un seul instrument.
Un stop bidon inventé pour satisfaire un validateur serait pire que pas de stop
du tout : il donnerait l'illusion d'une protection.

LES AUTRES RÈGLES RESTENT
--------------------------
R1 causalité, R2 séparation stratégie/risque (les poids sont des *intentions*,
la couche risque décide de l'exposition réelle), R7 manifest, R8 ledger,
R9 moteur commun.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pandas as pd


@dataclass(frozen=True)
class Allocation:
    """Répartition cible à un instant donné.

    `weights` : symbole -> poids dans [0, 1]. La somme peut être < 1 — le
    reliquat est du cash. Un dictionnaire vide signifie « tout en cash ».

    Ce sont des **intentions**, pas des ordres. La couche risque les traduit en
    exposition réelle selon le capital alloué par le dashboard (R2).
    """
    timestamp: datetime
    weights: dict[str, float]
    reason: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for sym, w in self.weights.items():
            if not (0.0 <= w <= 1.0):
                raise ValueError(f"poids hors [0,1] pour {sym} : {w}")
        total = sum(self.weights.values())
        if total > 1.0 + 1e-9:
            raise ValueError(
                f"somme des poids = {total:.4f} > 1. Le levier ne se déclare pas "
                f"ici : il appartient à core/risk/, jamais à la stratégie (R2)."
            )

    @property
    def cash_weight(self) -> float:
        return max(0.0, 1.0 - sum(self.weights.values()))

    @property
    def is_all_cash(self) -> bool:
        return sum(self.weights.values()) < 1e-9


@dataclass
class AllocationManifest:
    """Métadonnées d'une stratégie d'allocation (équivalent de StrategyManifest)."""
    strategy_id: str
    display_name: str
    version: str
    magic_number: int
    author: str
    source: str
    universe: list[str]              # instruments entre lesquels elle répartit
    timeframe: str
    warmup_bars: int
    param_grid: dict[str, list]
    default_params: dict[str, Any]

    # Propre à l'allocation
    max_single_weight: float = 1.0   # plafond sur un seul instrument
    rebalance: str = "on_change"     # on_change | daily | weekly | monthly
    allow_cash: bool = True

    status: str = "RESEARCH"
    notes: str = ""

    def __post_init__(self):
        if not (0.0 < self.max_single_weight <= 1.0):
            raise ValueError("max_single_weight doit être dans ]0, 1]")
        if len(self.universe) < 1:
            raise ValueError("universe ne peut pas être vide")


class AllocationModule(abc.ABC):
    """Contrat des stratégies d'allocation.

    Cycle :
        manifest()            la plateforme découvre la stratégie
        precompute(bars, p)   indicateurs, une fois par (univers, params)
        generate_allocations() chemin backtest, vectorisé
        on_bar(ctx)           chemin live, une décision par barre close
    """

    STRATEGY_ID: str = ""
    MAGIC_NUMBER: int = 0

    def __init__(self, params: Optional[dict] = None):
        if not self.STRATEGY_ID:
            raise ValueError(f"{type(self).__name__} doit définir STRATEGY_ID")
        if not self.MAGIC_NUMBER:
            raise ValueError(f"{type(self).__name__} doit définir MAGIC_NUMBER")
        self.params = dict(self.manifest().default_params)
        if params:
            unknown = set(params) - set(self.params)
            if unknown:
                raise ValueError(f"paramètres inconnus : {sorted(unknown)}")
            self.params.update(params)

    @abc.abstractmethod
    def manifest(self) -> AllocationManifest:
        """Description statique. Pure — aucune I/O, aucun état."""

    @abc.abstractmethod
    def precompute(self, bars: dict[str, pd.DataFrame], params: dict) -> Any:
        """Indicateurs, calculés une fois.

        `bars` : symbole -> DataFrame OHLC, **alignés sur un index commun**.
        Doit être causal : la valeur à l'indice i ne dépend que de [0, i].
        """

    @abc.abstractmethod
    def generate_allocations(self, data: Any, params: dict,
                             end_idx: int) -> list[Allocation]:
        """Répartitions cibles sur [0, end_idx).

        Même contrat `end_idx` que le chemin épisodique : rien au-delà ne doit
        influencer la sortie. L'invariant de troncature R1 s'applique tel quel —
        `core/validation/causality.py` sait tester les deux contrats.

        Il n'est pas nécessaire d'émettre une allocation par barre : seuls les
        **changements** comptent. Le moteur conserve la dernière répartition
        connue jusqu'à la suivante.
        """

    @abc.abstractmethod
    def on_bar(self, ctx: "AllocationContext") -> Optional[Allocation]:
        """Chemin live. Retourner None = conserver la répartition actuelle."""

    def health(self) -> dict:
        return {}


@dataclass
class AllocationContext:
    """Ce que la plateforme fournit à chaque barre close, en live.

    Omissions volontaires, comme pour le contrat épisodique : ni solde, ni
    exposition réelle, ni positions des autres stratégies. La stratégie exprime
    une intention ; elle ne sait pas ce qu'on en fait.
    """
    universe: list[str]
    timeframe: str
    bars: dict[str, pd.DataFrame]     # historique jusqu'à la barre close incluse
    now: datetime
    spreads: dict[str, float]
    current_weights: dict[str, float] = field(default_factory=dict)

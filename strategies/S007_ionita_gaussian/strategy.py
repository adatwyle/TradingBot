"""
Gaussian Channel Trend Radar — stratégie s07_ionita_gaussian
=============================================================

Source  : https://www.youtube.com/watch?v=fdGCGXcDByk  (Michael Ionita)
Règles  : transcrites depuis `frames_prompt/t12m04s.png` et `t12m12s.png`,
          référence interne de l'auteur `TR-GC-Crypto-LS-2`.
Analyse : `research/ANALYSIS.md` — lire AVANT de modifier ce fichier.

CONTRAT RETENU : ALLOCATION, PAS ÉPISODIQUE
--------------------------------------------
La source décrit un portefeuille : N positions simultanées, dimensionnées en
pourcentage de NAV (8 / 2 / 3 / 5 %), sans aucun stop de prix — les sorties sont
des conditions d'indicateur. C'est la définition du contrat `AllocationModule`.

Forcer ça dans `Signal(entry, stop, target)` obligerait à inventer un stop qui
n'existe pas dans la source, et à traiter comme des trades indépendants des
positions dont l'intérêt est justement d'être détenues ensemble. Sur ce projet,
ce malentendu a déjà produit « 1 trade sur 5 ans » (cf. `core/contracts/
allocation.py`). Le harnais mesurait sa propre erreur de modélisation.

Bénéfice décisif du contrat d'allocation ici : `run_allocation()` rend
systématiquement le buy & hold de chaque constituant ET l'équipondéré naïf.
L'auteur affirme battre le buy & hold ; c'est exactement la question que le
harnais répond nativement, et c'est le critère n°1 de `docs/METHODOLOGY.md`.

CE QUE CETTE IMPLÉMENTATION EST — ET N'EST PAS
-----------------------------------------------
Elle reproduit le MÉCANISME du canal gaussien tel que le prompt le décrit.
Elle NE reproduit PAS le « Trend Radar », produit propriétaire de Signum, qui
faisait deux choses distinctes :
  (a) sélectionner l'univers (quelles pièces sont éligibles),
  (b) le classer par rang de marché (les 50 premiers).
Aucun des deux n'est disponible. L'univers est donc FIXE et déclaré dans le
manifest. La conséquence est traitée frontalement dans `research/ANALYSIS.md` :
sans cette séparation, un bon résultat serait inattribuable.

LES QUATRE SUBSTITUTIONS, TOUTES DÉCLARÉES
-------------------------------------------
1. `Trend Radar` -> univers fixe du manifest. « Plus dans le radar » comme
   condition de sortie disparaît : sur un univers fixe, elle ne se déclenche
   jamais. Écart assumé, il rend la stratégie PLUS patiente que l'originale.
2. `rang de marché, 50 premiers` -> sans effet, l'univers testé fait moins de
   50 lignes. L'effet de sélection est donc neutralisé, ce qui est précisément
   ce qu'on veut pour isoler le canal.
3. `breakoutDate` (propriétaire) -> proxy Donchian explicite : date du dernier
   close supérieur au plus haut des `donchian_lookback` closes précédents.
   Le paramètre `sizing_mode="uniform"` permet de neutraliser ce proxy et de
   mesurer ce que le sizing 8/2 apporte réellement.
4. `prix d'entrée moyen dérivé du collatéral` (pour le take-profit short à
   0,65x) -> prix d'ouverture effectif de la jambe short, suivi en interne.

LES SHORTS ET LA LIMITE DU CONTRAT
-----------------------------------
`Allocation.weights` impose des poids dans [0, 1] : un poids négatif lève une
exception. Le contrat ne sait donc pas exprimer une jambe short.

Ce n'est pas contourné en douce. Deux variantes distinctes sont produites :
  - `enable_shorts=False` : univers = actifs réels, benchmarks propres. C'est
    la comparaison qui compte pour le critère n°1.
  - `enable_shorts=True`  : les jambes short sont portées par des séries
    synthétiques `SYM~S` construites en amont (cf. `run_backtest.py`), dont le
    rendement open->open est l'exact opposé de celui de `SYM`. Le moteur les
    traite comme des instruments ordinaires ; les benchmarks de ce run sont donc
    pollués et ne sont PAS lus — seule la courbe de la stratégie l'est, comparée
    aux benchmarks du run long-only sur la même période.

R2 — CE FICHIER NE CALCULE PAS DE TAILLE DE POSITION
-----------------------------------------------------
Les 8 / 2 / 3 / 5 % sont des POIDS RELATIFS d'intention, pas des lots ni un
risque. La couche `core/risk/` décide de l'exposition réelle. C'est exactement
ce que le contrat d'allocation appelle une intention.

`weight_mode` mérite une explication, parce que c'est le point où une
reproduction naïve devient une comparaison vide. Sur un univers de 50 pièces,
des poids de 8 % laissent le portefeuille pleinement investi. Sur l'univers de
deux cryptos dont nous disposons réellement, 8 % + 8 % = 16 % : on comparerait
un portefeuille investi à 16 % contre un buy & hold investi à 100 %. L'écart
mesurerait la taille du compte, pas la qualité du signal.

  - `weight_mode="absolute"`   : fidèle au prompt (8/2/3/5 % de NAV). Honnête
    seulement si l'univers est assez large pour absorber le capital.
  - `weight_mode="normalized"` : les mêmes poids relatifs, renormalisés pour que
    le portefeuille soit pleinement investi quand au moins une ligne est active.
    Isole le TIMING du canal de la taille de l'univers. C'est le mode qui rend
    la comparaison au buy & hold interprétable.

Les deux sont exécutés et rapportés. Aucun n'est « le bon » : ils répondent à
deux questions différentes, et le dire est plus utile que d'en cacher un.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.allocation import (
    Allocation, AllocationContext, AllocationManifest, AllocationModule,
)

if __package__ in (None, ""):
    # Loaded standalone (spec_from_file_location, no parent package): load the
    # sibling gaussian.py explicitly under a qualified module name. No sys.path
    # mutation, no bare "gaussian" registration in sys.modules — the module
    # lives in a local variable only.
    import importlib.util as _ilu
    import os as _os
    _spec = _ilu.spec_from_file_location(
        "strategies.S007_ionita_gaussian.gaussian",
        _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "gaussian.py"))
    _gaussian = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_gaussian)
    gaussian_channel = _gaussian.gaussian_channel
else:
    from .gaussian import gaussian_channel

SHORT_SUFFIX = "~S"


def short_symbol(sym: str) -> str:
    return f"{sym}{SHORT_SUFFIX}"


def is_short_symbol(sym: str) -> bool:
    return sym.endswith(SHORT_SUFFIX)


def base_symbol(sym: str) -> str:
    return sym[: -len(SHORT_SUFFIX)] if is_short_symbol(sym) else sym


class Strategy(AllocationModule):
    STRATEGY_ID = "s07_ionita_gaussian"
    MAGIC_NUMBER = 130007

    # L'univers est injectable pour que le même code serve les deux univers de
    # test (crypto disponible / panier large) sans dupliquer la logique. R7 est
    # respecté : le manifest reste la source de vérité, il est simplement
    # paramétré à la construction plutôt que figé dans le fichier.
    DEFAULT_UNIVERSE = ["BTCUSD", "ETHUSD"]

    def __init__(self, params: Optional[dict] = None,
                 universe: Optional[list[str]] = None):
        self._universe = list(universe) if universe else list(self.DEFAULT_UNIVERSE)
        super().__init__(params)

    # ── Manifest ────────────────────────────────────────────────────────────
    def manifest(self) -> AllocationManifest:
        return AllocationManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Gaussian Channel Trend Radar (Ionita)",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s07_ionita_gaussian",
            source="https://www.youtube.com/watch?v=fdGCGXcDByk",
            universe=list(self._universe),
            timeframe="D1",
            # 144 barres de période d'échantillonnage, 4 pôles. Le transitoire
            # d'amorçage du filtre est de l'ordre de la période ; on prend 3x
            # pour que rien de ce qui sert à décider n'en dépende.
            warmup_bars=450,
            param_grid={
                # Grille délibérément petite. 5 x 3 x 3 = 45 configurations,
                # soit ~2,25 réussites attendues par pur hasard au seuil 5 %
                # (docs/METHODOLOGY.md §6). Une grille de 500 cellules trouve un
                # meilleur faux positif, pas un meilleur edge.
                "period": [72, 108, 144, 180, 216],
                "poles": [3, 4, 5],
                "mult": [1.0, 1.414, 2.0],
            },
            default_params={
                # ── Canal gaussien : réglages par défaut du Pine Script d'origine
                "period": 144,
                "poles": 4,
                "mult": 1.414,
                "source": "hlc3",
                # ── Règles du prompt
                "enable_shorts": False,
                "btc_regime_symbol": "BTCUSD",
                "short_tp_ratio": 0.65,       # étape 5 : TP short à 0,65x l'entrée
                "bear_touch_ratio": 0.98,     # étape 7b : ohlc.h >= 0,98 x filter
                "w_long_fresh": 0.08,         # étape 6 : cassure < 25 j
                "w_long_stale": 0.02,         # étape 6 : cassure ancienne / absente
                "w_short_hedge": 0.03,        # étape 7a
                "w_short_bear": 0.05,         # étape 7b
                "breakout_max_age_days": 25,  # étape 6
                # ── Substitutions déclarées
                "donchian_lookback": 55,      # proxy de `breakoutDate`
                "sizing_mode": "donchian",    # donchian | uniform
                "weight_mode": "normalized",  # normalized | absolute
                "max_positions": 50,          # étape 6/7 : « take the first 50 rows »
            },
            max_single_weight=1.0,
            rebalance="daily",
            allow_cash=True,
            status="RESEARCH",
            notes="Contrat allocation. Trend Radar non reproductible : univers fixe. "
                  "Voir research/ANALYSIS.md pour les 4 substitutions.",
        )

    # ── Indicateurs ─────────────────────────────────────────────────────────
    def precompute(self, bars: dict[str, pd.DataFrame], params: dict) -> Any:
        """Canal gaussien pour chaque symbole, rendu comme UN SEUL DataFrame.

        LE FORMAT DE RETOUR EST UN CHOIX DÉLIBÉRÉ, PAS UNE COMMODITÉ
        -------------------------------------------------------------
        `core/validation/causality.py::_compare_precompute` commence par :

            if not isinstance(data_full, pd.DataFrame): return leaks

        Autrement dit, un `precompute()` qui renvoie un dict — le réflexe naturel
        pour une stratégie multi-actifs — **échappe silencieusement** au contrôle
        de la couche indicateur. Le gardien afficherait « R1 PASSÉ » sans avoir
        regardé une seule valeur du filtre gaussien. C'est arrivé sur s91.

        On rend donc un DataFrame à plat, une colonne par (symbole, série) :
        `BTCUSD__filter`, `BTCUSD__upper`, ... Toutes les colonnes sont
        numériques, donc toutes sont réellement comparées barre à barre entre le
        run complet et le run tronqué. Le filtre gaussien est ainsi sous
        surveillance effective, ce qui est le but.

        `validate_r1.py` archive la liste exacte des colonnes inspectées : un
        « R1 passé » ne vaut que la surface qu'il couvre, et cette surface doit
        être écrite noir sur blanc.
        """
        period = int(params["period"])
        poles = int(params["poles"])
        mult = float(params["mult"])
        src = str(params["source"])
        lookback = int(params["donchian_lookback"])

        frames = []
        for sym in sorted(bars):
            df = bars[sym]
            gc = gaussian_channel(df, period, poles, mult, src)

            close = df["close"]
            # Proxy de `breakoutDate` : dernier close ayant dépassé le plus haut
            # des `lookback` closes STRICTEMENT précédents. Le `shift(1)` est ce
            # qui rend la comparaison causale — sans lui, le maximum de la
            # fenêtre inclut la barre courante et la condition serait triviale.
            prior_max = close.shift(1).rolling(lookback, min_periods=lookback).max()
            is_breakout = (close > prior_max).fillna(False)

            # Nombre de barres écoulées depuis la dernière cassure. Construit par
            # report en avant d'un index, donc strictement passé.
            pos = pd.Series(np.arange(len(close), dtype=float), index=close.index)
            last_bo = pos.where(is_breakout).ffill()
            age = pos - last_bo          # NaN tant qu'aucune cassure n'a eu lieu

            block = pd.DataFrame({
                f"{sym}__open": df["open"].astype(float),
                f"{sym}__high": df["high"].astype(float),
                f"{sym}__close": close.astype(float),
                f"{sym}__filter": gc["filter"],
                f"{sym}__upper": gc["upper"],
                f"{sym}__lower": gc["lower"],
                f"{sym}__trend": gc["trend"],
                f"{sym}__bo_age": age,
            })
            frames.append(block)

        out = pd.concat(frames, axis=1)
        out.attrs["symbols"] = sorted(bars)
        return out

    # ── Décisions ───────────────────────────────────────────────────────────
    def generate_allocations(self, data: Any, params: dict,
                             end_idx: int) -> list[Allocation]:
        """Rejoue les huit étapes du prompt, barre par barre, sur [0, end_idx).

        Une allocation est émise à CHAQUE barre à partir du warmup, et non
        seulement aux changements. Motif : la stratégie d'origine est une routine
        quotidienne qui réévalue tout le portefeuille chaque jour. Émettre
        l'état complet chaque jour est la traduction fidèle, et évite un piège du
        moteur — une `Allocation` décrit le portefeuille ENTIER, un symbole
        absent pèse zéro.

        R1 : rien au-delà de `end_idx` n'est lu. La boucle s'arrête à
        `end_idx`, les indicateurs sont causaux, et l'état du portefeuille est
        construit de gauche à droite. L'invariant est vérifié mécaniquement par
        `validate_r1.py`, pas supposé ici.
        """
        symbols = list(data.attrs.get("symbols") or self._universe)
        n = min(int(end_idx), len(data))
        warmup = self.manifest().warmup_bars
        if n <= warmup + 1:
            return []

        col = {s: {k: data[f"{s}__{k}"].to_numpy()
                   for k in ("open", "high", "close", "filter", "upper",
                             "trend", "bo_age")}
               for s in symbols}
        index = data.index

        enable_shorts = bool(params["enable_shorts"])
        btc_sym = str(params["btc_regime_symbol"])
        tp_ratio = float(params["short_tp_ratio"])
        touch = float(params["bear_touch_ratio"])
        w_fresh = float(params["w_long_fresh"])
        w_stale = float(params["w_long_stale"])
        w_hedge = float(params["w_short_hedge"])
        w_bear = float(params["w_short_bear"])
        max_age = float(params["breakout_max_age_days"])
        sizing_mode = str(params["sizing_mode"])
        weight_mode = str(params["weight_mode"])
        max_pos = int(params["max_positions"])

        # État du portefeuille : symbole -> ("LONG"|"SHORT", poids, prix d'entrée)
        held: dict[str, tuple[str, float, float]] = {}
        out: list[Allocation] = []

        for i in range(warmup, n):
            exited_this_run: set[str] = set()

            # ── Étape 3 : régime BTC ────────────────────────────────────────
            # « BTC est en DOWNTREND si son CLOSE est SOUS son gc.filter. »
            btc_down = False
            if btc_sym in col:
                c, f = col[btc_sym]["close"][i], col[btc_sym]["filter"][i]
                btc_down = bool(np.isfinite(c) and np.isfinite(f) and c < f)

            # ── Étape 4 : sorties longues ───────────────────────────────────
            # « sortir à 100 % quand le CLOSE est SOUS la bande haute. »
            # La condition « n'est plus dans le Trend Radar » ne peut pas se
            # déclencher : l'univers est fixe. Écart assumé (cf. en-tête).
            for sym in [s for s, (side, _, _) in held.items() if side == "LONG"]:
                c, u = col[sym]["close"][i], col[sym]["upper"][i]
                if not (np.isfinite(c) and np.isfinite(u)) or c < u:
                    del held[sym]
                    exited_this_run.add(sym)

            # ── Étape 5 : sorties courtes ───────────────────────────────────
            for sym in [s for s, (side, _, _) in held.items() if side == "SHORT"]:
                c, f = col[sym]["close"][i], col[sym]["filter"][i]
                entry_px = held[sym][2]
                if not (np.isfinite(c) and np.isfinite(f)):
                    del held[sym]; exited_this_run.add(sym); continue
                stop = c > f                                   # STOP
                take = entry_px > 0 and c <= tp_ratio * entry_px   # TAKE PROFIT
                if stop or take:
                    del held[sym]
                    exited_this_run.add(sym)

            # ── Étape 6 : entrées longues ───────────────────────────────────
            # « ENTRER LONG quand le CLOSE a croisé AU-DESSUS de gc.upper sur la
            #   dernière bougie clôturée (close au-dessus ET close précédent au
            #   niveau ou en dessous). »
            for sym in symbols:
                if len(held) >= max_pos:
                    break
                if sym in held or sym in exited_this_run:
                    continue
                c, cp = col[sym]["close"][i], col[sym]["close"][i - 1]
                u, up = col[sym]["upper"][i], col[sym]["upper"][i - 1]
                if not all(np.isfinite(v) for v in (c, cp, u, up)):
                    continue                      # « si la donnée manque, ignorer »
                if not (c > u and cp <= up):
                    continue
                if sizing_mode == "uniform":
                    w = w_fresh
                else:
                    age = col[sym]["bo_age"][i]
                    w = w_fresh if (np.isfinite(age) and age <= max_age) else w_stale
                held[sym] = ("LONG", w, float(c))

            # ── Étape 7 : entrées courtes ───────────────────────────────────
            if enable_shorts:
                for sym in symbols:
                    if len(held) >= max_pos:
                        break
                    if sym in held or sym in exited_this_run:
                        continue
                    c, cp = col[sym]["close"][i], col[sym]["close"][i - 1]
                    f, fp = col[sym]["filter"][i], col[sym]["filter"][i - 1]
                    h, tr = col[sym]["high"][i], col[sym]["trend"][i]
                    if not all(np.isfinite(v) for v in (c, cp, f, fp, h, tr)):
                        continue
                    red = tr < 0
                    # a) HEDGE : trend rouge ET close croise le filtre à la baisse
                    if red and c < f and cp >= fp:
                        held[sym] = ("SHORT", w_hedge, float(c))
                        continue
                    # b) BEAR : BTC en downtrend, trend rouge, le high a touché le
                    #    filtre et le close est repassé dessous (rebond rejeté)
                    if btc_down and red and h >= touch * f and c < f:
                        held[sym] = ("SHORT", w_bear, float(c))

            # ── DÉCALAGE COMPENSATOIRE — À RETIRER QUAND core/ SERA CORRIGÉ ──
            # `allocation_engine` applique le poids décidé au timestamp `t` à la
            # barre suivante, et lui attribue le rendement `open[t] -> open[t+1]`.
            # Ce rendement COMMENCE à l'ouverture du jour t, donc avant la
            # clôture où la décision est prise : le moteur crédite un mouvement
            # déjà survenu. Démonstration chiffrée et reproductible dans
            # `bug_allocation_engine.py` (décision au close du jour 2 créditée
            # de +100 % alors que l'exécution à l'ouverture du jour 3, au prix
            # déjà monté, ne permet que 0 %).
            #
            # L'enjeu n'est pas cosmétique ici : la stratégie entre le jour où
            # le close franchit la bande haute, c'est-à-dire un jour de forte
            # hausse. Sans correction, elle encaisse cette hausse gratuitement.
            #
            # `core/` étant interdit d'écriture, on compense côté stratégie en
            # horodatant la décision du jour `i` à `index[i+1]`. Le moteur pose
            # alors le poids sur la barre `i+2` et le premier rendement subi est
            # `open[i+1] -> open[i+2]` : exactement la convention que son propre
            # docstring annonce.
            #
            # ATTENTION : ce décalage devra être SUPPRIMÉ le jour où le moteur
            # sera corrigé, sinon il s'appliquerait deux fois.
            #
            # La borne est `i + 1 < n` et non `< len(index)` : sur le chemin
            # tronqué, `index` s'arrête à T, alors qu'il va jusqu'au bout sur le
            # chemin complet. Bornier sur `len(index)` produirait un nombre
            # d'allocations différent entre les deux et ferait échouer R1 — pour
            # un motif purement technique, ce qui masquerait de vraies fuites.
            if i + 1 < n:
                out.append(Allocation(
                    timestamp=index[i + 1],
                    weights=self._to_weights(held, weight_mode),
                    reason=f"décidé au close du {index[i].date()} ; {len(held)} lignes ; "
                           f"BTC {'baissier' if btc_down else 'non baissier'}",
                    meta={"decided_at": str(index[i]),
                          "n_long": sum(1 for v in held.values() if v[0] == "LONG"),
                          "n_short": sum(1 for v in held.values() if v[0] == "SHORT"),
                          "btc_downtrend": btc_down},
                ))
        return out

    @staticmethod
    def _to_weights(held: dict[str, tuple[str, float, float]],
                    weight_mode: str) -> dict[str, float]:
        """Traduit l'état du portefeuille en poids acceptables par le contrat.

        Les jambes short sont routées vers le symbole synthétique `SYM~S`, dont
        la série de prix a un rendement opposé à celui de `SYM`. Le contrat
        n'admettant que des poids positifs, c'est la seule façon d'exprimer une
        position courte sans mentir au moteur — et elle est explicite.
        """
        raw = {(sym if side == "LONG" else short_symbol(sym)): w
               for sym, (side, w, _) in held.items()}
        if not raw:
            return {}

        total = sum(raw.values())
        if weight_mode == "normalized":
            # Pleinement investi dès qu'une ligne est active : isole le timing
            # du canal de la largeur de l'univers.
            return {s: w / total for s, w in raw.items()}
        # Mode absolu : fidèle au prompt, mais le contrat plafonne la somme à 1.
        # Sur un univers large la somme brute peut dépasser 100 % de NAV ; le
        # prompt ne prévoit pas ce cas (il compte sur le solde du compte pour
        # l'arbitrer). On réduit alors au prorata, ce qui est le comportement le
        # plus proche : chacun garde sa part relative.
        if total > 1.0:
            return {s: w / total for s, w in raw.items()}
        return raw

    # ── Chemin live (R5) ────────────────────────────────────────────────────
    def on_bar(self, ctx: AllocationContext) -> Optional[Allocation]:
        """Décision live. Réutilise EXACTEMENT le chemin backtest.

        R5 exige que backtest et live produisent la même décision sur le même
        état de marché. Le moyen le plus sûr de le garantir n'est pas de réécrire
        la logique en miroir — c'est de n'en avoir qu'une. On recalcule donc
        `precompute` + `generate_allocations` sur l'historique reçu et on rend la
        dernière allocation. Coûteux, mais impossible à désynchroniser.
        """
        bars = {s: df for s, df in ctx.bars.items() if not is_short_symbol(s)}
        if not bars:
            return None
        n = len(next(iter(bars.values())))
        data = self.precompute(bars, self.params)
        allocs = self.generate_allocations(data, self.params, n)
        return allocs[-1] if allocs else None

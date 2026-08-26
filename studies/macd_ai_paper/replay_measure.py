"""
REJEU À L'AVEUGLE ACCÉLÉRÉ — la mesure
=======================================

    python -m studies.macd_ai_paper.replay_measure

Joint les jugements (replay/judgments/*.jsonl — produits par les sous-agents
juges, qui n'ont JAMAIS vu mapping.json) aux outcomes (mapping.json), et
mesure :

    - prendre-tout : R par candidat, tous candidats jugés
    - bras IA      : R des candidats PRIS, percentile contre N tirages
                     aléatoires de MÊME effectif dans le même pool (graine
                     figée) — la falsification F1-rejeu du protocole
    - resserrage   : outcome recalculé avec les sl/tp_adjust demandés
                     (bornes clampées) — l'apport du « management » IA
    - splits       : MT5 (exécutable, coûts réels) vs LONGHIST (structurel)

Ce script ne décide pas : il imprime les chiffres et laquelle des lignes du
protocole est atteinte. Effectif TOUJOURS en regard.
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np                                        # noqa: E402

from studies.macd_ai_paper.paper_step import (            # noqa: E402
    clamp_decision, default_data_dir, load_sealed_params,
)
from studies.macd_ai_paper.replay_common import (         # noqa: E402
    DATASETS, load_dataset, spec_for, walk_outcome,
)
from studies.macd_ai_paper.run_paper import (             # noqa: E402
    PARAMS_PATH, PARAMS_SHA256,
)

# Migration tbot : même résolution d'état que paper_step (C:\db\tradingBot\…).
REPLAY_DIR = os.path.join(default_data_dir(), "replay")


def percentile_vs_draws(rs: np.ndarray, took: np.ndarray,
                        draws: int, seed: int):
    k = int(took.sum())
    if k == 0 or k == len(rs):
        return None, None
    r_sel = float(rs[took].sum())
    rng = np.random.default_rng(seed)
    sums = np.array([rs[rng.choice(len(rs), size=k, replace=False)].sum()
                     for _ in range(draws)])
    pct = float(100.0 * (sums < r_sel).mean() + 50.0 * (sums == r_sel).mean())
    return pct, r_sel


def block(name: str, rs: np.ndarray, took: np.ndarray, draws, seed) -> None:
    n, k = len(rs), int(took.sum())
    if n == 0:
        print(f"{name:<26} aucun candidat")
        return
    all_mean = float(rs.mean())
    print(f"{name:<26} pool n={n:<4} R/candidat={all_mean:+.3f} "
          f"(prendre-tout {rs.sum():+.1f} R)")
    if k == 0:
        print(f"{'':<26} IA : 0 pris — sélection vide, percentile non défini")
        return
    sel_mean = float(rs[took].mean())
    pct, r_sel = percentile_vs_draws(rs, took, draws, seed)
    line = (f"{'':<26} IA : pris {k}/{n} ({100 * k / n:.0f} %) · "
            f"R/pris={sel_mean:+.3f} · somme {r_sel:+.1f} R")
    if pct is not None:
        line += f" · percentile vs {draws} tirages : {pct:.1f}"
    print(line)


def main() -> int:
    params = load_sealed_params(PARAMS_PATH, PARAMS_SHA256)
    draws = params["control"]["draws"]
    seed = params["control"]["seed"]
    bounds = params["ai"]["bounds"]
    rules = params["stop_rules"]["fail_ai"]

    with open(os.path.join(REPLAY_DIR, "mapping.json"), encoding="utf-8") as f:
        mapping = json.load(f)

    judgments = {}
    for path in sorted(glob.glob(os.path.join(REPLAY_DIR, "judgments",
                                              "*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "id" in j:
                    judgments[j["id"]] = clamp_decision(j, bounds)

    ids = [cid for cid in mapping if cid in judgments]
    missing = [cid for cid in mapping if cid not in judgments]
    if not ids:
        print("Aucun jugement — lancer les sous-agents juges d'abord "
              "(voir PROTOCOL.md § rejeu).")
        return 1

    rs = np.array([mapping[cid]["outcome"]["pnl_r"] for cid in ids])
    rs_nc = np.array([mapping[cid]["outcome"]["pnl_r_nocost"] for cid in ids])
    took = np.array([judgments[cid]["decision"] == "take"
                     and judgments[cid]["size"] > 0 for cid in ids])
    sizes = np.array([judgments[cid]["size"] for cid in ids])
    is_mt5 = np.array([DATASETS[mapping[cid]["dataset"]]["kind"] == "mt5"
                       for cid in ids])

    print("=" * 88)
    print("REJEU À L'AVEUGLE ACCÉLÉRÉ — juge gestionnaire de risque sur "
          "candidats s12 anonymisés")
    print("=" * 88)
    print(f"candidats jugés : {len(ids)}"
          + (f" ({len(missing)} sans jugement — exclus)" if missing else ""))
    print()

    block("TOUS (net, base)", rs, took, draws, seed)
    block("TOUS (sans coût)", rs_nc, took, draws, seed + 1)
    block("MT5 seul (net)", rs[is_mt5], took[is_mt5], draws, seed + 2)
    block("LONGHIST seul (net)", rs[~is_mt5], took[~is_mt5], draws, seed + 3)
    print()

    # ── sizing gradué : le R pondéré par la taille bat-il le R plein ? ─────
    k = int(took.sum())
    if k:
        w = sizes[took]
        r_t = rs[took]
        if w.std() > 0:
            print(f"Sizing gradué : taille moyenne des pris {w.mean():.2f} · "
                  f"corrélation taille/R {np.corrcoef(w, r_t)[0, 1]:+.3f} "
                  f"(n={k})")
        else:
            print(f"Sizing gradué : taille uniforme {w.mean():.2f} — pas de "
                  f"gradation à mesurer (n={k})")

    # ── resserrage SL/TP : recalcul des outcomes ajustés des pris ──────────
    adj_ids = [cid for cid in ids
               if judgments[cid]["decision"] == "take"
               and judgments[cid]["size"] > 0
               and (judgments[cid]["sl_adjust"] != 1.0
                    or judgments[cid]["tp_adjust"] != 1.0)]
    if adj_ids:
        cache = {}
        base_sum = adj_sum = 0.0
        n_ok = 0
        for cid in adj_ids:
            m = mapping[cid]
            ds = m["dataset"]
            if ds not in cache:
                cache[ds] = load_dataset(ds)
            out = walk_outcome(cache[ds], m["bar"], m["entry"], m["stop"],
                               m["target"], spec_for(ds, params),
                               sl_adjust=judgments[cid]["sl_adjust"],
                               tp_adjust=judgments[cid]["tp_adjust"])
            if out is None:
                continue
            n_ok += 1
            base_sum += m["outcome"]["pnl_r"]
            adj_sum += out["pnl_r"]
        if n_ok:
            print(f"Resserrage SL/TP : {n_ok} pris ajustés · base "
                  f"{base_sum:+.1f} R -> ajusté {adj_sum:+.1f} R "
                  f"(delta {adj_sum - base_sum:+.1f} R)")
    else:
        print("Resserrage SL/TP : aucun ajustement demandé par le juge")
    print()

    # ── verdict contre la falsification F1-rejeu ───────────────────────────
    print("-" * 88)
    pct, _ = percentile_vs_draws(rs, took, draws, seed)
    n = len(ids)
    if pct is None:
        print(f"F1-rejeu : percentile non défini (pris {int(took.sum())}/{n} "
              f"— sélection vide ou totale). Un juge qui prend tout ou rien "
              f"n'informe pas : NON CONCLUSIF.")
    elif n < rules["min_decisions"]:
        print(f"F1-rejeu : effectif {n} < {rules['min_decisions']} — "
              f"NON CONCLUSIF.")
    elif pct < rules["percentile_below"]:
        print(f"F1-rejeu DÉCLENCHÉE : percentile {pct:.1f} < "
              f"{rules['percentile_below']} (n={n}). La sélection IA "
              f"n'ajoute rien à l'aléatoire de même taux sur ce flux. "
              f"VERDICT : ne PAS armer le runner temps réel.")
    elif pct < 95:
        print(f"F1-rejeu NON déclenchée mais signal MINCE : percentile "
              f"{pct:.1f} dans [{rules['percentile_below']} ; 95[ (n={n}). "
              f"Le protocole exige >= 95 pour parler de signal — zone grise, "
              f"décision Adrian documentée requise avant tout armement.")
    else:
        print(f"F1-rejeu : percentile {pct:.1f} >= 95 (n={n}) — signal de "
              f"sélection. L'armement du runner temps réel (couche de "
              f"confirmation) peut être DISCUTÉ — décision Adrian.")
    print("-" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

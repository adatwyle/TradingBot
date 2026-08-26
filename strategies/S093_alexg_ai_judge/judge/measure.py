"""
Mesure du rejeu à l'aveugle — les chiffres de FALSIFICATION.md, rien d'autre.

Entrées : judge/mapping.json (outcomes, jamais montrés au juge) +
          judge/logs/batch_*_scores.json (verdicts du juge).

Grades (déterministes, calculés ICI depuis les listes de confluences du juge —
pas par le juge, pour éliminer les erreurs d'arithmétique LLM) :
    grade_core = 10 × |core|            (cap 100)  — grille SANS COT
    grade_cot  = 10 × |core| + 10 × |cot| (cap 100) — grille AVEC COT

Pour chaque variante × seuil (50/60/70) :
    - R/trade moyen des PRIS vs TOUS les candidats (jamais le PnL total)
    - bras témoin : 200 tirages aléatoires de MÊME effectif parmi les MÊMES
      candidats (permutation, graine 20260816) -> percentile
    - effectif, win rate, R:R planifié médian, fréquence/semaine

La règle des effectifs : tout sous-groupe < 30 trades est marqué [MINCE] et ne
peut fonder aucun verdict.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20260816
DRAWS = 200
THRESHOLDS = (50, 60, 70)
WEEKS = 1855 / 7.0
CORE_KEYS = {"trend_2tf", "trend_3tf", "aoi_quality", "aoi_both_tf",
             "retrace_healthy", "shift_clean", "engulfing",
             "hs_neckline_retest", "round_level", "ema_aligned"}
COT_KEYS = {"cot_aligned", "cot_extreme_favor"}


def load() -> tuple[dict, dict]:
    mapping = json.load(open(os.path.join(HERE, "mapping.json"), encoding="utf-8"))
    scores = {}
    for fn in sorted(glob.glob(os.path.join(HERE, "logs", "batch_*_scores.json"))):
        txt = open(fn, encoding="utf-8").read()
        # tolère un éventuel fence markdown autour du tableau
        txt = txt.strip()
        if txt.startswith("```"):
            txt = txt.split("```")[1]
            txt = txt[txt.find("["):]
        arr = json.loads(txt)
        for r in arr:
            core = [k for k in r.get("core", []) if k in CORE_KEYS]
            cot = [k for k in r.get("cot", []) if k in COT_KEYS]
            scores[r["id"]] = {
                "core": core, "cot": cot,
                "grade_core": min(100, 10 * len(core)),
                "grade_cot": min(100, 10 * len(core) + 10 * len(cot)),
                "reason": r.get("reason", ""),
            }
    return mapping, scores


def stats(rs: np.ndarray) -> dict:
    if len(rs) == 0:
        return {"n": 0}
    return {
        "n": int(len(rs)),
        "mean_r": round(float(np.mean(rs)), 4),
        "median_r": round(float(np.median(rs)), 4),
        "wr_pct": round(100.0 * float(np.mean(rs > 0)), 1),
        "total_r": round(float(np.sum(rs)), 2),
    }


def main() -> None:
    mapping, scores = load()
    ids = [i for i in mapping if i in scores]
    missing = [i for i in mapping if i not in scores]
    r_all = np.array([mapping[i]["outcome"]["pnl_r"] for i in ids])
    rr_all = np.array([mapping[i]["dossier"]["rr"] for i in ids])

    out = {"n_candidates": len(ids), "n_missing_scores": len(missing),
           "all": stats(r_all), "seed": SEED, "draws": DRAWS,
           "variants": {}}

    rng_master = np.random.default_rng(SEED)
    lines = ["=" * 78,
             "REJEU À L'AVEUGLE — juge IA (grille fxalexg) vs sélection aléatoire",
             "=" * 78,
             f"{len(ids)} candidats jugés ({len(missing)} sans score) — "
             f"graine {SEED}, {DRAWS} tirages/nul",
             f"TOUS les candidats : {stats(r_all)}", ""]

    for variant, key in (("sans_cot", "grade_core"), ("avec_cot", "grade_cot")):
        out["variants"][variant] = {}
        lines.append(f"--- Variante {variant} ---")
        lines.append(f"{'seuil':>6} {'n_pris':>7} {'R/trade':>9} {'WR%':>6} "
                     f"{'rr_med':>7} {'freq/sem':>9} {'nul_méd':>9} {'pctile':>7}")
        for th in THRESHOLDS:
            taken = [i for i in ids if scores[i][key] >= th]
            rs = np.array([mapping[i]["outcome"]["pnl_r"] for i in taken])
            n = len(taken)
            if n == 0:
                lines.append(f"{th:>5}% {0:>7}       —")
                out["variants"][variant][th] = {"n": 0}
                continue
            # permutation : même effectif, mêmes candidats, graine dérivée
            rng = np.random.default_rng(SEED + th + (0 if variant == "sans_cot" else 7))
            null_means = np.array([
                float(np.mean(rng.choice(r_all, size=n, replace=False)))
                for _ in range(DRAWS)])
            mean_taken = float(np.mean(rs))
            pct = 100.0 * (np.sum(null_means < mean_taken)
                           + 0.5 * np.sum(null_means == mean_taken)) / DRAWS
            rr_med = float(np.median([mapping[i]["dossier"]["rr"] for i in taken]))
            row = {
                **stats(rs),
                "rr_planned_median": round(rr_med, 2),
                "freq_per_week": round(n / WEEKS, 3),
                "null_median_mean_r": round(float(np.median(null_means)), 4),
                "null_p95_mean_r": round(float(np.percentile(null_means, 95)), 4),
                "percentile_vs_null": round(pct, 1),
                "thin": n < 30,
            }
            out["variants"][variant][th] = row
            flag = "  [MINCE]" if n < 30 else ""
            lines.append(f"{th:>5}% {n:>7} {mean_taken:>+9.3f} {row['wr_pct']:>6} "
                         f"{rr_med:>7.2f} {row['freq_per_week']:>9.3f} "
                         f"{row['null_median_mean_r']:>+9.3f} {pct:>6.1f}%{flag}")
        lines.append("")

    # Contribution marginale COT (F6) : même seuil, avec vs sans
    lines.append("--- Contribution marginale COT (F6) ---")
    for th in THRESHOLDS:
        a = out["variants"]["avec_cot"].get(th, {})
        b = out["variants"]["sans_cot"].get(th, {})
        if a.get("n") and b.get("n"):
            d = a["mean_r"] - b["mean_r"]
            lines.append(f"  seuil {th}% : avec {a['mean_r']:+.3f} R/t (n={a['n']}) "
                         f"vs sans {b['mean_r']:+.3f} R/t (n={b['n']}) "
                         f"-> delta {d:+.3f}")
    lines.append("")

    # distribution des grades
    for key in ("grade_core", "grade_cot"):
        vals = sorted(set(scores[i][key] for i in ids))
        dist = {v: sum(1 for i in ids if scores[i][key] == v) for v in vals}
        lines.append(f"distribution {key} : {dist}")

    txt = "\n".join(lines)
    print(txt)
    with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(HERE, "..", "research", "judge_results.txt"), "w",
              encoding="utf-8") as f:
        f.write(txt + "\n")


if __name__ == "__main__":
    main()

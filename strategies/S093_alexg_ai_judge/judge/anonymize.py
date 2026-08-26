"""
Harnais d'anonymisation — le juge ne doit PAS pouvoir se souvenir de
l'histoire. C'est la fuite que R1 ne peut pas voir : un LLM connaît les
grands mouvements de 2021-2026 ; ticker + date + prix bruts suffiraient à
retrouver « ce qui s'est passé ensuite ».

Retiré / transformé avant envoi au juge :
    - ticker            -> supprimé (id opaque cand_NNN, ordre MÉLANGÉ, graine fixe)
    - dates/heures      -> supprimées ; il ne reste que la session (london/ny/asia)
                           et le jour relatif RIEN (pas de jour de semaine)
    - prix bruts        -> extrait de 48 barres H1 exprimé en (prix - entrée)/ATR,
                           arrondi 0,01 ; stop et target dans la même unité
    - COT               -> percentiles « sur 3 ans » et âge du rapport en jours
    - outcome           -> JAMAIS dans les fichiers du juge

La table de correspondance (id -> symbole, date, outcome) vit dans
judge/mapping.json, JAMAIS transmise au juge.

Sorties : judge/batches/batch_NN.json + judge/mapping.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from core.data.source import load_bars                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20260816
EXCERPT = 48
BATCH = 24


def _atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean().to_numpy()


def main() -> None:
    cands = [json.loads(x) for x in open(os.path.join(HERE, "candidates.jsonl"), encoding="utf-8")]

    bars_cache, atr_cache = {}, {}
    for c in cands:
        s = c["symbol"]
        if s not in bars_cache:
            bars_cache[s] = load_bars(s, "H1", days=1855, max_age_hours=10**9)
            atr_cache[s] = _atr(bars_cache[s])

    rng = np.random.default_rng(SEED)
    order = rng.permutation(len(cands))

    batches_dir = os.path.join(HERE, "batches")
    os.makedirs(batches_dir, exist_ok=True)
    mapping = {}
    judge_recs = []

    for rank, k in enumerate(order):
        c = cands[int(k)]
        cid = f"cand_{rank + 1:03d}"
        df = bars_cache[c["symbol"]]
        i = c["bar"]
        a = float(atr_cache[c["symbol"]][i])
        sl_ = df.iloc[i - EXCERPT + 1: i + 1]
        entry = c["entry"]

        def norm(x):
            return round((float(x) - entry) / a, 2)

        excerpt = {
            "o": [norm(v) for v in sl_["open"]],
            "h": [norm(v) for v in sl_["high"]],
            "l": [norm(v) for v in sl_["low"]],
            "c": [norm(v) for v in sl_["close"]],
        }

        d = dict(c["dossier"])
        cot = c.get("cot") or {}
        rec = {
            "id": cid,
            "side": d.pop("side"),
            "dossier": d,
            "cot": {
                "aligned_with_trade": cot.get("cot_aligned"),
                "pct3y_base": cot.get("cot_pct_base"),
                "pct3y_quote": cot.get("cot_pct_quote"),
                "extreme": cot.get("cot_extreme"),
                "report_age_days": cot.get("cot_report_age_days"),
            } if cot else None,
            "stop_atr": round((c["stop"] - entry) / a, 2),
            "target_atr": round((c["target"] - entry) / a, 2),
            "bars_atr_units": excerpt,   # 48 H1, (prix - entrée)/ATR ; entrée = close de la dernière
        }
        judge_recs.append(rec)
        mapping[cid] = {
            "symbol": c["symbol"], "time": c["time"], "bar": i,
            "outcome": c["outcome"],
            "cot": cot, "dossier": c["dossier"],
        }

    nb = 0
    for start in range(0, len(judge_recs), BATCH):
        nb += 1
        with open(os.path.join(batches_dir, f"batch_{nb:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(judge_recs[start:start + BATCH], f)

    with open(os.path.join(HERE, "mapping.json"), "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=1)

    print(f"[OK] {len(judge_recs)} candidats anonymisés -> {nb} batches de max {BATCH}")
    print(f"     graine {SEED}, extrait {EXCERPT} barres, mapping séparé (jamais montré au juge)")


if __name__ == "__main__":
    main()

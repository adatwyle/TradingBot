"""
REJEU À L'AVEUGLE ACCÉLÉRÉ — extraction + anonymisation des candidats
======================================================================

    python -m studies.macd_ai_paper.replay_extract

Reprend le motif de `strategies/s93_alexg_ai_judge/judge/anonymize.py` : le
juge ne doit PAS pouvoir se souvenir de l'histoire (un LLM connaît les grands
mouvements — ticker + date + prix bruts suffiraient à retrouver « ce qui s'est
passé ensuite »).

Retiré / transformé avant envoi au juge :
    - dataset/ticker    -> supprimé (id opaque cand_NNN, ordre MÉLANGÉ, graine fixe)
    - dates             -> supprimées (pas même le jour de semaine)
    - prix bruts        -> extrait de 60 barres D1 en (prix - entrée)/ATR,
                           arrondi 0,01 ; stop et cible dans la même unité
    - outcome           -> JAMAIS dans les fichiers du juge

La table de correspondance (id -> dataset, date, outcome base) vit dans
`replay/mapping.json`, JAMAIS transmise au juge.

Sorties (données, jamais dans l'arborescence de code) :
    C:\\db\\tbot\\macd_ai_paper\\replay\\candidates.jsonl
    C:\\db\\tbot\\macd_ai_paper\\replay\\batches\\batch_NN.json
    C:\\db\\tbot\\macd_ai_paper\\replay\\mapping.json
"""
from __future__ import annotations

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
import pandas as pd                                       # noqa: E402

from studies.macd_ai_paper.paper_step import (            # noqa: E402
    default_data_dir, load_sealed_params,
)
from studies.macd_ai_paper.replay_common import (         # noqa: E402
    DATASETS, gen_candidates, load_dataset, spec_for, walk_outcome,
)
from studies.macd_ai_paper.run_paper import (             # noqa: E402
    PARAMS_PATH, PARAMS_SHA256,
)

# Migration tbot : même résolution d'état que paper_step (C:\db\tradingBot\…).
REPLAY_DIR = os.path.join(default_data_dir(), "replay")
SEED = 20260816
EXCERPT = 60          # barres D1 montrées au juge
BATCH = 25
MAX_CANDIDATES = 400  # au-delà : sous-échantillon déterministe (graine SEED)


def _atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean().to_numpy()


def main() -> int:
    params = load_sealed_params(PARAMS_PATH, PARAMS_SHA256)
    cell = params["cell"]

    all_cands = []
    for ds_name in DATASETS:
        df = load_dataset(ds_name)
        if df is None or len(df) < 100:
            print(f"[SKIP] {ds_name} : dataset indisponible", file=sys.stderr)
            continue
        spec = spec_for(ds_name, params)
        cands = gen_candidates(df, cell, ds_name)
        n_open = 0
        for c in cands:
            out = walk_outcome(df, c["bar"], c["entry"], c["stop"],
                               c["target"], spec)
            if out is None:
                n_open += 1
                continue
            c["dataset"] = ds_name
            c["outcome"] = out
            all_cands.append(c)
        print(f"[OK] {ds_name:<13} {len(cands):>4} signaux · "
              f"{len(cands) - n_open:>4} clos ({n_open} jamais clos, exclus)")

    if not all_cands:
        print("[FAIL] aucun candidat", file=sys.stderr)
        return 1

    rng = np.random.default_rng(SEED)
    if len(all_cands) > MAX_CANDIDATES:
        keep = rng.choice(len(all_cands), size=MAX_CANDIDATES, replace=False)
        all_cands = [all_cands[int(k)] for k in sorted(keep)]
        print(f"[SUB] sous-échantillon déterministe : {MAX_CANDIDATES} "
              f"candidats (graine {SEED})")

    # bars/ATR par dataset pour l'anonymisation
    bars_cache, atr_cache = {}, {}
    for ds_name in {c["dataset"] for c in all_cands}:
        bars_cache[ds_name] = load_dataset(ds_name)
        atr_cache[ds_name] = _atr(bars_cache[ds_name])

    order = rng.permutation(len(all_cands))
    os.makedirs(os.path.join(REPLAY_DIR, "batches"), exist_ok=True)
    os.makedirs(os.path.join(REPLAY_DIR, "judgments"), exist_ok=True)

    mapping = {}
    judge_recs = []
    for rank, k in enumerate(order):
        c = all_cands[int(k)]
        cid = f"cand_{rank + 1:03d}"
        df = bars_cache[c["dataset"]]
        i = c["bar"]
        a = float(atr_cache[c["dataset"]][i])
        if not np.isfinite(a) or a <= 0:
            continue
        sl_ = df.iloc[max(0, i - EXCERPT + 1): i + 1]
        entry = c["entry"]

        def norm(x):
            return round((float(x) - entry) / a, 2)

        rec = {
            "id": cid,
            "strategy_rules": ("LONG only, indice actions D1, mean "
                               "reversion : MACD(12,26) < 0 et en baisse 5 "
                               "jours consécutifs ; close < close[veille] ; "
                               "close dans le bas du range 20 jours "
                               "(<= 20 %) ; sortie au dépassement du plus "
                               "haut de la veille (cible statique) ; "
                               "stop 3 ATR."),
            "side": "LONG",
            "stop_atr": round((c["stop"] - entry) / a, 2),
            "target_atr": (round((c["target"] - entry) / a, 2)
                           if c["target"] is not None else None),
            "reward_risk": (round(abs(c["target"] - entry)
                                  / abs(c["stop"] - entry), 3)
                            if c["target"] is not None else None),
            "range_pos": c["meta"].get("range_pos"),
            "macd_atr": (round(float(c["meta"]["macd"]) / a, 3)
                         if c["meta"].get("macd") is not None else None),
            "bars_atr_units": {
                "o": [norm(v) for v in sl_["open"]],
                "h": [norm(v) for v in sl_["high"]],
                "l": [norm(v) for v in sl_["low"]],
                "c": [norm(v) for v in sl_["close"]],
            },
        }
        judge_recs.append(rec)
        mapping[cid] = {"dataset": c["dataset"], "time": c["time"],
                        "bar": i, "entry": c["entry"], "stop": c["stop"],
                        "target": c["target"], "outcome": c["outcome"]}

    with open(os.path.join(REPLAY_DIR, "candidates.jsonl"), "w",
              encoding="utf-8") as f:
        for c in all_cands:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    nb = 0
    for start in range(0, len(judge_recs), BATCH):
        nb += 1
        with open(os.path.join(REPLAY_DIR, "batches", f"batch_{nb:02d}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(judge_recs[start:start + BATCH], f)

    with open(os.path.join(REPLAY_DIR, "mapping.json"), "w",
              encoding="utf-8") as f:
        json.dump(mapping, f, indent=1)

    print(f"[OK] {len(judge_recs)} candidats anonymisés -> {nb} batches de "
          f"max {BATCH} (graine {SEED}, extrait {EXCERPT} barres D1)")
    print(f"     mapping séparé (jamais montré au juge) : "
          f"{os.path.join(REPLAY_DIR, 'mapping.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

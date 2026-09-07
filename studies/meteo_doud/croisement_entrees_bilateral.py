"""
Croisement BILATERAL des entrées Doud contre nos barres XAUUSD, sur corpus purgé.

    python studies/meteo_doud/croisement_entrees_bilateral.py

CE QUE CE SCRIPT CORRIGE
------------------------
`croisement_entrees.py` (conservé, il documente ce qui a été fait) souffrait de deux
défauts de construction et travaillait sur un corpus non purgé :

1. **Test unilatéral.** Son `sweep_at` ne détectait qu'un balayage HAUSSIER — un
   plus-bas percé puis récupéré, c'est-à-dire une configuration d'ACHAT. Et son
   `forward` calculait `mfe = high - entry`, `mae = entry - low`, soit le P&L d'une
   position LONGUE. Un trade vendeur y était donc mesuré à l'envers, deux fois.
2. **Sens inconnu.** Le corpus ne portait pas le sens des positions.
3. **Corpus contaminé.** Doublons, et observations où elle commente une position
   DÉJÀ ouverte — l'horodatage datant alors la parole et non l'entrée.

Ce script teste les DEUX sens, oriente les excursions selon le sens, et travaille sur
`_entries_sens_2026-09-07.json` (corpus purgé par `REGLE_purge_2026-09-07.md`, sens
établi par lecture des transcriptions).

CE QU'IL MESURE
---------------
    ses entrées tombent-elles sur un balayage de liquidité COHÉRENT AVEC LEUR SENS,
    plus souvent qu'un instant quelconque de la même session ?

Pour une observation de sens connu, on ne teste que le balayage cohérent :
  - achat → balayage HAUSSIER (le plus-bas des LOOKBACK_REF barres est percé puis
    refermé au-dessus : les vendeurs sont sortis, le prix réintègre par le haut) ;
  - vente → balayage BAISSIER (le plus-haut est percé puis refermé en dessous).
Pour une observation de sens indéterminé, les deux sont rapportés et l'observation est
comptée séparément — elle n'entre pas dans le bras principal.

PARAMÈTRES — IDENTIQUES À LA MESURE D'ORIGINE, NON REJOUÉS
----------------------------------------------------------
    LOOKBACK_REF   60 barres M1
    WINDOW         30 barres M1
    WICK_MIN       0,50
    HORIZON        60 barres M1
    N_CONTROL      200 tirages
    SEED           20260906

Le bras témoin est construit exactement comme celui des observations : mêmes heures de
session, même graine, 200 tirages, et **un sens attribué à chaque tirage selon la même
distribution que le corpus purgé** — sans quoi on comparerait un test bilatéral à un
témoin unilatéral.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.data.source import load_bars  # noqa: E402

LOOKBACK_REF = 60
WINDOW = 30
WICK_MIN = 0.50
HORIZON = 60
N_CONTROL = 200
SEED = 20260906
PIP = 0.01
SENS_FILE = os.path.join(ROOT, "docs", "sources", "doudtrading",
                         "_entries_sens_2026-09-07.json")


# ── Détection du balayage, dans les deux sens ────────────────────────────────────
def sweep_at(bars: pd.DataFrame, i: int, sens: str) -> dict:
    """Un balayage COHÉRENT AVEC `sens` a-t-il eu lieu dans les WINDOW barres avant i ?

    `sens` == "achat" → balayage HAUSSIER : une barre j perce le plus-bas des
        LOOKBACK_REF barres qui la précèdent ET referme au-dessus (perçage rejeté par
        le haut). Mèche de rejet = mèche BASSE.
    `sens` == "vente" → balayage BAISSIER : une barre j perce le plus-haut des
        LOOKBACK_REF barres qui la précèdent ET referme en dessous. Mèche de rejet =
        mèche HAUTE.

    Symétrie stricte : les deux branches ont la même profondeur d'historique, la même
    fenêtre, le même seuil de mèche. Seul le côté du prix change.
    """
    if sens not in ("achat", "vente"):
        raise ValueError(f"sens attendu 'achat' ou 'vente', reçu {sens!r}")
    lo = bars["low"].to_numpy()
    hi = bars["high"].to_numpy()
    op = bars["open"].to_numpy()
    cl = bars["close"].to_numpy()
    start = i - WINDOW
    if start - LOOKBACK_REF < 0 or i >= len(bars):
        return {"sweep": None}

    for j in range(start, i + 1):
        rng = hi[j] - lo[j]
        if sens == "achat":
            ref = lo[j - LOOKBACK_REF:j].min()
            perce = lo[j] < ref and cl[j] > ref
            depth = ref - lo[j]
            wick = (min(op[j], cl[j]) - lo[j]) / rng if rng > 0 else 0.0
        else:
            ref = hi[j - LOOKBACK_REF:j].max()
            perce = hi[j] > ref and cl[j] < ref
            depth = hi[j] - ref
            wick = (hi[j] - max(op[j], cl[j])) / rng if rng > 0 else 0.0
        if perce:
            return {"sweep": True, "bars_before": i - j,
                    "depth_pips": round(float(depth) / PIP, 1),
                    "wick": round(float(wick), 2),
                    "rejet": bool(wick >= WICK_MIN)}
    return {"sweep": False}


def forward(bars: pd.DataFrame, i: int, entry: float, sens: str) -> dict:
    """MFE et MAE ORIENTÉS selon le sens de la position.

    achat : le marché lui donne quand il monte.  vente : quand il descend.
    """
    end = min(len(bars), i + 1 + HORIZON)
    win = bars.iloc[i + 1:end]
    if win.empty:
        return {}
    haut = float(win["high"].max())
    bas = float(win["low"].min())
    if sens == "achat":
        mfe, mae = haut - entry, entry - bas
    else:
        mfe, mae = entry - bas, haut - entry
    return {"mfe_pips": round(mfe / PIP, 0), "mae_pips": round(mae / PIP, 0)}


# ── Mesure ───────────────────────────────────────────────────────────────────────
def evalue(bars: pd.DataFrame, i: int, sens: str, entry: float | None) -> dict:
    """Évalue une observation. Sens indéterminé → les deux sens sont rapportés."""
    if sens == "indetermine":
        a, v = sweep_at(bars, i, "achat"), sweep_at(bars, i, "vente")
        if a["sweep"] is None or v["sweep"] is None:
            return {}
        return {"sens": "indetermine", "achat": a, "vente": v,
                "either": bool(a["sweep"] or v["sweep"])}
    s = sweep_at(bars, i, sens)
    if s["sweep"] is None:
        return {}
    out = {"sens": sens, "coherent": s, "either": bool(s["sweep"])}
    if entry is not None:
        out["fwd"] = forward(bars, i, entry, sens)
    return out


def p_unilaterale(hits: int, n: int, p0: float) -> float:
    """P(X >= hits) sous H0 : le taux observé est celui du témoin. Binomiale exacte."""
    if n == 0:
        return float("nan")
    return float(stats.binomtest(hits, n, p0, alternative="greater").pvalue)


def main() -> int:
    if not os.path.exists(SENS_FILE):
        print(f"corpus purgé introuvable : {SENS_FILE}")
        return 2
    doc = json.load(open(SENS_FILE, encoding="utf-8"))
    ents = doc["retenues"]
    bars = load_bars("XAUUSD", "M1", days=365 * 2)
    if bars is None:
        print("barres M1 indisponibles")
        return 2

    print(f"corpus purgé : {len(ents)} observations "
          f"({len(doc['purgees'])} purgées sur {len(ents) + len(doc['purgees'])})")
    print(f"règle de purge : {doc['_meta']['regle_de_purge']}")
    print(f"M1 {bars.index[0]} → {bars.index[-1]} ({len(bars)} barres)")
    print(f"balayage achat  = plus-bas des {LOOKBACK_REF} barres percé PUIS refermé "
          f"au-dessus")
    print(f"balayage vente  = plus-haut des {LOOKBACK_REF} barres percé PUIS refermé "
          f"en dessous")
    print(f"fenêtre {WINDOW} barres · rejet net si mèche ≥ {WICK_MIN:.0%}\n")

    idx = bars.index
    used = []
    print(f"{'live':13s} {'date/heure':17s} {'prix':>9s} {'sens':>12s} "
          f"{'balayage':>18s} {'il y a':>7s} {'profond':>8s} {'mèche':>6s} "
          f"{'MFE':>6s} {'MAE':>6s}")
    print("-" * 110)
    hors_fenetre: list[str] = []
    non_evaluables: list[str] = []
    for e in ents:
        i = int(idx.searchsorted(pd.Timestamp(e["dt"])))
        if i <= 0 or i >= len(bars):
            # `load_bars(days=730)` est ancrée sur l'instant présent : une
            # observation antérieure à la première barre disponible renvoie
            # i = 0. La perdre en silence ferait rétrécir l'effectif au fil
            # des jours sans que rien ne le signale — le corpus le plus ancien
            # s'évaporerait à mesure que la fenêtre glisse.
            hors_fenetre.append(f"{e['vid'][:12]} {e['dt'][:16]}")
            continue
        r = evalue(bars, i, e["sens"], float(e["prix"]))
        if not r:
            non_evaluables.append(f"{e['vid'][:12]} {e['dt'][:16]}")
            continue
        used.append((e, r))
        if e["sens"] == "indetermine":
            lib = (("haussier " if r["achat"]["sweep"] else "—        ") +
                   ("baissier" if r["vente"]["sweep"] else "—"))
            print(f"{e['vid'][:12]:13s} {e['dt'][:16]:17s} {e['prix']:9.2f} "
                  f"{'indetermine':>12s} {lib:>18s}")
        else:
            s = r["coherent"]
            f = r.get("fwd", {})
            print(f"{e['vid'][:12]:13s} {e['dt'][:16]:17s} {e['prix']:9.2f} "
                  f"{e['sens']:>12s} {('OUI' if s['sweep'] else 'non'):>18s} "
                  f"{(str(s.get('bars_before', '')) + ' b') if s['sweep'] else '':>7s} "
                  f"{(str(s.get('depth_pips', ''))) if s['sweep'] else '':>8s} "
                  f"{(str(s.get('wick', ''))) if s['sweep'] else '':>6s} "
                  f"{f.get('mfe_pips', ''):>6} {f.get('mae_pips', ''):>6}")

    if not used:
        print("aucune observation exploitable")
        return 0

    connus = [(e, r) for e, r in used if e["sens"] != "indetermine"]
    indets = [(e, r) for e, r in used if e["sens"] == "indetermine"]
    if hors_fenetre or non_evaluables:
        print()
        print("OBSERVATIONS ÉCARTÉES À LA MESURE — comptées, jamais silencieuses :")
        for lib in hors_fenetre:
            print(f"  hors fenêtre de données : {lib}")
        for lib in non_evaluables:
            print(f"  non évaluable           : {lib}")
        print(f"  total écarté : {len(hors_fenetre) + len(non_evaluables)} "
              f"sur {len(ents)} — effectif réellement mesuré : {len(used)}")
        if hors_fenetre:
            print("  ATTENTION : la fenêtre `load_bars(days=730)` glisse avec la date du")
            print("  jour. Un effectif qui rétrécit d'une exécution à l'autre vient de là,")
            print("  pas des données.")
        print()

    dist = Counter(e["sens"] for e, _ in used)

    # ── Témoin : mêmes heures, même graine, sens tiré selon la même distribution ──
    rng = np.random.default_rng(SEED)
    hours = sorted({pd.Timestamp(e["dt"]).hour for e, _ in used})
    pool = np.flatnonzero(np.isin(idx.hour, hours))
    pool = pool[(pool > LOOKBACK_REF + WINDOW + 1) & (pool < len(bars) - HORIZON - 1)]
    draws = rng.choice(pool, size=min(N_CONTROL, len(pool)), replace=False)

    labels = list(dist.keys())
    poids = np.array([dist[k] for k in labels], dtype=float)
    poids /= poids.sum()
    sens_tires = rng.choice(labels, size=len(draws), p=poids)

    t_connus_hits = t_connus_n = 0
    t_indet_hits = t_indet_n = 0
    t_either_hits = 0
    t_par_sens: dict[str, list[int]] = {"achat": [0, 0], "vente": [0, 0]}
    for j, s in zip(draws, sens_tires):
        r = evalue(bars, int(j), str(s), None)
        if not r:
            continue
        if s == "indetermine":
            t_indet_n += 1
            t_indet_hits += 1 if r["either"] else 0
        else:
            t_connus_n += 1
            t_connus_hits += 1 if r["coherent"]["sweep"] else 0
            t_par_sens[str(s)][1] += 1
            t_par_sens[str(s)][0] += 1 if r["coherent"]["sweep"] else 0
        t_either_hits += 1 if r["either"] else 0

    o_hits = sum(1 for _, r in connus if r["coherent"]["sweep"])
    o_n = len(connus)
    o_either = sum(1 for _, r in used if r["either"])

    print("\n" + "=" * 110)
    print(f"RÉPARTITION DES SENS · {dict(dist)} sur {len(used)} observations")
    print("=" * 110)

    print("\n--- BRAS PRINCIPAL : observations de sens CONNU, balayage cohérent ------")
    if o_n:
        p0 = t_connus_hits / t_connus_n if t_connus_n else float("nan")
        print(f"SES ENTRÉES      {o_hits}/{o_n} = {100 * o_hits / o_n:.0f} %")
        print(f"TÉMOIN           {t_connus_hits}/{t_connus_n} = {100 * p0:.0f} %"
              f"   (sens tiré selon la même distribution)")
        print(f"p unilatérale    {p_unilaterale(o_hits, o_n, p0):.3f}"
              f"   (binomiale exacte, H0 : taux observé = taux témoin)")
    else:
        print("aucune observation de sens connu")

    print("\n--- détail du témoin par sens ------------------------------------------")
    for s, (h, nn) in t_par_sens.items():
        if nn:
            print(f"  balayage {s:6s} {h:3d}/{nn:3d} = {100 * h / nn:.0f} %")

    print("\n--- BRAS SÉPARÉ : observations de sens INDÉTERMINÉ ----------------------")
    if indets:
        ha = sum(1 for _, r in indets if r["achat"]["sweep"])
        hv = sum(1 for _, r in indets if r["vente"]["sweep"])
        he = sum(1 for _, r in indets if r["either"])
        print(f"  n = {len(indets)} · balayage haussier {ha}/{len(indets)} · "
              f"baissier {hv}/{len(indets)} · l'un ou l'autre {he}/{len(indets)}")
        print(f"  témoin indéterminé (l'un ou l'autre) "
              f"{t_indet_hits}/{t_indet_n}")
        print("  Non fusionnées au bras principal : leur sens n'est pas établi, "
              "les compter\n  reviendrait à choisir le côté qui arrange.")
    else:
        print("  aucune")

    print("\n--- BRAS MIXTE : tout le corpus purgé, chaque observation à sa règle ----")
    print("  Sens connu → balayage cohérent seul. Sens indéterminé → l'un OU l'autre.")
    print("  Ce n'est donc PAS un test « un sens quelconque » : les indéterminées y ont")
    print("  deux chances de toucher, les autres une. Le témoin est construit pareil.")
    p0e = t_either_hits / len(draws)
    print(f"SES ENTRÉES      {o_either}/{len(used)} = {100 * o_either / len(used):.0f} %")
    print(f"TÉMOIN           {t_either_hits}/{len(draws)} = {100 * p0e:.0f} %")
    print(f"p unilatérale    {p_unilaterale(o_either, len(used), p0e):.3f}")

    print("\n--- ANCIENNE DÉFINITION rejouée sur le corpus purgé ---------------------")
    print("  Balayage HAUSSIER seul, quel que soit le sens réel — c'est exactement ce")
    print("  que mesurait croisement_entrees.py. À comparer au bras principal.")
    anc_o = anc_n = 0
    for e, _ in used:
        i = int(idx.searchsorted(pd.Timestamp(e["dt"])))
        s = sweep_at(bars, i, "achat")
        if s["sweep"] is None:
            continue
        anc_n += 1
        anc_o += 1 if s["sweep"] else 0
    anc_t = anc_tn = 0
    for j in draws:
        s = sweep_at(bars, int(j), "achat")
        if s["sweep"] is None:
            continue
        anc_tn += 1
        anc_t += 1 if s["sweep"] else 0
    p0a = anc_t / anc_tn if anc_tn else float("nan")
    print(f"SES ENTRÉES      {anc_o}/{anc_n} = {100 * anc_o / max(anc_n, 1):.0f} %")
    print(f"TÉMOIN           {anc_t}/{anc_tn} = {100 * p0a:.0f} %")
    print(f"p unilatérale    {p_unilaterale(anc_o, anc_n, p0a):.3f}")

    # ── Excursions, descriptives ─────────────────────────────────────────────────
    mfes = [r["fwd"]["mfe_pips"] for _, r in connus if r.get("fwd")]
    maes = [r["fwd"]["mae_pips"] for _, r in connus if r.get("fwd")]
    if mfes:
        print("\n--- excursions orientées selon le sens (descriptif, pas un verdict) --")
        print(f"  MFE médiane {np.median(mfes):.0f} pips · "
              f"MAE médiane {np.median(maes):.0f} pips · "
              f"rapport {np.median(mfes) / max(np.median(maes), 1e-9):.2f}")

    # ── Contrôle de sensibilité, explicitement POST-HOC ──────────────────────────
    if "--sens-indices" in sys.argv and indets:
        print("\n--- SENSIBILITÉ (post-hoc) : indéterminées rattachées à leur indice --")
        print("  Le champ `indice_non_retenu` du corpus penche `achat` pour les deux.")
        print("  Cet indice n'entre PAS dans les critères tranchants pré-enregistrés ;")
        print("  ce bras mesure seulement ce que le verdict deviendrait s'il y entrait.")
        forces = []
        for e, _ in used:
            s = e["sens"] if e["sens"] != "indetermine" else "achat"
            i = int(idx.searchsorted(pd.Timestamp(e["dt"])))
            r2 = evalue(bars, i, s, float(e["prix"]))
            if r2:
                forces.append((s, r2))
        d2 = Counter(s for s, _ in forces)
        rng2 = np.random.default_rng(SEED)
        lab2 = list(d2.keys())
        w2 = np.array([d2[k] for k in lab2], dtype=float)
        w2 /= w2.sum()
        st2 = rng2.choice(lab2, size=len(draws), p=w2)
        th = tn = 0
        for j, s in zip(draws, st2):
            r2 = evalue(bars, int(j), str(s), None)
            if not r2:
                continue
            tn += 1
            th += 1 if r2["coherent"]["sweep"] else 0
        oh2 = sum(1 for _, r2 in forces if r2["coherent"]["sweep"])
        p02 = th / tn if tn else float("nan")
        print(f"  répartition      {dict(d2)}")
        print(f"  SES ENTRÉES      {oh2}/{len(forces)} = "
              f"{100 * oh2 / len(forces):.0f} %")
        print(f"  TÉMOIN           {th}/{tn} = {100 * p02:.0f} %")
        print(f"  p unilatérale    {p_unilaterale(oh2, len(forces), p02):.3f}")

    print("\n" + "=" * 110)
    print(f"EFFECTIF : {o_n} observations de sens connu, "
          f"{len(indets)} indéterminées, {len(used)} au total.")
    if len(used) < 10:
        print("Sous le seuil de 10 fixé dans REGLE_purge_2026-09-07.md : "
              "aucune p-value n'est\nrevendiquée. Les taux ci-dessus sont "
              "DESCRIPTIFS. Verdict : EFFECTIF INSUFFISANT.")
    elif len(used) < 20:
        print("Entre 10 et 20 : le verdict CONFIRME est interdit par la règle "
              "(le résultat\nd'origine reposait déjà sur 20 observations).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

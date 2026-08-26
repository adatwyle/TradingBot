"""
ESSAI À BLANC fxalexg+IA — LE RAPPORT ET LES FALSIFICATIONS
============================================================

    python -m studies.alexg_paper.report_paper

Lit le journal scellé, vérifie son intégrité, puis confronte les chiffres aux
falsifications déclarées AVANT la première décision (PROTOCOL.md § 3). Ne
décide rien, n'écrit rien dans le journal : il RAPPORTE.

La mesure centrale (F1) est un test de permutation, repris de
`studies/macd_ai_paper/report_paper.py` : parmi les signaux que l'IA a
réellement DÉCIDÉS (pris ou passés) et dont le contrefactuel shadow est clos,
on compare la somme des R des k signaux qu'elle a pris à la distribution des
sommes de k signaux tirés au hasard dans le même vivier. Le percentile est la
seule lecture honnête d'une sélection : il neutralise la qualité intrinsèque
du flux et ne mesure QUE le tri.

Seuils scellés : ÉCHEC si percentile < 80 ; apport conclu seulement à >= 95.
Entre les deux : suggestif, non concluant. C'est exactement là que s93 s'est
arrêté (88,5) — la règle est écrite d'avance pour que 94 reste un échec.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from studies.alexg_paper.paper_step import (              # noqa: E402
    ARMS, JournalError, Paths, SealError, load_sealed_params, load_state,
    read_journal, verify_journal,
)
from studies.alexg_paper.run_paper import PARAMS_PATH     # noqa: E402


def selection_percentile(decided: list[tuple[str, bool]],
                         shadow_r: dict[str, float],
                         draws: int, seed: int) -> tuple:
    """(percentile, r_ia, n_decided_closed, n_taken_closed, distribution).

    `decided` : [(signal_id, taken)] pour chaque décision IA réelle.
    `shadow_r` : R contrefactuel net par signal_id (shadow clos uniquement).
    """
    pool = [(sid, took) for sid, took in decided if sid in shadow_r]
    if not pool:
        return None, 0.0, 0, 0, None
    rs = np.array([shadow_r[sid] for sid, _ in pool])
    took_mask = np.array([took for _, took in pool])
    k = int(took_mask.sum())
    r_ia = float(rs[took_mask].sum())
    if k == 0 or k == len(pool):
        return None, r_ia, len(pool), k, None    # sélection dégénérée
    rng = np.random.default_rng(seed)
    sums = np.array([rs[rng.choice(len(rs), size=k, replace=False)].sum()
                     for _ in range(draws)])
    pct = float(100.0 * (sums < r_ia).mean() + 50.0 * (sums == r_ia).mean())
    return pct, r_ia, len(pool), k, sums


def _spearman(x: list[float], y: list[float]) -> float:
    """Corrélation de rang, sans dépendance scipy."""
    if len(x) < 3:
        return float("nan")
    rx = np.argsort(np.argsort(np.asarray(x, dtype=float)))
    ry = np.argsort(np.argsort(np.asarray(y, dtype=float)))
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def main() -> int:
    try:
        params = load_sealed_params(PARAMS_PATH)
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3

    paths = Paths()
    state = load_state(paths.state)
    if state is None:
        print("Aucun état : l'essai n'a pas encore posé son scellé.")
        return 0
    try:
        verify_journal(paths.journal, state)
    except JournalError as e:
        print(f"[JOURNAL] {e}", file=sys.stderr)
        return 4

    rows = read_journal(paths.journal)
    rules = params["stop_rules"]

    # ── matière première ────────────────────────────────────────────────
    shadow_r, shadow_r_nocost = {}, {}
    for r in rows:
        if r["event"] == "SHADOW_CLOSE":
            shadow_r[r["signal_id"]] = float(r["pnl_r"])
            if r["pnl_r_nocost"]:
                shadow_r_nocost[r["signal_id"]] = float(r["pnl_r_nocost"])

    decided: list[tuple[str, bool]] = []
    sizes: dict[str, float] = {}
    for r in rows:
        if r["event"] == "DECISION" and r["arm"] == "AI" and r["decision"] != "na":
            took = r["decision"] == "take"
            decided.append((r["signal_id"], took))
            if took and r["size_frac"]:
                sizes[r["signal_id"]] = float(r["size_frac"])

    closes = defaultdict(list)
    for r in rows:
        if r["event"] == "CLOSE":
            closes[r["arm"]].append(float(r["pnl_r"]))

    print("=" * 78)
    print("ESSAI À BLANC fxalexg + JUGE IA — rapport")
    print("=" * 78)
    print(f"Départ : {state['started_at']} · journal : {len(rows)} lignes")
    print()
    print(f"{'bras':<7}{'clos':>6}{'R cumulé':>11}{'R/trade':>10}{'WR%':>8}"
          f"{'capital':>11}")
    for arm in ARMS:
        rs = closes.get(arm, [])
        st = state["arms"][arm]
        rpt = sum(rs) / len(rs) if rs else 0.0
        wr = 100 * sum(1 for x in rs if x > 0) / len(rs) if rs else 0.0
        print(f"{arm:<7}{len(rs):>6}{sum(rs):>+11.2f}{rpt:>+10.3f}{wr:>8.1f}"
              f"{st['capital']:>11.2f}")
    sh = state["shadow"]
    print(f"{'SHADOW':<7}{sh['n_closed']:>6}{sh['cum_r']:>+11.2f}"
          f"{(sh['cum_r'] / sh['n_closed'] if sh['n_closed'] else 0):>+10.3f}"
          f"{'':>8}{'—':>11}   (sans coût : {sh['cum_r_nocost']:+.2f})")
    print()

    verdicts: list[str] = []

    # ── F1 — la sélection bat-elle le hasard ? ──────────────────────────
    f1 = rules["fail_ai"]
    pct, r_ia, n_pool, k, sums = selection_percentile(
        decided, shadow_r, params["control"]["draws"],
        params["control"]["seed"])
    print("F1 — SÉLECTION IA vs TIRAGES ALÉATOIRES DE MÊME TAUX")
    if pct is None:
        print(f"    pas encore mesurable (vivier décidé+clos = {n_pool}, "
              f"pris = {k}) — une sélection tout-ou-rien n'est pas testable")
    else:
        print(f"    vivier {n_pool} · pris {k} · R des pris {r_ia:+.2f} · "
              f"percentile {pct:.1f} sur {len(sums)} tirages")
        if n_pool >= f1["min_decisions"]:
            if pct < f1["percentile_fail_below"]:
                verdicts.append(
                    f"F1 ATTEINTE — ÉCHEC : percentile {pct:.1f} < "
                    f"{f1['percentile_fail_below']} sur {n_pool} décisions. "
                    f"Le juge n'apporte rien.")
            elif pct >= f1["percentile_pass_at_or_above"]:
                verdicts.append(
                    f"F1 non atteinte — APPORT ÉTABLI : percentile {pct:.1f} "
                    f">= {f1['percentile_pass_at_or_above']} sur {n_pool} "
                    f"décisions.")
            else:
                verdicts.append(
                    f"F1 — SUGGESTIF, NON CONCLUANT : percentile {pct:.1f} "
                    f"entre {f1['percentile_fail_below']} et "
                    f"{f1['percentile_pass_at_or_above']}. Même zone que s93 "
                    f"(88,5). Ne pas promouvoir.")
        else:
            print(f"    (verdict inactif : {n_pool} < "
                  f"{f1['min_decisions']} décisions)")
    print()

    # ── F2 — le socle perd-il même sans coût ? ──────────────────────────
    f2 = rules["fail_base"]
    print("F2 — SOCLE MÉCANIQUE À COÛT NUL")
    print(f"    shadow clos {sh['n_closed']} · R cumulé sans coût "
          f"{sh['cum_r_nocost']:+.2f}")
    if sh["n_closed"] >= f2["min_signals"]:
        if sh["cum_r_nocost"] < f2["cum_r_nocost_below"]:
            verdicts.append(
                f"F2 ATTEINTE — le détecteur perd même sans aucun coût "
                f"({sh['cum_r_nocost']:+.2f} R sur {sh['n_closed']} signaux). "
                f"Seule la sélection peut sauver le dispositif.")
    else:
        print(f"    (verdict inactif : {sh['n_closed']} < "
              f"{f2['min_signals']} signaux)")
    print()

    # ── F3 — la taille demandée corrèle-t-elle au résultat ? ────────────
    print("F3 — TAILLE DEMANDÉE vs RÉSULTAT")
    pairs = [(sizes[sid], shadow_r[sid]) for sid in sizes if sid in shadow_r]
    if len(pairs) >= 3:
        rho = _spearman([p[0] for p in pairs], [p[1] for p in pairs])
        print(f"    n={len(pairs)} · corrélation de rang (taille, R) = {rho:+.3f}")
        if len(pairs) >= f1["min_decisions"] and not (rho > 0):
            verdicts.append(
                f"F3 ATTEINTE — la modulation de taille est du rituel "
                f"(rho={rho:+.3f} sur {len(pairs)}). À retirer en V2.")
    else:
        print(f"    (n={len(pairs)} — pas encore mesurable)")
    print()

    # ── F4 — le juge sélectionne-t-il, ou approuve-t-il en bloc ? ───────
    a = state["ai_stats"]
    print("F4 — TAUX DE PRISE")
    if a["n_decisions"]:
        rate = a["n_takes"] / a["n_decisions"]
        print(f"    {a['n_takes']}/{a['n_decisions']} = {100 * rate:.1f} % "
              f"(N/A : {a['n_na']})")
        if a["n_decisions"] >= f1["min_decisions"] and not (0.05 <= rate <= 0.95):
            verdicts.append(
                f"F4 ATTEINTE — taux de prise {100 * rate:.1f} % : le juge ne "
                f"sélectionne pas, il tranche en bloc. Prompt à revoir.")
    else:
        print("    aucune décision encore")
    print()

    # ── TEMPS ───────────────────────────────────────────────────────────
    t = rules["time"]
    from datetime import datetime, timezone
    started = datetime.strptime(state["started_at"], "%Y-%m-%dT%H:%M:%SZ")
    months = (datetime.now(timezone.utc).replace(tzinfo=None) - started).days / 30.44
    print(f"TEMPS — {months:.2f} mois écoulés · {a['n_decisions']} décisions "
          f"(seuil {t['min_decisions']} à {t['months']} mois)")
    if months >= t["months"] and a["n_decisions"] < t["min_decisions"]:
        verdicts.append(
            f"TEMPS ATTEINT — NON CONCLUSIF (données insuffisantes) : "
            f"{a['n_decisions']} décisions après {months:.1f} mois.")
    print()

    print("=" * 78)
    if verdicts:
        for v in verdicts:
            print(f"  ▸ {v}")
    else:
        print("  Aucune falsification atteinte à ce stade. L'essai continue.")
    print("=" * 78)
    print("Rappel PROTOCOL.md § 4 — la promotion en LIVE exige n>=40, "
          "percentile>=95, R/trade IA > 0 ET > MECH,")
    print("F4/F5 non atteintes, et la décision d'Adrian. Aucun de ces points "
          "n'est négociable après lecture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

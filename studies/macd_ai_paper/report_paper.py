"""
ESSAI À BLANC MACD+IA — LA LECTURE
===================================

    python -m studies.macd_ai_paper.report_paper

Affiche l'état de l'essai CONTRE les falsifications de PROTOCOL.md, et rien
d'autre. Ce script ne décide pas : il dit laquelle des falsifications, écrites
avant le premier signal, est déclenchée — ou qu'aucune ne l'est.

LE TÉMOIN F1 (sélection)
------------------------
Parmi les signaux sur lesquels l'IA a réellement DÉCIDÉ (take ou skip) et dont
le contrefactuel SHADOW est clos, on compare la somme des R shadow des signaux
PRIS par l'IA à la distribution de 1000 tirages aléatoires du même nombre de
signaux dans le même ensemble (graine figée). C'est la mesure de la SÉLECTION
seule, à taille et niveaux de base — le sizing et les resserrements SL/TP se
lisent, eux, dans les courbes de compte des trois bras (bras RND = témoin
vivant en monnaie).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

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
    ARMS, JournalError, Paths, SealError, load_sealed_params, load_state,
    read_journal, verify_journal,
)
from studies.macd_ai_paper.run_paper import (             # noqa: E402
    PARAMS_PATH, PARAMS_SHA256,
)


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
    pct = float(100.0 * (sums < r_ia).mean()
                + 50.0 * (sums == r_ia).mean())
    return pct, r_ia, len(pool), k, sums


def main() -> int:
    try:
        params = load_sealed_params(PARAMS_PATH, PARAMS_SHA256)
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3

    paths = Paths()
    state = load_state(paths.state)
    if state is None:
        print("Aucun état : l'essai n'a jamais tourné "
              "(python -m studies.macd_ai_paper.run_paper).")
        return 1
    try:
        verify_journal(paths.journal, state)
    except JournalError as e:
        print(f"[JOURNAL] {e}", file=sys.stderr)
        return 4

    journal = read_journal(paths.journal)
    rules = params["stop_rules"]
    started = datetime.strptime(state["started_at"], "%Y-%m-%dT%H:%M:%SZ")
    months = (datetime.now(timezone.utc).replace(tzinfo=None) - started).days / 30.44

    print("=" * 88)
    print("ESSAI À BLANC — Daily MACD assisté par IA (s12 / SP500+NASDAQ+DAX D1)")
    print("lecture contre PROTOCOL.md — le socle mécanique est mesuré PAS "
          "D'EDGE (s12 VERDICT)")
    print("=" * 88)
    print(f"scellé posé le {state['started_at']} · {months:.1f} mois écoulés")
    for sym, s in state["symbols"].items():
        print(f"    {sym:<7} dernière barre mesurée : {s['last_bar_time']}")
    print()

    # ── Les trois courbes de compte, côte à côte ───────────────────────────
    print(f"{'':<6}{'capital':>10}{'clos':>6}{'R cumulé':>10}{'WR %':>7}"
          f"{'ouverts':>9}")
    for arm in ARMS:
        st = state["arms"][arm]
        closes = [r for r in journal if r["event"] == "CLOSE"
                  and r["arm"] == arm]
        wins = sum(1 for r in closes if float(r["pnl_r"]) > 0)
        wr = f"{100 * wins / len(closes):.0f}" if closes else "—"
        n_open = sum(1 for slot in st["by_symbol"].values()
                     if slot["open_position"] is not None)
        print(f"{arm:<6}{st['capital']:>10.2f}{st['n_closed']:>6}"
              f"{st['cum_r']:>+10.2f}{wr:>7}{n_open:>9}")
    a = state["ai_stats"]
    rate = a["n_takes"] / a["n_decisions"] if a["n_decisions"] else None
    print(f"\nIA : {a['n_decisions']} décisions · {a['n_takes']} take "
          f"({100 * rate:.0f} %)" if rate is not None else
          f"\nIA : {a['n_decisions']} décisions")
    if a["n_na"]:
        print(f"     {a['n_na']} signaux N/A (panne CLI) — exclus des "
              f"décisions, témoins non affectés")
    sh = state["shadow"]
    print(f"SHADOW (contrefactuel, base) : {sh['n_closed']} clos · "
          f"R net {sh['cum_r']:+.2f} · R sans coût {sh['cum_r_nocost']:+.2f}")
    print()

    # ── F1 : sélection IA vs tirages aléatoires de même effectif ──────────
    decided = [(r["signal_id"], r["decision"] == "take")
               for r in journal
               if r["event"] == "DECISION" and r["arm"] == "AI"
               and r["decision"] in ("take", "skip")]
    shadow_r = {r["signal_id"]: float(r["pnl_r"])
                for r in journal if r["event"] == "SHADOW_CLOSE"}
    pct, r_ia, n_pool, k, sums = selection_percentile(
        decided, shadow_r, params["control"]["draws"],
        params["control"]["seed"])

    print("-" * 88)
    verdicts = []

    f1 = rules["fail_ai"]
    if pct is not None:
        print(f"F1 sélection : IA a pris {k}/{n_pool} signaux décidés+clos · "
              f"R des pris {r_ia:+.2f} · percentile vs {len(sums)} tirages "
              f"aléatoires de même effectif : {pct:.1f}")
        if n_pool >= f1["min_decisions"] and pct < f1["percentile_below"]:
            verdicts.append(
                f"F1 DÉCLENCHÉE : n = {n_pool} >= {f1['min_decisions']} et "
                f"percentile {pct:.1f} < {f1['percentile_below']} — la "
                f"sélection IA n'ajoute rien à l'aléatoire de même taux. "
                f"VERDICT : l'IA n'ajoute pas d'edge mesurable.")
    else:
        print(f"F1 sélection : non calculable (décisions closes : {n_pool}, "
              f"prises : {k} — sélection vide ou dégénérée)")

    f2 = rules["fail_base"]
    if (sh["n_closed"] >= f2["min_signals"]
            and sh["cum_r_nocost"] < f2["cum_r_nocost_below"]):
        verdicts.append(
            f"F2 DÉCLENCHÉE : {sh['n_closed']} signaux clos et R cumulé sans "
            f"coût {sh['cum_r_nocost']:+.2f} < "
            f"{f2['cum_r_nocost_below']} — le socle mécanique est mort sur "
            f"la fenêtre. ARRÊT (rien à sélectionner dans un flux mort).")

    f3 = rules["time"]
    if months >= f3["months"] and a["n_decisions"] < f3["min_decisions"]:
        verdicts.append(
            f"F3 (temps) : {months:.1f} mois écoulés et seulement "
            f"{a['n_decisions']} décisions < {f3['min_decisions']}. "
            f"NON CONCLUSIF — on ferme.")

    print()
    if verdicts:
        for v in verdicts:
            print(v)
    else:
        print("AUCUNE falsification déclenchée — continuer.")
        print(f"    F1 : armée à {f1['min_decisions']} décisions closes "
              f"(n = {n_pool})"
              + (f" ; percentile actuel {pct:.1f}" if pct is not None else ""))
        print(f"    F2 : armée à {f2['min_signals']} signaux shadow clos "
              f"(n = {sh['n_closed']}) ; R sans coût actuel "
              f"{sh['cum_r_nocost']:+.2f}")
        print(f"    F3 : {f3['months']} mois (écoulés {months:.1f})")
    print("-" * 88)
    print("Rappel invariance : toute modification des paramètres scellés "
          "invalide l'essai (redémarrage à zéro).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

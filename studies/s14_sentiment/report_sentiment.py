"""
ÉTUDE SCELLÉE s14 « SENTIMENT DES NEWS FOREX » — LA LECTURE
============================================================

    python -m studies.s14_sentiment.report_sentiment

Affiche l'état du corpus CONTRE les falsifications F1-F5 de PROTOCOL.md § 5,
et rien d'autre. Ce script ne décide pas : il dit laquelle des falsifications,
écrites avant la première news, est déclenchée — ou qu'aucune ne l'est. Il
n'écrit JAMAIS dans le journal (le worker est le seul écrivain, § 2.1).

« ON NE REGARDE PAS LA CASSEROLE » (§ 9)
-----------------------------------------
Tant que F1 n'est pas atteint pour un juge — N >= 150 verdicts comptables ET
>= 60 jours écoulés — **aucun hit-rate n'est calculé ni affiché pour lui**.
Seuls l'avancement (n/150, jours/60) et la distance à F1 sont montrés. Ce
n'est pas de la pudeur : une lecture précoce répétée fabrique des occasions de
conclure sur du bruit, et le protocole l'interdit avant l'effectif minimal.

LE VERDICT COMPTABLE — la définition du § 4, appliquée telle quelle
-------------------------------------------------------------------
Par cellule (juge, symbole, barre cible), le DERNIER verdict du juge avant
l'ouverture de la barre fait foi ; il n'est comptable que s'il est
DIRECTIONNEL (`positive`/`negative`) à confiance >= 0,8. Un `neutral` tardif
ANNULE donc un `positive` antérieur : la cellule n'est pas comptable.

Deux lectures tranchées ici, et documentées :

1. **Les lignes `na` ne participent pas à la réduction « dernier verdict ».**
   Le § 3 dit « les `na` n'entrent dans aucun effectif, aucune mesure », et le
   § 5/F4 parle du « dernier verdict non-`na` » : un `na` est une absence de
   mesure journalisée (panne du juge), pas une rétractation. Une panne
   survenue après un verdict directionnel ne doit donc pas effacer ce
   verdict — sinon la fiabilité du CLI deviendrait, en douce, un critère de
   sélection des cellules.

2. **N ne compte que les cellules RÉSOLUES** — celles dont la barre cible est
   close et dont le rendement est donc calculable. Une cellule comptable dont
   la barre n'a pas encore ouvert est en attente ; elle est affichée à part,
   jamais comptée dans l'effectif de F1, qui est « l'effectif de la mesure »
   (§ 4).

Le rendement de la barre cible vient de `core.data.source.load_bars` (D1,
heure serveur, timestamp NOMINAL — § 4) ; la dernière barre servie par MT5 est
EN FORMATION et n'est jamais utilisée.

CODES DE SORTIE
---------------
    0  lecture rendue (y compris « F1 pas encore atteint »)
    1  l'étude n'a jamais tourné (aucun état)
    2  barres MT5 indisponibles — rien n'est lu, rien n'est écrit
    3  scellé violé (hash de params.json)
    4  journal altéré (chaîne cassée, troncature)
"""
from __future__ import annotations

import math
import os
import sys
from datetime import date, datetime, timezone
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from studies.s14_sentiment.sentiment_step import (      # noqa: E402
    PARAMS_PATH, PARAMS_SHA256, JournalError, Paths, SealError,
    load_sealed_params, load_state, read_journal, target_bar_for,
    verify_journal,
)

ISO = "%Y-%m-%dT%H:%M:%SZ"
DIRECTIONAL = ("positive", "negative")


# ─────────────────────────────────────────────────────────────────────────────
# Statistique — IC de Wilson UNILATÉRAL (§ 5), kappa de Cohen 3 classes (F4)
# ─────────────────────────────────────────────────────────────────────────────

def wilson_one_sided(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """(borne basse, borne haute) de l'IC de Wilson UNILATÉRAL au niveau
    `level` — les deux bornes calculées au MÊME z unilatéral (z = 1,645 à
    95 %), chacune destinée à une lecture opposée : la basse pour toute
    revendication de valeur (> 0,52), la haute pour la fermeture F2 (< 0,52).

    Wilson et pas l'IC normal : à p proche de 0 ou 1 et n modeste, l'IC normal
    déborde des bornes de la proportion et ment sur la précision — c'est
    exactement le régime de cette étude à n = 150.
    """
    if n <= 0:
        return float("nan"), float("nan")
    # z unilatéral : quantile normal d'ordre `level` (1,6449 à 95 %).
    z = _z_one_sided(level)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def _z_one_sided(level: float) -> float:
    """Quantile normal standard d'ordre `level`. Table courte plutôt qu'une
    dépendance : le protocole ne connaît qu'un seul niveau (0,95)."""
    table = {0.90: 1.2815515655446004, 0.95: 1.6448536269514722,
             0.975: 1.959963984540054, 0.99: 2.3263478740408408}
    if level in table:
        return table[level]
    raise ValueError(f"niveau d'IC non tabulé : {level} — le scellé fixe 0.95")


def cohen_kappa(pairs: list[tuple[str, str]], labels: list[str]) -> float:
    """Kappa de Cohen sur 3 classes. NaN si indéfini (aucune paire, ou accord
    attendu = 1, cas d'une classe unique des deux côtés)."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    a = [x for x, _ in pairs]
    b = [y for _, y in pairs]
    po = sum(1 for x, y in pairs if x == y) / n
    pe = sum((a.count(lab) / n) * (b.count(lab) / n) for lab in labels)
    if abs(1 - pe) < 1e-12:
        return float("nan")
    return (po - pe) / (1 - pe)


# ─────────────────────────────────────────────────────────────────────────────
# Reconstruction des cellules depuis le journal
# ─────────────────────────────────────────────────────────────────────────────

def read_cells(journal: list[dict]) -> dict:
    """{(juge, symbole, barre_cible): dernière ligne VERDICT non-`na`}.

    Le journal est append-only et chronologique : la DERNIÈRE ligne écrite
    pour une cellule est le dernier verdict du juge avant l'ouverture de la
    barre (par construction, `target_bar_for` rend la première barre ouvrant
    STRICTEMENT après le verdict — tout verdict d'une cellule précède donc
    l'ouverture de sa barre). Une simple réaffectation suffit.
    """
    cells: dict = {}
    for r in journal:
        if r.get("event") != "VERDICT":
            continue
        sentiment = (r.get("sentiment") or "").strip()
        if not sentiment or sentiment == "na":
            continue                       # une panne n'est pas un verdict
        try:
            target = target_bar_for(r["measured_at_utc"])
        except (KeyError, TypeError, ValueError, RuntimeError):
            continue                       # horodatage illisible : hors mesure
        cells[(r.get("judge", ""), r.get("symbol", ""), target)] = r
    return cells


def is_countable(row: dict, threshold: float) -> bool:
    """Directionnel ET confiance >= seuil (§ 4). Le `neutral` ne revendique
    aucune direction : exclu du hit-rate, sa part est documentée."""
    if (row.get("sentiment") or "") not in DIRECTIONAL:
        return False
    try:
        return float(row.get("confidence") or 0.0) >= threshold
    except (TypeError, ValueError):
        return False


def bar_return(bars: dict, symbol: str, target: date) -> Optional[float]:
    """`close/open - 1` de la barre cible, ou None si la barre n'est pas
    close (cellule en attente). Un rendement exactement nul est un ÉCHEC —
    convention conservatrice du § 4 — il est rendu tel quel (0.0)."""
    day = (bars.get(symbol) or {}).get(target)
    if day is None:
        return None
    open_, close = day
    if not open_:
        return None
    return close / open_ - 1.0


def is_success(sentiment: str, ret: float) -> bool:
    return (sentiment == "positive" and ret > 0) or \
           (sentiment == "negative" and ret < 0)


# ─────────────────────────────────────────────────────────────────────────────
# Les barres D1 — source des rendements
# ─────────────────────────────────────────────────────────────────────────────

def load_universe_bars(universe: list[str]) -> tuple[dict, str]:
    """{symbole: {jour nominal: (open, close)}} ou ({}, erreur).

    STRICT : un seul symbole indisponible fait échouer la lecture (exit 2).
    Lire un hit-rate sur quatre symboles sur cinq mesurerait un autre corpus
    que celui du protocole, sans que rien ne le signale au lecteur.
    """
    from core.data.source import load_bars
    bars: dict = {}
    for sym in universe:
        try:
            df = load_bars(sym, "D1", max_age_hours=24)
        except Exception as e:                   # noqa: BLE001
            return {}, f"{sym} : chargement MT5 en échec ({e!r})"
        if df is None or len(df) < 2:
            return {}, f"{sym} : barres D1 indisponibles (MT5 fermé ou hors ligne)"
        # La dernière barre servie par MT5 est EN FORMATION : son close
        # n'existe pas encore, l'utiliser mesurerait un rendement fantôme.
        df = df.iloc[:-1]
        bars[sym] = {ts.date(): (float(o), float(c))
                     for ts, o, c in zip(df.index, df["open"], df["close"])}
    return bars, ""


# ─────────────────────────────────────────────────────────────────────────────
# La lecture
# ─────────────────────────────────────────────────────────────────────────────

def _hit(rows: list[dict]) -> tuple[int, int, float]:
    k = sum(1 for r in rows if is_success(r["sentiment"], r["ret"]))
    n = len(rows)
    return k, n, (k / n if n else float("nan"))


def main(argv: Optional[list[str]] = None, *, bars_source=None,
         now: Optional[datetime] = None) -> int:
    bars_source = bars_source or load_universe_bars
    now = now or datetime.now(timezone.utc)

    try:
        params = load_sealed_params(PARAMS_PATH, PARAMS_SHA256)
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"[SEAL] params.json illisible : {e}", file=sys.stderr)
        return 3

    paths = Paths()
    state = load_state(paths.state)
    if state is None:
        print("Aucun état : l'étude n'a jamais tourné "
              "(python -m studies.s14_sentiment.run_sentiment).")
        return 1
    try:
        verify_journal(paths.journal, state)
    except JournalError as e:
        print(f"[JOURNAL] {e}", file=sys.stderr)
        return 4

    journal = read_journal(paths.journal)
    fals = params["falsification"]
    threshold = float(fals["confidence_threshold_high"])
    floor = float(fals["hitrate_floor"])
    halves_floor = float(fals["halves_floor"])
    n_min = int(fals["n_min_verdicts"])
    min_days = int(fals["min_days"])
    universe = list(params["universe"])
    judge_names = [params["judge"]["name"], params["witness"]["name"]]
    labels = list(params["sentiment_labels"])

    started = datetime.strptime(state["started_at"], ISO).replace(
        tzinfo=timezone.utc)
    days = (now - started).days
    months = days / 30.44

    cells = read_cells(journal)
    countable = {k: v for k, v in cells.items() if is_countable(v, threshold)}

    print("=" * 88)
    print("s14_sentiment — SENTIMENT DES NEWS FOREX — lecture contre "
          "PROTOCOL.md § 5 (F1-F5)")
    print("=" * 88)
    print(f"scellé posé le {state['started_at']} · {days} jours écoulés "
          f"({months:.1f} mois sur {params['stop']['max_months']} max)")
    print(f"corpus : {state['n_news_total']} news · journal {len(journal)} "
          f"lignes · seuil de confiance comptable {threshold}")
    for name in judge_names:
        js = state["judges"].get(name, {})
        n_cells = sum(1 for (j, _, _) in cells if j == name)
        n_cnt = sum(1 for (j, _, _) in countable if j == name)
        n_neutral = sum(1 for (j, _, _), v in cells.items()
                        if j == name and v["sentiment"] == "neutral")
        print(f"    {name:<12} {js.get('n_verdicts_total', 0)} lignes VERDICT "
              f"({js.get('n_na', 0)} na, {js.get('n_stale_news', 0)} news "
              f"périmées) · {n_cells} cellules · {n_neutral} neutres · "
              f"{n_cnt} comptables (barre close ou non)")
    print()

    # ── Rendements : la seule dépendance externe de la lecture ─────────────
    bars, err = bars_source(universe)
    if err:
        print(f"[DATA] {err}", file=sys.stderr)
        print("[DATA] aucune lecture de valeur sans les barres cibles — "
              "rien n'a été écrit, réessayer MT5 ouvert.", file=sys.stderr)
        return 2

    resolved: dict[str, list[dict]] = {n: [] for n in judge_names}
    pending: dict[str, int] = {n: 0 for n in judge_names}
    for (judge, symbol, target), row in countable.items():
        if judge not in resolved:
            resolved[judge] = []
            pending[judge] = 0
        ret = bar_return(bars, symbol, target)
        if ret is None:
            pending[judge] += 1
            continue
        resolved[judge].append({**row, "symbol": symbol, "target": target,
                                "ret": ret})
    for rows in resolved.values():
        rows.sort(key=lambda r: r["measured_at_utc"])

    # ── F1, par juge — la porte de toute lecture de valeur ─────────────────
    print("-" * 88)
    f1_ok = {}
    for name in judge_names:
        n = len(resolved.get(name, []))
        f1_ok[name] = (n >= n_min and days >= min_days)
        etat = "ATTEINT" if f1_ok[name] else "pas atteint"
        print(f"F1 {name:<12} {etat} — {n}/{n_min} verdicts comptables "
              f"résolus, {days}/{min_days} jours"
              + (f" · {pending[name]} en attente de barre"
                 if pending.get(name) else ""))
    if not any(f1_ok.values()):
        print("-" * 88)
        print("Aucune lecture de valeur : le corpus n'a pas encore le droit "
              "de parler (§ 5/F1, § 9). Aucun hit-rate n'est calculé — on ne "
              "regarde pas la casserole.")
        for name in judge_names:
            n = len(resolved.get(name, []))
            print(f"    {name:<12} reste {max(0, n_min - n)} verdicts "
                  f"comptables et {max(0, min_days - days)} jours")
        return 0
    print()

    # ── F2 et F5, par juge ────────────────────────────────────────────────
    verdicts: list[str] = []
    hit: dict[str, tuple[int, int, float]] = {}
    for name in judge_names:
        rows = resolved.get(name, [])
        if not f1_ok[name]:
            print(f"{name:<12} F1 pas atteint — aucune lecture de valeur "
                  f"pour ce juge.")
            continue
        k, n, hr = _hit(rows)
        lo, hi = wilson_one_sided(k, n, float(fals["ci_level"]))
        hit[name] = (k, n, hr)
        print(f"{name:<12} hit-rate {100*hr:.1f} % ({k}/{n}) · IC 95 % "
              f"unilatéral Wilson [{100*lo:.1f} % ; {100*hi:.1f} %] · "
              f"plancher {100*floor:.0f} %")
        if hi < floor:
            verdicts.append(
                f"F2 DÉCLENCHÉE ({name}) : borne haute {100*hi:.1f} % < "
                f"{100*floor:.0f} % — PAS DE VALEUR, définitif pour ce juge "
                f"(§ 6).")
        # F5 — deux moitiés chronologiques, coupe à la médiane.
        mid = n // 2
        moities = [rows[:mid], rows[mid:]]
        hrs = [_hit(m)[2] for m in moities]
        print(f"             F5 moitiés : {100*hrs[0]:.1f} % "
              f"({len(moities[0])}) / {100*hrs[1]:.1f} % ({len(moities[1])}) "
              f"· plancher {100*halves_floor:.0f} %")
        if any(h <= halves_floor for h in hrs if h == h):
            verdicts.append(
                f"F5 DÉCLENCHÉE ({name}) : une moitié <= "
                f"{100*halves_floor:.0f} % — NON CONCLUSIF pour ce juge, "
                f"une valeur qui ne tient que sur une moitié est un artefact "
                f"de régime.")
        elif lo > floor:
            verdicts.append(
                f"VALEUR CANDIDATE possible ({name}) : borne basse "
                f"{100*lo:.1f} % > {100*floor:.0f} % et F5 tient"
                + (" — reste F3 (delta témoin) ci-dessous."
                   if name == params["judge"]["name"] else "."))
    print()

    # ── F3 — témoin, sur les cellules APPARIÉES (§ 5/F3) ──────────────────
    claude, finbert = params["judge"]["name"], params["witness"]["name"]
    print("-" * 88)
    if not (f1_ok.get(claude) and f1_ok.get(finbert)):
        print("F3 non évaluable : F1 doit être atteint par LES DEUX juges "
              "(§ 5/F3). Si le témoin n'atteint jamais F1, F3 reste non "
              "évaluable et c'est documenté.")
    else:
        idx = {name: {(r["symbol"], r["target"]): r for r in resolved[name]}
               for name in (claude, finbert)}
        commun = set(idx[claude]) & set(idx[finbert])
        if not commun:
            print("F3 non évaluable : aucune cellule (symbole, barre cible) "
                  "où les DEUX juges ont un verdict comptable résolu.")
        else:
            kc, nc, hc = _hit([idx[claude][c] for c in commun])
            kf, nf, hf = _hit([idx[finbert][c] for c in commun])
            delta = hc - hf
            print(f"F3 corpus commun apparié par cellule : {len(commun)} "
                  f"cellules · {claude} {100*hc:.1f} % ({kc}/{nc}) vs "
                  f"{finbert} {100*hf:.1f} % ({kf}/{nf}) · delta "
                  f"{100*delta:+.1f} pts")
            if delta <= float(fals["witness_delta_floor"]):
                verdicts.append(
                    f"F3 DÉCLENCHÉE : delta {100*delta:+.1f} pts <= 0 — les "
                    f"tokens ne sont pas justifiés, l'étude continue en "
                    f"{finbert} seul (§ 0, corollaire assumé).")

    # ── F4 — concordance, INFORMATIF (jamais éliminatoire) ────────────────
    idx_all = {}
    for name in (claude, finbert):
        idx_all[name] = {(s, t): v for (j, s, t), v in cells.items()
                         if j == name}
    commun4 = set(idx_all[claude]) & set(idx_all[finbert])
    if commun4:
        pairs = [(idx_all[claude][c]["sentiment"], idx_all[finbert][c]["sentiment"])
                 for c in commun4]
        kappa = cohen_kappa(pairs, labels)
        accord = sum(1 for a, b in pairs if a == b) / len(pairs)
        print(f"F4 concordance (informatif) : kappa de Cohen "
              f"{kappa:.3f} sur {len(pairs)} cellules appariées "
              f"(dernier verdict non-na, toutes confiances) · accord brut "
              f"{100*accord:.1f} %")
    else:
        print("F4 : aucune cellule appariée (dernier verdict non-na des deux "
              "juges) — concordance non calculable.")

    # ── Verdicts ───────────────────────────────────────────────────────────
    print("-" * 88)
    if verdicts:
        for v in verdicts:
            print(v)
    else:
        print("AUCUNE falsification déclenchée et aucune valeur dégagée — "
              "la question reste ouverte jusqu'à la lecture finale (§ 6, "
              "NON CONCLUSIF par défaut).")
    for name in judge_names:
        if name in hit:
            k, n, hr = hit[name]
            lo, _ = wilson_one_sided(k, n, float(fals["ci_level"]))
            if lo <= floor:
                print(f"    {name:<12} borne basse {100*lo:.1f} % <= "
                      f"{100*floor:.0f} % : aucune revendication de valeur "
                      f"possible (§ 5, exigence supplémentaire).")
    print("-" * 88)
    print("Rappel § 6 : quel que soit le verdict, AUCUNE promotion trading "
          "directe — une VALEUR CANDIDATE n'autorise qu'une proposition "
          "d'étude de FILTRE, décision Adrian (R10).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

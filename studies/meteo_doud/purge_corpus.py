"""
Application mécanique de REGLE_purge_2026-09-07.md au corpus d'entrées Doud.

    python studies/meteo_doud/purge_corpus.py

Ce script n'a aucune latitude : il implémente la règle, clause par clause, dans
l'ordre P1 → P2 → P3 → P4 → P5. Il produit la liste des survivantes et, pour chaque
observation purgée, le motif du PREMIER critère qui l'élimine.

Il n'établit PAS le sens des observations : le sens se lit dans les transcriptions
(cf. `_entries_sens_2026-09-07.json`), il n'est pas déductible par motif textuel.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.data.source import load_bars  # noqa: E402

ALIGNED = os.path.join(ROOT, "docs", "sources", "doudtrading", "_entries_aligned.json")

# Paramètres du test, repris tels quels de croisement_entrees.py — ils fondent P4 et P5b.
LOOKBACK_REF = 60
WINDOW = 30
HORIZON = 60
INDEP_MINUTES = LOOKBACK_REF + WINDOW  # 90 — fenêtre d'information de sweep_at

ERR_MAX = 0.30
PRIX_MIN = 1000.0

MOTIFS_HORS_TRADE = (
    "je suis pas dedans",
    "je ne suis pas dedans",
    "j'suis pas dedans",
    "imaginons",
    "c'est pour vous expliquer",
    "par exemple je rentre",
)

MOTIFS_RETROSPECTIF = (
    # (a) position antérieure à la parole
    "deja dedans",
    "j'y suis",
    "je suis deja",
    # (b) position clôturée ou réduite
    "j'ai cloture",
    "viens de cloturer",
    "je cloture",
    "j'ai coupe",
    "je suis sortie",
    "j'ai renforce",
    # (c) résultat courant cité
    "actuellement",
    "qui tournent",
)


def norm(txt: str) -> str:
    """Minuscules, accents supprimés, apostrophes typographiques unifiées."""
    txt = (txt or "").replace("’", "'").lower()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    return " ".join(txt.split())


def hits(ctx: str, motifs: tuple[str, ...]) -> list[str]:
    n = norm(ctx)
    return [m for m in motifs if m in n]


def purge(entries: list[dict], bars: pd.DataFrame) -> list[dict]:
    """Annote chaque observation d'un `motif_purge` (None si retenue)."""
    out = []
    for e in entries:
        rec = dict(e)
        rec["motif_purge"] = None
        rec["motifs_declencheurs"] = []

        # ── P1 prix non exploitable ──────────────────────────────────────────
        if not e.get("aligne"):
            rec["motif_purge"] = "prix-non-aligne"
        elif float(e.get("err_pct", 99)) > ERR_MAX:
            rec["motif_purge"] = "ecart-prix-excessif"
        elif float(e.get("prix", 0)) < PRIX_MIN:
            rec["motif_purge"] = "prix-tronque"

        # ── P2 hors trade ────────────────────────────────────────────────────
        if rec["motif_purge"] is None:
            h = hits(e.get("ctx", ""), MOTIFS_HORS_TRADE)
            if h:
                rec["motif_purge"] = "hors-trade"
                rec["motifs_declencheurs"] = h

        # ── P3 récit rétrospectif ────────────────────────────────────────────
        if rec["motif_purge"] is None:
            h = hits(e.get("ctx", ""), MOTIFS_RETROSPECTIF)
            if h:
                rec["motif_purge"] = "recit-retrospectif"
                rec["motifs_declencheurs"] = h

        # ── P4 fenêtre de mesure incomplète ──────────────────────────────────
        if rec["motif_purge"] is None:
            i = int(bars.index.searchsorted(pd.Timestamp(e["dt"])))
            rec["bar_index"] = i
            if i - (LOOKBACK_REF + WINDOW) < 0 or i + HORIZON >= len(bars) or i <= 0:
                rec["motif_purge"] = "fenetre-incomplete"
        out.append(rec)

    # ── P5 doublons et non-indépendance, en dernier, sur les survivantes ─────
    survivants = [r for r in out if r["motif_purge"] is None]
    survivants.sort(key=lambda r: (r["vid"], r["offset_s"]))
    gardes: list[dict] = []
    for r in survivants:
        conflit = None
        for g in gardes:
            if g["vid"] != r["vid"]:
                continue
            if abs(float(g["prix"]) - float(r["prix"])) < 0.005:
                conflit = ("doublon-exact", g)
                break
            dt_g = pd.Timestamp(g["dt"])
            dt_r = pd.Timestamp(r["dt"])
            if abs((dt_r - dt_g).total_seconds()) < INDEP_MINUTES * 60:
                conflit = ("non-independant", g)
                break
        if conflit is None:
            gardes.append(r)
        else:
            r["motif_purge"] = conflit[0]
            r["purge_au_profit_de"] = f"{conflit[1]['vid']}@{conflit[1]['offset_s']}"
    return out


def ctx_large(vid: str, offset_s: int, marge: int) -> str:
    """Transcription complète autour du timecode, ± `marge` secondes.

    Sert UNIQUEMENT au contrôle de sensibilité `--fenetre-large` : la règle
    pré-enregistrée s'applique au champ `ctx` du corpus, pas à cette fenêtre.
    """
    path = os.path.join(ROOT, "docs", "sources", "doudtrading", "lives", vid + ".txt")
    if not os.path.exists(path):
        return ""
    out = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"\[(\d+):(\d+)\]\s?(.*)", ln)
        if not m:
            continue
        t = int(m.group(1)) * 60 + int(m.group(2))
        if offset_s - marge <= t <= offset_s + marge:
            out.append(m.group(3))
    return " ".join(out)


def main() -> int:
    entries = json.load(open(ALIGNED, encoding="utf-8"))
    bars = load_bars("XAUUSD", "M1", days=365 * 2)
    if bars is None:
        print("barres M1 indisponibles")
        return 2

    annot = purge(entries, bars)
    retenues = [r for r in annot if r["motif_purge"] is None]

    print(f"corpus initial : {len(entries)} observations, "
          f"{len({e['vid'] for e in entries})} vidéos")
    print(f"dont marquées `aligne` : {sum(1 for e in entries if e.get('aligne'))}\n")

    print(f"{'vid':13s} {'date/heure':17s} {'prix':>9s}  motif de purge")
    print("-" * 78)
    for r in sorted(annot, key=lambda r: r["dt"]):
        motif = r["motif_purge"] or "RETENUE"
        extra = ""
        if r["motifs_declencheurs"]:
            extra = "  <- " + " / ".join(f'"{m}"' for m in r["motifs_declencheurs"])
        if r.get("purge_au_profit_de"):
            extra = "  <- au profit de " + r["purge_au_profit_de"]
        print(f"{r['vid'][:12]:13s} {r['dt'][:16]:17s} {r['prix']:9.2f}  "
              f"{motif}{extra}")

    print("-" * 78)
    compte: dict[str, int] = {}
    for r in annot:
        k = r["motif_purge"] or "RETENUE"
        compte[k] = compte.get(k, 0) + 1
    for k, v in sorted(compte.items(), key=lambda kv: -kv[1]):
        print(f"{v:3d}  {k}")
    print(f"\nEFFECTIF APRÈS PURGE : {len(retenues)} observations, "
          f"{len({r['vid'] for r in retenues})} vidéos")

    if "--fenetre-large" in sys.argv:
        marge = 150
        print()
        print("=" * 78)
        print("CONTRÔLE DE SENSIBILITÉ (post-hoc, HORS règle pré-enregistrée)")
        print(f"Mêmes marqueurs P2/P3, appliqués non plus au champ `ctx` (~250 car.)")
        print(f"mais à la transcription complète ± {marge} s autour du timecode.")
        print("=" * 78)
        survit = 0
        for r in retenues:
            large = ctx_large(r["vid"], int(r["offset_s"]), marge)
            h = hits(large, MOTIFS_HORS_TRADE) + hits(large, MOTIFS_RETROSPECTIF)
            if h:
                print(f"  {r['vid'][:12]:13s} {r['dt'][:16]:17s} tomberait  <- "
                      + " / ".join(f'"{m}"' for m in h))
            else:
                survit += 1
                print(f"  {r['vid'][:12]:13s} {r['dt'][:16]:17s} survit")
        print()
        print(f"EFFECTIF sous la fenêtre large : {survit}  "
              f"(contre {len(retenues)} sous la règle pré-enregistrée)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

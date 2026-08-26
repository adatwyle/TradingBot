"""
SERVEUR DE SUPERVISION — lecture seule
=======================================

Sert le tableau de bord avec l'état RÉEL du dépôt, sans toucher au fichier UI.

Principe : `server/ui/dashboard.html` embarque ses données dans deux constantes
JavaScript (`STRATS`, `LEDGER`) écrites à la main lors du prototypage — donc
figées et périmées. Plutôt que de réécrire l'interface, ce serveur remplace ces
deux constantes AU MOMENT DE SERVIR par des données reconstruites depuis :

  - `strategies/*/manifest.yaml` + `research/VERDICT.md`  (état des stratégies,
    à la RACINE PROJET — le code vit dans app/, les stratégies à côté)
  - `C:\\db\\tradingBot\\gold_forward\\`                    (forward-test scellé)
  - `studies/*/VERDICT.md`                                 (études)

Lecture seule stricte : ce serveur n'écrit RIEN, ne lance RIEN, n'expose aucun
ordre. La supervision qui pourrait agir sur les positions viendra plus tard,
derrière la couche de risque — jamais dans un serveur de consultation.

Lancement : via .claude/launch.json (preview) ou `python app/server/app.py`.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import datetime

from flask import Flask, jsonify

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/
# `core` vit dans app/ ; script lancé en direct -> app/ importable d'abord.
sys.path.insert(0, APP_DIR)
from core.paths import db_dir, project_root  # noqa: E402

UI = os.path.join(APP_DIR, "server", "ui", "dashboard.html")
DB_DIR = str(db_dir())
GOLD_DIR = os.path.join(DB_DIR, "gold_forward")

# Les trois forward-tests scellés — la seule activité vivante du projet.
# Chemins en slashs : Windows les accepte et ils sont immunisés contre les
# mésaventures d'échappement (un \t devenu tabulation a déjà cassé ce bloc).
#
# La 3e colonne nommait les tâches planifiées Windows. Elles ont été
# SUPPRIMÉES le 2026-08-17 : c'est la console `orchestrator/robinbot-factory.py`
# qui lance tout désormais, et elle seule. On y nomme donc le worker de la
# factory — un tableau de bord qui désigne un mécanisme mort induit en erreur
# exactement au moment où l'on cherche pourquoi rien ne tourne.
FORWARDS = [
    ("Or — s11 XAUUSD H1",       os.path.join(DB_DIR, "gold_forward"),  "factory:gold_forward",  "horaire"),
    ("MACD-IA — indices D1",     os.path.join(DB_DIR, "macd_ai_paper"), "factory:macd_ai_paper", "horaire"),
    ("s13 — AUDCAD ext-MACD D1", os.path.join(DB_DIR, "s13_forward"),   "factory:s13_forward",   "horaire"),
]

# L'étude sentiment ne se lit pas comme un forward-test : elle ne prend aucune
# position, elle accumule des verdicts. Ses métriques sont donc distinctes
# (verdicts par juge, backlog, avancement F1) — les afficher dans le tableau
# des trades donnerait « 0 trade, +0.00 R », lecture fausse d'une étude qui
# travaille.
SENTIMENT_DIR = os.path.join(DB_DIR, "s14_sentiment")

app = Flask(__name__)


# ── Reconstruction de l'état ────────────────────────────────────────────────
def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _verdict_of(sdir: str) -> tuple[str, str]:
    """(étiquette courte, note) depuis research/VERDICT.md — sans interpréter :
    on cite le fichier, on ne le résume pas."""
    txt = _read(os.path.join(sdir, "research", "VERDICT.md"))
    if not txt:
        return "NON TESTÉ", "pas de VERDICT.md"
    # Un VERDICT.md peut contenir plusieurs de ces motifs dans sa prose
    # (s04 discute « pas d'edge » tout en concluant NON CONCLUSIF). Le verdict
    # est en tête de fichier : on retient le motif qui apparaît LE PLUS TÔT,
    # pas le premier de notre liste.
    hits = []
    for pat, label in [
        (r"PAS D'EDGE", "PAS D'EDGE"),
        (r"NON REPRODUCTIBLE", "NON REPRODUCTIBLE"),
        (r"NON CONCLUSIF", "NON CONCLUSIF"),
        (r"EDGE CONFIRM", "EDGE CONFIRMÉ"),
    ]:
        m = re.search(pat, txt)
        if m:
            hits.append((m.start(), label))
    if hits:
        label = min(hits)[1]
        first = next((l.strip("# ").strip() for l in txt.splitlines()
                      if l.strip()), "")
        return label, first[:90]
    return "VERDICT ATYPIQUE", ""


def build_strats() -> list[dict]:
    out = []
    # Les stratégies vivent à la RACINE PROJET, pas dans app/ — résolution
    # unique via core.paths.project_root (seam TBOT_PROJECT_ROOT pour les tests).
    sroot = os.path.join(str(project_root()), "strategies")
    for d in sorted(os.listdir(sroot)):
        sdir = os.path.join(sroot, d)
        if d.startswith("_") or not os.path.isdir(sdir):
            continue
        mtxt = _read(os.path.join(sdir, "manifest.yaml"))
        name = re.search(r'display_name:\s*"?([^"\n]+)"?', mtxt)
        magic = re.search(r"magic_number:\s*(\d+)", mtxt)
        status = re.search(r"status:\s*(\w+)", mtxt)
        verdict, note = _verdict_of(sdir)
        st = (status.group(1) if status else "RESEARCH").upper()
        out.append({
            "id": d,
            "name": (name.group(1).strip() if name else d),
            "magic": int(magic.group(1)) if magic else 0,
            "state": st.lower(), "status": st,
            # Aucune stratégie n'est en trading : allocation zéro, désactivée.
            # Ces champs existent parce que l'UI les affiche — les mettre à
            # zéro EST l'information.
            "enabled": False, "alloc": 0, "capMax": 0,
            "pnl": 0.0, "trades": 0, "wr": 0.0, "dd": 0.0, "auto": False,
            "curve": [0, 0],
            "note": f"{verdict} — {note}" if note else verdict,
        })
    return out


def build_ledger() -> list[list]:
    """Le journal réel du forward-test or — la seule activité 'live' du projet."""
    rows = []
    jpath = os.path.join(GOLD_DIR, "journal.csv")
    if os.path.exists(jpath):
        try:
            with open(jpath, newline="", encoding="utf-8") as f:
                for r in list(csv.DictReader(f))[-40:]:
                    rows.append([
                        r.get("bar_time", ""), "s11/XAUUSD forward",
                        "FORWARD", "XAUUSD",
                        r.get("side", ""), r.get("size", ""),
                        r.get("entry", ""), r.get("exit", ""),
                        float(r.get("pnl_ccy", 0) or 0), 0.0, 0.0,
                        float(r.get("pnl_ccy", 0) or 0),
                        r.get("exit_reason", "OPEN"),
                    ])
            rows.reverse()
        except Exception as e:
            rows.append([datetime.now().isoformat(timespec="minutes"),
                         "journal illisible", "ERREUR", "", "", "", "", "",
                         0, 0, 0, 0, str(e)[:40]])
    return rows


def build_forwards() -> list[dict]:
    out = []
    for label, ddir, task, cadence in FORWARDS:
        st = {}
        p = os.path.join(ddir, "status.json")
        if os.path.exists(p):
            try:
                st = json.loads(_read(p))
            except Exception:
                st = {"error": "status.json illisible"}
        out.append({
            "label": label, "task": task, "cadence": cadence,
            "n_trades": st.get("n_closed_total", 0),
            "cum_r": st.get("cum_r", 0.0),
            "capital": st.get("capital"),
            "last_bar": st.get("last_bar_time") or "—",
            "measured_at": st.get("generated_at_utc") or "jamais",
            "open": bool(st.get("open_position")),
            "error": st.get("error"),
        })
    return out


def _forwards_panel_html() -> str:
    """Panneau serveur-rendu injecté avant </body> — aucune modification du
    fichier UI. Style aligné sur la console (fond sombre, monospace)."""
    rows = []
    for f in build_forwards():
        state = ("MESURE EN COURS" if f["measured_at"] != "jamais" else "EN ATTENTE DU 1er PASSAGE")
        pos = " · position ouverte" if f["open"] else ""
        err = f" · <span style='color:#ff6b6b'>{f['error']}</span>" if f.get("error") else ""
        rows.append(
            f"<tr><td style='padding:6px 14px'>{f['label']}</td>"
            f"<td style='padding:6px 14px;opacity:.8'>{f['cadence']}</td>"
            f"<td style='padding:6px 14px'>{f['n_trades']}</td>"
            f"<td style='padding:6px 14px'>{f['cum_r']:+.2f} R</td>"
            f"<td style='padding:6px 14px;opacity:.8'>{f['last_bar']}</td>"
            f"<td style='padding:6px 14px'>{state}{pos}{err}</td></tr>")
    return (
        "<section style=\"margin:26px 18px;padding:16px 18px;border:1px solid #2c3a4a;"
        "border-radius:8px;background:#101820;color:#d8e2ec;font-family:ui-monospace,monospace\">"
        "<h2 style='margin:0 0 4px;font-size:15px;letter-spacing:.08em'>FORWARD-TESTS SCELLÉS</h2>"
        "<div style='opacity:.6;font-size:11px;margin-bottom:10px'>protocoles hashés · journaux à chaîne de "
        "hachage · critères d'arrêt figés avant les données — la seule preuve qui compte est prospective</div>"
        "<table style='border-collapse:collapse;font-size:12.5px;width:100%'>"
        "<tr style='opacity:.55;text-align:left'><th style='padding:6px 14px'>scellé</th>"
        "<th style='padding:6px 14px'>cadence</th><th style='padding:6px 14px'>trades clos</th>"
        "<th style='padding:6px 14px'>R cumulé</th><th style='padding:6px 14px'>dernière barre</th>"
        "<th style='padding:6px 14px'>état</th></tr>"
        + "".join(rows) + "</table></section>")


def build_sentiment() -> dict:
    """État de l'étude s14 — vide tant qu'elle n'a pas tourné (c'est un état
    légitime, pas une erreur : le worker n'écrit qu'au premier passage)."""
    p = os.path.join(SENTIMENT_DIR, "status.json")
    if not os.path.exists(p):
        return {"active": False}
    try:
        st = json.loads(_read(p))
    except Exception:
        return {"active": True, "error": "status.json illisible"}
    judges = st.get("judges") or {}
    return {
        "active": True,
        "n_news": st.get("n_news_total", 0),
        "n_stale": st.get("n_stale", 0),
        "measured_at": st.get("generated_at_utc") or "jamais",
        "judges": {
            name: {
                "n_verdicts": j.get("n_verdicts_total", 0),
                "n_na": j.get("n_na", 0),
                "backlog": j.get("backlog_news", 0),
            }
            for name, j in judges.items()
        },
        "stop": st.get("stop_criteria") or {},
    }


def _sentiment_panel_html() -> str:
    s = build_sentiment()
    if not s.get("active"):
        corps = ("<div style='opacity:.6;font-size:12px'>en attente du premier "
                 "passage — le worker pose le scellé puis collecte</div>")
    elif s.get("error"):
        corps = f"<div style='color:#ff6b6b;font-size:12px'>{s['error']}</div>"
    else:
        lignes = []
        for name, j in sorted(s["judges"].items()):
            lignes.append(
                f"<tr><td style='padding:6px 14px'>{name}</td>"
                f"<td style='padding:6px 14px'>{j['n_verdicts']}</td>"
                f"<td style='padding:6px 14px;opacity:.8'>{j['n_na']}</td>"
                f"<td style='padding:6px 14px;opacity:.8'>{j['backlog']}</td></tr>")
        corps = (
            f"<div style='opacity:.75;font-size:12px;margin-bottom:8px'>"
            f"{s['n_news']} news collectées · {s['n_stale']} périmées · "
            f"dernier passage {s['measured_at']}</div>"
            "<table style='border-collapse:collapse;font-size:12.5px;width:100%'>"
            "<tr style='opacity:.55;text-align:left'><th style='padding:6px 14px'>juge</th>"
            "<th style='padding:6px 14px'>verdicts</th><th style='padding:6px 14px'>na</th>"
            "<th style='padding:6px 14px'>backlog</th></tr>"
            + "".join(lignes) + "</table>")
    return (
        "<section style=\"margin:26px 18px;padding:16px 18px;border:1px solid #2c3a4a;"
        "border-radius:8px;background:#101820;color:#d8e2ec;font-family:ui-monospace,monospace\">"
        "<h2 style='margin:0 0 4px;font-size:15px;letter-spacing:.08em'>s14 — SENTIMENT (SCELLÉ)</h2>"
        "<div style='opacity:.6;font-size:11px;margin-bottom:10px'>juge Claude + témoin FinBERT sur "
        "les mêmes news · aucun hit-rate affiché avant l'effectif F1 : le protocole l'interdit</div>"
        + corps + "</section>")


# ── LES TROIS NIVEAUX D'EXPLOITATION ────────────────────────────────────────
# Le « mode » d'une stratégie n'est pas un champ de plus : c'est le `status:`
# de son manifeste, que la règle R7 désigne comme seule source de vérité.
#   LIVE       -> production, argent réel
#   PAPER      -> validation en live, capital virtuel
#   RESEARCH   -> développement, backtest, mise au point
#   BACKTESTED -> idem, mais mesuré au moins une fois
#   RETIRED    -> clos
#
# POURQUOI trois niveaux empilés et non des onglets : ce qui tourne avec de
# l'argent réel ne doit jamais être à un clic. Une section « PRODUCTION —
# aucune stratégie armée » est une information, pas un vide à masquer. Et avec
# 0 en production, 4 en paper et 18 en dev, des onglets donneraient deux
# fenêtres presque vides.
#
# ET SURTOUT : on n'affiche pas ce que le manifeste DÉCLARE, on le confronte au
# RÉEL (une étude a-t-elle un journal vivant ?). Un manifeste qui annonce PAPER
# sans journal ment ; la divergence s'affiche au lieu de dormir.
ETUDES_VIVANTES = [
    # (dossier de données, stratégie instanciée, libellé)
    ("gold_forward", "s11_legacy_breakout", "Or — XAUUSD H1"),
    ("s13_forward", "s13_macd_fx", "AUDCAD ext-MACD D1"),
    ("macd_ai_paper", "s12_prt_macd_meanrev", "MACD-IA — indices D1"),
    ("s14_sentiment", None, "Sentiment des news (étude)"),
    ("portfolio_forward", None, "Portefeuille Tier-1 naïf"),
]


def _etude_etat(dossier: str) -> dict:
    """L'état réel d'une étude : ce que le disque dit, pas ce qu'on espère."""
    p = os.path.join(DB_DIR, dossier, "status.json")
    st = {}
    if os.path.exists(p):
        try:
            st = json.loads(_read(p))
        except Exception:
            return {"vivante": True, "erreur": "status.json illisible"}
    judges = st.get("judges") or {}
    return {
        "vivante": bool(st),
        "trades": st.get("n_closed_total", 0),
        "cum_r": st.get("cum_r", 0.0),
        "capital": st.get("capital"),
        "position": bool(st.get("open_position")),
        "mesure": st.get("generated_at_utc") or "jamais",
        "news": st.get("n_news_total"),
        "verdicts": (sum(int(j.get("n_verdicts_total", 0))
                         for j in judges.values()) if judges else None),
        "arret": st.get("stop_criteria") or {},
    }


def build_niveaux() -> dict:
    """Les stratégies rangées par niveau, le déclaré confronté au réel."""
    strats = {s["id"]: s for s in build_strats()}
    etudes = {}
    for dossier, strat_id, libelle in ETUDES_VIVANTES:
        e = _etude_etat(dossier)
        e.update({"dossier": dossier, "strategie": strat_id, "libelle": libelle})
        etudes[dossier] = e

    # Une stratégie est en PAPER dès qu'une étude vivante l'instancie.
    en_paper = {e["strategie"] for e in etudes.values()
                if e["vivante"] and e["strategie"]}

    niveaux = {"prod": [], "paper": [], "dev": [], "divergences": []}
    for sid, s in sorted(strats.items()):
        declare = (s.get("status") or "RESEARCH").upper()
        if declare == "LIVE":
            niveaux["prod"].append(s)
        elif declare == "PAPER" or sid in en_paper:
            niveaux["paper"].append(s)
            if declare != "PAPER":
                niveaux["divergences"].append(
                    f"{sid} : une étude tourne pour cette stratégie, mais son "
                    f"manifeste déclare {declare} (attendu PAPER)")
        elif declare == "RETIRED":
            continue
        else:
            niveaux["dev"].append(s)
        if declare == "PAPER" and sid not in en_paper:
            niveaux["divergences"].append(
                f"{sid} : le manifeste déclare PAPER mais aucune étude vivante "
                f"ne l'instancie")
    niveaux["etudes"] = etudes
    return niveaux


def _carte_etude(e: dict) -> str:
    if not e["vivante"]:
        corps = "<span style='opacity:.55'>en attente du premier passage</span>"
    elif e.get("erreur"):
        corps = f"<span style='color:#ff6b6b'>{e['erreur']}</span>"
    elif e.get("verdicts") is not None:
        # Étude de jugement : elle ne prend aucune position, on montre sa matière.
        corps = (f"<b>{e['news']}</b> news · <b>{e['verdicts']}</b> verdicts"
                 "<div style='opacity:.6;font-size:11px;margin-top:4px'>"
                 "aucun taux de réussite avant l'effectif du protocole</div>")
    else:
        pos = (" · <span style='color:#ffd479'>position ouverte</span>"
               if e["position"] else "")
        cap = f" · capital {e['capital']:.2f}" if e.get("capital") is not None else ""
        jalon = (e.get("arret") or {}).get("fail") or ""
        corps = (f"<b>{e['trades']}</b> trade(s) clos · <b>{e['cum_r']:+.2f} R</b>"
                 f"{cap}{pos}"
                 + (f"<div style='opacity:.6;font-size:11px;margin-top:4px'>"
                    f"{str(jalon)[:130]}</div>" if jalon else ""))
    return (
        "<div style=\"flex:1 1 300px;min-width:280px;padding:12px 14px;"
        "border:1px solid #2c3a4a;border-radius:7px;background:#0c141b\">"
        f"<div style='font-size:13px;margin-bottom:6px'>{e['libelle']}</div>"
        f"<div style='font-size:12.5px'>{corps}</div>"
        f"<div style='opacity:.45;font-size:10.5px;margin-top:7px'>"
        f"{e['dossier']} · dernier passage {e['mesure']}</div></div>")


def _bloc_niveau(titre: str, sous_titre: str, contenu: str) -> str:
    return (f"<h3 style='margin:18px 0 4px;font-size:13.5px;letter-spacing:.08em'>"
            f"{titre}</h3>"
            f"<div style='opacity:.55;font-size:11px;margin-bottom:8px'>"
            f"{sous_titre}</div>{contenu}")


def _niveaux_panel_html() -> str:
    n = build_niveaux()

    if n["prod"]:
        prod = "".join(
            f"<div style='padding:10px 14px;border:1px solid #ff6b6b;"
            f"border-radius:7px;margin-bottom:6px'>{s['name']}</div>"
            for s in n["prod"])
    else:
        prod = ("<div style='padding:14px;border:1px dashed #3a4a5c;"
                "border-radius:7px;opacity:.7;font-size:12.5px'>"
                "Aucune stratégie armée en argent réel. L'armement est un geste "
                "d'Adrian (R10), jamais automatique.</div>")

    cartes = "".join(_carte_etude(e) for e in n["etudes"].values())
    lignes_dev = "".join(
        f"<tr><td style='padding:5px 12px'>{s['id']}</td>"
        f"<td style='padding:5px 12px;opacity:.8'>{s['status']}</td>"
        f"<td style='padding:5px 12px;opacity:.75'>{s['note'][:78]}</td></tr>"
        for s in n["dev"])

    div = ""
    if n["divergences"]:
        div = ("<div style=\"margin:10px 0;padding:10px 14px;"
               "border:1px solid #ff6b6b;border-radius:7px;color:#ff9d9d;"
               "font-size:12px\"><b>DIVERGENCE déclaré / réel</b><br>"
               + "<br>".join(n["divergences"]) + "</div>")

    return (
        "<section style=\"margin:26px 18px;padding:16px 18px;"
        "border:1px solid #2c3a4a;border-radius:8px;background:#101820;"
        "color:#d8e2ec;font-family:ui-monospace,monospace\">"
        "<h2 style='margin:0 0 2px;font-size:15px;letter-spacing:.08em'>"
        "NIVEAUX D'EXPLOITATION</h2>"
        "<div style='opacity:.6;font-size:11px;margin-bottom:6px'>le niveau vient "
        "du <code>status:</code> du manifeste (R7, source unique de vérité), et il "
        "est confronté au réel : une étude qui tourne vaut PAPER, quoi qu'annonce "
        "le manifeste</div>"
        + div
        + _bloc_niveau("PRODUCTION — ARGENT RÉEL", "status: LIVE", prod)
        + _bloc_niveau("PAPER — VALIDATION EN LIVE, CAPITAL VIRTUEL",
                       "études scellées : protocole gelé avant la première mesure",
                       f"<div style='display:flex;flex-wrap:wrap;gap:10px'>{cartes}</div>")
        + _bloc_niveau("DEV — RECHERCHE, BACKTEST, MISE AU POINT",
                       f"{len(n['dev'])} stratégies · aucune ne prend de position",
                       "<details><summary style='cursor:pointer;font-size:12px;"
                       "opacity:.8'>déplier</summary>"
                       "<table style='border-collapse:collapse;font-size:12px;"
                       "width:100%;margin-top:8px'>"
                       "<tr style='opacity:.5;text-align:left'>"
                       "<th style='padding:5px 12px'>stratégie</th>"
                       "<th style='padding:5px 12px'>statut</th>"
                       "<th style='padding:5px 12px'>verdict</th></tr>"
                       + lignes_dev + "</table></details>")
        + "</section>")


@app.route("/api/state")
def api_state():
    status = {}
    spath = os.path.join(GOLD_DIR, "status.json")
    if os.path.exists(spath):
        try:
            status = json.loads(_read(spath))
        except Exception:
            status = {"error": "status.json illisible"}
    return jsonify({
        "generated": datetime.now().isoformat(timespec="seconds"),
        "strategies": build_strats(),
        "ledger": build_ledger(),
        "gold_forward": status,
        "forwards": build_forwards(),
        "sentiment": build_sentiment(),
        "niveaux": build_niveaux(),
    })


@app.route("/")
def dashboard():
    html = _read(UI)
    if not html:
        return "dashboard.html introuvable", 500

    strats = json.dumps(build_strats(), ensure_ascii=False, indent=1)
    ledger = json.dumps(build_ledger(), ensure_ascii=False, indent=1)

    # Remplace les constantes prototypées par l'état réel. Si l'UI change de
    # forme un jour, ces regex échouent BRUYAMMENT (bandeau d'erreur) plutôt
    # que de servir silencieusement les données périmées du prototype.
    new, n1 = re.subn(r"const STRATS = \[.*?\n\];",
                      f"const STRATS = {strats};", html, count=1, flags=re.S)
    new, n2 = re.subn(r"const LEDGER = \[.*?\n\];",
                      f"const LEDGER = {ledger};", new, count=1, flags=re.S)
    if n1 != 1 or n2 != 1:
        return ("<h1>Injection échouée</h1><p>La structure de dashboard.html a "
                "changé (STRATS/LEDGER introuvables). Refus de servir des "
                "données périmées.</p>", 500)
    stamp = (f"<div style='position:fixed;bottom:6px;right:10px;opacity:.55;"
             f"font:11px monospace'>données réelles · "
             f"{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>")
    # Le fichier UI du prototype ne contient PAS de balise </body> : une
    # injection par replace y échouait silencieusement — panneau et horodatage
    # n'apparaissaient jamais. On insère avant </body> si elle existe, sinon
    # on APPEND en fin de document (les navigateurs l'acceptent, et un panneau
    # visible vaut mieux qu'une élégance invisible).
    # Les trois niveaux remplacent les panneaux separes : une seule
    # lecture, du plus engageant (argent reel) au plus lointain.
    extra = _niveaux_panel_html() + stamp
    if "</body>" in new:
        return new.replace("</body>", extra + "</body>")
    return new + extra


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8742, debug=False)

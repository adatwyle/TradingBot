"""
Tests du pilote — synthétiques, AUCUN réseau, AUCUNE session Claude réelle.

POURQUOI ce banc : le pilote est le seul worker qui DÉPENSE des tokens. On
vérifie donc surtout ce qui garantit qu'il n'en dépense pas pour rien (silence
sans événement, une seule parole par jour) et qu'il ne rate pas ce qui compte
(trades, incidents, paliers, mesure figée).

    pytest orchestrator/test_robinbot_pilot.py -q
"""
from __future__ import annotations

import csv
import importlib.util
import json
import pathlib
from datetime import datetime

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "robinbot_pilot", _HERE / "robinbot-pilot.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

MATIN = datetime(2026, 8, 18, 9, 0)          # après l'heure de parole
NUIT = datetime(2026, 8, 18, 3, 0)           # avant
LENDEMAIN = datetime(2026, 8, 19, 9, 0)


class Usine:
    def __init__(self, tmp: pathlib.Path):
        self.tmp = tmp
        self.envois: list[str] = []
        self.analyses: list[list[str]] = []
        self.analyse_ok = True
        self.envoi_ok = True

    def status(self, etude: str, **champs) -> None:
        d = self.tmp / etude
        d.mkdir(parents=True, exist_ok=True)
        (d / "status.json").write_text(json.dumps(champs), encoding="utf-8")

    def journal(self, etude: str, n_lignes: int) -> None:
        d = self.tmp / etude
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "journal.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["a", "b"])
            for i in range(n_lignes):
                w.writerow([i, "x"])

    def panneau(self, contenu: str) -> None:
        (self.tmp / "panel.txt").write_text(contenu, encoding="utf-8")


@pytest.fixture
def usine(tmp_path, monkeypatch) -> Usine:
    u = Usine(tmp_path)
    notif = tmp_path / "notifier"
    notif.mkdir()
    (notif / "config.json").write_text(json.dumps({"chat_id": "111"}),
                                       encoding="utf-8")
    u.panneau("gold_forward = on\nsupervision = on\n")

    monkeypatch.setattr(mod, "PILOT_DIR", tmp_path / "pilot")
    monkeypatch.setattr(mod, "STATE_FILE", tmp_path / "pilot" / "state.json")
    monkeypatch.setattr(mod, "NOTIFY_DIR", notif)
    monkeypatch.setattr(mod, "PANEL_FILE", tmp_path / "panel.txt")
    monkeypatch.setattr(mod, "ETUDES", [
        ("gold_forward", str(tmp_path / "gold_forward")),
        ("s14_sentiment", str(tmp_path / "s14_sentiment")),
    ])
    monkeypatch.setattr(mod, "load_token", lambda: "TOKEN-BIDON")
    monkeypatch.setattr(mod, "analyser",
                        lambda faits: (u.analyses.append(faits),
                                       "lecture" if u.analyse_ok else None)[1])
    monkeypatch.setattr(mod, "send",
                        lambda t, c, txt: (u.envois.append(txt), u.envoi_ok)[1])
    return u


# == LE SILENCE (le cas normal) ================================================
def test_sans_evenement_aucun_token_depense(usine):
    usine.status("gold_forward", n_closed_total=0, generated_at_utc="T1")
    assert mod.tick(now_local=MATIN) == 0          # 1re photo
    usine.status("gold_forward", n_closed_total=0, generated_at_utc="T2")
    assert mod.tick(now_local=MATIN) == 0
    assert usine.analyses == [] and usine.envois == []


def test_avant_l_heure_de_parole_il_se_tait(usine):
    usine.status("gold_forward", n_closed_total=3, generated_at_utc="T1")
    assert mod.tick(now_local=NUIT) == 0
    assert usine.analyses == []


def test_une_seule_parole_par_jour(usine):
    usine.status("gold_forward", n_closed_total=0, generated_at_utc="T1")
    mod.tick(now_local=MATIN)                      # photo initiale
    usine.status("gold_forward", n_closed_total=2, generated_at_utc="T2")
    assert mod.tick(now_local=MATIN) == 0
    assert len(usine.envois) == 1

    usine.status("gold_forward", n_closed_total=5, generated_at_utc="T3")
    assert mod.tick(now_local=MATIN) == 0          # même jour : silence
    assert len(usine.envois) == 1
    assert mod.tick(now_local=LENDEMAIN) == 0      # le lendemain : il parle
    assert len(usine.envois) == 2


# == CE QU'IL NE RATE PAS ======================================================
def test_trades_nouveaux_declenchent_la_lecture(usine):
    usine.status("gold_forward", n_closed_total=0, generated_at_utc="T1")
    mod.tick(now_local=MATIN)
    usine.status("gold_forward", n_closed_total=2, generated_at_utc="T2")
    assert mod.tick(now_local=MATIN) == 0
    assert any("+2 trade" in f for f in usine.analyses[0])
    assert usine.envois[0].startswith("🧭 RobinBot — lecture du jour")


def test_incident_autooff_en_premiere_ligne(usine):
    usine.status("gold_forward", n_closed_total=0, generated_at_utc="T1")
    mod.tick(now_local=MATIN)
    usine.panneau("gold_forward = off   # AUTO-OFF 2026-08-18 — sortie 3\n")
    assert mod.tick(now_local=MATIN) == 0
    assert "INCIDENT" in usine.analyses[0][0]      # bien en tête


def test_palier_de_verdicts_franchi(usine):
    usine.status("s14_sentiment", judges={"claude-cli": {"n_verdicts_total": 5}})
    mod.tick(now_local=MATIN)
    # 5 -> 12 : palier 10 franchi, on parle.
    usine.status("s14_sentiment", judges={"claude-cli": {"n_verdicts_total": 12}})
    assert mod.tick(now_local=MATIN) == 0
    assert any("palier de 10" in f for f in usine.analyses[0])


def test_pas_de_bruit_entre_deux_paliers(usine):
    usine.status("s14_sentiment", judges={"claude-cli": {"n_verdicts_total": 12}})
    mod.tick(now_local=MATIN)
    usine.status("s14_sentiment", judges={"claude-cli": {"n_verdicts_total": 20}})
    assert mod.tick(now_local=MATIN) == 0
    assert usine.analyses == []                    # même palier : silence


def test_mesure_figee_signale_un_worker_muet(usine):
    usine.status("gold_forward", n_closed_total=0, generated_at_utc="FIGE")
    mod.tick(now_local=MATIN)
    assert mod.tick(now_local=LENDEMAIN) == 0
    assert any("aucune mesure nouvelle" in f for f in usine.analyses[0])


# == LES REFUS PROPRES =========================================================
def test_session_indisponible_exit_2_et_rien_de_perdu(usine, tmp_path):
    usine.status("gold_forward", n_closed_total=0, generated_at_utc="T1")
    mod.tick(now_local=MATIN)
    usine.status("gold_forward", n_closed_total=4, generated_at_utc="T2")
    usine.analyse_ok = False
    assert mod.tick(now_local=MATIN) == 2
    assert usine.envois == []
    # Ni la photo ni la date de parole n'ont bougé : le fait sera réinstruit.
    etat = json.loads((tmp_path / "pilot" / "state.json").read_text(encoding="utf-8"))
    assert etat["photo"]["etudes"]["gold_forward"]["n_trades"] == 0
    assert "last_spoke_date" not in etat

    usine.analyse_ok = True
    assert mod.tick(now_local=MATIN) == 0
    assert any("+4 trade" in f for f in usine.analyses[-1])


def test_envoi_echoue_exit_2(usine):
    usine.status("gold_forward", n_closed_total=0, generated_at_utc="T1")
    mod.tick(now_local=MATIN)
    usine.status("gold_forward", n_closed_total=1, generated_at_utc="T2")
    usine.envoi_ok = False
    assert mod.tick(now_local=MATIN) == 2


def test_dry_run_n_appelle_rien(usine, tmp_path):
    usine.status("gold_forward", n_closed_total=7, generated_at_utc="T1")
    assert mod.tick(now_local=MATIN, dry=True) == 0
    assert usine.analyses == [] and usine.envois == []
    assert not (tmp_path / "pilot" / "state.json").exists()


def test_lecture_seule_par_construction():
    """Le pilote observe et écrit à Adrian ; il n'agit pas."""
    outils = set(mod.ALLOWED_TOOLS.split(","))
    assert outils == {"Read", "Grep", "Glob"}
    for interdit in ("Bash", "Write", "Edit"):
        assert interdit not in mod.ALLOWED_TOOLS

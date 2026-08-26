"""
Tests de la tbot factory — le superviseur console TradingBot (TCK-005).

Ce banc couvre ce qui DÉCIDE : le panneau (fail-closed), les gardes matière
des workers claude: (tickets, snapshots S017), la fenêtre horaire du
collecteur GEX, le garde-fou R4, la cohérence du catalogue, et le contrat
STDIN des sessions claude (CLI mocké — aucune session réelle, aucun token).

Le catalogue est injecté par `TBF_CATALOGUE` (seam prévu dans le module) :
aucun vrai worker n'est jamais lancé ici.

    pytest app/orchestrator/test_tbot_factory.py -q
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import time
from datetime import datetime

import pytest

_HERE = pathlib.Path(__file__).resolve().parent

_ENV_KEYS = ("TBF_CATALOGUE", "TBF_ROOT", "TBF_PANEL", "TBF_LOG_DIR",
             "TBF_LOCK", "TBF_STOP", "TBF_STATE_DIR", "TBOT_DB_DIR",
             "TBF_CLAUDE_BIN", "TBOT_LIVE")


def _charger(tmp: pathlib.Path, catalogue: list[dict] | None):
    """Recharge le module avec une usine jetable (le catalogue est lu à
    l'import). catalogue=None -> catalogue RÉEL (ROOT = vrai dépôt)."""
    for k in _ENV_KEYS:
        os.environ.pop(k, None)
    if catalogue is not None:
        os.environ["TBF_CATALOGUE"] = json.dumps(catalogue)
        os.environ["TBF_ROOT"] = str(tmp)
    os.environ["TBF_PANEL"] = str(tmp / "panel.txt")
    os.environ["TBF_LOG_DIR"] = str(tmp / "logs")
    os.environ["TBF_LOCK"] = str(tmp / ".lock")
    os.environ["TBF_STOP"] = str(tmp / ".stop")
    os.environ["TBF_STATE_DIR"] = str(tmp / "state")
    os.environ["TBOT_DB_DIR"] = str(tmp / "db")
    spec = importlib.util.spec_from_file_location(
        "tbot_factory_test", _HERE / "tbot-factory.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CATALOGUE = [
    {"name": "collecte", "spec": "py:outil/run.py", "interval": 900, "kind": "tick"},
    {"name": "cc_app_queue", "spec": "claude:cc_app_queue", "interval": 1800, "kind": "tick"},
    {"name": "cc_S017", "spec": "claude:cc_S017", "interval": 3600, "kind": "tick"},
    {"name": "cc_support_block", "spec": "claude:cc_support_block", "interval": 300, "kind": "tick"},
    {"name": "libre", "spec": "claude:dis bonjour", "interval": 3600, "kind": "tick"},
]


@pytest.fixture
def usine(tmp_path):
    mod = _charger(tmp_path, CATALOGUE)
    yield mod
    for k in _ENV_KEYS:
        os.environ.pop(k, None)


@pytest.fixture
def usine_reelle(tmp_path):
    """Le module avec son catalogue RÉEL (aucun worker lancé — inspection)."""
    mod = _charger(tmp_path, None)
    yield mod
    for k in _ENV_KEYS:
        os.environ.pop(k, None)


class FauxProc:
    def __init__(self, pid=4242):
        self.pid = pid


class FauxStdin:
    def __init__(self):
        self.data = ""
        self.closed = False

    def write(self, t):
        self.data += t

    def close(self):
        self.closed = True


class FauxPopen:
    """CLI claude mocké : capture argv, stdin et env — sort en 0 aussitôt."""
    instances: list = []

    def __init__(self, cmd, **kw):
        self.cmd = list(cmd)
        self.kw = kw
        self.pid = 4242
        self.stdin = FauxStdin()
        FauxPopen.instances.append(self)

    def wait(self, timeout=None):
        return 0


def _ticket(tmp: pathlib.Path, tid: str, to: str, status: str = "open",
            blocking: str = "false") -> pathlib.Path:
    tdir = tmp / "tickets"
    tdir.mkdir(exist_ok=True)
    f = tdir / f"{tid}_test.md"
    f.write_text(f"---\nid: {tid}\nfrom: cc-x\nto: {to}\nstatus: {status}\n"
                 f"blocking: {blocking}\ncreated: 2026-08-26\n---\n\n"
                 f"## Question\ncontenu\n", encoding="utf-8")
    return f


# == LE PANNEAU (fail-closed, hérité et vérifié à l'identique) =================
def test_worker_absent_du_panneau_est_off(usine, tmp_path):
    (tmp_path / "panel.txt").write_text("collecte = on\n", encoding="utf-8")
    panel = usine.read_panel()
    assert usine.due("collecte", panel, time.time()) is True
    assert usine.due("cc_app_queue", panel, time.time()) is False   # absent = OFF


def test_panneau_introuvable_eteint_tout(usine, tmp_path):
    (tmp_path / "panel.txt").unlink(missing_ok=True)
    panel = usine.read_panel()
    assert panel == {}
    assert usine.due("collecte", panel, time.time()) is False


def test_cadence_forcee_et_ligne_illisible(usine, tmp_path):
    (tmp_path / "panel.txt").write_text(
        "collecte = on:120\ncc_app_queue = on:pouet\n# commentaire\nordure\n",
        encoding="utf-8")
    panel = usine.read_panel()
    assert panel["collecte"] == (True, 120)
    assert panel["cc_app_queue"] == (True, None)   # cadence illisible -> catalogue
    assert "ordure" not in panel


def test_pas_deux_ticks_du_meme_worker(usine, tmp_path):
    (tmp_path / "panel.txt").write_text("collecte = on\n", encoding="utf-8")
    panel = usine.read_panel()
    usine._running["collecte"] = FauxProc()
    assert usine.due("collecte", panel, time.time()) is False


def test_incident_auto_off_dans_le_panneau(usine, tmp_path):
    (tmp_path / "panel.txt").write_text("collecte = on\ncc_S017 = on\n",
                                        encoding="utf-8")
    usine.panel_set_off("collecte", "sortie 3 — SCELLÉ VIOLÉ")
    texte = (tmp_path / "panel.txt").read_text(encoding="utf-8")
    assert "collecte = off" in texte and "AUTO-OFF" in texte
    assert "cc_S017 = on" in texte                  # le reste intact
    assert usine.read_panel()["collecte"][0] is False


def test_verrou_et_stop(usine, tmp_path):
    usine.write_lock()
    assert usine.lock_is_fresh() is True
    vieux = time.time() - (usine.LOCK_STALE_SEC + 10)
    os.utime(tmp_path / ".lock", (vieux, vieux))
    assert usine.lock_is_fresh() is False           # factory morte : on passe
    (tmp_path / ".stop").write_text("", encoding="utf-8")
    assert usine.stop_requested() is True
    assert usine.run(dry=True, once=True) == 1      # refus explicite


# == CATALOGUE RÉEL : COHÉRENCE ================================================
def test_catalogue_reel_coherent(usine_reelle):
    """Noms uniques, specs valides, gardes claude: enregistrées, fichiers py:
    livrés, cwd existants — le catalogue v1 doit être lançable tel quel."""
    u = usine_reelle
    noms = [w[0] for w in u.WORKERS]
    assert len(noms) == len(set(noms)), "noms de workers non uniques"
    attendus = {"gex_S017", "cc_S017", "cc_app_queue", "cc_spec_queue",
                "cc_support_block", "gateway", "notify",
                # Serveur de supervision (T6/T4) : service persistant relancé
                # avec backoff — même mécanique que robinbot.
                "supervision",
                # Études scellées migrées du prototype (TCK-009/T10) —
                # cadences identiques à robinbot, off par défaut au panneau.
                "gold_forward", "s13_forward", "macd_ai_paper",
                "s14_sentiment", "alexg_paper"}
    assert attendus == set(noms)
    # supervision est le SEUL service persistant du catalogue v1.
    services = [w[0] for w in u.WORKERS if w[4] == "service"]
    assert services == ["supervision"]
    for name, cwd, spec, interval, kind in u.WORKERS:
        assert kind in ("tick", "service")
        assert interval > 0
        assert cwd.is_dir(), f"cwd absent pour {name}: {cwd}"
        if spec.startswith("py:"):
            cible = spec[3:].split()[0]
            assert (u.ROOT / cible).exists(), f"fichier py absent : {cible}"
        elif spec.startswith("claude:"):
            assert spec[7:].strip() in u.CLAUDE_GUARDS, \
                f"garde matière non enregistrée pour {name}"
        else:
            pytest.fail(f"spec inconnue au catalogue : {spec}")


def test_build_cmd_claude_stdin_contract(usine):
    """Le prompt ne figure JAMAIS dans l'argv (il passe par STDIN) ; flags du
    prototype conservés ; passage par cmd.exe (shim npm .cmd)."""
    cmd = usine.build_cmd("claude:cc_app_queue")
    assert cmd[:2] == ["cmd", "/c"]
    assert "-p" in cmd and "--output-format" in cmd and "--max-turns" in cmd
    assert "cc_app_queue" not in cmd                # pas de prompt dans l'argv


def test_spec_inconnue_refusee(usine):
    with pytest.raises(ValueError):
        usine.build_cmd("bash:rm -rf /")


# == GARDE-FOU R4 (jamais de trade réel) =======================================
def test_r4_catalogue_avec_marqueur_live_refuse(tmp_path):
    mauvais = [{"name": "paper_S013", "spec": "py:run_paper.py --live",
                "interval": 3600, "kind": "tick"}]
    with pytest.raises(AssertionError, match="R4"):
        _charger(tmp_path, mauvais)
    for k in _ENV_KEYS:
        os.environ.pop(k, None)


def test_r4_env_purge_des_ticks(usine):
    os.environ["TBOT_LIVE"] = "1"
    env = usine._child_env()
    assert "TBOT_LIVE" not in env
    os.environ.pop("TBOT_LIVE", None)
    # tick claude : purge aussi le contexte de session Claude Code parente
    os.environ["CLAUDE_TEST_MARKER"] = "x"
    env = usine._child_env(claude_tick=True)
    assert "CLAUDE_TEST_MARKER" not in env
    os.environ.pop("CLAUDE_TEST_MARKER", None)


# == GARDES MATIÈRE : TICKETS ==================================================
def test_garde_cc_app_prend_le_premier_ticket_ouvert(usine, tmp_path):
    _ticket(tmp_path, "TCK-010", "cc-app", "open")
    _ticket(tmp_path, "TCK-011", "cc-app", "answered")
    _ticket(tmp_path, "TCK-012", "cc-spec", "open", blocking="true")
    m = usine.guard_cc_app_queue()
    assert m is not None
    prompt, consommer = m
    assert "TCK-010" in prompt and "cc-app" in prompt
    assert "TCK-011" not in prompt                  # answered : ignoré
    # cc-spec voit le sien, pas celui de cc-app
    prompt_spec, _ = usine.guard_cc_spec_queue()
    assert "TCK-012" in prompt_spec
    # le débloqueur voit le bloquant ouvert
    prompt_bloc, _ = usine.guard_cc_support_block()
    assert "TCK-012" in prompt_bloc and "BLOQUANT" in prompt_bloc


def test_garde_cooldown_apres_tentative(usine, tmp_path):
    """Consommer avant de payer : un ticket tenté ne rejoue pas en boucle."""
    _ticket(tmp_path, "TCK-020", "cc-app", "open")
    prompt, consommer = usine.guard_cc_app_queue()
    assert "TCK-020" in prompt
    consommer()                                     # la factory note la tentative
    assert usine.guard_cc_app_queue() is None       # cooldown : pas de rejeu


def test_garde_file_vide_est_no_op(usine, tmp_path):
    (tmp_path / "tickets").mkdir(exist_ok=True)     # file VIDE
    assert usine.guard_cc_app_queue() is None
    assert usine.guard_cc_spec_queue() is None
    assert usine.guard_cc_support_block() is None


def test_garde_bloquant_ignore_les_non_bloquants(usine, tmp_path):
    _ticket(tmp_path, "TCK-030", "cc-app", "open", blocking="false")
    assert usine.guard_cc_support_block() is None


# == GARDE MATIÈRE : cc_S017 (nouveaux jours de snapshots) =====================
def _poser_snapshots(tmp: pathlib.Path, jours: list[str]) -> None:
    gdir = tmp / "db" / "S017" / "gex"
    gdir.mkdir(parents=True, exist_ok=True)
    for j in jours:
        (gdir / f"SPY_gex_{j}.csv").write_text("asof,spot\n", encoding="utf-8")


def _poser_mandat(tmp: pathlib.Path) -> None:
    d = tmp / "strategies" / "S017_ireland_gex"
    d.mkdir(parents=True, exist_ok=True)
    (d / "mandat-cc.txt").write_text("Relance research/phase_a.py et analyse.",
                                     encoding="utf-8")


def test_cc_s017_pas_assez_de_jours(usine, tmp_path):
    _poser_snapshots(tmp_path, ["2026-08-24", "2026-08-25"])   # 2 < N=3
    _poser_mandat(tmp_path)
    assert usine.guard_cc_s017() is None


def test_cc_s017_matiere_puis_consommation(usine, tmp_path):
    _poser_snapshots(tmp_path, ["2026-08-24", "2026-08-25", "2026-08-26"])
    _poser_mandat(tmp_path)
    m = usine.guard_cc_s017()
    assert m is not None
    prompt, consommer = m
    assert "3 nouveau(x) jour(s)" in prompt
    assert "Relance research/phase_a.py" in prompt   # le mandat est DANS le prompt
    consommer()                                      # jours marqués vus
    assert usine.guard_cc_s017() is None             # plus de matière
    # un 4e jour arrive : 1 nouveau < 3 -> toujours pas de matière
    _poser_snapshots(tmp_path, ["2026-08-27"])
    assert usine.guard_cc_s017() is None


def test_cc_s017_sans_mandat_ne_lance_rien(usine, tmp_path):
    _poser_snapshots(tmp_path, ["2026-08-24", "2026-08-25", "2026-08-26"])
    # pas de mandat-cc.txt
    assert usine.guard_cc_s017() is None


# == FENÊTRE HORAIRE DU COLLECTEUR GEX =========================================
@pytest.fixture
def collecteur():
    spec = importlib.util.spec_from_file_location(
        "tbot_collecte_test", _HERE / "tbot-collecte-gex-s017.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fenetre_horaire_collecteur(collecteur, tmp_path):
    sc = collecteur.should_collect
    # samedi 2026-08-22 : week-end
    assert sc(datetime(2026, 8, 22, 16, 0), tmp_path, "14:55")[0] is False
    # lundi 10:00 : avant la fenêtre
    assert sc(datetime(2026, 8, 24, 10, 0), tmp_path, "14:55")[0] is False
    # lundi 14:55 pile : fenêtre atteinte, snapshot absent -> GO
    ok, raison = sc(datetime(2026, 8, 24, 14, 55), tmp_path, "14:55")
    assert ok is True
    # lundi 19:00 (console démarrée tard) : RATTRAPAGE -> GO
    assert sc(datetime(2026, 8, 24, 19, 0), tmp_path, "14:55")[0] is True
    # snapshot canonique déjà là -> no-op
    (tmp_path / "SPY_gex_2026-08-24.csv").write_text("x", encoding="utf-8")
    ok, raison = sc(datetime(2026, 8, 24, 16, 0), tmp_path, "14:55")
    assert ok is False and "déjà présent" in raison


# == LANCEMENT claude: (CLI mocké — contrat STDIN, aucun token) ================
def test_launch_claude_nourrit_le_prompt_par_stdin(usine, tmp_path, monkeypatch):
    _ticket(tmp_path, "TCK-040", "cc-app", "open")
    FauxPopen.instances.clear()
    monkeypatch.setattr(usine.subprocess, "Popen", FauxPopen)
    usine.launch("cc_app_queue")
    assert len(FauxPopen.instances) == 1
    fake = FauxPopen.instances[0]
    assert fake.cmd[:2] == ["cmd", "/c"] and "-p" in fake.cmd
    assert not any("TCK-040" in tok for tok in fake.cmd)   # rien dans l'argv
    # le prompt arrive par STDIN (thread) — on attend la fermeture du pipe
    fin = time.time() + 2
    while not fake.stdin.closed and time.time() < fin:
        time.sleep(0.02)
    assert fake.stdin.closed
    assert "TCK-040" in fake.stdin.data
    assert "status: answered" in fake.stdin.data           # consigne de clôture
    # environnement purgé R4
    assert all(k not in fake.kw.get("env", {}) for k in usine.R4_FORBIDDEN_ENV)
    # la tentative a été notée AVANT le paiement : pas de rejeu immédiat
    assert usine.guard_cc_app_queue() is None


def test_launch_claude_sans_matiere_aucun_processus(usine, tmp_path, monkeypatch, capsys):
    (tmp_path / "tickets").mkdir(exist_ok=True)     # file vide
    def _interdit(*a, **k):
        pytest.fail("aucun processus ne doit partir sans matière")
    monkeypatch.setattr(usine.subprocess, "Popen", _interdit)
    usine.launch("cc_app_queue")
    out = capsys.readouterr().out
    assert "pas de matière" in out
    assert "cc_app_queue" in usine._last_run        # calé sur la cadence


def test_launch_py_fichier_introuvable_alerte(usine, capsys):
    usine.launch("collecte")                        # outil/run.py absent du tmp
    out = capsys.readouterr().out
    assert "INTROUVABLE" in out
    assert "collecte" not in usine._running


# == DRY-RUN (la sonde de validation — rien ne part) ===========================
def test_dry_run_once_ne_lance_rien(usine, tmp_path, monkeypatch, capsys):
    # fichier py présent pour que le worker 'collecte' passe le garde-fou
    f = tmp_path / "outil" / "run.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("", encoding="utf-8")
    _ticket(tmp_path, "TCK-050", "cc-app", "open")
    (tmp_path / "panel.txt").write_text(
        "collecte = on\ncc_app_queue = on\nlibre = on\n", encoding="utf-8")

    def _interdit(*a, **k):
        pytest.fail("dry-run : aucun processus ne doit partir")
    monkeypatch.setattr(usine.subprocess, "Popen", _interdit)

    assert usine.run(dry=True, once=True) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN [collecte]" in out
    assert "DRY-RUN [cc_app_queue]" in out          # matière -> montré, pas lancé
    assert "DRY-RUN [libre]" in out                 # prompt littéral (forme prototype)
    assert "[DRY-RUN]" in out                       # bannière
    # le dry-run n'a PAS consommé la matière (pas de tentative notée)
    assert usine.guard_cc_app_queue() is not None


# == REGISTRE DES STRATÉGIES ===================================================
def test_scan_strategies(usine, tmp_path):
    d = tmp_path / "strategies" / "S099_test"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.yaml").write_text(
        "strategy_id: S099\nname: test_strat\nmagic: 130099\n"
        "status: RESEARCH   # commentaire\n", encoding="utf-8")
    reg = usine.scan_strategies()
    assert len(reg) == 1
    assert reg[0]["id"] == "S099"
    assert reg[0]["status"] == "RESEARCH"
    assert reg[0]["magic"] == "130099"

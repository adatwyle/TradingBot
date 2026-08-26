"""
Tests du notifier Telegram — synthétiques, tmp_path, AUCUN réseau.

POURQUOI ce banc : le notifier est le seul worker qui parle à l'extérieur.
On vérifie donc le TEXTE qui partirait (stub d'envoi en mémoire) et le
contrat d'état — les curseurs n'avancent QU'APRÈS un envoi réussi, deux
ticks sans nouveauté ne produisent rien, un journal reconstruit ne déclenche
pas de rafale. Le module vit dans un fichier à tiret : import par chemin.

    pytest orchestrator/test_robinbot_notify.py -q
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import pathlib
from datetime import datetime

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "robinbot_notify", _HERE / "robinbot-notify.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# == JOURNAUX SYNTHÉTIQUES (schémas réels 16 et 18 colonnes) ===================
GOLD_COLS = ["measured_at_utc", "event", "trade_id", "bar_time", "side",
             "entry_price", "stop_price", "target_price", "size_lots",
             "risk_ccy", "exit_price", "exit_reason", "pnl_r", "pnl_ccy",
             "capital_after", "chain"]

S13_COLS = ["measured_at_utc", "event", "arm", "symbol", "trade_id",
            "bar_time", "side", "entry_price", "stop_price", "target_price",
            "size_lots", "risk_ccy", "exit_price", "exit_reason", "pnl_r",
            "pnl_ccy", "capital_after", "chain"]

# Heures de référence : un LUNDI et un VENDREDI (garantis par test_calendrier).
LUNDI_MIDI = datetime(2026, 8, 17, 12, 0)
LUNDI_2005 = datetime(2026, 8, 17, 20, 5)
MARDI_2001 = datetime(2026, 8, 18, 20, 1)
VENDREDI_2005 = datetime(2026, 8, 21, 20, 5)


def _csv_row(cols: list[str], row: dict) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow([row.get(c, "") for c in cols])
    return buf.getvalue()


def write_journal(path: pathlib.Path, cols: list[str], rows=()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(_csv_row(cols, r))


def append_rows(path: pathlib.Path, cols: list[str], rows) -> None:
    with open(path, "a", encoding="utf-8", newline="") as f:
        for r in rows:
            f.write(_csv_row(cols, r))


def gold_open(**kw) -> dict:
    base = {"measured_at_utc": "2026-08-17T10:00:00Z", "event": "OPEN",
            "trade_id": "LONG_20260817", "bar_time": "2026-08-17T09:00:00",
            "side": "LONG", "entry_price": "3311.45000",
            "stop_price": "3301.00000", "target_price": "3332.00000",
            "size_lots": "0.0900", "risk_ccy": "100.00",
            "capital_after": "10000.00", "chain": "x"}
    base.update(kw)
    return base


def gold_close(**kw) -> dict:
    base = {"measured_at_utc": "2026-08-17T11:00:00Z", "event": "CLOSE",
            "trade_id": "LONG_20260817", "bar_time": "2026-08-17T10:00:00",
            "side": "LONG", "entry_price": "3311.45000",
            "stop_price": "3301.00000", "target_price": "3332.00000",
            "size_lots": "0.0900", "risk_ccy": "100.00",
            "exit_price": "3301.00000", "exit_reason": "SL",
            "pnl_r": "-1.0000", "pnl_ccy": "-100.00",
            "capital_after": "9900.00", "chain": "x"}
    base.update(kw)
    return base


def s13_open(**kw) -> dict:
    base = {"measured_at_utc": "2026-08-17T10:00:00Z", "event": "OPEN",
            "arm": "PRIMARY", "symbol": "AUDCAD",
            "trade_id": "AUDCAD_SHORT_20260817",
            "bar_time": "2026-08-17T00:00:00", "side": "SHORT",
            "entry_price": "0.89123", "stop_price": "0.89623",
            "target_price": "", "size_lots": "0.2000", "risk_ccy": "100.00",
            "capital_after": "10000.00", "chain": "x"}
    base.update(kw)
    return base


def s13_close(**kw) -> dict:
    base = {"measured_at_utc": "2026-08-17T11:00:00Z", "event": "CLOSE",
            "arm": "PRIMARY", "symbol": "AUDCAD",
            "trade_id": "AUDCAD_SHORT_20260817",
            "bar_time": "2026-08-17T00:00:00", "side": "SHORT",
            "entry_price": "0.89123", "stop_price": "0.89623",
            "target_price": "", "size_lots": "0.2000", "risk_ccy": "100.00",
            "exit_price": "0.88523", "exit_reason": "TP",
            "pnl_r": "+0.8000", "pnl_ccy": "+80.00",
            "capital_after": "10080.00", "chain": "x"}
    base.update(kw)
    return base


# == L'USINE JETABLE ===========================================================
class SendStub:
    """Remplace send_telegram : capture le texte, échoue sur commande."""

    def __init__(self):
        self.ok = True
        self.sent: list[str] = []

    def __call__(self, token: str, chat_id: str, text: str) -> bool:
        if not self.ok:
            return False
        self.sent.append(text)
        return True


class Usine:
    def __init__(self, tmp: pathlib.Path, stub: SendStub):
        self.tmp = tmp
        self.stub = stub
        self.notifier = tmp / "notifier"
        self.panel = tmp / "robinbot-panel.txt"
        self.gold = tmp / "gold_forward" / "journal.csv"
        self.s13 = tmp / "s13_forward" / "journal.csv"
        self.gold_status = tmp / "gold_forward" / "status.json"
        self.s13_status = tmp / "s13_forward" / "status.json"

    @property
    def sent(self) -> list[str]:
        return self.stub.sent

    def state(self) -> dict:
        return json.loads((self.notifier / "state.json").read_text(encoding="utf-8"))


@pytest.fixture
def usine(tmp_path, monkeypatch) -> Usine:
    notifier = tmp_path / "notifier"
    notifier.mkdir()
    (notifier / "config.json").write_text(
        json.dumps({"chat_id": "111", "digest_hour_local": 20}),
        encoding="utf-8")
    envf = tmp_path / "telegram.env"
    envf.write_text("TELEGRAM_BOT_TOKEN=TEST-TOKEN\n", encoding="utf-8")
    panel = tmp_path / "robinbot-panel.txt"
    panel.write_text("gold_forward = on\nsupervision = on\n", encoding="utf-8")

    monkeypatch.setenv("ROBINBOT_NOTIFY_DIR", str(notifier))
    monkeypatch.setenv("ROBINBOT_TELEGRAM_ENV", str(envf))
    monkeypatch.setenv("RBF_PANEL", str(panel))
    monkeypatch.setenv("GOLD_FORWARD_DIR", str(tmp_path / "gold_forward"))
    monkeypatch.setenv("S13_FORWARD_DIR", str(tmp_path / "s13_forward"))
    monkeypatch.setenv("MACD_AI_PAPER_DIR", str(tmp_path / "macd_ai_paper"))
    monkeypatch.setenv("S14_SENTIMENT_DIR", str(tmp_path / "s14_sentiment"))

    stub = SendStub()
    monkeypatch.setattr(mod, "send_telegram", stub)
    return Usine(tmp_path, stub)


def test_calendrier_de_reference():
    """Les dates fixes des tests sont bien un lundi et un vendredi."""
    assert LUNDI_MIDI.weekday() == 0
    assert VENDREDI_2005.weekday() == 4


# == PREMIER PASSAGE ===========================================================
def test_premier_passage_seed_et_armement(usine):
    # Historique déjà présent : il ne doit JAMAIS partir en notification.
    write_journal(usine.gold, GOLD_COLS, [gold_open(), gold_close()])
    write_journal(usine.s13, S13_COLS)

    assert mod.tick(now_local=LUNDI_MIDI) == 0
    assert len(usine.sent) == 1
    assert "armé" in usine.sent[0]
    assert "2 études surveillées" in usine.sent[0]
    assert "📈" not in usine.sent[0] and "💰" not in usine.sent[0]

    # Curseurs posés à la fin : deuxième tick = zéro message (idempotence).
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    assert len(usine.sent) == 1
    assert usine.state()["cursors"]["gold_forward"]["lines"] == 2


# == OPEN / CLOSE — LES DEUX SCHÉMAS ===========================================
def test_open_close_gold_16_colonnes(usine):
    write_journal(usine.gold, GOLD_COLS)
    mod.tick(now_local=LUNDI_MIDI)                      # armement

    append_rows(usine.gold, GOLD_COLS, [gold_open()])
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    msg = usine.sent[-1]
    assert "📈 [gold_forward] OPEN XAUUSD LONG @ 3311.45000" in msg
    assert "(SL 3301.00000, TP 3332.00000)" in msg
    assert "bras" not in msg                            # pas de colonne arm

    append_rows(usine.gold, GOLD_COLS, [gold_close()])  # perte -1 R
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    msg = usine.sent[-1]
    assert "🔻 [gold_forward] CLOSE XAUUSD -1.00 R (-100 CHF) SL" in msg
    assert "capital 9900.00" in msg


def test_open_close_s13_18_colonnes(usine):
    write_journal(usine.s13, S13_COLS)
    mod.tick(now_local=LUNDI_MIDI)                      # armement

    append_rows(usine.s13, S13_COLS, [s13_open()])
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    msg = usine.sent[-1]
    assert "📈 [s13_forward] OPEN AUDCAD SHORT @ 0.89123" in msg
    assert "TP —" in msg                                # cible absente (ext-long)
    assert "bras PRIMARY" in msg

    append_rows(usine.s13, S13_COLS, [s13_close()])     # gain +0.8 R
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    msg = usine.sent[-1]
    assert "💰 [s13_forward] CLOSE AUDCAD +0.80 R (+80 CHF) TP" in msg
    assert "capital 10080.00" in msg
    # Le bras figure AUSSI au CLOSE : sur une étude multi-bras, savoir lequel
    # a encaissé est l'information utile.
    assert "bras PRIMARY" in msg


def test_shadow_open_prefixe(usine):
    write_journal(usine.s13, S13_COLS)
    mod.tick(now_local=LUNDI_MIDI)

    append_rows(usine.s13, S13_COLS, [s13_open(event="SHADOW_OPEN")])
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    assert "(shadow) OPEN AUDCAD" in usine.sent[-1]


# == REGROUPEMENT ==============================================================
def test_regroupement_un_seul_message(usine):
    write_journal(usine.gold, GOLD_COLS)
    write_journal(usine.s13, S13_COLS)
    mod.tick(now_local=LUNDI_MIDI)                      # armement
    n0 = len(usine.sent)

    append_rows(usine.gold, GOLD_COLS, [gold_open()])
    append_rows(usine.s13, S13_COLS, [s13_open()])
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    assert len(usine.sent) == n0 + 1                    # UN message, pas deux
    msg = usine.sent[-1]
    assert "[gold_forward]" in msg and "[s13_forward]" in msg
    assert "\n\n" in msg                                # sections séparées


# == ÉCHEC D'ENVOI : CURSEURS INCHANGÉS ========================================
def test_echec_envoi_curseur_inchange_puis_retentative(usine):
    write_journal(usine.gold, GOLD_COLS)
    mod.tick(now_local=LUNDI_MIDI)                      # armement
    cur0 = usine.state()["cursors"]["gold_forward"]

    append_rows(usine.gold, GOLD_COLS, [gold_open()])
    usine.stub.ok = False
    assert mod.tick(now_local=LUNDI_MIDI) == 2          # Telegram injoignable
    assert usine.state()["cursors"]["gold_forward"] == cur0   # rien perdu

    usine.stub.ok = True
    assert mod.tick(now_local=LUNDI_MIDI) == 0          # retentative naturelle
    assert "OPEN XAUUSD" in usine.sent[-1]
    assert usine.state()["cursors"]["gold_forward"]["lines"] == 1
    # EXACTEMENT une fois : ni perdu par l'échec, ni redit par la reprise.
    assert sum("OPEN XAUUSD" in m for m in usine.sent) == 1
    assert mod.tick(now_local=LUNDI_MIDI) == 0          # 3e tick : silence
    assert sum("OPEN XAUUSD" in m for m in usine.sent) == 1


def test_config_ou_token_absents_exit_2(usine, monkeypatch):
    (usine.notifier / "config.json").unlink()
    assert mod.tick(now_local=LUNDI_MIDI) == 2
    assert usine.sent == []

    (usine.notifier / "config.json").write_text(
        json.dumps({"chat_id": "111"}), encoding="utf-8")
    monkeypatch.setenv("ROBINBOT_TELEGRAM_ENV", str(usine.tmp / "absent.env"))
    assert mod.tick(now_local=LUNDI_MIDI) == 2
    assert usine.sent == []


# == DIGEST QUOTIDIEN (20 h) + SECTION SEMAINE LE VENDREDI =====================
def _statuts(usine: Usine) -> None:
    usine.gold_status.parent.mkdir(parents=True, exist_ok=True)
    usine.gold_status.write_text(json.dumps({
        "generated_at_utc": "2026-08-17T18:25:22Z", "n_closed_total": 3,
        "cum_r": 1.5, "capital": 10150.0, "open_position": None,
    }), encoding="utf-8")
    usine.s13_status.parent.mkdir(parents=True, exist_ok=True)
    usine.s13_status.write_text(json.dumps({
        "generated_at_utc": "2026-08-17T18:25:23Z",
        "arms": {
            "AUDCAD": {"arm": "PRIMARY", "n_closed_total": 1, "cum_r": 0.8,
                       "capital": 10080.0, "open_position": {"side": "SHORT"}},
            "EURJPY": {"arm": "OBSERVATION", "n_closed_total": 0, "cum_r": 0.0,
                       "capital": 10000.0, "open_position": None},
        },
    }), encoding="utf-8")


def test_digest_une_fois_par_jour(usine):
    write_journal(usine.gold, GOLD_COLS)
    _statuts(usine)
    mod.tick(now_local=LUNDI_MIDI)                      # armement (pas de digest)
    assert len(usine.sent) == 1

    # Avant 20 h : rien. Après : le digest, une seule fois.
    assert mod.tick(now_local=datetime(2026, 8, 17, 19, 59)) == 0
    assert len(usine.sent) == 1
    assert mod.tick(now_local=LUNDI_2005) == 0
    assert len(usine.sent) == 2
    digest = usine.sent[-1]
    assert "📊 RobinBot — digest du 17.08.2026" in digest
    assert "3 clos · +1.50 R · capital 10150.00 · flat" in digest
    assert "AUDCAD : 1 clos · +0.80 R · capital 10080.00 · position ouverte" in digest
    assert "EURJPY : 0 clos" in digest
    assert "macd_ai_paper : n/d" in digest              # status absent
    assert "s14_sentiment" not in digest                # étude pas en route
    assert "— Semaine —" not in digest                  # lundi : pas de bilan

    # Même soirée : pas de redéclenchement. Lendemain 20 h+ : nouveau digest.
    assert mod.tick(now_local=datetime(2026, 8, 17, 22, 30)) == 0
    assert len(usine.sent) == 2
    assert mod.tick(now_local=MARDI_2001) == 0
    assert len(usine.sent) == 3
    assert "digest du 18.08.2026" in usine.sent[-1]


def test_digest_trades_du_jour(usine):
    # Un CLOSE mesuré le jour même apparaît dans la section « Aujourd'hui ».
    write_journal(usine.gold, GOLD_COLS,
                  [gold_open(measured_at_utc="2026-08-17T09:00:00Z"),
                   gold_close(measured_at_utc="2026-08-17T11:00:00Z")])
    mod.tick(now_local=LUNDI_MIDI)                      # armement (seed, pas de notif)
    assert mod.tick(now_local=LUNDI_2005) == 0
    digest = usine.sent[-1]
    assert "Aujourd'hui :" in digest
    assert "gold_forward XAUUSD -1.00 R (SL)" in digest


def test_digest_vendredi_section_semaine(usine):
    # Deux CLOSE dans l'ISO-semaine (mercredi + vendredi), un OPEN sans effet.
    write_journal(usine.gold, GOLD_COLS, [
        gold_close(measured_at_utc="2026-08-19T11:00:00Z",
                   pnl_r="+1.5000", pnl_ccy="+150.00"),
        gold_close(measured_at_utc="2026-08-21T11:00:00Z",
                   pnl_r="-1.0000", pnl_ccy="-100.00"),
    ])
    mod.tick(now_local=datetime(2026, 8, 21, 12, 0))    # armement vendredi midi
    assert mod.tick(now_local=VENDREDI_2005) == 0
    digest = usine.sent[-1]
    assert "— Semaine —" in digest
    assert "gold_forward : 2 clos · +0.50 R · +50 CHF" in digest
    assert "Aujourd'hui :" in digest                    # le CLOSE du vendredi
    assert mod.tick(now_local=datetime(2026, 8, 21, 21, 0)) == 0
    assert len(usine.sent) == 2                         # un seul digest le vendredi


# == ROBUSTESSE ================================================================
def test_ligne_malformee_ignoree_sans_crash(usine):
    write_journal(usine.gold, GOLD_COLS)
    mod.tick(now_local=LUNDI_MIDI)                      # armement
    n0 = len(usine.sent)

    with open(usine.gold, "a", encoding="utf-8", newline="") as f:
        f.write("n'importe,quoi\n")                     # ligne difforme
    append_rows(usine.gold, GOLD_COLS, [gold_close(pnl_r="abc")])  # chiffre cassé
    assert mod.tick(now_local=LUNDI_MIDI) == 0          # pas de crash
    assert len(usine.sent) == n0                        # rien d'envoyable

    append_rows(usine.gold, GOLD_COLS, [gold_open()])   # la vie continue
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    assert len(usine.sent) == n0 + 1
    assert usine.sent[-1].count("OPEN") == 1


def test_autooff_detecte_une_seule_fois(usine):
    # Une ligne AUTO-OFF antérieure à l'armement = vieille nouvelle, silence.
    usine.panel.write_text(
        "gold_forward = off          # AUTO-OFF 2026-08-16 10:00:00 — "
        "sortie 3 — SCELLÉ VIOLÉ\ns13_forward = on\n", encoding="utf-8")
    write_journal(usine.gold, GOLD_COLS)
    mod.tick(now_local=LUNDI_MIDI)                      # armement
    assert "🚨" not in usine.sent[0]

    # Une NOUVELLE ligne AUTO-OFF déclenche, une seule fois.
    usine.panel.write_text(
        "gold_forward = off          # AUTO-OFF 2026-08-16 10:00:00 — "
        "sortie 3 — SCELLÉ VIOLÉ\n"
        "s13_forward = off          # AUTO-OFF 2026-08-17 11:00:00 — "
        "sortie 4 — JOURNAL ALTÉRÉ\n", encoding="utf-8")
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    msg = usine.sent[-1]
    assert "🚨 [s13_forward] AUTO-OFF" in msg and "JOURNAL ALTÉRÉ" in msg
    assert "SCELLÉ VIOLÉ" not in msg                    # l'ancienne se tait

    n = len(usine.sent)
    assert mod.tick(now_local=LUNDI_MIDI) == 0          # déjà vue : silence
    assert len(usine.sent) == n


def test_journal_tronque_reseed_sans_rafale(usine):
    write_journal(usine.gold, GOLD_COLS)
    mod.tick(now_local=LUNDI_MIDI)                      # armement
    append_rows(usine.gold, GOLD_COLS, [gold_open()])
    mod.tick(now_local=LUNDI_MIDI)                      # OPEN notifié
    n0 = len(usine.sent)

    write_journal(usine.gold, GOLD_COLS)                # reconstruit : en-tête seule
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    assert len(usine.sent) == n0                        # re-seed SILENCIEUX
    assert usine.state()["cursors"]["gold_forward"]["lines"] == 0

    append_rows(usine.gold, GOLD_COLS,
                [gold_open(trade_id="LONG_20260818",
                           entry_price="3400.00000")])
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    assert len(usine.sent) == n0 + 1                    # la nouveauté, elle, part
    assert "3400.00000" in usine.sent[-1]
    assert usine.sent[-1].count("OPEN") == 1            # pas l'historique


# == RÉGRESSIONS ISSUES DES REVIEWS (2026-08-17) ===============================

def test_token_jamais_dans_les_logs(monkeypatch, capsys):
    """Le repr des exceptions requests contient l'URL — donc le token. La
    factory redirigeant stderr vers un fichier, un simple {e!r} déposerait le
    token du bot dans un log à CHAQUE coupure réseau. On appelle donc le VRAI
    send_telegram (hors fixture, qui le remplace par un stub)."""
    def post_qui_echoue(*a, **kw):
        raise RuntimeError(
            "HTTPSConnectionPool: Max retries exceeded with url: "
            "/botTEST-TOKEN/sendMessage")

    monkeypatch.setattr(mod.requests, "post", post_qui_echoue)
    assert mod.send_telegram("TEST-TOKEN", "111", "coucou") is False

    sortie = capsys.readouterr()
    assert "TEST-TOKEN" not in (sortie.out + sortie.err)


def test_ligne_partielle_attendue_puis_notifiee_une_fois(usine):
    """Un journal surpris en cours d'écriture : la ligne sans `\n` final est
    ignorée ce tick-ci, puis notifiée UNE fois une fois complète."""
    write_journal(usine.gold, GOLD_COLS)
    mod.tick(now_local=LUNDI_MIDI)                      # armement
    n0 = len(usine.sent)

    ligne = _csv_row(GOLD_COLS, gold_open())
    with open(usine.gold, "a", encoding="utf-8", newline="") as f:
        f.write(ligne[:-20])                            # coupée, sans \n
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    assert len(usine.sent) == n0                        # rien ne part

    with open(usine.gold, "a", encoding="utf-8", newline="") as f:
        f.write(ligne[-20:])                            # l'écriture s'achève
    assert mod.tick(now_local=LUNDI_MIDI) == 0
    assert len(usine.sent) == n0 + 1
    assert "OPEN XAUUSD" in usine.sent[-1]
    assert mod.tick(now_local=LUNDI_MIDI) == 0          # et pas deux fois
    assert len(usine.sent) == n0 + 1


def test_armement_journal_illisible_ne_pose_aucun_etat(usine):
    """Journal présent mais illisible à l'armement : aucun état n'est posé,
    le tick suivant re-arme proprement. Un curseur manquant ferait partir
    tout l'historique en rafale. (Illisible simulé par un dossier au nom du
    journal — l'ouvrir lève OSError, comme un verrou antivirus.)"""
    usine.gold.parent.mkdir(parents=True, exist_ok=True)
    usine.gold.mkdir()

    mod.tick(now_local=LUNDI_MIDI)
    assert not (usine.notifier / "state.json").exists()   # aucun état posé
    assert usine.sent == []                               # pas d'armement bancal

    usine.gold.rmdir()                                    # le verrou se lève
    write_journal(usine.gold, GOLD_COLS, [gold_open()])
    assert mod.tick(now_local=LUNDI_MIDI) == 0            # re-armement propre
    assert usine.state()["cursors"]["gold_forward"]["lines"] == 1
    assert len(usine.sent) == 1                           # armement seul
    assert "armé" in usine.sent[0]                        # historique muet

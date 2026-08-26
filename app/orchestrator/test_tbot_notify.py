"""
Tests du notifier Telegram TradingBot — synthétiques, tmp_path, AUCUN réseau.

POURQUOI ce banc : le notifier est la voix sortante du canal T7. On vérifie
le TEXTE au caractère près (golden tests TG-T1 — la spec fixe les formats
exacts d'Adrian), le contrat de curseur (TG-T2 — n'avance qu'après envoi
réussi, close antidaté jamais perdu), le découpage 4000 (TG-T3), l'inertie
sans tokens (TG-T4) et l'anti-fuite du token (TG-T7). Le module vit dans un
fichier à tiret : import par chemin. Fuseau de reporting figé en UTC
(mod.LOCAL_TZ) : les golden sont déterministes sur tout poste.

    pytest app/orchestrator/test_tbot_notify.py -q
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timezone

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))                      # app/ -> core importable
from core.ledger import close_trade, open_trade, record_trade  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "tbot_notify", _HERE / "tbot-notify.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

TOKEN = "TOKEN-FIXTURE-123"

# Calendrier de référence (vérifié par test_calendrier_de_reference) :
# 26.08.2026 = mercredi (S35) · 28.08.2026 = vendredi S35 (lundi 24.08)
# 04.09.2026 = vendredi S36 (semaine à cheval : lundi 31.08) · 01.09 = mardi
MERCREDI_MIDI = datetime(2026, 8, 26, 12, 0)
MERCREDI_SOIR = datetime(2026, 8, 26, 22, 5)
VENDREDI_SOIR = datetime(2026, 8, 28, 22, 5)
VENDREDI_S36_SOIR = datetime(2026, 9, 4, 22, 5)
MARDI_1_SEPT_SOIR = datetime(2026, 9, 1, 22, 5)
LUNDI_28_DEC_MIDI = datetime(2026, 12, 28, 12, 0)
LUNDI_4_JAN_SOIR = datetime(2027, 1, 4, 22, 5)


def test_calendrier_de_reference():
    assert MERCREDI_MIDI.weekday() == 2
    assert VENDREDI_SOIR.weekday() == 4
    assert VENDREDI_SOIR.date().isocalendar()[1] == 35
    assert VENDREDI_S36_SOIR.weekday() == 4
    assert VENDREDI_S36_SOIR.date().isocalendar()[1] == 36
    assert LUNDI_4_JAN_SOIR.weekday() == 0            # pas de section semaine


# == L'USINE JETABLE ===========================================================
def seed_trade(db: str, *, close: str, net: float, reason: str = "SL",
               instance: str = "S001.CHF-USD", mode: str = "PAPER") -> int:
    """Un trade CLOS dans le ledger de test — net = gross (0 frais)."""
    return record_trade(
        db_path=db, strategy_id=instance.split(".")[0], instance_id=instance,
        strategy_version="1.0.0", magic_number=71001, mode=mode,
        symbol="CHFUSD", timeframe="H1", side="LONG", volume_lots=0.10,
        open_time=close, open_price=1.0, stop_price=0.99,
        close_time=close, close_price=1.0, exit_reason=reason, gross_pnl=net)


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
        self.db = str(tmp / "ledger.db")
        self.panel = tmp / "tbot-panel.txt"

    @property
    def sent(self) -> list[str]:
        return self.stub.sent

    def state(self) -> dict:
        return json.loads((self.notifier / "state.json").read_text(encoding="utf-8"))

    def config(self, **extra) -> None:
        cfg = {"chat_id": 111, "digest_hour": 22, "live_lines": True}
        cfg.update(extra)
        (self.notifier / "config.json").write_text(json.dumps(cfg),
                                                   encoding="utf-8")


@pytest.fixture
def usine(tmp_path, monkeypatch) -> Usine:
    notifier = tmp_path / "notifier"
    notifier.mkdir()
    (notifier / "token.txt").write_text(TOKEN + "\n", encoding="utf-8")

    monkeypatch.setenv("ROBINBOT_NOTIFY_DIR", str(notifier))
    monkeypatch.setenv("TBOT_LEDGER_DB", str(tmp_path / "ledger.db"))
    monkeypatch.setenv("TBF_PANEL", str(tmp_path / "tbot-panel.txt"))
    for env in ("GOLD_FORWARD_DIR", "S13_FORWARD_DIR",
                "MACD_AI_PAPER_DIR", "S14_SENTIMENT_DIR"):
        monkeypatch.setenv(env, str(tmp_path / env.lower()))
    # Fuseau de reporting figé : golden déterministes sur tout poste.
    monkeypatch.setattr(mod, "LOCAL_TZ", timezone.utc)

    stub = SendStub()
    monkeypatch.setattr(mod, "send_telegram", stub)
    u = Usine(tmp_path, stub)
    u.config()
    return u


# == PREMIER PASSAGE (prospectif) ==============================================
def test_premier_passage_armement_prospectif(usine):
    """L'historique du ledger ne part JAMAIS en notification : le curseur se
    pose sur le dernier trade clos existant."""
    seed_trade(usine.db, close="2026-08-25T10:00:00Z", net=-100.0)
    tid = seed_trade(usine.db, close="2026-08-25T11:00:00Z", net=50.0, reason="TP")

    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert len(usine.sent) == 1
    assert "armé" in usine.sent[0]
    assert "chf" not in usine.sent[0]                   # aucune ligne de trade

    st = usine.state()
    assert st["trade_cursor"] == {"close_time": "2026-08-25T11:00:00Z", "id": tid}
    # Idempotence : deuxième tick sans nouveauté = zéro message.
    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert len(usine.sent) == 1


# == TG-3 : LIGNE DE TRADE LIVE (golden) =======================================
def test_lignes_live_format_exact(usine):
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # armement, ledger vide
    seed_trade(usine.db, close="2026-08-26T10:53:00Z", net=-100.0, reason="SL")
    seed_trade(usine.db, close="2026-08-26T22:05:00Z", net=210.0, reason="TP")

    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert usine.sent[-1] == ("10:53 S001.CHF-USD SL -100chf\n"
                              "22:05 S001.CHF-USD TP +210chf")


def test_backtest_jamais_notifie(usine):
    """TG-2 : le backtest n'est pas de l'activité du jour."""
    mod.tick(now_local=MERCREDI_MIDI)
    seed_trade(usine.db, close="2026-08-26T10:00:00Z", net=999.0,
               mode="BACKTEST")
    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert len(usine.sent) == 1                         # armement seul


def test_arrondi_chf_entier_signe():
    """D-TG-5 : CHF entier, signé, suffixe collé — half away from zero,
    jamais de -0chf."""
    assert mod.chf(-100.0) == "-100chf"
    assert mod.chf(210.0) == "+210chf"
    assert mod.chf(210.5) == "+211chf"
    assert mod.chf(210.4) == "+210chf"
    assert mod.chf(-99.5) == "-100chf"
    assert mod.chf(-0.4) == "+0chf"
    assert mod.chf(0.0) == "+0chf"


# == TG-4 : RÉCAP QUOTIDIEN (golden) ===========================================
def test_recap_quotidien_golden(usine):
    seed_trade(usine.db, close="2026-08-26T10:53:00Z", net=-100.0, reason="SL")
    seed_trade(usine.db, close="2026-08-26T22:05:00Z", net=210.0, reason="TP")
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # armement (curseur à la fin)

    assert mod.tick(now_local=MERCREDI_SOIR) == 0
    assert usine.sent[-1] == ("📒 TradingBot — 26.08.2026\n"
                              "10:53 S001.CHF-USD SL -100chf\n"
                              "22:05 S001.CHF-USD TP +210chf\n"
                              "Total jour : +110chf")

    # Une fois par jour : re-tick le même soir = rien de neuf.
    n = len(usine.sent)
    assert mod.tick(now_local=datetime(2026, 8, 26, 23, 0)) == 0
    assert len(usine.sent) == n


def test_recap_jour_sans_trade_golden(usine):
    """Le silence total est indistinguable d'une panne — on le dit."""
    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert mod.tick(now_local=MERCREDI_SOIR) == 0
    assert usine.sent[-1] == ("📒 TradingBot — 26.08.2026\n"
                              "Aucun trade aujourd'hui.")


def test_avant_l_heure_du_digest_rien(usine):
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # armement
    assert mod.tick(now_local=datetime(2026, 8, 26, 21, 59)) == 0
    assert len(usine.sent) == 1                         # pas encore l'heure


# == TG-5 : SECTION HEBDO DU VENDREDI (golden) =================================
def test_recap_hebdo_vendredi_golden(usine):
    seed_trade(usine.db, close="2026-08-24T09:00:00Z", net=110.0, reason="TP")
    seed_trade(usine.db, close="2026-08-25T09:00:00Z", net=-40.0, reason="SL")
    seed_trade(usine.db, close="2026-08-27T09:00:00Z", net=75.0, reason="TP")
    seed_trade(usine.db, close="2026-08-28T10:00:00Z", net=-25.0, reason="SL")
    assert mod.tick(now_local=datetime(2026, 8, 28, 12, 0)) == 0    # armement

    assert mod.tick(now_local=VENDREDI_SOIR) == 0
    assert usine.sent[-1] == (
        "📒 TradingBot — 28.08.2026\n"
        "10:00 S001.CHF-USD SL -25chf\n"
        "Total jour : -25chf"
        "\n\n"
        "— Semaine 35 (24.08–28.08) —\n"
        "Lu +110chf\n"
        "Ma -40chf\n"
        "Me +0chf\n"
        "Je +75chf\n"
        "Ve -25chf\n"
        "Total semaine : +120chf")


def test_semaine_a_cheval_sur_deux_mois_golden(usine):
    """S36 2026 : lundi 31.08 → vendredi 04.09 — les deux mois s'agrègent."""
    seed_trade(usine.db, close="2026-08-31T09:00:00Z", net=50.0, reason="TP")
    seed_trade(usine.db, close="2026-09-04T10:00:00Z", net=-20.0, reason="SL")
    assert mod.tick(now_local=datetime(2026, 9, 4, 12, 0)) == 0     # armement
    # (armé le 04.09 : le marqueur mensuel se pose sur août — pas de récap
    # mensuel rétroactif à l'armement, seul le duo quotidien+hebdo part.)

    assert mod.tick(now_local=VENDREDI_S36_SOIR) == 0
    assert usine.sent[-1] == (
        "📒 TradingBot — 04.09.2026\n"
        "10:00 S001.CHF-USD SL -20chf\n"
        "Total jour : -20chf"
        "\n\n"
        "— Semaine 36 (31.08–04.09) —\n"
        "Lu +50chf\n"
        "Ma +0chf\n"
        "Me +0chf\n"
        "Je +0chf\n"
        "Ve -20chf\n"
        "Total semaine : +30chf")


# == TG-6 : RÉCAP MENSUEL + RÉTROSPECTIVE 12 MOIS (golden) =====================
def test_recap_mensuel_golden(usine):
    seed_trade(usine.db, close="2025-09-15T10:00:00Z", net=130.0, reason="TP")
    seed_trade(usine.db, close="2026-08-04T10:00:00Z", net=210.0, reason="TP")
    seed_trade(usine.db, close="2026-08-11T10:00:00Z", net=-80.0, reason="SL")
    seed_trade(usine.db, close="2026-08-18T10:00:00Z", net=45.0, reason="TP")
    seed_trade(usine.db, close="2026-08-25T10:00:00Z", net=120.0, reason="TP")
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # armement le 26.08

    # Premier créneau quotidien de septembre (D-TG-4) : mensuel d'août.
    assert mod.tick(now_local=MARDI_1_SEPT_SOIR) == 0
    assert usine.sent[-1] == (
        "📒 TradingBot — 01.09.2026\n"
        "Aucun trade aujourd'hui."
        "\n\n"
        "📒 Mois d'août 2026\n"
        "S32 +210chf\n"
        "S33 -80chf\n"
        "S34 +45chf\n"
        "S35 +120chf\n"
        "Total mois : +295chf\n"
        "\n"
        "— 12 derniers mois —\n"
        "09.2025 +130chf\n"
        "10.2025 +0chf\n"
        "11.2025 +0chf\n"
        "12.2025 +0chf\n"
        "01.2026 +0chf\n"
        "02.2026 +0chf\n"
        "03.2026 +0chf\n"
        "04.2026 +0chf\n"
        "05.2026 +0chf\n"
        "06.2026 +0chf\n"
        "07.2026 +0chf\n"
        "08.2026 +295chf")

    # Le mensuel ne part qu'une fois : digest du 2 septembre sans lui.
    assert mod.tick(now_local=datetime(2026, 9, 2, 22, 5)) == 0
    assert "Mois d'août" not in usine.sent[-1]


# == TG-7 : RÉCAP ANNUEL (golden) ==============================================
def test_recap_annuel_golden(usine):
    seed_trade(usine.db, close="2026-01-15T10:00:00Z", net=85.0, reason="TP")
    seed_trade(usine.db, close="2026-12-10T10:00:00Z", net=-30.0, reason="SL")
    assert mod.tick(now_local=LUNDI_28_DEC_MIDI) == 0   # armement fin décembre

    # Premier créneau de janvier : mensuel de décembre + annuel 2026.
    assert mod.tick(now_local=LUNDI_4_JAN_SOIR) == 0
    msg = usine.sent[-1]
    assert msg.startswith("📒 TradingBot — 04.01.2027\n"
                          "Aucun trade aujourd'hui.")
    assert "📒 Mois de décembre 2026" in msg            # liaison « de »
    assert "Total mois : -30chf" in msg
    assert msg.endswith(
        "📒 Année 2026\n"
        "01 +85chf\n"
        "02 +0chf\n"
        "03 +0chf\n"
        "04 +0chf\n"
        "05 +0chf\n"
        "06 +0chf\n"
        "07 +0chf\n"
        "08 +0chf\n"
        "09 +0chf\n"
        "10 +0chf\n"
        "11 +0chf\n"
        "12 -30chf\n"
        "Total année : +55chf")


# == TG-T2 : LE CURSEUR DES TRADES =============================================
def test_curseur_n_avance_pas_sur_echec_d_envoi(usine):
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # armement
    tid = seed_trade(usine.db, close="2026-08-26T10:53:00Z", net=-100.0)

    usine.stub.ok = False
    assert mod.tick(now_local=MERCREDI_MIDI) == 2       # envoi en échec
    assert usine.state()["trade_cursor"] is None        # rien n'a bougé

    usine.stub.ok = True
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # retenté, même ligne
    assert usine.sent[-1] == "10:53 S001.CHF-USD SL -100chf"
    assert usine.state()["trade_cursor"] == {
        "close_time": "2026-08-26T10:53:00Z", "id": tid}


def test_close_antidate_jamais_perdu(usine):
    """D-TG-6 : le close est un UPDATE — un trade ouvert TÔT (petit id) qui
    clôt APRÈS un trade au grand id serait perdu par un curseur en id ; le
    tuple (close_time, id) le rattrape."""
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # armement
    early_id = open_trade(
        db_path=usine.db, strategy_id="S001", instance_id="S001.CHF-USD",
        strategy_version="1.0.0", magic_number=71001, mode="PAPER",
        symbol="CHFUSD", timeframe="H1", side="LONG", volume_lots=0.10,
        open_time="2026-08-26T08:00:00Z", open_price=1.0, stop_price=0.99)
    late_id = seed_trade(usine.db, close="2026-08-26T10:00:00Z", net=50.0,
                         reason="TP")
    assert late_id > early_id

    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert usine.sent[-1] == "10:00 S001.CHF-USD TP +50chf"
    assert usine.state()["trade_cursor"]["id"] == late_id

    # Le trade au PETIT id clôt maintenant, après coup :
    close_trade(early_id, db_path=usine.db, close_time="2026-08-26T10:30:00Z",
                close_price=1.0, exit_reason="TRAIL", gross_pnl=33.0)
    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert usine.sent[-1] == "10:30 S001.CHF-USD TRAIL +33chf"
    assert usine.state()["trade_cursor"] == {
        "close_time": "2026-08-26T10:30:00Z", "id": early_id}


def test_live_lines_off_curseur_avance_recap_reprend(usine):
    """D-TG-2 : live_lines=false — pas de ligne immédiate, mais le trade
    reste marqué vu ET figure au récap du soir (le filet)."""
    usine.config(live_lines=False)
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # armement
    tid = seed_trade(usine.db, close="2026-08-26T10:53:00Z", net=-100.0)

    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert len(usine.sent) == 1                         # aucune ligne live
    assert usine.state()["trade_cursor"]["id"] == tid   # mais vu

    assert mod.tick(now_local=MERCREDI_SOIR) == 0
    assert "10:53 S001.CHF-USD SL -100chf" in usine.sent[-1]


# == TG-T3 : DÉCOUPAGE 4000 SUR FRONTIÈRE DE LIGNE =============================
def test_split_message_frontiere_de_ligne():
    lignes = [f"ligne {i:04d} " + "x" * 90 for i in range(80)]   # ~8 000 chars
    texte = "\n".join(lignes)
    morceaux = mod.split_message(texte, limit=4000)
    assert len(morceaux) >= 2
    assert all(len(m) <= 4000 for m in morceaux)
    assert "\n".join(morceaux) == texte                 # rien perdu, rien coupé
    originales = set(lignes)
    for m in morceaux:
        for l in m.split("\n"):
            assert l in originales                      # frontière de ligne


def test_send_telegram_decoupe_en_plusieurs_posts(monkeypatch):
    posts = []

    class Resp:
        ok = True
        status_code = 200

        @staticmethod
        def json():
            return {"ok": True}

    monkeypatch.setattr(mod.requests, "post",
                        lambda url, json=None, timeout=None:
                        posts.append(json) or Resp())
    texte = "\n".join("ligne " + "y" * 60 for _ in range(90))    # ~6 000 chars
    assert mod.send_telegram("T", "1", texte) is True
    assert len(posts) == 2
    assert all(len(p["text"]) <= 4000 for p in posts)


# == TG-T4 : INERTIE SANS TOKENS (TCK-007) =====================================
def test_inertie_dossier_vide_exit_2_sans_bruit(tmp_path, monkeypatch, capsys):
    ndir = tmp_path / "notifier"
    ndir.mkdir()
    monkeypatch.setenv("ROBINBOT_NOTIFY_DIR", str(ndir))
    monkeypatch.setenv("TBOT_LEDGER_DB", str(tmp_path / "ledger.db"))

    def aucun_reseau(*a, **k):
        raise AssertionError("aucun appel réseau ne doit sortir")

    monkeypatch.setattr(mod.requests, "post", aucun_reseau)
    assert mod.tick(now_local=MERCREDI_MIDI) == 2
    sortie = capsys.readouterr()
    assert sortie.out == "" and sortie.err == ""        # sans bruit (TG-1)
    assert not (ndir / "state.json").exists()


def test_inertie_config_sans_chat_id_exit_2(tmp_path, monkeypatch, capsys):
    ndir = tmp_path / "notifier"
    ndir.mkdir()
    (ndir / "token.txt").write_text(TOKEN, encoding="utf-8")
    (ndir / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ROBINBOT_NOTIFY_DIR", str(ndir))
    monkeypatch.setenv("TBOT_LEDGER_DB", str(tmp_path / "ledger.db"))
    assert mod.tick(now_local=MERCREDI_MIDI) == 2
    sortie = capsys.readouterr()
    assert sortie.out == "" and sortie.err == ""


def test_token_bom_tolere(tmp_path):
    p = tmp_path / "token.txt"
    p.write_bytes(b"\xef\xbb\xbf" + TOKEN.encode() + b"\n")
    assert mod.load_token(str(p)) == TOKEN


# == TG-T7 : LE TOKEN NE FUIT JAMAIS ===========================================
def test_token_jamais_dans_les_logs_sur_exception(monkeypatch, capsys):
    """Le repr des exceptions requests porte l'URL, donc le token — et la
    factory redirige stderr vers un fichier de log."""
    def post_qui_echoue(*a, **kw):
        raise RuntimeError("Max retries exceeded with url: "
                           f"/bot{TOKEN}/sendMessage")

    monkeypatch.setattr(mod.requests, "post", post_qui_echoue)
    assert mod.send_telegram(TOKEN, "1", "x") is False
    sortie = capsys.readouterr()
    assert TOKEN not in (sortie.out + sortie.err)


def test_token_masque_sur_refus_http(monkeypatch, capsys):
    class Resp:
        ok = False
        status_code = 401
        text = f"Unauthorized bot {TOKEN} rejected"

    monkeypatch.setattr(mod.requests, "post", lambda *a, **k: Resp())
    assert mod.send_telegram(TOKEN, "1", "x") is False
    sortie = capsys.readouterr()
    assert TOKEN not in (sortie.out + sortie.err)
    assert "<token>" in sortie.err


def test_le_state_ne_contient_jamais_le_token(usine):
    mod.tick(now_local=MERCREDI_MIDI)
    contenu = (usine.notifier / "state.json").read_text(encoding="utf-8")
    assert TOKEN not in contenu


# == TG-9 / TG-12 : ÉCHECS PROPRES =============================================
def test_envoi_en_echec_exit_2_et_message_retente(usine, capsys):
    usine.stub.ok = False
    assert mod.tick(now_local=MERCREDI_MIDI) == 2       # armement non remis
    assert not (usine.notifier / "state.json").exists()
    usine.stub.ok = True
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # ré-armé, état posé
    assert (usine.notifier / "state.json").exists()


def test_erreur_inattendue_exit_1(monkeypatch, capsys):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "tick", boom)
    assert mod.main() == 1
    assert "boom" in capsys.readouterr().err


# == TG-10 : SOURCES HÉRITÉES (panneau AUTO-OFF + journaux d'études) ===========
def test_autooff_alerte_une_seule_fois(usine):
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # armement
    usine.panel.write_text(
        "notify = on\n"
        "gold_forward = off          # AUTO-OFF 2026-08-26 12:00:00 — sortie 4\n",
        encoding="utf-8")
    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert "🚨 [gold_forward] AUTO-OFF" in usine.sent[-1]
    n = len(usine.sent)
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # même ligne : silence
    assert len(usine.sent) == n


def test_journal_d_etude_herite_notifie(usine, tmp_path):
    """La source « études scellées » reste branchée (E6) : un journal qui
    apparaît est surveillé, ses CLOSE partent — mécanique robinbot conservée."""
    gold = tmp_path / "gold_forward_dir" / "journal.csv"
    gold.parent.mkdir(parents=True)
    cols = ("measured_at_utc,event,trade_id,bar_time,side,entry_price,"
            "stop_price,target_price,size_lots,risk_ccy,exit_price,"
            "exit_reason,pnl_r,pnl_ccy,capital_after,chain")
    gold.write_text(cols + "\n", encoding="utf-8")
    assert mod.tick(now_local=MERCREDI_MIDI) == 0       # armement (curseur posé)

    with open(gold, "a", encoding="utf-8") as f:
        f.write("2026-08-26T11:00:00Z,CLOSE,T1,2026-08-26T10:00:00,LONG,"
                "3311.45,3301.00,3332.00,0.09,100.00,3301.00,SL,-1.0000,"
                "-100.00,9900.00,x\n")
    assert mod.tick(now_local=MERCREDI_MIDI) == 0
    assert "🔻 [gold_forward] CLOSE XAUUSD -1.00 R (-100 CHF) SL" in usine.sent[-1]

"""
Tests du RUNNER s14_sentiment — AUCUN réseau, AUCUN appel `claude` réel,
AUCUN chargement FinBERT réel, AUCUN accès à C:\\db (tout passe par `tmp_path`).

La collecte, le juge et le témoin sont des SEAMS injectés : `run_pass` les
reçoit en paramètres, exactement comme le vrai passage reçoit Finnhub, le CLI
et le modèle local. Ce qui est testé ici est donc l'ORCHESTRATION du passage —
ordre collecte/jugement, contrat de sortie, curseurs, `na`, judges.txt,
idempotence — la mécanique du journal étant déjà couverte par
`test_sentiment_step.py`.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core import secrets                                    # noqa: E402
from studies.s14_sentiment import ai_judge as aj              # noqa: E402
from studies.s14_sentiment import finbert_witness as fw       # noqa: E402
from studies.s14_sentiment import report_sentiment as rep     # noqa: E402
from studies.s14_sentiment import run_sentiment as rs         # noqa: E402
from studies.s14_sentiment import sentiment_step as ss        # noqa: E402

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
UNIVERSE = ["AUDCHF", "EURUSD", "AUDCAD", "EURJPY", "XAUUSD"]
CLAUDE, FINBERT = "claude-cli", "finbert"


# ─────────────────────────────────────────────────────────────────────────────
# Outils
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def params():
    return ss.load_sealed_params(ss.PARAMS_PATH, ss.PARAMS_SHA256)


@pytest.fixture
def paths(tmp_path):
    return ss.Paths(str(tmp_path))


def _item(nid, hours_old=1.0, headline=None, source="Reuters"):
    published = NOW - timedelta(hours=hours_old)
    return {"id": nid, "datetime": int(published.timestamp()),
            "headline": headline or f"Dollar firms after data ({nid})",
            "source": source}


def collector(items, err=""):
    """Une collecte injectée : rend toujours les mêmes items (ou l'erreur)."""
    def collect(paths, params):
        return list(items), err
    return collect


def judge_ok(sentiment="positive", confidence=0.9, reason="raison courte"):
    """Un juge injecté qui répond, et qui note les lots qu'il a vus."""
    def fn(batch):
        fn.last_error = ""
        fn.seen.append([b["news_id"] for b in batch])
        return {"verdicts": [{"symbol": s, "sentiment": sentiment,
                              "confidence": confidence, "reason": reason}
                             for s in UNIVERSE]}
    fn.last_error = ""
    fn.seen = []
    return fn


def judge_down(cause="timeout"):
    """Un juge en panne : None après relance, cause courte exposée."""
    def fn(batch):
        fn.last_error = cause
        fn.seen.append([b["news_id"] for b in batch])
        return None
    fn.last_error = ""
    fn.seen = []
    return fn


def rows_of(paths, event=None):
    rows = ss.read_journal(paths.journal)
    return [r for r in rows if event is None or r["event"] == event]


def journal_bytes(paths):
    with open(paths.journal, "rb") as f:
        return f.read()


def seal(paths, params, now=NOW - timedelta(hours=3)):
    """Premier passage : collecte vide mais RÉUSSIE -> le scellé est posé."""
    code = rs.run_pass(paths, params, collect=collector([]), judges=[], now=now)
    assert code == 0
    return code


# ─────────────────────────────────────────────────────────────────────────────
# Le passage complet
# ─────────────────────────────────────────────────────────────────────────────

def test_passage_complet_collecte_puis_deux_juges(paths, params):
    seal(paths, params)
    jc, jf = judge_ok("positive", 0.91), judge_ok("neutral", 0.62)

    code = rs.run_pass(paths, params, collect=collector([_item(1), _item(2),
                                                         _item(3)]),
                       judges=[(CLAUDE, jc), (FINBERT, jf)], now=NOW)

    assert code == 0
    assert len(rows_of(paths, "NEWS")) == 3
    verdicts = rows_of(paths, "VERDICT")
    assert len(verdicts) == 10                      # 5 instruments x 2 juges
    assert {v["judge"] for v in verdicts} == {CLAUDE, FINBERT}
    for name in (CLAUDE, FINBERT):
        par_juge = [v for v in verdicts if v["judge"] == name]
        assert {v["symbol"] for v in par_juge} == set(UNIVERSE)
        assert all(v["news_id"] == "1..3" for v in par_juge)   # plage du lot
    # Les deux juges ont vu le MÊME lot, chacun par son curseur.
    assert jc.seen == [["1", "2", "3"]] == jf.seen
    # Le journal reste vérifiable de bout en bout, et l'état à jour.
    state = ss.load_state(paths.state)
    ss.verify_journal(paths.journal, state)
    assert state["judges"][CLAUDE]["cursor"] == 3
    assert state["judges"][FINBERT]["cursor"] == 3
    assert json.load(open(paths.status, encoding="utf-8"))["n_news_total"] == 3


def test_idempotence_second_passage_sans_news(paths, params):
    seal(paths, params)
    items = [_item(1), _item(2)]
    rs.run_pass(paths, params, collect=collector(items),
                judges=[(CLAUDE, judge_ok()), (FINBERT, judge_ok())], now=NOW)
    avant = journal_bytes(paths)

    jc, jf = judge_ok(), judge_ok()
    code = rs.run_pass(paths, params, collect=collector(items),
                       judges=[(CLAUDE, jc), (FINBERT, jf)], now=NOW)

    assert code == 0
    assert journal_bytes(paths) == avant           # zéro octet ajouté
    assert jc.seen == [] and jf.seen == []         # juges jamais rappelés


# ─────────────────────────────────────────────────────────────────────────────
# Contrat de sortie — collecte
# ─────────────────────────────────────────────────────────────────────────────

def test_cle_absente_exit_2_et_aucune_ecriture(paths, params, tmp_path,
                                               monkeypatch, capsys):
    # ISOLATION OBLIGATOIRE du coffre partagé : sans elle, ce test cesserait
    # de tester quoi que ce soit le jour où une vraie clé est déposée dans
    # C:\db\tbot\secrets\ — il la trouverait et le passage ne rendrait plus 2.
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.setenv("TBOT_SECRETS_DIR", str(tmp_path / "coffre_vide"))
    importlib.reload(secrets)

    code = rs.run_pass(paths, params, judges=[(CLAUDE, judge_ok())], now=NOW)

    assert code == 2
    # Rien : pas de journal, pas d'état, pas de status, pas même le dossier
    # peuplé — le scellé ne se pose JAMAIS sur une collecte en panne.
    assert os.listdir(tmp_path) == []
    err = capsys.readouterr().err
    # Le message indique l'emplacement PARTAGÉ : la clé appartient au compte,
    # pas à l'étude — d'autres stratégies consommeront la même.
    assert str(secrets.secret_path("finnhub")) in err
    assert "FINNHUB_API_KEY" in err
    monkeypatch.undo()
    importlib.reload(secrets)


def test_finnhub_en_panne_mais_backlog_jugeable(paths, params):
    """§ 7 : la panne de collecte n'empêche PAS le jugement du passage — et
    le passage rend quand même 2, car le 2 qualifie la collecte."""
    seal(paths, params)
    # Passage où les deux juges sont coupés : les news entrent, rien n'est jugé.
    with open(paths.judges, "w", encoding="utf-8") as f:
        f.write("claude-cli = off\nfinbert = off\n")
    rs.run_pass(paths, params, collect=collector([_item(1), _item(2)]),
                judges=[(CLAUDE, judge_ok()), (FINBERT, judge_ok())], now=NOW)
    assert rows_of(paths, "VERDICT") == []
    os.remove(paths.judges)

    jc, jf = judge_ok(), judge_ok()
    code = rs.run_pass(paths, params,
                       collect=collector([], "Finnhub injoignable : timeout"),
                       judges=[(CLAUDE, jc), (FINBERT, jf)], now=NOW)

    assert code == 2                                # la collecte est aveugle
    assert jc.seen == [["1", "2"]] and jf.seen == [["1", "2"]]
    assert len(rows_of(paths, "VERDICT")) == 10     # le jugement a bien eu lieu
    ss.verify_journal(paths.journal, ss.load_state(paths.state))


def test_collecte_en_panne_avant_tout_scelle_ne_cree_rien(paths, params,
                                                          tmp_path):
    code = rs.run_pass(paths, params, collect=collector([], "Finnhub HTTP 500"),
                       judges=[(CLAUDE, judge_ok())], now=NOW)
    assert code == 2
    assert os.listdir(tmp_path) == []
    assert ss.load_state(paths.state) is None       # `started_at` non figé


# ─────────────────────────────────────────────────────────────────────────────
# Contrat de sortie — pannes de juge, scellé, journal
# ─────────────────────────────────────────────────────────────────────────────

def test_juge_claude_en_panne_na_et_temoin_juge_quand_meme(paths, params):
    seal(paths, params)
    jc, jf = judge_down("timeout"), judge_ok("negative", 0.85)

    code = rs.run_pass(paths, params, collect=collector([_item(1)]),
                       judges=[(CLAUDE, jc), (FINBERT, jf)], now=NOW)

    assert code == 0                                # un juge muet n'est pas
    verdicts = rows_of(paths, "VERDICT")            # une panne d'étude
    na = [v for v in verdicts if v["judge"] == CLAUDE]
    assert len(na) == 5 and all(v["sentiment"] == "na" for v in na)
    assert all(v["confidence"] == "" for v in na)
    assert all(v["reason"] == "timeout" for v in na)   # la cause, pas la prose
    temoin = [v for v in verdicts if v["judge"] == FINBERT]
    assert len(temoin) == 5
    assert all(v["sentiment"] == "negative" for v in temoin)
    # Le lot est CONSOMMÉ des deux côtés : on ne rejuge jamais.
    state = ss.load_state(paths.state)
    assert state["judges"][CLAUDE]["cursor"] == 1
    assert state["judges"][FINBERT]["cursor"] == 1


def test_judges_txt_coupe_claude_seul_finbert_produit(paths, params):
    seal(paths, params)
    with open(paths.judges, "w", encoding="utf-8") as f:
        f.write("claude-cli = off   # il brûle des tokens\n")
    jc, jf = judge_ok(), judge_ok("positive", 0.88)

    code = rs.run_pass(paths, params, collect=collector([_item(1)]),
                       judges=[(CLAUDE, jc), (FINBERT, jf)], now=NOW)

    assert code == 0
    assert jc.seen == []                            # jamais appelé, zéro token
    verdicts = rows_of(paths, "VERDICT")
    assert len(verdicts) == 5
    assert {v["judge"] for v in verdicts} == {FINBERT}
    state = ss.load_state(paths.state)
    assert state["judges"][CLAUDE]["cursor"] == 0   # son curseur attend
    assert state["judges"][FINBERT]["cursor"] == 1


def test_scelle_viole_exit_3(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("S14_SENTIMENT_DIR", str(tmp_path))
    monkeypatch.setattr(rs, "PARAMS_SHA256", "0" * 64)
    assert rs.main([]) == 3
    assert "SCELL" in capsys.readouterr().err
    assert os.listdir(tmp_path) == []


def test_journal_altere_exit_4(paths, params, capsys):
    seal(paths, params)
    rs.run_pass(paths, params, collect=collector([_item(1)]),
                judges=[(CLAUDE, judge_ok())], now=NOW)
    brut = journal_bytes(paths)
    with open(paths.journal, "wb") as f:
        f.write(brut.replace(b"Dollar firms", b"Dollar sinks"))

    code = rs.run_pass(paths, params, collect=collector([_item(2)]),
                       judges=[(CLAUDE, judge_ok())], now=NOW)

    assert code == 4
    assert "JOURNAL" in capsys.readouterr().err


# ─────────────────────────────────────────────────────────────────────────────
# --dry-run
# ─────────────────────────────────────────────────────────────────────────────

def test_dry_run_n_ecrit_rien_sur_etude_vierge(paths, params, tmp_path,
                                               monkeypatch, capsys):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    assert rs.dry_run(paths, params, now=NOW) == 0
    assert os.listdir(tmp_path) == []
    assert "DRY-RUN" in capsys.readouterr().out


def test_dry_run_n_ecrit_rien_sur_etude_vivante(paths, params, capsys):
    seal(paths, params)
    # 2 périmées puis 2 fraîches, non jugées : le dry-run doit les ANNONCER
    # sans écrire la moindre ligne STALE.
    rs.run_pass(paths, params,
                collect=collector([_item(1, 9), _item(2, 9),
                                   _item(3, 1), _item(4, 1)]),
                judges=[], now=NOW)
    avant = journal_bytes(paths)
    etat_avant = json.load(open(paths.state, encoding="utf-8"))

    assert rs.dry_run(paths, params, now=NOW) == 0

    assert journal_bytes(paths) == avant
    assert json.load(open(paths.state, encoding="utf-8")) == etat_avant
    out = capsys.readouterr().out
    assert "2 périmée(s)" in out and "lot de 2 news" in out


# ─────────────────────────────────────────────────────────────────────────────
# Le juge Claude — prompt, extraction, modèle épinglé (aucun appel réel)
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_json_object_tolere_du_texte_autour():
    texte = ('Voici mon analyse.\n```json\n{"verdicts": [{"symbol": "EURUSD", '
             '"sentiment": "negative", "confidence": 0.83, '
             '"reason": "dollar fort {accolade dans une chaîne}"}]}\n```\n'
             'Fin.')
    obj = aj.extract_json_object(texte)
    assert obj is not None
    assert obj["verdicts"][0]["symbol"] == "EURUSD"
    assert obj["verdicts"][0]["confidence"] == 0.83
    assert aj.extract_json_object("aucun json ici") is None
    # Un premier objet illisible ne masque pas le suivant.
    assert aj.extract_json_object('{pas du json} {"verdicts": []}') == \
        {"verdicts": []}


def test_prompt_du_juge_porte_les_5_symboles_et_aucune_date_absolue(params):
    batch = [{"news_id": "1",
              "published_at_utc": (NOW - timedelta(hours=2, minutes=5))
              .strftime(rs.ISO),
              "source": "Reuters", "headline": "Dollar firms after CPI"},
             {"news_id": "2",
              "published_at_utc": (NOW - timedelta(minutes=20)).strftime(rs.ISO),
              "source": "Bloomberg", "headline": "ECB hawks push back"}]
    prompt = aj.build_prompt(batch, params["universe"], now=NOW)

    for sym in UNIVERSE:
        assert sym in prompt
    assert "Dollar firms after CPI" in prompt and "ECB hawks push back" in prompt
    assert "il y a 2 h 05" in prompt and "il y a 20 min" in prompt
    # Aucune date absolue : le juge ne doit pas savoir QUAND on est.
    assert "2026" not in prompt and "-08-" not in prompt
    assert "positive" in prompt and "neutral" in prompt


def test_modele_epingle_journalise_dans_reason_sans_colonne_neuve(paths,
                                                                  params):
    """Le tag du modèle voyage dans `reason` — 12 colonnes, pas 13."""
    seal(paths, params)

    def juge_claude(batch):
        juge_claude.last_error = ""
        return aj.tag_model({"verdicts": [
            {"symbol": s, "sentiment": "positive", "confidence": 0.9,
             "reason": "le dollar recule"} for s in UNIVERSE]})
    juge_claude.last_error = ""

    rs.run_pass(paths, params, collect=collector([_item(1)]),
                judges=[(CLAUDE, juge_claude)], now=NOW)

    rows = ss.read_journal(paths.journal)
    assert list(rows[0].keys()) == ss.JOURNAL_COLUMNS       # toujours 12
    verdicts = [r for r in rows if r["event"] == "VERDICT"]
    assert len(verdicts) == 5
    assert all(v["reason"].startswith(f"[{aj.JUDGE_MODEL}] ") for v in verdicts)
    assert all("le dollar recule" in v["reason"] for v in verdicts)
    assert {v["judge"] for v in verdicts} == {CLAUDE}       # nom du juge intact


def test_na_reason_porte_aussi_le_modele():
    assert aj.na_reason("timeout") == f"[{aj.JUDGE_MODEL}] timeout"
    assert aj.na_reason("") == f"[{aj.JUDGE_MODEL}] juge indisponible"


def test_test_judge_n_ecrit_rien_et_rend_0_ou_2(paths, params, monkeypatch,
                                                tmp_path, capsys):
    """`--test-judge` est un contrôle de CHAÎNE : il appelle le juge et
    n'écrit rien. Ici le CLI est simulé — aucun `claude` réel n'est lancé."""
    monkeypatch.setenv("S14_SENTIMENT_DIR", str(tmp_path))

    monkeypatch.setattr(aj, "invoke_claude_once",
                        lambda p, t, m: ({"verdicts": [
                            {"symbol": s, "sentiment": "neutral",
                             "confidence": 0.5, "reason": "rien de saillant"}
                            for s in UNIVERSE]}, ""))
    assert rs.test_judge(params, now=NOW) == 0
    out = capsys.readouterr().out
    assert aj.JUDGE_MODEL in out and "TEST" in out

    monkeypatch.setattr(aj, "invoke_claude_once", lambda p, t, m: (None, "401"))
    assert rs.test_judge(params, now=NOW) == 2
    assert os.listdir(tmp_path) == []              # ni journal, ni état


def test_make_judge_relance_une_fois_puis_rend_na(params, monkeypatch):
    appels = []

    def faux_invoke(prompt, timeout_s, model):
        appels.append(model)
        return None, "timeout"
    monkeypatch.setattr(aj, "invoke_claude_once", faux_invoke)

    juge = aj.make_judge(params)
    batch = [{"news_id": "1", "published_at_utc": NOW.strftime(rs.ISO),
              "source": "X", "headline": "titre"}]
    assert juge(batch) is None
    assert appels == [aj.JUDGE_MODEL] * 2                  # 1 + retries(1)
    assert juge.last_error == f"[{aj.JUDGE_MODEL}] timeout"
    assert juge.model == aj.JUDGE_MODEL                    # le modèle épinglé


# ─────────────────────────────────────────────────────────────────────────────
# Le témoin FinBERT — jamais de chargement réel
# ─────────────────────────────────────────────────────────────────────────────

def test_temoin_applique_le_verdict_de_lot_aux_5_instruments(params,
                                                             monkeypatch):
    monkeypatch.setattr(fw, "estimate_sentiment",
                        lambda headlines, model: (0.873, "positive"))
    temoin = fw.make_witness(params)
    raw = temoin([{"headline": "a"}, {"headline": "b"}])

    assert [v["symbol"] for v in raw["verdicts"]] == params["universe"]
    assert all(v["sentiment"] == "positive" for v in raw["verdicts"])
    assert all(v["confidence"] == 0.873 for v in raw["verdicts"])
    assert all(fw.WITNESS_MODEL in v["reason"] for v in raw["verdicts"])
    assert temoin.last_error == ""


def test_temoin_indisponible_rend_none_jamais_une_exception(params,
                                                            monkeypatch):
    def _boom(model_name):
        raise ImportError("transformers absent")
    monkeypatch.setattr(fw, "_CACHE", None)
    monkeypatch.setattr(fw, "_load", _boom)

    temoin = fw.make_witness(params)
    assert temoin([{"headline": "un titre"}]) is None
    assert fw.WITNESS_MODEL in temoin.last_error

    # Et le runner en fait 5 lignes `na`, sans crash.
    assert fw.estimate_sentiment(["x"]) is None


def test_temoin_sur_lot_sans_headline_exploitable(params, monkeypatch):
    monkeypatch.setattr(fw, "_CACHE", None)
    monkeypatch.setattr(fw, "_load",
                        lambda m: pytest.fail("le modèle ne doit PAS être "
                                              "chargé pour un lot vide"))
    temoin = fw.make_witness(params)
    assert temoin([{"headline": "   "}]) is None


# ─────────────────────────────────────────────────────────────────────────────
# Collecte Finnhub — transport, sans réseau
# ─────────────────────────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("corps non-JSON")
        return self._payload


def _fake_requests(monkeypatch, resp=None, boom=None):
    import types
    module = types.ModuleType("requests")

    def get(url, params=None, timeout=None):
        if boom is not None:
            raise boom
        get.calls.append((url, params, timeout))
        return resp
    get.calls = []
    module.get = get
    monkeypatch.setitem(sys.modules, "requests", module)
    return get


def test_collecte_passe_les_items_tels_quels(paths, params, monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "clé-de-test")
    payload = [{"id": 7, "datetime": 1755000000, "headline": "t", "source": "s"},
               "une chaîne parasite"]
    get = _fake_requests(monkeypatch, _Resp(200, payload))

    items, err = rs.collect_finnhub(paths, params)

    assert err == ""
    assert items == [payload[0]]                   # non-dicts écartés
    url, qs, timeout = get.calls[0]
    assert url == params["collect"]["endpoint"]
    assert qs == {"category": params["collect"]["category"],
                  "token": "clé-de-test"}
    assert timeout == rs.HTTP_TIMEOUT_S


@pytest.mark.parametrize("resp,boom,motif", [
    (_Resp(429, None, "rate limited"), None, "HTTP 429"),
    (_Resp(200, None, "<html>"), None, "non-JSON"),
    (_Resp(200, {"error": "nope"}), None, "JSON inattendu"),
    (None, TimeoutError("timeout"), "injoignable"),
])
def test_collecte_en_echec_ne_leve_jamais(paths, params, monkeypatch,
                                          resp, boom, motif):
    monkeypatch.setenv("FINNHUB_API_KEY", "clé-de-test")
    _fake_requests(monkeypatch, resp, boom)
    items, err = rs.collect_finnhub(paths, params)
    assert items == [] and motif in err


def test_cle_lue_dans_le_fichier_si_pas_d_env(paths, params, tmp_path,
                                              monkeypatch):
    """Le chemin HÉRITÉ (nommé par le protocole scellé) reste servi quand le
    coffre partagé est vide. Isolation obligatoire : sans elle, ce test lit la
    vraie clé du poste et cesse de tester quoi que ce soit."""
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.setenv("TBOT_SECRETS_DIR", str(tmp_path / "coffre_vide"))
    importlib.reload(secrets)
    paths.ensure()
    with open(paths.finnhub_key, "w", encoding="utf-8") as f:
        f.write("  clé-fichier\n")
    key, err = rs.read_api_key(paths)
    assert key == "clé-fichier" and err == ""
    monkeypatch.undo()
    importlib.reload(secrets)


# ─────────────────────────────────────────────────────────────────────────────
# La lecture (report_sentiment) — statistique et refus avant F1
# ─────────────────────────────────────────────────────────────────────────────

def test_wilson_unilateral_encadre_et_borne():
    lo, hi = rep.wilson_one_sided(75, 150)
    assert 0.0 < lo < 0.5 < hi < 1.0
    # 0 succès : borne basse à 0, borne haute strictement sous 1.
    lo0, hi0 = rep.wilson_one_sided(0, 50)
    assert lo0 == 0.0 and 0.0 < hi0 < 1.0
    # Plus d'effectif = intervalle plus serré, à proportion égale.
    lo_petit, hi_petit = rep.wilson_one_sided(30, 50)
    lo_grand, hi_grand = rep.wilson_one_sided(300, 500)
    assert (hi_grand - lo_grand) < (hi_petit - lo_petit)
    assert rep.wilson_one_sided(0, 0)[0] != rep.wilson_one_sided(0, 0)[0]  # NaN


def test_kappa_accord_parfait_et_desaccord():
    labels = ["positive", "negative", "neutral"]
    parfait = [("positive", "positive"), ("negative", "negative"),
               ("neutral", "neutral")] * 5
    assert rep.cohen_kappa(parfait, labels) == pytest.approx(1.0)
    croise = [("positive", "negative"), ("negative", "positive")] * 5
    assert rep.cohen_kappa(croise, labels) < 0
    assert rep.cohen_kappa([], labels) != rep.cohen_kappa([], labels)  # NaN


def test_dernier_verdict_neutral_annule_le_directionnel_anterieur():
    """§ 4 : le DERNIER verdict de la cellule fait foi — un `neutral` tardif
    rend la cellule non comptable. Et un `na` postérieur, lui, n'efface rien."""
    def v(measured, sentiment, conf, judge=CLAUDE, symbol="EURUSD"):
        return {"event": "VERDICT", "measured_at_utc": measured,
                "judge": judge, "symbol": symbol, "sentiment": sentiment,
                "confidence": conf}
    journal = [v("2026-01-12T08:00:00Z", "positive", "0.900"),
               v("2026-01-12T11:00:00Z", "neutral", "0.700"),
               v("2026-01-12T09:00:00Z", "positive", "0.950", symbol="AUDCAD"),
               v("2026-01-12T12:00:00Z", "na", "", symbol="AUDCAD")]
    cells = rep.read_cells(journal)
    cible = date(2026, 1, 13)                      # lundi 12 -> barre du mardi

    assert cells[(CLAUDE, "EURUSD", cible)]["sentiment"] == "neutral"
    assert rep.is_countable(cells[(CLAUDE, "EURUSD", cible)], 0.8) is False
    # Le `na` n'est pas un verdict : le directionnel antérieur survit.
    assert cells[(CLAUDE, "AUDCAD", cible)]["sentiment"] == "positive"
    assert rep.is_countable(cells[(CLAUDE, "AUDCAD", cible)], 0.8) is True
    # Confiance sous le seuil : directionnel mais pas comptable.
    assert rep.is_countable({"sentiment": "positive", "confidence": "0.790"},
                            0.8) is False


def test_succes_et_rendement_nul():
    assert rep.is_success("positive", 0.004) is True
    assert rep.is_success("negative", -0.004) is True
    assert rep.is_success("positive", 0.0) is False      # nul = échec (§ 4)
    assert rep.is_success("negative", 0.0) is False
    bars = {"EURUSD": {date(2026, 1, 13): (1.10, 1.11)}}
    assert rep.bar_return(bars, "EURUSD", date(2026, 1, 13)) == \
        pytest.approx(1.11 / 1.10 - 1)
    assert rep.bar_return(bars, "EURUSD", date(2026, 1, 14)) is None   # attente
    assert rep.bar_return(bars, "XAUUSD", date(2026, 1, 13)) is None


def test_report_refuse_le_hitrate_avant_F1(paths, params, monkeypatch,
                                           tmp_path, capsys):
    monkeypatch.setenv("S14_SENTIMENT_DIR", str(tmp_path))
    seal(paths, params)
    rs.run_pass(paths, params, collect=collector([_item(1)]),
                judges=[(CLAUDE, judge_ok("positive", 0.95)),
                        (FINBERT, judge_ok("positive", 0.95))], now=NOW)

    bars = {s: {rep.target_bar_for(NOW): (1.0, 1.2)} for s in UNIVERSE}
    code = rep.main([], bars_source=lambda universe: (bars, ""), now=NOW)

    assert code == 0
    out = capsys.readouterr().out
    assert "F1" in out and "pas atteint" in out
    assert "on ne regarde pas la casserole" in out
    # Aucun TAUX n'est chiffré : ni hit-rate, ni IC, ni moitiés F5. Le mot
    # « hit-rate » apparaît dans la phrase de refus — c'est le CHIFFRE qui est
    # interdit avant F1, pas le mot.
    assert re.search(r"hit-rate\s*[\d,.]+\s*%", out) is None
    assert "unilatéral Wilson" not in out          # pas d'IC
    assert "F5 moitiés" not in out                 # pas de moitiés
    assert "F3 corpus commun" not in out           # pas de delta témoin
    assert "5/150" in out                          # l'avancement, lui, s'affiche


def _corpus_post_F1(paths, params, depart, jours=45):
    """Un corpus synthétique qui FRANCHIT F1 : une news par jour pendant
    `jours`, jugée par les deux juges. Claude dit toujours `positive`, le
    témoin toujours `negative` — avec des barres haussières, le premier fait
    100 % et le second 0 %, ce qui déclenche des falsifications OPPOSÉES et
    fait passer la lecture par toutes ses branches."""
    def verdicts(sentiment, conf):
        return {"verdicts": [{"symbol": s, "sentiment": sentiment,
                              "confidence": conf, "reason": "r"}
                             for s in UNIVERSE]}

    state, _ = ss.ingest_news(paths, None, [], now=depart)
    for k in range(1, jours + 1):
        t = depart + timedelta(days=k, hours=10)
        item = {"id": 1000 + k, "headline": f"news {k}", "source": "src",
                "datetime": int((t - timedelta(hours=1)).timestamp())}
        state, _ = ss.ingest_news(paths, state, [item], now=t)
        rows = ss.read_journal(paths.journal)
        for judge, sentiment, conf in ((CLAUDE, "positive", 0.90),
                                       (FINBERT, "negative", 0.85)):
            batch = ss.next_batch(paths, state, rows, judge, t)
            if batch:
                state = ss.record_verdicts(paths, state, judge, batch,
                                           verdicts(sentiment, conf), now=t)
    return state


def test_report_lit_F2_a_F5_une_fois_F1_franchi(paths, params, monkeypatch,
                                                tmp_path, capsys):
    monkeypatch.setenv("S14_SENTIMENT_DIR", str(tmp_path))
    depart = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
    maintenant = depart + timedelta(days=70)        # F1 : >= 60 jours
    _corpus_post_F1(paths, params, depart)

    # Toutes les barres montent : Claude (toujours positive) fait 100 %, le
    # témoin (toujours negative) fait 0 %.
    jours = {depart.date() + timedelta(days=k): (1.0, 1.01) for k in range(90)}
    bars = {s: dict(jours) for s in UNIVERSE}

    code = rep.main([], bars_source=lambda u: (bars, ""), now=maintenant)

    assert code == 0
    out = capsys.readouterr().out
    assert "F1 claude-cli   ATTEINT" in out and "F1 finbert      ATTEINT" in out
    assert "hit-rate 100.0 %" in out and "hit-rate 0.0 %" in out
    assert "unilatéral Wilson" in out and "F5 moitiés" in out
    # Le témoin s'effondre : F2 (borne haute sous le plancher) ET F5.
    assert "F2 DÉCLENCHÉE (finbert)" in out
    assert "F5 DÉCLENCHÉE (finbert)" in out
    # Claude tient : borne basse au-dessus du plancher, moitiés au-dessus.
    assert "VALEUR CANDIDATE possible (claude-cli)" in out
    assert "F2 DÉCLENCHÉE (claude-cli)" not in out
    # F3 apparié par cellule : delta franchement positif, donc PAS déclenchée.
    assert "F3 corpus commun apparié par cellule" in out
    assert "delta +100.0 pts" in out
    assert "F3 DÉCLENCHÉE" not in out
    # F4 reste informatif — jamais dans la liste des falsifications.
    assert "F4 concordance (informatif)" in out
    assert "AUCUNE promotion trading directe" in out


def test_report_exit_2_si_barres_indisponibles(paths, params, monkeypatch,
                                               tmp_path, capsys):
    monkeypatch.setenv("S14_SENTIMENT_DIR", str(tmp_path))
    seal(paths, params)
    avant = journal_bytes(paths)

    code = rep.main([], bars_source=lambda u: ({}, "MT5 hors ligne"), now=NOW)

    assert code == 2
    assert journal_bytes(paths) == avant           # le lecteur n'écrit jamais
    assert "MT5 hors ligne" in capsys.readouterr().err


def test_report_exit_1_si_jamais_tourne(monkeypatch, tmp_path):
    monkeypatch.setenv("S14_SENTIMENT_DIR", str(tmp_path))
    assert rep.main([], bars_source=lambda u: ({}, "")) == 1


def test_report_exit_4_si_journal_altere(paths, params, monkeypatch, tmp_path):
    monkeypatch.setenv("S14_SENTIMENT_DIR", str(tmp_path))
    seal(paths, params)
    rs.run_pass(paths, params, collect=collector([_item(1)]),
                judges=[(CLAUDE, judge_ok())], now=NOW)
    brut = journal_bytes(paths)
    with open(paths.journal, "wb") as f:
        f.write(brut.replace(b"Dollar firms", b"Dollar sinks"))
    assert rep.main([], bars_source=lambda u: ({}, ""), now=NOW) == 4


# ─────────────────────────────────────────────────────────────────────────────
# Régressions de la review adversariale (2026-08-18) — les chemins qui coûtent
# ─────────────────────────────────────────────────────────────────────────────

def test_journal_non_inscriptible_aucun_appel_paye(paths, params, monkeypatch,
                                                   capsys):
    """LE bug le plus cher : le juge est payé AVANT l'écriture. Si le journal
    n'est pas inscriptible (Excel ouvert dessus, disque plein), le curseur
    n'avance pas et le même lot serait rejugé — donc repayé — à chaque tick,
    sans une alarme. On vérifie qu'on refuse AVANT de dépenser."""
    juge = judge_ok()
    rs.run_pass(paths, params, collect=collector([_item(1), _item(2)]),
                judges=[], now=NOW)                       # scellé + news
    rs.run_pass(paths, params, collect=collector([_item(3)]),
                judges=[], now=NOW)

    vrai_open = open

    def open_verrouille(fichier, mode="r", *a, **kw):
        if str(fichier) == str(paths.journal) and ("a" in mode or "w" in mode):
            raise PermissionError("verrou Excel")
        return vrai_open(fichier, mode, *a, **kw)

    monkeypatch.setattr("builtins.open", open_verrouille)
    code = rs.run_pass(paths, params, collect=collector([]),
                       judges=[(CLAUDE, juge)], now=NOW)
    monkeypatch.undo()

    assert code == 4                       # incident : la factory coupe et crie
    assert juge.seen == []                 # AUCUN appel payé
    assert "non inscriptible" in capsys.readouterr().err

    # Le verrou levé, le lot est jugé une fois et une seule.
    assert rs.run_pass(paths, params, collect=collector([]),
                       judges=[(CLAUDE, juge)], now=NOW) == 0
    assert len(juge.seen) == 1


def test_cle_finnhub_jamais_dans_un_message(paths, params, monkeypatch):
    """La clé voyage en query string : le repr d'une exception requests porte
    l'URL complète, donc le secret — et ce message finit dans un log gardé des
    mois."""
    monkeypatch.setenv("FINNHUB_API_KEY", "CLE_ULTRA_SECRETE_123456")

    class FauxRequests:
        @staticmethod
        def get(url, params=None, timeout=None):
            raise RuntimeError(
                "HTTPSConnectionPool(host='finnhub.io', port=443): Max retries "
                "exceeded with url: /api/v1/news?category=forex&"
                "token=CLE_ULTRA_SECRETE_123456")

    monkeypatch.setitem(sys.modules, "requests", FauxRequests)
    items, err = rs.collect_finnhub(paths, params)
    assert items == [] and err
    assert "CLE_ULTRA_SECRETE_123456" not in err
    assert "<clé masquée>" in err


def test_faute_de_frappe_ne_declenche_aucun_passage(monkeypatch):
    """`--dry-runn` tombait dans la branche par défaut : vraie collecte, vrais
    appels payés, vraies écritures dans le scellé."""
    appels = []
    monkeypatch.setattr(rs, "run_pass",
                        lambda *a, **kw: appels.append("PASSAGE RÉEL") or 0)
    for faute in ("--dry-runn", "--dryrun", "-dry-run", "--force"):
        assert rs.main([faute]) == 1
    assert appels == []


def test_finbert_ne_telecharge_jamais_dans_un_tick(monkeypatch):
    """440 Mo dans un tick plafonné à 20 min ferait tuer l'arbre en plein vol,
    tick après tick, en vidant le bras témoin en silence."""
    vus = {}

    class FauxAuto:
        @staticmethod
        def from_pretrained(nom, **kw):
            vus.update(kw)
            raise OSError("modèle absent du cache local")

    faux = type(sys)("transformers")
    faux.AutoTokenizer = FauxAuto
    faux.AutoModelForSequenceClassification = FauxAuto
    monkeypatch.setitem(sys.modules, "transformers", faux)
    fw._CACHE = None

    assert fw.estimate_sentiment(["dollar firms"]) is None      # -> `na`
    assert vus.get("local_files_only") is True
    fw._CACHE = None

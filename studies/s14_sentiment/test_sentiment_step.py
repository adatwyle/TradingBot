"""
Tests du pas de mesure s14_sentiment — news synthétiques, AUCUN réseau,
AUCUN accès à C:\\db (tout passe par `tmp_path`).

Couvre les invariants du protocole scellé : hash épinglé, chaîne du journal
(réécriture, troncature, suppression), dedup d'ingestion, sanitisation,
pose du scellé au premier passage, lots contigus ≤ 40, curseurs par juge
indépendants qui ne SAUTENT jamais de ligne (péremption STALE en tête et au
milieu du backlog), « na consomme le lot », clamp des verdicts, judges.txt,
et le mapping barre cible du § 4 (week-end + bascule DST US comprises).
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from studies.s14_sentiment import sentiment_step as ss  # noqa: E402

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
UNIVERSE = ["AUDCHF", "EURUSD", "AUDCAD", "EURJPY", "XAUUSD"]


# ─────────────────────────────────────────────────────────────────────────────
# Outils
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def paths(tmp_path):
    p = ss.Paths(str(tmp_path))
    p.ensure()
    return p


def _item(nid, published: datetime, headline="Euro slips as dollar firms",
          source="src"):
    return {"id": nid, "datetime": int(published.timestamp()),
            "headline": headline, "source": source}


def _fresh(nid, headline="fresh headline", hours_old=1.0):
    return _item(nid, NOW - timedelta(hours=hours_old), headline=headline)


def _stale_item(nid, headline="stale headline"):
    return _item(nid, NOW - timedelta(hours=7), headline=headline)


def _seal(paths, items=()):
    """Premier passage : pose du scellé (journal en-tête seule)."""
    state, n = ss.ingest_news(paths, None, list(items),
                              now=NOW - timedelta(hours=2))
    assert n == 0
    return state


def _verdicts_ok(sentiment="positive", confidence=0.9):
    return {"verdicts": [{"symbol": s, "sentiment": sentiment,
                          "confidence": confidence, "reason": "raison courte"}
                         for s in UNIVERSE]}


def _journal_lines(paths):
    with open(paths.journal, "r", encoding="utf-8", newline="") as f:
        return [ln for ln in f.read().split("\n") if ln != ""]


# ─────────────────────────────────────────────────────────────────────────────
# Scellé
# ─────────────────────────────────────────────────────────────────────────────

def test_hash_du_vrai_fichier_scelle_correspond():
    # Épingle PARAMS_SHA256 contre le fichier réel du dépôt : la moindre
    # divergence (scellé violé) casse ce test.
    assert ss.sha256_file(ss.PARAMS_PATH) == ss.PARAMS_SHA256
    params = ss.load_sealed_params(ss.PARAMS_PATH, ss.PARAMS_SHA256)
    assert params["study"] == "s14_sentiment"
    assert params["universe"] == UNIVERSE


def test_refus_net_si_hash_faux():
    with pytest.raises(ss.SealError, match="SCELL"):
        ss.load_sealed_params(ss.PARAMS_PATH, "0" * 64)


# ─────────────────────────────────────────────────────────────────────────────
# Chaîne du journal
# ─────────────────────────────────────────────────────────────────────────────

def _build_small_journal(paths):
    state = _seal(paths)
    state, n = ss.ingest_news(
        paths, state,
        [_fresh(1, headline="AAAA-un"), _fresh(2, headline="BBBB-deux")],
        now=NOW)
    assert n == 2
    return state


def test_chaine_append_puis_verify_ok(paths):
    state = _build_small_journal(paths)
    ss.verify_journal(paths.journal, state)      # ne lève pas
    ss.verify_journal(paths.journal, None)       # la chaîne se vérifie seule


def test_reecriture_ligne_mediane_detectee(paths):
    state = _build_small_journal(paths)
    with open(paths.journal, "rb") as f:
        raw = f.read()
    with open(paths.journal, "wb") as f:
        f.write(raw.replace(b"AAAA-un", b"AAAA-uX"))
    with pytest.raises(ss.JournalError, match="CHA\u00ceNE CASS\u00c9E"):
        ss.verify_journal(paths.journal, state)


def test_reecriture_derniere_ligne_detectee_par_empreinte(paths):
    # La dernière ligne réécrite laisse la chaîne interne cohérente (aucun
    # maillon suivant) — c'est l'empreinte d'état qui l'attrape.
    state = _build_small_journal(paths)
    with open(paths.journal, "rb") as f:
        raw = f.read()
    with open(paths.journal, "wb") as f:
        f.write(raw.replace(b"BBBB-deux", b"BBBB-deuX"))
    with pytest.raises(ss.JournalError, match="r\u00e9\u00e9criture"):
        ss.verify_journal(paths.journal, state)


def test_troncature_detectee(paths):
    state = _build_small_journal(paths)
    with open(paths.journal, "rb") as f:
        raw = f.read()
    tronque = b"\n".join(raw.rstrip(b"\n").split(b"\n")[:-1]) + b"\n"
    with open(paths.journal, "wb") as f:
        f.write(tronque)
    with pytest.raises(ss.JournalError, match="tronqu"):
        ss.verify_journal(paths.journal, state)


def test_suppression_journal_detectee(paths):
    state = _build_small_journal(paths)
    os.remove(paths.journal)
    with pytest.raises(ss.JournalError, match="suppression"):
        ss.verify_journal(paths.journal, state)


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion — pose du scellé, dedup, sanitisation
# ─────────────────────────────────────────────────────────────────────────────

def test_premier_passage_pose_le_scelle_sans_jugement(paths):
    items = [_fresh(1), _fresh(2)]
    state, n = ss.ingest_news(paths, None, items, now=NOW)
    # Journal en-tête seule : le flux courant est l'histoire, pas le corpus.
    assert n == 0
    lines = _journal_lines(paths)
    assert len(lines) == 1
    assert lines[0].split(",") == ss.JOURNAL_COLUMNS
    # État posé : curseurs des deux juges à zéro, ids marqués vus.
    assert state["n_news_total"] == 0
    assert state["judges"]["claude-cli"]["cursor"] == 0
    assert state["judges"]["finbert"]["cursor"] == 0
    assert set(state["seen_ids"]) == {"1", "2"}
    # Aucun jugement : rien à juger, aucun lot.
    assert ss.next_batch(paths, state, ss.read_journal(paths.journal),
                         "claude-cli", NOW) == []
    # Les ids du scellement ne rentrent jamais (pas de backfill).
    state, n = ss.ingest_news(paths, state, items, now=NOW)
    assert n == 0
    assert len(_journal_lines(paths)) == 1


def test_dedup_deux_passages_memes_ids(paths):
    state = _seal(paths)
    items = [_fresh(10), _fresh(11)]
    state, n = ss.ingest_news(paths, state, items, now=NOW)
    assert n == 2
    with open(paths.journal, "rb") as f:
        avant = f.read()
    state, n = ss.ingest_news(paths, state, items, now=NOW)
    assert n == 0
    with open(paths.journal, "rb") as f:
        apres = f.read()
    assert avant == apres                      # zéro nouvelle ligne, à l'octet
    ss.verify_journal(paths.journal, state)


def test_sanitisation_headline(paths):
    state = _seal(paths)
    sale = "Ligne1\nLigne2\r\nLigne3" + "x" * 500
    state, n = ss.ingest_news(paths, state, [_fresh(1, headline=sale)],
                              now=NOW)
    assert n == 1
    rows = ss.read_journal(paths.journal)
    head = rows[0]["headline"]
    assert "\n" not in head and "\r" not in head
    assert len(head) == 300                    # collect.max_headline_chars
    assert head.startswith("Ligne1 Ligne2 Ligne3")
    ss.verify_journal(paths.journal, state)    # la chaîne survit au champ sale


# ─────────────────────────────────────────────────────────────────────────────
# Lots par juge
# ─────────────────────────────────────────────────────────────────────────────

def test_lot_max_40_et_contigu(paths):
    state = _seal(paths)
    state, n = ss.ingest_news(paths, state,
                              [_fresh(100 + i) for i in range(50)], now=NOW)
    assert n == 50
    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "claude-cli", NOW)
    assert len(batch) == 40                    # judge.batch_max_news
    assert [b["index"] for b in batch] == list(range(40))
    assert batch[0]["news_id"] == "100"
    assert batch[-1]["news_id"] == "139"


def test_curseurs_par_juge_independants(paths):
    state = _seal(paths)
    state, _ = ss.ingest_news(paths, state, [_fresh(i) for i in (1, 2, 3)],
                              now=NOW)
    rows = ss.read_journal(paths.journal)
    batch_c = ss.next_batch(paths, state, rows, "claude-cli", NOW)
    state = ss.record_verdicts(paths, state, "claude-cli", batch_c,
                               _verdicts_ok(), now=NOW)
    assert state["judges"]["claude-cli"]["cursor"] == 3
    assert state["judges"]["finbert"]["cursor"] == 0
    # Le témoin repart de zéro, sur les MÊMES news.
    batch_f = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                            "finbert", NOW)
    assert [b["index"] for b in batch_f] == [0, 1, 2]
    state = ss.record_verdicts(paths, state, "finbert", batch_f,
                               _verdicts_ok("neutral", 0.6), now=NOW)
    assert state["judges"]["finbert"]["cursor"] == 3
    judges_vus = {r["judge"] for r in ss.read_journal(paths.journal)
                  if r["event"] == "VERDICT"}
    assert judges_vus == {"claude-cli", "finbert"}
    ss.verify_journal(paths.journal, state)


def test_lot_ne_se_journalise_qu_une_fois(paths):
    state = _seal(paths)
    state, _ = ss.ingest_news(paths, state, [_fresh(1)], now=NOW)
    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "claude-cli", NOW)
    state = ss.record_verdicts(paths, state, "claude-cli", batch,
                               _verdicts_ok(), now=NOW)
    with pytest.raises(ValueError, match="d\u00e9synchronis"):
        ss.record_verdicts(paths, state, "claude-cli", batch,
                           _verdicts_ok(), now=NOW)


def test_stale_en_tete_consomme_en_une_ligne_par_juge(paths):
    state = _seal(paths)
    # 3 périmées puis 2 fraîches — dont une à EXACTEMENT 6 h (pas périmée :
    # la règle est strictement supérieur).
    state, n = ss.ingest_news(
        paths, state,
        [_stale_item(1), _stale_item(2), _stale_item(3),
         _fresh(4, hours_old=6.0), _fresh(5)], now=NOW)
    assert n == 5
    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "claude-cli", NOW)
    stales = [r for r in ss.read_journal(paths.journal) if r["event"] == "STALE"]
    assert len(stales) == 1
    assert stales[0]["news_id"] == "1..3"      # UNE ligne pour le run entier
    assert stales[0]["judge"] == "claude-cli"
    assert state["judges"]["claude-cli"]["cursor"] == 3
    assert state["judges"]["claude-cli"]["n_stale_news"] == 3
    assert [b["news_id"] for b in batch] == ["4", "5"]
    # Le témoin consomme SA péremption lui-même, indépendamment.
    batch_f = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                            "finbert", NOW)
    stales = [r for r in ss.read_journal(paths.journal) if r["event"] == "STALE"]
    assert len(stales) == 2
    assert {s["judge"] for s in stales} == {"claude-cli", "finbert"}
    assert [b["news_id"] for b in batch_f] == ["4", "5"]
    ss.verify_journal(paths.journal, state)


def test_news_perimee_au_milieu_coupe_le_lot_sans_saut(paths):
    state = _seal(paths)
    # fraîche, fraîche, PÉRIMÉE, fraîche — la périmée est au milieu.
    state, n = ss.ingest_news(
        paths, state,
        [_fresh(1), _fresh(2), _stale_item(3), _fresh(4)], now=NOW)
    assert n == 4
    # Passage 1 : le lot s'arrête AVANT la périmée, aucune ligne STALE.
    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "claude-cli", NOW)
    assert [b["news_id"] for b in batch] == ["1", "2"]
    assert [r for r in ss.read_journal(paths.journal)
            if r["event"] == "STALE"] == []
    state = ss.record_verdicts(paths, state, "claude-cli", batch,
                               _verdicts_ok(), now=NOW)
    assert state["judges"]["claude-cli"]["cursor"] == 2   # sans saut
    # Passage 2 : le segment périmé, maintenant en tête, part en STALE ;
    # le lot suivant reprend juste derrière.
    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "claude-cli", NOW)
    stales = [r for r in ss.read_journal(paths.journal) if r["event"] == "STALE"]
    assert len(stales) == 1 and stales[0]["news_id"] == "3..3"
    assert state["judges"]["claude-cli"]["cursor"] == 3
    assert [b["news_id"] for b in batch] == ["4"]
    state = ss.record_verdicts(paths, state, "claude-cli", batch,
                               _verdicts_ok(), now=NOW)
    assert state["judges"]["claude-cli"]["cursor"] == 4
    ss.verify_journal(paths.journal, state)


def _consumed_ids(rows, judge, news_ids):
    """Reconstruit, depuis le journal SEUL, la suite des news consommées par
    un juge (lots VERDICT + segments STALE, dans l'ordre du journal)."""
    out = []
    derniere_plage_verdict = None
    for r in rows:
        if r.get("judge") != judge or r["event"] not in ("VERDICT", "STALE"):
            continue
        rng = r["news_id"]
        if r["event"] == "VERDICT":
            if rng == derniere_plage_verdict:
                continue                       # 5 lignes par lot, une plage
            derniere_plage_verdict = rng
        a, b = rng.split("..")
        i, j = news_ids.index(a), news_ids.index(b)
        out.extend(news_ids[i:j + 1])
    return out


def test_curseur_ne_saute_jamais_reconstruction_depuis_journal(paths):
    # Observation du reviewer du protocole : chaque ligne NEWS doit finir
    # soit dans un lot jugé, soit dans un STALE — jamais sautée. On le
    # vérifie en reconstruisant la consommation depuis le journal seul.
    state = _seal(paths)
    state, _ = ss.ingest_news(
        paths, state,
        [_fresh(1), _stale_item(2), _stale_item(3), _fresh(4), _fresh(5),
         _stale_item(6), _fresh(7)], now=NOW)
    for judge in ("claude-cli", "finbert"):
        # On épuise le backlog du juge : lots + péremptions alternés.
        for _ in range(10):
            batch = ss.next_batch(paths, state,
                                  ss.read_journal(paths.journal), judge, NOW)
            if not batch:
                break
            state = ss.record_verdicts(paths, state, judge, batch,
                                       _verdicts_ok(), now=NOW)
    rows = ss.read_journal(paths.journal)
    news_ids = [r["news_id"] for r in rows if r["event"] == "NEWS"]
    assert news_ids == ["1", "2", "3", "4", "5", "6", "7"]
    for judge in ("claude-cli", "finbert"):
        assert _consumed_ids(rows, judge, news_ids) == news_ids
        assert state["judges"][judge]["cursor"] == len(news_ids)
    ss.verify_journal(paths.journal, state)


# ─────────────────────────────────────────────────────────────────────────────
# Verdicts — na consomme le lot, clamp
# ─────────────────────────────────────────────────────────────────────────────

def test_na_consomme_le_lot(paths):
    state = _seal(paths)
    state, _ = ss.ingest_news(paths, state, [_fresh(1), _fresh(2)], now=NOW)
    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "claude-cli", NOW)
    state = ss.record_verdicts(paths, state, "claude-cli", batch, None,
                               now=NOW, na_reason="timeout")
    verdicts = [r for r in ss.read_journal(paths.journal)
                if r["event"] == "VERDICT"]
    assert len(verdicts) == 5                  # un par instrument, même en na
    assert all(v["sentiment"] == "na" for v in verdicts)
    assert all(v["confidence"] == "" for v in verdicts)   # vide si na
    assert all(v["reason"] == "timeout" for v in verdicts)
    assert all(v["news_id"] == "1..2" for v in verdicts)
    # La panne CONSOMME le lot : le curseur avance, on ne rejuge jamais.
    assert state["judges"]["claude-cli"]["cursor"] == 2
    assert state["judges"]["claude-cli"]["n_na"] == 5
    assert ss.next_batch(paths, state, ss.read_journal(paths.journal),
                         "claude-cli", NOW) == []
    ss.verify_journal(paths.journal, state)


def test_clamp_verdicts(paths):
    state = _seal(paths)
    state, _ = ss.ingest_news(paths, state, [_fresh(1)], now=NOW)
    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "claude-cli", NOW)
    brut = {"verdicts": [
        {"symbol": "AUDCHF", "sentiment": "bullish",       # hors vocabulaire
         "confidence": 0.9, "reason": "vocabulaire inventé"},
        {"symbol": "EURUSD", "sentiment": "positive",
         "confidence": 1.7, "reason": "confiance > max"},
        {"symbol": "AUDCAD", "sentiment": "negative",
         "confidence": "abc", "reason": "confiance illisible"},
        # EURJPY absent -> na
        {"symbol": "XAUUSD", "sentiment": "neutral",
         "confidence": -0.2, "reason": "a\nb" + "z" * 400},
        {"symbol": "GBPUSD", "sentiment": "positive",      # hors univers
         "confidence": 0.5, "reason": "ignoré"},
    ]}
    state = ss.record_verdicts(paths, state, "claude-cli", batch, brut,
                               now=NOW)
    verdicts = {r["symbol"]: r for r in ss.read_journal(paths.journal)
                if r["event"] == "VERDICT"}
    assert set(verdicts) == set(UNIVERSE)      # 5 lignes, GBPUSD ignoré
    assert verdicts["AUDCHF"]["sentiment"] == "na"
    assert verdicts["AUDCHF"]["confidence"] == ""
    # § 3 : une ligne `na` porte la cause, pas la prose écartée.
    assert verdicts["AUDCHF"]["reason"] == "sentiment hors vocabulaire"
    assert "vocabulaire inventé" not in verdicts["AUDCHF"]["reason"]
    assert verdicts["EURUSD"]["confidence"] == "1.000"    # clampée au max
    assert verdicts["AUDCAD"]["confidence"] == "0.000"    # illisible = défaut
    assert verdicts["EURJPY"]["sentiment"] == "na"
    assert verdicts["XAUUSD"]["confidence"] == "0.000"    # clampée au min
    raison = verdicts["XAUUSD"]["reason"]
    assert "\n" not in raison and len(raison) == 300      # sanitisée
    assert state["judges"]["claude-cli"]["cursor"] == 1
    ss.verify_journal(paths.journal, state)


# ─────────────────────────────────────────────────────────────────────────────
# judges.txt
# ─────────────────────────────────────────────────────────────────────────────

def test_judges_txt(paths):
    # Fichier absent = tous ON.
    assert ss.read_judges(paths) == {}
    assert ss.judge_is_on({}, "claude-cli") is True
    assert ss.judge_is_on({}, "finbert") is True
    with open(paths.judges, "w", encoding="utf-8") as f:
        f.write("claude-cli = off   # il brûle des tokens\n"
                "ligne illisible sans egal\n"
                "finbert = on\n")
    judges = ss.read_judges(paths)
    assert judges == {"claude-cli": False, "finbert": True}
    assert ss.judge_is_on(judges, "claude-cli") is False
    assert ss.judge_is_on(judges, "finbert") is True
    assert ss.judge_is_on(judges, "gpt-futur") is True    # non listé = ON


# ─────────────────────────────────────────────────────────────────────────────
# Mapping barre cible (§ 4)
# ─────────────────────────────────────────────────────────────────────────────

def test_server_utc_offset_dst_us():
    # 2026 : 2e dimanche de mars = 8 mars ; 1er dimanche de novembre = 1er nov.
    assert ss.server_utc_offset(date(2026, 1, 12)) == 2    # hiver US
    assert ss.server_utc_offset(date(2026, 3, 7)) == 2     # veille bascule
    assert ss.server_utc_offset(date(2026, 3, 8)) == 3     # jour de bascule
    assert ss.server_utc_offset(date(2026, 7, 1)) == 3     # été US
    assert ss.server_utc_offset(date(2026, 10, 31)) == 3   # dernier jour été
    assert ss.server_utc_offset(date(2026, 11, 1)) == 2    # retour hiver


def test_barre_cible_lundi_hiver():
    # Verdict lundi 10:00 UTC (hiver US) : la barre du lundi a ouvert
    # dimanche 22:00 UTC — déjà passée. Cible = mardi.
    m = datetime(2026, 1, 12, 10, 0, tzinfo=timezone.utc)   # lundi
    assert ss.target_bar_for(m) == date(2026, 1, 13)        # mardi


def test_barre_cible_dimanche_avant_et_apres_ouverture():
    # Dimanche AVANT l'ouverture serveur (22:00 UTC en hiver) -> lundi.
    avant = datetime(2026, 1, 11, 15, 0, tzinfo=timezone.utc)
    assert ss.target_bar_for(avant) == date(2026, 1, 12)
    # Dimanche APRÈS l'ouverture -> la barre du lundi est déjà ouverte,
    # cible = mardi. Zéro lookahead, même le dimanche soir.
    apres = datetime(2026, 1, 11, 22, 30, tzinfo=timezone.utc)
    assert ss.target_bar_for(apres) == date(2026, 1, 13)
    # Frontière stricte : un verdict PILE à l'ouverture ne vise pas la barre
    # qui ouvre (strictement postérieure exigée).
    pile = datetime(2026, 1, 11, 22, 0, tzinfo=timezone.utc)
    assert ss.target_bar_for(pile) == date(2026, 1, 13)


def test_barre_cible_semaine_bascule_dst_mars():
    # Mercredi 11 mars 2026 21:30 UTC — semaine de la bascule DST US
    # (2e dimanche = 8 mars, US déjà en été, offset 3). La barre du jeudi
    # ouvre mercredi 21:00 UTC < 21:30 : déjà ouverte. Cible = vendredi.
    m = datetime(2026, 3, 11, 21, 30, tzinfo=timezone.utc)
    assert ss.bar_open_utc(date(2026, 3, 12)) == \
        datetime(2026, 3, 11, 21, 0, tzinfo=timezone.utc)
    assert ss.target_bar_for(m) == date(2026, 3, 13)       # vendredi


# ─────────────────────────────────────────────────────────────────────────────
# status.json
# ─────────────────────────────────────────────────────────────────────────────

def test_write_status_effectifs_sans_hitrate(paths):
    state = _seal(paths)
    state, _ = ss.ingest_news(paths, state, [_fresh(1), _fresh(2)], now=NOW)
    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "claude-cli", NOW)
    state = ss.record_verdicts(paths, state, "claude-cli", batch,
                               _verdicts_ok(), now=NOW)
    status = ss._write_status(paths, state, ss._now_iso(NOW),
                              first_pass=False)
    assert os.path.exists(paths.status)
    assert status["n_news_total"] == 2
    assert status["judges"]["claude-cli"]["n_verdicts_total"] == 5
    assert status["judges"]["claude-cli"]["cursor"] == 2
    assert status["judges"]["finbert"]["backlog_news"] == 2
    # Assertions ancrées sur le contexte, pas sur un chiffre isolé qui
    # matcherait n'importe quelle autre sous-chaîne.
    assert "150 verdicts" in status["stop_criteria"]["f1"]
    assert "60 jours" in status["stop_criteria"]["f1"]
    assert "6 mois" in status["stop_criteria"]["time"]
    # On ne regarde pas la casserole : aucun hit-rate avant F1.
    assert "hit_rate" not in json_dumps_lower(status)


# ─────────────────────────────────────────────────────────────────────────────
# Régressions issues des reviews (2026-08-17)
# ─────────────────────────────────────────────────────────────────────────────

def test_re_scellement_refuse_si_journal_non_vide(paths):
    """État perdu + journal peuplé : le passage suivant NE DOIT PAS re-poser
    le scellé (curseurs à 0 = tout le backlog rejugé, verdicts dupliqués,
    double comptage au report). C'est le bug silencieux qui coûte l'étude."""
    state = _seal(paths)
    state, _ = ss.ingest_news(paths, state, [_fresh(1), _fresh(2)], now=NOW)
    avant = _journal_lines(paths)

    with pytest.raises(ss.JournalError):
        ss.ingest_news(paths, None, [_fresh(3)], now=NOW)   # état « perdu »

    assert _journal_lines(paths) == avant                   # rien écrit


def test_lot_non_contigu_refuse(paths):
    """Un lot troué ferait sauter le curseur par-dessus des news SANS trace
    (ni VERDICT ni STALE) : refus structurel, pas seulement promesse."""
    state = _seal(paths)
    state, _ = ss.ingest_news(paths, state,
                              [_fresh(1), _fresh(2), _fresh(3)], now=NOW)
    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "claude-cli", NOW)
    troue = [batch[0], batch[2]]                            # index 0 puis 2
    with pytest.raises(ValueError, match="non contigu"):
        ss.record_verdicts(paths, state, "claude-cli", troue,
                           _verdicts_ok(), now=NOW)


def test_verification_integrite_meme_sans_collecte(paths):
    """Collecte en panne (items=[]) : l'intégrité est quand même vérifiée —
    c'est le pivot du modèle (§ 7, « avant toute écriture »)."""
    state = _seal(paths)
    state, _ = ss.ingest_news(paths, state, [_fresh(1)], now=NOW)
    lignes = _journal_lines(paths)
    lignes[1] = lignes[1].replace("fresh headline", "headline falsifiee")
    with open(paths.journal, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lignes) + "\n")

    with pytest.raises(ss.JournalError):
        ss.ingest_news(paths, state, [], now=NOW)


def test_juge_inconnu_sous_etat_paresseux(paths):
    """Un juge ajouté plus tard (gpt-*) démarre curseur 0 sans configuration
    préalable : son backlog part en STALE, son compteur F1 démarre à son
    arrivée (§ 2.5)."""
    state = _seal(paths)
    state, _ = ss.ingest_news(paths, state, [_fresh(1)], now=NOW)
    assert "gpt-test" not in state["judges"]

    batch = ss.next_batch(paths, state, ss.read_journal(paths.journal),
                          "gpt-test", NOW)
    assert len(batch) == 1
    state = ss.record_verdicts(paths, state, "gpt-test", batch,
                               _verdicts_ok(), now=NOW)
    assert state["judges"]["gpt-test"]["cursor"] == 1
    assert state["judges"]["claude-cli"]["cursor"] == 0     # intact
    ss.verify_journal(paths.journal, state)


def test_barre_cible_week_end(paths):
    """Vendredi soir et samedi visent tous deux la barre du lundi — la
    semaine de trading est fermée entre les deux."""
    # Hiver (serveur UTC+2) : lundi 12 janvier 2026 ouvre dimanche 22:00 UTC.
    vendredi_soir = datetime(2026, 1, 9, 22, 30, tzinfo=timezone.utc)
    samedi = datetime(2026, 1, 10, 15, 0, tzinfo=timezone.utc)
    assert ss.target_bar_for(vendredi_soir) == date(2026, 1, 12)
    assert ss.target_bar_for(samedi) == date(2026, 1, 12)

    # Été (serveur UTC+3) : lundi 15 juin 2026 ouvre dimanche 21:00 UTC.
    vendredi_ete = datetime(2026, 6, 12, 21, 30, tzinfo=timezone.utc)
    samedi_ete = datetime(2026, 6, 13, 8, 0, tzinfo=timezone.utc)
    assert ss.target_bar_for(vendredi_ete) == date(2026, 6, 15)
    assert ss.target_bar_for(samedi_ete) == date(2026, 6, 15)


def json_dumps_lower(obj):
    import json
    return json.dumps(obj).lower()

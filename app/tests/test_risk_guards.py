"""
Tests de la couche de risque.

Ce qui compte n'est pas qu'elle laisse passer un ordre normal — c'est qu'elle
REFUSE. Un garde-fou qui n'a jamais dit non n'a jamais été testé.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from core.contracts.strategy import Side, Signal
from core.risk.guards import Decision, Rejection, RiskLayer, RiskLimits

TS = datetime(2026, 8, 16, 10, 0)


def sig(symbol="EURUSD", side=Side.LONG, entry=1.1000, stop=1.0950, target=1.1100):
    return Signal(timestamp=TS, symbol=symbol, side=side, entry=entry,
                  stop=stop, target=target, reason="test")


def test_dimensionnement_par_le_risque():
    """On risque max_position_pct du capital sur la distance entrée-stop,
    pas une fraction du capital en notionnel."""
    r = RiskLayer(capital=10_000,
                  limits=RiskLimits(max_position_pct=0.02, max_book_risk_pct=0.06,
                                    max_book_leverage=100.0))
    d = r.evaluate(sig(entry=1.1000, stop=1.0950), value_per_unit=1.0)
    assert d.approved, d.detail
    assert abs(d.risk_amount - 200.0) < 1e-6, d.risk_amount   # 2 % de 10 000
    assert abs(d.size - 200.0 / 0.005) < 1e-6, d.size
    print(f"dimensionnement par le risque ...... OK (risque {d.risk_amount:.0f} €)")


def test_stop_large_reduit_la_taille():
    """Deux stops, même capital : le stop large doit donner une position plus
    petite pour un risque identique."""
    r = RiskLayer(capital=10_000)
    serre = r.evaluate(sig(stop=1.0990)).size
    large = r.evaluate(sig(stop=1.0900)).size
    assert large < serre, f"large={large}, serré={serre}"
    print(f"stop large => taille réduite ....... OK ({large:.0f} vs {serre:.0f})")


def test_contrat_refuse_le_stop_incoherent_en_premier():
    """Le contrat Signal refuse deja un stop du mauvais cote a la construction.
    C'est la PREMIERE barriere, et elle est plus forte : un tel signal ne peut
    meme pas exister."""
    for kw in ({"entry": 1.10, "stop": 1.10},
               {"side": Side.LONG, "entry": 1.10, "stop": 1.12},
               {"side": Side.SHORT, "entry": 1.10, "stop": 1.08, "target": 1.05}):
        try:
            sig(**kw)
            assert False, f"le contrat a accepte {kw}"
        except ValueError:
            pass
    print("contrat : stop incoherent refuse ... OK (3 formes)")


def test_couche_de_risque_en_seconde_barriere():
    """Defense en profondeur : si un Signal est altere apres construction
    (deserialisation, bug ailleurs), la couche de risque doit encore refuser.
    Une seule barriere n'est pas une barriere."""
    r = RiskLayer(capital=10_000)

    s1 = sig()
    object.__setattr__(s1, "stop", s1.entry)          # contourne le contrat
    d = r.evaluate(s1)
    assert not d and d.reason is Rejection.STOP_AT_ENTRY, d.reason

    s2 = sig()
    object.__setattr__(s2, "stop", 1.12)              # stop au-dessus, en LONG
    d = r.evaluate(s2)
    assert not d and d.reason is Rejection.NO_STOP, d.reason

    s3 = sig()
    object.__setattr__(s3, "stop", None)
    d = r.evaluate(s3)
    assert not d and d.reason is Rejection.NO_STOP, d.reason
    print("risque : seconde barriere tient .... OK (3 formes)")


def test_plafond_de_risque_du_livre():
    """Le risque CUMULÉ est borné : si tous les stops sautent le même jour, la
    perte reste sous le plafond. La dernière position est RÉDUITE plutôt que
    refusée tant qu'il reste de la place."""
    r = RiskLayer(capital=10_000,
                  limits=RiskLimits(max_position_pct=0.02, max_book_risk_pct=0.05,
                                    max_book_leverage=100.0,   # desserre pour isoler
                                    max_open_positions=10))
    for s in ["EURUSD", "USDJPY", "XAUUSD", "DAX", "SP500"]:
        d = r.evaluate(sig(symbol=s))
        if not d:
            assert d.reason is Rejection.BOOK_CAP, d.reason
            break
        r.register(sig(symbol=s), d.size, risk_amount=d.risk_amount)
    plafond = 10_000 * 0.05
    assert r.book_risk <= plafond + 1e-6, f"risque {r.book_risk} > plafond {plafond}"
    assert r.book_risk > plafond * 0.99, f"place non utilisee : {r.book_risk}"
    print(f"risque cumule du livre borne ....... OK "
          f"({r.book_risk:.0f} / {plafond:.0f} EUR, {len(r.positions)} positions)")


def test_plafond_de_levier():
    """Borne de marge, distincte de la borne de risque."""
    r = RiskLayer(capital=10_000,
                  limits=RiskLimits(max_position_pct=0.02, max_book_risk_pct=0.50,
                                    max_book_leverage=2.0, max_open_positions=10))
    for s in ["EURUSD", "USDJPY", "XAUUSD", "DAX", "SP500", "FTSE"]:
        d = r.evaluate(sig(symbol=s))
        if not d:
            assert d.reason is Rejection.LEVERAGE_CAP, d.reason
            break
        r.register(sig(symbol=s), d.size, risk_amount=d.risk_amount)
    assert r.book_exposure <= 10_000 * 2.0 + 1e-6, r.book_exposure
    print(f"levier notionnel borne ............. OK "
          f"({r.book_exposure / r.capital:.2f}x <= 2.00x)")


def test_une_position_par_instrument():
    r = RiskLayer(capital=10_000)
    d = r.evaluate(sig())
    r.register(sig(), d.size)
    d2 = r.evaluate(sig())
    assert not d2 and d2.reason is Rejection.ALREADY_OPEN
    print("une position par instrument ........ OK")


def test_coupe_circuit_s_arme_et_ne_se_desarme_pas():
    """LE test. Le coupe-circuit doit tenir même si l'equity remonte."""
    r = RiskLayer(capital=10_000, limits=RiskLimits(max_daily_loss_pct=0.03))
    r.start_day()

    d = r.evaluate(sig())
    r.register(sig(), d.size)
    r.close("EURUSD", -350.0)                       # -3,5 % : au-delà du seuil

    assert r.halted, "le coupe-circuit ne s'est pas armé"
    assert not r.evaluate(sig(symbol="XAUUSD")), "un ordre est passé après l'arrêt"
    assert r.evaluate(sig(symbol="XAUUSD")).reason is Rejection.DAILY_HALT

    # L'equity remonte : le coupe-circuit doit RESTER armé.
    r.capital += 1_000.0
    assert r.halted, "le coupe-circuit s'est désarmé tout seul — interdit"
    assert not r.evaluate(sig(symbol="DAX"))

    # Seul un appel explicite le rouvre.
    r.start_day()
    assert not r.halted
    assert r.evaluate(sig(symbol="DAX")).approved
    print("coupe-circuit tient après rebond ... OK")


def test_limites_incoherentes_refusees():
    """Une position seule ne peut pas dépasser le plafond du livre entier."""
    try:
        RiskLimits(max_position_pct=0.50, max_book_risk_pct=0.20)
        assert False, "limites incohérentes acceptées"
    except ValueError:
        pass
    print("limites incohérentes refusées ...... OK")


def test_refus_traces():
    """Un refus silencieux serait pire qu'une absence de contrôle."""
    r = RiskLayer(capital=10_000)
    for _ in range(2):
        bad = sig()
        object.__setattr__(bad, "stop", bad.entry)
        r.evaluate(bad)
    st = r.status()
    assert st["rejections"]["STOP_AT_ENTRY"] == 2, st
    print(f"refus comptés et tracés ............ OK ({st['rejections']})")


if __name__ == "__main__":
    for fn in (test_dimensionnement_par_le_risque, test_stop_large_reduit_la_taille,
               test_contrat_refuse_le_stop_incoherent_en_premier,
               test_couche_de_risque_en_seconde_barriere,
               test_plafond_de_risque_du_livre,
               test_plafond_de_levier,
               test_une_position_par_instrument,
               test_coupe_circuit_s_arme_et_ne_se_desarme_pas,
               test_limites_incoherentes_refusees, test_refus_traces):
        fn()

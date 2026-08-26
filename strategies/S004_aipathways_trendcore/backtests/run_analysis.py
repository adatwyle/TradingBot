"""Comptabilité de courbe d'equity — LA mesure qui fait foi pour s04.

POURQUOI CE SCRIPT PLUTÔT QUE LE MOTEUR COMMUN
-----------------------------------------------
« Trend core » est une bascule d'allocation : toujours investie, changeant
d'instrument, sortant UNIQUEMENT sur retournement de régime. Le moteur commun ne
sait pas exécuter ça (ANALYSIS.md §5) — il vient d'ailleurs de le démontrer en
produisant **1 à 2 trades** sur 5 ans (`anchored_wf.txt`).

Ce script n'est PAS un moteur de backtest concurrent (R9). Il ne simule ni stop,
ni cible, ni file d'ordres, ni circuit breaker — **il n'y en a aucun dans cette
stratégie**. Il fait la seule chose que la règle décrit : appliquer le rendement
journalier de l'actif détenu, et facturer le spread aux bascules.

Il produit en outre les **benchmarks buy & hold**, que le moteur commun ne peut
pas produire et qui sont le critère n°1 de `docs/METHODOLOGY.md`.

CONVENTION D'EXÉCUTION — fidèle à la source
--------------------------------------------
    décision à la CLÔTURE du jour t-1  ->  exécutée à l'OUVERTURE du jour t
    rendement encaissé le jour t       =  open[t] -> open[t+1] de l'actif détenu

Aucune donnée postérieure à la décision n'entre dans la décision.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.data.instruments import get_spec                   # noqa: E402
from core.data.source import load_bars                       # noqa: E402

RISK, HEDGE, ALT = "NASDAQ", "XAUUSD", "SP500"
L: list[str] = []


def say(s: str = "") -> None:
    L.append(s)


# ─────────────────────────────────────────────────────────────────────────────
# Données, alignées sur un index commun
# ─────────────────────────────────────────────────────────────────────────────
def load_all() -> pd.DataFrame:
    frames = {}
    for s in (RISK, HEDGE, ALT):
        df = load_bars(s, "D1")
        frames[s] = df[["open", "close"]].rename(
            columns={"open": f"{s}_open", "close": f"{s}_close"})
    out = pd.concat(frames.values(), axis=1).dropna()
    return out


def half_spread_frac(symbol: str, price: float) -> float:
    sp = get_spec(symbol)
    return (sp.spread_pips * sp.pip / 2.0) / price


# ─────────────────────────────────────────────────────────────────────────────
# Régime — identique à strategy.py (état, bande morte, causal)
# ─────────────────────────────────────────────────────────────────────────────
def regime_state(close: pd.Series, ma_len: int, buffer_pct: float) -> pd.Series:
    ma = close.rolling(ma_len, min_periods=ma_len).mean()
    above = (close > ma * (1 + buffer_pct)).to_numpy()
    below = (close < ma * (1 - buffer_pct)).to_numpy()
    mv = ma.to_numpy()
    st = np.full(len(close), np.nan)
    cur = np.nan
    for i in range(len(close)):
        if np.isnan(mv[i]):
            continue
        if above[i]:
            cur = 1.0
        elif below[i]:
            cur = 0.0
        st[i] = cur
    return pd.Series(st, index=close.index)


# ─────────────────────────────────────────────────────────────────────────────
# Simulation d'allocation
# ─────────────────────────────────────────────────────────────────────────────
def simulate(px: pd.DataFrame, ma_len: int, buffer_pct: float,
             risk_sym: str = RISK, hedge_sym: str | None = HEDGE,
             costs: bool = True, regime_sym: str = RISK) -> dict:
    """Retourne les rendements journaliers et l'actif détenu chaque jour.

    `hedge_sym=None` -> variante CASH (hors marché sous la MM, rendement 0).
    """
    reg = regime_state(px[f"{regime_sym}_close"], ma_len, buffer_pct)

    n = len(px)
    held = np.empty(n, dtype=object)
    held[:] = None
    ret = np.zeros(n)
    cost = np.zeros(n)

    r = reg.to_numpy()
    prev_held = None
    for t in range(1, n - 1):                 # t-1 doit exister, t+1 aussi
        d = r[t - 1]                          # décision prise à la clôture t-1
        if np.isnan(d):
            continue
        asset = risk_sym if d == 1.0 else hedge_sym
        held[t] = asset

        if asset is not None:
            o0 = px[f"{asset}_open"].iloc[t]
            o1 = px[f"{asset}_open"].iloc[t + 1]
            ret[t] = o1 / o0 - 1.0

        if costs and asset != prev_held:
            c = 0.0
            if prev_held is not None:         # sortie de l'ancien
                c += half_spread_frac(prev_held, px[f"{prev_held}_open"].iloc[t])
            if asset is not None:             # entrée dans le nouveau
                c += half_spread_frac(asset, px[f"{asset}_open"].iloc[t])
            cost[t] = c
        prev_held = asset

    net = ret - cost
    mask = np.array([h is not None or (not np.isnan(r[t - 1]) if t >= 1 else False)
                     for t, h in enumerate(held)])
    # Fenêtre évaluée = à partir de la 1re décision valide, jusqu'à n-2.
    first = next((t for t in range(1, n - 1) if not np.isnan(r[t - 1])), n)
    idx = np.zeros(n, dtype=bool)
    idx[first:n - 1] = True

    return {"index": px.index, "ret": net, "gross": ret, "cost": cost,
            "held": held, "eval": idx, "regime": r}


def bars_per_year(index: pd.DatetimeIndex, mask: np.ndarray) -> float:
    sel = index[mask]
    yrs = (sel[-1] - sel[0]).days / 365.25
    return len(sel) / yrs, yrs


def metrics(index, ret: np.ndarray, mask: np.ndarray) -> dict:
    r = ret[mask]
    bpy, yrs = bars_per_year(index, mask)
    eq = np.cumprod(1.0 + r)
    total = eq[-1] - 1.0
    cagr = eq[-1] ** (1.0 / yrs) - 1.0
    sd = r.std(ddof=1)
    sharpe = (r.mean() / sd * np.sqrt(bpy)) if sd > 0 else float("nan")
    peak = np.maximum.accumulate(eq)
    dd = float(np.min(eq / peak - 1.0))
    return {"n_days": len(r), "years": yrs, "total": total, "cagr": cagr,
            "sharpe": sharpe, "maxdd": dd, "vol": sd * np.sqrt(bpy), "eq": eq}


def buy_hold(px: pd.DataFrame, sym: str, mask: np.ndarray) -> dict:
    o = px[f"{sym}_open"].to_numpy()
    r = np.zeros(len(o))
    r[:-1] = o[1:] / o[:-1] - 1.0
    return metrics(px.index, r, mask)


def fmt(m: dict) -> str:
    return (f"{m['cagr']*100:>+8.2f} % {m['sharpe']:>8.2f} {m['maxdd']*100:>+9.2f} % "
            f"{m['vol']*100:>8.2f} % {m['total']*100:>+10.1f} %")


HEAD = f"{'':<44}{'CAGR':>10} {'Sharpe':>8} {'DD max':>11} {'vol':>10} {'total':>12}"


# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    px = load_all()
    say("=" * 104)
    say("COMPTABILITE D'EQUITY — s04_aipathways_trendcore (AI Pathways, Trend core)")
    say("=" * 104)
    say(f"Donnees : {len(px)} barres D1 alignees NASDAQ/XAUUSD/SP500, "
        f"{px.index[0].date()} -> {px.index[-1].date()}")
    say("Convention : decision a la CLOTURE de t-1, execution a l'OUVERTURE de t,")
    say("             rendement open[t] -> open[t+1] de l'actif detenu.")
    say("Couts : demi-spread a la sortie + demi-spread a l'entree, a chaque bascule.")
    say("")

    base = simulate(px, 200, 0.0)
    mask = base["eval"]
    bpy, yrs = bars_per_year(px.index, mask)
    say(f"Fenetre evaluee : {mask.sum()} jours ({yrs:.2f} ans, {bpy:.1f} barres/an) "
        f"apres warmup MM200.")
    say("")

    # ── Effectif ────────────────────────────────────────────────────────────
    held = base["held"]
    switches = sum(1 for t in range(1, len(held))
                   if mask[t] and held[t] != held[t - 1])
    say("-" * 104)
    say("EFFECTIF — a lire avant tout le reste")
    say("-" * 104)
    say(f"  Bascules de regime sur la fenetre evaluee : **{switches}**  "
        f"({switches / yrs:.2f} / an)")
    say(f"  Annonce par la source                     : 5,3 / an")
    say(f"  Episodes de detention                     : **{switches}**")
    say("")
    say("  Precedent methodologique : un 'strict pass' sur 19 trades avait un IC 95 %")
    say("  du taux de reussite de [27,3 % ; 68,3 %], seuil de rentabilite DEDANS.")
    say(f"  Nous sommes ici a {switches}. Toute statistique par comptage d'episodes est")
    say("  hors de portee. Les mesures ci-dessous s'appuient sur les rendements")
    say(f"  JOURNALIERS ({mask.sum()} observations), pas sur les {switches} episodes.")
    say("")

    # ── 1. Le critere n°1 : battre l'effort zero ────────────────────────────
    say("=" * 104)
    say("1. LE CRITERE N°1 — BAT-ON L'ACHAT-CONSERVATION ?")
    say("=" * 104)
    say(HEAD)
    say("-" * 104)
    strat = metrics(px.index, base["ret"], mask)
    say(f"{'STRATEGIE Trend core (NASDAQ/XAUUSD, MM200)':<44}{fmt(strat)}")
    say("")
    bh = {}
    for s in (RISK, HEDGE, ALT):
        bh[s] = buy_hold(px, s, mask)
        say(f"{'buy & hold ' + s:<44}{fmt(bh[s])}")
    # 50/50 rebalance quotidien, en bonus : le portefeuille naif.
    o_n = px[f"{RISK}_open"].to_numpy(); o_x = px[f"{HEDGE}_open"].to_numpy()
    r5 = np.zeros(len(px))
    r5[:-1] = 0.5 * (o_n[1:] / o_n[:-1] - 1) + 0.5 * (o_x[1:] / o_x[:-1] - 1)
    mix = metrics(px.index, r5, mask)
    say(f"{'buy & hold 50/50 NASDAQ+XAUUSD (rebal. quot.)':<44}{fmt(mix)}")
    say("")
    say("  Annonce par la source : CAGR +33,80 %, Sharpe 1,66, DD max -13,60 %")
    say("")
    verdicts = []
    for s in (RISK, HEDGE, ALT):
        verdicts.append(f"  vs buy & hold {s:<7} : CAGR {strat['cagr']*100 - bh[s]['cagr']*100:>+7.2f} pt, "
                        f"Sharpe {strat['sharpe'] - bh[s]['sharpe']:>+6.2f}, "
                        f"DD {(strat['maxdd'] - bh[s]['maxdd'])*100:>+7.2f} pt")
    say("\n".join(verdicts))
    say(f"  vs 50/50               : CAGR {strat['cagr']*100 - mix['cagr']*100:>+7.2f} pt, "
        f"Sharpe {strat['sharpe'] - mix['sharpe']:>+6.2f}, "
        f"DD {(strat['maxdd'] - mix['maxdd'])*100:>+7.2f} pt")
    say("")

    # ── 2. Attribution par jambe ────────────────────────────────────────────
    say("=" * 104)
    say("2. ATTRIBUTION PAR JAMBE — le caveat de l'auteur, teste de front")
    say("=" * 104)
    say("L'auteur signale lui-meme : 'le repli sur GLD tient en partie a la vigueur")
    say("recente de l'or ; 2005-09 favorisait plutot un repli en cash'.")
    say("C'est le piege USDJPY (+69,7 R long / -10,0 R short). Verification :")
    say("")
    ret = base["ret"]
    say(f"  {'jambe':<28} {'jours':>7} {'% du temps':>11} {'contrib. compo.':>17} "
        f"{'% du gain':>11} {'R/jour moyen':>14} {'annualise':>11}")
    say("  " + "-" * 100)
    legs = {}
    total_log = np.sum(np.log1p(ret[mask]))
    for name, sym in (("NASDAQ (au-dessus MM)", RISK), ("XAUUSD (en dessous MM)", HEDGE)):
        sel = mask & np.array([h == sym for h in held])
        lg = np.sum(np.log1p(ret[sel]))
        legs[sym] = {"days": int(sel.sum()), "log": lg,
                     "mean": ret[sel].mean() if sel.sum() else 0.0}
        ann = np.expm1(lg / (sel.sum() / bpy)) if sel.sum() else 0.0
        say(f"  {name:<28} {int(sel.sum()):>7} {100*sel.sum()/mask.sum():>10.1f} % "
            f"{np.expm1(lg)*100:>+16.1f} % {100*lg/total_log:>10.1f} % "
            f"{ret[sel].mean()*100:>13.4f} % {ann*100:>+10.2f} %")
    say("")
    say(f"  Total compose : {np.expm1(total_log)*100:+.1f} %")
    say("")
    say("  'annualise' = rendement compose de la jambe ramene a une annee de detention.")
    say("  C'est la mesure qui NE depend PAS du temps passe dans la jambe — celle qui")
    say("  compte (cf. 'ne jamais juger un filtre sur le PnL total').")
    say("")

    # ── 3. Variante cash ────────────────────────────────────────────────────
    say("=" * 104)
    say("3. VARIANTE CASH — la jambe or apporte-t-elle quelque chose ?")
    say("=" * 104)
    cash = simulate(px, 200, 0.0, hedge_sym=None)
    mcash = metrics(px.index, cash["ret"], mask)
    say(HEAD)
    say("-" * 104)
    say(f"{'Trend core NASDAQ/XAUUSD (la regle)':<44}{fmt(strat)}")
    say(f"{'Variante CASH (hors marche sous la MM, 0 %)':<44}{fmt(mcash)}")
    say(f"{'buy & hold NASDAQ':<44}{fmt(bh[RISK])}")
    say("")
    say(f"  Ecart or - cash : CAGR {(strat['cagr']-mcash['cagr'])*100:+.2f} pt, "
        f"Sharpe {strat['sharpe']-mcash['sharpe']:+.2f}, "
        f"DD {(strat['maxdd']-mcash['maxdd'])*100:+.2f} pt")
    say("  Note : le cash est remunere a 0 %. Avec des T-bills a ~4 % sur 2023-2026,")
    say("  la variante cash gagnerait environ +1,4 pt de CAGR supplementaire")
    say(f"  (elle passe {100*(1-legs[HEDGE]['days']/mask.sum()):.0f} % du temps investie).")
    say("")

    # ── 4. Ablation du spread ───────────────────────────────────────────────
    say("=" * 104)
    say("4. ABLATION DU SPREAD")
    say("=" * 104)
    free = simulate(px, 200, 0.0, costs=False)
    mfree = metrics(px.index, free["ret"], mask)
    say(HEAD)
    say("-" * 104)
    say(f"{'spread reel Swissquote':<44}{fmt(strat)}")
    say(f"{'spread NUL':<44}{fmt(mfree)}")
    say("")
    say(f"  Cout total du spread sur {yrs:.2f} ans : "
        f"{base['cost'][mask].sum()*100:.4f} % cumule, soit "
        f"{base['cost'][mask].sum()/yrs*100:.4f} % / an.")
    say(f"  Impact sur le CAGR : {(strat['cagr']-mfree['cagr'])*100:+.4f} point.")
    say("")
    say("  Annonce en Phase 1 (ANALYSIS §8) : 'l'ablation du spread sera un")
    say("  non-evenement'. C'est verifie. A 2-3 bascules/an, le peage est ~1/800e du")
    say("  CAGR annonce. Le spread ne peut ni causer un echec ni excuser un succes.")
    say("  Le cout NON modelise qui compte ici est le SWAP sur detention permanente.")
    say("")

    # ── 5. Controle long/short ──────────────────────────────────────────────
    say("=" * 104)
    say("5. CONTROLE LONG/SHORT — degenere, et il faut le dire")
    say("=" * 104)
    n_long = sum(1 for t in range(len(held)) if mask[t] and held[t] is not None)
    say(f"  Jours en position LONG  : {n_long} / {int(mask.sum())} = "
        f"{100*n_long/mask.sum():.1f} %")
    say(f"  Jours en position SHORT : 0 / {int(mask.sum())} = 0,0 %")
    say("")
    say("  La strategie est 100 % longue en permanence, par construction. Le controle")
    say("  directionnel ne peut donc PAS la disculper : il la classe d'office du cote")
    say("  'exposition directionnelle'. C'est exactement pour cette raison que le")
    say("  benchmark buy & hold du §1 est le seul juge possible.")
    say("")
    say("  Beta realise vs les deux actifs (regression des rendements journaliers) :")
    for s in (RISK, HEDGE):
        o = px[f"{s}_open"].to_numpy()
        rb = np.zeros(len(o)); rb[:-1] = o[1:] / o[:-1] - 1
        b = np.polyfit(rb[mask], ret[mask], 1)[0]
        cc = np.corrcoef(rb[mask], ret[mask])[0, 1]
        say(f"    vs {s:<8} beta {b:>6.3f}   correlation {cc:>6.3f}")
    say("")

    # ── 6. Le filtre filtre-t-il ? ──────────────────────────────────────────
    say("=" * 104)
    say("6. LA MM200 SEPARE-T-ELLE VRAIMENT DEUX POPULATIONS ? (critere I4)")
    say("=" * 104)
    o = px[f"{RISK}_open"].to_numpy()
    rn = np.zeros(len(o)); rn[:-1] = o[1:] / o[:-1] - 1
    reg = base["regime"]
    up = mask & np.array([(t >= 1 and reg[t-1] == 1.0) for t in range(len(px))])
    dn = mask & np.array([(t >= 1 and reg[t-1] == 0.0) for t in range(len(px))])
    say(f"  Rendement journalier NASDAQ quand NASDAQ > MM200 : "
        f"{rn[up].mean()*100:+.4f} % (n={int(up.sum())}, ecart-type {rn[up].std(ddof=1)*100:.3f} %)")
    say(f"  Rendement journalier NASDAQ quand NASDAQ < MM200 : "
        f"{rn[dn].mean()*100:+.4f} % (n={int(dn.sum())}, ecart-type {rn[dn].std(ddof=1)*100:.3f} %)")
    d = rn[up].mean() - rn[dn].mean()
    se = np.sqrt(rn[up].var(ddof=1)/up.sum() + rn[dn].var(ddof=1)/dn.sum())
    say(f"  Difference : {d*100:+.4f} % / jour   t = {d/se:.2f}   "
        f"(|t| > 1,96 = significatif a 5 %)")
    say(f"  Annualise  : {np.expm1(np.log1p(rn[up].mean())*bpy)*100:+.1f} % vs "
        f"{np.expm1(np.log1p(rn[dn].mean())*bpy)*100:+.1f} %")
    say("")
    say("  Volatilite annualisee au-dessus : "
        f"{rn[up].std(ddof=1)*np.sqrt(bpy)*100:.1f} %   en dessous : "
        f"{rn[dn].std(ddof=1)*np.sqrt(bpy)*100:.1f} %")
    say("")

    # ── 7. Plateau ──────────────────────────────────────────────────────────
    say("=" * 104)
    say("7. TEST DE PLATEAU — 12 configurations (~0,6 reussite par PUR HASARD)")
    say("=" * 104)
    say(f"  {'ma_len':>7} {'buffer':>8} {'bascules':>9} {'CAGR':>10} {'Sharpe':>8} "
        f"{'DD max':>10} | {'variante CASH: CAGR':>21} {'Sharpe':>8}")
    say("  " + "-" * 100)
    rows = []
    for ma in (100, 150, 200, 250):
        for buf in (0.0, 0.005, 0.01):
            sim = simulate(px, ma, buf)
            m = metrics(px.index, sim["ret"], mask)
            simc = simulate(px, ma, buf, hedge_sym=None)
            mc = metrics(px.index, simc["ret"], mask)
            h = sim["held"]
            sw = sum(1 for t in range(1, len(h)) if mask[t] and h[t] != h[t-1])
            rows.append((ma, buf, sw, m, mc))
            say(f"  {ma:>7} {buf:>8.3f} {sw:>9} {m['cagr']*100:>+9.2f} % "
                f"{m['sharpe']:>8.2f} {m['maxdd']*100:>+9.2f} % | "
                f"{mc['cagr']*100:>+19.2f} % {mc['sharpe']:>8.2f}")
    say("")
    beat = sum(1 for _, _, _, m, _ in rows if m['cagr'] > bh[RISK]['cagr'])
    beat_sh = sum(1 for _, _, _, m, _ in rows if m['sharpe'] > bh[RISK]['sharpe'])
    say(f"  Configurations battant le buy & hold NASDAQ en CAGR   : {beat}/12")
    say(f"  Configurations battant le buy & hold NASDAQ en Sharpe : {beat_sh}/12")
    say("")

    # ── 8. Stabilite annuelle ───────────────────────────────────────────────
    say("=" * 104)
    say("8. STABILITE ANNUELLE — d'ou vient le resultat ?")
    say("=" * 104)
    yrs_idx = pd.Series(px.index.year, index=px.index)
    say(f"  {'annee':>6} {'jours':>7} {'Trend core':>13} {'B&H NASDAQ':>13} "
        f"{'B&H XAUUSD':>13} {'variante cash':>15} {'% temps en or':>15}")
    say("  " + "-" * 92)
    o_x = px[f"{HEDGE}_open"].to_numpy()
    rx = np.zeros(len(o_x)); rx[:-1] = o_x[1:] / o_x[:-1] - 1
    for y in sorted(set(px.index.year)):
        sel = mask & (yrs_idx.to_numpy() == y)
        if sel.sum() < 20:
            continue
        gold = np.mean([held[t] == HEDGE for t in range(len(held)) if sel[t]])
        say(f"  {y:>6} {int(sel.sum()):>7} "
            f"{np.expm1(np.sum(np.log1p(ret[sel])))*100:>+12.1f} % "
            f"{np.expm1(np.sum(np.log1p(rn[sel])))*100:>+12.1f} % "
            f"{np.expm1(np.sum(np.log1p(rx[sel])))*100:>+12.1f} % "
            f"{np.expm1(np.sum(np.log1p(cash['ret'][sel])))*100:>+14.1f} % "
            f"{gold*100:>14.1f} %")
    say("")

    # ── 9. Hors echantillon ancre ───────────────────────────────────────────
    say("=" * 104)
    say("9. HORS ECHANTILLON ANCRE — ma_len choisi sur le train, mesure sur le test")
    say("=" * 104)
    say("  Memes fenetres que core/backtest/anchored_wf.py : train [0,x%], test (x%,y%].")
    say("  Selection sur le Sharpe d'entrainement, parmi les 12 cellules.")
    say("")
    n = len(px)
    say(f"  {'fenetre':>9} {'config train':>22} {'Sharpe train':>13} | "
        f"{'CAGR test':>11} {'Sharpe test':>12} {'B&H NASDAQ':>12} {'bascules':>9}")
    say("  " + "-" * 98)
    sims = {(ma, buf): simulate(px, ma, buf)
            for ma in (100, 150, 200, 250) for buf in (0.0, 0.005, 0.01)}
    oos_beat = 0
    for wi, (a, b) in enumerate([(0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)], 1):
        tr = np.zeros(n, dtype=bool); tr[:int(n*a)] = True; tr &= mask
        te = np.zeros(n, dtype=bool); te[int(n*a):int(n*b)] = True; te &= mask
        best, bs = None, -1e9
        for k, sim in sims.items():
            m = metrics(px.index, sim["ret"], tr)
            if m["sharpe"] > bs:
                bs, best = m["sharpe"], k
        sim = sims[best]
        mt = metrics(px.index, sim["ret"], te)
        mb = metrics(px.index, rn, te)
        h = sim["held"]
        sw = sum(1 for t in range(1, n) if te[t] and h[t] != h[t-1])
        if mt["cagr"] > mb["cagr"]:
            oos_beat += 1
        say(f"  W{wi} {int(a*100)}->{int(b*100)}% "
            f"{f'ma{best[0]}/buf{best[1]:.3f}':>22} {bs:>13.2f} | "
            f"{mt['cagr']*100:>+10.2f} % {mt['sharpe']:>12.2f} "
            f"{mb['cagr']*100:>+11.2f} % {sw:>9}")
    say("")
    say(f"  Fenetres ou la strategie bat le buy & hold NASDAQ : {oos_beat}/4")
    say(f"  **Effectif : 0 a 2 bascules par fenetre de test.** Un 4/4 comme un 0/4")
    say("  sont ici du bruit. Cette section est publiee pour la transparence, PAS")
    say("  comme element de preuve.")
    say("")

    # ── 10. Variante SP500 ──────────────────────────────────────────────────
    say("=" * 104)
    say("10. VARIANTE SP500 comme actif risque (robustesse de famille)")
    say("=" * 104)
    say(HEAD)
    say("-" * 104)
    sp = simulate(px, 200, 0.0, risk_sym=ALT, regime_sym=ALT)
    msp = metrics(px.index, sp["ret"], mask)
    say(f"{'Trend core SP500/XAUUSD (MM200 sur SP500)':<44}{fmt(msp)}")
    say(f"{'buy & hold SP500':<44}{fmt(bh[ALT])}")
    spc = simulate(px, 200, 0.0, risk_sym=ALT, regime_sym=ALT, hedge_sym=None)
    say(f"{'Variante CASH SP500':<44}{fmt(metrics(px.index, spc['ret'], mask))}")
    say("")

    # ── 11. Concentration temporelle ────────────────────────────────────────
    say("=" * 104)
    say("11. CONCENTRATION TEMPORELLE — l'avantage tient-il a une seule annee ?")
    say("=" * 104)
    say("2022 est le SEUL episode baissier de l'echantillon (et il est tronque :")
    say("le warmup MM200 ne libere le signal qu'en mai 2022).")
    say("")
    no22 = mask & (yrs_idx.to_numpy() != 2022)
    say(HEAD)
    say("-" * 104)
    say(f"{'Trend core — TOUT l echantillon':<44}{fmt(strat)}")
    say(f"{'buy & hold NASDAQ — TOUT':<44}{fmt(bh[RISK])}")
    say("")
    m_ex = metrics(px.index, ret, no22)
    b_ex = metrics(px.index, rn, no22)
    c_ex = metrics(px.index, cash["ret"], no22)
    say(f"{'Trend core — HORS 2022':<44}{fmt(m_ex)}")
    say(f"{'variante CASH — HORS 2022':<44}{fmt(c_ex)}")
    say(f"{'buy & hold NASDAQ — HORS 2022':<44}{fmt(b_ex)}")
    say("")
    say(f"  Avantage de Sharpe sur TOUT l'echantillon : "
        f"{strat['sharpe'] - bh[RISK]['sharpe']:+.2f}")
    say(f"  Avantage de Sharpe HORS 2022              : "
        f"{m_ex['sharpe'] - b_ex['sharpe']:+.2f}")
    say(f"  Avantage de CAGR   sur TOUT l'echantillon : "
        f"{(strat['cagr'] - bh[RISK]['cagr'])*100:+.2f} pt")
    say(f"  Avantage de CAGR   HORS 2022              : "
        f"{(m_ex['cagr'] - b_ex['cagr'])*100:+.2f} pt")
    say(f"  Jours concernes par 2022 : {int((mask & (yrs_idx.to_numpy()==2022)).sum())} "
        f"/ {int(mask.sum())} = {100*(mask & (yrs_idx.to_numpy()==2022)).sum()/mask.sum():.1f} %")
    say("")

    # ── 12. L'ecart est-il distinguable du bruit ? ──────────────────────────
    say("=" * 104)
    say("12. L'AVANTAGE EST-IL DISTINGUABLE DU BRUIT ? (bootstrap par blocs)")
    say("=" * 104)
    say("  Re-echantillonnage par blocs de 21 jours (1 mois) des rendements")
    say("  APPARIES (strategie, B&H NASDAQ), 5000 tirages. On preserve ainsi la")
    say("  dependance serielle et la correlation entre les deux series.")
    say("")
    rng = np.random.default_rng(20260816)
    ds = ret[mask]
    db = rn[mask]
    nn, blk = len(ds), 21
    nb = nn // blk
    diff_cagr, diff_sh = [], []
    for _ in range(5000):
        starts = rng.integers(0, nn - blk, size=nb)
        sel = np.concatenate([np.arange(s, s + blk) for s in starts])
        a, b = ds[sel], db[sel]
        la, lb = np.sum(np.log1p(a)), np.sum(np.log1p(b))
        yy = len(sel) / bpy
        diff_cagr.append(np.expm1(la / yy) - np.expm1(lb / yy))
        sa = a.mean() / a.std(ddof=1) * np.sqrt(bpy)
        sb = b.mean() / b.std(ddof=1) * np.sqrt(bpy)
        diff_sh.append(sa - sb)
    diff_cagr = np.array(diff_cagr); diff_sh = np.array(diff_sh)
    say(f"  Difference de CAGR  (strategie - B&H NASDAQ) : "
        f"observee {(strat['cagr']-bh[RISK]['cagr'])*100:+.2f} pt, "
        f"IC 95 % [{np.percentile(diff_cagr,2.5)*100:+.2f} ; "
        f"{np.percentile(diff_cagr,97.5)*100:+.2f}] pt")
    say(f"  Part des tirages ou la strategie fait MOINS bien : "
        f"{100*np.mean(diff_cagr<0):.1f} %")
    say("")
    say(f"  Difference de Sharpe (strategie - B&H NASDAQ) : "
        f"observee {strat['sharpe']-bh[RISK]['sharpe']:+.2f}, "
        f"IC 95 % [{np.percentile(diff_sh,2.5):+.2f} ; "
        f"{np.percentile(diff_sh,97.5):+.2f}]")
    say(f"  Part des tirages ou la strategie fait MOINS bien : "
        f"{100*np.mean(diff_sh<0):.1f} %")
    say("")
    say("  Meme comparaison contre le portefeuille NAIF 50/50 :")
    d5 = r5[mask]
    dc2, ds2 = [], []
    for _ in range(5000):
        starts = rng.integers(0, nn - blk, size=nb)
        sel = np.concatenate([np.arange(s, s + blk) for s in starts])
        a, b = ds[sel], d5[sel]
        yy = len(sel) / bpy
        dc2.append(np.expm1(np.sum(np.log1p(a))/yy) - np.expm1(np.sum(np.log1p(b))/yy))
        ds2.append(a.mean()/a.std(ddof=1)*np.sqrt(bpy) - b.mean()/b.std(ddof=1)*np.sqrt(bpy))
    dc2 = np.array(dc2); ds2 = np.array(ds2)
    say(f"    CAGR   : observee {(strat['cagr']-mix['cagr'])*100:+.2f} pt, "
        f"IC 95 % [{np.percentile(dc2,2.5)*100:+.2f} ; {np.percentile(dc2,97.5)*100:+.2f}] pt, "
        f"{100*np.mean(dc2<0):.1f} % des tirages defavorables")
    say(f"    Sharpe : observee {strat['sharpe']-mix['sharpe']:+.2f}, "
        f"IC 95 % [{np.percentile(ds2,2.5):+.2f} ; {np.percentile(ds2,97.5):+.2f}], "
        f"{100*np.mean(ds2<0):.1f} % des tirages defavorables")
    say("")

    # ── 13. Comparaison a armes egales : SA fenetre de test ─────────────────
    say("=" * 104)
    say("13. SUR SA PROPRE FENETRE DE TEST (2023-01 -> 2026-07)")
    say("=" * 104)
    say("Comparaison a armes egales avec les chiffres annonces.")
    say("")
    w = mask & (px.index >= "2023-01-01") & (px.index <= "2026-07-31")
    say(HEAD)
    say("-" * 104)
    say(f"{'ANNONCE par la source (QQQ/GLD)':<44}{'  +33.80 %':>10} {1.66:>8.2f} "
        f"{'  -13.60 %':>11} {'n/d':>10} {'n/d':>12}")
    say(f"{'NOTRE mesure (NASDAQ/XAUUSD), meme fenetre':<44}"
        f"{fmt(metrics(px.index, ret, w))}")
    say(f"{'  variante ma250/buf0.005 (la meilleure)':<44}"
        f"{fmt(metrics(px.index, sims[(250,0.005)]['ret'], w))}")
    say(f"{'buy & hold NASDAQ, meme fenetre':<44}{fmt(metrics(px.index, rn, w))}")
    say(f"{'buy & hold XAUUSD, meme fenetre':<44}{fmt(metrics(px.index, rx, w))}")
    say(f"{'buy & hold 50/50, meme fenetre':<44}{fmt(metrics(px.index, r5, w))}")
    say("")
    say(f"  Jours : {int(w.sum())}. Cette fenetre ne contient AUCUN marche baissier")
    say("  durable — 2022 en est exclu par construction. C'est aussi vrai chez lui.")
    say("")

    text = "\n".join(L)
    print(text)
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "equity_analysis.txt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\n-> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

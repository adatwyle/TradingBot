"""
COT (Commitment of Traders, CFTC) — positionnement des « gros spéculateurs ».

Construit, pour chaque devise, la série hebdomadaire de position nette des
NON-COMMERCIALS (rapport legacy « futures only ») :

    net = (noncomm long - noncomm short) / open interest

et son PERCENTILE GLISSANT sur 3 ans (156 rapports).

ANTI-FUITE — la règle non négociable
-------------------------------------
Le rapport porte sur le mardi (« as of date ») mais n'est PUBLIÉ que le
vendredi à 15h30 ET. La donnée du mardi n'est donc utilisable qu'à partir de :

    available_from = as_of (mardi) + 3 jours à 20:30 UTC (~15h30 ET)
                   = vendredi 22:30 heure serveur MT5 (UTC+2)

Toute jointure avec les barres passe par `merge_asof` sur `available_from`,
jamais sur la date du rapport. (En pratique, le détecteur n'entre que du lundi
au jeudi : le rapport actif est donc toujours celui du vendredi PRÉCÉDENT.)

Sources : fichiers annuels https://www.cftc.gov/files/dea/history/deacotYYYY.zip
(archivés dans le scratchpad de session, format legacy « Futures Only »).

Sortie : judge/cot_percentiles.csv — colonnes :
    available_from, currency, net_oi, pct3y (0-100)
"""
from __future__ import annotations

import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
COT_RAW_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "cot_raw")
OUT = os.path.join(HERE, "cot_percentiles.csv")

# Marchés legacy CME -> devise. Le dollar est couvert par l'indice ICE.
MARKETS = {
    "EURO FX - CHICAGO MERCANTILE EXCHANGE": "EUR",
    "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE": "JPY",
    "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE": "CHF",
    "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE": "GBP",
    "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE": "GBP",
    "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE": "AUD",
    "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE": "CAD",
    "USD INDEX - ICE FUTURES U.S.": "USD",
    "U.S. DOLLAR INDEX - ICE FUTURES U.S.": "USD",
}

ROLL = 156          # 3 ans de rapports hebdomadaires
MIN_ROLL = 52       # percentile calculé dès 1 an d'historique


def load_year(path: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"))
    df.columns = [c.strip() for c in df.columns]
    cols = {
        "Market and Exchange Names": "market",
        "As of Date in Form YYYY-MM-DD": "as_of",
        "Open Interest (All)": "oi",
        "Noncommercial Positions-Long (All)": "nc_long",
        "Noncommercial Positions-Short (All)": "nc_short",
    }
    df = df[list(cols)].rename(columns=cols)
    df["market"] = df["market"].str.strip()
    return df


def main() -> None:
    frames = []
    for fn in sorted(os.listdir(COT_RAW_DIR)):
        if fn.startswith("deacot") and fn.endswith(".zip"):
            frames.append(load_year(os.path.join(COT_RAW_DIR, fn)))
    raw = pd.concat(frames, ignore_index=True)
    raw = raw[raw["market"].isin(MARKETS)].copy()
    raw["currency"] = raw["market"].map(MARKETS)
    raw["as_of"] = pd.to_datetime(raw["as_of"])
    raw["net_oi"] = (raw["nc_long"] - raw["nc_short"]) / raw["oi"].replace(0, np.nan)
    raw = (raw.dropna(subset=["net_oi"])
              .sort_values(["currency", "as_of"])
              .drop_duplicates(["currency", "as_of"]))

    # Publication : vendredi 15h30 ET = mardi as_of + 3 jours, 20:30 UTC.
    # Les barres MT5 sont en heure serveur UTC+2 -> vendredi 22:30 serveur.
    raw["available_from"] = raw["as_of"] + pd.Timedelta(days=3, hours=22, minutes=30)

    def pct_rank(s: pd.Series) -> pd.Series:
        out = np.full(len(s), np.nan)
        v = s.to_numpy()
        for i in range(len(v)):
            lo = max(0, i - ROLL + 1)
            w = v[lo:i + 1]
            if len(w) >= MIN_ROLL:
                out[i] = 100.0 * (np.sum(w < v[i]) + 0.5 * np.sum(w == v[i])) / len(w)
        return pd.Series(out, index=s.index)

    raw["pct3y"] = raw.groupby("currency")["net_oi"].transform(pct_rank)
    out = raw[["available_from", "as_of", "currency", "net_oi", "pct3y"]].dropna(subset=["pct3y"])
    out.to_csv(OUT, index=False)
    print(f"[OK] {OUT} — {len(out)} lignes, "
          f"{out['currency'].nunique()} devises, "
          f"{out['as_of'].min().date()} -> {out['as_of'].max().date()}")
    print(out.groupby("currency")["as_of"].agg(["min", "max", "count"]))


if __name__ == "__main__":
    main()

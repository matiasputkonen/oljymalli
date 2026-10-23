#!/usr/bin/env python3
"""Rebuild derived daily files from raw sources: data/futures_daily.csv, data/hormuz_daily.csv, data/raw/cftc_wti_cot.csv, data/raw/cftc_wti_cot (legacy for long panel via deacot zips handled in long_panel.py)."""
import os, glob, zipfile, numpy as np, pandas as pd
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); RAW = f"{ROOT}/data/raw"; R3 = f"{ROOT}/data/raw3"; OUT = f"{ROOT}/data"
def rd(name):
    d = pd.read_csv(f"{R3}/eia_{name}.csv", parse_dates=["date"]); return d.set_index("date")["value"].astype(float).sort_index()
# ---- futures / spot daily ----
cl1, cl2, cl3, cl4 = rd("cl1"), rd("cl2"), rd("cl3"), rd("cl4"); ho1, rb1, ng1 = rd("ho1"), rd("rb1"), rd("ng1"); brent = rd("brent_spot"); wti_spot = rd("wti_spot")
cl1 = cl1.combine_first(wti_spot[wti_spot.index > cl1.index.max()])
px = pd.concat([cl1.rename("cl1"), cl2.rename("cl2"), cl3.rename("cl3"), cl4.rename("cl4"), ho1.rename("ho1"), rb1.rename("rb1"), ng1.rename("ng1"), brent.rename("brent")], axis=1).loc["2010":]
px["m1m2"] = px.cl1 - px.cl2; px["m1m4"] = px.cl1 - px.cl4; px["m1m4_pct"] = px.m1m4 / px.cl1 * 100; px["ho_crack"] = px.ho1 * 42 - px.cl1; px["rb_crack"] = px.rb1 * 42 - px.cl1
px.index.name = "date"; px.to_csv(f"{OUT}/futures_daily.csv"); print("futures_daily:", px.index.max().date(), "cl1", px.cl1.dropna().iloc[-1], "brent", px.brent.dropna().iloc[-1])
# ---- Hormuz daily ----
pw = pd.read_csv(f"{R3}/portwatch_chokepoints.csv", parse_dates=["date"]); hz = pw[pw.portname == "Strait of Hormuz"].set_index("date").sort_index()
hz = hz[~hz.index.duplicated(keep="last")]; hz[["n_tanker", "n_total", "capacity_tanker"]].to_csv(f"{OUT}/hormuz_daily.csv"); print("hormuz_daily:", hz.index.max().date(), "n_tanker", int(hz.n_tanker.iloc[-1]), "7d mean", round(hz.n_tanker.tail(7).mean(), 1))
# ---- CFTC disaggregated: WTI (067651) managed money / producer-merchant ----
rows = []
for z in sorted(glob.glob(f"{RAW}/cftc_*.zip")):
    try:
        zf = zipfile.ZipFile(z); name = [n for n in zf.namelist() if n.lower().endswith(".txt")][0]; df = pd.read_csv(zf.open(name), low_memory=False)
        d = df[df["CFTC_Contract_Market_Code"].astype(str).str.strip() == "067651"]
        rows.append(pd.DataFrame({"date": pd.to_datetime(d["Report_Date_as_YYYY-MM-DD"]), "mm_long": d["M_Money_Positions_Long_All"].astype(float), "mm_short": d["M_Money_Positions_Short_All"].astype(float), "oi": d["Open_Interest_All"].astype(float),
                                  "pm_long": d["Prod_Merc_Positions_Long_All"].astype(float), "pm_short": d["Prod_Merc_Positions_Short_All"].astype(float)}))
    except Exception as e: print("cftc zip fail", z, e)
cot = pd.concat(rows).drop_duplicates("date").sort_values("date"); cot["mm_net"] = cot.mm_long - cot.mm_short
cot = cot[cot.date >= "2015-01-01"]; cot.to_csv(f"{RAW}/cftc_wti_cot.csv", index=False); print("cot:", cot.date.max().date(), "mm_net", int(cot.mm_net.iloc[-1]))

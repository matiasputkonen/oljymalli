#!/usr/bin/env python3
"""Build a 2006–2026 monthly panel of the model variables and compare short (2015→) vs long (2006→) fair-value models."""
import json, zipfile, glob, numpy as np, pandas as pd, statsmodels.api as sm, warnings; warnings.filterwarnings("ignore")
RAW = "/home/claude/oil/data/raw"; R3 = "/home/claude/oil/data/raw3"; D = "/home/claude/oil/data"
idx = pd.date_range("2006-01-01", pd.Timestamp.today().strftime("%Y-%m-01"), freq="MS")
def fredm(n):
    d = pd.read_csv(f"{RAW}/fred_{n}.csv", parse_dates=["date"]); s = d.set_index("date")["value"].astype(float); s.index = s.index.to_period("M").to_timestamp(); return s
def fredd_m(n):
    d = pd.read_csv(f"{RAW}/fred_{n}.csv", parse_dates=["date"]); return d.set_index("date")["value"].astype(float).dropna().resample("MS").mean()
def eia_w(n):
    d = pd.read_csv(f"{RAW}/eia_{n}.csv", parse_dates=["date"]).dropna(); return d.set_index("date")["value"].astype(float).resample("MS").mean()
P = pd.DataFrame(index=idx)
P["brent"] = fredm("Brent_m").reindex(idx); P["wti"] = fredm("WTI_m").reindex(idx)
P["usd_broad"] = fredd_m("DollarBroad_d").reindex(idx)
P["us_total_stocks"] = (eia_w("WTTSTUS1w") / 1000).reindex(idx); P["us_crude_stocks"] = (eia_w("WCESTUS1w") / 1000).reindex(idx)
P["cushing"] = (eia_w("Cushing_w") / 1000).reindex(idx); P["us_spr"] = (eia_w("WCSSTUS1w") / 1000).reindex(idx); P["us_prod"] = (eia_w("WCRFPUS2w") / 1000).reindex(idx)
# S&P 500 monthly (Yahoo), fallback FRED
j = json.load(open(f"{R3}/yahoo_%5EGSPC_m.json"))["chart"]["result"][0]
sp = pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s")).dropna(); sp.index = sp.index.to_period("M").to_timestamp(); sp = sp[~sp.index.duplicated(keep="last")]
P["sp500"] = sp.reindex(idx)
# STEO splice 2006-2026 for OPEC production, world balance, OECD stocks
def steo_sheet(path):
    x = pd.read_excel(path, sheet_name="3atab", header=None)
    yrow = x.iloc[2, 2:].tolist(); mrow = x.iloc[3, 2:].tolist(); dates = []; cur = None
    for y, m in zip(yrow, mrow):
        if isinstance(y, (int, float)) and not pd.isna(y): cur = int(y)
        if cur is None or not isinstance(m, str): dates.append(None); continue
        dates.append(pd.Timestamp(year=cur, month=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(m[:3]) + 1, day=1))
    rows = {}
    for i in range(4, x.shape[0]):
        code = x.iloc[i, 0]
        if isinstance(code, str) and code.strip():
            vals = pd.to_numeric(x.iloc[i, 2:2 + len(dates)].values, errors="coerce")
            rows[code.strip()] = pd.Series([v for v, d in zip(vals, dates) if d is not None], index=[d for d in dates if d is not None])
    return rows
files = [(f"{R3}/steo_jan08_base.xls", "2006-01", "2007-12"), (f"{R3}/steo_jan10_base.xls", "2008-01", "2009-12"), (f"{R3}/steo_jan12_base.xls", "2010-01", "2011-12"), (f"{R3}/steo_jan14_base.xlsx", "2012-01", "2013-12"),
         (f"{RAW}/steo_jan16_base.xlsx", "2014-01", "2015-12"), (f"{RAW}/steo_jan18_base.xlsx", "2016-01", "2017-12"), (f"{RAW}/steo_jan20_base.xlsx", "2018-01", "2019-12"),
         (f"{RAW}/steo_jan22_base.xlsx", "2020-01", "2021-12"), (f"{RAW}/steo_jan24_base.xlsx", "2022-01", "2023-12"), (f"{RAW}/STEO_m.xlsx", "2024-01", pd.Timestamp.today().strftime("%Y-%m"))]
steo = {}
for fn, a, b in files:
    rows = steo_sheet(fn)
    for code in ["papr_opec", "papr_world", "patc_world", "t3_stchange_world", "pasc_oecd_t3", "pasc_oecd"]:
        if code in rows: steo.setdefault(code, []).append(rows[code].loc[a:b])
    print(fn.split("/")[-1], "has:", [c for c in ["papr_opec", "papr_world", "patc_world", "pasc_oecd_t3", "pasc_oecd"] if c in rows])
steo = {k: pd.concat(v).sort_index() for k, v in steo.items()}; steo = {k: v[~v.index.duplicated(keep="last")] for k, v in steo.items()}
P["opec_prod"] = steo["papr_opec"].reindex(idx); P["world_balance"] = (steo["papr_world"] - steo["patc_world"]).reindex(idx)
oecd = steo.get("pasc_oecd_t3", pd.Series(dtype=float)); P["oecd_stocks"] = oecd.reindex(idx)
# COT legacy non-commercial net, NYMEX WTI (067651)
cot = []
for z in sorted(glob.glob(f"{R3}/deacot*.zip")):
    try:
        zf = zipfile.ZipFile(z); name = [n for n in zf.namelist() if n.lower().endswith(".txt")][0]
        df = pd.read_csv(zf.open(name), low_memory=False)
        code_col = [c for c in df.columns if "Contract_Market_Code" in c or "CFTC Contract Market Code" in c][0]
        d = df[df[code_col].astype(str).str.strip() == "067651"]
        date_col = [c for c in df.columns if "YYYY-MM-DD" in c or "As of Date in Form YYYY-MM-DD" in c][0]
        lc = [c for c in df.columns if "Noncommercial Positions-Long (All)" in c or "NonComm_Positions_Long_All" in c][0]; sc = [c for c in df.columns if "Noncommercial Positions-Short (All)" in c or "NonComm_Positions_Short_All" in c][0]
        cot.append(pd.DataFrame({"date": pd.to_datetime(d[date_col]), "net": d[lc].astype(float) - d[sc].astype(float)}))
    except Exception as e: print("cot fail", z, e)
cot = pd.concat(cot).sort_values("date").set_index("date")["net"]
P["noncomm_net"] = (cot.resample("MS").mean() / 1000).reindex(idx)
# Hormuz disruption (PortWatch from 2019; 0 before)
pg = json.load(open(f"{D}/page_data.json")); S = {s["key"]: s for s in pg["series"]}
hz = pd.Series(S["hormuz_tankers"]["values"], index=pd.to_datetime(pg["dates"]), dtype=float)
P["hormuz_disr"] = np.clip(1 - hz / 50.0, 0, 1).reindex(idx).fillna(0.0)
P.to_csv(f"{D}/panel_long_2006_2026.csv", float_format="%.4f")
print(P.notna().sum().to_string()); print(P.loc["2006-01":"2006-03"].round(1).to_string())

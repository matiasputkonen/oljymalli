#!/usr/bin/env python3
"""Fetch: PortWatch chokepoint daily transits, CPC observed daily degree days, EIA futures xls->csv."""
import os, io, json, time, requests, pandas as pd
RAW = "/home/claude/oil/data/raw3"; os.makedirs(RAW, exist_ok=True)
S = requests.Session()
def get(url, **kw):
    r = S.get(url, timeout=(10, 90), **kw); r.raise_for_status(); return r

# ---- PortWatch daily chokepoints (Suez 1, Bab el-Mandeb 4, Malacca 5, Hormuz 6, Cape 7) ----
base = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0/query"
rows = []
for pid in ["chokepoint1", "chokepoint4", "chokepoint5", "chokepoint6", "chokepoint7"]:
    off = 0
    while True:
        try:
            r = get(base, params={"where": f"portid='{pid}'", "outFields": "date,portid,portname,n_tanker,n_cargo,n_total,capacity_tanker,capacity", "f": "json", "resultOffset": off, "resultRecordCount": 1000, "orderByFields": "date"})
            js = r.json(); feats = js.get("features", [])
        except Exception as e:
            print("PortWatch fail", pid, off, e, flush=True); break
        rows += [f["attributes"] for f in feats]
        if len(feats) < 1000: break
        off += 1000
    print("PortWatch", pid, "rows so far", len(rows), flush=True)
pw = pd.DataFrame(rows)
if len(pw):
    pw["date"] = pd.to_datetime(pw["date"], unit="ms").dt.normalize()
    pw.to_csv(f"{RAW}/portwatch_chokepoints.csv", index=False)
    print(pw.groupby("portname").date.agg(["min", "max", "count"]))

# ---- CPC observed daily degree days by state and census division ----
def cpc_parse(txt):
    lines = [l for l in txt.splitlines() if "|" in l]
    hdr = lines[0].split("|"); out = []
    for l in lines[1:]:
        p = l.split("|")
        for d, v in zip(hdr[1:], p[1:]):
            if d.isdigit(): out.append((p[0], pd.Timestamp(d), float(v) if v not in ("", "M") else None))
    return pd.DataFrame(out, columns=["region", "date", "value"])
obs = []
for yr in range(2015, 2027):
    for prod, fn in [("HDD_states", "StatesCONUS.Heating.txt"), ("HDD_div", "Population.Heating.txt"), ("CDD_states", "StatesCONUS.Cooling.txt"), ("CDD_div", "Population.Cooling.txt")]:
        try:
            r = get(f"https://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/daily_data/{yr}/{fn}")
            d = cpc_parse(r.text); d["product"] = prod; obs.append(d)
        except Exception as e:
            print("CPC obs fail", yr, fn, e, flush=True)
    print("CPC obs", yr, flush=True)
pd.concat(obs).to_csv(f"{RAW}/cpc_observed_daily.csv", index=False)

# ---- EIA futures/spot daily xls -> csv ----
for fn, name in [("RCLC1d", "cl1"), ("RCLC2d", "cl2"), ("RCLC3d", "cl3"), ("RCLC4d", "cl4"), ("EER_EPD2F_PE1_Y35NY_DPGd", "ho1"), ("EER_EPMRR_PE1_Y35NY_DPGd", "rb1"), ("RNGC1d", "ng1"), ("RBRTEd", "brent_spot"), ("RWTCd", "wti_spot")]:
    try:
        x = pd.read_excel(f"{RAW}/{fn}.xls", sheet_name=1, header=2).iloc[:, :2]; x.columns = ["date", "value"]
        x["date"] = pd.to_datetime(x["date"], errors="coerce"); x = x.dropna()
        x.to_csv(f"{RAW}/eia_{name}.csv", index=False); print(name, len(x), x.iloc[-1].tolist(), flush=True)
    except Exception as e:
        print("xls fail", fn, e, flush=True)
print("DONE3")

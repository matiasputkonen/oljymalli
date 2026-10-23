#!/usr/bin/env python3
"""Add the two monthly series that live outside the panel to page_data.json: Hormuz tanker transits (PortWatch) and the NYMEX M1–M4 term spread."""
import json, numpy as np, pandas as pd
D = "/home/claude/oil/data"
pg = json.load(open(f"{D}/page_data.json")); dates = pd.to_datetime(pg["dates"]); S = {s["key"]: s for s in pg["series"]}
def put(key, s, label, group, unit, source, note=""):
    s = s.reindex(dates); vals = [None if (v is None or (isinstance(v, float) and np.isnan(v))) else round(float(v), 4) for v in s.values]
    fv = s.first_valid_index(); lv = s.last_valid_index()
    rec = dict(key=key, label=label, group=group, unit=unit, freq="monthly", source=source, first=str(fv)[:7] if fv is not None else None, last=str(lv)[:7] if lv is not None else None, values=vals, on=S.get(key, {}).get("on", False))
    if key in S: S[key].update(rec)
    else: pg["series"].append(rec)
hz = pd.read_csv(f"{D}/hormuz_daily.csv", parse_dates=["date"]).set_index("date")["n_tanker"].astype(float).resample("MS").mean()
put("hormuz_tankers", hz, "Hormuzin tankkeritransitit (kpl/pv)", "Rahti", "kpl/pv", "IMF PortWatch (AIS), kk-keskiarvo")
fd = pd.read_csv(f"{D}/futures_daily.csv", parse_dates=["date"]).set_index("date")
put("term_m1m4", fd["m1m4"].dropna().resample("MS").mean(), "NYMEX-käyrä M1–M4 (USD; + = backwardaatio)", "Öljyn hinnat", "USD/bbl", "EIA/NYMEX CL1–CL4, päättyy 4/2024")
json.dump(pg, open(f"{D}/page_data.json", "w"), ensure_ascii=False)
print("extra series ok:", {k: (S[k]["first"], S[k]["last"]) for k in ["hormuz_tankers", "term_m1m4"] if k in S})

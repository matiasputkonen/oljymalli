#!/usr/bin/env python3
"""EIA STEO price-forecast vintages (monthly archives): for every vintage month, the WTI and Brent monthly path it published.
Downloads only vintages missing from data/steo_vintages.csv (raw files cached outside the repo), parses sheet 2tab (WTIPUUS, BREPUUS).
Columns: vintage (YYYY-MM), month (YYYY-MM-01), wti, brent."""
import os, sys, io, json, datetime as dt, pandas as pd, requests
from concurrent.futures import ThreadPoolExecutor
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); D = f"{ROOT}/data"; OUT = f"{D}/steo_vintages.csv"
CACHE = os.environ.get("STEO_CACHE", f"{ROOT}/../steo_cache"); os.makedirs(CACHE, exist_ok=True)
START = "2011-01"; MONS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
old = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame(columns=["vintage", "month", "wti", "brent"])
have = set(old.vintage.unique()); today = pd.Timestamp.today()
wanted = [str(p)[:7] for p in pd.period_range(START, today.strftime("%Y-%m"), freq="M") if str(p)[:7] not in have]
def fetch(v):
    y, m = int(v[:4]), int(v[5:7]); stem = f"{MONS[m - 1]}{y % 100:02d}_base"
    for ext in ["xlsx", "xls"]:
        fn = f"{CACHE}/steo_{stem}.{ext}"
        if os.path.exists(fn) and os.path.getsize(fn) > 100000: return fn
        try:
            r = requests.get(f"https://www.eia.gov/outlooks/steo/archives/{stem}.{ext}", timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and len(r.content) > 100000 and b"<html" not in r.content[:200].lower(): open(fn, "wb").write(r.content); return fn
        except Exception as e: print("fail", v, ext, str(e)[:60])
    return None
def parse(fn, v):
    x = pd.read_excel(fn, sheet_name="2tab", header=None)
    yrow = x.iloc[2, 2:].tolist(); mrow = x.iloc[3, 2:].tolist(); dates = []; cur = None
    for yy, mm in zip(yrow, mrow):
        if isinstance(yy, (int, float)) and not pd.isna(yy): cur = int(yy)
        if cur is None or not isinstance(mm, str) or mm[:3].capitalize() not in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]: dates.append(None); continue
        dates.append(pd.Timestamp(year=cur, month=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(mm[:3].capitalize()) + 1, day=1))
    ser = {}
    for i in range(4, x.shape[0]):
        code = str(x.iloc[i, 0]).strip().upper()
        if code in ("WTIPUUS", "BREPUUS"):
            vals = pd.to_numeric(x.iloc[i, 2:2 + len(dates)].values, errors="coerce"); ser[code] = pd.Series([a for a, d_ in zip(vals, dates) if d_ is not None], index=[d_ for d_ in dates if d_ is not None]).dropna()
    if "WTIPUUS" not in ser: return pd.DataFrame()
    df = pd.DataFrame({"wti": ser["WTIPUUS"], "brent": ser.get("BREPUUS", pd.Series(dtype=float))}); df.index.name = "month"; df = df.reset_index(); df.insert(0, "vintage", v)
    df["month"] = df["month"].dt.strftime("%Y-%m-%d"); return df
rows = []
with ThreadPoolExecutor(4) as ex:
    for v, fn in zip(wanted, ex.map(fetch, wanted)):
        if not fn: print("missing", v); continue
        try:
            df = parse(fn, v)
            if len(df): rows.append(df)
            else: print("no WTIPUUS", v)
        except Exception as e: print("parse fail", v, str(e)[:80])
new = pd.concat([old] + rows, ignore_index=True) if rows else old
new = new.drop_duplicates(["vintage", "month"], keep="last").sort_values(["vintage", "month"]); new.to_csv(OUT, index=False)
print(f"steo vintages: {new.vintage.nunique()} vintages ({new.vintage.min()} → {new.vintage.max()}), {len(rows)} new, rows {len(new)}")

#!/usr/bin/env python3
"""Real-time STEO supply/demand paths per vintage (table 3a): OPEC production, world production, world consumption, implied stock change.
Reads the cached vintage files (scripts/steo_vintages.py cache). Columns: vintage, month, opec, prod, cons, stchg. Writes data/steo_balance.csv."""
import os, glob, sys, pandas as pd
from concurrent.futures import ThreadPoolExecutor
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); D = f"{ROOT}/data"; CACHE = os.environ.get("STEO_CACHE", f"{ROOT}/../steo_cache")
MONS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]; MN = [m.capitalize() for m in MONS]
def parse(fn):
    x = pd.read_excel(fn, sheet_name="3atab", header=None); yrow = x.iloc[2, 2:].tolist(); mrow = x.iloc[3, 2:].tolist(); dates = []; cur = None
    for yy, mm in zip(yrow, mrow):
        if isinstance(yy, (int, float)) and not pd.isna(yy): cur = int(yy)
        dates.append(pd.Timestamp(year=cur, month=MN.index(mm[:3]) + 1, day=1) if (cur and isinstance(mm, str) and mm[:3] in MN) else None)
    want = {"papr_opec": "opec", "papr_world": "prod", "patc_world": "cons", "t3_stchange_world": "stchg"}; ser = {}
    for i in range(4, x.shape[0]):
        code = str(x.iloc[i, 0]).strip()
        if code in want and want[code] not in ser:
            vals = pd.to_numeric(x.iloc[i, 2:2 + len(dates)].values, errors="coerce"); ser[want[code]] = pd.Series([a for a, d in zip(vals, dates) if d is not None], index=[d for d in dates if d is not None])
    return pd.DataFrame(ser)
def job(fn):
    stem = os.path.basename(fn).replace("steo_", "").split("_base")[0]; v = f"20{stem[3:5]}-{MONS.index(stem[:3]) + 1:02d}"
    try: df = parse(fn); df.index.name = "month"; df = df.reset_index(); df.insert(0, "vintage", v); return df
    except Exception as e: print("fail", fn, str(e)[:60]); return None
files = sorted(glob.glob(f"{CACHE}/steo_*_base.xls*")); print(len(files), "files")
with ThreadPoolExecutor(4) as ex: parts = [p for p in ex.map(job, files) if p is not None]
out = pd.concat(parts, ignore_index=True).sort_values(["vintage", "month"]); out["month"] = out["month"].dt.strftime("%Y-%m-%d"); out.to_csv(f"{D}/steo_balance.csv", index=False)
print("steo_balance:", out.vintage.nunique(), "vintages", out.shape, out.isna().mean().round(2).to_dict())

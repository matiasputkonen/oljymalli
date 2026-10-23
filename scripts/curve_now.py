#!/usr/bin/env python3
"""Current WTI / Brent futures curves from the Yahoo contract histories (latest common date), plus an options file selection.
Writes data/curves_now.json: {wti: {date, label, curve: [{date, price, contract}]}, brent: {...}, options: {file, date, expiries}}"""
import os, json, glob, datetime as dt, pandas as pd
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); D = f"{ROOT}/data"; R3 = f"{D}/raw3"; R4 = f"{D}/raw4"
MON = {c: i + 1 for i, c in enumerate("FGHJKMNQUVXZ")}; MN = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
out = {}
for tgt, root, label in [("wti", "CL", "NYMEX WTI -futuurikäyrä"), ("brent", "BZ", "ICE Brent -futuurikäyrä (CME BZ)")]:
    pts = []
    for fn in sorted(glob.glob(f"{R3}/yahoo/{root}*.NYM.json")):
        code = fn.split("/")[-1].split(".")[0]
        try:
            j = json.load(open(fn))["chart"]["result"][0]; s = pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna(); s = s[~s.index.duplicated(keep="last")]
            if not len(s): continue
            yr = 2000 + int(code[-2:]); mo = MON[code[-3]]; pts.append((pd.Timestamp(year=yr, month=mo, day=1), float(s.iloc[-1]), s.index[-1], f"{MN[mo - 1]} {yr % 100}"))
        except Exception as e: print("skip", code, e)
    if not pts: continue
    last = max(p[2] for p in pts); nxt = (last.replace(day=1) + pd.DateOffset(months=1))
    cur = sorted([p for p in pts if (last - p[2]).days <= 3 and p[0] > last.replace(day=1) and not (p[2] < last and p[0] <= nxt)], key=lambda p: p[0])   # drop the expired front
    out[tgt] = dict(date=str(last.date()), label=f"{label} {last.strftime('%d.%m.%Y')}", curve=[dict(date=str(p[0].date()), price=round(p[1], 2), contract=p[3]) for p in cur])
    print(tgt, out[tgt]["date"], len(cur), "points:", [(c["contract"], c["price"]) for c in out[tgt]["curve"][:4]], "...", out[tgt]["curve"][-1])
# options: prefer a fresh Yahoo chain, else the CME settlement file
opt = None
if os.path.exists(f"{R4}/yahoo_options_CL.json"):
    m = json.load(open(f"{R4}/yahoo_options_CL.json")); opt = dict(file=f"{R4}/yahoo_options_CL.txt", date=m["date"], expiries=m["expiries"], source="Yahoo Finance (CL=F optioketju, bid/ask-keskihinta)")
else:
    opt = dict(file=f"{R4}/cme_options_2026-10-22.txt", date="2026-10-22", expiries={"LOZ26": "2026-11-17", "LOG27": "2027-01-14", "LOJ27": "2027-03-17", "LOM27": "2027-05-17", "LOZ27": "2027-11-16"}, source="CME settlements 22.10.2026 (manuaalinen)")
out["options"] = opt
json.dump(out, open(f"{D}/curves_now.json", "w")); print("options:", opt["date"], len(opt["expiries"]), "expiries")

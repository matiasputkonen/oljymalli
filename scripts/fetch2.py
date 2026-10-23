#!/usr/bin/env python3
"""Second pass: OWID (lower-case header), stooq via curl with retries, misc."""
import os, subprocess, time, requests, pandas as pd, io
RAW = "/home/claude/oil/data/raw"
S = requests.Session()
def get(url, **kw):
    r = S.get(url, timeout=(10, 60), **kw); r.raise_for_status(); return r

OWID = ["human-development-index", "wind-generation", "electric-car-sales-share", "electric-car-sales",
        "oil-consumption-by-country", "oil-production-by-country", "share-electricity-wind", "solar-energy-consumption",
        "share-of-the-population-with-completed-tertiary-education", "crude-birth-rate", "car-sales", "new-vehicles-sold",
        "wind-energy-consumption", "electricity-generation-wind"]
for slug in OWID:
    try:
        r = get(f"https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=true")
        if not r.text.lower().startswith("entity"): raise ValueError(r.text[:60])
        open(f"{RAW}/owid_{slug}.csv", "w").write(r.text)
        print(f"OWID ok {slug} bytes={len(r.text)} header={r.text.splitlines()[0]}", flush=True)
    except Exception as e:
        print(f"OWID FAIL {slug}: {str(e)[:100]}", flush=True)

STOOQ = ["cl.f", "cb.f", "ng.f", "xle.us", "xop.us", "^spx", "jets.us", "hg.f", "rb.f", "ho.f", "^dax", "^shc", "eurusd", "^vix", "xom.us", "tsla.us", "uso.us", "oih.us", "^bdi", "bdi.e", "dx.f", "^dxy"]
for sym in STOOQ:
    ok = False
    for attempt in range(3):
        try:
            out = subprocess.run(["curl", "-sS", "--max-time", "40", f"https://stooq.com/q/d/l/?s={sym}&i=d"], capture_output=True, text=True, timeout=50)
            txt = out.stdout
            if txt.startswith("Date"):
                open(f"{RAW}/stooq_{sym.replace('^','_')}.csv", "w").write(txt)
                print(f"STOOQ ok {sym} rows={txt.count(chr(10))} tail={txt.strip().splitlines()[-1]}", flush=True); ok = True; break
            else:
                print(f"STOOQ try{attempt} {sym}: {txt[:60]!r} {out.stderr[:80]!r}", flush=True)
        except Exception as e:
            print(f"STOOQ try{attempt} {sym} exc {e}", flush=True)
        time.sleep(2)
    if not ok: print(f"STOOQ FAIL {sym}", flush=True)
print("DONE2")

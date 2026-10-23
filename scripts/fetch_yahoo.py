import requests, json, time, sys, os, pandas as pd
OUT="/home/claude/oil/data/raw3/yahoo"
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept":"application/json"}
months="FGHJKMNQUVXZ"
syms=[]
for root in ["CL","BZ"]:
    for yr in [24,25,26,27,28]:
        for m in months: syms.append(f"{root}{m}{yr}.NYM")
ok=0
for s in syms:
    fn=f"{OUT}/{s}.json"
    if os.path.exists(fn): ok+=1; continue
    for attempt in range(3):
        try:
            r=requests.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{s}",params={"range":"5y","interval":"1d"},headers=H,timeout=(10,40))
            if r.status_code==200 and '"timestamp"' in r.text:
                open(fn,"w").write(r.text); ok+=1; break
            elif r.status_code==404: break
            else: time.sleep(2)
        except Exception as e: time.sleep(2)
    time.sleep(0.4)
print("fetched",ok,"of",len(syms))

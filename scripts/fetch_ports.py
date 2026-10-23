import requests, pandas as pd, time
base="https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/FeatureServer/0/query"
PORTS={"port1091":"Ras Tanura","port526":"Juaymah","port570":"Yanbu","port743":"Mina Al Ahmadi","port20":"Al Basrah","port362":"Fujairah","port744":"Jebel Ali","port107":"Bandar Abbas","port1020":"Primorsk","port833":"Novorossiysk","port1095":"Ust-Luga","port264":"Corpus Christi","port481":"Houston","port134":"Beaumont","port1214":"South Louisiana","port1069":"Qingdao","port824":"Ningbo","port1114":"Rotterdam"}
S=requests.Session(); rows=[]
for pid,name in PORTS.items():
    off=0
    while True:
        try:
            r=S.get(base,params={"where":f"portid='{pid}'","outFields":"date,portid,portname,country,portcalls_tanker,import_tanker,export_tanker,portcalls","f":"json","resultOffset":off,"resultRecordCount":1000,"orderByFields":"date"},timeout=(10,90)); js=r.json(); feats=js.get("features",[])
        except Exception as e: print("fail",pid,off,e,flush=True); break
        rows+=[f["attributes"] for f in feats]
        if len(feats)<1000: break
        off+=1000
    print(name,len(rows),flush=True)
pw=pd.DataFrame(rows); pw["date"]=pd.to_datetime(pw["date"],unit="ms").dt.normalize(); pw.to_csv("/home/claude/oil/data/raw3/portwatch_ports.csv",index=False); print("DONE")

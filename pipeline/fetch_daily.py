#!/usr/bin/env python3
"""Fault-tolerant data refresh for the automated run. Every source is wrapped: on failure the previous file is kept and the
status is recorded in data/status_fetch.json. Daily sources run every time; slow-moving sources (World Bank, OWID, NASA, freight) weekly or with --full."""
import os, io, sys, json, time, zipfile, datetime as dt, requests, pandas as pd
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); RAW = f"{ROOT}/data/raw"; R3 = f"{ROOT}/data/raw3"; R4 = f"{ROOT}/data/raw4"; R5 = f"{ROOT}/data/raw5"
for d in [RAW, R3, R4, R5, f"{R3}/yahoo"]: os.makedirs(d, exist_ok=True)
FULL = "--full" in sys.argv or dt.date.today().weekday() == 0
S = requests.Session(); STATUS = {}
def get(url, timeout=(10, 60), **kw):
    r = S.get(url, timeout=timeout, **kw); r.raise_for_status(); return r
def step(name, fn):
    t0 = time.time()
    try:
        info = fn(); STATUS[name] = dict(ok=True, info=str(info)[:200], secs=round(time.time() - t0, 1)); print(f"OK   {name}: {str(info)[:120]}", flush=True)
    except Exception as e:
        STATUS[name] = dict(ok=False, error=str(e)[:200], secs=round(time.time() - t0, 1)); print(f"FAIL {name}: {str(e)[:160]}", flush=True)

sys.path.insert(0, f"{ROOT}/scripts")
# ---------------- FRED ----------------
FRED = {"WTI_m": "MCOILWTICO", "Brent_m": "MCOILBRENTEU", "Dubai_m": "POILDUBUSDM", "APSP_m": "POILAPSPUSDM", "WTI_d": "DCOILWTICO", "Brent_d": "DCOILBRENTEU",
        "HenryHub_m": "MHHNGSP", "EUgas_m": "PNGASEUUSDM", "Gasoline_US_m": "GASREGM", "Diesel_US_m": "GASDESM", "USprod_m": "MCRFPUS2",
        "IP_total": "INDPRO", "IP_manuf": "IPMAN", "IP_mining": "IPMINE", "IP_oilgas_extr": "IPG211S", "IP_drilling": "IPN213111S", "IP_chem": "IPG325S", "IP_autos": "IPG3361T3S", "IP_petrol_coal": "IPG324S",
        "AirRPM": "AIRRPMTSI", "VMT": "TRFVOLUSM227NFWA", "TSI_freight": "TSIFRGHT", "Cass_shipments": "FRGSHPUSM649NCIS", "VehicleSales_US": "TOTALSA",
        "GDP_US_q": "GDPC1", "GDP_DE_q": "CLVMNACSCAB1GQDE", "GDP_CN_q_nom": "CHNGDPNQDSMEI", "CPI_US": "CPIAUCSL", "CPI_energy_US": "CPIENGSL", "FedFunds": "FEDFUNDS", "UST10y": "GS10", "Unemp_US": "UNRATE",
        "DollarBroad_d": "DTWEXBGS", "SP500_d": "SP500", "VIX_d": "VIXCLS", "IP_CN": "CHNPRINTO01IXPYM", "IP_DE": "DEUPROINDMISMEI",
        "Copper": "PCOPPUSDM", "Aluminum": "PALUMUSDM", "IronOre": "PIORECRUSDM", "Nickel": "PNICKUSDM", "Steel_PPI": "WPU1017", "Lumber_PPI": "WPU081", "Commodities_all": "PALLFNFINDEXM", "Metals_idx": "PMETAINDEXM",
        "Energy_idx": "PNRGINDEXM", "Food_idx": "PFOODINDEXM", "Fertilizer_idx": "PFERTINDEXM", "NonFuel_idx": "PNFUELINDEXM", "PPI_all": "PPIACO"}
def fred_all():
    ok = 0; last = {}
    for name, sid in FRED.items():
        try:
            r = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=(10, 45)); df = pd.read_csv(io.StringIO(r.text))
            if df.shape[1] < 2 or len(df) < 10: raise ValueError("short")
            df.columns = ["date", "value"]; df["value"] = pd.to_numeric(df["value"], errors="coerce"); df.to_csv(f"{RAW}/fred_{name}.csv", index=False); ok += 1
            if name in ("WTI_d", "Brent_d"): last[name] = df.dropna().iloc[-1].tolist()
        except Exception as e: print("  fred fail", name, str(e)[:60])
        time.sleep(0.15)
    # OVX to raw3 (used by models)
    r = get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=OVXCLS", timeout=(10, 45)); open(f"{R3}/fred_OVX.csv", "w").write(r.text)
    return f"{ok}/{len(FRED)} series; {last}"
step("fred", fred_all)
# ---------------- EIA ----------------
EIA_XLS = {"CrudeStocksExSPR_m": "MCESTUS1m.xls", "SPR_m": "MCSSTUS1m.xls", "Cushing_w": "W_EPC0_SAX_YCUOK_MBBLw.xls", "Rigs_m": "E_ERTRRO_XR0_NUS_Cm.xls", "CrudeExports_m": "MCREXUS2m.xls", "CrudeImports_m": "MCRIMUS2m.xls",
           "ProductSupplied_m": "MTTUPUS2m.xls", "RefUtil_m": "MOPUEUS2m.xls", "Brent_EIA_m": "RBRTEm.xls", "WCESTUS1w": "WCESTUS1w.xls", "WCSSTUS1w": "WCSSTUS1w.xls", "WTTSTUS1w": "WTTSTUS1w.xls",
           "WGTSTUS1w": "WGTSTUS1w.xls", "WDISTUS1w": "WDISTUS1w.xls", "WCRFPUS2w": "WCRFPUS2w.xls", "MCRFPUS2m": "MCRFPUS2m.xls", "MTTEXUS2m": "MTTEXUS2m.xls", "MGFUPUS2m": "MGFUPUS2m.xls", "MDIUPUS2m": "MDIUPUS2m.xls", "MKJUPUS2m": "MKJUPUS2m.xls"}
def eia_xls(name, fn, outdir=RAW, prefix="eia_"):
    r = get(f"https://www.eia.gov/dnav/pet/hist_xls/{fn}"); x = pd.read_excel(io.BytesIO(r.content), sheet_name=1, header=2); x.columns = ["date", "value"] + list(x.columns[2:]); x = x[["date", "value"]]
    x["date"] = pd.to_datetime(x["date"], errors="coerce"); x = x.dropna()
    open(f"{outdir}/{prefix}{name}.xls", "wb").write(r.content); x.to_csv(f"{outdir}/{prefix}{name}.csv", index=False); return x.iloc[-1].tolist()
def eia_all():
    ok = 0; last = {}
    for name, fn in EIA_XLS.items():
        try: last[name] = eia_xls(name, fn); ok += 1
        except Exception as e: print("  eia fail", name, str(e)[:60])
    return f"{ok}/{len(EIA_XLS)}; WCESTUS1w {last.get('WCESTUS1w')}"
step("eia_weekly_monthly", eia_all)
def eia_daily():
    out = {}
    for fn, name in [("RCLC1d", "cl1"), ("RCLC2d", "cl2"), ("RCLC3d", "cl3"), ("RCLC4d", "cl4"), ("EER_EPD2F_PE1_Y35NY_DPGd", "ho1"), ("EER_EPMRR_PE1_Y35NY_DPGd", "rb1"), ("RNGC1d", "ng1"), ("RBRTEd", "brent_spot"), ("RWTCd", "wti_spot")]:
        try:
            r = get(f"https://www.eia.gov/dnav/pet/hist_xls/{fn}.xls"); open(f"{R3}/{fn}.xls", "wb").write(r.content)
            x = pd.read_excel(io.BytesIO(r.content), sheet_name=1, header=2).iloc[:, :2]; x.columns = ["date", "value"]; x["date"] = pd.to_datetime(x["date"], errors="coerce"); x = x.dropna(); x.to_csv(f"{R3}/eia_{name}.csv", index=False); out[name] = str(x.date.iloc[-1].date())
        except Exception as e: print("  eia daily fail", name, str(e)[:60])
    return out
step("eia_daily_futures_spot", eia_daily)
def eia_other():
    for tbl in ["T07.02A", "T07.02B", "T01.02", "T03.07A"]:
        r = get(f"https://www.eia.gov/totalenergy/data/browser/csv.php?tbl={tbl}"); open(f"{RAW}/eia_totalenergy_{tbl}.csv", "w").write(r.text)
    r = get("https://www.eia.gov/outlooks/steo/xls/STEO_m.xlsx"); open(f"{RAW}/STEO_m.xlsx", "wb").write(r.content)
    x = pd.read_excel(io.BytesIO(r.content), sheet_name="2tab", header=None); return f"STEO vintage {x.iloc[3, 0]}"
step("eia_totalenergy_steo", eia_other)
step("opec_basket", lambda: (open(f"{RAW}/opec_basket.xml", "w").write(get("https://www.opec.org/basket/basketDayArchives.xml").text), "ok")[1])
# ---------------- CFTC (current + previous year zip; older years cached) ----------------
def cftc():
    yr = dt.date.today().year; got = []
    for y in [yr - 1, yr]:
        r = get(f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{y}.zip"); open(f"{RAW}/cftc_{y}.zip", "wb").write(r.content); got.append(y)
    try:
        r = get(f"https://www.cftc.gov/files/dea/history/deacot{yr}.zip"); open(f"{R3}/deacot{yr}.zip", "wb").write(r.content); got.append(f"deacot{yr}")
    except Exception as e: print("  deacot fail", str(e)[:60])
    return got
step("cftc", cftc)
# ---------------- PortWatch chokepoints ----------------
def portwatch():
    base = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0/query"; rows = []
    for pid in ["chokepoint1", "chokepoint4", "chokepoint5", "chokepoint6", "chokepoint7"]:
        off = 0
        while True:
            r = get(base, params={"where": f"portid='{pid}'", "outFields": "date,portid,portname,n_tanker,n_cargo,n_total,capacity_tanker,capacity", "f": "json", "resultOffset": off, "resultRecordCount": 2000, "orderByFields": "date"}, timeout=(10, 90))
            feats = r.json().get("features", []); rows += [f["attributes"] for f in feats]
            if len(feats) < 2000: break
            off += 2000
    pw = pd.DataFrame(rows)
    if len(pw) < 1000: raise ValueError("too few rows")
    pw["date"] = pd.to_datetime(pw["date"], unit="ms").dt.normalize(); pw.to_csv(f"{R3}/portwatch_chokepoints.csv", index=False)
    hz = pw[pw.portname == "Strait of Hormuz"]; return f"{len(pw)} rows; Hormuz last {hz.date.max().date()} n_tanker {hz.sort_values('date').n_tanker.iloc[-1]}"
step("portwatch", portwatch)
# ---------------- GPR daily + monthly ----------------
def gpr():
    r = get("https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"); open(f"{R5}/gpr_daily.xls", "wb").write(r.content)
    x = pd.read_excel(io.BytesIO(r.content)); last = x.dropna(subset=["GPRD"]).iloc[-1]
    try: r2 = get("https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"); open(f"{R3}/gpr.xls", "wb").write(r2.content)
    except Exception as e: print("  gpr monthly fail", str(e)[:60])
    return f"daily last {last['date']} GPRD {float(last['GPRD']):.0f}"
step("gpr", gpr)
# ---------------- Yahoo: futures contracts (append), S&P monthly, WTI options chain (best effort) ----------------
YH = {"Accept": "application/json"}
def yahoo_get(url, params=None):
    for host in ["query1", "query2"]:
        for attempt in range(2):
            r = S.get(url.replace("HOST", host), params=params, headers=YH, timeout=(10, 40))
            if r.status_code == 200: return r
            time.sleep(3 + 5 * attempt)
    raise RuntimeError(f"yahoo {r.status_code}")
def yahoo_contracts():
    months = "FGHJKMNQUVXZ"; today = dt.date.today(); ok = 0; tried = 0
    for root in ["CL", "BZ"]:
        for yr in [today.year % 100, today.year % 100 + 1, today.year % 100 + 2]:
            for m in months:
                code = f"{root}{m}{yr:02d}.NYM"; fn = f"{R3}/yahoo/{code}.json"
                exp = dt.date(2000 + yr, months.index(m) + 1, 1)
                if exp < today.replace(day=1): continue
                tried += 1
                try:
                    r = yahoo_get(f"https://HOST.finance.yahoo.com/v8/finance/chart/{code}", {"range": "3mo" if os.path.exists(fn) else "5y", "interval": "1d"}); j = r.json()["chart"]["result"][0]
                    if os.path.exists(fn):   # merge
                        old = json.load(open(fn))["chart"]["result"][0]; ts = old["timestamp"]; cl = old["indicators"]["quote"][0]["close"]; have = set(ts)
                        for t, c in zip(j["timestamp"], j["indicators"]["quote"][0]["close"]):
                            if t not in have: ts.append(t); cl.append(c)
                        order = sorted(range(len(ts)), key=lambda i: ts[i]); old["timestamp"] = [ts[i] for i in order]; old["indicators"]["quote"][0]["close"] = [cl[i] for i in order]
                        json.dump({"chart": {"result": [old]}}, open(fn, "w"))
                    else: open(fn, "w").write(r.text)
                    ok += 1
                except Exception as e:
                    if "404" in str(e): continue
                    print("  yahoo fail", code, str(e)[:50]);
                    if "429" in str(e): raise
                time.sleep(0.5)
    return f"{ok}/{tried} contracts"
step("yahoo_contracts", yahoo_contracts)
def yahoo_sp():
    r = yahoo_get("https://HOST.finance.yahoo.com/v8/finance/chart/%5EGSPC", {"range": "20y", "interval": "1mo"}); open(f"{R3}/yahoo_%5EGSPC_m.json", "w").write(r.text); return "ok"
step("yahoo_sp500_monthly", yahoo_sp)
def yahoo_options():
    """WTI options chains for the listed expirations; written in the same 'exp|C/P|strike|price|oi' format as the CME settlement file, with expiries.json."""
    r = yahoo_get("https://HOST.finance.yahoo.com/v7/finance/options/CL%3DF"); j = r.json()["optionChain"]["result"][0]; exps = j["expirationDates"]; lines = []; meta = {}
    for ts in exps[:12]:
        rr = yahoo_get("https://HOST.finance.yahoo.com/v7/finance/options/CL%3DF", {"date": ts}); o = rr.json()["optionChain"]["result"][0]["options"][0]; expd = dt.datetime.utcfromtimestamp(ts).date()
        code = f"Y{expd.strftime('%y%m%d')}"; meta[code] = str(expd); n = 0
        for side, key in [("C", "calls"), ("P", "puts")]:
            for c in o.get(key, []):
                px = c.get("lastPrice"); bid = c.get("bid"); ask = c.get("ask")
                if bid and ask and ask > 0: px = (bid + ask) / 2
                if px and px > 0: lines.append(f"{code}|{side}|{c['strike']}|{px}|{c.get('openInterest', 0)}"); n += 1
        time.sleep(0.5)
    if len(lines) < 100: raise ValueError("too few options")
    open(f"{R4}/yahoo_options_CL.txt", "w").write("\n".join(lines)); json.dump(dict(date=str(dt.date.today()), expiries=meta, underlying=j.get("quote", {}).get("regularMarketPrice")), open(f"{R4}/yahoo_options_CL.json", "w")); return f"{len(lines)} quotes, {len(meta)} expiries"
step("yahoo_options", yahoo_options)
# ---------------- weekly: NASA, World Bank, OWID, BDI/freight ----------------
if FULL:
    def nasa():
        for name in ["GLB", "NH", "SH"]: open(f"{RAW}/gistemp_{name}.csv", "w").write(get(f"https://data.giss.nasa.gov/gistemp/tabledata_v4/{name}.Ts+dSST.csv").text)
        return "ok"
    step("nasa_gistemp", nasa)
    WB = {"GDPgrowth": "NY.GDP.MKTP.KD.ZG", "GDPpcPPP": "NY.GDP.PCAP.PP.KD", "BirthRate": "SP.DYN.CBRT.IN", "TertiaryEnrol": "SE.TER.ENRR", "GDPreal": "NY.GDP.MKTP.KD", "TertiaryAttainBA": "SE.TER.CUAT.BA.ZS", "Fertility": "SP.DYN.TFRT.IN", "EnergyUsePC": "EG.USE.PCAP.KG.OE"}
    def worldbank():
        rows = []
        for name, ind in WB.items():
            r = get(f"https://api.worldbank.org/v2/country/USA;CHN;DEU;IND;WLD/indicator/{ind}?format=json&per_page=500&date=2005:2026"); js = r.json()
            for rec in js[1]: rows.append(dict(indicator=name, code=ind, country=rec["country"]["id"], iso3=rec["countryiso3code"], year=int(rec["date"]), value=rec["value"]))
        df = pd.DataFrame(rows)
        if len(df) < 200: raise ValueError("short")
        df.to_csv(f"{RAW}/worldbank.csv", index=False); return len(rows)
    step("worldbank", worldbank)
    OWID = ["human-development-index", "wind-generation", "electric-car-sales-share", "electric-car-sales", "oil-consumption-by-country", "oil-production-by-country", "share-electricity-wind", "solar-energy-consumption",
            "share-of-the-population-with-completed-tertiary-education", "crude-birth-rate", "car-sales", "new-vehicles-sold", "wind-energy-consumption", "electricity-generation-wind"]
    def owid():
        ok = 0
        for slug in OWID:
            try:
                r = get(f"https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=true")
                if r.text.lower().startswith("entity"): open(f"{RAW}/owid_{slug}.csv", "w").write(r.text); ok += 1
            except Exception as e: print("  owid fail", slug, str(e)[:50])
        return f"{ok}/{len(OWID)}"
    step("owid", owid)
    # BDI / container freight (stock-marketdata.com Plotly pages) are refreshed manually for now: static files in data/raw.
json.dump(dict(run=str(dt.datetime.utcnow())[:19] + "Z", full=FULL, status=STATUS), open(f"{ROOT}/data/status_fetch.json", "w"), indent=1)
print("fetch done:", {k: v["ok"] for k, v in STATUS.items()})

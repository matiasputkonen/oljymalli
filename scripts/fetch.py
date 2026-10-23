#!/usr/bin/env python3
"""Fetch raw series into data/raw/. Each source is isolated with try/except so one failure never stops the rest."""
import io, os, sys, json, time, zipfile, re
import requests, pandas as pd

RAW = "/home/claude/oil/data/raw"
os.makedirs(RAW, exist_ok=True)
S = requests.Session()
# NOTE: a browser-like User-Agent makes FRED hang through the proxy; keep the default python-requests UA.
LOG = []

def log(msg):
    print(msg, flush=True); LOG.append(msg)

def get(url, **kw):
    r = S.get(url, timeout=(10, 45), **kw); r.raise_for_status(); return r

# ---------------- FRED ----------------
FRED = {
    # oil & energy prices
    "WTI_m": "MCOILWTICO", "Brent_m": "MCOILBRENTEU", "Dubai_m": "POILDUBUSDM", "APSP_m": "POILAPSPUSDM",
    "WTI_d": "DCOILWTICO", "Brent_d": "DCOILBRENTEU",
    "HenryHub_m": "MHHNGSP", "EUgas_m": "PNGASEUUSDM", "Gasoline_US_m": "GASREGM", "Diesel_US_m": "GASDESM",
    # supply / stocks
    "USprod_m": "MCRFPUS2", "CrudeStocksExSPR_w": "WCESTUS1", "SPR_w": "WCSSTUS1", "TotalPetStocks_w": "WTTSTUS1",
    "GasolineStocks_w": "WGTSTUS1", "DistillateStocks_w": "WDISTUS1",
    # sectors (industrial production etc.)
    "IP_total": "INDPRO", "IP_manuf": "IPMAN", "IP_mining": "IPMINE", "IP_oilgas_extr": "IPG211S",
    "IP_drilling": "IPN213111S", "IP_chem": "IPG325S", "IP_autos": "IPG3361T3S", "IP_petrol_coal": "IPG324S",
    "AirRPM": "AIRRPMTSI", "VMT": "TRFVOLUSM227NFWA", "TSI_freight": "TSIFRGHT", "Cass_shipments": "FRGSHPUSM649NCIS",
    "VehicleSales_US": "TOTALSA",
    # macro
    "GDP_US_q": "GDPC1", "GDP_DE_q": "CLVMNACSCAB1GQDE", "GDP_CN_q_nom": "CHNGDPNQDSMEI",
    "CPI_US": "CPIAUCSL", "CPI_energy_US": "CPIENGSL", "FedFunds": "FEDFUNDS", "UST10y": "GS10", "Unemp_US": "UNRATE",
    "DollarBroad_d": "DTWEXBGS", "SP500_d": "SP500", "VIX_d": "VIXCLS",
    "IP_CN": "CHNPRINTO01IXPYM", "IP_DE": "DEUPROINDMISMEI",
    # materials
    "Copper": "PCOPPUSDM", "Aluminum": "PALUMUSDM", "IronOre": "PIORECRUSDM", "Nickel": "PNICKUSDM",
    "Steel_PPI": "WPU1017", "Lumber_PPI": "WPU081", "Commodities_all": "PALLFNFINDEXM", "Metals_idx": "PMETAINDEXM",
    "Energy_idx": "PNRGINDEXM", "Food_idx": "PFOODINDEXM", "Fertilizer_idx": "PFERTINDEXM", "NonFuel_idx": "PNFUELINDEXM",
    "PPI_all": "PPIACO",
}
for name, sid in FRED.items():
    try:
        r = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}")
        df = pd.read_csv(io.StringIO(r.text))
        if df.shape[1] < 2: raise ValueError("no cols")
        df.columns = ["date", "value"]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df.to_csv(f"{RAW}/fred_{name}.csv", index=False)
        log(f"FRED ok {name} ({sid}) rows={len(df)} last={df.dropna().iloc[-1].to_dict()}")
    except Exception as e:
        log(f"FRED FAIL {name} ({sid}): {e}")
    time.sleep(0.2)

# ---------------- EIA dnav xls ----------------
EIA_XLS = {
    "CrudeStocksExSPR_m": "MCESTUS1m.xls", "SPR_m": "MCSSTUS1m.xls", "Cushing_w": "W_EPC0_SAX_YCUOK_MBBLw.xls",
    "Rigs_m": "E_ERTRRO_XR0_NUS_Cm.xls", "CrudeExports_m": "MCREXUS2m.xls", "CrudeImports_m": "MCRIMUS2m.xls",
    "ProductSupplied_m": "MTTUPUS2m.xls", "RefUtil_m": "MOPUEUS2m.xls", "Brent_EIA_m": "RBRTEm.xls",
}
for name, fn in EIA_XLS.items():
    try:
        r = get(f"https://www.eia.gov/dnav/pet/hist_xls/{fn}")
        open(f"{RAW}/eia_{name}.xls", "wb").write(r.content)
        x = pd.read_excel(io.BytesIO(r.content), sheet_name=1, header=2)
        x.columns = ["date", "value"] + list(x.columns[2:])
        x = x[["date", "value"]]
        x.to_csv(f"{RAW}/eia_{name}.csv", index=False)
        log(f"EIA ok {name} rows={len(x)} last={x.dropna().iloc[-1].to_dict()}")
    except Exception as e:
        log(f"EIA FAIL {name}: {e}")

# EIA total energy monthly (wind generation etc.)
for tbl in ["T07.02A", "T07.02B", "T01.02", "T03.07A"]:
    try:
        r = get(f"https://www.eia.gov/totalenergy/data/browser/csv.php?tbl={tbl}")
        open(f"{RAW}/eia_totalenergy_{tbl}.csv", "w").write(r.text)
        log(f"EIA TotalEnergy ok {tbl} bytes={len(r.text)}")
    except Exception as e:
        log(f"EIA TotalEnergy FAIL {tbl}: {e}")

# EIA STEO full data file
for url in ["https://www.eia.gov/outlooks/steo/xls/STEO_m.xlsx", "https://www.eia.gov/outlooks/steo/xls/3atab.xlsx", "https://www.eia.gov/outlooks/steo/xls/4atab.xlsx"]:
    try:
        r = get(url)
        fn = url.split("/")[-1]
        open(f"{RAW}/{fn}", "wb").write(r.content)
        log(f"STEO ok {fn} bytes={len(r.content)}")
    except Exception as e:
        log(f"STEO FAIL {url}: {e}")

# ---------------- OPEC basket ----------------
try:
    r = get("https://www.opec.org/basket/basketDayArchives.xml")
    open(f"{RAW}/opec_basket.xml", "w").write(r.text)
    log(f"OPEC basket ok bytes={len(r.text)}")
except Exception as e:
    log(f"OPEC basket FAIL: {e}")

# ---------------- NASA GISTEMP ----------------
for name in ["GLB", "NH", "SH"]:
    try:
        r = get(f"https://data.giss.nasa.gov/gistemp/tabledata_v4/{name}.Ts+dSST.csv")
        open(f"{RAW}/gistemp_{name}.csv", "w").write(r.text)
        log(f"GISTEMP ok {name} bytes={len(r.text)}")
    except Exception as e:
        log(f"GISTEMP FAIL {name}: {e}")

# ---------------- World Bank ----------------
WB = {"GDPgrowth": "NY.GDP.MKTP.KD.ZG", "GDPreal": "NY.GDP.MKTP.KD", "GDPpcPPP": "NY.GDP.PCAP.PP.KD",
      "BirthRate": "SP.DYN.CBRT.IN", "Fertility": "SP.DYN.TFRT.IN", "TertiaryEnrol": "SE.TER.ENRR",
      "TertiaryAttainBA": "SE.TER.CUAT.BA.ZS", "EnergyUsePC": "EG.USE.PCAP.KG.OE", "CO2pc": "EN.ATM.CO2E.PC"}
rows = []
for name, ind in WB.items():
    try:
        r = get(f"https://api.worldbank.org/v2/country/USA;CHN;DEU;IND;WLD/indicator/{ind}?format=json&per_page=500&date=2005:2026")
        js = r.json()
        for d in js[1]:
            rows.append({"indicator": name, "code": ind, "country": d["country"]["id"], "iso3": d["countryiso3code"], "year": int(d["date"]), "value": d["value"]})
        log(f"WB ok {name} n={len(js[1])}")
    except Exception as e:
        log(f"WB FAIL {name}: {e}")
pd.DataFrame(rows).to_csv(f"{RAW}/worldbank.csv", index=False)

# ---------------- OWID ----------------
OWID = ["human-development-index", "wind-generation", "electric-car-sales-share", "electric-car-sales",
        "oil-consumption-by-country", "oil-production-by-country", "share-electricity-wind", "solar-energy-consumption",
        "share-of-the-population-with-completed-tertiary-education", "new-vehicles-type-area", "crude-birth-rate"]
for slug in OWID:
    try:
        r = get(f"https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=true")
        if not r.text.startswith("Entity"): raise ValueError("unexpected content")
        open(f"{RAW}/owid_{slug}.csv", "w").write(r.text)
        log(f"OWID ok {slug} bytes={len(r.text)}")
    except Exception as e:
        log(f"OWID FAIL {slug}: {e}")

# ---------------- stooq ----------------
STOOQ = ["cl.f", "cb.f", "bz.f", "brn.f", "ng.f", "xle.us", "xop.us", "^spx", "^dxy", "jets.us", "tan.us", "^bdi", "bdi.e",
         "hg.f", "rb.f", "ho.f", "^shc", "^dax", "eurusd", "usdcnh", "^vix", "uso.us", "oih.us", "tsla.us", "xom.us"]
for sym in STOOQ:
    try:
        r = get(f"https://stooq.com/q/d/l/?s={sym}&i=d")
        if "Date" not in r.text[:50]: raise ValueError(r.text[:80])
        open(f"{RAW}/stooq_{sym.replace('^','_')}.csv", "w").write(r.text)
        log(f"STOOQ ok {sym} rows={r.text.count(chr(10))} tail={r.text.strip().splitlines()[-1]}")
    except Exception as e:
        log(f"STOOQ FAIL {sym}: {e}")
    time.sleep(0.5)

# ---------------- CFTC disaggregated COT ----------------
for yr in range(2015, 2027):
    try:
        r = get(f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{yr}.zip")
        open(f"{RAW}/cftc_{yr}.zip", "wb").write(r.content)
        log(f"CFTC ok {yr} bytes={len(r.content)}")
    except Exception as e:
        log(f"CFTC FAIL {yr}: {e}")

open(f"{RAW}/_fetch_log.txt", "w").write("\n".join(LOG))
print("DONE")

#!/usr/bin/env python3
"""Build monthly + annual panels from data/raw into data/panel_monthly.csv, data/panel_annual.csv, data/series_meta.json"""
import os, json, re, numpy as np, pandas as pd
RAW = "/home/claude/oil/data/raw"; OUT = "/home/claude/oil/data"
START = "2015-01-01"; END = pd.Timestamp.today().strftime("%Y-%m-01")
idx = pd.date_range(START, END, freq="MS")
M = pd.DataFrame(index=idx)           # monthly panel (raw units)
META = {}                             # key -> dict(label, group, unit, freq, source, note)

def add(key, s, label, group, unit, source, freq="monthly", note=""):
    s = s.copy(); s.index = pd.to_datetime(s.index); s = s[~s.index.duplicated()]
    s = s.reindex(idx)
    M[key] = s.values
    META[key] = dict(label=label, group=group, unit=unit, source=source, freq=freq, note=note,
                     first=str(s.first_valid_index())[:10] if s.first_valid_index() is not None else None,
                     last=str(s.last_valid_index())[:10] if s.last_valid_index() is not None else None)

def fred(name):
    d = pd.read_csv(f"{RAW}/fred_{name}.csv"); d["date"] = pd.to_datetime(d["date"])
    return d.set_index("date")["value"].astype(float)

def to_monthly(s, how="mean"):
    s = s.dropna(); s.index = pd.to_datetime(s.index)
    r = s.resample("MS")
    return r.mean() if how == "mean" else r.last()

def fred_m(name):  # monthly series already dated on 1st
    s = fred(name); s.index = s.index.to_period("M").to_timestamp(); return s

def eia(name):
    d = pd.read_csv(f"{RAW}/eia_{name}.csv"); d["date"] = pd.to_datetime(d["date"], errors="coerce"); d = d.dropna()
    return d.set_index("date")["value"].astype(float)

def eia_m(name):
    s = eia(name); s.index = s.index.to_period("M").to_timestamp(); return s

# ---------- Oil prices (extend monthly with daily averages for the latest months) ----------
def spliced(monthly, daily):
    dm = to_monthly(daily)
    out = monthly.copy()
    for d, v in dm.items():
        if d not in out.index or pd.isna(out.get(d)): out.loc[d] = v
    return out.sort_index()

brent = spliced(fred_m("Brent_m"), fred("Brent_d")); wti = spliced(fred_m("WTI_m"), fred("WTI_d"))
add("brent", brent, "Brent (USD/bbl)", "Öljyn hinnat", "USD/bbl", "FRED/EIA (MCOILBRENTEU, DCOILBRENTEU)")
add("wti", wti, "WTI (USD/bbl)", "Öljyn hinnat", "USD/bbl", "FRED/EIA (MCOILWTICO, DCOILWTICO)")
add("dubai", fred_m("Dubai_m"), "Dubai Fateh (USD/bbl)", "Öljyn hinnat", "USD/bbl", "IMF via FRED (POILDUBUSDM)")
add("apsp", fred_m("APSP_m"), "IMF APSP keskihinta (USD/bbl)", "Öljyn hinnat", "USD/bbl", "IMF via FRED (POILAPSPUSDM)")
add("brent_wti_spread", brent - wti, "Brent–WTI-ero (USD/bbl)", "Öljyn hinnat", "USD/bbl", "laskettu")
add("dubai_brent_spread", fred_m("Dubai_m") - brent, "Dubai–Brent-ero (USD/bbl)", "Öljyn hinnat", "USD/bbl", "laskettu")
add("henryhub", fred_m("HenryHub_m"), "Maakaasu Henry Hub (USD/MMBtu)", "Öljyn hinnat", "USD/MMBtu", "FRED (MHHNGSP)")
add("eugas", fred_m("EUgas_m"), "Maakaasu Eurooppa (USD/MMBtu)", "Öljyn hinnat", "USD/MMBtu", "IMF via FRED (PNGASEUUSDM)")
add("gasoline_us", fred_m("Gasoline_US_m"), "Bensiini USA (USD/gal)", "Polttoaineet", "USD/gal", "EIA via FRED (GASREGM)")
add("diesel_us", fred_m("Diesel_US_m"), "Diesel USA (USD/gal)", "Polttoaineet", "USD/gal", "EIA via FRED (GASDESM)")

# ---------- Inventories ----------
add("us_crude_stocks", to_monthly(eia("WCESTUS1w")) / 1000, "USA raakaöljyvarastot pl. SPR (milj. bbl)", "Varastot", "milj. bbl", "EIA WCESTUS1 (viikko→kk-keskiarvo)")
add("us_spr", to_monthly(eia("WCSSTUS1w")) / 1000, "USA strateginen varasto SPR (milj. bbl)", "Varastot", "milj. bbl", "EIA WCSSTUS1")
add("us_total_stocks", to_monthly(eia("WTTSTUS1w")) / 1000, "USA öljy+tuotteet varastot yht. (milj. bbl)", "Varastot", "milj. bbl", "EIA WTTSTUS1")
add("us_gasoline_stocks", to_monthly(eia("WGTSTUS1w")) / 1000, "USA bensiinivarastot (milj. bbl)", "Varastot", "milj. bbl", "EIA WGTSTUS1")
add("us_distillate_stocks", to_monthly(eia("WDISTUS1w")) / 1000, "USA tislevarastot (milj. bbl)", "Varastot", "milj. bbl", "EIA WDISTUS1")
add("cushing", to_monthly(eia("Cushing_w")) / 1000, "Cushing-varastot (milj. bbl)", "Varastot", "milj. bbl", "EIA W_EPC0_SAX_YCUOK")
add("us_crude_stock_chg", (to_monthly(eia("WCESTUS1w")) / 1000).diff(), "USA raakaöljyvarastojen muutos (milj. bbl/kk)", "Varastot", "milj. bbl/kk", "laskettu EIA:sta")

# ---------- STEO world balance splice ----------
def steo_sheet(path):
    x = pd.read_excel(path, sheet_name="3atab", header=None)
    years = [int(v) for v in x.iloc[2, 2:].tolist() if isinstance(v, (int, float)) and not pd.isna(v)]
    # year header row has year at the first column of each 12-month block; build date list from row 3 (month names) and row 2
    yrow = x.iloc[2, 2:].tolist(); mrow = x.iloc[3, 2:].tolist()
    dates = []; cur = None
    for y, m in zip(yrow, mrow):
        if isinstance(y, (int, float)) and not pd.isna(y): cur = int(y)
        dates.append(pd.Timestamp(year=cur, month=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(str(m)[:3]) + 1, day=1))
    rows = {}
    for i in range(4, x.shape[0]):
        code = x.iloc[i, 0]
        if isinstance(code, str) and code.strip():
            rows[code.strip()] = pd.Series(pd.to_numeric(x.iloc[i, 2:2 + len(dates)].values, errors="coerce"), index=dates)
    return rows

steo_files = [("steo_jan16_base.xlsx", "2014-01", "2015-12"), ("steo_jan18_base.xlsx", "2016-01", "2017-12"),
              ("steo_jan20_base.xlsx", "2018-01", "2019-12"), ("steo_jan22_base.xlsx", "2020-01", "2021-12"),
              ("steo_jan24_base.xlsx", "2022-01", "2023-12"), ("STEO_m.xlsx", "2024-01", pd.Timestamp.today().strftime("%Y-%m"))]
steo = {}
for fn, a, b in steo_files:
    rows = steo_sheet(f"{RAW}/{fn}")
    for code, s in rows.items():
        seg = s.loc[a:b]
        steo.setdefault(code, []).append(seg)
steo = {k: pd.concat(v).sort_index() for k, v in steo.items()}
steo = {k: v[~v.index.duplicated(keep="last")] for k, v in steo.items()}
add("world_prod", steo["papr_world"], "Maailman öljyntuotanto (mb/d)", "Tarjonta & kysyntä", "mb/d", "EIA STEO (arkistot + lokakuu 2026)")
add("world_cons", steo["patc_world"], "Maailman öljynkulutus (mb/d)", "Tarjonta & kysyntä", "mb/d", "EIA STEO")
add("opec_prod", steo["papr_opec"], "OPEC-tuotanto (mb/d)", "Tarjonta & kysyntä", "mb/d", "EIA STEO")
add("china_cons", steo["patc_ch"], "Kiinan öljynkulutus (mb/d)", "Tarjonta & kysyntä", "mb/d", "EIA STEO")
add("world_stock_draw", steo["t3_stchange_world"], "Maailman varastojen nettopurku (mb/d, + = purku)", "Varastot", "mb/d", "EIA STEO")
add("world_balance", steo["papr_world"] - steo["patc_world"], "Tarjonta–kysyntä-tase (mb/d)", "Tarjonta & kysyntä", "mb/d", "laskettu STEO:sta")
if "pasc_oecd_t3" in steo:
    add("oecd_stocks", steo["pasc_oecd_t3"], "OECD kaupalliset varastot (milj. bbl)", "Varastot", "milj. bbl", "EIA STEO (saatavilla 2018→)")

# ---------- US supply/demand ----------
add("us_prod", to_monthly(eia("WCRFPUS2w")) / 1000, "USA raakaöljyn tuotanto (mb/d)", "Tarjonta & kysyntä", "mb/d", "EIA WCRFPUS2 (viikko)")
add("us_exports", eia_m("CrudeExports_m") / 1000, "USA raakaöljyn vienti (mb/d)", "Tarjonta & kysyntä", "mb/d", "EIA MCREXUS2")
add("us_imports", eia_m("CrudeImports_m") / 1000, "USA raakaöljyn tuonti (mb/d)", "Tarjonta & kysyntä", "mb/d", "EIA MCRIMUS2")
add("us_product_supplied", eia_m("ProductSupplied_m") / 1000, "USA öljytuotteiden kulutus (mb/d)", "Tarjonta & kysyntä", "mb/d", "EIA MTTUPUS2")
add("us_jet_demand", eia_m("MKJUPUS2m") / 1000, "USA lentopetrolin kulutus (mb/d)", "Toimialat", "mb/d", "EIA MKJUPUS2")
add("us_ref_util", eia_m("RefUtil_m"), "USA jalostamoiden käyttöaste (%)", "Tarjonta & kysyntä", "%", "EIA MOPUEUS2")
add("us_rigs", eia_m("Rigs_m"), "USA öljynporauslautat (kpl)", "Tarjonta & kysyntä", "kpl", "EIA/Baker Hughes (E_ERTRRO_XR0_NUS_C)")

# ---------- Sectors ----------
for k, n, lab in [("ip_total", "IP_total", "Teollisuustuotanto USA (indeksi)"), ("ip_manuf", "IP_manuf", "Valmistava teollisuus USA"),
                  ("ip_mining", "IP_mining", "Kaivannaisteollisuus USA"), ("ip_oilgas", "IP_oilgas_extr", "Öljyn & kaasun tuotanto USA (IP)"),
                  ("ip_drilling", "IP_drilling", "Poraustoiminta USA (IP)"), ("ip_chem", "IP_chem", "Kemianteollisuus USA (IP)"),
                  ("ip_autos", "IP_autos", "Autoteollisuus USA (IP)"), ("ip_refining", "IP_petrol_coal", "Jalostus & hiilituotteet USA (IP)")]:
    add(k, fred_m(n), lab, "Toimialat", "indeksi 2017=100", f"FRED ({n})")
add("air_rpm", fred_m("AirRPM") / 1e6, "Lentoliikenne USA (mrd matkustaja-mailia)", "Toimialat", "mrd RPM", "BTS via FRED (AIRRPMTSI)")
add("vmt", fred_m("VMT") / 1000, "Ajosuorite USA (mrd mailia/kk)", "Toimialat", "mrd mailia", "FHWA via FRED (TRFVOLUSM227NFWA)")
add("tsi_freight", fred_m("TSI_freight"), "Rahtiliikenneindeksi USA (TSI)", "Rahti", "indeksi", "BTS via FRED (TSIFRGHT)")
add("cass", fred_m("Cass_shipments"), "Cass Freight -lähetysindeksi USA", "Rahti", "indeksi", "FRED (FRGSHPUSM649NCIS)")
add("vehicle_sales_us", fred_m("VehicleSales_US"), "Autojen myynti USA (milj./v, SAAR)", "Toimialat", "milj. kpl/v", "BEA via FRED (TOTALSA)")

# ---------- Macro ----------
gdp_us = fred_m("GDP_US_q"); gdp_us.index = gdp_us.index + pd.offsets.MonthBegin(0)
add("gdp_us", gdp_us.resample("MS").interpolate(), "BKT USA, reaalinen (mrd USD 2017, kvartaali→kk)", "Makrotalous", "mrd USD", "BEA via FRED (GDPC1)", freq="quarterly")
gdp_de = fred_m("GDP_DE_q")
add("gdp_de", (gdp_de / 1000).resample("MS").interpolate(), "BKT Saksa, reaalinen (mrd EUR 2010, kvartaali→kk)", "Makrotalous", "mrd EUR", "Eurostat via FRED (CLVMNACSCAB1GQDE)", freq="quarterly")
add("cpi_us", fred_m("CPI_US"), "Kuluttajahinnat USA (CPI)", "Makrotalous", "indeksi", "BLS via FRED (CPIAUCSL)")
add("cpi_energy_us", fred_m("CPI_energy_US"), "Energian kuluttajahinnat USA (CPI energy)", "Makrotalous", "indeksi", "BLS via FRED (CPIENGSL)")
add("fedfunds", fred_m("FedFunds"), "Fed-ohjauskorko (%)", "Makrotalous", "%", "FRED (FEDFUNDS)")
add("ust10y", fred_m("UST10y"), "USA 10 v korko (%)", "Makrotalous", "%", "FRED (GS10)")
add("unemp_us", fred_m("Unemp_US"), "Työttömyys USA (%)", "Makrotalous", "%", "BLS via FRED (UNRATE)")
add("usd_broad", to_monthly(fred("DollarBroad_d")), "Dollari-indeksi (broad)", "Makrotalous", "indeksi", "Fed via FRED (DTWEXBGS)")
add("sp500", to_monthly(fred("SP500_d")), "S&P 500", "Makrotalous", "pistettä", "FRED (SP500)")
add("vix", to_monthly(fred("VIX_d")), "VIX-volatiliteetti", "Makrotalous", "pistettä", "Cboe via FRED (VIXCLS)")

# ---------- Materials ----------
for k, n, lab, unit in [("copper", "Copper", "Kupari (USD/t)", "USD/t"), ("aluminum", "Aluminum", "Alumiini (USD/t)", "USD/t"),
                        ("iron_ore", "IronOre", "Rautamalmi (USD/t)", "USD/t"), ("nickel", "Nickel", "Nikkeli (USD/t)", "USD/t"),
                        ("steel_ppi", "Steel_PPI", "Teräs, tuottajahinnat USA (PPI)", "indeksi"), ("lumber_ppi", "Lumber_PPI", "Puutavara, PPI USA", "indeksi"),
                        ("commod_all", "Commodities_all", "Raaka-aineindeksi, kaikki (IMF)", "indeksi"), ("metals_idx", "Metals_idx", "Metalli-indeksi (IMF)", "indeksi"),
                        ("energy_idx", "Energy_idx", "Energiaindeksi (IMF)", "indeksi"), ("food_idx", "Food_idx", "Ruokaindeksi (IMF)", "indeksi"),
                        ("nonfuel_idx", "NonFuel_idx", "Ei-energia-raaka-aineet (IMF)", "indeksi"), ("ppi_all", "PPI_all", "Tuottajahinnat USA (PPI, kaikki)", "indeksi")]:
    add(k, fred_m(n), lab, "Raaka-aineet", unit, f"FRED ({n})")

# ---------- Climate & energy ----------
def gistemp(name):
    d = pd.read_csv(f"{RAW}/gistemp_{name}.csv", skiprows=1)
    rows = []
    for _, r in d.iterrows():
        for mi, mn in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]):
            v = pd.to_numeric(r[mn], errors="coerce")
            rows.append((pd.Timestamp(year=int(r["Year"]), month=mi + 1, day=1), v))
    return pd.Series(dict(rows)).sort_index()
add("temp_global", gistemp("GLB"), "Lämpötilapoikkeama, maapallo (°C vs 1951–80)", "Ilmasto & energia", "°C", "NASA GISTEMP v4")
add("temp_nh", gistemp("NH"), "Lämpötilapoikkeama, pohj. pallonpuolisko (°C)", "Ilmasto & energia", "°C", "NASA GISTEMP v4")
te = pd.read_csv(f"{RAW}/eia_totalenergy_T07.02A.csv")
w = te[te["MSN"] == "WYETPUS"].copy(); w = w[w["YYYYMM"].astype(str).str[-2:] != "13"]
w["date"] = pd.to_datetime(w["YYYYMM"].astype(str), format="%Y%m"); w["value"] = pd.to_numeric(w["Value"], errors="coerce")
add("wind_gen_us", w.set_index("date")["value"] / 1000, "Tuulisähkö USA (TWh/kk)", "Ilmasto & energia", "TWh", "EIA Total Energy (WYETPUS)")
tot = te[te["MSN"] == "ELETPUS"].copy(); tot = tot[tot["YYYYMM"].astype(str).str[-2:] != "13"]
tot["date"] = pd.to_datetime(tot["YYYYMM"].astype(str), format="%Y%m"); tot["value"] = pd.to_numeric(tot["Value"], errors="coerce")
add("wind_share_us", (w.set_index("date")["value"] / tot.set_index("date")["value"] * 100), "Tuulen osuus sähköstä USA (%)", "Ilmasto & energia", "%", "laskettu EIA:sta")

# ---------- Freight ----------
bdi = pd.read_csv(f"{RAW}/bdi_daily.csv"); bdi["date"] = pd.to_datetime(bdi["date"])
add("bdi", to_monthly(bdi.set_index("date")["value"]), "Baltic Dry Index (kuivarahti)", "Rahti", "pistettä", "Baltic Exchange (stock-marketdata.com)")
for n, lab in [("FBX", "Freightos FBX konttirahti (USD/FEU)"), ("WCI", "Drewry WCI konttirahti (USD/FEU)"), ("SCFI", "Shanghai SCFI konttirahti"), ("CCFI", "China CCFI konttirahti")]:
    f = pd.read_csv(f"{RAW}/freight_{n}.csv"); f["date"] = pd.to_datetime(f["date"])
    add(f"freight_{n.lower()}", to_monthly(f.set_index("date")["value"]), lab, "Rahti", "indeksi", f"{n} (stock-marketdata.com)")

# ---------- Positioning ----------
cot = pd.read_csv(f"{RAW}/cftc_wti_cot.csv"); cot["date"] = pd.to_datetime(cot["date"])
add("mm_net_wti", to_monthly(cot.set_index("date")["mm_net"]) / 1000, "Rahastojen nettopositio WTI (tuhatta sopimusta)", "Positiot", "tuhatta sop.", "CFTC COT (managed money, NYMEX WTI)")
add("oi_wti", to_monthly(cot.set_index("date")["oi"]) / 1000, "Avoin positio WTI (tuhatta sopimusta)", "Positiot", "tuhatta sop.", "CFTC COT")

M.index.name = "date"
M.to_csv(f"{OUT}/panel_monthly.csv", float_format="%.4f")

# ---------- Annual panel ----------
A = pd.DataFrame(index=pd.Index(range(2010, 2027), name="year")); AMETA = {}
def adda(key, s, label, group, unit, source, note=""):
    s = pd.Series(s).dropna(); s.index = s.index.astype(int)
    A[key] = s.reindex(A.index)
    AMETA[key] = dict(label=label, group=group, unit=unit, source=source, freq="annual", note=note,
                      first=int(s.index.min()) if len(s) else None, last=int(s.index.max()) if len(s) else None)
wb = pd.read_csv(f"{RAW}/worldbank.csv")
def wbs(ind, iso):
    d = wb[(wb.indicator == ind) & (wb.iso3 == iso)]; return pd.Series(d.value.values, index=d.year.values)
cn = {"USA": "USA", "CHN": "Kiina", "DEU": "Saksa", "IND": "Intia", "WLD": "maailma"}
for iso in ["USA", "CHN", "DEU"]:
    adda(f"gdp_growth_{iso.lower()}", wbs("GDPgrowth", iso), f"BKT:n kasvu {cn[iso]} (%)", "Makrotalous", "%", "World Bank NY.GDP.MKTP.KD.ZG")
    adda(f"gdp_pc_ppp_{iso.lower()}", wbs("GDPpcPPP", iso), f"BKT/asukas PPP {cn[iso]} (USD 2021)", "Väestö & elintaso", "USD", "World Bank NY.GDP.PCAP.PP.KD")
    adda(f"birth_rate_{iso.lower()}", wbs("BirthRate", iso), f"Syntyvyys {cn[iso]} (per 1000)", "Väestö & elintaso", "per 1000", "World Bank SP.DYN.CBRT.IN")
    adda(f"tertiary_enrol_{iso.lower()}", wbs("TertiaryEnrol", iso), f"Korkeakouluopiskelijat {cn[iso]} (% ikäluokasta, brutto)", "Väestö & elintaso", "%", "World Bank SE.TER.ENRR")
adda("birth_rate_wld", wbs("BirthRate", "WLD"), "Syntyvyys maailma (per 1000)", "Väestö & elintaso", "per 1000", "World Bank")
adda("gdp_growth_wld", wbs("GDPgrowth", "WLD"), "BKT:n kasvu maailma (%)", "Makrotalous", "%", "World Bank")
def owid(slug, col, entity):
    d = pd.read_csv(f"{RAW}/owid_{slug}.csv"); d = d[d.entity == entity]; return pd.Series(d[col].values, index=d.year.values)
ent = {"USA": "United States", "CHN": "China", "DEU": "Germany"}
for iso in ["USA", "CHN", "DEU"]:
    adda(f"hdi_{iso.lower()}", owid("human-development-index", "hdi__sex_total", ent[iso]), f"Inhimillisen kehityksen indeksi HDI {cn[iso]}", "Väestö & elintaso", "indeksi 0–1", "UNDP via OWID")
    adda(f"tertiary_attain_{iso.lower()}", owid("share-of-the-population-with-completed-tertiary-education", "mf_adults__25_64_years__percentage_of_tertiary_education", ent[iso]), f"Korkeakoulutettujen osuus 25–64 v {cn[iso]} (%)", "Väestö & elintaso", "%", "OECD via OWID")
    cs = pd.read_csv(f"{RAW}/owid_car-sales.csv"); cs = cs[cs.entity == ent[iso]]
    adda(f"car_sales_{iso.lower()}", pd.Series((cs.ev_sales + cs.non_ev_cars_sold).values / 1e6, index=cs.year.values), f"Henkilöautojen myynti {cn[iso]} (milj. kpl)", "Toimialat", "milj. kpl", "IEA via OWID (ev + non-ev)")
    adda(f"ev_share_{iso.lower()}", owid("electric-car-sales-share", "ev_sales_share", ent[iso]), f"Sähköautojen osuus myynnistä {cn[iso]} (%)", "Teknologia", "%", "IEA via OWID")
adda("ev_share_wld", owid("electric-car-sales-share", "ev_sales_share", "World"), "Sähköautojen osuus myynnistä, maailma (%)", "Teknologia", "%", "IEA via OWID")
adda("wind_gen_wld", owid("wind-generation", "wind_generation__twh", "World"), "Tuulisähkö maailma (TWh)", "Ilmasto & energia", "TWh", "Energy Institute via OWID")
adda("solar_gen_wld", owid("solar-energy-consumption", "solar_generation__twh", "World"), "Aurinkosähkö maailma (TWh)", "Ilmasto & energia", "TWh", "Energy Institute via OWID")
adda("oil_cons_wld", owid("oil-consumption-by-country", "oil_consumption_twh", "World") / 1000, "Öljynkulutus maailma (tuhatta TWh)", "Tarjonta & kysyntä", "PWh", "Energy Institute via OWID")
adda("oil_cons_chn", owid("oil-consumption-by-country", "oil_consumption_twh", "China") / 1000, "Öljynkulutus Kiina (tuhatta TWh)", "Tarjonta & kysyntä", "PWh", "Energy Institute via OWID")
# annual averages of key monthly series for the annual correlation table
for k in ["brent", "wti", "dubai", "gasoline_us", "us_crude_stocks", "bdi", "copper", "usd_broad", "sp500", "temp_global", "vehicle_sales_us"]:
    adda(f"{k}_avg", M[k].groupby(M.index.year).mean().where(M[k].groupby(M.index.year).count() >= 6), META[k]["label"] + " (vuosikeskiarvo)", META[k]["group"], META[k]["unit"], META[k]["source"])
A.to_csv(f"{OUT}/panel_annual.csv", float_format="%.4f")
json.dump({"monthly": META, "annual": AMETA}, open(f"{OUT}/series_meta.json", "w"), ensure_ascii=False, indent=1)
print("monthly", M.shape, "annual", A.shape)
for k, m in META.items(): print(f"{k:22} {m['first']} → {m['last']}  {m['label']}")
print(A.loc[2015:2026].T.to_string(max_cols=12))

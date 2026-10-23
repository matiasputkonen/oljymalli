#!/usr/bin/env python3
"""Assemble data + analysis into a self-contained HTML page (Plotly from cdnjs)."""
import json, math, numpy as np, pandas as pd
D = "/home/claude/oil/data"
M = pd.read_csv(f"{D}/panel_monthly.csv", index_col=0, parse_dates=True)
A = pd.read_csv(f"{D}/panel_annual.csv", index_col=0)
META = json.load(open(f"{D}/series_meta.json"))
R = json.load(open(f"{D}/analysis.json"))
dates = [d.strftime("%Y-%m-%d") for d in M.index]

def clean(v):
    return None if (v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))) else round(float(v), 4)

GROUP_ORDER = ["Öljyn hinnat", "Polttoaineet", "Varastot", "Tarjonta & kysyntä", "Toimialat", "Rahti", "Makrotalous", "Raaka-aineet", "Ilmasto & energia", "Väestö & elintaso", "Teknologia", "Positiot"]
DEFAULT_ON = {"brent", "wti", "dubai", "gasoline_us", "oecd_stocks", "world_balance", "usd_broad", "sp500", "copper", "bdi", "temp_global", "mm_net_wti", "gdp_growth_wld", "ev_share_wld", "vehicle_sales_us", "us_rigs"}
series = []
for k, m in META["monthly"].items():
    vals = [clean(v) for v in M[k].values]
    series.append(dict(key=k, label=m["label"], group=m["group"], unit=m["unit"], freq=m["freq"], source=m["source"], first=m["first"], last=m["last"], values=vals, on=(k in DEFAULT_ON)))
# annual -> monthly interpolation (value placed at July of each year, linear in between, no extrapolation)
for k, m in META["annual"].items():
    if k.endswith("_avg"): continue
    s = A[k].dropna()
    if len(s) < 3: continue
    pts = pd.Series(s.values, index=[pd.Timestamp(year=int(y), month=7, day=1) for y in s.index])
    interp = pts.reindex(pts.index.union(M.index)).interpolate(method="time").reindex(M.index)
    interp[(M.index < pts.index.min()) | (M.index > pts.index.max())] = np.nan
    series.append(dict(key=k, label=m["label"] + " ◦", group=m["group"], unit=m["unit"], freq="annual", source=m["source"], first=str(int(s.index.min())), last=str(int(s.index.max())),
                       values=[clean(v) for v in interp.values], annual={str(int(y)): clean(v) for y, v in s.items()}, on=(k in DEFAULT_ON)))
series.sort(key=lambda d: (GROUP_ORDER.index(d["group"]) if d["group"] in GROUP_ORDER else 99))

EVENTS = [
    ("2015-12", "USA sallii raakaöljyn viennin (18.12.2015); OPEC pumppaa markkinaosuuden puolesta", "pol"),
    ("2016-01", "Pohja: Brent n. 30 $ – ylitarjonta, Kiina-pelot", "mkt"),
    ("2016-11", "OPEC+ syntyy: 1,8 mb/d leikkaus (30.11.2016)", "pol"),
    ("2018-05", "USA irtautuu Iranin ydinsopimuksesta; pakotteet palaavat", "geo"),
    ("2018-11", "Keltaliivit Ranskassa polttoaineveron takia; Brent 86 $ → Q4-romahdus; OPEC+ leikkaa 1,2 mb/d", "pub"),
    ("2019-09", "Abqaiq-drooni-isku: Saudi-tuotanto –5,7 mb/d hetkellisesti", "geo"),
    ("2019-12", "Saudi Aramcon listautuminen (1,7 bilj. $)", "corp"),
    ("2020-03", "COVID-sulut + Saudi–Venäjä-hintasota", "mkt"),
    ("2020-04", "WTI –37 $ (20.4.); OPEC+ 9,7 mb/d leikkaus", "pol"),
    ("2021-11", "USA vapauttaa 50 mb SPR:stä; Euroopan kaasukriisi", "pol"),
    ("2022-02", "Venäjä hyökkää Ukrainaan (24.2.); Brent 128 $ (8.3.)", "geo"),
    ("2022-03", "IEA 60 mb + USA 180 mb SPR-vapautus", "pol"),
    ("2022-06", "USA:n bensa 5 $/gal; Fed +75 bp; julkinen paine ennätys", "pub"),
    ("2022-10", "OPEC+ leikkaa 2 mb/d", "pol"),
    ("2022-12", "EU-embargo Venäjän öljylle + G7 hintakatto 60 $", "pol"),
    ("2023-04", "OPEC+ yllätysleikkaus 1,16 mb/d; Saudi +1 mb/d heinäkuussa", "pol"),
    ("2023-10", "Hamasin isku 7.10.; Exxon–Pioneer 60 mrd $ ja Chevron–Hess 53 mrd $", "corp"),
    ("2023-12", "Huthien iskut Punaisellamerellä alkavat → konttirahti nousee", "geo"),
    ("2024-09", "Brent alle 70 $: Kiinan kysyntä heikko, OPEC+ purkamisaikeet", "mkt"),
    ("2025-01", "USA pakottaa Venäjän öljy-yhtiöitä ja 183 tankkeria (10.1.)", "pol"),
    ("2025-04", "Tullishokki (2.4.) + OPEC+ kiihdyttää leikkausten purkua; Brent n. 60 $", "pol"),
    ("2025-06", "Israel–Iran 12 päivän sota (13.–24.6.)", "geo"),
    ("2025-10", "USA pakottaa Rosneftin ja Lukoilin; rahastot nettolyhyenä WTI:ssä", "pol"),
    ("2026-02", "USA & Israel iskevät Iraniin 28.2.; Hormuz sulkeutuu; Khamenei kuolee", "geo"),
    ("2026-03", "Brent >100 $ (8.3.), Dubai 166 $ (19.3.); IEA 400 mb; Saudi –20 %; Qatar LNG force majeure", "geo"),
    ("2026-04", "Tulitauko 8.4.; USA:n merisaarto 13.4.; Brent 126 $ (30.4.); Saksa laskee polttoaineveroa", "pol"),
    ("2026-05", "UAE eroaa OPEC:sta; Spirit Airlines lopettaa; Devon–Coterra-fuusio; OPEC+ 'symbolinen' +188 kb/d", "corp"),
    ("2026-06", "Islamabadin sopimus 17.6.; Brent n. 70 $ heinäkuun alussa", "pol"),
    ("2026-07", "Sopimus romahtaa 8.7.; saarto palaa 14.7.; Brent >100 $; huthit kieltävät Saudi-satamat 20.7.", "geo"),
    ("2026-08", "Yanbu-lastaukset 'pimeinä' (AIS pois): Vortexa 2,4 / Kpler 1,8 / AXSMarine <1 mb/d; Bab el-Mandeb 32 alusta/pv (ennen 50)", "mkt"),
    ("2026-09", "Uudet tankkeri-iskut; Saudi itä–länsi-putki vaurioituu; VLCC >700 000 $/pv; USA:n diesel 6,53 $/gal (ennätys)", "mkt"),
    ("2026-10", "Huthit iskevät Riadiin; SPR alin sitten 1982; Brent 112 $; Trump höllentää Venäjä-pakotteita", "geo"),
]
events = [dict(n=i + 1, date=d + "-01", text=t, kind=k) for i, (d, t, k) in enumerate(EVENTS)]

# ---------- analysis tables for the page ----------
lab = {k: v["label"] for k, v in META["monthly"].items()}
def top(lst, n, key="r"): return [dict(label=d["label"], r=d[key], n=d["n"], group=d.get("group", "")) for d in lst[:n]]
level_top = [d for d in R["level_corr_vs_brent"] if d["series"] not in ("wti", "apsp", "dubai", "energy_idx", "commod_all")][:14]
change_top = [d for d in R["change_corr_vs_brent"] if d["series"] not in ("wti", "apsp", "dubai", "energy_idx", "commod_all")][:16]
change_zero = sorted(R["change_corr_vs_brent"], key=lambda d: abs(d["r"]))[:10]
sub_keys = ["usd_broad", "sp500", "vix", "mm_net_wti", "gasoline_us", "us_crude_stocks", "oecd_stocks", "world_balance", "opec_prod", "us_rigs", "copper", "bdi"]
sub_tbl = [dict(label=lab[k], vals=[R["subperiod_change_corr"][p].get(k) for p in R["subperiod_change_corr"]]) for k in sub_keys]
sub_periods = list(R["subperiod_change_corr"].keys())
ll_keys = ["us_rigs", "ip_drilling", "ip_oilgas", "us_prod", "us_jet_demand", "ip_mining", "vix", "fedfunds", "us_crude_stocks", "us_total_stocks", "bdi", "mm_net_wti", "sp500", "copper", "usd_broad"]
ll_tbl = [dict(label=lab[k], lag=R["lead_lag"][k]["best_lag"], r=R["lead_lag"][k]["best_r"], r0=R["lead_lag"][k]["contemporaneous"]) for k in ll_keys if k in R["lead_lag"]]
gr_tbl = [dict(cause=g["cause_label"], effect=g["effect_label"], p1=g["p"].get("lag1"), p2=g["p"].get("lag2"), p3=g["p"].get("lag3")) for g in R["granger"] if "lag1" in g["p"]]
ann_tbl = [dict(label=d["label"], n=d["n"], r=d["r_level"], p=d["p_level"], rc=d["r_change"]) for d in R["annual_corr_vs_brent"] if not d["label"].endswith("(vuosikeskiarvo)")][:14]
roll = {k: R["rolling24"][k] for k in ["usd_broad", "sp500", "vix", "us_crude_stocks", "oecd_stocks", "mm_net_wti"]}
page_data = dict(dates=dates, series=series, events=events, groups=GROUP_ORDER, analysis=dict(level_top=level_top, change_top=change_top, change_zero=change_zero, sub=dict(periods=sub_periods, rows=sub_tbl),
                 leadlag=ll_tbl, granger=gr_tbl, predictive=R["predictive"], inv=R["inventory_curve"], inv_us=R["inventory_curve_us"], annual=ann_tbl, stats=R["stats"], roll=roll))
json.dump(page_data, open(f"{D}/page_data.json", "w"), ensure_ascii=False)
print("series:", len(series), "events:", len(events), "json bytes:", len(json.dumps(page_data, ensure_ascii=False)))

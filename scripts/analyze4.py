#!/usr/bin/env python3
"""Consensus-surprise reaction, current futures curve vs model, PortWatch port-level AIS flows."""
import json, glob, os, numpy as np, pandas as pd, statsmodels.api as sm, warnings; warnings.filterwarnings("ignore")
R3 = "/home/claude/oil/data/raw3"; D = "/home/claude/oil/data"
def rd(name):
    d = pd.read_csv(f"{R3}/eia_{name}.csv", parse_dates=["date"]); return d.set_index("date")["value"].astype(float).sort_index()
cl1 = rd("cl1"); wti = rd("wti_spot"); brent = rd("brent_spot"); rb1 = rd("rb1"); ho1 = rd("ho1")
px = cl1.combine_first(wti[wti.index > cl1.index.max()])   # CL1 to 4/2024, WTI spot after
r = np.log(px).diff()
print("=== 1. EIA-KONSENSUSYLLÄTYS (investing.com) → raporttipäivän tuotto ===")
c = pd.read_csv(f"{R3}/eia_crude_consensus_investing.csv"); c["date"] = pd.to_datetime(c["time"].str[:10]); c = c.dropna(subset=["forecast"]).sort_values("date")
c["surprise"] = c["actual"] - c["forecast"]
c["r"] = c["date"].map(r); c["r_rb"] = c["date"].map(np.log(rb1).diff()); c["r_ho"] = c["date"].map(np.log(ho1).diff()); c["r_next"] = c["date"].map(r.shift(-1))
c = c.dropna(subset=["r"])
for a, b in [("2011", "2026"), ("2015", "2019"), ("2020", "2021"), ("2022", "2025"), ("2026", "2026")]:
    s = c[(c.date >= a) & (c.date <= f"{b}-12-31")]
    m = sm.OLS(s.r * 100, sm.add_constant(s.surprise)).fit()
    print(f"  {a}-{b}: n={len(s):3d} r(yllätys, tuotto)={s.surprise.corr(s.r):+.2f}  kerroin {m.params['surprise']:+.3f} %/mb (p={m.pvalues['surprise']:.4f})  |yllätys| mediaani {s.surprise.abs().median():.1f} mb")
s = c[c.date >= "2015"]
print(f"  2015→: seuraavan päivän tuotto vs yllätys r={s.surprise.corr(s.r_next):+.2f} (ei jatkoreaktiota); RBOB r={s.surprise.corr(s.r_rb):+.2f}; HO r={s.surprise.corr(s.r_ho):+.2f}")
q = pd.qcut(s.surprise, 5, labels=["suuri purku-yllätys", "purku", "neutraali", "kertymä", "suuri kertymä-yllätys"])
print("  kvintiilit → raporttipäivän tuotto %:"); print((s.groupby(q).r.mean() * 100).round(2).to_string())
m = sm.OLS(s.r * 100, sm.add_constant(s.surprise)).fit(); res = s.r * 100 - m.predict(sm.add_constant(s.surprise))
print(f"  2015→: R² {m.rsquared:.3f}; raporttipäivän tuoton hajonta {s.r.std()*100:.2f} % → yllätyksen jälkeen {res.std():.2f} %")
# asymmetry
big = s[s.surprise.abs() >= 3]; print(f"  |yllätys| ≥ 3 mb (n={len(big)}): keskituotto purku-yllätys {big[big.surprise<0].r.mean()*100:+.2f} %, kertymä-yllätys {big[big.surprise>0].r.mean()*100:+.2f} %")
# consensus accuracy itself
print(f"  Konsensuksen oma tarkkuus 2015→: r(ennuste, toteuma)={s.forecast.corr(s.actual):+.2f}, virheen keskihajonta {s.surprise.std():.1f} mb, toteuman hajonta {s.actual.std():.1f} mb")
c.to_csv(f"{D}/eia_consensus_reactions.csv", index=False)

print("\n=== 2. TERMIINIKÄYRÄ 21.10.2026 (CME) ===")
cv = pd.read_csv(f"{R3}/cme_curves_2026-10.csv")
for p in ["CL", "BZ"]:
    s = cv[(cv["product"] == p) & (cv.trade_date == "2026-10-21")]
    get = lambda m: float(s[s.contract == m].settle.iloc[0])
    print(f"  {p}: Dec-26 {get('DEC 26'):.1f} | Jun-27 {get('JUN 27'):.1f} | Dec-27 {get('DEC 27'):.1f} | Dec-28 {get('DEC 28'):.1f} | Dec-29 {get('DEC 29'):.1f} | Dec-30 {get('DEC 30'):.1f}  → 12 kk backwardaatio {get('DEC 26')-get('DEC 27'):.1f} $ ({(get('DEC 26')/get('DEC 27')-1)*100:.0f} %)")
# Yahoo contract histories: Dec26-Dec27 spread history as 1-yr slope proxy
def yh(sym):
    j = json.load(open(f"{R3}/yahoo/{sym}.json")); res = j["chart"]["result"][0]
    return pd.Series(res["indicators"]["quote"][0]["close"], index=pd.to_datetime(res["timestamp"], unit="s").normalize()).dropna()
try:
    z26, z27, x26 = yh("CLZ26.NYM"), yh("CLZ27.NYM"), yh("CLX26.NYM")
    sp = (z26 - z27).dropna(); spm = sp.resample("MS").mean()
    print("  Dec26–Dec27 -spread (USD), kk-keskiarvo:"); print(spm.loc["2025-01":].round(2).to_string())
    bz26, bz27 = yh("BZZ26.NYM"), yh("BZZ27.NYM"); bsp = (bz26 - bz27).dropna().resample("MS").mean()
    print("  Brent Dec26–Dec27:", bsp.loc["2026-01":].round(2).to_dict())
    pd.DataFrame({"CLZ26": z26, "CLZ27": z27, "CLX26": x26, "BZZ26": bz26, "BZZ27": bz27}).to_csv(f"{D}/yahoo_contracts_daily.csv")
except Exception as e: print("yahoo err", e)

print("\n=== 3. PORTWATCH SATAMAT (AIS): tankkerivienti ja -tuonti ===")
pw = pd.read_csv(f"{R3}/portwatch_ports.csv", parse_dates=["date"])
pv = pw.pivot_table(index="date", columns="portname", values="export_tanker").resample("MS").sum() / 1e6  # million tons per month
gulf = ["Ras Tanura", "Juaymah", "Yanbu (King Fahd Port)", "Mina Al Ahmadi", "Al Basrah", "Fujairah", "Jebel Ali", "Bandar Abbas"]
gulf = [g for g in gulf if g in pv.columns]
us = [c for c in ["Corpus Christi", "Houston (US-TX)", "Beaumont", "South Louisiana"] if c in pv.columns]
ru = [c for c in ["Primorsk", "Novorossiysk", "Ust-Luga"] if c in pv.columns]
pd.set_option("display.width", 220)
tab = pd.DataFrame({"Persianlahti (sis. Yanbu)": pv[gulf].sum(axis=1), "USA Gulf": pv[us].sum(axis=1), "Venäjä (Itämeri+Musta meri)": pv[ru].sum(axis=1)})
print("  Tankkerivienti, milj. tonnia/kk:"); print(tab.loc["2025-10":].round(1).T.to_string())
print("  2019–2025 keskiarvo:", tab.loc["2019":"2025"].mean().round(1).to_dict())
imp = pw.pivot_table(index="date", columns="portname", values="import_tanker").resample("MS").sum() / 1e6
cn = [c for c in ["Qingdao Port", "Ningbo"] if c in imp.columns]
print("  Kiinan tankkerituonti Qingdao+Ningbo milj. t/kk:", imp[cn].sum(axis=1).loc["2025-10":].round(1).to_dict())
# Yanbu (Red Sea) vs Ras Tanura (Gulf) in 2026 -> pipeline rerouting
for p in ["Ras Tanura", "Yanbu (King Fahd Port)", "Fujairah", "Al Basrah", "Corpus Christi", "Primorsk"]:
    if p in pv.columns: print(f"  {p:24} 2025 ka {pv[p].loc['2025'].mean():.2f} → 2026 Mar {pv[p].get('2026-03-01', np.nan):.2f}, Jun {pv[p].get('2026-06-01', np.nan):.2f}, Sep {pv[p].get('2026-09-01', np.nan):.2f} milj. t/kk")
# weekly Gulf exports vs Brent weekly returns 2026
wk = pw[pw.portname.isin(gulf)].groupby("date").export_tanker.sum().resample("W-FRI").sum()
bw = np.log(brent.resample("W-FRI").last()).diff()
z = pd.concat([wk.pct_change().rename("dexp"), bw.rename("rb")], axis=1).dropna()
for a, b in [("2019", "2025"), ("2026-03", "2026-10")]:
    s = z.loc[a:b]; print(f"  Persianlahden viikkoviennin %-muutos vs Brent: {a}..{b} sama vko r={s.dexp.corr(s.rb):+.2f}, seuraava vko r={s.dexp.corr(s.rb.shift(-1)):+.2f} (n={len(s)})")
tab.to_csv(f"{D}/portwatch_exports_monthly.csv")
print("DONE")

#!/usr/bin/env python3
"""Analyses on the new daily datasets: term structure, EIA report-day reactions, Hormuz transits, GoM hurricanes, CPC HDD forecasts."""
import os, re, glob, json, numpy as np, pandas as pd, statsmodels.api as sm, warnings
from pandas.tseries.holiday import USFederalHolidayCalendar
warnings.filterwarnings("ignore")
RAW = "/home/claude/oil/data/raw"; R3 = "/home/claude/oil/data/raw3"; OUT = "/home/claude/oil/data"
res = {}
def rd(name):
    d = pd.read_csv(f"{R3}/eia_{name}.csv", parse_dates=["date"]); return d.set_index("date")["value"].astype(float).sort_index()
cl1, cl2, cl3, cl4 = rd("cl1"), rd("cl2"), rd("cl3"), rd("cl4"); ho1, rb1, ng1 = rd("ho1"), rd("rb1"), rd("ng1"); brent = rd("brent_spot")
wti_spot = rd("wti_spot"); cl1 = cl1.combine_first(wti_spot[wti_spot.index > cl1.index.max()])
px = pd.concat([cl1.rename("cl1"), cl2.rename("cl2"), cl3.rename("cl3"), cl4.rename("cl4"), ho1.rename("ho1"), rb1.rename("rb1"), ng1.rename("ng1"), brent.rename("brent")], axis=1).loc["2010":]
px["m1m2"] = px.cl1 - px.cl2; px["m1m4"] = px.cl1 - px.cl4; px["m1m4_pct"] = px.m1m4 / px.cl1 * 100
px["ho_crack"] = px.ho1 * 42 - px.cl1; px["rb_crack"] = px.rb1 * 42 - px.cl1
r1 = np.log(px.cl1).diff()
print("=== 1. TERMIINIKÄYRÄ (NYMEX CL1-CL4, EIA) ===")
m = px.resample("MS").mean()
print("M1-M2 (USD): 2015-19 %.2f | 2020 %.2f | 2021-22 %.2f | 2023-25 %.2f | 2026 %.2f" % tuple(m.loc[a:b, "m1m2"].mean() for a, b in [("2015", "2019"), ("2020", "2020"), ("2021", "2022"), ("2023", "2025"), ("2026", "2026")]))
print("M1-M2 ääriarvot:", "min %.2f (%s)" % (px.m1m2.min(), px.m1m2.idxmin().date()), "max %.2f (%s)" % (px.m1m2.max(), px.m1m2.idxmax().date()))
print("2026 kuukausittain M1-M2 / M1-M4:", m.loc["2026", ["m1m2", "m1m4"]].round(2).T.to_string())
# spread vs Cushing stock change next 4/8 weeks
cush = pd.read_csv(f"{RAW}/eia_Cushing_w.csv", parse_dates=["date"]).dropna().set_index("date")["value"] / 1000
spw = px.m1m2.resample("W-FRI").mean()
z = pd.concat([spw.rename("sp"), cush.diff(4).shift(-4).rename("dc4"), cush.diff(8).shift(-8).rename("dc8")], axis=1).dropna().loc["2015":]
print("M1-M2 (backwardaatio +) vs Cushing-muutos seuraavat 4 vko r=%.2f, 8 vko r=%.2f (n=%d)" % (z.sp.corr(z.dc4), z.sp.corr(z.dc8), len(z)))
# predictive: m1m4_pct at month end vs next h-month cl1 return, OOS
mm = px.resample("MS").last().loc["2010":]; lp = np.log(mm.cl1)
for h in [1, 3, 6]:
    fwd = lp.shift(-h) - lp
    d = pd.concat([fwd.rename("y"), mm.m1m4_pct.rename("x")], axis=1).dropna().loc["2012":]
    em, e0, hit = [], [], []
    for t in d.index[d.index >= pd.Timestamp("2018-01-01")]:
        tr = d.loc[:t].iloc[:-h]
        if len(tr) < 36: continue
        mod = sm.OLS(tr.y, sm.add_constant(tr.x)).fit(); p = mod.params["const"] + mod.params["x"] * d.loc[t, "x"]
        em.append(d.loc[t, "y"] - p); e0.append(d.loc[t, "y"]); hit.append(np.sign(p) == np.sign(d.loc[t, "y"]))
    ratio = np.sqrt(np.mean(np.square(em))) / np.sqrt(np.mean(np.square(e0)))
    print(f"  carry-signaali (M1-M4 % hinnasta) → CL1 seuraavat {h} kk: r={d.y.corr(d.x):+.2f}, OOS RMSE-suhde {ratio:.2f}, suunta {np.mean(hit):.2f} (n_oos={len(em)})")
# simple rule: long when backwardation, flat when contango
sig = (mm.m1m4 > 0).astype(int).shift(1); ret = lp.diff()
strat = (sig * ret).dropna().loc["2012":]
print("  sääntö 'pitkänä vain backwardaatiossa' 2012→: %.1f %%/v vs. aina pitkänä %.1f %%/v; backwardaatiokuukausien keskituotto %.2f %%, contango %.2f %%" % (strat.mean() * 1200, ret.loc["2012":].mean() * 1200, ret[sig == 1].mean() * 100, ret[sig == 0].mean() * 100))
res["term"] = dict(m1m2_last=float(px.m1m2.dropna().iloc[-1]), m1m2_last_date=str(px.m1m2.dropna().index[-1].date()))

print("\n=== 2. EIA-RAPORTTIPÄIVÄN REAKTIO (CL1 päivätuotto raporttipäivänä vs. varastomuutos) ===")
crude = pd.read_csv(f"{RAW}/eia_WCESTUS1w.csv", parse_dates=["date"]).dropna().set_index("date")["value"] / 1000
gaso = pd.read_csv(f"{RAW}/eia_WGTSTUS1w.csv", parse_dates=["date"]).dropna().set_index("date")["value"] / 1000
dist = pd.read_csv(f"{RAW}/eia_WDISTUS1w.csv", parse_dates=["date"]).dropna().set_index("date")["value"] / 1000
hol = set(USFederalHolidayCalendar().holidays("2010-01-01", "2027-01-01"))
def report_date(week_end):  # EIA week ends Friday; report following Wednesday 10:30 ET, Thursday after Monday holidays
    wed = week_end + pd.Timedelta(days=5)
    if (week_end + pd.Timedelta(days=3)) in hol or wed in hol: return wed + pd.Timedelta(days=1)
    return wed
def surprise(s):
    ch = s.diff(); wk = ch.index.isocalendar().week.values
    exp = pd.Series([ch[(ch.index < d) & (ch.index >= d - pd.Timedelta(days=365 * 5 + 7)) & (ch.index.isocalendar().week.values == w)].mean() for d, w in zip(ch.index, wk)], index=ch.index)
    return ch, ch - exp
ch_c, su_c = surprise(crude); ch_g, su_g = surprise(gaso); ch_d, su_d = surprise(dist)
rows = []
for we in crude.index[crude.index >= "2015-01-01"]:
    rdte = report_date(we)
    if rdte not in r1.index or pd.isna(r1.get(rdte)): continue
    rows.append(dict(week=we, report=rdte, r_cl1=r1[rdte], r_rb=np.log(px.rb1).diff().get(rdte), r_ho=np.log(px.ho1).diff().get(rdte), ch_crude=ch_c.get(we), su_crude=su_c.get(we), su_total=su_c.get(we) + su_g.get(we, 0) + su_d.get(we, 0), su_gas=su_g.get(we), su_dist=su_d.get(we)))
ev = pd.DataFrame(rows).dropna(subset=["r_cl1", "su_crude"])
print("n raporttipäiviä =", len(ev))
for col, lab in [("ch_crude", "raakaöljyn muutos (raaka)"), ("su_crude", "raakaöljyn yllätys vs. 5 v kausinormi"), ("su_total", "yllätys raaka+bensa+tisleet"), ("su_gas", "bensiiniyllätys"), ("su_dist", "tisleyllätys")]:
    print(f"  {lab:40} vs CL1 r={ev.r_cl1.corr(ev[col]):+.2f} | RBOB r={ev.r_rb.corr(ev[col]):+.2f} | HO r={ev.r_ho.corr(ev[col]):+.2f}")
mod = sm.OLS(ev.r_cl1 * 100, sm.add_constant(ev[["su_crude", "su_gas", "su_dist"]])).fit()
print("  regressio CL1 %% ~ yllätykset (mb): " + ", ".join(f"{k}={v:+.3f} (p={mod.pvalues[k]:.3f})" for k, v in mod.params.items() if k != "const") + f"  R2={mod.rsquared:.3f}")
q = pd.qcut(ev.su_crude, 5, labels=["suuri purku", "purku", "neutraali", "kertymä", "suuri kertymä"])
print("  kvintiilit (yllätys) → CL1 keskituotto raporttipäivänä %:"); print((ev.groupby(q).r_cl1.mean() * 100).round(2).to_string())
nonrep = r1.loc["2015":].drop(ev.report, errors="ignore")
print("  raporttipäivien |tuotto| keskiarvo %.2f %% vs muut päivät %.2f %%" % (ev.r_cl1.abs().mean() * 100, nonrep.abs().mean() * 100))
ev.to_csv(f"{OUT}/eia_report_day_reactions.csv", index=False)

print("\n=== 3. HORMUZ-TRANSITIT (IMF PortWatch, AIS) vs Brent ===")
if os.path.exists(f"{R3}/portwatch_chokepoints.csv"):
    pw = pd.read_csv(f"{R3}/portwatch_chokepoints.csv", parse_dates=["date"])
    hz = pw[pw.portname == "Strait of Hormuz"].set_index("date").sort_index()
    print("  Hormuz tankkerit/pv: 2019-25 keskiarvo %.1f; 2026 kuukausittain:" % hz.loc["2019":"2025", "n_tanker"].mean())
    print(hz.loc["2026", ["n_tanker", "n_total"]].resample("MS").mean().round(1).T.to_string())
    d = pd.concat([np.log(brent).diff().rename("rb"), hz.n_tanker.rolling(7).mean().diff(7).rename("dtank7")], axis=1).dropna().loc["2026-02-15":]
    print("  2026: 7 pv tankkerimäärän muutos vs Brent 7 pv tuotto (päivätaso) r=%.2f; tankkerit edeltää 3 pv r=%.2f; Brent edeltää 3 pv r=%.2f" % (d.rb.rolling(7).sum().corr(d.dtank7), d.rb.rolling(7).sum().corr(d.dtank7.shift(3)), d.rb.rolling(7).sum().shift(3).corr(d.dtank7)))
    wk = pd.concat([np.log(brent).resample("W-FRI").last().diff().rename("rb"), hz.n_tanker.resample("W-FRI").sum().rename("tank")], axis=1).dropna()
    wk["dtank"] = wk.tank.pct_change()
    for a, b in [("2019", "2025"), ("2026-03", "2026-10")]:
        s = wk.loc[a:b]; print(f"  viikkotaso {a}..{b}: tankkerimäärän %-muutos vs Brent-tuotto sama vko r={s.rb.corr(s.dtank):+.2f}, seuraava vko r={s.rb.shift(-1).corr(s.dtank):+.2f} (n={len(s)})")
    bab = pw[pw.portname == "Bab el-Mandeb Strait"].set_index("date").sort_index(); cape = pw[pw.portname == "Cape of Good Hope"].set_index("date").sort_index()
    print("  Bab el-Mandeb tankkerit/pv: 2023 %.1f → 2024 %.1f → 2026 %.1f; Hyväntoivonniemi %.1f → %.1f → %.1f" % (bab.loc["2023", "n_tanker"].mean(), bab.loc["2024", "n_tanker"].mean(), bab.loc["2026", "n_tanker"].mean(), cape.loc["2023", "n_tanker"].mean(), cape.loc["2024", "n_tanker"].mean(), cape.loc["2026", "n_tanker"].mean()))
    hz[["n_tanker", "n_total", "capacity_tanker"]].to_csv(f"{OUT}/hormuz_daily.csv")

print("\n=== 4. MEKSIKONLAHDEN HURRIKAANIT (HURDAT2) → tuotanto, CL1, RBOB ===")
lines = open(f"{R3}/hurdat2_atl.txt").read().splitlines(); storms = []; cur = None
for l in lines:
    if l.startswith("AL"):
        p = [x.strip() for x in l.split(",")]; cur = dict(id=p[0], name=p[1], pts=[]); storms.append(cur)
    else:
        p = [x.strip() for x in l.split(",")]
        lat = float(p[4][:-1]) * (1 if p[4][-1] == "N" else -1); lon = float(p[5][:-1]) * (-1 if p[5][-1] == "W" else 1)
        cur["pts"].append((pd.Timestamp(p[0] + p[1]), p[3], lat, lon, int(p[6])))
prod = pd.read_csv(f"{RAW}/eia_WCRFPUS2w.csv", parse_dates=["date"]).dropna().set_index("date")["value"] / 1000
evs = []
for s in storms:
    gom = [q for q in s["pts"] if 18 <= q[2] <= 30.5 and -98 <= q[3] <= -82 and q[0].year >= 2015 and q[4] >= 50]
    if not gom: continue
    t0 = min(q[0] for q in gom).normalize(); wmax = max(q[4] for q in gom)
    def ret(s_, a, b):
        ss = s_.loc[a:b].dropna(); return np.log(ss.iloc[-1] / ss.iloc[0]) * 100 if len(ss) > 1 else np.nan
    pre = prod[prod.index < t0].iloc[-1] if (prod.index < t0).any() else np.nan; post = prod.loc[t0:t0 + pd.Timedelta(days=21)].min()
    evs.append(dict(name=s["name"], date=t0.date(), kt=wmax, prod_drop=round(post - pre, 2), cl1_pre5=round(ret(px.cl1, t0 - pd.Timedelta(days=7), t0), 1), cl1_post5=round(ret(px.cl1, t0, t0 + pd.Timedelta(days=7)), 1), rb_post5=round(ret(px.rb1, t0, t0 + pd.Timedelta(days=7)), 1), hocrack_chg=round(px.ho_crack.loc[t0:t0 + pd.Timedelta(days=7)].mean() - px.ho_crack.loc[t0 - pd.Timedelta(days=7):t0].mean(), 1)))
E = pd.DataFrame(evs); print(E.to_string(index=False))
print("  keskiarvo: tuotanto %.2f mb/d, CL1 5 pv ennen %.1f %%, 5 pv jälkeen %.1f %%, RBOB jälkeen %.1f %%; hurrikaanit (≥64 kt): CL1 jälkeen %.1f %%, RBOB %.1f %%" % (E.prod_drop.mean(), E.cl1_pre5.mean(), E.cl1_post5.mean(), E.rb_post5.mean(), E[E.kt >= 64].cl1_post5.mean(), E[E.kt >= 64].rb_post5.mean()))
E.to_csv(f"{OUT}/gom_storm_events.csv", index=False)

print("\n=== 5. CPC 7 PV HDD-ENNUSTEET (NDFD) → kaasu, lämmitysöljy, Texasin tuotanto ===")
files = sorted(glob.glob(f"{R3}/cpc_fc/*.txt")); fc = []
for f in files:
    try:
        txt = open(f).read(); lines_ = [l for l in txt.splitlines() if "|" in l]
        hdr = lines_[0].split("|"); issued = pd.Timestamp(os.path.basename(f)[:10])
        for l in lines_[1:]:
            p = l.split("|")
            if p[0] in ("CONUS", "7", "1", "2"):
                vals = [float(v) for v in p[1:8]]
                if min(vals) < 0 or len(vals) < 7: continue   # -9999 = missing
                fc.append(dict(issued=issued, region=p[0], total7=sum(vals), d1=vals[0], d2=vals[1], d3=vals[2], max7=max(vals), v=vals))
    except Exception: pass
F = pd.DataFrame(fc)
print("  ennustetiedostoja:", len(files), "(%s → %s)" % (F.issued.min().date() if len(F) else None, F.issued.max().date() if len(F) else None))
if len(F) > 300:
    conus = F[F.region == "CONUS"].set_index("issued").sort_index(); tx = F[F.region == "7"].set_index("issued").sort_index(); ne = F[F.region.isin(["1", "2"])].groupby("issued").total7.sum().sort_index()
    # revision: change in the 7-day total vs yesterday's issue (overlapping 6 days approximated by total)
    # revision for the SAME target days: issue t covers t..t+6, issue t-1 covers t-1..t+5 -> overlap t..t+5 = new[0:6] vs old[1:7]
    V = pd.DataFrame(conus.v.tolist(), index=conus.index)
    prev = V.shift(1); prev_ok = (V.index.to_series().diff() == pd.Timedelta(days=1))
    rev = (V.iloc[:, 0:6].values - prev.iloc[:, 1:7].values).sum(axis=1); rev = pd.Series(rev, index=V.index).where(prev_ok)
    rng = np.log(px.ng1).diff(); rho = np.log(px.ho1).diff()
    d = pd.concat([rev.rename("rev"), rng.rename("ng"), rho.rename("ho"), r1.rename("cl")], axis=1).dropna()
    for a, b in [("2015", "2026")]:
        s = d.loc[a:b]; w = s[s.index.month.isin([11, 12, 1, 2, 3])]
        print(f"  CONUS 7 pv HDD-ennusteen päivärevisio vs. sama päivä: NG1 r={s.rev.corr(s.ng):+.2f}, HO1 r={s.rev.corr(s.ho):+.2f}, CL1 r={s.rev.corr(s.cl):+.2f} (n={len(s)}); talvikuukaudet NG1 r={w.rev.corr(w.ng):+.2f}, HO1 r={w.rev.corr(w.ho):+.2f}, CL1 r={w.rev.corr(w.cl):+.2f} (n={len(w)})")
        # 3-day cumulative revision
        s3 = pd.concat([rev.rolling(3).sum().rename("rev3"), rng.rolling(3).sum().rename("ng3"), rho.rolling(3).sum().rename("ho3")], axis=1).dropna(); w3 = s3[s3.index.month.isin([11, 12, 1, 2, 3])]
        print(f"  3 pv kumulatiivinen revisio: NG1 r={w3.rev3.corr(w3.ng3):+.2f}, HO1 r={w3.rev3.corr(w3.ho3):+.2f} (talvi, n={len(w3)})")
        mod = sm.OLS(w.ng * 100, sm.add_constant(w.rev)).fit(); print(f"  talvi: +10 HDD revisio 7 pv summaan → NG1 {mod.params['rev'] * 10:+.2f} % samana päivänä (p={mod.pvalues['rev']:.4f})")
    # Texas forecast max daily HDD → weekly production change (freeze-off risk)
    txw = tx.max7.resample("W-FRI").max(); dp = prod.diff()
    d2 = pd.concat([txw.rename("txmax"), dp.rename("dprod"), dp.shift(-1).rename("dprod_next")], axis=1).dropna().loc["2015":]
    print("  Texas (WSC) ennustettu max päivä-HDD viikolla vs tuotannon muutos: sama vko r=%.2f, seuraava vko r=%.2f; kun max ≥ 35: tuotanto %.2f mb/d (n=%d) vs muut %.2f" % (d2.txmax.corr(d2.dprod), d2.txmax.corr(d2.dprod_next), d2[d2.txmax >= 35].dprod.mean(), (d2.txmax >= 35).sum(), d2[d2.txmax < 35].dprod.mean()))
    F.to_csv(f"{OUT}/cpc_forecasts_daily.csv", index=False)
json.dump(res, open(f"{OUT}/analysis3.json", "w"), default=float)
px.to_csv(f"{OUT}/futures_daily.csv")
print("\nDONE")

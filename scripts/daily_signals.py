#!/usr/bin/env python3
"""Daily / weekly horizon signals for Brent and WTI: transits, front spread, COT, OVX, GPR, momentum, EIA stock change.
Full-sample HAC regressions, walk-forward OOS vs no-change at 1/5/21 trading days, current readings. Writes data/daily_signals.json."""
import json, glob, warnings, numpy as np, pandas as pd, statsmodels.api as sm
warnings.filterwarnings("ignore")
D = "/home/claude/oil/data"; RAW = f"{D}/raw"; R3 = f"{D}/raw3"; R5 = f"{D}/raw5"
def fred(fn):
    d = pd.read_csv(fn); d.columns = ["date", "value"]; d["date"] = pd.to_datetime(d["date"]); return pd.to_numeric(d.set_index("date")["value"], errors="coerce").dropna()
brent = fred(f"{RAW}/fred_Brent_d.csv"); wti = fred(f"{RAW}/fred_WTI_d.csv"); ovx = fred(f"{R3}/fred_OVX.csv")
idx = brent.index[brent.index >= "2018-06-01"]
hz = pd.read_csv(f"{D}/hormuz_daily.csv", parse_dates=["date"]).set_index("date")["n_tanker"].astype(float); tr7 = hz.rolling(7).mean()
gpr = pd.read_excel(f"{R5}/gpr_daily.xls"); gpr["date"] = pd.to_datetime(gpr["date"]); gprd = gpr.set_index("date")["GPRD"].astype(float); gpr7 = gprd.rolling(7).mean()
cot = pd.read_csv(f"{RAW}/cftc_wti_cot.csv", parse_dates=["date"]).set_index("date")["mm_net"].astype(float) / 1000
stocks = pd.read_csv(f"{RAW}/eia_WCESTUS1w.csv", parse_dates=["date"]).set_index("date")["value"].astype(float) / 1000; dstock = stocks.diff()
fd = pd.read_csv(f"{D}/futures_daily.csv", parse_dates=["date"]).set_index("date")
hzj = json.load(open(f"{D}/hazard.json")); hs = pd.DataFrame(hzj["series"]); hs["date"] = pd.to_datetime(hs["date"]); hs = hs.set_index("date")
# front spread: EIA cl1-cl2 to 2024-04, then Yahoo-curve based (hazard.json carries m1m2 only in signals; rebuild from contracts)
MON = {c: i + 1 for i, c in enumerate("FGHJKMNQUVXZ")}
con = {}
for fn in sorted(glob.glob(f"{R3}/yahoo/CL*.NYM.json")):
    code = fn.split("/")[-1].split(".")[0]; j = json.load(open(fn))["chart"]["result"][0]
    s = pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna(); con[code] = (2000 + int(code[-2:]), MON[code[-3]], s[~s.index.duplicated(keep="last")])
m1m2y = {}
for t in pd.date_range("2024-04-01", brent.index.max()):
    c = {}
    for code, (yr, mo, s) in con.items():
        if t in s.index:
            m = (yr - t.year) * 12 + mo - t.month
            if 1 <= m <= 36: c[m] = float(s.loc[t])
    if len(c) >= 2: ms = sorted(c); m1m2y[t] = c[ms[0]] - c[ms[1]]
m1m2 = pd.concat([fd["m1m2"].dropna().loc[:"2024-04-05"], pd.Series(m1m2y).loc["2024-04-08":]]).sort_index(); m1m2 = m1m2[~m1m2.index.duplicated(keep="last")]
X = pd.DataFrame(index=idx)
X["dtr7"] = (tr7 - tr7.shift(7)).shift(2).reindex(idx, method="ffill")           # PortWatch publication lag ~2 days
X["disr"] = (1 - tr7 / 48.0).clip(0, 1).shift(2).reindex(idx, method="ffill")
X["m1m2"] = m1m2.reindex(idx, method="ffill")
cotz = ((cot - cot.rolling(52).mean()) / cot.rolling(52).std()); X["cotz"] = cotz.shift(3, freq="D").reindex(idx, method="ffill")   # Tuesday positions, Friday release
X["dovx5"] = (ovx - ovx.shift(5)).reindex(idx, method="ffill"); X["ovx"] = ovx.reindex(idx, method="ffill")
X["dgpr7"] = (gpr7 - gpr7.shift(7)).reindex(idx, method="ffill"); X["gpr7"] = gpr7.reindex(idx, method="ffill")
X["mom5"] = np.log(brent).diff(5).reindex(idx); X["mom21"] = np.log(brent).diff(21).reindex(idx)
X["dstock"] = dstock.shift(1, freq="D").reindex(idx, method="ffill") / 1.0   # EIA Wednesday release
OUT = {"targets": {}}
FEATS = ["dtr7", "disr", "m1m2", "cotz", "dovx5", "dgpr7", "mom5", "mom21", "dstock"]
for tname, px in [("brent", brent), ("wti", wti)]:
    y = np.log(px).reindex(idx); res = {}
    for h in [1, 5, 21]:
        tgt = (y.shift(-h) - y).rename("y") * 100; df = pd.concat([tgt, X[FEATS]], axis=1).dropna()
        Z = sm.add_constant(df[FEATS]); m = sm.OLS(df.y, Z).fit(cov_type="HAC", cov_kwds={"maxlags": h})
        # walk-forward from 2022-01 (expanding), ridge-lite via OLS (n large) ; crisis sub-sample 2026
        preds = {}; origins = df.index[df.index >= "2022-01-01"]
        step = 5 if h <= 5 else 21
        for i, t in enumerate(origins):
            if i % step == 0:
                tr = df[df.index <= t - pd.Timedelta(days=int(h * 1.5) + 2)]; mm = sm.OLS(tr.y, sm.add_constant(tr[FEATS])).fit()
            preds[t] = float(np.dot(np.r_[1.0, df.loc[t, FEATS].values], mm.params.values))
        pr = pd.Series(preds); act = df.y.reindex(pr.index); e_m = act - 0.5 * pr; e_0 = act   # 50 % shrinkage toward zero
        ratio = float(np.sqrt((e_m**2).mean()) / np.sqrt((e_0**2).mean())); mask26 = pr.index >= "2026-03-01"
        ratio26 = float(np.sqrt((e_m[mask26]**2).mean()) / np.sqrt((e_0[mask26]**2).mean())) if mask26.sum() > 10 else None
        dir_acc = float(np.mean(np.sign(act) == np.sign(pr))); dir26 = float(np.mean(np.sign(act[mask26]) == np.sign(pr[mask26]))) if mask26.sum() > 10 else None
        x_now = X[FEATS].iloc[-1]; p_now = float(np.dot(np.r_[1.0, x_now.values], m.params.values)) if not x_now.isna().any() else None
        res[str(h)] = dict(n=int(m.nobs), r2=round(float(m.rsquared), 4), coef={k: round(float(v), 4) for k, v in m.params.items()}, t={k: round(float(v), 2) for k, v in m.tvalues.items()},
                           oos_rmse_ratio=round(ratio, 3), oos_rmse_ratio_2026=(round(ratio26, 3) if ratio26 else None), dir_acc=round(dir_acc, 3), dir_acc_2026=(round(dir26, 3) if dir26 else None), n_oos=int(len(pr)),
                           pred_now_pct=(round(p_now, 2) if p_now is not None else None), pred_now_shrunk_pct=(round(0.5 * p_now, 2) if p_now is not None else None), rmse_nochange_pct=round(float(np.sqrt((e_0**2).mean())), 2))
        sig = {k: f"{v:+.2f}" for k, v in zip(FEATS, m.tvalues[1:])}
        print(f"{tname} h={h:>2} pv: n={m.nobs:.0f} R²={m.rsquared:.3f} OOS RMSE-suhde {ratio:.3f} (2026: {ratio26 if ratio26 is None else round(ratio26,3)}) suunta {dir_acc:.2f} | t-arvot {sig} | ennuste nyt {p_now if p_now is None else round(p_now,2)} %")
    OUT["targets"][tname] = res
xl = X.iloc[-1]; z = {}
for k in FEATS:
    s = X[k].dropna(); z[k] = dict(value=round(float(xl[k]), 3) if not np.isnan(xl[k]) else None, z=round(float((xl[k] - s.mean()) / s.std()), 2) if not np.isnan(xl[k]) else None, pct=round(float((s < xl[k]).mean() * 100), 0) if not np.isnan(xl[k]) else None)
OUT["now"] = dict(date=str(idx[-1].date()), signals=z, labels={"dtr7": "Hormuz-transitit, 7 pv ka:n muutos (alusta/pv)", "disr": "Hormuz-häiriöaste (1 − transitit/48)", "m1m2": "Etukuukausien ero M1−M2 ($)", "cotz": "Rahastojen nettopositio, z (52 vk)", "dovx5": "OVX 5 pv muutos", "dgpr7": "GPR 7 pv ka:n muutos", "mom5": "Momentum 5 pv (log)", "mom21": "Momentum 21 pv (log)", "dstock": "EIA raakaöljyvarastojen viikkomuutos (mb)"})
json.dump(OUT, open(f"{D}/daily_signals.json", "w"), default=float); print("saved; now:", OUT["now"]["date"], {k: v["value"] for k, v in z.items()})

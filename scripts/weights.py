#!/usr/bin/env python3
"""Rolling estimation of forecast-stack weights (dossier item 3). Members with real-time history at month-end origins:
no-change, futures curve, fair-value gap reversion (walk-forward), VAR(6). NNLS sum-to-one weights on expanding windows,
OOS evaluation 2023->, current weights applied to the live members from models8.json. Writes data/weights.json."""
import json, glob, warnings, numpy as np, pandas as pd, statsmodels.api as sm
from scipy.optimize import nnls, minimize
warnings.filterwarnings("ignore")
D = "/home/claude/oil/data"; RAW = f"{D}/raw"; R3 = f"{D}/raw3"
M = pd.read_csv(f"{D}/panel_monthly.csv", index_col=0, parse_dates=True); pg = json.load(open(f"{D}/page_data.json")); m8 = json.load(open(f"{D}/models8.json"))
H = [1, 3, 6, 12]; MEMBERS = ["nochange", "futures", "physical", "var"]
MON = {c: i + 1 for i, c in enumerate("FGHJKMNQUVXZ")}
def fredd(n):
    d = pd.read_csv(f"{RAW}/fred_{n}.csv"); d.columns = ["date", "value"]; d["date"] = pd.to_datetime(d["date"]); return pd.to_numeric(d.set_index("date")["value"], errors="coerce").dropna()
daily = {"wti": fredd("WTI_d"), "brent": fredd("Brent_d")}
# ---- futures at month end: Yahoo contracts (2021-10->) + EIA cl1-4 (->2024-04) for WTI ----
def contracts(root):
    out = {}
    for fn in sorted(glob.glob(f"{R3}/yahoo/{root}*.NYM.json")):
        code = fn.split("/")[-1].split(".")[0]; j = json.load(open(fn))["chart"]["result"][0]
        s = pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna(); out[(2000 + int(code[-2:]), MON[code[-3]])] = s[~s.index.duplicated(keep="last")]
    return out
CON = {"wti": contracts("CL"), "brent": contracts("BZ")}
fd = pd.read_csv(f"{D}/futures_daily.csv", parse_dates=["date"]).set_index("date")
def fut_at(t, tgt, h):
    """Price at month-end t of the contract that is front during target month t+h (delivery t+h+1)."""
    dm = t + pd.DateOffset(months=h + 1); key = (dm.year, dm.month); s = CON[tgt].get(key)
    if s is not None:
        w = s[(s.index <= t + pd.Timedelta(days=0)) & (s.index > t - pd.Timedelta(days=6))]
        if len(w): return float(w.iloc[-1])
    if tgt == "wti" and h <= 4:
        w = fd[f"cl{h}"].dropna(); w = w[(w.index <= t) & (w.index > t - pd.Timedelta(days=6))]
        if len(w): return float(w.iloc[-1])
    return np.nan
# ---- gap model (as in model.py / models8.py), walk-forward member forecasts ----
S = {s["key"]: s for s in pg["series"]}; dates_pg = pd.to_datetime(pg["dates"]); hz = pd.Series(S["hormuz_tankers"]["values"], index=dates_pg, dtype=float).fillna(50.0)
dev = lambda s: (s - s.rolling(36, min_periods=24).mean()) / 100
BASE = {"oecd_dev": dev(M.oecd_stocks), "opec": np.log(M.opec_prod), "hormuz": np.clip(1 - hz / 50.0, 0, 1), "usd": np.log(M.usd_broad), "cot": M.mm_net_wti / 100, "usstocks": dev(M.us_total_stocks), "sp": np.log(M.sp500)}
WTI_EXTRA = {"cushing_dev": dev(M.cushing * 10) / 10, "uscrude_dev": dev(M.us_crude_stocks), "usprod": np.log(M.us_prod), "spr_dev": dev(M.us_spr)}
def fit(df, alpha=0.0015):
    Xs = df.drop(columns="y"); mu = Xs.mean(); sd = Xs.std().replace(0, 1); Z = (Xs - mu) / sd
    m = sm.OLS(df.y, sm.add_constant(Z, has_constant="add")).fit_regularized(alpha=alpha, L1_wt=0.0)
    def pred(Xn): return float(np.dot(np.r_[1.0, ((Xn - mu) / sd).values.ravel()], m.params))
    return m, pred, pd.Series([pred(Xs.loc[[t]]) for t in Xs.index], index=Xs.index)
# ---- VAR(6) member ----
from statsmodels.tsa.api import VAR
bdi = pd.read_csv(f"{RAW}/bdi_daily.csv", parse_dates=["date"]).set_index("date")["value"].resample("MS").mean()
cpi = pd.read_csv(f"{RAW}/fred_CPI_US.csv", parse_dates=["date"]).set_index("date")["value"]; cpi.index = cpi.index.to_period("M").to_timestamp()
wp = pd.read_csv(f"{D}/panel_long_2006_2026.csv", index_col=0, parse_dates=True)
V = pd.DataFrame({"supply": np.log(wp.opec_prod).diff(), "activity": np.log(bdi).diff(), "rprice": np.log(wp.brent / cpi.reindex(wp.index) * 100), "dstock": wp.oecd_stocks.diff() / 100}).dropna()
V = V.loc["2006-06":]; V = V.reindex(pd.date_range(V.index.min(), V.index.max(), freq="MS")).interpolate(limit=2).dropna()
def var_fc(t, h):
    tr = V.loc[:t]
    if len(tr) < 60: return np.nan
    try: r = VAR(tr).fit(6); fc = r.forecast(tr.values[-6:], h)[:, 2]; return float(fc[h - 1] - tr.rprice.iloc[-1]) + 0.0025 * h
    except Exception: return np.nan
OUT = {}
for tgt, feats in [("wti", {**BASE, **WTI_EXTRA}), ("brent", BASE)]:
    y = np.log(M[tgt]); X = pd.DataFrame(feats); d = pd.concat([y.rename("y"), X], axis=1).dropna()
    dd = daily[tgt]; yo = np.log(dd.resample("MS").last()).reindex(d.index).fillna(d.y); last_day = dd.resample("MS").apply(lambda s: s.index[-1] if len(s) else pd.NaT)
    rows = []
    for t in d.index[d.index >= "2019-01-01"]:
        trl = d.loc[:t]; ml, prl, fl = fit(trl); gaps = yo.loc[trl.index] - fl; te = last_day.get(t, t + pd.offsets.MonthEnd(0))
        for h in H:
            tt = t + pd.DateOffset(months=h); a = float(d.y.loc[tt] - yo.loc[t]) if tt in d.index else np.nan
            g2 = pd.concat([(trl.y.shift(-h) - yo.loc[trl.index]).rename("dy"), gaps.rename("g")], axis=1).dropna()
            p = np.nan
            if len(g2) > 24:
                mg = sm.OLS(g2.dy, sm.add_constant(g2[["g"]], has_constant="add")).fit(); p = 0.5 * float(mg.params["g"] * gaps.iloc[-1])
            F = fut_at(te, tgt, h); ff = float(np.log(F) - yo.loc[t]) if not np.isnan(F) else np.nan
            if np.isnan(ff) and tgt == "brent":   # proxy: WTI curve slope
                Fw = fut_at(te, "wti", h); yw = np.log(daily["wti"].resample("MS").last()).get(t, np.nan); ff = float(np.log(Fw) - yw) if not (np.isnan(Fw) or np.isnan(yw)) else np.nan
            rows.append(dict(t=t, h=h, actual=a, nochange=0.0, futures=ff, physical=p, var=var_fc(t, h)))
    R = pd.DataFrame(rows); res = {}
    for h in H:
        Rh = R[(R.h == h)].set_index("t"); cnt = Rh[MEMBERS].notna().sum()
        mem = [k for k in MEMBERS if cnt[k] >= 36]   # members with enough real-time history (futures curve beyond 4 months exists only from 2026)
        Rh = Rh.dropna(subset=mem); ev = Rh[Rh.actual.notna()]
        def est(sub):
            A = sub[mem].values; b = sub.actual.values
            f = lambda w: float(((A @ w - b) ** 2).sum()); cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)   # sum-to-one, non-negative
            r = minimize(f, np.ones(len(mem)) / len(mem), bounds=[(0, 1)] * len(mem), constraints=cons, method="SLSQP"); return r.x
        WD = {"nochange": 0.20, "futures": 0.15, "physical": 0.20, "var": 0.15}
        preds = {"est": {}, "equal": {}, "dossier": {}, "shrunk": {}}; wd = np.array([WD[k] for k in mem]); wd = wd / wd.sum(); weights_hist = {}
        for s in ev.index[ev.index >= "2023-01-01"]:
            train = ev[ev.index <= s - pd.DateOffset(months=h)]
            if len(train) < 18: continue
            w = est(train); weights_hist[str(s.date())[:7]] = [round(float(x), 3) for x in w]; x = ev.loc[s, mem].values
            preds["est"][s] = float(x @ w); preds["equal"][s] = float(x.mean()); preds["dossier"][s] = float(x @ wd); preds["shrunk"][s] = float(x @ (0.5 * w + 0.5 * wd))
        out = {}
        if preds["est"]:
            idx = list(preds["est"].keys()); act = ev.actual.loc[idx]
            rm = lambda p: float(np.sqrt(np.mean((act.values - np.array([p[i] for i in idx])) ** 2)))
            r0 = float(np.sqrt(np.mean(act.values ** 2)))
            out = dict(n_oos=len(idx), rmse_ratio_est=round(rm(preds["est"]) / r0, 3), rmse_ratio_equal=round(rm(preds["equal"]) / r0, 3), rmse_ratio_dossier=round(rm(preds["dossier"]) / r0, 3), rmse_ratio_shrunk=round(rm(preds["shrunk"]) / r0, 3),
                       rmse_ratio_members={k: round(float(np.sqrt(np.mean((act.values - ev.loc[idx, k].values) ** 2))) / r0, 3) for k in mem})
        wfull = est(ev); out["members"] = mem; out["weights_now"] = {k: round(float(v), 3) for k, v in zip(mem, wfull)}; out["n_train"] = int(len(ev)); out["sample"] = [str(ev.index[0].date())[:7], str(ev.index[-1].date())[:7]]; out["weights_hist"] = weights_hist
        hs = m8["stack"][tgt]["horizons"].get(str(h))   # live members; members without history keep the dossier weight (renormalised)
        if hs:
            lm = hs["members"]; missing = [k for k in MEMBERS if k not in mem]; w_missing = sum(WD[k] for k in missing)
            live_est = sum(lm[k] * wfull[i] for i, k in enumerate(mem)); live = (1 - w_missing) * live_est + sum(lm[k] * WD[k] for k in missing)
            wsh = 0.5 * wfull + 0.5 * wd; live_sh = (1 - w_missing) * sum(lm[k] * wsh[i] for i, k in enumerate(mem)) + sum(lm[k] * WD[k] for k in missing)
            out["stack_est_now"] = round(float(live), 1); out["stack_shrunk_now"] = round(float(live_sh), 1); out["weights_shrunk"] = {k: round(float(v), 3) for k, v in zip(mem, wsh)}; out["stack_dossier_now"] = hs["stack"]; out["missing_members"] = missing
        res[str(h)] = out
        print(f"{tgt} h={h}: otos {out['sample']} n={out['n_train']} | painot nyt " + " ".join(f"{k} {v:.2f}" for k, v in out["weights_now"].items()) + (f" | OOS 2023→ (n={out['n_oos']}) RMSE-suhde est {out['rmse_ratio_est']} kutistettu {out['rmse_ratio_shrunk']} tasa {out['rmse_ratio_equal']} dossieri {out['rmse_ratio_dossier']} jäsenet {out['rmse_ratio_members']}" if "n_oos" in out else "") + (f" | pino nyt est {out.get('stack_est_now')} vs dossieri {out.get('stack_dossier_now')}" if hs else ""))
    OUT[tgt] = res
json.dump(OUT, open(f"{D}/weights.json", "w"), default=float); print("saved")

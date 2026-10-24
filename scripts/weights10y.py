#!/usr/bin/env python3
"""Ten-year retrospective weight analysis of the forecast components (no-change, funda, futuuri, STEO) at month-end origins.
All members are real-time: funda = walk-forward fair-value gap reversion (fit only on data up to the origin), futuuri = contract that is
front during the target month (EIA CL1-4 to 4/2024, Yahoo contracts from 10/2021), STEO = the vintage published in the origin month
(data/steo_vintages.csv). Forecasts and actuals are log deviations from the end-of-month price, so RMSE ratios to no-change are scale-free.
Outputs data/weights10y.json: per target and horizon the member RMSE ratios (10 y and sub-periods), the in-sample optimum and grid landscape,
and the walk-forward out-of-sample test of estimated vs equal vs current-recipe weights."""
import os, json, glob, warnings, numpy as np, pandas as pd, statsmodels.api as sm
from scipy.optimize import minimize
warnings.filterwarnings("ignore")
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); D = f"{ROOT}/data"; RAW = f"{D}/raw"; R3 = f"{D}/raw3"
M = pd.read_csv(f"{D}/panel_monthly.csv", index_col=0, parse_dates=True); pg = json.load(open(f"{D}/page_data.json"))
H = [1, 3, 6, 12]; MEMBERS = ["nochange", "funda", "futuuri", "steo"]; WINDOW = "2016-10-01"; MIN_TRAIN = 36
PERIODS = [("2016-10", "2019-12"), ("2020-01", "2022-12"), ("2023-01", "2026-12")]
MON = {c: i + 1 for i, c in enumerate("FGHJKMNQUVXZ")}
def fredd(n):
    d = pd.read_csv(f"{RAW}/fred_{n}.csv"); d.columns = ["date", "value"]; d["date"] = pd.to_datetime(d["date"]); return pd.to_numeric(d.set_index("date")["value"], errors="coerce").dropna()
daily = {"wti": fredd("WTI_d"), "brent": fredd("Brent_d")}
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
    dm = t + pd.DateOffset(months=h + 1); s = CON[tgt].get((dm.year, dm.month))
    if s is not None:
        w = s[(s.index <= t) & (s.index > t - pd.Timedelta(days=6))]
        if len(w): return float(w.iloc[-1])
    if tgt == "wti" and h <= 4:
        w = fd[f"cl{h}"].dropna(); w = w[(w.index <= t) & (w.index > t - pd.Timedelta(days=6))]
        if len(w): return float(w.iloc[-1])
    return np.nan
# STEO vintages: vintage of the origin month, value at the target month
SV = {}
try:
    sv = pd.read_csv(f"{D}/steo_vintages.csv"); sv["month"] = pd.to_datetime(sv["month"])
    for v, g in sv.groupby("vintage"): SV[v] = g.set_index("month")[["wti", "brent"]]
except Exception as e: print("no steo vintages", e)
def steo_at(t, tgt, h):
    g = SV.get(str(t.date())[:7])
    if g is None: return np.nan
    tt = t + pd.DateOffset(months=h); return float(g[tgt].get(tt, np.nan)) if tt in g.index else np.nan
# fair-value model (as in model.py), walk-forward
S = {s["key"]: s for s in pg["series"]}; dates_pg = pd.to_datetime(pg["dates"]); hz = pd.Series(S["hormuz_tankers"]["values"], index=dates_pg, dtype=float).fillna(50.0)
dev = lambda s: (s - s.rolling(36, min_periods=24).mean()) / 100
BASE = {"oecd_dev": dev(M.oecd_stocks), "opec": np.log(M.opec_prod), "hormuz": np.clip(1 - hz / 50.0, 0, 1), "usd": np.log(M.usd_broad), "cot": M.mm_net_wti / 100, "usstocks": dev(M.us_total_stocks), "sp": np.log(M.sp500)}
WTI_EXTRA = {"cushing_dev": dev(M.cushing * 10) / 10, "uscrude_dev": dev(M.us_crude_stocks), "usprod": np.log(M.us_prod), "spr_dev": dev(M.us_spr)}
def fit(df, alpha=0.0015):
    Xs = df.drop(columns="y"); mu = Xs.mean(); sd = Xs.std().replace(0, 1); Z = (Xs - mu) / sd
    m = sm.OLS(df.y, sm.add_constant(Z, has_constant="add")).fit_regularized(alpha=alpha, L1_wt=0.0)
    def pred(Xn): return float(np.dot(np.r_[1.0, ((Xn - mu) / sd).values.ravel()], m.params))
    return m, pred, pd.Series([pred(Xs.loc[[t]]) for t in Xs.index], index=Xs.index)
def est(A, b):
    f = lambda w: float(((A @ w - b) ** 2).sum()); cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)
    return minimize(f, np.ones(A.shape[1]) / A.shape[1], bounds=[(0, 1)] * A.shape[1], constraints=cons, method="SLSQP").x
def grid(k, step=0.05):
    pts = []
    def rec(prefix, left):
        if len(prefix) == k - 1: pts.append(prefix + [round(left, 2)]); return
        v = 0.0
        while v <= left + 1e-9: rec(prefix + [round(v, 2)], round(left - v, 2)); v += step
    rec([], 1.0); return np.array(pts)
try: vj = json.load(open(f"{D}/views.json")); WS0 = float(vj.get("steo_weight", 0))
except Exception: WS0 = 0.05
OUT = {"window": WINDOW[:7], "periods": PERIODS, "members": MEMBERS, "note": "RMSE suhteessa ei-muutokseen (log-virhe); kaikki jäsenet reaaliaikaisia kuukauden lopun lähtöpisteestä", "targets": {}}
for tgt, feats in [("wti", {**BASE, **WTI_EXTRA}), ("brent", BASE)]:
    y = np.log(M[tgt]); X = pd.DataFrame(feats); d = pd.concat([y.rename("y"), X], axis=1).dropna()
    dd = daily[tgt]; yo = np.log(dd.resample("MS").last()).reindex(d.index).fillna(d.y); last_day = dd.resample("MS").apply(lambda s: s.index[-1] if len(s) else pd.NaT)
    rows = []
    for t in d.index[d.index >= "2012-01-01"]:
        trl = d.loc[:t]
        if len(trl) < MIN_TRAIN: continue
        ml, prl, fl = fit(trl); gaps = yo.loc[trl.index] - fl; te = last_day.get(t, t + pd.offsets.MonthEnd(0))
        for h in H:
            tt = t + pd.DateOffset(months=h); a = float(d.y.loc[tt] - yo.loc[t]) if tt in d.index else np.nan
            g2 = pd.concat([(trl.y.shift(-h) - yo.loc[trl.index]).rename("dy"), gaps.rename("g")], axis=1).dropna(); p = np.nan
            if len(g2) > 24: mg = sm.OLS(g2.dy, sm.add_constant(g2[["g"]], has_constant="add")).fit(); p = 0.5 * float(mg.params["g"] * gaps.iloc[-1])
            F = fut_at(te, tgt, h); ff = float(np.log(F) - yo.loc[t]) if not np.isnan(F) else np.nan
            if np.isnan(ff) and tgt == "brent":   # proxy: WTI curve slope
                Fw = fut_at(te, "wti", h); yw = np.log(daily["wti"].resample("MS").last()).get(t, np.nan); ff = float(np.log(Fw) - yw) if not (np.isnan(Fw) or np.isnan(yw)) else np.nan
            Sx = steo_at(t, tgt, h); sf = float(np.log(Sx) - yo.loc[t]) if not np.isnan(Sx) else np.nan
            rows.append(dict(t=t, h=h, actual=a, nochange=0.0, funda=p, futuuri=ff, steo=sf))
    R = pd.DataFrame(rows); res = {}
    for h in H:
        Rh = R[R.h == h].set_index("t"); ev = Rh[Rh.actual.notna()]; win = ev[ev.index >= WINDOW]
        cnt = win[MEMBERS].notna().sum(); mem = [k for k in MEMBERS if cnt[k] >= MIN_TRAIN]
        win = win.dropna(subset=mem); r0 = lambda sub: float(np.sqrt(np.mean(sub.actual.values ** 2)))
        rm = lambda sub, pred: float(np.sqrt(np.mean((sub.actual.values - pred) ** 2)))
        out = dict(n=int(len(win)), members=mem, sample=[str(win.index[0].date())[:7], str(win.index[-1].date())[:7]] if len(win) else None)
        if not len(win): res[str(h)] = out; continue
        out["ratio_members"] = {k: round(rm(win, win[k].values) / r0(win), 3) for k in mem}
        out["ratio_periods"] = {}
        for a, b in PERIODS:
            sub = win[(win.index >= a) & (win.index <= b + "-01")]
            if len(sub) >= 12: out["ratio_periods"][f"{a}–{b[:4]}"] = dict(n=int(len(sub)), **{k: round(rm(sub, sub[k].values) / r0(sub), 3) for k in mem})
        # in-sample optimum and grid landscape over the window
        A = win[mem].values; b = win.actual.values; w_in = est(A, b); out["optimum_insample"] = dict(w={k: round(float(v), 3) for k, v in zip(mem, w_in)}, ratio=round(rm(win, A @ w_in) / r0(win), 3))
        G = grid(len(mem)); gr = np.array([rm(win, A @ g) for g in G]) / r0(win); order = np.argsort(gr)
        out["grid"] = dict(n=int(len(G)), best=[dict(w={k: float(v) for k, v in zip(mem, G[i])}, ratio=round(float(gr[i]), 3)) for i in order[:5]], median=round(float(np.median(gr)), 3), worst=round(float(gr.max()), 3))
        # recipes: equal over members; current = funda/futuuri split with STEO weight WS0 (no-change 0)
        def recipe(w):
            v = np.array([w.get(k, 0.0) for k in mem]); return v / v.sum() if v.sum() > 0 else np.ones(len(mem)) / len(mem)
        w_eq = np.ones(len(mem)) / len(mem); w_cur = recipe({"funda": (1 - WS0) / 2, "futuuri": (1 - WS0) / 2, "steo": WS0})
        out["ratio_equal"] = round(rm(win, A @ w_eq) / r0(win), 3); out["ratio_current"] = round(rm(win, A @ w_cur) / r0(win), 3); out["w_current"] = {k: round(float(v), 3) for k, v in zip(mem, w_cur)}
        # walk-forward OOS over the window: weights estimated from origins whose targets were known at the time
        evm = ev.dropna(subset=mem); preds = {"est": {}, "equal": {}, "current": {}, "shrunk": {}}; hist = {}
        for s in win.index:
            train = evm[evm.index <= s - pd.DateOffset(months=h)]
            if len(train) < MIN_TRAIN: continue
            w = est(train[mem].values, train.actual.values); x = win.loc[s, mem].values; hist[str(s.date())[:7]] = [round(float(v), 2) for v in w]
            preds["est"][s] = float(x @ w); preds["equal"][s] = float(x @ w_eq); preds["current"][s] = float(x @ w_cur); preds["shrunk"][s] = float(x @ (0.5 * w + 0.5 * w_eq))
        if preds["est"]:
            idx = list(preds["est"].keys()); sub = win.loc[idx]
            out["oos"] = dict(n=len(idx), sample=[str(idx[0].date())[:7], str(idx[-1].date())[:7]], **{k: round(rm(sub, np.array([preds[k][i] for i in idx])) / r0(sub), 3) for k in preds})
            out["oos"]["members"] = {k: round(rm(sub, sub[k].values) / r0(sub), 3) for k in mem}
            out["weights_hist"] = {k: hist[k] for k in list(hist)[::12]}; out["weights_latest"] = {k: round(float(v), 3) for k, v in zip(mem, est(evm[mem].values, evm.actual.values))}
        res[str(h)] = out
    OUT["targets"][tgt] = res
json.dump(OUT, open(f"{D}/weights10y.json", "w"), indent=1, default=float)
for tgt in ["wti", "brent"]:
    print(tgt)
    for h, o in OUT["targets"][tgt].items():
        if "ratio_members" not in o: print(f"  h={h}: n={o['n']} (ei tarpeeksi dataa)"); continue
        oo = o.get("oos", {}); print(f"  h={h:>2} n={o['n']:3d} {o['sample']} members {o['ratio_members']} | in-sample opt {o['optimum_insample']} | equal {o['ratio_equal']} current {o['ratio_current']} | OOS est {oo.get('est')} equal {oo.get('equal')} current {oo.get('current')} shrunk {oo.get('shrunk')} (n={oo.get('n')})")
        for k, v in o.get("ratio_periods", {}).items(): print(f"       {k}: {v}")

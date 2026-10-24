#!/usr/bin/env python3
"""Edge search for the 3-month horizon. Month-end origins, target y = log(monthly average price of month t+3) - log(last daily price of t).
All signals are known at the origin. Protocol (fixed before looking at results): K candidate signals, walk-forward expanding window (only
targets already realised at the origin), OOS 2014-01 -> latest; metrics vs no-change (RMSE ratio, Clark-West with Newey-West), vs the futures curve
(does the signal predict the futuuri error?), by sub-period (2014-19, 2020-22, 2023-26). Multiple-testing: K is reported, a signal counts only with
CW p < 0.05/K or consistent gains in all three sub-periods. Writes data/edge3m.json."""
import os, json, glob, warnings, numpy as np, pandas as pd, statsmodels.api as sm
from scipy import stats
warnings.filterwarnings("ignore")
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); D = f"{ROOT}/data"; RAW = f"{D}/raw"; R3 = f"{D}/raw3"
H = 3; OOS0 = pd.Timestamp("2014-01-01"); PER = [("2014-01", "2019-12"), ("2020-01", "2022-12"), ("2023-01", "2026-12")]
MON = {c: i + 1 for i, c in enumerate("FGHJKMNQUVXZ")}
def fredd(n, base=RAW):
    d = pd.read_csv(f"{base}/fred_{n}.csv"); d.columns = ["date", "value"]; d["date"] = pd.to_datetime(d["date"]); return pd.to_numeric(d.set_index("date")["value"], errors="coerce").dropna()
dd = {"wti": fredd("WTI_d"), "brent": fredd("Brent_d")}
usd = fredd("DollarBroad_d"); spx = fredd("SP500_d"); ovx = fredd("OVX", R3)
L = pd.read_csv(f"{D}/panel_long_2006_2026.csv", index_col=0, parse_dates=True)
fd = pd.read_csv(f"{D}/futures_daily.csv", parse_dates=["date"]).set_index("date")
def contracts(root):
    out = {}
    for fn in sorted(glob.glob(f"{R3}/yahoo/{root}*.NYM.json")):
        code = fn.split("/")[-1].split(".")[0]; j = json.load(open(fn))["chart"]["result"][0]
        s = pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna(); out[(2000 + int(code[-2:]), MON[code[-3]])] = s[~s.index.duplicated(keep="last")]
    return out
CON = contracts("CL")
def fut_wti(t_last, h):   # price at the origin of the contract that is front during target month t+h
    dm = (t_last.replace(day=1) + pd.DateOffset(months=h + 1)); s = CON.get((dm.year, dm.month))
    if s is not None:
        w = s[(s.index <= t_last) & (s.index > t_last - pd.Timedelta(days=6))]
        if len(w): return float(w.iloc[-1])
    if h <= 4:
        w = fd[f"cl{h}"].dropna(); w = w[(w.index <= t_last) & (w.index > t_last - pd.Timedelta(days=6))]
        if len(w): return float(w.iloc[-1])
    return np.nan
def build(tgt):
    s = dd[tgt]; ls = np.log(s); me = s.resample("MS").last(); avg = s.resample("MS").mean(); lastday = s.resample("MS").apply(lambda x: x.index[-1] if len(x) else pd.NaT)
    idx = me.index; X = pd.DataFrame(index=idx); lme = np.log(me)
    X["y"] = np.log(avg).shift(-H) - lme
    for k in [1, 3, 6, 12]: X[f"r{k}"] = lme - lme.shift(k)
    X["r12_1"] = lme.shift(1) - lme.shift(12)   # classic 12-1 momentum
    ret = ls.diff(); X["rv3"] = ret.rolling(63).std().resample("MS").last() * np.sqrt(252)
    X["rv3_chg"] = np.log(X["rv3"] / X["rv3"].shift(6))
    X["hi12"] = (ls - ls.rolling(252).max()).resample("MS").last(); X["lo12"] = (ls - ls.rolling(252).min()).resample("MS").last()
    X["ma12"] = lme - np.log(me).rolling(12).mean(); X["ma36"] = lme - np.log(me).rolling(36).mean()
    X["acc"] = (lme - lme.shift(3)) - (lme.shift(3) - lme.shift(6))   # momentum acceleration
    # curve (WTI contracts; Brent target uses the WTI slope as a proxy)
    b3 = []; b1 = []
    for t, ld in lastday.items():
        if pd.isna(ld): b3.append(np.nan); b1.append(np.nan); continue
        pw = float(dd["wti"].get(ld, np.nan)) if ld in dd["wti"].index else np.nan
        f3 = fut_wti(ld, 3); f1 = fut_wti(ld, 1)
        b3.append(np.log(f3 / pw) if (f3 == f3 and pw == pw) else np.nan); b1.append(np.log(f1 / pw) if (f1 == f1 and pw == pw) else np.nan)
    X["basis3"] = b3; X["basis1"] = b1
    X["m1m4"] = (fd["m1m4_pct"].resample("MS").last() / 100).reindex(idx) if "m1m4_pct" in fd else np.nan
    # positioning, stocks, macro (lag 1-2 months for publication delay)
    nc = L["noncomm_net"].reindex(idx); X["cot_lvl"] = (nc.shift(1) - nc.shift(1).rolling(36, min_periods=24).mean()) / nc.shift(1).rolling(36, min_periods=24).std(); X["cot_chg3"] = (nc.shift(1) - nc.shift(4)) / nc.shift(1).rolling(36, min_periods=24).std()
    oe = L["oecd_stocks"].reindex(idx); X["oecd_dev"] = (oe.shift(2) - oe.shift(2).rolling(36, min_periods=24).mean()) / oe.shift(2).rolling(36, min_periods=24).std()
    us = L["us_total_stocks"].reindex(idx); X["us_stk_dev"] = (us.shift(1) - us.shift(1).rolling(36, min_periods=24).mean()) / us.shift(1).rolling(36, min_periods=24).std()
    u = np.log(usd).resample("MS").last().reindex(idx); X["usd3"] = u - u.shift(3)
    sp = np.log(spx).resample("MS").last().reindex(idx); X["sp3"] = sp - sp.shift(3)
    ov = ovx.resample("MS").last().reindex(idx); X["ovx"] = np.log(ov); X["ovx_rel"] = np.log(ov / ov.rolling(12, min_periods=8).mean())
    sw = np.log(dd["brent"]).resample("MS").last().reindex(idx) - np.log(dd["wti"]).resample("MS").last().reindex(idx); X["bw"] = sw; X["bw_chg"] = sw - sw.shift(3)
    # futuuri forecast of y (log F(t,3) - log P_t), WTI contracts for both targets (Brent: slope proxy)
    X["fut"] = X["basis3"]
    return X, me
def nw_t(e, lags=3):
    e = np.asarray(e, float); e = e[~np.isnan(e)]; n = len(e)
    if n < 12: return np.nan, np.nan
    m = e.mean(); u = e - m; v = (u @ u) / n
    for l in range(1, lags + 1): v += 2 * (1 - l / (lags + 1)) * (u[l:] @ u[:-l]) / n
    t = m / np.sqrt(v / n); return float(t), float(2 * (1 - stats.norm.cdf(abs(t))))
def walk(X, cols, intercept=False, ridge=0.0, start=OOS0):
    """Expanding window; training rows = origins s with s + H months <= t (target realised)."""
    pred = pd.Series(np.nan, index=X.index)
    for t in X.index[X.index >= start]:
        tr = X[X.index <= t - pd.DateOffset(months=H)].dropna(subset=cols + ["y"])
        if len(tr) < 48 or X.loc[t, cols].isna().any(): continue
        A = tr[cols].values; mu = A.mean(0) if ridge else 0; sd = A.std(0) if ridge else 1; Z = (A - mu) / sd; b = tr.y.values
        if intercept: Z = np.c_[np.ones(len(Z)), Z]
        k = Z.shape[1]; R = ridge * np.eye(k) * len(Z);
        if intercept: R[0, 0] = 0
        beta = np.linalg.solve(Z.T @ Z + R, Z.T @ b); z = (X.loc[t, cols].values.astype(float) - mu) / sd
        pred[t] = float((np.r_[1.0, z] if intercept else z) @ beta)
    return pred
def evaluate(X, pred, label, K=1):
    d = pd.concat([X.y.rename("y"), pred.rename("p"), X.fut.rename("f")], axis=1).dropna(subset=["y", "p"]); d = d[d.index >= OOS0]
    if len(d) < 24: return None
    e0 = d.y.values; e1 = d.y.values - d.p.values; rm0 = np.sqrt((e0 ** 2).mean()); rm1 = np.sqrt((e1 ** 2).mean())
    cw = e0 ** 2 - (e1 ** 2 - d.p.values ** 2); t, p = nw_t(cw)   # Clark-West adjusted loss differential vs no-change (one-sided p = p/2 when t>0)
    out = dict(label=label, n=int(len(d)), ratio=round(float(rm1 / rm0), 3), cw_t=round(t, 2), cw_p1=round(p / 2 if t > 0 else 1 - p / 2, 4), sign_hit=round(float((np.sign(d.p) == np.sign(d.y)).mean()), 3),
               corr=round(float(np.corrcoef(d.p, d.y)[0, 1]), 3), periods={})
    for a, b in PER:
        s = d[(d.index >= a) & (d.index <= b + "-28")]
        if len(s) >= 12: out["periods"][f"{a[:4]}-{b[:4]}"] = round(float(np.sqrt(((s.y - s.p) ** 2).mean()) / np.sqrt((s.y ** 2).mean())), 3)
    g = d.dropna(subset=["f"])   # versus the futuuri: does the signal add to the curve forecast?
    if len(g) >= 24:
        ef = g.y - g.f; comb = g.y - (g.f + g.p); out["vs_fut"] = dict(n=int(len(g)), rmse_fut=round(float(np.sqrt((ef ** 2).mean())), 4), rmse_fut_plus=round(float(np.sqrt((comb ** 2).mean())), 4), ratio_to_fut=round(float(np.sqrt((comb ** 2).mean()) / np.sqrt((ef ** 2).mean())), 3), cw_t=round(nw_t(ef ** 2 - (comb ** 2 - g.p ** 2))[0], 2))
    return out
SIGNALS = ["r1", "r3", "r6", "r12", "r12_1", "rv3", "rv3_chg", "hi12", "lo12", "ma12", "ma36", "acc", "basis3", "basis1", "m1m4", "cot_lvl", "cot_chg3", "oecd_dev", "us_stk_dev", "usd3", "sp3", "ovx", "ovx_rel", "bw", "bw_chg"]
if __name__ == "__main__":
    RES = {"H": H, "oos_start": str(OOS0.date())[:7], "K_signals": len(SIGNALS), "targets": {}}
    for tgt in ["wti", "brent"]:
        X, me = build(tgt); rows = []
        # benchmarks: futuuri itself and 'funda-free' constants
        fut = X.fut.dropna(); d = pd.concat([X.y, X.fut], axis=1).dropna(); d = d[d.index >= OOS0]
        base = dict(fut_ratio=round(float(np.sqrt(((d.y - d.fut) ** 2).mean()) / np.sqrt((d.y ** 2).mean())), 3), n_fut=int(len(d)),
                    fut_periods={f"{a[:4]}-{b[:4]}": round(float(np.sqrt(((s.y - s.fut) ** 2).mean()) / np.sqrt((s.y ** 2).mean())), 3) for a, b in PER for s in [d[(d.index >= a) & (d.index <= b + "-28")]] if len(s) >= 12})
        for c in SIGNALS:
            for ic in [False]:
                ev = evaluate(X, walk(X, [c], intercept=ic), c)
                if ev: rows.append(ev)
        rows.sort(key=lambda r: r["ratio"]); RES["targets"][tgt] = dict(baseline=base, univariate=rows)
        print(f"\n== {tgt.upper()} h={H} OOS {RES['oos_start']}→: futuuri vs no-change {base['fut_ratio']} (n={base['n_fut']}) {base['fut_periods']}")
        print(f"{'signal':10s} {'n':>4s} {'ratio':>6s} {'CW t':>6s} {'p(1s)':>7s} {'hit':>5s} {'corr':>6s} | periods | vs futuuri (ratio, CW t)")
        for r in rows: print(f"{r['label']:10s} {r['n']:4d} {r['ratio']:6.3f} {r['cw_t']:6.2f} {r['cw_p1']:7.4f} {r['sign_hit']:5.2f} {r['corr']:6.3f} | {r['periods']} | {r.get('vs_fut',{}).get('ratio_to_fut')} {r.get('vs_fut',{}).get('cw_t')}")
    json.dump(RES, open(f"{D}/edge3m.json", "w"), indent=1, default=float)

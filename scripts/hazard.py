#!/usr/bin/env python3
"""Daily Hormuz reopening hazard: calibrate the 2-state tree to each day's WTI/Brent futures curve (2026 crisis),
relate hazard changes to tanker transits (IMF PortWatch), the daily GPR index and OVX, and nowcast the next move.
Writes data/hazard.json."""
import json, glob, warnings, numpy as np, pandas as pd, statsmodels.api as sm
warnings.filterwarnings("ignore")
D = "/home/claude/oil/data"; RAW = f"{D}/raw"; R3 = f"{D}/raw3"; R5 = f"{D}/raw5"
MON = {c: i + 1 for i, c in enumerate("FGHJKMNQUVXZ")}
HL = 4.0; HMAX = 30; GRID = np.linspace(0.005, 0.6, 120)

def load_contracts(root):
    out = {}
    for fn in sorted(glob.glob(f"{R3}/yahoo/{root}*.NYM.json")):
        code = fn.split("/")[-1].split(".")[0]
        try:
            j = json.load(open(fn))["chart"]["result"][0]; s = pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna()
            s = s[~s.index.duplicated(keep="last")]; out[code] = (2000 + int(code[-2:]), MON[code[-3]], s)
        except Exception as e: print("skip", code, e)
    return out

def daily_curves(root, front=None):
    """Return dict date -> {months_ahead: price} using Yahoo contracts (+ optional EIA front series for m=1)."""
    con = load_contracts(root); dates = sorted(set().union(*[set(s.index) for _, _, s in con.values()]))
    curves = {}
    for t in dates:
        if t < pd.Timestamp("2025-06-01"): continue
        c = {}
        for code, (yr, mo, s) in con.items():
            if t in s.index:
                m = (yr - t.year) * 12 + mo - t.month
                if m >= 1 and m <= 36: c[m] = float(s.loc[t])
        if front is not None and t in front.index and 1 not in c: c[1] = float(front.loc[t])
        if len(c) >= 4: curves[t] = c
    return curves

# expected price path under hazard h: closed at P_closed, reopening -> converge to P_open with half-life HL
def path_matrix():
    M = np.zeros((len(GRID), HMAX))
    for gi, h in enumerate(GRID):
        surv = (1 - h) ** np.arange(0, HMAX + 1)
        for m in range(1, HMAX + 1):
            w_closed = surv[m]; w_open = 0.0
            for j in range(1, m + 1): w_open += surv[j - 1] * h * 0.5 ** ((m - j) / HL)   # weight on (P_closed - P_open) still remaining
            M[gi, m - 1] = w_closed + w_open   # E[P_m] = P_open + (P_closed - P_open) * M
    return M
PM = path_matrix()

def calibrate(c, p_open_fallback=None):
    c = {m: p for m, p in c.items() if m >= 2} if len([m for m in c if m >= 2]) >= 4 else dict(c)   # drop the prompt month: its premium is convenience yield / expiry squeeze, not reopening odds
    ms = sorted(c); P_closed = c[ms[0]]
    P_open = c[ms[-1]] if ms[-1] >= 24 else (p_open_fallback if p_open_fallback is not None else c[ms[-1]])   # long-run level: >=24-month point, else fallback
    if ms[-1] < 12 or P_closed - P_open < 8: return np.nan, P_closed, P_open   # no crisis premium to calibrate
    idx = np.array([m for m in ms if m <= HMAX]) - 1; y = np.array([c[m + 1] for m in idx])
    pred = P_open + (P_closed - P_open) * PM[:, idx]; err = ((pred - y) ** 2).sum(axis=1)
    return float(GRID[int(err.argmin())]), P_closed, P_open

front_wti = pd.read_csv(f"{D}/futures_daily.csv", parse_dates=["date"]).set_index("date")["cl1"].dropna()
rows = []; back_cl = {}; m1m2 = {}
for root, front in [("CL", front_wti), ("BZ", None)]:
    cv = daily_curves(root, front)
    for t, c in cv.items():
        fb = (back_cl.get(t, 73.0) + 4.0) if root == "BZ" else 73.0
        h, pc, po = calibrate(c, fb); rows.append(dict(date=t, root=root, hazard=h, front=pc, back=po, n=len(c), m_max=max(c)))
        if root == "CL":
            back_cl[t] = c[max(c)] if max(c) >= 24 else 73.0; ms = sorted(c); m1m2[t] = c[ms[0]] - c[ms[1]] if len(ms) > 1 else np.nan
H = pd.DataFrame(rows).pivot(index="date", columns="root", values=["hazard", "front", "back"]); H.columns = [f"{a}_{b}" for a, b in H.columns]
H = H.sort_index()
# ---- signals ----
hz = pd.read_csv(f"{D}/hormuz_daily.csv", parse_dates=["date"]).set_index("date")["n_tanker"].astype(float)
tr7 = hz.rolling(7).mean()
gpr = pd.read_excel(f"{R5}/gpr_daily.xls"); gpr["date"] = pd.to_datetime(gpr["date"]); gpr = gpr.set_index("date")
gprd = gpr["GPRD"].astype(float); gthreat = gpr["GPRD_THREAT"].astype(float); gpr7 = gprd.rolling(7).mean()
_o = pd.read_csv(f"{R3}/fred_OVX.csv"); _o.columns = ["date", "value"]; _o["date"] = pd.to_datetime(_o["date"]); ovx = pd.to_numeric(_o.set_index("date")["value"], errors="coerce").dropna()
fd = pd.read_csv(f"{D}/futures_daily.csv", parse_dates=["date"]).set_index("date")
X = pd.DataFrame(index=H.index)
X["tr7"] = tr7.reindex(X.index, method="ffill"); X["dtr7"] = (tr7 - tr7.shift(7)).reindex(X.index, method="ffill")
X["gpr7"] = gpr7.reindex(X.index, method="ffill"); X["dgpr7"] = (gpr7 - gpr7.shift(7)).reindex(X.index, method="ffill"); X["gthreat7"] = gthreat.rolling(7).mean().reindex(X.index, method="ffill")
X["ovx"] = ovx.reindex(X.index, method="ffill"); X["dovx5"] = (ovx - ovx.shift(5)).reindex(X.index, method="ffill")
X["m1m2"] = pd.Series(m1m2).reindex(X.index)   # front spread from the Yahoo curve (two nearest maturities)
A = pd.concat([H, X], axis=1)
C = A[A.hazard_CL.notna()].copy()   # crisis sample
res = {}
for root in ["CL", "BZ"]:
    hcol = f"hazard_{root}"; s = A[hcol]
    d3 = (s.shift(-3) - s)   # change over next 3 trading days
    df = pd.concat([d3.rename("dh3"), A.dtr7, A.dgpr7, A.dovx5, (s - s.shift(3)).rename("dh_lag")], axis=1).dropna()
    df = df[df.index >= "2026-03-01"]
    if len(df) < 30: continue
    Z = sm.add_constant(df[["dtr7", "dgpr7", "dovx5", "dh_lag"]]); m = sm.OLS(df.dh3, Z).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    # cross-correlation: corr(dh3 at t, dtr7 at t+k): k<0 -> transits lead
    xc = {}
    for k in range(-10, 11):
        xc[k] = float(df.dh3.corr(A.dtr7.shift(-k).reindex(df.index)))
    res[root] = dict(n=int(m.nobs), r2=round(float(m.rsquared), 3), coef={k: round(float(v), 5) for k, v in m.params.items()}, t={k: round(float(v), 2) for k, v in m.tvalues.items()},
                     xcorr={str(k): round(v, 3) for k, v in xc.items()}, sd_dtr7=round(float(df.dtr7.std()), 2), sd_dgpr7=round(float(df.dgpr7.std()), 2), sd_dh3=round(float(df.dh3.std()), 4))
    print(f"{root}: n={m.nobs:.0f} R²={m.rsquared:.3f} | " + " ".join(f"{k} {v:+.4f} (t {m.tvalues[k]:+.1f})" for k, v in m.params.items()))
    best = max(xc.items(), key=lambda kv: abs(kv[1])); print(f"   ristikorrelaatio Δh(3pv) vs Δtransitit: vahvin k={best[0]} r={best[1]:+.2f}; k=0 {xc[0]:+.2f}, k=-3 {xc[-3]:+.2f}, k=+3 {xc[3]:+.2f}")
# ---- now / nowcast ----
last = A.index[-1]; now = {}
for root in ["CL", "BZ"]:
    h = float(A[f"hazard_{root}"].dropna().iloc[-1]); hd = str(A[f"hazard_{root}"].dropna().index[-1].date())
    r = res.get(root); adj = 0.0
    if r:
        c = r["coef"]; x = A.loc[last]
        adj = float(c["dtr7"] * (0 if np.isnan(x.dtr7) else x.dtr7) + c["dgpr7"] * (0 if np.isnan(x.dgpr7) else x.dgpr7) + c["dovx5"] * (0 if np.isnan(x.dovx5) else x.dovx5))
    hn = float(np.clip(h + 0.5 * adj, 0.005, 0.6))
    now[root] = dict(hazard=round(h, 4), hazard_date=hd, nowcast=round(hn, 4), adj_3d=round(adj, 4), p_open={str(k): round(float(1 - (1 - h) ** k), 3) for k in [1, 3, 6, 12, 24]}, p_open_nowcast={str(k): round(float(1 - (1 - hn) ** k), 3) for k in [1, 3, 6, 12, 24]},
                     front=round(float(A[f"front_{root}"].dropna().iloc[-1]), 2), back=round(float(A[f"back_{root}"].dropna().iloc[-1]), 2), expected_months=round(1 / h, 1))
    print(f"{root} nyt: hasardi {h*100:.1f} %/kk ({hd}), nowcast {hn*100:.1f} %/kk (3 pv säätö {adj*100:+.2f} %-yks); P(auki) 3/6/12 kk {now[root]['p_open']['3']*100:.0f}/{now[root]['p_open']['6']*100:.0f}/{now[root]['p_open']['12']*100:.0f} %")
sig = dict(date=str(last.date()), transits7=round(float(A.tr7.iloc[-1]), 1), dtr7=round(float(A.dtr7.iloc[-1]), 1), transits_normal=round(float(hz.loc["2019":"2025"].mean()), 1), gpr7=round(float(A.gpr7.iloc[-1]), 1), dgpr7=round(float(A.dgpr7.iloc[-1]), 1),
           gpr_last=round(float(gprd.dropna().iloc[-1]), 1), gpr_date=str(gprd.dropna().index[-1].date()), gpr_mean_2025=round(float(gprd.loc["2025"].mean()), 1), ovx=round(float(A.ovx.dropna().iloc[-1]), 1), m1m2=round(float(A.m1m2.dropna().iloc[-1]), 2), transits_date=str(hz.index[-1].date()))
print("signaalit:", sig)
S = A.loc["2026-01-01":]
ser = dict(date=[str(t.date()) for t in S.index], hazard_wti=[None if np.isnan(v) else round(v, 4) for v in S.hazard_CL], hazard_brent=[None if np.isnan(v) else round(v, 4) for v in S.hazard_BZ],
           front_wti=[None if np.isnan(v) else round(v, 2) for v in S.front_CL], transits7=[None if np.isnan(v) else round(v, 1) for v in S.tr7], gpr7=[None if np.isnan(v) else round(v, 1) for v in S.gpr7], ovx=[None if np.isnan(v) else round(v, 1) for v in S.ovx],
           p6_wti=[None if np.isnan(v) else round(float(1 - (1 - v) ** 6), 3) for v in S.hazard_CL])
OUT = dict(series=ser, regression=res, now=now, signals=sig, params=dict(half_life_months=HL, P_open="curve back end (longest maturity)", P_closed="front contract", crisis_rule="front - back >= 8 $ and curve >= 12 months"))
json.dump(OUT, open(f"{D}/hazard.json", "w"), default=float); print("saved", len(ser["date"]), "days; hazard non-NaN", int(S.hazard_CL.notna().sum()))

#!/usr/bin/env python3
"""Second pass of the 3-month edge search: new signal families (STEO gap and revisions, geopolitical risk, EIA inventory surprises, seasonality),
curve-shrinkage models, small multivariate combinations, and robustness over neighbouring horizons. Same walk-forward protocol as edge3m.py."""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__)); import edge3m as E
D = E.D
sv = pd.read_csv(f"{D}/steo_vintages.csv"); sv["month"] = pd.to_datetime(sv["month"]); SV = {v: g.set_index("month")[["wti", "brent"]] for v, g in sv.groupby("vintage")}
gpr = pd.read_excel(f"{D}/raw5/gpr_daily.xls"); gpr["date"] = pd.to_datetime(gpr["date"]); gpr = gpr.set_index("date")
cons = pd.read_csv(f"{E.R3}/eia_crude_consensus_investing.csv"); cons["date"] = pd.to_datetime(cons["time"].str[:10]); cons = cons.dropna(subset=["actual", "forecast"]).sort_values("date"); cons["surp"] = cons["actual"] - cons["forecast"]
def extend(X, tgt, h):
    X = X.copy(); idx = X.index; me = E.dd[tgt].resample("MS").last()
    sg, sr = [], []
    for t in idx:
        v = SV.get(str(t.date())[:7]); vp = SV.get(str((t - pd.DateOffset(months=1)).date())[:7]); tt = t + pd.DateOffset(months=h)
        a = float(v[tgt].get(tt, np.nan)) if v is not None and tt in v.index else np.nan; b = float(vp[tgt].get(tt, np.nan)) if vp is not None and tt in vp.index else np.nan
        pm = float(me.get(t, np.nan)); sg.append(np.log(a / pm) if a == a and pm == pm else np.nan); sr.append(np.log(a / b) if a == a and b == b else np.nan)
    X["steo_gap"] = sg; X["steo_rev"] = sr; X["steo_vs_fut"] = X["steo_gap"] - X["basisH"]
    g = np.log(gpr["GPRD"]).resample("MS").mean().reindex(idx); X["gpr"] = g - g.rolling(36, min_periods=24).mean(); X["gpr_chg"] = g - g.shift(3)
    th = np.log(gpr["GPRD_THREAT"]).resample("MS").mean().reindex(idx); X["gpr_thr"] = th - th.rolling(36, min_periods=24).mean()
    s = cons.set_index("date")["surp"]; eo = []
    for t in idx:
        end = (t + pd.offsets.MonthEnd(0)); w = s[(s.index <= end) & (s.index > end - pd.Timedelta(days=91))]; eo.append(float(w.sum()) if len(w) >= 8 else np.nan)
    X["eia_surp"] = eo
    return X
def season(X, h, start=E.OOS0, shrink=0.5):
    pred = pd.Series(np.nan, index=X.index)
    for t in X.index[X.index >= start]:
        tr = X[X.index <= t - pd.DateOffset(months=h)].dropna(subset=["y"]); tr = tr[tr.index.month == t.month]
        if len(tr) >= 8: pred[t] = shrink * float(tr.y.mean())
    return pred
def run(tgt, h, verbose=True):
    E.H = h; X, me = E.build(tgt); X["basisH"] = [np.nan] * len(X)
    lastday = E.dd[tgt].resample("MS").apply(lambda x: x.index[-1] if len(x) else pd.NaT); b = []
    for t, ld in lastday.items():
        pw = float(E.dd["wti"].get(ld, np.nan)) if (not pd.isna(ld) and ld in E.dd["wti"].index) else np.nan; f = E.fut_wti(ld, h) if not pd.isna(ld) else np.nan; b.append(np.log(f / pw) if (f == f and pw == pw) else np.nan)
    X["basisH"] = b; X["fut"] = X["basisH"]; X = extend(X, tgt, h); res = []
    new = ["steo_gap", "steo_rev", "steo_vs_fut", "gpr", "gpr_chg", "gpr_thr", "eia_surp"]
    for c in new + ["basisH", "m1m4", "r3", "ma36", "bw"]:
        ev = E.evaluate(X, E.walk(X, [c]), c)
        if ev: res.append(ev)
    ev = E.evaluate(X, season(X, h), "season"); res.append(ev) if ev else None
    # curve shrinkage with intercept (drift allowed), and combinations (ridge on standardised inputs)
    for label, cols, ic, rg in [("basisH+int", ["basisH"], True, 0.0), ("m1m4+int", ["m1m4"], True, 0.0), ("m1m4+basisH", ["m1m4", "basisH"], False, 0.02), ("m1m4+r3", ["m1m4", "r3"], False, 0.02), ("m1m4+r3+ma36", ["m1m4", "r3", "ma36"], False, 0.05),
                                ("curve+steo", ["m1m4", "steo_gap"], False, 0.02), ("curve+bw+r3", ["m1m4", "bw", "r3"], False, 0.05), ("mom+curve+bw+gpr", ["m1m4", "r3", "bw", "gpr"], False, 0.05)]:
        ev = E.evaluate(X, E.walk(X, cols, intercept=ic, ridge=rg), label)
        if ev: res.append(ev)
    res.sort(key=lambda r: r["ratio"])
    if verbose:
        print(f"\n== {tgt.upper()} h={h}")
        for r in res: print(f"{r['label']:18s} n={r['n']:3d} ratio={r['ratio']:.3f} CW t={r['cw_t']:5.2f} p1={r['cw_p1']:.3f} hit={r['sign_hit']:.2f} | {r['periods']} | vsFut {r.get('vs_fut',{}).get('ratio_to_fut')} t={r.get('vs_fut',{}).get('cw_t')}")
    return res
if __name__ == "__main__":
    out = {}
    for tgt in ["wti", "brent"]:
        out[tgt] = {}
        for h in [3, 2, 4]: out[tgt][str(h)] = run(tgt, h, verbose=(h == 3))
    print("\nrobustness over horizons (ratio vs no-change):")
    for tgt in ["wti", "brent"]:
        labs = sorted({r["label"] for h in out[tgt] for r in out[tgt][h]})
        for l in labs:
            row = {h: next((r["ratio"] for r in out[tgt][h] if r["label"] == l), None) for h in ["2", "3", "4"]}
            if row["3"] is not None and row["3"] < 0.99: print(f"  {tgt} {l:18s} {row}")
    json.dump(out, open(f"{D}/edge3m_b.json", "w"), indent=1, default=float)

#!/usr/bin/env python3
"""Fourth pass: (a) robustness of the curve-slope effect (leave-episode-out, robust regression, trading-rule P&L vs the futuuri),
(b) STEO real-time balance signals incl. the expected OPEC production change (tests the supply-return thesis historically)."""
import os, sys, json, numpy as np, pandas as pd, statsmodels.api as sm
sys.path.insert(0, os.path.dirname(__file__)); import edge3m as E; import edge3m_c as C
def balance_signals(X, h):
    sb = pd.read_csv(f"{E.D}/steo_balance.csv"); sb["month"] = pd.to_datetime(sb["month"]); V = {v: g.set_index("month") for v, g in sb.groupby("vintage")}; rows = []
    for t in X.index:
        g = V.get(str(t.date())[:7]); gp = V.get(str((t - pd.DateOffset(months=1)).date())[:7]); tt = [t + pd.DateOffset(months=k) for k in range(1, h + 1)]
        if g is None or any(m not in g.index for m in tt) or t not in g.index: rows.append([np.nan] * 5); continue
        bal = (g.prod - g.cons); bal_fc = float(bal.loc[tt].mean()); rev = np.nan
        if gp is not None and all(m in gp.index for m in tt): rev = bal_fc - float((gp.prod - gp.cons).loc[tt].mean())
        rows.append([float(np.log(g.opec.loc[tt[-1]] / g.opec.loc[t])), bal_fc, float(bal.loc[t]), rev, float(g.stchg.loc[tt].mean()) if "stchg" in g and g.stchg.loc[tt].notna().all() else np.nan])
    X[["opec_fc", "bal_fc", "bal_now", "bal_rev", "stchg_fc"]] = rows; return X
def main():
    h = 3; res = {}
    for tgt in ["wti", "brent"]:
        X = C.prep(tgt, h); X = balance_signals(X, h); print(f"\n===== {tgt.upper()} h={h} =====")
        # (a) robustness of beta on the curve basis
        d = X.dropna(subset=["y", "basisH"]); d = d[d.index >= "2010-01-01"]
        def beta(s, col="basisH"): m = sm.OLS(s.y, s[[col]]).fit(cov_type="HAC", cov_kwds={"maxlags": 3}); return m.params[col], m.bse[col]
        print(f"beta(basisH) all {beta(d)[0]:.2f}±{beta(d)[1]:.2f} | ex 2020-02..2020-09 {beta(d[(d.index < '2020-02-01') | (d.index > '2020-09-30')])[0]:.2f}±{beta(d[(d.index < '2020-02-01') | (d.index > '2020-09-30')])[1]:.2f} | ex 2022 {beta(d[(d.index < '2022-01-01') | (d.index > '2022-12-31')])[0]:.2f}±{beta(d[(d.index < '2022-01-01') | (d.index > '2022-12-31')])[1]:.2f} | ex both {beta(d[((d.index < '2020-02-01') | (d.index > '2020-09-30')) & ((d.index < '2022-01-01') | (d.index > '2022-12-31'))])[0]:.2f}±{beta(d[((d.index < '2020-02-01') | (d.index > '2020-09-30')) & ((d.index < '2022-01-01') | (d.index > '2022-12-31'))])[1]:.2f}")
        rl = sm.RLM(d.y, d[["basisH"]], M=sm.robust.norms.HuberT()).fit(); print(f"Huber robust beta {rl.params['basisH']:.2f}±{rl.bse['basisH']:.2f}")
        # trading rule vs the curve: position = sign((beta-1)*basis) with beta estimated walk-forward; P&L = pos * (y - basis) in log points
        pb = E.walk(X, ["basisH"]); t = pd.concat([X.y, X.basisH, pb.rename("p")], axis=1).dropna(); t = t[t.index >= E.OOS0]; pos = np.sign(t.p - t.basisH); pnl = pos * (t.y - t.basisH)
        tt, pp = E.nw_t(pnl.values); print(f"rule 'short when curve under-predicts the roll': n={len(t)}, mean pnl {pnl.mean()*100:.2f} % per trade, hit {np.mean(pnl>0):.2f}, NW t={tt:.2f}; by period: " + str({f"{a[:4]}-{b[:4]}": round(float(pnl[(pnl.index >= a) & (pnl.index <= b + '-28')].mean() * 100), 2) for a, b in E.PER}))
        # (b) STEO balance signals
        print("STEO balance signals (walk-forward, no intercept):")
        for c in ["opec_fc", "bal_fc", "bal_now", "bal_rev", "stchg_fc"]:
            ev = E.evaluate(X, E.walk(X, [c]), c)
            if not ev: continue
            m = sm.OLS(X.dropna(subset=["y", c]).y, X.dropna(subset=["y", c])[[c]]).fit(cov_type="HAC", cov_kwds={"maxlags": 3}); b_, se_ = m.params[c], m.bse[c]
            print(f"  {c:9s} n={ev['n']:3d} ratio={ev['ratio']:.3f} CW t={ev['cw_t']:5.2f} p1={ev['cw_p1']:.3f} hit={ev['sign_hit']:.2f} beta={b_:.2f}±{se_:.2f} {ev['periods']}")
            res[f"{tgt}_{c}"] = dict(ev, beta=float(b_), se=float(se_))
        for cols, lab in [(["basisH", "bal_fc"], "curve+bal_fc"), (["basisH", "opec_fc"], "curve+opec_fc"), (["basisH", "bal_rev"], "curve+bal_rev"), (["basisH", "bal_fc", "opec_fc"], "curve+bal+opec")]:
            ev = E.evaluate(X, E.walk(X, cols, ridge=0.02), lab)
            if ev: print(f"  {lab:14s} n={ev['n']:3d} ratio={ev['ratio']:.3f} CW t={ev['cw_t']:5.2f} p1={ev['cw_p1']:.3f} {ev['periods']} vsFut {ev.get('vs_fut',{}).get('ratio_to_fut')} t={ev.get('vs_fut',{}).get('cw_t')}"); res[f"{tgt}_{lab}"] = ev
    json.dump(res, open(f"{E.D}/edge3m_d.json", "w"), indent=1, default=float)
if __name__ == "__main__": main()

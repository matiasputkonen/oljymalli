#!/usr/bin/env python3
"""Third pass: curve-slope signals computed consistently over the whole sample (EIA CL1-4 to 4/2024, Yahoo contracts after), coefficient
estimates, behaviour in crisis regimes, and block-bootstrap uncertainty of the RMSE gain."""
import os, sys, json, numpy as np, pandas as pd, statsmodels.api as sm
sys.path.insert(0, os.path.dirname(__file__)); import edge3m as E; import edge3m_b as B
def prep(tgt, h):
    E.H = h; X, me = E.build(tgt); lastday = E.dd[tgt].resample("MS").apply(lambda x: x.index[-1] if len(x) else pd.NaT); rows = []
    for t, ld in lastday.items():
        if pd.isna(ld): rows.append((np.nan,) * 5); continue
        pw = float(E.dd["wti"].get(ld, np.nan)) if ld in E.dd["wti"].index else np.nan; F = {k: E.fut_wti(ld, k) for k in [1, 2, 3, 4, h]}
        ok = lambda a, b: np.log(a / b) if (a == a and b == b and a > 0 and b > 0) else np.nan
        rows.append((ok(F[h], pw), ok(F[1], F[4]), ok(F[1], F[3]), ok(F[2], F[4]), ok(F[1], pw)))
    X[["basisH", "bk14", "bk13", "bk24", "basis1"]] = pd.DataFrame(rows, index=X.index); X["fut"] = X["basisH"]; return X
def main():
    out = {}
    for tgt in ["wti", "brent"]:
        for h in [3]:
            X = prep(tgt, h); print(f"\n== {tgt.upper()} h={h}: slope signals over full OOS (coverage {X.bk14.dropna().index.min().date()} → {X.bk14.dropna().index.max().date()})")
            for c in ["basisH", "bk14", "bk13", "bk24"]:
                ev = E.evaluate(X, E.walk(X, [c]), c); print(f"  {c:7s} n={ev['n']} ratio={ev['ratio']} CW t={ev['cw_t']} p1={ev['cw_p1']} hit={ev['sign_hit']} {ev['periods']} vsFut {ev.get('vs_fut',{}).get('ratio_to_fut')} t={ev.get('vs_fut',{}).get('cw_t')}")
                out[f"{tgt}_{c}"] = ev
            d = X.dropna(subset=["y", "bk14", "basisH"]); d = d[d.index >= "2010-01-01"]
            for c in ["basisH", "bk14"]:
                m = sm.OLS(d.y, d[[c]]).fit(cov_type="HAC", cov_kwds={"maxlags": 3}); print(f"  full-sample beta({c}) = {m.params[c]:.2f} ± {m.bse[c]:.2f} (HAC), n={len(d)}; mean({c})={d[c].mean():.3f} sd={d[c].std():.3f}")
            for a, b in [("2010", "2016"), ("2017", "2019"), ("2020", "2022"), ("2023", "2026")]:
                s = d[(d.index >= a) & (d.index <= b + "-12-31")]
                if len(s) > 12: m = sm.OLS(s.y, s[["basisH"]]).fit(cov_type="HAC", cov_kwds={"maxlags": 3}); print(f"    beta(basisH) {a}-{b}: {m.params['basisH']:.2f} ± {m.bse['basisH']:.2f} (n={len(s)})")
            # crisis behaviour: origins 2022-02..2022-07 and 2026-03..2026-07, forecast vs actual (log pts)
            p = E.walk(X, ["basisH"]); 
            for lab, a, b in [("Ukraina 2022", "2022-02-01", "2022-08-01"), ("Hormuz 2026", "2026-03-01", "2026-07-01")]:
                s = pd.concat([X.y, X.basisH, p.rename("beta_fc")], axis=1).loc[a:b].dropna(subset=["y"])
                print(f"    {lab}: actual 3m log change {np.round(s.y.values,3)} | curve {np.round(s.basisH.values,3)} | beta-shrunk {np.round(s.beta_fc.values,3)}")
            # block bootstrap of RMSE-ratio (basisH-beta model vs no-change), 6-month blocks
            pr = E.walk(X, ["basisH"]); dd_ = pd.concat([X.y, pr.rename("p")], axis=1).dropna(); dd_ = dd_[dd_.index >= E.OOS0]; y = dd_.y.values; pp = dd_.p.values; n = len(y); rng = np.random.default_rng(1); rs = []
            for _ in range(2000):
                idx = np.concatenate([np.arange(s, s + 6) % n for s in rng.integers(0, n, n // 6 + 1)])[:n]; rs.append(np.sqrt(((y[idx] - pp[idx]) ** 2).mean() / (y[idx] ** 2).mean()))
            print(f"    bootstrap RMSE ratio basisH-model: median {np.median(rs):.3f}, 90 % interval {np.percentile(rs,5):.3f}–{np.percentile(rs,95):.3f}, P(ratio<1) = {np.mean(np.array(rs)<1):.2f}")
            out[f"{tgt}_boot"] = dict(median=float(np.median(rs)), lo=float(np.percentile(rs, 5)), hi=float(np.percentile(rs, 95)), p_lt1=float(np.mean(np.array(rs) < 1)))
    json.dump(out, open(f"{E.D}/edge3m_c.json", "w"), indent=1, default=float)
if __name__ == "__main__": main()

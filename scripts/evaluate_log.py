#!/usr/bin/env python3
"""Item 8: calibration of logged forecasts once targets realise. Reads data/forecast_log.csv, scores every forecast whose target
month is complete: error, PIT (piecewise-linear CDF through the logged quantiles), 50/90 % coverage, CRPS (quantile approximation),
and Brier for the hazard-implied P(open) when data/resolution.json marks the reopening. Writes data/eval.json."""
import os, json, numpy as np, pandas as pd
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); D = f"{ROOT}/data"
M = pd.read_csv(f"{D}/panel_monthly.csv", index_col=0, parse_dates=True); today = pd.Timestamp(pd.Timestamp.today().date())
log = pd.read_csv(f"{D}/forecast_log.csv") if os.path.exists(f"{D}/forecast_log.csv") else pd.DataFrame()
res = dict(n_logged=int(len(log)), n_runs=int(log.run.nunique()) if len(log) else 0, first_target=None, scored=[], summary={}, generated=str(today.date()))
if len(log):
    log["target_month"] = pd.to_datetime(log["target_month"] + "-01"); res["first_target"] = str(log.target_month.min().date())[:7]
    # keep one forecast per day per (target, h): the last run of the day
    log["run_day"] = log.run.str[:10]; log = log.sort_values("run").groupby(["run_day", "target", "h"]).tail(1)
    def pit(a, q05, q25, q50, q75, q95):
        xs = [q05, q25, q50, q75, q95]; ps = [0.05, 0.25, 0.5, 0.75, 0.95]
        if a <= xs[0]: return max(0.0, 0.05 * np.exp((a - xs[0]) / max(xs[1] - xs[0], 1e-6)))
        if a >= xs[-1]: return min(1.0, 1 - 0.05 * np.exp(-(a - xs[-1]) / max(xs[-1] - xs[-2], 1e-6)))
        return float(np.interp(a, xs, ps))
    def crps_q(a, qs):   # quantile-based CRPS approximation (average pinball loss × 2)
        ps = [0.05, 0.25, 0.5, 0.75, 0.95]; return float(2 * np.mean([max(p * (a - q), (p - 1) * (a - q)) for p, q in zip(ps, qs)]))
    comps = []   # logged components per forecast, for the weight grid
    for _, r in log.iterrows():
        tm = r.target_month
        if tm + pd.offsets.MonthEnd(0) + pd.Timedelta(days=2) > today or tm not in M.index or pd.isna(M.loc[tm, r.target]): continue
        a = float(M.loc[tm, r.target]); qs = [r.p05, r.p25, r.comb, r.p75, r.p95]
        if any(pd.isna(qs)): continue
        cp = [r.get("model_median"), r.get("curve"), r.get("steo"), r.get("view")]
        if not any(pd.isna(v) for v in cp): comps.append(dict(run=r.run, target=r.target, h=int(r.h), target_month=str(tm.date())[:7], actual=a, funda=float(cp[0]), futuuri=float(cp[1]), steo=float(cp[2]), nakemys=float(cp[3])))
        res["scored"].append(dict(run=r.run, target=r.target, h=int(r.h), target_month=str(tm.date())[:7], actual=round(a, 2), forecast=round(float(r.comb), 2), curve=(None if pd.isna(r.curve) else round(float(r.curve), 2)), error=round(a - float(r.comb), 2),
                                  abs_err_pct=round(abs(a - float(r.comb)) / float(r.anchor) * 100, 2), pit=round(pit(a, *qs), 3), in50=bool(r.p25 <= a <= r.p75), in90=bool(r.p05 <= a <= r.p95), crps=round(crps_q(a, qs), 2),
                                  nochange_err=round(a - float(r.anchor), 2), curve_err=(None if pd.isna(r.curve) else round(a - float(r.curve), 2)), base_err=(None if ("comb_base" not in r or pd.isna(r.get("comb_base"))) else round(a - float(r.comb_base), 2)), view_err=(None if ("view" not in r or pd.isna(r.get("view"))) else round(a - float(r.view), 2)), steo_err=(None if ("steo" not in r or pd.isna(r.get("steo"))) else round(a - float(r.steo), 2))))
    sc = pd.DataFrame(res["scored"])
    if len(sc):
        for (t, h), g in sc.groupby(["target", "h"]):
            res["summary"][f"{t}_{h}"] = dict(n=int(len(g)), mae=round(float(g.error.abs().mean()), 2), rmse=round(float(np.sqrt((g.error**2).mean())), 2), rmse_nochange=round(float(np.sqrt((g.nochange_err**2).mean())), 2),
                                             rmse_curve=(round(float(np.sqrt((g.curve_err.dropna()**2).mean())), 2) if g.curve_err.notna().any() else None), cov50=round(float(g.in50.mean()), 2), cov90=round(float(g.in90.mean()), 2), pit_mean=round(float(g.pit.mean()), 3), crps=round(float(g.crps.mean()), 2),
                                             rmse_base=(round(float(np.sqrt((g.base_err.dropna()**2).mean())), 2) if g.base_err.notna().any() else None), rmse_view=(round(float(np.sqrt((g.view_err.dropna()**2).mean())), 2) if g.view_err.notna().any() else None), rmse_steo=(round(float(np.sqrt((g.steo_err.dropna()**2).mean())), 2) if g.steo_err.notna().any() else None))
# ---- weight grid: every combination of funda/futuuri/STEO/näkemys in 5 % steps, scored on the logged components (one forecast per
# target month and horizon: the last run of the origin month). 1771 combinations; with few resolved months the best one is partly luck,
# so the landscape (median, pure components, current weights' rank) matters more than the winner. ----
try:
    import itertools
    STEP = 0.05; GRID = [(a, b, c, round(1 - a - b - c, 2)) for a in np.round(np.arange(0, 1 + 1e-9, STEP), 2) for b in np.round(np.arange(0, 1 - a + 1e-9, STEP), 2) for c in np.round(np.arange(0, 1 - a - b + 1e-9, STEP), 2)]
    Wg = np.array(GRID)   # columns: funda, futuuri, steo, näkemys
    try:
        vj = json.load(open(f"{D}/views.json")); ws0 = float(vj.get("steo_weight", 0)); wu0 = float(vj.get("user_view", {}).get("weight", 0)); cur_w = ((1 - ws0 - wu0) / 2, (1 - ws0 - wu0) / 2, ws0, wu0)
    except Exception: cur_w = (0.5, 0.5, 0.0, 0.0)
    grid_out = dict(n_combos=len(GRID), step=STEP, current=[round(x, 3) for x in cur_w], groups={}, pooled={})
    if len(log) and len(comps):
        C = pd.DataFrame(comps); C = C.sort_values("run").groupby(["target", "h", "target_month"]).tail(1)
        def score(g):
            X = g[["funda", "futuuri", "steo", "nakemys"]].values; a = g.actual.values[:, None]
            E = a - X @ Wg.T; rmse = np.sqrt((E ** 2).mean(axis=0)); order = np.argsort(rmse)
            d = np.abs(Wg - np.array(cur_w)).sum(axis=1); ci = int(np.argmin(d)); rank = int((rmse < rmse[ci]).sum()) + 1
            pure = {k: round(float(np.sqrt(((g.actual - g[k]) ** 2).mean())), 2) for k in ["funda", "futuuri", "steo", "nakemys"]}
            eq = round(float(np.sqrt(((g.actual - X.mean(axis=1)) ** 2).mean())), 2)
            from scipy.optimize import nnls   # exact optimum (weights >= 0, sum = 1): the grid only maps the landscape around it
            Xa = np.vstack([X, 1000 * np.ones((1, 4))]); ya = np.append(g.actual.values, 1000.0); wo, _ = nnls(Xa, ya); wo = wo / wo.sum()
            opt = dict(w=[round(float(x), 3) for x in wo], rmse=round(float(np.sqrt(((g.actual.values - X @ wo) ** 2).mean())), 2))
            return dict(n=int(len(g)), months=sorted(g.target_month.unique().tolist()), best=[dict(w=[float(x) for x in Wg[i]], rmse=round(float(rmse[i]), 2)) for i in order[:10]], current=dict(w=[round(x, 3) for x in cur_w], rmse=round(float(rmse[ci]), 2), rank=rank),
                        optimum=opt, median_rmse=round(float(np.median(rmse)), 2), worst_rmse=round(float(rmse.max()), 2), pure=pure, equal=eq)
        for (t, h), g in C.groupby(["target", "h"]): grid_out["groups"][f"{t}_{h}"] = score(g)
        for t, g in C.groupby("target"): grid_out["pooled"][t] = score(g)
    res["grid"] = grid_out
except Exception as e: res["grid_error"] = str(e)[:120]
# hazard / P(open) Brier: resolution file marks the month the strait reopened (>= 50 % of normal transits for a full month)
try:
    hz = pd.read_csv(f"{D}/hormuz_daily.csv", parse_dates=["date"]).set_index("date")["n_tanker"].astype(float); normal = float(hz.loc["2019":"2025"].mean()); mm = hz.resample("MS").mean()
    reopened = mm[(mm.index >= "2026-03-01") & (mm >= 0.5 * normal)]; res["reopen_month"] = str(reopened.index[0].date())[:7] if len(reopened) else None
    if len(log) and "hazard" in log.columns:
        rows = []
        for _, r in log.iterrows():
            if pd.isna(r.hazard): continue
            h = float(r.hazard); run_m = pd.Timestamp(r.run[:7] + "-01")
            for k in [3, 6]:
                due = run_m + pd.DateOffset(months=k)
                if due + pd.offsets.MonthEnd(0) > today: continue
                p = 1 - (1 - h) ** k; y = 1.0 if (res["reopen_month"] and pd.Timestamp(res["reopen_month"] + "-01") <= due) else 0.0
                rows.append(dict(run=r.run, k=k, p=round(p, 3), y=y, brier=round((p - y) ** 2, 3)))
        res["brier"] = dict(n=len(rows), mean=(round(float(np.mean([x["brier"] for x in rows])), 3) if rows else None), rows=rows[-20:])
except Exception as e: res["brier_error"] = str(e)[:100]
json.dump(res, open(f"{D}/eval.json", "w"), default=float)
print(f"eval: {res['n_logged']} kirjattua ennustetta {res['n_runs']} ajosta; pisteytetty {len(res['scored'])}; ensimmäinen kohdekuukausi {res['first_target']}; avautumiskuukausi {res.get('reopen_month')}")

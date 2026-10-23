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
    for _, r in log.iterrows():
        tm = r.target_month
        if tm + pd.offsets.MonthEnd(0) + pd.Timedelta(days=2) > today or tm not in M.index or pd.isna(M.loc[tm, r.target]): continue
        a = float(M.loc[tm, r.target]); qs = [r.p05, r.p25, r.comb, r.p75, r.p95]
        if any(pd.isna(qs)): continue
        res["scored"].append(dict(run=r.run, target=r.target, h=int(r.h), target_month=str(tm.date())[:7], actual=round(a, 2), forecast=round(float(r.comb), 2), curve=(None if pd.isna(r.curve) else round(float(r.curve), 2)), error=round(a - float(r.comb), 2),
                                  abs_err_pct=round(abs(a - float(r.comb)) / float(r.anchor) * 100, 2), pit=round(pit(a, *qs), 3), in50=bool(r.p25 <= a <= r.p75), in90=bool(r.p05 <= a <= r.p95), crps=round(crps_q(a, qs), 2),
                                  nochange_err=round(a - float(r.anchor), 2), curve_err=(None if pd.isna(r.curve) else round(a - float(r.curve), 2))))
    sc = pd.DataFrame(res["scored"])
    if len(sc):
        for (t, h), g in sc.groupby(["target", "h"]):
            res["summary"][f"{t}_{h}"] = dict(n=int(len(g)), mae=round(float(g.error.abs().mean()), 2), rmse=round(float(np.sqrt((g.error**2).mean())), 2), rmse_nochange=round(float(np.sqrt((g.nochange_err**2).mean())), 2),
                                             rmse_curve=(round(float(np.sqrt((g.curve_err.dropna()**2).mean())), 2) if g.curve_err.notna().any() else None), cov50=round(float(g.in50.mean()), 2), cov90=round(float(g.in90.mean()), 2), pit_mean=round(float(g.pit.mean()), 3), crps=round(float(g.crps.mean()), 2))
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

#!/usr/bin/env python3
"""Fair-value model + forecast cone for Brent and WTI. Writes model dict into data/page_data.json['model'][target]."""
import pandas as pd, numpy as np, json, statsmodels.api as sm, warnings; warnings.filterwarnings("ignore")
D = "/home/claude/oil/data"
M = pd.read_csv(f"{D}/panel_monthly.csv", index_col=0, parse_dates=True)
pg = json.load(open(f"{D}/page_data.json")); dates = pd.to_datetime(pg["dates"]); S = {s["key"]: s for s in pg["series"]}
hz = pd.Series(S["hormuz_tankers"]["values"], index=dates, dtype=float).fillna(50.0)
dev = lambda s: (s - s.rolling(36, min_periods=24).mean()) / 100
BASE = {"oecd_dev": dev(M.oecd_stocks), "opec": np.log(M.opec_prod), "hormuz": np.clip(1 - hz / 50.0, 0, 1), "usd": np.log(M.usd_broad),
        "cot": M.mm_net_wti / 100, "usstocks": dev(M.us_total_stocks), "sp": np.log(M.sp500)}
WTI_EXTRA = {"cushing_dev": dev(M.cushing * 10) / 10, "uscrude_dev": dev(M.us_crude_stocks), "usprod": np.log(M.us_prod), "spr_dev": dev(M.us_spr)}
DAILY = {t: pd.read_csv(f"{D}/raw/fred_{'WTI' if t == 'wti' else 'Brent'}_d.csv", parse_dates=["date"]).dropna().set_index("date")["value"].astype(float) for t in ["wti", "brent"]}
LABELS = {"oecd_dev": "OECD-varastot", "opec": "OPEC", "hormuz": "Hormuz", "usd": "dollari", "cot": "positiot", "usstocks": "USA-varastot yht.", "sp": "S&P",
          "cushing_dev": "Cushing", "uscrude_dev": "USA raakaöljyvarastot", "usprod": "USA tuotanto", "spr_dev": "SPR"}

def fit(df, alpha=0.0015):
    Xs = df.drop(columns="y"); mu = Xs.mean(); sd = Xs.std().replace(0, 1); Z = (Xs - mu) / sd
    m = sm.OLS(df.y, sm.add_constant(Z, has_constant="add")).fit_regularized(alpha=alpha, L1_wt=0.0)
    def pred(Xn): return float(np.dot(np.r_[1.0, ((Xn - mu) / sd).values.ravel()], m.params))
    return m, pred, pd.Series([pred(Xs.loc[[t]]) for t in Xs.index], index=Xs.index)

def build(target, feats, P0_date=None):
    y = np.log(M[target]); X = pd.DataFrame(feats); d = pd.concat([y.rename("y"), X], axis=1).dropna()
    P0_date = P0_date or str(M[target].dropna().index[-1].date())   # latest month with a price (current month = daily average so far)
    dd = DAILY[target]; yo = np.log(dd.resample("MS").last()).reindex(d.index).fillna(d.y); P0_day = str(dd.index[-1].date())   # origin = last daily price of the month (end-of-month information)
    m, pred, fitted = fit(d); fv_in = np.exp(fitted); act = np.exp(d.y); r2 = 1 - ((d.y - fitted) ** 2).sum() / ((d.y - d.y.mean()) ** 2).sum()
    coef = {LABELS[k]: round(float(v), 3) for k, v in zip(list(X.columns), m.params[1:])}
    wf = {}
    for t in d.index[d.index >= "2020-01-01"]:
        mm, pr, _ = fit(d.loc[:t].iloc[:-1]); wf[t] = float(np.exp(pr(d.loc[[t]].drop(columns="y"))))
    wf = pd.Series(wf); ew = act.reindex(wf.index) - wf
    H = [1, 2, 3, 4, 5, 6]; errs = {h: [] for h in H}; e0 = {}; gapcoef = {}
    for h in H:
        idx = d.index[(d.index >= "2020-01-01") & (d.index <= d.index[-1] - pd.DateOffset(months=h))]
        for t in idx:
            trl = d.loc[:t]; ml, prl, fl = fit(trl); gaps = yo.loc[trl.index] - fl
            g2 = pd.concat([(trl.y.shift(-h) - yo.loc[trl.index]).rename("dy"), gaps.rename("g")], axis=1).dropna(); mg = sm.OLS(g2.dy, sm.add_constant(g2[["g"]], has_constant="add")).fit()
            p = 0.5 * float(mg.params["g"] * gaps.iloc[-1]); errs[h].append(float(d.y.loc[t + pd.DateOffset(months=h)] - yo.loc[t] - p))   # drift-free gap reversion
        e0[h] = [float(d.y.loc[t + pd.DateOffset(months=h)] - yo.loc[t]) for t in idx]
        gaps = yo - fitted; g2 = pd.concat([(d.y.shift(-h) - yo).rename("dy"), gaps.rename("g")], axis=1).dropna(); mg = sm.OLS(g2.dy, sm.add_constant(g2[["g"]], has_constant="add")).fit(); gapcoef[h] = (float(mg.params["const"]), float(mg.params["g"]))
    qs = {h: {q: float(np.quantile(errs[h], q)) for q in [0.05, 0.25, 0.5, 0.75, 0.95]} for h in H}
    P0 = float(dd.iloc[-1]); gap_now = float(np.log(P0) - fitted.iloc[-1]); P0_month = float(M[target].loc[P0_date]); fv_now = float(np.exp(fitted.iloc[-1]))   # origin = latest daily price vs latest fair value
    # drift-free: centre the error quantiles on their median; median path = gap reversion only
    curve = CURVES.get(target, []); cdates = [pd.Timestamp(c["date"]) for c in curve]; cprice = [c["price"] for c in curve]
    def curve_at(dt):
        if not curve: return None
        if dt <= cdates[0]: return cprice[0]
        for i in range(1, len(cdates)):
            if dt <= cdates[i]:
                w = (dt - cdates[i-1]).days / (cdates[i] - cdates[i-1]).days; return cprice[i-1] + w * (cprice[i] - cprice[i-1])
        return cprice[-1]
    fc = []
    for h in H:
        c0, c1 = gapcoef[h]; p = 0.5 * c1 * gap_now; dt = pd.Timestamp(P0_date) + pd.DateOffset(months=h)
        med = P0 * np.exp(p); cv = curve_at(dt); comb = 0.5 * med + 0.5 * cv if cv else med
        q = {k: v - qs[h][0.5] for k, v in qs[h].items()}   # centred
        fc.append(dict(h=h, date=str(dt.date()), median=round(med, 1), curve=(round(cv, 1) if cv else None), comb=round(comb, 1),
                       p25=round(comb * np.exp(q[0.25]), 1), p75=round(comb * np.exp(q[0.75]), 1), p05=round(comb * np.exp(q[0.05]), 1), p95=round(comb * np.exp(q[0.95]), 1)))
    rm = {h: (round(np.sqrt(np.mean(np.square(errs[h]))) * 100, 1), round(np.sqrt(np.mean(np.square(e0[h]))) * 100, 1)) for h in H}
    out = dict(target=target, dates=[str(t.date()) for t in d.index], actual=[round(float(v), 2) for v in act], fv_insample=[round(float(v), 2) for v in fv_in],
               fv_walkforward={str(k.date()): round(v, 2) for k, v in wf.items()}, coef=coef, r2=round(float(r2), 3),
               insample_rmse=round(float(np.sqrt(((act - fv_in) ** 2).mean())), 1), insample_med=round(float((act - fv_in).abs().median()), 1),
               wf_med=round(float(ew.abs().median()), 1), wf_90=round(float(ew.abs().quantile(.9)), 1), wf_max=round(float(ew.abs().max()), 1), forecast=fc, P0=round(P0, 2), P0_date=P0_date[:7], P0_day=P0_day, P0_month=round(P0_month, 2), daily_recent=[dict(date=str(t.date()), price=round(float(v), 2)) for t, v in dd.loc[dd.index >= pd.Timestamp(P0_date) - pd.DateOffset(months=2)].items()],
               fv_now=round(fv_now, 1), gap_pct=round(gap_now * 100, 1), quantiles={h: {str(q): round(v * 100, 1) for q, v in qs[h].items()} for h in H}, rmse_vs_rw=rm)
    print(f"{target}: R2 {r2:.2f} in-sample med ±{out['insample_med']} | wf med ±{out['wf_med']} 90% ±{out['wf_90']} max {out['wf_max']} | fv_now {fv_now:.0f} P0 {P0:.0f} gap {gap_now*100:+.0f}% | rmse model/rw {rm}")
    print("  coef:", coef); print("  1kk", fc[0], "\n  3kk", fc[2], "\n  6kk", fc[5])
    return out

CURVES = {}; CLABEL = {}
try:
    _cn = json.load(open(f"{D}/curves_now.json")); CURVES = {t: _cn[t]["curve"] for t in ["brent", "wti"] if t in _cn}; CLABEL = {t: _cn[t]["label"] for t in CURVES}
except Exception as e: print("no curves_now.json", e)
if not CURVES:
    try:
        _pg = json.load(open(f"{D}/page_data.json")); CURVES = {t: _pg["model"][t]["curve"] for t in ["brent", "wti"] if t in _pg.get("model", {}) and "curve" in _pg["model"][t]}; CLABEL = {t: _pg["model"][t].get("curve_label", "") for t in CURVES}
    except Exception as e: print("no curves", e)
models = {"brent": build("brent", BASE), "wti": build("wti", {**BASE, **WTI_EXTRA}), "wti_base": build("wti", BASE)}
for t in ["brent", "wti"]:
    models[t]["curve"] = CURVES.get(t, []); models[t]["curve_label"] = CLABEL.get(t, "futuurikäyrä")
pg["model"] = {"brent": models["brent"], "wti": models["wti"]}
json.dump(pg, open(f"{D}/page_data.json", "w"), ensure_ascii=False); json.dump(models, open(f"{D}/model.json", "w"))

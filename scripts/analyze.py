#!/usr/bin/env python3
"""Correlation / lead-lag / rolling / predictive analysis on the monthly panel. Writes data/analysis.json."""
import json, numpy as np, pandas as pd, warnings
from scipy import stats
import statsmodels.api as sm
from statsmodels.tsa.stattools import grangercausalitytests
warnings.filterwarnings("ignore")
D = "/home/claude/oil/data"
M = pd.read_csv(f"{D}/panel_monthly.csv", index_col=0, parse_dates=True)
META = json.load(open(f"{D}/series_meta.json"))["monthly"]
A = pd.read_csv(f"{D}/panel_annual.csv", index_col=0)
AMETA = json.load(open(f"{D}/series_meta.json"))["annual"]

DIFF = {"brent_wti_spread", "dubai_brent_spread", "us_crude_stock_chg", "world_stock_draw", "world_balance", "fedfunds", "ust10y",
        "unemp_us", "temp_global", "temp_nh", "mm_net_wti", "wind_share_us", "us_ref_util"}
def changes(df):
    out = {}
    for c in df.columns:
        s = df[c]
        if c in DIFF or (s.dropna() <= 0).any(): out[c] = s.diff()
        else: out[c] = np.log(s).diff()
    return pd.DataFrame(out)
C = changes(M)
R = {}

# 1. Level & change correlations vs Brent (full sample)
def corr_table(target, frame, minn=36):
    rows = []
    for c in frame.columns:
        if c == target: continue
        x = frame[[target, c]].dropna()
        if len(x) < minn: continue
        r, p = stats.pearsonr(x[target], x[c]); rho, _ = stats.spearmanr(x[target], x[c])
        rows.append(dict(series=c, label=META[c]["label"], group=META[c]["group"], n=len(x), r=round(r, 3), p=round(p, 4), spearman=round(rho, 3)))
    return sorted(rows, key=lambda d: -abs(d["r"]))
R["level_corr_vs_brent"] = corr_table("brent", M)
R["change_corr_vs_brent"] = corr_table("brent", C)

# 2. Sub-period change correlations
periods = {"2015-2019": ("2015-01", "2019-12"), "2020-2021 (COVID)": ("2020-01", "2021-12"), "2022-2025": ("2022-01", "2025-12"), "2026 (Hormuz)": ("2026-01", pd.Timestamp.today().strftime("%Y-%m"))}
sub = {}
for name, (a, b) in periods.items():
    sub[name] = {d["series"]: d["r"] for d in corr_table("brent", C.loc[a:b], minn=8)}
R["subperiod_change_corr"] = sub

# 3. Lead-lag cross-correlations: corr(ΔX_{t-k}, r_brent_t), k=-12..12 (k>0 → X leads Brent)
ll = {}
rb = C["brent"]
for c in C.columns:
    if c == "brent": continue
    res = {}
    for k in range(-12, 13):
        x = pd.concat([rb, C[c].shift(k)], axis=1).dropna()
        if len(x) >= 48: res[k] = round(x.iloc[:, 0].corr(x.iloc[:, 1]), 3)
    if res:
        best = max(res, key=lambda k: abs(res[k]))
        ll[c] = dict(label=META[c]["label"], group=META[c]["group"], best_lag=best, best_r=res[best], contemporaneous=res.get(0), curve=res)
R["lead_lag"] = ll

# 4. Rolling 24-month correlations of changes for key pairs
roll = {}
for c in ["usd_broad", "sp500", "us_crude_stocks", "copper", "bdi", "mm_net_wti", "vix", "oecd_stocks", "gasoline_us", "cpi_energy_us", "us_rigs", "world_balance", "temp_global"]:
    r = C["brent"].rolling(24, min_periods=18).corr(C[c])
    roll[c] = {str(k)[:7]: (None if pd.isna(v) else round(v, 3)) for k, v in r.items()}
R["rolling24"] = roll

# 5. Granger causality (lags 1-3) for selected pairs, both directions
def granger(x, y, maxlag=3):  # does x Granger-cause y?
    d = pd.concat([C[y], C[x]], axis=1).dropna()
    try:
        g = grangercausalitytests(d.values, maxlag=maxlag)
        return {f"lag{l}": round(g[l][0]["ssr_ftest"][1], 4) for l in range(1, maxlag + 1)}
    except Exception as e:
        return {"error": str(e)}
pairs = [("us_crude_stocks", "brent"), ("oecd_stocks", "brent"), ("world_balance", "brent"), ("mm_net_wti", "brent"), ("usd_broad", "brent"), ("sp500", "brent"),
         ("bdi", "brent"), ("copper", "brent"), ("vix", "brent"), ("us_rigs", "brent"), ("temp_global", "brent"), ("wind_gen_us", "brent"), ("opec_prod", "brent"),
         ("brent", "us_rigs"), ("brent", "gasoline_us"), ("brent", "cpi_energy_us"), ("brent", "cpi_us"), ("brent", "us_prod"), ("brent", "us_crude_stocks"), ("brent", "mm_net_wti"),
         ("brent", "vehicle_sales_us"), ("brent", "ip_drilling"), ("brent", "air_rpm"), ("brent", "sp500"), ("brent", "ust10y"), ("brent", "fedfunds"), ("brent", "us_exports")]
R["granger"] = [dict(cause=x, effect=y, cause_label=META[x]["label"], effect_label=META[y]["label"], p=granger(x, y)) for x, y in pairs]

# 6. Predictive regression: Brent return(t+1) on lagged predictors, expanding window OOS from 2020-01 vs random walk (zero return) and vs AR(1)
preds = ["us_crude_stocks", "mm_net_wti", "usd_broad", "sp500", "bdi", "copper", "us_rigs", "world_balance", "vix"]
X = C[preds].copy(); y = C["brent"].shift(-1)
df = pd.concat([y.rename("y"), X, C["brent"].rename("brent_lag")], axis=1).dropna()
oos_start = pd.Timestamp("2020-01-01")
errs = {"model": [], "rw": [], "ar1": [], "mean": []}
for t in df.index[df.index >= oos_start]:
    train = df.loc[:t].iloc[:-1]; test = df.loc[[t]]
    Xtr = sm.add_constant(train.drop(columns="y")); mod = sm.OLS(train["y"], Xtr).fit()
    pred = mod.predict(sm.add_constant(test.drop(columns="y"), has_constant="add")).iloc[0]
    ar = sm.OLS(train["y"], sm.add_constant(train[["brent_lag"]])).fit()
    ar_pred = ar.predict(sm.add_constant(test[["brent_lag"]], has_constant="add")).iloc[0]
    errs["model"].append(test["y"].iloc[0] - pred); errs["rw"].append(test["y"].iloc[0]); errs["ar1"].append(test["y"].iloc[0] - ar_pred); errs["mean"].append(test["y"].iloc[0] - train["y"].mean())
rmse = {k: round(float(np.sqrt(np.mean(np.square(v)))), 4) for k, v in errs.items()}
full = sm.OLS(df["y"], sm.add_constant(df.drop(columns="y"))).fit()
R["predictive"] = dict(predictors=preds + ["brent_lag"], oos_from="2020-01", n_oos=len(errs["model"]), rmse_monthly_logret=rmse,
                       insample_r2=round(full.rsquared, 3), insample_adj_r2=round(full.rsquared_adj, 3),
                       coef={k: dict(coef=round(v, 4), p=round(full.pvalues[k], 3)) for k, v in full.params.items()})
# directional accuracy
sign_model = np.mean([(df.loc[t, "y"] > 0) == ((df.loc[t, "y"] - e) > 0) for t, e in zip(df.index[df.index >= oos_start], errs["model"])])
R["predictive"]["directional_accuracy_model"] = round(float(sign_model), 3)

# 7. Inventory-price curve (Ye–Zyren–Shore style): Brent level vs OECD stocks deviation from 36m trailing mean; and vs US stocks days-of-supply proxy
oecd_dev = M["oecd_stocks"] - M["oecd_stocks"].rolling(36, min_periods=24).mean()
d = pd.concat([M["brent"], oecd_dev.rename("oecd_dev")], axis=1).dropna()
m1 = sm.OLS(np.log(d["brent"]), sm.add_constant(d["oecd_dev"])).fit()
R["inventory_curve"] = dict(n=len(d), r=round(d["brent"].corr(d["oecd_dev"]), 3), r2_log=round(m1.rsquared, 3), slope_pct_per_10mb=round(float(m1.params["oecd_dev"] * 10 * 100), 2))
us_dev = M["us_crude_stocks"] - M["us_crude_stocks"].rolling(36, min_periods=24).mean()
d2 = pd.concat([M["brent"], us_dev.rename("us_dev")], axis=1).dropna()
R["inventory_curve_us"] = dict(n=len(d2), r=round(d2["brent"].corr(d2["us_dev"]), 3))
# excluding 2026
d3 = d.loc[:"2025-12"]; R["inventory_curve"]["r_excl_2026"] = round(d3["brent"].corr(d3["oecd_dev"]), 3)
d4 = d2.loc[:"2025-12"]; R["inventory_curve_us"]["r_excl_2026"] = round(d4["brent"].corr(d4["us_dev"]), 3)

# 8. Annual correlations (n small!) vs Brent annual average
ann = []
for c in A.columns:
    if c == "brent_avg": continue
    x = A[["brent_avg", c]].dropna()
    if len(x) < 6: continue
    r, p = stats.pearsonr(x["brent_avg"], x[c])
    # also on yoy changes
    xd = A[["brent_avg", c]].pct_change().dropna() if (A[c].dropna() > 0).all() else A[["brent_avg", c]].diff().dropna()
    rd = xd["brent_avg"].corr(xd[c]) if len(xd) >= 5 else None
    ann.append(dict(series=c, label=AMETA[c]["label"], n=len(x), r_level=round(r, 3), p_level=round(p, 3), r_change=(None if rd is None or pd.isna(rd) else round(rd, 3)), n_change=len(xd)))
R["annual_corr_vs_brent"] = sorted(ann, key=lambda d: -abs(d["r_level"]))

# 9. Full change-correlation matrix for a core set (for the page)
core = ["brent", "wti", "dubai", "gasoline_us", "diesel_us", "us_crude_stocks", "oecd_stocks", "world_balance", "opec_prod", "us_prod", "us_rigs", "mm_net_wti", "usd_broad", "sp500", "vix",
        "copper", "metals_idx", "food_idx", "cpi_energy_us", "bdi", "freight_fbx", "air_rpm", "vmt", "ip_total", "vehicle_sales_us", "temp_global", "wind_gen_us", "fedfunds", "ust10y"]
cm = C[core].corr(min_periods=36)
R["change_corr_matrix"] = dict(keys=core, labels=[META[k]["label"] for k in core], matrix=[[None if pd.isna(v) else round(v, 2) for v in row] for row in cm.values])
lm = M[core].corr(min_periods=36)
R["level_corr_matrix"] = dict(keys=core, labels=[META[k]["label"] for k in core], matrix=[[None if pd.isna(v) else round(v, 2) for v in row] for row in lm.values])

# 10. Simple stats
R["stats"] = {}
for k in ["brent", "wti", "dubai", "brent_wti_spread", "dubai_brent_spread", "gasoline_us", "diesel_us", "us_spr", "oecd_stocks", "bdi", "freight_fbx", "mm_net_wti"]:
    s = M[k].dropna()
    R["stats"][k] = dict(label=META[k]["label"], min=round(s.min(), 2), min_date=str(s.idxmin())[:7], max=round(s.max(), 2), max_date=str(s.idxmax())[:7], last=round(s.iloc[-1], 2), last_date=str(s.index[-1])[:7], mean=round(s.mean(), 2))
json.dump(R, open(f"{D}/analysis.json", "w"), ensure_ascii=False, indent=1, default=float)

# ---- print summary ----
print("=== LEVEL corr vs Brent (top 25) ===")
for d in R["level_corr_vs_brent"][:25]: print(f"{d['r']:+.2f} (sp {d['spearman']:+.2f}, n={d['n']}) {d['label']}")
print("=== CHANGE corr vs Brent (top 25) ===")
for d in R["change_corr_vs_brent"][:25]: print(f"{d['r']:+.2f} (p={d['p']}, n={d['n']}) {d['label']}")
print("=== lowest change corr ===")
for d in sorted(R["change_corr_vs_brent"], key=lambda d: abs(d["r"]))[:12]: print(f"{d['r']:+.2f} (p={d['p']}) {d['label']}")
print("=== Subperiods (change corr) ===")
for c in ["usd_broad", "sp500", "us_crude_stocks", "oecd_stocks", "copper", "bdi", "mm_net_wti", "vix", "gasoline_us", "world_balance", "opec_prod", "us_rigs"]:
    print(f"{c:18}", {k: v.get(c) for k, v in sub.items()})
print("=== Lead-lag (|r|>0.25 or interesting) ===")
for c, d in sorted(ll.items(), key=lambda kv: -abs(kv[1]["best_r"])):
    if abs(d["best_r"]) >= 0.2: print(f"{d['best_r']:+.2f} @lag {d['best_lag']:+d} (contemp {d['contemporaneous']}) {d['label']}")
print("=== Granger p-values ===")
for g in R["granger"]: print(f"{g['cause']:>18} -> {g['effect']:<18} {g['p']}")
print("=== Predictive ===", json.dumps(R["predictive"], indent=0)[:1500])
print("=== Inventory curve ===", R["inventory_curve"], R["inventory_curve_us"])
print("=== Annual corr vs Brent ===")
for d in R["annual_corr_vs_brent"]: print(f"{d['r_level']:+.2f} (p={d['p_level']}, n={d['n']}) chg {d['r_change']} {d['label']}")
print("=== stats ===")
for k, v in R["stats"].items(): print(v)

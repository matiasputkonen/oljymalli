#!/usr/bin/env python3
"""Dossier integration (23.10.2026): EIA STEO path, end-of-month origin test, Diebold–Mariano / Clark–West tests,
rolling cone coverage, dossier-weighted forecast stack (model 8) and exponential tilting of the options density.
Writes data/models8.json and page_data.json['d8']."""
import json, warnings, numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm
from scipy.optimize import brentq
warnings.filterwarnings("ignore")
D = "/home/claude/oil/data"; RAW = f"{D}/raw"; R3 = f"{D}/raw3"; R4 = f"{D}/raw4"
M = pd.read_csv(f"{D}/panel_monthly.csv", index_col=0, parse_dates=True)
pg = json.load(open(f"{D}/page_data.json")); mj = json.load(open(f"{D}/model.json")); m17 = json.load(open(f"{D}/models17.json"))
OUT = {}
H = [1, 3, 6, 12]
CUR = str(M["wti"].dropna().index[-1].date())[:7]; CUR_MS = pd.Timestamp(CUR + "-01"); TODAY = pd.Timestamp(pd.Timestamp.today().date())

# ============ 0. EIA STEO October 2026 price path ============
x = pd.read_excel(f"{RAW}/STEO_m.xlsx", sheet_name="2tab", header=None)
yrow = x.iloc[2, 2:].tolist(); mrow = x.iloc[3, 2:].tolist(); dates = []; cur = None
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
for y, m in zip(yrow, mrow):
    if isinstance(y, (int, float)) and not pd.isna(y): cur = int(y)
    dates.append(pd.Timestamp(year=cur, month=MON.index(m[:3]) + 1, day=1) if (cur and isinstance(m, str)) else None)
steo = {}
for i in range(x.shape[0]):
    code = str(x.iloc[i, 0]).strip()
    if code in ("WTIPUUS", "BREPUUS"):
        vals = pd.to_numeric(x.iloc[i, 2:2 + len(dates)].values, errors="coerce")
        s = pd.Series([v for v, d in zip(vals, dates) if d is not None], index=[d for d in dates if d is not None]).dropna()
        steo["wti" if code == "WTIPUUS" else "brent"] = s
OUT["steo"] = {t: [{"date": str(d.date()), "price": round(float(v), 1)} for d, v in s.loc[CUR:].items()] for t, s in steo.items()}
OUT["steo_meta"] = {"vintage": str(x.iloc[3, 0]), "label": "EIA STEO " + str(x.iloc[1, 1]).split("-")[-1].strip()}
print("STEO", OUT["steo_meta"], {t: [(e["date"][:7], e["price"]) for e in v[:15]] for t, v in OUT["steo"].items()})

# ============ 1. End-of-month origin vs monthly-average origin (dossier: up to 40 % lower 1-m MSPE) ============
eom = {}
for t in ["wti", "brent"]:
    d = pd.read_csv(f"{RAW}/fred_{'WTI' if t == 'wti' else 'Brent'}_d.csv", parse_dates=["date"]).dropna().set_index("date")["value"].astype(float)
    avg = d.resample("MS").mean(); last = d.resample("MS").last(); last5 = d.resample("MS").apply(lambda s: s.tail(5).mean())
    avg = avg.loc[:CUR_MS - pd.DateOffset(months=1)]; last = last.loc[:CUR_MS - pd.DateOffset(months=1)]; last5 = last5.loc[:CUR_MS - pd.DateOffset(months=1)]   # current month incomplete
    res = {}
    for h in [1, 3, 6, 12]:
        for per, a in [("2015", "2015-01-01"), ("2020", "2020-01-01")]:
            tgt = avg.shift(-h); idx = avg.index[(avg.index >= a) & (~tgt.isna())]
            eA = (tgt - avg).loc[idx]; eB = (tgt - last).loc[idx]; eC = (tgt - last5).loc[idx]
            rm = lambda e: float(np.sqrt(np.mean(np.square(e))))
            res[f"h{h}_{per}"] = dict(rmse_avg=round(rm(eA), 2), rmse_last=round(rm(eB), 2), rmse_last5=round(rm(eC), 2), ratio_last=round(rm(eB) / rm(eA), 3), ratio_last5=round(rm(eC) / rm(eA), 3), n=int(len(idx)),
                                      mae_avg=round(float(eA.abs().median()), 2), mae_last=round(float(eB.abs().median()), 2))
    print(f"{t}: viimeisin päivä {d.index[-1].date()} {d.iloc[-1]:.1f} $, kuukauden ka {d.loc[CUR].mean():.1f} $")
    for k, v in res.items(): print(f"   {k}: RMSE kk-ka {v['rmse_avg']} vs viim. päivä {v['rmse_last']} (suhde {v['ratio_last']}), 5 pv ka {v['rmse_last5']} ({v['ratio_last5']}), n={v['n']}")
    eom[t] = res; eom[t]["last_daily"] = round(float(d.iloc[-1]), 2); eom[t]["last_daily_date"] = str(d.index[-1].date()); eom[t]["oct_avg"] = round(float(d.loc[CUR].mean()), 2)
OUT["eom"] = eom

# ============ 2. Walk-forward gap model: DM / CW tests and rolling coverage ============
S = {s["key"]: s for s in pg["series"]}; dates_pg = pd.to_datetime(pg["dates"])
hz = pd.Series(S["hormuz_tankers"]["values"], index=dates_pg, dtype=float).fillna(50.0)
dev = lambda s: (s - s.rolling(36, min_periods=24).mean()) / 100
BASE = {"oecd_dev": dev(M.oecd_stocks), "opec": np.log(M.opec_prod), "hormuz": np.clip(1 - hz / 50.0, 0, 1), "usd": np.log(M.usd_broad), "cot": M.mm_net_wti / 100, "usstocks": dev(M.us_total_stocks), "sp": np.log(M.sp500)}
WTI_EXTRA = {"cushing_dev": dev(M.cushing * 10) / 10, "uscrude_dev": dev(M.us_crude_stocks), "usprod": np.log(M.us_prod), "spr_dev": dev(M.us_spr)}
def fit(df, alpha=0.0015):
    Xs = df.drop(columns="y"); mu = Xs.mean(); sd = Xs.std().replace(0, 1); Z = (Xs - mu) / sd
    m = sm.OLS(df.y, sm.add_constant(Z, has_constant="add")).fit_regularized(alpha=alpha, L1_wt=0.0)
    def pred(Xn): return float(np.dot(np.r_[1.0, ((Xn - mu) / sd).values.ravel()], m.params))
    return m, pred, pd.Series([pred(Xs.loc[[t]]) for t in Xs.index], index=Xs.index)
def hac_t(d, lags):
    d = np.asarray(d, dtype=float); r = sm.OLS(d, np.ones(len(d))).fit(cov_type="HAC", cov_kwds={"maxlags": max(lags, 1)}); return float(r.tvalues[0])
tests = {}; gapcoef = {}; gapnow = {}; fvnow = {}
for target, feats in [("brent", BASE), ("wti", {**BASE, **WTI_EXTRA})]:
    y = np.log(M[target]); X = pd.DataFrame(feats); d = pd.concat([y.rename("y"), X], axis=1).dropna()
    dd_ = pd.read_csv(f"{RAW}/fred_{'WTI' if target == 'wti' else 'Brent'}_d.csv", parse_dates=["date"]).dropna().set_index("date")["value"].astype(float); yo = np.log(dd_.resample("MS").last()).reindex(d.index).fillna(d.y)   # end-of-month origin, as in model.py
    m, pred, fitted = fit(d); gaps_full = yo - fitted; fvnow[target] = float(np.exp(fitted.iloc[-1])); gapnow[target] = float(gaps_full.iloc[-1])
    gc = {}
    for h in H:
        g2 = pd.concat([(d.y.shift(-h) - yo).rename("dy"), gaps_full.rename("g")], axis=1).dropna(); mg = sm.OLS(g2.dy, sm.add_constant(g2[["g"]], has_constant="add")).fit(); gc[h] = (float(mg.params["const"]), float(mg.params["g"]))
    gapcoef[target] = gc
    tt = {}
    for h in H:
        idx = d.index[(d.index >= "2020-01-01") & (d.index <= d.index[-1] - pd.DateOffset(months=h))]
        rows = []
        for t in idx:
            trl = d.loc[:t]; ml, prl, fl = fit(trl); gaps = yo.loc[trl.index] - fl
            g2 = pd.concat([(trl.y.shift(-h) - yo.loc[trl.index]).rename("dy"), gaps.rename("g")], axis=1).dropna(); mg = sm.OLS(g2.dy, sm.add_constant(g2[["g"]], has_constant="add")).fit()
            p = 0.5 * float(mg.params["g"] * gaps.iloc[-1]); a = float(d.y.loc[t + pd.DateOffset(months=h)] - yo.loc[t])
            rows.append((t, a - p, a, p))
        E = pd.DataFrame(rows, columns=["t", "em", "e0", "p"]).set_index("t")
        dm = hac_t(E.em**2 - E.e0**2, h); cw = hac_t(E.e0**2 - E.em**2 + E.p**2, h)
        # rolling coverage: at origin t use errors whose targets are realised (origins <= t-h), min 12 obs, evaluate from 2022
        cov = {"50_raw": [], "90_raw": [], "50_c": [], "90_c": []}
        for t in E.index[E.index >= "2022-01-01"]:
            past = E.em[E.index <= t - pd.DateOffset(months=h)]
            if len(past) < 12: continue
            q = past.quantile([0.05, 0.25, 0.5, 0.75, 0.95]); e = E.em.loc[t]
            cov["50_raw"].append(q[0.25] <= e <= q[0.75]); cov["90_raw"].append(q[0.05] <= e <= q[0.95])
            cov["50_c"].append(q[0.25] - q[0.5] <= e <= q[0.75] - q[0.5]); cov["90_c"].append(q[0.05] - q[0.5] <= e <= q[0.95] - q[0.5])
        tt[h] = dict(n=int(len(E)), rmse_ratio=round(float(np.sqrt((E.em**2).mean()) / np.sqrt((E.e0**2).mean())), 3), dm_t=round(dm, 2), cw_t=round(cw, 2),
                     dir_acc=round(float(np.mean(np.sign(E.e0) == np.sign(E.p))), 2), cov_n=len(cov["50_raw"]), **{k: (round(float(np.mean(v)), 2) if v else None) for k, v in cov.items()})
        print(f"{target} h={h}: n={len(E)} RMSE-suhde {tt[h]['rmse_ratio']} DM t={dm:+.2f} CW t={cw:+.2f} suunta {tt[h]['dir_acc']:.2f} | peitto (n={len(cov['50_raw'])}) 50 % {tt[h]['50_raw']} / 90 % {tt[h]['90_raw']} (keskitetty {tt[h]['50_c']} / {tt[h]['90_c']})")
    tests[target] = tt
OUT["tests"] = {t: {str(h): v for h, v in tt.items()} for t, tt in tests.items()}

# ============ 3. Dossier-weighted forecast stack (model 8) ============
W = {"nochange": 0.20, "futures": 0.15, "physical": 0.20, "var": 0.15, "midas": 0.10, "nonlinear": 0.10, "options": 0.10}
# curve interpolation (from page_data model curves, 21.10.2026)
def curve_fn(t):
    c = pg["model"][t]["curve"]; cd = [pd.Timestamp(e["date"]) for e in c]; cp = [e["price"] for e in c]
    def f(dt):
        if dt <= cd[0]: return cp[0]
        for i in range(1, len(cd)):
            if dt <= cd[i]: w = (dt - cd[i-1]).days / (cd[i] - cd[i-1]).days; return cp[i-1] + w * (cp[i] - cp[i-1])
        return cp[-1]
    return f
# VAR(6) real-price forecast change (same spec as models17 §7)
from statsmodels.tsa.api import VAR
bdi = pd.read_csv(f"{RAW}/bdi_daily.csv", parse_dates=["date"]).set_index("date")["value"].resample("MS").mean()
cpi = pd.read_csv(f"{RAW}/fred_CPI_US.csv", parse_dates=["date"]).set_index("date")["value"]; cpi.index = cpi.index.to_period("M").to_timestamp()
wp = pd.read_csv(f"{D}/panel_long_2006_2026.csv", index_col=0, parse_dates=True)
V = pd.DataFrame({"supply": np.log(wp.opec_prod).diff(), "activity": np.log(bdi).diff(), "rprice": np.log(wp.brent / cpi.reindex(wp.index) * 100), "dstock": wp.oecd_stocks.diff() / 100}).dropna()
V = V.loc["2006-06":]; V = V.reindex(pd.date_range(V.index.min(), V.index.max(), freq="MS")).interpolate(limit=2).dropna()
vres = VAR(V).fit(6); vfc = vres.forecast(V.values[-6:], 14)[:, 2]
# last observation is September; the anchor is the latest October price, so use the VAR's expected change from October (step 1) to October+h (step 1+h), plus ~3 %/yr inflation
var_dlog = {h: float(vfc[h] - vfc[0]) + 0.0025 * h for h in H}
print("VAR viimeinen havainto", V.index[-1].date(), "reaalihinnan log-muutosennuste lokakuusta", {h: round(v, 3) for h, v in var_dlog.items()})
opt = m17["options"]; ex = sorted(opt.values(), key=lambda v: v["days"]); od = [v["days"] for v in ex]
def opt_q(days, p="0.5"): return float(np.interp(days, od, [v["q"][p] for v in ex]))
def opt_F(days): return float(np.interp(days, od, [v["F"] for v in ex]))
stack = {}
for t in ["wti", "brent"]:
    P_d = float(pg["model"][t]["P0"]); P_m = float(M[t].loc[CUR_MS]); cf = curve_fn(t); cw = curve_fn("wti"); wk = m17["weekly"][t]; qn = m17["quantile"][t]["horizons"]   # anchor = same as the page model (WTI: front contract latest close)
    gap_d = float(np.log(P_d) - np.log(fvnow[t])); gap_w = float(np.log(wk["actual_last"] / wk["fv_last"]))
    rows = {}
    for h in H:
        dt = CUR_MS + pd.DateOffset(months=h); days = max(1, (dt + pd.Timedelta(days=15) - TODAY).days)
        c0, c1 = gapcoef[t][h]
        mem = {"nochange": P_d, "futures": cf(dt), "physical": P_d * np.exp(0.5 * c1 * gap_d), "var": P_d * np.exp(var_dlog[h]), "midas": P_d * np.exp(0.5 * c1 * gap_w)}
        if str(h) in qn: mem["nonlinear"] = float(qn[str(h)]["cond"]["0.5"]) * P_d / P_m
        mem["options"] = opt_q(days) if t == "wti" else opt_q(days) * cf(dt) / cw(dt)
        ws = {k: W[k] for k in mem}; tot = sum(ws.values()); st = sum(mem[k] * ws[k] for k in mem) / tot
        vals = np.array(list(mem.values()))
        rows[str(h)] = dict(date=str(dt.date()), members={k: round(float(v), 1) for k, v in mem.items()}, weights={k: round(ws[k] / tot, 3) for k in mem}, stack=round(float(st), 1), disagreement=round(float(vals.std()), 1), lo=round(float(vals.min()), 1), hi=round(float(vals.max()), 1),
                            steo=(round(float(steo[t].get(dt, np.nan)), 1) if dt in steo[t].index else None))
        print(f"{t} h={h} ({dt.date()}): pino {st:.1f} $ | " + " ".join(f"{k}={v:.0f}" for k, v in mem.items()) + f" | hajonta {vals.std():.1f} | STEO {rows[str(h)]['steo']}")
    stack[t] = dict(anchor=P_d, anchor_date=pg["model"][t].get("P0_day", eom[t]["last_daily_date"]), month_avg=P_m, fv_now=round(fvnow[t], 1), gap_daily_pct=round(gap_d * 100, 1), gap_weekly_pct=round(gap_w * 100, 1), gapcoef={str(h): [round(a, 4), round(b, 4)] for h, (a, b) in gapcoef[t].items()}, horizons=rows)
OUT["stack"] = stack; OUT["weights"] = W

# ============ 4. Exponential tilting of the WTI options density to a physical measure ============
OPT = json.load(open(f"{D}/curves_now.json"))["options"]
rows = [l.strip().split("|") for l in open(OPT["file"]) if l.strip()]
op = pd.DataFrame(rows, columns=["exp", "type", "K", "px", "oi"]); op["K"] = op.K.astype(float); op["px"] = op.px.astype(float)
EXP = {k: v for k, v in OPT["expiries"].items() if k in m17["options"]}; t0 = pd.Timestamp(OPT["date"]); r = 0.04
def black76(F, K, T, sig, call=True):
    d1 = (np.log(F / K) + 0.5 * sig**2 * T) / (sig * np.sqrt(T)); d2 = d1 - sig * np.sqrt(T)
    return np.exp(-r * T) * ((F * norm.cdf(d1) - K * norm.cdf(d2)) if call else (K * norm.cdf(-d2) - F * norm.cdf(-d1)))
def iv(price, F, K, T, call):
    try: return brentq(lambda s: black76(F, K, T, s, call) - price, 0.01, 4.0)
    except Exception: return np.nan
tilt = {}
sh = stack["wti"]["horizons"]; sdays = [(pd.Timestamp(v["date"]) + pd.Timedelta(days=15) - t0).days for v in sh.values()]; svals = [v["stack"] for v in sh.values()]
for e, expd in EXP.items():
    d = op[op.exp == e]; T = (pd.Timestamp(expd) - t0).days / 365.0
    C = d[d.type == "C"].set_index("K").px; P = d[d.type == "P"].set_index("K").px; both = C.index.intersection(P.index); F0 = float(json.load(open(f"{D}/curves_now.json"))["wti"]["curve"][0]["price"]); near = both[(both > 0.6 * F0) & (both < 1.4 * F0)]
    F = float(np.median([(C[k] - P[k]) * np.exp(r * T) + k for k in near]))
    pts = [(k, iv(C[k], F, k, T, True)) for k in C.index if k >= F] + [(k, iv(P[k], F, k, T, False)) for k in P.index if k < F]
    pts = pd.DataFrame(pts, columns=["K", "iv"]).dropna(); pts = pts[(pts.iv > 0.05) & (pts.iv < 3)]
    xk = np.log(pts.K / F); w = np.ones(len(pts)); w[(pts.K > 0.6 * F) & (pts.K < 1.6 * F)] = 3.0; coef = np.polyfit(xk, pts.iv, 4, w=w)
    Kg = np.linspace(20, 260, 2401); xg = np.log(Kg / F); ivg = np.clip(np.polyval(coef, xg), 0.08, 3.0); lo, hi = xk.min(), xk.max(); ivg[xg < lo] = np.polyval(coef, lo); ivg[xg > hi] = np.polyval(coef, hi)
    Cg = black76(F, Kg, T, ivg, True); q = np.clip(np.gradient(np.gradient(Cg, Kg), Kg) * np.exp(r * T), 0, None); q /= np.trapezoid(q, Kg)
    mean_q = float(np.trapezoid(Kg * q, Kg)); target = float(np.interp(int(T * 365), sdays, svals))
    def tilted(lam):   # log-space tilt p ∝ q · K^λ: shifts a lognormal's location without inflating its tails
        p = q * np.exp(lam * np.log(Kg / F)); return p / np.trapezoid(p, Kg)
    lam = brentq(lambda l: np.trapezoid(Kg * tilted(l), Kg) - target, -20, 20); p = tilted(lam)
    cdf = np.cumsum(p) * (Kg[1] - Kg[0]); cdf /= cdf[-1]; qq = {str(pp): round(float(np.interp(pp, cdf, Kg)), 1) for pp in [0.05, 0.25, 0.5, 0.75, 0.95]}
    pr = lambda a, b: round(float(np.interp(b, Kg, cdf) - np.interp(a, Kg, cdf)), 3)
    tilt[e] = dict(expiry=expd, days=int(T * 365), rn_mean=round(mean_q, 1), target_mean=round(target, 1), lam=round(lam, 3), q=qq, p_below_80=pr(0, 80), p_above_120=pr(120, 400), p_above_150=pr(150, 400))
    print(f"tilt {e}: RN-keskiarvo {mean_q:.1f} → tavoite {target:.1f} (λ={lam:+.3f}); kvantiilit " + "/".join(str(v) for v in qq.values()) + f"; P(<80) {pr(0,80)*100:.0f} % P(>120) {pr(120,400)*100:.0f} %")
OUT["tilt"] = tilt
json.dump(OUT, open(f"{D}/models8.json", "w"), default=float)
pg["d8"] = OUT; json.dump(pg, open(f"{D}/page_data.json", "w"), ensure_ascii=False, default=float)
print("saved")

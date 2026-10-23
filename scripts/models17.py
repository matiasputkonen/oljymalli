#!/usr/bin/env python3
"""Models 1-7: options-implied density, Hormuz scenario tree, regime switching, Kalman TVP, quantile cone, weekly nowcast, SVAR.
Writes data/models17.json and prints a summary."""
import json, warnings, numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm
from scipy.optimize import brentq, minimize
warnings.filterwarnings("ignore")
D = "/home/claude/oil/data"; R3 = f"{D}/raw3"; R4 = f"{D}/raw4"
OUT = {}
M = pd.read_csv(f"{D}/panel_monthly.csv", index_col=0, parse_dates=True)
L = pd.read_csv(f"{D}/panel_long_2006_2026.csv", index_col=0, parse_dates=True)
mj = json.load(open(f"{D}/model.json"))
pg = json.load(open(f"{D}/page_data.json"))

# ============ 1. OPTIONS-IMPLIED DISTRIBUTION (WTI, CME settlements 22.10.2026) ============
print("=== 1. OPTIOISTA JOHDETTU JAKAUMA (WTI, CME 22.10.2026) ===")
CN = json.load(open(f"{D}/curves_now.json")); OPT = CN["options"]; TODAY = pd.Timestamp(pd.Timestamp.today().date())
rows = [l.strip().split("|") for l in open(OPT["file"]) if l.strip()]
op = pd.DataFrame(rows, columns=["exp", "type", "K", "px", "oi"]); op["K"] = op.K.astype(float); op["px"] = op.px.astype(float); op["oi"] = op.oi.astype(float)
EXP = {k: (v, "") for k, v in OPT["expiries"].items() if (pd.Timestamp(v) - pd.Timestamp(OPT["date"])).days >= 20 and len(op[op.exp == k]) >= 20}
t0 = pd.Timestamp(OPT["date"]); r = 0.04; OUT["options_meta"] = dict(date=OPT["date"], source=OPT.get("source", ""))
def black76(F, K, T, sig, call=True):
    d1 = (np.log(F / K) + 0.5 * sig**2 * T) / (sig * np.sqrt(T)); d2 = d1 - sig * np.sqrt(T)
    return np.exp(-r * T) * ((F * norm.cdf(d1) - K * norm.cdf(d2)) if call else (K * norm.cdf(-d2) - F * norm.cdf(-d1)))
def iv(price, F, K, T, call):
    try: return brentq(lambda s: black76(F, K, T, s, call) - price, 0.01, 4.0)
    except Exception: return np.nan
opt_res = {}
for e, (expd, und) in EXP.items():
    d = op[op.exp == e]; T = (pd.Timestamp(expd) - t0).days / 365.0
    C = d[d.type == "C"].set_index("K").px; P = d[d.type == "P"].set_index("K").px
    both = C.index.intersection(P.index); parity = (C[both] - P[both]) * np.exp(r * T) + both.values  # F = C-P (undiscounted) + K
    F0 = float(CN["wti"]["curve"][0]["price"]); near = both[(both > 0.6 * F0) & (both < 1.4 * F0)]; F = float(np.median([(C[k] - P[k]) * np.exp(r * T) + k for k in near]))
    # implied vols from OTM options
    pts = []
    for k in C.index:
        if k >= F: s = iv(C[k], F, k, T, True); pts.append((k, s, "C"))
    for k in P.index:
        if k < F: s = iv(P[k], F, k, T, False); pts.append((k, s, "P"))
    pts = pd.DataFrame(pts, columns=["K", "iv", "src"]).dropna(); pts = pts[(pts.iv > 0.05) & (pts.iv < 3)]
    x = np.log(pts.K / F); w = np.ones(len(pts)); w[(pts.K > 0.6 * F) & (pts.K < 1.6 * F)] = 3.0
    coef = np.polyfit(x, pts.iv, 4, w=w)
    Kg = np.linspace(20, 260, 2401); xg = np.log(Kg / F); ivg = np.clip(np.polyval(coef, xg), 0.08, 3.0)
    # extrapolate flat beyond observed range
    lo, hi = x.min(), x.max(); ivg[xg < lo] = np.polyval(coef, lo); ivg[xg > hi] = np.polyval(coef, hi)
    Cg = black76(F, Kg, T, ivg, True); dens = np.gradient(np.gradient(Cg, Kg), Kg) * np.exp(r * T); dens = np.clip(dens, 0, None); dens /= np.trapezoid(dens, Kg)
    cdf = np.cumsum(dens) * (Kg[1] - Kg[0]); cdf /= cdf[-1]
    q = {p: float(np.interp(p, cdf, Kg)) for p in [0.05, 0.25, 0.5, 0.75, 0.95]}
    pr = lambda a, b: float(np.interp(b, Kg, cdf) - np.interp(a, Kg, cdf))
    mean = float(np.trapezoid(Kg * dens, Kg)); atm = float(np.polyval(coef, 0.0))
    skew = float(np.polyval(coef, np.log(0.9)) - np.polyval(coef, np.log(1.1)))  # 90% put iv - 110% call iv
    opt_res[e] = dict(expiry=expd, days=int(T * 365), F=round(F, 2), atm_iv=round(atm, 3), skew_90_110=round(skew, 3), mean=round(mean, 1), q=q, p_below_70=round(pr(0, 70), 3), p_below_80=round(pr(0, 80), 3), p_above_120=round(pr(120, 400), 3), p_above_150=round(pr(150, 400), 3), n_iv=int(len(pts)))
    print(f"  {e} ({expd}, {int(T*365)} pv): F={F:.1f} ATM-vol {atm*100:.0f} % vinous(90p−110c) {skew*100:+.1f} %-yks | kvantiilit 5/25/50/75/95: " + "/".join(f"{q[p]:.0f}" for p in [0.05, 0.25, 0.5, 0.75, 0.95]) + f" | P(<80) {pr(0,80)*100:.0f} % P(>120) {pr(120,400)*100:.0f} % P(>150) {pr(150,400)*100:.0f} %")
OUT["options"] = opt_res

# ============ 2. HORMUZ SCENARIO TREE ============
print("\n=== 2. HORMUZ-SKENAARIOPUU ===")
CURM = pd.Timestamp(CN["wti"]["date"]).replace(day=1)
def curve_series(prod):   # months from the current month, from curves_now.json (Yahoo contracts)
    c = CN["brent" if prod == "BZ" else "wti"]["curve"]; s = pd.Series({(pd.Timestamp(e["date"]).year - CURM.year) * 12 + pd.Timestamp(e["date"]).month - CURM.month: float(e["price"]) for e in c})
    return s[s.index >= 1].sort_index()
scen = {}
for tgt, P_open_lr, curve in [("brent", 76.0, curve_series("BZ")), ("wti", 73.0, curve_series("CL"))]:
    P_closed = float(curve.iloc[0]); H = 30; hl = 4.0  # half-life (months) of convergence to open-level after reopening (stock rebuild)
    def exp_path(h):  # h = monthly hazard of reopening; returns E[P_m] for m=1..H
        surv = (1 - h) ** np.arange(0, H + 1)  # P(still closed at start of month m)
        E = []
        for m in range(1, H + 1):
            # reopened at month j<=m with prob surv[j-1]*h ; price then = open_lr + (P_closed-open_lr)*0.5**((m-j)/hl)
            val = surv[m] * P_closed
            for j in range(1, m + 1):
                pj = surv[j - 1] * h; val += pj * (P_open_lr + (P_closed - P_open_lr) * 0.5 ** ((m - j) / hl))
            E.append(val)
        return np.array(E)
    ms = [m for m in curve.index if 1 <= m <= 26]
    obj = lambda h: np.sum((exp_path(h[0])[np.array(ms) - 1] - curve.loc[ms].values) ** 2)
    best = min([(obj([h]), h) for h in np.linspace(0.01, 0.6, 60)])[1]
    E = exp_path(best); surv = (1 - best) ** np.arange(0, H + 1)
    cum = {m: round(float(1 - surv[m]), 3) for m in [1, 3, 6, 12, 24]}
    scen[tgt] = dict(hazard=round(best, 3), expected_months=round(1 / best, 1), cum_open=cum, P_closed=P_closed, P_open_lr=P_open_lr, path={m: round(float(E[m - 1]), 1) for m in [1, 3, 6, 12, 24]}, curve={int(m): float(curve.loc[m]) for m in ms})
    print(f"  {tgt}: kalibroitu hasardi {best*100:.1f} %/kk (odotettu kesto {1/best:.0f} kk); kumulatiivinen P(auki): 3 kk {cum[3]*100:.0f} %, 6 kk {cum[6]*100:.0f} %, 12 kk {cum[12]*100:.0f} %, 24 kk {cum[24]*100:.0f} % | odotuspolku 3/6/12 kk {E[2]:.0f}/{E[5]:.0f}/{E[11]:.0f} $ vs käyrä {curve.get(3,np.nan):.0f}/{curve.get(6,np.nan):.0f}/{curve.get(12,np.nan):.0f} $")
OUT["scenario"] = scen

# ============ 3. REGIME SWITCHING (2006→) ============
print("\n=== 3. REGIIMIT (Markov-switching, 2006→) ===")
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
rb = np.log(L.brent).diff(); rsp = np.log(L.sp500).diff(); rusd = np.log(L.usd_broad).diff()
dd = pd.concat([rb.rename("y"), rsp.rename("sp"), rusd.rename("usd")], axis=1).dropna()
try:
    ms = None
    for kw in [dict(switching_variance=True), dict(switching_variance=False)]:
        try:
            ms = MarkovRegression(dd.y.values * 100, k_regimes=2, exog=dd[["sp", "usd"]].values * 100, **kw).fit(search_reps=50, disp=False); break
        except Exception as e2: print("  MS retry:", e2)
    if ms is None: raise RuntimeError("MS failed")
    probs = pd.Series(ms.smoothed_marginal_probabilities[:, 0], index=dd.index)
    p = np.asarray(ms.params); names = list(ms.model.param_names)
    reg = {n: round(float(v), 3) for n, v in zip(names, p)}
    # identify which regime has the higher S&P beta
    b0 = reg.get("x1[0]", 0); b1 = reg.get("x1[1]", 0); dem = 0 if b0 > b1 else 1
    pdem = probs if dem == 0 else 1 - probs
    OUT["regime"] = dict(params=reg, demand_regime_index=dem, p_demand={str(k.date())[:7]: round(float(v), 2) for k, v in pdem.loc["2019":].items()}, expected_durations=[round(float(x), 1) for x in ms.expected_durations])
    print("  parametrit:", reg); print("  odotetut kestot (kk):", [round(float(x), 1) for x in ms.expected_durations])
    print("  P(kysyntäregiimi) 2026:", {str(k.date())[:7]: round(float(v), 2) for k, v in pdem.loc["2026"].items()})
    print("  P(kysyntäregiimi) keskiarvo 2006-19 %.2f, 2020-21 %.2f, 2022-25 %.2f" % (pdem.loc[:"2019"].mean(), pdem.loc["2020":"2021"].mean(), pdem.loc["2022":"2025"].mean()))
except Exception as e:
    print("  MS fail:", e); OUT["regime"] = {"error": str(e)}
# regime-conditional fair value (regime = sign of rolling 12m corr oil vs S&P)
dev = lambda s: (s - s.rolling(36, min_periods=24).mean()) / 100
XL = pd.DataFrame({"oecd_dev": dev(L.oecd_stocks), "opec": np.log(L.opec_prod), "hormuz": L.hormuz_disr, "usd": np.log(L.usd_broad), "cot": L.noncomm_net / 100, "usstocks": dev(L.us_total_stocks), "sp": np.log(L.sp500)})
corr12 = rb.rolling(12).corr(rsp); regime = (corr12 > 0).astype(int)  # 1 = demand regime
def fit(df, alpha=0.0015):
    Xs = df.drop(columns="y"); mu = Xs.mean(); sd = Xs.std().replace(0, 1); Z = (Xs - mu) / sd
    m = sm.OLS(df.y, sm.add_constant(Z, has_constant="add")).fit_regularized(alpha=alpha, L1_wt=0.0)
    return lambda Xn: float(np.dot(np.r_[1.0, ((Xn - mu) / sd).values.ravel()], m.params)), m
for tgt in ["brent", "wti"]:
    y = np.log(L[tgt]); d = pd.concat([y.rename("y"), XL, regime.rename("reg")], axis=1).dropna()
    errs_pool, errs_reg = [], []
    for t in d.index[d.index >= "2020-01-01"]:
        tr = d.loc[:t].iloc[:-1]; cur = d.loc[[t]]
        pp, _ = fit(tr.drop(columns="reg")); e_pool = float(np.exp(d.y.loc[t]) - np.exp(pp(cur.drop(columns=["y", "reg"]))))
        trr = tr[tr.reg == int(cur.reg.iloc[0])]
        if len(trr) >= 48: pr_, _ = fit(trr.drop(columns="reg")); e_reg = float(np.exp(d.y.loc[t]) - np.exp(pr_(cur.drop(columns=["y", "reg"]))))
        else: e_reg = e_pool
        errs_pool.append(e_pool); errs_reg.append(e_reg)
    ep, er = np.abs(errs_pool), np.abs(errs_reg)
    OUT.setdefault("regime_fv", {})[tgt] = dict(pooled_med=round(float(np.median(ep)), 1), pooled_90=round(float(np.quantile(ep, .9)), 1), regime_med=round(float(np.median(er)), 1), regime_90=round(float(np.quantile(er, .9)), 1), share_demand_2026=round(float(regime.loc["2026"].mean()), 2))
    print(f"  {tgt} walk-forward 2020→: yhteinen malli med ±{np.median(ep):.1f} $ (90 % ±{np.quantile(ep,.9):.1f}) | regiimikohtainen med ±{np.median(er):.1f} $ (90 % ±{np.quantile(er,.9):.1f}); 2026 kysyntäregiimissä {regime.loc['2026'].mean()*100:.0f} % kuukausista")

# ============ 4. KALMAN TVP REGRESSION ============
print("\n=== 4. KALMAN (ajassa muuttuvat kertoimet) ===")
def tvp_kalman(y, X, q, R_var):
    n, k = X.shape; beta = np.zeros(k); Pm = np.eye(k) * 1.0; preds = np.full(n, np.nan); betas = np.zeros((n, k))
    for t in range(n):
        Pm = Pm + np.eye(k) * q  # predict
        preds[t] = X[t] @ beta
        S = X[t] @ Pm @ X[t] + R_var; Kg = Pm @ X[t] / S
        beta = beta + Kg * (y[t] - preds[t]); Pm = Pm - np.outer(Kg, X[t]) @ Pm; betas[t] = beta
    return preds, betas
for tgt in ["brent", "wti"]:
    y = np.log(L[tgt]); d = pd.concat([y.rename("y"), XL], axis=1).dropna()
    Xs = d.drop(columns="y"); Z = ((Xs - Xs.mean()) / Xs.std()).values; Z = np.c_[np.ones(len(Z)), Z]; yv = d.y.values
    best = None
    for q in [1e-5, 3e-5, 1e-4, 3e-4, 1e-3]:
        preds, betas = tvp_kalman(yv, Z, q, 0.01)
        e = np.exp(yv) - np.exp(preds); ev = e[d.index >= "2012-01-01"]
        sc = float(np.median(np.abs(ev)))
        if best is None or sc < best[0]: best = (sc, q, preds, betas, e)
    sc, q, preds, betas, e = best; e20 = e[d.index >= "2020-01-01"]
    OUT.setdefault("kalman", {})[tgt] = dict(q=q, med_2012=round(sc, 1), med_2020=round(float(np.median(np.abs(e20))), 1), p90_2020=round(float(np.quantile(np.abs(e20), .9)), 1), fv_now=round(float(np.exp(preds[-1])), 1),
                                            beta_now={c: round(float(b), 3) for c, b in zip(["const"] + list(Xs.columns), betas[-1])}, beta_path={str(k.date())[:7]: round(float(b), 3) for k, b in zip(d.index[::12], betas[::12, 1])})
    print(f"  {tgt}: q={q}; yhden askeleen fair value -virhe 2012→ med ±{sc:.1f} $, 2020→ med ±{np.median(np.abs(e20)):.1f} $ (90 % ±{np.quantile(np.abs(e20),.9):.1f}); fair value nyt {np.exp(preds[-1]):.0f} $; OECD-varastokerroin 2008 {betas[24,1]:+.3f} → 2016 {betas[120,1]:+.3f} → nyt {betas[-1,1]:+.3f}")

# ============ 5. QUANTILE REGRESSION CONE ============
print("\n=== 5. KVANTIILIREGRESSIO (tilariippuva kartio) ===")
ovx = pd.read_csv(f"{R3}/fred_OVX.csv"); ovx["date"] = pd.to_datetime(ovx.iloc[:, 0]); ovx["v"] = pd.to_numeric(ovx.iloc[:, 1], errors="coerce"); ovx = ovx.set_index("date")["v"].resample("MS").mean()
gpr = pd.read_excel(f"{R3}/gpr.xls"); gpr["date"] = pd.to_datetime(gpr["month"]); gpr = gpr.set_index("date")["GPR"]
qr_in = pd.DataFrame({"ovx": np.log(ovx), "gpr": np.log(gpr), "cot": L.noncomm_net / 100}).reindex(L.index)
qr_res = {}
for tgt in ["brent", "wti"]:
    y = np.log(L[tgt]); gap = y - pd.Series(tvp_kalman(y.reindex(XL.dropna().index).values, np.c_[np.ones(len(XL.dropna())), ((XL.dropna() - XL.dropna().mean()) / XL.dropna().std()).values], 1e-4, 0.01)[0], index=XL.dropna().index)
    res_h = {}
    for h in [1, 3, 6]:
        fwd = (y.shift(-h) - y).rename("y")
        d = pd.concat([fwd, qr_in, gap.rename("gap")], axis=1).dropna()
        now = pd.concat([qr_in, gap.rename("gap")], axis=1).dropna().iloc[-1]
        qs = {}
        for p in [0.05, 0.25, 0.5, 0.75, 0.95]:
            m = sm.QuantReg(d.y, sm.add_constant(d[["ovx", "gpr", "cot", "gap"]])).fit(q=p, max_iter=2000)
            qs[p] = float(m.params["const"] + np.dot(m.params[["ovx", "gpr", "cot", "gap"]].values, now[["ovx", "gpr", "cot", "gap"]].values))
            if p == 0.5 and h == 3: coef_med = {k: round(float(v), 3) for k, v in m.params.items()}
        uncond = {p: float(d.y.quantile(p)) for p in [0.05, 0.25, 0.5, 0.75, 0.95]}
        P0 = float(L[tgt].iloc[-1]) if not np.isnan(L[tgt].iloc[-1]) else float(L[tgt].dropna().iloc[-1])
        res_h[h] = dict(cond={str(p): round(P0 * np.exp(v), 1) for p, v in qs.items()}, uncond={str(p): round(P0 * np.exp(v), 1) for p, v in uncond.items()}, width50_cond=round(P0 * (np.exp(qs[0.75]) - np.exp(qs[0.25])), 1), width50_uncond=round(P0 * (np.exp(uncond[0.75]) - np.exp(uncond[0.25])), 1))
        print(f"  {tgt} {h} kk: tilariippuva 5/25/50/75/95 = " + "/".join(f"{P0*np.exp(qs[p]):.0f}" for p in [0.05, 0.25, 0.5, 0.75, 0.95]) + f" $ (50 % leveys {res_h[h]['width50_cond']:.0f} $) vs ehdoton " + "/".join(f"{P0*np.exp(uncond[p]):.0f}" for p in [0.05, 0.25, 0.5, 0.75, 0.95]) + f" $ (leveys {res_h[h]['width50_uncond']:.0f} $)")
    qr_res[tgt] = dict(horizons=res_h, coef_median_3m=coef_med, state_now={k: round(float(v), 3) for k, v in now.items()})
    print(f"  {tgt} nykytila: OVX {ovx.dropna().iloc[-1]:.0f}, GPR {gpr.dropna().iloc[-1]:.0f} (mediaanin kertoimet 3 kk: {coef_med})")
OUT["quantile"] = qr_res

# ============ 6. WEEKLY NOWCAST (MIDAS-light) ============
print("\n=== 6. VIIKOITTAINEN NOWCAST ===")
RAW = f"{D}/raw"
def eia_w(n): d = pd.read_csv(f"{RAW}/eia_{n}.csv", parse_dates=["date"]).dropna(); return d.set_index("date")["value"].astype(float).resample("W-FRI").last()
def fredd(n): d = pd.read_csv(f"{RAW}/fred_{n}.csv", parse_dates=["date"]); return d.set_index("date")["value"].astype(float).dropna().resample("W-FRI").mean()
W = pd.DataFrame({"brent": fredd("Brent_d"), "wti": fredd("WTI_d"), "usstocks": eia_w("WTTSTUS1w") / 1000, "cushing": eia_w("Cushing_w") / 1000, "spr": eia_w("WCSSTUS1w") / 1000, "usd": fredd("DollarBroad_d"), "sp": fredd("SP500_d")})
cot = pd.read_csv(f"{RAW}/cftc_wti_cot.csv", parse_dates=["date"]).set_index("date")["mm_net"].resample("W-FRI").last() / 1000
hz = pd.read_csv(f"{D}/hormuz_daily.csv", index_col=0, parse_dates=True)["n_tanker"].resample("W-FRI").mean()
W["cot"] = cot; W["hormuz"] = np.clip(1 - hz / 50.0, 0, 1); W.loc[W.index < "2019-01-01", "hormuz"] = 0.0
W["opec"] = np.log(M["opec_prod"]).resample("W-FRI").ffill().reindex(W.index).ffill()
W["oecd"] = M["oecd_stocks"].resample("W-FRI").ffill().reindex(W.index).ffill()
W = W.loc["2016-10":]
XW = pd.DataFrame({"usstocks": (W.usstocks - W.usstocks.rolling(156, min_periods=100).mean()) / 100, "cushing": (W.cushing - W.cushing.rolling(156, min_periods=100).mean()) / 10, "spr": (W.spr - W.spr.rolling(156, min_periods=100).mean()) / 100,
                   "oecd": (W.oecd - W.oecd.rolling(156, min_periods=100).mean()) / 100, "usd": np.log(W.usd), "sp": np.log(W.sp), "cot": W.cot / 100, "hormuz": W.hormuz, "opec": W.opec})
for tgt in ["brent", "wti"]:
    d = pd.concat([np.log(W[tgt]).rename("y"), XW], axis=1).dropna()
    pp, m = fit(d); fv = np.exp(pd.Series([pp(d.drop(columns="y").loc[[t]]) for t in d.index], index=d.index)); act = np.exp(d.y)
    wf = {}
    for t in d.index[d.index >= "2024-01-05"]:
        if t.month != (t - pd.Timedelta(days=7)).month or t == d.index[d.index >= "2024-01-05"][0]:  # refit monthly to save time
            pw, _ = fit(d.loc[:t].iloc[:-1])
        wf[t] = float(np.exp(pw(d.drop(columns="y").loc[[t]])))
    wf = pd.Series(wf); ew = (act.reindex(wf.index) - wf).abs()
    last = d.index[-1]
    OUT.setdefault("weekly", {})[tgt] = dict(last_week=str(last.date()), fv_last=round(float(fv.iloc[-1]), 1), actual_last=round(float(act.iloc[-1]), 1), r2=round(float(1 - ((d.y - np.log(fv))**2).sum() / ((d.y - d.y.mean())**2).sum()), 3), wf_med_2024=round(float(ew.median()), 1), wf_90_2024=round(float(ew.quantile(.9)), 1),
                                         fv_recent={str(k.date()): round(float(v), 1) for k, v in fv.iloc[-12:].items()}, act_recent={str(k.date()): round(float(v), 1) for k, v in act.iloc[-12:].items()})
    print(f"  {tgt}: viikkomalli 2016-10→ R² {OUT['weekly'][tgt]['r2']:.2f}; walk-forward 2024→ med ±{ew.median():.1f} $ (90 % ±{ew.quantile(.9):.1f}); viimeisin viikko {last.date()}: fair value {fv.iloc[-1]:.0f} $ vs toteutunut {act.iloc[-1]:.0f} $")
    print("    viimeiset viikot fv/act:", " ".join(f"{k.strftime('%m-%d')}:{v:.0f}/{act.loc[k]:.0f}" for k, v in fv.iloc[-8:].items()))

# ============ 7. SVAR (Kilian-style) ============
print("\n=== 7. SVAR (tarjonta / aktiviteetti / hinta / varastot), 2006→ ===")
from statsmodels.tsa.api import VAR
bdi = pd.read_csv(f"{RAW}/bdi_daily.csv", parse_dates=["date"]).set_index("date")["value"].resample("MS").mean()
cpi = pd.read_csv(f"{RAW}/fred_CPI_US.csv", parse_dates=["date"]).set_index("date")["value"]; cpi.index = cpi.index.to_period("M").to_timestamp()
wp = pd.read_csv(f"{D}/panel_long_2006_2026.csv", index_col=0, parse_dates=True)
steo_world = None
try:
    import glob
    # world production spliced is not in long panel; rebuild quickly from long_panel's STEO cache not saved -> use opec_prod + world_balance proxy: use OPEC production growth as supply
    supply = np.log(wp.opec_prod).diff()
except Exception: supply = None
V = pd.DataFrame({"supply": supply, "activity": np.log(bdi).diff(), "rprice": np.log(wp.brent / cpi.reindex(wp.index) * 100), "dstock": wp.oecd_stocks.diff() / 100}).dropna()
V = V.loc["2006-06":]; V = V.reindex(pd.date_range(V.index.min(), V.index.max(), freq="MS")).interpolate(limit=2).dropna()
def var_oos(V, h, start="2015-01-01", lags=6):
    errs, e0 = [], []
    for t in V.index[(V.index >= start) & (V.index <= V.index[-1] - pd.DateOffset(months=h))]:
        tr = V.loc[:t]
        try:
            res = VAR(tr).fit(lags); fc = res.forecast(tr.values[-lags:], h)[-1, 2]
        except Exception: continue
        if (t + pd.DateOffset(months=h)) not in V.index: continue
        a = V.rprice.loc[t + pd.DateOffset(months=h)]; errs.append(a - fc); e0.append(a - V.rprice.loc[t])
    return float(np.sqrt(np.mean(np.square(errs))) / np.sqrt(np.mean(np.square(e0)))), len(errs)
svar = {}
for h in [1, 3, 6, 12]:
    ratio, n = var_oos(V, h); svar[f"rmse_ratio_h{h}"] = round(ratio, 3); print(f"  VAR(6) reaalihinnan ennuste vs ei-muutosta, {h} kk: RMSE-suhde {ratio:.3f} (n={n})")
res = VAR(V).fit(6)
# historical decomposition for 2026 via structural shocks (Cholesky, order supply->activity->price->stock)
u = res.resid; Sigma = np.cov(u.values.T); Pc = np.linalg.cholesky(Sigma); eps = pd.DataFrame(np.linalg.solve(Pc, u.values.T).T, index=u.index, columns=V.columns)
irf = res.irf(24).orth_irfs  # shape (25, k, k): response of var i to shock j
k = V.shape[1]; pi = 2  # price index
start = pd.Timestamp(f"{TODAY.year}-01-01"); idx = eps.index[eps.index >= start]
contrib = {c: 0.0 for c in V.columns}
for s_j, col in enumerate(V.columns):
    tot = 0.0
    for i, t in enumerate(idx):
        lag = len(idx) - 1 - i
        if lag <= 24: tot += irf[lag, pi, s_j] * eps.loc[t, col]
    contrib[col] = round(float(tot * 100), 1)
svar["decomp_2026_logpct"] = contrib; svar["actual_change_2026_logpct"] = round(float((V.rprice.iloc[-1] - V.rprice.loc[f"{TODAY.year - 1}-12-01"]) * 100), 1); svar["year"] = TODAY.year
print("  2026 (tammi→syys) reaalihinnan muutos %.0f %% jaettuna shokkeihin (log-%%): " % svar["actual_change_2026_logpct"], contrib, " (loppu = alkuehdot/viiveet)")
OUT["svar"] = svar
json.dump(OUT, open(f"{D}/models17.json", "w"), default=float)
pg = json.load(open(f"{D}/page_data.json")); pg["m17"] = json.load(open(f"{D}/models17.json")); json.dump(pg, open(f"{D}/page_data.json", "w"), ensure_ascii=False, default=float)
print("\nDONE")

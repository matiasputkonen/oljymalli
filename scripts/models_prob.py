#!/usr/bin/env python3
"""Probability toolkit (items 1, 2, 4, 5, 7): Bayesian hazard with uncertainty and competing risks, entropy pooling of
model views into the options-implied distribution, Merton jump-diffusion calibration to WTI options, Ornstein–Uhlenbeck
estimate of the fair-value gap half-life, Kelly sizing. Writes data/prob.json and page_data.json['prob']."""
import os, json, warnings, numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm, beta as beta_dist
from scipy.optimize import brentq, minimize
warnings.filterwarnings("ignore")
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); D = f"{ROOT}/data"
pg = json.load(open(f"{D}/page_data.json")); hzj = json.load(open(f"{D}/hazard.json")); CN = json.load(open(f"{D}/curves_now.json")); OPT = CN["options"]
OUT = {}
TODAY = pd.Timestamp(pd.Timestamp.today().date())

# ============ 1. Bayesian hazard: Beta-binomial survival with competing risks ============
hz = pd.read_csv(f"{D}/hormuz_daily.csv", parse_dates=["date"]).set_index("date")["n_tanker"].astype(float)
normal = float(hz.loc["2019":"2025"].mean()); m = hz.resample("MS").mean(); closed = m < 0.5 * normal   # month counts as closed if transits < 50 % of normal
crisis_start = closed[closed].index[0] if closed.any() else None
months_closed = int(closed.loc[crisis_start:].sum()) if crisis_start is not None else 0
daily_open = (hz.loc[crisis_start:].rolling(7).mean() > 0.2 * normal) if crisis_start is not None else pd.Series(dtype=bool)
# reopening events = runs of >= 7 days with the 7-day mean above 20 % of normal (the June 2026 memorandum window, 10–21 tankers/day, counts as one partial reopening)
runs = (daily_open != daily_open.shift()).cumsum(); open_runs = daily_open.groupby(runs).agg(["sum", "first"]); n_open_events = int(((open_runs["first"]) & (open_runs["sum"] >= 7)).sum())
# escalation events after the crisis start, from the events list (geo/pol kinds)
ESC = [e for e in pg["events"] if e["date"] >= str(crisis_start.date()) and e["kind"] in ("geo", "pol") and e["date"] > "2026-03-01"]
n_esc = len(ESC); n_months = max(months_closed, 1)
h_mkt = float(hzj["now"]["CL"]["hazard"])
def posterior(successes, trials, prior_mean=None, prior_n=0.0):
    a0, b0 = (1.0, 1.0) if prior_mean is None else (prior_mean * prior_n, (1 - prior_mean) * prior_n)
    a, b = a0 + successes, b0 + trials - successes; d = beta_dist(a, b)
    q = {p: float(d.ppf(p)) for p in [0.05, 0.25, 0.5, 0.75, 0.95]}
    sim = d.rvs(20000, random_state=1); cum = {k: {"mean": float(np.mean(1 - (1 - sim) ** k)), "p05": float(np.quantile(1 - (1 - sim) ** k, 0.05)), "p95": float(np.quantile(1 - (1 - sim) ** k, 0.95))} for k in [3, 6, 12]}
    return dict(a=round(a, 2), b=round(b, 2), mean=round(float(d.mean()), 3), q={str(k): round(v, 3) for k, v in q.items()}, cum_open=cum)
flat = posterior(n_open_events, n_months); informed = posterior(n_open_events, n_months, prior_mean=h_mkt, prior_n=6.0)
esc = posterior(n_esc, n_months)
h_o, h_e = informed["mean"], esc["mean"]; p_esc_first = h_e / (h_o + h_e)
OUT["bayes"] = dict(crisis_start=str(crisis_start.date()) if crisis_start is not None else None, months_closed=months_closed, n_open_events=n_open_events, n_escalations=n_esc, escalations=[e["text"][:60] for e in ESC], market_hazard=h_mkt,
                    flat=flat, informed=informed, escalation=esc, p_escalation_before_opening=round(float(p_esc_first), 3), normal_transits=round(normal, 1))
print(f"1. Bayes: kriisi alkoi {crisis_start.date() if crisis_start is not None else '–'}, {months_closed} kk kiinni, {n_open_events} avautumisjakso(a), {n_esc} eskalaatiota | markkinahasardi {h_mkt*100:.0f} %/kk")
print(f"   tasapriori: hasardi {flat['mean']*100:.0f} % (90 % väli {flat['q']['0.05']*100:.0f}–{flat['q']['0.95']*100:.0f}); P(auki 6 kk) {flat['cum_open'][6]['mean']*100:.0f} % ({flat['cum_open'][6]['p05']*100:.0f}–{flat['cum_open'][6]['p95']*100:.0f})")
print(f"   markkinapriori (n=6): hasardi {informed['mean']*100:.0f} % ({informed['q']['0.05']*100:.0f}–{informed['q']['0.95']*100:.0f}); P(auki 6 kk) {informed['cum_open'][6]['mean']*100:.0f} % ({informed['cum_open'][6]['p05']*100:.0f}–{informed['cum_open'][6]['p95']*100:.0f}); eskalaatiohasardi {h_e*100:.0f} %/kk → P(eskalaatio ennen avautumista) {p_esc_first*100:.0f} %")

# ============ options densities (shared by 2 and 4) ============
rows = [l.strip().split("|") for l in open(OPT["file"]) if l.strip()]
op = pd.DataFrame(rows, columns=["exp", "type", "K", "px", "oi"]); op["K"] = op.K.astype(float); op["px"] = op.px.astype(float)
t0 = pd.Timestamp(OPT["date"]); r = 0.04; F0 = float(CN["wti"]["curve"][0]["price"])
def black76(F, K, T, sig, call=True):
    d1 = (np.log(F / K) + 0.5 * sig**2 * T) / (sig * np.sqrt(T)); d2 = d1 - sig * np.sqrt(T)
    return np.exp(-r * T) * ((F * norm.cdf(d1) - K * norm.cdf(d2)) if call else (K * norm.cdf(-d2) - F * norm.cdf(-d1)))
def iv(price, F, K, T, call):
    try: return brentq(lambda s: black76(F, K, T, s, call) - price, 0.01, 4.0)
    except Exception: return np.nan
DENS = {}
for code, expd in OPT["expiries"].items():
    d = op[op.exp == code]; T = (pd.Timestamp(expd) - t0).days / 365.0
    if T < 0.05 or len(d) < 20: continue
    C = d[d.type == "C"].set_index("K").px; P = d[d.type == "P"].set_index("K").px; both = C.index.intersection(P.index); near = both[(both > 0.6 * F0) & (both < 1.4 * F0)]
    if len(near) < 3: continue
    F = float(np.median([(C[k] - P[k]) * np.exp(r * T) + k for k in near]))
    pts = [(k, iv(C[k], F, k, T, True)) for k in C.index if k >= F] + [(k, iv(P[k], F, k, T, False)) for k in P.index if k < F]
    pts = pd.DataFrame(pts, columns=["K", "iv"]).dropna(); pts = pts[(pts.iv > 0.05) & (pts.iv < 3)]
    xk = np.log(pts.K / F); w = np.ones(len(pts)); w[(pts.K > 0.6 * F) & (pts.K < 1.6 * F)] = 3.0; coef = np.polyfit(xk, pts.iv, 4, w=w)
    Kg = np.linspace(20, 260, 2401); xg = np.log(Kg / F); ivg = np.clip(np.polyval(coef, xg), 0.08, 3.0); lo, hi = xk.min(), xk.max(); ivg[xg < lo] = np.polyval(coef, lo); ivg[xg > hi] = np.polyval(coef, hi)
    Cg = black76(F, Kg, T, ivg, True); q = np.clip(np.gradient(np.gradient(Cg, Kg), Kg) * np.exp(r * T), 0, None); q /= np.trapezoid(q, Kg)
    DENS[code] = dict(expiry=expd, T=T, F=F, K=Kg, q=q, pts=pts)
def qstats(K, p):
    cdf = np.cumsum(p) * (K[1] - K[0]); cdf /= cdf[-1]
    return dict(q={str(pp): round(float(np.interp(pp, cdf, K)), 1) for pp in [0.05, 0.25, 0.5, 0.75, 0.95]}, mean=round(float(np.trapezoid(K * p, K)), 1), p_below_80=round(float(np.interp(80, K, cdf)), 3), p_above_120=round(float(1 - np.interp(120, K, cdf)), 3))

# ============ 2. Entropy pooling (Meucci): minimum-relative-entropy distribution satisfying model views ============
md = pg["model"]["wti"]; P0 = md["P0"]
def entropy_pool(K, q, constraints):
    """constraints: list of (f(K) array, target). Solve dual: p ∝ q·exp(Σ λ_j f_j) with E_p[f_j] = target_j."""
    Fm = np.vstack([c[0] for c in constraints]); tgt = np.array([c[1] for c in constraints])
    def p_of(lam): w = q * np.exp(np.clip(lam @ Fm, -50, 50)); return w / np.trapezoid(w, K)
    def dual(lam): p = p_of(lam); return float(np.trapezoid(p * np.log(np.maximum(p, 1e-300) / np.maximum(q, 1e-300)), K) - lam @ (np.array([np.trapezoid(p * f, K) for f in Fm]) - tgt)) * -1
    def resid(lam): p = p_of(lam); return np.array([np.trapezoid(p * f, K) for f in Fm]) - tgt
    res = minimize(lambda l: float((resid(l) ** 2).sum()), np.zeros(len(constraints)), method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-10, "maxiter": 4000})
    p = p_of(res.x); kl = float(np.trapezoid(p * np.log(np.maximum(p, 1e-300) / np.maximum(q, 1e-300)), K)); return p, res.x, kl, resid(res.x)
EP = {}
for code, dn in DENS.items():
    K, q, T = dn["K"], dn["q"], dn["T"]; months = T * 12
    # model view at this horizon: interpolate the combination forecast median and 50 % interval
    fc = md["forecast"]; hs = [f["h"] for f in fc]; h = float(np.clip(months, min(hs), max(hs)))
    med = float(np.interp(h, hs, [f["comb"] for f in fc])); p25 = float(np.interp(h, hs, [f["p25"] for f in fc])); p75 = float(np.interp(h, hs, [f["p75"] for f in fc]))
    cons = [((K <= med).astype(float), 0.5), (((K >= p25) & (K <= p75)).astype(float), 0.5)]
    p, lam, kl, rs = entropy_pool(K, q, cons)
    conf = 0.5; p_c = conf * p + (1 - conf) * q   # opinion pooling with 50 % confidence in the model
    EP[code] = dict(expiry=dn["expiry"], months=round(months, 1), view=dict(median=round(med, 1), p25=round(p25, 1), p75=round(p75, 1)), market=qstats(K, q), pooled=qstats(K, p), blended=qstats(K, p_c), kl=round(kl, 4), lam=[round(float(x), 3) for x in lam], resid=[round(float(x), 4) for x in rs])
    print(f"2. Entropy pooling {code} ({dn['expiry']}): markkina med {EP[code]['market']['q']['0.5']} → näkemys {med:.0f} → pooled med {EP[code]['pooled']['q']['0.5']} (KL {kl:.3f}), P(<80) {EP[code]['market']['p_below_80']*100:.0f} → {EP[code]['pooled']['p_below_80']*100:.0f} %, blend50 {EP[code]['blended']['q']['0.5']}")
OUT["entropy_pooling"] = EP

# ============ 4. Merton jump-diffusion calibrated to option implied vols (joint over expiries) ============
import math
def merton_call_v(F, K, T, sig, lam, muJ, sJ, nmax=25):
    kappa = np.exp(muJ + 0.5 * sJ**2) - 1; lam2 = lam * (1 + kappa); tot = np.zeros_like(K, dtype=float)
    for n in range(nmax):
        Fn = F * np.exp(n * np.log(1 + kappa) - lam * kappa * T); sn = np.sqrt(sig**2 + n * sJ**2 / T); wgt = math.exp(-lam2 * T) * (lam2 * T) ** n / math.factorial(n)
        tot += wgt * black76(Fn, K, T, sn, True)
    return tot
fit_sets = [(c, DENS[c]) for c in DENS if 0.15 <= DENS[c]["T"] <= 0.7]
def iv_from_price(F, K, T, C):
    out = []
    for k, c in zip(K, C):
        try: out.append(brentq(lambda s: black76(F, k, T, s, True) - c, 0.01, 4.0))
        except Exception: out.append(np.nan)
    return np.array(out)
def loss(x):
    sig, lam, muJ, sJ = x
    if sig <= 0.03 or lam < 0 or sJ <= 0.01: return 1e6
    tot = 0.0
    for code, dn in fit_sets:
        pts = dn["pts"]; sel = pts[(pts.K > 0.65 * dn["F"]) & (pts.K < 1.5 * dn["F"])]; K = sel.K.values; T = dn["T"]
        C = merton_call_v(dn["F"], K, T, sig, lam, muJ, sJ); ivm = iv_from_price(dn["F"], K, T, C)
        tot += float(np.nansum((ivm - sel.iv.values) ** 2))
    return tot
JD = {}
if fit_sets:
    best = None
    for x0 in [(0.35, 1.0, -0.15, 0.15), (0.30, 2.0, 0.10, 0.15), (0.30, 0.5, -0.30, 0.20), (0.40, 1.5, -0.05, 0.25)]:
        res = minimize(loss, np.array(x0), method="Nelder-Mead", options={"maxiter": 1500, "xatol": 1e-4, "fatol": 1e-8})
        if best is None or res.fun < best.fun: best = res
    sig, lam, muJ, sJ = best.x; kappa = float(np.exp(muJ + 0.5 * sJ**2) - 1)
    JD = dict(expiries=[c for c, _ in fit_sets], sigma=round(float(sig), 3), lam_per_year=round(float(lam), 3), jump_mean_pct=round(float(kappa * 100), 1), jump_sd_pct=round(float(sJ * 100), 1), p_jump_3m=round(float(1 - np.exp(-lam * 0.25)), 3), p_jump_12m=round(float(1 - np.exp(-lam)), 3),
              total_var_share_jumps=round(float(lam * (muJ**2 + sJ**2) / (sig**2 + lam * (muJ**2 + sJ**2))), 3), rmse_iv_pts=round(float(np.sqrt(best.fun / sum(len(d["pts"]) for _, d in fit_sets))) * 100, 2))
    print(f"4. Merton: diffuusio σ {sig*100:.0f} %, hyppyintensiteetti {lam:.2f}/v (P(hyppy 3 kk) {JD['p_jump_3m']*100:.0f} %), hypyn keskikoko {kappa*100:+.1f} % ± {sJ*100:.0f} %, hyppyjen osuus varianssista {JD['total_var_share_jumps']*100:.0f} %, sovitusvirhe {JD['rmse_iv_pts']:.1f} vol-%")
OUT["jump_diffusion"] = JD

# ============ 5. Ornstein–Uhlenbeck / AR(1) on the fair-value gap ============
OU = {}
for t in ["wti", "brent"]:
    m_ = pg["model"][t]; g = pd.Series(np.log(np.array(m_["actual"]) / np.array(m_["fv_insample"])), index=pd.to_datetime(m_["dates"])).dropna()
    X = sm.add_constant(g.shift(1).dropna()); y = g.iloc[1:]; ols = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3}); phi = float(ols.params.iloc[1]); se = float(ols.bse.iloc[1])
    hl = lambda p: float(-np.log(2) / np.log(p)) if 0 < p < 1 else float("inf")
    phi_lo, phi_hi = max(phi - 1.645 * se, 0.01), min(phi + 1.645 * se, 0.999)
    rev = {h: round(float(1 - phi ** h), 3) for h in [1, 3, 6, 12]}; gap_now = float(m_["gap_pct"]) / 100
    OU[t] = dict(phi=round(phi, 3), phi_se=round(se, 3), half_life=round(hl(phi), 1), half_life_90=[round(hl(phi_hi), 1), round(hl(phi_lo), 1)], reversion=rev, gap_now_pct=round(gap_now * 100, 1), sd_gap_pct=round(float(g.std() * 100), 1), n=int(len(y)),
                 implied_path={h: round(float(m_["P0"] * np.exp(-gap_now * (1 - phi ** h))), 1) for h in [1, 3, 6, 12]}, model_median={str(f["h"]): f["median"] for f in m_["forecast"]})
    print(f"5. OU {t}: φ {phi:.2f} ± {se:.2f} → puoliintumisaika {hl(phi):.1f} kk (90 % väli {hl(phi_hi):.1f}–{hl(phi_lo):.1f}); palautuma 3/6/12 kk {rev[3]*100:.0f}/{rev[6]*100:.0f}/{rev[12]*100:.0f} %; gap nyt {gap_now*100:+.1f} % → OU-polku 3 kk {OU[t]['implied_path'][3]} $ (malli {OU[t]['model_median'].get('3')})")
OUT["ou"] = OU

# ============ 7. Kelly sizing from distributions (log-return over horizon) ============
KL = {}
def kelly_from_density(K, p, S0):
    R = K / S0 - 1; mu = float(np.trapezoid(p * R, K)); var = float(np.trapezoid(p * (R - mu) ** 2, K)); f = mu / var if var > 0 else 0.0   # discrete Kelly approximation f* = E[R]/Var[R]
    return dict(mu_pct=round(mu * 100, 2), sd_pct=round(np.sqrt(var) * 100, 1), kelly=round(float(f), 3), quarter_kelly=round(float(f / 4), 3))
for code, dn in DENS.items():
    if code not in EP: continue
    K, q = dn["K"], dn["q"]; p_pool = None
    # rebuild pooled density for this expiry
    fc = md["forecast"]; hs = [f["h"] for f in fc]; h = float(np.clip(dn["T"] * 12, min(hs), max(hs))); med = float(np.interp(h, hs, [f["comb"] for f in fc])); p25 = float(np.interp(h, hs, [f["p25"] for f in fc])); p75 = float(np.interp(h, hs, [f["p75"] for f in fc]))
    p_pool, _, _, _ = entropy_pool(K, q, [((K <= med).astype(float), 0.5), (((K >= p25) & (K <= p75)).astype(float), 0.5)])
    KL[code] = dict(expiry=dn["expiry"], F=round(dn["F"], 1), market=kelly_from_density(K, q, dn["F"]), pooled=kelly_from_density(K, p_pool, dn["F"]), blended=kelly_from_density(K, 0.5 * p_pool + 0.5 * q, dn["F"]))
    print(f"7. Kelly {code}: markkina f*={KL[code]['market']['kelly']:+.2f} (μ {KL[code]['market']['mu_pct']:+.1f} %, σ {KL[code]['market']['sd_pct']} %), pooled f*={KL[code]['pooled']['kelly']:+.2f} (μ {KL[code]['pooled']['mu_pct']:+.1f} %), blend f*={KL[code]['blended']['kelly']:+.2f}; ¼-Kelly {KL[code]['blended']['quarter_kelly']:+.2f}")
OUT["kelly"] = KL; OUT["meta"] = dict(options_date=OPT["date"], anchor=P0, generated=str(TODAY.date()))
json.dump(OUT, open(f"{D}/prob.json", "w"), default=float)
pg = json.load(open(f"{D}/page_data.json")); pg["prob"] = json.load(open(f"{D}/prob.json")); json.dump(pg, open(f"{D}/page_data.json", "w"), ensure_ascii=False, default=float)
print("saved prob.json")

import pandas as pd, numpy as np, json, warnings
warnings.filterwarnings('ignore')
OUT = '/home/claude/oil'
p = pd.read_csv(f'{OUT}/panel_monthly.csv', parse_dates=['date']).set_index('date')
a = pd.read_csv(f'{OUT}/annual.csv').set_index('year')

LOG = ['brent','wti','dubai','ttf_gas_eu','lng_japan','coal_aus','copper','iron_ore','aluminum','urea','wheat','idx_energy','idx_metals','idx_agri','idx_fertilizer','henry_hub','gold','gasoline_us','us_crude_stocks','us_spr','us_total_petroleum_stocks','cushing_stocks','us_crude_production','us_crude_exports','us_gasoline_demand','sp500','vix','usd_broad','eurusd','cpi_us','indpro_us','vehicle_sales_us','bdi','gdp_us_real','gdp_de_real','refinery_utilization']
DIFF = ['cftc_mm_net_wti','us10y','fed_funds','unrate_us','igrea','global_temp_anomaly']
chg = pd.DataFrame(index=p.index)
for c in LOG: chg[c] = np.log(p[c]).diff()
for c in DIFF: chg[c] = p[c].diff()
chg['cftc_mm_net_wti'] = chg['cftc_mm_net_wti'] / 1000.0  # thousand contracts
cols = [c for c in p.columns]

res = {}
# 1. level and change correlations with Brent
lv = p.corr(method='pearson')['brent'].drop('brent')
ch = chg.corr(method='pearson')['brent'].drop('brent')
sp_ch = chg.corr(method='spearman')['brent'].drop('brent')
n_ch = chg.apply(lambda s: s.notna() & chg['brent'].notna()).sum()
tab = pd.DataFrame({'level_corr': lv, 'change_corr': ch, 'change_spearman': sp_ch, 'n': n_ch})
res['brent_corr_table'] = tab.round(3).reset_index().rename(columns={'index': 'var'}).to_dict('records')
print(tab.sort_values('change_corr', key=abs, ascending=False).round(2).to_string())

# 2. full change-correlation matrix for heatmap (selected vars)
heat_vars = ['brent','wti','dubai','henry_hub','ttf_gas_eu','gasoline_us','copper','iron_ore','gold','idx_metals','idx_agri','us_crude_stocks','us_spr','cushing_stocks','us_crude_production','us_crude_exports','us_gasoline_demand','cftc_mm_net_wti','sp500','vix','usd_broad','us10y','igrea','bdi','indpro_us','vehicle_sales_us','global_temp_anomaly','cpi_us']
H = chg[heat_vars].corr().round(2)
res['heat_vars'] = heat_vars; res['heat_change'] = H.values.tolist()
HL = p[heat_vars].corr().round(2); res['heat_level'] = HL.values.tolist()

# 3. lead-lag: corr(brent_ret_t, x_chg_{t+k}) k=-6..6 ; k<0 => x leads brent
ll = {}
for c in chg.columns:
    if c == 'brent': continue
    row = {}
    for k in range(-6, 7):
        row[k] = chg['brent'].corr(chg[c].shift(-k))
    ll[c] = row
LL = pd.DataFrame(ll).T
LL.columns = [str(k) for k in LL.columns]
best = LL.abs().idxmax(axis=1)
res['leadlag'] = {c: {'best_lag': int(best[c]), 'best_corr': round(float(LL.loc[c, best[c]]), 3), 'lags': {k: (None if np.isnan(v) else round(float(v), 3)) for k, v in LL.loc[c].items()}} for c in LL.index}
print(LL[['-3','-2','-1','0','1','2','3']].round(2).to_string())

# 4. rolling 24m correlation of brent returns
roll = {}
for c in ['usd_broad','sp500','us_crude_stocks','igrea','cftc_mm_net_wti','henry_hub','copper','bdi','vix']:
    r = chg['brent'].rolling(24, min_periods=18).corr(chg[c])
    roll[c] = [None if np.isnan(v) else round(float(v), 3) for v in r.values]
res['rolling24'] = roll; res['dates'] = [d.strftime('%Y-%m') for d in p.index]

# 5. regressions (contemporaneous + predictive)
import statsmodels.api as sm
X = chg[['us_crude_stocks','igrea','usd_broad','sp500','cftc_mm_net_wti','vix']].copy()
y = chg['brent']
d = pd.concat([y, X], axis=1).dropna()
m = sm.OLS(d['brent'], sm.add_constant(d.drop(columns='brent'))).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
res['reg_contemp'] = {'r2': round(float(m.rsquared), 3), 'n': int(m.nobs), 'coef': {k: [round(float(v), 4), round(float(m.pvalues[k]), 3)] for k, v in m.params.items()}}
print(m.summary().tables[1]); print('R2', m.rsquared, 'n', m.nobs)
# predictive: brent_{t+1} on x_t
Xl = X.shift(1); Xl['brent_lag'] = y.shift(1)
# add level-based predictors: inventory deviation (stocks vs 12m mean), futures-curve proxy not available
inv_dev = np.log(p['us_crude_stocks']) - np.log(p['us_crude_stocks']).rolling(12).mean()
Xl['inv_dev'] = inv_dev.shift(1)
d2 = pd.concat([y, Xl], axis=1).dropna()
m2 = sm.OLS(d2['brent'], sm.add_constant(d2.drop(columns='brent'))).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
res['reg_pred'] = {'r2': round(float(m2.rsquared), 3), 'n': int(m2.nobs), 'coef': {k: [round(float(v), 4), round(float(m2.pvalues[k]), 3)] for k, v in m2.params.items()}}
print(m2.summary().tables[1]); print('R2 pred', m2.rsquared)
# out-of-sample check: expanding window from 2021, compare to no-change (zero return) forecast
preds, acts = [], []
for i in range(60, len(d2)):
    tr = d2.iloc[:i]; te = d2.iloc[i]
    mm = sm.OLS(tr['brent'], sm.add_constant(tr.drop(columns='brent'))).fit()
    xr = te.drop('brent'); xr = pd.concat([pd.Series({'const': 1.0}), xr])
    preds.append(float((mm.params * xr[mm.params.index]).sum())); acts.append(float(te['brent']))
preds, acts = np.array(preds), np.array(acts)
mse_model = np.mean((acts - preds) ** 2); mse_naive = np.mean(acts ** 2)
res['oos'] = {'n': len(acts), 'mse_ratio_model_vs_nochange': round(float(mse_model / mse_naive), 3), 'hit_rate': round(float(np.mean(np.sign(preds) == np.sign(acts))), 3)}
print('OOS', res['oos'])

# 6. Brent volatility stats and drawdowns
res['stats'] = {'brent_min': [p['brent'].idxmin().strftime('%Y-%m'), round(float(p['brent'].min()), 2)], 'brent_max': [p['brent'].idxmax().strftime('%Y-%m'), round(float(p['brent'].max()), 2)], 'brent_ret_std_m': round(float(chg['brent'].std()), 3), 'brent_ann_vol': round(float(chg['brent'].std() * np.sqrt(12)), 3)}
# spreads
res['spreads'] = {'brent_wti_mean': round(float((p['brent'] - p['wti']).mean()), 2), 'brent_dubai_mean': round(float((p['brent'] - p['dubai']).mean()), 2), 'brent_dubai_2026_09': round(float((p['brent'] - p['dubai']).loc['2026-09-01']), 2), 'brent_wti_2026_10': round(float((p['brent'] - p['wti']).loc['2026-10-01']), 2)}

# 7. annual correlations (2016-2025)
A = a.loc[2016:2025].copy()
acols = [c for c in A.columns if A[c].loc[2016:2024].notna().sum() >= 7]
al = A[acols].corr()['brent_avg'].drop('brent_avg')
ad = A[acols].pct_change().corr()['brent_avg'].drop('brent_avg')
AT = pd.DataFrame({'level': al, 'yoy_change': ad}).round(2)
res['annual_corr'] = AT.reset_index().rename(columns={'index': 'var'}).to_dict('records')
print(AT.sort_values('level', key=abs, ascending=False).to_string())

# 8. episodes
events = [('2016-11-30','OPEC+ leikkaussopimus (Alger/Wien)'),('2018-05-08','USA irtautuu Iran-sopimuksesta'),('2018-10-01','Huippu 86 $ ennen Q4 2018 romahdusta'),('2019-09-14','Abqaiq-isku'),('2020-03-08','OPEC+-hintasota alkaa'),('2020-04-20','WTI negatiivinen'),('2022-02-24','Venäjä hyökkää Ukrainaan'),('2022-03-31','USA SPR 180 Mb'),('2022-12-05','Hintakatto 60 $'),('2023-04-02','OPEC+ yllätysleikkaus'),('2023-10-07','Hamas-isku'),('2023-12-15','Punaisenmeren hyökkäykset'),('2025-04-02','USA:n tullit'),('2025-06-13','Israel–Iran 12 pv sota'),('2026-02-28','USA+Israel iskevät Iraniin, Hormuz sulkeutuu'),('2026-04-30','Brent 126,41 $ (vuoden huippu)'),('2026-05-01','UAE eroaa OPECista'),('2026-06-30','Hormuzin liikenne normalisoituu'),('2026-09-01','USA–Iran-iskut uusiutuvat'),('2026-09-26','Trump hylkää Iranin 7 pv suunnitelman'),('2026-10-16','Tankkerit miinoihin Hormuzissa')]
ep = []
for dte, name in events:
    t = pd.Timestamp(dte).to_period('M').to_timestamp()
    try:
        b0 = p['brent'].loc[t]; b1 = p['brent'].shift(-1).loc[t]; b3 = p['brent'].shift(-3).loc[t]
        ep.append({'date': dte, 'event': name, 'brent_month': round(float(b0), 1), 'chg_1m_pct': None if np.isnan(b1) else round(float(b1 / b0 - 1) * 100, 1), 'chg_3m_pct': None if np.isnan(b3) else round(float(b3 / b0 - 1) * 100, 1)})
    except KeyError: pass
res['episodes'] = ep
json.dump(res, open(f'{OUT}/analysis.json', 'w'), indent=1)
print('saved')

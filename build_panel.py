import pandas as pd, numpy as np, json, re, base64, glob, os
D = '/tmp/data'; DL = f'{D}/dl'; OUT = '/home/claude/oil'
os.makedirs(OUT, exist_ok=True)
START, END = '2016-01-01', '2026-10-31'

def fred(sid):
    df = pd.read_csv(f'{DL}/{sid}.csv', na_values='.')
    df.columns = ['date', 'v']; df['date'] = pd.to_datetime(df['date'])
    return df.set_index('date')['v'].astype(float)

def monthly_mean(s):
    s = s.dropna(); s = s[(s.index >= START) & (s.index <= END)]
    return s.resample('MS').mean()

def eia_xls(name):
    d = pd.read_excel(f'{DL}/{name}.xls', sheet_name='Data 1', header=None, skiprows=3)
    s = pd.Series(d[1].astype(float).values, index=pd.to_datetime(d[0]))
    return s

series = {}
# --- prices ---
brent_d = pd.read_csv(f'{D}/oil-prices/data/brent-daily.csv', parse_dates=['Date']).set_index('Date')['Price']
wti_d = pd.read_csv(f'{D}/oil-prices/data/wti-daily.csv', parse_dates=['Date']).set_index('Date')['Price']
series['brent'] = monthly_mean(brent_d)
series['wti'] = monthly_mean(wti_d)
# Pink sheet monthly prices
pk = pd.read_excel(f'{DL}/pink2026.xlsx', sheet_name='Monthly Prices', header=None)
hdr = pk.iloc[4].tolist()
pkd = pk.iloc[6:].copy(); pkd.columns = ['date'] + hdr[1:]
pkd['date'] = pd.to_datetime(pkd['date'].astype(str).str.replace('M', '-') + '-01')
pkd = pkd.set_index('date')
def pink(col):
    return pd.to_numeric(pkd[col], errors='coerce').loc[START:END]
series['dubai'] = pink('Crude oil, Dubai')
series['ttf_gas_eu'] = pink('Natural gas, Europe')
series['lng_japan'] = pink('Liquefied natural gas, Japan')
series['coal_aus'] = pink('Coal, Australian')
series['copper'] = pink('Copper')
series['iron_ore'] = pink('Iron ore, cfr spot')
series['aluminum'] = pink('Aluminum')
series['urea'] = pink('Urea ')
series['wheat'] = pink('Wheat, US HRW')
# Pink indices
pi = pd.read_excel(f'{DL}/pink2026.xlsx', sheet_name='Monthly Indices', header=None)
names = {}
for r in range(5, 9):
    for c, v in enumerate(pi.iloc[r].tolist()):
        if isinstance(v, str) and v.strip() and c not in names: names[c] = v.strip()
pid = pi.iloc[9:].copy(); pid = pid[pid[0].astype(str).str.match(r'\d{4}M\d{2}')]
pid.index = pd.to_datetime(pid[0].astype(str).str.replace('M', '-') + '-01')
def pidx(label):
    c = [k for k, v in names.items() if v.lower().startswith(label.lower())][0]
    return pd.to_numeric(pid[c], errors='coerce').loc[START:END]
series['idx_energy'] = pidx('Energy')
series['idx_metals'] = pidx('Metals')
series['idx_agri'] = pidx('Agriculture')
series['idx_fertilizer'] = pidx('Fertilizers')
series['henry_hub'] = fred('MHHNGSP').loc[START:END]
gold = pd.read_csv(f'{D}/gold-prices/data/monthly.csv'); gold['Date'] = pd.to_datetime(gold['Date'] + '-01')
series['gold'] = gold.set_index('Date')['Price'].loc[START:END]
series['gasoline_us'] = monthly_mean(fred('GASREGW'))
# --- EIA weekly -> monthly ---
for k, f in {'us_crude_stocks': 'WCESTUS1w', 'us_spr': 'WCSSTUS1w', 'us_total_petroleum_stocks': 'WTTSTUS1w',
             'cushing_stocks': 'W_EPC0_SAX_YCUOK_MBBLw', 'us_crude_production': 'WCRFPUS2w', 'us_crude_exports': 'WCREXUS2w',
             'refinery_utilization': 'WPULEUS3w', 'us_gasoline_demand': 'WGFUPUS2w'}.items():
    series[k] = monthly_mean(eia_xls(f))
# --- CFTC managed money net long WTI (NYMEX 067651) ---
rows = []
for f in sorted(glob.glob(f'{DL}/cftc/y*/f_year.txt')):
    df = pd.read_csv(f, dtype=str, low_memory=False)
    df = df[df['CFTC_Contract_Market_Code'].str.strip() == '067651']
    rows.append(df[['Report_Date_as_YYYY-MM-DD', 'M_Money_Positions_Long_All', 'M_Money_Positions_Short_All']])
c = pd.concat(rows); c.columns = ['date', 'long', 'short']
c['date'] = pd.to_datetime(c['date']); c = c.drop_duplicates('date').set_index('date').sort_index()
net = c['long'].astype(float) - c['short'].astype(float)
series['cftc_mm_net_wti'] = monthly_mean(net)
# --- macro/markets ---
sp = pd.read_csv(f'{D}/s-and-p-500/data/data.csv', parse_dates=['Date']).set_index('Date')
series['sp500'] = sp['SP500'].loc[START:END]
series['vix'] = monthly_mean(fred('VIXCLS'))
series['us10y'] = monthly_mean(fred('DGS10'))
series['fed_funds'] = fred('FEDFUNDS').loc[START:END]
series['usd_broad'] = monthly_mean(fred('DTWEXBGS'))
series['eurusd'] = monthly_mean(fred('DEXUSEU'))
series['cpi_us'] = fred('CPIAUCSL').loc[START:END]
series['indpro_us'] = fred('INDPRO').loc[START:END]
series['unrate_us'] = fred('UNRATE').loc[START:END]
series['igrea'] = fred('IGREA').loc[START:END]
series['vehicle_sales_us'] = fred('TOTALSA').loc[START:END]
# BDI (decoded from page)
h = open(f'{DL}/bdi_ts.html', encoding='utf-8', errors='ignore').read()
p = 1278
m = re.match(r'\[(?:"[0-9]{4}-[0-9]{2}-[0-9]{2}T00:00:00\.000000",?)+\]', h[p:])
dates = json.loads(m.group(0)); e = p + len(m.group(0))
mm = re.match(r',"y":\{"dtype":"(\w+)","bdata":"([^"]+)"\}', h[e:])
arr = np.frombuffer(base64.b64decode(mm.group(2).replace('\\u002f', '/')), dtype={'i2': '<i2', 'f8': '<f8', 'i4': '<i4'}[mm.group(1)])
bdi = pd.Series(arr.astype(float), index=pd.to_datetime([d[:10] for d in dates]))
series['bdi'] = monthly_mean(bdi)
# temperature
gt = pd.read_csv(f'{D}/global-temp/data/monthly.csv'); gt = gt[gt.Source == 'GISTEMP']
gt['date'] = pd.to_datetime(gt['Year'] + '-01')
series['global_temp_anomaly'] = gt.set_index('date')['Mean'].loc[START:END]
# quarterly GDP -> monthly (interpolated, then forward)
for k, sid in {'gdp_us_real': 'GDPC1', 'gdp_de_real': 'CLVMNACSCAB1GQDE'}.items():
    q = fred(sid).loc['2015-10-01':END]
    series[k] = q.resample('MS').interpolate('linear').loc[START:END]

panel = pd.DataFrame(series).loc[START:END]
panel.index.name = 'date'
panel.to_csv(f'{OUT}/panel_monthly.csv')
print(panel.shape); print(panel.tail(3).T)
print(panel.notna().sum())

# ---------------- annual ----------------
ann = {}
def wb(ind):
    j = json.load(open(f'{DL}/wb_{ind}.json'))[1]
    df = pd.DataFrame([(r['countryiso3code'], int(r['date']), r['value']) for r in j], columns=['c', 'year', 'v'])
    return df.pivot(index='year', columns='c', values='v')
for ind, k in {'NY.GDP.MKTP.KD.ZG': 'gdp_growth', 'NY.GDP.PCAP.PP.KD': 'gdp_pc_ppp', 'SP.DYN.TFRT.IN': 'fertility',
               'SE.TER.ENRR': 'tertiary_enrol', 'SE.TER.CUAT.BA.ZS': 'tertiary_attain'}.items():
    w = wb(ind)
    for c in w.columns: ann[f'{k}_{c}'] = w[c]
hdi = pd.read_csv(f'{DL}/human-development-index.csv')
for c, n in {'USA': 'United States', 'CHN': 'China', 'DEU': 'Germany'}.items():
    s = hdi[hdi.Code == c].set_index('Year')['Human Development Index']; ann[f'hdi_{c}'] = s
en = pd.read_csv(f'{D}/energy-data/owid-energy-data.csv', usecols=['country', 'year', 'wind_electricity', 'wind_share_elec', 'oil_consumption', 'oil_production', 'solar_electricity'])
for c, n in {'USA': 'United States', 'CHN': 'China', 'DEU': 'Germany', 'WLD': 'World'}.items():
    s = en[en.country == n].set_index('year')
    ann[f'wind_twh_{c}'] = s['wind_electricity']; ann[f'oil_cons_twh_{c}'] = s['oil_consumption']; ann[f'oil_prod_twh_{c}'] = s['oil_production']; ann[f'solar_twh_{c}'] = s['solar_electricity']
pop = pd.read_csv(f'{D}/population/data/population.csv')
for c in ['USA', 'CHN', 'DEU']:
    ann[f'population_{c}'] = pop[pop['Country Code'] == c].set_index('Year')['Value']
annual = pd.DataFrame(ann); annual = annual.loc[2010:2026]
annual['brent_avg'] = panel['brent'].groupby(panel.index.year).mean()
annual['vehicle_sales_us'] = panel['vehicle_sales_us'].groupby(panel.index.year).mean()
annual.index.name = 'year'
annual.to_csv(f'{OUT}/annual.csv')
print(annual.loc[2015:].T.to_string())

Crude-Oil Forecasting Dossier
As of 23 October 2026, the dominant 1–12-month forecasting variable is not ordinary demand growth but the transition probability from restricted Hormuz traffic to normalized Gulf exports. The most defensible forecast architecture combines a no-change baseline, futures curve, real-time physical-balance models, forecast combinations and an options-implied distribution; individual structural or machine-learning models are too unstable to use alone.

Data limitation: Some requested proprietary observations—complete ICE options surfaces, CME CVOL skew, bank model specifications, historical Kpler/Vortexa exports and current contract-level open interest—cannot be verified from freely accessible primary data. They should be purchased or retrieved directly rather than inferred from news reports.

State of the market
Conflict timeline
Date	Event	Market relevance
28 Feb 2026	US–Israeli military operations against Iran began; Iranian attacks and warnings rapidly disrupted commercial shipping.	Start of the physical-supply regime break.
2 Mar	IRGC formally confirmed restrictions against “unfriendly” shipping.	Insurers and shipowners treated the route as effectively closed even without a universally enforceable legal closure.
4 Mar	IMF PortWatch reportedly recorded zero transits.	Illustrates the initial collapse rather than a permanent zero-flow condition.
7–8 Apr	US–Iran ceasefire halted major combat.	Iran continued asserting control over routing; normal commercial access did not resume.
13 Apr	The US imposed a blockade on traffic to and from Iranian ports.	Created two simultaneous restrictions: Iranian control of Hormuz and US interdiction of Iranian commerce.
17–18 Jun	Islamabad memorandum and temporary lifting of the blockade.	Iran committed to use “best efforts” to permit safe, no-charge passage for 60 days; traffic briefly recovered.
24 Jun	PortWatch transits reportedly peaked at 51.	Still below normal, but the clearest temporary reopening signal.
14–18 Jul	US blockade reinstated; Iran suspended its commitments.	Reversal to a restricted-transit state.
20 Jul	Houthis announced restrictions against Saudi ports and Saudi-linked shipping.	Extended the disruption from Hormuz to the Red Sea escape route.
Aug	Yanbu liftings increasingly went “dark” by disabling AIS.	Greatly increased disagreement among vessel-tracking providers.
Early Sep	Attacks interrupted Saudi Arabia’s East–West pipeline and reduced bypass exports.	Removed part of the principal Saudi alternative to Hormuz.
Oct	Hormuz remained far below normal commercial capacity and subject to permit, escort and blockade constraints.	The market remained a geopolitical state-transition problem rather than a conventional inventory cycle.
The pre-war route carried about one-fifth of global oil and LNG flows. In August, Hormuz oil flows averaged 7.6 mb/d, 13.1 mb/d below their pre-war level, and cumulative export losses were approaching 2.8 billion barrels, according to the IEA on 10 September 2026.

Production and bypasses
Saudi Arabia’s East–West pipeline feeds Yanbu on the Red Sea, while the UAE’s ADCOP/Habshan–Fujairah pipeline reaches the Gulf of Oman outside Hormuz. Reuters reported nominal capacities of about 5 mb/d for the Saudi route and 1.5 mb/d for ADCOP, although loading terminals, attacks, maintenance and downstream routing make effective capacity lower and time-varying.

Combined Yanbu and Fujairah exports rose from 4.1 mb/d in February to 7.8 mb/d in June, but Houthi attacks reduced them to 5.5 mb/d in August. Kpler separately estimated that Yanbu and Fujairah had reached approximately 3.8 mb/d and 1.7 mb/d respectively in May, near their effective logistics limits.

The routing constraint produced large shut-ins because Saudi Arabia, Iraq, Kuwait and other Gulf producers could not indefinitely pump into full storage. The important distinction is:

Available production capacity
≠
deliverable export supply
.
Available production capacity

=deliverable export supply.
Forecasts should therefore model fields, pipelines, terminals, tankers and destination routes separately rather than treating Gulf production quotas as immediately exportable supply.

Red Sea disruption
The Houthis’ 20 July warning prohibited loading and discharge at Saudi ports and immediately caused some Saudi cargoes to reverse course toward Suez rather than Bab el-Mandeb. By August, Kpler estimated Bab el-Mandeb traffic at about 32 vessels per day, versus roughly 50 before the renewed blockade.

AIS opacity became material: Vortexa estimated Yanbu loadings at 2.38 mb/d in one August week, Kpler at 1.78 mb/d and AXSMarine below 1 mb/d, partly because 70% or more of west-coast loadings were reportedly conducted with incomplete AIS coverage. That disagreement is not measurement noise that should be averaged away; it is a signal that the observation model has changed.

Tankers can route north through Suez or transfer through Egypt’s SUMED system, but this increases sailing distance, handling requirements and freight costs, especially for Asian buyers.

Emergency reserves
On 11 March, all 32 IEA members approved a record release of more than 400 million barrels, including 172 million barrels from the US and approximately 80 million from Japan. The release was equivalent to only about 20 days of the initial Hormuz supply loss and required weeks or months to reach the market.

By 15 October, approximately 330 million barrels had been released and about 100 million barrels remained available under the March action, including more than 20 million barrels of diesel scheduled for accelerated release. IEA members still held roughly 1.1 billion barrels of publicly owned emergency stocks in October, but the buffer was substantially smaller than in March.

The US contribution was scheduled over roughly 120 days, with the administration proposing to acquire approximately 200 million replacement barrels during the following year. Consequently, reserve releases support prompt supply but create a later restocking demand term:

Net SPR impulse
t
=
release
t
−
refill
t
.
Net SPR impulse 
t
​
 =release 
t
​
 −refill 
t
​
 .
OPEC+ and UAE
Eight OPEC+ members had paused further target increases for January–March 2026 after a 137,000 b/d December 2025 increase. After the conflict began, additional target increases became largely symbolic because transport constraints prevented members from realizing their nominal output targets.

The UAE announced on 28 April that it would withdraw from OPEC and OPEC+, effective 1 May 2026. EIA emphasized that the immediate effect was limited by Hormuz constraints, but the exit reduced OPEC+’s future control over one of the few producers with meaningful spare capacity.

The UAE’s liquids capacity was estimated near 5 mb/d, while analysts suggested that roughly 1 mb/d of incremental supply might eventually become available after logistics normalize. That makes the UAE exit bearish for medium-term prices after reopening, but not necessarily during the current export bottleneck.

Sanctions and waivers
The verifiable 2026 restriction was the US maritime blockade covering traffic to and from Iranian ports, initially imposed on 13 April, relaxed in June and reinstated in July. Claims about broad October waivers for Russian energy and “shadow fleet” sanctions appeared in secondary publications, but they could not be corroborated here against an OFAC notice or executive order and should not be placed in a quantitative baseline without primary documentation.

For model construction, sanctions should enter as vessel- and destination-specific effective discounts and transport frictions—not simply as sanctioned versus unsanctioned production:

Effective export supply
=
production
×
(
1
−
interdiction probability
)
×
(
1
−
logistics loss
)
.
Effective export supply=production×(1−interdiction probability)×(1−logistics loss).
Tanker rates
Kpler reported on 19 October that Middle East Gulf–China VLCC freight had reached approximately $24/bbl, versus $12/bbl for cargoes loading outside Hormuz in the Gulf of Oman. Freight represented about 25% of crude value for Gulf loadings, compared with roughly 5% before the war.

This matters because the relevant refiner price is:

P
landed
=
P
FOB
+
freight
+
insurance
+
delay cost
+
quality adjustment
.
P 
landed
​
 =P 
FOB
​
 +freight+insurance+delay cost+quality adjustment.
A forecast based only on screen Brent will understate regional scarcity when freight, war-risk insurance and demurrage become major parts of the landed barrel price.

Prices and curve
Price snapshots need explicit contract and timestamp conventions. On 21 October at 03:50 GMT, December Brent traded around $110.38/bbl and December WTI around $99.18/bbl, producing a same-month Brent premium of approximately $11.20/bbl. A later Brent quote on 23 October was near $113.9/bbl, but no synchronized WTI quote was available from the same source and timestamp.

Dated Brent reportedly traded near $134/bbl in mid-October, approximately $27–31/bbl above corresponding futures indications. This exceptionally large physical premium reflects prompt cargo scarcity and means that “Brent” must be separated into Dated Brent, ICE front month, constant-maturity futures and calendar-average spot series.

The curve was in severe backwardation. On 19 October, an expiring Brent contract settled around $109.55 while the more actively traded December contract settled near $98.54, an $11.01 prompt premium; reported volume was approximately 26,000 versus 195,000 lots respectively. Because expiry distorted that comparison, a production system should use constant-maturity interpolation and exclude contracts inside a configurable delivery/expiry window.

Exact contract-level open interest should be downloaded directly from ICE and CME daily settlement files. Volume cannot substitute for open interest.

Implied volatility
Cboe OVX closed at 53.28 on 21 October, compared with a 52-week range of approximately 28.4–126.0. OVX measures option-implied volatility on USO options rather than a clean constant-maturity WTI terminal distribution, so it is best used as a broad volatility state variable.

A current CME WTI CVOL number and delta-skew surface were not verifiable from the freely accessible sources reviewed. Do not infer skew from OVX: the same volatility index can coexist with very different upside-call and downside-put tail prices.

Published forecasts
Forecaster and date	Forecast	Key assumption
EIA STEO, 10 Mar 2026	Brent $79 average in 2026; $64 in 2027	Outages would ease sufficiently for prices to fall below $80 in Q3 2026 and toward $70 by year-end.
EIA STEO, Sep 2026	Brent about $90 in 2H26; $74 average in 2027	Production rises and inventories rebuild.
EIA STEO, 6 Oct 2026	Brent $105 in Q4 2026; $84 average in 2027	Middle East flows improve, but less quickly than assumed in September.
The movement from $64 to $74 and then $84 for the 2027 average demonstrates that the forecast is mostly an evolving assumption about the outage path, not stable statistical precision. A single 2027 point forecast should therefore be replaced with reopening-conditioned paths.

No directly comparable October 2026 IMF, IEA and bank price tables with explicit Hormuz assumptions were verified. Morgan Stanley was publicly reported as expecting refined-fuel tightness to persist through mid-2027, but this is not equivalent to a documented Brent point forecast.

Academic literature
What actually beats no-change
Define the relative mean-squared prediction error as:

R
M
S
P
E
h
=
M
S
P
E
(
model
,
h
)
M
S
P
E
(
no change
,
h
)
.
RMSPE 
h
​
 = 
MSPE(no change,h)
MSPE(model,h)
​
 .
Values below 1 indicate improvement. A reported “18% MSPE reduction” therefore means 
R
M
S
P
E
=
0.82
RMSPE=0.82.

Method	Main result	Horizon	Real-time verdict
Futures prices, older literature	Generally approximately as accurate as a random walk; crude-oil improvements were small and statistically insignificant at 3, 6 and 12 months.	3–12m	Survived as “hard to beat,” not as clear superiority.
Baumeister–Kilian combinations	Real-time combinations reduced MSPE by up to 18%, with directional accuracy as high as 77%.	1–24m	Yes, for monthly-average real prices.
Expanded real-time pooling	Pooled forecasts reduced MSPE by 3–29% and achieved directional accuracy as high as 73%.	Up to 24m	Yes; pooling was more stable than model selection.
Inventory MIDAS	US inventory-change MIDAS reduced MSPE by 8% at 12 months and 16% at 24 months; directional accuracy reached 71% and 77%.	12–24m	Yes, although monthly inventory models were often nearly as good.
End-of-month futures information	Using end-of-month futures to forecast monthly-average prices reduced one-month MSPE by as much as 40%; 12-month reduction was about 13%.	1–12m	Yes for monthly averages; sensitive to target definition.
Risk-adjusted futures	Full-sample adjustment reduced MSPE relative to raw futures by 20% at 3 months and 34% at 12 months.	3–12m	No: the advantage disappeared when the risk premium was estimated strictly in real time.
Random forest	More than 50% lower 1–3-month RMSE than OLS with the same predictors.	1–3m	Not demonstrated against no-change; the reported benchmark was OLS.
Quantile Bayesian VAR, 2026 preprint	Median forecast improvement of 2–5% relative to conventional Bayesian VARs.	Multiple	Not yet strong evidence against no-change; preprint and non-RW benchmark.
Forecast combinations, 2024 re-evaluation	Significant improvement over no-change for monthly-average prices through 24 months, but little or no improvement for end-of-month prices.	1–24m	Yes, with a major target-definition caveat.
Hamilton and structural models
Hamilton’s 2009 paper was primarily causal rather than a forecasting model. It argued that the 2007–08 increase resulted from strong demand confronting stagnant production, whereas many earlier shocks reflected physical supply disruptions; low short-run demand elasticity was central to the price response.

Kilian’s 2009 SVAR used global oil production, a shipping-rate-based global activity index and the real oil price to identify supply, aggregate-demand and oil-specific/precautionary-demand shocks. Its main forecasting implication is that equal-sized price movements generated by different shocks should not be extrapolated identically.

Kilian and Murphy added above-ground inventories and sign/elasticity restrictions, allowing expected future scarcity and inventory demand to affect prices. This is particularly relevant in 2026 because a closure creates both a current flow shortfall and precautionary demand for accessible barrels.

Baumeister and Hamilton’s 2019 Bayesian SVAR emphasized that structural inference depends materially on prior information about supply and demand elasticities and that recursive zero-impact restrictions are not innocuous. Structural decompositions are therefore useful scenario engines, but their identified shocks should not be treated as observed facts.

Product spreads and inventories
The gasoline–Brent crack spread approximates the incentive for refiners to transform crude into products. Baumeister, Kilian and Zhou found that it contains information about the future real price of oil, with a wider spread indicating stronger derived crude demand.

Ye, Zyren and Shore’s relative-inventory approach compares inventory with a seasonal or normal level, allowing high- and low-inventory regimes to have different price effects. Its practical limitation in 2026 is that US inventories represent only one accessible pool while Middle Eastern barrels may be physically stranded behind shipping constraints.

The EIA’s operational forecasting system reflects this literature: it pools a VAR, futures-basis model, non-oil commodity-price model, time-varying product-spread model and cumulative US-inventory-change model.

Futures and risk premia
Chinn and Coibion found energy futures broadly consistent with unbiasedness but only weakly able to explain actual spot changes; for crude oil, the basis explained little variation and futures performed approximately like a random walk. Unbiasedness does not imply low forecast error.

Hamilton and Wu modeled futures as expected future spot prices plus a time-varying risk premium. Oil’s short-end risk premium declined relative to longer maturities after the mid-2000s, coinciding with increased financial participation.

The critical real-time result is negative: although ex-post risk-premium adjustments looked powerful, recursively estimated adjustments did not reliably outperform raw futures. For production use, report both:

E
t
Q
[
S
T
]
≈
F
t
,
T
E 
t
Q
​
 [S 
T
​
 ]≈F 
t,T
​
 
and

E
t
P
[
S
T
]
=
F
t
,
T
+
R
P
^
t
,
T
,
E 
t
P
​
 [S 
T
​
 ]=F 
t,T
​
 + 
RP
  
t,T
​
 ,
while assigning wider uncertainty to the physical-measure estimate.

Carry and basis momentum
Commodity carry is related to the futures-curve slope and therefore to inventories and convenience yield. Backwardated commodities have historically earned higher futures returns than contangoed commodities in cross-sectional strategies, but this is return prediction—not necessarily spot-price-level prediction.

Boons and Prado define basis momentum as the difference between past returns on first- and second-nearby futures. It was stronger than conventional carry or momentum in their commodity cross-section. These signals are useful for CTA allocation and risk-premium forecasts, but evidence that they beat no-change for monthly Brent or WTI levels is insufficient.

Regime and TVP models
Regime switching is economically appropriate when price dynamics differ between normal inventories, physical shortage, demand collapse and geopolitical closure. Statistical benefits nevertheless tend to disappear when the regime is estimated rather than observed, especially in short evaluation windows.

Time-varying-parameter models are most useful for relationships that visibly drift—product spreads, dollar sensitivity and inventory elasticities. They should be shrunk strongly toward parsimonious benchmarks and evaluated recursively; unrestricted TVP systems are highly vulnerable to parameter uncertainty.

Density and quantiles
Probabilistic forecast combinations have outperformed individual oil models in both point and density evaluation in real-time exercises. A 2022 density study found WTI futures to be the only individual predictor delivering useful density forecasts across several horizons, while combinations beat an AR benchmark; long-horizon densities beyond about five years were not correctly calibrated.

A 2026 Quantile Bayesian VAR reported 2–5% improvements in median forecasts over ordinary BVARs and documented different predictor effects across the distribution. Because that result is a preprint and the benchmark is not no-change, it is promising rather than operationally decisive.

Conformal prediction can provide finite-sample marginal coverage under exchangeability assumptions, but oil returns in crisis periods are neither stationary nor exchangeable. No robust oil-specific study was verified that demonstrated 1–12-month real-time conformal coverage through repeated structural breaks; conformal bands should therefore use rolling or regime-weighted residuals and be stress-overlaid.

Machine learning
The strongest recent ML evidence found here is Kohlscheen’s random forest: more than 50% lower 1–3-month RMSE than linear OLS using the same 11 high-frequency predictors, with rates, the dollar and VIX accounting for a substantial part of the gain. Because the comparison was against OLS rather than no-change, it does not establish a 50% gain over the standard oil benchmark.

The World Bank’s 2024 forecasting comparison concluded that no method dominates across commodities or horizons; for oil, bivariate regressions, consensus forecasts and ML had broadly similar accuracy through one year. The operational lesson is to use ML as one ensemble member and nonlinear interaction detector—not as the sole forecast.

Common reasons published neural-network gains fail live deployment include random rather than chronological train/test splits, leakage from two-sided decomposition filters, tuning on the test period, revised macro data, failure to model contract rolls and comparison against weak ARIMA rather than no-change. Papers without a frozen walk-forward design and no-change benchmark should receive little weight.

Text, search and GPR
News sentiment, Google Trends and Caldara–Iacoviello geopolitical-risk indices can improve event classification and volatility/tail forecasts. Their weaker use case is unconditional oil-price-level forecasting because the same geopolitical-news increase can imply either lost supply, lower demand or a temporary risk premium.

A robust implementation should distinguish:

Conflict escalation versus de-escalation.

Physical infrastructure or vessel events versus rhetoric.

Supply-region news versus consuming-region demand news.

Novel events versus repeated coverage.

Publication timestamp versus event timestamp.

Expected versus surprise components.

No sufficiently documented real-time MSPE result was verified here that justifies replacing no-change or forecast combinations with a standalone text/GPR model.

Options-implied distributions
Extraction procedure
For each expiry:

Obtain official settlement prices, strike, option type, futures settlement, expiry, contract multiplier and discount rate.

Remove zero-bid, stale and obvious parity-violating observations.

Convert prices to Black-76 implied volatilities.

Fit total implied variance across log-moneyness 
k
=
ln
⁡
(
K
/
F
)
k=ln(K/F).

Enforce calendar and butterfly no-arbitrage conditions.

Differentiate the fitted call-price function twice with respect to strike.

Normalize and integrate the resulting density.

Calculate probabilities, quantiles, expected shortfall and moments.

Under Breeden–Litzenberger:

q
T
(
K
)
=
e
r
T
∂
2
C
(
K
,
T
)
∂
K
2
.
q 
T
​
 (K)=e 
rT
  
∂K 
2
 
∂ 
2
 C(K,T)
​
 .
A convenient SVI slice is:

w
(
k
)
=
a
+
b
[
ρ
(
k
−
m
)
+
(
k
−
m
)
2
+
σ
2
]
,
w(k)=a+b[ρ(k−m)+ 
(k−m) 
2
 +σ 
2
 
​
 ],
where 
w
(
k
)
=
σ
imp
2
T
w(k)=σ 
imp
2
​
 T. SABR is an alternative when a parametric forward-smile model is preferred, but raw SABR fits still require explicit arbitrage checks.

For sparse oil strikes, fit calls and puts jointly after applying put–call parity, weight observations by inverse bid–ask width and avoid finite-differencing unsmoothed settlements. Tail probabilities are otherwise dominated by numerical noise.

Physical probabilities
The extracted density is risk-neutral, 
q
(
x
)
q(x), and embeds both beliefs and risk premia. A practical conversion is exponential tilting:

p
(
x
)
=
q
(
x
)
exp
⁡
(
λ
x
)
∫
q
(
u
)
exp
⁡
(
λ
u
)
 
d
u
,
p(x)= 
∫q(u)exp(λu)du
q(x)exp(λx)
​
 ,
with 
λ
λ calibrated so that the physical mean matches a historical, survey or risk-premium-adjusted expectation. Bliss–Panigirtzoglou-style transformations instead estimate a pricing-kernel adjustment from historical forecast errors.

Report at least three distributions:

Raw risk-neutral density.

Historically tilted physical density.

Scenario-adjusted density incorporating discrete closure/reopening states.

For the current market, the discrete geopolitical mixture is:

p
(
S
T
)
=
∑
j
P
(
z
T
=
j
)
 
p
(
S
T
∣
z
T
=
j
)
,
p(S 
T
​
 )= 
j
∑
​
 P(z 
T
​
 =j)p(S 
T
​
 ∣z 
T
​
 =j),
where 
z
T
z 
T
​
  could represent full closure, escorted restricted passage, partial reopening and normal passage.

Data access
CME WTI options: official settlements and paid DataMine history; public daily pages may be usable manually but are not a reliable bulk API.

ICE Brent options: ICE Data Services; full historical strike-level settlements are generally licensed.

Cboe OVX: downloadable index history and methodology; OVX was 53.28 on 21 October 2026.

CME CVOL: methodology and current dashboard are public; full historical surfaces and contract-level analytics may require licensed data.

OVX, CVOL and ATM volatility are not substitutes for a strike-level density. Tail analysis requires the complete smile and bid–ask quality controls.

Nowcasting signals
AIS and maritime flows
Signal	Forecast use	Main failure mode
Kpler/Vortexa vessel flows	Origin, destination, cargo grade, load/discharge timing and floating storage.	Proprietary revisions and differing cargo-identification algorithms.
IMF PortWatch	Free port calls and trade-flow monitoring.	Port calls are not identical to loaded oil volumes.
AIS draught changes	Probabilistic loading/discharge detection.	Draught fields may be missing, rounded or manually entered.
Dark periods	Geopolitical-risk and hidden-flow signal.	Cannot distinguish concealment from equipment or coverage loss without ancillary data.
STS detection	Identifies sanctions evasion and cargo reassignment.	Requires spatial clustering and vessel-identity resolution.
Satellite confirmation	Validates terminal activity and floating storage.	Cloud, revisit frequency, SAR interpretation and cost.
The 2026 Yanbu episode shows the scale of the problem: Vortexa, Kpler and AXSMarine generated materially different load estimates after most liftings lost continuous AIS coverage. Never treat any single provider as ground truth during deliberate AIS suppression.

Satellite inventories
Optical imagery can estimate floating-roof tank levels from shadow geometry; synthetic-aperture radar can operate through cloud and at night. Providers such as Orbital Insight and Ursa Space convert imagery into facility-level inventory estimates, but historical backfills, tank metadata and validation generally require commercial licenses.

Use satellite data as a noisy measurement in a state-space model:

y
t
s
a
t
=
I
t
+
ϵ
t
s
a
t
,
y
t
r
e
p
o
r
t
e
d
=
I
t
+
ϵ
t
r
e
p
o
r
t
e
d
.
y 
t
sat
​
 =I 
t
​
 +ϵ 
t
sat
​
 ,y 
t
reported
​
 =I 
t
​
 +ϵ 
t
reported
​
 .
This avoids treating either reported or remotely sensed inventory as error-free.

EIA and API
The EIA Weekly Petroleum Status Report provides US crude stocks, Cushing inventories, refinery inputs, utilization, imports, exports and petroleum-product stocks. API publishes an industry estimate ahead of EIA; Bloomberg, Reuters, S&P Global Commodity Insights and Investing.com compile analyst consensus surveys.

The tradable surprise is:

S
u
r
p
r
i
s
e
t
=
A
c
t
u
a
l
t
−
C
o
n
s
e
n
s
u
s
t
,
Surprise 
t
​
 =Actual 
t
​
 −Consensus 
t
​
 ,
not the weekly inventory change by itself. A useful intraday model includes crude, Cushing, gasoline, distillates, refinery utilization, net imports and an adjustment term because apparently bullish crude draws can be offset by product builds or low refinery runs.

Estimate price response over 1-, 5-, 15- and 60-minute windows, separating scheduled EIA releases from simultaneous macro announcements. Historical elasticities should be regime-conditioned because a 5-million-barrel draw matters differently in contango and in severe backwardation.

CFTC positioning
Use disaggregated COT positions for producer/merchant, swap-dealer, managed-money and other reportables. Preferred transformations are:

N
e
t
S
h
a
r
e
t
=
L
o
n
g
t
−
S
h
o
r
t
t
O
p
e
n
I
n
t
e
r
e
s
t
t
NetShare 
t
​
 = 
OpenInterest 
t
​
 
Long 
t
​
 −Short 
t
​
 
​
 
and a rolling positioning z-score.

Positioning is more reliable as a vulnerability or crowding variable than as a standalone directional predictor. Extreme managed-money length can amplify liquidation, but it does not identify the catalyst or timing.

Weather and outages
Relevant weather channels include:

NOAA CPC degree-day and temperature outlooks for product demand.

National Hurricane Center tracks for Gulf production, ports and refineries.

BSEE shut-in reports for offshore oil and gas.

Freeze forecasts for Permian, Bakken and midcontinent wellhead disruption.

River levels and fog for Houston Ship Channel and Louisiana logistics.

Commercial Genscape/Wood Mackenzie refinery and pipeline outage data are useful because refinery runs translate product margins into crude demand. Maintenance schedules should be separated into planned, extended and unplanned outages.

MIDAS nowcasting
MIDAS directly maps high-frequency predictors into lower-frequency oil prices through a restricted lag polynomial:

R
ˉ
t
+
h
=
a
h
+
β
h
B
(
L
1
/
m
;
θ
h
)
X
t
,
n
+
ϵ
t
+
h
.
R
ˉ
  
t+h
​
 =a 
h
​
 +β 
h
​
 B(L 
1/m
 ;θ 
h
​
 )X 
t,n
​
 +ϵ 
t+h
​
 .
Baumeister and Kilian’s inventory-based MIDAS achieved MSPE reductions of 8% at 12 months and 16% at 24 months, but monthly aggregation often captured most of the available information. MIDAS is therefore most valuable for within-month nowcasts and release timing, not automatically for improving every long-horizon model.

Practitioner methods
Publicly replicable detail is much thinner than media descriptions imply.

Practitioner group	Defensible public characterization	Evidence boundary
Goldman Sachs, Morgan Stanley, JPMorgan, Citi	Balance sheets linking demand, non-OPEC supply, OPEC policy, inventories and spare capacity; scenario price paths and time-spread analysis.	Coefficients, code, trader overrides and position data are proprietary.
Energy Aspects, Rystad	Bottom-up country and field balances, outage tracking, refinery runs and policy scenarios.	Historical forecast vintages and full models usually require subscriptions.
Kpler, Vortexa	Cargo-level AIS, port, grade, destination, storage and freight analytics.	Provider disagreement becomes substantial during dark shipping, as in Yanbu.
Vitol, Trafigura, Gunvor	Physical flow, optionality, storage, freight, refinery economics and regional basis relationships.	Public interviews reveal frameworks, not replicable forecasting equations.
Andurand and discretionary macro-energy funds	Concentrated scenario analysis around supply shocks, spare capacity, demand elasticity and convex options.	Portfolio details and probabilities are not publicly auditable.
Citadel, Millennium pods	Short-horizon alternative data, event models, relative value and strict portfolio/risk limits.	No reliable public basis for attributing a specific oil model.
AQR, Man AHL, Winton and CTAs	Trend, carry, momentum, curve and volatility scaling across diversified futures.	These predict futures returns and portfolio allocation, not necessarily terminal spot-price levels. Basis momentum is documented academically.
The safest rule is: do not attribute a precise method to a firm unless it appears in a signed paper, regulatory filing, detailed interview or reproducible presentation.

Data sources
Core series
Series	Source and identifier	Frequency	Start	Access
WTI Cushing spot	FRED DCOILWTICO	Daily	Jan 1986	https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILWTICO
Brent Europe spot	FRED DCOILBRENTEU	Daily	May 1987	https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU
WTI monthly	FRED MCOILWTICO	Monthly	1986	FRED CSV/API
Brent monthly	FRED MCOILBRENTEU	Monthly	1987	FRED CSV/API
WTI spot	EIA PET.RWTC.D	Daily	1986	https://api.eia.gov/v2/petroleum/pri/spt/data/; API key
Brent spot	EIA PET.RBRTE.D	Daily	1987	Same route; API key
Spot-price workbook	EIA DNav	Daily/monthly	Varies	https://www.eia.gov/dnav/pet/xls/PET_PRI_SPT_S1_D.xls
US commercial crude stocks	EIA PET.WCESTUS1.W	Weekly	Aug 1982	EIA API/WPSR
Cushing crude stocks	EIA Cushing ending stocks	Weekly	Apr 2004	EIA API/WPSR
US crude production	EIA weekly field production	Weekly	1983	EIA API/WPSR
Refinery inputs/utilization	EIA WPSR	Weekly	1980s	EIA API/XLS
Crude imports/exports	EIA WPSR	Weekly	Varies	EIA API/XLS
STEO Brent forecast	EIA STEO, commonly STEO.BREPUUS.M	Monthly vintage	Varies	EIA API and STEO archives
STEO WTI forecast	EIA STEO, commonly STEO.WTIPUUS.M	Monthly vintage	Varies	EIA API and STEO archives
IEA global balances	IEA Oil Market Report	Monthly	Historical backfile	https://www.iea.org/reports/oil-market-report; latest summary free, detail subscription
OPEC production/balance	OPEC MOMR	Monthly	Long history	https://www.opec.org/opec_web/en/publications/338.htm; PDFs
Country oil data	JODI Oil	Monthly	Mainly 2002 onward	https://www.jodidata.org/oil/; registration/download
Rig count	Baker Hughes	Weekly/monthly	1944 US history	https://rigcount.bakerhughes.com/; XLS
Managed-money positions	CFTC disaggregated COT	Weekly Tuesday positions, Friday release	2009	https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
Legacy COT	CFTC	Weekly	1986	Historical compressed files
Hurricane tracks	NOAA/NHC	Event/6-hourly	Varies	https://www.nhc.noaa.gov/gis/; free
Temperature outlooks	NOAA CPC	Daily/weekly/monthly	Varies	https://www.cpc.ncep.noaa.gov/; free
Port traffic	IMF PortWatch	Daily/weekly	Recent	https://portwatch.imf.org/; free dashboard/download
Brent futures	Yahoo BZ=F	Daily/intraday	Provider-dependent	Download endpoint; unofficial and subject to changes
WTI futures	Yahoo CL=F	Daily/intraday	Provider-dependent	Same limitation
OVX	Yahoo/Cboe ^OVX	Daily	2007-era history	Cboe or Yahoo download
WTI settlements/options	CME NYMEX CL	Daily	Contract-dependent	CME public pages/DataMine; licensed history
Brent settlements/options	ICE Brent	Daily	Contract-dependent	ICE Data Services; licensed
Consensus inventories	Reuters/Bloomberg/S&P/Investing	Weekly	Provider-dependent	Mostly paid; Investing often blocks automated scraping
Macro and commodity indicators	Trading Economics	Daily/monthly	Series-dependent	API key and paid tiers
Historical price downloads	Investing.com	Daily	Series-dependent	Manual access; automated scraping often blocked
Energy statistics	Our World in Data	Annual	Long history	https://ourworldindata.org/energy; CSV/GitHub
GPR index	Caldara–Iacoviello	Monthly/daily variants	1900/1985 depending series	https://www.matteoiacoviello.com/gpr.htm
Commercial datasets
Provider	Highest-value fields
Kpler	Cargoes, grades, origins, destinations, storage, freight and refinery flows
Vortexa	Seaborne crude/product flows, floating storage and voyage analytics
Wood Mackenzie/Genscape	Pipelines, refineries, storage and outage monitoring
Bloomberg	Curves, options, bank forecasts, consensus surveys and archived releases
LSEG/Refinitiv	Physical assessments, freight, news and futures/options histories
S&P Global Commodity Insights	Platts physical assessments, refinery and shipping intelligence
Argus	Physical crude differentials, freight and regional assessments
LSEG Datastream/Haver	Real-time macro vintages and forecast databases
A useful public code example is the 2026 Brent rolling-origin repository that implements no-change, ARIMA, Diebold–Mariano and Clark–West comparisons. Its result—that no tested ARIMA consistently beat the random walk—should be treated as an illustrative implementation, not peer-reviewed evidence.

Forecast evaluation
Walk-forward design
Use an expanding or rolling origin:

Freeze all data available at forecast date 
t
t.

Preserve release lags and preliminary values.

Re-estimate transformations, feature selection and hyperparameters using only data through 
t
t.

Forecast 
t
+
h
t+h for 
h
=
1
,
3
,
6
,
12
h=1,3,6,12.

Advance the origin by one month.

Score the exact target definition: monthly average, end-of-month or futures settlement.

Retain every vintage and model output.

Revised production, inventory and macro data must not replace real-time observations. The target should also avoid hindsight-created continuous futures unless the historical roll rule is frozen.

Metrics and tests
Report:

R
M
S
E
h
=
1
N
∑
e
t
,
h
2
,
M
A
E
h
=
1
N
∑
∣
e
t
,
h
∣
.
RMSE 
h
​
 = 
N
1
​
 ∑e 
t,h
2
​
 
​
 ,MAE 
h
​
 = 
N
1
​
 ∑∣e 
t,h
​
 ∣.
Also report relative MSPE, median absolute error, directional accuracy and error as a percentage of the forecast-origin price.

Use Diebold–Mariano with HAC/Newey–West variance for non-nested forecasts and overlapping multi-step errors. For a larger model nesting the benchmark, use Clark–West because standard DM is biased toward the restricted model.

For probabilistic forecasts report:

Pinball loss by quantile.

Continuous ranked probability score.

Log predictive score.

Empirical coverage at 50%, 80%, 90% and 95%.

Average interval width.

Probability integral transform diagnostics.

Tail-event Brier scores.

Typical error scale
There is no stable, regime-invariant “typical” dollar error. One transparent monthly-Brent backtest reported no-change RMSE of $6.77/bbl at one month, $15.35 at six months and $22.77 at twelve months. At a $100 starting price, these correspond mechanically to about 7%, 15% and 23%, but the result is sample- and target-dependent.

This scale is consistent with the academic finding that a successful model often improves MSPE by 5–20%, not that it eliminates forecast uncertainty. In crisis regimes, scenario-selection error can overwhelm ordinary model error.

Evaluation should therefore include:

Full sample.

Pre-2008 and post-2008.

Shale era.

COVID period.

Russia–Ukraine period.

2026 Hormuz regime.

Excluding and including negative-WTI observations.

Monthly average versus month-end target.

Scenario analysis
Published baseline
EIA’s October path—Brent averaging $105 in Q4 2026 and $84 in 2027—is the clearest current official baseline. It implicitly assumes a material improvement in Middle Eastern production and flows, but not an immediate restoration to pre-war conditions.

No official institution was found publishing a numerical monthly hazard rate for full Hormuz reopening. Political-event probabilities from consultancies should not be converted into price forecasts unless the event definition, horizon and update history are disclosed.

State model
A practical state transition model is:

State	Description	Observable triggers
A: Severe restriction	Minimal unescorted traffic; attacks and high war-risk premiums.	Low PortWatch transits, rising freight, Dated Brent dislocation.
B: Escorted corridor	Regular but capacity-limited escorted passage.	Stable daily tanker count, lower attack frequency, continued insurance premium.
C: Partial reopening	Commercial passage allowed with permits or nationality restrictions.	Rising independent transits, falling freight and physical premiums.
D: Normalization	Broad unrestricted passage and normal insurance.	Flows near pre-war levels for several weeks.
Estimate a transition matrix recursively rather than assigning one reopening date:

P
=
[
p
A
A
p
A
B
p
A
C
p
A
D
p
B
A
p
B
B
p
B
C
p
B
D
p
C
A
p
C
B
p
C
C
p
C
D
p
D
A
p
D
B
p
D
C
p
D
D
]
.
P= 
​
  
p 
AA
​
 
p 
BA
​
 
p 
CA
​
 
p 
DA
​
 
​
  
p 
AB
​
 
p 
BB
​
 
p 
CB
​
 
p 
DB
​
 
​
  
p 
AC
​
 
p 
BC
​
 
p 
CC
​
 
p 
DC
​
 
​
  
p 
AD
​
 
p 
BD
​
 
p 
CD
​
 
p 
DD
​
 
​
  
​
 .
Price paths
Scenario	Physical assumptions	Indicative implication
Normalization during early 2027	Hormuz approaches normal traffic; Yanbu/Fujairah constraints ease; shut-in fields ramp; UAE adds supply outside OPEC discipline; SPR releases stop and refilling begins.	Convergence toward or below EIA’s $84 2027 average, with rapidly narrowing Dated-Brent and freight premiums.
Prolonged partial reopening	7–12 mb/d continues through Hormuz with intermittent attacks; bypass routes remain heavily used.	Brent remains above the EIA baseline and backwardation persists, although less extreme than in October.
Renewed near-closure	Escorted corridor fails, attacks intensify or Red Sea bypasses are simultaneously interrupted.	Dated Brent and freight lead futures higher; reserve policy and demand destruction become the binding stabilizers.
Rapid reopening plus demand slowdown	Logistics normalize while high prices reduce consumption and non-OPEC supply remains resilient.	Physical premiums collapse first; flat-price weakness follows as inventories rebuild.
These are conditional paths, not point forecasts. The model should calculate:

E
t
[
P
t
+
h
]
=
∑
j
P
t
(
z
t
+
h
=
j
)
E
t
[
P
t
+
h
∣
z
t
+
h
=
j
]
.
E 
t
​
 [P 
t+h
​
 ]= 
j
∑
​
 P 
t
​
 (z 
t+h
​
 =j)E 
t
​
 [P 
t+h
​
 ∣z 
t+h
​
 =j].
Demand destruction
Demand destruction should be modeled by product and region rather than using a single global elasticity. Jet fuel, petrochemical feedstocks, road fuels and power-generation fuels respond on different timescales; subsidized markets also transmit crude prices more slowly.

Useful observable indicators are:

OECD implied product demand.

Indian and Chinese refinery runs.

Airline capacity and jet cracks.

Gasoline and diesel cracks.

Freight activity.

Consumer fuel prices in local currency.

Industrial PMIs.

Subsidy and tax changes.

Spare capacity after reopening
Nominal spare capacity will not become deliverable instantly. Field restart constraints, reservoir pressure, terminal repairs, tanker availability and destination logistics create a ramp rather than a step function.

The UAE could eventually bring roughly 1 mb/d of additional production to market once export constraints ease, while its total crude-and-liquids capability has been estimated near 5 mb/d. Saudi spare capacity remains strategically important, but the relevant forecast input is sustainable export capacity after pipeline, terminal and security constraints—not the published maximum production number.

Recommended forecasting stack
Weight	Component	Purpose
20%	No-change forecast	Hard-to-beat variance-minimizing baseline
15%	Constant-maturity futures	Market price and curve information
20%	Physical balance/state-space model	Production, exports, inventories, refinery runs and demand
15%	Real-time VAR/product-spread/inventory pool	Econometric mean forecast
10%	MIDAS nowcast	Within-month inventory, prices and financial signals
10%	Regularized nonlinear model	Interactions and regime nonlinearities
10%	Options-implied median/tail overlay	Market-implied distribution and stress probabilities
Weights should be estimated on rolling out-of-sample performance but constrained to prevent abrupt concentration. During the 2026 crisis, add an explicit geopolitical-state overlay rather than allowing a generic ML model to infer the closure from a handful of observations.

The operational output should include:

1-, 3-, 6- and 12-month Brent and WTI medians.

50%, 80% and 95% intervals.

State-conditioned forecasts.

Brent–WTI and Dated–futures basis forecasts.

Reopening probability.

Expected production/export gap.

Model disagreement.

Data-quality score.

Change since the previous forecast and attribution.

Top ten readings
Alquist, Kilian & Vigfusson, “Forecasting the Price of Oil,” Handbook of Economic Forecasting, 2013 — benchmark survey and no-change result.

Baumeister & Kilian, “Forecasting the Real Price of Oil in a Changing World,” 2013 — real-time combinations and 18% maximum MSPE gain.

Baumeister, Kilian and coauthors, EIA pooling study — 3–29% MSPE reduction and real-time implementation.

EIA, Short-Term Energy Outlook Crude Oil Price Forecast Methodology — five-model operational pool.

Kilian, “Not All Oil Price Shocks Are Alike,” AER, 2009 — supply, aggregate-demand and precautionary-demand decomposition.

Kilian & Murphy, “The Role of Inventories and Speculative Trading,” JAE, 2014 — inventories and expected scarcity.

Baumeister & Hamilton, “Structural Interpretation of VARs with Incomplete Identification,” AER, 2019 — identification and elasticity uncertainty.

Hamilton & Wu, “Risk Premia in Crude Oil Futures Prices,” 2014 — futures-term-structure risk premia and the real-time caveat.

IEA, “Oil Markets Strain to Plug the Gap…,” 10 Sep 2026 — best concise physical account of Hormuz and bypass-route losses.

Congressional Research Service, “The Strait of Hormuz: Security Developments and Impacts,” 6 Aug 2026 — strongest sourced conflict and policy chronology.

Open disagreements
How open is Hormuz? Iran, the US and commercial trackers use different definitions: legal openness, physical passage and commercially insurable passage are not equivalent.

How much oil is actually leaving Yanbu? AIS suppression caused provider estimates to differ by more than 1 mb/d in the same week.

How quickly can shut-in production restart? Published capacity numbers omit field restart, terminal repair and tanker constraints.

Will reopening be bearish immediately? Restored Gulf and UAE output is bearish, but SPR refilling, depleted commercial stocks and accumulated demand may initially absorb part of the supply.

Do sophisticated forecasts genuinely beat no-change? Forecast combinations and inventory/MIDAS models show moderate real-time gains for monthly-average prices, while futures-risk-premium adjustments, ARIMA and many ML claims weaken under strict real-time evaluation or different target definitions.


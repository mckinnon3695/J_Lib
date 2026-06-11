# Oil Price Forecasting Models — Research Brief

*For: building a supply-and-demand regression model for crude oil price*
*Prepared: June 2026*

---

## Executive summary

If you take one thing from this brief: **practitioners and the best academic work both anchor short-run oil price on the physical supply-demand balance expressed through inventories** — the change in stocks (builds/draws) and the level of OECD commercial inventories versus their 5-year (or trailing 4-year) seasonal norm. Price is modelled as the variable that moves to clear the imbalance.

The single most replicable real-world template is the **U.S. EIA's Short-Term Energy Outlook (STEO)** regression, which models the month-to-month change in Brent on three inputs: the change in petroleum inventories, the level of OECD stocks vs. their seasonal norm, and the change in global GDP. That is almost exactly the supply-demand regression you have in mind, and it is published and documented.

Two hard truths shape everything below:

1. **The random walk (no-change forecast) is very hard to beat.** For the *nominal* price beyond ~3 months, today's price is the recommended forecast. Beating ARIMA is trivial and meaningless; beating the random walk *out-of-sample in real time* is the real bar.
2. **Oil futures are not reliably better than today's spot** at predicting the future spot, because a time-varying risk premium sits between them. The forward curve is a useful risk-neutral benchmark and signal input, not a point forecast.

There is also an important recent dispute (Benyo et al., 2026) that even the structural-VAR short-horizon edge may be an artifact of how the no-change benchmark is defined. Take reported "edges" with great care.

---

## 1. The academic foundation: Kilian's structural supply-demand program

Modern oil-price econometrics begins with **Lutz Kilian's structural VAR (SVAR)**, which reframed oil prices as *endogenous* to the global economy rather than as exogenous shocks.

### Kilian (2009), "Not All Oil Price Shocks Are Alike" (*American Economic Review*)

A 3-variable monthly SVAR on: (1) percent change in global crude oil production, (2) a measure of global real economic activity (Kilian's index of dry-bulk shipping freight rates, now published as the Dallas Fed **IGREA** series), and (3) the real price of oil. Identified by a recursive (Cholesky) short-run ordering: oil supply is predetermined within the month (vertical short-run supply curve), and oil-specific demand does not move global activity contemporaneously.

It decomposes every oil price move into three structural shocks:

- **Supply shock** — unexpected disruption to crude availability.
- **Aggregate demand shock** — shifts in the global business cycle that lift demand for all industrial commodities.
- **Oil-specific (precautionary) demand shock** — demand to hold inventory as insurance against future shortfalls (the convenience-yield / fear premium).

**Headline conclusion: demand, not supply, drives most oil price fluctuations.** Supply shocks explain relatively little of historical price variation; the 2003–2008 run-up was the aggregate-demand (global growth) shock. Crucially, the *type* of shock changes the effect on prices and the economy — which is why naïve oil-price/GDP regressions are unstable.

### Kilian & Murphy (2014), "The Role of Inventories and Speculative Trading" (*Journal of Applied Econometrics*)

Adds a fourth variable — **changes in global crude inventories** — and switches to **sign-restriction** identification. This is the canonical reference for bounding the short-run price elasticity of oil demand (impact elasticity bounded around ~0.026) and for identifying a **speculative/storage demand shock**. It rules out *both* diminishing supply and speculation as the cause of the 2003–08 surge (strong world consumption did it), but finds speculation mattered in 1979, 1986, 1990.

**Why this matters for you:** the four Kilian-Murphy variables — *oil production growth, global real activity, inventory change, real oil price* — are the workhorse variable set for structural oil forecasting. If you build a structural model, start here.

*Caveats:* the sign-restriction elasticity bounds are contested (Dallas Fed WP 1907, "Facts and Fiction in Oil Market Modeling"), and Kilian's activity index had a correction (use the corrected IGREA series).

---

## 2. The definitive forecasting survey and the "what actually works" results

### Alquist, Kilian & Vigfusson (2013), "Forecasting the Price of Oil" (*Handbook of Economic Forecasting*, Vol. 2)

The definitive survey. All results below are mean-squared-prediction-error (MSPE) ratios versus the no-change benchmark — **below 1.0 means the model beats the random walk** (evaluation ~1991–2009):

**Nominal price of oil:**

- **Oil futures:** MSPE ~0.94–1.00, improvements ≤6% and *not* statistically significant; long-horizon futures are strictly worse. Futures are poor predictors of the nominal spot.
- **Industrial raw-materials / CRB commodity indices:** large, significant gains at short horizons — MSPE as low as **0.78 at 3 months** (~22% improvement); fades after 3 months.
- **Commodity-exporter currencies (CAD, AUD):** small (7–13%) but significant gains at ≤3 months.
- **Survey forecasts** (Consensus, EIA): generally do *not* beat no-change.

**Real price of oil:**

- **Unrestricted VAR** (the 4-variable oil-market VAR): significant gains up to ~19% at 1–6 months (MSPE ~0.81 at 1 month).
- **Bayesian VAR:** similar; shrinkage helps when heavily parameterised.

**The chapter's practical recommendation:**

- *Nominal price:* 1–3 months → adjust today's price by the recent change in industrial raw-materials prices; 6–48 months → just use today's price (no-change); 60 months → adjust no-change by expected inflation.
- *Real price:* 1–6 months → recursive VAR; beyond 6 months → no-change.

### Baumeister & Kilian — real-time forecasting and forecast combination

- **Baumeister & Kilian (2012)** first showed model-based forecasts beat no-change in *genuine real time* (vintage data): MSPE reductions up to ~25% at 1 month, ~19% at 3 months.
- **Baumeister & Kilian (2015), forecast combination** — an *equal-weighted* combination of four models (oil-market VAR, futures-based, product-spread, no-change/AR). MSPE reductions up to ~18%, directional accuracy up to ~77%. **The simple equal-weighted combination is more stable and accurate than the best single model** — the most robust single recommendation in the literature.
- **Product spreads** (Baumeister, Kilian & Zhou): the gasoline spread with the intercept *restricted to zero* gives large significant gains; the popular 3:2:1 crack spread shows none. **Parameter restrictions matter enormously.**

### The critical recent caveat — Benyo et al. (2026), "A Reappraisal" (*Economic Inquiry*)

Replicates Baumeister & Kilian (2012) and argues that with the *correct end-of-month* no-change benchmark, the VAR/combination short-horizon edge mostly disappears; only futures-based forecasts beat the benchmark, and only at longer horizons. **Implication: your reported "edge" is highly sensitive to exactly how you define the no-change benchmark and how you align timing/vintages.**

---

## 3. How industry actually forecasts oil

### Official agencies — the most transparent templates

**EIA Short-Term Energy Outlook (STEO)** is the clearest real-world regression template. EIA forecasts **Brent first**, then derives WTI via a Brent-WTI spread. Three inputs feed the Brent view:

1. **A pooling model** — a simple average of five linear-regression models: a VAR; a futures-minus-spot (forward-curve) model; a non-oil industrial-commodity-price model; a time-varying model linking gasoline/heating-oil crack spreads to crude; and a model on cumulative U.S. crude inventory change. (Follows Baumeister, Kilian & Lee, 2014.)
2. **A direct linear regression** of the month-to-month change in Brent on: change in U.S. petroleum inventories (timely global-balance proxy), **total OECD petroleum inventories vs. the previous four-year average for that month**, and the change in global GDP (Oxford Economics).
3. **Analyst judgment**, iterated until consistent with the supply-demand balance. Demand is built from country GDP (price-inelastic short-run); supply from U.S. tight oil (price-elastic, ~6-month lag from price to Lower-48 output), non-OPEC projects, and OPEC. The residual is the **"call on OPEC" = global consumption − non-OPEC supply**.

**IEA Oil Market Report** publishes the *balance*, not a price model: world demand/supply, detailed OECD industry/government stock data vs. the 5-year average, refinery runs, and the implied call on OPEC. The IEA's OECD inventory series (released ~2-month lag) is the input EIA uses.

**OPEC MOMR** uses the same framework (demand for DoC crude). The three agencies' balances diverge materially — that spread is itself a forecastable uncertainty.

Conceptual variables agencies emphasise: inventory change and level-vs-norm; **OPEC spare capacity** (low spare capacity adds a risk premium); non-OPEC supply as price-takers; GDP-driven demand.

### Investment banks (Goldman Sachs, Morgan Stanley, JPMorgan)

Banks run the same balance → inventory path → price chain, with two anchors academics often skip:

- **OECD commercial stocks as the best predictor of Brent timespreads.** Goldman models the inventory build/draw path first, then price — and refines *where* barrels land (OECD-visible vs. China/floating/opaque), since that changes the price read of a given global build.
- **Cost-of-production / marginal-cost anchors.** The medium/long curve is anchored to the marginal cost of the price-setting barrel — post-2014 that is U.S. shale breakevens, plus cost of capital. JPMorgan ties the back end to marginal cost and frames a floor near cash cost. Morgan Stanley layers OPEC spare capacity and a **geopolitical risk premium (~$20–30/bbl)** onto the balance.

### Hedge funds and CTAs — they mostly don't point-forecast flat price

Your premise is right: pure price-level forecasting is rare. Funds trade *signals and relative value*:

- **Trend-following / momentum** — the core CTA strategy; commodity momentum has historically earned ~9%/yr in studies.
- **Carry / roll yield from the term structure** — backwardation gives positive carry (favourable for longs), contango gives negative carry (a drag). Funds go long backwardated, short contangoed contracts.
- **Term-structure slope** as a fundamentals proxy — backwardation = physical tightness/low inventories/high convenience yield; contango = glut/storage demand.
- **Hedging-pressure / positioning** — using **CFTC Commitments of Traders** when commercials crowd one side.
- **Relative value** — timespreads (prompt vs. deferred), inter-grade/location spreads (Brent-WTI, Brent-Dubai), crack spreads — rather than flat price.

### Physical trading houses (Vitol, Glencore, Trafigura, Gunvor, Mercuria)

No flat-price forecasts; their edge is **physical-fundamentals intelligence and arbitrage**: real-time cargo/vessel flows and refinery runs, storage arbitrage (cash-and-carry when contango exceeds storage + financing cost), time/location/quality arbitrage, refining margins/crack spreads (which drive crude demand), and freight rates as the swing cost that opens/closes arbitrage windows.

### The practical regressor menu (what to actually feed a model)

| Input | Source | Proxies | Cadence |
|---|---|---|---|
| U.S. crude/product stocks | EIA Weekly Petroleum Status Report; API (private) | Most timely global-balance proxy | Weekly |
| OECD commercial inventories vs. 5-yr avg | IEA OMR / MODS | Global storage level | Monthly, ~2-mo lag |
| Cushing stocks | EIA; Kayrros drone data | WTI/timespread pressure | Weekly / sub-weekly |
| Rig count | Baker Hughes | Forward U.S. supply | Weekly (Fri) |
| Speculative positioning | CFTC Commitments of Traders | Sentiment, hedging pressure, crowding | Weekly |
| Satellite tank & floating storage | Kayrros, Orbital Insight, Ursa | Real-time inventory ahead of official data | Near-real-time |
| Cargo/vessel flows, refinery runs | Kpler, Vortexa, Wood Mackenzie | Physical balance, trade flows | Real-time |
| OPEC compliance/production | OPEC MOMR, secondary surveys | Supply discipline vs. quotas | Monthly |

---

## 4. Other methods, briefly

**VECM / cointegration (spot-futures):** spot and futures are usually cointegrated (Johansen), motivating error-correction forecasting — but "not always": cointegration can be regime/threshold-dependent, so a VECM assuming a *constant* relationship may be misspecified out-of-sample.

**GARCH-family (volatility, not level):** for *volatility* forecasting, RiskMetrics/GARCH(1,1) win at short horizons, EGARCH at medium, Markov-switching GARCH at long; **Student-t innovations beat normal** (oil returns are fat-tailed). Keep the level forecast and the volatility/risk forecast separate.

**Machine learning / deep learning (LSTM, CNN-LSTM, random forests):** the applied-ML literature overwhelmingly *self-reports* beating traditional benchmarks — but methodology is frequently weak. Common flaws: single train/test splits, no benchmarking against the *random walk* (only against ARIMA or each other), in-sample-flattering metrics, data leakage (10-fold CV inflates accuracy materially), and overfitting as feature count grows. **There is no robust consensus that ML/DL systematically beats the random walk or Kilian-style VAR/combination benchmarks out-of-sample in real time.** Where ML wins, it is usually against weak benchmarks, at very short horizons, or on a single favourable sample. Use regularisation (lasso/ridge) if you go this route.

---

## 5. Generally best-regarded models — the consensus ranking

For a *point forecast of the price level*, ranked by how well they hold up out-of-sample:

1. **Forecast combination (equal-weighted) of structural + futures + spread + no-change models** — the most robust single recommendation (Baumeister-Kilian). Most stable, beats the best individual model.
2. **The 4-variable oil-market VAR / BVAR** (production, global real activity, inventory change, real price) — best structural model for the *real* price at 1–6 months.
3. **The EIA STEO regression** (Δinventories, OECD stocks vs. norm, ΔGDP) — the most practical, documented supply-demand regression; your closest off-the-shelf template.
4. **No-change / random walk** — the benchmark everything must beat; itself the recommended *nominal* forecast beyond ~3 months.
5. **Short-horizon adjustments** — industrial raw-materials (CRB) price changes and the restricted gasoline product spread give genuine, significant gains at ≤3 months.
6. **Oil futures / forward curve** — weak point predictor (risk premium), but a valuable risk-neutral benchmark and signal input.

For *trading* rather than point forecasting, the best-regarded approaches are signal-based: **momentum/trend, carry/roll-yield, term-structure slope, and positioning** — combined across timespreads and relative value rather than flat price.

---

## 6. Recommended build for your model

A defensible baseline that mirrors best practice:

**Baseline (replicate EIA):**

```
ΔBrent_t = β0 + β1·Δ(U.S. petroleum stocks)_t
              + β2·(OECD stocks − 4yr seasonal avg)_t
              + β3·Δ(global GDP)_t + ε_t
```

Then:

- **Benchmark religiously against the random walk** (define it precisely — end-of-month vs. monthly-average matters) *and* the forward curve. Use real-time/vintage data and recursive (expanding-window) out-of-sample evaluation. No single train/test splits; no look-ahead in feature construction.
- **Add signal regressors** funds rely on: a term-structure (timespread) variable and a CFTC positioning factor.
- **Consider a level-anchor term:** OPEC spare capacity / risk premium, and a marginal-cost (shale breakeven) floor for longer horizons.
- **Impose restrictions / shrinkage** (lasso, ridge, Bayesian priors) to fight overfitting — repeatedly shown to improve out-of-sample accuracy.
- **Strongly consider forecast combination** rather than betting on one specification.
- **Separate level from volatility** (GARCH-t for volatility; predictive densities for risk).

Expect inventories and the inventory-vs-norm term to carry most of the short-horizon explanatory weight.

---

## Key sources

**Academic**
- Kilian (2009), *AER* — https://www.aeaweb.org/articles?id=10.1257%2Faer.99.3.1053
- Kilian & Murphy (2014), *JAE* — https://onlinelibrary.wiley.com/doi/abs/10.1002/jae.2322
- Alquist, Kilian & Vigfusson (2013), Handbook ch. (Fed IFDP 1022) — https://www.federalreserve.gov/pubs/ifdp/2011/1022/ifdp1022.pdf
- Baumeister & Kilian (2012), real-time — https://ideas.repec.org/p/bca/bocawp/11-16.html
- Baumeister & Kilian (2015), forecast combination — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2297208
- Baumeister & Kilian, "Art and Science of Forecasting Oil" (BoC Review) — https://www.bankofcanada.ca/wp-content/uploads/2014/05/boc-review-spring14-baumeister.pdf
- Benyo et al. (2026), "A Reappraisal" (*Economic Inquiry*) — https://onlinelibrary.wiley.com/doi/full/10.1111/ecin.70009
- GARCH volatility survey (*IJF* 2018) — https://ideas.repec.org/a/eee/intfor/v34y2018i4p622-635.html
- IMF WP/15/251, Brent VARs — https://www.imf.org/external/pubs/ft/wp/2015/wp15251.pdf

**Industry / agency**
- EIA STEO crude-price methodology — https://www.eia.gov/analysis/handbook/pdf/STEO_Crude_Oil_Price.pdf
- EIA "What Drives Crude Oil Prices" — https://www.eia.gov/finance/markets/crudeoil/
- EIA WTI-on-OECD-inventory paper — https://www.eia.gov/petroleum/archive/crudeforecast1.pdf
- IEA Oil Market Report — https://www.iea.org/reports/oil-market-report-may-2026
- OPEC MOMR — https://www.opec.org/monthly-oil-market-report.html
- Goldman "The New Oil Order" — https://www.gspublishing.com/content/research/en/reports/2014/10/26/686d2683-76d2-4c4b-a201-200783ee1877.pdf
- JPMorgan oil outlook — https://www.jpmorgan.com/insights/global-research/commodities/oil-prices
- Pirrong, "Economics of Commodity Trading Firms" — https://www.bauer.uh.edu/spirrong/economics-commodity-trading-firms.pdf
- Gorton & Rouwenhorst (NBER), commodity futures — https://www.nber.org/system/files/working_papers/w11222/w11222.pdf
- Macrosynergy, commodity carry signals — https://macrosynergy.com/research/commodity-carry-as-a-trading-signal-part-1/
- EIA Weekly Petroleum Status Report — https://www.eia.gov/petroleum/supply/weekly/
- CFTC Commitments of Traders — https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm

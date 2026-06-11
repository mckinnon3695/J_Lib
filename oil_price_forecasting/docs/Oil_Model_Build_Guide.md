# Oil Price Forecasting — Model Build Guide

*A hands-on companion to the research brief. Equations, variables, estimation, data, and evaluation for each model you'd actually build.*

A note on notation: lowercase italic with logs means natural log. Δ is the first difference (this period minus last). "Real" price = nominal price deflated by US CPI. Most of this literature works in **monthly** frequency; weekly is possible for the inventory-driven models but noisier.

---

## 0. Decide what you are forecasting first

Three choices drive everything downstream:

1. **Nominal vs. real price.** Structural VARs forecast the *real* price (deflated). The EIA regression forecasts the *nominal* Brent. Pick one and stay consistent. For a first build, nominal Brent is simpler and matches what you trade.
2. **Level vs. change vs. log-change.** Oil prices are non-stationary (near unit-root), so you almost never regress on the *level* directly — you'll get spurious fit. Model the **change** (Δ price) or **log-change** (log return). The EIA model uses the change; the VARs use log-levels inside a system that's stationary as a whole.
3. **Horizon.** 1-month, 3-month, 6-month, 12-month. The honest finding: short horizons (1–3m) are where inventory/commodity signals beat the random walk; past ~6 months almost nothing reliably does. Build and evaluate each horizon separately.

---

## 1. The EIA STEO regression — your best starting point

This is the most buildable supply-demand regression and it's documented. Build this one first.

### Core specification

EIA models the **month-over-month change in the Brent spot price** as a linear function of three fundamentals:

```
ΔP_t  =  β0  +  β1·ΔINV_us_t  +  β2·(INV_oecd_t − INV_oecd_norm_t)  +  β3·ΔGDP_world_t  +  ε_t
```

Where:

- **ΔP_t** — change in Brent spot, month t vs. t−1 (try both the raw $ change and the log change; log is better behaved).
- **ΔINV_us_t** — month-over-month change in total US petroleum inventories (crude + products). This is your *timely* global-balance proxy because US data is weekly and current while global data lags ~2 months. Sign expected **negative**: a build (stocks up) pushes price down.
- **(INV_oecd_t − INV_oecd_norm_t)** — the *level* of total OECD commercial petroleum stocks minus their seasonal norm (EIA uses the previous **4-year average for that same calendar month**, which removes seasonality). Sign expected **negative**: stocks above the norm = oversupplied = downward pressure. This is the single most important "where are we in the cycle" variable.
- **ΔGDP_world_t** — change in global GDP (a demand-activity term; EIA uses Oxford Economics, but you can proxy with global industrial production or the Kilian/IGREA real-activity index, which is free). Sign expected **positive**.

### How to build the seasonal norm

For each calendar month m, `INV_oecd_norm` = average of OECD stocks in that month over the prior 4 years. So June 2026's norm = mean(June 2022, 2023, 2024, 2025). The regressor is the *deviation* from that. This deviation-from-norm construction is what makes a non-stationary stock level usable in a regression.

### Estimation

Plain **OLS** with Newey-West (HAC) standard errors (autocorrelated, heteroskedastic residuals are guaranteed in this data). That's it — this is a linear regression. The sophistication is entirely in the variable construction and the honest out-of-sample test (Section 7), not the estimator.

### The pooling layer (EIA's actual published model)

EIA doesn't trust one regression. Its published Brent forecast is the **simple average of five separate linear models**:

1. A VAR (Section 2).
2. A model on the **futures-minus-spot spread** (the forward curve as a signal).
3. A model on **non-oil industrial commodity prices** (e.g. an industrial metals/raw-materials index — the CRB industrials).
4. A **time-varying-parameter** model linking gasoline and heating-oil crack spreads to crude.
5. A model on the **cumulative change in US crude inventories**.

Average the five point forecasts with equal weights. The research is unambiguous that this equal-weight pooling is more stable than any single member — so even a rough version of each, averaged, will outperform your best single regression.

---

## 2. Kilian's structural VAR — the academic gold standard

This forecasts the **real** price and, more importantly, tells you *why* the price is moving (supply vs. demand vs. precautionary). Build it when you want the structural story, not just a number.

### Kilian (2009) — the 3-variable system

A monthly VAR in three variables, **24 lags**:

```
z_t = [ Δprod_t ,  rea_t ,  rpo_t ]'
```

- **Δprod_t** — percent change in *global* crude oil production (world, not just US).
- **rea_t** — a measure of global real economic activity. Kilian's own index (detrended dry-bulk ocean shipping freight rates) is published free as the Dallas Fed **IGREA** series. Use the *corrected* IGREA (there was a 2019 fix).
- **rpo_t** — the log of the *real* price of oil (nominal oil price deflated by US CPI).

Estimate the reduced-form VAR by OLS:  `z_t = c + Σ_{i=1..24} A_i · z_{t−i} + u_t`. The residuals `u_t` are correlated across equations — they're a mix of the underlying structural shocks.

### Recovering the three structural shocks (identification)

You impose a **recursive (Cholesky) ordering** on the contemporaneous relationships, in exactly the order above. The economic assumptions baked into that ordering:

1. **Oil supply doesn't react within the month to demand** — drilling/production is slow, so the short-run supply curve is vertical. → production is ordered first.
2. **Real activity reacts to supply shocks within the month but not to oil-specific demand shocks within the month** — the global economy responds to a physical shortfall but precautionary oil-buying doesn't move global GDP instantly. → activity second.
3. **The oil price absorbs everything contemporaneously** — it's the fastest-moving variable. → price last.

This gives you the three shocks: **oil supply shock**, **aggregate demand shock** (global business cycle), and **oil-specific / precautionary demand shock**. The headline result is that the second and third — demand — explain most price variation.

### Forecasting with it

The VAR forecasts by iterating the estimated equation forward. For the *real* price, this beats the no-change forecast by up to ~19% (MSPE) at 1–6 months in the studies. Use an **expanding (recursive) window** and re-estimate each period.

### Kilian & Murphy (2014) — add inventories, switch identification

Add a fourth variable — **change in global crude oil inventories** (proxied: OECD stock changes scaled to a world figure, the standard hack since true global stocks aren't observed):

```
z_t = [ Δprod_t ,  rea_t ,  ΔInv_t ,  rpo_t ]'
```

Identification switches from Cholesky to **sign restrictions** — instead of a strict ordering you impose the *signs* of the impulse responses that each shock must produce (e.g. a supply shock lowers production and raises price; a demand shock raises both). This is more flexible but more involved to code (you draw many candidate rotations and keep those satisfying the signs). The payoff: it identifies a fourth **speculative/storage demand shock** and lets you bound the short-run demand elasticity (~0.026 impact). Build this only after the 3-variable version works.

---

## 3. The product-spread model — a genuinely useful short-horizon edge

One of the few things that reliably beats the random walk. The idea (Verleger): refined-product prices embed information about future crude demand.

```
P_crude_{t+h}  −  P_crude_t  =  α  +  β·( P_gasoline_t − P_crude_t )  +  ε
```

The regressor is the **gasoline-crude spread** (the crack). The critical, non-obvious finding: you must **restrict the intercept α = 0**. With a free intercept the model fails out-of-sample; with α forced to zero the *restricted* gasoline spread gives large, statistically significant MSPE reductions at 6–24 month horizons. The popular **3:2:1 crack spread shows no out-of-sample power** — use the single gasoline spread, restricted. This is a clean illustration of the theme: in oil forecasting, *parameter restrictions beat free parameters* because they fight overfitting.

---

## 4. Forecast combination — do this, it's the most robust result

Don't pick a winner. Take the point forecasts from several models and **average them with equal weights**:

```
P_combined_{t+h}  =  (1/N) · Σ_k  P_model-k_{t+h}
```

Members in the canonical Baumeister-Kilian combination: (1) the oil-market VAR, (2) a futures-based forecast, (3) a product-spread model, (4) a no-change/AR forecast. Equal weighting beats fancy inverse-MSPE or regression-based weighting schemes out-of-sample — because estimating optimal weights overfits. Reductions up to ~18% MSPE and ~77% directional accuracy. **This is the highest-confidence recommendation in the whole literature.**

---

## 5. The benchmarks you must beat

You cannot claim anything works until it beats these.

- **No-change / random walk:**  `P̂_{t+h} = P_t`. Today's price is the forecast. For the *nominal* price beyond 3 months this is the recommended forecast, full stop.
- **Futures-based:**  `P̂_{t+h} = F_t^{(h)}` — the price of the h-month futures contract today. Intuitive but *not* reliably better than no-change, because of a time-varying risk premium between the futures price and the expected future spot. Include it as a member and a benchmark, not as your answer.
- **Random walk with drift / AR(1) on returns** — weak but standard.

A model that beats ARIMA but not the random walk has achieved nothing.

---

## 6. Volatility — a separate model (GARCH), not the level

If you also want the *risk* (option pricing, position sizing), the level model won't give it. Model returns `r_t = ΔlogP_t` with a **GARCH(1,1)**:

```
r_t = μ + ε_t,   ε_t = σ_t·z_t
σ²_t = ω + α·ε²_{t−1} + β·σ²_{t−1}
```

Use **Student-t innovations**, not normal — oil returns are fat-tailed and t-errors fit materially better. Short horizons: GARCH(1,1)/RiskMetrics; medium: EGARCH (captures the leverage/asymmetry where down-moves raise vol more); long: Markov-switching GARCH. Keep this entirely separate from your level forecast.

---

## 7. The evaluation protocol — where most builds go wrong

This matters more than the model choice. Get this wrong and your backtest lies to you.

1. **Recursive (expanding-window) out-of-sample.** Estimate on data up to time t, forecast t+h, roll forward one month, re-estimate, repeat. Never estimate on the whole sample and "test" on a slice of it.
2. **Real-time / vintage data where possible.** Inventory and GDP figures get revised. Using *final revised* numbers you couldn't have known at the time is look-ahead bias and inflates results. The structural-VAR real-time edge largely depends on this.
3. **The score is the MSPE ratio vs. the random walk:**  `MSPE(model) / MSPE(no-change)`. Below 1.0 = you beat it. Report this per horizon.
4. **Test significance with Diebold-Mariano** (or Clark-West for nested models). A ratio of 0.95 that isn't statistically significant is noise.
5. **Also report directional accuracy** — the fraction of times you got the *sign* of the move right. For trading this often matters more than MSPE. Above 50% (and significantly so) is the bar.
6. **Watch the benchmark definition.** The 2026 reappraisal showed the structural-VAR short-horizon edge can vanish if you use an *end-of-month* no-change benchmark vs. a monthly-average one. Define your benchmark precisely and test robustness to it.

If you use any machine-learning model, the leakage traps are: k-fold cross-validation on time series (use forward-chaining splits instead), scaling/feature construction using the full sample, and benchmarking only against ARIMA. All three manufacture fake outperformance.

---

## 8. Data — where to get each variable (mostly free)

| Variable | Source | Notes |
|---|---|---|
| Brent & WTI spot, futures curve | EIA; CME (futures) | EIA has free daily/monthly spot history |
| US petroleum inventories (weekly) | EIA Weekly Petroleum Status Report | Current, your timely proxy |
| OECD commercial stocks (monthly) | IEA OMR / MODS (paid); EIA reproduces some | ~2-month lag; build the 4-yr seasonal norm from it |
| Global oil production | EIA International; OPEC MOMR | Monthly |
| Global real activity (IGREA) | Dallas Fed (free) | Use the corrected series; demand proxy |
| World / OECD GDP, industrial production | OECD, World Bank, FRED | Quarterly GDP → interpolate, or use monthly IP |
| Gasoline / product prices (for spreads) | EIA | For the product-spread model |
| Rig count | Baker Hughes (free) | Forward US supply signal |
| CFTC positioning | CFTC Commitments of Traders (free) | Weekly; sentiment/crowding factor |
| US CPI (to deflate) | FRED (free) | For real-price models |

Most of what you need is free from **EIA, FRED, the Dallas Fed, Baker Hughes, and the CFTC**. The only genuinely paywalled core input is the timely *global* OECD inventory level (IEA) — and you can lean on US weekly stocks as your real-time proxy in the meantime.

---

## 9. Suggested build order

1. **EIA-style single regression** (Section 1) in nominal Brent, monthly. Get the data, build the seasonal-norm term, run OLS.
2. **Wire up the evaluation harness** (Section 7) — recursive OOS, MSPE ratio vs. random walk, Diebold-Mariano, directional accuracy. *Do this before adding complexity.*
3. **Add the product-spread model** (Section 3, restricted intercept) and the **futures benchmark**.
4. **Combine** the regression + spread + futures + no-change with equal weights (Section 4). This is likely your best forecaster.
5. **Add the 3-variable Kilian VAR** (Section 2) for the real price and the structural decomposition.
6. **Add GARCH-t** (Section 6) if you want volatility/risk.
7. Only then consider sign-restriction VAR or ML — and benchmark them honestly.

A reasonable expectation: at 1–3 months you can beat the random walk by a meaningful, significant margin using inventories + product spreads + combination. Past ~6 months, expect to converge toward the no-change forecast — and treat any model that claims otherwise with suspicion until it survives Section 7.

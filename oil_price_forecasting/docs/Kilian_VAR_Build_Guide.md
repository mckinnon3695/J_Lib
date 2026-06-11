# Building the Kilian (2009) Structural VAR — Step-by-Step Guide

*No code — this tells you what to do, what to decide, and what to check at each step. Pair it with `kilian_var_dataset.csv` and its data dictionary.*

---

## Which language: R

**Use R.** Structural VAR work — recursive (Cholesky) identification, impulse responses with bootstrap confidence bands, variance decompositions, and historical decompositions — is far better supported in R than in Python. The packages `vars` and `svars` do almost all of it out of the box, and they're the de-facto standard in this literature, so your output will line up with published work.

Python (`statsmodels`) can estimate the VAR, do a Cholesky IRF and a variance decomposition, but you'll hand-build the historical decomposition and the bootstrap bands, which is exactly the fiddly part R already handles. Pick Python only if you're far more fluent in it; otherwise R will save you days.

Packages to install in R: `vars`, `svars`, `tseries` (unit-root tests), `urca` (cointegration/unit-root if you go deeper), and `readr`/`tidyverse` for data handling.

---

## What this model is, in one paragraph

You are estimating a 3-variable monthly vector autoregression — every variable regressed on 24 lags of itself and the other two — then imposing a triangular (recursive) ordering on the *contemporaneous* relationships to split the messy correlated forecast errors into three clean, economically-named structural shocks: an **oil supply shock**, an **aggregate (global business-cycle) demand shock**, and an **oil-specific / precautionary demand shock**. Once you have the shocks you can trace their effects (impulse responses), measure how much of price variation each explains (variance decomposition), and reconstruct history (historical decomposition).

---

## Phase 1 — Prepare the data

**Step 1. Load the dataset.** Read `kilian_var_dataset.csv`. Confirm it's monthly, sorted by date ascending, 613 rows, 1974-01 to 2025-01.

**Step 2. Pick your three variables, in this exact order.** Order is not cosmetic — it *is* the identifying assumption (Phase 3). The order is:
1. `dprod_pct` — percent change in world oil production (variable 1, the supply block).
2. `real_activity_igrea` — the global real activity index (variable 2, the aggregate-demand block).
3. `ln_real_oil_price` — log of the real oil price (variable 3, the price block).

**Step 3. Drop the first row.** `dprod_pct` is blank in row 1 (a change needs a prior month). Your estimation sample starts 1974-02.

**Step 4. Decide your sample window.** Two sensible choices:
- *Replicate the paper first:* restrict to 1973–2007 using `kilian2009_original_data.txt` (already in Kilian's exact three-column order). Getting his published impulse responses back is your proof the machinery works.
- *Then go live:* switch to the full `kilian_var_dataset.csv` through 2025. Build both; the first validates the second.

**Step 5. Sanity-check each series before modelling.** Plot all three. You're looking for: production change hovering around zero with spikes at known disruptions (1979, 1990, 2020); the activity index swinging with global cycles (deep troughs in 2008–09 and 2020); the log real price trending and spiking. Anything flat, constant, or full of gaps means a data problem — fix it now, not after estimation.

**Step 6. Note the stationarity convention — and follow it deliberately.** Run unit-root tests (ADF/KPSS) so you understand your data, but **do not** difference the log real price even though it looks non-stationary. Kilian's deliberate choice is to estimate the VAR in *levels* of the real price (only production is differenced). Differencing everything would throw away long-run information and isn't what the model does. So: production enters as a percent change, activity and the log real price enter in levels. This is the standard and you should match it.

---

## Phase 2 — Estimate the reduced-form VAR

**Step 7. Set the lag length to 24.** Monthly oil VARs use 24 lags by convention (two years of history), and Kilian fixes it at 24. You *may* also look at what AIC/BIC/HQ suggest as a cross-check, but don't let an information criterion talk you down to 2–3 lags — the long lag length is part of the design and captures slow-moving oil-market dynamics. Report that you used 24.

**Step 8. Include a constant (intercept), no time trend.** A trend isn't part of the specification.

**Step 9. Estimate by OLS, equation by equation.** A VAR is just three OLS regressions, each variable on 24 lags of all three. The package does this in one call. What you get back: coefficient matrices (rarely interpreted directly — there are 200+ of them) and, crucially, the **residuals** (the one-step-ahead forecast errors). The residuals are the raw material for everything structural.

**Step 10. Check stability.** The package reports the VAR's roots / eigenvalues of the companion matrix. All should lie inside the unit circle (modulus < 1). With the log real price in levels you may see one root very close to 1 — that's expected and accepted here; what you don't want is a root clearly above 1, which signals misspecification.

**Step 11. Inspect the residuals.** Look at the residual correlation matrix across the three equations — the off-diagonal correlations are *non-zero*, and that's the whole point: the reduced-form errors are blends of the underlying structural shocks. Untangling them is Phase 3. (Optional: check residuals for remaining autocorrelation; with 24 lags there shouldn't be much.)

---

## Phase 3 — Identify the three structural shocks (the heart of it)

**Step 12. Understand what identification does.** You have three correlated residuals; you want three *uncorrelated*, economically meaningful shocks. You get there by assuming a specific contemporaneous (within-the-same-month) cause-and-effect ordering. Mathematically this is a Cholesky decomposition of the residual covariance matrix; economically it's a story about what can react to what *within a month*.

**Step 13. Impose the recursive ordering — production → activity → price.** This is exactly the variable order from Step 2, and it encodes three assumptions:
- **Oil production reacts to nothing else within the month.** Drilling and output decisions are slow and planned; producers don't change this month's output in response to this month's demand or price news. (Short-run supply curve is vertical.) → production is ordered first and is hit only by the oil supply shock contemporaneously.
- **Global real activity reacts to oil-supply shocks within the month, but not to oil-specific demand shocks within the month.** A physical shortfall can ripple into the global economy quickly, but precautionary oil-buying (fear-driven inventory demand) doesn't move world GDP inside a month. → activity is ordered second.
- **The real oil price reacts to everything within the month.** Price is the fastest-moving variable and absorbs all three shocks contemporaneously. → price is ordered last.

**Step 14. Name the three shocks.** After the decomposition you have three orthogonal shocks, identified by position:
1. **Oil supply shock** — the innovation to production.
2. **Aggregate demand shock** — the innovation to global real activity not driven by supply.
3. **Oil-specific (precautionary) demand shock** — the innovation to the real price not explained by the first two.

**Step 15. Fix the sign normalization.** Decide the direction of each shock so the responses are readable. The convention: define the oil **supply** shock as a *negative* production innovation (a disruption), and define both **demand** shocks as *positive* (they raise the real price). This way "a supply shock" and "a demand shock" both correspond to upward price pressure, and your plots match the published figures. Decide this explicitly rather than accepting whatever sign the software defaults to.

---

## Phase 4 — Read the results

**Step 16. Compute impulse response functions (IRFs).** Trace each variable's response to each one-standard-deviation structural shock over the next ~15–18 months. This is the main output. Generate **bootstrap confidence bands** (recursive-design wild bootstrap, ~1,000–2,000 replications) so you can see which responses are statistically distinguishable from zero. What you expect to see, as the validation that it worked:
- A supply disruption: production falls, the real price rises modestly and briefly.
- An aggregate-demand shock: production rises, activity rises, and the real price rises persistently — the big, durable price driver.
- An oil-specific demand shock: a sharp, immediate jump in the real price with little production response.

**Step 17. Compute the forecast-error variance decomposition (FEVD).** For each horizon, this tells you the share of the real price's forecast-error variance attributable to each shock. The headline result you're trying to reproduce: **demand shocks (aggregate + oil-specific) explain the large majority of real-price variation; pure supply shocks explain relatively little.** If supply dominates, your ordering or signs are wrong — go back to Phase 3.

**Step 18. Compute the historical decomposition.** Reconstruct the actual path of the real oil price as the cumulative sum of the contributions of each shock over time. This is the famous Kilian chart — it lets you say, e.g., "the 2003–2008 run-up was overwhelmingly the aggregate-demand (global boom) shock, not supply." Overlay the three cumulative contributions on the actual price to see which shock drove each historical episode.

---

## Phase 5 — Turn it into a forecast (your original goal)

**Step 19. Generate the VAR forecast.** The estimated reduced-form VAR forecasts by iterating forward: feed in the last 24 months, predict next month, append it, predict the month after, and so on, out to your horizon (1, 3, 6, 12 months). The third variable's forecast is your **real oil price** forecast; convert back to a nominal price by multiplying by your CPI projection if you need nominal.

**Step 20. Benchmark it honestly — this is non-negotiable.** Build the **no-change (random walk) forecast**: next period's predicted real price = this period's real price. Your VAR only earns its keep if it beats this out-of-sample.

**Step 21. Do it as a recursive (expanding-window) out-of-sample test.** Estimate on data up to month *t*, forecast *t+h*, roll forward one month, **re-estimate**, repeat across many years. Never estimate once on the whole sample and "test" inside it — that's look-ahead bias and it will flatter you.

**Step 22. Score it.** Compute the ratio of the VAR's mean-squared prediction error to the no-change forecast's MSPE, per horizon. Below 1.0 means you beat the random walk. Test significance with Diebold-Mariano (or Clark-West, since the models are nested). Also report **directional accuracy** — how often you got the sign of the price change right. The literature's expectation: meaningful, significant gains at 1–6 months for the *real* price; convergence toward no-change beyond that.

**Step 23. Mind the benchmark definition.** Recent work shows the apparent short-horizon edge can shrink or vanish depending on whether your no-change benchmark uses end-of-month vs. monthly-average prices, and on data vintages. Define your benchmark precisely and check that your result survives a reasonable alternative definition before you trust it.

---

## Phase 6 — Validate and document

**Step 24. Reproduce the paper before trusting the extension.** Run Phases 1–4 on the 1973–2007 sample and confirm your impulse responses and variance decomposition qualitatively match Kilian (2009). Only then believe your 2025 numbers.

**Step 25. Stress-test the identification.** Re-run with a different but defensible ordering or with sign-restriction identification (see below) and see whether your main conclusions hold. Results that flip under a small, reasonable change in assumptions aren't robust.

**Step 26. Record every choice.** Sample window, 24 lags, ordering, sign normalization, bootstrap settings, benchmark definition. These determine your numbers, and "I can't remember what I did" is the most common way these projects become unreproducible.

---

## Where to go next (optional extensions)

- **Kilian & Murphy (2014) 4-variable model.** Add a global crude **inventory change** series and switch from Cholesky to **sign-restriction** identification (impose the *signs* of impulse responses rather than a strict ordering). This adds a fourth **speculative/storage demand shock** and lets you bound the short-run demand elasticity. It's the natural upgrade once the 3-variable version is solid — but it's a meaningful step up in coding effort (you draw many candidate rotations and keep those satisfying the sign restrictions). The `VAR_data_assembled.csv` already carries the pieces you'd need to start.
- **Forecast combination.** Per the research brief, your best *forecasting* result will likely come from averaging this VAR's forecast with a futures-based forecast, a product-spread forecast, and the no-change forecast — equal weights. The VAR is one strong member of that ensemble, not the whole answer.

---

## Quick reference — the settings that define this model

| Choice | Value |
|---|---|
| Frequency | Monthly |
| Variables (in order) | `dprod_pct`, `real_activity_igrea`, `ln_real_oil_price` |
| Lags | 24 |
| Deterministic terms | Constant only (no trend) |
| Estimator | OLS, equation by equation |
| Identification | Recursive / Cholesky, ordering production → activity → price |
| Sign normalization | Supply shock = production disruption; demand shocks raise price |
| IRF horizon | ~15–18 months |
| Confidence bands | Recursive-design wild bootstrap, ~1,000–2,000 reps |
| Forecast benchmark | No-change (random walk) on the real price |
| Evaluation | Recursive out-of-sample, MSPE ratio + Diebold-Mariano + directional accuracy |

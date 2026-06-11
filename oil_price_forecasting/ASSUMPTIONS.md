# Register of Assumptions — Oil Supply, Demand & Markets

Every modelling assumption in this project, with its value, where it lives in
code, and how to stress it. Numbered so results can cite which assumptions
they ride on.

Legend: **[H]** = high leverage (changing it materially moves headline
results) · **[M]** = moderate · **[L]** = minor/technical.

---

## A. Hormuz satellite data interpretation (`src/oil_models/hormuz.py`)

| # | Assumption | Value / location | How to stress it |
|---|---|---|---|
| A1 **[H]** | **West>East transits are the laden export flow** (supply to market); East>West are ballast returns and carry no supply information. | `direction="west_east"` defaults in `daily_series`, `disruption_metrics`, `monthly_aggregates` | Rerun with `direction="both"` (doubles baseline flow) or `"east_west"`; compare shortfalls. |
| A2 **[H]** | **Every DWT is cargo**: tankers transit fully laden, so barrels = DWT × factor (crude 7.33, LNG 8.001, LPG 7.542 bbl/DWT). Real tankers load ~90–95% of DWT (bunkers, stores) and not all sail full. | `BOE_PER_DWT` dict | Multiply factors by a utilisation fraction (e.g. 0.9); baseline and shortfall scale linearly. |
| A3 **[H]** | **No pipeline bypass**: all lost transit volume is lost supply. In reality the Saudi East-West line (~5 mb/d) and UAE ADCRUDE-to-Fujairah line (~1.5 mb/d) can move barrels around Hormuz. | Not modelled anywhere | Subtract an assumed bypass volume from the shortfall before it enters scenarios (reduce `monthly_supply_loss_pct`). |
| A4 **[M]** | **Satellite coverage is complete**: a zero-DWT day means no transits, not a missed pass. Zeros are kept in all averages. | `parse_boil` treats blanks/zeros as 0.0 | Recompute baselines excluding zero days, or interpolate; pre-decline crude has no zero days so this mainly affects LNG/LPG and the post period. |
| A5 **[M]** | **Decline starts exactly 2026-02-28** (from the workbook). Baseline = simple mean of ALL days before that date; no seasonality, trend, or outlier treatment in the baseline. | `DECLINE_START` | Move the date; use a median or seasonal baseline; winsorise spike days. |
| A6 **[L]** | **Surplus days don't offset the shortfall**: daily shortfall is floored at zero, so a day above baseline never credits back. | `.clip(lower=0)` in `disruption_metrics` / `monthly_aggregates` | Remove the clip for a net-flow view (lowers cumulative shortfall). |
| A7 **[M]** | **Chemical/Products tankers carry no oil supply** (no BOE conversion, excluded from all supply math) — though product flows are real petroleum supply. | `BOE_PER_DWT` has no entry; `boe=NaN` | Add a products factor (~7.5 with a clean-cargo utilisation haircut) and include in shortfall. |
| A8 **[H]** | **World oil production is a constant 82 mb/d** when expressing the loss as a % of world supply. | `WORLD_PRODUCTION_BPD = 82_000_000` | Change the constant, or wire in `world_production_monthly.csv` once fetched. |
| A9 **[M]** | **Consumption constants** (China 20.3, USA 16.1, EU 10.5, Global 104.6 mb/d) are fixed, taken from your workbook, with no demand elasticity — "days of consumption" assumes consumption doesn't fall as prices rise. | `CONSUMPTION_BPD` | Edit the dict; or scale consumption down with a price-elasticity in the scenario months. |
| A10 **[M]** | **Implied inventory draw = 100% of the shortfall**: every barrel not transiting is drawn from consumer-side stocks (no demand destruction, no substitution). | `hormuz_implied_inv_draw_mmb` in `monthly_aggregates` | Apply a fraction < 1 for the share met by stock draws. |

## B. Kilian structural VAR (`src/oil_models/kilian_var.py`, `data_prep.py`)

| # | Assumption | Value / location | How to stress it |
|---|---|---|---|
| B1 **[H]** | **Three variables are sufficient** to span oil-market dynamics: world production growth, IGREA real-activity index, log real price. No inventories, spare capacity, positioning, or financial conditions. | `VAR_COLUMNS` in `data_prep.py` | Add the 4th Kilian-Murphy inventory variable (slot exists via Hormuz/external data) — needs sign-restriction identification to interpret. |
| B2 **[M]** | **24 lags, constant, no trend, monthly** — the literature convention. | `DEFAULT_LAGS = 24`; `fit()` builds constant-only X | Re-fit with 12 or 36 lags; add a trend; results should be qualitatively stable. |
| B3 **[H]** | **Linearity and constant parameters over 1974–2025**: one set of coefficients covers the OPEC embargo era, the shale era, and COVID; responses scale proportionally with shock size forever. | OLS in `fit()` | Estimate on subsamples (e.g. post-1985, post-2000); compare IRFs. This is THE binding assumption for the giant Hormuz shock. |
| B4 **[M]** | **Real price enters in (log) levels** despite a near-unit root (max root 0.986/0.989 accepted); production enters differenced. | Kilian's convention; `data_prep` columns | Difference the price as an alternative; you lose long-run info. |
| B5 **[H]** | **Recursive (Cholesky) identification, ordered production → activity → price**, which asserts: (i) supply does not respond within the month to demand or price (vertical short-run supply curve); (ii) global activity responds to supply shocks but not to oil-specific demand shocks within the month; (iii) price absorbs everything contemporaneously. | `_normalize_signs(np.linalg.cholesky(...))` in `fit()` | Re-order variables and re-run (one-line change to `VAR_COLUMNS` order); if FEVD conclusions flip, identification is fragile. Sign-restriction identification is the bigger upgrade. |
| B6 **[L]** | **Sign conventions**: supply shock = disruption (production falls); both demand shocks raise price on impact. | `_normalize_signs` | Cosmetic; flips chart signs only. |
| B7 **[L]** | **Wild bootstrap (Rademacher) with fixed initial conditions** is an adequate small-sample band; residuals independent over time. | `bootstrap_irf` | Try moving-block bootstrap; bands typically similar. |
| B8 **[M]** | **IGREA (dry-bulk freight-rate index) is a valid global demand proxy** — including post-2008 when shipping supply gluts distorted freight rates. | Variable choice | Swap in world industrial production (`wip` column in `data/raw/VAR_data_assembled.csv`). |
| B9 **[M]** | **The oil price is the US refiners' acquisition cost deflated by US CPI** — a US deflator and a US import price stand in for "the world real oil price". | `kilian_var_dataset.csv` construction | Rebuild with WTI (`MCOILWTICO.csv`) or Brent once fetched. |

## C. Hormuz → price scenario engine (`src/oil_models/scenarios.py`)

| # | Assumption | Value / location | How to stress it |
|---|---|---|---|
| C1 **[H]** | **A blocked barrel = a non-produced barrel**: transit loss enters the VAR as a world *production* shock. (Physically, Gulf producers may keep pumping into storage; the model can't tell the difference.) | `supply_shock_path` maps loss% → `dprod_pct` shock | This is what the pass-through fractions partially absorb; calibrate pass-through to actual production shut-in data when it exists. |
| C2 **[H]** | **Pass-through fractions 25% / 50% / 100%** bracket how much of the measured transit loss truly leaves the market (rest = rerouting, bypass, backfill from spare capacity, buyer-side stock draws). No explicit model of OPEC response, SPR releases, or rerouting. | `PASS_THROUGH` dict | Edit the dict freely — this is your main narrative dial. |
| C3 **[H]** | **Linear extrapolation of historical IRFs to a ~20%-of-world-supply shock** — a shock ~10–20× larger than anything in the estimation sample, priced at the historical per-unit response. With near-zero short-run demand elasticity the true response is convex, so the full-loss path is best read as the model's LOWER bound on a sustained full closure. | `scenario_forecast` (linear in shocks by construction) | Build the elasticity-based shortage pricing module (ΔP ≈ Δq/elasticity, Kilian-Murphy elasticity 0.03–0.08) as the convex upper bound. |
| C4 **[M]** | **The disruption ends when the data ends**: shocks applied only Mar–May 2026 (months with >0.05% loss); nothing persists beyond May except the IRF dynamics. February's 1–2 decline days are dropped by the 0.05% threshold. | `monthly_supply_loss_pct` filter; shock path length | Extend the loss series with an assumed continuation (e.g. 6 more months at May's rate) before calling `supply_shock_path`. |
| C5 **[M]** | **The 13-month bridge is news-free**: estimation ends 2025-01, so the path to Feb 2026 is the unconditional VAR forecast — no 2025 shocks, no market information from 2025–26 except the satellite data. | `run_scenarios` offset logic | Fetch post-2025 prices (DATA_REQUEST_PROMPT.md), re-estimate, and re-anchor. |
| C6 **[M]** | **Precautionary-demand overlay = a one-month, 1990-Gulf-War-sized oil-specific demand shock (≈3.4 sd)**, optional and additive. Fear premium doesn't persist or grow. | `gulf_war_sd` in `scripts/run_all.py::stage_scenarios`; `precautionary_sd` arg | Set any size/duration; spread it over several months. |
| C7 **[L]** | **Constant-dollar reporting**: scenario paths in 2025-01 USD via the last observed CPI; separately, a **2.5%/yr CPI** assumption converts them to nominal for the options comparison. | `ref_cpi` in `run_all.py`; `CPI_ASSUMPTION = 0.025` in `scripts/options_analysis.py` | Change the inflation rate; levels shift ~1–3%. |

## D. Forecast evaluation (`src/oil_models/evaluate.py`, `benchmarks.py`)

| # | Assumption | Value / location | How to stress it |
|---|---|---|---|
| D1 **[M]** | **No-change benchmark uses monthly-average prices** (the dataset's construction). Benyo et al. (2026) show edges can vanish under end-of-month benchmarks. | `benchmarks.no_change` on the monthly series | Re-test with end-of-month prices once daily data is fetched. |
| D2 **[M]** | **Final revised data, not real-time vintages**: the harness sees today's revised production/CPI history, which slightly flatters all models. | `recursive_forecasts` uses the one dataset | Real-time vintages (ALFRED) would be the clean fix. |
| D3 **[L]** | **Regressors are known at the forecast origin**: month-t production and IGREA are usable for month-t forecasts, ignoring 1–2 month publication lags. | `adapted_regression` uses `iloc[-1]` | Lag regressors by their true publication delay. |
| D4 **[L]** | Evaluation window 1992→2025, horizons 1/3/6/12, expanding window; DM test with HLN correction and Bartlett truncation at h−1. | `recursive_forecasts(start="1992-01-01")`, `dm_test` | Shift the start; results are sample-sensitive (the 2014 and 2020 crashes dominate). |
| D5 **[L]** | **Equal weights** in the combination, membership = {no-change, AR(1), VAR, regression}. | `combine.equal_weight` call in `run_all.py` | Add/remove members; the literature says don't estimate weights. |

## E. Volatility (`src/oil_models/volatility.py`)

| # | Assumption | Value / location | How to stress it |
|---|---|---|---|
| E1 **[M]** | **GARCH(1,1) with Student-t** captures the risk; no leverage asymmetry (EGARCH), no regime switching, no jumps. Volatility is independent of the level forecast. | `fit_garch_t` | Fit EGARCH / Markov-switching GARCH; in a crisis regime plain GARCH understates persistence of high vol. |

## F. Options-implied densities (`src/oil_models/options_rnd.py`, `scripts/options_analysis.py`)

| # | Assumption | Value / location | How to stress it |
|---|---|---|---|
| F1 **[H]** | **Risk-neutral = upper bound on real-world probability**, with no quantitative risk-premium correction. Tail P(>$X) numbers embed the market's fear price, not just its forecast. | Stated in report; no adjustment anywhere | Apply a pricing-kernel adjustment (e.g. power utility) to shift RND → physical; tail probs drop meaningfully. |
| F2 **[H]** | **The smile beyond quoted strikes (~$95–101 top) decays smoothly to flat** (slope decay scale = 15% of the future). Everything above ~$100 — i.e. most of the headline tail — rides on this extrapolation. | `scale = 0.15 * chain.future` in `fit_rnd` | Vary scale 0.05–0.5; better, export wider strikes ($120–150 wings) and re-run. |
| F3 **[M]** | **Black-76, European exercise**: CL options are American; early-exercise premium ignored (small for options on futures, larger deep ITM — we use OTM only, mitigating this). | `black76_call` | Compare with an American pricer (CRR tree) if you want precision. |
| F4 **[M]** | **Quoted IV mids are clean and synchronous**: one evening snapshot, bid>0 AND ask>0 filter defines a usable quote, mid IV taken at face value, OTM side only. | `otm_smile` | Filter by volume>0 instead; re-export at a liquid hour. |
| F5 **[L]** | Flat **4% risk-free rate**; distribution support 0.25×F to 3×F; spline smoothing factor 1.0; negative density clipped & renormalized. | `RISK_FREE`, `fit_rnd` args | All are low-sensitivity; vary and confirm (martingale drift check prints on every run). |
| F6 **[M]** | **Expiry month ≈ scenario calendar month, WTI ≈ the scenario's price concept**: option expiry mapped to the scenario path's month, and nominal WTI compared against scenario levels built from the refiners'-acquisition-cost real price (RAC usually sits $1–3 under WTI; basis ignored). | `scenario_prob_table` month mapping; comparison in `options_analysis.py` | Add a WTI–RAC basis adjustment; shift the month mapping ±1. |

## G. Inactive models awaiting data (`src/oil_models/regression.py`, `external_data.py`)

| # | Assumption | Value / location | How to stress it |
|---|---|---|---|
| G1 **[M]** | EIA STEO spec is linear with **US inventories proxying the global balance** and a **prior-4-year seasonal norm** defining "normal" OECD stocks. | `build_eia_dataset`, `external_data.seasonal_norm(years=4)` | Change norm window (5-yr is the IEA convention); add Hormuz flow anomaly as a regressor once price overlap exists. |
| G2 **[L]** | Product-spread model uses the **single gasoline spread with intercept forced to 0**; futures member treats the futures price as the forecast (ignoring the risk premium, deliberately, as a benchmark). | `product_spread_forecast`; `benchmarks.futures_based` | Free the intercept to see why the restriction matters. |

## H. Data provenance (inherited, not chosen here)

| # | Assumption | Notes |
|---|---|---|
| H1 **[L]** | The Kilian dataset merge (EIA production, corrected IGREA, CPIAUCSL, RAC price) is accurate; the production column's units label is wrong (values are thousand bbl/d) but harmless since only growth rates enter. | `docs/DATA_DICTIONARY.md` |
| H2 **[L]** | Your workbook's conversion arithmetic is correct — we reproduce its baseline to 99.9% and its 94-day shortfall to 98.6%; the residual is its "before feb 24" cutoff vs our 2026-02-28. | `hormuz.validate_against_workbook` |

---

## The five that matter most

If you stress only five, make it these — together they drive nearly all
headline numbers:

1. **A1 + A2 + A3** (laden-flow reading, full-cargo DWT conversion, no
   pipeline bypass) — jointly set the size of the measured shock.
2. **C2** (pass-through fractions) — the main narrative dial between
   "manageable rerouting" and "full loss".
3. **C3** (linear IRF extrapolation) — makes the full-loss path a *floor*,
   not a ceiling; the elasticity view implies far higher prices for a
   sustained full closure.
4. **B5** (Cholesky ordering) — the entire supply/demand shock labelling
   rests on it.
5. **F1 + F2** (risk-neutral reading + smile extrapolation past ~$100) —
   both push the options tail numbers around; wider-strike exports fix F2
   cheaply.

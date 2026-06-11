# Oil Price Forecasting — Kilian SVAR + Hormuz Disruption Analysis

Implements the models from the research brief and build guides in `docs/`
(Kilian 2009 structural VAR, supply-demand regressions, forecast
combination, GARCH volatility, honest out-of-sample evaluation) and
integrates a satellite-measured Strait of Hormuz tanker dataset
(`data/raw/Boil_1.xlsx`) as a measured supply shock: daily tanker DWT
transits converted to barrels of oil equivalent, showing a ~96% collapse in
laden crude flows from 2026-02-28.

## Quick start

```bash
pip install -r requirements.txt
python scripts/run_all.py            # full pipeline (~2-3 min, 1000 bootstrap reps)
python scripts/run_all.py --fast     # smoke run (200 reps, ~30 s)
python scripts/options_analysis.py   # options-implied tail risk (needs run_all first)
```

Outputs: `reports/RESULTS.md`, `reports/OPTIONS_TAIL_RISK.md`,
`reports/figures/`, `data/processed/`.

## What gets built

| Stage | What | Where |
|---|---|---|
| Data | Kilian monthly dataset 1974–2025, validated | `src/oil_models/data_prep.py` |
| Hormuz | Tidy daily/monthly transit flows, baseline vs collapse, cumulative shortfall, days-of-consumption, implied inventory draw | `src/oil_models/hormuz.py` |
| Replication | Kilian (2009) SVAR on his 1973–2007 data — the validation gate | `src/oil_models/kilian_var.py` |
| Full SVAR | Same model on 1974–2025: IRFs (wild-bootstrap bands), FEVD, historical decomposition | same |
| Scenarios | Hormuz transit loss → structural supply shocks → conditional price paths (25% / 50% / full pass-through, optional 1990-sized precautionary demand overlay) | `src/oil_models/scenarios.py` |
| Evaluation | Recursive out-of-sample: MSPE vs no-change, Diebold-Mariano, directional accuracy; equal-weight combination | `src/oil_models/evaluate.py`, `combine.py` |
| Volatility | GARCH(1,1)-t on monthly returns, separate from the level forecast | `src/oil_models/volatility.py` |
| Options tail risk | Breeden-Litzenberger risk-neutral densities from WTI option chains; market-implied probabilities of the SVAR scenario levels | `src/oil_models/options_rnd.py` |

Notebooks in `notebooks/` are thin interactive wrappers over the package.

## The Hormuz integration (supply & demand)

- **Supply:** the lost laden crude flow (West>East), as a % of world
  production, becomes a sequence of structural oil-supply shocks pushed
  through the estimated SVAR impulse responses — conditional price scenario
  paths in `reports/figures/05_scenario_paths.png`.
- **Demand:** the cumulative shortfall is expressed in days of
  China/USA/EU/global consumption, and an **implied inventory-draw series**
  (`hormuz_implied_inv_draw_mmb` in `data/processed/hormuz_monthly.csv`) is
  the Kilian-Murphy ΔInventory proxy, ready for the 4-variable extension.
- **Nowcasting slot:** `hormuz_monthly.csv` is keyed by month-start dates so
  it merges directly onto the VAR dataset once post-2025 prices arrive —
  the satellite series then becomes a timely regressor that leads official
  (2-month-lagged) inventory data.

## Missing data → `DATA_REQUEST_PROMPT.md`

This environment cannot reach FRED/EIA/IBKR. The EIA STEO inventory
regression, restricted gasoline-spread model, and futures benchmark are
fully coded but inactive until the files specified in
`DATA_REQUEST_PROMPT.md` are placed in `data/external/`. Give that prompt
to Claude on an internet-connected machine, drop the CSVs in, and re-run.

## Caveats (read before quoting numbers)

- The measured transit loss (~20–24% of world production) is far outside
  the shock sizes the linear VAR was estimated on; the full-loss scenario
  is the model's upper bound, not a point prediction.
- The estimation sample ends 2025-01; scenario paths ride on a 13-month
  unconditional forecast before the shocks hit. Re-estimate with updated
  data (see prompt) and validate against the realized 2026 price move.
- The no-change benchmark here uses monthly-average prices; check
  robustness to an end-of-month definition before trusting any edge
  (Benyo et al. 2026).
